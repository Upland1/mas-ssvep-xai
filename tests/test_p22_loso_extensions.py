"""P22.1-P22.3 tests: `within_lda`, explicit `--channels <names>`, fold configuration / `check_fold`, fold-count guard.

Known answers on planted synthetic data; each fix test names the bug it guards and a variant that fails it.
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_window_sweep as W
from src.features.ssvep.fbcsp_extraction import FBCSPTransformer
from tests.test_p21_loso import C, FS, T, make_subject

NAMES8 = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]


def one_subject(seed=3, n_trials=20, wpt=5, **kw):
  d = make_subject("S01", seed, n_trials=n_trials, wpt=wpt, **kw)
  P = L.pool([d], ["fbcsp"])
  return d, P


# P22.1 within_lda -----------------------------------------------------------------------------------------------------

def independent_within(bands, fb, yi, groups, folds, repeats, seed, K):
  """Reference computed in the test: grouped CV, CSP + FBCCA features per fold, sklearn pipeline built by hand."""
  out = np.zeros((repeats, len(yi), K))
  for r in range(repeats):
    sp = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed + r).split(np.zeros(len(yi)), yi, groups)
    for tr, te in sp:
      csp = FBCSPTransformer(1).fit(bands[tr], yi[tr])
      f = lambda i: np.hstack([csp.transform(bands[i]), fb[i]])
      pipe = Pipeline([("s", StandardScaler()), ("l", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))])
      pipe.fit(f(tr), yi[tr])
      out[r, te] = pipe.predict_proba(f(te))
  return out


def test_within_lda_equals_an_independent_grouped_cv_lda_and_is_far_above_chance():
  d, P = one_subject(snr=0.8)
  got = L.within_lda_fold(P["bands"]["fbcsp"], P["fb"], P["yi"], P["trial"], folds=3, repeats=2, seed=42, n_classes=5)
  ref = independent_within(P["bands"]["fbcsp"], P["fb"], P["yi"], P["trial"], 3, 2, 42, 5)
  assert got["proba"].shape == (2, len(P["yi"]), 5)
  assert np.allclose(got["proba"], ref, atol=1e-10)
  assert np.allclose(got["proba"].sum(2), 1) and min(got["acc"]) > 0.9           # planted variance: class c in channel c


def trial_signature_subject():
  """Labels random per trial and NO class information in the features; every trial has its own channel gains, shared by its
  windows. Only a split that lets a trial's windows sit on both sides can 'classify' (the PF-01 leak)."""
  d = make_subject("S01", 9, n_trials=30, wpt=6, snr=0.0, fb_sinus=False)
  rng = np.random.default_rng(1)
  gain = rng.uniform(0.2, 4.0, (30, C))
  g = gain[d["trial_ids"]]
  d["bands"]["fbcsp"] = d["bands"]["fbcsp"] * g[:, None, :, None]
  d["fb"] = np.random.default_rng(2).normal(size=d["fb"].shape)                  # no class information either
  return d, L.pool([d], ["fbcsp"])


def test_within_lda_is_grouped_by_trial_and_the_window_level_variant_leaks():
  """R1 / PF-01: with trial signatures and random labels the grouped accuracy is chance (~0.2); a window-level StratifiedKFold
  version of the same fold loop (the bug) reads the signature and scores far above it."""
  d, P = trial_signature_subject()
  b, fb, yi, tid = P["bands"]["fbcsp"], P["fb"], P["yi"], P["trial"]
  grouped = L.within_lda_fold(b, fb, yi, tid, 5, 2, 42, 5)
  assert np.mean(grouped["acc"]) < 0.35
  leaky = np.zeros(len(yi), dtype=int)
  for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(yi)), yi):
    leaky[te] = L.lda_loso_fold(b, fb, yi, np.zeros(len(yi), int), tr, te)["proba"].argmax(1)
  assert np.mean(leaky == yi) > np.mean(grouped["acc"]) + 0.25


