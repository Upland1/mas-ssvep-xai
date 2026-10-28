"""Condition-level magnitude-squared coherence between channels (P12, R4, PF-15, PF-16).

Legacy conventions kept on purpose (labelled): features assume fs = 250 Hz although the recordings
are 256 Hz (PF-04), so the band edges live on the fs-250 frequency axis; windows are the raw legacy
windows (no continuous filtering, R3 era B); the gate is the P07 per-script two-tier gate (R5 from P16).

Estimators:
- `compute_condition_coherence` (REPORTED path, R4): concatenate the clean windows of a condition per
  channel, run `scipy.signal.coherence` once per pair, average the bins inside the band.
- `compute_coherence_matrix` (DIAGNOSTIC only, PF-15): per-window coherence; averaging it over windows
  is biased upward at 256 samples / nperseg 128 (about 0.33 for independent noise).

Matrices are `(C, C)`, symmetric, with a NaN diagonal (self-coherence is 1 by definition and is
excluded from every summary). Channel order is the order of the input channels (PF-06).
"""

from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from scipy.signal import coherence

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # legacy label (PF-04)
from src.io.channels import subject_channel_names
from src.io.subject_data import QUALITY_MODES, load_subject
from src.preprocessing.dataset.cv_utils import LEGACY_TRIAL_LENGTHS, build_trial_ids, trial_block_report
from src.preprocessing.signal.quality_check import apply_artifact_quality_pipeline

CONDITION_FREQS = {101: 24.0, 102: 20.0, 103: 15.0, 104: 10.9091, 105: 8.5714}
BASELINE_CONDITION = 201
BASELINE_BAND = (5.0, 35.0)  # broadband baseline: only the PF-16 "before" side
HALF_WIDTH_HZ = 1.0
NPERSEG = 256
DIAG_NPERSEG = 128
# P07 per-script two-tier gate, every threshold explicit (R5 style).
GATE = dict(vpp_min=5.0, vpp_max=120.0, std_min=1.0, std_max=35.0, channel_fail_fraction_thresh=0.5)
_EPS = 1e-9


def band_for_condition(condition: int, half_width: float = HALF_WIDTH_HZ) -> tuple:
  """`(f_c - half_width, f_c + half_width)` on the fs-250 axis (legacy, PF-04)."""
  f = CONDITION_FREQS[int(condition)]
  return (f - half_width, f + half_width)


def band_average(freqs: np.ndarray, coh: np.ndarray, band: tuple) -> np.ndarray:
  """Mean of `coh[..., k]` over the bins with `band[0] <= freqs[k] <= band[1]` (inclusive).

  If no bin falls inside (band narrower than the resolution) the nearest bin is used.
  """
  lo, hi = band
  sel = (freqs >= lo - _EPS) & (freqs <= hi + _EPS)
  if not sel.any():
    sel = np.zeros(len(freqs), dtype=bool)
    sel[int(np.argmin(np.abs(freqs - 0.5 * (lo + hi))))] = True
  return coh[..., sel].mean(axis=-1)


def pairwise_coherence(signal: np.ndarray, fs: float, nperseg: int, noverlap: Optional[int] = None) -> tuple:
  """`(freqs, coh (C, C, F))` of a `(C, N)` signal; one `scipy.signal.coherence` call per pair.

  `noverlap=None` keeps the scipy default (50 %); the aligned diagnostic passes 0. The diagonal holds NaN. Index layout: `coh[i, j] = coh[j, i]` is the pair of channels i, j (R6).
  """
  x = np.asarray(signal, dtype=np.float64)
  n_ch = x.shape[0]
  nper = min(int(nperseg), x.shape[1])
  freqs = None
  out = None
  for i in range(n_ch):
    for j in range(i + 1, n_ch):
      kw = {} if noverlap is None else {"noverlap": noverlap}
      f, c = coherence(x[i], x[j], fs=fs, nperseg=nper, **kw)
      if out is None:
        freqs = f
        out = np.full((n_ch, n_ch, len(f)), np.nan)
      out[i, j] = out[j, i] = c
  if out is None:
    raise ValueError("need at least 2 channels")
  return freqs, out


def concatenate_windows(windows: np.ndarray) -> np.ndarray:
  """`(n, C, T)` -> `(C, n * T)`: the windows of a condition one after another, per channel."""
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got {w.shape}")
  return np.concatenate(list(w), axis=1)


