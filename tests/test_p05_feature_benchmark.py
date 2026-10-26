"""P05 tests (ml-engineer): extractors, CSP, suite, benchmark helpers, scripts on a synthetic legacy tree.

Synthetic data only (tests/p05_synth.py, fixed seeds); fs 250 as the legacy Era A extractors assume.
"""

import numpy as np
import pandas as pd
import pytest
from scipy.signal import cheby1, freqz
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
from sklearn.model_selection import StratifiedKFold

from scripts.benchmarks.feature_based import benchmark_cross_validation as bcv
from scripts.benchmarks.feature_based import benchmark_harmonic_fbcca as bhf
from scripts.evaluation import evaluate_confusion_matrix as ecm
from scripts.evaluation import test_sklearn_models as tsm
from scripts.exploration import visualize_data as vd
from scripts.training import train_models as tm
from src.features.ssvep import fbcca_extraction as fb
from src.features.ssvep import fbcsp_extraction as csp
from src.features.ssvep.harmonic_psd import VISUAL_CLUSTER, visual_cluster_harmonic_psd
from src.features.ssvep.psd_extraction import continuous_psd_freqs, extract_continuous_psd_features
from src.features.ssvep.window_mask import GATE_THRESHOLDS, NO_CHANNEL_DROP, P05_MASK_THRESHOLDS
from src.models.classical import legacy_eval as le
from src.models.classical.feature_spaces import build_feature_blocks
from src.models.classical.sklearn_models import MODEL_NAMES, get_sklearn_model_suite
from src.preprocessing.dataset.smoothing import smooth_probabilities_legacy, smooth_probabilities_mod5
from tests.p05_synth import FS, SCALP, TARGETS, keep_all, make_windows, write_subject


# --- FBCCA ----------------------------------------------------------------------

def test_reference_signals_known_answer():
  """Known answer: rows sin/cos(2 pi h f t), t = n/250, h = 1..3, shape (6, 256). Tolerance 1e-12 (spec P05.1)."""
  r = fb.generate_reference_signals(15.0, 250.0, 256, 3)
  assert r.shape == (6, 256)
  t = np.arange(256) / 250.0
  for h in (1, 2, 3):
    assert np.allclose(r[2 * (h - 1)], np.sin(2 * np.pi * h * 15.0 * t), atol=1e-12)
    assert np.allclose(r[2 * (h - 1) + 1], np.cos(2 * np.pi * h * 15.0 * t), atol=1e-12)


def test_chebyshev_subbands_design_and_gain():
  """Known answer: 3 order-4, 3 dB ripple band-pass filters on [6|14|22, 90] Hz (spec P05.1); same
  coefficients as scipy cheby1; |H| ~ 1 inside the band, << 1 at 2 Hz; at fs 256 the high edge is still 90."""
  bands = fb.get_chebyshev_subbands(250.0)
  assert len(bands) == 3
  for (b, a), low in zip(bands, (6, 14, 22)):
    b0, a0 = cheby1(4, 3, [low, 90], btype="band", fs=250.0)
    assert np.allclose(b, b0) and np.allclose(a, a0)
    assert len(a) == 9                                         # order 4 band-pass -> 8th-order polynomial
    w, h = freqz(b, a, worN=[2.0, 40.0], fs=250.0)
    assert abs(h[0]) < 0.01 and 0.7 < abs(h[1]) <= 1.01       # ripple 3 dB = 0.708
  for (b, a), low in zip(fb.get_chebyshev_subbands(256.0), (6, 14, 22)):
    b0, a0 = cheby1(4, 3, [low, 90], btype="band", fs=256.0)   # nyq - 1 = 127 > 90
    assert np.allclose(b, b0)


def test_fbcca_planted_sinusoid_picks_its_target():
  """Known answer: a 7-channel window with a sinusoid at target k (+ noise) has its largest FBCCA score at k, X (5, 5)."""
  X, y = make_windows(n_trials=1, seed=3)
  Xf, yf, mask, _ = fb.extract_fbcca_features(X[::5], y[::5])   # one window per class
  assert Xf.shape == (5, 5) and mask.tolist() == [1] * 5
  assert np.argmax(Xf, axis=1).tolist() == [0, 1, 2, 3, 4]
  assert np.all(Xf >= 0) and np.all(Xf <= fb.fbcca_weights(3).sum() + 1e-9)