def test_within_splits_never_share_a_trial_and_cover_every_window_once():
  d, P = one_subject()
  for r in range(3):
    sp = L.within_splits(P["yi"], P["trial"], 5, 42 + r)
    te = np.concatenate([t for _, t in sp])
    assert np.array_equal(np.sort(te), np.arange(len(P["yi"])))
    for tr, t in sp:
      assert not set(P["trial"][tr]) & set(P["trial"][t])
  a, b = L.within_splits(P["yi"], P["trial"], 5, 42), L.within_splits(P["yi"], P["trial"], 5, 43)
  assert any(not np.array_equal(x[1], y[1]) for x, y in zip(a, b))              # repeat r uses random_state 42 + r
  tr, te = a[0]
  bad = np.union1d(tr, np.flatnonzero(P["trial"] == P["trial"][te[0]]))
  with pytest.raises(AssertionError):                                          # the guard itself detects a straddling trial
    L.assert_no_shared_trials([(bad, te)], P["trial"])


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("p22") / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    S.write_built_subject(root, s, n_trials=10, seed=i + 1)
  return root.parent


def cli(root, out, *extra, methods=("fbcca", "lda", "within_lda")):
  return ["--data-root", str(root), "--out-dir", str(out), "--methods", *methods, "--folds", "2", "--within-repeats", "2", *extra]


def test_within_lda_uses_the_loso_channels_and_records_its_configuration(built, tmp_path):
  assert L.main(cli(built, tmp_path)) == 0
  s = pd.read_csv(tmp_path / "summary.csv")
  w, lo = s[s["Method"] == "within_lda"], s[s["Method"] == "lda"]
  assert (w["Channels"].values == lo["Channels"].values).all()                # same channel string as the LOSO method
  sub = w[w["Subject"].str.fullmatch(r"S\d+")]
  assert (sub["Runs"] == 2).all() and (sub["Acc SD"] >= 0).all() and (sub["Folds"] == 1).all()
  _, cfg = L.load_fold(L.fold_path(tmp_path, "within_lda", "S02"))
  _, cfg_lo = L.load_fold(L.fold_path(tmp_path, "lda", "S02"))
  assert cfg["channels"] == cfg_lo["channels"] and cfg["train_subjects"] == ["S02"] and cfg_lo["train_subjects"] == ["S01", "S03"]
  assert cfg["hyper"]["folds"] == 2 and cfg["hyper"]["within_repeats"] == 2
  arrays, _ = L.load_fold(L.fold_path(tmp_path, "within_lda", "S02"))
  assert arrays["proba_rep"].shape[0] == 2 and np.allclose(arrays["proba"], arrays["proba_rep"][0])


def test_within_lda_trial_ids_in_the_fold_are_the_subjects_own_and_repeat_accuracies_give_the_sd(built, tmp_path):
  assert L.main(cli(built, tmp_path, methods=("within_lda",))) == 0
  arrays, cfg = L.load_fold(L.fold_path(tmp_path, "within_lda", "S01"))
  classes = np.array(cfg["classes"])
  accs = [np.mean(p.argmax(1) == np.searchsorted(classes, arrays["y"])) for p in arrays["proba_rep"]]
  row = pd.read_csv(tmp_path / "summary.csv").query("Subject == 'S01'").iloc[0]
  assert row["Acc (%)"] == round(100 * np.mean(accs), 2) and row["Acc SD"] == round(100 * np.std(accs, ddof=1), 2)


# P22.2 explicit channels ----------------------------------------------------------------------------------------------

def test_parse_channels_modes_and_errors():
  assert L.parse_channels(["common"]) == ("common", []) and L.parse_channels(["all"]) == ("all", [])
  assert L.parse_channels(["Oz", "PO3", "O1"]) == ("names", ["Oz", "PO3", "O1"])      # order kept as given
  for bad in (["common", "Oz"], ["Oz", "Oz"], []):
    with pytest.raises(ValueError):
      L.parse_channels(bad)


