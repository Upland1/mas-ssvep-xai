"""P23 independent known-answer tests (synthetic-tester; not the builders' tests).

Era C graph features are checked against a separate numpy/scipy computation (not the module's own helpers); the GNN LOSO harness
against sentinels, permutations and hand-computed expectations. Synthetic only, CPU, one torch thread, no real data.
"""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import scipy.signal as ss
import torch

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_loso_warmup as WU
from scripts.connectivity.graph_modeling import benchmark_gnn_loso as G
from src.features.connectivity import graph_features_subject as gfs
from src.io.subject_data import load_subject
from tests.p16_synth import write_built_subject

FS = 256.0
T = 256
NAMES7 = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
TARGETS = [24.0, 20.0, 15.0, 10.9091, 8.5714]
CONFIG = G.ROOT / "configs" / "pipeline_config.yaml"
SPEC_P = {"variant": "nodes+coh+F", "norm": "pooled", "method": "gnn_nodes+coh+F"}
SPEC_S = {"variant": "nodes+coh+F", "norm": "subject", "method": "gnn_nodes+coh+F_subjnorm"}


@pytest.fixture(autouse=True)
def one_thread():
  old = torch.get_num_threads()
  torch.set_num_threads(1)
  yield
  torch.set_num_threads(old)


# --- independent reference computation of the P15 features ----------------------------------------------------------------

def _bins(freqs, f0):
  sel = np.flatnonzero(np.abs(freqs - f0) <= 1.0 + 1e-9)
  return sel if len(sel) else np.array([int(np.argmin(np.abs(freqs - f0)))])


