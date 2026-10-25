"""Shrinkage-LDA weight heatmaps of one subject (P04.5, legacy Era A).

Data: legacy stimulus windows of <processed-dir>/<S>/ (P02, OO session). Features: 32 harmonic-PSD
(POz, O1, Oz, O2 x bins 9, 11, 15, 17, 20, 22, 24, 30 Hz) + 5 FBCCA (legacy fs 250). Fit: full data
(export/XAI only; R2 exception), StandardScaler then Shrinkage-LDA (lsqr, auto); the weights are
coefficients on z-scored features, so magnitudes are comparable across features.

Figures (<out-dir>/figures/xai_heatmaps/):
- xai_spatial_spectral_weights.png: `coef_[:, :32]` reshaped to (5 classes, 4 channels, 8 bins);
- xai_fbcca_weights.png: `coef_[:, -5:]` (5 classes x 5 FBCCA targets).
For a subject other than the default S04, files are written with the suffix `_<S>`.
Each caption states data, features and fit. Weights are descriptive of the full-data fit, not of
generalisation.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from scripts.training.train_final_model import (  # noqa: E402
  DEFAULT_SUBJECT, fit_full_lda, load_subject_inputs)
from scripts.training.train_models import (  # noqa: E402
  CLASS_CODES, DEFAULT_CONFIG, KEEP_CHANNEL_NAMES, STIM_FREQS_HZ, arrays_exist, check_keep_channels, check_subject_keep_channels,
  harmonic_bin_indices, load_config)

N_SPATIAL = 32
N_FBCCA = 5
FIGURE_SPATIAL = "xai_spatial_spectral_weights.png"
FIGURE_FBCCA = "xai_fbcca_weights.png"


def weight_arrays(coef: np.ndarray) -> tuple:
  """Split `coef_ (5, 37)` into spatial-spectral `(5, 4, 8)` (channel-major: [k, r, c] = coef[k, 8 r + c])
  and FBCCA `(5, 5)` (`coef_[:, -5:]`)."""
  coef = np.asarray(coef)
  if coef.ndim != 2 or coef.shape[1] != N_SPATIAL + N_FBCCA:
    raise ValueError(f"coef_ must be (n_classes, 37), got {coef.shape}")
  return coef[:, :N_SPATIAL].reshape(coef.shape[0], 4, 8), coef[:, -N_FBCCA:]


def bin_labels_hz() -> list:
  return [f"{h:g}" for h in np.linspace(5, 35, 31)[harmonic_bin_indices()]]


def caption(subject: str, n: int) -> str:
  return (f"{subject}: legacy windows (OO session, n={n} stimulus windows); 32 harmonic-PSD + 5 FBCCA "
          "(fs 250 legacy); fit: full data, StandardScaler + Shrinkage-LDA (export/XAI only, R2 exception)")


def draw_spatial(axes, spatial: np.ndarray, vmax: float, classes=CLASS_CODES) -> object:
  """One heatmap per class on `axes`; returns the last image (for a colourbar)."""
  im = None
  for k, ax in enumerate(np.atleast_1d(axes)):
    im = ax.imshow(spatial[k], cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_title(f"{classes[k]} ({STIM_FREQS_HZ[k]:g} Hz)", fontsize=8)
    ax.set_xticks(range(8), bin_labels_hz(), fontsize=6, rotation=90)
    ax.set_yticks(range(4), KEEP_CHANNEL_NAMES, fontsize=7)
    ax.set_xlabel("frequency bin (Hz)", fontsize=7)
  return im


def draw_fbcca(ax, fb: np.ndarray, vmax: float, classes=CLASS_CODES) -> object:
  im = ax.imshow(fb, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
  ax.set_xticks(range(len(STIM_FREQS_HZ)), [f"{f:g}" for f in STIM_FREQS_HZ], fontsize=6, rotation=90)
  ax.set_yticks(range(len(classes)), [str(c) for c in classes], fontsize=7)
  ax.set_xlabel("FBCCA target (Hz)", fontsize=7)
  ax.set_ylabel("class", fontsize=7)
  return im


def plot_xai(spatial: np.ndarray, fb: np.ndarray, subject: str, n: int, fig_dir: Path,
             suffix: str = "") -> list:
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  fig_dir = Path(fig_dir)
  fig_dir.mkdir(parents=True, exist_ok=True)
  out = []
  vmax = float(np.abs(spatial).max()) or 1.0
  fig, axes = plt.subplots(1, 5, figsize=(14, 3.6), sharey=True)
  im = draw_spatial(axes, spatial, vmax)
  fig.colorbar(im, ax=axes, fraction=0.02, label="LDA coefficient (z-scored features)")
  fig.suptitle("Shrinkage-LDA spatial-spectral weights (class x channel x frequency)", fontsize=10)
  fig.text(0.01, 0.01, caption(subject, n), fontsize=6)
  p = fig_dir / f"{FIGURE_SPATIAL[:-4]}{suffix}.png"
  fig.savefig(p, dpi=150, bbox_inches="tight")
  plt.close(fig)
  out.append(p)
  vmax = float(np.abs(fb).max()) or 1.0
  fig, ax = plt.subplots(figsize=(5.2, 4.2))
  im = draw_fbcca(ax, fb, vmax)
  fig.colorbar(im, ax=ax, label="LDA coefficient (z-scored features)")
  ax.set_title("Shrinkage-LDA FBCCA weights", fontsize=10)
  fig.text(0.01, -0.02, caption(subject, n), fontsize=5, wrap=True)
  p = fig_dir / f"{FIGURE_FBCCA[:-4]}{suffix}.png"
  fig.savefig(p, dpi=150, bbox_inches="tight")
  plt.close(fig)
  out.append(p)
  return out


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"default: {DEFAULT_SUBJECT}")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None)
  p.add_argument("--out-dir", type=Path, default=None, help="default: <root>/outputs")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  check_keep_channels(cfg["channels"]["scalp"])
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  out = args.out_dir or ROOT / "outputs"
  if not arrays_exist(processed, args.subject):
    print(f"[x] {args.subject}: arrays missing in {processed}/{args.subject}")
    return 1
  try:
    check_subject_keep_channels(processed, args.subject)
  except ValueError as exc:
    print(f"[x] {exc}")
    return 1
  _, _, y, hybrid = load_subject_inputs(processed, args.subject)
  _, lda = fit_full_lda(hybrid, y)
  spatial, fb = weight_arrays(lda.coef_)
  print(caption(args.subject, len(y)))
  suffix = "" if args.subject == DEFAULT_SUBJECT else f"_{args.subject}"
  for p in plot_xai(spatial, fb, args.subject, len(y), Path(out) / "figures" / "xai_heatmaps", suffix):
    print(f"Saved: {p}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
