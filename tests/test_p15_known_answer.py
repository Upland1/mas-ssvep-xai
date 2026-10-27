"""Independent known-answer tests of P15 (graph features, connectivity gate, GNN).

Own generators and own numpy references; synthetic data only (no generated or ignored files are read).
Layouts: node column h*5 + k (harmonic-major); upper triangle pair-major, then band, then cos/sin.
"""

import hashlib
import types

import numpy as np
import pandas as pd
import pytest
import torch
from scipy.signal import coherence as sp_coherence

from scripts.connectivity.graph_modeling import benchmark_connectivity_gate as gate
from scripts.connectivity.graph_modeling import benchmark_gnn as gnn
from scripts.connectivity.graph_modeling import build_graph_dataset as bgd
from src.features.connectivity import connectivity_graph_features as cgf
from src.features.connectivity import graph_dataset as gd
from src.features.connectivity import graph_inputs as gi
from src.models.classical import legacy_eval as le
from src.models.graph.connectivity_gnn import ConnectivityGNN, EdgeGatedLayer, count_parameters
from tests.p05_synth import write_subject

FS = 250.0
T = 256
TARGETS = (24.0, 20.0, 15.0, 10.9091, 8.5714)


def _t():
  return np.arange(T) / FS


def _noise(n, C, seed, sd=0.05):
  return np.random.default_rng(seed).normal(0, sd, (n, C, T))


# --- node band power ------------------------------------------------------------------------

@pytest.mark.parametrize("h", [1, 2])
@pytest.mark.parametrize("k", range(5))
def test_node_power_tone_lands_in_harmonic_major_column(h, k):
  ch = (3 * k + h) % 7
  w = _noise(1, 7, 10 * h + k)
  w[0, ch] += np.sin(2 * np.pi * h * TARGETS[k] * _t() + 0.3)
  out = cgf.node_band_power(w, FS)
  assert out.shape == (1, 7, 10)
  assert np.unravel_index(np.argmax(out[0]), out[0].shape) == (ch, (h - 1) * 5 + k)


def test_node_power_hand_check_log10_of_mean_over_pm1hz_bins():
  fs, n = 16.0, 16                       # 1 Hz bins
  rng = np.random.default_rng(3)
  x = rng.normal(size=(1, 2, n))
  out = cgf.node_band_power(x, fs, targets=[3.0, 4.0])
  hann = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
  p = np.abs(np.fft.rfft((x[0] - x[0].mean(axis=-1, keepdims=True)) * hann, axis=-1)) ** 2
  # fundamentals 3 and 4 Hz -> bins {2,3,4} and {3,4,5}; 2nd harmonics 6 and 8 Hz -> bins {5,6,7} and {7,8}
  exp = np.stack([np.log10(p[:, [2, 3, 4]].mean(1)), np.log10(p[:, [3, 4, 5]].mean(1)),
                  np.log10(p[:, [5, 6, 7]].mean(1)), np.log10(p[:, [7, 8]].mean(1))], axis=-1)
  assert np.allclose(out[0], exp, rtol=1e-9, atol=1e-9)
  assert not np.allclose(out[0], np.log10(p[:, [2, 3, 4]].sum(1))[:, None])      # mean, not sum


def test_node_power_nearest_bin_fallback():
  fs, n = 16.0, 4                        # bins 0, 4, 8 Hz: nothing within +-1 Hz of 5.5
  x = np.random.default_rng(1).normal(size=(1, 1, n))
  out = cgf.node_band_power(x, fs, targets=[5.5])
  hann = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
  p = np.abs(np.fft.rfft((x[0, 0] - x[0, 0].mean()) * hann)) ** 2
  assert np.isclose(out[0, 0, 0], np.log10(p[1]))        # 5.5 -> 4 Hz
  assert np.isclose(out[0, 0, 1], np.log10(p[2]))        # 11 Hz -> 8 Hz (last bin)


# --- edge coherence ---------------------------------------------------------------------------

