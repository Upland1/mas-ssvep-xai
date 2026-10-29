# P23 · 05 · Run

Status: READY
Author: verifier
Reads: 00_assignment.md, 02_plan.md (Run commands, Pre-run audit additions: V1..V12, round 2 amendments of V8 and V10, PR-1..PR-9, RR-1..RR-7, Acceptance checks), 03_changes_*.md, 04_tests.md, 07_review.md (pre-run audit PASS round 2, 1be5e3c)
Branch / commit: phase/P23-gnn-loso @ a9ba18b230e751de5b590c0f59cfb96311be9c8d ("chore: P23 pre-run checks in plan"; its parent chain contains 1be5e3c). `02_plan.md` contains "Pre-run audit additions" (line 185). Clean detached worktree `mas/state/scratch/verify/P23` (data, reports, outputs, baselines and `.venv` symlinked to the main tree; `git status --porcelain` empty before and after the run, `git status --porcelain -- src scripts configs` empty).
Machine: Linux 7.0.0-38-generic x86_64, 16 logical CPUs, Python 3.12.3, torch 2.14.1+cu130 (`torch.get_num_threads()` = 12, `reports/logs/P23/torch_threads.txt`). Result runs pinned to `--threads 2 --device cpu`; no GPU used.

Data source: built continuous folders `data/processed_continuous/w1_s0.25/<S>/`, session OO, quality source both, banks fbcca and fbcsp; cohort S01-S05 (explicit `--subjects`), channels `common` (PO3, POz, PO4, PO8, O1, Oz, O2).

## Commands executed

Local time 2026-10-29. All from the worktree through `.venv/bin/python -m ...` (driver `mas/state/scratch/p23_run_steps.sh`, scratch, not committed; every command writes its log, which starts with the command line, git head and dirty count). Logs in `reports/logs/P23/`; start/end/exit lines of each step in `steps.txt`.

`P=".venv/bin/python -m"`, `M=scripts.connectivity.graph_modeling.benchmark_gnn_loso`, `C="--data-root data/processed_continuous --window 1 --stride-sec 0.25 --subjects S01 S02 S03 S04 S05 --channels common --variants nodes+F nodes+coh+F --seeds 3 --threads 2 --device cpu"`.

| # | Command | Start | Wall | Exit | Log |
|---|---|---|---|---|---|
| V1 | `ls -d reports/loso_gnn reports/within_gnn`; `git status --porcelain -- src scripts configs` | 02:10 | <1 s | ls 2 (both absent); git 0 lines | `v1_ls_before.txt` |
| 0 | sha256 of the 65 files of S01-S05 (before) | 02:10 | <1 s | 0 | `hash_before.txt`, `hash_before_files.txt` |
| T | `pytest tests/ -q -o addopts="" -p no:cacheprovider`, alone | 02:10:44 | 870.26 s in pytest (0:14:30; `/usr/bin/time` 14:32.63) | 0: `1513 passed, 22 warnings` | `pytest_full.log`, `pytest_full.time`, `pytest_full.exit` |
| 1 | `$P $M --smoke-test --out-dir mas/state/scratch/p23_verify_smoke` | 02:25:36 | 37 s | 0 | `smoke.log` |
| 2 | `$P $M $C --norm pooled --protocol within --out-dir reports/within_gnn` | 02:26:21 | 472 s (7.9 min) | 0 | `within.log` |
| 3 | `$P $M $C --norm pooled subject --protocol loso --out-dir reports/loso_gnn` | 02:34:13 | 721 s (12.0 min) | 0 | `loso.log` |
| H1 | sha256 of the six CSVs and `gnn_loso_config.json` (after step 3) | 02:46:27 | <1 s | 0 | `v8_hashes.txt` (`after_step3`) |
| 8b | step 3, unchanged, rerun | 02:46:34 | 5 s | 0 (20 `[skip]`, 0 `[+] gnn_` fold lines) | `loso_rerun_same.log` |
| 8c | step 3 with `--seeds 2` | 02:46:39 | 5 s | 1: `... configuration differs {'seeds': ([42, 43, 44], [42, 43])} (saved, now); use a new --out-dir` | `loso_rerun_seeds2.log` |
| 10a | (my mistake, see Anomalies) step 3 arguments with `--norm pooled` only, both variants | 02:46:56 | 5 s | 0 (10 `[skip]`, 0 `[+] gnn_`, 0 `left out`) | `loso_v10.log` |
| 8d | step 3, unchanged, rerun | 02:47:01 | 5 s | 0 (20 `[skip]`, 0 `[+] gnn_`) | `loso_final_rerun.log` |
| 10b | V10 as amended: step 3 arguments with `--variants nodes+F --norm pooled` | 02:47:22 | 5 s | 0 (5 `[skip]`, 0 `[+] gnn_`, 0 `left out`) | `loso_v10_correct.log` |
| 8e | step 3, unchanged, final rerun | 02:47:27 | 5 s | 0 (20 `[skip]`, 0 `[+] gnn_`) | `loso_final_rerun2.log` |
| 5 | sha256 of S01-S05 (after) | 02:48 | <1 s | 0, `cmp` identical | `hash_after.txt`, `hash_after_files.txt` |
| A | `.venv/bin/python mas/state/scratch/p23_analysis.py` (read-only: V2-V7, V9, RR-1/2, PR-1..PR-9) | 02:49 | seconds | 0 | `analysis.txt`, `v9_folds_table.md` |
| V12 | `PYTHONPATH=. .venv/bin/python mas/state/scratch/p23_v12.py` (read-only `load_subject`) | 02:51 | seconds | 0 | `v12.txt` |

