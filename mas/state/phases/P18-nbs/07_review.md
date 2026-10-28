# P18 · 07 · Scientific review

Status: READY (pre-run audit PASS; results review APPROVE)
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

Reviewed: HEAD `7fa6806`. The run ran at `32738cc`. `git diff --stat aa71e1c 32738cc -- src scripts tests configs` and
`git diff --stat 0044229 HEAD -- src scripts tests configs` are both empty, so the audited code is the code that ran.
Read: 05_run.md, 06_verify.md (verifier PASS, b96d5df), `reports/logs/P18/01`–`06`, `10_check_pairwise.txt`,
`11_check_cohort.txt`, `12_directions.txt`, `reports/connectivity_cohort_summary_p18_nbs{,_p200}.csv`,
`reports/connectivity_graph_size_p18_nbs.csv`, `reports/connectivity_nbs_sweep_p18_nbs.csv`,
`reports/connectivity_cohort_flips_p18_nbs_p200_vs_p18_nbs.csv`,
`reports/connectivity_comparison/{coherence,plv,wpli}_pairwise_{tests,null}_p18_nbs.csv`, the edge npz files
(S01 wpli, S04 pdc, S05 plv) and `reports/n_subjects_benchmark_v2cont.csv`. All my recomputations were read-only, done
with `.venv/bin/python -c` in this session; the commands are quoted where a number is new.

Verdict: APPROVE

### Acceptance (00_assignment.md, verbatim items)

| Item | Result | Evidence |
|---|---|---|
| NBS unit tests | met | `tests/test_p18_nbs.py` and `tests/test_p18_independent_known_answer.py` are in the suite: `1204 passed, 1 skipped` on the clean checkout (`reports/logs/P18/01_pytest.log`). Mutants M1–M6 were killed (pre-run audit). |
| Cohort tables with both FDR and NBS | met | Both summaries have 33 columns, A-FDR and A-NBS in separate columns (V2). The graph-size table carries `nbs_size_pct` with the FDR % in brackets, printed in `03_cohort_p1000.log:59-…`. The sweep table has 400 rows (V4). The FDR path is unchanged, |Δ| = 0 against v2cont (V3). |
| The report compares graph sizes across subjects and frequencies (record) | data met; report pending | The per subject × method × frequency table exists (`12_directions.txt`, "largest pct (*=sig)"). `mas/state/reports/P18.md` does not exist yet. The scribe must write that comparison following S1–S9 below. |
| V0–V8 | met | 06_verify.md. I re-checked V6 and F2 from the flips file (17 rows) and V7 from the CSVs. |

### Pre-committed reporting rules applied

**F1, A-FDR flips (14).** k = ceil(m/(201·0.05)) gives 3, 3, 5 and 6 for m = 21, 28, 42 and 56
(`python3 -c "import math; [math.ceil(m/(201*0.05)) for m in (21,28,42,56)]"`).
- **BH-resolution-limited: 11 flips.** Each goes from 0 edges at 200 permutations to between 1 and k−1 edges at 1000:
  S01 pdc 101 (2/42), 103 (1/42), 105 (1/42); S03 coherence 104 (1/21), plv 105 (1/21), wpli 102 (2/21); S04 plv 105
  (1/21), wpli 103 (2/21); S05 wpli 102 (1/28), pdc 102 (5/56), pdc 105 (2/56).
- **Not BH-limited by F1: 3 flips.** These are Monte Carlo flips of the p grid.
  - S01 wpli 104 (0 → 4/21). Its edge p at 200 were 0.005, 0.005, 0.01 and 0.0149, and BH needs p(4) ≤ 0.0095.
  - S04 pdc 105 (0 → 6/42).
  - S05 plv 101 (3 → 0/28), the only downward flip. Its p went from 0.005 ×3 to 0.003, 0.005 and 0.006, against BH
    limits of 0.0054, 0.0036 and 0.0018. This came from reading the per-edge `p_<c>` at the FDR edges in both npz runs.

All 14 flips are inconclusive (R7).

**F2, A-NBS flips (6).** All 6 are **threshold-boundary**: the observed size changed in every one, and none is
p-resolution. The cells are:

