"""Cohort benchmark of the flagship with the two-tier quality gate (P07.6, legacy Era A).

Data source: legacy folders <data-root>/<S>/ (P02, OO session; 7 channels in data/processed, or the
kept channels listed in a subject's channels.json), stimulus windows only, every folder matching
S<digits> that holds the three arrays (or `--subjects`). Per subject the P05 flagship code path:
FBCSP m = 1 (in-fold, R2/PF-11) + FBCCA on the kept channels (55 columns) -> StandardScaler ->
Shrinkage-LDA (lsqr, auto), behind ONE quality decision (PF-10) = the two-tier gate: tier 1 drops a
channel failing the limits in > 50 % of the windows for the whole subject, tier 2 rejects windows on
the surviving channels (vpp 5-120 uV, std 1-35 uV; R5 per-script gate, every threshold explicit).
The per-channel report is printed for every subject.

CV protocol (P11): `--cv grouped` (default) = StratifiedGroupKFold(5, shuffle, 42) over reconstructed
trial ids (R1; ids from contiguous same-label blocks of the pre-gate labels, indexed by the valid
mask, PF-03) and `--smoothing mod5` (default, reported: R8 legacy-folder clause, i%5 on legacy folders; `trial` = reset
at each trial id, the PF-02 diagnostic).
`--cv legacy --smoothing mod5` reproduces the P05-P10 leaky protocol (R1/PF-01 window-level
StratifiedKFold, R8/PF-02 i%5 smoothing; NOT comparable with the leak-free R-6) and writes under
<reports-dir>/legacy_leaky/. Still legacy (labelled): R3/PF-14 and PF-04 per-window sub-band
filtering at fs 250.

Output: <reports-dir>[/legacy_leaky]/n_subjects_benchmark[_suffix].csv with the columns of 02_REQUIREMENTS section 6
(Subject, Channels Kept, Channels Dropped, Clean Windows, Rejected Windows, 1.0s Acc (%),
2.0s Smoothed (%)); "Channels Kept" is the count, "Channels Dropped" the names ("none" if empty);
then a Mean row of the accuracy columns. A .meta.txt next to it carries the protocol labels and the
kept/dropped channel names of each subject. Subjects run in parallel with `--n-jobs` (joblib).
"""

import argparse
import contextlib
import io
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

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

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  add_protocol_args, channel_summary, discover_subjects, legacy_header_lines, load_config, output_dir,
  prepare_subject, print_trial_report, protocol_labels)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  SEED, accuracies, oof_space, space_width, splits_for)
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
MODEL = "Shrinkage-LDA lsqr"
SPACE = "FBCSP + FBCCA (in-fold)"
COLUMNS = ["Subject", "Channels Kept", "Channels Dropped", "Clean Windows", "Rejected Windows",
           "1.0s Acc (%)", "2.0s Smoothed (%)"]
ACC_COLUMNS = ["1.0s Acc (%)", "2.0s Smoothed (%)"]


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="subject folders (default: discover S<digits> folders)")
  p.add_argument("--data-root", type=Path, default=None,
                 help="folder with <S>/ arrays (default: <root>/ + paths.data_processed_dir, i.e. data/processed)")
  p.add_argument("--n-jobs", type=int, default=1, help="parallel subjects (joblib; default 1, -1 = all cores)")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1)")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--out-suffix", default="", help="writes n_subjects_benchmark_<suffix>.csv")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  add_protocol_args(p)
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def evaluate_subject(processed: Path, subject: str, m: int = 1, fs: float = LEGACY_FS_HZ,
                     seed: int = SEED, cv: str = "grouped", smoothing: str = "mod5") -> dict:
  """One subject: gate once, flagship out-of-fold. Returns `{"subject", "row" or None, "log", "kept",
  "dropped", "header", "approximate"}`; a subject that cannot be evaluated has `row = None` and its reason in `log`.
  Console text is collected in `log` (printed in order by the caller, so parallel jobs do not interleave)."""
  buf = io.StringIO()
  out = {"subject": subject, "row": None, "kept": [], "dropped": [], "header": None, "approximate": False}
  with contextlib.redirect_stdout(buf):
    try:
      b = prepare_subject(processed, subject, None, fs, verbose=True)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      out["log"] = buf.getvalue()
      return out
    out["header"] = legacy_header_lines(fs, b["thresholds"], seed, *protocol_labels(cv, smoothing),
                                        b["fbcca_channels"], b["channel_fail_fraction"])
    out["approximate"] = b["trial_ids_approximate"]
    print_trial_report(subject, b)
    space = [sp for sp in benchmark_spaces(b, m) if sp.name == SPACE][0]
    res, errs = oof_space(space, b["subbands"], b["y"], {MODEL: get_sklearn_model_suite(seed)[MODEL]}, seed,
                          splits_for(cv, b["y"], b["trial_ids"], seed))
    if errs:
      print(f"[x] {subject}: {MODEL} failed: {errs[MODEL]}")
    else:
      a1, a2 = accuracies(b["y"], res[MODEL]["pred"], res[MODEL]["scores"], b["trial_ids"], smoothing)
      out["kept"], out["dropped"] = b["channels_kept"], b["channels_dropped"]
      out["row"] = {"Subject": subject, "Channels Kept": len(b["channels_kept"]),
                    "Channels Dropped": " ".join(b["channels_dropped"]) or "none",
                    "Clean Windows": b["n_clean"], "Rejected Windows": b["n_rejected"],
                    "1.0s Acc (%)": round(100 * a1, 2), "2.0s Smoothed (%)": round(100 * a2, 2)}
      print(f"  {channel_summary(b)}")
      print(f"[+] {subject}: {b['n_stimulus']} stimulus, {b['n_clean']} clean, {b['n_rejected']} rejected; "
            f"p={space_width(space, b['subbands'].shape[1])}; 1.0 s {100 * a1:.2f}%  2.0 s smoothed {100 * a2:.2f}%")
  out["log"] = buf.getvalue()
  return out


