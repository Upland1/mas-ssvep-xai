"""P16.5 build_windows end to end on a fake .ebr: files of 5.2, legacy starts, modes, guard, resume, refusals."""

import json

import numpy as np
import pytest

from scripts import build_windows as bw
from src.preprocessing.windowing import compare_trial_ids
from tests import p16_synth as S


@pytest.fixture(scope="module")
def raw(tmp_path_factory):
  root = tmp_path_factory.mktemp("raw")
  S.write_raw_subject(root, "S01", n_trials=10, seed=1)
  S.write_raw_subject(root, "S02", n_trials=10, seed=2, spike_s=57.5, bad_channel="O2")
  (root / "S03").mkdir()                         # no OO.ebr -> skipped
  return root


def _run(raw, out, *extra):
  return bw.main(["--raw-dir", str(raw), "--out-root", str(out), *extra])


def test_files_shapes_and_metadata(raw, tmp_path, capsys):
  assert _run(raw, tmp_path / "cont", "--filter-mode", "continuous", "--check-legacy-starts") == 0
  out = capsys.readouterr().out
  assert "[-] Skipping S03" in out
  d = tmp_path / "cont" / "S01"
  n = 10 * 8                                       # per trial 2 + 1 + 5 windows
  for name, shape in (("X_time_windows", (n, 8, 256)), ("X_raw_windows", (n, 8, 256)),
                      ("X_bands_fbcca", (n, 3, 8, 256)), ("X_bands_fbcsp", (n, 5, 8, 256)), ("y_labels", (n,)),
                      ("trial_ids", (n,)), ("window_starts", (n,)), ("sub_idx", (n,)), ("window_offsets", (n,)),
                      ("valid_mask", (n,)), ("valid_mask_no_guard", (n,)), ("reject_reason", (n,))):
    assert np.load(d / f"{name}.npy").shape == shape, name
  assert np.load(d / "valid_mask.npy").dtype == np.int8 and np.load(d / "y_labels.npy").dtype == np.int64
  meta = json.loads((d / "windows_meta.json").read_text())
  assert meta["fs"] == 256.0 and meta["filter_mode"] == "continuous" and len(meta["channels"]) == 8
  assert meta["windows_per_trial"] == {"201": 2, "202": 1, **{str(c): 5 for c in range(101, 106)}}
  assert 0.5 < meta["quality"]["guard_sec"] < 5.0              # measured ringing of the 1 Hz high-pass
  assert meta["n_trials"] == 10 * 3                                # one id per segment
  # legacy starts: every condition equal (acceptance 3)
  for line in [l for l in out.splitlines() if "legacy-starts S01" in l]:
    nums = dict(p.split(" ") for p in line.split(": ")[1].replace("max|d| ", "max ").split(", "))
    assert nums["n_legacy"] == nums["n_built"] == nums["n_equal"], line
  assert "trial-ids S01" in out and "startup S01" in out


def test_trial_ids_of_the_legacy_reconstruction_are_consistent_on_a_clean_subject(raw, tmp_path, capsys):
  _run(raw, tmp_path / "c", "--filter-mode", "continuous", "--subjects", "S01", "--check-legacy-starts")
  line = [l for l in capsys.readouterr().out.splitlines() if "trial-ids S01" in l][0]
  assert line.endswith("windows in inconsistent groups 0") and "reconstructed trials 10" in line


def test_compare_trial_ids_known_answer():
  true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
  assert compare_trial_ids(true + 7, true)["n_inconsistent_windows"] == 0           # renamed ids
  shifted = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 2])                                 # a lost window shifts chunks
  r = compare_trial_ids(shifted, true)
  assert r["n_inconsistent_windows"] == 10 and r["n_reconstructed"] == 3 and r["n_true"] == 2


def test_modes_differ_only_in_the_bands(raw, tmp_path):
  assert _run(raw, tmp_path / "c", "--filter-mode", "continuous", "--subjects", "S01") == 0
  assert _run(raw, tmp_path / "p", "--filter-mode", "per_window", "--subjects", "S01") == 0
  c, p = tmp_path / "c" / "S01", tmp_path / "p" / "S01"
  for name in ("X_time_windows", "X_raw_windows", "y_labels", "trial_ids", "window_starts", "valid_mask"):
    assert np.array_equal(np.load(c / f"{name}.npy"), np.load(p / f"{name}.npy")), name
  bc, bp = np.load(c / "X_bands_fbcsp.npy"), np.load(p / "X_bands_fbcsp.npy")
  assert not np.allclose(bc, bp)
  # PF-14: per-window narrow-band error is larger at the window edges than in the centre
  err = np.abs(bp - bc)[:, 1]
  e = 26
  assert err[..., :e].mean() + err[..., -e:].mean() > 2 * 2 * err[..., 2 * e:-2 * e].mean()


def test_planted_spike_and_bad_channel_in_the_saved_decision(raw, tmp_path):
  assert _run(raw, tmp_path / "c", "--subjects", "S02") == 0
  d = tmp_path / "c" / "S02"
  meta = json.loads((d / "windows_meta.json").read_text())
  assert meta["quality"]["channels_dropped"] == ["O2"]
  reason, starts = np.load(d / "reject_reason.npy"), np.load(d / "window_starts.npy")
  spike = int(57.5 * 256)
  hit = (starts <= spike) & (starts + 256 > spike)
  assert hit.sum() >= 1 and np.all(reason[hit] == 1)
  guard = (reason == 2)
  assert guard.sum() >= 1
  # reason-2 windows are valid without the guard and rejected with it
  assert np.all(np.load(d / "valid_mask_no_guard.npy")[guard] == 1) and np.all(np.load(d / "valid_mask.npy")[guard] == 0)
  near = np.abs(starts[guard] + 128 - spike) / 256 <= meta["quality"]["guard_sec"] + 1.0
  assert near.all()
  assert meta["quality"]["rejections_by_label"]


def test_resume_refuses_legacy_folder_and_stride_subfolder(raw, tmp_path, capsys):
  assert _run(raw, tmp_path / "c", "--subjects", "S01") == 0
  capsys.readouterr()
  assert _run(raw, tmp_path / "c", "--subjects", "S01", "--resume") == 0
  assert "already built" in capsys.readouterr().out
  assert _run(raw, tmp_path / "c", "--subjects", "S01", "--resume", "--guard-sec", "0.5") == 1   # P19 C-a: refused
  capsys.readouterr()
  assert _run(raw, tmp_path / "c", "--subjects", "S01", "--resume", "--guard-sec", "0.5", "--overwrite") == 0
  assert "already built" not in capsys.readouterr().out                 # other parameters: rebuilt
  leg = tmp_path / "leg"
  (leg / "S01").mkdir(parents=True)
  np.save(leg / "S01" / "X_psd_features.npy", np.zeros((1, 2)))
  assert _run(raw, leg, "--subjects", "S01") == 1
  assert _run(raw, tmp_path / "s", "--subjects", "S01", "--stride-sec", "0.5") == 0
  assert (tmp_path / "s" / "w1_s0.5" / "S01" / "windows_meta.json").is_file()
  assert not list((tmp_path / "s").rglob("*.partial"))


def test_config_missing_key_is_reported(tmp_path, capsys):
  bad = tmp_path / "c.yaml"
  bad.write_text("project: {target_conditions: [101]}\n")
  assert bw.main(["--config", str(bad)]) == 1
  assert "missing config key" in capsys.readouterr().out
