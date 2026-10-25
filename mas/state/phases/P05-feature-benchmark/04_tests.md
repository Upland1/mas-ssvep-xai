# P05 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_ml-engineer.md, mas/RULES.md, mas/05_PITFALLS.md (PF-04/06/10/11/12/14)
Branch: phase/P05-feature-benchmark; tests commit 8dca3f4

## Tests added

NEW `tests/test_p05_known_answer.py` (30 tests, ~9 s). Expected values come from closed forms or an independent oracle, not from the builder's code. All PASS. "Mutant" = buggy variant defined inside the test file; the paired test asserts the check fails on it (`pytest.raises(AssertionError)`).

| Test id (`tests/test_p05_known_answer.py::`) | Simulates | Expected | Tolerance | Source | Catches (mutant) | Result |
|---|---|---|---|---|---|---|
| `test_reference_signals_closed_form_other_frequency` | f=8.5714, fs 250, T 256, H 3 and 1 | rows sin/cos(2 pi h f n/250), shape (6,256)/(2,256) | 1e-12 | roadmap P05.1 | wrong row order/harmonics | PASS |
| `test_target_freqs_constant` | constant | [24,20,15,10.9091,8.5714] | exact | roadmap | - | PASS |
| `test_chebyshev_design_by_ripple_properties` | `get_chebyshev_subbands(250)` | degree-8 polynomial, edge gain 10^(-3/20)=0.70795, 4 ripple maxima, ~0 at 2 Hz | 5e-4 | Chebyshev-I theory | - | PASS |
| `test_chebyshev_mutants_fail[4]` | Butterworth 4, cheby order 3, 1 dB, 100 Hz edge | check fails on each | - | - | wrong filter family/order/ripple/edge (P04-style Butterworth) | PASS |
| `test_cca_of_pure_tone_is_one_at_fs250_and_not_at_fs256` | 24 Hz tone, refs at fs 250 / 256 / 15 Hz | r=1; <0.8 (measured 0.54); <0.5 | 1e-9 | analytic (tone in span of refs) | PF-04 fs slip | PASS |
| `test_fbcca_argmax_recovers_planted_target_other_seed` | 20 windows, 7 ch, random mixing, noise sd 2 | argmax = planted target, (20,5), scores in [0, 2.4237] | exact | roadmap | - | PASS |
| `test_fbcca_at_wrong_fs_loses_the_24hz_target_margin` | fs 256 vs 250 extraction | 24 Hz score drops >25 % | - | PF-04 | fs 256 silently | PASS |
| `test_fbcca_failure_gives_zero_correlation_not_exception` | constant and zero windows | r = 0 exactly, scores finite, zero window score 0 | exact | roadmap ("0 on failure") | exception on failure | PASS |
| `test_csp_analytic_eigenvalues_and_vector` | S_A=I+15uu^T, S_B=I+15vv^T | eigenvalues 16/17 and 1/17, filters align with u, v (abs cos>0.95), all in (0,1) | 0.03 | analytic | - | PASS |
| `test_csp_filters_solve_the_generalized_eigenproblem_independently` | random 6-ch data, 3 classes, m=2 | filters/eigenvalues equal an independent `eigh(St, St+Sr+1e-6 I)` (m largest desc, m smallest) | 1e-9 / cos>1-1e-8 | roadmap | wrong ridge/ordering | PASS |
| `test_csp_features_log10_ratio_and_variance_floor` | zero window; hand filters with a zero component | log10(1/2) for floored variances; log10(v/(v+1e-12)) | 1e-9 | roadmap (1e-12 floor) | missing floor | PASS |
| `test_csp_unnormalised_covariance_mutant_is_detected` | one window with channel 3 x1000 | real filters keep abs cos>0.95; un-normalised CSP does not | - | roadmap (trace normalisation) | no trace normalisation | PASS |
| `test_fbcsp_layout_band_major_class_known_answer` | 5 classes, 5 bands, 7 ch | (n,50) equals independent scipy Butterworth+eigh oracle column by column, order band, class, component | 1e-6 | roadmap, R6 | - | PASS |
| `test_fbcsp_layout_mutants_fail[2]` | class-major/band-minor columns; flipped component order | oracle check fails | - | R6 | swapped band/class order | PASS |
| `test_continuous_psd_closed_form_amplitude_and_channel_major_position` | on-bin tone A=6 in channel 2 only | feature 64 = A^2 N/(2 fs) = 18.432, others ~0; (1,210); bins 6..35 * 250/256 (5.859...34.180 Hz); fs 256 gives 31 bins | rtol 1e-9 | periodogram scaling | wrong fs / channel-minor flatten | PASS |
| `test_harmonic_psd_picks_po8_o1_oz_o2_by_name_with_closed_form_power` | 3 channel orders, per-channel 15 Hz on-bin tones (3..9) | harmonic (n,32); column 8r+2 = A^2*0.512 for A(PO8,O1,Oz,O2)=6,7,8,9; P04 set (POz,O1,Oz,O2) fails | rtol 1e-6 | 01_DATA_SPEC §6, PF-06 | P04's POz set / positional pick | PASS |
| `test_infold_csp_gives_chance_on_label_free_noise_and_full_data_csp_does_not` | pure noise, 100 windows, FBCSP + Shrinkage-LDA, legacy CV | in-fold 0.23 (<=0.35); CSP fitted on all windows 0.67 (>0.45, gap >=0.15) | - | chance = 0.20 | PF-11 leaky CSP | PASS |
| `test_fold_matrices_fit_csp_on_training_rows_only` | spy on `FBCSPTransformer.fit` inside `fold_matrices` | each fit receives exactly the training rows and labels (5 fits) | exact | PF-11 | fit on all rows | PASS |
| `test_fold_matrices_spy_detects_a_leaky_fold_function` | all-rows fit | the spy criterion fails | - | PF-11 | leaked fit | PASS |
| `test_single_mask_removes_window_from_every_block_under_stricter_threshold` | window with std ~30 | shared gate keeps it in every block; std_max 25 removes it from y, psd, harmonic, fbcca, subbands alike; separate-gate mutant gives different block lengths | exact | PF-10 | blocks gated separately | PASS |
| `test_blocks_receive_the_same_mask_object` | spies on PSD and FBCCA extractors | same non-None `valid_mask` = returned mask | exact | PF-10 | per-extractor gating | PASS |
| `test_suite_parameter_table_via_get_params` | `get_sklearn_model_suite()` under warnings-as-errors | 10 models, every roadmap parameter via `get_params`, `l1_ratio` 0/1/0.5, QDA reg 0.5, no warning, seed reaches SGD | exact | roadmap P05.4 | wrong parameter/deprecated `penalty` | PASS |
| `test_benchmark_models_exclude_qda` | `run_benchmark` with spy on `oof_space` | 6 spaces each get 9 models without QDA; only the argmax row is extra | exact | PF-12 | QDA in benchmark | PASS |
| `test_legacy_smoothing_hand_example_crosses_trials` | rows 0..9 | out[j]=(p[j-1]+p[j])/2 incl. j=5; mod-5 diagnostic resets | exact | R8 legacy | trial reset in legacy path | PASS |
| `test_legacy_cv_splits_equal_independent_construction` | y 5x40 | folds equal independent `StratifiedKFold(5, True, 42)`; a trial straddles train/test | exact | R1 legacy | grouped/unshuffled CV | PASS |
| `test_flagship_script_runs_as_module_on_synthetic_tree` | `python -m scripts.evaluation.evaluate_confusion_matrix` as subprocess | exit 0, legacy label printed, CSV 100 clean / 0 rejected / m=1 | exact | [own] | entry-point break | PASS |