def ref_node(w, fs):
  """w (C, T): log10 mean power of the mean-removed periodic-Hann FFT in f +- 1 Hz, harmonic-major."""
  n = w.shape[-1]
  hann = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
  P = np.abs(np.fft.rfft((w - w.mean(-1, keepdims=True)) * hann, axis=-1)) ** 2
  fr = np.arange(n // 2 + 1) * fs / n
  return np.log10(np.stack([P[:, _bins(fr, h * f)].mean(-1) for h in (1, 2) for f in TARGETS], -1) + 1e-12)


def ref_coh(w, fs):
  """Edge coherence via scipy.signal.coherence (nperseg 128, overlap 64), band mean."""
  C = w.shape[0]
  out = np.zeros((C, C, 5))
  fr = np.arange(65) * fs / 128
  for i in range(C):
    for j in range(C):
      if i == j:
        out[i, j] = 1.0
        continue
      _, c = ss.coherence(w[i], w[j], fs=fs, window="hann", nperseg=128, noverlap=64)
      out[i, j] = [c[_bins(fr, f)].mean() for f in TARGETS]
  return out


def ref_phase(w, fs):
  n = w.shape[-1]
  hann = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
  X = np.fft.rfft((w - w.mean(-1, keepdims=True)) * hann, axis=-1)
  fr = np.arange(n // 2 + 1) * fs / n
  C = w.shape[0]
  out = np.zeros((C, C, 5, 2))
  for k, f in enumerate(TARGETS):
    b = _bins(fr, f)
    for i in range(C):
      for j in range(C):
        a = np.angle(np.sum(X[i, b] * np.conj(X[j, b])))
        out[i, j, k] = [np.cos(a), np.sin(a)]
  return out


def fake_d(X, fs=FS, **kw):
  n, C, _ = X.shape
  d = dict(subject="S99", built=True, fs=fs, fs_source="meta", filter_mode="continuous", X=X, y=np.full(n, 103),
           trial_ids=np.arange(n) // 3, offsets=np.arange(n) % 3, cv_groups=np.arange(n) // 3,
           channel_names=[f"c{i}" for i in range(C)], channels_dropped=[], trial_ids_approximate=False,
           bands={"fbcca": np.random.default_rng(1).normal(size=(n, 3, C, T))})
  d.update(kw)
  return d


def test_features_equal_independent_numpy_reference_at_fs256():
  rng = np.random.default_rng(10)
  X = rng.normal(size=(4, 4, T))
  t = np.arange(T) / FS
  X[:, 1] += 2 * np.sin(2 * np.pi * 20 * t + 0.4)             # structure so coherences/phases are not just noise
  X[:, 2] += 1.5 * np.sin(2 * np.pi * 20 * t - 0.3)
  ds = gfs.graph_features_for_subject(fake_d(X), None, chunk=3)
  assert ds.fs == 256.0
  for r in range(4):
    np.testing.assert_allclose(ds.node[r], ref_node(X[r], FS), atol=1e-8)
    np.testing.assert_allclose(ds.edge_coh[r], ref_coh(X[r], FS), atol=1e-8)
    np.testing.assert_allclose(ds.edge_phase[r], ref_phase(X[r], FS), atol=1e-7)


def test_features_would_differ_at_fs250_so_the_reference_pins_the_sampling_rate():
  X = np.random.default_rng(11).normal(size=(2, 3, T))
  X[:, 0] += 3 * np.sin(2 * np.pi * 23 * np.arange(T) / FS)
  ds = gfs.graph_features_for_subject(fake_d(X), None)
  assert np.abs(ds.node[0] - ref_node(X[0], 250.0)).max() > 0.2          # a 250 Hz computation is a different number
  np.testing.assert_allclose(ds.node[0], ref_node(X[0], FS), atol=1e-8)


def test_planted_tone_band_columns_and_harmonic():
  t = np.arange(T) / FS
  rng = np.random.default_rng(12)
  X = 0.05 * rng.normal(size=(3, 5, T))
  X[:, 3] += np.sin(2 * np.pi * 20 * t)                       # fundamental of target 2 (col 1) on channel 3
  X[:, 1] += np.sin(2 * np.pi * 48 * t)                       # 2nd harmonic of 24 Hz (col 5 + 0) on channel 1
  node = gfs.graph_features_for_subject(fake_d(X), None).node
  for r in range(3):
    assert node[r, :, 1].argmax() == 3 and node[r, 3, 1] - np.delete(node[r, :, 1], 3).max() > 2
    assert node[r, 3].argmax() == 1                              # that channel's strongest column is the 20 Hz one
    assert node[r, :, 5].argmax() == 1 and node[r, 1, 5] - np.delete(node[r, :, 5], 1).max() > 2


def test_coupled_pair_coherence_and_phase_lag_only_on_that_edge():
  t = np.arange(T) / FS
  rng = np.random.default_rng(13)
  lag = 0.7
  X = rng.normal(size=(6, 4, T)) * 0.3
  base = np.sin(2 * np.pi * 15 * t)
  X[:, 0] += base
  X[:, 2] += np.sin(2 * np.pi * 15 * t - lag)                 # channel 2 lags channel 0 by `lag` rad at 15 Hz (col 2)
  ds = gfs.graph_features_for_subject(fake_d(X), None)
  assert (ds.edge_coh[:, 0, 2, 2] > 0.95).all() and (ds.edge_coh[:, 2, 0, 2] > 0.95).all()
  other = np.delete(ds.edge_coh[:, :, :, 2].reshape(6, -1), [0 * 4 + 2, 2 * 4 + 0, 0, 5, 10, 15], axis=1)
  assert other.max() < 0.8
  assert (ds.edge_coh[:, 0, 2, [0, 1, 3, 4]] < 0.8).all()    # other bands carry no coupling
  # phase of X_0 conj(X_2) = +lag
  np.testing.assert_allclose(ds.edge_phase[:, 0, 2, 2, 0], np.cos(lag), atol=0.12)
  np.testing.assert_allclose(ds.edge_phase[:, 0, 2, 2, 1], np.sin(lag), atol=0.12)
  np.testing.assert_allclose(ds.edge_phase[:, 2, 0, 2, 1], -np.sin(lag), atol=0.12)
  for r in range(6):                                              # and exactly my independent angle computation
    np.testing.assert_allclose(ds.edge_phase[r], ref_phase(X[r], FS), atol=1e-7)


def test_upper_tri_layout_flat_columns_follow_triu_pair_major_order():
  from src.features.connectivity.connectivity_graph_features import upper_tri_flat
  C = 5
  a = np.zeros((1, C, C, 5, 2))
  for i in range(C):
    for j in range(C):
      for k in range(5):
        for c in range(2):
          a[0, i, j, k, c] = 1000 * i + 100 * j + 10 * k + c
  flat = upper_tri_flat(a)[0]
  pairs = [(i, j) for i in range(C) for j in range(i + 1, C)]
  assert flat.size == len(pairs) * 10
  for p, (i, j) in enumerate(pairs):
    for k in range(5):
      for c in range(2):
        assert flat[(p * 5 + k) * 2 + c] == 1000 * i + 100 * j + 10 * k + c


def test_rows_align_with_load_subject_and_match_the_reference_per_row(tmp_path):
  root = tmp_path / "w1_s0.25"
  write_built_subject(root, "S01", n_trials=10, seed=21)
  d = load_subject(root / "S01", bands=("fbcca",), channels=NAMES7)
  assert d["fs"] == 256.0
  ds = gfs.graph_features_for_subject(d, NAMES7)
  n = len(d["y"])
  assert ds.node.shape[0] == ds.edge_coh.shape[0] == ds.edge_phase.shape[0] == ds.X_fbcca.shape[0] == n
  assert np.array_equal(ds.y, d["y"]) and np.array_equal(ds.trial_ids, d["trial_ids"]) and np.array_equal(ds.offsets, d["offsets"])
  # rows are sorted by (trial, offset) and the features follow that order (R8)
  assert np.array_equal(np.lexsort((d["offsets"], d["trial_ids"])), np.arange(n))
  for r in (0, n // 2, n - 1):
    np.testing.assert_allclose(ds.node[r], ref_node(d["X"][r], 256.0), atol=1e-8)
    np.testing.assert_allclose(ds.edge_phase[r], ref_phase(d["X"][r], 256.0), atol=1e-7)
  # planted stimulus tone: the FBCCA argmax recovers the label above chance (5 classes)
  assert np.mean(ds.X_fbcca.argmax(1) == (d["y"] - 101)) > 0.5


# --- harness helpers -------------------------------------------------------------------------------------------------------

def make_args(**kw):
  a = G.build_parser().parse_args([])
  a.max_epochs, a.patience, a.seeds, a.threads, a.channels = 4, 2, 2, 1, "synthetic"
  a.variants, a.norm, a.protocol = list(G.VARIANTS), ["pooled"], "loso"
  for k, v in kw.items():
    setattr(a, k, v)
  return a


def world(protocol="loso", trials=5, wins=3):
  loaded, datasets = G.synthetic_cohort(4, trials, wins)
  P = G.assemble(loaded, datasets, G.VARIANTS)
  ctx = G.make_ctx(P, loaded, Path("synthetic"), CONFIG)
  if protocol == "within":
    G.add_within_splits(ctx, P, 5)
  return P, ctx


def sentinel(P, k, val=500.0):
  Q = copy.deepcopy(P)
  Q.pop("_subjnorm", None)
  rows = np.flatnonzero(Q["subj"] == k)
  for inp in Q["inputs"].values():
    for arr in (inp.node, inp.edge, inp.graph):
      if arr is not None:
        arr[rows] += val
  return Q


def zs(a, rows):
  mu, sd = a[rows].mean(0), a[rows].std(0)
  return (a - mu) / np.where(sd < 1e-6, 1.0, sd)


# --- R2: pooled ------------------------------------------------------------------------------------------------------------

def test_pooled_training_arrays_are_my_own_zscore_of_training_rows_and_ignore_a_heldout_sentinel():
  P, ctx = world()
  k = 2
  tr, te = L.loso_split(P["subj"], k)
  inp = P["inputs"]["nodes+coh+F"]
  a, _ = G.fold_inputs(P, SPEC_P, tr, te)
  np.testing.assert_allclose(a.node, zs(inp.node, tr)[tr], atol=1e-4)
  np.testing.assert_allclose(a.edge, zs(inp.edge, tr)[tr], atol=1e-4)
  np.testing.assert_allclose(a.graph, zs(inp.graph, tr)[tr], atol=1e-4)
  Q = sentinel(P, k)
  b, _ = G.fold_inputs(Q, SPEC_P, tr, te)
  assert np.array_equal(a.node, b.node) and np.array_equal(a.edge, b.edge) and np.array_equal(a.graph, b.graph)
  args = make_args()
  r1 = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], G.fold_inputs(P, SPEC_P, tr, te)[1], args, "cpu")
  r2 = G.gnn_fold(b, P["yi"][tr], P["groups"][tr], G.fold_inputs(Q, SPEC_P, tr, te)[1], args, "cpu")
  for x, y in zip(r1["runs"], r2["runs"]):
    for kk, v in x["model"].state_dict().items():
      assert torch.equal(v, y["model"].state_dict()[kk])
  assert not np.array_equal(r1["proba"], r2["proba"])                  # the sentinel does reach the held-out predictions


# --- PF-35: subject normalization ------------------------------------------------------------------------------------------

def test_subjnorm_uses_each_subjects_own_statistics_and_no_labels():
  P, ctx = world()
  inp = P["inputs"]["nodes+coh+F"]
  k = 1
  tr, te = L.loso_split(P["subj"], k)
  a_tr, a_te = G.fold_inputs(P, SPEC_S, tr, te)
  for s in range(4):                                                  # my own per-subject z-score of every training subject
    rows = np.flatnonzero(P["subj"] == s)
    ref = zs(inp.node, rows)[rows]
    got = a_te.node if s == k else a_tr.node[P["subj"][tr] == s]
    np.testing.assert_allclose(got, ref, atol=1e-4)
  # permuting the held-out labels changes nothing in inputs or probabilities
  Q = copy.deepcopy(P)
  rows = np.flatnonzero(Q["subj"] == k)
  perm = np.random.default_rng(3).permutation(len(rows))
  Q["y"][rows], Q["yi"][rows] = P["y"][rows][perm], P["yi"][rows][perm]
  assert not np.array_equal(P["yi"], Q["yi"])
  p1, _ = G.run_fold(SPEC_S, P, k, None, ctx, make_args(), "cpu")
  p2, _ = G.run_fold(SPEC_S, Q, k, None, ctx, make_args(), "cpu")
  assert np.array_equal(p1["proba"], p2["proba"]) and np.array_equal(p1["proba_seed"], p2["proba_seed"])
  # but a sentinel in the held-out subject cannot move the training subjects' normalized arrays either
  R = sentinel(P, k)
  r_tr, _ = G.fold_inputs(R, SPEC_S, tr, te)
  assert np.array_equal(r_tr.node, a_tr.node)


def test_subjnorm_is_refused_under_within_by_the_cli(capsys):
  with pytest.raises(SystemExit):
    G.main(["--protocol", "within", "--norm", "subject", "--smoke-test"])
  with pytest.raises(SystemExit):
    G.main(["--protocol", "within", "--norm", "pooled", "subject", "--smoke-test"])


# --- R1/PF-32/PF-33: validation groups, within splits ---------------------------------------------------------------------

def test_validation_excludes_heldout_subject_and_splits_by_trial_in_every_loso_fold():
  P, ctx = world(trials=6, wins=3)
  for k in range(4):
    tr, te = L.loso_split(P["subj"], k)
    a, _ = G.fold_inputs(P, SPEC_P, tr, te)
    for seed in (42, 43):
      r = G.fit_gnn(a, P["yi"][tr], P["groups"][tr], seed, "cpu", max_epochs=3, patience=2)
      g = P["groups"][tr]
      assert len(r["val_idx"]) > 0
      assert not set(P["subj"][tr][r["val_idx"]]) & {k}
      assert not set(g[r["val_idx"]]) & set(g[r["fit_idx"]])             # no trial on both sides
      assert not set(g[r["val_idx"]]) & set(P["groups"][te])
  # a window-level splitter (the bug) is caught by that same check
  from src.models.cnn import training as tr_mod
  def per_window(yi, groups, frac, seed):
    idx = np.random.default_rng(seed).permutation(len(yi))
    return np.sort(idx[int(len(yi) * frac):]), np.sort(idx[:int(len(yi) * frac)])
  orig = G.split_validation
  G.split_validation = per_window
  try:
    with pytest.raises(AssertionError):
      G.fit_gnn(a, P["yi"][tr], P["groups"][tr], 42, "cpu", max_epochs=3, patience=2)
  finally:
    G.split_validation = orig


def test_within_folds_never_split_a_trial_and_cover_each_window_once():
  P, ctx = world("within", trials=8, wins=3)
  for s, k in zip(P["subjects"], range(4)):
    rows = np.flatnonzero(P["subj"] == k)
    seen = []
    for tr, te in ctx["within_splits"][s]:
      assert not set(P["groups"][rows][tr]) & set(P["groups"][rows][te])
      assert set(P["yi"][rows][tr]) == set(range(5))
      seen += list(te)
    assert sorted(seen) == list(range(len(rows)))
  # inside run_fold, validation is also trial-grouped and inside the fold's training rows
  tr_l, te_l = ctx["within_splits"]["S02"][1]
  arrays, _ = G.run_fold(SPEC_P, P, 1, 1, ctx, make_args(protocol="within"), "cpu")
  assert len(arrays["y"]) == len(te_l) and np.array_equal(arrays["row_idx"], te_l)
  assert float(arrays["n_train"]) == len(tr_l)


# --- PF-28: seeds ----------------------------------------------------------------------------------------------------------

def test_fold_probability_is_mean_of_seed_softmax_and_rerun_is_bit_identical():
  P, ctx = world()
  tr, te = L.loso_split(P["subj"], 3)
  a, b = G.fold_inputs(P, SPEC_P, tr, te)
  args = make_args(seeds=3)
  r = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, args, "cpu")
  assert G.seeds_of(args) == [42, 43, 44]
  per = []
  for run in r["runs"]:
    with torch.no_grad():
      x = torch.from_numpy(np.ascontiguousarray(b.node, dtype=np.float32))
      e = torch.from_numpy(np.ascontiguousarray(b.edge, dtype=np.float32))
      g = torch.from_numpy(np.ascontiguousarray(b.graph, dtype=np.float32))
      per.append(torch.softmax(run["model"].eval()(x, e, g), dim=1).numpy())
  np.testing.assert_allclose(r["proba"], np.mean(per, axis=0), atol=1e-6)
  assert not np.allclose(per[0], per[1])                                  # the seeds really differ
  assert not np.allclose(r["proba"], per[-1], atol=1e-4)                   # last-seed is not the mean
  np.testing.assert_allclose(r["proba"].sum(1), 1.0, atol=1e-5)
  r2 = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, args, "cpu")
  assert np.array_equal(r["proba"], r2["proba"]) and np.array_equal(r["proba_seed"], r2["proba_seed"])


