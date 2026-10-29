"""P21.1 tests: LOSO harness (`scripts/benchmarks/benchmark_loso.py`) on synthetic subjects with known answers.

Planted data: class c carries extra variance in channel c of every sub-band (CSP/log-variance features) and a sinusoid at the
target frequency in the FBCCA bank. Each fix test names the bug it guards and a variant that fails it.
"""

import json
import re

import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace
from sklearn.preprocessing import StandardScaler

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_window_sweep as W
from src.features.ssvep.fbcca_extraction import TARGET_FREQS
from src.models.classical.sklearn_models import get_sklearn_model_suite
from src.preprocessing.dataset.smoothing import smooth_probabilities_legacy

FS = 256
C, T, B = 6, 256, 3
NAMES = [f"CH{i}" for i in range(C)]


def make_subject(name, seed, n_trials=20, wpt=6, chan_gain=None, snr=1.0, fb_sinus=True):
  """A `load_subject`-like dict: trial ids restart at 0, rows ordered by (trial, offset), offsets in samples."""
  rng = np.random.default_rng(seed)
  tid = np.repeat(np.arange(n_trials), wpt)
  y = np.repeat(101 + rng.permutation(np.arange(n_trials) % 5), wpt)
  n = len(y)
  gain = np.ones(C) if chan_gain is None else np.asarray(chan_gain, dtype=float)
  boost = np.ones((n, C))
  boost[np.arange(n), (y - 101)] = 1.0 + 2.0 * snr
  csp = rng.normal(size=(n, B, C, T)) * boost[:, None, :, None] * gain[None, None, :, None]
  t = np.arange(T) / FS
  fbb = rng.normal(size=(n, 3, C, T))
  if fb_sinus:
    for i in range(n):
      fbb[i] += 1.5 * np.sin(2 * np.pi * TARGET_FREQS[y[i] - 101] * t)[None, None, :]
  d = {"subject": name, "y": y, "trial_ids": tid, "cv_groups": tid, "offsets": np.tile(np.arange(wpt) * 64, n_trials),
       "fs": float(FS), "source": "synthetic", "channel_names": list(NAMES), "channels_all": list(NAMES), "X": csp[:, 0],
       "bands": {"fbsp": None, "fbcsp": csp, "fbcca": fbb}, "meta": {"session": "OO"}}
  d["bands"].pop("fbsp")
  d["fb"] = W.fbcca_features(d)
  return d


def cohort(n=4, **kw):
  return [make_subject(f"S{i + 1:02d}", i, **kw) for i in range(n)]


def pooled(subs):
  P = L.pool(subs, ["fbcsp"])
  return P


# 1. planted SSVEP ----------------------------------------------------------------------------------------------------

def test_fbcca_loso_equals_the_within_value_per_subject_and_lda_is_above_chance():
  """Known answer: the FBCCA decision needs no training, so the LOSO value of a subject equals `benchmark_window_sweep`'s
  fbcca cell exactly (R-16), and is high for the planted frequencies. `lda` on the planted variance is far above 20 %."""
  subs = cohort(3)
  P = pooled(subs)
  args = W.build_parser().parse_args([])
  for k, d in enumerate(subs):
    _, te = L.loso_split(P["subj"], k)
    pred = L.fbcca_fold(P["fb"], te)["proba"].argmax(1)
    within = W.run_cell(d, 1.0, W.FBCCA, args, "cpu", d["fb"])[0]["Acc (%)"]
    assert round(100 * float(np.mean(pred == P["yi"][te])), 2) == within
    assert within > 90
  tr, te = L.loso_split(P["subj"], 0)
  r = L.lda_loso_fold(P["bands"]["fbcsp"], P["fb"], P["yi"], P["subj"], tr, te)
  assert np.mean(r["proba"].argmax(1) == P["yi"][te]) > 0.9 and np.allclose(r["proba"].sum(1), 1)


def test_lda_loso_fold_equals_the_window_sweep_fold_on_the_same_split():
  """Duplication guard: the LOSO `lda` fold is the flagship of P20 (`lda_fold`) up to float noise."""
  P = pooled(cohort(3, snr=0.3, fb_sinus=False))
  tr, te = L.loso_split(P["subj"], 2)
  mine = L.lda_loso_fold(P["bands"]["fbcsp"], P["fb"], P["yi"], P["subj"], tr, te)
  proba, tacc = W.lda_fold(P["bands"]["fbcsp"], P["fb"], P["yi"], tr, te)
  assert np.allclose(mine["proba"], proba, atol=1e-10) and mine["train_acc"] == tacc


# 2. subject gain shift -----------------------------------------------------------------------------------------------

