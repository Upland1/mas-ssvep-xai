"""Known-answer tests for P01 Round 2 (07_review.md required fix 2).

(a) `inventory_raw.py --strict` on a spec-conformant synthetic tree writes a CSV
byte-identical to the run without the flag; both exit 0.
(b) A header with `comments 1` but no `comment_1` line, or `bands 1` but no
`band_1` line: `--strict` exits 1 with an `unreadable:` deviation naming the
list, while the run without the flag exits 0. A mutation check shows (b) fails
on an inventory that parses `--strict` but never passes it to the parser.
Plus: exact `data_type` matching ([spec §2] "any other value raises
ValueError") and repeated header lines (strict raises, non-strict keeps last).

Synthetic files only, written with the P00 known-answer writers (calibration
protocol of [spec §3]) into tmp_path. No real recording is read.
"""

import csv
import subprocess
import sys

import numpy as np
import pytest

from scripts.exploration import inventory_raw as inv
from src.io import ebr_parser as ep
from tests.test_p00_inventory_known_answer import recording, write_ebr

ROOT = inv.ROOT
SCRIPT = ROOT / "scripts" / "exploration" / "inventory_raw.py"
SPEC_STRINGS = ["int8", "char", "uint8", "unsigned char", "int16", "short", "uint16",
                "unsigned short", "int32", "int", "uint32", "unsigned int", "int64", "__int64",
                "uint64", "unsigned __int64", "float", "double", "complex",
                "class std::complex<double>"]                          # [spec §2], 20 strings


def _clean_tree(raw):
  """Spec-conformant tree: S01/OO, S01/mOO, S02/OO, all calibration runs."""
  write_ebr(raw / "S01" / "OO.ebr", recording(seed=1))
  write_ebr(raw / "S01" / "mOO.ebr", recording(seed=2))
  write_ebr(raw / "S02" / "OO.ebr", recording(seed=3))


def _drop_header_line(path, line):
  """Remove one exact header line (bytes before end_header only)."""
  blob = path.read_bytes()
  cut = blob.index(b"\nend_header\n")
  head, rest = blob[:cut + 1], blob[cut + 1:]
  target = b"\n" + line.encode("ascii") + b"\n"
  assert head.count(target) == 1
  path.write_bytes(head.replace(target, b"\n") + rest)


def _run(raw, out, *extra):
  code = inv.main(["--raw-dir", str(raw), "--out", str(out), *extra])
  rows = list(csv.DictReader(open(out))) if out.exists() else None
  return code, rows


# ---------------------------------------------------------------- (a)

def test_strict_flag_clean_tree_byte_identical(tmp_path):
  """Known answer (fix 2a): on a spec-conformant tree, `--strict` and the default
  run both exit 0, with no deviation, and the two CSVs are byte-identical."""
  raw = tmp_path / "raw"
  _clean_tree(raw)
  c0, rows0 = _run(raw, tmp_path / "plain.csv")
  c1, rows1 = _run(raw, tmp_path / "strict.csv", "--strict")
  assert (c0, c1) == (0, 0)
  assert len(rows0) == 3 and all(r["deviations"] == "" for r in rows0)
  assert (tmp_path / "plain.csv").read_bytes() == (tmp_path / "strict.csv").read_bytes()


def test_strict_flag_clean_tree_subprocess(tmp_path):
  """Same as (a) through the command line (script run as a file): both exit 0,
  CSVs byte-identical."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(seed=1))
  codes = []
  for name, extra in (("plain.csv", []), ("strict.csv", ["--strict"])):
    p = subprocess.run([sys.executable, str(SCRIPT), "--raw-dir", str(raw),
                        "--out", str(tmp_path / name), *extra],
                       capture_output=True, text=True, cwd=ROOT)
    codes.append(p.returncode)
  assert codes == [0, 0]
  assert (tmp_path / "plain.csv").read_bytes() == (tmp_path / "strict.csv").read_bytes()


# ---------------------------------------------------------------- (b)

CASES = [("comment_1 Sample selection", "comment"), ("band_1 Raw Data", "band")]


@pytest.mark.parametrize("line, listname", CASES)
def test_strict_flag_missing_list_line(tmp_path, line, listname):
  """Known answer (fix 2b): S01/OO with `<list> 1` declared but its `_1` line
  removed. Without the flag: exit 0, no deviation. With `--strict`: exit 1, the
  file's row has an `unreadable:` deviation naming the list; a clean S02/OO in
  the same tree stays clean in both runs."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(seed=1))
  write_ebr(raw / "S02" / "OO.ebr", recording(seed=3))
  _drop_header_line(raw / "S01" / "OO.ebr", line)
  c0, rows0 = _run(raw, tmp_path / "plain.csv")
  assert c0 == 0 and all(r["deviations"] == "" for r in rows0)
  c1, rows1 = _run(raw, tmp_path / "strict.csv", "--strict")
  assert c1 == 1
  by = {(r["subject"], r["file"]): r for r in rows1}
  dev = by[("S01", "OO")]["deviations"]
  assert dev.startswith("unreadable:") and listname in dev
  assert by[("S02", "OO")]["deviations"] == ""


