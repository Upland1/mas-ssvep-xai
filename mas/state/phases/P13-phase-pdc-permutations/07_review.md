# P13 · 07 · Scientific review

Status: READY (results review Round 2: APPROVE)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Audited: `git diff main..HEAD -- src scripts tests` at bb486a9 (7 code files, 2 test files), 00, 02, 03, 04, decisions.md rows 114–118, mas/state/reports/P12.md, RULES.md, 03_ROADMAP P13, 02_REQUIREMENTS §6, 04_REFERENCE R-12 and the tolerance table, 05_PITFALLS PF-03, PF-17–PF-20.
Own checks (synthetic or arithmetic only, no recordings read): `.venv/bin/python -m pytest tests/test_p13_connectivity.py tests/test_p13_known_answer.py -o addopts="" -q` → `64 passed in 6.37s`. Other commands are quoted where used.

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no classifier or CV in this phase |
| R2 Fit only in-fold | N/A | no train/test split; the MVAR fit is the statistic of each (permuted) group, `src/features/connectivity/mvar_pdc.py:69-73` |
| R3 for phase (enforced from P13) | PASS | phase from the band-averaged complex CSD, `src/features/connectivity/phase_connectivity.py:39-42` (`csd`, `nperseg=min(T,128)`, Welch segments inside each window); PLV/wPLI formulas `:48`, `:53-57` match roadmap task 1. `grep -rn "hilbert\|filtfilt"` over src/scripts finds Hilbert only in `scripts/connectivity/diagnostics/demo_hilbert_edges.py` (plus the pre-existing legacy FBCSP/FBCCA filtfilt, not touched). Edge-immunity tests `tests/test_p13_known_answer.py:172`, mutant M3 killed |
| R3 sub-band filtering, fs 250 | LEGACY (by design) | fs-250 axis `scripts/connectivity/analysis/analyze_connectivity_cohort.py:88`, labelled in `SOURCE` `:59` and the details CSV; PF-04 era row |
| R4 Small-sample bias | PASS + CONCERN C1 | coherence is the concatenated estimator recomputed on every permuted group (`permutation.py:95`, `connectivity_extraction.py:100-103`); see C1 (junctions) |
| R5 Shared quality decision | LEGACY (by design) | one P07 gate per subject shared by all methods and conditions, every threshold explicit (`**GATE`, `connectivity_extraction.py` `gate_selection`; `analyze_connectivity_cohort.py:119`); `load_subject(quality_mode="shared")` is P16 |
| R6 Index layouts verified | PASS | strided `weights[lag::p, :].T` `mvar_pdc.py:50`; channel-major design `:29-32`; PDC column normalisation over the source column `:63` then zero diagonal `:65`, `[i, j]` = j → i. Proven by `test_mvar_row_layout_channel_major_with_known_weights`, `test_pdc_hand_computed_orientation_and_column_normalisation` (`tests/test_p13_known_answer.py:102`, hand formula, 1e-9), mutants M1, M2a, M2b killed. Contiguous slicing exists only in `demo_mvar_slicing.py:63-66` (allowed, diagnostic) |
| R7 Honest statistics (enforced from P13) | PASS | trial-level split with observed sizes `permutation.py:56-82` and `:151-156` (`n_first = ns`); +1 pseudo-count `:160-165`; global p and FDR count kept in separate fields `:173-177`, separate summary columns and console lines `analyze_connectivity_cohort.py:134-140`, `:165-176`; flip list `:190-202`. Window-level first run labelled `permutation_unit = window` `:120`, `permutation.py:178` → LEGACY (by design) for the R7 first-run row. Gap in the run commands for task 6: F1 |
| R8 Smoothing | N/A | no smoothing |
| R9 Per subject with data source | PASS | per-subject rows; `SOURCE`, fs, window counts, `trial_ids_approximate` in `..._details.csv` (`analyze_connectivity_cohort.py:141-147`); console prints source and APPROXIMATE flag `:115-123` |
| R10 Sources | PASS | 03 and 04 cite roadmap, §6, R-12, PF rows; BH 1995 DOI is correct (10.1111/j.2517-6161.1995.tb02031.x) |
| R10 Copied lines | N/A | no borrowed code declared; nothing resembling copied blocks |
| R11 Reference | PASS | no consultation listed in 03/04; `mas/state/scratch/reference_access.log` has no entry after 2026-10-26T12:05:15 (P11/P12 era); P13 commits start 15:26:34 |
| Golden rule 3 | PASS | Hilbert and contiguous slicing reachable in kept demos; window-level permutations behind `--permutation-unit window`; aligned estimator labelled DIAGNOSTIC `analyze_connectivity_cohort.py:82-83`, `:230-231` |
| Tests cover every change; fail on the historical bug | PASS | 27 + 37 tests; mutants M1 (PF-17), M3 (PF-18), M4a/M4b/M5/M8 (PF-19), M7 (PF-20), M9 (PF-03), M6 (pseudo-count) killed (04_tests.md) |
| Changes match 02_plan.md and the roadmap | FAIL (F1) | code matches the settled points; the plan's run list cannot produce the task-6 acceptance row (window vs trial comparison), and the builder-documented overwrite of `connectivity_cohort_flips.csv` (`analyze_connectivity_cohort.py:213`) makes the result order-dependent |
| No data, recordings, local tooling files or vendor names | PASS | `git diff --name-only main..HEAD` has no data/tooling paths; fragment-built vendor scan over the diff, `git log main..HEAD` messages and `git grep HEAD -- mas/state src scripts tests`: no hit (only the pre-existing recording-suffix mentions in blockers B002/B005) |

### Checks asked by the orchestrator

**PF-17 / PDC orientation.** PASS (R6 row). The PDC direction test drives a single channel and checks `[i, j]` = j → i with a hand formula, so a transposed or row-normalised PDC fails.

