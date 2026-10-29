# P21 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md, 03_changes_ml-engineer.md, mas/RULES.md, PF-31..PF-33, decisions P20 C-1..C-3
Branch: phase/P21-loso-colab
Commit(s): 9cb17ee (test: thread-pinned hash tests), a8d2615 (feat: device fallback, network tests), docs: this file

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| scripts/benchmarks/benchmark_loso.py | MODIFIED | `pick_device` (cuda if available; `--device cuda` without a GPU falls back to CPU with a warning), used in `main`; `--save-models` stores the state dict moved to CPU. `network_fold` and `is_degenerate` (builder 1) were reviewed and left unchanged: they already implement settled points 5 (networks) and 8 | P21.2 | PF-31, PF-32, P20 C-2 |
| tests/test_p21_loso_networks.py | NEW | 9 test cases (6 CPU, 3 CUDA parametrisations, skipped without a GPU; they ran here) | P21.2 | [own] |
| tests/test_p09_compact_shallow.py | MODIFIED | `single_thread()` context manager (set_num_threads(1), restored), `assert_eegnet_smoke_proba` (byte hash at 1 thread + row sums + tolerance vs the originally pinned 12-thread values), new pinned hashes | P20 C-1 | [own] |
| tests/test_p10_augmentation.py | MODIFIED | `test_off_path_identical_to_p09` uses the same helpers | P20 C-1 | [own] |

`src/models/cnn/training.py` is unchanged: `fit_network` already takes pooled windows with offset group ids, so no pooled entry point was needed.

## Legacy behaviour implemented

None.

## P20 C-1: hash-pinned tests

Cause: float32 CPU kernels sum in a thread-count-dependent order. Probabilities differ by at most 6.1e-05 between 1 and 12 threads (same argmax) but the byte hash changes.
Before the change (this machine, 16 cores, default torch threads 12): both tests failed at OMP_NUM_THREADS 1 and 4, passed at 12 and 16.

Model code unchanged: `git diff main --stat -- src` shows only `src/io/subject_data.py` (builder 1, unrelated); `eegnet.py`, `eegnet_cv.py`, `augmentation.py` and `tests/p05_synth.py` are untouched since P08/P11. Proof by recomputation, same script, on a detached worktree of `main` (add8ea1) and on this branch (the arrays are bit-equal at 1, 2 and 12 threads):

| threads | proba SHA-256 (main = this branch) |
|---|---|
| 1 | 017ccd7b538abe0932f77a8dd4f84f72ec914f703af738efba93ffe9d0bdd19a |
| 2 | 85bc5950c50f40cb5e4010332fb77bb903f42b38a268bd4b9580ac172b84cc2b |
| 12 | adf2cc7d6252d06f2bcd70ce15d14d118a5816061c64e1ec5145f3836e75322c (the previously pinned value) |

CSV hash of `eegnet_benchmark_cpu.csv` (P09 test): 1 thread fb7392d8cd04fefa0e7582d7219965cca3fd960cd81d5d19b69b996fda95a13f, 12 threads 6dbbe4aae453dbe3f313df927728863cfd852d5333550de75b960759bb9bd478 (previous pin); identical on main and on this branch at each count.
New pins are the 1-thread values; the old ones are recorded in the test file comments. The tolerance check (rows sum to 1 within 1e-6; first 3 rows within 1e-3 of the 12-thread values) does not depend on the thread count.
After the change both tests pass at OMP_NUM_THREADS 1, 4, 12 and 16 (`2 passed` each). Failing variant: the unpinned tests fail at 1 and 4 (above).

## P20 C-2: degenerate flag

`is_degenerate(best_epoch, train_acc, n_classes)`: best epoch <= 5 or train acc < 1/K + 0.10; written as `degenerate` in `folds.csv` and printed as `[warn] degenerate network folds ...`. The stopping rule in `fit_network` is unchanged. Tests: boundaries (5 True, 6 False; 0.25 True, 0.31 False), a real 1-epoch fold gives best epoch 1 and is flagged, NaN (classical rows) is never flagged.

## Tests (tests/test_p21_loso_networks.py, ~7 s)

