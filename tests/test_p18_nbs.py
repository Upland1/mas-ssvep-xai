"""P18 Network-Based Statistic: known-answer tests of `src/stats/nbs.py` and of the two ports.

Synthetic data only. Edge vectors are in upper-triangle order (`np.triu_indices(C, 1)`). Planted components have
known sizes, null maxima are constructed so the p-value is known, and the cohort / pairwise scripts are checked
against the permutation functions they wrap (FDR, global p and edge arrays unchanged by the port, settled point 6).
"""

import numpy as np
import pandas as pd
import pytest

from scripts.connectivity.analysis import analyze_connectivity_cohort as cohort
from scripts.connectivity.comparison import test_connectivity_frequency_differences as pair
from src.features.connectivity import connectivity_extraction as ce
from src.features.connectivity import permutation as pm
from src.io.subject_data import load_subject
from src.stats import nbs
from tests import p16_synth


def edge_index(c, pairs):
  iu = np.triu_indices(c, 1)
  lookup = {(int(i), int(j)): k for k, (i, j) in enumerate(zip(*iu))}
  return np.array([lookup[tuple(sorted(p))] for p in pairs])


# ---------------------------------------------------------------- pseudo-z, components, p formula

def test_pseudo_z_exact_and_zero_std_edge():
  null = np.array([[-1.0, 5.0], [1.0, 5.0]])            # edge 0: mean 0, std 1; edge 1 constant (std 0)
  z_obs, z_null = nbs.edge_pseudo_z(np.array([3.0, 7.0]), null)
  assert np.allclose(z_obs, [3.0, 0.0], atol=1e-12) and np.isfinite(z_null).all()
  assert np.allclose(z_null, [[-1.0, 0.0], [1.0, 0.0]], atol=1e-12)
  z2, zn2 = nbs.edge_pseudo_z(np.array([-3.0, 7.0]), null, two_tailed=True)
  assert np.allclose(z2, [3.0, 0.0], atol=1e-12) and (zn2 >= 0).all()
  zn, _ = nbs.edge_pseudo_z(np.array([-3.0, 7.0]), null)
  assert zn[0] == -3.0                                    # one-tailed keeps the sign


def test_planted_cluster_largest_component_is_found_with_its_size():
  c = 8
  cluster = [(0, 1), (1, 2), (2, 3), (0, 2), (1, 3)]      # 5 edges on nodes 0-3
  z = np.zeros(28)
  z[edge_index(c, cluster + [(5, 6)])] = 5.0              # plus one isolated edge
  lab, sizes = nbs.edge_components(z > 2, c)
  assert sorted(sizes.tolist()) == [1, 5] and nbs.max_component_size(z > 2, c) == 5
  assert (lab[edge_index(c, cluster)] == lab[edge_index(c, cluster)[0]]).all()
  assert lab[edge_index(c, [(5, 6)])[0]] != lab[edge_index(c, cluster)[0]]
  # two disjoint clusters: the triangle (3 edges) beats the path (2 edges)
  z = np.zeros(28)
  z[edge_index(c, [(0, 1), (1, 2), (0, 2)] + [(4, 5), (5, 6)])] = 5.0
  assert nbs.max_component_size(z > 2, c) == 3


def test_edges_matrix_roundtrip_layout():
  c = 8
  m = np.arange(c * c, dtype=float).reshape(c, c)
  m = (m + m.T) / 2
  e = nbs.matrix_to_edges(m)
  iu = np.triu_indices(c, 1)
  assert np.array_equal(e, m[iu]) and nbs.n_channels_from_edges(len(e)) == c
  back = nbs.edges_to_matrix(e, c)
  assert np.array_equal(back[iu], m[iu]) and np.array_equal(back, back.T) and (np.diag(back) == 0).all()
  with pytest.raises(ValueError):
    nbs.n_channels_from_edges(20)


