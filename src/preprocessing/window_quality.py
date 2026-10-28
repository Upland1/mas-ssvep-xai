"""One shared quality decision per subject, with an artifact guard (P16.4, R5, PF-14, 01_DATA_SPEC 5.2).

`subject_quality_gate` decides, once per subject and for every analysis:

1. channel tier and window tier of P07 (`apply_artifact_quality_pipeline`, limits passed explicitly from
   the config `quality:` block): a channel failing the Vpp/std limits in strictly more than
   `channel_fail_fraction` of the windows is dropped for the whole subject; windows are then judged on
   the surviving channels only (reason 1 = fails its own Vpp/std gate);
2. an artifact guard: the continuous broadband-filtered signal is cut into `artifact_block_sec` blocks,
   every block whose Vpp exceeds `vpp_max` on any kept channel is an artifact, the artifact is dilated by
   `guard_sec` on both sides and any window overlapping the dilated region is rejected (reason 2).
   `guard_sec = "auto"` is the longest ringing time of all filters applied to the continuous signal,
   measured on the zero-phase impulse response as the largest distance from the impulse at which
   |h| exceeds `guard_rel_amplitude` (1 %) of its peak (`ringing_time_sec`).

Reason codes (`reject_reason.npy`): 0 valid, 1 failed the own Vpp/std gate, 2 within the guard of an
artifact, 3 failed the raw Vpp/std gate (P19, unused here: `source: filtered`). `valid_mask_no_guard` is the
decision without step 2. `params` has no defaults: a missing key raises (R5).
"""

from typing import Callable, Optional, Sequence

import numpy as np
from scipy.signal import sosfiltfilt

from src.preprocessing.signal.quality_check import apply_artifact_quality_pipeline

PARAM_KEYS = ("vpp_min", "vpp_max", "std_min", "std_max", "channel_fail_fraction", "artifact_block_sec",
              "guard_sec", "guard_rel_amplitude")
REASONS = {0: "valid", 1: "own_gate", 2: "guard", 3: "raw_gate"}
MAX_RINGING_SEC = 60.0


def quality_params_from_config(cfg: dict) -> dict:
  """Flat `params` for `subject_quality_gate` from the config `quality:` block (every key required).

  `vpp_range_uv: [lo, hi]` and `std_range_uv: [lo, hi]` become `vpp_min, vpp_max, std_min, std_max`;
  `guard_sec` stays `"auto"` or a float. ValueError names the missing key.
  """
  q = cfg.get("quality") or {}
  need = ("vpp_range_uv", "std_range_uv", "channel_fail_fraction", "artifact_block_sec", "guard_sec",
          "guard_rel_amplitude")
  missing = [k for k in need if k not in q]
  if missing:
    raise ValueError(f"config quality: is missing {missing}")
  guard = q["guard_sec"]
  return {"vpp_min": float(q["vpp_range_uv"][0]), "vpp_max": float(q["vpp_range_uv"][1]),
          "std_min": float(q["std_range_uv"][0]), "std_max": float(q["std_range_uv"][1]),
          "channel_fail_fraction": float(q["channel_fail_fraction"]),
          "artifact_block_sec": float(q["artifact_block_sec"]),
          "guard_sec": "auto" if guard == "auto" else float(guard),
          "guard_rel_amplitude": float(q["guard_rel_amplitude"])}


def _check_params(params: dict) -> dict:
  missing = [k for k in PARAM_KEYS if k not in params]
  if missing:
    raise ValueError(f"params must name every threshold explicitly (R5); missing {missing}")
  return params


def ringing_time_sec(filters: Sequence, fs: float, rel: float = 0.01, max_sec: float = MAX_RINGING_SEC) -> float:
  """Longest ringing time in seconds of `filters`, each applied zero-phase as in the pipeline.

  An item is a callable on a `(1, N)` array (e.g. the broadband filter) or an object with `.sos` (a
  `BandFilter`) or a raw `sos` array (applied with `sosfiltfilt`). A unit impulse in the middle of
  `N = 2 * max_sec * fs + 1` samples is filtered; the ringing is the largest distance (in samples) from the
  impulse at which `|h| > rel * max|h|`, divided by `fs`. ValueError if `|h|` is still above the limit at the
  end of the buffer (the filter rings longer than `max_sec`).
  """
  half = int(max_sec * fs)
  worst = 0
  for f in filters:
    imp = np.zeros((1, 2 * half + 1))
    imp[0, half] = 1.0
    if callable(f):
      h = np.asarray(f(imp), dtype=np.float64)[0]
    else:
      sos = getattr(f, "sos", f)
      h = sosfiltfilt(np.asarray(sos), imp, axis=-1)[0]
    above = np.flatnonzero(np.abs(h) > rel * np.abs(h).max())
    span = int(np.abs(above - half).max())
    if span >= half - 1:
      raise ValueError(f"filter rings longer than {max_sec:g} s at the {rel:g} level")
    worst = max(worst, span)
  return worst / float(fs)


