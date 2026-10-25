"""P04 independent known-answer tests (synthetic only, CPU, legacy Era A: fs 250 assumed in FBCCA).

Expected values come from the roadmap/plan and analytic reasoning, not from the builders' code.
Mutant tests run the same check against a deliberately buggy variant and require it to FAIL
(the check helpers raise AssertionError), proving each known-answer check has teeth.
"""

import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
import torch
from scipy.signal import periodogram
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, ClassifierMixin

from scripts.training import train_models as tm
from scripts.xai import run_xai
from src.models.cnn import spatial_spectral_cnn as cnn

ROOT = Path(__file__).resolve().parents[1]
FREQS = {101: 24.0, 102: 20.0, 103: 15.0, 104: 10.9091, 105: 8.5714}
KEEP = (1, 4, 5, 6)
BINS = (4, 6, 10, 12, 15, 17, 19, 25)


# --- shared builders -------------------------------------------------------------

def _psd_marker(n=3):
  """X_psd (n, 217): value 1000*i + 100*c + j at row i, channel c, bin j."""
  i, c, j = np.meshgrid(np.arange(n), np.arange(7), np.arange(31), indexing="ij")
  return (1000 * i + 100 * c + j).reshape(n, -1).astype(float)


def _expected_harmonic(n=3):
  return np.array([[1000 * i + 100 * KEEP[r] + BINS[c] for r in range(4) for c in range(8)]
                   for i in range(n)], dtype=float)


def _sine_window(f, fs, T, rng, amp=3.0, noise=1.0, channels=range(7)):
  t = np.arange(T) / fs
  w = rng.normal(0, noise, (7, T))
  for ch in channels:
    w[ch] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6))
  return w


# --- harmonic features (R6) --------------------------------------------------------

def check_harmonic(fn):
  got = fn(_psd_marker())
  assert got.shape == (3, 32)
  assert np.array_equal(got, _expected_harmonic())


def test_harmonic_features_channel_major():
  """Known answer: feature 8r+c = channel KEEP[r], bin BINS[c] (exact). Source: plan row 1, R6."""
  check_harmonic(tm.extract_harmonic_features)


def test_harmonic_bins_are_9_11_15_17_20_22_24_30_hz():
  """Known answer: indices 4,6,10,12,15,17,19,25 on linspace(5,35,31) = 9..30 Hz. Source: plan."""
  idx = tm.harmonic_bin_indices()
  assert idx.tolist() == list(BINS)
  assert np.linspace(5, 35, 31)[idx].tolist() == [9, 11, 15, 17, 20, 22, 24, 30]


def test_mutant_frequency_major_harmonic_flatten_fails():
  """Mutant: flatten (bin-major) -> check must fail (R6)."""
  def bad(X):
    sel = X.reshape(len(X), 7, 31)[:, list(KEEP)][:, :, list(BINS)]
    return sel.transpose(0, 2, 1).reshape(len(X), -1)
  with pytest.raises(AssertionError):
    check_harmonic(bad)


def test_keep_channel_names_asserted_pf06():
  """Known answer: positions (1,4,5,6) of the 7-ch layout are POz,O1,Oz,O2; other layouts raise."""
  import yaml
  scalp = yaml.safe_load(open(ROOT / "configs" / "pipeline_config.yaml"))["channels"]["scalp"]
  tm.check_keep_channels(scalp)
  with pytest.raises(ValueError):
    tm.check_keep_channels(["PO7"] + list(scalp))      # 8-channel layout shifts every position
  with pytest.raises(ValueError):
    tm.check_keep_channels(list(reversed(scalp)))


# --- tensor builder ----------------------------------------------------------------

def check_tensor(fn):
  t = fn(_psd_marker())
  assert t.shape == (3, 1, 4, 8)
  exp = _expected_harmonic()
  for i in range(3):
    for r in range(4):
      for c in range(8):
        assert t[i, 0, r, c] == exp[i, 8 * r + c]


def test_tensor_builder_known_layout():
  """Known answer: [i,0,r,c] = harmonic feature 8r+c (exact). Source: plan row 'tensor builder', R6."""
  check_tensor(cnn.prepare_spatial_spectral_tensors)


