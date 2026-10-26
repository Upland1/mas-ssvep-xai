"""P12 builder tests: coherence bias (PF-15), matched baseline (PF-16), layouts (R6), bands, plots."""

import numpy as np
import pytest

from src.features.connectivity import connectivity_extraction as ce
from src.visualization import connectivity_plots as cp

FS = 250.0
BAND = (23.0, 25.0)


def _noise(seed=0, n=40, c=7, t=256):
  return np.random.default_rng(seed).standard_normal((n, c, t))


def test_bias_independent_noise():
  w = _noise()
  per_win = ce.mean_offdiag(ce.per_window_mean_matrix(w, FS, BAND))
  concat = ce.mean_offdiag(ce.compute_condition_coherence(w, FS, BAND, 256))
  assert 0.30 <= per_win <= 0.37  # the historical bug
  assert concat <= 0.03  # the fix


def test_coupled_both_high():
  rng = np.random.default_rng(1)
  w = rng.standard_normal((40, 1, 256)) + 0.1 * rng.standard_normal((40, 7, 256))
  assert ce.mean_offdiag(ce.per_window_mean_matrix(w, FS, BAND)) >= 0.95
  assert ce.mean_offdiag(ce.compute_condition_coherence(w, FS, BAND, 256)) >= 0.95


def _narrow(rng, n, f, coupled=True, c=7, t=256, amp=3.0):
  """Noise plus a 24 Hz-like narrowband common component (random phase per window)."""
  tt = np.arange(t) / FS
  w = rng.standard_normal((n, c, t))
  ph = rng.uniform(0, 2 * np.pi, (n, 1, 1))
  return w + amp * np.sin(2 * np.pi * f * tt + ph) if coupled else w


def test_matched_baseline_removes_band_artifact():
  rng = np.random.default_rng(2)
  f = ce.CONDITION_FREQS[101]
  stim, base = _narrow(rng, 40, f), _narrow(rng, 40, f)
  w = np.concatenate([stim, base])
  y = np.array([101] * 40 + [201] * 40)
  s = ce.compute_condition_connectivity(w, y, FS)
  m, idx = ce.compute_baseline_matched_connectivity(w, y, FS)
  d_matched = ce.mean_offdiag(ce.compute_difference_matrices(s, m)[101])
  d_broad = ce.mean_offdiag(s[101]) - ce.mean_offdiag(s[201])
  assert abs(d_matched) <= 0.05
  assert d_broad > 0.2  # broadband baseline: apples to oranges


def test_pair_layout_and_symmetry():
  rng = np.random.default_rng(3)
  w = rng.standard_normal((40, 7, 256))
  w[:, 4] = w[:, 1] + 0.1 * rng.standard_normal((40, 256))
  m = ce.compute_condition_coherence(w, FS, BAND)
  assert np.array_equal(m[~np.isnan(m)], m.T[~np.isnan(m.T)])
  assert np.all(np.isnan(np.diag(m)))
  off = np.nan_to_num(m, nan=-1)
  assert np.unravel_index(np.argmax(off), off.shape) in {(1, 4), (4, 1)}
  assert np.isclose(m[1, 4], m[4, 1])


def test_band_bins_fs250():
  lo, hi = ce.band_for_condition(101)
  assert (lo, hi) == (23.0, 25.0)
  freqs = np.fft.rfftfreq(256, 1 / FS)
  coh = np.tile(np.arange(len(freqs), dtype=float), (2, 2, 1))
  sel = (freqs >= lo) & (freqs <= hi)
  assert 2 == sel.sum() and np.all((freqs[sel] >= 23) & (freqs[sel] <= 25))
  got = ce.band_average(freqs, coh, (lo, hi))
  assert np.allclose(got, np.arange(len(freqs))[sel].mean())


def test_band_narrower_than_resolution_uses_nearest_bin():
  freqs = np.array([0.0, 2.0, 4.0])
  assert ce.band_average(freqs, np.array([1.0, 2.0, 3.0]), (1.9, 2.1)) == 2.0


def test_baseline_same_windows_every_band():
  rng = np.random.default_rng(4)
  w = rng.standard_normal((30, 4, 256))
  y = np.array([101] * 10 + [201] * 10 + [202] * 5 + [102] * 5)
  m, idx = ce.compute_baseline_matched_connectivity(w, y, FS)
  assert list(idx) == list(range(10, 20))
  assert set(m) == set(ce.CONDITION_FREQS)
  # same windows -> same spectrum: matched value in a band equals a direct recompute on idx
  direct = ce.compute_condition_coherence(w[idx], FS, ce.band_for_condition(102))
  assert np.allclose(np.nan_to_num(m[102]), np.nan_to_num(direct))


def test_condition_filter_excludes_other_conditions():
  rng = np.random.default_rng(5)
  w = rng.standard_normal((20, 3, 256))
  w[10:] += 50.0 * rng.standard_normal((10, 1, 256))  # coupled windows of another condition
  y = np.array([101] * 10 + [202] * 10)
  s = ce.compute_condition_connectivity(w, y, FS)
  assert set(s) == {101}
  assert ce.mean_offdiag(s[101]) <= 0.1


