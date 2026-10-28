"""NN sweep (P20.4): CCNN, compact_eegnet and eegnet on built continuous windows, trial-grouped CV, no smoothing.

Data source: `<data-root>/w<len>_s<stride>/<S>/` (`scripts.build_windows --filter-mode continuous --stride-sec ...`),
read only through `src.io.subject_data.load_subject` (shared quality decision, R5; fs from the metadata; kept channels
of each subject, never a fixed count). Classes 101-105 only.

CV (R1): `StratifiedGroupKFold(5, shuffle, random_state=seed+r)` with the true trial ids (`cv_groups`) as groups; the
script asserts that no trial is in both train and test. Each fold calls `src.models.cnn.training.cnn_fold`
(PF-32: early-stopping validation = first inner grouped split of the TRAINING trials, ~20 %; AdamW / cosine / label
smoothing 0.1, patience 25, max 150 epochs, best validation-loss state; augmentation on by default, `--no-augment`
turns it off; normalisation statistics and augmentation use training windows only, R2).

Model names (PF-31): `ccnn`; `compact_eegnet` (CLI alias `compact`) = EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2,
dropout=0.5); `eegnet` = EEGNetSSVEP(F1=8, D=2, F2=16, kernel=fs//2). Neither is P09's `compact_cnn`.

Output (`<out-dir>`, default reports/nn_sweep): `summary.csv` (Subject, Window (s), Method, Windows, Trials, Acc (%),
Acc SD, BalAcc (%), ITR (bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch; plus Params, Augment, Device,
Data source), `folds.csv` (one row per fold), `predictions.csv` (subject, window_sec, method, run, trial_id, offset_sec,
true, pred, p_101..p_105) and `confusion.csv` (window_sec, method, true, pred, count). Acc = pooled over the test
windows of the run(s); Acc SD = SD over runs (0 when Runs = 1); Train/Val Acc and Best Epoch = mean over folds
(Train Acc: eval mode, un-augmented fitting windows, PF-30). ITR: Wolpaw, N = 5, T = window + 0.5 s.
"""

import argparse
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
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from src.io.subject_data import CLASS_CODES, discover_subjects, is_built, load_subject  # noqa: E402
from src.models.classical.benchmark_runner import load_config  # noqa: E402
from src.models.cnn.spatial_spectral_cnn import label_maps, resolve_device  # noqa: E402
from src.models.cnn.training import ALIASES, MODELS, cnn_fold  # noqa: E402
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials, make_splits  # noqa: E402
from src.preprocessing.window_quality import quality_params_from_config  # noqa: E402

GAZE_SEC = 0.5
SEED = 42
SUMMARY_COLUMNS = ["Subject", "Window (s)", "Method", "Windows", "Trials", "Acc (%)", "Acc SD", "BalAcc (%)",
                   "ITR (bits/min)", "Train Acc (%)", "Runs", "Val Acc (%)", "Best Epoch", "Params", "Augment",
                   "Device", "Data source"]


def itr_bits_per_min(acc: float, n_classes: int, seconds: float) -> float:
  """Wolpaw ITR in bits/min; 0 for acc <= 1/N, log2(N) bits for acc = 1."""
  if acc <= 1.0 / n_classes:
    return 0.0
  bits = np.log2(n_classes) if acc >= 1.0 else (
    np.log2(n_classes) + acc * np.log2(acc) + (1 - acc) * np.log2((1 - acc) / (n_classes - 1)))
  return float(bits * 60.0 / seconds)


def balanced_accuracy(y: np.ndarray, pred: np.ndarray) -> float:
  return float(np.mean([np.mean(pred[y == c] == c) for c in np.unique(y)]))


