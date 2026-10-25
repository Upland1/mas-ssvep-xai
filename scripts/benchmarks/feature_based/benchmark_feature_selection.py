"""Feature-selection ablation on one subject (P06.2, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows
only, one window mask (vpp 0.5-120 uV, std 0.1-35 uV; R5 per-script gate) as the P05 flagship.
Base matrix = the P05 flagship: FBCSP m = 1 on 5 bands (50 columns, CSP fitted on the training
rows of each fold, R2/PF-11) + 5 FBCCA scores (all 7 channels) = 55. Model: StandardScaler ->
Shrinkage-LDA (lsqr, auto), as the flagship.

Five rows, all evaluated inside the same legacy folds of the flagship; every selection is
fitted on the training rows of its fold only (R2/PF-11) and applied to the test rows:
  Full baseline                      p = 55
  Sub-band pruning (drop 38-52 Hz)   p = 45 (band 5 = FBCSP columns 40-49 removed, R6)
  ANOVA F-score                      p = k + 5 (SelectKBest(f_classif) on the 50 FBCSP columns, FBCCA kept)
  Mutual information                 p = k + 5 (mutual_info_classif, random_state = seed)
  Sequential forward selection       p = 15 + 5 (SFS of the scaler + Shrinkage-LDA pipeline on the 50
                                     FBCSP columns, scikit-learn inner 5-fold CV, FBCCA kept)

Legacy behaviours (labelled, fixed in later phases): R1/PF-01 StratifiedKFold(5, shuffle, 42) over
windows (leaky); R8/PF-02 "2.0 s smoothed" = legacy i%5 trial smoothing; R3/PF-14 and PF-04
per-window sub-band filtering at fs 250.

Output: <reports-dir>/feature_selection_ablation_<S>.csv (Subject, Method, p, 1.0s Acc (%),
2.0s Smoothed (%), Clean Windows, Rejected) and a .meta.txt with the protocol labels.
"""

import argparse
import sys
import time
import warnings
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else three levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.features.selection.feature_selection import (  # noqa: E402
  select_k_best_fbcsp_features, select_sfs_fbcsp_features, subband_pruned_columns, with_fbcca)
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS  # noqa: E402
from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  DEFAULT_SUBJECT, legacy_header_lines, load_config, prepare_subject)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  CV_LABEL, SEED, SMOOTH_LABEL, accuracies, class_scores, fold_matrices, legacy_cv, space_width)
from src.preprocessing.dataset.legacy_windows import CLASS_CODES  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
SPACE = "FBCSP + FBCCA (in-fold)"
COLUMNS = ["Subject", "Method", "p", "1.0s Acc (%)", "2.0s Smoothed (%)", "Clean Windows", "Rejected"]
FULL, PRUNED, ANOVA, MI, SFS = ("Full baseline", "Sub-band pruning (drop 38-52 Hz)", "ANOVA F-score",
                                "Mutual information", "Sequential forward selection")
METHODS = (FULL, PRUNED, ANOVA, MI, SFS)
DROP_BAND = DEFAULT_SUBBANDS.index((38, 52))


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default: {DEFAULT_SUBJECT})")
  p.add_argument("--k-features", type=int, default=20, help="FBCSP columns kept by ANOVA and MI (default 20)")
  p.add_argument("--sfs-features", type=int, default=15, help="FBCSP columns chosen by SFS (default 15)")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1)")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None, help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle and MI seed (default {SEED})")
  p.add_argument("--n-jobs", type=int, default=1, help="SFS parallel jobs (results do not depend on it)")
  p.add_argument("--skip-sfs", action="store_true", help="omit the SFS row (smoke runs only)")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def _model() -> Pipeline:
  return Pipeline([("scaler", StandardScaler()), ("clf", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))])


