"""The one loader of subject windows for every analysis from P16 on (P16.6, R3, R5, R8, 01_DATA_SPEC 5).

`load_subject(sub_dir, ...)` reads either

- a **built** folder (`scripts/build_windows.py`, `windows_meta.json` present): all 8 channels, true trial
  ids, saved sub-bands, the shared quality decision (`valid_mask`, `valid_mask_no_guard`), `fs` from the
  metadata (256 Hz); or
- a **legacy** folder (`data/processed/<S>/`, P02): 7 channels, no sampling rate stored (`fs = 250.0`, the
  historical assumption, labelled `fs_source = "legacy-assumed"`; `fs_override` replaces it), trial ids
  reconstructed from contiguous label blocks (`trial_ids_approximate` reports when the gate broke a block,
  PF-03), the per-script two-tier gate of P07 as the only quality decision.

and returns the same dict, so an analysis never cares which. Rows are the selected `conditions` that pass
the quality decision, columns only the kept channels (by name, PF-06). `smoothing` is the R8 rule that fits
the folder: `"trial"` (built: reset at every true trial id; rows are ordered by trial then offset) or
`"mod5"` (legacy `i % 5` of the clean array).

`quality_mode`: `"shared"` (built: `valid_mask`), `"shared-no-guard"` (built: `valid_mask_no_guard`) or
`"per-script"` (the P07 two-tier gate rerun on the selected windows, explicit thresholds; legacy folders
only have this one, so every mode means it there and `quality["source"]` says so).
"""

import json
import re
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.features.ssvep.window_mask import channel_report, quality_gate
from src.io.channels import FULL_MONTAGE, resolve_channel_names, subject_channel_names  # noqa: F401 (re-export)
from src.preprocessing.dataset.cv_utils import LEGACY_TRIAL_LENGTHS, build_trial_ids, trial_block_report

SUBJECT_PATTERN = re.compile(r"^S\d+$")
QUALITY_MODES = ("shared", "shared-no-guard", "per-script")
CLASS_CODES = (101, 102, 103, 104, 105)
META_FILE = "windows_meta.json"
BUILT_FILES = ("X_time_windows", "y_labels", "trial_ids", "window_starts", "sub_idx", "window_offsets",
               "valid_mask", "valid_mask_no_guard", "reject_reason")
LEGACY_FILES = ("X_time_windows", "y_labels")


def find_project_root(start: Optional[Path] = None) -> Path:
  """Repository root: the first parent of `start` (default: this file) holding configs/pipeline_config.yaml."""
  here = Path(start if start is not None else __file__).resolve()
  for parent in [here, *here.parents]:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  raise FileNotFoundError(f"no configs/pipeline_config.yaml above {here}")


def is_built(sub_dir) -> bool:
  """True for a folder written by `build_windows.py` (has `windows_meta.json` and `trial_ids.npy`)."""
  d = Path(sub_dir)
  return (d / META_FILE).is_file() and (d / "trial_ids.npy").is_file()


def discover_subjects(data_root) -> list:
  """Subject folders `S\\d+` of `data_root` that hold built or legacy windows, in numeric order."""
  root = Path(data_root)
  found = [p.name for p in root.iterdir() if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name)
           and (is_built(p) or all((p / f"{n}.npy").is_file() for n in LEGACY_FILES))]
  return sorted(found, key=lambda s: int(s[1:]))


def built_dir_name(filter_mode: str, window_sec: Optional[float] = None, stride_sec: Optional[float] = None) -> str:
  """`processed_<filter_mode>` or `processed_<filter_mode>/w<len>_s<stride>` (01_DATA_SPEC 5.2)."""
  base = f"processed_{filter_mode}"
  if window_sec is None and stride_sec is None:
    return base
  return f"{base}/w{window_sec:g}_s{stride_sec:g}"


