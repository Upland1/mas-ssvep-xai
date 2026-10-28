"""Split-half reliability and pairwise frequency tests of connectivity deltas (P14.2, R4, R7, PF-19, PF-22).

Methods: coherence, PLV, wPLI (PDC excluded, directed). Data source (P16.7, through `load_subject`): the legacy
root `data/processed` by default (P02 raw windows, conditions 101-105 and 201; ONE P07 two-tier gate per subject;
trial ids from the pre-gate labels (PF-03; S02/S04 are approximate, P11 D-2, flagged in the CSV); fs-250 axis
(PF-04, labelled); outputs equal the pre-P16 ones) or a built root (fs from the metadata, true trial ids, shared
quality mask of `--quality`); `--fs` overrides the axis.

Per subject and method:
- trial-level split-half reliability of each delta matrix (stimulus AND baseline trials halved, 10 random
  splits, Fisher-mean r, Spearman-Brown 2r/(1+r) only if r > 0, else r uncorrected and labelled
  "not reliable", PF-22);
- for each of the 10 frequency pairs (a, b): the trials of a and b are exchanged at trial level with the
  observed group sizes (PF-19, the P13 splitter); each relabelled group is scored in its own band against the
  same 201 windows re-scored in that band (the baseline is fixed, not permuted). The null is EXCHANGEABILITY of
  the a and b trials, not D_a = D_b: it is generally off-centre, so p_mag >= 0.05 never means "D_a ~ D_b" and
  p_pat < 0.05 does not mean "the delta patterns differ" (P14 audit F2). Magnitude statistic
  t_mag = mean over edges of (D_a - D_b), two-sided; pattern statistic d_pat = 1 - r(D_a, D_b), one-sided;
  both share the same permutations. A DIAGNOSTIC file <m>_pairwise_null[_s].csv gives the null mean/SD of both
  statistics and p_mag_centred = (1 + #{|t_null - mean| >= |t_obs - mean|}) / (n + 1). Edge-level two-sided p + BH-FDR; BH across the 10 pairs per subject and
  method for p_mag and p_pat separately; reliability ceiling sqrt(rel_a rel_b); disattenuated r only if
  the ceiling > 0.1. Fisher-combined p across responders (from the benchmark CSV only, PF-21) and across
  non-responders. Five subjects: every inferential number is descriptive.

Output (suffix `_<s>` from --out-suffix): reports/connectivity_comparison/<m>_pairwise_tests[_s].csv (section 6
schema), <m>_split_half_reliability[_s].csv (section 6 schema), <m>_split_half_details[_s].csv (uncorrected r,
label), <m>_pairwise_null[_s].csv (DIAGNOSTIC null centre), <m>_pairwise_combined[_s].csv (Fisher-combined p per group and pair). `--compare A B` writes
pairwise_flips.csv (cells crossing alpha on any criterion between two runs; '' = the unsuffixed final run).
P18: on the same pairwise permutations a two-tailed Network-Based Statistic (`src/stats/nbs.py`) at |z| > 2 (edge
pseudo-z from each edge's null mean/std) gives `nbs_max_size` (largest component, edges), `nbs_p`, `n_edges_nbs` (edges of
significant components), plus `fs`; it is a separate criterion from p_mag, p_pat and the FDR count (PF-20, R7).
`--summary-only` re-prints the group summaries from the saved CSVs of `--out-suffix` without recomputation.
The 500 and 1000 permutation nulls are nested (the first 500 seeds are shared), so a flip is a
resolution effect, not an independent replication (P13 D-4).
"""

import argparse
import itertools
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.features.connectivity.comparison import (  # noqa: E402
  SEED, disattenuate, fisher_combined_p, pairwise_permutation_test, reliability_ceiling, responders_from_benchmark,
  split_half_delta_reliability)
from src.features.connectivity.connectivity_extraction import (  # noqa: E402
  BASELINE_CONDITION, CONDITION_FREQS, GATE, band_for_condition, compute_condition_coherence,
  load_condition_windows, source_text)