Local budget used: about 14.5 min (suite) + about 21 min (steps 1-3 and checks) = about 36 min of `LOCAL_RUN_BUDGET_MIN` 120 (plan estimate 20 min, worst case 28 min for steps 2 and 3: measured 472 + 721 s = 19.9 min). GPU time: none.

S01-S05 hash (`hash_before.txt`, `hash_after.txt`, 65 files each, recipe of P21): `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4`; the file lists are byte-identical (`cmp`). V12 only read the built folders after step 5.

## V8 hashes (sha256 of the six CSVs; `gnn_loso_config.json` excluded per the amendment)

Taken after step 3, after 8b, after 8c (refused), after 10a, after 8d, after 10b and after 8e (`v8_hashes.txt`); all seven snapshots give the same value for each file:

| File | sha256 |
|---|---|
| summary.csv | 7fe2e20c98224702218ef810d0626dc0cab3bba31c13379f3cf044f6d01bbba5 |
| per_subject.csv | cd5723b783fdeddfd584415376a431fc9e678158ccf2be13908b96b57d927d64 |
| predictions.csv | cde628c406a81ab3eab92b907e06358fe7292ae29a44a9e6a4300d58c1588fcf |
| confusion.csv | 2298df89e50efc7b3091e1ff4539a809212eb6d92c666b7368133b896d5793dc |
| folds.csv | e00a93a1c1bccec62c90049f6f7a3bae9f7646bb66cbb1d2352da58782a5369d |
| seeds.csv | 21c958b8966650c17bf0035a43fa0b6ef749dc02eb914d74339ee065ad131342 |

`gnn_loso_config.json` (informative): `65efdc4d...` after step 3, 8b, 8c, 8d and 8e (the final rerun restored the all-methods description); `a37252c6...` after 10a and `1d9a2fb3...` after 10b (it records `this_invocation`, N11).

## Human run requests

None.

## Produced files

- `reports/within_gnn/` and `reports/loso_gnn/` (each: `summary.csv`, `per_subject.csv`, `predictions.csv`, `confusion.csv`, `folds.csv`, `seeds.csv`, `gnn_loso_config.json`, `folds/*.npz`: 50 and 20 files, no `*.tmp`)
- `reports/logs/P23/*` (list above)
- `mas/state/scratch/p23_run_steps.sh`, `p23_hash6.sh`, `p23_analysis.py`, `p23_v12.py`, `p23_verify_smoke/` (scratch, not committed)

## Anomalies