def column_sets(Xtr: np.ndarray, ytr: np.ndarray, n_fbcsp: int, k: int, sfs_k: int, seed: int,
                n_jobs: Optional[int] = 1, include_sfs: bool = True) -> dict:
  """Column indices (into the 55-column fold matrix) of every method, computed from the TRAINING rows only (R2/PF-11)."""
  n_cols = Xtr.shape[1]
  fb = Xtr[:, :n_fbcsp]
  tail = np.arange(n_fbcsp, n_cols)
  sel = {FULL: np.arange(n_cols),
         PRUNED: subband_pruned_columns(n_cols, [DROP_BAND], n_bands=len(DEFAULT_SUBBANDS)),
         ANOVA: np.concatenate([select_k_best_fbcsp_features(fb, ytr, k, "anova", seed), tail]),
         MI: np.concatenate([select_k_best_fbcsp_features(fb, ytr, k, "mutual_info", seed), tail])}
  if include_sfs:
    sel[SFS] = np.concatenate([select_sfs_fbcsp_features(fb, ytr, sfs_k, n_jobs=n_jobs), tail])
  return sel


def run_ablation(blocks: dict, subject: str, k: int = 20, sfs_k: int = 15, m: int = 1, seed: int = SEED,
                 n_jobs: Optional[int] = 1, include_sfs: bool = True, verbose: bool = True) -> list:
  """Rows of the ablation table; fold matrices (and the CSP) are built once per fold from its training rows."""
  y = blocks["y"]
  space = [s for s in benchmark_spaces(blocks, m) if s.name == SPACE][0]
  n_bands = blocks["subbands"].shape[1]
  n_fbcsp = len(CLASS_CODES) * 2 * m * n_bands
  methods = [mm for mm in METHODS if include_sfs or mm != SFS]
  classes = np.unique(y)
  out = {mm: {"pred": np.zeros(len(y), dtype=y.dtype), "scores": np.zeros((len(y), len(classes)))} for mm in methods}
  widths = {}
  for f, (tr, te) in enumerate(legacy_cv(seed).split(np.zeros((len(y), 1)), y)):
    t0 = time.time()
    Xtr, Xte = fold_matrices(space, blocks["subbands"], y, tr, te)
    sel = column_sets(Xtr, y[tr], n_fbcsp, k, sfs_k, seed, n_jobs, include_sfs)
    for mm in methods:
      cols = sel[mm]
      widths[mm] = len(cols)
      with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe = _model().fit(Xtr[:, cols], y[tr])
        out[mm]["pred"][te] = pipe.predict(Xte[:, cols])
        out[mm]["scores"][te] = class_scores(pipe, Xte[:, cols])
    if verbose:
      print(f"  fold {f + 1}/5 done ({time.time() - t0:.1f} s)")
  common = {"Subject": subject, "Clean Windows": blocks["n_clean"], "Rejected": blocks["n_rejected"]}
  rows = []
  for mm in methods:
    a1, a2 = accuracies(y, out[mm]["pred"], out[mm]["scores"])
    rows.append({**common, "Method": mm, "p": widths[mm],
                 "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)})
    if verbose:
      print(f"  {mm:<34} p={widths[mm]:<3} 1.0 s {100 * a1:6.2f}%  2.0 s smoothed {100 * a2:6.2f}%")
  assert widths[FULL] == space_width(space, n_bands, len(CLASS_CODES))
  return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  scalp = list(cfg["channels"]["scalp"])
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  reports = Path(args.reports_dir or ROOT / "reports")
  t0 = time.time()
  try:
    b = prepare_subject(processed, args.subject, scalp, args.fs)
  except (FileNotFoundError, ValueError) as exc:
    print(f"[-] Skipping {args.subject}: {exc}")
    return 1
  header = legacy_header_lines(args.fs, b["thresholds"], args.seed, CV_LABEL, SMOOTH_LABEL, b["fbcca_channels"])
  header.append(f"selection (R2/PF-11): ANOVA/MI keep {args.k_features} of the FBCSP columns, SFS {args.sfs_features}, "
                f"FBCCA always kept; all selection fitted on the training rows of each fold")
  print(f"Data source: legacy windows, {_rel(processed)}/{args.subject}/ (P02, OO session), stimulus windows only")
  print("\n".join(header))
  print(f"\n[+] {args.subject}: {b['n_stimulus']} stimulus windows, {b['n_clean']} clean, {b['n_rejected']} rejected")
  rows = run_ablation(b, args.subject, args.k_features, args.sfs_features, args.m, args.seed, args.n_jobs,
                      include_sfs=not args.skip_sfs)
  df = pd.DataFrame(rows, columns=COLUMNS)
  csv = reports / f"feature_selection_ablation_{args.subject}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text("\n".join(header) + "\n")
  print(f"\nCohort: 1 subject ({args.subject}), {len(df)} rows; runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
