"""Edge-gated connectivity GNN under leave-one-subject-out (P23.2), with a within-subject reference on the same windows.

Data source: `<data-root>/w<len>_s<stride>/<S>/` (built continuous folders, `scripts.build_windows --filter-mode continuous
--banks fbcca fbcsp`), read only through `load_subject` with the channel choice of `benchmark_loso` (`--channels common|all|NAMES`,
PF-34; `load_cohort` is reused). Graph features are computed in memory per subject (`graph_features_for_subject`: P15 node power,
band-averaged coherence and CSD phase on the continuously filtered windows, fs from the metadata, R3) + the FBCCA scores of the
saved bank; the legacy 250 Hz cache is not used. Coherence is a per-window edge feature, so R4 concatenation does not apply.

Variants (P15): `nodes+F`, `nodes+coh+F` (default both; any `nodes[+coh][+phase][+F]`). Normalization (`--norm`, R2):
- `pooled` -> method `gnn_<variant>`: every input array is z-scored with the statistics of the TRAINING windows only.
- `subject` -> method `gnn_<variant>_subjnorm`: UNSUPERVISED PER-SUBJECT NORMALIZATION (test-time, R2 exception, PF-35): each
  subject's arrays (training subjects and the held-out one) are z-scored with that subject's OWN unlabeled whole-session statistics,
  no labels (offline upper bound; the held-out session is in the statistics). The `Normalization` column carries the label.

Protocols: `--protocol loso` (default): the subject is held out, the other subjects train (trial ids offset per subject, R1,
PF-33; nothing of the held-out subject reaches a `.fit()`). `--protocol within`: `StratifiedGroupKFold(5, shuffle, 42)` over the
true trial ids inside each subject (`benchmark_loso.within_splits`, R1) on the same windows and channels; only `--norm pooled`
runs there (subject normalization is a no-op).

`fit_gnn` (PF-32, PF-28): early stopping on ~20 % of the training TRIALS (first split of an inner grouped 5-fold over the
training windows' trial ids, `training.split_validation`; the held-out subject is never in it); `--val-frac 0` = fixed
`--max-epochs` epochs, last state. AdamW (lr 1e-3, wd 1e-2), cosine annealing (eta_min 1e-5, T_max = max epochs), label smoothing 0.05, batch 32 (P15
constants); patience 25, max 150 epochs, restore the best validation-loss state. `torch.manual_seed(seed)` precedes the model,
the batch shuffle uses its own generator seeded with `seed`. `--seeds 3` fits seeds 42, 43, 44 per fold; the fold probability is the
MEAN of the seeds' softmax, per-seed results are kept (`seeds.csv`, `Seed SD`). Per seed: train accuracy (eval mode, fitting windows),
validation accuracy, best epoch (1-based), epochs run; a seed is degenerate (P20 C-2) when its best epoch <= 5 or its train accuracy
< chance + 10 pp, a fold when any seed is. CPU runs are bit-identical on a rerun with the same `--threads`; CUDA is seeded but not asserted.

Resumable (PF-37, P21 C-1, P22 C-1): every fold is written atomically to `<out-dir>/folds/<method>__<protocol>__test-<S>[__fold-k].npz`
with a JSON `config` (cohort, training subjects, channels, window, stride, fs, variant, norm, protocol, seeds, hyperparameters,
device, training window counts, build `git_commit`s, config hash, git head recorded once at process start, dirty flag) and skipped
on rerun. `benchmark_loso.check_fold` REFUSES a different configuration or code ("use a new --out-dir"); there is no override.

Outputs (`--out-dir`, default `reports/loso_gnn` or `reports/within_gnn`): `summary.csv` (columns of `benchmark_loso` + `Protocol`,
`Normalization`, `Seeds`, `Seed SD`; `Acc SD` = SD over seeds of the 1.0 s accuracy), `per_subject.csv`, `predictions.csv`,
`confusion.csv`, `folds.csv` (per fold: train/val/test accuracy, gap, best epoch, seconds, degenerate, PF-30 diagnosis),
`seeds.csv`, `gnn_loso_config.json`. 2-tap smoothing within trial (R8); ITR = Wolpaw N = 5, T = window + 0.5 s. A within row of
a subject pools its 5 out-of-fold probability sets; its `Data source` says within-subject (P22 C-6). A method with fewer subjects
than the cohort gets no Mean/SD (`--partial-mean` overrides).

`--smoke-test`: 4 synthetic subjects (different gain, noise and offset), 2 variants x 2 norms, the within protocol, a rerun that must
skip every fold, mean synthetic LOSO accuracy > 40 %; scratch out-dir only (never `reports/`). Numbers are not results.
"""

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Sequence


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402

from scripts.benchmarks import benchmark_loso as L  # noqa: E402
from scripts.benchmarks.benchmark_window_sweep import folder_name  # noqa: E402
from scripts.connectivity.graph_modeling.benchmark_gnn import _tensors, diagnosis, make_model, predict_proba  # noqa: E402
from src.features.connectivity.graph_dataset import GraphDataset  # noqa: E402
from src.features.connectivity.graph_features_subject import graph_features_for_subject  # noqa: E402
from src.features.connectivity.graph_inputs import (GraphInputs, apply_standardizer, build_inputs, fit_standardizer,  # noqa: E402
                                                    parse_variant, standardize_fold)
from src.io.subject_data import CLASS_CODES, is_built, load_subject  # noqa: E402
from src.models.classical.benchmark_runner import load_config  # noqa: E402
from src.models.cnn.eegnet_cv import BATCH_SIZE, ETA_MIN, LABEL_SMOOTHING, LR, WEIGHT_DECAY  # noqa: E402
from src.models.cnn.spatial_spectral_cnn import resolve_device  # noqa: E402
from src.models.cnn.training import MAX_EPOCHS, PATIENCE, VAL_FRAC, split_validation  # noqa: E402
from src.models.graph.connectivity_gnn import count_parameters  # noqa: E402
from src.preprocessing.window_quality import quality_params_from_config  # noqa: E402

