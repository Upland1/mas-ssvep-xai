# P22 · 07 · Scientific review

Status: READY (pre-run audit Round 2 PASS; results review APPROVE)
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

## Pre-run audit — Round 2

Scope, as set in Round 1: the F1/F2 diff (101a0f7), the T1-T3 tests (daadad8, 3cf689c) and the full suite.

| Item | Result | Evidence |
|---|---|---|
| F1 dirty-flag rules | PASS | `scripts/benchmarks/benchmark_loso.py` `fold_problem`: differing flags are refused at any head; a dirty side with differing heads is refused; both dirty at the same head is accepted; the docstrings (module and function) state this rule. Same read-only probe as Round 1 (docs-only heads `4d14bb0` / `91bf2f8`), results below. |
| F2 `configs` in `CODE_PATHS` | PASS | `CODE_PATHS = ("src", "scripts", "configs")`; the refusal message names `configs/`. |
| T1 six-row table | PASS | `test_round1_dirty_and_configs_table` (temporary git repo: base → docs-only → configs-only) matches the six rows. Mutants on a scratch copy: F1 revert killed by the 3 differing-head dirty rows, F2 revert killed by the configs-only row (04_tests.md "Fix round 1"). |
| T2 masked first window | PASS | `test_masked_first_window_keeps_rank_and_first_k_set_through_load_subject`: `valid_mask = 0` on disk is read through `load_subject`; ranks are kept, the first start moves to the second window, and the first-K sets for K = 1, 2, 3, 5, 8 are unchanged. |
| T3 suite | PASS | `1441 passed, 22 warnings in 817.69s (0:13:37)`, log `mas/state/scratch/p22/full_suite_tester_r1.log` (last line read). `git diff 3cf689c HEAD -- src scripts tests configs` is empty, so the log covers the current code. Reviewer rerun of the P21 + P22 test files: `125 passed in 24.76s`. |
| R11, privacy | PASS | `reference_access.log` is still 42 lines (no new access). Scan with the guard's term list (built from fragments) on `git diff 581ab9a HEAD` and the commit messages: 0 / 0. |

Probe output (read-only, `.venv/bin/python -c "... L.fold_problem(...)"`), as saved → now:

| Heads | Dirty | Result |
|---|---|---|
| 4d14bb0 → 91bf2f8 | False → True | `working tree state differs (dirty False -> True, ...)` |
| 4d14bb0 → 91bf2f8 | True → False | refused (`working tree state differs`) |
| 4d14bb0 → 91bf2f8 | True → True | `... with uncommitted code changes` (refused) |
| 4d14bb0 → 91bf2f8 | False → False | `None` (accepted) |
| 91bf2f8 → 91bf2f8 | True → True | `None` (accepted, documented deviation) |
| 91bf2f8 → 91bf2f8 | False → True | refused |

Non-blocking notes:

- **N8.** The docstring of `code_changed` (`benchmark_loso.py:142`) still says "`src/` or `scripts/`", but the function diffs `CODE_PATHS`, which now includes `configs`. Fix it with the next code change.
- **N9.** P21-era fold files have no `git_dirty` key (`None`). Against a clean run (`False`) they are now refused. That is safe and consistent with the PF-37 intent; P22 runs use fresh out-dirs (V2).

The predictions PR-1..PR-7 and the run-list items V1..V11 of Round 1 stand unchanged.

Verdict: PASS

## Results review

Reads:

- `05_run.md` and `06_verify.md` (f5700bd, with the privacy-line fix 5f73505);
- `reports/logs/P22/analysis.txt` and `pytest_full.log`;
- `reports/loso_w1_p22_{common,all,names}/summary.csv` and `predictions.csv`;
- `reports/loso_warmup/{summary,cohort,recording_order}.csv`.

Run at 461ef33 from a clean worktree (V1: one head, `git_dirty` False in all 48 folds and in the 4 config files).

### Deviations from references

R-16 sets no numeric target. The pre-registered predictions are PR-1..PR-7, read against the wording above. They were written after the builder smokes had been seen (disclosed above). V10 shows that the verifier numbers equal those smokes exactly, so these are plausibility checks, not blind tests.

