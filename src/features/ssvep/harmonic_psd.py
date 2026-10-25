"""Harmonic-PSD feature selections on the legacy periodogram layouts.

Two selections live here:

- the P04 hybrid features (`extract_harmonic_features`): 8 bins of the 1 Hz grid
  `linspace(5, 35, 31)` on `POz, O1, Oz, O2`, taken from the saved `X_psd_features`
  (moved from `scripts/training/train_models.py` in P05, re-exported there);
- the P05 benchmark features (`visual_cluster_harmonic_psd`): 8 bins nearest to the
  harmonic targets on the continuous-PSD grid of the extractor (fs 250, bin spacing
  250/256 Hz) on the visual cluster `PO8, O1, Oz, O2` selected by name (PF-06,
  01_DATA_SPEC section 6).

Both are channel-major: feature `8 r + c` = channel r, bin c.
"""

from typing import Sequence

import numpy as np

from src.features.ssvep.spectral_power import select_channels_by_name

KEEP_CHANNEL_NAMES = ("POz", "O1", "Oz", "O2")        # P04: positions (1, 4, 5, 6) of the 7-channel layout
KEEP_CHANNELS = (1, 4, 5, 6)
HARMONIC_TARGETS_HZ = (8.57, 10.91, 15.0, 20.0, 24.0, 17.14, 21.82, 30.0)   # P04 order
BENCHMARK_TARGETS_HZ = (8.57, 10.91, 15.0, 17.14, 20.0, 21.82, 24.0, 30.0)  # P05 / roadmap order
VISUAL_CLUSTER = ("PO8", "O1", "Oz", "O2")            # P05: 01_DATA_SPEC section 6, by name


def check_keep_channels(scalp_names: Sequence[str], keep_channels: Sequence[int] = KEEP_CHANNELS,
                        expected: Sequence[str] = KEEP_CHANNEL_NAMES) -> None:
  """Assert that the positional `keep_channels` are `expected` by name (PF-06)."""
  got = tuple(scalp_names[i] for i in keep_channels)
  if got != tuple(expected):
    raise ValueError(f"keep_channels {tuple(keep_channels)} select {got}, expected {tuple(expected)}")


def harmonic_bin_indices(freq_start: float = 5, freq_end: float = 35,
                         targets: Sequence[float] = HARMONIC_TARGETS_HZ) -> np.ndarray:
  """Sorted, deduplicated indices of the grid `linspace(freq_start, freq_end, 31)` nearest to `targets`.

  Default: 9, 11, 15, 17, 20, 22, 24, 30 Hz = indices 4, 6, 10, 12, 15, 17, 19, 25.
  """
  grid = np.linspace(freq_start, freq_end, int(round(freq_end - freq_start)) + 1)
  return np.unique([int(np.argmin(np.abs(grid - t))) for t in targets])


def extract_harmonic_features(X_psd: np.ndarray, n_channels: int = 7, freq_start: float = 5,
                              freq_end: float = 35, keep_channels: Sequence[int] = KEEP_CHANNELS) -> np.ndarray:
  """32 harmonic-PSD features `(n, 4 * 8)`, channel-major: feature `8 r + c` = channel r, bin c.

  `X_psd (n, n_channels * 31)` is reshaped to `(n, n_channels, 31)` (P02 layout, channel-major),
  channels `keep_channels` (POz, O1, Oz, O2 for the 7-channel layout; names are asserted by
  `check_keep_channels` in the scripts) and the grid bins nearest to the harmonic targets are kept.
  """
  X = np.asarray(X_psd)
  n_bins = int(round(freq_end - freq_start)) + 1
  if X.ndim != 2 or X.shape[1] != n_channels * n_bins:
    raise ValueError(f"X_psd {X.shape} is not (n, {n_channels} * {n_bins})")
  idx = harmonic_bin_indices(freq_start, freq_end)
  sel = X.reshape(X.shape[0], n_channels, n_bins)[:, list(keep_channels)][:, :, idx]
  return sel.reshape(X.shape[0], -1)


def nearest_bin_indices(freqs: np.ndarray, targets: Sequence[float] = BENCHMARK_TARGETS_HZ) -> np.ndarray:
  """Index of the bin of `freqs` nearest to each target, in target order (ties go to the lower bin)."""
  f = np.asarray(freqs, dtype=float)
  return np.array([int(np.argmin(np.abs(f - t))) for t in targets])


def visual_cluster_harmonic_psd(X_psd: np.ndarray, freqs: np.ndarray, channel_names: Sequence[str],
                                cluster: Sequence[str] = VISUAL_CLUSTER,
                                targets: Sequence[float] = BENCHMARK_TARGETS_HZ) -> np.ndarray:
  """Harmonic PSD `(n, len(cluster) * len(targets))` of the benchmark (P05), channel-major.

  `X_psd (n, C * F)` is the continuous PSD (channel-major, `F = len(freqs)`); channels are
  picked by name in the order of `cluster` (PF-06), bins are the ones of `freqs` nearest to
  each target (fs-250 grid when `freqs` comes from `extract_continuous_psd_features`).
  """
  X = np.asarray(X_psd)
  n_ch, n_f = len(channel_names), len(freqs)
  if X.ndim != 2 or X.shape[1] != n_ch * n_f:
    raise ValueError(f"X_psd {X.shape} is not (n, {n_ch} channels * {n_f} bins)")
  ch = select_channels_by_name(channel_names, list(cluster), n_ch)
  bins = nearest_bin_indices(freqs, targets)
  sel = X.reshape(X.shape[0], n_ch, n_f)[:, ch][:, :, bins]
  return sel.reshape(X.shape[0], -1)
