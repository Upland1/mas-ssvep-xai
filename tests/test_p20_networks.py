"""P20 known-answer tests: CCNN (plan test 4), `fit_network` / `cnn_fold` (plan test 5), NN-sweep helpers.

Synthetic data only. Planted sinusoids at distinct frequencies per class; planted loss curve for the best-state restore.
"""

import numpy as np
import pytest
import torch
from sklearn.model_selection import StratifiedGroupKFold

from src.models.cnn import training as T
from src.models.cnn.ccnn import CCNN
from src.models.cnn.eegnet import count_parameters

FS = 256.0
FREQS = [8.0, 10.0, 12.0, 15.0, 20.0]


def planted(n_trials=30, per_trial=4, C=4, n=256, seed=0, amp=1.0, noise=1.0):
  """Windows `(N, C, n)`, labels 0..4, trial ids; class k = sinusoid at FREQS[k] on every channel + noise."""
  rng = np.random.default_rng(seed)
  t = np.arange(n) / FS
  X, y, g = [], [], []
  for tr in range(n_trials):
    k = tr % 5
    for _ in range(per_trial):
      ph = rng.uniform(0, 2 * np.pi)
      X.append(amp * np.sin(2 * np.pi * FREQS[k] * t + ph)[None, :] + noise * rng.standard_normal((C, n)))
      y.append(k)
      g.append(tr)
  return np.array(X), np.array(y), np.array(g)


def test_ccnn_shape_nfft_bins_and_params():
  for C, n in [(7, 256), (8, 128), (8, 1024)]:
    m = CCNN(5, C, n, fs=FS)
    assert m.nfft == max(n, int(FS / 0.25)) == 1024
    assert m.bins_hz.min() >= 3.0 and m.bins_hz.max() <= 50.0
    assert m.bins_hz.min() < 3.0 + 0.25 and m.bins_hz.max() > 50.0 - 0.25  # span the whole band
    assert m.n_bins == 189  # 3.00 .. 50.00 Hz step 0.25
    out = m(torch.randn(3, C, n))
    assert out.shape == (3, 5)
    F = 2 * C
    expected = 2 * F * C + 2 * F + F * F * 10 + 2 * F + F * (189 - 10 + 1) * 5 + 5  # bias-free convs (B004)
    assert count_parameters(m) == expected
  assert CCNN(5, 8, 256, fs=FS).spectral[0].kernel_size == (1, 10)


def test_ccnn_nfft_follows_window_longer_than_resolution():
  m = CCNN(5, 8, 2048, fs=FS)  # 8 s window > fs/resolution
  assert m.nfft == 2048 and m.bins_hz[1] - m.bins_hz[0] == pytest.approx(FS / 2048)


def test_ccnn_spectrum_known_answer():
  """A cosine of amplitude A at an on-grid frequency gives real part A/2 at that bin (divided by T), imag 0."""
  n, f, A = 256, 12.0, 3.0
  t = np.arange(n) / FS
  x = torch.tensor(A * np.cos(2 * np.pi * f * t), dtype=torch.float32).view(1, 1, n).repeat(1, 4, 1)
  m = CCNN(5, 4, n, fs=FS)
  s = m.spectrum(x)  # (1, 2, 4, bins)
  j = int(np.argmin(np.abs(m.bins_hz - f)))
  assert m.bins_hz[j] == pytest.approx(f)
  assert s.shape == (1, 2, 4, m.n_bins)
  assert s[0, 0, 0].argmax().item() == j
  assert s[0, 0, 0, j].item() == pytest.approx(A / 2, rel=1e-4)
  assert abs(s[0, 1, 0, j].item()) < 1e-4


def test_ccnn_rejects_wrong_shape():
  with pytest.raises(ValueError):
    CCNN(5, 4, 256, fs=FS)(torch.zeros(2, 5, 256))


def test_param_counts_pf31_compact_eegnet_8ch():
  """PF-31: compact_eegnet = 28,229 parameters at 8 channels, 1 s, fs 256, 5 classes; eegnet has bias-free convs."""
  assert count_parameters(T.model_factory("compact_eegnet", FS)(5, 8, 256)) == 28229
  assert count_parameters(T.model_factory("compact", FS)(5, 8, 256)) == 28229  # alias
  assert count_parameters(T.model_factory("eegnet", FS)(5, 8, 256)) == 2389
  with pytest.raises(ValueError):
    T.model_factory("compact_cnn", FS)


