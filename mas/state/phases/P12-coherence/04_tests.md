# P12 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_connectivity-stats.md, mas/RULES.md, mas/05_PITFALLS.md (PF-04, PF-15, PF-16)

## Tests added

NEW `tests/test_p12_known_answer.py` (15 test cases, synthetic data only, builder tests untouched).

| Test id (`tests/test_p12_known_answer.py::`) | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_pf15_independent_noise_bias_through_reported_path` | 60 x 7 x 256 independent noise | per-window averaged in [0.30, 0.37]; concatenated <= 0.03 | as stated | R-11, analytic | PF-15 | PASS |
| `test_pf15_summary_rows_reported_value_is_concatenated` | noise, `summary_rows` | `mean_raw`, `mean_matched_baseline` <= 0.05; diagnostic column 0.28-0.40 | as stated | PF-15 | PF-15 (reported path averaged) | PASS |
| `test_pf15_coupled_high` | shared source + small noise | both estimators >= 0.95 | | analytic | | PASS |
| `test_pf16_identical_narrowband_coupling_matched_zero_broadband_not` | identical 20 Hz coupling in 102 and 201 | matched diff <= 0.05 in abs; broadband diff > 0.2 (also via `summary_rows`) | as stated | PF-16 | PF-16 | PASS |
| `test_r6_pair_layout_argmax_and_symmetry[3 pairs]` | coupling only on (0,6), (2,3), (1,4) | that entry is the argmax, > 0.9; all others < 0.3; symmetric; NaN diagonal | exact | R6 | transposed/one-sided index | PASS |
| `test_r6_dropped_channel_names_follow` | channel Oz noisy and gated out; POz-O2 coupled | matrix 6x6; argmax pair maps to names {POz, O2} | exact | R6, PF-06 | name/index shift | PASS |
| `test_band_bins_fs250_hand_mean` | fs 250, f_c 24, nperseg 256 | bins 24, 25 (23.4375, 24.4141 Hz); band average equals hand mean | exact | task 1 | off-by-one bins | PASS |
| `test_band_bins_fs256_differ_pf04_guard` | same band at fs 256 | bins 23, 24, 25; frequency axes differ between fs 250 and 256 | exact | PF-04 | fs mislabelling | PASS |
| `test_same_201_windows_in_every_band` | 201 windows non-contiguous, with 202 in between | idx == all 201 positions; one spectral estimate; every band equals a band average of it | exact | PF-16 | per-band re-selection | PASS |
| `test_condition_filter_excludes_202` | 202 windows with coherence 1 | keys {101, 201}; coherence < 0.1; idx excludes 202 | | plan | 202 included | PASS |
| `test_gate_single_call_explicit_thresholds` | spy on `apply_artifact_quality_pipeline` | exactly one call, over labels 101-105 + 201 (no 202), the five thresholds passed explicitly | exact | R5, settled point 1 | per-condition/implicit gates | PASS |
| `test_gate_union_decision_shared_channels` | channel noisy only in baseline (60 % of the union) | dropped for the stimulus windows too | exact | settled point 1 | per-condition gating | PASS |
| `test_difference_colour_limits_symmetric` | asymmetric data range (-0.10..0.50) | `symmetric_limit` = max abs; colourbar limits (-v, v) | exact | task 3 | asymmetric limits | PASS |

## Mutation checks (src restored with `git checkout` after each; `git status` clean for src)

Baseline: 15 passed. Mutants of `src/features/connectivity/connectivity_extraction.py`:

| Mutant | Failing tests of the new file |
|---|---|
| M1 `compute_condition_coherence` returns the per-window averaged coherence (PF-15) | 6 failed: pf15_independent_noise, pf15_summary_rows, r6_pair_layout x3, condition_filter_excludes_202 |
| M2 matched baseline uses the broadband (5-35 Hz) band (PF-16) | 2 failed: pf16_identical_narrowband, same_201_windows |
| M3 only `out[i, j]` filled (no mirror) | 4 failed: r6_pair_layout x3, r6_dropped_channel |
| M3b mirror transposed/reversed (`out[j, i] = c[::-1]`) | 3 failed: r6_pair_layout x3 |
| M4 baseline windows re-selected per band (strided subsets) | 3 failed: pf15_summary_rows, same_201_windows, condition_filter_excludes_202 |

## Builder bugs found

None. Status READY.

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```
