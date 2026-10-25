"""First model benchmark on the harmonic-PSD + FBCCA hybrid (P04.1, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/{X_psd_features,X_time_windows,y_labels}.npy
(P02, OO session, 7 channels, 256-sample windows), stimulus windows only (101-105; chance 20 %).
Hybrid features: 32 harmonic-PSD bins (POz, O1, Oz, O2 x 8 bins, channel-major) + 5 FBCCA scores.

Classifiers (each in a Pipeline(StandardScaler, clf), so the scaler is fitted on the training
fold only, R2): Shrinkage-LDA (lsqr, auto), LogisticRegression, Linear SVM, RBF SVM, Random
Forest, MLP (64-32).

Legacy behaviours of this phase (all labelled; fixed in later phases, kept reachable here):
- R1 / PF-01: `StratifiedKFold(5, shuffle, 42)` over windows. Windows of one trial land in
  train and test, so the accuracies are leaky and are NOT comparable with the leak-free R-6.
- R8 / PF-02: the 2-window causal average ignores trial boundaries (no reset).
- fs250 / PF-04: FBCCA filters and references use fs 250 on 256 Hz data (`LEGACY_FS_HZ`).
- R3 / PF-14: FBCCA sub-bands are filtered on each 1 s window (edge effects).

Outputs: <out-dir>/reports/<S>_model_evaluation.csv (columns Subject, Classifier, Accuracy,
Recall per Class, then smoothed and bookkeeping columns) and confusion matrices
<out-dir>/figures/confusion_matrices/<S>/cm_<model>.png (S01 also at .../cm_<model>.png).
"""

import argparse
import re
import sys
import warnings
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import yaml


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else two levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from scipy.signal import butter, filtfilt  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.cross_decomposition import CCA  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, confusion_matrix, recall_score  # noqa: E402
from sklearn.model_selection import StratifiedKFold  # noqa: E402
from sklearn.neural_network import MLPClassifier  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.svm import SVC  # noqa: E402

from src.features.ssvep.harmonic_psd import (  # noqa: E402,F401  (moved to src in P05; re-exported)
  HARMONIC_TARGETS_HZ, KEEP_CHANNEL_NAMES, KEEP_CHANNELS, check_keep_channels, check_subject_keep_channels,
  extract_harmonic_features, harmonic_bin_indices)
from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.preprocessing.dataset.legacy_windows import (  # noqa: E402,F401  (moved to src in P05)
  CLASS_CODES, arrays_exist, load_stimulus_windows)
from src.preprocessing.dataset.smoothing import smooth_probabilities_legacy  # noqa: E402,F401

# SVC(probability=True) is the settled P04 setting (decisions.md); silence its deprecation notice.
warnings.filterwarnings("ignore", message="The `probability` parameter", category=FutureWarning)

SUBJECT_PATTERN = re.compile(r"^S\d+$")
DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
DEFAULT_SUBJECT = "S01"          # the subject of R-2's saved CSV
STIM_FREQS_HZ = (24.0, 20.0, 15.0, 10.9091, 8.5714)   # in CLASS_CODES order (01_DATA_SPEC section 6)
FBCCA_HIGH_HZ = 55.0
FBCCA_LOW_HZ = (6.0, 14.0, 22.0)
N_FOLDS = 5
SEED = 42
CV_LABEL = "StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky)"
SMOOTH_LABEL = "legacy no-reset 2-window average (R8/PF-02)"
FIT_LABEL = "full data (export/XAI only; R2 exception)"
MODEL_FILES = {"Shrinkage-LDA": "shrinkage_lda", "Logistic Regression": "logistic_regression",
               "Linear SVM": "linear_svm", "RBF SVM": "rbf_svm", "Random Forest": "random_forest",
               "MLP (64-32)": "mlp"}


# --- Features ------------------------------------------------------------------

def fbcca_weights(n_bands: int = 3) -> np.ndarray:
  """Sub-band weights `b^-1.25 + 0.25`, b = 1..n_bands."""
  return np.arange(1, n_bands + 1, dtype=float) ** -1.25 + 0.25