def test_leave_out_for_names_planted_gate_drops():
  m = {s: NAMES8 for s in ("S01", "S02", "S03")}
  kept = {"S01": [c for c in NAMES8 if c != "PO7"], "S02": NAMES8, "S03": [c for c in NAMES8 if c not in ("Oz", "PO3")]}
  rem, left = L.leave_out_for_names(m, kept, ["PO3", "Oz", "O1"])
  assert rem == ["S01", "S02"] and left == {"S03": ["PO3", "Oz"]}                    # PO7 is not named: S01 stays
  rem, left = L.leave_out_for_names(m, kept, NAMES8)
  assert rem == ["S02"] and left == {"S01": ["PO7"], "S03": ["PO3", "Oz"]}
  with pytest.raises(ValueError, match="not in the montage"):
    L.leave_out_for_names(m, kept, ["PO3", "Fz"])
  # the bug (PF-34): keeping every subject whatever the gate dropped
  keep_all = [s for s in m]
  assert keep_all != rem
  assert L.choose_channels(m, kept, "names", ["O1", "PO3"]) == ["O1", "PO3"]


def test_explicit_names_end_to_end_leave_out_print_and_error(tmp_path, capsys):
  from tests import p16_synth as S
  root = tmp_path / "d" / "w1_s0.25"
  S.write_built_subject(root, "S01", n_trials=10, seed=1, bad_channel="Oz")
  S.write_built_subject(root, "S02", n_trials=10, seed=2)
  S.write_built_subject(root, "S03", n_trials=10, seed=3)
  out = tmp_path / "n"
  assert L.main(cli(root.parent, out, "--channels", "O1", "Oz", "POz", methods=("fbcca", "within_lda"))) == 0
  txt = capsys.readouterr().out
  assert "[-] Leaving out S01: gate dropped Oz" in txt and "[=] Keeping S02" in txt
  s = pd.read_csv(out / "summary.csv")
  assert set(s["Subject"]) == {"S02", "S03", "Mean", "SD"}
  assert (s["Channels"] == "O1, Oz, POz").all()                                  # the order as given
  assert "cohort 2 subjects" in s["Data source"].iloc[0]
  cfg = json.loads((out / "loso_config.json").read_text())
  assert cfg["cohort"] == ["S02", "S03"] and cfg["channels_mode"] == "names" and cfg["channels"] == ["O1", "Oz", "POz"]
  with pytest.raises(SystemExit, match="not in the montage"):
    L.main(cli(root.parent, tmp_path / "u", "--channels", "O1", "Fz", methods=("fbcca",)))
  with pytest.raises(SystemExit, match=">= 2 subjects"):                         # only S01 would drop Oz; add a second dropper
    S.write_built_subject(root, "S02", n_trials=10, seed=2, bad_channel="Oz")
    S.write_built_subject(root, "S03", n_trials=10, seed=3, bad_channel="Oz")
    L.main(cli(root.parent, tmp_path / "e", "--channels", "Oz", "O1", methods=("fbcca",)))


# P22.3 fold configuration and check_fold ------------------------------------------------------------------------------

def git(repo, *a):
  return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
  r = tmp_path / "r"
  (r / "src").mkdir(parents=True)
  (r / "scripts").mkdir()
  (r / "docs").mkdir()
  (r / "src" / "a.py").write_text("x = 1\n")
  (r / "docs" / "n.md").write_text("a\n")
  git(r, "init", "-q")
  git(r, "add", "-A")
  git(r, "commit", "-qm", "c0")
  h0 = git(r, "rev-parse", "HEAD")
  (r / "docs" / "n.md").write_text("b\n")
  git(r, "commit", "-qam", "doc only")
  h1 = git(r, "rev-parse", "HEAD")
  (r / "src" / "a.py").write_text("x = 2\n")
  git(r, "commit", "-qam", "code")
  return r, h0, h1, git(r, "rev-parse", "HEAD")


BASE = {"method": "lda", "test_subject": "S01", "train_subjects": ["S02", "S03"], "cohort": ["S01", "S02", "S03"],
        "channels_mode": "common", "channels": ["O1", "Oz"], "window_sec": 1.0, "stride_sec": 0.25, "fs": 256.0, "classes": [101, 102],
        "quality": "shared", "seed": 42, "trial_offset": 10000, "hyper": {"a": 1}, "n_windows_test": 100,
        "git_head": "h", "git_dirty": False, "data_root": "/x"}
CHANGES = {"method": "fbcca", "test_subject": "S02", "train_subjects": ["S02"], "cohort": ["S01", "S02"], "channels_mode": "all",
           "channels": ["O1"], "window_sec": 2.0, "stride_sec": 0.5, "fs": 250.0, "classes": [101], "quality": "per-script",
           "seed": 43, "trial_offset": 1, "hyper": {"a": 2}, "n_windows_test": 99}


