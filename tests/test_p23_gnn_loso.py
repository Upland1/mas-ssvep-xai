"""P23.2 known-answer tests for `benchmark_gnn_loso` (synthetic cohorts, CPU, one thread, no real data).

Each fix test also runs the historical bug (a mutant of the guarded step) and asserts that the check catches it:
pooled statistics that include the held-out subject (R2), per-subject normalization that reads labels or other subjects (PF-35),
validation windows chosen per window instead of per trial / without trial-id offsets (PF-32, PF-33), a window-level within splitter (R1),
a fold probability that is not the mean of the seeds (PF-28), configs that are not compared (PF-37).
"""

import copy
from pathlib import Path

import numpy as np
import pytest
import torch
from sklearn.model_selection import StratifiedKFold

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks.benchmark_window_sweep import itr_bits_per_min
from scripts.connectivity.graph_modeling import benchmark_gnn_loso as G
from src.features.connectivity import graph_inputs as gi

CONFIG = G.ROOT / "configs" / "pipeline_config.yaml"
SPEC_P = {"variant": "nodes+coh+F", "norm": "pooled", "method": "gnn_nodes+coh+F"}
SPEC_S = {"variant": "nodes+coh+F", "norm": "subject", "method": "gnn_nodes+coh+F_subjnorm"}


@pytest.fixture(autouse=True)
def one_thread():
  old = torch.get_num_threads()
  torch.set_num_threads(1)
  yield
  torch.set_num_threads(old)


def make_args(**kw):
  a = G.build_parser().parse_args([])
  a.max_epochs, a.patience, a.seeds, a.threads, a.channels = 6, 3, 2, 1, "synthetic"
  a.variants, a.norm, a.protocol = list(G.VARIANTS), ["pooled"], "loso"
  for k, v in kw.items():
    setattr(a, k, v)
  return a


def make_world(protocol="loso", trials=5, wins=3):
  loaded, datasets = G.synthetic_cohort(4, trials, wins)
  P = G.assemble(loaded, datasets, G.VARIANTS)
  ctx = G.make_ctx(P, loaded, Path("synthetic"), CONFIG)
  if protocol == "within":
    G.add_within_splits(ctx, P, 5)
  return P, ctx


def perturb_subject(P, k, big=1e3):
  """Copy of `P` whose subject `k` has sentinel values in every input array."""
  Q = copy.deepcopy(P)
  Q.pop("_subjnorm", None)
  rows = np.flatnonzero(Q["subj"] == k)
  for inp in Q["inputs"].values():
    for arr in (inp.node, inp.edge, inp.graph):
      if arr is not None:
        arr[rows] += big
  return Q


def states_equal(models_a, models_b):
  return all(torch.equal(v, mb.state_dict()[k]) for ma, mb in zip(models_a, models_b) for k, v in ma.state_dict().items())


# --- R2: pooled statistics ------------------------------------------------------------------------------------------

def test_pooled_sentinel_in_heldout_subject_leaves_training_and_weights_bit_identical():
  P, ctx = make_world()
  Q = perturb_subject(P, 0)
  args = make_args()
  a1, m1 = G.run_fold(SPEC_P, P, 0, None, ctx, args, "cpu")
  a2, m2 = G.run_fold(SPEC_P, Q, 0, None, ctx, args, "cpu")
  tr, te = L.loso_split(P["subj"], 0)
  t1, _ = G.fold_inputs(P, SPEC_P, tr, te)
  t2, _ = G.fold_inputs(Q, SPEC_P, tr, te)
  for x, y in ((t1.node, t2.node), (t1.edge, t2.edge), (t1.graph, t2.graph)):
    assert np.array_equal(x, y)
  assert states_equal(m1, m2)
  assert np.array_equal(a1["train_acc_seed"], a2["train_acc_seed"]) and np.array_equal(a1["best_epoch_seed"], a2["best_epoch_seed"])
  assert not np.array_equal(a1["proba"], a2["proba"])            # the sentinel does reach the held-out predictions


