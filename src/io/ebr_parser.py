"""Reader for the EBR binary 1.0 recordings (mas/01_DATA_SPEC.md section 2).

An EBR file is an ASCII header of newline-terminated lines ending with
`end_header`, followed by a little-endian block of `nt * nc * nb * ns` elements
stored in C order as `(trials, channels, bands, samples)`.

`load_ebr_file` reads a whole file into the 14-key dict of the specification;
`read_ebr_header` and `open_ebr_block` give the header and a lazy memory map for
callers that need less. The parser is montage-agnostic: it returns every channel
of the file (channel selection by name is `select_scalp_channels`).
"""

import re
from pathlib import Path
from typing import Sequence, Union

import numpy as np

PathLike = Union[str, Path]

EBR_MAGIC = "ebr binary 1.0"

# data_type string -> little-endian numpy dtype (spec section 2).
EBR_DTYPES = {
  "int8": "<i1", "char": "<i1",
  "uint8": "<u1", "unsigned char": "<u1",
  "int16": "<i2", "short": "<i2",
  "uint16": "<u2", "unsigned short": "<u2",
  "int32": "<i4", "int": "<i4",
  "uint32": "<u4", "unsigned int": "<u4",
  "int64": "<i8", "__int64": "<i8",
  "uint64": "<u8", "unsigned __int64": "<u8",
  "float": "<f4",
  "double": "<f8",
  "complex": "<c16", "class std::complex<double>": "<c16",
}

# The keys load_ebr_file returns, in the order of the spec.
RECORDING_KEYS = ("data_type", "sampling_rate", "number_of_trials", "trials",
                  "number_of_channels", "channels", "number_of_bands", "bands",
                  "number_of_samples", "number_of_comments", "comments",
                  "number_of_marks", "marks", "data")

_REQUIRED_KEYS = ("data_type", "sampling_rate", "samples", "channels")
_INDEXED = re.compile(r"(band|channel|trial|comment|mark)_(\d+)")
_MAX_HEADER_BYTES = 1 << 20


def ebr_dtype(data_type: str) -> np.dtype:
  """Numpy dtype for an EBR `data_type` string, matched exactly (case-sensitive).

  Raises ValueError for any string outside the table of spec section 2
  (e.g. `Double` or `double ` raise; the delivered files all say `double`).
  """
  if data_type not in EBR_DTYPES:
    raise ValueError(f"unsupported EBR data_type {data_type!r}")
  return np.dtype(EBR_DTYPES[data_type])


def _parse_header_lines(f, path: PathLike) -> dict:
  """Parse header lines from an open binary file, leaving it at the data block."""
  fields: dict = {}
  indexed: dict = {"band": {}, "channel": {}, "trial": {}, "comment": {}, "mark": {}}
  magic = None
  duplicates: list = []
  while True:
    raw = f.readline()
    if not raw:
      raise ValueError(f"{path}: no end_header line")
    if f.tell() > _MAX_HEADER_BYTES:
      raise ValueError(f"{path}: header exceeds {_MAX_HEADER_BYTES} bytes without end_header")
    line = raw.decode("ascii", errors="replace").strip()
    if not line:
      continue
    if magic is None:
      magic = line
      continue
    if line == "end_header":
      data_offset = f.tell()
      break
    parts = line.split(maxsplit=1)
    key, value = parts[0], (parts[1] if len(parts) > 1 else "")
    m = _INDEXED.fullmatch(key)
    if m:
      group, k = m.group(1), int(m.group(2))
      if k in indexed[group]:
        duplicates.append(f"{group}_{k}")
      indexed[group][k] = value
    else:
      if key in fields:
        duplicates.append(key)
      fields[key] = value

  for key in _REQUIRED_KEYS:
    if key not in fields:
      raise ValueError(f"{path}: header has no '{key}' line")

  def _int(key: str, default: int) -> int:
    try:
      return int(fields.get(key, default))
    except ValueError:
      raise ValueError(f"{path}: header '{key}' is not an integer: {fields[key]!r}") from None

  marks = []
  for k in sorted(indexed["mark"]):
    idx, _, label = indexed["mark"][k].partition(" ")
    try:
      marks.append((int(idx), label.strip()))
    except ValueError:
      raise ValueError(f"{path}: mark_{k} has no integer sample index: {indexed['mark'][k]!r}") from None

  try:
    fs = float(fields["sampling_rate"])
  except ValueError:
    raise ValueError(f"{path}: header 'sampling_rate' is not a number: {fields['sampling_rate']!r}") from None

  header = {
    "magic": magic,
    "data_type": fields["data_type"],
    "sampling_rate": fs,
    "number_of_trials": _int("trials", 1),
    "trials": [indexed["trial"][k] for k in sorted(indexed["trial"])],
    "number_of_channels": _int("channels", 0),
    "channels": [indexed["channel"][k] for k in sorted(indexed["channel"])],
    "number_of_bands": _int("bands", 1),
    "bands": [indexed["band"][k] for k in sorted(indexed["band"])],
    "number_of_samples": _int("samples", 0),
    "number_of_comments": _int("comments", 0),
    "comments": [indexed["comment"][k] for k in sorted(indexed["comment"])],
    "number_of_marks": _int("marks", 0),
    "marks": marks,
    "data_offset": data_offset,
    "_indices": {name: sorted(d) for name, d in indexed.items()},
    "_duplicates": duplicates,
  }
  for key in ("number_of_trials", "number_of_channels", "number_of_bands", "number_of_samples"):
    if header[key] < 0:
      raise ValueError(f"{path}: negative {key} ({header[key]})")
  return header


