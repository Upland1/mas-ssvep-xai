"""P11 builder tests (ml-engineer): trial ids, grouped CV, trial-aware smoothing, the classical scripts.

Synthetic data only. Known answers by hand; the planted-leak, pre-gate and smoothing tests fail on the
historical bugs (PF-01 window-level split, PF-03 post-gate ids, PF-02 i%5 smoothing).
"""

import hashlib
import warnings

import numpy as np
import pytest
from sklearn.neighbors import KNeighborsClassifier

from scripts.benchmarks.feature_based import benchmark_cross_validation as bcv
from scripts.benchmarks.feature_based import benchmark_feature_selection as bfs
from scripts.benchmarks.feature_based import benchmark_harmonic_fbcca as bhf
from scripts.benchmarks.feature_based import benchmark_n_subjects as bns
from scripts.evaluation import evaluate_confusion_matrix as ecm
from src.models.classical import benchmark_runner as br
from src.models.classical import legacy_eval as le
from src.preprocessing.dataset import cv_utils as cu
from src.preprocessing.dataset.smoothing import smooth_probabilities_by_trial, smooth_probabilities_mod5
from tests.p05_synth import write_subject

LENGTHS = cu.LEGACY_TRIAL_LENGTHS


# --- trial ids (P11.1, PF-03) -------------------------------------------------------

def test_ids_clean_blocks_known_answer():
  y = np.array([201] * 4 + [202] * 2 + [101] * 10 + [102] * 10)
  ids = cu.build_trial_ids(y, LENGTHS)
  assert ids.tolist() == [0, 0, 1, 1, 2, 3] + [4] * 5 + [5] * 5 + [6] * 5 + [7] * 5


def test_ids_int_trial_length_and_same_label_adjacent_blocks_stay_separate():
  y = np.array([101] * 5 + [102] * 5 + [101] * 5)
  assert cu.build_trial_ids(y, 5).tolist() == [0] * 5 + [1] * 5 + [2] * 5


def test_ids_remainder_gets_own_id_warns_and_is_reported():
  y = np.array([101] * 9 + [102] * 5)
  with pytest.warns(UserWarning, match="approximate"):
    ids, trunc = cu.build_trial_ids(y, 5, return_truncated=True)
  assert ids.tolist() == [0] * 5 + [1] * 4 + [2] * 5
  assert trunc == [(101, 0, 9)]
  rep = cu.trial_block_report(y, ids, 5)
  assert rep["approximate"] and rep["blocks"] == {101: [9], 102: [5]} and rep["n_trials"] == 3
  with warnings.catch_warnings():
    warnings.simplefilter("error")
    clean = cu.build_trial_ids(np.array([101] * 10), 5)
  assert not cu.trial_block_report(np.array([101] * 10), clean, 5)["approximate"]


def test_ids_are_built_before_the_gate_then_masked_pf03():
  """A window removed by the gate mid-trial: ids[mask] keeps the true ids; ids of the gated labels (the bug) shift them."""
  y_pre = np.array([101] * 10)
  mask = np.ones(10, bool)
  mask[2] = False
  good = cu.build_trial_ids(y_pre, 5)[mask]
  assert good.tolist() == [0, 0, 0, 0, 1, 1, 1, 1, 1]
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    bug = cu.build_trial_ids(y_pre[mask], 5)
  assert bug.tolist() == [0, 0, 0, 0, 0, 1, 1, 1, 1] and not np.array_equal(good, bug)


# --- grouped CV and the no-shared-trials helper (P11.2) ---------------------------------

def _layout(n_trials=10, wpt=5, n_class=5):
  y = np.repeat(np.arange(101, 101 + n_class), n_trials * wpt)
  return y, np.repeat(np.arange(n_class * n_trials), wpt)


def test_grouped_splits_share_no_trial_and_are_stratified_within_one_trial():
  y, g = _layout()
  splits = cu.make_splits("grouped", y, g)
  cu.assert_no_shared_trials(splits, g)
  assert np.array_equal(np.sort(np.concatenate([te for _, te in splits])), np.arange(len(y)))
  for _, te in splits:
    per_class = [len(set(g[te][y[te] == c])) for c in np.unique(y)]
    assert max(per_class) - min(per_class) <= 1


def test_assert_no_shared_trials_catches_the_window_level_split():
  y, g = _layout()
  with pytest.raises(AssertionError):
    cu.assert_no_shared_trials(cu.make_splits("legacy", y, g), g)


def test_make_splits_validates_arguments():
  y, g = _layout(3)
  with pytest.raises(ValueError):
    cu.make_splits("grouped", y, None)
  with pytest.raises(ValueError):
    cu.make_splits("nope", y, g)


def test_output_dir_by_cv():
  assert cu.output_dir("reports", "legacy").as_posix() == "reports/legacy_leaky"
  assert cu.output_dir("reports", "grouped").as_posix() == "reports"