| Cell | Size at 200 → 1000 | NBS p at 200 → 1000 |
|---|---|---|
| S01 pdc 101 | 3 → 1 | 0.0299 → 0.2717 |
| S02 wpli 102 | 3 → 2 | 0.0448 → 0.1039 |
| S03 plv 103 | 4 → 2 | 0.0100 → 0.0509 |
| S04 plv 105 | 1 → 3 | 0.0846 → 0.0110 |
| S05 wpli 101 | 3 → 5 | 0.0647 → 0.0290 |
| S05 pdc 105 | 3 → 2 | 0.0348 → 0.1049 |

By method there are 2 each for pdc, plv and wpli, and 0 for coherence. B had 0 flips. Every flip is inconclusive.
This confirms the pre-run C4 mechanism at cohort scale: when the null is re-estimated, the standardization moves
edges that sit near z = 2 across the threshold. The reported values are the 1000-permutation ones.

**R1 (FDR × NBS at 1000).** The 2 × 2 tables, as [FDR−/NBS−, FDR−/NBS+; FDR+/NBS−, FDR+/NBS+], are:

| Method | Table |
|---|---|
| coherence | [12, 0; 1, 12] |
| pdc | [9, 2; 5, 9] |
| plv | [16, 1; 0, 8] |
| wpli | [11, 1; 3, 10] |

The 13 disagreeing cells are listed in `12_directions.txt`.
- **FDR+/NBS−: 9 cells.** In 8 of them the FDR count is ≤ 2 edges, and all 8 had 0 FDR edges at 200. The ninth is
  S04 pdc 102 (see P3). These are focal edges whose component does not beat the null maximum.
- **FDR−/NBS+: 4 cells.** S03 pdc 104 (size 3, p 0.0190), S03 pdc 105 (3, 0.0150), S05 plv 101 (3, 0.0280) and
  S05 wpli 101 (5, 0.0290). These are extended moderate effects. The last two are flips.

The PDC denominators (42/56 directed vs 21/28 symmetrized) and the symmetrization caveat must sit beside the PDC table.

**R2.** The graph-size table and `12_directions.txt` give sizes in %. S02 and S05 have 8 channels, so they are compared
with the others only as %. PDC on 8 channels is not comparable with PDC on 7 (P16 D-8).

**R3–R5 (pairwise).** Pairwise NBS is centred, as pre-registered (C1). The wording of rule R3 is mandatory. The R4
agreement tables against `p_mag_centred` were not in 06_verify.md, so I computed them. `p_mag_centred` is in
`<m>_pairwise_null_p18_nbs.csv`, which joins one-to-one with the tests CSV on (subject, method, freq_a, freq_b), 50 rows
per method. I used
`.venv/bin/python -c "…t.merge(n,on=k); pd.crosstab(t.nbs_p<.05, n.p_mag_centred<.05)…"` (session command, read-only).
Tables are [NBS−/x−, NBS−/x+; NBS+/x−, NBS+/x+]:

| Method | vs `p_mag` (agree /50) | vs `p_mag_centred` (agree /50) | "null off-centre" cells (p_mag ≠ p_mag_centred side of 0.05): NBS agrees with mag / centred |
|---|---|---|---|
| coherence | [36, 6; 3, 5] (41) | [41, 1; 3, 5] (46) | 7: 1 / 6 |
| plv | [33, 3; 9, 5] (38) | [35, 1; 5, 9] (44) | 6: 0 / 6 |
| wpli | [41, 3; 2, 4] (45) | [43, 1; 2, 4] (47) | 4: 1 / 3 |

The 13 "null off-centre" cells of P14 D-2 came from a different data source: legacy windows on the fs-250 axis
(`reports/logs/P14/cmd3_final.log` header). P18's p_mag differs from P14's (`np.allclose` False for all three methods).
The off-centre cells are therefore defined on P18's own data: 17 cells (7 + 6 + 4). **P18 is the first pairwise run on
the continuous build** (fs 256, S02/S05 with 8 channels), and the report must state this source (R9) and not compare
it with P14 as a re-run.

