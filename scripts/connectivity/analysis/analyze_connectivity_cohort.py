"""Cohort connectivity with permutation statistics (P13.5): coherence, PLV, wPLI, PDC.

Data source (P16.7, through `load_subject`): `--data-root` is either the legacy root `data/processed` (default;
P02 windows, raw, R3 era B, fs 250 on the frequency axis (legacy, PF-04), one P07 two-tier gate per subject,
trial ids from `build_trial_ids` on the pre-gate labels then the gate mask: PF-03, S02/S04 approximate, P11
D-2; with the defaults the outputs equal the pre-P16 ones) or a built root `data/processed_<filter_mode>`
(`scripts/build_windows.py`: fs from the metadata, true trial ids in the trial-level permutations, the shared
quality mask of `--quality`, the kept channels). `--fs` overrides the frequency axis. Conditions 101-105 and 201.
Bands f_c +- 1 Hz; baseline = the same 201 windows re-scored in each band (PF-16).

Statistics: stimulus minus matched baseline, permutations with the observed group sizes. Unit
`trial` (final) permutes whole trials; `window` is the legacy R7 first run and is labelled. FDR over 21
undirected edges (coherence, PLV, wPLI) or 42 directed edges (PDC, `[i, j]` = j -> i). The console reports
(A) subjects with >= 1 FDR edge and (B) subjects with global p < alpha SEPARATELY (PF-20).

Output (suffix `_<s>` from --out-suffix): reports/connectivity_cohort_summary[_s].csv (section 6 schema),
..._details.csv (extra columns), reports/connectivity_edges[_s]/<S>_<method>.npz,
reports/connectivity_alpha_diagnostic[_s].csv (104/105, P12 D-3). `--compare A B` writes
reports/connectivity_cohort_flips.csv (cells crossing alpha on either criterion between two runs).

Network-Based Statistic (P18, `src/stats/nbs.py`): on the SAME trial-level permutations, edge pseudo-z from each edge's
null mean/std, one-tailed z > t supra-threshold edges (stimulus > baseline, as the edge p), connected components
(size = edges), null = largest component of each permutation, p = (1 + #{null_max >= size})/(n + 1). Primary
`--nbs-primary` (2.0), sweep `--nbs-thresholds`. PDC is symmetrized (M + M.T)/2, nulls likewise, before NBS (PF-25);
its FDR keeps the 42 directed edges, so the FDR and NBS denominators differ. Possible NBS edges = C(C-1)/2 of the
subject's kept channels (PF-26). `--stats {nbs,fdr}` picks the criterion (A) in the console summary; FDR, NBS and the
global p (B) are always saved and reported as separate criteria (PF-20). Extra outputs: connectivity_graph_size[_s].csv
(largest component as % of possible edges, FDR counts also as %) and connectivity_nbs_sweep[_s].csv, both printed
as tables; `nbs_<c>` boolean (C, C) masks at the primary threshold in the edge npz.
"""

import argparse
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
  CONDITION_FREQS, GATE, compute_aligned_condition_coherence, compute_condition_coherence, load_condition_windows,
  source_text)
from src.features.connectivity.mvar_pdc import compute_condition_pdc  # noqa: E402
from src.features.connectivity.permutation import SEED, extract_connectivity_by_condition  # noqa: E402
from src.features.connectivity.phase_connectivity import compute_condition_plv, compute_condition_wpli  # noqa: E402
from src.io.subject_data import QUALITY_MODES, discover_subjects, is_built  # noqa: E402
from src.stats.nbs import DEFAULT_THRESHOLDS, edges_to_matrix, matrix_to_edges, nbs_sweep  # noqa: E402

METHODS = {"coherence": compute_condition_coherence, "plv": compute_condition_plv,
           "wpli": compute_condition_wpli, "pdc": compute_condition_pdc}
