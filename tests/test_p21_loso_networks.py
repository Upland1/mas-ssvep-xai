"""P21.2 tests (deep-learning): network methods of the LOSO harness on small synthetic subjects, CPU (and CUDA when present).

Planted data: class c is a sinusoid at TARGET_FREQS[c] on every channel plus noise, a different gain per subject. Each fix
test names the bug it guards and a variant that fails it.
"""

import numpy as np
import pytest
import torch

from scripts.benchmarks import benchmark_loso as L
from src.features.ssvep.fbcca_extraction import TARGET_FREQS
from src.models.cnn import training as TR
from tests.test_p21_loso import FS, T, make_subject

C = 6


def sinus_subject(name, seed, gain=1.0, n_trials=20, wpt=4):
  d = make_subject(name, seed, n_trials=n_trials, wpt=wpt)
  rng = np.random.default_rng(100 + seed)
  t = np.arange(T) / FS
  sig = np.sin(2 * np.pi * np.asarray(TARGET_FREQS)[d["y"] - 101][:, None] * t[None, :])
  d["X"] = (gain * (sig[:, None, :] + 0.5 * rng.normal(size=(len(sig), C, T)))).astype(np.float64)
  return d


@pytest.fixture(scope="module")
def planted():
  subs = [sinus_subject("S01", 1, 1.0), sinus_subject("S02", 2, 5.0), sinus_subject("S03", 3, 0.2), sinus_subject("S04", 4, 2.0)]
  return L.pool(subs, ["fbcsp"])


def net_args(*extra):
  return L.build_parser().parse_args(["--max-epochs", "12", "--patience", "12", "--device", "cpu", *extra])


def test_pooled_ccnn_learns_the_planted_classes_on_the_held_out_subject(planted):
  P = planted
  tr, te = L.loso_split(P["subj"], 3)
  r = L.network_fold(P, tr, te, "ccnn", net_args(), "cpu")
  acc = float(np.mean(r["proba"].argmax(1) == P["yi"][te]))
  assert acc > 0.8 and r["train_acc"] > 0.8, (acc, r["train_acc"])   # chance is 0.2
  assert r["proba"].shape == (len(te), 5) and np.allclose(r["proba"].sum(1), 1.0, atol=1e-5)
  assert not L.is_degenerate(r["best_epoch"], r["train_acc"], 5)
  # the reported accuracies stay next to each other
  assert 0.0 <= r["val_acc"] <= 1.0
  # bug variant: training labels shuffled (the planted structure destroyed) must not pass the same accuracy check
  Q = dict(P, yi=P["yi"].copy())
  Q["yi"][tr] = np.random.default_rng(0).permutation(Q["yi"][tr])
  r2 = L.network_fold(Q, tr, te, "ccnn", net_args(), "cpu")
  assert float(np.mean(r2["proba"].argmax(1) == P["yi"][te])) < 0.6


def test_validation_windows_exclude_the_held_out_subject_and_the_raw_id_bug_is_caught(planted, monkeypatch):
  """PF-32 / PF-33. Offset ids: no validation window is from the test subject. Bug: pooling with raw (un-offset) trial ids
  makes the groups collide across subjects and `network_fold` refuses."""
  P = planted
  tr, te = L.loso_split(P["subj"], 1)
  seen = {}
  real = TR.fit_network

  def spy(X, y, groups, *a, **k):
    r = real(X, y, groups, *a, **k)
    seen["val_subj"] = set(P["subj"][tr][r["val_idx"]])
    seen["fit_subj"] = set(P["subj"][tr][r["fit_idx"]])
    return r

  monkeypatch.setattr(TR, "fit_network", spy)
  L.network_fold(P, tr, te, "eegnet", net_args("--max-epochs", "1"), "cpu")
  assert 1 not in seen["val_subj"] | seen["fit_subj"] and len(seen["val_subj"]) >= 2
  bad = dict(P, groups=P["groups"] % L.TRIAL_OFFSET)   # the bug: raw ids
  with pytest.raises(AssertionError, match="held-out trial ids"):
    L.network_fold(bad, tr, te, "eegnet", net_args("--max-epochs", "1"), "cpu")
  # the guard is meaningful: fitting on all rows (test subject included) does put it into the validation split
  r = real(P["X"], P["yi"], P["groups"], TR.model_factory("eegnet", P["fs"]), max_epochs=1, device="cpu")
  assert 1 in set(P["subj"][r["val_idx"]])