from src.io.subject_data import QUALITY_MODES, discover_subjects, is_built  # noqa: E402
from src.features.connectivity.permutation import benjamini_hochberg, derive_seed  # noqa: E402
from src.stats.nbs import nbs_sweep  # noqa: E402
from src.features.connectivity.phase_connectivity import compute_condition_plv, compute_condition_wpli  # noqa: E402

METHODS = {"coherence": compute_condition_coherence, "plv": compute_condition_plv, "wpli": compute_condition_wpli}
CONDITIONS = tuple(CONDITION_FREQS)
PAIRWISE_COLUMNS = ["subject", "method", "freq_a", "freq_b", "t_mag", "p_mag", "d_pat", "p_pat", "r_obs",
                    "n_edges_fdr", "n_edges", "reliability_ceiling", "r_disattenuated", "trial_ids_approximate",
                    "sig_bh_mag", "sig_bh_pat", "nbs_max_size", "nbs_p", "n_edges_nbs", "fs"]
NBS_Z = 2.0
RELIABILITY_COLUMNS = ["subject", "method", "condition", "frequency", "split_half_reliability"]
DETAIL_COLUMNS = ["subject", "method", "condition", "frequency", "r_fisher_uncorrected", "spearman_brown_applied",
                  "n_valid_splits", "label", "n_stim_windows", "n_baseline_windows", "fs", "source"]
NULL_COLUMNS = ["subject", "method", "freq_a", "freq_b", "t_null_mean", "t_null_sd", "p_mag_centred",
                "d_null_mean", "d_null_sd"]
COMBINED_COLUMNS = ["method", "group", "freq_a", "freq_b", "k_subjects", "chi2_mag", "p_fisher_mag",
                    "chi2_pat", "p_fisher_pat"]
SOURCE = "legacy windows (P02), raw, fs-250 axis (PF-04)"


def _sfx(suffix: str) -> str:
  return f"_{suffix}" if suffix else ""


def out_dir(reports: Path) -> Path:
  return Path(reports) / "connectivity_comparison"


def csv_path(reports: Path, method: str, kind: str, suffix: str) -> Path:
  return out_dir(reports) / f"{method}_{kind}{_sfx(suffix)}.csv"


def flips_path(reports: Path, a: str, b: str) -> Path:
  if (a, b) == ("p500", ""):
    return out_dir(reports) / "pairwise_flips.csv"
  return out_dir(reports) / f"pairwise_flips_{a or 'final'}_vs_{b or 'final'}.csv"


def _head(data_root: Path, subjects: Sequence[str]) -> str:
  built = bool(subjects) and is_built(Path(data_root) / subjects[0])
  return "built windows (load_subject; fs, true ids and quality per subject)" if built else SOURCE


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--methods", nargs="+", choices=list(METHODS), default=list(METHODS))
  p.add_argument("--subjects", nargs="+", default=None, help="default: every S<digits> folder in the data root")
  p.add_argument("--permutations", type=int, default=1000)
  p.add_argument("--splits", type=int, default=10, help="split-half repetitions")
  p.add_argument("--summary-only", action="store_true",
                 help="re-print the group summaries from the saved pairwise/reliability CSVs of --out-suffix; no computation")
  p.add_argument("--n-jobs", type=int, default=-1)
  p.add_argument("--out-suffix", default="")
  p.add_argument("--compare", nargs=2, metavar=("SUFFIX_A", "SUFFIX_B"), default=None,
                 help="flip list between two runs; use '' for the unsuffixed final run")
  p.add_argument("--responders", nargs="*", default=None,
                 help="explicit responder list; default: 2.0 s smoothed >= 80 %% in the benchmark CSV (PF-21)")
  p.add_argument("--benchmark", type=Path, default=ROOT / "reports" / "n_subjects_benchmark.csv")
  p.add_argument("--threshold", type=float, default=80.0)
  p.add_argument("--alpha", type=float, default=0.05)
  p.add_argument("--random-state", type=int, default=SEED)
  p.add_argument("--fs", type=float, default=None,
                 help="override the frequency axis; default: the folder's (metadata 256 on built roots, "
                      "legacy-assumed 250 on data/processed, PF-04)")
  p.add_argument("--quality", choices=list(QUALITY_MODES), default="shared",
                 help="built roots: shared mask, shared-no-guard or per-script gate; legacy roots always per-script")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  return p


