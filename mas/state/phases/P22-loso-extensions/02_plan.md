# P22 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Make the LOSO comparison matched and online-realistic:

- a within-subject LDA on exactly the LOSO channels (`within_lda`);
- explicit channel lists;
- a resume guard that refuses mixed configurations;
- a warm-up study: normalize a new subject from its first K unlabeled trials only.

## Data source

- Built folders `data/processed_continuous/w1_s0.25/<S>/`, session OO, `--quality-source both`,
  `--banks fbcca fbcsp`.
- These are the P20/P21 folders, unchanged; their S01–S05 hash pin is `e7f55081…bebab4`.
- **Cohort S01–S05 only** (B003 as amended by Sebastian, 2026-10-28). The subject list is
  explicit in every command (`--subjects S01 S02 S03 S04 S05`); the folder also holds
  S06–S040.

## Settled points (inferred; recorded in decisions.md)

1. **`within_lda`.**
   - Per subject: `StratifiedGroupKFold(5, shuffle=True, random_state=42+r)` over true trial
     ids, r = 0..4 (`--folds 5 --within-repeats 5`).
   - Same features and pipeline as LOSO `lda`: CSP m = 1 per band, fitted in-fold, plus
     FBCCA, then scaler, then shrinkage-LDA.
   - It uses **exactly the channel list of the LOSO run** (`common`, `all` or names).
   - It reports mean and SD over repeats.
   - Saved folds: `within_lda__test-<S>.npz`, with a config like the other methods.
   - With `common` it is the matched comparison for every subject (P21 C-3).
2. **`--channels <names>`.**
   - Any argument other than `common`/`all` is a list of montage names, and it is validated
     against the montage.
   - Subjects whose gate dropped any named channel are left out. The script prints
     `[-] Leaving out <S>: gate dropped <channels>`, and for the others what the gate
     dropped.
   - Fewer than 2 remaining subjects is an error.
   - The order of the names is kept as given; folds record the list.
3. **Fold config and `check_fold` (PF-37, P21 C-1).**
   - `git_head` and a dirty-tree flag are recorded **once at process start**.
   - The config stores channels, train subjects, window, stride, method hyperparameters,
     seed, folds/repeats, git head and dirty flag.
   - `check_fold` refuses any difference outside `data_root` with the message
     "configuration differs …; use a new --out-dir".
   - A different `git_head` is refused only when `git diff --stat <h1> <h2> -- src scripts`
     is non-empty. A head that git cannot resolve is refused.
   - `--allow-config-mismatch` is **removed**, since the roadmap says "refuses". The
     accepted P21 deviation ends here.
4. **Fold-count guard (P21 C-2).** The summary flags any method whose number of fold files
   is below the cohort size (`Folds` column plus a `[warn]` line). By default it refuses
   to write a cohort Mean for that method (`Mean` left empty, flagged).
5. **Warm-up (`benchmark_loso_warmup.py`, PF-35, PF-36).**
   - Recording order of the held-out subject's trials = sort by each trial's **first window
     start in samples on the continuous recording**. If built folders store only per-trial
     offsets, the builder derives absolute starts from the stored metadata, proves it with a
     test, and records the source. Never use the trial id.
   - For K ∈ {1, 2, 5, 10}:
     - The first K trials are the warm-up. Their features are used **without labels** to
       compute mean/std.
     - Only trials after K are scored, under three normalizations:
       - `full`: whole-session stats of the held-out subject, i.e. `lda_subjnorm`;
       - `warmup`: first-K stats;
       - `none`: plain `lda`.
     - All three are scored on the same windows.
   - Training subjects are normalized with their own whole-session stats, as in
     `lda_subjnorm`.
   - Model: CSP + scaler + LDA fitted once per held-out subject on the training subjects
     (the same fit as LOSO `lda`/`lda_subjnorm`). Only the test normalization changes.
   - Output `reports/loso_warmup/summary.csv` with the §6 columns (`Subject, Warm-up trials,
     Warm-up windows, Warm-up classes, Warm-up span (s), Scored windows, full (%),
     warmup (%), none (%)`), plus a cohort table with `warmup − full`.
   - Zero or one warm-up window gives std 0. It is guarded (std floor or fallback), and the
     guard is reported.
6. **Smoothing and ITR** are as in P21: 2-tap within trial, N = 5, T = 1.5 s. The warm-up
   table reports unsmoothed accuracy; smoothed accuracy goes in a separate column if cheap.
7. **Prediction margins (P21 C-3).** Directional statements use the binomial SE of each
   accuracy (per subject, from its scored windows) as the noise unit, not a fixed 1 pp.

