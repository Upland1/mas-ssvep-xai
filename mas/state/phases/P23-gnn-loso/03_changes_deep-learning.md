# P23 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md (settled 2-7, row 3, risks, tests 2-8, run commands, budget), 03_changes_connectivity-stats.md, 03_changes_ml-engineer.md, mas/RULES.md
Branch: phase/P23-gnn-loso
Commit(s): bd6379e (feat: benchmark_gnn_loso), the following test: commit (tests), docs: commit (this file); see `git log`

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py` | NEW | `fit_gnn`, variants x norms, protocols loso / within, resumable folds, outputs, `--smoke-test` | P23.2 | R1, R2, R8, PF-28, PF-30, PF-32, PF-33, PF-35, PF-37, [own] |
| `tests/test_p23_gnn_loso.py` | NEW | 22 known-answer tests, each fix test also runs its historical bug | P23.2 | R1, R2, PF-28, PF-32, PF-33, PF-35, PF-37 |

No file of `src/` was modified. Reused, not duplicated: `benchmark_loso` (`load_cohort`, `pool`, `loso_split`, `within_splits`, `check_fold` / `fold_problem`, `save_fold` / `load_fold`, `capture_run_state` / `RUN_STATE`, `cohort_provenance`, `provenance_fields`, `within_source`, `fold_rows`, `cohort_rows`, `smooth_two_tap`, `is_degenerate`, `parse_channels`, `pick_device`), `graph_features_subject.graph_features_for_subject`, `graph_inputs` (`build_inputs`, `fit_standardizer`, `apply_standardizer`, `standardize_fold`), `benchmark_gnn` (`make_model`, `predict_proba`, `diagnosis`, tensors), `training.split_validation` and the P15 constants.

## How it works (settled points)

- **Data**: `load_cohort` (channel choice of `benchmark_loso`, PF-34) for windows, FBCCA scores and provenance; a second `load_subject(..., bands=("fbcca",))` per subject feeds `graph_features_for_subject` (load_cohort drops the FBCCA bank). The harness asserts that the graph rows equal the loaded rows (labels, trial ids, FBCCA). Features are label-free and computed once, in memory.
- **Variants / norms**: default `nodes+F nodes+coh+F`; `--norm pooled` -> `gnn_<variant>` (statistics of the training windows only, R2); `--norm subject` -> `gnn_<variant>_subjnorm` (each subject's own unlabeled whole-session statistics, offline upper bound, PF-35). The `Normalization` column carries the R2 label on every row.
- **`fit_gnn`**: validation = first split of the inner grouped 5-fold over the training windows' offset trial ids (~20 % of the training trials; never the held-out subject), best validation-loss state restored, patience 25, max 150, AdamW lr 1e-3 / wd 1e-2, cosine (T_max = max epochs, eta_min 1e-5), label smoothing 0.05, batch 32 (P15 constants). `--val-frac 0` = fixed `--max-epochs`, last state. `torch.manual_seed(seed)` precedes the model; batches use their own generator seeded with `seed`.
- **Seeds**: `--seeds 3` = 42, 43, 44; fold probability = mean of the seeds' softmax; per-seed train / val accuracy, best epoch, epochs run, val loss and degenerate flag are stored in each fold file and listed in `seeds.csv`; `Acc SD` = `Seed SD` = SD (ddof 1) of the per-seed 1.0 s accuracy; fold degenerate when any seed has best epoch <= 5 or train accuracy < chance + 10 pp (P20 C-2).
- **Protocols**: `loso` (subject held out, offset trial ids); `within` = `StratifiedGroupKFold(5, shuffle, 42)` on the subject's true trial ids through `benchmark_loso.within_splits` (asserts no shared trial), pooled only (`--norm subject` with `--protocol within` is refused), validation again 20 % of the fold's training trials. A within row pools the 5 out-of-fold probability sets; `Data source` through `within_source` says within-subject.
- **Folds**: `<out-dir>/folds/<method>__<protocol>__test-<S>[__fold-k].npz` with JSON config: variant, norm, normalization label, protocol, fold, training subjects, cohort, channels, window, stride, fs, classes, seeds, hyperparameters (incl. `threads`), device, feature source, test window count, `n_windows_train_fold`, plus `n_windows_train`, `build_git_commits`, `config_hash` (P22 C-1, `provenance_fields`) and `git_head` / `git_dirty` recorded once at process start. `check_fold` refuses any difference ("use a new --out-dir"). A test proves that every key is compared.
- **Outputs**: `summary.csv` (`benchmark_loso` columns + `Protocol`, `Normalization`, `Seeds`, `Seed SD`), `per_subject.csv`, `predictions.csv` (+ protocol), `confusion.csv`, `folds.csv` (train / val / test accuracy, train - test gap, best epoch, epochs run, seconds, degenerate, Degenerate seeds, PF-30 Diagnosis from P15's `diagnosis`), `seeds.csv`, `gnn_loso_config.json`. 2-tap smoothing within trial (R8); ITR N = 5, T = window + 0.5 s = 1.5 s. A method with fewer subjects than the cohort gets no Mean / SD (`--partial-mean` overrides).

## Final CLI

```
python -m scripts.connectivity.graph_modeling.benchmark_gnn_loso
  [--data-root data/processed_continuous] [--window 1] [--stride-sec 0.25] [--subjects S01 ...]
  [--channels common|all|NAME ...] [--variants nodes+F nodes+coh+F] [--norm pooled subject]
  [--protocol loso|within] [--seeds 3] [--seed 42] [--val-frac 0.2] [--max-epochs 150] [--patience 25]
  [--batch-size 32] [--lr 1e-3] [--folds 5] [--device auto|cpu|cuda] [--threads 2]
  [--only-test S01 ...] [--only-fold K] [--partial-mean] [--out-dir <dir>] [--config <yaml>] [--smoke-test]