def test_sentinel_test_detects_statistics_fitted_on_all_rows(monkeypatch):
  P, _ = make_world()
  Q = perturb_subject(P, 0)
  tr, te = L.loso_split(P["subj"], 0)

  def leaky(inputs, train_idx, test_idx):                          # the bug: statistics over train AND test rows
    st = gi.fit_standardizer(inputs, np.concatenate([train_idx, test_idx]))
    return (gi.apply_standardizer(inputs.take(np.asarray(train_idx)), st), gi.apply_standardizer(inputs.take(np.asarray(test_idx)), st))

  monkeypatch.setattr(G, "standardize_fold", leaky)
  t1, _ = G.fold_inputs(P, SPEC_P, tr, te)
  t2, _ = G.fold_inputs(Q, SPEC_P, tr, te)
  assert not np.array_equal(t1.node, t2.node)


def test_pooled_statistics_are_the_training_rows_only():
  P, _ = make_world()
  tr, te = L.loso_split(P["subj"], 2)
  t, _ = G.fold_inputs(P, SPEC_P, tr, te)
  assert np.allclose(t.node.mean(axis=0), 0, atol=1e-4)           # training rows are standardized by their own mean
  inp = P["inputs"]["nodes+coh+F"]
  assert not np.allclose(inp.take(te).node.mean(axis=0), inp.take(tr).node.mean(axis=0), atol=1e-3)


# --- PF-35: subject normalization ------------------------------------------------------------------------------------

def test_subjnorm_ignores_labels_and_other_subjects():
  P, ctx = make_world()
  args = make_args()
  Q = copy.deepcopy(P)
  rng = np.random.default_rng(0)
  rows = np.flatnonzero(Q["subj"] == 1)
  perm = rng.permutation(len(rows))
  Q["y"][rows], Q["yi"][rows] = P["y"][rows][perm], P["yi"][rows][perm]      # permute the held-out subject's labels
  a1, _ = G.run_fold(SPEC_S, P, 1, None, ctx, args, "cpu")
  a2, _ = G.run_fold(SPEC_S, Q, 1, None, ctx, args, "cpu")
  tr, te = L.loso_split(P["subj"], 1)
  _, x1 = G.fold_inputs(P, SPEC_S, tr, te)
  _, x2 = G.fold_inputs(Q, SPEC_S, tr, te)
  assert np.array_equal(x1.node, x2.node) and np.array_equal(x1.edge, x2.edge) and np.array_equal(x1.graph, x2.graph)
  assert np.array_equal(a1["proba"], a2["proba"]) and np.array_equal(a1["proba_seed"], a2["proba_seed"])
  assert not np.array_equal(P["yi"], Q["yi"])                                  # the permutation really changed the labels
  # each subject is normalized with its own statistics: perturbing another subject leaves it bit-identical
  R = perturb_subject(P, 3)
  _, y1 = G.fold_inputs(P, SPEC_S, tr, te)
  _, y2 = G.fold_inputs(R, SPEC_S, tr, te)
  assert np.array_equal(y1.node, y2.node)
  z = G.fold_inputs(P, SPEC_S, tr, te)[1]
  assert np.allclose(z.node.mean(axis=0), 0, atol=1e-4) and np.allclose(z.node.std(axis=0), 1, atol=1e-3)


def test_subjnorm_differs_from_pooled_when_subjects_differ_and_mutant_is_caught():
  P, _ = make_world()
  tr, te = L.loso_split(P["subj"], 0)
  _, zs = G.fold_inputs(P, SPEC_S, tr, te)
  _, zp = G.fold_inputs(P, SPEC_P, tr, te)
  assert not np.allclose(zs.node, zp.node, atol=1e-2)             # held-out subject has another gain / offset
  # the bug "subject norm = pooled stats of all rows" is not per-subject: it would change when another subject changes
  inp = P["inputs"]["nodes+coh+F"]
  buggy = gi.apply_standardizer(inp.take(te), gi.fit_standardizer(inp, np.arange(len(inp))))
  assert not np.allclose(buggy.node.mean(axis=0), 0, atol=1e-2)


# --- PF-32 / PF-33: validation groups -------------------------------------------------------------------------------

def test_validation_never_contains_heldout_subject_and_is_trial_grouped():
  P, _ = make_world(trials=6)
  for k in range(4):
    tr, te = L.loso_split(P["subj"], k)
    inp, _ = G.fold_inputs(P, SPEC_P, tr, te)
    for seed in (42, 43):
      r = G.fit_gnn(inp, P["yi"][tr], P["groups"][tr], seed, "cpu", max_epochs=2)
      assert k not in set(P["subj"][tr][r["val_idx"]])
      assert not set(P["groups"][tr][r["fit_idx"]]) & set(P["groups"][tr][r["val_idx"]])
      frac = len(set(P["groups"][tr][r["val_idx"]])) / len(set(P["groups"][tr]))
      assert 0.1 <= frac <= 0.3                                    # about 20 % of the training trials
      assert len(r["fit_idx"]) + len(r["val_idx"]) == len(tr)


