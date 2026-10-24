"""Signal figures for the legacy windows (P02): one window, PSD by condition, stimulus vs baseline.

Figures are rendered with the Agg backend, saved to the given path (parent
folders created) and closed; nothing is shown. Inputs are the records of
`src/features/ssvep/psd_extraction.py` (`{code: [record, ...]}`, records with
`psd (C, F)` and `freqs (F,)`).
"""

from pathlib import Path
from typing import Optional, Sequence, Union

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PathLike = Union[str, Path]

# Stimulation frequencies (mas/01_DATA_SPEC.md section 3).
STIM_FREQS_HZ = {101: 24.0, 102: 20.0, 103: 15.0, 104: 120.0 / 11.0, 105: 60.0 / 7.0}
CONDITION_NAMES = {201: "201 fixation", 202: "202 cue (pre-pulse)", 101: "101 24 Hz",
                   102: "102 20 Hz", 103: "103 15 Hz", 104: "104 10.91 Hz", 105: "105 8.57 Hz"}
PLOT_CONDITIONS = (201, 202, 101, 102, 103, 104, 105)

# Fixed categorical order, one slot per condition (validated light palette).
_SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6")
_STYLES = ("-", "--", "-", "-.", "-", ":", "-")
_CONDITION_COLOR = dict(zip(PLOT_CONDITIONS, _SERIES))
_CONDITION_STYLE = dict(zip(PLOT_CONDITIONS, _STYLES))
_BASELINE_COLOR = "#6f6e69"
_INK, _MUTED, _GRID = "#1f1f1e", "#6f6e69", "#e4e3df"


def _style_axes(ax) -> None:
  ax.grid(True, color=_GRID, linewidth=0.6)
  ax.set_axisbelow(True)
  for side in ("top", "right"):
    ax.spines[side].set_visible(False)
  for side in ("left", "bottom"):
    ax.spines[side].set_color(_MUTED)
  ax.tick_params(colors=_MUTED, labelcolor=_INK, labelsize=8)


def _save(fig, save_path: PathLike) -> Path:
  path = Path(save_path)
  path.parent.mkdir(parents=True, exist_ok=True)
  fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
  plt.close(fig)
  return path


def _mean_psd(recs: Sequence[dict], channels: Optional[Sequence[int]]) -> tuple:
  """Mean PSD over records and channels: `(freqs, psd)`; channels by index, all if None."""
  freqs = np.asarray(recs[0]["freqs"])
  stack = np.stack([np.asarray(r["psd"], dtype=np.float64) for r in recs])
  if channels is not None:
    stack = stack[:, list(channels), :]
  return freqs, stack.mean(axis=(0, 1))


def plot_eeg_window(window: np.ndarray, fs: float, save_path: PathLike,
                    channel_names: Optional[Sequence[str]] = None,
                    title: Optional[str] = None, spacing_uv: Optional[float] = None) -> Path:
  """Stacked traces of one `(C, T)` window against time (s), saved to `save_path`.

  Channels are offset by `spacing_uv` (default: 1.2 x the largest channel
  peak-to-peak, at least 1 uV) and labelled by `channel_names` (default
  `ch0..`). Returns the saved path.
  """
  w = np.asarray(window, dtype=np.float64)
  if w.ndim != 2:
    raise ValueError(f"window must be (C, T), got shape {w.shape}")
  n_ch, n_t = w.shape
  names = list(channel_names) if channel_names is not None else [f"ch{c}" for c in range(n_ch)]
  if len(names) != n_ch:
    raise ValueError(f"{len(names)} channel names for {n_ch} channels")
  if spacing_uv is None:
    spacing_uv = max(1.2 * float(np.max(np.ptp(w, axis=-1))), 1.0)
  t = np.arange(n_t) / fs
  fig, ax = plt.subplots(figsize=(8, 0.6 * n_ch + 1.5))
  offsets = spacing_uv * np.arange(n_ch)[::-1]
  for c in range(n_ch):
    ax.plot(t, w[c] - w[c].mean() + offsets[c], color=_SERIES[0], linewidth=1.0)
  ax.set_yticks(offsets)
  ax.set_yticklabels(names)
  ax.set_xlabel("Time (s)", color=_INK)
  ax.set_ylabel(f"Channel (offset {spacing_uv:.3g} uV)", color=_INK)
  ax.set_xlim(t[0], t[-1] if n_t > 1 else 1.0 / fs)
  _style_axes(ax)
  ax.set_title(title or "EEG window", color=_INK, fontsize=10, loc="left")
  return _save(fig, save_path)


