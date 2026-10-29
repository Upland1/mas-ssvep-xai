"""P21 independent known-answer tests (synthetic-tester; written without reusing the builders' fixtures).

Planted data: class c = extra variance in channel c of every FBCSP band (log-variance / CSP features) and, in the FBCCA bank,
a sinusoid at the c-th target frequency. Subjects differ in gain, trial count and windows per trial. Each test states its
known answer; the mutation checks of 04_tests.md name the planted bug that kills each of them.
"""

import json
import re
import shutil

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_window_sweep as W
from src.features.ssvep.fbcca_extraction import TARGET_FREQS

FS, C, T, B = 256, 6, 256, 3
NAMES = [f"CH{i}" for i in range(C)]


def subject(name, seed, n_trials, wpt, gain=1.0, snr=2.0, sinus=1.5):
  """`load_subject`-like dict. Trial ids restart at 0 (the PF-33 situation); `wpt` windows per trial, offsets in samples."""
  rng = np.random.default_rng(seed)
  tid = np.repeat(np.arange(n_trials), wpt)
  y = np.repeat(101 + rng.permutation(np.arange(n_trials) % 5), wpt)
  n = len(y)
  boost = np.ones((n, C))
  boost[np.arange(n), y - 101] = 1.0 + snr
  csp = rng.normal(size=(n, B, C, T)) * boost[:, None, :, None] * gain
  t = np.arange(T) / FS
  fbb = rng.normal(size=(n, 3, C, T)) * gain
  fbb += sinus * gain * np.sin(2 * np.pi * np.asarray(TARGET_FREQS)[y - 101][:, None] * t)[:, None, None, :]
  d = {"subject": name, "y": y, "trial_ids": tid, "cv_groups": tid.copy(), "offsets": np.tile(np.arange(wpt) * 64, n_trials),
       "fs": float(FS), "channel_names": list(NAMES), "channels_all": list(NAMES), "X": csp[:, 0].copy(),
       "bands": {"fbcsp": csp, "fbcca": fbb}, "meta": {"session": "OO"}}
  d["fb"] = W.fbcca_features(d)
  return d


def cohort(gains=(1.0, 2.5, 0.4, 1.7), **kw):
  return [subject(f"S{i + 1:02d}", 70 + i, n_trials=15 + 2 * i, wpt=4 + i % 3, gain=g, **kw) for i, g in enumerate(gains)]


def pooled(subs):
  return L.pool(subs, ["fbcsp"])


def acc_of(proba, yi):
  return float(np.mean(np.asarray(proba).argmax(1) == yi))


@pytest.fixture(scope="module")
def P4():
  return pooled(cohort())


# 1. planted frequencies ----------------------------------------------------------------------------------------------

def test_fbcca_loso_is_the_planted_class_and_equals_the_within_value_on_the_same_channels(P4):
  """Known answer: a strong planted sinusoid is recovered by argmax of the FBCCA scores, per subject, whatever the gain
  (CCA is scale-free). LOSO fbcca of a subject = the subject's own within argmax, exactly (nothing is trained)."""
  subs = cohort()
  for k, d in enumerate(subs):
    _, te = L.loso_split(P4["subj"], k)
    loso_pred = L.fbcca_fold(P4["fb"], te)["proba"].argmax(1)
    within_pred = W.fbcca_features(d).argmax(1)          # the subject alone, no pooling
    assert np.array_equal(loso_pred, within_pred)
    assert np.array_equal(loso_pred, d["y"] - 101)       # planted frequency -> its class


def test_fbcca_fold_proba_is_normalised_scores_and_uniform_for_all_zero_scores():
  p = L.fbcca_fold(np.array([[1.0, 3.0, 0, 0, 0], [0, 0, 0, 0, 0.0]]), np.array([0, 1]))["proba"]
  assert np.allclose(p[0], [.25, .75, 0, 0, 0]) and np.allclose(p[1], 0.2)


