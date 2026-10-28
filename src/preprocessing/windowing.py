"""Window index, window cutting and sub-band filtering of the built windows (P16.2, mas/01_DATA_SPEC.md 5.2).

Segments (`L(s) = int(s * fs)` samples), as in the legacy P02 windowing:

- cross (201): `[onset, onset + L(cross_duration_sec))`;
- cue (202): `[onset - L(cue_lookback_sec), onset)`, complete only (start >= 0);
- stimulus (101-105): `[onset, onset + L(stim_duration_sec))`, complete trials only.

Windows of `n = L(sub_window_sec)` samples start every `stride` samples and lie fully inside their
segment. `stride_sec=None` means `stride = n` (non-overlapping) and reproduces the legacy window starts
exactly (2 / 1 / 5 windows per 201 / 202 / 10x trial). Rows are ordered by condition (`cross, cue,
stim_conditions...` as given), then by onset, then by offset. One trial id per segment, increasing in row
order; offsets restart at 0 in every segment, so any ordering that matters (R8) is by `(trial_id, offsets)`.
PF-13: the 202 window lies inside the fixation period and duplicates a 201 window; with
`cue_shares_cross_id=True` (default) it gets the id of the 201 segment it overlaps, so a grouped split can
never separate them.

Sub-band windows (R3, PF-14): `band_windows(..., mode="continuous")` filters the whole broadband-filtered
recording per band and cuts afterwards; `mode="per_window"` (legacy) cuts first and filters each window with
`filtfilt`, which distorts the first and last ~100 ms of narrow bands. Filter banks are those of P05
(`fbcca_filter_bank`: Chebyshev I order 4, 3 dB, 3 sub-bands; `fbcsp_filter_bank`: Butterworth order 4, 5
bands), always built for the `fs` passed in (never a literal, PF-04).
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
from scipy.signal import butter, cheby1, filtfilt, sosfiltfilt

from src.features.ssvep.fbcca_extraction import (CHEBY_ORDER, CHEBY_RIPPLE_DB, SUBBAND_HIGH_HZ,
                                                 SUBBAND_LOW_HZ)
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS
from src.features.ssvep.psd_extraction import find_event_onsets
from src.io import ebr_parser

MODES = ("continuous", "per_window")
BANK_NAMES = ("fbcca", "fbcsp")


# --- recording and events -----------------------------------------------------------

def load_session(path, scalp_channels: Sequence[str], mark: str = "MARK") -> tuple:
  """`(x (C, T), mark (T,), fs)` of one `.ebr` file: scalp channels by name (PF-06), MARK, header fs.

  Raises ValueError for a missing channel or MARK, FileNotFoundError for a missing file.
  """
  rec = ebr_parser.load_ebr_file(path)
  x, _ = ebr_parser.extract_scalp_signal(rec, scalp_channels)
  mi = ebr_parser.get_mark_channel_index(rec["channels"], mark)
  if mi < 0:
    raise ValueError(f"no {mark} channel in {path}")
  return x, np.asarray(rec["data"][0, mi, 0, :], dtype=np.float64), float(rec["sampling_rate"])


def event_onsets(mark: np.ndarray, code: int) -> np.ndarray:
  """Onset samples of `code` in a MARK channel (01_DATA_SPEC section 3); the P02 rule."""
  return find_event_onsets(mark, code)


# --- window index -------------------------------------------------------------------

@dataclass
class WindowIndex:
  """Window table of a recording, all arrays `(n,)` int64 in row order (see the module docstring)."""
  starts: np.ndarray       # start sample in the continuous recording
  labels: np.ndarray       # condition code
  trial_ids: np.ndarray    # one per segment (202 shares its 201 segment's id)
  sub_idx: np.ndarray      # position inside the segment (0, 1, ...)
  offsets: np.ndarray      # samples from the segment start to the window start
  skipped: list = field(default_factory=list)   # [{condition, onset, why}] incomplete segments

  def __len__(self) -> int:
    return len(self.starts)

  def select(self, mask: np.ndarray) -> "WindowIndex":
    """Rows where `mask` is true (boolean or index array)."""
    return WindowIndex(self.starts[mask], self.labels[mask], self.trial_ids[mask], self.sub_idx[mask],
                       self.offsets[mask], list(self.skipped))


def windows_per_segment(segment_len: int, window_len: int, stride: int) -> int:
  """Number of windows of `window_len` samples every `stride` samples fully inside `segment_len` samples."""
  if window_len < 1 or stride < 1:
    raise ValueError(f"window_len and stride must be >= 1, got {window_len}, {stride}")
  return 0 if segment_len < window_len else (segment_len - window_len) // stride + 1


def segment_starts(onsets: np.ndarray, offset: int, length: int, n_samples: int) -> tuple:
  """`(starts, skipped_onsets)`: segment start `onset + offset` of every onset whose `[start, start + length)`
  lies inside `[0, n_samples)`; the other onsets are returned as skipped (incomplete segments)."""
  starts = np.asarray(onsets, dtype=np.int64) + int(offset)
  ok = (starts >= 0) & (starts + int(length) <= int(n_samples))
  return starts[ok], np.asarray(onsets, dtype=np.int64)[~ok]


def build_window_index(mark: np.ndarray, fs: float, stim_conditions: Sequence[int],
                       cross_condition: int = 201, cue_condition: int = 202,
                       sub_window_sec: float = 1.0, stim_duration_sec: float = 5.0,
                       cross_duration_sec: float = 2.0, cue_lookback_sec: float = 1.0,
                       stride_sec: Optional[float] = None, cue_shares_cross_id: bool = True) -> WindowIndex:
  """The `WindowIndex` of a MARK channel (module docstring); `fs` is the header rate.

  Raises ValueError for a non-positive `fs`, window or stride.
  """
  m = np.asarray(mark).reshape(-1)
  if not fs > 0:
    raise ValueError(f"fs must be positive, got {fs}")
  n = int(sub_window_sec * fs)
  stride = n if stride_sec is None else int(stride_sec * fs)
  if n < 1 or stride < 1:
    raise ValueError(f"window {sub_window_sec} s / stride {stride_sec} s give no samples at fs {fs}")
  plan = [(int(cross_condition), 0, int(cross_duration_sec * fs)),
          (int(cue_condition), -int(cue_lookback_sec * fs), int(cue_lookback_sec * fs))]
  plan += [(int(c), 0, int(stim_duration_sec * fs)) for c in stim_conditions]

  cols = {k: [] for k in ("starts", "labels", "trial_ids", "sub_idx", "offsets")}
  skipped, cross_segments, next_id = [], [], 0
  for code, off, length in plan:
    onsets = event_onsets(m, code)
    starts, bad = segment_starts(onsets, off, length, len(m))
    skipped += [{"condition": code, "onset": int(o),
                 "why": "starts before the recording" if o + off < 0 else "ends after the recording"}
                for o in bad]
    k = windows_per_segment(length, n, stride)
    for s in starts:
      s = int(s)
      if k == 0:
        continue
      tid = next_id
      if code == cue_condition and cue_shares_cross_id:
        best = max(((min(s + length, e) - max(s, b), i) for b, e, i in cross_segments), default=(0, None))
        if best[0] > 0:
          tid = best[1]
      if tid == next_id:
        next_id += 1
      if code == cross_condition:
        cross_segments.append((s, s + length, tid))
      for j in range(k):
        cols["starts"].append(s + j * stride)
        cols["labels"].append(code)
        cols["trial_ids"].append(tid)
        cols["sub_idx"].append(j)
        cols["offsets"].append(j * stride)
  arr = {k: np.asarray(v, dtype=np.int64) for k, v in cols.items()}
  return WindowIndex(arr["starts"], arr["labels"], arr["trial_ids"], arr["sub_idx"], arr["offsets"], skipped)


def cut_windows(x: np.ndarray, starts: np.ndarray, n: int) -> np.ndarray:
  """Windows `x[..., s:s + n]` for each start: `(n_windows, C, n)` for `x (C, T)`. ValueError if one leaves `x`."""
  x = np.asarray(x)
  if x.ndim != 2:
    raise ValueError(f"x must be (C, T), got {x.shape}")
  s = np.asarray(starts, dtype=np.int64)
  if len(s) and (s.min() < 0 or s.max() + n > x.shape[1]):
    raise ValueError(f"window [{s.min()}, {s.max() + n}) outside the recording of {x.shape[1]} samples")
  return np.stack([x[:, i:i + n] for i in s]) if len(s) else np.empty((0, x.shape[0], n), x.dtype)


# --- filter banks -------------------------------------------------------------------

@dataclass(frozen=True)
class BandFilter:
  """One sub-band filter: `sos` (continuous, `sosfiltfilt`) and `ba` (per-window legacy, `filtfilt`) of the
  same design; `low`/`high` are the design edges in Hz."""
  name: str
  low: float
  high: float
  sos: np.ndarray
  ba: tuple


def fbcca_filter_bank(fs: float) -> list:
  """FBCCA bank of P05: 3 Chebyshev-I band-passes (order 4, 3 dB ripple) from 6, 14, 22 Hz to
  `min(90, fs/2 - 1)` Hz."""
  high = min(SUBBAND_HIGH_HZ, fs / 2.0 - 1.0)
  return [BandFilter(f"cheb_{lo:g}-{high:g}", lo, high,
                     cheby1(CHEBY_ORDER, CHEBY_RIPPLE_DB, [lo, high], btype="band", fs=fs, output="sos"),
                     cheby1(CHEBY_ORDER, CHEBY_RIPPLE_DB, [lo, high], btype="band", fs=fs))
          for lo in SUBBAND_LOW_HZ]


def fbcsp_filter_bank(fs: float, subbands: Sequence[tuple] = tuple(DEFAULT_SUBBANDS), order: int = 4) -> list:
  """FBCSP bank of P05: Butterworth order 4 band-passes on `DEFAULT_SUBBANDS` (7-12, 13-17, 18-26, 27-36,
  38-52 Hz), the upper edge capped at `fs/2 - 1` Hz."""
  out = []
  for lo, hi in subbands:
    hi = min(float(hi), fs / 2.0 - 1.0)
    out.append(BandFilter(f"butter_{lo:g}-{hi:g}", float(lo), hi,
                          butter(order, [lo, hi], btype="band", fs=fs, output="sos"),
                          butter(order, [lo, hi], btype="band", fs=fs)))
  return out


def filter_bank(name: str, fs: float) -> list:
  """`fbcca_filter_bank(fs)` or `fbcsp_filter_bank(fs)` by name; ValueError for any other name."""
  if name == "fbcca":
    return fbcca_filter_bank(fs)
  if name == "fbcsp":
    return fbcsp_filter_bank(fs)
  raise ValueError(f"unknown filter bank {name!r}; choose from {BANK_NAMES}")


def band_windows(broadband: np.ndarray, starts: np.ndarray, n: int, bank: Sequence[BandFilter],
                 mode: str) -> np.ndarray:
  """Sub-band windows `(n_windows, n_bands, C, n)` of the broadband-filtered recording `(C, T)` (R6 layout).

  `mode="continuous"`: each band filters the whole recording zero-phase (`sosfiltfilt`), then the windows are
  cut (R3). `mode="per_window"` (legacy, PF-14): windows are cut first and each is filtered alone with
  `filtfilt(b, a)`, as the P05 extractors did.
  """
  if mode not in MODES:
    raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
  x = np.asarray(broadband, dtype=np.float64)
  if x.ndim != 2:
    raise ValueError(f"broadband must be (C, T), got {x.shape}")
  if not len(bank):
    raise ValueError("empty filter bank")
  if mode == "continuous":
    return np.stack([cut_windows(sosfiltfilt(b.sos, x, axis=-1), starts, n) for b in bank], axis=1)
  w = cut_windows(x, starts, n)
  return np.stack([filtfilt(b.ba[0], b.ba[1], w, axis=-1) for b in bank], axis=1)


def select_clean_bands(bands: np.ndarray, valid_mask: np.ndarray,
                       channels_kept_idx: Optional[Sequence[int]] = None) -> np.ndarray:
  """`bands (n, B, C, T)` restricted to the valid windows (`valid_mask == 1`) and, if given, the kept channels
  (positions in the input; PF-06). ValueError if the mask length differs from `n`."""
  b = np.asarray(bands)
  keep = np.asarray(valid_mask).reshape(-1) == 1
  if len(keep) != len(b):
    raise ValueError(f"valid_mask has {len(keep)} entries for {len(b)} windows")
  b = b[keep]
  return b if channels_kept_idx is None else b[:, :, np.asarray(channels_kept_idx, dtype=int), :]
