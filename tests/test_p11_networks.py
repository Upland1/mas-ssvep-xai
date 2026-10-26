"""P11 network tests (deep-learning): trial-grouped folds in every network script, ids through the gate (PF-03),
N4 carry-forward (training dataset = training fold, seeded loader generator in both arms), outputs per `--cv`.
Synthetic trees (tests/p05_synth), 1-2 epochs, CPU."""

import numpy as np
import pandas as pd
import pytest
import torch

from scripts.benchmarks.neural_networks import benchmark_compact_cnn as bc
from scripts.benchmarks.neural_networks import benchmark_eegnet as be
from scripts.benchmarks.neural_networks import benchmark_nn_augmentation as ab
from scripts.benchmarks.neural_networks import benchmark_shallow_convnet as bs
from src.models.cnn import benchmark_common, eegnet_cv
from src.models.cnn.eegnet_cv import train_and_eval_cv
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials, shared_trials
from tests.p05_synth import make_windows, write_subject

REST = 20  # 201 rows written by write_subject (10 trials of 2)


def _tree(tmp_path, subjects=("S03",), reject_stim_row=None):
  for s in subjects:
    write_subject(tmp_path / "proc", s, n_trials=3)
    if reject_stim_row is not None:  # one window far above the 120 uV gate: removed by the gate, mid-block
      f = tmp_path / "proc" / s / "X_time_windows.npy"
      X = np.load(f)
      X[REST + reject_stim_row] += 400.0 * np.sign(np.sin(2 * np.pi * 7 * np.arange(X.shape[2]) / 250.0))
      np.save(f, X)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  return ["--epochs", "1", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
          "--reports-dir", str(tmp_path / "rep"), "--config", str(cfg)]


def _spy_splits(monkeypatch):
  rec = []
  real = eegnet_cv.make_splits

  def spy(cv, y, ids, seed=42):
    out = real(cv, y, ids, seed)
    rec.append({"cv": cv, "ids": None if ids is None else np.asarray(ids).copy(), "splits": out})
    return out

  monkeypatch.setattr(eegnet_cv, "make_splits", spy)
  return rec


# ---------- R1 / PF-01: no network script shares a trial between train and test ----------

SCRIPTS = [("eegnet", be, ["--subject", "S03"]), ("compact_cnn", bc, ["--subject", "S03"]),
           ("shallow_convnet", bs, ["--subject", "S03"]),
           ("nn_augmentation", ab, ["--model", "eegnet", "--subjects", "S03"])]


@pytest.mark.parametrize("name,mod,extra", SCRIPTS, ids=[s[0] for s in SCRIPTS])
def test_every_network_script_split_shares_no_trial_id(tmp_path, monkeypatch, name, mod, extra):
  argv = _tree(tmp_path)
  rec = _spy_splits(monkeypatch)
  assert mod.main([*extra, *argv]) == 0  # default protocol = grouped
  assert rec and all(r["cv"] == "grouped" for r in rec)
  for r in rec:
    assert len(np.unique(r["ids"])) == 15 and len(r["splits"]) == 5
    assert_no_shared_trials(r["splits"], r["ids"])


def test_legacy_split_does_share_trials_negative_control(tmp_path, monkeypatch):
  """The historical window-level split leaks trials: the helper used above must fail on it."""
  argv = _tree(tmp_path)
  rec = _spy_splits(monkeypatch)
  assert be.main(["--subject", "S03", "--cv", "legacy", *argv]) == 0
  ids = benchmark_common.gated_windows(tmp_path / "proc", "S03")["trial_ids"]
  assert shared_trials(rec[0]["splits"], ids)
  with pytest.raises(AssertionError):
    assert_no_shared_trials(rec[0]["splits"], ids)


def test_train_and_eval_cv_asserts_grouped_needs_ids():
  X, y = make_windows(n_trials=2, seed=0)
  with pytest.raises(ValueError):
    train_and_eval_cv(X, y, epochs=1, device="cpu")  # grouped by default, no ids


# ---------- PF-03: ids built on the pre-gate labels, then the valid mask ----------