Mutant proofs: the mutant tests (Chebyshev x4, layout x2, un-normalised CSP, leaky CSP, leaky spy, separate-gate mask, PF-04 fs, P04 cluster set) pass only because the check under test fails on the buggy variant. The headline PF-11 gap is 0.23 (in-fold) vs 0.67 (leaked), measured by running both in the test body.

Plan rows already covered independently by the builder and not re-done: Chebyshev numerical equality with `scipy.cheby1`, QDA rank-failure caught, scripts smoke on a synthetic tree (benchmark_cross_validation, harmonic_fbcca, test_sklearn_models, visualize_data), P04 re-exports (`tests/test_p05_feature_benchmark.py`, `tests/test_no_leakage.py`).

## Command

```bash
python -m pytest tests/ -q
```

## Output summary

- `tests/test_p05_known_answer.py`: 30 passed, ~9 s.
- Full suite (collected 413 = 383 builder-reported + 30 new), `.venv/bin/python -m pytest tests/ -q -p no:warnings`: all dots, exit code 0, wall time `real 2m0.778s` (user 5m17 s) on this machine, above the "about a minute" target. My file adds ~9 s; the builder reported 111 s for 383 tests, so the overhead predates this step (P04 CNN/ML smoke, P05 script tests).
- The summary line was swallowed by `tail -3` after `time`; the single-file run gave `30 passed`. I did not re-run the 2 min suite just to capture the line.

## Bugs found

None. No test exposed a defect in `src/`, `scripts/` or `configs/`.

## Coverage gaps

