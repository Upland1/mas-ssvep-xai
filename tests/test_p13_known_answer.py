"""P13 independent known-answer tests (synthetic-tester): MVAR layout, PDC, CSD phase, permutations.

Every expected value is derived by hand or from a system constructed here, not from the builder's
helpers (the builder's demo systems are not reused).
"""

import numpy as np
import pandas as pd
import pytest
from scipy.signal import butter, hilbert, sosfiltfilt

from scripts.connectivity.analysis import analyze_connectivity_cohort as cohort
from src.features.connectivity import connectivity_extraction as ce
from src.features.connectivity import mvar_pdc as mp
from src.features.connectivity import permutation as pm
from src.features.connectivity import phase_connectivity as pc
from src.preprocessing.dataset.cv_utils import build_trial_ids

FS = 250.0
BAND = (23.0, 25.0)


# ------------------------------------------------------------------ PF-17: VAR recovery

A1 = np.array([[0.40, 0.00, 0.00, 0.30],
               [0.50, 0.20, 0.00, 0.00],
               [0.00, -0.40, 0.30, 0.00],
               [0.00, 0.00, 0.45, -0.30]])
A2 = np.array([[-0.20, 0.00, 0.25, 0.00],
               [0.00, -0.25, 0.00, 0.20],
               [0.20, 0.00, -0.20, 0.00],
               [0.00, 0.15, 0.00, 0.20]])
TRUE_VAR = np.stack([A1, A2])


def _simulate(coefs, n=100, t=256, seed=0, burn=60):
  p, c, _ = coefs.shape
  rng = np.random.default_rng(seed)
  out = np.zeros((n, c, t))
  for k in range(n):
    x = np.zeros((c, t + burn))
    e = rng.standard_normal((c, t + burn))
    for s in range(p, t + burn):
      x[:, s] = e[:, s] + sum(coefs[l] @ x[:, s - 1 - l] for l in range(p))
    out[k] = x[:, burn:]
  return out


def _relerr(est, true):
  return float(np.linalg.norm(est - true) / np.linalg.norm(true))


def test_hand_picked_var2_is_stable():
  c = 4
  comp = np.zeros((2 * c, 2 * c))
  comp[:c, :c], comp[:c, c:] = A1, A2
  comp[c:, :c] = np.eye(c)
  assert max(abs(np.linalg.eigvals(comp))) < 0.9


def test_mvar_strided_recovers_hand_picked_var2_contiguous_is_far():
  w = _simulate(TRUE_VAR)
  wts = mp.fit_mvar_ols(w, 2)
  assert wts.shape == (8, 4)
  coefs = mp.mvar_coefficients(wts, 2)
  assert coefs.shape == (2, 4, 4)
  assert _relerr(coefs, TRUE_VAR) < 0.10
  # entry-wise: the planted 1 -> ... couplings keep orientation and sign (A[lag][i, j]: j -> i)
  assert coefs[0][1, 0] == pytest.approx(0.50, abs=0.06)
  assert coefs[0][2, 1] == pytest.approx(-0.40, abs=0.06)
  assert coefs[0][0, 1] == pytest.approx(0.0, abs=0.06)  # reverse direction is empty
  # the contiguous slicing of the same weights (PF-17 bug) is far from the truth
  contiguous = np.stack([wts[l * 4:(l + 1) * 4].T for l in range(2)])
  assert _relerr(contiguous, TRUE_VAR) > 0.5
  assert _relerr(contiguous, TRUE_VAR) > 5 * _relerr(coefs, TRUE_VAR)


def test_mvar_row_layout_channel_major_with_known_weights():
  # y = 2 * x_ch1[t-3] only: weights[c * p + (lag - 1), i] must be 2 at (1 * 4 + 2, 0)
  rng = np.random.default_rng(0)
  w = rng.standard_normal((30, 2, 200))
  w[:, 0, 4:] = 2.0 * w[:, 1, 1:-3]
  wts = mp.fit_mvar_ols(w[:, :, :], 4)
  assert wts[1 * 4 + 2, 0] == pytest.approx(2.0, abs=0.02)
  coefs = mp.mvar_coefficients(wts, 4)
  assert coefs[2][0, 1] == pytest.approx(2.0, abs=0.02)


# ------------------------------------------------------------------ PDC

