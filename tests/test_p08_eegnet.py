"""P08 tests (deep-learning): EEGNetSSVEP count/shape/max-norm, z-scoring, per-fold seeding, learnable task,
CV protocol and the benchmark script on a synthetic legacy tree. Synthetic data only, fixed seeds, CPU."""

import numpy as np
import pandas as pd
import pytest
import torch

from scripts.benchmarks.neural_networks import benchmark_eegnet as be
from src.models.cnn.eegnet import EEGNetSSVEP, count_parameters
from src.models.cnn.eegnet_cv import train_and_eval_eegnet_cv, train_model, zscore_windows
from tests.p05_synth import make_windows, write_subject


def test_param_count_r8_and_no_conv_bias():
  m = EEGNetSSVEP()
  assert count_parameters(m) == 2349  # R-8; with biased convs it would be larger (B004)
  convs = [l for l in m.modules() if isinstance(l, torch.nn.Conv2d)]
  assert len(convs) == 4 and all(c.bias is None for c in convs)
  assert m.head.in_features == 16 * 8


@pytest.mark.parametrize("C,T", [(7, 256), (8, 256), (7, 128), (7, 512), (5, 256)])
def test_shapes_and_input_forms(C, T):
  m = EEGNetSSVEP(n_channels=C, n_samples=T).eval()
  x = torch.randn(3, C, T)
  a, b = m(x), m(x.unsqueeze(1))
  assert a.shape == (3, 5) and torch.allclose(a, b, atol=1e-6)


def test_spatial_filter_acts_over_channels_and_wrong_layout_rejected():
  m = EEGNetSSVEP().eval()
  with pytest.raises(ValueError):
    m(torch.randn(2, 256, 7))  # (B, T, C) swapped
  x = torch.randn(2, 7, 256)
  assert not torch.allclose(m(x), m(x.flip(1)))  # channel order matters (spatial conv spans channels)


def test_max_norm_after_step_and_other_layers_free():
  torch.manual_seed(0)
  m = EEGNetSSVEP()
  with torch.no_grad():
    m.spatial.weight.mul_(10)
    m.pointwise.weight.mul_(10)
  big = float(m.pointwise.weight.detach().flatten(1).norm(dim=1).max())
  opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
  m(torch.randn(8, 7, 256)).sum().backward()
  opt.step()
  m.apply_max_norm()
  norms = m.spatial.weight.flatten(1).norm(dim=1)
  assert float(norms.max()) <= 1.0 + 1e-6 and len(norms) == 16
  assert float(m.pointwise.weight.detach().flatten(1).norm(dim=1).max()) > 1.0 and big > 1.0  # unconstrained


def test_max_norm_leaves_small_filters_unchanged():
  m = EEGNetSSVEP()
  with torch.no_grad():
    m.spatial.weight.mul_(1e-3)
  before = m.spatial.weight.clone()
  m.apply_max_norm()
  assert torch.equal(before, m.spatial.weight)


def test_all_parameters_receive_gradients():
  m = EEGNetSSVEP()
  m(torch.randn(8, 7, 256)).sum().backward()
  assert all(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in m.parameters())


def test_zscore_per_window_channel_and_independent_of_other_windows():
  rng = np.random.default_rng(0)
  X = rng.normal(0, 1, (6, 7, 256)) * rng.uniform(1, 50, (6, 7, 1)) + rng.uniform(-100, 100, (6, 7, 1))
  Z = zscore_windows(X)
  assert np.allclose(Z.mean(-1), 0, atol=1e-5) and np.allclose(Z.std(-1), 1, atol=1e-4)
  X2 = X.copy()
  X2[3] *= 7.0
  X2[3] += 40.0
  Z2 = zscore_windows(X2)
  assert np.array_equal(np.delete(Z, 3, 0), np.delete(Z2, 3, 0)) and np.allclose(Z[3], Z2[3], atol=1e-4)


def _data(n_trials=4, seed=0):
  X, y = make_windows(n_trials=n_trials, seed=seed)
  return X, y


def test_cv_deterministic_seed_sensitive_and_protocol():
  X, y = _data()
  a = train_and_eval_eegnet_cv(X, y, epochs=2, device="cpu", cv="legacy")
  b = train_and_eval_eegnet_cv(X, y, epochs=2, device="cpu", cv="legacy")
  c = train_and_eval_eegnet_cv(X, y, epochs=2, device="cpu", seed=7, cv="legacy")
  assert np.array_equal(a["proba"], b["proba"]) and not np.allclose(a["proba"], c["proba"])
  assert len(a["fold_test_acc"]) == 5 and 0 <= a["train_accuracy"] <= 1 and a["n_params"] == 2349
  assert a["classes"] == [101, 102, 103, 104, 105]
  assert "StratifiedKFold(5, shuffle, 42)" in a["cv"]
  from src.models.classical.legacy_eval import accuracies
  assert (a["accuracy"], a["smoothed_accuracy"]) == accuracies(y, a["pred"], a["proba"])


def test_fold_models_seeded_by_fold():
  X, y = _data(2)
  Z = zscore_windows(X)
  yi = y - 101
  w = lambda s: train_model(Z, yi, s, torch.device("cpu"), epochs=1).head.weight.detach().clone()
  assert torch.equal(w(42), w(42)) and not torch.equal(w(42), w(43))


def test_learnable_planted_sinusoids():
  X, y = _data(n_trials=8)
  r = train_and_eval_eegnet_cv(X, y, epochs=25, device="cpu", lr=3e-3, cv="legacy")
  assert r["accuracy"] > 0.6, r["accuracy"]


def test_script_smoke_and_augment_choices(tmp_path):
  write_subject(tmp_path / "proc", "S03", n_trials=3)
  rep = tmp_path / "rep" / "legacy_leaky"  # --cv legacy writes under legacy_leaky/ (P11)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  args = ["--subject", "S03", "--epochs", "2", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
          "--reports-dir", str(tmp_path / "rep"), "--config", str(cfg), "--cv", "legacy", "--smoothing", "mod5"]
  assert be.main(args) == 0
  df = pd.read_csv(rep / "eegnet_benchmark_cpu.csv")
  assert list(df.columns) == be.COLUMNS and df.loc[0, "Params"] == 2349 and df.loc[0, "Device"] == "cpu"
  assert df.loc[0, "Clean Windows"] + df.loc[0, "Rejected"] == 75
  meta = (rep / "eegnet_benchmark_cpu.meta.txt").read_text()
  assert "legacy" in meta and "i%5" in meta and "PF-30" in meta
  with pytest.raises(SystemExit):
    be.build_parser().parse_args(["--augment", "maybe"])