VARIANTS = ("nodes+F", "nodes+coh+F")
NORMS = ("pooled", "subject")
PROTOCOLS = ("loso", "within")
WITHIN_FOLDS, WITHIN_SPLIT_SEED = 5, 42
SEED_BASE = 42
THREADS = 2
N_CLASSES = 5
FEATURE_SOURCE = ("graph_features_for_subject (P15 definitions, in memory, continuously filtered clean stimulus windows, "
                  "fs from metadata, CSD phase) + FBCCA scores of the saved bank")
NORM_LABEL = {
  "pooled": "pooled: z-scored with the statistics of the training windows only (R2)",
  "subject": ("subject: unsupervised per-subject normalization, each subject's arrays z-scored with its own unlabeled whole-session "
              "statistics, no labels (test-time normalization, offline upper bound: the held-out session is in the statistics; "
              "R2 exception, PF-35)")}
EXTRA_COLUMNS = ["Protocol", "Normalization", "Seeds", "Seed SD"]
SUMMARY_COLUMNS = L.SUMMARY_COLUMNS + EXTRA_COLUMNS
SMOKE = {"max_epochs": 30, "patience": 8, "seeds": 2, "n_subjects": 4, "trials_per_class": 6, "windows_per_trial": 4}
SMOKE_MIN_ACC = 40.0


def method_name(variant: str, norm: str) -> str:
  return f"gnn_{variant}" + ("_subjnorm" if norm == "subject" else "")


def make_specs(variants: Sequence[str], norms: Sequence[str]) -> list:
  """Method specs in output order: variant-major, `pooled` before `subject`."""
  return [{"variant": v, "norm": n, "method": method_name(v, n)} for v in variants for n in NORMS if n in norms]


# --- inputs and normalization (R2) ---------------------------------------------------------------------------------

def concat_inputs(parts: Sequence[GraphInputs]) -> GraphInputs:
  cat = lambda f: None if f(parts[0]) is None else np.concatenate([f(p) for p in parts])
  return GraphInputs(cat(lambda p: p.node), cat(lambda p: p.edge), cat(lambda p: p.graph))


def subject_standardize(inp: GraphInputs, subj: np.ndarray) -> GraphInputs:
  """Every subject's rows z-scored with that subject's own statistics over all its rows (no labels, PF-35)."""
  out = {"node": np.empty_like(inp.node), "edge": None if inp.edge is None else np.empty_like(inp.edge),
         "graph": None if inp.graph is None else np.empty_like(inp.graph)}
  for s in np.unique(subj):
    rows = np.flatnonzero(subj == s)
    z = apply_standardizer(inp.take(rows), fit_standardizer(inp, rows))
    for key, arr in (("node", z.node), ("edge", z.edge), ("graph", z.graph)):
      if arr is not None:
        out[key][rows] = arr
  return GraphInputs(out["node"], out["edge"], out["graph"])


def fold_inputs(P: dict, spec: dict, tr: np.ndarray, te: np.ndarray) -> tuple:
  """`(train, test)` `GraphInputs` of a fold. pooled: statistics of the rows `tr` only. subject: each subject's own statistics
  (cached per variant; it never sees a label)."""
  inp = P["inputs"][spec["variant"]]
  if spec["norm"] == "pooled":
    return standardize_fold(inp, tr, te)
  cache = P.setdefault("_subjnorm", {})
  if spec["variant"] not in cache:
    cache[spec["variant"]] = subject_standardize(inp, P["subj"])
  z = cache[spec["variant"]]
  return z.take(tr), z.take(te)


# --- fit_gnn -------------------------------------------------------------------------------------------------------

def _loss_acc(model: nn.Module, inp: GraphInputs, y: np.ndarray, device) -> tuple:
  if len(y) == 0:
    return float("nan"), float("nan")
  p = predict_proba(model, inp, device)
  nll = -np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None))
  return float(nll.mean()), float(np.mean(p.argmax(1) == y))


def fit_gnn(train_inp: GraphInputs, yi: np.ndarray, groups: np.ndarray, seed: int = SEED_BASE, device="cpu",
            val_frac: float = VAL_FRAC, max_epochs: int = MAX_EPOCHS, patience: int = PATIENCE, batch_size: int = BATCH_SIZE,
            lr: float = LR, weight_decay: float = WEIGHT_DECAY, label_smoothing: float = LABEL_SMOOTHING) -> dict:
  """Train one ConnectivityGNN on the (already standardized) training rows. `yi` in 0..4, `groups` = trial ids of those rows.

  `val_frac > 0`: ~`val_frac` of the training TRIALS (grouped) validate early stopping and the best validation-loss state is
  restored (PF-32); `val_frac == 0`: no validation, `max_epochs` fixed epochs, last state. Returns `model` (eval mode),
  `fit_idx`/`val_idx` (into the arguments), `train_acc` (fitting rows, eval mode), `val_acc`, `val_loss`, `best_epoch` (1-based),
  `epochs_run`, `n_params`, `history` (train loss, val loss per epoch)."""
  dev = torch.device(device)
  yi, groups = np.asarray(yi).astype(np.int64), np.asarray(groups)
  if val_frac > 0:
    fit_idx, val_idx = split_validation(yi, groups, val_frac, seed)
    if set(groups[fit_idx]) & set(groups[val_idx]):
      raise AssertionError("trial shared between fitting and validation windows")
  else:
    fit_idx, val_idx = np.arange(len(yi)), np.zeros(0, dtype=int)
  fit_inp, val_inp = train_inp.take(fit_idx), train_inp.take(val_idx)
  yf, yv = yi[fit_idx], yi[val_idx]
  torch.manual_seed(seed)
  model = make_model(fit_inp, N_CLASSES).to(dev)
  opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
  sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max_epochs, eta_min=ETA_MIN)
  crit = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
  x, e, g = _tensors(fit_inp, dev)
  y = torch.from_numpy(yf).to(dev)
  gen = torch.Generator().manual_seed(seed)
  n = len(yf)
  best = {"loss": np.inf, "epoch": 0, "state": None}
  history, since = [], 0
  for epoch in range(1, max_epochs + 1):
    model.train()
    tot = 0.0
    perm = torch.randperm(n, generator=gen)
    for i in range(0, n, batch_size):
      b = perm[i:i + batch_size].to(dev)
      opt.zero_grad()
      loss = crit(model(x[b], None if e is None else e[b], None if g is None else g[b]), y[b])
      loss.backward()
      opt.step()
      tot += loss.item() * len(b)
    sched.step()
    if len(yv):
      vloss, _ = _loss_acc(model, val_inp, yv, dev)
      history.append((tot / n, vloss))
      if vloss < best["loss"]:
        best.update(loss=vloss, epoch=epoch, state={k: v.detach().clone() for k, v in model.state_dict().items()})
        since = 0
      else:
        since += 1
        if since >= patience:
          break
    else:
      history.append((tot / n, float("nan")))
  if len(yv):
    model.load_state_dict(best["state"])
    best_epoch = best["epoch"]
  else:
    best_epoch = len(history)
  model.eval()
  _, train_acc = _loss_acc(model, fit_inp, yf, dev)
  vloss, val_acc = _loss_acc(model, val_inp, yv, dev)
  return {"model": model, "fit_idx": fit_idx, "val_idx": val_idx, "train_acc": train_acc, "val_acc": val_acc, "val_loss": vloss,
          "best_epoch": best_epoch, "epochs_run": len(history), "n_params": count_parameters(model), "history": history}


