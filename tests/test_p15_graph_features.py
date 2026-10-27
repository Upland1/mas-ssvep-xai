"""P15 builder tests (connectivity-stats): graph features, the cached dataset, the connectivity gate.

Synthetic data only (never reads generated or git-ignored files). Known answers by hand; the planted-leak,
pre-gate-id and verdict tests fail on the historical bugs (PF-01 window-level split, PF-03 post-gate ids).
"""

import hashlib

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedKFold

from scripts.connectivity.graph_modeling import benchmark_connectivity_gate as gate
from scripts.connectivity.graph_modeling import build_graph_dataset as bgd
from src.features.connectivity import connectivity_graph_features as cgf
from src.features.connectivity import graph_dataset as gd
from src.preprocessing.dataset import cv_utils as cu
from tests.p05_synth import write_subject

FS = 250.0
T = 256
TARGETS = cgf.TARGET_FREQS


def _noise(n=6, C=7, seed=0):
  return np.random.default_rng(seed).normal(0, 1.0, (n, C, T))


def _tone(f, fs=FS, phase=0.0):
  return np.cos(2 * np.pi * f * np.arange(T) / fs + phase)


# --- graph features (P15.1, R6) -------------------------------------------------------

def test_node_power_layout_tone_in_channel_2_at_15hz():
  """15 Hz is target index 2 (fundamental, column 2); channel 2 holds the maximum of the (C, 10) map."""
  w = _noise()
  w[:, 2] += 6 * _tone(15.0)
  node = cgf.node_band_power(w, FS)
  assert node.shape == (6, 7, 10)
  for i in range(len(w)):
    assert np.unravel_index(np.argmax(node[i]), node[i].shape) == (2, 2)


def test_node_power_second_harmonic_column():
  """A tone at 2 x 10.9091 Hz lands in column 5 + 3 = 8 (harmonic-major, target 3)."""
  w = _noise(seed=1)
  w[:, 4] += 6 * _tone(2 * 10.9091)
  node = cgf.node_band_power(w, FS)
  for i in range(len(w)):
    assert np.unravel_index(np.argmax(node[i]), node[i].shape) == (4, 8)


def test_band_bins_nearest_when_none():
  freqs = np.array([0.0, 4.0, 8.0])
  assert cgf.band_bins(freqs, 5.5, 1.0).tolist() == [1]     # no bin within 1 Hz: nearest (4.0, |1.5| < |2.5|)
  assert cgf.band_bins(freqs, 4.5, 1.0).tolist() == [1]


def test_edge_coherence_planted_pair_is_the_maximum_edge():
  """Pair (1, 4) shares a 20 Hz source; every other pair is independent noise. Welch: 3 segments."""
  rng = np.random.default_rng(3)
  w = rng.normal(0, 1.0, (20, 7, T))
  src = rng.normal(0, 1.0, (20, T))
  # narrowband common source around 20 Hz
  spec = np.fft.rfft(src, axis=-1)
  f = np.fft.rfftfreq(T, 1 / FS)
  spec[:, np.abs(f - 20.0) > 3.0] = 0
  s = np.fft.irfft(spec, n=T, axis=-1)
  s = 8 * s / s.std()
  w[:, 1] += s
  w[:, 4] += 0.5 * s
  coh = cgf.edge_coherence(w, FS)
  assert coh.shape == (20, 7, 7, 5)
  m = coh[..., 1].mean(axis=0)      # band index 1 = 20 Hz
  iu, ju = np.triu_indices(7, 1)
  best = np.argmax(m[iu, ju])
  assert (iu[best], ju[best]) == (1, 4)
  assert m[1, 4] > 0.9 and np.sort(m[iu, ju])[-2] < 0.75
  assert np.allclose(coh, coh.transpose(0, 2, 1, 3))
  assert np.allclose(coh[:, 0, 0], 1.0)