def test_fbcca_weights_known_values():
  assert np.allclose(fb.fbcca_weights(3), [1.25, 0.6704, 0.5033], atol=1e-4)


def test_fbcca_constant_window_gives_zero_not_exception():
  """Known answer: a constant band cannot be correlated: r = 0 exactly (CCA failure path), and the window score stays finite, no exception."""
  const = np.full((7, 256), 3.0)
  assert fb.canonical_correlation(const.T, fb.generate_reference_signals(15.0, 250.0, 256).T) == 0.0
  s = fb.fbcca_window_scores(const, fb.get_chebyshev_subbands(250.0),
                             [fb.generate_reference_signals(f, 250.0, 256) for f in fb.TARGET_FREQS])
  assert s.shape == (5,) and np.all(np.isfinite(s)) and np.all(s >= 0)   # filtfilt edge transients stay finite


# --- CSP / FBCSP -------------------------------------------------------------------

def _csp_data(seed=0, C=7, T=256, n=40, gain=3.0):
  rng = np.random.default_rng(seed)
  U = np.linalg.qr(rng.normal(size=(C, C)))[0]
  X, y = [], []
  for k in range(5):
    for _ in range(n):
      X.append(rng.normal(size=(C, T)) + gain * np.outer(U[:, k], rng.normal(size=T)))
      y.append(101 + k)
  return np.stack(X), np.array(y), U


def test_csp_known_answer_aligns_with_planted_spatial_vector():
  """Known answer: class k has extra variance along orthonormal u_k; its first (largest-eigenvalue)
  filter has |cos| > 0.95 with u_k; filters (K, C, 2m); features (n, 5 * 2m)."""
  X, y, U = _csp_data()
  c = csp.MulticlassCSP(1).fit(X, y)
  assert c.filters_.shape == (5, 7, 2)
  for k in range(5):
    f = c.filters_[k][:, 0]
    assert abs(f @ U[:, k]) / np.linalg.norm(f) > 0.95
  assert c.transform(X).shape == (len(X), 10)
  assert csp.MulticlassCSP(2).fit(X, y).transform(X).shape == (len(X), 20)


def test_csp_math_eigenvalues_and_features():
  """Known answer: eigenvalues of eigh(St, St+Sr+1e-6 I) lie in (0, 1); features equal
  log10(var_j / sum_j var_j) of the projections (floor 1e-12); independent recomputation, tol 1e-9."""
  X, y, _ = _csp_data(seed=1)
  c = csp.MulticlassCSP(1).fit(X, y)
  assert np.all(c.eigenvalues_ > 0) and np.all(c.eigenvalues_ < 1)
  assert np.all(c.eigenvalues_[:, 0] > c.eigenvalues_[:, 1])           # m largest first, then m smallest
  F = c.transform(X)
  w = X[7]
  for k in range(5):
    v = np.array([np.var(c.filters_[k][:, j] @ w) for j in range(2)])
    v = np.maximum(v, 1e-12)
    assert np.allclose(F[7, 2 * k:2 * k + 2], np.log10(v / v.sum()), atol=1e-9)


def test_csp_trace_normalised_covariance_is_scale_free():
  """Known answer: scaling one window by 100 does not change the fitted filters beyond the 1e-6 ridge effect."""
  X, y, _ = _csp_data(seed=2)
  X2 = X.copy()
  X2[0] *= 100.0
  f1 = csp.MulticlassCSP(1).fit(X, y).filters_
  f2 = csp.MulticlassCSP(1).fit(X2, y).filters_
  assert np.allclose(np.abs(np.einsum("kcj,kcj->kj", f1, f2)) / (np.linalg.norm(f1, axis=1) * np.linalg.norm(f2, axis=1)), 1.0, atol=1e-2)


