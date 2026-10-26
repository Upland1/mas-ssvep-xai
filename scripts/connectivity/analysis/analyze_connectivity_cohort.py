"""Cohort connectivity with permutation statistics (P13.5): coherence, PLV, wPLI, PDC.

Data source: legacy folders <data-root>/<S>/ (P02, raw windows, R3 era B), conditions 101-105 and 201;
fs 250 on the frequency axis (legacy, PF-04). One P07 two-tier gate per subject; trial ids from
`build_trial_ids` on the pre-gate labels then the gate mask (PF-03; S02/S04 may be approximate, P11 D-2).
Bands f_c +- 1 Hz; baseline = the same 201 windows re-scored in each band (PF-16).

Statistics: stimulus minus matched baseline, permutations with the observed group sizes. Unit
`trial` (final) permutes whole trials; `window` is the legacy R7 first run and is labelled. FDR over 21
undirected edges (coherence, PLV, wPLI) or 42 directed edges (PDC, `[i, j]` = j -> i). The console reports
(A) subjects with >= 1 FDR edge and (B) subjects with global p < alpha SEPARATELY (PF-20).

Output (suffix `_<s>` from --out-suffix): reports/connectivity_cohort_summary[_s].csv (section 6 schema),
..._details.csv (extra columns), reports/connectivity_edges[_s]/<S>_<method>.npz,
reports/connectivity_alpha_diagnostic[_s].csv (104/105, P12 D-3). `--compare A B` writes
reports/connectivity_cohort_flips.csv (cells crossing alpha on either criterion between two runs).
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.features.connectivity.connectivity_extraction import (  # noqa: E402
  CONDITION_FREQS, GATE, LEGACY_FS_HZ, compute_aligned_condition_coherence, compute_condition_coherence,
  gate_selection, load_legacy_selection)
from src.features.connectivity.mvar_pdc import compute_condition_pdc  # noqa: E402
from src.features.connectivity.permutation import SEED, extract_connectivity_by_condition  # noqa: E402
from src.features.connectivity.phase_connectivity import compute_condition_plv, compute_condition_wpli  # noqa: E402

METHODS = {"coherence": compute_condition_coherence, "plv": compute_condition_plv,
           "wpli": compute_condition_wpli, "pdc": compute_condition_pdc}
SUMMARY_COLUMNS = ["subject", "method", "condition", "frequency_hz", "label", "obs_diff", "p_one_tailed",
                   "significant_uncorrected", "n_edges_sig_uncorrected", "n_edges_sig_fdr", "total_edges",
                   "n_channels", "channels_dropped", "permutation_unit", "fdr_backed"]
DETAIL_COLUMNS = ["subject", "method", "condition", "frequency_hz", "p_two_tailed", "null_mean", "null_std",
                  "null_ci_lo", "null_ci_hi", "n_permutations", "n_stim_windows", "n_baseline_windows",
                  "fs", "source", "trial_ids_approximate", "coherence_estimator", "random_state"]
ALPHA_COLUMNS = ["subject", "method", "condition", "frequency_hz", "mean_baseline_matched", "mean_stimulus",
                 "mean_difference", "p_one_tailed", "p_lower_tailed", "permutation_unit"]
SOURCE = "legacy windows (P02), raw, fs-250 axis (PF-04)"


def _sfx(suffix: str) -> str:
  return f"_{suffix}" if suffix else ""


def summary_path(reports: Path, suffix: str) -> Path:
  return Path(reports) / f"connectivity_cohort_summary{_sfx(suffix)}.csv"


def flips_path(reports: Path, a: str, b: str) -> Path:
  """`connectivity_cohort_flips.csv` for the required (trial100, final) pair, else one file per pair."""
  if (a, b) == ("trial100", ""):
    return Path(reports) / "connectivity_cohort_flips.csv"
  return Path(reports) / f"connectivity_cohort_flips_{a or 'final'}_vs_{b or 'final'}.csv"


def edges_dir(reports: Path, suffix: str) -> Path:
  return Path(reports) / f"connectivity_edges{_sfx(suffix)}"


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--methods", nargs="+", choices=list(METHODS), default=list(METHODS))
  p.add_argument("--subjects", nargs="+", default=None, help="default: every S<digits> folder in the data root")
  p.add_argument("--permutations", type=int, default=200)
  p.add_argument("--permutation-unit", choices=["trial", "window"], default="trial")
  p.add_argument("--n-jobs", type=int, default=-1)
  p.add_argument("--out-suffix", default="")
  p.add_argument("--coherence-estimator", choices=["concatenated", "aligned"], default="concatenated",
                 help="aligned = P12 D-2 junction diagnostic (reported numbers stay concatenated)")
  p.add_argument("--compare", nargs=2, metavar=("SUFFIX_A", "SUFFIX_B"), default=None,
                 help="flip list between two runs; use '' for the unsuffixed final run")
  p.add_argument("--alpha", type=float, default=0.05)
  p.add_argument("--random-state", type=int, default=SEED)
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help="frequency axis, legacy 250 (PF-04)")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  return p


def discover_subjects(data_root: Path) -> list:
  return sorted(d.name for d in Path(data_root).iterdir() if d.is_dir() and re.fullmatch(r"S\d+", d.name))


def label_for(c: int) -> str:
  return f"{CONDITION_FREQS[c]:.2f} Hz".replace(".00 Hz", " Hz")


def _method_fn(method: str, estimator: str):
  if method == "coherence" and estimator == "aligned":
    return compute_aligned_condition_coherence
  return METHODS[method]


def run_cohort(args) -> dict:
  """Run every subject x method; returns the three DataFrames and writes the edge files."""
  reports = Path(args.reports_dir)
  subjects = args.subjects or discover_subjects(args.data_root)
  summ, det, alpha = [], [], []
  edir = edges_dir(reports, args.out_suffix)
  edir.mkdir(parents=True, exist_ok=True)
  print(f"Data source: {SOURCE}; subjects {subjects}; methods {args.methods}; {args.permutations} "
        f"{args.permutation_unit}-level permutations; gate {GATE}")
  for s in subjects:
    sel = load_legacy_selection(args.data_root, s)
    quality = gate_selection(sel)  # one decision shared by every method and condition (R5 style)
    ids = sel["trial_ids"] if args.permutation_unit == "trial" else None
    print(f"[{s}] kept {quality['channels_kept']} dropped {quality['channels_dropped'] or 'none'}; "
          f"clean {len(quality['y_clean'])}/{len(sel['y'])}; trial ids "
          f"{'APPROXIMATE' if sel['trial_ids_approximate'] else 'exact'}")
    for m in args.methods:
      t0 = time.time()
      res = extract_connectivity_by_condition(
        sel["windows"], sel["y"], args.fs, _method_fn(m, args.coherence_estimator), list(CONDITION_FREQS),
        sel["channel_names"], n_permutations=args.permutations, trial_ids=ids, quality=quality,
        n_jobs=args.n_jobs, random_state=args.random_state, alpha=args.alpha, seed_keys=(s, m))
      meta = res.pop("_meta")
      npz = {"channels_kept": np.array(meta["channels_kept"])}
      for c, r in res.items():
        unit = r["permutation_unit"]
        summ.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c], label=label_for(c),
                         obs_diff=r["obs_diff"], p_one_tailed=r["p_one_tailed"],
                         significant_uncorrected=r["significant_uncorrected"],
                         n_edges_sig_uncorrected=r["n_edges_sig_uncorrected"], n_edges_sig_fdr=r["n_edges_sig_fdr"],
                         total_edges=r["total_edges"], n_channels=len(meta["channels_kept"]),
                         channels_dropped=";".join(meta["channels_dropped"]), permutation_unit=unit,
                         fdr_backed=bool(r["n_edges_sig_fdr"] >= 1)))
        det.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c],
                        p_two_tailed=r["p_two_tailed"], null_mean=r["null_mean"], null_std=r["null_std"],
                        null_ci_lo=r["null_ci"][0], null_ci_hi=r["null_ci"][1], n_permutations=r["n_permutations"],
                        n_stim_windows=r["n_stim"], n_baseline_windows=r["n_base"], fs=args.fs, source=SOURCE,
                        trial_ids_approximate=sel["trial_ids_approximate"],
                        coherence_estimator=args.coherence_estimator if m == "coherence" else "n/a",
                        random_state=args.random_state))
        npz.update({f"stim_{c}": r["stim_matrix"], f"base_{c}": r["base_matrix"], f"diff_{c}": r["observed_diff"],
                    f"p_{c}": r["edge_p_one_tailed"], f"fdr_{c}": r["fdr_significant"]})
        if c in (104, 105):
          emask = ~np.isnan(r["stim_matrix"]) if not r["directed"] else ~np.eye(len(r["stim_matrix"]), dtype=bool)
          alpha.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c],
                            mean_baseline_matched=float(r["base_matrix"][emask].mean()),
                            mean_stimulus=float(r["stim_matrix"][emask].mean()), mean_difference=r["obs_diff"],
                            p_one_tailed=r["p_one_tailed"], p_lower_tailed=r["p_lower_tailed"],
                            permutation_unit=unit))
      np.savez(edir / f"{s}_{m}.npz", **npz)
      tot = sum(r["n_edges_sig_fdr"] for r in res.values())
      print(f"  [{s}] {m}: FDR edges total {tot}; global p " +
            " ".join(f"{label_for(c)}={r['p_one_tailed']:.3f}" for c, r in res.items()) +
            f"  ({time.time() - t0:.1f} s)")
  return dict(summary=pd.DataFrame(summ, columns=SUMMARY_COLUMNS), details=pd.DataFrame(det, columns=DETAIL_COLUMNS),
              alpha=pd.DataFrame(alpha, columns=ALPHA_COLUMNS))


def criteria_report(df: pd.DataFrame, alpha: float) -> list:
  """Console lines: (A) subjects with >= 1 FDR edge and (B) subjects with global p < alpha, separately (PF-20)."""
  out = []
  for m, g in df.groupby("method", sort=False):
    out.append(f"== {m} ({g['permutation_unit'].iloc[0]}-level) ==")
    for c, gc in g.groupby("condition", sort=True):
      a = sorted(gc.loc[gc["n_edges_sig_fdr"] >= 1, "subject"])
      b = sorted(gc.loc[gc["p_one_tailed"] < alpha, "subject"])
      out.append(f"  {label_for(c):>9}  (A) >=1 FDR edge: {a or 'none'}   (B) global p < {alpha:g}: {b or 'none'}")
    tot = g.groupby("subject", sort=True)["n_edges_sig_fdr"].sum()
    out.append("  FDR edge totals per subject: " + ", ".join(f"{k} {int(v)}" for k, v in tot.items()))
  return out


def alpha_relation_lines(alpha_df: pd.DataFrame) -> list:
  """Descriptive Spearman between matched-baseline level and difference across subjects (n small, no inference)."""
  from scipy.stats import spearmanr
  out = ["Alpha diagnostic (P12 D-3), descriptive, no inference: Spearman(matched baseline, difference) across subjects"]
  for (m, c), g in alpha_df.groupby(["method", "condition"], sort=False):
    if len(g) >= 3 and g["mean_baseline_matched"].nunique() > 1 and g["mean_difference"].nunique() > 1:
      r = spearmanr(g["mean_baseline_matched"], g["mean_difference"])[0]
      out.append(f"  {m} {label_for(c)}: rho {r:+.2f} (n = {len(g)})")
  return out


def compare_runs(reports: Path, suffix_a: str, suffix_b: str, alpha: float = 0.05) -> pd.DataFrame:
  """Cells whose verdict crosses alpha between two runs on criterion A (>= 1 FDR edge) or B (global p < alpha)."""
  a = pd.read_csv(summary_path(reports, suffix_a))
  b = pd.read_csv(summary_path(reports, suffix_b))
  key = ["subject", "method", "condition", "frequency_hz"]
  ka, kb = set(map(tuple, a[key[:3]].values)), set(map(tuple, b[key[:3]].values))
  if ka != kb:
    raise ValueError(f"summaries '{suffix_a}' and '{suffix_b}' differ in (subject, method, condition) rows: "
                     f"only in A {sorted(ka - kb)[:5]}, only in B {sorted(kb - ka)[:5]}")
  mg = a.merge(b, on=key, suffixes=("_a", "_b"), validate="one_to_one")
  mg["crit_B_a"], mg["crit_B_b"] = mg["p_one_tailed_a"] < alpha, mg["p_one_tailed_b"] < alpha
  mg["crit_A_a"], mg["crit_A_b"] = mg["n_edges_sig_fdr_a"] >= 1, mg["n_edges_sig_fdr_b"] >= 1
  mg["flip_B"], mg["flip_A"] = mg["crit_B_a"] != mg["crit_B_b"], mg["crit_A_a"] != mg["crit_A_b"]
  mg["inconclusive"] = mg["flip_A"] | mg["flip_B"]
  cols = key + ["p_one_tailed_a", "p_one_tailed_b", "n_edges_sig_fdr_a", "n_edges_sig_fdr_b",
                "flip_B", "flip_A", "inconclusive", "permutation_unit_a", "permutation_unit_b"]
  return mg.loc[mg["inconclusive"], cols].reset_index(drop=True).assign(suffix_a=suffix_a, suffix_b=suffix_b)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  reports = Path(args.reports_dir)
  reports.mkdir(parents=True, exist_ok=True)
  if args.compare:
    a, b = args.compare
    flips = compare_runs(reports, a, b, args.alpha)
    n_cells = len(pd.read_csv(summary_path(reports, a)))
    out = flips_path(reports, a, b)
    flips.to_csv(out, index=False)
    print(f"compared '{a or 'final'}' vs '{b or 'final'}': {n_cells} cells compared, {len(flips)} flip across "
          f"alpha={args.alpha:g} (inconclusive, R7)")
    if len(flips):
      print(flips.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"saved {out}")
    return 0
  t0 = time.time()
  res = run_cohort(args)
  sp = summary_path(reports, args.out_suffix)
  res["summary"].to_csv(sp, index=False)
  res["details"].to_csv(sp.with_name(sp.stem + "_details.csv"), index=False)
  ap = reports / f"connectivity_alpha_diagnostic{_sfx(args.out_suffix)}.csv"
  res["alpha"].to_csv(ap, index=False)
  print("\n".join(criteria_report(res["summary"], args.alpha)))
  print("\n".join(alpha_relation_lines(res["alpha"])))
  if args.coherence_estimator == "aligned":
    print("NOTE: coherence estimator = aligned (P12 D-2 DIAGNOSTIC), not the reported concatenated estimator")
  print(f"saved {sp}, {ap}, {edges_dir(reports, args.out_suffix)}  (total {time.time() - t0:.1f} s)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
