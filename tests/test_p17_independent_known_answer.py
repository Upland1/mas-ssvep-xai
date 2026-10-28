"""P17 independent known-answer tests (synthetic-tester): centres and skip rule, tone-to-band mapping, bank
concatenation, four-bank build identity, 6-class selection / priors / groups, metrics, summed confusion, C-1, C-2.

Expected values are written out from the protocol and the arithmetic, not read from the code under test.
Synthetic recordings only; no generated or ignored file is read.
"""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

from scripts import build_windows as bw
from scripts import freeze_baseline as fb
from scripts.benchmarks.feature_based import benchmark_n_subjects as B
from src.io import subject_data as SD
from src.models.classical import rest_metrics as RM
from src.preprocessing.windowing import band_windows, build_bank, harmonic_centers, intermediate_centers, narrow_filter_bank
from tests import p05_synth, p16_synth as S

TH = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}
ALL = ("fbcca", "fbcsp", "harmonic", "intermediate")
F = {101: 24.0, 102: 20.0, 103: 15.0, 104: 10.91, 105: 8.57}            # 01_DATA_SPEC section 2, two decimals as the plan fixes them


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  root = tmp_path_factory.mktemp("ind17")
  S.write_built_subject(root, "S01", n_trials=10, seed=11, banks=ALL)
  return root


@pytest.fixture(scope="module")
def legacy(tmp_path_factory):
  root = tmp_path_factory.mktemp("ind17_leg")
  p05_synth.write_subject(root, "S03", n_trials=6)
  return root


# --- centres and skip rule ------------------------------------------------------------------------------------------

def test_centres_are_multiples_and_midpoints_of_the_protocol_frequencies():
  want = [k * f for f in (24.0, 20.0, 15.0, 10.91, 8.57) for k in (1, 2, 3)]
  assert harmonic_centers(3) == pytest.approx(want) and len(want) == 15
  ordered = sorted(F.values())
  assert intermediate_centers() == pytest.approx([(a + b) / 2 for a, b in zip(ordered, ordered[1:])])
  assert intermediate_centers() == pytest.approx([9.74, 12.955, 17.5, 22.0], abs=1e-9)


@pytest.mark.parametrize("fs,max_hz,skipped", [
  (256.0, 90.0, {60.0}),                    # only the 60 Hz notch (72 + 1 = 73 < 90 < 127)
  (200.0, 90.0, {60.0}),                    # nyq - 1 = 99 > 90
  (128.0, 90.0, {60.0, 72.0}),              # nyq - 1 = 63: 72 Hz band (71-73) is above, 60 is the notch
  (100.0, 90.0, {60.0, 72.0}),              # nyq - 1 = 49: 48 Hz band tops at 49 = cap, kept; 60 and 72 skipped
  (256.0, 45.0, {60.0, 72.0, 48.0, 45.0}), # max_hz 45: bands 47-49, 71-73 and 44-46 end above 45; 60 is the notch; 40 (39-41) kept
])
def test_skip_rule(fs, max_hz, skipped):
  bank, sk = narrow_filter_bank(fs, harmonic_centers(3), 1.0, 2, max_hz, (60.0,))
  got = {round(s["center"], 6) for s in sk if s["center"] in (24.0, 48.0, 72.0, 20.0, 40.0, 60.0, 15.0, 30.0, 45.0)}
  assert got == skipped
  assert len(bank) + len(sk) == 15
  assert all(f.high <= min(max_hz, fs / 2 - 1) + 1e-12 and not (f.low <= 60.0 <= f.high) for f in bank)


@pytest.mark.parametrize("target", [101, 102, 103, 104, 105])
def test_double_frequency_tone_lands_in_its_own_harmonic_band(target):
  fs = 256.0
  bank, skipped = build_bank("harmonic", fs)
  centres = [c for c in harmonic_centers(3) if abs(c - 60.0) > 1e-9]
  assert [round((b.low + b.high) / 2, 6) for b in bank] == pytest.approx(centres)
  t = np.arange(int(12 * fs)) / fs
  x = np.sin(2 * np.pi * 2 * F[target] * t)[None]
  w = band_windows(x, np.array([int(4 * fs)]), int(fs), bank, "continuous")
  power = (w[0, :, 0] ** 2).mean(-1)
  best = int(np.argmax(power))
  assert (bank[best].low + bank[best].high) / 2 == pytest.approx(2 * F[target])
  assert power[best] > 0.4 and power[np.arange(len(power)) != best].max() < 0.05 * power[best]


