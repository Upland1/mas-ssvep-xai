"""P16.2 windowing: window index vs the P02 legacy starts, stride, trial ids, band_windows modes, banks (256 Hz)."""

import numpy as np
import pytest
from scipy.signal import butter, sosfiltfilt

from src.features.ssvep.psd_extraction import process_condition_windows_with_baseline
from src.preprocessing import windowing as W

FS = 256.0
STIM = (101, 102, 103, 104, 105)
ORDER = (201, 202, *STIM)


def make_mark(n_trials=10, truncate_last=False, seed=0, fs=FS, tail_s=6.0):
  """Protocol of 01_DATA_SPEC section 3: 201 at t, 202 at t+2, 10x at t+5, 15 s per trial, first 201 at 5 s."""
  rng = np.random.default_rng(seed)
  codes = rng.permutation(np.repeat(STIM, int(np.ceil(n_trials / 5))))[:n_trials]
  T = int((5 + 15 * n_trials + tail_s) * fs)
  m = np.zeros(T)
  for i, c in enumerate(codes):
    t = 5 + 15 * i
    for off, code in ((0, 201), (2, 202), (5, c)):
      m[int((t + off) * fs)] = code
  if truncate_last:                      # cut inside the last stimulus period
    m = m[: int((5 + 15 * (n_trials - 1) + 5 + 3) * fs)]
  return m


def legacy_starts(m, fs=FS):
  recs = process_condition_windows_with_baseline(
    np.zeros((1, len(m))), m, fs, target_conditions=STIM, cue_condition=202, cross_condition=201,
    vpp_thresh=np.inf, std_range=(-np.inf, np.inf), vpp_min=-np.inf)
  return np.asarray([r["start"] for c in ORDER for r in recs[c]]), \
    np.asarray([c for c in ORDER for _ in recs[c]])


def test_stride_none_reproduces_legacy_starts_and_counts():
  """Known answer: stride=None gives exactly the P02 starts/labels; a full 40-trial session gives 80/40/200."""
  m = make_mark(n_trials=40)
  idx = W.build_window_index(m, FS, STIM)
  s, y = legacy_starts(m)
  assert np.array_equal(idx.starts, s) and np.array_equal(idx.labels, y)
  assert (idx.labels == 201).sum() == 80 and (idx.labels == 202).sum() == 40
  assert sum((idx.labels == c).sum() for c in STIM) == 200


def test_truncated_last_trial_dropped_like_legacy():
  m = make_mark(n_trials=10, truncate_last=True)
  idx = W.build_window_index(m, FS, STIM)
  s, y = legacy_starts(m)
  assert np.array_equal(idx.starts, s) and np.array_equal(idx.labels, y)
  assert sum((idx.labels == c).sum() for c in STIM) == 5 * 9          # 9 complete stimulus trials
  assert any(k["why"] == "ends after the recording" for k in idx.skipped)


def test_trial_ids_one_per_segment_and_sub_idx():
  m = make_mark(n_trials=10)
  idx = W.build_window_index(m, FS, STIM)
  n_seg = 10 * 3                                                       # 201, 202, 10x per trial
  assert len(np.unique(idx.trial_ids)) == n_seg
  for t in np.unique(idx.trial_ids):
    r = idx.trial_ids == t
    k = r.sum()
    assert np.array_equal(idx.sub_idx[r], np.arange(k))
    assert np.array_equal(idx.offsets[r], np.arange(k) * 256)
    assert len(set(idx.labels[r])) == 1
    assert np.array_equal(idx.starts[r], idx.starts[r][0] + idx.offsets[r])
  assert np.all(np.diff(idx.trial_ids) >= 0)                           # increasing in row order


def test_cue_window_shares_the_fixation_trial_id_pf13():
  """The 202 window is the second 201 sub-window (same samples): the same group (PF-13)."""
  m = make_mark(n_trials=6)
  assert len(np.unique(W.build_window_index(m, FS, STIM).trial_ids)) == 6 * 3      # default: one id per segment
  idx = W.build_window_index(m, FS, STIM, cue_shares_cross_id=True)
  assert len(np.unique(idx.trial_ids)) == 6 * 2                        # 201+202 share, 10x separate
  for s in idx.starts[idx.labels == 202]:
    twin = (idx.labels == 201) & (idx.starts == s)
    assert twin.sum() == 1
    assert idx.trial_ids[twin][0] == idx.trial_ids[(idx.labels == 202) & (idx.starts == s)][0]


def test_stride_half_second_windows_inside_segments_offsets_restart():
  m = make_mark(n_trials=5)
  idx = W.build_window_index(m, FS, STIM, stride_sec=0.5)
  # 5 s stimulus: starts 0, .5, ..., 4.0 -> 9 windows; 201 (2 s): 3 windows; 202 (1 s): 1
  assert W.windows_per_segment(5 * 256, 256, 128) == 9
  for lab, k in ((201, 3), (202, 1), *[(c, 9) for c in STIM]):
    for t in np.unique(idx.trial_ids[idx.labels == lab]):
      r = (idx.trial_ids == t) & (idx.labels == lab)
      assert r.sum() == k
      assert idx.offsets[r][0] == 0 and idx.offsets[r][-1] == (k - 1) * 128
  s5 = idx.labels >= 101
  seg_start = idx.starts - idx.offsets
  stim = np.isin(idx.labels, STIM)
  assert np.all(idx.starts[stim] + 256 <= seg_start[stim] + 5 * 256)    # fully inside
  assert idx.offsets[stim].min() == 0


