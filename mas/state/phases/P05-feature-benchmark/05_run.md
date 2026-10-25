# P05 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: `phase/P05-feature-benchmark` @ e47e799e779a718945398274e67a130ec698c57f (clean tree before the runs; `git status --porcelain` empty in every log header)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (`.venv`), CPU only, defaults (`--fs 250`, `--seed 42`, `--m 1`), figures on.

## Clean-checkout test run

Worktree `mas/state/scratch/verify_P05` @ e47e799 (removed afterwards), `data` and `.venv` symlinked.
`python -m pytest tests/ -p no:warnings -o addopts="" -q` (file `mas/state/scratch/pytest_P05_verify.txt`):
`413 passed in 120.23s (0:02:00)`, exit 0.

## Commands executed

Launcher: `mas/state/scratch/run_P05.sh` (`set -o pipefail`; each project command wrapped as `{ echo "$ cmd"; git rev-parse HEAD; start; git status --porcelain; python -V; cmd; } 2>&1 | tee log`, exit code from `PIPESTATUS[0]`; summary in `mas/state/scratch/run_P05_summary.txt`). Every command was run once, from the repo root, starting 2026-10-24T23:44:34-06:00.

| # | Command (prefix `.venv/bin/python -m`) | Runtime | Exit | Log (`reports/logs/P05/`) |
|---|---|---|---|---|
| 1 | `scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03` | 14 s | 0 | `benchmark_cross_validation_S03_20261024T234434.log` |
| 2 | `scripts.benchmarks.feature_based.benchmark_harmonic_fbcca --subject S03` | 5 s | 0 | `benchmark_harmonic_fbcca_S03_20261024T234448.log` |
| 3 | `scripts.evaluation.test_sklearn_models --subject S03` | 13 s | 0 | `test_sklearn_models_S03_20261024T234453.log` |
| 4 | `scripts.evaluation.evaluate_confusion_matrix --subject S03` | 7 s | 0 | `evaluate_confusion_matrix_S03_20261024T234506.log` |
| 5 | `scripts.evaluation.evaluate_confusion_matrix --subject S03 --m 2` | 6 s | 0 | `evaluate_confusion_matrix_S03_m2_20261024T234513.log` |
| 6 | `scripts.evaluation.evaluate_confusion_matrix --subject S01` | 6 s | 0 | `evaluate_confusion_matrix_S01_20261024T234519.log` |
| 7 | `scripts.evaluation.evaluate_confusion_matrix --subject S02` | 6 s | 0 | `evaluate_confusion_matrix_S02_20261024T234525.log` |
| 8 | `scripts.evaluation.evaluate_confusion_matrix --subject S04` | 5 s | 0 | `evaluate_confusion_matrix_S04_20261024T234531.log` |
| 9 | `scripts.evaluation.evaluate_confusion_matrix --subject S05` | 6 s | 0 | `evaluate_confusion_matrix_S05_20261024T234536.log` |
| 10 | `scripts.exploration.visualize_data --subject S03` | 6 s | 0 | `visualize_data_S03_20261024T234542.log` |

Total about 74 s, far below `LOCAL_RUN_BUDGET_MIN` (120). No human-run request.

## Key console numbers (verbatim from the logs)

- #1: `Cohort: 1 subject (S03), 55 rows, 0 model failures; best FBCSP + FBCCA (in-fold) / Shrinkage-LDA eigen 90.36% / 95.94%; runtime 14 s`; `FBCCA argmax (zero-training) p=5 argmax 1.0 s 48.73% 2.0 s smoothed 51.78%`.
- #2: `S03 Harmonic PSD + FBCCA -> Shrinkage-LDA lsqr; ... out-of-fold 1.0 s accuracy 74.11%, 2.0 s smoothed 86.29%; clean windows 197, rejected 3`.
- #3: `Cohort: 1 subject (S03), 28 model x space rows, 2 failures (Continuous PSD/QDA, FBCSP (in-fold)/QDA); runtime 11 s`.
- #4: `[+] S03: 200 stimulus windows, 197 clean, 3 rejected; FBCSP + FBCCA (in-fold), m=1, p=55 (FBCSP 50 + FBCCA 5)`; `Shrinkage-LDA lsqr: 1.0 s 90.36%  2.0 s smoothed 95.94% (legacy no-reset)`; `DIAGNOSTIC only (not the reported number): trial-aware j%5 smoothing 95.43%`; report line `101 (24 Hz) 0.8537 0.8974 0.8750 39`.
- #5: `m=2, p=105`: `1.0 s 92.89%  2.0 s smoothed 96.95%`; j%5 diagnostic 95.94%.
- #6-#9: see `06_verify.md`, section S01-S05.
- #10: `fbcsp: X (200, 50) (50 features (full-data CSP, visualization only)`; `Cohort: 1 subjects plotted, 0 skipped (none); mask kept 317, rejected 0; PSD fs 250 Hz (legacy)`.

## Outputs written (git-ignored)

- `reports/feature_space_benchmark_S03.csv` (55 rows), `reports/feature_space_benchmark_S03.meta.txt`, `reports/sklearn_suite_S03.csv`
- `reports/flagship_S01.csv` ... `flagship_S05.csv` (S03: rows m = 1, 2)
- `reports/classification_report_benchmark_harmonic_fbcca_S03.txt`, `reports/classification_report_evaluate_confusion_matrix_S0{1..5}.txt`, `..._S03_m2.txt`
- `outputs/figures/confusion_matrices/cm_harmonic_fbcca_cv[_S03].png`, `cm_fbcsp_m1_fbcca_cv[_S0x].png`, `cm_fbcsp_m2_fbcca_cv[_S03].png`
- `outputs/figures/exploration/S03/{psd,fbcca,fbcsp}_features_by_class.png`
- Logs: 10 files in `reports/logs/P05/`.

## Human run requests

None.