BASE_SUMMARY_COLUMNS = ["subject", "method", "condition", "frequency_hz", "label", "obs_diff", "p_one_tailed",
                        "significant_uncorrected", "n_edges_sig_uncorrected", "n_edges_sig_fdr", "total_edges",
                        "n_channels", "channels_dropped", "permutation_unit", "fdr_backed"]
GRAPH_SIZE_COLUMNS = ["subject", "method", "condition", "frequency_hz", "label", "n_channels", "possible_edges_nbs",
                      "nbs_threshold", "nbs_max_size", "nbs_size_pct", "nbs_p", "nbs_significant", "n_edges_sig_fdr",
                      "total_edges_fdr", "fdr_pct_of_total"]
SWEEP_COLUMNS = ["subject", "method", "condition", "frequency_hz", "label", "threshold", "max_size", "size_pct", "p",
                 "n_sig_edges", "significant", "possible_edges"]
DETAIL_COLUMNS = ["subject", "method", "condition", "frequency_hz", "p_two_tailed", "null_mean", "null_std",
                  "null_ci_lo", "null_ci_hi", "n_permutations", "n_stim_windows", "n_baseline_windows",
                  "fs", "source", "trial_ids_approximate", "coherence_estimator", "random_state"]
ALPHA_COLUMNS = ["subject", "method", "condition", "frequency_hz", "mean_baseline_matched", "mean_stimulus",
                 "mean_difference", "p_one_tailed", "p_lower_tailed", "permutation_unit"]
SOURCE = "legacy windows (P02), raw, fs-250 axis (PF-04)"


def tkey(t: float) -> str:
  """Threshold as it appears in column names: 1.5, 2, 2.5, 3."""
  return f"{float(t):g}"


def summary_columns(thresholds: Sequence[float]) -> list:
  """Section 6 columns: the pre-P18 ones, then the NBS columns (P18)."""
  return (BASE_SUMMARY_COLUMNS + ["nbs_threshold", "nbs_max_size", "nbs_size_fraction", "nbs_p", "nbs_n_sig_edges",
                                  "nbs_significant"] + [f"nbs_size_z{tkey(t)}" for t in thresholds] +
          [f"nbs_p_z{tkey(t)}" for t in thresholds] + ["n_stim_windows", "n_baseline_windows", "fs", "source"])


SUMMARY_COLUMNS = summary_columns(DEFAULT_THRESHOLDS)  # default sweep; pre-P18 columns first and unchanged


def sweep_thresholds(args) -> list:
  """Sorted thresholds of the sweep, always containing the primary one."""
  return sorted({float(t) for t in args.nbs_thresholds} | {float(args.nbs_primary)})


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
  p.add_argument("--stats", choices=["nbs", "fdr"], default="nbs",
                 help="criterion (A) printed in the console summary; FDR, NBS and global p are always saved")
  p.add_argument("--nbs-thresholds", nargs="+", type=float, default=list(DEFAULT_THRESHOLDS),
                 help="pseudo-z thresholds of the NBS sweep (same permutations)")
  p.add_argument("--nbs-primary", type=float, default=2.0, help="threshold of the nbs_* columns and the nbs_<c> masks")
  p.add_argument("--permutation-unit", choices=["trial", "window"], default="trial")
  p.add_argument("--n-jobs", type=int, default=-1)
  p.add_argument("--out-suffix", default="")
  p.add_argument("--coherence-estimator", choices=["concatenated", "aligned"], default="concatenated",
                 help="aligned = P12 D-2 junction diagnostic (reported numbers stay concatenated)")
  p.add_argument("--compare", nargs=2, metavar=("SUFFIX_A", "SUFFIX_B"), default=None,
                 help="flip list between two runs; use '' for the unsuffixed final run")
  p.add_argument("--alpha", type=float, default=0.05)
  p.add_argument("--random-state", type=int, default=SEED)
  p.add_argument("--fs", type=float, default=None,
                 help="override the frequency axis; default: the folder's (metadata 256 on built roots, "
                      "legacy-assumed 250 on data/processed, PF-04)")
  p.add_argument("--quality", choices=list(QUALITY_MODES), default="shared",
                 help="built roots: shared mask, shared-no-guard (row c') or per-script gate; legacy roots always "
                      "use the per-script P07 gate")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  return p


