"""P07 Round 1 independent known-answer tests (synthetic-tester): legacy P02 switch, protection of legacy arrays,
Makefile target, per-subject check of the P04 positional channels. Expected values come from the review's fix text:
legacy = P02 arrays (n, 7, 256) / (n, 217), PO7 excluded by name, tier 1 off, no channels.json; legacy folders are never
touched without --legacy-p02 / --overwrite-legacy-arrays; P04 positions (1, 4, 5, 6) must be POz, O1, Oz, O2.
Synthetic recordings and arrays in tmp_path only.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.signal import periodogram

from scripts.preprocessing import run_preprocessing as rp
from tests.p05_synth import write_subject
from tests.test_p02_preprocessing_smoke import FS, _signal, _write_ebr

ROOT = Path(__file__).resolve().parents[1]
NAMES8 = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]


def _run(tmp, proc, *extra):
  return rp.main(["--raw-dir", str(tmp / "raw"), "--processed-dir", str(tmp / proc), "--no-figures", *extra])


def _noisy_recording(tmp, noisy=None):
  b = _signal(5, seed=2)
  if noisy is not None:                                              # chronically noisy channel row
    b[noisy] = np.random.default_rng(9).normal(0, 100.0, b.shape[1])
  _write_ebr(tmp / "raw" / "S03" / "OO.ebr", b)


def _digest(folder):
  return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def test_legacy_switch_reproduces_p02_arrays(tmp_path):
  """Known answer: with --legacy-p02 the arrays are the P02 layout (tier 1 off):
  X_time (n, 7, 256) equal (array_equal) to the 8-channel --no-channel-drop run with row PO7 removed; X_psd (n, 217)
  equal to the 5-35 Hz periodogram of X_time; y equal; no channels.json. Mutant: PO7 kept gives 8 channels."""
  _noisy_recording(tmp_path)
  assert _run(tmp_path, "leg", "--legacy-p02") == 0
  assert _run(tmp_path, "ref", "--no-channel-drop") == 0
  L, R = tmp_path / "leg" / "S03", tmp_path / "ref" / "S03"
  X = np.load(L / "X_time_windows.npy")
  assert X.shape[1:] == (7, 256) and not (L / "channels.json").exists() and not (tmp_path / "leg" / "channels.json").exists()
  Xr = np.load(R / "X_time_windows.npy")
  assert Xr.shape[1] == 8
  np.testing.assert_array_equal(X, np.delete(Xr, NAMES8.index("PO7"), axis=1))
  np.testing.assert_array_equal(np.load(L / "y_labels.npy"), np.load(R / "y_labels.npy"))
  f, p = periodogram(X, fs=FS, axis=-1)
  sel = (f >= 5) & (f <= 35)
  psd = np.load(L / "X_psd_features.npy")
  assert psd.shape == (len(X), 217)
  np.testing.assert_allclose(psd, p[..., sel].reshape(len(X), -1), rtol=1e-6, atol=1e-12)


def test_legacy_switch_has_no_tier1(tmp_path):
  """Known answer: with POz chronically noisy, the P02 gate (tier 1 off) rejects the windows containing it, so the legacy
  run produces no 6-channel arrays and no channels.json; at most 7-channel arrays. Mutant with tier 1 left on drops
  POz and writes (n, 6, 256) plus channels.json."""
  _noisy_recording(tmp_path, noisy=2)
  _run(tmp_path, "leg", "--legacy-p02")
  x = tmp_path / "leg" / "S03" / "X_time_windows.npy"
  assert not x.exists() or np.load(x).shape[1] == 7
  assert not (tmp_path / "leg" / "S03" / "channels.json").exists()


def _legacy_folder(tmp):
  """A legacy P02 output (S03 + root copy, 7 channels, no channels.json) plus a skipped subject S02 with arrays."""
  _noisy_recording(tmp)
  assert _run(tmp, "proc", "--legacy-p02") == 0
  (tmp / "raw" / "S02").mkdir(parents=True)                          # no recording: skipped
  stale = tmp / "proc" / "S02"
  stale.mkdir(parents=True, exist_ok=True)
  write_subject(tmp / "proc", "S02", n_trials=1)                    # 7-channel arrays for the skipped subject
  return tmp / "proc"


def test_refuses_to_touch_legacy_arrays_and_flag_lifts_it(tmp_path, capsys):
  """Known answer: without --legacy-p02 a target folder holding 7-channel arrays and no channels.json makes the script
  exit 1 and change nothing (byte-identical tree, including the skipped S02 arrays and the root copy); with
  --overwrite-legacy-arrays it runs (exit 0) and writes channels.json. Mutant without the refusal overwrites S03 and
  deletes S02's arrays."""
  proc = _legacy_folder(tmp_path)
  before = _digest(proc)
  assert (proc / "S02" / "y_labels.npy").is_file() and (proc / "S03" / "X_time_windows.npy").is_file()
  capsys.readouterr()
  assert _run(tmp_path, "proc", "--all") == 1
  assert "Refusing" in capsys.readouterr().out
  assert _digest(proc) == before
  assert _run(tmp_path, "proc", "--all", "--overwrite-legacy-arrays") == 0
  assert (proc / "S03" / "channels.json").is_file()
  assert not (proc / "S02" / "y_labels.npy").exists()               # skipped subject's stale arrays removed once allowed


def test_makefile_preprocess_uses_legacy_switch():
  """Known answer: the `preprocess` target of the Makefile runs run_preprocessing with --legacy-p02 (so make never
  produces 8-channel arrays in data/processed/). Mutant: switch removed from the recipe."""
  lines = (ROOT / "Makefile").read_text().splitlines()
  i = lines.index("preprocess:")
  recipe = [l for l in lines[i + 1:] if l.startswith("\t")][:1]
  assert recipe and "scripts.preprocessing.run_preprocessing" in recipe[0] and "--legacy-p02" in recipe[0]


def test_p04_scripts_refuse_subject_whose_positions_shifted(tmp_path, capsys):
  """Known answer: S02 has 7 channels with channels.json kept = PO7, PO3, POz, PO4, O1, Oz, O2 (PO8 dropped), so
  positions (1, 4, 5, 6) would be PO3, O1, Oz, O2 -> not POz, O1, Oz, O2. train_models and batch_run_subjects skip S02
  with a reason (no result files), train_final_model and run_xai exit 1. The legacy S01 passes the same check.
  Mutant (config-only check) trains S02 silently."""
  from scripts.training import batch_run_subjects as brs, train_final_model as tfm, train_models as tm
  from scripts.xai import run_xai
  write_subject(tmp_path, "S02", n_trials=2, seed=32)
  (tmp_path / "S02" / "channels.json").write_text(json.dumps(
    {"kept": ["PO7", "PO3", "POz", "PO4", "O1", "Oz", "O2"], "dropped": ["PO8"]}))
  out = tmp_path / "out"
  tm.main(["--all", "--processed-dir", str(tmp_path), "--out-dir", str(out), "--no-figures"])
  assert "Skipping S02" in capsys.readouterr().out
  brs.main(["--subjects", "S02", "--processed-dir", str(tmp_path), "--out-dir", str(out), "--skip-cnn"])
  assert "Skipping S02" in capsys.readouterr().out
  assert not list(out.rglob("*S02*")) and not (out / "reports" / "batch_run_subjects.csv").exists()
  assert tfm.main(["--subject", "S02", "--processed-dir", str(tmp_path), "--out-dir", str(out), "--skip-cnn"]) == 1
  assert run_xai.main(["--subject", "S02", "--processed-dir", str(tmp_path), "--out-dir", str(out)]) == 1