def test_null_max_from_each_permutations_own_map_and_p_formula():
  c, n = 5, 20
  tri = edge_index(c, [(0, 1), (1, 2), (0, 2)])
  far = edge_index(c, [(3, 4)])                           # disjoint from the triangle
  z_null = np.zeros((n, 10))
  z_null[:, far] = 3.0                                    # every permutation has a 1-edge component
  hit = [0, 3, 7, 11]                                     # four permutations also have a 3-edge triangle
  z_null[np.ix_(hit, tri)] = 3.0
  z_obs = np.zeros(10)
  z_obs[tri] = 4.0
  r = nbs.nbs_test(z_obs, z_null, threshold=2.0, alpha=0.05)
  assert r["max_size"] == 3 and sorted(set(r["null_max"].tolist())) == [1, 3] and (r["null_max"] == 3).sum() == 4
  assert r["p"] == (1 + 4) / (n + 1) and not r["significant"] and not r["mask"].any()
  # a 4-edge observed component (triangle + pendant) exceeds every null maximum: smallest attainable p
  z_obs[edge_index(c, [(2, 3)])] = 4.0
  r2 = nbs.nbs_test(z_obs, z_null, 2.0, 0.25)
  assert r2["max_size"] == 4 and r2["p"] == 1 / (n + 1) and r2["significant"]
  assert r2["possible_edges"] == 10 and r2["n_sig_edges"] == 4 and r2["mask"][tri].all()


def test_threshold_is_strict_and_two_tailed_uses_absolute_value():
  c = 3
  null = np.array([[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]] * 10)
  r = nbs.nbs_sweep(np.array([-3.0, -3.0, -3.0]), null, (2.0,), two_tailed=False)[2.0]
  assert r["max_size"] == 0                               # one-tailed: a large negative effect is not supra-threshold
  r = nbs.nbs_sweep(np.array([-3.0, -3.0, -3.0]), null, (2.0,), two_tailed=True)[2.0]
  assert r["max_size"] == 3
  r = nbs.nbs_sweep(np.array([2.0, 2.0, 2.0]), null, (2.0,))[2.0]
  assert r["max_size"] == 0                               # z == threshold is not above it


# ---------------------------------------------------------------- power, type-I rate, sweep

def _planted(rng, c=8, n=200, clique=(0, 1, 2, 3), shift=6.0):
  e = c * (c - 1) // 2
  null = rng.standard_normal((n, e))
  obs = rng.standard_normal(e)
  planted = edge_index(c, [(i, j) for i in clique for j in clique if i < j])
  obs[planted] += shift
  return obs, null, planted


def test_coupled_subnetwork_is_significant_and_mask_is_the_planted_edges():
  obs, null, planted = _planted(np.random.default_rng(0))
  r = nbs.nbs_sweep(obs, null, (2.0,))[2.0]
  assert r["significant"] and r["p"] == 1 / 201
  expect = np.zeros(28, dtype=bool)
  expect[planted] = True
  assert np.array_equal(r["mask"], expect)
  assert r["max_size"] == 6 and r["n_sig_edges"] == 6 and r["possible_edges"] == 28


def test_independent_networks_are_not_significant_in_most_seeds():
  rejected = 0
  n_seeds = 200
  for seed in range(n_seeds):
    rng = np.random.default_rng(1000 + seed)
    r = nbs.nbs_sweep(rng.standard_normal(28), rng.standard_normal((100, 28)), (2.0,))[2.0]
    rejected += r["p"] < 0.05
  assert 1 - rejected / n_seeds >= 0.90                   # nominal 0.95; fixed seeds, binomial slack


def test_sweep_sizes_are_non_increasing_in_threshold_on_the_same_permutations():
  obs, null, _ = _planted(np.random.default_rng(5), shift=3.0)
  sw = nbs.nbs_sweep(obs, null, (1.5, 2.0, 2.5, 3.0))
  ths = sorted(sw)
  assert ths == [1.5, 2.0, 2.5, 3.0]
  sizes = [sw[t]["max_size"] for t in ths]
  assert sizes == sorted(sizes, reverse=True) and sizes[0] > sizes[-1]
  for a, b in zip(ths[:-1], ths[1:]):
    assert (sw[a]["null_max"] >= sw[b]["null_max"]).all()  # the same permutations, a higher bar can only shrink


# ---------------------------------------------------------------- PDC symmetrization

