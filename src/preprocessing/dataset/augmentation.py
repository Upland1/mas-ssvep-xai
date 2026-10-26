"""Simple EEG augmentation for raw SSVEP windows (P10.1), applied to the training fold only (PF-29).

Four operations on a window `(C, T)`: Gaussian noise proportional to each channel's own std, one amplitude factor
per window, circular time shift, and intra-class mixup (the partner always has the anchor's label: blending two
classes would mix two stimulation frequencies that match neither label). `SSVEPAugmentedDataset` applies them on
the fly in the order mixup -> scale -> shift -> noise, each with probability 0.5, using its own
`numpy.random.Generator(seed)`; it never touches the torch RNG, so the model initialisation of an OFF and an ON arm
seeded identically stays identical (PF-28).

Windows are expected z-scored per window and channel (the network's input space), so the noise std equals
`std_frac` there. Statistics are per window (R2): nothing is estimated across windows.
"""

from typing import Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

OP_ORDER = ("mixup", "scale", "shift", "noise")


def _rng(rng: Optional[np.random.Generator]) -> np.random.Generator:
  return rng if rng is not None else np.random.default_rng()


def add_gaussian_noise(window: np.ndarray, std_frac: float = 0.05, rng: Optional[np.random.Generator] = None) -> np.ndarray:
  """`window + N(0, (std_frac * std_c)^2)` per channel c (std over the window's own time axis)."""
  w = np.asarray(window)
  sd = w.std(axis=-1, keepdims=True)
  return w + _rng(rng).standard_normal(w.shape) * std_frac * sd


def scale_amplitude(window: np.ndarray, scale_range: Tuple[float, float] = (0.9, 1.1),
                    rng: Optional[np.random.Generator] = None) -> np.ndarray:
  """Multiply the whole window by one factor drawn from U(scale_range)."""
  return np.asarray(window) * _rng(rng).uniform(scale_range[0], scale_range[1])


def time_shift(window: np.ndarray, max_shift_frac: float = 0.1, rng: Optional[np.random.Generator] = None) -> np.ndarray:
  """Circular roll along time by an integer in [-s, s], s = floor(max_shift_frac * T)."""
  w = np.asarray(window)
  s = int(max_shift_frac * w.shape[-1])
  return np.roll(w, int(_rng(rng).integers(-s, s + 1)), axis=-1)


def mixup_intra_class(a: np.ndarray, b: np.ndarray, alpha: float = 0.4, rng: Optional[np.random.Generator] = None) -> np.ndarray:
  """`lam * a + (1 - lam) * b`, lam ~ Beta(alpha, alpha) folded to `max(lam, 1 - lam)` so the anchor `a` dominates.

  The caller guarantees that `a` and `b` belong to the same class (the dataset draws `b` from the anchor's class)."""
  lam = _rng(rng).beta(alpha, alpha)
  lam = max(lam, 1.0 - lam)
  return lam * np.asarray(a) + (1.0 - lam) * np.asarray(b)


class SSVEPAugmentedDataset(Dataset):
  """Training-fold dataset augmenting each sample on the fly; returns float32 `(C, T)` and long label tensors.

  `X (n, C, T)` and `y (n,)` are the training fold only. Each operation is applied with its own probability, in the
  order mixup -> scale -> shift -> noise. A class -> indices lookup is precomputed for the mixup partner. All
  randomness comes from `numpy.random.default_rng(seed)`; with a seeded, single-process DataLoader the stream is
  deterministic."""

  def __init__(self, X: np.ndarray, y: np.ndarray, p_noise: float = 0.5, p_scale: float = 0.5, p_shift: float = 0.5,
               p_mixup: float = 0.5, seed: int = 42):
    self.X = np.asarray(X, dtype=np.float32)
    self.y = np.asarray(y).astype(np.int64)
    self.p = {"mixup": p_mixup, "scale": p_scale, "shift": p_shift, "noise": p_noise}
    self.rng = np.random.default_rng(seed)
    self.class_idx = {int(c): np.flatnonzero(self.y == c) for c in np.unique(self.y)}

  def __len__(self) -> int:
    return len(self.y)

  def augment(self, i: int) -> np.ndarray:
    x = self.X[i].astype(np.float64)
    for op in OP_ORDER:
      if self.rng.random() >= self.p[op]:
        continue
      if op == "mixup":
        pool = self.class_idx[int(self.y[i])]
        x = mixup_intra_class(x, self.X[pool[self.rng.integers(len(pool))]], rng=self.rng)
      elif op == "scale":
        x = scale_amplitude(x, rng=self.rng)
      elif op == "shift":
        x = time_shift(x, rng=self.rng)
      else:
        x = add_gaussian_noise(x, rng=self.rng)
    return x

  def __getitem__(self, i: int):
    return torch.from_numpy(self.augment(int(i)).astype(np.float32)), torch.tensor(int(self.y[i]), dtype=torch.long)