def label_for(c: int) -> str:
  return f"{CONDITION_FREQS[c]:.2f} Hz".replace(".00 Hz", " Hz")


def _method_fn(method: str, estimator: str):
  if method == "coherence" and estimator == "aligned":
    return compute_aligned_condition_coherence
  return METHODS[method]


def nbs_for_result(r: dict, directed: bool, thresholds: Sequence[float], alpha: float) -> dict:
  """NBS sweep on a `compute_permutation_test` result: one-tailed, PDC symmetrized with its null (PF-25)."""
  obs = matrix_to_edges(r["observed_diff"], directed)
  null = matrix_to_edges(r["null_matrices"], directed)
  return nbs_sweep(obs, null, thresholds, alpha, two_tailed=False)


def run_cohort(args) -> dict:
  """Run every subject x method; returns the DataFrames (summary, details, alpha, graph_size, sweep), writes edges."""
  reports = Path(args.reports_dir)
  subjects = args.subjects or discover_subjects(args.data_root)
  summ, det, alpha, gsize, sweep_rows = [], [], [], [], []
  ths = sweep_thresholds(args)
  prim = float(args.nbs_primary)
  edir = edges_dir(reports, args.out_suffix)
  edir.mkdir(parents=True, exist_ok=True)
  built_root = bool(subjects) and is_built(Path(args.data_root) / subjects[0])
  head = "built windows (load_subject; fs, true ids and quality per subject below)" if built_root else SOURCE
  print(f"Data source: {head if args.fs is None else head + f' (fs {args.fs:g} override)'}; "
        f"subjects {subjects}; methods {args.methods}; {args.permutations} "
        f"{args.permutation_unit}-level permutations; gate {GATE}; quality {args.quality}; root {args.data_root}")
  for s in subjects:
    sel = load_condition_windows(args.data_root, s, args.quality, args.fs)
    quality = sel["quality"]  # one decision shared by every method and condition (R5)
    fs = sel["fs"]
    source = source_text(sel, SOURCE)
    ids = sel["trial_ids"] if args.permutation_unit == "trial" else None
    print(f"[{s}] kept {quality['channels_kept']} dropped {quality['channels_dropped'] or 'none'}; "
          f"clean {len(sel['y'])}/{sel['n_total_windows']}; trial ids "
          f"{'APPROXIMATE' if sel['trial_ids_approximate'] else 'exact'}; fs {fs:g} ({sel['fs_source']})")
    for m in args.methods:
      t0 = time.time()
      res = extract_connectivity_by_condition(
        sel["windows"], sel["y"], fs, _method_fn(m, args.coherence_estimator), list(CONDITION_FREQS),
        sel["channel_names"], n_permutations=args.permutations, trial_ids=ids, quality=quality,
        n_jobs=args.n_jobs, random_state=args.random_state, alpha=args.alpha, seed_keys=(s, m))
      meta = res.pop("_meta")
      npz = {"channels_kept": np.array(meta["channels_kept"])}
      for c, r in res.items():
        unit = r["permutation_unit"]
        nb = nbs_for_result(r, r["directed"], ths, args.alpha)
        np_ = nb[prim]
        row_nbs = dict(nbs_threshold=prim, nbs_max_size=np_["max_size"], nbs_size_fraction=np_["size_fraction"],
                       nbs_p=np_["p"], nbs_n_sig_edges=np_["n_sig_edges"], nbs_significant=np_["significant"],
                       n_stim_windows=r["n_stim"], n_baseline_windows=r["n_base"], fs=fs, source=source)
        row_nbs.update({f"nbs_size_z{tkey(t)}": nb[t]["max_size"] for t in ths})
        row_nbs.update({f"nbs_p_z{tkey(t)}": nb[t]["p"] for t in ths})
        summ.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c], label=label_for(c),
                         obs_diff=r["obs_diff"], p_one_tailed=r["p_one_tailed"],
                         significant_uncorrected=r["significant_uncorrected"],
                         n_edges_sig_uncorrected=r["n_edges_sig_uncorrected"], n_edges_sig_fdr=r["n_edges_sig_fdr"],
                         total_edges=r["total_edges"], n_channels=len(meta["channels_kept"]),
                         channels_dropped=";".join(meta["channels_dropped"]), permutation_unit=unit,
                         fdr_backed=bool(r["n_edges_sig_fdr"] >= 1), **row_nbs))
        gsize.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c], label=label_for(c),
                          n_channels=len(meta["channels_kept"]), possible_edges_nbs=np_["possible_edges"],
                          nbs_threshold=prim, nbs_max_size=np_["max_size"], nbs_size_pct=100.0 * np_["size_fraction"],
                          nbs_p=np_["p"], nbs_significant=np_["significant"], n_edges_sig_fdr=r["n_edges_sig_fdr"],
                          total_edges_fdr=r["total_edges"],
                          fdr_pct_of_total=100.0 * r["n_edges_sig_fdr"] / r["total_edges"]))
        for t in ths:
          sweep_rows.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c], label=label_for(c),
                                 threshold=t, max_size=nb[t]["max_size"], size_pct=100.0 * nb[t]["size_fraction"],
                                 p=nb[t]["p"], n_sig_edges=nb[t]["n_sig_edges"], significant=nb[t]["significant"],
                                 possible_edges=nb[t]["possible_edges"]))
        det.append(dict(subject=s, method=m, condition=c, frequency_hz=CONDITION_FREQS[c],
                        p_two_tailed=r["p_two_tailed"], null_mean=r["null_mean"], null_std=r["null_std"],
                        null_ci_lo=r["null_ci"][0], null_ci_hi=r["null_ci"][1], n_permutations=r["n_permutations"],
                        n_stim_windows=r["n_stim"], n_baseline_windows=r["n_base"], fs=fs, source=source,
                        trial_ids_approximate=sel["trial_ids_approximate"],
                        coherence_estimator=args.coherence_estimator if m == "coherence" else "n/a",
                        random_state=args.random_state))
        npz.update({f"stim_{c}": r["stim_matrix"], f"base_{c}": r["base_matrix"], f"diff_{c}": r["observed_diff"],
                    f"p_{c}": r["edge_p_one_tailed"], f"fdr_{c}": r["fdr_significant"],
                    f"nbs_{c}": edges_to_matrix(np_["mask"], np_["n_channels"])})
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
  return dict(summary=pd.DataFrame(summ, columns=summary_columns(ths)), details=pd.DataFrame(det, columns=DETAIL_COLUMNS),
              alpha=pd.DataFrame(alpha, columns=ALPHA_COLUMNS),
              graph_size=pd.DataFrame(gsize, columns=GRAPH_SIZE_COLUMNS),
              sweep=pd.DataFrame(sweep_rows, columns=SWEEP_COLUMNS))