def compute_coherence_matrix(window: np.ndarray, fs: float, band: tuple, nperseg: Optional[int] = None) -> np.ndarray:
  """DIAGNOSTIC (PF-15): band-averaged coherence of ONE `(C, T)` window, `nperseg=min(T, 128)`.

  Averaging this over windows is the historical biased estimator; never use it in reported results (R4).
  """
  w = np.asarray(window, dtype=np.float64)
  nper = min(w.shape[1], DIAG_NPERSEG) if nperseg is None else nperseg
  freqs, coh = pairwise_coherence(w, fs, nper)
  return band_average(freqs, coh, band)


def compute_condition_coherence(windows: np.ndarray, fs: float, band: tuple, nperseg: int = NPERSEG) -> np.ndarray:
  """Condition-level coherence (R4): concatenate the windows, estimate once per pair, band-average."""
  freqs, coh = pairwise_coherence(concatenate_windows(windows), fs, nperseg)
  return band_average(freqs, coh, band)


def mean_offdiag(matrix: np.ndarray) -> float:
  """Mean of the upper-triangle off-diagonal entries (the R-11 summary statistic)."""
  m = np.asarray(matrix)
  return float(np.nanmean(m[np.triu_indices(m.shape[0], k=1)]))


def compute_condition_connectivity(windows: np.ndarray, y: np.ndarray, fs: float = LEGACY_FS_HZ,
                                   nperseg: int = NPERSEG) -> dict:
  """`{condition: (C, C)}` for 101-105 in their own band and 201 in the broadband (PF-16 'before' side)."""
  y = np.asarray(y)
  out = {}
  for c in list(CONDITION_FREQS) + [BASELINE_CONDITION]:
    sel = y == c
    if not sel.any():
      continue
    band = BASELINE_BAND if c == BASELINE_CONDITION else band_for_condition(c)
    out[c] = compute_condition_coherence(windows[sel], fs, band, nperseg)
  return out


def compute_baseline_matched_connectivity(windows: np.ndarray, y: np.ndarray, fs: float = LEGACY_FS_HZ,
                                          nperseg: int = NPERSEG) -> tuple:
  """`({condition: (C, C)}, idx)`: the SAME 201 windows (`idx`) re-scored in each stimulus band (PF-16)."""
  idx = np.flatnonzero(np.asarray(y) == BASELINE_CONDITION)
  if len(idx) == 0:
    raise ValueError("no baseline (201) windows")
  freqs, coh = pairwise_coherence(concatenate_windows(windows[idx]), fs, nperseg)
  return {c: band_average(freqs, coh, band_for_condition(c)) for c in CONDITION_FREQS}, idx


def compute_difference_matrices(stimulus: dict, matched: dict) -> dict:
  """`{condition: stimulus - matched baseline}` for the conditions present in `stimulus`."""
  return {c: stimulus[c] - matched[c] for c in CONDITION_FREQS if c in stimulus}


def per_window_mean_matrix(windows: np.ndarray, fs: float, band: tuple) -> np.ndarray:
  """DIAGNOSTIC (PF-15): `compute_coherence_matrix` averaged over windows (the historical 'before')."""
  return np.mean([compute_coherence_matrix(w, fs, band) for w in windows], axis=0)


def compute_aligned_condition_coherence(windows: np.ndarray, fs: float, band: tuple) -> np.ndarray:
  """DIAGNOSTIC (F2): concatenated coherence with Welch segments aligned to the windows.

  `nperseg = T`, `noverlap = 0`, so no segment spans a window junction (junction discontinuities cannot
  leak low-frequency power into the band). Not the reported estimator.
  """
  w = np.asarray(windows, dtype=np.float64)
  freqs, coh = pairwise_coherence(concatenate_windows(w), fs, w.shape[2], noverlap=0)
  return band_average(freqs, coh, band)