def load_subject_groups(data_root: Path, subject: str, quality_mode: str = "shared",
                        fs_override: Optional[float] = None) -> dict:
  """Clean windows per condition with their trial ids; ONE quality decision for 101-105 and 201 (PF-03, R5)."""
  sel = load_condition_windows(data_root, subject, quality_mode, fs_override)
  w, y, ids = sel["windows"], sel["y"], sel["trial_ids"]
  groups = {c: (w[y == c], ids[y == c]) for c in list(CONDITIONS) + [BASELINE_CONDITION] if (y == c).any()}
  return dict(groups=groups, approximate=bool(sel["trial_ids_approximate"]), kept=list(sel["channels_kept"]),
              dropped=list(sel["channels_dropped"]), n_total=int(sel["n_total_windows"]), n_clean=int(len(y)),
              fs=sel["fs"], source=source_text(sel, SOURCE))


def reliability_table(subject: str, method: str, groups: dict, fs: float, n_splits: int, random_state: int,
                      approximate: bool, source: str = SOURCE) -> tuple:
  fn = METHODS[method]
  base, base_ids = groups[BASELINE_CONDITION]
  rel_rows, det_rows, rel = [], [], {}
  for c in CONDITIONS:
    if c not in groups:
      continue
    w, ids = groups[c]
    r = split_half_delta_reliability(w, ids, base, base_ids, band_for_condition(c), fs, fn, n_splits,
                                     derive_seed(random_state, subject, method, c, "splithalf"))
    rel[c] = r["reliability"]
    rel_rows.append(dict(subject=subject, method=method, condition=c, frequency=CONDITION_FREQS[c],
                         split_half_reliability=r["reliability"]))
    label = "Spearman-Brown corrected" if r["corrected"] else "not reliable (r <= 0, uncorrected)"
    det_rows.append(dict(subject=subject, method=method, condition=c, frequency=CONDITION_FREQS[c],
                         r_fisher_uncorrected=r["r_fisher"], spearman_brown_applied=r["corrected"],
                         n_valid_splits=r["n_valid"], label=label, n_stim_windows=len(w), n_baseline_windows=len(base),
                         fs=fs, source=source))
  return rel_rows, det_rows, rel


def _pair_job(subject, method, a, b, win_a, ids_a, win_b, ids_b, base, fs, n_perm, seed, alpha):
  res = pairwise_permutation_test(win_a, ids_a, win_b, ids_b, base, band_for_condition(a), band_for_condition(b),
                                  fs, METHODS[method], n_perm, seed, alpha)
  nb = nbs_sweep(res["diff_edges"], res["null_edges"], (NBS_Z,), alpha, two_tailed=True)[NBS_Z]
  out = {k: v for k, v in res.items() if k not in ("delta_a", "delta_b", "diff_edges", "null_edges")}
  out.update(nbs_max_size=nb["max_size"], nbs_p=nb["p"], n_edges_nbs=nb["n_sig_edges"], fs=float(fs))
  return subject, method, a, b, out


def null_table(jobs_out: list) -> dict:
  """DIAGNOSTIC null-centre tables per method (does not touch the section 6 pairwise CSV)."""
  rows = {}
  for subject, method, a, b, r in jobs_out:
    rows.setdefault(method, []).append(dict(
      subject=subject, method=method, freq_a=CONDITION_FREQS[a], freq_b=CONDITION_FREQS[b],
      **{k: r[k] for k in NULL_COLUMNS[4:]}))
  return {m: pd.DataFrame(v, columns=NULL_COLUMNS) for m, v in rows.items()}


