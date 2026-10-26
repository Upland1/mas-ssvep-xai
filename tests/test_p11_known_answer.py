"""P11 independent known-answer tests (synthetic-tester): trial ids, grouped CV, trial smoothing, R6 alignment.

Written without reading the builders' tests. Expected values are hand-built arrays or planted structure, never
computed with the code under test. The split checks of the nine scripts patch scikit-learn's own splitter classes,
so they see every split regardless of which helper the script uses. Each test names the historical bug it fails on
(PF-01 window-level split, PF-02 smoothing across trials / i%5, PF-03 ids built after the gate).
"""

import warnings
from collections import defaultdict

import numpy as np
import pytest
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier

from scripts.benchmarks.feature_based import benchmark_cross_validation as bcv
from scripts.benchmarks.feature_based import benchmark_feature_selection as bfs
from scripts.benchmarks.feature_based import benchmark_harmonic_fbcca as bhf
from scripts.benchmarks.feature_based import benchmark_n_subjects as bns
from scripts.benchmarks.neural_networks import benchmark_compact_cnn as bc
from scripts.benchmarks.neural_networks import benchmark_eegnet as be
from scripts.benchmarks.neural_networks import benchmark_nn_augmentation as ab
from scripts.benchmarks.neural_networks import benchmark_shallow_convnet as bs
from scripts.evaluation import evaluate_confusion_matrix as ecm
from src.models.classical import legacy_eval as le
from src.models.cnn import benchmark_common
from src.preprocessing.dataset import cv_utils as cu
from src.preprocessing.dataset.smoothing import smooth_probabilities_by_trial, smooth_probabilities_mod5
from tests.p05_synth import write_subject

D = {201: 2, 202: 1, 101: 5, 102: 5, 103: 5, 104: 5, 105: 5}


def _ids(y, spt=D):
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    return cu.build_trial_ids(np.asarray(y), spt).tolist()


def _same_partition(a, b):
  """True when `a` and `b` group the rows identically (ids equal up to a relabelling)."""
  a, b = list(a), list(b)
  if len(a) != len(b):
    return False
  ab_, ba = {}, {}
  for u, v in zip(a, b):
    if ab_.setdefault(u, v) != v or ba.setdefault(v, u) != u:
      return False
  return True


# --- 1. build_trial_ids on hand-built label arrays ----------------------------------------------------

