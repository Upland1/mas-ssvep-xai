# P22 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, Pre-run audit additions PR-1..PR-7 and V1..V11, Acceptance checks), 07_review.md (pre-run audit PASS, round 2, a120f0b), 03_changes_ml-engineer.md, 04_tests.md
Branch / commit: phase/P22-loso-extensions @ 461ef330d1ca145c8375e4b059b4bc529244c135 (HEAD "chore: P22 pre-run checks in plan"), clean detached worktree `mas/state/scratch/verify/P22` (the data, reports, outputs, baselines and `.venv` folders are symlinked to the main tree and excluded in the worktree; `git status --short` empty). The worktree was created after the orchestrator's note that the plan additions were committed; it is at the final HEAD.
Machine: Linux 7.0.0-38-generic x86_64, 16 logical CPUs, Python 3.12.3, torch 2.14.1+cu130, scikit-learn 1.9.1, numpy 2.5.4. `torch.get_num_threads()` = 12 (`reports/logs/P22/torch_threads.txt`). Every command ran with `CUDA_VISIBLE_DEVICES=""` (classical, CPU only, no GPU use).

Data source: built continuous folders `data/processed_continuous/w1_s0.25/<S>/`, session OO, quality source both, banks fbcca fbcsp; cohort S01-S05 (explicit `--subjects`; the folder also holds S06-S040, not used).

## Commands executed

All from the worktree, via `.venv/bin/python -m ...`, stdout+stderr redirected to the log inside the command. Logs in `reports/logs/P22/`. Local time, 2026-10-28.

| # | Command (arguments exactly as in 02_plan.md) | Start | Wall | Exit | Log |
|---|---|---|---|---|---|
| T | `pytest tests/ -q -o addopts=""`, alone | 23:12:44 | 800.46 s in pytest (0:13:20; `/usr/bin/time` 13:22.15) | 0: `1433 passed, 8 skipped, 22 warnings` | `pytest_full.log`, `pytest_full.time`, `pytest_full.exit` |
| V2 | `ls -d` of the four out-dirs | 23:26:14 | <1 s | 2 (all four absent) | `v2_ls_before.txt` |
| 0 | sha256 of S01-S05 built folders (before) | 23:26:15 | <1 s | 0 | `hash_before.txt` |
| 1 | `benchmark_loso ... --methods fbcca lda lda_subjnorm within_lda --channels common --folds 5 --within-repeats 5 --out-dir reports/loso_w1_p22_common` | 23:26:15 | 23.79 s | 0 | `loso_cmd1_common.log` |
| V5a | sha256 of every file of `reports/loso_w1_p22_common` (before, after command 1) | 23:26:46 | <1 s | 0 | `v5_hash_before.txt` (26 files) |
| 2 | same with `--channels all --out-dir reports/loso_w1_p22_all` | 23:26:46 | 29.47 s | 0 | `loso_cmd2_all.log` |
| 3 | same with `--channels PO7 PO3 POz PO4 PO8 O1 Oz O2 --out-dir reports/loso_w1_p22_names` | 23:27:15 | 8.82 s | 0 | `loso_cmd3_names.log` |
| 4a | command 1 with `--seed 43`, same out-dir | 23:27:24 | about 3 s | 1 (refused) | `loso_cmd4_seed43_refusal.log` |
| 4b | command 1 with `--within-repeats 3`, same out-dir | 23:27:27 | about 2 s | 1 (refused) | `loso_cmd4_repeats3_refusal.log` |
| 4c | command 1 unchanged, same out-dir | 23:27:29 | 2.51 s | 0 | `loso_cmd4_rerun_unchanged.log` |
| 5 | `benchmark_loso_warmup ... --warmup-trials 1 2 5 10 --channels common --out-dir reports/loso_warmup` | 23:27:35 | 5.79 s | 0 | `warmup_cmd5.log` |
| 6 | sha256 of S01-S05 built folders (after) | 23:27:42 | <1 s | 0 | `hash_after.txt` |
| A | `.venv/bin/python mas/state/scratch/verify/analysis_p22.py` (read-only checks V1, V3, V6-V10, PR-1..PR-7) | 23:28 | seconds | 0 | `analysis.txt` |

Start times of 4a, 4b, 4c, 5 are taken from log modification times minus wall (4a and 4b walls were not timed separately; "about" values are bounded by the mtime gaps). Local budget used: about 13.4 min (suite) + about 1.2 min (commands) of `LOCAL_RUN_BUDGET_MIN` 120. GPU time: none.

Hash (`hash_before.txt`, `hash_after.txt`, 65 files each): `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4`.

## Human run requests

None.

## Produced files

- `reports/loso_w1_p22_common/`, `reports/loso_w1_p22_all/`, `reports/loso_w1_p22_names/` (each: `summary.csv`, `per_subject.csv`, `predictions.csv`, `confusion.csv`, `folds.csv`, `loso_config.json`, `folds/*.npz`)
- `reports/loso_warmup/` (`summary.csv`, `cohort.csv`, `recording_order.csv`, `warmup_config.json`)
- `reports/logs/P22/*` (list above)
- `mas/state/scratch/verify/analysis_p22.py` (scratch, not committed)

## Anomalies

- 8 tests skipped in the suite (1433 + 8 = 1441 collected, the tester's count); the run had `CUDA_VISIBLE_DEVICES=""`. Skip reasons were not inspected beyond the count.
- No `[warn]`, `INCOMPLETE`, traceback or `.tmp` file in any P22 log or CSV (the two refusal logs end in the intended `[x]` line).
- Results are in `06_verify.md`; nothing is interpreted here.

## Questions