def test_lda_above_chance_on_a_held_out_subject_with_a_different_gain(P4):
  tr, te = L.loso_split(P4["subj"], 1)                 # gain 2.5 held out, trained on 1.0 / 0.4 / 1.7
  r = L.lda_loso_fold(P4["bands"]["fbcsp"], P4["fb"], P4["yi"], P4["subj"], tr, te)
  assert acc_of(r["proba"], P4["yi"][te]) > 0.9 and np.allclose(r["proba"].sum(1), 1)


def test_subjnorm_not_below_lda_under_a_known_gain_shift_and_much_better_than_chance():
  """Known answer: the held-out subject has a very different gain per electrode (x0.2 ... x6); that adds a per-feature
  constant to its CSP log-variances, plain lda is shifted off its boundaries and a per-subject z-score removes the constant."""
  subs = cohort(gains=(1.0, 1.0, 1.0, 1.0, 1.0), snr=0.5, sinus=0.0)
  g = np.array([0.2, 6.0, 0.3, 4.0, 0.25, 5.0])
  subs[0]["bands"]["fbcsp"] = subs[0]["bands"]["fbcsp"] * g[None, None, :, None]
  P = pooled(subs)
  tr, te = L.loso_split(P["subj"], 0)
  a = (P["bands"]["fbcsp"], P["fb"], P["yi"], P["subj"], tr, te)
  plain, norm = acc_of(L.lda_loso_fold(*a)["proba"], P["yi"][te]), acc_of(L.lda_loso_fold(*a, subjnorm=True)["proba"], P["yi"][te])
  assert norm >= plain + 0.05 and norm > 0.5


def test_subject_zscore_is_affine_invariant_per_subject_and_has_zero_mean_unit_std():
  rng = np.random.default_rng(0)
  F = rng.normal(size=(60, 4))
  s = np.repeat([0, 1, 2], 20)
  Z = L.subject_zscore(F, s)
  F2 = F.copy()
  F2[s == 1] = F2[s == 1] * 9.0 + 100.0                 # change subject 1's gain and offset only
  Z2 = L.subject_zscore(F2, s)
  assert np.allclose(Z, Z2)
  for k in range(3):
    assert np.allclose(Z[s == k].mean(0), 0, atol=1e-12) and np.allclose(Z[s == k].std(0), 1)
  const = L.subject_zscore(np.full((6, 2), 3.0), np.zeros(6))
  assert np.all(np.isfinite(const)) and np.all(const == 0)    # constant column: no division by zero


# 2. trial-id collisions ----------------------------------------------------------------------------------------------

def test_equal_trial_ids_in_every_subject_never_collide_after_pooling_and_the_validation_split_excludes_the_test_subject():
  """Known answer: all subjects have trial ids 0..m-1 (shared raw ids). Pooled group count = sum of trial counts. The inner
  grouped validation split of every training set contains no window of the held-out subject, for every held-out subject."""
  from src.models.cnn.training import split_validation
  subs = cohort()
  P = pooled(subs)
  assert len(np.unique(P["groups"])) == sum(len(np.unique(d["trial_ids"])) for d in subs) and len(np.unique(P["trial"])) == len(np.unique(P["groups"]))
  raw = np.concatenate([d["trial_ids"] for d in subs])
  assert len(np.unique(raw)) < len(np.unique(P["groups"]))           # the raw ids WOULD collide
  for k in range(len(subs)):
    tr, te = L.loso_split(P["subj"], k)
    fit, val = split_validation(P["yi"][tr], P["groups"][tr], 0.2, 42)
    assert not set(P["subj"][tr][val]) & {k} and not set(P["subj"][tr][fit]) & {k}
    assert not set(P["groups"][tr]) & set(P["groups"][te])
    # a pooled group never mixes two subjects
    for g in np.unique(P["groups"]):
      assert len(np.unique(P["subj"][P["groups"] == g])) == 1


