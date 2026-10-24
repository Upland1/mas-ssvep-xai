"""Known-answer tests for src/io/ebr_parser.py (P01.1, P01.4).

Every input is a synthetic EBR file written into tmp_path by this module's own
writer; no real recording is read. Expected values come from
mas/01_DATA_SPEC.md section 2 ([spec §2]), the plan's helper semantics
(02_plan.md, [plan]) or analytic encoding. The writer uses its own dtype table
copied from [spec §2], never the parser's, and builds the binary block with
`struct` so the byte layout does not depend on numpy's reshape.
"""

import struct
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.io import ebr_parser as ep

ROOT = Path(__file__).resolve().parents[1]
FS = 256
CHANNELS = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2",
            "TIMESTAMP", "FLASHINGTIME", "MARK"]                       # [spec §2]
KEYS = {"data_type", "sampling_rate", "number_of_trials", "trials", "number_of_channels",
        "channels", "number_of_bands", "bands", "number_of_samples", "number_of_comments",
        "comments", "number_of_marks", "marks", "data"}                # [spec §2], 14 keys

# [spec §2] data_type -> (struct format char, bytes, expected parsed numpy dtype).
SPEC_DTYPES = {
  "int8": ("b", 1, np.float64), "char": ("b", 1, np.float64),
  "uint8": ("B", 1, np.float64), "unsigned char": ("B", 1, np.float64),
  "int16": ("h", 2, np.float64), "short": ("h", 2, np.float64),
  "uint16": ("H", 2, np.float64), "unsigned short": ("H", 2, np.float64),
  "int32": ("i", 4, np.float64), "int": ("i", 4, np.float64),
  "uint32": ("I", 4, np.float64), "unsigned int": ("I", 4, np.float64),
  "int64": ("q", 8, np.float64), "__int64": ("q", 8, np.float64),
  "uint64": ("Q", 8, np.float64), "unsigned __int64": ("Q", 8, np.float64),
  "float": ("f", 4, np.float64), "double": ("d", 8, np.float64),
  "complex": ("dd", 16, np.complex128), "class std::complex<double>": ("dd", 16, np.complex128),
}

# Values exactly representable in the file type and in float64 (analytic).
DTYPE_VALUES = {
  "b": [-128, -1, 0, 1, 127], "B": [0, 1, 128, 254, 255],
  "h": [-32768, -2, 0, 3, 32767], "H": [0, 1, 40000, 65534, 65535],
  "i": [-2**31, -5, 0, 7, 2**31 - 1], "I": [0, 9, 2**31, 2**32 - 2, 2**32 - 1],
  "q": [-2**53, -11, 0, 13, 2**53], "Q": [0, 17, 2**40, 2**52, 2**53],
  "f": [-1.5, 0.0, 0.25, 3.0e5, 0.1], "d": [-1.0e300, -0.1, 0.0, 1.0 / 3.0, 6.02e23],
}
COMPLEX_VALUES = [complex(1.0, -2.0), complex(0.0, 0.5), complex(-3.25, 0.0),
                  complex(1e10, 1e-10), complex(0.0, 0.0)]


def _pack(values, data_type):
  """Little-endian bytes of a flat value list in the [spec §2] type (struct, not numpy)."""
  fmt = SPEC_DTYPES[data_type][0] if data_type in SPEC_DTYPES else "d"
  if fmt == "dd":
    return b"".join(struct.pack("<dd", v.real, v.imag) for v in values)
  return b"".join(struct.pack("<" + fmt, v) for v in values)


