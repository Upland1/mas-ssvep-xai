"""P05 Round 2 independent known-answer tests (synthetic-tester).

Decisions under test (mas/state/decisions.md, last three P05 rows): (1) reported "2.0 s smoothed" is the
legacy i % 5 trial smoothing, no-reset only a diagnostic; (2) extractor mask vpp 0.5-120 uV, std 0.1-35 uV;
(3) harmonic+FBCCA script gives FBCCA the visual cluster PO8, O1, Oz, O2 by name, with the single mask.
Expected values are written from the definitions; mutants are defined in this file. Synthetic only.
"""

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks.feature_based import benchmark_harmonic_fbcca as bhf
from scripts.evaluation import evaluate_confusion_matrix as ecm
from src.features.ssvep import fbcca_extraction as fb
from src.features.ssvep.harmonic_psd import VISUAL_CLUSTER
from src.features.ssvep.psd_extraction import extract_continuous_psd_features
from src.features.ssvep.window_mask import P05_MASK_THRESHOLDS, resolve_window_mask
from src.models.classical import feature_spaces as fsp
from src.models.classical import legacy_eval as le
from tests.p05_synth import SCALP, make_windows, write_subject

T = 256
OLD_LIMITS = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}


def _i5_accuracy(y, scores):
  """Definition written out: row i = row i if i % 5 == 0 else (row i-1 + row i) / 2; argmax -> sorted classes."""
  out = scores.copy()
  for i in range(len(scores)):
    if i % 5 != 0:
      out[i] = (scores[i - 1] + scores[i]) / 2
  return float(np.mean(np.unique(y)[out.argmax(1)] == y))


def _noreset_accuracy(y, scores):
  out = scores.copy()
  out[1:] = (scores[:-1] + scores[1:]) / 2
  return float(np.mean(np.unique(y)[out.argmax(1)] == y))


# --- (1) reported smoothing = i % 5 -----------------------------------------------------------------

def _hand_scores():
  """10 windows, two trials of 5: trial 1 true 101, trial 2 true 102. Row 5 (first window of trial 2) is weakly
  correct [0.45, 0.55]; every other row is confident and correct. Row 4 is [0.9, 0.1]."""
  y = np.array([101] * 5 + [102] * 5)
  s = np.where((y == 101)[:, None], [0.9, 0.1], [0.1, 0.9]).astype(float)
  s[5] = [0.45, 0.55]
  return y, s


def test_accuracies_uses_trial_reset_at_i_mod_5():
  """Known answer: i%5 smoothing leaves row 5 = [0.45, 0.55] (class 102, correct) so 2.0 s accuracy is 10/10 = 1.0;
  the no-reset average would give row 5 = (0.9+0.45)/2 = 0.675 vs 0.325 -> class 101 (wrong): 9/10 = 0.9.
  `le.accuracies` must return 1.0 (exact); the 1.0 s accuracy is from the given predictions (10/10)."""
  y, s = _hand_scores()
  pred = np.unique(y)[s.argmax(1)]
  a1, a2 = le.accuracies(y, pred, s)
  assert a1 == 1.0 and a2 == 1.0
  assert _i5_accuracy(y, s) == 1.0 and _noreset_accuracy(y, s) == 0.9


def test_accuracies_mutant_no_reset_fails(monkeypatch):
  """Mutant: `accuracies` wired to the no-reset rule returns 0.9 on the hand example, so the exact-1.0 check fails."""
  from src.preprocessing.dataset.smoothing import smooth_probabilities_legacy
  monkeypatch.setattr(le, "smooth_reported", smooth_probabilities_legacy)
  y, s = _hand_scores()
  assert le.accuracies(y, np.unique(y)[s.argmax(1)], s)[1] == 0.9


def test_trial_reset_is_on_clean_array_index_not_trial_ids():
  """Known answer (decisions.md: reset at i % 5 == 0 of the CLEAN array): with 12 rows the resets are rows 0, 5, 10;
  row 10 equals itself, row 11 averages rows 10 and 11, row 6 averages rows 5 and 6."""
  from src.preprocessing.dataset.smoothing import smooth_probabilities_mod5
  p = np.arange(12, dtype=float)[:, None] * np.ones((1, 3))
  o = smooth_probabilities_mod5(p)[:, 0]
  assert o.tolist() == [0, 0.5, 1.5, 2.5, 3.5, 5, 5.5, 6.5, 7.5, 8.5, 10, 10.5]