def test_edge_coherence_matches_scipy_welch_three_segments():
  rng = np.random.default_rng(5)
  w = rng.normal(size=(2, 4, T))
  w[:, 2] += 0.7 * w[:, 0]
  out = cgf.edge_coherence(w, FS)
  f, c = sp_coherence(w[1, 0], w[1, 2], fs=FS, window="hann", nperseg=128, noverlap=64, detrend="constant")
  for kk, tf in enumerate(TARGETS):
    sel = np.abs(f - tf) <= 1.0 + 1e-9
    if not sel.any():
      sel = np.zeros_like(sel); sel[np.argmin(np.abs(f - tf))] = True
    assert np.isclose(out[1, 0, 2, kk], c[sel].mean(), atol=1e-9)


def test_edge_coherence_coupled_pair_high_independent_low_symmetric():
  w = _noise(1, 7, 10, sd=1.0)
  tone = np.sin(2 * np.pi * 20.0 * _t())
  w[0, 1] += 5 * tone
  w[0, 4] += 5 * np.sin(2 * np.pi * 20.0 * _t() + 0.8)
  out = cgf.edge_coherence(w, FS)[0]
  assert out.shape == (7, 7, 5)
  assert out[1, 4, 1] > 0.9
  others = [out[i, j, 1] for i in range(7) for j in range(i + 1, 7) if (i, j) != (1, 4)]
  assert out[1, 4, 1] > max(others) + 0.1 and np.mean(others) < 0.5   # 3-segment MSC of noise is biased upward (~1/3)
  assert np.allclose(out, out.transpose(1, 0, 2)) and np.allclose(out[np.arange(7), np.arange(7)], 1.0)
  assert (out >= -1e-12).all() and (out <= 1 + 1e-9).all()


# --- edge phase -------------------------------------------------------------------------------

def test_edge_phase_known_lag_is_unit_phasor_cos_sin():
  f0 = 20 * FS / T                       # bin-centred 19.53125 Hz
  phis = [0.0, 0.7, -1.9, 2.5]
  w = np.stack([3.0 * np.cos(2 * np.pi * f0 * _t() + p) for p in phis])[None]
  out = cgf.edge_phase(w, FS, targets=[f0])
  assert out.shape == (1, 4, 4, 1, 2)
  for i in range(4):
    for j in range(4):
      d = phis[i] - phis[j]
      assert np.allclose(out[0, i, j, 0], [np.cos(d), np.sin(d)], atol=1e-6)
      assert np.allclose(out[0, j, i, 0, 1], -out[0, i, j, 0, 1], atol=1e-9)
      assert np.isclose(out[0, j, i, 0, 0], out[0, i, j, 0, 0], atol=1e-9)


def test_edge_phase_unit_norm_for_noise_default_targets():
  out = cgf.edge_phase(_noise(3, 5, 4, sd=7.0), FS)
  assert out.shape == (3, 5, 5, 5, 2)
  assert np.allclose(np.linalg.norm(out, axis=-1), 1.0, atol=1e-9)
  assert np.allclose(out[:, np.arange(5), np.arange(5)], [1.0, 0.0])


def test_upper_tri_flat_pair_major_then_band_then_cs():
  n, C, B = 2, 5, 5
  code = np.zeros((n, C, C, B, 2))
  for s in range(n):
    for i in range(C):
      for j in range(C):
        for b in range(B):
          for c in range(2):
            code[s, i, j, b, c] = 10000 * s + 1000 * i + 100 * j + 10 * b + c
  flat = cgf.upper_tri_flat(code)
  exp = [[10000 * s + 1000 * i + 100 * j + 10 * b + c for i in range(C) for j in range(i + 1, C)
          for b in range(B) for c in range(2)] for s in range(n)]
  assert flat.shape == (n, 10 * 5 * 2) and np.array_equal(flat, np.array(exp))
  flat4 = cgf.upper_tri_flat(code[..., 0])
  assert flat4.shape == (n, 50)
  assert flat4[0, 5] == 0 * 1000 + 2 * 100 + 0                       # pair (0,2) band 0


# --- dimensions with 7 and 6 channels ------------------------------------------------------------

class _Sized:
  def __init__(self, ns, n):
    self.__dict__.update(vars(ns))
    self._n = n

  def __len__(self):
    return self._n