def criteria_report(df: pd.DataFrame, alpha: float, stats: str = "fdr") -> list:
  """Console lines: (A) the `stats` criterion and (B) subjects with global p < alpha, separately (PF-20).

  `fdr`: (A) = subjects with >= 1 FDR edge (the pre-P18 text); `nbs`: (A) = subjects whose largest NBS component
  has p < alpha at the primary threshold.
  """
  if stats == "nbs":
    out = []
    for m, g in df.groupby("method", sort=False):
      out.append(f"== {m} ({g['permutation_unit'].iloc[0]}-level) ==")
      for c, gc in g.groupby("condition", sort=True):
        a = sorted(gc.loc[gc["nbs_p"] < alpha, "subject"])
        b = sorted(gc.loc[gc["p_one_tailed"] < alpha, "subject"])
        out.append(f"  {label_for(c):>9}  (A) NBS largest component p < {alpha:g} (z > {gc['nbs_threshold'].iloc[0]:g}): "
                   f"{a or 'none'}   (B) global p < {alpha:g}: {b or 'none'}")
      tot = g.groupby("subject", sort=True)["nbs_n_sig_edges"].sum()
      out.append("  NBS significant edge totals per subject: " + ", ".join(f"{k} {int(v)}" for k, v in tot.items()))
    return out
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