@pytest.mark.parametrize("key", sorted(CHANGES))
def test_check_fold_refuses_every_changed_configuration_key(key, tmp_path):
  mine = {**BASE, key: CHANGES[key]}
  with pytest.raises(SystemExit, match="use a new --out-dir") as e:
    L.check_fold(tmp_path / "f.npz", BASE, mine)
  assert key in str(e.value)
  L.check_fold(tmp_path / "f.npz", BASE, {**BASE})                               # identical: accepted
  L.check_fold(tmp_path / "f.npz", BASE, {**BASE, "data_root": "/elsewhere"})    # a moved data root alone is not a change


def test_every_config_key_of_a_real_fold_is_covered(built, tmp_path):
  assert L.main(cli(built, tmp_path, methods=("lda",))) == 0
  _, cfg = L.load_fold(L.fold_path(tmp_path, "lda", "S01"))
  assert set(cfg) == set(BASE), set(cfg) ^ set(BASE)                             # a new key must be added to this test


def test_check_fold_head_rules_doc_only_accepted_code_change_refused(repo, tmp_path):
  r, h0, h1, h2 = repo
  mk = lambda h, dirty=False: {**BASE, "git_head": h, "git_dirty": dirty}
  assert L.code_changed(h0, h1, r) is False and L.code_changed(h1, h2, r) is True
  L.check_fold(tmp_path / "f", mk(h0), mk(h1), r)                                # docs-only head change: accepted
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    L.check_fold(tmp_path / "f", mk(h1), mk(h2), r)                              # src/ changed between heads
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    L.check_fold(tmp_path / "f", mk(h1), mk("deadbeef" * 5), r)                  # a head git cannot resolve
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    L.check_fold(tmp_path / "f", mk("unknown"), mk(h1), r)
  L.check_fold(tmp_path / "f", mk(h1, True), mk(h1, True), r)                    # same head, both dirty: not decidable, accepted
  with pytest.raises(SystemExit, match="working tree state differs"):
    L.check_fold(tmp_path / "f", mk(h1, False), mk(h1, True), r)                 # same head, uncommitted code appeared


def test_head_and_dirty_flag_are_recorded_once_per_process(built, tmp_path, monkeypatch):
  calls = []
  monkeypatch.setattr(L, "git_head", lambda: calls.append("head") or "h-start")
  monkeypatch.setattr(L, "git_dirty", lambda: calls.append("dirty") or False)
  assert L.main(cli(built, tmp_path, methods=("fbcca", "lda"))) == 0
  assert calls == ["head", "dirty"]                                              # not once per fold (6 folds)
  for m in ("fbcca", "lda"):
    for s in ("S01", "S02", "S03"):
      _, cfg = L.load_fold(L.fold_path(tmp_path, m, s))
      assert cfg["git_head"] == "h-start" and cfg["git_dirty"] is False
  assert json.loads((tmp_path / "loso_config.json").read_text())["git_head"] == "h-start"