def seeds_of(args) -> list:
  return [int(args.seed) + i for i in range(int(args.seeds))]


def fit_hyper(args) -> dict:
  return {"val_frac": args.val_frac, "max_epochs": args.max_epochs, "patience": args.patience, "batch_size": args.batch_size,
          "lr": args.lr, "weight_decay": WEIGHT_DECAY, "label_smoothing": LABEL_SMOOTHING, "eta_min": ETA_MIN,
          "threads": args.threads, "optimizer": "AdamW", "schedule": "cosine annealing, T_max = max_epochs", "model": "ConnectivityGNN(hidden 32, 2 layers, dropout 0.3)"}


def gnn_fold(train_inp: GraphInputs, yi_tr: np.ndarray, groups_tr: np.ndarray, test_inp: GraphInputs, args, dev: str) -> dict:
  """Fit every seed on the training rows, predict the test rows. `proba` = mean of the seeds' softmax; per-seed arrays kept."""
  kw = dict(val_frac=args.val_frac, max_epochs=args.max_epochs, patience=args.patience, batch_size=args.batch_size, lr=args.lr)
  runs = []
  for s in seeds_of(args):
    r = fit_gnn(train_inp, yi_tr, groups_tr, s, dev, **kw)
    r["proba"] = predict_proba(r["model"], test_inp, torch.device(dev))
    runs.append(r)
  seed_proba = np.stack([r["proba"] for r in runs])
  per = lambda key: np.array([r[key] for r in runs], dtype=float)
  return {"proba": seed_proba.mean(axis=0), "proba_seed": seed_proba, "runs": runs, "train_acc_seed": per("train_acc"),
          "val_acc_seed": per("val_acc"), "best_epoch_seed": per("best_epoch"), "epochs_run_seed": per("epochs_run"),
          "val_loss_seed": per("val_loss"), "n_val": float(np.mean([len(r["val_idx"]) for r in runs])),
          "degenerate_seed": np.array([L.is_degenerate(r["best_epoch"], r["train_acc"], N_CLASSES) for r in runs])}


# --- folds ---------------------------------------------------------------------------------------------------------

def fold_path(out: Path, method: str, protocol: str, subject: str, fold: Optional[int] = None) -> Path:
  return Path(out) / "folds" / (f"{method}__{protocol}__test-{subject}" + ("" if fold is None else f"__fold-{fold}") + ".npz")


def fold_config(spec: dict, test: str, fold: Optional[int], ctx: dict, args, dev: str) -> dict:
  state = L.RUN_STATE or L.capture_run_state()
  if args.protocol == "within":
    train = [test]
    n_train_fold = len(ctx["within_splits"][test][fold][0])
    n_test = len(ctx["within_splits"][test][fold][1])
  else:
    train = [s for s in ctx["subjects"] if s != test]
    n_train_fold = sum(ctx["n_windows"][s] for s in train)
    n_test = ctx["n_windows"][test]
  return {"method": spec["method"], "protocol": args.protocol, "variant": spec["variant"], "norm": spec["norm"],
          "normalization": NORM_LABEL[spec["norm"]], "test_subject": test, "fold": fold,
          "n_folds": args.folds if args.protocol == "within" else None,
          "within_split": (f"StratifiedGroupKFold({args.folds}, shuffle, random_state={WITHIN_SPLIT_SEED}) over true trial ids"
                           if args.protocol == "within" else None),
          "train_subjects": train, "cohort": ctx["subjects"], "channels_mode": args.channels, "channels": ctx["channels"],
          "window_sec": args.window, "stride_sec": args.stride_sec, "fs": ctx["fs"], "classes": ctx["classes"],
          "quality": "shared", "seeds": seeds_of(args), "hyper": fit_hyper(args), "device": dev,
          "feature_source": FEATURE_SOURCE, "trial_offset": L.TRIAL_OFFSET, "n_windows_test": n_test,
          "n_windows_train_fold": int(n_train_fold), **L.provenance_fields(ctx, train, test),
          "git_head": state["git_head"], "git_dirty": state["git_dirty"], "data_root": str(ctx["root"])}


