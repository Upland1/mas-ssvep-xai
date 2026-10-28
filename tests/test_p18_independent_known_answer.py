"""P18 Network-Based Statistic: independent known-answer tests (synthetic-tester; written without the builder's file).

Every expected value is derived by hand or by a small brute-force reference defined here (BFS components, explicit
nested loops for the edge layout, plain numpy for the pseudo-z). Nothing reads generated or git-ignored files.
"""

from collections import deque

import numpy as np
import pandas as pd
import pytest

from scripts.connectivity.analysis import analyze_connectivity_cohort as cohort
from scripts.connectivity.comparison import test_connectivity_frequency_differences as pair
from src.features.connectivity import connectivity_extraction as ce
from src.features.connectivity import permutation as pm
from src.stats import nbs
from tests import p16_synth


# ------------------------------------------------------------------ references


def pairs_of(c):
  return [(i, j) for i in range(c) for j in range(i + 1, c)]


def eidx(c, a, b):
  return pairs_of(c).index((min(a, b), max(a, b)))


def ref_components(supra, c):
  """BFS over nodes; returns a list of edge-index lists (one per component with >= 1 edge)."""
  prs = pairs_of(c)
  adj = {k: [] for k in range(c)}
  for e, on in enumerate(supra):
    if on:
      i, j = prs[e]
      adj[i].append(j)
      adj[j].append(i)
  seen, comps = set(), []
  for s in range(c):
    if s in seen or not adj[s]:
      continue
    q, nodes = deque([s]), {s}
    seen.add(s)
    while q:
      u = q.popleft()
      for v in adj[u]:
        if v not in seen:
          seen.add(v)
          nodes.add(v)
          q.append(v)
    comps.append([e for e, on in enumerate(supra) if on and prs[e][0] in nodes])
  return comps


def ref_nbs(obs, null, t, two=False):
  mu, sd = null.mean(0), null.std(0)
  zo = np.array([(o - m) / s if s > 0 and np.isfinite(s) else 0.0 for o, m, s in zip(obs, mu, sd)])
  zn = np.array([[(x - m) / s if s > 0 and np.isfinite(s) else 0.0 for x, m, s in zip(row, mu, sd)] for row in null])
  if two:
    zo, zn = np.abs(zo), np.abs(zn)
  c = nbs.n_channels_from_edges(len(obs))
  size = max([len(k) for k in ref_components(zo > t, c)], default=0)
  nm = np.array([max([len(k) for k in ref_components(z > t, c)], default=0) for z in zn])
  return size, nm, (1 + (nm >= size).sum()) / (len(null) + 1)


# ------------------------------------------------------------------ pseudo-z


def test_pseudo_z_known_null_mean_and_std():
  rng = np.random.default_rng(0)
  # null built so each edge has exactly mean m and std s (n = 2: values m -/+ s)
  m, s = np.array([1.0, -2.0, 0.5]), np.array([2.0, 0.5, 4.0])
  null = np.stack([m - s, m + s])
  obs = np.array([5.0, -3.0, 0.5])
  zo, zn = nbs.edge_pseudo_z(obs, null)
  assert np.allclose(zo, [2.0, -2.0, 0.0], atol=1e-12)
  assert np.allclose(zn, [[-1, -1, -1], [1, 1, 1]], atol=1e-12)
  zo2, zn2 = nbs.edge_pseudo_z(obs, null, two_tailed=True)
  assert np.allclose(zo2, [2, 2, 0]) and (zn2 >= 0).all()
  big = rng.normal(3.0, 7.0, size=(5000, 4))
  _, zb = nbs.edge_pseudo_z(np.zeros(4), big)
  assert np.allclose(zb.mean(0), 0, atol=1e-12) and np.allclose(zb.std(0), 1, atol=1e-12)