def test_edge_phase_known_lag_unit_phasor():
  """Exact-bin tone at 16 Hz (fs 256): [i, j] = (cos, sin)(phi_i - phi_j), |.| = 1, [j, i] conjugate."""
  fs = 256.0
  w = np.zeros((1, 3, T))
  phis = [0.3, 1.1, -0.7]
  for c, p in enumerate(phis):
    w[0, c] = _tone(16.0, fs, p)
  ph = cgf.edge_phase(w, fs, targets=[16.0, 20.0, 15.0, 10.0, 8.0])
  assert ph.shape == (1, 3, 3, 5, 2)
  for i in range(3):
    for j in range(3):
      d = phis[i] - phis[j]
      assert np.allclose(ph[0, i, j, 0], [np.cos(d), np.sin(d)], atol=1e-6)
  assert np.allclose(np.linalg.norm(ph, axis=-1), 1.0, atol=1e-9)


def test_upper_tri_flat_layout_pair_major_then_band_then_cs():
  """C = 4: pairs (0,1),(0,2),(0,3),(1,2),(1,3),(2,3); index pair * 5 + band (* 2 + cos/sin)."""
  C = 4
  a = np.zeros((1, C, C, 5))
  a[0] = np.arange(C * C * 5).reshape(C, C, 5)
  flat = cgf.upper_tri_flat(a)
  assert flat.shape == (1, 30)
  pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
  for p, (i, j) in enumerate(pairs):
    for b in range(5):
      assert flat[0, p * 5 + b] == a[0, i, j, b]
  e = np.arange(C * C * 5 * 2, dtype=float).reshape(1, C, C, 5, 2)
  fe = cgf.upper_tri_flat(e)
  assert fe.shape == (1, 60) and fe[0, (4 * 5 + 3) * 2 + 1] == e[0, 1, 3, 3, 1]


def test_build_graph_features_shapes():
  g = cgf.build_graph_features(_noise(3), FS)
  assert g["node"].shape == (3, 7, 10) and g["edge_coh"].shape == (3, 7, 7, 5) and g["edge_phase"].shape == (3, 7, 7, 5, 2)


# --- the cached dataset ----------------------------------------------------------------

def _build(tmp_path, bad_window=None, subject="S03"):
  """Synthetic legacy tree; optionally a stimulus window made unusable (rejected by the gate)."""
  d = write_subject(tmp_path, subject, n_trials=8)
  if bad_window is not None:
    X = np.load(d / "X_time_windows.npy")
    X[bad_window] += 500.0 * np.sign(np.sin(2 * np.pi * 7 * np.arange(X.shape[2]) / FS))   # all channels: Vpp 1000 uV
    np.save(d / "X_time_windows.npy", X)
  return d


def _hash(d):
  return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*.npy"))}


def test_dimensions_of_the_nine_sets(tmp_path):
  _build(tmp_path)
  arrays, b = bgd.build_subject(tmp_path, "S03")
  gd.save_graph_dataset(gd.cache_path("S03", tmp_path), arrays, FS, gd.code_fingerprint(FS), b["channels_dropped"], b["trial_ids_approximate"])
  ds = gd.load_graph_dataset("S03", tmp_path)
  sets = gate.feature_sets(ds)
  n = len(ds)
  assert {k: v.shape[1] for k, v in sets.items()} == {"N": 70, "F": 5, "Base": 75, "Ec": 105, "Ep": 210, "Ec+Ep": 315,
                                                      "Base+Ec": 180, "Base+Ep": 285, "Base+Ec+Ep": 390}
  assert all(v.shape[0] == n for v in sets.values()) and ds.channels_kept == ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  assert np.array_equal(ds.y_index, ds.y - 101) and ds.classes == (101, 102, 103, 104, 105)