# --- band order and concatenation -----------------------------------------------------------------------------------

def _load(root, bank, classes=5):
  return SD.load_subject(root / "S01", SD.CLASS_CODES + ((201,) if classes == 6 else ()), "shared",
                         bands=("fbcca", "fbcsp") + B.EXTRA_BANKS[bank], thresholds=TH, channel_fail_fraction=0.5)


def test_meta_order_is_array_order_and_banks_concatenate_in_fixed_order(built):
  d = _load(built, "harm+mid")
  fs = float(d["fs"])
  for name in ("fbcsp", "harmonic", "intermediate"):
    expect = [(f.low, f.high) for f in build_bank(name, fs)[0]]
    got = [(b["low"], b["high"]) for b in d["meta"]["bands"][name]]
    assert got == pytest.approx(expect)
  want_n = {"base": 5, "harm": 5 + 14, "harm+mid": 5 + 14 + 4}
  for bank, n in want_n.items():
    dd = _load(built, bank)
    _, sub = B.feature_blocks(dd, 1, bank)
    assert sub.shape[1] == n
    pieces = [dd["bands"]["fbcsp"]] + [dd["bands"][b] for b in B.EXTRA_BANKS[bank]]
    assert np.array_equal(sub, np.concatenate(pieces, axis=1))
  # the extra bands are not sorted by frequency: harmonic centre 48 Hz (index 1) precedes 20 Hz (index 3)
  hm = d["meta"]["bands"]["harmonic"]
  assert hm[1]["low"] == pytest.approx(47.0) and hm[3]["low"] == pytest.approx(19.0)


# --- four-bank build leaves the two-bank files identical (fixed guard) --------------------------------------------------

def _sha(p):
  return hashlib.sha256(p.read_bytes()).hexdigest()


def test_four_banks_do_not_touch_two_bank_files_when_the_guard_is_fixed(tmp_path):
  block = S.make_block(n_trials=10, seed=5)
  outs = {}
  for tag, banks in (("two", ("fbcca", "fbcsp")), ("four", ALL)):
    params = S.build_params("continuous", banks=banks, guard_sec=1.5)
    built = bw.build_subject(block[:8], block[10], float(S.FS), params)
    meta = bw.build_meta(built, params, float(S.FS), "S01", "synthetic", "test")
    outs[tag] = tmp_path / tag
    bw.save_built(outs[tag], built, meta)
  two, four = ({p.name for p in outs[k].iterdir()} for k in ("two", "four"))
  assert four - two == {"X_bands_harmonic.npy", "X_bands_intermediate.npy"}
  for name in sorted(two - {"windows_meta.json"}):
    assert _sha(outs["two"] / name) == _sha(outs["four"] / name), name
  m2 = json.loads((outs["two"] / "windows_meta.json").read_text())
  m4 = json.loads((outs["four"] / "windows_meta.json").read_text())
  assert m4["bands"]["fbcca"] == m2["bands"]["fbcca"] and m4["bands"]["fbcsp"] == m2["bands"]["fbcsp"]


# --- 6 classes: selection, priors, groups, legacy -----------------------------------------------------------------------

