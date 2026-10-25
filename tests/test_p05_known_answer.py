"""P05 independent known-answer tests (synthetic-tester).

Every expected value comes from closed forms (periodogram scaling, CCA of a pure tone, CSP of a
planted spatial vector, Chebyshev ripple) or from the roadmap spec, not from the builder's code.
Mutants (historical or plausible bugs) are defined inside this file; each `*_mutant_*` test proves
that the corresponding check fails on the buggy variant. Legacy Era A: fs 250 on 256-sample windows.
Seeded; no data/ access.
"""

import warnings

import numpy as np
import pytest
from scipy.linalg import eigh
from scipy.signal import butter, cheby1, freqz
from sklearn.base import clone
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.features.ssvep import fbcca_extraction as fb
from src.features.ssvep import fbcsp_extraction as csp
from src.features.ssvep.harmonic_psd import VISUAL_CLUSTER, visual_cluster_harmonic_psd
from src.features.ssvep.psd_extraction import continuous_psd_freqs, extract_continuous_psd_features
from src.models.classical import feature_spaces as fsp
from src.models.classical import legacy_eval as le
from src.models.classical.sklearn_models import get_sklearn_model_suite
from src.preprocessing.dataset.smoothing import smooth_probabilities_legacy, smooth_probabilities_mod5
from tests.p05_synth import SCALP, keep_all, make_windows

FS = 250.0
T = 256
t = np.arange(T) / FS


# --- reference signals -------------------------------------------------------------------------

def test_reference_signals_closed_form_other_frequency():
  """Known answer (spec P05.1): for f = 8.5714, fs 250, T 256, H 3 the rows are
  [sin(2 pi f t), cos(2 pi f t), sin(4 pi f t), cos(4 pi f t), sin(6 pi f t), cos(6 pi f t)], t = n/250.
  Tolerance 1e-12. Also H = 1 gives (2, T) and the first row is 0 at n = 0, the second 1."""
  f = 8.5714
  r = fb.generate_reference_signals(f, FS, T, 3)
  exp = np.stack([g(2 * np.pi * h * f * t) for h in (1, 2, 3) for g in (np.sin, np.cos)])
  assert r.shape == (6, T) and np.allclose(r, exp, atol=1e-12)
  r1 = fb.generate_reference_signals(f, FS, T, 1)
  assert r1.shape == (2, T) and r1[0, 0] == 0.0 and r1[1, 0] == 1.0


def test_target_freqs_constant():
  """Known answer (roadmap P05.1): TARGET_FREQS = [24, 20, 15, 10.9091, 8.5714] exactly."""
  assert list(fb.TARGET_FREQS) == [24.0, 20.0, 15.0, 10.9091, 8.5714]


# --- Chebyshev bands ---------------------------------------------------------------------------

def _ripple_summary(b, a, low, high=90.0):
  f = np.linspace(low, high, 4000)
  _, h = freqz(b, a, worN=f, fs=FS)
  g = np.abs(h)
  n_max = int(((g[1:-1] > g[:-2]) & (g[1:-1] > g[2:])).sum())
  return g, n_max


def _check_chebyshev(bands):
  """Order 4, ripple 3 dB, edges [low, 90]: the gain at both band edges is the ripple level
  10^(-3/20) = 0.70795 (+-5e-4), a band-pass of Chebyshev-I order 4 has 4 ripple maxima in the band
  (order 3 has 3, 1 dB ripple has a 0.891 edge), gain ~0 at 2 Hz."""
  assert len(bands) == 3
  for (b, a), low in zip(bands, (6.0, 14.0, 22.0)):
    assert len(a) - 1 == 8                                    # order 4 band-pass -> degree 8
    g, n_max = _ripple_summary(b, a, low)
    assert abs(g[0] - 10 ** (-3 / 20)) < 5e-4 and abs(g[-1] - 10 ** (-3 / 20)) < 5e-4
    assert n_max == 4
    assert abs(freqz(b, a, worN=[2.0], fs=FS)[1][0]) < 0.01


def test_chebyshev_design_by_ripple_properties():
  """Known answer: see `_check_chebyshev` (analytic Chebyshev-I band-pass ripple level and count)."""
  _check_chebyshev(fb.get_chebyshev_subbands(FS))