def run_fold(spec: dict, P: dict, k: int, fold: Optional[int], ctx: dict, args, dev: str) -> tuple:
  """Compute one fold of the subject index `k` (LOSO: `fold` None). Returns `(arrays to store, fitted models)`."""
  t0 = time.time()
  rows = np.flatnonzero(P["subj"] == k)
  if args.protocol == "within":
    tr_l, te_l = ctx["within_splits"][P["subjects"][k]][fold]
    tr, te = rows[tr_l], rows[te_l]
    assert not set(P["groups"][tr]) & set(P["groups"][te]), "a trial is on both sides of a within fold"
  else:
    tr, te = L.loso_split(P["subj"], k)
    te_l = np.arange(len(te))
    assert not set(P["groups"][tr]) & set(P["groups"][te]), "held-out trial ids reach the training groups"
  tr_inp, te_inp = fold_inputs(P, spec, tr, te)
  r = gnn_fold(tr_inp, P["yi"][tr], P["groups"][tr], te_inp, args, dev)
  for run in r["runs"]:
    if set(P["subj"][tr][run["val_idx"]]) & {k} and args.protocol == "loso":
      raise AssertionError("validation windows of the held-out subject")
  arrays = {"proba": r["proba"], "proba_seed": r["proba_seed"], "y": P["y"][te], "trial_id": P["trial"][te] - L.TRIAL_OFFSET * k,
            "offset": P["offsets"][te], "row_idx": np.asarray(te_l), "train_acc": r["train_acc_seed"].mean(),
            "val_acc": np.nanmean(r["val_acc_seed"]) if not np.isnan(r["val_acc_seed"]).all() else np.nan,
            "best_epoch": r["best_epoch_seed"].mean(), "epochs_run": r["epochs_run_seed"].mean(),
            "train_acc_seed": r["train_acc_seed"], "val_acc_seed": r["val_acc_seed"], "best_epoch_seed": r["best_epoch_seed"],
            "epochs_run_seed": r["epochs_run_seed"], "val_loss_seed": r["val_loss_seed"], "degenerate_seed": r["degenerate_seed"],
            "n_train": len(tr), "n_val": r["n_val"], "seconds": time.time() - t0}
  return {k_: np.asarray(v) for k_, v in arrays.items()}, [x["model"] for x in r["runs"]]


def run_protocol(P: dict, ctx: dict, specs: list, args, dev: str, out: Path) -> dict:
  """Run (or skip) every fold of `args.protocol`; returns counters `{"run", "skipped"}`."""
  count = {"run": 0, "skipped": 0}
  only = set(args.only_test or [])
  for spec in specs:
    for k, s in enumerate(P["subjects"]):
      if only and s not in only:
        continue
      folds = [None] if args.protocol == "loso" else [f for f in range(args.folds) if args.only_fold in (None, f)]
      for f in folds:
        path = fold_path(out, spec["method"], args.protocol, s, f)
        cfg_now = fold_config(spec, s, f, ctx, args, dev)
        tag = f"{spec['method']} {args.protocol} test-{s}" + ("" if f is None else f" fold-{f}")
        if path.is_file():
          _, saved = L.load_fold(path)
          L.check_fold(path, saved, cfg_now)
          print(f"[skip] {tag}", flush=True)
          count["skipped"] += 1
          continue
        arrays, _ = run_fold(spec, P, k, f, ctx, args, dev)
        L.save_fold(path, arrays, cfg_now)
        count["run"] += 1
        acc = float(np.mean(arrays["proba"].argmax(1) == np.searchsorted(P["classes"], arrays["y"])))
        seed_acc = [float(np.mean(p.argmax(1) == np.searchsorted(P["classes"], arrays["y"]))) for p in arrays["proba_seed"]]
        print(f"[+] {tag}: acc {100 * acc:.2f}% (seeds {', '.join(f'{100 * a:.1f}' for a in seed_acc)}) on {len(arrays['y'])} windows, "
              f"train {100 * float(arrays['train_acc']):.2f}%, best epoch {float(arrays['best_epoch']):.1f}, "
              f"{float(arrays['seconds']):.1f} s", flush=True)
  return count


# --- summary -------------------------------------------------------------------------------------------------------

def assemble_within(parts: list) -> dict:
  """Pool the out-of-fold arrays of one subject's within folds back into subject row order (every row once)."""
  idx = np.concatenate([a["row_idx"] for a in parts])
  n = len(idx)
  if not np.array_equal(np.sort(idx), np.arange(n)):
    raise ValueError("within folds do not cover the subject's windows exactly once")
  out = {}
  for key in ("y", "trial_id", "offset", "proba"):
    out[key] = np.empty((n,) + parts[0][key].shape[1:], dtype=parts[0][key].dtype)
    out[key][idx] = np.concatenate([a[key] for a in parts])
  out["proba_seed"] = np.empty((parts[0]["proba_seed"].shape[0], n, parts[0]["proba_seed"].shape[2]))
  out["proba_seed"][:, idx] = np.concatenate([a["proba_seed"] for a in parts], axis=1)
  mean = lambda key: np.asarray(np.nanmean([float(a[key]) for a in parts]) if not all(np.isnan(float(a[key])) for a in parts) else np.nan)
  for key in ("train_acc", "val_acc", "best_epoch", "epochs_run", "n_train", "n_val"):
    out[key] = mean(key)
  out["seconds"] = np.asarray(sum(float(a["seconds"]) for a in parts))
  for key in ("train_acc_seed", "val_acc_seed", "best_epoch_seed", "epochs_run_seed"):
    out[key] = np.nanmean(np.stack([a[key] for a in parts]), axis=0) if not np.isnan(np.stack([a[key] for a in parts])).all() \
      else np.full(parts[0][key].shape, np.nan)
  return out