def test_six_classes_use_201_only_with_uniform_priors_and_true_trial_groups(built, monkeypatch):
  raw_labels = np.load(built / "S01" / "y_labels.npy")
  assert (raw_labels == 202).any() and (raw_labels == 201).any()
  seen = {"priors": [], "groups": [], "ids": []}
  orig_fit = LinearDiscriminantAnalysis.fit

  def spy_fit(self, X, y, *a, **k):
    out = orig_fit(self, X, y, *a, **k)
    seen["priors"].append(np.asarray(self.priors_).copy())
    return out
  monkeypatch.setattr(LinearDiscriminantAnalysis, "fit", spy_fit)
  orig_guard = B.assert_no_shared_trials

  def spy_guard(splits, groups):
    seen["groups"].append(np.asarray(groups).copy())
    return orig_guard(splits, groups)
  monkeypatch.setattr(B, "assert_no_shared_trials", spy_guard)
  out = B.evaluate_subject(built, "S01", thresholds=TH, classes=6, repeats=2)
  cls, cm = out["confusion"]
  assert cls == [101, 102, 103, 104, 105, 201]                    # no 202 column
  assert seen["priors"] and all(p.shape == (6,) and np.allclose(p, 1 / 6) for p in seen["priors"])
  assert len(seen["groups"]) == 2                                 # one grouped-CV guard per repeat
  d = _load(built, "base", 6)
  assert np.array_equal(seen["groups"][0], d["trial_ids"])
  # trial ids are the saved ids of the rows kept, not row positions
  saved = np.load(built / "S01" / "trial_ids.npy")
  assert set(np.unique(seen["groups"][0])) <= set(np.unique(saved))
  # every 201 trial contributes at most its two windows, so rest rows / rest trials <= 2
  rest = d["y"] == 201
  assert rest.sum() <= 2 * len(np.unique(d["trial_ids"][rest]))
  assert cm[-1].sum() == 2 * rest.sum()                           # 2 repeats, each rest window predicted once


def test_five_classes_keep_the_default_prior(built, monkeypatch):
  priors = []
  orig_fit = LinearDiscriminantAnalysis.fit

  def spy_fit(self, X, y, *a, **k):
    out = orig_fit(self, X, y, *a, **k)
    priors.append(np.asarray(self.priors_).copy())
    return out
  monkeypatch.setattr(LinearDiscriminantAnalysis, "fit", spy_fit)
  B.evaluate_subject(built, "S01", thresholds=TH, classes=5)
  assert priors and all(p.shape == (5,) for p in priors)


def test_six_classes_on_a_legacy_root_raise(legacy):
  with pytest.raises(ValueError):
    B.evaluate_subject(legacy, "S03", thresholds=TH, fail_fraction=0.5, classes=6)


# --- metrics ----------------------------------------------------------------------------------------------------------

def test_metrics_on_a_hand_built_confusion():
  # rows true, columns predicted; classes 101 102 201
  cm = np.array([[6, 2, 2],      # 101: 10 windows, 6 own, 2 other stimulus, 2 to rest
                 [1, 7, 2],      # 102: 10 windows
                 [3, 1, 6]])     # 201: 10 windows, 4 predicted as a stimulus
  y = np.repeat([101, 102, 201], 10)   # one row of 10 windows per class
  y_all = np.concatenate([np.repeat(c, 10) for c in (101, 102, 201)])
  pred = np.concatenate([np.repeat([101, 102, 201], row) for row in cm])
  m = RM.rest_metrics(y_all, pred)
  assert m["FalseAct"] == pytest.approx(40.0)                      # (3 + 1) / 10
  assert m["Missed"] == pytest.approx(100 * 4 / 20)                # (2 + 2) / 20
  assert m["StimCorrect"] == pytest.approx(100 * 13 / 20)          # (6 + 7) / 20
  assert m["BalAcc"] == pytest.approx(100 * (0.6 + 0.7 + 0.6) / 3)
  assert (RM.confusion_counts(y_all, pred, [101, 102, 201]) == cm).all()
  assert RM.confusion_counts(y, y, [101, 102, 201]).tolist() == [[10, 0, 0], [0, 10, 0], [0, 0, 10]]


def test_row_metrics_are_the_definitions_applied_to_the_summed_confusion(built):
  out = B.evaluate_subject(built, "S01", thresholds=TH, classes=6, repeats=1)
  cls, cm = out["confusion"]
  r, rest, stim = out["row"], cls.index(201), [i for i, c in enumerate(cls) if c != 201]
  assert cm.sum() == len(_load(built, "base", 6)["y"])            # one repeat: every window once
  false_act = 100 * (cm[rest].sum() - cm[rest, rest]) / cm[rest].sum()
  missed = 100 * cm[np.ix_(stim, [rest])].sum() / cm[stim].sum()
  correct = 100 * sum(cm[i, i] for i in stim) / cm[stim].sum()
  recall = np.diag(cm) / cm.sum(1)
  assert r["2.0s FalseAct (%)"] == pytest.approx(false_act, abs=0.006)
  assert r["2.0s Missed (%)"] == pytest.approx(missed, abs=0.006)
  assert r["2.0s StimCorrect (%)"] == pytest.approx(correct, abs=0.006)
  assert r["2.0s BalAcc (%)"] == pytest.approx(100 * recall.mean(), abs=0.006)


