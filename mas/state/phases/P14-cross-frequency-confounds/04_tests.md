# P14 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 00_assignment.md, 02_plan.md, 03_changes_connectivity-stats.md (incl. "Round 1 audit fix"), 07_review.md, mas/RULES.md, mas/05_PITFALLS.md (PF-19, PF-21 to PF-27), mas/02_REQUIREMENTS.md section 6

## Tests added

NEW `tests/test_p14_known_answer.py`: 44 tests (40 in the first pass, 4 in Round 1), synthetic data only, about 6 s. The builder's `tests/test_p14_connectivity_comparison.py` is not edited. All are in the new file; "Catches" names the bug or plausible variant the test fails on (mutant numbers refer to the table below).

| # | Test | Simulates | Expected (source) | Catches | Result |
|---|---|---|---|---|---|
| 1 | `test_embedding_unordered_kept_with_dropped_channel_and_po7_nan` | kept out of montage order, PO7/PO8/Oz absent | entries by name, NaN rows/cols, nothing else filled (analytic) | PF-26 positional embedding (M6) | PASS |
| 2 | `test_embedding_full_montage_identity_and_shuffled_full_montage` | full and shuffled 8 channels | identity / permuted by name (analytic) | PF-26 (M6) | PASS |
| 3 | `test_pdc_node_strength_hand_values_through_script_loader` | 4-channel directed matrix, diagonal 9, npz with decoy keys | node strength 10/3, 4, 9/2, 23/6; global 23.5/6 (hand `(M+M^T)/2`) | PF-25 (M5), PF-24 (M4), M6 | PASS |
| 4 | `test_symmetric_methods_not_symmetrized_twice_and_raw_keys_ignored` | symmetric edge file with raw `stim_/base_/p_` decoys | `diff_` values only (analytic) | PF-24 (M4), M6 | PASS |
| 5 | `test_script_reads_only_delta_fdr_and_channel_keys` | spy on `np.load` | only `diff_`, `fdr_`, `channels_kept` touched | PF-24 (M4) | PASS |
| 6 | `test_fisher_mean_known_values_and_group_summary` | r = 0.2, 0.9, -0.5; group table | `tanh(mean(atanh r))`, not arithmetic mean, 1e-12 (hand) | arithmetic mean of r | PASS |
| 7 | `test_qap_relabelled_copy_gives_r_one_and_minimum_p` | graph vs itself and relabelled on both sides | r = 1, p = 1/(n+1) for n = 19, 499 (analytic) | rows-only permutation (M7), missing +1 | PASS |
| 8 | `test_qap_pvalue_is_a_multiple_of_one_over_n_plus_one_and_never_zero` | 10 independent pairs | p >= 1/(n+1), integer count | missing +1 pseudo-count | PASS |
| 9 | `test_qap_independent_matrices_give_uniform_p` | 300 independent pairs | P(p <= q) = q, tol 0.08 (analytic) | biased null | PASS |
| 10 | `test_qap_exhaustive_with_missing_channels_and_asymmetric_structure` | 5 channels inside the 8 x 8, all 5! relabellings | p = exhaustive fraction, tol 0.025 (enumeration) | rows-only (M7), PF-26 | PASS |
| 11 | `test_qap_exhaustive_n6_distinguishes_rows_only_permutation` | structured 6-node case, 6! | p = exhaustive, tol 0.02 | inconsistent row/column permutation | PASS |
| 12 | `test_qap_applicability_rules` | 4 shared channels with 6 / 5 finite pairs; 3 shared; 5 vs 3 shared | applicable / NaN / NaN / NaN (task 1 rule) | rule dropped | PASS |
| 13 | `test_qap_script_marks_skipped_pairs_as_nan` | script, one 3-channel subject | S02 r and p NaN | skip rule in script | PASS |
| 14 | `test_responders_threshold_edge_cases` | CSV with 80.0, 79.99, NaN, `Mean` row | 80.0 in, NaN out, Mean ignored (PF-21) | threshold off by one | PASS |
| 15 | `test_responders_independent_of_connectivity` | S02 has the largest deltas, low accuracy; connectivity then flipped | groups S01+S03 / S02 in both runs; group means = hand means (PF-21) | responders from connectivity (M1) | PASS |
| 16 | `test_responders_override_flag_wins` | `--responders S02` | group sizes 1 / 1 | override ignored | PASS |
| 17 | `test_split_half_negative_r_is_not_spearman_browned` | stub with exactly anti-correlated halves (r = -1) | `corrected` False, reliability = r (PF-22) | SB on r <= 0 (M2) | PASS |
| 18 | `test_split_half_positive_r_corrected_by_formula` | 0 < r < 1 | `2r/(1+r)`, 1e-12 | wrong SB formula | PASS |
| 19 | `test_split_half_halves_are_trial_disjoint` | tagged trials, spy on estimator | halves share no trial, sizes k//2 | trial leakage between halves | PASS |
| 20 | `test_ceiling_and_disattenuation_ten_percent_rule` | ceilings 0.72, exactly 0.1, NaN | 0.5, NaN at <= 0.1, not clipped | 0.1 rule | PASS |
| 21 | `test_pairwise_tables_ceiling_disattenuation_and_bh` | 10 fake pair results | ceilings, NaN handling, BH selects 2 of 10 | BH/ceiling wiring | PASS |
| 22 | `test_fisher_combined_hand_chi_square` | k = 1, 2, 4 | closed-form chi-square sf (df 2, 4, 8), 1e-12 (hand) | wrong df | PASS |
| 23 | `test_combined_table_uses_group_members_only` | 3 subjects, 2 groups, one NaN | hand Fisher p per group, NaN dropped | wrong group | PASS |
| 24 | `test_pairwise_matches_independent_reference_exactly` | independent loop with the same splitter and seeds | p_mag, p_pat, t_mag, d_pat equal to 1e-12 | statistics on separate draws, window-level (M8) | PASS |
| 25 | `test_pairwise_baseline_scored_in_own_band` | identical processes, different bands, band offset | offset cancels, p > 0.05 | baseline scored in the wrong band | PASS |
| 26 | `test_pairwise_splitter_called_once_per_draw_with_observed_sizes_and_shared_nested` | spy on the splitter | one call per draw, sizes (25, 45), 10 draws = head of 20 (PF-19) | window-level (M8), size mismatch, non-nested nulls | PASS |
| 27 | `test_pairwise_trial_level_null_is_not_anticonservative_with_heterogeneous_trials` | 70 reps, strong trial-to-trial coupling | P(p<.05) < 0.18, mean p in (.35, .65) (R7) | window-level (M8) | PASS |
| 28 | `test_pairwise_identical_processes_uniform_p_both_statistics` | 80 reps | uniform quantiles, tol 0.14 | biased null | PASS |
| 29 | `test_pairwise_planted_magnitude_difference_small_pmag_not_ppat` | coupling x0.3 | p_mag <= .01, t > .05 | statistic mix-up | PASS |
| 30 | `test_pairwise_planted_pattern_difference_equal_magnitude_small_ppat_only` | mirrored channel pattern | p_pat <= .01, p_mag > .05 | statistic mix-up | PASS |
| 31 | `test_target_gain_and_alpha_drop_planted_for_10_91_hz` | bin-centred tones, +6.02 dB target, -3 dB alpha | SNR 6.02, alpha -3.0, tol 0.2 dB (planted) | PF-23 (M3) | PASS |
| 32 | `test_target_tone_inside_alpha_does_not_change_alpha_measure_for_both_in_alpha_targets` | target-only gain at 10.91 and 8.57 Hz | alpha change about 0 (PF-23) | PF-23 (M3) | PASS |
| 33 | `test_alpha_mask_excludes_f0_band_and_is_shared_by_stimulus_and_baseline` | mask on the fs-250 axis | f0 +- 1.5 Hz excluded | PF-23 (M3) | PASS |
| 34 | `test_only_listed_channels_enter_the_power_metrics` | huge tone on a non-occipital channel | only listed channels count | channel misindexing | PASS |
| 35 | `test_subject_rows_use_o1_oz_o2_by_name_with_a_dropped_channel` | Oz dropped, order PO3 O1 POz O2 | `channels_used` O1;O2, SNR 6 dB | index misalignment | PASS |
| 36 | `test_ols_r2_hand_values` | hand slope, R^2 = corr^2, intercept 100 | exact, 1e-12 | no intercept | PASS |
| 37 | `test_centre_within_subject_hand_values_and_simpson_case` | Simpson data | all-cell rho > 0.5, centred rho = -1, centred R^2 = 1 | no centring | PASS |
| 38 | `test_no_misspelled_duplicate_anywhere_in_repo` | filesystem and `git ls-files` | no `cofound` name (PF-27) | PF-27 | PASS |
| 39 | `test_confound_script_end_to_end_schema_and_no_cofound_file` | tiny tree, `main` | section 6 columns, no `cofound` output | schema drift, PF-27 | PASS |
| 40 | `test_comparison_script_section6_schemas_for_all_four_methods` | 2 subjects x 4 methods | exact columns and row counts | schema drift | PASS |
| 41 | `test_common_band_effect_gives_nonsmall_pmag_and_centred_p_because_null_is_off_centre` | R1: every a and b trial couples in band A only (own generator, 8 seeds) | t > 0.2; null mean within 0.1 of t_mag and > 0.15; mean p_mag > 0.3, mean p_mag_centred > 0.3; at most 1 of 8 p_mag < .05 (review F2) | reading p_mag as a D_a = D_b test | PASS |
| 42 | `test_cross_band_response_gives_pmag_one_and_small_centred_p` | R1: D_a = D_b = 0, b-trials couple in band A (6 seeds) | \|t_mag\| < .06, null mean > .1, p_mag > .9, p_mag_centred < .05 (review F2) | uncentred p_mag_centred (M9) | PASS |
| 43 | `test_centred_p_matches_review_definition_from_the_splitter` | independent recomputation with the same splitter and seeds | null mean, SD, p_mag_centred = `(1 + #{\|t_null - mean\| >= \|t_obs - mean\|})/(n+1)`, p_mag, 1e-12 | wrong centring (M9) | PASS |
| 44 | `test_pairwise_null_diagnostic_csv_columns_and_section6_csv_unchanged` | script run, 9 permutations, suffix `t` | `plv_pairwise_null_t.csv` columns `subject, method, freq_a, freq_b, t_null_mean, t_null_sd, p_mag_centred, d_null_mean, d_null_sd`, 10 rows; section 6 pairwise columns unchanged; unsuffixed file absent | schema drift | PASS |