**R5 (borderline).** There are 6, 8 and 5 borderline cells for coherence, plv and wpli (my list matches the verifier's
counts). Five of the 28 NBS+ cells are borderline on `nbs_p` itself: S02 coherence 24–8.57 (0.0450) and 15–10.91
(0.0470), S05 coherence 24–10.91 (0.0470), S03 plv 24–20 (0.0480) and S01 wpli 20–8.57 (0.0460). All five are labelled
"borderline, not flip-checked (single permutation count)".

**R6 / responder split.** From `reports/n_subjects_benchmark_v2cont.csv` (continuous build, session OO, 5 classes),
1.0 s / 2.0 s smoothed accuracy is: S01 72.8 / 77.9 (SD 2.1), S02 72.42 / 75.26, S03 93.61 / 93.92, S04 99.49 / 99.49,
S05 98.59 / 98.79. S01 is (80 − 77.9)/2.1 = 1.0 SD below the 80 % cut (`python3 -c`, this session). Its
non-responder label is a fixed classifier rule (PF-21), not a finding.

### A-priori directions (R-16: record; a miss is investigated, not tuned)

| | Direction | Obtained | Reading |
|---|---|---|---|
| P1 | sweep non-increasing | held in all 100 cells of both runs (V5) | met (exact by construction) |
| P2 | A-NBS ≥ A-FDR at 1000 | 43 vs 48; at 200, 45 vs 36 | **refuted at 1000** (D-2) |
| P3 | ≥ 80 % of cells with ≥ 3 FDR edges are A-NBS | 36/37 = 97.3 % | met; the exception is explained (D-3) |
| P4 | responders larger; non-responders ≤ 4/40 A-NBS | non-responders 1/40 (S01 wpli 104, size 4, p 0.0350; also 0.0398 at 200); responders 42/60; mean largest % S01 2.6, S02 1.6, S03 38.8, S04 32.1, S05 12.1 | met; non-responder count consistent with chance (Bin(40, 0.05) mean 2) |
| P5 | B+ cells have larger NBS sizes | mean size B−/B+: coherence 2.0/14.0, pdc 1.81/4.33, plv 1.0/8.25, wpli 1.36/9.0 | met in 4/4 methods |
| P6 | PDC graphs (%) smaller than coherence, PLV, wPLI | mean %: pdc 12.1, coherence 26.3, plv 10.1, wpli 21.3. PDC smaller / equal / larger than the same cell: vs coherence 13/4/8, vs wpli 11/5/9, vs plv 4/6/15 (of 25) | **partly refuted** (D-4): holds for coherence and wPLI on average, not for PLV |
| P7 | coherence and PLV graphs small at 10.91/8.57 Hz | coherence 14.0/16.9 vs mean 33.5 at 24/20/15 Hz; PLV 8.6/5.7 vs 12.1 (PLV 15 Hz 6.7 lies between) | met on means. wPLI (not predicted) is high at 104/105 (23.1/26.9). One-tailed test only. Large per-subject spread (coherence 104: S04 57.1 %, S03 4.8 %, S05 3.6 %) |
| P8 | pairwise NBS agrees more with `p_mag_centred` than `p_mag` | 46 vs 41, 44 vs 38, 47 vs 45; off-centre cells 15/17 with centred vs 2/17 with mag | met in 3/3 methods (D-5) |

**P2 (own basis error).** My basis was that FDR edges at the BH threshold have z ≳ 2.4, so they are supra-threshold. I
took supra-threshold to mean significant, and that does not follow. A 1- or 2-edge component must still beat the null
maximum. For S01 PDC, P(null_max ≥ 1) is about 0.27–0.31 (pre-run C4). At 1000 permutations BH also admits 1- or
2-edge results that are impossible at 200, so A-FDR rose 36 → 48 almost entirely through such cells (F1: 11
resolution-limited flips). The arithmetic is 48 − 43 = 5 = 9 FDR+/NBS− − 4 FDR−/NBS+.

Neither criterion is uniformly more sensitive. NBS gains on extended moderate effects and loses on focal ones. The
200-permutation comparison (45 vs 36) is not a fair test either, because FDR is resolution-limited there. The report
states P2 as refuted, with this decomposition, and does not call NBS "more sensitive".

