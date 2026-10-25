"""Dual-branch fusion CNN on harmonic PSD (spatial-spectral) + FBCCA scores (P04.2, legacy Era A).

Branch 1 takes the `(B, 1, 4, 8)` map (4 occipital channels x 8 harmonic bins), branch 2 the 5
FBCCA scores. Both convolutions have `bias=False` (they are followed by BatchNorm; R-8 count
10,005, blocker B004). Training convention: AdamW lr 1e-3 wd 1e-2, cosine over 140 epochs,
label smoothing 0.1, batch 16, `torch.manual_seed(42 + fold)` before each fold's model (PF-28).

Legacy behaviours (labelled, fixed in P11):
- R1 / PF-01: `StratifiedKFold(5, shuffle, 42)` over windows (leaky).
- R8 / PF-02: `evaluate_temporal_smoothing` averages with the previous row, no trial reset.
Training accuracy is returned next to test accuracy. Runs on CPU and CUDA.
"""

from typing import Optional, Sequence

import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.features.ssvep.harmonic_psd import extract_harmonic_features
from src.preprocessing.dataset.smoothing import smooth_probabilities_legacy

N_CLASSES = 5
N_SPATIAL = (4, 8)
N_FBCCA = 5
EPOCHS = 140
BATCH_SIZE = 16
LR = 1e-3
WEIGHT_DECAY = 1e-2
LABEL_SMOOTHING = 0.1
SEED = 42
N_FOLDS = 5
ARCHITECTURE = {"name": "DualBranchFusionCNN", "n_classes": N_CLASSES, "spatial_shape": N_SPATIAL,
                "n_fbcca": N_FBCCA, "dropout": 0.3, "conv_bias": False}


class DualBranchFusionCNN(nn.Module):
  """Spatial-spectral CNN branch + FBCCA MLP branch, concatenated (48) and classified."""

  def __init__(self, n_classes: int = N_CLASSES, n_fbcca: int = N_FBCCA, dropout: float = 0.3):
    super().__init__()
    self.spatial = nn.Sequential(
      nn.Conv2d(1, 16, (4, 1), bias=False), nn.BatchNorm2d(16), nn.ELU(), nn.Dropout2d(dropout),
      nn.Conv2d(16, 32, (1, 3), bias=False), nn.BatchNorm2d(32), nn.ELU(), nn.Dropout2d(dropout),
      nn.Flatten(), nn.Linear(32 * 6, 32), nn.ELU(), nn.Dropout(dropout))
    self.fbcca = nn.Sequential(
      nn.Linear(n_fbcca, 16), nn.BatchNorm1d(16), nn.ELU(), nn.Dropout(dropout),
      nn.Linear(16, 16), nn.ELU())
    self.head = nn.Sequential(nn.Linear(48, 32), nn.ELU(), nn.Dropout(dropout), nn.Linear(32, n_classes))

  def forward(self, x_spatial: torch.Tensor, x_fbcca: torch.Tensor) -> torch.Tensor:
    return self.head(torch.cat([self.spatial(x_spatial), self.fbcca(x_fbcca)], dim=1))


def count_parameters(model: nn.Module) -> int:
  return sum(p.numel() for p in model.parameters() if p.requires_grad)


def resolve_device(device: str = "auto") -> torch.device:
  if device == "auto":
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
  return torch.device(device)


def prepare_spatial_spectral_tensors(X_psd: np.ndarray) -> np.ndarray:
  """`(n, 1, 4, 8)` float32 from `X_psd (n, 217)`: row r = channel, column c = bin (channel-major, R6)."""
  feats = extract_harmonic_features(X_psd)
  return feats.reshape(len(feats), 1, *N_SPATIAL).astype(np.float32)


def label_maps(y: np.ndarray) -> tuple:
  """`(classes, code->index)` with classes sorted (101..105 -> 0..4)."""
  classes = [int(c) for c in np.unique(y)]
  return classes, {c: i for i, c in enumerate(classes)}


def fit_scalers(X_spatial: np.ndarray, X_fbcca: np.ndarray) -> tuple:
  """Per-branch StandardScalers fitted on the given rows (the spatial one on the flattened 32 features)."""
  return StandardScaler().fit(X_spatial.reshape(len(X_spatial), -1)), StandardScaler().fit(X_fbcca)


def apply_scalers(scalers: tuple, X_spatial: np.ndarray, X_fbcca: np.ndarray) -> tuple:
  s_sp, s_fb = scalers
  xs = s_sp.transform(X_spatial.reshape(len(X_spatial), -1)).reshape(X_spatial.shape).astype(np.float32)
  return xs, s_fb.transform(X_fbcca).astype(np.float32)