@pytest.mark.parametrize("make", [
  lambda low: butter(4, [low, 90], btype="band", fs=FS),               # Butterworth (P04 style)
  lambda low: cheby1(3, 3, [low, 90], btype="band", fs=FS),            # wrong order
  lambda low: cheby1(4, 1, [low, 90], btype="band", fs=FS),            # wrong ripple
  lambda low: cheby1(4, 3, [low, 100], btype="band", fs=FS),           # wrong upper edge
])
def test_chebyshev_mutants_fail(make):
  """Mutants (Butterworth, order 3, 1 dB, 100 Hz edge) must fail the Chebyshev design check."""
  with pytest.raises(AssertionError):
    _check_chebyshev([make(low) for low in (6.0, 14.0, 22.0)])


# --- FBCCA ------------------------------------------------------------------------------------

def test_cca_of_pure_tone_is_one_at_fs250_and_not_at_fs256():
  """Known answer: one channel sin(2 pi 24 t + 0.3), t = n/250, is in the span of the 24 Hz references
  generated at fs 250 (r = 1, tol 1e-9); references generated at fs 256 (PF-04 slip) give r < 0.8
  (measured 0.54); a non-harmonic target (15 Hz) gives r < 0.5."""
  x = np.sin(2 * np.pi * 24 * t + 0.3)[:, None]
  assert abs(fb.canonical_correlation(x, fb.generate_reference_signals(24.0, 250.0, T).T) - 1) < 1e-9
  assert fb.canonical_correlation(x, fb.generate_reference_signals(24.0, 256.0, T).T) < 0.8
  assert fb.canonical_correlation(x, fb.generate_reference_signals(15.0, 250.0, T).T) < 0.5


def test_fbcca_argmax_recovers_planted_target_other_seed():
  """Known answer: 7-channel windows (random mixing of the tone over channels, noise sd 2, distinct
  random phases), 4 windows per target: argmax of the (n, 5) score matrix is the planted target index
  for every window; scores are within [0, sum of weights = 2.3837]."""
  rng = np.random.default_rng(2024)
  X, y = [], []
  for k, f in enumerate(fb.TARGET_FREQS):
    for _ in range(4):
      mix = rng.uniform(0.5, 1.5, 7) * rng.choice([-1, 1], 7)
      X.append(8 * mix[:, None] * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))[None] + rng.normal(0, 2, (7, T)))
      y.append(k)
  X, y = np.stack(X), np.array(y)
  S, yc, mask, rep = fb.extract_fbcca_features(X, y)
  assert S.shape == (20, 5) and mask.sum() == 20 and rep["channels_dropped"] == []
  assert np.array_equal(S.argmax(1), y)
  assert S.min() >= 0 and S.max() <= 1.25 + 0.6704 + 0.5033 + 1e-3


def test_fbcca_at_wrong_fs_loses_the_24hz_target_margin():
  """PF-04 mutant: scoring a 250 Hz-sampled 24 Hz tone with fs = 256 references lowers the 24 Hz score
  by >= 25 % relative to fs 250 (measured ratio ~0.6)."""
  rng = np.random.default_rng(5)
  x = 8 * np.sin(2 * np.pi * 24 * t + 1.0)[None] * np.ones((7, 1)) + rng.normal(0, 1, (7, T))
  s250, _, _, _ = fb.extract_fbcca_features(x[None], np.array([0]), fs=250.0)
  s256, _, _, _ = fb.extract_fbcca_features(x[None], np.array([0]), fs=256.0)
  assert s256[0, 0] < 0.75 * s250[0, 0]


def test_fbcca_failure_gives_zero_correlation_not_exception():
  """Known answer: a constant (and an all-zero) window has r = 0 exactly in every band and target;
  extract_fbcca_features does not raise when the mask is forced to keep them, and the scores are finite."""
  const = np.full((7, T), 3.0)
  assert fb.canonical_correlation(const.T, fb.generate_reference_signals(10.0, FS, T).T) == 0.0
  X = np.stack([const, np.zeros((7, T))])
  S, _, m, _ = fb.extract_fbcca_features(X, np.array([101, 102]), precomputed=keep_all(2))
  assert S.shape == (2, 5) and np.all(np.isfinite(S)) and m.tolist() == [1, 1]
  assert np.all(S[1] == 0.0)                                                # zero window -> r = 0 -> score 0


# --- CSP --------------------------------------------------------------------------------------

def _two_class_csp_data(seed=0, C=4, n=60, amp=4.0):
  """Class A: variance 1 + amp^2 = 17 along u = e0, class B along v = e1 (orthonormal), unit noise elsewhere."""
  rng = np.random.default_rng(seed)
  X, y = [], []
  for cls, ax in ((101, 0), (102, 1)):
    for _ in range(n):
      w = rng.normal(size=(C, T))
      w[ax] += amp * rng.normal(size=T)
      X.append(w)
      y.append(cls)
  return np.stack(X), np.array(y)


