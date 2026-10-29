# P21 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md
Branch: phase/P21-loso-colab
Commit(s): see `git log` (feat: LOSO harness; test: LOSO known-answer tests + guard registration; docs: this file)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| scripts/benchmarks/benchmark_loso.py | NEW | LOSO harness: CLI, `choose_channels`, `pool` (trial-id offset), `lda_loso_fold` (lda, lda_subjnorm), `fbcca_fold`, `network_fold` hook, atomic fold store with config JSON, summary/per_subject/predictions/confusion/folds outputs, 2-tap smoothing, ITR | P21.1 | R1, R2, R8, R9, PF-33..PF-35, PF-37, [own] |
| src/io/subject_data.py | MODIFIED | `load_subject(..., channels=None)`: optional channel names (built folders) replacing the gate-kept list, needed by `--channels all`; default behaviour unchanged | P21.1 | PF-34 |
| tests/test_p21_loso.py | NEW | 22 known-answer tests (below) | P21.1 | [own] |
| tests/test_no_leakage.py | MODIFIED | `loso_split` registered in `LEAK_FREE` (no trial or subject shared train/test); `benchmark_loso.py` imports no sklearn splitter, so `KNOWN_SPLITTER_FILES` needs no entry | R1 | [own] |

## Legacy behaviour implemented

None.

## Final CLI

```
python -m scripts.benchmarks.benchmark_loso
  [--data-root data/processed_continuous] [--window 1] [--stride-sec 0.25]
  [--subjects S01 S02 ...]                       default: every built S<k>, numeric order
  [--methods fbcca lda lda_subjnorm ccnn compact eegnet]   default: fbcca lda lda_subjnorm; compact = compact_eegnet (PF-31)
  [--channels common|all]                        default common
  [--out-dir reports/loso_w1] [--save-models] [--models-dir outputs/models/loso_w1]
  [--allow-config-mismatch]                      default: a saved fold from another configuration is refused
  [--no-augment] [--max-epochs 150] [--patience 25] [--device auto|cpu|cuda]   (networks)
  [--seed 42] [--config configs/pipeline_config.yaml]
```

The plan's run commands work unchanged (`--window 1 --stride-sec 0.25 --subjects ... --methods ... --channels common --out-dir ...`).
Folds are `<out-dir>/folds/<method>__test-<S>.npz` (method names `fbcca lda lda_subjnorm ccnn compact_eegnet eegnet`).
Outputs: `summary.csv`, `per_subject.csv`, `predictions.csv`, `confusion.csv`, `folds.csv`, `loso_config.json`. The summary is
rebuilt from every fold in `folds/` that belongs to the current cohort, so classical and network runs can share one `--out-dir`
(plan commands 2 and 3 do).

## Settled points as implemented

1. Subjects: `--subjects` or `discover_subjects`; `check_subject_names` sorts numerically and refuses `S10` + `S010`; cohort and size printed and written in every `Data source`; < 2 built subjects aborts.
2. Classes 101-105 (`CLASS_CODES`).
3. `choose_channels(montages, kept, mode)`: `common` = montage channels kept in every subject (order of the montage); `all` = whole montage; differing montages or empty result raise. `all` is realised by `load_subject(channels=...)`; the summary `Channels` cell says "(all, gate channel drops ignored)". Probe pass: `load_subject(sub, conditions=())` reads the montage and gate decision without loading windows.
4. Pooling: trial id `+ 10_000 * subject_index` (`TRIAL_OFFSET`, error if an id reaches it); `groups` (= `cv_groups`) offset likewise; `loso_split` asserts no shared subject. Folds store the original (un-offset) ids.
5. Methods: `fbcca` = argmax of the saved-bank FBCCA scores (`p_*` = scores / sum); `lda` = in-fold FBCSP(m=1) on training subjects + FBCCA -> StandardScaler -> Shrinkage-LDA (lsqr, auto), numerically equal to `benchmark_window_sweep.lda_fold` (tested); `lda_subjnorm` = same with each subject's feature matrix (CSP + FBCCA columns, training subjects and held-out subject alike) z-scored with its own unlabeled whole-session mean/std before the pooled scaler + LDA; method label in tables "lda_subjnorm (unsupervised per-subject normalization)" and the log line states "test-time, offline upper bound; R2 exception, PF-35". Networks: `network_fold` calls `fit_network` on the pooled training subjects (groups = offset trial ids; asserts held-out ids absent from training groups and held-out subject absent from the validation indices); this is the hook for P21.2 (degenerate rule, device, extra reporting).
6. Fold store: atomic (`.tmp` + `os.replace`), arrays proba/y/trial_id/offset/train_acc/val_acc/best_epoch/epochs_run/n_train/seconds + `config` JSON (method, test subject, training subjects, cohort, channels and mode, window, stride, fs, classes, quality, seed, trial offset, method hyperparameters, test windows, git HEAD, data root). `[skip] <method> test-<S>` on rerun.
7. Outputs per plan; 2-tap smoothing = `smooth_probabilities_by_trial` after sorting by (trial, offset) and restoring the order; Mean/SD rows per method (SD ddof = 1); ITR Wolpaw N = 5, T = 1.5 s; `Runs` = 1, `Acc SD` = 0.
8. Degenerate flag: `is_degenerate` (best epoch <= 5 or train acc < 0.30) writes `degenerate` in `folds.csv` and prints a warning (only networks can be True).
11. Not mine to run; see "Left to do".

