"""EEGNet for SSVEP on raw windows (P08.1, legacy Era A).

Architecture after Lawhern et al. 2018 (EEGNet-8,2), sized for 7 channels x 256 samples and 5 classes:
block 1 temporal conv (1, K) -> BN -> depthwise spatial conv (C, 1) with max-norm 1.0 -> BN -> ELU ->
AvgPool(1, 4) -> Dropout; block 2 depthwise (1, 16) + pointwise 1x1 -> BN -> ELU -> AvgPool(1, 8) ->
Dropout; Linear head sized by a dummy forward pass. Every convolution has `bias=False` (R-8: 2,349
parameters, blocker B004 for the bias terms; each conv is followed by BatchNorm).

Max-norm (documented choice): `apply_max_norm()` renorms every depthwise spatial filter (one per output
channel, L2 norm over the channel axis) to <= `max_norm` and is called by the trainer after each optimizer
step, as in the original EEGNet (Keras `max_norm` constraint). Other layers are unconstrained.

Input: `(B, C, T)` or `(B, 1, C, T)` (R6: axis 2 of the 4-D form is channels, axis 3 is time).
"""

import torch
from torch import nn

N_CLASSES = 5


class EEGNetSSVEP(nn.Module):
  """EEGNet: temporal conv -> spatial depthwise (max-norm) -> separable conv -> linear head."""

  def __init__(self, n_classes: int = N_CLASSES, n_channels: int = 7, n_samples: int = 256,
               F1: int = 8, D: int = 2, F2: int = 16, kernel_length: int = 125,
               dropout_rate: float = 0.25, max_norm: float = 1.0):
    super().__init__()
    self.n_channels, self.n_samples, self.max_norm = n_channels, n_samples, max_norm
    self.temporal = nn.Conv2d(1, F1, (1, kernel_length), padding=(0, kernel_length // 2), bias=False)
    self.bn1 = nn.BatchNorm2d(F1)
    self.spatial = nn.Conv2d(F1, F1 * D, (n_channels, 1), groups=F1, bias=False)
    self.bn2 = nn.BatchNorm2d(F1 * D)
    self.depthwise2 = nn.Conv2d(F1 * D, F1 * D, (1, 16), padding=(0, 8), groups=F1 * D, bias=False)
    self.pointwise = nn.Conv2d(F1 * D, F2, (1, 1), bias=False)
    self.bn3 = nn.BatchNorm2d(F2)
    self.block1_tail = nn.Sequential(nn.ELU(), nn.AvgPool2d((1, 4)), nn.Dropout(dropout_rate))
    self.block2_tail = nn.Sequential(nn.ELU(), nn.AvgPool2d((1, 8)), nn.Dropout(dropout_rate))
    with torch.no_grad():  # head size from a dummy forward (eval: BN statistics untouched)
      was = self.training
      self.eval()
      n_flat = self.features(torch.zeros(1, 1, n_channels, n_samples)).shape[1]
      self.train(was)
    self.head = nn.Linear(n_flat, n_classes)

  def features(self, x: torch.Tensor) -> torch.Tensor:
    x = self.block1_tail(self.bn2(self.spatial(self.bn1(self.temporal(x)))))
    x = self.block2_tail(self.bn3(self.pointwise(self.depthwise2(x))))
    return x.flatten(1)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    if x.dim() == 3:
      x = x.unsqueeze(1)
    if x.dim() != 4 or x.shape[1] != 1 or x.shape[2] != self.n_channels:
      raise ValueError(f"expected (B, {self.n_channels}, T) or (B, 1, {self.n_channels}, T), got {tuple(x.shape)}")
    return self.head(self.features(x))

  @torch.no_grad()
  def apply_max_norm(self) -> None:
    """Rescale every depthwise spatial filter with L2 norm > `max_norm` to `max_norm` (others unchanged)."""
    w = self.spatial.weight  # (F1*D, 1, C, 1)
    norms = w.flatten(1).norm(dim=1).clamp_min(1e-12).view(-1, 1, 1, 1)
    w.mul_(torch.clamp(norms, max=self.max_norm) / norms)


def count_parameters(model: nn.Module) -> int:
  return sum(p.numel() for p in model.parameters() if p.requires_grad)
