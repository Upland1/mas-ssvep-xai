"""Known-answer tests for scripts/exploration/inventory_raw.py (P00).

Every input is a synthetic EBR file written into tmp_path by this module; no
real recording is read. Expected values come from mas/01_DATA_SPEC.md
sections 1-4 (cited as [spec §n]) or are analytic. The EBR writer below uses
its own dtype table copied from [spec §2], not the script's.
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts.exploration import inventory_raw as inv

FS = 256
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "exploration" / "inventory_raw.py"
CHANNELS = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2",
            "TIMESTAMP", "FLASHINGTIME", "MARK"]                      # [spec §2]
T0_MS = 1635456840000                                                 # 2021-10-28 21:34:00 UTC
CAL_N = 154904                                                        # S01 OO [spec §4]

# [spec §2] data_type -> (numpy dtype, bytes). Independent of the script's table.
SPEC_DTYPES = {
  "int8": ("<i1", 1), "char": ("<i1", 1), "uint8": ("<u1", 1), "unsigned char": ("<u1", 1),
  "int16": ("<i2", 2), "short": ("<i2", 2), "uint16": ("<u2", 2), "unsigned short": ("<u2", 2),
  "int32": ("<i4", 4), "int": ("<i4", 4), "uint32": ("<u4", 4), "unsigned int": ("<u4", 4),
  "int64": ("<i8", 8), "__int64": ("<i8", 8), "uint64": ("<u8", 8),
  "unsigned __int64": ("<u8", 8), "float": ("<f4", 4), "double": ("<f8", 8),
  "complex": ("<c16", 16), "class std::complex<double>": ("<c16", 16),
}


# --- synthetic file helpers ---------------------------------------------------

def write_ebr(path, data, channels=CHANNELS, fs=FS, data_type="double", magic="ebr binary 1.0",
              n_channels=None, extra_lines=(), trailing=b"", truncate=0, end_header=True):
  """Write an EBR file per [spec §2]; data is (n_channels, n_samples)."""
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  nc = len(channels) if n_channels is None else n_channels
  lines = [magic, f"data_type {data_type}", f"sampling_rate {fs}", f"samples {data.shape[1]}",
           "bands 1", "band_1 Raw Data", f"channels {nc}"]
  lines += [f"channel_{k} {c}" for k, c in enumerate(channels, 1)]
  lines += ["trials 1", "trial_1 EEG Register", "comments 1", "comment_1 Sample selection",
            "marks 0", *extra_lines]
  if end_header:
    lines.append("end_header")
  dt = SPEC_DTYPES.get(data_type, ("<f8", 8))[0]
  blob = np.ascontiguousarray(data, dtype=dt).tobytes() + trailing
  if truncate:
    blob = blob[:-truncate]
  path.write_bytes(("\n".join(lines) + "\n").encode("ascii") + blob)
  return path


def calibration_mark(n=CAL_N, pulse_len=1, drop=None, extra=None, seed=0):
  """MARK of a calibration run: 40 trials, 8 per target, timing of [spec §3].

  201 at t, 202 at t+2, 203 at t+4, 10x at t+5, 200 at t+10; first 201 at 5.0 s,
  trials every 15 s. `drop=code` removes the first pulse of that code; `extra`
  = (time_s, code) adds one pulse.
  """
  mark = np.zeros(n)
  targets = np.repeat(np.arange(101, 106), 8)
  np.random.default_rng(seed).shuffle(targets)
  dropped = False
  for i, code in enumerate(targets):
    t = 5.0 + 15.0 * i
    for off, c in ((0, 201), (2, 202), (4, 203), (5, int(code)), (10, 200)):
      if drop == c and not dropped:
        dropped = True
        continue
      s = int(round((t + off) * FS))
      mark[s:s + pulse_len] = c
  if extra is not None:
    s = int(round(extra[0] * FS))
    mark[s:s + pulse_len] = extra[1]
  return mark


def recording(n=CAL_N, mark=None, seed=1):
  """(11, n) array: N(0, 10) EEG, TIMESTAMP from T0_MS, FLASHINGTIME 0.005, MARK."""
  rng = np.random.default_rng(seed)
  x = np.zeros((11, n))
  x[:8] = rng.normal(0.0, 10.0, (8, n))
  x[8] = T0_MS + np.arange(n) * 1000.0 / FS
  x[9] = 0.005
  x[10] = calibration_mark(n) if mark is None else mark
  return x


def run(raw, tmp_path, *extra):
  """main() on raw; returns (exit code, rows of the CSV or None if not written)."""
  out = tmp_path / "out" / "inv.csv"
  code = inv.main(["--raw-dir", str(raw), "--out", str(out), *extra])
  rows = list(csv.DictReader(open(out))) if out.exists() else None
  return code, rows


EXPECTED_CAL_COUNTS = "101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40"


# --- clean calibration run ------------------------------------------------------

def test_clean_calibration_run(tmp_path):
  """Known answer [spec §3, §4]: S01/OO with ns 154904 -> samples 154904, duration
  605.1, stim 40, onsets 201/202/203/200 = 40 and 101-105 = 8, no deviation, exit 0.
  Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording())
  code, rows = run(raw, tmp_path)
  assert code == 0
  assert len(rows) == 1
  r = rows[0]
  assert list(r) == ["subject", "file", "samples", "duration_s", "stim_events",
                     "session_start_utc", "p99_abs_eeg_uv", "fs", "n_channels", "channels",
                     "event_counts", "kind", "deviations"]
  assert (r["subject"], r["file"], r["samples"], r["duration_s"], r["stim_events"]) == \
         ("S01", "OO", "154904", "605.1", "40")
  assert r["event_counts"] == EXPECTED_CAL_COUNTS
  assert float(r["fs"]) == 256.0 and r["n_channels"] == "11"
  assert r["channels"].split(";") == CHANNELS
  assert r["kind"] == "calibration"
  assert r["deviations"] == ""


