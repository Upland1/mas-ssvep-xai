# P18 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_connectivity-stats.md, mas/RULES.md (R6, R7), mas/05_PITFALLS.md PF-19/20/25/26, decisions.md P18

NEW `tests/test_p18_independent_known_answer.py` (21 tests, about 18 s). Written without the builder's `tests/test_p18_nbs.py`; expected values come from hand-built cases and a brute-force reference defined in the file (BFS components, explicit nested loops for the edge layout, plain-numpy pseudo-z). Synthetic data only; no generated, ignored or raw files. No source file was changed (mutants were applied to scratch edits and reverted; `git status` shows only the new test file).

## Tests added

| Test (in `tests/test_p18_independent_known_answer.py`) | Simulates | Expected (known answer) | Catches |
|---|---|---|---|
| `test_pseudo_z_known_null_mean_and_std` | null of two values m -/+ s per edge; 5000-draw null | z = 2, -2, 0 exactly (1e-12); z_null = -1/+1; null z-map has mean 0, std 1 | wrong ddof/standardization |
| `test_pseudo_z_zero_or_nonfinite_std_is_zero_not_inf` | constant edge, NaN edge, inf observed | z = 0, all finite | division by zero |
| `test_components_planted_clique_path_and_isolated_edge_sizes_are_edge_counts` | C=10: 4-clique (6 edges), 2-edge path, isolated edge; 60 random graphs vs BFS | sizes {6, 2, 1}, largest 6 (edges, not 4 nodes); labels as planted | node-count sizes, wrong grouping |
| `test_no_supra_threshold_edge_gives_size_zero` | all-zero z | size 0, p = 1 | empty-graph crash |
| `test_upper_triangle_layout_matches_nested_loops_and_roundtrips` (R6) | C=6 labelled matrix | edge vector = nested loops; round trip symmetric, zero diagonal; batch axis; 22 edges raises; edge (0,5)=4, (1,4)=7 | wrong triu order |
| `test_p_value_formula_with_constructed_null_maxima_and_plus_one` | 20 permutations with set maxima (stars/5-clique), exactly six >= 3 | null_max equals the constructed list; p = 7/21; size 11 beats all: p = 1/21, mask = the 11 edges; tie counts: 2/21 | dropped +1, `>` instead of `>=` |
| `test_null_max_uses_each_permutations_own_zmap_from_raw_statistics` | per-edge null scales 0.05 (clique) vs 1 | equals brute-force `ref_nbs`; differs from a global observed scale | null standardized by observed only |
| `test_random_cross_check_against_bruteforce_reference` | 25 random cases, C in {4,6,7,8}, both tails, 4 thresholds | size, null_max, p equal the reference | any of the above |
| `test_tails_and_strict_threshold` | z = -4 cluster; z == 2 and 2.0001 | one-tailed 0, two-tailed 2; z == t not supra | tail, strictness |
| `test_sweep_sizes_non_increasing_and_same_permutations` | 120 permutations, 4 thresholds | sizes non-increasing; null_max non-increasing elementwise | separate permutations per threshold |
| `test_pdc_is_symmetrized_before_nbs_obs_and_null` (PF-25) | lower-triangle-only PDC; antisymmetric null noise | size 3 (triangle); M and M.T identical; antisymmetric null cancels -> size 0; upper-only reads < 3 | PDC not symmetrized (obs or null) |
| `test_type_one_rate_independent_channels` | 400 seeds, 24 trials x 8 independent channels, 199 trial-label permutations | 3/400 = 0.0075 significant | inflated type I |
| `test_power_planted_coupled_subnetwork_statistic_level` | 4-channel coupled clique (6 edges), 10 seeds | significant in 10/10; planted edges within the mask, mask <= 12 | no power |
| `test_cohort_planted_subnetwork_found_with_planted_edges` | real cohort script, synthetic built folder: tone on POz/PO4/O1/Oz only (planted 6 edges), PLV, 99 permutations | NBS significant in 5/5 conditions (sizes 11, 6, 7, 11, 8; p 0.01-0.02); planted edges within every significant mask; `nbs_n_sig_edges` = mask size | missed subnetwork |
| `test_cohort_possible_edges_from_kept_channels_7_vs_8` (PF-26) | S01 8 channels, S02 PO8 dropped | possible edges 28 / 21; PDC FDR total 56 / 42 (directed); undirected FDR total = possible | fixed channel count, PDC denominator |
| `test_cohort_criteria_are_separate_columns` (PF-20) | the same run | `n_edges_sig_fdr`, `fdr_backed`, `nbs_p`, `nbs_significant`, `p_one_tailed` separate columns, consistent with their definitions; console (A)/(B) lines differ by `--stats` | criteria merged |
| `test_cohort_sweep_table_on_same_permutations` | the same run | thresholds 1.5/2/2.5/3; max_size non-increasing | |
| `test_stats_fdr_keeps_fdr_columns_global_p_and_edge_arrays` | `--stats nbs` vs `--stats fdr`, 49 permutations | summary CSV frames and every npz array identical; FDR columns, global p, `fdr_*` and `p_*` arrays equal a direct `extract_connectivity_by_condition` call | port altered FDR |
| `test_pairwise_two_tailed_nbs_finds_planted_difference_of_either_sign` | 4 coupled channels in a (then in b), 199 permutations | NBS p < 0.05, 6 <= edges <= 12, size >= 6, 28 edges, both signs | one-tailed pairwise |
| `test_pairwise_null_difference_rate` | 40 null cells | 1/40 significant | |
| `test_pairwise_summary_only_reproduces_summary_without_recomputation` | full run then `--summary-only` with `run` and `load_subject_groups` patched to fail | every summary line (group lines, NBS line, split-half) appears verbatim in the full run output | recomputation, drift |

