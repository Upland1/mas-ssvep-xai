"""P09 tests (deep-learning): CompactCNN / ShallowConvNet counts (R-8), kernel and pooling arithmetic, log clamp,
shapes and gradients, the shared mirror protocol, EEGNet regression after the refactor, benchmark scripts and the
count_parameters script on a synthetic legacy tree. Synthetic data only, fixed seeds, CPU."""

import hashlib

import numpy as np
import pandas as pd
import pytest
import torch

from scripts.benchmarks.neural_networks import benchmark_compact_cnn as bc
from scripts.benchmarks.neural_networks import benchmark_eegnet as be
from scripts.benchmarks.neural_networks import benchmark_shallow_convnet as bs
from scripts.benchmarks.neural_networks import count_parameters as cp
from src.models.cnn.compact_cnn import CompactCNN, temporal_kernel_length
from src.models.cnn.eegnet import EEGNetSSVEP, count_parameters
from src.models.cnn.eegnet_cv import train_and_eval_cv, train_and_eval_eegnet_cv
from src.models.cnn.shallow_conv_net import LOG_EPS, ShallowConvNet
from tests.p05_synth import make_windows, write_subject

EEGNET_SMOKE_CSV_SHA256 = "6dbbe4aae453dbe3f313df927728863cfd852d5333550de75b960759bb9bd478"  # pre-refactor (P08 code)
EEGNET_SMOKE_PROBA_SHA256 = "adf2cc7d6252d06f2bcd70ce15d14d118a5816061c64e1ec5145f3836e75322c"


def test_param_counts_r8_and_no_conv_bias():
  c, s, e = CompactCNN(), ShallowConvNet(), EEGNetSSVEP()
  assert (count_parameters(c), count_parameters(s), count_parameters(e)) == (56021, 14485, 2349)
  for m, n in ((c, 2), (s, 2)):
    convs = [l for l in m.modules() if isinstance(l, torch.nn.Conv2d)]
    assert len(convs) == n and all(l.bias is None for l in convs)
  assert c.head.in_features == 32 * 256 and s.head.in_features == 40 * 11


def test_compact_kernel_length_fs_label_and_clamp():
  assert temporal_kernel_length(250.0, 8.5714, 256) == 29 and temporal_kernel_length(256.0, 8.5714, 256) == 30
  assert temporal_kernel_length(10.0, 8.5714, 256) == 4  # lower clamp
  assert temporal_kernel_length(5000.0, 8.5714, 256) == 256  # upper clamp to the window
  assert CompactCNN().kernel_length == 29 and CompactCNN(fs=256.0).kernel_length == 30
  assert count_parameters(CompactCNN(fs=256.0)) != 56021  # PF-04: the legacy fs matters for the count


def test_compact_layer_arithmetic():
  m = CompactCNN()
  assert m.spatial.weight.shape == (16, 1, 7, 1) and m.temporal.weight.shape == (32, 16, 1, 29)
  assert m.temporal.padding == (0, 14)
  assert 16 * 7 + 2 * 16 + 32 * 16 * 29 + 2 * 32 + 32 * 256 * 5 + 5 == 56021


def test_shallow_pooling_and_clamps():
  m = ShallowConvNet()
  assert m.pool(torch.zeros(1, 40, 1, 232)).shape[-1] == 11 == (232 - 75) // 15 + 1
  s = ShallowConvNet(n_samples=128)  # 104 after the temporal conv; kernels fit
  assert s(torch.randn(3, 7, 128)).shape == (3, 5)
  t = ShallowConvNet(n_samples=40)  # pool clamped to 16 samples
  assert t.pool_kernel == 16 and t.pool_stride == 15 and t(torch.randn(2, 7, 40)).shape == (2, 5)
  u = ShallowConvNet(n_samples=10)  # temporal kernel clamped to the window
  assert u.kernel_length == 10 and u(torch.randn(2, 7, 10)).shape == (2, 5)


def test_shallow_log_clamp_finite_on_zero_input():
  m = ShallowConvNet().eval()
  x = torch.zeros(2, 7, 256)
  with torch.no_grad():
    feats = m.features(x.unsqueeze(1))
  assert torch.isfinite(feats).all() and torch.isfinite(m(x)).all()
  m.train()
  m(x + 1e-9).sum().backward()
  assert all(p.grad is None or torch.isfinite(p.grad).all() for p in m.parameters())
  assert LOG_EPS == 1e-6


@pytest.mark.parametrize("cls", [CompactCNN, ShallowConvNet])
@pytest.mark.parametrize("C,T", [(7, 256), (8, 256), (7, 128), (7, 512), (5, 256)])
def test_shapes_input_forms_and_gradients(cls, C, T):
  m = cls(n_channels=C, n_samples=T)
  x = torch.randn(4, C, T)
  m.eval()
  assert m(x).shape == (4, 5) and torch.allclose(m(x), m(x.unsqueeze(1)), atol=1e-6)
  m.train()
  m(x).sum().backward()
  assert all(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in m.parameters())


@pytest.mark.parametrize("cls", [CompactCNN, ShallowConvNet])
def test_wrong_layout_rejected_and_channel_order_matters(cls):
  m = cls().eval()
  with pytest.raises(ValueError):
    m(torch.randn(2, 256, 7))
  x = torch.randn(2, 7, 256)
  assert not torch.allclose(m(x), m(x.flip(1)))


