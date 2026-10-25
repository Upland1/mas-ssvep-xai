"""Synthetic legacy subject folder for the P05 tests (no recordings; fixed seeds)."""

from pathlib import Path

import numpy as np
from scipy.signal import periodogram

FS = 250.0
TARGETS = (24.0, 20.0, 15.0, 10.9091, 8.5714)
SCALP = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]


def make_windows(n_trials: int = 8, snr: float = 1.0, seed: int = 0, n_ch: int = 7, T: int = 256) -> tuple:
  """`(X (n, C, T), y)` in condition order (5 windows per trial): class k = sinusoid at TARGETS[k]
  with a fixed per-class spatial pattern on top of noise; amplitudes keep every window inside the P05 gate."""
  rng = np.random.default_rng(seed)
  t = np.arange(T) / FS
  pats = rng.uniform(0.6, 1.4, size=(5, n_ch)) * rng.choice([-1, 1], size=(5, n_ch))
  X, y = [], []
  for k in range(5):
    for _ in range(n_trials * 5):
      s = np.sin(2 * np.pi * TARGETS[k] * t + rng.uniform(0, 2 * np.pi))
      X.append(8.0 * snr * pats[k][:, None] * s[None, :] + rng.normal(0, 6.0, (n_ch, T)))
      y.append(101 + k)
  return np.stack(X), np.array(y)


def write_subject(root: Path, subject: str = "S03", **kw) -> Path:
  """Legacy folder `<root>/<subject>/{X_psd_features,X_time_windows,y_labels}.npy` with 201 rows too."""
  X, y = make_windows(**kw)
  rng = np.random.default_rng(99)
  rest = rng.normal(0, 6.0, (20, X.shape[1], X.shape[2]))
  Xall = np.concatenate([rest, X])
  yall = np.concatenate([np.full(20, 201), y])
  f, p = periodogram(Xall, fs=256.0, axis=-1)
  sel = (f >= 5) & (f <= 35)
  d = Path(root) / subject
  d.mkdir(parents=True, exist_ok=True)
  np.save(d / "X_time_windows.npy", Xall)
  np.save(d / "y_labels.npy", yall)
  np.save(d / "X_psd_features.npy", p[..., sel].reshape(len(Xall), -1))
  return d
