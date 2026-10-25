# P04 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_ml-engineer.md, 03_changes_deep-learning.md, mas/RULES.md, mas/05_PITFALLS.md

## Tests added

All in `tests/test_p04_early_models_known_answer.py` (NEW; synthetic, CPU, fs 250 legacy assumption). Rows marked (M) are mutant tests: the same check is run against the buggy variant and the test passes only if the check fails on it. Expected values come from the plan/roadmap and analytic reasoning.

| Test id (`::`) | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| test_harmonic_features_channel_major | `X_psd` with 1000i+100c+j | feature 8r+c = channel (1,4,5,6)[r], bin (4,6,10,12,15,17,19,25)[c] | exact | plan, R6 | — | PASS |
| test_mutant_frequency_major_harmonic_flatten_fails | bin-major flatten | check raises | — | R6 | frequency-major flatten (M) | PASS |
| test_harmonic_bins_are_9_11_15_17_20_22_24_30_hz | bin grid | indices and Hz as listed | exact | plan | wrong bins | PASS |
| test_keep_channel_names_asserted_pf06 | config scalp names; PO7-prefixed and reversed layouts | POz,O1,Oz,O2 accepted; others raise | exact | PF-06 | positional channels pointing elsewhere | PASS |
| test_tensor_builder_known_layout | same marker array | `[i,0,r,c]` = feature 8r+c, shape (n,1,4,8) | exact | plan, R6 | — | PASS |
| test_mutant_tensor_frequency_major_fails | transposed layout | check raises | — | R6 | frequency-major tensor (M) | PASS |
| test_fbcca_weights_and_harmonics | weights, harmonics, reference columns | 1.25, 0.6704, 0.5033; 2,2,3,3,3; sin/cos at h·f, t=arange/250 | 1e-4 | plan | wrong weights/harmonics | PASS |
| test_fbcca_target_wins[101..105] | 7-ch sinusoid at each target, fs 250, noise | argmax = k; scores in [0, sum w] | — | plan | wrong reference/band | PASS x5 |
| test_fbcca_uses_all_seven_channels | tone on channel 0 only | target 103 wins | — | plan, decisions.md | CCA on kept channels only | PASS |
| test_fbcca_legacy_fs_250_vs_256 | 24 Hz at 256 Hz, fs 250 vs 256 | scores differ; fs 256 picks 101 with a higher score; default = 250 | — | PF-04 | — | PASS |
| test_mutant_fbcca_fs_256_default_fails | default fs 256 | check raises | — | PF-04 | FBCCA at 256 (M) | PASS |
| test_in_fold_scaling_matches_hand_per_fold | offset +50 only in fold-0 test rows | `oof_predictions` == hand per-fold scaler + LR | 1e-9 | R2 | — | PASS |
| test_mutant_scaler_fit_on_all_windows_fails | scaler fitted on all windows | probabilities differ from in-fold | 1e-6 | R2 | leaked scaler (M) | PASS |
| test_legacy_cv_splits_equal_stratified_kfold_5_true_42 | recording estimator inside `run_evaluation` | train/test row ids of the 5 folds == `StratifiedKFold(5,True,42)` | exact | R1 legacy | — | PASS |
| test_mutant_other_seed_cv_fails | random_state 0 | check raises | — | R1 | wrong CV (M) | PASS |
| test_smoothing_legacy_no_reset | 10x5 probabilities | p0 kept; p_j=(p_{j-1}+p_j)/2 incl. j=5 | 1e-15 | PF-02 | — | PASS |
| test_mutant_trial_aware_smoothing_fails | reset at j%5 | pinned legacy check raises | — | R8 legacy | trial-aware smoothing (M) | PASS |
| test_cnn_temporal_smoothing_is_legacy | rows 4 and 5 averaged across the boundary | accuracy 1.0; trial-aware variant (monkeypatched) 0.9 | exact | PF-02 | trial-aware smoothing (M) | PASS |
| test_temporal_integration_eval_uses_legacy | random probabilities | predictions/accuracy = argmax of no-reset average | exact | PF-02 | — | PASS |
| test_fusion_cnn_params_10005_no_conv_bias | instantiate | 10,005 trainable; 2 convs, bias None | exact | R-8 | — | PASS |
| test_mutant_conv_with_bias_fails | convs with bias | 10,053 (= 10,005+16+32); check raises | exact | R-8 | conv biases (M) | PASS |
| test_fusion_forward_shape_and_both_branches_get_gradients | (6,1,4,8), (6,5) | out (6,5); non-zero grads in spatial, FBCCA, head | — | plan | dead branch | PASS |
| test_cnn_cv_deterministic_and_seed_sensitive | 2-epoch CV twice on CPU; seed 7 | identical pred/proba; different seed differs; rows sum to 1 | exact | PF-28 | nondeterminism, seed no-op | PASS |
| test_cnn_scalers_fitted_on_training_fold_only | offset +40 in fold-0 test rows | scaler means == training-fold means | 1e-12 | R2 | — | PASS |
| test_mutant_cnn_scalers_fitted_on_all_windows_fails | scalers fit on all windows | check raises | — | R2 | leaked CNN scalers (M) | PASS |
| test_xai_weight_arrays_channel_major | `coef_ = arange(5*37)` | `sp[k,r,c] = 37k+8r+c`; fb = `coef[:, -5:]`; (5,36) raises | exact | R6 | — | PASS |
| test_mutant_frequency_major_lda_reshape_fails | reshape(5,8,4).transpose | check raises | — | R6 | frequency-major XAI reshape (M) | PASS |
| test_scripts_smoke_exports_and_csv | synthetic legacy tree (S01, S04; 30 stimulus + 6 other windows each) | all six scripts exit 0 as subprocesses (`--epochs 2 --device cpu`, `--skip-cnn` variants); header states legacy / no-reset / fs=250; CSV leading columns `Subject, Classifier, Accuracy, Recall per Class`, 6 rows; 6 CM figures per subject plus S01 at root; LDA accuracy and smoothed accuracy equal an independent recomputation; joblib and `.pt` keys, classes, 10,005, label_map; `.pt` reload reproduces `train_accuracy` exactly; XAI and comparison PNGs; batch CSV columns; batch LDA == train_models LDA | 1e-4 / exact | plan | — | PASS |