def test_cnn_fold_learns_planted_sinusoids_cpu():
  X, y, g = planted(n_trials=40, C=4)
  tr = g < 30
  r = T.cnn_fold(X[tr], y[tr], g[tr], X[~tr], FS, 5, model="ccnn", seed=1, device="cpu", augment=True, max_epochs=12)
  acc = float(np.mean(r["proba"].argmax(1) == y[~tr]))
  assert acc > 0.6, acc  # chance 0.2
  assert r["train_acc"] > 0.6 and 1 <= r["best_epoch"] <= 12
  assert r["proba"].shape == (int((~tr).sum()), 5) and np.allclose(r["proba"].sum(1), 1.0, atol=1e-5)
  assert set(r) >= {"proba", "train_acc", "val_acc", "best_epoch"}


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA")
@pytest.mark.parametrize("model", ["ccnn", "compact_eegnet", "eegnet"])
def test_cnn_fold_runs_on_cuda(model):
  X, y, g = planted(n_trials=20, C=4)
  tr = g < 15
  r = T.cnn_fold(X[tr], y[tr], g[tr], X[~tr], FS, 5, model=model, seed=1, device="cuda", max_epochs=2)
  assert r["proba"].shape == (int((~tr).sum()), 5)


@pytest.mark.parametrize("model", ["ccnn", "compact_eegnet", "eegnet"])
def test_every_model_runs_cpu_all_window_lengths(model):
  for n in (128, 256, 512):
    X, y, g = planted(n_trials=25, per_trial=2, C=3, n=n)
    r = T.fit_network(X, y, g, T.model_factory(model, FS), seed=0, device="cpu", max_epochs=1)
    assert 0.0 <= r["train_acc"] <= 1.0


def test_validation_is_subset_of_training_trials_and_disjoint_from_test():
  """PF-32: the early-stopping split is made inside the training trials; the test trials never reach `fit_network`."""
  X, y, g = planted(n_trials=50, C=3)
  sgk = StratifiedGroupKFold(5, shuffle=True, random_state=42)
  tr, te = next(iter(sgk.split(X, y, g)))
  seen = {}
  orig = T.fit_network

  def spy(Xa, ya, ga, *a, **k):
    seen["groups"] = set(np.asarray(ga))
    return orig(Xa, ya, ga, *a, **k)

  T.fit_network, saved = spy, T.fit_network
  try:
    T.cnn_fold(X[tr], y[tr], g[tr], X[te], FS, 5, model="eegnet", seed=3, max_epochs=1)
  finally:
    T.fit_network = saved
  assert seen["groups"] == set(g[tr]) and not (seen["groups"] & set(g[te]))
  r = T.fit_network(X[tr], y[tr], g[tr], T.model_factory("eegnet", FS), seed=3, max_epochs=1)
  gv, gf = set(g[tr][r["val_idx"]]), set(g[tr][r["fit_idx"]])
  assert gv <= set(g[tr]) and not (gv & set(g[te]))
  assert not (gv & gf)  # whole trials: no trial in both fitting and validation windows
  assert len(r["val_idx"]) + len(r["fit_idx"]) == len(tr)
  assert 0.1 < len(r["val_idx"]) / len(tr) < 0.3  # ~20 %
  # R2: normalisation statistics come from the fitting windows only
  assert np.allclose(r["mean"], X[tr][r["fit_idx"]].mean(axis=(0, 2), keepdims=True))


