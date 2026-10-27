"""P14 builder tests: embedding, QAP, node strength, Fisher-z, responders, split-half, pairwise permutations,
ceiling, Fisher-combined p, SNR/alpha, OLS/Spearman, file list (PF-21 to PF-27, R4, R6, R7)."""

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import chi2

from scripts.connectivity.comparison import compare_connectivity_frequencies as c1
from scripts.connectivity.comparison import test_connectivity_frequency_differences as c2
from scripts.connectivity.diagnostics import check_power_alpha_confound as c3
from src.features.connectivity import comparison as cmp
from src.features.connectivity import permutation as pm
from src.features.connectivity.connectivity_extraction import compute_condition_coherence
from src.features.connectivity.phase_connectivity import compute_condition_plv

ROOT = Path(__file__).resolve().parents[1]
FS = 250.0
BAND_A, BAND_B = (23.0, 25.0), (19.0, 21.0)


def _sym(rng, n):
  m = rng.standard_normal((n, n))
  m = 0.5 * (m + m.T)
  np.fill_diagonal(m, np.nan)
  return m


# ---------------------------------------------------------------- embedding, node strength, Fisher-z (PF-25, PF-26)

def test_embedding_with_missing_channel_aligns_by_name():
  kept = ["PO3", "POz", "PO4", "PO8", "O1", "O2"]          # PO7 and Oz absent
  m = np.arange(36, dtype=float).reshape(6, 6)
  e = cmp.embed_to_montage(m, kept)
  mont = list(cmp.MONTAGE)
  assert e.shape == (8, 8)
  for name in ("PO7", "Oz"):
    i = mont.index(name)
    assert np.isnan(e[i]).all() and np.isnan(e[:, i]).all()
  for i, a in enumerate(kept):
    for j, b in enumerate(kept):
      assert e[mont.index(a), mont.index(b)] == m[i, j]
  # O2 sits after the missing Oz in the montage but before nothing in kept: the shift is by name, not position
  assert e[mont.index("O2"), mont.index("PO3")] == m[5, 0]


def test_embedding_rejects_unknown_channel():
  with pytest.raises(ValueError):
    cmp.embed_to_montage(np.zeros((2, 2)), ["PO3", "Cz"])


def test_node_strength_known_matrix_and_pdc_symmetrized():
  kept = ["PO3", "POz", "PO4"]
  m = np.array([[0, 1.0, 2.0], [3.0, 0, 4.0], [5.0, 6.0, 0]])      # directed, [i, j] = j -> i
  s = c1.undirected_delta(m, kept, directed=True)
  mont = list(cmp.MONTAGE)
  i, j, k = (mont.index(c) for c in kept)
  assert s[i, j] == s[j, i] == 2.0 and s[i, k] == s[k, i] == 3.5 and s[j, k] == s[k, j] == 5.0
  ns = cmp.node_strength(s)
  assert ns[i] == pytest.approx((2.0 + 3.5) / 2) and ns[j] == pytest.approx((2.0 + 5.0) / 2)
  assert ns[k] == pytest.approx((3.5 + 5.0) / 2) and np.isnan(ns[mont.index("PO7")])
  # global mean of the symmetrized matrix = mean over all 6 directed entries
  assert cmp.mean_upper(s) == pytest.approx(np.mean([1, 2, 3, 4, 5, 6]))
  # symmetric methods are untouched
  sym = np.array([[0, 1.0], [1.0, 0]])
  assert c1.undirected_delta(sym, ["PO3", "POz"], directed=False)[mont.index("PO3"), mont.index("POz")] == 1.0


def test_fisher_mean_hand_result():
  z = (math.atanh(0.5) + math.atanh(0.8)) / 2
  assert cmp.fisher_mean([0.5, 0.8]) == pytest.approx(math.tanh(z), abs=1e-12)
  assert cmp.fisher_mean([0.3, np.nan]) == pytest.approx(0.3, abs=1e-12)


# ---------------------------------------------------------------- QAP

