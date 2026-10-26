# P10 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_deep-learning.md, mas/RULES.md, mas/05_PITFALLS.md (PF-28/29/30), mas/03_ROADMAP.md P10

## Tests added

NEW `tests/test_p10_augmentation_known_answer.py` (16 test items, 3.8 s). They extend the builder's `tests/test_p10_augmentation.py` (15 tests, unchanged). Expected values come from the roadmap and analytic reasoning. The A/B script tests stub the trainer, so no network is trained there.

| Test id (`tests/test_p10_augmentation_known_answer.py::`) | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_noise_variance_is_per_channel_fraction_of_that_channels_std` | channels with std 1, 7, 40 and offsets | noise std = 0.05 sigma_c per channel; channels independent | 8 % rel. | analytic | noise from a global std | PASS |
| `test_noise_std_frac_zero_is_identity_and_input_not_mutated` | all four ops | std_frac 0 is identity; inputs never mutated | exact | analytic | in-place ops | PASS |
| `test_scale_factor_shared_across_channels_and_uniform_on_range` | 3000 draws | out/in identical across channels; k ~ U(0.9, 1.1) | 1e-12; KS p > 0.01 | roadmap | one factor per channel | PASS |
| `test_shift_is_circular_not_padded_and_bounded_for_non_round_T` | T = 205 ramp | multiset kept; roll by k in [-20, 20], both signs, all extremes reached | exact | roadmap | zero-padded shift; bound | PASS |
| `test_mixup_fold_mean_matches_analytic_and_never_below_half` | 20000 draws, a=1, b=0 | lambda in [0.5, 1]; mean = E[max(L, 1-L)] by quadrature; a == b returns a | 0.005 | analytic | lambda not folded | PASS |
| `test_dataset_op_order_and_independent_probabilities` | instrumented ops | p=1: exact order mixup, scale, shift, noise; p=0: identity; default p: each 0.5 and P(mixup and noise) = 0.25 | binomial 3 sigma | roadmap | wrong order; no-op; dependence | PASS |
| `test_dataset_does_not_mutate_stored_windows_and_label_is_anchor_label` | p = 1 all, 3 passes | stored X unchanged, label = anchor label | exact | roadmap | in-place mutation | PASS |
| `test_dataset_mixup_only_output_is_convex_combination_within_class` | class levels differ by 10 | output mean within 0.01 of anchor level | 0.01 | PF-29 | cross-class mixup | PASS |
| `test_marker_augmentation_reaches_training_batches_only` | augment replaced by +1000 offset, CV | ON: all training batches carry it; test-fold and train-accuracy passes (10 calls) never; OFF: none | exact | PF-29/PF-30 | aug on test fold, on train-acc pass, no-op ON | PASS |
| `test_augment_seed_is_42_plus_fold_and_train_model_seeds_torch_first` | CV ON, spy on dataset init | seeds 42..46; torch RNG state unchanged by construction | exact | PF-28 | torch RNG consumed | PASS |
| `test_ab_script_values_deltas_arm_order_columns_and_freeze` | stubbed trainer, 2 subjects | OFF then ON, same data and seed; Delta = ON - OFF with sign; train columns not swapped; Mean row; frozen CSV and meta byte-identical | exact | [2] section 6 | OFF-ON deltas, swapped train columns, differing freeze copy | PASS |
| `test_ab_script_no_freeze_without_flag_and_alias_name` | `--model shallow_convnet` | canonical file name; no `legacy_leaky/` without flag | exact | plan | wrong name | PASS |
| `test_warning_threshold_applies_to_off_train_only` (4 params) | OFF train 0.3999, 0.40, 0.0, 0.41 | warns iff < 40 %; ON train < 40 % alone never warns | exact | roadmap, PF-30 | missing warning, wrong arm | PASS |

Mutant check (copy of the branch in a scratch directory; `src/` and `scripts/` in the repo untouched). Each mutant makes at least one test of the new file fail:

| Mutant | Failing test |
|---|---|
| cross-class mixup pool (PF-29) | mixup_only_output_is_convex_combination_within_class |
| noise added to the test-fold input (PF-29) | marker_augmentation_reaches_training_batches_only |
| noise added to the train-accuracy pass (PF-30) | marker_augmentation_reaches_training_batches_only |
| dataset touches the torch RNG (PF-28) | augment_seed_is_42_plus_fold... |
| order scale before mixup | op_order_and_independent_probabilities |
| lambda not folded | mixup_fold_mean_matches_analytic... |
| scale factor per channel | scale_factor_shared_across_channels... |
| zero-padded (non-circular) shift | shift_is_circular_not_padded... |
| noise from global std | noise_variance_is_per_channel_fraction... |
| deltas OFF - ON | ab_script_values_deltas... |
| train accuracy columns swapped | ab_script_values_deltas... |
| warning removed | warning_threshold... (0.3999, 0.0) and ab_script_values_deltas... |
| frozen copy differs from main CSV | ab_script_values_deltas... |
| augmentation never applied | op_order_and_independent_probabilities |
| in-place mutation of stored windows | does_not_mutate_stored_windows... |

## Command

```bash
.venv/bin/python -m pytest tests/ -o addopts="" -q
```

## Output summary

`604 passed, 21 warnings in 212.06s (0:03:32)` (588 before + 16). New file alone: 16 passed in 3.78 s. No bugs found in the builder's code.

## Coverage gaps

- The "initial weights identical OFF/ON" and "OFF regression vs P09" rows are covered by the builder's tests (`test_fold_scope_and_same_init_off_vs_on`, `test_off_path_identical_to_p09`) and were not duplicated. A mutant that builds the dataset before `torch.manual_seed` with torch draws would be caught by that test, not by mine (mine catches any torch RNG use by the dataset).
- The ON-arm trainer itself (actual gradients with augmented batches) is exercised only on the 2-epoch smoke; learning quality is the verifier's run.
- Mixup partner may be the anchor itself (builder deviation); the tests accept it (same class).
- No tolerance was loosened from the plan.

## Reference consultations (R11)

None.

## Sources

1. `mas/03_ROADMAP.md` P10 (opened in this run).
2. `mas/02_REQUIREMENTS.md` section 6; `mas/05_PITFALLS.md` PF-28/29/30.

## Questions
