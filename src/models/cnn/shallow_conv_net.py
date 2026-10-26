"""ShallowConvNet for SSVEP on raw windows (P09.2, legacy Era A).

After Schirrmeister et al. 2017 (shallow ConvNet): temporal Conv2d(1 -> F1, (1, 25)) -> spatial Conv2d(F1 -> F1,
(C, 1)) -> BN -> square -> AvgPool((1, 75), stride (1, 15)) -> log(clamp(x, 1e-6)) -> Dropout -> Linear. Both
convolutions have `bias=False` (the spatial conv is followed by BatchNorm and the temporal one is linear in it;
R-8: 14,485 parameters at 7 x 256, blocker B004). At 256 samples the pooled length is 11.

The temporal kernel is clamped to the window and the pooling kernel to the length after the temporal conv
(stride to the pooling kernel), so short windows (e.g. 128 samples) run. The log is clamped at `LOG_EPS` = 1e-6
so zero or negative pooled power stays finite.

Input: `(B, C, T)` or `(B, 1, C, T)` (R6: axis 2 of the 4-D form is channels, axis 3 is time).
"""

import torch
from torch import nn

from src.models.cnn.eegnet import N_CLASSES, count_parameters  # noqa: F401  (count_parameters re-exported)

LOG_EPS = 1e-6


class ShallowConvNet(nn.Module):
  """Temporal conv -> spatial conv -> BN -> square -> mean pool -> log -> dropout -> linear."""

  def __init__(self, n_classes: int = N_CLASSES, n_channels: int = 7, n_samples: int = 256, F1: int = 40,
               temporal_kernel_length: int = 25, pool_kernel_length: int = 75, pool_stride: int = 15,
               dropout_rate: float = 0.5):
    super().__init__()
    self.n_channels, self.n_samples = n_channels, n_samples
    self.kernel_length = k = max(1, min(temporal_kernel_length, n_samples))
    n_conv = n_samples - k + 1
    self.pool_kernel = pk = max(1, min(pool_kernel_length, n_conv))
    self.pool_stride = max(1, min(pool_stride, pk))
    self.temporal = nn.Conv2d(1, F1, (1, k), bias=False)
    self.spatial = nn.Conv2d(F1, F1, (n_channels, 1), bias=False)
    self.bn = nn.BatchNorm2d(F1)
    self.pool = nn.AvgPool2d((1, pk), stride=(1, self.pool_stride))
    self.drop = nn.Dropout(dropout_rate)
    with torch.no_grad():
      was = self.training
      self.eval()
      n_flat = self.features(torch.zeros(1, 1, n_channels, n_samples)).shape[1]
      self.train(was)
    self.head = nn.Linear(n_flat, n_classes)

  def features(self, x: torch.Tensor) -> torch.Tensor:
    x = self.bn(self.spatial(self.temporal(x)))
    x = torch.log(torch.clamp(self.pool(x * x), min=LOG_EPS))
    return self.drop(x).flatten(1)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    if x.dim() == 3:
      x = x.unsqueeze(1)
    if x.dim() != 4 or x.shape[1] != 1 or x.shape[2] != self.n_channels:
      raise ValueError(f"expected (B, {self.n_channels}, T) or (B, 1, {self.n_channels}, T), got {tuple(x.shape)}")
    return self.head(self.features(x))