def test_qap_identical_structure_is_significant_and_independent_is_not():
  rng = np.random.default_rng(0)
  x = rng.standard_normal(7)
  a = np.outer(x, x) + 0.05 * _sym(rng, 7)
  b = a + 0.05 * _sym(rng, 7)
  np.fill_diagonal(a, np.nan)
  np.fill_diagonal(b, np.nan)
  q = cmp.qap_pvalue(a, b, 2000, 1)
  assert q["r"] > 0.9 and q["p"] <= 0.01 and q["n_pairs"] == 21 and q["n_shared"] == 7
  ps = [cmp.qap_pvalue(_sym(rng, 7), _sym(rng, 7), 1000, i)["p"] for i in range(150)]
  assert 0.4 < np.mean(ps) < 0.6 and np.mean(np.array(ps) < 0.05) < 0.12


def test_qap_matches_exhaustive_relabelling_distribution():
  """R6: rows and columns are permuted together; compare with all 7! node relabellings."""
  rng = np.random.default_rng(3)
  a, b = _sym(rng, 7), _sym(rng, 7)
  iu = np.triu_indices(7, 1)
  obs = np.corrcoef(a[iu], b[iu])[0, 1]
  exact = np.mean([np.corrcoef(a[iu], b[np.ix_(p, p)][iu])[0, 1] >= obs - 1e-12
                   for p in itertools.permutations(range(7))])
  q = cmp.qap_pvalue(a, b, 6000, 5)
  assert q["r"] == pytest.approx(obs, abs=1e-12)
  assert q["p"] == pytest.approx(exact, abs=0.03)


def test_qap_permutes_only_present_channels_and_applicability():
  rng = np.random.default_rng(1)
  kept = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  a = cmp.embed_to_montage(_sym(rng, 7), kept)
  b = cmp.embed_to_montage(_sym(rng, 7), kept)
  q = cmp.qap_pvalue(a, b, 200, 0)
  assert q["n_shared"] == 7 and q["n_pairs"] == 21 and np.isfinite(q["p"])
  few = cmp.embed_to_montage(_sym(rng, 3), kept[:3])
  assert np.isnan(cmp.qap_pvalue(few, few, 200, 0)["p"])           # < 4 shared channels
  four = cmp.embed_to_montage(_sym(rng, 4), kept[:4])
  assert np.isfinite(cmp.qap_pvalue(four, four, 200, 0)["p"]) and cmp.qap_pvalue(four, four, 200, 0)["n_pairs"] == 6


def test_qap_seed_is_reproducible():
  rng = np.random.default_rng(2)
  a, b = _sym(rng, 7), _sym(rng, 7)
  assert cmp.qap_pvalue(a, b, 300, 11) == cmp.qap_pvalue(a, b, 300, 11)


# ---------------------------------------------------------------- responders (PF-21)

def test_responders_from_benchmark_csv(tmp_path):
  p = tmp_path / "b.csv"
  pd.DataFrame({"Subject": ["S01", "S02", "S03", "S04", "Mean"], "2.0s Smoothed (%)": [67.5, 61.7, 90.4, 80.0, 74.9]}
               ).to_csv(p, index=False)
  resp, non = cmp.responders_from_benchmark(p)
  assert resp == ["S03", "S04"] and non == ["S01", "S02"]


def test_responders_real_benchmark_if_present():
  p = ROOT / "reports" / "n_subjects_benchmark.csv"
  if not p.is_file():
    pytest.skip("no benchmark")
  assert cmp.responders_from_benchmark(p) == (["S03", "S04", "S05"], ["S01", "S02"])


# ---------------------------------------------------------------- reliability (PF-22), ceiling

def test_spearman_brown_only_for_positive_r():
  assert cmp.spearman_brown(0.5) == (pytest.approx(2 * 0.5 / 1.5), True)
  assert cmp.spearman_brown(-0.4) == (-0.4, False)       # 2r/(1+r) would be -1.33
  assert cmp.spearman_brown(0.0) == (0.0, False)


