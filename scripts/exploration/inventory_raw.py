"""Inventory of the raw recordings (P00).

Walks <raw-dir>/S*/ (subjects matched by ^S\\d+$, only *.ebr files), reads each
EBR file through src/io/ebr_parser.load_ebr_file (since P01) and uses only the
MARK, TIMESTAMP and EEG channels.
Writes one row per file to reports/raw_inventory.csv with the columns of
mas/01_DATA_SPEC.md section 4 plus fs, channel list, event-code counts, run kind
and the list of deviations from the spec.

Checks (mas/01_DATA_SPEC.md sections 2-4):
  all files        magic "ebr binary 1.0", fs == 256, the 11 channel names in
                   order, trials == bands == 1, binary block size
  calibration      (OO, mOO, C, mC) onsets 201, 202, 203, 200 = 40 each,
                   101..105 = 8 each, no other code
  online           (online_*) only codes 1001..1005
  joined           (cb_mas_mcb) 80 stimulus onsets
Any deviation is printed and the script exits 1 after writing the CSV.
"""

import argparse
import csv
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else two levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.io import ebr_parser  # noqa: E402  (needs ROOT on sys.path)

# --- Specification (mas/01_DATA_SPEC.md) -------------------------------------

EBR_MAGIC = "ebr binary 1.0"
EXPECTED_FS = 256.0
EXPECTED_CHANNELS = ("PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2",
                     "TIMESTAMP", "FLASHINGTIME", "MARK")
EEG_CHANNELS = EXPECTED_CHANNELS[:8]
SUBJECT_PATTERN = re.compile(r"^S\d+$")

CALIBRATION_STEMS = ("OO", "mOO", "C", "mC")
JOINED_STEMS = ("cb_mas_mcb",)
ONLINE_PREFIX = "online_"

CALIBRATION_COUNTS = {201: 40, 202: 40, 203: 40, 200: 40,
                      101: 8, 102: 8, 103: 8, 104: 8, 105: 8}
STIM_CODES = (101, 102, 103, 104, 105)
ONLINE_CODES = (1001, 1002, 1003, 1004, 1005)
JOINED_STIM_EVENTS = 80

CSV_COLUMNS = ("subject", "file", "samples", "duration_s", "stim_events",
               "session_start_utc", "p99_abs_eeg_uv",
               "fs", "n_channels", "channels", "event_counts", "kind", "deviations")

# --- EBR reading (src/io/ebr_parser.py since P01) ----------------------------
# Thin wrappers keep the P00 public names; all reading goes through the parser.

def ebr_dtype(data_type: str) -> np.dtype:
  """Numpy dtype for an EBR data_type string; ValueError if unsupported."""
  return ebr_parser.ebr_dtype(data_type)


def parse_ebr_header(path: Path) -> dict:
  """EBR header (spec keys plus `magic` and `data_offset`); see ebr_parser.read_ebr_header."""
  return ebr_parser.read_ebr_header(path)


def open_ebr_data(path: Path, header: dict) -> np.memmap:
  """Memory map of the block as (nt, nc, nb, ns) in the file dtype; see ebr_parser.open_ebr_block."""
  return ebr_parser.open_ebr_block(path, header)


def trailing_bytes(path: Path, header: dict) -> int:
  """Bytes after the declared binary block (0 for a well-formed file)."""
  return ebr_parser.trailing_bytes(path, header)


def default_raw_dir() -> Path:
  """ROOT / `paths.data_raw_dir` of configs/pipeline_config.yaml (data/raw if unset)."""
  cfg_path = ROOT / "configs" / "pipeline_config.yaml"
  rel = "data/raw"
  if cfg_path.is_file():
    with open(cfg_path) as f:
      cfg = yaml.safe_load(f) or {}
    rel = (cfg.get("paths") or {}).get("data_raw_dir") or rel
  return ROOT / rel


# --- Events and per-file summary ---------------------------------------------

def event_onset_counts(mark: np.ndarray) -> dict:
  """Onsets per nonzero code: samples where MARK == code and differs from the previous sample.

  Implements `(mark == code) & (diff(mark, prepend=0) != 0)` of 01_DATA_SPEC.md
  section 3 for every code at once, so a multi-sample plateau counts once.
  """
  m = np.rint(np.asarray(mark, dtype=np.float64)).astype(np.int64)
  onset = (m != 0) & (np.diff(m, prepend=0) != 0)
  return {int(c): int(n) for c, n in sorted(Counter(m[onset].tolist()).items())}