**PF-18.** PASS (R3 row). The reported PLV/wPLI never see time-domain filtering. Note: the PLV/wPLI fast path computes the per-window CSD once for the pooled windows (`phase_connectivity.py:85-88`, `permutation.py:139-142`). This is valid only because the per-window CSD does not depend on the grouping, and `test_fast_path_equals_direct_call` proves equality.

**PF-19 and the "at most one split trial" rule with the offset baseline ids.** PASS. The ids come from `build_trial_ids` on the full pre-gate labels (`connectivity_extraction.py:257`), so they are already globally unique. The offset at `permutation.py:138` maps the baseline ids to values above `max(stim)`, keeps them distinct from each other, and cannot create a trial shared by the two pools. The greedy fill adds whole trials and splits at most the first trial that does not fit, then stops (`:66-78`). The sizes are exact because `n_first = ns`. Tests cover 8 + 4 parametrised layouts × 40/30 seeds and the "no split when possible" case. One check of my own: on an S03-like layout (8 stimulus trials × 5 + 40 baseline trials × 2, `n_first` 40) the null groups are mixtures of 5- and 2-window trials. That is the expected trial-level exchangeability, and C1 depends on it. With approximate ids (S02/S04, PF-03), a short "trial" can merge or split real trials. The null is still trial-like, and the flag is in the details CSV and the console.

**p-value pseudo-count.** PASS. `p = (1 + #{null ≥ obs}) / (n + 1)`, so the minimum is 1/201 = 0.004975 at 200 and 1/101 at 100 permutations. M6 was killed.

**BH on one-tailed edge p (builder choice 1).** PASS, judged on the text before any real number. The roadmap (task 3) computes one- and two-tailed edge p and does not say which feeds BH, and R7 is silent too. R-12 labels its global p "one-tailed (stimulus − matched baseline)", and an "effect" there is an increase. A two-tailed BH would count decreases as FDR edges, so the R-12 totals would mix directions. One-tailed (stimulus > baseline) is therefore the natural reading. Pre-committed: the choice is frozen. The results review grades R-12 totals on the one-tailed BH only and does not switch tails after seeing numbers (golden rule 5). The report must state "BH-FDR over one-tailed (stimulus > baseline) edge p; npz `p_c` are one-tailed". The builder's S03 smoke per-cell agreement (20/21/15/0/8 vs 20/21/16/0/8) is consistent with this, but my judgement does not rest on it.
BH discreteness, from `python -c` (`ceil(pmin·m/0.05)`): at 200 permutations, a frequency with 21 edges can have 0 FDR edges or at least 3, never 1 or 2. At 100 permutations the minimum is 5. For PDC's 42 edges it is 5 (200) and 9 (100). Consequences: (i) R-12's per-cell counts of 3 (S02 wPLI 20 Hz, S03 wPLI 15/10.91 Hz, S05 coh 20 Hz) are minimum non-zero counts. (ii) Some criterion-A flips between trial100 and trial200 are pure resolution artefacts: a cell with 3–4 edges at 200 cannot have any at 100. The flip list still labels them inconclusive, and the report should name the mechanism.

**PF-20.** PASS. `significant_uncorrected` (B, global p < α) and `fdr_backed` (A, ≥ 1 FDR edge) are separate columns. The console prints (A) and (B) on separate lists per frequency. Two tests construct both kinds of disagreement, and M7 was killed. R-12 itself has both kinds: S02 wPLI 20 Hz is A without B (3 edges, p 0.144), and S05 wPLI 24 Hz is B without A (p 0.015, 0 edges). The report must keep them apart.

**PF-03.** PASS. Ids are built on the pre-gate labels with 202 included in the walk, then the condition selection, then the gate mask `valid_mask` (`connectivity_extraction.py:257`, `permutation.py:209`). The test uses a gate-rejected window, and M9 was killed.

**Seeds and determinism.** PASS. The cell seed is `derive_seed(42, subject, method, condition)` (`permutation.py:50-53`, `:223`). Permutation i uses the i-th word of `SeedSequence(cell).generate_state(n)` (`:149`), so the result is independent of `n_jobs` (test, n_jobs 1 vs 2, exact). Note: I checked `generate_state(100)` against `generate_state(200)[:100]` and they are equal (`python -c`, `prefix True`). The trial100 null is therefore the first half of the trial200 null, so the 100-vs-200 flip list measures Monte Carlo resolution with shared draws, not two independent runs. This is acceptable and is how a fixed `random_state` behaves, but the report must say so. The window, trial and aligned runs share cell seeds, but their splits differ in kind, so this only matters for the aligned-vs-concatenated pairing, where it is intended (identical splits).

**42-edge PDC reading.** PASS with a corrected rationale. "21/28" in the roadmap is most naturally C(7,2) = 21 and C(8,2) = 28, the 7- and 8-channel undirected counts, not a directed count, because 28 ≠ 42. The text therefore does not fix the directed case. Each direction is a separate hypothesis for a directed measure, so 42 off-diagonal entries is the methodologically sound choice. A directed matrix read as an upper triangle would test only j → i with j > i. R-12 has no PDC row, so the choice cannot affect acceptance. Required wording for the report: "PDC: 42 directed edges, our choice (roadmap gives 21/28 for 7/8 channels, undirected)". No R11 consultation is needed.

