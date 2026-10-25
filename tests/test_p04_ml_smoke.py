"""P04 ml-engineer smoke tests: LDA/XAI scripts on a synthetic legacy tree (tmp_path only)."""

import joblib
import numpy as np
import pytest
from scipy.signal import periodogram

from scripts.training import batch_run_subjects, train_final_model, train_models
from scripts.xai import compare_subject_xai, run_xai

FS = 256
FREQ = {101: 24.0, 102: 20.0, 103: 15.0, 104: 10.9091, 105: 8.5714}


def _make(root, subject, per_class=12, seed=0):
  rng = np.random.default_rng(seed)
  t = np.arange(FS) / FS
  Xp, Xt, y = [], [], []
  for code in (201, 202) + tuple(FREQ):
    for _ in range(3 if code in (201, 202) else per_class):
      w = rng.normal(0, 1, (7, FS))
      if code in FREQ:
        w[[1, 4, 5, 6]] += 3 * np.sin(2 * np.pi * FREQ[code] * t + rng.uniform(0, 6))
      f, p = periodogram(w, fs=FS, axis=-1)
      Xp.append(p[:, (f >= 5) & (f <= 35)].reshape(-1)); Xt.append(w); y.append(code)
  d = root / subject
  d.mkdir(parents=True)
  np.save(d / "X_psd_features.npy", np.array(Xp))
  np.save(d / "X_time_windows.npy", np.array(Xt))
  np.save(d / "y_labels.npy", np.array(y))


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
  root = tmp_path_factory.mktemp("p04")
  for i, s in enumerate(("S01", "S04")):
    _make(root / "processed", s, seed=i)
  return root


def test_harmonic_features_channel_major():
  X = np.arange(7 * 31, dtype=float)[None]
  out = train_models.extract_harmonic_features(X)
  assert out.shape == (1, 32)
  assert out[0, :8].tolist() == [31 + j for j in (4, 6, 10, 12, 15, 17, 19, 25)]


def test_smoothing_no_reset():
  p = np.arange(20, dtype=float).reshape(10, 2)
  s = train_models.smooth_probabilities_legacy(p)
  assert np.allclose(s[0], p[0]) and np.allclose(s[5], (p[4] + p[5]) / 2)


def test_pipeline_end_to_end(tree):
  proc, out = tree / "processed", tree / "out"
  assert train_models.main(["--subject", "S01", "--processed-dir", str(proc), "--out-dir", str(out)]) == 0
  assert (out / "reports" / "S01_model_evaluation.csv").is_file()
  for s in ("S01", "S04"):
    assert train_final_model.main(["--subject", s, "--processed-dir", str(proc), "--out-dir", str(out), "--epochs", "2"]) == 0
  b = joblib.load(out / "models" / "S01_shrinkage_lda.joblib")
  assert {"model", "scaler", "classes", "subject_id", "feature_dim"} <= set(b) and b["feature_dim"] == 37
  assert run_xai.main(["--subject", "S04", "--processed-dir", str(proc), "--out-dir", str(out)]) == 0
  assert compare_subject_xai.main(["--out-dir", str(out)]) == 0
  assert (out / "figures" / "xai_heatmaps" / "compare_S01_S04.png").is_file()
  assert batch_run_subjects.main(["--subjects", "S01", "S04", "--processed-dir", str(proc),
                                  "--out-dir", str(out), "--epochs", "2"]) == 0


def test_weight_arrays_slices():
  coef = np.random.default_rng(0).normal(size=(5, 37))
  sp, fb = run_xai.weight_arrays(coef)
  assert sp.shape == (5, 4, 8) and sp[2, 1, 3] == coef[2, 8 + 3] and np.array_equal(fb, coef[:, -5:])
