"""Compact-CNN for SSVEP on raw windows (P09.1, legacy Era A).

After Waytowich et al. 2018 ("Compact convolutional neural networks for classification of asynchronous
steady-state visual evoked potentials"), faithful in spirit: spatial Conv2d(1 -> F1, (C, 1)) + BN, then temporal
Conv2d(F1 -> F2, (1, K), padding K // 2) + BN + ELU + Dropout, Flatten, Linear. Both convolutions have
`bias=False` (each is followed by BatchNorm; R-8: 56,021 parameters at 7 x 256, blocker B004).

Temporal kernel: `K = clamp(round(fs / lowest_freq_hz), 4, n_samples)`, one cycle of the slowest target
(8.5714 Hz). The default `fs=250.0` is the legacy label (PF-04: Era A assumes 250 Hz although the recordings
are 256 Hz): K = 29 and 56,021 parameters; with fs 256, K = 30 and the head grows by one time step.
This is the spatial -> temporal `compact_cnn`, not the P20 `compact` EEGNet variant (PF-31).

Input: `(B, C, T)` or `(B, 1, C, T)` (R6: axis 2 of the 4-D form is channels, axis 3 is time).
"""

import torch
from torch import nn

from src.models.cnn.eegnet import N_CLASSES, count_parameters  # noqa: F401  (count_parameters re-exported)

LEGACY_FS_HZ = 250.0  # legacy label (PF-04)
LOWEST_FREQ_HZ = 8.5714


def temporal_kernel_length(fs: float, lowest_freq_hz: float, n_samples: int) -> int:
  """One cycle of the slowest target in samples, clamped to [4, n_samples]."""
  return int(min(max(round(fs / lowest_freq_hz), 4), n_samples))


class CompactCNN(nn.Module):
  """Spatial conv -> temporal conv -> ELU -> dropout -> linear head (head sized by a dummy forward)."""

  def __init__(self, n_classes: int = N_CLASSES, n_channels: int = 7, n_samples: int = 256,
               fs: float = LEGACY_FS_HZ, lowest_freq_hz: float = LOWEST_FREQ_HZ, F1: int = 16, F2: int = 32,
               dropout_rate: float = 0.5):
    super().__init__()
    self.n_channels, self.n_samples = n_channels, n_samples
    self.kernel_length = K = temporal_kernel_length(fs, lowest_freq_hz, n_samples)
    self.spatial = nn.Conv2d(1, F1, (n_channels, 1), bias=False)
    self.bn1 = nn.BatchNorm2d(F1)
    self.temporal = nn.Conv2d(F1, F2, (1, K), padding=(0, K // 2), bias=False)
    self.bn2 = nn.BatchNorm2d(F2)
    self.tail = nn.Sequential(nn.ELU(), nn.Dropout(dropout_rate))
    with torch.no_grad():
      was = self.training
      self.eval()
      n_flat = self.features(torch.zeros(1, 1, n_channels, n_samples)).shape[1]
      self.train(was)
    self.head = nn.Linear(n_flat, n_classes)

  def features(self, x: torch.Tensor) -> torch.Tensor:
    x = self.bn1(self.spatial(x))
    return self.tail(self.bn2(self.temporal(x))).flatten(1)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    if x.dim() == 3:
      x = x.unsqueeze(1)
    if x.dim() != 4 or x.shape[1] != 1 or x.shape[2] != self.n_channels:
      raise ValueError(f"expected (B, {self.n_channels}, T) or (B, 1, {self.n_channels}, T), got {tuple(x.shape)}")
    return self.head(self.features(x))