def write_ebr(path, flat_values, nt, nc, nb, ns, channels=None, data_type="double",
              fs="256", magic="ebr binary 1.0", marks=(), comments=("Sample selection",),
              extra_lines=(), cut_bytes=0, trailing=b""):
  """Write an EBR file whose block is `flat_values` in file order; returns the path."""
  channels = list(channels) if channels is not None else [f"CH{k}" for k in range(1, nc + 1)]
  lines = [magic, f"data_type {data_type}", f"sampling_rate {fs}", f"samples {ns}",
           f"bands {nb}"] + [f"band_{k} Band {k}" for k in range(1, nb + 1)]
  lines += [f"channels {nc}"] + [f"channel_{k} {c}" for k, c in enumerate(channels, 1)]
  lines += [f"trials {nt}"] + [f"trial_{k} Trial {k}" for k in range(1, nt + 1)]
  lines += [f"comments {len(comments)}"] + [f"comment_{k} {c}" for k, c in enumerate(comments, 1)]
  lines += [f"marks {len(marks)}"] + [f"mark_{k} {i} {lab}" for k, (i, lab) in enumerate(marks, 1)]
  lines += list(extra_lines) + ["end_header"]
  blob = _pack(flat_values, data_type) + trailing
  if cut_bytes:
    blob = blob[:-cut_bytes]
  path.write_bytes(("\n".join(lines) + "\n").encode("ascii") + blob)
  return path


def coded_flat(nt, nc, nb, ns):
  """File-order values of a C-order (nt, nc, nb, ns) block: code(t,c,b,s) = 1000t+100c+10b+s."""
  return [1000 * t + 100 * c + 10 * b + s
          for t in range(nt) for c in range(nc) for b in range(nb) for s in range(ns)]


def assert_layout(data, nt, nc, nb, ns):
  """Every element data[t, c, b, s] equals its code (R6)."""
  assert data.shape == (nt, nc, nb, ns)
  for t in range(nt):
    for c in range(nc):
      for b in range(nb):
        for s in range(ns):
          assert data[t, c, b, s] == 1000 * t + 100 * c + 10 * b + s, (t, c, b, s)


# ---------------------------------------------------------------- round trip

def _roundtrip_file(tmp_path, ns=1000):
  flat = [1000 * c + t for c in range(11) for t in range(ns)]
  marks = [(1280, "201"), (1792, "202")]
  path = write_ebr(tmp_path / "rt.ebr", flat, 1, 11, 1, ns, channels=CHANNELS, marks=marks,
                   comments=("Sample selection", "Data Manipulation - Join Time-Series"))
  return path, marks


def test_roundtrip_keys_shape_values(tmp_path):
  """Known answer [spec §2]: nt=1, nc=11, nb=1, ns=1000 doubles with channel c sample t
  = 1000*c + t parse to exactly the 14 keys, data shape (1, 11, 1, 1000) float64 and
  data[0, c, 0, t] == 1000*c + t; header lists equal what was written. Exact."""
  path, marks = _roundtrip_file(tmp_path)
  rec = ep.load_ebr_file(path)
  assert set(rec) == KEYS
  d = rec["data"]
  assert d.shape == (1, 11, 1, 1000) and d.dtype == np.float64
  c, t = np.meshgrid(np.arange(11), np.arange(1000), indexing="ij")
  np.testing.assert_array_equal(d[0, :, 0, :], 1000 * c + t)
  assert rec["channels"] == CHANNELS and rec["number_of_channels"] == 11
  assert rec["sampling_rate"] == 256.0 and isinstance(rec["sampling_rate"], float)
  assert rec["number_of_samples"] == 1000 and rec["number_of_trials"] == 1
  assert rec["number_of_bands"] == 1 and rec["bands"] == ["Band 1"]
  assert rec["trials"] == ["Trial 1"] and rec["data_type"] == "double"
  assert rec["number_of_comments"] == 2
  assert rec["comments"] == ["Sample selection", "Data Manipulation - Join Time-Series"]
  assert rec["number_of_marks"] == 2
  assert [(int(i), str(l)) for i, l in rec["marks"]] == marks


def test_roundtrip_fractional_fs(tmp_path):
  """Known answer [spec §2]: sampling_rate is a float; 'sampling_rate 250.5' -> 250.5."""
  path = write_ebr(tmp_path / "fs.ebr", [0.0] * 4, 1, 2, 1, 2, fs="250.5")
  assert ep.load_ebr_file(path)["sampling_rate"] == 250.5