**C1: junction effect in the permutation null (P12 D-2). CONCERN, handled by the diagnostic.** Junctions affect only coherence: PLV/wPLI use per-window CSDs, and MVAR rows never cross windows (`mvar_pdc.py:29`). For coherence (`nperseg` 256, 50 % overlap) I computed the fraction of Welch segments straddling a trial junction with `_trial_permutation_split` on the S03-like layout above, over 500 seeds: observed stimulus 0.089, observed baseline 0.245 (gap −0.157); trial-level null first group 0.196, second 0.197 (gap −0.001); window-level null 0.394 / 0.296. The trial-level null is therefore balanced, and the observed split is not. If junction steps raise coherence (P12 synthetic regime), the observed difference is shifted NEGATIVE relative to the null. The one-tailed (stimulus > baseline) p is then conservative, and any lower-tail reading (P12 D-3 alpha suppression) is anti-conservative. The window-level null has its own junction imbalance (+0.098, opposite sign), which is one more reason it is only the legacy record. The builder's S03 smoke has the aligned estimator less significant than the concatenated one at 8.57 Hz (0.697 vs 0.104), which is the opposite of the junction prediction for the upper tail. So, as at P12, "estimator-sensitive" is the label, not "junction-biased".

**Pre-committed treatment of estimator-dependent cells (results review, cannot be moved):**
- E1. Reported numbers and every R-12 comparison use the concatenated estimator (R4, roadmap). The aligned run is a diagnostic and is never graded against R-12. Its S03 FDR total (smoke 48) is not tested against the S03 window.
- E2. An S03 coherence cell (frequency) is **estimator-dependent** if criterion A (≥ 1 FDR edge) or B (p < 0.05) differs between the concatenated trial200 and the aligned_S03 run.
- E3. Label an estimator-dependent cell "junction-consistent" only if the aligned estimator is the MORE significant one (lower p or more FDR edges) in the stimulus > baseline direction. Otherwise label it "estimator-sensitive (not junction-biased)".
- E4. No qualitative claim may rest on an estimator-dependent cell. The report states it as inconclusive with both values. If S03 24 Hz were estimator-dependent, it counts as a 24 Hz switch to explain (A3 below).
- E5. Any coherence statement that stimulus is BELOW baseline (alpha suppression, D-3) counts only if it holds with the aligned estimator too (S03 only). For S01, S02, S04 and S05 such statements are labelled "not cross-checked for junction effects".

**Alpha diagnostic CSV.** PASS on content (matched-baseline mean, stimulus mean, difference, one-tailed p, unit; `analyze_connectivity_cohort.py:150-155`). The cross-subject Spearman is printed as descriptive (`:179-187`). Note N2: the suppression hypothesis needs the LOWER tail. With continuous statistics (no ties), `p_lower = 1 − p_one + 1/(n+1)` exactly, and the results review derives it with a shown command unless N2 is adopted. The relation baseline-level vs difference at n = 5 is descriptive: no "supports" claim, only "consistent with / not consistent with" per subject.

**Schemas.** PASS. `SUMMARY_COLUMNS` (`analyze_connectivity_cohort.py:51-53`) matches 02_REQUIREMENTS §6 (pre-P18) in name and order. The npz keys are `channels_kept`, `stim_c`, `base_c`, `diff_c`, `p_c`, `fdr_c` (`:131`, `:148-149`). The extras go to the `_details.csv` sidecar. The test hard-codes the §6 list (`tests/test_p13_known_answer.py:522`).

**Verifier commands vs acceptance.** FAIL (F1). Commands 1–5 and 7 produce the demos, window200, trial100, trial200 (final, unsuffixed) and aligned_S03. Command 6 produces the trial100-vs-final flips. Nothing produces the task-6 row "window vs trial p-value comparison printed". `--compare window200 ""` is not in the list, and if it were run after command 6 it would overwrite the required flips file (`analyze_connectivity_cohort.py:213`). Also, `compare_runs` uses an inner merge (`:195`), so if one summary lacks rows (for example a partial re-run with `--subjects`), the comparison silently shrinks. An empty flips file written by `.assign` has no rows that name the compared pair (P11 lesson: same-name outputs).

**Demo numbers versus the roadmap.** Accept as synthetic-system dependence. No action beyond reporting both numbers.
- MVAR: the contiguous slices of a channel-major `weights` are a permutation of the same C·p·C estimated entries. So `‖P(Â) − A‖ / ‖A‖ ≈ √(2(1 − ρ))`, which is 141 % for uncorrelated entries. 150–200 % needs a negatively correlated permutation (ρ ≤ −0.125), which depends on the system. Five seeds of the builder's demo system (`python -c`, `demo_mvar_slicing.run(s)`, s = 0–4) give strided 6.6/7.2/5.4/5.8/5.6 % and contiguous 129.7/139.1/135.2/132.1/133.7 %. That is stable, near the √2 expectation, and 18–26× the strided error. The bug's signature (≥ 100 % vs ≤ 15 %) is unambiguous.
- CSD PLV 1.0000 → 0.9999 vs the roadmap's 0.998 → 0.998: the level depends on the noise, and the claim being tested is invariance under edge corruption (Δ ≤ 0.005), which holds.
- Hilbert envelope 0.39–0.76 (first 15 samples) and 0.02–0.17 (last 15) vs "5–70 %": the overall span 2–76 % is the same phenomenon, and the upper end exceeds 70 % slightly.
- The report must print the roadmap numbers beside ours and say "system-dependent; qualitative claim reproduced". It must not write "reproduces ~150–200 %".

### Pre-committed acceptance windows for R-12 (trial200 = the unsuffixed final run, concatenated coherence, one-tailed BH; fixed now, not movable by the results review)

Tolerance: "same qualitative pattern; FDR-edge totals per subject within ±25 % or ±5 edges" (04_REFERENCE tolerance table). The half-width is max(0.25·R, 5), integers inclusive. From `python -c` (`h=max(0.25*r,5); ceil(r-h), floor(r+h)`):

| Method | S01 (R 0) | S02 | S03 | S04 | S05 |
|---|---|---|---|---|---|
| coherence total | 0–5 | 0–5 (R 0) | 49–81 (R 65) | 39–63 (R 51) | 10–20 (R 15) |
| wPLI total | 0–5 | 0–8 (R 3) | 29–47 (R 38) | 25–41 (R 33) | 13–23 (R 18) |

