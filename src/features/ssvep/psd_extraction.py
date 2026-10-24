"""Legacy condition windows and periodogram features (P02, mas/01_DATA_SPEC.md section 5.1).

`process_condition_windows_with_baseline` cuts the condition segments of an
already broadband-filtered continuous recording (filter first, then window: R3),
`extract_clean_subwindows_psd` slices each segment into 1 s sub-windows, gates
them with the legacy raw limits and computes their periodograms, and
`prepare_feature_matrix` stacks the records into the saved arrays
(`X_psd_features`, `X_time_windows`, `y_labels`).

Record format (one dict per accepted sub-window): `time_data (C, n)`,
`vpp (C,)`, `std (C,)`, `psd (C, F)`, `freqs (F,)`, `sub_index` (position in
its segment); records from `process_condition_windows_with_baseline` also carry
`condition`, `onset` (event onset sample) and `start` (absolute start sample).
"""

from typing import Optional, Sequence

import numpy as np
from scipy.signal import periodogram

from src.preprocessing.signal.quality_check import (
  ensure_quality_stats, merge_quality_stats, new_quality_stats, update_quality_stats,
  window_quality_flags)

TARGET_CONDITIONS = (101, 102, 103, 104, 105)
FEATURE_CONDITIONS = (201, 202, 101, 102, 103, 104, 105)


def find_event_onsets(mark: np.ndarray, code: int) -> np.ndarray:
  """Onset samples of `code` in a MARK channel (mas/01_DATA_SPEC.md section 3).

  Onsets are the samples where `mark == code` and `diff(mark, prepend=0) != 0`,
  so a single-sample pulse and a multi-sample plateau each give one onset (its
  first sample). Fallback (roadmap P02.2): if no such edge is found, the first
  sample of every contiguous plateau of `code`. Under the section 3 rule every
  plateau starts with an edge, so the fallback only matters for MARK signals
  that break that rule; it is kept for fidelity to the roadmap.
  """
  m = np.asarray(mark, dtype=np.float64).reshape(-1)
  is_code = m == code
  onsets = np.flatnonzero(is_code & (np.diff(m, prepend=0.0) != 0))
  if onsets.size == 0 and is_code.any():
    idx = np.flatnonzero(is_code)
    onsets = idx[np.concatenate(([True], np.diff(idx) > 1))]
  return onsets.astype(np.int64)


def extract_clean_subwindows_psd(segment: np.ndarray, fs: float, sub_window_sec: float = 1.0,
                                 vpp_thresh: float = 200.0, std_range: tuple = (0.5, 60.0),
                                 quality_stats: Optional[dict] = None,
                                 vpp_min: float = 0.5) -> list:
  """Gate the 1 s sub-windows of one segment and compute their periodograms.

  `segment` is `(C, T)`; it is sliced into `T // n` consecutive sub-windows of
  `n = int(sub_window_sec * fs)` samples (a shorter remainder is dropped). Each
  sub-window is gated by `validate_eeg_windows` semantics with
  `vpp_min=vpp_min, vpp_max=vpp_thresh, std_min=std_range[0],
  std_max=std_range[1]`, every threshold passed explicitly (PF-07: the shared
  default `vpp_min=5.0` never reaches this legacy gate). Accepted sub-windows
  become records `{time_data, vpp, std, psd, freqs, sub_index}` in time order,
  with `freqs, psd = scipy.signal.periodogram(x, fs=fs, axis=-1)` (defaults:
  boxcar window, constant detrend, density scaling; 1 Hz bins at n = fs).
  `quality_stats`, if given, is updated in place (`quality_check.new_quality_stats`).
  """
  x = np.asarray(segment, dtype=np.float64)
  if x.ndim != 2:
    raise ValueError(f"segment must be (C, T), got shape {x.shape}")
  n = int(sub_window_sec * fs)
  if n <= 0:
    raise ValueError(f"sub-window of {sub_window_sec} s at fs {fs} has no samples")
  n_sub = x.shape[1] // n
  windows = x[:, :n_sub * n].reshape(x.shape[0], n_sub, n).transpose(1, 0, 2)
  flags = window_quality_flags(windows, vpp_min=vpp_min, vpp_max=vpp_thresh,
                               std_min=std_range[0], std_max=std_range[1])
  if quality_stats is not None:
    update_quality_stats(quality_stats, flags)
  records = []
  for k in np.flatnonzero(flags["valid"] == 1):
    w = windows[k].copy()
    freqs, psd = periodogram(w, fs=fs, axis=-1)
    records.append({"time_data": w, "vpp": flags["vpp"][k].copy(), "std": flags["std"][k].copy(),
                    "psd": psd, "freqs": freqs, "sub_index": int(k)})
  return records