def collect(out: Path, specs: list, subjects: list, config_of, args) -> tuple:
  """Stored folds of this invocation's methods: `({(method, subject): (arrays, config of fold 0)}, [per-fold info])`.
  Every file passes `check_fold` (PF-37). A within subject needs all its folds."""
  items, info = {}, []
  folds = [None] if args.protocol == "loso" else [f for f in range(args.folds) if args.only_fold in (None, f)]
  for spec in specs:
    for s in subjects:
      parts, cfgs = [], []
      for f in folds:
        p = fold_path(out, spec["method"], args.protocol, s, f)
        if not p.is_file():
          continue
        arrays, saved = L.load_fold(p)
        L.check_fold(p, saved, config_of(spec, s, f))
        parts.append(arrays)
        cfgs.append(saved)
        info.append((spec, s, f, arrays, saved))
      if not parts:
        continue
      if len(parts) < len(folds):
        print(f"[warn] {spec['method']} test-{s}: {len(parts)} of {len(folds)} within folds; subject left out of the summary", flush=True)
        continue
      items[(spec["method"], s)] = (parts[0] if args.protocol == "loso" else assemble_within(parts), cfgs[0])
  return items, info


def seed_table(spec: dict, subject: str, arrays: dict, config: dict, classes: np.ndarray, protocol: str) -> list:
  yi = np.searchsorted(classes, arrays["y"])
  rows = []
  for i, (seed, pr) in enumerate(zip(config["seeds"], arrays["proba_seed"])):
    sm = L.smooth_two_tap(pr, arrays["trial_id"], arrays["offset"]).argmax(1)
    rows.append({"Protocol": protocol, "Method": spec["method"], "Subject": subject, "Seed": seed,
                 "Acc (%)": round(100 * float(np.mean(pr.argmax(1) == yi)), 2),
                 "2-tap Smoothed (%)": round(100 * float(np.mean(sm == yi)), 2),
                 "Train Acc (%)": round(100 * float(arrays["train_acc_seed"][i]), 2),
                 "Val Acc (%)": round(100 * float(arrays["val_acc_seed"][i]), 2) if not np.isnan(arrays["val_acc_seed"][i]) else np.nan,
                 "Best Epoch": float(arrays["best_epoch_seed"][i]), "Epochs Run": float(arrays["epochs_run_seed"][i])})
  return rows


def build_outputs(out: Path, specs: list, subjects: list, classes: np.ndarray, config_of, source: str, args) -> dict:
  items, finfo = collect(out, specs, subjects, config_of, args)
  if not items:
    return {}
  rows, preds, cms, seed_rows = [], [], {}, []
  for spec in specs:
    for s in subjects:
      if (spec["method"], s) not in items:
        continue
      arrays, cfg = items[(spec["method"], s)]
      row, pr, cm = L.fold_rows(spec["method"], s, arrays, cfg, classes, source)
      sr = seed_table(spec, s, arrays, cfg, classes, args.protocol)
      sd = round(float(np.std([r_["Acc (%)"] for r_ in sr], ddof=1)), 2) if len(sr) > 1 else 0.0
      row.update({"Acc SD": sd, "Runs": len(sr), "Protocol": args.protocol, "Normalization": NORM_LABEL[spec["norm"]],
                  "Seeds": len(sr), "Seed SD": sd})
      pr.insert(0, "protocol", args.protocol)
      rows.append(row)
      preds.append(pr)
      cms[spec["method"]] = cms.get(spec["method"], 0) + cm
      seed_rows += sr
  per = pd.DataFrame(rows)
  order = [sp["method"] for sp in specs]
  short = {m: int((per["Method"] == m).sum()) for m in per["Method"].unique() if int((per["Method"] == m).sum()) < len(subjects)}
  for m, n in short.items():
    print(f"[warn] {m}: {n} subjects for a cohort of {len(subjects)}; " +
          ("cohort Mean/SD kept (--partial-mean)" if args.partial_mean else "no cohort Mean/SD written"), flush=True)
  cohort = L.cohort_rows(per, len(subjects), args.partial_mean)
  summary = pd.concat([per, cohort], ignore_index=True)
  info = {sp["method"]: sp for sp in specs}
  for m, sp in info.items():
    g = summary["Method"] == m
    summary.loc[g, "Protocol"] = args.protocol
    summary.loc[g, "Normalization"] = NORM_LABEL[sp["norm"]]
    summary.loc[g, "Seeds"] = len(seeds_of(args))
    sub = summary[g & ~summary["Subject"].isin(["Mean", "SD"])]["Seed SD"].astype(float)
    full = m not in short or args.partial_mean
    summary.loc[g & (summary["Subject"] == "Mean"), "Seed SD"] = round(float(sub.mean()), 2) if full and len(sub) else np.nan
    summary.loc[g & (summary["Subject"] == "SD"), "Seed SD"] = round(float(sub.std(ddof=1)), 2) if full and len(sub) > 1 else np.nan
  summary = summary[SUMMARY_COLUMNS]
  summary["_m"] = summary["Method"].map({m: i for i, m in enumerate(order)})
  summary["_s"] = summary["Subject"].map(lambda s: (1, 0) if s == "Mean" else (2, 0) if s == "SD" else (0, int(s[1:])))
  summary = summary.sort_values(["_m", "_s"], kind="mergesort").drop(columns=["_m", "_s"]).reset_index(drop=True)
  subs_only = summary[~summary["Subject"].isin(["Mean", "SD"])]
  piv = lambda col: subs_only.pivot(index="Subject", columns="Method", values=col)
  cols = [m for m in order if m in set(subs_only["Method"])]
  per_subject = pd.concat({"Acc (%)": piv("Acc (%)")[cols], "2-tap Smoothed (%)": piv("2-tap Smoothed (%)")[cols]}, axis=1)
  per_subject = per_subject.loc[sorted(per_subject.index, key=lambda s: int(s[1:]))]
  per_subject.loc["Mean"] = per_subject.mean()
  per_subject.loc["SD"] = per_subject.iloc[:-1].std(ddof=1) if len(per_subject) > 2 else 0.0
  if not args.partial_mean:
    for m in short:
      per_subject.loc[["Mean", "SD"], [(c, m) for c in ("Acc (%)", "2-tap Smoothed (%)")]] = np.nan
  conf = pd.DataFrame([{"method": m, "protocol": args.protocol, "true": int(classes[i]), "pred": int(classes[j]), "count": int(cm[i, j])}
                       for m, cm in cms.items() for i in range(len(classes)) for j in range(len(classes))])
  finfo_rows = []
  for spec, s, f, arrays, saved in finfo:
    if (spec["method"], s) not in items:
      continue
    yi = np.searchsorted(classes, arrays["y"])
    test_acc = 100 * float(np.mean(arrays["proba"].argmax(1) == yi))
    tr = 100 * float(arrays["train_acc"])
    finfo_rows.append({"Protocol": args.protocol, "Method": spec["method"], "Test subject": s, "Fold": "" if f is None else f,
                       "Train subjects": len(saved["train_subjects"]), "Train windows": int(arrays["n_train"]),
                       "Test windows": len(arrays["y"]), "Train Acc (%)": round(tr, 2),
                       "Val Acc (%)": round(100 * float(arrays["val_acc"]), 2) if not np.isnan(float(arrays["val_acc"])) else np.nan,
                       "Test Acc (%)": round(test_acc, 2), "Train - Test (pp)": round(tr - test_acc, 2),
                       "Best Epoch": round(float(arrays["best_epoch"]), 2), "Epochs Run": round(float(arrays["epochs_run"]), 2),
                       "Seconds": round(float(arrays["seconds"]), 2), "degenerate": bool(np.any(arrays["degenerate_seed"])),
                       "Degenerate seeds": int(np.sum(arrays["degenerate_seed"])), "Seeds": len(saved["seeds"]),
                       "Diagnosis": diagnosis(tr, test_acc)})
  return {"summary": summary, "per_subject": per_subject.round(2), "predictions": pd.concat(preds, ignore_index=True),
          "confusion": conf, "folds": pd.DataFrame(finfo_rows), "seeds": pd.DataFrame(seed_rows)}


