"""The 10-model sklearn suite on PSD, FBCCA and FBCSP features of one subject (P05.5, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus
windows only; one quality decision for every feature block (two-tier gate from P07, R5 per-script gate, PF-10). Feature
spaces: continuous PSD (210), FBCCA (5), FBCSP in-fold (50 for m = 1). Models: the whole
suite including QDA (reg_param 0.5); a model that fails (QDA rank failure on high-dimensional
spaces, PF-12) is caught and reported as `[-] ... failed`, not fatal. Each model is a
Pipeline(StandardScaler, model); the CSP is fitted on the training fold only (R2/PF-11).

Legacy (labelled): R1/PF-01 StratifiedKFold(5, shuffle, 42) over windows (leaky); legacy i%5
trial smoothing of the out-of-fold scores (R8 legacy, PF-02); R3/PF-14 and PF-04 per-window
filtering, fs 250. Quality gate: two-tier, vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the windows.

Output: <reports-dir>/sklearn_suite_<S>.csv (columns of feature_space_benchmark_<S>.csv; failed
models have no row) and the failures printed.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else two levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import channel_summary  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  DEFAULT_SUBJECT, legacy_header_lines, load_config, prepare_subject)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  CV_LABEL, SEED, SMOOTH_LABEL, accuracies, oof_space, space_width)
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
SPACES = ("Continuous PSD", "FBCCA", "FBCSP (in-fold)")
COLUMNS = ["Subject", "Feature space", "p", "Model", "1.0s Acc (%)", "2.0s Smoothed (%)",
           "Clean Windows", "Rejected"]


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


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  reports = Path(args.reports_dir or ROOT / "reports")
  t0 = time.time()
  try:
    b = prepare_subject(processed, args.subject, None, args.fs)
  except (FileNotFoundError, ValueError) as exc:
    print(f"[-] Skipping {args.subject}: {exc}")
    return 1
  header = legacy_header_lines(args.fs, b["thresholds"], args.seed, CV_LABEL, SMOOTH_LABEL)
  print(f"Data source: legacy windows, {_rel(processed)}/{args.subject}/ (P02, OO session), stimulus windows only")
  print("\n".join(header))
  print(f"  {channel_summary(b)}")
  print(f"\n[+] {args.subject}: {b['n_stimulus']} stimulus windows, {b['n_clean']} clean, {b['n_rejected']} rejected")
  models = get_sklearn_model_suite(args.seed)
  y = b["y"]
  rows, failures = [], []
  for space in [s for s in benchmark_spaces(b, args.m) if s.name in SPACES]:
    p = space_width(space, n_bands=b["subbands"].shape[1])
    res, errs = oof_space(space, b["subbands"], y, models, args.seed)
    for name, r in res.items():
      a1, a2 = accuracies(y, r["pred"], r["scores"])
      rows.append({"Subject": args.subject, "Feature space": space.name, "p": p, "Model": name,
                   "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2),
                   "Clean Windows": b["n_clean"], "Rejected": b["n_rejected"]})
      print(f"  {space.name:<18} p={p:<3} {name:<20} 1.0 s {100 * a1:6.2f}%  2.0 s smoothed {100 * a2:6.2f}%")
    for name, e in errs.items():
      failures.append((space.name, name, e))
      print(f"  [-] {space.name} / {name} failed: {e}")
  csv = reports / f"sklearn_suite_{args.subject}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  pd.DataFrame(rows, columns=COLUMNS).to_csv(csv, index=False)
  print(f"\nCohort: 1 subject ({args.subject}), {len(rows)} model x space rows, {len(failures)} failures "
        f"({', '.join(f'{s}/{m}' for s, m, _ in failures) or 'none'}); runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
