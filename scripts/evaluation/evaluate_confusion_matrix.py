"""Flagship hybrid: FBCSP (in-fold) + FBCCA -> StandardScaler -> Shrinkage-LDA (P05.5, legacy Era A).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus
windows only. Features: FBCSP with m CSP components per side (default m = 1: 5 bands x 5
classes x 2 = 50) fitted on the training rows of each fold (R2/PF-11) + 5 FBCCA scores = 55;
one quality decision (two-tier gate from P07, limits written out: vpp 5-120 uV, std 1-35 uV, channel
dropped if it fails in > 50 % of the windows; R5 gate) feeds both blocks (PF-10). Model: Pipeline(StandardScaler, LDA(lsqr, shrinkage auto)).

Reported: out-of-fold 1.0 s accuracy, and "2.0 s smoothed" = 2-window average of the out-of-fold
probabilities. P11: `--smoothing trial` (default, R8) resets at each reconstructed trial id;
`--smoothing mod5` is the legacy i%5 rule of the clean array (R8 legacy, PF-02, the original's
"2.0s Trial Smoothed"). The P04 no-reset average is printed as a labelled DIAGNOSTIC only.

CV (P11): `--cv grouped` (default) = StratifiedGroupKFold(5, shuffle, 42) over trial ids (R1);
`--cv legacy` = P05-P10 window-level StratifiedKFold (leaky; outputs under <reports-dir>/legacy_leaky/
and <figures-dir>/legacy_leaky/). Still legacy (labelled): R3/PF-14 and PF-04, fs 250.

Smoothed-prediction outputs (labelled): confusion counts and classification report of the 2.0 s
smoothed predictions under the legacy i%5 rule (*_smoothed_mod5.txt), the trial rule
(*_smoothed_trial.txt, grouped runs only) and the DIAGNOSTIC no-reset rule (*_smoothed_noreset.txt).

Output: <reports-dir>[/legacy_leaky]/flagship_<S>.csv (Subject, Clean Windows, Rejected, m, 1.0s Acc (%),
2.0s Smoothed (%); one row per m, rewritten on rerun), the classification report
<reports-dir>/classification_report_evaluate_confusion_matrix_<S>[_m<m>].txt and the confusion
matrix <figures-dir>/confusion_matrices/cm_fbcsp_m<m>_fbcca_cv_<S>.png (S03 also
cm_fbcsp_m<m>_fbcca_cv.png).
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


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

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.preprocessing.dataset.legacy_windows import CLASS_CODES  # noqa: E402
from src.models.classical.benchmark_runner import channel_summary  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  DEFAULT_SUBJECT, add_protocol_args, figure_paths, legacy_header_lines, load_config, output_dir, plot_confusion,
  prepare_subject, print_trial_report, protocol_labels, save_classification_report, trial_ids_header)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  SEED, accuracies, oof_space, space_width, splits_for)
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402
from sklearn.metrics import confusion_matrix  # noqa: E402
from src.models.classical.benchmark_runner import CLASS_NAMES  # noqa: E402
from src.preprocessing.dataset.smoothing import (  # noqa: E402
  smooth_probabilities_by_trial, smooth_probabilities_legacy, smooth_probabilities_mod5)
from src.features.ssvep.window_mask import MASK_LABEL  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
MODEL = "Shrinkage-LDA lsqr"
SPACE = "FBCSP + FBCCA (in-fold)"
COLUMNS = ["Subject", "Clean Windows", "Rejected", "m", "1.0s Acc (%)", "2.0s Smoothed (%)"]


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default: {DEFAULT_SUBJECT})")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1; 2 = variant)")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--processed-dir", type=Path, default=None, help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--figures-dir", type=Path, default=None, help="default: <root>/ + paths.figures_dir")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  p.add_argument("--no-figures", action="store_true")
  add_protocol_args(p)
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def smoothed_diagnostics(y: np.ndarray, scores: np.ndarray, reports: Path, subject: str, tag: str,
                         trial_ids: Optional[np.ndarray] = None, reported: str = "mod5") -> dict:
  """Confusion counts and classification report of the 2.0 s smoothed predictions under the rules
  (mod5 = legacy i%5; trial = R8, only if `trial_ids` is given; noreset = DIAGNOSTIC); the rule named by
  `reported` is marked REPORTED; written to
  <reports>/classification_report_evaluate_confusion_matrix_<S><tag>_smoothed_{noreset,mod5,trial}.txt and printed.
  Returns {rule: accuracy}."""
  classes = np.array(CLASS_CODES)
  accs = {}
  rules = [("noreset", smooth_probabilities_legacy), ("mod5", smooth_probabilities_mod5)]
  if trial_ids is not None:
    rules.append(("trial", lambda sc: smooth_probabilities_by_trial(sc, trial_ids)))
  for rule, fn in rules:
    pred = classes[np.argmax(fn(scores), axis=1)]
    cm = confusion_matrix(y, pred, labels=list(classes))
    accs[rule] = float(np.mean(pred == y))
    names = {"mod5": "legacy i%5 trial smoothing, R8 legacy, PF-02", "trial": "trial-aware smoothing, R8"}
    kind = ("DIAGNOSTIC (P04 no-reset rule, not the reported number)" if rule == "noreset"
            else f"REPORTED ({names[rule]})" if rule == reported else f"DIAGNOSTIC ({names[rule]}, not the reported rule)")
    title = (f"{kind} {subject} 2.0 s smoothed predictions, rule {rule}; "
             f"accuracy {100 * accs[rule]:.2f}%\nconfusion counts (rows true, columns predicted, order {list(classes)}):\n"
             + "\n".join(" ".join(f"{v:4d}" for v in row) for row in cm))
    rep = save_classification_report(y, pred, reports / f"classification_report_evaluate_confusion_matrix_{subject}{tag}_smoothed_{rule}.txt", title)
    print(f"  {kind.split(' ', 1)[0]} smoothed {rule}: accuracy {100 * accs[rule]:.2f}%\n" + title.split("\n", 1)[1] + "\n" + rep)
  return accs


def update_flagship_csv(path: Path, row: dict) -> pd.DataFrame:
  """Write `row` into `path`, replacing an existing row of the same (Subject, m)."""
  new = pd.DataFrame([row], columns=COLUMNS)
  if Path(path).is_file():
    old = pd.read_csv(path)
    old = old[~((old["Subject"] == row["Subject"]) & (old["m"] == row["m"]))]
    new = pd.concat([old, new], ignore_index=True)
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  new.to_csv(path, index=False)
  return new


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  reports = output_dir(args.reports_dir or ROOT / "reports", args.cv)
  figures = output_dir(args.figures_dir or ROOT / cfg["paths"]["figures_dir"], args.cv)
  t0 = time.time()
  try:
    b = prepare_subject(processed, args.subject, None, args.fs)
  except (FileNotFoundError, ValueError) as exc:
    print(f"[-] Skipping {args.subject}: {exc}")
    return 1
  cv_lab, sm_lab = protocol_labels(args.cv, args.smoothing)
  header = legacy_header_lines(args.fs, b["thresholds"], args.seed, cv_lab, sm_lab)
  print(f"Data source: legacy windows, {_rel(processed)}/{args.subject}/ (P02, OO session), stimulus windows only")
  print("\n".join(header))
  print(trial_ids_header(b))
  print_trial_report(args.subject, b)
  space = [s for s in benchmark_spaces(b, args.m) if s.name == SPACE][0]
  y = b["y"]
  n_bands = b["subbands"].shape[1]
  print(f"  {channel_summary(b)}")
  print(f"\n[+] {args.subject}: {b['n_stimulus']} stimulus windows, {b['n_clean']} clean, {b['n_rejected']} rejected; "
        f"{SPACE}, m={args.m}, p={space_width(space, n_bands)} (FBCSP {5 * 2 * args.m * n_bands} + FBCCA 5)")
  res, errs = oof_space(space, b["subbands"], y, {MODEL: get_sklearn_model_suite(args.seed)[MODEL]}, args.seed,
                      splits_for(args.cv, y, b["trial_ids"], args.seed))
  if errs:
    print(f"[x] {MODEL} failed: {errs[MODEL]}")
    return 1
  r = res[MODEL]
  a1, a2 = accuracies(y, r["pred"], r["scores"], b["trial_ids"], args.smoothing)
  classes = np.unique(y)
  diag = float(np.mean(classes[np.argmax(smooth_probabilities_legacy(r["scores"]), axis=1)] == y))
  print(f"  {MODEL}: 1.0 s {100 * a1:.2f}%  2.0 s smoothed {100 * a2:.2f}% (cv={args.cv}, smoothing={args.smoothing})")
  print(f"  DIAGNOSTIC only (not the reported number): no-reset smoothing {100 * diag:.2f}%")
  tag = "" if args.m == 1 else f"_m{args.m}"
  smoothed_diagnostics(y, r["scores"], reports, args.subject, tag, b["trial_ids"] if args.cv == "grouped" else None,
                       args.smoothing)
  txt = reports / f"classification_report_evaluate_confusion_matrix_{args.subject}{tag}.txt"
  title = (f"{args.subject} {SPACE} m={args.m} -> {MODEL}; {cv_lab}; out-of-fold 1.0 s accuracy "
           f"{100 * a1:.2f}%, 2.0 s smoothed {100 * a2:.2f}% ({sm_lab}); clean windows {b['n_clean']}, "
           f"rejected {b['n_rejected']} ({MASK_LABEL})")
  print(save_classification_report(y, r["pred"], txt, title))
  print(f"Saved: {_rel(txt)}")
  csv = reports / f"flagship_{args.subject}.csv"
  update_flagship_csv(csv, {"Subject": args.subject, "Clean Windows": b["n_clean"], "Rejected": b["n_rejected"],
                            "m": args.m, "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)})
  print(f"Saved: {_rel(csv)}")
  if not args.no_figures:
    cvt = "legacy leaky CV (R1/PF-01)" if args.cv == "legacy" else "trial-grouped CV (R1)"
    ttl = (f"{args.subject} FBCSP(m={args.m}, in-fold) + FBCCA -> Shrinkage-LDA\n"
           f"{cvt}, out-of-fold; 1.0 s {100 * a1:.2f}%")
    for p in plot_confusion(y, r["pred"], ttl, figure_paths(Path(figures) / "confusion_matrices",
                                                           f"cm_fbcsp_m{args.m}_fbcca_cv", args.subject)):
      print(f"Figure: {_rel(p)}")
  print(f"\nCohort: 1 subject ({args.subject}), m={args.m}: clean {b['n_clean']}, rejected {b['n_rejected']}, "
        f"1.0 s {100 * a1:.2f}%, 2.0 s smoothed {100 * a2:.2f}%; runtime {time.time() - t0:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