def baseline_broadband_stats(windows: np.ndarray, y: np.ndarray, fs: float = LEGACY_FS_HZ) -> dict:
  """REPORTED R-11 'baseline coherence': gated 201 windows, 5-35 Hz, mean off-diagonal.

  `before` = per-window coherence (nperseg min(T, 128)) averaged over the windows (PF-15 bug, DIAGNOSTIC
  side); `after` = concatenated (nperseg 256, R4); `after_aligned` = window-aligned diagnostic.
  """
  idx = np.flatnonzero(np.asarray(y) == BASELINE_CONDITION)
  if len(idx) == 0:
    raise ValueError("no baseline (201) windows")
  w = np.asarray(windows)[idx]
  return dict(before=mean_offdiag(per_window_mean_matrix(w, fs, BASELINE_BAND)),
              after=mean_offdiag(compute_condition_coherence(w, fs, BASELINE_BAND)),
              after_aligned=mean_offdiag(compute_aligned_condition_coherence(w, fs, BASELINE_BAND)))


def band_bins(fs: float, nperseg: int, band: tuple, true_fs: float = 256.0) -> tuple:
  """`(bins_on_fs_axis, true_hz)` of the Welch bins inside `band` on the fs axis (PF-04 label).

  The recordings are `true_fs` = 256 Hz, so a bin at `f` on the 250 axis is really `f * true_fs / fs`.
  """
  f = np.fft.rfftfreq(nperseg, 1.0 / fs)
  sel = f[(f >= band[0] - _EPS) & (f <= band[1] + _EPS)]
  return [round(float(v), 3) for v in sel], [round(float(v) * true_fs / fs, 3) for v in sel]


# REPORTED = enters the reported result; DIAGNOSTIC = bug demo / sensitivity check, never a result.
COLUMN_LABELS = {
  "condition": "id", "f_c": "id", "band_lo": "id", "band_hi": "id", "n_windows": "id", "n_baseline": "id",
  "mean_raw": "REPORTED (concatenated, R4)",
  "mean_matched_baseline": "REPORTED (same 201 windows re-scored in the band, PF-16 fix)",
  "mean_difference": "REPORTED (stimulus - matched baseline)",
  "baseline_broadband_before": "DIAGNOSTIC side of R-11 baseline (per-window averaged, PF-15 bug)",
  "baseline_broadband_after": "REPORTED R-11 baseline coherence (201, 5-35 Hz, concatenated)",
  "baseline_broadband_after_aligned": "DIAGNOSTIC (window-aligned segments, F2)",
  "mean_baseline_perwindow": "DIAGNOSTIC (per-band per-window averaged, PF-15 bug; secondary 'before')",
  "mean_difference_broadband": "DIAGNOSTIC (stimulus - 5-35 Hz broadband baseline, PF-16 bug)",
  "mean_difference_aligned": "DIAGNOSTIC (window-aligned segments nperseg=T, noverlap=0; junction sensitivity, F2)",
}


def summary_rows(windows: np.ndarray, y: np.ndarray, fs: float = LEGACY_FS_HZ) -> list:
  """One dict per stimulus condition with the R-11 statistics (mean off-diagonal values).

  Keys: see `COLUMN_LABELS` (REPORTED vs DIAGNOSTIC). The per-subject broadband baseline
  (`baseline_broadband_before/after/after_aligned`) is repeated on every row.
  """
  y = np.asarray(y)
  stim = compute_condition_connectivity(windows, y, fs)
  matched, idx = compute_baseline_matched_connectivity(windows, y, fs)
  diff = compute_difference_matrices(stim, matched)
  bb = baseline_broadband_stats(windows, y, fs)
  rows = []
  for c in CONDITION_FREQS:
    if c not in stim:
      continue
    band = band_for_condition(c)
    before = mean_offdiag(per_window_mean_matrix(windows[idx], fs, band))
    raw = mean_offdiag(stim[c])
    aligned = (mean_offdiag(compute_aligned_condition_coherence(windows[y == c], fs, band))
               - mean_offdiag(compute_aligned_condition_coherence(windows[idx], fs, band)))
    rows.append(dict(
      condition=c, f_c=CONDITION_FREQS[c], band_lo=band[0], band_hi=band[1],
      n_windows=int((y == c).sum()), n_baseline=len(idx), mean_raw=raw,
      mean_matched_baseline=mean_offdiag(matched[c]), mean_difference=mean_offdiag(diff[c]),
      baseline_broadband_before=bb["before"], baseline_broadband_after=bb["after"],
      baseline_broadband_after_aligned=bb["after_aligned"],
      mean_baseline_perwindow=before, mean_difference_broadband=raw - bb["after"],
      mean_difference_aligned=aligned))
  return rows