## Deviations from the plan

1. **Config mismatch is refused, not only warned** (settled point 6 says warn, P22 refuses). My role prompt and PF-37 say a rerun must refuse reuse; a silent mix of configurations would corrupt a cohort table. `--allow-config-mismatch` gives the plan's behaviour (reuse with `[warn]`). `git_head` and `data_root` are excluded from the comparison (code revisions of later builders and Colab paths must not invalidate folds). If the orchestrator wants warn-only, flip the default of that flag.
2. **`fbcca` uses the chosen cohort channels**, so with `--channels common` its LOSO value differs from the within-subject cell for subjects whose own gate kept a different channel set. Measured on S01-S05 (common = 7 channels, P20 `reports/window_sweep` within cells): S01 58.68 = 58.68, S03 91.07 = 91.07, S04 98.80 = 98.80, S05 95.43 = 95.43, S02 68.01 vs 64.60 (S02 has 8 channels in the within run). With `--channels all` (8 channels) S02 = 64.60 and S05 = 95.43 equal the within values, S01/S03/S04 do not (their within runs used 7). The equality check of R-16 is therefore exact only on identical channels (proved on synthetic data: test 1); the report should state this and compare on the same channels (P22 `within_lda` is the planned fix).
3. `src/io/subject_data.py` was modified (new optional `channels` argument); the plan listed no change there. Backwards compatible.
4. Network fold uses `fit_network` directly (not `cnn_fold`) so `--save-models` can save the state dict; the body is the same computation.

## Tests (tests/test_p21_loso.py, all synthetic, ~8 s)

| Plan test | Test | Guards / failing variant |
|---|---|---|
| 1 planted SSVEP | `test_fbcca_loso_equals_the_within_value_per_subject_and_lda_is_above_chance`, `test_lda_loso_fold_equals_the_window_sweep_fold_on_the_same_split` | fbcca LOSO == `run_cell` fbcca per subject; lda > 90 % |
| 2 gain shift | `test_subjnorm_beats_plain_lda_when_subjects_differ_in_channel_gain` | subjnorm >= lda + 5 pp, > 50 % |
| 2 / 10 labels | `test_subject_normalization_ignores_the_held_out_labels` | permuting held-out labels leaves features unchanged; a class-centred (label-using) normalizer fails the same check |
| 3 offset | `test_pooled_groups_are_unique_...`, `test_without_the_offset_trial_ids_collide`, `test_pool_refuses_...` | raw-id pooling collides (PF-33) |
| 4 sentinel | `test_replacing_the_test_subject_by_a_sentinel_changes_no_fitted_parameter[False/True]` | CSP filters, scaler, LDA bit-identical; a scaler fitted on all rows changes |
| 5 channels | `test_choose_channels_common_all_and_errors`, `test_channels_all_keeps_the_gate_dropped_channel_and_common_drops_it` (planted 80 uV channel through the real build), `test_subject_names_...` | |
| 6 resume | `test_interrupted_run_resumes_...` (KeyboardInterrupt after 4 of 9 folds; rerun prints 4 `[skip]`, 5 computed, all CSVs byte-identical to an uninterrupted run), `test_atomic_write_leaves_no_partial_fold`, `test_fold_stores_its_configuration_and_a_mismatched_rerun_is_refused` | |
| 7 smoothing | `test_two_tap_smoothing_averages_only_within_a_trial_whatever_the_row_order` | no-reset legacy rule differs |
| 8 networks | `test_network_fold_never_sees_the_test_subject_in_training_or_validation`, `test_save_models_and_network_methods_through_the_cli`, `test_degenerate_flag_...` | spy on `fit_network` groups / `val_idx` |
| R1 guard | `LEAK_FREE` entry in `tests/test_no_leakage.py` | |

