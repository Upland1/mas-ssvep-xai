"""Network training for the P20 sweeps: `fit_network` (grouped early stopping) and `cnn_fold`.

Convention (PF-32, R2; decisions 2026-10-28 P20): the validation set for early stopping is the first split of an inner
`StratifiedGroupKFold(round(1 / val_frac), shuffle, random_state=seed)` over the TRAINING windows with their trial
ids (`groups`), i.e. ~20 % of the training trials; the test fold never enters. Input normalisation (per-channel mean
and std over the windows and time samples of the fitting windows) and augmentation (P10: intra-class mixup, scale,
shift, noise on the normalised training windows only, own numpy generator) use training windows only. AdamW (lr 1e-3,
batch 16, weight decay 0.01 = torch default), cosine annealing over `max_epochs` (eta_min 1e-5), label smoothing 0.1
on the training loss, validation loss is the plain cross-entropy; the state with the lowest validation loss is
restored (patience 25, max 150 epochs). `torch.manual_seed(seed)` precedes the model (PF-28).

Reported: `train_acc` (eval mode, un-augmented fitting windows = training minus validation, PF-30), `val_acc` and
`best_epoch` (1-based). Runs on CPU and CUDA.

Model names (PF-31 labels): `ccnn`; `compact_eegnet` = EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2, dropout=0.5);
`eegnet` = EEGNetSSVEP(F1=8, D=2, F2=16, kernel=fs//2, dropout=0.25). Neither is P09's `CompactCNN` (`compact_cnn`).
"""

import copy
from typing import Callable, Optional

import numpy as np
import torch
from sklearn.model_selection import StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.models.cnn.ccnn import CCNN
from src.models.cnn.eegnet import EEGNetSSVEP
from src.preprocessing.dataset.augmentation import SSVEPAugmentedDataset

MODELS = ("ccnn", "compact_eegnet", "eegnet")
MODEL_LABELS = {"ccnn": "ccnn", "compact_eegnet": "compact_eegnet", "eegnet": "eegnet"}
ALIASES = {"compact": "compact_eegnet", "cnn": "compact_eegnet"}
BATCH_SIZE = 16
LR = 1e-3
WEIGHT_DECAY = 0.01
ETA_MIN = 1e-5
LABEL_SMOOTHING = 0.1
VAL_FRAC = 0.2
MAX_EPOCHS = 150
PATIENCE = 25
NORM_EPS = 1e-6


def model_factory(name: str, fs: float) -> Callable:
  """`build(n_classes, n_channels, n_samples)` of a named network at sampling rate `fs` (kernel = fs // 2)."""
  name = ALIASES.get(name, name)
  k = int(fs) // 2
  if name == "ccnn":
    return lambda nc, ch, T: CCNN(nc, ch, T, fs=fs)
  if name == "compact_eegnet":
    return lambda nc, ch, T: EEGNetSSVEP(nc, ch, T, F1=96, D=1, F2=96, kernel_length=k, dropout_rate=0.5)
  if name == "eegnet":
    return lambda nc, ch, T: EEGNetSSVEP(nc, ch, T, F1=8, D=2, F2=16, kernel_length=k, dropout_rate=0.25)
  raise ValueError(f"unknown model {name!r}; choose from {MODELS}")


def fit_stats(X: np.ndarray) -> tuple:
  """Per-channel mean and std `(1, C, 1)` over windows and time of `X (n, C, T)` (fitting windows only)."""
  X = np.asarray(X, dtype=np.float64)
  return X.mean(axis=(0, 2), keepdims=True), X.std(axis=(0, 2), keepdims=True) + NORM_EPS


def normalise(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
  return ((np.asarray(X, dtype=np.float64) - mean) / std).astype(np.float32)


def predict_proba(model: nn.Module, X: np.ndarray, device: torch.device, chunk: int = 256) -> np.ndarray:
  """Softmax probabilities `(n, K)` of normalised float32 `X`, eval mode."""
  model.eval()
  out = []
  with torch.no_grad():
    for i in range(0, len(X), chunk):
      out.append(torch.softmax(model(torch.from_numpy(X[i:i + chunk]).to(device)), 1).cpu().numpy())
  return np.concatenate(out) if out else np.zeros((0, 0))


def split_validation(y: np.ndarray, groups: np.ndarray, val_frac: float, seed: int) -> tuple:
  """`(fit_idx, val_idx)` inside the training windows: first split of the inner grouped CV (PF-32)."""
  n_splits = max(2, int(round(1.0 / val_frac)))
  sgk = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
  fit, val = next(iter(sgk.split(np.zeros((len(y), 1)), y, groups)))
  return fit, val


def _loss_acc(model: nn.Module, X: np.ndarray, y: np.ndarray, device: torch.device) -> tuple:
  p = predict_proba(model, X, device)
  nll = -np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None))
  return float(nll.mean()), float(np.mean(p.argmax(1) == y))


