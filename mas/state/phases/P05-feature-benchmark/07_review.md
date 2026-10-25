# P05 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Scope: every file in `git diff main...HEAD --stat` (HEAD f43d8b6) opened and read in full or at the cited lines; specs read: `mas/03_ROADMAP.md` P05, `mas/01_DATA_SPEC.md` §5.1, §6, `mas/02_REQUIREMENTS.md` §1, §4–§7, `mas/04_REFERENCE_RESULTS.md` tolerance rules, R-3, R-5, `mas/05_PITFALLS.md` PF-01/02/04/06/10/11/12/14, `mas/state/decisions.md` P04–P05 rows [1–5]. Full suite re-run by me: `.venv/bin/python -m pytest tests/ -p no:warnings -o addopts=""` → `413 passed in 121.54s (0:02:01)`, exit 0.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) — prescribed P04–P10 `StratifiedKFold(5, shuffle, 42)` over windows; labelled in docstring, console header and `.meta.txt` | `src/models/classical/legacy_eval.py:28,32-34`; `src/models/classical/benchmark_runner.py:43-52`; `scripts/benchmarks/feature_based/benchmark_cross_validation.py:241`; registry `tests/test_no_leakage.py:53-56,89-96` |
| R2 Fit only in-fold | PASS. CSP fitted on `subbands[tr], y[tr]` only, test rows only transformed; scaler + model in one `Pipeline` per fold; LDA shrinkage estimated in-fold; no feature selection; static blocks (PSD, harmonic, FBCCA, sub-band filtering, mask) use no labels and fit nothing. No model selection feeds a reported number (each script reports a fixed model or the whole table). Full-data CSP only in `extract_fbcsp_features`, used only by `visualize_data` (docstring + figure caption) = the prescribed R2 exception. CONCERN (test strength) below, note 1 | `legacy_eval.py:55-66,99-108`; `fbcsp_extraction.py:254-263`; `scripts/exploration/visualize_data.py` `fbcsp_block`, `_plot_class_feature_heatmap` caption; tests `tests/test_p05_known_answer.py:390-431` (in-fold 0.23 vs leaky 0.67; spy on fit rows), `tests/test_p05_feature_benchmark.py:242-258` |
| R3 Filter continuous, then window | LEGACY (by design) — Chebyshev (FBCCA) and Butterworth (FBCSP) sub-bands filtered on each 1 s window (PF-14), labelled | `src/features/ssvep/fbcca_extraction.py:9,104`; `src/features/ssvep/fbcsp_extraction.py:17-20,179-183` |
| R4 Estimator small-sample bias | N/A (no coherence/PLV) | — |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) — per-script gate; all four limits written out (vpp 5–120, std 1–35), a thresholds dict missing a key raises; printed in every header. PF-10: one mask computed once, handed to every extractor, alignment asserted — PASS | `src/features/ssvep/window_mask.py:16,28-33`; `src/models/classical/feature_spaces.py:161-169`; tests `test_p05_known_answer.py:434-477` (separate-gate mutant gives different lengths) |
| R6 Index layouts verified | PASS. FBCSP `(n, B·K·2m)` band→class→component proven column by column against an independent Butterworth+eigh oracle, with swapped-order mutants failing; continuous PSD channel-major proven by a closed-form on-bin tone; harmonic PSD channel-major by name; `filters_ (K, C, 2m)` | `fbcsp_extraction.py:146-148,213-226,248`; `test_p05_known_answer.py:287-315,317-389` |
| R7 Honest statistics | N/A | — |
| R8 Smoothing respects trials | LEGACY (by design) — no-reset 2-tap average in array order (PF-02); `j % 5` variant only printed, labelled DIAGNOSTIC, never in a CSV | `src/preprocessing/dataset/smoothing.py:328-350`; `legacy_eval.py:114-118`; `scripts/evaluation/evaluate_confusion_matrix.py:122-125`; test `test_p05_known_answer.py:531` (smoothed differs from raw at a trial boundary) |
| R9 Per-subject reporting with data source | PASS. Each script prints the data source (legacy folder, OO session, stimulus windows), 1.0 s and 2.0 s for the subject, clean and rejected counts; flagship CSV per subject | `benchmark_cross_validation.py:232-246`; `evaluate_confusion_matrix.py:109,132-143` |
| R10 Every change and test cites a source that exists and says what is claimed | CONCERN. The formulas are cited to the roadmap [2] (correct). The handoff also lists Chen 2015, Ramoser 2000, Ang 2008 as "cited from the spec, paper not opened in this run"; the spec does not cite them (`grep -n "Chen\|Ramoser\|Ang " mas/*.md` → no hit), and R10 says to cite only what was opened. The DOIs and the attributed formulas (FBCCA weights `n^-1.25 + 0.25`; `log(var/Σvar)` per CSP) are, to my knowledge, the right ones, so nothing false is claimed. Note 3 | `03_changes_ml-engineer.md` Sources 5–7; `fbcca_extraction.py:5-6`; `fbcsp_extraction.py:6-7` |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A — nothing consulted or copied | — |
| R11 Reference consulted only after an attempt, every consultation listed | PASS. Both handoffs say "None"; the access log has no entry after the 21:27 lines (already settled as pre-P04 in decisions.md P04) | `mas/state/scratch/reference_access.log` (tail); 03/04 handoffs |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS. Every legacy behaviour is labelled where it lives (docstrings, console header, `.meta.txt`, figure titles). For now it is the only path; P11/P16 must keep it behind a flag | as above |
| Tests cover every change; at least one fails on the historical bug | PASS. PF-11: the full-data CSP mutant gives 0.67 on label-free noise vs 0.23 in-fold; PF-10: separate-gate mutant; PF-04: 24 Hz CCA r 1 at fs 250 vs < 0.8 at 256; PF-06: the P04 POz set fails; PF-12: QDA excluded (spy) and its failure caught. Gaps in notes 1, 2 | `tests/test_p05_known_answer.py`, `tests/test_p05_feature_benchmark.py`, `tests/test_no_leakage.py` |
| Changes match 02_plan.md and the roadmap tasks | PASS. P05.1–P05.5, the visualize_data extension and the P04 carry-forward are all done; the 7 listed deviations are acceptable (notes 5–7) | 03 handoff "Deviations" |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS. Fragment-built patterns: `git grep -i -E` over HEAD, `git diff main...HEAD` and `git log main..HEAD --format=%B` → 0 hits; no tracked `data/`, `reports/`, `outputs/`, tooling or answer-key paths; the diff only touches `src/`, `scripts/`, `tests/`, `mas/state/` | commands in this run |

