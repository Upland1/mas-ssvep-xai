"""Training and CV of EEGNet on raw windows (P08.2); network-agnostic since P09; trial-grouped CV since P11.

`train_model` / `train_and_eval_cv` take a `build_model(n_classes, n_channels, n_samples)` factory (default
EEGNet), so Compact-CNN and ShallowConvNet (P09) use the identical protocol and cannot drift. The max-norm
step runs only for models that define `apply_max_norm` (EEGNet).

Convention (PF-28): `torch.manual_seed(42 + fold)` before each fold's model, a seeded DataLoader
generator, AdamW (wd 1e-2), CosineAnnealingLR(T_max=epochs, eta_min=1e-5), CrossEntropyLoss(label_smoothing
0.05), fixed epochs, no validation split and no early stopping, augmentation off by default (P10: `augment=True`
wraps the training fold only, after z-scoring, in `SSVEPAugmentedDataset(seed=42 + fold)`, whose generator is
separate from the torch RNG). Max-norm is applied
after every optimizer step. Each window is z-scored per channel over its own time samples (R2: uses no
other window).

Protocol (P11): `cv="grouped"` (default, R1) = `StratifiedGroupKFold(5, shuffle, 42)` over trial ids `groups`
(`cv_utils.make_splits`), the same fold matrix for the OFF and ON arms; `cv="legacy"` = the P05-P10 window-level
`StratifiedKFold` (R1/PF-01, leaky, labelled). 2.0 s rule `smoothing="mod5"` (default: R8 legacy-folder clause, `i % 5`
of the clean array) or `"trial"` (reset at each trial id, PF-02 diagnostic), both via `legacy_eval.accuracies`.
Training accuracy (PF-30) is measured in eval mode on the un-augmented training fold after the last epoch.
"""

from typing import Callable, Optional

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.models.classical.legacy_eval import SEED, accuracies, cv_label, smooth_label
from src.models.cnn.eegnet import EEGNetSSVEP
from src.models.cnn.spatial_spectral_cnn import label_maps, resolve_device
from src.preprocessing.dataset.augmentation import SSVEPAugmentedDataset
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials, make_splits

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
                batch_size: int = BATCH_SIZE, lr: float = LR, build_model: Optional[Callable] = None,
                augment_seed: Optional[int] = None) -> nn.Module:
  """Train one network (default EEGNet) on z-scored `X (n, C, T)`. `torch.manual_seed(seed)` precedes the model (PF-28).

  `augment_seed` not None: the training windows are augmented on the fly (P10, PF-29) from a separate numpy generator."""
  torch.manual_seed(seed)
  model = (build_model or build_eegnet)(int(yi.max()) + 1, X.shape[1], X.shape[2]).to(device)
  max_norm = getattr(model, "apply_max_norm", None)
  opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
  sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=ETA_MIN)
  crit = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
  gen = torch.Generator().manual_seed(seed)
  if augment_seed is None:
    data = TensorDataset(torch.from_numpy(X), torch.from_numpy(yi.astype(np.int64)))
  else:
    data = SSVEPAugmentedDataset(X, yi, seed=augment_seed)
  loader = DataLoader(data, batch_size=batch_size, shuffle=True, generator=gen)
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
                      verbose: bool = False, augment: bool = False, groups: Optional[np.ndarray] = None,
                      cv: str = "grouped", smoothing: str = "mod5") -> dict:
  """CV of a network (default EEGNet) on raw clean windows `X (n, C, T)` with condition codes `y`.

  `cv="grouped"` (R1) needs `groups` = trial id per window (`cv_utils.build_trial_ids` on the pre-gate labels, then the
  valid mask, PF-03) and asserts that no id is on both sides of any fold; `cv="legacy"` is the leaky P05-P10 split.
  Returns `pred` (codes), `proba` (classes sorted), `accuracy`, `smoothed_accuracy` (`smoothing` rule), `train_accuracy`
  (mean over folds, un-augmented training fold), per-fold lists, `classes`, `n_params`, `cv`, `smoothing`, `splits`.
  """
  dev = resolve_device(device)
  classes, to_idx = label_maps(y)
  yi = np.array([to_idx[int(c)] for c in y])
  Xz = zscore_windows(X)
  proba = np.zeros((len(y), len(classes)))
  fold_train, fold_test, n_params = [], [], 0
  splits = make_splits(cv, yi, groups, seed)
  if cv == "grouped":
    assert_no_shared_trials(splits, groups)
  for fold, (tr, te) in enumerate(splits):
    model = train_model(Xz[tr], yi[tr], seed + fold, dev, epochs, batch_size, lr, build_model,
                        seed + fold if augment else None)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    proba[te] = predict_proba(model, Xz[te], dev)
    fold_test.append(float(np.mean(proba[te].argmax(1) == yi[te])))
    fold_train.append(float(np.mean(predict_proba(model, Xz[tr], dev).argmax(1) == yi[tr])))
    if verbose:
      print(f"    fold {fold}: train acc {100 * fold_train[-1]:.2f}%  test acc {100 * fold_test[-1]:.2f}%", flush=True)
  pred = np.array(classes)[proba.argmax(1)]
  a1, a2 = accuracies(np.asarray(y), pred, proba, groups, smoothing)
  return {"pred": pred, "proba": proba, "accuracy": a1, "smoothed_accuracy": a2,
          "train_accuracy": float(np.mean(fold_train)), "fold_test_acc": fold_test, "fold_train_acc": fold_train,
          "classes": classes, "n_params": n_params, "cv": cv_label(cv), "smoothing": smooth_label(smoothing, cv),
          "splits": splits}


def train_and_eval_eegnet_cv(X: np.ndarray, y: np.ndarray, epochs: int = EPOCHS, batch_size: int = BATCH_SIZE,
                             lr: float = LR, device: str = "auto", seed: int = SEED, verbose: bool = False,
                             groups: Optional[np.ndarray] = None, cv: str = "grouped", smoothing: str = "mod5") -> dict:
  """EEGNet entry point of `train_and_eval_cv` (P08 signature plus the P11 protocol arguments)."""
  return train_and_eval_cv(X, y, build_eegnet, epochs, batch_size, lr, device, seed, verbose, False, groups, cv, smoothing)