def test_fbcsp_layout_is_band_class_component():
  """R6 known answer: (n, 50) for m = 1; column ((b*5)+k)*2 + j = band b, class k, component j; a source planted
  only in band 2 (18-26 Hz) separates the classes in the band-2 columns."""
  rng = np.random.default_rng(5)
  C, T, n = 7, 256, 30
  t = np.arange(T) / FS
  U = np.linalg.qr(rng.normal(size=(C, C)))[0]
  X, y = [], []
  for k in range(5):
    for _ in range(n):
      x = rng.normal(size=(C, T))
      x += 6.0 * np.outer(U[:, k], np.sin(2 * np.pi * 22.0 * t + rng.uniform(0, 6.28)))
      X.append(x); y.append(101 + k)
  X, y = np.stack(X), np.array(y)
  sw = csp.filter_subbands(X, FS)
  assert sw.shape == (len(X), 5, C, T)
  tr = csp.FBCSPTransformer(1).fit(sw, y)
  F = tr.transform(sw)
  assert F.shape == (len(X), 50)
  for b in range(5):
    for k in range(5):
      cols = F[:, (b * 5 + k) * 2:(b * 5 + k) * 2 + 2]
      assert np.allclose(cols, tr.csps_[b].transform(sw[:, b])[:, 2 * k:2 * k + 2])
  # separation of the first component of class k (own minus other windows): >= 1.9 in band 2, <= 0.6 elsewhere
  # (the small band-0/1 value is CSP fitting class-specific noise on 30 windows); a band/class mix-up fails this.
  for k in range(5):
    sep = [F[y == 101 + k, (b * 5 + k) * 2].mean() - F[y != 101 + k, (b * 5 + k) * 2].mean() for b in range(5)]
    assert sep[2] > 1.5 and max(sep[b] for b in (0, 1, 3, 4)) < 1.0


def test_butter_bandpass_caps_high_edge_at_nyquist_minus_one():
  """Known answer: high = min(high, nyq - 1): a 200 Hz request at fs 250 is designed to 124 Hz without error."""
  x = np.random.default_rng(0).normal(size=(2, 256))
  y = csp.butter_bandpass_filter(x, 7, 200, 250.0)
  assert y.shape == x.shape and np.all(np.isfinite(y))


# --- PSD ---------------------------------------------------------------------------

def test_continuous_psd_shape_and_bins():
  """Known answer: 256-sample windows at fs 250, 5-35 Hz -> 30 bins 5.859...34.180 Hz, (n, 7*30 = 210)."""
  X, y = make_windows(n_trials=1)
  P, yc, mask, _ = extract_continuous_psd_features(X, y)
  assert P.shape == (len(X), 210) and len(yc) == len(X)
  f = continuous_psd_freqs(256, 250.0, (5, 35))
  assert len(f) == 30 and np.isclose(f[0], 6 * 250 / 256) and np.isclose(f[-1], 35 * 250 / 256)
  Pdb, _, _, _ = extract_continuous_psd_features(X, y, use_db=True)
  assert np.allclose(Pdb, 10 * np.log10(P + 1e-12))


def test_visual_cluster_selects_by_name_not_position():
  """PF-06 known answer: each channel's PSD is constant = its own name code; whatever order the names come in,
  the harmonic PSD holds PO8, O1, Oz, O2 (in that order), 8 bins each = 32 features."""
  freqs = continuous_psd_freqs(256, 250.0)
  code = {n: i + 1 for i, n in enumerate(SCALP)}
  for names in (SCALP, list(reversed(SCALP)), ["O2", "PO3", "Oz", "POz", "PO8", "O1", "PO4"]):
    psd = np.stack([np.full(len(freqs), float(code[n])) for n in names])[None].reshape(1, -1)
    H = visual_cluster_harmonic_psd(psd, freqs, names)
    assert H.shape == (1, 32)
    assert H.reshape(4, 8).mean(axis=1).tolist() == [code[n] for n in VISUAL_CLUSTER]
  with pytest.raises(ValueError):
    visual_cluster_harmonic_psd(psd, freqs, SCALP[:-1])        # name list of the wrong length