def test_mutant_tensor_frequency_major_fails():
  """Mutant: reshape (n,8,4) then transpose-less view as (4,8) -> check must fail."""
  def bad(X):
    f = tm.extract_harmonic_features(X)
    return f.reshape(len(f), 1, 8, 4).transpose(0, 1, 3, 2).copy().astype(np.float32).reshape(len(f), 1, 4, 8)
  with pytest.raises(AssertionError):
    check_tensor(bad)


# --- FBCCA ---------------------------------------------------------------------------

def test_fbcca_weights_and_harmonics():
  """Known answer: w_b = b^-1.25+0.25 = 1.25, 0.6704, 0.5033 (1e-4); harmonics 2,2,3,3,3."""
  assert np.allclose(tm.fbcca_weights(3), [1.25, 0.6704, 0.5033], atol=1e-4)
  assert [tm.n_harmonics(f) for f in tm.STIM_FREQS_HZ] == [2, 2, 3, 3, 3]
  ref = tm.fbcca_reference(15.0, 250, 250)
  t = np.arange(250) / 250
  assert ref.shape == (250, 6)
  assert np.allclose(ref[:, 0], np.sin(2 * np.pi * 15 * t)) and np.allclose(ref[:, 1], np.cos(2 * np.pi * 15 * t))
  assert np.allclose(ref[:, 4], np.sin(2 * np.pi * 45 * t))
  assert tm.fbcca_reference(24.0, 250, 250).shape == (250, 4)


@pytest.mark.parametrize("code", sorted(FREQS))
def test_fbcca_target_wins(code):
  """Known answer: sinusoid at target k (fs 250 consistent) + noise -> argmax k; scores in [0, sum w]."""
  rng = np.random.default_rng(code)
  s = tm.compute_fbcca_correlations(_sine_window(FREQS[code], 250, 250, rng), fs=250)
  assert int(np.argmax(s)) == code - 101
  assert np.all(s >= 0) and np.all(s <= tm.fbcca_weights(3).sum() + 1e-9)


def test_fbcca_uses_all_seven_channels():
  """Known answer: tone only on channel 0 (PO3, not a kept PSD channel) still wins (plan: all 7 channels)."""
  rng = np.random.default_rng(3)
  w = _sine_window(15.0, 250, 250, rng, amp=4.0, channels=[0])
  assert int(np.argmax(tm.compute_fbcca_correlations(w, fs=250))) == 2


def check_fs_sensitivity(fn_default):
  """24 Hz at 256 Hz: legacy default (250) differs from 256 and 256 gives a higher r for class 101."""
  rng = np.random.default_rng(11)
  w = _sine_window(24.0, 256, 256, rng, amp=3.0, noise=0.5)
  s250 = fn_default(w)
  s256 = tm.compute_fbcca_correlations(w, fs=256)
  assert tm.LEGACY_FS_HZ == 250
  assert int(np.argmax(s256)) == 0
  assert not np.allclose(s250, s256)
  assert s256[0] > s250[0]
  assert np.allclose(s250, tm.compute_fbcca_correlations(w, fs=250))   # default IS the legacy 250


def test_fbcca_legacy_fs_250_vs_256():
  """PF-04: default fs is 250 and differs from the correct 256 on 256 Hz data (legacy by design)."""
  check_fs_sensitivity(tm.compute_fbcca_correlations)


def test_mutant_fbcca_fs_256_default_fails():
  """Mutant: default silently 256 -> the legacy-default check must fail (PF-04)."""
  with pytest.raises(AssertionError):
    check_fs_sensitivity(lambda w: tm.compute_fbcca_correlations(w, fs=256))


# --- R2 in-fold scaling / R1 legacy CV ------------------------------------------------

def _offset_data(seed=0):
  rng = np.random.default_rng(seed)
  y = np.repeat(np.arange(101, 106), 20)
  X = rng.normal(size=(100, 6)) + 0.8 * np.eye(5, 6)[y - 101]
  _, te0 = next(StratifiedKFold(5, shuffle=True, random_state=42).split(X, y))
  X[te0] += 50.0                  # constant offset only in the first test fold
  return X, y