def test_trial_ids_are_offset_per_subject_and_per_window_groups_are_caught():
  P, _ = make_world()
  sets = [set(P["groups"][P["subj"] == k]) for k in range(4)]
  assert all(not (sets[i] & sets[j]) for i in range(4) for j in range(i + 1, 4))      # PF-33: offsets make ids unique
  raw = P["groups"] % L.TRIAL_OFFSET
  assert set(raw[P["subj"] == 0]) & set(raw[P["subj"] == 1])                         # without offsets they collide
  tr, te = L.loso_split(P["subj"], 0)
  inp, _ = G.fold_inputs(P, SPEC_P, tr, te)
  bad = G.fit_gnn(inp, P["yi"][tr], np.arange(len(tr)), 42, "cpu", max_epochs=1)     # the bug: one group per window
  assert set(P["groups"][tr][bad["fit_idx"]]) & set(P["groups"][tr][bad["val_idx"]])  # the trial check sees the leak


def test_fixed_epochs_without_validation_and_early_stopping_restores_best():
  P, _ = make_world()
  tr, te = L.loso_split(P["subj"], 0)
  inp, _ = G.fold_inputs(P, SPEC_P, tr, te)
  r0 = G.fit_gnn(inp, P["yi"][tr], P["groups"][tr], 42, "cpu", val_frac=0.0, max_epochs=4)
  assert r0["epochs_run"] == 4 and r0["best_epoch"] == 4 and len(r0["val_idx"]) == 0 and np.isnan(r0["val_acc"])
  assert len(r0["fit_idx"]) == len(tr)
  rng = np.random.default_rng(1)
  r = G.fit_gnn(inp, rng.integers(0, 5, len(tr)), P["groups"][tr], 42, "cpu", max_epochs=60, patience=2)   # random labels: val loss rises
  assert r["epochs_run"] < 60 and r["best_epoch"] == r["epochs_run"] - 2
  assert r["val_loss"] == pytest.approx(min(h[1] for h in r["history"]), abs=1e-5)       # best state restored, not the last


# --- R1: within protocol --------------------------------------------------------------------------------------------

def test_within_never_splits_a_trial_covers_every_window_once_and_window_level_cv_is_caught():
  P, ctx = make_world("within")
  for k, s in enumerate(P["subjects"]):
    rows = np.flatnonzero(P["subj"] == k)
    seen = []
    for tr_l, te_l in ctx["within_splits"][s]:
      assert not set(P["groups"][rows[tr_l]]) & set(P["groups"][rows[te_l]])
      assert set(P["yi"][rows[tr_l]]) == set(range(5))
      seen += list(te_l)
    assert sorted(seen) == list(range(len(rows)))
    bad = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(rows)), P["yi"][rows]))
    assert any(set(P["groups"][rows[a]]) & set(P["groups"][rows[b]]) for a, b in bad)   # the legacy window-level split leaks
  a, _ = G.run_fold(SPEC_P, P, 1, 2, ctx, make_args(protocol="within"), "cpu")
  tr_l, te_l = ctx["within_splits"]["S02"][2]
  assert np.array_equal(a["row_idx"], te_l) and len(a["y"]) == len(te_l) and int(a["n_train"]) == len(tr_l)


def test_within_refuses_subject_norm_and_default_out_dirs():
  with pytest.raises(SystemExit):
    G.check_args(make_args(protocol="within", norm=["pooled", "subject"]))
  G.check_args(make_args(protocol="within", norm=["pooled"]))
  assert G.build_parser().parse_args([]).out_dir is None


def test_within_assemble_covers_rows_once_and_incomplete_subject_is_left_out(tmp_path):
  P, ctx = make_world("within")
  args = make_args(protocol="within", variants=["nodes+coh+F"], only_test=["S01"])
  specs = G.make_specs(args.variants, ["pooled"])
  G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  config_of = lambda sp, s, f: G.fold_config(sp, s, f, ctx, args, "cpu")
  items, _ = G.collect(tmp_path, specs, P["subjects"], config_of, args)
  arrays, _ = items[("gnn_nodes+coh+F", "S01")]
  n = int((P["subj"] == 0).sum())
  assert len(arrays["y"]) == n and arrays["proba"].shape == (n, 5) and arrays["proba_seed"].shape == (2, n, 5)
  G.fold_path(tmp_path, "gnn_nodes+coh+F", "within", "S01", 3).unlink()
  items, _ = G.collect(tmp_path, specs, P["subjects"], config_of, args)
  assert items == {}                                               # 4 of 5 folds: no subject row


