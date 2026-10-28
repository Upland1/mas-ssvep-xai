# P18 · 07 · Scientific review

Status: READY (pre-run audit); results review pending
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Audited commit: `aa71e1c` (branch `phase/P18-nbs`, base `main` 0038eec). Era C, no legacy behaviour prescribed.
Read: 00, 02, 03_changes_connectivity-stats.md, 04_tests.md, decisions.md P13/P14/P16/P18 rows, `git diff main..HEAD`
(src/stats/nbs.py, permutation.py, comparison.py, both connectivity scripts, P13/P14/P18 tests).

Verdict: PASS

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no classifier; permutations are trial-level (`src/features/connectivity/permutation.py:149`, unit "trial" in the run commands) |
| R2 Fit only in-fold | N/A | no fitted estimator; pseudo-z uses null statistics only, no labels beyond the permutation design |
| R3 Filter continuous, then window | PASS | `data/processed_continuous` broadband windows (P16 decision row: connectivity reads continuously filtered broadband in both modes); NBS adds no filtering |
| R4 Estimator small-sample bias | PASS | concatenated estimators unchanged; observed and null matrices come from the same `compute_permutation_test` call (`permutation.py:176`); group-size bias of the null is removed per edge by the pseudo-z centring (`src/stats/nbs.py:58-62`) |
| R5 Shared quality, explicit thresholds | PASS | `--quality shared`; one `quality` dict per subject reused across methods (`scripts/connectivity/analysis/analyze_connectivity_cohort.py` run loop, unchanged by P18) |
| R6 Index layouts verified | PASS | edge vector = `triu_indices(C,1)` (`nbs.py:38`), inverse `nbs.py:42-49`, C from E (`nbs.py:25-30`); tested against nested loops and a BFS reference (`tests/test_p18_independent_known_answer.py`, layout and random cross-check tests); PDC `(M+Mᵀ)/2` on obs and null (`nbs.py:36-37`, cohort `:160-164`), mutant M4 killed |
| R7 Honest statistics | PASS with CONCERNS C1, C3, C4 | pseudo-z from the trial-level null (`nbs.py:52-66`); null max from each permutation's own z-map (`nbs.py:95`); p with +1 and `>=` (`nbs.py:96,102`); size = edges (`nbs.py:81`); one-tailed cohort (`cohort:164`), two-tailed pairwise (`test_connectivity_frequency_differences.py:175`); A-FDR, A-NBS, B in separate columns and console lines (`cohort:253-280`); flip rule extended to A-NBS (`cohort:344`, pairwise `:333`) |
| R8 Smoothing respects trials | N/A | no smoothing |
| R9 Per subject, data source | PASS | per-subject rows in every table; `fs`, `source`, window counts appended to the summary (§6 order, pinned literally in `tests/test_p18_nbs.py:207-210`) |
| R10 Sources | PASS | no external NBS source opened; `nbs.py:12-13` says so and implements the roadmap P18.1 definition. The report may cite the original NBS paper only if it is opened in that run |
| R10 Copied lines | N/A | none |
| R11 Reference after attempt | PASS | no P18 entry in `mas/state/scratch/reference_access.log` (`grep -c 2026-10-28` → 0); handoff says "not consulted" |
| Golden rule 3 | N/A | no legacy path changed; `--stats fdr` keeps the pre-P18 console text |
| Tests | PASS | 17 builder + 21 independent tests; I re-ran both P18 files and the four edited P13/P14 schema tests: `42 passed in 78.54s`. Mutants M1 (+1 dropped), M2 (observed-only standardization), M3 (full-graph components), M4 (no PDC symmetrization), M5 (one-tailed pairwise), M6 (fixed 8 channels) killed (04_tests.md) |
| Changes match plan / roadmap | PASS | P18.1–P18.3 and settled points 1–7 implemented as written; `--summary-only` patched-out recomputation test |
| Privacy scan | PASS | fragment-built scan of `git diff main..HEAD` and of commit messages: 0 and 0; no data, recording files or local tooling paths in `git diff --name-only` (0) |

### Checks of the points in the request

