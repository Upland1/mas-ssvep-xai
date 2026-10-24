"""Window quality gates (P02: the legacy per-window Vpp/std gate).

A window is an array `(C, T)`; a stack of windows is `(n, C, T)`. Per channel,
`vpp = ptp(x)` and `std = std(x)` (population, ddof 0) along the time axis. A
window is valid when **every** channel has `vpp_min <= vpp <= vpp_max` and
`std_min <= std <= std_max` (bounds inclusive; NaN fails).

`validate_eeg_windows` keeps the shared defaults of the roadmap
(`vpp_min=5.0, vpp_max=120.0, std_min=1.0, std_max=35.0`). Those defaults are
**not** the legacy raw-gate limits: the legacy path passes every threshold
explicitly (PF-07). The other helpers of this module take their thresholds as
required keyword arguments, so no caller can inherit one silently (R5).

`quality_stats` is a plain dict accumulator (see `new_quality_stats`) that the
extractors of `src/features/ssvep/psd_extraction.py` update in place, so a
script can report rejected windows per condition and per reason.
"""

from typing import Optional, Sequence

import numpy as np

# Reason names, in the order they are reported.
REJECT_REASONS = ("vpp_low", "vpp_high", "std_low", "std_high")


def _as_window_stack(windows: np.ndarray) -> np.ndarray:
  """`(n, C, T)` float64 view of `windows`; a single `(C, T)` window becomes `(1, C, T)`."""
  w = np.asarray(windows, dtype=np.float64)
  if w.ndim == 2:
    w = w[np.newaxis]
  if w.ndim != 3:
    raise ValueError(f"windows must be (n, C, T) or (C, T), got shape {w.shape}")
  return w


def window_quality_flags(windows: np.ndarray, *, vpp_min: float, vpp_max: float,
                         std_min: float, std_max: float) -> dict:
  """Per-window, per-channel quality measures and flags (legacy helper).

  `windows` is `(n, C, T)` (or one `(C, T)` window). Thresholds are required
  keywords (R5, PF-07). Returns a dict of arrays:
  `vpp`, `std` `(n, C)` float64; `vpp_low`, `vpp_high`, `std_low`, `std_high`
  `(n, C)` bool (True = that channel fails for that reason); `channel_ok`
  `(n, C)` bool; `valid` `(n,)` int (1 if every channel is ok, else 0).
  A NaN value fails both of its bounds.
  """
  w = _as_window_stack(windows)
  vpp = np.ptp(w, axis=-1)
  std = np.std(w, axis=-1)
  vpp_ok = (vpp >= vpp_min) & (vpp <= vpp_max)
  std_ok = (std >= std_min) & (std <= std_max)
  channel_ok = vpp_ok & std_ok
  return {
    "vpp": vpp,
    "std": std,
    "vpp_low": ~(vpp >= vpp_min),
    "vpp_high": ~(vpp <= vpp_max),
    "std_low": ~(std >= std_min),
    "std_high": ~(std <= std_max),
    "channel_ok": channel_ok,
    "valid": np.all(channel_ok, axis=-1).astype(int),
  }


def validate_eeg_windows(windows: np.ndarray, vpp_min: float = 5.0, vpp_max: float = 120.0,
                         std_min: float = 1.0, std_max: float = 35.0) -> np.ndarray:
  """Quality mask, one int per window: 1 if every channel passes, else 0.

  A channel passes when `vpp_min <= ptp <= vpp_max` and `std_min <= std <=
  std_max` along the last axis (bounds inclusive). `windows` is `(n, C, T)`;
  a single `(C, T)` window gives a mask of length 1. The defaults are the
  shared gate's (roadmap P02.1); the legacy raw gate must pass all four
  thresholds, in particular `vpp_min=0.5` (PF-07).
  """
  return window_quality_flags(windows, vpp_min=vpp_min, vpp_max=vpp_max,
                              std_min=std_min, std_max=std_max)["valid"]


def filter_dataset(X: np.ndarray, y: np.ndarray, mask: np.ndarray) -> tuple:
  """`(X[keep], y[keep])` with `keep = mask == 1`, along the first axis.

  Raises ValueError when `X`, `y` and `mask` differ in length.
  """
  X = np.asarray(X)
  y = np.asarray(y)
  mask = np.asarray(mask).reshape(-1)
  if not len(X) == len(y) == len(mask):
    raise ValueError(f"length mismatch: X {len(X)}, y {len(y)}, mask {len(mask)}")
  keep = mask == 1
  return X[keep], y[keep]