| Ref | Expected (pre-registered) | Obtained (`06_verify.md`, `analysis.txt`) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| PR-1 | no subject with `lda − within_lda > +2 SE_Δ` (common, all); Mean within ≥ lda; strict in common for S01, S02, S05 | common −2.74 / −2.56 / −1.26 / −0.76 / −2.68 SE_Δ; all −1.81 / −3.00 / −0.55 / 0.00 / −1.38; Means 90.79 vs 87.61 and 88.99 vs 86.34 | — | yes | LOSO stays below within on matched channels; strict where the subject is off ceiling | yes |
| PR-2 | `lda_subjnorm − lda ≥ −2 SE_Δ` per subject (common, all); Mean subjnorm ≥ lda | minimum is all S05 at −1.89 SE_Δ (reviewer recomputation: −1.62 pp, −1.885 SE_Δ); Means 90.03 vs 87.61 and 88.75 vs 86.34 | 0.11 SE_Δ from refutation | yes, at the edge (D-3) | strict gain only for S01 (+2.30 / +2.26) and S02 (+3.06 / +3.59) | yes |
| PR-3 | reported, no direction | common +0.44 / −0.50 / +1.67 / +0.33 / +2.68 SE_Δ; all −0.45 / −0.59 / +1.10 / 0.00 / +3.16 | — | n/a | whole-session normalization brings LOSO to within-subject level (ties) for S01–S04; S05 within is strictly above subjnorm | recorded |
| PR-4 | cohort mean \|warmup − full\| non-increasing over K; at K = 10 none ≤ warmup ≤ full | 27.27, 19.16, 5.66, 0.91; 88.19 ≤ 89.78 ≤ 90.69 | — | yes | signed means −27.27, −19.16, −5.46, −0.91 (S03 K=5 is +0.51) | yes (D-7) |
| PR-5 | K = 10, \|warmup − full\| ≤ 2 SE_Δ in ≥ 4/5 | 4/5; S05 −2.16 SE_Δ | — | yes | the exception was pre-registered from the smoke value; mechanism open (D-4) | yes |
| PR-6 | K = 1 warmup < none by > 2 SE_Δ in ≥ 4/5; K = 2 in ≥ 3/5 | K = 1: 4/5 (S02 −0.59, tie); K = 2: 5/5 | — | yes | every K = 1 warm-up holds 1 class; K = 2 holds 1–2 classes | yes |
| PR-7 | sign of `full − none` (post-K) = sign of `lda_subjnorm − lda` (all windows), wherever \|Δ\| > 2 SE_Δ | S01 +4.82 / +4.49 / +4.20 / +4.11 pp vs +5.59; S02 +7.01 / +7.05 / +8.05 / +8.20 vs +6.83 | — | yes | complete check, see D-6 | yes |
| V1–V11 | binding run items | all MET (`06_verify.md` table) | — | yes | reviewer spot-checks below | yes |

**Reviewer spot-checks.** These are independent recomputations from the CSVs (`.venv/bin/python` heredoc in this session):

- **V8:** `lda_subjnorm` / `lda` accuracy over the trials ranked after K in `recording_order.csv`:

  | Subject | K | Scored windows | `full` recomputed vs CSV | `none` recomputed vs CSV |
  |---|---|---|---|---|
  | S01 | 10 | 510 | 73.333 vs 73.33 | 69.216 vs 69.22 |
  | S04 | 1 | 662 | 99.698 vs 99.70 | 99.547 vs 99.55 |
  | S05 | 5 | 594 | 97.643 vs 97.64 | 97.811 vs 97.81 |

- **PR-2 edge:** −1.885 SE_Δ, recomputed.
- **Skipped tests:** the 8 skips are exactly the CUDA-only tests:

  ```
  CUDA_VISIBLE_DEVICES="" .venv/bin/python -m pytest -q -rs tests/test_p15_gnn.py::test_model_runs_on_cuda tests/test_p21_loso_networks.py::test_network_fold_runs_on_cuda tests/test_p20_networks.py::test_cnn_fold_runs_on_cuda tests/test_p08_eegnet_known_answer.py::test_cuda_forward_matches_cpu
  ```

  Output: `SKIPPED [1] test_p15_gnn.py:209`, `[3] test_p21_loso_networks.py:127`, `[3] test_p20_networks.py:94`, `[1] test_p08_eegnet_known_answer.py:174`, `8 skipped`. None of them is a P22 test. 1433 + 8 = 1441, the tester's count.

### Interpretation check

- **Matched LOSO vs within (P21 C-3 closed).** `within_lda` runs on the LOSO pool. V3 shows equal channel lists in every fold, and V7 shows that `fbcca`, `lda` and `lda_subjnorm` are bitwise equal to P21's `reports/loso_w1_s01-s05` and `reports/loso_w1_s01-s05_all`. So P22 adds a matched within reference without moving any P21 number.
  - The LOSO cost on matched channels is material (strict) only for S01, S02 and S05 in common, and only for S02 in all.
  - S03 and S04 are at ceiling, where window-level SE cannot separate the methods.
- **Test-time normalization.** `lda_subjnorm` is offline and uses unlabeled whole-session statistics.
  - It brings LOSO to within-subject level (ties) for S01–S04.
  - It never helps S03–S05.
  - It comes within 0.11 SE_Δ of hurting S05 under `all`.

  This is an upper bound and must not be read as an online result.
