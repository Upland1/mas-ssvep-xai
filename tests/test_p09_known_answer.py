"""P09 independent known-answer tests (synthetic-tester): per-layer parameter arithmetic, kernel/pool arithmetic,
layout of the spatial/temporal convs (R6), exact log clamp value, recorded training protocol of the three network
benchmarks (mirror), count_parameters failing on a mismatch, and the P08 carry-forward gate-equality test
(network gate == classical prepare_subject decision on a tree with a bad channel). Expected values come from
mas/04_REFERENCE_RESULTS.md R-8 and hand arithmetic, not from the builders' code. Synthetic data, fixed seeds, CPU."""

import math

import numpy as np
import pytest
import torch

from scripts.benchmarks.neural_networks import benchmark_compact_cnn as bc
from scripts.benchmarks.neural_networks import benchmark_eegnet as be
from scripts.benchmarks.neural_networks import benchmark_shallow_convnet as bs
from scripts.benchmarks.neural_networks import count_parameters as cp
from src.models.classical.benchmark_runner import prepare_subject
from src.models.cnn import eegnet_cv
from src.models.cnn.compact_cnn import CompactCNN
from src.models.cnn.shallow_conv_net import ShallowConvNet
from tests.p05_synth import write_subject


def n_params(m):
  return sum(p.numel() for p in m.parameters() if p.requires_grad)


# ---------- hand arithmetic (R-8) ----------

