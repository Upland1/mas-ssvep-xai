"""P20.2: vectorized FBCCA, ITR, trial-grouped CV on overlapping windows, in-fold LDA, method-split merge, C-b."""

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks import benchmark_window_sweep as W
from src.features.ssvep import fbcca_extraction as F
from src.preprocessing.dataset.cv_utils import shared_trials

FS = 256.0
TH = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}


def loop_scores(bands, fs, freqs=F.TARGET_FREQS, n_harm=3):
  """Independent reference: per window/band/target, first canonical correlation from the covariance eigenproblem."""
  w = F.fbcca_weights(bands.shape[1])
  out = np.zeros((len(bands), len(freqs)))
  for i, win in enumerate(bands):
    for k, f in enumerate(freqs):
      y = F.generate_reference_signals(f, fs, win.shape[-1], n_harm).T
      y = y - y.mean(0)
      for b in range(win.shape[0]):
        x = win[b].T - win[b].T.mean(0)
        cxx, cyy, cxy = x.T @ x, y.T @ y, x.T @ y
        m = np.linalg.solve(cxx, cxy) @ np.linalg.solve(cyy, cxy.T)
        r2 = np.max(np.linalg.eigvals(m).real)
        out[i, k] += w[b] * min(max(r2, 0.0), 1.0)
  return out


def test_vectorized_equals_loop_reference_to_1e10():
  rng = np.random.default_rng(1)
  bands = rng.normal(size=(7, 3, 6, 200))
  bases = F.reference_bases(FS, 200)
  assert np.max(np.abs(F.fbcca_scores_vectorized(bands, bases, chunk=3) - loop_scores(bands, FS))) < 1e-10


def test_bases_are_orthonormal_and_centred_and_correlations_in_unit_interval():
  bases = F.reference_bases(FS, 256)
  assert bases.shape == (5, 256, 6)
  for q in bases:
    assert np.allclose(q.T @ q, np.eye(6), atol=1e-12) and np.allclose(q.mean(0), 0, atol=1e-12)
  rng = np.random.default_rng(2)
  x = rng.normal(size=(20, 1, 5, 256))
  s = F.fbcca_scores_vectorized(x, bases, weights=np.array([1.0]))   # one band, weight 1: score = r^2 in [0, 1]
  assert s.min() >= 0 and s.max() <= 1.0
  assert F.fbcca_scores_vectorized(bases[0].T[None, None], bases, weights=np.array([1.0]))[0, 0] == pytest.approx(1.0)


@pytest.mark.parametrize("length", [0.5, 1.0, 2.0])
def test_planted_sinusoid_at_each_stimulus_frequency_is_classified(length):
  rng = np.random.default_rng(3)
  T = int(length * FS)
  t = np.arange(T) / FS
  bands = np.stack([np.stack([np.stack([np.sin(2 * np.pi * f * t + 0.3 * c) + 0.3 * rng.normal(size=T)
                                         for c in range(4)]) for _ in range(3)]) for f in F.TARGET_FREQS])
  pred = F.fbcca_scores_vectorized(bands, F.reference_bases(FS, T)).argmax(1)
  assert list(pred) == [0, 1, 2, 3, 4]


def test_flat_band_and_duplicated_channel_are_finite_and_consistent():
  rng = np.random.default_rng(4)
  bands = rng.normal(size=(3, 3, 4, 128))
  bases = F.reference_bases(FS, 128)
  flat = bands.copy()
  flat[0, 1] = 0.0
  s = F.fbcca_scores_vectorized(flat, bases)
  assert np.isfinite(s).all()
  assert np.allclose(s[0], loop_scores(flat[:1, [0, 2]], FS) * 0 + _band_sum(flat[0], bases, [0, 2]), atol=1e-10)
  dup = bands.copy()
  dup[1, :, 3] = dup[1, :, 2]                                       # rank-deficient window: same span as 3 channels
  three = bands[1:2, :, :3]
  assert np.allclose(F.fbcca_scores_vectorized(dup[1:2, :, :4], bases), F.fbcca_scores_vectorized(
    np.concatenate([three[:, :, :2], bands[1:2, :, 2:3]], axis=2), bases), atol=1e-10)


def _band_sum(win, bases, band_idx):
  w = F.fbcca_weights(3)
  return np.array([sum(w[b] * F.fbcca_scores_vectorized(win[b][None, None], bases, np.array([1.0]))[0, k] for b in band_idx)
                   for k in range(len(bases))])


