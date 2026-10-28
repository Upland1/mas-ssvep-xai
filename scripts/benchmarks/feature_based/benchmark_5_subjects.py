"""Legacy cohort benchmark of the P05 flagship (P06.3, legacy Era A; superseded by benchmark_n_subjects in P11).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), every folder
matching S<digits> that holds the three arrays, stimulus windows only. Per subject exactly the
P05 flagship code path: FBCSP m = 1 (in-fold, R2/PF-11) + FBCCA on the kept channels (55 columns)
-> StandardScaler -> Shrinkage-LDA (lsqr, auto), one quality decision (two-tier gate from P07: vpp 5-120 uV,
std 1-35 uV, channel dropped if it fails in > 50 % of the windows; R5 per-script gate, PF-10).

Legacy behaviours (labelled, fixed in later phases): R1/PF-01 StratifiedKFold(5, shuffle, 42) over
windows (leaky, so NOT comparable with the leak-free R-6); R8/PF-02 "2.0 s smoothed" = legacy i%5
trial smoothing; R3/PF-14 and PF-04 per-window sub-band filtering at fs 250.

Output: <reports-dir>/five_subjects_benchmark.csv (Subject, Clean Windows, Rejected, 1.0s Acc (%),
2.0s Smoothed (%); one row per subject, then a Mean row of the accuracy columns; Clean Windows and
Rejected are blank in it) and a .meta.txt with the protocol labels.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

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
  discover_subjects, legacy_header_lines, load_config, prepare_subject)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  CV_LABEL, SEED, SMOOTH_LABEL, accuracies, oof_space, space_width, splits_for)
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
MODEL = "Shrinkage-LDA lsqr"
SPACE = "FBCSP + FBCCA (in-fold)"
COLUMNS = ["Subject", "Clean Windows", "Rejected", "1.0s Acc (%)", "2.0s Smoothed (%)"]


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="subject folders (default: discover S<digits> folders)")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1)")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None, help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def with_mean_row(rows: list) -> pd.DataFrame:
  """Subject rows + `Mean` row (mean of the CSV's rounded accuracy values, 2 decimals; counts blank)."""
  df = pd.DataFrame(rows, columns=COLUMNS)
  mean = {"Subject": "Mean", "Clean Windows": "", "Rejected": "",
          "1.0s Acc (%)": round(float(df["1.0s Acc (%)"].mean()), 2),
          "2.0s Smoothed (%)": round(float(df["2.0s Smoothed (%)"].mean()), 2)}
  return pd.concat([df, pd.DataFrame([mean], columns=COLUMNS)], ignore_index=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = Path(args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"])
  reports = Path(args.reports_dir or ROOT / "reports")
  subjects = args.subjects or discover_subjects(processed)
  if not subjects:
    print(f"[-] No subject folders with arrays in {_rel(processed)}")
    return 1
  t0 = time.time()
  print(f"Data source: legacy windows, {_rel(processed)}/<S>/ (P02, OO session), stimulus windows only; "
        f"subjects {', '.join(subjects)}")
  rows, header = [], None
  for s in subjects:
    try:
      b = prepare_subject(processed, s, None, args.fs)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    if header is None:
      header = legacy_header_lines(args.fs, b["thresholds"], args.seed, CV_LABEL, SMOOTH_LABEL, b["fbcca_channels"])
      print("\n".join(header))
    space = [sp for sp in benchmark_spaces(b, args.m) if sp.name == SPACE][0]
    res, errs = oof_space(space, b["subbands"], b["y"], {MODEL: get_sklearn_model_suite(args.seed)[MODEL]}, args.seed,
                          splits_for("legacy", b["y"], None, args.seed))   # legacy PF-01, explicit since P16 (N1)
    if errs:
      print(f"[x] {s}: {MODEL} failed: {errs[MODEL]}")
      continue
    a1, a2 = accuracies(b["y"], res[MODEL]["pred"], res[MODEL]["scores"])
    rows.append({"Subject": s, "Clean Windows": b["n_clean"], "Rejected": b["n_rejected"],
                 "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)})
    print(f"  {channel_summary(b)}")
    print(f"[+] {s}: {b['n_stimulus']} stimulus, {b['n_clean']} clean, {b['n_rejected']} rejected; "
          f"p={space_width(space, b['subbands'].shape[1])}; 1.0 s {100 * a1:.2f}%  2.0 s smoothed {100 * a2:.2f}%")
  if not rows:
    print("[-] No subject evaluated")
    return 1
  df = with_mean_row(rows)
  csv = reports / "five_subjects_benchmark.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text("\n".join(header) + f"\nmodel: {SPACE} -> {MODEL}\n")
  print("\n" + df.to_string(index=False))
  m = df.iloc[-1]
  print(f"\nCohort: {len(rows)} subjects, mean 1.0 s {m['1.0s Acc (%)']:.2f}%, 2.0 s smoothed "
        f"{m['2.0s Smoothed (%)']:.2f}% (legacy leaky CV, not comparable with R-6); runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