def _hand_pdc(coefs, f, fs):
  p, c, _ = coefs.shape
  a = np.eye(c, dtype=complex)
  for l in range(1, p + 1):
    a = a - coefs[l - 1] * np.exp(-2j * np.pi * f * l / fs)
  mag = np.abs(a)
  out = mag / np.sqrt((mag ** 2).sum(axis=0, keepdims=True))
  np.fill_diagonal(out, 0.0)
  return out


def test_pdc_hand_computed_orientation_and_column_normalisation():
  # channel 0 drives channel 2 only
  coefs = np.zeros((1, 3, 3))
  coefs[0] = np.diag([0.3, 0.2, 0.1])
  coefs[0][2, 0] = 0.6
  f = 12.0
  got = pc_pdc = mp.pdc_from_coefficients(coefs, FS, np.array([f]))[0]
  z = np.exp(-2j * np.pi * f / FS)
  expected_20 = 0.6 / np.sqrt(abs(1 - 0.3 * z) ** 2 + 0.36)
  assert got[2, 0] == pytest.approx(expected_20, rel=1e-9)  # [i, j] = flow j -> i
  assert got[0, 2] == 0.0 and got[1, 0] == 0.0 and got[0, 1] == 0.0
  assert np.all(np.diag(pc_pdc) == 0.0)
  assert np.allclose(got, _hand_pdc(coefs, f, FS))
  # column normalisation: including the (zeroed) diagonal term, every column has unit L2 norm
  a_diag = np.abs(1 - 0.3 * z)
  assert got[2, 0] ** 2 + (a_diag / np.sqrt(a_diag ** 2 + 0.36)) ** 2 == pytest.approx(1.0)


def test_pdc_random_coefficients_match_hand_formula_asymmetric():
  coefs = np.random.default_rng(5).standard_normal((3, 5, 5)) * 0.15
  freqs = np.array([5.0, 17.0, 40.0])
  got = mp.pdc_from_coefficients(coefs, FS, freqs)
  for k, f in enumerate(freqs):
    assert np.allclose(got[k], _hand_pdc(coefs, f, FS))
  assert not np.allclose(got[0], got[0].T)  # a transposed implementation would be symmetric to this one


def test_pdc_end_to_end_driver_direction_7_channels_42_edges():
  # channel 1 drives channel 5 in a 7-channel AR(1) system
  c, p = 7, 1
  coefs = np.zeros((1, c, c))
  coefs[0] = 0.2 * np.eye(c)
  coefs[0][5, 1] = 0.6
  w = _simulate(coefs, n=80, t=256, seed=3)
  m = mp.compute_condition_pdc(w, FS, BAND, order=2)
  assert m.shape == (7, 7)
  assert m[5, 1] > m[1, 5] + 0.3
  assert np.all(np.diag(m) == 0.0)
  off = ~np.eye(7, dtype=bool)
  assert off.sum() == 42 and np.all(m[off] > 0)
  assert pm.edge_mask(7, True).sum() == 42 and pm.edge_mask(7, False).sum() == 21
  assert not pm.edge_mask(7, True)[3, 3] and not pm.edge_mask(7, False)[4, 2]  # upper triangle only


# ------------------------------------------------------------------ PF-18, wPLI, PLV

def _coupled(n=120, lag=0.7, noise=0.1, seed=0, t=256):
  rng = np.random.default_rng(seed)
  tt = np.arange(t) / FS
  ph = rng.uniform(0, 2 * np.pi, (n, 1))
  a = np.sin(2 * np.pi * 24 * tt + ph)
  b = np.sin(2 * np.pi * 24 * tt + ph + lag)
  return np.stack([a, b], 1) + noise * rng.standard_normal((n, 2, t))


def _hilbert_plv(w, band, fs):
  sos = butter(3, [band[0] / (fs / 2), band[1] / (fs / 2)], btype="band", output="sos")
  an = hilbert(sosfiltfilt(sos, w, axis=-1), axis=-1)
  d = np.angle(an[:, 0]) - np.angle(an[:, 1])
  return float(np.abs(np.exp(1j * d).mean()))


def _corrupt(w, k=15, seed=9):
  out = w.copy()
  rng = np.random.default_rng(seed)
  out[..., :k] = 5.0 * rng.standard_normal(out[..., :k].shape)
  out[..., -k:] = 5.0 * rng.standard_normal(out[..., -k:].shape)
  return out