def test_network_trial_ids_survive_a_gate_rejection_pf03(tmp_path):
  _tree(tmp_path, reject_stim_row=7)  # stimulus window 7 = 2nd window of trial 1 of class 101
  g = benchmark_common.gated_windows(tmp_path / "proc", "S03")
  assert g["n_stimulus"] == 75 and g["n_clean"] == 74 and len(g["trial_ids"]) == 74
  full = np.repeat(np.arange(REST // 2, REST // 2 + 15), 5)  # pre-gate ids of the 75 stimulus rows
  assert np.array_equal(g["trial_ids"], np.delete(full, 7))
  assert not g["trial_ids_approximate"]  # the gate does not make ids approximate
  # the bug (ids built after the gate) would shift every later chunk
  from src.preprocessing.dataset.cv_utils import build_trial_ids
  assert not np.array_equal(build_trial_ids(g["y"], 5, warn=False) + REST // 2, g["trial_ids"])


def test_network_ids_flag_truncated_block_as_approximate(tmp_path):
  _tree(tmp_path)
  f = tmp_path / "proc" / "S03"
  y = np.load(f / "y_labels.npy")
  keep = np.ones(len(y), bool)
  keep[REST + 3] = False  # a window lost before the arrays were saved: block of 14
  for n in ("X_psd_features", "X_time_windows", "y_labels"):
    np.save(f / f"{n}.npy", np.load(f / f"{n}.npy")[keep])
  g = benchmark_common.gated_windows(tmp_path / "proc", "S03")
  assert g["trial_ids_approximate"] and len(np.unique(g["trial_ids"])) == 15


# ---------- N4 and PF-28: fold scope, seeded generator, shared folds in OFF and ON ----------

def test_n4_training_dataset_is_training_fold_and_generator_seeded_in_both_arms(monkeypatch):
  X, y = make_windows(n_trials=4, seed=0)
  ids = np.repeat(np.arange(len(y) // 5), 5)
  seen = {}
  DL = eegnet_cv.DataLoader
  for arm in (False, True):
    rec = {"len": [], "gen": [], "shuffle": []}

    def dl(ds, rec=rec, **kw):
      rec["len"].append(len(ds))
      rec["gen"].append(kw["generator"].initial_seed())
      rec["shuffle"].append(kw["shuffle"])
      return DL(ds, **kw)

    monkeypatch.setattr(eegnet_cv, "DataLoader", dl)
    r = train_and_eval_cv(X, y, epochs=1, device="cpu", augment=arm, groups=ids)
    monkeypatch.undo()
    seen[arm] = (rec, r)
    assert rec["len"] == [len(tr) for tr, _ in r["splits"]]  # dataset = training fold only, never the whole array
    assert all(n < len(y) for n in rec["len"])
    assert rec["gen"] == [42 + k for k in range(5)] and all(rec["shuffle"])  # generator seeded seed+fold, shuffle on
  assert seen[False][0]["len"] == seen[True][0]["len"]
  assert all(np.array_equal(a[1], b[1]) and np.array_equal(a[0], b[0])
             for a, b in zip(seen[False][1]["splits"], seen[True][1]["splits"]))


def test_ab_script_arms_share_one_fold_split_and_seeds(tmp_path, monkeypatch):
  argv = _tree(tmp_path)
  rec = _spy_splits(monkeypatch)
  assert ab.main(["--model", "eegnet", "--subjects", "S03", *argv]) == 0
  assert len(rec) == 2
  assert all(np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]) for a, b in zip(rec[0]["splits"], rec[1]["splits"]))
  assert np.array_equal(rec[0]["ids"], rec[1]["ids"])


# ---------- smoothing rule is passed through ----------

@pytest.mark.parametrize("rule", ["mod5", "trial"])
def test_smoothing_rule_and_ids_reach_accuracies(monkeypatch, rule):
  X, y = make_windows(n_trials=4, seed=0)
  ids = np.repeat(np.arange(len(y) // 5), 5)
  calls = []
  real = eegnet_cv.accuracies
  monkeypatch.setattr(eegnet_cv, "accuracies", lambda *a, **k: (calls.append(a), real(*a, **k))[1])
  r = train_and_eval_cv(X, y, epochs=1, device="cpu", groups=ids, smoothing=rule)
  assert calls[0][3] is ids and calls[0][4] == rule
  assert (r["smoothing"].startswith("2.0 s rule = trial-reset")) == (rule == "trial") and "StratifiedGroupKFold" in r["cv"]


# ---------- outputs per --cv, meta ----------

def test_grouped_outputs_in_reports_legacy_under_legacy_leaky_and_meta(tmp_path):
  argv = _tree(tmp_path, ("S01", "S02"), reject_stim_row=7)
  assert be.main(["--subjects", "S01", "S02", *argv]) == 0
  rep = tmp_path / "rep"
  assert (rep / "eegnet_benchmark_cpu.csv").is_file() and not (rep / "legacy_leaky").exists()
  meta = (rep / "eegnet_benchmark_cpu.meta.txt").read_text()
  assert "StratifiedGroupKFold(5, shuffle, 42)" in meta and "R8 legacy-folder clause" in meta
  assert "trial_ids_approximate subjects: none" in meta and "indexed by the valid mask" in meta
  assert be.main(["--subjects", "S01", "--cv", "legacy", "--smoothing", "mod5", *argv]) == 0
  leg = rep / "legacy_leaky" / "eegnet_benchmark_cpu.meta.txt"
  assert leg.is_file() and "StratifiedKFold(5, shuffle, 42) over windows" in leg.read_text()
  assert "StratifiedGroupKFold" in (rep / "eegnet_benchmark_cpu.meta.txt").read_text()  # grouped file untouched
  assert be.main(["--subject", "S01", "--smoothing", "trial", "--reports-dir", str(tmp_path / "rep2"), *argv[:-4], "--config", argv[-1]]) == 0
  assert "2.0 s rule = trial-reset" in (tmp_path / "rep2" / "eegnet_benchmark_cpu.meta.txt").read_text()


def test_ab_outputs_dirs_meta_and_freeze_legacy_only_with_legacy(tmp_path, capsys):
  argv = _tree(tmp_path)
  with pytest.raises(SystemExit):
    ab.main(["--model", "eegnet", "--subjects", "S03", "--freeze-legacy", *argv])
  assert not (tmp_path / "rep").exists()
  assert ab.main(["--model", "eegnet", "--subjects", "S03", *argv]) == 0
  csv = tmp_path / "rep" / "augmentation_ab_eegnet.csv"
  assert csv.is_file()
  meta = csv.with_suffix(".meta.txt").read_text()
  assert "StratifiedGroupKFold" in meta and "2.0 s rule=mod5" in meta and "approximate" in meta
  assert ab.main(["--model", "eegnet", "--subjects", "S03", "--cv", "legacy", "--freeze-legacy", *argv]) == 0
  leg = tmp_path / "rep" / "legacy_leaky" / csv.name
  assert leg.is_file() and "legacy leaky" in leg.with_suffix(".meta.txt").read_text()
  assert list(pd.read_csv(leg).columns) == ab.COLUMNS


# ---------- P11 round 2: the network path and the classical flagship path see the same folds ----------

def test_network_folds_equal_classical_flagship_folds(tmp_path):
  """`gated_windows` + `train_and_eval_cv` (networks) and `prepare_subject` + `splits_for` (flagship, = R-6) give the
  same clean windows, labels, trial ids and (train, test) folds, with a gate rejection inside a block (PF-03)."""
  from src.models.classical.benchmark_runner import prepare_subject
  from src.models.classical.legacy_eval import splits_for
  _tree(tmp_path, reject_stim_row=7)
  proc = tmp_path / "proc"
  g = benchmark_common.gated_windows(proc, "S03")
  b = prepare_subject(proc, "S03")
  assert g["n_clean"] == b["n_clean"] == 74
  np.testing.assert_array_equal(g["y"], b["y"])
  np.testing.assert_array_equal(g["trial_ids"], b["trial_ids"])
  r = train_and_eval_cv(g["X"], g["y"], epochs=1, device="cpu", groups=g["trial_ids"], cv="grouped")
  ref = splits_for("grouped", b["y"], b["trial_ids"], 42)
  assert len(r["splits"]) == len(ref) == 5
  for (tr, te), (rtr, rte) in zip(r["splits"], ref):
    np.testing.assert_array_equal(tr, rtr)
    np.testing.assert_array_equal(te, rte)
