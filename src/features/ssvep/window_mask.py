"""One window quality mask for the P05 extractors and benchmarks (R5 per-script gate, PF-10).

The extractors apply the shared `validate_eeg_windows` limits, every threshold passed
explicitly (vpp 5-120 uV, std 1-35 uV; decisions.md P05), to the stimulus windows. The mask
is computed once per script and handed to every extractor (`valid_mask=`) so that all
feature blocks keep exactly the same rows (PF-10, no double gating).
"""

from typing import Optional

import numpy as np

from src.preprocessing.signal.quality_check import validate_eeg_windows

# legacy (R5): per-script gate with the shared defaults written out, never inherited.
P05_MASK_THRESHOLDS = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}


def resolve_window_mask(windows: np.ndarray, valid_mask: Optional[np.ndarray] = None,
                        thresholds: Optional[dict] = None) -> np.ndarray:
  """Int mask `(n,)` (1 = keep): `valid_mask` if given (length-checked), else the explicit gate."""
  n = len(windows)
  if valid_mask is not None:
    m = (np.asarray(valid_mask).reshape(-1) != 0).astype(int)
    if len(m) != n:
      raise ValueError(f"valid_mask has {len(m)} entries for {n} windows")
    return m
  th = dict(P05_MASK_THRESHOLDS if thresholds is None else thresholds)
  missing = {"vpp_min", "vpp_max", "std_min", "std_max"} - set(th)
  if missing:
    raise ValueError(f"thresholds must name every limit explicitly (R5); missing {sorted(missing)}")
  return validate_eeg_windows(windows, vpp_min=th["vpp_min"], vpp_max=th["vpp_max"],
                              std_min=th["std_min"], std_max=th["std_max"])