def gain_cohort():
  rng = np.random.default_rng(5)
  gains = [rng.uniform(0.3, 3.0, C) for _ in range(5)]
  gains[0] = np.array([0.15, 4.0, 0.2, 3.5, 0.3, 5.0])   # the held-out subject has a very different electrode gain
  return [make_subject(f"S{i + 1:02d}", 20 + i, snr=0.35, fb_sinus=False, chan_gain=g) for i, g in enumerate(gains)]


def test_subjnorm_beats_plain_lda_when_subjects_differ_in_channel_gain():
  """Known answer: a per-channel gain adds a constant to the log-variance features of a subject; z-scoring each subject
  with its own unlabeled mean/std removes it, so `lda_subjnorm` >= `lda` on the held-out subject (and clearly above
  chance), where plain `lda` is thrown off by the shifted features."""
  P = pooled(gain_cohort())
  tr, te = L.loso_split(P["subj"], 0)
  args = (P["bands"]["fbcsp"], P["fb"], P["yi"], P["subj"], tr, te)
  acc = lambda r: float(np.mean(r["proba"].argmax(1) == P["yi"][te]))
  plain, norm = acc(L.lda_loso_fold(*args)), acc(L.lda_loso_fold(*args, subjnorm=True))
  assert norm >= plain + 0.05 and norm > 0.5


def subjnorm_matrix(P, tr, te, labels, fn=None):
  """Features after the training-subject CSP and the per-subject normalization (rows tr + te)."""
  csp = L.FBCSPTransformer(1).fit(P["bands"]["fbcsp"][tr], P["yi"][tr])
  rows = np.concatenate([tr, te])
  F = np.hstack([csp.transform(P["bands"]["fbcsp"][rows]), P["fb"][rows]])
  return (fn or (lambda F, s, lab: L.subject_zscore(F, s)))(F, P["subj"][rows], labels[rows])


def label_normalizer(F, subj, lab):
  """The plausible bug: z-score per (subject, class) mean using the labels."""
  out = F.copy()
  for s in np.unique(subj):
    m = subj == s
    out[m] = (F[m] - F[m].mean(0)) / (F[m].std(0) + 1e-12)
    for c in np.unique(lab[m]):
      mc = m & (lab == c)
      out[mc] -= out[mc].mean(0)
  return out


def test_subject_normalization_ignores_the_held_out_labels():
  """PF-35 / R2 exception (a): permuting the held-out subject's labels leaves its normalized features unchanged.
  A label-using normalizer (class-centred) fails the same check, so the check is able to detect the bug."""
  P = pooled(cohort(3, snr=0.4, fb_sinus=False))
  tr, te = L.loso_split(P["subj"], 1)
  perm = P["yi"].copy()
  perm[te] = np.random.default_rng(0).permutation(perm[te])
  a, b = subjnorm_matrix(P, tr, te, P["yi"]), subjnorm_matrix(P, tr, te, perm)
  assert np.array_equal(a, b)
  bad_a = subjnorm_matrix(P, tr, te, P["yi"], label_normalizer)
  bad_b = subjnorm_matrix(P, tr, te, perm, label_normalizer)
  assert not np.allclose(bad_a, bad_b)


def test_subjnorm_name_and_data_source_carry_the_label():
  assert "unsupervised per-subject normalization" in L.label_of("lda_subjnorm")
  assert "unsupervised per-subject normalization" in L.SUBJNORM_NOTE and "offline upper bound" in L.SUBJNORM_NOTE
  assert L.label_of("lda") == "lda" and L.METHOD_LABELS.keys() == {"lda_subjnorm"}


# 3. trial-id offset (PF-33) ------------------------------------------------------------------------------------------

def test_pooled_groups_are_unique_per_subject_and_trial_and_the_test_subject_stays_out_of_training():
  """Known answer: two subjects with identical raw trial ids 0..n-1 give 2n distinct pooled groups; the test subject's
  groups never occur among the training groups. With the offset removed (the PF-33 bug) the groups collide."""
  subs = cohort(3)
  P = pooled(subs)
  assert len(np.unique(P["groups"])) == sum(d["n_trials"] if "n_trials" in d else len(np.unique(d["trial_ids"])) for d in subs)
  for k in range(3):
    tr, te = L.loso_split(P["subj"], k)
    assert not set(P["groups"][tr]) & set(P["groups"][te]) and not set(P["trial"][tr]) & set(P["trial"][te])
  # fold output stores the original (un-offset) trial ids
  arrays, _ = L.run_fold("fbcca", P, 1, L.build_parser().parse_args([]), "cpu")
  assert np.array_equal(arrays["trial_id"], subs[1]["trial_ids"])


