# P18 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, V0-V8), 07_review.md (pre-run audit PASS)
Branch / commit: `phase/P18-nbs` @ 32738ccaf768a087073942e680ee5e0f6fda2891, `git status --porcelain` empty before and during every command (each log header records HEAD and porcelain count 0)
Machine: Linux 7.0.0-38, Python 3.12.3 (`.venv`), 16 logical CPUs (12th Gen Intel i5-12500H), no GPU used

## Commands executed

Cumulative wall clock runs from the pre-state hash (04:12:29). Commands 1-5 are numbered as in 02_plan.md; the suite is step 0. Log file numbers are sequential (01 = suite).

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 0 | `pytest tests -o addopts="" -q` in a clean worktree of HEAD (`mas/state/scratch/verify/P18`, removed afterwards) | 04:12:55 | 751 s | 0 | `reports/logs/P18/01_pytest.log` | 1204 passed, 1 skipped, 22 warnings in 749.44s |
| 1 | cohort, `--permutations 200 --out-suffix p18_nbs_p200` (full flags in 02_plan.md) | 04:25:22 | 370 s (script total 369.0 s) | 0 | `reports/logs/P18/02_cohort_p200.log` | `connectivity_cohort_summary_p18_nbs_p200.csv` (+ `_details`), `connectivity_graph_size_`, `connectivity_nbs_sweep_`, `connectivity_alpha_diagnostic_`, `connectivity_edges_p18_nbs_p200/` |
| 2 | cohort, `--permutations 1000 --out-suffix p18_nbs` | 04:31:32 | 1853 s (script total 1851.5 s) | 0 | `reports/logs/P18/03_cohort_p1000.log` | same set with suffix `p18_nbs` |
| 3 | `--compare p18_nbs_p200 p18_nbs` | 05:02:25 | 1 s | 0 | `reports/logs/P18/04_compare.log` | `connectivity_cohort_flips_p18_nbs_p200_vs_p18_nbs.csv` |
| 4 | pairwise, `--methods coherence plv wpli --permutations 1000 --benchmark reports/n_subjects_benchmark_v2cont.csv --out-suffix p18_nbs` | 05:02:38 | 2537 s (script total 2536.2 s) | 0 | `reports/logs/P18/05_pairwise_p1000.log` | `reports/connectivity_comparison/<m>_pairwise_tests_p18_nbs.csv`, `_split_half_reliability_`, `_split_half_details_`, `_pairwise_null_`, `_pairwise_combined_` for coherence, plv, wpli |
| 5 | pairwise `--summary-only` (same methods, suffix, benchmark) | 05:44:55 | 1 s | 0 | `reports/logs/P18/06_pairwise_summary.log` | console only |

V0 (budget): cumulative wall time after command 3 = 04:12:29 -> 05:02:26 = 49.9 min <= 69 min, so commands 4-5 were run. Total from pre-state to end of command 5 (05:44:56) = 92.5 min, inside `LOCAL_RUN_BUDGET_MIN` 120 (`reports/logs/P18/after_cmd3.txt`, `after_cmd5.txt`).

## Human run requests

None.

## Produced files

- `reports/connectivity_cohort_summary_p18_nbs{,_p200}.csv`, `..._details.csv`
- `reports/connectivity_graph_size_p18_nbs{,_p200}.csv`, `reports/connectivity_nbs_sweep_p18_nbs{,_p200}.csv`, `reports/connectivity_alpha_diagnostic_p18_nbs{,_p200}.csv`
- `reports/connectivity_edges_p18_nbs/`, `reports/connectivity_edges_p18_nbs_p200/` (20 npz each)
- `reports/connectivity_cohort_flips_p18_nbs_p200_vs_p18_nbs.csv`
- `reports/connectivity_comparison/{coherence,plv,wpli}_{pairwise_tests,split_half_reliability,split_half_details,pairwise_null,pairwise_combined}_p18_nbs.csv`
- Logs: `reports/logs/P18/` (`00_hash_before.txt`, `01`-`06` command logs, `10_check_pairwise.txt`, `11_check_cohort.txt`, `12_directions.txt` = outputs of the read-only verification scripts, `99_hash_after.txt`, `after_cmd3.txt`, `after_cmd5.txt`)

## Anomalies

- None in exit codes of the P18 commands. Pytest: 22 warnings (as in earlier phases), 1 skipped.
- The `--summary-only` header lines print "(21 edges, ...)" while the responder lines print "of 28 edges" (mixed 7- and 8-channel cohort); recorded as is, not interpreted.
- Pairwise split-half: "2 of 75 subject x method x condition cells have r <= 0" (log 05).

## Questions
