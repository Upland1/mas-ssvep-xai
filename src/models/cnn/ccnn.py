"""Complex-spectrum CNN (CCNN) for SSVEP detection on raw windows (P20.3).

Input `(B, C, T)` or `(B, 1, C, T)` (R6: axis 1 of the 3-D form is channels, last axis is time). The window is
zero-padded to `nfft = max(T, round(fs / resolution_hz))` samples, transformed with `rfft`, the bins with
`f_min <= f <= f_max` are kept and the real and imaginary parts are stacked as two input maps divided by `T`:
`(B, 2, C, n_bins)`. Then spatial Conv2d (C, 1) -> BN -> ReLU -> Dropout, spectral Conv2d (1, `spectral_kernel`) ->
BN -> ReLU -> Dropout, Flatten, Linear. Both convolutions have `bias=False` (each is followed by BatchNorm; B004).

Parameters (bias-free convs): 2*F*C + 2F (BN1) + F*F*K + 2F (BN2) + F*(n_bins-K+1)*n_classes + n_classes,
with F = n_filters.
"""

import numpy as np
import torch
from torch import nn


class CCNN(nn.Module):
  """Complex-spectrum CNN: zero-padded rFFT features -> spatial conv -> spectral conv -> linear."""

  def __init__(self, n_classes: int, n_channels: int, n_samples: int, fs: float = 256.0, f_min: float = 3.0,
               f_max: float = 50.0, resolution_hz: float = 0.25, n_filters: int = None, spectral_kernel: int = 10,
               dropout: float = 0.25):
    super().__init__()
    self.n_channels, self.n_samples, self.fs = int(n_channels), int(n_samples), float(fs)
    self.nfft = max(self.n_samples, int(round(self.fs / resolution_hz)))
    freqs = np.fft.rfftfreq(self.nfft, 1.0 / self.fs)
    idx = np.flatnonzero((freqs >= f_min) & (freqs <= f_max))
    if len(idx) < spectral_kernel:
      raise ValueError(f"only {len(idx)} bins in [{f_min}, {f_max}] Hz, need >= spectral_kernel={spectral_kernel}")
    self.register_buffer("bin_idx", torch.as_tensor(idx, dtype=torch.long), persistent=False)
    self.bins_hz = freqs[idx]
    self.n_bins = len(idx)
    F = int(n_filters) if n_filters else 2 * self.n_channels
    self.spatial = nn.Sequential(nn.Conv2d(2, F, (self.n_channels, 1), bias=False), nn.BatchNorm2d(F), nn.ReLU(),
                                 nn.Dropout(dropout))
    self.spectral = nn.Sequential(nn.Conv2d(F, F, (1, spectral_kernel), bias=False), nn.BatchNorm2d(F), nn.ReLU(),
                                  nn.Dropout(dropout))
    self.head = nn.Linear(F * (self.n_bins - spectral_kernel + 1), n_classes)

  def spectrum(self, x: torch.Tensor) -> torch.Tensor:
    """`(B, 2, C, n_bins)`: [real, imag] of the zero-padded rFFT in the kept band, divided by T."""
    z = torch.fft.rfft(x, n=self.nfft, dim=-1)[..., self.bin_idx] / self.n_samples
    return torch.stack([z.real, z.imag], dim=1)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    if x.dim() == 4 and x.shape[1] == 1:
      x = x[:, 0]
    if x.dim() != 3 or x.shape[1] != self.n_channels or x.shape[2] != self.n_samples:
      raise ValueError(f"expected (B, {self.n_channels}, {self.n_samples}), got {tuple(x.shape)}")
    return self.head(self.spectral(self.spatial(self.spectrum(x))).flatten(1))
