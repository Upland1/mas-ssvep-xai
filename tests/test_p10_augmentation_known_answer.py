"""P10 independent known-answer tests (synthetic-tester): augmentation ops, dataset, fold scope, A/B script.

Expected values come from the roadmap (P10.1) and analytic reasoning, not from the implementation: Var(added noise)
= (0.05 sigma_c)^2, one scale factor per window, circular integer roll <= floor(0.1 T), lambda ~ folded Beta(0.4, 0.4),
P(op applied) = 0.5, order mixup -> scale -> shift -> noise. Synthetic data only, fixed seeds, CPU."""

import numpy as np
import pandas as pd
import pytest
import torch
from scipy import integrate, stats

from scripts.benchmarks.neural_networks import benchmark_nn_augmentation as ab
from src.models.cnn import eegnet_cv
from src.models.cnn.eegnet_cv import train_and_eval_cv
from src.preprocessing.dataset import augmentation as aug
from src.preprocessing.dataset.augmentation import (
  SSVEPAugmentedDataset, add_gaussian_noise, mixup_intra_class, scale_amplitude, time_shift)
from tests.p05_synth import make_windows, write_subject


def test_noise_variance_is_per_channel_fraction_of_that_channels_std():
  """Var(added noise_c) = (0.05 sigma_c)^2 with sigma_c the window's own channel std (channel stds 1, 7, 40).
  Tolerance 8 % on the std over 400 draws x 2048 samples; the ratio between channels must follow sigma_c
  (a single global std would give ratio 1 or a constant noise level)."""
  rng = np.random.default_rng(10)
  sig = np.array([1.0, 7.0, 40.0])
  w = rng.standard_normal((3, 2048)) * sig[:, None] + np.array([[0.0], [5.0], [-100.0]])  # offsets must not matter
  d = np.stack([add_gaussian_noise(w, 0.05, np.random.default_rng(i)) - w for i in range(400)])
  got = d.std(axis=(0, 2))
  want = 0.05 * w.std(axis=-1)
  assert np.allclose(got, want, rtol=0.08)
  assert got[2] / got[0] == pytest.approx(want[2] / want[0], rel=0.1)
  assert np.allclose(np.corrcoef(d[:, 0, :].ravel(), d[:, 1, :].ravel())[0, 1], 0, atol=0.01)  # independent channels


def test_noise_std_frac_zero_is_identity_and_input_not_mutated():
  w = np.random.default_rng(0).standard_normal((2, 50))
  w0 = w.copy()
  assert np.array_equal(add_gaussian_noise(w, 0.0, np.random.default_rng(1)), w0)
  add_gaussian_noise(w, 0.5, np.random.default_rng(1))
  scale_amplitude(w, rng=np.random.default_rng(1))
  time_shift(w, rng=np.random.default_rng(1))
  mixup_intra_class(w, w0 * 2, rng=np.random.default_rng(1))
  assert np.array_equal(w, w0)


def test_scale_factor_shared_across_channels_and_uniform_on_range():
  """Per window: out/in identical for all channels (1e-12). Over 3000 draws k ~ U(0.9, 1.1): KS p > 0.01, mean 1.0.
  A per-channel factor makes the channel ratios differ."""
  w = np.random.default_rng(2).standard_normal((8, 40)) + 3.0
  ks = []
  for i in range(3000):
    ratio = scale_amplitude(w, (0.9, 1.1), np.random.default_rng(i)) / w
    assert np.ptp(ratio) < 1e-12
    ks.append(ratio[0, 0])
  assert stats.kstest(ks, stats.uniform(0.9, 0.2).cdf).pvalue > 0.01
  assert min(ks) >= 0.9 and max(ks) <= 1.1


def test_shift_is_circular_not_padded_and_bounded_for_non_round_T():
  """T = 205 -> max shift floor(20.5) = 20. Rolled window keeps the multiset of samples (a zero-padded shift loses
  them), equals np.roll by some k in [-20, 20], both signs and 0 occur, |k| = 21 never."""
  T = 205
  w = np.tile(np.arange(1, T + 1, dtype=float), (2, 1))
  ks = []
  for i in range(2000):
    out = time_shift(w, 0.1, np.random.default_rng(i))
    assert np.array_equal(np.sort(out[0]), w[0])
    k = int(np.argmax(out[0] == 1.0))  # position of the original first sample == the roll
    k = k if k <= 20 else k - T
    assert np.array_equal(out, np.roll(w, k, axis=-1)) and abs(k) <= 20
    ks.append(k)
  assert min(ks) == -20 and max(ks) == 20 and 0 in ks


