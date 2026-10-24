"""Builder smoke tests for src/io/ebr_parser.py and src/preprocessing/signal/filters.py.

Synthetic files only (written to tmp_path); the known-answer suite of P01 is separate.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml
from scipy.signal import filtfilt, iirfilter

from src.io import ebr_parser as ep
from src.preprocessing.signal.filters import apply_iir_bandpass

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2", "TIMESTAMP", "FLASHINGTIME", "MARK"]


def _write(path, block, channels, data_type="double", magic="ebr binary 1.0", marks=(),
           extra=b"", cut=0, declared_channels=None):
  """EBR file with a (nt, nc, nb, ns) block; returns the path."""
  nt, nc, nb, ns = block.shape
  lines = [magic, f"data_type {data_type}", "sampling_rate 256", f"samples {ns}", f"bands {nb}"]
  lines += [f"band_{k} B{k}" for k in range(1, nb + 1)]
  lines += [f"channels {declared_channels or nc}"] + [f"channel_{k} {c}" for k, c in enumerate(channels, 1)]
  lines += [f"trials {nt}"] + [f"trial_{k} T{k}" for k in range(1, nt + 1)]
  lines += ["comments 1", "comment_1 Sample selection", f"marks {len(marks)}"]
  lines += [f"mark_{k} {i} {lab}" for k, (i, lab) in enumerate(marks, 1)] + ["end_header"]
  dt = np.dtype(ep.EBR_DTYPES.get(data_type, "<f8"))
  blob = np.ascontiguousarray(block, dtype=dt).tobytes() + extra
  if cut:
    blob = blob[:-cut]
  path.write_bytes(("\n".join(lines) + "\n").encode("ascii") + blob)
  return path


def _coded_block(nt, nc, nb, ns):
  t, c, b, s = np.meshgrid(*(np.arange(k) for k in (nt, nc, nb, ns)), indexing="ij")
  return (1000 * t + 100 * c + 10 * b + s).astype(np.float64)


def test_load_returns_spec_keys_and_c_order_layout(tmp_path):
  block = _coded_block(2, 3, 2, 5)
  p = _write(tmp_path / "f.ebr", block, ["A", "B", "C"], marks=[(10, "start"), (20, "stop")])
  rec = ep.load_ebr_file(p)
  assert tuple(rec) == ep.RECORDING_KEYS
  assert rec["data"].shape == (2, 3, 2, 5) and rec["data"].dtype == np.float64
  np.testing.assert_array_equal(rec["data"], block)
  assert rec["channels"] == ["A", "B", "C"] and rec["sampling_rate"] == 256.0
  assert rec["marks"] == [(10, "start"), (20, "stop")]


@pytest.mark.parametrize("data_type", sorted(ep.EBR_DTYPES))
def test_every_dtype_reads_and_casts(tmp_path, data_type):
  block = np.arange(11 * 4, dtype=np.float64).reshape(1, 11, 1, 4)
  rec = ep.load_ebr_file(_write(tmp_path / "f.ebr", block, CHANNELS, data_type=data_type))
  expected = np.complex128 if "complex" in data_type else np.float64
  assert rec["data"].dtype == expected
  np.testing.assert_array_equal(rec["data"].real, block)


@pytest.mark.parametrize("case", ["bogus", "truncated", "magic", "names", "trailing"])
def test_loud_failures(tmp_path, case):
  block = _coded_block(1, 11, 1, 50)
  kw = {"bogus": {"data_type": "bogus"}, "truncated": {"cut": 8}, "magic": {"magic": "foo 2.0"},
        "names": {"declared_channels": 12}, "trailing": {"extra": b"\0" * 8}}[case]
  p = _write(tmp_path / "f.ebr", block, CHANNELS, **kw)
  with pytest.raises(ValueError):
    ep.load_ebr_file(p)
  if case in ("magic", "trailing"):
    ep.load_ebr_file(p, strict=False)


def test_helpers(tmp_path):
  shuffled = ["MARK", "O2", "PO3", "Oz", "TIMESTAMP", "O1", "PO8", "POz", "PO4", "PO7", "FLASHINGTIME"]
  assert ep.select_scalp_channels(shuffled, ["PO3", "O2"]) == [2, 1]
  with pytest.raises(ValueError):
    ep.select_scalp_channels(shuffled, ["Cz"])
  assert ep.get_mark_channel_index(shuffled) == 0
  assert ep.get_mark_channel_index(CHANNELS[:-1]) == -1
  (tmp_path / "S01").mkdir()
  (tmp_path / "S01" / "OO.ebr").write_bytes(b"")
  assert ep.resolve_recording_path(tmp_path, "S01", "OO") == tmp_path / "S01" / "OO.ebr"
  with pytest.raises(FileNotFoundError):
    ep.resolve_recording_path(tmp_path, "S01", "mOO.ebr")


def test_extract_scalp_signal_with_config_v1(tmp_path):
  cfg = yaml.safe_load(open(ROOT / "configs" / "pipeline_config.yaml"))
  scalp = cfg["channels"]["scalp"]
  block = _coded_block(1, 11, 1, 30)
  rec = ep.load_ebr_file(_write(tmp_path / "f.ebr", block, CHANNELS))
  x, names = ep.extract_scalp_signal(rec, scalp)
  assert names == scalp and "PO7" not in names and x.shape == (7, 30)
  for row, name in zip(x, names):
    np.testing.assert_array_equal(row, block[0, CHANNELS.index(name), 0])


def test_bandpass_equals_formula_and_requires_fs():
  x = np.random.default_rng(0).normal(size=(2, 3, 1024))
  b, a = iirfilter(4, [1 / 128, 60 / 128], btype="bandpass", ftype="butter")
  np.testing.assert_allclose(apply_iir_bandpass(x, 256.0), filtfilt(b, a, x, axis=-1), atol=1e-12)
  with pytest.raises(TypeError):
    apply_iir_bandpass(x)  # fs has no default (PF-04)
  with pytest.raises(ValueError):
    apply_iir_bandpass(x, 100.0)  # highcut 60 >= Nyquist 50


def test_dtype_match_is_exact():
  assert ep.ebr_dtype("double") == np.float64
  for bad in ("Double", "DOUBLE", " double"):
    with pytest.raises(ValueError):
      ep.ebr_dtype(bad)


def test_strict_rejects_repeated_channel_line(tmp_path):
  block = _coded_block(1, 3, 1, 4)
  p = _write(tmp_path / "f.ebr", block, ["A", "B", "C"])
  p.write_bytes(p.read_bytes().replace(b"channel_3 C\n", b"channel_3 C\nchannel_3 D\n"))
  with pytest.raises(ValueError, match="repeated"):
    ep.load_ebr_file(p)
  assert ep.load_ebr_file(p, strict=False)["channels"] == ["A", "B", "D"]


def test_inventory_strict_flag(tmp_path):
  from scripts.exploration import inventory_raw as inv
  from tests import test_p00_inventory_known_answer as ka
  raw = tmp_path / "raw"
  ka.write_ebr(raw / "S01" / "OO.ebr", ka.recording())
  outs = {}
  for flag in ([], ["--strict"]):
    out = tmp_path / f"inv{len(flag)}.csv"
    assert inv.main(["--raw-dir", str(raw), "--out", str(out), *flag]) == 0
    outs[len(flag)] = out.read_bytes()
  assert outs[0] == outs[1]
  p = raw / "S01" / "OO.ebr"
  p.write_bytes(p.read_bytes().replace(b"comment_1 Sample selection\n", b"", 1))
  assert inv.main(["--raw-dir", str(raw), "--out", str(tmp_path / "a.csv")]) == 0
  out = tmp_path / "b.csv"
  assert inv.main(["--raw-dir", str(raw), "--out", str(out), "--strict"]) == 1
  row = list(inv.csv.DictReader(open(out)))[0]
  assert row["deviations"].startswith("unreadable:") and "comment" in row["deviations"]
