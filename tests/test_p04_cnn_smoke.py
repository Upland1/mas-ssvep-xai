"""P04 deep-learning smoke tests: parameter count, forward, short CV, export (synthetic arrays only)."""

import numpy as np
import torch

from src.models.cnn.spatial_spectral_cnn import (
  DualBranchFusionCNN, count_parameters, evaluate_temporal_smoothing, prepare_spatial_spectral_tensors,
  train_and_eval_fusion_cnn_cv)


def test_parameter_count_r8():
  m = DualBranchFusionCNN()
  assert count_parameters(m) == 10005
  convs = [l for l in m.modules() if isinstance(l, torch.nn.Conv2d)]
  assert len(convs) == 2 and all(c.bias is None for c in convs)
  assert m(torch.zeros(3, 1, 4, 8), torch.zeros(3, 5)).shape == (3, 5)


def _data(n=100, seed=0):
  rng = np.random.default_rng(seed)
  y = np.repeat([101, 102, 103, 104, 105], n // 5)
  X_psd = rng.normal(size=(n, 217)) ** 2
  fb = rng.normal(size=(n, 5)) + 3 * np.eye(5)[y - 101]
  return X_psd, fb, y


def test_cv_short_deterministic_and_reports_train_acc():
  X_psd, fb, y = _data()
  xs = prepare_spatial_spectral_tensors(X_psd)
  assert xs.shape == (100, 1, 4, 8)
  a = train_and_eval_fusion_cnn_cv(xs, fb, y, epochs=2, device="cpu")
  b = train_and_eval_fusion_cnn_cv(xs, fb, y, epochs=2, device="cpu")
  assert np.array_equal(a["pred"], b["pred"]) and np.allclose(a["proba"], b["proba"])
  assert 0 <= a["train_accuracy"] <= 1 and len(a["fold_test_acc"]) == 5
  assert 0 <= evaluate_temporal_smoothing(a["proba"], y, a["classes"]) <= 1