def test_directed_matrix_is_symmetrized_before_nbs():
  c = 4
  m = np.zeros((c, c))
  m[0, 1], m[1, 2], m[0, 2] = 6.0, 6.0, 6.0               # only i -> j, j -> i stays 0
  e = nbs.matrix_to_edges(m, directed=True)
  assert np.allclose(e[edge_index(c, [(0, 1), (1, 2), (0, 2)])], 3.0) and np.array_equal(
    nbs.matrix_to_edges(m, True), nbs.matrix_to_edges(m.T, True))
  null = np.random.default_rng(0).standard_normal((50, c, c))
  e_null = nbs.matrix_to_edges(null, directed=True)
  assert e_null.shape == (50, 6) and np.allclose(e_null, (null + null.transpose(0, 2, 1))[:, [0, 0, 0, 1, 1, 2], [1, 2, 3, 2, 3, 3]] / 2)
  # transposing the observed matrix (reversing every arrow) leaves the NBS result unchanged
  big = 10 * m
  a = cohort.nbs_for_result(dict(observed_diff=big, null_matrices=null), True, (2.0,), 0.05)[2.0]
  b = cohort.nbs_for_result(dict(observed_diff=big.T, null_matrices=null), True, (2.0,), 0.05)[2.0]
  assert a["max_size"] == b["max_size"] == 3 and a["p"] == b["p"] and np.array_equal(a["mask"], b["mask"])
  assert a["possible_edges"] == 6                          # 4 channels: 6 undirected edges, not 12 directed


# ---------------------------------------------------------------- cohort port

@pytest.fixture(scope="module")
def built_root(tmp_path_factory):
  root = tmp_path_factory.mktemp("built18")
  p16_synth.write_built_subject(root, "S01", "continuous", n_trials=20, seed=3, spike_s=12.5, bad_channel="PO8")
  return root


@pytest.fixture(scope="module")
def cohort_run(built_root, tmp_path_factory):
  rep = tmp_path_factory.mktemp("rep18")
  args = cohort.build_parser().parse_args(
    ["--methods", "coherence", "pdc", "--permutations", "19", "--n-jobs", "1", "--data-root", str(built_root),
     "--reports-dir", str(rep), "--out-suffix", "t", "--stats", "fdr"])
  return args, cohort.run_cohort(args)


def test_cohort_fdr_global_p_and_edges_equal_the_permutation_function(built_root, cohort_run):
  args, new = cohort_run
  sel = ce.load_condition_windows(built_root, "S01", "shared", None)
  summ = new["summary"]
  for m in ("coherence", "pdc"):
    res = pm.extract_connectivity_by_condition(
      sel["windows"], sel["y"], sel["fs"], cohort.METHODS[m], list(ce.CONDITION_FREQS), sel["channel_names"],
      n_permutations=19, trial_ids=sel["trial_ids"], quality=sel["quality"], n_jobs=1, random_state=args.random_state,
      alpha=args.alpha, seed_keys=("S01", m))
    res.pop("_meta")
    ed = np.load(args.reports_dir / "connectivity_edges_t" / f"S01_{m}.npz")
    for c, r in res.items():
      row = summ[(summ["method"] == m) & (summ["condition"] == c)].iloc[0]
      assert row["p_one_tailed"] == r["p_one_tailed"] and row["n_edges_sig_fdr"] == r["n_edges_sig_fdr"]
      assert row["obs_diff"] == r["obs_diff"] and row["total_edges"] == r["total_edges"]
      assert np.array_equal(ed[f"fdr_{c}"], r["fdr_significant"]) and np.array_equal(ed[f"p_{c}"], r["edge_p_one_tailed"])
      assert np.array_equal(ed[f"diff_{c}"], r["observed_diff"], equal_nan=True)
      # NBS columns are the NBS of the same null
      nb = cohort.nbs_for_result(r, r["directed"], [1.5, 2.0, 2.5, 3.0], 0.05)
      assert row["nbs_max_size"] == nb[2.0]["max_size"] and row["nbs_p"] == nb[2.0]["p"]
      assert row["nbs_size_z1.5"] == nb[1.5]["max_size"] and row["nbs_p_z3"] == nb[3.0]["p"]
      assert np.array_equal(ed[f"nbs_{c}"], nbs.edges_to_matrix(nb[2.0]["mask"], nb[2.0]["n_channels"]))