def n_harmonics(f_hz: float, high: float = FBCCA_HIGH_HZ, cap: int = 3) -> int:
  """`min(3, 55 // f)` harmonics of a target frequency."""
  return int(min(cap, high // f_hz))


def fbcca_reference(f_hz: float, n_samples: int, fs: float) -> np.ndarray:
  """Sin/cos reference `(T, 2 H)` at h*f, h = 1..H, with `t = arange(T) / fs` (fs legacy 250)."""
  t = np.arange(n_samples) / fs
  cols = []
  for h in range(1, n_harmonics(f_hz) + 1):
    cols += [np.sin(2 * np.pi * h * f_hz * t), np.cos(2 * np.pi * h * f_hz * t)]
  return np.stack(cols, axis=1)


def compute_fbcca_correlations(window: np.ndarray, fs: float = LEGACY_FS_HZ,
                               freqs: Sequence[float] = STIM_FREQS_HZ) -> np.ndarray:
  """FBCCA score of one window `(C, T)` for each target in `freqs` (all C channels).

  legacy (R3/PF-14): each of the 3 Butterworth order-3 sub-bands (low 6/14/22 Hz, high 55 Hz) is
  filtered on the 1 s window itself with `filtfilt`. legacy (PF-04): default `fs=250` although the
  recordings are 256 Hz. Per band the first canonical correlation r of `CCA(n_components=1)`
  against the reference; score `sum_b w_b r_b^2`, `w_b = b^-1.25 + 0.25`.
  """
  x = np.asarray(window, dtype=np.float64)
  w = fbcca_weights(len(FBCCA_LOW_HZ))
  bands = []
  for low in FBCCA_LOW_HZ:
    b, a = butter(3, [low, FBCCA_HIGH_HZ], btype="band", fs=fs)
    bands.append(filtfilt(b, a, x, axis=1).T)  # (T, C)
  scores = np.zeros(len(freqs))
  for k, f in enumerate(freqs):
    ref = fbcca_reference(f, x.shape[1], fs)
    for bi, xb in enumerate(bands):
      try:
        u, v = CCA(n_components=1).fit_transform(xb, ref)
        r = np.corrcoef(u[:, 0], v[:, 0])[0, 1]
        r = 0.0 if not np.isfinite(r) else r
      except Exception:  # degenerate window (constant band): no correlation
        r = 0.0
      scores[k] += w[bi] * r ** 2
  return scores


def extract_all_fbcca_features(X_time: np.ndarray, fs: float = LEGACY_FS_HZ,
                               freqs: Sequence[float] = STIM_FREQS_HZ) -> np.ndarray:
  """FBCCA features `(n, len(freqs))` of every window of `X_time (n, C, T)`."""
  return np.stack([compute_fbcca_correlations(w, fs, freqs) for w in np.asarray(X_time)])


def build_hybrid(X_psd: np.ndarray, X_time: np.ndarray, fs: float = LEGACY_FS_HZ) -> np.ndarray:
  """Hybrid matrix `(n, 37)`: 32 harmonic-PSD columns then 5 FBCCA columns."""
  return np.hstack([extract_harmonic_features(X_psd), extract_all_fbcca_features(X_time, fs)])


# --- Data ----------------------------------------------------------------------

def load_config(path: Path = DEFAULT_CONFIG) -> dict:
  with open(path) as f:
    return yaml.safe_load(f) or {}


def discover_subjects(processed_dir: Path) -> list:
  """Subject folders of `processed_dir` matching ^S\\d+$ that hold the three arrays, numeric order."""
  found = [p.name for p in Path(processed_dir).iterdir()
           if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name) and arrays_exist(processed_dir, p.name)]
  return sorted(found, key=lambda s: int(s[1:]))


# --- Evaluation ----------------------------------------------------------------

def make_classifiers() -> dict:
  """The six classifiers, each in a Pipeline(StandardScaler, clf) (scaler fitted in-fold, R2)."""
  clfs = {
    "Shrinkage-LDA": LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    "Logistic Regression": LogisticRegression(C=1.0, max_iter=1000),
    "Linear SVM": SVC(kernel="linear", C=1.0, probability=True, random_state=SEED),
    "RBF SVM": SVC(kernel="rbf", C=2.0, gamma="scale", probability=True, random_state=SEED),
    "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=6, random_state=SEED),
    "MLP (64-32)": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=SEED),
  }
  return {k: Pipeline([("scaler", StandardScaler()), ("clf", v)]) for k, v in clfs.items()}