**P3 exception (S04 pdc 102).** There are 5 directed FDR edges, all at p 0.001–0.002 (`connectivity_edges_p18_nbs/S04_pdc.npz`):
POz→Oz, O1→PO3, O1→Oz, Oz→PO3 and Oz→POz. They share nodes (Oz is in 4 of them), so neither exception listed under P3
applies. The cause is the symmetrization caveat pre-registered in point 2 and P6: opposite directions cancel. The
diffs are O1–Oz +0.2255 / −0.2229 and Oz–PO3 +0.1123 / −0.0641. Only POz↔Oz (+0.2624 / +0.200) stays strong, so the
largest undirected component has 1 edge (p 0.3506). The mechanism was pre-stated, so this is an explained exception.

### Interpretation check

- **Per subject.** S03 and S04 carry the graph results: 16 and 18 of 20 cells are A-NBS, with mean largest components of
  38.8 % and 32.1 %. S05 is intermediate (8/20, 12.1 %). It is led by coherence at 24 Hz (57.1 %*) and wPLI at
  8.57 Hz (39.3 %*), and PLV is near zero except at 24 Hz. S01 and S02 have no graph effect: 1/40 A-NBS cells, which is
  chance level. S01's single cell, wPLI at 10.91 Hz, is an alpha frequency and S01 is 1 SD from the responder cut, so it
  is not read as a responder-like effect. S05's weak graphs, despite 98.79 % accuracy, mean that classifier accuracy does
  not predict graph size beyond the responder split. This is reported per subject, not as a group mean.
- **Criteria separate (R7).** A-FDR, A-NBS and B are reported as three criteria with their own counts:
  48 / 43 / 32 cells at 1000, with A-FDR ∧ B 27, A-NBS ∧ B 26 and A-FDR ∧ A-NBS 39. All 17 flipped cells are inconclusive.
- **One-tailed cohort NBS.** Decreases (stimulus < baseline, for example alpha suppression at 104/105) are not tested
  (N3). Small graphs at 10.91 and 8.57 Hz are therefore not evidence of "no coupling change".
- **Pairwise pattern, exploratory.** NBS+ cells are more frequent in the non-responders: 19 of 60 subject × pair cells
  (coherence 7, plv 6, wpli 6) against 9 of 90 in the responders (1, 8, 0) (`05_pairwise_p1000.log`). In addition,
  26 of the 28 NBS+ cells involve 10.91 or 8.57 Hz, against a base rate of 35/50 pairs (expected 19.6). I computed this
  from the tests CSVs with `freq < 12`. The test is centred (C1), it uses a single permutation count (C3), and 5 of the
  28 are borderline. The reading allowed is: "the per-edge excess over the exchange null concentrates on pairs with an
  alpha-band frequency, mostly in S01/S02". It must not be read as "non-responders have more frequency-specific
  connectivity", and not as Δa ≠ Δb. Alpha-state variation between trials is a plausible, untested explanation.
- **Leakage / fitting.** Not applicable: there is no classifier, and the pseudo-z uses only the permutation null. The
  responders come from classifier accuracy only (PF-21).
- **Cosmetic log label.** The pairwise group lines print "mean NBS largest component … of 28 edges" for groups that mix
  21- and 28-edge subjects, and the header prints "(21 edges …)". The report quotes per-subject % instead (C-2).

### Binding items for the scribe (S1–S9)

- S1. Quote counts from `11_check_cohort.txt`, `12_directions.txt` and `10_check_pairwise.txt`, and the tables above,
  with their paths. Sizes go in % only (R2).
- S2. Apply the F1 labels (11 BH-resolution-limited, 3 Monte Carlo) and the F2 labels (6 threshold-boundary, 0 p-resolution). All flips are inconclusive.
- S3. P2 is stated as refuted at 1000 permutations, with the 9/4 decomposition. Avoid "NBS is more sensitive".
- S4. Put the PDC denominators and the symmetrization caveat beside every PDC count. Give the S04 pdc 102 cancellation example.
- S5. Use the R3 pairwise wording verbatim, the R4 tables above with my command, and the R5 borderline labels.
  Pairwise results are worded as "excess beyond the per-edge exchange-null centre", never "the frequencies differ".