1. **NBS definition.** Matches settled point 1 by inspection. Pseudo-z per edge from the null mean and std
   (ddof 0); std 0 or non-finite → 0, and `nan_to_num` on both maps (`nbs.py:58-63`). Null z-maps use the same
   standardization, and each permutation's largest component is taken from its own map (`nbs.py:95`).
   `p = (1 + #{null_max ≥ size})/(n+1)` for each component (`nbs.py:96`). Size is the number of edges (`bincount` of
   edge labels, `nbs.py:79-81`). The threshold is strict (`z > t`). With no supra-threshold edge, size is 0 and p = 1.
   The mask keeps only components with p < α. Because p is monotone in size, `nbs_significant == False` implies
   `nbs_n_sig_edges == 0`; the verifier checks this (V5). The standardization uses a null that contains the
   permutation itself; this is the usual convention and makes a negligible difference.
2. **PDC.** Symmetrized difference and null before NBS (21 or 28 undirected edges). FDR stays on the 42 or 56
   directed edges, so the two PDC denominators differ, and the graph-size table carries both
   (`possible_edges_nbs`, `total_edges_fdr`, `cohort:215-219`). Symmetrization averages i→j with j→i. A
   one-directional effect is halved, and opposite directions cancel. PDC NBS is therefore a test of undirected
   coupling change, not of directed flow, and PDC FDR-vs-NBS counts must not be compared as raw counts.
3. **Possible edges from kept channels.** C is derived from the edge-vector length of matrices built on the kept
   channels. `reports/connectivity_cohort_summary_v2cont.csv` shows 8 channels for S02/S05 (`total_edges` 28,
   PDC 56) and 7 for S01/S03/S04 (21/42). Mutant M6 was killed by the 7-vs-8 test.
4. **R7 and the flip rule.** The criteria are separate. The nulls are nested: the 200 seeds are the prefix of the
   1000. I checked this on S01 PDC 101 (`np.array_equal(null200, null1000[:200])` → True), so a flip is a
   resolution or standardization effect, not a replication (P13 D-4). **C4, new mechanism.** The builder's S01
   PDC 24 Hz flip (NBS p 0.030 → 0.272) is not p resolution. I recomputed it read-only in memory from
   `load_condition_windows` with no file written. At 200 permutations the observed component has 3 edges
   (top z 2.903, 2.026, 2.008). At 1000 it has 1 edge (2.704, 1.985, 1.848), because the re-estimated null
   std moves two edges below z = 2. The null tail is stable: P(null_max ≥ 3) is 0.025 vs 0.02, and
   P(null_max ≥ 1) is 0.305 vs 0.271. NBS flips can therefore come from observed edges sitting at the threshold
   (threshold-boundary fragility of the pseudo-z), which the sweep table makes visible. All flips stay
   inconclusive (R7). Classification rules are pre-committed below. The builder's 4/20 S01 flips are consistent
   with this: three A-FDR flips, where the BH minimum count makes 1–2 FDR edges impossible at 200 (rule F1
   below), plus this A-NBS case.
5. **Regression (settled point 6).** The FDR, global-p and edge-array path is unchanged. The only source edits
   add return keys (`permutation.py:176`, `comparison.py:326`). Seeds come from `SeedSequence(...).generate_state(n)`,
   independent of `n_jobs` chunking (`permutation.py:149`). The builder showed 15/15 columns equal on S01. The
   tester showed `--stats nbs` vs `fdr` frames and every npz array identical. I pinned the P16 root hash now:
   `find data/processed_continuous -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum` →
   `c59c94b8ac90a77f57148f057698411f97690ec1174b1202237b37624144a54e`, 65 files. This equals the P17 pin, so
   the v2cont inputs are unchanged and exact equality is the right expectation (V3).
6. **Schema-pin edits.** P14 pins are extended with literal column names
   (`tests/test_p14_known_answer.py`, `tests/test_p14_connectivity_comparison.py`). The P13 pin keeps the 15
   pre-P18 columns literally and compares the remainder with `cohort.SUMMARY_COLUMNS`. That comparison is
   self-referential, but the tail is pinned literally in `tests/test_p18_nbs.py:207-210`, so nothing is lost. The
   npz key set adds `nbs` literally. Acceptable.
