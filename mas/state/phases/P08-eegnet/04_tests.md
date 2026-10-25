# P08 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_deep-learning.md, mas/RULES.md, mas/05_PITFALLS.md

## Tests added

NEW `tests/test_p08_eegnet_known_answer.py` (10 tests, about 3 s), added to the builder's `tests/test_p08_eegnet.py` (15 tests, kept). Data are synthetic (`tests/p05_synth.make_windows`, fixed seeds), 256 samples as the legacy folders; expected values from R-8 arithmetic, sklearn and hand calculation, not from the builder's code.

| Test id (`tests/test_p08_eegnet_known_answer.py::`) | Simulates | Expected | Tolerance | Source | Catches (mutant run, all fail as intended) | Result |
|---|---|---|---|---|---|---|
| `test_layer_by_layer_parameter_arithmetic` | `EEGNetSSVEP()` | 1000+16+112+32+256+256+32+645 = 2,349; shapes per layer; no conv bias | exact | R-8 arithmetic | conv with bias | PASS |
| `test_padding_keeps_length_and_flatten_is_128` | forward through layers | 256 -> 256 (pad 62) -> 65 (pad 8) -> flatten 16x8 = 128 | exact | roadmap P08.1 | padding 0 on temporal conv; padding 0 on depthwise (1,16) | PASS |
| `test_depthwise_spatial_group_structure` | gradient of spatial output 5 | depends only on map 5//2, all 7 electrodes contribute | exact | grouped-conv definition | wrong axis / groups | PASS |
| `test_max_norm_known_scaling_direction_and_layer` | filter norms 3, 2.8, 0.5; pointwise and depthwise2 scaled x20 | norm 3 -> 1 with direction kept; 0.5 untouched; other layers bit-identical | 1e-6 | max-norm definition | no-op max-norm; max-norm applied to pointwise | PASS |
| `test_max_norm_holds_after_training_with_large_steps` | `train_model`, lr 0.5, 3 epochs | all 16 spatial filter norms <= 1+1e-6; pointwise norm > 1 | 1e-6 | [2] | max-norm not called after optimizer steps; max-norm on pointwise | PASS |
| `test_zscore_scaling_one_window_changes_no_other_and_constant_is_finite` | scale/offset window 2 | other windows bit-identical; constant channel -> finite zeros | exact / 1e-4 | R2 | z-score with dataset (global) statistics | PASS |
| `test_seed_per_fold_and_folds_are_stratifiedkfold_5_true_42` | spy on `train_model`/`predict_proba` in the CV | seeds 42..46 (7..11 for seed 7); train and held-out rows equal sklearn `StratifiedKFold(5, True, 42)` | exact | PF-28, R1 legacy | seed set once; CV with another seed | PASS |
| `test_train_accuracy_is_on_training_rows_pf30` | recompute each fold model's accuracy on its own training rows | equals reported `train_accuracy` | 1e-12 | PF-30 | train accuracy computed on test rows (also tripped by the row-spy test) | PASS |
| `test_smoothing_resets_at_i_mod_5` | 10 windows, window 4 confidently wrong for window 5 | smoothed accuracy 1.0 (no-reset gives 0.9) | exact | R8 legacy | smoothing without the i%5 reset | PASS |
| `test_cuda_forward_matches_cpu` | same weights, eval, CPU vs CUDA | agree | 1e-4 | — | CUDA path (skipped without a device) | PASS (CUDA present) |

Mutants were applied to a scratch copy of the tracked `src/` tree (scratchpad, not the repo), one at a time; each of the 11 mutants failed at least one test above, the unmutated copy passed 10/10. Additional mutants checked: pad-0 and bias also trip the parameter test.

## Command

```bash
.venv/bin/python -m pytest tests/ -o addopts="" -q
```

## Output summary

`528 passed, 21 warnings in 192.01s (0:03:12)` (518 before + 10 new). Builder's 15 P08 tests and the new 10 pass. No bugs found in the builder code.

## Coverage gaps

- Script smoke, determinism, learnable task, shapes for 8/128/512: covered by the builder's tests, not duplicated.
- The suite takes about 3 minutes, above the "about a minute" target; the P08 files add about 11 s of it.
- No test of a real S03 run (verifier's job).

## Reference consultations (R11)

None.

## Sources

1. `mas/state/phases/P08-eegnet/02_plan.md` (Tests required), `03_changes_deep-learning.md` (opened in this run).
2. `mas/RULES.md` (R1, R2, R8, era matrix).

## Questions