def _manual_oof(X, y, clf):
  proba = np.zeros((len(y), 5))
  for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(X, y):
    sc = StandardScaler().fit(X[tr])
    proba[te] = clf().fit(sc.transform(X[tr]), y[tr]).predict_proba(sc.transform(X[te]))
  return proba


def test_in_fold_scaling_matches_hand_per_fold():
  """Known answer: oof_predictions == per-fold hand-fitted scaler + LR (probas 1e-9). Source: R2."""
  X, y = _offset_data()
  model = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
  _, proba = tm.oof_predictions(model, X, y)
  assert np.allclose(proba, _manual_oof(X, y, lambda: LogisticRegression(max_iter=1000)), atol=1e-9)


def test_mutant_scaler_fit_on_all_windows_fails():
  """Mutant: scaler fitted on all windows (leak) gives different probabilities than the in-fold hand result."""
  X, y = _offset_data()
  Xs = StandardScaler().fit_transform(X)                           # leak
  proba = np.zeros((100, 5))
  for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(Xs, y):
    proba[te] = LogisticRegression(max_iter=1000).fit(Xs[tr], y[tr]).predict_proba(Xs[te])
  assert not np.allclose(proba, _manual_oof(X, y, lambda: LogisticRegression(max_iter=1000)), atol=1e-6)


class _Recorder(BaseEstimator, ClassifierMixin):
  fits, preds = [], []

  def fit(self, X, y):
    _Recorder.fits.append(X[:, 0].astype(int).copy())
    self.classes_ = np.unique(y)
    return self

  def predict_proba(self, X):
    _Recorder.preds.append(X[:, 0].astype(int).copy())
    return np.full((len(X), len(self.classes_)), 1.0 / len(self.classes_))

  def predict(self, X):
    return self.classes_[np.zeros(len(X), dtype=int)]


def _splits_seen(cv_factory=None, monkeypatch=None):
  y = np.repeat(np.arange(101, 106), 12)
  X = np.arange(60, dtype=float)[:, None]
  _Recorder.fits, _Recorder.preds = [], []
  if cv_factory is not None:
    monkeypatch.setattr(tm, "legacy_cv", cv_factory)
  tm.run_evaluation(X, y, "T", {"rec": _Recorder()})
  return X, y


def _assert_legacy_splits(X, y):
  exp = list(StratifiedKFold(5, shuffle=True, random_state=42).split(X, y))
  assert len(_Recorder.fits) == 5
  for (tr, te), f, p in zip(exp, _Recorder.fits, _Recorder.preds):
    assert np.array_equal(f, tr) and np.array_equal(p, te)


def test_legacy_cv_splits_equal_stratified_kfold_5_true_42():
  """Known answer: run_evaluation trains/tests on exactly StratifiedKFold(5, True, 42).split (exact). R1 legacy."""
  X, y = _splits_seen()
  _assert_legacy_splits(X, y)


def test_mutant_other_seed_cv_fails(monkeypatch):
  """Mutant: random_state=0 -> split check must fail."""
  X, y = _splits_seen(lambda: StratifiedKFold(5, shuffle=True, random_state=0), monkeypatch)
  with pytest.raises(AssertionError):
    _assert_legacy_splits(X, y)


# --- R8 legacy smoothing ------------------------------------------------------------

def _smooth_expected(p):
  out = p.copy()
  for j in range(1, len(p)):
    out[j] = (p[j - 1] + p[j]) / 2
  return out


def check_smooth(fn):
  p = np.random.default_rng(1).random((10, 5))
  p /= p.sum(1, keepdims=True)
  assert np.array_equal(fn(p)[0], p[0])
  assert np.allclose(fn(p), _smooth_expected(p), atol=1e-15)
  assert np.allclose(fn(p)[5], (p[4] + p[5]) / 2)     # no reset at j % 5 == 0


def trial_aware_smooth(p):
  out = p.copy()
  for j in range(1, len(p)):
    if j % 5:
      out[j] = (p[j - 1] + p[j]) / 2
  return out