@pytest.mark.parametrize("stem", ["OO", "mOO", "C", "mC"])
def test_all_calibration_stems_are_checked(tmp_path, stem):
  """Known answer [spec §3]: OO, mOO, C, mC are calibration runs; a missing 101 pulse
  is a deviation for each. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / f"{stem}.ebr", recording(mark=calibration_mark(drop=101)))
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert rows[0]["kind"] == "calibration"
  assert "101" in rows[0]["deviations"]


# --- plateau pulses (onset rule) --------------------------------------------------

def _naive_counts(mark):
  """Buggy variant: counts samples equal to each code, `(mark == code).sum()`."""
  m = np.rint(np.asarray(mark, dtype=float)).astype(int)
  return {int(c): int((m == c).sum()) for c in np.unique(m) if c != 0}


def test_plateau_pulses_count_once(tmp_path):
  """Known answer [spec §3 onset rule; 02_REQUIREMENTS §7 "event onsets"]: pulses
  3 samples long give the same counts as single-sample pulses (40/8), exit 0.
  Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "mOO.ebr", recording(mark=calibration_mark(pulse_len=3)))
  code, rows = run(raw, tmp_path)
  assert code == 0
  assert rows[0]["event_counts"] == EXPECTED_CAL_COUNTS
  assert rows[0]["stim_events"] == "40"
  assert rows[0]["deviations"] == ""


def test_plateau_test_fails_on_naive_counter(tmp_path, monkeypatch):
  """Bug guard: with `(mark == code).sum()` swapped in, the plateau file yields
  3x counts (stim 120, 201 = 120) and deviations, so the plateau test above would
  fail on that variant. Known answer: 3 * 40 = 120. Tolerance: exact."""
  path = write_ebr(tmp_path / "raw" / "S01" / "mOO.ebr", recording(mark=calibration_mark(pulse_len=3)))
  monkeypatch.setattr(inv, "event_onset_counts", _naive_counts)
  r = inv.inventory_file(path, "S01")
  assert r["stim_events"] == 120
  assert "201:120" in r["event_counts"]
  assert r["deviations"] != ""