def write_outputs(out: Path, res: dict, args, ctx: dict, source: str) -> None:
  out.mkdir(parents=True, exist_ok=True)
  res["summary"].to_csv(out / "summary.csv", index=False)
  res["per_subject"].to_csv(out / "per_subject.csv")
  res["predictions"].to_csv(out / "predictions.csv", index=False)
  res["confusion"].to_csv(out / "confusion.csv", index=False)
  res["folds"].to_csv(out / "folds.csv", index=False)
  res["seeds"].to_csv(out / "seeds.csv", index=False)
  (out / "gnn_loso_config.json").write_text(json.dumps(
    {"protocol": args.protocol, "cohort": ctx["subjects"], "channels_mode": args.channels, "channels": ctx["channels"],
     "variants": list(args.variants), "norms": list(args.norm), "seeds": seeds_of(args), "hyper": fit_hyper(args),
     "git_head": L.RUN_STATE["git_head"], "git_dirty": L.RUN_STATE["git_dirty"], "window_sec": args.window,
     "stride_sec": args.stride_sec, "feature_source": FEATURE_SOURCE, "source": source}, indent=2) + "\n")


# --- data ----------------------------------------------------------------------------------------------------------

def assemble(loaded: list, datasets: list, variants: Sequence[str]) -> dict:
  """Pooled arrays (`benchmark_loso.pool`: offset trial ids, subject index) + one pooled `GraphInputs` per variant.
  Row i of the pool is row i of the matching dataset (same order as `loaded`)."""
  P = L.pool(loaded, ())
  P["inputs"] = {v: concat_inputs([build_inputs(ds, v) for ds in datasets]) for v in variants}
  if not np.array_equal(P["y"], np.concatenate([np.asarray(ds.y) for ds in datasets])):
    raise AssertionError("graph dataset rows do not follow the pooled windows")
  return P


def make_ctx(P: dict, loaded: list, root: Path, config_path: Path) -> dict:
  return {"subjects": P["subjects"], "channels": P["channels"], "fs": P["fs"], "classes": [int(c) for c in P["classes"]],
          "root": root, **L.cohort_provenance(loaded, config_path)}


def add_within_splits(ctx: dict, P: dict, folds: int) -> None:
  ctx["within_splits"] = {}
  for k, s in enumerate(P["subjects"]):
    rows = np.flatnonzero(P["subj"] == k)
    ctx["within_splits"][s] = L.within_splits(P["yi"][rows], P["groups"][rows], folds, WITHIN_SPLIT_SEED)


def load_real(args) -> tuple:
  try:
    mode, names = L.parse_channels(args.channels)
  except ValueError as e:
    raise SystemExit(f"[x] {e}")
  args.channels = mode
  root = args.data_root / folder_name(args.window, args.stride_sec)
  from src.io.subject_data import discover_subjects
  subjects = L.check_subject_names(args.subjects if args.subjects else discover_subjects(root))
  bad = [s for s in subjects if not is_built(root / s)]
  if bad or len(subjects) < 2:
    raise SystemExit(f"[x] needs >= 2 built subjects in {root}; not built or too few: {bad or subjects}")
  config_path = args.config or ROOT / "configs" / "pipeline_config.yaml"
  q = quality_params_from_config(load_config(config_path))
  thresholds = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  try:
    chosen, loaded = L.load_cohort(root, subjects, mode, ("fbcca",), thresholds, q["channel_fail_fraction"], False, names)
  except ValueError as e:
    raise SystemExit(f"[x] {e}")
  datasets = []
  for d in loaded:                     # second read keeps the FBCCA bank that load_cohort drops; features are label-free
    dd = load_subject(root / d["subject"], CLASS_CODES, "shared", bands=("fbcca",), thresholds=thresholds,
                      channel_fail_fraction=q["channel_fail_fraction"], channels=chosen)
    ds = graph_features_for_subject(dd, chosen)
    if not (np.array_equal(ds.y, d["y"]) and np.array_equal(ds.trial_ids, d["trial_ids"]) and np.allclose(ds.X_fbcca, d["fb"])):
      raise AssertionError(f"{d['subject']}: graph rows differ from the loaded windows")
    datasets.append(ds)
    print(f"[+] {d['subject']}: graph features {ds.node.shape} node, {ds.edge_coh.shape} coh, fs {ds.fs:g}", flush=True)
  sessions = sorted({str(d["meta"].get("session", "?")) for d in loaded})
  P = assemble(loaded, datasets, args.variants)
  ctx = make_ctx(P, loaded, root, config_path)
  subs = P["subjects"]
  source = (f"built continuous folders {root.parent.name}/{root.name}, session {'/'.join(sessions)}, cohort {len(subs)} "
            f"subjects ({', '.join(subs) if len(subs) < 8 else subs[0] + '-' + subs[-1]}), LOSO, channels {mode}")
  return P, ctx, source


