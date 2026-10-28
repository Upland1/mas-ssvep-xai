"""Cohort benchmark of the flagship on legacy or built windows (P07.6 legacy Era A; ported to `load_subject` in P16.7;
`--bank` and `--classes` in P17).

Data source: `<data-root>/<S>/` read only through `src.io.subject_data.load_subject` (OO session). Default root
`data/processed` = legacy folders (7 channels, fs 250 assumed, trial ids reconstructed, per-script two-tier gate,
`i % 5` smoothing; reproduces the P11 leak-free R-6 exactly with the defaults). A root of folders written by
`scripts/build_windows.py` (`data/processed_per_window`, `data/processed_continuous`, 8 channels, fs from the
metadata, true trial ids, shared quality decision) is detected per subject: FBCCA reads the saved `fbcca`
bands and the CSP the saved `fbcsp` bands (nothing is refiltered; continuous = R3, per_window = legacy PF-14), the
2.0 s smoothing resets at each true trial id of rows ordered by (trial, offset) (R8), and the CV groups are the
loader's `cv_groups` (R1). Stimulus windows only, unless `--classes 6`.

P17: `--bank {base, harm, harm+mid}` appends narrow FBCSP bands to the 5 saved `fbcsp` bands (CSP m = 1 per band, in-fold;
FBCCA unchanged): `harm` = base + the saved `harmonic` bank (k*f, k = 1..3, 60 Hz band skipped by the build), `harm+mid` =
+ the saved `intermediate` bank (midpoints of neighbouring targets). Band counts come from the folder, order from the
metadata. `--classes 6` adds the fixation cross (condition 201; 202 never enters, PF-13) as a rest class: uniform LDA priors
(1/6), CV groups = true trial ids (`assert_no_shared_trials`), R8 smoothing on the 201 trials too; built roots only (a legacy
root raises). It adds the columns `Rest Windows, 1.0s/2.0s BalAcc (%), 1.0s/2.0s FalseAct (%), 1.0s/2.0s Missed (%),
2.0s StimCorrect (%)` (+ `... SD` per column under `--cv-repeats`) and writes the 2.0 s confusion matrices (summed over
CV repeats; rows = true class) to `<csv>_confusion.csv`; definitions in `src/models/classical/rest_metrics.py`.
`--fs` on a built root raises unless `--allow-fs-override` is given (diagnostic only; the fs of the metadata is the rule).

Per subject the flagship: FBCSP m = 1 (CSP fitted in-fold, R2/PF-11) + FBCCA (55 columns for 5 CSP bands x 5 classes
x 2 + 5 scores) -> StandardScaler -> Shrinkage-LDA (lsqr, auto), behind ONE quality decision (PF-10).
`--quality shared|shared-no-guard|per-script` picks it (R5; on legacy folders every value is the per-script
two-tier gate: vpp 5-120 uV, std 1-35 uV, channel dropped if failing in > 50 % of the windows).
`--fs` overrides the feature sampling rate (built default: metadata; legacy default: 250, PF-04).

CV protocol (P11): `--cv grouped` (default) = StratifiedGroupKFold(5, shuffle, seed) over trial ids (R1);
`--cv legacy` = the P05-P10 leaky window-level StratifiedKFold (output under <reports-dir>/legacy_leaky/, not
comparable). `--smoothing` (parser default mod5) is `trial` on built roots unless given explicitly (R8 era clause).
`--cv-repeats N` repeats the split with seeds `--seed + r` (42 + r) and reports the mean and the sample SD (ddof 1)
of the N accuracies; the seed-42 values are printed too.

Output: <reports-dir>[/legacy_leaky]/n_subjects_benchmark[_suffix].csv with the columns of 02_REQUIREMENTS section 6
(Subject, Channels Kept, Channels Dropped, Clean Windows, Rejected Windows, [Bank, CSP Bands,] 1.0s Acc (%),
2.0s Smoothed (%) [, 1.0s SD, 2.0s SD, CV repeats] [, 6-class columns]); `Bank, CSP Bands` appear on built roots; "Channels Kept" is the count,
"Channels Dropped" the names ("none" if empty); a Mean row follows. Suffix rule: `--out-suffix` is used verbatim;
without it a run that is not the legacy default (built root, `--quality` other than shared, `--fs` override,
`--cv-repeats` > 1, `--bank` other than base, `--classes 6`) gets a derived suffix (`<filter_mode>`, `<quality>`, `fs<fs>`,
`harm`/`harmmid`, `6class`, `rep<N>`), so a default file is never
overwritten by another configuration. A .meta.txt next to it carries the protocol labels, fs and its source, the
quality decision and the kept/dropped channels of each subject. Subjects run in parallel with `--n-jobs` (joblib).
"""

