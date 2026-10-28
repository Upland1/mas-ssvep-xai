# P20 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_*.md, mas/RULES.md, mas/05_PITFALLS.md

Independent file `tests/test_p20_independent_known_answer.py` (NEW, 21 tests, ~8 s, CPU, synthetic built folder from
`tests/p16_synth.py`; the builders' test files are untouched). Expected answers are re-derived independently (own Wolpaw
formula, principal-angle CCA, own stopping rule, `np.fft`, scipy `sosfilt`).

## Tests added

| Test id (in the file above) | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_sweep_predictions_are_in_seconds_and_cover_each_window_once_per_run` | window sweep on a synthetic built folder (fbcca, lda x2, cnn) | offsets {0..4} s, end <= 5 s, each window once per run, fbcca `p_*` empty, probabilities sum to 1 | 1e-6 | analytic | offset_sec in samples (build fix 54156df) | PASS |
| `test_end_to_end_sweep_to_dynamic_stopping_matches_independent_rule` | shuffled predictions.csv -> `simulate_dynamic_stopping` CLI | every (method, run, trial, threshold) decision, time, forced flag equal an independent rule; fbcca skipped; ITR = Wolpaw at T = mean time + 0.5 s | exact / 1e-4 | own re-implementation | no (trial, offset) sort, time without window, no gaze in ITR, samples as seconds | PASS |
| `test_threshold_is_inclusive_forced_flag_and_time_rule` | hand-built probability sequences, reversed order, window before skip | hit at max == threshold, forced at last window with time = offset + window | exact | hand | `>` vs `>=`, no sort, skip off by one | PASS |
| `test_itr_wolpaw_values_across_modules` | four ITR helpers (sweep, NN sweep, stopping, pseudo-online) | P = 1 gives log2(5)*40; P <= 0.2 gives 0; P = 0.8, T = 2 gives 36.0 bits/min | 1e-3 / 1e-12 | analytic | modules diverging | PASS |
| `test_nn_sweep_compact_equals_window_sweep_cnn_at_identical_seeds` | NN sweep `compact` vs window-sweep `cnn (compact_eegnet)`, 1 s, 2 epochs | same probabilities per (trial, offset) | 1e-5 | contract | different seeds/splits, offsets in samples | PASS |
| `test_cnn_cv_never_puts_a_trial_in_train_and_test_and_validation_inside_training` | `run_cell` with `cnn_fold` spy, 2 repeats x 5 folds | no trial on both sides; validation trials inside training trials, disjoint from fitting and test | exact | R1, PF-32 | window-level split, validation from test | PASS |
| `test_normalisation_statistics_come_from_fitting_windows_only` | `fit_network` with `fit_stats` spy | stats input equals `X[fit_idx]`, no validation window | exact | R2 | stats over all training windows | PASS |
| `test_test_only_perturbation_does_not_change_training_or_other_predictions` | `cnn_fold`, other test windows scaled x50 + 1e3 | train/val acc, best epoch, val loss identical; the untouched test windows give the same proba | 1e-7 | R2 | test statistics at predict | PASS |
| `test_lda_fold_scaler_and_csp_ignore_test_rows` | `lda_fold`, half the test rows perturbed | train acc identical, other test rows unchanged | 1e-9 | R2 | CSP/scaler fitted on test | PASS |
| `test_fbcca_vectorized_matches_independent_principal_angle_cca` | random windows, T = 128/256/384 | scores equal sum_b w_b cos^2(min principal angle) over 3 bands; no cross-window dependence | 1e-10 | scipy `subspace_angles` | uncentred references, wrong weights | PASS |
| `test_fbcca_planted_tone_wins_and_dc_offset_is_ignored` | tone at each stimulus frequency, +1000 DC | argmax = planted class; DC no effect | 1e-8 | analytic | — | PASS |
| `test_chunked_filter_equals_independent_one_pass_and_chunk_size_is_irrelevant` | chunks 1..3000 with DC 40 | equals scipy `sosfilt` with `zi = sosfilt_zi * x[0]` | 1e-10 | PF-38 | zi not carried | PASS |
| `test_replay_windows_ignore_future_samples_and_chunking` | future samples (after 4000) replaced | windows ending before are bit-identical; chunk size irrelevant; clock = k*stride | exact / 1e-9 | PF-38 | state or window leaking the future | PASS |
| `test_decide_period_rest_class_never_decides_and_excluded_from_threshold` | rest-heavy probabilities | no decision unforced; forced pred in 0..4; hit time rule; threshold inclusive | exact | analytic | rest in the threshold rule | PASS |
| `test_score_stream_decisions_fall_in_the_right_periods_and_never_use_the_future` | synthetic MARK, planted per-period class | 6 correct decisions at 1.0 s, no false activation; scrambling later windows leaves the decision | exact | analytic | — | PASS |
| `test_score_stream_six_class_rest_never_decides_and_false_activation_counts` | 6-class, rest-dominant, then 101-dominant | no target decisions; 101 in rest periods counts as false activation | exact | analytic | rest decides | PASS |
| `test_pseudo_online_stream_probabilities_ignore_mark_and_future_samples` | `run_window_length`, MARK zeroed; stream altered after 100 s | identical proba/valid/kept; earlier windows unchanged; 5 and 6 columns | 1e-7 | PF-38 | MARK or future in inference | PASS |
| `test_ccnn_spectrum_bin_scaling_and_nfft[fs,T]` x4 | cos/sin tones at 15 Hz, (256,256), (256,512), (250,250), (256,2048) | nfft = max(T, fs/0.25); bins span [3,50]; real = A/2, imag = -A/2 at the tone bin; [real, imag]/T equals np.fft | 1e-6 | analytic | no /T, imag first, nfft = T | PASS |

## Mutants (scratch copy `mas/state/scratch/p20_mut/`, 21 independent tests run against each)

All 18 killed; baseline copy 21 passed.

| Mutant | Killed by |
|---|---|
| M1 window-level split (`legacy` splits, no guard) in window sweep | NN-vs-sweep equality; grouped-CV spy |
| M2 `zi` not carried in `CausalSOSFilter` | chunked filter; replay |
| M3 sweep offsets not divided by fs | seconds test; end-to-end; NN-vs-sweep |
| M3b NN-sweep offsets not divided by fs | NN-vs-sweep |
| M4 normalisation stats over all training windows | fit-stats spy |
| M4b validation split at window level | grouped-CV spy, fit-stats, perturbation, pseudo-online (guard raises) |
| M4c test-set statistics at predict | perturbation |
| M5 threshold `>` instead of `>=` | inclusive threshold |
| M6 no (trial, offset) sort | end-to-end; inclusive threshold |
| M7 time without window length | end-to-end; inclusive threshold |
| M7b ITR without the 0.5 s gaze | end-to-end |
| M8 rest class inside the threshold rule | decide_period; six-class |
| M9 CCNN without `/ T` | spectrum x4 |
| M9b CCNN [imag, real] | spectrum x4 |
| M10 nfft = T | spectrum x3 |
| M11 FBCCA references not centred | principal-angle CCA |
| M12 skip `>` instead of `>=` | inclusive threshold |
| M13 MARK reaches the stream signal | pseudo-online MARK erasure |


## Command

```bash
.venv/bin/python -m pytest tests/ -q -o addopts=""
```

## Output summary

Full suite (log `mas/state/scratch/p20_full_suite.log`): `1297 passed, 22 warnings in 781.21s (0:13:01)`.
New file alone: `21 passed in 8.46s`. No defect found in the builders' code.

## Coverage gaps

- Built synthetic folders hold 5 windows per trial at stride 1 s (stride of `p16_synth`), not the 17 windows of stride 0.25 s; the
  contracts are unit-independent, offsets in seconds are checked against `window_offsets` in samples.
- CCNN learning above chance, GPU runs and real recordings are not exercised here (builders' tests / verifier).
- Pseudo-online fallback retrain and channel drop at the 30 s check are covered by the builders' tests only.

## Reference consultations (R11)

None.

## Sources

1. `02_plan.md` tests 1-9, settled points 1-12; `mas/05_PITFALLS.md` PF-31, PF-32, PF-38.

## Questions

None.