def _fake_ds(C, n=4):
  rng = np.random.default_rng(C)
  ds = types.SimpleNamespace(
    node=rng.normal(size=(n, C, 10)), edge_coh=rng.uniform(size=(n, C, C, 5)),
    edge_phase=rng.normal(size=(n, C, C, 5, 2)), X_fbcca=rng.uniform(size=(n, 5)))
  return _Sized(ds, n)


@pytest.mark.parametrize("C", [7, 6])
def test_feature_set_dimensions_follow_channel_count(C):
  p = C * (C - 1) // 2
  N, F, Ec, Ep = 10 * C, 5, 5 * p, 10 * p
  sets = gate.feature_sets(_fake_ds(C))
  assert {k: v.shape[1] for k, v in sets.items()} == {
    "N": N, "F": F, "Base": N + F, "Ec": Ec, "Ep": Ep, "Ec+Ep": Ec + Ep, "Base+Ec": N + F + Ec,
    "Base+Ep": N + F + Ep, "Base+Ec+Ep": N + F + Ec + Ep}
  if C == 7:
    assert (N, Ec, Ep, N + F + Ec + Ep) == (70, 105, 210, 390)
  g = cgf.build_graph_features(np.random.default_rng(0).normal(size=(2, C, T)), FS)
  assert g["node"].shape == (2, C, 10) and g["edge_coh"].shape == (2, C, C, 5) and g["edge_phase"].shape == (2, C, C, 5, 2)
  inp = gi.build_inputs(_fake_ds(C), "nodes+coh+phase+F")
  assert inp.node.shape[1:] == (C, 10) and inp.edge.shape[1:] == (C, C, 15) and inp.graph.shape[1:] == (5,)


# --- gate verdict -------------------------------------------------------------------------------

def _table(base, edge, k=0, other=None):
  rows = []
  for s in base:
    rows.append(dict(subject=s, set="Base", k_select=k, repeat=0, dim=75, acc_1s=base[s], acc_2s=base[s]))
    rows.append(dict(subject=s, set="Base+Ec", k_select=k, repeat=0, dim=180, acc_1s=base[s] + edge[s], acc_2s=0))
    rows.append(dict(subject=s, set="Base+Ep", k_select=k, repeat=0, dim=285, acc_1s=base[s] + (other or {}).get(s, -1), acc_2s=0))
  return pd.DataFrame(rows)


B5 = dict(S01=40.0, S02=50.0, S03=80.0, S04=95.0, S05=96.0)


def test_gate_verdict_cohort_mean_passes_but_responders_fail_gives_no_pass():
  v = gate.gate_verdict(_table(B5, dict(S01=15.0, S02=10.0, S03=0.5, S04=0.0, S05=-1.0)), 0)
  assert v["mean_delta"] >= 2.0 and v["responders_ok"] == 0 and v["passed"] is False


def test_gate_verdict_cases():
  assert gate.gate_verdict(_table(B5, dict(S01=3, S02=3, S03=3, S04=3, S05=3)), 0)["passed"] is True
  # exactly 2 of 3 responders and mean >= 2
  assert gate.gate_verdict(_table(B5, dict(S01=0, S02=0, S03=3, S04=3, S05=1.9)), 0)["passed"] is False   # mean 1.58
  assert gate.gate_verdict(_table(B5, dict(S01=2, S02=2, S03=3, S04=3, S05=1.0)), 0)["passed"] is True
  # responders fine (3 of 3) but cohort mean below 2
  assert gate.gate_verdict(_table(B5, dict(S01=-10, S02=-10, S03=2, S04=2, S05=2)), 0)["passed"] is False
  # only one responder over the bar
  assert gate.gate_verdict(_table(B5, dict(S01=5, S02=5, S03=9, S04=1, S05=1)), 0)["passed"] is False
  # the best edge set is chosen by cohort mean
  v = gate.gate_verdict(_table(B5, dict(S01=1, S02=1, S03=1, S04=1, S05=1), other=dict(S01=4, S02=4, S03=4, S04=4, S05=4)), 0)
  assert v["best"] == "Base+Ep" and v["passed"] is True