1. **V10 first executed with the wrong arguments (verifier error).** The driver's first V10 line reused `$C`, which carries `--variants nodes+F nodes+coh+F`, so 10a skipped 10 folds (both variants, pooled) instead of the 5 expected. It changed nothing (no fold run, no refusal, six CSV hashes unchanged). The amended V10 (`--variants nodes+F --norm pooled`) was then run as 10b: 5 `[skip]`, 0 `[+]`, no `left out`, exit 0, hashes equal, `summary.csv` holds the 4 methods (28 rows). Because 10a and 10b both rewrote `gnn_loso_config.json`, the final unchanged rerun was done after 10b (8e); 8d was the earlier one. Both final reruns: 20 `[skip]`, exit 0, six hashes unchanged.
2. **Step 3's `[+]` count.** `grep -c '^\[+\]'` on a rerun log counts also the 10 data-loading and graph-feature lines (`[+] S01: ...`); the fold lines are `[+] gnn_...` (20 in `loso.log`, 50 in `within.log`, 0 in every rerun).
3. **V5, within fold.** `build_git_commits` has 1 entry (S01, the training subject) and `n_windows_train = {S01: 680}`, because the within training set is the subject's own windows. LOSO folds have 5 entries each, as V5 requires; the "5 entries" wording of V5 cannot hold for within folds.
4. No warnings, no `[warn]` lines in the GNN logs; the suite shows the usual 22 warnings.
5. The suite's `torch.get_num_threads()` is 12 (default); the GNN steps used 2 as fixed in the fold config.

## PF-30 fold table (V9): all 70 `folds.csv` rows

Source: `reports/within_gnn/folds.csv` (50 rows) and `reports/loso_gnn/folds.csv` (20 rows); "Diagnosis" is the first words of the column (`OVERFITTING` or `no strong gap`); Train, Val, Test acc in %, Train - Test in pp. Degenerate rows (best epoch <= 5 or train < chance + 10 pp, any seed): **none** in either protocol (`degenerate` False in all 70 rows, `Degenerate seeds` 0).

