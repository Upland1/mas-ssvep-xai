"""P12 independent known-answer tests: PF-15 bias, PF-16 matched baseline, R6 layout, bands, gate, plots."""

import numpy as np
import pytest

from src.features.connectivity import connectivity_extraction as ce
from src.visualization import connectivity_plots as cp

FS = 250.0


def _tone(rng, n, c, f, amp, t=256):
  tt = np.arange(t) / FS
  ph = rng.uniform(0, 2 * np.pi, (n, 1, 1))
  return rng.standard_normal((n, c, t)) + amp * np.sin(2 * np.pi * f * tt + ph)


def _offdiag_mean(m):
  return float(np.nanmean(m[np.triu_indices(m.shape[0], k=1)]))


# --- PF-15 -------------------------------------------------------------------------------------

def test_pf15_independent_noise_bias_through_reported_path():
  w = np.random.default_rng(11).standard_normal((60, 7, 256))
  band = ce.band_for_condition(101)
  avg = _offdiag_mean(np.mean([ce.compute_coherence_matrix(x, FS, band) for x in w], axis=0))
  cat = _offdiag_mean(ce.compute_condition_coherence(w, FS, band))
  assert 0.30 <= avg <= 0.37
  assert cat <= 0.03


def test_pf15_summary_rows_reported_value_is_concatenated():
  # reported mean_raw on pure noise must be near 0, not near the averaged-window 0.33
  rng = np.random.default_rng(12)
  w = rng.standard_normal((50, 5, 256))
  y = np.array([101] * 25 + [201] * 25)
  row = ce.summary_rows(w, y, FS)[0]
  assert row["mean_raw"] <= 0.05
  assert row["mean_matched_baseline"] <= 0.05
  assert 0.28 <= row["mean_baseline_perwindow"] <= 0.40  # diagnostic column keeps the biased value


def test_pf15_coupled_high():
  rng = np.random.default_rng(13)
  w = rng.standard_normal((40, 1, 256)) + 0.05 * rng.standard_normal((40, 6, 256))
  band = ce.band_for_condition(102)
  assert _offdiag_mean(ce.compute_condition_coherence(w, FS, band)) >= 0.95
  assert _offdiag_mean(np.mean([ce.compute_coherence_matrix(x, FS, band) for x in w], axis=0)) >= 0.95


# --- PF-16 -------------------------------------------------------------------------------------

def test_pf16_identical_narrowband_coupling_matched_zero_broadband_not():
  rng = np.random.default_rng(14)
  f = ce.CONDITION_FREQS[102]
  w = np.concatenate([_tone(rng, 40, 6, f, 3.0), _tone(rng, 40, 6, f, 3.0)])
  y = np.array([102] * 40 + [201] * 40)
  stim = ce.compute_condition_connectivity(w, y, FS)
  matched, _ = ce.compute_baseline_matched_connectivity(w, y, FS)
  d = _offdiag_mean(ce.compute_difference_matrices(stim, matched)[102])
  broad = _offdiag_mean(stim[102]) - _offdiag_mean(stim[201])
  assert abs(d) <= 0.05
  assert broad > 0.2
  row = ce.summary_rows(w, y, FS)[0]
  assert abs(row["mean_difference"]) <= 0.05
  assert row["mean_difference_broadband"] > 0.2


# --- R6 ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("pair", [(0, 6), (2, 3), (1, 4)])
def test_r6_pair_layout_argmax_and_symmetry(pair):
  rng = np.random.default_rng(15)
  i, j = pair
  w = rng.standard_normal((40, 7, 256))
  w[:, j] = w[:, i] + 0.05 * rng.standard_normal((40, 256))
  m = ce.compute_condition_coherence(w, FS, ce.band_for_condition(101))
  off = np.where(np.eye(7, dtype=bool), -1.0, m)
  assert np.unravel_index(np.argmax(off), off.shape) in {(i, j), (j, i)}
  assert m[i, j] == m[j, i] and m[i, j] > 0.9
  rest = off.copy()
  rest[[i, j], [j, i]] = -1
  assert rest.max() < 0.3
  assert np.array_equal(np.isnan(m), np.eye(7, dtype=bool))
  assert np.allclose(np.nan_to_num(m), np.nan_to_num(m).T)


