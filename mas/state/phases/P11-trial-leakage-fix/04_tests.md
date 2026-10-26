# P11 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_ml-engineer.md (incl. Round 1), 03_changes_deep-learning.md, mas/RULES.md, mas/05_PITFALLS.md PF-01-03

No builder bug found. Builder tests were not edited. New file: `tests/test_p11_known_answer.py` (NEW, 30 tests, ~55 s, CPU, synthetic data only), written independently of the builders' tests.

## Tests added

| Test id (`tests/test_p11_known_answer.py::`) | Simulates | Expected | Tolerance | Source of expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_ids_hand_built_arrays_with_dict_lengths` (6 cases) | 201x4/202x2/101x10/102x10; adjacent same-label runs; 201x3; 105x9+101x5; 202+104x39 (7x5+4); block shorter than a trial | hand-written id lists (201 pairs, each 202 its own trial, remainder own id) | exact | by hand | wrong per-label length, remainder merged | PASS |
| `test_ids_remainder_is_flagged_warned_and_clean_is_silent` | 12-window block among 201/102 | truncated `[(101, 2, 12)]`, warning; clean array silent | exact | by hand | silent remainder | PASS |
| `test_ids_int_length_applies_to_every_label` | int trial length 2 and 5 | `[0,0,1,1,2,2,3,3,4]`, `[0,0,0,0,1,1,1,1,1]` | exact | by hand | dict/int mix-up | PASS |
| `test_pre_gate_ids_masked_equal_true_ids_post_gate_ids_do_not` | window dropped mid-trial (2, 13) | `ids_pre[mask]` = true ids; ids of gated labels differ | exact | by hand | PF-03 | PASS |
| `test_chained_masks_stimulus_selection_then_gate_keep_true_ids` | 201/202 prefix, stimulus selection then gate | `[3,3,3,3,4,4,4,4]` | exact | by hand | PF-03 (wrong mask / order) | PASS |
| `test_gate_drop_of_a_whole_trial_leaves_a_gap_not_a_renumbering` | whole trial gated | ids `[0]*5+[2]*5` | exact | by hand | PF-03 | PASS |
| `test_classical_script_default_split_is_grouped_with_true_ids[x5]` | each of the 5 classical scripts, default flags, synthetic S03 with one gate-rejected window; scikit-learn `StratifiedKFold.split`/`StratifiedGroupKFold.split` patched at class level | no window-level split; recorded groups equal the hand-known ids (up to relabelling, 74 clean windows); no id on both sides in 5 folds; test folds partition the windows | exact | by hand (`arange(75)//5` minus the rejected row) | PF-01, PF-03 | PASS |
| `test_network_script_default_split_is_grouped_with_true_ids[x4]` | EEGNet, Compact-CNN, ShallowConvNet, A/B script, 1 epoch | same as above | exact | by hand | PF-01, PF-03 | PASS |
| `test_negative_control_the_spy_sees_the_window_level_split_in_legacy_mode` | `--cv legacy` | plain split recorded, every fold shares ids | exact | by hand | spy is live | PASS |
| `test_feature_selection_sfs_inner_cv_is_grouped_and_shares_no_id` | feature-selection script end to end | >=5 inner grouped splits over training rows, no shared id, no plain `StratifiedKFold` call | exact | by hand | PF-01 (inner CV) | PASS |
| `test_column_sets_sfs_inner_cv_uses_training_ids_only` | `column_sets` direct; with ids and with `ids_tr=None` | grouped inner splits with groups = `ids`; legacy path does share ids | exact | by hand | PF-01 | PASS |
| `test_planted_trial_fingerprint_leaks_through_window_split_not_trial_split` | per-trial random fingerprint, labels independent, 4 seeds, 1-NN (+LDA) | leaky >0.9 (LDA >0.6); grouped mean/max within chance + binomial 3 sigma (chance 0.25, 80 trials) | 3 sigma | planted | PF-01 | PASS |
| `test_trial_smoothing_hand_computed_and_differs_from_mod5` | ids `[0]*4+[1]*5+[2]*2` | rows 4, 5, 10 = `[4,96]`, `[4.5,95.5]`, `[9.5,90.5]`; mod5 row 4 = `[3.5,96.5]`, row 5 = `[5,95]`; no-reset rule differs | exact | by hand | PF-02 | PASS |
| `test_trial_smoothing_never_mixes_one_hot_trials` | one-hot trials | no mass from previous trial | exact | by hand | PF-02 | PASS |
| `test_accuracies_2s_by_trial_hand_computed` | 7 windows, ambiguous window at a trial start | trial rule 1.0, mod5 rule 6/7, 1.0 s = 1.0 | exact | by hand | PF-02 | PASS |
| `test_grouped_folds_are_stratified_within_one_trial_per_class_and_partition_all_windows` | 10/12/15/10/8 trials per class | per-class test trials per fold within 1 of n/5, every window tested once, a trial in one test fold only, all classes in training | +-1 trial | by hand | PF-01 | PASS |
| `test_window_content_encodes_its_trial_id_after_the_gate` | window DC offset = 100 x true trial id; two gate drops (windows 7, 47) | content-decoded id = hand ids = `gated_windows` ids; one class per id | exact | planted | R6, PF-03 | PASS |
| `test_classical_prepare_subject_ids_follow_the_mask` | `prepare_subject` | ids partition = hand ids, non-decreasing | exact | by hand | R6, PF-03 | PASS |