def test_onset_rule_on_small_arrays():
  """Known answer [spec §3]: onset = MARK == code and differs from previous sample.
  [0,5,5,5,0,5,0] -> one plateau + one pulse = 2 onsets of 5; back-to-back codes
  [7,7,8,8] -> 1 onset each (no zero between them); a pulse at sample 0 counts
  (prepend=0). Tolerance: exact."""
  assert inv.event_onset_counts(np.array([0, 5, 5, 5, 0, 5, 0])) == {5: 2}
  assert inv.event_onset_counts(np.array([7, 7, 8, 8, 0])) == {7: 1, 8: 1}
  assert inv.event_onset_counts(np.array([201.0, 0, 0])) == {201: 1}
  assert inv.event_onset_counts(np.zeros(10)) == {}


# --- deviations: exit 1, CSV still written ----------------------------------------

def test_wrong_fs_is_deviation_and_csv_written(tmp_path):
  """Known answer [roadmap P00.2]: header `sampling_rate 250` -> deviation naming fs,
  exit 1; the CSV is still written with the clean S01 row and the bad S02 row.
  Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording())
  write_ebr(raw / "S02" / "OO.ebr", recording(), fs=250)
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert rows is not None and [r["subject"] for r in rows] == ["S01", "S02"]
  assert rows[0]["deviations"] == ""
  assert "fs" in rows[1]["deviations"] and "250" in rows[1]["deviations"]


def test_renamed_channel_is_deviation(tmp_path):
  """Known answer [spec §2, roadmap P00.2]: channel 1 named `Fp1` instead of PO7 ->
  channel-list deviation, exit 1, CSV written. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(), channels=["Fp1"] + CHANNELS[1:])
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert rows is not None and "channels" in rows[0]["deviations"]


def test_ten_channels_is_deviation(tmp_path):
  """Known answer [spec §2]: FLASHINGTIME missing (10 channels, consistent header) ->
  channel-list deviation, exit 1; MARK still found by name so counts are 40/8.
  Tolerance: exact."""
  raw = tmp_path / "raw"
  x = np.delete(recording(), 9, axis=0)
  write_ebr(raw / "S01" / "OO.ebr", x, channels=CHANNELS[:9] + ["MARK"])
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert rows[0]["n_channels"] == "10"
  assert "channels" in rows[0]["deviations"]
  assert rows[0]["event_counts"] == EXPECTED_CAL_COUNTS


def test_missing_trial_is_deviation(tmp_path):
  """Known answer [spec §3]: only 7 pulses of 103 -> `code 103` deviation, stim 39,
  exit 1. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(mark=calibration_mark(drop=103)))
  code, rows = run(raw, tmp_path)
  assert code == 1
  r = rows[0]
  assert "103:7" in r["event_counts"]
  assert r["stim_events"] == "39"
  assert "code 103" in r["deviations"]


def test_unexpected_code_in_calibration_is_deviation(tmp_path):
  """Known answer [spec §3]: calibration runs contain only 200-203 and 101-105; an
  extra pulse of 1001 -> deviation, exit 1. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(mark=calibration_mark(extra=(1.0, 1001))))
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert "1001" in rows[0]["deviations"]


def test_cli_exit_codes_as_subprocess(tmp_path):
  """Known answer [roadmap P00.2]: the script run as a file exits 0 on a clean tree
  and 1 on a deviation (fs 250), writing the CSV in both cases. Tolerance: exact."""
  good, bad = tmp_path / "good", tmp_path / "bad"
  write_ebr(good / "S01" / "OO.ebr", recording())
  write_ebr(bad / "S01" / "OO.ebr", recording(), fs=250)
  for raw, expected in ((good, 0), (bad, 1)):
    out = tmp_path / f"{raw.name}.csv"
    p = subprocess.run([sys.executable, str(SCRIPT), "--raw-dir", str(raw), "--out", str(out)],
                       capture_output=True, text=True, cwd=tmp_path, timeout=120)
    assert p.returncode == expected, p.stdout + p.stderr
    assert out.exists()


# --- online and joined runs ---------------------------------------------------------

