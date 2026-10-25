"""Feature-space x model benchmark on one subject (P05.5, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels, 256-sample
windows), stimulus windows only (101-105). One quality decision (two-tier gate from P07, limits
written out: vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the windows; R5
per-script gate) feeds every feature block (PF-10).

Six feature spaces (p printed at fs 250): continuous PSD 5-35 Hz (210), harmonic PSD on
PO8, O1, Oz, O2 (32 = 4 channels x 8 bins), FBCCA (5), harmonic PSD + FBCCA (37), FBCSP
in-fold (50 for m = 1), FBCSP + FBCCA (55); each x the sklearn suite without QDA (PF-12, QDA
runs in scripts.evaluation.test_sklearn_models), plus the zero-training FBCCA argmax baseline.
Every model is a Pipeline(StandardScaler, model) and the CSP is fitted on the training fold
only (R2/PF-11).

Legacy behaviours (labelled, fixed in later phases):
- R1 / PF-01: StratifiedKFold(5, shuffle, 42) over windows (leaky; not comparable with R-6).
- R8 / PF-02: "2.0 s smoothed" = legacy i%5 trial smoothing of the out-of-fold scores (2-window
  average, reset at i % 5 == 0 of the clean array).
- R3 / PF-14 and PF-04: per-window sub-band filtering, fs 250 on 256 Hz data.

Output: <reports-dir>/feature_space_benchmark_<S>.csv (Subject, Feature space, p, Model,
1.0s Acc (%), 2.0s Smoothed (%), Clean Windows, Rejected) and a .meta.txt with the protocol labels.
"""

import argparse
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

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import channel_summary  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  DEFAULT_SUBJECT, legacy_header_lines, load_config, prepare_subject)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  CV_LABEL, SEED, SMOOTH_LABEL, accuracies, fbcca_argmax_baseline, oof_space, smooth_reported, space_width)
from src.models.classical.sklearn_models import QDA_NAME, get_sklearn_model_suite  # noqa: E402
from src.preprocessing.dataset.legacy_windows import CLASS_CODES  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
COLUMNS = ["Subject", "Feature space", "p", "Model", "1.0s Acc (%)", "2.0s Smoothed (%)",
           "Clean Windows", "Rejected"]
ARGMAX_SPACE = "FBCCA argmax (zero-training)"


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default: {DEFAULT_SUBJECT})")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None, help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle and SGD seed (default {SEED})")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def run_benchmark(blocks: dict, subject: str, m: int = 1, seed: int = SEED, verbose: bool = True) -> tuple:
  """Rows of the benchmark table and the model failures `[(space, model, error)]`."""
  y = blocks["y"]
  models = {k: v for k, v in get_sklearn_model_suite(seed).items() if k != QDA_NAME}   # PF-12
  rows, failures = [], []
  common = {"Subject": subject, "Clean Windows": blocks["n_clean"], "Rejected": blocks["n_rejected"]}
  for space in benchmark_spaces(blocks, m):
    t0 = time.time()
    res, errs = oof_space(space, blocks["subbands"], y, models, seed)
    p = space_width(space, n_bands=blocks["subbands"].shape[1], n_classes=len(CLASS_CODES))
    for name, r in res.items():
      a1, a2 = accuracies(y, r["pred"], r["scores"])
      rows.append({**common, "Feature space": space.name, "p": p, "Model": name,
                   "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)})
      if verbose:
        print(f"  {space.name:<26} p={p:<3} {name:<20} 1.0 s {100 * a1:6.2f}%  2.0 s smoothed {100 * a2:6.2f}%")
    for name, e in errs.items():
      failures.append((space.name, name, e))
      print(f"  [-] {space.name} / {name} failed: {e}")
    if verbose:
      print(f"  ({space.name}: {time.time() - t0:.1f} s)")
  pred, sc = fbcca_argmax_baseline(blocks["fbcca"], y, CLASS_CODES)
  classes = sorted(set(int(v) for v in y))
  sm = np.asarray(classes)[np.argmax(smooth_reported(sc), axis=1)]
  a1, a2 = float(np.mean(pred == y)), float(np.mean(sm == y))
  rows.append({**common, "Feature space": ARGMAX_SPACE, "p": blocks["fbcca"].shape[1], "Model": "argmax",
               "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)})
  if verbose:
    print(f"  {ARGMAX_SPACE:<26} p={blocks['fbcca'].shape[1]:<3} {'argmax':<20} 1.0 s {100 * a1:6.2f}%  "
          f"2.0 s smoothed {100 * a2:6.2f}%  (all clean windows, nothing fitted)")
  return rows, failures


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  reports = args.reports_dir or ROOT / "reports"
  t0 = time.time()
  try:
    blocks = prepare_subject(processed, args.subject, None, args.fs)
  except (FileNotFoundError, ValueError) as exc:
    print(f"[-] Skipping {args.subject}: {exc}")
    return 1
  header = legacy_header_lines(args.fs, blocks["thresholds"], args.seed, CV_LABEL, SMOOTH_LABEL,
                         blocks["fbcca_channels"])
  print(f"Data source: legacy windows, {_rel(processed)}/{args.subject}/ (P02, OO session), stimulus windows only")
  print("\n".join(header))
  print(f"  {channel_summary(blocks)}")
  print(f"\n[+] {args.subject}: {blocks['n_stimulus']} stimulus windows, {blocks['n_clean']} clean, "
        f"{blocks['n_rejected']} rejected")
  rows, failures = run_benchmark(blocks, args.subject, args.m, args.seed)
  df = pd.DataFrame(rows, columns=COLUMNS)
  csv = Path(reports) / f"feature_space_benchmark_{args.subject}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text("\n".join(header) + "\n")
  best = df[df["Feature space"] != ARGMAX_SPACE].sort_values("1.0s Acc (%)", ascending=False).iloc[0]
  print(f"\nCohort: 1 subject ({args.subject}), {len(df)} rows, {len(failures)} model failures; best "
        f"{best['Feature space']} / {best['Model']} {best['1.0s Acc (%)']:.2f}% / {best['2.0s Smoothed (%)']:.2f}%; "
        f"runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