def test_normalisation_statistics_ignore_the_held_out_subject(planted):
  """R2: replacing the held-out subject's windows by a sentinel changes neither the statistics nor the training result."""
  P = planted
  tr, te = L.loso_split(P["subj"], 2)
  r0 = L.network_fold(P, tr, te, "eegnet", net_args("--max-epochs", "2"), "cpu")
  S = dict(P, X=P["X"].copy())
  S["X"][te] = 1e6
  r1 = L.network_fold(S, tr, te, "eegnet", net_args("--max-epochs", "2"), "cpu")
  assert np.array_equal(r0["mean"], r1["mean"]) and np.array_equal(r0["std"], r1["std"])
  assert all(torch.equal(a, b) for a, b in zip(r0["model"].state_dict().values(), r1["model"].state_dict().values()))
  # bug variant: statistics over all rows depend on the held-out subject
  assert not np.allclose(TR.fit_stats(S["X"])[0], TR.fit_stats(P["X"])[0])


def test_degenerate_flag_fires_on_best_epoch_one_and_low_train_accuracy(planted):
  assert L.is_degenerate(1, 0.95, 5) and L.is_degenerate(5, 0.95, 5) and not L.is_degenerate(6, 0.95, 5)
  assert L.is_degenerate(30, 0.25, 5) and not L.is_degenerate(30, 0.31, 5)
  P = planted
  tr, te = L.loso_split(P["subj"], 0)
  r = L.network_fold(P, tr, te, "compact_eegnet", net_args("--max-epochs", "1", "--patience", "1"), "cpu")
  assert r["best_epoch"] == 1 and L.is_degenerate(r["best_epoch"], r["train_acc"], 5)   # planted best-epoch-1 history
  assert not L.is_degenerate(float("nan"), float("nan"), 5)                          # classical rows are never flagged


def test_saved_state_dict_reproduces_the_fold_probabilities(planted, tmp_path):
  P = planted
  tr, te = L.loso_split(P["subj"], 0)
  r = L.network_fold(P, tr, te, "eegnet", net_args("--max-epochs", "2"), "cpu")
  ctx = {"channels": P["channels"], "fs": P["fs"]}
  L.save_models(tmp_path, "eegnet", "S01", {"model": r["model"], "mean": r["mean"], "std": r["std"]}, ctx)
  blob = torch.load(tmp_path / "eegnet__test-S01.pt", weights_only=False)
  m = TR.model_factory("eegnet", blob["fs"])(5, P["X"].shape[1], P["X"].shape[2])
  m.load_state_dict(blob["state_dict"])
  p = TR.predict_proba(m, TR.normalise(P["X"][te], blob["mean"], blob["std"]), torch.device("cpu"))
  assert np.array_equal(p, r["proba"])


def test_method_names_and_device_fallback(monkeypatch, capsys):
  assert L.NETWORK_METHODS["compact"] == "compact_eegnet"   # PF-31: tables print compact_eegnet
  assert L.pick_device("cpu") == "cpu"
  monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
  assert L.pick_device("cuda") == "cpu" and "falling back to cpu" in capsys.readouterr().out
  assert L.pick_device("auto") == "cpu"
  monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
  assert L.pick_device("auto") == "cuda" and L.pick_device("cuda") == "cuda" and L.pick_device("cpu") == "cpu"


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA device")
@pytest.mark.parametrize("method", ["ccnn", "compact_eegnet", "eegnet"])
def test_network_fold_runs_on_cuda(planted, method):
  P = planted
  tr, te = L.loso_split(P["subj"], 0)
  r = L.network_fold(P, tr, te, method, net_args("--max-epochs", "2"), "cuda")
  assert r["proba"].shape == (len(te), 5) and np.isfinite(r["proba"]).all()
