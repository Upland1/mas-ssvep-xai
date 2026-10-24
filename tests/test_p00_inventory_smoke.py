"""Builder smoke tests for scripts/exploration/inventory_raw.py (synthetic files only).

The independent known-answer suite is written by the synthetic-tester.
"""

import csv

import numpy as np

from scripts.exploration import inventory_raw as inv

FS = 256


def _write_ebr(path, channels, data, fs=FS, data_type="double", magic="ebr binary 1.0"):
  """Write a synthetic EBR file; data is (n_channels, n_samples)."""
  lines = [magic, f"data_type {data_type}", f"sampling_rate {fs}", f"samples {data.shape[1]}",
           "bands 1", "band_1 Raw Data", f"channels {len(channels)}"]
  lines += [f"channel_{k} {c}" for k, c in enumerate(channels, 1)]
  lines += ["trials 1", "trial_1 EEG Register", "comments 1", "comment_1 Sample selection",
            "marks 0", "end_header"]
  dtype = inv.ebr_dtype(data_type)
  with open(path, "wb") as f:
    f.write(("\n".join(lines) + "\n").encode("ascii"))
    f.write(np.ascontiguousarray(data, dtype=dtype).tobytes())


def _calibration_mark(n_samples, missing_103=False):
  """40 trials, 8 per target, timing of 01_DATA_SPEC.md section 3 (single-sample pulses)."""
  mark = np.zeros(n_samples)
  targets = np.repeat(np.arange(101, 106), 8)
  np.random.default_rng(0).shuffle(targets)
  dropped = False
  for i, code in enumerate(targets):
    t = 5.0 + 15.0 * i
    for offset, c in ((0, 201), (2, 202), (4, 203), (5, code), (10, 200)):
      if missing_103 and c == 103 and not dropped:
        dropped = True
        continue
      mark[int(round((t + offset) * FS))] = c
  return mark


def _recording(n_samples=154904, **kw):
  rng = np.random.default_rng(1)
  x = np.zeros((11, n_samples))
  x[:8] = rng.normal(0, 10, (8, n_samples))
  x[8] = 1635456840000 + np.arange(n_samples) * 1000 / FS
  x[9] = 0.005
  x[10] = _calibration_mark(n_samples, **kw)
  return x


def test_clean_calibration_run_exits_zero(tmp_path):
  (tmp_path / "S01").mkdir()
  _write_ebr(tmp_path / "S01" / "OO.ebr", inv.EXPECTED_CHANNELS, _recording())
  out = tmp_path / "inv.csv"
  assert inv.main(["--raw-dir", str(tmp_path), "--out", str(out)]) == 0
  rows = list(csv.DictReader(open(out)))
  assert len(rows) == 1
  r = rows[0]
  assert (r["subject"], r["file"], r["samples"], r["duration_s"], r["stim_events"]) == \
         ("S01", "OO", "154904", "605.1", "40")
  assert r["session_start_utc"] == "2021-10-28 21:34"
  assert r["deviations"] == ""


def test_missing_trial_is_a_deviation(tmp_path):
  (tmp_path / "S01").mkdir()
  _write_ebr(tmp_path / "S01" / "OO.ebr", inv.EXPECTED_CHANNELS, _recording(missing_103=True))
  out = tmp_path / "inv.csv"
  assert inv.main(["--raw-dir", str(tmp_path), "--out", str(out)]) == 1
  r = next(csv.DictReader(open(out)))
  assert "code 103: 7 onsets, expected 8" in r["deviations"]
