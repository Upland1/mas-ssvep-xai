"""P14 independent known-answer tests (synthetic data only).

Complements `test_p14_connectivity_comparison.py` where that file is thin or self-referential: QAP against exhaustive
relabelling and its skip rules, 8 x 8 embedding by name, hand node strength with PDC symmetrization (PF-25),
responders from the benchmark CSV only (PF-21), Spearman-Brown only for r > 0 (PF-22), pairwise permutation test
recomputed independently (shared null draws, trial-level exchange, observed sizes; PF-19, R7), reliability
ceiling, Fisher combination, planted SNR / alpha change with the f0 exclusion (PF-23), within-subject centring,
no misspelled duplicate (PF-27) and the section-6 schemas.
"""

import itertools
import math
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.signal import periodogram

from scripts.connectivity.comparison import compare_connectivity_frequencies as c1
from scripts.connectivity.comparison import test_connectivity_frequency_differences as c2
from scripts.connectivity.diagnostics import check_power_alpha_confound as c3
from src.features.connectivity import comparison as cmp
from src.features.connectivity import permutation as pm

ROOT = Path(__file__).resolve().parents[1]
FS = 250.0
MONT = list(cmp.MONTAGE)
BAND_A, BAND_B = (23.0, 25.0), (19.0, 21.0)


def _sym(rng, n):
  m = rng.standard_normal((n, n))
  m = 0.5 * (m + m.T)
  np.fill_diagonal(m, np.nan)
  return m


# ------------------------------------------------------------------ embedding (PF-26)

def test_embedding_unordered_kept_with_dropped_channel_and_po7_nan():
  kept = ["O2", "PO3", "POz", "O1", "PO4"]                  # not in montage order; PO7, PO8, Oz absent
  rng = np.random.default_rng(0)
  m = rng.standard_normal((5, 5))
  e = cmp.embed_to_montage(m, kept)
  assert e.shape == (8, 8)
  for name in ("PO7", "PO8", "Oz"):
    i = MONT.index(name)
    assert np.isnan(e[i]).all() and np.isnan(e[:, i]).all()
  for i, a in enumerate(kept):
    for j, b in enumerate(kept):
      assert e[MONT.index(a), MONT.index(b)] == m[i, j]
  assert np.isfinite(e).sum() == 25                            # nothing else is filled


def test_embedding_full_montage_identity_and_shuffled_full_montage():
  rng = np.random.default_rng(1)
  m = rng.standard_normal((8, 8))
  assert np.array_equal(cmp.embed_to_montage(m, MONT), m)
  order = [5, 2, 7, 0, 3, 1, 6, 4]
  e = cmp.embed_to_montage(m, [MONT[i] for i in order])
  assert np.array_equal(e[np.ix_(order, order)], m)


# ------------------------------------------------------------------ node strength, PDC symmetrization (PF-25)

M_PDC = np.array([[9.0, 1, 2, 3], [5, 9, 6, 7], [8, 2, 9, 4], [1, 3, 5, 9]])   # diagonal 9 must not count
KEPT4 = ["O2", "POz", "Oz", "O1"]
NS_SYM = {"O2": 10 / 3, "POz": 4.0, "Oz": 4.5, "O1": 11.5 / 3}    # hand: S_ij = (M_ij + M_ji) / 2
NS_RAW = {"O2": 2.0, "POz": 6.0, "Oz": 14 / 3, "O1": 3.0}        # row means of the directed matrix (the PF-25 bug)


def _write_edges(path, kept, diffs, decoy=True):
  d = {"channels_kept": np.array(kept)}
  for c, m in diffs.items():
    d[f"diff_{c}"] = m
    d[f"fdr_{c}"] = np.zeros(m.shape, dtype=bool)
    if decoy:                                              # section-6 files also hold raw stim/base/p
      d[f"stim_{c}"] = np.full(m.shape, 123.0)
      d[f"base_{c}"] = np.full(m.shape, -77.0)
      d[f"p_{c}"] = np.full(m.shape, 0.5)
  np.savez(path, **d)


def test_pdc_node_strength_hand_values_through_script_loader(tmp_path):
  _write_edges(tmp_path / "S01_pdc.npz", KEPT4, {101: M_PDC, 102: 2 * M_PDC})
  loaded = c1.load_deltas(tmp_path, "S01", "pdc")
  sim, node, glob = c1.subject_tables("S01", "pdc", loaded, 20, 42)
  nd = pd.DataFrame(node)
  for c, k in ((101, 1), (102, 2)):
    for ch in MONT:
      v = nd[(nd.condition == c) & (nd.channel == ch)]["node_strength"].iloc[0]
      if ch in NS_SYM:
        assert v == pytest.approx(k * NS_SYM[ch], abs=1e-12)
        assert abs(v - k * NS_RAW[ch]) > 1e-3                # the unsymmetrized value is different
      else:
        assert np.isnan(v)
  g = pd.DataFrame(glob).set_index("condition")
  assert g.loc[101, "mean_delta"] == pytest.approx(23.5 / 6, abs=1e-12)
  assert g.loc[102, "mean_delta"] == pytest.approx(2 * 23.5 / 6, abs=1e-12)
  assert len(sim) == 1


def test_symmetric_methods_not_symmetrized_twice_and_raw_keys_ignored(tmp_path):
  s = 0.5 * (M_PDC + M_PDC.T)
  _write_edges(tmp_path / "S01_coherence.npz", KEPT4, {101: s})
  loaded = c1.load_deltas(tmp_path, "S01", "coherence")
  m = loaded["deltas"][101]
  pos = [MONT.index(c) for c in KEPT4]
  sub = m[np.ix_(pos, pos)]
  off = ~np.eye(4, dtype=bool)
  assert np.allclose(sub[off], s[off])                       # diff_ read, not stim_ (123) / base_ (-77) / p_
  assert np.isnan(np.diag(m)).all()
  assert c1.DIRECTED == {"pdc"}