- A1 Synthetic: the full suite passes on the clean checkout. Both demos exit 0: strided ≤ 15 % and contiguous ≥ 100 %; CSD ΔPLV ≤ 0.005 and Hilbert edge envelope < 80 %.
- A2 FDR totals: all 10 cells inside the table. One cell outside is "not within tolerance". It can be accepted only as a recorded deviation with a mechanism shown by an output (flip-list membership of the cells that make it up, approximate ids S02/S04 with the gate counts, or E2 estimator dependence for S03 coherence). No re-run with other seeds or permutation counts may replace the final run.
- A3 24 Hz pattern (criterion B, global p < 0.05): all six cells S03–S05 × {coherence, wPLI} at 24 Hz must be significant, and S01/S02 at 24 Hz must be non-significant in both methods (R-12: 1.000/1.000/1.000/0.323). Any 24 Hz cell whose B verdict differs from R-12 is a "24 Hz switch", which is in the failure column of the tolerance table. It must be explained by output evidence (in the flip list, E2, or approximate ids). "Monte Carlo noise" alone is not accepted for a reference p ≤ 0.015 (S03–S05 all) unless the cell is in the flip list. Criterion-A changes at 24 Hz (for example S05 wPLI gaining FDR edges where R-12 has 0) are reported and explained, but do not by themselves fail A3.
- A4 "Only 24 Hz": no other frequency has p < 0.05 in all of S03–S05 in BOTH coherence and wPLI. This joint reading is forced: in R-12 itself, wPLI alone is significant in all three at 10.91 Hz (0.015/0.015/0.005) and 8.57 Hz (0.005/0.025/0.010). Frequencies that meet this for one method only are reported descriptively.
- A5 S01/S02 "null on essentially everything": FDR totals inside the table, and at most 1 of each subject's 10 coherence + wPLI cells with p < 0.05 (R-12 has 0), never at 24 Hz (A3).
- A6 Flips: the trial100-vs-final flips CSV exists, and every listed cell is labelled inconclusive in the report. The report names the flips that come only from BH resolution (minimum non-zero count 5 at 100 vs 3 at 200) and says the two nulls share their first 100 draws. A count of flips is not graded.
- A7 Task 6: window200 summary with `permutation_unit = window` in every row. The window-vs-trial comparison is produced by the plan command (after F1). Descriptive expectation (PF-19): window-level p no larger than trial-level at most cells. This is not graded, and the C1 junction imbalance of the window null is stated.
- A8 PLV and PDC have no reference values. They are reported descriptively and labelled "no reference". PDC uses 42 directed edges.

### Non-blocking notes

- N1. `p_two_tailed` (`permutation.py:161`, `:165`) compares |null| with |obs| around 0. The null is not centred at 0, because the group sizes differ and the estimator bias depends on size. Centre on the null mean, or keep it out of any claim. It is only in the details CSV.
- N2. Recommended in the same round as fix 1: add `p_lower_tailed = (1 + #{null ≤ obs}) / (n + 1)` to the result dict and the alpha CSV (P12 D-3 suppression test), with a reversed planted-effect test. If not adopted, the results review uses `1 − p_one + 1/(n+1)` (exact without ties) and says so.
- N3. 03_changes "PDC 42 edges: reading of 21/28" and decisions.md P13 point 2: the rationale should read "our choice for the directed case; 21/28 = 7/8 channels undirected" (see above).
- N4. The S03 smoke numbers in 03_changes are labelled SMOKE and are not reportable. The report must use only the verifier's run.

Verdict: FAIL

### Required fixes

1. connectivity-stats (R7, R9; `scripts/connectivity/analysis/analyze_connectivity_cohort.py:190-219`): make `--compare` order-independent.
   - The pair (`trial100`, `""`) keeps writing `reports/connectivity_cohort_flips.csv`. Any other pair writes `reports/connectivity_cohort_flips_<a>_vs_<b>.csv`, with `final` for `""`.
   - Print the compared suffixes and the number of compared cells in every case.
   - Raise if the two summaries do not have the same (subject, method, condition) key set.
   - Add a test: two compares in either order leave both files with their own pairs, and a missing row raises.
2. orchestrator (task 6 acceptance; `02_plan.md` "Run commands"): add `.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --compare window200 ""` after the final trial200 run. Add the pre-committed windows A1–A8 above to the acceptance table by reference.

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Pre-run audit — Round 2

Audited: `git diff 934cc2f..089ebda -- src scripts tests mas/state` (fix commits b8e5ccc, 643f0f9, 628759d, e80cfad; tester round 9d547b0, 6c2f935). Own check: `.venv/bin/python -m pytest tests/test_p13_connectivity.py tests/test_p13_known_answer.py -o addopts="" -q` gives `73 passed in 6.61s`. The tester reports a full-suite result of `796 passed, 21 warnings in 361.15s`.