## Measured runtimes (this machine, CPU, `CUDA_VISIBLE_DEVICES=""`; logs in console only)

Cohort 5 (S01-S05, built folders `data/processed_continuous/w1_s0.25`, 7 common channels), output in `mas/state/scratch/p21_loso_c5/`:

- `fbcca lda lda_subjnorm` end to end: 11.7 s wall (load 0.3-0.4 s/subject; fbcca fold 0.0 s; lda fold 1.0-1.5 s; lda_subjnorm fold 1.1 s). Rerun (all 15 folds present): 2.8 s, 15 `[skip]`.
- `--channels all`: 11.3 s. Networks smoke (eegnet, 2 epochs, CPU, 5 folds): 15 s wall.
- Scaling to 40 subjects (measured with S01-S05 replicated 4x = 20 subjects, 13 316 windows, 19 training subjects, i.e. the real code on real windows): one `lda` fold 11.3 s, one `lda_subjnorm` fold 9.9 s; peak RSS 2.2 GB. Linear extrapolation to 40 subjects (~26 600 windows, 39 training subjects): ~22 s per fold, 40 folds ~ 15 min per LDA method (~30 min for both), load ~ 40 x 0.4 s = 16 s, `fbcca` seconds, peak RSS ~ 4.5 GB (bands are pooled in float64; the loader frees each subject as it is pooled). Classical LOSO for 40 subjects therefore fits the 120 min budget (~35 min). Networks: see P21.2 / the plan estimate.
- Real-data numbers of the smoke (informational, R-16 directions only): mean Acc over S01-S05 `fbcca` 82.40, `lda` 87.61, `lda_subjnorm` 90.03 (2-tap 82.72 / 88.64 / 90.75); LOSO `lda` is below the within `lda` of `reports/window_sweep` for every subject (S01 69.26 vs 75.88, S02 76.24 vs 77.36, S03 96.07 vs 97.31, S04 99.55 vs 99.79, S05 96.91 vs 99.09); `lda_subjnorm` >= `lda` for S01, S02, S04, S05 and 0.46 pp lower for S03 (cohort mean higher). Source: `mas/state/scratch/p21_loso_c5/summary.csv`.

## How to run / reproduce

```bash
.venv/bin/python -m scripts.benchmarks.benchmark_loso --window 1 --stride-sec 0.25 --subjects S01 S02 S03 S04 S05 \
  --methods fbcca lda lda_subjnorm --channels common --out-dir mas/state/scratch/p21_loso_c5
.venv/bin/python -m pytest tests/test_p21_loso.py tests/test_no_leakage.py -q -o addopts=""
```

## How I verified

- `tests/test_p21_loso.py` + `tests/test_no_leakage.py`: 36 passed.
- Full suite alone: see "Full suite" below.

## Full suite

`.venv/bin/python -m pytest tests/ -q -o addopts=""` alone on commit d1c4b91 (feat + test commits): `1320 passed, 22 warnings in 813.85s (0:13:33)`.

## Left to do / known limitations

- P21.2 fills the network details (hook `network_fold`, `is_degenerate`, `--device`); it edits only those parts of `benchmark_loso.py`.
- The harness holds the pooled windows in memory (float64); a 40-subject cohort needs ~4.5 GB for the classical methods and, for networks, a further ~1.1 GB of raw windows. Colab's 12 GB suffices.
- Within-vs-LOSO tables need the within reference on the same channels (deviation 2).

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

1. mas/RULES.md R1, R2, R8, R9; mas/05_PITFALLS.md PF-31..PF-37; mas/02_REQUIREMENTS.md section 6; scripts/benchmarks/benchmark_window_sweep.py (reused `lda_fold` logic, ITR, balanced accuracy, `fbcca_features`); src/preprocessing/dataset/smoothing.py (`smooth_probabilities_by_trial`); src/models/cnn/training.py (`fit_network`).

## Questions

ACK 02_plan.md ml-engineer 2026-10-28
