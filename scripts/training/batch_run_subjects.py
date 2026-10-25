"""Per-subject LDA summary over several subjects (P04.4, legacy Era A).

For each subject: if its legacy arrays are missing, run `scripts.preprocessing.run_preprocessing`
for it (the only step that reads recordings); then report Shrinkage-LDA 1.0 s and 2-window
smoothed accuracy on the hybrid (32 harmonic-PSD + 5 FBCCA) under
`cv=StratifiedKFold (legacy, leaky, R1/PF-01)` and `smoothing: legacy no-reset (R8/PF-02)`
(scaler inside each fold, R2). Data source: legacy windows, the `--paradigm` session file.
Output: <out-dir>/reports/batch_run_subjects.csv.

HOOK (deep-learning builder): `evaluate_subject` returns the row dict of one subject; the fusion
CNN adds its columns there (`CNN 1.0 s`, `CNN smoothed`) by updating the same dict.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from scripts.training.train_final_model import load_subject_inputs  # noqa: E402
from scripts.training.train_models import (  # noqa: E402
  CLASS_CODES, DEFAULT_CONFIG, N_FOLDS, arrays_exist, check_keep_channels, load_config, make_classifiers,
  print_legacy_header, run_evaluation)

DEFAULT_PARADIGM = "OO.ebr"


def ensure_arrays(subject: str, processed: Path, paradigm: str, raw_dir: Optional[Path]) -> bool:
  """True if the arrays exist or the legacy preprocessing script produced them."""
  if arrays_exist(processed, subject):
    return True
  from scripts.preprocessing import run_preprocessing
  argv = ["--subject", subject, "--session", Path(paradigm).stem, "--no-figures",
          "--processed-dir", str(processed)]
  if raw_dir is not None:
    argv += ["--raw-dir", str(raw_dir)]
  print(f"[*] {subject}: arrays missing, running run_preprocessing")
  run_preprocessing.main(argv)
  return arrays_exist(processed, subject)


def evaluate_subject(subject: str, processed: Path, paradigm: str) -> dict:
  """Row of one subject: LDA 1.0 s / smoothed (legacy leaky CV, no-reset smoothing)."""
  X_psd, X_time, y, hybrid = load_subject_inputs(processed, subject)
  if len(y) < N_FOLDS * len(CLASS_CODES):
    raise ValueError(f"only {len(y)} stimulus windows")
  lda = {k: v for k, v in make_classifiers().items() if k == "Shrinkage-LDA"}
  df, _ = run_evaluation(hybrid, y, subject, lda)
  r = df.iloc[0]
  # HOOK(deep-learning): compute the fusion CNN CV on (X_psd, hybrid[:, -5:], y) and add its columns.
  return {"Subject": subject, "Data source": f"legacy windows, {paradigm}", "n_windows": len(y),
          "LDA 1.0 s": r["Accuracy"], "LDA smoothed": r["Smoothed Accuracy"],
          "cv": r["cv"], "smoothing": r["smoothing"]}


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="+", required=True)
  p.add_argument("--paradigm", default=DEFAULT_PARADIGM, help=f"session file (default: {DEFAULT_PARADIGM})")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--raw-dir", type=Path, default=None)
  p.add_argument("--processed-dir", type=Path, default=None)
  p.add_argument("--out-dir", type=Path, default=None, help="default: <root>/outputs")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  check_keep_channels(cfg["channels"]["scalp"])
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  out = args.out_dir or ROOT / "outputs"
  print_legacy_header(processed)
  rows = []
  for s in args.subjects:
    if not ensure_arrays(s, processed, args.paradigm, args.raw_dir):
      print(f"[-] Skipping {s}: no arrays")
      continue
    try:
      row = evaluate_subject(s, processed, args.paradigm)
    except (ValueError, RuntimeError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    rows.append(row)
    print(f"  {s}: n={row['n_windows']}  LDA 1.0 s {100 * row['LDA 1.0 s']:.2f}%  "
          f"smoothed {100 * row['LDA smoothed']:.2f}%")
  if not rows:
    return 1
  df = pd.DataFrame(rows)
  csv = Path(out) / "reports" / "batch_run_subjects.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  print(f"Mean over {len(df)} subjects: LDA 1.0 s {100 * df['LDA 1.0 s'].mean():.2f}%, "
        f"smoothed {100 * df['LDA smoothed'].mean():.2f}%")
  print(f"Saved: {csv}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