import argparse
import contextlib
import io
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


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

from src.features.ssvep.fbcca_extraction import TARGET_FREQS, extract_fbcca_features  # noqa: E402
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS, filter_subbands  # noqa: E402
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION  # noqa: E402
from src.io.subject_data import CLASS_CODES, QUALITY_MODES, discover_subjects, is_built, load_subject  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  add_protocol_args, channel_summary, legacy_header_lines, load_config, output_dir, print_trial_report,
  protocol_labels)
from src.models.classical.legacy_eval import (  # noqa: E402
  SEED, FeatureSpace, accuracies, oof_space, smooth_scores, space_width, splits_for)
from src.models.classical.rest_metrics import REST_LABEL, confusion_counts, rest_metrics  # noqa: E402
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials  # noqa: E402
from src.preprocessing.window_quality import quality_params_from_config  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
MODEL = "Shrinkage-LDA lsqr"
SPACE = "FBCSP + FBCCA (in-fold)"
BASE_COLUMNS = ["Subject", "Channels Kept", "Channels Dropped", "Clean Windows", "Rejected Windows"]
BUILT_COLUMNS = ["Bank", "CSP Bands"]
ACC_COLUMNS = ["1.0s Acc (%)", "2.0s Smoothed (%)"]
SD_COLUMNS = ["1.0s SD", "2.0s SD", "CV repeats"]
BANKS = ("base", "harm", "harm+mid")
REST_COUNT_COLUMN = "Rest Windows"
EXTRA_BANKS = {"base": (), "harm": ("harmonic",), "harm+mid": ("harmonic", "intermediate")}
# 6-class metric columns in the order of 02_REQUIREMENTS section 6: (column, metric, decision time index 0/1 = 1.0 s / 2.0 s)
REST_COLUMNS = [("1.0s BalAcc (%)", "BalAcc", 0), ("2.0s BalAcc (%)", "BalAcc", 1),
                ("1.0s FalseAct (%)", "FalseAct", 0), ("2.0s FalseAct (%)", "FalseAct", 1),
                ("1.0s Missed (%)", "Missed", 0), ("2.0s Missed (%)", "Missed", 1),
                ("2.0s StimCorrect (%)", "StimCorrect", 1)]
REST_SD_COLUMNS = [c.replace(" (%)", " SD") for c, _, _ in REST_COLUMNS]
COLUMNS = BASE_COLUMNS + ACC_COLUMNS   # the legacy layout (P07-P11)
CSP_BANDS_TEXT = " ".join(f"{lo}-{hi}" for lo, hi in DEFAULT_SUBBANDS)


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="subject folders (default: discover S<digits> folders)")
  p.add_argument("--data-root", type=Path, default=None,
                 help="folder with <S>/ windows, legacy or built (default: <root>/ + paths.data_processed_dir, "
                      "i.e. data/processed, the legacy folders)")
  p.add_argument("--n-jobs", type=int, default=1, help="parallel subjects (joblib; default 1, -1 = all cores)")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1)")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--out-suffix", default=None,
                 help="writes n_subjects_benchmark_<suffix>.csv, used verbatim (default: derived from the run if it "
                      "is not the legacy default, else none)")
  p.add_argument("--fs", type=float, default=None,
                 help="feature sampling rate override (default: metadata fs on built roots, 250 on legacy roots, "
                      "PF-04)")
  p.add_argument("--allow-fs-override", action="store_true",
                 help="allow --fs on a built root (documented diagnostic only; the metadata fs is the rule)")
  p.add_argument("--bank", choices=BANKS, default="base",
                 help="CSP bands: base = the 5 saved fbcsp bands; harm = + harmonic bank; harm+mid = + harmonic and "
                      "intermediate banks (built roots with those banks, P17)")
  p.add_argument("--classes", type=int, choices=(5, 6), default=5,
                 help="5 = the stimuli; 6 = + the fixation cross 201 as rest class (built roots only, P17)")
  p.add_argument("--quality", choices=QUALITY_MODES, default="shared",
                 help="quality decision (R5): shared / shared-no-guard (built roots) / per-script (P07 two-tier "
                      "gate; the only one on legacy roots, where every value means it)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  p.add_argument("--cv-repeats", type=int, default=1,
                 help="repeat the CV with seeds seed+r (r = 0..N-1) and report mean and SD columns (default 1)")
  add_protocol_args(p)
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def quality_arguments(cfg: dict) -> tuple:
  """`(thresholds, channel_fail_fraction)` from the config `quality:` block, all four limits explicit (R5)."""
  q = quality_params_from_config(cfg)
  return ({k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}, q["channel_fail_fraction"])


