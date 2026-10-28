"""Filter-bank CCA features (P05.1, legacy Era A).

Per window and target frequency f: the window `(C, T)` is band-pass filtered in 3
Chebyshev type I sub-bands, each is correlated (CCA, one component) with the sin/cos
references at h*f (h = 1..H), and the score is `sum_b w_b r_b^2`, `w_b = b^-1.25 + 0.25`
(Chen et al. 2015, J. Neural Eng. 12:046008, doi:10.1088/1741-2560/12/4/046008).

Legacy labels:
- R3 / PF-14: the sub-bands are filtered on each 1 s window (edge effects); fixed from P16.
- PF-04: `fs` defaults to `LEGACY_FS_HZ = 250` although the recordings are 256 Hz.
- R5: the quality decision is the per-script two-tier gate of `window_mask` (P07, limits explicit).

P07 returns `(X, y_clean, valid_mask, channel_report)`; P16 adds `subband_windows=` (the 3 sub-bands saved by
`scripts/build_windows.py`, filtered continuously, R3: nothing is refiltered) and `quality=` (the decision of
`load_subject`, R5: no gate is rerun).
"""

import warnings
from typing import Optional, Sequence

import numpy as np
from scipy.signal import cheby1, filtfilt
from sklearn.cross_decomposition import CCA

from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, channel_report, loader_decision, quality_gate

TARGET_FREQS = [24.0, 20.0, 15.0, 10.9091, 8.5714]
SUBBAND_LOW_HZ = (6.0, 14.0, 22.0)
SUBBAND_HIGH_HZ = 90.0
CHEBY_ORDER = 4
CHEBY_RIPPLE_DB = 3.0


def generate_reference_signals(f: float, fs: float, n_samples: int, n_harmonics: int = 3) -> np.ndarray:
  """Sin/cos references `(2 H, T)`: rows `sin(2 pi h f t), cos(2 pi h f t)` for h = 1..H, `t = n / fs`."""
  t = np.arange(n_samples) / fs
  rows = []
  for h in range(1, n_harmonics + 1):
    rows += [np.sin(2 * np.pi * h * f * t), np.cos(2 * np.pi * h * f * t)]
  return np.stack(rows)


def get_chebyshev_subbands(fs: float) -> list:
  """Three Chebyshev-I band-pass filters `(b, a)`: order 4, 3 dB ripple, `[low, min(90, nyq - 1)]` Hz."""
  high = min(SUBBAND_HIGH_HZ, fs / 2.0 - 1.0)
  return [cheby1(CHEBY_ORDER, CHEBY_RIPPLE_DB, [low, high], btype="band", fs=fs)
          for low in SUBBAND_LOW_HZ]


def fbcca_weights(n_bands: int = 3) -> np.ndarray:
  """Sub-band weights `b^-1.25 + 0.25`, b = 1..n_bands (1.25, 0.6704, 0.5033 for 3)."""
  return np.arange(1, n_bands + 1, dtype=float) ** -1.25 + 0.25


def canonical_correlation(x: np.ndarray, ref: np.ndarray) -> float:
  """First canonical correlation of `x (T, C)` and `ref (T, R)`: Pearson r of the CCA(1) variates; 0 on failure."""
  try:
    with warnings.catch_warnings():
      warnings.simplefilter("ignore")
      u, v = CCA(n_components=1).fit_transform(x, ref)
    r = np.corrcoef(u[:, 0], v[:, 0])[0, 1]
  except Exception:  # degenerate window (constant band, rank deficiency): no correlation
    return 0.0
  return float(r) if np.isfinite(r) else 0.0


def fbcca_window_scores(window: np.ndarray, filters: list, refs: Sequence[np.ndarray]) -> np.ndarray:
  """FBCCA score per target for one window `(C, T)`; `refs[k]` is `(2H, T)`. Sub-bands filtered per window (R3 legacy)."""
  x = np.asarray(window, dtype=np.float64)
  return fbcca_band_scores(np.stack([filtfilt(b, a, x, axis=1) for b, a in filters]), refs)


