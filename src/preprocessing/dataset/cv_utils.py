"""Trial ids and trial-grouped CV for legacy window folders (R1, R8; PF-01, PF-03; fixed in P11).

Legacy folders store no trial ids. A trial is `sub_windows_per_trial` consecutive windows of a
contiguous same-label block (5 per stimulus trial, 2 per 201, 1 per 202; 01_DATA_SPEC 5.1).
`build_trial_ids` walks the label array once; call it on the PRE-gate labels and index the result
with the same valid mask as the windows (PF-03): `ids[valid_mask]`; chain masks when two gates apply.
When a window was lost inside a block the chunks after it are shifted (the ids are then
approximate): the short last chunk gets its own id, a warning is issued, and the block is reported.
"""

import warnings
from pathlib import Path
from typing import Optional, Sequence, Union

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

N_FOLDS = 5
SEED = 42
LEGACY_TRIAL_LENGTHS = {201: 2, 202: 1, 101: 5, 102: 5, 103: 5, 104: 5, 105: 5}
CV_CHOICES = ("grouped", "legacy")
SMOOTHING_CHOICES = ("trial", "mod5")
LEGACY_DIR = "legacy_leaky"   # subfolder of the reports dir for `--cv legacy` outputs (P11)


def _length(spt: Union[int, dict], label: int) -> int:
  n = spt.get(int(label), 5) if isinstance(spt, dict) else int(spt)
  if n < 1:
    raise ValueError(f"sub_windows_per_trial must be >= 1, got {n}")
  return n


def contiguous_blocks(y: np.ndarray) -> list:
  """`[(label, start, length)]` of the maximal runs of equal labels, in array order."""
  y = np.asarray(y)
  if len(y) == 0:
    return []
  edges = np.flatnonzero(np.diff(y) != 0) + 1
  starts = np.concatenate([[0], edges])
  ends = np.concatenate([edges, [len(y)]])
  return [(int(y[s]), int(s), int(e - s)) for s, e in zip(starts, ends)]


def build_trial_ids(y: np.ndarray, sub_windows_per_trial: Union[int, dict] = 5,
                    return_truncated: bool = False, warn: bool = True):
  """Trial id per window from contiguous same-label blocks (consecutive chunks of the trial length).

  `sub_windows_per_trial`: int, or dict label -> length (labels absent from the dict use 5).
  A block whose length is not a multiple of the trial length ends in a short chunk that gets its
  own id; such blocks are warned about and returned with `return_truncated=True` as
  `[(label, start, length)]`. Ids are 0, 1, 2, ... in array order (non-decreasing).
  """
  y = np.asarray(y)
  ids = np.zeros(len(y), dtype=np.int64)
  truncated, nxt = [], 0
  for label, start, length in contiguous_blocks(y):
    n = _length(sub_windows_per_trial, label)
    k = np.arange(length) // n
    ids[start:start + length] = nxt + k
    nxt += int(k[-1]) + 1
    if length % n:
      truncated.append((label, start, length))
  if truncated and warn:
    warnings.warn("trial ids approximate: block(s) not a multiple of the trial length "
                  + ", ".join(f"label {lb} at {s} (length {n})" for lb, s, n in truncated), stacklevel=2)
  return (ids, truncated) if return_truncated else ids


def trial_block_report(y: np.ndarray, ids: np.ndarray,
                       sub_windows_per_trial: Union[int, dict] = 5) -> dict:
  """Block lengths per label of `y`, the number of trials and the approximate flag.

  Returns `{"blocks": {label: [lengths]}, "n_trials": int, "truncated": [(label, start, length)],
  "approximate": bool}`; `approximate` is True when a block is not a multiple of its trial length
  (a window lost to a gate inside a block, PF-03).
  """
  y = np.asarray(y)
  blocks: dict = {}
  trunc = []
  for label, start, length in contiguous_blocks(y):
    blocks.setdefault(label, []).append(length)
    if length % _length(sub_windows_per_trial, label):
      trunc.append((label, start, length))
  return {"blocks": blocks, "n_trials": int(len(np.unique(ids))), "truncated": trunc,
          "approximate": bool(trunc)}


def format_block_report(rep: dict) -> str:
  """One printable line per label: block lengths, then the approximate verdict."""
  lines = [f"  condition {lb}: blocks {rep['blocks'][lb]}" for lb in sorted(rep["blocks"])]
  lines.append(f"  trials {rep['n_trials']}; trial ids "
               + ("APPROXIMATE (block not a multiple of the trial length)" if rep["approximate"] else "exact"))
  return "\n".join(lines)


def grouped_cv(seed: int = SEED) -> StratifiedGroupKFold:
  """R1: `StratifiedGroupKFold(5, shuffle=True, random_state=seed)`; use with `groups=trial_ids`
  (LOSO: groups = subject)."""
  return StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)


def make_splits(cv: str, y: np.ndarray, trial_ids: Optional[np.ndarray], seed: int = SEED) -> list:
  """List of `(train, test)` index arrays. `cv="grouped"` needs `trial_ids` (R1); `cv="legacy"`
  is the P05-P10 window-level `StratifiedKFold(5, shuffle, seed)` (leaky, PF-01)."""
  y = np.asarray(y)
  if cv == "grouped":
    if trial_ids is None:
      raise ValueError("cv='grouped' needs trial_ids")
    return list(grouped_cv(seed).split(np.zeros((len(y), 1)), y, np.asarray(trial_ids)))
  if cv == "legacy":
    from src.models.classical.legacy_eval import legacy_cv
    return list(legacy_cv(seed).split(np.zeros((len(y), 1)), y))
  raise ValueError(f"cv must be one of {CV_CHOICES}, got {cv!r}")


def shared_trials(splits: Sequence, groups: np.ndarray) -> list:
  """`[(fold, sorted shared ids)]` of groups present in both train and test of a fold."""
  g = np.asarray(groups)
  return [(i, sorted(set(g[tr]) & set(g[te]))) for i, (tr, te) in enumerate(splits)
          if set(g[tr]) & set(g[te])]


def assert_no_shared_trials(splits: Sequence, groups: np.ndarray) -> None:
  """R1: raise AssertionError if any trial id (or subject) is on both sides of any fold."""
  bad = shared_trials(splits, groups)
  assert not bad, f"groups shared between train and test: fold {bad[0][0]} shares {bad[0][1][:5]}"


def output_dir(reports_dir: Union[str, Path], cv: str) -> Path:
  """Where a script writes its outputs: `<reports>/legacy_leaky/` for `--cv legacy`, else `<reports>/`."""
  return Path(reports_dir) / LEGACY_DIR if cv == "legacy" else Path(reports_dir)
