"""P11 seed-spread DIAGNOSTIC (results review Round 1, required step 1): fixed seed-42 grouped folds across seed bases,
base 42 = the reported A/B path, outputs only under reports/diagnostics/, A/B legacy and grouped pins unchanged.
Synthetic trees (tests/p05_synth), 1-2 epochs, CPU."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks.neural_networks import benchmark_nn_augmentation as ab
from scripts.diagnostics import network_seed_spread as nss
from src.models.cnn.benchmark_common import gated_windows
from src.models.cnn.eegnet_cv import train_and_eval_cv
from tests.p05_synth import write_subject

# A/B CSVs on the 2-subject tree (S01, S02, n_trials=3), 2 epochs, CPU, made with the code before `model_seed` existed
# (compact_cnn legacy also equals the pre-P11 pin of 03_changes_deep-learning.md).
AB_PINS = {
  ("eegnet", "legacy"): "1a660174aa8ecda8e6fadc2ec913dd74bc20fbce3fa6a1b7b816804ae63750d0",
  ("eegnet", "grouped"): "52affafced2e1b80c3414d7a85beda5ee6720572c0c62367a33e82ba02efdc59",
  ("compact_cnn", "legacy"): "8f16e9ee639d810a68254ba55bdd8a723b2b06a6473b5b85fef65e375c78e002",
  ("compact_cnn", "grouped"): "2b27cc7abaf388fd975e1e118c6859fc63e9a5b9f4869af9e6bea88163b0bc1f",
}


def _tree(tmp_path, subjects=("S01", "S02")):
  for s in subjects:
    write_subject(tmp_path / "proc", s, n_trials=3)
  cfg = tmp_path / "cfg.yaml"
  cfg.write_text("paths:\n  data_processed_dir: data/processed\n")
  return ["--device", "cpu", "--data-root", str(tmp_path / "proc"), "--config", str(cfg)]


def test_folds_identical_across_seed_bases_and_the_base_changes_training(tmp_path):
  _tree(tmp_path, ("S03",))
  g = gated_windows(tmp_path / "proc", "S03")
  runs = {b: train_and_eval_cv(g["X"], g["y"], epochs=2, device="cpu", seed=42, groups=g["trial_ids"], cv="grouped",
                               model_seed=b, augment=True) for b in (42, 1042, 2042)}
  for b in (1042, 2042):
    for (tr, te), (tr0, te0) in zip(runs[b]["splits"], runs[42]["splits"]):
      np.testing.assert_array_equal(tr, tr0)
      np.testing.assert_array_equal(te, te0)
    assert not np.array_equal(runs[b]["proba"], runs[42]["proba"])  # the base reaches the model / loader / augmentation


def test_model_seed_42_and_none_reproduce_the_reported_path_exactly(tmp_path):
  _tree(tmp_path, ("S03",))
  g = gated_windows(tmp_path / "proc", "S03")
  for augment in (False, True):
    ref = train_and_eval_cv(g["X"], g["y"], epochs=2, device="cpu", groups=g["trial_ids"], augment=augment)
    got = train_and_eval_cv(g["X"], g["y"], epochs=2, device="cpu", groups=g["trial_ids"], augment=augment, model_seed=42)
    np.testing.assert_array_equal(got["proba"], ref["proba"])
    assert got["fold_train_acc"] == ref["fold_train_acc"]


def test_script_base_42_equals_ab_rows_and_writes_only_diagnostics(tmp_path):
  argv = _tree(tmp_path)
  rep = tmp_path / "rep"
  assert nss.main(["--model", "eegnet", "--seed-bases", "42", "1042", "--epochs", "2", "--reports-dir", str(rep), *argv]) == 0
  files = sorted(p.relative_to(rep).as_posix() for p in rep.rglob("*") if p.is_file())
  assert files == ["diagnostics/p11_seed_spread_eegnet.csv", "diagnostics/p11_seed_spread_eegnet.meta.txt"]
  df = pd.read_csv(rep / "diagnostics" / "p11_seed_spread_eegnet.csv")
  assert list(df.columns) == nss.COLUMNS
  assert list(df["Subject"]) == ["S01", "S02", "Mean", "S01", "S02", "Mean"]
  assert list(df["Seed base"]) == [42, 42, 42, 1042, 1042, 1042]
  meta = (rep / "diagnostics" / "p11_seed_spread_eegnet.meta.txt").read_text()
  assert "DIAGNOSTIC" in meta and "random_state=42" in meta and "1042" in meta
  abrep = tmp_path / "abrep"
  assert ab.main(["--model", "eegnet", "--epochs", "2", "--reports-dir", str(abrep), *argv]) == 0
  ref = pd.read_csv(abrep / "augmentation_ab_eegnet.csv")
  b42 = df[df["Seed base"] == 42].drop(columns="Seed base").reset_index(drop=True)
  pd.testing.assert_frame_equal(b42, ref, check_dtype=False)


def test_script_rejects_unknown_model():
  with pytest.raises(SystemExit):
    nss.build_parser().parse_args(["--model", "ccnn", "--seed-bases", "1042"])


@pytest.mark.parametrize("model,cv", sorted(AB_PINS), ids=[f"{m}-{c}" for m, c in sorted(AB_PINS)])
def test_ab_legacy_and_grouped_pins_unchanged(tmp_path, model, cv):
  argv = _tree(tmp_path)
  rep = tmp_path / "rep"
  assert ab.main(["--model", model, "--epochs", "2", "--cv", cv, "--reports-dir", str(rep), *argv]) == 0
  f = (rep / "legacy_leaky" if cv == "legacy" else rep) / f"augmentation_ab_{model}.csv"
  assert hashlib.sha256(f.read_bytes()).hexdigest() == AB_PINS[(model, cv)]