def test_r6_dropped_channel_names_follow(tmp_path):
  # channel "Oz" (position 5) is noisy and dropped; coupling between POz (2) and O2 (6) must land on
  # the kept names POz / O2 in the reduced matrix
  rng = np.random.default_rng(16)
  names = ["PO7", "PO3", "POz", "PO4", "PO8", "Oz", "O2"]
  X = 10 * rng.standard_normal((40, 7, 256))
  X[:, 6] = X[:, 2] + 0.5 * rng.standard_normal((40, 256))
  X[:, 5] *= 100  # fails every window
  y = np.array([101] * 20 + [201] * 20)
  d = tmp_path / "S98"
  d.mkdir()
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  g = ce.load_gated_conditions(tmp_path, "S98", channel_names=names)
  assert g["channels_dropped"] == ["Oz"]
  kept = list(g["channels_kept"])
  assert kept == ["PO7", "PO3", "POz", "PO4", "PO8", "O2"]
  m = ce.compute_condition_coherence(g["windows"][g["y"] == 101], FS, ce.band_for_condition(101))
  assert m.shape == (6, 6)
  off = np.where(np.eye(6, dtype=bool), -1.0, m)
  a, b = np.unravel_index(np.argmax(off), off.shape)
  assert {kept[a], kept[b]} == {"POz", "O2"}


# --- bands -------------------------------------------------------------------------------------

def test_band_bins_fs250_hand_mean():
  freqs, coh = ce.pairwise_coherence(np.random.default_rng(17).standard_normal((3, 2048)), FS, 256)
  lo, hi = ce.band_for_condition(101)
  assert (lo, hi) == (23.0, 25.0)
  hand_bins = [k for k in range(len(freqs)) if 23.0 <= freqs[k] <= 25.0]
  assert hand_bins == [24, 25]  # 23.4375 and 24.4141 Hz
  np.testing.assert_allclose(freqs[hand_bins], [24 * FS / 256, 25 * FS / 256])
  got = ce.band_average(freqs, coh, (lo, hi))
  hand = (coh[..., 24] + coh[..., 25]) / 2
  np.testing.assert_allclose(np.nan_to_num(got), np.nan_to_num(hand))


def test_band_bins_fs256_differ_pf04_guard():
  f250 = np.fft.rfftfreq(256, 1 / 250.0)
  f256 = np.fft.rfftfreq(256, 1 / 256.0)
  band = ce.band_for_condition(101)
  b250 = np.flatnonzero((f250 >= band[0]) & (f250 <= band[1]))
  b256 = np.flatnonzero((f256 >= band[0]) & (f256 <= band[1]))
  assert list(b250) == [24, 25] and list(b256) == [23, 24, 25]
  # the estimator follows the fs it is given
  x = np.random.default_rng(18).standard_normal((2, 2048))
  fr250, _ = ce.pairwise_coherence(x, 250.0, 256)
  fr256, _ = ce.pairwise_coherence(x, 256.0, 256)
  assert not np.allclose(fr250, fr256)


# --- baseline windows and conditions ---------------------------------------------------------

def test_same_201_windows_in_every_band(monkeypatch):
  rng = np.random.default_rng(19)
  w = rng.standard_normal((40, 4, 256))
  y = np.array([101] * 8 + [201] * 12 + [202] * 6 + [103] * 6 + [201] * 8)
  seen = []
  orig = ce.concatenate_windows
  monkeypatch.setattr(ce, "concatenate_windows", lambda a: (seen.append(np.array(a)), orig(a))[1])
  m, idx = ce.compute_baseline_matched_connectivity(w, y, FS)
  expected = np.flatnonzero(y == 201)
  assert np.array_equal(idx, expected)
  assert len(seen) == 1 and np.array_equal(seen[0], w[expected])  # one estimate, shared by all bands
  # every band equals a band average of the SAME spectrum
  freqs, coh = ce.pairwise_coherence(orig(w[expected]), FS, ce.NPERSEG)
  for c in ce.CONDITION_FREQS:
    np.testing.assert_allclose(np.nan_to_num(m[c]),
                               np.nan_to_num(ce.band_average(freqs, coh, ce.band_for_condition(c))))


def test_condition_filter_excludes_202():
  rng = np.random.default_rng(20)
  w = rng.standard_normal((30, 3, 256))
  w[10:20] = w[10:11]  # 202 windows: identical in all channels (coherence 1)
  y = np.array([101] * 10 + [202] * 10 + [201] * 10)
  s = ce.compute_condition_connectivity(w, y, FS)
  assert set(s) == {101, 201}
  assert _offdiag_mean(s[101]) < 0.1 and _offdiag_mean(s[201]) < 0.1
  m, idx = ce.compute_baseline_matched_connectivity(w, y, FS)
  assert list(idx) == list(range(20, 30))
  assert _offdiag_mean(m[101]) < 0.1


# --- gate --------------------------------------------------------------------------------------