def test_gate_loader_shared_channels_and_counts(tmp_path):
  rng = np.random.default_rng(6)
  X = 10 * rng.standard_normal((30, 7, 256))
  y = np.array([101] * 10 + [201] * 10 + [202] * 5 + [103] * 5)
  X[3] *= 100  # one rejected stimulus window
  d = tmp_path / "S99"
  d.mkdir()
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  g = ce.load_gated_conditions(tmp_path, "S99")
  assert g["counts"][101] == dict(total=10, clean=9, rejected=1)
  assert 202 not in g["y"] and len(g["channels_kept"]) == 7
  assert g["counts"][201]["total"] == 10


def test_plots(tmp_path):
  rng = np.random.default_rng(7)
  names = list("ABCDE")
  mats = {}
  for c in (101, 102):
    a = rng.uniform(-0.3, 0.5, (5, 5))
    a = (a + a.T) / 2
    np.fill_diagonal(a, np.nan)
    mats[c] = a
  vmax = cp.symmetric_limit(mats)
  assert vmax == pytest.approx(max(np.nanmax(np.abs(m)) for m in mats.values()))
  cp.plot_difference_panel(mats, names, path=tmp_path / "d.png")
  cp.plot_all_conditions_panel(mats, names, path=tmp_path / "r.png")
  assert (tmp_path / "d.png").stat().st_size > 0 and (tmp_path / "r.png").stat().st_size > 0


# --- Round 1 audit fixes ---------------------------------------------------------------------------

def test_broadband_baseline_before_after_known_answer():
  """R-11 baseline: independent noise -> before (per-window, nperseg 128) in [0.27, 0.40], after <= 0.05."""
  w = np.concatenate([_noise(10, n=20), _noise(11, n=40)])
  y = np.array([101] * 20 + [201] * 40)
  bb = ce.baseline_broadband_stats(w, y, FS)
  idx = np.flatnonzero(y == 201)
  assert 0.27 <= bb["before"] <= 0.40
  assert bb["after"] <= 0.05
  assert bb["before"] == pytest.approx(ce.mean_offdiag(ce.per_window_mean_matrix(w[idx], FS, ce.BASELINE_BAND)))
  assert bb["after"] == pytest.approx(ce.mean_offdiag(ce.compute_condition_coherence(w[idx], FS, ce.BASELINE_BAND)))
  rows = ce.summary_rows(w, y, FS)
  assert all(r["baseline_broadband_before"] == bb["before"] and r["baseline_broadband_after"] == bb["after"] for r in rows)


def test_meta_labels_bins_and_channel_count():
  rows = [dict(mean_baseline_perwindow=0.7, mean_matched_baseline=0.6)]
  txt = "\n".join(ce.meta_lines(rows, ["A", "B", "C"], ["D"], FS))
  assert "channels (3)" in txt and "REPORTED" in txt and "DIAGNOSTIC" in txt
  assert "band 101: (23.0000, 25.0000)" in txt and "[23.438, 24.414]" in txt and "[24.0, 25.0]" in txt
  bins, true = ce.band_bins(FS, 256, (23.0, 25.0))
  assert bins == [23.438, 24.414] and true == [24.0, 25.0]


def test_raw_panel_201_title_states_broadband():
  assert "5-35 Hz broadband" in cp.CONDITION_LABELS[201]


def _junction_trials(rng, amp, n_trials, n_win):
  """Independent cuts of a 1-60 Hz stream (common < 4 Hz component + noise): junctions between trials."""
  from scipy.signal import butter, sosfiltfilt
  out = []
  for _ in range(n_trials):
    n = n_win * 256 + 2000
    common = sosfiltfilt(butter(4, 4, fs=FS, output="sos"), rng.standard_normal(n))
    x = amp * (common / common.std())[None] + rng.standard_normal((7, n))
    x = sosfiltfilt(butter(2, [1, 60], "band", fs=FS, output="sos"), x, axis=1)[:, 500:500 + n_win * 256]
    out.append(x.reshape(7, n_win, 256).transpose(1, 0, 2))
  return np.concatenate(out)


def test_junction_bias_prescribed_vs_aligned():
  """No true difference; the prescribed estimator is pushed negative at 8.57 Hz, the aligned one is not (F2)."""
  band = ce.band_for_condition(105)
  d_pres, d_al = [], []
  for seed in range(10):
    rng = np.random.default_rng(seed)
    s, b = _junction_trials(rng, 8.0, 8, 5), _junction_trials(rng, 8.0, 40, 2)
    d_pres.append(ce.mean_offdiag(ce.compute_condition_coherence(s, FS, band))
                  - ce.mean_offdiag(ce.compute_condition_coherence(b, FS, band)))
    d_al.append(ce.mean_offdiag(ce.compute_aligned_condition_coherence(s, FS, band))
                - ce.mean_offdiag(ce.compute_aligned_condition_coherence(b, FS, band)))
  assert np.mean(d_pres) < -0.10
  assert abs(np.mean(d_al)) <= 0.03


def test_aligned_equals_default_estimator_on_white_noise_scale():
  """The aligned estimator is a different (diagnostic) estimator, same band/shape contract."""
  w = _noise(12, n=10)
  m = ce.compute_aligned_condition_coherence(w, FS, BAND)
  assert m.shape == (7, 7) and np.all(np.isnan(np.diag(m)))