def test_pool_assigns_subject_index_in_the_given_order_and_keeps_rows_aligned():
  subs = cohort()
  P = pooled(subs)
  assert list(P["subjects"]) == [d["subject"] for d in subs]
  for k, d in enumerate(subs):
    m = P["subj"] == k
    assert np.array_equal(P["y"][m], d["y"]) and np.array_equal(P["fb"][m], d["fb"]) and np.array_equal(P["bands"]["fbcsp"][m], d["bands"]["fbcsp"])
    assert np.array_equal(P["trial"][m] - L.TRIAL_OFFSET * k, d["trial_ids"])


# 3. leakage sentinel -------------------------------------------------------------------------------------------------

def _probe_outputs(r, probe):
  """Everything fitted, observed on a fixed probe matrix: the pipeline output and the CSP transform."""
  return r["pipeline"].predict_proba(probe), r["csp"].transform(probe_bands)


probe_bands = np.random.default_rng(3).normal(size=(5, B, C, T))


@pytest.mark.parametrize("method", ["lda", "lda_subjnorm"])
def test_sentinel_in_the_held_out_subject_changes_no_training_side_output(P4, method):
  """Known answer: the held-out subject's bands and FBCCA scores replaced by a huge sentinel leave the CSP filters, the
  scaler, the LDA and the train accuracy bit-identical (nothing of the test subject is fitted)."""
  tr, te = L.loso_split(P4["subj"], 2)
  bands, fb = P4["bands"]["fbcsp"], P4["fb"]
  b2, f2 = bands.copy(), fb.copy()
  b2[te], f2[te] = 5e3, 1e7
  sub = method == "lda_subjnorm"
  ra = L.lda_loso_fold(bands, fb, P4["yi"], P4["subj"], tr, te, sub)
  rb = L.lda_loso_fold(b2, f2, P4["yi"], P4["subj"], tr, te, sub)
  la, lb = ra["pipeline"].named_steps["lda"], rb["pipeline"].named_steps["lda"]
  assert np.array_equal(la.coef_, lb.coef_) and np.array_equal(la.intercept_, lb.intercept_)
  for k in ("mean_", "scale_"):
    assert np.array_equal(getattr(ra["pipeline"].named_steps["scaler"], k), getattr(rb["pipeline"].named_steps["scaler"], k))
  assert np.array_equal(ra["csp"].transform(probe_bands), rb["csp"].transform(probe_bands))
  assert ra["train_acc"] == rb["train_acc"]


def test_sentinel_in_one_subject_leaves_every_other_fbcca_fold_unchanged(P4):
  """fbcca trains nothing: the fold of subject j depends on subject j's rows only."""
  fb2 = P4["fb"].copy()
  fb2[P4["subj"] == 1] = 1e9
  for j in (0, 2, 3):
    _, te = L.loso_split(P4["subj"], j)
    assert np.array_equal(L.fbcca_fold(P4["fb"], te)["proba"], L.fbcca_fold(fb2, te)["proba"])


def test_labels_of_the_held_out_subject_reach_no_classical_prediction(P4):
  """Known answer: permuting the held-out subject's labels leaves its probabilities bit-identical for lda and
  lda_subjnorm (the per-subject normalization is unsupervised, PF-35)."""
  tr, te = L.loso_split(P4["subj"], 3)
  yi2 = P4["yi"].copy()
  yi2[te] = np.random.default_rng(1).permutation(yi2[te])
  assert not np.array_equal(yi2, P4["yi"])
  for sub in (False, True):
    a = L.lda_loso_fold(P4["bands"]["fbcsp"], P4["fb"], P4["yi"], P4["subj"], tr, te, sub)["proba"]
    b = L.lda_loso_fold(P4["bands"]["fbcsp"], P4["fb"], yi2, P4["subj"], tr, te, sub)["proba"]
    assert np.array_equal(a, b)