```

Default out-dirs: `reports/loso_gnn` (loso), `reports/within_gnn` (within); `--smoke-test` refuses any path under `reports/` and defaults to a temporary directory.

## Legacy behaviour implemented

None (Era C).

## Differences from the cited examples

- P15 `benchmark_gnn.py` (fixed epochs, no validation, legacy folders, repeats) is untouched; here early stopping on grouped training trials, seeds instead of repeats, built folders. The model, constants and `diagnosis` are imported from it.

## Deviations from the plan

1. **`--threads` (default 2, part of the fold config).** Not in the plan. The networks are tiny: with torch's default of 16 threads on this machine a fold took 2.4x longer than with 2 (below), and results depend on the thread count at the last digits. The flag pins it; `0` leaves torch's default. Resuming with another value is refused.
2. **`device` is in the fold config.** A fold computed on CUDA is not reused by a CPU rerun (and vice versa); not asked for, in the spirit of PF-37.
3. **`--only-test`, `--only-fold`.** Debug / timing switches (a partial invocation has no cohort Mean / SD). Not for result runs.
4. **Second read per subject.** `load_cohort` drops the FBCCA bank that `graph_features_for_subject` needs; the subject is read twice (load time ~0.0 s per subject, connectivity-stats' timing) rather than modifying `benchmark_loso.load_cohort`.
5. `Acc SD` and `Seed SD` are the same number on subject rows (SD over seeds); the cohort Mean row of `Seed SD` is the mean of the subject values, the SD row their SD.
6. `Runs` = number of seeds.

## How to run / reproduce

```bash
P=".venv/bin/python -m"
S="--subjects S01 S02 S03 S04 S05"
$P scripts.connectivity.graph_modeling.benchmark_gnn_loso --smoke-test --out-dir mas/state/scratch/<dir>
$P scripts.connectivity.graph_modeling.benchmark_gnn_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --channels common --variants nodes+F nodes+coh+F --norm pooled --protocol within --seeds 3 --out-dir reports/within_gnn
$P scripts.connectivity.graph_modeling.benchmark_gnn_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --channels common --variants nodes+F nodes+coh+F --norm pooled subject --protocol loso --seeds 3 --out-dir reports/loso_gnn
.venv/bin/python -m pytest tests/test_p23_gnn_loso.py -q -o addopts=""
```

## How I verified

- `tests/test_p23_gnn_loso.py`: 22 passed in 27.4 s (CPU, one thread; CUDA test runs when a GPU is visible). Known answers:
  - pooled sentinel: a +1e3 sentinel in every array of the held-out subject leaves the training arrays and all seed weights bit-identical; the held-out probabilities do change;
  - `_subjnorm`: permuting the held-out labels leaves the normalized arrays and the fold probabilities bit-identical; perturbing another subject leaves a subject's normalized arrays bit-identical; normalized arrays have mean 0 / SD 1 per feature;
  - validation never contains the held-out subject, is trial-grouped and holds 10-30 % of the training trials (all 4 folds, 2 seeds); trial ids are unique across subjects (PF-33);
  - `--val-frac 0` gives fixed epochs and no validation; early stopping stops at `epochs_run - patience` and restores the best-validation state;
  - within folds never share a trial, cover every window exactly once, hold all 5 classes in training; an incomplete subject is left out of the summary;
  - seed average = mean of seed softmax (bit-exact), a rerun is bit-identical in probabilities and weights, seeds differ, seeds are 42, 43, 44;
  - degenerate flag per seed; interrupt after 3 of 8 folds, rerun skips them; outputs identical on a second rerun; every config key (including the three C-1 fields, `device`, `threads`) changes `fold_problem`; refusal text "use a new --out-dir"; summary columns, labels, within `Data source`, ITR (N = 5, T = 1.5 s), seed table, folds table; smoke acceptance (16 + 40 folds run, every fold skipped on rerun, PASS) and its failure when the accuracy gate is not met.
- Mutation check (the mutant is applied to the script, the suite is run, the script is restored; `cmp` confirmed the restore): pooled statistics over all rows -> sentinel test fails; fold probability = last seed -> seed test fails; validation grouped per window -> sentinel test fails (assertion in `fit_gnn` / `run_fold`); subject normalization with one pooled group -> `_subjnorm` test fails; window-level within splitter -> within test fails; dropping the C-1 provenance keys -> key-coverage test fails. Each in-test mutant (leaky standardizer, per-window groups, `StratifiedKFold`) is also asserted to be caught by the same checks.
- Smoke test on this machine (`--smoke-test`, 2 threads): `[smoke] loso: 16 folds run, rerun skipped 16 and ran 0; outputs identical True`, `[smoke] within: 40 folds run, rerun skipped 40 and ran 0; outputs identical True`, mean synthetic LOSO accuracy 87.97 % (> 40 %), 35 s wall. Synthetic, not results.
- Full suite once, alone: `.venv/bin/python -m pytest tests/ -q -o addopts=""` -> `1483 passed, 22 warnings in 859.25s (0:14:19)` (log `mas/state/scratch/p23_dl_suite.log`; no other job running)

## Measured times (one real fold per protocol, S01-S05 built, `common` = 7 channels, nodes+coh+F pooled, 3 seeds, held-out S01 / within fold 0)

Scratch out-dirs under `mas/state/scratch/p23_real_*` (never `reports/`). Seconds are the `seconds` printed by the harness (training + prediction, features excluded; loading + graph features ~3 s per invocation).

| Fold | CPU torch default (16 threads) | CPU `--threads 2` | CUDA (RTX 3050 laptop) |
|---|---|---|---|
| LOSO, held-out S01 (680 test windows, ~2700 training windows), nodes+coh+F | 60.5 s | 36.7 s | 39.4 s |
| LOSO, held-out S01, nodes+F | - | 35.3 s | - |
| within S01 fold 0 (153 test windows), nodes+coh+F | 21.8 s | 8.9 s | 10.2 s |

These single folds are previews, not results: LOSO S01 nodes+coh+F pooled 70.88 % (seeds 69.7 / 70.3 / 66.5 on CPU 2 threads) with train 98.3 % (the PF-30 pattern the report must interpret); within S01 fold 0 69.93 %, train 90.0 %. Best epochs were 81 (LOSO) and 93 (within), so folds ran ~106 and ~118 of at most 150 epochs.

## Extrapolation of the full runs (for the verifier's budget table)

Full within = 2 variants x pooled x 5 subjects x 5 folds = 50 folds; full LOSO = 2 variants x 2 norms x 5 subjects = 20 folds; same fold times for both variants (measured 36.7 vs 35.3 s) and for `_subjnorm` (same cost). Arithmetic: `python3 -c` over the table above.

| Run | CPU `--threads 2` | CUDA | CPU torch default |
|---|---|---|---|
| within (50 folds) | 7.4 min | 8.5 min | 18.2 min |
| LOSO (20 folds) | 12.2 min | 13.1 min | 20.2 min |
| both | 19.7 min | 21.6 min | 38.3 min |
| both, worst case if every seed ran 150 epochs (x150/106) | 27.8 min | 30.6 min | 54.2 min |

All routes are far below the roadmap's 75 min and below `LOCAL_RUN_BUDGET_MIN`/120 min. The small network is faster on 2 CPU threads than on the laptop GPU; no GPU is needed (`MAX_GPU_HOURS_PER_PHASE` unaffected). Run from the clean verifier checkout so `git_dirty` is false in every fold config.

## Left to do / known limitations

- Subject-to-subject fold times vary a few percent (windows 644-680); only S01 was timed.
- CUDA reruns are seeded but not asserted bit-identical (CPU is).
- `_subjnorm` is the offline upper bound: the held-out subject's whole session is in its statistics. No online (first-K) GNN variant exists in this phase; any "online" claim needs the P22 warm-up numbers pre-registered (P22 C-4).
- The suite hook prints "tests took over 150 s" on every edit; the suite is ~14 min (P22 report), not a P23 regression.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

1. `mas/RULES.md` R1, R2, R3, R8, R9, R11; `mas/05_PITFALLS.md` PF-28, PF-30, PF-32, PF-33, PF-35, PF-37; `mas/state/decisions.md` P20 C-2, P21 C-1, P22 C-1, C-3, C-4, C-6.
2. `scripts/benchmarks/benchmark_loso.py`, `scripts/connectivity/graph_modeling/benchmark_gnn.py`, `src/models/cnn/training.py`, `src/features/connectivity/graph_inputs.py`, `src/features/connectivity/graph_features_subject.py` (opened in this run).

## Questions