@pytest.mark.parametrize("line, listname", CASES)
def test_strict_flag_dropped_variant_is_caught(tmp_path, monkeypatch, line, listname):
  """Mutation check: an inventory that parses `--strict` but never passes it to the
  parser (inventory_file patched to ignore its `strict` argument) exits 0 with no
  deviation under `--strict`, so the assertions of the test above fail on it."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(seed=1))
  _drop_header_line(raw / "S01" / "OO.ebr", line)
  real = inv.inventory_file
  monkeypatch.setattr(inv, "inventory_file", lambda path, subject, strict=False: real(path, subject))
  code, rows = _run(raw, tmp_path / "strict.csv", "--strict")
  assert code == 0 and rows[0]["deviations"] == ""
  with pytest.raises(AssertionError):
    assert code == 1 and rows[0]["deviations"].startswith("unreadable:")


def test_strict_flag_missing_comment_subprocess(tmp_path):
  """(b) through the command line: missing `comment_1` -> exit 0 without the flag,
  exit 1 with `--strict` and an `unreadable:` DEVIATION line on the console."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(seed=1))
  _drop_header_line(raw / "S01" / "OO.ebr", "comment_1 Sample selection")
  base = [sys.executable, str(SCRIPT), "--raw-dir", str(raw), "--out", str(tmp_path / "o.csv")]
  p0 = subprocess.run(base, capture_output=True, text=True, cwd=ROOT)
  p1 = subprocess.run(base + ["--strict"], capture_output=True, text=True, cwd=ROOT)
  assert p0.returncode == 0
  assert p1.returncode == 1 and "DEVIATION S01/OO: unreadable:" in p1.stdout


# ---------------------------------------------------------------- exact data_type

@pytest.mark.parametrize("s", SPEC_STRINGS)
def test_ebr_dtype_accepts_every_spec_string(s):
  """Known answer [spec §2]: every one of the 20 strings, written exactly, is accepted."""
  assert isinstance(ep.ebr_dtype(s), np.dtype)


@pytest.mark.parametrize("s", ["Double", "DOUBLE", " double", "double ", "Float", "INT",
                               "unsigned  int", "Complex", "class std::complex<Double>"])
def test_ebr_dtype_exact_match(s):
  """Known answer [spec §2] "any other value raises ValueError": case or whitespace
  variants of a table string are other values."""
  with pytest.raises(ValueError):
    ep.ebr_dtype(s)


@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("s", ["Double", "DOUBLE", "unsigned  int"])
def test_file_with_case_variant_dtype_raises(tmp_path, s, strict):
  """A file whose header says `data_type Double` (etc.) raises ValueError in both modes."""
  path = write_ebr(tmp_path / "d.ebr", np.zeros((11, 4)), data_type=s)
  with pytest.raises(ValueError):
    ep.load_ebr_file(path, strict=strict)


def test_inventory_case_variant_dtype_is_unreadable(tmp_path):
  """The inventory reports `data_type Double` as `unreadable:` without the flag (exit 1)."""
  raw = tmp_path / "raw"
  write_ebr(raw / "S01" / "OO.ebr", recording(seed=1), data_type="Double")
  code, rows = _run(raw, tmp_path / "o.csv")
  assert code == 1 and rows[0]["deviations"].startswith("unreadable:")


# ---------------------------------------------------------------- repeated lines

def _write_raw(path, header_lines, values):
  head = "\n".join(header_lines + ["end_header"]) + "\n"
  path.write_bytes(head.encode("ascii") + np.asarray(values, dtype="<f8").tobytes())
  return path


BASE = ["ebr binary 1.0", "data_type double", "sampling_rate 256", "bands 1", "band_1 B",
        "trials 1", "trial_1 T", "comments 0", "marks 0"]


@pytest.mark.parametrize("dup", ["channel_2 C", "channel_02 C"])
def test_repeated_channel_line(tmp_path, dup):
  """Known answer [own, 07_review note 4]: `channel_2` given twice (also as
  `channel_02`, same index 2) -> strict ValueError; non-strict keeps the last
  value: channels ['A', 'C']."""
  lines = BASE + ["samples 2", "channels 2", "channel_1 A", "channel_2 B", dup]
  path = _write_raw(tmp_path / "r.ebr", lines, [1, 2, 3, 4])
  with pytest.raises(ValueError):
    ep.load_ebr_file(path, strict=True)
  rec = ep.load_ebr_file(path, strict=False)
  assert rec["channels"] == ["A", "C"]
  np.testing.assert_array_equal(rec["data"][0, :, 0, :], [[1, 2], [3, 4]])


def test_repeated_scalar_line(tmp_path):
  """Known answer [own]: `samples 2` then `samples 3` -> strict ValueError; non-strict
  keeps the last value (ns = 3) and reads a (1, 2, 1, 3) block exactly."""
  lines = BASE + ["samples 2", "channels 2", "channel_1 A", "channel_2 B", "samples 3"]
  path = _write_raw(tmp_path / "s.ebr", lines, [0, 1, 2, 10, 11, 12])
  with pytest.raises(ValueError):
    ep.load_ebr_file(path, strict=True)
  rec = ep.load_ebr_file(path, strict=False)
  assert rec["number_of_samples"] == 3
  np.testing.assert_array_equal(rec["data"][0, :, 0, :], [[0, 1, 2], [10, 11, 12]])


def test_no_repeat_parses_in_strict(tmp_path):
  """Control: the same header without the repeat parses in strict mode."""
  lines = BASE + ["samples 2", "channels 2", "channel_1 A", "channel_2 B"]
  path = _write_raw(tmp_path / "ok.ebr", lines, [1, 2, 3, 4])
  assert ep.load_ebr_file(path, strict=True)["channels"] == ["A", "B"]
