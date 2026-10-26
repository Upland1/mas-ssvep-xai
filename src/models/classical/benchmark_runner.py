"""Shared plumbing of the P05 benchmark scripts: config, subject data, labels, reports, figures."""

import re
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import yaml
from sklearn.metrics import classification_report, confusion_matrix

from src.features.ssvep.fbcca_extraction import TARGET_FREQS
from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, MASK_LABEL
from src.io.channels import subject_channel_names
from src.models.classical.feature_spaces import build_feature_blocks
from src.models.classical.legacy_eval import SEED, cv_label, smooth_label
from src.preprocessing.dataset.cv_utils import (
  CV_CHOICES, LEGACY_TRIAL_LENGTHS, SMOOTHING_CHOICES, build_trial_ids, format_block_report, output_dir,
  trial_block_report)
from src.preprocessing.dataset.legacy_windows import CLASS_CODES, arrays_exist, load_stimulus_windows

DEFAULT_SUBJECT = "S03"   # acceptance subject of P05 (R-3)
CLASS_NAMES = [f"{c} ({f:g} Hz)" for c, f in zip(CLASS_CODES, (24.0, 20.0, 15.0, 10.91, 8.57))]


SUBJECT_PATTERN = re.compile(r"^S\d+$")


def discover_subjects(processed_dir: Path) -> list:
  """Folders of `processed_dir` matching ^S\\d+$ that hold the three arrays, numeric order."""
  found = [p.name for p in Path(processed_dir).iterdir()
           if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name) and arrays_exist(processed_dir, p.name)]
  return sorted(found, key=lambda s: int(s[1:]))


def load_config(path: Path) -> dict:
  with open(path) as f:
    return yaml.safe_load(f) or {}


def add_protocol_args(parser) -> None:
  """`--cv {grouped,legacy}` (default grouped, R1) and `--smoothing {trial,mod5}` (default mod5, R8 legacy-folder clause); P11."""
  parser.add_argument("--cv", choices=CV_CHOICES, default="grouped",
                      help="grouped = StratifiedGroupKFold over trial ids (R1, default); legacy = P05-P10 window-level "
                           "StratifiedKFold (leaky, outputs under <reports-dir>/legacy_leaky/)")
  parser.add_argument("--smoothing", choices=SMOOTHING_CHOICES, default="mod5",
                      help="2.0 s rule: mod5 = i%%5 of the clean array (R8 legacy-folder clause, default, reported); "
                           "trial = reset at each trial id (PF-02 diagnostic on legacy folders)")


def protocol_labels(cv: str, smoothing: str) -> tuple:
  """`(cv label, smoothing label)` for headers and report titles."""
  return cv_label(cv), smooth_label(smoothing, cv)


def trial_ids_header(b: dict) -> str:
  """Meta line naming the trial-id source and whether the ids are approximate (PF-03)."""
  return (f"trial ids: contiguous same-label blocks of the pre-gate labels, indexed by the valid mask; "
          f"trial_ids_approximate={'yes' if b['trial_ids_approximate'] else 'no'}; {b['n_trials']} trials in "
          f"{b['n_clean']} clean windows")


def print_trial_report(subject: str, b: dict) -> None:
  """Block lengths per condition and the approximate-id verdict of one subject (task 2)."""
  print(f"Trial blocks of {subject} (stimulus windows before the quality gate):")
  print(format_block_report(b["trial_block_report"]))


def prepare_subject(processed_dir: Path, subject: str, scalp: Optional[Sequence[str]] = None,
                    fs: float = LEGACY_FS_HZ, thresholds: Optional[dict] = None,
                    fbcca_channels: Optional[Sequence[str]] = None,
                    channel_fail_fraction: float = CHANNEL_FAIL_FRACTION,
                    verbose: bool = False) -> dict:
  """Stimulus windows of a legacy subject folder, gated once (two-tier, P07), with every feature block.

  Channel names: `subject_channel_names` (channels.json, else `scalp`, else by count). Returns the dict of
  `build_feature_blocks` plus `channel_names` (input), `n_stimulus`, `n_clean`, `n_rejected`.
  Raises FileNotFoundError when the arrays are missing.
  """
  if not arrays_exist(processed_dir, subject):
    raise FileNotFoundError(f"arrays missing in {Path(processed_dir) / subject}")
  _, X_time, y = load_stimulus_windows(processed_dir, subject)
  # trial ids on the PRE-gate labels (201/202 rows included in the walk), then the stimulus selection (PF-03)
  y_all = np.load(Path(processed_dir) / subject / "y_labels.npy")
  ids_all = build_trial_ids(y_all, LEGACY_TRIAL_LENGTHS, warn=False)
  ids_stim = ids_all[np.isin(y_all, CLASS_CODES)]
  names = subject_channel_names(processed_dir, subject, X_time.shape[1], scalp)
  blocks = build_feature_blocks(X_time, y, names, fs, thresholds, fbcca_channels,
                                channel_fail_fraction, verbose)
  blocks["channel_names"] = names
  rep = trial_block_report(y, ids_stim, LEGACY_TRIAL_LENGTHS)
  blocks["trial_ids"] = ids_stim[np.asarray(blocks["mask"]).astype(bool)]
  blocks["trial_block_report"] = rep
  blocks["trial_ids_approximate"] = rep["approximate"]
  blocks["n_trials"] = int(len(np.unique(blocks["trial_ids"])))
  blocks["n_stimulus"] = int(len(y))
  blocks["n_clean"] = int(len(blocks["y"]))
  blocks["n_rejected"] = blocks["n_stimulus"] - blocks["n_clean"]
  return blocks


def channel_summary(blocks: dict) -> str:
  """One line: channels kept / dropped of a prepared subject (R9)."""
  return (f"channels kept {len(blocks['channels_kept'])} [{', '.join(blocks['channels_kept'])}]; "
          f"dropped {len(blocks['channels_dropped'])} [{', '.join(blocks['channels_dropped']) or 'none'}]")


def legacy_header_lines(fs: float, thresholds: dict, seed: int, cv_label: str, smooth_label: str,
                        fbcca_channels: Optional[Sequence[str]] = None,
                        channel_fail_fraction: float = CHANNEL_FAIL_FRACTION) -> list:
  """Protocol lines of a legacy benchmark; `fbcca_channels` (names, `blocks["fbcca_channels"]`) adds a line naming the FBCCA input."""
  th = thresholds
  lines = [
    f"cv={cv_label}; seed={seed}",
    f"smoothing: {smooth_label}",
    f"features: legacy fs={fs:g} Hz (PF-04), per-window sub-band filtering (R3/PF-14); scaler and CSP fitted "
    f"inside each training fold (R2/PF-11)",
    f"quality gate (R5 per-script, {MASK_LABEL}, one decision for every block, PF-10): vpp "
    f"[{th['vpp_min']:g}, {th['vpp_max']:g}] uV, std [{th['std_min']:g}, {th['std_max']:g}] uV, "
    f"channel dropped if it fails in > {channel_fail_fraction:.0%} of the windows",
  ]
  if fbcca_channels is not None:
    lines.append(f"FBCCA channels ({len(fbcca_channels)}): {', '.join(fbcca_channels)}")
  return lines


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


__all__ = ["DEFAULT_SUBJECT", "TARGET_FREQS", "load_config", "prepare_subject", "subject_channel_names", "channel_summary", "discover_subjects", "legacy_header_lines", "add_protocol_args", "protocol_labels", "trial_ids_header", "print_trial_report", "output_dir", "SEED",
           "save_classification_report", "plot_confusion", "figure_paths", "CLASS_NAMES"]