def test_without_the_offset_trial_ids_collide():
  a, b = cohort(2)
  naive = np.concatenate([a["cv_groups"], b["cv_groups"]])      # the PF-33 bug: pooling the raw ids
  assert len(np.unique(naive)) < 2 * len(np.unique(a["cv_groups"]))
  P = pooled([a, b])
  assert len(np.unique(P["groups"])) == 2 * len(np.unique(a["cv_groups"]))


def test_pool_refuses_different_channels_and_oversized_trial_ids():
  a, b = cohort(2)
  b["channel_names"] = NAMES[:-1]
  with pytest.raises(ValueError, match="different channels"):
    L.pool([a, b])
  a["trial_ids"] = a["trial_ids"] + L.TRIAL_OFFSET
  with pytest.raises(ValueError, match="TRIAL_OFFSET"):
    L.pool(cohort(1) + [a])


def test_network_fold_never_sees_the_test_subject_in_training_or_validation(monkeypatch):
  """PF-32: `fit_network` receives only training-subject windows and trial groups; the validation split drawn from them
  contains no window of the held-out subject."""
  from src.models.cnn import training as TR
  P = pooled(cohort(3, n_trials=10))
  seen = {}
  real = TR.fit_network

  def spy(X, y, groups, *a, **k):
    seen["n"], seen["groups"] = len(X), set(groups)
    r = real(X, y, groups, *a, **k)
    seen["val_groups"] = set(groups[r["val_idx"]])
    return r

  monkeypatch.setattr(TR, "fit_network", spy)
  args = L.build_parser().parse_args(["--max-epochs", "1", "--patience", "1"])
  tr, te = L.loso_split(P["subj"], 2)
  r = L.network_fold(P, tr, te, "eegnet", args, "cpu")
  assert seen["n"] == len(tr) and not seen["groups"] & set(P["groups"][te]) and not seen["val_groups"] & set(P["groups"][te])
  assert r["proba"].shape == (len(te), 5) and np.allclose(r["proba"].sum(1), 1, atol=1e-5)


# 4. leakage sentinel (R2) --------------------------------------------------------------------------------------------

def fitted_params(r):
  lda = r["pipeline"].named_steps["lda"]
  return (r["pipeline"].named_steps["scaler"].mean_, r["pipeline"].named_steps["scaler"].scale_, lda.coef_, lda.intercept_,
          np.stack(r["csp"].csps_[0].filters_), r["train_acc"])


def leaky_fold(csp_bands, fb, yi, subj, tr, te, subjnorm=False, seed=42):
  """The plausible bug: scaler fitted on the training AND test rows."""
  r = L.lda_loso_fold(csp_bands, fb, yi, subj, tr, te, subjnorm, seed)
  F = np.hstack([r["csp"].transform(csp_bands), fb])
  scaler = StandardScaler().fit(F)
  lda = get_sklearn_model_suite(seed)["Shrinkage-LDA lsqr"].fit(scaler.transform(F[tr]), yi[tr])
  return {**r, "pipeline": SimpleNamespace(named_steps={"scaler": scaler, "lda": lda})}


@pytest.mark.parametrize("subjnorm", [False, True])
def test_replacing_the_test_subject_by_a_sentinel_changes_no_fitted_parameter(subjnorm):
  """Known answer: nothing of the held-out subject is fitted, so CSP filters, scaler and LDA are bit-identical when its
  windows (bands and FBCCA scores) are replaced by a huge sentinel. The scaler-on-all-rows variant fails this."""
  P = pooled(cohort(3, snr=0.5, fb_sinus=False))
  tr, te = L.loso_split(P["subj"], 0)
  bands, fb = P["bands"]["fbcsp"], P["fb"]
  b2, f2 = bands.copy(), fb.copy()
  b2[te], f2[te] = 1e3, 1e6
  ra = L.lda_loso_fold(bands, fb, P["yi"], P["subj"], tr, te, subjnorm)
  rb = L.lda_loso_fold(b2, f2, P["yi"], P["subj"], tr, te, subjnorm)
  for u, v in zip(fitted_params(ra), fitted_params(rb)):
    assert np.array_equal(u, v)
  la = leaky_fold(bands, fb, P["yi"], P["subj"], tr, te)
  lb = leaky_fold(b2, f2, P["yi"], P["subj"], tr, te)
  assert not np.allclose(fitted_params(la)[0], fitted_params(lb)[0])


def test_loso_split_refuses_nothing_shared_and_flags_a_leak():
  subj = np.repeat(np.arange(4), 10)
  for k in range(4):
    tr, te = L.loso_split(subj, k)
    assert not set(subj[tr]) & set(subj[te]) and len(tr) + len(te) == len(subj) and set(subj[te]) == {k}


