"""Window-length sweep (P20.2): accuracy and ITR against window length for FBCCA, in-fold FBCSP+FBCCA LDA and a CNN.

Data source: `<data-root>/w<len>_s<stride>/<S>/` (`scripts.build_windows --filter-mode continuous --banks fbcca fbcsp
--stride-sec ...`), read only through `src.io.subject_data.load_subject` (shared quality decision, R5; fs from the
metadata; the channels kept of each subject, never a fixed count). Classes 101-105 only. No smoothing.

Methods (labels in every table):
- `fbcca`: vectorized FBCCA (`fbcca_extraction.reference_bases` / `fbcca_scores_vectorized`: QR-orthonormalised mean-centred
  sin/cos references, 3 harmonics; top singular value of `Qx^T Qy`, clipped to [0, 1]; weighted squared sum over the saved
  continuous `fbcca` bank), prediction = argmax. Nothing is trained, so it is evaluated once on all windows: Runs 1,
  Acc SD 0, no train accuracy, no probabilities (`p_*` empty).
- `lda`: `lda_fold` = in-fold CSP per band (m = 1, saved `fbcsp` bank) + FBCCA scores -> StandardScaler ->
  Shrinkage-LDA (lsqr, auto); `--cv-repeats` repeats; `p_*` = predict_proba.
- `cnn (compact_eegnet)` (CLI `cnn`): `src.models.cnn.training.cnn_fold` with `compact_eegnet` = EEGNetSSVEP(F1=96, D=1,
  F2=96, kernel=fs//2, dropout=0.5) at the real fs (PF-31; not P09's `compact_cnn`); `--cnn-repeats` repeats; early-stopping
  validation = 20 % of the training trials (PF-32); `p_*` = softmax.

CV (R1, R2): `StratifiedGroupKFold(5, shuffle, random_state=seed+r)` with the true trial ids (`cv_groups`) as groups; the
script asserts that no trial id is in both train and test of any fold (stride-0.25 windows of one trial overlap by up to
94 %). Scalers, CSP filters and network statistics are fitted on the training windows only.

Output (`--out-dir`, default reports/window_sweep): `summary.csv` (Subject, Window (s), Method, Windows, Trials, Acc (%),
Acc SD, BalAcc (%), ITR (bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch, Data source), `predictions.csv` (subject,
window_sec, method, run, trial_id, offset_sec, true, pred, p_101..p_105), `confusion.csv` (window_sec, method, true, pred,
count; pooled over subjects and runs), `timing.csv` (seconds per subject x window x method) and `sweep_config.json`.
Acc = pooled over the test windows of all runs; Acc SD = SD over runs; ITR = Wolpaw, N = 5, T = window + 0.5 s.

Splitting the work: methods can be run in separate invocations (`--methods fbcca lda`, later `--methods cnn`, possibly on
another machine) into the same `--out-dir`. Each run MERGES into the existing files: it replaces only the rows of its own
(method, window, subject) cells and sorts everything canonically (method order fbcca, lda, cnn; then window, subject, run,
trial_id, offset_sec), so the combined files are identical whatever the order of the runs. A run whose shared settings
(stride, seed, classes, quality) differ from the stored ones for other methods is refused unless `--overwrite`.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Sequence


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else three levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.features.ssvep.fbcca_extraction import TARGET_FREQS, fbcca_scores_vectorized, reference_bases  # noqa: E402
from src.io.subject_data import CLASS_CODES, discover_subjects, is_built, load_subject  # noqa: E402
from src.models.classical.benchmark_runner import load_config  # noqa: E402
from src.models.classical.legacy_eval import FeatureSpace, fold_matrices  # noqa: E402
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials, make_splits  # noqa: E402
from src.preprocessing.window_quality import quality_params_from_config  # noqa: E402

GAZE_SEC = 0.5
SEED = 42
FBCCA, LDA, CNN = "fbcca", "lda", "cnn (compact_eegnet)"
METHOD_ORDER = [FBCCA, LDA, CNN]
CLI_METHODS = {"fbcca": FBCCA, "lda": LDA, "cnn": CNN}
SHARED_CONFIG_KEYS = ("stride", "seed", "classes", "quality")
SUMMARY_COLUMNS = ["Subject", "Window (s)", "Method", "Windows", "Trials", "Acc (%)", "Acc SD", "BalAcc (%)",
                   "ITR (bits/min)", "Train Acc (%)", "Runs", "Val Acc (%)", "Best Epoch", "Data source"]
CELL = ["Subject", "Window (s)", "Method"]


def itr_bits_per_min(acc: float, n_classes: int, seconds: float) -> float:
  """Wolpaw ITR in bits/min; 0 for acc <= 1/N, log2(N) bits for acc = 1 (the limit)."""
  if acc <= 1.0 / n_classes:
    return 0.0
  bits = np.log2(n_classes) if acc >= 1.0 else (
    np.log2(n_classes) + acc * np.log2(acc) + (1 - acc) * np.log2((1 - acc) / (n_classes - 1)))
  return float(bits * 60.0 / seconds)


def balanced_accuracy(y: np.ndarray, pred: np.ndarray) -> float:
  return float(np.mean([np.mean(pred[y == c] == c) for c in np.unique(y)]))


def folder_name(window: float, stride: float) -> str:
  return f"w{window:g}_s{stride:g}"


def fbcca_features(d: dict) -> np.ndarray:
  """Vectorized FBCCA scores `(n, 5)` of a loaded built subject (saved continuous `fbcca` bank, R3; no fitting)."""
  bands = d["bands"]["fbcca"]
  bases = reference_bases(d["fs"], bands.shape[-1], TARGET_FREQS)
  return fbcca_scores_vectorized(bands, bases)


def lda_fold(csp_bands: np.ndarray, fbcca: np.ndarray, y: np.ndarray, tr: np.ndarray, te: np.ndarray,
             seed: int = SEED) -> tuple:
  """One fold of the flagship: in-fold CSP (m = 1) per band on `csp_bands[tr]` + FBCCA scores -> StandardScaler ->
  Shrinkage-LDA (lsqr, auto), all fitted on the training rows only (R2). Returns `(proba_te (n_te, K), train_acc)` with the
  columns in sorted class order (`y` are indices 0..K-1)."""
  space = FeatureSpace("FBCSP + FBCCA (in-fold)", [fbcca], fbcsp_m=1)
  xtr, xte = fold_matrices(space, csp_bands, y, tr, te)
  model = Pipeline([("scaler", StandardScaler()), ("lda", get_sklearn_model_suite(seed)["Shrinkage-LDA lsqr"])])
  model.fit(xtr, y[tr])
  return model.predict_proba(xte), float(np.mean(model.predict(xtr) == y[tr]))


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--data-root", type=Path, default=Path("data/processed_continuous"))
  p.add_argument("--windows", type=float, nargs="+", default=[0.5, 1, 1.5, 2, 3, 4], help="window lengths in s")
  p.add_argument("--stride", type=float, default=0.25, help="stride of the built folders (default 0.25)")
  p.add_argument("--methods", nargs="+", default=["fbcca", "lda", "cnn"], choices=sorted(CLI_METHODS),
                 help="run a subset and merge into --out-dir (e.g. fbcca lda locally, cnn on a GPU machine)")
  p.add_argument("--subjects", nargs="*", default=None, help="default: every S<k> found")
  p.add_argument("--cv-repeats", type=int, default=5, help="repeats of the LDA CV, seed 42+r (default 5)")
  p.add_argument("--cnn-repeats", type=int, default=1, help="repeats of the CNN CV (default 1)")
  p.add_argument("--max-folds", type=int, default=None, help="smoke runs: evaluate only the first k folds")
  p.add_argument("--no-augment", action="store_true", help="CNN: turn the P10 augmentation off (default on)")
  p.add_argument("--max-epochs", type=int, default=150)
  p.add_argument("--patience", type=int, default=25)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--seed", type=int, default=SEED)
  p.add_argument("--config", type=Path, default=None)
  p.add_argument("--out-dir", type=Path, default=Path("reports/window_sweep"))
  p.add_argument("--overwrite", action="store_true", help="replace stored results made with different shared settings")
  return p


def _prediction_frame(d: dict, window: float, method: str, run: int, idx: np.ndarray, yi: np.ndarray,
                      classes: np.ndarray, pred_idx: np.ndarray, proba: Optional[np.ndarray]) -> pd.DataFrame:
  frame = pd.DataFrame({"subject": d["subject"], "window_sec": window, "method": method, "run": run,
                        "trial_id": np.asarray(d["trial_ids"])[idx], "offset_sec": np.asarray(d["offsets"])[idx] / float(d["fs"]),
                        "true": classes[yi[idx]], "pred": classes[pred_idx]})
  for j, c in enumerate(classes):
    frame[f"p_{c}"] = np.nan if proba is None else proba[:, j]
  return frame


def run_cell(d: dict, window: float, method: str, args, dev: str, fb: np.ndarray) -> tuple:
  """CV of one subject x window x method. Returns `(summary_row, prediction_frame, (classes, confusion), seconds)`."""
  t0 = time.time()
  classes = np.unique(d["y"])
  yi = np.searchsorted(classes, d["y"])
  groups = np.asarray(d["cv_groups"])
  n_cls = len(classes)
  everything = np.arange(len(yi))
  frames, ys, ps, accs, trains, vals, epochs = [], [], [], [], [], [], []
  if method == FBCCA:
    pred_idx = fb.argmax(1)
    frames.append(_prediction_frame(d, window, method, 0, everything, yi, classes, pred_idx, None))
    ys, ps, accs = [yi], [pred_idx], [float(np.mean(pred_idx == yi))]
    runs = 1
  else:
    runs = args.cv_repeats if method == LDA else args.cnn_repeats
    csp_bands = d["bands"]["fbcsp"]
    for r in range(runs):
      seed = args.seed + r
      splits = make_splits("grouped", yi, groups, seed)
      assert_no_shared_trials(splits, groups)   # R1 runtime guard
      proba = np.full((len(yi), n_cls), np.nan)
      for k, (tr, te) in enumerate(splits):
        if args.max_folds is not None and k >= args.max_folds:
          break
        if method == LDA:
          proba[te], tacc = lda_fold(csp_bands, fb, yi, tr, te, seed)
          trains.append(tacc)
        else:
          from src.models.cnn.training import cnn_fold
          out = cnn_fold(d["X"][tr], yi[tr], groups[tr], d["X"][te], float(d["fs"]), n_cls, model="compact_eegnet",
                         seed=seed + k, device=dev, augment=not args.no_augment, max_epochs=args.max_epochs,
                         patience=args.patience)
          proba[te] = out["proba"]
          trains.append(out["train_acc"])
          vals.append(out["val_acc"])
          epochs.append(out["best_epoch"])
          print(f"    {d['subject']} w{window:g} {method} run {r} fold {k}: train {100 * out['train_acc']:.2f}% val "
                f"{100 * out['val_acc']:.2f}% best epoch {out['best_epoch']}/{out['epochs_run']}", flush=True)
      ok = ~np.isnan(proba[:, 0])
      pred_idx = proba[ok].argmax(1)
      frames.append(_prediction_frame(d, window, method, r, np.flatnonzero(ok), yi, classes, pred_idx, proba[ok]))
      ys.append(yi[ok])
      ps.append(pred_idx)
      accs.append(float(np.mean(pred_idx == yi[ok])))
  yy, pp = np.concatenate(ys), np.concatenate(ps)
  acc = float(np.mean(yy == pp))
  row = {"Subject": d["subject"], "Window (s)": window, "Method": method, "Windows": len(yi),
         "Trials": int(len(np.unique(groups))), "Acc (%)": round(100 * acc, 2),
         "Acc SD": round(100 * float(np.std(accs, ddof=1)), 2) if len(accs) > 1 else 0.0,
         "BalAcc (%)": round(100 * balanced_accuracy(yy, pp), 2),
         "ITR (bits/min)": round(itr_bits_per_min(acc, n_cls, window + GAZE_SEC), 2),
         "Train Acc (%)": round(100 * float(np.mean(trains)), 2) if trains else np.nan, "Runs": runs,
         "Val Acc (%)": round(100 * float(np.mean(vals)), 2) if vals else np.nan,
         "Best Epoch": round(float(np.mean(epochs)), 1) if epochs else np.nan, "Data source": d["source"]}
  cm = np.zeros((n_cls, n_cls), dtype=int)
  np.add.at(cm, (yy, pp), 1)
  return row, pd.concat(frames, ignore_index=True), (classes, cm), time.time() - t0


def canonical(df: pd.DataFrame, keys: list) -> pd.DataFrame:
  """Deterministic row order: method order, then the remaining keys."""
  df = df.copy()
  df["_m"] = df[keys[0]].map({m: i for i, m in enumerate(METHOD_ORDER)}).fillna(len(METHOD_ORDER))
  return df.sort_values(["_m"] + keys[1:], kind="mergesort").drop(columns="_m").reset_index(drop=True)


def merge_frame(path: Path, new: pd.DataFrame, cell_cols: dict, order: list, columns: Optional[list] = None) -> pd.DataFrame:
  """Merge `new` into the CSV at `path`: stored rows of the (method, window, subject) cells being replaced are dropped.
  `cell_cols` maps the cell keys to this file's column names."""
  if path.is_file():
    old = pd.read_csv(path)
    hit = np.zeros(len(old), dtype=bool)
    cells = set(zip(new[cell_cols["m"]], new[cell_cols["w"]].round(6), new[cell_cols["s"]])) if cell_cols.get("s") else \
      set(zip(new[cell_cols["m"]], new[cell_cols["w"]].round(6)))
    keys = zip(old[cell_cols["m"]], old[cell_cols["w"]].round(6), old[cell_cols["s"]]) if cell_cols.get("s") else \
      zip(old[cell_cols["m"]], old[cell_cols["w"]].round(6))
    hit = np.array([k in cells for k in keys], dtype=bool)
    new = pd.concat([old[~hit], new], ignore_index=True)
  out = canonical(new, order)
  return out[columns] if columns else out


