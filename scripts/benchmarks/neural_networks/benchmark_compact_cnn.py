"""Compact-CNN (spatial -> temporal, Waytowich et al. 2018) on raw legacy windows (P09.3, legacy Era A, numbers are leaky).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows only,
gated once by the P07 two-tier gate (vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the
windows; R5 per-script gate) exactly as the classical flagship; no preprocessing is run. Each window is
z-scored per channel over its own samples; CompactCNN is trained from scratch per fold.

Legacy behaviours (labelled, fixed in P11): R1/PF-01 StratifiedKFold(5, shuffle, 42) over windows (leaky,
NOT comparable with the leak-free R-6); R8/PF-02 "2.0 s smoothed" = legacy i%5 trial smoothing. Fixed
epochs, no validation split, no early stopping, augmentation off (P10). Train accuracy = un-augmented
training fold (PF-30). CPU and CUDA give different but individually deterministic numbers: the device is
stated with every number and in the CSV name (reports/compact_cnn_benchmark_<device>.csv; `auto` -> resolved device).
fs 250 sets the temporal kernel K = 29 (PF-04 legacy label; 56,021 parameters); named compact_cnn, not the P20 `compact` EEGNet variant (PF-31).

Output: <reports-dir>/compact_cnn_benchmark_<device>.csv (Subject, Device, Clean Windows, Rejected, 1.0s Acc (%),
2.0s Smoothed (%), Train Acc (%), Params) + .meta.txt with the protocol labels, data source and n_channels.
Shared driver: src/models/cnn/benchmark_common.py (identical protocol for all raw-window networks).
"""

import sys
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

from src.models.cnn.benchmark_common import COLUMNS, NetSpec, build_parser as _parser, gated_windows, run_benchmark  # noqa: E402,F401
from src.models.cnn.compact_cnn import CompactCNN  # noqa: E402

SPEC = NetSpec(
  "compact_cnn", lambda c, ch, t: CompactCNN(n_classes=c, n_channels=ch, n_samples=t),
  "model: CompactCNN(n_classes=5, fs=250.0 legacy PF-04 -> K=29, lowest_freq_hz=8.5714, F1=16, F2=32, dropout=0.5)",
  "sets the temporal kernel K = 29, PF-04 legacy", "")


def build_parser():
  return _parser(__doc__)


def main(argv: Optional[Sequence[str]] = None) -> int:
  return run_benchmark(SPEC, ROOT, argv, __doc__)


if __name__ == "__main__":
  sys.exit(main())
