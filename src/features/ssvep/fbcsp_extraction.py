"""Filter-bank common spatial patterns (P05.2, legacy Era A).

`MulticlassCSP` is one-vs-rest CSP: for class k the generalized eigenproblem
`eigh(S_k, S_k + S_rest + 1e-6 I)` (S = mean of the trace-normalized window covariances
`W W^T / tr(W W^T)` of the group) gives spatial filters; the `m` eigenvectors with the largest
and the `m` with the smallest eigenvalue are kept (Ramoser et al. 2000, IEEE Trans. Rehab.
Eng. 8:441, doi:10.1109/86.895946; Ang et al. 2008, IJCNN, doi:10.1109/IJCNN.2008.4634130).
Features of a window: `log10(var_j / sum_j var_j)` over the `2m` projections of each class
(variances floored at 1e-12), so `n_classes * 2m` per band. The filter bank has 5 bands
(`DEFAULT_SUBBANDS`), giving `5 classes * 2 * 5 bands = 50` features for m = 1.

Layout (R6): `features[:, ((b * K) + k) * 2m + j]` = band b, class k, component j; component
order within a class is the m largest eigenvalues (descending) then the m smallest.
`filters_` has shape `(K, C, 2m)`: column j of `filters_[k]` is the j-th filter of class k.

Legacy labels: R3 / PF-14, sub-bands filtered on each 1 s window (Butterworth order 4, filtfilt);
PF-04, fs 250. R2 exception / PF-11: `extract_fbcsp_features` fits the CSP on all windows it is
given and is for visualization only; benchmarks fit `MulticlassCSP` / `FBCSPTransformer`
on the training rows of each fold.
"""

from typing import Optional, Sequence

import numpy as np
from scipy.linalg import eigh
from scipy.signal import butter, filtfilt

from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, channel_report, loader_decision, quality_gate

DEFAULT_SUBBANDS = [(7, 12), (13, 17), (18, 26), (27, 36), (38, 52)]
CSP_REG = 1e-6
VAR_FLOOR = 1e-12


def butter_bandpass_filter(data: np.ndarray, low: float, high: float, fs: float,
                           order: int = 4) -> np.ndarray:
  """Zero-phase Butterworth band-pass along the last axis; `high` is capped at `nyq - 1`."""
  nyq = fs / 2.0
  high = min(float(high), nyq - 1.0)
  b, a = butter(order, [low, high], btype="band", fs=fs)
  return filtfilt(b, a, np.asarray(data, dtype=np.float64), axis=-1)


def filter_subbands(windows: np.ndarray, fs: float = LEGACY_FS_HZ,
                    subbands: Sequence[tuple] = tuple(DEFAULT_SUBBANDS)) -> np.ndarray:
  """Sub-band windows `(n, B, C, T)`; legacy (R3/PF-14): filtered on each window, nothing is fitted."""
  w = np.asarray(windows, dtype=np.float64)
  return np.stack([butter_bandpass_filter(w, lo, hi, fs) for lo, hi in subbands], axis=1)


def _mean_normalized_cov(X: np.ndarray) -> np.ndarray:
  """Mean over windows `(n, C, T)` of `W W^T / tr(W W^T)` -> `(C, C)`."""
  cov = np.einsum("nct,ndt->ncd", X, X)
  tr = np.trace(cov, axis1=1, axis2=2)
  tr = np.where(tr > 0, tr, 1.0)
  return (cov / tr[:, None, None]).mean(axis=0)