def bank_bands_text(d: dict, bank: str = "base") -> str:
  """CSP band list ("lo-hi" in the order of the FBCSP columns) of a built subject for `--bank`: the 5 `fbcsp` bands, then the
  saved extra banks in the order of the metadata (R6); the legacy default list for legacy folders."""
  if not d["built"]:
    return CSP_BANDS_TEXT
  names = ["fbcsp"] + list(EXTRA_BANKS[bank])
  return " ".join(f"{b['low']:g}-{b['high']:g}" for n in names for b in d["meta"]["bands"][n])


def feature_blocks(d: dict, m: int, bank: str = "base") -> tuple:
  """`(FeatureSpace, sub-bands (n, B, C', T))` of a loaded subject: FBCCA scores (55-column flagship, with the
  in-fold CSP of `m`). Built folders use the saved bands (no filtering here, R3); legacy folders filter per window
  at `d["fs"]` (legacy PF-14). `bank` (built folders; load `d` with `bands=` the extra banks): the extra narrow bands are
  concatenated after the `fbcsp` bands along the band axis; their count must equal the metadata's."""
  X, y, q, names, fs = d["X"], d["y"], d["quality"], d["channel_names"], d["fs"]
  fb_bands = d["bands"].get("fbcca") if d["built"] else None
  cs_bands = d["bands"].get("fbcsp") if d["built"] else None
  clean = {"valid_mask": np.ones(len(y), dtype=int), "channels_kept": list(names)}   # rows/channels already selected by the loader
  fbcca, _, _, _ = extract_fbcca_features(X, y, names, fs, TARGET_FREQS, subband_windows=fb_bands, quality=clean)
  sub = cs_bands if cs_bands is not None else filter_subbands(X, fs, DEFAULT_SUBBANDS)
  if bank != "base":
    if not d["built"]:
      raise ValueError(f"--bank {bank} needs a built folder (legacy folders have no saved narrow banks)")
    for b in EXTRA_BANKS[bank]:
      extra = d["bands"][b]
      if extra.shape[1] != len(d["meta"]["bands"][b]):
        raise RuntimeError(f"{b}: {extra.shape[1]} bands saved, metadata lists {len(d['meta']['bands'][b])}")
      sub = np.concatenate([sub, extra], axis=1)
  if d["built"]:
    n_meta = len(d["meta"]["bands"]["fbcsp"]) + sum(len(d["meta"]["bands"][b]) for b in EXTRA_BANKS[bank])
    if sub.shape[1] != n_meta:
      raise RuntimeError(f"{sub.shape[1]} CSP bands loaded, metadata lists {n_meta}")
  return FeatureSpace(SPACE, [fbcca], fbcsp_m=m), sub


def make_model(seed: int, n_classes: int = 5):
  """The flagship classifier. With 6 classes the LDA priors are uniform (1/6) instead of the class frequencies (the rest
  class has twice the windows of a stimulus class)."""
  model = get_sklearn_model_suite(seed)[MODEL]
  if n_classes == 6:
    model.set_params(priors=np.full(6, 1.0 / 6.0))
  return model


