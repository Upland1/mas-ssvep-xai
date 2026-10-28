"""P16.8 compare_v1_v2: joins and differences only, with a planted answer; exact regression check."""

import pandas as pd

from scripts.diagnostics import compare_v1_v2 as C


def flag_csv(path, a1, a2, sd=None):
  cols = {"Subject": ["S01", "S02", "Mean"], "1.0s Acc (%)": [a1, a1 + 10, a1 + 5], "2.0s Smoothed (%)": [a2, a2 + 10, a2 + 5]}
  if sd is not None:
    cols.update({"1.0s SD": [sd] * 3, "2.0s SD": [sd] * 3, "CV repeats": [5] * 3})
  pd.DataFrame(cols).to_csv(path, index=False)


def conn_csv(path, fdr, p):
  pd.DataFrame({"subject": ["S01", "S01"], "method": ["coherence", "plv"], "condition": [101, 101], "frequency_hz": [24.0, 24.0],
                "obs_diff": [0.1, 0.2], "p_one_tailed": [p, p], "n_edges_sig_fdr": [fdr, fdr + 1]}).to_csv(path, index=False)


def tree(tmp_path):
  snap = tmp_path / "baselines" / "v1_2026-10-27" / "reports"
  snap.mkdir(parents=True)
  rep = tmp_path / "reports"
  rep.mkdir()
  flag_csv(snap / "n_subjects_benchmark.csv", 60.0, 65.0)
  conn_csv(snap / "connectivity_cohort_summary.csv", 1, 0.5)
  for suffix, base in (("v1rep5", 60.0), ("v1fs256", 70.0), ("v2pw", 72.0), ("v2cont", 75.0), ("v2cont_noguard", 74.0)):
    flag_csv(rep / f"n_subjects_benchmark_{suffix}.csv", base, base + 3, sd=1.5)
  for suffix, fdr in (("v2pw", 2), ("v2cont", 4), ("v2cont_noguard", 3)):
    conn_csv(rep / f"connectivity_cohort_summary_{suffix}.csv", fdr, 0.04)
  return tmp_path


def test_effects_are_plain_differences(tmp_path):
  t = tree(tmp_path)
  assert C.main(["--baselines-dir", str(t / "baselines"), "--reports-dir", str(t / "reports")]) == 0
  f = pd.read_csv(t / "reports" / "v1_vs_v2" / "flagship.csv")
  r = f[(f["subject"] == "S01") & (f["window"] == "1.0s")].iloc[0]
  assert (r["v1_frozen"], r["a"], r["a_prime"], r["b"], r["c"], r["c_prime"]) == (60.0, 60.0, 70.0, 72.0, 75.0, 74.0)
  assert (r["d_fs"], r["d_build"], r["d_filter_mode"], r["d_guard"], r["d_total"]) == (10.0, 2.0, 3.0, 1.0, 15.0)
  assert r["c_sd"] == 1.5
  c = pd.read_csv(t / "reports" / "v1_vs_v2" / "connectivity.csv")
  q = c[c["method"] == "plv"].iloc[0]
  assert (q["n_edges_sig_fdr_a"], q["n_edges_sig_fdr_b"], q["n_edges_sig_fdr_c"], q["n_edges_sig_fdr_c_prime"]) == (2, 3, 5, 4)
  assert (q["d_n_edges_sig_fdr_filter_mode"], q["d_n_edges_sig_fdr_guard"], q["d_n_edges_sig_fdr_build"]) == (2, 1, 1)
  md = (t / "reports" / "v1_vs_v2" / "v1_vs_v2.md").read_text()
  assert "## 1.0s window" in md and "## Connectivity" in md and "| S01 | 60.00 | 60.00 (1.50) | 70.00 (1.50)" in md


def test_missing_variant_leaves_empty_columns(tmp_path):
  t = tree(tmp_path)
  (t / "reports" / "n_subjects_benchmark_v2cont.csv").unlink()
  assert C.main(["--baselines-dir", str(t / "baselines"), "--reports-dir", str(t / "reports")]) == 0
  f = pd.read_csv(t / "reports" / "v1_vs_v2" / "flagship.csv")
  assert f["c"].isna().all() and f["d_filter_mode"].isna().all() and f["d_fs"].notna().all()


def test_regression_check_is_exact(tmp_path):
  t = tree(tmp_path)
  snap = t / "baselines" / "v1_2026-10-27" / "reports"
  for name, src in (("n_subjects_benchmark", "n_subjects_benchmark"), ("connectivity_cohort_summary", "connectivity_cohort_summary")):
    (t / "reports" / f"{name}_v1check.csv").write_bytes((snap / f"{src}.csv").read_bytes())
  args = ["--baselines-dir", str(t / "baselines"), "--reports-dir", str(t / "reports"), "--check-regression"]
  assert C.main(args) == 0
  df = pd.read_csv(t / "reports" / "n_subjects_benchmark_v1check.csv")
  df.loc[0, "1.0s Acc (%)"] += 0.01
  df.to_csv(t / "reports" / "n_subjects_benchmark_v1check.csv", index=False)
  assert C.main(args) == 1
