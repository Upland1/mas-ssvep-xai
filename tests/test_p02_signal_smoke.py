"""P02 builder smoke tests (signal-processing): gate, PF-07, segments, feature layout, plots.

Synthetic data only. The independent known-answer suite is the synthetic-tester's.
"""

import numpy as np
import pytest

from src.features.ssvep.psd_extraction import (
  extract_clean_subwindows_psd, find_event_onsets, prepare_feature_matrix,
  process_condition_windows_with_baseline)
from src.preprocessing.signal.quality_check import (
  filter_dataset, new_quality_stats, segment_and_validate_eeg, summarize_window_quality,
  validate_eeg_windows, window_quality_flags)

FS = 256


def _sine(amp, f=10.0, n=FS, n_ch=3):
  t = np.arange(n) / FS
  return np.tile(amp * np.sin(2 * np.pi * f * t + 0.3), (n_ch, 1))


def _recording(n_trials=10, n_ch=7, pulse=1):
  """MARK with the section-3 timing; channel c carries a sinusoid at 5 + 3c Hz."""
  codes = [101, 102, 103, 104, 105] * (n_trials // 5)
  T = 5 * FS + n_trials * 15 * FS
  mark = np.zeros(T)
  for i, c in enumerate(codes):
    t = 5 * FS + i * 15 * FS
    for off, code in [(0, 201), (2, 202), (4, 203), (5, c), (10, 200)]:
      mark[t + off * FS:t + off * FS + pulse] = code
  tt = np.arange(T) / FS
  eeg = np.vstack([10 * np.sin(2 * np.pi * (5 + 3 * ch) * tt) for ch in range(n_ch)])
  return eeg, mark


def test_gate_bounds_inclusive_and_every_channel():
  w = np.stack([_sine(1.0), _sine(1.0)])
  flags = window_quality_flags(w, vpp_min=0.0, vpp_max=np.inf, std_min=0.0, std_max=np.inf)
  vpp, std = flags["vpp"][0, 0], flags["std"][0, 0]
  assert validate_eeg_windows(w, vpp_min=vpp, vpp_max=vpp, std_min=std, std_max=std).tolist() == [1, 1]
  w[1, 2] *= 100
  mask = validate_eeg_windows(w, vpp_min=vpp, vpp_max=vpp * 1.01, std_min=std, std_max=std * 1.01)
  assert mask.tolist() == [1, 0] and mask.dtype.kind == "i"


def test_pf07_vpp_min_forwarded():
  w = _sine(1.0)  # Vpp ~ 2 uV, std ~ 0.71 uV
  assert validate_eeg_windows(w[None]).tolist() == [0]  # shared default vpp_min = 5.0
  assert len(extract_clean_subwindows_psd(w, FS)) == 1  # legacy vpp_min = 0.5
  assert len(extract_clean_subwindows_psd(w, FS, vpp_min=5.0)) == 0


def test_subwindows_psd_and_rejection_stats():
  seg = _sine(10.0, n=5 * FS)
  seg[0, 2 * FS + 10] += 300.0
  qs = new_quality_stats()
  recs = extract_clean_subwindows_psd(seg, FS, quality_stats=qs)
  assert [r["sub_index"] for r in recs] == [0, 1, 3, 4]
  assert qs["n_rejected"] == 1 and qs["reasons"]["vpp_high"] == 1
  assert qs["rejected"][0]["channels"] == [0]
  r = recs[0]
  assert r["time_data"].shape == (3, FS) and np.allclose(np.diff(r["freqs"]), 1.0)
  assert r["freqs"][np.argmax(r["psd"][0])] == 10.0


@pytest.mark.parametrize("pulse", [1, 3])
def test_segments_counts_positions_and_layout(pulse):
  eeg, mark = _recording(pulse=pulse)
  qs = new_quality_stats()
  recs = process_condition_windows_with_baseline(eeg, mark, FS, quality_stats=qs)
  assert {k: len(v) for k, v in recs.items()} == {201: 20, 202: 10, 101: 10, 102: 10,
                                                   103: 10, 104: 10, 105: 10}
  onset = find_event_onsets(mark, 202)[0]
  assert recs[202][0]["start"] == onset - FS  # PF-13: the second before the pulse
  on101 = find_event_onsets(mark, 101)[0]
  assert [r["start"] - on101 for r in recs[101][:5]] == [0, FS, 2 * FS, 3 * FS, 4 * FS]
  for r in recs[201] + recs[103]:
    assert np.array_equal(r["time_data"], eeg[:, r["start"]:r["start"] + FS])
  assert qs["by_condition"][201]["n_total"] == 20 and qs["n_total"] == 80
  X_psd, X_time, y = prepare_feature_matrix(recs)
  assert X_psd.shape == (80, 217) and X_time.shape == (80, 7, FS) and y.dtype == np.int64
  order = [201, 202, 101, 102, 103, 104, 105]
  assert [order.index(v) for v in y] == sorted(order.index(v) for v in y)
  assert [int(np.argmax(X_psd[0, 31 * c:31 * c + 31])) for c in range(7)] == [3 * c for c in range(7)]


def test_segments_that_do_not_fit_are_dropped():
  eeg, mark = _recording(n_trials=5)
  mark[100] = 202
  mark[-3 * FS] = 101
  qs = new_quality_stats()
  recs = process_condition_windows_with_baseline(eeg, mark, FS, quality_stats=qs)
  assert len(recs[202]) == 5 and len(recs[101]) == 5
  assert {(e["condition"], e["onset"]) for e in qs["skipped_segments"]} == {
    (202, 100), (101, len(mark) - 3 * FS)}


def test_helpers():
  x = np.vstack([_sine(10.0, n=3 * FS + 7)[0]] * 2)
  x[1, FS + 5] = 500.0
  wins, mask = segment_and_validate_eeg(x, FS, vpp_min=0.5, vpp_max=200.0, std_min=0.5, std_max=60.0)
  assert wins.shape == (3, 2, FS) and mask.tolist() == [1, 0, 1]
  Xk, yk = filter_dataset(wins, np.array([1, 2, 3]), mask)
  assert yk.tolist() == [1, 3] and len(Xk) == 2
  with pytest.raises(ValueError):
    filter_dataset(wins, np.array([1, 2]), mask)
  s = summarize_window_quality(wins, vpp_min=0.5, vpp_max=200.0, std_min=0.5, std_max=60.0,
                               verbose=False)
  assert s["n_rejected"] == 1 and s["reasons"]["vpp_high"] == 1


def test_plots_written(tmp_path):
  from src.visualization.signal_plots import (
    plot_average_psd_by_condition, plot_eeg_window, plot_stimulus_vs_baseline_psd)
  eeg, mark = _recording()
  recs = process_condition_windows_with_baseline(eeg, mark, FS)
  for p in (plot_average_psd_by_condition(recs, tmp_path / "a" / "psd.png"),
            plot_stimulus_vs_baseline_psd(recs, tmp_path / "svb.png"),
            plot_eeg_window(recs[101][0]["time_data"], FS, tmp_path / "w.png")):
    assert p.is_file() and p.stat().st_size > 0