def synthetic_cohort(n_subjects: int, trials_per_class: int, windows_per_trial: int, C: int = 7, seed: int = 0) -> tuple:
  """In-memory stand-in: subject s has its own gain, noise and offset on class-dependent node, coherence and FBCCA features."""
  rng = np.random.default_rng(seed)
  proto_n = rng.normal(size=(5, C, 10))
  proto_e = rng.normal(size=(5, C, C, 5)) * 0.15
  gains, noises = [0.8, 1.0, 1.25, 1.5, 0.9, 1.1][:n_subjects], [0.9, 1.1, 1.4, 1.7, 1.0, 1.3][:n_subjects]
  loaded, datasets = [], []
  for s in range(n_subjects):
    n_trials = 5 * trials_per_class
    codes = rng.permutation(np.tile(np.arange(101, 106), trials_per_class))
    y = np.repeat(codes, windows_per_trial)
    tid = np.repeat(np.arange(n_trials), windows_per_trial)
    off = np.tile(np.arange(windows_per_trial) * 64, n_trials)
    yi = y - 101
    node = gains[s] * proto_n[yi] + noises[s] * rng.normal(size=(len(y), C, 10)) + rng.normal() * 2 + rng.normal(size=(C, 10))
    coh = np.clip(0.4 + gains[s] * proto_e[yi] + 0.1 * noises[s] * rng.normal(size=(len(y), C, C, 5)), 0, 1)
    fb = gains[s] * np.eye(5)[yi] * 0.5 + 0.3 * noises[s] * rng.normal(size=(len(y), 5)) + 0.5
    ds = GraphDataset(f"S{s + 1:02d}", node, coh, rng.normal(size=(len(y), C, C, 5, 2)), fb, y, tid, [f"c{i}" for i in range(C)],
                      [], 256.0, "synthetic", False)
    loaded.append({"subject": ds.subject, "y": y, "trial_ids": tid, "cv_groups": tid, "offsets": off, "fb": fb, "fs": 256.0,
                   "channel_names": ds.channels_kept, "meta": {"git_commit": "synthetic", "session": "SYN"}})
    datasets.append(ds)
  return loaded, datasets


def make_synthetic(args) -> tuple:
  loaded, datasets = synthetic_cohort(SMOKE["n_subjects"], SMOKE["trials_per_class"], SMOKE["windows_per_trial"])
  P = assemble(loaded, datasets, args.variants)
  ctx = make_ctx(P, loaded, Path("synthetic"), ROOT / "configs" / "pipeline_config.yaml")
  source = (f"SYNTHETIC in-memory cohort of {len(loaded)} subjects (different gain, noise, offset); not data, LOSO, "
            f"channels {len(P['channels'])} synthetic")
  return P, ctx, source


# --- driver --------------------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--data-root", type=Path, default=Path("data/processed_continuous"))
  p.add_argument("--window", type=float, default=1.0, help="window length of the built folders in s (default 1)")
  p.add_argument("--stride-sec", type=float, default=0.25, help="stride of the built folders (default 0.25)")
  p.add_argument("--subjects", nargs="*", default=None, help="default: every built S<k> found, numeric order")
  p.add_argument("--channels", nargs="+", default=["common"], metavar="common|all|NAME", help="as benchmark_loso (PF-34)")
  p.add_argument("--variants", nargs="+", default=list(VARIANTS), help=f"default {' '.join(VARIANTS)}")
  p.add_argument("--norm", nargs="+", choices=NORMS, default=["pooled"],
                 help="pooled -> gnn_<variant>; subject -> gnn_<variant>_subjnorm (test-time, offline upper bound)")
  p.add_argument("--protocol", choices=PROTOCOLS, default="loso")
  p.add_argument("--seeds", type=int, default=3, help="seeds per fold: --seed, --seed+1, ... (default 3 = 42 43 44)")
  p.add_argument("--seed", type=int, default=SEED_BASE)
  p.add_argument("--val-frac", type=float, default=VAL_FRAC, help="share of training trials for early stopping; 0 = fixed epochs")
  p.add_argument("--max-epochs", type=int, default=MAX_EPOCHS)
  p.add_argument("--patience", type=int, default=PATIENCE)
  p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
  p.add_argument("--lr", type=float, default=LR)
  p.add_argument("--folds", type=int, default=WITHIN_FOLDS, help="within protocol: StratifiedGroupKFold splits (default 5)")
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--threads", type=int, default=THREADS,
                 help=f"torch CPU threads (default {THREADS}: the networks are tiny and 16 threads were 2.4x slower in the P23 timing; "
                      "0 = torch default); part of the fold configuration")
  p.add_argument("--only-test", nargs="*", default=None, help="run only these held-out subjects (debug / timing; Mean/SD stay empty)")
  p.add_argument("--only-fold", type=int, default=None, help="within: run only this fold index (debug / timing)")
  p.add_argument("--partial-mean", action="store_true", help="write cohort Mean/SD of a method with fewer subjects than the cohort")
  p.add_argument("--out-dir", type=Path, default=None, help="default reports/loso_gnn or reports/within_gnn")
  p.add_argument("--config", type=Path, default=None)
  p.add_argument("--smoke-test", action="store_true", help="synthetic cohort, scratch out-dir; see the module docstring")
  return p


