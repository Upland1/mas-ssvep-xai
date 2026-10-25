# P06 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Audited at `765abc7` (`git diff main...HEAD`). Opened in this run: `AGENTS.md`-referenced `mas/RULES.md` (era matrix, R8 row line 28 as corrected in `3ac8fb3`), `mas/PROCEDURES.md` (scientific-reviewer), `mas/03_ROADMAP.md` P06 (lines 248–270) and the Conventions line (18–19), `mas/02_REQUIREMENTS.md` §4–§6 (lines 140–222), `mas/04_REFERENCE_RESULTS.md` R-4/R-5 (lines 53–74), `mas/05_PITFALLS.md` PF-01/02/11, `mas/state/decisions.md` P05/P06 rows (51–64), `mas/state/reports/P05.md`, the phase files 00/02/03/04, and every changed code and test file.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) | Era row P04–P10: window-level `StratifiedKFold(5, shuffle, 42)`. Ablation uses `legacy_cv(seed)` (`benchmark_feature_selection.py:127`, `legacy_eval.py:35-37`), cohort uses `oof_space` with the same splitter (`benchmark_5_subjects.py:116`, `legacy_eval.py:96-97`). Labelled: `CV_LABEL` (`legacy_eval.py:29`) in console and `.meta.txt` (`benchmark_feature_selection.py:165,177`; `benchmark_5_subjects.py:113,132`), module docstrings (`:18-20`, `:9-11`). The SFS inner CV (sklearn default unshuffled stratified 5-fold over windows of the training fold) is also window-level; inside Era A this is the same prescribed legacy behaviour, not an extra leak across the outer split |
| R2 Fit only in-fold | PASS | CSP: `fold_matrices` fits `FBCSPTransformer` on `subbands[tr], y[tr]` (`legacy_eval.py:63`), called once per fold (`benchmark_feature_selection.py:129`). ANOVA, MI and SFS: `column_sets(Xtr, y[tr], ...)` on the training matrix only (`:101-113,130`); indices applied unchanged to `Xte` (`:136-138`). SFS inner CV runs inside `X_tr` (`feature_selection.py:59-61`). Scaler is the first Pipeline step per fold (`:97-98,136`). Tests: spy shows 15 selector calls of exactly 80 of 100 rows and rejects an all-rows mutant (`test_p06_known_answer.py:119-140`); test-only informative column not selected by ANOVA/MI/SFS from training rows, selected by a full-data fit (`test_p06_feature_selection.py:47-57`, `test_p06_known_answer.py:101-105`). No full-data fit in the diff |
| R3 Filter continuous, then window | LEGACY (by design) | Per-window sub-band filtering inherited from P05 (`prepare_subject` → `build_feature_blocks`), labelled in `legacy_header_lines` (`benchmark_runner.py:52-53`, "per-window sub-band filtering (R3/PF-14)") |
| R4 Estimator small-sample bias | N/A | No coherence/PLV estimator |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) | Per-script extractor mask vpp 0.5–120, std 0.1–35 µV (decisions.md P05 row 56), one mask for every block, printed in the header (`benchmark_runner.py:54-55`). Both scripts call `prepare_subject` with the same default thresholds as the P05 flagship (`benchmark_feature_selection.py:161`, `benchmark_5_subjects.py:108`) |
| R6 Index layouts verified | PASS | Pruning drops `DEFAULT_SUBBANDS.index((38, 52))` = 4 (`benchmark_feature_selection.py:71`; `fbcsp_extraction.py:31`) → columns 40–49, 45 kept (`feature_selection.py:70-84`). Exact set test (`test_p06_known_answer.py:145-157`) and a non-vacuous transformer layout test: swapping band b's content changes a non-empty set of columns inside 10b..10b+9 for b = 0, 2, 4 (`:160-172`). Builder's test at `test_p06_feature_selection.py:84-94` is vacuous (see notes) |
| R7 Honest statistics | N/A | No permutation statistics |
| R8 Smoothing respects trials | LEGACY (by design) | Corrected era row (RULES.md:28): P05–P10 reset at `i % 5 == 0` of the clean array. Reported 2.0 s = `smooth_reported = smooth_probabilities_mod5` via `accuracies` (`legacy_eval.py:32,117-122`), scores stored in clean-array order (`benchmark_feature_selection.py:137-138`). Cross-checked against the roadmap Conventions line ("smoothing" = §5.6 trial-aware rule, `j % 5` on legacy folders; `02_REQUIREMENTS.md` §5.6): consistent. Test: reported 2.0 s equals an independent `i % 5` smoothing of the captured scores, and the no-reset variant differs on that tree (`test_p06_known_answer.py:202-228`) |
| R9 Per-subject reporting with data source | PASS | Cohort CSV one row per subject with counts, 1.0 s and 2.0 s, plus a Mean row (`benchmark_5_subjects.py:121-128`); console states data source and legacy labels (`:103-104,113-114`). Ablation is single-subject by the roadmap (S03) with the data-source line (`benchmark_feature_selection.py:168`) |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | Builder cites roadmap/R-4/R-5/§6 opened in its run, and the scikit-learn API "as installed, docs not fetched" (honest; no paper cited). Tester cites `scipy.stats.f_oneway` (used as an independent oracle) and R-4/§6 |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | No copied code; scikit-learn used through its public API |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | Both handoffs list none; `mas/state/scratch/reference_access.log` has no entry after 2026-10-24T23:49:50 (P05 Round 2) |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS | All P06 behaviour is legacy and labelled in docstrings, console, `.meta.txt`; the cohort script is kept as history (superseded by `benchmark_n_subjects.py` in P11, roadmap P06.3) |
| Tests cover every change; at least one fails on the historical bug | PASS (CONCERN on two weak tests, notes 1–2) | PF-11: all-rows selection mutant rejected (`test_p06_known_answer.py:130-140`); full-data SFS/ANOVA/MI picks the leaked column (`:101-105`, builder `:47-57`); PF-02: no-reset mutant distinguishable (`:228`); p values 55/45/25/25/20 with FBCCA-tail mutant (`:177-197`); Full row equals the flagship CSV on a low-SNR tree (`:202-216`); cohort schema/Mean/order mutants (`:236-273`). I re-ran both P06 files: `29 passed in 158.69s` |
| Changes match 02_plan.md and the roadmap tasks | PASS | P06.1–P06.3 as planned; deviations 1–4 of `03_changes_ml-engineer.md` are within the plan (FBCCA appended by the caller; SFS estimator scaler + sLDA with sklearn inner defaults; Mean of rounded values; extra flags). P06.4 (report v1) is due from the scribe after the run and is reviewed in the results review |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | Fragment-built case-insensitive pattern (vendor/assistant/co-author names) over `git diff main...HEAD`, `git log main..HEAD --format=%B` and `git grep HEAD`: 0 hits. `git ls-files` filtered for raw-data, recording suffix, local tooling folder and local instructions file: 0 hits |

