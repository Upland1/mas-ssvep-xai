# P22 · 07 · Scientific review

Status: READY (pre-run audit, Round 1)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_ml-engineer.md, 04_tests.md, `git diff main -- src scripts tests configs` (branch @ 91bf2f8), decisions.md P21 C-1..C-6 and P22 rows, RULES R1/R2/R8/R9, PF-34..37, R-16, builder smoke outputs under `mas/state/scratch/p22/`

## Pre-run audit — Round 1

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | `within_splits` = `StratifiedGroupKFold(folds, shuffle, seed)` over the subject's true trial ids, with `assert_no_shared_trials` (`scripts/benchmarks/benchmark_loso.py:316-323`), seeds `seed + r` (`:325-344`). It is called only on the held-out subject's rows (`:478-482`). The LOSO outer split is still the subject (`loso_split :268-272`). The splitter is registered as leak-free in `tests/test_no_leakage.py`. Groups are `P["trial"]`, not `P["groups"]`. These are identical for classes 101-105, because `cv_groups` differs from `trial_ids` only on 202 rows (`src/io/subject_data.py:195-201`); see note N2. |
| R2 Fit only in-fold | PASS | CSP is fitted on `tr` only (`lda_features :287-291`), the scaler and LDA sit in the fold pipeline, and FBCCA is calibration-free. Warm-up: the statistics come only from `Fte[m]`, the first-K rows (`benchmark_loso_warmup.py:112-114`). No test label is an argument (`:99`). Post-K rows and labels do not enter (tests `test_warmup_statistics_ignore_labels_and_every_window_after_k`, tester's first-K/post-K test). `full` = `subject_zscore` over every held-out row (`:109`), i.e. the `lda_subjnorm` normalization. The docstring (`:1-24`) labels it "offline upper bound" and `warmup` "the online variant", per the R2 exception (a)-(c). Labelling in the CSV: note N3. |
| R3 Filter continuous, then window | PASS | No filtering in the new code. Saved bands come from the continuous build (`load_subject(..., bands=...)`). |
| R4 Estimator small-sample bias | N/A | No connectivity estimator. |
| R5 Shared quality decision | PASS | `load_subject(..., "shared", thresholds=..., channel_fail_fraction=...)` gets every threshold explicitly (`benchmark_loso.py:675, 693`). In shared mode these values are inert: the mask is the folder's `valid_mask` (`src/io/subject_data.py:177-183`). This matters for the `configs/` decision (F2). |
| R6 Index layouts verified | PASS | `proba_rep` (repeats, n, K) is checked against an independent grouped CV (tester, atol 1e-6). The recording order is checked on planted layouts where the id order differs from the recording order (builder + tester). |
| R7 Honest statistics | N/A | No permutation statistics. Margins are in binomial-SE units (P21 C-3), see predictions. |
| R8 Smoothing respects trials | PASS | `smooth_two_tap` sorts by (trial, offset) (`benchmark_loso.py:518-525`) and is applied per repeat for `within_lda`. Warm-up smoothing runs on the scored (post-K) rows only, so warm-up trials are excluded whole (`benchmark_loso_warmup.py:123-140`). |
| R9 Per-subject reporting with data source | PASS | Per-subject rows plus Mean/SD. The data-source string names the build folder, session, cohort and channel mode. 2.0 s does not apply (LOSO at w1 only, as in P21). Scribe obligations: N3, N4, N5. |
| R10 Sources | PASS | 03/04 list only project specification files and code that were opened. No external source is claimed. |
| R10 Copied lines | N/A | Nothing adapted. |
| R11 Reference after an attempt | PASS | 03 and 04 declare none. `mas/state/scratch/reference_access.log` has 42 lines, and its last entry (2026-10-28T07:41, P19 scribe) predates P22. |
| Golden rule 3 | N/A | Era C, and the roadmap prescribes no legacy behaviour. The removed `--allow-config-mismatch` was a P21 deviation, not a legacy path (decisions.md P21 row "deviations accepted (1)"). |
| Tests cover every change; one fails on the bug | **FAIL** | The refusal hole F1 has no test (`test_check_fold_head_rules` covers the dirty flag only at equal heads). A `configs/`-only head change is untested (tester gap). There is no planted case for a trial whose first window was rejected (PF-36 caveat in 03). `04_tests.md` "Full suite" still reads `SUITE_PLACEHOLDER`. |
| Changes match 02_plan.md and roadmap | **FAIL** | The module docstring promises "a changed dirty flag is refused" (`benchmark_loso.py:39`). `fold_problem` refuses it only at equal heads (`:404-411`). Deviations 1-7 of 03 are accepted in decisions.md (P22 row, 2026-10-28). |
| No data, `.ebr`, local tooling or vendor names | PASS | Privacy scan with the guard's term list (built from fragments) on `git diff main`, on the commit messages `main..HEAD` and on the changed file names: 0 / 0 / 0. |

### Specific checks requested

1. **`within_lda` grouping and channels.**
   - It uses the LOSO pool `P` (`:478-482`), so its CSP bands and FBCCA scores are exactly the arrays of `lda` / `lda_subjnorm`. That makes it the matched comparison of P21 C-3 for every subject in every channel mode.
   - Tester: in a CLI with names `Oz O1 POz`, `lda` and `within_lda` configs carry the same list, and `proba_rep` is recomputed independently on `load_subject(channels=names)`.
   - Smoke at `e1d696c` (clean, `all2`): the `within_lda` accuracies of S02/S05 under `all` (77.36 / 99.09) equal those under `names` (77.36 / 99.09, `mas/state/scratch/p22/{all2,names}/summary.csv`). This is as expected: the subject's arrays are the same and the within fit does not depend on the cohort. It is binding item V7.
2. **Explicit `--channels`.**
   - `parse_channels` rejects mixing `common`/`all` with names, duplicates and an empty list.
   - `leave_out_for_names` validates against the montage and leaves out any subject whose gate dropped a named channel. It prints `[-] Leaving out ...` and `[=] Keeping ...: gate dropped ...` (`:676-689`).
   - Fewer than 2 subjects exits. The cohort, the fold-count guard and the trial offsets use the remaining subjects (`:744`).
   - PASS.
3. **`check_fold` coverage.** Every config key is refused except `data_root`; `test_alt_covers_every_config_key` guards the coverage. An unresolvable head is refused. `git_head` / `git_dirty` are captured once at process start (`:708`, and `capture_run_state` in the warm-up `main`).
   - **Hole F1.** With different heads and no src/scripts difference, a dirty-flag change is accepted. Probe on this branch (read-only, Python):

     ```
     .venv/bin/python -c "from scripts.benchmarks import benchmark_loso as L; ... fold_problem({lda,42,4d14bb0,dirty False},{lda,42,91bf2f8,dirty True})"
     code_changed False
     diff heads, clean->dirty: None
     same head, clean->dirty: working tree state differs at the same head (dirty False -> True)
     ```

     So a fold saved from a clean tree is reused by a process running uncommitted `src/` edits, if a docs-only commit landed in between. That is the live-tree scenario of P21 C-1 (doc commits mid-run). It is harmless for the verifier's clean-worktree run, but `check_fold` is the contract P23 resumes on.
4. **`configs/` in `CODE_PATHS` (decision).**
   - For the current methods, a `configs/` change cannot alter a fold. `benchmark_loso.py` reads the config only for the quality thresholds and the fail fraction (`:720-722`), and shared mode ignores both (`src/io/subject_data.py:177-183`).
   - Still, `DIRTY_PATHS` includes `configs` while `CODE_PATHS` does not (`:107-108`), so a committed config change is accepted and the same edit uncommitted is refused.
   - Other harness entry points read the config: `src/models/cnn/benchmark_common.py:139` does. A later per-script gate or config-read hyperparameter would therefore mix silently.
   - **Decision: `configs` joins `CODE_PATHS` (F2).** The cost is a refusal after a config-only commit, which is rare and safe.
   - Separately, `--config <file>` is not recorded. This is inert in shared mode; recorded as note N7.
5. **Fold-count guard (P21 C-2).**
   - `short` (`:613`) flags every method with fewer fold files than the remaining cohort. That includes non-requested methods left in the out-dir; those whose config differs are dropped with `[warn]` first.
   - Mean/SD are NaN in `summary.csv` and `per_subject.csv`, and `Data source` reads "INCOMPLETE ... (cohort mean refused)". `--partial-mean` is an accepted deviation.
   - The P21 `reports/loso_w1` scenario (2 eegnet folds, cohort 39 config) is refused by the `cohort` key before the guard.
   - PASS.
6. **Warm-up.**
   - **Recording order** = the smallest `window_starts` among the trial's loaded (valid) rows, ties broken by id (`benchmark_loso_warmup.py:58-66`). `window_starts` = the start sample in the one continuous recording (01_DATA_SPEC §5.2).
   - When a trial's first window is rejected, its rank uses its first valid window. The shift is at most segment length − window (≤ 4 s at 5 s segments), and trial onsets are about 15 s apart in the smoke (`recording_order.csv`, S01 ranks 1-11). So the order cannot change while consecutive first starts are more than 5 s apart (binding item V9).
   - Trials with no valid window neither count toward K nor are scored.
   - **The three variants are scored on the same windows** (`sc = ~warm`, `:123`).
   - **`full` and `none` are exactly the LOSO `lda_subjnorm` / `lda` fits.** It is the same `lda_features`, the same per-subject z-score of the training rows in the same order, and the same pipeline seed. Their per-window probabilities must therefore equal the common-run predictions (binding item V8).
   - **Std guards:** < 2 warm-up rows gives std 1 (centring only), and features with std < 1e-12 get 1. Both are reported in `Std guard`. In the smoke, no row triggered either guard, but S04 K = 1 had only 3 warm-up windows (span 1.5 s).
   - **R2 labelling:** PASS in code text. The CSV lacks the label (N3).
7. **Builder deviations** (decisions.md P22 row 168): accepted. `--partial-mean` defaults to refusing the Mean. The `Folds` column and the extra columns come after the §6 columns. The warm-up script is single-pass (V2 requires an absent out-dir). Same dirty head accepted: F1 narrows this to equal heads only.

### Required fixes

1. **F1 (ml-engineer; PF-37, P21 C-1; `scripts/benchmarks/benchmark_loso.py:397-413` and docstring `:36-41`).**
   - Refuse whenever the dirty flags differ, at any head.
   - Also refuse when either side is dirty and the heads differ, because dirty content cannot be compared across heads.
   - The only accepted dirty case stays "same head, both dirty" (accepted deviation).
   - Make the docstring state exactly this rule.
2. **F2 (ml-engineer; PF-37; `:107`).** `CODE_PATHS = ("src", "scripts", "configs")`. Update the docstring (`:39`) and the refusal message ("changes src/, scripts/ or configs/").
3. **T1 (synthetic-tester; tests for F1/F2, temp git repo as in `test_check_fold_head_rules`).** Each case below must give the stated answer. A test reverting F1 or F2 must fail, recorded as a mutant.

   | Head change | Dirty flags (saved → now) | Expected |
   |---|---|---|
   | docs-only | clean → dirty | refused |
   | docs-only | dirty → clean | refused |
   | docs-only | dirty → dirty | refused |
   | docs-only | clean → clean | accepted (unchanged) |
   | configs-only | clean → clean | refused |
   | none (same head) | dirty → dirty | accepted (documented deviation) |
4. **T2 (synthetic-tester; PF-36).**
   - Build a planted synthetic built folder where the earliest window of one trial is `valid_mask = False`.
   - That trial must keep its recording rank, with `First window start` = its second window's start.
   - The first-K set must be unchanged against the unmasked folder, end-to-end through `load_subject`.
5. **T3 (synthetic-tester).** Replace `SUITE_PLACEHOLDER` in `04_tests.md` with the suite count, runtime and log path, rerun alone after F1/F2.

Round 2 audits only the F1/F2 diff, T1-T3 and the full suite.

### Non-blocking notes

- **N1.** The builder's `common`, `names` and `warmup` smokes ran from a dirty tree at `046e45b`; `all2` ran from a clean tree at `e1d696c`. `benchmark_loso.py` is unchanged from `efe635c` to HEAD, so V10 compares the verifier outputs with these smokes.
- **N2.** `within_lda` should pass `P["groups"]` (`cv_groups`) rather than `P["trial"]`. The two are identical for 101-105, but would differ if 201/202 ever join (PF-13).
- **N3 (scribe, R2 (b)/(c)).** Every table must carry these labels: `full` = test-time normalization with whole-session unlabeled statistics (offline upper bound); `warmup` = statistics of the first K unlabeled trials in recording order (online variant, fixed after K); `none` = no test-time normalization. Optional for P23: write the label into the warm-up `Data source`.
- **N4 (scribe).** Report `Warm-up windows`, `Warm-up classes` and `Std guard` next to every K. K counts trials with at least one valid window. A K = 1 warm-up holds one class only, so its loss is a class-coverage effect, not a normalization defect.
- **N5 (scribe).** The `names` run is a 2-subject LOSO: each fit has ONE training subject. It is not comparable with the 5-subject `common` / `all` LOSO numbers, and its `lda` vs `lda_subjnorm` direction carries no R-16 expectation.
- **N6.** Window-level binomial SE ignores the correlation of the ≈ 17 overlapping windows per trial. A margin of 2 SE_Δ is therefore necessary for a directional claim, not sufficient for a "material" one. Optional: a trial-level SE.
- **N7 (P23).** These inputs are recorded per test subject only, or not at all:
  - the window count of the training subjects;
  - the built-folder `meta.git_commit`;
  - the `--config` file hash.

  An in-place rebuild of a training subject's folder would therefore pass `check_fold`. The S01-S05 hash pin covers this run; record these in fold configs before P23 resumes long jobs.

### Pre-registered predictions for the results review (copy verbatim into 02_plan.md)

Disclosure: these were written after the reviewer read the builder's smoke outputs (`mas/state/scratch/p22/`, same code and data), so they are plausibility and reproduction checks, not blind predictions.

Noise unit: SE = 100·√(p(1−p)/n) in pp, with n the windows scored for that accuracy; SE_Δ = √(SE_a² + SE_b²) (P21 C-3). A > B means Δ > +2 SE_Δ. A tie means |Δ| ≤ 2 SE_Δ. "A ≥ B" is refuted by Δ < −2 SE_Δ. The reviewer computes these from `summary.csv` with a shown command.

- **PR-1 (R-16, LOSO below within, matched channels).** In `reports/loso_w1_p22_common` and `reports/loso_w1_p22_all`:
  - For every subject, `lda − within_lda ≤ +2 SE_Δ`.
  - Cohort Mean `within_lda ≥ lda`.
  - Expected strict (> +2 SE_Δ) in common for S01, S02 and S05. S03 and S04 sit near the ceiling and are expected to tie.
  - Smoke: common +2.7 / +2.6 / +1.3 / +0.8 / +2.7 SE_Δ for S01-S05; all +1.8 / +3.0 / +0.6 / 0.0 / +1.4.
- **PR-2 (R-16, `lda_subjnorm ≥ lda`).** In common and all:
  - For every subject, `lda_subjnorm − lda ≥ −2 SE_Δ`.
  - Cohort Mean `lda_subjnorm ≥ lda`.
  - Expected strict gain for S01 and S02 (the subjects far from ceiling). Ties are expected for S03-S05.
  - Smoke all S05 = −1.9 SE_Δ: a tie, but within 0.1 SE_Δ of refutation. If it falls below −2, it is reported as a refutation, not explained away.
  - `names` run: no prediction (N5).
- **PR-3 (test-time normalization vs within).** No direction is predicted. The scribe reports `within_lda − lda_subjnorm` per subject in SE_Δ, and states as a finding whether whole-session normalization closes the LOSO gap (smoke common S01 +0.4, S02 −0.5 SE_Δ).
- **PR-4 (warm-up, cohort).** The cohort Mean `|warmup − full|` is non-increasing over K = 1, 2, 5, 10. At K = 10, cohort Means satisfy `none ≤ warmup ≤ full` (R-16 "warmup between none and full as K grows").
- **PR-5 (warm-up, per subject, K = 10).**
  - `|warmup − full| ≤ 2 SE_Δ` in at least 4 of 5 subjects. Smoke S05 = −2.2: the expected exception, 2 classes in its first 5 trials.
  - Per-subject monotonicity in K is NOT predicted, since class coverage of the warm-up drives it (smoke S02 K1 −3.7 vs K2 −7.0 SE_Δ).
- **PR-6 (warm-up, small K).**
  - At K = 1, `warmup < none` by more than 2 SE_Δ in at least 4 of 5 subjects. Smoke S02 −0.6 is the expected tie.
  - At K = 2, `warmup < none` by more than 2 SE_Δ in at least 3 of 5.
  - Mechanism to state: a 1-2 class warm-up mean shifts every feature toward those classes.
- **PR-7 (identity, not direction).** `full − none` on the post-K windows has the sign of `lda_subjnorm − lda` on all windows for each subject wherever |Δ| > 2 SE_Δ (S01, S02).

### Binding run-list items for the verifier (copy verbatim into 02_plan.md)

- **V1.** Run from the clean verifier worktree. Every fold config and `loso_config.json` / `warmup_config.json` carries ONE `git_head` (= the worktree HEAD) and `git_dirty: false`. Count the distinct heads with a shown command.
- **V2.** Before command 1, the out-dirs `reports/loso_w1_p22_common`, `_all`, `_names` and `reports/loso_warmup` are absent (`ls` shown). The warm-up script overwrites in place.
- **V3.** In every out-dir, the `channels` of each `within_lda__test-<S>.npz` config equals that of `lda__test-<S>.npz`, and equals the expected list:
  - common = `PO3, POz, PO4, PO8, O1, Oz, O2`;
  - all = the 8-channel montage;
  - names = the 8 names in the given order.

  Also check `train_subjects == [S]` for `within_lda` and `Runs = 5` in the summary.
- **V4.** The `names` log contains `[-] Leaving out` lines for exactly S01, S03 and S04 (gate dropped PO7) and `[=] Keeping` lines for S02 and S05. The cohort in `loso_config.json` is `[S02, S05]`.
- **V5.** Refusal check (command 4). It is preceded and followed by sha256 of every file in `reports/loso_w1_p22_common`, the "before" hash taken after command 1 has finished (no later command writes there).
  - It exits ≠ 0, and the message names `seed` and contains "use a new --out-dir". The hashes are equal.
  - Add `--within-repeats 3` (same out-dir, otherwise identical): refused, naming `hyper`.
  - Then rerun command 1 unchanged: 20 `[skip]` lines, exit 0, and `summary.csv` byte-identical.
- **V6.** Every method shows `Folds = 5` (common, all) or `Folds = 2` (names). No `[warn]` or `INCOMPLETE` appears in any log or summary.
- **V7.** Identities across runs (per window, `np.array_equal` on the fold files, or `predictions.csv` joined on subject, trial_id, offset_sec):
  - `within_lda` `proba_rep` of S02 and S05 is identical between `_all` and `_names`;
  - `fbcca` predictions of S02 and S05 are identical between `_all` and `_names`;
  - `fbcca`, `lda` and `lda_subjnorm` predictions are identical between `_common` and P21's `reports/loso_w1_s01-s05`, and between `_all` and `reports/loso_w1_s01-s05_all` (code refactor only). Any mismatch is a finding.
- **V8.** Warm-up identity. For each subject and K, recompute the accuracy of the common run's `lda_subjnorm` and `lda` predictions on the windows of trials ranked > K in `reports/loso_warmup/recording_order.csv`. The results must equal `full (%)` and `none (%)` within 0.005 pp, with a shown command.
- **V9.** For each subject in `recording_order.csv`:
  - the trial count equals the `Trials` column of the common summary;
  - the ranks are not the id order;
  - the minimum gap between consecutive `First window start (s)` is ≥ 5 s.

  Report the minimum gap.
- **V10.** The numeric columns of the four verifier outputs equal the builder smokes in `mas/state/scratch/p22/{common,all2,names,warmup}/summary.csv`. Report any difference with the smoke's head and dirty flag (N1).
- **V11.** The S01-S05 built-folder hash before and after equals `e7f55081…bebab4`. Run the full suite alone. Check the R11 log. Run the privacy scan of 05/06 themselves with the guard's term list, named by reference only.

Verdict: FAIL

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

### Decisions for decisions.md

## Sources spot-check

## Questions