def check_args(args) -> None:
  for v in args.variants:
    parse_variant(v)
  if args.seeds < 1 or not 0 <= args.val_frac < 1:
    raise SystemExit("[x] --seeds >= 1 and 0 <= --val-frac < 1")
  if args.protocol == "within" and "subject" in args.norm:
    raise SystemExit("[x] --protocol within runs --norm pooled only: per-subject normalization is a no-op inside one subject")


def run_and_report(P: dict, ctx: dict, source: str, args, dev: str, out: Path) -> dict:
  specs = make_specs(args.variants, args.norm)
  if args.protocol == "within":
    add_within_splits(ctx, P, args.folds)
    source = L.within_source(source)
  count = run_protocol(P, ctx, specs, args, dev, out)
  config_of = lambda sp, s, f: fold_config(sp, s, f, ctx, args, dev)
  res = build_outputs(out, specs, P["subjects"], P["classes"], config_of, source, args)
  if res:
    write_outputs(out, res, args, ctx, source)
  return {"count": count, "res": res}


def print_report(r: dict, out: Path) -> None:
  res = r["res"]
  print("\n" + res["summary"].drop(columns=["Channels", "Data source", "Normalization"]).to_string(index=False))
  print(f"\nPer subject:\n{res['per_subject'].to_string()}")
  f = res["folds"]
  if len(f) and f["degenerate"].any():
    print("\n[warn] degenerate folds (a seed with best epoch <= 5 or train acc < chance + 10 pp):\n"
          + f[f["degenerate"]].drop(columns=["Diagnosis"]).to_string(index=False))
  print(f"\nSaved: {out}/summary.csv, per_subject.csv, predictions.csv, confusion.csv, folds.csv, seeds.csv, gnn_loso_config.json")


def smoke_out_dir(arg: Optional[Path]) -> Path:
  out = Path(arg) if arg else Path(tempfile.mkdtemp(prefix="gnn_loso_smoke_"))
  res, rep = out.resolve(), (ROOT / "reports").resolve()
  if res == rep or rep in res.parents:
    raise SystemExit(f"[x] --smoke-test writes to a scratch directory, never under reports/: {out}")
  return out


def file_digest(path: Path) -> str:
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_smoke(args) -> int:
  """Synthetic acceptance: LOSO (2 variants x 2 norms) and within (pooled), rerun skips every fold with identical outputs,
  mean synthetic LOSO accuracy > SMOKE_MIN_ACC. Returns the exit code."""
  out = smoke_out_dir(args.out_dir)
  args.variants, args.norm = list(VARIANTS), list(NORMS)
  args.seeds, args.max_epochs, args.patience = SMOKE["seeds"], SMOKE["max_epochs"], SMOKE["patience"]
  args.channels, args.only_test, args.only_fold = "synthetic", None, None
  dev = L.pick_device(args.device)
  P, ctx, source = make_synthetic(args)
  print(f"SMOKE TEST: {SMOKE} on a SYNTHETIC cohort; numbers are not results; out-dir {out}", flush=True)
  ok, results = True, {}
  for protocol, norms in (("loso", NORMS), ("within", ("pooled",))):
    args.protocol, args.norm = protocol, list(norms)
    d = out / protocol
    first = run_and_report(P, ctx, source, args, dev, d)
    digests = {n: file_digest(d / n) for n in ("summary.csv", "per_subject.csv", "predictions.csv", "confusion.csv", "folds.csv")}
    again = run_and_report(P, ctx, source, args, dev, d)
    same = digests == {n: file_digest(d / n) for n in digests}
    total = first["count"]["run"]
    skipped_all = again["count"]["run"] == 0 and again["count"]["skipped"] == total and total > 0
    print(f"[smoke] {protocol}: {total} folds run, rerun skipped {again['count']['skipped']} and ran {again['count']['run']}; "
          f"outputs identical {same}", flush=True)
    ok &= skipped_all and same
    results[protocol] = first["res"]
  s = results["loso"]["summary"]
  means = s[s["Subject"] == "Mean"].set_index("Method")["Acc (%)"]
  within = results["within"]["summary"]
  print("\nSynthetic LOSO mean accuracy per method (%):\n" + means.to_string())
  print("Synthetic within mean accuracy per method (%):\n" + within[within["Subject"] == "Mean"].set_index("Method")["Acc (%)"].to_string())
  overall = float(means.mean())
  print(f"\n[smoke] mean synthetic LOSO accuracy {overall:.2f}% (needs > {SMOKE_MIN_ACC:g}%)", flush=True)
  ok &= overall > SMOKE_MIN_ACC
  print("[smoke] PASS" if ok else "[smoke] FAIL", flush=True)
  return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  check_args(args)
  L.capture_run_state()
  t0 = time.time()
  if args.threads > 0:
    torch.set_num_threads(args.threads)
  if args.smoke_test:
    return run_smoke(args)
  dev = L.pick_device(args.device)
  if dev == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  out = args.out_dir or Path("reports/loso_gnn" if args.protocol == "loso" else "reports/within_gnn")
  P, ctx, source = load_real(args)
  print(f"GNN {args.protocol}: variants {args.variants}, norms {args.norm}, seeds {seeds_of(args)}, cohort {len(P['subjects'])} subjects "
        f"[{', '.join(P['subjects'])}], channels {', '.join(P['channels'])}, device {dev}; every fit on training windows only (R2), "
        f"early stopping on {args.val_frac:g} of the training trials; 2-tap smoothing within trial (R8)"
        + (f"; {NORM_LABEL['subject']}" if "subject" in args.norm else ""), flush=True)
  r = run_and_report(P, ctx, source, args, dev, out)
  if not r["res"]:
    print("[-] nothing evaluated")
    return 1
  print_report(r, out)
  print(f"runtime {time.time() - t0:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