def meta_lines(rows: list, channels: Sequence[str], dropped: Sequence[str], fs: float, nperseg: int = NPERSEG) -> list:
  """Meta text shared by the demo and the analysis: column labels, bands with true bins, channel count."""
  out = [f"channels ({len(channels)}) = {list(channels)}; dropped = {list(dropped)}",
         f"fs axis = {fs:g} Hz ({'true recording rate' if fs == 256.0 else 'legacy, PF-04'}); recordings are 256 Hz, so a bin at f on this axis is f*256/{fs:g} Hz"]
  for c in CONDITION_FREQS:
    b = band_for_condition(c)
    bins, true = band_bins(fs, nperseg, b)
    out.append(f"band {c}: ({b[0]:.4f}, {b[1]:.4f}) on the fs-{fs:g} axis; bins {bins} (axis Hz) = {true} (true Hz)")
  out.append("column labels:")
  out += [f"  {k}: {v}" for k, v in COLUMN_LABELS.items()]
  if rows:
    out.append(f"secondary diagnostic: mean of the 5 per-band matched baselines, before "
               f"{np.mean([r['mean_baseline_perwindow'] for r in rows]):.4f}, after "
               f"{np.mean([r['mean_matched_baseline'] for r in rows]):.4f} (cannot replace the 5-35 Hz baseline, A2)")
  return out


def load_legacy_selection(processed_dir: Path, subject: str, channel_names: Optional[Sequence[str]] = None) -> dict:
  """PRE-gate legacy windows of 101-105 and 201 with trial ids (P13, PF-03).

  Trial ids come from `build_trial_ids` on the full pre-gate labels (202 included in the walk), then the
  same condition selection as the windows. Returns `windows`, `y`, `trial_ids`, `channel_names`,
  `trial_ids_approximate` (True when a pre-gate block is not a multiple of its trial length, P11 D-2).
  """
  d = Path(processed_dir) / subject
  X = np.load(d / "X_time_windows.npy")
  y_all = np.load(d / "y_labels.npy").astype(np.int64).reshape(-1)
  if X.ndim != 3 or len(X) != len(y_all):
    raise ValueError(f"{subject}: X_time_windows {X.shape} vs y {y_all.shape}")
  ids_all = build_trial_ids(y_all, LEGACY_TRIAL_LENGTHS, warn=False)
  approx = trial_block_report(y_all, ids_all, LEGACY_TRIAL_LENGTHS)["approximate"]
  keep = np.isin(y_all, list(CONDITION_FREQS) + [BASELINE_CONDITION])
  names = list(channel_names) if channel_names is not None else subject_channel_names(processed_dir, subject, X.shape[1])
  return dict(windows=X[keep], y=y_all[keep], trial_ids=ids_all[keep], channel_names=names,
              trial_ids_approximate=bool(approx))


def gate_selection(sel: dict) -> dict:
  """ONE P07 two-tier gate over a `load_legacy_selection` dict, every threshold explicit."""
  return apply_artifact_quality_pipeline(sel["windows"], sel["y"], sel["channel_names"], verbose=False, **GATE)


def load_gated_conditions(processed_dir: Path, subject: str, channel_names: Optional[Sequence[str]] = None) -> dict:
  """Legacy windows of 101-105 and 201 after ONE P07 gate decision over their union (202 excluded).

  Returns `windows (n, C', T)`, `y`, `trial_ids` (pre-gate ids masked like the windows, PF-03),
  `trial_ids_approximate`, `channels_kept`, `channels_dropped`, `counts` (per condition:
  total / clean / rejected) and `n_total_windows`. Stimulus and baseline share the same channels.
  """
  sel = load_legacy_selection(processed_dir, subject, channel_names)
  y = sel["y"]
  q = gate_selection(sel)
  counts = {}
  for c in list(CONDITION_FREQS) + [BASELINE_CONDITION]:
    n_tot, n_ok = int((y == c).sum()), int((q["y_clean"] == c).sum())
    counts[c] = dict(total=n_tot, clean=n_ok, rejected=n_tot - n_ok)
  return dict(windows=q["windows_clean"], y=q["y_clean"], channels_kept=q["channels_kept"],
              channels_dropped=q["channels_dropped"], counts=counts, n_total_windows=len(y),
              trial_ids=sel["trial_ids"][np.asarray(q["valid_mask"]).astype(bool)],
              trial_ids_approximate=sel["trial_ids_approximate"])