def test_csd_plv_is_immune_to_edge_corruption_and_hilbert_is_not():
  w = _coupled(noise=0.2)
  wc = _corrupt(w)
  csd0 = pc.compute_condition_plv(w, FS, BAND)[0, 1]
  csd1 = pc.compute_condition_plv(wc, FS, BAND)[0, 1]
  assert csd0 > 0.95
  assert abs(csd0 - csd1) <= 0.03
  hil_drop = _hilbert_plv(w, BAND, FS) - _hilbert_plv(wc, BAND, FS)
  assert hil_drop > 2 * abs(csd0 - csd1)  # the time-domain variant degrades more (the PF-18 bug)


def test_plv_wpli_zero_lag_and_quadrature():
  zero = _coupled(lag=0.0, noise=0.05)
  quad = _coupled(lag=np.pi / 2, noise=0.05)
  assert pc.compute_condition_plv(zero, FS, BAND)[0, 1] > 0.95
  assert pc.compute_condition_wpli(zero, FS, BAND)[0, 1] < 0.2
  assert pc.compute_condition_plv(quad, FS, BAND)[0, 1] > 0.95
  assert pc.compute_condition_wpli(quad, FS, BAND)[0, 1] > 0.95
  # a uniformly random lag per window: PLV near 0 (not locked)
  rng = np.random.default_rng(2)
  tt = np.arange(256) / FS
  ph, lg = rng.uniform(0, 2 * np.pi, (300, 1)), rng.uniform(0, 2 * np.pi, (300, 1))
  rand = np.stack([np.sin(2 * np.pi * 24 * tt + ph), np.sin(2 * np.pi * 24 * tt + ph + lg)], 1)
  assert pc.compute_condition_plv(rand, FS, BAND)[0, 1] < 0.2


def test_wpli_and_plv_hand_computed_from_csd():
  s = np.zeros((4, 2, 2), dtype=complex)
  s[:, 0, 1] = [1 + 1j, 2 + 1j, 3 - 1j, 1 + 2j]
  s[:, 1, 0] = np.conj(s[:, 0, 1])
  s[:, 0, 0] = s[:, 1, 1] = np.nan
  # Im = [1, 1, -1, 2]: |mean| = 0.75, mean|.| = 1.25
  assert pc.wpli_from_csd(s)[0, 1] == pytest.approx(0.6)
  ang = np.angle(s[:, 0, 1])
  assert pc.plv_from_csd(s)[0, 1] == pytest.approx(abs(np.exp(1j * ang).mean()))
  # magnitude does not matter for PLV
  assert pc.plv_from_csd(s * 7.0)[0, 1] == pytest.approx(pc.plv_from_csd(s)[0, 1])
  # equal numbers of angle 0 and pi/2: PLV = sqrt(2)/2 whatever the magnitudes
  s2 = np.zeros((2, 2, 2), dtype=complex)
  s2[:, 0, 1] = [5.0, 0.1j]
  assert pc.plv_from_csd(s2)[0, 1] == pytest.approx(np.sqrt(2) / 2)


def test_wpli_zero_denominator_gives_zero_not_nan():
  s = np.zeros((6, 3, 3), dtype=complex)
  s[:, 0, 1] = 2.0           # real CSD: Im = 0 for every window
  s[:, 0, 2] = [1j] * 6      # constant positive Im: wPLI = 1
  s[:, 1, 2] = 1j * np.array([0.5, 0.5, 0.5, -0.5, -0.5, -0.5])  # cancelling signs: wPLI = 0
  for i in range(3):
    s[:, i, i] = np.nan
  s[:, 1, 0], s[:, 2, 0], s[:, 2, 1] = np.conj(s[:, 0, 1]), np.conj(s[:, 0, 2]), np.conj(s[:, 1, 2])
  w = pc.wpli_from_csd(s)
  assert w[0, 1] == 0.0 and not np.isnan(w[0, 1])
  assert w[0, 2] == pytest.approx(1.0)
  assert w[1, 2] == pytest.approx(0.0)
  assert np.all(np.isnan(np.diag(w)))


# ------------------------------------------------------------------ PF-19: trial split

def _ids(sizes):
  return np.repeat(np.arange(len(sizes)), sizes)