def test_online_run(tmp_path):
  """Known answer [spec §3, §4]: online_OO with ns 16728 and 7 pulses in 1001-1005 ->
  kind online, stim 7, duration 65.3, exit 0. Tolerance: exact."""
  n = 16728
  mark = np.zeros(n)
  codes = [1001, 1002, 1003, 1004, 1005, 1001, 1003]
  for i, c in enumerate(codes):
    mark[int((3.0 + 8.0 * i) * FS)] = c
  raw = tmp_path / "raw"
  write_ebr(raw / "S05" / "online_OO.ebr", recording(n=n, mark=mark))
  code, rows = run(raw, tmp_path)
  assert code == 0
  r = rows[0]
  assert (r["kind"], r["stim_events"], r["samples"], r["duration_s"]) == ("online", "7", "16728", "65.3")
  assert r["event_counts"] == "1001:2;1002:1;1003:2;1004:1;1005:1"
  assert r["deviations"] == ""


def test_online_run_with_cue_code_is_deviation(tmp_path):
  """Known answer [spec §3]: online runs hold only 1001-1005; a 202 pulse -> deviation,
  exit 1. Tolerance: exact."""
  n = 16728
  mark = np.zeros(n)
  mark[1000] = 1001
  mark[3000] = 202
  raw = tmp_path / "raw"
  write_ebr(raw / "S05" / "online_OO.ebr", recording(n=n, mark=mark))
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert "202" in rows[0]["deviations"]


def test_joined_run(tmp_path):
  """Known answer [spec §4]: cb_mas_mcb, two calibration runs back to back (309816
  samples) -> kind joined, stim 80, duration 1210.2, exit 0. Tolerance: exact."""
  half = 309816 // 2
  mark = np.concatenate([calibration_mark(half, seed=0), calibration_mark(half, seed=3)])
  raw = tmp_path / "raw"
  write_ebr(raw / "S03" / "cb_mas_mcb.ebr", recording(n=309816, mark=mark))
  code, rows = run(raw, tmp_path)
  assert code == 0
  r = rows[0]
  assert (r["kind"], r["stim_events"], r["samples"], r["duration_s"]) == ("joined", "80", "309816", "1210.2")


# --- durations of every sample count in §4 -------------------------------------------

@pytest.mark.parametrize("n,expected", [(154896, "605.1"), (154904, "605.1"), (154912, "605.1"),
                                        (154920, "605.2"), (30088, "117.5"), (16728, "65.3")])
def test_duration_to_0p1_s(tmp_path, n, expected):
  """Known answer [spec §4]: duration = samples / 256 to 0.1 s for every sample count
  of the inventory (154920 -> 605.156 -> 605.2). File kind `unknown` (MARK all zero,
  warning only, no protocol check). Tolerance: exact string at 0.1 s."""
  x = np.zeros((11, n))
  x[8] = T0_MS
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "X.ebr", x)
  code, rows = run(raw, tmp_path)
  assert code == 0
  assert rows[0]["kind"] == "unknown"
  assert (rows[0]["samples"], rows[0]["duration_s"]) == (str(n), expected)


# --- discovery -----------------------------------------------------------------------

def test_discovery(tmp_path, capsys):
  """Known answer [spec §1]: only folders matching ^S\\d+$ and only *.ebr files.
  Folders S01, S10, S2, S1x, notes, s03 and an empty S04; S01 holds OO.ebr, photo.jpg,
  video.mp4, notes.txt; S1x/notes/s03 hold a valid OO.ebr. Expected rows:
  (S01, OO), (S2, OO), (S10, OO) in numeric order; S04 skipped with a message.
  Tolerance: exact."""
  raw = tmp_path / "raw"
  for s in ("S01", "S10", "S2", "S1x", "notes", "s03"):
    write_ebr(raw / s / "OO.ebr", recording())
  (raw / "S04").mkdir()
  (raw / "S01" / "photo.jpg").write_bytes(b"\xff\xd8\xff")
  (raw / "S01" / "video.mp4").write_bytes(b"\x00" * 16)
  (raw / "S01" / "notes.txt").write_text("not a recording")
  (raw / "S99.ebr").write_bytes(b"stray")                     # file, not a folder
  code, rows = run(raw, tmp_path)
  assert code == 0
  assert [(r["subject"], r["file"]) for r in rows] == [("S01", "OO"), ("S2", "OO"), ("S10", "OO")]
  assert "Skipping S04" in capsys.readouterr().out