def test_reported_flagship_csv_uses_i_mod_5(tmp_path, monkeypatch):
  """The reported 2.0 s of `flagship_S03.csv` equals the accuracy of an independent i%5 smoothing of the same
  out-of-fold scores (2 decimals) and the SMOOTH_LABEL names i%5. Noisy tree (snr 0.15) so the two rules differ."""
  write_subject(tmp_path / "processed", "S03", n_trials=6, snr=0.15, seed=31)
  captured = {}
  orig = le.oof_space

  def spy(space, sub, yy, models, seed=42, splits=None):
    res, errs = orig(space, sub, yy, models, seed, splits)
    captured["res"], captured["y"] = res, yy
    return res, errs

  monkeypatch.setattr(ecm, "oof_space", spy)
  rc = ecm.main(["--subject", "S03", "--processed-dir", str(tmp_path / "processed"), "--reports-dir", str(tmp_path / "rep"),
                 "--figures-dir", str(tmp_path / "fig"), "--no-figures"])
  assert rc == 0
  r = captured["res"]["Shrinkage-LDA lsqr"]
  yy = captured["y"]
  df = pd.read_csv(tmp_path / "rep" / "flagship_S03.csv")
  assert df.loc[0, "2.0s Smoothed (%)"] == round(100 * _i5_accuracy(yy, r["scores"]), 2)
  assert _i5_accuracy(yy, r["scores"]) != _noreset_accuracy(yy, r["scores"])      # the rules are distinguishable here
  assert "i%5" in le.SMOOTH_LABEL and "no-reset" not in le.SMOOTH_LABEL.split("DIAGNOSTIC")[0]
  assert "DIAGNOSTIC" in le.DIAG_SMOOTH_LABEL


def test_argmax_baseline_row_is_smoothed_with_i_mod_5(tmp_path):
  """The zero-training FBCCA argmax row of the benchmark CSV uses i%5 as well: recompute from the blocks (FBCCA
  scores row-normalised, argmax over classes) and compare to the CSV row (2 decimals)."""
  from scripts.benchmarks.feature_based import benchmark_cross_validation as bcv
  from src.models.classical.benchmark_runner import prepare_subject
  write_subject(tmp_path / "processed", "S03", n_trials=4, snr=0.15, seed=32)
  blocks = prepare_subject(tmp_path / "processed", "S03", SCALP)
  # run only the baseline part of run_benchmark by stubbing the (empty) list of feature spaces
  orig = bcv.benchmark_spaces
  bcv.benchmark_spaces = lambda b, m=1: []
  try:
    rows, _ = bcv.run_benchmark(blocks, "S03", verbose=False)
  finally:
    bcv.benchmark_spaces = orig
  row = [r for r in rows if r["Model"] == "argmax"][0]
  s = blocks["fbcca"] / blocks["fbcca"].sum(1, keepdims=True)
  assert row["2.0s Smoothed (%)"] == round(100 * _i5_accuracy(blocks["y"], s), 2)


# --- (2) mask limits ---------------------------------------------------------------------------------

def _tiny_window():
  """All 7 channels: 32 samples +1, 32 samples -1, rest 0 -> vpp 2 uV, std sqrt(64/256) = 0.5 uV."""
  w = np.zeros((7, T))
  w[:, :32], w[:, 32:64] = 1.0, -1.0
  return w


def _mask_batch():
  X, y = make_windows(n_trials=1, seed=40)
  X = X.copy()
  X[0] = _tiny_window()
  return X, y


def test_mask_limits_are_0p5_120_and_0p1_35():
  """Known answer (decisions.md P05): thresholds exactly vpp 0.5-120, std 0.1-35."""
  assert P05_MASK_THRESHOLDS == {"vpp_min": 0.5, "vpp_max": 120.0, "std_min": 0.1, "std_max": 35.0}


def _check_tiny_window_kept(mask_fn):
  X, _ = _mask_batch()
  w = _tiny_window()
  assert np.isclose(np.ptp(w, axis=1), 2.0).all() and np.isclose(w.std(axis=1), 0.5).all()
  m = mask_fn(X)
  assert m[0] == 1 and m.sum() == len(X)


def test_window_with_vpp2_std0p5_is_kept_by_default_gate_and_rejected_by_old_limits():
  """Known answer: a window with Vpp 2 uV / std 0.5 uV on every channel is kept by the default (0.5/0.1) gate and
  by every extractor and block builder; under the superseded 5/1 limits it is rejected, so the check fails on that
  mutant. Boundary cases: Vpp 0.4 (< 0.5) or std 0.05 (< 0.1) is rejected; Vpp 130 (> 120) is rejected."""
  X, y = _mask_batch()
  _check_tiny_window_kept(lambda A: resolve_window_mask(A))
  with pytest.raises(AssertionError):
    _check_tiny_window_kept(lambda A: resolve_window_mask(A, thresholds=OLD_LIMITS))
  P, yc, m = extract_continuous_psd_features(X, y)
  assert m[0] == 1 and len(P) == len(X)
  F, _, mf = fb.extract_fbcca_features(X, y)
  assert mf[0] == 1 and len(F) == len(X)
  b = fsp.build_feature_blocks(X, y, SCALP)
  assert b["mask"][0] == 1 and all(len(b[k]) == len(X) for k in ("y", "psd", "harmonic", "fbcca", "subbands"))
  assert fsp.build_feature_blocks(X, y, SCALP, thresholds=OLD_LIMITS)["mask"][0] == 0
  for amp, why in ((0.2, "vpp 0.4"), (0.025, "std ~0.05"), (65.0, "vpp 130")):
    Z = X.copy()
    Z[1] = 0.0
    Z[1, :, :32], Z[1, :, 32:64] = amp, -amp
    if why == "std ~0.05":
      Z[1] = 0.0
      Z[1, :, 0] = 0.1                                   # vpp 0.1: fails vpp_min 0.5 (std ~0.006 also < 0.1)
    assert resolve_window_mask(Z)[1] == 0, why