def test_ceiling_and_disattenuation():
  assert cmp.reliability_ceiling(0.81, 0.64) == pytest.approx(0.72, abs=1e-12)
  assert np.isnan(cmp.reliability_ceiling(-0.2, 0.9)) and np.isnan(cmp.reliability_ceiling(0.0, 0.9))
  assert cmp.disattenuate(0.4, 0.5) == pytest.approx(0.8)
  assert np.isnan(cmp.disattenuate(0.4, 0.1)) and np.isnan(cmp.disattenuate(0.4, 0.05))
  assert cmp.disattenuate(0.4, 0.1000001) == pytest.approx(0.4 / 0.1000001)


def test_fisher_combined_matches_closed_form():
  p = [0.05, 0.2, 0.5]
  stat, pc, k = cmp.fisher_combined_p(p)
  x = -2 * sum(math.log(v) for v in p)
  closed = math.exp(-x / 2) * sum((x / 2) ** j / math.factorial(j) for j in range(3))   # chi2 sf, df = 6
  assert k == 3 and stat == pytest.approx(x, abs=1e-12) and pc == pytest.approx(closed, abs=1e-12)
  assert cmp.fisher_combined_p([np.nan, 0.5])[2] == 1


def _coupled(rng, n_win, weights, t=256, coupling=True):
  """Windows (n, C, T): channels share one latent source with channel weights; noise is independent."""
  c = len(weights)
  noise = rng.standard_normal((n_win, c, t))
  if not coupling:
    return noise
  s = rng.standard_normal((n_win, 1, t))
  return noise + np.asarray(weights)[None, :, None] * s