def segment_and_validate_eeg(eeg: np.ndarray, fs: float, window_sec: float = 1.0, *,
                             vpp_min: float, vpp_max: float, std_min: float,
                             std_max: float) -> tuple:
  """Cut a continuous `(C, T)` signal into non-overlapping windows and gate them (legacy helper).

  Window length `int(window_sec * fs)` samples; window k covers samples
  `[k*n, (k+1)*n)`; a trailing remainder shorter than `n` is dropped. Returns
  `(windows (n_win, C, n), mask (n_win,) int)` with the mask of
  `validate_eeg_windows` at the given (required) thresholds. Filter the
  continuous signal before calling this (R3).
  """
  x = np.asarray(eeg, dtype=np.float64)
  if x.ndim != 2:
    raise ValueError(f"eeg must be (C, T), got shape {x.shape}")
  n = int(window_sec * fs)
  if n <= 0:
    raise ValueError(f"window of {window_sec} s at fs {fs} has no samples")
  n_win = x.shape[1] // n
  windows = x[:, :n_win * n].reshape(x.shape[0], n_win, n).transpose(1, 0, 2).copy()
  mask = validate_eeg_windows(windows, vpp_min=vpp_min, vpp_max=vpp_max,
                              std_min=std_min, std_max=std_max)
  return windows, mask


def summarize_window_quality(windows: np.ndarray, *, vpp_min: float, vpp_max: float,
                             std_min: float, std_max: float, label: Optional[str] = None,
                             verbose: bool = True) -> dict:
  """Observed Vpp/std ranges against the thresholds (PF-07 diagnostic).

  Returns a dict: `n_windows`, `n_valid`, `n_rejected`, `vpp_min_obs`,
  `vpp_median_obs`, `vpp_max_obs`, `std_min_obs`, `std_median_obs`,
  `std_max_obs` (over all windows and channels; NaN when there are none),
  `reasons` (windows failing for each reason of `REJECT_REASONS`, a window
  may count under several) and `thresholds`. Prints one block when `verbose`.
  """
  flags = window_quality_flags(windows, vpp_min=vpp_min, vpp_max=vpp_max,
                               std_min=std_min, std_max=std_max)
  vpp, std = flags["vpp"], flags["std"]
  n = int(vpp.shape[0])

  def _stat(fn, a):
    return float(fn(a)) if a.size else float("nan")

  out = {
    "n_windows": n,
    "n_valid": int(flags["valid"].sum()),
    "n_rejected": n - int(flags["valid"].sum()),
    "vpp_min_obs": _stat(np.nanmin, vpp), "vpp_median_obs": _stat(np.nanmedian, vpp),
    "vpp_max_obs": _stat(np.nanmax, vpp),
    "std_min_obs": _stat(np.nanmin, std), "std_median_obs": _stat(np.nanmedian, std),
    "std_max_obs": _stat(np.nanmax, std),
    "reasons": {r: int(np.any(flags[r], axis=-1).sum()) for r in REJECT_REASONS},
    "thresholds": {"vpp_min": vpp_min, "vpp_max": vpp_max, "std_min": std_min, "std_max": std_max},
  }
  if verbose:
    head = f"[quality] {label}: " if label else "[quality] "
    print(f"{head}{out['n_valid']}/{n} windows valid, {out['n_rejected']} rejected")
    print(f"  Vpp observed {out['vpp_min_obs']:.3f} / {out['vpp_median_obs']:.3f} / "
          f"{out['vpp_max_obs']:.3f} uV (min/median/max) vs limits [{vpp_min:g}, {vpp_max:g}]")
    print(f"  std observed {out['std_min_obs']:.3f} / {out['std_median_obs']:.3f} / "
          f"{out['std_max_obs']:.3f} uV (min/median/max) vs limits [{std_min:g}, {std_max:g}]")
    print("  rejected by reason: " + ", ".join(f"{r} {out['reasons'][r]}" for r in REJECT_REASONS))
  return out


# --- quality_stats accumulator -------------------------------------------------

def _new_counts() -> dict:
  return {"n_total": 0, "n_accepted": 0, "n_rejected": 0,
          "reasons": {r: 0 for r in REJECT_REASONS}}


def new_quality_stats() -> dict:
  """Empty `quality_stats` accumulator.

  Keys: `n_total`, `n_accepted`, `n_rejected` (sub-windows gated);
  `reasons` {reason: rejected windows failing it on any channel; a window may
  count under several}; `by_condition` {code: same four keys}; `rejected`
  (list of dicts `condition`, `onset`, `start`, `sub_index`, `reasons`,
  `channels` = failing channel indices); `skipped_segments` (list of dicts
  `condition`, `onset`, `why` for segments that do not fit the recording).
  `condition`, `onset` and `start` are None when the gate ran outside
  `process_condition_windows_with_baseline`.
  """
  stats = _new_counts()
  stats.update({"by_condition": {}, "rejected": [], "skipped_segments": []})
  return stats