### Judgements requested by the assignment

**(1) Legacy and in-fold.** Only the prescribed Era-A legacy behaviours are present (R1, R3, R5, R8 `i % 5`, fs 250), all labelled. No unprescribed leak: CSP, ANOVA, MI and SFS (including its inner CV) see training rows only; the selected indices are applied unchanged to the test rows.

**(2) Ablation definitions vs R-4.** p = 55 (full), 45 (band index 4 = (38, 52) Hz dropped, columns 40–49), 25 (ANOVA 20 + 5 FBCCA), 25 (MI 20 + 5, `random_state=42`), 20 (SFS 15 + 5), matching R-4's p column and decisions.md row 63. SFS estimator `Pipeline(StandardScaler, LDA(lsqr, auto))`, `direction="forward"`, sklearn default `cv=5` (unshuffled stratified) and accuracy scoring. The original's estimator inside SFS is unknown. I checked whether the scaler matters (shown command, synthetic, features scaled by factors 0.01–100):

```bash
.venv/bin/python - <<'EOF'   # (abridged; full command in this audit's session)
make_pipeline(StandardScaler(), LDA(solver="lsqr", shrinkage="auto")) vs LDA(solver="lsqr", shrinkage="auto")
EOF
# pred agree: 1.0 max|dproba| 3.941291737419306e-15
```

sklearn's `shrinkage="auto"` standardises before Ledoit–Wolf and rescales, so scaled and bare Shrinkage-LDA are the same classifier up to rounding. "Scaled or not" is therefore not a degree of freedom. The remaining unknowns are the estimator family (Shrinkage-LDA vs another model), the inner `cv` and the scoring.

**Pre-committed procedure if an R-4 row is missed (beyond ±1.5 pp):**
1. Counts first: Clean 197 / Rejected 3 on every row. The Full row must equal `reports/flagship_S03.csv` exactly (Δ 0.00). Any Full-row deviation is a bug in the ablation script, not a definition question.
2. One investigation round with labelled DIAGNOSTIC rows only (not in the reported CSV): for a missed SFS row, the inner `cv` (5 vs 3/10 vs shuffled) and the estimator (sLDA vs LDA svd). For a missed MI row, MI with `n_neighbors` default and seeds 0/42. For a missed ANOVA or pruning row, the fold split equals the flagship (Full row check) and `k`. Report all variants side by side. Never pick the one closest to R-4 on that basis alone.
3. R11 after that round (access log timestamps after the diagnostics commit; I check the ordering). Change the reported definition only for a deviation shown in the original code at the P06-stage commit, recorded in decisions.md.
4. Pruning and ANOVA are deterministic given the flagship folds. MI and SFS are deterministic given `random_state=42` and sklearn's unshuffled inner CV. So a miss on these rows cannot be explained as run-to-run noise.