# 5. choose_channels (PF-34) ------------------------------------------------------------------------------------------

def test_choose_channels_common_all_and_errors():
  mont = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  kept = {"S01": mont[1:], "S02": mont, "S03": [c for c in mont if c != "PO8"]}
  m = {s: mont for s in kept}
  assert L.choose_channels(m, kept, "common") == ["PO3", "POz", "PO4", "O1", "Oz", "O2"]
  assert L.choose_channels(m, kept, "all") == mont
  with pytest.raises(ValueError, match="differs"):
    L.choose_channels({**m, "S03": mont[::-1]}, kept, "common")
  with pytest.raises(ValueError, match="no channel"):
    L.choose_channels({"a": ["x"], "b": ["x"]}, {"a": [], "b": ["x"]}, "common")
  with pytest.raises(ValueError):
    L.choose_channels(m, kept, "some")


def test_subject_names_sorted_numerically_and_numeric_collisions_refused():
  assert L.check_subject_names(["S10", "S2", "S01"]) == ["S01", "S2", "S10"]
  with pytest.raises(ValueError, match="share a number"):
    L.check_subject_names(["S10", "S010"])


# 7. 2-tap smoothing (R8) ---------------------------------------------------------------------------------------------

def test_two_tap_smoothing_averages_only_within_a_trial_whatever_the_row_order():
  """Known answer: rows (trial, offset) = (7,0),(7,64),(7,128),(9,0),(9,64); one-hot probabilities of classes 0,1,1,2,2.
  Smoothed: row1 = (e0+e1)/2, row2 = (e1+e1)/2, row3 unchanged (new trial), row4 = e2. Shuffled input gives the same rows.
  The no-reset legacy rule mixes trial 7 into row 3."""
  trial = np.array([7, 7, 7, 9, 9])
  off = np.array([0, 64, 128, 0, 64])
  p = np.eye(3)[[0, 1, 1, 2, 2]]
  exp = np.array([[1, 0, 0], [.5, .5, 0], [0, 1, 0], [0, 0, 1], [0, 0, 1]], dtype=float)
  assert np.allclose(L.smooth_two_tap(p, trial, off), exp)
  perm = np.array([3, 0, 4, 2, 1])
  assert np.allclose(L.smooth_two_tap(p[perm], trial[perm], off[perm]), exp[perm])
  assert not np.allclose(smooth_probabilities_legacy(p)[3], exp[3])


# 6. outputs and resume -----------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loso_root(tmp_path_factory):
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("loso") / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    S.write_built_subject(root, s, n_trials=10, seed=i + 1)
  return root.parent


def args_for(root, out, *extra):
  return ["--data-root", str(root), "--out-dir", str(out), "--methods", "fbcca", "lda", "lda_subjnorm", *extra]


def test_end_to_end_outputs_columns_and_cohort_rows(loso_root, tmp_path, capsys):
  assert L.main(args_for(loso_root, tmp_path)) == 0
  s = pd.read_csv(tmp_path / "summary.csv")
  assert list(s.columns) == L.SUMMARY_COLUMNS
  assert set(s["Subject"]) == {"S01", "S02", "S03", "Mean", "SD"}
  assert s["Data source"].str.contains("cohort 3 subjects").all() and s["Channels"].str.contains("O1").all()
  assert (tmp_path / "per_subject.csv").is_file() and (tmp_path / "folds.csv").is_file()
  p = pd.read_csv(tmp_path / "predictions.csv")
  assert len(p[p["method"] == "lda"]) == s[(s["Method"] == "lda") & s["Subject"].str.startswith("S")]["Windows"].sum()
  cf = pd.read_csv(tmp_path / "confusion.csv")
  assert cf.groupby("method")["count"].sum().to_dict() == p.groupby("method").size().to_dict()
  cfg = json.loads((tmp_path / "loso_config.json").read_text())
  assert cfg["cohort"] == ["S01", "S02", "S03"] and cfg["channels_mode"] == "common"
  assert "cohort 3 subjects" in capsys.readouterr().out