def read_ebr_header(path: PathLike) -> dict:
  """Parse the ASCII header of an EBR file without reading the binary block.

  Returns the 13 non-data keys of `RECORDING_KEYS` plus `magic` (first non-blank
  line, stripped, as written) and `data_offset` (byte where the block starts).
  Blank lines are skipped and unknown keys ignored; a repeated line keeps its
  last value. Missing count lines default to `trials = bands = 1` and
  `comments = marks = 0` [own]. Raises ValueError when `end_header` or one of
  data_type, sampling_rate, samples, channels is missing. No consistency check
  is applied here (see `load_ebr_file(strict=True)`).
  """
  with open(path, "rb") as f:
    header = _parse_header_lines(f, path)
  header.pop("_indices")
  header.pop("_duplicates")
  return header


def block_shape(header: dict) -> tuple:
  """Shape `(nt, nc, nb, ns)` of the binary block declared by a header."""
  return (header["number_of_trials"], header["number_of_channels"],
          header["number_of_bands"], header["number_of_samples"])


def trailing_bytes(path: PathLike, header: dict) -> int:
  """Bytes after the declared binary block (0 for a well-formed file; negative if short)."""
  n = int(np.prod(block_shape(header)))
  return Path(path).stat().st_size - header["data_offset"] - n * ebr_dtype(header["data_type"]).itemsize


def open_ebr_block(path: PathLike, header: dict) -> np.memmap:
  """Memory-map the binary block as `(nt, nc, nb, ns)`, C order, in the file's own dtype.

  Nothing is read until indexed; no cast is applied. Raises ValueError if the
  file is shorter than the block declared by `header` (from `read_ebr_header`).
  """
  dtype = ebr_dtype(header["data_type"])
  shape = block_shape(header)
  needed = header["data_offset"] + int(np.prod(shape)) * dtype.itemsize
  size = Path(path).stat().st_size
  if size < needed:
    raise ValueError(f"{path}: truncated, {size} bytes < {needed} declared by the header")
  return np.memmap(path, dtype=dtype, mode="r", offset=header["data_offset"], shape=shape)


def _check_consistency(header: dict, path: PathLike) -> None:
  """Strict checks: magic, no repeated header line, every `<name>_<k>` list numbered 1..n."""
  if (header["magic"] or "").lower() != EBR_MAGIC:
    raise ValueError(f"{path}: magic {header['magic']!r}, expected {EBR_MAGIC!r}")
  if header["_duplicates"]:
    raise ValueError(f"{path}: repeated header lines {header['_duplicates']}")
  declared = {"channel": "number_of_channels", "band": "number_of_bands", "trial": "number_of_trials",
              "comment": "number_of_comments", "mark": "number_of_marks"}
  for name, key in declared.items():
    found = header["_indices"][name]
    if found != list(range(1, header[key] + 1)):
      raise ValueError(f"{path}: header declares {header[key]} {name}(s) but has "
                       f"{name}_k lines for k = {found}")


