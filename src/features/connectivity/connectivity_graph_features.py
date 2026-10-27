"""Per-window graph features of the P15 connectivity gate and GNN (legacy Era B).

For a window `(C, T)` (T = 256 samples) and the five targets f_k = 24, 20, 15, 10.9091, 8.5714 Hz:
- node features `node_band_power`: log10 of the mean Hann-FFT power in `f +- 1 Hz` (nearest bin if
  the band holds none) at the targets (fundamentals) and their 2nd harmonics, harmonic-major:
  column `h * 5 + k` is harmonic `h + 1` of target `k` -> `(n, C, 10)`;
- edge coherence `edge_coherence`: in-window Welch (nperseg 128, step 64 -> 3 Hann segments in 256
  samples), magnitude-squared coherence averaged over the band bins -> `(n, C, C, 5)`;
- edge phase `edge_phase`: unit phasor `(cos, sin)` of the cross-spectrum of the full Hann-windowed
  window summed over the band bins (phase from the CSD, R3) -> `(n, C, C, 5, 2)`; entry `[i, j]` is
  the phase of `X_i conj(X_j)`, so `[j, i]` is its conjugate.

Legacy labels: R3 (features on the raw legacy windows, no continuous filtering exists before P16), fs
defaults to 250 although the recordings are 256 Hz (PF-04, the axis is labelled). The 3-segment
coherence is strongly biased upward (R4, PF-12 style): that is the object under test in the gate.

Layouts (R6): `upper_tri_flat` flattens the pairs `np.triu_indices(C, 1)` (row-major: (0,1), (0,2), ...)
as the slowest axis, then band (then cos/sin): index `pair * 5 + k` for coherence, `(pair * 5 + k) * 2 + c`
for phase. C = 7 gives Ec 21 * 5 = 105 and Ep 21 * 5 * 2 = 210.
"""

from typing import Optional, Sequence

import numpy as np
from scipy.signal import get_window

from src.features.ssvep.fbcca_extraction import TARGET_FREQS
from src.features.ssvep.spectral_power import LEGACY_FS_HZ

HALF_WIDTH_HZ = 1.0
WELCH_NPERSEG = 128
WELCH_STEP = 64
N_HARMONICS = 2
_EPS = 1e-9
_LOG_FLOOR = 1e-12


def band_bins(freqs: np.ndarray, f_hz: float, half_width: float = HALF_WIDTH_HZ) -> np.ndarray:
  """Indices of the bins with `|freq - f_hz| <= half_width`; the single nearest bin if there is none."""
  freqs = np.asarray(freqs)
  sel = np.flatnonzero(np.abs(freqs - f_hz) <= half_width + _EPS)
  if len(sel) == 0:
    sel = np.array([int(np.argmin(np.abs(freqs - f_hz)))])
  return sel


def _as_windows(windows: np.ndarray) -> np.ndarray:
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim == 2:
    w = w[np.newaxis]
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T) or (C, T), got {w.shape}")
  return w


def _hann_fft(w: np.ndarray) -> np.ndarray:
  """rfft of the mean-removed, periodic-Hann windowed signal along the last axis."""
  T = w.shape[-1]
  x = w - w.mean(axis=-1, keepdims=True)
  return np.fft.rfft(x * get_window("hann", T), axis=-1)


def node_band_power(windows: np.ndarray, fs: float = LEGACY_FS_HZ,
                    targets: Sequence[float] = TARGET_FREQS) -> np.ndarray:
  """log10 band power per channel at the targets and 2nd harmonics, `(n, C, 10)`, harmonic-major."""
  w = _as_windows(windows)
  freqs = np.fft.rfftfreq(w.shape[-1], d=1.0 / float(fs))
  power = np.abs(_hann_fft(w)) ** 2
  cols = []
  for h in range(1, N_HARMONICS + 1):
    for f in targets:
      cols.append(power[..., band_bins(freqs, h * f)].mean(axis=-1))
  return np.log10(np.stack(cols, axis=-1) + _LOG_FLOOR)


def edge_coherence(windows: np.ndarray, fs: float = LEGACY_FS_HZ,
                   targets: Sequence[float] = TARGET_FREQS) -> np.ndarray:
  """In-window Welch MSC (nperseg 128, step 64, Hann, constant detrend), band-averaged: `(n, C, C, 5)`.

  Symmetric; the diagonal is 1 (a channel is coherent with itself)."""
  w = _as_windows(windows)
  n, C, T = w.shape
  starts = np.arange(0, T - WELCH_NPERSEG + 1, WELCH_STEP)
  if len(starts) == 0:
    raise ValueError(f"window of {T} samples is shorter than nperseg {WELCH_NPERSEG}")
  seg = np.stack([w[..., s:s + WELCH_NPERSEG] for s in starts], axis=2)   # (n, C, S, L)
  X = _hann_fft(seg)                                                       # (n, C, S, F)
  freqs = np.fft.rfftfreq(WELCH_NPERSEG, d=1.0 / float(fs))
  sxy = np.einsum("ncsf,ndsf->ncdf", X, np.conj(X)) / len(starts)          # (n, C, C, F)
  sxx = (np.abs(X) ** 2).mean(axis=2)                                       # (n, C, F)
  den = sxx[:, :, None, :] * sxx[:, None, :, :]
  msc = np.abs(sxy) ** 2 / np.maximum(den, _LOG_FLOOR)
  return np.stack([msc[..., band_bins(freqs, f)].mean(axis=-1) for f in targets], axis=-1)


def edge_phase(windows: np.ndarray, fs: float = LEGACY_FS_HZ,
               targets: Sequence[float] = TARGET_FREQS) -> np.ndarray:
  """Unit phasor `(cos, sin)` of the full-window cross-spectrum summed over the band bins: `(n, C, C, 5, 2)`.

  `[i, j]` = phase of `sum_k X_i(k) conj(X_j(k))`; the diagonal is (1, 0). A zero cross-spectrum gives (1, 0)."""
  w = _as_windows(windows)
  freqs = np.fft.rfftfreq(w.shape[-1], d=1.0 / float(fs))
  X = _hann_fft(w)                                                          # (n, C, F)
  out = []
  for f in targets:
    b = band_bins(freqs, f)
    g = np.einsum("nck,ndk->ncd", X[..., b], np.conj(X[..., b]))            # (n, C, C)
    mag = np.abs(g)
    ok = mag > _LOG_FLOOR
    ph = np.where(ok, g / np.where(ok, mag, 1.0), 1.0 + 0j)
    out.append(np.stack([ph.real, ph.imag], axis=-1))
  return np.stack(out, axis=3)


def upper_tri_flat(arr: np.ndarray) -> np.ndarray:
  """`(n, C, C, ...)` -> `(n, C (C - 1) / 2 * prod(rest))`: the pairs of `np.triu_indices(C, 1)` first, then the rest."""
  a = np.asarray(arr)
  iu, ju = np.triu_indices(a.shape[1], 1)
  return a[:, iu, ju].reshape(len(a), -1)


def build_graph_features(windows: np.ndarray, fs: float = LEGACY_FS_HZ,
                         targets: Sequence[float] = TARGET_FREQS) -> dict:
  """`{"node": (n, C, 10), "edge_coh": (n, C, C, 5), "edge_phase": (n, C, C, 5, 2)}` for `windows (n, C, T)`."""
  return {"node": node_band_power(windows, fs, targets), "edge_coh": edge_coherence(windows, fs, targets),
          "edge_phase": edge_phase(windows, fs, targets)}