def test_rerun_with_a_changed_setting_is_refused_and_leaves_every_file_untouched(built, tmp_path):
  assert L.main(cli(built, tmp_path)) == 0
  snap = lambda: {p.name: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
  before = snap()
  for extra in (("--seed", "7"), ("--channels", "all"), ("--folds", "3")):
    with pytest.raises(SystemExit, match="use a new --out-dir"):
      L.main(cli(built, tmp_path, *extra))
    assert snap() == before
  assert L.main(cli(built, tmp_path)) == 0                                       # the same configuration resumes


def test_allow_config_mismatch_flag_is_gone(built, tmp_path):
  with pytest.raises(SystemExit) as e:
    L.main(cli(built, tmp_path, "--allow-config-mismatch"))
  assert e.value.code == 2
  assert "allow-config-mismatch" not in L.build_parser().format_help()


# P21 C-2 fold-count guard ---------------------------------------------------------------------------------------------

def test_cohort_rows_without_all_folds_have_no_mean_unless_asked():
  df = pd.DataFrame({"Subject": ["S01", "S02"], "Window (s)": 1.0, "Method": "eegnet", "Windows": [10, 20], "Trials": [2, 3],
                     "Acc (%)": [50.0, 60.0], "Acc SD": 0.0, "BalAcc (%)": 50.0, "ITR (bits/min)": 1.0, "Train Acc (%)": np.nan,
                     "Runs": 1, "Val Acc (%)": np.nan, "Best Epoch": np.nan, "2-tap Smoothed (%)": 50.0, "Channels": "a",
                     "Data source": "x | cohort 5"})
  out = L.cohort_rows(df, cohort_size=5).set_index("Subject")
  assert out["Acc (%)"].isna().all() and out.loc["Mean", "Folds"] == 2 and "INCOMPLETE: 2 of 5 folds" in out.loc["Mean", "Data source"]
  kept = L.cohort_rows(df, cohort_size=5, partial_mean=True).set_index("Subject")
  assert kept.loc["Mean", "Acc (%)"] == 55.0 and "--partial-mean" in kept.loc["Mean", "Data source"]
  full = L.cohort_rows(df, cohort_size=2).set_index("Subject")
  assert full.loc["Mean", "Acc (%)"] == 55.0 and "INCOMPLETE" not in full.loc["Mean", "Data source"]
  assert L.cohort_rows(df).set_index("Subject").loc["Mean", "Acc (%)"] == 55.0   # no cohort size given: previous behaviour


def test_summary_flags_a_method_with_missing_fold_files(built, tmp_path, capsys):
  assert L.main(cli(built, tmp_path)) == 0
  L.fold_path(tmp_path, "lda", "S03").unlink()
  assert L.main(cli(built, tmp_path, methods=("fbcca",))) == 0                   # lda not requested: its 2 folds remain on disk
  out = capsys.readouterr().out
  assert "[warn] lda: 2 fold files for a cohort of 3" in out
  s = pd.read_csv(tmp_path / "summary.csv")
  lda = s[s["Method"] == "lda"].set_index("Subject")
  assert set(lda.index) == {"S01", "S02", "Mean", "SD"} and lda.loc["Mean", "Acc (%)"] != lda.loc["Mean", "Acc (%)"]   # NaN
  assert lda.loc["Mean", "Folds"] == 2 and "INCOMPLETE" in lda.loc["Mean", "Data source"]
  fb = s[s["Method"] == "fbcca"].set_index("Subject")
  assert fb.loc["Mean", "Acc (%)"] == round(fb.loc[["S01", "S02", "S03"], "Acc (%)"].mean(), 2)
  assert np.isnan(pd.read_csv(tmp_path / "per_subject.csv", header=[0, 1], index_col=0).loc["Mean", ("Acc (%)", "lda")])


def test_fix_round_1_dirty_rules_and_configs_in_code_paths(repo, tmp_path):
  """F1: differing dirty flags are refused at ANY head; a dirty side with differing heads is refused; both dirty at the same
  head is accepted. F2: a change under configs/ between heads is a code change."""
  r, h0, h1, h2 = repo
  mk = lambda h, dirty: {**BASE, "git_head": h, "git_dirty": dirty}
  for a, b in ((mk(h0, False), mk(h1, True)), (mk(h0, True), mk(h1, False)), (mk(h0, True), mk(h1, True))):
    with pytest.raises(SystemExit, match="use a new --out-dir"):      # old code accepted these (heads differ by docs only)
      L.check_fold(tmp_path / "f", a, b, r)
  L.check_fold(tmp_path / "f", mk(h1, True), mk(h1, True), r)
  L.check_fold(tmp_path / "f", mk(h0, False), mk(h1, False), r)
  (r / "configs").mkdir()
  (r / "configs" / "c.yaml").write_text("a: 1\n")
  git(r, "add", "-A")
  git(r, "commit", "-qm", "cfg")
  h3 = git(r, "rev-parse", "HEAD")
  assert L.code_changed(h2, h3, r) is True                              # old CODE_PATHS (src, scripts) said False
  with pytest.raises(SystemExit, match="src/, scripts/ or configs/"):
    L.check_fold(tmp_path / "f", mk(h2, False), mk(h3, False), r)