def graph_size_lines(gs: pd.DataFrame) -> list:
  """Graph-size table: largest NBS component as % of possible edges ('*' if significant), FDR edges as %."""
  out = ["Graph sizes: largest NBS component as % of possible edges (* = component p < alpha); "
         "FDR edges as % of the method's own edge count in brackets (PDC: 42 directed vs 21 symmetrized)"]
  labels = list(dict.fromkeys(gs["label"]))
  out.append(f"{'subject':<8}{'method':<10}{'ch':>3} " + " ".join(f"{lb:>17}" for lb in labels))
  for (s, m), g in gs.groupby(["subject", "method"], sort=False):
    cells = []
    for lb in labels:
      r = g[g["label"] == lb]
      if r.empty:
        cells.append(f"{'-':>17}")
        continue
      r = r.iloc[0]
      cells.append(f"{r['nbs_size_pct']:6.1f}%{'*' if r['nbs_significant'] else ' '} [{r['fdr_pct_of_total']:4.1f}%]".rjust(17))
    out.append(f"{s:<8}{m:<10}{int(g['n_channels'].iloc[0]):>3} " + " ".join(cells))
  return out


def sweep_lines(sw: pd.DataFrame) -> list:
  """Threshold-sweep table: largest component size (edges) and p per threshold ('*' marks p < alpha)."""
  ths = sorted(sw["threshold"].unique())
  out = ["NBS threshold sweep: largest component size in edges / p (same permutations)"]
  out.append(f"{'subject':<8}{'method':<10}{'freq':>9} " + " ".join(f"{'z>' + tkey(t):>14}" for t in ths))
  for (s, m, lb), g in sw.groupby(["subject", "method", "label"], sort=False):
    cells = []
    for t in ths:
      r = g[g["threshold"] == t].iloc[0]
      cells.append(f"{int(r['max_size']):>3}/{r['p']:.3f}{'*' if r['significant'] else ' '}".rjust(14))
    out.append(f"{s:<8}{m:<10}{lb:>9} " + " ".join(cells))
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
  if "nbs_p_a" in mg and "nbs_p_b" in mg:  # P18: the NBS criterion (A-NBS) joins the R7 flip rule
    mg["flip_NBS"] = (mg["nbs_p_a"] < alpha) != (mg["nbs_p_b"] < alpha)
    mg["inconclusive"] = mg["inconclusive"] | mg["flip_NBS"]
    cols = cols[:-3] + ["nbs_p_a", "nbs_p_b", "flip_NBS"] + cols[-3:]
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
  gp = sp.with_name(f"connectivity_graph_size{_sfx(args.out_suffix)}.csv")
  swp = sp.with_name(f"connectivity_nbs_sweep{_sfx(args.out_suffix)}.csv")
  res["graph_size"].to_csv(gp, index=False)
  res["sweep"].to_csv(swp, index=False)
  print("\n".join(criteria_report(res["summary"], args.alpha, args.stats)))
  print("\n".join(graph_size_lines(res["graph_size"])))
  print("\n".join(sweep_lines(res["sweep"])))
  print("\n".join(alpha_relation_lines(res["alpha"])))
  if args.coherence_estimator == "aligned":
    print("NOTE: coherence estimator = aligned (P12 D-2 DIAGNOSTIC), not the reported concatenated estimator")
  print(f"saved {sp}, {gp}, {swp}, {ap}, {edges_dir(reports, args.out_suffix)}  (total {time.time() - t0:.1f} s)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
