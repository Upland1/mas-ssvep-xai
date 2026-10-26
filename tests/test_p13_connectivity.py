"""P13 builder tests: MVAR layout (PF-17), PDC direction, CSD phase (PF-18), permutations (R7, PF-19/20)."""

import numpy as np
import pandas as pd
import pytest

from scripts.connectivity.analysis import analyze_connectivity_cohort as cohort
from scripts.connectivity.diagnostics import demo_hilbert_edges as dh
from scripts.connectivity.diagnostics import demo_mvar_slicing as dm
from src.features.connectivity import connectivity_extraction as ce
from src.features.connectivity import mvar_pdc as mp
from src.features.connectivity import permutation as pm
from src.features.connectivity import phase_connectivity as pc

FS = 250.0
BAND = (23.0, 25.0)


# ---------------------------------------------------------------- MVAR / PDC (PF-17, R6)

def test_mvar_strided_recovers_var_contiguous_does_not():
  true = dm.random_var(0, c=4, p=3)
  w = dm.simulate_var(true, n=120, seed=1)
  wts = mp.fit_mvar_ols(w, 3)
  assert dm.rel_error(mp.mvar_coefficients(wts, 3), true) <= 0.15
  assert dm.rel_error(dm.contiguous_coefficients(wts, 3), true) >= 1.0  # the PF-17 bug fails


def test_mvar_demo_numbers():
  r = dm.run()
  assert r["strided_error"] <= 0.15 and r["contiguous_error"] >= 1.0


def test_design_rows_do_not_cross_windows():
  w = np.random.default_rng(0).standard_normal((3, 2, 12))
  x, y = mp._design(w, 4)
  assert x.shape == (3 * 8, 2 * 4) and y.shape == (3 * 8, 2)
  # row 0 of window 1 = lags 1..4 of channel 1 at t = 4 of window 1 only (channel-major columns)
  r = 8
  assert np.allclose(x[r, 4:8], w[1, 1, 0:4][::-1]) and np.allclose(y[r], w[1, :, 4])


def test_pdc_direction_and_normalisation():
  c, n, t = 4, 80, 256
  rng = np.random.default_rng(3)
  w = np.zeros((n, c, t))
  for k in range(n):
    x = np.zeros((c, t + 50)); e = rng.standard_normal((c, t + 50))
    for s in range(1, t + 50):
      x[:, s] = e[:, s] + 0.3 * x[:, s - 1]
      x[3, s] += 0.7 * x[0, s - 1]  # channel 0 drives channel 3
    w[k] = x[:, 50:]
  m = mp.compute_condition_pdc(w, FS, BAND, order=3)
  assert m[3, 0] > m[0, 3] + 0.3
  assert np.all(np.diag(m) == 0)
  full = mp.pdc_from_coefficients(mp.mvar_coefficients(mp.fit_mvar_ols(w, 3), 3), FS, np.array([10.0]))
  assert full.shape == (1, c, c)


def test_pdc_columns_normalised_with_diagonal():
  coefs = np.random.default_rng(0).standard_normal((2, 3, 3)) * 0.1
  a = np.abs(np.eye(3) - np.einsum("l,lij->ij", np.exp(-2j * np.pi * 10 * np.arange(1, 3) / FS), coefs))
  expected = a / np.sqrt((a ** 2).sum(axis=0, keepdims=True))
  got = mp.pdc_from_coefficients(coefs, FS, np.array([10.0]))[0]
  off = ~np.eye(3, dtype=bool)
  assert np.allclose(got[off], expected[off])


# ---------------------------------------------------------------- phase from the CSD (R3, PF-18)

def test_edge_immunity_csd_vs_hilbert():
  w = dh.make_windows(0)
  wc = dh.corrupt_edges(w)
  csd = abs(pc.compute_condition_plv(w, FS, BAND)[0, 1] - pc.compute_condition_plv(wc, FS, BAND)[0, 1])
  hil = dh.hilbert_plv(w, BAND, FS) - dh.hilbert_plv(wc, BAND, FS)
  assert csd <= 0.005
  assert hil > 5 * csd and hil > 0.01
  env = dh.edge_envelope_ratio(w, BAND, FS)
  assert env["first_min"] < 0.8 and env["last_min"] < 0.5


def test_wpli_ignores_zero_lag_plv_does_not():
  rng = np.random.default_rng(0)
  n, t = 80, 256
  tt = np.arange(t) / FS
  ph = rng.uniform(0, 2 * np.pi, (n, 1))
  s = np.sin(2 * np.pi * 24 * tt + ph)
  zero = np.stack([s, s], 1) + 0.05 * rng.standard_normal((n, 2, t))
  lag = np.stack([s, np.sin(2 * np.pi * 24 * tt + ph + 1.0)], 1) + 0.05 * rng.standard_normal((n, 2, t))
  assert pc.compute_condition_plv(zero, FS, BAND)[0, 1] > 0.95
  assert pc.compute_condition_wpli(zero, FS, BAND)[0, 1] < 0.15
  assert pc.compute_condition_wpli(lag, FS, BAND)[0, 1] > 0.9