def folder_name(window: float, stride: float) -> str:
  return f"w{window:g}_s{stride:g}"


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--data-root", type=Path, default=Path("data/processed_continuous"))
  p.add_argument("--windows", type=float, nargs="+", default=[1.0], help="window lengths in s (default 1)")
  p.add_argument("--stride", type=float, default=0.25, help="stride of the built folders (default 0.25)")
  p.add_argument("--models", nargs="+", default=["ccnn", "compact", "eegnet"],
                 help="ccnn, compact (= compact_eegnet), compact_eegnet, eegnet")
  p.add_argument("--subjects", nargs="*", default=None, help="default: every S<k> found")
  p.add_argument("--no-augment", action="store_true", help="turn the P10 augmentation off (default on)")
  p.add_argument("--repeats", type=int, default=1, help="CV repeats, seed 42+r (default 1)")
  p.add_argument("--max-folds", type=int, default=None, help="smoke runs: evaluate only the first k folds")
  p.add_argument("--max-epochs", type=int, default=150)
  p.add_argument("--patience", type=int, default=25)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--seed", type=int, default=SEED)
  p.add_argument("--config", type=Path, default=None)
  p.add_argument("--out-dir", type=Path, default=Path("reports/nn_sweep"))
  return p


def run_subject_model(d: dict, model: str, window: float, args, dev: str, thresholds_note: str) -> tuple:
  """CV of one subject x model. Returns `(summary_row, fold_rows, prediction_frame, confusion_counts)`."""
  classes, to_idx = label_maps(d["y"])
  yi = np.array([to_idx[int(c)] for c in d["y"]])
  groups, ids, offs = np.asarray(d["cv_groups"]), np.asarray(d["trial_ids"]), np.asarray(d["offsets"])
  X, fs = d["X"], float(d["fs"])
  n_cls = len(classes)
  accs, fold_rows, preds, runs_pred = [], [], [], []
  for r in range(args.repeats):
    seed = args.seed + r
    splits = make_splits("grouped", yi, groups, seed)
    assert_no_shared_trials(splits, groups)
    proba = np.full((len(yi), n_cls), np.nan)
    for k, (tr, te) in enumerate(splits):
      if args.max_folds is not None and k >= args.max_folds:
        break
      t0 = time.time()
      out = cnn_fold(X[tr], yi[tr], groups[tr], X[te], fs, n_cls, model=model, seed=seed + k, device=dev,
                     augment=not args.no_augment, max_epochs=args.max_epochs, patience=args.patience)
      proba[te] = out["proba"]
      fold_rows.append({"Subject": d["subject"], "Window (s)": window, "Method": model, "Run": r, "Fold": k,
                        "Train windows": len(tr), "Test windows": len(te),
                        "Train Acc (%)": round(100 * out["train_acc"], 2), "Val Acc (%)": round(100 * out["val_acc"], 2),
                        "Test Acc (%)": round(100 * float(np.mean(out["proba"].argmax(1) == yi[te])), 2),
                        "Best Epoch": out["best_epoch"], "Epochs run": out["epochs_run"],
                        "Params": out["n_params"], "Seconds": round(time.time() - t0, 1)})
      print(f"    {d['subject']} {model} w{window:g} run {r} fold {k}: train {fold_rows[-1]['Train Acc (%)']:.2f}% "
            f"val {fold_rows[-1]['Val Acc (%)']:.2f}% test {fold_rows[-1]['Test Acc (%)']:.2f}% best epoch "
            f"{out['best_epoch']}/{out['epochs_run']} ({fold_rows[-1]['Seconds']:.1f} s)", flush=True)
    ok = ~np.isnan(proba[:, 0])
    pred_idx = proba[ok].argmax(1)
    accs.append(float(np.mean(pred_idx == yi[ok])))
    frame = pd.DataFrame({"subject": d["subject"], "window_sec": window, "method": model, "run": r,
                          "trial_id": ids[ok], "offset_sec": offs[ok], "true": np.array(classes)[yi[ok]],
                          "pred": np.array(classes)[pred_idx]})
    for j, c in enumerate(classes):
      frame[f"p_{c}"] = proba[ok][:, j]
    preds.append(frame)
    runs_pred.append((yi[ok], pred_idx))
  yy = np.concatenate([a for a, _ in runs_pred])
  pp = np.concatenate([b for _, b in runs_pred])
  acc = float(np.mean(yy == pp))
  mine = [f for f in fold_rows]
  row = {"Subject": d["subject"], "Window (s)": window, "Method": model, "Windows": len(yi),
         "Trials": int(len(np.unique(groups))), "Acc (%)": round(100 * acc, 2),
         "Acc SD": round(100 * float(np.std(accs, ddof=1)), 2) if len(accs) > 1 else 0.0,
         "BalAcc (%)": round(100 * balanced_accuracy(yy, pp), 2),
         "ITR (bits/min)": round(itr_bits_per_min(acc, n_cls, window + GAZE_SEC), 2),
         "Train Acc (%)": round(float(np.mean([f["Train Acc (%)"] for f in mine])), 2), "Runs": args.repeats,
         "Val Acc (%)": round(float(np.mean([f["Val Acc (%)"] for f in mine])), 2),
         "Best Epoch": round(float(np.mean([f["Best Epoch"] for f in mine])), 1), "Params": mine[0]["Params"],
         "Augment": "off" if args.no_augment else "on", "Device": dev, "Data source": d["source"]}
  cm = np.zeros((n_cls, n_cls), dtype=int)
  np.add.at(cm, (yy, pp), 1)
  return row, fold_rows, pd.concat(preds, ignore_index=True), (classes, cm)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  models = [ALIASES.get(m, m) for m in args.models]
  bad = [m for m in models if m not in MODELS]
  if bad:
    print(f"[x] unknown model(s) {bad}; choose from {list(MODELS)} (alias compact)")
    return 1
  cfg = load_config(args.config or ROOT / "configs" / "pipeline_config.yaml")
  q = quality_params_from_config(cfg)
  thresholds = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  dev = resolve_device(args.device).type
  if dev == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  summary, folds, preds, confs = [], [], [], []
  t_all = time.time()
  print(f"NN sweep: models {models} (PF-31 labels; `compact_eegnet` is not P09 `compact_cnn`), augment "
        f"{'off' if args.no_augment else 'on'}, device {dev}, repeats {args.repeats}, seed {args.seed}; "
        f"CV StratifiedGroupKFold(5, shuffle, seed+r) on true trial ids (R1); early stopping on 20% of the training "
        f"trials (PF-32); no smoothing")
  for w in args.windows:
    root = args.data_root / folder_name(w, args.stride)
    if not root.is_dir():
      print(f"[-] {root} not found, skipping window {w:g} s")
      continue
    subjects = args.subjects or discover_subjects(root)
    print(f"Data source: {root}/<S>/ via load_subject (shared quality decision), subjects {', '.join(subjects)}")
    for s in subjects:
      sub = root / s
      if not is_built(sub):
        print(f"[-] {sub} is not a built folder, skipping")
        continue
      d = load_subject(sub, CLASS_CODES, "shared", thresholds=thresholds, channel_fail_fraction=q["channel_fail_fraction"])
      print(f"[+] {s} w{w:g}: {len(d['y'])} windows of {d['n_trials']} trials, fs {d['fs']:g} ({d['fs_source']}), "
            f"channels kept {len(d['channel_names'])} [{', '.join(d['channel_names'])}], {d['source']}", flush=True)
      for m in models:
        row, fr, pr, (classes, cm) = run_subject_model(d, m, w, args, dev, "")
        summary.append(row)
        folds += fr
        preds.append(pr)
        confs += [{"window_sec": w, "method": m, "true": classes[i], "pred": classes[j], "count": int(cm[i, j])}
                  for i in range(len(classes)) for j in range(len(classes))]
        print(f"[+] {s} w{w:g} {m}: acc {row['Acc (%)']:.2f}% balacc {row['BalAcc (%)']:.2f}% train "
              f"{row['Train Acc (%)']:.2f}% val {row['Val Acc (%)']:.2f}% best epoch {row['Best Epoch']} "
              f"ITR {row['ITR (bits/min)']:.2f} params {row['Params']}", flush=True)
  if not summary:
    print("[-] nothing evaluated")
    return 1
  out = args.out_dir
  out.mkdir(parents=True, exist_ok=True)
  df = pd.DataFrame(summary, columns=SUMMARY_COLUMNS)
  df.to_csv(out / "summary.csv", index=False)
  pd.DataFrame(folds).to_csv(out / "folds.csv", index=False)
  pd.concat(preds, ignore_index=True).to_csv(out / "predictions.csv", index=False)
  conf = pd.DataFrame(confs).groupby(["window_sec", "method", "true", "pred"], as_index=False)["count"].sum()
  conf.to_csv(out / "confusion.csv", index=False)
  print("\n" + df.drop(columns=["Data source"]).to_string(index=False))
  print(f"\nSaved: {out}/summary.csv, folds.csv, predictions.csv, confusion.csv; runtime {time.time() - t_all:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
