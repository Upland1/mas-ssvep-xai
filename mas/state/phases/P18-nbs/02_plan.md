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

```bash
P=".venv/bin/python -m"
C="$P scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutation-unit trial --n-jobs -1 --data-root data/processed_continuous --quality shared"
$C --permutations 200  --out-suffix p18_nbs_p200
$C --permutations 1000 --out-suffix p18_nbs
$P scripts.connectivity.comparison.test_connectivity_frequency_differences --methods coherence plv wpli --permutations 1000 --data-root data/processed_continuous --quality shared --benchmark reports/n_subjects_benchmark_v2cont.csv --out-suffix p18_nbs
$P scripts.connectivity.comparison.test_connectivity_frequency_differences --summary-only --out-suffix p18_nbs --benchmark reports/n_subjects_benchmark_v2cont.csv
```

Exact flag names (NBS thresholds, primary, the graph-size and sweep tables' paths) are
confirmed in `03_changes_connectivity-stats.md`; the orchestrator copies the final list
here before the run. Estimate from P16/P14 logs: cohort 200 ≈ 7 min, cohort 1000 ≈ 35
min, pairwise 1000 ≈ 45 min, suite ≈ 11 min: ≈ 100 min, inside `LOCAL_RUN_BUDGET_MIN` 120
but close. The builder measures one subject; if the projected total exceeds 110 min, the
orchestrator issues a human-run request for the pairwise run.

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