# --- R2 and R1 in the gate ----------------------------------------------------------------------

def _tiny_ds(n_trials=24, C=3, signal=0.0, seed=0):
  rng = np.random.default_rng(seed)
  n = n_trials * 5
  y = np.tile(np.arange(101, 106), n_trials)
  trial = np.repeat(np.arange(n_trials), 5)
  return gd.GraphDataset("Sx", rng.normal(size=(n, C, 10)) + signal * (y - 103)[:, None, None],
                         rng.uniform(size=(n, C, C, 5)), rng.normal(size=(n, C, C, 5, 2)), rng.uniform(size=(n, 5)),
                         y, trial, [f"c{i}" for i in range(C)], [], 250.0, "h", False)


def _spy_splits(monkeypatch, module):
  calls = []
  orig = module.make_splits

  def spy(cv, y, ids, seed=42):
    s = orig(cv, y, ids, seed)
    calls.append((cv, seed, s, np.asarray(ids)))
    return s
  monkeypatch.setattr(module, "make_splits", spy)
  return calls


def _no_shared(calls):
  for cv, _, splits, ids in calls:
    assert cv == "grouped"
    for tr, te in splits:
      assert not set(ids[tr]) & set(ids[te])


def test_gate_r1_no_trial_shared_for_every_repeat(monkeypatch):
  calls = _spy_splits(monkeypatch, gate)
  gate.evaluate_subject(_tiny_ds(), 3, [0], sets=["Base"])
  assert [c[1] for c in calls] == [42, 43, 44] and len(calls) == 3
  _no_shared(calls)


@pytest.mark.parametrize("k", [0, 30])
def test_gate_r2_test_row_values_do_not_move_other_predictions(k):
  ds = _tiny_ds(signal=0.5)
  X = gate.feature_sets(ds)["Base"]
  y = ds.y
  splits = le.splits_for("grouped", y, ds.trial_ids, 42)
  tr, te = splits[0]
  space = lambda M: le.FeatureSpace("b", [M])
  res0, _ = le.oof_space(space(X), None, y, {"m": gate.make_model(k, X.shape[1])}, 42, [splits[0]])
  X2 = X.copy()
  X2[te[0]] = 1e6
  res1, _ = le.oof_space(space(X2), None, y, {"m": gate.make_model(k, X.shape[1])}, 42, [splits[0]])
  assert np.array_equal(res0["m"]["pred"][te[1:]], res1["m"]["pred"][te[1:]])
  assert np.array_equal(res0["m"]["scores"][te[1:]], res1["m"]["scores"][te[1:]])


def test_gate_r2_selector_pure_noise_stays_at_chance():
  rng = np.random.default_rng(0)
  n_trials = 40
  y = np.tile(np.arange(101, 106), n_trials)
  ids = np.repeat(np.arange(n_trials), 5)
  X = rng.normal(size=(len(y), 600))
  accs = []
  for r in range(3):
    sp = le.splits_for("grouped", y, ids, 42 + r)
    res, _ = le.oof_space(le.FeatureSpace("n", [X]), None, y, {"m": gate.make_model(30, 600)}, 42 + r, sp)
    accs.append((res["m"]["pred"] == y).mean())
  assert np.mean(accs) < 0.30       # chance 0.20; selection on all rows would give far more


def test_gate_scaler_is_in_fold_shifted_test_rows_do_not_move_the_others():
  """A huge shift of one test feature column in the whole test fold leaves the fitted pipeline unchanged: the
  prediction of a test row depends only on that row and the training rows (bit-exact against a clean copy)."""
  ds = _tiny_ds(signal=0.7)
  X = gate.feature_sets(ds)["Base"]
  y = ds.y
  sp = le.splits_for("grouped", y, ds.trial_ids, 42)
  tr, te = sp[0]
  run = lambda M: le.oof_space(le.FeatureSpace("a", [M]), None, y, {"m": gate.make_model(0, X.shape[1])}, 42, [sp[0]])[0]["m"]["scores"]
  base = run(X)
  X2 = X.copy()
  X2[te[0], 3] += 1e4
  X2[te[1], 5] -= 1e4
  shifted = run(X2)
  assert np.array_equal(base[te[2:]], shifted[te[2:]])