| Protocol | Method | Test | Fold | Train | Val | Test acc | Train - Test | Best Epoch | Epochs Run | degenerate | Diagnosis |
|---|---|---|---|---|---|---|---|---|---|---|---|
| within | gnn_nodes+F | S01 | 0 | 89.20 | 69.14 | 68.63 | 20.57 | 110.0 | 130.3 | False | OVERFITTING |
| within | gnn_nodes+F | S01 | 1 | 90.20 | 62.46 | 68.38 | 21.81 | 121.0 | 144.3 | False | OVERFITTING |
| within | gnn_nodes+F | S01 | 2 | 90.20 | 65.55 | 72.06 | 18.14 | 95.7 | 120.7 | False | OVERFITTING |
| within | gnn_nodes+F | S01 | 3 | 88.39 | 68.35 | 75.00 | 13.39 | 123.0 | 140.7 | False | no strong gap |
| within | gnn_nodes+F | S01 | 4 | 88.84 | 66.95 | 70.59 | 18.25 | 124.7 | 145.0 | False | OVERFITTING |
| within | gnn_nodes+F | S02 | 0 | 94.92 | 76.98 | 74.26 | 20.65 | 141.7 | 150.0 | False | OVERFITTING |
| within | gnn_nodes+F | S02 | 1 | 95.69 | 71.99 | 79.10 | 16.59 | 129.7 | 147.0 | False | OVERFITTING |
| within | gnn_nodes+F | S02 | 2 | 94.20 | 75.49 | 75.19 | 19.01 | 144.3 | 150.0 | False | OVERFITTING |
| within | gnn_nodes+F | S02 | 3 | 94.86 | 73.28 | 73.11 | 21.75 | 134.7 | 147.7 | False | OVERFITTING |
| within | gnn_nodes+F | S02 | 4 | 94.37 | 76.47 | 81.15 | 13.22 | 144.3 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S03 | 0 | 99.19 | 92.19 | 94.12 | 5.08 | 146.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S03 | 1 | 99.29 | 89.63 | 84.73 | 14.56 | 125.0 | 142.3 | False | no strong gap |
| within | gnn_nodes+F | S03 | 2 | 99.67 | 89.11 | 89.71 | 9.97 | 130.7 | 139.7 | False | no strong gap |
| within | gnn_nodes+F | S03 | 3 | 99.35 | 88.87 | 89.21 | 10.14 | 137.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S03 | 4 | 99.07 | 89.47 | 94.12 | 4.95 | 129.3 | 144.3 | False | no strong gap |
| within | gnn_nodes+F | S04 | 0 | 100.00 | 98.37 | 99.26 | 0.74 | 143.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S04 | 1 | 100.00 | 98.02 | 98.53 | 1.47 | 142.3 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S04 | 2 | 100.00 | 97.74 | 100.00 | 0.00 | 145.3 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S04 | 3 | 100.00 | 98.41 | 98.55 | 1.45 | 147.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S04 | 4 | 100.00 | 98.31 | 95.80 | 4.20 | 141.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S05 | 0 | 100.00 | 98.59 | 92.65 | 7.35 | 114.7 | 139.3 | False | no strong gap |
| within | gnn_nodes+F | S05 | 1 | 100.00 | 98.60 | 99.26 | 0.74 | 109.7 | 134.7 | False | no strong gap |
| within | gnn_nodes+F | S05 | 2 | 100.00 | 97.20 | 99.26 | 0.74 | 122.7 | 145.0 | False | no strong gap |
| within | gnn_nodes+F | S05 | 3 | 100.00 | 97.19 | 98.53 | 1.47 | 142.3 | 150.0 | False | no strong gap |
| within | gnn_nodes+F | S05 | 4 | 100.00 | 98.32 | 99.26 | 0.74 | 134.7 | 145.3 | False | no strong gap |
| within | gnn_nodes+coh+F | S01 | 0 | 90.00 | 66.57 | 69.93 | 20.07 | 93.0 | 116.0 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S01 | 1 | 91.76 | 62.46 | 71.32 | 20.44 | 111.0 | 136.0 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S01 | 2 | 90.75 | 63.59 | 69.12 | 21.63 | 95.3 | 120.3 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S01 | 3 | 91.29 | 67.51 | 73.53 | 17.76 | 118.0 | 135.3 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S01 | 4 | 91.55 | 69.75 | 69.75 | 21.81 | 125.3 | 145.0 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S02 | 0 | 95.57 | 80.61 | 73.53 | 22.05 | 137.7 | 148.7 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S02 | 1 | 95.95 | 74.56 | 81.34 | 14.60 | 125.3 | 147.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S02 | 2 | 96.46 | 73.90 | 72.93 | 23.52 | 122.7 | 143.3 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S02 | 3 | 95.74 | 73.93 | 73.11 | 22.63 | 139.3 | 150.0 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S02 | 4 | 95.32 | 75.82 | 77.05 | 18.27 | 130.7 | 148.0 | False | OVERFITTING |
| within | gnn_nodes+coh+F | S03 | 0 | 99.28 | 92.19 | 95.59 | 3.69 | 142.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S03 | 1 | 99.53 | 91.92 | 85.50 | 14.03 | 124.7 | 148.7 | False | no strong gap |
| within | gnn_nodes+coh+F | S03 | 2 | 99.75 | 89.09 | 89.71 | 10.05 | 122.3 | 144.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S03 | 3 | 99.44 | 89.39 | 88.49 | 10.95 | 138.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S03 | 4 | 99.22 | 90.35 | 95.80 | 3.42 | 134.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S04 | 0 | 100.00 | 99.35 | 99.26 | 0.74 | 128.7 | 145.7 | False | no strong gap |
| within | gnn_nodes+coh+F | S04 | 1 | 100.00 | 98.59 | 99.26 | 0.74 | 148.7 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S04 | 2 | 100.00 | 99.15 | 99.26 | 0.74 | 136.3 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S04 | 3 | 100.00 | 99.07 | 98.55 | 1.45 | 148.0 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S04 | 4 | 100.00 | 98.87 | 97.48 | 2.52 | 143.3 | 150.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S05 | 0 | 100.00 | 99.44 | 94.85 | 5.15 | 133.3 | 146.0 | False | no strong gap |
| within | gnn_nodes+coh+F | S05 | 1 | 100.00 | 99.72 | 100.00 | 0.00 | 101.3 | 126.3 | False | no strong gap |
| within | gnn_nodes+coh+F | S05 | 2 | 100.00 | 97.48 | 99.26 | 0.74 | 129.0 | 145.3 | False | no strong gap |
| within | gnn_nodes+coh+F | S05 | 3 | 100.00 | 98.31 | 100.00 | 0.00 | 130.3 | 145.7 | False | no strong gap |
| within | gnn_nodes+coh+F | S05 | 4 | 100.00 | 98.88 | 100.00 | 0.00 | 133.0 | 144.0 | False | no strong gap |
| loso | gnn_nodes+F | S01 | nan | 97.99 | 94.18 | 70.15 | 27.84 | 97.0 | 122.0 | False | OVERFITTING |
| loso | gnn_nodes+F | S02 | nan | 96.32 | 92.39 | 80.90 | 15.42 | 87.7 | 112.7 | False | OVERFITTING |
| loso | gnn_nodes+F | S03 | nan | 94.32 | 88.97 | 96.37 | -2.05 | 102.7 | 127.7 | False | no strong gap |
| loso | gnn_nodes+F | S04 | nan | 94.49 | 88.52 | 99.70 | -5.21 | 94.7 | 119.7 | False | no strong gap |
| loso | gnn_nodes+F | S05 | nan | 93.97 | 90.07 | 98.97 | -5.00 | 101.3 | 126.3 | False | no strong gap |
| loso | gnn_nodes+F_subjnorm | S01 | nan | 98.07 | 94.88 | 75.15 | 22.92 | 108.3 | 133.3 | False | OVERFITTING |
| loso | gnn_nodes+F_subjnorm | S02 | nan | 95.91 | 93.32 | 81.99 | 13.93 | 70.7 | 95.7 | False | no strong gap |
| loso | gnn_nodes+F_subjnorm | S03 | nan | 93.85 | 90.32 | 96.07 | -2.22 | 65.7 | 90.7 | False | no strong gap |
| loso | gnn_nodes+F_subjnorm | S04 | nan | 94.40 | 89.46 | 99.55 | -5.15 | 89.7 | 114.7 | False | no strong gap |
| loso | gnn_nodes+F_subjnorm | S05 | nan | 93.20 | 90.45 | 98.82 | -5.62 | 78.3 | 103.3 | False | no strong gap |
| loso | gnn_nodes+coh+F | S01 | nan | 98.30 | 94.18 | 70.88 | 27.42 | 81.3 | 106.3 | False | OVERFITTING |
| loso | gnn_nodes+coh+F | S02 | nan | 96.92 | 92.64 | 79.35 | 17.58 | 93.7 | 118.7 | False | OVERFITTING |
| loso | gnn_nodes+coh+F | S03 | nan | 94.50 | 88.66 | 96.22 | -1.71 | 73.3 | 98.3 | False | no strong gap |
| loso | gnn_nodes+coh+F | S04 | nan | 94.90 | 88.33 | 99.55 | -4.65 | 82.7 | 107.7 | False | no strong gap |
| loso | gnn_nodes+coh+F | S05 | nan | 94.85 | 89.56 | 98.82 | -3.97 | 97.7 | 122.7 | False | no strong gap |
| loso | gnn_nodes+coh+F_subjnorm | S01 | nan | 98.71 | 95.13 | 74.71 | 24.01 | 104.3 | 129.3 | False | OVERFITTING |
| loso | gnn_nodes+coh+F_subjnorm | S02 | nan | 96.44 | 93.63 | 82.61 | 13.83 | 77.3 | 102.3 | False | no strong gap |
| loso | gnn_nodes+coh+F_subjnorm | S03 | nan | 94.38 | 90.62 | 95.76 | -1.38 | 64.3 | 89.3 | False | no strong gap |
| loso | gnn_nodes+coh+F_subjnorm | S04 | nan | 94.47 | 89.46 | 99.55 | -5.08 | 73.7 | 98.7 | False | no strong gap |
| loso | gnn_nodes+coh+F_subjnorm | S05 | nan | 94.65 | 90.89 | 98.82 | -4.18 | 85.0 | 110.0 | False | no strong gap |

## Questions
