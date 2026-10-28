# P18 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Branch: phase/P18-nbs (from main @ 0038eec)
Reads: 00_assignment.md, 02_plan.md, mas/02_REQUIREMENTS.md §6, mas/05_PITFALLS.md PF-19/20/25/26, decisions.md P13/P14/P16

## Files

| Status | Path | What |
|---|---|---|
| NEW | `src/stats/nbs.py` | `edge_pseudo_z`, `edge_components` / `max_component_size` (`scipy.sparse.csgraph.connected_components`), `nbs_test` / `nbs_from_z`, `nbs_sweep`, layout helpers `matrix_to_edges` (PDC symmetrized `(M+Mᵀ)/2`, also on the nulls), `edges_to_matrix`, `n_channels_from_edges` |
| MODIFIED | `src/features/connectivity/permutation.py` | `compute_permutation_test` additionally returns `null_matrices (n, C, C)`; no existing value changed |
| MODIFIED | `src/features/connectivity/comparison.py` | `pairwise_permutation_test` additionally returns `diff_edges`, `null_edges`; no existing value changed |
| MODIFIED | `scripts/connectivity/analysis/analyze_connectivity_cohort.py` | `--stats {nbs,fdr}` (default nbs), `--nbs-thresholds` (default 1.5 2 2.5 3), `--nbs-primary` (2.0); §6 NBS columns appended after the 15 pre-P18 columns; `nbs_<c>` symmetric boolean `(C, C)` masks in the edge npz; `connectivity_graph_size[_s].csv`, `connectivity_nbs_sweep[_s].csv` and both tables on the console; `compare_runs` adds `flip_NBS` when both summaries carry `nbs_p` |
| MODIFIED | `scripts/connectivity/comparison/test_connectivity_frequency_differences.py` | two-tailed NBS at \|z\| > 2 on the pairwise null (`NBS_Z`), §6 pairwise columns `nbs_max_size, nbs_p, n_edges_nbs, fs` appended, per-group summary lines, `--summary-only`, `compare_runs` adds `flip_nbs` |
| NEW | `tests/test_p18_nbs.py` | 17 known-answer tests (below) |
| MODIFIED | `tests/test_p13_known_answer.py`, `tests/test_p14_known_answer.py`, `tests/test_p14_connectivity_comparison.py` | pinned schemas extended with the appended P18 columns / `nbs_<c>` npz keys (pre-P18 columns and values are still asserted first) |

Commits on the branch: `2df7341 chore: P18 phase files, decisions and status`; `529e5f8 feat: Network-Based Statistic in cohort and pairwise connectivity scripts`; this file in a final `docs:` commit.

## Design (as built)

