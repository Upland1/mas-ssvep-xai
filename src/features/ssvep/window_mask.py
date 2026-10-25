"""One quality decision for the extractors and benchmarks: the two-tier gate (P07.2, PF-10, R5).

From P07 every extractor runs `apply_artifact_quality_pipeline` (tier 1: channels failing the limits
in > 50 % of the windows are dropped for the whole subject; tier 2: windows are rejected on the
surviving channels) with every threshold passed explicitly: vpp 5-120 uV, std 1-35 uV, channel fail
fraction 0.5 (decisions.md P07). The decision is computed once per script and handed to every
extractor (`precomputed=`), so all feature blocks keep the same rows and the same channels (PF-10).

legacy (R5, P05-P06): the single-tier gate with the original extractor limits (vpp 0.5-120, std
0.1-35) stays reachable as `thresholds=P05_MASK_THRESHOLDS, channel_fail_fraction=1.0` (no channel
can fail in more than 100 % of the windows, so tier 1 is off).
"""

from typing import Optional, Sequence

import numpy as np

from src.io.channels import resolve_channel_names
from src.preprocessing.signal.quality_check import LIMIT_KEYS, apply_artifact_quality_pipeline

# P07 shared gate, written out so that nothing is inherited from a default (R5, PF-07).
GATE_THRESHOLDS = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}
CHANNEL_FAIL_FRACTION = 0.5
MASK_LABEL = "two-tier gate (P07)"
# legacy (R5): P05-P06 single-tier gate, original extractor limits.
P05_MASK_THRESHOLDS = {"vpp_min": 0.5, "vpp_max": 120.0, "std_min": 0.1, "std_max": 35.0}
NO_CHANNEL_DROP = 1.0   # channel_fail_fraction that switches tier 1 off (legacy P05 gate)

_BULKY = ("windows_clean", "y_clean")


def names_for(channel_names: Optional[Sequence[str]], n_channels: int) -> list:
  """`channel_names` as a list, or `resolve_channel_names(n_channels)` when None (8 -> montage, 7 -> legacy).

  Raises ValueError when the layout is unknown and no names were given (PF-06).
  """
  if channel_names is None:
    names = resolve_channel_names(n_channels)
    if names is None:
      raise ValueError(f"{n_channels} channels: layout unknown, pass channel_names")
    return names
  return [str(c) for c in channel_names]


def quality_gate(windows: np.ndarray, y: np.ndarray, channel_names: Optional[Sequence[str]] = None,
                 thresholds: Optional[dict] = None,
                 channel_fail_fraction: float = CHANNEL_FAIL_FRACTION,
                 precomputed: Optional[dict] = None, verbose: bool = False) -> dict:
  """The two-tier pipeline result for `windows (n, C, T)` (see `apply_artifact_quality_pipeline`).

  `thresholds` default to `GATE_THRESHOLDS` and must name all four limits when given (R5).
  `precomputed` (an earlier result or `channel_report`) is reused as is (PF-10).
  """
  w = np.asarray(windows)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got {w.shape}")
  th = dict(GATE_THRESHOLDS if thresholds is None else thresholds)
  missing = [k for k in LIMIT_KEYS if k not in th]
  if missing:
    raise ValueError(f"thresholds must name every limit explicitly (R5); missing {missing}")
  return apply_artifact_quality_pipeline(
    w, y, names_for(channel_names, w.shape[1]), vpp_min=th["vpp_min"], vpp_max=th["vpp_max"],
    std_min=th["std_min"], std_max=th["std_max"], channel_fail_fraction_thresh=channel_fail_fraction,
    verbose=verbose, precomputed=precomputed)


def channel_report(result: dict) -> dict:
  """The decision part of a pipeline result (no window arrays): `valid_mask`, `channels_kept`,
  `channels_kept_idx`, `channels_dropped`, `channel_stats`. Valid as `precomputed=`."""
  return {k: v for k, v in result.items() if k not in _BULKY}


def resolve_window_mask(windows: np.ndarray, valid_mask: Optional[np.ndarray] = None,
                        thresholds: Optional[dict] = None) -> np.ndarray:
  """Single-tier int mask `(n,)` (1 = keep): `valid_mask` if given (length-checked), else the explicit
  window gate on all channels. legacy helper of P05-P06; the extractors use `quality_gate`."""
  from src.preprocessing.signal.quality_check import validate_eeg_windows
  n = len(windows)
  if valid_mask is not None:
    m = (np.asarray(valid_mask).reshape(-1) != 0).astype(int)
    if len(m) != n:
      raise ValueError(f"valid_mask has {len(m)} entries for {n} windows")
    return m
  th = dict(P05_MASK_THRESHOLDS if thresholds is None else thresholds)
  missing = [k for k in LIMIT_KEYS if k not in th]
  if missing:
    raise ValueError(f"thresholds must name every limit explicitly (R5); missing {sorted(missing)}")
  return validate_eeg_windows(windows, vpp_min=th["vpp_min"], vpp_max=th["vpp_max"],
                              std_min=th["std_min"], std_max=th["std_max"])