def load_ebr_file(path: PathLike, strict: bool = True) -> dict:
  """Read a whole EBR file (spec section 2).

  Returns a dict with exactly the keys of `RECORDING_KEYS`. `data` has shape
  `(nt, nc, nb, ns)` (C order of the block); real types are cast to float64,
  complex types stay complex128. `marks` is a list of `(sample_index, label)`.
  The continuous signal of channel `c` in a delivered file is `data[0, c, 0, :]`.

  Always raises ValueError for: no `end_header`, a missing required key, an
  unsupported `data_type`, or a block shorter than declared (no silent short read).
  With `strict=True` (default) it also raises when the magic is not
  `ebr binary 1.0` (case-insensitive, stripped), when a header line is repeated
  (e.g. two `channel_3` lines), when a channel/band/trial/
  comment/mark list does not hold exactly the declared `_1..n` lines, or when
  bytes follow the declared block. `strict=False` skips those four checks so a
  caller (the raw inventory) can report them as deviations itself.
  """
  with open(path, "rb") as f:
    header = _parse_header_lines(f, path)
    dtype = ebr_dtype(header["data_type"])
    shape = block_shape(header)
    n = int(np.prod(shape))
    if strict:
      _check_consistency(header, path)
    needed = header["data_offset"] + n * dtype.itemsize
    size = Path(path).stat().st_size
    if size < needed:
      raise ValueError(f"{path}: truncated, {size} bytes < {needed} declared by the header")
    flat = np.fromfile(f, dtype=dtype, count=n)
  if flat.size != n:
    raise ValueError(f"{path}: truncated, block holds {flat.size} of the {n} {dtype.name} "
                     f"elements declared by the header {shape}")
  if strict:
    extra = trailing_bytes(path, header)
    if extra:
      raise ValueError(f"{path}: {extra} bytes after the declared data block {shape}")
  data = flat.reshape(shape, order="C")
  if dtype.kind != "c":
    data = data.astype(np.float64, copy=False)
  rec = {k: header[k] for k in RECORDING_KEYS if k != "data"}
  rec["data"] = data
  return rec


def resolve_recording_path(raw_root: PathLike, session: str, filename: str) -> Path:
  """Path of one recording: `raw_root / session / filename`.

  `session` is the subject folder (e.g. `S01`), `filename` the run file
  (`OO.ebr`; a bare stem such as `OO` gets `.ebr`). Raises FileNotFoundError
  naming the path when it is not an existing file.
  """
  name = str(filename)
  if not Path(name).suffix:
    name += ".ebr"
  path = Path(raw_root) / str(session) / name
  if not path.is_file():
    raise FileNotFoundError(f"recording not found: {path}")
  return path


def select_scalp_channels(channels: Sequence[str], scalp_names: Sequence[str]) -> list:
  """Indices into `channels` of each name of `scalp_names`, in the order of `scalp_names`.

  Lookup is by name, never by position (PF-06). Raises ValueError when a name is
  missing, appears more than once in `channels`, or is repeated in `scalp_names`.
  """
  channels = list(channels)
  scalp_names = list(scalp_names)
  dup = sorted({c for c in scalp_names if scalp_names.count(c) > 1})
  if dup:
    raise ValueError(f"scalp_names repeats {dup}")
  missing = [c for c in scalp_names if c not in channels]
  if missing:
    raise ValueError(f"channels {missing} not found in {channels}")
  ambiguous = [c for c in scalp_names if channels.count(c) > 1]
  if ambiguous:
    raise ValueError(f"channels {ambiguous} appear more than once in {channels}")
  return [channels.index(c) for c in scalp_names]


def get_mark_channel_index(channels: Sequence[str], mark_name: str = "MARK") -> int:
  """Index of the event-code channel `mark_name` in `channels`, or -1 if absent.

  Raises ValueError if the name appears more than once.
  """
  channels = list(channels)
  n = channels.count(mark_name)
  if n > 1:
    raise ValueError(f"channel {mark_name!r} appears {n} times in {channels}")
  return channels.index(mark_name) if n else -1


def extract_scalp_signal(recording: dict, scalp_names: Sequence[str]) -> tuple:
  """Continuous scalp signals of a recording from `load_ebr_file`.

  Returns `(x, names)`: `x = data[0, idx, 0, :]` as float64 with shape `(C, T)`,
  `C = len(scalp_names)`, rows in the order of `scalp_names`, and `names` that
  list. Raises ValueError for a missing channel, a complex block, or a block with
  more than one trial or band (the continuous signal is undefined there).
  """
  data = np.asarray(recording["data"])
  if data.ndim != 4:
    raise ValueError(f"recording data must be (nt, nc, nb, ns), got shape {data.shape}")
  if data.shape[0] != 1 or data.shape[2] != 1:
    raise ValueError(f"expected nt == nb == 1 for a continuous recording, got shape {data.shape}")
  if np.iscomplexobj(data):
    raise ValueError("complex EBR data has no real scalp signal")
  channels = list(recording["channels"])
  if len(channels) != data.shape[1]:
    raise ValueError(f"{len(channels)} channel names for {data.shape[1]} data channels")
  idx = select_scalp_channels(channels, scalp_names)
  x = np.asarray(data[0, idx, 0, :], dtype=np.float64)
  return x, list(scalp_names)