def test_pseudo_z_zero_or_nonfinite_std_is_zero_not_inf():
  null = np.array([[1.0, 2.0, np.nan, 4.0], [1.0, 3.0, 1.0, 6.0], [1.0, 4.0, 2.0, 8.0]])
  obs = np.array([9.0, 3.0, 5.0, 4.0])
  zo, zn = nbs.edge_pseudo_z(obs, null)
  assert zo[0] == 0 and zo[2] == 0 and np.isfinite(zo).all() and np.isfinite(zn).all()   # std 0 ; nan std
  assert (zn[:, 0] == 0).all() and (zn[:, 2] == 0).all()
  assert zo[1] == pytest.approx(0.0) and zo[3] == pytest.approx((4 - 6) / np.std([4, 6, 8]))
  zo_inf, _ = nbs.edge_pseudo_z(np.array([np.inf, 3, 5, 4.0]), null)
  assert np.isfinite(zo_inf).all()


# ------------------------------------------------------------------ components, layout (R6)


def test_components_planted_clique_path_and_isolated_edge_sizes_are_edge_counts():
  c = 10
  planted = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]            # 4-clique: 4 nodes, 6 edges
  path = [(4, 5), (5, 6)]                                                # 2 edges
  iso = [(7, 8)]
  supra = np.zeros(45, bool)
  for a, b in planted + path + iso:
    supra[eidx(c, a, b)] = True
  lab, sizes = nbs.edge_components(supra, c)
  assert sorted(sizes.tolist()) == [1, 2, 6] and nbs.max_component_size(supra, c) == 6
  assert len({lab[eidx(c, a, b)] for a, b in planted}) == 1
  assert lab[eidx(c, 4, 5)] == lab[eidx(c, 5, 6)] != lab[eidx(c, 7, 8)]
  assert (lab[~supra] == -1).all()
  assert sizes[lab[eidx(c, 0, 1)]] == 6
  rng = np.random.default_rng(1)
  for _ in range(60):
    sp = rng.random(45) < rng.choice([0.05, 0.15, 0.3])
    want = sorted(len(k) for k in ref_components(sp, c))
    assert sorted(nbs.edge_components(sp, c)[1].tolist()) == want


def test_no_supra_threshold_edge_gives_size_zero():
  assert nbs.max_component_size(np.zeros(28, bool), 8) == 0
  r = nbs.nbs_test(np.zeros(28), np.zeros((9, 28)), 2.0)
  assert r["max_size"] == 0 and r["n_sig_edges"] == 0 and r["p"] == 1.0 and not r["significant"]


def test_upper_triangle_layout_matches_nested_loops_and_roundtrips():
  c = 6
  m = np.arange(c * c, dtype=float).reshape(c, c)
  m = m + m.T
  want = np.array([m[i, j] for i in range(c) for j in range(i + 1, c)])
  assert np.array_equal(nbs.matrix_to_edges(m), want)
  back = nbs.edges_to_matrix(want, c)
  assert np.array_equal(back, back.T) and np.array_equal(np.diag(back), np.zeros(c))
  assert np.array_equal(back[np.triu_indices(c, 1)], want)
  stack = np.stack([m, 2 * m])
  assert np.array_equal(nbs.matrix_to_edges(stack)[1], 2 * want)
  assert nbs.n_channels_from_edges(21) == 7 and nbs.n_channels_from_edges(28) == 8
  with pytest.raises(ValueError):
    nbs.n_channels_from_edges(22)
  sp = np.zeros(15, bool)
  for a, b in [(1, 4), (4, 2), (0, 5)]:
    sp[eidx(c, a, b)] = True
  assert sorted(nbs.edge_components(sp, c)[1].tolist()) == [1, 2]
  assert eidx(c, 0, 5) == 4 and eidx(c, 1, 4) == 7


# ------------------------------------------------------------------ null and p formula


