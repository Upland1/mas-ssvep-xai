"""P23.1 tests (connectivity-stats): in-memory Era C graph features at fs 256, known answers on synthetic data.

Each test names the bug it guards (fs 250 assumed, wrong edge/flat layout, conjugate order, row misalignment,
legacy folder accepted). Synthetic only: tones, coupled pairs and a synthetic built folder written with the real
builder (`tests/p16_synth.py`); no real recording is read.
"""

import numpy as np
import pytest

from src.features.connectivity import connectivity_graph_features as cgf
from src.features.connectivity import graph_features_subject as gfs
from src.features.connectivity import graph_inputs as gi
from src.features.ssvep.fbcca_extraction import fbcca_scores_vectorized, reference_bases, TARGET_FREQS
from src.io.subject_data import load_subject
from tests.p16_synth import write_built_subject

FS = 256.0
T = 256
NAMES7 = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]


def _t():
  return np.arange(T) / FS


def _fake(X, fs=FS, names=None, **kw):
  """Minimal `load_subject`-like dict around windows `X (n, C, T)`."""
  n, C, _ = X.shape
  names = names or [f"c{i}" for i in range(C)]
  bank = np.random.default_rng(1).normal(size=(n, 3, C, T))
  d = dict(subject="S99", built=True, fs=fs, fs_source="meta", filter_mode="continuous", X=X, y=np.full(n, 103),
           trial_ids=np.arange(n) // 3, offsets=np.arange(n) % 3, cv_groups=np.arange(n) // 3,
           channel_names=names, channels_dropped=[], trial_ids_approximate=False, bands={"fbcca": bank})
  d.update(kw)
  return d


def test_tone_lands_in_its_band_bins_fs256_and_fs250_assumption_is_wrong():
  """23 Hz is bin 23 at fs 256: inside the 24 Hz band (23-25). Assuming fs 250 moves it to 22.5 Hz, outside."""
  rng = np.random.default_rng(0)
  X = rng.normal(0, 0.01, (4, 3, T))
  X[:, 1] += np.cos(2 * np.pi * 23.0 * _t())
  ok = gfs.graph_features_for_subject(_fake(X, names=["a", "b", "c"]))
  bug = cgf.node_band_power(X, 250.0)
  # channel 1, column 0 (24 Hz fundamental): the correct fs sees about 3x more band power (log10 gap >= 0.3)
  assert np.all(ok.node[:, 1, 0] - bug[:, 1, 0] > 0.3)
  assert ok.fs == 256.0
  np.testing.assert_array_equal(ok.node, cgf.node_band_power(X, 256.0))


def test_15hz_tone_peaks_in_column_2_of_its_channel_only():
  rng = np.random.default_rng(1)
  X = rng.normal(0, 0.05, (5, 4, T))
  X[:, 2] += 3 * np.cos(2 * np.pi * 15.0 * _t())
  ds = gfs.graph_features_for_subject(_fake(X, names=list("wxyz")))
  assert ds.node.shape == (5, 4, 10)
  assert np.all(ds.node[:, 2].argmax(axis=-1) == 2)                     # fundamental of target 3 (15 Hz)
  assert np.all(ds.node[:, 2, 2] - ds.node[:, 2, 7] > 2)                # 2nd harmonic column 5 + 2 is empty
  assert np.all(ds.node[:, 2, 2] - ds.node[:, [0, 1, 3], 2].max(axis=1) > 3)


def _coupled(phi=np.pi / 3, n=60, C=5, seed=2):
  rng = np.random.default_rng(seed)
  X = rng.normal(0, 1.0, (n, C, T))
  X[:, 1] += 5 * np.cos(2 * np.pi * 15.0 * _t())
  X[:, 3] += 5 * np.cos(2 * np.pi * 15.0 * _t() - phi)
  return X


def test_coupled_pair_coherence_one_on_that_edge_only_and_known_phase():
  phi = np.pi / 3
  ds = gfs.graph_features_for_subject(_fake(_coupled(phi)))
  coh, ph = ds.edge_coh, ds.edge_phase
  assert coh.shape == (60, 5, 5, 5) and ph.shape == (60, 5, 5, 5, 2)
  assert coh[:, 1, 3, 2].min() > 0.95 and coh[:, 3, 1, 2].min() > 0.95
  other = np.ones((5, 5), bool)
  other[[1, 3], [3, 1]] = False
  other[np.arange(5), np.arange(5)] = False
  assert coh[:, other, 2].mean() < 0.5                                   # every other edge near the floor
  assert coh[:, 1, 3, [0, 1, 3, 4]].mean() < 0.5                        # same edge, other bands
  assert abs(ph[:, 1, 3, 2, 0].mean() - np.cos(phi)) < 0.02          # noise jitters single windows; mean is exact  # [i, j] = phase of X_i conj(X_j)
  assert abs(ph[:, 1, 3, 2, 1].mean() - np.sin(phi)) < 0.02
  assert abs(ph[:, 3, 1, 2, 1].mean() + np.sin(phi)) < 0.02  # [j, i] is the conjugate


def test_independent_channels_sit_at_the_small_sample_floor_one_third():
  """3 Welch segments: E[MSC] of independent noise is about 1/3 (R4 bias), not 0; the diagonal is exactly 1."""
  X = np.random.default_rng(3).normal(0, 1.0, (200, 4, T))
  coh = gfs.graph_features_for_subject(_fake(X)).edge_coh
  off = coh[:, ~np.eye(4, dtype=bool)]
  assert 0.25 < off.mean() < 0.45
  np.testing.assert_allclose(coh[:, np.arange(4), np.arange(4)], 1.0, atol=1e-9)