def test_phase_matrices_symmetric_nan_diag_and_wpli_zero_denominator():
  w = np.random.default_rng(1).standard_normal((20, 3, 256))
  for fn in (pc.compute_condition_plv, pc.compute_condition_wpli):
    m = fn(w, FS, BAND)
    assert np.all(np.isnan(np.diag(m))) and np.allclose(m[0, 1], m[1, 0])
  s = np.ones((5, 2, 2), dtype=complex)  # real CSD: Im = 0 everywhere
  assert pc.wpli_from_csd(s)[0, 1] == 0.0
  with pytest.raises(ValueError):
    pc.compute_phase_connectivity(w, FS, BAND, "bad")


# ---------------------------------------------------------------- permutation machinery

def test_benjamini_hochberg_hand_case():
  p = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205])
  # m = 8, thresholds k * 0.05 / 8 = 0.00625, 0.0125, 0.01875, 0.025, ...: only p1, p2 pass? k=2: 0.008 <= 0.0125
  assert benjamini_list(p) == [True, True, False, False, False, False, False, False]
  q = np.array([0.01, 0.02, 0.03, 0.04, 0.9])  # thresholds 0.01, 0.02, 0.03, 0.04, 0.05: first four
  assert benjamini_list(q) == [True, True, True, True, False]
  assert benjamini_list(q[::-1]) == [False, True, True, True, True]  # order of the input is irrelevant


def benjamini_list(p):
  return pm.benjamini_hochberg(np.asarray(p)).tolist()


def _ids(sizes):
  return np.repeat(np.arange(len(sizes)), sizes)