def test_harmonic_bins_on_fs250_grid():
  """Known answer: nearest bins of the 250/256 Hz grid to [8.57, 10.91, 15, 17.14, 20, 21.82, 24, 30] are
  k = 9, 11, 15, 18, 20, 22, 25, 31 (8 distinct), i.e. 8.79, 10.74, 14.65, 17.58, 19.53, 21.48, 24.41, 30.27 Hz."""
  from src.features.ssvep.harmonic_psd import nearest_bin_indices
  f = continuous_psd_freqs(256, 250.0)
  assert np.round(f[nearest_bin_indices(f)] * 256 / 250).astype(int).tolist() == [9, 11, 15, 18, 20, 22, 25, 31]


# --- Mask (PF-10) ----------------------------------------------------------------------

def test_single_mask_aligns_every_block():
  """PF-10 known answer: one window with a huge artefact is removed from EVERY block, the others keep their
  rows (blocks equal the extractors run on the clean windows alone); the thresholds are the explicit shared ones."""
  X, y = make_windows(n_trials=2, seed=4)
  bad = 17
  X = X.copy()
  X[bad, 3, :] += 500.0 * np.sin(np.arange(256))
  b = build_feature_blocks(X, y, SCALP)
  assert b["thresholds"] == GATE_THRESHOLDS and b["channels_dropped"] == []
  assert b["mask"].sum() == len(X) - 1 and b["mask"][bad] == 0
  n = len(X) - 1
  assert all(len(b[k]) == n for k in ("y", "psd", "harmonic", "fbcca", "subbands"))
  keep = np.delete(np.arange(len(X)), bad)
  ref, _, _, _ = fb.extract_fbcca_features(X[keep], y[keep], precomputed=keep_all(n))
  assert np.allclose(b["fbcca"], ref)


def test_extractors_do_not_regate_when_given_a_mask():
  """PF-10 known answer: a window failing the extractor gate (flat: vpp 0) is kept when the decision handed in
  (`precomputed`) says 1 and dropped by the extractor's own gate otherwise (no second, different decision)."""
  X, y = make_windows(n_trials=1, seed=6)
  X = X.copy()
  X[2] = 0.0
  own, _, m_own, _ = extract_continuous_psd_features(X, y)
  forced, _, m_forced, _ = extract_continuous_psd_features(X, y, precomputed=keep_all(len(X)))
  assert m_own[2] == 0 and len(own) == len(X) - 1
  assert len(forced) == len(X) and m_forced.all()
  with pytest.raises(ValueError):
    extract_continuous_psd_features(X, y, precomputed=keep_all(len(X) - 1))
  with pytest.raises(ValueError):
    extract_continuous_psd_features(X, y, thresholds={"vpp_min": 5.0})   # R5: every limit explicit


# --- In-fold CSP (PF-11) ------------------------------------------------------------------

def test_fold_matrices_never_see_test_rows():
  """PF-11 known answer: the training matrix of a fold is unchanged when the test windows are replaced by
  anything (a planted pattern only in test rows); a CSP fitted on all rows (historical bug) does change it."""
  X, y = make_windows(n_trials=4, seed=7)
  sub = csp.filter_subbands(X, FS)
  space = le.FeatureSpace("FBCSP", [], fbcsp_m=1)
  tr, te = next(le.legacy_cv().split(np.zeros(len(y)), y))
  Xtr, Xte = le.fold_matrices(space, sub, y, tr, te)
  sub2 = sub.copy()
  rng = np.random.default_rng(1)
  sub2[te] = 30.0 * rng.normal(size=sub2[te].shape) * np.linspace(1, 8, 7)[None, None, :, None]   # test-only pattern
  Xtr2, Xte2 = le.fold_matrices(space, sub2, y, tr, te)
  assert np.array_equal(Xtr, Xtr2)
  assert not np.allclose(Xte, Xte2)
  # the historical bug: filters fitted on all rows leak the test pattern into the training features
  leaky = csp.FBCSPTransformer(1).fit(sub2, y).transform(sub2[tr])
  assert not np.allclose(leaky, Xtr)