def test_cohort_columns_graph_size_and_sweep_tables(cohort_run):
  args, new = cohort_run
  summ, gs, sw = new["summary"], new["graph_size"], new["sweep"]
  assert list(summ.columns[:15]) == cohort.BASE_SUMMARY_COLUMNS
  tail = ["nbs_threshold", "nbs_max_size", "nbs_size_fraction", "nbs_p", "nbs_n_sig_edges", "nbs_significant",
          "nbs_size_z1.5", "nbs_size_z2", "nbs_size_z2.5", "nbs_size_z3", "nbs_p_z1.5", "nbs_p_z2", "nbs_p_z2.5", "nbs_p_z3",
          "n_stim_windows", "n_baseline_windows", "fs", "source"]
  assert list(summ.columns[15:]) == tail and (summ["nbs_threshold"] == 2.0).all() and (summ["fs"] == 256.0).all()
  assert (summ["n_channels"] == 7).all()                   # PO8 dropped: possible edges from the kept channels
  assert (gs["possible_edges_nbs"] == 21).all()
  pdc = gs[gs["method"] == "pdc"]
  assert (pdc["total_edges_fdr"] == 42).all()              # directed FDR denominator stays 42
  assert np.allclose(gs["nbs_size_pct"], 100 * gs["nbs_max_size"] / gs["possible_edges_nbs"])
  assert np.allclose(gs["fdr_pct_of_total"], 100 * gs["n_edges_sig_fdr"] / gs["total_edges_fdr"])
  assert len(sw) == len(gs) * 4 and set(sw["threshold"]) == {1.5, 2.0, 2.5, 3.0}
  for _, g in sw.groupby(["method", "condition"]):
    assert g.sort_values("threshold")["max_size"].is_monotonic_decreasing
  txt = "\n".join(cohort.graph_size_lines(gs) + cohort.sweep_lines(sw))
  assert "Graph sizes" in txt and "z>1.5" in txt


def test_stats_flag_changes_only_the_printed_criterion_and_files_are_written(built_root, tmp_path, capsys):
  common = ["--methods", "coherence", "--permutations", "9", "--n-jobs", "1", "--data-root", str(built_root),
            "--reports-dir", str(tmp_path / "rep"), "--nbs-thresholds", "2", "2.5", "--nbs-primary", "2.5"]
  assert cohort.main(common + ["--stats", "nbs", "--out-suffix", "a"]) == 0
  out_nbs = capsys.readouterr().out
  assert cohort.main(common + ["--stats", "fdr", "--out-suffix", "b"]) == 0
  out_fdr = capsys.readouterr().out
  assert "(A) NBS largest" in out_nbs and "(A) NBS largest" not in out_fdr and ">=1 FDR edge" in out_fdr and ">=1 FDR edge" not in out_nbs
  assert "(B) global p" in out_nbs and "(B) global p" in out_fdr and "Graph sizes" in out_nbs
  a = pd.read_csv(tmp_path / "rep" / "connectivity_cohort_summary_a.csv")
  b = pd.read_csv(tmp_path / "rep" / "connectivity_cohort_summary_b.csv")
  pd.testing.assert_frame_equal(a, b)                      # both criteria always saved, identical
  assert (a["nbs_threshold"] == 2.5).all() and "nbs_size_z2.5" in a and "nbs_size_z1.5" not in a
  assert (tmp_path / "rep" / "connectivity_graph_size_a.csv").is_file() and (tmp_path / "rep" / "connectivity_nbs_sweep_a.csv").is_file()


def test_cohort_compare_adds_nbs_flips(tmp_path):
  base = dict(subject="S01", method="coherence", condition=101, frequency_hz=24.0, p_one_tailed=0.3, n_edges_sig_fdr=0,
              permutation_unit="trial")
  for sfx, p in (("a", 0.04), ("b", 0.06)):
    pd.DataFrame([dict(base, nbs_p=p)]).to_csv(cohort.summary_path(tmp_path, sfx), index=False)
  fl = cohort.compare_runs(tmp_path, "a", "b")
  assert len(fl) == 1 and bool(fl["flip_NBS"].iloc[0]) and not fl["flip_A"].iloc[0] and not fl["flip_B"].iloc[0]