### Judgements requested by the assignment

**(1) Legacy behaviours and leaks.** Each legacy behaviour in the code is one the era matrix prescribes (R1, R3, R5, R8, fs 250, the R2 visualization exception) and is labelled. I found no unprescribed leak. FBCCA, PSD, harmonic PSD, the sub-band filtering and the mask use no labels. The CSP, the scaler and the LDA shrinkage are fitted on training rows. Test folds choose no model, threshold or feature.

**(2) Extractor math against the roadmap.** Checked by reading the code, not only through the tests:
- FBCCA. Chebyshev-I, order 4, 3 dB, passband `[low, min(90, nyq−1)]` for low ∈ {6, 14, 22} Hz, `fs=fs` design (`fbcca_extraction.py:76-80`). References are sin and cos rows at h·f, h = 1..3, with `t = n/fs` (`:67-73`). CCA(1) uses all window channels. `r_b` is the Pearson r of the canonical variates, 0 on exception or non-finite r (`:88-97`). The score is `Σ_b w_b r_b²` (squared, `:108`) with `w = 1.25, 0.6704, 0.5033`, which I recomputed. This covers the formula slips that ranking tests miss (w·r instead of w·r², a wrong high edge, missing cos rows; bug_patterns P04).
- FBCSP. Covariance is `W Wᵀ / tr(W Wᵀ)`, uncentred as the roadmap writes it, averaged per group (`fbcsp_extraction.py:186-191`). `eigh(S_t, S_t + S_r + 1e-6 I)` (`:212`). The filters kept are the m largest in descending order, then the m smallest (`:213`). Variances are floored at 1e-12 before `log10(var/Σvar)` (`:224-225`). Butterworth is order 4 with filtfilt and the high edge capped at nyq−1 (`:170-176`).
- **Per-class normalisation reading.** Per-class is the natural reading. One-vs-rest CSP is K separate two-class CSPs, and the Ramoser log-variance normalisation of a CSP sums over that CSP's own 2m selected projections. The roadmap's "→ 5 classes × 2m per band" also groups the features by class. A global sum over all 5·2m projections would mix filters from five different eigenproblems, each scaled by its own `S_t + S_r` constraint. A side effect worth recording: with m = 1, each class pair is redundant (`f₂ = log10(1 − 10^{f₁})`), so the 50 FBCSP columns carry 25 degrees of freedom. Shrinkage-LDA tolerates this. I accept the builder's reading.
- **Pre-committed procedure if R-3 is missed** (golden rule 5; decisions.md P05):
  - (a) Counts first. If S03 is not exactly 197 kept / 3 rejected, the investigation is about the mask (thresholds, the input array, per-channel failures), not the CSP.
  - (b) If the counts are exact but either accuracy is outside ±1.5 pp, the ml-engineer gets one investigation round. The global-sum CSP normalisation, the CCA implementation (iterative sklearn CCA vs closed form) and the filter form may each be computed **as labelled diagnostics only**.
  - (c) After that round, an R11 consultation of the original's CSP transform and FBCCA scorer is allowed and is logged.
  - (d) The definition changes only if the reference shows a demonstrated deviation from the spec text, recorded in decisions.md. Picking whichever variant lands closest to R-3 is forbidden.
  - (e) If R-3 is still missed, the results review decides between an accepted, explained deviation and a blocker. Nothing is tuned.

**(3) Shared mask and PF-10.** `validate_eeg_windows` runs with the shared defaults written out (`window_mask.py:16`). It runs once in `build_feature_blocks`, and the same mask reaches the PSD, FBCCA, harmonic and sub-band blocks. A length check raises on misalignment (`feature_spaces.py:161-169`). Extractors given a mask do not gate again (`window_mask.py:23-27`). This satisfies decisions.md P05. The 197/3 count on real data is the verifier's check.

**(4) Layouts, suite and QDA.**
- Layouts: as in the R6 row.
- Suite: matches P05.4 (`sklearn_models.py:202-220`), confirmed by `get_params` under warnings-as-errors (`test_p05_known_answer.py:481`).
- Elastic-net LogReg: `max_iter=3000, tol=1e-3` are not in the roadmap (they copy the L1 row). This is an [own] choice; record it in decisions.md.
- PA SGD: gains `random_state=seed`, which is harmless.
- Models without `predict_proba`: in this environment Ridge and SGD PA have no `predict_proba` through the Pipeline, so they get a softmax of the decision function. That only affects their 2.0 s column. It is labelled.
- QDA: excluded from `benchmark_cross_validation` (`:189`), run in `test_sklearn_models`, with failures caught and printed (`legacy_eval.py:109-110`). Expected outcome: the rank failure appears on PSD (210) and FBCSP (50) but not on FBCCA (5), because a training fold has about 32 windows per class.