# --- PF-28: seeds ---------------------------------------------------------------------------------------------------

def test_seed_average_is_mean_of_softmax_and_rerun_is_bit_identical():
  P, _ = make_world()
  tr, te = L.loso_split(P["subj"], 0)
  a, b = G.fold_inputs(P, SPEC_P, tr, te)
  args = make_args(seeds=3)
  r1 = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, args, "cpu")
  r2 = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, args, "cpu")
  assert r1["proba_seed"].shape == (3, len(te), 5)
  assert np.array_equal(r1["proba"], r1["proba_seed"].mean(axis=0))
  assert np.allclose(r1["proba"].sum(axis=1), 1.0, atol=1e-6)
  assert not np.array_equal(r1["proba_seed"][0], r1["proba_seed"][1])
  assert np.array_equal(r1["proba_seed"], r2["proba_seed"]) and np.array_equal(r1["proba"], r2["proba"])
  assert states_equal([x["model"] for x in r1["runs"]], [x["model"] for x in r2["runs"]])
  assert not np.array_equal(r1["proba"], r1["proba_seed"][-1])      # not just the last seed
  assert G.seeds_of(args) == [42, 43, 44]


def test_degenerate_flag_is_per_seed_and_any_seed_flags_the_fold():
  P, _ = make_world()
  tr, te = L.loso_split(P["subj"], 0)
  a, b = G.fold_inputs(P, SPEC_P, tr, te)
  r = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, make_args(max_epochs=1, seeds=2), "cpu")   # best epoch 1 <= 5
  assert r["degenerate_seed"].tolist() == [True, True]
  r = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, make_args(max_epochs=40, patience=40, seeds=1), "cpu")
  assert r["degenerate_seed"].tolist() == [False] and r["train_acc_seed"][0] > 0.5


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_runs_on_cuda_too():
  P, _ = make_world()
  tr, te = L.loso_split(P["subj"], 0)
  a, b = G.fold_inputs(P, SPEC_P, tr, te)
  r = G.gnn_fold(a, P["yi"][tr], P["groups"][tr], b, make_args(max_epochs=4, seeds=1), "cuda")
  assert r["proba"].shape == (len(te), 5) and np.allclose(r["proba"].sum(axis=1), 1.0, atol=1e-5)


# --- PF-37: resume and refusals --------------------------------------------------------------------------------------

def test_interrupt_then_rerun_skips_finished_folds_and_outputs_match(tmp_path, monkeypatch):
  P, ctx = make_world()
  args = make_args(variants=["nodes+coh+F"], norm=["pooled", "subject"])
  specs = G.make_specs(args.variants, args.norm)
  real, calls = G.run_fold, {"n": 0}

  def flaky(*a, **kw):
    calls["n"] += 1
    if calls["n"] == 4:
      raise KeyboardInterrupt
    return real(*a, **kw)

  monkeypatch.setattr(G, "run_fold", flaky)
  with pytest.raises(KeyboardInterrupt):
    G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  assert len(list((tmp_path / "folds").glob("*.npz"))) == 3 and not list((tmp_path / "folds").glob("*.tmp"))
  monkeypatch.setattr(G, "run_fold", real)
  c = G.run_protocol(P, ctx, specs, args, "cpu", tmp_path)
  assert c == {"run": 5, "skipped": 3}
  r1 = G.build_outputs(tmp_path, specs, P["subjects"], P["classes"], lambda sp, s, f: G.fold_config(sp, s, f, ctx, args, "cpu"), "src", args)
  assert G.run_protocol(P, ctx, specs, args, "cpu", tmp_path) == {"run": 0, "skipped": 8}
  r2 = G.build_outputs(tmp_path, specs, P["subjects"], P["classes"], lambda sp, s, f: G.fold_config(sp, s, f, ctx, args, "cpu"), "src", args)
  assert r1["summary"].equals(r2["summary"]) and r1["predictions"].equals(r2["predictions"])
  assert set(r1["summary"]["Method"]) == {"gnn_nodes+coh+F", "gnn_nodes+coh+F_subjnorm"}