def test_confusion_file_is_the_sum_of_the_subject_matrices(tmp_path):
  root = tmp_path / "r"
  S.write_built_subject(root, "S01", n_trials=10, seed=1, banks=ALL)
  S.write_built_subject(root, "S02", n_trials=10, seed=2, banks=ALL)
  assert B.main(["--data-root", str(root), "--classes", "6", "--cv-repeats", "2", "--out-suffix", "t",
                 "--reports-dir", str(tmp_path / "rep")]) == 0
  cf = pd.read_csv(tmp_path / "rep" / "n_subjects_benchmark_t_confusion.csv")
  cols = ["101", "102", "103", "104", "105", "201"]
  a, b, tot = (cf[cf["Subject"] == s][cols].to_numpy() for s in ("S01", "S02", "Sum"))
  assert np.array_equal(a + b, tot) and a.shape == (6, 6)
  # per subject: each true-class row sums to (windows of the class) x repeats
  assert a[-1].sum() % 2 == 0 and a.sum() % 2 == 0


# --- C-1 and C-2 ----------------------------------------------------------------------------------------------------------

def test_c1_mean_row_skipped_unless_requested(tmp_path):
  (tmp_path / "reports").mkdir()
  (tmp_path / "reports" / "n_subjects_benchmark.csv").write_text(
    "Subject,Clean Windows,Rejected Windows,1.0s Acc (%),2.0s Smoothed (%)\n"
    "S01,100,0,40.0,50.0\nS02,100,0,60.0,70.0\nMean,,,50.0,60.0\n")
  new = {(p, s, m): v for p, s, m, v in fb.summary_rows(tmp_path, skip_mean_row=True)}
  assert not any(k[1] == "Mean" for k in new)
  assert new[("flagship_n_subjects", "MEAN", "1.0s Acc (%)")] == pytest.approx(50.0)
  old = {(p, s, m): v for p, s, m, v in fb.summary_rows(tmp_path, skip_mean_row=False)}
  assert ("flagship_n_subjects", "Mean", "1.0s Acc (%)") in old
  assert fb.LEGACY_MEAN_ROW_TAGS == ("v1",)


def test_c2_no_threshold_fallback_and_fs_override_guard(built, legacy, tmp_path):
  with pytest.raises(ValueError):
    B.evaluate_subject(built, "S01")                                # thresholds=None
  with pytest.raises(ValueError):
    B.evaluate_subject(built, "S01", thresholds=TH, fs=250.0)       # built root: metadata fs only
  assert B.main(["--data-root", str(built), "--fs", "250", "--reports-dir", str(tmp_path)]) == 1
  ok = B.evaluate_subject(built, "S01", thresholds=TH, fs=250.0, allow_fs_override=True)
  assert ok["row"] is not None
  assert B.evaluate_subject(legacy, "S03", thresholds=TH, fail_fraction=0.5, fs=250.0)["row"] is not None


def test_c2_per_window_build_meta_is_legacy():
  block = S.make_block(n_trials=10, seed=2)
  params = S.build_params("per_window", banks=("fbcsp",), guard_sec=1.5)
  built = bw.build_subject(block[:8], block[10], float(S.FS), params)
  meta = bw.build_meta(built, params, float(S.FS), "S01", "synthetic", "test")
  assert meta["legacy"] is True
  params = S.build_params("continuous", banks=("fbcsp",), guard_sec=1.5)
  built = bw.build_subject(block[:8], block[10], float(S.FS), params)
  assert bw.build_meta(built, params, float(S.FS), "S01", "synthetic", "test")["legacy"] is False