def predict_proba(model: nn.Module, xs: np.ndarray, xf: np.ndarray, device: torch.device) -> np.ndarray:
  model.eval()
  with torch.no_grad():
    logits = model(torch.from_numpy(xs).to(device), torch.from_numpy(xf).to(device))
    return torch.softmax(logits, dim=1).cpu().numpy()


def train_model(xs: np.ndarray, xf: np.ndarray, yi: np.ndarray, seed: int, device: torch.device,
                epochs: int = EPOCHS, batch_size: int = BATCH_SIZE) -> DualBranchFusionCNN:
  """Train one model on already scaled arrays. `torch.manual_seed(seed)` precedes the model (PF-28)."""
  torch.manual_seed(seed)
  model = DualBranchFusionCNN().to(device)
  opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
  sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
  crit = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
  gen = torch.Generator().manual_seed(seed)
  ds = TensorDataset(torch.from_numpy(xs), torch.from_numpy(xf), torch.from_numpy(yi.astype(np.int64)))
  loader = DataLoader(ds, batch_size=batch_size, shuffle=True, generator=gen)
  for _ in range(epochs):
    model.train()
    for bs, bf, by in loader:
      if len(by) < 2:  # BatchNorm cannot train on a single row
        continue
      bs, bf, by = bs.to(device), bf.to(device), by.to(device)
      opt.zero_grad()
      crit(model(bs, bf), by).backward()
      opt.step()
    sched.step()
  return model


def train_and_eval_fusion_cnn_cv(X_spatial: np.ndarray, X_fbcca: np.ndarray, y: np.ndarray,
                                 epochs: int = EPOCHS, batch_size: int = BATCH_SIZE, device: str = "auto",
                                 seed: int = SEED, verbose: bool = False) -> dict:
  """Legacy leaky CV (R1/PF-01: `StratifiedKFold(5, shuffle, 42)` over windows) of the fusion CNN.

  `X_spatial (n,1,4,8)`, `X_fbcca (n,5)`, `y` condition codes. Scalers are fitted on each training
  fold only (R2). Returns dict with out-of-fold `pred` (codes), `proba` (classes sorted), `accuracy`
  (test, pooled), `train_accuracy` (mean over folds, eval mode on the training fold),
  `fold_test_acc`, `fold_train_acc`, `classes`, `cv`.
  """
  dev = resolve_device(device)
  classes, to_idx = label_maps(y)
  yi = np.array([to_idx[int(c)] for c in y])
  proba = np.zeros((len(y), len(classes)))
  fold_train, fold_test = [], []
  skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)  # legacy (R1, PF-01)
  for fold, (tr, te) in enumerate(skf.split(X_spatial.reshape(len(y), -1), yi)):
    scalers = fit_scalers(X_spatial[tr], X_fbcca[tr])
    xs_tr, xf_tr = apply_scalers(scalers, X_spatial[tr], X_fbcca[tr])
    xs_te, xf_te = apply_scalers(scalers, X_spatial[te], X_fbcca[te])
    model = train_model(xs_tr, xf_tr, yi[tr], seed + fold, dev, epochs, batch_size)
    proba[te] = predict_proba(model, xs_te, xf_te, dev)
    fold_test.append(float(np.mean(proba[te].argmax(1) == yi[te])))
    fold_train.append(float(np.mean(predict_proba(model, xs_tr, xf_tr, dev).argmax(1) == yi[tr])))
    if verbose:
      print(f"    fold {fold}: train acc {100 * fold_train[-1]:.2f}%  test acc {100 * fold_test[-1]:.2f}%")
  pred_idx = proba.argmax(1)
  return {"pred": np.array(classes)[pred_idx], "proba": proba, "accuracy": float(np.mean(pred_idx == yi)),
          "train_accuracy": float(np.mean(fold_train)), "fold_test_acc": fold_test, "fold_train_acc": fold_train,
          "classes": classes, "cv": "StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky)"}


def evaluate_temporal_smoothing(proba: np.ndarray, y: np.ndarray, classes: Optional[Sequence[int]] = None) -> float:
  """legacy (R8, PF-02): accuracy of the 2-window causal average over the array order, no trial reset."""
  classes = np.array(classes if classes is not None else np.unique(y))
  return float(np.mean(classes[smooth_probabilities_legacy(proba).argmax(1)] == np.asarray(y)))