# --- PF-37: resume and refusal ---------------------------------------------------------------------------------------------

def test_resume_skips_finished_folds_and_every_config_change_is_refused(tmp_path, monkeypatch):
  P, ctx = world()
  args = make_args(variants=["nodes+coh+F"], only_test=["S01"])
  specs = G.make_specs(args.variants, ["pooled"])
  c1 = G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  assert c1 == {"run": 1, "skipped": 0}
  c2 = G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  assert c2 == {"run": 0, "skipped": 1}

  def attempt(ctx_=ctx, args_=args, dev="cpu"):
    with pytest.raises(SystemExit, match="use a new --out-dir"):
      G.run_protocol(P, ctx_, specs, args_, dev, tmp_path)

  def a_(**kw):
    return make_args(variants=["nodes+coh+F"], only_test=["S01"], **kw)

  for kw in ({"seeds": 3}, {"seed": 7}, {"val_frac": 0.0}, {"max_epochs": 5}, {"patience": 3}, {"batch_size": 16}, {"lr": 5e-4},
             {"threads": 2}, {"window": 2.0}, {"stride_sec": 0.5}, {"channels": "all"}):
    attempt(args_=a_(**kw))
  attempt(dev="cuda")
  for key, new in (("subjects", ["S01", "S02", "S03"]), ("channels", ["a"]), ("fs", 250.0), ("classes", [1, 2]),
                   ("n_windows", {**ctx["n_windows"], "S02": ctx["n_windows"]["S02"] + 1}),
                   ("build_commits", {**ctx["build_commits"], "S03": "zzz"}), ("config_hash", "0" * 64)):
    c = copy.deepcopy(ctx)
    c[key] = new
    attempt(ctx_=c)
  # code state recorded at process start: a dirty flag flip or a different head with dirty tree is refused
  st = dict(L.RUN_STATE or L.capture_run_state())
  monkeypatch.setattr(L, "RUN_STATE", {**st, "git_dirty": not st["git_dirty"]})
  attempt()
  # an untouched configuration is still accepted afterwards
  monkeypatch.setattr(L, "RUN_STATE", st)
  assert G.run_protocol(P, ctx, specs, args, "cpu", tmp_path) == {"run": 0, "skipped": 1}