# ---------------------------------------------------------------- layout (R6)

def test_layout_nt_nb_gt_1(tmp_path):
  """Known answer [spec §2], R6: a (2, 3, 2, 5) C-order block whose value encodes
  (t, c, b, s) as 1000t+100c+10b+s parses with data[t, c, b, s] == its code. Exact."""
  shape = (2, 3, 2, 5)
  path = write_ebr(tmp_path / "lay.ebr", coded_flat(*shape), *shape)
  rec = ep.load_ebr_file(path)
  assert_layout(rec["data"], *shape)


@pytest.mark.parametrize("variant", ["fortran", "ns_nc", "nc_ns_bands_last"])
def test_layout_check_rejects_wrong_reshape(tmp_path, variant):
  """Mutation check for the R6 test: the same file read with a plausible buggy
  reshape (Fortran order; samples-major `(ns, nc)` then transposed; bands as the
  fastest axis) must FAIL `assert_layout`. Shows the layout test catches them."""
  shape = nt, nc, nb, ns = (2, 3, 2, 5)
  path = write_ebr(tmp_path / "lay.ebr", coded_flat(*shape), *shape)
  hdr = ep.read_ebr_header(path)
  flat = np.fromfile(path, dtype="<f8", offset=hdr["data_offset"])
  if variant == "fortran":
    bad = flat.reshape(shape, order="F")
  elif variant == "ns_nc":
    bad = flat.reshape(nt, nb, ns, nc).transpose(0, 3, 1, 2)
  else:
    bad = flat.reshape(nt, nc, ns, nb).transpose(0, 1, 3, 2)
  assert bad.shape == shape
  with pytest.raises(AssertionError):
    assert_layout(bad, *shape)


def test_layout_buggy_parser_monkeypatched(tmp_path, monkeypatch):
  """Mutation check: monkeypatching the parser's numpy reshape to Fortran order
  makes the R6 layout assertion fail; restoring it passes (test above)."""
  shape = (2, 3, 2, 5)
  path = write_ebr(tmp_path / "lay.ebr", coded_flat(*shape), *shape)
  real_fromfile = np.fromfile

  class _FortranFlat(np.ndarray):
    def reshape(self, *a, **k):
      k["order"] = "F"
      return np.asarray(self).reshape(*a, **k)

  def fake_fromfile(*a, **k):
    return real_fromfile(*a, **k).view(_FortranFlat)

  monkeypatch.setattr(ep.np, "fromfile", fake_fromfile)
  rec = ep.load_ebr_file(path)
  monkeypatch.undo()
  with pytest.raises(AssertionError):
    assert_layout(np.asarray(rec["data"]), *shape)


# ---------------------------------------------------------------- dtype table

@pytest.mark.parametrize("data_type", sorted(SPEC_DTYPES))
def test_dtype_table(tmp_path, data_type):
  """Known answer [spec §2]: each of the 20 data_type strings is read with its
  little-endian width; real types come back float64, both complex strings
  complex128; values preserved exactly (chosen exactly representable)."""
  fmt, nbytes, out_dtype = SPEC_DTYPES[data_type]
  values = COMPLEX_VALUES if fmt == "dd" else DTYPE_VALUES[fmt]
  if fmt == "f":
    values = [struct.unpack("<f", struct.pack("<f", v))[0] for v in values]
  path = write_ebr(tmp_path / "dt.ebr", values, 1, 1, 1, len(values), data_type=data_type)
  # File size check: the writer's block is exactly n * width bytes.
  hdr = ep.read_ebr_header(path)
  assert path.stat().st_size - hdr["data_offset"] == len(values) * nbytes
  rec = ep.load_ebr_file(path)
  assert rec["data"].dtype == out_dtype
  assert rec["data"].shape == (1, 1, 1, len(values))
  assert rec["data"][0, 0, 0, :].tolist() == values