def test_best_validation_state_is_restored(monkeypatch):
  """Planted validation-loss curve [3, 2, 1, 2, 3, 4 ...]: best epoch 3, patience 3 stops at epoch 6, epoch-3 weights restored."""
  X, y, g = planted(n_trials=20, C=3)
  curve = [3.0, 2.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
  snaps, calls = [], {"n": 0}
  real = T._loss_acc

  def fake(model, Xv, yv, dev):
    calls["n"] += 1
    if calls["n"] <= 6:  # the 6 per-epoch validation calls
      snaps.append({k: v.detach().clone() for k, v in model.state_dict().items()})
      return curve[calls["n"] - 1], 0.5
    return real(model, Xv, yv, dev)

  monkeypatch.setattr(T, "_loss_acc", fake)
  r = T.fit_network(X, y, g, T.model_factory("eegnet", FS), seed=0, max_epochs=8, patience=3)
  assert r["best_epoch"] == 3 and r["epochs_run"] == 6
  for k, v in r["model"].state_dict().items():
    assert torch.equal(v, snaps[2][k]), k
  assert not torch.equal(r["model"].state_dict()["head.weight"], snaps[5]["head.weight"])


def test_cnn_fold_rejects_labels_out_of_range():
  X, y, g = planted(n_trials=10, C=3)
  with pytest.raises(ValueError):
    T.cnn_fold(X, y + 1, g, X[:3], FS, 5)


def test_no_augment_flag_changes_training_not_split():
  X, y, g = planted(n_trials=20, C=3)
  a = T.fit_network(X, y, g, T.model_factory("eegnet", FS), seed=0, augment=True, max_epochs=2)
  b = T.fit_network(X, y, g, T.model_factory("eegnet", FS), seed=0, augment=False, max_epochs=2)
  assert np.array_equal(a["val_idx"], b["val_idx"])


def test_itr_known_values():
  from scripts.benchmarks.neural_networks.benchmark_nn_sweep import itr_bits_per_min, folder_name
  assert itr_bits_per_min(1.0, 5, 1.5) == pytest.approx(np.log2(5) * 60 / 1.5)
  assert itr_bits_per_min(0.2, 5, 1.5) == 0.0 and itr_bits_per_min(0.1, 5, 1.5) == 0.0
  assert folder_name(0.5, 0.25) == "w0.5_s0.25" and folder_name(1.0, 0.25) == "w1_s0.25"


def test_nn_sweep_cli_synthetic(tmp_path, capsys):
  from scripts.benchmarks.neural_networks import benchmark_nn_sweep as B
  from tests import p16_synth as S
  S.write_built_subject(tmp_path / "w1_s0.25", "S01", n_trials=20)
  rc = B.main(["--data-root", str(tmp_path), "--windows", "1", "--models", "ccnn", "compact", "eegnet",
               "--max-epochs", "1", "--max-folds", "2", "--device", "cpu", "--out-dir", str(tmp_path / "out")])
  assert rc == 0
  import pandas as pd
  df = pd.read_csv(tmp_path / "out" / "summary.csv")
  assert list(df["Method"]) == ["ccnn", "compact_eegnet", "eegnet"]
  assert {"Val Acc (%)", "Best Epoch", "Train Acc (%)", "ITR (bits/min)"} <= set(df.columns)
  pr = pd.read_csv(tmp_path / "out" / "predictions.csv")
  assert {"trial_id", "offset_sec", "p_101", "p_105"} <= set(pr.columns)


def test_nn_sweep_offset_sec_is_in_seconds(tmp_path):
  """Built folders store window offsets in samples (multiples of fs/4 here); predictions.csv must give seconds."""
  import pandas as pd
  from scripts.benchmarks.neural_networks import benchmark_nn_sweep as B
  from src.io.subject_data import load_subject
  from tests import p16_synth as S
  S.write_built_subject(tmp_path / "w1_s0.25", "S01", n_trials=20)
  d = load_subject(tmp_path / "w1_s0.25" / "S01", quality_mode="shared")
  assert np.asarray(d["offsets"]).max() > 100  # samples
  assert B.main(["--data-root", str(tmp_path), "--windows", "1", "--models", "eegnet", "--max-epochs", "1",
                 "--max-folds", "1", "--device", "cpu", "--out-dir", str(tmp_path / "out")]) == 0
  pr = pd.read_csv(tmp_path / "out" / "predictions.csv")
  assert pr["offset_sec"].max() <= 5.0
  assert set(np.round(pr["offset_sec"], 6)) <= set(np.round(np.unique(d["offsets"]) / d["fs"], 6))
