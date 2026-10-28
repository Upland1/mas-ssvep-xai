"""P10 tests (deep-learning): augmentation functions with known answers, dataset order / probability / same-class /
dtype, fold scope and identical initial weights OFF vs ON (PF-28/PF-29/PF-30), determinism, OFF regression against
the P09 hashes, and the A/B script on a synthetic legacy tree. Synthetic data only, fixed seeds, CPU."""

import numpy as np
import pandas as pd
import pytest
import torch
from scipy import stats

from scripts.benchmarks.neural_networks import benchmark_eegnet as be
from scripts.benchmarks.neural_networks import benchmark_nn_augmentation as ab
from src.models.cnn import eegnet_cv
from src.models.cnn.eegnet_cv import train_and_eval_cv, train_and_eval_eegnet_cv, zscore_windows
from src.preprocessing.dataset import augmentation as aug
from src.preprocessing.dataset.augmentation import (
  SSVEPAugmentedDataset, add_gaussian_noise, mixup_intra_class, scale_amplitude, time_shift)
from tests.p05_synth import make_windows, write_subject
from tests.test_p09_compact_shallow import assert_eegnet_smoke_proba, single_thread


def test_noise_proportional_to_channel_std():
  rng = np.random.default_rng(0)
  base = rng.standard_normal((2, 4096))
  w = base * np.array([[1.0], [10.0]])
  diff = np.stack([add_gaussian_noise(w, 0.05, np.random.default_rng(i)) - w for i in range(200)])
  expected = 0.05 * w.std(axis=-1)
  assert np.allclose(diff.std(axis=(0, 2)), expected, rtol=0.1)
  assert abs(diff.mean()) < 0.05


def test_scale_one_factor_per_window():
  w = np.random.default_rng(1).standard_normal((7, 64))
  ks = []
  for i in range(50):
    out = scale_amplitude(w, (0.9, 1.1), np.random.default_rng(i))
    k = out[0, 0] / w[0, 0]
    assert np.allclose(out, k * w, atol=1e-12) and 0.9 <= k <= 1.1
    ks.append(k)
  assert np.ptp(ks) > 0.05


def test_shift_is_integer_circular_roll_within_bound():
  T = 100
  w = np.tile(np.arange(T, dtype=float), (3, 1))
  seen = set()
  for i in range(300):
    out = time_shift(w, 0.1, np.random.default_rng(i))
    s = next(k for k in range(-10, 11) if np.array_equal(out, np.roll(w, k, axis=-1)))
    seen.add(s)
  assert seen == set(range(-10, 11))  # every shift in [-10, 10] reached, none outside


def test_mixup_lambda_folded_beta_and_formula():
  a, b = np.ones((2, 8)), np.zeros((2, 8))
  lams = np.array([mixup_intra_class(a, b, 0.4, np.random.default_rng(i))[0, 0] for i in range(2000)])
  assert lams.min() >= 0.5
  ref = np.random.default_rng(123).beta(0.4, 0.4, 2000)
  ref = np.maximum(ref, 1 - ref)
  assert stats.ks_2samp(lams, ref).pvalue > 0.01
  x, z = np.random.default_rng(0).standard_normal((2, 16)), np.random.default_rng(1).standard_normal((2, 16))
  lam = np.random.default_rng(5).beta(0.4, 0.4)
  lam = max(lam, 1 - lam)
  assert np.allclose(mixup_intra_class(x, z, 0.4, np.random.default_rng(5)), lam * x + (1 - lam) * z, atol=1e-12)