def pairwise_tables(jobs_out: list, rel: dict, approx: dict, alpha: float) -> dict:
  """Assemble the per-method pairwise DataFrames: ceilings, disattenuation, BH across pairs per subject."""
  rows = {}
  for subject, method, a, b, r in jobs_out:
    ceiling = reliability_ceiling(rel[(subject, method)].get(a, np.nan), rel[(subject, method)].get(b, np.nan))
    rows.setdefault(method, []).append(dict(
      subject=subject, method=method, freq_a=CONDITION_FREQS[a], freq_b=CONDITION_FREQS[b], t_mag=r["t_mag"],
      p_mag=r["p_mag"], d_pat=r["d_pat"], p_pat=r["p_pat"], r_obs=r["r_obs"], n_edges_fdr=r["n_edges_fdr"],
      n_edges=r["n_edges"], reliability_ceiling=ceiling, r_disattenuated=disattenuate(r["r_obs"], ceiling),
      trial_ids_approximate=approx[subject], sig_bh_mag=False, sig_bh_pat=False,
      nbs_max_size=r["nbs_max_size"], nbs_p=r["nbs_p"], n_edges_nbs=r["n_edges_nbs"], fs=r["fs"]))
  out = {}
  for m, rs in rows.items():
    df = pd.DataFrame(rs, columns=PAIRWISE_COLUMNS)
    for s, idx in df.groupby("subject").groups.items():
      p_m, p_p = df.loc[idx, "p_mag"].values, df.loc[idx, "p_pat"].fillna(1.0).values
      df.loc[idx, "sig_bh_mag"] = benjamini_hochberg(p_m, alpha)
      df.loc[idx, "sig_bh_pat"] = benjamini_hochberg(p_p, alpha)
    out[m] = df
  return out


def combined_table(df: pd.DataFrame, groups: dict) -> pd.DataFrame:
  """Fisher-combined p across the subjects of a group, per frequency pair (magnitude and pattern)."""
  rows = []
  for g, subs in groups.items():
    for (fa, fb), x in df[df["subject"].isin(subs)].groupby(["freq_a", "freq_b"], sort=False):
      cm, pm_, k = fisher_combined_p(x["p_mag"].values)
      cp, pp, _ = fisher_combined_p(x["p_pat"].values)
      rows.append(dict(method=x["method"].iloc[0], group=g, freq_a=fa, freq_b=fb, k_subjects=k, chi2_mag=cm,
                       p_fisher_mag=pm_, chi2_pat=cp, p_fisher_pat=pp))
  return pd.DataFrame(rows, columns=COMBINED_COLUMNS)