**(5) P04 carry-forward and registry.**
- The moves change no behaviour. The function bodies are identical; `train_models.py` re-exports them; `spatial_spectral_cnn.py` drops its lazy `scripts.*` imports.
- The P04 test edit only retargets the monkeypatch to the name now bound in `cnn` (`tests/test_p04_early_models_known_answer.py:304`). P03/P04 tests all pass (413 passed).
- `--seed` defaults to 42. `train_models.main` sets the module global `SEED`, which persists across in-process calls. CONCERN, note 4.
- `tests/test_no_leakage.py` is a sound start: the helper's leak detection is itself proven, the legacy leak is documented, and an unregistered `from sklearn.model_selection import …` fails the scan. Gaps for P11 are in note 2.

**(6) Runtime.**
- The runs fit the budget easily. The builder measured about 51 s for the four scripts on a synthetic 200-window tree. With a 3× real-data margin, 11 commands come to ≲ 15 min, against `LOCAL_RUN_BUDGET_MIN: 120`. No human run is needed.
- Suite runtime: 121.54 s, against the "about a minute" target. Correctness is unaffected, so this is a CONCERN, not a FAIL. The slowest test is P04's `test_scripts_smoke_exports_and_csv` at 39.60 s; the P05 script smokes add about 25 s (`--durations=8`, this run). The orchestrator should record a decision before P06 adds more, e.g. a `slow` marker for script smokes or smaller synthetic trees.

**(7) Privacy.** PASS (last row of the rule table).

### Required fixes

None.

### Non-blocking notes

1. **R2 test strength (synthetic-tester, next touch).** `tests/test_p05_feature_benchmark.py:261-285` builds `p1`/`p2` Pipelines inside the test and never asserts on `oof_space` output (`res2` is unused). A variant that fits the scaler on all rows before CV would pass. The code is correct by inspection (`legacy_eval.py:106`). Replace it with a check that goes through `oof_space`, e.g. perturb only fold-0 test rows and assert that fold-0 training statistics (spy on `StandardScaler.fit` row count) are unchanged.
2. **Registry gaps (P11).** The scan misses `cross_val_score/cross_val_predict/cross_validate` with an integer `cv` (unshuffled window-level splits), `from sklearn import model_selection`, and `import sklearn.model_selection as …`. The CNN's inline splitter (`spatial_spectral_cnn.py:137`) is registered as a file but has no `LEGACY` factory. Add these when P11 moves splitters to `LEAK_FREE`.
3. **R10 (ml-engineer, next handoff).** Cite the papers only after opening them, or cite them as "named in the code docstring, not verified in this run". Do not write "cited from the spec".
4. **Global seed (ml-engineer, next touch).** `scripts/training/train_models.py` `main` rebinds the module global `SEED`. Pass the seed through as a parameter instead.
5. **Confusion counts.** No text or CSV output holds the confusion matrix; only the annotated PNG does. Print it in the classification-report txt if the script is touched. Otherwise the verifier reads the cell counts from `outputs/figures/confusion_matrices/cm_fbcsp_m1_fbcca_cv_S03.png` and names it as the source.
6. **Harmonic PSD bins under PF-04 (LEGACY (by design), for interpretation).** On the fs-250 grid, the nearest bins to 17.14, 24 and 30 Hz are k = 18, 25 and 31. A true response sits at k = 17, 24 and 30 (`.venv/bin/python` enumeration in this run; the other five targets hit their true bin). So the benchmark harmonic PSD has no 24 Hz fundamental bin. A weak class 101 in that space is a PF-04 artefact, not physiology. P16 fixes it.
7. `visualize_data` now computes `psd fbcca fbcsp` by default, so the P03 run line produces two extra figures. The PSD figure is unchanged. Accepted.

