"""P15 builder tests (deep-learning): graph inputs, standardizer, ConnectivityGNN, benchmark_gnn.

Synthetic data only (never reads generated or git-ignored files). Parameter counts are the exact R-8 figures.
"""

import numpy as np
import pandas as pd
import pytest
import torch

from scripts.connectivity.graph_modeling import benchmark_gnn as bg
from scripts.connectivity.graph_modeling import build_graph_dataset as bgd
from src.features.connectivity import graph_dataset as gd
from src.features.connectivity import graph_inputs as gi
from src.models.graph.connectivity_gnn import ConnectivityGNN, EdgeGatedLayer, count_parameters
from src.preprocessing.dataset import cv_utils as cu
from tests.p05_synth import write_subject

FS = 250.0


def _ds(n_trials=20, seed=0):
  return bg.synthetic_dataset(seed, n_trials)


# --- parameter counts and shapes (R-8) -----------------------------------------------------------

def test_exact_parameter_counts_r8():
  assert count_parameters(ConnectivityGNN(7, 10, 0, 5)) == 5150      # nodes+F
  assert count_parameters(ConnectivityGNN(7, 10, 5, 5)) == 5534      # nodes+coh+F


def test_counts_follow_the_layer_choices():
  """Per layer: 2 bias-free 32x32 Linear (2048) + LayerNorm (64) [+ gate Linear(5, 32) = 192]; the bias terms of W_self
  and W_msg would add 128 (the literal default-bias reading: 5,278 / 5,662, B004)."""
  base = 10 * 32 + 32 + 7 * 32 + 2 * (2 * 32 * 32 + 64) + (64 + 5) * 5 + 5
  assert base == 5150
  assert count_parameters(ConnectivityGNN(7, 10, 5, 5)) - count_parameters(ConnectivityGNN(7, 10, 0, 5)) == 2 * (5 * 32 + 32)
  m = ConnectivityGNN(7, 10, 5, 5)
  assert m.layers[0].w_self.bias is None and m.layers[0].w_msg.bias is None


def test_output_shapes_and_no_hardcoded_channel_count():
  for C in (7, 8, 5):
    m = ConnectivityGNN(C, 10, 15, 5)
    out = m(torch.randn(4, C, 10), torch.randn(4, C, C, 15), torch.randn(4, 5))
    assert out.shape == (4, 5)
  assert ConnectivityGNN(7, 10)(torch.randn(3, 7, 10)).shape == (3, 5)


def test_channel_embedding_init_std():
  m = ConnectivityGNN(64, 10, hidden=256)
  assert abs(m.embed.std().item() - 0.1) < 0.01 and abs(m.embed.mean().item()) < 0.01


# --- edge gating ---------------------------------------------------------------------------------

def _ref_layer(layer, h, gate_value):
  """numpy reference: LN(h + ELU(W_self h + mean_{j != i} gate * W_msg h_j))."""
  W_s, W_m = layer.w_self.weight.detach().numpy(), layer.w_msg.weight.detach().numpy()
  h = h.numpy()
  msg = h @ W_m.T
  n = h.shape[1]
  agg = (msg.sum(axis=1, keepdims=True) - msg) * gate_value / (n - 1)
  z = h @ W_s.T + agg
  z = np.where(z > 0, z, np.expm1(z))
  u = h + z
  mu, var = u.mean(-1, keepdims=True), u.var(-1, keepdims=True)
  return (u - mu) / np.sqrt(var + layer.norm.eps) * layer.norm.weight.detach().numpy() + layer.norm.bias.detach().numpy()


def test_edge_gate_scales_messages_by_sigmoid_and_excludes_self():
  torch.manual_seed(0)
  layer = EdgeGatedLayer(8, 3, dropout=0.0).eval()
  with torch.no_grad():
    layer.gate.weight.zero_()
    layer.gate.bias.fill_(0.0)                 # gate = sigmoid(0) = 0.5 whatever the edge input
  h = torch.randn(2, 6, 8)
  for e in (torch.zeros(2, 6, 6, 3), torch.ones(2, 6, 6, 3)):
    np.testing.assert_allclose(layer(h, e).detach().numpy(), _ref_layer(layer, h, 0.5), atol=1e-5)
  with torch.no_grad():
    layer.gate.bias.fill_(-30.0)               # gate ~ 0: no messages
  closed = layer(h, torch.zeros(2, 6, 6, 3)).detach().numpy()
  np.testing.assert_allclose(closed, _ref_layer(layer, h, 0.0), atol=1e-5)
  with torch.no_grad():
    layer.gate.bias.fill_(30.0)                # gate ~ 1 equals the ungated layer
  ungated = EdgeGatedLayer(8, 0, dropout=0.0).eval()
  ungated.load_state_dict({k: v for k, v in layer.state_dict().items() if not k.startswith("gate")})
  np.testing.assert_allclose(layer(h, torch.zeros(2, 6, 6, 3)).detach().numpy(), ungated(h).detach().numpy(), atol=1e-5)