def test_csp_analytic_eigenvalues_and_vector():
  """Known answer: with S_A = I + 15 u u^T, S_B = I + 15 v v^T (u perp v, trace-normalised, equal traces)
  the CSP eigenvalues of class A are 16/17 = 0.941 (filter ~ u) and 1/17 = 0.059 (filter ~ v);
  tolerance 0.03 on the eigenvalues (sampling), |cos| > 0.95 with u; eigenvalues within (0, 1)."""
  X, y = _two_class_csp_data()
  c = csp.MulticlassCSP(1).fit(X, y)
  assert c.filters_.shape == (2, 4, 2) and c.eigenvalues_.shape == (2, 2)
  assert abs(c.eigenvalues_[0, 0] - 16 / 17) < 0.03 and abs(c.eigenvalues_[0, 1] - 1 / 17) < 0.03
  assert abs(c.eigenvalues_[1, 0] - 16 / 17) < 0.03
  fa = c.filters_[0][:, 0]
  fv = c.filters_[0][:, 1]
  assert abs(fa[0]) / np.linalg.norm(fa) > 0.95 and abs(fv[1]) / np.linalg.norm(fv) > 0.95
  assert np.all((c.eigenvalues_ > 0) & (c.eigenvalues_ < 1))


def test_csp_filters_solve_the_generalized_eigenproblem_independently():
  """Known answer: recompute S_t, S_r (mean of W W^T / tr(W W^T)) from scratch on random data, solve
  eigh(S_t, S_t + S_r + 1e-6 I); filters_ columns equal the m largest (descending) and m smallest
  eigenvectors up to sign (|cos| = 1, tol 1e-8), eigenvalues equal (tol 1e-9). Random SPD data, 3 classes, m = 2."""
  rng = np.random.default_rng(3)
  C = 6
  X = np.stack([(rng.normal(size=(C, C)) @ rng.normal(size=(C, 128))) for _ in range(45)])
  y = np.repeat([1, 2, 3], 15)
  c = csp.MulticlassCSP(2).fit(X, y)

  def cov(sel):
    covs = [w @ w.T / np.trace(w @ w.T) for w in X[sel]]
    return np.mean(covs, axis=0)

  for ci, cls in enumerate((1, 2, 3)):
    st, sr = cov(y == cls), cov(y != cls)
    vals, vecs = eigh(st, st + sr + 1e-6 * np.eye(C))
    pick = [C - 1, C - 2, 0, 1]
    assert np.allclose(c.eigenvalues_[ci], vals[pick], atol=1e-9)
    for j, p in enumerate(pick):
      a, b = c.filters_[ci][:, j], vecs[:, p]
      assert abs(a @ b) / (np.linalg.norm(a) * np.linalg.norm(b)) > 1 - 1e-8


def test_csp_features_log10_ratio_and_variance_floor():
  """Known answer (roadmap): feature = log10(var_j / sum_j var_j) over a class's 2m projections.
  (a) All-zero window -> both variances floored to 1e-12 -> each feature log10(1/2) = -0.30103 (tol 1e-9).
  (b) Filters set by hand so that component 1 projects to zero: features are
  log10(v/(v+1e-12)) and log10(1e-12/(v+1e-12)) = -12 + log10(1/(1+1e-12/v)) (tol 1e-9)."""
  X, y = _two_class_csp_data(seed=1)
  c = csp.MulticlassCSP(1).fit(X, y)
  F0 = c.transform(np.zeros((1, 4, T)))
  assert np.allclose(F0, np.log10(0.5), atol=1e-9)
  c.filters_ = np.zeros_like(c.filters_)
  c.filters_[:, 0, 0] = 1.0                                                 # comp 0 = channel 0, comp 1 = zero vector
  w = X[3]
  v = np.var(w[0])
  F = c.transform(w[None])
  exp = [np.log10(v / (v + 1e-12)), np.log10(1e-12 / (v + 1e-12))]
  assert np.allclose(F[0, :2], exp, atol=1e-9) and np.allclose(F[0, 2:], exp, atol=1e-9)