- Real-data counts (197 kept / 3 rejected) and R-3 accuracies are out of scope for synthetic tests (verifier).
- The CSP normalisation choice (per-class sum over its 2m projections, the builder's flagged deviation) is checked against the roadmap wording; my oracle uses the same reading, so it is not validated against R-3 here. If the verifier's S03 run misses R-3, this is the first suspect.
- The layout oracle uses m=1; m=2 is covered only by the builder's shape test and my m=2 eigenproblem test.
- The full suite exceeds one minute (2 min); not caused by this file.

## Reference consultations (R11)

None. The original repository snapshot was not opened.

## Sources

1. `mas/03_ROADMAP.md` P05 tasks (via 00_assignment.md) and `02_plan.md` "Tests required" (opened in this run).
2. `mas/05_PITFALLS.md` PF-04/06/10/11/12/14; `mas/01_DATA_SPEC.md` §6 (via plan); `mas/RULES.md` (opened).
3. Closed forms derived analytically: boxcar periodogram density A^2 N/(2 fs); Chebyshev-I ripple level 10^(-ripple/20); CSP eigenvalues 16/17, 1/17 for S = I + 15 uu^T; checked by running scipy/sklearn in `.venv`.

## Questions

## Round 2

Status: READY
Tests commit: eb613db. NEW `tests/test_p05_round2_known_answer.py` (10 tests, ~12 s). Expected values from the definitions in the last three P05 rows of `mas/state/decisions.md`; synthetic data only; mutants defined in the test file.

| Test id (`tests/test_p05_round2_known_answer.py::`) | Simulates | Expected | Source | Catches (mutant) | Result |
|---|---|---|---|---|---|
| `test_accuracies_uses_trial_reset_at_i_mod_5` | 10 windows, two trials; row 5 weakly correct [0.45, 0.55] | `le.accuracies` 2.0 s = 1.0 (i%5); no-reset would give 0.9 | decision (1) | no-reset reported | PASS |
| `test_accuracies_mutant_no_reset_fails` | `smooth_reported` monkeypatched to the no-reset helper | returns 0.9, so the exact-1.0 check fails | decision (1) | no-reset reported | PASS |
| `test_trial_reset_is_on_clean_array_index_not_trial_ids` | 12 rows | output [0, .5, 1.5, 2.5, 3.5, 5, 5.5, 6.5, 7.5, 8.5, 10, 10.5] | decision (1) | reset at wrong index | PASS |
| `test_reported_flagship_csv_uses_i_mod_5` | flagship script on a noisy synthetic tree, spy on out-of-fold scores | CSV 2.0 s = independent i%5 accuracy (2 dp); i%5 and no-reset values differ on this tree; labels | decision (1) | CSV written with no-reset | PASS |
| `test_argmax_baseline_row_is_smoothed_with_i_mod_5` | benchmark FBCCA argmax row | equals independent i%5 on row-normalised FBCCA scores | decision (1) | argmax row left on no-reset | PASS |
| `test_mask_limits_are_0p5_120_and_0p1_35` | constant | exact dict | decision (2) | old 5/1 | PASS |
| `test_window_with_vpp2_std0p5_is_kept_by_default_gate_and_rejected_by_old_limits` | window vpp 2 / std 0.5 on all channels | kept by gate, PSD, FBCCA and block builder; rejected under 5/1 (check fails on that mutant); vpp 0.4, vpp 0.1 and vpp 130 rejected | decision (2) | old limits | PASS |
| `test_fbcca_block_uses_named_cluster_channels_in_cluster_order` | three channel-name orders | FBCCA block = extractor on PO8, O1, Oz, O2 columns with the shared mask (1e-9); differs from all-channel and from POz set | decision (3), PF-06 | positional/wrong set | PASS |
| `test_mask_stays_shared_when_only_a_non_cluster_channel_is_bad` | artefact on PO3 only | window removed from psd, harmonic, fbcca, subbands, y (n-1); own 4-channel gate keeps it (length mismatch) | decision (3), PF-10 | FBCCA gated separately | PASS |
| `test_harmonic_script_requests_the_visual_cluster` | script run with spy on `prepare_subject` | called with `fbcca_channels` = PO8, O1, Oz, O2; names in console and report | decision (3) | script still all-channel | PASS |

Round 1 tests: none edited. Each Round 1 test that touches the changed definitions still holds under the new decisions and was left as is: the PF-10 single-mask test passes explicit strict (5/1/std_max 25) thresholds and its planted window (std ~30, vpp 60) passes the new default too; `test_legacy_smoothing_hand_example_crosses_trials` and the CV test pin the helper functions (no-reset and mod-5 as functions), which are unchanged; the FBCCA, CSP, PSD and layout tests use `valid_mask` or clean windows. The builder's own tests that pinned old definitions were updated by the builder (see its Round 2 section), not by me.

Command and result (verbatim summary line):

```bash
.venv/bin/python -m pytest tests/ -o addopts="" -q
```
`426 passed, 10 warnings in 106.25s (0:01:46)`

No bugs found in Round 2. Coverage gap: the real-data effect (197/3 count under the new limits, R-3 2.0 s) is for the verifier.