def with_mean_row(rows: list) -> pd.DataFrame:
  """Subject rows + `Mean` row (mean of the CSV's rounded accuracy values, 2 decimals; other columns blank)."""
  df = pd.DataFrame(rows, columns=COLUMNS)
  mean = {c: "" for c in COLUMNS}
  mean["Subject"] = "Mean"
  for c in ACC_COLUMNS:
    mean[c] = round(float(df[c].mean()), 2)
  return pd.concat([df, pd.DataFrame([mean], columns=COLUMNS)], ignore_index=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = Path(args.data_root or ROOT / cfg["paths"]["data_processed_dir"])
  reports = Path(args.reports_dir or ROOT / "reports")
  if not processed.is_dir():
    print(f"[x] Data root not found: {processed}")
    return 1
  subjects = args.subjects or discover_subjects(processed)
  if not subjects:
    print(f"[-] No subject folders with arrays in {_rel(processed)}")
    return 1
  t0 = time.time()
  print(f"Data source: legacy windows, {_rel(processed)}/<S>/ (P02, OO session), stimulus windows only; "
        f"subjects {', '.join(subjects)}; n_jobs {args.n_jobs}")
  if args.n_jobs == 1:
    results = [evaluate_subject(processed, s, args.m, args.fs, args.seed, args.cv, args.smoothing) for s in subjects]
  else:
    from joblib import Parallel, delayed
    results = Parallel(n_jobs=args.n_jobs)(
      delayed(evaluate_subject)(processed, s, args.m, args.fs, args.seed, args.cv, args.smoothing) for s in subjects)
  rows, header, chans, approx = [], None, [], []
  for r in results:
    if header is None and r["header"]:
      header = r["header"]
      print("\n".join(header))
    print(r["log"], end="")
    if r["row"] is not None:
      rows.append(r["row"])
      if r["approximate"]:
        approx.append(r["subject"])
      chans.append(f"{r['subject']}: kept {' '.join(r['kept'])}; dropped {' '.join(r['dropped']) or 'none'}")
  if not rows:
    print("[-] No subject evaluated")
    return 1
  df = with_mean_row(rows)
  name = "n_subjects_benchmark" + (f"_{args.out_suffix}" if args.out_suffix else "")
  csv = output_dir(reports, args.cv) / f"{name}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  meta = (header or []) + [f"cv={args.cv}, smoothing={args.smoothing}; trial_ids_approximate subjects: "
                           f"{' '.join(approx) or 'none'}", f"model: {SPACE} -> {MODEL}", f"data source: legacy windows, {_rel(processed)}/<S>/"] + chans
  csv.with_suffix(".meta.txt").write_text("\n".join(meta) + "\n")
  print("\n" + df.to_string(index=False))
  mean = df.iloc[-1]
  print(f"\nCohort: {len(rows)} subjects, mean 1.0 s {mean['1.0s Acc (%)']:.2f}%, 2.0 s smoothed "
        f"{mean['2.0s Smoothed (%)']:.2f}% ({'legacy leaky CV, not comparable with R-6' if args.cv == 'legacy' else 'trial-grouped CV, R1'}; "
        f"smoothing {args.smoothing}); runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