@pytest.mark.parametrize("n_first", [1, 4, 7, 16, 17, 22, 33, 43])
def test_trial_split_mixed_lengths_exact_and_whole_trials(n_first):
  ids = _ids([5] * 6 + [2] * 7)  # 44 windows, 13 trials
  total = len(ids)
  firsts = set()
  for seed in range(40):
    a, b = pm._trial_permutation_split(ids, n_first, np.random.default_rng(seed))
    assert len(a) == n_first and len(b) == total - n_first
    assert np.array_equal(np.sort(np.concatenate([a, b])), np.arange(total))
    ta, tb = set(ids[a]), set(ids[b])
    shared = ta & tb
    assert len(shared) <= 1
    for t in (ta | tb) - shared:  # every non-split trial sits entirely in one group
      members = set(np.flatnonzero(ids == t))
      assert members <= set(a) or members <= set(b)
    firsts.add(tuple(a))
  assert len(firsts) > 5  # different seeds give different splits


def test_trial_split_can_hit_the_count_without_splitting_when_possible():
  ids = _ids([5, 5, 5, 5])
  for seed in range(20):
    a, b = pm._trial_permutation_split(ids, 10, np.random.default_rng(seed))
    assert not (set(ids[a]) & set(ids[b]))
    assert len(set(ids[a])) == 2


def _spy_splits(monkeypatch):
  calls = {"trial": [], "window": 0}
  orig_t, orig_w = pm._trial_permutation_split, pm._window_permutation_split

  def spy_t(ids, n_first, rng):
    a, b = orig_t(ids, n_first, rng)
    calls["trial"].append((len(a), n_first))
    return a, b

  def spy_w(n_total, n_first, rng):
    calls["window"] += 1
    return orig_w(n_total, n_first, rng)

  monkeypatch.setattr(pm, "_trial_permutation_split", spy_t)
  monkeypatch.setattr(pm, "_window_permutation_split", spy_w)
  return calls