def classify_kind(stem: str) -> str:
  """Run kind from the file stem: calibration, online, joined or unknown."""
  if stem in CALIBRATION_STEMS:
    return "calibration"
  if stem.startswith(ONLINE_PREFIX):
    return "online"
  if stem in JOINED_STEMS:
    return "joined"
  return "unknown"


def stim_event_count(counts: dict, kind: str) -> int:
  """Stimulus onsets: 101-105 (calibration, joined), 1001-1005 (online), both (unknown)."""
  if kind == "online":
    codes = ONLINE_CODES
  elif kind == "unknown":
    codes = STIM_CODES + ONLINE_CODES
  else:
    codes = STIM_CODES
  return sum(counts.get(c, 0) for c in codes)


def protocol_deviations(counts: dict, kind: str) -> list:
  """Deviations of the onset counts from the protocol of 01_DATA_SPEC.md sections 3-4."""
  devs = []
  if kind == "calibration":
    for code, expected in CALIBRATION_COUNTS.items():
      if counts.get(code, 0) != expected:
        devs.append(f"code {code}: {counts.get(code, 0)} onsets, expected {expected}")
    extra = sorted(set(counts) - set(CALIBRATION_COUNTS))
    if extra:
      devs.append(f"unexpected codes {extra} in a calibration run")
  elif kind == "online":
    extra = sorted(set(counts) - set(ONLINE_CODES))
    if extra:
      devs.append(f"unexpected codes {extra} in an online run (only 1001-1005 allowed)")
  elif kind == "joined":
    n = stim_event_count(counts, kind)
    if n != JOINED_STIM_EVENTS:
      devs.append(f"{n} stimulus onsets, expected {JOINED_STIM_EVENTS} in a joined run")
  return devs


def format_counts(counts: dict) -> str:
  """`code:n;code:n` sorted by code."""
  return ";".join(f"{c}:{n}" for c, n in sorted(counts.items()))


def session_start_utc(timestamp_ms: float) -> str:
  """First TIMESTAMP sample (ms since the Unix epoch) as `YYYY-MM-DD HH:MM` UTC."""
  return datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def inventory_file(path: Path, subject: str, strict: bool = False) -> dict:
  """One inventory row (CSV_COLUMNS) for one EBR file; problems go to `deviations`.

  `strict=True` reads with `load_ebr_file(path, strict=True)`: a strict-mode
  ValueError becomes the `unreadable: <message>` deviation.
  """
  path = Path(path)
  stem = path.stem
  kind = classify_kind(stem)
  row = {k: "" for k in CSV_COLUMNS}
  row.update(subject=subject, file=stem, kind=kind)
  devs = []
  try:
    header = parse_ebr_header(path)
    data = ebr_parser.load_ebr_file(path, strict=strict)["data"]
  except ValueError as exc:
    row["deviations"] = f"unreadable: {exc}"
    return row

  fs = header["sampling_rate"]
  ns = header["number_of_samples"]
  names = header["channels"]
  row.update(samples=ns, fs=fs, n_channels=header["number_of_channels"], channels=";".join(names))
  if fs > 0:
    row["duration_s"] = round(ns / fs, 1)

  if (header["magic"] or "").lower() != EBR_MAGIC:
    devs.append(f"magic {header['magic']!r}, expected {EBR_MAGIC!r}")
  if fs != EXPECTED_FS:
    devs.append(f"fs {fs:g}, expected {EXPECTED_FS:g}")
  if tuple(names) != EXPECTED_CHANNELS:
    devs.append(f"channels {names}, expected {list(EXPECTED_CHANNELS)}")
  if len(names) != header["number_of_channels"]:
    devs.append(f"header declares {header['number_of_channels']} channels but names {len(names)}")
  if header["number_of_trials"] != 1 or header["number_of_bands"] != 1:
    devs.append(f"trials={header['number_of_trials']}, bands={header['number_of_bands']}, expected 1 and 1")
  extra = trailing_bytes(path, header)
  if extra:
    devs.append(f"{extra} bytes after the declared data block")
  if ns <= 0:
    devs.append("no samples")
    row["deviations"] = " | ".join(devs)
    return row

  def _channel(name: str):
    if name in names and names.index(name) < header["number_of_channels"]:
      return np.asarray(data[0, names.index(name), 0, :], dtype=np.float64)
    return None

  mark = _channel("MARK")
  if mark is None:
    devs.append("no MARK channel")
  else:
    if not np.all(np.isfinite(mark)) or np.any(np.abs(mark - np.rint(mark)) > 1e-6):
      devs.append("MARK has non-integer or non-finite values")
    counts = event_onset_counts(np.nan_to_num(mark))
    row["event_counts"] = format_counts(counts)
    row["stim_events"] = stim_event_count(counts, kind)
    devs.extend(protocol_deviations(counts, kind))

  ts = _channel("TIMESTAMP")
  if ts is None:
    devs.append("no TIMESTAMP channel")
  elif np.isfinite(ts[0]):
    row["session_start_utc"] = session_start_utc(ts[0])
  else:
    devs.append("first TIMESTAMP sample is not finite")

  eeg_idx = [names.index(c) for c in EEG_CHANNELS if c in names and names.index(c) < header["number_of_channels"]]
  if eeg_idx:
    eeg = np.asarray(data[0, eeg_idx, 0, :], dtype=np.float64)
    row["p99_abs_eeg_uv"] = float(np.percentile(np.abs(eeg), 99))

  row["deviations"] = " | ".join(devs)
  return row