| Item | Result | Evidence |
|---|---|---|
| Fix 1: order-independent `--compare` | PASS | `flips_path` in `scripts/connectivity/analysis/analyze_connectivity_cohort.py` keeps `connectivity_cohort_flips.csv` only for (`trial100`, `""`); every other pair writes `connectivity_cohort_flips_<a>_vs_<b>.csv` (`final` for `""`). The console prints both suffixes and the number of cells compared. `compare_runs` raises when the (subject, method, condition) sets differ, and `validate="one_to_one"` also rejects duplicate rows. Tests: builder `test_compare_is_order_independent` (both orders) and `test_compare_raises_on_missing_rows`; tester `test_compare_writes_distinct_files_in_both_orders_with_hand_flips` (hand-predicted flips, no overwrite of the required file) and `..._missing_row_in_either_direction`. Mutants R1 (single file name) and R2 (row check disabled) were killed. |
| Fix 2: plan | PASS | `02_plan.md` adds `--compare window200 ""` after the final trial200 run. The task-6 acceptance row names `connectivity_cohort_flips_window200_vs_final.csv`, which matches `flips_path("window200", "")`. The acceptance table binds to A1–A8, the FDR-total table and E1–E5 of Round 1 (934cc2f), and they prevail where more specific. The windows are unchanged. |
| N2: lower tail | PASS | `p_low = (1 + #{null ≤ obs}) / (n + 1)` in `src/features/connectivity/permutation.py`, returned as `p_lower_tailed` and written to the alpha CSV. The tester's hand-count test with ties (6/11, 9/11, 7/11) kills the `1 − p_one` mutant R3. The results review therefore uses the column directly, so the Round 1 fallback formula is no longer needed. |
| N3: rationale | PASS | `03_changes_connectivity-stats.md:140` and the new P13 row in decisions.md state that 21/28 means 7/8 channels undirected and that 42 directed edges is our own choice. The original settled-point row is kept (append-only). |
| N1: two-tailed p centred on 0 | open, non-blocking | Unchanged. It is only in the details CSV, and no acceptance criterion or claim may use `p_two_tailed`. |
| Scope | PASS | The diff touches only the compare path, the lower-tail p and tests. No change to estimators, splits, seeds or BH, so the Round 1 rule verdicts stand. The vendor and trailer scan of the new commits and this file finds nothing (command below the table). |

Scan: `git log 934cc2f..HEAD --format=%B` and `git diff 934cc2f..HEAD`, with a fragment-built pattern that also covers the trailer token, give no hit.

Carried into the results review unchanged: A1–A8, the FDR windows (coherence 0–5 / 0–5 / 49–81 / 39–63 / 10–20; wPLI 0–5 / 0–8 / 29–47 / 25–41 / 13–23), E1–E5, BH on one-tailed edge p, and nested 100/200 nulls stated in the report. For coherence suppression readings (E5), `p_lower_tailed` is the test statistic.

Verdict: PASS

## Results review — Round 1

Read: 05_run.md (139f5f4), 06_verify.md (57e5fbd, verifier FAIL on A2), run at 7f6cabb (15 min 05 s, all 8 commands exit 0, one execution each), the CSVs and npz under `reports/`, and `reports/logs/P13/*.log`. My own re-derivations are read-only `python -c` commands on those files.
- FDR totals per method × subject from `reports/connectivity_cohort_summary.csv` reproduce 06_verify exactly: coherence 0/0/64/49/12, wPLI 4/0/42/28/5, PLV 0/0/44/23/0, PDC 0/5/10/26/5.
- Window-level p ≤ trial-level p in 71 of 100 cells.
- `p_lower_tailed` < 0.05 in 7 of the 40 alpha-diagnostic rows.

Code ran at the audited state: `git diff --stat 089ebda 7f6cabb -- src scripts tests configs` is empty, because 7f6cabb only records the Round 2 audit. The legacy inputs are unchanged (15 sha256 identical before and after, 05_run.md). As expected for two subjects with all 320 windows and identical condition order, the S01 and S05 `y_labels.npy` hashes are equal; the `X_time_windows` hashes differ.

### Pre-committed criteria (fixed in Round 1)

| Criterion | Result | Reading |
|---|---|---|
| A1 synthetic + demos | met | suite `796 passed`; MVAR strided 6.6 % / contiguous 129.7 %; CSD PLV 1.0000 → 0.9999; Hilbert envelope 39–76 % (first 15 samples) and 2–17 % (last 15). The report prints the roadmap values beside these and calls the demo magnitudes system-dependent. |
| A2 FDR totals | **not met: 9/10** | wPLI S05 = 5, window 13–23 (R-12 18). See "A2 miss" below. |
| A3 24 Hz pattern | met | S03–S05 coherence 0.005/0.005/0.005, wPLI 0.005/0.005/0.040. S01/S02 are non-significant in both methods (coherence 1.000/1.000, wPLI 0.995/0.318). No 24 Hz switch. S05 wPLI 24 Hz has 0 FDR edges, as in R-12. Its p 0.040 is the weakest of the six; it is not in the trial100 flip list, and it moved 0.005 → 0.040 between window and trial level. |
| A4 only 24 Hz (joint) | met | the joint set is {24 Hz}. wPLI alone is significant in all of S03–S05 at 10.91 and 8.57 Hz too (descriptive, same as R-12). |
| A5 S01/S02 null | met | 0 cells with p < 0.05 among each subject's 10 coherence + wPLI cells. FDR totals 0/4 (S01) and 0/0 (S02) are inside their windows. S01 wPLI 10.91 Hz has 4 FDR edges with p 0.154. That is criterion A without B (PF-20), and the cell is in the trial100 flip list, so it is inconclusive. |
| A6 flips | met | 11 cells in `connectivity_cohort_flips.csv`, all inconclusive. 10 are criterion-A flips with 0 edges at 100 permutations and 4–6 at 200, at or below twice the BH minimum. They come from BH resolution on nested nulls. The one criterion-B flip is S03 wPLI 15 Hz, p 0.069 → 0.050 (10/201 < 0.05; R-12 0.065). |
| A7 task 6 | met | window200 is labelled `window` in all 100 rows. The comparison file lists 14 cells. Window-level p ≤ trial-level p in 71/100 cells, as PF-19 predicts (a null that is too narrow). The window null also has a junction imbalance (C1), so the window-vs-trial differences in coherence are not attributable to the unit alone. |
| A8 PLV/PDC | met | reported, no reference. PDC has 42 edges, and its FDR counts sit at the BH minimum (5) in 8 of the 9 non-zero cells (the 9th has 6), so they are near-resolution. |
| E1–E5 | applied | Only S03 coherence 8.57 Hz is estimator-dependent: criterion A gives 8 edges concatenated vs 0 aligned, with p 0.104 vs 0.697. The aligned estimator is the less significant one, so the label is "estimator-sensitive (not junction-biased)" (E3), and the cell is inconclusive (E4). R-12 also has 8 edges at this cell, so its agreement with R-12 cannot be used as support either. 24 Hz is not estimator-dependent. |

