"""Split-half reliability and pairwise frequency tests of connectivity deltas (P14.2, R4, R7, PF-19, PF-22).

Methods: coherence, PLV, wPLI (PDC excluded, directed). Data source: legacy folders <data-root>/<S>/ (P02, raw
windows), conditions 101-105 and 201; ONE P07 two-tier gate per subject (the P13 loader); trial ids from the
pre-gate labels (PF-03; S02/S04 are approximate, P11 D-2, flagged in the CSV); fs-250 axis (PF-04, labelled).

Per subject and method:
- trial-level split-half reliability of each delta matrix (stimulus AND baseline trials halved, 10 random
  splits, Fisher-mean r, Spearman-Brown 2r/(1+r) only if r > 0, else r uncorrected and labelled
  "not reliable", PF-22);
- for each of the 10 frequency pairs (a, b): the trials of a and b are exchanged at trial level with the
  observed group sizes (PF-19, the P13 splitter); each relabelled group is scored in its own band against the
  same 201 windows re-scored in that band (the baseline is fixed, not permuted); magnitude statistic
  t_mag = mean over edges of (D_a - D_b), two-sided; pattern statistic d_pat = 1 - r(D_a, D_b), one-sided;
  both share the same permutations. Edge-level two-sided p + BH-FDR; BH across the 10 pairs per subject and
  method for p_mag and p_pat separately; reliability ceiling sqrt(rel_a rel_b); disattenuated r only if
  the ceiling > 0.1. Fisher-combined p across responders (from the benchmark CSV only, PF-21) and across
  non-responders. Five subjects: every inferential number is descriptive.

Output (suffix `_<s>` from --out-suffix): reports/connectivity_comparison/<m>_pairwise_tests[_s].csv (section 6
schema), <m>_split_half_reliability[_s].csv (section 6 schema), <m>_split_half_details[_s].csv (uncorrected r,
label), <m>_pairwise_combined[_s].csv (Fisher-combined p per group and pair). `--compare A B` writes
pairwise_flips.csv (cells crossing alpha on any criterion between two runs; '' = the unsuffixed final run).
The 500 and 1000 permutation nulls are nested (the first 500 seeds are shared), so a flip is a
resolution effect, not an independent replication (P13 D-4).
"""

import argparse
import itertools
import re
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
  BASELINE_CONDITION, CONDITION_FREQS, GATE, LEGACY_FS_HZ, band_for_condition, gate_selection,
  load_legacy_selection, compute_condition_coherence)
from src.features.connectivity.permutation import benjamini_hochberg, derive_seed  # noqa: E402
from src.features.connectivity.phase_connectivity import compute_condition_plv, compute_condition_wpli  # noqa: E402

METHODS = {"coherence": compute_condition_coherence, "plv": compute_condition_plv, "wpli": compute_condition_wpli}
CONDITIONS = tuple(CONDITION_FREQS)
PAIRWISE_COLUMNS = ["subject", "method", "freq_a", "freq_b", "t_mag", "p_mag", "d_pat", "p_pat", "r_obs",
                    "n_edges_fdr", "n_edges", "reliability_ceiling", "r_disattenuated", "trial_ids_approximate",
                    "sig_bh_mag", "sig_bh_pat"]
RELIABILITY_COLUMNS = ["subject", "method", "condition", "frequency", "split_half_reliability"]
DETAIL_COLUMNS = ["subject", "method", "condition", "frequency", "r_fisher_uncorrected", "spearman_brown_applied",
                  "n_valid_splits", "label", "n_stim_windows", "n_baseline_windows", "fs", "source"]
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


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--methods", nargs="+", choices=list(METHODS), default=list(METHODS))
  p.add_argument("--subjects", nargs="+", default=None, help="default: every S<digits> folder in the data root")
  p.add_argument("--permutations", type=int, default=1000)
  p.add_argument("--splits", type=int, default=10, help="split-half repetitions")
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
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help="frequency axis, legacy 250 (PF-04)")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  return p


def discover_subjects(data_root: Path) -> list:
  return sorted(d.name for d in Path(data_root).iterdir() if d.is_dir() and re.fullmatch(r"S\d+", d.name))


def load_subject_groups(data_root: Path, subject: str) -> dict:
  """Gated windows per condition with their trial ids; ONE gate decision for 101-105 and 201 (PF-03)."""
  sel = load_legacy_selection(data_root, subject)
  q = gate_selection(sel)
  mask = np.asarray(q["valid_mask"]).astype(bool)
  w, y, ids = q["windows_clean"], q["y_clean"], np.asarray(sel["trial_ids"])[mask]
  groups = {c: (w[y == c], ids[y == c]) for c in list(CONDITIONS) + [BASELINE_CONDITION] if (y == c).any()}
  return dict(groups=groups, approximate=bool(sel["trial_ids_approximate"]), kept=list(q["channels_kept"]),
              dropped=list(q["channels_dropped"]), n_total=int(len(sel["y"])), n_clean=int(len(y)))


def reliability_table(subject: str, method: str, groups: dict, fs: float, n_splits: int, random_state: int,
                      approximate: bool) -> tuple:
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
                         fs=fs, source=SOURCE))
  return rel_rows, det_rows, rel