## Rates and bounds

| Rate | Observed | Bound used | Why |
|---|---|---|---|
| NBS type I (400 seeds, alpha 0.05) | 3/400 = 0.75 % | 1 <= X <= 37 | X ~ Bin(400, <= 0.05): mean <= 20, sd <= 4.36; 37 = mean + 4 sd. The permutation test is valid and conservative (discrete p), so the rate is at most 5 % and here well below; the lower bound only catches a degenerate test. |
| Pairwise null (40 cells) | 1/40 | X <= 7 | Bin(40, <= 0.05): mean <= 2, sd <= 1.38; P(X >= 8) < 1e-3. |
| Power, statistic level | 10/10 | >= 9 | planted effect, fixed seeds. |
| Power, cohort script (PLV) | 5/5 conditions | >= 3 | fixed seeds. |

All seeds are fixed, so the suite is deterministic; the bounds document what they mean.

## Mutation check (applied to `src/` and `scripts/`, then restored from copies; `git status` clean afterwards)

| Mutant | Result (this file) | Killed by |
|---|---|---|
| M1 drop the +1 in both p formulas | 4 failed | p-formula, no-supra (p = 1), heterogeneous null, random cross-check |
| M2 null standardized with observed values only (global obs mean/std) | 4 failed | pseudo-z (2), heterogeneous null, random cross-check |
| M3 components on the full graph (all edges link; size counts supra edges of the full-graph component) | 7 failed | components, layout, p-formula, null, cross-check, power, pairwise |
| M4 PDC not symmetrized (`directed` ignored in `nbs_for_result`) | 1 failed | `test_pdc_is_symmetrized_before_nbs_obs_and_null` |
| M5 one-tailed in the pairwise (`two_tailed=False`) | 1 failed | pairwise either-sign test |
| M6 fixed 8 channels (`possible_edges_nbs = 28`) | 1 failed | `test_cohort_possible_edges_from_kept_channels_7_vs_8` |

Not covered: the builder's `test_p18_nbs.py` was not run against the mutants (only this file). Window-level nulls (PF-19) are not a mode of the NBS functions; the cohort passes the trial-level null, which `test_stats_fdr_keeps_...` ties to `extract_connectivity_by_condition`.

## Command

```bash
.venv/bin/python -m pytest tests/test_p18_independent_known_answer.py -q -o addopts=""
.venv/bin/python -m pytest tests -q -o addopts=""
```

Suite line (run once, at the end, on the final tree): `1205 passed, 22 warnings in 749.59s (0:12:29)` (log in the session scratchpad; 1184 builder suite + 21 new).

Status: READY