def test_cache_is_new_file_legacy_arrays_untouched_and_stale_guard(tmp_path):
  d = _build(tmp_path)
  before = _hash(d)
  assert bgd.main(["--data-root", str(tmp_path), "--reports-dir", str(tmp_path / "rep"), "--subjects", "S03"]) == 0
  assert _hash(d) == before and (d / "graph_dataset.npz").is_file()
  assert (tmp_path / "rep" / "graph_dataset_sanity.csv").is_file()
  with pytest.raises(ValueError):
    gd.save_graph_dataset(d / "X_time_windows.npy", {}, FS, "h", [], False)    # never overwrites a legacy array
  # stale: a different stored hash is refused
  z = dict(np.load(d / "graph_dataset.npz"))
  z["code_hash"] = np.array("0" * 64)
  np.savez(d / "graph_dataset.npz", **z)
  with pytest.raises(gd.StaleGraphDataset):
    gd.load_graph_dataset("S03", tmp_path)
  assert gd.load_graph_dataset("S03", tmp_path, check_hash=False).fs == FS
  with pytest.raises(FileNotFoundError):
    gd.load_graph_dataset("S99", tmp_path)


def test_trial_ids_are_pre_gate_pf03(tmp_path):
  """Window 22 (3rd of the first 101 trial, after 20 rows of 201) is rejected: the first trial keeps 4 windows
  and the next block starts a new id; ids built after the gate (the bug) would give the first id 5 windows."""
  _build(tmp_path, bad_window=22)
  arrays, b = bgd.build_subject(tmp_path, "S03")
  ids = arrays["trial_ids"]
  assert b["n_rejected"] == 1 and len(ids) == 199
  first = ids[0]
  assert (ids == first).sum() == 4 and ids[4] == first + 1 and (ids == first + 1).sum() == 5
  assert b["trial_ids_approximate"] is False   # approximate flags the PRE-gate blocks, which are exact here


def test_sanity_rows_planted_class_signal(tmp_path):
  _build(tmp_path)
  arrays, b = bgd.build_subject(tmp_path, "S03")
  gd.save_graph_dataset(gd.cache_path("S03", tmp_path), arrays, FS, gd.code_fingerprint(FS), [], False)
  rows = bgd.sanity_rows(gd.load_graph_dataset("S03", tmp_path))
  assert len(rows) == 5 and all(r["n_own"] == 40 for r in rows)
  assert all(r["node_f1_diff"] > 0.3 for r in rows)      # planted sinusoid at the own target raises own-band power


# --- the gate (P15.3) ------------------------------------------------------------------

def _tiny_ds(n_trials=20, outlier_row=None, seed=0):
  rng = np.random.default_rng(seed)
  n = n_trials * 5
  y = np.repeat(np.arange(101, 106), n // 5)
  trial_ids = np.arange(n) // 5
  node = rng.normal(size=(n, 7, 10)) + 0.5 * (y[:, None, None] - 103)
  ds = gd.GraphDataset("Sxx", node, rng.uniform(0, 1, (n, 7, 7, 5)), rng.normal(size=(n, 7, 7, 5, 2)),
                       rng.uniform(0, 1, (n, 5)), y, trial_ids, ["c"] * 7, [], FS, "h", False)
  if outlier_row is not None:
    ds.node[outlier_row] = 1e6
  return ds


def test_gate_split_has_no_shared_trial_ids_and_catches_a_window_level_split():
  ds = _tiny_ds()
  for r in range(3):
    sp = cu.make_splits("grouped", ds.y, ds.trial_ids, 42 + r)
    cu.assert_no_shared_trials(sp, ds.trial_ids)
  leaky = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros((len(ds.y), 1)), ds.y))
  with pytest.raises(AssertionError):
    cu.assert_no_shared_trials(leaky, ds.trial_ids)


@pytest.mark.parametrize("k", [0, 30])
def test_gate_r2_test_fold_outlier_does_not_move_other_predictions(k):
  """A planted outlier (1e6) in one TEST window changes no other prediction of its fold: scaler and SelectKBest
  see the training fold only (a global fit would shift every statistic)."""
  from src.models.classical.legacy_eval import FeatureSpace, oof_space
  ds = _tiny_ds()
  X0 = gate.feature_sets(ds)["Base+Ec"]
  splits = cu.make_splits("grouped", ds.y, ds.trial_ids, 42)
  row = splits[0][1][0]
  X1 = X0.copy()
  X1[row] = 1e6
  res = []
  for X in (X0, X1):
    r, e = oof_space(FeatureSpace("s", [X]), None, ds.y, {"m": gate.make_model(k, X.shape[1])}, 42, splits)
    assert not e
    res.append(r["m"]["scores"])
  te = splits[0][1]
  others = te[te != row]
  assert np.array_equal(res[0][others], res[1][others])