def run_cv(space: FeatureSpace, sub: np.ndarray, d: dict, cv: str, smoothing: str, seed: int, repeats: int,
           n_classes: int = 5, keep: Optional[list] = None) -> list:
  """Per repeat r (seed+r) `(1.0 s acc, 2.0 s smoothed acc)` in [0, 1], or raises RuntimeError with the model error.
  `keep` (a list) receives per repeat `(pred 1.0 s, pred 2.0 s)`, the out-of-fold predictions, for the 6-class metrics."""
  groups = d.get("cv_groups", d["trial_ids"])   # R1 group key; legacy folders: the reconstructed ids
  out = []
  for r in range(repeats):
    splits = splits_for(cv, d["y"], groups, seed + r)
    if cv == "grouped":
      assert_no_shared_trials(splits, groups)   # R1 runtime guard: no trial id on both sides of any fold
    res, errs = oof_space(space, sub, d["y"], {MODEL: make_model(seed + r, n_classes)}, seed + r, splits)
    if errs:
      raise RuntimeError(errs[MODEL])
    out.append(accuracies(d["y"], res[MODEL]["pred"], res[MODEL]["scores"], d["trial_ids"], smoothing))
    if keep is not None:
      classes = np.unique(d["y"])
      sm = classes[np.argmax(smooth_scores(res[MODEL]["scores"], d["trial_ids"], smoothing), axis=1)]
      keep.append((res[MODEL]["pred"], sm))
  return out


def print_channel_report(d: dict) -> None:
  """Per-channel report of the per-script gate (as P07 printed it); shared decisions list kept/dropped only (R9)."""
  stats, q = d["quality"].get("channel_stats"), d["quality"]
  print(f"[quality] {q['source']}")
  for n in d["channels_all"]:
    s = (stats or {}).get(n)
    if s is None:
      print(f"  {n}{'  -> DROPPED' if n in d['channels_dropped'] else ''}")
      continue
    print(f"  {n}: fail {s['fail_fraction']:.1%} ({s['n_failed']}/{d['n_selected']}), mean Vpp {s['mean_vpp']:.2f} uV, "
          f"mean std {s['mean_std']:.2f} uV{'  -> DROPPED' if n in d['channels_dropped'] else ''}")


def header_lines(d: dict, seed: int, cv: str, smoothing: str, thresholds: dict, fail_fraction: float,
                 repeats: int, bank: str = "base", classes: int = 5) -> list:
  """Protocol lines of a run (console and .meta.txt)."""
  cvl, sml = protocol_labels(cv, smoothing)
  if not d["built"]:
    lines = legacy_header_lines(d["fs"], thresholds, seed, cvl, sml, None, fail_fraction)
    lines[2] = (f"features: legacy windows, per-window sub-band filtering (R3/PF-14), fs={d['fs']:g} Hz "
                f"({d['fs_source']}{', PF-04' if d['fs_source'] == 'legacy-assumed' else ''}); scaler and CSP fitted "
                f"inside each training fold (R2/PF-11)")
  else:
    q = d["quality"]
    lines = [f"cv={cvl}; seed={seed}", f"smoothing: {sml if smoothing == 'mod5' else 'trial-reset 2-window average over true trial ids ordered by (trial, offset) (R8)'}",
             f"features: {d['filter_mode']} build, FBCCA from the saved fbcca bands, CSP on the saved fbcsp bands "
             f"({bank_bands_text(d, bank)}); fs={d['fs']:g} Hz ({d['fs_source']}); scaler and CSP fitted inside each training fold "
             f"(R2/PF-11)",
             f"quality: {q['mode']} ({q['source']}); guard_sec {q['guard_sec']}; params {q['params']}"]
  lines.append(f"cv repeats {repeats}: seeds {seed}..{seed + repeats - 1}")
  if bank != "base":
    lines.append(f"bank {bank}: the fbcsp bands + {' + '.join(EXTRA_BANKS[bank])} (CSP m per band); FBCCA unchanged")
  if classes == 6:
    lines.append("classes 6: 101-105 + rest 201 (202 excluded, PF-13); uniform LDA priors 1/6; CV groups = true trial ids "
                 "(R1); 2.0 s smoothing resets at each trial id (R8)")
  return lines


