"""v1 vs v2 tables of P16.8 (an addition of this rebuild; joins CSVs, computes differences only).

Flagship (`reports/n_subjects_benchmark_<suffix>.csv`, 5 repeats, seeds 42+r), per subject + Mean, 1.0 s and 2.0 s:
  v1   frozen `baselines/v1_*/reports/n_subjects_benchmark.csv` (seed 42, one repeat, fs 250, per-script gate)
  a    legacy folders, fs 250,      suffix v1rep5      (the rows below are judged against this one)
  a'   legacy folders, fs 256,      suffix v1fs256     fs effect            = a'  - a
  a't  as a' with --smoothing trial (suffix v1fs256trial): smoothing-rule effect (2.0 s) = a't - a'
  b    per_window build, shared,    suffix v2pw        8 channels + 1-90 Hz + shared gate + true ids
                                                    = b - a' (1.0 s), b - a't (2.0 s)
  c    continuous build, shared,    suffix v2cont      filtering-mode effect = c - b
  c'   continuous, shared-no-guard, suffix v2cont_noguard   guard effect     = c - c'
Connectivity (`reports/connectivity_cohort_summary_<suffix>.csv`, joined on subject, method, condition,
frequency): a = frozen `baselines/v1_*/reports/connectivity_cohort_summary.csv`, a' = v1fs256 (fs effect a' - a), b = v2pw (build b - a'), c = v2cont,
c' = v2cont_noguard; obs_diff, p_one_tailed, n_edges_sig_fdr per variant and the differences; the filter-mode column is "not applicable (same input)" (both build modes filter the
broadband windows continuously; the effect is flagship only).

Outputs in `--out-dir` (default reports/v1_vs_v2): flagship.csv, connectivity.csv, v1_vs_v2.md. A file that does not
exist leaves its columns empty and is named on the console. `--check-regression` instead compares
`n_subjects_benchmark_v1check.csv` and `connectivity_cohort_summary_v1check.csv` with the frozen files cell by cell
(exact; settled point 4) and exits 1 on any difference.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

FLAGSHIP_VARIANTS = {"a": "v1rep5", "a_prime": "v1fs256", "a_prime_t": "v1fs256trial", "b": "v2pw", "c": "v2cont", "c_prime": "v2cont_noguard"}
CONN_VARIANTS = {"a_prime": "v1fs256", "b": "v2pw", "c": "v2cont", "c_prime": "v2cont_noguard"}
FLAG_METRICS = {"1.0s": ("1.0s Acc (%)", "1.0s SD"), "2.0s": ("2.0s Smoothed (%)", "2.0s SD")}
NOT_APPLICABLE = "not applicable (same input)"
CONN_KEY = ["subject", "method", "condition", "frequency_hz"]
CONN_VALUES = ["obs_diff", "p_one_tailed", "n_edges_sig_fdr"]


def frozen_dir(reports_root: Path, tag: str = "v1") -> Optional[Path]:
  """Latest `baselines/<tag>_*/` snapshot, or None."""
  found = sorted(Path(reports_root).glob(f"{tag}_*"))
  return found[-1] if found else None


def read_csv(path: Path, what: str) -> Optional[pd.DataFrame]:
  if not path.is_file():
    print(f"[-] missing {what}: {path}")
    return None
  return pd.read_csv(path)


def flagship_table(frozen: Optional[pd.DataFrame], variants: dict) -> pd.DataFrame:
  """Long table, one row per subject (and Mean) and window: values and SDs of v1 and every variant, then differences."""
  subjects = []
  for df in [frozen, *variants.values()]:
    if df is not None:
      subjects = list(dict.fromkeys(subjects + list(df["Subject"])))
  subjects = sorted([s for s in subjects if s != "Mean"], key=lambda s: int(s[1:])) + (["Mean"] if "Mean" in subjects else [])
  rows = []
  for s in subjects:
    for w, (acc, sd) in FLAG_METRICS.items():
      row = {"subject": s, "window": w}
      def get(df, col):
        if df is None or col not in df.columns:
          return np.nan
        v = df.loc[df["Subject"] == s, col]
        return float(v.iloc[0]) if len(v) and v.iloc[0] != "" and pd.notna(v.iloc[0]) else np.nan
      row["v1_frozen"] = get(frozen, acc)
      for k, df in variants.items():
        row[k], row[f"{k}_sd"] = get(df, acc), get(df, sd)
      row["d_fs"] = row["a_prime"] - row["a"]
      # 2.0 s: a' still smooths by i % 5 on reconstructed ids, b by true ids; a't separates the rule (fix 4)
      row["d_smoothing"] = row["a_prime_t"] - row["a_prime"] if w == "2.0s" else np.nan
      row["d_build"] = row["b"] - (row["a_prime_t"] if w == "2.0s" else row["a_prime"])
      row["d_filter_mode"] = row["c"] - row["b"]
      row["d_guard"] = row["c"] - row["c_prime"]
      row["d_total"] = row["c"] - row["a"]
      rows.append(row)
  return pd.DataFrame(rows).round(4)


def connectivity_table(frozen: Optional[pd.DataFrame], variants: dict) -> pd.DataFrame:
  """Outer join of the cohort summaries on `CONN_KEY`; columns `<value>_<a|b|c|c_prime>` and differences."""
  parts = {"a": frozen, **variants}
  merged = None
  for k, df in parts.items():
    if df is None:
      continue
    sub = df[CONN_KEY + CONN_VALUES].rename(columns={v: f"{v}_{k}" for v in CONN_VALUES})
    merged = sub if merged is None else merged.merge(sub, on=CONN_KEY, how="outer")
  if merged is None:
    return pd.DataFrame(columns=CONN_KEY)
  for k in parts:
    for v in CONN_VALUES:
      if f"{v}_{k}" not in merged.columns:
        merged[f"{v}_{k}"] = np.nan
  for v in CONN_VALUES:
    merged[f"d_{v}_fs"] = merged[f"{v}_a_prime"] - merged[f"{v}_a"]
    merged[f"d_{v}_build"] = merged[f"{v}_b"] - merged[f"{v}_a_prime"]
    merged[f"d_{v}_filter_mode"] = NOT_APPLICABLE   # connectivity reads the broadband windows: same input in b and c
    merged[f"d_{v}_guard"] = merged[f"{v}_c"] - merged[f"{v}_c_prime"]
  return merged.sort_values(["method", "frequency_hz", "subject"]).reset_index(drop=True)


def markdown(flag: pd.DataFrame, conn: pd.DataFrame) -> str:
  def f(x, nd=2):
    return "" if pd.isna(x) else f"{x:.{nd}f}"
  out = ["# v1 vs v2 (P16.8)", "",
         "Flagship FBCSP(m=1)+FBCCA -> StandardScaler -> Shrinkage-LDA, accuracy % (mean over 5 CV repeats, seeds 42+r; SD in "
         "brackets). v1 = frozen seed-42 run. Differences in percentage points: fs = a' - a, smoothing rule (2.0 s) = a't - a', build = b - a' (1.0 s) / b - a't (2.0 s), filter mode = c - b, "
         "guard = c - c', total = c - a.", ""]
  for w in FLAG_METRICS:
    out += [f"## {w} window", "", "| Subject | v1 | a | a' | a't | b | c | c' | fs | smoothing | build | filter mode | guard | total |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in flag[flag["window"] == w].iterrows():
      cell = lambda k: f"{f(r[k])} ({f(r[k + '_sd'])})" if pd.notna(r[k]) else ""
      out.append(f"| {r['subject']} | {f(r['v1_frozen'])} | {cell('a')} | {cell('a_prime')} | {cell('a_prime_t')} | {cell('b')} | "
                 f"{cell('c')} | {cell('c_prime')} | {f(r['d_fs'])} | {f(r['d_smoothing'])} | {f(r['d_build'])} | "
                 f"{f(r['d_filter_mode'])} | {f(r['d_guard'])} | {f(r['d_total'])} |")
    out.append("")
  if len(conn):
    out += ["## Connectivity (cohort summary; edges significant after FDR / one-tailed global p)", "",
            "| Subject | Method | Hz | FDR a | FDR a' | FDR b | FDR c | FDR c' | p a | p a' | p b | p c | p c' | dFDR fs | dFDR build | "
            "filter mode | dFDR guard |", "|" + "---|" * 17]
    for _, r in conn.iterrows():
      g = lambda k: "" if pd.isna(r[k]) else f"{r[k]:.0f}"
      p = lambda k: "" if pd.isna(r[k]) else f"{r[k]:.3f}"
      fd = lambda v: g(f"n_edges_sig_fdr_{v}")
      pp = lambda v: p(f"p_one_tailed_{v}")
      out.append(f"| {r['subject']} | {r['method']} | {r['frequency_hz']:g} | {fd('a')} | {fd('a_prime')} | {fd('b')} | {fd('c')} | "
                 f"{fd('c_prime')} | {pp('a')} | {pp('a_prime')} | {pp('b')} | {pp('c')} | {pp('c_prime')} | "
                 f"{g('d_n_edges_sig_fdr_fs')} | {g('d_n_edges_sig_fdr_build')} | n/a (same input) | {g('d_n_edges_sig_fdr_guard')} |")
    out.append("")
  return "\n".join(out)


def _verdict(new: Path, old: Path) -> str:
  """`byte-equal`, `value-equal only` (frames equal cell by cell, bytes differ) or `different: <first line>`."""
  if new.read_bytes() == old.read_bytes():
    return "byte-equal"
  a, b = pd.read_csv(new, keep_default_na=False), pd.read_csv(old, keep_default_na=False)
  try:
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    return "value-equal only"
  except AssertionError as exc:
    return f"different: {str(exc).splitlines()[0]}"


def check_regression(reports: Path, snapshot: Path, suffix: str = "v1check") -> int:
  """Compares the `_v1check` outputs with the frozen ones (settled point 4): flagship CSV, connectivity cohort summary
  and its `_details`, the alpha diagnostic, and every `connectivity_edges_<suffix>/*.npz` (array_equal per key).
  Prints byte-equal / value-equal only / different per file; returns 0 when none is different."""
  import numpy as np
  status = 0
  for name in ("n_subjects_benchmark", "connectivity_cohort_summary", "connectivity_cohort_summary_details",
               "connectivity_alpha_diagnostic"):
    # the suffix goes before `_details` in the cohort summary file name
    new_name = name.replace("_details", f"_{suffix}_details") if name.endswith("_details") else f"{name}_{suffix}"
    new, old = reports / f"{new_name}.csv", snapshot / "reports" / f"{name}.csv"
    if not new.is_file() or not old.is_file():
      print(f"[x] {name}: missing {new if not new.is_file() else old}")
      status = 1
      continue
    v = _verdict(new, old)
    print(f"[{'x' if v.startswith('different') else '+'}] {name}: {new.name} vs frozen {old.name}: {v}")
    status |= v.startswith("different")
  new_dir, old_dir = reports / f"connectivity_edges_{suffix}", snapshot / "reports" / "connectivity_edges"
  if not new_dir.is_dir() or not old_dir.is_dir():
    print(f"[-] connectivity_edges: {new_dir if not new_dir.is_dir() else old_dir} missing (not compared)")
  else:
    files = sorted(p.name for p in old_dir.glob("*.npz"))
    bad = []
    for fn in files:
      if not (new_dir / fn).is_file():
        bad.append(fn)
        continue
      with np.load(new_dir / fn, allow_pickle=False) as x, np.load(old_dir / fn, allow_pickle=False) as y:
        if set(x.files) != set(y.files) or not all(np.array_equal(x[k], y[k]) for k in y.files):
          bad.append(fn)
    print(f"[{'x' if bad else '+'}] connectivity_edges: {len(files) - len(bad)}/{len(files)} npz files equal per key"
          + (f"; different or missing: {bad[:5]}" if bad else ""))
    status |= bool(bad)
  return int(bool(status))


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--baselines-dir", type=Path, default=ROOT / "baselines")
  p.add_argument("--baseline-tag", default="v1")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  p.add_argument("--out-dir", type=Path, default=None, help="default: <reports-dir>/v1_vs_v2")
  for k, v in {**{f"flagship-{k.replace('_', '-')}": s for k, s in FLAGSHIP_VARIANTS.items()}}.items():
    p.add_argument(f"--{k}-suffix", default=v)
  for k, v in CONN_VARIANTS.items():
    p.add_argument(f"--conn-{k.replace('_', '-')}-suffix", default=v)
  p.add_argument("--check-regression", action="store_true", help="compare the _v1check CSVs with the frozen ones")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  snap = frozen_dir(args.baselines_dir, args.baseline_tag)
  if snap is None:
    print(f"[x] no {args.baseline_tag}_* snapshot in {args.baselines_dir}")
    return 1
  if args.check_regression:
    return check_regression(args.reports_dir, snap)
  rep = args.reports_dir
  frozen_f = read_csv(snap / "reports" / "n_subjects_benchmark.csv", "frozen flagship")
  var_f = {k: read_csv(rep / f"n_subjects_benchmark_{getattr(args, f'flagship_{k}_suffix')}.csv", f"flagship {k}")
           for k in FLAGSHIP_VARIANTS}
  frozen_c = read_csv(snap / "reports" / "connectivity_cohort_summary.csv", "frozen connectivity")
  var_c = {k: read_csv(rep / f"connectivity_cohort_summary_{getattr(args, f'conn_{k}_suffix')}.csv", f"connectivity {k}")
           for k in CONN_VARIANTS}
  flag, conn = flagship_table(frozen_f, var_f), connectivity_table(frozen_c, var_c)
  out = Path(args.out_dir or rep / "v1_vs_v2")
  out.mkdir(parents=True, exist_ok=True)
  flag.to_csv(out / "flagship.csv", index=False)
  conn.to_csv(out / "connectivity.csv", index=False)
  (out / "v1_vs_v2.md").write_text(markdown(flag, conn) + "\n")
  print(f"Snapshot {snap}; flagship {len(flag)} rows, connectivity {len(conn)} rows")
  print(f"Saved: {out / 'flagship.csv'}, {out / 'connectivity.csv'}, {out / 'v1_vs_v2.md'}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