def test_interrupt_then_resume_runs_only_missing_folds(tmp_path, monkeypatch):
  P, ctx = world()
  args = make_args(variants=["nodes+F"])
  specs = G.make_specs(args.variants, ["pooled"])
  real = L.save_fold
  n = {"c": 0}

  def flaky(path, arrays, cfg):
    if n["c"] == 2:
      raise KeyboardInterrupt
    n["c"] += 1
    real(path, arrays, cfg)

  monkeypatch.setattr(G.L, "save_fold", flaky)
  with pytest.raises(KeyboardInterrupt):
    G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  monkeypatch.setattr(G.L, "save_fold", real)
  assert len(list((tmp_path / "folds").glob("*.npz"))) == 2 and not list((tmp_path / "folds").glob("*.tmp"))
  assert G.run_protocol(P, ctx, specs, args, "cpu", tmp_path) == {"run": 2, "skipped": 2}


def test_fold_count_guard_incomplete_within_subject_is_left_out(tmp_path):
  P, ctx = world("within")
  args = make_args(protocol="within", variants=["nodes+F"], only_fold=0, only_test=["S01"])
  specs = G.make_specs(args.variants, ["pooled"])
  G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  full = make_args(protocol="within", variants=["nodes+F"])
  cfg = lambda sp, s, f: G.fold_config(sp, s, f, ctx, full, "cpu")
  assert G.build_outputs(tmp_path, specs, P["subjects"], P["classes"], cfg, "src, LOSO, x", full) == {}
  with pytest.raises(ValueError):                                             # pooling folds that miss rows is refused
    G.assemble_within([{"row_idx": np.array([0, 1]), "y": np.zeros(2), "trial_id": np.zeros(2), "offset": np.zeros(2),
                        "proba": np.zeros((2, 5)), "proba_seed": np.zeros((1, 2, 5))},
                       {"row_idx": np.array([3]), "y": np.zeros(1), "trial_id": np.zeros(1), "offset": np.zeros(1),
                        "proba": np.zeros((1, 5)), "proba_seed": np.zeros((1, 1, 5))}])