def test_dtype_table_has_exactly_20_strings():
  """Known answer [spec §2]: the table lists 20 strings; ebr_dtype accepts all."""
  assert len(SPEC_DTYPES) == 20
  for s, (_, nbytes, _) in SPEC_DTYPES.items():
    assert ep.ebr_dtype(s).itemsize == nbytes


def test_little_endian_bytes(tmp_path):
  """Known answer [spec §2] little-endian: int16 bytes 01 02 -> 0x0201 = 513;
  big-endian would give 258."""
  path = write_ebr(tmp_path / "le.ebr", [513], 1, 1, 1, 1, data_type="int16")
  raw = path.read_bytes()
  assert raw.endswith(b"\x01\x02")
  assert ep.load_ebr_file(path)["data"][0, 0, 0, 0] == 513.0


@pytest.mark.parametrize("bogus", ["bogus", "float16", "long double", "complex64"])
@pytest.mark.parametrize("strict", [True, False])
def test_unsupported_dtype_raises(tmp_path, bogus, strict):
  """Known answer [spec §2]: any data_type outside the table raises ValueError,
  in strict and non-strict mode."""
  path = write_ebr(tmp_path / "bad.ebr", [0.0] * 4, 1, 2, 1, 2, data_type=bogus)
  with pytest.raises(ValueError):
    ep.load_ebr_file(path, strict=strict)


# ---------------------------------------------------------------- truncation

@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("cut", [8, 8 * 11, 3])
def test_truncated_block_raises(tmp_path, strict, cut):
  """Known answer [own, plan]: header says ns=1000 (nc=11) but the block is short
  (one double, one sample of all channels = 999 samples, or a partial element)
  -> ValueError naming the truncation, in both modes; never a silent short read."""
  flat = [float(v) for v in range(11 * 1000)]
  path = write_ebr(tmp_path / "tr.ebr", flat, 1, 11, 1, 1000, channels=CHANNELS, cut_bytes=cut)
  with pytest.raises(ValueError, match="(?i)truncat"):
    ep.load_ebr_file(path, strict=strict)


def test_truncated_plain_fromfile_variant_is_not_caught(tmp_path):
  """Mutation check: the plain `np.fromfile(...).reshape(...)` reader raises a reshape
  ValueError without 'truncat' (so the message match above distinguishes it), and a
  `count=` read of a file cut by 3 bytes returns fewer elements silently."""
  flat = [float(v) for v in range(11 * 1000)]
  path = write_ebr(tmp_path / "tr.ebr", flat, 1, 11, 1, 1000, channels=CHANNELS, cut_bytes=8)
  hdr = ep.read_ebr_header(path)
  with pytest.raises(ValueError) as e:
    np.fromfile(path, dtype="<f8", offset=hdr["data_offset"]).reshape(1, 11, 1, 1000)
  assert "truncat" not in str(e.value).lower()
  assert np.fromfile(path, dtype="<f8", offset=hdr["data_offset"]).size == 10999


# ---------------------------------------------------------------- header rules

def test_header_rules(tmp_path):
  """Known answer [spec §2]: blank lines skipped, unknown keys ignored, magic
  'EBR Binary 1.0' with outer spaces accepted (case-insensitive after strip),
  'marks 2' with two mark lines -> marks [(10, 'stim on'), (300, '201')]. Exact."""
  marks = [(10, "stim on"), (300, "201")]
  path = tmp_path / "hdr.ebr"
  header = ("  EBR Binary 1.0  \n\ndata_type double\n\nsampling_rate 256\nsamples 3\n"
            "operator Someone Unknown\nbands 1\nband_1 Raw Data\n\nchannels 2\nchannel_1 Oz\n"
            "channel_2 MARK\nweird_key 42\ntrials 1\ntrial_1 EEG Register\ncomments 1\n"
            "comment_1 Sample selection\nmarks 2\nmark_1 10 stim on\n\nmark_2 300 201\n"
            "end_header\n")
  path.write_bytes(header.encode("ascii") + _pack([1.0, 2.0, 3.0, 0.0, 201.0, 0.0], "double"))
  rec = ep.load_ebr_file(path)
  assert set(rec) == KEYS
  assert rec["channels"] == ["Oz", "MARK"] and rec["bands"] == ["Raw Data"]
  assert rec["trials"] == ["EEG Register"] and rec["comments"] == ["Sample selection"]
  assert rec["number_of_marks"] == 2
  assert [(int(i), str(l)) for i, l in rec["marks"]] == marks
  np.testing.assert_array_equal(rec["data"][0, :, 0, :], [[1, 2, 3], [0, 201, 0]])