def test_csp_unnormalised_covariance_mutant_is_detected():
  """PF-adjacent mutant: CSP without trace normalisation lets one huge window dominate. Known answer: scaling
  channel 3 of one training window x1000 changes the filters' alignment with the planted vector by < 0.05 (|cos| stays > 0.95)
  for the real code; the unnormalised mutant (reimplemented here) drops below 0.95."""
  X, y = _two_class_csp_data(seed=2)
  X2 = X.copy()
  X2[0, 3] *= 1000.0                                                       # one class-A window dominated by channel 3
  fa = csp.MulticlassCSP(1).fit(X2, y).filters_[0][:, 0]
  assert abs(fa[0]) / np.linalg.norm(fa) > 0.95

  def raw_filter(Xm, ym):
    st = np.mean([w @ w.T for w in Xm[ym == 101]], axis=0)
    sr = np.mean([w @ w.T for w in Xm[ym == 102]], axis=0)
    vals, vecs = eigh(st, st + sr + 1e-6 * np.eye(4))
    return vecs[:, -1]

  fm = raw_filter(X2, y)
  assert abs(fm[0]) / np.linalg.norm(fm) < 0.95


# --- 50-feature layout (R6) -------------------------------------------------------------------

BANDS = [(7, 12), (13, 17), (18, 26), (27, 36), (38, 52)]


def _layout_windows(seed=8, n=14, C=7):
  """Class k: white noise with class-specific channel gains plus a class-specific tone (so every band and
  every class has its own covariance structure)."""
  rng = np.random.default_rng(seed)
  gains = rng.uniform(0.5, 3.0, size=(5, C))
  X, y = [], []
  for k in range(5):
    for _ in range(n):
      tone = np.sin(2 * np.pi * (9.5 + 8.0 * k) * t + rng.uniform(0, 6.28))
      X.append(gains[k][:, None] * rng.normal(size=(C, T)) + 2.0 * rng.normal(size=(C, 1)) * tone[None])
      y.append(101 + k)
  return np.stack(X), np.array(y)


def _oracle_fbcsp(X, y, m=1):
  """Independent FBCSP oracle: scipy Butterworth(4)+filtfilt per band; per class one-vs-rest
  eigh(S_t, S_t + S_r + 1e-6 I); m largest (descending) then m smallest; feature log10(var_j / sum_j var_j);
  column order ((band * 5) + class) * 2m + j."""
  from scipy.signal import filtfilt
  cols = []
  for lo, hi in BANDS:
    bb, aa = butter(4, [lo, min(hi, FS / 2 - 1)], btype="band", fs=FS)
    xb = filtfilt(bb, aa, X, axis=-1)
    covs = np.array([w @ w.T / np.trace(w @ w.T) for w in xb])
    for cls in np.unique(y):
      st, sr = covs[y == cls].mean(0), covs[y != cls].mean(0)
      _, vecs = eigh(st, st + sr + 1e-6 * np.eye(X.shape[1]))
      W = np.hstack([vecs[:, ::-1][:, :m], vecs[:, :m]])
      v = np.maximum(np.einsum("cj,nct->njt", W, xb).var(-1), 1e-12)
      cols.append(np.log10(v / v.sum(1, keepdims=True)))
  return np.hstack(cols)


def _layout_check(transform_cls):
  """(n, 50) matrix equals the independent oracle column by column (tol 1e-6): band-major, class, component."""
  X, y = _layout_windows()
  sw = csp.filter_subbands(X, FS)
  assert sw.shape == (len(X), 5, 7, T)
  F = transform_cls(1).fit(sw, y).transform(sw)
  assert F.shape == (len(X), 50)
  assert np.allclose(F, _oracle_fbcsp(X, y), atol=1e-6)


def test_fbcsp_layout_band_major_class_known_answer():
  """R6 known answer: layout is band-major, then class, then component; (n, 50) for m = 1; source: independent oracle."""
  _layout_check(csp.FBCSPTransformer)


class _ClassMajorFBCSP(csp.FBCSPTransformer):
  """Mutant: columns reordered class-major, band-minor (the swapped-order bug)."""

  def transform(self, sw):
    F = super().transform(sw)
    return F.reshape(len(F), 5, 5, 2).transpose(0, 2, 1, 3).reshape(len(F), -1)


class _ReversedComponentFBCSP(csp.FBCSPTransformer):
  """Mutant: component order within a class flipped (smallest-eigenvalue filter first)."""

  def transform(self, sw):
    F = super().transform(sw)
    return F.reshape(len(F), 5, 5, 2)[..., ::-1].reshape(len(F), -1)