# --- R8: smoothing -----------------------------------------------------------------------------------------------------------

def test_two_tap_smoothing_averages_only_within_trial_in_offset_order_whatever_the_row_order():
  rng = np.random.default_rng(5)
  trial = np.repeat([4, 9, 2], [3, 1, 4])
  off = np.concatenate([np.arange(3), [0], np.arange(4)]) * 64
  p = rng.dirichlet(np.ones(5), size=len(trial))
  perm = rng.permutation(len(trial))
  sm = L.smooth_two_tap(p[perm], trial[perm], off[perm])
  exp = np.empty_like(p)
  for i in range(len(trial)):
    prev = [j for j in range(len(trial)) if trial[j] == trial[i] and off[j] < off[i]]
    exp[i] = p[i] if not prev else (p[max(prev, key=lambda j: off[j])] + p[i]) / 2
  np.testing.assert_allclose(sm, exp[perm], atol=1e-12)


def test_output_two_tap_accuracy_matches_my_recomputation_from_stored_fold(tmp_path):
  P, ctx = world()
  args = make_args(variants=["nodes+F"], only_test=None)
  r = G.run_and_report(P, ctx, "built x, LOSO, y", args, "cpu", tmp_path)["res"]
  s = r["summary"]
  for sub in ("S01", "S03"):
    arr, _ = L.load_fold(G.fold_path(tmp_path, "gnn_nodes+F", "loso", sub))
    o = np.lexsort((arr["offset"], arr["trial_id"]))
    pr, tid, yi = arr["proba"][o], arr["trial_id"][o], np.searchsorted(P["classes"], arr["y"][o])
    sm = pr.copy()
    for i in range(1, len(pr)):
      if tid[i] == tid[i - 1]:
        sm[i] = (pr[i - 1] + pr[i]) / 2
    row = s[(s["Method"] == "gnn_nodes+F") & (s["Subject"] == sub)].iloc[0]
    assert row["2-tap Smoothed (%)"] == pytest.approx(100 * np.mean(sm.argmax(1) == yi), abs=0.01)


