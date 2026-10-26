"""Feature-selection ablation on one subject (P06.2, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows
only, one quality decision (two-tier gate from P07: vpp 5-120 uV, std 1-35 uV, channel dropped if it fails
in > 50 % of the windows; R5 per-script gate) as the P05 flagship.
Base matrix = the P05 flagship: FBCSP m = 1 on 5 bands (50 columns, CSP fitted on the training
rows of each fold, R2/PF-11) + 5 FBCCA scores (all kept channels) = 55. Model: StandardScaler ->
Shrinkage-LDA (lsqr, auto), as the flagship.

Five rows, all evaluated inside the same legacy folds of the flagship; every selection is
fitted on the training rows of its fold only (R2/PF-11) and applied to the test rows:
  Full baseline                      p = 55
  Sub-band pruning (drop 38-52 Hz)   p = 45 (band 5 = FBCSP columns 40-49 removed, R6)
  ANOVA F-score                      p = k + 5 (SelectKBest(f_classif) on the 50 FBCSP columns, FBCCA kept)
  Mutual information                 p = k + 5 (mutual_info_classif, random_state = seed)
  Sequential forward selection       p = 15 + 5 (SFS of the scaler + Shrinkage-LDA pipeline on the 50
                                     FBCSP columns, inner 5-fold CV, FBCCA kept)

CV protocol (P11): `--cv grouped` (default) = StratifiedGroupKFold(5, shuffle, 42) over reconstructed
trial ids for the outer folds AND for the SFS inner CV (grouped over the training-fold trial ids,
PF-01) and `--smoothing mod5` (default, R8 legacy-folder clause; `trial` = PF-02 diagnostic). `--cv legacy --smoothing mod5` reproduces P06 (window-level
outer StratifiedKFold, scikit-learn default inner 5-fold, i%5 smoothing; leaky) and writes under
<reports-dir>/legacy_leaky/. The `--sfs-diagnostics` variants keep their labelled P06 inner CVs.
Still legacy (labelled): R3/PF-14 and PF-04 per-window sub-band filtering at fs 250.

Output: <reports-dir>[/legacy_leaky]/feature_selection_ablation_<S>.csv (Subject, Method, p, 1.0s Acc (%),
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
from sklearn.model_selection import StratifiedKFold  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.features.selection.feature_selection import (  # noqa: E402
  select_k_best_fbcsp_features, select_sfs_fbcsp_features, subband_pruned_columns, with_fbcca)
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS  # noqa: E402
from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import channel_summary  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  DEFAULT_SUBJECT, add_protocol_args, legacy_header_lines, load_config, output_dir, prepare_subject,
  print_trial_report, protocol_labels, trial_ids_header)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  SEED, accuracies, class_scores, fold_matrices, space_width, splits_for)
from src.preprocessing.dataset.cv_utils import grouped_cv  # noqa: E402
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
  p.add_argument("--sfs-diagnostics", action="store_true",
                 help="DIAGNOSTIC only: also run labelled SFS variants and a leak audit (reported rows unchanged)")
  p.add_argument("--skip-sfs", action="store_true", help="omit the SFS row (smoke runs only)")
  add_protocol_args(p)
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def _model() -> Pipeline:
  return Pipeline([("scaler", StandardScaler()), ("clf", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))])


def inner_sfs_splits(ytr: np.ndarray, ids_tr: Optional[np.ndarray], seed: int = SEED) -> Optional[list]:
  """PF-01: grouped inner splits of the SFS over the training-fold trial ids (`StratifiedGroupKFold(5,
  shuffle, seed)`); None (legacy: scikit-learn default inner 5-fold over windows) when `ids_tr` is None."""
  if ids_tr is None:
    return None
  return list(grouped_cv(seed).split(np.zeros((len(ytr), 1)), ytr, np.asarray(ids_tr)))


def column_sets(Xtr: np.ndarray, ytr: np.ndarray, n_fbcsp: int, k: int, sfs_k: int, seed: int,
                n_jobs: Optional[int] = 1, include_sfs: bool = True, ids_tr: Optional[np.ndarray] = None) -> dict:
  """Column indices (into the 55-column fold matrix) of every method, computed from the TRAINING rows only (R2/PF-11).
  `ids_tr` (trial ids of the training rows) makes the SFS inner CV trial-grouped (PF-01)."""
  n_cols = Xtr.shape[1]
  fb = Xtr[:, :n_fbcsp]
  tail = np.arange(n_fbcsp, n_cols)
  sel = {FULL: np.arange(n_cols),
         PRUNED: subband_pruned_columns(n_cols, [DROP_BAND], n_bands=len(DEFAULT_SUBBANDS)),
         ANOVA: np.concatenate([select_k_best_fbcsp_features(fb, ytr, k, "anova", seed), tail]),
         MI: np.concatenate([select_k_best_fbcsp_features(fb, ytr, k, "mutual_info", seed), tail])}
  if include_sfs:
    sel[SFS] = np.concatenate([select_sfs_fbcsp_features(fb, ytr, sfs_k, n_jobs=n_jobs, cv=inner_sfs_splits(ytr, ids_tr, seed)), tail])
  return sel


def run_ablation(blocks: dict, subject: str, k: int = 20, sfs_k: int = 15, m: int = 1, seed: int = SEED,
                 n_jobs: Optional[int] = 1, include_sfs: bool = True, verbose: bool = True,
                 cv: str = "grouped", smoothing: str = "mod5") -> list:
  """Rows of the ablation table; fold matrices (and the CSP) are built once per fold from its training rows."""
  y = blocks["y"]
  ids = blocks.get("trial_ids")
  space = [s for s in benchmark_spaces(blocks, m) if s.name == SPACE][0]
  n_bands = blocks["subbands"].shape[1]
  n_fbcsp = len(CLASS_CODES) * 2 * m * n_bands
  methods = [mm for mm in METHODS if include_sfs or mm != SFS]
  classes = np.unique(y)
  out = {mm: {"pred": np.zeros(len(y), dtype=y.dtype), "scores": np.zeros((len(y), len(classes)))} for mm in methods}
  widths = {}
  for f, (tr, te) in enumerate(splits_for(cv, y, ids, seed)):
    t0 = time.time()
    Xtr, Xte = fold_matrices(space, blocks["subbands"], y, tr, te)
    sel = column_sets(Xtr, y[tr], n_fbcsp, k, sfs_k, seed, n_jobs, include_sfs,
                      ids[tr] if cv == "grouped" else None)
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
    a1, a2 = accuracies(y, out[mm]["pred"], out[mm]["scores"], ids, smoothing)
    rows.append({**common, "Method": mm, "p": widths[mm],
                 "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)})
    if verbose:
      print(f"  {mm:<34} p={widths[mm]:<3} 1.0 s {100 * a1:6.2f}%  2.0 s smoothed {100 * a2:6.2f}%")
  assert widths[FULL] == space_width(space, n_bands, len(CLASS_CODES))
  return rows


# --- DIAGNOSTIC (P06 round 1): SFS variants and leak audit; never part of the reported rows ----------

DIAG_LABEL = "DIAGNOSTIC (P06 round 1), not a reported result"
DIAG_COLUMNS = ["Subject", "Variant", "Inner CV", "Inner shuffle", "Estimator", "Candidates", "n_features", "p",
                "1.0s Acc (%)", "2.0s Smoothed (%)", "Clean Windows", "Rejected", "Label"]
AUDIT_COLUMNS = ["Subject", "Fold", "Train rows", "Test rows", "Disjoint indices", "Test rows found in SFS input",
                 "Selected FBCSP columns", "Label"]
EST_SCALED, EST_SVD, EST_NOSCALE = "scaler+Shrinkage-LDA lsqr (reported)", "plain LDA svd", "Shrinkage-LDA lsqr, no scaler"
CAND_FBCSP, CAND_ALL = "50 FBCSP cols, FBCCA appended (reported)", "all 55 cols"


def _diag_estimator(name: str):
  if name == EST_SVD:
    return LinearDiscriminantAnalysis(solver="svd")
  if name == EST_NOSCALE:
    return LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
  return _model()


def sfs_variants(sfs_k: int = 15) -> list:
  """One-factor-at-a-time variants around the reported SFS: (name, cv, shuffle, estimator, candidates, n)."""
  cur = (5, False, EST_SCALED, CAND_FBCSP, sfs_k)
  v = [("reported", *cur)]
  for cv in (3, 10):
    v.append((f"cv={cv}", cv, False, EST_SCALED, CAND_FBCSP, sfs_k))
  for cv in (3, 5, 10):
    v.append((f"cv={cv} shuffled", cv, True, EST_SCALED, CAND_FBCSP, sfs_k))
  v += [("plain LDA svd", 5, False, EST_SVD, CAND_FBCSP, sfs_k),
        ("Shrinkage-LDA no scaler", 5, False, EST_NOSCALE, CAND_FBCSP, sfs_k),
        ("all 55 columns, n=20", 5, False, EST_SCALED, CAND_ALL, 20),
        ("n=20 FBCSP columns", 5, False, EST_SCALED, CAND_FBCSP, 20)]
  return v


def _sfs_columns(Xtr, ytr, n_fbcsp, cv, shuffle, est, cand, n, seed, n_jobs):
  folds = StratifiedKFold(cv, shuffle=True, random_state=seed) if shuffle else cv
  if cand == CAND_ALL:
    return select_sfs_fbcsp_features(Xtr, ytr, n, _diag_estimator(est), n_jobs, folds)
  idx = select_sfs_fbcsp_features(Xtr[:, :n_fbcsp], ytr, n, _diag_estimator(est), n_jobs, folds)
  return np.concatenate([idx, np.arange(n_fbcsp, Xtr.shape[1])])


def leak_audit_row(subject: str, f: int, tr: np.ndarray, te: np.ndarray, Xtr: np.ndarray, Xte: np.ndarray,
                   cols: np.ndarray, n_fbcsp: int) -> dict:
  """What one SFS fit receives: `Xtr` (= the training rows), checked disjoint from the outer test rows by
  index and by content (no test row equals any row of the SFS input); asserts both."""
  disjoint = np.intersect1d(tr, te).size == 0
  inp = np.round(Xtr[:, :n_fbcsp], 10)
  found = int(sum(bool((inp == np.round(r[:n_fbcsp], 10)).all(axis=1).any()) for r in Xte))
  assert disjoint and found == 0 and Xtr.shape[0] == len(tr), "SFS input overlaps the outer test rows"
  return {"Subject": subject, "Fold": f + 1, "Train rows": int(Xtr.shape[0]), "Test rows": int(len(te)),
          "Disjoint indices": disjoint, "Test rows found in SFS input": found,
          "Selected FBCSP columns": " ".join(str(c) for c in cols if c < n_fbcsp), "Label": DIAG_LABEL}


def run_sfs_diagnostics(blocks: dict, subject: str, sfs_k: int = 15, m: int = 1, seed: int = SEED,
                        n_jobs: Optional[int] = 1, variants: Optional[list] = None, verbose: bool = True,
                        cv_outer: str = "grouped", smoothing: str = "mod5") -> tuple:
  """`(variant rows, audit rows)`. The final classifier of every variant is the reported scaler + Shrinkage-LDA;
  only the SFS configuration changes. Fold matrices (and CSP) are built once per fold from its training rows."""
  y = blocks["y"]
  space = [s for s in benchmark_spaces(blocks, m) if s.name == SPACE][0]
  n_fbcsp = len(CLASS_CODES) * 2 * m * blocks["subbands"].shape[1]
  variants = sfs_variants(sfs_k) if variants is None else variants
  classes = np.unique(y)
  ids = blocks.get("trial_ids")
  splits = splits_for(cv_outer, y, ids, seed)
  mats = [fold_matrices(space, blocks["subbands"], y, tr, te) for tr, te in splits]
  audit = []
  rows = []
  for name, cv, shuffle, est, cand, n in variants:
    t0 = time.time()
    pred, sc = np.zeros(len(y), dtype=y.dtype), np.zeros((len(y), len(classes)))
    width = 0
    for f, ((tr, te), (Xtr, Xte)) in enumerate(zip(splits, mats)):
      cols = _sfs_columns(Xtr, y[tr], n_fbcsp, cv, shuffle, est, cand, n, seed, n_jobs)
      width = len(cols)
      if name == "reported":
        audit.append(leak_audit_row(subject, f, tr, te, Xtr, Xte, cols, n_fbcsp))
      with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe = _model().fit(Xtr[:, cols], y[tr])
        pred[te], sc[te] = pipe.predict(Xte[:, cols]), class_scores(pipe, Xte[:, cols])
    a1, a2 = accuracies(y, pred, sc, ids, smoothing)
    rows.append({"Subject": subject, "Variant": name, "Inner CV": cv, "Inner shuffle": shuffle, "Estimator": est,
                 "Candidates": cand, "n_features": n, "p": width, "1.0s Acc (%)": round(100 * a1, 2),
                 "2.0s Smoothed (%)": round(100 * a2, 2), "Clean Windows": blocks["n_clean"],
                 "Rejected": blocks["n_rejected"], "Label": DIAG_LABEL})
    if verbose:
      print(f"  [{DIAG_LABEL}] {name:<26} p={width:<3} 1.0 s {100 * a1:6.2f}%  2.0 s smoothed {100 * a2:6.2f}% "
            f"({time.time() - t0:.0f} s)")
  return rows, audit


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  reports = output_dir(args.reports_dir or ROOT / "reports", args.cv)
  t0 = time.time()
  try:
    b = prepare_subject(processed, args.subject, None, args.fs)
  except (FileNotFoundError, ValueError) as exc:
    print(f"[-] Skipping {args.subject}: {exc}")
    return 1
  header = legacy_header_lines(args.fs, b["thresholds"], args.seed, *protocol_labels(args.cv, args.smoothing),
                          b["fbcca_channels"])
  header.append("SFS inner CV: " + ("StratifiedGroupKFold(5, shuffle, 42) over the training-fold trial ids (PF-01)"
                                    if args.cv == "grouped" else "scikit-learn default 5-fold over windows (legacy P06, leaky)"))
  header.append(f"selection (R2/PF-11): ANOVA/MI keep {args.k_features} of the FBCSP columns, SFS {args.sfs_features}, "
                f"FBCCA always kept; all selection fitted on the training rows of each fold")
  print(f"Data source: legacy windows, {_rel(processed)}/{args.subject}/ (P02, OO session), stimulus windows only")
  print("\n".join(header))
  print_trial_report(args.subject, b)
  print(f"  {channel_summary(b)}")
  print(f"\n[+] {args.subject}: {b['n_stimulus']} stimulus windows, {b['n_clean']} clean, {b['n_rejected']} rejected")
  rows = run_ablation(b, args.subject, args.k_features, args.sfs_features, args.m, args.seed, args.n_jobs,
                      include_sfs=not args.skip_sfs, cv=args.cv, smoothing=args.smoothing)
  df = pd.DataFrame(rows, columns=COLUMNS)
  csv = reports / f"feature_selection_ablation_{args.subject}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text("\n".join(header + [trial_ids_header(b)]) + "\n")
  if args.sfs_diagnostics:
    print(f"\n{DIAG_LABEL}: SFS variants (final classifier = reported scaler + Shrinkage-LDA; reported rows above unchanged)")
    drows, arows = run_sfs_diagnostics(b, args.subject, args.sfs_features, args.m, args.seed, args.n_jobs,
                                   cv_outer=args.cv, smoothing=args.smoothing)
    dcsv = reports / f"feature_selection_sfs_diagnostics_{args.subject}.csv"
    pd.DataFrame(drows, columns=DIAG_COLUMNS).to_csv(dcsv, index=False)
    acsv = reports / f"feature_selection_sfs_audit_{args.subject}.csv"
    pd.DataFrame(arows, columns=AUDIT_COLUMNS).to_csv(acsv, index=False)
    print(f"{DIAG_LABEL}: leak audit of the reported SFS (assertions passed)")
    for r in arows:
      print(f"  fold {r['Fold']}: SFS input {r['Train rows']} rows, outer test {r['Test rows']} rows, disjoint indices "
            f"{r['Disjoint indices']}, test rows found in input {r['Test rows found in SFS input']}; "
            f"selected FBCSP columns {r['Selected FBCSP columns']}")
    print(f"Saved: {_rel(dcsv)}\nSaved: {_rel(acsv)}")
  print(f"\nCohort: 1 subject ({args.subject}), {len(df)} rows; runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