def process_condition_windows_with_baseline(
    eeg: np.ndarray, mark: np.ndarray, fs: float,
    target_conditions: Sequence[int] = TARGET_CONDITIONS, cue_condition: int = 202,
    cross_condition: int = 201, sub_window_sec: float = 1.0, vpp_thresh: float = 200.0,
    std_range: tuple = (0.5, 60.0), stim_duration_sec: float = 5.0,
    cue_lookback_sec: float = 1.0, quality_stats: Optional[dict] = None,
    vpp_min: float = 0.5, cross_duration_sec: float = 2.0) -> dict:
  """Gated sub-window records of every condition segment of a continuous recording.

  `eeg` is the broadband-filtered continuous signal `(C, T)` (filter before
  calling: R3); `mark` the MARK channel `(T,)`; `fs` the header rate. Onsets by
  `find_event_onsets`. Segments (`L(s) = int(s * fs)` samples):

  - `cue_condition` (202): `[onset - L(cue_lookback_sec), onset)`, kept only if
    complete (start >= 0). This second lies at the end of the fixation period,
    before the cue pulse (PF-13); it is kept as the historical definition and
    is never a no-stimulus baseline.
  - each of `target_conditions` (101-105): `[onset, onset + L(stim_duration_sec))`,
    kept only if it fits the recording.
  - `cross_condition` (201): `[onset, onset + L(cross_duration_sec))` (2.0 s),
    kept only if it fits.

  Each segment goes through `extract_clean_subwindows_psd` with the given
  thresholds and `vpp_min` passed explicitly (PF-07). Returns
  `{code: [records in time order]}` with keys `cross_condition`,
  `cue_condition`, then `target_conditions` (empty lists included). Records
  carry `condition`, `onset` and `start`. `quality_stats`, if given, receives
  per-condition counts, every rejected sub-window and every skipped segment.
  """
  x = np.asarray(eeg, dtype=np.float64)
  m = np.asarray(mark).reshape(-1)
  if x.ndim != 2:
    raise ValueError(f"eeg must be (C, T), got shape {x.shape}")
  if m.size != x.shape[1]:
    raise ValueError(f"mark has {m.size} samples, eeg {x.shape[1]}")
  n_samples = x.shape[1]
  n_sub = int(sub_window_sec * fs)
  if quality_stats is not None:
    ensure_quality_stats(quality_stats)

  plan = [(int(cross_condition), 0, int(cross_duration_sec * fs)),
          (int(cue_condition), -int(cue_lookback_sec * fs), int(cue_lookback_sec * fs))]
  plan += [(int(c), 0, int(stim_duration_sec * fs)) for c in target_conditions]

  out: dict = {}
  for code, offset, length in plan:
    recs = out.setdefault(code, [])
    for onset in find_event_onsets(m, code):
      onset = int(onset)
      start = onset + offset
      if start < 0 or start + length > n_samples:
        if quality_stats is not None:
          why = "starts before the recording" if start < 0 else "ends after the recording"
          quality_stats["skipped_segments"].append(
            {"condition": code, "onset": onset, "why": why})
        continue
      seg = x[:, start:start + length]
      local = new_quality_stats() if quality_stats is not None else None
      seg_recs = extract_clean_subwindows_psd(
        seg, fs, sub_window_sec=sub_window_sec, vpp_thresh=vpp_thresh,
        std_range=std_range, quality_stats=local, vpp_min=vpp_min)
      if quality_stats is not None:
        merge_quality_stats(quality_stats, local, condition=code, onset=onset,
                            segment_start=start, sub_window_samples=n_sub)
      for r in seg_recs:
        r.update({"condition": code, "onset": onset, "start": start + r["sub_index"] * n_sub})
        recs.append(r)
  return out


def prepare_feature_matrix(records: dict, target_conditions: Sequence[int] = FEATURE_CONDITIONS,
                           freq_range: tuple = (5, 35)) -> tuple:
  """Stack records into `(X_psd, X_time, y)` (mas/01_DATA_SPEC.md section 5.1).

  `records` maps condition code -> list of records (as returned by
  `process_condition_windows_with_baseline`). Conditions are concatenated in
  the order of `target_conditions`, each in its list order (time order);
  codes not listed are ignored. `X_psd` `(n, C * F)` float64: each record's
  `psd[:, (freqs >= lo) & (freqs <= hi)]` (inclusive), flattened channel-major,
  so feature `c * F + j` is channel c, j-th bin (31 bins and 217 features for 7
  channels at fs 256). `X_time` `(n, C, T)` float64, `y` `(n,)` int64. With no
  records: shapes `(0, 0)`, `(0, 0, 0)`, `(0,)`. Raises ValueError when records
  differ in shape or in their masked frequency bins.
  """
  lo, hi = freq_range
  psd_rows, time_rows, labels = [], [], []
  ref_freqs = None
  for code in target_conditions:
    for r in records.get(code, []):
      f = np.asarray(r["freqs"])
      sel = (f >= lo) & (f <= hi)
      if ref_freqs is None:
        ref_freqs = f[sel]
      elif not np.array_equal(f[sel], ref_freqs):
        raise ValueError(f"record of condition {code} has different PSD bins in {freq_range}")
      psd_rows.append(np.asarray(r["psd"], dtype=np.float64)[:, sel].reshape(-1))
      time_rows.append(np.asarray(r["time_data"], dtype=np.float64))
      labels.append(int(code))
  if not labels:
    return np.zeros((0, 0)), np.zeros((0, 0, 0)), np.zeros(0, dtype=np.int64)
  shapes = {t.shape for t in time_rows}
  if len(shapes) != 1:
    raise ValueError(f"records have different time_data shapes {sorted(shapes)}")
  return np.stack(psd_rows), np.stack(time_rows), np.asarray(labels, dtype=np.int64)