# --- 2.0 s smoothing ----------------------------------------------------------------------------

def test_accuracies_mod5_matches_hand_smoothing_and_differs_from_trial_rule():
  rng = np.random.default_rng(2)
  n = 20
  scores = rng.dirichlet(np.ones(5), n)
  y = np.tile(np.arange(101, 106), 4)
  trial = np.repeat([0, 1, 2, 3], [3, 7, 4, 6])           # misaligned with i % 5
  sm = scores.copy()
  for i in range(n):
    if i % 5 != 0:
      sm[i] = 0.5 * (scores[i] + scores[i - 1])
  pred = np.zeros(n, int) + 101
  _, a2 = le.accuracies(y, pred, scores, trial, "mod5")
  assert np.isclose(a2, (np.asarray(range(101, 106))[sm.argmax(1)] == y).mean())
  _, a2t = le.accuracies(y, pred, scores, trial, "trial")
  sm_t = scores.copy()
  for i in range(n):
    if i > 0 and trial[i] == trial[i - 1]:
      sm_t[i] = 0.5 * (scores[i] + scores[i - 1])
  assert np.isclose(a2t, (np.asarray(range(101, 106))[sm_t.argmax(1)] == y).mean())


def test_both_benchmarks_request_the_mod5_rule(monkeypatch):
  seen = []
  orig_g = gate.accuracies
  monkeypatch.setattr(gate, "accuracies", lambda *a, **k: (seen.append(a[-1]), orig_g(*a, **k))[1])
  gate.evaluate_subject(_tiny_ds(), 1, [0], sets=["Base"])
  orig_n = gnn.accuracies
  monkeypatch.setattr(gnn, "accuracies", lambda *a, **k: (seen.append(a[-1]), orig_n(*a, **k))[1])
  gnn.evaluate_variant(_tiny_ds(), "nodes+F", 0, 1, torch.device("cpu"))
  assert seen == ["mod5", "mod5"]


# --- cache: stale guard, legacy arrays untouched --------------------------------------------------

def _digests(d, skip="graph_dataset.npz"):
  return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
          for p in sorted(d.iterdir()) if p.name != skip}


def test_stale_cache_guard_rebuild_and_legacy_arrays_never_written(tmp_path):
  d = write_subject(tmp_path, "S03", n_trials=6)
  before = _digests(d)
  rep = tmp_path / "rep"
  args = ["--data-root", str(tmp_path), "--reports-dir", str(rep), "--subjects", "S03"]
  assert bgd.main(args) == 0
  assert _digests(d) == before
  cache = d / "graph_dataset.npz"

  def tamper(**ch):
    z = dict(np.load(cache))
    z.update(ch)
    np.savez(cache, **z)

  # a valid cache is reused without --rebuild, replaced with it
  tamper(node=np.zeros_like(np.load(cache)["node"]))
  assert bgd.main(args) == 0
  assert np.allclose(gd.load_graph_dataset("S03", tmp_path).node, 0)
  assert bgd.main(args + ["--rebuild"]) == 0
  assert not np.allclose(gd.load_graph_dataset("S03", tmp_path).node, 0)
  # a stale cache is refused by the loader and rebuilt by the builder
  tamper(code_hash=np.array("f" * 64), node=np.zeros_like(np.load(cache)["node"]))
  with pytest.raises(gd.StaleGraphDataset):
    gd.load_graph_dataset("S03", tmp_path)
  assert bgd.main(args) == 0
  assert not np.allclose(gd.load_graph_dataset("S03", tmp_path).node, 0)
  assert _digests(d) == before
  with pytest.raises(ValueError):
    gd.save_graph_dataset(d / "y_labels.npy", {}, FS, "h", [], False)