7. **Pairwise NBS on an off-centre null (P14 D-2). CONCERN C1.** The pairwise pseudo-z centres each edge on its
   exchange-null mean. A two-tailed |z| > 2 NBS is therefore a **centred** test: it asks whether the a/b
   difference exceeds what the own-band exchange null already produces per edge. That is the edge-level analogue
   of `p_mag_centred`, not of `p_mag` or of the uncentred edge FDR (`|null| ≥ |obs|`, `comparison.py`). On real
   data the null centre was 0.62–0.79 of |t_mag| (P14 D-2), so most of the band-level offset is removed before
   thresholding. A significant pairwise NBS component is then the excess beyond the band-level part. Pairwise
   NBS and FDR/p_mag can disagree for this reason alone, and the H0 is still a/b-trial exchangeability, not
   Δa = Δb. In addition, two-tailed |z| lets one component mix positive and negative edges. That is allowed by
   the roadmap ("two-tailed NBS at |z| > 2") but must be stated. No code change: wording and report items R3–R4
   below.
8. **Responders source.** `reports/n_subjects_benchmark_v2cont.csv` is the right Era C source: P16 continuous
   build, the same root and masks as the connectivity windows, fs 256, 5 classes. P17 files use the `_p17` root
   and 6 classes, so they are not comparable. From the CSV, 2.0 s smoothed gives S01 77.90 (SD 2.10), S02
   75.26, S03 93.92, S04 99.49, S05 98.79, so the responders are S03/S04/S05, the same split as P14. S01 is
   1.0 SD below the 80 % cut. The split is a fixed classifier-only rule (PF-21) used only in the pairwise group
   lines, and the report must say that S01 is near the cut. PASS.
9. **Budget. CONCERN C2.** The builder's projection (≈ 89 min) is low. P16 logs
   (`reports/logs/P16/15_…cohort.log`) show coherence at 82.2 s (S02) and 87.9 s (S05) vs 62.7–68.2 s on the
   7-channel subjects, so 8 channels do slow the expensive part. Measured anchors: cohort 200 permutations =
   387.3 s (P16 v2cont); pairwise 1000 = 2700.5 s on 7 channels (P14 `cmd3_final.log`). Projection
   (`python3 -c`, shown in the audit session): cohort 200 ≈ 6.5 min, cohort 1000 ≈ 32.3 min, pairwise 1000 ≈ 45.0
   to 50.8 min (8-channel adjustment), suite ≈ 12.5 min, total ≈ 96–102 min. This is inside 120 and below the
   plan's 110-min trigger, with about 18 min margin. Stop rule V0 below.
10. **C3, pairwise has no second permutation count.** Settled point 4 gives the pairwise test 1000 permutations
   only, so the R7 flip rule cannot be applied to `nbs_p`, `p_mag` or `p_pat` in P18. A p500 run would cost about
   25 min and exceed the budget. Report item R5 requires the borderline labelling below instead. Not blocking,
   because the plan settled it and P14 already holds the p500/p1000 flip record for the same test design.

### Required fixes

None. Verdict PASS. The run is valid only if the verifier carries out V0–V8 below; the orchestrator copies them
into `02_plan.md` before the run.

### Pre-committed run checks (verifier)

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

### Pre-committed reporting rules (scribe and results review)

- **F1 (A-FDR flips).** All flips are inconclusive (R7). An A-FDR flip with 0 edges at 200 and 1 to (k−1) edges at
  1000 is labelled **BH-resolution-limited**, where k = the smallest non-zero BH count possible at 200
  permutations: ceil(m/(201·0.05)) = 3 for m = 21 or 28, 5 for 42, and 6 for 56 (`python3 -c`, audit session).
  This is because such counts cannot occur at 200.
- **F2 (A-NBS flips).** Join `nbs_max_size` from both summaries. If the observed size differs, the flip is
  labelled **threshold-boundary** (standardization moved edges across z = 2, as on S01 PDC 24 Hz). If the size
  is equal, it is labelled **p-resolution**. Flips of B are Monte Carlo flips. Report counts per class and
  method. The reported values are the 1000-permutation ones.
- **R1 (FDR vs NBS disagreement).** At 1000 permutations, report per method a 2 × 2 table of A-FDR × A-NBS with
  B beside it. List every disagreeing cell with its FDR count, NBS size and p, and global p. FDR+/NBS− = focal
  edges whose components do not beat the null maximum. FDR−/NBS+ = an extended moderate effect. For PDC, the
  denominators (42/56 directed vs 21/28 symmetrized) and the symmetrization caveat are stated beside the table.
  Counts are compared as % of each method's own denominator (P16 C-4).