## Work split

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | ml-engineer | MODIFIED `scripts/benchmarks/benchmark_loso.py`, NEW `scripts/benchmarks/benchmark_loso_warmup.py`, NEW `tests/test_p22_loso_extensions.py`, `tests/test_p22_warmup.py`; MODIFIED P21 tests only where the removed flag is used | P22.1–P22.4; settled 1–6 |

The builder smoke-runs on synthetic data and on S01–S05 (under 5 min) with measured times, and runs the full suite alone (≈ 14 min).

## Methodological risks

| Rule / PF | Risk | Guard |
|---|---|---|
| R1 | `within_lda` folds split a trial | grouped by true trial ids; test with overlapping windows |
| R2 / PF-35 | warm-up statistics use labels or post-K windows | test: permuting labels of warm-up trials and altering post-K windows leaves warm-up stats unchanged |
| PF-36 | warm-up uses class order instead of recording order | planted recording order differing from id order; known first-K set |
| PF-37 | resumed folds from another config/code | refusal test per config key and for a src change between heads |
| PF-34 | explicit names silently keep a subject missing a channel | planted gate drop; subject left out and printed |
| R9 | cohort mean only | per-subject rows, Mean/SD, data source |

## Tests required (known answers)

1. `within_lda` on planted synthetic subjects equals an independent grouped-CV LDA computed in the test, and uses the LOSO channel list.
2. Explicit names: a planted gate drop leaves the right subjects out, and the printed line names the dropped channel. An unknown name raises.
3. `check_fold`:
   - every config key change is refused with "use a new --out-dir";
   - a doc-only head change is accepted;
   - a src/scripts head change is refused;
   - the removed `--allow-config-mismatch` flag is rejected by argparse.
4. Fold-count guard: a method with fewer fold files than subjects has no Mean and is flagged.
5. Warm-up:
   - recording-order sort on a planted layout;
   - with K = all trials, `warmup` == `full` exactly, and with no normalization it equals `none`;
   - a gain-shifted held-out subject gives `warmup` ≥ `none` for K large enough (known answer);
   - label invariance of the warm-up stats;
   - std-floor guard for K = 1.
6. Each fix test fails on the bug it guards.

## Run commands (for the verifier; runtimes to be replaced by the builder's measurements)

```bash
P=".venv/bin/python -m"
S="--subjects S01 S02 S03 S04 S05"
# 0. hash S01–S05 built folders (must equal e7f55081…bebab4); out-dirs absent
# 1. LOSO + matched within, common channels (≈ 1–3 min CPU)
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --methods fbcca lda lda_subjnorm within_lda --channels common --folds 5 --within-repeats 5 --out-dir reports/loso_w1_p22_common
# 2. same with all channels
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --methods fbcca lda lda_subjnorm within_lda --channels all --folds 5 --within-repeats 5 --out-dir reports/loso_w1_p22_all
# 3. explicit full montage: keeps only subjects whose gate accepted all 8 (expected S02, S05; printed)
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --methods fbcca lda lda_subjnorm within_lda --channels PO7 PO3 POz PO4 PO8 O1 Oz O2 --folds 5 --within-repeats 5 --out-dir reports/loso_w1_p22_names
# 4. refusal check: rerun 1 with --seed 43 into the same out-dir → must refuse with "use a new --out-dir", exit ≠ 0, no file changed (hash)
# 5. warm-up, common channels
$P scripts.benchmarks.benchmark_loso_warmup --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --warmup-trials 1 2 5 10 --channels common --out-dir reports/loso_warmup
# 6. hash S01–S05 (after)
```

**Budget.** Everything is classical on S01–S05, so minutes on CPU, well within `LOCAL_RUN_BUDGET_MIN` 120. There is no GPU use.

### Pre-run audit additions (07_review.md 581ab9a, round 2 PASS a120f0b; copied verbatim)

#### Pre-registered predictions for the results review (copy verbatim into 02_plan.md)

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

#### Binding run-list items for the verifier (copy verbatim into 02_plan.md)

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

## Acceptance checks (for the verifier)

1. Both scripts run (commands 1–3, 5 exit 0).
2. A changed configuration on an existing out-dir is refused (command 4), and nothing changes in that out-dir.
3. Warm-up table produced and recorded per subject and as a cohort with `warmup − full`.
4. `within_lda` channel list equals the LOSO list in every out-dir. LOSO vs within is reported per subject with the binomial SE (C-3).
5. Explicit-names run prints who is left out and what the gate dropped.
6. S01–S05 hash unchanged; suite passes alone; R11 log; privacy scan (guard term list) clean.

## Sources

- `mas/03_ROADMAP.md` P22.
- `mas/05_PITFALLS.md` PF-34..37.
- `mas/02_REQUIREMENTS.md` §6.
- `mas/04_REFERENCE_RESULTS.md` R-16.
- `mas/state/decisions.md` P21 rows (C-1..C-6, B003 amendment).

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
