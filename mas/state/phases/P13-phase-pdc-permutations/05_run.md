# P13 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, amended), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: phase/P13-phase-pdc-permutations @ 7f6cabb30d63d4059898fa3b4437d922960c58f6
Machine: Linux 7.0.0-38-generic, 12th Gen Intel Core i5-12500H (16 logical CPUs), Python 3.12.3, numpy 2.5.4, scipy 1.18.1, CPU only.
Clean checkout: `mas/state/scratch/verify/P13` (detached worktree at the HEAD above). Its `data`, `reports` and `.venv` are symlinks to the main repository, so every output landed in the main repository's `reports/`. The only entries in `git status --porcelain` of the worktree are those three symlinks (`?? .venv`, `?? data`, `?? reports`); with `--untracked-files=no` the status is empty (0 lines) after all runs.

## Commands executed

Each command ran once, in the listed order, through `mas/state/scratch/verify/runlog.sh` (header with command, HEAD, porcelain status and START; footer with END and EXIT; output tee'd into the log). All logs are under `reports/logs/P13/`. Times are local clock (UTC-6).

| # | Command | Start | Runtime | Exit | Log |
|---|---|---|---|---|---|
| 0 | `.venv/bin/python -m pytest tests -o addopts="" -q` | 17:56 | 6 min 04 s | 0 | `reports/logs/P13/pytest_full.log` (`796 passed, 21 warnings in 363.52s`) |
| 1 | `-m scripts.connectivity.diagnostics.demo_hilbert_edges` | 18:02:49 | < 1 s | 0 | `reports/logs/P13/c1_demo_hilbert.log` |
| 2 | `-m scripts.connectivity.diagnostics.demo_mvar_slicing` | 18:02:50 | 1 s | 0 | `reports/logs/P13/c2_demo_mvar.log` |
| 3 | `analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit window --n-jobs -1 --out-suffix window200` | 18:02:51 | 5 min 35 s | 0 | `reports/logs/P13/c3_window200.log` |
| 4 | `... --permutations 100 --permutation-unit trial --n-jobs -1 --out-suffix trial100` | 18:08:26 | 3 min 01 s | 0 | `reports/logs/P13/c4_trial100.log` |
| 5 | `... --permutations 200 --permutation-unit trial --n-jobs -1` (final, unsuffixed) | 18:11:27 | 5 min 46 s (printed total 345.1 s) | 0 | `reports/logs/P13/c5_trial200_final.log` |
| 6 | `... --compare trial100 ""` | 18:17:13 | 1 s | 0 | `reports/logs/P13/c6_compare_trial100.log` |
| 7 | `... --compare window200 ""` | 18:17:14 | 1 s | 0 | `reports/logs/P13/c7_compare_window200.log` |
| 8 | `... --methods coherence --subjects S03 --permutations 200 --permutation-unit trial --coherence-estimator aligned --n-jobs -1 --out-suffix aligned_S03` | 18:17:15 | 39 s | 0 | `reports/logs/P13/c8_aligned_S03.log` |

Total of commands 1-8: 15 min 05 s (18:02:49 to 18:17:54), against `LOCAL_RUN_BUDGET_MIN` = 120. Every log carries `HEAD: 7f6cabb30d63d4059898fa3b4437d922960c58f6`. The `STATUS(porcelain)` header lists only the three symlinks above.

Legacy arrays (S01-S05 `X_psd_features.npy`, `X_time_windows.npy`, `y_labels.npy`): sha256 before (`reports/logs/P13/legacy_sha256_before.txt`) and after (`reports/logs/P13/legacy_sha256_after.txt`), `diff` of the two files prints nothing (identical, 15 files).

| File | sha256 (before = after) |
| `data/processed/S01/X_psd_features.npy` | `45a9b0332d257a7364c2fb8e9bca3264dbaf43f1af9d029ac22f513610181d53` |
| `data/processed/S01/X_time_windows.npy` | `241adcdcc438fe3f6263e91a8c583ebd33ec76c1fbe0b12f07725a544ace1d15` |
| `data/processed/S01/y_labels.npy` | `1846c4e5b4faabb3149e448bcdc2ffbaa77da29a560e111b8a8be7eed2ea62ea` |
| `data/processed/S02/X_psd_features.npy` | `9c2ff184b6c0791e86a223e93f9978da1b92cd303ce89884879dd9d179edeae7` |
| `data/processed/S02/X_time_windows.npy` | `1ad628ad2119e36b2ebd52f9db70448ee8a9a75100abe997ebf11f74e198219f` |
| `data/processed/S02/y_labels.npy` | `37c0f53c5c4a9949182a93fc5bd7f67756b48651fd9d121ad648a86625662ab6` |
| `data/processed/S03/X_psd_features.npy` | `51262dccc970a5d148330a622cee54e8af6584759fd591f86c0eb518734da972` |
| `data/processed/S03/X_time_windows.npy` | `88e9a294b668e5b5631430ccce2fae1df03b32dc7075e24726eff96a9fe7541e` |
| `data/processed/S03/y_labels.npy` | `112c8507c38f2193a5bd7dbf8fc72d5d46f1662e6b0ecbb6f17442a6525d5c4c` |
| `data/processed/S04/X_psd_features.npy` | `eb6ef0fbc96c47df7606827821c03d8a2c4b13912a99a277b69acfa3c0bce7b2` |
| `data/processed/S04/X_time_windows.npy` | `d9dbca887edfdd827edec5aa093fb7503fe0958561cff6946d6a27d96dea85c1` |
| `data/processed/S04/y_labels.npy` | `cebc9c5858b6f90f4a53be13f46967929f0419442cf7b1cf70ee5509af5f44ac` |
| `data/processed/S05/X_psd_features.npy` | `9400ebfd5057a2235bd88bfbfdfda36e9cb02bc9ff7b78abc55e5f821a518df9` |
| `data/processed/S05/X_time_windows.npy` | `d41793f3ed5a6e3594f2cea2b00c02fc72c50135ab62157ecd1751ede7241b0e` |
| `data/processed/S05/y_labels.npy` | `1846c4e5b4faabb3149e448bcdc2ffbaa77da29a560e111b8a8be7eed2ea62ea` |

## Human run requests

None.

## Produced files

Main repository `reports/` (ignored by git):
- `connectivity_cohort_summary.csv` (+ `_details.csv`), `connectivity_alpha_diagnostic.csv`, `connectivity_edges/` (20 npz, one per subject x method): final trial200.
- `connectivity_cohort_summary_window200.csv` (+ `_details`), `connectivity_alpha_diagnostic_window200.csv`, `connectivity_edges_window200/`.
- `connectivity_cohort_summary_trial100.csv` (+ `_details`), `connectivity_alpha_diagnostic_trial100.csv`, `connectivity_edges_trial100/`.
- `connectivity_cohort_summary_aligned_S03.csv` (+ `_details`), `connectivity_alpha_diagnostic_aligned_S03.csv`, `connectivity_edges_aligned_S03/`.
- `connectivity_cohort_flips.csv` (trial100 vs final), `connectivity_cohort_flips_window200_vs_final.csv`.
- `connectivity/hilbert_edges_demo.csv` (+ `.meta.txt`), `connectivity/mvar_slicing_demo.csv` (+ `.meta.txt`).
- `logs/P13/*.log`, `logs/P13/legacy_sha256_{before,after}.txt`.

Scratch (not committed): `mas/state/scratch/verify/{runlog.sh,runall.sh,analyze.py,runall.out}`.

## Anomalies

- Worktree porcelain is not literally empty because `data`, `reports`, `.venv` are symlinks into the main repository (untracked entries); tracked files are unchanged.
- Log headers and `--compare` commands print `""` as an empty argument (the CMD line shows the command with the quotes consumed by the shell).
- No warnings or errors in logs 1-8. The `details` CSV has an empty `coherence_estimator` for the non-coherence rows.
- The npz keys are per condition (`channels_kept`, `stim_<cond>`, `base_<cond>`, `diff_<cond>`, `p_<cond>`, `fdr_<cond>`), not the `stim_c` shorthand of 07_review.md.

## Questions

None.