@pytest.mark.parametrize("mutant", [_ClassMajorFBCSP, _ReversedComponentFBCSP])
def test_fbcsp_layout_mutants_fail(mutant):
  """Mutants with swapped band/class order or flipped components must fail the layout check."""
  with pytest.raises(AssertionError):
    _layout_check(mutant)


# --- continuous PSD ----------------------------------------------------------------------------

def test_continuous_psd_closed_form_amplitude_and_channel_major_position():
  """Known answer: a noise-free on-bin tone A sin(2 pi k fs/N t) (k = 10 -> 9.765625 Hz) in channel 2 only
  has a boxcar periodogram density A^2 N / (2 fs) = A^2 * 0.512 in bin k and ~0 elsewhere (tol 1e-9 rel.).
  Feature index = channel * 30 + (k - 6) = 2*30 + 4 = 64; shape (1, 210). Bin list 6..35 * 250/256 Hz.
  The mutant fs = 256 labels bins differently (spacing 1 Hz, 31 bins in 5..35)."""
  A = 6.0
  x = np.zeros((1, 7, T))
  tt = np.arange(T) / FS
  x[0, 2] = A * np.sin(2 * np.pi * 10 * FS / T * tt)
  P, _, m, _ = extract_continuous_psd_features(x, np.array([101]), precomputed=keep_all(1))
  assert P.shape == (1, 210)
  assert np.isclose(P[0, 64], A ** 2 * T / (2 * FS), rtol=1e-9)
  other = np.delete(P[0], 64)
  assert other.max() < 1e-9 * P[0, 64]
  f = continuous_psd_freqs(T, FS)
  assert np.allclose(f, np.arange(6, 36) * FS / T) and f[0] == pytest.approx(5.859375) and f[-1] == pytest.approx(34.1796875)
  f256 = continuous_psd_freqs(T, 256.0)
  assert len(f256) == 31 and len(f256) != len(f)


# --- visual cluster by name ------------------------------------------------------------------------

AMP = {"PO3": 3.0, "POz": 4.0, "PO4": 5.0, "PO8": 6.0, "O1": 7.0, "Oz": 8.0, "O2": 9.0}


def _named_windows(names, seed=0):
  """Each channel is a noise-free 15 Hz on-bin tone (k = 15 -> 14.648 Hz) with amplitude AMP[name]."""
  rng = np.random.default_rng(seed)
  tt = np.arange(T) / FS
  X = np.stack([[AMP[n] * np.sin(2 * np.pi * 15 * FS / T * tt + rng.uniform(0, 6.28)) for n in names] for _ in range(10)])
  return X, np.repeat(np.arange(101, 106), 2)


def test_harmonic_psd_picks_po8_o1_oz_o2_by_name_with_closed_form_power():
  """PF-06 known answer: whatever the channel order, harmonic PSD column 8*r + 2 (r-th cluster channel,
  15 Hz bin = third target) equals A^2 * 0.512 for A = AMP[PO8, O1, Oz, O2] = 6, 7, 8, 9 (tol 1e-6 rel.);
  shape (n, 32). The P04 set (POz, O1, Oz, O2) would give 4, 7, 8, 9: that mutant must fail."""
  want = np.array([AMP[n] ** 2 * T / (2 * FS) for n in VISUAL_CLUSTER])
  for names in (SCALP, ["O2", "PO3", "Oz", "POz", "PO8", "O1", "PO4"], list(reversed(SCALP))):
    X, y = _named_windows(names)
    b = fsp.build_feature_blocks(X, y, names)
    H = b["harmonic"]
    assert H.shape == (10, 32)
    assert np.allclose(H[:, 2::8], want[None], rtol=1e-6)
  p04 = np.array([AMP[n] ** 2 * T / (2 * FS) for n in ("POz", "O1", "Oz", "O2")])
  assert not np.allclose(p04, want)
  assert VISUAL_CLUSTER == ("PO8", "O1", "Oz", "O2")
  freqs = continuous_psd_freqs(T, FS)
  P, _, _, _ = extract_continuous_psd_features(X, y, precomputed=keep_all(10))
  mut = visual_cluster_harmonic_psd(P, freqs, list(reversed(SCALP)), cluster=("POz", "O1", "Oz", "O2"))
  assert not np.allclose(mut[:, 2::8], want[None], rtol=1e-6)


# --- in-fold CSP (PF-11) ------------------------------------------------------------------------------