def test_network_fit_gets_no_held_out_window_and_the_sentinel_changes_no_trained_weight(monkeypatch):
  """One small CCNN on CPU. `fit_network` sees exactly the training rows; its validation indices are inside them; replacing
  the held-out subject's windows by a sentinel leaves the trained weights and normalization statistics bit-identical."""
  import torch
  from src.models.cnn import training as TR
  torch.set_num_threads(1)
  subs = cohort(gains=(1.0, 2.0, 0.5), snr=1.0)
  for d in subs:
    d["X"] = d["X"][:, :, :]
  P = pooled([{**d, "X": d["X"].astype(np.float64)} for d in subs])
  tr, te = L.loso_split(P["subj"], 1)
  args = L.build_parser().parse_args(["--max-epochs", "2", "--patience", "2", "--device", "cpu"])
  seen = {}
  real = TR.fit_network

  def spy(X, y, groups, *a, **k):
    r = real(X, y, groups, *a, **k)
    seen.update(n=len(X), groups=set(groups), val=r["val_idx"])
    return r

  monkeypatch.setattr(TR, "fit_network", spy)
  ra = L.network_fold(P, tr, te, "ccnn", args, "cpu")
  assert seen["n"] == len(tr) and not seen["groups"] & set(P["groups"][te]) and seen["val"].max() < len(tr)
  Q = dict(P, X=P["X"].copy())
  Q["X"][te] = 1e4
  rb = L.network_fold(Q, tr, te, "ccnn", args, "cpu")
  for (n1, p1), (n2, p2) in zip(ra["model"].state_dict().items(), rb["model"].state_dict().items()):
    assert n1 == n2 and torch.equal(p1, p2), n1
  assert np.array_equal(ra["mean"], rb["mean"]) and np.array_equal(ra["std"], rb["std"])
  assert ra["train_acc"] == rb["train_acc"]


# 4. channels ---------------------------------------------------------------------------------------------------------

def test_choose_channels_planted_drops_and_mismatched_montages():
  mont = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  kept = {"S01": [c for c in mont if c != "PO7"], "S02": [c for c in mont if c not in ("Oz", "PO8")], "S05": mont,
          "S09": [c for c in mont if c != "PO3"]}
  m = {s: list(mont) for s in kept}
  assert L.choose_channels(m, kept) == ["POz", "PO4", "O1", "O2"]                # montage order, dropped anywhere = dropped
  assert L.choose_channels(m, kept, "all") == mont
  assert L.choose_channels({"a": mont}, {"a": mont[2:]}, "common") == mont[2:]    # one subject: its own kept list
  with pytest.raises(ValueError):
    L.choose_channels({**m, "S09": mont[:-1]}, kept)                              # fewer channels
  with pytest.raises(ValueError):
    L.choose_channels({**m, "S09": mont[::-1]}, kept)                             # same set, different order
  with pytest.raises(ValueError):
    L.choose_channels({**m, "S09": mont[:-1] + ["Fz"]}, kept, "all")              # different name, even for 'all'
  with pytest.raises(ValueError):
    L.choose_channels(m, {**kept, "S05": ["PO7"]}, "common")                      # intersection empty
  assert L.choose_channels(m, {**kept, "S05": ["PO7"]}, "all") == mont            # ... but 'all' never empty


# 5. smoothing, ITR, cohort rows --------------------------------------------------------------------------------------