def test_edge_input_changes_output_only_through_the_gate():
  torch.manual_seed(1)
  m = ConnectivityGNN(7, 10, 5, 0).eval()
  x = torch.randn(2, 7, 10)
  e1, e2 = torch.randn(2, 7, 7, 5), torch.randn(2, 7, 7, 5)
  assert not torch.allclose(m(x, e1), m(x, e2))
  with pytest.raises(ValueError):
    m(x)                                       # a gated model needs edges


def test_gate_direction_is_target_row_i_source_column_j():
  """e[b, i, j] gates the message from j into i: opening only (i=0, j=1) changes node 0 and no other node."""
  torch.manual_seed(2)
  layer = EdgeGatedLayer(8, 1, dropout=0.0).eval()
  with torch.no_grad():
    layer.gate.weight.fill_(40.0)
    layer.gate.bias.fill_(-20.0)               # e = 0 -> closed, e = 1 -> open
  h = torch.randn(1, 5, 8)
  e = torch.zeros(1, 5, 5, 1)
  base = layer(h, e)
  e[0, 0, 1, 0] = 1.0
  out = layer(h, e)
  changed = (out - base).abs().amax(dim=-1)[0] > 1e-6
  assert changed.tolist() == [True, False, False, False, False]


# --- variants and standardizer (R2) --------------------------------------------------------------

def test_variant_validation_and_dims():
  ds = _ds()
  for bad in ("coh", "F+nodes", "nodes+bogus", "nodes+coh+coh", "Nodes", ""):
    with pytest.raises(ValueError):
      gi.parse_variant(bad)
  assert gi.parse_variant("nodes+coh+phase+F") == (True, True, True)
  a = gi.build_inputs(ds, "nodes")
  assert a.node.shape == (100, 7, 10) and a.edge is None and a.graph is None
  b = gi.build_inputs(ds, "nodes+F")
  assert b.edge is None and b.graph.shape == (100, 5)
  c = gi.build_inputs(ds, "nodes+coh+F")
  assert c.edge.shape == (100, 7, 7, 5)
  d = gi.build_inputs(ds, "nodes+coh+phase+F")
  assert d.edge.shape == (100, 7, 7, 15)
  np.testing.assert_array_equal(d.edge[..., :5], c.edge)
  # R6: phase channel layout is band-major then (cos, sin): ds.edge_phase[n,i,j,b,s] -> edge[n,i,j,5+2b+s]
  assert d.edge[3, 1, 2, 5 + 2 * 4 + 1] == np.float32(ds.edge_phase[3, 1, 2, 4, 1])
  assert gi.variant_name(True, False, True) == "nodes+coh+F"


def test_standardizer_uses_train_rows_only_and_catches_the_leak():
  ds = _ds()
  inp = gi.build_inputs(ds, "nodes+coh+F")
  tr, te = np.arange(0, 80), np.arange(80, 100)
  inp.node[te[0]] = 1e6                           # planted test-fold outlier
  inp.graph[te[0]] = 1e6
  st = gi.fit_standardizer(inp, tr)
  np.testing.assert_allclose(st.node_mean, inp.node[tr].mean(0), rtol=1e-5)
  np.testing.assert_allclose(st.node_std, inp.node[tr].std(0), rtol=1e-5)
  np.testing.assert_allclose(st.graph_mean, inp.graph[tr].mean(0), rtol=1e-5)
  a_tr, a_te = gi.standardize_fold(inp, tr, te)
  inp2 = gi.build_inputs(ds, "nodes+coh+F")        # same train rows, different test rows
  b_tr, _ = gi.standardize_fold(inp2, tr, te)
  np.testing.assert_array_equal(a_tr.node, b_tr.node)
  np.testing.assert_allclose(a_tr.node.mean(0), 0, atol=1e-4)
  all_rows = gi.fit_standardizer(inp, np.arange(100))   # the historical bug: fit on everything
  assert not np.allclose(all_rows.node_mean, st.node_mean)
  assert a_te.node.max() > 1e4                      # the outlier stays an outlier: nothing was fitted on it


def test_constant_columns_are_left_unscaled():
  ds = _ds()
  inp = gi.build_inputs(ds, "nodes+coh")
  inp.edge[:, 2, 2, :] = 1.0                        # unit diagonal
  tr, _ = gi.standardize_fold(inp, np.arange(50), np.arange(50, 100))
  assert np.isfinite(tr.edge).all() and np.allclose(tr.edge[:, 2, 2, :], 0.0)