def _noise_problem(seed=0, n=100):
  rng = np.random.default_rng(seed)
  X = rng.normal(0, 8, size=(n, 7, T))
  y = np.repeat(np.arange(101, 106), n // 5)
  return X, y


def _cv_accuracy_with(fold_fn, sub, y, model):
  """Out-of-fold accuracy of Pipeline(StandardScaler, model) with fold matrices from `fold_fn`."""
  pred = np.zeros(len(y), dtype=int)
  for tr, te in le.legacy_cv().split(np.zeros(len(y)), y):
    Xtr, Xte = fold_fn(sub, y, tr, te)
    with warnings.catch_warnings():
      warnings.simplefilter("ignore")
      pred[te] = Pipeline([("s", StandardScaler()), ("c", clone(model))]).fit(Xtr, y[tr]).predict(Xte)
  return float(np.mean(pred == y))


def test_infold_csp_gives_chance_on_label_free_noise_and_full_data_csp_does_not():
  """PF-11 known answer: windows are pure noise, labels arbitrary: an honest estimate is chance (0.20).
  In-fold CSP + Shrinkage-LDA stays <= 0.35; the same CV with CSP fitted on all windows (historical leak,
  mutant defined here) exceeds 0.45 and exceeds the honest value by >= 0.15. Seed fixed."""
  X, y = _noise_problem()
  sub = csp.filter_subbands(X, FS)
  model = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
  space = le.FeatureSpace("FBCSP", [], fbcsp_m=1)
  honest = _cv_accuracy_with(lambda s, yy, tr, te: le.fold_matrices(space, s, yy, tr, te), sub, y, model)
  Fall = csp.FBCSPTransformer(1).fit_transform(sub, y)                   # leak: filters see test labels
  leaky = _cv_accuracy_with(lambda s, yy, tr, te: (Fall[tr], Fall[te]), sub, y, model)
  assert honest <= 0.35, honest
  assert leaky > 0.45 and leaky - honest >= 0.15, (honest, leaky)


def test_fold_matrices_fit_csp_on_training_rows_only(monkeypatch):
  """PF-11 known answer: the FBCSP transformer used by `fold_matrices` is fitted on exactly the training
  indices (row count and labels), never on test rows. A spy records every fit; a leaky variant fits on all."""
  X, y = _noise_problem(seed=1, n=50)
  sub = csp.filter_subbands(X, FS)
  fits = []
  orig = csp.FBCSPTransformer.fit

  def spy(self, sw, yy):
    fits.append((len(sw), np.asarray(yy).copy()))
    return orig(self, sw, yy)

  monkeypatch.setattr(le.FBCSPTransformer, "fit", spy)
  space = le.FeatureSpace("FBCSP", [], fbcsp_m=1)
  for tr, te in le.legacy_cv().split(np.zeros(len(y)), y):
    le.fold_matrices(space, sub, y, tr, te)
    assert fits[-1][0] == len(tr) < len(y) and np.array_equal(fits[-1][1], y[tr])
  assert len(fits) == 5


# --- single mask (PF-10) -------------------------------------------------------------------------------

def _square_wave_window(rng, amp=30.0):
  """Window with ~std amp (square wave, vpp 2*amp) on channel 2: passes std_max 35, fails std_max 25."""
  w = rng.normal(0, 3, (7, T))
  w[2] = amp * np.sign(np.sin(2 * np.pi * 10 * t))
  return w


def test_single_mask_removes_window_from_every_block_under_stricter_threshold():
  """PF-10 known answer: one window with channel std ~30 passes the shared gate (std_max 35: kept in every
  block, n rows) and fails a stricter gate (std_max 25): then it is absent from psd, harmonic, fbcca, subbands
  and y alike (n - 1 rows, mask 0 at that index). A mutant that gates the FBCCA block separately with the
  stricter limit while the other blocks use the shared one yields blocks of different length."""
  X, y = make_windows(n_trials=2, seed=12)
  X = X.copy()
  bad = 23
  X[bad] = _square_wave_window(np.random.default_rng(1))
  keys = ("y", "psd", "harmonic", "fbcca", "subbands")
  loose = fsp.build_feature_blocks(X, y, SCALP)
  assert loose["mask"][bad] == 1 and all(len(loose[k]) == len(X) for k in keys)
  strict_th = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 25.0}
  strict = fsp.build_feature_blocks(X, y, SCALP, thresholds=strict_th)
  assert strict["mask"][bad] == 0 and strict["mask"].sum() == len(X) - 1
  assert all(len(strict[k]) == len(X) - 1 for k in keys)
  keep = np.delete(np.arange(len(X)), bad)
  assert np.array_equal(strict["y"], y[keep])
  ref = extract_continuous_psd_features(X[keep], y[keep], precomputed=keep_all(len(keep)))[0]
  assert np.allclose(strict["psd"], ref)
  # mutant: PSD on the shared mask, FBCCA gated on its own with the strict limit -> misaligned
  psd_loose = loose["psd"]
  fb_strict, _, _, _ = fb.extract_fbcca_features(X, y, thresholds=strict_th, channel_fail_fraction=1.0)
  assert len(psd_loose) != len(fb_strict)