## Mutation checks (temporary edits of `src/`/`scripts/`, restored with `git checkout`; `git status` clean afterwards)

| Mutant | Edit | Failing tests of the new file |
|---|---|---|
| M1 StratifiedKFold over windows | `cv_utils.grouped_cv` returns `StratifiedKFold(5, shuffle, seed)` | 13: all 5 classical + all 4 network split tests, SFS inner (script and direct), planted leak, stratification |
| M2 ids after the gate | `benchmark_runner.prepare_subject` and `benchmark_common.gated_windows` call `build_trial_ids` on the gated `y` | 11: 5 classical + 4 network split tests, window-content alignment, `prepare_subject` ids |
| M3 smoothing across ids | `smooth_probabilities_by_trial`: `same` always True | 3: both smoothing tests and `accuracies` hand case |
| M4 ungrouped SFS inner CV | `inner_sfs_splits` always returns None | 3: feature-selection script, SFS script-level, `column_sets` direct |
| M5 trial length ignored | `build_trial_ids` chunks by 5 for every label | 4 of the id tests (`-k ids` run: 4 failed, 17 passed) |

## Notes
- The split spies patch scikit-learn's two splitter classes, so every split the nine scripts request is seen even if a script bypasses `cv_utils`. The nine: `benchmark_n_subjects`, `benchmark_cross_validation`, `benchmark_feature_selection`, `benchmark_harmonic_fbcca`, `evaluate_confusion_matrix`, `benchmark_eegnet`, `benchmark_compact_cnn`, `benchmark_shallow_convnet`, `benchmark_nn_augmentation`.
- Smoothing on legacy folders: tests of the scripts use the default `mod5`; `trial` is exercised on the library functions (PF-02 diagnostic) as the last P11 decision row states.
- Not covered by me (builders' tests cover them): legacy sha256 byte-identity pins, output directories, N4, demo CSV columns.

Full suite on the final tree: `676 passed, 21 warnings in 337.92s (0:05:37)` (646 builder tests + 30 new).

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```

## Round 1

Status: READY

Audit fix bb4d2ea (`demo_cv_leakage.network_section` pairs A/B CSVs by the splitter label in `.meta.txt`).

| Test id (`tests/test_p11_known_answer.py::`) | Simulates | Expected | Catches bug | Result |
|---|---|---|---|---|
| `test_demo_network_section_skips_leaky_vs_leaky_and_computes_hand_deltas` | synthetic reports tree, two subjects: eegnet = frozen leaky file+meta in both slots; compact_cnn = valid leaky/grouped pair; shallow_conv_net = swapped (grouped in the frozen slot) | eegnet and shallow_conv_net skipped with a printed reason; compact_cnn deltas by hand: OFF S01 -20.0, S02 -10.0; ON S01 -15.0, S02 -18.0; augmentation gain leaky 10.0/10.0, grouped 15.0/2.0 | stale leaky result presented as grouped | PASS |

Mutant M6 (label check removed: `if (so, sn) != ("leaky", "grouped"):` replaced by `if False:`): the new test fails; restored with `git checkout`, tree clean.

Full suite: `678 passed, 21 warnings in 365.55s (0:06:05)`.