def test_oof_pipeline_fits_scaler_on_training_fold_only():
  """R2 known answer: a feature whose scale differs hugely only in the test rows does not change the
  predictions of training rows' model: the out-of-fold prediction of test rows uses train statistics."""
  rng = np.random.default_rng(0)
  y = np.repeat(np.arange(101, 106), 20)
  Xs = rng.normal(size=(100, 4)) + (y[:, None] - 103) * 0.8
  space = le.FeatureSpace("S", [Xs])
  splits = list(le.legacy_cv().split(Xs, y))
  models = {"lda": LinearDiscriminantAnalysis()}
  res, _ = le.oof_space(space, None, y, models, splits=splits)
  Xs2 = Xs.copy()
  te = splits[0][1]
  Xs2[te] = Xs2[te] * 5 + 100          # only test rows of fold 0 change
  res2, _ = le.oof_space(le.FeatureSpace("S", [Xs2]), None, y, models, splits=splits[:1])
  # fold 0 model is fitted on train rows only: identical training data -> same coefficients -> same transform of the old test rows
  tr0 = splits[0][0]
  from sklearn.pipeline import Pipeline
  from sklearn.preprocessing import StandardScaler
  p1 = Pipeline([("s", StandardScaler()), ("c", LinearDiscriminantAnalysis())]).fit(Xs[tr0], y[tr0])
  p2 = Pipeline([("s", StandardScaler()), ("c", LinearDiscriminantAnalysis())]).fit(Xs2[tr0], y[tr0])
  assert np.allclose(p1.predict_proba(Xs[te]), p2.predict_proba(Xs[te]))
  assert res["lda"]["scores"].shape == (100, 5)


# --- Suite -------------------------------------------------------------------------------

def test_model_suite_parameters():
  """Known answer: 10 named models with the spec P05.4 parameters (l1_ratio style for LogisticRegression)."""
  s = get_sklearn_model_suite()
  assert tuple(s) == MODEL_NAMES and len(s) == 10
  assert isinstance(s["Ridge"], RidgeClassifier) and s["Ridge"].alpha == 1.0 and s["Ridge"].class_weight == "balanced"
  l2, l1, en = s["LogReg L2"], s["LogReg L1"], s["LogReg ElasticNet"]
  assert isinstance(l2, LogisticRegression) and (l2.l1_ratio, l2.solver, l2.C, l2.max_iter) == (0.0, "lbfgs", 1.0, 1000)
  assert (l1.l1_ratio, l1.solver, l1.max_iter, l1.tol, l1.class_weight) == (1.0, "saga", 3000, 1e-3, "balanced")
  assert (en.l1_ratio, en.solver, en.max_iter) == (0.5, "saga", 3000)
  sg, pa = s["SGD log-loss"], s["SGD PA"]
  assert isinstance(sg, SGDClassifier)
  assert (sg.loss, sg.penalty, sg.l1_ratio, sg.alpha, sg.max_iter, sg.class_weight, sg.random_state) == (
    "log_loss", "elasticnet", 0.5, 1e-3, 2000, "balanced", 42)
  assert (pa.loss, pa.penalty, pa.learning_rate, pa.eta0, pa.max_iter) == ("hinge", None, "pa1", 1.0, 2000)
  assert s["LDA svd"].solver == "svd" and s["LDA svd"].shrinkage is None
  assert (s["Shrinkage-LDA lsqr"].solver, s["Shrinkage-LDA lsqr"].shrinkage) == ("lsqr", "auto")
  assert (s["Shrinkage-LDA eigen"].solver, s["Shrinkage-LDA eigen"].shrinkage) == ("eigen", "auto")
  assert isinstance(s["QDA"], QuadraticDiscriminantAnalysis) and s["QDA"].reg_param == 0.5