### A2 miss: S05 wPLI (5 vs 13–23)

The S05 wPLI cells (`connectivity_cohort_summary.csv`):

| Cell | p | Uncorrected edges | FDR edges | R-12 (p, FDR) |
|---|---|---|---|---|
| 24 Hz | 0.040 | 7 | 0 | 0.015, 0 |
| 20 Hz | 0.065 | 1 | 0 | 0.070, 0 |
| 15 Hz | 0.368 | 0 | 0 | 0.398, 0 |
| 10.91 Hz | 0.015 | 13 | 0 | 0.005, 13 |
| 8.57 Hz | 0.010 | 9 | 5 | 0.010, 5 |

The whole deficit is the 10.91 Hz cell (13 → 0). From `reports/connectivity_edges/S05_wpli.npz`, `p_104`:
- The sorted edge p begin 0.005, 0.010, 0.0199, 0.0199, 0.0249, 0.0299 (×4), 0.0348, 0.0398, 0.0398, 0.0448.
- The smallest ratio p_(k) / (0.05·k/21) is 1.393, at k = 9 (0.0299 vs 0.0214). BH rejects nothing.
- For all 13 edges to pass, p_(13) must be ≤ 0.0310, which is 6/201. The four largest of the 13 sit at 7/201 to 9/201 (6–8 null exceedances each).
- At p ≈ 0.035 and 200 permutations, the binomial SD of an exceedance count is √(200·0.035·0.965) = 2.6. The edges share the same null draws, so they move together. This is exactly the BH all-or-nothing block the orchestrator describes.

This is a plausible mechanism, and the npz shows it. But it is not one of the three mechanisms A2 lists, and golden rule 5 forbids adding one after the numbers. Whether a different Monte Carlo draw of the same procedure reaches the reference is cheap to measure (wPLI uses the per-window CSD fast path, about 0.3 s per subject). So I require the diagnostic below and do not sign on the present evidence.
- Ruled out by the outputs: approximate ids (S05 ids are exact, 280/280 clean, 7 channels), estimator dependence (E2 does not apply to wPLI), and data source (S05 OO, the same session as the reference; R-6 S05 was reproduced at P11).

#### Pre-committed diagnostic DIAG-A2 (fixed now, before any run; reported numbers stay at random_state 42)

The verifier runs these from the clean checkout at the commit that records this review, with no code change, once each, logging to `reports/logs/P13/diagA2_rs<B>.log`:

```bash
for B in 42 1 2 3 4 5; do
  .venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods wpli --subjects S05 --permutations 200 --permutation-unit trial --n-jobs -1 --random-state $B --out-suffix diagA2_rs$B
done
```

Outputs: `reports/connectivity_cohort_summary_diagA2_rs<B>.csv` (+ `_details`, alpha CSV, `connectivity_edges_diagA2_rs<B>/`). None of them touches the final files. For each base B, T_B is the S05 wPLI FDR total over the five conditions, and E_B is the 10.91 Hz FDR count.

Decision rule, applied in this order:
1. **R0 (identity).** The rs42 rows must equal the final S05 wPLI rows of `connectivity_cohort_summary.csv` exactly (p, uncorrected edges, FDR edges per condition). If not, the final run is not reproducible: REJECT, and connectivity-stats investigates determinism before anything else.
2. **R1, "Monte Carlo / BH resolution" → accepted deviation.** At least one of B ∈ {1..5} has T_B ≥ 13 and E_B ≥ 3. Recorded as: "S05 wPLI FDR total 5 at seed 42 is outside 13–23. The deficit is the 10.91 Hz block (13 uncorrected edges at p 0.005–0.045, 0 FDR). Other seed bases of the same procedure give T = [list] and 10.91 Hz = [list], so the count is resolution-limited at 200 permutations, not a method difference." The report then states the 10.91 Hz FDR count as inconclusive, gives the six T_B values, and keeps the reported 5. The results review then APPROVEs, provided nothing else changes.
3. **R2, "systematic" → Sebastian.** All five bases give T_B ≤ 12. In that case the shortfall is not a resolution artefact of one draw: R-12 S05 wPLI is not reproduced within tolerance, and the cause is not established.
   - Consequences: the A2 FAIL stands. The orchestrator opens a blocker to Sebastian with the six T_B and E_B values and the 10.91 Hz edge p, asking whether the original used another permutation count, seed scheme or FDR tail for this cell.
   - An R11 consultation of the original's wPLI/permutation code by connectivity-stats is then allowed: our implementation and test exist, and the result deviates beyond tolerance after one investigation round. It must be listed in a handoff.
   - The phase does not gate until Sebastian decides.

No other cell is re-run, and the six diagnostic values are not averaged into a reported number.

### Interpretation check (binding on the report)

- **Statistics unit.** The final results are trial-level, with 200 permutations, the observed group sizes, BH over one-tailed (stimulus > baseline) edge p within each frequency (21 edges; PDC 42), and no correction across frequencies or methods. Criteria (A) and (B) are reported separately.
- **Per subject.**
  - S01/S02 are null at 24 Hz and essentially everywhere. S01 wPLI 10.91 Hz (A without B) and S02 PDC 24 Hz (5 edges, p 0.015, in the flip list) are inconclusive.
  - S03–S05 show the 24 Hz effect in coherence and wPLI.
  - S03 adds 20 and 15 Hz in coherence/PLV.
  - S04 adds effects at all coherence frequencies (FDR edges 12/11/7/12/7).
  - S05 coherence and PLV have no FDR edges below 24 Hz.