def test_smoothing_legacy_no_reset():
  """Known answer: p0 unchanged, p_j=(p_{j-1}+p_j)/2 for every j>=1 incl. j=5 (exact). PF-02, plan row."""
  check_smooth(tm.smooth_probabilities_legacy)


def test_mutant_trial_aware_smoothing_fails():
  """Mutant: reset at j%5 (the later fix) must FAIL the pinned legacy test (R8 legacy pinned)."""
  with pytest.raises(AssertionError):
    check_smooth(trial_aware_smooth)


def test_cnn_temporal_smoothing_is_legacy(monkeypatch):
  """Known answer: row 5 is averaged with row 4 across the trial boundary: (0.9+0.0)/2 > (0.0+0.5)/2 -> class 101,
  so all 10 rows are right (accuracy 1.0, exact); the trial-aware variant gets row 5 wrong (0.9). PF-02."""
  classes = [101, 102, 103, 104, 105]
  p = np.zeros((10, 5))
  p[:, 0] = 0.5
  p[4, 0] = 0.9
  p[5] = [0.0, 0.5, 0.1, 0.0, 0.0]
  y = np.full(10, 101)
  assert cnn.evaluate_temporal_smoothing(p, y, classes) == 1.0
  monkeypatch.setattr(tm, "smooth_probabilities_legacy", trial_aware_smooth)
  assert cnn.evaluate_temporal_smoothing(p, y, classes) == pytest.approx(0.9)


def test_temporal_integration_eval_uses_legacy():
  """Known answer: accuracy of argmax of the no-reset average (exact)."""
  rng = np.random.default_rng(5)
  p = rng.random((25, 5))
  p /= p.sum(1, keepdims=True)
  y = rng.integers(101, 106, 25)
  acc, rec, pred = tm.run_temporal_integration_evaluation(p, y, [101, 102, 103, 104, 105])
  exp_pred = np.arange(101, 106)[_smooth_expected(p).argmax(1)]
  assert np.array_equal(pred, exp_pred) and acc == pytest.approx(np.mean(exp_pred == y))
  assert rec.shape == (5,)


# --- fusion CNN (R-8, forward, determinism, scalers) ----------------------------------

def check_params(m):
  convs = [l for l in m.modules() if isinstance(l, torch.nn.Conv2d)]
  assert sum(p.numel() for p in m.parameters() if p.requires_grad) == 10005
  assert len(convs) == 2 and all(c.bias is None for c in convs)


def test_fusion_cnn_params_10005_no_conv_bias():
  """Known answer: 10,005 trainable parameters, conv biases None (exact). Source: R-8."""
  check_params(cnn.DualBranchFusionCNN())


def test_mutant_conv_with_bias_fails():
  """Mutant: conv biases on -> 10,005 + 16 + 32 = 10,053 (analytic) -> check fails."""
  m = cnn.DualBranchFusionCNN()
  m.spatial[0] = torch.nn.Conv2d(1, 16, (4, 1), bias=True)
  m.spatial[4] = torch.nn.Conv2d(16, 32, (1, 3), bias=True)
  assert sum(p.numel() for p in m.parameters()) == 10005 + 48
  with pytest.raises(AssertionError):
    check_params(m)


def test_fusion_forward_shape_and_both_branches_get_gradients():
  m = cnn.DualBranchFusionCNN()
  m.train()
  xs, xf = torch.randn(6, 1, 4, 8), torch.randn(6, 5)
  out = m(xs, xf)
  assert out.shape == (6, 5)
  out.sum().backward()
  assert m.spatial[0].weight.grad.abs().sum() > 0
  assert m.fbcca[0].weight.grad.abs().sum() > 0
  assert m.head[-1].weight.grad.abs().sum() > 0