def test_subjects_flag_and_empty_tree(tmp_path):
  """Known answer [plan: --subjects; 03_changes deviation 4]: --subjects S02 keeps only
  S02; an existing raw folder with no .ebr file exits 1. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording())
  write_ebr(raw / "S02" / "OO.ebr", recording())
  code, rows = run(raw, tmp_path, "--subjects", "S02")
  assert code == 0 and [r["subject"] for r in rows] == ["S02"]
  empty = tmp_path / "empty"
  (empty / "S01").mkdir(parents=True)
  assert inv.main(["--raw-dir", str(empty), "--out", str(tmp_path / "e.csv")]) == 1
  assert inv.main(["--raw-dir", str(tmp_path / "missing"), "--out", str(tmp_path / "m.csv")]) == 1


# --- session start --------------------------------------------------------------------

def test_session_start(tmp_path):
  """Known answer [spec §4 S01 mC]: TIMESTAMP[0] = 1635456840000 ms -> `2021-10-28 21:34`
  UTC; a later first sample (+59 s) stays in the same minute. Tolerance: exact."""
  assert inv.session_start_utc(1635456840000) == "2021-10-28 21:34"
  assert inv.session_start_utc(1635456840000 + 59_000) == "2021-10-28 21:34"
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "mC.ebr", recording(n=154896, mark=calibration_mark(154896)))
  code, rows = run(raw, tmp_path)
  assert code == 0
  assert rows[0]["session_start_utc"] == "2021-10-28 21:34"


# --- p99 -----------------------------------------------------------------------------------

def test_p99_pooled_over_eeg_only(tmp_path):
  """Known answer [own, analytic]: EEG |x| is a permutation of 0..N-1 (N = 8*ns) with
  random signs spread over the 8 EEG channels -> pooled linear-interpolated 99th
  percentile = 0.99 * (N - 1). TIMESTAMP (~1.6e12), FLASHINGTIME and MARK must not
  enter the pool. Tolerance: 1e-9 relative."""
  n = 2048
  rng = np.random.default_rng(7)
  vals = rng.permutation(8 * n).astype(float) * rng.choice([-1.0, 1.0], 8 * n)
  x = np.zeros((11, n))
  x[:8] = vals.reshape(8, n)
  x[8] = T0_MS
  x[9] = 0.005
  x[10, 100] = 201
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "X.ebr", x)
  code, rows = run(raw, tmp_path)
  assert code == 0
  expected = 0.99 * (8 * n - 1)
  assert float(rows[0]["p99_abs_eeg_uv"]) == pytest.approx(expected, rel=1e-9)
  assert float(rows[0]["p99_abs_eeg_uv"]) == pytest.approx(np.percentile(np.abs(vals), 99), rel=1e-9)


def test_p99_includes_po7(tmp_path):
  """Known answer [plan: pooled over the 8 EEG channels idx 0-7]: only PO7 nonzero
  (|x| = 1000 everywhere), others 0 -> 1/8 of the pool is 1000 -> p99 = 1000.
  A 7-channel pool (PO7 excluded) would give 0. Tolerance: 1e-9."""
  n = 1024
  x = np.zeros((11, n))
  x[0] = -1000.0
  x[8] = T0_MS
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "X.ebr", x)
  code, rows = run(raw, tmp_path)
  assert float(rows[0]["p99_abs_eeg_uv"]) == pytest.approx(1000.0, abs=1e-9)


# --- dtype and header parsing ----------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(SPEC_DTYPES))
def test_dtype_table(name):
  """Known answer [spec §2]: each data_type string maps to the listed numpy kind and
  byte size. Tolerance: exact."""
  dt = inv.ebr_dtype(name)
  assert dt == np.dtype(SPEC_DTYPES[name][0])
  assert dt.itemsize == SPEC_DTYPES[name][1]


def test_bogus_dtype_raises():
  """Known answer [spec §2]: any other data_type raises ValueError. Tolerance: exact."""
  with pytest.raises(ValueError):
    inv.ebr_dtype("bogus")


def test_float32_block_parsed(tmp_path):
  """Known answer [spec §2]: `data_type float` -> float32 block of the same shape;
  values read back equal to the planted float32 values; counts 40/8, exit 0.
  TIMESTAMP = 12477973 * 2**17 = 1635456909312 ms, exact in float32 (spacing 2**17
  at 1.6e12) -> session start 2021-10-28 21:35:09 UTC -> `2021-10-28 21:35`.
  Tolerance: exact."""
  x = recording()
  ts0 = 1635456909312
  assert ts0 % 2**17 == 0 and float(np.float32(ts0)) == ts0
  x[8] = ts0
  x32 = x.astype(np.float32)
  path = write_ebr(tmp_path / "raw" / "S01" / "C.ebr", x32, data_type="float")
  header = inv.parse_ebr_header(path)
  data = inv.open_ebr_data(path, header)
  assert data.shape == (1, 11, 1, CAL_N)
  assert data.dtype == np.float32
  np.testing.assert_array_equal(np.asarray(data[0, :, 0, :]), x32)
  code, rows = run(tmp_path / "raw", tmp_path)
  assert code == 0
  assert rows[0]["event_counts"] == EXPECTED_CAL_COUNTS
  assert rows[0]["session_start_utc"] == "2021-10-28 21:35"


def test_bogus_dtype_file_is_unreadable_deviation(tmp_path):
  """Known answer [spec §2, 03_changes deviation 2a]: a file with `data_type bogus`
  becomes an `unreadable` deviation, exit 1, CSV written. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(), data_type="bogus")
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert rows[0]["deviations"].startswith("unreadable")
  assert "bogus" in rows[0]["deviations"]