@pytest.mark.parametrize("y,expect", [
  # 201 pairs, 202 singles (every 202 is its own trial), stimulus blocks of 5
  ([201] * 4 + [202] * 2 + [101] * 10 + [102] * 10,
   [0, 0, 1, 1, 2, 3] + [4] * 5 + [5] * 5 + [6] * 5 + [7] * 5),
  # same label twice in a row across what would be two blocks of different labels: runs are maximal
  ([103] * 5 + [104] * 5 + [103] * 5, [0] * 5 + [1] * 5 + [2] * 5),
  # 201 remainder (3 = 2 + 1)
  ([201] * 3 + [101] * 5, [0, 0, 1] + [2] * 5),
  # stimulus remainder 9 = 5 + 4, then a full block
  ([105] * 9 + [101] * 5, [0] * 5 + [1] * 4 + [2] * 5),
  # remainder in the LAST block (39 = 7*5 + 4) after a 202
  ([202] + [104] * 39, [0] + [1 + k // 5 for k in range(39)]),
  # a block shorter than one trial
  ([101] * 3, [0, 0, 0]),
])
def test_ids_hand_built_arrays_with_dict_lengths(y, expect):
  assert _ids(y) == expect


def test_ids_remainder_is_flagged_warned_and_clean_is_silent():
  y = np.array([201] * 2 + [101] * 12 + [102] * 5)
  with pytest.warns(UserWarning):
    ids, trunc = cu.build_trial_ids(y, D, return_truncated=True)
  assert trunc == [(101, 2, 12)]
  assert ids.tolist() == [0, 0] + [1] * 5 + [2] * 5 + [3] * 2 + [4] * 5
  with warnings.catch_warnings():
    warnings.simplefilter("error")
    _, trunc = cu.build_trial_ids(np.array([201] * 4 + [101] * 10), D, return_truncated=True)
  assert trunc == []


def test_ids_int_length_applies_to_every_label():
  assert _ids([201] * 4 + [101] * 5, 2) == [0, 0, 1, 1, 2, 2, 3, 3, 4]
  assert _ids([201] * 4 + [101] * 5, 5) == [0, 0, 0, 0, 1, 1, 1, 1, 1]


# --- 2. pre-gate vs post-gate ids (PF-03) -------------------------------------------------------------

def test_pre_gate_ids_masked_equal_true_ids_post_gate_ids_do_not():
  """Fails on the bug: ids built from the labels that survive the gate."""
  y_pre = np.array([101] * 10 + [102] * 10)
  true = np.repeat(np.arange(4), 5)
  for drop in (2, 13):   # mid-trial windows of trials 0 and 2 (a drop in the last trial of a block is invisible)
    mask = np.ones(20, bool)
    mask[drop] = False
    pre = cu.build_trial_ids(y_pre, 5)[mask]
    assert pre.tolist() == true[mask].tolist()
    assert _ids(y_pre[mask], 5) != true[mask].tolist()


def test_chained_masks_stimulus_selection_then_gate_keep_true_ids():
  y_all = np.array([201] * 4 + [202] + [101] * 5 + [102] * 5)
  ids_all = cu.build_trial_ids(y_all, D)
  stim = np.isin(y_all, [101, 102])
  valid = np.ones(10, bool)
  valid[[1, 6]] = False
  got = ids_all[stim][valid]
  assert got.tolist() == [3, 3, 3, 3, 4, 4, 4, 4]
  # the buggy order: stimulus labels alone, gated, then walked
  assert _ids(y_all[stim][valid], D) != got.tolist()


def test_gate_drop_of_a_whole_trial_leaves_a_gap_not_a_renumbering():
  y = np.array([101] * 15)
  mask = np.ones(15, bool)
  mask[5:10] = False
  assert cu.build_trial_ids(y, 5)[mask].tolist() == [0] * 5 + [2] * 5


# --- 3. no shared trial id across train/test in the nine scripts --------------------------------------

REJECT = 7        # stimulus window index (trial 1 of class 101) made unusable by the gate
REST = 20


def _truth_ids(n_stim=75, reject=REJECT):
  """Hand-known trial id of every clean stimulus window of the synthetic subject (5 windows per trial)."""
  return np.delete(np.arange(n_stim) // 5, reject)


def _make_tree(tmp_path, reject=REJECT):
  write_subject(tmp_path / "proc", "S03", n_trials=3, seed=3, snr=0.12)
  f = tmp_path / "proc" / "S03" / "X_time_windows.npy"
  X = np.load(f)
  X[REST + reject] += 400.0 * np.sign(np.sin(2 * np.pi * 7 * np.arange(X.shape[2]) / 250.0))
  np.save(f, X)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  return tmp_path / "proc", cfg


class SplitSpy:
  """Records every call of the scikit-learn splitters the scripts could use (window-level or grouped)."""

  def __init__(self, monkeypatch):
    self.grouped, self.plain = [], []
    spy = self
    og, op = StratifiedGroupKFold.split, StratifiedKFold.split

    def split_g(self_, X, y=None, groups=None):
      out = list(og(self_, X, y, groups))
      spy.grouped.append((None if groups is None else np.asarray(groups).copy(), np.asarray(y).copy(), out))
      return iter(out)

    def split_p(self_, X, y=None, groups=None):
      out = list(op(self_, X, y, groups))
      spy.plain.append((np.asarray(y).copy(), out))
      return iter(out)

    monkeypatch.setattr(StratifiedGroupKFold, "split", split_g)
    monkeypatch.setattr(StratifiedKFold, "split", split_p)

  def outer(self, n):
    """Grouped calls over `n` windows (the outer fold split)."""
    return [c for c in self.grouped if len(c[1]) == n]


def _check_outer(spy, n_clean):
  truth = _truth_ids()
  assert not spy.plain, "a window-level StratifiedKFold split was requested (PF-01)"
  outer = spy.outer(n_clean)
  assert outer, "no grouped split over the clean windows"
  for groups, y, splits in outer:
    assert groups is not None and _same_partition(groups, truth)   # ids = the hand-known ids (PF-03, R6)
    assert len(splits) == 5
    for tr, te in splits:
      assert not (set(groups[tr]) & set(groups[te]))
    assert sorted(np.concatenate([te for _, te in splits]).tolist()) == list(range(n_clean))
  return outer


CLASSICAL = {
  "benchmark_n_subjects": lambda proc, cfg, out: bns.main(["--data-root", str(proc), "--reports-dir", str(out)]),
  "benchmark_cross_validation": lambda proc, cfg, out: bcv.main(
    ["--subject", "S03", "--processed-dir", str(proc), "--reports-dir", str(out)]),
  "benchmark_feature_selection": lambda proc, cfg, out: bfs.main(
    ["--subject", "S03", "--processed-dir", str(proc), "--reports-dir", str(out), "--k-features", "10",
     "--sfs-features", "3"]),
  "benchmark_harmonic_fbcca": lambda proc, cfg, out: bhf.main(
    ["--subject", "S03", "--processed-dir", str(proc), "--reports-dir", str(out), "--no-figures"]),
  "evaluate_confusion_matrix": lambda proc, cfg, out: ecm.main(
    ["--subject", "S03", "--processed-dir", str(proc), "--reports-dir", str(out), "--no-figures"]),
}


@pytest.mark.parametrize("name", sorted(CLASSICAL))
def test_classical_script_default_split_is_grouped_with_true_ids(tmp_path, monkeypatch, name):
  proc, cfg, = _make_tree(tmp_path)
  spy = SplitSpy(monkeypatch)
  assert CLASSICAL[name](proc, cfg, tmp_path / "rep") == 0
  _check_outer(spy, 74)


def test_feature_selection_sfs_inner_cv_is_grouped_and_shares_no_id(tmp_path, monkeypatch):
  proc, cfg = _make_tree(tmp_path)
  spy = SplitSpy(monkeypatch)
  assert CLASSICAL["benchmark_feature_selection"](proc, cfg, tmp_path / "rep") == 0
  outer_ids = set(spy.outer(74)[0][0].tolist())
  inner = [c for c in spy.grouped if len(c[1]) < 74]
  assert len(inner) >= 5, "the SFS inner CV of each outer fold must come from a grouped splitter"
  for groups, y, splits in inner:
    assert groups is not None and set(groups.tolist()) <= outer_ids
    for tr, te in splits:
      assert not (set(groups[tr]) & set(groups[te]))
  assert not spy.plain   # sklearn's default inner StratifiedKFold(5) over windows would be recorded here


NETS = {
  "eegnet": (be, ["--subject", "S03"]),
  "compact_cnn": (bc, ["--subject", "S03"]),
  "shallow_convnet": (bs, ["--subject", "S03"]),
  "nn_augmentation": (ab, ["--model", "eegnet", "--subjects", "S03"]),
}


@pytest.mark.parametrize("name", sorted(NETS))
def test_network_script_default_split_is_grouped_with_true_ids(tmp_path, monkeypatch, name):
  proc, cfg = _make_tree(tmp_path)
  spy = SplitSpy(monkeypatch)
  mod, extra = NETS[name]
  argv = [*extra, "--epochs", "1", "--device", "cpu", "--data-root", str(proc), "--reports-dir",
          str(tmp_path / "rep"), "--config", str(cfg)]
  assert mod.main(argv) == 0
  _check_outer(spy, 74)


def test_negative_control_the_spy_sees_the_window_level_split_in_legacy_mode(tmp_path, monkeypatch):
  proc, cfg = _make_tree(tmp_path)
  spy = SplitSpy(monkeypatch)
  assert bcv.main(["--subject", "S03", "--processed-dir", str(proc), "--reports-dir", str(tmp_path / "rep"),
                   "--cv", "legacy", "--smoothing", "mod5"]) == 0
  assert spy.plain and not spy.outer(74)
  y, splits = spy.plain[0]
  shared = [set(_truth_ids()[tr]) & set(_truth_ids()[te]) for tr, te in splits]
  assert all(shared)    # every fold shares trials: the leak


# --- 4. planted leak ----------------------------------------------------------------------------------

def _planted(seed, n_trials=80, wpt=5, p=30, k=4):
  rng = np.random.default_rng(seed)
  sig = rng.normal(size=(n_trials, p))                       # unique fingerprint per trial
  X = np.repeat(sig, wpt, axis=0) + 0.05 * rng.normal(size=(n_trials * wpt, p))
  y_tr = np.repeat(np.arange(k), n_trials // k)              # labels assigned independently of the fingerprints
  rng.shuffle(y_tr)
  return X, np.repeat(y_tr, wpt), np.repeat(np.arange(n_trials), wpt)


def test_planted_trial_fingerprint_leaks_through_window_split_not_trial_split():
  chance, n_trials = 0.25, 80
  sigma = np.sqrt(chance * (1 - chance) / n_trials)          # one draw per trial
  acc = {"legacy": [], "grouped": []}
  for seed in range(4):
    X, y, g = _planted(seed)
    for cv in acc:
      pred = np.zeros(len(y), int)
      for tr, te in cu.make_splits(cv, y, g):
        pred[te] = KNeighborsClassifier(1).fit(X[tr], y[tr]).predict(X[te])
      acc[cv].append(float(np.mean(pred == y)))
  assert min(acc["legacy"]) > 0.9
  assert np.mean(acc["grouped"]) <= chance + 3 * sigma / np.sqrt(4) + 0.02
  assert max(acc["grouped"]) <= chance + 3 * sigma
  # the same data through LDA (a different classifier family): the leak is a property of the split
  X, y, g = _planted(0, p=60)
  pred = np.zeros(len(y), int)
  for tr, te in cu.make_splits("legacy", y, g):
    pred[te] = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(X[tr], y[tr]).predict(X[te])
  assert np.mean(pred == y) > 0.6


# --- 5. smoothing, hand-computed ---------------------------------------------------------------------

def test_trial_smoothing_hand_computed_and_differs_from_mod5():
  # clean array after one window of trial 0 was gated out: trial 0 has 4 windows, trial 1 has 5, trial 2 has 2
  ids = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2])
  p = np.arange(11, dtype=float)[:, None] * np.array([[1.0, -1.0]]) + np.array([[0.0, 100.0]])
  by_trial = smooth_probabilities_by_trial(p, ids)
  first = {0, 4, 9}
  for j in range(11):
    exp = p[j] if j in first else (p[j - 1] + p[j]) / 2
    assert np.allclose(by_trial[j], exp), j
  # hand values for three rows: j=4 first window of trial 1 unchanged; j=5 averages 4 and 5; j=10 averages 9 and 10
  assert by_trial[4].tolist() == [4.0, 96.0]
  assert by_trial[5].tolist() == [4.5, 95.5]
  assert by_trial[10].tolist() == [9.5, 90.5]
  mod5 = smooth_probabilities_mod5(p)
  assert mod5[4].tolist() == [3.5, 96.5]            # mod5 mixes trial 0 into trial 1 here (PF-02)
  assert mod5[5].tolist() == [5.0, 95.0]            # and resets at the wrong row
  assert not np.allclose(mod5, by_trial)
  # the no-reset P04 rule is wrong at the first window of every trial too
  assert not np.allclose(smooth_probabilities_by_trial(p, np.zeros(11, int)), by_trial)


def test_trial_smoothing_never_mixes_one_hot_trials():
  p = np.eye(3)[[0, 0, 1, 1, 1, 2]]
  ids = np.array([0, 0, 1, 1, 1, 2])
  out = smooth_probabilities_by_trial(p, ids)
  assert np.array_equal(out[2], p[2]) and np.array_equal(out[5], p[5])    # no mass from the previous trial
  assert np.array_equal(out[3], p[3]) and np.array_equal(out[1], p[1])    # same-trial neighbours identical here


def test_accuracies_2s_by_trial_hand_computed():
  # 7 windows; rejection shifted the blocks: ids [0,0,0,0,1,1,1]; true classes 0,0,0,0,1,1,1
  y = np.array([101, 101, 101, 101, 102, 102, 102])
  scores = np.array([[.9, .1], [.9, .1], [.9, .1], [.9, .1], [.2, .8], [.2, .8], [.2, .8]])
  scores[3] = [.55, .45]
  scores[4] = [.45, .55]
  pred = 101 + scores.argmax(1)
  a1, a2_trial = le.accuracies(y, pred, scores, np.array([0, 0, 0, 0, 1, 1, 1]), "trial")
  a1b, a2_mod5 = le.accuracies(y, pred, scores, np.array([0, 0, 0, 0, 1, 1, 1]), "mod5")
  assert a1 == a1b == 1.0
  assert a2_trial == 1.0
  # mod5 averages row 4 with row 3: (.55+.45)/2=.5 vs (.45+.55)/2=.5 -> argmax picks class 0 (tie): row 4 wrong
  assert a2_mod5 == 6 / 7


# --- 6. stratification of the grouped folds -------------------------------------------------------------

def test_grouped_folds_are_stratified_within_one_trial_per_class_and_partition_all_windows():
  counts = {101: 10, 102: 12, 103: 15, 104: 10, 105: 8}     # unequal trials per class
  y = np.concatenate([np.full(5 * n, c) for c, n in counts.items()])
  g = np.repeat(np.arange(sum(counts.values())), 5)
  splits = cu.make_splits("grouped", y, g)
  seen = np.sort(np.concatenate([te for _, te in splits]))
  assert seen.tolist() == list(range(len(y)))                # each window tested exactly once
  for c, n in counts.items():
    per_fold = [len(set(g[te][y[te] == c])) for _, te in splits]
    assert sum(per_fold) == n
    assert all(abs(k - n / 5) <= 1 + 1e-9 for k in per_fold), (c, per_fold)
  for tr, te in splits:
    assert set(y[tr]) == set(counts)                          # every class present in training
  # a trial is never split across test folds
  owner = {}
  for f, (_, te) in enumerate(splits):
    for t in set(g[te]):
      assert owner.setdefault(t, f) == f


# --- 7. SFS inner CV (direct) -------------------------------------------------------------------------

def test_column_sets_sfs_inner_cv_uses_training_ids_only(monkeypatch):
  rng = np.random.default_rng(1)
  n_trials, wpt = 30, 5
  ids = np.repeat(np.arange(n_trials), wpt)
  y = np.repeat(np.arange(5).repeat(n_trials // 5), wpt)
  X = rng.normal(size=(len(y), 12)) + y[:, None] * 0.5
  spy = SplitSpy(monkeypatch)
  bfs.column_sets(X, y, n_fbcsp=10, k=4, sfs_k=2, seed=42, ids_tr=ids)
  assert not spy.plain
  assert spy.grouped, "SFS inner CV did not use a grouped splitter"
  groups, _, splits = spy.grouped[-1]
  assert np.array_equal(groups, ids)
  for tr, te in splits:
    assert not (set(ids[tr]) & set(ids[te]))
  # without ids (legacy) the inner CV is the window-level default: it does share trials
  spy.plain.clear()
  bfs.column_sets(X, y, n_fbcsp=10, k=4, sfs_k=2, seed=42, ids_tr=None)
  assert spy.plain and any(set(ids[tr]) & set(ids[te]) for tr, te in spy.plain[-1][1])


# --- 8. ids/windows alignment (R6) ----------------------------------------------------------------------

def test_window_content_encodes_its_trial_id_after_the_gate(tmp_path):
  """Each stimulus window carries a DC offset 100 x its hand-known trial id; the gate drops windows mid-trial."""
  proc, _ = _make_tree(tmp_path)
  f = proc / "S03" / "X_time_windows.npy"
  X = np.load(f)
  truth_all = np.arange(75) // 5
  X[REST:] += 100.0 * truth_all[:, None, None]
  # a second rejection, in trial 9, so shifts happen twice
  second = 47
  X[REST + second] += 400.0 * np.sign(np.sin(2 * np.pi * 7 * np.arange(X.shape[2]) / 250.0))
  np.save(f, X)
  g = benchmark_common.gated_windows(proc, "S03")
  truth = np.delete(truth_all, [REJECT, second])
  assert len(g["trial_ids"]) == len(g["X"]) == 73
  content = np.rint(g["X"].mean(axis=(1, 2)) / 100.0).astype(int)
  assert content.tolist() == truth.tolist()
  assert _same_partition(g["trial_ids"], content)
  # one class per trial
  by_id = defaultdict(set)
  for i, c in zip(g["trial_ids"], g["y"]):
    by_id[i].add(c)
  assert all(len(v) == 1 for v in by_id.values())


def test_classical_prepare_subject_ids_follow_the_mask(tmp_path):
  from src.models.classical import benchmark_runner as br
  proc, _ = _make_tree(tmp_path)
  b = br.prepare_subject(proc, "S03", None, 250.0)
  assert _same_partition(b["trial_ids"], _truth_ids())
  assert len(b["trial_ids"]) == len(b["y"]) == 74
  # ids are in non-decreasing order, as the trial smoothing requires (sorted by trial, not by offset)
  assert np.all(np.diff(b["trial_ids"]) >= 0)


# --- 9. demo network section pairs A/B files by splitter label (Round 1) ------------------------------

def test_demo_network_section_skips_leaky_vs_leaky_and_computes_hand_deltas(tmp_path, capsys):
  from scripts.diagnostics import demo_cv_leakage as demo
  head = "Subject,Clean Windows,1.0s OFF (%),1.0s ON (%),1.0s Delta,2.0s OFF (%),2.0s ON (%),2.0s Delta\n"
  frozen = head + "S01,70,80.0,90.0,10.0,85.0,92.0,7.0\nS02,70,50.0,60.0,10.0,55.0,64.0,9.0\n"
  p11 = head + "S01,70,60.0,75.0,15.0,66.0,78.0,12.0\nS02,70,40.0,42.0,2.0,45.0,47.0,2.0\n"
  leaky = "cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky); seed=42\n"
  grouped = "cv=StratifiedGroupKFold(5, shuffle, 42) over reconstructed trial ids (R1, leak-free); seed=42\n"
  (tmp_path / "legacy_leaky").mkdir()

  def put(path, csv, meta):
    path.write_text(csv)
    path.with_suffix(".meta.txt").write_text(meta)

  # eegnet: the frozen leaky file sits in BOTH slots (stale P10 result in the P11 slot): must be skipped
  put(tmp_path / "legacy_leaky" / "augmentation_ab_eegnet.csv", frozen, leaky)
  put(tmp_path / "augmentation_ab_eegnet.csv", frozen, leaky)
  # compact_cnn: valid pair
  put(tmp_path / "legacy_leaky" / "augmentation_ab_compact_cnn.csv", frozen, leaky)
  put(tmp_path / "augmentation_ab_compact_cnn.csv", p11, grouped)
  # shallow_conv_net: grouped file in the frozen slot (swapped): must be skipped
  put(tmp_path / "legacy_leaky" / "augmentation_ab_shallow_conv_net.csv", p11, grouped)
  put(tmp_path / "augmentation_ab_shallow_conv_net.csv", frozen, leaky)
  net = demo.network_section(tmp_path)
  out = capsys.readouterr().out
  assert set(net["Model"]) == {"compact_cnn"}
  assert "eegnet skipped" in out and "shallow_conv_net skipped" in out
  r = net.set_index("Subject")
  assert r.loc["S01", "Delta OFF 1.0"] == -20.0 and r.loc["S01", "Delta ON 1.0"] == -15.0   # 60-80, 75-90
  assert r.loc["S02", "Delta OFF 1.0"] == -10.0 and r.loc["S02", "Delta ON 1.0"] == -18.0   # 40-50, 42-60
  assert r.loc["S01", "Augmentation gain 1.0 leaky"] == 10.0 and r.loc["S01", "Augmentation gain 1.0 grouped"] == 15.0
  assert r.loc["S02", "Augmentation gain 1.0 leaky"] == 10.0 and r.loc["S02", "Augmentation gain 1.0 grouped"] == 2.0
