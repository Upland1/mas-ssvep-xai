# P15 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 00_assignment.md, 02_plan.md, 03_changes_connectivity-stats.md, 03_changes_deep-learning.md, decisions.md P15 row, mas/RULES.md
Branch: phase/P15-graph-gnn

No builder bug found. All tests are in the NEW file `tests/test_p15_known_answer.py` (38 test cases, own generators and numpy/scipy references, synthetic data only, no generated or ignored file is read). The only builder helper used is `tests/p05_synth.write_subject`, to create a synthetic legacy tree for the cache test. The builders' tests are untouched.

## Tests added

| Test id (in `tests/test_p15_known_answer.py`) | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_node_power_tone_lands_in_harmonic_major_column` (10 cases) | tone at each target and each 2nd harmonic, one channel, fs 250 | argmax cell = (channel, h*5+k) | exact | analytic, R6 | class-major layout | PASS |
| `test_node_power_hand_check_log10_of_mean_over_pm1hz_bins` | fs 16, T 16 (1 Hz bins), random signal | log10 of mean power over +-1 Hz bins, own periodic-Hann FFT | 1e-9 | analytic | sum instead of mean, layout | PASS |
| `test_node_power_nearest_bin_fallback` | fs 16, T 4, target 5.5 Hz (no bin within 1 Hz) | nearest bin (4 Hz); 2nd harmonic 11 Hz -> 8 Hz bin | exact | analytic | no fallback | PASS |
| `test_edge_coherence_matches_scipy_welch_three_segments` | random coupled windows | equals `scipy.signal.coherence(nperseg=128, noverlap=64, hann, constant)` band-averaged (3 segments) | 1e-9 | scipy, independent | wrong nperseg/step/segment count | PASS |
| `test_edge_coherence_coupled_pair_high_independent_low_symmetric` | 20 Hz tone shared by channels 1 and 4 plus noise | edge (1,4) > 0.9 and the maximum by a margin 0.1, others mean < 0.5; symmetric, diagonal 1, in [0,1] | see test | analytic | wrong edge index | PASS |
| `test_edge_phase_known_lag_is_unit_phasor_cos_sin` | bin-centred tone, amplitude 3, four phases | `[i,j]` = (cos(phi_i-phi_j), sin(...)); `[j,i]` conjugate | 1e-6 | analytic | phasor not normalised, sign of lag | PASS |
| `test_edge_phase_unit_norm_for_noise_default_targets` | noise | norm 1 everywhere, diagonal (1,0) | 1e-9 | analytic | phasor not normalised | PASS |
| `test_upper_tri_flat_pair_major_then_band_then_cs` | index-coded `(n,5,5,5,2)` array | pair-major, then band, then cos/sin | exact | own loops, R6 | wrong flatten order | PASS |
| `test_feature_set_dimensions_follow_channel_count` (C = 7, 6) | arrays with C channels | all nine set widths (7: 70/5/75/105/210/315/180/285/390; 6: 60/5/65/75/150/225/140/215/290); `build_inputs` dims | exact | formulas | hardcoded channel count | PASS |
| `test_gate_verdict_cohort_mean_passes_but_responders_fail_gives_no_pass` | hand deltas: mean >= 2 pp, 0 of 3 responders | no pass | exact | plan point 3 | verdict on mean only | PASS |
| `test_gate_verdict_cases` | hand deltas: all pass; mean 1.58; 2 of 3 plus mean; mean < 2 with 3 of 3; 1 of 3; best set by cohort mean | per rule | exact | plan point 3 | verdict rule | PASS |
| `test_gate_r1_no_trial_shared_for_every_repeat` | spy on `make_splits` in `evaluate_subject`, 3 repeats | cv "grouped", seeds 42, 43, 44, no shared trial id | exact | R1, PF-01 | window-level split | PASS |
| `test_gate_r2_test_row_values_do_not_move_other_predictions[0,30]` | one test row set to 1e6 | other test rows' predictions and scores bit-identical (k = 0 and 30) | exact | R2 | full-data scaler / selector | PASS |
| `test_gate_scaler_is_in_fold_shifted_test_rows_do_not_move_the_others` | two test rows shifted by +-1e4 | other test rows' scores bit-identical | exact | R2 | full-data scaler | PASS |
| `test_gate_r2_selector_pure_noise_stays_at_chance` | 600 noise features, random labels, k = 30, grouped CV | mean accuracy < 0.30 (chance 0.20) | see test | R2 | selection on all rows (not mutation-tested) | PASS |
| `test_accuracies_mod5_matches_hand_smoothing_and_differs_from_trial_rule` | trial ids misaligned with i % 5 | 2.0 s equals own mod5 smoothing; the trial rule is separate | exact | R8 legacy clause | wrong smoothing rule | PASS |
| `test_both_benchmarks_request_the_mod5_rule` | spy on `accuracies` in gate and GNN | both pass "mod5" | exact | R8 | trial rule on legacy | PASS |
| `test_stale_cache_guard_rebuild_and_legacy_arrays_never_written` | synthetic tree; valid cache reused, `--rebuild`, stale hash | loader raises `StaleGraphDataset`; builder rebuilds; sha256 and mtime of every legacy file unchanged; `save_graph_dataset` refuses a `.npy` | exact | plan "Cache" | stale reuse, legacy overwrite | PASS |
| `test_fingerprint_depends_on_fs_thresholds_and_feature_source` | vary fs, channel-fail fraction, thresholds, feature source file | hash changes each time | exact | plan "Cache" | hash ignoring inputs | PASS |
| `test_standardizer_uses_training_rows_only` | test rows shifted by 1e4/50/1e3 | statistics equal numpy on train rows; train z-scores mean 0, std 1; test stays shifted | 1e-4 | R2 | standardizer on all rows | PASS |
| `test_gnn_r1_no_shared_trial_and_fold_seeds` | spy on `make_splits` and `train_fold`, r = 0..2 | seeds 42+r, no shared trial, fold seeds 1000 r + fold | exact | R1, PF-28 | window split, seeds | PASS |
| `test_gnn_evaluate_variant_is_deterministic` | same call twice | identical dict | exact | PF-28 | unseeded training | PASS |
| `test_gnn_standardizer_fitted_on_train_rows_in_the_benchmark` | spy on `fit_standardizer` | indices equal each fold's training set, disjoint from test | exact | R2 | standardizer on all rows | PASS |
| `test_parameter_counts_exact` | `ConnectivityGNN(7, 10, 0 or 5, 5)` | 5,150 and 5,534; no bias on W_self/W_msg | exact | R-8 | bias=True | PASS |
| `test_embedding_init_is_normal_0_0p1` | 400 x 64 embedding | mean < 0.005, std in (0.095, 0.105) | loose | task 5 | wrong init | PASS |
| `test_edge_gated_layer_matches_numpy_reference_including_no_self_messages` | tiny layer, with and without gate | equals own numpy forward (sigmoid gate `[b,i,j]`, mean over j != i, ELU, residual LayerNorm) | 1e-5 | analytic | self messages, bias | PASS |
| `test_full_forward_matches_numpy_readout_mean_max_then_graph_features` | tiny network | equals numpy: encoder + embedding, layers, concat(mean, max), graph features, head | 1e-4 | analytic | readout order | PASS |

## Mutation checks (each applied, run, restored with `git checkout`)

| Mutant | File | Tests that failed |
|---|---|---|
| bias=True on W_self/W_msg | `src/models/graph/connectivity_gnn.py` | `test_parameter_counts_exact`, layer and full-forward numpy tests |
| class-major node layout | `src/features/connectivity/connectivity_graph_features.py` | 8 of the tone-layout cases, `test_node_power_hand_check_...` |
| full-data scaler in the gate (scaler fitted on train+test inside `oof_space`) | `src/models/classical/legacy_eval.py` | both `test_gate_r2_test_row_values_...` cases, `test_gate_scaler_is_in_fold_...` |
| window-level split in the gate | `scripts/connectivity/graph_modeling/benchmark_connectivity_gate.py` | `test_gate_r1_...`, `test_both_benchmarks_request_...` |
| window-level split in the GNN benchmark | `scripts/connectivity/graph_modeling/benchmark_gnn.py` | `test_gnn_r1_...`, determinism, standardizer-in-benchmark, `test_both_benchmarks_...` |
| verdict on the cohort mean only | `benchmark_connectivity_gate.py` | `test_gate_verdict_cohort_mean_passes_...`, `test_gate_verdict_cases` |
| standardizer fitted on all rows | `src/features/connectivity/graph_inputs.py` | `test_standardizer_uses_training_rows_only` |
| phasor not normalised | `connectivity_graph_features.py` | `test_edge_phase_known_lag_...`, `test_edge_phase_unit_norm_...` |
| self-messages included | `connectivity_gnn.py` | layer and full-forward numpy tests |

`git status` after the mutations showed only the new test file (all mutants restored). The SelectKBest-on-all-rows variant was not mutated; its test is a statistical guard.

## Notes

- Independent noise gives 3-segment MSC up to about 0.95 in single pairs (small-sample bias, the R4 object of the gate), so the coherence test asserts a margin and a mean, not a hard per-pair ceiling.
- The scipy reference confirms 3 Hann segments (nperseg 128, step 64) for 256 samples.

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```

Result: `948 passed, 21 warnings in 436.95s (0:07:16)`. New file alone: `38 passed in 9.01s`.
