# P16 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, amended), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: `phase/P16-continuous-filtering` @ bb8c999 (clean tree, `git status --porcelain` empty at every command)
Machine: Linux 7.0.0-38-generic x86_64, Python 3.12.3 (`.venv`), Intel i5-12500H (16 threads), CUDA available (not used by P16 commands)

All commands run once, in plan order, from the repository root at HEAD (real `data/processed_per_window/`,
`data/processed_continuous/`, `reports/`, `outputs/`, `baselines/`). `P=.venv/bin/python -m`. Command 1 ran first,
before any other writer; its log was written to `mas/state/scratch/p16_freeze.log` and copied to
`reports/logs/P16/01_freeze_baseline.log` after it exited. Each log starts with CMD, HEAD, PORCELAIN, START and ends with EXIT, END.
Extra executions (not phase commands, read-only checks): command 1 repeated verbatim once to test refusal (exit 1, below);
full pytest on a clean `git worktree` of bb8c999 (log `reports/logs/P16/00_pytest_full.log`).

## Commands executed

Date 2026-10-27, local time (UTC-6). Logs in `reports/logs/P16/`.

| # | Command (module after `P`; flags abbreviated only where identical to 02_plan.md) | Start | Runtime | Exit | Log |
|---|---|---|---|---|---|
| 1 | `scripts.freeze_baseline --tag v1 --configs-git-rev 97a29be --note "Era A/B outputs before P16 (main 97a29be)"` | 23:23:07 | ~1 s | 0 | `01_freeze_baseline.log` |
| 2 | `scripts.diagnostics.demo_edge_effects --subject S03` | 23:23:27 | 2 s | 0 | `02_scripts.diagnostics.demo_edge_effects.log` |
| 3 | `scripts.build_windows --filter-mode per_window --subjects S01..S05 --session OO --check-legacy-starts` | 23:23:29 | 3 s | 0 | `03_scripts.build_windows.log` |
| 4 | `scripts.build_windows --filter-mode continuous ... --check-legacy-starts` | 23:23:32 | 3 s | 0 | `04_scripts.build_windows.log` |
| 5 | `benchmark_n_subjects --out-suffix v1check` | 23:23:35 | 12 s | 0 | `05_scripts.benchmarks.feature_based.benchmark_n_subjects.log` |
| 6 | `analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1 --out-suffix v1check` | 23:23:47 | 5 min 28 s | 0 | `06_scripts.connectivity.analysis.analyze_connectivity_cohort.log` |
| 7 | `benchmark_n_subjects --cv-repeats 5 --out-suffix v1rep5` (row a) | 23:29:15 | 16 s | 0 | `07_...benchmark_n_subjects.log` |
| 8 | `... --fs 256 --cv-repeats 5 --out-suffix v1fs256` (row a') | 23:29:31 | 17 s | 0 | `08_...` |
| 9 | `... --fs 256 --smoothing trial --cv-repeats 5 --out-suffix v1fs256trial` (row a't) | 23:29:48 | 17 s | 0 | `09_...` |
| 10 | `... --data-root data/processed_per_window --quality shared --cv-repeats 5 --out-suffix v2pw` (row b) | 23:30:05 | 15 s | 0 | `10_...` |
| 11 | `... --data-root data/processed_continuous --quality shared --cv-repeats 5 --out-suffix v2cont` (row c) | 23:30:20 | 16 s | 0 | `11_...` |
| 12 | `... --data-root data/processed_continuous --quality shared-no-guard --cv-repeats 5 --out-suffix v2cont_noguard` (row c') | 23:30:36 | 15 s | 0 | `12_...` |
| 13 | `analyze_connectivity_cohort ... --fs 256 --out-suffix v1fs256` | 23:30:51 | 5 min 40 s | 0 | `13_scripts.connectivity.analysis.analyze_connectivity_cohort.log` |
| 14 | `analyze_connectivity_cohort ... --data-root data/processed_per_window --quality shared --out-suffix v2pw` | 23:36:31 | 6 min 25 s | 0 | `14_...` |
| 15 | `analyze_connectivity_cohort ... --data-root data/processed_continuous --quality shared --out-suffix v2cont` | 23:42:56 | 6 min 28 s | 0 | `15_...` |
| 16 | `analyze_connectivity_cohort ... --data-root data/processed_continuous --quality shared-no-guard --out-suffix v2cont_noguard` | 23:49:24 | 6 min 33 s | 0 | `16_...` |
| 17 | `scripts.diagnostics.compare_v1_v2 --check-regression` | 23:55:57 | < 1 s | **1** | `17_scripts.diagnostics.compare_v1_v2.log` |
| 18 | `scripts.diagnostics.compare_v1_v2` | 23:55:57 | < 1 s | 0 | `18_scripts.diagnostics.compare_v1_v2.log` |
| - | `pytest tests -o addopts= -q -p no:cacheprovider` (clean worktree) | 23:56:18 | 10 min 14 s | 0 | `00_pytest_full.log` |

Total phase commands about 33 min plus suite 10 min; `LOCAL_RUN_BUDGET_MIN` 120 not approached.

Flags were exactly those of the amended list; none differed from the handoffs.

## Human run requests

None.

## Produced files

Paths only (all git-ignored).
- `baselines/v1_2026-10-27/` (MANIFEST.json, baseline_summary.csv, configs/, data/, outputs/, reports/, superseded/), read-only.
- `reports/edge_effects_summary.csv`, `outputs/figures/edge_effects/edge_effects_S03.png`.
- `data/processed_per_window/S01..S05/`, `data/processed_continuous/S01..S05/` (13 files each, incl. `windows_meta.json`, `valid_mask.npy`, `valid_mask_no_guard.npy`).
- `reports/n_subjects_benchmark_{v1check,v1rep5,v1fs256,v1fs256trial,v2pw,v2cont,v2cont_noguard}.csv` (+ `.meta.txt`).
- `reports/connectivity_cohort_summary_{v1check,v1fs256,v2pw,v2cont,v2cont_noguard}.csv`, `..._details.csv`, `reports/connectivity_alpha_diagnostic_*.csv`, `reports/connectivity_edges_*/`.
- `reports/v1_vs_v2/flagship.csv`, `connectivity.csv`, `v1_vs_v2.md`.
- `reports/logs/P16/00..18_*.log`.

## Anomalies

1. Command 17 exited 1 (see 06_verify.md, criterion 2): `connectivity_edges: 5/20 npz files equal per key`. The 15 "different" files are the coherence, PLV and wPLI ones, whose 7x7 matrices carry a NaN diagonal. A NaN-aware comparison (below) finds all 20 files equal.
2. The full suite shows `1088 passed, 1 skipped`; the tester/reviewer counted 1089 passed. The skip is `tests/test_p14_connectivity_comparison.py::test_responders_real_benchmark_if_present`, which skips when `reports/n_subjects_benchmark.csv` is absent (a clean checkout has no `reports/`). It reads an ignored file (P14 D-5 pattern).
3. Tier-1 QC dropped PO7 in S01, S03 and S04 (not S02, S05) in both builds (`windows_meta.json`). The reviewer's note mentioned S03 only.
4. No warnings or errors in any command log.

## Questions

None.

## Round 2 re-verification

HEAD 215bf44 (clean tree). Commands 1-16 outputs unchanged. Logs with `_r2` suffix in `reports/logs/P16/`; first-run logs kept.

| # | Command | Start | Runtime | Exit | Log |
|---|---|---|---|---|---|
| 17 | `scripts.diagnostics.compare_v1_v2 --check-regression` | 2026-10-28 00:29:39 | < 1 s | 0 | `17_scripts.diagnostics.compare_v1_v2_r2.log` |
| 18 | `scripts.diagnostics.compare_v1_v2` | 2026-10-28 00:29:39 | < 1 s | 0 | `18_scripts.diagnostics.compare_v1_v2_r2.log` |
| - | `pytest tests -o addopts= -q -p no:cacheprovider` (clean worktree of 215bf44, removed after) | 00:29:30 | 10 min 13 s | 0 | `00_pytest_full_r2.log` |

Command 18 rewrote `reports/v1_vs_v2/{flagship,connectivity}.csv`; both are byte-identical (`cmp`) to the first-run copies.