**(3) Cohort script.** It reuses the flagship code path: `prepare_subject` → `benchmark_spaces` (space "FBCSP + FBCCA (in-fold)") → `oof_space` with `get_sklearn_model_suite(seed)["Shrinkage-LDA lsqr"]` (`sklearn_models.py:36`) → `accuracies`. This is the same call as `scripts/evaluation/evaluate_confusion_matrix.py:147`. There is no re-implementation. The schema matches §6 exactly (`benchmark_5_subjects.py:54`). The Mean row is the mean of the rounded CSV values, with counts blank (`:83-89`). R-5's means reproduce from the rounded values (shown command): `np.mean([64.50,66.33,90.36,98.98,96.50])` = 83.334 → 83.33, `np.mean([75.50,71.94,95.43,98.48,96.50])` = 87.57. Subjects are discovered by `^S\d+$` in numeric order, and a subject that cannot be evaluated is skipped with a printed `[-] Skipping`. Not tested: if a subject is skipped, the Mean covers fewer than five; the console count line shows it.

**(4) Tests.**
- Confirmed: the builder's `test_band_major_layout_matches_fbcsp_transformer` is vacuous. Running its exact construction (`make_windows(n_trials=4, seed=2)`, band 4 ×10) gives `changed cols (builder test): []`, so `set() <= {40..49}` holds trivially. Its docstring ("planted 45 Hz source of class 101 only") also describes data that the test does not build. The tester's parametrised content-swap test replaces it as evidence. But the vacuous test is **still in the suite** (`tests/test_p06_feature_selection.py:84-94`); it was not removed.
- `test_ablation_rejects_selection_on_all_windows`'s docstring says the rows are "matched by value against the fold's test matrix", but only row counts are asserted (`test_p06_known_answer.py:129,140`). This is enough for the all-rows mutant. The claim overstates the test.
- Other buggy variants I checked by inspection, all caught or impossible:
  - a split different from the flagship's (caught by the Full == flagship equality on a low-SNR tree);
  - the FBCCA tail not appended (caught by the p mutant);
  - the wrong band (exact set test);
  - selection indices applied to a re-ordered matrix (the same `cols` index both `Xtr` and `Xte`, `:136-138`);
  - an unseeded MI (asserted through the kwargs, since behaviour cannot show it).
- Gap: the cohort test compares only the 1.0 s value with the flagship CSV (`test_p06_feature_selection.py:146`). The 2.0 s value goes through the same `accuracies` call, which is compared for the ablation (`test_p06_known_answer.py:216`). Acceptable.

**(5) Run commands and runtime.** Run the plan's two commands unchanged (below). Builder smoke estimate: ablation 1.5–3 min (the SFS is about 14 s per fold), cohort 0.5–1 min. Both are far under `LOCAL_RUN_BUDGET_MIN`. These are extrapolations; the verifier records the real runtimes.

**(6) Suite runtime.** The tester measured 274.37 s. The decisions.md P05 row 54 threshold (5 min) is not crossed. Measured here (`--durations`, P06 files only, 158.69 s total): `test_ablation_script_rows_and_flagship_equivalence` 76.10 s, because it runs the real 15-step SFS on the synthetic tree. `test_sfs_selects_planted_columns_and_count` takes 18.03 s, `test_ablation_selection_sees_training_rows_only` 17.38 s, `test_p_values_...` 14.17 s and `test_ablation_rejects_selection_on_all_windows` 13.22 s.

Recommendation, not a blocker (ml-engineer, at the next touch or in P07 at the latest, before the suite crosses 5 min):
- pass `--sfs-features 2` in the builder's script smoke and assert p = 55, 45, 25, 25, 7 (p = 20 is already proven by the stubbed test, the count 15 by `test_sfs_selects_planted_columns_and_count`), saving about 70 s;
- or mark the 15-step SFS cases `slow` and keep a fast default run.

**(7) Privacy.** Clean (table row above).

### Required fixes

None (no FAIL).

### Non-blocking notes

