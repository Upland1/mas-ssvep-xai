# P06 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: phase/P06-feature-selection-cohort @ 7575405d2bffccc326a715b16644085cfb30898f (clean tree before each run)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (project venv), CPU, defaults

## Test suite (clean worktree `mas/state/scratch/verify_P06` at HEAD, removed afterwards)

`.venv/bin/python -m pytest tests/ -o addopts="" -q` -> `455 passed, 10 warnings in 264.82s (0:04:24)`

## Commands executed (repo root, run once each)

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 1 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20` | 2026-10-25T03:55:46-06:00 | 80 s (script: 79 s) | 0 | `reports/logs/P06/benchmark_feature_selection_20261025_035546.log` | `reports/feature_selection_ablation_S03.csv`, `.meta.txt` |
| 2 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_5_subjects` | 2026-10-25T03:57:06-06:00 | 13 s (script: 12 s) | 0 | `reports/logs/P06/benchmark_5_subjects_20261025_035706.log` | `reports/five_subjects_benchmark.csv`, `.meta.txt` |

Each log starts with the command, HEAD, start time, `git status --porcelain` (empty) and Python version; the exit code is the last line (`EXIT_CODE=0`, captured inside the piped group). Both runs are far below `LOCAL_RUN_BUDGET_MIN` (120).

## Console numbers (verbatim)

Ablation (S03; 200 stimulus windows, 197 clean, 3 rejected):
```
Full baseline                      p=55  1.0 s  90.36%  2.0 s smoothed  95.43%
Sub-band pruning (drop 38-52 Hz)   p=45  1.0 s  87.31%  2.0 s smoothed  94.92%
ANOVA F-score                      p=25  1.0 s  86.29%  2.0 s smoothed  94.42%
Mutual information                 p=25  1.0 s  87.82%  2.0 s smoothed  93.40%
Sequential forward selection       p=20  1.0 s  89.85%  2.0 s smoothed  95.94%
```
Cohort: `Cohort: 5 subjects, mean 1.0 s 83.33%, 2.0 s smoothed 87.57% (legacy leaky CV, not comparable with R-6); runtime 12 s`; per-subject rows in `reports/five_subjects_benchmark.csv`.

## Human run requests

None.
