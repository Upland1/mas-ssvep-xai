"""P17.3: `--bank` and `--classes {5,6}` of benchmark_n_subjects, the 6-class metrics, C-2.

Synthetic folders only (`p05_synth` legacy, `p16_synth` built with the real build code); no generated or ignored file is read.
"""

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks.feature_based import benchmark_n_subjects as B
from src.io import subject_data as SD
from src.models.classical import rest_metrics as RM
from src.preprocessing.dataset.smoothing import smooth_probabilities_by_trial
from tests import p05_synth, p16_synth as S

TH = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}
ALL_BANKS = ("fbcca", "fbcsp", "harmonic", "intermediate")
REST_COLS = ["Rest Windows", "1.0s BalAcc (%)", "2.0s BalAcc (%)", "1.0s FalseAct (%)", "2.0s FalseAct (%)",
             "1.0s Missed (%)", "2.0s Missed (%)", "2.0s StimCorrect (%)"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  root = tmp_path_factory.mktemp("built_p17")
  S.write_built_subject(root, "S01", n_trials=10, seed=1, banks=ALL_BANKS)
  S.write_built_subject(root, "S02", n_trials=10, seed=2, banks=ALL_BANKS)
  return root


@pytest.fixture(scope="module")
def legacy(tmp_path_factory):
  root = tmp_path_factory.mktemp("legacy_p17")
  p05_synth.write_subject(root, "S03", n_trials=6)
  return root


def load(root, subject, bank="base", classes=5):
  return SD.load_subject(root / subject, SD.CLASS_CODES + ((201,) if classes == 6 else ()), "shared",
                         bands=("fbcca", "fbcsp") + B.EXTRA_BANKS[bank], thresholds=TH, channel_fail_fraction=0.5)


# --- bank ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bank,extra", [("base", ()), ("harm", ("harmonic",)), ("harm+mid", ("harmonic", "intermediate"))])
def test_bank_band_counts_and_order_are_base_plus_listed_bands(built, bank, extra):
  d = load(built, "S01", bank)
  _, sub = B.feature_blocks(d, 1, bank)
  n_listed = [len(d["meta"]["bands"][b]) for b in ("fbcsp",) + extra]
  assert (n_listed[0], sub.shape[1]) == (5, sum(n_listed))
  assert len(d["meta"]["bands"]["harmonic"]) == 14 and len(d["meta"]["bands"]["intermediate"]) == 4   # 60 Hz band skipped
  # R6: columns are fbcsp, then harmonic, then intermediate, each in the order of the saved array
  at = 5
  assert np.array_equal(sub[:, :5], d["bands"]["fbcsp"])
  for b in extra:
    n = d["bands"][b].shape[1]
    assert np.array_equal(sub[:, at:at + n], d["bands"][b])
    at += n
  assert len(B.bank_bands_text(d, bank).split()) == sub.shape[1]
  assert sub.shape[1] == {"base": 5, "harm": 19, "harm+mid": 23}[bank]


def test_bank_text_follows_the_metadata_band_edges(built):
  d = load(built, "S01", "harm+mid")
  txt = B.bank_bands_text(d, "harm+mid").split()
  hb = d["meta"]["bands"]["harmonic"]
  assert txt[5] == f"{hb[0]['low']:g}-{hb[0]['high']:g}" and txt[5] == "23-25"   # first harmonic centre 24 Hz
  assert txt[-4] == "8.74-10.74"                                                  # first midpoint 9.74 Hz


def test_bank_row_labels_and_feature_width(built):
  out = B.evaluate_subject(built, "S01", thresholds=TH, bank="harm")
  r = out["row"]
  assert r["Bank"] == "fbcca+harm" and len(r["CSP Bands"].split()) == 19
  assert "p=" in out["log"] and "p=" + str(5 * 2 * 19 + 5) in out["log"]
  base = B.evaluate_subject(built, "S01", thresholds=TH)["row"]
  assert base["Bank"] == "fbcca" and len(base["CSP Bands"].split()) == 5
  assert list(base) == B.BASE_COLUMNS + B.BUILT_COLUMNS + B.ACC_COLUMNS   # the P16 built layout is unchanged


def test_bank_on_a_legacy_root_raises(legacy):
  with pytest.raises(ValueError, match="built folder"):
    B.evaluate_subject(legacy, "S03", thresholds=TH, fail_fraction=0.5, bank="harm")


# --- 6 classes ------------------------------------------------------------------------------------------------------

def test_six_classes_select_201_and_never_202_and_groups_are_true_ids(built):
  d = load(built, "S01", classes=6)
  raw = np.load(built / "S01" / "y_labels.npy")
  assert (raw == 202).any()                                  # the folder has cue windows ...
  assert set(np.unique(d["y"])) == {101, 102, 103, 104, 105, 201} and 202 not in d["y"]   # ... they never enter
  assert np.array_equal(d["cv_groups"], d["trial_ids"])
  rest = d["y"] == 201
  assert rest.sum() == 20 and len(np.unique(d["trial_ids"][rest])) == 10   # 2 windows per 201 trial
  assert not set(d["trial_ids"][rest]) & set(d["trial_ids"][~rest])         # no trial id shared by rest and stimulus


def test_six_class_priors_are_uniform_and_five_class_unchanged():
  assert np.allclose(B.make_model(42, 6).priors, np.full(6, 1 / 6))
  assert B.make_model(42, 5).priors is None                                 # flagship default untouched


def test_six_class_lda_uses_the_uniform_prior_in_the_fitted_model(built):
  d = load(built, "S01", classes=6)
  space, sub = B.feature_blocks(d, 1)
  from sklearn.pipeline import Pipeline
  from sklearn.preprocessing import StandardScaler
  from src.models.classical.legacy_eval import fold_matrices
  idx = np.arange(len(d["y"]))
  Xtr, _ = fold_matrices(space, sub, d["y"], idx, idx)
  m = Pipeline([("s", StandardScaler()), ("c", B.make_model(42, 6))]).fit(Xtr, d["y"])
  assert np.allclose(m[-1].priors_, 1 / 6)                                  # 201 has 20 windows, a stimulus 16: not the frequencies


def test_six_classes_on_a_legacy_root_raise(legacy):
  with pytest.raises(ValueError, match="built folder"):
    B.evaluate_subject(legacy, "S03", thresholds=TH, fail_fraction=0.5, classes=6)
  assert B.main(["--data-root", str(legacy), "--classes", "6", "--reports-dir", str(legacy / "r")]) == 1


def test_rest_trials_are_smoothed_inside_their_trial_only(built):
  d = load(built, "S01", classes=6)
  scores = np.random.default_rng(0).random((len(d["y"]), 6))
  sm = smooth_probabilities_by_trial(scores, d["trial_ids"])
  ids, rest = d["trial_ids"], np.flatnonzero(d["y"] == 201)
  first = [i for i in rest if i == 0 or ids[i] != ids[i - 1]]
  second = [i for i in rest if i > 0 and ids[i] == ids[i - 1]]
  assert len(first) == 10 and len(second) == 10
  assert np.allclose(sm[first], scores[first])                              # a 201 trial restarts (R8)
  assert np.allclose(sm[second], (scores[np.array(second) - 1] + scores[second]) / 2)


def test_six_class_run_columns_sd_confusion(built):
  out = B.evaluate_subject(built, "S01", thresholds=TH, classes=6, repeats=2)
  r = out["row"]
  assert list(r) == (B.BASE_COLUMNS + B.BUILT_COLUMNS + B.ACC_COLUMNS + B.SD_COLUMNS + [REST_COLS[0]] + REST_COLS[1:]
                     + B.REST_SD_COLUMNS)
  assert r["Rest Windows"] == 20 and r["Clean Windows"] + r["Rejected Windows"] == 20 + 50
  cls, cm = out["confusion"]
  assert cls == [101, 102, 103, 104, 105, 201]
  assert cm.sum() == 2 * r["Clean Windows"]                                 # every window predicted once per repeat
  assert cm[-1].sum() == 2 * 20                                             # rows = true class
  assert r["2.0s StimCorrect (%)"] + r["2.0s Missed (%)"] <= 100.0 + 1e-9


# --- metrics --------------------------------------------------------------------------------------------------------

def test_rest_metrics_equal_hand_values_and_the_two_rates_are_not_swapped():
  y = np.array([201] * 4 + [101] * 2 + [102] * 2)
  pred = np.array([201, 101, 102, 201, 101, 201, 102, 102])
  m = RM.rest_metrics(y, pred)
  assert m["FalseAct"] == 50.0                       # 2 of 4 rest windows predicted as a stimulus
  assert m["Missed"] == 25.0                         # 1 of 4 stimulus windows predicted as rest
  assert m["StimCorrect"] == 75.0                    # 3 of 4 stimulus windows predicted as their own stimulus
  assert m["BalAcc"] == pytest.approx(100 * (0.5 + 0.5 + 1.0) / 3)
  cm = RM.confusion_counts(y, pred, [101, 102, 201])
  assert cm.tolist() == [[1, 0, 1], [0, 2, 0], [1, 1, 2]]
  assert cm.sum() == 8 and cm.diagonal().sum() == 5


def test_stimulus_to_other_stimulus_is_neither_missed_nor_correct():
  y = np.array([201, 101, 101, 101])
  pred = np.array([201, 102, 102, 101])
  m = RM.rest_metrics(y, pred)
  assert (m["FalseAct"], m["Missed"]) == (0.0, 0.0) and m["StimCorrect"] == pytest.approx(100 / 3)


def test_perfect_predictions_give_100_and_0():
  y = np.array([201, 201, 101, 102])
  m = RM.rest_metrics(y, y)
  assert (m["BalAcc"], m["FalseAct"], m["Missed"], m["StimCorrect"]) == (100.0, 0.0, 0.0, 100.0)


# --- C-2 ------------------------------------------------------------------------------------------------------------

def test_no_threshold_fallback(built, legacy):
  assert not hasattr(B, "GATE_THRESHOLDS") and "GATE_THRESHOLDS" not in inspect.getsource(B)
  with pytest.raises(ValueError, match="thresholds are required"):
    B.evaluate_subject(built, "S01")
  with pytest.raises(ValueError, match="thresholds are required"):
    B.evaluate_subject(legacy, "S03")


def test_fs_on_a_built_root_needs_the_flag(built, tmp_path):
  with pytest.raises(ValueError, match="allow-fs-override"):
    B.evaluate_subject(built, "S01", thresholds=TH, fs=250.0)
  assert B.main(["--data-root", str(built), "--fs", "250", "--reports-dir", str(tmp_path)]) == 1
  assert not list(tmp_path.glob("*.csv"))
  r = B.evaluate_subject(built, "S01", thresholds=TH, fs=250.0, allow_fs_override=True)
  assert r["row"] is not None and "fs 250 (override)" in r["log"]
  assert B.evaluate_subject(built, "S01", thresholds=TH)["row"] is not None   # default: metadata fs


def test_fs_on_a_legacy_root_is_still_allowed(legacy):
  assert B.evaluate_subject(legacy, "S03", thresholds=TH, fail_fraction=0.5, fs=256.0)["row"] is not None


# --- suffixes and the CLI --------------------------------------------------------------------------------------------

def test_derived_suffixes_for_the_six_runs():
  s = lambda bank, c: B.derived_suffix(True, "continuous", "shared", None, 10, bank, c)
  names = {s(b, c) for b in B.BANKS for c in (5, 6)}
  assert len(names) == 6 and sum("6class" in n for n in names) == 3
  assert s("base", 5) == "continuous_rep10"                                 # the P16 name is unchanged
  assert s("harm+mid", 6) == "continuous_harmmid_6class_rep10"
  assert B.derived_suffix(False, None, "shared", None, 1) == ""             # legacy default: no suffix


def test_main_six_classes_writes_both_csvs(built, tmp_path):
  rc = B.main(["--data-root", str(built), "--bank", "harm", "--classes", "6", "--cv-repeats", "2",
               "--out-suffix", "t_harm_6class", "--reports-dir", str(tmp_path)])
  assert rc == 0
  df = pd.read_csv(tmp_path / "n_subjects_benchmark_t_harm_6class.csv")
  assert list(df["Subject"]) == ["S01", "S02", "Mean"]
  assert all(c in df.columns for c in REST_COLS + B.REST_SD_COLUMNS)
  assert df.loc[2, "2.0s BalAcc (%)"] == pytest.approx(df.loc[:1, "2.0s BalAcc (%)"].mean(), abs=0.006)
  cf = pd.read_csv(tmp_path / "n_subjects_benchmark_t_harm_6class_confusion.csv")
  assert list(cf.columns) == ["Subject", "True", "101", "102", "103", "104", "105", "201", "CV repeats"]
  assert list(cf["Subject"].unique()) == ["S01", "S02", "Sum"] and len(cf) == 18
  both = cf[cf["Subject"] != "Sum"][["101", "102", "103", "104", "105", "201"]].to_numpy().sum()
  assert cf[cf["Subject"] == "Sum"][["101", "102", "103", "104", "105", "201"]].to_numpy().sum() == both
  assert "harm" in (tmp_path / "n_subjects_benchmark_t_harm_6class.meta.txt").read_text()


def test_main_five_class_built_run_has_no_six_class_columns_or_confusion_file(built, tmp_path):
  assert B.main(["--data-root", str(built), "--reports-dir", str(tmp_path)]) == 0
  csv = tmp_path / "n_subjects_benchmark_continuous.csv"
  assert list(pd.read_csv(csv).columns) == B.BASE_COLUMNS + B.BUILT_COLUMNS + B.ACC_COLUMNS
  assert not list(tmp_path.glob("*confusion*"))