def test_two_tap_never_mixes_trials_or_subjects_on_pooled_rows_in_any_order():
  """Known answer: pooled over subjects with offset ids, smoothing equals the per-subject smoothing; shuffling the rows
  changes nothing; the first window of a trial (and of a subject) is unchanged; a window is averaged with ITS predecessor."""
  rng = np.random.default_rng(4)
  subs = cohort(gains=(1, 1, 1))
  P = pooled(subs)
  proba = rng.dirichlet(np.ones(5), size=len(P["y"]))
  sm = L.smooth_two_tap(proba, P["trial"], P["offsets"])
  for k, d in enumerate(subs):
    m = P["subj"] == k
    assert np.allclose(sm[m], L.smooth_two_tap(proba[m], d["trial_ids"], d["offsets"]))
  first = np.r_[True, np.diff(P["trial"]) != 0]
  assert np.array_equal(sm[first], proba[first])
  prev = np.roll(proba, 1, axis=0)
  assert np.allclose(sm[~first], (proba[~first] + prev[~first]) / 2)
  perm = rng.permutation(len(proba))
  assert np.allclose(L.smooth_two_tap(proba[perm], P["trial"][perm], P["offsets"][perm]), sm[perm])
  # boundary case with raw ids: two subjects both starting at trial 0 would mix if concatenated unsplit
  raw = np.concatenate([d["trial_ids"] for d in subs])
  off = np.concatenate([d["offsets"] for d in subs])
  assert not np.allclose(L.smooth_two_tap(proba, raw, off), sm)


def test_itr_known_value_and_edges_in_the_summary_row():
  """Wolpaw N = 5, acc 0.8, T = 1 + 0.5 s: bits = log2 5 + .8 log2 .8 + .2 log2(.05) = 1.2000 -> 48.00 bits/min.
  acc 1: log2(5) * 40 = 92.88; acc = chance 0.2: 0."""
  assert abs(np.log2(5) + .8 * np.log2(.8) + .2 * np.log2(.05) - 1.2) < 2e-4
  classes = np.array([101, 102, 103, 104, 105])

  def row(n_ok, n=10):
    y = np.repeat(classes, 2)[:n]
    proba = np.eye(5)[np.searchsorted(classes, y)]
    wrong = np.arange(n) >= n_ok
    proba[wrong] = np.eye(5)[(np.searchsorted(classes, y[wrong]) + 1) % 5]
    arr = {"proba": proba, "y": y, "trial_id": np.arange(n), "offset": np.zeros(n), "train_acc": np.array(1.0),
           "val_acc": np.array(np.nan), "best_epoch": np.array(np.nan)}
    cfg = {"window_sec": 1.0, "fs": 256, "channels": NAMES, "channels_mode": "common"}
    return L.fold_rows("lda", "S01", arr, cfg, classes, "src")[0]

  r = row(8)
  assert r["Acc (%)"] == 80.0 and r["ITR (bits/min)"] == 48.0
  assert row(10)["ITR (bits/min)"] == round(np.log2(5) * 40, 2) and row(2)["ITR (bits/min)"] == 0.0
  assert r["Windows"] == 10 and r["Trials"] == 10 and r["Runs"] == 1


def test_cohort_rows_mean_and_sd_use_ddof_1_over_held_out_subjects():
  df = pd.DataFrame({"Subject": ["S01", "S02", "S03"], "Window (s)": 1.0, "Method": "lda", "Windows": [10, 20, 30],
                     "Trials": [2, 3, 4], "Acc (%)": [50.0, 60.0, 100.0], "Acc SD": 0.0, "BalAcc (%)": [50.0, 60.0, 100.0],
                     "ITR (bits/min)": [1.0, 2.0, 3.0], "Train Acc (%)": np.nan, "Runs": 1, "Val Acc (%)": np.nan,
                     "Best Epoch": np.nan, "2-tap Smoothed (%)": [50.0, 60.0, 100.0], "Channels": "a",
                     "Data source": "x | cohort 3"})
  out = L.cohort_rows(df).set_index("Subject")
  assert out.loc["Mean", "Acc (%)"] == 70.0 and out.loc["SD", "Acc (%)"] == round(float(np.std([50, 60, 100], ddof=1)), 2)
  assert out.loc["Mean", "Windows"] == 20.0 and "3 held-out subjects" in out.loc["Mean", "Data source"]


# 6. end-to-end on built synthetic folders: resume, config refusal, channels ------------------------------------------