def run(args) -> dict:
  reports = Path(args.reports_dir)
  out_dir(reports).mkdir(parents=True, exist_ok=True)
  subjects = args.subjects or discover_subjects(args.data_root)
  if args.responders is not None:
    resp = list(args.responders)
  else:
    resp, _ = responders_from_benchmark(args.benchmark, args.threshold)
  groups = {"responders": [s for s in subjects if s in set(resp)],
            "non_responders": [s for s in subjects if s not in set(resp)]}
  print(f"Data source: {_head(args.data_root, subjects)}; subjects {subjects}; methods {args.methods}; {args.permutations} trial-level "
        f"permutations (quality {args.quality}; root {args.data_root}; null = exchangeability of the a/b trials, each scored in its own band against the fixed "
        f"matched baseline; NOT D_a = D_b, see <m>_pairwise_null); gate {GATE}; responders {groups['responders']}, non-responders {groups['non_responders']}")
  t0 = time.time()
  rel_rows, det_rows, rel, approx, jobs = [], [], {}, {}, []
  for s in subjects:
    d = load_subject_groups(args.data_root, s, args.quality, args.fs)
    approx[s] = d["approximate"]
    print(f"[{s}] kept {d['kept']} dropped {d['dropped'] or 'none'}; clean {d['n_clean']}/{d['n_total']}; trial ids "
          f"{'APPROXIMATE' if d['approximate'] else 'exact'}")
    g = d["groups"]
    base, _ = g[BASELINE_CONDITION]
    for m in args.methods:
      a_, b_, r_ = reliability_table(s, m, g, d["fs"], args.splits, args.random_state, d["approximate"], d["source"])
      rel_rows += a_
      det_rows += b_
      rel[(s, m)] = r_
      for a, b in itertools.combinations([c for c in CONDITIONS if c in g], 2):
        jobs.append((s, m, a, b, g[a][0], g[a][1], g[b][0], g[b][1], base, d["fs"]))
  print(f"reliability done ({time.time() - t0:.1f} s); {len(jobs)} pairwise jobs")
  t1 = time.time()
  # one job per (subject, method, pair); every job carries its own derived seed, so the result does not
  # depend on n_jobs or on the job order
  jobs_out = Parallel(n_jobs=args.n_jobs)(
    delayed(_pair_job)(s, m, a, b, wa, ia, wb, ib, base, fs, args.permutations,
                       derive_seed(args.random_state, s, m, "pair", a, b), args.alpha)
    for (s, m, a, b, wa, ia, wb, ib, base, fs) in jobs)
  print(f"pairwise permutation tests done ({time.time() - t1:.1f} s)")
  tables = pairwise_tables(jobs_out, rel, approx, args.alpha)
  nulls = null_table(jobs_out)
  rel_df, det_df = pd.DataFrame(rel_rows, columns=RELIABILITY_COLUMNS), pd.DataFrame(det_rows, columns=DETAIL_COLUMNS)
  for m, df in tables.items():
    df.to_csv(csv_path(reports, m, "pairwise_tests", args.out_suffix), index=False)
    rel_df[rel_df["method"] == m].to_csv(csv_path(reports, m, "split_half_reliability", args.out_suffix), index=False)
    det_df[det_df["method"] == m].to_csv(csv_path(reports, m, "split_half_details", args.out_suffix), index=False)
    nulls[m].to_csv(csv_path(reports, m, "pairwise_null", args.out_suffix), index=False)
    combined_table(df, groups).to_csv(csv_path(reports, m, "pairwise_combined", args.out_suffix), index=False)
  return dict(tables=tables, reliability=rel_df, details=det_df, groups=groups)


def report_lines(res: dict, alpha: float) -> list:
  out = []
  for m, df in res["tables"].items():
    out.append(f"== {m} ({int(df['n_edges'].iloc[0])} edges, {len(df)} subject x pair cells) ==")
    out.append(f"  p_mag < {alpha:g}: {int((df['p_mag'] < alpha).sum())}; p_pat < {alpha:g}: {int((df['p_pat'] < alpha).sum())}; "
               f"BH-significant mag {int(df['sig_bh_mag'].sum())}, pat {int(df['sig_bh_pat'].sum())}; cells with >= 1 FDR edge "
               f"{int((df['n_edges_fdr'] >= 1).sum())}; cells with NBS p < {alpha:g} (two-tailed |z| > {NBS_Z:g}) "
               f"{int((df['nbs_p'] < alpha).sum())}")
    for g, subs in res["groups"].items():
      x = df[df["subject"].isin(subs)]
      if len(x):
        out.append(f"  {g} ({', '.join(subs)}): {len(x)} cells; p_mag < {alpha:g} {int((x['p_mag'] < alpha).sum())}; "
                   f"FDR edge {int((x['n_edges_fdr'] >= 1).sum())}; NBS p < {alpha:g} {int((x['nbs_p'] < alpha).sum())}; "
                   f"mean NBS largest component {x['nbs_max_size'].mean():.1f} of {int(x['n_edges'].max())} edges")
  rd = res["reliability"]
  out.append(f"split-half: {int((~rd['split_half_reliability'].gt(0)).sum())} of {len(rd)} subject x method x condition "
             f"cells have r <= 0 (reported uncorrected, 'not reliable')")
  return out