def _check_trial_order(trial_ids: np.ndarray, offsets: np.ndarray) -> None:
  """Rows must be grouped by trial id with strictly increasing offsets inside it (R8); RuntimeError otherwise."""
  if len(trial_ids) == 0:
    return
  new = np.concatenate([[True], trial_ids[1:] != trial_ids[:-1]])
  if new.sum() != len(np.unique(trial_ids)):
    raise RuntimeError("a trial id appears in more than one run of rows (rows not grouped by trial)")
  same = ~new
  if np.any(np.diff(offsets)[same[1:]] <= 0):
    raise RuntimeError("window offsets do not increase inside a trial (rows not ordered by (trial, offset))")


def _per_script_gate(X: np.ndarray, y: np.ndarray, names: Sequence[str], thresholds: Optional[dict],
                     channel_fail_fraction: Optional[float]) -> dict:
  """The P07 two-tier gate on `X (n, C, T)` with explicit thresholds; the decision part of its result."""
  if thresholds is None or channel_fail_fraction is None:
    raise ValueError("the per-script gate needs explicit `thresholds` and `channel_fail_fraction` (R5); "
                     "none is inherited from a default")
  th = dict(thresholds)
  return channel_report(quality_gate(X, y, list(names), th, channel_fail_fraction))


def load_subject(sub_dir, conditions: Sequence[int] = CLASS_CODES, quality_mode: str = "shared",
                 bands: Sequence[str] = (), fs_override: Optional[float] = None,
                 scalp: Optional[Sequence[str]] = None, thresholds: Optional[dict] = None,
                 channel_fail_fraction: Optional[float] = None) -> dict:
  """Windows of one subject folder for the given condition codes (module docstring).

  Returns a dict with: `subject`, `sub_dir`, `built`, `source` (text for report headers), `filter_mode`
  (built: from the metadata; legacy: `"legacy"`), `fs`, `fs_source` (`meta` | `legacy-assumed` | `override`),
  `X` (n, C', T) windows of the kept channels, `y`, `trial_ids` (one per segment; the R8 smoothing key), `cv_groups` (the R1 group key: `trial_ids`, with a
  202 window in the group of its 201 twin, PF-13), `trial_ids_approximate`, `window_starts` /
  `sub_idx` / `offsets` (None on legacy folders), `bands` ({bank: (n, B, C', T)}), `channel_names` (kept),
  `channels_dropped`, `channels_all`, `smoothing` (`"trial"` | `"mod5"`), `n_trials`, `n_selected` (rows of the
  conditions before the quality decision), `n_rejected`, `quality` (`mode`, `source`, `valid_mask` over the
  selected rows, `rows` folder rows of the selected conditions, `channels_kept`, `channels_dropped`,
  `rejections_by_label`, `guard_sec`, `artifact_fraction`, `params` when built; `channel_stats` of the per-script
  gate (None for shared decisions); `per-script` thresholds
  otherwise) and `meta` (the metadata dict, `{}` on legacy folders).

  `thresholds` (the four limits) and `channel_fail_fraction` are REQUIRED whenever the per-script gate runs
  (`quality_mode="per-script"`, and every mode on a legacy folder): ValueError otherwise (R5). `bands` names saved banks (`"fbcca"`, `"fbcsp"`, ...) and exists on built folders only. `scalp` names the
  channels of a legacy folder without `channels.json`. Raises ValueError for an unknown mode, FileNotFoundError
  for a missing file, RuntimeError for rows that violate the layout.
  """
  if quality_mode not in QUALITY_MODES:
    raise ValueError(f"quality_mode must be one of {QUALITY_MODES}, got {quality_mode!r}")
  d = Path(sub_dir)
  conds = [int(c) for c in conditions]
  built = is_built(d)
  if built:
    return _load_built(d, conds, quality_mode, tuple(bands), fs_override, thresholds, channel_fail_fraction)
  if bands:
    raise ValueError(f"{d}: legacy folders have no saved sub-bands (bands={tuple(bands)}); build windows with "
                     "scripts/build_windows.py")
  return _load_legacy(d, conds, quality_mode, fs_override, scalp, thresholds, channel_fail_fraction)


def _fs(meta_fs: Optional[float], override: Optional[float]) -> tuple:
  if override is not None:
    if not override > 0:
      raise ValueError(f"fs_override must be positive, got {override}")
    return float(override), "override"
  if meta_fs is None:
    return LEGACY_FS_HZ, "legacy-assumed"
  return float(meta_fs), "meta"


