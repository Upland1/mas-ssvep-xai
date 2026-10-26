"""P08 independent known-answer tests (synthetic-tester): R-8 layer arithmetic, padding/flatten, max-norm on the
depthwise spatial conv only, per-window z-score, per-fold seeds, legacy CV folds, i%5 smoothing, PF-30 train accuracy.
Expected values come from the roadmap/R-8 arithmetic and sklearn, not from the builder's code. Synthetic, CPU."""

import numpy as np
import pytest
import torch
from sklearn.model_selection import StratifiedKFold

from src.models.classical.legacy_eval import accuracies
from src.models.cnn import eegnet_cv
from src.models.cnn.eegnet import EEGNetSSVEP
from src.models.cnn.eegnet_cv import train_and_eval_eegnet_cv, zscore_windows
from tests.p05_synth import make_windows

CPU = torch.device("cpu")


def test_layer_by_layer_parameter_arithmetic():
  """Known answer (R-8 arithmetic): temporal 8*125=1000, BN1 16, spatial 16*7=112, BN2 32, depthwise 16*16=256,
  pointwise 16*16=256, BN3 32, head 128*5+5=645; total 2349. Exact."""
  m = EEGNetSSVEP()
  assert tuple(m.temporal.weight.shape) == (8, 1, 1, 125) and m.temporal.weight.numel() == 1000
  assert tuple(m.spatial.weight.shape) == (16, 1, 7, 1) and m.spatial.weight.numel() == 112
  assert tuple(m.depthwise2.weight.shape) == (16, 1, 1, 16)
  assert tuple(m.pointwise.weight.shape) == (16, 16, 1, 1)
  assert sum(p.numel() for p in m.head.parameters()) == 645
  bn = sum(p.numel() for l in m.modules() if isinstance(l, torch.nn.BatchNorm2d) for p in l.parameters())
  assert bn == 16 + 32 + 32
  assert sum(p.numel() for p in m.parameters()) == 2349
  assert all(l.bias is None for l in m.modules() if isinstance(l, torch.nn.Conv2d))


def test_padding_keeps_length_and_flatten_is_128():
  """Known answer: temporal conv K=125 with pad K//2=62 keeps 256 samples; pool 4 -> 64; depthwise (1,16) pad 8
  gives 65; pool 8 -> 8; flatten 16*8 = 128. Exact."""
  m = EEGNetSSVEP().eval()
  x = torch.randn(2, 1, 7, 256)
  t = m.temporal(x)
  assert tuple(t.shape) == (2, 8, 7, 256)
  s = m.spatial(t)
  assert tuple(s.shape) == (2, 16, 1, 256)
  assert m.depthwise2(m.block1_tail(m.bn2(s))).shape[-1] == 65
  assert m.features(x).shape == (2, 128) and m.head.in_features == 128


def test_depthwise_spatial_group_structure():
  """Known answer: spatial output channel j depends only on temporal map j // 2 (groups=8) and sums over all 7
  channels. Gradient support check, exact zeros elsewhere."""
  m = EEGNetSSVEP().eval()
  t = torch.randn(1, 8, 7, 64, requires_grad=True)
  m.spatial(t)[0, 5].sum().backward()
  g = t.grad.abs().sum(dim=(2, 3))[0]
  assert float(g[2]) > 0 and float(g.sum() - g[2]) == 0.0  # 5 // 2 == 2
  assert (t.grad[0, 2].abs().sum(dim=1) > 0).all()  # every electrode contributes


def test_max_norm_known_scaling_direction_and_layer():
  """Known answer: a spatial filter of L2 norm 3 is rescaled to exactly 1 keeping its direction; filter of norm
  0.5 is untouched; pointwise/temporal/depthwise2 weights are never touched. Tolerance 1e-6."""
  m = EEGNetSSVEP()
  with torch.no_grad():
    m.spatial.weight.zero_()
    m.spatial.weight[0, 0, :, 0] = torch.tensor([3.0, 0, 0, 0, 0, 0, 0])
    m.spatial.weight[1, 0, :, 0] = torch.tensor([0.0, 1.2, 0, 1.6, 0, 0, 2.0]) * 1.0
    m.spatial.weight[2, 0, :, 0] = torch.tensor([0.0, 0, 0.3, 0.4, 0, 0, 0])
    m.pointwise.weight.mul_(20)
    m.depthwise2.weight.mul_(20)
  pw, dw = m.pointwise.weight.clone(), m.depthwise2.weight.clone()
  v1 = m.spatial.weight[1, 0, :, 0].clone()
  m.apply_max_norm()
  w = m.spatial.weight[:, 0, :, 0]
  assert torch.allclose(w[0], torch.tensor([1.0, 0, 0, 0, 0, 0, 0]), atol=1e-6)
  assert torch.allclose(w[1], v1 / v1.norm(), atol=1e-6)
  assert torch.allclose(w[2].norm(), torch.tensor(0.5), atol=1e-6)
  assert torch.equal(pw, m.pointwise.weight) and torch.equal(dw, m.depthwise2.weight)


def test_max_norm_holds_after_training_with_large_steps():
  """Known answer: after train_model with a huge lr (0.5) every one of 16 spatial filters has norm <= 1 + 1e-6 while
  the pointwise conv is unconstrained (norm > 1). Fails if max-norm is missing or applied to the wrong layer."""
  X, y = make_windows(n_trials=2, seed=1)
  m = eegnet_cv.train_model(zscore_windows(X), y - 101, 0, CPU, epochs=3, lr=0.5)
  n = m.spatial.weight.detach().flatten(1).norm(dim=1)
  assert len(n) == 16 and float(n.max()) <= 1.0 + 1e-6
  assert float(m.pointwise.weight.detach().flatten(1).norm(dim=1).max()) > 1.0