def test_changed_configuration_is_refused_with_new_out_dir_message(tmp_path):
  P, ctx = make_world()
  args = make_args(variants=["nodes+coh+F"])
  specs = G.make_specs(args.variants, ["pooled"])
  G.run_protocol(P, ctx, specs, make_args(variants=["nodes+coh+F"], only_test=["S01"]), "cpu", tmp_path)
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    G.run_protocol(P, ctx, specs, make_args(variants=["nodes+coh+F"], only_test=["S01"], seeds=3), "cpu", tmp_path)
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    G.run_protocol(P, ctx, specs, make_args(variants=["nodes+coh+F"], only_test=["S01"], val_frac=0.0), "cpu", tmp_path)
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    G.build_outputs(tmp_path, specs, P["subjects"], P["classes"], lambda sp, s, f: G.fold_config(sp, s, f, ctx, make_args(seeds=3), "cpu"),
                    "src", make_args(variants=["nodes+coh+F"], seeds=3))


def test_every_configuration_key_is_compared():
  P, ctx = make_world("within")
  args = make_args(protocol="within")
  base = G.fold_config(SPEC_P, "S01", 0, ctx, args, "cpu")
  assert {"n_windows_train", "build_git_commits", "config_hash", "git_head", "git_dirty", "n_windows_train_fold"} <= set(base)
  def cfg(spec=SPEC_P, test="S01", fold=0, ctx_=ctx, args_=args, dev="cpu"):
    return G.fold_config(spec, test, fold, ctx_, args_, dev)
  def with_ctx(**kw):
    c = copy.deepcopy(ctx)
    for k, v in kw.items():
      c[k] = v(c[k]) if callable(v) else v
    return c
  loso_args = make_args()
  variants = {
    "variant+method": cfg(spec={**SPEC_P, "variant": "nodes+F", "method": "gnn_nodes+F"}),
    "norm+method+normalization": cfg(spec=SPEC_S),
    "test_subject": cfg(test="S02"), "fold+n_windows_test+n_windows_train_fold": cfg(fold=1),
    "protocol+train_subjects+n_folds": G.fold_config(SPEC_P, "S01", None, ctx, loso_args, "cpu"),
    "cohort": cfg(ctx_=with_ctx(subjects=["S01", "S02", "S03", "S09"])),
    "channels_mode": cfg(args_=make_args(protocol="within", channels="all")),
    "channels": cfg(ctx_=with_ctx(channels=["a", "b"])),
    "window_sec": cfg(args_=make_args(protocol="within", window=2.0)),
    "stride_sec": cfg(args_=make_args(protocol="within", stride_sec=0.5)),
    "fs": cfg(ctx_=with_ctx(fs=250.0)), "classes": cfg(ctx_=with_ctx(classes=[1, 2, 3, 4, 5])),
    "seeds": cfg(args_=make_args(protocol="within", seeds=3)),
    "hyper": cfg(args_=make_args(protocol="within", lr=2e-3)),
    "device": cfg(dev="cuda"),
    "n_windows_train": cfg(ctx_=with_ctx(n_windows=lambda d: {**d, "S01": d["S01"] + 1})),
    "build_git_commits": cfg(ctx_=with_ctx(build_commits=lambda d: {**d, "S01": "other"})),
    "config_hash": cfg(ctx_=with_ctx(config_hash="0" * 64)),
  }
  covered = set()
  for name, other in variants.items():
    assert L.fold_problem(base, other) is not None, name
    covered |= set(L.config_diff(base, other))
  assert set(base) - covered <= set(L.IGNORED_CONFIG_KEYS) | {"quality", "trial_offset", "feature_source", "within_split"}, set(base) - covered
  for key in ("val_frac", "max_epochs", "patience", "batch_size", "lr", "threads"):          # hyperparameters inside `hyper`
    other = cfg(args_=make_args(protocol="within", **{key: getattr(args, key) * 2 if key != "val_frac" else 0.1}))
    assert L.fold_problem(base, other) is not None, key
  assert L.fold_problem(base, copy.deepcopy(base)) is None


# --- outputs --------------------------------------------------------------------------------------------------------

