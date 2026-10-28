# P18 · 00 · Assignment — Network-Based Statistic replaces FDR

Status: READY
Author: orchestrator
Branch: phase/P18-nbs (from main @ 0038eec, tag p17-done)
Era: C. Legacy behaviours required: **none**. Enforced: R3 (phase from the CSD; continuous built windows), R4 (concatenated estimators), R5 (shared quality, explicit thresholds), R6 (edge/upper-triangle layouts), R7 (trial-level permutations with observed group sizes; global p, FDR and NBS as separate criteria; flips across p = 0.05 between permutation counts are inconclusive), R9, fs from metadata.
Owners (agents): connectivity-stats (Connectivity & Stats); scientific-reviewer; verifier
Depends on: P16 (passed), P17 (passed; merged 0038eec)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Branch `feature/network-based-statistics`: replace edge-wise FDR with
graph-based statistics and compare the sizes of the significant graphs.
**Depends on:** P16 (uses the P13/P14 machinery). **Owners:** Connectivity & Stats,
Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/stats/nbs.py`: `edge_pseudo_z(obs, null, two_tailed)` (standardize by each
   edge's null mean/std, infinite std → 0), connected components of supra-threshold
   edges (`scipy.sparse.csgraph`), `nbs_test(z_obs, z_null, threshold, alpha)`
   (component size = number of edges; null = max component size per permutation;
   p = (1 + #{null_max ≥ size})/(n+1); significant mask, max size, p of largest,
   n significant edges, possible edges), `nbs_sweep(obs, null, thresholds=(1.5, 2.0,
   2.5, 3.0), …)` reusing the same permutations.
2. Cohort script: NBS on the existing permutation nulls per condition (PDC symmetrized
   first), `--stats {nbs,fdr}` (default nbs) selects the summary criterion, both always
   saved; `--nbs-thresholds`, `--nbs-primary 2.0`; new CSV columns (§6); `nbs_c` masks
   in the edge files; a **graph-size table** (largest component as % of possible
   edges, * if significant) and a threshold-sweep table.
3. Between-frequency tests: two-tailed NBS at |z| > 2 on the pairwise permutation
   nulls; `--summary-only` re-prints group summaries from saved CSVs.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/stats/nbs.py`, NBS columns and graph-size tables

## Acceptance (verbatim)

Acceptance: NBS unit tests; cohort tables with both FDR and NBS; the report compares
graph sizes across subjects and frequencies (record).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-19 | mas/05_PITFALLS.md | NBS reuses trial-level permutation nulls with matched group sizes |
| PF-20 | mas/05_PITFALLS.md | (A) ≥ 1 FDR/NBS edge and (B) global p < α reported separately |
| PF-21 | mas/05_PITFALLS.md | responders from classifier accuracy only (Era C source: `reports/n_subjects_benchmark_v2cont.csv`, 2.0 s ≥ 80 %: S03, S04, S05) |
| PF-25 | mas/05_PITFALLS.md | PDC symmetrized, nulls likewise, before NBS |
| PF-26 | mas/05_PITFALLS.md | `channels_kept` in every edge file; possible edges depend on the channel count (S02/S05 have 8 channels) |
| R-16 | mas/04_REFERENCE_RESULTS.md | no preserved NBS numbers; record, reviewer checks direction and plausibility |
| §6 | mas/02_REQUIREMENTS.md | cohort summary NBS columns (`nbs_threshold … source`), `nbs_c` in edge npz, pairwise columns `nbs_max_size, nbs_p, n_edges_nbs, fs` |
| decisions P16 C-4 | | FDR counts as fractions of possible edges when channel sets differ |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| connectivity-stats | P18.1–P18.3, C-4 | `03_changes_connectivity-stats.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P18.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