def test_itr_known_values_and_equals_the_nn_sweep_helper():
  from scripts.benchmarks.neural_networks import benchmark_nn_sweep as N
  assert W.itr_bits_per_min(1.0, 5, 1.5) == pytest.approx(np.log2(5) * 60 / 1.5)
  assert W.itr_bits_per_min(0.2, 5, 1.5) == 0.0 and W.itr_bits_per_min(0.05, 5, 1.5) == 0.0
  assert W.itr_bits_per_min(0.5, 5, 1.5) == pytest.approx(
    (np.log2(5) + 0.5 * np.log2(0.5) + 0.5 * np.log2(0.5 / 4)) * 60 / 1.5)
  for acc in (0.0, 0.2, 0.35, 0.7, 0.99, 1.0):
    for sec in (1.0, 2.5, 4.5):
      assert W.itr_bits_per_min(acc, 5, sec) == N.itr_bits_per_min(acc, 5, sec)
  assert W.folder_name(0.5, 0.25) == N.folder_name(0.5, 0.25) == "w0.5_s0.25"


def fake_subject(n_trials=20, wpt=8, C=5, T=128, seed=0, signal=1.0):
  rng = np.random.default_rng(seed)
  tid = np.repeat(np.arange(n_trials), wpt)
  y = np.repeat(101 + np.arange(n_trials) % 5, wpt)
  X = rng.normal(size=(len(y), C, T))
  cls = (y - 101)
  X[np.arange(len(y)), cls % C, :] *= 1.0 + signal
  return {"subject": "Sx", "trial_ids": tid, "cv_groups": tid, "y": y,
          "offsets": np.tile(np.arange(wpt) * 64, n_trials),   # SAMPLES like window_offsets.npy (0.25 s at 256 Hz)
          "fs": FS, "source": "synthetic", "X": X,
          "bands": {"fbcca": rng.normal(size=(len(y), 3, C, T)), "fbcsp": np.stack([X] * 5, axis=1) + rng.normal(size=(len(y), 5, C, T))}}


def test_no_trial_id_shared_between_train_and_test_on_overlapping_windows(monkeypatch):
  d = fake_subject()
  seen = []
  real = W.lda_fold

  def spy(csp, fb, yi, tr, te, seed=42):
    seen.append((tr.copy(), te.copy()))
    return real(csp, fb, yi, tr, te, seed)

  monkeypatch.setattr(W, "lda_fold", spy)
  args = W.build_parser().parse_args(["--cv-repeats", "3"])
  W.run_cell(d, 0.5, W.LDA, args, "cpu", W.fbcca_features(d))
  assert len(seen) == 15
  g = d["cv_groups"]
  for tr, te in seen:
    assert not set(g[tr]) & set(g[te]) and not set(tr) & set(te)
  # the historical bug: a window-level split of the same overlapping windows shares trials in every fold
  from sklearn.model_selection import StratifiedKFold
  leaky = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros((len(g), 1)), d["y"]))
  assert len(shared_trials(leaky, g)) == 5


def test_lda_fold_fits_csp_and_scaler_on_training_rows_only(monkeypatch):
  from src.features.ssvep import fbcsp_extraction as C
  d = fake_subject()
  yi = np.searchsorted(np.unique(d["y"]), d["y"])
  tr = np.flatnonzero(d["cv_groups"] < 14)
  te = np.flatnonzero(d["cv_groups"] >= 14)
  rows = []
  real = C.FBCSPTransformer.fit

  def spy(self, sw, y):
    rows.append(len(sw))
    return real(self, sw, y)

  monkeypatch.setattr(C.FBCSPTransformer, "fit", spy)
  proba, tacc = W.lda_fold(d["bands"]["fbcsp"], np.zeros((len(yi), 5)), yi, tr, te)
  assert rows == [len(tr)] and proba.shape == (len(te), 5) and np.allclose(proba.sum(1), 1)
  # test windows can be replaced by noise without changing the training accuracy or the fitted filters
  d2 = d["bands"]["fbcsp"].copy()
  d2[te] = np.random.default_rng(9).normal(size=d2[te].shape)
  _, tacc2 = W.lda_fold(d2, np.zeros((len(yi), 5)), yi, tr, te)
  assert tacc == tacc2


def test_lda_learns_a_planted_signal():
  d = fake_subject(n_trials=30, signal=3.0)
  args = W.build_parser().parse_args(["--cv-repeats", "2"])
  row, pr, (classes, cm), _ = W.run_cell(d, 0.5, W.LDA, args, "cpu", W.fbcca_features(d))
  assert row["Acc (%)"] > 60 and row["Runs"] == 2 and cm.sum() == 2 * len(d["y"])
  assert list(classes) == [101, 102, 103, 104, 105]
  assert np.allclose(pr[[f"p_{c}" for c in classes]].sum(axis=1), 1)