def test_planted_leak_leaky_split_is_far_above_chance_grouped_is_chance():
  """Each trial has its own random signature, labels are random per trial: no class signal exists.
  1-NN on signatures reads the label from a trial-mate in train (window-level split) and cannot across trials."""
  rng = np.random.default_rng(0)
  n_trials, wpt, p = 100, 5, 40
  sig = rng.normal(size=(n_trials, p))
  X = np.repeat(sig, wpt, axis=0) + 0.05 * rng.normal(size=(n_trials * wpt, p))
  y_trial = np.repeat(np.arange(5), n_trials // 5)
  rng.shuffle(y_trial)
  y, g = np.repeat(y_trial, wpt), np.repeat(np.arange(n_trials), wpt)
  acc = {}
  for cv in ("legacy", "grouped"):
    pred = np.zeros(len(y), int)
    for tr, te in cu.make_splits(cv, y, g):
      pred[te] = KNeighborsClassifier(1).fit(X[tr], y[tr]).predict(X[te])
    acc[cv] = float(np.mean(pred == y))
  sigma = np.sqrt(0.2 * 0.8 / n_trials)   # per-trial binomial sigma (windows of a trial are one draw)
  assert acc["legacy"] > 0.95
  assert acc["grouped"] <= 0.2 + 3 * sigma


# --- trial smoothing (P11.3, R8, PF-02) ---------------------------------------------------

def test_smoothing_by_trial_known_answer_and_no_mixing():
  p = np.eye(3)[[0, 0, 0, 1, 1, 2]]
  ids = np.array([0, 0, 0, 1, 1, 2])
  out = smooth_probabilities_by_trial(p, ids)
  expect = p.copy()
  expect[1] = (p[0] + p[1]) / 2
  expect[2] = (p[1] + p[2]) / 2
  expect[4] = (p[3] + p[4]) / 2
  assert np.array_equal(out, expect)
  assert np.array_equal(out[3], p[3]) and np.array_equal(out[5], p[5])   # first window of a trial unchanged
  # i%5 on the same short trials (a trial of 3 then 2: a window was rejected): mixes trial 0 and 1 at row 3
  mod5 = smooth_probabilities_mod5(p)
  assert np.allclose(mod5[3], (p[2] + p[3]) / 2) and not np.allclose(mod5[3], out[3])


def test_smoothing_length_mismatch_raises():
  with pytest.raises(ValueError):
    smooth_probabilities_by_trial(np.zeros((4, 2)), np.zeros(3))


def test_accuracies_rules_and_default():
  y = np.array([101, 101, 101, 102, 102])
  sc = np.array([[.9, .1], [.9, .1], [.2, .8], [.1, .9], [.1, .9]])
  ids = np.array([0, 0, 0, 1, 1])
  pred = np.array([101, 101, 102, 102, 102])
  a1, a2 = le.accuracies(y, pred, sc, ids)             # default with ids = trial rule
  assert a1 == pytest.approx(0.8)
  assert le.accuracies(y, pred, sc) == le.accuracies(y, pred, sc, None, "mod5")   # pre-P11 call = mod5
  with pytest.raises(ValueError):
    le.accuracies(y, pred, sc, None, "trial")
  # trial rule: row 2 = (.9,.1)+(.2,.8) / 2 -> class 101 vs truth 101 after smoothing -> 4 or 5 correct
  assert a2 == pytest.approx(1.0)


# --- SFS inner CV grouped (PF-01) -------------------------------------------------------

def test_sfs_inner_splits_share_no_trial_and_legacy_is_none():
  y, g = _layout(8)
  inner = bfs.inner_sfs_splits(y, g)
  assert len(inner) == 5
  cu.assert_no_shared_trials(inner, g)
  assert bfs.inner_sfs_splits(y, None) is None


def test_column_sets_sfs_receives_grouped_inner_cv(monkeypatch):
  seen = {}

  def fake_sfs(fb, ytr, k, estimator=None, n_jobs=None, cv=None):
    seen["cv"] = cv
    return np.arange(k)

  monkeypatch.setattr(bfs, "select_sfs_fbcsp_features", fake_sfs)
  y, g = _layout(8)
  rng = np.random.default_rng(1)
  Xtr = rng.normal(size=(len(y), 55))
  bfs.column_sets(Xtr, y, 50, 10, 3, 42, 1, True, g)
  cu.assert_no_shared_trials(seen["cv"], g)
  bfs.column_sets(Xtr, y, 50, 10, 3, 42, 1, True, None)
  assert seen["cv"] is None


# --- the classical scripts on a synthetic legacy tree ----------------------------------

REJECT_AT = 7    # stimulus-window index (trial 1 of class 101) made unusable: ids must NOT shift (PF-03)
BAD_PRE_ROWS = 20   # tests.p05_synth puts 20 rest rows (201) before the stimulus windows


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
  root = tmp_path_factory.mktemp("p11tree")
  write_subject(root, "S03", n_trials=3, seed=3, snr=0.12)
  x = np.load(root / "S03" / "X_time_windows.npy")
  x[BAD_PRE_ROWS + REJECT_AT] *= 50.0     # Vpp far above 120 uV on every channel: rejected by the window gate
  np.save(root / "S03" / "X_time_windows.npy", x)
  # S05: one stimulus window missing from the saved arrays (lost to the raw gate): block of 14, ids approximate
  write_subject(root, "S05", n_trials=3, seed=5, snr=0.12)
  for name in ("X_time_windows", "X_psd_features", "y_labels"):
    a = np.load(root / "S05" / f"{name}.npy")
    np.save(root / "S05" / f"{name}.npy", np.delete(a, BAD_PRE_ROWS + REJECT_AT, axis=0))
  return root


def _run_all(tree, out, cv, sm):
  common = ["--reports-dir", str(out), "--cv", cv, "--smoothing", sm]
  assert bns.main(["--data-root", str(tree), *common]) == 0
  assert bcv.main(["--subject", "S03", "--processed-dir", str(tree), *common]) == 0
  assert bfs.main(["--subject", "S03", "--processed-dir", str(tree), "--k-features", "10", "--sfs-features", "3", *common]) == 0
  assert bhf.main(["--subject", "S03", "--processed-dir", str(tree), "--no-figures", *common]) == 0
  assert ecm.main(["--subject", "S03", "--processed-dir", str(tree), "--no-figures", *common]) == 0


@pytest.fixture(scope="module")
def grouped_run(tree, tmp_path_factory):
  """All five classical scripts in grouped mode with a spy on every split they request."""
  import src.preprocessing.dataset.cv_utils as mod
  calls, orig = [], mod.make_splits

  def spy(cv, y, trial_ids, seed=42):
    s = orig(cv, y, trial_ids, seed)
    calls.append((cv, np.asarray(trial_ids) if trial_ids is not None else None, s))
    return s

  out = tmp_path_factory.mktemp("grouped")
  mp = pytest.MonkeyPatch()
  mp.setattr(mod, "make_splits", spy)
  try:
    _run_all(tree, out, "grouped", "trial")
  finally:
    mp.undo()
  return out, calls


def test_every_classical_script_uses_trial_grouped_splits(grouped_run):
  out, calls = grouped_run
  assert len(calls) >= 5   # n_subjects x2 subjects, cross_validation, feature_selection, harmonic, flagship
  for cv, ids, splits in calls:
    assert cv == "grouped" and ids is not None
    cu.assert_no_shared_trials(splits, ids)
  assert (out / "n_subjects_benchmark.csv").is_file() and not (out / "legacy_leaky").exists()


def test_prepare_subject_trial_ids_are_pre_gate_then_masked(tree):
  b = br.prepare_subject(tree, "S03", None, 250.0)
  assert b["n_rejected"] == 1
  expect = 10 + np.arange(75) // 5          # 10 ids of the 201 rows, then 15 stimulus trials of 5 windows
  expect = np.delete(expect, REJECT_AT)
  assert np.array_equal(b["trial_ids"], expect) and len(b["trial_ids"]) == len(b["y"])
  assert not b["trial_ids_approximate"]     # the gate ran after the ids: still exact (only raw-file losses make ids approximate)
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    bug = cu.build_trial_ids(b["y"], 5)
  assert not np.array_equal(bug, b["trial_ids"] - 10)   # ids built after the gate would shift later trials


def test_trial_ids_approximate_when_a_window_is_missing_from_the_saved_arrays(tree):
  b = br.prepare_subject(tree, "S05", None, 250.0)
  assert b["trial_ids_approximate"] and b["trial_block_report"]["truncated"] == [(101, 0, 14)]
  assert b["trial_block_report"]["blocks"][101] == [14]


def test_trial_ids_exact_when_nothing_is_rejected(tmp_path):
  write_subject(tmp_path, "S04", n_trials=3, seed=4, snr=0.12)
  b = br.prepare_subject(tmp_path, "S04", None, 250.0)
  assert not b["trial_ids_approximate"] and b["n_trials"] == 15
  assert np.array_equal(b["trial_ids"], 10 + np.arange(75) // 5)


# legacy regression: sha256 of the CSV/TXT outputs of the pre-P11 scripts (same synthetic tree as below,
# saga models seeded) -- `--cv legacy --smoothing mod5` must reproduce them byte for byte.
LEGACY_PINS = {
  "classification_report_benchmark_harmonic_fbcca_S03.txt": "8a9d2cc597cba8d8ec9ca2bcfc60c82207d626a07e483bdca86aa48a259bbc9a",
  "classification_report_evaluate_confusion_matrix_S03.txt": "b3d4a1238e4129e6b731611f35aef6663a8cffad21a175a4d9d2cb4886c4cd28",
  "classification_report_evaluate_confusion_matrix_S03_smoothed_mod5.txt": "1289afe3e0772aef37ec746faaa55460e3538ac9a3a322e62b6952f728a07356",
  "classification_report_evaluate_confusion_matrix_S03_smoothed_noreset.txt": "7fafc186fc4270bb362ffb725ae466bde32ba4b611b52b697f3343948ca0741e",
  "feature_selection_ablation_S03.csv": "ee1709d2a3e6a655c88333c582092e87b52f487f03017c686e4ce991cc661f0e",
  "feature_space_benchmark_S03.csv": "8c228cae492a0e5015f244cc321f3ff3743aaadcace82202b9617bb2fb8829ef",
  "flagship_S03.csv": "e71f41bf97f50386b489eeba56df360a670605b7faffe05d76a4b32f91b6bab2",
  "n_subjects_benchmark.csv": "9ec74a37620b37193b29f981887fc77e248921b52c9f577e4f6a04cdb1220d73",
}


def test_legacy_mode_is_byte_identical_to_pre_p11_and_writes_under_legacy_leaky(tmp_path):
  root = tmp_path / "tree"
  for s, seed in (("S03", 3), ("S04", 4)):
    write_subject(root, s, n_trials=4, seed=seed, snr=0.12)
  out = tmp_path / "reports"
  _run_all(root, out, "legacy", "mod5")
  leg = out / "legacy_leaky"
  assert {p.name for p in out.iterdir()} == {"legacy_leaky"}
  got = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in leg.iterdir()
         if p.suffix in (".csv", ".txt") and not p.name.endswith(".meta.txt")}
  assert got == LEGACY_PINS
  meta = (leg / "n_subjects_benchmark.meta.txt").read_text()
  assert "StratifiedKFold(5, shuffle, 42) over windows" in meta and "trial_ids_approximate subjects" in meta


def test_grouped_meta_names_splitter_smoothing_and_approximate_subjects(grouped_run):
  out, _ = grouped_run
  meta = (out / "n_subjects_benchmark.meta.txt").read_text()
  assert "StratifiedGroupKFold" in meta and "trial-aware" in meta
  assert "trial_ids_approximate subjects: S05" in meta
  assert "trial ids:" in (out / "feature_space_benchmark_S03.meta.txt").read_text()
  assert "SFS inner CV: StratifiedGroupKFold" in (out / "feature_selection_ablation_S03.meta.txt").read_text()


# --- demo_cv_leakage (P11.4) --------------------------------------------------------------

def test_demo_cv_leakage_columns_mean_row_and_network_section(tree, tmp_path, capsys):
  import pandas as pd
  from scripts.diagnostics import demo_cv_leakage as demo
  rep = tmp_path / "reports"
  (rep / "legacy_leaky").mkdir(parents=True)
  hdr = "Subject,Clean Windows,1.0s OFF (%),1.0s ON (%),1.0s Delta,2.0s OFF (%),2.0s ON (%),2.0s Delta\n"
  (rep / "legacy_leaky" / "augmentation_ab_eegnet.csv").write_text(hdr + "S03,75,60.0,70.0,10.0,65.0,75.0,10.0\nMean,75,60.0,70.0,10.0,65.0,75.0,10.0\n")
  (rep / "augmentation_ab_eegnet.csv").write_text(hdr + "S03,75,30.0,31.0,1.0,35.0,36.0,1.0\nMean,75,30.0,31.0,1.0,35.0,36.0,1.0\n")
  assert demo.main(["--data-root", str(tree), "--subjects", "S03", "S05", "--reports-dir", str(rep)]) == 0
  df = pd.read_csv(rep / "cv_leakage_demo.csv")
  assert list(df.columns) == demo.COLUMNS and df["Subject"].tolist() == ["S03", "S05", "Mean"]
  assert df.loc[df.Subject == "S05", "Approximate ids"].item() == "yes"
  for _, r in df.iloc[:2].iterrows():
    assert r["Delta 1.0 (pp)"] == pytest.approx(r["1.0s grouped (%)"] - r["1.0s leaky (%)"], abs=0.011)
  assert df.iloc[-1]["1.0s leaky (%)"] == pytest.approx(df.iloc[:2]["1.0s leaky (%)"].mean(), abs=0.006)
  net = pd.read_csv(rep / "cv_leakage_demo_networks.csv")
  assert net.loc[net.Subject == "S03", "Delta OFF 1.0"].item() == pytest.approx(-30.0)
  assert net.loc[net.Subject == "S03", "Augmentation gain 1.0 grouped"].item() == pytest.approx(1.0)
  assert "compact_cnn skipped" in capsys.readouterr().out