def test_script_reads_only_delta_fdr_and_channel_keys(tmp_path, monkeypatch):
  _write_edges(tmp_path / "S01_plv.npz", KEPT4, {101: 0.5 * (M_PDC + M_PDC.T)})
  touched = set()
  orig = np.load

  class Spy:
    def __init__(self, z):
      self.z = z
      self.files = z.files

    def __getitem__(self, k):
      touched.add(k)
      return self.z[k]

  monkeypatch.setattr(c1.np, "load", lambda *a, **k: Spy(orig(*a, **k)))
  c1.load_deltas(tmp_path, "S01", "plv")
  assert touched <= {"channels_kept", "diff_101", "fdr_101"} and "diff_101" in touched


# ------------------------------------------------------------------ Fisher-z

def test_fisher_mean_known_values_and_group_summary():
  r = [0.2, 0.9, -0.5]
  hand = math.tanh((math.atanh(0.2) + math.atanh(0.9) + math.atanh(-0.5)) / 3)
  assert cmp.fisher_mean(r) == pytest.approx(hand, abs=1e-12)
  assert abs(cmp.fisher_mean(r) - np.mean(r)) > 1e-3         # not the arithmetic mean
  assert math.isfinite(cmp.fisher_mean([1.0, 0.5])) and cmp.fisher_mean([1.0, 1.0]) == pytest.approx(1.0, abs=1e-6)
  assert math.isnan(cmp.fisher_mean([np.nan]))
  sim = pd.DataFrame({"subject": ["S01", "S02", "S03"], "method": "plv", "freq_a": 24.0, "freq_b": 20.0,
                      "r": r, "p_qap": [0.01, 0.2, 0.04]})
  g = c1.group_similarity(sim, {"all": ["S01", "S02", "S03"], "responders": ["S01", "S03"]}).set_index("group")
  assert g.loc["all", "r_fisher_mean"] == pytest.approx(hand, abs=1e-12)
  assert g.loc["all", "n_p_qap_lt_05"] == 2 and g.loc["responders", "n_subjects"] == 2
  assert g.loc["responders", "r_fisher_mean"] == pytest.approx(math.tanh((math.atanh(0.2) + math.atanh(-0.5)) / 2),
                                                               abs=1e-12)


# ------------------------------------------------------------------ QAP

def test_qap_relabelled_copy_gives_r_one_and_minimum_p():
  """A matrix and a copy of it under the same node relabelling are the same graph: r = 1, p at its minimum."""
  rng = np.random.default_rng(4)
  a = _sym(rng, 7)
  perm = rng.permutation(7)
  b = a[np.ix_(perm, perm)]
  for n in (19, 499):
    for x, y in ((a, a), (b, b), (a, a.copy())):
      q = cmp.qap_pvalue(x, y, n, 3)
      assert q["r"] == pytest.approx(1.0, abs=1e-12)
      assert q["p"] == pytest.approx(1 / (n + 1), abs=1e-12)    # +1 pseudo-count: never 0
  # the relabelled copy against the unrelabelled original is NOT the same alignment: r is far from 1
  assert cmp.qap_pvalue(a, b, 19, 3)["r"] < 0.9


def test_qap_pvalue_is_a_multiple_of_one_over_n_plus_one_and_never_zero():
  rng = np.random.default_rng(5)
  for i in range(10):
    a, b = _sym(rng, 6), _sym(rng, 6)
    n = 49
    p = cmp.qap_pvalue(a, b, n, i)["p"]
    assert p >= 1 / (n + 1) and abs(p * (n + 1) - round(p * (n + 1))) < 1e-9


def test_qap_independent_matrices_give_uniform_p():
  rng = np.random.default_rng(6)
  ps = np.array([cmp.qap_pvalue(_sym(rng, 7), _sym(rng, 7), 199, i)["p"] for i in range(300)])
  for q in (0.1, 0.25, 0.5, 0.75):
    assert abs(np.mean(ps <= q) - q) < 0.08, (q, np.mean(ps <= q))


def test_qap_exhaustive_with_missing_channels_and_asymmetric_structure():
  """5 present channels inside the 8 x 8 montage (3 NaN rows/cols); compare with all 5! relabellings."""
  rng = np.random.default_rng(7)
  kept = ["PO3", "PO4", "O1", "Oz", "O2"]
  x = rng.standard_normal(5)
  a5 = np.outer(x, x) + 0.6 * _sym(rng, 5)
  b5 = np.outer(x, x[::-1]) + 0.6 * _sym(rng, 5)
  a5, b5 = 0.5 * (a5 + a5.T), 0.5 * (b5 + b5.T)
  a, b = cmp.embed_to_montage(a5, kept), cmp.embed_to_montage(b5, kept)
  np.fill_diagonal(a, np.nan)
  np.fill_diagonal(b, np.nan)
  iu = np.triu_indices(5, 1)
  obs = np.corrcoef(a5[iu], b5[iu])[0, 1]
  exact = np.mean([np.corrcoef(a5[iu], b5[np.ix_(p, p)][iu])[0, 1] >= obs - 1e-12
                   for p in itertools.permutations(range(5))])
  q = cmp.qap_pvalue(a, b, 8000, 11)
  assert q["n_shared"] == 5 and q["n_pairs"] == 10
  assert q["r"] == pytest.approx(obs, abs=1e-12)
  assert q["p"] == pytest.approx(exact, abs=0.025)


def test_qap_exhaustive_n6_distinguishes_rows_only_permutation():
  rng = np.random.default_rng(12)
  x = rng.standard_normal(6)
  a = np.outer(x, x) + 0.3 * _sym(rng, 6)
  a = 0.5 * (a + a.T)
  b = a + 0.3 * _sym(rng, 6)
  np.fill_diagonal(a, np.nan)
  np.fill_diagonal(b, np.nan)
  iu = np.triu_indices(6, 1)
  obs = np.corrcoef(a[iu], b[iu])[0, 1]
  exact = np.mean([np.corrcoef(a[iu], b[np.ix_(p, p)][iu])[0, 1] >= obs - 1e-12
                   for p in itertools.permutations(range(6))])
  q = cmp.qap_pvalue(a, b, 8000, 2)
  assert q["p"] == pytest.approx(exact, abs=0.02)
  assert exact < 0.2                                          # structured case: informative comparison


