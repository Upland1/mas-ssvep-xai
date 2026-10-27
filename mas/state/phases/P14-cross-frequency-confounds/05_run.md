# P14 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: phase/P14-cross-frequency-confounds @ 6b4ec212a0bb536e16e16c238fe672f9ffbcd31f (porcelain-empty before and after every command; each log header shows `STATUS_PORCELAIN: []`)
Machine: Linux 7.0.0-38-generic, 16 cores, Python 3.12 (`.venv`), CPU only. Wrapper: `mas/state/scratch/p14_run.sh` (tee into the log, writes HEAD, status, RUNTIME_S, EXIT).

Suite: clean worktree `mas/state/scratch/verify/P14` @ 6b4ec21. Pipeline commands: main repository (clean, same HEAD), because the inputs (`data/processed`, `reports/connectivity_edges`, `reports/n_subjects_benchmark.csv`) are ignored files that live there. Outputs went to `reports/connectivity_comparison/` and `outputs/figures/connectivity_comparison/` of the main repository.

## Commands executed

| # | Command | Start (UTC-6) | Runtime | Exit | Log |
|---|---|---|---|---|---|
| 0 | `.venv/bin/python -m pytest tests -o addopts="" -q` (clean worktree) | 19:58:01 | 405 s | **1** (2 failed, 871 passed, 1 skipped, 21 warnings in 402.78s) | `reports/logs/P14/pytest_full.log` |
| 0b | the 2 failed tests re-run in the main repository (supplementary, not a substitute) | | 5 s | 0 (2 passed) | `reports/logs/P14/pytest_two_failed_in_main.log` |
| 1 | hash pre-check `sha256sum reports/connectivity_edges/*.npz reports/n_subjects_benchmark.csv \| sha256sum` | before cmd 1 | <1 s | 0 | printed `804b1ced5c949644f22396ca35aa17b5090f2068654ff559c2f7b02a3649e697` (matches; recomputed after the run: identical) |
| 2 | `-m scripts.connectivity.comparison.compare_connectivity_frequencies` | | 6 s | 0 | `reports/logs/P14/cmd1_compare.log` |
| 3 | `-m scripts.connectivity.comparison.test_connectivity_frequency_differences --permutations 500 --n-jobs -1 --out-suffix p500` | | 1343 s | 0 | `reports/logs/P14/cmd2_p500.log` |
| 4 | `... --permutations 1000 --n-jobs -1` | 20:28:11 | 2702 s | 0 | `reports/logs/P14/cmd3_final.log` |
| 5 | `... --compare p500 ""` | 21:13:44 | 1 s | 0 | `reports/logs/P14/cmd4_compare_p500_final.log` |
| 6 | `-m scripts.connectivity.diagnostics.check_power_alpha_confound` | | 1 s | 0 | `reports/logs/P14/cmd5_confound.log` |
| 7 | conditional DIAG-E3 | not run | | | E3 trigger did not fire (06_verify.md, E3) |

Pipeline runtime, commands 2–6: 4053 s = 67.55 min (inside `LOCAL_RUN_BUDGET_MIN` = 120). Each command ran once.

## Human run requests

None.

## Produced files

- `reports/connectivity_comparison/` (61 files): `<m>_frequency_similarity[_groups].csv`, `<m>_node_strength[_groups].csv`, `<m>_global_delta[_groups].csv` for coherence, plv, wpli, pdc; `<m>_split_half_reliability[_p500].csv`, `<m>_split_half_details[_p500].csv`, `<m>_pairwise_tests[_p500].csv`, `<m>_pairwise_null[_p500].csv`, `<m>_pairwise_combined[_p500].csv` for coherence, plv, wpli; `pairwise_flips.csv`; `power_confound_table.csv`, `power_vs_connectivity_cells.csv`, `power_confound_correlations.csv`, `power_confound_ols.csv`, `power_confound_alpha_split.csv`, `power_confound_s05.csv`.
- `outputs/figures/connectivity_comparison/` (21 PNG): per method (4) `_frequency_similarity`, `_node_strength`, `_delta_matrices_{all,responders,non_responders}`; plus `connectivity_delta_vs_power.png`.
- Verifier scratch: `mas/state/scratch/p14_run.sh`, `p14_analysis.py`, `p14_analysis.out`, `p14_legacy_before.txt`, `p14_legacy_after.txt`.

## Anomalies

1. The clean-checkout suite exits 1: two P14 tests need the ignored generated file `reports/n_subjects_benchmark.csv` (absent in a clean worktree). See 06_verify.md, reason 1.
2. Suite runtime 6.7 min (known, review N6).
3. Pairwise p500 run 1343 s and final run 2702 s; the plan estimate of 18–34 min total was low (actual 67.6 min), still within budget.
4. Split-half: 5 of 75 subject x method x condition cells have r <= 0 (reported uncorrected; `cmd2_p500.log`). Pairwise flip list: 150 cells compared, 8 flip (`cmd4_compare_p500_final.log`).
5. Trial ids approximate for S02 and S04 (console of every run).

## Questions