def _ids(n_win, per_trial):
  return np.repeat(np.arange(n_win // per_trial), per_trial)


def test_split_half_high_on_strong_pattern_and_sb_applied():
  rng = np.random.default_rng(0)
  w = [2.5, 2.0, 1.4, 1.0, 0.6, 0.3]
  stim, base = _coupled(rng, 60, w), _coupled(rng, 60, w, coupling=False)
  r = cmp.split_half_delta_reliability(stim, _ids(60, 5), base, _ids(60, 2), BAND_A, FS, compute_condition_coherence,
                                       n_splits=6, seed=1)
  assert r["r_fisher"] > 0.8 and r["corrected"] and r["reliability"] > r["r_fisher"]
  assert r["reliability"] == pytest.approx(2 * r["r_fisher"] / (1 + r["r_fisher"]))
  assert r["n_valid"] == 6


def test_split_half_nonpositive_left_uncorrected():
  """Two halves with no shared pattern: whenever the Fisher mean r is <= 0 it is reported as is."""
  rng = np.random.default_rng(0)
  for seed in range(8):
    r = cmp.split_half_delta_reliability(_coupled(rng, 20, [1] * 5, coupling=False), _ids(20, 5),
                                         _coupled(rng, 20, [1] * 5, coupling=False), _ids(20, 2), BAND_A, FS,
                                         compute_condition_plv, n_splits=4, seed=seed)
    if r["r_fisher"] <= 0:
      assert not r["corrected"] and r["reliability"] == r["r_fisher"]
    else:
      assert r["corrected"]


# ---------------------------------------------------------------- pairwise permutation test (PF-19, R7)

def test_pairwise_uses_observed_sizes_and_whole_trials(monkeypatch):
  rng = np.random.default_rng(0)
  a, b, base = rng.standard_normal((25, 4, 128)), rng.standard_normal((40, 4, 128)), rng.standard_normal((20, 4, 128))
  ids_a, ids_b = _ids(25, 5), _ids(40, 5)                     # labels collide on purpose
  seen = []
  orig = pm._trial_permutation_split

  def spy(ids, n_first, rng_):
    ia, ib = orig(ids, n_first, rng_)
    seen.append((len(ia), len(ib), n_first, ids, ia))
    return ia, ib
  monkeypatch.setattr(cmp, "_trial_permutation_split", spy)
  cmp.pairwise_permutation_test(a, ids_a, b, ids_b, base, BAND_A, BAND_B, FS, compute_condition_plv, 12, 7)
  assert len(seen) == 12
  for na, nb, n_first, ids, ia in seen:
    assert na == 25 == n_first and nb == 40
    assert len(np.unique(ids)) == 5 + 8                          # colliding labels were made distinct
    whole = sum(1 for u in np.unique(ids) if (np.isin(np.flatnonzero(ids == u), ia).all()
                                              or not np.isin(np.flatnonzero(ids == u), ia).any()))
    assert whole >= len(np.unique(ids)) - 1                      # at most one trial is split


def test_pairwise_null_is_uniform_for_identical_processes_and_small_for_planted_difference():
  w = [1.5, 1.2, 1.0, 0.8, 0.5]
  ps_mag, ps_pat = [], []
  for rep in range(40):
    rng = np.random.default_rng(100 + rep)
    a, b = _coupled(rng, 30, w), _coupled(rng, 30, w)
    base = _coupled(rng, 40, [0.0] * 5, coupling=False)
    r = cmp.pairwise_permutation_test(a, _ids(30, 5), b, _ids(30, 5) , base, BAND_A, BAND_B, FS,
                                      compute_condition_plv, 99, rep)
    ps_mag.append(r["p_mag"])
    ps_pat.append(r["p_pat"])
  assert 0.35 < np.mean(ps_mag) < 0.65 and np.mean(np.array(ps_mag) < 0.05) < 0.15
  assert 0.35 < np.mean(ps_pat) < 0.65 and np.mean(np.array(ps_pat) < 0.05) < 0.15
  rng = np.random.default_rng(5)
  a = _coupled(rng, 40, w)                                       # coupled vs independent noise
  b = _coupled(rng, 40, w, coupling=False)
  base = _coupled(rng, 40, w, coupling=False)
  r = cmp.pairwise_permutation_test(a, _ids(40, 5), b, _ids(40, 5), base, BAND_A, BAND_B, FS, compute_condition_coherence, 99, 3)
  assert r["p_mag"] <= 0.02 and r["t_mag"] > 0 and r["n_edges"] == 10


def test_pairwise_pattern_detects_different_pattern_with_same_magnitude():
  rng = np.random.default_rng(8)
  wa, wb = [2.0, 2.0, 0.2, 0.2, 0.2, 0.2], [0.2, 0.2, 0.2, 0.2, 2.0, 2.0]
  a, b = _coupled(rng, 50, wa), _coupled(rng, 50, wb)
  base = _coupled(rng, 50, [0.0] * 6, coupling=False)
  r = cmp.pairwise_permutation_test(a, _ids(50, 5), b, _ids(50, 5), base, BAND_A, BAND_A, FS,
                                    compute_condition_coherence, 99, 4)
  assert r["r_obs"] < 0.2 and r["p_pat"] <= 0.02


def test_pairwise_is_deterministic_and_nested_seeds():
  rng = np.random.default_rng(0)
  a, b, base = (rng.standard_normal((20, 4, 128)) for _ in range(3))
  args = (a, _ids(20, 5), b, _ids(20, 5), base, BAND_A, BAND_B, FS, compute_condition_plv)
  r1, r2 = cmp.pairwise_permutation_test(*args, 30, 9), cmp.pairwise_permutation_test(*args, 30, 9)
  assert r1["p_mag"] == r2["p_mag"] and r1["p_pat"] == r2["p_pat"]
  assert (np.random.SeedSequence(5).generate_state(500) == np.random.SeedSequence(5).generate_state(1000)[:500]).all()


def test_pairwise_rejects_directed_methods():
  from src.features.connectivity.mvar_pdc import compute_condition_pdc
  x = np.random.default_rng(0).standard_normal((10, 3, 64))
  with pytest.raises(ValueError):
    cmp.pairwise_permutation_test(x, _ids(10, 5), x, _ids(10, 5), x, BAND_A, BAND_B, FS, compute_condition_pdc, 5, 0)


# ---------------------------------------------------------------- end-to-end on a synthetic tree

def _tree(root, subject="S01", seed=0, reps=8):
  rng = np.random.default_rng(seed)
  labels = []
  for _ in range(reps):
    for c in (201, 101, 201, 102, 201, 103, 201, 104, 201, 105):
      labels += [c] * (2 if c == 201 else 5)
    labels += [202]
  y = np.array(labels)
  X = 10.0 * rng.standard_normal((len(y), 7, 256))
  d = Path(root) / subject
  d.mkdir(parents=True)
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  return y


def test_pairwise_script_schema_and_njobs_independence(tmp_path):
  _tree(tmp_path / "data")
  outs = []
  for nj, sub in ((1, "a"), (2, "b")):
    args = c2.build_parser().parse_args(["--data-root", str(tmp_path / "data"), "--reports-dir", str(tmp_path / sub),
                                         "--methods", "plv", "--permutations", "9", "--splits", "3", "--n-jobs", str(nj),
                                         "--out-suffix", "t", "--responders", "S01"])
    c2.run(args)
    outs.append(pd.read_csv(c2.csv_path(tmp_path / sub, "plv", "pairwise_tests", "t")))
  pd.testing.assert_frame_equal(outs[0], outs[1])
  df = outs[0]
  assert list(df.columns) == ["subject", "method", "freq_a", "freq_b", "t_mag", "p_mag", "d_pat", "p_pat", "r_obs",
                              "n_edges_fdr", "n_edges", "reliability_ceiling", "r_disattenuated",
                              "trial_ids_approximate", "sig_bh_mag", "sig_bh_pat"]
  assert len(df) == 10 and (df["n_edges"] == 21).all() and (df["p_mag"] >= 1 / 10).all()
  rel = pd.read_csv(c2.csv_path(tmp_path / "a", "plv", "split_half_reliability", "t"))
  assert list(rel.columns) == ["subject", "method", "condition", "frequency", "split_half_reliability"] and len(rel) == 5
  comb = pd.read_csv(c2.csv_path(tmp_path / "a", "plv", "pairwise_combined", "t"))
  assert set(comb["group"]) == {"responders"} and (comb["k_subjects"] == 1).all()   # no non-responder in this tree


def test_compare_flips_across_alpha(tmp_path):
  base = dict(subject="S01", method="plv", freq_a=24.0, freq_b=20.0, t_mag=0.1, d_pat=0.3, r_obs=0.7,
              n_edges=21, reliability_ceiling=0.9, r_disattenuated=0.7, trial_ids_approximate=False,
              sig_bh_mag=False, sig_bh_pat=False)
  rows_a = [dict(base, p_mag=0.04, p_pat=0.30, n_edges_fdr=0), dict(base, freq_b=15.0, p_mag=0.30, p_pat=0.30, n_edges_fdr=0)]
  rows_b = [dict(base, p_mag=0.06, p_pat=0.30, n_edges_fdr=0), dict(base, freq_b=15.0, p_mag=0.31, p_pat=0.30, n_edges_fdr=0)]
  (tmp_path / "connectivity_comparison").mkdir()
  pd.DataFrame(rows_a).to_csv(c2.csv_path(tmp_path, "plv", "pairwise_tests", "p500"), index=False)
  pd.DataFrame(rows_b).to_csv(c2.csv_path(tmp_path, "plv", "pairwise_tests", ""), index=False)
  fl = c2.compare_runs(tmp_path, "p500", "", ["plv"])
  assert len(fl) == 1 and fl["flip_p_mag"].iloc[0] and fl["freq_b"].iloc[0] == 20.0


def test_comparison_script_embeds_symmetrizes_and_writes_schemas(tmp_path):
  edges = tmp_path / "edges"
  edges.mkdir()
  rng = np.random.default_rng(0)
  full = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  for s, kept in (("S01", full), ("S02", [c for c in full if c != "Oz"])):
    for m in ("coherence", "pdc"):
      d = {"channels_kept": np.array(kept)}
      for c in (101, 102, 103, 104, 105):
        n = len(kept)
        x = rng.standard_normal((n, n))
        x = x if m == "pdc" else 0.5 * (x + x.T)
        d[f"diff_{c}"] = x
        d[f"fdr_{c}"] = np.zeros((n, n), dtype=bool)
      np.savez(edges / f"{s}_{m}.npz", **d)
  args = c1.build_parser().parse_args(["--edges-dir", str(edges), "--reports-dir", str(tmp_path / "rep"),
                                       "--figures-dir", str(tmp_path / "fig"), "--methods", "coherence", "pdc",
                                       "--qap-permutations", "50", "--responders", "S01"])
  out = c1.run(args)
  d = tmp_path / "rep" / "connectivity_comparison"
  assert list(pd.read_csv(d / "coherence_frequency_similarity.csv").columns) == ["subject", "method", "freq_a", "freq_b", "r", "p_qap"]
  nd = pd.read_csv(d / "pdc_node_strength.csv")
  assert list(nd.columns) == ["subject", "method", "condition", "frequency", "channel", "node_strength"]
  assert nd[(nd.subject == "S02") & (nd.channel == "Oz")]["node_strength"].isna().all()
  assert nd[(nd.channel == "PO7")]["node_strength"].isna().all()
  gd = pd.read_csv(d / "pdc_global_delta.csv")
  assert list(gd.columns) == ["subject", "method", "condition", "frequency", "mean_delta", "n_fdr_edges"] and len(gd) == 10
  assert (d / "coherence_delta_matrices_all.png").is_file() or (tmp_path / "fig" / "coherence_delta_matrices_all.png").is_file()
  assert len(out["pdc"]["similarity"]) == 20                    # 2 subjects x 10 pairs


# ---------------------------------------------------------------- SNR / alpha (PF-23)

def _tones(n, freqs_amps, fs=FS, t=256, noise=1e-4, seed=0):
  rng = np.random.default_rng(seed)
  tt = np.arange(t) / fs
  x = noise * rng.standard_normal((n, 3, t))
  for f, a in freqs_amps:
    x += a * np.sin(2 * np.pi * f * tt)[None, None, :]
  return x


def test_snr_and_alpha_change_as_planted():
  base = _tones(20, [(20.0, 1.0), (9.765625, 1.0)])
  stim = _tones(20, [(20.0, 2.0), (9.765625, 0.5)], seed=1)         # +6.02 dB at the target, -6.02 dB in alpha
  m = c3.power_metrics(stim, base, [0, 1, 2], 20.0, FS)
  assert m["target_snr_db"] == pytest.approx(20 * math.log10(2.0), abs=0.2)
  assert m["alpha_change_db"] == pytest.approx(20 * math.log10(0.5), abs=0.2)


def test_target_inside_alpha_does_not_contaminate_alpha_measure():
  """PF-23: a 10.91 Hz target gives alpha change ~ 0; without the f0 +- 1.5 Hz exclusion it does not."""
  rng = np.random.default_rng(0)
  base = rng.standard_normal((300, 3, 256))
  stim = rng.standard_normal((300, 3, 256)) + 0.6 * np.sin(2 * np.pi * 10.9091 * np.arange(256) / FS)[None, None]
  f0 = 10.9091
  m = c3.power_metrics(stim, base, [0, 1, 2], f0, FS)
  assert m["target_snr_db"] > 5.0
  assert abs(m["alpha_change_db"]) < 0.2
  f, ps = c3.mean_psd(stim, [0, 1, 2], FS)
  _, pb = c3.mean_psd(base, [0, 1, 2], FS)
  naive = (f >= 8) & (f <= 13)                                       # the historical contaminated measure
  assert 10 * math.log10(ps[naive].mean() / pb[naive].mean()) > 1.0
  am = c3.alpha_mask(f, f0)
  assert not am[np.abs(f - f0) <= 1.5].any() and am.any()


def test_alpha_mask_edges_for_both_in_alpha_targets():
  f = np.fft.rfftfreq(256, 1 / FS)
  for f0 in (10.9091, 8.5714):
    am = c3.alpha_mask(f, f0)
    assert f[am].min() >= 8 and f[am].max() <= 13 and (np.abs(f[am] - f0) > 1.5).all()
  assert c3.alpha_mask(f, 24.0).sum() == ((f >= 8) & (f <= 13)).sum()    # nothing to exclude out of band


# ---------------------------------------------------------------- OLS / Spearman / files

def test_ols_and_spearman_known_linear_data():
  rng = np.random.default_rng(0)
  rows = []
  for s in ("S01", "S02", "S03", "S04", "S05"):
    for c in (101, 102, 103, 104, 105):
      snr, al = rng.uniform(0, 10), rng.uniform(-3, 1)
      rows.append(dict(subject=s, condition=c, frequency=1.0, method="coherence", target_snr_db=snr,
                       alpha_change_db=al, mean_delta=0.5 + 0.2 * snr - 0.1 * al))
  cells = pd.DataFrame(rows)
  st = c3.confound_statistics(cells)
  ols = st["ols"].set_index("scope")
  assert ols.loc["all", "r2"] == pytest.approx(1.0, abs=1e-9) and ols.loc["centred", "r2"] == pytest.approx(1.0, abs=1e-9)
  assert ols.loc["all", "coef_snr"] == pytest.approx(0.2) and ols.loc["all", "coef_alpha"] == pytest.approx(-0.1)
  r2, _ = c3.ols_r2(cells["mean_delta"].values, cells[["target_snr_db"]].values)
  assert 0 < r2 < 1
  x = np.arange(10.0)
  assert c3.spearman(x, x ** 3)[0] == pytest.approx(1.0) and c3.spearman(x, -x)[0] == pytest.approx(-1.0)


def test_alpha_split_groups_and_s05_table():
  rows = []
  for s in ("S04", "S05"):
    for c, d in zip((101, 102, 103, 104, 105), (1.0, 1.0, 1.0, 5.0, 5.0)):
      rows.append(dict(subject=s, condition=c, frequency=float(c), method="wpli", target_snr_db=float(c - 100),
                       alpha_change_db=-1.0, mean_delta=d))
  cells = pd.DataFrame(rows)
  sp = c3.confound_statistics(cells)["alpha_split"].set_index("group")
  assert sp.loc["in_alpha", "mean_delta"] == 5.0 and sp.loc["out_of_alpha", "mean_delta"] == 1.0
  assert sp.loc["in_alpha", "n_cells"] == 4 and sp.loc["out_of_alpha", "n_cells"] == 6
  s05 = c3.s05_table(cells)
  assert set(s05["subject"]) == {"S05"} and len(s05) == 5


def test_no_misspelled_duplicate_script():
  bad = "co" + "found"                                               # PF-27
  names = [p.name for d in ("scripts", "src", "tests") for p in (ROOT / d).rglob("*.py")]
  assert not [n for n in names if bad in n]
  assert (ROOT / "scripts" / "connectivity" / "diagnostics" / "check_power_alpha_confound.py").is_file()


def test_scripts_do_not_read_raw_recordings():
  for p in (ROOT / "scripts" / "connectivity").rglob("*.py"):
    assert "data/raw" not in p.read_text() and ".ebr" not in p.read_text()


# ---------------------------------------------------------------- pairwise null reading (audit F2)

def _band_coupled(rng, n_win, band, weights, t=256):
  """Windows (n, C, T): independent noise plus ONE latent source restricted to `band`, with channel weights."""
  c = len(weights)
  noise = rng.standard_normal((n_win, c, t))
  spec = np.fft.rfft(rng.standard_normal((n_win, 1, t)), axis=-1)
  f = np.fft.rfftfreq(t, 1 / FS)
  spec[..., (f < band[0]) | (f > band[1])] = 0
  s = 12.0 * np.fft.irfft(spec, n=t, axis=-1)
  return noise + np.asarray(weights)[None, :, None] * s


def test_pairwise_null_is_off_centre_for_a_common_band_effect():
  """Every trial responds in band a only: D_a > 0, D_b ~ 0, so D_a - D_b != 0, yet p_mag is not small
  because the exchange keeps the band effect in the null; the null mean is far from 0 and the centred
  diagnostic puts the observation at the null centre."""
  rng = np.random.default_rng(0)
  w = [1.0] * 5
  a, b = _band_coupled(rng, 40, BAND_A, w), _band_coupled(rng, 40, BAND_A, w)
  base = _coupled(rng, 40, w, coupling=False)
  r = cmp.pairwise_permutation_test(a, _ids(40, 5), b, _ids(40, 5), base, BAND_A, BAND_B, FS,
                                    compute_condition_plv, 199, 1)
  assert r["t_mag"] > 0.2                                              # Delta_a - Delta_b is clearly non-zero
  assert r["p_mag"] > 0.3                                              # ... and is NOT rejected
  assert abs(r["t_null_mean"]) > 0.2 and abs(r["t_null_mean"] - r["t_mag"]) < 0.1   # null centred away from 0
  assert r["p_mag_centred"] > 0.3


def test_pairwise_null_zero_delta_with_b_trials_responding_in_band_a():
  """Delta_a = Delta_b = 0 (b responds only in band a, which b is not scored in): t_obs ~ 0, p_mag ~ 1 although the
  null mean is clearly positive; the centred diagnostic exposes the off-centre null."""
  rng = np.random.default_rng(1)
  w = [1.0] * 5
  a = _coupled(rng, 40, w, coupling=False)
  b = _band_coupled(rng, 40, BAND_A, w)
  base = _coupled(rng, 40, w, coupling=False)
  r = cmp.pairwise_permutation_test(a, _ids(40, 5), b, _ids(40, 5), base, BAND_A, BAND_B, FS,
                                    compute_condition_plv, 199, 2)
  assert abs(r["t_mag"]) < 0.05 and r["p_mag"] > 0.9
  assert r["t_null_mean"] > 0.1 and r["t_null_sd"] > 0
  assert r["p_mag_centred"] < 0.05
  assert r["p_mag_centred"] >= 1 / 200                                       # +1 pseudo-count floor


def test_null_diagnostic_csv_leaves_primary_csvs_untouched(tmp_path):
  """The section 6 pairwise CSV is byte-identical whether or not the diagnostic exists, and has the F2 columns."""
  _tree(tmp_path / "data")
  def go(sub):
    args = c2.build_parser().parse_args(["--data-root", str(tmp_path / "data"), "--reports-dir", str(tmp_path / sub),
                                         "--methods", "plv", "--permutations", "9", "--splits", "3", "--n-jobs", "1",
                                         "--out-suffix", "t", "--random-state", "7", "--responders", "S01"])
    c2.run(args)
    return tmp_path / sub
  r1, r2 = go("a"), go("b")
  f = c2.csv_path(r1, "plv", "pairwise_tests", "t")
  assert f.read_bytes() == c2.csv_path(r2, "plv", "pairwise_tests", "t").read_bytes()
  assert list(pd.read_csv(f).columns) == c2.PAIRWISE_COLUMNS
  nl = pd.read_csv(c2.csv_path(r1, "plv", "pairwise_null", "t"))
  assert list(nl.columns) == ["subject", "method", "freq_a", "freq_b", "t_null_mean", "t_null_sd", "p_mag_centred",
                              "d_null_mean", "d_null_sd"] and len(nl) == 10
  assert ((nl["p_mag_centred"] >= 1 / 10) & (nl["p_mag_centred"] <= 1)).all()
  # the primary columns equal the ones computed without the diagnostic fields (same seeds, same code path)
  prim = pd.read_csv(f)
  assert (prim["p_mag"] >= 0.1).all()


def test_random_state_and_suffix_for_diag_e3(tmp_path):
  _tree(tmp_path / "data")
  outs = {}
  for rs in (1, 2):
    args = c2.build_parser().parse_args(["--data-root", str(tmp_path / "data"), "--reports-dir", str(tmp_path / "r"),
                                         "--methods", "plv", "--permutations", "9", "--splits", "2", "--n-jobs", "1",
                                         "--random-state", str(rs), "--out-suffix", f"diagE3_rs{rs}",
                                         "--responders", "S01"])
    c2.run(args)
    outs[rs] = pd.read_csv(c2.csv_path(tmp_path / "r", "plv", "pairwise_tests", f"diagE3_rs{rs}"))
  assert (tmp_path / "r" / "connectivity_comparison" / "plv_pairwise_null_diagE3_rs1.csv").is_file()
  assert not (tmp_path / "r" / "connectivity_comparison" / "plv_pairwise_tests.csv").exists()   # suffix keeps runs apart
  assert not outs[1]["p_mag"].equals(outs[2]["p_mag"])                                           # seed changes the draws