# --- labels and strings ------------------------------------------------------------------------------------------------------

def test_strings_normalization_protocol_data_source_in_loso_and_within(tmp_path):
  P, ctx = world()
  a = make_args(variants=["nodes+F"], norm=["pooled", "subject"])
  s = G.run_and_report(P, ctx, "built folders x, session OO, LOSO, channels common", a, "cpu", tmp_path / "l")["res"]["summary"]
  assert set(s["Method"]) == {"gnn_nodes+F", "gnn_nodes+F_subjnorm"}
  assert (s["Protocol"] == "loso").all() and (s["Seeds"] == 2).all()
  pooled, sub = s[s["Method"] == "gnn_nodes+F"], s[s["Method"] == "gnn_nodes+F_subjnorm"]
  assert pooled["Normalization"].str.contains("training windows only").all() and pooled["Normalization"].str.contains("R2").all()
  for key in ("unsupervised", "no labels", "test-time", "offline upper bound", "R2 exception"):
    assert sub["Normalization"].str.contains(key).all(), key
  assert not pooled["Normalization"].str.contains("test-time").any()
  assert s["Data source"].str.contains("LOSO").all() and not s["Data source"].str.contains("within-subject").any()
  Pw, ctxw = world("within")
  aw = make_args(variants=["nodes+F"], protocol="within")
  sw = G.run_and_report(Pw, ctxw, "built folders x, session OO, LOSO, channels common", aw, "cpu", tmp_path / "w")["res"]["summary"]
  assert (sw["Protocol"] == "within").all()
  assert sw["Data source"].str.contains("within-subject").all() and not sw["Data source"].str.contains("LOSO").any()
  assert set(sw["Method"]) == {"gnn_nodes+F"}                                  # pooled only under within


