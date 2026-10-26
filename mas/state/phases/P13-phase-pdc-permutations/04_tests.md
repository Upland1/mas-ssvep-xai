# P13 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 00_assignment.md, 02_plan.md, 03_changes_connectivity-stats.md, mas/RULES.md, mas/05_PITFALLS.md (PF-03, PF-17 to PF-20), decisions.md P13 row

## Tests added

NEW `tests/test_p13_known_answer.py` (37 tests, 3.4 s). The builder's `tests/test_p13_connectivity.py` is untouched. Systems are built in the test file (the builder's demo systems are not reused); expected values are hand-derived.

| Test (in `tests/test_p13_known_answer.py`) | Simulates | Expected | Tolerance | Source of expected | Catches |
|---|---|---|---|---|---|
| `test_mvar_strided_recovers_hand_picked_var2_contiguous_is_far` | hand-picked stable VAR(2), 4 ch, 100 windows | strided error < 0.10, entries A1[1,0] = 0.5, A1[2,1] = -0.4, reverse entry 0; contiguous > 0.5 and > 5x strided | stated | analytic (coefficients chosen) | PF-17 |
| `test_mvar_row_layout_channel_major_with_known_weights` | y0[t] = 2 x1[t-3] | `weights[1*p + 2, 0] = 2` | 0.02 | analytic | PF-17, R6 |
| `test_hand_picked_var2_is_stable` | companion matrix | spectral radius < 0.9 | | analytic | premise |
| `test_pdc_hand_computed_orientation_and_column_normalisation` | 0 drives 2, coefficients known | `[2,0] = 0.6 / sqrt(abs(1-0.3z)^2 + 0.36)`, `[0,2] = 0`, zero diagonal, unit column norm | 1e-9 | hand formula | transposed PDC, row normalisation |
| `test_pdc_random_coefficients_match_hand_formula_asymmetric` | random 5-ch VAR(3) | equals an independent column-normalised implementation at 3 frequencies; not symmetric | allclose | hand formula | transposed PDC |
| `test_pdc_end_to_end_driver_direction_7_channels_42_edges` | 7-ch AR(1), ch 1 drives ch 5 | `PDC[5,1] > PDC[1,5] + 0.3`, zero diagonal, 42 positive off-diagonals, edge masks 42 / 21 | | analytic | orientation, edge count |
| `test_csd_plv_is_immune_to_edge_corruption_and_hilbert_is_not` | coupled pair, first/last 15 samples replaced by noise | CSD PLV change <= 0.03; own filtfilt+Hilbert PLV drops by more than twice that | stated | PF-18 | Hilbert in reported path |
| `test_plv_wpli_zero_lag_and_quadrature` | zero lag, lag pi/2, random lag | zero lag: PLV > 0.95, wPLI < 0.2; pi/2: both > 0.95; random: PLV < 0.2 | stated | analytic | |
| `test_wpli_and_plv_hand_computed_from_csd` | crafted CSD, Im = [1,1,-1,2] | wPLI = 0.6; PLV scale-invariant; angles 0 and pi/2 give sqrt(2)/2 | 1e-9 | hand arithmetic | |
| `test_wpli_zero_denominator_gives_zero_not_nan` | real CSD; constant Im; cancelling Im | 0 (not NaN); 1; 0; NaN diagonal | exact | task 1 | 0/0 |
| `test_trial_split_mixed_lengths_exact_and_whole_trials[n_first]` (8 cases x 40 seeds) | 6 trials of 5 + 7 of 2 windows | exact group sizes, partition, at most one shared trial, other trials whole, more than 5 distinct splits | exact | PF-19 | split trial count, window shuffle |
| `test_trial_split_can_hit_the_count_without_splitting_when_possible` | 4 x 5 windows, n_first 10 | no shared trial | exact | PF-19 | |
| `test_trial_ids_route_to_trial_split_with_observed_stim_size` | ids given | only the trial splitter is called, 6 times, first-group size = n_stim | exact | PF-19 | window split with ids, unmatched sizes |
| `test_no_ids_routes_to_window_split` | no ids | window splitter only; label `window` | exact | R7 | |
| `test_colliding_stim_and_baseline_trial_labels_stay_distinct` | overlapping id labels | 19 distinct pooled trials | exact | | label collision |
| `test_pseudo_count_minimum_p_and_tails[19, 99]` | stim far above base; and reversed | one- and two-tailed p = 1/(n+1); reversed: one-tailed 1.0, two-tailed 1/(n+1) | exact | R7 | no pseudo-count, tail mix-up |
| `test_p_values_on_exchangeable_null_are_in_range_and_two_tailed_covers_one` | 15 null draws | p in [1/(n+1), 1]; p = (1 + #null >= obs)/(n+1) recomputed from the null | exact | definition | |
| `test_bh_hand_computed` (5), `test_bh_ties_shape_and_monotonicity` | hand p vectors incl. step-up case and ties; 100 random tied vectors | counts 2, 4, 4, 0, 1; equals an independent loop; rejected set is a prefix; larger alpha never rejects fewer; ties share a decision | exact | BH 1995 (step-up), hand | |
| `test_global_p_without_fdr_edge_and_fdr_edge_without_global_p` | one moving edge of 3; two opposing edges | (B) true with (A) = 0 edges; (A) >= 1 edge with global p >= 0.05 | exact | PF-20 | merged criterion |
| `test_summary_columns_keep_the_two_criteria_separate_and_console_lists_both` | 4 subjects | (A) ['S01','S03'], (B) ['S02','S03'] | exact | PF-20 | merged star |
| `test_trial_ids_are_built_pre_gate_then_masked_like_windows` | 101 block of 2 trials, one window rejected | ids passed on equal pre-gate ids masked; differ from ids rebuilt after the gate | exact | PF-03 | ids after gate |
| `test_determinism_n_jobs_and_seed_sensitivity` | coherence, PDC, direct PLV at n_jobs 1 and 2 | null, edge p, FDR mask, p identical; different seed gives a different null | exact | settled point 7 | |
| `test_null_calibration_loose_across_methods` | 12 null datasets, trial-level PLV | at most 4 of 12 below 0.05, at most 2 FDR edges | loose | R7 | |
| `test_cohort_summary_and_npz_schema` | synthetic legacy tree, plv + pdc, 7 permutations | §6 columns in order (hard-coded here), 10 rows, frequencies, edges 21 / 42, `fdr_backed` and `significant_uncorrected` consistent with their sources, console has (A) and (B), npz keys and shapes | exact | §6 | |

## Mutation checks

Each mutant was applied to `src/` (or the cohort script), `tests/test_p13_known_answer.py` was run, and the file restored with `git checkout`. The final `git status` shows only the new test file.

| Mutant | Result |
|---|---|
| M1 contiguous MVAR slicing in `mvar_coefficients` (PF-17) | KILLED (`test_mvar_strided_recovers_hand_picked_var2_contiguous_is_far`) |
| M2a transposed PDC output | KILLED (`test_pdc_hand_computed_orientation_and_column_normalisation`) |
| M2b PDC normalised per row instead of per column | KILLED (same test) |
| M3 filtfilt + Hilbert PLV as `compute_condition_plv` (PF-18) | KILLED (`test_csd_plv_is_immune_to_edge_corruption_and_hilbert_is_not`) |
| M4a trial ids dropped inside `compute_permutation_test` (window split, label window) | KILLED (`test_trial_ids_route_to_trial_split_with_observed_stim_size`) |
| M4b window split used while the label stays "trial" | KILLED (same test) |
| M5 group size `len(pool)//2` instead of the observed stimulus size | KILLED (same test) |
| M6 no +1 pseudo-count | KILLED (`test_pseudo_count_minimum_p_and_tails[19]`) |
| M7 merged star (criterion B includes FDR-edge subjects) | KILLED (`test_summary_columns_keep_the_two_criteria_separate_and_console_lists_both`) |
| M8 trial splitter degraded to a window shuffle | KILLED (`test_trial_split_mixed_lengths_exact_and_whole_trials[4]`) |
| M9 trial ids rebuilt after the gate (PF-03) | KILLED (`test_trial_ids_are_built_pre_gate_then_masked_like_windows`) |
| M10 wPLI `num / den` without the zero guard | KILLED (`test_wpli_zero_denominator_gives_zero_not_nan`) |

A first M8 attempt (`break` replaced by `continue` after the partial fill) survived because it is an equivalent mutant: once the count is met, no later trial can add windows. It was replaced by the window-shuffle variant above.

## Findings

No builder bug found. Notes for the reviewer, none blocking:
1. A trial that straddles the stimulus/baseline pools is impossible by construction (ids are offset), so "at most one split trial" is tested on the pooled ids with distinct labels.
2. The builder's `significant_uncorrected` (global p < alpha) and `fdr_backed` (>= 1 FDR edge) are two columns of the same summary; PF-20 is satisfied by those columns plus the separate console lines.

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```

Output (full suite, CPU, synthetic data only): `787 passed, 21 warnings in 368.21s (0:06:08)` (750 before, plus 37). New file alone: `37 passed in 3.43s`.

## Questions

None.

## Round 1

Status: READY. Scope: audit fix in b8e5ccc, 643f0f9, 628759d. Four tests appended to `tests/test_p13_known_answer.py` (41 tests in the file now, `41 passed in 3.38s`).

| Test | Simulates | Expected | Catches |
|---|---|---|---|
| `test_compare_writes_distinct_files_in_both_orders_with_hand_flips` | three hand-made summaries (trial100, final, window200), 3 cells each | (trial100, "") writes `connectivity_cohort_flips.csv` with S01 only, printed "3 cells compared, 1 flip"; (window200, "") writes `..._flips_window200_vs_final.csv` with 3 hand-predicted flips and does not overwrite the required file; ("", trial100) writes `..._flips_final_vs_trial100.csv` with S01 and p values swapped; ("", window200) writes its own file | R1 |
| `test_compare_raises_on_missing_row_in_either_direction` | summary lacking one row | `ValueError` from `compare_runs` in both argument orders and from `main` | R2 |
| `test_lower_and_upper_tail_p_against_hand_counts_with_ties` | controlled 10-value null with ties (-0.5 ... 1.5), observed 0.3, 2.0, -2.0 | p_one 6/11, p_lower 9/11, p_two 7/11 (hand counts); 1 - p_one is not the lower tail; extremes 1/11 and 1.0 | R3 |
| `test_alpha_diagnostic_carries_p_lower_tailed` | synthetic tree, plv, 7 permutations | `p_lower_tailed` column in the alpha CSV, within [1/8, 1] | missing column |

Mutants (applied then `git checkout`; `git status` shows only the test file modified):

| Mutant | Result |
|---|---|
| R1 every pair writes the same file (`flips_path` always the required name) | KILLED |
| R2 inner merge with the row-set check disabled | KILLED |
| R3 lower tail computed as `1 - p_one` | KILLED |

Full suite: `796 passed, 21 warnings in 361.15s (0:06:01)`.