def test_p_value_formula_with_constructed_null_maxima_and_plus_one():
  c, n = 6, 20
  obs = np.zeros(15)
  for a, b in [(0, 1), (1, 2), (2, 3)]:                                   # path of 3 edges
    obs[eidx(c, a, b)] = 3.0
  sizes = [3, 3, 4, 5, 3, 10, 2, 1, 0, 2, 2, 1, 1, 2, 2, 0, 0, 1, 2, 2]  # exactly six with max >= 3
  zn = np.zeros((n, 15))
  for r, k in enumerate(sizes):
    if k <= 5:
      chosen = [(0, j) for j in range(1, c)][:k]                          # star: one component of k edges
    else:
      chosen = [(i, j) for i in range(5) for j in range(i + 1, 5)]        # 5-clique: 10 edges
    for a, b in chosen:
      zn[r, eidx(c, a, b)] = 3.0
  res = nbs.nbs_test(obs, zn, 2.0)
  assert res["max_size"] == 3
  assert res["null_max"].tolist() == sizes
  assert res["p"] == pytest.approx((1 + 6) / (n + 1)) and res["p"] != pytest.approx(6 / n)
  assert not res["significant"] and res["n_sig_edges"] == 0
  obs2 = np.zeros(15)
  for a, b in [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (4, 5)]:
    obs2[eidx(c, a, b)] = 3.0
  r2 = nbs.nbs_test(obs2, np.zeros((n, 15)), 2.0)
  assert r2["max_size"] == 11 and r2["p"] == pytest.approx(1 / 21) and r2["significant"]
  assert np.array_equal(r2["mask"], obs2 > 0)
  zn3 = np.zeros((n, 15))                                                 # a tie counts (>=)
  zn3[0, eidx(c, 0, 1)] = zn3[0, eidx(c, 1, 2)] = zn3[0, eidx(c, 2, 3)] = 3.0
  assert nbs.nbs_test(obs, zn3, 2.0)["p"] == pytest.approx(2 / 21)


def test_null_max_uses_each_permutations_own_zmap_from_raw_statistics():
  """Heterogeneous per-edge null scales: the cluster edges have tiny null spread, the rest a large one."""
  rng = np.random.default_rng(3)
  c, n = 8, 300
  scale = np.full(28, 1.0)
  clique = [eidx(c, a, b) for a in range(4) for b in range(a + 1, 4)]
  scale[clique] = 0.05
  mean = rng.normal(0, 0.3, 28)
  null = mean + scale * rng.standard_normal((n, 28))
  obs = mean.copy()
  obs[clique] += 0.05 * 4.0                                              # z about 4 on the clique
  res = nbs.nbs_sweep(obs, null, (2.0,))[2.0]
  size, nm, p = ref_nbs(obs, null, 2.0)
  assert res["max_size"] == size >= 6
  assert np.array_equal(res["null_max"], nm) and res["p"] == pytest.approx(p)
  zg = (null - obs.mean()) / obs.std()                                   # a single global (observed) scale
  alt = np.array([nbs.max_component_size(z > 2.0, c) for z in zg])
  assert not np.array_equal(alt, nm)


def test_random_cross_check_against_bruteforce_reference():
  rng = np.random.default_rng(11)
  for case in range(25):
    c = int(rng.choice([4, 6, 7, 8]))
    e = c * (c - 1) // 2
    null = rng.standard_normal((40, e)) * rng.uniform(0.2, 3, e) + rng.normal(0, 1, e)
    obs = null.mean(0) + rng.normal(0, 2.5, e) * null.std(0)
    two = bool(case % 2)
    out = nbs.nbs_sweep(obs, null, (1.5, 2.0, 2.5, 3.0), two_tailed=two)
    for t, r in out.items():
      size, nm, p = ref_nbs(obs, null, t, two)
      assert r["max_size"] == size and np.array_equal(r["null_max"], nm) and r["p"] == pytest.approx(p)
      assert r["possible_edges"] == e and r["n_channels"] == c


def test_tails_and_strict_threshold():
  c = 5
  null = np.array([[-1.0] * 10, [1.0] * 10])                              # mean 0, std 1 per edge
  obs = np.zeros(10)
  obs[eidx(c, 0, 1)] = obs[eidx(c, 1, 2)] = -4.0                          # strongly negative cluster of 2
  one = nbs.nbs_sweep(obs, null, (2.0,))[2.0]
  two = nbs.nbs_sweep(obs, null, (2.0,), two_tailed=True)[2.0]
  assert one["max_size"] == 0 and two["max_size"] == 2
  obs_eq = np.zeros(10)
  obs_eq[eidx(c, 0, 1)] = 2.0                                             # z == threshold: not supra
  assert nbs.nbs_sweep(obs_eq, null, (2.0,))[2.0]["max_size"] == 0
  obs_eq[eidx(c, 0, 1)] = 2.0001
  assert nbs.nbs_sweep(obs_eq, null, (2.0,))[2.0]["max_size"] == 1


