"""Training and legacy leaky CV of EEGNet on raw windows (P08.2, legacy Era A); network-agnostic since P09.

`train_model` / `train_and_eval_cv` take a `build_model(n_classes, n_channels, n_samples)` factory (default
EEGNet), so Compact-CNN and ShallowConvNet (P09) use the identical protocol and cannot drift. The max-norm
step runs only for models that define `apply_max_norm` (EEGNet).

Convention (PF-28): `torch.manual_seed(42 + fold)` before each fold's model, a seeded DataLoader
generator, AdamW (wd 1e-2), CosineAnnealingLR(T_max=epochs, eta_min=1e-5), CrossEntropyLoss(label_smoothing
0.05), fixed epochs, no validation split and no early stopping, no augmentation (P10). Max-norm is applied
after every optimizer step. Each window is z-scored per channel over its own time samples (R2: uses no
other window).

Legacy behaviours (labelled, fixed in P11): R1/PF-01 `StratifiedKFold(5, shuffle, 42)` over windows;
R8/PF-02 `i % 5` smoothing of the out-of-fold probabilities (`legacy_eval.accuracies`).
Training accuracy (PF-30) is measured in eval mode on the un-augmented training fold after the last epoch.
"""

from typing import Callable, Optional

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.models.classical.legacy_eval import CV_LABEL, SEED, accuracies, legacy_cv
from src.models.cnn.eegnet import EEGNetSSVEP
from src.models.cnn.spatial_spectral_cnn import label_maps, resolve_device

EPOCHS = 150
BATCH_SIZE = 32
LR = 1e-3
WEIGHT_DECAY = 1e-2
ETA_MIN = 1e-5
LABEL_SMOOTHING = 0.05
ZSCORE_EPS = 1e-6


def zscore_windows(X: np.ndarray, eps: float = ZSCORE_EPS) -> np.ndarray:
  """`(x - mean_t) / (std_t + eps)` per window and channel over its own time axis; float32 `(n, C, T)`."""
  X = np.asarray(X, dtype=np.float64)
  mu = X.mean(axis=-1, keepdims=True)
  sd = X.std(axis=-1, keepdims=True)
  return ((X - mu) / (sd + eps)).astype(np.float32)


def predict_proba(model: nn.Module, X: np.ndarray, device: torch.device, chunk: int = 256) -> np.ndarray:
  model.eval()
  out = []
  with torch.no_grad():
    for i in range(0, len(X), chunk):
      out.append(torch.softmax(model(torch.from_numpy(X[i:i + chunk]).to(device)), dim=1).cpu().numpy())
  return np.concatenate(out)


def build_eegnet(n_classes: int, n_channels: int, n_samples: int) -> nn.Module:
  return EEGNetSSVEP(n_classes=n_classes, n_channels=n_channels, n_samples=n_samples)


def train_model(X: np.ndarray, yi: np.ndarray, seed: int, device: torch.device, epochs: int = EPOCHS,
                batch_size: int = BATCH_SIZE, lr: float = LR, build_model: Optional[Callable] = None) -> nn.Module:
  """Train one network (default EEGNet) on z-scored `X (n, C, T)`. `torch.manual_seed(seed)` precedes the model (PF-28)."""
  torch.manual_seed(seed)
  model = (build_model or build_eegnet)(int(yi.max()) + 1, X.shape[1], X.shape[2]).to(device)
  max_norm = getattr(model, "apply_max_norm", None)
  opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
  sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=ETA_MIN)
  crit = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
  gen = torch.Generator().manual_seed(seed)
  loader = DataLoader(TensorDataset(torch.from_numpy(X), torch.from_numpy(yi.astype(np.int64))),
                      batch_size=batch_size, shuffle=True, generator=gen)
  if max_norm:
    max_norm()
  for _ in range(epochs):
    model.train()
    for bx, by in loader:
      if len(by) < 2:  # BatchNorm cannot train on a single row
        continue
      bx, by = bx.to(device), by.to(device)
      opt.zero_grad()
      crit(model(bx), by).backward()
      opt.step()
      if max_norm:
        max_norm()
    sched.step()
  return model


def train_and_eval_cv(X: np.ndarray, y: np.ndarray, build_model: Optional[Callable] = None, epochs: int = EPOCHS,
                      batch_size: int = BATCH_SIZE, lr: float = LR, device: str = "auto", seed: int = SEED,
                      verbose: bool = False) -> dict:
  """Legacy leaky CV (R1/PF-01) of a network (default EEGNet) on raw clean windows `X (n, C, T)` with condition codes `y`.

  Returns `pred` (codes), `proba` (classes sorted), `accuracy`, `smoothed_accuracy` (i%5, R8 legacy),
  `train_accuracy` (mean over folds, un-augmented training fold), per-fold lists, `classes`, `n_params`, `cv`.
  """
  dev = resolve_device(device)
  classes, to_idx = label_maps(y)
  yi = np.array([to_idx[int(c)] for c in y])
  Xz = zscore_windows(X)
  proba = np.zeros((len(y), len(classes)))
  fold_train, fold_test, n_params = [], [], 0
  for fold, (tr, te) in enumerate(legacy_cv(seed).split(np.zeros((len(y), 1)), yi)):
    model = train_model(Xz[tr], yi[tr], seed + fold, dev, epochs, batch_size, lr, build_model)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    proba[te] = predict_proba(model, Xz[te], dev)
    fold_test.append(float(np.mean(proba[te].argmax(1) == yi[te])))
    fold_train.append(float(np.mean(predict_proba(model, Xz[tr], dev).argmax(1) == yi[tr])))
    if verbose:
      print(f"    fold {fold}: train acc {100 * fold_train[-1]:.2f}%  test acc {100 * fold_test[-1]:.2f}%", flush=True)
  pred = np.array(classes)[proba.argmax(1)]
  a1, a2 = accuracies(np.asarray(y), pred, proba)
  return {"pred": pred, "proba": proba, "accuracy": a1, "smoothed_accuracy": a2,
          "train_accuracy": float(np.mean(fold_train)), "fold_test_acc": fold_test, "fold_train_acc": fold_train,
          "classes": classes, "n_params": n_params, "cv": CV_LABEL}


def train_and_eval_eegnet_cv(X: np.ndarray, y: np.ndarray, epochs: int = EPOCHS, batch_size: int = BATCH_SIZE,
                             lr: float = LR, device: str = "auto", seed: int = SEED, verbose: bool = False) -> dict:
  """EEGNet entry point of `train_and_eval_cv` (P08 signature, unchanged results)."""
  return train_and_eval_cv(X, y, build_eegnet, epochs, batch_size, lr, device, seed, verbose)