def test_gate_single_call_explicit_thresholds(monkeypatch, tmp_path):
  rng = np.random.default_rng(21)
  X = 10 * rng.standard_normal((36, 7, 256))
  y = np.array([101] * 8 + [102] * 4 + [103] * 4 + [104] * 4 + [105] * 4 + [201] * 8 + [202] * 4)
  d = tmp_path / "S97"
  d.mkdir()
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  calls = []
  orig = ce.apply_artifact_quality_pipeline

  def spy(windows, yy, names, **kw):
    calls.append((len(windows), set(np.unique(yy).tolist()), kw))
    return orig(windows, yy, names, **kw)

  monkeypatch.setattr(ce, "apply_artifact_quality_pipeline", spy)
  ce.load_gated_conditions(tmp_path, "S97")
  assert len(calls) == 1
  n, labels, kw = calls[0]
  assert n == 32 and labels == {101, 102, 103, 104, 105, 201}
  for k, v in dict(vpp_min=5.0, vpp_max=120.0, std_min=1.0, std_max=35.0,
                   channel_fail_fraction_thresh=0.5).items():
    assert kw[k] == v


def test_gate_union_decision_shared_channels(tmp_path):
  # channel 3 is noisy in every baseline window only; baseline is 60 % of the union -> the channel
  # fails in > 50 % of windows and is dropped for stimulus windows too (shared channels)
  rng = np.random.default_rng(22)
  X = 10 * rng.standard_normal((50, 7, 256))
  y = np.array([101] * 10 + [102] * 10 + [201] * 30)
  X[y == 201, 3] *= 100
  d = tmp_path / "S96"
  d.mkdir()
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  g = ce.load_gated_conditions(tmp_path, "S96")
  assert len(g["channels_dropped"]) == 1 and g["windows"].shape[1] == 6
  assert g["counts"][101]["clean"] == 10 and g["counts"][201]["clean"] == 30


# --- plots -------------------------------------------------------------------------------------

def test_difference_colour_limits_symmetric(tmp_path):
  import matplotlib.pyplot as plt
  rng = np.random.default_rng(23)
  mats = {}
  for c, (lo, hi) in {101: (0.05, 0.50), 102: (-0.10, 0.20)}.items():  # asymmetric data range
    a = rng.uniform(lo, hi, (5, 5))
    a = (a + a.T) / 2
    np.fill_diagonal(a, np.nan)
    mats[c] = a
  vmax = max(np.nanmax(np.abs(m)) for m in mats.values())
  assert cp.symmetric_limit(mats) == pytest.approx(vmax)
  fig = cp.plot_difference_panel(mats, list("ABCDE"), path=tmp_path / "d.png")
  cb = fig.axes[-1]  # colourbar axes carries the shared normalisation
  lo, hi = cb.get_xlim()
  assert lo == pytest.approx(-hi) and hi == pytest.approx(vmax)
  plt.close("all")


# --- Round 1: reported broadband baseline, labels, aligned diagnostic ---------------------------

from scipy.signal import coherence as _sp_coh  # noqa: E402


def _direct_mean_coh(sig, nperseg, lo=5.0, hi=35.0, noverlap=None):
  """Independent hand computation: scipy per pair, mean of the bins in [lo, hi], mean over pairs."""
  vals = []
  for i in range(sig.shape[0]):
    for j in range(i + 1, sig.shape[0]):
      kw = {} if noverlap is None else {"noverlap": noverlap}
      f, c = _sp_coh(sig[i], sig[j], fs=FS, nperseg=nperseg, **kw)
      vals.append(c[(f >= lo) & (f <= hi)].mean())
  return float(np.mean(vals))


def test_r1_broadband_baseline_independent_noise():
  w = np.random.default_rng(31).standard_normal((50, 5, 256))
  y = np.array([101] * 20 + [201] * 30)
  bb = ce.baseline_broadband_stats(w, y, FS)
  assert 0.27 <= bb["before"] <= 0.40
  assert bb["after"] <= 0.05


def test_r1_broadband_baseline_coupled():
  rng = np.random.default_rng(32)
  w = rng.standard_normal((40, 1, 256)) + 0.05 * rng.standard_normal((40, 5, 256))
  y = np.array([201] * 40)
  bb = ce.baseline_broadband_stats(w, y, FS)
  assert bb["before"] >= 0.95 and bb["after"] >= 0.95


def test_r1_broadband_baseline_hand_built_uses_only_201():
  rng = np.random.default_rng(33)
  w = rng.standard_normal((30, 3, 256))
  w[:, 1] = 0.7 * w[:, 0] + 0.3 * rng.standard_normal((30, 256))  # known partial coupling
  y = np.array([201] * 10 + [101] * 10 + [202] * 10)
  w[10:] = rng.standard_normal((20, 3, 256))  # other conditions carry no coupling
  bb = ce.baseline_broadband_stats(w, y, FS)
  cat = np.concatenate(list(w[:10]), axis=1)
  assert bb["after"] == pytest.approx(_direct_mean_coh(cat, 256), abs=1e-9)
  per = np.mean([_direct_mean_coh(x, 128) for x in w[:10]])
  assert bb["before"] == pytest.approx(per, abs=1e-9)
  assert bb["before"] != pytest.approx(bb["after"], abs=0.02)