def test_qda_rank_failure_is_caught_and_other_models_survive():
  """PF-12 known answer: QDA on 210 features with 20 windows per class fails (rank), is reported in `errors`,
  and the other models still return out-of-fold results."""
  rng = np.random.default_rng(0)
  y = np.repeat(np.arange(101, 106), 20)
  X = rng.normal(size=(100, 210)) + (y[:, None] - 103) * 0.3
  models = {k: v for k, v in get_sklearn_model_suite().items() if k in ("QDA", "Ridge")}
  res, errs = le.oof_space(le.FeatureSpace("wide", [X]), None, y, models)
  assert "QDA" in errs and "Ridge" in res and "QDA" not in res


def test_class_scores_softmax_for_models_without_proba():
  """Known answer: Ridge has no predict_proba; scores are the softmax of the decision function (rows sum to 1, same argmax)."""
  rng = np.random.default_rng(0)
  y = np.repeat(np.arange(5), 20)
  X = rng.normal(size=(100, 3)) + y[:, None]
  m = RidgeClassifier().fit(X, y)
  s = le.class_scores(m, X)
  assert np.allclose(s.sum(axis=1), 1.0) and np.array_equal(s.argmax(1), m.decision_function(X).argmax(1))


# --- Legacy CV and smoothing --------------------------------------------------------------

def test_legacy_cv_and_smoothing_definitions():
  """R1/R8 legacy known answer: StratifiedKFold(5, shuffle, 42); the average crosses trial boundaries (row 5 with
  row 4); the mod-5 diagnostic resets at j % 5 == 0."""
  cv = le.legacy_cv()
  assert (cv.n_splits, cv.shuffle, cv.random_state) == (5, True, 42)
  y = np.repeat(np.arange(5), 10)
  exp = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(50), y))
  got = list(cv.split(np.zeros(50), y))
  assert all(np.array_equal(a[1], b[1]) for a, b in zip(exp, got))
  p = np.zeros((10, 5)); p[:, 0] = 0.5; p[4, 0] = 0.9; p[5] = [0.0, 0.5, 0.1, 0.0, 0.0]
  assert np.allclose(smooth_probabilities_legacy(p)[5], (p[4] + p[5]) / 2)
  assert np.allclose(smooth_probabilities_mod5(p)[5], p[5])
  assert np.allclose(smooth_probabilities_mod5(p)[6], (p[5] + p[6]) / 2)
  assert tm.smooth_probabilities_legacy is smooth_probabilities_legacy      # re-export keeps P04 imports


def test_p04_carry_forward_reexports():
  """P04 regression: the moved helpers are still importable from scripts.training.train_models."""
  for name in ("extract_harmonic_features", "harmonic_bin_indices", "check_keep_channels", "KEEP_CHANNELS",
               "HARMONIC_TARGETS_HZ", "load_stimulus_windows", "arrays_exist", "smooth_probabilities_legacy"):
    assert hasattr(tm, name)
  assert tm.build_parser().parse_args(["--seed", "7"]).seed == 7


def test_fbcca_argmax_baseline_known_answer():
  """Known answer: the baseline predicts the code of the largest score; scores are row-normalised."""
  s = np.array([[0.1, 0.9, 0.0, 0.0, 0.0], [0.5, 0.1, 0.1, 0.1, 0.2]])
  pred, sc = le.fbcca_argmax_baseline(s, np.array([102, 101]), (101, 102, 103, 104, 105))
  assert pred.tolist() == [102, 101] and np.allclose(sc.sum(1), 1.0)


# --- Scripts on a synthetic legacy tree ------------------------------------------------------

@pytest.fixture(scope="module")
def tree(tmp_path_factory):
  root = tmp_path_factory.mktemp("p05")
  write_subject(root / "processed", "S03", n_trials=4, seed=11)
  return root


LEG = ["--cv", "legacy", "--smoothing", "mod5"]   # P11: these tests pin the P05-P10 legacy protocol (outputs under legacy_leaky/)


def _flags(root, *extra):
  return ["--subject", "S03", "--processed-dir", str(root / "processed"), "--reports-dir", str(root / "reports"),
          *extra]