def test_qap_applicability_rules():
  rng = np.random.default_rng(8)
  kept = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  # 4 shared channels, 6 finite pairs: applicable
  a4 = cmp.embed_to_montage(_sym(rng, 4), kept[:4])
  b4 = cmp.embed_to_montage(_sym(rng, 4), kept[:4])
  q = cmp.qap_pvalue(a4, b4, 50, 0)
  assert q["n_pairs"] == 6 and q["n_shared"] == 4 and np.isfinite(q["p"]) and np.isfinite(q["r"])
  # 4 shared channels, only 5 finite pairs: skipped
  a4n = a4.copy()
  i, j = MONT.index("PO3"), MONT.index("POz")
  a4n[i, j] = a4n[j, i] = np.nan
  q = cmp.qap_pvalue(a4n, b4, 50, 0)
  assert q["n_pairs"] == 5 and np.isnan(q["r"]) and np.isnan(q["p"])
  # 3 shared channels (3 pairs): skipped
  a3 = cmp.embed_to_montage(_sym(rng, 3), kept[:3])
  q = cmp.qap_pvalue(a3, a3, 50, 0)
  assert q["n_shared"] == 3 and np.isnan(q["p"])
  # 5 channels in a, 3 of them shared with b: shared rule uses the intersection
  a5 = cmp.embed_to_montage(_sym(rng, 5), kept[:5])
  b3 = cmp.embed_to_montage(_sym(rng, 3), kept[2:5])
  q = cmp.qap_pvalue(a5, b3, 50, 0)
  assert q["n_shared"] == 3 and np.isnan(q["p"])


def test_qap_script_marks_skipped_pairs_as_nan(tmp_path):
  rng = np.random.default_rng(9)
  full = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  for s, kept in (("S01", full), ("S02", full[:3])):
    n = len(kept)
    diffs = {c: 0.5 * ((x := rng.standard_normal((n, n))) + x.T) for c in (101, 102)}
    _write_edges(tmp_path / f"{s}_coherence.npz", kept, diffs)
  pd.DataFrame({"Subject": ["S01", "S02"], "2.0s Smoothed (%)": [90.0, 50.0]}).to_csv(tmp_path / "b.csv", index=False)
  args = c1.build_parser().parse_args(["--edges-dir", str(tmp_path), "--reports-dir", str(tmp_path / "rep"),
                                       "--methods", "coherence", "--qap-permutations", "30", "--no-figures",
                                       "--benchmark", str(tmp_path / "b.csv")])
  out = c1.run(args)["coherence"]["similarity"].set_index("subject")
  assert np.isfinite(out.loc["S01", "p_qap"]) and np.isnan(out.loc["S02", "p_qap"]) and np.isnan(out.loc["S02", "r"])


# ------------------------------------------------------------------ responders (PF-21)

def test_responders_threshold_edge_cases(tmp_path):
  p = tmp_path / "b.csv"
  pd.DataFrame({"Subject": ["S01", "S02", "S03", "S04", "S05", "Mean"],
                "2.0s Smoothed (%)": [80.0, 79.99, 100.0, np.nan, 50.0, 80.0]}).to_csv(p, index=False)
  resp, non = cmp.responders_from_benchmark(p)
  assert resp == ["S01", "S03"] and non == ["S02", "S04", "S05"]       # >= 80 inclusive, NaN is non-responder
  assert cmp.responders_from_benchmark(p, threshold=90.0)[0] == ["S03"]


def _edge_set(root, scale):
  rng = np.random.default_rng(0)
  kept = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  for s, k in (("S01", 0.01), ("S02", 1.0), ("S03", 0.02)):
    diffs = {}
    for c in (101, 102, 103, 104, 105):
      x = rng.standard_normal((7, 7))
      diffs[c] = (0.5 * (x + x.T)) * 0.01 + (k * scale if scale else 0.0) + 0.01 * (c - 100)
    _write_edges(Path(root) / f"{s}_coherence.npz", kept, diffs)


def test_responders_independent_of_connectivity(tmp_path):
  """Benchmark: S01 and S03 respond. Connectivity: S02 has by far the largest deltas, then it flips."""
  pd.DataFrame({"Subject": ["S01", "S02", "S03"], "2.0s Smoothed (%)": [90.0, 50.0, 80.0]}).to_csv(
    tmp_path / "b.csv", index=False)
  got = []
  for tag, scale in (("a", 1.0), ("b", -5.0)):
    e = tmp_path / f"edges_{tag}"
    e.mkdir()
    _edge_set(e, scale)
    args = c1.build_parser().parse_args(["--edges-dir", str(e), "--reports-dir", str(tmp_path / f"rep_{tag}"),
                                         "--methods", "coherence", "--qap-permutations", "10", "--no-figures",
                                         "--benchmark", str(tmp_path / "b.csv")])
    c1.run(args)
    d = tmp_path / f"rep_{tag}" / "connectivity_comparison"
    gd = pd.read_csv(d / "coherence_global_delta.csv")
    grp = pd.read_csv(d / "coherence_global_delta_groups.csv")
    r = grp[grp.group == "responders"].set_index("condition")
    n = grp[grp.group == "non_responders"].set_index("condition")
    assert (r["n_subjects"] == 2).all() and (n["n_subjects"] == 1).all()
    hand_r = gd[gd.subject.isin(["S01", "S03"])].groupby("condition")["mean_delta"].mean()
    hand_n = gd[gd.subject == "S02"].set_index("condition")["mean_delta"]
    assert np.allclose(r["mean_delta_mean"], hand_r.loc[r.index])
    assert np.allclose(n["mean_delta_mean"], hand_n.loc[n.index])
    got.append((r["n_subjects"].iloc[0], n["n_subjects"].iloc[0]))
  assert got[0] == got[1]