def test_header_layout_c_order(tmp_path):
  """Known answer [spec §2, R6]: block reshaped (nt, nc, nb, ns) C order; channel c
  is data[0, c, 0, :]. Channel c planted as c*1000 + sample index. Tolerance: exact."""
  n = 50
  x = np.arange(11)[:, None] * 1000.0 + np.arange(n)[None, :]
  path = write_ebr(tmp_path / "f.ebr", x)
  h = inv.parse_ebr_header(path)
  d = inv.open_ebr_data(path, h)
  for c in range(11):
    np.testing.assert_array_equal(np.asarray(d[0, c, 0, :]), c * 1000.0 + np.arange(n))
  assert h["channels"] == CHANNELS
  assert (h["sampling_rate"], h["number_of_samples"], h["number_of_channels"]) == (256.0, n, 11)


def test_header_blank_lines_unknown_keys_and_magic_case(tmp_path):
  """Known answer [spec §2]: blank lines skipped, unknown keys ignored, magic compared
  case-insensitively after strip -> `EBR Binary 1.0  ` with a blank line and
  `operator X` is clean (exit 0); magic `foo binary 2.0` is a deviation. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(), magic="EBR Binary 1.0  ",
            extra_lines=("", "operator X", ""))
  code, rows = run(raw, tmp_path)
  assert code == 0, rows[0]["deviations"]
  raw2 = tmp_path / "raw2"
  write_ebr(raw2 / "S01" / "OO.ebr", recording(), magic="foo binary 2.0")
  code, rows = run(raw2, tmp_path)
  assert code == 1 and "magic" in rows[0]["deviations"]


# --- builder's additional hard checks ------------------------------------------------------

def test_trailing_bytes_is_deviation(tmp_path):
  """Known answer [spec §2 block size; 03_changes deviation 2c]: 8 bytes appended after
  the block -> deviation naming 8 bytes, exit 1. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(), trailing=b"\x00" * 8)
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert "8 bytes" in rows[0]["deviations"]


def test_channel_count_mismatch_is_deviation(tmp_path):
  """Known answer [03_changes deviation 2b]: header `channels 11` with only 10
  `channel_k` lines (FLASHINGTIME line missing) -> deviation, exit 1. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(), channels=CHANNELS[:9] + ["MARK"], n_channels=11)
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert "declares 11 channels" in rows[0]["deviations"]


def test_non_integer_mark_is_deviation(tmp_path):
  """Known answer [03_changes deviation 2d]: one MARK sample = 0.5 -> deviation,
  exit 1. Tolerance: exact."""
  mark = calibration_mark()
  mark[10] = 0.5
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(mark=mark))
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert "non-integer" in rows[0]["deviations"]


@pytest.mark.parametrize("kind", ["truncated", "no_end_header"])
def test_unreadable_file_is_deviation(tmp_path, kind):
  """Known answer [spec §2; 03_changes deviation 2a]: a block 100 bytes short of the
  declared size, or a header without `end_header`, -> `unreadable` deviation, no
  crash, exit 1, CSV written with the other subject's clean row. Tolerance: exact."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording())
  if kind == "truncated":
    write_ebr(raw / "S02" / "OO.ebr", recording(), truncate=100)
  else:
    write_ebr(raw / "S02" / "OO.ebr", np.zeros((11, 4)), end_header=False)
  code, rows = run(raw, tmp_path)
  assert code == 1
  assert [r["subject"] for r in rows] == ["S01", "S02"]
  assert rows[0]["deviations"] == ""
  assert rows[1]["deviations"].startswith("unreadable")


