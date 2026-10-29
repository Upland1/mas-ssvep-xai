# P23 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_*.md, mas/RULES.md, mas/05_PITFALLS.md (PF-28, PF-32, PF-33, PF-35, PF-37)

All tests are in NEW `tests/test_p23_independent_known_answer.py` (21 tests, about 8 s, CPU, one torch thread, synthetic only). They do not copy the builders' tests: the graph features are compared with a separate numpy/scipy computation (`scipy.signal.coherence`, hand-written periodic Hann FFT, `np.angle` of the cross-spectrum), the normalizations with my own z-scores, the smoothing with a brute-force recomputation.

## Tests added

| Test id (`tests/test_p23_independent_known_answer.py::`) | Simulates | Expected (known answer) | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_features_equal_independent_numpy_reference_at_fs256` | random windows + 20 Hz common tone, fs 256 | node, coherence, phase equal the independent reference per row (chunk 3) | 1e-8 / 1e-7 | analytic, scipy | fs 250, reversed rows, conjugate order | PASS |
| `test_features_would_differ_at_fs250_so_the_reference_pins_the_sampling_rate` | 23 Hz tone | fs-250 numbers differ from fs-256 by > 0.2 log10 | 0.2 | analytic | fs 250 (PF-04) | PASS |
| `test_planted_tone_band_columns_and_harmonic` | 20 Hz on ch 3, 48 Hz on ch 1 | node col 1 argmax = ch 3 (> 2 log10 margin), col 5 argmax = ch 1 (2nd harmonic of 24) | margin 2 | analytic | band / harmonic layout | PASS |
| `test_coupled_pair_coherence_and_phase_lag_only_on_that_edge` | ch 2 lags ch 0 by 0.7 rad at 15 Hz | coherence > 0.95 at (0,2),(2,0) band 2 only; cos/sin = (cos 0.7, sin 0.7), conjugate at (2,0) | 0.12 and exact vs reference | analytic | wrong edge/band, phase sign | PASS |
| `test_upper_tri_layout_flat_columns_follow_triu_pair_major_order` | coded array value = 1000i+100j+10k+c | flat index `(pair*5+k)*2+c` holds the code | exact | R6 | wrong flatten | PASS |
| `test_rows_align_with_load_subject_and_match_the_reference_per_row` | built synthetic folder via real builder | y, trial ids, offsets equal `load_subject`; rows in (trial, offset) order; features = reference; FBCCA argmax > chance | 1e-8 | R6, R8 | row misalignment | PASS |
| `test_pooled_training_arrays_are_my_own_zscore_of_training_rows_and_ignore_a_heldout_sentinel` | +500 sentinel in held-out subject | training arrays = my z-score of training rows; sentinel leaves them and all seed weights bit-identical; held-out proba changes | exact | R2 | pooled stats over all rows | PASS |
| `test_subjnorm_uses_each_subjects_own_statistics_and_no_labels` | 4 subjects, permuted held-out labels | each subject = own z-score; inputs and proba bit-identical under permutation; sentinel in held-out subject leaves training subjects identical | exact | PF-35 | pooled stats under `_subjnorm`, label use | PASS |
| `test_subjnorm_is_refused_under_within_by_the_cli` | `--protocol within --norm subject` | SystemExit | - | plan 2 | no-op norm under within | PASS |
| `test_validation_excludes_heldout_subject_and_splits_by_trial_in_every_loso_fold` | 4 LOSO folds x 2 seeds | val rows not of held-out subject, no trial shared fit/val/test; window-level splitter raises | exact | R1, PF-32/33 | window-level val groups | PASS |
| `test_within_folds_never_split_a_trial_and_cover_each_window_once` | within, 4 subjects x 5 folds | no shared trial, all 5 classes in training, each window tested once; `run_fold` row_idx/n_train equal the split | exact | R1 | window-level within CV | PASS |
| `test_fold_probability_is_mean_of_seed_softmax_and_rerun_is_bit_identical` | 3 seeds | proba = mean of per-model softmax I compute; seeds 42, 43, 44; rerun bit-identical | 1e-6 / exact | PF-28 | last seed, nondeterminism | PASS |
| `test_resume_skips_finished_folds_and_every_config_change_is_refused` | one fold on disk | rerun skips; refusal ("use a new --out-dir") for seeds, seed, val_frac, epochs, patience, batch, lr, threads, window, stride, channels mode, device, subjects, channels, fs, classes, n_windows, build_git_commits, config_hash, git_dirty | - | PF-37 | dropped key, skipped check | PASS |
| `test_interrupt_then_resume_runs_only_missing_folds` | save raises on 3rd fold | 2 files, no `.tmp`, rerun: 2 run, 2 skipped | exact | PF-37 | non-atomic save | PASS |
| `test_fold_count_guard_incomplete_within_subject_is_left_out` | 1 of 5 within folds | `build_outputs` returns {}; `assemble_within` raises on uncovered rows | - | R1 | partial subject averaged | PASS |
| `test_two_tap_smoothing_averages_only_within_trial_in_offset_order_whatever_the_row_order` | shuffled rows, trials of sizes 3/1/4 | brute-force expectation | 1e-12 | R8 | smoothing across trials, unsorted | PASS |
| `test_output_two_tap_accuracy_matches_my_recomputation_from_stored_fold` | stored fold npz | summary smoothed accuracy = my loop | 0.01 pp | R8 | reporting path wrong | PASS |
| `test_strings_normalization_protocol_data_source_in_loso_and_within` | tiny LOSO (2 norms) and within runs | Normalization pooled "training windows only/R2"; subject "unsupervised/no labels/test-time/offline upper bound/R2 exception"; Protocol; within Data source "within-subject" not "LOSO"; within pooled only | - | R2, R9, P22 C-3/C-6 | mislabels | PASS |
| `test_cli_defaults_two_variants_and_pooled` | parser defaults | variants, pooled, 3 seeds, loso | - | plan 2-3 | - | PASS |
| `test_warmup_summary_has_normalization_column_with_r2_wording` | 3-subject built folders | `Normalization` in summary.csv and cohort.csv, wording; config json | - | P22 C-3 | missing label | PASS |
| `test_within_lda_receives_cv_groups_and_says_within_subject` | cv_groups != trial_ids planted | spy receives `cv_groups`; `within_source` drops LOSO | exact | P22 N2/W-1 | trial ids passed | PASS |

## Mutation checks

Run by `mas/state/scratch/p23_mutate.py` (not committed): each mutant is applied to a throw-away copy of `src/ scripts/ configs/ tests/` under `mas/state/scratch/p23_mut/<name>/`, my test file is run with `-x`, the copy is deleted. The tree was never modified (`git status` clean apart from the new test).

| Mutant | Killed by |
|---|---|
| `fs = 250.0` in `graph_features_for_subject` | features reference test |
| node rows reversed | features reference test |
| phase conjugate order swapped (frozen P15 module copy) | features reference test |
| pooled stats over train + test rows | pooled sentinel test |
| `_subjnorm` with one pooled group | subjnorm test |
| fold proba = last seed | seed-mean test |
| validation groups per window | pooled test (assertion in `fit_gnn`; the validation test also covers it) |
| provenance keys (`n_windows_train`, commits, config hash) dropped from fold config | resume/refusal test |
| `threads` dropped from config | resume/refusal test |
| `device` dropped from config | resume/refusal test |
| `check_fold` skipped on resume | resume/refusal test |
| within Data source not rewritten (says LOSO) | strings test |
| within splitter window-level | within test |
| `--norm subject` allowed under within | CLI test |
| smoothing ignores trial ids | smoothing test |
| `within_lda` receives `trial` instead of `groups` | within_lda test |
| warm-up `Normalization` column renamed | warm-up test |
| `_subjnorm` label loses "test-time" | strings test |

18 of 18 killed.

## Gaps

- CUDA is not tested (CPU only); GPU bit-identity is not asserted (as the builders state).
- Real built folders (`data/processed_continuous`) are not read; alignment with `load_subject` uses the synthetic built folder only.
- The coherence phase test uses noisy tones, hence the 0.12 tolerance on the lag; the exact value is pinned by the reference comparison.
- `git_head` change with a clean tree (`code_changed`) is not re-tested here (covered by P22 tests); only the dirty-flag flip is.
- The notebook section 10b is covered by the data-signal builder's structure test only; not re-tested here.
- The smoke test acceptance (> 40 %) is not re-run here (builders' test covers it).

## Command

```bash
.venv/bin/python -m pytest tests/test_p23_independent_known_answer.py -q -o addopts=""
.venv/bin/python -m pytest tests/ -q -o addopts=""
```

## Result

Independent file: 21 passed in 7.55 s.
Full suite (alone): 1512 passed, 22 warnings in 855.89s (0:14:15), run alone, no other job running (log `mas/state/scratch/p23_tester_suite.log`)

## Questions
