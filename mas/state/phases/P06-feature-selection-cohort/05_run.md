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

## Diagnostic run (investigation round 1)

Diagnostics only; the verdict above is unchanged. Command (repo root, HEAD 7de11cea6518cfc53cdb1a2ffaad1a181f57dabd, clean tree, start 2026-10-25T04:35:43-06:00, exit 0, runtime 674 s):
`.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20 --sfs-diagnostics --n-jobs 8`
Log: `reports/logs/P06/benchmark_feature_selection_diag_20261025_043543.log`. Outputs: `reports/feature_selection_ablation_S03.csv`, `reports/feature_selection_sfs_diagnostics_S03.csv`, `reports/feature_selection_sfs_audit_S03.csv`.

(a) Reported rows (console, verbatim): Full 55 90.36/95.43; pruning 45 87.31/94.92; ANOVA 25 86.29/94.42; MI 25 87.82/93.40; SFS 20 89.85/95.94. `cmp` of the rewritten reports/feature_selection_ablation_S03.csv against the first run's copy: identical.

(b) reports/feature_selection_sfs_diagnostics_S03.csv (all labelled "DIAGNOSTIC (P06 round 1), not a reported result"; windows = round(acc*1.97)):

| Variant | p | 1.0 s (%) | windows | in 165-169 | 2.0 s (%) | windows | in 182-186 |
|---|---|---|---|---|---|---|---|
| reported | 20 | 89.85 | 177 | no | 95.94 | 189 | no |
| cv=3 | 20 | 87.82 | 173 | no | 93.91 | 185 | yes |
| cv=10 | 20 | 88.32 | 174 | no | 94.92 | 187 | no |
| cv=3 shuffled | 20 | 87.82 | 173 | no | 95.43 | 188 | no |
| cv=5 shuffled | 20 | 87.82 | 173 | no | 95.43 | 188 | no |
| cv=10 shuffled | 20 | 88.83 | 175 | no | 95.43 | 188 | no |
| plain LDA svd | 20 | 87.31 | 172 | no | 95.94 | 189 | no |
| Shrinkage-LDA no scaler | 20 | 89.85 | 177 | no | 95.94 | 189 | no |
| all 55 columns, n=20 | 20 | 84.26 | 166 | yes | 90.86 | 179 | no |
| n=20 FBCSP columns | 25 | 89.85 | 177 | no | 94.92 | 187 | no |

No variant lands in both R-4 SFS ranges. Only "all 55 columns, n=20" (166 windows) lands in the 1.0 s range, and its 2.0 s value (179) is outside; only "cv=3" (185 windows) lands in the 2.0 s range, with its 1.0 s value (173) outside.

(c) reports/feature_selection_sfs_audit_S03.csv (assertions passed):

| Fold | SFS rows | Test rows | Disjoint | Test rows found in SFS input | Selected FBCSP columns |
|---|---|---|---|---|---|
| 1 | 157 | 40 | True | 0 | 3 8 9 14 15 17 20 23 25 27 30 38 41 47 48 |
| 2 | 157 | 40 | True | 0 | 0 1 2 7 9 14 19 20 21 23 32 40 46 47 48 |
| 3 | 158 | 39 | True | 0 | 0 3 5 6 9 14 16 17 20 23 27 36 41 43 45 |
| 4 | 158 | 39 | True | 0 | 3 8 9 18 21 22 25 26 30 33 36 37 42 45 47 |
| 5 | 158 | 39 | True | 0 | 2 9 11 12 21 24 26 30 32 35 36 42 43 44 45 |