def evaluate_subject(root: Path, subject: str, m: int = 1, fs: Optional[float] = None, seed: int = SEED,
                     cv: str = "grouped", smoothing: Optional[str] = None, quality: str = "shared",
                     repeats: int = 1, thresholds: Optional[dict] = None,
                     fail_fraction: float = CHANNEL_FAIL_FRACTION, bank: str = "base", classes: int = 5,
                     allow_fs_override: bool = False) -> dict:
  """One subject: load once, flagship out-of-fold. Returns `{"subject", "row" or None, "log", "kept", "dropped",
  "header", "approximate", "built", "seed0"}`; a subject that cannot be evaluated has `row = None` and its reason
  in `log`. Console text is collected in `log` (printed in order by the caller, so parallel jobs do not interleave).
  `thresholds` (the four limits) are required, never defaulted (R5, C-2). ValueError: `fs` on a built root without
  `allow_fs_override`; `bank` other than base or `classes=6` on a legacy root; unknown bank/classes."""
  if thresholds is None:
    raise ValueError("thresholds are required (R5): pass the four limits of the config quality: block")
  thresholds = dict(thresholds)
  if bank not in BANKS or classes not in (5, 6):
    raise ValueError(f"bank must be one of {BANKS} and classes 5 or 6, got {bank!r}, {classes!r}")
  built = is_built(Path(root) / subject)
  if built and fs is not None and not allow_fs_override:
    raise ValueError(f"--fs {fs:g} on a built root ({Path(root).name}/{subject}): the sampling rate comes from the "
                     "metadata (P16); --allow-fs-override runs it as a documented diagnostic")
  if not built and (bank != "base" or classes == 6):
    raise ValueError(f"--bank {bank} / --classes {classes} need a built folder (legacy folders have no narrow banks and "
                     f"no true trial ids): {Path(root).name}/{subject}")
  buf = io.StringIO()
  out = {"subject": subject, "row": None, "kept": [], "dropped": [], "header": None, "approximate": False,
         "built": built, "seed0": None, "filter_mode": None, "confusion": None}
  with contextlib.redirect_stdout(buf):
    sub_dir = Path(root) / subject
    try:
      d = load_subject(sub_dir, CLASS_CODES + ((REST_LABEL,) if classes == 6 else ()), quality,
                       bands=("fbcca", "fbcsp") + EXTRA_BANKS[bank] if built else (), fs_override=fs,
                       thresholds=thresholds, channel_fail_fraction=fail_fraction)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      out["log"] = buf.getvalue()
      return out
    rule = smoothing or d["smoothing"]
    out["header"] = header_lines(d, seed, cv, rule, thresholds, fail_fraction, repeats, bank, classes)
    out["approximate"], out["built"], out["filter_mode"] = d["trial_ids_approximate"], built, d["filter_mode"]
    print_channel_report(d)
    if not built:
      print(f"Trial blocks of {subject} (stimulus windows before the quality gate):")
      from src.preprocessing.dataset.cv_utils import format_block_report
      print(format_block_report(d["trial_block_report"]))
    try:
      if classes == 6:
        assert 202 not in d["y"] and np.array_equal(d["cv_groups"], d["trial_ids"])   # PF-13: groups are the true ids
      space, sub = feature_blocks(d, m, bank)
      kept_preds = [] if classes == 6 else None
      accs = run_cv(space, sub, d, cv, rule, seed, repeats, classes, kept_preds)
    except RuntimeError as exc:
      print(f"[x] {subject}: {MODEL} failed: {exc}")
      out["log"] = buf.getvalue()
      return out
    a = np.asarray(accs) * 100
    out["seed0"] = (float(a[0, 0]), float(a[0, 1]))
    out["kept"], out["dropped"] = d["channel_names"], d["channels_dropped"]
    row = {"Subject": subject, "Channels Kept": len(d["channel_names"]),
           "Channels Dropped": " ".join(d["channels_dropped"]) or "none",
           "Clean Windows": len(d["y"]), "Rejected Windows": d["n_rejected"]}
    if built:
      row.update({"Bank": "fbcca" if bank == "base" else "fbcca+" + bank, "CSP Bands": bank_bands_text(d, bank)})
    row.update({"1.0s Acc (%)": round(float(a[:, 0].mean()), 2), "2.0s Smoothed (%)": round(float(a[:, 1].mean()), 2)})
    if repeats > 1:
      row.update({"1.0s SD": round(float(a[:, 0].std(ddof=1)), 2), "2.0s SD": round(float(a[:, 1].std(ddof=1)), 2),
                  "CV repeats": repeats})
    if classes == 6:
      cls = [int(c) for c in np.unique(d["y"])]
      row[REST_COUNT_COLUMN] = int((d["y"] == REST_LABEL).sum())
      m_all = np.array([[rest_metrics(d["y"], kp[t])[name] for _, name, t in REST_COLUMNS] for kp in kept_preds])
      for k, (col, _, _) in enumerate(REST_COLUMNS):
        row[col] = round(float(m_all[:, k].mean()), 2)
      if repeats > 1:
        for k, col in enumerate(REST_SD_COLUMNS):
          row[col] = round(float(m_all[:, k].std(ddof=1)), 2)
      out["confusion"] = (cls, sum(confusion_counts(d["y"], kp[1], cls) for kp in kept_preds))
    out["row"] = row
    print(f"  {channel_summary({'channels_kept': d['channel_names'], 'channels_dropped': d['channels_dropped']})}")
    print(f"[+] {subject}: {d['n_selected']} stimulus, {len(d['y'])} clean, {d['n_rejected']} rejected; "
          f"p={space_width(space, sub.shape[1], classes)}; fs {d['fs']:g} ({d['fs_source']}); 1.0 s {row['1.0s Acc (%)']:.2f}%  "
          f"2.0 s smoothed {row['2.0s Smoothed (%)']:.2f}%"
          + (f"; seed {seed} alone {out['seed0'][0]:.2f}% / {out['seed0'][1]:.2f}%" if repeats > 1 else ""))
  out["log"] = buf.getvalue()
  return out


