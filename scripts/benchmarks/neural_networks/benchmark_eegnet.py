"""EEGNet on raw legacy windows (P08.2, legacy Era A, numbers are leaky).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows only,
gated once by the P07 two-tier gate (vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the
windows; R5 per-script gate) exactly as the classical flagship; no preprocessing is run. Each window is
z-scored per channel over its own samples; EEGNetSSVEP is trained from scratch per fold.

Protocol (P11): `--cv grouped` (default) = StratifiedGroupKFold(5, shuffle, 42) over reconstructed trial ids (R1);
`--cv legacy` = the P08-P10 window-level StratifiedKFold (R1/PF-01, leaky, outputs under <reports-dir>/legacy_leaky/);
`--smoothing mod5` (default, R8 legacy-folder clause: i%5 of the clean array) or `trial` (PF-02 diagnostic). Fixed
epochs, no validation split, no early stopping, augmentation off by default, `--augment on` (P10). Train accuracy = un-augmented
training fold (PF-30). CPU and CUDA give different but individually deterministic numbers: the device is
stated with every number and in the CSV name (reports/eegnet_benchmark_<device>.csv; `auto` -> resolved device).

Output: <reports-dir>[/legacy_leaky]/eegnet_benchmark_<device>.csv (Subject, Device, Clean Windows, Rejected, 1.0s Acc (%),
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
from src.models.cnn.eegnet_cv import build_eegnet  # noqa: E402

SPEC = NetSpec(
  "eegnet", build_eegnet, "model: EEGNetSSVEP(n_classes=5, F1=8, D=2, F2=16, kernel_length=125, dropout=0.25)",
  "not used by EEGNet", "max-norm 1.0 on the spatial depthwise filters, ")


def build_parser():
  return _parser(__doc__)


def main(argv: Optional[Sequence[str]] = None) -> int:
  return run_benchmark(SPEC, ROOT, argv, __doc__)


if __name__ == "__main__":
  sys.exit(main())