# ------------------------------------------------------------------ sweep


def test_sweep_sizes_non_increasing_and_same_permutations():
  rng = np.random.default_rng(5)
  e = 28
  null = rng.standard_normal((120, e))
  obs = rng.normal(0, 1.8, e)
  th = (1.5, 2.0, 2.5, 3.0)
  out = nbs.nbs_sweep(obs, null, th)
  sizes = [out[t]["max_size"] for t in th]
  assert sizes == sorted(sizes, reverse=True)
  for lo, hi in zip(th[:-1], th[1:]):
    assert (out[lo]["null_max"] >= out[hi]["null_max"]).all()
    assert len(out[lo]["null_max"]) == len(out[hi]["null_max"]) == 120


# ------------------------------------------------------------------ PDC (PF-25)


def test_pdc_is_symmetrized_before_nbs_obs_and_null():
  c = 4
  rng = np.random.default_rng(2)
  obs = np.zeros((c, c))
  for a, b in [(1, 0), (2, 1), (2, 0)]:                                   # lower triangle only
    obs[a, b] = 10.0
  null = 0.5 * rng.standard_normal((200, c, c))
  r = {"observed_diff": obs, "null_matrices": null}
  sym = cohort.nbs_for_result(r, True, (2.0,), 0.05)[2.0]
  assert sym["max_size"] == 3 and sym["n_channels"] == 4 and sym["possible_edges"] == 6
  bad = cohort.nbs_for_result(r, False, (2.0,), 0.05)[2.0]                 # upper triangle only sees zeros
  assert bad["max_size"] < 3
  # the null is symmetrized too: antisymmetric null noise cancels, so its std is 0 and z = 0
  a = rng.choice([-1.0, 1.0], size=200)
  null2 = np.zeros((200, c, c))
  null2[:, 0, 1], null2[:, 1, 0] = a, -a
  obs2 = np.zeros((c, c))
  obs2[0, 1], obs2[1, 0] = 3.0, -3.0
  r2 = cohort.nbs_for_result({"observed_diff": obs2, "null_matrices": null2}, True, (2.0,), 0.05)[2.0]
  assert r2["max_size"] == 0
  b1 = cohort.nbs_for_result({"observed_diff": obs.T, "null_matrices": np.swapaxes(null, 1, 2)}, True, (2.0,), 0.05)[2.0]
  assert b1["max_size"] == 3 and np.array_equal(b1["mask"], sym["mask"])
  assert np.allclose(nbs.matrix_to_edges(obs, True), (nbs.matrix_to_edges(obs) + nbs.matrix_to_edges(obs.T)) / 2)


# ------------------------------------------------------------------ type-I rate and power at the statistic level


