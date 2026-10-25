"""Shared plumbing of the P05 benchmark scripts: config, subject data, labels, reports, figures."""

from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import yaml
from sklearn.metrics import classification_report, confusion_matrix

from src.features.ssvep.fbcca_extraction import TARGET_FREQS
from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.models.classical.feature_spaces import build_feature_blocks
from src.preprocessing.dataset.legacy_windows import CLASS_CODES, arrays_exist, load_stimulus_windows

DEFAULT_SUBJECT = "S03"   # acceptance subject of P05 (R-3)
CLASS_NAMES = [f"{c} ({f:g} Hz)" for c, f in zip(CLASS_CODES, (24.0, 20.0, 15.0, 10.91, 8.57))]


def load_config(path: Path) -> dict:
  with open(path) as f:
    return yaml.safe_load(f) or {}


def prepare_subject(processed_dir: Path, subject: str, scalp: Sequence[str],
                    fs: float = LEGACY_FS_HZ, thresholds: Optional[dict] = None) -> dict:
  """Stimulus windows of a legacy subject folder, gated once, with every feature block.

  Returns the dict of `build_feature_blocks` plus `n_stimulus`, `n_clean`, `n_rejected`.
  Raises FileNotFoundError when the arrays are missing.
  """
  if not arrays_exist(processed_dir, subject):
    raise FileNotFoundError(f"arrays missing in {Path(processed_dir) / subject}")
  _, X_time, y = load_stimulus_windows(processed_dir, subject)
  if X_time.shape[1] != len(scalp):
    raise ValueError(f"{subject}: {X_time.shape[1]} channels in the arrays, {len(scalp)} names in the config")
  blocks = build_feature_blocks(X_time, y, scalp, fs, thresholds)
  blocks["n_stimulus"] = int(len(y))
  blocks["n_clean"] = int(len(blocks["y"]))
  blocks["n_rejected"] = blocks["n_stimulus"] - blocks["n_clean"]
  return blocks


def legacy_header_lines(fs: float, thresholds: dict, seed: int, cv_label: str, smooth_label: str) -> list:
  th = thresholds
  return [
    f"cv={cv_label}; seed={seed}",
    f"smoothing: {smooth_label}",
    f"features: legacy fs={fs:g} Hz (PF-04), per-window sub-band filtering (R3/PF-14); scaler and CSP fitted "
    f"inside each training fold (R2/PF-11)",
    f"window mask (R5 per-script gate, one mask for every block, PF-10): vpp [{th['vpp_min']:g}, "
    f"{th['vpp_max']:g}] uV, std [{th['std_min']:g}, {th['std_max']:g}] uV",
  ]


def save_classification_report(y: np.ndarray, pred: np.ndarray, path: Path, title: str) -> str:
  """Per-class precision/recall/F1 text (printed by the caller) saved to `path`; returns the text."""
  labels = list(CLASS_CODES)
  rep = classification_report(y, pred, labels=labels, target_names=CLASS_NAMES, digits=4, zero_division=0)
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(f"{title}\n\n{rep}\n")
  return rep


def plot_confusion(y: np.ndarray, pred: np.ndarray, title: str, paths: Sequence[Path]) -> list:
  """Row-normalized confusion matrix with counts, saved to every path (matplotlib Agg)."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  labels = list(CLASS_CODES)
  cm = confusion_matrix(y, pred, labels=labels)
  cmn = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
  fig, ax = plt.subplots(figsize=(5.6, 4.8))
  im = ax.imshow(cmn, vmin=0, vmax=1, cmap="Blues")
  for i in range(len(labels)):
    for j in range(len(labels)):
      ax.text(j, i, f"{cm[i, j]}", ha="center", va="center",
              color="white" if cmn[i, j] > 0.5 else "black", fontsize=9)
  ticks = [f"{c}\n{f:g}" for c, f in zip(labels, (24.0, 20.0, 15.0, 10.91, 8.57))]
  ax.set_xticks(range(5), ticks, fontsize=8)
  ax.set_yticks(range(5), ticks, fontsize=8)
  ax.set_xlabel("predicted (code, Hz)")
  ax.set_ylabel("true (code, Hz)")
  ax.set_title(title, fontsize=8)
  fig.colorbar(im, ax=ax, fraction=0.046, label="row fraction")
  fig.tight_layout()
  written = []
  for p in paths:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150)
    written.append(Path(p))
  plt.close(fig)
  return written


def figure_paths(fig_dir: Path, stem: str, subject: str, default_subject: str = DEFAULT_SUBJECT) -> list:
  """`<fig_dir>/<stem>_<S>.png`; the default subject also at the roadmap path `<fig_dir>/<stem>.png`."""
  paths = [Path(fig_dir) / f"{stem}_{subject}.png"]
  if subject == default_subject:
    paths.append(Path(fig_dir) / f"{stem}.png")
  return paths


__all__ = ["DEFAULT_SUBJECT", "TARGET_FREQS", "load_config", "prepare_subject", "legacy_header_lines",
           "save_classification_report", "plot_confusion", "figure_paths", "CLASS_NAMES"]