# ------------------------------------------------------------------ P16: the loader of every connectivity script

CONNECTIVITY_CONDITIONS = tuple(CONDITION_FREQS) + (BASELINE_CONDITION,)


def load_condition_windows(data_root, subject: str, quality_mode: str = "shared", fs_override: Optional[float] = None,
                           scalp: Optional[Sequence[str]] = None) -> dict:
  """Clean windows of 101-105 and 201 of `<data_root>/<subject>/` through `load_subject` (P16.7, R3, R5, R8).

  `data_root` is a legacy root (`data/processed`: fs 250 assumed, ids reconstructed, per-script P07 gate, the
  pre-P16 numbers) or a built root (`data/processed_<filter_mode>`: fs from the metadata, true trial ids,
  the shared quality mask of `quality_mode`, the kept channels). On a legacy root this returns the same arrays
  as `load_gated_conditions` + `load_legacy_selection` (tested), which stay as the pre-P16 reference.

  Returns `windows (n, C', T)`, `y`, `trial_ids` (aligned with the windows; true ids on built folders),
  `trial_ids_approximate`, `channels_kept`, `channels_dropped`, `channel_names` (= kept), `counts` (per condition
  total / clean / rejected), `n_total_windows` (selected before the quality decision), `fs`, `fs_source`,
  `built`, `source`, `filter_mode`, `quality_mode` and `quality` (an identity pass-through in the format of
  `apply_artifact_quality_pipeline`: the decision was already taken, so `valid_mask` is all ones over the
  returned windows and the ids are not masked a second time).
  """
  d = load_subject(Path(data_root) / subject, conditions=CONNECTIVITY_CONDITIONS, quality_mode=quality_mode,
                   fs_override=fs_override, scalp=scalp,
                   thresholds={k: GATE[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")},
                   channel_fail_fraction=GATE["channel_fail_fraction_thresh"])  # R5: explicit, the P13 GATE
  y_all = np.load(Path(data_root) / subject / "y_labels.npy").astype(np.int64).reshape(-1)
  y_sel = y_all[np.asarray(d["quality"]["rows"])]
  y = np.asarray(d["y"])
  counts = {}
  for c in CONNECTIVITY_CONDITIONS:
    n_tot, n_ok = int((y_sel == c).sum()), int((y == c).sum())
    counts[c] = dict(total=n_tot, clean=n_ok, rejected=n_tot - n_ok)
  approx = bool(d["trial_ids_approximate"])
  if not d["built"]:  # the pre-P16 flag: block check on the full pre-gate labels (202 included in the walk)
    ids_all = build_trial_ids(y_all, LEGACY_TRIAL_LENGTHS, warn=False)
    approx = bool(trial_block_report(y_all, ids_all, LEGACY_TRIAL_LENGTHS)["approximate"])
  kept, dropped = list(d["channel_names"]), list(d["channels_dropped"])
  identity = dict(windows_clean=d["X"], y_clean=y, valid_mask=np.ones(len(y), dtype=np.int8),
                  channels_kept=kept, channels_dropped=dropped)
  return dict(windows=d["X"], y=y, trial_ids=np.asarray(d["trial_ids"]), trial_ids_approximate=approx,
              channels_kept=kept, channels_dropped=dropped, channel_names=kept, counts=counts,
              n_total_windows=int(len(y_sel)), fs=float(d["fs"]), fs_source=d["fs_source"], built=bool(d["built"]),
              source=d["source"], filter_mode=d["filter_mode"], quality_mode=quality_mode, quality=identity)


def source_text(sel: dict, legacy_text: str) -> str:
  """Report header for a loaded subject: `legacy_text` unchanged for a legacy folder at the assumed fs, else the
  build, the fs and where it came from, and the quality mode."""
  if not sel["built"] and sel["fs_source"] == "legacy-assumed":
    return legacy_text
  return f"{sel['source']}; fs {sel['fs']:g} Hz ({sel['fs_source']}); quality {sel['quality_mode']}"
