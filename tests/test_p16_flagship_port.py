"""P16.7 flagship port: legacy root identical to the pre-port code, built root on the saved bands, N1, PF-04, R1/R8.

Synthetic folders only (`p05_synth` legacy, `p16_synth` built); no generated or ignored file is read.
"""

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks.feature_based import benchmark_n_subjects as B
from src.features.ssvep import fbcca_extraction as FC
from src.features.ssvep import fbcsp_extraction as FS
from src.io import subject_data as SD
from src.models.classical import legacy_eval as le
from src.models.classical.benchmark_runner import prepare_subject
from src.models.classical.feature_spaces import benchmark_spaces
from src.models.classical.sklearn_models import get_sklearn_model_suite
from src.preprocessing.dataset.smoothing import smooth_probabilities_by_trial
from tests import p05_synth, p16_synth as S

TH = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}


@pytest.fixture(scope="module")
def legacy(tmp_path_factory):
  root = tmp_path_factory.mktemp("legacy_port")
  p05_synth.write_subject(root, "S03", n_trials=6)
  p05_synth.write_subject(root, "S04", n_trials=6, bad_channels=("O1",), seed=3)
  return root


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  root = tmp_path_factory.mktemp("built_port")
  S.write_built_subject(root, "S01", n_trials=10, seed=1)
  S.write_built_subject(root, "S02", n_trials=10, seed=2, spike_s=57.5, bad_channel="O2")
  return root


def pre_port(root, subject, cv="grouped", smoothing="mod5", seed=42):
  """The pre-port flow (P11): prepare_subject -> benchmark_spaces -> oof_space -> accuracies."""
  b = prepare_subject(root, subject, None, 250.0)
  space = [s for s in benchmark_spaces(b, 1) if s.name == B.SPACE][0]
  res, _ = le.oof_space(space, b["subbands"], b["y"], {B.MODEL: get_sklearn_model_suite(seed)[B.MODEL]}, seed,
                        le.splits_for(cv, b["y"], b["trial_ids"], seed))
  a1, a2 = le.accuracies(b["y"], res[B.MODEL]["pred"], res[B.MODEL]["scores"], b["trial_ids"], smoothing)
  return b, round(100 * a1, 2), round(100 * a2, 2)


@pytest.mark.parametrize("subject", ["S03", "S04"])
def test_legacy_root_defaults_equal_pre_port_code(legacy, subject):
  b, a1, a2 = pre_port(legacy, subject)
  out = B.evaluate_subject(legacy, subject, thresholds=TH, fail_fraction=0.5)
  r = out["row"]
  assert (r["1.0s Acc (%)"], r["2.0s Smoothed (%)"]) == (a1, a2)
  assert r["Clean Windows"] == b["n_clean"] and r["Rejected Windows"] == b["n_rejected"]
  assert r["Channels Dropped"] == (" ".join(b["channels_dropped"]) or "none")
  assert list(r) == B.COLUMNS                      # the legacy CSV layout, no Bank/SD columns
  # the feature matrices themselves are identical (not just the accuracies)
  d = SD.load_subject(legacy / subject, thresholds=TH, channel_fail_fraction=0.5)
  space, sub = B.feature_blocks(d, 1)
  assert np.array_equal(space.static[0], b["fbcca"]) and np.array_equal(sub, b["subbands"])


def test_legacy_root_cv_legacy_and_trial_smoothing_still_match(legacy):
  _, a1, a2 = pre_port(legacy, "S04", cv="legacy", smoothing="trial")
  r = B.evaluate_subject(legacy, "S04", cv="legacy", smoothing="trial", thresholds=TH)["row"]
  assert (r["1.0s Acc (%)"], r["2.0s Smoothed (%)"]) == (a1, a2)


