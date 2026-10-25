"""Side-by-side LDA weights of two subjects from their exported joblib files (P04.5, legacy Era A).

Default S01 (low SNR) vs S04 (high SNR). Reads <models-dir>/<S>_shrinkage_lda.joblib written by
`scripts.training.train_final_model` (fit: full data, export/XAI only; R2 exception), so it needs
no recordings. Rows: subjects; columns: the five classes' (channel x frequency) weights and the
(class x FBCCA target) weights. Colour scale shared by all panels, so magnitudes compare.
The caption states data (legacy stimulus windows, OO session), features (32 harmonic-PSD + 5 FBCCA,
fs 250 legacy) and fit (full data, StandardScaler + Shrinkage-LDA).

Output: <out-dir>/figures/xai_heatmaps/compare_<A>_<B>.png (default compare_S01_S04.png).
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

import joblib  # noqa: E402
import numpy as np  # noqa: E402

from scripts.xai.run_xai import draw_fbcca, draw_spatial, weight_arrays  # noqa: E402


def load_weights(models_dir: Path, subject: str) -> tuple:
  """`(spatial (5, 4, 8), fbcca (5, 5), n_windows)` from the exported joblib of `subject`."""
  path = Path(models_dir) / f"{subject}_shrinkage_lda.joblib"
  bundle = joblib.load(path)
  if bundle.get("subject_id") != subject:
    raise ValueError(f"{path} holds subject {bundle.get('subject_id')}, expected {subject}")
  spatial, fb = weight_arrays(bundle["model"].coef_)
  return spatial, fb, int(bundle.get("n_windows", 0))


def plot_comparison(subjects: Sequence[str], weights: dict, out_path: Path) -> Path:
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  vmax = max(float(np.abs(w[0]).max()) for w in weights.values()) or 1.0      # spatial panels
  vmax_fb = max(float(np.abs(w[1]).max()) for w in weights.values()) or 1.0   # FBCCA panels (own scale)
  fig, axes = plt.subplots(len(subjects), 6, figsize=(17, 3.4 * len(subjects)),
                           gridspec_kw={"width_ratios": [1, 1, 1, 1, 1, 1.1]})
  axes = np.atleast_2d(axes)
  im = None
  for r, s in enumerate(subjects):
    spatial, fb, n = weights[s]
    im = draw_spatial(axes[r, :5], spatial, vmax)
    imf = draw_fbcca(axes[r, 5], fb, vmax_fb)
    axes[r, 0].set_ylabel(f"{s} (n={n})\nchannel", fontsize=8)
    axes[r, 5].set_title("FBCCA (class x target)", fontsize=8)
  fig.subplots_adjust(hspace=0.55, right=0.9)
  fig.colorbar(im, ax=axes[:, :5], fraction=0.015, label="LDA coefficient, spatial panels")
  fig.colorbar(imf, ax=axes[:, 5], fraction=0.05, label="LDA coefficient, FBCCA panels")
  fig.suptitle(f"Shrinkage-LDA weights: {' vs '.join(subjects)}", fontsize=11)
  fig.text(0.01, 0.0, "Data: legacy stimulus windows (OO session, P02); features: 32 harmonic-PSD "
           "(POz, O1, Oz, O2) + 5 FBCCA (fs 250 legacy); fit: full data, StandardScaler + "
           "Shrinkage-LDA (export/XAI only, R2 exception)", fontsize=6)
  out_path = Path(out_path)
  out_path.parent.mkdir(parents=True, exist_ok=True)
  fig.savefig(out_path, dpi=150, bbox_inches="tight")
  plt.close(fig)
  return out_path


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs=2, default=["S01", "S04"], metavar=("A", "B"))
  p.add_argument("--out-dir", type=Path, default=None, help="default: <root>/outputs (models in <out>/models)")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  out = args.out_dir or ROOT / "outputs"
  try:
    weights = {s: load_weights(Path(out) / "models", s) for s in args.subjects}
  except (OSError, ValueError) as exc:
    print(f"[x] {exc} (run scripts.training.train_final_model --subject <S> first)")
    return 1
  name = "compare_" + "_".join(args.subjects) + ".png"
  p = plot_comparison(args.subjects, weights, Path(out) / "figures" / "xai_heatmaps" / name)
  print(f"Saved: {p}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
