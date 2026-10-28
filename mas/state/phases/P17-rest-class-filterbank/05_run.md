# P17 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, Run-list additions 1-4), 07_review.md (pre-run audit PASS)
Branch / commit: phase/P17-rest-class-filterbank @ 59b0f10261f3dea48934d23fff05d306979144a8 (porcelain status empty in every log header; the only untracked entry in the pytest worktree was the `.venv` link)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (`.venv`), CPU only, no GPU

## Commands executed

All from the repository root at HEAD except the suite (clean worktree `mas/state/scratch/verify/P17`, removed afterwards). Each log starts with the command line, commit, porcelain status, Python version and start time, and ends with `exit=` and runtime. Logs are under `reports/logs/P17/` (suffix = UTC timestamp).

| # | Command (abridged) | Runtime | Exit | Log (prefix) | Outputs |
|---|---|---|---|---|---|
| 0 | `.venv/bin/python -m pytest tests/ -q -o addopts=""` (worktree) | 674.59 s | 0 | `pytest_full_20261028T081533Z.log` | `1166 passed, 1 skipped, 22 warnings` |
| 1a | item 1 pre-run state + P16 root hash | 0 s | 0 | `item1_prerun_hash_20261028T082701Z.log` | `data/processed_continuous_p17` absent; `ls reports | grep -c p17` = 0; 65 files; hash `c59c94b8ac90a77f57148f057698411f97690ec1174b1202237b37624144a54e` |
| 1 | step 1 `scripts.build_windows ... --banks fbcca fbcsp harmonic intermediate --out-root data/processed_continuous_p17` | 4 s | 0 | `step1_build_windows_20261028T082706Z.log` | `data/processed_continuous_p17/S01..S05` (15 files each) |
| 2 | item 2 (D2) | 0 s | 0 | `item2_D2_20261028T082722Z.log` | table below |
| 3 | item 3 (D1) | 0 s | 0 | `item3_D1_20261028T082722Z.log` | table below |
| 4 | item 4 (D0) `--cv-repeats 5 --bank base --classes 5 --out-suffix p17_diag_base_5class_rep5` | 15 s | 0 | `item4_D0_20261028T082731Z.log` | `reports/n_subjects_benchmark_p17_diag_base_5class_rep5.csv` (+ `.meta.txt`) |
| 5 | step 2 `--bank base --classes 5` | 19 s | 0 | `step2_p17_base_5class_20261028T082746Z.log` | `reports/n_subjects_benchmark_p17_base_5class.csv` |
| 6 | step 3 `--bank base --classes 6` | 28 s | 0 | `step3_p17_base_6class_20261028T082805Z.log` | `..._p17_base_6class.csv`, `..._6class_confusion.csv` |
| 7 | step 4 `--bank harm --classes 5` | 50 s | 0 | `step4_p17_harm_5class_20261028T082833Z.log` | `..._p17_harm_5class.csv` |
| 8 | step 5 `--bank harm --classes 6` | 72 s | 0 | `step5_p17_harm_6class_20261028T082923Z.log` | `..._p17_harm_6class.csv`, `_confusion.csv` |
| 9 | step 6 `--bank harm+mid --classes 5` | 57 s | 0 | `step6_p17_harmmid_5class_20261028T083035Z.log` | `..._p17_harmmid_5class.csv` |
| 10 | step 7 `--bank harm+mid --classes 6` | 83 s | 0 | `step7_p17_harmmid_6class_20261028T083132Z.log` | `..._p17_harmmid_6class.csv`, `_confusion.csv` |
| 11 | item 1 hash after the last step | 0 s | 0 | `item1_posthash_20261028T083302Z.log` | 65 files, hash `c59c94b8...a54e` (equal); porcelain empty |

Total wall about 18 min (suite 11.2 min + runs 5 min) of `LOCAL_RUN_BUDGET_MIN` 120.

### D2 (verbatim, `item2_D2_20261028T082722Z.log`)

```
done
S01 guard 231 268 valid 320 320 stim 200 200 rest 80 80 p17-only 0 stim mask equal True
S02 guard 231 268 valid 301 301 stim 190 190 rest 74 74 p17-only 0 stim mask equal True
S03 guard 231 268 valid 310 310 stim 194 194 rest 77 77 p17-only 0 stim mask equal True
S04 guard 231 268 valid 309 307 stim 195 195 rest 76 75 p17-only 0 stim mask equal True
S05 guard 231 268 valid 319 319 stim 199 199 rest 80 80 p17-only 0 stim mask equal True
```

### D1 (verbatim, `item3_D1_20261028T082722Z.log`)

```
S01 min gap between windows of different trials (s): 2.969
S02 ... S05: 2.969 (identical line for each)
```

## Human run requests

None.

## Produced files

- `data/processed_continuous_p17/S01..S05/` (git-ignored); P16 root untouched.
- `reports/n_subjects_benchmark_p17_{base,harm,harmmid}_{5,6}class.csv` and `.meta.txt` (six pairs).
- `reports/n_subjects_benchmark_p17_{base,harm,harmmid}_6class_confusion.csv` (three).
- `reports/n_subjects_benchmark_p17_diag_base_5class_rep5.csv` and `.meta.txt` (D0).
- `reports/logs/P17/*.log` (13 logs).

## Anomalies

- None in exit codes or warnings of the runs. The suite reports 1 skipped test (not in `tests/test_p17_leak_controls.py`, which has 12 collected tests; no skip marker in that file).
- Valid-window counts differ from P16 only on S04 (309 -> 307: 2 rest windows removed by the longer guard; stimulus windows unchanged).
- Runs are far below the estimate for the six benchmarks (about 5 min against 6-30 min).

## Questions

None.