- **Window vs trial.** Window-level FDR totals are mostly higher (coherence 3/0/66/58/15, wPLI 0/3/46/37/20), and 14 cells change verdict, including S05 wPLI 24 Hz (10 edges → 0). This is the PF-19 effect, described as such. It is not evidence for which unit the reference used: window-level S05 wPLI gives 20 in total, inside the window, but with 10 edges at 24 Hz where R-12 has 0 and 3 at 10.91 Hz where R-12 has 13. The per-cell pattern does not match either.
- **Flip list.** 11 cells, inconclusive. The report names BH resolution (minimum non-zero count 3 at 200 and 5 at 100 permutations for 21 edges; 5 and 9 for 42) and states that the 100-permutation null is the first half of the 200-permutation null.
- **Alpha hypotheses (P12 D-3), from `connectivity_alpha_diagnostic.csv` with `p_lower_tailed`:**
  - **Ceiling (S03).** The S03 matched coherence baseline is higher than S04's at 10.91/8.57 Hz (0.6435/0.7390 vs 0.5831/0.6422), and its differences are small (−0.0366/+0.0414 vs +0.1934/+0.1286). This is consistent with a ceiling for coherence in S03. But the cross-subject coherence Spearman rho is only −0.10/−0.30 (n = 5), so there is no cohort-level support. The wPLI rho of −0.90/−0.80 cannot be read as a ceiling either:
    - S03 has the lowest wPLI baselines (0.134/0.107) and the largest wPLI increases (+0.350/+0.466).
    - rho(baseline, stimulus − baseline) is biased negative by construction, because the baseline enters both terms (regression to the mean).
    - So the report must call every rho "descriptive, expected negative under no effect".
  - **Alpha suppression (S03 104).** Not supported. The coherence lower-tail p is 0.219 (concatenated) and 0.368 (aligned), with an observed difference of −0.0366. The wPLI difference is positive (p_lower 0.985).
  - **Unplanned, exploratory.** 7 of 40 lower-tail p are below 0.05 with no correction; about 2 are expected by chance. The strongest are in S05, where stimulus is below baseline in coherence (10.91 Hz p_lower 0.005, 8.57 Hz 0.035) and PLV (0.015, 0.005) while wPLI rises (p_one 0.015, 0.010). PLV is free of junction effects (per-window CSD), whereas the S05 coherence values are "not cross-checked for junction effects" (E5). The report may describe this as an exploratory S05 observation: a drop in zero-lag alpha synchrony during stimulation alongside an increase in lagged coupling. It is not a confirmed hypothesis, and S03 (the subject D-3 named) does not show it.
- **Leakage.** Nothing is fitted across groups. The MVAR and coherence are recomputed for each permuted group, and the shared gate uses no labels beyond the conditions.

### Report requirements (scribe, P13.md)

1. Every number is quoted verbatim with its CSV or log path. Data source: legacy 7-channel windows (P02, OO), fs-250 axis (PF-04), one P07 gate per subject, approximate ids for S02/S04.
2. Per-subject tables for coherence and wPLI (p and FDR per frequency) beside R-12. PLV and PDC go in separate tables labelled "no reference".
3. A2: the S05 wPLI line exactly as decided after DIAG-A2 (R1 wording, or R2 "not reproduced, cause not established, question to Sebastian"). Never "reproduces R-12" for S05 wPLI.
4. Criteria (A) and (B) are named separately everywhere. Cells in the flip list and the E2 cell (S03 coherence 8.57 Hz) are labelled inconclusive, with both values.
5. Methods:
   - BH over one-tailed edge p;
   - nested 100/200 nulls;
   - BH minimum counts;
   - PDC uses 42 directed edges by our choice (21/28 = 7/8 channels undirected);
   - window-level run = legacy R7 first run.
6. Demos: the roadmap and our values side by side, "qualitative claim reproduced, magnitudes system-dependent".
7. Alpha section as in the interpretation check: ceiling consistent for S03 coherence only; suppression not supported for S03; S05 exploratory; rho descriptive and negatively biased by construction.
8. No figures were produced, so P12 D-4 does not apply. If any cross-subject panel is added, it shares one colour limit.
9. Grep the draft for "reproduc" and make each use match the per-criterion verdicts above (P06 lesson).

### Decisions for decisions.md (proposed; final wording after DIAG-A2)

- D-1. R-12 A1, A3–A8 met as pre-committed. A2: 9/10 FDR totals inside. S05 wPLI (5 vs 13–23) is pending DIAG-A2. Under R1 it is an accepted deviation (BH/Monte Carlo resolution at 10.91 Hz, values listed). Under R2 it goes to Sebastian as a blocker, with R11 allowed.
- D-2. S03 coherence 8.57 Hz is estimator-sensitive (not junction-biased) and inconclusive. The junction concern from P12 D-2 is closed for P13: no junction-consistent cell.
- D-3. P12 D-3 alpha hypotheses: ceiling consistent for S03 coherence only, with no cohort-level support. S03 suppression not supported. S05 exploratory lower-tail finding (coherence/PLV down, wPLI up), carried to P14 as a hypothesis, not a result.
- D-4. Flip-list policy: criterion-A flips at the BH minimum count are labelled resolution-limited; any later phase that grades FDR counts uses the same nested-seed convention and states the BH minimum.

Verdict: REJECT

Next step: the orchestrator commits this review, then the verifier runs DIAG-A2 exactly as written (6 commands, wPLI S05 only), records it in 05_run.md / 06_verify.md under "DIAG-A2", and the scientific reviewer applies R0–R2 in "Results review — Round 2". No code or plan change is needed.

## Results review — Round 2

Read: 05_run.md (c6fa935) and 06_verify.md (3865ba6), DIAG-A2 at dba0e05. `git diff --stat 7f6cabb dba0e05 -- src scripts tests configs` is empty. The final files are byte-unchanged (`reports/logs/P13/diagA2_final_sha_before.txt` / `_after.txt`). I re-read `reports/connectivity_cohort_summary_diagA2_rs<B>.csv` for every base (`python -c`, read-only):