def test_responders_override_flag_wins(tmp_path):
  pd.DataFrame({"Subject": ["S01", "S02"], "2.0s Smoothed (%)": [90.0, 50.0]}).to_csv(tmp_path / "b.csv", index=False)
  rng = np.random.default_rng(0)
  for s in ("S01", "S02"):
    _write_edges(tmp_path / f"{s}_plv.npz", ["PO3", "POz", "PO4", "O1", "O2"],
                 {101: 0.5 * ((x := rng.standard_normal((5, 5))) + x.T)})
  args = c1.build_parser().parse_args(["--edges-dir", str(tmp_path), "--reports-dir", str(tmp_path / "rep"),
                                       "--methods", "plv", "--qap-permutations", "10", "--no-figures",
                                       "--benchmark", str(tmp_path / "b.csv"), "--responders", "S02"])
  c1.run(args)
  grp = pd.read_csv(tmp_path / "rep" / "connectivity_comparison" / "plv_global_delta_groups.csv")
  assert grp[grp.group == "responders"]["n_subjects"].iloc[0] == 1
  assert grp[grp.group == "non_responders"]["n_subjects"].iloc[0] == 1


# ------------------------------------------------------------------ split-half (PF-22)

def _tagged(n_trials, per, c=4, t=8):
  ids = np.repeat(np.arange(n_trials), per)
  w = np.ones((len(ids), c, t)) * ids[:, None, None].astype(float)
  return w, ids


def test_split_half_negative_r_is_not_spearman_browned():
  """Stub estimator: delta = G * (mean(windows) - overall mean) -> the two halves are exactly anti-correlated."""
  rng = np.random.default_rng(0)
  g = rng.standard_normal((4, 4))
  g = 0.5 * (g + g.T)
  stim, sids = _tagged(10, 3)
  c = stim.mean()
  base = np.full((12, 4, 8), c)
  bids = np.repeat(np.arange(6), 2)

  def fn(x, fs, band):
    return g * (x.mean() - c)
  r = cmp.split_half_delta_reliability(stim, sids, base, bids, BAND_A, FS, fn, n_splits=5, seed=1)
  assert r["r_fisher"] == pytest.approx(-1.0, abs=1e-6)
  assert not r["corrected"]
  assert r["reliability"] == pytest.approx(r["r_fisher"], abs=1e-12) and r["reliability"] >= -1.0 - 1e-6


def test_split_half_positive_r_corrected_by_formula():
  rng = np.random.default_rng(1)
  g = rng.standard_normal((4, 4))
  g = 0.5 * (g + g.T)
  stim, sids = _tagged(10, 3)
  base = np.zeros((12, 4, 8))
  bids = np.repeat(np.arange(6), 2)

  def fn(x, fs, band):                                       # shared pattern plus half-specific noise
    noise = np.random.default_rng(int(abs(x.sum()) * 7) % 10_000).standard_normal((4, 4))
    return g * 3.0 + 0.8 * 0.5 * (noise + noise.T)
  r = cmp.split_half_delta_reliability(stim, sids, base, bids, BAND_A, FS, fn, n_splits=8, seed=2)
  assert 0 < r["r_fisher"] < 1 and r["corrected"]
  assert r["reliability"] == pytest.approx(2 * r["r_fisher"] / (1 + r["r_fisher"]), abs=1e-12)


def test_split_half_halves_are_trial_disjoint(monkeypatch):
  stim, sids = _tagged(10, 3)
  base, bids = _tagged(6, 2)
  seen = []

  def fn(x, fs, band):
    seen.append(frozenset(np.unique(x[:, 0, 0])))
    return np.eye(4) * x.mean()
  cmp.split_half_delta_reliability(stim, sids, base, bids, BAND_A, FS, fn, n_splits=4, seed=3)
  # per split the calls are: d1 stim, d1 base, d2 stim, d2 base
  for s1, s2 in zip(seen[0::4], seen[2::4]):
    assert not (s1 & s2) and len(s1) == 5 and len(s2) == 5
  for s1, s2 in zip(seen[1::4], seen[3::4]):
    assert not (s1 & s2) and len(s1) == 3 and len(s2) == 3
  assert len(seen) == 16


# ------------------------------------------------------------------ ceiling, disattenuation, tables

def test_ceiling_and_disattenuation_ten_percent_rule():
  assert cmp.reliability_ceiling(0.01, 1.0) == pytest.approx(0.1)
  assert np.isnan(cmp.disattenuate(0.5, cmp.reliability_ceiling(0.01, 1.0)))        # exactly 0.1 is not > 0.1
  assert cmp.disattenuate(0.36, cmp.reliability_ceiling(0.81, 0.64)) == pytest.approx(0.5, abs=1e-12)
  assert np.isnan(cmp.reliability_ceiling(-0.5, -0.5))                              # product positive, still invalid
  assert np.isnan(cmp.reliability_ceiling(np.nan, 0.5))
  assert cmp.disattenuate(0.9, 0.5) == pytest.approx(1.8)                           # not clipped to 1


F24, F20, F15, F1091, F857 = (c3.CONDITION_FREQS[c] for c in (101, 102, 103, 104, 105))


def _fake_job(subject, a, b, p_mag, p_pat, r_obs):
  return (subject, "plv", a, b, dict(t_mag=0.1, p_mag=p_mag, d_pat=1 - r_obs, p_pat=p_pat, r_obs=r_obs,
                                    n_edges_fdr=0, n_edges=21))