def _planted(n=60, C=3, T=32):
  """Each class has a distinct constant level, so a mixed window's value reveals which classes were blended."""
  y = np.repeat(np.arange(5), n // 5)
  X = np.tile((y * 10.0)[:, None, None], (1, C, T)) + np.random.default_rng(0).standard_normal((n, C, T)) * 1e-3
  return X.astype(np.float32), y


def test_mixup_partner_always_same_class(monkeypatch):
  X, y = _planted()
  partners = []
  orig = aug.mixup_intra_class

  def spy(a, b, alpha=0.4, rng=None):
    partners.append((a.mean(), b.mean()))
    return orig(a, b, alpha, rng)

  monkeypatch.setattr(aug, "mixup_intra_class", spy)
  ds = SSVEPAugmentedDataset(X, y, p_noise=0, p_scale=0, p_shift=0, p_mixup=1.0, seed=3)
  for i in range(len(ds)):
    ds[i]
  assert len(partners) == len(ds)
  assert all(abs(a - b) < 0.1 for a, b in partners)  # same level == same class (levels differ by 10)


def test_cross_class_mixup_would_be_caught():
  """Negative control: a partner pool drawn from all windows (the PF-29 bug) breaks the same-class property."""
  X, y = _planted()
  ds = SSVEPAugmentedDataset(X, y, p_noise=0, p_scale=0, p_shift=0, p_mixup=1.0, seed=3)
  ds.class_idx = {c: np.arange(len(y)) for c in ds.class_idx}
  gaps = [abs(ds.X[i].mean() - ds.augment(i).mean()) for i in range(len(ds))]
  assert max(gaps) > 1.0


def test_order_and_probability(monkeypatch):
  X, y = _planted(n=100)
  log = []
  for name in ("add_gaussian_noise", "scale_amplitude", "time_shift"):
    orig = getattr(aug, name)
    monkeypatch.setattr(aug, name, (lambda o, n: lambda w, *a, **k: (log.append(n), o(w, *a, **k))[1])(orig, name))
  om = aug.mixup_intra_class
  monkeypatch.setattr(aug, "mixup_intra_class", lambda *a, **k: (log.append("mixup"), om(*a, **k))[1])
  ds = SSVEPAugmentedDataset(X, y, seed=0)
  per_item, N = [], 4000
  for i in range(N):
    log.clear()
    ds[i % len(ds)]
    per_item.append(list(log))
  rank = {"mixup": 0, "scale_amplitude": 1, "time_shift": 2, "add_gaussian_noise": 3}
  assert all([rank[o] for o in p] == sorted(rank[o] for o in p) for p in per_item)
  for op in rank:
    k = sum(op in p for p in per_item)
    assert abs(k - N / 2) < 3 * np.sqrt(N / 4), (op, k)


def test_dtypes_and_lengths():
  X, y = _planted()
  ds = SSVEPAugmentedDataset(X.astype(np.float64), y, seed=0)
  x, t = ds[0]
  assert len(ds) == 60 and x.dtype == torch.float32 and t.dtype == torch.long and x.shape == (3, 32) and int(t) == 0
  assert ds.rng is not None and all(len(v) == 12 for v in ds.class_idx.values())


def test_dataset_does_not_touch_torch_rng_and_is_deterministic():
  X, y = _planted()
  torch.manual_seed(5)
  before = torch.get_rng_state()
  ds = SSVEPAugmentedDataset(X, y, seed=9)
  a = [ds[i][0].numpy() for i in range(20)]
  assert torch.equal(before, torch.get_rng_state())
  ds2 = SSVEPAugmentedDataset(X, y, seed=9)
  assert all(np.array_equal(u, ds2[i][0].numpy()) for i, u in enumerate(a))


def _spy_training(monkeypatch):
  """Record, per fold, the initial weights and the arrays seen by DataLoader (training) and predict_proba (eval)."""
  rec = {"init": [], "loader": [], "eval": []}
  orig_train = eegnet_cv.train_model
  orig_pred = eegnet_cv.predict_proba
  DL = eegnet_cv.DataLoader

  def dl(ds, **kw):
    rec["loader"].append(type(ds).__name__)
    return DL(ds, **kw)

  def pred(model, X, device, chunk=256):
    rec["eval"].append(np.asarray(X).copy())
    return orig_pred(model, X, device, chunk)

  def build_spy(n_classes, n_channels, n_samples):
    m = eegnet_cv.build_eegnet(n_classes, n_channels, n_samples)
    rec["init"].append([p.detach().clone() for p in m.parameters()])
    return m

  monkeypatch.setattr(eegnet_cv, "DataLoader", dl)
  monkeypatch.setattr(eegnet_cv, "predict_proba", pred)
  return rec, build_spy


def test_fold_scope_and_same_init_off_vs_on(monkeypatch):
  X, y = make_windows(n_trials=4, seed=0)
  recs = {}
  for arm in (False, True):
    rec, build = _spy_training(monkeypatch)
    train_and_eval_cv(X, y, build, epochs=2, device="cpu", augment=arm, cv="legacy")
    recs[arm] = rec
    monkeypatch.undo()
  off, on = recs[False], recs[True]
  assert set(off["loader"]) == {"TensorDataset"} and set(on["loader"]) == {"SSVEPAugmentedDataset"}
  assert len(off["init"]) == len(on["init"]) == 5
  for po, pn in zip(off["init"], on["init"]):  # PF-28: identical weights before epoch 1
    assert all(torch.equal(a, b) for a, b in zip(po, pn))
  assert len(off["eval"]) == len(on["eval"]) == 10  # test pass + un-augmented train pass per fold
  assert all(np.array_equal(a, b) for a, b in zip(off["eval"], on["eval"]))  # PF-29/PF-30: eval inputs untouched
  Xz = zscore_windows(X)
  rows = {r.tobytes() for r in Xz}  # every evaluated row is an exact z-scored window: nothing augmented
  assert all(r.tobytes() in rows for e in on["eval"] for r in e)


def test_augmentation_changes_training_only_and_is_deterministic():
  X, y = make_windows(n_trials=4, seed=0)
  off = train_and_eval_cv(X, y, epochs=3, device="cpu", cv="legacy")
  on1 = train_and_eval_cv(X, y, epochs=3, device="cpu", augment=True, cv="legacy")
  on2 = train_and_eval_cv(X, y, epochs=3, device="cpu", augment=True, cv="legacy")
  assert np.array_equal(on1["proba"], on2["proba"]) and not np.array_equal(on1["proba"], off["proba"])
  assert on1["n_params"] == off["n_params"] and len(on1["fold_train_acc"]) == 5


def test_off_path_identical_to_p09():
  X, y = make_windows(n_trials=4, seed=0)
  with single_thread():
    r = train_and_eval_eegnet_cv(X, y, epochs=3, device="cpu", cv="legacy")
    assert_eegnet_smoke_proba(r["proba"])
    r2 = train_and_eval_cv(X, y, eegnet_cv.build_eegnet, epochs=3, device="cpu", augment=False, cv="legacy")
  assert np.array_equal(r["proba"], r2["proba"])


def _tree(tmp_path, subjects=("S01", "S02"), n_trials=3):
  for s in subjects:
    write_subject(tmp_path / "proc", s, n_trials=n_trials)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  return ["--epochs", "2", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
          "--reports-dir", str(tmp_path / "rep"), "--config", str(cfg), "--cv", "legacy", "--smoothing", "mod5"]


def test_driver_augment_on_flag_and_file_names(tmp_path):
  argv = _tree(tmp_path, ("S03",))
  assert be.main(["--subject", "S03", "--augment", "on", *argv]) == 0
  assert (tmp_path / "rep" / "legacy_leaky" / "eegnet_aug_benchmark_cpu.csv").is_file()
  assert "augment=on" in (tmp_path / "rep" / "legacy_leaky" / "eegnet_aug_benchmark_cpu.meta.txt").read_text()


def test_ab_script_schema_deltas_mean_freeze_and_warning(tmp_path, capsys):
  argv = _tree(tmp_path)
  assert ab.main(["--model", "shallow_convnet", "--freeze-legacy", *argv]) == 0
  out = capsys.readouterr().out
  csv = tmp_path / "rep" / "legacy_leaky" / "augmentation_ab_shallow_conv_net.csv"
  df = pd.read_csv(csv)
  assert list(df.columns) == ab.COLUMNS and list(df["Subject"]) == ["S01", "S02", "Mean"]
  body = df.iloc[:2]
  assert np.allclose(body["1.0s Delta"], body["1.0s ON (%)"] - body["1.0s OFF (%)"], atol=0.011)
  assert np.allclose(body["2.0s Delta"], body["2.0s ON (%)"] - body["2.0s OFF (%)"], atol=0.011)
  assert np.isclose(df.iloc[2]["1.0s OFF (%)"], body["1.0s OFF (%)"].mean(), atol=0.011)
  frozen = csv  # --cv legacy writes under legacy_leaky/ directly; --freeze-legacy is redundant there (P11)
  assert frozen.read_bytes() == csv.read_bytes() and frozen.with_suffix(".meta.txt").is_file()
  assert "legacy" in csv.with_suffix(".meta.txt").read_text() and "OFF then ON" in out
  assert out.count("augment OFF") == 2 and out.count("augment ON") == 2


def test_warning_when_off_train_below_40(tmp_path, capsys, monkeypatch):
  argv = _tree(tmp_path, ("S01",))
  real = ab.train_and_eval_cv

  def forced(*a, **k):
    r = real(*a, **k)
    r["train_accuracy"] = 0.30 if not k.get("augment") else 0.9
    return r

  monkeypatch.setattr(ab, "train_and_eval_cv", forced)
  assert ab.main(["--model", "eegnet", *argv]) == 0
  assert "WARNING S01: OFF train accuracy 30.00% < 40%" in capsys.readouterr().out
  monkeypatch.setattr(ab, "train_and_eval_cv", lambda *a, **k: {**real(*a, **k), "train_accuracy": 0.9})
  assert ab.main(["--model", "eegnet", *argv]) == 0
  assert "WARNING" not in capsys.readouterr().out