def with_mean_row(rows: list) -> pd.DataFrame:
  """Subject rows + `Mean` row (mean of the CSV's rounded accuracy and SD values, 2 decimals; other columns blank)."""
  cols = list(rows[0].keys())
  df = pd.DataFrame(rows, columns=cols)
  mean = {c: "" for c in cols}
  mean["Subject"] = "Mean"
  for c in ACC_COLUMNS + [c for c in SD_COLUMNS[:2] + [r[0] for r in REST_COLUMNS] + REST_SD_COLUMNS if c in cols]:
    mean[c] = round(float(df[c].mean()), 2)
  if "CV repeats" in cols:
    mean["CV repeats"] = rows[0]["CV repeats"]
  return pd.concat([df, pd.DataFrame([mean], columns=cols)], ignore_index=True)


def confusion_frame(results: list, repeats: int) -> pd.DataFrame:
  """2.0 s confusion matrices of the evaluated subjects (rows = true class, columns = predicted class), each summed over
  the CV repeats of one subject (every window is predicted once per repeat), plus a `Sum` block over the subjects."""
  frames, total = [], None
  for r in results:
    cls, cm = r["confusion"]
    total = cm if total is None else total + cm
    frames.append((r["subject"], cls, cm))
  frames.append(("Sum", frames[0][1], total))
  rows = [{"Subject": s, "True": t, **{str(c): int(v) for c, v in zip(cls, line)}, "CV repeats": repeats}
          for s, cls, cm in frames for t, line in zip(cls, cm)]
  return pd.DataFrame(rows)