def test_pairwise_tables_ceiling_disattenuation_and_bh():
  rel = {("S01", "plv"): {101: 0.81, 102: 0.64, 103: -0.3, 104: 0.01, 105: 1.0}}
  jobs = [_fake_job("S01", 101, 102, 0.001, 0.8, 0.36), _fake_job("S01", 101, 103, 0.004, 0.9, 0.5),
          _fake_job("S01", 104, 105, 0.02, np.nan, 0.5)] + [
    _fake_job("S01", 102, 103, 0.5, 0.5, 0.1), _fake_job("S01", 102, 104, 0.6, 0.5, 0.1),
    _fake_job("S01", 102, 105, 0.7, 0.5, 0.1), _fake_job("S01", 103, 104, 0.8, 0.5, 0.1),
    _fake_job("S01", 103, 105, 0.9, 0.5, 0.1), _fake_job("S01", 101, 104, 0.95, 0.5, 0.1),
    _fake_job("S01", 101, 105, 0.99, 0.5, 0.1)]
  df = c2.pairwise_tables(jobs, rel, {"S01": True}, 0.05)["plv"].set_index(["freq_a", "freq_b"])
  r = df.loc[(F24, F20)]
  assert r["reliability_ceiling"] == pytest.approx(0.72) and r["r_disattenuated"] == pytest.approx(0.5)
  assert np.isnan(df.loc[(F24, F15)]["reliability_ceiling"]) and np.isnan(df.loc[(F24, F15)]["r_disattenuated"])
  assert np.isnan(df.loc[(F1091, F857)]["r_disattenuated"])                         # ceiling 0.1: not > 0.1
  assert df["trial_ids_approximate"].all()
  # BH at 0.05 over 10 pairs: 0.001 <= 0.005, 0.004 <= 0.010, 0.02 > 0.015 -> two significant
  assert df["sig_bh_mag"].sum() == 2 and df.loc[(F24, F20), "sig_bh_mag"] and not df.loc[(F1091, F857), "sig_bh_mag"]
  assert df["sig_bh_pat"].sum() == 0


def test_fisher_combined_hand_chi_square():
  # k = 1: chi2 with 2 df has sf exp(-x/2) = p
  x, p, k = cmp.fisher_combined_p([0.3])
  assert k == 1 and p == pytest.approx(0.3, abs=1e-12) and x == pytest.approx(-2 * math.log(0.3), abs=1e-12)
  # k = 2: 4 df, sf = exp(-x/2) (1 + x/2) = p1 p2 (1 - ln(p1 p2))
  p1, p2 = 0.01, 0.2
  x, p, k = cmp.fisher_combined_p([p1, p2])
  hand = p1 * p2 * (1 - math.log(p1 * p2))
  assert k == 2 and x == pytest.approx(-2 * math.log(p1 * p2), abs=1e-12) and p == pytest.approx(hand, abs=1e-12)
  # k = 4: 8 df, closed form with 4 terms
  ps = [0.2, 0.3, 0.6, 0.9]
  x, p, k = cmp.fisher_combined_p(ps)
  half = -sum(math.log(v) for v in ps)
  hand = math.exp(-half) * sum(half ** j / math.factorial(j) for j in range(4))
  assert p == pytest.approx(hand, abs=1e-12)


def test_combined_table_uses_group_members_only():
  rows = []
  for s, pm_, pp in (("S01", 0.01, 0.4), ("S02", 0.2, 0.5), ("S03", 0.3, np.nan)):
    rows.append(dict(subject=s, method="plv", freq_a=24.0, freq_b=20.0, p_mag=pm_, p_pat=pp))
  tab = c2.combined_table(pd.DataFrame(rows), {"responders": ["S01", "S03"], "non_responders": ["S02"]})
  tab = tab.set_index("group")
  hand = 0.01 * 0.3 * (1 - math.log(0.01 * 0.3))
  assert tab.loc["responders", "p_fisher_mag"] == pytest.approx(hand, abs=1e-12) and tab.loc["responders", "k_subjects"] == 2
  assert tab.loc["non_responders", "p_fisher_mag"] == pytest.approx(0.2, abs=1e-12)
  assert tab.loc["responders", "p_fisher_pat"] == pytest.approx(0.4, abs=1e-12)     # NaN dropped


# ------------------------------------------------------------------ pairwise permutation test (PF-19, R7)

def corr_fn(x, fs, band):
  """Zero-lag correlation of the channels over the concatenated windows; the band only adds an offset that
  cancels exactly when each group and its baseline are scored in the SAME band."""
  c = x.shape[1]
  m = np.corrcoef(np.transpose(x, (1, 0, 2)).reshape(c, -1))
  np.fill_diagonal(m, 0.0)
  return m + 0.05 * band[0]


def _coupled(rng, n_win, weights, t=64):
  c = len(weights)
  return rng.standard_normal((n_win, c, t)) + np.asarray(weights)[None, :, None] * rng.standard_normal((n_win, 1, t))