def fbcca_band_scores(bands: np.ndarray, refs: Sequence[np.ndarray]) -> np.ndarray:
  """FBCCA score per target for the sub-bands of one window `(B, C, T)` (already filtered; `refs[k]` is `(2H, T)`)."""
  bands = np.asarray(bands, dtype=np.float64)
  w = fbcca_weights(len(bands))
  scores = np.zeros(len(refs))
  for k, ref in enumerate(refs):
    for bi in range(len(bands)):
      scores[k] += w[bi] * canonical_correlation(bands[bi].T, ref.T) ** 2
  return scores


def extract_fbcca_features(windows: np.ndarray, y: np.ndarray,
                           channel_names: Optional[Sequence[str]] = None, fs: float = LEGACY_FS_HZ,
                           target_freqs: Sequence[float] = TARGET_FREQS, n_harmonics: int = 3,
                           precomputed: Optional[dict] = None, thresholds: Optional[dict] = None,
                           channel_fail_fraction: float = CHANNEL_FAIL_FRACTION,
                           verbose: bool = False, subband_windows: Optional[np.ndarray] = None,
                           quality: Optional[dict] = None) -> tuple:
  """FBCCA scores of the accepted windows: `(X (n_clean, n_targets), y_clean, valid_mask (n,), channel_report)`.

  `windows (n, C, T)`, `y (n,)`, `channel_names` (C names; None -> `resolve_channel_names(C)`, PF-06).
  The two-tier gate (`window_mask.quality_gate`, limits explicit) drops noisy channels and rejects
  windows; the CCA uses the surviving channels only (`channel_report["channels_kept"]`). `precomputed`
  (an earlier `channel_report`) reuses one decision for every feature block (PF-10).
  legacy (R3/PF-14, PF-04): per-window filtering and `fs = 250` by default.

  P16: `quality` (a `load_subject(...)["quality"]` dict) replaces the gate (nothing is rerun, thresholds and
  `precomputed` are ignored; see `window_mask.loader_decision` for the accepted row/channel layouts).
  `subband_windows (n, 3, C, T)` (rows and channels as `windows`) are the saved continuous sub-bands: they are
  used as they are, `fs` only sets the reference signals.
  """
  w = np.asarray(windows, dtype=np.float64)
  y = np.asarray(y)
  if w.ndim != 3 or len(w) != len(y):
    raise ValueError(f"windows {w.shape} and y {y.shape} do not match")
  sb = None
  if subband_windows is not None:
    sb = np.asarray(subband_windows, dtype=np.float64)
    if sb.ndim != 4 or sb.shape[0] != len(w) or sb.shape[2:] != w.shape[1:]:
      raise ValueError(f"subband_windows {sb.shape} do not match windows {w.shape} (need (n, B, C, T))")
    if sb.shape[1] != len(SUBBAND_LOW_HZ):
      raise ValueError(f"FBCCA needs {len(SUBBAND_LOW_HZ)} sub-bands, got {sb.shape[1]}")
  if quality is not None:
    rows, idx, rep = loader_decision(quality, len(w), w.shape[1], channel_names)
    wc, y_c, valid = w[rows][:, idx, :], y[rows], rep["valid_mask"]
    sb = None if sb is None else sb[rows][:, :, idx, :]
  else:
    q = quality_gate(w, y, channel_names, thresholds, channel_fail_fraction, precomputed, verbose)
    wc, y_c, valid, rep = q["windows_clean"], q["y_clean"], q["valid_mask"], channel_report(q)
    if sb is not None:
      sb = sb[np.asarray(valid).astype(bool)][:, :, q["channels_kept_idx"], :]
  refs = [generate_reference_signals(f, fs, w.shape[-1], n_harmonics) for f in target_freqs]
  X = np.zeros((len(wc), len(target_freqs)))
  if sb is None:
    filters = get_chebyshev_subbands(fs)
    for i, win in enumerate(wc):
      X[i] = fbcca_window_scores(win, filters, refs)
  else:
    for i in range(len(wc)):
      X[i] = fbcca_band_scores(sb[i], refs)
  return X, y_c, valid, rep
