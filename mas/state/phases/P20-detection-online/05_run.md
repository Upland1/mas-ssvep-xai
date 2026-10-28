# P20 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, Pre-run audit additions A-I, S, P1-P6, R-P1-R-P12), 07_review.md (pre-run audit PASS)
Branch / commit: phase/P20-detection-online @ 5d9326d (clean detached worktree `mas/state/scratch/verify/P20`; `data/`, `reports/`, `outputs/`, `.venv` linked, so outputs land in the main tree)
Machine: Linux 7.0.0-38-generic x86_64, Python 3.12.3, torch 2.14.1+cu130 (CUDA 13.0), GPU NVIDIA GeForce RTX 3050 Laptop (4096 MiB), CPU 12th Gen Intel Core i5-12500H; `DEVICE: auto` -> `cuda` (NN sweep summary `Device` column = cuda; pseudo-online console `device cuda`). The window-sweep summary has no Device column: the cnn cells ran on the same machine and GPU as command 3.

Data source (R-P1): sweep = continuous build `data/processed_continuous/w<L>_s0.25/`, shared quality (source both), OO session; pseudo-online = OO -> mOO, causal stream replay, window tier without guard, session files.

## Pre-run checks (item B)

- `df -h .` before command 1: `/dev/nvme1n1p4  313G  281G  17G  95% /` (17 GB free >= 8 GB); after all runs: 11 GB free.
- `ls -d reports/window_sweep reports/nn_sweep reports/dynamic_stopping* reports/pseudo_online data/processed_continuous/w*_s0.25` before command 1: all "No such file or directory" (none pre-existed).
- Hash of the 65 files of `data/processed_continuous/S0*` (command 0): `reports/logs/P20/hash_before.txt`, `sha256sum` = `c6e72a797e06ccc7fafe03dde3bb81e9ea07eb863909d6ec6a48a5b011e12aec`.

## Commands executed

All via `.venv/bin/python -m ...` from the worktree. Logs in `reports/logs/P20/` (written by `tee` or shell redirection inside the run command, not by hand). Start times are local (UTC-6), 2026-10-28.

| # | Command (arguments as in 02_plan.md; item A/C changes noted) | Start | Wall | Exit | Log |
|---|---|---|---|---|---|
| tests | `pytest tests/ -q -o addopts=""`, run concurrently with 0-1 (first run) | 10:16 | 801.98 s (13m21s) | 0: `2 failed, 1295 passed, 22 warnings` | `pytest_full.log` |
| tests | the 2 failed tests alone | | 6.87 s | `2 passed` | `pytest_rerun_2failed.log` |
| tests | full suite again, nothing else running (diagnostic) | ~10:30 | 768.43 s | `1297 passed, 22 warnings` | `pytest_full_rerun_isolated.log` |
| 0 | sha256 of `data/processed_continuous/S0*` (before) | 10:16:47 | <1 s | 0 | `hash_before.txt` |
| 1 | `scripts.build_windows --filter-mode continuous --subjects S01..S05 --session OO --banks fbcca fbcsp --quality-source both --window-sec W --stride-sec 0.25`, W = 0.5 1 1.5 2 3 4 | 10:16:53 | 46 s (all six; cohort times 2.7, 3.7, 4.3, 4.1, 5.6, 2.4 s) | 0 x6 | `build_windows_w<W>.log` |
| H | `pytest tests/test_p20_online.py -v -o addopts="" -k causal_filter` | ~10:43 | 2.01 s | 0 | `pytest_H_causal_filter.log` |
| 2a | `scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 0.5 1 1.5 2 3 4 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep` | 10:43:35 | 121 s | 0 | `window_sweep_2a.log` |
| 3 | `scripts.benchmarks.neural_networks.benchmark_nn_sweep --data-root data/processed_continuous --windows 1 --models ccnn compact eegnet --out-dir reports/nn_sweep` | 10:45:40 | 944 s | 0 | `nn_sweep.log`, `nn_sweep.start` |
| 4a | `scripts.benchmarks.simulate_dynamic_stopping reports/window_sweep/predictions.csv --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5 --out-dir reports/dynamic_stopping_lda` | 11:01:31 | 2 s | 0 | `dynamic_stopping_4a.log` |
| 5 | `scripts.benchmarks.pseudo_online --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --tag ccnn_5class --quality-source both` | 11:01:37 | 33 s | 0 | `pseudo_online_5class.log` |
| 6 | same with `--rest-class --tag ccnn_6class --quality-source both` | 11:02:10 | 63 s | 0 | `pseudo_online_6class.log` |
| S | stop rule (below) | 11:03 | | | |
| 2b | `scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows W --stride 0.25 --methods cnn --cnn-repeats 1 --out-dir reports/window_sweep`, six invocations W = 0.5 1 1.5 2 3 4 via `mas/state/scratch/p20_verify/run_2b.sh` | 11:03:36 | 429, 619, 658, 767, 689, 483 s = 3645 s (60.75 min) | 0 x6 | `window_sweep_2b_w<W>.log`, `window_sweep_2b_checks.txt` |
| 4b | `scripts.benchmarks.simulate_dynamic_stopping reports/window_sweep/predictions.csv --thresholds ... --skip-sec 0.5 --out-dir reports/dynamic_stopping` | 12:04:36 | 3 s | 0 | `dynamic_stopping_4b.log` |
| 7 | sha256 of `data/processed_continuous/S0*` (after) | 12:04 | <1 s | 0 | `hash_after.txt` |