def _ids(n_win, per):
  return np.repeat(np.arange(n_win // per), per)


def _pearson(x, y):
  return float(np.corrcoef(x, y)[0, 1])


def _reference_pairwise(win_a, ids_a, win_b, ids_b, base, band_a, band_b, fn, n, seed):
  """Independent recomputation: same splitter and seeds, plain loops, one set of draws for both statistics."""
  pool, ids = np.concatenate([win_a, win_b]), np.concatenate([ids_a, ids_b])
  na = len(win_a)
  iu = np.triu_indices(win_a.shape[1], 1)
  da = fn(win_a, FS, band_a) - fn(base, FS, band_a)
  db = fn(win_b, FS, band_b) - fn(base, FS, band_b)
  t_obs = (da - db)[iu].mean()
  d_obs = 1 - _pearson(da[iu], db[iu])
  nt, nd = [], []
  for s in np.random.SeedSequence(seed).generate_state(n):
    ia, ib = pm._trial_permutation_split(ids, na, np.random.default_rng(int(s)))
    pa = fn(pool[ia], FS, band_a) - fn(base, FS, band_a)
    pb = fn(pool[ib], FS, band_b) - fn(base, FS, band_b)
    nt.append((pa - pb)[iu].mean())
    nd.append(1 - _pearson(pa[iu], pb[iu]))
  nt, nd = np.array(nt), np.array(nd)
  return (1 + np.sum(np.abs(nt) >= abs(t_obs))) / (n + 1), (1 + np.sum(nd >= d_obs)) / (n + 1), t_obs, d_obs


def test_pairwise_matches_independent_reference_exactly():
  rng = np.random.default_rng(10)
  wa, wb = [1.5, 1.0, 0.5, 0.2, 0.2], [0.2, 0.2, 0.5, 1.0, 1.5]
  a, b = _coupled(rng, 40, wa), _coupled(rng, 30, wb)
  base = _coupled(rng, 36, [0.3] * 5)
  ia, ib = _ids(40, 5), _ids(30, 5) + 100
  r = cmp.pairwise_permutation_test(a, ia, b, ib, base, BAND_A, BAND_B, FS, corr_fn, 120, 21)
  pmag, ppat, t_obs, d_obs = _reference_pairwise(a, ia, b, ib, base, BAND_A, BAND_B, corr_fn, 120, 21)
  assert r["p_mag"] == pytest.approx(pmag, abs=1e-12) and r["p_pat"] == pytest.approx(ppat, abs=1e-12)
  assert r["t_mag"] == pytest.approx(t_obs, abs=1e-12) and r["d_pat"] == pytest.approx(d_obs, abs=1e-12)
  assert (r["n_a"], r["n_b"], r["n_base"], r["n_edges"]) == (40, 30, 36, 10)


def test_pairwise_baseline_scored_in_own_band():
  """Identical processes, different bands: the band offset must cancel, so the magnitude is ~0 and p not tiny."""
  rng = np.random.default_rng(11)
  w = [1.0, 0.8, 0.6, 0.4, 0.2]
  a, b = _coupled(rng, 40, w), _coupled(rng, 40, w)
  base = _coupled(rng, 40, [0.0] * 5)
  r = cmp.pairwise_permutation_test(a, _ids(40, 5), b, _ids(40, 5) + 50, base, (30.0, 32.0), (10.0, 12.0), FS,
                                    corr_fn, 99, 3)
  assert abs(r["t_mag"]) < 0.1 and r["p_mag"] > 0.05


def test_pairwise_splitter_called_once_per_draw_with_observed_sizes_and_shared_nested(monkeypatch):
  rng = np.random.default_rng(12)
  a, b, base = _coupled(rng, 25, [1.0] * 4), _coupled(rng, 45, [1.0] * 4), _coupled(rng, 20, [0.0] * 4)
  ia, ib = _ids(25, 5), _ids(45, 5) + 40
  calls = []
  orig = pm._trial_permutation_split

  def spy(ids, n_first, rng_):
    first, second = orig(ids, n_first, rng_)
    calls.append((n_first, len(first), len(second), tuple(first)))
    return first, second
  monkeypatch.setattr(cmp, "_trial_permutation_split", spy)
  cmp.pairwise_permutation_test(a, ia, b, ib, base, BAND_A, BAND_B, FS, corr_fn, 10, 5)
  short = list(calls)
  calls.clear()
  cmp.pairwise_permutation_test(a, ia, b, ib, base, BAND_A, BAND_B, FS, corr_fn, 20, 5)
  assert len(short) == 10 and len(calls) == 20              # one split per draw, shared by both statistics
  assert all(c[:3] == (25, 25, 45) for c in calls)
  assert short == calls[:10]                                # nested nulls: 10 permutations are the head of 20


def _het(rng, n_trials, per, weights, t=64):
  """Trials differ a lot in coupling strength; windows of a trial share it."""
  ids = np.repeat(np.arange(n_trials), per)
  s = np.exp(1.2 * rng.standard_normal(n_trials))[ids]
  w = rng.standard_normal((len(ids), len(weights), t)) + (s[:, None, None] * np.asarray(weights)[None, :, None]
                                                           * rng.standard_normal((len(ids), 1, t)))
  return w, ids


def test_pairwise_trial_level_null_is_not_anticonservative_with_heterogeneous_trials():
  w = [1.0, 0.9, 0.8, 0.7]
  ps = []
  for rep in range(70):
    rng = np.random.default_rng(1000 + rep)
    a, ia = _het(rng, 6, 5, w)
    b, ib = _het(rng, 6, 5, w)
    base = _coupled(rng, 20, [0.0] * 4)
    ps.append(cmp.pairwise_permutation_test(a, ia, b, ib + 100, base, BAND_A, BAND_A, FS, corr_fn, 99, rep)["p_mag"])
  ps = np.array(ps)
  assert np.mean(ps < 0.05) < 0.18 and 0.35 < ps.mean() < 0.65


def test_pairwise_identical_processes_uniform_p_both_statistics():
  w = [1.2, 1.0, 0.8, 0.6, 0.4]
  pmag, ppat = [], []
  for rep in range(80):
    rng = np.random.default_rng(2000 + rep)
    a, b, base = _coupled(rng, 30, w), _coupled(rng, 30, w), _coupled(rng, 30, [0.0] * 5)
    r = cmp.pairwise_permutation_test(a, _ids(30, 3), b, _ids(30, 3) + 50, base, BAND_A, BAND_A, FS, corr_fn, 99, rep)
    pmag.append(r["p_mag"])
    ppat.append(r["p_pat"])
  for ps in (np.array(pmag), np.array(ppat)):
    for q in (0.25, 0.5, 0.75):
      assert abs(np.mean(ps <= q) - q) < 0.14, (q, np.mean(ps <= q))
    assert np.mean(ps < 0.05) < 0.15


def test_pairwise_planted_magnitude_difference_small_pmag_not_ppat():
  rng = np.random.default_rng(13)
  w = np.array([1.5, 1.2, 1.0, 0.8, 0.6, 0.4])
  a, b = _coupled(rng, 60, w), _coupled(rng, 60, 0.3 * w)       # same ordering of strengths, weaker coupling
  base = _coupled(rng, 60, [0.0] * 6)
  r = cmp.pairwise_permutation_test(a, _ids(60, 5), b, _ids(60, 5) + 50, base, BAND_A, BAND_A, FS, corr_fn, 199, 4)
  assert r["p_mag"] <= 0.01 and r["t_mag"] > 0.05


def test_pairwise_planted_pattern_difference_equal_magnitude_small_ppat_only():
  rng = np.random.default_rng(14)
  wa, wb = [2.0, 2.0, 0.1, 0.1, 0.1, 0.1], [0.1, 0.1, 0.1, 0.1, 2.0, 2.0]
  a, b = _coupled(rng, 60, wa), _coupled(rng, 60, wb)
  base = _coupled(rng, 60, [0.0] * 6)
  r = cmp.pairwise_permutation_test(a, _ids(60, 5), b, _ids(60, 5) + 50, base, BAND_A, BAND_A, FS, corr_fn, 199, 5)
  assert r["p_pat"] <= 0.01 and r["r_obs"] < 0.2
  assert abs(r["t_mag"]) < 0.05 and r["p_mag"] > 0.05


# ------------------------------------------------------------------ confound script (PF-23)

def _tone_windows(freq_amp, n=12, t=256, noise=1e-3, seed=0, channels=3):
  rng = np.random.default_rng(seed)
  tt = np.arange(t) / FS
  x = noise * rng.standard_normal((n, channels, t))
  for f, a in freq_amp:
    x += a * np.sin(2 * np.pi * f * tt)[None, None, :]
  return x


BIN = FS / 256                                              # 0.9765625 Hz: tones below are bin-centred
F_T1091, F_ALPHA_IN, F_ALPHA_HI = 11 * BIN, 9 * BIN, 13 * BIN   # 10.742, 8.789, 12.695 Hz


def test_target_gain_and_alpha_drop_planted_for_10_91_hz():
  base = _tone_windows([(F_T1091, 1.0), (F_ALPHA_IN, 1.0)])
  stim = _tone_windows([(F_T1091, 2.0), (F_ALPHA_IN, 10 ** (-3 / 20))], seed=1)     # +6.02 dB target, -3 dB alpha
  m = c3.power_metrics(stim, base, [0, 1, 2], 10.91, FS)
  assert m["target_snr_db"] == pytest.approx(6.02, abs=0.2)
  assert m["alpha_change_db"] == pytest.approx(-3.0, abs=0.2)


def test_target_tone_inside_alpha_does_not_change_alpha_measure_for_both_in_alpha_targets():
  # 10.91 Hz: only the target tone gains 6 dB, alpha reference unchanged
  base = _tone_windows([(F_T1091, 1.0), (F_ALPHA_IN, 1.0)])
  stim = _tone_windows([(F_T1091, 2.0), (F_ALPHA_IN, 1.0)], seed=1)
  m = c3.power_metrics(stim, base, [0, 1, 2], 10.91, FS)
  assert m["target_snr_db"] == pytest.approx(6.02, abs=0.2) and abs(m["alpha_change_db"]) < 0.2
  # 8.57 Hz: target tone at 8.789, alpha reference at 11.719 Hz
  f_ref = 12 * BIN
  base = _tone_windows([(F_ALPHA_IN, 1.0), (f_ref, 1.0)])
  stim = _tone_windows([(F_ALPHA_IN, 2.0), (f_ref, 10 ** (-3 / 20))], seed=1)
  m = c3.power_metrics(stim, base, [0, 1, 2], 8.57, FS)
  assert m["target_snr_db"] == pytest.approx(6.02, abs=0.2) and m["alpha_change_db"] == pytest.approx(-3.0, abs=0.2)


def test_alpha_mask_excludes_f0_band_and_is_shared_by_stimulus_and_baseline():
  f, _ = periodogram(np.zeros(256), fs=FS, window="hann")
  for f0 in (F1091, F857):
    am = c3.alpha_mask(f, f0)
    assert am.any() and not am[np.abs(f - f0) <= 1.5].any()
    assert f[am].min() >= 8 - 1e-6 and f[am].max() <= 13 + 1e-6
  assert c3.alpha_mask(f, 24.0).sum() == ((f >= 8) & (f <= 13)).sum()


def test_only_listed_channels_enter_the_power_metrics():
  base = _tone_windows([(F_T1091, 1.0)], channels=4)
  stim = _tone_windows([(F_T1091, 1.0)], channels=4, seed=1)
  stim[:, 0, :] += 50 * np.sin(2 * np.pi * F_T1091 * np.arange(256) / FS)      # huge tone on channel 0 only
  assert c3.power_metrics(stim, base, [1, 2, 3], 10.91, FS)["target_snr_db"] == pytest.approx(0.0, abs=0.2)
  assert c3.power_metrics(stim, base, [0], 10.91, FS)["target_snr_db"] > 30


def test_subject_rows_use_o1_oz_o2_by_name_with_a_dropped_channel(monkeypatch):
  kept = ["PO3", "O1", "POz", "O2"]                          # Oz dropped by the gate; occipital ones at 1 and 3
  n_t, n_b = 10, 10
  base = _tone_windows([(F_T1091, 1.0)], n=n_b, channels=4)
  stim = {c: _tone_windows([(F_T1091, 1.0)], n=n_t, channels=4, seed=c) for c in (101, 102, 103, 104, 105)}
  stim[104][:, [1, 3], :] += 1.0 * np.sin(2 * np.pi * F_T1091 * np.arange(256) / FS)   # +6 dB on O1, O2 only
  stim[104][:, [0, 2], :] -= 0.9 * np.sin(2 * np.pi * F_T1091 * np.arange(256) / FS)   # PO3, POz would give < 0
  w = np.concatenate([stim[c] for c in sorted(stim)] + [base])
  y = np.concatenate([np.full(n_t, c) for c in sorted(stim)] + [np.full(n_b, 201)])
  monkeypatch.setattr(c3, "load_gated_conditions", lambda root, s: dict(windows=w, y=y, channels_kept=kept))
  rows = pd.DataFrame(c3.subject_rows(Path("."), "S01", FS)).set_index("condition")
  assert rows.loc[104, "channels_used"] == "O1;O2"
  assert rows.loc[104, "target_snr_db"] == pytest.approx(6.0, abs=0.5)
  assert rows.loc[102, "target_snr_db"] == pytest.approx(0.0, abs=0.5)
  assert rows.loc[104, "n_stim_windows"] == n_t and rows.loc[104, "n_base_windows"] == n_b


# ------------------------------------------------------------------ OLS, Spearman, centring

def test_ols_r2_hand_values():
  x = np.array([1.0, 2.0, 3.0, 5.0])
  y = np.array([1.0, 3.0, 2.0, 5.0])
  r2, beta = c3.ols_r2(y, x[:, None])
  assert r2 == pytest.approx(np.corrcoef(x, y)[0, 1] ** 2, abs=1e-12)
  slope = np.cov(x, y, bias=True)[0, 1] / x.var()
  assert beta[1] == pytest.approx(slope) and beta[0] == pytest.approx(y.mean() - slope * x.mean())
  assert c3.ols_r2(100 + 2 * x, x[:, None])[0] == pytest.approx(1.0, abs=1e-12)       # intercept is fitted
  rng = np.random.default_rng(0)
  x2 = rng.standard_normal((30, 2))
  assert c3.ols_r2(1.0 + 3 * x2[:, 0] - 2 * x2[:, 1], x2)[0] == pytest.approx(1.0, abs=1e-12)


def test_centre_within_subject_hand_values_and_simpson_case():
  df = pd.DataFrame({"subject": ["S01"] * 3 + ["S02"] * 3, "v": [1.0, 2.0, 3.0, 10.0, 20.0, 60.0]})
  c = c3.centre_within_subject(df, ["v"])
  assert np.allclose(c["v"], [-1, 0, 1, -20, -10, 30])
  rows = []
  for s, off in (("S01", 0.0), ("S02", 10.0), ("S03", 20.0)):
    for i, c_ in enumerate((101, 102, 103)):
      rows.append(dict(subject=s, condition=c_, method="plv", target_snr_db=off + i, alpha_change_db=0.1 * i * (-1) ** i,
                       mean_delta=off - 0.5 * i))                      # between-subject slope up, within-subject down
  st = c3.confound_statistics(pd.DataFrame(rows))
  cor = st["correlations"].set_index(["scope", "predictor"])
  assert cor.loc[("all", "target_snr_db"), "spearman_rho"] > 0.5
  assert cor.loc[("centred", "target_snr_db"), "spearman_rho"] == pytest.approx(-1.0)
  ols = st["ols"].set_index("scope")
  assert ols.loc["centred", "r2_snr_only"] == pytest.approx(1.0, abs=1e-9)


# ------------------------------------------------------------------ file list (PF-27) and schemas (section 6)

def test_no_misspelled_duplicate_anywhere_in_repo():
  bad = "co" + "found"
  skip = {".git", ".venv", "data", "reference", "scratch", "__pycache__", "outputs", "reports"}
  hits = [p for p in ROOT.rglob("*") if bad in p.name and not (skip & set(p.relative_to(ROOT).parts))]
  assert hits == []
  tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
  assert bad not in tracked
  assert (ROOT / "scripts/connectivity/diagnostics/check_power_alpha_confound.py").is_file()


def _fixture_tree(root, n_subjects=1):
  rng = np.random.default_rng(0)
  labels = []
  for _ in range(8):
    for c in (201, 101, 201, 102, 201, 103, 201, 104, 201, 105):
      labels += [c] * (2 if c == 201 else 5)
    labels += [202]
  y = np.array(labels)
  for i in range(n_subjects):
    d = Path(root) / f"S0{i + 1}"
    d.mkdir(parents=True)
    np.save(d / "X_time_windows.npy", 10.0 * rng.standard_normal((len(y), 7, 256)))
    np.save(d / "y_labels.npy", y)


def test_confound_script_end_to_end_schema_and_no_cofound_file(tmp_path):
  _fixture_tree(tmp_path / "data")
  comp = tmp_path / "rep" / "connectivity_comparison"
  comp.mkdir(parents=True)
  rows = [dict(subject="S01", method="coherence", condition=c, frequency=f, mean_delta=0.1 * i, n_fdr_edges=0)
          for i, (c, f) in enumerate(c3.CONDITION_FREQS.items())]
  pd.DataFrame(rows).to_csv(comp / "coherence_global_delta.csv", index=False)
  assert c3.main(["--data-root", str(tmp_path / "data"), "--reports-dir", str(tmp_path / "rep"), "--methods",
                  "coherence", "--no-figures"]) == 0
  tab = pd.read_csv(comp / "power_confound_table.csv")
  assert list(tab.columns) == ["subject", "condition", "frequency", "target_snr_db", "alpha_change_db",
                               "n_stim_windows", "n_base_windows", "channels_used"] and len(tab) == 5
  cells = pd.read_csv(comp / "power_vs_connectivity_cells.csv")
  assert set(cells.columns) == set(tab.columns) | {"mean_delta", "method"}
  assert len(cells) == 5 and set(cells["method"]) == {"coherence"}
  assert not [p for p in (tmp_path / "rep").rglob("*") if ("co" + "found") in p.name]
  assert {p.name for p in comp.glob("power_*.csv")} >= {"power_confound_table.csv", "power_vs_connectivity_cells.csv"}


def test_comparison_script_section6_schemas_for_all_four_methods(tmp_path):
  rng = np.random.default_rng(3)
  kept = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  for s in ("S01", "S02"):
    for m in ("coherence", "plv", "wpli", "pdc"):
      diffs = {}
      for c in (101, 102, 103, 104, 105):
        x = rng.standard_normal((7, 7))
        diffs[c] = x if m == "pdc" else 0.5 * (x + x.T)
      _write_edges(tmp_path / f"{s}_{m}.npz", kept, diffs)
  args = c1.build_parser().parse_args(["--edges-dir", str(tmp_path), "--reports-dir", str(tmp_path / "rep"),
                                       "--qap-permutations", "20", "--no-figures", "--responders", "S01"])
  c1.run(args)
  d = tmp_path / "rep" / "connectivity_comparison"
  for m in ("coherence", "plv", "wpli", "pdc"):
    assert list(pd.read_csv(d / f"{m}_frequency_similarity.csv").columns) == ["subject", "method", "freq_a", "freq_b", "r", "p_qap"]
    assert list(pd.read_csv(d / f"{m}_node_strength.csv").columns) == ["subject", "method", "condition", "frequency",
                                                                       "channel", "node_strength"]
    gd = pd.read_csv(d / f"{m}_global_delta.csv")
    assert list(gd.columns) == ["subject", "method", "condition", "frequency", "mean_delta", "n_fdr_edges"]
    assert len(gd) == 10 and len(pd.read_csv(d / f"{m}_frequency_similarity.csv")) == 20
    assert len(pd.read_csv(d / f"{m}_node_strength.csv")) == 2 * 5 * 8