@pytest.mark.parametrize("sizes,n_first", [([5] * 8, 40 // 2), ([5] * 8, 17), ([2] * 20, 13), ([5] * 8 + [2] * 20, 40)])
def test_trial_split_sizes_and_one_split(sizes, n_first):
  ids = _ids(sizes)
  for seed in range(30):
    a, b = pm._trial_permutation_split(ids, n_first, np.random.default_rng(seed))
    assert len(a) == n_first and len(b) == len(ids) - n_first
    assert len(np.intersect1d(a, b)) == 0 and len(np.union1d(a, b)) == len(ids)
    ta, tb = set(ids[a]), set(ids[b])
    assert len(ta & tb) <= 1  # at most one trial is split between the groups


def test_window_split_sizes():
  a, b = pm._window_permutation_split(30, 11, np.random.default_rng(0))
  assert len(a) == 11 and len(b) == 19 and len(np.union1d(a, b)) == 30


def test_seed_derivation_deterministic_and_distinct():
  assert pm.derive_seed(42, "S03", "pdc", 101) == pm.derive_seed(42, "S03", "pdc", 101)
  assert len({pm.derive_seed(42, "S03", "pdc", c) for c in (101, 102, 103)}) == 3
  assert pm.derive_seed(42, "S03", "pdc", 101) != pm.derive_seed(42, "S04", "pdc", 101)


def _planted(seed=0, n_s=40, n_b=60, c=5, planted=((0, 1), (2, 3)), amp=2.0):
  rng = np.random.default_rng(seed)
  tt = np.arange(256) / FS
  stim = rng.standard_normal((n_s, c, 256))
  base = rng.standard_normal((n_b, c, 256))
  for i, j in planted:
    ph = rng.uniform(0, 2 * np.pi, (n_s, 1))  # independent phase per planted pair
    s = amp * np.sin(2 * np.pi * 24 * tt + ph)
    stim[:, i] += s
    stim[:, j] += s
  ids_s, ids_b = np.repeat(np.arange(n_s // 5), 5), np.repeat(np.arange(n_b // 2), 2) + 100
  return stim, base, ids_s, ids_b


def test_planted_effect_min_p_and_fdr_on_planted_pairs():
  stim, base, ids_s, ids_b = _planted()
  r = pm.compute_permutation_test(stim, base, BAND, FS, 99, pc.compute_condition_plv, 1, 7,
                                  stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
  assert r["p_one_tailed"] == pytest.approx(1 / 100)
  assert r["permutation_unit"] == "trial" and r["total_edges"] == 10
  flagged = {tuple(ix) for ix in np.argwhere(r["fdr_significant"])}
  assert flagged == {(0, 1), (2, 3)}
  assert r["null_ci"][0] < r["null_mean"] < r["null_ci"][1]


def test_null_calibration_roughly_uniform():
  ps = []
  for seed in range(10):
    rng = np.random.default_rng(100 + seed)
    a, b = rng.standard_normal((40, 4, 256)), rng.standard_normal((60, 4, 256))
    r = pm.compute_permutation_test(a, b, BAND, FS, 50, pc.compute_condition_wpli, 1, seed,
                                    stim_trial_ids=np.repeat(np.arange(8), 5), baseline_trial_ids=np.repeat(np.arange(30), 2))
    ps.append(r["p_one_tailed"])
  assert sum(p < 0.05 for p in ps) <= 2


def test_fast_path_equals_direct_call():
  stim, base, ids_s, ids_b = _planted(1, 20, 30)
  for fn in (pc.compute_condition_plv, pc.compute_condition_wpli):
    r_fast = pm.compute_permutation_test(stim, base, BAND, FS, 15, fn, 1, 5, stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
    slow = lambda w, fs, b, f=fn: f(w, fs, b)  # noqa: E731  (no per_window attribute: direct path)
    r_slow = pm.compute_permutation_test(stim, base, BAND, FS, 15, slow, 1, 5, stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
    assert np.allclose(r_fast["null_distribution"], r_slow["null_distribution"])
    assert r_fast["p_one_tailed"] == r_slow["p_one_tailed"]


@pytest.mark.parametrize("fn", [ce.compute_condition_coherence, mp.compute_condition_pdc])
def test_determinism_across_n_jobs(fn):
  stim, base, ids_s, ids_b = _planted(2, 20, 30, c=4)
  kw = dict(stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
  r1 = pm.compute_permutation_test(stim, base, BAND, FS, 12, fn, 1, 9, **kw)
  r2 = pm.compute_permutation_test(stim, base, BAND, FS, 12, fn, 2, 9, **kw)
  assert np.array_equal(r1["null_distribution"], r2["null_distribution"])
  assert r1["p_one_tailed"] == r2["p_one_tailed"]


def test_directed_pdc_has_42_edges_symmetric_21():
  assert pm.edge_mask(7, True).sum() == 42 and pm.edge_mask(7, False).sum() == 21
  stim, base, ids_s, ids_b = _planted(3, 20, 30, c=4, planted=((0, 1),))
  r = pm.compute_permutation_test(stim, base, BAND, FS, 5, mp.compute_condition_pdc, 1, 1,
                                  stim_trial_ids=ids_s, baseline_trial_ids=ids_b)
  assert r["total_edges"] == 12 and r["directed"] is True


def test_window_unit_label_without_ids_and_ids_must_pair():
  stim, base, ids_s, _ = _planted(4, 10, 20, c=3, planted=((0, 1),))
  r = pm.compute_permutation_test(stim, base, BAND, FS, 5, pc.compute_condition_plv, 1)
  assert r["permutation_unit"] == "window"
  with pytest.raises(ValueError):
    pm.compute_permutation_test(stim, base, BAND, FS, 5, pc.compute_condition_plv, 1, stim_trial_ids=ids_s)


def test_criteria_a_and_b_disagree_and_are_reported_separately():
  rows = [dict(subject="S01", method="m", condition=101, n_edges_sig_fdr=3, p_one_tailed=0.30, permutation_unit="trial"),
          dict(subject="S02", method="m", condition=101, n_edges_sig_fdr=0, p_one_tailed=0.01, permutation_unit="trial")]
  text = "\n".join(cohort.criteria_report(pd.DataFrame(rows), 0.05))
  assert "(A) >=1 FDR edge: ['S01']" in text and "(B) global p < 0.05: ['S02']" in text


# ---------------------------------------------------------------- gate + trial ids (PF-03) and the cohort schema

def _tree(tmp_path, bad_window=None, seed=0):
  """Synthetic legacy tree: S01 with 4 blocks of every stimulus label (5 windows each) and 201 blocks (2)."""
  rng = np.random.default_rng(seed)
  labels = []
  for rep in range(4):
    for c in (201, 101, 201, 102, 201, 103, 201, 104, 201, 105):
      labels += [c] * (2 if c == 201 else 5)
    labels += [202]
  y = np.array(labels)
  X = 10.0 * rng.standard_normal((len(y), 7, 256))
  if bad_window is not None:
    X[bad_window] *= 100.0  # fails the vpp / std limits
  d = tmp_path / "S01"
  d.mkdir()
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  return y


def test_trial_ids_pre_gate_then_gate_mask(tmp_path):
  y = _tree(tmp_path)
  sel = ce.load_legacy_selection(tmp_path, "S01")
  assert not sel["trial_ids_approximate"]
  assert len(sel["trial_ids"]) == len(sel["y"]) == int((y != 202).sum())
  # drop one window of a stimulus block through the gate: its trial keeps the other windows' id (PF-03)
  y2 = _tree(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path, bad_window=14)
  g = ce.load_gated_conditions(tmp_path / "x", "S01")
  sel2 = ce.load_legacy_selection(tmp_path / "x", "S01")
  assert len(g["y"]) == len(sel2["y"]) - 1
  assert len(g["trial_ids"]) == len(g["y"])
  ids_full = sel2["trial_ids"]
  rejected = np.flatnonzero(ce.gate_selection(sel2)["valid_mask"] == 0)
  assert len(rejected) == 1
  assert np.array_equal(g["trial_ids"], np.delete(ids_full, rejected))


def test_cohort_schema_and_edges_on_synthetic_tree(tmp_path):
  _tree(tmp_path / "data_dir" if (tmp_path / "data_dir").mkdir() is None else tmp_path)
  rep = tmp_path / "rep"
  rc = cohort.main(["--methods", "wpli", "pdc", "--permutations", "9", "--n-jobs", "1", "--data-root",
                    str(tmp_path / "data_dir"), "--reports-dir", str(rep), "--out-suffix", "t"])
  assert rc == 0
  df = pd.read_csv(rep / "connectivity_cohort_summary_t.csv")
  assert list(df.columns) == cohort.SUMMARY_COLUMNS
  assert set(df["method"]) == {"wpli", "pdc"} and len(df) == 10
  assert set(df.loc[df["method"] == "pdc", "total_edges"]) == {42}
  assert set(df.loc[df["method"] == "wpli", "total_edges"]) == {21}
  assert set(df["permutation_unit"]) == {"trial"}
  z = np.load(rep / "connectivity_edges_t" / "S01_wpli.npz")
  assert {"channels_kept", "stim_101", "base_101", "diff_101", "p_101", "fdr_101"} <= set(z.files)
  alpha = pd.read_csv(rep / "connectivity_alpha_diagnostic_t.csv")
  assert set(alpha["condition"]) == {104, 105}
  det = pd.read_csv(rep / "connectivity_cohort_summary_t_details.csv")
  assert (det["n_permutations"] == 9).all()


def test_compare_lists_flips(tmp_path):
  base = dict(subject="S01", method="m", condition=101, frequency_hz=24.0, permutation_unit="trial")
  a = pd.DataFrame([dict(base, p_one_tailed=0.04, n_edges_sig_fdr=0), dict(base, subject="S02", p_one_tailed=0.5, n_edges_sig_fdr=0)])
  b = pd.DataFrame([dict(base, p_one_tailed=0.06, n_edges_sig_fdr=2), dict(base, subject="S02", p_one_tailed=0.4, n_edges_sig_fdr=0)])
  a.to_csv(tmp_path / "connectivity_cohort_summary_a.csv", index=False)
  b.to_csv(tmp_path / "connectivity_cohort_summary.csv", index=False)
  flips = cohort.compare_runs(tmp_path, "a", "")
  assert len(flips) == 1 and flips.loc[0, "subject"] == "S01" and bool(flips.loc[0, "flip_A"]) and bool(flips.loc[0, "flip_B"])


def _trial_process(rng, n_trials, per, c=2):
  """Windows of one trial share a random coupling strength (within-trial dependence, PF-19)."""
  tt = np.arange(256) / FS
  out, ids = [], []
  for k in range(n_trials):
    a = rng.choice([0.0, 2.5])
    for _ in range(per):
      s = np.sin(2 * np.pi * 24 * tt + rng.uniform(0, 2 * np.pi))
      w = rng.standard_normal((c, 256))
      w[0] += a * s
      w[1] += a * s
      out.append(w)
      ids.append(k)
  return np.array(out), np.array(ids)


def test_window_level_null_too_narrow_trial_level_calibrated():
  rej = {"window": 0, "trial": 0}
  n_rep = 40
  for seed in range(n_rep):
    rng = np.random.default_rng(500 + seed)
    a, ia = _trial_process(rng, 8, 5)
    b, ib = _trial_process(rng, 15, 2)
    ib = ib + 100
    for unit, kw in (("window", {}), ("trial", dict(stim_trial_ids=ia, baseline_trial_ids=ib))):
      r = pm.compute_permutation_test(a, b, BAND, FS, 99, pc.compute_condition_plv, 1, seed, **kw)
      rej[unit] += r["p_two_tailed"] < 0.05
  assert rej["window"] > rej["trial"]  # PF-19: window-level permutations reject the null too often
  assert rej["window"] >= 4 and rej["trial"] <= 3  # nominal 5 % of 40 is 2