def _load_built(d: Path, conds: list, mode: str, banks: tuple, fs_override, thresholds, fail_fraction) -> dict:
  for n in BUILT_FILES:
    if not (d / f"{n}.npy").is_file():
      raise FileNotFoundError(f"{d / (n + '.npy')} is missing (built folder, 01_DATA_SPEC 5.2)")
  meta = json.loads((d / META_FILE).read_text())
  load = lambda n: np.load(d / f"{n}.npy")
  y_all, ids_all, offs_all = load("y_labels"), load("trial_ids"), load("window_offsets")
  n_all = len(y_all)
  for n in BUILT_FILES:
    if len(np.load(d / f"{n}.npy", mmap_mode="r")) != n_all:
      raise RuntimeError(f"{d / (n + '.npy')}: length differs from y_labels ({n_all})")
  rows = np.flatnonzero(np.isin(y_all, conds))
  X_all = np.load(d / "X_time_windows.npy", mmap_mode="r")
  names_all = list(meta["channels"])
  if X_all.shape[1] != len(names_all):
    raise RuntimeError(f"{d}: X_time_windows has {X_all.shape[1]} channels, metadata names {names_all}")
  dq = meta.get("quality", {})
  if mode == "per-script":
    Xs = np.asarray(X_all[rows], dtype=np.float64)
    dec = _per_script_gate(Xs, y_all[rows], names_all, thresholds, fail_fraction)
    keep_local = np.asarray(dec["valid_mask"]).astype(bool)
    kept, dropped = list(dec["channels_kept"]), list(dec["channels_dropped"])
    source = "per-script P07 two-tier gate rerun on the built windows"
    params = {**thresholds, "channel_fail_fraction": fail_fraction}
    rej = None
    guard, art = None, None
  else:
    key = "valid_mask" if mode == "shared" else "valid_mask_no_guard"
    keep_local = load(key)[rows].astype(bool)
    kept, dropped = list(dq["channels_kept"]), list(dq["channels_dropped"])
    source = f"shared decision of the built folder ({key}), quality source {dq.get('source', 'filtered')}"
    params = dq.get("params")
    rej = None
    guard, art = dq.get("guard_sec"), dq.get("artifact_fraction")
  sel = rows[keep_local]
  kept_idx = [names_all.index(c) for c in kept]
  ids, offs = ids_all[sel], offs_all[sel]
  _check_trial_order(ids, offs)
  starts_all = load("window_starts")
  cv_groups = ids_all.copy()                      # PF-13: a 202 window overlaps a 201 window (same group)
  i201 = np.flatnonzero(y_all == 201)
  wlen = X_all.shape[2]
  for i in np.flatnonzero(y_all == 202):
    ov = np.minimum(starts_all[i201], starts_all[i]) + wlen - np.maximum(starts_all[i201], starts_all[i])  # overlap
    if len(ov) and ov.max() > 0:
      cv_groups[i] = ids_all[i201[int(ov.argmax())]]
  out_bands = {}
  for b in banks:
    f = d / f"X_bands_{b}.npy"
    if not f.is_file():
      raise FileNotFoundError(f"{f} is missing; build it with scripts/build_windows.py --banks {b}")
    out_bands[b] = np.asarray(np.load(f, mmap_mode="r")[sel][:, :, kept_idx, :], dtype=np.float64)
  fs, fs_src = _fs(meta.get("fs"), fs_override)
  reason = load("reject_reason")[rows]
  if mode != "per-script":
    rej = {int(lab): {"total": int((y_all[rows] == lab).sum()),
                      "valid": int(((y_all[rows] == lab) & keep_local).sum()),
                      "own_gate": int(((y_all[rows] == lab) & (reason == 1)).sum()),
                      "guard": int(((y_all[rows] == lab) & (reason == 2) & ~keep_local).sum()),
                      "raw": int(((y_all[rows] == lab) & (reason == 3) & ~keep_local).sum())}   # P19 C-2
           for lab in sorted(set(int(v) for v in y_all[rows]))}
  return {
    "subject": d.name, "sub_dir": str(d), "built": True,
    "source": f"{meta.get('filter_mode', '?')} build ({d.parent.name}/{d.name}), session {meta.get('session', '?')}",
    "filter_mode": meta.get("filter_mode"), "fs": fs, "fs_source": fs_src,
    "X": np.asarray(X_all[sel][:, kept_idx, :], dtype=np.float64), "y": y_all[sel], "trial_ids": ids,
    "cv_groups": cv_groups[sel], "trial_ids_approximate": False, "window_starts": starts_all[sel],
    "sub_idx": load("sub_idx")[sel], "offsets": offs, "bands": out_bands,
    "channel_names": kept, "channels_dropped": dropped, "channels_all": names_all,
    "smoothing": "trial", "n_trials": int(len(np.unique(ids))), "n_selected": int(len(rows)),
    "n_rejected": int(len(rows) - len(sel)),
    "quality": {"mode": mode, "source": source, "valid_mask": keep_local.astype(np.int8), "rows": rows,
                "channels_kept": kept, "channels_dropped": dropped, "rejections_by_label": rej,
                "guard_sec": guard, "artifact_fraction": art, "params": params},
    "meta": meta}


