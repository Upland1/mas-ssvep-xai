"""MVAR fit by ridge OLS and partial directed coherence (P13, R6, PF-17).

The design matrix has one row per time sample of each window (rows never cross a window boundary)
and COLUMNS CHANNEL-MAJOR: `column = c * p + (lag - 1)`, built from `window[:, t-p:t][:, ::-1]`
flattened. Coefficients of lag `l` (0-based `lag = l - 1`) are therefore the STRIDED rows
`weights[lag::p, :].T` (PF-17); contiguous slicing `weights[lag*C:(lag+1)*C]` is the historical bug,
kept only in `scripts/connectivity/diagnostics/demo_mvar_slicing.py`.

`A[l-1][i, j]` is the effect of channel j at lag l on channel i. `compute_condition_pdc` returns a
`(C, C)` matrix with entry `[i, j]` = flow j -> i, zero diagonal (directed: 42 edges at 7 channels).
Legacy: bands live on the fs-250 axis (PF-04).
"""

import numpy as np

ORDER = 10
N_FREQS = 15
RIDGE_SCALE = 1e-4


def _design(windows: np.ndarray, p: int) -> tuple:
  """`(X (rows, C*p), Y (rows, C))` with channel-major columns; no row crosses a window boundary."""
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got {w.shape}")
  n, c, t = w.shape
  if t <= p:
    raise ValueError(f"window length {t} must exceed the order {p}")
  seg = np.lib.stride_tricks.sliding_window_view(w, p + 1, axis=2)  # (n, C, T-p, p+1)
  lagged = seg[..., :p][..., ::-1]                                  # [..., l-1] = x[t-l]
  x = lagged.transpose(0, 2, 1, 3).reshape(n * (t - p), c * p)      # (c, lag) flattened, channel-major
  y = seg[..., p].transpose(0, 2, 1).reshape(n * (t - p), c)
  return x, y


def fit_mvar_ols(windows: np.ndarray, p: int = ORDER) -> np.ndarray:
  """`weights (C*p, C)` of the ridge OLS fit (ridge `1e-4 * tr(G) / dim`, `G = X'X`).

  `weights[c*p + lag, i]` is the coefficient of channel c at lag+1 on channel i.
  """
  x, y = _design(windows, p)
  g = x.T @ x
  ridge = RIDGE_SCALE * np.trace(g) / g.shape[0]
  return np.linalg.solve(g + ridge * np.eye(g.shape[0]), x.T @ y)


def mvar_coefficients(weights: np.ndarray, p: int) -> np.ndarray:
  """`(p, C, C)`: `A[lag][i, j]` from the strided rows `weights[lag::p, :].T` (PF-17, R6)."""
  wts = np.asarray(weights)
  return np.stack([wts[lag::p, :].T for lag in range(p)])


def pdc_from_coefficients(coefs: np.ndarray, fs: float, freqs: np.ndarray) -> np.ndarray:
  """`(F, C, C)` column-normalised |A(f)| with `A(f) = I - sum_l A_l exp(-2 pi i f l / fs)`; zero diagonal.

  `[f, i, j]` is the flow j -> i: `|A_ij| / sqrt(sum_k |A_kj|^2)` (normalised per source column).
  """
  p, c, _ = coefs.shape
  lags = np.arange(1, p + 1)
  e = np.exp(-2j * np.pi * np.asarray(freqs)[:, None] * lags[None, :] / fs)  # (F, p)
  a = np.eye(c)[None] - np.einsum("fl,lij->fij", e, coefs)
  mag = np.abs(a)
  pdc = mag / np.sqrt((mag ** 2).sum(axis=1, keepdims=True))
  idx = np.arange(c)
  pdc[:, idx, idx] = 0.0
  return pdc


def compute_condition_pdc(windows: np.ndarray, fs: float, band: tuple, order: int = ORDER) -> np.ndarray:
  """`(C, C)` PDC of a condition: MVAR on all windows, 15 frequencies across `band`, averaged; `[i, j]` = j -> i."""
  coefs = mvar_coefficients(fit_mvar_ols(windows, order), order)
  freqs = np.linspace(band[0], band[1], N_FREQS)
  return pdc_from_coefficients(coefs, fs, freqs).mean(axis=0)


compute_condition_pdc.directed = True