def load_saved(args) -> dict:
  """Rebuild the objects `report_lines` needs from the saved CSVs of `--out-suffix` (no recomputation)."""
  reports = Path(args.reports_dir)
  tables, rels = {}, []
  for m in args.methods:
    pt, rt = csv_path(reports, m, "pairwise_tests", args.out_suffix), csv_path(reports, m, "split_half_reliability", args.out_suffix)
    if not pt.is_file() or not rt.is_file():
      raise FileNotFoundError(f"--summary-only needs {pt} and {rt}; run without --summary-only first")
    tables[m] = pd.read_csv(pt)
    rels.append(pd.read_csv(rt))
  subjects = sorted({s for df in tables.values() for s in df["subject"]})
  if args.responders is not None:
    resp = list(args.responders)
  else:
    resp, _ = responders_from_benchmark(args.benchmark, args.threshold)
  groups = {"responders": [s for s in subjects if s in set(resp)], "non_responders": [s for s in subjects if s not in set(resp)]}
  return dict(tables=tables, reliability=pd.concat(rels, ignore_index=True), groups=groups)


def compare_runs(reports: Path, a: str, b: str, methods: Sequence[str], alpha: float = 0.05) -> pd.DataFrame:
  """Cells crossing alpha between two runs on p_mag, p_pat, >= 1 FDR edge, BH-mag or BH-pat (R7)."""
  key = ["subject", "method", "freq_a", "freq_b"]
  parts = []
  for m in methods:
    da, db = pd.read_csv(csv_path(reports, m, "pairwise_tests", a)), pd.read_csv(csv_path(reports, m, "pairwise_tests", b))
    ka, kb = set(map(tuple, da[key].values)), set(map(tuple, db[key].values))
    if ka != kb:
      raise ValueError(f"{m}: runs '{a}' and '{b}' differ in rows")
    mg = da.merge(db, on=key, suffixes=("_a", "_b"), validate="one_to_one")
    crit = {"p_mag": lambda d, s: d[f"p_mag{s}"] < alpha, "p_pat": lambda d, s: d[f"p_pat{s}"] < alpha,
            "fdr_edge": lambda d, s: d[f"n_edges_fdr{s}"] >= 1,
            "bh_mag": lambda d, s: d[f"sig_bh_mag{s}"].astype(bool), "bh_pat": lambda d, s: d[f"sig_bh_pat{s}"].astype(bool)}
    flips = []
    for name, f in crit.items():
      mg[f"flip_{name}"] = f(mg, "_a") != f(mg, "_b")
      flips.append(f"flip_{name}")
    cols = key + ["p_mag_a", "p_mag_b", "p_pat_a", "p_pat_b", "n_edges_fdr_a", "n_edges_fdr_b"]
    if "nbs_p_a" in mg and "nbs_p_b" in mg:  # P18: the NBS criterion joins the R7 flip rule
      mg["flip_nbs"] = (mg["nbs_p_a"] < alpha) != (mg["nbs_p_b"] < alpha)
      flips.append("flip_nbs")
      cols += ["nbs_p_a", "nbs_p_b"]
    mg["inconclusive"] = mg[flips].any(axis=1)
    cols += flips
    parts.append(mg.loc[mg["inconclusive"], cols])
  df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
  return df.assign(suffix_a=a, suffix_b=b)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  reports = Path(args.reports_dir)
  if args.compare:
    a, b = args.compare
    flips = compare_runs(reports, a, b, args.methods, args.alpha)
    n_cells = sum(len(pd.read_csv(csv_path(reports, m, "pairwise_tests", a))) for m in args.methods)
    path = flips_path(reports, a, b)
    flips.to_csv(path, index=False)
    print(f"compared '{a or 'final'}' vs '{b or 'final'}': {n_cells} cells compared, {len(flips)} flip across "
          f"alpha={args.alpha:g} on at least one criterion (inconclusive, R7; the nulls are nested, P13 D-4)")
    if len(flips):
      print(flips.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"saved {path}")
    return 0
  if args.summary_only:
    res = load_saved(args)
    print(f"Summary only (no recomputation): CSVs of suffix '{args.out_suffix}' in {out_dir(reports)}")
    print("\n".join(report_lines(res, args.alpha)))
    return 0
  t0 = time.time()
  res = run(args)
  print("\n".join(report_lines(res, args.alpha)))
  print(f"saved CSVs in {out_dir(reports)} (suffix '{args.out_suffix}'; total {time.time() - t0:.1f} s)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