def fit_network(X: np.ndarray, y: np.ndarray, groups: np.ndarray, build_model: Callable, seed: int = 42,
                device: str = "cpu", augment: bool = True, val_frac: float = VAL_FRAC, max_epochs: int = MAX_EPOCHS,
                patience: int = PATIENCE, batch_size: int = BATCH_SIZE, lr: float = LR,
                weight_decay: float = WEIGHT_DECAY, label_smoothing: float = LABEL_SMOOTHING) -> dict:
  """Train on the training windows `X (n, C, T)` with labels `y` in `0..K-1` and trial ids `groups`.

  Returns `model` (best-validation-loss state restored, eval mode), `mean`/`std` (normalisation of the fitting windows),
  `fit_idx`/`val_idx` (indices into the arguments), `train_acc`, `val_acc`, `val_loss`, `best_epoch` (1-based),
  `epochs_run`, `n_params`, `history` (per epoch train loss and val loss)."""
  X, y, groups = np.asarray(X), np.asarray(y).astype(np.int64), np.asarray(groups)
  dev = torch.device(device)
  fit_idx, val_idx = split_validation(y, groups, val_frac, seed)
  if set(groups[fit_idx]) & set(groups[val_idx]):
    raise AssertionError("trial shared between fitting and validation windows")
  mean, std = fit_stats(X[fit_idx])
  Xf, Xv = normalise(X[fit_idx], mean, std), normalise(X[val_idx], mean, std)
  yf, yv = y[fit_idx], y[val_idx]
  torch.manual_seed(seed)
  n_classes = int(y.max()) + 1
  model = build_model(n_classes, X.shape[1], X.shape[2]).to(dev)
  max_norm = getattr(model, "apply_max_norm", None)
  opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
  sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max_epochs, eta_min=ETA_MIN)
  crit = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
  gen = torch.Generator().manual_seed(seed)
  data = SSVEPAugmentedDataset(Xf, yf, seed=seed) if augment else TensorDataset(torch.from_numpy(Xf), torch.from_numpy(yf))
  loader = DataLoader(data, batch_size=batch_size, shuffle=True, generator=gen)
  if max_norm:
    max_norm()
  best = {"loss": np.inf, "epoch": 0, "state": copy.deepcopy(model.state_dict())}
  history, since = [], 0
  for epoch in range(1, max_epochs + 1):
    model.train()
    tot, cnt = 0.0, 0
    for bx, by in loader:
      if len(by) < 2:  # BatchNorm cannot train on one row
        continue
      bx, by = bx.to(dev), by.to(dev)
      opt.zero_grad()
      loss = crit(model(bx), by)
      loss.backward()
      opt.step()
      if max_norm:
        max_norm()
      tot, cnt = tot + loss.item() * len(by), cnt + len(by)
    sched.step()
    vloss, _ = _loss_acc(model, Xv, yv, dev)
    history.append((tot / max(cnt, 1), vloss))
    if vloss < best["loss"]:
      best.update(loss=vloss, epoch=epoch, state=copy.deepcopy(model.state_dict()))
      since = 0
    else:
      since += 1
      if since >= patience:
        break
  model.load_state_dict(best["state"])
  model.eval()
  _, train_acc = _loss_acc(model, Xf, yf, dev)
  vloss, val_acc = _loss_acc(model, Xv, yv, dev)
  return {"model": model, "mean": mean, "std": std, "fit_idx": fit_idx, "val_idx": val_idx, "train_acc": train_acc,
          "val_acc": val_acc, "val_loss": vloss, "best_epoch": best["epoch"], "epochs_run": len(history),
          "n_params": int(sum(p.numel() for p in model.parameters() if p.requires_grad)), "history": history}


def cnn_fold(X_tr: np.ndarray, y_tr: np.ndarray, groups_tr: np.ndarray, X_te: np.ndarray, fs: float, n_classes: int,
             model: str = "compact_eegnet", seed: int = 42, device: str = "cpu", augment: bool = True,
             **fit_kwargs) -> dict:
  """One CV fold: fit on the training windows, predict the test windows. `y_tr` in `0..n_classes-1`.

  Returns `proba (n_te, n_classes)`, `train_acc`, `val_acc`, `best_epoch` (plus `n_params`, `epochs_run`,
  `val_loss`). `groups_tr` are the true trial ids of the training windows (PF-32); the test windows are only
  normalised with the training statistics and predicted."""
  y_tr = np.asarray(y_tr)
  if y_tr.min() < 0 or y_tr.max() >= n_classes:
    raise ValueError(f"y_tr must lie in 0..{n_classes - 1}")
  build = model_factory(model, fs)
  r = fit_network(X_tr, y_tr, groups_tr, build, seed=seed, device=device, augment=augment, **fit_kwargs)
  proba = np.zeros((len(X_te), n_classes))
  if len(X_te):
    p = predict_proba(r["model"], normalise(X_te, r["mean"], r["std"]), torch.device(device))
    proba[:, :p.shape[1]] = p
  return {"proba": proba, "train_acc": r["train_acc"], "val_acc": r["val_acc"], "best_epoch": r["best_epoch"],
          "n_params": r["n_params"], "epochs_run": r["epochs_run"], "val_loss": r["val_loss"]}