def test_main_writes_the_legacy_csv_without_suffix(legacy, tmp_path):
  rc = B.main(["--data-root", str(legacy), "--reports-dir", str(tmp_path)])
  assert rc == 0
  df = pd.read_csv(tmp_path / "n_subjects_benchmark.csv")
  assert list(df.columns) == B.COLUMNS and list(df["Subject"]) == ["S03", "S04", "Mean"]
  _, a1, _ = pre_port(legacy, "S03")
  assert df.loc[0, "1.0s Acc (%)"] == a1


@pytest.mark.parametrize("subject", ["S01", "S02"])
def test_built_root_uses_saved_bands_and_trial_reset_smoothing(built, subject, monkeypatch):
  def boom(*a, **k):
    raise AssertionError("a built folder must not be refiltered (R3)")
  monkeypatch.setattr(B, "filter_subbands", boom)
  monkeypatch.setattr(FC, "get_chebyshev_subbands", boom)
  monkeypatch.setattr(FC, "filtfilt", boom)
  out = B.evaluate_subject(built, subject, thresholds=TH)
  r = out["row"]
  assert list(r)[:7] == ["Subject", "Channels Kept", "Channels Dropped", "Clean Windows", "Rejected Windows",
                         "Bank", "CSP Bands"]
  assert r["Channels Kept"] == (8 if subject == "S01" else 7)
  # independent recomputation from the loader output
  d = SD.load_subject(built / subject, bands=("fbcca", "fbcsp"))
  assert r["Clean Windows"] == len(d["y"])
  assert d["smoothing"] == "trial" and d["fs"] == 256.0
  space, sub = B.feature_blocks(d, 1)
  assert np.array_equal(sub, d["bands"]["fbcsp"])
  res, _ = le.oof_space(space, sub, d["y"], {B.MODEL: get_sklearn_model_suite(42)[B.MODEL]}, 42,
                        le.splits_for("grouped", d["y"], d["cv_groups"], 42))
  sc = res[B.MODEL]["scores"]
  sm = smooth_probabilities_by_trial(sc, d["trial_ids"])
  want2 = round(100 * float(np.mean(np.unique(d["y"])[np.argmax(sm, 1)] == d["y"])), 2)
  assert r["2.0s Smoothed (%)"] == want2
  if subject == "S02":   # rejected windows break the i % 5 blocks here: the legacy rule would differ (PF-02)
    from src.preprocessing.dataset.smoothing import smooth_probabilities_mod5
    assert not np.array_equal(smooth_probabilities_mod5(sc), sm)
  assert r["1.0s Acc (%)"] == round(100 * float(np.mean(res[B.MODEL]["pred"] == d["y"])), 2)


def test_fbcca_features_come_from_the_saved_bands(built):
  d = SD.load_subject(built / "S01", bands=("fbcca",))
  refs = [FC.generate_reference_signals(f, d["fs"], d["X"].shape[-1]) for f in FC.TARGET_FREQS]
  want = np.stack([FC.fbcca_band_scores(b, refs) for b in d["bands"]["fbcca"]])
  X, y, valid, rep = FC.extract_fbcca_features(d["X"], d["y"], d["channel_names"], d["fs"], subband_windows=d["bands"]["fbcca"],
                                               quality=d["quality"])
  assert np.array_equal(X, want) and len(valid) == len(y)
  # planted tones: the right target wins in most windows
  assert np.mean(np.argmax(X, 1) == d["y"] - 101) > 0.8


def test_quality_layouts_full_rows_and_preselected_agree(built):
  conds = (101, 102, 103, 104, 105)
  d = SD.load_subject(built / "S02", conds, bands=("fbcsp",))
  full = SD.load_subject(built / "S02", conds, quality_mode="shared-no-guard", bands=("fbcsp",))
  assert len(full["y"]) > len(d["y"])
  # d["quality"]["valid_mask"] is over the selected rows: applied to the no-guard rows it reproduces d
  rows_ng = SD.load_subject(built / "S02", conds, quality_mode="shared-no-guard")
  assert d["channel_names"] == full["channel_names"]
  q = dict(d["quality"])
  Xs = d["X"]
  a = FS.extract_fbcsp_features(Xs, d["y"], d["channel_names"], d["fs"], subband_windows=d["bands"]["fbcsp"], quality=q)
  assert a[0].shape == (len(d["y"]), 50) and a[2].sum() == len(d["y"])
  with pytest.raises(ValueError):   # a decision is never applied to misaligned rows
    FS.extract_fbcsp_features(Xs[:7], d["y"][:7], d["channel_names"], d["fs"], quality=q)
  assert rows_ng["n_selected"] == d["n_selected"]


