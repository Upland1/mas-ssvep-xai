"""Trainable parameter counts of the raw-window networks at 7 channels x 256 samples (P09.4, R-8).

Checks EEGNet 2,349, ShallowConvNet 14,485 and Compact-CNN 56,021 (fs 250 legacy, K = 29, PF-04) exactly
and writes <reports-dir>/network_parameter_counts.csv (Model, Channels, Samples, Params). Exit 1 on any mismatch.
Uses synthetic zeros only; no recordings are read.
"""

import argparse
import sys
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

from src.models.cnn.compact_cnn import CompactCNN  # noqa: E402
from src.models.cnn.eegnet import EEGNetSSVEP, count_parameters  # noqa: E402
from src.models.cnn.shallow_conv_net import ShallowConvNet  # noqa: E402

CHANNELS, SAMPLES = 7, 256
R8 = {"eegnet": 2349, "shallow_convnet": 14485, "compact_cnn": 56021}  # mas/04_REFERENCE_RESULTS.md R-8
COLUMNS = ["Model", "Channels", "Samples", "Params"]


def counts() -> dict:
  nets = {"eegnet": EEGNetSSVEP, "shallow_convnet": ShallowConvNet, "compact_cnn": CompactCNN}
  return {k: count_parameters(cls(n_channels=CHANNELS, n_samples=SAMPLES)) for k, cls in nets.items()}


def main(argv: Optional[Sequence[str]] = None) -> int:
  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  args = p.parse_args(argv)
  got = counts()
  df = pd.DataFrame([{"Model": k, "Channels": CHANNELS, "Samples": SAMPLES, "Params": v} for k, v in got.items()],
                    columns=COLUMNS)
  out = Path(args.reports_dir or ROOT / "reports") / "network_parameter_counts.csv"
  out.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(out, index=False)
  ok = True
  for k, v in got.items():
    status = "OK" if v == R8[k] else "MISMATCH"
    ok &= v == R8[k]
    print(f"{k:16s} {v:>7,d} (R-8 {R8[k]:,d}) {status}")
  print(f"Saved: {out}")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