# --- training: determinism, no shared trials, train accuracy -------------------------------------

def test_splits_of_every_repeat_share_no_trial_ids():
  ds = _ds()
  for r in range(3):
    cu.assert_no_shared_trials(cu.make_splits("grouped", ds.y, ds.trial_ids, 42 + r), ds.trial_ids)


def test_evaluate_variant_is_deterministic_and_seeded_by_repeat():
  ds = _ds(n_trials=10)
  dev = torch.device("cpu")
  a = bg.evaluate_variant(ds, "nodes+coh+F", 0, 2, dev)
  b = bg.evaluate_variant(ds, "nodes+coh+F", 0, 2, dev)
  assert a == b and a["n_params"] == 5534
  c = bg.evaluate_variant(ds, "nodes+coh+F", 1, 2, dev)
  assert (c["acc_1s"], c["train_acc"]) != (a["acc_1s"], a["train_acc"])


def test_fold_models_are_seeded_per_fold():
  """Same seed -> identical weights after training; the seed 1000 r + k changes them (PF-28)."""
  ds = _ds(n_trials=20)
  inp = gi.build_inputs(ds, "nodes+F")
  tr, _ = gi.standardize_fold(inp, np.arange(60), np.arange(60, 100))
  dev = torch.device("cpu")
  m1, m2, m3 = (bg.train_fold(tr, ds.y_index[:60], s, dev, epochs=2) for s in (1000, 1000, 1001))
  assert all(torch.equal(p, q) for p, q in zip(m1.parameters(), m2.parameters()))
  assert not all(torch.equal(p, q) for p, q in zip(m1.parameters(), m3.parameters()))


def test_planted_signal_is_learned_and_train_accuracy_reported():
  ds = _ds(n_trials=20)
  r = bg.evaluate_variant(ds, "nodes+F", 0, 40, torch.device("cpu"))
  assert r["acc_1s"] > 80 and r["train_acc"] >= r["acc_1s"] - 5


def test_diagnosis_hints():
  assert "UNDERFITTING" in bg.diagnosis(50.0, 45.0)
  assert "OVERFITTING" in bg.diagnosis(95.0, 70.0)
  assert "no strong gap" in bg.diagnosis(85.0, 80.0)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA device")
def test_model_runs_on_cuda():
  m = ConnectivityGNN(7, 10, 5, 5).cuda()
  assert m(torch.randn(2, 7, 10).cuda(), torch.randn(2, 7, 7, 5).cuda(), torch.randn(2, 5).cuda()).shape == (2, 5)


# --- smoke run -----------------------------------------------------------------------------------

def test_smoke_on_synthetic_tree_with_and_without_gate_csv(tmp_path, capsys):
  write_subject(tmp_path, "S03", n_trials=8)
  assert bgd.main(["--data-root", str(tmp_path), "--reports-dir", str(tmp_path / "rep")]) == 0
  args = ["--smoke-test", "--data-root", str(tmp_path), "--reports-dir", str(tmp_path / "rep")]
  assert bg.main(args) == 0
  assert "gate rows" not in capsys.readouterr().out
  out = tmp_path / "rep" / "gnn_benchmark_smoke.csv"
  df = pd.read_csv(out)
  assert list(df.columns) == bg.COLUMNS and len(df) == 2 and set(df.variant) == set(bg.VARIANTS) and set(df.subject) == {"S03"}
  assert not (tmp_path / "rep" / "gnn_benchmark.csv").exists()
  meta = out.with_suffix(".meta.txt").read_text()
  assert "SMOKE" in meta and "5150" in meta and "5534" in meta and "i%5" in meta
  pd.DataFrame([{"subject": "S03", "set": s, "k_select": 0, "repeat": 0, "dim": 1, "acc_1s": 50.0, "acc_2s": 55.0}
                for s in ("N", "F", "Base", "Base+Ec")]).to_csv(tmp_path / "rep" / "connectivity_gate_benchmark.csv", index=False)
  assert bg.main(args) == 0
  assert "gate rows" in capsys.readouterr().out


def test_smoke_without_cache_uses_in_memory_dataset(tmp_path):
  assert bg.main(["--smoke-test", "--data-root", str(tmp_path / "none"), "--reports-dir", str(tmp_path / "rep")]) == 0
  assert (tmp_path / "rep" / "gnn_benchmark_smoke.csv").is_file()
  assert bg.main(["--data-root", str(tmp_path / "none"), "--reports-dir", str(tmp_path / "rep")]) == 1   # full run needs data


def test_cli_rejects_a_variant_that_does_not_start_with_nodes(tmp_path):
  with pytest.raises(ValueError):
    bg.main(["--smoke-test", "--variants", "coh+F", "--data-root", str(tmp_path), "--reports-dir", str(tmp_path)])