### Run commands for the verifier (repo root, clean tree, CPU)

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_harmonic_fbcca --subject S03
.venv/bin/python -m scripts.evaluation.test_sklearn_models --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03 --m 2
for S in S01 S02 S04 S05; do .venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject $S; done
.venv/bin/python -m scripts.exploration.visualize_data --subject S03
```

All other flags stay at their defaults (`--fs 250`, `--seed 42`, `--m 1`). Do not pass `--no-figures`.

Expected outputs:
- `reports/feature_space_benchmark_S03.csv` (55 rows) and `.meta.txt`
- `reports/sklearn_suite_S03.csv`
- `reports/flagship_S0{1..5}.csv` (S03 with rows m = 1 and m = 2)
- `reports/classification_report_{benchmark_harmonic_fbcca_S03, evaluate_confusion_matrix_S0x, evaluate_confusion_matrix_S03_m2}.txt`
- `outputs/figures/confusion_matrices/cm_harmonic_fbcca_cv[_S03].png`, `cm_fbcsp_m1_fbcca_cv[_S0x].png`, `cm_fbcsp_m2_fbcca_cv[_S03].png`
- `outputs/figures/exploration/S03/{psd,fbcca,fbcsp}_features_by_class.png`

Runtime ≲ 15 min.

### Pre-committed checks for the results review

1. **Counts (exact).** S03 must be 200 stimulus, 197 clean, 3 rejected in both CSVs and the console. Otherwise, procedure (2a).
2. **R-3 accuracy, `flagship_S03.csv` m = 1.**
   - 1.0 s: 90.36 % = 178/197. Tolerance [88.86, 91.86] %, i.e. 176–180 windows.
   - 2.0 s: 95.43 % = 188/197. Tolerance [93.93, 96.93] %, i.e. 186–190 windows.
   - Counts: `python3 -c` in this run.
   - The pipeline is deterministic, so an exact match is expected if the reading matches. A result inside tolerance but not exact is accepted with an explanation. A miss triggers procedure (2b–e).
3. **The hybrid beats every single-domain space.** On 1.0 s, the maximum over the 9 models of `FBCSP + FBCCA (in-fold)` must be strictly greater than the maximum of each of Continuous PSD, Harmonic PSD, FBCCA and `FBCSP (in-fold)`. A tie does not count as beating. 2.0 s is reported alongside. This best-of-9 comparison picks the maximum on the test folds and is descriptive only.
4. **FBCCA argmax is the lowest supervised reference.** Following the R-3 wording, the argmax 1.0 s must be below all 18 supervised rows of the two hybrid spaces. I will also report its rank among all 54 rows. A single-domain row below the argmax (Harmonic PSD is a candidate, note 6) is reported, not counted as an acceptance fail.
5. **R-3 qualitative.** S03 m = 1 classification report: 101 precision = 1.0000. The largest two-way off-diagonal count is the 104↔105 pair. Shrinkage-LDA lsqr is the best, or tied best, model on FBCSP + FBCCA. A miss is explained, not an automatic reject.
6. **Table and QDA.** The benchmark CSV has 6 × 9 + 1 rows with p = 210, 32, 5, 37, 50, 55, 5 (argmax). A missing row needs its printed failure. In the suite CSV, QDA is absent for PSD and FBCSP and present for FBCCA, with the failures printed.
7. **S01–S05 flagship rows.** Read per subject against R-5 as a diagnostic: an early warning for P06, not P05 acceptance.
   - Counts expected: S01 200/0, S02 196/3, S04 197/1, S05 200/0.
   - Accuracy within ±1.5 pp is noted.
   - All are leaky (R1) and not comparable with R-6.
   - On condition-ordered arrays the no-reset 2.0 s average crosses only 4 class changes. A 2.0 s gain is label-order smoothing, not a 2 s decision gain.
   - On S02 (199 stimulus windows) the printed `j % 5` diagnostic drifts after the short block (PF-02).
8. **Logs.** Every number quoted comes from `reports/logs/P05/*.log` or the CSVs. Each log header carries the commit and a clean-tree flag. The visualize_data FBCSP caption says it is a full-data fit.

## Pre-run audit — Round 2

Verdict: PASS

Trigger: `06_verify.md` (ce30892) gave Verdict FAIL on one stated qualitative R-3 criterion: class-101 precision 0.8537 and a tied 101↔102 / 104↔105 confusion. All quantitative R-3 items passed:
- 197/3 exact;
- 1.0 s 178/197 exact;
- 2.0 s no-reset 189/197, inside tolerance;
- the printed j%5 diagnostic gave 188/197 = R-3, and it matched all five R-5 2.0 s values.

Read for this round:
- `03_changes_ml-engineer.md` "Round 2" and "Round 2 — implementation"; `04_tests.md` "Round 2";
- `mas/RULES.md` @ 3ac8fb3 and the three new P05 rows of `mas/state/decisions.md`;
- the code diff `80a0a5b..efc1020` (`src/`, `scripts/`, `tests/`);
- `mas/03_ROADMAP.md` lines 18-19 (conventions), 155-160 (P04.4) and 186-189 (P04 acceptance); PF-02; `02_REQUIREMENTS.md` §5.6;
- `mas/state/scratch/reference_access.log`.

I did not open the reference tree. Suite re-run at HEAD efc1020: `.venv/bin/python -m pytest tests/ -o addopts="" -q -p no:warnings` → `426 passed in 106.62s (0:01:46)`.

### (1) Is a spec deviation demonstrated, and was anything tuned?

My Round 1 condition was that a definition may change only on a demonstrated deviation from the spec or the original, never because a variant lands closer to R-3.

| Change | Evidence | Demonstrated? | Tuned toward R-3? |
|---|---|---|---|
| Reported "2.0 s smoothed" = reset at `i % 5 == 0` of the clean array (was no-reset) | **The spec itself:** `03_ROADMAP.md:18-19` defines "smoothing" for every phase as "the 2-tap trial-aware rule of `02_REQUIREMENTS.md` §5.6". §5.6 defines it on legacy folders as `j % 5 == 0` on the clean array. The only stated exception is P04.4, "**without** trial reset — the original early behavior" (`03_ROADMAP.md:158-159`). PF-02 tells the same history: earliest no-reset, then the `i % 5` legacy rule. **The original:** the R11 read of the P05-stage commit 69873ea, `evaluate_confusion_matrix.py:97-113`, shows `pos = i % 5`; the benchmark scripts at that commit have no smoothing. The independent R-3/R-5 fit (5 of 5 subjects exact under j%5) is corroboration, not the reason | **Yes.** The roadmap text and the original agree. The Round 1 era row (no-reset P04–P10), and the plan and decision built on it, contradicted the roadmap's own convention. I accepted that row as LEGACY (by design) in Round 1; this was my miss | No. The rule was fixed by the spec text before any number is consulted. j%5 was a pre-planned diagnostic of the first run, not chosen among alternatives after the fact |
| Mask limits vpp 0.5–120 µV, std 0.1–35 µV (were 5–120 / 1–35) | R11: the original extractors' defaults (`fbcca_extraction.py:39-40`, `fbcsp_extraction.py:84-85`, `psd_extraction.py:14-15`, `quality_check.py:6-12` @ 69873ea). The spec is consistent with this: PF-07 says the shared default became `vpp_min = 5.0` only in P07. The roadmap names no thresholds for P05, so the Round 1 "shared defaults" choice anticipated P07 | **Yes,** a deviation from the original legacy behaviour (golden rule 3) | No. The mask could not have helped R-3: under the old limits the counts (197/3) and 1.0 s (178/197) already matched exactly. The change can only leave the numbers unchanged (same rejected set) or move them away from R-3. Re-run check 2 tests this |
| `benchmark_harmonic_fbcca` gives FBCCA only PO8, O1, Oz, O2 (by name); mask still on all channels; no double gate | R11: original `benchmark_harmonic_fbcca.py:25,34` @ 69873ea selects positional `[3, 4, 5, 6]`, which is PO8, O1, Oz, O2 in the 7-channel layout. Roadmap P05.5 says only "occipital harmonic PSD + FBCCA". Not reproducing the original's unmasked harmonic PSD follows PF-10 ("Align every feature block with the final mask"), a P05 prevention, not a legacy behaviour | **Yes** for the FBCCA channel set; by-name selection follows PF-06 / §6 | No. This script carries no reference number |

**R11 procedure: CONCERN.**
- The first answer-key access (log 23:48:50) came 30 s before the diagnostics commit 1e85c17 (23:49:20). The investigation round and the consultation therefore overlapped; no real-data diagnostic run came between them.
- The R11 trigger was still met: an implementation and tests existed, the verifier had FAILed, and the planned j%5 diagnostic had already pointed to the cause.
- Every access is logged under ml-engineer and listed in the handoff table with files, lines and commit. Nothing was copied, and no code changed in the consultation round itself.
- Not a FAIL. For later phases, the diagnostics should be run before the answer key is opened.

### (2) Corrected R8 era row

The corrected row reads: "P04: no-reset; P05–P10: reset at `i % 5 == 0` of the clean array (misaligned once a window of a trial is rejected, PF-02)". It is consistent with:
- PF-02 (both stages, in that order);
- roadmap P04.4 (no-reset is "the original early behavior") and the P04 acceptance note ("smoothing ignores trial boundaries");
- the roadmap convention (lines 18-19) and §5.6 (the j%5 legacy definition on the clean array).

The P04 code still uses no-reset (`scripts/training/train_models.py:206`, `src/models/cnn/spatial_spectral_cnn.py:154-157`), as the corrected row requires. **PASS.**

Residual spec tension, for the P11 assignment (orchestrator; non-blocking now):
- R8's text ("`i % 5` on legacy") and §5.6 ("legacy folders define … `j % 5 == 0` on the clean array, a known approximation") make i%5 look like the enforced form on legacy folders.
- The corrected row, PF-02 ("reset at the first window of each true trial") and PF-03 (pre-gate `build_trial_ids`, indexed with the mask) treat it as the legacy flaw.
- P11 must state which rule its R-6 numbers use on legacy folders: i%5 on the clean array, or pre-gate trial ids. In a subject with a rejection (S02, S03, S04) the two differ.

### (3) Implementation and tests

PASS.
- `legacy_eval.accuracies` uses `smooth_reported = smooth_probabilities_mod5` (`src/models/classical/legacy_eval.py`). The argmax row uses the same rule (`benchmark_cross_validation.py:104`).
- Every header, `.meta.txt` file and report title carries `SMOOTH_LABEL` and `MASK_LABEL`. No-reset appears only as a printed DIAGNOSTIC line and as `_smoothed_noreset.txt`, titled "DIAGNOSTIC … not the reported number". `_smoothed_mod5.txt` is titled REPORTED. Both files hold the confusion counts as text, which resolves Round 1 note 5 for the smoothed predictions.
- The mask is still computed once on all channels and shared. `fbcca_channels` is selected by name and defaults to None, so the flagship, `test_sklearn_models` and the six-space benchmark are unchanged (`src/models/classical/feature_spaces.py`).
- The new tests catch the plausible wrong variants I would try: no-reset wired into `accuracies` (mutant, 0.9 vs 1.0); reset by trial id instead of clean index (12-row closed form); a CSV written with no-reset (flagship script vs independent i%5 on spied scores, on a tree where the rules differ); an argmax row left on no-reset; the old 5/1 limits (vpp 2 / std 0.5 window, plus boundary cases); a positional or POz cluster; FBCCA gated on its own 4 channels (PF-10 mutant).
- The tests pin the "mask on all channels" choice. That choice differs from the original harmonic script, where FBCCA gated its own 4-channel input; it is labelled in the script docstring and affects no reference.

### (4) Two different "Harmonic PSD + FBCCA" numbers

The six-space benchmark row keeps all-channel FBCCA, while `benchmark_harmonic_fbcca` uses the 4-channel cluster. **Acceptable, with labelling.**
- Inside the six-space table one FBCCA block serves the FBCCA, Harmonic PSD + FBCCA and FBCSP + FBCCA rows, and the all-channel flagship reproduced R-3 1.0 s exactly.
- The decision row names only the harmonic script.
- The original `benchmark_cross_validation.py` was searched only for smoothing and thresholds, so its FBCCA channel set is **unverified**. Record it as an open item; a verification-type R11 read is allowed later.
- Labelling is incomplete: the harmonic script's console and report name the channels, but the six-space header and `.meta.txt` do not say "FBCCA on all channels".
- Required of the verifier and the scribe: quote the two numbers under distinct names ("six-space table, FBCCA all 7 channels" vs "harmonic script, FBCCA PO8/O1/Oz/O2"), never as one quantity. The ml-engineer adds the channel names to the six-space header when the file is next touched (non-blocking).

### (5) Run commands and re-run checks

The run commands are unchanged from Round 1 (same seven lines, defaults `--fs 250 --seed 42 --m 1`, no `--no-figures`, repo root, clean tree):

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_harmonic_fbcca --subject S03
.venv/bin/python -m scripts.evaluation.test_sklearn_models --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03 --m 2
for S in S01 S02 S04 S05; do .venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject $S; done
.venv/bin/python -m scripts.exploration.visualize_data --subject S03
```

New outputs to collect: `reports/classification_report_evaluate_confusion_matrix_<S>[_m2]_smoothed_{mod5,noreset}.txt`.

Pre-committed re-run checks. They replace Round 1 checks 1, 2, 5 and 7; checks 3, 4, 6 and 8 stand.
1. **Counts under the new limits (exact).** S03: 200 / 197 / 3. Others: S01 200/0, S02 196/3, S04 197/1, S05 200/0. Any change means the 0.5/0.1 limits contradict the R-3/R-5 counts. That would be a finding against decision (2), reported, with no further change in this phase.
2. **Same rejected set.** The 1.0 s values must be unchanged from the first run: S03 90.36 (178/197); S01 64.50, S02 66.33, S04 98.98, S05 96.50. The same 1.0 s with the same counts is the observable sign that the rejected windows are the same. Any 1.0 s change is reported with the affected windows.
3. **2.0 s equals the former j%5 diagnostic.**
   - Flagship m=1: S03 95.43 (188/197), S01 75.50, S02 71.94, S04 98.48, S05 96.50 (`06_verify.md` table). S03 m=2: 95.94.
   - The new DIAGNOSTIC no-reset line must repeat the first run's reported values: S03 95.94, S01 77.00, S02 71.94, S04 98.48, S05 98.00.
   - Any other value is a bug (same scores, a different rule applied).
4. **Qualitative R-3, read only from the REPORTED file** `classification_report_evaluate_confusion_matrix_S03_smoothed_mod5.txt` (m=1): class-101 precision = 1.0000, and the largest two-way off-diagonal total is 104↔105.
   - Not read from the 1.0 s report, the no-reset file, m=2 or the 1.0 s figure.
   - Choosing among these outputs after the fact is forbidden.
   - If either part fails while checks 1–3 pass exactly, it is a qualitative deviation. The results review explains it (the statement's source is only inferred: the original's figure is computed from smoothed predictions, 69873ea:130) or rejects it. No further definition change is allowed.
5. **Benchmark table.** The 1.0 s columns of `feature_space_benchmark_S03.csv` must equal the first run, so the hybrid and argmax criteria hold as before. All 2.0 s columns change, the argmax row included.
6. **Two Harmonic PSD + FBCCA numbers.** The harmonic script's Shrinkage-LDA value is reported next to the six-space row with the channel sets named. They are expected to differ.

### Required fixes

None.

### Non-blocking notes (Round 2)

1. Name the FBCCA channels in the six-space header and `.meta.txt` (ml-engineer, next touch).
2. Before P11 relies on the original `benchmark_cross_validation.py`, settle its FBCCA channel set and its mask-on-which-channels choice by a logged verification read.
3. R11 sequencing: run the diagnostics before opening the answer key.
4. The flagship figure `cm_fbcsp_m1_fbcca_cv[_S].png` shows 1.0 s predictions (title says so). The original's figure showed smoothed predictions; the smoothed counts are now in `_smoothed_mod5.txt`. Accepted as labelled.
5. Carry the R8-on-legacy-folders question (i%5 on the clean array vs pre-gate trial ids) into the P11 assignment.

## Results review

Verdict: APPROVE
Accepted deviation: D-1 (qualitative, see below).

**What I read:**
- `05_run.md` and `06_verify.md` "Round 2" (971171d);
- the run outputs:
  - `reports/flagship_S0{1..5}.csv`;
  - `reports/feature_space_benchmark_S03.csv` and its `.meta.txt`;
  - `reports/sklearn_suite_S03.csv`;
  - `reports/classification_report_evaluate_confusion_matrix_S03_smoothed_{mod5,noreset}.txt`;
  - `reports/classification_report_benchmark_harmonic_fbcca_S03.txt`;
- the log `reports/logs/P05/evaluate_confusion_matrix_S03_r2_20261025T024450.log`. Its header shows commit edcc177 and an empty `porcelain:` block.

**How the numbers were checked:**
- I recomputed every acceptance criterion from the CSVs with a shown `.venv/bin/python` pandas command (groupby maxima, hybrid-row minima, row count).
- All arithmetic used `python3 -c`.
- No new runs, and no definition changed.

### Acceptance (verbatim criteria)

| Criterion | Obtained | Met? |
|---|---|---|
| S03 FBCSP(m=1)+FBCCA → Shrinkage-LDA = R-3 (90.36 % / 95.43 %, 197 clean, 3 rejected) within tolerance | 90.36 / 95.43, 197 / 3 (`flagship_S03.csv`; log lines 12-13); 178/197 and 188/197; Δ 0.00 / 0.00 pp | **Yes, exact** |
| the hybrid beats every single-domain space | best of 9 at 1.0 s: FBCSP+FBCCA 90.36 > FBCSP 84.77, PSD 84.26, FBCCA 71.57, Harmonic PSD 71.57 (margin 5.59 pp); also at 2.0 s: 95.43 > 90.86 (PSD), the highest single-domain value | **Yes** |
| FBCCA argmax is the lowest supervised reference | argmax 48.73 / 52.28, below the minimum of the 18 hybrid-space rows (70.05 / 77.16) and of all 54 supervised rows (62.94 at 1.0 s); rank 55 of 55 | **Yes** |
| Report the full feature-space × model table | 55 rows = 6 × 9 + argmax; p ∈ {210, 32, 5, 37, 50, 55}; 197/3 on every row | **Yes** (the scribe copies it from the CSV) |
| R-3 qualitative (04_REFERENCE_RESULTS, cited in 00_assignment): perfect precision on 24 Hz; residual confusion concentrated on 10.91/8.57; hybrid + lsqr LDA best; every supervised hybrid configuration beats the argmax | from the REPORTED `_smoothed_mod5.txt`: 101 precision 0.9750 (39/40), recall 1.0000 (39/39); largest two-way confusion 104↔105 = 6, every other pair ≤ 1; lsqr and eigen tied best (90.36 / 95.43), LogReg L2 ties at 2.0 s; argmax below all hybrid rows | 24 Hz precision **not met by one window** (accepted, D-1); the other three qualitative items **met** |

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-3 counts | 197 / 3 | 197 / 3 | 0 | yes (exact) | — | — |
| R-3 1.0 s | 90.36 | 90.36 (178/197) | 0.00 | yes | — | — |
| R-3 2.0 s | 95.43 | 95.43 (188/197), i%5 rule | 0.00 | yes | after the Round 2 rule correction (spec convention + original code; Round 2 audit) | — |
| R-3 qualitative, 24 Hz precision | "perfect" (1.0) | 0.9750 = 39/40; one true-102 window predicted 101 (`_smoothed_mod5.txt`) | −2.5 pp of precision = 1 window of 40 predictions (1/40 = 2.5 %) | no numeric tolerance (qualitative) | see D-1 | **yes** |
| R-5 (P06 target, read for the record) | 10 values | all 10 exact (`flagship_S0x.csv`) | 0 | yes | — | — |

**D-1, the one-window 24 Hz precision difference.** It is acceptable under the tolerance rule ("a deviation can be accepted when the Scientific Reviewer signs an explanation … documented ambiguity").
- **What is exact.** Every quantitative quantity matches, for all five subjects:
  - window counts;
  - 1.0 s accuracy;
  - 2.0 s accuracy;
  - all ten R-5 values.
  
  The deviation is the predicted label of **one misclassified window**: true 102, predicted 101.
- **Why the exact accuracies do not decide it.** Moving that window's error from column 101 to another column would leave every accuracy unchanged. So the exact numbers neither prove nor exclude the original having precision 1.0.
- **Two explanations remain. Both are inferences; neither is demonstrated.**
  - (a) **The wording describes recall, not precision.** The original's figure was computed from the smoothed predictions (`confusion_matrix(y_clean, preds_smoothed)`, 69873ea:130, as quoted in the ml-engineer's R11 table). The 24 Hz row of such a figure is perfect: 39/39, recall 1.0000 here. This makes it the most likely reading of "perfect … on 24 Hz". I did not check whether the original figure was row-normalised; the answer key was not opened by me.
  - (b) **A different library version changes where one error lands.** The iterative sklearn CCA, the Ledoit-Wolf shrinkage and the LDA lsqr solve could all differ slightly between scikit-learn versions. Such a difference could move one near-tie window between the 101 and 103 columns of row 102, again without changing any accuracy.
- **No further definition change, as pre-committed.** The criterion was read only from the REPORTED file. I did not shop among the other outputs (1.0 s, no-reset, m=2).
- **Optional.** A logged verification read of the original figure's normalisation (R11 permits verifying a finished implementation) could turn explanation (a) from inferred to demonstrated. It is not needed for this decision.

**Restating the verifier's verdict.** The verifier's FAIL rests only on this item. With D-1 accepted, the orchestrator and scribe should restate the P05 verification as **PASS with one accepted deviation (D-1)**. All other verifier checks pass exactly. `06_verify.md` itself stays as written (the verifier's file).

### Interpretation check

**Leakage and comparability**
- Every P05 accuracy comes from window-level `StratifiedKFold` (R1 legacy, leaky). None is comparable with R-6.
- Leaky flagship minus R-6 at 1.0 s: S01 +3.50, S02 +10.21, S03 +3.56, S04 +1.52, S05 +1.50 pp. These gaps are expected from the leak and are left for P11 to measure.
- No fitted object leaks beyond the prescribed legacy CV:
  - CSP, scaler and LDA shrinkage are fitted in-fold;
  - the full-data CSP appears only in the visualisation, labelled in the log.

**2.0 s smoothing**
- Gains (2.0 s − 1.0 s) under the reported i%5 rule: S01 +11.00, S02 +5.61, S03 +5.07, S04 −0.50, S05 0.00 pp.
- On condition-ordered legacy arrays, i%5 averages adjacent windows of the same or a neighbouring same-class trial. After a rejection (S02, S03, S04) the blocks drift across trial boundaries (PF-02).
- So the gain is partly an artefact of the legacy order and is not an honest 2 s decision gain. P11 fixes this.
- The no-reset diagnostic is never below i%5 (S01 +1.50, S03 +0.51, S05 +1.50, S02/S04 0.00 pp). This is consistent with the extra cross-trial averaging also exploiting label order. Diagnostic only.

**Feature-space × model table (S03)**
- The hybrid wins by 5.59 pp over the best single-domain space at 1.0 s.
- Spatial (FBCSP 84.77) and broadband spectral (PSD 84.26) are close.
- FBCCA (71.57) and harmonic PSD (71.57) are weaker.
- Shrinkage-LDA lsqr and eigen give identical numbers, which is expected: the same shrunk covariance and the same discriminant. They are best or tied best on the hybrid. LogReg L2 ties at 2.0 s.
- "Best of 9" is a maximum over models evaluated on the test folds, so it is descriptive only and not an accuracy estimate.
- Two readings are plausible but **not demonstrated** in P05:
  - the weak harmonic PSD and the very low zero-training argmax (48.73) are consistent with the fs-250 error: off-target bins for 17.14/24/30 Hz (Round 1 note 6); reference sinusoids off-frequency (PF-04);
  - P16 quantifies this, and this report must not claim it as the cause.

**Two "Harmonic PSD + FBCCA" numbers (Shrinkage-LDA lsqr)**
- Six-space table, FBCCA on all 7 channels: 74.11 / 84.77.
- Harmonic script, FBCCA on PO8/O1/Oz/O2: 75.63 / 84.77.
- Δ 1.52 pp at 1.0 s = 3 windows (`python3 -c`: 3/197 = 1.52 %); identical at 2.0 s.
- No reference exists for either. They are separate quantities and must keep separate names in the report.

**QDA**
- As expected under PF-12: rank failures, printed as `LinAlgError`, on Continuous PSD (210) and FBCSP (50).
- It runs on FBCCA (5) with 70.56 / 80.20, slightly below the linear models on that space. `sklearn_suite_S03.csv` has 28 rows = 3 spaces × 10 models − 2 failures.

**m=2 variant**
- 92.89 / 95.94; no reference. The +2.53 pp at 1.0 s over m=1 is a single leaky split on one subject; inconclusive.

**S01–S05 for P06**
- All ten R-5 values are reproduced exactly, with exact counts. P06's cohort table should reproduce them unchanged.
- S01 and S02 (64.50 / 66.33 at 1.0 s) agree with the P03 finding of weak or absent SSVEP peaks. S04 and S05 are near ceiling.
- Per-subject reading only; no cohort claim is made here.

### Round history (for the report)

1. **Round 1, pre-run.** My audit PASSed and accepted the era row "no-reset P04–P10" as LEGACY. That row contradicted the roadmap convention (`03_ROADMAP.md:18-19` → §5.6). It was my miss and is recorded in my bug patterns.
2. **Round 1, run.** Verifier FAIL on the 24 Hz precision (0.8537, from 1.0 s predictions). The pre-planned j%5 diagnostic equalled R-3 and all five R-5 2.0 s values.
3. **Investigation, R11, and three corrections.** Each was demonstrated by the spec and/or the original:
   - the R8 era row: P04 no-reset; P05–P10 i%5 on the clean array;
   - mask limits 0.5–120 / 0.1–35;
   - visual-cluster FBCCA in the harmonic script.
   
   None was tuning: the counts and 1.0 s already matched before, and the smoothing rule follows from the spec text.
4. **R11 sequencing CONCERN.** The first access came 30 s before the diagnostics commit. Every access was logged and listed.
5. **Round 2 run.** Pre-committed checks 1, 2, 3, 5 and 6 came out exact, and check 4 is split (D-1). Two pre-run rounds were used; neither pre-run FAILed.

### Decisions for decisions.md

- P05 results accepted at 971171d:
  - R-3 exact: 197/3, 90.36 / 95.43 = 178/197, 188/197;
  - all ten R-5 values exact under the i%5 rule and the original mask limits (feeds P06);
  - hybrid > every single-domain space (90.36 vs 84.77); FBCCA argmax last (48.73);
  - table 55 rows.
- **D-1 (accepted deviation).** R-3 qualitative "perfect precision on 24 Hz" is not reproduced by one window: 101 precision 0.9750 (39/40) and recall 1.0000 in the REPORTED i%5 smoothed report. Every accuracy and count is exact, and 104↔105 is the dominant confusion as R-3 states. Most plausible explanations: the wording describes the perfect 24 Hz row (recall) of the original's smoothed-prediction figure, or a library-version difference in where one error lands. No definition was changed. With D-1 the P05 verification is restated as PASS with an accepted deviation.
- **Labelling.** Every P05 accuracy is legacy-leaky (R1) with legacy i%5 smoothing (R8, misaligned after rejections), fs 250 (PF-04) and per-window filtering (R3), and is not comparable with R-6. 2.0 s gains are partly label-order artefacts.
- **Two "Harmonic PSD + FBCCA" quantities.** Six-space (FBCCA 7 channels) 74.11 / 84.77 vs harmonic script (FBCCA PO8/O1/Oz/O2) 75.63 / 84.77. Always named separately.
- **Open items.**
  - Six-space header/`.meta.txt` to name the FBCCA channels (ml-engineer, next touch).
  - Before reuse, a logged verification read of the original `benchmark_cross_validation.py` FBCCA channel set and of whether the original figure was row-normalised (optional, for D-1).
  - P11 assignment must state the R8 legacy-folder rule (i%5 on the clean array vs pre-gate trial ids) for R-6.
  - R11 practice: run the diagnostics before opening the answer key.

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Sources

1. RULE — `mas/RULES.md` R1–R11 and era matrix; `AGENTS.md`; `mas/PROCEDURES.md` "scientific-reviewer" (opened in this run).
2. REQUEST — `mas/03_ROADMAP.md` P05 tasks and acceptance; `00_assignment.md`, `02_plan.md` (opened in this run).
3. RULE — `mas/01_DATA_SPEC.md` §5.1, §6; `mas/02_REQUIREMENTS.md` §1, §4–§7 (opened in this run).
4. RULE — `mas/04_REFERENCE_RESULTS.md` tolerance rules, R-3, R-5; `mas/05_PITFALLS.md` PF-01/02/04/06/10/11/12/14 (opened in this run).
5. HANDOFF — `mas/state/decisions.md` P04–P05 rows; `03_changes_ml-engineer.md`; `04_tests.md` (opened in this run).
6. DATA — `.venv/bin/python -m pytest tests/ -p no:warnings -o addopts=""` and `--durations=8`, HEAD f43d8b6, this run.
7. DATA — `reports/flagship_S0{1..5}.csv`, `reports/feature_space_benchmark_S03.csv` (+ `.meta.txt`), `reports/sklearn_suite_S03.csv`, `reports/classification_report_evaluate_confusion_matrix_S03_smoothed_{mod5,noreset}.txt`, `reports/classification_report_benchmark_harmonic_fbcca_S03.txt`, `reports/logs/P05/evaluate_confusion_matrix_S03_r2_20261025T024450.log`; produced by the Round 2 commands of `05_run.md` at edcc177 (opened in this run, results review).
8. HANDOFF — `06_verify.md` "Round 2" (971171d); `03_changes_ml-engineer.md` "Round 2" R11 table (69873ea:130 quoted there, not opened by me).

## Questions