# --- Discovery and CLI -------------------------------------------------------

def discover_subjects(raw_dir: Path) -> list:
  """Subject folders of raw_dir matching ^S\\d+$, in numeric order."""
  found = [p.name for p in Path(raw_dir).iterdir() if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name)]
  return sorted(found, key=lambda s: int(s[1:]))


def run_inventory(raw_dir: Path, subjects=None, strict: bool = False) -> list:
  """Inventory rows for every *.ebr file of the given (or discovered) subjects."""
  raw_dir = Path(raw_dir)
  rows = []
  for subject in (subjects if subjects else discover_subjects(raw_dir)):
    folder = raw_dir / subject
    if not folder.is_dir():
      print(f"[-] Skipping {subject}: folder not found in {raw_dir}")
      continue
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".ebr")
    if not files:
      print(f"[-] Skipping {subject}: no .ebr files")
      continue
    for path in files:
      row = inventory_file(path, subject, strict=strict)
      if row["kind"] == "unknown":
        print(f"[!] {subject}/{path.name}: unknown run kind, no protocol checks applied")
      rows.append(row)
  return rows


def write_csv(rows: list, out: Path) -> None:
  """Write the rows with CSV_COLUMNS as header, creating the parent folder."""
  out = Path(out)
  out.parent.mkdir(parents=True, exist_ok=True)
  with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)


def _fmt(value, spec: str) -> str:
  """Format a console cell; an empty value prints as '-' padded to the same width."""
  if value == "":
    return format("-", re.match(r"[<>^]?\d*", spec).group())
  return format(value, spec)


def main(argv=None) -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--raw-dir", type=Path, default=default_raw_dir(),
                      help="folder holding the S*/ subject folders (default: <root>/ + "
                           "paths.data_raw_dir of configs/pipeline_config.yaml)")
  parser.add_argument("--out", type=Path, default=ROOT / "reports" / "raw_inventory.csv",
                      help="output CSV (default: <root>/reports/raw_inventory.csv)")
  parser.add_argument("--subjects", nargs="+", default=None,
                      help="subject folders to include (default: all matching ^S\\d+$)")
  parser.add_argument("--strict", action="store_true",
                      help="read with load_ebr_file(strict=True); a strict-mode error is an "
                           "'unreadable' deviation (default: off, P00 behaviour)")
  args = parser.parse_args(argv)

  if not args.raw_dir.is_dir():
    print(f"[x] Raw folder not found: {args.raw_dir}")
    return 1
  rows = run_inventory(args.raw_dir, args.subjects, strict=args.strict)
  if not rows:
    print(f"[x] No .ebr files found under {args.raw_dir}")
    return 1

  print(f"{'subject':<8} {'file':<12} {'samples':>8} {'dur_s':>7} {'stim':>5} "
        f"{'session_start_utc':<17} {'p99_uV':>8}  kind")
  for r in rows:
    print(f"{r['subject']:<8} {r['file']:<12} {_fmt(r['samples'], '>8')} {_fmt(r['duration_s'], '>7.1f')} "
          f"{_fmt(r['stim_events'], '>5')} {r['session_start_utc'] or '-':<17} "
          f"{_fmt(r['p99_abs_eeg_uv'], '>8.1f')}  {r['kind']}")

  n_dev = 0
  for r in rows:
    if r["deviations"]:
      items = r["deviations"].split(" | ")
      n_dev += len(items)
      for item in items:
        print(f"[x] DEVIATION {r['subject']}/{r['file']}: {item}")

  write_csv(rows, args.out)
  n_subjects = len({r["subject"] for r in rows})
  print(f"{len(rows)} files, {n_subjects} subjects, {n_dev} deviations")
  print(f"Saved: {args.out}")
  return 1 if n_dev else 0


if __name__ == "__main__":
  sys.exit(main())
