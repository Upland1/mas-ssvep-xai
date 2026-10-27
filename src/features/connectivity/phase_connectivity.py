"""Phase connectivity from the cross-spectral density: PLV and wPLI (P13, R3, PF-18).

Per window and channel pair one band-averaged complex CSD value (`scipy.signal.csd`, Welch,
`nperseg = min(T, 128)`); the phase is its angle. No time-domain filtering or Hilbert transform
touches a short window (that is the PF-18 bug, kept only in `scripts/connectivity/diagnostics/
demo_hilbert_edges.py`).

- PLV  = |mean_w exp(i angle(S_w))|
- wPLI = |mean_w Im(S_w)| / mean_w |Im(S_w)|  (0 when the denominator is 0)

Matrices are `(C, C)`, symmetric, NaN diagonal, input channel order (R6).
Legacy: bands live on the fs-250 axis (PF-04).
"""

from typing import Optional

import numpy as np
from scipy.signal import csd

from src.features.connectivity.connectivity_extraction import band_average

PHASE_NPERSEG = 128
METRICS = ("plv", "wpli")


def window_csd(windows: np.ndarray, fs: float, band: tuple, nperseg: Optional[int] = None) -> np.ndarray:
  """`(n, C, C)` complex band-averaged CSD per window; `[:, i, j]` and `[:, j, i]` are conjugates.

  The diagonal holds NaN. Pair `(i, j)` uses `csd(x_i, x_j)` over all windows at once.
  """
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got {w.shape}")
  n, c, t = w.shape
  nper = min(t, PHASE_NPERSEG) if nperseg is None else min(int(nperseg), t)
  out = np.full((n, c, c), np.nan + 0j, dtype=np.complex128)
  for i in range(c):
    for j in range(i + 1, c):
      f, pxy = csd(w[:, i], w[:, j], fs=fs, nperseg=nper, axis=-1)
      s = band_average(f, pxy, band)
      out[:, i, j] = s
      out[:, j, i] = np.conj(s)
  return out


def plv_from_csd(s: np.ndarray) -> np.ndarray:
  """PLV `(C, C)` from per-window complex CSD `(n, C, C)`."""
  return np.abs(np.exp(1j * np.angle(s)).mean(axis=0))


def wpli_from_csd(s: np.ndarray) -> np.ndarray:
  """wPLI `(C, C)` from per-window complex CSD `(n, C, C)`; 0 where mean|Im| is 0."""
  im = np.imag(s)
  num = np.abs(np.mean(im, axis=0))
  den = np.mean(np.abs(im), axis=0)
  with np.errstate(invalid="ignore", divide="ignore"):
    out = np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)
  out[np.isnan(s).any(axis=0)] = np.nan  # the NaN diagonal
  return out


_REDUCERS = {"plv": plv_from_csd, "wpli": wpli_from_csd}


def compute_phase_connectivity(windows: np.ndarray, fs: float, band: tuple, metric: str,
                               nperseg: Optional[int] = None) -> np.ndarray:
  """`(C, C)` PLV or wPLI of a condition's windows in `band` (phase from the CSD, R3)."""
  if metric not in _REDUCERS:
    raise ValueError(f"metric must be one of {METRICS}, got {metric!r}")
  return _REDUCERS[metric](window_csd(windows, fs, band, nperseg))


def compute_condition_plv(windows: np.ndarray, fs: float, band: tuple) -> np.ndarray:
  """Condition-level PLV from the CSD."""
  return compute_phase_connectivity(windows, fs, band, "plv")


def compute_condition_wpli(windows: np.ndarray, fs: float, band: tuple) -> np.ndarray:
  """Condition-level wPLI from the CSD."""
  return compute_phase_connectivity(windows, fs, band, "wpli")


# Permutation fast path: the per-window CSD does not depend on the grouping, so it is computed once
# on the pooled windows and each permutation only reduces a subset (identical to the direct call).
compute_condition_plv.per_window = window_csd
compute_condition_plv.reduce = plv_from_csd
compute_condition_wpli.per_window = window_csd
compute_condition_wpli.reduce = wpli_from_csd
