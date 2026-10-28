"""Cohort benchmark of the flagship on legacy or built windows (P07.6 legacy Era A; ported to `load_subject` in P16.7).

Data source: `<data-root>/<S>/` read only through `src.io.subject_data.load_subject` (OO session). Default root
`data/processed` = legacy folders (7 channels, fs 250 assumed, trial ids reconstructed, per-script two-tier gate,
`i % 5` smoothing; reproduces the P11 leak-free R-6 exactly with the defaults). A root of folders written by
`scripts/build_windows.py` (`data/processed_per_window`, `data/processed_continuous`, 8 channels, fs from the
metadata, true trial ids, shared quality decision) is detected per subject: FBCCA reads the saved `fbcca`
bands and the CSP the saved `fbcsp` bands (nothing is refiltered; continuous = R3, per_window = legacy PF-14), the
2.0 s smoothing resets at each true trial id of rows ordered by (trial, offset) (R8), and the CV groups are the
loader's `cv_groups` (R1). Stimulus windows only.

Per subject the flagship: FBCSP m = 1 (CSP fitted in-fold, R2/PF-11) + FBCCA (55 columns for 5 CSP bands x 5 classes
x 2 + 5 scores) -> StandardScaler -> Shrinkage-LDA (lsqr, auto), behind ONE quality decision (PF-10).
`--quality shared|shared-no-guard|per-script` picks it (R5; on legacy folders every value is the per-script
two-tier gate: vpp 5-120 uV, std 1-35 uV, channel dropped if failing in > 50 % of the windows).
`--fs` overrides the feature sampling rate (built default: metadata; legacy default: 250, PF-04).

CV protocol (P11): `--cv grouped` (default) = StratifiedGroupKFold(5, shuffle, seed) over trial ids (R1);
`--cv legacy` = the P05-P10 leaky window-level StratifiedKFold (output under <reports-dir>/legacy_leaky/, not
comparable). `--smoothing` defaults to `trial` on built roots and `mod5` on legacy roots (R8 era clause).
`--cv-repeats N` repeats the split with seeds `--seed + r` (42 + r) and reports the mean and the sample SD (ddof 1)
of the N accuracies; the seed-42 values are printed too.

Output: <reports-dir>[/legacy_leaky]/n_subjects_benchmark[_suffix].csv with the columns of 02_REQUIREMENTS section 6
(Subject, Channels Kept, Channels Dropped, Clean Windows, Rejected Windows, [Bank, CSP Bands,] 1.0s Acc (%),
2.0s Smoothed (%) [, 1.0s SD, 2.0s SD, CV repeats]); `Bank, CSP Bands` appear on built roots; "Channels Kept" is the count,
"Channels Dropped" the names ("none" if empty); a Mean row follows. Suffix rule: `--out-suffix` is used verbatim;
without it a run that is not the legacy default (built root, `--quality` other than shared, `--fs` override,
`--cv-repeats` > 1) gets a derived suffix (`<filter_mode>`, `<quality>`, `fs<fs>`, `rep<N>`), so a default file is never
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
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, GATE_THRESHOLDS  # noqa: E402
from src.io.subject_data import CLASS_CODES, QUALITY_MODES, discover_subjects, is_built, load_subject  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  add_protocol_args, channel_summary, legacy_header_lines, load_config, output_dir, print_trial_report,
  protocol_labels)
from src.models.classical.legacy_eval import (  # noqa: E402
  SEED, FeatureSpace, accuracies, oof_space, space_width, splits_for)
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
  p.add_argument("--quality", choices=QUALITY_MODES, default="shared",
                 help="quality decision (R5): shared / shared-no-guard (built roots) / per-script (P07 two-tier "
                      "gate; the only one on legacy roots, where every value means it)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  p.add_argument("--cv-repeats", type=int, default=1,
                 help="repeat the CV with seeds seed+r (r = 0..N-1) and report mean and SD columns (default 1)")
  add_protocol_args(p)
  p.set_defaults(smoothing=None)   # None = the rule of the folder: trial (built) / mod5 (legacy)
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


def feature_blocks(d: dict, m: int) -> tuple:
  """`(FeatureSpace, sub-bands (n, B, C', T))` of a loaded subject: FBCCA scores (55-column flagship, with the
  in-fold CSP of `m`). Built folders use the saved bands (no filtering here, R3); legacy folders filter per window
  at `d["fs"]` (legacy PF-14)."""
  X, y, q, names, fs = d["X"], d["y"], d["quality"], d["channel_names"], d["fs"]
  fb_bands = d["bands"].get("fbcca") if d["built"] else None
  cs_bands = d["bands"].get("fbcsp") if d["built"] else None
  clean = {"valid_mask": np.ones(len(y), dtype=int), "channels_kept": list(names)}   # rows/channels already selected by the loader
  fbcca, _, _, _ = extract_fbcca_features(X, y, names, fs, TARGET_FREQS, subband_windows=fb_bands, quality=clean)
  sub = cs_bands if cs_bands is not None else filter_subbands(X, fs, DEFAULT_SUBBANDS)
  return FeatureSpace(SPACE, [fbcca], fbcsp_m=m), sub


def run_cv(space: FeatureSpace, sub: np.ndarray, d: dict, cv: str, smoothing: str, seed: int, repeats: int) -> list:
  """Per repeat r (seed+r) `(1.0 s acc, 2.0 s smoothed acc)` in [0, 1], or raises RuntimeError with the model error."""
  groups = d.get("cv_groups", d["trial_ids"])   # R1 group key; legacy folders: the reconstructed ids
  out = []
  for r in range(repeats):
    splits = splits_for(cv, d["y"], groups, seed + r)
    if cv == "grouped":
      assert_no_shared_trials(splits, groups)   # R1 runtime guard: no trial id on both sides of any fold
    res, errs = oof_space(space, sub, d["y"], {MODEL: get_sklearn_model_suite(seed + r)[MODEL]}, seed + r, splits)
    if errs:
      raise RuntimeError(errs[MODEL])
    out.append(accuracies(d["y"], res[MODEL]["pred"], res[MODEL]["scores"], d["trial_ids"], smoothing))
  return out


def header_lines(d: dict, seed: int, cv: str, smoothing: str, thresholds: dict, fail_fraction: float,
                 repeats: int) -> list:
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
             f"({CSP_BANDS_TEXT}); fs={d['fs']:g} Hz ({d['fs_source']}); scaler and CSP fitted inside each training fold "
             f"(R2/PF-11)",
             f"quality: {q['mode']} ({q['source']}); guard_sec {q['guard_sec']}; params {q['params']}"]
  lines.append(f"cv repeats {repeats}: seeds {seed}..{seed + repeats - 1}")
  return lines


def evaluate_subject(root: Path, subject: str, m: int = 1, fs: Optional[float] = None, seed: int = SEED,
                     cv: str = "grouped", smoothing: Optional[str] = None, quality: str = "shared",
                     repeats: int = 1, thresholds: Optional[dict] = None,
                     fail_fraction: float = CHANNEL_FAIL_FRACTION) -> dict:
  """One subject: load once, flagship out-of-fold. Returns `{"subject", "row" or None, "log", "kept", "dropped",
  "header", "approximate", "built", "seed0"}`; a subject that cannot be evaluated has `row = None` and its reason
  in `log`. Console text is collected in `log` (printed in order by the caller, so parallel jobs do not interleave)."""
  thresholds = dict(GATE_THRESHOLDS if thresholds is None else thresholds)
  buf = io.StringIO()
  out = {"subject": subject, "row": None, "kept": [], "dropped": [], "header": None, "approximate": False,
         "built": False, "seed0": None, "filter_mode": None}
  with contextlib.redirect_stdout(buf):
    sub_dir = Path(root) / subject
    try:
      built = is_built(sub_dir)
      d = load_subject(sub_dir, CLASS_CODES, quality, bands=("fbcca", "fbcsp") if built else (), fs_override=fs,
                       thresholds=thresholds, channel_fail_fraction=fail_fraction)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      out["log"] = buf.getvalue()
      return out
    rule = smoothing or d["smoothing"]
    out["header"] = header_lines(d, seed, cv, rule, thresholds, fail_fraction, repeats)
    out["approximate"], out["built"], out["filter_mode"] = d["trial_ids_approximate"], built, d["filter_mode"]
    if not built:
      print(f"Trial blocks of {subject} (stimulus windows before the quality gate):")
      from src.preprocessing.dataset.cv_utils import format_block_report
      print(format_block_report(d["trial_block_report"]))
    try:
      space, sub = feature_blocks(d, m)
      accs = run_cv(space, sub, d, cv, rule, seed, repeats)
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
      row.update({"Bank": "fbcca", "CSP Bands": CSP_BANDS_TEXT})
    row.update({"1.0s Acc (%)": round(float(a[:, 0].mean()), 2), "2.0s Smoothed (%)": round(float(a[:, 1].mean()), 2)})
    if repeats > 1:
      row.update({"1.0s SD": round(float(a[:, 0].std(ddof=1)), 2), "2.0s SD": round(float(a[:, 1].std(ddof=1)), 2),
                  "CV repeats": repeats})
    out["row"] = row
    print(f"  {channel_summary({'channels_kept': d['channel_names'], 'channels_dropped': d['channels_dropped']})}")
    print(f"[+] {subject}: {d['n_selected']} stimulus, {len(d['y'])} clean, {d['n_rejected']} rejected; "
          f"p={space_width(space, sub.shape[1])}; fs {d['fs']:g} ({d['fs_source']}); 1.0 s {row['1.0s Acc (%)']:.2f}%  "
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
  for c in ACC_COLUMNS + [c for c in SD_COLUMNS[:2] if c in cols]:
    mean[c] = round(float(df[c].mean()), 2)
  if "CV repeats" in cols:
    mean["CV repeats"] = rows[0]["CV repeats"]
  return pd.concat([df, pd.DataFrame([mean], columns=cols)], ignore_index=True)


def derived_suffix(built: bool, filter_mode: Optional[str], quality: str, fs: Optional[float], repeats: int) -> str:
  """Suffix of a run that is not the legacy default (see the module docstring); "" for the default."""
  parts = []
  if built and filter_mode:
    parts.append(filter_mode)
  if quality != "shared":
    parts.append(quality.replace("-", ""))
  if fs is not None:
    parts.append(f"fs{fs:g}")
  if repeats > 1:
    parts.append(f"rep{repeats}")
  return "_".join(parts)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
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
            repeats=args.cv_repeats, thresholds=thresholds, fail_fraction=fail_fraction)
  if args.n_jobs == 1:
    results = [evaluate_subject(processed, s, **kw) for s in subjects]
  else:
    from joblib import Parallel, delayed
    results = Parallel(n_jobs=args.n_jobs)(delayed(evaluate_subject)(processed, s, **kw) for s in subjects)
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
    suffix = derived_suffix(built, fmode, args.quality, args.fs, args.cv_repeats)
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
  print("\n" + df.to_string(index=False))
  mean = df.iloc[-1]
  print(f"\nCohort: {len(rows)} subjects, mean 1.0 s {mean['1.0s Acc (%)']:.2f}%, 2.0 s smoothed "
        f"{mean['2.0s Smoothed (%)']:.2f}% ({'legacy leaky CV, not comparable with R-6' if args.cv == 'legacy' else 'trial-grouped CV, R1'}; "
        f"smoothing {rule}); runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