def _pair_job(subject, method, a, b, win_a, ids_a, win_b, ids_b, base, fs, n_perm, seed, alpha):
  res = pairwise_permutation_test(win_a, ids_a, win_b, ids_b, base, band_for_condition(a), band_for_condition(b),
                                  fs, METHODS[method], n_perm, seed, alpha)
  return subject, method, a, b, {k: v for k, v in res.items() if k not in ("delta_a", "delta_b")}


def pairwise_tables(jobs_out: list, rel: dict, approx: dict, alpha: float) -> dict:
  """Assemble the per-method pairwise DataFrames: ceilings, disattenuation, BH across pairs per subject."""
  rows = {}
  for subject, method, a, b, r in jobs_out:
    ceiling = reliability_ceiling(rel[(subject, method)].get(a, np.nan), rel[(subject, method)].get(b, np.nan))
    rows.setdefault(method, []).append(dict(
      subject=subject, method=method, freq_a=CONDITION_FREQS[a], freq_b=CONDITION_FREQS[b], t_mag=r["t_mag"],
      p_mag=r["p_mag"], d_pat=r["d_pat"], p_pat=r["p_pat"], r_obs=r["r_obs"], n_edges_fdr=r["n_edges_fdr"],
      n_edges=r["n_edges"], reliability_ceiling=ceiling, r_disattenuated=disattenuate(r["r_obs"], ceiling),
      trial_ids_approximate=approx[subject], sig_bh_mag=False, sig_bh_pat=False))
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
  print(f"Data source: {SOURCE}; subjects {subjects}; methods {args.methods}; {args.permutations} trial-level "
        f"permutations; gate {GATE}; responders {groups['responders']}, non-responders {groups['non_responders']}")
  t0 = time.time()
  rel_rows, det_rows, rel, approx, jobs = [], [], {}, {}, []
  for s in subjects:
    d = load_subject_groups(args.data_root, s)
    approx[s] = d["approximate"]
    print(f"[{s}] kept {d['kept']} dropped {d['dropped'] or 'none'}; clean {d['n_clean']}/{d['n_total']}; trial ids "
          f"{'APPROXIMATE' if d['approximate'] else 'exact'}")
    g = d["groups"]
    base, _ = g[BASELINE_CONDITION]
    for m in args.methods:
      a_, b_, r_ = reliability_table(s, m, g, args.fs, args.splits, args.random_state, d["approximate"])
      rel_rows += a_
      det_rows += b_
      rel[(s, m)] = r_
      for a, b in itertools.combinations([c for c in CONDITIONS if c in g], 2):
        jobs.append((s, m, a, b, g[a][0], g[a][1], g[b][0], g[b][1], base))
  print(f"reliability done ({time.time() - t0:.1f} s); {len(jobs)} pairwise jobs")
  t1 = time.time()
  # one job per (subject, method, pair); every job carries its own derived seed, so the result does not
  # depend on n_jobs or on the job order
  jobs_out = Parallel(n_jobs=args.n_jobs)(
    delayed(_pair_job)(s, m, a, b, wa, ia, wb, ib, base, args.fs, args.permutations,
                       derive_seed(args.random_state, s, m, "pair", a, b), args.alpha)
    for (s, m, a, b, wa, ia, wb, ib, base) in jobs)
  print(f"pairwise permutation tests done ({time.time() - t1:.1f} s)")
  tables = pairwise_tables(jobs_out, rel, approx, args.alpha)
  rel_df, det_df = pd.DataFrame(rel_rows, columns=RELIABILITY_COLUMNS), pd.DataFrame(det_rows, columns=DETAIL_COLUMNS)
  for m, df in tables.items():
    df.to_csv(csv_path(reports, m, "pairwise_tests", args.out_suffix), index=False)
    rel_df[rel_df["method"] == m].to_csv(csv_path(reports, m, "split_half_reliability", args.out_suffix), index=False)
    det_df[det_df["method"] == m].to_csv(csv_path(reports, m, "split_half_details", args.out_suffix), index=False)
    combined_table(df, groups).to_csv(csv_path(reports, m, "pairwise_combined", args.out_suffix), index=False)
  return dict(tables=tables, reliability=rel_df, details=det_df, groups=groups)


def report_lines(res: dict, alpha: float) -> list:
  out = []
  for m, df in res["tables"].items():
    out.append(f"== {m} ({int(df['n_edges'].iloc[0])} edges, {len(df)} subject x pair cells) ==")
    out.append(f"  p_mag < {alpha:g}: {int((df['p_mag'] < alpha).sum())}; p_pat < {alpha:g}: {int((df['p_pat'] < alpha).sum())}; "
               f"BH-significant mag {int(df['sig_bh_mag'].sum())}, pat {int(df['sig_bh_pat'].sum())}; cells with >= 1 FDR edge "
               f"{int((df['n_edges_fdr'] >= 1).sum())}")
  rd = res["reliability"]
  out.append(f"split-half: {int((~rd['split_half_reliability'].gt(0)).sum())} of {len(rd)} subject x method x condition "
             f"cells have r <= 0 (reported uncorrected, 'not reliable')")
  return out


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
    mg["inconclusive"] = mg[flips].any(axis=1)
    cols = key + ["p_mag_a", "p_mag_b", "p_pat_a", "p_pat_b", "n_edges_fdr_a", "n_edges_fdr_b"] + flips
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
  t0 = time.time()
  res = run(args)
  print("\n".join(report_lines(res, args.alpha)))
  print(f"saved CSVs in {out_dir(reports)} (suffix '{args.out_suffix}'; total {time.time() - t0:.1f} s)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