- **R2 (graph sizes).** Sizes are % of the subject's possible edges. 7- and 8-channel subjects are compared only
  as %. PDC on 8 channels is not comparable with 7 channels (P16 D-8).
- **R3 (pairwise wording).** "Pairwise NBS (two-tailed, |z| > 2 on the exchange null centred per edge): tests
  a/b-trial exchangeability beyond the per-edge null centre; not a test of Δa = Δb; components may mix signs."
  `<m>_pairwise_null` is reported alongside (P14 D-2).
- **R4 (pairwise agreement).** Give 2 × 2 tables of NBS p < 0.05 vs `p_mag` < 0.05 and vs `p_mag_centred` < 0.05,
  with counts in the 13 P14 "null off-centre" cells reported separately.
- **R5 (pairwise borderline).** Pairwise cells with 0.036 ≤ p ≤ 0.064 on `nbs_p`, `p_mag` or `p_pat` (±2
  binomial SE at 1000, SE = 0.0069) are labelled "borderline, not flip-checked (single permutation count)".
- **R6.** The 1.0 s/2.0 s accuracy behind the responder split is quoted from the v2cont CSV with its source.
  S01 is noted as 1 SD below the cut.

### A-priori directions (record, R-16: no numeric target; a miss is investigated, not tuned)

- **P1.** Sweep sizes do not increase with the threshold (exact, V5). NBS p is not expected to be monotone.
- **P2 (sensitivity).** At 1000 permutations, the number of A-NBS cells is ≥ the number of A-FDR cells overall.
  For reference, P16 v2cont at 200 had A-FDR in 36/100 cells, B in 32/100 and both in 25/100. Basis: FDR edges
  at the BH threshold have one-tailed p ≲ 0.007, i.e. z ≳ 2.4 > 2, and the null tail is small
  (S01 PDC P(null_max ≥ 3) ≈ 0.02).
- **P3.** Of the cells with ≥ 3 FDR edges at 1000, ≥ 80 % are A-NBS. Exceptions must show FDR edges with no
  shared node, or a heavy null-maximum tail (volume-conducted coherence).
- **P4 (responders).** S03/S04/S05 have larger graphs and more A-NBS cells than S01/S02. In P16 v2cont, S01/S02
  had 0 FDR edges in every coherence, PLV and wPLI cell. For the non-responders (40 cells), ≤ 4 A-NBS cells is
  consistent with chance: Bin(40, 0.05) has mean 2 and P(X ≥ 5) = 0.048 (`python3 -c`, audit session). ≥ 5 is
  reported as "more than chance" and examined cell by cell. S01 already had 2 at 200 permutations.
- **P5.** Cells with B positive have larger NBS sizes than B-negative cells within each method, because a
  widespread effect raises both.
- **P6 (PDC).** Symmetrized PDC graphs are smaller (in %) than coherence, PLV and wPLI graphs of the same
  subject and frequency. A-NBS is not expected where the PDC FDR edges are one-directional.
- **P7 (alpha frequencies).** At 8.57 and 10.91 Hz, coherence and PLV graphs are small in the one-tailed
  (stimulus > baseline) test, because a stimulus can sit below baseline there (P13 D-3). Decreases are not
  tested by the one-tailed NBS, and the report must say that.
- **P8 (pairwise).** NBS agrees more often with `p_mag_centred` than with `p_mag` (C1). A pairwise NBS cell is
  read as a stimulus-specific excess, never as "the two frequencies differ in connectivity" without that
  qualifier.

### Non-blocking notes

- N1. The cohort flips file carries `nbs_p` but not `nbs_max_size`. F2 joins the two summaries; adding the sizes to
  the flips file would be a small later improvement (connectivity-stats).
- N2. 03_changes says 8-channel subjects "add edges only to the cheap parts". The P16 logs contradict this (coherence
  +20–30 s per 8-channel subject at 200 permutations). Use measured multi-subject logs for future projections
  (P14 D-5 lesson).
- N3. The cohort NBS is upper-tailed only. A lower-tailed NBS (stimulus < baseline, alpha suppression) is not computed;
  this is an open option for a later phase, not a P18 requirement.

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