- **Warm-up (online variant).**
  - With 1–2 warm-up trials (1–2 classes, 4–20 s of signal), first-K normalization is far worse than none: cohort −25.03 and −16.95 pp vs `none` at K = 1 and 2.
  - At K = 10 (about 140 s, all 5 classes in every subject), it sits between none and full: cohort 88.19 ≤ 89.78 ≤ 90.69.
  - Per subject at K = 10, `warmup − none` is strict only for S02 (+3.42 SE_Δ). The cohort +1.59 pp (SD 4.33) is therefore driven by S02 and is not a general online gain.
  - The 1–2-class loss at small K is a class-coverage effect of the warm-up mean, not a code defect: V8 shows that `full` and `none` reproduce the LOSO fits exactly, and `Std guard` = none in all 20 rows.
- **S05 at K = 10 (−2.16 SE_Δ).** All 5 classes are seen, but the first 10 trials are unbalanced: classes 103 ×4, 102 ×2, 105 ×2, 104 ×1, 101 ×1 (`recording_order.csv`, against 8 per class in the session). A biased warm-up mean is a plausible cause, but it was not tested. The pre-run wording ("2 classes in its first 5 trials") does not explain K = 10, and that wording is corrected here.
- **Names run (N5).** This is a 2-subject LOSO, so each fit has one training subject.
  - S02 `lda` 46.27 % is trained on S05 alone, against within 77.36 (−12.12 SE_Δ). S05 `lda_subjnorm − lda` is −3.71 SE_Δ.
  - The run shows that the explicit-names path works (V4, V7), and that one training subject is a poor LOSO cohort. It is not a cohort result, and it carries no R-16 direction.
- **Noise unit.** All SE_Δ values are window-level. About 17 overlapping windows per trial makes them lower bounds (N6), so "strict" claims are necessary-condition claims.
  - `within_lda` SD over 5 repeats is 0.08–1.00 pp, below the window-level SE.
- **R2 labelling.** The code labels are present: the method label `lda_subjnorm (unsupervised per-subject normalization)` and the warm-up docstring. The warm-up CSV columns and `Data source` carry no test-time label. This is a scribe obligation (S1) and a P23 code item (C-3).
- **R9.** Per-subject rows exist for every method, with `2-tap Smoothed (%)` and a data-source string that names the build, session, cohort and channel mode. 2.0 s does not apply (LOSO at w1).
- **Traceability.** Every number in 05/06 points to `reports/logs/P22/*` or the out-dir CSVs. I re-derived the spot-checks above. The cohort |warmup − full| at K = 5 (5.66) is a mean of absolute values, and 06 explains why it differs from the CSV's signed −5.46.
- **Privacy.**
  - The first verification commit f5700bd wrote the path of the local hook script into `06_verify.md`. That path contains one hit of the guard's term list (scan by reference, fragment-built pattern: `git show f5700bd` 1 hit; its removal line in 5f73505 is 1 hit).
  - f5700bd also committed a result placeholder. So the privacy scan ran after the commit, not before it, which repeats the P09 slip.
  - The HEAD tree is clean: `git grep` over the P22 phase folder gives 0, and commit messages give 0.
  - History is not rewritten by agents (P09, P10 and P21 precedent). The hit stays in the branch history and is recorded as D-2 for Sebastian.

### Decisions for decisions.md

Accepted deviations:

- **D-1.** Suite on the clean worktree: `1433 passed, 8 skipped, 22 warnings in 800.46s`. The 8 skips are the CUDA-only tests, skipped because `CUDA_VISIBLE_DEVICES=""` (reviewer `-rs` run: 1 + 3 + 3 + 1). This equals the tester's 1441 passed, and no P22 test was skipped.
- **D-2.** Privacy: f5700bd committed the local hook-script path, 1 hit of the guard's term list, in `06_verify.md`. It was corrected in 5f73505, and the HEAD tree and commit messages are clean. History is not rewritten (P09/P10/P21 precedent); Sebastian may squash before pushing. The scan ran after the commit (a placeholder was committed too), which is a process slip against the P09 rule.
- **D-3.** PR-2 holds at the edge: S05 under `all` is −1.89 SE_Δ, a tie by the pre-registered rule and 0.11 SE_Δ from refutation. It is reported as a tie, not as a gain.
- **D-4.** The PR-5 exception, S05 K = 10 at −2.16 SE_Δ, was pre-registered from the smoke value. The pre-run rationale ("2 classes in its first 5 trials") does not apply at K = 10. Class imbalance of S05's first 10 trials (103 ×4, 101 ×1) is an untested hypothesis.
- **D-5.** The names run is a 2-subject LOSO (one training subject per fit). Its numbers are a record of the explicit-names path, not a cohort result. S05 `lda_subjnorm − lda` −3.71 SE_Δ lies outside every prediction's scope.
- **D-6.** The PR-7 check on S01 and S02 only is complete under the wording. Those are the only subjects with all-window |`lda_subjnorm − lda`| > 2 SE_Δ in common (+2.30, +3.06); S03–S05 tie, and no (subject, K) cell has |z_fn| > 2 with the opposite sign. S01's post-K `full − none` is not strict (1.45–1.97 SE_Δ), so the warm-up table must not call it strict.
- **D-7.** PR-4 is read on the cohort mean of absolute values (27.27, 19.16, 5.66, 0.91). The CSV's signed means (−27.27, −19.16, −5.46, −0.91) are reported beside it.
- **D-8.** The builder smokes (dirty tree at 046e45b) equal the clean verifier run to 0.0 (V10). The smokes are confirmed as previews, not results.