| Base | T_B (S05 wPLI FDR total) | FDR edges 24/20/15/10.91/8.57 Hz | global p 24/20/15/10.91/8.57 Hz |
|---|---|---|---|
| 42 | 5 | 0/0/0/0/5 | 0.040/0.065/0.368/0.015/0.010 |
| 1 | 7 | 0/0/0/0/7 | 0.030/0.090/0.373/0.025/0.015 |
| 2 | 14 | 0/0/0/9/5 | 0.030/0.080/0.368/0.010/0.010 |
| 3 | 12 | 7/0/0/0/5 | 0.025/0.075/0.348/0.020/0.015 |
| 4 | 7 | 0/0/0/0/7 | 0.015/0.0498/0.368/0.010/0.010 |
| 5 | 12 | 0/0/0/7/5 | 0.040/0.055/0.393/0.010/0.005 |
| R-12 | 18 | 0/0/0/13/5 | 0.015/0.070/0.398/0.005/0.010 |

**Applying the pre-committed rule.**
- **R0 holds:** the base-42 rows equal the final S05 wPLI rows (`DataFrame.equals` True on condition, p, uncorrected and FDR edges).
- **R1 holds:** base 2 gives T = 14 (≥ 13) and E = 9 (≥ 3).
- **R2 does not hold.**

A2 is therefore an **accepted deviation (BH / Monte Carlo resolution)**.

**Honest reading.** R1 was met at its threshold, not comfortably:
- Only 1 of the 6 bases falls inside the window 13–23. The six totals have median 9.5, and five lie below the window.
- No base reaches R-12's 13 edges at 10.91 Hz (maximum 9).
- The 10.91 Hz count is all-or-nothing across bases (0/0/9/0/0/7) while its global p stays between 0.010 and 0.025. The 24 Hz cell also flips on criterion A (7 edges in base 3 only).

So the FDR count of this subject is resolution-limited at 200 permutations, and the seed-42 value of 5 is one draw from a spread of 5–14. The spread also leans below the reference. The data cannot tell whether that lean is chance (six draws) or a small systematic difference from the original (for example its seed scheme), and I do not claim either. This is recorded as information for Sebastian, not as a blocker, because the pre-committed R2 condition is not met.

The criteria that rest on global p are stable across all six bases:
- S05 wPLI 24 Hz p is 0.015–0.040, so A3 holds in every base.
- 10.91 and 8.57 Hz stay significant (0.005–0.025), so the wPLI-only part of A4 is unchanged.
- 20 Hz is borderline: p 0.0498 in base 4 (10/201 < 0.05) and 0.055–0.090 in the others (R-12 0.070). The report labels it inconclusive.

### Final decisions (for decisions.md)

- **D-1.** R-12 accepted. A1 and A3–A8 met as pre-committed. A2: 9 of 10 FDR totals inside. S05 wPLI is an accepted deviation.
  - Seed-42 total 5 against the window 13–23 (R-12 18).
  - DIAG-A2, same procedure, random_state bases 42/1/2/3/4/5: totals 5/7/14/12/7/12; 10.91 Hz FDR edges 0/0/9/0/0/7 (R-12 13); global p at 10.91 Hz 0.005–0.025 in every base.
  - Cause: a BH all-or-nothing block of 13 uncorrected edges at p 0.005–0.045, so the count is resolution-limited at 200 permutations.
  - Only 1 of 6 bases falls inside the window, and the spread leans below R-12; whether that lean is systematic is not established (information for Sebastian).
  - The reported value stays 5.
- **D-2.** S03 coherence 8.57 Hz is estimator-sensitive (not junction-biased): 8 FDR edges concatenated vs 0 aligned, p 0.104 vs 0.697. It is inconclusive. The P12 D-2 junction concern is closed for P13: no cell is junction-consistent.
- **D-3.** P12 D-3 alpha hypotheses:
  - Ceiling: consistent for S03 coherence only (baseline 0.6435/0.7390 vs S04 0.5831/0.6422), with no cohort-level support. The baseline–difference rho is descriptive and biased negative by construction.
  - S03 alpha suppression: not supported (coherence p_lower 0.219 concatenated, 0.368 aligned).
  - S05: an exploratory, uncorrected observation (coherence/PLV below baseline at 10.91/8.57 Hz, wPLI above; 7 of 40 lower-tail p < 0.05, about 2 expected by chance). It is carried to P14 as a hypothesis only.
- **D-4.** Monte Carlo policy for FDR counts:
  - Criterion-A flips at the BH minimum count are labelled resolution-limited.
  - Any later phase that grades FDR-edge counts pre-commits a seed-base diagnostic of this kind for misses, and its acceptance windows name "BH/Monte Carlo resolution shown by that diagnostic" as an admissible mechanism. This closes a gap in my P13 A2 list.
  - The nested 100/200 nulls and the BH minimum counts are stated wherever counts are compared.

### Report requirements (confirmed, with the A2 wording fixed)

Requirements 1–9 of Round 1 stand. Requirement 3 is now concrete. The S05 wPLI line reads:

> FDR total 5 at seed 42 (window 13–23, R-12 18), not within tolerance. Accepted deviation, BH/Monte Carlo resolution: the same procedure with bases 1–5 gives 7/14/12/7/12 (10.91 Hz: 0/9/0/0/7 edges, R-12 13); 1 of 6 draws inside the window, the spread leans below the reference, and the cause of that lean is not established.

It must never say "reproduces R-12" for this cell. Also:
- Add the DIAG-A2 table above, with its CSV paths, as a labelled DIAGNOSTIC. Its values are not averaged into any reported number.
- S05 wPLI 20 Hz is listed as inconclusive (p 0.0498–0.090 across bases).
- The "reproduc" grep (requirement 9) also covers the S05 paragraphs.

Verdict: APPROVE

## Questions
