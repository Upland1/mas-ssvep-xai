"""Window spectra for the exploration checks (P03): FFT power, periodogram features, channels by name.

Windows are `(n, C, T)` arrays of already-filtered legacy windows (P02). The
legacy arrays store no sampling rate, so every function takes `fs` explicitly;
Era A assumes `LEGACY_FS_HZ = 250` (legacy, PF-04) while the recordings are
256 Hz. With `fs = 250` on 256-sample windows the bins are spaced 250/256 Hz:
a 24 Hz sinusoid sampled at 256 Hz stays in bin 24 and is labelled
24 * 250/256 = 23.4375 Hz. `fs_label` names the mode so it can be printed and
written into figure titles.
"""

from typing import Optional, Sequence

import numpy as np
from scipy.signal import periodogram

# legacy: Era A feature code assumes 250 Hz on 256 Hz recordings (02_REQUIREMENTS 5.4, PF-04).
LEGACY_FS_HZ = 250.0


def fs_label(fs: float, header_fs: Optional[float] = None) -> str:
  """`fs=250 (legacy)`, `fs=256 (header)` or `fs=<x> (override)` for consoles and titles.

  `header_fs` is the true sampling rate when known (legacy windows: samples per
  window / sub-window seconds). Header wins when both match.
  """
  if header_fs is not None and float(fs) == float(header_fs):
    kind = "header"
  elif float(fs) == LEGACY_FS_HZ:
    kind = "legacy"
  else:
    kind = "override"
  return f"fs={float(fs):g} ({kind})"


def select_channels_by_name(names: Sequence[str], wanted: Sequence[str],
                            n_channels: int) -> list:
  """Indices of `wanted` in `names`, in the order of `wanted` (PF-06: names, never positions).

  Raises ValueError when `len(names) != n_channels` (the name list does not
  describe the array) or when a wanted name is missing or duplicated.
  """
  names = list(names)
  if len(names) != int(n_channels):
    raise ValueError(f"{len(names)} channel names {names} for an array with {n_channels} channels")
  idx = []
  for w in wanted:
    hits = [k for k, n in enumerate(names) if n == w]
    if len(hits) != 1:
      raise ValueError(f"channel {w!r} found {len(hits)} times in {names}")
    idx.append(hits[0])
  return idx


def fft_power(windows: np.ndarray, fs: float) -> tuple:
  """`(freqs (F,), power (n, C, F))`: `|rfft(x)|^2` along the last axis, no window, no scaling.

  `freqs = rfftfreq(T, 1/fs)`, so the bin spacing is `fs / T`; `fs` only labels
  the axis (the power values do not depend on it).
  """
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim == 2:
    w = w[np.newaxis]
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T) or (C, T), got shape {w.shape}")
  power = np.abs(np.fft.rfft(w, axis=-1)) ** 2
  return np.fft.rfftfreq(w.shape[-1], d=1.0 / float(fs)), power


def band_mask(freqs: np.ndarray, freq_range: tuple) -> np.ndarray:
  """Boolean mask `lo <= f <= hi` (inclusive, as `prepare_feature_matrix`)."""
  lo, hi = freq_range
  f = np.asarray(freqs)
  return (f >= lo) & (f <= hi)


def mean_spectrum(power: np.ndarray, channels: Optional[Sequence[int]] = None) -> np.ndarray:
  """Mean of `power (n, C, F)` over windows and the selected channels (all if None) -> `(F,)`."""
  p = np.asarray(power, dtype=np.float64)
  if channels is not None:
    p = p[:, list(channels), :]
  if p.shape[0] == 0 or p.shape[1] == 0:
    raise ValueError(f"no windows or channels to average (power {p.shape})")
  return p.mean(axis=(0, 1))


def spectrum_peaks(freqs: np.ndarray, spectrum: np.ndarray, freq_range: tuple,
                   target_hz: Optional[float] = None, n_harmonics: int = 2) -> dict:
  """Maximum of `spectrum` in `freq_range` and the power at the bins nearest the target harmonics.

  Returns `f_max`, `p_max`, `k_max` (bin index of the maximum on the full
  axis), `band_median` (median power in the range) and `harmonics`: a list of
  `{h, f_target, k, f_bin, power}` for `h = 1..n_harmonics` whose `h * target_hz`
  lies in the range, where `k` is the bin nearest `h * target_hz` on the
  labelled axis (ties to the lower bin).
  """
  f = np.asarray(freqs, dtype=np.float64)
  s = np.asarray(spectrum, dtype=np.float64)
  sel = np.flatnonzero(band_mask(f, freq_range))
  if sel.size == 0:
    raise ValueError(f"no bins in {freq_range}")
  k_max = int(sel[np.argmax(s[sel])])
  out = {"f_max": float(f[k_max]), "p_max": float(s[k_max]), "k_max": k_max,
         "band_median": float(np.median(s[sel])), "harmonics": []}
  if target_hz is not None:
    lo, hi = freq_range
    for h in range(1, n_harmonics + 1):
      ft = h * float(target_hz)
      if not lo <= ft <= hi:
        continue
      k = int(np.argmin(np.abs(f - ft)))
      out["harmonics"].append({"h": h, "f_target": ft, "k": k, "f_bin": float(f[k]),
                               "power": float(s[k])})
  return out


def psd_features(windows: np.ndarray, fs: float, freq_range: tuple = (5.0, 35.0)) -> tuple:
  """Periodogram features with the P02 layout: `(X (n, C * F), freqs (F,), psd (n, C, F))`.

  `scipy.signal.periodogram(x, fs=fs, axis=-1)` with its defaults (boxcar,
  constant detrend, density scaling), bins `lo <= f <= hi`, flattened
  channel-major (feature `c * F + j`). On 256-sample windows: 31 bins at fs 256,
  30 at fs 250 (legacy).
  """
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got shape {w.shape}")
  freqs, psd = periodogram(w, fs=float(fs), axis=-1)
  sel = band_mask(freqs, freq_range)
  psd = psd[..., sel]
  return psd.reshape(psd.shape[0], psd.shape[1] * psd.shape[2]), freqs[sel], psd