| Test | Guards / failing variant |
|---|---|
| `test_pooled_ccnn_learns_the_planted_classes_on_the_held_out_subject` | planted sinusoid classes, 3 training subjects with different gain, held-out accuracy > 0.8 (chance 0.2); variant with shuffled training labels stays < 0.6 |
| `test_validation_windows_exclude_the_held_out_subject_and_the_raw_id_bug_is_caught` | offset ids: no fitting or validation window of the test subject; un-offset ids make `network_fold` raise; fitting on all rows does put the test subject into validation (so the guard is meaningful) |
| `test_normalisation_statistics_ignore_the_held_out_subject` | held-out windows replaced by 1e6: mean/std and every trained weight bit-identical; statistics over all rows differ |
| `test_degenerate_flag_fires_on_best_epoch_one_and_low_train_accuracy` | see C-2 |
| `test_saved_state_dict_reproduces_the_fold_probabilities` | `--save-models` file reloads into a fresh model and reproduces `proba` exactly |
| `test_method_names_and_device_fallback` | `compact` -> `compact_eegnet` (PF-31); cuda requested without a GPU falls back to CPU with a warning |
| `test_network_fold_runs_on_cuda[ccnn / compact_eegnet / eegnet]` | skipped without CUDA |

Parameter counts (R-8, B004) are not touched in this phase; the P20 count tests remain in the suite.

## Smoke on built S01-S05 (real windows, 7 common channels, held-out S01, 2649 training windows)

Seed 42, P20 hyperparameters, full early-stopping rule (max 150, patience 25), device cuda, torch threads 12. Log `mas/state/scratch/p21_net_smoke/smoke_cuda_fold.log`. Total 180 s (one fold per model, run through `run_fold` from a scratch script).

| Model | Test acc S01 (%) | Train acc (%) | Val acc (%) | Best epoch | Epochs run | Fold seconds | ms per training-window-epoch | Degenerate |
|---|---|---|---|---|---|---|---|---|
| ccnn | 71.32 | 99.91 | 97.91 | 31 | 56 | 20.3 | 0.137 | False |
| compact_eegnet | 60.29 | 99.91 | 95.63 | 70 | 95 | 114.8 | 0.456 | False |
| eegnet | 57.94 | 98.30 | 96.39 | 44 | 69 | 45.1 | 0.247 | False |

ms per training-window-epoch = seconds / (epochs run x 2649); P20 `nn_sweep` gave 0.115 / 0.458 / 0.218. Informational only: one seed, one subject, no R-16 conclusion (P20 C-3). The large train-minus-test gap is the expected LOSO one (validation windows come from the training subjects).
CPU (`CUDA_VISIBLE_DEVICES=""`, 2 epochs, includes warm-up, log `smoke_cpu_2epochs.log`): 3.6 / 15.6 / 4.4 s for ccnn / compact_eegnet / eegnet, i.e. about 1.8 / 7.8 / 2.2 s per epoch on 2119 fitting windows. CPU suits tests and tiny runs, not the cohort.

Runtime table for the verifier (computed from the GPU rates above with the epochs of this one fold; real epoch counts vary by fold):

| Model | Cohort 5: 5 folds (min) | 40 subjects: s per epoch (25 935 training windows) | 40 subjects: min per fold | 40 folds (h) |
|---|---|---|---|---|
| ccnn | 1.7 | 3.5 | 3.3 | 2.2 |
| compact_eegnet | 9.6 | 11.8 | 18.7 | 12.5 |
| eegnet | 3.8 | 6.4 | 7.4 | 4.9 |

Cohort 5 networks: about 15 min on this GPU (plan estimate 12.5 min), inside `MAX_GPU_HOURS_PER_PHASE` 2. Forty subjects: about 19.6 h (plan estimate 16 h), a human run as planned. Memory: pooled float64 windows of 40 subjects ~1.1 GB for the networks on top of the classical footprint (builder 1: ~4.5 GB peak).

## Deviations from the plan

1. `network_fold`, `is_degenerate` and `training.py` needed no change; the edits in `benchmark_loso.py` are limited to device handling and the CPU state dict.
2. The hash-pinned tests now pin the 1-thread hashes (not the old 12-thread values).
3. The smoke ran one fold per model from a scratch script (the CLI would run 5 folds per model and exceed the 5-minute budget).

## How I verified

- `.venv/bin/python -m pytest tests/test_p21_loso_networks.py tests/test_p21_loso.py -q -o addopts=""`: 31 passed.
- Hash tests at OMP_NUM_THREADS 1, 4, 12, 16: 2 passed each.
- Full suite alone (nothing else running; `torch.get_num_threads()` = 12): `.venv/bin/python -m pytest tests/ -q -o addopts=""` -> `1329 passed, 22 warnings in 867.99s (0:14:27)` (log `mas/state/scratch/p21_net_smoke/full_suite.log`).

## Reference consultations (R11)

None. The answer-key repository was not opened.

## Sources

mas/RULES.md R1, R2; mas/05_PITFALLS.md PF-28, PF-31, PF-32, PF-33; mas/state/decisions.md P20 C-1..C-3; src/models/cnn/training.py (`fit_network`, `fit_stats`, `normalise`); P20 `reports/nn_sweep/folds.csv` (cost per window-epoch, as quoted in the plan).

## Questions

ACK 02_plan.md deep-learning 2026-10-28
