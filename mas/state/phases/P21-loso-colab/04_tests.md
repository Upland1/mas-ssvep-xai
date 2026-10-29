# P21 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_ml-engineer.md, 03_changes_deep-learning.md, 03_changes_data-signal.md, mas/RULES.md, mas/05_PITFALLS.md (PF-31..PF-37)

## Tests added

NEW `tests/test_p21_independent_known_answer.py` (23 tests, about 8 s, CPU only, synthetic dicts plus the real build on tiny
`tests/p16_synth` recordings). Its fixtures are my own (4-5 subjects with different gain, trial count and windows per trial;
class c = extra variance in channel c of every FBCSP band plus a sinusoid at the c-th target frequency in the FBCCA bank).

| Test | Known answer | Catches |
|---|---|---|
| `test_fbcca_loso_is_the_planted_class_and_equals_the_within_value_on_the_same_channels` | fbcca fold = the subject's own FBCCA argmax = planted class, gains 0.4-2.5 | M15 |
| `test_fbcca_fold_proba_is_normalised_scores_and_uniform_for_all_zero_scores` | [1,3,0,0,0] -> [.25,.75,0,0,0]; zeros -> 0.2 | M15 |
| `test_lda_above_chance_on_a_held_out_subject_with_a_different_gain` | lda > 0.9 with gain 2.5 held out | |
| `test_subjnorm_not_below_lda_under_a_known_gain_shift_and_much_better_than_chance` | held-out per-electrode gain x0.2..x6: subjnorm >= lda + 5 pp, > 50 % | M8 |
| `test_subject_zscore_is_affine_invariant_per_subject_and_has_zero_mean_unit_std` | rescaling one subject changes no z-score; constant column -> 0 | M8 |
| `test_equal_trial_ids_in_every_subject_never_collide_after_pooling_and_the_validation_split_excludes_the_test_subject` | groups = sum of trial counts; the inner validation split of every LOSO training set has no held-out window; no group spans two subjects | M1, M16 (PF-33, PF-32) |
| `test_pool_assigns_subject_index_in_the_given_order_and_keeps_rows_aligned` | pooled rows equal each subject's arrays; pooled id - offset*k = own id | M1, M19 |
| `test_sentinel_in_the_held_out_subject_changes_no_training_side_output[lda, lda_subjnorm]` | held-out bands/scores = 5e3/1e7: CSP, scaler, LDA, train acc bit-identical | M2, M3, M7, M8 (R2) |
| `test_sentinel_in_one_subject_leaves_every_other_fbcca_fold_unchanged` | fbcca fold j independent of subject i != j | |
| `test_labels_of_the_held_out_subject_reach_no_classical_prediction` | permuting held-out labels: probabilities bit-identical for lda and lda_subjnorm | M2 (PF-35) |
| `test_network_fit_gets_no_held_out_window_and_the_sentinel_changes_no_trained_weight` | CCNN, CPU, 1 thread: `fit_network` sees exactly the training rows; sentinel 1e4 in the held-out windows leaves state dict, mean/std, train acc bit-identical | M1, M5, M16 (PF-32) |
| `test_choose_channels_planted_drops_and_mismatched_montages` | drops (PO7; Oz+PO8; PO3) -> [POz, PO4, O1, O2]; `all` = montage; shorter, reordered or renamed montage raises; empty intersection raises, `all` does not | M11 (PF-34) |
| `test_common_channels_drop_every_subjects_bad_channel_and_all_keeps_the_montage` | real build, bad O1 in S01 and bad PO3 in S04: common = 6 channels without both, all = 8 | M11 |
| `test_two_tap_never_mixes_trials_or_subjects_on_pooled_rows_in_any_order` | pooled smoothing = per-subject; first row of each trial unchanged; others (prev+cur)/2; shuffle-invariant; raw ids would mix | M1, M4, M10 (R8) |
| `test_itr_known_value_and_edges_in_the_summary_row` | acc .8, N=5, T=1.5 s -> 48.00; acc 1 -> 92.88; acc .2 -> 0 | M9 |
| `test_cohort_rows_mean_and_sd_use_ddof_1_over_held_out_subjects` | [50,60,100] -> mean 70, SD 26.46 | M14 |
| `test_interrupt_mid_write_then_resume_gives_byte_identical_outputs_and_skips_only_finished` | die inside the 6th write (stale .tmp left): 5 .npz, rerun skips 5 and runs 4; summary, per_subject, predictions, confusion byte-identical to an uninterrupted run; second rerun skips 9 | M12 (PF-37) |
| `test_rerun_with_another_configuration_is_refused_and_leaves_the_folds_alone[--seed, --channels all]` | SystemExit "different configuration"; fold bytes unchanged | M6, M13 |
| `test_tampered_training_subjects_in_a_fold_config_is_refused_but_a_moved_data_root_and_new_head_are_not` | copied data root and new git head: reused (3 skips); train_subjects tampered: refused | M6 |
| `test_summary_rows_cover_every_held_out_subject_with_the_cohort_in_the_data_source` | per-subject rows + Mean/SD, cohort in Data source, lda_subjnorm label, first window of every trial unsmoothed, stored ids < offset | M4, M18 (R9, PF-35) |
| `test_run_fold_stores_the_subjects_own_trial_ids_and_labels` | stored trial ids = own ids; n_train = rows of the other subjects | M18 |