Generator for 41-43 (own, not the builder's): windows have two time halves; band A (low edge >= 20 Hz) is scored on the first half and band B on the second; channels share a source in a chosen half. This makes "responds in band A" a controlled property of each trial.

## Mutation checks

Each mutant was applied by a scripted exact-string replace (scratchpad `mut.py`), `tests/test_p14_known_answer.py` was run, and the file restored with `git checkout <file>`; `git status` showed no change in `src/` or `scripts/` afterwards.

| Mutant | File | Killed by |
|---|---|---|
| M1 responders from connectivity (median of `\|diff_101\|`) | `scripts/.../compare_connectivity_frequencies.py` | #15 (1 failed) |
| M2 Spearman-Brown applied to r <= 0 | `src/.../comparison.py` | #17 (1 failed) |
| M3 no f0 exclusion from the alpha band | `scripts/.../check_power_alpha_confound.py` | #31, #32, #33 (3 failed) |
| M4 raw `stim_` matrices instead of `diff_` | `compare_connectivity_frequencies.py` | #3, #4, #5, #13 (4 failed) |
| M5 PDC not symmetrized | `comparison.py` | #3 (1 failed) |
| M6 channel misalignment (positional embedding) | `comparison.py` | #1, #2, #3, #4 (4 failed) |
| M7 QAP permuting rows only | `comparison.py` | #7, #10 (2 failed) |
| M8 window-level instead of trial-level permutation | `comparison.py` | #24, #26, #27 (3 failed) |
| M9 (Round 1) `p_mag_centred` computed without centring: `np.abs(null_t) >= abs(t_obs)` | `comparison.py` | #42, #43 (2 failed, 42 passed) |

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```

Last line, verbatim: `874 passed, 21 warnings in 408.68s (0:06:48)`.
New file alone: `44 passed in 6.09s`.

## Coverage gaps

- **Off-centre pairwise null.** First pass: no test had an off-centre null (review F1/F2); closed in Round 1 by #41 to #43 with a half-window generator. Gap that remains: the generator uses a zero-lag correlation estimator, not coherence/PLV/wPLI on real band-limited data, so the size of the off-centre effect on real data is not measured here. `p_pat` under cross-band response (review: 22 % rejections with no delta) is not asserted.
- No real data: nothing reads `data/`, `reports/` or any recording. Real-data behaviour (PO7 absent in every subject, gate decisions, S02/S04 approximate trial ids, the Hann leakage at fs 250) is the verifier's and reviewer's.
- The first-pass pairwise uniformity tests are Monte Carlo with fixed seeds and loose tolerances (0.08 to 0.18); they would not detect a small bias.
- The `--compare` flip list, the figures (PNGs) and the `n_jobs` byte-identity are covered only by the builder's tests.
- The Fisher-combined p across subjects is tested against closed forms, not for validity under dependence between pairs.
- Test #24 and #43 reuse the plan's seed rule (`SeedSequence(seed).generate_state(n)`) and `_trial_permutation_split`, so they check statistics, sizes and shared draws, not the seed rule.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

1. `mas/state/phases/P14-cross-frequency-confounds/02_plan.md` "Tests required" and "Settled points" (opened in this run).
2. `03_changes_connectivity-stats.md` including "Round 1 audit fix"; `07_review.md` pre-run audit Round 1 (F1, F2) (opened in this run).
3. `mas/05_PITFALLS.md` PF-19, PF-21 to PF-27; `mas/02_REQUIREMENTS.md` section 6 (opened in this run).

## Round 1

Status: READY

- **F1.** The first `04_tests.md` commit (e4c9817) held the empty template because the write was blocked together with the commit command. This file replaces it; the commit is verified with `git show HEAD:<path>` before reporting.
- **F2 tests.** #41 (common band effect gives non-small p_mag and p_mag_centred, null mean within 0.1 of t_mag), #42 (D_a = D_b = 0 with b-trials responding in band A gives p_mag > 0.9 and p_mag_centred < 0.05), #43 (p_mag_centred equals the review's definition recomputed from the splitter), #44 (diagnostic CSV `<m>_pairwise_null*.csv` columns, 10 rows, section 6 pairwise CSV unchanged).
- **Mutant M9** (no centring) fails #42 and #43; file restored with `git checkout`.
- **Full suite** after the builder's fix (d86364a, b2a036c, 9aeb5db) and the new tests: `874 passed, 21 warnings in 408.68s (0:06:48)`.
- No builder bug found.

## Questions

None.