def test_blocks_receive_the_same_mask_object(monkeypatch):
  """PF-10 known answer: build_feature_blocks hands one identical non-None decision (`precomputed`, P07) to the PSD
  and the FBCCA extractor (spy); its `valid_mask` is the returned mask."""
  seen = {}
  X, y = make_windows(n_trials=1, seed=3)

  def wrap(name, fn):
    def inner(*a, **k):
      seen[name] = k.get("precomputed")
      return fn(*a, **k)
    return inner

  monkeypatch.setattr(fsp, "extract_continuous_psd_features", wrap("psd", fsp.extract_continuous_psd_features))
  monkeypatch.setattr(fsp, "extract_fbcca_features", wrap("fbcca", fsp.extract_fbcca_features))
  b = fsp.build_feature_blocks(X, y, SCALP)
  assert seen["psd"] is not None and seen["fbcca"] is not None
  assert np.array_equal(seen["psd"]["valid_mask"], seen["fbcca"]["valid_mask"])
  assert np.array_equal(seen["psd"]["valid_mask"], b["mask"])


# --- suite ----------------------------------------------------------------------------------------------

def test_suite_parameter_table_via_get_params():
  """Known answer (roadmap P05.4): 10 models, each with exactly the listed parameters (get_params subset).
  LogisticRegression is configured through l1_ratio (L2 0, L1 1, EN 0.5), no deprecated `penalty` set;
  constructing the suite raises no warning; QDA reg_param 0.5; seed argument reaches the SGD models."""
  with warnings.catch_warnings():
    warnings.simplefilter("error")
    s = get_sklearn_model_suite()
  table = {
    "Ridge": (RidgeClassifier, dict(alpha=1.0, class_weight="balanced")),
    "LogReg L2": (LogisticRegression, dict(l1_ratio=0.0, solver="lbfgs", C=1.0, max_iter=1000, class_weight="balanced")),
    "LogReg L1": (LogisticRegression, dict(l1_ratio=1.0, solver="saga", tol=1e-3, max_iter=3000, class_weight="balanced")),
    "LogReg ElasticNet": (LogisticRegression, dict(l1_ratio=0.5, solver="saga", max_iter=3000)),
    "SGD log-loss": (SGDClassifier, dict(loss="log_loss", penalty="elasticnet", l1_ratio=0.5, alpha=1e-3,
                                          max_iter=2000, class_weight="balanced", random_state=42)),
    "SGD PA": (SGDClassifier, dict(loss="hinge", penalty=None, learning_rate="pa1", eta0=1.0, max_iter=2000)),
    "LDA svd": (LinearDiscriminantAnalysis, dict(solver="svd", shrinkage=None)),
    "Shrinkage-LDA lsqr": (LinearDiscriminantAnalysis, dict(solver="lsqr", shrinkage="auto")),
    "Shrinkage-LDA eigen": (LinearDiscriminantAnalysis, dict(solver="eigen", shrinkage="auto")),
    "QDA": (QuadraticDiscriminantAnalysis, dict(reg_param=0.5)),
  }
  assert list(s) == list(table) and len(s) == 10
  for name, (cls, params) in table.items():
    assert type(s[name]) is cls, name
    got = s[name].get_params()
    for k, v in params.items():
      assert got[k] == v, (name, k, got[k], v)
  assert get_sklearn_model_suite(seed=7)["SGD log-loss"].random_state == 7


def test_benchmark_models_exclude_qda(monkeypatch):
  """PF-12 known answer: run_benchmark passes the suite without QDA (9 models) to every feature space and
  the argmax row is the only extra row; QDA is not in the output rows."""
  from scripts.benchmarks.feature_based import benchmark_cross_validation as bcv
  X, y = make_windows(n_trials=2, seed=2)
  blocks = fsp.build_feature_blocks(X, y, SCALP)
  blocks.update(n_clean=len(blocks["y"]), n_rejected=0)
  seen = []

  def fake_oof(space, sub, yy, models, seed=42, splits=None):
    seen.append(tuple(models))
    return {}, {}

  monkeypatch.setattr(bcv, "oof_space", fake_oof)
  rows, fails = bcv.run_benchmark(blocks, "S99", verbose=False)
  assert len(seen) == 6 and all(len(m) == 9 and "QDA" not in m for m in seen)
  assert [r["Model"] for r in rows] == ["argmax"]