def legacy_cv(seed: Optional[int] = None) -> StratifiedKFold:
  """legacy (R1, PF-01): fixed in P11 by StratifiedGroupKFold over trial ids. `seed` default: `SEED` (42)."""
  return StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED if seed is None else seed)


def oof_predictions(model, X: np.ndarray, y: np.ndarray) -> tuple:
  """Out-of-fold `(pred (n,), proba (n, n_classes))`; classes in sorted label order.

  Folds from `legacy_cv()`; the whole Pipeline (scaler included) is cloned and fitted on each
  training fold only (R2).
  """
  classes = np.unique(y)
  pred = np.zeros(len(y), dtype=y.dtype)
  proba = np.zeros((len(y), len(classes)))
  for tr, te in legacy_cv().split(X, y):
    m = clone(model).fit(X[tr], y[tr])
    pred[te] = m.predict(X[te])
    proba[te] = m.predict_proba(X[te])
  return pred, proba


def per_class_recall(y_true: np.ndarray, y_pred: np.ndarray, labels: Sequence[int]) -> np.ndarray:
  return recall_score(y_true, y_pred, labels=list(labels), average=None, zero_division=0)


def run_temporal_integration_evaluation(proba: np.ndarray, y: np.ndarray, classes: Sequence[int]) -> tuple:
  """`(accuracy, per-class recall, predictions)` of the legacy 2-window average (no reset, PF-02)."""
  classes = np.asarray(classes)
  pred = classes[np.argmax(smooth_probabilities_legacy(proba), axis=1)]
  return accuracy_score(y, pred), per_class_recall(y, pred, classes), pred


def _fmt_recall(r: np.ndarray) -> str:
  return "[" + ", ".join(f"{v:.4f}" for v in r) + "]"


def run_evaluation(X: np.ndarray, y: np.ndarray, subject: str, classifiers: Optional[dict] = None) -> tuple:
  """Legacy-CV evaluation of every classifier; returns `(DataFrame, details)`.

  DataFrame columns: Subject, Classifier, Accuracy, Recall per Class (R-2 schema), then
  Smoothed Accuracy, Smoothed Recall per Class, n_windows, cv, smoothing. `details[name]` holds
  `pred`, `proba`, `smoothed_pred`. y holds condition codes (sorted = fixed class order).
  """
  classifiers = classifiers or make_classifiers()
  labels = np.unique(y)
  rows, details = [], {}
  for name, model in classifiers.items():
    pred, proba = oof_predictions(model, X, y)
    s_acc, s_rec, s_pred = run_temporal_integration_evaluation(proba, y, labels)
    rows.append({"Subject": subject, "Classifier": name, "Accuracy": accuracy_score(y, pred),
                 "Recall per Class": _fmt_recall(per_class_recall(y, pred, labels)),
                 "Smoothed Accuracy": s_acc, "Smoothed Recall per Class": _fmt_recall(s_rec),
                 "n_windows": len(y), "cv": "StratifiedKFold (legacy, leaky)",
                 "smoothing": "legacy no-reset (PF-02)"})
    details[name] = {"pred": pred, "proba": proba, "smoothed_pred": s_pred}
  return pd.DataFrame(rows), details