- Edges are upper-triangle vectors; C follows from E = C(C−1)/2, so possible edges come from the kept channels (PF-26; 21 at 7 channels, 28 at 8).
- Pseudo-z: `(obs − mean_null)/std_null` per edge (ddof 0); std 0 or non-finite gives z 0. Null z-maps use the same mean/std. Two-tailed takes absolute values.
- Component size = number of edges; supra-threshold means strictly `z > t`. Null = largest component of each permutation's own z-map. `p = (1 + #{null_max ≥ size})/(n+1)` for each component; the reported `nbs_p` is that of the largest; the mask = edges of components with p < alpha.
- Cohort: one-tailed z > t (matches the one-tailed edge p). PDC symmetrized with its null before NBS (PF-25); its FDR still counts the 42 directed edges, so `total_edges` (FDR) and `possible_edges_nbs` differ for PDC. The graph-size table gives both denominators (`fdr_pct_of_total` = FDR count as % of the method's own edge count, P16 C-4).
- Column names for the sweep: `nbs_size_z<t>`, `nbs_p_z<t>` with `<t>` formatted by `:g` (`1.5, 2, 2.5, 3`). `nbs_size_fraction` is a fraction (0–1); the table has the percentage. `SUMMARY_COLUMNS` in the script is the default-sweep column list.
- `--stats` only changes the console criterion (A): `fdr` prints the unchanged pre-P18 text (`(A) >=1 FDR edge … (B) global p`), `nbs` prints `(A) NBS largest component p < α …` and `(B) global p`. Both criteria and the global p are always saved (PF-20). The graph-size and sweep tables are printed in both modes.
- Settled point 6 (FDR, global p, edge arrays unchanged): proved in `test_cohort_fdr_global_p_and_edges_equal_the_permutation_function` (summary + npz equal a direct `extract_connectivity_by_condition` call on the same synthetic built folder) and on real data: the S01 smoke output at 200 permutations has all 15 pre-P18 columns of `reports/connectivity_cohort_summary_v2cont.csv` (S01 rows) equal (`True` for every column, max abs diff 0.0 for `obs_diff`, `p_one_tailed`, `frequency_hz`).
- R10: no external NBS source was opened; `src/stats/nbs.py` states this and implements the definition in `02_plan.md` settled point 1 / roadmap P18.1. Nothing is cited.
- R11: reference code not consulted (no consultation).

## Tests (tests/test_p18_nbs.py, 17)

| Test | Known answer |
|---|---|
| pseudo-z exact, zero-std edge | z = 3 and 0; finite; two-tailed absolute; one-tailed keeps sign (1e-12) |
| planted cluster | 5-edge cluster + isolated edge → sizes {1, 5}, largest 5, labels as planted; triangle (3) beats path (2) |
| edge ↔ matrix layout (R6) | `matrix_to_edges` = `triu_indices` order; round trip symmetric, zero diagonal; non-triangular E raises |
| null max / p formula | constructed permutations: null_max ∈ {1, 3}, four with 3 → p = (1+4)/(n+1); size 4 beats all → p = 1/(n+1), mask = the 4 edges |
| strict threshold / tails | one-tailed ignores a large negative effect; z == t is not supra-threshold; two-tailed finds it |
| power | 8-channel planted 4-clique (6 edges, +6 SD) → significant, mask exactly the planted edges, p = 1/201 |
| type-I | 200 fixed seeds of noise vs its null: not significant in ≥ 90 % (nominal 95 %; slack for binomial spread) |
| sweep | sizes non-increasing in threshold; null_max non-increasing elementwise (same permutations) |
| PDC (PF-25) | asymmetric planted matrix → 3.0 on the three symmetrized edges; M and Mᵀ give identical NBS; 4 channels → 6 possible edges, not 12 |
| cohort FDR/global p/edges unchanged | summary + npz equal direct call; NBS columns and `nbs_<c>` equal recomputation |
| cohort columns and tables | 15 pre-P18 columns first, then the NBS list; 7 channels → 21 possible edges, PDC FDR total 42; % columns; sweep rows ×4 |
| `--stats` | different (A) console line, identical saved CSVs; custom `--nbs-thresholds 2 2.5 --nbs-primary 2.5` columns |
| compare flips | `flip_NBS` / `flip_nbs` appear when p crosses 0.05 between two runs |
| pairwise power / null | planted coupled 4-channel difference → NBS p < 0.05, size ≥ 6; 20 null cells: ≤ 3 significant |
| pairwise columns | appended `nbs_max_size, nbs_p, n_edges_nbs, fs`; `NBS_Z == 2.0` |
| `--summary-only` | text equals the full run's summary lines; `run` and `load_subject_groups` patched to fail (no recomputation); missing CSVs raise |

Mutation: not run separately; the p-formula test fixes `(1+k)/(n+1)` exactly, so dropping the +1 or using the observed map for the null maximum fails it. Window-level nulls are not a mode of the NBS functions (they only take the caller's null; the cohort script passes the trial-level one, PF-19).

## Smoke on real data (S01, `data/processed_continuous`, shared quality, 16 cores, `--n-jobs -1`; outputs to a scratch dir, deleted)

| Command | Wall time |
|---|---|
| cohort, 4 methods, 200 permutations | 66 s (coherence 59.8 s, plv 0.5, wpli 0.4, pdc 3.4) |
| cohort, 4 methods, 1000 permutations | 330 s |
| pairwise, coherence plv wpli, 1000 permutations (incl. split-half) | 521 s (pairwise tests 501.3 s) |

Projection for five subjects (linear in subjects; S01 has 7 channels, S02/S05 8): cohort 200 ≈ 5.5 min, cohort 1000 ≈ 27.5 min, pairwise 1000 ≈ 43.4 min: total ≈ 76 min, plus the suite (12.2 min measured below) ≈ 89 min. **Below the 110 min threshold; inside LOCAL_RUN_BUDGET_MIN 120. No human-run request needed on this estimate**; 8-channel subjects add edges (28 vs 21) only to the cheap parts, the coherence permutations dominate.

S01 content (record, R-16, 200 permutations): wPLI 10.91 Hz NBS p 0.040 (largest component 4 edges, 19.0 % of 21); PDC 24 Hz NBS p 0.030 (3 edges), global p 0.010, FDR 0 edges. R7 flips between 200 and 1000 permutations on S01 (`--compare p18_nbs_p200 p18_nbs`): 4 of 20 cells flip on at least one criterion (wPLI 10.91 Hz and PDC 15/8.57 Hz on A-FDR; PDC 24 Hz also on A-NBS, p 0.030 → 0.272 while global p 0.010 → 0.004): inconclusive per R7; the verifier runs the compare on all subjects.

## Exact verifier commands

```bash
P=".venv/bin/python -m"
C="$P scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutation-unit trial --n-jobs -1 --data-root data/processed_continuous --quality shared --stats nbs --nbs-thresholds 1.5 2.0 2.5 3.0 --nbs-primary 2.0"
$C --permutations 200  --out-suffix p18_nbs_p200
$C --permutations 1000 --out-suffix p18_nbs
$P scripts.connectivity.analysis.analyze_connectivity_cohort --compare p18_nbs_p200 p18_nbs
$P scripts.connectivity.comparison.test_connectivity_frequency_differences --methods coherence plv wpli --permutations 1000 --data-root data/processed_continuous --quality shared --benchmark reports/n_subjects_benchmark_v2cont.csv --out-suffix p18_nbs
$P scripts.connectivity.comparison.test_connectivity_frequency_differences --summary-only --methods coherence plv wpli --out-suffix p18_nbs --benchmark reports/n_subjects_benchmark_v2cont.csv
```

Outputs (per `--out-suffix s`, under `reports/`):
- `connectivity_cohort_summary_<s>.csv` (+ `_details.csv`), `connectivity_edges_<s>/<S>_<method>.npz` (with `nbs_<c>`), `connectivity_alpha_diagnostic_<s>.csv`
- graph-size table: `reports/connectivity_graph_size_<s>.csv` (also printed, "Graph sizes: …") for `p18_nbs` and `p18_nbs_p200`
- sweep table: `reports/connectivity_nbs_sweep_<s>.csv` (also printed, "NBS threshold sweep: …")
- R7 flips: `reports/connectivity_cohort_flips_p18_nbs_p200_vs_p18_nbs.csv` (rows flip on FDR-A, global-B or NBS-A)
- pairwise: `reports/connectivity_comparison/<m>_pairwise_tests_p18_nbs.csv` (with the four NBS columns), `<m>_split_half_reliability_p18_nbs.csv`, `_pairwise_null_`, `_pairwise_combined_`
- settled point 6 check: the FDR columns of `connectivity_cohort_summary_p18_nbs_p200.csv` against `reports/connectivity_cohort_summary_v2cont.csv` (same data, same 200 permutations; the 15 pre-P18 columns must be identical; S01 already verified above).
- `--summary-only` needs `--methods` equal to the run's (default is all three) and the benchmark CSV (or `--responders`).

## Suite

`.venv/bin/python -m pytest tests -q -o addopts=""` (once, at the end): `1184 passed, 22 warnings in 730.88s (0:12:10)` (log `/tmp/p18_suite.txt`; the new file adds ≈ 1 min). The suite ran at ≈ 12.2 min, so the projected total is ≈ 76 + 12 ≈ 88-89 min, still below 110 min.

Status: READY