def test_eegnet_regression_after_refactor(tmp_path):
  X, y = make_windows(n_trials=4, seed=0)
  r = train_and_eval_eegnet_cv(X, y, epochs=3, device="cpu")
  assert hashlib.sha256(r["proba"].tobytes()).hexdigest() == EEGNET_SMOKE_PROBA_SHA256
  write_subject(tmp_path / "proc", "S03", n_trials=3)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  assert be.main(["--subject", "S03", "--epochs", "2", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
                  "--reports-dir", str(tmp_path / "rep"), "--config", str(cfg)]) == 0
  csv = (tmp_path / "rep" / "eegnet_benchmark_cpu.csv").read_bytes()
  assert hashlib.sha256(csv).hexdigest() == EEGNET_SMOKE_CSV_SHA256


def test_cv_protocol_and_learnable_for_new_networks():
  X, y = make_windows(n_trials=8, seed=0)
  for build, n in ((lambda c, ch, t: CompactCNN(c, ch, t), 56021), (lambda c, ch, t: ShallowConvNet(c, ch, t), 14485)):
    a = train_and_eval_cv(X, y, build, epochs=12, device="cpu", lr=3e-3)
    b = train_and_eval_cv(X, y, build, epochs=12, device="cpu", lr=3e-3)
    assert np.array_equal(a["proba"], b["proba"]) and a["n_params"] == n
    assert len(a["fold_test_acc"]) == 5 and "StratifiedKFold(5, shuffle, 42)" in a["cv"]
    assert a["train_accuracy"] >= a["accuracy"] and a["accuracy"] > 0.4, (a["accuracy"], a["train_accuracy"])


def _run(mod, tmp_path, tag):
  write_subject(tmp_path / "proc", "S03", n_trials=3) if not (tmp_path / "proc").exists() else None
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  rep = tmp_path / f"rep_{tag}"
  assert mod.main(["--subject", "S03", "--epochs", "2", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
                   "--reports-dir", str(rep), "--config", str(cfg)]) == 0
  return rep


@pytest.mark.parametrize("mod,name,params", [(bc, "compact_cnn", 56021), (bs, "shallow_convnet", 14485),
                                             (be, "eegnet", 2349)])
def test_scripts_smoke_columns_and_meta(tmp_path, mod, name, params):
  rep = _run(mod, tmp_path, name)
  df = pd.read_csv(rep / f"{name}_benchmark_cpu.csv")
  assert list(df.columns) == mod.COLUMNS and df.loc[0, "Params"] == params and df.loc[0, "Device"] == "cpu"
  assert df.loc[0, "Clean Windows"] + df.loc[0, "Rejected"] == 75
  meta = (rep / f"{name}_benchmark_cpu.meta.txt").read_text()
  assert "legacy" in meta and "i%5" in meta and "PF-30" in meta
  assert "Data source: legacy windows" in meta and "n_channels (after the gate): S03=7" in meta
  with pytest.raises(SystemExit):
    mod.build_parser().parse_args(["--augment", "on"])


def test_mirror_protocol_identical_across_networks(tmp_path):
  metas = {}
  for mod, name in ((be, "eegnet"), (bc, "compact_cnn"), (bs, "shallow_convnet")):
    rep = _run(mod, tmp_path, name)
    metas[name] = (rep / f"{name}_benchmark_cpu.meta.txt").read_text().splitlines()
  keep = lambda lines: [l for l in lines if l.startswith(("device=", "cv=", "smoothing", "quality gate", "train accuracy"))]
  assert keep(metas["eegnet"]) == keep(metas["compact_cnn"]) == keep(metas["shallow_convnet"]) and len(keep(metas["eegnet"])) == 5
  tr = lambda lines: [l for l in lines if l.startswith("training:")][0].replace(", max-norm 1.0 on the spatial depthwise filters", "")
  assert tr(metas["eegnet"]) == tr(metas["compact_cnn"]) == tr(metas["shallow_convnet"])
  # single code path: the three scripts share the driver and the CV function
  import inspect
  for mod in (be, bc, bs):
    assert "run_benchmark" in inspect.getsource(mod.main)
  assert be.gated_windows is bc.gated_windows is bs.gated_windows


def test_gate_drops_bad_channel_for_all_scripts(tmp_path):
  write_subject(tmp_path / "proc", "S03", bad_channels=("O2",), n_trials=3)
  g = bc.gated_windows(tmp_path / "proc", "S03")
  assert "O2" in g["dropped"] and g["X"].shape[1] == 6 and be.gated_windows(tmp_path / "proc", "S03")["kept"] == g["kept"]


def test_count_parameters_script(tmp_path):
  assert cp.main(["--reports-dir", str(tmp_path)]) == 0
  df = pd.read_csv(tmp_path / "network_parameter_counts.csv")
  assert list(df.columns) == ["Model", "Channels", "Samples", "Params"]
  assert dict(zip(df["Model"], df["Params"])) == {"eegnet": 2349, "shallow_convnet": 14485, "compact_cnn": 56021}
  assert set(df["Channels"]) == {7} and set(df["Samples"]) == {256}