def _load_legacy(d: Path, conds: list, mode: str, fs_override, scalp, thresholds, fail_fraction) -> dict:
  for n in LEGACY_FILES:
    if not (d / f"{n}.npy").is_file():
      raise FileNotFoundError(f"{d / (n + '.npy')} is missing (legacy folder, 01_DATA_SPEC 5.1)")
  y_all = np.load(d / "y_labels.npy")
  X_all = np.load(d / "X_time_windows.npy")
  if len(X_all) != len(y_all):
    raise RuntimeError(f"{d}: X_time_windows {len(X_all)} rows, y_labels {len(y_all)}")
  # trial ids on the PRE-gate labels of the whole folder, then the condition selection (PF-03)
  ids_all = build_trial_ids(y_all, LEGACY_TRIAL_LENGTHS, warn=False)
  rows = np.flatnonzero(np.isin(y_all, conds))
  names = subject_channel_names(d.parent, d.name, X_all.shape[1], scalp)
  Xs, ys, ids_s = X_all[rows], y_all[rows], ids_all[rows]
  dec = _per_script_gate(Xs, ys, names, thresholds, fail_fraction)
  keep = np.asarray(dec["valid_mask"]).astype(bool)
  kept_idx = list(dec["channels_kept_idx"])
  rep = trial_block_report(ys, ids_s, LEGACY_TRIAL_LENGTHS)
  fs, fs_src = _fs(None, fs_override)
  ids = ids_s[keep]
  return {
    "subject": d.name, "sub_dir": str(d), "built": False,
    "source": f"legacy folder ({d.parent.name}/{d.name}), per-script gate", "filter_mode": "legacy",
    "fs": fs, "fs_source": fs_src, "X": np.asarray(Xs[keep][:, kept_idx, :], dtype=np.float64), "y": ys[keep],
    "trial_ids": ids, "trial_ids_approximate": bool(rep["approximate"]), "window_starts": None,
    "sub_idx": None, "offsets": None, "bands": {}, "channel_names": list(dec["channels_kept"]),
    "channels_dropped": list(dec["channels_dropped"]), "channels_all": list(names), "smoothing": "mod5",
    "n_trials": int(len(np.unique(ids))), "n_selected": int(len(rows)), "n_rejected": int(len(rows) - keep.sum()),
    "trial_block_report": rep,
    "quality": {"mode": mode, "source": "per-script P07 two-tier gate (legacy folders have no shared decision)",
                "valid_mask": keep.astype(np.int8), "rows": rows, "channels_kept": list(dec["channels_kept"]),
                "channel_stats": dec.get("channel_stats"),
                "channels_dropped": list(dec["channels_dropped"]), "rejections_by_label": None,
                "guard_sec": None, "artifact_fraction": None,
                "params": {**thresholds, "channel_fail_fraction": fail_fraction}},
    "meta": {}}