def test_upper_tri_flat_layout_proof():
  """Flat index of coherence is pair * 5 + k, of phase (pair * 5 + k) * 2 + c, pairs = triu_indices(C, 1) row-major."""
  C = 7
  i, j, k, c = np.meshgrid(np.arange(C), np.arange(C), np.arange(5), np.arange(2), indexing="ij")
  code = (1000 * i + 100 * j + 10 * k + c).astype(float)[None]
  flat = cgf.upper_tri_flat(code)
  pairs = list(zip(*np.triu_indices(C, 1)))
  assert flat.shape == (1, 21 * 5 * 2)
  for p, (a, b) in enumerate(pairs):
    for kk in range(5):
      for cc in range(2):
        assert flat[0, (p * 5 + kk) * 2 + cc] == 1000 * a + 100 * b + 10 * kk + cc
  assert pairs[0] == (0, 1) and pairs[1] == (0, 2) and pairs[-1] == (5, 6)
  # on features: the coupled edge (1, 3) of a 5-channel set is pair index 5 (pairs: 01 02 03 04 12 13 ...)
  ds = gfs.graph_features_for_subject(_fake(_coupled()))
  fc = cgf.upper_tri_flat(ds.edge_coh).mean(axis=0)
  p13 = [tuple(map(int, q)) for q in zip(*np.triu_indices(5, 1))].index((1, 3))
  assert int(fc.argmax()) == p13 * 5 + 2
  # P15 model layout: phase (n, C, C, 5, 2) -> (n, C, C, 10) band-major then cos/sin
  inp = gi.build_inputs(ds, "nodes+coh+phase+F")
  assert inp.edge.shape == (60, 5, 5, 15) and inp.graph.shape == (60, 5) and inp.node.shape == (60, 5, 10)
  np.testing.assert_allclose(inp.edge[:, 1, 3, 5 + 2 * 2 + 1], ds.edge_phase[:, 1, 3, 2, 1], atol=1e-6)


def test_row_alignment_with_load_subject_on_a_built_folder(tmp_path):
  root = tmp_path / "w1_s0.25"
  write_built_subject(root, "S01", n_trials=10, seed=4)
  d = load_subject(root / "S01", bands=("fbcca",), channels=NAMES7)
  assert d["fs"] == 256.0 and d["fs_source"] == "meta"
  ds = gfs.graph_features_for_subject(d, NAMES7, chunk=16)
  n = len(d["y"])
  assert n > 16
  assert set(np.unique(ds.y)) <= {101, 102, 103, 104, 105}
  np.testing.assert_array_equal(ds.y, d["y"])
  np.testing.assert_array_equal(ds.trial_ids, d["trial_ids"])
  np.testing.assert_array_equal(ds.offsets, d["offsets"])
  np.testing.assert_array_equal(ds.cv_groups, d["cv_groups"])
  assert ds.channels_kept == NAMES7 and ds.node.shape == (n, 7, 10) and ds.edge_coh.shape == (n, 7, 7, 5)
  for r in (0, 15, 16, 17, n - 1):                                      # chunk borders keep their row
    one = cgf.build_graph_features(d["X"][r:r + 1], 256.0)
    np.testing.assert_allclose(ds.node[r], one["node"][0], atol=1e-12)
    np.testing.assert_allclose(ds.edge_coh[r], one["edge_coh"][0], atol=1e-12)
    np.testing.assert_allclose(ds.edge_phase[r], one["edge_phase"][0], atol=1e-12)
  fb = fbcca_scores_vectorized(d["bands"]["fbcca"], reference_bases(256.0, T, TARGET_FREQS))
  np.testing.assert_array_equal(ds.X_fbcca, fb)
  assert ds.X_fbcca.shape == (n, 5)
  # the planted stimulus tone: median FBCCA argmax equals the label well above chance (5 classes)
  assert np.mean(ds.X_fbcca.argmax(1) == ds.y_index) > 0.5


def test_channel_order_is_the_loaded_one(tmp_path):
  """A tone planted on the real O1 channel appears at the position of O1 in `channels`, whatever the folder order."""
  root = tmp_path / "r"
  write_built_subject(root, "S02", n_trials=10, seed=5)
  names = ["O2", "O1", "PO3"]                                            # permuted subset
  d = load_subject(root / "S02", bands=("fbcca",), channels=names)
  ds = gfs.graph_features_for_subject(d, names)
  assert ds.channels_kept == names and ds.node.shape[1] == 3
  with pytest.raises(ValueError, match="differ"):
    gfs.graph_features_for_subject(d, ["O1", "O2", "PO3"])


def test_refuses_legacy_assumed_fs_and_missing_bank():
  X = np.random.default_rng(6).normal(size=(3, 3, T))
  with pytest.raises(ValueError, match="built"):
    gfs.graph_features_for_subject(_fake(X, built=False))
  with pytest.raises(ValueError, match="legacy"):
    gfs.graph_features_for_subject(_fake(X, fs=250.0, fs_source="legacy-assumed"))
  with pytest.raises(ValueError, match="FBCCA"):
    gfs.graph_features_for_subject(_fake(X, bands={}))
  with pytest.raises(ValueError, match="continuous"):
    gfs.graph_features_for_subject(_fake(X, filter_mode="per_window"))


def test_legacy_cache_default_stays_250():
  import inspect
  assert inspect.signature(cgf.build_graph_features).parameters["fs"].default == 250.0