## Mutant evidence

Every (M) test runs the check against its buggy variant (frequency-major flatten, FBCCA fs 256, scaler on all windows, trial-aware smoothing, conv biases, frequency-major LDA reshape, other CV seed, CNN scalers on all windows) and passes, so each check detects its mutant.

## Command

```bash
.venv/bin/python -m pytest tests/ -q
```

## Output summary

Full suite (CPU; run with `-o addopts="" -q` because `pytest.ini` already has `addopts = -q` and a bare `-q` becomes `-qq`, which hides the summary line): `349 passed, 10 warnings in 83.06s (0:01:23)`.
New file alone: `32 passed in 44.81s`.

Bugs found in builder code: none.

## Coverage gaps

- `batch_run_subjects` with a missing subject (preprocessing from raw recordings) is not run: it would read raw data, which is forbidden here.
- No `--device cuda` test (CPU only) and no 140-epoch run.
- Smoke-tree accuracies are not asserted against any target (leaky legacy CV; R-6 is not a target).
- Exact FBCCA scores are not pinned against a closed form; only ranking, bounds and fs sensitivity.
- The new smoke test costs about 40 s (subprocess startups plus CNN epochs).

## Reference consultations (R11)

None; `reference/` was not opened.

## Sources

1. `02_plan.md` "Tests required" (opened in this run).
2. `mas/RULES.md`, `mas/05_PITFALLS.md` PF entries as cited in the plan (opened in this run).

## Questions

ACK 02_plan.md synthetic-tester 2026-10-24
