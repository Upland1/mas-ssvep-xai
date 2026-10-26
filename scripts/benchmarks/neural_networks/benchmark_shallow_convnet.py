"""ShallowConvNet (Schirrmeister et al. 2017) on raw legacy windows (P09.3, legacy Era A, numbers are leaky).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows only,
gated once by the P07 two-tier gate (vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the
windows; R5 per-script gate) exactly as the classical flagship; no preprocessing is run. Each window is
z-scored per channel over its own samples; ShallowConvNet is trained from scratch per fold.

Legacy behaviours (labelled, fixed in P11): R1/PF-01 StratifiedKFold(5, shuffle, 42) over windows (leaky,
NOT comparable with the leak-free R-6); R8/PF-02 "2.0 s smoothed" = legacy i%5 trial smoothing. Fixed
epochs, no validation split, no early stopping, augmentation off by default, `--augment on` (P10). Train accuracy = un-augmented
training fold (PF-30). CPU and CUDA give different but individually deterministic numbers: the device is
stated with every number and in the CSV name (reports/shallow_convnet_benchmark_<device>.csv; `auto` -> resolved device).

Output: <reports-dir>/shallow_convnet_benchmark_<device>.csv (Subject, Device, Clean Windows, Rejected, 1.0s Acc (%),
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
from src.models.cnn.shallow_conv_net import ShallowConvNet  # noqa: E402

SPEC = NetSpec(
  "shallow_convnet", lambda c, ch, t: ShallowConvNet(n_classes=c, n_channels=ch, n_samples=t),
  "model: ShallowConvNet(n_classes=5, F1=40, temporal_kernel_length=25, pool_kernel_length=75, pool_stride=15, dropout=0.5)",
  "not used by ShallowConvNet", "")


def build_parser():
  return _parser(__doc__)


def main(argv: Optional[Sequence[str]] = None) -> int:
  return run_benchmark(SPEC, ROOT, argv, __doc__)


if __name__ == "__main__":
  sys.exit(main())