def test_benchmark_cross_validation_script(tree):
  """Smoke: 6 spaces x 9 models (no QDA, PF-12) + argmax = 55 rows with the specified columns; mask counts printed."""
  assert bcv.main(_flags(tree, *LEG)) == 0
  df = pd.read_csv(tree / "reports" / "legacy_leaky" / "feature_space_benchmark_S03.csv")
  assert list(df.columns) == bcv.COLUMNS and len(df) == 55
  assert "QDA" not in set(df["Model"])
  assert df.groupby("Feature space")["p"].first().to_dict()["FBCSP + FBCCA (in-fold)"] == 55
  assert set(df["Clean Windows"]) == {100} and set(df["Rejected"]) == {0}
  assert (tree / "reports" / "legacy_leaky" / "feature_space_benchmark_S03.meta.txt").read_text().count("legacy") >= 3


def test_flagship_and_harmonic_scripts(tree):
  fig = tree / "fig"
  assert ecm.main(_flags(tree, *LEG, "--figures-dir", str(fig))) == 0
  assert ecm.main(_flags(tree, *LEG, "--figures-dir", str(fig), "--m", "2")) == 0
  df = pd.read_csv(tree / "reports" / "legacy_leaky" / "flagship_S03.csv")
  assert list(df.columns) == ecm.COLUMNS and df["m"].tolist() == [1, 2]
  assert ecm.main(_flags(tree, *LEG, "--figures-dir", str(fig))) == 0           # rerun replaces the m = 1 row
  assert pd.read_csv(tree / "reports" / "legacy_leaky" / "flagship_S03.csv")["m"].tolist() == [2, 1]
  assert bhf.main(_flags(tree, *LEG, "--figures-dir", str(fig))) == 0
  cm = fig / "legacy_leaky" / "confusion_matrices"
  for n in ("cm_fbcsp_m1_fbcca_cv_S03.png", "cm_fbcsp_m1_fbcca_cv.png", "cm_fbcsp_m2_fbcca_cv.png",
            "cm_harmonic_fbcca_cv_S03.png", "cm_harmonic_fbcca_cv.png"):
    assert (cm / n).is_file(), n
  assert (tree / "reports" / "legacy_leaky" / "classification_report_evaluate_confusion_matrix_S03.txt").is_file()
  for rule, kind in (("noreset", "DIAGNOSTIC"), ("mod5", "REPORTED (legacy i%5")):   # Round 2 labels
    t = (tree / "reports" / "legacy_leaky" / f"classification_report_evaluate_confusion_matrix_S03_smoothed_{rule}.txt").read_text()
    assert t.startswith(kind) and "confusion counts" in t
  t = (tree / "reports" / "legacy_leaky" / "classification_report_benchmark_harmonic_fbcca_S03.txt").read_text()
  assert "FBCCA on PO8, O1, Oz, O2" in t                 # Round 2: visual-cluster FBCCA


def test_sklearn_suite_script_reports_qda_failure(tree, capsys):
  """PF-12: the suite script keeps QDA, prints the rank failure on the wide spaces and still exits 0."""
  assert tsm.main(_flags(tree)) == 0
  out = capsys.readouterr().out
  assert "QDA failed" in out and "Continuous PSD / QDA failed" in out
  df = pd.read_csv(tree / "reports" / "sklearn_suite_S03.csv")
  assert "QDA" in set(df["Model"])                       # QDA ran on FBCCA (p = 5)


def test_scripts_skip_missing_subject(tree, capsys):
  assert bcv.main(["--subject", "S09", "--processed-dir", str(tree / "processed"), "--reports-dir", str(tree / "reports")]) == 1
  assert "[-] Skipping S09" in capsys.readouterr().out


def test_visualize_data_p05_blocks(tree):
  figs = tree / "figs"
  rc = vd.main(["--subject", "S03", "--processed-dir", str(tree / "processed"), "--figures-dir", str(figs)])
  assert rc == 0
  for stem in ("psd_features_by_class", "fbcca_features_by_class", "fbcsp_features_by_class"):
    assert (figs / "exploration" / "S03" / f"{stem}.png").is_file()