def test_marks_zero_is_empty_list(tmp_path):
  """Known answer [spec §2]: 'marks 0' -> number_of_marks 0, marks []."""
  path = write_ebr(tmp_path / "m0.ebr", [0.0] * 2, 1, 1, 1, 2)
  rec = ep.load_ebr_file(path)
  assert rec["number_of_marks"] == 0 and list(rec["marks"]) == []


def test_binary_starts_right_after_end_header(tmp_path):
  """Known answer [spec §2]: data starts right after 'end_header\\n' even when the
  first data bytes look like ASCII digits/newlines (0x0A as the first byte)."""
  path = write_ebr(tmp_path / "nl.ebr", [10, 10, 49, 13], 1, 1, 1, 4, data_type="uint8")
  assert path.read_bytes().endswith(b"end_header\n\n\n1\r")
  np.testing.assert_array_equal(ep.load_ebr_file(path)["data"].ravel(), [10, 10, 49, 13])


# ---------------------------------------------------------------- strict switch

def test_strict_wrong_magic(tmp_path):
  """Builder deviation 1 (03_changes): magic other than 'ebr binary 1.0' raises in
  strict mode (default) and parses with strict=False, data unchanged."""
  path = write_ebr(tmp_path / "mg.ebr", [1.0, 2.0], 1, 1, 1, 2, magic="ebr binary 2.0")
  with pytest.raises(ValueError):
    ep.load_ebr_file(path)
  np.testing.assert_array_equal(ep.load_ebr_file(path, strict=False)["data"].ravel(), [1, 2])


def test_strict_trailing_bytes(tmp_path):
  """Builder deviation 1: 8 bytes after the declared block raise in strict mode; with
  strict=False the declared block is returned unchanged."""
  path = write_ebr(tmp_path / "tb.ebr", [1.0, 2.0], 1, 1, 1, 2, trailing=b"\x00" * 8)
  with pytest.raises(ValueError):
    ep.load_ebr_file(path, strict=True)
  np.testing.assert_array_equal(ep.load_ebr_file(path, strict=False)["data"].ravel(), [1, 2])


def test_strict_channel_name_count(tmp_path):
  """Builder deviation 1: 'channels 3' with only two channel_k lines raises in strict
  mode; with strict=False the 3-channel block parses and 2 names are returned."""
  path = tmp_path / "cn.ebr"
  hdr = ("ebr binary 1.0\ndata_type double\nsampling_rate 256\nsamples 2\nchannels 3\n"
         "channel_1 A\nchannel_2 B\nend_header\n")
  path.write_bytes(hdr.encode("ascii") + _pack([0.0, 1.0, 100.0, 101.0, 200.0, 201.0], "double"))
  with pytest.raises(ValueError):
    ep.load_ebr_file(path)
  rec = ep.load_ebr_file(path, strict=False)
  assert rec["data"].shape == (1, 3, 1, 2) and rec["channels"] == ["A", "B"]
  np.testing.assert_array_equal(rec["data"][0, :, 0, :], [[0, 1], [100, 101], [200, 201]])


def test_strict_well_formed_file_passes(tmp_path):
  """A spec-conformant file gives identical results in both modes."""
  path, _ = _roundtrip_file(tmp_path, ns=50)
  a, b = ep.load_ebr_file(path, strict=True), ep.load_ebr_file(path, strict=False)
  np.testing.assert_array_equal(a["data"], b["data"])
  assert {k: v for k, v in a.items() if k != "data"} == {k: v for k, v in b.items() if k != "data"}


