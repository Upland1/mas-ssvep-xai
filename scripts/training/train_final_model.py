"""Export the full-data final models of one subject (P04.3, legacy Era A).

`fit: full data (export/XAI only; R2 exception)` -- these models are fitted on every stimulus
window of the subject, are not cross-validated and carry no accuracy claim; they feed the XAI
figures and the exported artefacts only.

LDA part: StandardScaler + Shrinkage-LDA (lsqr, auto) on the 37-feature hybrid (32 harmonic PSD
+ 5 FBCCA, legacy fs 250, per-window FBCCA), saved to <models-dir>/<S>_shrinkage_lda.joblib as a
dict {model, scaler, classes, subject_id, feature_dim, fit, data_source, feature_names}.

HOOK (deep-learning builder): the fusion CNN export is added in `main` after the LDA export, as a
function `export_fusion_cnn(subject, X_psd, X_time, y, hybrid, models_dir)` writing
<models-dir>/<S>_fusion_cnn.pt; reuse `load_subject_inputs` below.
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
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from scripts.training.train_models import (  # noqa: E402
  CLASS_CODES, DEFAULT_CONFIG, FIT_LABEL, KEEP_CHANNEL_NAMES, STIM_FREQS_HZ, arrays_exist, build_hybrid,
  check_keep_channels, harmonic_bin_indices, load_config, load_stimulus_windows)

DEFAULT_SUBJECT = "S04"
DATA_SOURCE = "legacy windows data/processed/<S>/ (P02, OO session), stimulus windows only"


def feature_names() -> list:
  """Names of the 37 hybrid columns: `<channel>@<Hz>` x 32 (channel-major), then `FBCCA@<Hz>` x 5."""
  hz = np.linspace(5, 35, 31)[harmonic_bin_indices()]
  names = [f"{c}@{h:g}Hz" for c in KEEP_CHANNEL_NAMES for h in hz]
  return names + [f"FBCCA@{f:g}Hz" for f in STIM_FREQS_HZ]


def fit_full_lda(X: np.ndarray, y: np.ndarray) -> tuple:
  """Scaler and Shrinkage-LDA fitted on all rows (R2 exception: export/XAI only). Returns `(scaler, lda)`."""
  scaler = StandardScaler().fit(X)
  lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(scaler.transform(X), y)
  return scaler, lda


def load_subject_inputs(processed_dir: Path, subject: str) -> tuple:
  """`(X_psd, X_time, y, hybrid)` of the stimulus windows of a legacy subject (hybrid `(n, 37)`)."""
  X_psd, X_time, y = load_stimulus_windows(processed_dir, subject)
  return X_psd, X_time, y, build_hybrid(X_psd, X_time)


def export_lda(subject: str, hybrid: np.ndarray, y: np.ndarray, models_dir: Path) -> Path:
  """Fit on all windows and write <models-dir>/<S>_shrinkage_lda.joblib."""
  scaler, lda = fit_full_lda(hybrid, y)
  bundle = {"model": lda, "scaler": scaler, "classes": [int(c) for c in lda.classes_],
            "subject_id": subject, "feature_dim": int(hybrid.shape[1]), "fit": FIT_LABEL,
            "data_source": DATA_SOURCE, "feature_names": feature_names(), "n_windows": int(len(y))}
  path = Path(models_dir) / f"{subject}_shrinkage_lda.joblib"
  path.parent.mkdir(parents=True, exist_ok=True)
  joblib.dump(bundle, path)
  return path


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"default: {DEFAULT_SUBJECT}")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None)
  p.add_argument("--out-dir", type=Path, default=None, help="default: <root>/outputs (models in <out>/models)")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  check_keep_channels(cfg["channels"]["scalp"])
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  models_dir = (args.out_dir or ROOT / "outputs") / "models"
  if not arrays_exist(processed, args.subject):
    print(f"[x] {args.subject}: arrays missing in {processed}/{args.subject} (run scripts.preprocessing.run_preprocessing)")
    return 1
  X_psd, X_time, y, hybrid = load_subject_inputs(processed, args.subject)
  print(f"Data source: {DATA_SOURCE}; fit: {FIT_LABEL}")
  print(f"{args.subject}: {len(y)} windows, hybrid {hybrid.shape}, classes {sorted(set(y.tolist()))}; "
        f"FBCCA legacy fs=250 (PF-04), per-window sub-bands (R3/PF-14)")
  path = export_lda(args.subject, hybrid, y, models_dir)
  print(f"Saved: {path}")
  # HOOK(deep-learning): export_fusion_cnn(args.subject, X_psd, X_time, y, hybrid, models_dir) goes here.
  return 0


if __name__ == "__main__":
  sys.exit(main())