# --- legacy CV and smoothing -------------------------------------------------------------------------------

def test_legacy_smoothing_hand_example_crosses_trials():
  """R8/PF-02 legacy known answer: p = rows [0..9]; out[0] = p0, out[j] = (p[j-1] + p[j]) / 2 for all j
  including j = 5 (trial boundary, no reset). The mod-5 diagnostic leaves rows 0 and 5 unchanged."""
  p = np.arange(10, dtype=float)[:, None] * np.ones((1, 5))
  out = smooth_probabilities_legacy(p)
  assert np.allclose(out[:, 0], [0] + [(j - 1 + j) / 2 for j in range(1, 10)])
  d = smooth_probabilities_mod5(p)
  assert d[0, 0] == 0 and d[5, 0] == 5 and d[6, 0] == 5.5
  # mutant: a reset at the boundary changes row 5 -> would not satisfy the legacy definition
  assert out[5, 0] == 4.5 != d[5, 0]


def test_legacy_cv_splits_equal_independent_construction():
  """R1/PF-01 known answer: fold test indices are those of an independently constructed
  StratifiedKFold(5, shuffle=True, random_state=42); windows of a single trial (5 consecutive rows)
  are split across train and test in at least one fold (the leak the legacy protocol has)."""
  from sklearn.model_selection import StratifiedKFold
  y = np.repeat(np.arange(101, 106), 40)
  a = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y))
  b = list(le.legacy_cv().split(np.zeros(len(y)), y))
  assert all(np.array_equal(p[0], q[0]) and np.array_equal(p[1], q[1]) for p, q in zip(a, b))
  te = set(b[0][1].tolist())
  assert any(0 < len(te & set(range(s, s + 5))) < 5 for s in range(0, len(y), 5))


def test_fold_matrices_spy_detects_a_leaky_fold_function(monkeypatch):
  """PF-11 mutant proof: the spy assertion of the in-fold test fails on a fold function that fits the
  transformer on all rows (the historical full-data CSP)."""
  X, y = _noise_problem(seed=1, n=50)
  sub = csp.filter_subbands(X, FS)
  fits = []
  orig = csp.FBCSPTransformer.fit

  def spy(self, sw, yy):
    fits.append(len(sw))
    return orig(self, sw, yy)

  monkeypatch.setattr(csp.FBCSPTransformer, "fit", spy)
  tr, te = next(le.legacy_cv().split(np.zeros(len(y)), y))
  tf = csp.FBCSPTransformer(1).fit(sub, y)                    # leaky: all rows
  tf.transform(sub[tr]), tf.transform(sub[te])
  assert fits == [len(y)] and fits[-1] != len(tr)


# --- scripts as modules ---------------------------------------------------------------------------------

def test_flagship_script_runs_as_module_on_synthetic_tree(tmp_path):
  """Smoke: `python -m scripts.evaluation.evaluate_confusion_matrix` on a seeded synthetic legacy tree exits 0,
  prints the legacy labels and writes flagship_S03.csv with 100 clean windows, 0 rejected, m = 1."""
  import subprocess
  import sys
  from pathlib import Path

  import pandas as pd

  from tests.p05_synth import write_subject
  root = Path(__file__).resolve().parents[1]
  write_subject(tmp_path / "processed", "S03", n_trials=4, seed=21)
  r = subprocess.run([sys.executable, "-m", "scripts.evaluation.evaluate_confusion_matrix", "--subject", "S03",
                      "--processed-dir", str(tmp_path / "processed"), "--reports-dir", str(tmp_path / "rep"),
                      "--figures-dir", str(tmp_path / "fig")], cwd=root, capture_output=True, text=True, timeout=240)
  assert r.returncode == 0, r.stderr[-800:]
  assert "legacy" in r.stdout and "fs" in r.stdout
  df = pd.read_csv(tmp_path / "rep" / "flagship_S03.csv")
  assert df.loc[0, "Clean Windows"] == 100 and df.loc[0, "Rejected"] == 0 and df.loc[0, "m"] == 1
  assert 0 <= df.loc[0, "1.0s Acc (%)"] <= 100