def test_zscore_scaling_one_window_changes_no_other_and_constant_is_finite():
  """Known answer: per-window statistics only; scaling/offsetting window 2 leaves the others bit-identical;
  a constant window maps to finite zeros (epsilon)."""
  rng = np.random.default_rng(3)
  X = rng.normal(5, 3, (5, 7, 256))
  Z = zscore_windows(X)
  X2 = X.copy()
  X2[2] = 100 * X2[2] - 7
  Z2 = zscore_windows(X2)
  assert np.array_equal(np.delete(Z, 2, 0), np.delete(Z2, 2, 0))
  assert np.allclose(Z[2], Z2[2], atol=1e-4)
  X[0, 0] = 4.0
  Zc = zscore_windows(X)
  assert np.isfinite(Zc).all() and np.allclose(Zc[0, 0], 0)


def _spy_cv(monkeypatch, X, y, **kw):
  calls = {"train_X": [], "seeds": [], "models": [], "pred_X": []}
  real_train, real_pred = eegnet_cv.train_model, eegnet_cv.predict_proba

  def train(Xz, yi, seed, device, *a, **k):
    calls["train_X"].append(Xz.copy())
    calls["seeds"].append(seed)
    mdl = real_train(Xz, yi, seed, device, *a, **k)
    calls["models"].append(mdl)
    return mdl

  def pred(model, Xe, device, chunk=256):
    calls["pred_X"].append(Xe.copy())
    return real_pred(model, Xe, device, chunk)

  monkeypatch.setattr(eegnet_cv, "train_model", train)
  monkeypatch.setattr(eegnet_cv, "predict_proba", pred)
  res = train_and_eval_eegnet_cv(X, y, epochs=1, device="cpu", **kw, cv="legacy")
  return res, calls


def test_seed_per_fold_and_folds_are_stratifiedkfold_5_true_42(monkeypatch):
  """Known answer: seeds 42..46 (seed+fold) and training rows equal StratifiedKFold(5, True, 42) of sklearn,
  held-out rows are those predicted. Exact. Fails for a once-set seed or other CV seed/shuffle."""
  X, y = make_windows(n_trials=3, seed=2)
  res, c = _spy_cv(monkeypatch, X, y)
  yi = y - 101
  Z = zscore_windows(X)
  folds = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros((len(y), 1)), yi))
  assert c["seeds"] == [42, 43, 44, 45, 46]
  for k, (tr, te) in enumerate(folds):
    assert np.array_equal(c["train_X"][k], Z[tr])
    assert np.array_equal(c["pred_X"][2 * k], Z[te])
  assert [len(p) for p in c["pred_X"][1::2]] == [len(tr) for tr, _ in folds]
  _, c2 = _spy_cv(monkeypatch, X, y, seed=7)
  assert c2["seeds"] == [7, 8, 9, 10, 11]


def test_train_accuracy_is_on_training_rows_pf30(monkeypatch):
  """Known answer (PF-30): reported train accuracy = mean over folds of accuracy of that fold's model on its own
  un-augmented training rows (recomputed independently here); tolerance 1e-12."""
  X, y = make_windows(n_trials=3, seed=4)
  res, c = _spy_cv(monkeypatch, X, y)
  yi = y - 101
  Z = zscore_windows(X)
  accs = []
  for mdl, (tr, te) in zip(c["models"], StratifiedKFold(5, shuffle=True, random_state=42).split(Z, yi)):
    mdl.eval()
    with torch.no_grad():
      p = mdl(torch.from_numpy(Z[tr])).argmax(1).numpy()
    accs.append(float(np.mean(p == yi[tr])))
  assert res["train_accuracy"] == pytest.approx(np.mean(accs), abs=1e-12)


def test_smoothing_resets_at_i_mod_5():
  """Known answer (R8 legacy): windows 0-4 class 101, 5-9 class 102; window 4 is confidently 101 and window 5 is
  correct (0.6 vs 0.4). With the i%5 reset window 5 is not averaged with window 4: smoothed acc = 1.0 (a no-reset
  average gives 0.9). Raw acc = 1.0."""
  P = np.zeros((10, 5))
  P[:5, 0] = 0.9
  P[5:, 1] = 0.9
  P[4] = [0.99, 0.0025, 0.0025, 0.0025, 0.0025]
  P[5] = [0.4, 0.6, 0, 0, 0]
  y = np.array([101] * 5 + [102] * 5)
  pred = np.array([101, 102, 103, 104, 105])[P.argmax(1)]
  a1, a2 = accuracies(y, pred, P)
  assert a1 == 1.0 and a2 == 1.0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA device")
def test_cuda_forward_matches_cpu():
  """Known answer: same weights, eval mode, CPU and CUDA outputs agree to 1e-4; output (B, 5)."""
  torch.manual_seed(0)
  m = EEGNetSSVEP().eval()
  x = torch.randn(4, 7, 256)
  with torch.no_grad():
    a = m(x)
    b = m.cuda()(x.cuda()).cpu()
  assert b.shape == (4, 5) and torch.allclose(a, b, atol=1e-4)
