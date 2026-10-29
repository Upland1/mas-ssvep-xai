"""P23 ml-engineer carry-forwards (P22 C-1, C-3, C-6; review N2, N8; report W-1) on `benchmark_loso.py` and the warm-up study.

Each test names the old line it fails on."""

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_loso_warmup as WU
from tests.test_p22_loso_extensions import cli


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("p23cf") / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    S.write_built_subject(root, s, n_trials=10, seed=i + 1)
  return root.parent


def test_code_changed_docstring_names_configs():                    # old text: "`src/` or `scripts/` differ"
  doc = inspect.getdoc(L.code_changed)
  assert "configs/" in doc and all(p in doc for p in L.CODE_PATHS)


def test_within_groups_equal_trial_ids_for_stimulus_classes_and_within_lda_receives_groups(built, tmp_path, monkeypatch):
  from src.io.subject_data import load_subject
  d = load_subject(built / "w1_s0.25" / "S01", L.CLASS_CODES, "shared")
  assert np.array_equal(d["trial_ids"], d["cv_groups"])             # identical for 101-105: the swap changes no number
  seen = []
  orig = L.within_lda_fold
  monkeypatch.setattr(L, "within_lda_fold", lambda b, fb, yi, groups, *a, **k: (seen.append(groups.copy()), orig(b, fb, yi, groups, *a, **k))[1])
  assert L.main(cli(built, tmp_path, methods=("within_lda",))) == 0
  assert len(seen) == 3
  # old line passed P["trial"]: make groups differ from trial and see which one reaches within_lda
  src = inspect.getsource(L.run_fold)
  assert 'P["groups"][rows], args.folds' in src and 'P["trial"][rows], args.folds' not in src


def test_within_lda_gets_cv_groups_not_trial_ids_when_they_differ(monkeypatch):
  from tests.test_p21_loso import make_subject
  from types import SimpleNamespace
  d = make_subject("S01", 3, n_trials=10, wpt=5)
  d["cv_groups"] = d["trial_ids"] + 500                              # planted difference (as a 202 row would give)
  P = L.pool([d], ["fbcsp"])
  seen = []
  monkeypatch.setattr(L, "within_lda_fold", lambda b, fb, yi, groups, *a, **k: (seen.append(groups), {
    "proba": np.zeros((1, len(yi), 5)), "train_acc": 0.0, "n_train": 1})[1])
  L.run_fold("within_lda", P, 0, SimpleNamespace(folds=2, within_repeats=1, seed=42), "cpu")
  assert np.array_equal(seen[0], P["groups"]) and not np.array_equal(seen[0], P["trial"])


def test_within_lda_data_source_says_within_subject_and_loso_rows_keep_loso(built, tmp_path):
  assert L.main(cli(built, tmp_path)) == 0
  s = pd.read_csv(tmp_path / "summary.csv")
  w, lo = s[s["Method"] == "within_lda"], s[s["Method"] == "lda"]
  assert w["Data source"].str.contains("within-subject").all() and not w["Data source"].str.contains("LOSO").any()
  assert lo["Data source"].str.contains("LOSO").all() and not lo["Data source"].str.contains("within-subject").any()
  assert w["Data source"].str.contains(r"\| 3 held-out subjects").sum() == 2          # Mean and SD rows keep the suffix


def test_fold_config_records_training_counts_build_commits_and_config_hash(built, tmp_path):
  assert L.main(cli(built, tmp_path, methods=("lda", "within_lda"))) == 0
  _, c = L.load_fold(L.fold_path(tmp_path, "lda", "S02"))
  assert set(c["n_windows_train"]) == {"S01", "S03"} and all(v > 0 for v in c["n_windows_train"].values())
  assert set(c["build_git_commits"]) == {"S01", "S02", "S03"} and all(isinstance(v, str) and v for v in c["build_git_commits"].values())
  assert c["config_hash"] == L.file_sha256(L.ROOT / "configs" / "pipeline_config.yaml") and len(c["config_hash"]) == 64
  _, w = L.load_fold(L.fold_path(tmp_path, "within_lda", "S02"))
  assert set(w["n_windows_train"]) == {"S02"} and set(w["build_git_commits"]) == {"S02"}


def test_rerun_refused_when_a_training_window_count_a_build_commit_or_the_config_file_changes(built, tmp_path):
  import copy
  assert L.main(cli(built, tmp_path, methods=("lda",))) == 0
  p = L.fold_path(tmp_path, "lda", "S01")
  _, saved = L.load_fold(p)
  for key, new in (("n_windows_train", {"S02": 1, "S03": 1}), ("build_git_commits", {"S01": "z", "S02": "z", "S03": "z"}),
                   ("config_hash", "f" * 64)):
    with pytest.raises(SystemExit, match="use a new --out-dir") as e:
      L.check_fold(p, saved, {**copy.deepcopy(saved), key: new})
    assert key in str(e.value)
  # end to end: a different --config file (same content but one comment byte) is refused
  cfg2 = tmp_path / "cfg.yaml"
  cfg2.write_text((L.ROOT / "configs" / "pipeline_config.yaml").read_text() + "\n# changed\n")
  with pytest.raises(SystemExit, match="config_hash"):
    L.main(cli(built, tmp_path, "--config", str(cfg2), methods=("lda",)))


def test_provenance_helpers_are_reusable_by_other_harnesses(tmp_path):
  f = tmp_path / "c.yaml"
  f.write_text("a: 1\n")
  loaded = [{"subject": s, "y": np.zeros(n), "meta": {"git_commit": g}} for s, n, g in (("S01", 3, "aa"), ("S02", 5, "bb"), ("S03", 7, None))]
  loaded[2]["meta"] = {}
  prov = L.cohort_provenance(loaded, f)
  assert prov["n_windows"] == {"S01": 3, "S02": 5, "S03": 7} and prov["build_commits"]["S03"] == "unknown"
  assert L.provenance_fields(prov, ["S02", "S03"], "S01") == {
    "n_windows_train": {"S02": 5, "S03": 7}, "build_git_commits": {"S02": "bb", "S03": "unknown", "S01": "aa"},
    "config_hash": L.file_sha256(f)}


def test_warmup_csvs_carry_the_normalization_label(built, tmp_path):
  out = tmp_path / "w"
  assert WU.main(["--data-root", str(built), "--out-dir", str(out), "--warmup-trials", "1", "2"]) == 0
  s, coh = pd.read_csv(out / "summary.csv"), pd.read_csv(out / "cohort.csv")
  assert list(s.columns)[-2:] == ["Data source", "Normalization"]                  # after the earlier columns
  for df in (s, coh):
    assert df["Normalization"].notna().all()
    t = df["Normalization"].iloc[0]
    assert "offline upper bound" in t and "online" in t and "none" in t and "test-time" in t
