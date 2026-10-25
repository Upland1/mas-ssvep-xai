"""Loader of the legacy window arrays (P02: `<processed-dir>/<S>/*.npy`)."""

from pathlib import Path

import numpy as np

CLASS_CODES = (101, 102, 103, 104, 105)


def arrays_exist(processed_dir: Path, subject: str) -> bool:
  d = Path(processed_dir) / subject
  return all((d / f"{n}.npy").is_file() for n in ("X_psd_features", "X_time_windows", "y_labels"))


def load_stimulus_windows(processed_dir: Path, subject: str) -> tuple:
  """`(X_psd, X_time, y)` of the stimulus windows (101-105) of a legacy subject folder.

  y holds the condition codes; 201/202 rows are dropped (stimulus-only, decisions.md P02).
  """
  d = Path(processed_dir) / subject
  X_psd = np.load(d / "X_psd_features.npy")
  X_time = np.load(d / "X_time_windows.npy")
  y = np.load(d / "y_labels.npy")
  if not (len(X_psd) == len(X_time) == len(y)):
    raise RuntimeError(f"{subject}: array lengths differ ({len(X_psd)}, {len(X_time)}, {len(y)})")
  m = np.isin(y, CLASS_CODES)
  return X_psd[m], X_time[m], y[m]