def derived_suffix(built: bool, filter_mode: Optional[str], quality: str, fs: Optional[float], repeats: int,
                   bank: str = "base", classes: int = 5) -> str:
  """Suffix of a run that is not the legacy default (see the module docstring); "" for the default."""
  parts = []
  if built and filter_mode:
    parts.append(filter_mode)
  if quality != "shared":
    parts.append(quality.replace("-", ""))
  if fs is not None:
    parts.append(f"fs{fs:g}")
  if bank != "base":
    parts.append(bank.replace("+", ""))
  if classes == 6:
    parts.append("6class")
  if repeats > 1:
    parts.append(f"rep{repeats}")
  return "_".join(parts)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  explicit = any(a == "--smoothing" or a.startswith("--smoothing=") for a in (sys.argv[1:] if argv is None else argv))
  if not explicit:
    args.smoothing = None   # the rule of the folder: trial (built roots) / mod5 (legacy roots, the parser default)
  if args.cv_repeats < 1:
    print("[x] --cv-repeats must be >= 1")
    return 1
  cfg = load_config(args.config)
  thresholds, fail_fraction = quality_arguments(cfg)
  processed = Path(args.data_root or ROOT / cfg["paths"]["data_processed_dir"])
  reports = Path(args.reports_dir or ROOT / "reports")
  if not processed.is_dir():
    print(f"[x] Data root not found: {processed}")
    return 1
  subjects = args.subjects or discover_subjects(processed)
  if not subjects:
    print(f"[-] No subject folders with windows in {_rel(processed)}")
    return 1
  t0 = time.time()
  print(f"Data source: windows of {_rel(processed)}/<S>/ via load_subject (OO session), stimulus windows only; "
        f"quality {args.quality}; subjects {', '.join(subjects)}; n_jobs {args.n_jobs}")
  kw = dict(m=args.m, fs=args.fs, seed=args.seed, cv=args.cv, smoothing=args.smoothing, quality=args.quality,
            repeats=args.cv_repeats, thresholds=thresholds, fail_fraction=fail_fraction, bank=args.bank,
            classes=args.classes, allow_fs_override=args.allow_fs_override)
  try:
    if args.n_jobs == 1:
      results = [evaluate_subject(processed, s, **kw) for s in subjects]
    else:
      from joblib import Parallel, delayed
      results = Parallel(n_jobs=args.n_jobs)(delayed(evaluate_subject)(processed, s, **kw) for s in subjects)
  except ValueError as exc:   # unusable option for this root (--fs / --bank / --classes on legacy or built folders)
    print(f"[x] {exc}")
    return 1
  rows, header, chans, approx = [], None, [], []
  for r in results:
    if header is None and r["header"]:
      header = r["header"]
      print("\n".join(header))
    print(r["log"], end="")
    if r["row"] is not None:
      rows.append(r["row"])
      if r["approximate"]:
        approx.append(r["subject"])
      chans.append(f"{r['subject']}: kept {' '.join(r['kept'])}; dropped {' '.join(r['dropped']) or 'none'}")
  if not rows:
    print("[-] No subject evaluated")
    return 1
  built = any(r["built"] for r in results if r["row"] is not None)
  if built and not all(r["built"] for r in results if r["row"] is not None):
    print("[x] data root mixes built and legacy subject folders")
    return 1
  df = with_mean_row(rows)
  suffix = args.out_suffix
  if suffix is None:
    fmode = next((r["filter_mode"] for r in results if r["row"] is not None), None)
    suffix = derived_suffix(built, fmode, args.quality, args.fs, args.cv_repeats, args.bank, args.classes)
    if suffix:
      print(f"[i] no --out-suffix: derived suffix '{suffix}' (not the legacy default configuration)")
  name = "n_subjects_benchmark" + (f"_{suffix}" if suffix else "")
  csv = output_dir(reports, args.cv) / f"{name}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  rule = args.smoothing or ("trial" if built else "mod5")
  meta = (header or []) + [f"cv={args.cv}, smoothing={rule}; trial_ids_approximate subjects: "
                           f"{' '.join(approx) or 'none'}", f"model: {SPACE} -> {MODEL}",
                           f"data source: {'built' if built else 'legacy'} windows, {_rel(processed)}/<S>/; "
                           f"quality {args.quality}{' (legacy folders: per-script)' if not built else ''}; fs {'override ' + format(args.fs, 'g') if args.fs else 'default of the folder'}"] + chans
  csv.with_suffix(".meta.txt").write_text("\n".join(meta) + "\n")
  if args.classes == 6:
    conf = confusion_frame([r for r in results if r["row"] is not None], args.cv_repeats)
    conf.to_csv(csv.with_name(csv.stem + "_confusion.csv"), index=False)
  print("\n" + df.to_string(index=False))
  mean = df.iloc[-1]
  print(f"\nCohort: {len(rows)} subjects, mean 1.0 s {mean['1.0s Acc (%)']:.2f}%, 2.0 s smoothed "
        f"{mean['2.0s Smoothed (%)']:.2f}% ({'legacy leaky CV, not comparable with R-6' if args.cv == 'legacy' else 'trial-grouped CV, R1'}; "
        f"smoothing {rule}); runtime {time.time() - t0:.0f} s")
  if args.classes == 6:
    print(f"6 classes: mean 2.0 s BalAcc {mean['2.0s BalAcc (%)']:.2f}%, FalseAct {mean['2.0s FalseAct (%)']:.2f}%, "
          f"Missed {mean['2.0s Missed (%)']:.2f}%, StimCorrect {mean['2.0s StimCorrect (%)']:.2f}%")
  print(f"Saved: {_rel(csv)}")
  if args.classes == 6:
    print(f"Saved: {_rel(csv.with_name(csv.stem + '_confusion.csv'))}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