def test_window_index_uses_fs_given_not_a_literal():
  """PF-04: the window length follows fs (256 Hz -> 256 samples, 250 Hz -> 250)."""
  assert W.build_window_index(make_mark(3, fs=250.0), 250.0, STIM).starts.size == 3 * (2 + 1 + 5)
  m = make_mark(2)
  a = W.build_window_index(m, 256.0, STIM)
  assert np.all(np.diff(a.starts[a.labels == 201][:2]) == 256)


def test_invalid_arguments_raise():
  with pytest.raises(ValueError):
    W.build_window_index(make_mark(2), 0.0, STIM)
  with pytest.raises(ValueError):
    W.build_window_index(make_mark(2), FS, STIM, stride_sec=0.0)
  with pytest.raises(ValueError):
    W.windows_per_segment(10, 0, 1)


def test_cut_windows_known_answer():
  x = np.arange(2 * 100, dtype=float).reshape(2, 100)
  w = W.cut_windows(x, np.array([0, 10, 90]), 10)
  assert w.shape == (3, 2, 10)
  assert np.array_equal(w[1, 1], x[1, 10:20])
  with pytest.raises(ValueError):
    W.cut_windows(x, np.array([95]), 10)


def _tone(f, T, fs=FS, C=2, seed=0):
  t = np.arange(T) / fs
  rng = np.random.default_rng(seed)
  return np.stack([np.sin(2 * np.pi * f * t + p) for p in (0.0, 1.0)][:C]) + 0.1 * rng.normal(size=(C, T))


def test_band_windows_continuous_equals_filter_then_cut_and_layout():
  """Known answer: continuous mode is exactly sosfiltfilt of the whole recording, then cut; layout (n, B, C, T)."""
  x = _tone(15.0, 20 * 256)
  starts = np.array([3 * 256, 9 * 256 + 17])
  bank = W.fbcsp_filter_bank(FS)
  out = W.band_windows(x, starts, 256, bank, "continuous")
  assert out.shape == (2, 5, 2, 256)
  sos = butter(4, [13, 17], btype="band", fs=FS, output="sos")
  ref = sosfiltfilt(sos, x, axis=-1)
  assert np.array_equal(out[1, 1, 0], ref[0, starts[1]:starts[1] + 256])
  # R6: a 15 Hz tone lands in band 1 (13-17), not in band 0 (7-12) or 4 (38-52)
  rms = np.sqrt((out ** 2).mean(axis=(0, 2, 3)))
  assert rms.argmax() == 1 and rms[1] > 10 * rms[0] and rms[1] > 10 * rms[4]


def test_per_window_edge_error_much_larger_than_centre_pf14():
  """PF-14: per-window filtering of the 13-17 Hz band is wrong at the first/last 100 ms (ratio >> 1);
  the continuous output is the reference. Fails on a build that filters per window and calls it continuous."""
  rng = np.random.default_rng(1)
  x = _tone(15.0, 60 * 256, C=1) + 0.5 * rng.normal(size=(1, 60 * 256))
  starts = np.arange(2 * 256, 55 * 256, 256)
  bank = [W.fbcsp_filter_bank(FS)[1]]
  cont = W.band_windows(x, starts, 256, bank, "continuous")[:, 0, 0]
  pw = W.band_windows(x, starts, 256, bank, "per_window")[:, 0, 0]
  err = np.abs(pw - cont) / np.sqrt((cont ** 2).mean())
  e = int(0.1 * FS)
  edge = np.concatenate([err[:, :e], err[:, -e:]], axis=1).mean()
  centre = err[:, 2 * e:-2 * e].mean()
  assert edge / centre > 3.0, (edge, centre)
  assert not np.allclose(pw, cont, atol=1e-3)


def test_banks_follow_fs_and_edges():
  """PF-04: edges are Hz values, valid at 256 Hz; the upper edges cap at nyquist - 1."""
  b = W.fbcsp_filter_bank(FS)
  assert [(f.low, f.high) for f in b] == [(7, 12), (13, 17), (18, 26), (27, 36), (38, 52)]
  c = W.fbcca_filter_bank(FS)
  assert [f.low for f in c] == [6.0, 14.0, 22.0] and all(f.high == 90.0 for f in c)
  assert W.fbcsp_filter_bank(100.0)[-1].high == 49.0
  # a 24 Hz tone: the 38-52 band passes ~nothing, the 18-26 band passes it, at the fs used to design
  t = np.arange(8 * 256) / FS
  x = np.sin(2 * np.pi * 24 * t)[None]
  out = W.band_windows(x, np.array([3 * 256]), 256, b, "continuous")[0, :, 0]
  assert np.sqrt((out ** 2).mean(axis=-1)).argmax() == 2


def test_select_clean_bands_and_mode_validation():
  b = np.arange(4 * 2 * 3 * 5, dtype=float).reshape(4, 2, 3, 5)
  out = W.select_clean_bands(b, np.array([1, 0, 1, 0]), [0, 2])
  assert out.shape == (2, 2, 2, 5) and np.array_equal(out[1, :, 1], b[2, :, 2])
  with pytest.raises(ValueError):
    W.select_clean_bands(b, np.ones(3))
  with pytest.raises(ValueError):
    W.band_windows(np.zeros((1, 600)), np.array([0]), 256, W.fbcsp_filter_bank(FS), "other")