def test_cv_repeats_columns_and_seeds(built, legacy):
  r = B.evaluate_subject(legacy, "S04", repeats=3, thresholds=TH)
  row = r["row"]
  assert list(row)[-3:] == B.SD_COLUMNS and row["CV repeats"] == 3
  vals = [pre_port(legacy, "S04", seed=42 + k)[1:] for k in range(3)]
  assert row["1.0s Acc (%)"] == round(float(np.mean([v[0] for v in vals])), 2)
  assert row["1.0s SD"] == round(float(np.std([v[0] for v in vals], ddof=1)), 2)
  assert r["seed0"][0] == vals[0][0]
  df = B.with_mean_row([row])
  assert df.iloc[-1]["CV repeats"] == 3 and df.iloc[-1]["1.0s SD"] == row["1.0s SD"]


def test_suffix_rules(built, legacy, tmp_path):
  assert B.derived_suffix(False, "legacy", "shared", None, 1) == ""
  assert B.derived_suffix(True, "continuous", "shared-no-guard", None, 5) == "continuous_sharednoguard_rep5"
  assert B.derived_suffix(False, "legacy", "shared", 256.0, 1) == "fs256"
  assert B.main(["--data-root", str(built), "--reports-dir", str(tmp_path)]) == 0
  assert (tmp_path / "n_subjects_benchmark_continuous.csv").is_file()
  assert B.main(["--data-root", str(built), "--reports-dir", str(tmp_path), "--out-suffix", "v2cont", "--subjects", "S01"]) == 0
  df = pd.read_csv(tmp_path / "n_subjects_benchmark_v2cont.csv")
  assert list(df["Subject"]) == ["S01", "Mean"] and not (tmp_path / "n_subjects_benchmark.csv").exists()
  assert B.main(["--data-root", str(legacy), "--reports-dir", str(tmp_path), "--fs", "256", "--subjects", "S03"]) == 0
  assert (tmp_path / "n_subjects_benchmark_fs256.csv").is_file()


def test_n1_oof_space_without_splits_raises():
  X = np.random.default_rng(0).normal(size=(40, 3))
  y = np.repeat([101, 102], 20)
  with pytest.raises(ValueError, match="explicit splits"):
    le.oof_space(le.FeatureSpace("n", [X]), None, y, {"m": get_sklearn_model_suite(42)[B.MODEL]})


def test_pf04_tone_scores_depend_on_the_true_fs():
  fs = 256.0
  t = np.arange(256) / fs
  rng = np.random.default_rng(0)
  w = (np.sin(2 * np.pi * 24.0 * t)[None] * np.array([1.0, 0.8, 1.2, 0.9])[:, None] + 0.3 * rng.normal(size=(4, 256)))[None]
  q = {"valid_mask": [1], "channels_kept": list("abcd")}
  X256 = FC.extract_fbcca_features(w, np.array([101]), list("abcd"), 256.0, quality=q)[0][0]
  X250 = FC.extract_fbcca_features(w, np.array([101]), list("abcd"), 250.0, quality=q)[0][0]
  assert np.argmax(X256) == 0 and X256[0] > X250[0] + 0.1      # the 250 Hz literal smears the 24 Hz reference


def test_r1_built_cv_groups_never_straddle_a_fold(built):
  d = SD.load_subject(built / "S02", bands=())
  for seed in (42, 43, 44):
    for tr, te in le.splits_for("grouped", d["y"], d["cv_groups"], seed):
      assert not set(d["cv_groups"][tr]) & set(d["cv_groups"][te])