def check_config(path: Path, mine: dict, methods: list, overwrite: bool) -> dict:
  """Stored per-method settings; refuse a merge whose shared settings differ from those of the other stored methods."""
  stored = json.loads(path.read_text()) if path.is_file() else {}
  for m, conf in stored.items():
    if m in methods:
      continue
    diff = {k: (conf.get(k), mine[k]) for k in SHARED_CONFIG_KEYS if conf.get(k) != mine[k]}
    if diff and not overwrite:
      raise SystemExit(f"[x] {path} holds results of '{m}' with different settings {diff} (stored, now); rerun with the "
                       "same settings or pass --overwrite")
  for m in methods:
    stored[m] = mine["methods"][m]
    stored[m].update({k: mine[k] for k in SHARED_CONFIG_KEYS})
  return stored


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  methods = [CLI_METHODS[m] for m in dict.fromkeys(args.methods)]
  methods = [m for m in METHOD_ORDER if m in methods]
  cfg = load_config(args.config or ROOT / "configs" / "pipeline_config.yaml")
  q = quality_params_from_config(cfg)
  thresholds = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  dev = "cpu"
  if CNN in methods:
    import torch
    from src.models.cnn.spatial_spectral_cnn import resolve_device
    dev = resolve_device(args.device).type
    if dev == "cuda":
      torch.backends.cudnn.deterministic = True
      torch.backends.cudnn.benchmark = False
  mine = {"stride": args.stride, "seed": args.seed, "classes": 5, "quality": "shared",
          "methods": {m: {"cv_repeats": args.cnn_repeats if m == CNN else (args.cv_repeats if m == LDA else 1),
                          "windows": args.windows, "subjects": args.subjects, "augment": (not args.no_augment) if m == CNN else None,
                          "max_folds": args.max_folds} for m in methods}}
  out = args.out_dir
  conf_path = out / "sweep_config.json"
  stored_conf = check_config(conf_path, mine, methods, args.overwrite)
  summary, preds, confs, times = [], [], [], []
  t_all = time.time()
  print(f"Window sweep: methods {methods} (PF-31: `cnn (compact_eegnet)` is not P09 `compact_cnn`), windows {args.windows}, "
        f"stride {args.stride:g}; CV StratifiedGroupKFold(5, shuffle, seed+r) on true trial ids (R1), scalers/CSP/network "
        f"statistics in-fold (R2); lda repeats {args.cv_repeats}, cnn repeats {args.cnn_repeats}; no smoothing; device {dev}")
  for w in args.windows:
    root = args.data_root / folder_name(w, args.stride)
    if not root.is_dir():
      print(f"[-] {root} not found, skipping window {w:g} s")
      continue
    subjects = args.subjects or discover_subjects(root)
    print(f"Data source: {root}/<S>/ via load_subject (shared quality decision, continuous filtering), "
          f"subjects {', '.join(subjects)}")
    for s in subjects:
      sub = root / s
      if not is_built(sub):
        print(f"[-] {sub} is not a built folder, skipping")
        continue
      t_load = time.time()
      d = load_subject(sub, CLASS_CODES, "shared", bands=("fbcca", "fbcsp"), thresholds=thresholds,
                       channel_fail_fraction=q["channel_fail_fraction"])
      fb = fbcca_features(d)
      t_load = time.time() - t_load
      print(f"[+] {s} w{w:g}: {len(d['y'])} windows of {d['n_trials']} trials, fs {d['fs']:g} ({d['fs_source']}), "
            f"channels kept {len(d['channel_names'])} [{', '.join(d['channel_names'])}], {d['source']}; "
            f"load + vectorized FBCCA features {t_load:.1f} s", flush=True)
      for m in methods:
        row, pr, (classes, cm), secs = run_cell(d, w, m, args, dev, fb)
        if m == FBCCA:
          secs += t_load
        summary.append(row)
        preds.append(pr)
        confs += [{"window_sec": w, "method": m, "true": int(classes[i]), "pred": int(classes[j]), "count": int(cm[i, j])}
                  for i in range(len(classes)) for j in range(len(classes))]
        times.append({"Subject": s, "Window (s)": w, "Method": m, "Seconds": round(secs, 2)})
        print(f"[+] {s} w{w:g} {m}: acc {row['Acc (%)']:.2f}% (SD {row['Acc SD']:.2f}) balacc {row['BalAcc (%)']:.2f}% "
              f"ITR {row['ITR (bits/min)']:.2f} runs {row['Runs']}; {secs:.1f} s", flush=True)
  if not summary:
    print("[-] nothing evaluated")
    return 1
  out.mkdir(parents=True, exist_ok=True)
  sm = merge_frame(out / "summary.csv", pd.DataFrame(summary), {"m": "Method", "w": "Window (s)", "s": "Subject"},
                   ["Method", "Window (s)", "Subject"], SUMMARY_COLUMNS)
  sm.to_csv(out / "summary.csv", index=False)
  pr = merge_frame(out / "predictions.csv", pd.concat(preds, ignore_index=True),
                   {"m": "method", "w": "window_sec", "s": "subject"},
                   ["method", "window_sec", "subject", "run", "trial_id", "offset_sec"])
  pr.to_csv(out / "predictions.csv", index=False)
  tm = merge_frame(out / "timing.csv", pd.DataFrame(times), {"m": "Method", "w": "Window (s)", "s": "Subject"},
                   ["Method", "Window (s)", "Subject"])
  tm.to_csv(out / "timing.csv", index=False)
  # confusion.csv is pooled over subjects: recomputed from the merged predictions so a partial rerun cannot double count
  cf = pr.groupby(["window_sec", "method", "true", "pred"], as_index=False).size().rename(columns={"size": "count"})
  full = pd.MultiIndex.from_product([sorted(pr["window_sec"].unique()), [m for m in METHOD_ORDER if m in set(pr["method"])],
                                     sorted(pr["true"].unique()), sorted(pr["true"].unique())],
                                    names=["window_sec", "method", "true", "pred"])
  cf = cf.set_index(["window_sec", "method", "true", "pred"]).reindex(full, fill_value=0).reset_index()
  cf = canonical(cf.rename(columns={"method": "Method"}), ["Method", "window_sec", "true", "pred"]).rename(columns={"Method": "method"})
  cf[["window_sec", "method", "true", "pred", "count"]].to_csv(out / "confusion.csv", index=False)
  conf_path.write_text(json.dumps(stored_conf, indent=2, sort_keys=True) + "\n")
  print("\n" + sm.drop(columns=["Data source"]).to_string(index=False))
  print(f"\nTiming (s per subject x window x method, this run):\n{pd.DataFrame(times).pivot_table(index='Window (s)', columns='Method', values='Seconds', aggfunc='sum').round(1).to_string()}")
  print(f"\nSaved: {out}/summary.csv, predictions.csv, confusion.csv, timing.csv, sweep_config.json; "
        f"runtime {time.time() - t_all:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