1. **Tests, vacuous R6 test (ml-engineer).** Delete or replace `tests/test_p06_feature_selection.py:84-94`. As written it passes for any layout and its docstring describes data it does not build. The R6 evidence is the tester's `test_band_major_layout_against_transformer`. Also correct the docstring overclaim at `tests/test_p06_known_answer.py:120-122` (synthetic-tester): rows are counted, not matched by value.
2. **Suite runtime (ml-engineer).** See (6). Shrink the 76 s script smoke.
3. **§4 `--subjects` (ml-engineer, cosmetic).** The ablation script has `--subject` (singular), as the roadmap's run line prescribes. §4 asks every script for `--subjects`. Accept for this single-subject legacy script; record it if P11 supersedes it.
4. **SFS estimator.** Scaled vs bare Shrinkage-LDA is not a degree of freedom (shown above). If R-4's SFS row is missed, the procedure in (2) applies.

### Pre-committed results-review checks

**R-4 (S03), as window counts of 197.** ±1.5 pp, integer range computed with the shown command `math.ceil((p-1.5)*1.97)`, `math.floor((p+1.5)*1.97)`. p must be exact; Clean 197 / Rejected 3 on every row.

| Method | p | 1.0 s target (count) | accepted counts | 2.0 s target (count) | accepted counts |
|---|---|---|---|---|---|
| Full baseline | 55 | 90.36 (178) | 178 only (must equal flagship_S03.csv) | 95.43 (188) | 188 only |
| Sub-band pruning | 45 | 87.31 (172) | 170–174 | 94.92 (187) | 185–189 |
| ANOVA F-score | 25 | 86.29 (170) | 168–172 | 94.42 (186) | 184–188 |
| Mutual information | 25 | 87.82 (173) | 171–175 | 93.40 (184) | 182–186 |
| Sequential forward selection | 20 | 84.77 (167) | 165–169 | 93.40 (184) | 182–186 |

Qualitative reading checked (not tuned): whether every reduction is at or below the Full row, as in R-4. A selected subset that beats Full on 1.0 s is checked as a possible leak before it is accepted.

**R-5.**
- Counts exact: S01 200/0, S02 196/3, S03 197/3, S04 197/1, S05 200/0.
- Per-subject accuracies within ±1.5 pp. P05 reproduced all ten exactly on the same code path, so any Δ ≠ 0 is investigated as a regression (e.g. a stale `data/processed` or a changed mask).
- Mean within ±1.0 pp of 83.33 / 87.57, and equal to the mean of the CSV's rounded rows.
- Exactly five subject rows + Mean; the console says the CV is leaky.

**Report v1 (`docs/report/v1/`), from the scribe after the run.**
- (a) `report.md` has the sections Abstract, Introduction, Materials and Methods, Results, Discussion, Conclusion and References, at roughly 5 pages.
- (b) The historical title is verbatim. The correction note sits directly under it ("Historical document (P06). Its 'leakage-free' claim was later shown wrong: window-level CV leaks trials (P11)" or equivalent). No other sentence presents "leakage-free" or "leak-free" as true; every occurrence is checked.
- (c) The ablation table equals `reports/feature_selection_ablation_S03.csv` and the cohort table equals `reports/five_subjects_benchmark.csv` cell by cell, with each table's CSV path stated.
- (d) Methods state the legacy protocol: window-level CV, `i % 5` smoothing, fs 250, per-window filtering, the per-script mask limits, FBCCA on all 7 channels.
- (e) R9: per-subject 1.0 s and 2.0 s for S01–S05 with the data source (legacy folders, OO session); never the mean alone.
- (f) R10: every reference is listed as opened in the scribe's run in `03_changes_scribe.md`. Papers not opened are not cited (P05 open item 7). I open at least two cited sources.
- (g) `methodology_infographic_v1.svg` exists, is valid SVG, is labelled v1/historical and shows the planned flow (recording → 1–60 Hz → 1 s windows → mask → FBCSP + FBCCA → scaler → Shrinkage-LDA → i%5 smoothing).
- (h) There are no vendor, assistant or tool names, and no answer-key path, in the committed report files.