def test_fingerprint_depends_on_fs_thresholds_and_feature_source(tmp_path, monkeypatch):
  h = gd.code_fingerprint(250.0)
  assert h == gd.code_fingerprint(250.0)
  assert h != gd.code_fingerprint(256.0)
  assert h != gd.code_fingerprint(250.0, channel_fail_fraction=0.4)
  th = dict(gd.GATE_THRESHOLDS)
  key = sorted(th)[0]
  th[key] = th[key] * 2 + 1
  assert h != gd.code_fingerprint(250.0, thresholds=th)
  src = tmp_path / "fake_features.py"
  src.write_text("# other code\n")
  monkeypatch.setattr(cgf, "__file__", str(src))
  assert h != gd.code_fingerprint(250.0)


# --- graph inputs: standardizer ----------------------------------------------------------------------

def _inputs(n=30, C=4, seed=0):
  rng = np.random.default_rng(seed)
  return gi.GraphInputs(rng.normal(3, 2, (n, C, 10)).astype(np.float32), rng.uniform(size=(n, C, C, 5)).astype(np.float32),
                        rng.normal(-1, 4, (n, 5)).astype(np.float32))


def test_standardizer_uses_training_rows_only():
  inp = _inputs()
  tr = np.arange(0, 20)
  te = np.arange(20, 30)
  inp.node[te] += 1e4
  inp.edge[te] += 50
  inp.graph[te] -= 1e3
  st = gi.fit_standardizer(inp, tr)
  assert np.allclose(st.node_mean, inp.node[tr].mean(0), atol=1e-4)
  assert np.allclose(st.node_std, inp.node[tr].std(0), rtol=1e-4)
  assert np.allclose(st.graph_mean, inp.graph[tr].mean(0), atol=1e-4)
  a, b = gi.standardize_fold(inp, tr, te)
  assert np.allclose(a.node.mean(0), 0, atol=1e-4) and np.allclose(a.node.std(0), 1, atol=1e-4)
  assert np.allclose(a.graph.mean(0), 0, atol=1e-4)
  assert b.node.mean() > 100                # the shifted test rows stay shifted
  assert np.allclose(b.node, (inp.node[te] - inp.node[tr].mean(0)) / inp.node[tr].std(0), rtol=1e-4, atol=1e-4)


# --- R1 in the GNN benchmark, seeds, determinism ------------------------------------------------------

def test_gnn_r1_no_shared_trial_and_fold_seeds(monkeypatch):
  calls = _spy_splits(monkeypatch, gnn)
  seeds = []
  orig = gnn.train_fold

  def spy(inp, yi, seed, *a, **k):
    seeds.append(seed)
    return orig(inp, yi, seed, *a, **k)
  monkeypatch.setattr(gnn, "train_fold", spy)
  ds = _tiny_ds(n_trials=15)
  for r in range(3):
    gnn.evaluate_variant(ds, "nodes+F", r, 1, torch.device("cpu"))
  assert [c[1] for c in calls] == [42, 43, 44]
  _no_shared(calls)
  assert seeds == [1000 * r + f for r in range(3) for f in range(5)]


def test_gnn_evaluate_variant_is_deterministic():
  ds = _tiny_ds(n_trials=15, signal=0.5)
  a = gnn.evaluate_variant(ds, "nodes+coh+F", 1, 2, torch.device("cpu"))
  b = gnn.evaluate_variant(ds, "nodes+coh+F", 1, 2, torch.device("cpu"))
  assert a == b
  c = gnn.evaluate_variant(ds, "nodes+coh+F", 2, 2, torch.device("cpu"))
  assert {k: c[k] for k in ("repeat",)} != {k: a[k] for k in ("repeat",)}


def test_gnn_standardizer_fitted_on_train_rows_in_the_benchmark(monkeypatch):
  fitted = []
  orig = gi.fit_standardizer

  def spy(inputs, idx):
    fitted.append((len(inputs), np.asarray(idx)))
    return orig(inputs, idx)
  monkeypatch.setattr(gi, "fit_standardizer", spy)
  calls = _spy_splits(monkeypatch, gnn)
  gnn.evaluate_variant(_tiny_ds(n_trials=15), "nodes+F", 0, 1, torch.device("cpu"))
  splits = calls[0][2]
  assert len(fitted) == 5
  for (n, idx), (tr, te) in zip(fitted, splits):
    assert np.array_equal(np.sort(idx), np.sort(tr)) and not set(idx) & set(te)