def _toy(c=3, ns=20, nb=30, seed=0, shift=0.0):
  rng = np.random.default_rng(seed)
  return (rng.standard_normal((ns, c, 256)) + shift, rng.standard_normal((nb, c, 256)),
          np.repeat(np.arange(ns // 5), 5), np.repeat(np.arange(nb // 2), 2) + 50)


def test_trial_ids_route_to_trial_split_with_observed_stim_size(monkeypatch):
  calls = _spy_splits(monkeypatch)
  stim, base, ids_s, ids_b = _toy()
  r = pm.compute_permutation_test(stim, base, BAND, FS, 6, pc.compute_condition_plv, 1, 3,
                                  stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
  assert r["permutation_unit"] == "trial"
  assert calls["window"] == 0
  assert len(calls["trial"]) == 6 and all(got == 20 == want for got, want in calls["trial"])


def test_no_ids_routes_to_window_split(monkeypatch):
  calls = _spy_splits(monkeypatch)
  stim, base, _, _ = _toy()
  r = pm.compute_permutation_test(stim, base, BAND, FS, 6, pc.compute_condition_plv, 1, 3)
  assert r["permutation_unit"] == "window"
  assert calls["window"] == 6 and calls["trial"] == []


def test_colliding_stim_and_baseline_trial_labels_stay_distinct(monkeypatch):
  seen = []
  orig = pm._trial_permutation_split
  monkeypatch.setattr(pm, "_trial_permutation_split", lambda ids, n, rng: (seen.append(np.asarray(ids)), orig(ids, n, rng))[1])
  stim, base, ids_s, _ = _toy()
  ids_b = np.repeat(np.arange(15), 2)  # labels 0..14 collide with the stimulus labels 0..3
  pm.compute_permutation_test(stim, base, BAND, FS, 2, pc.compute_condition_plv, 1, 1,
                              stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
  assert len(np.unique(seen[0])) == 4 + 15


# ------------------------------------------------------------------ p-values and BH

def _mean_fn(windows, fs, band):
  m = float(np.mean(windows[:, 0, 0]))
  return np.array([[np.nan, m], [m, np.nan]])


def _scalar_windows(rng, n, loc):
  return loc + rng.standard_normal((n, 2, 1))


@pytest.mark.parametrize("n_perm", [19, 99])
def test_pseudo_count_minimum_p_and_tails(n_perm):
  rng = np.random.default_rng(0)
  hi, lo = _scalar_windows(rng, 12, 50.0), _scalar_windows(rng, 18, 0.0)
  r = pm.compute_permutation_test(hi, lo, BAND, FS, n_perm, _mean_fn, 1, 4)
  assert r["p_one_tailed"] == pytest.approx(1 / (n_perm + 1))
  assert r["p_two_tailed"] == pytest.approx(1 / (n_perm + 1))
  assert r["edge_p_one_tailed"][0, 1] == pytest.approx(1 / (n_perm + 1))
  neg = pm.compute_permutation_test(lo, hi, BAND, FS, n_perm, _mean_fn, 1, 4)
  assert neg["p_one_tailed"] == pytest.approx(1.0)               # opposite tail: every null >= obs
  assert neg["p_two_tailed"] == pytest.approx(1 / (n_perm + 1))  # but extreme in absolute value


def test_p_values_on_exchangeable_null_are_in_range_and_two_tailed_covers_one():
  rng = np.random.default_rng(1)
  for k in range(15):
    a, b = _scalar_windows(rng, 15, 0.0), _scalar_windows(rng, 25, 0.0)
    r = pm.compute_permutation_test(a, b, BAND, FS, 49, _mean_fn, 1, k)
    for key in ("p_one_tailed", "p_two_tailed"):
      assert 1 / 50 <= r[key] <= 1.0
    if r["obs_diff"] >= 0:
      assert r["p_two_tailed"] >= r["p_one_tailed"]
    # count identity: p = (1 + #{null >= obs}) / (n + 1)
    expected = (1 + np.sum(r["null_distribution"] >= r["obs_diff"])) / 50
    assert r["p_one_tailed"] == pytest.approx(expected)
    assert len(r["null_distribution"]) == 49


def _bh_reference(p, alpha=0.05):
  p = np.asarray(p, dtype=float)
  m = len(p)
  order = np.argsort(p)
  k_max = 0
  for rank, idx in enumerate(order, start=1):
    if p[idx] <= alpha * rank / m:
      k_max = rank
  out = np.zeros(m, dtype=bool)
  out[order[:k_max]] = True
  return out


@pytest.mark.parametrize("p,expected", [
  ([0.005, 0.01, 0.03, 0.03, 0.04, 0.20, 0.5, 0.9], 2),
  ([0.011, 0.04, 0.026, 0.045], 4),          # step-up: p(2), p(3) fail their thresholds but p(4) passes
  ([0.015, 0.015, 0.015, 0.015, 0.9], 4),    # ties are rejected together
  ([0.2, 0.3, 0.4], 0),
  ([0.001], 1),
])
def test_bh_hand_computed(p, expected):
  p = np.array(p)
  got = pm.benjamini_hochberg(p)
  assert got.sum() == expected
  assert np.array_equal(got, _bh_reference(p))


def test_bh_ties_shape_and_monotonicity():
  rng = np.random.default_rng(0)
  for _ in range(100):
    p = np.round(rng.uniform(0, 0.1, 21), 3)  # many ties
    rej = pm.benjamini_hochberg(p)
    assert np.array_equal(rej, _bh_reference(p))
    if rej.any() and (~rej).any():
      assert p[rej].max() <= p[~rej].min()    # rejected set is a prefix of the sorted p
    for lo, hi in ((0.01, 0.05), (0.05, 0.2)):  # larger alpha never rejects fewer
      assert pm.benjamini_hochberg(p, lo).sum() <= pm.benjamini_hochberg(p, hi).sum()
    tied = p == p[0]
    assert len(set(rej[tied])) == 1           # equal p-values share a decision
  m = rng.uniform(0, 0.02, (7, 7))
  assert pm.benjamini_hochberg(m).shape == (7, 7)


# ------------------------------------------------------------------ PF-20: (A) vs (B)

def _edge_fn(sign_other):
  def fn(windows, fs, band):
    m = float(np.mean(windows[:, 0, 0]))
    out = np.zeros((3, 3))
    out[0, 1] = out[1, 0] = m
    out[0, 2] = out[2, 0] = sign_other * m
    np.fill_diagonal(out, np.nan)
    return out
  return fn


def test_global_p_without_fdr_edge_and_fdr_edge_without_global_p():
  rng = np.random.default_rng(2)
  hi, lo = _scalar_windows(rng, 12, 5.0), _scalar_windows(rng, 18, 0.0)
  hi, lo = np.repeat(hi, 3, axis=1), np.repeat(lo, 3, axis=1)
  # (B) only: one of three edges moves; its edge p = 1/30 > BH threshold 0.05/3, global p = 1/30 < 0.05
  b_only = pm.compute_permutation_test(hi, lo, BAND, FS, 29, _edge_fn(0.0), 1, 1)
  assert b_only["p_one_tailed"] < 0.05 and b_only["significant_uncorrected"]
  assert b_only["n_edges_sig_fdr"] == 0
  # (A) only: two edges move in opposite directions, the global mean cancels
  a_only = pm.compute_permutation_test(hi, lo, BAND, FS, 99, _edge_fn(-1.0), 1, 1)
  assert a_only["n_edges_sig_fdr"] >= 1
  assert a_only["p_one_tailed"] >= 0.05 and not a_only["significant_uncorrected"]


def test_summary_columns_keep_the_two_criteria_separate_and_console_lists_both():
  rows = []
  for s, fdr, p in (("S01", 3, 0.30), ("S02", 0, 0.01), ("S03", 5, 0.01), ("S04", 0, 0.60)):
    rows.append(dict(subject=s, method="wpli", condition=101, n_edges_sig_fdr=fdr, p_one_tailed=p,
                     permutation_unit="trial"))
  lines = "\n".join(cohort.criteria_report(pd.DataFrame(rows), 0.05))
  assert "(A) >=1 FDR edge: ['S01', 'S03']" in lines
  assert "(B) global p < 0.05: ['S02', 'S03']" in lines
  assert "wpli (trial-level)" in lines


# ------------------------------------------------------------------ PF-03: ids before the gate

def test_trial_ids_are_built_pre_gate_then_masked_like_windows(monkeypatch):
  # a 101 block of two trials (10 windows); gate rejects window 2 of the first trial
  y = np.array([201] * 2 + [101] * 10 + [201] * 2)
  n = len(y)
  c = 3
  windows = np.random.default_rng(0).standard_normal((n, c, 256))
  ids_pre = build_trial_ids(y, {201: 2, 101: 5})
  mask = np.ones(n, dtype=bool)
  mask[4] = False  # third window of the first 101 trial
  quality = dict(valid_mask=mask.astype(int), windows_clean=windows[mask], y_clean=y[mask],
                 channels_kept=["a", "b", "c"], channels_dropped=[])
  seen = {}

  def spy(stim, base, band, fs, n_perm, fn, n_jobs, seed, alpha, sid, bid, directed):
    seen["stim"], seen["base"] = np.asarray(sid), np.asarray(bid)
    return dict(dummy=True)

  monkeypatch.setattr(pm, "compute_permutation_test", spy)
  pm.extract_connectivity_by_condition(windows, y, FS, pc.compute_condition_plv, [101], ["a", "b", "c"],
                                       n_permutations=2, trial_ids=ids_pre, quality=quality)
  sel = (y == 101)[mask]
  assert np.array_equal(seen["stim"], ids_pre[mask][sel])
  assert list(seen["stim"]) == [ids_pre[2]] * 4 + [ids_pre[7]] * 5  # 4 + 5 windows
  rebuilt = build_trial_ids(y[mask], {201: 2, 101: 5}, warn=False)[sel]          # the post-gate (buggy) ids
  assert not np.array_equal(seen["stim"], rebuilt)                   # re-chunking would shift the boundary
  assert len(seen["base"]) == int((y[mask] == 201).sum())


# ------------------------------------------------------------------ determinism

def test_determinism_n_jobs_and_seed_sensitivity():
  stim, base, ids_s, ids_b = _toy(c=4, seed=5)
  kw = dict(stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
  slow_plv = lambda w, fs, b: pc.compute_condition_plv(w, fs, b)  # noqa: E731  (no fast path)
  for fn in (slow_plv, mp.compute_condition_pdc, ce.compute_condition_coherence):
    r1 = pm.compute_permutation_test(stim, base, BAND, FS, 10, fn, 1, 11, **kw)
    r2 = pm.compute_permutation_test(stim, base, BAND, FS, 10, fn, 2, 11, **kw)
    assert np.array_equal(r1["null_distribution"], r2["null_distribution"])
    assert np.array_equal(r1["edge_p_one_tailed"], r2["edge_p_one_tailed"])
    assert np.array_equal(r1["fdr_significant"], r2["fdr_significant"])
    assert r1["p_one_tailed"] == r2["p_one_tailed"]
  r_a = pm.compute_permutation_test(stim, base, BAND, FS, 10, slow_plv, 1, 11, **kw)
  r_b = pm.compute_permutation_test(stim, base, BAND, FS, 10, slow_plv, 1, 12, **kw)
  assert not np.array_equal(r_a["null_distribution"], r_b["null_distribution"])


# ------------------------------------------------------------------ null calibration (loose)

def test_null_calibration_loose_across_methods():
  rej = 0
  total = 0
  for seed in range(12):
    rng = np.random.default_rng(300 + seed)
    a, b = rng.standard_normal((30, 4, 256)), rng.standard_normal((40, 4, 256))
    ia, ib = np.repeat(np.arange(6), 5), np.repeat(np.arange(20), 2)
    r = pm.compute_permutation_test(a, b, BAND, FS, 49, pc.compute_condition_plv, 1, seed,
                                    stim_trial_ids=ia, baseline_trial_ids=ib)
    rej += r["p_one_tailed"] < 0.05
    total += 1
    assert r["n_edges_sig_fdr"] <= 2
  assert rej <= 4  # nominal 5 % of 12 is 0.6; loose upper bound


# ------------------------------------------------------------------ schemas

SUMMARY_COLS_S6 = ["subject", "method", "condition", "frequency_hz", "label", "obs_diff", "p_one_tailed",
                   "significant_uncorrected", "n_edges_sig_uncorrected", "n_edges_sig_fdr", "total_edges",
                   "n_channels", "channels_dropped", "permutation_unit", "fdr_backed"]


def _tree(root, seed=0):
  rng = np.random.default_rng(seed)
  labels = []
  for _ in range(4):
    for c in (201, 101, 201, 102, 201, 103, 201, 104, 201, 105):
      labels += [c] * (2 if c == 201 else 5)
    labels += [202]
  y = np.array(labels)
  d = root / "S01"
  d.mkdir(parents=True)
  np.save(d / "X_time_windows.npy", 10.0 * rng.standard_normal((len(y), 7, 256)))
  np.save(d / "y_labels.npy", y)


def test_cohort_summary_and_npz_schema(tmp_path, capsys):
  _tree(tmp_path / "data")
  rep = tmp_path / "rep"
  rc = cohort.main(["--methods", "plv", "pdc", "--permutations", "7", "--n-jobs", "1",
                    "--data-root", str(tmp_path / "data"), "--reports-dir", str(rep)])
  assert rc == 0
  out = capsys.readouterr().out
  assert "(A)" in out and "(B)" in out
  df = pd.read_csv(rep / "connectivity_cohort_summary.csv")
  assert list(df.columns) == SUMMARY_COLS_S6
  assert len(df) == 10 and set(df["condition"]) == {101, 102, 103, 104, 105}
  assert set(df["permutation_unit"]) == {"trial"}
  assert sorted(df["frequency_hz"].unique().round(2)) == [8.57, 10.91, 15.0, 20.0, 24.0]
  assert (df["p_one_tailed"] >= 1 / 8 - 1e-12).all() and (df["p_one_tailed"] <= 1).all()
  assert list(df["fdr_backed"]) == list(df["n_edges_sig_fdr"] >= 1)
  assert list(df["significant_uncorrected"]) == list(df["p_one_tailed"] < 0.05)
  assert set(df.loc[df.method == "pdc", "total_edges"]) == {42}
  assert set(df.loc[df.method == "plv", "total_edges"]) == {21}
  assert set(df["n_channels"]) == {7}
  for m in ("plv", "pdc"):
    z = np.load(rep / "connectivity_edges" / f"S01_{m}.npz")
    expected = {"channels_kept"} | {f"{k}_{c}" for c in (101, 102, 103, 104, 105)
                                    for k in ("stim", "base", "diff", "p", "fdr")}
    assert set(z.files) == expected
    assert z["stim_101"].shape == (7, 7) and z["fdr_101"].dtype == bool
    assert len(z["channels_kept"]) == 7
    assert z["p_101"].min() >= 1 / 8 - 1e-12
    if m == "pdc":
      assert np.all(np.diag(z["stim_101"]) == 0.0)
    else:
      assert np.all(np.isnan(np.diag(z["stim_101"])))