def test_cli_defaults_two_variants_and_pooled(monkeypatch):
  a = G.build_parser().parse_args([])
  assert a.variants == ["nodes+F", "nodes+coh+F"] and a.norm == ["pooled"] and a.seeds == 3 and a.protocol == "loso"


# --- carry-forwards ----------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def built3(tmp_path_factory):
  root = tmp_path_factory.mktemp("p23ind") / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    write_built_subject(root, s, n_trials=10, seed=40 + i)
  return root.parent


def test_warmup_summary_has_normalization_column_with_r2_wording(built3, tmp_path):
  out = tmp_path / "wu"
  assert WU.main(["--data-root", str(built3), "--out-dir", str(out), "--warmup-trials", "1", "2"]) == 0
  for name in ("summary.csv", "cohort.csv"):
    df = pd.read_csv(out / name)
    assert "Normalization" in df.columns and df["Normalization"].notna().all()
    for key in ("whole-session", "first K", "none", "R2 exception"):
      assert key in df["Normalization"].iloc[0], (name, key)
  cfg = json.loads((out / "warmup_config.json").read_text())
  assert "offline upper bound" in cfg["normalization"]


def test_within_lda_receives_cv_groups_and_says_within_subject(monkeypatch):
  from tests.test_p21_loso import make_subject
  d = make_subject("S01", 5, n_trials=10, wpt=5)
  d["cv_groups"] = d["trial_ids"] + 777
  P = L.pool([d], ["fbcsp"])
  seen = []

  def spy(b, fb, yi, groups, *a, **k):
    seen.append(np.asarray(groups).copy())
    return {"proba": np.zeros((1, len(yi), 5)), "train_acc": 0.0, "n_train": 1}

  monkeypatch.setattr(L, "within_lda_fold", spy)
  L.run_fold("within_lda", P, 0, SimpleNamespace(folds=2, within_repeats=1, seed=42), "cpu")
  assert len(seen) == 1 and np.array_equal(seen[0], d["cv_groups"]) and not np.array_equal(seen[0], d["trial_ids"])
  assert "within-subject" in L.within_source("x, session OO, LOSO, channels common")
  assert "LOSO" not in L.within_source("x, session OO, LOSO, channels common")
