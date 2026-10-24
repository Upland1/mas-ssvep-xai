"""P02 builder smoke tests (data-engineer): scripts/preprocessing/run_preprocessing.py.

Synthetic EBR files written to tmp_path only (never data/); the known-answer suite is the
synthetic-tester's.
"""

import numpy as np
import pytest

from scripts.preprocessing import run_preprocessing as rp
from src.preprocessing.signal.filters import apply_iir_bandpass

FS = 256
CHANNELS = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2", "TIMESTAMP", "FLASHINGTIME", "MARK"]
SCALP = CHANNELS[1:8]


def _signal(n_trials=10, seed=0, spike_trial=None):
  """(11, T) block with the section-3 timing; channel c carries 10 uV at 5 + 3c Hz plus noise."""
  codes = [101, 102, 103, 104, 105] * (n_trials // 5)
  T = 5 * FS + n_trials * 15 * FS
  mark = np.zeros(T)
  for i, c in enumerate(codes):
    t = 5 * FS + i * 15 * FS
    for off, code in [(0, 201), (2, 202), (4, 203), (5, c), (10, 200)]:
      mark[t + off * FS] = code
  rng = np.random.default_rng(seed)
  tt = np.arange(T) / FS
  block = np.zeros((len(CHANNELS), T))
  for k in range(8):
    block[k] = 10 * np.sin(2 * np.pi * (5 + 3 * k) * tt) + rng.normal(0, 2, T)
  if spike_trial is not None:  # 400 uV spike in the first stimulus second of that trial
    s = 5 * FS + spike_trial * 15 * FS + 5 * FS + 100
    block[3, s:s + 5] += 400.0
  block[8] = 1.7e12 + 1000 * tt
  block[10] = mark
  return block


def _write_ebr(path, block):
  nc, ns = block.shape
  lines = ["ebr binary 1.0", "data_type double", f"sampling_rate {FS}", f"samples {ns}",
           "bands 1", "band_1 B1", f"channels {nc}"]
  lines += [f"channel_{k} {c}" for k, c in enumerate(CHANNELS, 1)]
  lines += ["trials 1", "trial_1 T1", "comments 1", "comment_1 Sample selection", "marks 0",
            "end_header"]
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(("\n".join(lines) + "\n").encode("ascii")
                   + np.ascontiguousarray(block.reshape(1, nc, 1, ns), dtype="<f8").tobytes())
  return path


@pytest.fixture
def tree(tmp_path):
  raw = tmp_path / "raw"
  _write_ebr(raw / "S01" / "OO.ebr", _signal(seed=1, spike_trial=2))
  _write_ebr(raw / "S03" / "OO.ebr", _signal(seed=3))
  (raw / "S02").mkdir(parents=True)          # no OO.ebr -> skipped
  (raw / "notes").mkdir()                    # not a subject folder
  return tmp_path


def _run(tree, *extra):
  return rp.main(["--raw-dir", str(tree / "raw"), "--processed-dir", str(tree / "proc"),
                  "--figures-dir", str(tree / "fig"), *extra])


def test_all_writes_arrays_root_copy_figures_and_skips(tree, capsys):
  assert _run(tree, "--all") == 0
  out = capsys.readouterr().out
  assert "[-] Skipping S02: recording not found" in out
  assert "Cohort: 2 subjects processed, 1 skipped (S02)" in out
  for s, n in (("S01", 79), ("S03", 80)):
    d = tree / "proc" / s
    X_psd, X_time, y = (np.load(d / f"{k}.npy") for k in rp.ARRAY_FILES)
    assert X_time.shape == (n, 7, 256) and X_psd.shape == (n, 217) and y.shape == (n,)
    assert y.dtype == np.int64 and X_time.dtype == np.float64
    assert (tree / "fig" / "spectra" / s / rp.PSD_FIGURE).stat().st_size > 0
    assert (tree / "fig" / "spectra" / s / rp.STIM_FIGURE).stat().st_size > 0
  y1 = np.load(tree / "proc" / "S01" / "y_labels.npy")
  assert rp.condition_counts(y1, (201, 202, 101, 102, 103, 104, 105)) == {
    201: 20, 202: 10, 101: 10, 102: 10, 103: 9, 104: 10, 105: 10}
  for k in rp.ARRAY_FILES:  # PF-09: root arrays equal the S03 folder
    np.testing.assert_array_equal(np.load(tree / "proc" / f"{k}.npy"),
                                  np.load(tree / "proc" / "S03" / f"{k}.npy"))
  assert (tree / "fig" / "spectra" / rp.PSD_FIGURE).is_file()


def test_default_subject_is_s03(tree, capsys):
  assert _run(tree, "--no-figures") == 0
  assert "[+] S03/OO.ebr: fs 256 Hz (header)" in capsys.readouterr().out
  assert not (tree / "proc" / "S01").exists() and (tree / "proc" / "y_labels.npy").is_file()


def test_windows_are_slices_of_the_continuous_filtered_signal(tree):
  """R3: row i of X_time equals apply_iir_bandpass(full recording)[:, start_i:start_i + 256]."""
  x, mark, fs = rp.load_recording(tree / "raw" / "S03" / "OO.ebr", SCALP, "MARK")
  assert fs == 256.0
  args = rp.build_parser().parse_args([])
  params = rp.resolve_params(rp.load_config(rp.DEFAULT_CONFIG), args)
  assert params["vpp_min"] == 0.5 and params["cross_duration_sec"] == 2.0
  out = rp.preprocess_recording(x, mark, fs, params)
  x_f = apply_iir_bandpass(x, fs, 1.0, 60.0, 4)
  for i, s in enumerate(out["starts"]):
    np.testing.assert_allclose(out["X_time"][i], x_f[:, s:s + 256], rtol=0, atol=1e-12)


def test_check_arrays_fails_loudly():
  y = np.array([201, 202, 101])
  ok = dict(n_channels=7, n_samples=256, conditions=(201, 202, 101))
  rp.check_arrays(np.zeros((3, 217)), np.zeros((3, 7, 256)), y, np.array([0, 1, 2]), **ok)
  with pytest.raises(RuntimeError, match="length mismatch"):
    rp.check_arrays(np.zeros((2, 217)), np.zeros((3, 7, 256)), y, np.array([0, 1, 2]), **ok)
  with pytest.raises(RuntimeError, match="condition order"):
    rp.check_arrays(np.zeros((3, 217)), np.zeros((3, 7, 256)), y[::-1], np.array([0, 1, 2]), **ok)
  with pytest.raises(RuntimeError, match="X_time"):
    rp.check_arrays(np.zeros((3, 217)), np.zeros((3, 8, 256)), y, np.array([0, 1, 2]), **ok)