def test_r1_labels_reported_vs_diagnostic():
  rng = np.random.default_rng(34)
  w = rng.standard_normal((30, 4, 256))
  y = np.array([101] * 10 + [201] * 20)
  rows = ce.summary_rows(w, y, FS)
  meta = ce.meta_lines(rows, list("ABCD"), [], FS)
  labels = {}
  for line in meta:
    if line.startswith("  ") and ": " in line:
      k, v = line.strip().split(": ", 1)
      labels[k] = v
  assert set(rows[0]) - {"condition", "f_c", "band_lo", "band_hi", "n_windows", "n_baseline"} <= set(labels)
  reported = {"mean_raw", "mean_matched_baseline", "mean_difference", "baseline_broadband_after"}
  diagnostic = {"baseline_broadband_before", "baseline_broadband_after_aligned", "mean_baseline_perwindow",
                "mean_difference_broadband", "mean_difference_aligned"}
  for k in reported:
    assert labels[k].startswith("REPORTED"), k
  for k in diagnostic:
    assert labels[k].startswith("DIAGNOSTIC") or "DIAGNOSTIC" in labels[k], k
    assert not labels[k].startswith("REPORTED"), k
  assert any("4 " in l or "(4)" in l for l in meta[:1])  # channel count taken from the data


def _noise(seed, n, c, t=256):
  return np.random.default_rng(seed).standard_normal((n, c, t))


def _lf_trials(rng, n_trials, n_win, amp=6.0, t=256):
  """Each trial: common random 1-3 Hz sinusoids (random phase, per trial) + independent noise.
  Trials are cut independently, so the concatenation has junction discontinuities."""
  out = []
  tt = np.arange(n_win * t) / FS
  for _ in range(n_trials):
    com = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) for f in (1.0, 1.7, 2.4, 3.1))
    x = amp * com[None] + rng.standard_normal((6, n_win * t))
    out.append(x.reshape(6, n_win, t).transpose(1, 0, 2))
  return np.concatenate(out)


def test_r1_aligned_matches_hand_scipy_and_default_untouched():
  w = _noise(35, 8, 4)
  band = ce.band_for_condition(105)
  cat = np.concatenate(list(w), axis=1)
  # aligned == scipy with nperseg = T, noverlap = 0
  al = ce.compute_aligned_condition_coherence(w, FS, band)
  f, c = _sp_coh(cat[0], cat[2], fs=FS, nperseg=256, noverlap=0)
  assert al[0, 2] == pytest.approx(c[(f >= band[0]) & (f <= band[1])].mean(), abs=1e-12)
  # reported == scipy defaults (nperseg 256, 50 % overlap) and does not use noverlap
  rep = ce.compute_condition_coherence(w, FS, band)
  f, c = _sp_coh(cat[0], cat[2], fs=FS, nperseg=256)
  assert rep[0, 2] == pytest.approx(c[(f >= band[0]) & (f <= band[1])].mean(), abs=1e-12)
  assert not np.isclose(rep[0, 2], al[0, 2])
  # the new argument left at its default changes nothing
  f1, c1 = ce.pairwise_coherence(cat, FS, 256)
  f2, c2 = ce.pairwise_coherence(cat, FS, 256, noverlap=None)
  assert np.array_equal(np.nan_to_num(c1), np.nan_to_num(c2))
  # nperseg = T, noverlap = 0: shorter T is used as nperseg
  w2 = _noise(36, 8, 3, 200)
  cat2 = np.concatenate(list(w2), axis=1)
  al2 = ce.compute_aligned_condition_coherence(w2, FS, band)
  f, c = _sp_coh(cat2[0], cat2[1], fs=FS, nperseg=200, noverlap=0)
  assert al2[0, 1] == pytest.approx(c[(f >= band[0] - 1e-9) & (f <= band[1] + 1e-9)].mean(), abs=1e-12)


def test_r1_junction_aligned_zero_prescribed_negative():
  band = ce.band_for_condition(105)
  d_pres, d_al = [], []
  for seed in range(8):
    rng = np.random.default_rng(100 + seed)
    s, b = _lf_trials(rng, 8, 5), _lf_trials(rng, 40, 2)  # same true state, different junction density
    d_pres.append(ce.mean_offdiag(ce.compute_condition_coherence(s, FS, band))
                  - ce.mean_offdiag(ce.compute_condition_coherence(b, FS, band)))
    d_al.append(ce.mean_offdiag(ce.compute_aligned_condition_coherence(s, FS, band))
                - ce.mean_offdiag(ce.compute_aligned_condition_coherence(b, FS, band)))
  assert np.mean(d_pres) < -0.15
  assert abs(np.mean(d_al)) <= 0.03