def ensure_quality_stats(stats: dict) -> dict:
  """Fill the missing keys of a (possibly empty) accumulator in place; return it."""
  for k, v in new_quality_stats().items():
    stats.setdefault(k, v)
  for r in REJECT_REASONS:
    stats["reasons"].setdefault(r, 0)
  return stats


def update_quality_stats(stats: dict, flags: dict, condition: Optional[int] = None,
                         onset: Optional[int] = None,
                         starts: Optional[Sequence[int]] = None) -> dict:
  """Add one gated batch (the output of `window_quality_flags`) to `stats` in place.

  `condition` adds the counts to `by_condition[condition]` too; `onset` and
  `starts` (absolute start sample per window) are copied into each rejected
  entry. Returns `stats`.
  """
  ensure_quality_stats(stats)
  valid = np.asarray(flags["valid"]).astype(bool)
  n, n_ok = int(valid.size), int(valid.sum())
  targets = [stats]
  if condition is not None:
    targets.append(stats["by_condition"].setdefault(int(condition), _new_counts()))
  for t in targets:
    t["n_total"] += n
    t["n_accepted"] += n_ok
    t["n_rejected"] += n - n_ok
    for r in REJECT_REASONS:
      t["reasons"][r] += int(np.sum(np.any(flags[r], axis=-1) & ~valid))
  for k in np.flatnonzero(~valid):
    stats["rejected"].append({
      "condition": None if condition is None else int(condition),
      "onset": None if onset is None else int(onset),
      "start": None if starts is None else int(starts[k]),
      "sub_index": int(k),
      "reasons": [r for r in REJECT_REASONS if np.any(flags[r][k])],
      "channels": [int(c) for c in np.flatnonzero(~flags["channel_ok"][k])],
    })
  return stats


def merge_quality_stats(dst: dict, src: dict, condition: Optional[int] = None,
                        onset: Optional[int] = None, segment_start: Optional[int] = None,
                        sub_window_samples: Optional[int] = None) -> dict:
  """Add accumulator `src` to `dst` in place; return `dst`.

  Totals and reasons are summed; `src["by_condition"]` is summed into
  `dst["by_condition"]`. With `condition`, all of `src`'s top-level counts
  are also added to `dst["by_condition"][condition]`, and rejected entries
  without a condition get it (likewise `onset`; `start = segment_start +
  sub_index * sub_window_samples` when both are given). Use it to fold one
  segment into a subject, or subjects into a cohort.
  """
  ensure_quality_stats(dst)
  src = ensure_quality_stats(src)

  def _add(t, c):
    for k in ("n_total", "n_accepted", "n_rejected"):
      t[k] += c[k]
    for r in REJECT_REASONS:
      t["reasons"][r] += c["reasons"].get(r, 0)

  _add(dst, src)
  for code, c in src["by_condition"].items():
    _add(dst["by_condition"].setdefault(int(code), _new_counts()), c)
  if condition is not None:
    _add(dst["by_condition"].setdefault(int(condition), _new_counts()), src)
  for e in src["rejected"]:
    e = dict(e)
    if e.get("condition") is None and condition is not None:
      e["condition"] = int(condition)
    if e.get("onset") is None and onset is not None:
      e["onset"] = int(onset)
    if e.get("start") is None and segment_start is not None and sub_window_samples is not None:
      e["start"] = int(segment_start + e["sub_index"] * sub_window_samples)
    dst["rejected"].append(e)
  dst["skipped_segments"].extend(dict(e) for e in src["skipped_segments"])
  return dst


def format_quality_stats(stats: dict, channel_names: Optional[Sequence[str]] = None) -> str:
  """Multi-line text of an accumulator: totals, per condition, per reason, each rejected window."""
  stats = ensure_quality_stats(dict(stats))

  def _reasons(c):
    return ", ".join(r + " " + str(c["reasons"][r]) for r in REJECT_REASONS)

  lines = [f"gated {stats['n_total']}: accepted {stats['n_accepted']}, "
           f"rejected {stats['n_rejected']} ({_reasons(stats)})"]
  for code in sorted(stats["by_condition"]):
    c = stats["by_condition"][code]
    lines.append(f"  {code}: accepted {c['n_accepted']}/{c['n_total']}, "
                 f"rejected {c['n_rejected']} ({_reasons(c)})")
  for e in stats["rejected"]:
    chans = e["channels"]
    if channel_names is not None:
      chans = [channel_names[c] for c in chans]
    lines.append(f"  rejected: condition {e['condition']} onset {e['onset']} start {e['start']}"
                 f" sub {e['sub_index']} reasons {e['reasons']} channels {chans}")
  for e in stats["skipped_segments"]:
    lines.append(f"  skipped segment: condition {e['condition']} onset {e['onset']} ({e['why']})")
  return "\n".join(lines)