@pytest.fixture(scope="module")
def built(tmp_path_factory):
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("ind") / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S04"]):
    S.write_built_subject(root, s, n_trials=10, seed=11 + i)
  return root.parent


def cli(root, out, *extra, methods=("fbcca", "lda", "lda_subjnorm")):
  return ["--data-root", str(root), "--out-dir", str(out), "--methods", *methods, *extra]


OUTPUTS = ("summary.csv", "per_subject.csv", "predictions.csv", "confusion.csv")   # folds.csv holds wall-clock Seconds


def test_interrupt_mid_write_then_resume_gives_byte_identical_outputs_and_skips_only_finished(built, tmp_path, monkeypatch, capsys):
  full, part = tmp_path / "full", tmp_path / "part"
  assert L.main(cli(built, full)) == 0
  capsys.readouterr()
  real_save, n = L.save_fold, []

  def dying(path, arrays, config):
    if len(n) == 5:                                   # the 6th fold dies inside the write: only an unfinished tmp may exist
      path.parent.mkdir(parents=True, exist_ok=True)
      path.with_name(path.name + ".tmp").write_bytes(b"half a fold")
      raise KeyboardInterrupt
    n.append(1)
    real_save(path, arrays, config)

  monkeypatch.setattr(L, "save_fold", dying)
  with pytest.raises(KeyboardInterrupt):
    L.main(cli(built, part))
  monkeypatch.setattr(L, "save_fold", real_save)
  assert len(list((part / "folds").glob("*.npz"))) == 5
  capsys.readouterr()
  assert L.main(cli(built, part)) == 0
  out = capsys.readouterr().out
  assert len(re.findall(r"^\[skip\]", out, re.M)) == 5 and len(re.findall(r"^\[\+\] (?:fbcca|lda|lda_subjnorm) test-", out, re.M)) == 4
  for f in OUTPUTS:
    assert (full / f).read_bytes() == (part / f).read_bytes(), f
  assert pd.read_csv(full / "folds.csv").drop(columns="Seconds").equals(pd.read_csv(part / "folds.csv").drop(columns="Seconds"))
  # folds already complete: a second rerun skips all 9 and still rewrites identical outputs
  capsys.readouterr()
  assert L.main(cli(built, part)) == 0
  assert capsys.readouterr().out.count("[skip]") == 9
  assert (full / "summary.csv").read_bytes() == (part / "summary.csv").read_bytes()


@pytest.mark.parametrize("change", [["--seed", "5"], ["--channels", "all"]])
def test_rerun_with_another_configuration_is_refused_and_leaves_the_folds_alone(built, tmp_path, change):
  """Known answer: the second run raises SystemExit naming the configuration difference, no fold file is touched."""
  from tests import p16_synth as S
  root = tmp_path / "data" / "w1_s0.25"
  for i, s in enumerate(["S01", "S02"]):
    S.write_built_subject(root, s, n_trials=10, seed=40 + i, bad_channel="Oz" if s == "S02" else None)
  out = tmp_path / "o"
  assert L.main(cli(root.parent, out, methods=("fbcca", "lda"))) == 0
  before = {p.name: p.read_bytes() for p in (out / "folds").glob("*.npz")}
  with pytest.raises(SystemExit, match="different configuration"):
    L.main(cli(root.parent, out, *change, methods=("fbcca", "lda")))
  assert {p.name: p.read_bytes() for p in (out / "folds").glob("*.npz")} == before


