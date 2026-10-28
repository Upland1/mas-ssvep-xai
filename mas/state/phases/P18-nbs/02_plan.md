# P18 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md R3/R4/R5/R7, mas/02_REQUIREMENTS.md §5.8, §6, mas/04_REFERENCE_RESULTS.md R-16, mas/05_PITFALLS.md PF-19/20/21/25/26, decisions.md P13 (D-4 nested nulls, BH), P14 (pairwise null off-centre, D-5), P16 (C-4)
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Add the Network-Based Statistic (as specified in the roadmap) next to edge-wise FDR in the
cohort connectivity script and the between-frequency tests, on the Era C data, and
compare the sizes of the significant graphs across subjects and frequencies.

## Data source

- `data/processed_continuous/<S>/` (P16 continuous build, guard 0.902 s, shared quality),
  broadband windows; the P17 root is not needed (connectivity does not use the narrow
  banks). fs, true trial ids and kept channels from `load_subject`.
- Responders (PF-21): `--benchmark reports/n_subjects_benchmark_v2cont.csv`, 2.0 s ≥ 80 %
  → S03, S04, S05 (the same data source as the connectivity windows).

## Settled points (inferred; recorded in decisions.md)

1. **NBS definition (task 1).** Pseudo-z per edge = (obs − null mean)/null std over the
   permutations of that edge; std 0 or non-finite → z 0. Supra-threshold edges at z > t
   (one-tailed stimulus > baseline in the cohort, matching the existing one-tailed edge p;
   two-tailed |z| > 2 in the between-frequency tests, task 3). Components with
   `scipy.sparse.csgraph.connected_components` on the undirected supra-threshold graph;
   size = number of edges. Null: for each permutation, its z-map (standardized with the
   same null mean/std) → max component size. p = (1 + #{null_max ≥ size})/(n + 1).
   Primary threshold 2.0; sweep (1.5, 2.0, 2.5, 3.0) on the same permutations.
2. **PDC** symmetrized `(M + Mᵀ)/2`, nulls likewise, before NBS (PF-25). FDR on PDC
   keeps its directed 42 edges (P13), so FDR and NBS denominators differ for PDC;
   both are recorded.
3. **Criteria kept separate** (PF-20, R7): (A-FDR) ≥ 1 FDR edge, (A-NBS) NBS largest
   component p < α, (B) global p < α. `--stats {nbs,fdr}` selects the criterion printed
   in the console summary; both always saved.
4. **Permutations.** Cohort: 1000 trial-level permutations (final) and 200 (the P16
   `v2cont` count) to apply the R7 flip rule to the NBS p; between-frequency: 1000 (the
   P14 final count). Seed 42 as before. Exact counts may be lowered only by a
   human-run request if the measured runtime exceeds the budget.
5. **Graph-size table.** Largest component as % of possible edges (n_channels·(n−1)/2 for
   the subject's kept channels), `*` if NBS-significant, per subject × method ×
   frequency; threshold-sweep table per subject × method × frequency × threshold. FDR
   edge counts are also given as % of possible edges (P16 C-4).
6. **Regression.** With `--stats fdr` the existing FDR columns, global p and edge arrays
   are byte/value-identical to the pre-port script on the same data and permutations
   (NBS only adds columns and the `nbs_c` keys). Proved on a synthetic folder and, in the
   run, by comparing the 200-permutation output's FDR columns with P16
   `reports/connectivity_cohort_summary_v2cont.csv` (same data, same 200 permutations).
7. **`--summary-only`** re-prints group summaries from saved CSVs without recomputation.
8. **Tests** never read generated or git-ignored files.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Task |
|---|---|---|---|
| connectivity-stats | NEW `src/stats/nbs.py`; MODIFIED `src/features/connectivity/permutation.py` as needed, `scripts/connectivity/analysis/analyze_connectivity_cohort.py`, `scripts/connectivity/comparison/test_connectivity_frequency_differences.py` | tasks 1–3, settled points 1–7 | P18.1–P18.3 |

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R7 / NBS | null max computed with the observed standardization only, or on the observed graph | test: null max sizes from each permutation's own z-map; p formula with +1 |
| R7 | a null-std of 0 makes z infinite | test: std 0 → z 0 |
| R6 | upper-triangle ↔ matrix mapping wrong; components on the wrong edges | planted connected cluster of known size → found with that size; two disjoint clusters → largest = bigger one |
| PF-25 | PDC not symmetrized | test: asymmetric planted PDC → symmetric matrix enters NBS |
| PF-26 | possible edges from a fixed 7 or 8 | from kept channels |
| PF-20 | NBS significance shown as the global criterion | separate columns and console lines |
| PF-19 | NBS on window-level nulls | NBS reuses the trial-level null only |

## Tests required

| Test | Simulated input | Expected result | Tolerance |
|---|---|---|---|
| pseudo-z | known null mean/std; zero-std edge | exact z; 0 for zero std | 1e-12 |
| components | planted cluster of 5 edges + isolated edge | largest = 5 | exact |
| NBS null | permutations with known max sizes | p = (1 + #{≥})/(n+1) | exact |
| NBS power | 8-channel coupled subnetwork vs independent | significant, mask = planted edges; independent → p ≥ α in ≥ 95 % of seeds | exact / rate |
| sweep | same permutations, 4 thresholds | sizes non-increasing in threshold | exact |
| PDC | asymmetric planted | symmetrized before NBS | exact |
| cohort port | synthetic built folder | FDR columns unchanged vs `--stats fdr`; NBS columns and `nbs_c` present; graph-size table | exact |
| pairwise | synthetic two-frequency difference | two-tailed NBS at 2 finds it; null → not | exact / rate |
| summary-only | saved CSVs | same summary text, no recomputation | exact |

## Run commands (for the verifier, in order)

Final list, copied from `03_changes_connectivity-stats.md` (882fdc9) before the run:

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

Measured by the builder (S01): cohort 200 ≈ 5.5 min, cohort 1000 ≈ 27.5 min, pairwise 1000 ≈ 43.4 min for 5 subjects; with the suite (≈ 12.5 min) ≈ 89 min, inside 120.

Estimate from P16/P14 logs: cohort 200 ≈ 7 min, cohort 1000 ≈ 35
min, pairwise 1000 ≈ 45 min, suite ≈ 11 min: ≈ 100 min, inside `LOCAL_RUN_BUDGET_MIN` 120
but close. The builder measures one subject; if the projected total exceeds 110 min, the
orchestrator issues a human-run request for the pairwise run.

### Pre-committed run checks V0–V8 (07_review.md 0044229, copied verbatim; binding for the verifier)

- **V0 (budget, before and during the run).** Run the suite first, then commands 1–3. If cumulative wall time
  after command 3 exceeds 69 min (120 − 51), command 4 (pairwise) and command 5 become a human-run request.
  Record every command's runtime in 05_run.md.
- **V1 (pre-state).** `find reports -name "*p18*" | wc -l` → 0 (0 at audit time; no stale same-name outputs). The
  P16 root hash command above gives `c59c94b8…144a54e` with 65 files before command 1 and after the last command.
- **V2 (columns and npz).** Every summary CSV has 33 columns: the 15 pre-P18 ones in order, then
  `nbs_threshold, nbs_max_size, nbs_size_fraction, nbs_p, nbs_n_sig_edges, nbs_significant, nbs_size_z1.5,
  nbs_size_z2, nbs_size_z2.5, nbs_size_z3, nbs_p_z1.5, nbs_p_z2, nbs_p_z2.5, nbs_p_z3, n_stim_windows,
  n_baseline_windows, fs, source`. There are 100 rows (5 subjects × 4 methods × 5 conditions) with fs 256.0.
  Each run has 20 edge npz files, each with `channels_kept` and `stim/base/diff/p/fdr/nbs_<c>` for the five
  conditions. Every `nbs_<c>` is a boolean (C, C) array, symmetric, with a False diagonal, where C =
  len(channels_kept). Pairwise CSVs have the 20 §6 columns and 50 rows per method (150 in total).
- **V3 (settled point 6, exact).** For `connectivity_cohort_summary_p18_nbs_p200.csv` vs
  `connectivity_cohort_summary_v2cont.csv`, sorted by (subject, method, condition): every one of the 15 columns
  is equal. Floats must satisfy |Δ| ≤ 1e-12 with NaN aligned; strings and bools must be equal with
  NaN = NaN (`channels_dropped` is empty for S02/S05). The same holds for the shared `_details.csv` columns and
  for the `stim/base/diff/p/fdr` arrays of `connectivity_edges_p18_nbs_p200/` vs `connectivity_edges_v2cont/`
  (`np.array_equal(..., equal_nan=True)`). Any difference is a FAIL of the regression claim: determinism
  investigation, no reinterpretation.
- **V4 (tables complete).** Each `connectivity_graph_size_<s>.csv` has 100 rows with `possible_edges_nbs` = 21
  (S01/S03/S04) and 28 (S02/S05) for **all four methods** including PDC, and `total_edges_fdr` 21/28, or
  42/56 for PDC. Each `connectivity_nbs_sweep_<s>.csv` has 400 rows (5 × 4 × 5 × 4 thresholds 1.5/2/2.5/3).
  Both tables are printed in the log.
- **V5 (internal consistency, every row).** `nbs_size_z2 == nbs_max_size` and `nbs_p_z2 == nbs_p`.
  `nbs_significant == (nbs_p < 0.05)`. `nbs_size_fraction × possible == nbs_max_size`. p ≥ 1/(n+1).
  If `nbs_significant` is False then `nbs_n_sig_edges == 0`, else `nbs_n_sig_edges ≥ nbs_max_size`. The sum of
  `nbs_<c>` / 2 == `nbs_n_sig_edges`. In the sweep, `max_size` is non-increasing in the threshold for every
  cell (guaranteed by construction; any violation is a bug).
- **V6 (flips file).** `connectivity_cohort_flips_p18_nbs_p200_vs_p18_nbs.csv` exists, and its rows are exactly
  the cells where A-FDR (≥ 1 edge), B (global p < 0.05) or A-NBS (`nbs_p < 0.05`) differ between the two
  summaries. Recompute this from the summaries and compare.
- **V7 (pairwise).** `nbs_p ≥ 1/1001`; `n_edges` = 21/28 by subject; `n_edges_nbs == 0` whenever
  `nbs_p ≥ 0.05`; `--summary-only` output lines equal the corresponding lines of command 4's log.
- **V8.** No file under `reports/` is edited by hand; logs go to `reports/logs/P18/`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked |
|---|---|
| NBS unit tests | the tests above pass in the suite |
| cohort tables with both FDR and NBS | `reports/connectivity_cohort_summary_p18_nbs.csv` with the §6 NBS columns, `nbs_c` in every edge npz, graph-size and sweep tables |
| the report compares graph sizes across subjects and frequencies (record) | tables complete for S01–S05 × 4 methods × 5 frequencies; R-16, no target |
| (settled point 6) | 200-permutation FDR columns equal P16 `connectivity_cohort_summary_v2cont.csv` |
| (R7) | NBS p at 200 vs 1000 permutations: cells flipping across 0.05 listed as inconclusive |

## Sources

1. `mas/03_ROADMAP.md` P18 (opened in this run).
2. `mas/02_REQUIREMENTS.md` §5.8, §6; `mas/05_PITFALLS.md` PF-19/20/25/26 (opened in this run).

No external NBS source was opened by the orchestrator (R10); the builder cites per
`mas/CITING.md` any source it opens.

## Questions