# --- Round 2: anchored subject discovery and module form ----------------------------------

DECOY_FOLDERS = ("S01x", "S01_old", "S01 copy", "xS01", "S01\n")


def _discover_with(pattern_match):
  """Buggy-variant discovery: the script's rule with `pattern_match(name)` swapped in."""
  def discover(raw_dir):
    return sorted(p.name for p in Path(raw_dir).iterdir() if p.is_dir() and pattern_match(p.name))
  return discover


def test_decoy_subject_folders_not_discovered(tmp_path):
  """Known answer [spec §1: subjects match ^S\\d+$ as the whole name]: among S01, S02 and
  the decoys S01x, S01_old, `S01 copy`, xS01 and `S01<newline>` (each holding a valid
  OO.ebr), only S01 and S02 are discovered and inventoried; exit 0. Tolerance: exact."""
  raw = tmp_path / "raw"
  for s in ("S01", "S02") + DECOY_FOLDERS:
    write_ebr(raw / s / "OO.ebr", recording())
  assert inv.discover_subjects(raw) == ["S01", "S02"]
  code, rows = run(raw, tmp_path)
  assert code == 0
  assert [(r["subject"], r["file"]) for r in rows] == [("S01", "OO"), ("S02", "OO")]


def test_decoy_folders_catch_unanchored_and_dollar_variants(tmp_path):
  """Bug guard: the decoy set is discriminating. An unanchored `re.match(r"S\\d+")`
  accepts S01x, S01_old, `S01 copy` and `S01<newline>`; the pre-Round-2
  `re.match(r"^S\\d+$")` accepts `S01<newline>` (`$` matches before a trailing newline).
  Either variant fails test_decoy_subject_folders_not_discovered. Tolerance: exact."""
  raw = tmp_path / "raw"
  for s in ("S01",) + DECOY_FOLDERS:
    (raw / s).mkdir(parents=True)
  unanchored = _discover_with(lambda n: re.match(r"S\d+", n))(raw)
  assert set(unanchored) == {"S01", "S01x", "S01_old", "S01 copy", "S01\n"}
  dollar = _discover_with(lambda n: re.match(r"^S\d+$", n))(raw)
  assert set(dollar) == {"S01", "S01\n"}
  assert inv.discover_subjects(raw) == ["S01"]


def test_cli_module_form(tmp_path):
  """Known answer [plan: runs as file and as module, 02_REQUIREMENTS §4]:
  `python -m scripts.exploration.inventory_raw --raw-dir <tmp> --out <tmp>` from the
  repo root exits 0 on a clean S01/OO and writes a 1-row CSV with samples 154904 and
  stim 40; on an fs-250 tree it exits 1 and still writes the CSV. Tolerance: exact."""
  good, bad = tmp_path / "good", tmp_path / "bad"
  write_ebr(good / "S01" / "OO.ebr", recording())
  write_ebr(bad / "S01" / "OO.ebr", recording(), fs=250)
  for raw, expected in ((good, 0), (bad, 1)):
    out = tmp_path / f"{raw.name}_module.csv"
    p = subprocess.run([sys.executable, "-m", "scripts.exploration.inventory_raw",
                        "--raw-dir", str(raw), "--out", str(out)],
                       capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert p.returncode == expected, p.stdout + p.stderr
    rows = list(csv.DictReader(open(out)))
    assert [(r["subject"], r["file"], r["samples"], r["stim_events"]) for r in rows] == \
           [("S01", "OO", "154904", "40")]