def _trial_edges(rng, n_trials, c, t, coupled=0.0, clique=()):
  out = np.empty((n_trials, c * (c - 1) // 2))
  for k in range(n_trials):
    x = rng.standard_normal((c, t))
    if coupled and len(clique):
      x[list(clique)] += coupled * rng.standard_normal((1, t))
    out[k] = nbs.matrix_to_edges(np.corrcoef(x))
  return out


def _perm_test(x, na, rng, n_perm=199):
  obs = x[:na].mean(0) - x[na:].mean(0)
  null = np.empty((n_perm, x.shape[1]))
  for i in range(n_perm):
    idx = rng.permutation(len(x))
    null[i] = x[idx[:na]].mean(0) - x[idx[na:]].mean(0)
  return obs, null


def test_type_one_rate_independent_channels():
  """400 seeds; X ~ Bin(400, <= 0.05): mean <= 20, sd <= 4.36; assert 1 <= X <= 37 (mean + 4 sd)."""
  n_seeds, hits = 400, 0
  for seed in range(n_seeds):
    rng = np.random.default_rng(1000 + seed)
    x = _trial_edges(rng, 24, 8, 96)
    obs, null = _perm_test(x, 12, rng)
    hits += nbs.nbs_sweep(obs, null, (2.0,))[2.0]["p"] < 0.05
  print(f"TYPE1 {hits}/{n_seeds} = {hits / n_seeds:.4f}")
  assert 1 <= hits <= 37, f"{hits}/{n_seeds} = {hits / n_seeds:.3f}"


def test_power_planted_coupled_subnetwork_statistic_level():
  c, clique = 8, (1, 2, 5, 6)
  planted = {eidx(c, a, b) for a in clique for b in clique if a < b}
  found = 0
  for seed in range(10):
    rng = np.random.default_rng(50 + seed)
    xa = _trial_edges(rng, 12, c, 96, coupled=1.5, clique=clique)
    xb = _trial_edges(rng, 12, c, 96)
    obs, null = _perm_test(np.vstack([xa, xb]), 12, rng)
    r = nbs.nbs_sweep(obs, null, (2.0,))[2.0]
    if r["significant"]:
      found += 1
      assert planted <= set(np.flatnonzero(r["mask"]).tolist())
      assert r["n_sig_edges"] <= 12
  print(f"POWER {found}/10")
  assert found >= 9


# ------------------------------------------------------------------ cohort script on a synthetic built folder


CLIQUE = (2, 3, 5, 6)         # POz PO4 O1 Oz


def _planted_block(seed, n_trials, coupled):
  b = p16_synth.make_block(n_trials=n_trials, seed=seed, tone_amp=0.0)
  fs = p16_synth.FS
  mark = b[10]
  t = np.arange(b.shape[1]) / fs
  if coupled:
    for s in np.flatnonzero((mark >= 101) & (mark <= 105)):
      f = p16_synth.TARGETS[int(mark[s])]
      a, e = int(s), int(s) + 5 * fs
      b[list(CLIQUE), a:e] += 12.0 * np.sin(2 * np.pi * f * t[a:e])[None]
  return b


def _write(root, subject, coupled, seed, bad_channel=None, n_trials=20):
  from scripts import build_windows as bw
  b = _planted_block(seed, n_trials, coupled)
  if bad_channel:
    b[p16_synth.SCALP.index(bad_channel)] = np.random.default_rng(9).normal(0, 80.0, b.shape[1])
  params = p16_synth.build_params("continuous")
  built = bw.build_subject(b[:8], b[10], float(p16_synth.FS), params)
  meta = bw.build_meta(built, params, float(p16_synth.FS), subject, "synthetic_session", "test")
  bw.save_built(root / subject, built, meta)


@pytest.fixture(scope="module")
def cohort_root(tmp_path_factory):
  root = tmp_path_factory.mktemp("built18i")
  _write(root, "S01", True, 21)                       # 8 channels, planted coupled subnetwork
  _write(root, "S02", False, 22, bad_channel="PO8")   # 7 channels, no planted effect
  return root


@pytest.fixture(scope="module")
def cohort_out(cohort_root, tmp_path_factory):
  rep = tmp_path_factory.mktemp("rep18i")
  args = cohort.build_parser().parse_args(
    ["--methods", "plv", "wpli", "pdc", "--permutations", "99", "--n-jobs", "1", "--data-root", str(cohort_root),
     "--reports-dir", str(rep), "--out-suffix", "n"])
  return args, cohort.run_cohort(args)


def test_cohort_planted_subnetwork_found_with_planted_edges(cohort_out):
  args, out = cohort_out
  summ = out["summary"]
  rows = summ[(summ["subject"] == "S01") & (summ["method"] == "plv")]
  assert len(rows) == 5
  planted = {eidx(8, a, b) for a in CLIQUE for b in CLIQUE if a < b}
  ed = np.load(args.reports_dir / "connectivity_edges_n" / "S01_plv.npz")
  n_found = 0
  for _, row in rows.iterrows():
    mask = ed[f"nbs_{int(row['condition'])}"][np.triu_indices(8, 1)]
    if row["nbs_significant"]:
      n_found += 1
      assert planted <= set(np.flatnonzero(mask).tolist())
      assert row["nbs_n_sig_edges"] == mask.sum() >= 6
      assert row["nbs_max_size"] >= 6 and row["nbs_p"] < 0.05
  print(f"COHORT_PLANTED found {n_found}/5 {rows['nbs_max_size'].tolist()} {rows['nbs_p'].tolist()}")
  assert n_found >= 3, rows[["condition", "nbs_max_size", "nbs_p"]].to_string()


def test_cohort_possible_edges_from_kept_channels_7_vs_8(cohort_out):
  _, out = cohort_out
  gs = out["graph_size"]
  assert (gs[gs["subject"] == "S01"]["possible_edges_nbs"] == 28).all()
  assert (gs[gs["subject"] == "S02"]["possible_edges_nbs"] == 21).all()
  assert (gs[gs["subject"] == "S02"]["n_channels"] == 7).all()
  pdc = gs[gs["method"] == "pdc"]
  assert (pdc[pdc["subject"] == "S01"]["total_edges_fdr"] == 56).all()    # directed 8*7
  assert (pdc[pdc["subject"] == "S02"]["total_edges_fdr"] == 42).all()    # directed 7*6, FDR keeps directed edges
  und = gs[gs["method"] != "pdc"]
  assert (und["total_edges_fdr"] == und["possible_edges_nbs"]).all()
  assert np.allclose(gs["nbs_size_pct"], 100 * gs["nbs_max_size"] / gs["possible_edges_nbs"])


def test_cohort_criteria_are_separate_columns(cohort_out):
  _, out = cohort_out
  s = out["summary"]
  for col in ("n_edges_sig_fdr", "fdr_backed", "nbs_p", "nbs_significant", "p_one_tailed", "nbs_n_sig_edges"):
    assert col in s.columns
  assert (s["fdr_backed"] == (s["n_edges_sig_fdr"] >= 1)).all()
  assert (s["nbs_significant"] == (s["nbs_p"] < 0.05)).all()
  assert not s["nbs_p"].equals(s["p_one_tailed"])
  lines = "\n".join(cohort.criteria_report(s, 0.05, "nbs"))
  assert "(A) NBS" in lines and "(B) global p" in lines and ">=1 FDR" not in lines
  lines = "\n".join(cohort.criteria_report(s, 0.05, "fdr"))
  assert ">=1 FDR edge" in lines and "(B) global p" in lines and "NBS" not in lines


def test_cohort_sweep_table_on_same_permutations(cohort_out):
  _, out = cohort_out
  sw = out["sweep"]
  assert set(sw["threshold"]) == {1.5, 2.0, 2.5, 3.0}
  for _, g in sw.groupby(["subject", "method", "condition"]):
    g = g.sort_values("threshold")
    assert g["max_size"].is_monotonic_decreasing and g["n_sig_edges"].le(g["possible_edges"]).all()


def test_stats_fdr_keeps_fdr_columns_global_p_and_edge_arrays(cohort_root, tmp_path, capsys):
  common = ["--methods", "plv", "--permutations", "49", "--n-jobs", "1", "--data-root", str(cohort_root),
            "--subjects", "S02", "--reports-dir", str(tmp_path)]
  assert cohort.main(common + ["--stats", "nbs", "--out-suffix", "a"]) == 0
  o_nbs = capsys.readouterr().out
  assert cohort.main(common + ["--stats", "fdr", "--out-suffix", "b"]) == 0
  o_fdr = capsys.readouterr().out
  assert o_nbs != o_fdr
  a, b = (pd.read_csv(tmp_path / f"connectivity_cohort_summary_{k}.csv") for k in "ab")
  pd.testing.assert_frame_equal(a, b)
  za, zb = (np.load(tmp_path / f"connectivity_edges_{k}" / "S02_plv.npz") for k in "ab")
  assert sorted(za.files) == sorted(zb.files)
  for f in za.files:
    assert np.array_equal(za[f], zb[f]) or (za[f].dtype.kind == "f" and np.array_equal(za[f], zb[f], equal_nan=True))
  sel = ce.load_condition_windows(cohort_root, "S02", "shared", None)
  res = pm.extract_connectivity_by_condition(
    sel["windows"], sel["y"], sel["fs"], cohort.METHODS["plv"], list(ce.CONDITION_FREQS), sel["channel_names"],
    n_permutations=49, trial_ids=sel["trial_ids"], quality=sel["quality"], n_jobs=1, random_state=42, alpha=0.05,
    seed_keys=("S02", "plv"))
  res.pop("_meta")
  for c, r in res.items():
    row = a[a["condition"] == c].iloc[0]
    assert row["p_one_tailed"] == r["p_one_tailed"] and row["n_edges_sig_fdr"] == r["n_edges_sig_fdr"]
    assert np.array_equal(za[f"fdr_{c}"], r["fdr_significant"]) and np.array_equal(za[f"p_{c}"], r["edge_p_one_tailed"])


# ------------------------------------------------------------------ pairwise two-tailed NBS


def _corr_fn(windows, fs, band):
  return np.corrcoef(np.concatenate(list(windows), axis=1))


def _grp(rng, n, coupled):
  w = rng.standard_normal((n, 8, 64))
  if coupled:
    w[:, :4] += 2.0 * rng.standard_normal((n, 1, 64))
  return w


def _pairjob(mp, a_coupled, b_coupled, seed):
  mp.setitem(pair.METHODS, "synthcorr", _corr_fn)
  rng = np.random.default_rng(seed)
  base = _grp(rng, 60, False)
  wa, wb = _grp(rng, 40, a_coupled), _grp(rng, 40, b_coupled)
  return pair._pair_job("S01", "synthcorr", 101, 102, wa, np.arange(40), wb, np.arange(40), base, 256.0, 199,
                        100 + seed, 0.05)[4]


def test_pairwise_two_tailed_nbs_finds_planted_difference_of_either_sign(monkeypatch):
  for a, b in ((True, False), (False, True)):          # b > a gives negative z: only a two-tailed test finds it
    r = _pairjob(monkeypatch, a, b, 0)
    assert r["nbs_p"] < 0.05 and 6 <= r["n_edges_nbs"] <= 12 and r["nbs_max_size"] >= 6 and r["n_edges"] == 28


def test_pairwise_null_difference_rate(monkeypatch):
  """40 null cells: X ~ Bin(40, <= 0.05), mean <= 2, sd <= 1.38; assert X <= 7 (P < 1e-3)."""
  hits = sum(_pairjob(monkeypatch, False, False, s)["nbs_p"] < 0.05 for s in range(1, 41))
  print(f"PAIRNULL {hits}/40")
  assert hits <= 7, hits


def test_pairwise_summary_only_reproduces_summary_without_recomputation(cohort_root, tmp_path, capsys, monkeypatch):
  common = ["--data-root", str(cohort_root), "--reports-dir", str(tmp_path), "--methods", "plv", "wpli",
            "--subjects", "S02", "--out-suffix", "t", "--responders", "S01"]
  assert pair.main(common + ["--permutations", "9", "--splits", "2", "--n-jobs", "1"]) == 0
  full = capsys.readouterr().out.splitlines()
  monkeypatch.setattr(pair, "run", lambda *a, **k: pytest.fail("recomputed"))
  monkeypatch.setattr(pair, "load_subject_groups", lambda *a, **k: pytest.fail("recomputed"))
  assert pair.main(common + ["--summary-only"]) == 0
  again = capsys.readouterr().out.splitlines()
  keep = [ln for ln in again if ln.startswith(("==", "  p_mag", "  non_responders", "  responders", "split-half"))]
  assert len(keep) >= 5 and any("NBS p <" in ln for ln in keep)
  for ln in keep:
    assert ln in full