def compact_expected(C=7, T=256, K=29, F1=16, F2=32, n_classes=5):
  """spatial F1*C + BN 2*F1 + temporal F2*F1*K + BN 2*F2 + head (F2*L)*n + n, with L = T + 2*(K//2) - K + 1."""
  L = T + 2 * (K // 2) - K + 1
  return F1 * C + 2 * F1 + F2 * F1 * K + 2 * F2 + F2 * L * n_classes + n_classes


def shallow_expected(C=7, T=256, F1=40, k=25, pk=75, ps=15, n_classes=5):
  """temporal F1*k + spatial F1*F1*C + BN 2*F1 + head (F1*L)*n + n, with L = (T-k+1-pk)//ps + 1."""
  L = (T - k + 1 - pk) // ps + 1
  return F1 * k + F1 * F1 * C + 2 * F1 + F1 * L * n_classes + n_classes


def test_r8_counts_by_hand_arithmetic():
  """R-8: Compact-CNN 56,021 (K=29), ShallowConvNet 14,485 (pooled length 11); exact, hand formulas agree."""
  assert compact_expected() == 56021 and shallow_expected() == 14485
  assert n_params(CompactCNN()) == 56021 and n_params(ShallowConvNet()) == 14485


@pytest.mark.parametrize("fs,K", [(250.0, 29), (256.0, 30)])
def test_compact_kernel_from_fs(fs, K):
  """K = round(fs/8.5714): 250 -> 29.17 -> 29, 256 -> 29.87 -> 30 (PF-04). Count follows hand formula."""
  m = CompactCNN(fs=fs)
  assert m.temporal.kernel_size == (1, K) and n_params(m) == compact_expected(K=K)
  assert compact_expected(K=30) == 56693  # PF-04 mutant (K from fs 256 at the legacy default) is not R-8


def test_compact_default_is_legacy_250_not_256():
  """The default constructor must give K=29 (legacy fs 250), not 30 -> 56,021 not 56,693."""
  assert CompactCNN().temporal.kernel_size == (1, 29) and n_params(CompactCNN()) != 56693


@pytest.mark.parametrize("pk,ps,L", [(75, 15, 11), (50, 15, 13), (75, 10, 16)])
def test_shallow_pool_arithmetic(pk, ps, L):
  """Pooled length (T-25+1-pk)//ps+1 for T=256; the R-8 pool (75/15) is the only one giving 14,485."""
  m = ShallowConvNet(pool_kernel_length=pk, pool_stride=ps)
  assert m.head.in_features == 40 * L and n_params(m) == shallow_expected(pk=pk, ps=ps)
  assert (n_params(m) == 14485) == ((pk, ps) == (75, 15))


def test_conv_bias_mutants_break_r8():
  """A conv bias adds F1+F2 (Compact: 48) or 2*F1 (Shallow: 80) parameters, so it cannot match R-8."""
  c = CompactCNN()
  c.spatial = torch.nn.Conv2d(1, 16, (7, 1), bias=True)
  assert n_params(c) == 56021 + 16
  s = ShallowConvNet()
  s.temporal = torch.nn.Conv2d(1, 40, (1, 25), bias=True)
  s.spatial = torch.nn.Conv2d(40, 40, (7, 1), bias=True)
  assert n_params(s) == 14485 + 80
  assert all(l.bias is None for m in (CompactCNN(), ShallowConvNet()) for l in m.modules()
             if isinstance(l, torch.nn.Conv2d))


# ---------- layout (R6) and log clamp ----------

def _identity_bn(m):
  for l in m.modules():
    if isinstance(l, torch.nn.BatchNorm2d):
      l.eval()


def test_compact_spatial_temporal_layout_identity_path():
  """R6: spatial filter 0 = one-hot on channel 3, temporal filter 0 = centred delta (index K//2) on input map 0.
  In eval (BN at init ~ identity, scale 1/sqrt(1+1e-5)) feature map 0 equals ELU(x[:,3,:]) with no time shift;
  tolerance 1e-3 relative (BN eps)."""
  m = CompactCNN().eval()
  with torch.no_grad():
    m.spatial.weight.zero_()
    m.spatial.weight[0, 0, 3, 0] = 1.0
    m.temporal.weight.zero_()
    m.temporal.weight[0, 0, 0, 14] = 1.0
  x = torch.from_numpy(np.random.default_rng(0).uniform(0.5, 2.0, (2, 7, 256)).astype(np.float32))
  with torch.no_grad():
    f = m.features(x.unsqueeze(1)).reshape(2, 32, 256)
  assert torch.allclose(f[:, 0, :], x[:, 3, :], rtol=1e-3, atol=1e-3)
  assert float(f[:, 1:, :].abs().max()) < 1e-6


def test_shallow_spatial_temporal_layout():
  """R6: temporal filter 0 = delta at tap 0 (output[t] = x[t]); spatial filter 0 = one-hot on (map 0, channel 5).
  Then the pre-BN map 0 is x[:,5,:232]; BN eval ~identity; the pooled square mean equals the mean of x^2 over each
  75-sample window, so log(pool) = log(mean x^2) at the 11 windows (tolerance 1e-3)."""
  m = ShallowConvNet().eval()
  with torch.no_grad():
    m.temporal.weight.zero_()
    m.temporal.weight[0, 0, 0, 0] = 1.0
    m.spatial.weight.zero_()
    m.spatial.weight[0, 0, 5, 0] = 1.0
  x = torch.from_numpy(np.random.default_rng(1).normal(0, 1.0, (2, 7, 256)).astype(np.float32)) + 3.0
  with torch.no_grad():
    f = m.features(x.unsqueeze(1)).reshape(2, 40, 11)
  sq = (x[:, 5, :232] ** 2 / (1 + 1e-5)).numpy()  # BN eval with init stats scales by 1/sqrt(1+eps)
  want = np.log(np.stack([sq[:, i * 15:i * 15 + 75].mean(1) for i in range(11)], axis=1))
  assert np.allclose(f[:, 0, :].numpy(), want, atol=1e-3)


def test_shallow_zero_input_gives_exactly_log_eps():
  """Zero input -> pooled power 0 -> log(clamp(0, 1e-6)) = log(1e-6) = -13.8155 for every feature (exact, 1e-5);
  an unclamped log gives -inf. Output logits and gradients are finite."""
  m = ShallowConvNet().eval()
  x = torch.zeros(2, 7, 256)
  with torch.no_grad():
    f = m.features(x.unsqueeze(1))
  assert torch.allclose(f, torch.full_like(f, math.log(1e-6)), atol=1e-5)
  m.train()
  m(x).sum().backward()
  assert all(torch.isfinite(p.grad).all() for p in m.parameters() if p.grad is not None)


# ---------- count_parameters script ----------

def test_count_parameters_fails_on_mismatch(tmp_path, monkeypatch):
  """A count that differs from R-8 by one parameter must give exit 1 (and the CSV is still written)."""
  assert cp.main(["--reports-dir", str(tmp_path / "ok")]) == 0
  real = cp.counts()
  assert real == {"eegnet": 2349, "shallow_convnet": 14485, "compact_cnn": 56021}
  for k in real:
    bad = dict(real, **{k: real[k] + 1})
    monkeypatch.setattr(cp, "counts", lambda bad=bad: bad)
    assert cp.main(["--reports-dir", str(tmp_path / f"bad_{k}")]) == 1


# ---------- mirror protocol: what the three benchmarks actually call ----------

def _record(mod, tmp_path, tag, monkeypatch, extra=()):
  """Run a benchmark main (2 epochs, tiny synthetic tree) and record optimizer, scheduler, loss, seeds, loader and
  fold calls made by the shared training code."""
  calls = {"seed": [], "adamw": [], "sched": [], "loss": [], "loader": [], "folds": []}
  Opt, Sch, Loss = torch.optim.AdamW, torch.optim.lr_scheduler.CosineAnnealingLR, torch.nn.CrossEntropyLoss
  Seed, DL, cv = torch.manual_seed, eegnet_cv.DataLoader, eegnet_cv.make_splits

  def opt(params, **kw):
    calls["adamw"].append(kw)
    return Opt(params, **kw)

  def sch(o, *a, **kw):
    calls["sched"].append((a, kw))
    return Sch(o, *a, **kw)

  def loss(*a, **kw):
    calls["loss"].append((a, kw))
    return Loss(*a, **kw)

  def seed(s):
    calls["seed"].append(int(s))
    return Seed(s)

  def dl(ds, **kw):
    calls["loader"].append({k: v for k, v in kw.items() if k != "generator"})
    return DL(ds, **kw)

  def make_splits(kind, y, ids, s=42):
    calls["folds"].append(f"{kind} n_splits=5 shuffle=True random_state={s}")
    return cv(kind, y, ids, s)

  monkeypatch.setattr(torch.optim, "AdamW", opt)
  monkeypatch.setattr(torch.optim.lr_scheduler, "CosineAnnealingLR", sch)
  monkeypatch.setattr(torch.nn, "CrossEntropyLoss", loss)
  monkeypatch.setattr(torch, "manual_seed", seed)
  monkeypatch.setattr(eegnet_cv, "DataLoader", dl)
  monkeypatch.setattr(eegnet_cv, "make_splits", make_splits)
  if not (tmp_path / "proc").exists():
    write_subject(tmp_path / "proc", "S03", n_trials=3)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  argv = ["--subject", "S03", "--epochs", "2", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
          "--reports-dir", str(tmp_path / f"rep_{tag}"), "--config", str(cfg), "--cv", "legacy", "--smoothing", "mod5", *extra]
  assert mod.main(argv) == 0
  monkeypatch.undo()
  return calls


def test_mirror_recorded_training_calls_identical(tmp_path, monkeypatch):
  """EEGNet, Compact-CNN and ShallowConvNet call AdamW(lr 1e-3, wd 1e-2), Cosine(T_max 2, eta_min 1e-5),
  CE(label_smoothing 0.05), manual_seed 42..46, the same loader settings and the same StratifiedKFold(5, shuffle, 42)."""
  rec = {n: _record(m, tmp_path, n, monkeypatch) for m, n in ((be, "eegnet"), (bc, "compact_cnn"), (bs, "shallow_convnet"))}
  ref = rec["eegnet"]
  assert ref["seed"] == [42, 43, 44, 45, 46] and len(ref["adamw"]) == 5
  assert all(k["lr"] == 1e-3 and k["weight_decay"] == 1e-2 for k in ref["adamw"])
  assert all(kw == {"T_max": 2, "eta_min": 1e-5} for _, kw in ref["sched"])
  assert all(kw == {"label_smoothing": 0.05} for _, kw in ref["loss"])
  assert "n_splits=5" in ref["folds"][0] and "shuffle=True" in ref["folds"][0] and "random_state=42" in ref["folds"][0]
  for n in ("compact_cnn", "shallow_convnet"):
    assert rec[n] == ref, n


@pytest.mark.parametrize("extra", [("--seed", "7"), ("--epochs", "3"), ("--lr", "0.01"), ("--batch-size", "16")])
def test_mirror_recorder_detects_drift(tmp_path, monkeypatch, extra):
  """Negative control: a script run with a different seed / epochs / lr / batch yields a different record, so the
  mirror comparison above would fail on such a script."""
  base = _record(bs, tmp_path, "base", monkeypatch)
  other = _record(bs, tmp_path, "other", monkeypatch, extra)
  assert base != other


# ---------- P08 carry-forward: gate equality with the classical decision ----------

@pytest.mark.parametrize("bad", [(), ("O2",), ("PO4", "Oz")])
def test_network_gate_equals_classical_prepare_subject(tmp_path, bad):
  """The network benchmarks' gated_windows and the classical prepare_subject make the same decision on the same
  tree: identical kept channels, dropped channels, clean-window count and clean labels. Bad channels (Vpp 400 uV
  square wave) are dropped by both, so the array has 7 - len(bad) channels."""
  write_subject(tmp_path, "S03", bad_channels=bad, n_trials=3)
  ref = prepare_subject(tmp_path, "S03")
  for mod in (be, bc, bs):
    g = mod.gated_windows(tmp_path, "S03")
    assert g["kept"] == list(ref["channels_kept"]) and g["dropped"] == list(ref["channels_dropped"])
    assert g["n_clean"] == ref["n_clean"] and g["n_stimulus"] == ref["n_stimulus"]
    assert np.array_equal(g["y"], ref["y"])
    assert g["X"].shape[1] == 7 - len(bad) and set(g["dropped"]) == set(bad)