## Mutation checks

Run on a copy of the tracked tree in the scratchpad (script `scratchpad/mutate.py`); the working tree was never modified
(`git status` clean apart from the new test file). 19 mutants of `scripts/benchmarks/benchmark_loso.py`; 18 killed, 1 equivalent.

| Mutant | Killed by |
|---|---|
| M1 no trial-id offset (trial and groups) | equal_trial_ids, pool_assigns, network_fit, two_tap |
| M2 subjnorm centres by test-class labels | sentinel[lda_subjnorm], labels_of_the_held_out_subject |
| M3 CSP fitted on all subjects | sentinel[lda], sentinel[lda_subjnorm] |
| M4 smoothing ignores trial boundaries | two_tap, summary_rows |
| M5 network fit/validation includes the test subject (assertions removed) | network_fit |
| M6 skip ignores config | rerun_refused x2, tampered_training_subjects |
| M7 whole-data feature standardisation | sentinel x2 (bit level) |
| M8 subjnorm z-score over pooled rows, not per subject | gain_shift, sentinel[lda_subjnorm] |
| M9 ITR without the 0.5 s gaze time | itr |
| M10 smoothing sorted by row, not by offset | two_tap |
| M11 common = union of kept channels | choose_channels, common_channels_drop |
| M12 non-atomic fold write | interrupt_mid_write and 5 others |
| M13 seed/channels ignored in config comparison | rerun_refused x2 |
| M14 cohort SD ddof = 0 | cohort_rows |
| M15 fbcca decision inverted | fbcca x2 |
| M16 groups not offset (trial ids offset) | equal_trial_ids, network_fit |
| M17 scaler `.fit(all rows)` before `pipe.fit(train)` | SURVIVED, equivalent: `Pipeline.fit` refits the scaler on the training rows |
| M18 stored fold trial ids keep the pooled offset | summary_rows, run_fold_stores (survived the first version of the file; test added) |
| M19 subject index constant | equal_trial_ids, pool_assigns, two_tap |

## Command

```bash
.venv/bin/python -m pytest tests/test_p21_independent_known_answer.py -q -o addopts=""   # 23 passed, ~8 s
.venv/bin/python -m pytest tests/ -q -o addopts=""                                      # alone, at the end
```

## Output summary

- Own file: `23 passed in 7.5 s`.
- Full suite run alone on branch `phase/P21-loso-colab`: `1360 passed, 22 warnings in 787.55s (0:13:07)`.
  `torch.get_num_threads()` = 12 (`.venv/bin/python -c`).
- No test exposed a bug; nothing BLOCKED.

## Observations and coverage gaps

1. `folds.csv` holds wall-clock `Seconds`, so it is not byte-identical between an interrupted and an uninterrupted run; the four
   other outputs are. The test compares `folds.csv` without `Seconds`. The verifier's "hash unchanged" check must use `summary.csv`.
2. A leak that only rescales features (scaler fitted on all rows, M7/M17) cannot change LDA predictions because the pipeline
   scaler is refit; the sentinel test sees M7 only through bit-different parameters; M17 is equivalent.
3. Network leak/sentinel tests cover `ccnn` only (CPU, 2 epochs). `compact_eegnet` and `eegnet` share `network_fold`, so the same path,
   but their weights are not compared. The builders' CUDA test is skipped without a GPU.
4. Not tested (needs real data or a GPU): real-subject accuracies, network degeneracy rates, running the notebook on Colab. The
   notebook is covered by the builders' structure test only.
5. The end-to-end synthetic cohort is easy (100 % accuracy), so it proves wiring, not discrimination; discrimination is covered by
   the dict-level tests with weaker SNR (gain shift).

## Reference consultations (R11)

None. The original repository was not opened.

## Sources

1. Wolpaw ITR as implemented in `scripts/benchmarks/benchmark_window_sweep.py::itr_bits_per_min`; value checked by hand: log2 5 + .8 log2 .8 + .2 log2 .05 = 1.2000 bits.
2. `mas/05_PITFALLS.md` PF-31..PF-37; `mas/RULES.md` R1, R2, R8, R9.

## Questions

None.