Carry-forwards for P23:

- **C-1 (ml-engineer).** Add three fields to fold configs before any long resumable P23 job:
  - training-subject window counts;
  - the built-folder `meta.git_commit`;
  - the `--config` file hash (N7).

  Also fix the `code_changed` docstring (N8), and pass `P["groups"]` to `within_lda` (N2).
- **C-2 (verifier).** Run the privacy scan on the staged diff (`git diff --cached`) before every commit. Never write local tooling paths into handoffs; any non-zero hit stops the commit (P09 rule).
- **C-3 (ml-engineer, scribe).** Make the warm-up `Data source` (or a `Normalization` column) carry the R2 test-time label, and do the same for any GNN `_subjnorm` output.
- **C-4 (orchestrator, reviewer).** P23 GNN `_subjnorm` variants are labelled offline upper bounds unless a first-K warm-up is run. On this cohort, K ≤ 2 loses 17–25 pp against no normalization, and K = 10 (about 140 s) is the first K tied with whole-session normalization in 4/5 subjects. Pre-register any "online" GNN claim against these P22 numbers.
- **C-5 (all).** Never resume into P21 out-dirs: their folds have no `git_dirty` and are refused (N9). Per-subject network claims keep the P21 C-4 seed-range floor in addition to window-level SE.

### Binding items for the scribe

- **S1.**
  - Every table states its data source: built continuous folders `processed_continuous/w1_s0.25`, session OO, cohort and channel mode, LOSO or within-subject, 1.0 s windows, stride 0.25 s.
  - Every table labels the normalizations:
    - `full` = test-time normalization from unlabeled whole-session statistics (offline upper bound);
    - `warmup` = statistics of the first K unlabeled trials in recording order (online variant, fixed after K);
    - `none` = no test-time normalization.
  - `lda_subjnorm` keeps its "(unsupervised per-subject normalization)" label.
- **S2 (R9).** For the common and all runs, report per subject the Acc and the 2-tap Smoothed accuracy of `fbcca`, `lda`, `lda_subjnorm` and `within_lda` (with its SD over 5 repeats), plus the Mean/SD rows and `Folds`. Never report means only.
- **S3.** In the warm-up table, give per subject and K:
  - warm-up windows, classes, span (s), scored windows and `Std guard` (none in all 20 rows);
  - `full`, `warmup` and `none`, and `warmup − full` with SE_Δ;
  - the cohort table.

  State two facts: K counts trials with at least one valid window, and S04 at K = 1 had 3 windows (1.5 s).
- **S4.** Give PR-1..PR-7 outcomes in SE_Δ units, with the window-level caveat (N6). Also state:
  - PR-2 at the edge (D-3);
  - PR-5's exception with its mechanism open (D-4);
  - that the predictions were written after the builder smokes were seen.
- **S5.** The names run is labelled a 2-subject LOSO with one training subject per fit. It is not compared with the 5-subject runs.
- **S6.** State the regression identity (V7): the P22 refactor leaves `fbcca`, `lda` and `lda_subjnorm` per-window identical to P21's cohort-5 out-dirs.
- **S7.** Acceptance 2: quote the two refusal messages verbatim (`seed`, `hyper`), the unchanged hashes and the 20 `[skip]` lines of the unchanged rerun.
- **S8.** Suite: `1433 passed, 8 skipped` with CUDA hidden; the 8 are the CUDA-only tests (D-1).
- **S9.** Privacy note D-2, written by reference only: "a local tool path, a hit of the guard's term list". Never spell the path or the terms.

## Sources spot-check

The following were opened in this review, and each says what 06 claims:

- `reports/logs/P22/analysis.txt` exists;
- `reports/logs/P22/pytest_full.log`, last line `1433 passed, 8 skipped, 22 warnings in 800.46s (0:13:20)`;
- `reports/loso_warmup/recording_order.csv` (S05 class sequence);
- `reports/loso_w1_p22_common/predictions.csv` (V8 recomputation);
- `reports/loso_w1_p22_all/summary.csv` (PR-2 edge).

`mas/state/scratch/reference_access.log` is still 42 lines, so there was no R11 access.

## Questions

Verdict: APPROVE
