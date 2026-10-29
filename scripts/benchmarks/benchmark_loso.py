"""Leave-one-subject-out (LOSO) generalization (P21.1): train on every subject but one, test on the held-out one.

Data source: `<data-root>/w<len>_s<stride>/<S>/` (`scripts.build_windows --filter-mode continuous --banks fbcca fbcsp
--stride-sec ...`), read only through `src.io.subject_data.load_subject` (shared quality decision R5, fs from the
metadata, classes 101-105). Subjects: `--subjects` or every built `S<k>` found, in numeric order; two folder names with the
same number (S10, S010) are refused. The cohort and its size are printed and written into every `Data source` cell.

Channels (PF-34): the montage must be identical in every subject. `--channels common` (default) = montage channels kept by
the shared gate in EVERY subject of the cohort (`choose_channels`); `all` = the whole montage for every subject, gate drops
ignored (window validity still from the shared `valid_mask`); both refuse an empty list. `--channels PO3 POz Oz ...`
(P22.2) = exactly these montage names, in this order; subjects whose gate dropped any named channel are LEFT OUT (printed with
what the gate dropped) and the cohort is the remaining subjects (fewer than 2 is an error). All subjects and methods use the
same channels, so CSP filters and network inputs have the same shape. The `Channels` column lists them.

Grouping (R1, PF-33): the outer split is the subject. Trial ids restart at 0 in every subject, so they are offset by
`TRIAL_OFFSET * subject_index` before pooling (`pool`); nothing of the held-out subject reaches any `.fit()` (R2).

Methods (CLI names; `compact` is `compact_eegnet`, PF-31):
- `fbcca`: argmax of the FBCCA scores of the saved continuous bank; nothing is trained (calibration-free floor). With the
  same channels it equals the per-subject value of `benchmark_window_sweep` (R-16). `p_*` = scores / sum (normalized scores).
- `lda`: CSP per band (m = 1, saved `fbcsp` bank) fitted on the training subjects + FBCCA scores -> StandardScaler ->
  Shrinkage-LDA (lsqr, auto), all fitted on the training subjects (R2).
- `lda_subjnorm`: UNSUPERVISED PER-SUBJECT NORMALIZATION (test-time, R2 exception, PF-35): after the training-subject CSP,
  every subject's feature matrix (training subjects and held-out subject) is z-scored with its OWN mean/std over all its clean
  windows of the session, no labels (offline upper bound; the statistics come from the whole session); then the pooled scaler
  and Shrinkage-LDA as for `lda`.
- `within_lda` (P22.1): the within-subject reference on EXACTLY the LOSO channels: per held-out subject, `--folds 5`
  StratifiedGroupKFold(shuffle, random_state = 42 + r) over the subject's true trial ids, r = 0..`--within-repeats`-1 (R1);
  the same features and pipeline as `lda` (CSP m = 1 fitted on the training trials of the fold, + FBCCA, scaler, Shrinkage-LDA).
  Acc = mean over repeats, Acc SD = SD over repeats (ddof 1), Runs = repeats; predictions/confusion use repeat 0.
- `ccnn`, `compact_eegnet`, `eegnet`: `src.models.cnn.training.fit_network` on the pooled training subjects' filtered
  windows (P20 hyperparameters); early-stopping validation = first split of the inner grouped 5-fold over the offset training
  trial ids (PF-32), so it never contains the held-out subject; normalization statistics from the fitting windows only.

Resumable (PF-37): every (method, test subject) fold is written atomically to `<out-dir>/folds/<method>__test-<S>.npz` with its
`config` JSON (cohort, training subjects, channels, window, stride, fs, hyperparameters, seed, git HEAD recorded once at process
start, dirty flag of src/scripts/configs) and skipped on rerun (`[skip] <method> test-<S>`). `check_fold` REFUSES a saved fold
whose configuration differs in any key except `data_root` ("use a new --out-dir"); a different git HEAD is refused only when
`git diff --stat <h1> <h2> -- src scripts configs` is non-empty or a head cannot be resolved; differing dirty flags are refused at
any head, a dirty side with differing heads is refused, and dirty is accepted only when both sides are dirty at the same head. There is
no override flag. The summary is always rebuilt from the fold files; a method with fewer fold files than the cohort is flagged
(`Folds` column, `[warn]`) and gets no cohort Mean unless `--partial-mean`.

Outputs (`--out-dir`): `summary.csv` (Subject, Window (s), Method, Windows, Trials, Acc (%), Acc SD, BalAcc (%), ITR
(bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch, 2-tap Smoothed (%), Channels, Data source; cohort rows Mean and SD
per method, SD with ddof = 1), `per_subject.csv` (Subject x Method pivots of Acc and 2-tap), `predictions.csv`, `confusion.csv`
(pooled over the held-out subjects), `folds.csv` (per fold: train/val accuracy, best epoch, seconds, `degenerate`) and
`loso_config.json`. 2-tap smoothing averages a window with the previous window of the SAME trial (sorted by trial, offset;
R8). ITR = Wolpaw, N = 5, T = window + 0.5 s. `Runs` = 1 (one fit per held-out subject, seed 42; `within_lda`: repeats).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else three levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from scripts.benchmarks.benchmark_window_sweep import (  # noqa: E402
  GAZE_SEC, SEED, balanced_accuracy, fbcca_features, folder_name, itr_bits_per_min)
from src.features.ssvep.fbcsp_extraction import FBCSPTransformer  # noqa: E402
from src.io.subject_data import CLASS_CODES, discover_subjects, is_built, load_subject  # noqa: E402
from src.models.classical.benchmark_runner import load_config  # noqa: E402
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials  # noqa: E402
from src.preprocessing.dataset.smoothing import smooth_probabilities_by_trial  # noqa: E402
from src.preprocessing.window_quality import quality_params_from_config  # noqa: E402

TRIAL_OFFSET = 10_000        # subject k's trial ids become id + TRIAL_OFFSET * k (PF-33)
CLASSICAL = ("fbcca", "lda", "lda_subjnorm", "within_lda")
NETWORK_METHODS = {"ccnn": "ccnn", "compact": "compact_eegnet", "compact_eegnet": "compact_eegnet", "eegnet": "eegnet"}
METHOD_ORDER = ["fbcca", "lda", "lda_subjnorm", "within_lda", "ccnn", "compact_eegnet", "eegnet"]
CLI_METHODS = ["fbcca", "lda", "lda_subjnorm", "within_lda", "ccnn", "compact", "eegnet"]
METHOD_LABELS = {"lda_subjnorm": "lda_subjnorm (unsupervised per-subject normalization)"}
SUBJNORM_NOTE = ("unsupervised per-subject normalization: each subject's features z-scored with its own unlabeled "
                 "whole-session mean/std (test-time, offline upper bound; R2 exception, PF-35)")
SUMMARY_COLUMNS = ["Subject", "Window (s)", "Method", "Windows", "Trials", "Acc (%)", "Acc SD", "BalAcc (%)",
                   "ITR (bits/min)", "Train Acc (%)", "Runs", "Val Acc (%)", "Best Epoch", "2-tap Smoothed (%)",
                   "Folds", "Channels", "Data source"]
NUMERIC = ["Windows", "Trials", "Acc (%)", "Acc SD", "BalAcc (%)", "ITR (bits/min)", "Train Acc (%)", "Runs",
           "Val Acc (%)", "Best Epoch", "2-tap Smoothed (%)"]
DEGENERATE_BEST_EPOCH = 5    # P20 C-2: restored best epoch <= 5 or train acc < chance + 10 pp
DEGENERATE_MARGIN = 0.10
CHUNK = 2048                 # rows per CSP transform call (memory)
IGNORED_CONFIG_KEYS = ("git_head", "git_dirty", "data_root")   # paths never matter; the code revision has its own rule (`fold_problem`)
WITHIN_FOLDS, WITHIN_REPEATS = 5, 5
CODE_PATHS = ("src", "scripts", "configs")      # a head change is harmless only if nothing here differs between the two heads
DIRTY_PATHS = ("src", "scripts", "configs")


def label_of(method: str) -> str:
  return METHOD_LABELS.get(method, method)


def git_head() -> str:
  try:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip() or "unknown"
  except Exception:
    return "unknown"


def git_dirty() -> bool:
  """True when tracked or untracked (non-ignored) files under src/scripts/configs differ from HEAD; True when git fails."""
  try:
    r = subprocess.run(["git", "status", "--porcelain", "--", *DIRTY_PATHS], cwd=ROOT, capture_output=True, text=True, timeout=30)
    return r.returncode != 0 or bool(r.stdout.strip())
  except Exception:
    return True


RUN_STATE: dict = {}      # {"git_head", "git_dirty"}: captured ONCE per process by `capture_run_state` (P21 C-1), not per fold


def capture_run_state() -> dict:
  RUN_STATE.clear()
  RUN_STATE.update({"git_head": git_head(), "git_dirty": git_dirty()})
  return RUN_STATE


def code_changed(h1: str, h2: str, repo: Path = ROOT) -> bool:
  """True when `src/` or `scripts/` differ between heads `h1` and `h2` (`git diff --stat`), or when git cannot say (an
  unresolvable head counts as changed: the refusal is the safe answer)."""
  if "unknown" in (h1, h2) or not h1 or not h2:
    return True
  try:
    r = subprocess.run(["git", "diff", "--stat", h1, h2, "--", *CODE_PATHS], cwd=repo, capture_output=True, text=True, timeout=60)
  except Exception:
    return True
  return r.returncode != 0 or bool(r.stdout.strip())


# --- subjects and channels -----------------------------------------------------------------------------------------

def check_subject_names(names: Sequence[str]) -> list:
  """Subject names in numeric order; ValueError for a duplicate name or two names with the same number (S10 / S010)."""
  names = list(names)
  if len(set(names)) != len(names):
    raise ValueError(f"duplicate subject names in {names}")
  nums = [int(n[1:]) for n in names]
  if len(set(nums)) != len(nums):
    raise ValueError(f"two subject folders share a number (numeric sorting would collide): {names}")
  return [n for _, n in sorted(zip(nums, names))]


def parse_channels(values: Sequence[str]) -> tuple:
  """`--channels` values -> `(mode, names)`: `common` / `all` (alone) or `names` with the explicit list (order kept)."""
  vals = [str(v) for v in values]
  if not vals:
    raise ValueError("--channels needs 'common', 'all' or a list of montage channel names")
  if len(vals) == 1 and vals[0] in ("common", "all"):
    return vals[0], []
  if any(v in ("common", "all") for v in vals):
    raise ValueError(f"'common'/'all' cannot be mixed with channel names: {vals}")
  if len(set(vals)) != len(vals):
    raise ValueError(f"duplicate channel names in {vals}")
  return "names", vals


def leave_out_for_names(montages: dict, kept: dict, names: Sequence[str]) -> tuple:
  """PF-34 / P22.2: `(remaining subjects, {left-out subject: [named channels its gate dropped]})`. ValueError if a name is not in
  the (common) montage or the montages differ. A subject stays only if its gate kept EVERY named channel."""
  subs = list(montages)
  ref = list(montages[subs[0]])
  for s in subs:
    if list(montages[s]) != ref:
      raise ValueError(f"montage of {s} {list(montages[s])} differs from {subs[0]} {ref}")
  unknown = [c for c in names if c not in ref]
  if unknown:
    raise ValueError(f"channels {unknown} are not in the montage {ref}")
  out = {s: [c for c in names if c not in kept[s]] for s in subs}
  return [s for s in subs if not out[s]], {s: d for s, d in out.items() if d}


def choose_channels(montages: dict, kept: dict, mode: str = "common", names: Sequence[str] = ()) -> list:
  """The one channel list of the cohort (PF-34). `montages[s]` = montage of subject s, `kept[s]` = channels the shared gate
  kept. `common`: montage channels kept in every subject (montage order); `all`: the whole montage; `names`: `names` as given
  (validated against the montage; the caller leaves out subjects whose gate dropped one, `leave_out_for_names`). ValueError if
  the montages differ between subjects, the mode is unknown or the result is empty."""
  if mode not in ("common", "all", "names"):
    raise ValueError(f"channels must be 'common', 'all' or 'names', got {mode!r}")
  subs = list(montages)
  ref = list(montages[subs[0]])
  for s in subs:
    if list(montages[s]) != ref:
      raise ValueError(f"montage of {s} {list(montages[s])} differs from {subs[0]} {ref}")
  if mode == "names":
    leave_out_for_names(montages, kept, names)
    return [str(c) for c in names]
  chosen = ref if mode == "all" else [c for c in ref if all(c in kept[s] for s in subs)]
  if not chosen:
    raise ValueError("no channel is kept by the gate in every subject; use --channels all")
  return chosen


# --- pooling (R1, PF-33) -------------------------------------------------------------------------------------------

def pool(subs: list, banks: Sequence[str] = (), consume: bool = False) -> dict:
  """Concatenate the loaded subjects (`load_subject` dicts, one fs, same channels) with offset trial ids.

  Returns `y` (class codes), `yi` (indices 0..K-1 in sorted code order), `classes`, `subj` (subject index per row),
  `trial` (offset trial ids: unique per (subject, trial)), `groups` (offset `cv_groups`), `offsets` (samples), `X`,
  `fb` (FBCCA scores) and `bands[bank]`, whichever the subjects carry. `consume=True` drops each subject's `X` and bands
  as soon as they are copied into the pooled arrays (peak memory of a 40-subject cohort ~ one copy, not two)."""
  ch = [tuple(d["channel_names"]) for d in subs]
  if len(set(ch)) != 1:
    raise ValueError(f"subjects have different channels: {sorted(set(ch))}")
  if len({float(d["fs"]) for d in subs}) != 1:
    raise ValueError("subjects have different sampling rates")
  for d in subs:
    if len(d["trial_ids"]) and int(np.max(d["trial_ids"])) >= TRIAL_OFFSET:
      raise ValueError(f"{d['subject']}: trial ids reach {TRIAL_OFFSET}; raise TRIAL_OFFSET")
  cat = lambda f: np.concatenate([f(d) for d in subs]) if subs else np.zeros(0)
  y = cat(lambda d: np.asarray(d["y"]))
  classes = np.unique(y)
  out = {"y": y, "classes": classes, "yi": np.searchsorted(classes, y),
         "subj": cat(lambda d: np.full(len(d["y"]), subs.index(d))),
         "trial": cat(lambda d: np.asarray(d["trial_ids"]) + TRIAL_OFFSET * subs.index(d)),
         "groups": cat(lambda d: np.asarray(d["cv_groups"]) + TRIAL_OFFSET * subs.index(d)),
         "offsets": cat(lambda d: np.asarray(d["offsets"])), "fs": float(subs[0]["fs"]),
         "starts": (cat(lambda d: np.asarray(d["window_starts"])) if all(d.get("window_starts") is not None for d in subs)
                    else None),
         "channels": list(subs[0]["channel_names"]), "subjects": [d["subject"] for d in subs]}
  if all("fb" in d for d in subs):
    out["fb"] = np.concatenate([d["fb"] for d in subs])
  getters = {"X": lambda d: d.get("X"), **{("bands", b): (lambda d, b=b: d["bands"].get(b)) for b in banks}}
  out["bands"] = {}
  for key, get in getters.items():
    first = [get(d) for d in subs[:1]]
    if first[0] is None or any(get(d) is None for d in subs):
      continue
    n = sum(len(get(d)) for d in subs)
    arr = np.empty((n,) + get(subs[0]).shape[1:], dtype=get(subs[0]).dtype)
    i = 0
    for d in subs:
      v = get(d)
      arr[i:i + len(v)] = v
      i += len(v)
      if consume:
        d.pop("X", None) if key == "X" else d["bands"].pop(key[1], None)
      del v
    if key == "X":
      out["X"] = arr
    else:
      out["bands"][key[1]] = arr
  return out


def loso_split(subj: np.ndarray, test: int) -> tuple:
  """`(train_idx, test_idx)` of the LOSO fold whose held-out subject index is `test`; asserts R1 (no shared subject)."""
  tr, te = np.flatnonzero(subj != test), np.flatnonzero(subj == test)
  assert_no_shared_trials([(tr, te)], subj)
  return tr, te


# --- classical methods ---------------------------------------------------------------------------------------------

def subject_zscore(F: np.ndarray, subj: np.ndarray) -> np.ndarray:
  """Z-score every subject's rows of `F` with that subject's own mean/std over all its rows. No labels (PF-35)."""
  out = np.asarray(F, dtype=np.float64).copy()
  for s in np.unique(subj):
    m = subj == s
    mu, sd = out[m].mean(axis=0), out[m].std(axis=0)
    out[m] = (out[m] - mu) / np.where(sd < 1e-12, 1.0, sd)
  return out


def lda_features(csp_bands: np.ndarray, fb: np.ndarray, yi: np.ndarray, tr: np.ndarray) -> tuple:
  """`(csp, F)`: CSP (m = 1 per band) fitted on the rows `tr` only (R2), `F` = [CSP log-variances, FBCCA scores] of EVERY row."""
  csp = FBCSPTransformer(1).fit(csp_bands[tr], yi[tr])
  csp_feats = np.vstack([csp.transform(csp_bands[i:i + CHUNK]) for i in range(0, len(csp_bands), CHUNK)])   # no copy of the bands
  return csp, np.hstack([csp_feats, fb])


def lda_pipeline(seed: int = SEED) -> Pipeline:
  """StandardScaler + Shrinkage-LDA (lsqr, auto): the classifier of `lda`, `lda_subjnorm`, `within_lda` and the warm-up study."""
  return Pipeline([("scaler", StandardScaler()), ("lda", get_sklearn_model_suite(seed)["Shrinkage-LDA lsqr"])])


def lda_loso_fold(csp_bands: np.ndarray, fb: np.ndarray, yi: np.ndarray, subj: np.ndarray, tr: np.ndarray,
                  te: np.ndarray, subjnorm: bool = False, seed: int = SEED) -> dict:
  """`lda` / `lda_subjnorm` fold on pooled arrays. CSP (m = 1) is fitted on `csp_bands[tr]` only, features = CSP + FBCCA,
  optionally z-scored per subject without labels (`subjnorm`), then StandardScaler + Shrinkage-LDA (lsqr, auto) on the
  training rows. Returns `proba` (n_te, K), `train_acc` and the fitted `csp`, `pipeline`."""
  csp, Fall = lda_features(csp_bands, fb, yi, tr)
  rows = np.concatenate([tr, te])
  F = Fall[rows]
  if subjnorm:
    F = subject_zscore(F, subj[rows])
  ftr, fte = F[:len(tr)], F[len(tr):]
  pipe = lda_pipeline(seed)
  pipe.fit(ftr, yi[tr])
  return {"proba": pipe.predict_proba(fte), "train_acc": float(np.mean(pipe.predict(ftr) == yi[tr])),
          "csp": csp, "pipeline": pipe}


def within_splits(yi: np.ndarray, groups: np.ndarray, folds: int, seed: int) -> list:
  """R1 splitter of `within_lda`: `StratifiedGroupKFold(folds, shuffle, random_state = seed)` over the subject's true trial ids;
  asserts that no trial id is on both sides of any fold."""
  from sklearn.model_selection import StratifiedGroupKFold
  splits = list(StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed).split(np.zeros(len(yi)), yi, groups))
  assert_no_shared_trials(splits, groups)
  return splits


def within_lda_fold(csp_bands: np.ndarray, fb: np.ndarray, yi: np.ndarray, groups: np.ndarray, folds: int = WITHIN_FOLDS,
                    repeats: int = WITHIN_REPEATS, seed: int = SEED, n_classes: int = 0) -> dict:
  """P22.1 `within_lda` for ONE subject: arrays hold only that subject's rows, `groups` = its true trial ids (R1).
  Repeat r = StratifiedGroupKFold(folds, shuffle, random_state = seed + r), every fold fits the `lda` pipeline on its training
  trials only (`lda_loso_fold`, same features). Returns `proba` (repeats, n, K) out of fold (each row predicted by the fold
  that did not train on its trial), `acc` per repeat, `train_acc` (mean over folds and repeats) and `n_train`."""
  K = n_classes or int(yi.max()) + 1
  proba = np.zeros((repeats, len(yi), K))
  tra, ntr = [], []
  subj0 = np.zeros(len(yi), dtype=int)
  for r in range(repeats):
    splits = within_splits(yi, groups, folds, seed + r)
    for tr, te in splits:
      f = lda_loso_fold(csp_bands, fb, yi, subj0, tr, te, False, seed)
      proba[r, te] = f["proba"]
      tra.append(f["train_acc"])
      ntr.append(len(tr))
  return {"proba": proba, "acc": [float(np.mean(p.argmax(1) == yi)) for p in proba], "train_acc": float(np.mean(tra)),
          "n_train": float(np.mean(ntr))}


def fbcca_fold(fb: np.ndarray, te: np.ndarray) -> dict:
  """Calibration-free: normalized FBCCA scores of the held-out rows (argmax = the FBCCA decision)."""
  s = np.asarray(fb[te], dtype=np.float64)
  tot = s.sum(axis=1, keepdims=True)
  return {"proba": np.where(tot > 0, s / np.where(tot > 0, tot, 1.0), 1.0 / s.shape[1])}


# --- network methods (hook; P21.2 fills the details) ---------------------------------------------------------------

def network_fold(P: dict, tr: np.ndarray, te: np.ndarray, method: str, args, dev: str) -> dict:
  """One LOSO network fold: `fit_network` on the pooled training subjects (groups = offset trial ids, so the inner
  validation split never contains the held-out subject, PF-32), normalization statistics from the fitting windows only.
  Returns `proba`, `train_acc`, `val_acc`, `best_epoch`, `epochs_run`, `model`."""
  import torch
  from src.models.cnn.training import fit_network, model_factory, normalise, predict_proba
  groups = P["groups"][tr]
  assert not set(groups) & set(P["groups"][te]), "held-out trial ids reach the training groups"
  r = fit_network(P["X"][tr], P["yi"][tr], groups, model_factory(method, P["fs"]), seed=args.seed, device=dev,
                  augment=not args.no_augment, max_epochs=args.max_epochs, patience=args.patience)
  assert not set(P["subj"][tr][r["val_idx"]]) & set(P["subj"][te]), "validation windows of the held-out subject"
  p = predict_proba(r["model"], normalise(P["X"][te], r["mean"], r["std"]), torch.device(dev))
  return {"proba": p, "train_acc": r["train_acc"], "val_acc": r["val_acc"], "best_epoch": r["best_epoch"],
          "epochs_run": r["epochs_run"], "model": r["model"], "mean": r["mean"], "std": r["std"]}


def pick_device(requested: str = "auto") -> str:
  """`cuda` when available, else `cpu`; an explicit `cuda` without a GPU falls back to CPU with a warning."""
  import torch
  has = torch.cuda.is_available()
  if requested == "cuda" and not has:
    print("[warn] --device cuda requested but CUDA is not available; falling back to cpu", flush=True)
  return "cuda" if requested in ("auto", "cuda") and has else "cpu"


def is_degenerate(best_epoch: float, train_acc: float, n_classes: int) -> bool:
  """P20 C-2: restored best epoch <= 5 or training accuracy below chance + 10 pp (networks only)."""
  if best_epoch is None or np.isnan(best_epoch):
    return False
  return bool(best_epoch <= DEGENERATE_BEST_EPOCH or train_acc < 1.0 / n_classes + DEGENERATE_MARGIN)


# --- fold store (PF-37) --------------------------------------------------------------------------------------------

def fold_path(out: Path, method: str, subject: str) -> Path:
  return Path(out) / "folds" / f"{method}__test-{subject}.npz"


def comparable(config: dict) -> dict:
  return {k: v for k, v in config.items() if k not in IGNORED_CONFIG_KEYS}


def fold_problem(saved: dict, mine: dict, repo: Path = ROOT) -> Optional[str]:
  """Why a saved fold must not be reused with the current configuration, or None (PF-37, P21 C-1).

  Any difference of a configuration key except `data_root` is a problem. A different `git_head` is a problem only when `src/` or
  `scripts/` or `configs/` differ between the heads (`code_changed`; an unresolvable head counts as a difference). Dirty flags
  (uncommitted code changes): differing flags are a problem at any head; a dirty side with differing heads is a problem; dirty
  is accepted only when both sides are dirty at the same head."""
  diff = config_diff(saved, mine)
  if diff:
    return f"configuration differs {diff} (saved, now)"
  h1, h2 = saved.get("git_head", "unknown"), mine.get("git_head", "unknown")
  d1, d2 = saved.get("git_dirty"), mine.get("git_dirty")
  if d1 != d2:
    return f"working tree state differs (dirty {d1} -> {d2}, heads {h1[:10]} -> {h2[:10]})"
  if h1 != h2:
    if d1 or d2:
      return f"git head {h1[:10]} -> {h2[:10]} with uncommitted code changes (dirty {d1} -> {d2})"
    if code_changed(h1, h2, repo):
      return f"git head {h1[:10]} -> {h2[:10]} changes src/, scripts/ or configs/ (or a head cannot be resolved)"
  return None


def check_fold(path: Path, saved: dict, mine: dict, repo: Path = ROOT) -> None:
  """Refuse (SystemExit) to reuse a fold made with another configuration or code; there is no override (P22.3)."""
  why = fold_problem(saved, mine, repo)
  if why:
    raise SystemExit(f"[x] {path} was made with a different configuration: {why}; use a new --out-dir")


def config_diff(saved: dict, mine: dict) -> dict:
  a, b = comparable(saved), comparable(mine)
  return {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


def save_fold(path: Path, arrays: dict, config: dict) -> None:
  """Atomic write: temporary file in the same folder, then rename; an interrupt never leaves a half fold."""
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(path.name + ".tmp")
  try:
    with open(tmp, "wb") as f:
      np.savez(f, config=np.array(json.dumps(config, sort_keys=True)), **arrays)
    os.replace(tmp, path)
  finally:
    if tmp.exists():
      tmp.unlink()


def load_fold(path: Path) -> tuple:
  z = np.load(path, allow_pickle=False)
  return {k: z[k] for k in z.files if k != "config"}, json.loads(str(z["config"]))


def method_hyper(method: str, args) -> dict:
  if method == "fbcca":
    return {"decision": "argmax of FBCCA scores (continuous bank), 3 harmonics"}
  if method in ("lda", "lda_subjnorm", "within_lda"):
    h = {"features": "FBCSP (m=1, in-fold on training subjects) + FBCCA", "scaler": "StandardScaler",
         "classifier": "Shrinkage-LDA lsqr auto"}
    if method == "lda_subjnorm":
      h["subject_norm"] = SUBJNORM_NOTE
    if method == "within_lda":
      h.update({"protocol": "within-subject StratifiedGroupKFold over true trial ids, random_state = seed + repeat",
                "folds": args.folds, "within_repeats": args.within_repeats})
    return h
  from src.models.cnn import training as T
  return {"model": method, "lr": T.LR, "batch_size": T.BATCH_SIZE, "weight_decay": T.WEIGHT_DECAY,
          "label_smoothing": T.LABEL_SMOOTHING, "val_frac": T.VAL_FRAC, "max_epochs": args.max_epochs,
          "patience": args.patience, "augment": not args.no_augment}


def fold_config(method: str, test: str, ctx: dict, args) -> dict:
  state = RUN_STATE or capture_run_state()
  return {"method": method, "test_subject": test,
          "train_subjects": [test] if method == "within_lda" else [s for s in ctx["subjects"] if s != test],
          "cohort": ctx["subjects"], "channels_mode": args.channels, "channels": ctx["channels"],
          "window_sec": args.window, "stride_sec": args.stride_sec, "fs": ctx["fs"], "classes": ctx["classes"],
          "quality": "shared", "seed": args.seed, "trial_offset": TRIAL_OFFSET, "hyper": method_hyper(method, args),
          "n_windows_test": ctx["n_windows"][test], "git_head": state["git_head"], "git_dirty": state["git_dirty"],
          "data_root": str(ctx["root"])}


def run_fold(method: str, P: dict, k: int, args, dev: str) -> tuple:
  """Compute one fold. Returns `(arrays to store, fitted objects for --save-models)`."""
  t0 = time.time()
  extra = {}
  if method == "within_lda":
    rows = np.flatnonzero(P["subj"] == k)
    r = within_lda_fold(P["bands"]["fbcsp"][rows], P["fb"][rows], P["yi"][rows], P["trial"][rows], args.folds,
                        args.within_repeats, args.seed, len(P["classes"]))
    arrays = {"proba": r["proba"][0], "proba_rep": r["proba"], "y": P["y"][rows], "trial_id": P["trial"][rows] - TRIAL_OFFSET * k,
              "offset": P["offsets"][rows], "train_acc": r["train_acc"], "val_acc": np.nan, "best_epoch": np.nan,
              "epochs_run": np.nan, "n_train": r["n_train"], "seconds": time.time() - t0}
    return {k_: np.asarray(v) for k_, v in arrays.items()}, {}
  tr, te = loso_split(P["subj"], k)
  if method == "fbcca":
    r = fbcca_fold(P["fb"], te)
  elif method in ("lda", "lda_subjnorm"):
    r = lda_loso_fold(P["bands"]["fbcsp"], P["fb"], P["yi"], P["subj"], tr, te, method == "lda_subjnorm", args.seed)
    extra = {"csp": r["csp"], "pipeline": r["pipeline"]}
  else:
    r = network_fold(P, tr, te, method, args, dev)
    extra = {"model": r["model"], "mean": r["mean"], "std": r["std"]}
  nan = float("nan")
  arrays = {"proba": np.asarray(r["proba"], dtype=np.float64), "y": P["y"][te], "trial_id": P["trial"][te] - TRIAL_OFFSET * k,
            "offset": P["offsets"][te], "train_acc": r.get("train_acc", nan), "val_acc": r.get("val_acc", nan),
            "best_epoch": r.get("best_epoch", nan), "epochs_run": r.get("epochs_run", nan),
            "n_train": len(tr), "seconds": time.time() - t0}
  return {k_: np.asarray(v) for k_, v in arrays.items()}, extra


def save_models(path_dir: Path, method: str, subject: str, extra: dict, ctx: dict) -> None:
  """`--save-models`: classical objects with joblib, networks as a torch state dict + normalization."""
  path_dir.mkdir(parents=True, exist_ok=True)
  stem = path_dir / f"{method}__test-{subject}"
  if "model" in extra:
    import torch
    torch.save({"state_dict": {k: v.cpu() for k, v in extra["model"].state_dict().items()}, "mean": extra["mean"], "std": extra["std"],
                "channels": ctx["channels"], "fs": ctx["fs"]}, str(stem) + ".pt")
  elif extra:
    import joblib
    joblib.dump({**extra, "channels": ctx["channels"], "classes": ctx["classes"]}, str(stem) + ".joblib")


# --- summary -------------------------------------------------------------------------------------------------------

def smooth_two_tap(proba: np.ndarray, trial_id: np.ndarray, offset: np.ndarray) -> np.ndarray:
  """2-tap causal smoothing within trial (R8): rows sorted by (trial, offset), a window is averaged with the previous
  window of the SAME trial; returned in the original row order."""
  order = np.lexsort((offset, trial_id))
  sm = smooth_probabilities_by_trial(proba[order], trial_id[order])
  out = np.empty_like(sm)
  out[order] = sm
  return out


def fold_rows(method: str, subject: str, arrays: dict, config: dict, classes: np.ndarray, source: str) -> tuple:
  """Summary row, prediction frame and confusion matrix of one stored fold."""
  proba, y = arrays["proba"], arrays["y"]
  yi = np.searchsorted(classes, y)
  pred = proba.argmax(1)
  sm_pred = smooth_two_tap(proba, arrays["trial_id"], arrays["offset"]).argmax(1)
  reps = arrays["proba_rep"] if "proba_rep" in arrays else proba[None]        # within_lda: every repeat is a run (P22.1)
  r_pred = [p_.argmax(1) for p_ in reps]
  r_sm = [smooth_two_tap(p_, arrays["trial_id"], arrays["offset"]).argmax(1) for p_ in reps]
  accs = [float(np.mean(p_ == yi)) for p_ in r_pred]
  acc = float(np.mean(accs))
  K = len(classes)
  fin = lambda key: float(arrays[key]) if key in arrays and not np.isnan(arrays[key]) else np.nan
  pct = lambda v: round(100 * v, 2) if not np.isnan(v) else np.nan
  row = {"Subject": subject, "Window (s)": config["window_sec"], "Method": label_of(method), "Windows": len(y),
         "Trials": int(len(np.unique(arrays["trial_id"]))), "Acc (%)": pct(acc),
         "Acc SD": round(100 * float(np.std(accs, ddof=1)), 2) if len(accs) > 1 else 0.0,
         "BalAcc (%)": pct(float(np.mean([balanced_accuracy(yi, p_) for p_ in r_pred]))),
         "ITR (bits/min)": round(itr_bits_per_min(acc, K, config["window_sec"] + GAZE_SEC), 2),
         "Train Acc (%)": pct(fin("train_acc")), "Runs": len(reps), "Val Acc (%)": pct(fin("val_acc")),
         "Best Epoch": fin("best_epoch"), "2-tap Smoothed (%)": pct(float(np.mean([np.mean(q == yi) for q in r_sm]))), "Folds": 1,
         "Channels": ", ".join(config["channels"]) + (" (all, gate channel drops ignored)" if config["channels_mode"] == "all" else ""),
         "Data source": source}
  pr = pd.DataFrame({"subject": subject, "window_sec": config["window_sec"], "method": label_of(method),
                     "trial_id": arrays["trial_id"], "offset_sec": arrays["offset"] / float(config["fs"]),
                     "true": y, "pred": classes[pred], "pred_2tap": classes[sm_pred]})
  for j, c in enumerate(classes):
    pr[f"p_{c}"] = proba[:, j]
  cm = np.zeros((K, K), dtype=int)
  np.add.at(cm, (yi, pred), 1)
  return row, pr, cm


def cohort_rows(summary: pd.DataFrame, cohort_size: Optional[int] = None, partial_mean: bool = False) -> pd.DataFrame:
  """Mean and SD (ddof = 1) over the held-out subjects, per method. A method with fewer folds than `cohort_size` (P21 C-2) gets
  EMPTY Mean/SD (numbers NaN, `Data source` says INCOMPLETE) unless `partial_mean`; `Folds` = folds present."""
  rows = []
  for m, g in summary.groupby("Method", sort=False):
    incomplete = cohort_size is not None and len(g) < cohort_size
    for name, f in (("Mean", lambda a: a.mean()), ("SD", lambda a: a.std(ddof=1) if len(a) > 1 else 0.0)):
      r = {c: f(g[c].astype(float)) if g[c].notna().any() and not (incomplete and not partial_mean) else np.nan for c in NUMERIC}
      src = f"{g['Data source'].iloc[0].split(' | ')[0]} | {len(g)} held-out subjects"
      if incomplete:
        src += f" | INCOMPLETE: {len(g)} of {cohort_size} folds" + (" (cohort mean refused)" if not partial_mean else " (--partial-mean)")
      r.update({"Subject": name, "Window (s)": g["Window (s)"].iloc[0], "Method": m, "Channels": g["Channels"].iloc[0],
                "Folds": len(g), "Data source": src})
      for c in NUMERIC[2:]:
        r[c] = round(r[c], 2) if not pd.isna(r[c]) else np.nan
      rows.append(r)
  return pd.DataFrame(rows)


def build_summary(out: Path, subjects: list, classes: np.ndarray, methods: Sequence[str], config_of: dict, source: str,
                  partial_mean: bool = False) -> dict:
  """Rebuild every output from the fold files of `out/folds` that belong to this cohort and these channels.

  Folds of requested methods must pass `check_fold` (else SystemExit, PF-37); stored folds of other methods that do not are
  left out with a warning. A method with fewer folds than subjects is flagged and gets no cohort Mean (P21 C-2)."""
  rows, preds, cms, fold_info = [], [], {}, []
  for m in METHOD_ORDER:
    for s in subjects:
      p = fold_path(out, m, s)
      if not p.is_file():
        continue
      arrays, saved = load_fold(p)
      if m in methods:
        check_fold(p, saved, config_of(m, s))
      else:
        why = fold_problem(saved, config_of(m, s))
        if why:
          print(f"[warn] {p.name}: {why}; left out")
          continue
      row, pr, cm = fold_rows(m, s, arrays, saved, classes, source)
      rows.append(row)
      preds.append(pr)
      cms[label_of(m)] = cms.get(label_of(m), 0) + cm
      bep = float(arrays["best_epoch"]) if "best_epoch" in arrays else np.nan
      fold_info.append({"Method": label_of(m), "Test subject": s, "Train subjects": len(saved["train_subjects"]),
                        "Train windows": int(arrays["n_train"]), "Train Acc (%)": row["Train Acc (%)"],
                        "Val Acc (%)": row["Val Acc (%)"], "Best Epoch": bep, "Epochs Run": float(arrays["epochs_run"]),
                        "Seconds": round(float(arrays["seconds"]), 2),
                        "degenerate": is_degenerate(bep, float(arrays["train_acc"]), len(classes)) if m in NETWORK_METHODS.values() else False})
  if not rows:
    return {}
  per = pd.DataFrame(rows)
  short = {m_: int((per["Method"] == m_).sum()) for m_ in per["Method"].unique() if int((per["Method"] == m_).sum()) < len(subjects)}
  for m_, n_ in short.items():
    print(f"[warn] {m_}: {n_} fold files for a cohort of {len(subjects)}; " +
          ("cohort Mean/SD kept (--partial-mean)" if partial_mean else "no cohort Mean/SD written"), flush=True)
  summary = pd.concat([per, cohort_rows(per, len(subjects), partial_mean)], ignore_index=True)[SUMMARY_COLUMNS]
  order = {label_of(m): i for i, m in enumerate(METHOD_ORDER)}
  summary["_m"] = summary["Method"].map(order)
  summary["_s"] = summary["Subject"].map(lambda s: (1, 0) if s == "Mean" else (2, 0) if s == "SD" else (0, int(s[1:])))
  summary = summary.sort_values(["_m", "_s"], kind="mergesort").drop(columns=["_m", "_s"]).reset_index(drop=True)
  subs_only = summary[~summary["Subject"].isin(["Mean", "SD"])]
  piv = lambda col: subs_only.pivot(index="Subject", columns="Method", values=col)
  cols = [label_of(m) for m in METHOD_ORDER if label_of(m) in set(subs_only["Method"])]
  a, b = piv("Acc (%)")[cols], piv("2-tap Smoothed (%)")[cols]
  per_subject = pd.concat({"Acc (%)": a, "2-tap Smoothed (%)": b}, axis=1)
  per_subject = per_subject.loc[sorted(per_subject.index, key=lambda s: int(s[1:]))]
  per_subject.loc["Mean"] = per_subject.mean()
  per_subject.loc["SD"] = per_subject.iloc[:-1].std(ddof=1) if len(per_subject) > 2 else 0.0
  if not partial_mean:
    for m_ in short:
      per_subject.loc[["Mean", "SD"], [(c, m_) for c in ("Acc (%)", "2-tap Smoothed (%)")]] = np.nan
  predictions = pd.concat(preds, ignore_index=True)
  conf = pd.DataFrame([{"method": m, "true": int(classes[i]), "pred": int(classes[j]), "count": int(cm[i, j])}
                       for m, cm in cms.items() for i in range(len(classes)) for j in range(len(classes))])
  return {"summary": summary, "per_subject": per_subject.round(2), "predictions": predictions, "confusion": conf,
          "folds": pd.DataFrame(fold_info)}


# --- driver --------------------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--data-root", type=Path, default=Path("data/processed_continuous"))
  p.add_argument("--window", type=float, default=1.0, help="window length of the built folders in s (default 1)")
  p.add_argument("--stride-sec", type=float, default=0.25, help="stride of the built folders (default 0.25)")
  p.add_argument("--subjects", nargs="*", default=None, help="default: every built S<k> found, numeric order")
  p.add_argument("--methods", nargs="+", default=["fbcca", "lda", "lda_subjnorm"], choices=CLI_METHODS,
                 help="`compact` = compact_eegnet (PF-31)")
  p.add_argument("--channels", nargs="+", default=["common"], metavar="common|all|NAME",
                 help="common: kept by the gate in every subject (default); all: whole montage; or explicit montage names "
                      "(subjects whose gate dropped any of them are left out) (PF-34)")
  p.add_argument("--folds", type=int, default=WITHIN_FOLDS, help="within_lda: StratifiedGroupKFold splits (default 5)")
  p.add_argument("--within-repeats", type=int, default=WITHIN_REPEATS,
                 help="within_lda: repeats with random_state = seed + r (default 5)")
  p.add_argument("--partial-mean", action="store_true",
                 help="write the cohort Mean/SD of a method that has fewer folds than the cohort (default: leave it empty, P21 C-2)")
  p.add_argument("--out-dir", type=Path, default=Path("reports/loso_w1"))
  p.add_argument("--save-models", action="store_true", help="save every fitted fold model under --models-dir")
  p.add_argument("--models-dir", type=Path, default=Path("outputs/models/loso_w1"))
  p.add_argument("--no-augment", action="store_true", help="networks: P10 augmentation off (default on)")
  p.add_argument("--max-epochs", type=int, default=150)
  p.add_argument("--patience", type=int, default=25)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto", help="networks only")
  p.add_argument("--seed", type=int, default=SEED)
  p.add_argument("--config", type=Path, default=None)
  return p


def load_cohort(root: Path, subjects: list, channels_mode: str, banks: Sequence[str], thresholds: dict, fail_fraction: float,
                need_x: bool, names: Sequence[str] = ()) -> tuple:
  """Probe every subject (montage, gate decision), choose the channels, load the windows with them (`load_subject`).
  `channels_mode == "names"` (P22.2): subjects whose gate dropped a named channel are left out (printed with the dropped
  channels); the cohort is the rest, `ValueError` below 2 subjects. Returns `(channels, loaded subjects)`."""
  probe = {s: load_subject(root / s, (), "shared", thresholds=thresholds, channel_fail_fraction=fail_fraction) for s in subjects}
  montages = {s: d["channels_all"] for s, d in probe.items()}
  kept_of = {s: d["channel_names"] for s, d in probe.items()}
  if channels_mode == "names":
    remaining, left = leave_out_for_names(montages, kept_of, names)
    for s, dropped in left.items():
      print(f"[-] Leaving out {s}: gate dropped {', '.join(dropped)}", flush=True)
    for s in remaining:
      gd = probe[s]["channels_dropped"]
      print(f"[=] Keeping {s}: gate accepted every named channel; gate dropped {', '.join(gd) if gd else 'nothing'}", flush=True)
    if len(remaining) < 2:
      raise ValueError(f"LOSO needs >= 2 subjects whose gate accepted all of {list(names)}; left: {remaining}")
    subjects = remaining
    montages, kept_of = {s: montages[s] for s in subjects}, {s: kept_of[s] for s in subjects}
  chosen = choose_channels(montages, kept_of, channels_mode, names)
  loaded = []
  for s in subjects:
    t0 = time.time()
    d = load_subject(root / s, CLASS_CODES, "shared", bands=banks, thresholds=thresholds,
                     channel_fail_fraction=fail_fraction, channels=chosen)
    if "fbcca" in banks:
      d["fb"] = fbcca_features(d)
    if not need_x:
      d.pop("X")
    d["bands"].pop("fbcca", None)   # only the scores `fb` are pooled
    print(f"[+] {s}: {len(d['y'])} windows of {d['n_trials']} trials, fs {d['fs']:g} ({d['fs_source']}), gate kept "
          f"[{', '.join(probe[s]['channel_names'])}], {d['source']}; {time.time() - t0:.1f} s", flush=True)
    loaded.append(d)
  return chosen, loaded


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  capture_run_state()                                  # git head + dirty flag ONCE per process (P21 C-1)
  try:
    args.channels, args.channel_names = parse_channels(args.channels)
  except ValueError as e:
    raise SystemExit(f"[x] {e}")
  methods = [NETWORK_METHODS.get(m, m) for m in dict.fromkeys(args.methods)]
  methods = [m for m in METHOD_ORDER if m in methods]
  root = args.data_root / folder_name(args.window, args.stride_sec)
  subjects = check_subject_names(args.subjects if args.subjects else discover_subjects(root))
  bad = [s for s in subjects if not is_built(root / s)]
  if bad or len(subjects) < 2:
    raise SystemExit(f"[x] LOSO needs >= 2 built subjects in {root}; not built or too few: {bad or subjects}")
  cfg = load_config(args.config or ROOT / "configs" / "pipeline_config.yaml")
  q = quality_params_from_config(cfg)
  thresholds = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  nets = [m for m in methods if m in NETWORK_METHODS.values()]
  dev = "cpu"
  if nets:
    import torch
    dev = pick_device(args.device)
    if dev == "cuda":
      torch.backends.cudnn.deterministic = True
      torch.backends.cudnn.benchmark = False
  out = args.out_dir
  print(f"LOSO: methods {methods}, window {args.window:g} s stride {args.stride_sec:g} s, cohort {len(subjects)} subjects "
        f"[{', '.join(subjects)}], channels {args.channels if args.channels != 'names' else args.channel_names}; outer split = subject, trial ids offset by {TRIAL_OFFSET} per subject "
        f"(R1, PF-33), every fit on the training subjects only (R2); 2-tap smoothing within trial (R8); {SUBJNORM_NOTE if 'lda_subjnorm' in methods else ''}; "
        f"device {dev}", flush=True)
  banks = tuple(b for b, need in (("fbcca", any(m in CLASSICAL for m in methods)),
                                  ("fbcsp", any("lda" in m for m in methods))) if need)
  t_all = time.time()
  try:
    chosen, loaded = load_cohort(root, subjects, args.channels, banks, thresholds, q["channel_fail_fraction"], bool(nets),
                                 args.channel_names)
  except ValueError as e:
    raise SystemExit(f"[x] {e}")
  subjects = [d["subject"] for d in loaded]            # explicit names may have left subjects out
  sessions = sorted({str(d["meta"].get("session", "?")) for d in loaded})
  P = pool(loaded, [b for b in banks if b != "fbcca"], consume=True)
  ctx = {"subjects": subjects, "channels": chosen, "fs": P["fs"], "classes": [int(c) for c in P["classes"]], "root": root,
         "n_windows": {d["subject"]: int(len(d["y"])) for d in loaded}}
  del loaded
  source = (f"built continuous folders {root.parent.name}/{root.name}, session {'/'.join(sessions)}, cohort {len(subjects)} "
            f"subjects ({', '.join(subjects) if len(subjects) < 8 else subjects[0] + '-' + subjects[-1]}), LOSO, channels {args.channels}")
  config_of = lambda m, s: fold_config(m, s, ctx, args)
  print(f"Channels ({args.channels}): {', '.join(chosen)}" + {"common": "", "all": " (gate channel drops ignored)",
                                                           "names": " (explicit; gate accepted all in the kept subjects)"}[args.channels],
        flush=True)
  for m in methods:
    for k, s in enumerate(subjects):
      path = fold_path(out, m, s)
      cfg_now = config_of(m, s)
      if path.is_file():
        _, saved = load_fold(path)
        check_fold(path, saved, cfg_now)
        print(f"[skip] {m} test-{s}", flush=True)
        continue
      arrays, extra = run_fold(m, P, k, args, dev)
      save_fold(path, arrays, cfg_now)
      if args.save_models:
        save_models(args.models_dir, m, s, extra, ctx)
      acc = float(np.mean(np.asarray(arrays["proba"]).argmax(1) == np.searchsorted(P["classes"], arrays["y"])))
      print(f"[+] {m} test-{s}: acc {100 * acc:.2f}% on {len(arrays['y'])} windows, train {100 * float(arrays['train_acc']):.2f}%, "
            f"{float(arrays['seconds']):.1f} s", flush=True)
  res = build_summary(out, subjects, P["classes"], methods, config_of, source, args.partial_mean)
  if not res:
    print("[-] nothing evaluated")
    return 1
  out.mkdir(parents=True, exist_ok=True)
  res["summary"].to_csv(out / "summary.csv", index=False)
  res["per_subject"].to_csv(out / "per_subject.csv")
  res["predictions"].to_csv(out / "predictions.csv", index=False)
  res["confusion"].to_csv(out / "confusion.csv", index=False)
  res["folds"].to_csv(out / "folds.csv", index=False)
  (out / "loso_config.json").write_text(json.dumps(
    {"cohort": subjects, "channels_mode": args.channels, "channels": chosen, "git_head": RUN_STATE["git_head"],
     "git_dirty": RUN_STATE["git_dirty"], "folds": args.folds, "within_repeats": args.within_repeats, "window_sec": args.window,
     "stride_sec": args.stride_sec, "seed": args.seed, "trial_offset": TRIAL_OFFSET, "source": source}, indent=2) + "\n")
  print("\n" + res["summary"].drop(columns=["Channels", "Data source"]).to_string(index=False))
  print(f"\nPer subject:\n{res['per_subject'].to_string()}")
  if res["folds"]["degenerate"].any():
    print("\n[warn] degenerate network folds (best epoch <= 5 or train acc < chance + 10 pp):\n"
          + res["folds"][res["folds"]["degenerate"]].to_string(index=False))
  print(f"\nSaved: {out}/summary.csv, per_subject.csv, predictions.csv, confusion.csv, folds.csv, loso_config.json; "
        f"runtime {time.time() - t_all:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