def test_fbcca_cell_has_no_probabilities_runs_1_and_no_train_accuracy():
  d = fake_subject()
  args = W.build_parser().parse_args([])
  row, pr, _, _ = W.run_cell(d, 0.5, W.FBCCA, args, "cpu", W.fbcca_features(d))
  assert row["Runs"] == 1 and row["Acc SD"] == 0.0 and np.isnan(row["Train Acc (%)"])
  assert pr[[f"p_{c}" for c in range(101, 106)]].isna().all().all() and len(pr) == len(d["y"])


@pytest.fixture(scope="module")
def sweep_root(tmp_path_factory):
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("sweep") / "w1_s0.25"
  S.write_built_subject(root, "S01", n_trials=20, seed=1)
  return root.parent


def run(root, out, *extra):
  return W.main(["--data-root", str(root), "--windows", "1", "--cv-repeats", "2", "--max-folds", "2", "--out-dir", str(out),
                 *extra])


def test_method_split_runs_merge_to_identical_files_in_either_order(sweep_root, tmp_path):
  cnn = ["--methods", "cnn", "--cnn-repeats", "1", "--max-epochs", "1", "--device", "cpu"]
  a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
  assert run(sweep_root, a, "--methods", "fbcca", "lda") == 0 and run(sweep_root, a, *cnn) == 0
  assert run(sweep_root, b, *cnn) == 0 and run(sweep_root, b, "--methods", "lda", "fbcca") == 0
  assert run(sweep_root, c, "--methods", "fbcca", "lda", "cnn", "--cnn-repeats", "1", "--max-epochs", "1", "--device", "cpu") == 0
  for name in ("summary.csv", "predictions.csv", "confusion.csv", "sweep_config.json"):
    assert (a / name).read_bytes() == (b / name).read_bytes() == (c / name).read_bytes(), name
  s = pd.read_csv(a / "summary.csv")
  assert list(s["Method"]) == ["fbcca", "lda", "cnn (compact_eegnet)"]
  p = pd.read_csv(a / "predictions.csv")
  assert list(p.columns) == ["subject", "window_sec", "method", "run", "trial_id", "offset_sec", "true", "pred"] + [
    f"p_{c}" for c in range(101, 106)]
  assert p[p["method"] == "fbcca"]["p_101"].isna().all() and p[p["method"] == "lda"]["p_101"].notna().all()
  cf = pd.read_csv(a / "confusion.csv")
  assert cf.groupby("method")["count"].sum().to_dict() == {
    "fbcca": int((p["method"] == "fbcca").sum()), "lda": int((p["method"] == "lda").sum()),
    "cnn (compact_eegnet)": int((p["method"] == "cnn (compact_eegnet)").sum())}


def test_rerun_with_different_shared_settings_is_refused(sweep_root, tmp_path):
  assert run(sweep_root, tmp_path, "--methods", "fbcca") == 0
  with pytest.raises(SystemExit):
    run(sweep_root, tmp_path, "--methods", "lda", "--seed", "7")
  assert run(sweep_root, tmp_path, "--methods", "lda", "--seed", "7", "--overwrite") == 0


def test_evaluate_subject_requires_fail_fraction_c_b(tmp_path):
  from scripts.benchmarks.feature_based import benchmark_n_subjects as B
  with pytest.raises(ValueError, match="fail_fraction"):
    B.evaluate_subject(tmp_path, "S01", thresholds=TH)


def test_offset_sec_is_in_seconds_while_loader_offsets_are_samples(sweep_root):
  from src.io.subject_data import CLASS_CODES, load_subject
  d = load_subject(sweep_root / "w1_s0.25" / "S01", CLASS_CODES, "shared", bands=("fbcca", "fbcsp"), thresholds=TH,
                   channel_fail_fraction=0.5)
  _, pr, _, _ = W.run_cell(d, 1.0, W.FBCCA, W.build_parser().parse_args([]), "cpu", W.fbcca_features(d))
  assert np.allclose(pr["offset_sec"].to_numpy(), np.asarray(d["offsets"]) / d["fs"])
  fk = fake_subject()
  _, pf, _, _ = W.run_cell(fk, 0.5, W.FBCCA, W.build_parser().parse_args([]), "cpu", W.fbcca_features(fk))
  assert set(np.round(pf["offset_sec"], 6)) == {k * 0.25 for k in range(8)}