# ---------------------------------------------------------------- helpers

def test_select_scalp_channels_shuffled():
  """Known answer [plan], PF-06: indices follow scalp_names order, looked up by name
  in a shuffled channel list."""
  rng = np.random.default_rng(0)
  shuffled = list(rng.permutation(CHANNELS))
  scalp = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  idx = ep.select_scalp_channels(shuffled, scalp)
  assert [shuffled[i] for i in idx] == scalp
  assert ep.select_scalp_channels(CHANNELS, ["O2", "PO7"]) == [7, 0]


def test_select_scalp_channels_missing_name():
  """Known answer [plan]: a missing scalp name raises ValueError."""
  with pytest.raises(ValueError):
    ep.select_scalp_channels(CHANNELS[1:], ["PO7", "Oz"])


def test_get_mark_channel_index():
  """Known answer [plan]: MARK at index 10 of the montage -> 10; shuffled -> its
  position; absent -> -1; custom name honoured."""
  assert ep.get_mark_channel_index(CHANNELS) == 10
  shuffled = ["MARK"] + CHANNELS[:10]
  assert ep.get_mark_channel_index(shuffled) == 0
  assert ep.get_mark_channel_index(CHANNELS[:10]) == -1
  assert ep.get_mark_channel_index(CHANNELS, mark_name="TIMESTAMP") == 8


def test_resolve_recording_path(tmp_path):
  """Known answer [plan, decisions.md P01]: raw_root/session/filename; a bare stem
  gets '.ebr'; an absent file raises FileNotFoundError naming the path."""
  (tmp_path / "S03").mkdir()
  f = tmp_path / "S03" / "mOO.ebr"
  f.write_bytes(b"")
  assert Path(ep.resolve_recording_path(tmp_path, "S03", "mOO.ebr")) == f
  assert Path(ep.resolve_recording_path(str(tmp_path), "S03", "mOO")) == f
  with pytest.raises(FileNotFoundError, match="OO.ebr"):
    ep.resolve_recording_path(tmp_path, "S03", "OO")
  with pytest.raises(FileNotFoundError):
    ep.resolve_recording_path(tmp_path, "S09", "mOO.ebr")


def _v1_scalp():
  cfg = yaml.safe_load((ROOT / "configs" / "pipeline_config.yaml").read_text())
  return cfg["channels"]["scalp"]


@pytest.mark.parametrize("shuffle", [False, True])
def test_extract_scalp_signal_config_v1(tmp_path, shuffle):
  """Known answer [spec §2, REQ §3 v1]: an 11-channel recording (channel named X has
  row value 1000*montage_index(X) + t) through extract_scalp_signal with the v1 scalp
  list gives shape (7, T), names == v1 list, no PO7, and row r == planted signal of
  scalp[r], also when the file's channel order is shuffled. Exact."""
  ns = 300
  order = list(np.random.default_rng(1).permutation(CHANNELS)) if shuffle else CHANNELS
  flat = [1000 * CHANNELS.index(name) + t for name in order for t in range(ns)]
  path = write_ebr(tmp_path / "x.ebr", flat, 1, 11, 1, ns, channels=order)
  rec = ep.load_ebr_file(path)
  scalp = _v1_scalp()
  x, names = ep.extract_scalp_signal(rec, scalp)
  assert x.shape == (7, ns) and x.dtype == np.float64
  assert list(names) == scalp and "PO7" not in names
  for r, name in enumerate(scalp):
    np.testing.assert_array_equal(x[r], 1000 * CHANNELS.index(name) + np.arange(ns))


def test_parser_returns_all_channels_po7_included(tmp_path):
  """PF-05: the parser is montage-agnostic; PO7 stays in the parsed channels."""
  path = write_ebr(tmp_path / "a.ebr", [0.0] * 22, 1, 11, 1, 2, channels=CHANNELS)
  rec = ep.load_ebr_file(path)
  assert rec["channels"][0] == "PO7" and rec["data"].shape[1] == 11
