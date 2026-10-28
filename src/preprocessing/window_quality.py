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

Source (P19): `params["source"]` is `filtered`, `raw` or `both` (required, no default). The raw signal is the
unfiltered continuous recording and `raw_windows` its windows at the same starts (never filtered per window, R3).
A channel is dropped if it exceeds `channel_fail_fraction` on any checked signal; the window tier and the
artifact guard then use the surviving channels only, on every checked signal; artifact blocks are searched on each
checked continuous signal with the same `guard_sec` (one guard per subject, R5).

Reason codes (`reject_reason.npy`), by precedence: 0 valid, 1 failed the Vpp/std gate on the filtered window, 2
within the guard of a filtered-signal artifact, 3 passes every filtered check but fails a raw check (raw gate or
raw-artifact guard; with `source=raw` every rejection is 3). `valid_mask_no_guard` is the decision without any
guard. `params` has no defaults: a missing key raises (R5).
"""

from typing import Callable, Optional, Sequence

import numpy as np
from scipy.signal import sosfiltfilt

from src.preprocessing.signal.quality_check import compute_channel_quality_stats, validate_eeg_windows

PARAM_KEYS = ("vpp_min", "vpp_max", "std_min", "std_max", "channel_fail_fraction", "artifact_block_sec",
              "guard_sec", "guard_rel_amplitude", "source")
SOURCES = ("filtered", "raw", "both")
REASONS = {0: "valid", 1: "own_gate", 2: "guard", 3: "raw"}
MAX_RINGING_SEC = 60.0


def quality_params_from_config(cfg: dict) -> dict:
  """Flat `params` for `subject_quality_gate` from the config `quality:` block (every key required).

  `vpp_range_uv: [lo, hi]` and `std_range_uv: [lo, hi]` become `vpp_min, vpp_max, std_min, std_max`;
  `guard_sec` stays `"auto"` or a float. ValueError names the missing key.
  """
  q = cfg.get("quality") or {}
  need = ("vpp_range_uv", "std_range_uv", "channel_fail_fraction", "artifact_block_sec", "guard_sec",
          "guard_rel_amplitude", "source")
  missing = [k for k in need if k not in q]
  if missing:
    raise ValueError(f"config quality: is missing {missing}")
  guard = q["guard_sec"]
  return {"vpp_min": float(q["vpp_range_uv"][0]), "vpp_max": float(q["vpp_range_uv"][1]),
          "std_min": float(q["std_range_uv"][0]), "std_max": float(q["std_range_uv"][1]),
          "channel_fail_fraction": float(q["channel_fail_fraction"]),
          "artifact_block_sec": float(q["artifact_block_sec"]),
          "guard_sec": "auto" if guard == "auto" else float(guard),
          "guard_rel_amplitude": float(q["guard_rel_amplitude"]), "source": _check_source(q["source"])}


class AllChannelsDropped(ValueError):
  """Every channel exceeds `channel_fail_fraction` on a checked signal (a recorded result, PF-07)."""


def _check_source(source) -> str:
  if source not in SOURCES:
    raise ValueError(f"quality source must be one of {SOURCES}, got {source!r}")
  return source


def _check_params(params: dict) -> dict:
  missing = [k for k in PARAM_KEYS if k not in params]
  if missing:
    raise ValueError(f"params must name every threshold explicitly (R5); missing {missing}")
  _check_source(params["source"])
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
  """`{label: {"total", "valid", "own_gate", "guard", "raw"}}` counts (reasons 0/1/2/3) per condition and reason code."""
  y, r = np.asarray(labels), np.asarray(reason)
  out = {}
  for lab in sorted(set(int(v) for v in y)):
    rr = r[y == lab]
    out[lab] = {"total": int(len(rr)), **{name: int((rr == code).sum()) for code, name in REASONS.items()}}
  return out


def _signal_gate(w: np.ndarray, names: list, p: dict, what: str) -> dict:
  """Channel stats and dropped channels of one checked signal (`compute_channel_quality_stats`, strictly >)."""
  limits = {"vpp_min": p["vpp_min"], "vpp_max": p["vpp_max"], "std_min": p["std_min"], "std_max": p["std_max"]}
  stats = compute_channel_quality_stats(w, names, limits)
  return {"stats": stats, "dropped": {n for n, s in stats.items() if s["fail_fraction"] > p["channel_fail_fraction"]},
          "limits": limits, "what": what}


def subject_quality_gate(windows: np.ndarray, starts: np.ndarray, broadband: np.ndarray, fs: float,
                         channel_names: Sequence[str], filters: Sequence, params: dict,
                         labels: Optional[np.ndarray] = None, raw_windows: Optional[np.ndarray] = None,
                         raw: Optional[np.ndarray] = None) -> dict:
  """The shared quality decision of one subject (module docstring).

  `windows (n, C, T)`: the broadband-filtered windows of all channels at `starts (n,)` of the continuous
  filtered recording `broadband (C, T)`; `raw_windows (n, C, T)` / `raw (C, T)`: the unfiltered windows at the
  same starts and the unfiltered continuous recording (required unless `params["source"] == "filtered"`, then
  ignored); `filters`: everything applied to the continuous signal (for `guard_sec="auto"`); `params`: the
  keys of `PARAM_KEYS`, none defaulted; `labels (n,)` optional, for `rejections_by_label`. Returns
  `valid_mask`, `valid_mask_no_guard` `(n,)` int8, `reason (n,)` int8, `channels_kept`, `channels_kept_idx`,
  `channels_dropped`, `channel_stats` (fail fractions of the filtered windows, of the raw ones when
  `source=raw`), `channel_stats_raw` (None unless raw is checked), `guard_sec`, `guard_samples`,
  `artifact_fraction`, `guarded_fraction`, `n_artifact_blocks` (of the primary signal, as above),
  `n_raw_gate`, `n_raw_guard` (reason-3 windows failing a raw window gate / only the raw guard), the
  `*_raw` artifact statistics, `rejections_by_label` (None without labels), `n_windows`, `source`, `params`.
  `AllChannelsDropped` (a ValueError) if every channel is dropped, ValueError on a missing key or shape.
  """
  p = _check_params(params)
  src = p["source"]
  use_f, use_r = src in ("filtered", "both"), src in ("raw", "both")
  names = list(channel_names)
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T), got {w.shape}")
  starts = np.asarray(starts, dtype=np.int64)
  if len(starts) != len(w):
    raise ValueError(f"{len(starts)} starts for {len(w)} windows")
  if np.asarray(broadband).shape[0] != w.shape[1]:
    raise ValueError(f"broadband has {np.asarray(broadband).shape[0]} channels, windows {w.shape[1]}")
  if len(names) != w.shape[1]:
    raise ValueError(f"{len(names)} channel names for {w.shape[1]} channels")
  rw = None
  if use_r:
    if raw_windows is None or raw is None:
      raise ValueError(f"source={src!r} needs raw_windows and raw")
    rw = np.asarray(raw_windows, dtype=np.float64)
    if rw.shape != w.shape:
      raise ValueError(f"raw_windows {rw.shape} differ from windows {w.shape}")
    if np.asarray(raw).shape[0] != w.shape[1]:
      raise ValueError(f"raw has {np.asarray(raw).shape[0]} channels, windows {w.shape[1]}")
  checked = ([("filtered", w)] if use_f else []) + ([("raw", rw)] if use_r else [])
  gates = {k: _signal_gate(x, names, p, k) for k, x in checked}
  dropped = set().union(*[g["dropped"] for g in gates.values()])
  kept = [c for c in names if c not in dropped]
  if not kept:
    raise AllChannelsDropped(f"all {len(names)} channels fail the limits in > "
                             f"{p['channel_fail_fraction']:.0%} of the windows (source={src})")
  kept_idx = np.array([names.index(c) for c in kept], dtype=int)
  limits = next(iter(gates.values()))["limits"]
  ok = {k: np.asarray(validate_eeg_windows(x[:, kept_idx], **limits)).astype(bool) for k, x in checked}
  guard = (ringing_time_sec(filters, fs, p["guard_rel_amplitude"]) if p["guard_sec"] == "auto"
           else float(p["guard_sec"]))
  n_win = w.shape[-1]
  signals = {"filtered": broadband, "raw": raw}
  art, over = {}, {}
  for k, _ in checked:
    art[k] = artifact_mask(np.asarray(signals[k])[kept_idx], fs, p["artifact_block_sec"], p["vpp_max"], guard)
    over[k] = overlaps_mask(art[k]["samples"], starts, n_win) if len(w) else np.zeros(0, bool)
  none = np.zeros(len(w), dtype=bool)
  f_gate = ~ok["filtered"] if use_f else none
  f_over = over["filtered"] if use_f else none
  r_gate = ~ok["raw"] if use_r else none
  r_over = over["raw"] if use_r else none
  no_guard = ~(f_gate | r_gate)
  valid = (no_guard & ~f_over & ~r_over).astype(np.int8)
  r_fail = r_gate | r_over
  reason = np.where(f_gate, 1, np.where(f_over, 2, np.where(r_fail, 3, 0))).astype(np.int8)
  r3 = reason == 3
  prim = "filtered" if use_f else "raw"
  return {"valid_mask": valid, "valid_mask_no_guard": no_guard.astype(np.int8), "reason": reason,
          "channels_kept": kept, "channels_kept_idx": kept_idx, "channels_dropped": [c for c in names if c in dropped],
          "channel_stats": gates[prim]["stats"], "channel_stats_raw": gates["raw"]["stats"] if use_r else None,
          "guard_sec": float(guard), "guard_samples": int(round(guard * fs)),
          "artifact_fraction": float(art[prim]["artifact_fraction"]),
          "guarded_fraction": float(art[prim]["guarded_fraction"]),
          "n_artifact_blocks": int(art[prim]["block_flags"].sum()),
          "n_artifact_blocks_raw": int(art["raw"]["block_flags"].sum()) if use_r else None,
          "artifact_fraction_raw": float(art["raw"]["artifact_fraction"]) if use_r else None,
          "guarded_fraction_raw": float(art["raw"]["guarded_fraction"]) if use_r else None,
          "n_raw_gate": int((r3 & r_gate).sum()), "n_raw_guard": int((r3 & ~r_gate).sum()),
          "rejections_by_label": None if labels is None else rejections_by_label(labels, reason),
          "n_windows": int(len(w)), "source": src, "params": dict(p)}