def test_tampered_training_subjects_in_a_fold_config_is_refused_but_a_moved_data_root_and_new_head_are_not(built, tmp_path, capsys):
  out = tmp_path / "o"
  assert L.main(cli(built, out, methods=("fbcca",))) == 0
  moved = tmp_path / "moved"
  shutil.copytree(built, moved)                                # same data, another path (Colab vs local)
  capsys.readouterr()
  assert L.main(cli(moved, out, methods=("fbcca",))) == 0
  assert capsys.readouterr().out.count("[skip]") == 3
  p = L.fold_path(out, "fbcca", "S01")
  arrays, cfg = L.load_fold(p)
  cfg["git_head"] = "deadbeef"
  L.save_fold(p, arrays, cfg)
  with pytest.raises(SystemExit, match="use a new --out-dir"):   # P22.3: a head git cannot resolve is refused
    L.main(cli(moved, out, methods=("fbcca",)))
  cfg["git_head"] = L.git_head()                               # the current head: nothing differs
  L.save_fold(p, arrays, cfg)
  assert L.main(cli(moved, out, methods=("fbcca",))) == 0
  cfg["train_subjects"] = ["S01", "S02"]                       # a training set that includes the test subject
  L.save_fold(p, arrays, cfg)
  with pytest.raises(SystemExit, match="different configuration"):
    L.main(cli(moved, out, methods=("fbcca",)))


def test_common_channels_drop_every_subjects_bad_channel_and_all_keeps_the_montage(tmp_path):
  """Two different planted bad channels (S01: O1, S04: PO3) are both absent under `common`; `all` lists the 8 channels."""
  from tests import p16_synth as S
  root = tmp_path / "d" / "w1_s0.25"
  S.write_built_subject(root, "S01", n_trials=10, seed=1, bad_channel="O1")
  S.write_built_subject(root, "S02", n_trials=10, seed=2)
  S.write_built_subject(root, "S04", n_trials=10, seed=3, bad_channel="PO3")
  assert L.main(cli(root.parent, tmp_path / "c", methods=("fbcca",))) == 0
  assert L.main(cli(root.parent, tmp_path / "a", methods=("fbcca",), *("--channels", "all"))) == 0
  common = pd.read_csv(tmp_path / "c" / "summary.csv")["Channels"].iloc[0].split(", ")
  allc = pd.read_csv(tmp_path / "a" / "summary.csv")["Channels"].iloc[0].replace(" (all, gate channel drops ignored)", "").split(", ")
  assert "O1" not in common and "PO3" not in common and len(common) == 6 and len(allc) == 8
  cfg = json.loads((tmp_path / "c" / "loso_config.json").read_text())
  assert cfg["cohort"] == ["S01", "S02", "S04"] and cfg["channels"] == common


def test_summary_rows_cover_every_held_out_subject_with_the_cohort_in_the_data_source(built, tmp_path):
  assert L.main(cli(built, tmp_path)) == 0
  s = pd.read_csv(tmp_path / "summary.csv")
  subj = s[~s["Subject"].isin(["Mean", "SD"])]
  assert set(subj["Subject"]) == {"S01", "S02", "S04"} and (subj.groupby("Method").size() == 3).all()
  assert s["Data source"].str.contains("cohort 3 subjects").all()
  assert s.loc[s["Method"].str.startswith("lda_subjnorm"), "Method"].str.contains("unsupervised per-subject normalization").all()
  pr = pd.read_csv(tmp_path / "predictions.csv")
  # smoothing never crossed a subject: the first window of each (subject, method, trial) equals its raw prediction
  first = pr.sort_values(["subject", "method", "trial_id", "offset_sec"]).groupby(["subject", "method", "trial_id"]).head(1)
  assert (first["pred"] == first["pred_2tap"]).all()
  assert pr["trial_id"].max() < L.TRIAL_OFFSET                    # stored ids are the subject's own, not the pooled offset ones


def test_run_fold_stores_the_subjects_own_trial_ids_and_labels(P4):
  args = L.build_parser().parse_args([])
  for k in (0, 3):
    arrays, _ = L.run_fold("fbcca", P4, k, args, "cpu")
    m = P4["subj"] == k
    assert np.array_equal(arrays["trial_id"], P4["trial"][m] - L.TRIAL_OFFSET * k) and arrays["trial_id"].max() < L.TRIAL_OFFSET
    assert np.array_equal(arrays["y"], P4["y"][m]) and int(arrays["n_train"]) == int((~m).sum())