class MulticlassCSP:
  """One-vs-rest CSP with `n_components = m` (keeps `2m` filters per class)."""

  def __init__(self, n_components: int = 1):
    self.n_components = int(n_components)

  def fit(self, X: np.ndarray, y: np.ndarray) -> "MulticlassCSP":
    """Fit on `X (n, C, T)`, labels `y`; classes in sorted order (101..105 -> 0..4)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y)
    self.classes_ = np.unique(y)
    n_ch, m = X.shape[1], self.n_components
    if 2 * m > n_ch:
      raise ValueError(f"2 * n_components = {2 * m} exceeds the {n_ch} channels")
    filters, eigvals = [], []
    for c in self.classes_:
      s_t = _mean_normalized_cov(X[y == c])
      s_r = _mean_normalized_cov(X[y != c])
      vals, vecs = eigh(s_t, s_t + s_r + CSP_REG * np.eye(n_ch))   # ascending
      pick = np.r_[np.arange(n_ch - 1, n_ch - 1 - m, -1), np.arange(m)]   # m largest (desc), m smallest
      filters.append(vecs[:, pick])
      eigvals.append(vals[pick])
    self.filters_ = np.stack(filters)       # (K, C, 2m)
    self.eigenvalues_ = np.stack(eigvals)   # (K, 2m)
    return self

  def transform(self, X: np.ndarray) -> np.ndarray:
    """Features `(n, K * 2m)`: per class, `log10(var_j / sum_j var_j)` of its 2m projections."""
    X = np.asarray(X, dtype=np.float64)
    proj = np.einsum("kcj,nct->nkjt", self.filters_, X)
    var = np.maximum(proj.var(axis=-1), VAR_FLOOR)            # (n, K, 2m)
    feats = np.log10(var / var.sum(axis=-1, keepdims=True))
    return feats.reshape(len(X), -1)

  def fit_transform(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return self.fit(X, y).transform(X)


class FBCSPTransformer:
  """Filter-bank CSP on sub-band windows `(n, B, C, T)`: one `MulticlassCSP` per band, fitted on the rows given."""

  def __init__(self, n_components: int = 1):
    self.n_components = int(n_components)

  def fit(self, subband_windows: np.ndarray, y: np.ndarray) -> "FBCSPTransformer":
    sw = np.asarray(subband_windows, dtype=np.float64)
    self.csps_ = [MulticlassCSP(self.n_components).fit(sw[:, b], y) for b in range(sw.shape[1])]
    return self

  def transform(self, subband_windows: np.ndarray) -> np.ndarray:
    """`(n, B * K * 2m)`, band-major (see module docstring)."""
    sw = np.asarray(subband_windows, dtype=np.float64)
    if sw.shape[1] != len(self.csps_):
      raise ValueError(f"{sw.shape[1]} bands given, fitted on {len(self.csps_)}")
    return np.hstack([c.transform(sw[:, b]) for b, c in enumerate(self.csps_)])

  def fit_transform(self, subband_windows: np.ndarray, y: np.ndarray) -> np.ndarray:
    return self.fit(subband_windows, y).transform(subband_windows)


def extract_fbcsp_features(windows: np.ndarray, y: np.ndarray,
                           channel_names: Optional[Sequence[str]] = None, fs: float = LEGACY_FS_HZ,
                           subbands: Sequence[tuple] = tuple(DEFAULT_SUBBANDS), m: int = 1,
                           precomputed: Optional[dict] = None, thresholds: Optional[dict] = None,
                           channel_fail_fraction: float = CHANNEL_FAIL_FRACTION,
                           verbose: bool = False, subband_windows: Optional[np.ndarray] = None,
                           quality: Optional[dict] = None) -> tuple:
  """FBCSP features of the accepted windows: `(X (n_clean, 5 * 2m * B), y_clean, valid_mask, channel_report)`.

  The two-tier gate (`window_mask.quality_gate`) runs first, or `precomputed` (an earlier
  `channel_report`) is reused (PF-10); the CSP uses the surviving channels only.
  VISUALIZATION ONLY (R2 exception, PF-11): the CSP filters are fitted on every accepted window
  and label given, so the features of a window depend on its own label. Benchmarks must use
  `FBCSPTransformer` fitted on the training fold. legacy (R3/PF-14, PF-04): per-window
  filtering, fs 250.

  P16: `subband_windows (n, B, C, T)` (the continuous `fbcsp` bank saved by `build_windows.py`, rows and
  channels as `windows`) are used as they are, nothing is refiltered (R3); `quality` (a
  `load_subject(...)["quality"]` dict) replaces the gate (R5; see `window_mask.loader_decision`).
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
  if quality is not None:
    rows, idx, rep = loader_decision(quality, len(w), w.shape[1], channel_names)
    y_c, valid = y[rows], rep["valid_mask"]
    sw = sb[rows][:, :, idx, :] if sb is not None else filter_subbands(w[rows][:, idx, :], fs, subbands)
  else:
    q = quality_gate(w, y, channel_names, thresholds, channel_fail_fraction, precomputed, verbose)
    y_c, valid, rep = q["y_clean"], q["valid_mask"], channel_report(q)
    if sb is None:
      sw = filter_subbands(q["windows_clean"], fs, subbands)
    else:
      sw = sb[np.asarray(valid).astype(bool)][:, :, q["channels_kept_idx"], :]
  return FBCSPTransformer(m).fit_transform(sw, y_c), y_c, valid, rep