# ---------------------------------------------------------------- pairwise port

def _corr_fn(windows, fs, band):
  x = np.concatenate(list(windows), axis=1)
  return np.corrcoef(x)


def _group(rng, n, c, t, shared):
  w = rng.standard_normal((n, c, t))
  if shared:
    w[:, :4] += 2.0 * rng.standard_normal((n, 1, t))      # channels 0-3 coupled
  return w


def _pair(monkeypatch, shared_a, seed):
  monkeypatch.setitem(pair.METHODS, "synthcorr", _corr_fn)
  rng = np.random.default_rng(seed)
  na = nb = 40
  base = _group(rng, 60, 8, 64, False)
  wa, wb = _group(rng, na, 8, 64, shared_a), _group(rng, nb, 8, 64, False)
  ia, ib = np.arange(na), np.arange(nb)
  return pair._pair_job("S01", "synthcorr", 101, 102, wa, ia, wb, ib, base, 256.0, 200, 7 + seed, 0.05)[4]


def test_pairwise_nbs_finds_a_planted_difference_and_not_a_null(monkeypatch):
  r = _pair(monkeypatch, True, 0)
  assert r["n_edges"] == 28 and r["nbs_max_size"] >= 6 and r["nbs_p"] < 0.05 and r["n_edges_nbs"] >= 6 and r["fs"] == 256.0
  hits = sum(_pair(monkeypatch, False, s)["nbs_p"] < 0.05 for s in range(1, 21))
  assert hits <= 3                                         # nominal 5 % of 20 cells


def test_pairwise_columns_and_two_tailed_threshold(monkeypatch):
  r = _pair(monkeypatch, True, 2)
  rel = {("S01", "synthcorr"): {101: 0.5, 102: 0.5}}
  tab = pair.pairwise_tables([("S01", "synthcorr", 101, 102, r)], rel, {"S01": False}, 0.05)["synthcorr"]
  assert list(tab.columns[-4:]) == ["nbs_max_size", "nbs_p", "n_edges_nbs", "fs"] and list(tab.columns) == pair.PAIRWISE_COLUMNS
  assert pair.NBS_Z == 2.0


def test_pairwise_summary_only_reprints_from_csvs_without_recomputation(built_root, tmp_path, capsys, monkeypatch):
  common = ["--data-root", str(built_root), "--reports-dir", str(tmp_path / "rep"), "--methods", "coherence", "plv",
            "--out-suffix", "t", "--responders", "S01"]
  assert pair.main(common + ["--permutations", "9", "--splits", "2", "--n-jobs", "1"]) == 0
  full = capsys.readouterr().out
  monkeypatch.setattr(pair, "run", lambda *a, **k: pytest.fail("recomputed"))
  monkeypatch.setattr(pair, "load_subject_groups", lambda *a, **k: pytest.fail("recomputed"))
  assert pair.main(common + ["--summary-only"]) == 0
  again = capsys.readouterr().out
  body = again.split("\n", 1)[1]
  assert "Summary only" in again and "NBS p <" in body and "responders (S01)" in body
  assert body.strip() in full
  with pytest.raises(FileNotFoundError):
    pair.main(common[:-4] + ["--out-suffix", "missing", "--responders", "S01", "--summary-only"])


def test_pairwise_compare_adds_nbs_flip(tmp_path):
  rows = lambda p: pd.DataFrame([dict(subject="S01", method="coherence", freq_a=24.0, freq_b=20.0, p_mag=0.5, p_pat=0.5,
                                      n_edges_fdr=0, sig_bh_mag=False, sig_bh_pat=False, nbs_p=p)])
  out = tmp_path / "connectivity_comparison"
  out.mkdir()
  rows(0.04).to_csv(pair.csv_path(tmp_path, "coherence", "pairwise_tests", "a"), index=False)
  rows(0.07).to_csv(pair.csv_path(tmp_path, "coherence", "pairwise_tests", "b"), index=False)
  fl = pair.compare_runs(tmp_path, "a", "b", ["coherence"])
  assert len(fl) == 1 and bool(fl["flip_nbs"].iloc[0]) and not fl["flip_p_mag"].iloc[0]