Item A console line quoted from both pseudo-online logs (line 2, identical in 5 and 6 classes):
`Filter: causal Butterworth 1-90 Hz order 4 + notch 60.0 Hz Q 30, stateful (zi = sosfilt_zi * x[0]); quality source both, limits {'vpp_min': 5.0, 'vpp_max': 120.0, 'std_min': 1.0, 'std_max': 35.0}, channel fail fraction 0.5, no artifact guard (online)`

### Stop rule S (shown computation)

Command: `python3` snippet in the session (script `mas/state/scratch/p20_verify/run_2b.sh` embeds the same constants); `folds.csv` = `reports/nn_sweep/folds.csv`.

- `compact_eegnet` rows of `folds.csv`: sum of `Seconds` = 526.1 s; `P_2b = 7.0 x 526.1 / 60 = 61.378 min`.
- `T_A` (wall minutes of phase commands 1, 2a, 3, 4a, 5, 6 from their logs) = (46 + 121 + 944 + 2 + 33 + 63) / 60 = 20.15 min.
- `T_A + P_2b + 3 = 84.53 <= 120`: run 2b locally. (Also with both full-suite runs added to T_A, 46.32 + 61.38 + 3 = 110.70 <= 120.)
- Per-window checks `elapsed + P_2b x share_L <= 117` (`window_sweep_2b_checks.txt`, elapsed counted from T_A = 20.15 min plus real 2b wall time): W 0.5: 20.15 + 6.08; W 1: 27.30 + 8.78; W 1.5: 37.62 + 11.42; W 2: 48.58 + 12.71; W 3: 61.37 + 12.95; W 4: 72.85 + 9.51; all `ok=1`.
- Total wall of phase commands (1, 2a, 3, 4a, 5, 6, 2b, 4b): 4857 s = 80.95 min <= 120. GPU time (3, 5, 6, 2b): 4685 s = 1.30 h <= 2 h. No stop; all six cnn windows ran locally.

The measured 2b time (60.75 min) was 0.99 x P_2b (61.38): the builders' 80-120 min estimate was pessimistic.

## Human run requests

None. 2b (all six windows) and 4b ran locally within budget. Acceptance checks 1 and 3 are therefore evaluated, not PENDING-HUMAN.

## Produced files

Main tree paths (the worktree links to them):
- `data/processed_continuous/w0.5_s0.25/`, `w1_s0.25/`, `w1.5_s0.25/`, `w2_s0.25/`, `w3_s0.25/`, `w4_s0.25/` (S01-S05 each; 4.6 GB for `data/processed_continuous` in total).
- `reports/window_sweep/{summary,predictions,confusion,timing}.csv`, `sweep_config.json`
- `reports/nn_sweep/{summary,folds,predictions,confusion}.csv`
- `reports/dynamic_stopping_lda/` and `reports/dynamic_stopping/`, each `{best_threshold,cohort,decisions,per_subject}.csv`
- `reports/pseudo_online/{summary,decisions}_ccnn_{5class,6class}.csv`
- `reports/logs/P20/*` (listed above, plus `hash_D_*.txt`, `analysis_sweep.txt`, `analysis_nn_dynstop.txt`, `analysis_pseudo_online.txt`)
- Verifier scripts (read-only analyses): `mas/state/scratch/p20_verify/{hash_d.py,check_f.py,analysis.py,analysis2.py,po.py,run_2b.sh}`

## Anomalies

1. **First full-suite run: 2 failed, 1295 passed** (`pytest_full.log`): `tests/test_p09_compact_shallow.py::test_eegnet_regression_after_refactor` and `tests/test_p10_augmentation.py::test_off_path_identical_to_p09` (both compare `sha256(proba)` with `EEGNET_SMOKE_PROBA_SHA256`: obtained `2ae23a96...` vs pinned `adf2cc7d...`). That run executed concurrently with commands 0-1 (CPU load). The two tests alone pass (`2 passed in 6.87s`), and the full suite re-run with nothing else running gives `1297 passed` (`pytest_full_rerun_isolated.log`). The pinned hashes are therefore sensitive to machine load or execution order; the reviewer should judge. Not a P20 file (both are P09/P10 tests).
2. Same-machine check E: no difference (see 06_verify.md). The suite flake in item 1 shows the repo has bit-level tests sensitive to load, whereas the cnn sweep cell and the NN-sweep cell matched exactly.
3. `reports/window_sweep/sweep_config.json` keeps the last invocation's window list (`windows` of the last 2b call), known non-blocking item of the pre-run audit.
4. Item F channel lists (from the six build logs, `dropped` field): identical across the six lengths for every subject: S01 PO7 dropped (7 kept), S02 none (8), S03 PO7 (7), S04 PO7 (7), S05 none (8). No subject flagged.
5. S02 `cnn (compact_eegnet)` at 4 s: Acc 39.56 %, Train Acc 73.55 %, Val Acc 37.67 % (`reports/window_sweep/summary.csv`); S01 at 4 s: 77.00 %. These drive the cohort cnn drop at 4 s (83.10 %). Values only; no re-run.
6. Disk: 11 GB free after the runs.

## Questions