# --- (3) FBCCA on PO8, O1, Oz, O2 by name with the shared mask -------------------------------------------

NAMES = ["O2", "PO3", "Oz", "POz", "PO8", "O1", "PO4"]


def _cluster_idx(names):
  return [names.index(n) for n in VISUAL_CLUSTER]


def test_fbcca_block_uses_named_cluster_channels_in_cluster_order():
  """Known answer: for any channel-name order the FBCCA block equals the extractor run on the columns that carry
  PO8, O1, Oz, O2 (in that order), with the same mask; without `fbcca_channels` it uses all 7 channels and differs.
  Tolerance 1e-9."""
  X, y = make_windows(n_trials=2, seed=41)
  for names in (SCALP, NAMES, list(reversed(SCALP))):
    b = fsp.build_feature_blocks(X, y, names, fbcca_channels=VISUAL_CLUSTER)
    ref, _, _ = fb.extract_fbcca_features(X[:, _cluster_idx(names)], y, valid_mask=b["mask"])
    assert b["fbcca_channels"] == list(VISUAL_CLUSTER)
    assert np.allclose(b["fbcca"], ref, atol=1e-9)
  full = fsp.build_feature_blocks(X, y, NAMES)
  assert not np.allclose(full["fbcca"], b["fbcca"])
  # wrong positional pick (the P04-style POz set) differs from the named pick
  wrong = fsp.build_feature_blocks(X, y, NAMES, fbcca_channels=("POz", "O1", "Oz", "O2"))
  assert not np.allclose(wrong["fbcca"], fsp.build_feature_blocks(X, y, NAMES, fbcca_channels=VISUAL_CLUSTER)["fbcca"])


def test_mask_stays_shared_when_only_a_non_cluster_channel_is_bad():
  """PF-10 known answer: window 7 has an artefact (vpp 400) on PO3 only, which is not in the cluster. The single
  mask (computed on all channels) rejects it, so psd, harmonic, FBCCA (cluster only), subbands and y all have n - 1
  rows. Mutant: gating the 4-channel FBCCA input on its own keeps the window (n rows) and misaligns the blocks."""
  X, y = make_windows(n_trials=2, seed=42)
  X = X.copy()
  bad = 7
  X[bad, SCALP.index("PO3")] += 200.0 * np.sign(np.sin(np.arange(T)))
  b = fsp.build_feature_blocks(X, y, SCALP, fbcca_channels=VISUAL_CLUSTER)
  keys = ("y", "psd", "harmonic", "fbcca", "subbands")
  assert b["mask"][bad] == 0 and b["mask"].sum() == len(X) - 1
  assert all(len(b[k]) == len(X) - 1 for k in keys)
  mutant, _, _ = fb.extract_fbcca_features(X[:, _cluster_idx(SCALP)], y)          # own gate on 4 channels
  assert len(mutant) == len(X) and len(mutant) != len(b["psd"])


def test_harmonic_script_requests_the_visual_cluster(tmp_path, monkeypatch, capsys):
  """The script `benchmark_harmonic_fbcca` calls `prepare_subject(..., fbcca_channels=PO8, O1, Oz, O2)` (spy), prints
  the channels, and its saved report names them; the other spaces are unaffected (block keeps 5 FBCCA scores)."""
  write_subject(tmp_path / "processed", "S03", n_trials=4, seed=43)
  seen = {}
  orig = bhf.prepare_subject

  def spy(*a, **k):
    seen.update(k)
    return orig(*a, **k)

  monkeypatch.setattr(bhf, "prepare_subject", spy)
  rc = bhf.main(["--subject", "S03", "--processed-dir", str(tmp_path / "processed"), "--reports-dir", str(tmp_path / "rep"),
                 "--figures-dir", str(tmp_path / "fig")])
  assert rc == 0
  assert tuple(seen["fbcca_channels"]) == ("PO8", "O1", "Oz", "O2")
  assert "PO8, O1, Oz, O2" in capsys.readouterr().out
  txt = (tmp_path / "rep" / "classification_report_benchmark_harmonic_fbcca_S03.txt").read_text()
  assert "FBCCA on PO8, O1, Oz, O2" in txt