def test_evaluate_subject_rows_and_seeds():
  ds = _tiny_ds()
  rows = gate.evaluate_subject(ds, 2, [0, 30], sets=("Base", "Base+Ec"))
  df = pd.DataFrame(rows)
  assert list(df.columns) == gate.COLUMNS and len(df) == 2 * 2 * 2
  assert set(df.dim) == {75, 180} and df.acc_1s.between(0, 100).all() and df.acc_2s.between(0, 100).all()
  again = pd.DataFrame(gate.evaluate_subject(ds, 2, [0, 30], sets=("Base", "Base+Ec")))
  assert df.equals(again)    # deterministic: splits seed 42 + r


def _table(deltas, k=0, edge="Base+Ec", base=70.0):
  rows = []
  for s, d in deltas.items():
    for name, a in (("Base", base), (edge, base + d), ("Base+Ep", base - 5), ("Base+Ec+Ep", base - 5)):
      rows.append({"subject": s, "set": name, "k_select": k, "repeat": 0, "dim": 1, "acc_1s": a, "acc_2s": a})
  return pd.DataFrame(rows)


def test_gate_verdict_rule():
  # mean >= 2 and 2 of 3 responders >= 2 -> pass
  assert gate.gate_verdict(_table({"S01": 0, "S02": 0, "S03": 3, "S04": 2.5, "S05": 0}), 0)["passed"] is False  # mean 1.1
  assert gate.gate_verdict(_table({"S01": 5, "S02": 5, "S03": 3, "S04": 2.5, "S05": 0}), 0)["passed"] is True
  # mean >= 2 but only 1 of 3 responders -> fail (the R-14 shape)
  v = gate.gate_verdict(_table({"S01": 16, "S02": 3, "S03": 1.3, "S04": 0.1, "S05": -1.7}), 0)
  assert v["mean_delta"] > 2 and v["responders_ok"] == 0 and v["passed"] is False
  # responders pass but cohort mean < 2 -> fail
  assert gate.gate_verdict(_table({"S01": -10, "S02": 0, "S03": 3, "S04": 3, "S05": 3}), 0)["passed"] is False
  # exactly 2 of 3 is enough; the best set is picked by cohort mean
  v = gate.gate_verdict(_table({"S01": 4, "S02": 4, "S03": 2, "S04": 2, "S05": 1.9}), 0)
  assert v["passed"] is True and v["best"] == "Base+Ec" and v["responders_ok"] == 2
  # no responder present -> not evaluable
  assert gate.gate_verdict(_table({"S01": 9, "S02": 9}), 0)["passed"] is False
  assert "PASSES" in gate.verdict_text(gate.gate_verdict(_table({"S03": 5, "S04": 5, "S05": 5}), 0))


def test_gate_script_smoke_on_synthetic_cache(tmp_path):
  _build(tmp_path)
  assert bgd.main(["--data-root", str(tmp_path), "--reports-dir", str(tmp_path / "rep")]) == 0
  assert gate.main(["--data-root", str(tmp_path), "--reports-dir", str(tmp_path / "rep"), "--repeats", "1", "--k-select", "0", "30"]) == 0
  df = pd.read_csv(tmp_path / "rep" / "connectivity_gate_benchmark.csv")
  assert list(df.columns) == gate.COLUMNS and len(df) == 1 * len(gate.SET_NAMES) * 2 * 1
  meta = (tmp_path / "rep" / "connectivity_gate_benchmark.meta.txt").read_text()
  assert "fs=250" in meta and "gate" in meta and "i%5" in meta
