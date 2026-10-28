"""P16.4 shared quality decision: ringing time, artifact guard, tiers, explicit thresholds (R5)."""

import numpy as np
import pytest

from src.preprocessing import window_quality as WQ
from src.preprocessing.windowing import cut_windows, fbcsp_filter_bank

FS = 256.0
PARAMS = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0, "channel_fail_fraction": 0.5,
          "artifact_block_sec": 0.25, "guard_sec": 1.0, "guard_rel_amplitude": 0.01}


def boxcar(n):
  return lambda z: np.convolve(z[0], np.ones(n) / n, mode="same")[None]


def test_ringing_time_boxcar_known_answer():
  """An 11-tap centred boxcar has h != 0 exactly for |i - c| <= 5: ringing 5 samples = 5 / fs (1 sample)."""
  assert WQ.ringing_time_sec([boxcar(11)], FS) == pytest.approx(5 / FS, abs=1 / FS)
  assert WQ.ringing_time_sec([boxcar(11), boxcar(31)], FS) == pytest.approx(15 / FS, abs=1 / FS)


def test_ringing_time_butterworth_matches_independent_span():
  from scipy.signal import butter, sosfiltfilt
  sos = butter(4, [13, 17], btype="band", fs=FS, output="sos")
  imp = np.zeros(2 * 20 * 256 + 1)
  imp[20 * 256] = 1
  h = sosfiltfilt(sos, imp)
  ref = np.abs(np.flatnonzero(np.abs(h) > 0.01 * np.abs(h).max()) - 20 * 256).max()
  got = WQ.ringing_time_sec([sos], FS, max_sec=20)
  assert abs(got * FS - ref) <= 1
  # a lower band rings longer, the broadband 1 Hz edge longest
  assert WQ.ringing_time_sec([fbcsp_filter_bank(FS)[0]], FS) > WQ.ringing_time_sec([fbcsp_filter_bank(FS)[4]], FS)


def _signal(T=60 * 256, C=3, seed=0, std=5.0):
  return np.random.default_rng(seed).normal(0, std, size=(C, T))


def _gate(x, params=PARAMS, labels=None, starts=None, names=("A", "B", "C")):
  starts = np.arange(0, x.shape[1] - 255, 256) if starts is None else starts
  w = cut_windows(x, starts, 256)
  return starts, WQ.subject_quality_gate(w, starts, x, FS, list(names), [], params, labels)


def test_planted_spike_rejects_windows_within_guard_only():
  """Known answer: spike at 30 s + 100 samples (500 uV, one channel). Its 64-sample block is dilated by 1 s:
  region [29*256+64, 31*256+128). Windows 29 and 31 overlap it -> reason 2; window 30 holds it -> reason 1;
  every other window valid; valid_mask_no_guard keeps 29 and 31."""
  x = _signal()
  x[1, 30 * 256 + 100] += 500.0
  starts, q = _gate(x)
  k = np.arange(len(starts))
  assert q["reason"][29] == 2 and q["reason"][31] == 2 and q["reason"][30] == 1
  others = (k != 29) & (k != 30) & (k != 31)
  assert np.all(q["reason"][others] == 0) and np.all(q["valid_mask"][others] == 1)
  assert q["valid_mask"][[29, 30, 31]].tolist() == [0, 0, 0]
  assert q["valid_mask_no_guard"][[29, 31]].tolist() == [1, 1] and q["valid_mask_no_guard"][30] == 0
  assert q["n_artifact_blocks"] == 1
  assert q["artifact_fraction"] == pytest.approx(64 / x.shape[1])
  assert q["guard_sec"] == 1.0 and q["guard_samples"] == 256


def test_guard_zero_equals_no_guard_and_clean_signal_all_valid():
  x = _signal()
  x[1, 30 * 256 + 100] += 500.0
  _, q0 = _gate(x, {**PARAMS, "guard_sec": 0.0})
  assert np.array_equal(q0["valid_mask"], q0["valid_mask_no_guard"])
  _, qc = _gate(_signal(seed=3))
  assert qc["valid_mask"].all() and (qc["reason"] == 0).all()


def test_auto_guard_is_the_longest_ringing_time():
  x = _signal(T=20 * 256)
  w = cut_windows(x, np.array([0]), 256)
  q = WQ.subject_quality_gate(w, np.array([0]), x, FS, list("ABC"), [boxcar(11), boxcar(31)],
                              {**PARAMS, "guard_sec": "auto"})
  assert q["guard_samples"] == 15 and q["guard_sec"] == pytest.approx(15 / FS)


def test_bad_channel_dropped_and_not_used_by_the_guard():
  """Tier 1: channel C (std 80 uV: Vpp > 120 in every window) fails 100 % > 50 % -> dropped; windows are
  judged on A, B only, and C's huge blocks do not flag artifacts (the guard uses kept channels)."""
  x = _signal()
  x[2] = np.random.default_rng(9).normal(0, 80.0, x.shape[1])
  starts, q = _gate(x)
  assert q["channels_dropped"] == ["C"] and q["channels_kept"] == ["A", "B"]
  assert q["channels_kept_idx"].tolist() == [0, 1]
  assert q["valid_mask"].all() and q["n_artifact_blocks"] == 0
  assert q["channel_stats"]["C"]["fail_fraction"] == 1.0


def test_exactly_half_failing_keeps_the_channel():
  x = _signal(T=40 * 256)
  x[0, :20 * 256] *= 30.0                                  # fails in exactly 20 of 40 windows
  _, q = _gate(x)
  assert q["channel_stats"]["A"]["fail_fraction"] == 0.5 and q["channels_dropped"] == []


def test_every_threshold_is_required():
  x = _signal(T=5 * 256)
  w = cut_windows(x, np.array([0]), 256)
  for key in WQ.PARAM_KEYS:
    bad = {k: v for k, v in PARAMS.items() if k != key}
    with pytest.raises(ValueError, match="explicitly"):
      WQ.subject_quality_gate(w, np.array([0]), x, FS, list("ABC"), [], bad)


def test_rejections_by_label_counts():
  x = _signal()
  x[1, 30 * 256 + 100] += 500.0
  starts = np.arange(0, x.shape[1] - 255, 256)
  labels = np.where(starts < 30 * 256, 101, 102)
  _, q = _gate(x, labels=labels)
  r = q["rejections_by_label"]
  assert r[101]["guard"] == 1 and r[102]["guard"] == 1 and r[102]["own_gate"] == 1
  assert r[101]["total"] == 30 and r[102]["valid"] == r[102]["total"] - 2


def test_params_from_config():
  cfg = {"quality": {"vpp_range_uv": [5.0, 120.0], "std_range_uv": [1.0, 35.0], "channel_fail_fraction": 0.5,
                     "artifact_block_sec": 0.25, "guard_sec": "auto", "guard_rel_amplitude": 0.01}}
  p = WQ.quality_params_from_config(cfg)
  assert p == {**PARAMS, "guard_sec": "auto"}
  del cfg["quality"]["guard_sec"]
  with pytest.raises(ValueError, match="guard_sec"):
    WQ.quality_params_from_config(cfg)