def plot_confusion_matrices(details: dict, y: np.ndarray, subject: str, fig_dir: Path,
                            root_subject: str = DEFAULT_SUBJECT) -> list:
  """`cm_<model>.png` per classifier under <fig_dir>/<subject>/; the root subject also at <fig_dir>/."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  labels = np.unique(y)
  written = []
  for name, d in details.items():
    cm = confusion_matrix(y, d["pred"], labels=labels)
    cmn = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(5, 4.4))
    im = ax.imshow(cmn, vmin=0, vmax=1, cmap="Blues")
    for i in range(len(labels)):
      for j in range(len(labels)):
        ax.text(j, i, f"{cm[i, j]}", ha="center", va="center",
                color="white" if cmn[i, j] > 0.5 else "black", fontsize=9)
    ax.set_xticks(range(len(labels)), [str(int(c)) for c in labels])
    ax.set_yticks(range(len(labels)), [str(int(c)) for c in labels])
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title(f"{subject} {name} (legacy leaky CV, out-of-fold)", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, label="row fraction")
    fig.tight_layout()
    targets = [Path(fig_dir) / subject / f"cm_{MODEL_FILES[name]}.png"]
    if subject == root_subject:
      targets.append(Path(fig_dir) / f"cm_{MODEL_FILES[name]}.png")
    for p in targets:
      p.parent.mkdir(parents=True, exist_ok=True)
      fig.savefig(p, dpi=150)
      written.append(p)
    plt.close(fig)
  return written


# --- CLI -----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  who = p.add_mutually_exclusive_group()
  who.add_argument("--subject", default=None, help=f"one subject (default: {DEFAULT_SUBJECT})")
  who.add_argument("--all", action="store_true", help="every subject folder with arrays")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None, help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--out-dir", type=Path, default=None, help="default: <root>/outputs")
  p.add_argument("--no-figures", action="store_true")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle and model seed (default: {SEED})")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def print_legacy_header(processed: Path) -> None:
  print(f"Data source: legacy windows, {_rel(processed)}/<S>/ (P02, OO session), stimulus windows only")
  print(f"cv={CV_LABEL}; seed={SEED}")
  print(f"smoothing: {SMOOTH_LABEL}")
  print(f"FBCCA: legacy fs={LEGACY_FS_HZ:g} Hz (PF-04), per-window sub-band filtering (R3/PF-14), all channels")
  print("Features: 32 harmonic-PSD (POz, O1, Oz, O2) + 5 FBCCA; scaler inside each fold (R2)")


def main(argv: Optional[Sequence[str]] = None) -> int:
  global SEED
  args = build_parser().parse_args(argv)
  SEED = args.seed   # read at call time by legacy_cv() and make_classifiers()
  cfg = load_config(args.config)
  check_keep_channels(cfg["channels"]["scalp"])
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  out = args.out_dir or ROOT / "outputs"
  subjects = discover_subjects(processed) if args.all else [args.subject or DEFAULT_SUBJECT]
  if not subjects:
    print(f"[x] No subject folders with arrays in {processed}")
    return 1
  print_legacy_header(processed)
  done = 0
  for s in subjects:
    if not arrays_exist(processed, s):
      print(f"[-] Skipping {s}: arrays missing in {_rel(processed)}/{s}")
      continue
    try:
      check_subject_keep_channels(processed, s)
    except ValueError as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    X_psd, X_time, y = load_stimulus_windows(processed, s)
    if len(y) < N_FOLDS * len(CLASS_CODES):
      print(f"[-] Skipping {s}: only {len(y)} stimulus windows")
      continue
    X = build_hybrid(X_psd, X_time)
    print(f"\n[+] {s}: {len(y)} stimulus windows, hybrid {X.shape}")
    df, details = run_evaluation(X, y, s)
    csv = Path(out) / "reports" / f"{s}_model_evaluation.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv, index=False)
    for _, r in df.iterrows():
      print(f"  {r['Classifier']:<20} 1.0 s {100 * r['Accuracy']:6.2f}%  smoothed {100 * r['Smoothed Accuracy']:6.2f}%"
            f"  recall {r['Recall per Class']}")
    print(f"  Saved: {_rel(csv)}")
    if not args.no_figures:
      figs = plot_confusion_matrices(details, y, s, Path(out) / "figures" / "confusion_matrices")
      print(f"  Figures: {len(figs)} confusion matrices under {_rel(Path(out) / 'figures' / 'confusion_matrices')}")
    done += 1
  return 0 if done else 1


if __name__ == "__main__":
  sys.exit(main())