def plot_average_psd_by_condition(records: dict, save_path: PathLike,
                                  freq_range: tuple = (1.0, 60.0),
                                  conditions: Sequence[int] = PLOT_CONDITIONS,
                                  channels: Optional[Sequence[int]] = None,
                                  title: Optional[str] = None, log_scale: bool = True) -> Path:
  """Mean periodogram per condition (over windows and channels) in `freq_range`, one line each.

  Conditions with no records are skipped (named in the legend as `n=0`).
  Dotted vertical lines mark the stimulation frequencies of the plotted
  stimulus codes. `channels` selects channel indices (default all). Returns
  the saved path.
  """
  lo, hi = freq_range
  fig, ax = plt.subplots(figsize=(8, 4.5))
  for code in conditions:
    recs = records.get(code, [])
    label = f"{CONDITION_NAMES.get(code, str(code))} (n={len(recs)})"
    if not recs:
      ax.plot([], [], color=_CONDITION_COLOR.get(code, _MUTED), label=label)
      continue
    freqs, psd = _mean_psd(recs, channels)
    sel = (freqs >= lo) & (freqs <= hi)
    ax.plot(freqs[sel], psd[sel], color=_CONDITION_COLOR.get(code, _MUTED),
            linestyle=_CONDITION_STYLE.get(code, "-"), linewidth=1.5, label=label)
    if code in STIM_FREQS_HZ:
      ax.axvline(STIM_FREQS_HZ[code], color=_CONDITION_COLOR[code], linestyle=":",
                 linewidth=0.8, alpha=0.8)
  if log_scale:
    ax.set_yscale("log")
  ax.set_xlim(lo, hi)
  ax.set_xlabel("Frequency (Hz)", color=_INK)
  ax.set_ylabel("PSD (uV^2/Hz)", color=_INK)
  _style_axes(ax)
  ax.legend(fontsize=8, frameon=False, ncol=2)
  ax.set_title(title or "Average PSD by condition", color=_INK, fontsize=10, loc="left")
  return _save(fig, save_path)


def plot_stimulus_vs_baseline_psd(records: dict, save_path: PathLike,
                                  baseline_condition: int = 201,
                                  target_conditions: Sequence[int] = (101, 102, 103, 104, 105),
                                  freq_range: tuple = (1.0, 60.0),
                                  channels: Optional[Sequence[int]] = None,
                                  n_harmonics: int = 2, title: Optional[str] = None,
                                  log_scale: bool = True) -> Path:
  """One panel per stimulus code: its mean PSD against the `baseline_condition` mean PSD.

  Dotted lines mark the stimulation frequency and its harmonics up to
  `n_harmonics` inside `freq_range`. Panels share both axes. Returns the saved path.
  """
  lo, hi = freq_range
  codes = list(target_conditions)
  n = max(len(codes), 1)
  fig, axes = plt.subplots(1, n, figsize=(3.0 * n, 3.4), sharex=True, sharey=True, squeeze=False)
  base = records.get(baseline_condition, [])
  base_psd = _mean_psd(base, channels) if base else None
  for ax, code in zip(axes[0], codes):
    recs = records.get(code, [])
    if base_psd is not None:
      f, p = base_psd
      sel = (f >= lo) & (f <= hi)
      ax.plot(f[sel], p[sel], color=_BASELINE_COLOR, linestyle="--", linewidth=1.2,
              label=f"{baseline_condition} baseline (n={len(base)})")
    if recs:
      f, p = _mean_psd(recs, channels)
      sel = (f >= lo) & (f <= hi)
      ax.plot(f[sel], p[sel], color=_CONDITION_COLOR.get(code, _SERIES[0]), linewidth=1.5,
              label=f"{code} (n={len(recs)})")
    f0 = STIM_FREQS_HZ.get(code)
    if f0 is not None:
      for h in range(1, n_harmonics + 1):
        if lo <= h * f0 <= hi:
          ax.axvline(h * f0, color=_MUTED, linestyle=":", linewidth=0.8)
    if log_scale and (recs or base_psd is not None):
      ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Frequency (Hz)", color=_INK)
    _style_axes(ax)
    ax.set_title(CONDITION_NAMES.get(code, str(code)), color=_INK, fontsize=9, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper right")
  axes[0][0].set_ylabel("PSD (uV^2/Hz)", color=_INK)
  fig.suptitle(title or "Stimulus vs baseline PSD", color=_INK, fontsize=10, x=0.01, ha="left")
  return _save(fig, save_path)