def test_mixup_fold_mean_matches_analytic_and_never_below_half():
  """E[max(L, 1-L)], L ~ Beta(0.4, 0.4), by numerical integration; the sample mean of lambda over 20000 draws agrees
  within 0.005. lambda < 0.5 is impossible; a == b returns a exactly; output lies between a and b."""
  f = lambda x: max(x, 1 - x) * stats.beta(0.4, 0.4).pdf(x)  # noqa: E731
  expect = integrate.quad(f, 0, 0.5)[0] + integrate.quad(f, 0.5, 1)[0]
  a, b = np.full((1, 4), 1.0), np.zeros((1, 4))
  lam = np.array([mixup_intra_class(a, b, 0.4, np.random.default_rng(i))[0, 0] for i in range(20000)])
  assert lam.min() >= 0.5 and lam.max() <= 1.0
  assert lam.mean() == pytest.approx(expect, abs=0.005)
  assert (lam > 0.95).mean() > 0.2  # U-shaped Beta(0.4, 0.4): much mass near the anchor
  x = np.random.default_rng(3).standard_normal((2, 9))
  assert np.allclose(mixup_intra_class(x, x, 0.4, np.random.default_rng(0)), x, atol=1e-12)


def _planted(n=100, C=3, T=64):
  y = np.repeat(np.arange(5), n // 5)
  X = np.tile((y * 10.0)[:, None, None], (1, C, T)) + np.random.default_rng(0).standard_normal((n, C, T)) * 1e-3
  return X.astype(np.float32), y


def test_dataset_op_order_and_independent_probabilities(monkeypatch):
  """With p = 1 for all, the call sequence is exactly mixup, scale, shift, noise. With p = 0 the output equals the
  input (float32 cast). With default p, each op occurs with frequency 0.5 (binomial 3 sigma) and ops are
  independent: P(mixup and noise) = 0.25 (3 sigma)."""
  X, y = _planted()
  log = []

  def wrap(name):
    orig = getattr(aug, name)
    monkeypatch.setattr(aug, name, lambda *a, **k: (log.append(name), orig(*a, **k))[1])

  for n in ("mixup_intra_class", "scale_amplitude", "time_shift", "add_gaussian_noise"):
    wrap(n)
  ds = SSVEPAugmentedDataset(X, y, p_noise=1, p_scale=1, p_shift=1, p_mixup=1, seed=0)
  ds[0]
  assert log == ["mixup_intra_class", "scale_amplitude", "time_shift", "add_gaussian_noise"]
  log.clear()
  ds0 = SSVEPAugmentedDataset(X, y, p_noise=0, p_scale=0, p_shift=0, p_mixup=0, seed=0)
  for i in range(len(y)):
    assert np.array_equal(ds0[i][0].numpy(), X[i]) and int(ds0[i][1]) == y[i]
  assert log == []
  ds = SSVEPAugmentedDataset(X, y, seed=1)
  N, seqs = 3000, []
  for i in range(N):
    log.clear()
    ds[i % len(y)]
    seqs.append(tuple(log))
  sd = 3 * np.sqrt(N * 0.25)
  for n in ("mixup_intra_class", "scale_amplitude", "time_shift", "add_gaussian_noise"):
    assert abs(sum(n in s for s in seqs) - N / 2) < sd, n
  both = sum("mixup_intra_class" in s and "add_gaussian_noise" in s for s in seqs)
  assert abs(both - N / 4) < 3 * np.sqrt(N * 0.1875)


def test_dataset_does_not_mutate_stored_windows_and_label_is_anchor_label():
  X, y = _planted()
  ds = SSVEPAugmentedDataset(X, y, p_noise=1, p_scale=1, p_shift=1, p_mixup=1, seed=4)
  before = ds.X.copy()
  for _ in range(3):
    for i in range(len(y)):
      assert int(ds[i][1]) == y[i]
  assert np.array_equal(ds.X, before) and np.array_equal(before, X)


def test_dataset_mixup_only_output_is_convex_combination_within_class():
  """p_mixup = 1 only: planted class levels differ by 10, so the output mean must stay within 0.01 of the anchor's
  level (partner of the same class, any lambda) for every anchor; cross-class partners would shift it by >= 2.5."""
  X, y = _planted()
  ds = SSVEPAugmentedDataset(X, y, p_noise=0, p_scale=0, p_shift=0, p_mixup=1, seed=8)
  for r in range(5):
    for i in range(len(y)):
      assert abs(ds[i][0].numpy().mean() - 10.0 * y[i]) < 0.01


class _Marker(SSVEPAugmentedDataset):
  """Augmentation replaced by a huge offset so any leak into an evaluation pass is unmistakable."""

  def augment(self, i):
    return self.X[i].astype(np.float64) + 1000.0


def test_marker_augmentation_reaches_training_batches_only(monkeypatch):
  """ON: training batches carry the marker (augmentation is not a no-op), the test-fold pass and the train-accuracy
  pass (both predict_proba calls) never do (PF-29/PF-30); OFF: no batch carries it."""
  X, y = make_windows(n_trials=4, seed=1)
  seen = {"batch_max": [], "eval_max": []}
  DL, pp = eegnet_cv.DataLoader, eegnet_cv.predict_proba

  def dl(ds, **kw):
    for bx, _ in DL(ds, batch_size=32):
      seen["batch_max"].append(float(bx.abs().max()))
    return DL(ds, **kw)

  def pred(model, Xe, device, chunk=256):
    seen["eval_max"].append(float(np.abs(Xe).max()))
    return pp(model, Xe, device, chunk)

  monkeypatch.setattr(eegnet_cv, "DataLoader", dl)
  monkeypatch.setattr(eegnet_cv, "predict_proba", pred)
  train_and_eval_cv(X, y, epochs=1, device="cpu", augment=False)
  assert max(seen["batch_max"]) < 50 and len(seen["eval_max"]) == 10
  seen["batch_max"].clear(), seen["eval_max"].clear()
  monkeypatch.setattr(eegnet_cv, "SSVEPAugmentedDataset", _Marker)
  train_and_eval_cv(X, y, epochs=1, device="cpu", augment=True)
  assert min(seen["batch_max"]) > 900 and len(seen["batch_max"]) >= 5
  assert len(seen["eval_max"]) == 10 and max(seen["eval_max"]) < 50


def test_augment_seed_is_42_plus_fold_and_train_model_seeds_torch_first(monkeypatch):
  """ON passes seed+fold to the dataset (fold 0..4 -> 42..46) and the dataset construction leaves the torch RNG
  untouched (so initial weights equal the OFF arm's)."""
  X, y = make_windows(n_trials=4, seed=2)
  seeds, states = [], []
  orig_init = SSVEPAugmentedDataset.__init__

  def init(self, Xa, ya, *a, **k):
    states.append(torch.get_rng_state().clone())
    orig_init(self, Xa, ya, *a, **k)
    states.append(torch.get_rng_state().clone())
    seeds.append(k.get("seed", a[4] if len(a) > 4 else None))

  monkeypatch.setattr(SSVEPAugmentedDataset, "__init__", init)
  train_and_eval_cv(X, y, epochs=1, device="cpu", augment=True)
  assert seeds == [42, 43, 44, 45, 46]
  assert all(torch.equal(states[2 * i], states[2 * i + 1]) for i in range(5))


# ---------------------------------------------------------------- A/B script with a stubbed trainer (no training)

def _tree(tmp_path, subjects):
  for s in subjects:
    write_subject(tmp_path / "proc", s, n_trials=3)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  return ["--epochs", "1", "--device", "cpu", "--data-root", str(tmp_path / "proc"),
          "--reports-dir", str(tmp_path / "rep"), "--config", str(cfg)]


def _stub(monkeypatch, table):
  """table[(call_index)] -> (acc, smoothed, train); calls are S01 OFF, S01 ON, S02 OFF, S02 ON, ..."""
  calls = []

  def fake(X, y, build, epochs, bs, lr, dev, seed, verbose=False, augment=False):
    i = len(calls)
    calls.append({"augment": augment, "seed": seed, "X": X, "y": y, "epochs": epochs})
    a, s, t = table[i]
    return {"accuracy": a, "smoothed_accuracy": s, "train_accuracy": t}

  monkeypatch.setattr(ab, "train_and_eval_cv", fake)
  return calls


TABLE = [(0.50, 0.60, 0.95), (0.40, 0.70, 0.99),   # S01: 1.0 s regresses, 2.0 s improves
         (0.2, 0.25, 0.30), (0.2625, 0.3, 0.80)]   # S02: OFF train 30 % -> warning


def test_ab_script_values_deltas_arm_order_columns_and_freeze(tmp_path, monkeypatch, capsys):
  """Stubbed trainer: Delta = ON - OFF (sign kept: S01 1.0 s = -10.00), train columns not swapped, Mean row =
  unweighted column mean, OFF called before ON with identical data/seed, frozen copy byte-identical."""
  argv = _tree(tmp_path, ("S01", "S02"))
  calls = _stub(monkeypatch, TABLE)
  assert ab.main(["--model", "eegnet", "--freeze-legacy", *argv]) == 0
  out = capsys.readouterr().out
  assert [c["augment"] for c in calls] == [False, True, False, True]
  assert all(np.array_equal(calls[2 * i]["X"], calls[2 * i + 1]["X"]) and calls[2 * i]["seed"] == calls[2 * i + 1]["seed"]
             for i in range(2))
  csv = tmp_path / "rep" / "augmentation_ab_eegnet.csv"
  df = pd.read_csv(csv)
  s1 = df.iloc[0]
  assert (s1["1.0s OFF (%)"], s1["1.0s ON (%)"], s1["1.0s Delta"]) == (50.0, 40.0, -10.0)
  assert (s1["2.0s OFF (%)"], s1["2.0s ON (%)"], s1["2.0s Delta"]) == (60.0, 70.0, 10.0)
  assert (s1["Train Acc OFF (%)"], s1["Train Acc ON (%)"]) == (95.0, 99.0)
  s2 = df.iloc[1]
  assert (s2["1.0s Delta"], s2["2.0s Delta"], s2["Train Acc OFF (%)"], s2["Train Acc ON (%)"]) == (6.25, 5.0, 30.0, 80.0)
  assert df.iloc[2]["Subject"] == "Mean" and df.iloc[2]["1.0s Delta"] == pytest.approx(-1.875, abs=0.006)
  assert df.iloc[2]["Train Acc OFF (%)"] == pytest.approx(62.5)
  assert list(df.columns) == ["Subject", "Clean Windows", "1.0s OFF (%)", "1.0s ON (%)", "1.0s Delta", "2.0s OFF (%)",
                              "2.0s ON (%)", "2.0s Delta", "Train Acc OFF (%)", "Train Acc ON (%)"]
  frozen = tmp_path / "rep" / "legacy_leaky" / csv.name
  assert frozen.read_bytes() == csv.read_bytes()
  assert frozen.with_suffix(".meta.txt").read_bytes() == csv.with_suffix(".meta.txt").read_bytes()
  assert "WARNING S02" in out and "WARNING S01" not in out


def test_ab_script_no_freeze_without_flag_and_alias_name(tmp_path, monkeypatch):
  argv = _tree(tmp_path, ("S01",))
  _stub(monkeypatch, TABLE)
  assert ab.main(["--model", "shallow_convnet", *argv]) == 0
  assert (tmp_path / "rep" / "augmentation_ab_shallow_conv_net.csv").is_file()
  assert not (tmp_path / "rep" / "legacy_leaky").exists()


@pytest.mark.parametrize("off_train,warns", [(0.3999, True), (0.40, False), (0.0, True), (0.41, False)])
def test_warning_threshold_applies_to_off_train_only(tmp_path, monkeypatch, capsys, off_train, warns):
  """Warn iff OFF train accuracy < 40 %; an ON train accuracy below 40 % alone must not warn."""
  argv = _tree(tmp_path, ("S01",))
  _stub(monkeypatch, [(0.5, 0.5, off_train), (0.5, 0.5, 0.1 if off_train >= 0.4 else 0.9)])
  assert ab.main(["--model", "eegnet", *argv]) == 0
  assert ("WARNING" in capsys.readouterr().out) is warns