- S6. Write "first pairwise run on the continuous build (fs 256, OO)". Do not compare it with P14 as a re-run.
- S7. Quote the 1.0 s and 2.0 s accuracy of every subject from the v2cont CSV. Note that S01 is 1.0 SD below the cut.
- S8. The cohort NBS is upper-tailed only (P7/N3).
- S9. Cite the original NBS paper only if it is opened in that run (R10).

### Deviations (for decisions.md)

- **D-1.** Acceptance is met: NBS unit tests, cohort tables with FDR and NBS, and the graph-size and sweep tables. The
  report item is pending with the scribe under S1–S9. R-16 has no numeric target. V0–V8 are met (06_verify.md).
- **D-2.** A-priori P2 (A-NBS ≥ A-FDR) is refuted at 1000 permutations: 43 vs 48. Cause: BH at 1000 admits 1- or 2-edge
  FDR results that are impossible at 200, and focal 1- or 2-edge components do not beat the NBS null maximum
  (9 FDR+/NBS− vs 4 FDR−/NBS+). The reviewer's basis conflated supra-threshold with significant. Recorded, not tuned.
- **D-3.** The single P3 exception, S04 pdc 102 (5 directed FDR edges, NBS size 1, p 0.3506), is explained by
  opposite-direction cancellation in the PDC symmetrization (O1↔Oz +0.2255/−0.2229; Oz↔PO3 +0.1123/−0.0641). This was a
  pre-stated mechanism, but it is not one of the two P3-listed exceptions.
- **D-4.** A-priori P6 is partly refuted. Symmetrized PDC graphs are smaller than coherence (12.1 vs 26.3 %) and wPLI
  (21.3 %), but not smaller than PLV (10.1 %): PDC is larger than PLV in 15/25 subject × frequency cells. Recorded.
- **D-5.** The pairwise `p_mag_centred` agreement table (rule R4) is not required for acceptance. The reviewer computed
  it by joining `<m>_pairwise_null_p18_nbs.csv`. NBS agrees with `p_mag_centred` in 46/44/47 of 50 cells and with
  `p_mag` in 41/38/45, and in 15 of the 17 P18 off-centre cells it sides with the centred p (P8 met). The P14 13-cell
  set comes from the legacy fs-250 source and is not reused.
- **D-6.** P18's pairwise run is the first on the continuous build (fs 256; S02/S05 with 8 channels). Its p_mag differs
  from P14's legacy run, and it is reported as a new data source (R9). The concentration of NBS+ cells on
  alpha-frequency pairs in S01/S02 (26/28 involve 10.91 or 8.57 Hz, vs 19.6 expected) is exploratory: single
  permutation count, 5 borderline cells.

### Carry-forwards

- **C-1.** connectivity-stats: write `p_mag_centred` (and the null centre) into `<m>_pairwise_tests_*.csv`, or print the
  NBS × `p_mag_centred` table in the pairwise summary, so the verifier does not need a join.
- **C-2.** connectivity-stats: the pairwise group lines and header print edge counts ("of 28 edges", "(21 edges …)") for
  mixed 7/8-channel cohorts. Report the mean largest component as % of each subject's possible edges.
- **C-3.** connectivity-stats: add `nbs_max_size` from both runs to the cohort flips file (pre-run N1), so F2 needs no join.
- **C-4.** Open option: a lower-tailed cohort NBS (stimulus < baseline) for the alpha frequencies (pre-run N3; P7).
- **C-5.** The pairwise test has only a 1000-permutation run on the continuous build. Any later phase that builds on
  pairwise NBS, p_mag or p_pat claims needs a second permutation count (p500) before applying the R7 flip rule (pre-run C3).
- **C-6.** FDR vs NBS comparisons must be read at a stated permutation count. At 200 permutations BH cannot return
  1–(k−1) edges (k = 3, 3, 5, 6 for m = 21, 28, 42, 56), so cross-count comparisons of A-FDR mix resolution with sensitivity.

## Sources spot-check

No external source was cited by the builder, the tester or the verifier, and none was opened in this review (R10).
`reference_access.log` has no P18 entry (06_verify.md: 40 lines before and after the run). R11: PASS.
Privacy scan of `git diff main..HEAD` and of the branch commit messages, built from fragments: 0 and 0 hits. No data,
recording or local-tooling paths are in `git diff --name-only main..HEAD` (0).

## Questions