def test_summary_columns_labels_itr_and_within_data_source(tmp_path):
  P, ctx = make_world("within")
  args = make_args(variants=["nodes+coh+F"], norm=["pooled"], protocol="within")
  res = G.run_and_report(P, ctx, "built folder src, LOSO, channels common", args, "cpu", tmp_path / "w")["res"]
  s = res["summary"]
  assert list(s.columns) == G.SUMMARY_COLUMNS and {"Protocol", "Normalization", "Seeds", "Seed SD"} <= set(s.columns)
  assert set(s["Protocol"]) == {"within"} and "within-subject" in s["Data source"].iloc[0] and "LOSO" not in s["Data source"].iloc[0]
  row = s[s["Subject"] == "S01"].iloc[0]
  assert row["ITR (bits/min)"] == pytest.approx(round(itr_bits_per_min(row["Acc (%)"] / 100, 5, 1.5), 2), abs=0.1)
  assert {"Mean", "SD"} <= set(s["Subject"])
  seeds = res["seeds"]
  assert len(seeds) == 4 * 2 and set(seeds["Seed"]) == {42, 43}
  per = seeds[seeds["Subject"] == "S01"]["Acc (%)"].to_numpy()
  assert row["Seed SD"] == pytest.approx(round(float(np.std(per, ddof=1)), 2))
  f = res["folds"]
  assert len(f) == 4 * 5 and {"degenerate", "Train Acc (%)", "Test Acc (%)", "Diagnosis"} <= set(f.columns)
  a = make_args(variants=["nodes+coh+F"], norm=["pooled", "subject"])
  res = G.run_and_report(P, make_world()[1], "built folder src, LOSO, channels common", a, "cpu", tmp_path / "l")["res"]
  s = res["summary"]
  sub = s[s["Method"] == "gnn_nodes+coh+F_subjnorm"]
  assert "offline upper bound" in sub["Normalization"].iloc[0] and "PF-35" in sub["Normalization"].iloc[0]
  assert "training windows only" in s[s["Method"] == "gnn_nodes+coh+F"]["Normalization"].iloc[0]
  assert set(s["Protocol"]) == {"loso"} and "LOSO" in s["Data source"].iloc[0]


def test_incomplete_method_gets_no_cohort_mean(tmp_path):
  P, ctx = make_world()
  args = make_args(variants=["nodes+coh+F"], only_test=["S01", "S02"])
  res = G.run_and_report(P, ctx, "src, LOSO", args, "cpu", tmp_path)["res"]
  s = res["summary"]
  assert s[s["Subject"] == "Mean"]["Acc (%)"].isna().all()


# --- smoke test -----------------------------------------------------------------------------------------------------

def test_smoke_refuses_reports_dir():
  with pytest.raises(SystemExit):
    G.smoke_out_dir(G.ROOT / "reports" / "x")
  with pytest.raises(SystemExit):
    G.smoke_out_dir(G.ROOT / "reports")
  assert G.smoke_out_dir(None).name.startswith("gnn_loso_smoke_")


def test_smoke_test_passes_and_rerun_skips_every_fold(tmp_path, monkeypatch, capsys):
  monkeypatch.setitem(G.SMOKE, "trials_per_class", 5)
  monkeypatch.setitem(G.SMOKE, "max_epochs", 20)
  rc = G.main(["--smoke-test", "--threads", "1", "--device", "cpu", "--out-dir", str(tmp_path / "smoke")])
  out = capsys.readouterr().out
  assert rc == 0 and "[smoke] PASS" in out
  assert "loso: 16 folds run, rerun skipped 16 and ran 0" in out and "within: 40 folds run, rerun skipped 40 and ran 0" in out
  assert len(list((tmp_path / "smoke" / "loso" / "folds").glob("*.npz"))) == 16
  assert len(list((tmp_path / "smoke" / "within" / "folds").glob("*.npz"))) == 40


def test_smoke_fails_when_accuracy_gate_is_not_met(tmp_path, monkeypatch, capsys):
  monkeypatch.setitem(G.SMOKE, "trials_per_class", 5)
  monkeypatch.setitem(G.SMOKE, "max_epochs", 2)
  monkeypatch.setattr(G, "SMOKE_MIN_ACC", 99.9)
  rc = G.main(["--smoke-test", "--threads", "1", "--device", "cpu", "--out-dir", str(tmp_path / "smoke2")])
  assert rc == 1 and "[smoke] FAIL" in capsys.readouterr().out