def test_interrupted_run_resumes_skipping_exactly_the_finished_folds(loso_root, tmp_path, monkeypatch, capsys):
  full = tmp_path / "full"
  assert L.main(args_for(loso_root, full)) == 0
  capsys.readouterr()
  part = tmp_path / "part"
  real, calls = L.run_fold, []

  def dying(*a, **k):
    if len(calls) == 4:
      raise KeyboardInterrupt
    calls.append(1)
    return real(*a, **k)

  monkeypatch.setattr(L, "run_fold", dying)
  with pytest.raises(KeyboardInterrupt):
    L.main(args_for(loso_root, part))
  monkeypatch.setattr(L, "run_fold", real)
  assert len(list((part / "folds").glob("*.npz"))) == 4 and not list((part / "folds").glob("*.tmp"))
  capsys.readouterr()
  assert L.main(args_for(loso_root, part)) == 0
  out = capsys.readouterr().out
  assert out.count("[skip]") == 4 and len(re.findall(r"^\[\+\] \w+ test-", out, re.M)) == 5
  for name in ("summary.csv", "per_subject.csv", "predictions.csv", "confusion.csv"):
    assert (full / name).read_bytes() == (part / name).read_bytes(), name


def test_atomic_write_leaves_no_partial_fold(tmp_path, monkeypatch):
  path = tmp_path / "folds" / "lda__test-S01.npz"

  def boom(f, **kw):
    f.write(b"half")
    raise OSError("disk full")

  monkeypatch.setattr(L.np, "savez", boom)
  with pytest.raises(OSError):
    L.save_fold(path, {"proba": np.zeros((2, 5))}, {"a": 1})
  assert not path.exists() and not list(path.parent.glob("*"))


def test_fold_stores_its_configuration_and_a_mismatched_rerun_is_refused(loso_root, tmp_path, capsys):
  assert L.main(args_for(loso_root, tmp_path, "--seed", "42")) == 0
  _, cfgd = L.load_fold(L.fold_path(tmp_path, "lda", "S02"))
  for k in ("train_subjects", "channels", "window_sec", "stride_sec", "hyper", "seed", "git_head", "fs", "cohort"):
    assert k in cfgd
  assert cfgd["train_subjects"] == ["S01", "S03"] and cfgd["seed"] == 42
  with pytest.raises(SystemExit, match="different configuration"):
    L.main(args_for(loso_root, tmp_path, "--seed", "7"))
  with pytest.raises(SystemExit, match="different configuration"):
    L.main(args_for(loso_root, tmp_path, "--channels", "all"))
  with pytest.raises(SystemExit):                      # P22.3: the override flag no longer exists
    L.main(args_for(loso_root, tmp_path, "--seed", "7", "--allow-config-mismatch"))


def test_channels_all_keeps_the_gate_dropped_channel_and_common_drops_it(tmp_path_factory):
  """A planted bad channel (noise 80 uV) in S02 fails the gate there: `common` omits it for everybody, `all` keeps it."""
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("chan") / "w1_s0.25"
  S.write_built_subject(root, "S01", n_trials=10, seed=1)
  S.write_built_subject(root, "S02", n_trials=10, seed=2, bad_channel="Oz")
  out = root.parent / "o"
  assert L.main(["--data-root", str(root.parent), "--out-dir", str(out / "c"), "--methods", "fbcca"]) == 0
  assert L.main(["--data-root", str(root.parent), "--out-dir", str(out / "a"), "--methods", "fbcca", "--channels", "all"]) == 0
  common = pd.read_csv(out / "c" / "summary.csv")["Channels"].iloc[0]
  allc = pd.read_csv(out / "a" / "summary.csv")["Channels"].iloc[0]
  assert "Oz" not in common.split(", ") and "Oz" in allc and "gate channel drops ignored" in allc


def test_degenerate_flag_on_a_planted_best_epoch_one_history():
  assert L.is_degenerate(1, 0.9, 5) and L.is_degenerate(40, 0.25, 5) and not L.is_degenerate(40, 0.9, 5)
  assert not L.is_degenerate(float("nan"), float("nan"), 5)


def test_save_models_and_network_methods_through_the_cli(loso_root, tmp_path):
  models = tmp_path / "models"
  out = tmp_path / "o"
  assert L.main(["--data-root", str(loso_root), "--out-dir", str(out), "--methods", "lda", "eegnet", "--max-epochs", "1",
                 "--patience", "1", "--device", "cpu", "--save-models", "--models-dir", str(models)]) == 0
  assert sorted(p.name for p in models.glob("*")) == sorted(
    [f"lda__test-S0{i}.joblib" for i in (1, 2, 3)] + [f"eegnet__test-S0{i}.pt" for i in (1, 2, 3)])
  s = pd.read_csv(out / "summary.csv")
  assert set(s["Method"]) == {"lda", "eegnet"}
  f = pd.read_csv(out / "folds.csv")
  assert f[f["Method"] == "eegnet"]["degenerate"].all() and not f[f["Method"] == "lda"]["degenerate"].any()   # 1 epoch: best epoch 1