# --- Round 2 (decisions.md P05: original extractor limits, i%5 reported smoothing, visual-cluster FBCCA) ---

def test_p05_limits_stay_reachable_and_the_default_is_the_p07_gate():
  """Known answer (R11 round 2, P07): the legacy P05 limits vpp 0.5-120 uV, std 0.1-35 uV stay reachable
  (`thresholds=P05_MASK_THRESHOLDS`, tier 1 off); a window with a 2 uV peak-to-peak channel (std ~0.7) is kept by
  them and rejected by the default P07 gate (5-120 / 1-35 + channel drop at > 50 %)."""
  assert P05_MASK_THRESHOLDS == {"vpp_min": 0.5, "vpp_max": 120.0, "std_min": 0.1, "std_max": 35.0}
  assert GATE_THRESHOLDS == {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}
  X, y = make_windows(n_trials=1, seed=8)
  X = X.copy()
  X[3, 4] = np.sign(np.sin(2 * np.pi * 10 * np.arange(256) / FS))   # vpp 2, std 1 -> scale to std ~0.7
  X[3, 4] *= 0.7
  b = build_feature_blocks(X, y, SCALP, thresholds=P05_MASK_THRESHOLDS, channel_fail_fraction=NO_CHANNEL_DROP)
  assert b["mask"][3] == 1 and b["channels_dropped"] == []
  shared = build_feature_blocks(X, y, SCALP)
  assert shared["mask"][3] == 0


def test_reported_smoothing_is_legacy_i_mod_5():
  """Known answer: `accuracies` smooths with the i%5 reset. Scores: row 5 (true class 1) is weakly class 1, row 4
  strongly class 0; with the reset row 5 stays class 1 (2.0 s acc 10/10), the no-reset average flips it (9/10)."""
  y = np.array([0] * 5 + [1] * 5)
  s = np.zeros((10, 2))
  s[:5, 0] = 1.0
  s[5] = [0.4, 0.6]
  s[6:, 1] = 1.0
  a1, a2 = le.accuracies(y, y.copy(), s)
  assert a1 == 1.0 and a2 == 1.0
  assert np.mean(np.argmax(smooth_probabilities_legacy(s), axis=1) == y) == 0.9   # the diagnostic rule differs
  assert le.smooth_reported is smooth_probabilities_mod5 and "i%5" in le.SMOOTH_LABEL


def test_fbcca_channels_by_name_and_same_mask():
  """Known answer: `fbcca_channels=VISUAL_CLUSTER` gives FBCCA = extractor on X[:, PO8, O1, Oz, O2] picked by name
  (also under a reordered name list); the mask is the all-channel one, so PSD/harmonic rows are unchanged."""
  X, y = make_windows(n_trials=1, seed=9)
  full = build_feature_blocks(X, y, SCALP)
  vis = build_feature_blocks(X, y, SCALP, fbcca_channels=VISUAL_CLUSTER)
  idx = [list(SCALP).index(c) for c in VISUAL_CLUSTER]
  ref, _, _, _ = fb.extract_fbcca_features(X[:, idx], y, list(VISUAL_CLUSTER),
                                           precomputed=dict(full["channel_report"], channels_kept=list(VISUAL_CLUSTER)))
  assert np.allclose(vis["fbcca"], ref) and not np.allclose(vis["fbcca"], full["fbcca"])
  assert np.array_equal(vis["mask"], full["mask"]) and np.allclose(vis["psd"], full["psd"])
  assert vis["fbcca_channels"] == list(VISUAL_CLUSTER) and full["fbcca_channels"] == list(SCALP)
  perm = np.arange(len(SCALP))[::-1]
  rev = build_feature_blocks(X[:, perm], y, [SCALP[i] for i in perm], fbcca_channels=VISUAL_CLUSTER)
  assert np.allclose(rev["fbcca"], vis["fbcca"])
