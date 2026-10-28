"""P16.6 load_subject on built and legacy fake folders: fs, trial ids, quality modes, channel names, layout checks."""

import numpy as np
import pytest

from src.io import subject_data as SD
from src.models.classical.benchmark_runner import prepare_subject
from tests import p05_synth, p16_synth as S


TH = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}
GATE = {"thresholds": TH, "channel_fail_fraction": 0.5}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  root = tmp_path_factory.mktemp("built")
  S.write_built_subject(root, "S01", n_trials=10, seed=1)
  S.write_built_subject(root, "S02", n_trials=10, seed=2, spike_s=57.5, bad_channel="O2")
  return root


@pytest.fixture(scope="module")
def legacy(tmp_path_factory):
  root = tmp_path_factory.mktemp("legacy")
  p05_synth.write_subject(root, "S03", n_trials=6)
  p05_synth.write_subject(root, "S04", n_trials=6, bad_channels=("O1",))
  return root


def test_built_folder_contract(built):
  d = SD.load_subject(built / "S01")
  assert d["built"] and d["fs"] == 256.0 and d["fs_source"] == "meta" and d["smoothing"] == "trial"
  assert d["channel_names"] == S.SCALP and d["channels_dropped"] == []
  n = len(d["y"])
  assert d["X"].shape == (n, 8, 256) and set(np.unique(d["y"])) == {101, 102, 103, 104, 105}
  assert n == 50 and d["n_trials"] == 10 and not d["trial_ids_approximate"]
  assert np.array_equal(d["sub_idx"], d["offsets"] // 256)
  assert d["window_starts"].shape == (n,) and d["bands"] == {}
  assert d["quality"]["mode"] == "shared" and d["n_rejected"] == d["n_selected"] - n
  assert d["meta"]["fs"] == 256.0 and "continuous" in d["source"]


def test_bands_use_kept_channels_in_the_saved_layout(built):
  d = SD.load_subject(built / "S02", bands=("fbcca", "fbcsp"))
  assert d["channels_dropped"] == ["O2"] and d["channel_names"] == S.SCALP[:7]
  assert d["X"].shape[1] == 7 and d["bands"]["fbcsp"].shape == (len(d["y"]), 5, 7, 256)
  assert d["bands"]["fbcca"].shape == (len(d["y"]), 3, 7, 256)
  with pytest.raises(FileNotFoundError):
    SD.load_subject(built / "S02", bands=("harmonic",))


def test_quality_modes(built):
  sh = SD.load_subject(built / "S02", conditions=(201, 202, 101, 102, 103, 104, 105))
  ng = SD.load_subject(built / "S02", conditions=(201, 202, 101, 102, 103, 104, 105), quality_mode="shared-no-guard")
  assert np.array_equal(np.sort(np.unique(sh["y"])), [101, 102, 103, 104, 105, 201, 202])
  ps = SD.load_subject(built / "S02", quality_mode="per-script", **GATE)
  assert len(ng["y"]) > len(sh["y"])                                  # the guard rejected windows around the spike
  assert ng["quality"]["guard_sec"] == sh["quality"]["guard_sec"]
  assert sh["quality"]["rejections_by_label"] and ps["quality"]["rejections_by_label"] is None
  assert ps["channels_dropped"] == ["O2"]
  with pytest.raises(ValueError, match="quality_mode"):
    SD.load_subject(built / "S01", quality_mode="x")


def test_cv_groups_put_the_cue_window_with_its_fixation_twin(built):
  """PF-13: with 201 and 202 selected, a grouped split must keep the 202 window with its 201 twin."""
  d = SD.load_subject(built / "S01", conditions=(201, 202, 101))
  n101 = len(np.unique(d["trial_ids"][d["y"] == 101]))
  assert d["n_trials"] == 10 + 10 + n101                              # trial_ids: one per segment
  for s in d["window_starts"][d["y"] == 202]:
    g202 = d["cv_groups"][(d["y"] == 202) & (d["window_starts"] == s)]
    g201 = d["cv_groups"][(d["y"] == 201) & (d["window_starts"] == s)]
    assert len(g201) == 1 and g202[0] == g201[0]
  assert len(np.unique(d["cv_groups"])) == 10 + n101
  st = SD.load_subject(built / "S01")
  assert np.array_equal(st["cv_groups"], st["trial_ids"])


def test_fs_override_and_pf04_tone_bin(built):
  """PF-04: the 24 Hz class peaks at 24.0 Hz with the metadata fs (256), at 23.44 Hz if fs=250 is assumed."""
  d = SD.load_subject(built / "S01", conditions=(101,))
  assert d["fs"] == 256.0
  spec = np.abs(np.fft.rfft(d["X"][:, 3:, :] * np.hanning(256), axis=-1)).mean(axis=(0, 1))
  peak = np.fft.rfftfreq(256, 1 / d["fs"])[spec[5:40].argmax() + 5]
  assert peak == pytest.approx(24.0, abs=0.01)
  assert np.fft.rfftfreq(256, 1 / 250.0)[spec[5:40].argmax() + 5] != pytest.approx(24.0, abs=0.01)
  o = SD.load_subject(built / "S01", fs_override=250.0)
  assert o["fs"] == 250.0 and o["fs_source"] == "override"
  with pytest.raises(ValueError):
    SD.load_subject(built / "S01", fs_override=0)


def test_legacy_folder_contract_and_equals_prepare_subject(legacy):
  d = SD.load_subject(legacy / "S03", **GATE)
  assert not d["built"] and d["fs"] == 250.0 and d["fs_source"] == "legacy-assumed" and d["smoothing"] == "mod5"
  assert d["window_starts"] is None and d["offsets"] is None
  b = prepare_subject(legacy, "S03")
  assert np.array_equal(d["y"], b["y"]) and np.array_equal(d["trial_ids"], b["trial_ids"])
  assert d["channel_names"] == b["channels_kept"] and d["trial_ids_approximate"] == b["trial_ids_approximate"]
  assert SD.load_subject(legacy / "S03", fs_override=256.0, **GATE)["fs"] == 256.0
  with pytest.raises(ValueError, match="legacy"):
    SD.load_subject(legacy / "S03", bands=("fbcsp",), **GATE)
  for mode in SD.QUALITY_MODES:                                       # one decision exists on legacy folders
    assert np.array_equal(SD.load_subject(legacy / "S03", quality_mode=mode, **GATE)["y"], d["y"])


def test_legacy_bad_channel_dropped_by_name(legacy):
  d = SD.load_subject(legacy / "S04", **GATE)
  assert d["channels_dropped"] == ["O1"] and "O1" not in d["channel_names"] and d["X"].shape[1] == 6


def test_discover_is_built_and_names(built, legacy, tmp_path):
  assert SD.discover_subjects(built) == ["S01", "S02"] and SD.is_built(built / "S01")
  assert SD.discover_subjects(legacy) == ["S03", "S04"] and not SD.is_built(legacy / "S03")
  (tmp_path / "S10").mkdir()
  (tmp_path / "notes").mkdir()
  assert SD.discover_subjects(tmp_path) == []
  assert SD.built_dir_name("continuous") == "processed_continuous"
  assert SD.built_dir_name("per_window", 1.0, 0.5) == "processed_per_window/w1_s0.5"
  assert SD.resolve_channel_names(8)[0] == "PO7" and SD.find_project_root().joinpath("configs").is_dir()


def test_rows_not_ordered_by_trial_and_offset_are_refused():
  ids = np.array([0, 0, 1, 1, 0])
  with pytest.raises(RuntimeError, match="grouped"):
    SD._check_trial_order(ids, np.array([0, 256, 0, 256, 512]))
  with pytest.raises(RuntimeError, match="offsets"):
    SD._check_trial_order(np.array([0, 0, 1]), np.array([256, 0, 0]))
  SD._check_trial_order(np.array([0, 0, 1, 1]), np.array([0, 256, 0, 256]))


def test_missing_files_fail_loudly(tmp_path):
  (tmp_path / "S01").mkdir()
  with pytest.raises(FileNotFoundError):
    SD.load_subject(tmp_path / "S01")


def test_per_script_gate_without_explicit_thresholds_raises_r5(built, legacy):
  """R5: no threshold is inherited. Fails on the historical default (thresholds=None -> GATE_THRESHOLDS)."""
  with pytest.raises(ValueError, match="explicit"):
    SD.load_subject(legacy / "S03")
  with pytest.raises(ValueError, match="explicit"):
    SD.load_subject(built / "S01", quality_mode="per-script")
  with pytest.raises(ValueError, match="explicit"):
    SD.load_subject(built / "S01", quality_mode="per-script", thresholds=TH)       # fail fraction missing too
  assert len(SD.load_subject(built / "S01")["y"]) == 50                            # shared needs no gate params


def test_cv_groups_pair_a_jittered_cue_window_by_overlap(tmp_path):
  """PF-13: a 202 window 8 samples off its 201 twin still joins that group (largest overlap); exact-start
  matching (the first implementation) leaves 202 windows in their own group."""
  S.write_built_subject(tmp_path, "S01", n_trials=10, seed=1, cue_jitter=8)
  d = SD.load_subject(tmp_path / "S01", conditions=(201, 202))
  m202 = np.flatnonzero(d["y"] == 202)
  assert len(m202) == 10
  for i in m202:
    s = d["window_starts"][i]
    two = np.flatnonzero((d["y"] == 201) & (np.abs(d["window_starts"] - s) < 256))
    assert len(two) == 1 and d["window_starts"][two[0]] == s - 8                    # the twin, 8 samples earlier
    assert d["cv_groups"][i] == d["cv_groups"][two[0]]
  assert len(np.unique(d["cv_groups"])) == 10                                      # 10 fixation trials only