def artifact_mask(signal: np.ndarray, fs: float, block_sec: float, vpp_max: float, guard_sec: float) -> dict:
  """Artifact blocks of a continuous `(C, T)` signal and their dilation.

  Blocks of `int(block_sec * fs)` samples (a shorter last block included); a block is an artifact when its
  Vpp exceeds `vpp_max` on any channel. Returns `block_flags (n_blocks,)` bool, `samples (T,)` bool (the
  blocks dilated by `int(round(guard_sec * fs))` samples each side), `artifact_fraction` (flagged blocks'
  samples / T, before dilation) and `guarded_fraction` (dilated samples / T).
  """
  x = np.asarray(signal, dtype=np.float64)
  if x.ndim != 2:
    raise ValueError(f"signal must be (C, T), got {x.shape}")
  T = x.shape[1]
  b = int(block_sec * fs)
  if b < 1:
    raise ValueError(f"block of {block_sec} s at fs {fs} has no samples")
  g = int(round(guard_sec * fs))
  edges = np.arange(0, T, b)
  flags = np.array([np.ptp(x[:, s:s + b], axis=-1).max() > vpp_max for s in edges], dtype=bool)
  diff = np.zeros(T + 1, dtype=np.int64)
  raw = 0
  for s in edges[flags]:
    e = min(s + b, T)
    raw += e - s
    diff[max(s - g, 0)] += 1
    diff[min(e + g, T)] -= 1
  mask = np.cumsum(diff[:-1]) > 0
  return {"block_flags": flags, "samples": mask, "artifact_fraction": raw / T if T else 0.0,
          "guarded_fraction": float(mask.mean()) if T else 0.0}


def overlaps_mask(mask: np.ndarray, starts: np.ndarray, n: int) -> np.ndarray:
  """True for every window `[s, s + n)` that contains at least one True sample of `mask`."""
  cs = np.concatenate([[0], np.cumsum(mask.astype(np.int64))])
  s = np.asarray(starts, dtype=np.int64)
  return (cs[s + n] - cs[s]) > 0


def rejections_by_label(labels: np.ndarray, reason: np.ndarray) -> dict:
  """`{label: {"total", "valid", "own_gate", "guard", "raw_gate"}}` counts per condition and reason code."""
  y, r = np.asarray(labels), np.asarray(reason)
  out = {}
  for lab in sorted(set(int(v) for v in y)):
    rr = r[y == lab]
    out[lab] = {"total": int(len(rr)), **{name: int((rr == code).sum()) for code, name in REASONS.items()}}
  return out


def subject_quality_gate(windows: np.ndarray, starts: np.ndarray, broadband: np.ndarray, fs: float,
                         channel_names: Sequence[str], filters: Sequence, params: dict,
                         labels: Optional[np.ndarray] = None) -> dict:
  """The shared quality decision of one subject (module docstring).

  `windows (n, C, T)`: the broadband-filtered windows of all channels at `starts (n,)` of the continuous
  filtered recording `broadband (C, T)`; `filters`: everything applied to the continuous signal (for
  `guard_sec="auto"`); `params`: the keys of `PARAM_KEYS`, none defaulted; `labels (n,)` optional, for
  `rejections_by_label`. Returns `valid_mask`, `valid_mask_no_guard` `(n,)` int8, `reason (n,)` int8,
  `channels_kept`, `channels_kept_idx`, `channels_dropped`, `channel_stats` (fail fractions), `guard_sec`,
  `guard_samples`, `artifact_fraction`, `guarded_fraction`, `n_artifact_blocks`, `rejections_by_label`
  (None without labels), `n_windows`, `params`. ValueError if every channel is dropped or a key is missing.
  """
  p = _check_params(params)
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got {w.shape}")
  starts = np.asarray(starts, dtype=np.int64)
  if len(starts) != len(w):
    raise ValueError(f"{len(starts)} starts for {len(w)} windows")
  if np.asarray(broadband).shape[0] != w.shape[1]:
    raise ValueError(f"broadband has {np.asarray(broadband).shape[0]} channels, windows {w.shape[1]}")
  q = apply_artifact_quality_pipeline(
    w, np.zeros(len(w), dtype=int), list(channel_names), vpp_min=p["vpp_min"], vpp_max=p["vpp_max"],
    std_min=p["std_min"], std_max=p["std_max"], channel_fail_fraction_thresh=p["channel_fail_fraction"],
    verbose=False)
  no_guard = np.asarray(q["valid_mask"]).astype(np.int8)
  kept_idx = np.asarray(q["channels_kept_idx"], dtype=int)
  guard = (ringing_time_sec(filters, fs, p["guard_rel_amplitude"]) if p["guard_sec"] == "auto"
           else float(p["guard_sec"]))
  art = artifact_mask(np.asarray(broadband)[kept_idx], fs, p["artifact_block_sec"], p["vpp_max"], guard)
  over = overlaps_mask(art["samples"], starts, w.shape[-1]) if len(w) else np.zeros(0, bool)
  valid = ((no_guard == 1) & ~over).astype(np.int8)
  reason = np.where(no_guard == 0, 1, np.where(over, 2, 0)).astype(np.int8)
  return {"valid_mask": valid, "valid_mask_no_guard": no_guard, "reason": reason,
          "channels_kept": list(q["channels_kept"]), "channels_kept_idx": kept_idx,
          "channels_dropped": list(q["channels_dropped"]), "channel_stats": q["channel_stats"],
          "guard_sec": float(guard), "guard_samples": int(round(guard * fs)),
          "artifact_fraction": float(art["artifact_fraction"]), "guarded_fraction": float(art["guarded_fraction"]),
          "n_artifact_blocks": int(art["block_flags"].sum()),
          "rejections_by_label": None if labels is None else rejections_by_label(labels, reason),
          "n_windows": int(len(w)), "params": dict(p)}