# --- ConnectivityGNN -------------------------------------------------------------------------------

def test_parameter_counts_exact():
  assert count_parameters(ConnectivityGNN(7, 10, 0, 5)) == 5150
  assert count_parameters(ConnectivityGNN(7, 10, 5, 5)) == 5534
  m = ConnectivityGNN(7, 10, 5, 5)
  for layer in m.layers:
    assert layer.w_self.bias is None and layer.w_msg.bias is None and layer.gate.bias is not None


def test_embedding_init_is_normal_0_0p1():
  torch.manual_seed(0)
  e = ConnectivityGNN(400, 10, 0, 0, hidden=64).embed.detach().numpy()
  assert abs(e.mean()) < 0.005 and 0.095 < e.std() < 0.105


def _sig(x):
  return 1 / (1 + np.exp(-x))


def _np_layer(layer, h, e):
  W = lambda lin: lin.weight.detach().numpy()
  B, N, H = h.shape
  msg = h @ W(layer.w_msg).T
  if layer.gate is not None:
    g = _sig(e @ W(layer.gate).T + layer.gate.bias.detach().numpy())     # (B, N, N, H) [b, i, j]
  else:
    g = np.ones((B, N, N, H))
  agg = np.zeros_like(h)
  for i in range(N):
    for j in range(N):
      if i != j:
        agg[:, i] += g[:, i, j] * msg[:, j]
  agg /= (N - 1)
  u = h @ W(layer.w_self).T + agg
  u = np.where(u > 0, u, np.expm1(np.minimum(u, 0)))                     # ELU
  z = h + u
  mu, var = z.mean(-1, keepdims=True), z.var(-1, keepdims=True)
  return (z - mu) / np.sqrt(var + layer.norm.eps) * layer.norm.weight.detach().numpy() + layer.norm.bias.detach().numpy()


def test_edge_gated_layer_matches_numpy_reference_including_no_self_messages():
  torch.manual_seed(1)
  layer = EdgeGatedLayer(4, n_edge_feats=3, dropout=0.0).eval()
  rng = np.random.default_rng(1)
  h = rng.normal(size=(2, 3, 4)).astype(np.float32)
  e = rng.normal(size=(2, 3, 3, 3)).astype(np.float32)
  out = layer(torch.from_numpy(h), torch.from_numpy(e)).detach().numpy()
  assert np.allclose(out, _np_layer(layer, h.astype(np.float64), e.astype(np.float64)), atol=1e-5)
  layer0 = EdgeGatedLayer(4, n_edge_feats=0, dropout=0.0).eval()
  out0 = layer0(torch.from_numpy(h)).detach().numpy()
  assert np.allclose(out0, _np_layer(layer0, h.astype(np.float64), None), atol=1e-5)


def test_full_forward_matches_numpy_readout_mean_max_then_graph_features():
  torch.manual_seed(2)
  m = ConnectivityGNN(4, 6, 2, 3, n_classes=5, hidden=8, n_layers=2, dropout=0.0).eval()
  rng = np.random.default_rng(2)
  x = rng.normal(size=(3, 4, 6)).astype(np.float32)
  e = rng.normal(size=(3, 4, 4, 2)).astype(np.float32)
  g = rng.normal(size=(3, 3)).astype(np.float32)
  out = m(torch.from_numpy(x), torch.from_numpy(e), torch.from_numpy(g)).detach().numpy()
  enc = m.encoder[0]
  u = x.astype(np.float64) @ enc.weight.detach().numpy().T + enc.bias.detach().numpy()
  h = np.where(u > 0, u, np.expm1(np.minimum(u, 0))) + m.embed.detach().numpy()
  for layer in m.layers:
    h = _np_layer(layer, h, e.astype(np.float64))
  z = np.concatenate([h.mean(1), h.max(1), g], axis=1)
  exp = z @ m.head.weight.detach().numpy().T + m.head.bias.detach().numpy()
  assert out.shape == (3, 5) and np.allclose(out, exp, atol=1e-4)