def _cnn_data(n=60, seed=0):
  rng = np.random.default_rng(seed)
  y = np.repeat(np.arange(101, 106), n // 5)
  X_psd = rng.normal(size=(n, 217)) ** 2
  fb = rng.normal(size=(n, 5)) + 2 * np.eye(5)[y - 101]
  return cnn.prepare_spatial_spectral_tensors(X_psd), fb, y


def test_cnn_cv_deterministic_and_seed_sensitive():
  """Known answer: two 2-epoch CPU runs identical (exact); a different seed differs (not a no-op). PF-28."""
  xs, fb, y = _cnn_data()
  a = cnn.train_and_eval_fusion_cnn_cv(xs, fb, y, epochs=2, device="cpu")
  b = cnn.train_and_eval_fusion_cnn_cv(xs, fb, y, epochs=2, device="cpu")
  c = cnn.train_and_eval_fusion_cnn_cv(xs, fb, y, epochs=2, device="cpu", seed=7)
  assert np.array_equal(a["pred"], b["pred"]) and np.array_equal(a["proba"], b["proba"])
  assert not np.allclose(a["proba"], c["proba"])
  assert a["proba"].shape == (60, 5) and np.allclose(a["proba"].sum(1), 1)


def _record_scalers(monkeypatch, impl):
  seen = []

  def spy(Xs, Xf):
    seen.append((Xs.copy(), Xf.copy()))
    return impl(Xs, Xf)
  monkeypatch.setattr(cnn, "fit_scalers", spy)
  return seen


def _run_scaler_cv(monkeypatch, impl):
  xs, fb, y = _cnn_data(seed=2)
  folds = list(StratifiedKFold(5, shuffle=True, random_state=42).split(xs.reshape(60, -1), y))
  xs = xs.copy()
  fb = fb.copy()
  xs[folds[0][1]] += 40.0      # planted offset in the first test fold only
  fb[folds[0][1]] += 40.0
  holder = {}
  orig = cnn.fit_scalers

  def impl_wrap(Xs, Xf):
    r = impl(Xs, Xf, xs, fb)
    holder.setdefault("sc", []).append(r)
    return r
  monkeypatch.setattr(cnn, "fit_scalers", impl_wrap)
  cnn.train_and_eval_fusion_cnn_cv(xs, fb, y, epochs=1, device="cpu")
  monkeypatch.setattr(cnn, "fit_scalers", orig)
  return xs, fb, folds, holder["sc"]


def _check_scaler_means(xs, fb, folds, scs):
  assert len(scs) == 5
  for (tr, _), (s_sp, s_fb) in zip(folds, scs):
    assert np.allclose(s_sp.mean_, xs[tr].reshape(len(tr), -1).mean(0), atol=1e-12)
    assert np.allclose(s_fb.mean_, fb[tr].mean(0), atol=1e-12)


def test_cnn_scalers_fitted_on_training_fold_only(monkeypatch):
  """Known answer: scaler means == training-fold means (1e-12) with an offset planted in test rows. R2."""
  orig = cnn.fit_scalers
  xs, fb, folds, scs = _run_scaler_cv(monkeypatch, lambda a, b, XS, FB: orig(a, b))
  _check_scaler_means(xs, fb, folds, scs)


def test_mutant_cnn_scalers_fitted_on_all_windows_fails(monkeypatch):
  """Mutant: scalers fitted on all windows -> means differ from training-fold means."""
  orig = cnn.fit_scalers
  xs, fb, folds, scs = _run_scaler_cv(monkeypatch, lambda a, b, XS, FB: orig(XS, FB))
  with pytest.raises(AssertionError):
    _check_scaler_means(xs, fb, folds, scs)


# --- XAI reshape (R6) ----------------------------------------------------------------

def check_weights(fn):
  coef = np.arange(5 * 37, dtype=float).reshape(5, 37)
  sp, fb = fn(coef)
  assert sp.shape == (5, 4, 8) and fb.shape == (5, 5)
  for k in range(5):
    for r in range(4):
      for c in range(8):
        assert sp[k, r, c] == 37 * k + 8 * r + c
  assert np.array_equal(fb, coef[:, 32:])


def test_xai_weight_arrays_channel_major():
  """Known answer: sp[k,r,c]=coef[k,8r+c]; fb=coef[:, -5:] (exact). Source: plan row 'XAI reshape', R6."""
  check_weights(run_xai.weight_arrays)
  with pytest.raises(ValueError):
    run_xai.weight_arrays(np.zeros((5, 36)))


def test_mutant_frequency_major_lda_reshape_fails():
  """Mutant: coef[:, :32].reshape(5,8,4).transpose(0,2,1) -> check must fail."""
  def bad(coef):
    return coef[:, :32].reshape(5, 8, 4).transpose(0, 2, 1), coef[:, -5:]
  with pytest.raises(AssertionError):
    check_weights(bad)


# --- synthetic legacy tree: CSV schema, exports, scripts smoke --------------------------

def _make_subject(root, subject, per_class=6, seed=0):
  rng = np.random.default_rng(seed)
  t = np.arange(256) / 256
  Xp, Xt, y = [], [], []
  for code in (201, 202) + tuple(FREQS):
    for _ in range(3 if code in (201, 202) else per_class):
      w = rng.normal(0, 1, (7, 256))
      if code in FREQS:
        w[list(KEEP)] += 3 * np.sin(2 * np.pi * FREQS[code] * t + rng.uniform(0, 6))
      f, p = periodogram(w, fs=256, axis=-1)
      Xp.append(p[:, (f >= 5) & (f <= 35)].reshape(-1)); Xt.append(w); y.append(code)
  d = root / subject
  d.mkdir(parents=True)
  np.save(d / "X_psd_features.npy", np.array(Xp))
  np.save(d / "X_time_windows.npy", np.array(Xt))
  np.save(d / "y_labels.npy", np.array(y))


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
  root = tmp_path_factory.mktemp("p04ka")
  for i, s in enumerate(("S01", "S04")):
    _make_subject(root / "processed", s, seed=i)
  return root


def _run(mod, *args):
  r = subprocess.run([sys.executable, "-m", mod, *map(str, args)], cwd=ROOT, capture_output=True, text=True, timeout=300)
  assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
  return r.stdout


def test_scripts_smoke_exports_and_csv(tree):
  """Every script exits 0 on a synthetic legacy tree; figures/CSVs written; CSV schema; export keys and reload."""
  proc, out = tree / "processed", tree / "out"
  stdout = _run("scripts.training.train_models", "--all", "--processed-dir", proc, "--out-dir", out)
  assert "legacy" in stdout and "no-reset" in stdout and "fs=250" in stdout
  for s in ("S01", "S04"):
    csv = out / "reports" / f"{s}_model_evaluation.csv"
    df = pd.read_csv(csv)
    assert list(df.columns[:4]) == ["Subject", "Classifier", "Accuracy", "Recall per Class"]
    assert len(df) == 6 and set(df.Subject) == {s}
    assert df.Accuracy.between(0, 1).all()
    assert all(len(r.strip("[]").split(",")) == 5 for r in df["Recall per Class"])
    assert len(list((out / "figures" / "confusion_matrices" / s).glob("cm_*.png"))) == 6
  assert len(list((out / "figures" / "confusion_matrices").glob("cm_*.png"))) == 6      # S01 at root path

  # independent recomputation of the LDA row (out-of-fold accuracy and no-reset smoothed accuracy)
  X_psd = np.load(proc / "S01" / "X_psd_features.npy"); X_t = np.load(proc / "S01" / "X_time_windows.npy")
  y_all = np.load(proc / "S01" / "y_labels.npy"); m = np.isin(y_all, list(FREQS))
  y = y_all[m]
  H = np.hstack([_expected_harmonic_from(X_psd[m]), np.stack([tm.compute_fbcca_correlations(w, 250) for w in X_t[m]])])
  from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
  pred = np.zeros(len(y), int); proba = np.zeros((len(y), 5))
  for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(H, y):
    sc = StandardScaler().fit(H[tr]); l = LDA(solver="lsqr", shrinkage="auto").fit(sc.transform(H[tr]), y[tr])
    pred[te] = l.predict(sc.transform(H[te])); proba[te] = l.predict_proba(sc.transform(H[te]))
  row = pd.read_csv(out / "reports" / "S01_model_evaluation.csv").set_index("Classifier").loc["Shrinkage-LDA"]
  assert row.Accuracy == pytest.approx(np.mean(pred == y), abs=1e-4 + 1e-12)
  sm = np.arange(101, 106)[_smooth_expected(proba).argmax(1)]
  assert row["Smoothed Accuracy"] == pytest.approx(np.mean(sm == y), abs=1e-12 + 1e-4)

  for s in ("S01", "S04"):
    _run("scripts.training.train_final_model", "--subject", s, "--processed-dir", proc, "--out-dir", out,
         "--epochs", 2, "--device", "cpu")
  _run("scripts.training.train_final_model", "--subject", "S01", "--processed-dir", proc, "--out-dir", out / "lda_only",
       "--skip-cnn")
  assert not (out / "lda_only" / "models" / "S01_fusion_cnn.pt").exists()
  assert (out / "lda_only" / "models" / "S01_shrinkage_lda.joblib").is_file()

  b = joblib.load(out / "models" / "S01_shrinkage_lda.joblib")
  assert {"model", "scaler", "classes", "subject_id", "feature_dim"} <= set(b)
  assert b["classes"] == [101, 102, 103, 104, 105] and b["subject_id"] == "S01" and b["feature_dim"] == 37
  assert "full data" in b["fit"]
  assert np.array_equal(b["model"].predict(b["scaler"].transform(H)),
                        LDA(solver="lsqr", shrinkage="auto").fit(StandardScaler().fit_transform(H), y)
                        .predict(StandardScaler().fit_transform(H)))

  d = torch.load(out / "models" / "S01_fusion_cnn.pt", weights_only=False)
  assert {"state_dict", "scalers", "classes", "label_map", "subject_id", "architecture", "n_parameters", "fit",
          "train_accuracy"} <= set(d)
  assert d["n_parameters"] == 10005 and d["classes"] == [101, 102, 103, 104, 105] and "full data" in d["fit"]
  assert d["label_map"] == {101: 0, 102: 1, 103: 2, 104: 3, 105: 4}
  net = cnn.DualBranchFusionCNN(); net.load_state_dict(d["state_dict"]); net.eval()
  xs, xf = cnn.apply_scalers(d["scalers"], cnn.prepare_spatial_spectral_tensors(X_psd[m]), H[:, -5:])
  p = cnn.predict_proba(net, xs, xf, torch.device("cpu"))
  assert np.mean(p.argmax(1) == (y - 101)) == pytest.approx(d["train_accuracy"], abs=1e-12)    # reload consistency

  _run("scripts.xai.run_xai", "--subject", "S04", "--processed-dir", proc, "--out-dir", out)
  _run("scripts.xai.compare_subject_xai", "--out-dir", out)
  xd = out / "figures" / "xai_heatmaps"
  for f in ("xai_spatial_spectral_weights.png", "xai_fbcca_weights.png", "compare_S01_S04.png"):
    assert (xd / f).stat().st_size > 1000

  _run("scripts.training.batch_run_subjects", "--subjects", "S01", "S04", "--processed-dir", proc,
       "--out-dir", out, "--epochs", 2, "--device", "cpu")
  bd = pd.read_csv(out / "reports" / "batch_run_subjects.csv")
  assert {"Subject", "LDA 1.0 s", "LDA smoothed", "CNN 1.0 s", "CNN train acc", "CNN smoothed", "n_windows"} <= set(bd.columns)
  assert list(bd.Subject) == ["S01", "S04"]
  assert bd["LDA 1.0 s"].iloc[0] == pytest.approx(row.Accuracy, abs=1e-12)     # batch LDA == train_models LDA
  _run("scripts.training.batch_run_subjects", "--subjects", "S01", "--processed-dir", proc, "--out-dir",
       out / "nocnn", "--skip-cnn")
  assert "CNN 1.0 s" not in pd.read_csv(out / "nocnn" / "reports" / "batch_run_subjects.csv").columns


def _expected_harmonic_from(X_psd):
  """Independent harmonic extraction by explicit indexing (channel-major)."""
  return np.array([[row.reshape(7, 31)[KEEP[r], BINS[c]] for r in range(4) for c in range(8)] for row in X_psd])