### Run commands (for the verifier, unchanged from 02_plan.md)

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_5_subjects
```

Expected: about 1.5–3 min and about 0.5–1 min on one core (builder extrapolation). Outputs `reports/feature_selection_ablation_S03.csv` (+ `.meta.txt`) and `reports/five_subjects_benchmark.csv` (+ `.meta.txt`). Logs go under `reports/logs/P06/`.

## Results review

Part 1 of 2: the numeric results (R-4, R-5). Part 2, report v1 (P06.4), is pending below, and the verdict waits for it.

Opened in this part:
- `05_run.md` and `06_verify.md` (b695b9a, plus the diagnostic-run sections 348f3a4/f2fba32);
- `03_changes_ml-engineer.md` "Round 1 — investigation" and "Round 1 — R11 consultation" (fbf7391);
- the last decisions.md rows;
- `reports/feature_selection_ablation_S03.csv` and the header of `reports/feature_selection_sfs_diagnostics_S03.csv`;
- `mas/state/scratch/reference_access.log`;
- the code diff `3030a25..HEAD`.

### Deviations from references

Counts: windows of 197, the pre-committed ranges. Arithmetic: `round(x/1.97, 2)` and `89.85-84.77`, `95.94-93.40` (shown command: `rep [89.85, 95.94]`, `5.08 2.54`).

| Ref | Expected | Obtained (`reports/feature_selection_ablation_S03.csv`, log `reports/logs/P06/benchmark_feature_selection_20261025_035546.log`) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-4 Full, p 55 | 90.36 (178) / 95.43 (188), = flagship | 90.36 (178) / 95.43 (188), p 55, 197/3; equals `flagship_S03.csv` | 0.00 / 0.00 | yes (exact, as pre-committed) | — | yes |
| R-4 Pruning, p 45 | 87.31 (172) / 94.92 (187) | 87.31 / 94.92, p 45, 197/3 | 0.00 / 0.00 | yes | — | yes |
| R-4 ANOVA, p 25 | 86.29 (170) / 94.42 (186) | 86.29 / 94.42, p 25, 197/3 | 0.00 / 0.00 | yes | — | yes |
| R-4 MI, p 25 | 87.82 (173) / 93.40 (184) | 87.82 / 93.4, p 25, 197/3 | 0.00 / 0.00 | yes | — | yes |
| R-4 SFS, p 20 | 84.77 (167; 165–169) / 93.40 (184; 182–186) | 89.85 (177) / 95.94 (189), p 20, 197/3 | +5.08 / +2.54 pp (+10 / +5 windows) | **no** | No reference implementation exists (below). The leak audit is clean. Ten labelled variants do not reach both ranges | **yes, as accepted deviation D-1 (P06)** |
| R-5 S01–S05 | 200/0 64.50/75.50; 196/3 66.33/71.94; 197/3 90.36/95.43; 197/1 98.98/98.48; 200/0 96.50/96.50 | identical (`reports/five_subjects_benchmark.csv`, 06_verify R-5 table) | 0.00 on all ten | yes | same code path as P05 | yes |
| R-5 Mean | 83.33 / 87.57 | 83.33 / 87.57 (= mean of the rounded rows, 83.334 / 87.57) | 0.00 | yes | — | yes |

**Four R-4 rows and all of R-5 are exact.** I read this as fidelity of the shared path: folds, CSP, mask, FBCCA, scaler + Shrinkage-LDA and `i % 5`. The R11 reading confirms the original's ANOVA, MI and pruning definitions (277ddab `benchmark_feature_selection.py:59-64,88-122`). The one structural difference: the original selects on the scaled FBCSP block, ours on the unscaled one. It cannot move ANOVA (F is invariant to per-column affine scaling). It barely moves MI, because sklearn's MI standardises continuous features internally (installed `sklearn/feature_selection/_mutual_info.py:297`, `scale(...)`). Both rows are exact, so no change is warranted.

### Decision on the SFS row: ACCEPT as deviation D-1 (P06)

Evidence, each item opened in this run:
1. **There is no SFS in the original's code to reproduce.** The R11 consultation searched the original's history: `log --all -S SequentialFeatureSelector`, "forward selection", the README at the P06-stage commit and at HEAD. It found no sequential forward selection on any branch. The P06-stage ablation script has exactly four methods: Full, ANOVA, MI, pruning (277ddab `benchmark_feature_selection.py:59-64`). R-4's SFS row therefore comes from a run or text that is not in the repository. The original report (.docx) was not readable by the agents. Estimator, candidate set, inner CV, scoring, scaling and in-fold vs full-data fitting are all unknown. No definition can be "demonstrated" from the reference, and golden rule 5 forbids choosing one because it lands near the target.
2. **The pre-committed procedure was followed, in order.**
   - The verifier's FAIL came first (b695b9a, 03:58).
   - Labelled diagnostics: code a5bdafb at 04:14; the run started 04:35:43 and lasted 674 s; recorded in 348f3a4 at 04:47:32.
   - The first reference access followed at 04:48:01 (`reference_access.log`), after the diagnostics, as required. Every access is a read-only query listed in the handoff (rows 1–6).
   - No reported definition changed: the diagnostics CSV "reported" variant equals the reported row, and the re-written ablation CSV is byte-identical (`cmp`, 05_run.md).
   - The diagnostic code is behind `--sfs-diagnostics`, off by default. Its rows carry "DIAGNOSTIC (P06 round 1), not a reported result". `select_sfs_fbcsp_features(cv=None)` keeps cv=5. The new splitter import is registered as legacy in `tests/test_no_leakage.py`.
3. **No leak in our SFS.** `reports/feature_selection_sfs_audit_S03.csv` shows, per outer fold:
   - 157–158 SFS input rows, equal to the training rows;
   - outer index sets disjoint;
   - 0 outer test rows found by content in the SFS input.

   The audit asserts all of this in code (`leak_audit_row`, `benchmark_feature_selection.py`). This agrees with the pre-run R2 finding and the PF-11 mutant tests.
4. **No variant reaches both ranges** (06_verify.md "Diagnostic run" table).
   - "all 55 columns, n=20" hits the 1.0 s range (166) but misses the 2.0 s range (179).
   - "cv=3" hits the 2.0 s range (185) but misses the 1.0 s range (173).

   A single, natural definition that reproduces R-4 would have been evidence; two different variants each matching one column is not. Note: R-4's 84.77 (167/197) also appears in P05 for other spaces (e.g. FBCSP-only Shrinkage-LDA 1.0 s, `mas/state/reports/P05.md:158`). With 197 windows only about 200 values are possible, so this coincidence is **not** evidence of a transcription error. I mention it only so nobody uses it as one.

Rejecting would only turn an unanswerable definition question into a blocker. Neither code fix nor tuning can resolve it from the material available to the team. Accepting is conditional on:
- (a) The SFS value is reported as ours, 89.85 / 95.94, with R-4's 84.77 / 93.40 next to it and the reason. It is never called "reproduced".
- (b) Our SFS definition is named everywhere it appears: `SequentialFeatureSelector`, forward, scaler + Shrinkage-LDA (lsqr, auto), unshuffled stratified inner cv=5, accuracy, 15 of the 50 FBCSP columns + 5 FBCCA, fitted in-fold.
- (c) **Open question for Sebastian** (not a blocker): the .docx report, or his memory of the SFS run, may give the original configuration. If it does, the row is revisited as a labelled re-run, not a silent change.

**Verifier restatement.** With D-1 accepted, the numeric part of `06_verify.md` should be restated as **PASS with accepted deviation D-1 (R-4 SFS row)**, in the same way P05's D-1 was handled (appended restatement, original FAIL kept). P06.4 (report v1) still has to pass before the phase verdict.

### Interpretation check

- **SFS vs Full.** SFS is +1 window at 2.0 s (189 vs 188) and −1 window at 1.0 s (177 vs 178). That is a tie within one window, not "SFS beats Full". The pre-committed leak check for a subset beating Full was done (item 3) and is clean. Under window-level outer CV every row here is leaky (R1/PF-01): S03's trials have windows in both training and test folds. So neither SFS nor any other selection can be read as a real gain or loss over Full. The ordering of rows separated by a few windows is not interpretable.
- **Configuration sensitivity.** Inner-CV and estimator changes alone move SFS between 172 and 177 windows at 1.0 s (87.31–89.85 %) and between 185 and 189 at 2.0 s (93.91–95.94 %). That is a 5-window (2.5 pp) and 4-window (2.0 pp) spread with the same p = 20. Changing the candidate set (55 columns incl. FBCCA) drops it to 166 / 179. The selected FBCSP columns differ strongly between outer folds (the audit lists five different 15-column sets; only column 9 is in all five). SFS on about 158 rows over 50 correlated CSP features is unstable. R-4's SFS row (−5.6 pp vs Full) is well inside what a plausible configuration change could produce, so the original's ranking "SFS lowest" is not a robust finding. Report v1 must not draw a methodological conclusion from the SFS row.
- **Per subject (R9).** The ablation is single-subject (S03) by the roadmap. The cohort table reports all five subjects at 1.0 s and 2.0 s with the data source (legacy folders, OO session). The spread is large: S01 64.50 and S02 66.33 against S04 98.98 and S05 96.50. The mean of 83.33 / 87.57 hides it. All values are leaky and not comparable with R-6, as the console and `.meta.txt` state.
- **Fitted objects.** Pre-run, I found no full-data fit in the reported path. The R11 note adds that the original fits its scalers per block in-fold, which is equivalent.
- **Statistics:** none in this phase (R7 N/A).

### Report v1 (P06.4) — Round 1

Reviewed at a42a66f: `docs/report/v1/report.md` (3881 words, `wc -w`), `docs/report/v1/methodology_infographic_v1.svg`, and `03_changes_scribe.md`. Both report files are tracked (`git ls-files docs/report/v1`).

| Check | Result | Evidence |
|---|---|---|
| (a) Seven sections, about 5 pages | PASS | Abstract (`report.md:7`), 1 Introduction (`:11`), 2 Materials and Methods (`:17`), 3 Results (`:63`), 4 Discussion (`:135`), 5 Conclusion (`:147`), References (`:155`). There is also a §6 "shown script" (`:151`). 3881 words is about 5–6 pages |
| (b) Historical title + correction note directly under it; no sentence presenting leakage-free as true | PASS | The title (`:1`) is verbatim the roadmap's. The boxed note at `:3` is directly under it. `grep -noiE "leak(age)?[- ]free"` hits only `:1`, `:3`, `:9` ("claim is wrong") and `:145` ("claim is therefore wrong") |
| (c) Tables equal the CSVs cell by cell, with paths | PASS | Shown command: `.venv/bin/python -I -` parsed the markdown tables of `report.md` and compared them with `pd.read_csv(..., dtype=str, keep_default_na=False)`. Output: `reports/feature_selection_ablation_S03.csv header eq True cells eq True`, `reports/five_subjects_benchmark.csv header eq True cells eq True`, `diag table eq True` (Table 5 vs `reports/feature_selection_sfs_diagnostics_S03.csv`, window counts `round(acc*1.97)`). Each table caption names its CSV and log. Table 2 deltas re-derived: +5.08 / +2.54 |
| (d) Legacy methods stated | PASS | §2.2 (`:25-33`): window-level StratifiedKFold(5, shuffle, 42), `i % 5`, fs 250, per-window filtering, per-script mask 0.5–120 / 0.1–35 µV, FBCCA on 7 channels (`:37`), PO7 excluded (`:23`) |
| (e) R9 per subject with data source | PASS (one factual fix) | Table 3 lists all five subjects at 1.0 s and 2.0 s; §2.1 gives the data source (legacy folders `data/processed/<S>/`, OO session). Fix 1 below (rejected-window sentence) |
| (f) R10, only opened sources | PASS | 16 references, all repository paths or installed-package lines; primary papers explicitly not cited (`:174`). Spot-checked in this run: `sklearn/feature_selection/_sequential.py:189-191` (`direction="forward"`, `scoring=None`, `cv=5`); `sklearn/discriminant_analysis.py:48` ("'auto': automatic shrinkage using the Ledoit-Wolf lemma"); `src/features/ssvep/window_mask.py:17` (0.5/120/0.1/35); `configs/pipeline_config.yaml:15-21` (1–60 Hz, order 4, vpp 200, std 0.5–60); `scripts/preprocessing/run_preprocessing.py:1-7,60-61` (filtfilt, vpp_min 0.5); `mas/state/reports/P05.md:25,59` (Chebyshev-I order 4, 3 harmonics). Each says what the report claims |
| (g) Infographic present, valid, labelled | PASS | `xml.etree.ElementTree` parse OK, root `svg`, viewBox `0 0 1200 720`. The text includes "Methodology pipeline v1 (historical, P06)", "v1 — historical" and "Not the corrected pipeline". The flow is the planned 8 steps, with the legacy notes (R1/PF-01, PF-04, R3/PF-14) and source paths |
| (h) No vendor/tool names | PASS (one wording fix) | Fragment-built pattern over `docs/report/v1/*` and the last 3 commit messages: no vendor or assistant hits. The internal word "handback" at `:153` is fix 4 |
| D-1 (a) ours beside R-4, with reason, never "reproduced" | **FAIL (fix 2)** | §2.5, §3.1 Table 2, §4 and §5 are correct. But three blanket sentences claim the whole ablation was reproduced: `:13` "This report reproduces both", `:137` "The cohort table and the ablation reproduce the legacy protocol numerically", `:149` "This report reproduces … the S03 feature-selection ablation" (`:149` then says four of five; `:13` and `:137` do not) |
| D-1 (b) SFS definition named | PASS | `:51` and `:87` give the full definition. The abstract and conclusion refer to the row as deviation D-1 without a ranking claim |
| Interpretation | **FAIL (fix 3)** | `:139` says "No uncertainty interval was computed, so the rows are not ranked by significance" and then "The sub-band pruning result is the clearest effect". Table 1 contradicts it: ANOVA costs more than pruning at 1.0 s (shown command: full − ANOVA = 4.07 pp, 8.02 windows; full − pruning = 3.05; full − MI = 2.54). A single-subject, leaky, interval-free difference is not an "effect" of the band |

### Required fixes (report v1, scribe; saved to `docs/report/v1/report.md` by whoever holds write permission, as for a42a66f)

1. **R9 / factual, `report.md:143`.** "The S02 subject has three rejected windows and S04 one" leaves out S03, which also has 3 rejected windows (Table 3) and is the ablation subject. Name S02 (3), S03 (3) and S04 (1). Say that the `i % 5` resets of these subjects, including every S03 ablation row, are misaligned after their rejections.
2. **D-1 (a), `report.md:13` and `:137`, and `:149` for consistency.** Qualify the reproduction claims: four of the five ablation rows and all cohort values reproduce the reference; the SFS row is deviation D-1 (ours, not reproduced). Suggested for `:137`: "The cohort table and four of the five ablation rows reproduce the reference values numerically; the SFS row does not (D-1)."
3. **Interpretation, `report.md:139`.** Delete "The sub-band pruning result is the clearest effect: removing the 38–52 Hz band costs about three points at 1.0 s on this subject." Or replace it with a reading Table 1 supports, e.g. "Every reduced set is at or below the full baseline at 1.0 s (by 0.51–4.07 pp, 1–8 windows); with one subject, a leaky split and no interval, no reduction is singled out." Any arithmetic must come from a shown command.
4. **Traceability, `report.md:153`.** "The script is in Part C of the handback" points to something not in the repository. Point to `mas/state/phases/P06-feature-selection-cohort/03_changes_scribe.md`, "Part C". Also extend reference [8] (`:164`) with "results review part 1 (D-1, commit 637dad6)", since §2.5, §3.1 and §4 cite [8] for D-1.

No other change is needed. Tables, title, note, methods, references and infographic pass. Re-review covers the changed lines and re-runs the table-equality command.

Verdict: REJECT

### Decisions for decisions.md

From the results review (part 1):
- P06 | **Accepted deviation D-1:** R-4 SFS row (p 20) is not reproducible from reference code (no sequential forward selection in any commit; P06-stage 277ddab `benchmark_feature_selection.py:59-64` has Full/ANOVA/MI/pruning only). Ours 89.85 / 95.94 (177 / 189 of 197) vs 84.77 / 93.40. Leak audit clean, ten labelled variants none in both ranges, procedure order verified (diagnostics 04:47:32 before first access 04:48:01). Report it as ours, with R-4 beside it, definition named; open question to Sebastian (original .docx / run). Verifier restates the numeric verification as PASS with D-1 | results review | `P06-feature-selection-cohort/07_review.md`, `06_verify.md`, `03_changes_ml-engineer.md` R11
- P06 | Four R-4 rows (Full, pruning, ANOVA, MI) and all ten R-5 values + means exact (Δ 0.00); the original selects on the scaled FBCSP block (277ddab l.88–91), ours on the unscaled one — equivalent for ANOVA, MI exact too; not changed | results review | same
- P06 | Interpretation: SFS vs Full is a ±1-window tie; SFS spans 172–177 / 185–189 windows across inner-CV/estimator variants (unstable, fold-to-fold column sets differ), so neither R-4's "SFS lowest" nor our order is a finding; all P06 numbers leaky (window-level CV) | results review | same

Proposed from the pre-run audit:
- P06 | SFS estimator scaled vs bare Shrinkage-LDA (lsqr, auto) is the same classifier up to rounding (synthetic check, max |Δproba| 3.9e-15); the open SFS unknowns are estimator family, inner cv and scoring; pre-committed R-4 miss procedure in `07_review.md`.
- P06 | Test hygiene: the builder's vacuous R6 layout test (`tests/test_p06_feature_selection.py:84-94`) to be removed; the 76 s script smoke to use a small `--sfs-features`; suite runtime 274 s, below the 5-min threshold.

## Sources spot-check

Pre-run: `mas/04_REFERENCE_RESULTS.md` R-4/R-5 (lines 53–74) opened and matched to the plan's targets; `mas/RULES.md:28` (R8 era row) opened; `mas/02_REQUIREMENTS.md` §6 schema line opened and matched to `benchmark_5_subjects.py:54`.

Results (part 1): `reports/feature_selection_ablation_S03.csv` was opened and matches 05_run.md's console rows (MI 2.0 s written `93.4`). The diagnostics CSV "reported" row is 89.85 / 95.94, equal to the reported SFS row. `reference_access.log` entries at 2026-10-25T04:48:01–04:48:46 are all ml-engineer read-only queries, matching handoff rows 1–6. I did not open the reference tree myself.

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
