"""Occipital harmonic PSD + FBCCA -> Shrinkage-LDA on one subject (P05.5, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus
windows only. Features: 32 harmonic-PSD bins (PO8, O1, Oz, O2 selected by name x 8 bins nearest
8.57, 10.91, 15, 17.14, 20, 21.82, 24, 30 Hz on the fs-250 periodogram grid) + 5 FBCCA scores = 37;
FBCCA gets the same visual cluster PO8, O1, Oz, O2 only, selected by name (as the original;
decisions.md P05). The harmonic PSD is computed on the windows kept by the one window mask that
also gates FBCCA (R5 per-script gate, original extractor limits vpp 0.5-120 uV, std 0.1-35 uV,
computed on all channels; PF-10: the original's unmasked harmonic PSD is not reproduced). Model: Pipeline(StandardScaler, Shrinkage-LDA lsqr auto) fitted per
training fold (R2).

Legacy (labelled): R1/PF-01 StratifiedKFold(5, shuffle, 42) over windows (leaky); legacy i%5
trial smoothing (R8 legacy, PF-02); R3/PF-14 and PF-04 per-window filtering, fs 250.

Output: confusion matrix <figures-dir>/confusion_matrices/cm_harmonic_fbcca_cv_<S>.png (S03 also
cm_harmonic_fbcca_cv.png) and <reports-dir>/classification_report_benchmark_harmonic_fbcca_<S>.txt.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np


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

from src.io.channels import legacy_scalp  # noqa: E402
from src.features.ssvep.harmonic_psd import VISUAL_CLUSTER  # noqa: E402
from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  DEFAULT_SUBJECT, figure_paths, legacy_header_lines, load_config, plot_confusion, prepare_subject,
  save_classification_report)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  CV_LABEL, SEED, SMOOTH_LABEL, accuracies, oof_space, space_width)
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
MODEL = "Shrinkage-LDA lsqr"
SPACE = "Harmonic PSD + FBCCA"


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default: {DEFAULT_SUBJECT})")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None, help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--figures-dir", type=Path, default=None, help="default: <root>/ + paths.figures_dir")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  p.add_argument("--no-figures", action="store_true")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  scalp = legacy_scalp(cfg["channels"]["scalp"])  # legacy 7-channel arrays (config v2 has PO7)
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  reports = args.reports_dir or ROOT / "reports"
  figures = args.figures_dir or ROOT / cfg["paths"]["figures_dir"]
  t0 = time.time()
  try:
    b = prepare_subject(processed, args.subject, scalp, args.fs, fbcca_channels=VISUAL_CLUSTER)
  except (FileNotFoundError, ValueError) as exc:
    print(f"[-] Skipping {args.subject}: {exc}")
    return 1
  header = legacy_header_lines(args.fs, b["thresholds"], args.seed, CV_LABEL, SMOOTH_LABEL)
  print(f"Data source: legacy windows, {_rel(processed)}/{args.subject}/ (P02, OO session), stimulus windows only")
  print("\n".join(header))
  space = [s for s in benchmark_spaces(b) if s.name == SPACE][0]
  y = b["y"]
  print(f"\n[+] {args.subject}: {b['n_stimulus']} stimulus windows, {b['n_clean']} clean, {b['n_rejected']} rejected; "
        f"{SPACE} p={space_width(space)} (harmonic PSD {b['harmonic'].shape[1]} + FBCCA {b['fbcca'].shape[1]} "
        f"on {', '.join(b['fbcca_channels'])})")
  res, errs = oof_space(space, None, y, {MODEL: get_sklearn_model_suite(args.seed)[MODEL]}, args.seed)
  if errs:
    print(f"[x] {MODEL} failed: {errs[MODEL]}")
    return 1
  r = res[MODEL]
  a1, a2 = accuracies(y, r["pred"], r["scores"])
  print(f"  {MODEL}: 1.0 s {100 * a1:.2f}%  2.0 s smoothed {100 * a2:.2f}% (out-of-fold; legacy i%5 trial smoothing)")
  txt = Path(reports) / f"classification_report_benchmark_harmonic_fbcca_{args.subject}.txt"
  title = (f"{args.subject} {SPACE} (FBCCA on {', '.join(b['fbcca_channels'])}) -> {MODEL}; {CV_LABEL}; "
           f"out-of-fold 1.0 s accuracy {100 * a1:.2f}%, 2.0 s smoothed {100 * a2:.2f}% ({SMOOTH_LABEL}); "
           f"clean windows {b['n_clean']}, rejected {b['n_rejected']}")
  print(save_classification_report(y, r["pred"], txt, title))
  print(f"Saved: {_rel(txt)}")
  if not args.no_figures:
    ttl = f"{args.subject} {SPACE} -> {MODEL}\nlegacy leaky CV (R1/PF-01), out-of-fold; 1.0 s {100 * a1:.2f}%"
    for p in plot_confusion(y, r["pred"], ttl, figure_paths(Path(figures) / "confusion_matrices",
                                                           "cm_harmonic_fbcca_cv", args.subject)):
      print(f"Figure: {_rel(p)}")
  print(f"\nCohort: 1 subject ({args.subject}); 1.0 s {100 * a1:.2f}%, 2.0 s smoothed {100 * a2:.2f}%; "
        f"runtime {time.time() - t0:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
