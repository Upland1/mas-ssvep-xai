# P21 · 07 · Scientific review

Status: READY (results review, round 2)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Audited at a3ea7bc: `git diff main -- src scripts tests notebooks configs` (benchmark_loso.py NEW, subject_data.py
MODIFIED, notebooks/loso_colab.ipynb NEW, four NEW and three MODIFIED test files), 00, 02 (settled 1–12, risks, tests,
run commands, measured runtimes, budget), the three 03 handoffs, 04, RULES R1/R2/R5/R8/R9, PF-31..PF-37, PF-40, R-16,
decisions.md P21 rows. Era C: no legacy behaviour is prescribed, so every rule below is enforced.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | The outer split is the subject: `scripts/benchmarks/benchmark_loso.py:191-195` (`loso_split` + `assert_no_shared_trials` on the subject index). Trial ids and `cv_groups` are offset by `10_000 × subject index` (`:161-163`), and the code raises if an id reaches the offset (`:154-156`). The inner validation is `StratifiedGroupKFold` over the offset training groups (`src/models/cnn/training.py:79-85,104-106`). Held-out groups are asserted absent from training (`benchmark_loso.py:244`) and from `val_idx` (`:247`). Registered in `LEAK_FREE` (`tests/test_no_leakage.py:71-73`). Mutants M1, M5, M16 and M19 are killed (04_tests.md). |
| R2 Fit only in-fold | PASS | CSP is fitted on `csp_bands[tr]` only (`:215`). The test rows are only transformed (`:217`). Scaler and LDA live in one Pipeline fitted on `ftr` (`:222-223`). Network mean/std come from `X[fit_idx]` (`training.py:107`), and early stopping uses training-subject windows only. FBCCA has no fit (`:228-232`). The held-out labels are used only for scoring (`:339`, `:374-377`). The sentinel tests (lda, lda_subjnorm, ccnn) leave every fitted parameter bit-identical (`tests/test_p21_loso.py:222`; independent tests 04 §sentinel). Mutants M3 and M7 are killed; M17 is equivalent, because the Pipeline refits its scaler. |
| R2 exception: `lda_subjnorm` | PASS | `subject_zscore` (`:200-207`) takes no labels. Each subject's own mean/std is computed over all its clean stimulus windows, and the training subjects are normalised the same way (`:219-220`). Label: `METHOD_LABELS` "unsupervised per-subject normalization" (`:85`) in Method; `SUBJNORM_NOTE` "test-time, offline upper bound" in the log (`:538`) and in the fold config (`:308-309`). The label-permutation test leaves the probabilities bit-identical (independent test `labels_of_the_held_out_subject`), and the class-centred mutant M2 is killed. CSV rows carry the label but not "whole session"; the scribe must state it (note 4). |
| R3 Filter continuous, then window | PASS | The data come only from `load_subject` on `w1_s0.25` continuous builds. FBCCA comes from the saved continuous `fbcca` bank (`benchmark_window_sweep.py:97-101`) and CSP from the saved `fbcsp` bank (`:333`). No filtering is done in the harness. |
| R4 Estimator small-sample bias | N/A | No coherence/PLV estimator. |
| R5 Shared quality decision, explicit thresholds | PASS | `load_subject(..., "shared", thresholds=..., channel_fail_fraction=...)` gets all four thresholds and the fail fraction explicitly from the config (`:496,502-503,524-526`). `channels=` changes only the returned channels: `valid_mask` and `quality["channels_kept"]` stay the gate's (`src/io/subject_data.py:185-190,228`). With `--channels all`, a gate-dropped channel enters without its own window check. This is stated in the `Channels` cell (`:387`) and is acceptable as a labelled sensitivity mode. |
| R6 Index layouts verified | PASS | Pooled row alignment and the subject-index order are tested (`pool_assigns_subject_index...`). The `[sel][:, :, kept_idx, :]` channel selection is tested with a planted 80 µV channel through the real build (`tests/test_p21_loso.py:368`) and with planted drops (independent test, real build). Chunked CSP transform: `lda_loso_fold` equals the window-sweep `lda_fold` numerically (`:78`). |
| R7 Honest statistics | N/A | No hypothesis test. The R-16 directions are descriptive sign counts (predictions below). |
| R8 Smoothing respects trials | PASS | One fold holds one subject. `smooth_two_tap` sorts by (trial, offset) with `lexsort((offset, trial_id))`, smooths with `smooth_probabilities_by_trial` (reset on id change) and restores the row order (`:361-368`). The stored trial ids are the subject's own (`:339`). The shuffle-invariance test and the raw-id cross-subject mutant are covered (M4, M10). |
| R9 Per-subject reporting with data source | PASS | Per-subject rows plus Mean/SD with ddof 1 (`:399-410`). `Data source` names the build, session, cohort size and range, LOSO and channel mode (`:549-550`). `per_subject.csv` holds Acc and 2-tap. LOSO is 1 s only by the roadmap, so the 2.0 s smoothed cell is out of scope and the report must say so (note 4). |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | Handoffs cite RULES, PF-31..37/40, the P20 decisions and the reused modules. I spot-checked the ITR known value: 48.00 bits/min at acc 0.8, N 5, T 1.5 s (04 §Sources). |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | No external code copied. |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | All four handoffs say "none". The last entries of `mas/state/scratch/reference_access.log` are from P18/P19 (2026-10-28 07:41, scribe P19); there is no P21-era access. |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | N/A | No legacy behaviour in P21. |
| Tests cover every change; at least one fails on the historical bug | PASS | PF-33 (no offset collides), PF-32 (validation from the held-out subject), PF-35 (label-using normalizer), PF-34 (union of channels), PF-37 (config ignored) and R8 all have killed mutants (18/19 killed, 04_tests.md). Gap: the `channels=` error paths of `load_subject` (unknown name, legacy folder) are untested (note 6). |
| P20 C-1 hash pins: test-only, model code unchanged | PASS | `git diff main --stat -- src/models src/preprocessing tests/p05_synth.py` is empty. I re-derived the hash on this tree, which equals main's model code, at `torch.set_num_threads(1)`: `017ccd7b538abe0932f77a8dd4f84f72ec914f703af738efba93ffe9d0bdd19a`, equal to the new pin (`tests/test_p09_compact_shallow.py:28`). Both tests pass at `OMP_NUM_THREADS=1` and `16` (`2 passed` each). The 12-thread values are kept as a tolerance check (`:29-33`). |
| P20 C-2 degenerate flag | PASS | `is_degenerate` (`:262-266`) is written to `folds.csv` for network rows only (`:443`) and printed (`:590-592`). `fit_network`'s stopping rule is unchanged. |
| Resumable folds and config refusal (PF-37) | PASS | Atomic `.tmp` + `os.replace` (`:284-294`). The config is compared before every skip (`:558-566`) and again when the summary is rebuilt (`:426-432`). The default is to refuse; refusal-by-default is the accepted deviation (decisions.md P21 row 3). `git_head` and `data_root` are ignored in the comparison (`:96`): see note 2 and binding item B10. |
| Channels `common`/`all` and fbcca LOSO = within | PASS (with a caveat for the results review) | `choose_channels` (`:123-137`) refuses differing montages and an empty `common`. I checked the per-window identity read-only on the builder's smoke (`mas/state/scratch/p21_loso_c5/predictions.csv`) against P20 `reports/window_sweep/predictions.csv` (1 s, fbcca). 0 mismatches for S01, S03, S04, which drop PO7 like `common`. 55 mismatches for S02 and **7 mismatches for S05**, whose gate kept 8 channels. S05's LOSO accuracy nevertheless equals its within accuracy (95.43 = 95.43). So equal accuracy does not show equality; the check must be per-window predictions on matched channels (P1). |
| ITR | PASS | Wolpaw, N = K = 5, T = window + `GAZE_SEC` 0.5 (`:384`), computed on unsmoothed accuracy. Tested (M9). |
| Notebook (PF-40) | PASS | It installs `pip install -q pyyaml joblib` only (cell 10). It clones fresh with `rm -rf` and `--depth 1 --branch` (cell 8); `rm -rf` does not follow the Drive symlinks. Raw data, built windows, `reports` and `outputs/models` are symlinked to Drive (cell 12). Folds are resumable, and the advice to use a new `LOSO_OUT` per configuration is given (cell 5). The runtime is released (cell 26). The settings cell prints only folder names and `MISSING` lines, and no cell prints recording content. The notebook is committed without outputs, and the CLI lines are checked against the real parsers (`tests/test_p21_notebook.py`). It has never run on Colab (acceptance item 3: human run). |
| Changes match 02_plan.md and the roadmap tasks | PASS | P21.1–P21.3 and C-1/C-2 are done. Three deviations are recorded and accepted: refusal by default, fbcca checked on matched channels only, and `load_subject(channels=)`. The notebook deviations are a processed-folder symlink, `window_sweep_colab` and a per-`LOSO_OUT` models directory. They are sound and close PF-40 more tightly. |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | **FAIL** | `git grep -il` with the vendor/tool name built from fragments finds exactly one hit on HEAD and none on main: **`mas/state/decisions.md`**, P21 row "B003 resolved by Sebastian…". Its Sources cell reads "B003, 03_ROADMAP P21, \<local instructions file name\> compute rules". That file name contains the tool name, and the file itself is excluded from the public repository. No data, recording file or local tooling folder is in `git diff main --name-only`, and commit messages have 0 hits. |

### Required fixes

1. **orchestrator** (privacy; project rule that no tool or vendor name appears in committed files): in `mas/state/decisions.md`,
   the P21 row beginning "B003 resolved by Sebastian: option B", in the Sources column, replace the local-instructions
   file name with `AGENTS.md compute rules` (or `mas/README.md compute rules`). Commit it as a `docs:` fix. Round 2 is a
   re-scan only: `P1="clau""de"; P2="anthrop""ic"; git grep -il "$P1\|$P2" HEAD -- .` must print nothing.

No builder fix is required. The code, tests and notebook pass.

### Non-blocking notes

1. **Within vs LOSO channel confound.** The within references (P20 `reports/window_sweep`, `reports/nn_sweep`, and
   command 5) use each subject's own gate channels; LOSO uses one cohort list. In cohort 5, S02 and S05 kept 8
   channels and `common` has 7 (PO7 out; `windows_meta.json` channels_dropped: S01/S03/S04 `['PO7']`, S02/S05 `[]`). The S02
   fbcca shift from the channel change alone is 68.01 − 64.60 = +3.41 pp. Direction checks therefore use **matched
   subjects only** (P2). Binding item B4 adds the cheap cohort-5 `--channels all` run, so that S02 and S05 also get a matched
   comparison. P22 `within_lda` closes the gap.
2. **Fold integrity across code revisions.** `git_head` is ignored when folds are reused (`:96`). On Colab the notebook
   clones the moving `BRANCH` head each session, so a 12.5 h `compact_eegnet` run that spans sessions can mix code
   revisions without a warning. Binding item B10 checks this in the results review. For P22, consider a `COMMIT` setting
   in the notebook, or refusing a `src/`/`scripts/` change between `git_head`s.
3. **Fold config lacks the build signature.** The config records `quality: "shared"`, but not the folder's
   `build_params` (quality source, banks, guard). A Drive folder rebuilt with other parameters at the same path would
   pass the comparison, guarded only by `n_windows_test`. B6 checks every subject's build signature read-only. P22 could store a hash of each
   subject's `build_params`.
4. **For the scribe (R2(c), R9).** `lda_subjnorm` statistics come from each subject's whole session: all clean
   stimulus windows (shared `valid_mask` and codes 101–105), with no labels. The training subjects are normalised the same way.
   It is an offline upper bound, not an online method (P22 warm-up). LOSO is 1 s only (roadmap), so there is no 2.0 s smoothed
   cell. The Colab comparison table (cell 24) uses unsmoothed `Acc (%)`, and the 2-tap values are in `per_subject.csv`.
5. **Network `Val Acc` is not a LOSO estimate.** The validation windows come from the training subjects, which is
   correct by PF-32. The builder smoke shows val 95.6–97.9 % against S01 test 57.9–71.3 %. The scribe must not read the gap
   as overfitting, and the val accuracy must not be quoted as generalisation.
6. **Test gap.** `load_subject(channels=[unknown])` and `channels=` on a legacy folder raise by inspection
   (`subject_data.py:131-132,186-188`) but have no test. Low risk; P22 can add two `pytest.raises` lines.
7. **Human-run hand-back.** Notebook cell 25 and data-signal manual step 7 ask for `summary.csv`, `per_subject.csv`
   and `folds.csv` only. The results review needs the whole `LOSO_OUT` folder, including `folds/*.npz` (configs, git heads)
   and `predictions.csv` (B11).
8. **Cohort naming.** B003 describes the raw folders as "S01–S040, including S020". `check_subject_names` sorts
   numerically and refuses only true number collisions (S10 with S010). The original's LOSO cohort had 39 subjects without
   S020, but R-16 has no numeric target, so this matters only for the scribe's wording.

### Binding run-list items for the verifier (copy verbatim into 02_plan.md)

B1. **Pre-state.** `reports/loso_w1_s01-s05`, `reports/loso_w1_s01-s05_all`, `reports/loso_w1`,
`reports/loso_w1_fbcca_all` and `reports/window_sweep_w1_all` must be absent before their commands run (stale-fold rule).
Hash of the S01–S05 built folders before command 1 and after the last command, with exactly this command:
`find data/processed_continuous/w1_s0.25/S0[1-5] -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`.
The pinned value at a3ea7bc is `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4` (65 files). Before and after must
both equal it.

B2. **Cohort gate.** Command 1's last lines (`Cohort: N subjects built (...)`, `[-] Skipping <S>: <reason>`) are quoted
verbatim in 05_run.md. If N = 5, commands 5, 6, B5 and 7 are **not run locally**; they join the human-run request, and
the phase is reported as `PASS (partial; human run pending)`. Command 6 must never run on a 5-subject root, because it
would write a duplicate cohort-5 table labelled as the full cohort. Every skipped subject and its reason goes into the report.

B3. **Cohort-5 classical reproduces the builder smoke.** `Acc (%)` of `reports/loso_w1_s01-s05/summary.csv` for fbcca, lda
and lda_subjnorm, S01–S05, must equal `mas/state/scratch/p21_loso_c5/summary.csv`. fbcca: 58.68, 68.01, 91.07, 98.80, 95.43.
lda: 69.26, 76.24, 96.07, 99.55, 96.91. lda_subjnorm: 74.85, 83.07, 95.61, 99.70, 96.91. A difference larger than 1 window per subject
is a stop, to be explained before any interpretation.

B4. **Cohort-5 `--channels all` (≈ 11 s).**
`$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --subjects S01 S02 S03 S04 S05 --methods fbcca lda lda_subjnorm --channels all --out-dir reports/loso_w1_s01-s05_all`

B5. **Full cohort fbcca with `--channels all` (only if N > 5; seconds to minutes).**
`$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods fbcca --channels all --out-dir reports/loso_w1_fbcca_all`.
The full classical `--channels all` run (≈ 35 min) is required only if fewer than 50 % of the full-cohort subjects have gate-kept
channels equal to `common`. It is run locally if the remaining budget allows, otherwise it joins the human-run request,
into `reports/loso_w1_all`.

B6. **Channel and build record.** For every cohort, copy from the harness log the `Channels (...)` line and every
`[+] <S>: ... gate kept [...]` line. Then list, read-only from each `windows_meta.json`, `fs`, the `quality.source` (it must be
`both` for every subject) and `channels_dropped`. Count the subjects whose gate-kept list equals `common` and those equal to the
full montage.

B7. **Real interrupt (acceptance 2).** Run command 3 under `timeout -s INT 300`. Then list `folds/*.npz` (count k)
and confirm that no `*.tmp` is left. Rerun command 3 to completion: exactly k `[skip]` lines, then the rest computed.
After that, run command 4 (rerun command 2). Hash the four CSVs **after command 3 completes and after command 4** with
`sha256sum reports/loso_w1_s01-s05/{summary,per_subject,predictions,confusion}.csv`; the hashes must be equal.
Command 4 rebuilds the summary from all folds, networks included, so the "before" hash is the one taken after
command 3, not after command 2. `folds.csv` is excluded (wall-clock `Seconds`).

B8. **Within reference consistency (only if command 5 runs).** The S01–S05 rows of `reports/window_sweep_w1_all/summary.csv`
(1 s, fbcca and lda: `Acc (%)` and `Acc SD`) must equal the P20 `reports/window_sweep/summary.csv` 1 s rows exactly. fbcca:
58.68, 64.60, 91.07, 98.80, 95.43. lda: 75.88, 77.36, 97.31, 99.79, 99.09. A difference is a stop: the folders or the code changed.

B9. **Budget and stop rules.** Classical runs use `CUDA_VISIBLE_DEVICES=""` (acceptance 1). For command 6: if the
mean time of the first 3 `lda` folds is above 60 s (the builder projected ≈ 22 s), stop with Ctrl-C after a fold line,
because the folds resume. The remainder joins the human-run request, with the measured time per fold. Command 3 (≈ 15 min
GPU) and the B7 interrupt stay well inside `MAX_GPU_HOURS_PER_PHASE` 2. Command 7 is always a human run. The suite runs alone
and records `torch.get_num_threads()` (P20 C-1).
*Optional* D1, only if ≥ 40 min of budget remain after the binding items: cohort-5 `ccnn eegnet` with `--seed 43` and
`--seed 44` (≈ 11 min GPU), each in its own out-dir `reports/loso_w1_s01-s05_seed<k>`. Without D1, P21 makes no ranking
claim between networks and classical methods (P20 C-3).

B10. **Fold integrity (results review, every out-dir).** For each fold `.npz`: `config.train_subjects` excludes
`test_subject`; `n_train` = (sum of the cohort's test windows) − `n_windows_test`; the set of `git_head` values is reported.
If there is more than one, `git diff --stat <h1> <h2> -- src scripts` must be empty, otherwise the table mixes code revisions.

B11. **Human-run request content.** The request asks Sebastian to return the whole `LOSO_OUT` folder (including
`folds/`, `predictions.csv`, `confusion.csv`, `loso_config.json`) and `window_sweep_colab/`. They go into
`reports/loso_w1_colab/` and `reports/window_sweep_colab/`, never into a local out-dir. The data source of these rows
says "Colab build" (the Colab session builds its own windows from Drive).

### Pre-registered directional predictions for the results review (copy verbatim into 02_plan.md)

The cohort-5 classical and S01-network smoke numbers were seen before these predictions (03 handoffs), so the cohort-5
items are consistency checks; the full-cohort items are blind. "Matched" = a subject whose within run used the same
channels as the LOSO run: cohort 5 `common` → S01, S03, S04; `all` → S02, S05; full cohort per B6.

- **P1 (identity, bug check).** For every matched subject, the LOSO `fbcca` per-window predictions are identical to the
  within `fbcca` predictions of the same subject, with 0 mismatches. This is joined on (subject, trial_id, offset_sec) of the two
  `predictions.csv`. A mismatch on a matched subject is a bug (FAIL), not a deviation. Equal accuracy is not evidence
  (S05: 7 mismatches at equal 95.43 %). Expected for cohort 5: S01/S03/S04 from command 2, S02/S05 from B4.
- **P2 (LOSO below within, trained methods).** This is judged on matched subjects for `lda` (against within `lda`) and for
  each network (against the P20 `reports/nn_sweep` 1 s value of the same network, cohort 5 only). Holds if the matched-subject
  mean LOSO < the within mean, **and** LOSO ≤ within + 1 pp in ≥ 80 % of matched subjects. Ties at the ceiling count as
  holding. Any matched subject with LOSO `lda` > within `lda` + 5 pp triggers the B10 audit and is reported as
  "unexplained", never tuned.
  For `lda_subjnorm` (transductive), LOSO above within on a matched subject is reported but is not a violation. In
  the smoke, matched S01/S03/S04 are below within for both methods; unmatched S02 lda_subjnorm is 83.07 vs within 77.36.
- **P3 (`lda_subjnorm` ≥ `lda`, same run, same channels).** Holds if the cohort mean Δ = subjnorm − lda ≥ 0 **and**
  at most 20 % of subjects have Δ < −2 pp. Smaller negative Δs are within-noise ties. Example: smoke S03 −0.46 pp = 3.04
  windows of 661 (shown command: `(96.07-95.61)/100*661`). Basis: per-subject z-scoring removes subject gain and offset, which
  LOSO cannot learn; the smoke Δ was +5.59, +6.83, −0.46, +0.15, 0.00 (mean +2.42).
- **P4 (networks, cohort 5).** 0 degenerate folds for `ccnn` and `eegnet` (smoke S01: best epochs 31 and 44, train ≥ 98 %).
  Any degenerate fold (`compact_eegnet` included) is reported per fold. It stays in the table but is excluded from P2's sign
  count for that network.
- **P5 (exploratory, full cohort, no consequence).** The S01–S05 rows of the full-cohort LOSO `lda` (39 training subjects) are compared
  with the cohort-5 values (4 training subjects) only if `common` is the same 7 channels. Expected: mean ≥ the cohort-5 mean
  − 2 pp. If channels differ, the comparison is not made.
- **Consequence rule.** A failed P2/P3 is not a FAIL by itself (R-16 has no numeric target). It must be reported per subject as
  "direction not observed". It is explained only by a mechanism shown in the data (channel mismatch, degenerate fold,
  B10 finding), and no setting is changed afterwards (golden rule 5). A failed P1 or B3/B8 is a stop.

Verdict: FAIL

## Pre-run audit — Round 2

Re-checked at e214117 (after ec48847 "docs: P21 decisions source name" and e214117 "chore: P21 pre-run checks in plan").

| Check | Result | Evidence |
|---|---|---|
| Required fix 1 (privacy) | PASS | `P1="clau""de"; P2="anthrop""ic"; git grep -il "$P1\|$P2" HEAD -- .` prints nothing. Commit messages 7facac5..HEAD: 0 hits. The B003 P21 row's Sources cell now reads "B003, 03_ROADMAP P21, AGENTS.md compute rules" (`git diff 7facac5 HEAD -- mas/state/decisions.md`). |
| No code changed | PASS | `git diff 7facac5 HEAD --stat` touches only `mas/state/decisions.md`, `02_plan.md` and `log.md`. src/, scripts/, tests/, notebooks/ and configs/ are unchanged, so the round-1 code verdicts stand. |
| B1–B11 and P1–P5 copied verbatim into 02_plan.md | PASS | Each of the 76 non-empty, non-heading lines of this review, from "B1. **Pre-state.**" to the round-1 verdict, appears verbatim in `02_plan.md`: 0 missing, checked with a shown Python substring comparison. The plan diff deletes no lines. |
| New decisions.md row | PASS | The round-1 outcome row names the file only as "the local instructions file". |

Verdict: PASS

## Results review

Reviewed at c9b30d1 (`phase/P21-loso-colab`). Read in full: 02_plan.md (settled 1–12, B1–B11, P1–P5, consequence
rule), 05_run.md (cohort-5 run, "Full cohort — part 1", "part 2 (stopped)"), 06_verify.md (`Verdict: PASS`, f22bafa),
log.md, decisions.md P21 rows 158–163. Outputs read: `reports/logs/P21/` (`full_part1_checks.txt`,
`full_part2_checks.txt`, `loso_w1_ccnn.log`, `build_windows_human.log`), `summary.csv`, `predictions.csv`, `folds.csv`
and `folds/*.npz` of `reports/loso_w1{,_all,_fbcca_all,_s01-s05,_s01-s05_all,_s01-s05_seed43,_s01-s05_seed44}/`,
`reports/window_sweep_w1_all/`, and the 39 `windows_meta.json` of `data/processed_continuous/w1_s0.25/` (built folders,
read-only; nothing under the raw-data folder was touched). Code since the pre-run audit: `git diff --stat 8cfa30b HEAD --
src scripts tests configs notebooks` is empty (9 commits, documentation only), so the pre-run code verdicts stand.

### Independent re-computations (read-only, `.venv/bin/python -c ...` in this session)

| Check | Result |
|---|---|
| P1, cohort 39 | Join of `loso_w1_all` fbcca with `window_sweep_w1_all` fbcca (1 s) on (subject, trial_id, offset_sec): 24497/24497 rows joined; **0 mismatches on the 32 subjects with `channels_dropped == []`**; unmatched S01 59, S03 14, S04 2, S013 15, S019 94, S040 54, S029 0. Equals `full_part1_checks.txt`. |
| P2 `lda`, cohort 39, `all` | Matched 32: mean LOSO 85.67 vs within 86.51 (−0.84, `python3 -c "print(round(85.67-86.51,2))"`); LOSO ≤ within + 1 pp in 22/32 (68.8 %); max S015 +4.94. Sign tally of LOSO − within: 15 positive, 17 negative, median −0.30. Equals the verifier. |
| P3 | `loso_w1`: mean Δ +2.62, 0 subjects < −2 pp; `loso_w1_all`: S039 the only one below −2 pp (verifier: −2.99). Mean rows match `summary.csv`. |
| Cohort-39 ccnn | 39 folds; mean 71.58 vs lda 72.54 (−0.96); ccnn > lda in 19/39; S015 29.66 vs 56.13 (−26.47). S015 ccnn is not a collapse: predictions spread over all 5 classes (crosstab of `predictions.csv`, diagonal 27/38/53/16/33), best epoch 13, train 77.11 %, val 74.85 % (`folds.csv`), not degenerate by the P20 C-2 rule. |
| B10 | Every fold of the 7 out-dirs: `test_subject` ∉ `train_subjects` (0 violations). `git_head` sets: `loso_w1` classical f0fa371 only; ccnn S01–S04 f0fa371, S05–S040 da92a47 (35); eegnet 2 × da92a47; all cohort-5 out-dirs e349656 only. `git diff --stat f0fa371 da92a47 -- src scripts tests configs notebooks` is empty; `git diff --stat e349656 f0fa371 -- src scripts configs tests` is empty. |
| Build provenance | `windows_meta.json` `git_commit`: S01–S05 5d9326d (P20 build), S06–S040 **605ce52** (34 folders, meta mtimes 18:47:27–18:48:01, about 1 s apart, one invocation). `build_params` equal to S01's in 34/34. `git diff --stat 5d9326d 605ce52 -- src scripts/build_windows.py configs` = `src/io/subject_data.py` only (the `channels=` read option of `load_subject`; `build_windows.py` imports only `built_dir_name` from it). No two subjects share a `X_raw_windows.npy` sha256 (39 distinct). fs 256.0 in 39/39. |
| Cohort-5 seeds | Per-subject range over seeds 42/43/44: ccnn 0.30–5.12 pp, eegnet 0.30–8.23 pp (S02). eegnet below cohort-5 `lda` (seed-independent) in all three seeds on S01, S02, S03, S05; above on S04 (99.85 mean vs 99.55). ccnn below `lda` in all seeds on S02, S03, S05. Cohort means minus lda 87.61: ccnn −1.44/−2.25/−1.03 (mean −1.57), eegnet −7.85/−9.03/−8.84 (mean −8.57) (shown command: `python3 -c` over the six means). |

### Deviations from references

R-16 has no numeric target (direction only, `mas/04_REFERENCE_RESULTS.md` R-16). The rows below are the pre-registered
checks and the plan items that did not run as written.

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| B3 | cohort-5 classical = builder smoke | 21 rows, max abs diff 0.0 (`b3_compare.txt`) | 0 | yes | — | — |
| B8 | S01–S05 within rows = P20 | 10/10 equal, Acc and Acc SD (`full_part1_checks.txt`) | 0 | yes | — | — |
| R-16 / P1 fbcca LOSO = within | 0 mismatches on matched subjects | cohort 5: 0 on S01/S03/S04 (`common`) and S02/S05 (`all`); cohort 39: 0 on 32 (`all`) | 0 | yes | negative controls discriminate (238 mismatches on 6/7 unmatched) | — |
| R-16 / P2 lda, cohort 5 | matched mean below, ≥ 80 % at ≤ +1 pp | 86.63 vs 89.89; 5/5 (`p2p3p4_b10.txt`) | −3.26 | holds | — | — |
| R-16 / P2 lda, cohort 39 | as above | 85.67 vs 86.51; 22/32 = 68.8 % (`full_part1_checks.txt`) | −0.84 mean; 10 subjects > +1 pp | **direction not observed** | no mechanism shown in the data (no channel mismatch on matched subjects, no degenerate fold, B10 clean) | D-4 |
| R-16 / P2 networks, cohort 5 | matched below within (P20 `nn_sweep`) | ccnn 3/3, compact_eegnet 3/3, eegnet 3/3 (`p2p3p4_b10.txt`) | −0.30 to −23.83 | holds | compact_eegnet single seed (D-7) | — |
| R-16 / P2 networks, cohort 39 | — | not evaluable: no within network on POz/PO4/O1 | — | — | D-6 | D-6 |
| R-16 / P3 subjnorm ≥ lda | mean Δ ≥ 0, ≤ 20 % below −2 pp | c5 common +2.42 / 0 %; c5 all +2.41 / 0 %; c39 common +2.62 / 0 %; c39 all +2.72 / 2.6 % | — | holds (4/4) | — | — |
| P4 degenerate folds | 0 for ccnn/eegnet cohort 5 | 0 in every network out-dir, incl. ccnn cohort 39 (`full_part2_checks.txt`) | 0 | holds | — | — |
| P5 | only if `common` = 7 channels | `common` = 3 channels | — | not evaluable | rule | D-2 |
| Cohort size (plan: 40) | 40 discovered subjects | 39 built; S020 skipped "all channels dropped (source=both)" (`build_windows_human.log`) | −1 | — | shared gate decision (R5) | D-1 |
| Command 1 provenance | S06–S040 built by command 1 | folders pre-existed (605ce52, 18:47–18:48, no project log); `--resume` printed `[=]` for 39 | — | — | see D-3 evidence | D-3 |
| Command 7 (networks, cohort 39) | ccnn, compact, eegnet on 39 | ccnn 39/39; eegnet 2/39 (stopped); compact 0 | — | — | Sebastian's instruction, decisions.md row 163 | D-6 |
| HR-3 exit code | captured | not captured; log ends `Saved:`, 117 folds, B10 clean | — | — | tool backgrounding | D-8 |
| Budget | ≤ 120 min local, ≤ 2 GPU-h | part 1 ≈ 36 min CPU + cohort-39 networks 19:37–21:19 ≈ 1.7 h GPU (ccnn 39 folds, eegnet 2), beyond the cohort-5 46 min | — | — | Sebastian's authorisation, decisions.md row 162 | D-9 |

### Interpretation check

1. **`common` = 3 channels on cohort 39 (item 1).** The intersection of gate-kept channels over 39 subjects is POz, PO4, O1
   (`loso_w1_classical.log`); 0/39 subjects ran their within reference on those channels and 32/39 kept all 8. Therefore:
   - every `reports/loso_w1/` row (fbcca, lda, lda_subjnorm, ccnn) must be worded "cohort-39 LOSO on 3 channels (POz, PO4,
     O1), the cohort intersection of gate-kept channels". It is **not** comparable to any within value (no subject is
     matched), nor to the cohort-5 `common` rows (7 channels), nor to `loso_w1_all`. The mean drop against within
     (e.g. lda 72.54 vs 84.76) mixes the subject shift with a channel loss of 5 channels and must not be called a LOSO
     generalisation gap;
   - the comparable classical cohort-39 result is `reports/loso_w1_all/` (8 channels, gate channel drops ignored),
     judged against within on the 32 matched subjects only. For the 7 unmatched subjects (S01, S03, S04, S013, S019,
     S029, S040) the `all` run includes gate-dropped channels that have no per-window check of their own (pre-run R5 row);
     their LOSO − within differences are reported per subject as "unmatched channels";
   - the 3-channel `common` default is a consequence of the cohort's union of drops (S013 PO8, S019 PO3+PO8, S029 O2,
     S040 Oz, S01/S03/S04 PO7), not a choice made after seeing results (log.md "HR-4 running"). No sentence may imply the
     channel set was selected.
2. **P2 `lda`, cohort 39 (item 2).** The pre-registered wording "direction not observed" is correct and is the only
   allowed summary. The mean condition holds (85.67 < 86.51) and the ≥ 80 % condition fails (22/32). No subject exceeds
   within + 5 pp, so the B10 "unexplained" trigger did not fire and B10 is clean anyway. The consequence rule forbids an
   explanation without a mechanism shown in the data; none is shown. The scribe may state, as **untested hypotheses**
   only: (a) within `lda` trains on about 4/5 of one subject's windows while LOSO trains on 38 subjects (about 24 k
   windows; `folds.csv` Train windows), and the two subjects whose within `lda` is at or below their own fbcca (S015 47.46
   vs 51.15; S040 47.56 vs 50.00) are low-SNR cases where more training data could matter; (b) the +1 pp margin is smaller
   than the window-level binomial SE of a single LOSO accuracy (0.65–2.10 pp on the 10 subjects above +1 pp; computed
   `sqrt(p(1−p)/n)`), which itself understates the error because windows of one trial overlap by 75 %. Signs are 15
   positive / 17 negative, median −0.30, so the cohort-39 result does not show LOSO above within either. Forbidden
   wordings: "LOSO matches/exceeds within", "LOSO generalises as well as within-subject", "P2 holds". A post-hoc,
   unregistered observation, labelled as such if used: on the same 8 channels, S01–S05 `lda` LOSO moves from the cohort-5
   mean 86.34 to the cohort-39 mean 87.92 (+1.58; S02 70.03 → 81.06), consistent with hypothesis (a) but not a test of it;
   it is **not** P5. Carry-forward C-3.
3. **ccnn cohort 39 (item 3).** Acceptable as an extra data source: "cohort-39 LOSO ccnn, 3 channels (POz, PO4, O1), seed
   42, one fit per held-out subject". It is descriptive only: no within network reference exists on these channels (P2
   not evaluable), it is a single repeat (P20 C-3: S015 −26.47 pp against lda is a single-repeat cell far larger than 5 pp,
   so no claim about S015 or about ccnn vs lda on cohort 39 is allowed), and the ccnn − lda mean −0.96 with 19/39
   subjects above lda is a tie by any reading. S015 is not a degenerate fold (best epoch 13, train 77.11 %); report it
   per subject without a cause. Train accuracy ≈ 75–78 % on pooled 38-subject training windows is not a degenerate flag and
   must not be read as underfitting or overfitting (pre-run note 5 on `Val Acc`). The 2 eegnet folds (S01, S02) are not a
   result: they are absent from `summary.csv` (rebuilt 21:02:41 by the ccnn run) and must not be quoted. compact_eegnet
   was not run on cohort 39.
4. **Provenance of S06–S040 (item 4). Acceptable with disclosure; no rebuild is required.** Evidence beyond the
   verifier's `--resume` line: the meta `git_commit` of all 34 folders is 605ce52, a committed revision of this branch;
   the build code at 605ce52 equals the P20 build revision 5d9326d except for the read-only `channels=` option of
   `load_subject`, which the writer does not call; `build_params` equal S01's in 34/34; the 34 meta files were written
   about 1 s apart in one 34-s span, consistent with a single `build_windows` invocation; no two subjects share a raw-window
   hash, so no subject is a duplicate of another (a duplicate would leak in LOSO); the within and LOSO runs read the same
   folders (P1 0 mismatches on 32). What cannot be verified: who ran the build and whether the working tree was clean at
   605ce52. The disclosure (D-3) must say "built at 18:47–18:48 by an invocation not logged by the project; meta
   git_commit 605ce52; build parameters and build code identical to S01–S05". A rebuild into a fresh root with a byte
   comparison is needed only if a later phase reuses the cohort-39 folders (B003 amended: P22–P23 use S01–S05, whose
   hash pin e7f55081 held before and after every part).
5. **B10 git_head mix in ccnn (item 5). Not a code mix.** `loso_w1_ccnn.log` holds one `LOSO: methods ['ccnn']` header,
   39 `[+]` and 0 `[skip]` lines: it was **one** invocation. `git_head()` is called per fold at fold start
   (`scripts/benchmarks/benchmark_loso.py:103-105,322`) on the live main tree, and commit da92a47 (19:42:40) was made
   while fold S04 was training (S04 saved 19:44:57, head f0fa371). The code in memory was f0fa371's for all 39 folds, and
   the diff to da92a47 is documentation only. The verifier's phrase "resumed from the earlier launch" (06_verify.md
   part 2, B10 row) is inaccurate; the scribe uses this item's wording. The lesson is C-1: a per-fold head read from a
   working tree that receives commits does not identify the code that ran, in either direction.
6. **Cohort-5 networks (item 6).** All three networks use `common` = 7 channels, the same as cohort-5 `lda`, so the
   network-vs-classical comparison is channel-matched. Allowed wording per P20 C-3:
   - ccnn (3 seeds): cohort mean 86.04 vs `lda` 87.61 (−1.57; per seed −1.44/−2.25/−1.03). This is a tie inside the
     per-subject seed range (up to 5.12 pp); no ranking between ccnn and `lda`. ccnn is below `lda` in every seed on
     S02, S03 and S05; this may be stated per subject.
   - eegnet (3 seeds): below `lda` in every seed at cohort level (−7.85 to −9.03) and on S01, S02, S03, S05 in every seed;
     "eegnet LOSO is lower than lda LOSO on cohort 5 (3 seeds)" is allowed. Per-subject single-seed magnitudes are not
     interpreted (eegnet S02 seed range 8.23 pp).
   - compact_eegnet (seed 42 only): reported per subject; its P2 direction holds on 3/3 matched subjects, but no ranking
     against any method and no magnitude interpretation (S01 −23.83 vs within is a single-repeat cell > 5 pp).
   - `lda_subjnorm` (90.03) is transductive (whole-session test-time statistics, offline upper bound) and is never
     ranked against inductive methods without that label.
   - Network `Val Acc` (training subjects) is not a LOSO estimate (pre-run note 5).
7. **R9 per subject with data source (item 7).** Every LOSO out-dir has one row per held-out subject plus Mean and SD
   (ddof 1), with `Acc (%)` (the 1.0 s window) and `2-tap Smoothed (%)` (the project's "2.0 s decision" smoothing,
   `mas/02_REQUIREMENTS.md` §5.6, within trial). LOSO is 1 s only by the roadmap; no 2.0 s-window cell exists for any
   cohort, and the report must say so rather than call the 2-tap column a 2.0 s window. Within cohort 39
   (`window_sweep_w1_all`) is 1 s only; S06–S040 have no 2-tap within value in P21. The `Data source` cell of the
   cohort-39 CSVs reads "cohort 39 subjects (S01-S040)": the report must add "without S020 (skipped: all channels
   dropped)" because the range alone suggests 40. Every cohort-39 number in 05_run.md that I re-derived (P1, P2, P3,
   ccnn means, per-subject table spot rows S02, S015, S039) matches the CSVs. Data sources to name, one per table:
   cohort 5 `common` 7 ch; cohort 5 `all` 8 ch; cohort 5 seeds 43/44; cohort 39 `common` 3 ch; cohort 39 `all` 8 ch;
   cohort 39 fbcca `all`; within cohort 39 (`window_sweep_w1_all`, own gate channels, 5 × 5 grouped CV for lda, fbcca once);
   within cohort 5 (P20 `window_sweep`, `nn_sweep`).
8. **Leakage.** No fit sees the held-out subject (B10 in 7 out-dirs; pre-run R1/R2 rows), CSV labels are used only for
   scoring, validation is drawn from training subjects (PF-32). `lda_subjnorm` statistics: each subject's whole session
   of clean stimulus windows, no labels (R2 exception (a)–(c); the report must say "whole session = offline upper bound").
   No stale fold: the four classical/network out-dirs were absent before their commands (B1, HR-0).

### Required fix (blocking)

1. **verifier** (privacy, project rule: no tool or vendor name in committed files; acceptance item 7). `06_verify.md`
   lines 115–117 ("Privacy scan" of the first section, committed in 89bb7d4) spell out the vendor and tool names that the
   scan searched for. `main` has 0 such hits; this branch has exactly this one file. Replace the three term lists by
   "searched for the guard's vendor/tool term list (built from fragments)" and commit as `docs:`. Round 2 is a re-scan only:
   `P1="clau""de"; P2="anthrop""ic"; git grep -il "$P1\|$P2" HEAD -- .` must print nothing. No result or number changes.

### Accepted deviations (D-n)

- D-1. Cohort 39 (S01–S040 without S020), not 40: S020 skipped by the shared gate ("all channels dropped
  (source=both)"). Every cohort-39 table says "39 subjects, S01–S040 without S020".
- D-2. Cohort-39 `common` = POz, PO4, O1 (0/39 matched, 32/39 full montage). `loso_w1_all` is the comparable classical
  cohort-39 result (32 matched subjects); `loso_w1` rows are 3-channel results, not comparable to within or to cohort 5.
  P5 not evaluable by its own rule.
- D-3. S06–S040 built folders pre-existed the verifier's `--resume` (meta git_commit 605ce52, 18:47:27–18:48:01, no
  project log). Accepted with disclosure: build parameters equal (34/34), build code equal to the P20 build revision except
  the read-only loader option, 39 distinct raw-window hashes, S01–S05 hash pin unchanged. A rebuild is required only if a
  later phase reuses these folders.
- D-4. P2 for `lda` on cohort 39: "direction not observed" (22/32 ≤ within + 1 pp; mean 85.67 vs 86.51; max S015 +4.94;
  signs 15+/17−). No mechanism shown; nothing changed; hypotheses labelled untested (interpretation item 2).
- D-5. B10 `git_head` mix in `loso_w1` ccnn (S01–S04 f0fa371, S05–S040 da92a47): one invocation, per-fold head read on a
  tree that received a documentation commit mid-run; code identical. Not a mixed-code table.
- D-6. Cohort-39 networks limited by Sebastian's instruction (decisions.md row 163): ccnn 39/39 kept as an extra
  descriptive data source (3 channels, single repeat, no within network reference, P2 not evaluable); eegnet 2/39 not a
  result; compact_eegnet not run.
- D-7. compact_eegnet cohort 5 has one seed (D1 was optional and covered ccnn and eegnet only): no ranking or magnitude
  claim for compact_eegnet.
- D-8. HR-3 exit code not captured; completeness established from the log (`Saved:`), 117 fold files and B10.
- D-9. Local budget exceeded for the full-cohort part under Sebastian's authorisation (decisions.md row 162);
  config.yaml unchanged.

### Carry-forward lessons (C-n, for P22–P23 on S01–S05)

- C-1 (ml-engineer, verifier). Record `git_head` once at process start (and a dirty-tree flag), not per fold; run long
  jobs from the clean verifier worktree, never from a tree that receives commits. P22's `check_fold` refuses folds whose
  heads differ in `src/` or `scripts/`.
- C-2 (verifier, ml-engineer). `reports/loso_w1/folds/` holds 2 eegnet folds. Any rerun of the harness on that out-dir
  rebuilds `summary.csv` with an eegnet Mean over 2 subjects under a "cohort 39" data source. Never rerun into
  `reports/loso_w1`; P22 summaries must flag or refuse a method whose fold count is below the cohort size.
- C-3 (orchestrator, reviewer). Directional predictions in P22–P23 state their margin in units of the noise of the
  compared quantity (trial-level, or at least the binomial SE of each accuracy, 0.65–2.10 pp here), not a fixed 1 pp.
  P22 `within_lda` on exactly the LOSO channels (settled 11) is the matched comparison for S01–S05; matched sets for
  cohort 5 are `common` → S01, S03, S04 and `all` → S02, S05.
- C-4 (deep-learning, verifier). Network comparisons in P22–P23 use ≥ 3 seeds per network (P20 C-3); the cohort-5
  per-subject seed range (ccnn ≤ 5.12 pp, eegnet ≤ 8.23 pp) is the noise floor for any per-subject network claim.
  compact_eegnet needs seeds 43/44 before any ranking.
- C-5 (verifier). Any built folder that a phase uses but did not create with a logged command is recorded with its meta
  `git_commit`, a `build_params` equality check, a duplicate-subject hash check, and the code diff to the reference
  build revision — or rebuilt in the run.
- C-6 (verifier). Privacy-scan descriptions name the term list by reference ("guard term list, built from fragments"),
  never by the terms themselves.

### Binding items for the scribe

S1. Every cohort-39 `common` row is labelled "3 channels (POz, PO4, O1), cohort intersection; not comparable to within or
to cohort 5"; `loso_w1_all` is the cohort-39 classical comparison, on 32 matched subjects.
S2. P2 `lda` cohort 39 is written "direction not observed" with 22/32, 85.67 vs 86.51, S015 +4.94, and the hypotheses
of interpretation item 2 only as untested; none of the forbidden wordings.
S3. Cohort-39 ccnn is "extra data source, descriptive, single repeat"; no ccnn-vs-lda claim on cohort 39; S015 reported
without a cause; the 2 eegnet folds are not quoted.
S4. Disclosures D-3 (provenance, with the evidence of item 4) and D-5 (one invocation, doc-only head change; not
"resumed from the earlier launch").
S5. Cohort-5 networks worded per interpretation item 6 (ccnn ≈ lda; eegnet lower in 3 seeds; compact_eegnet single seed,
no ranking).
S6. R9: per-subject rows for every cohort and method, `Acc (%)` and the 2-tap column named "2-tap smoothed (within
trial)", no 2.0 s-window cell; data source per table as in item 7, with "39 subjects, without S020"; `lda_subjnorm`
labelled "unsupervised per-subject normalization, test-time, whole session = offline upper bound".
S7. Every number with its CSV/log path (`full_part1_checks.txt`, `full_part2_checks.txt`, out-dir `summary.csv`).

### Decisions for decisions.md

- P21 results review: D-1..D-9 accepted as listed in 07_review.md (results review); P2 `lda` cohort 39 "direction not
  observed", no setting changed; cohort-39 `common` rows are 3-channel results; S06–S040 provenance accepted with
  disclosure (no rebuild unless reused).
- P21 carry-forwards C-1..C-6 to P22–P23 (S01–S05): git_head at process start and clean worktree; partial eegnet folds
  in `reports/loso_w1`; noise-sized prediction margins and `within_lda` on LOSO channels; ≥ 3 network seeds; provenance
  record for unlogged built folders; privacy-scan wording.

### Sources spot-check

- `mas/04_REFERENCE_RESULTS.md` R-16: direction only, no numeric target (as cited in 06_verify.md "Sources spot-check").
- `mas/02_REQUIREMENTS.md:179` §5.6 "Smoothing (2.0 s decision)": 2-tap within trial; supports item 7's naming.
- decisions.md rows 162 (local run authorisation) and 163 (networks on cohort 5; B003 amended for P22–P23): quoted
  correctly by 05_run.md and 06_verify.md.
- `scripts/benchmarks/benchmark_loso.py:103-105,322`: `git_head()` = `git rev-parse HEAD` at fold-config time.
- R11: `mas/state/scratch/reference_access.log` 42 lines, last 2026-10-28T07:41 (P19 scribe); no P21 access. I did not
  open the reference folder.
- Privacy: 1 hit on HEAD (06_verify.md, required fix 1); commit messages 8cfa30b..HEAD 0 hits.

Reason: step 8 (verifier), 06_verify.md lines 115–117, privacy fix 1 only. All scientific items are accepted as
D-1..D-9; round 2 is a re-scan.

Verdict: REJECT

## Results review — Round 2

Re-checked at b01e9fb (after 61131b9 "docs: P21 verify wording" and b01e9fb "chore: P21 log verify wording fix").

| Check | Result | Evidence |
|---|---|---|
| Required fix 1 (privacy) | PASS | `P1="clau""de"; P2="anthrop""ic"; git grep -il "$P1\|$P2" HEAD -- .` prints nothing. Commit messages 1cf6e06..HEAD: 0 hits. `06_verify.md` privacy lines now read "searched for the guard's vendor/tool term list (built from fragments)" and "no local-instruction files, tool directories, `data/` or recording files". |
| D-5 wording | PASS | `05_run.md` part 2 B10 line now says "one invocation, a documentation commit landed mid-run" instead of "resumed from the earlier launch", as interpretation item 5 requires. |
| Scope of the change | PASS | `git diff --stat 1cf6e06 HEAD` touches only `05_run.md` (1 line), `06_verify.md` (3 lines) and `log.md` (2 rows). No code, test, config, notebook or result changed (`git diff 1cf6e06 HEAD -- src scripts tests configs notebooks` is empty), so the results review of round 1 stands: D-1..D-9, C-1..C-6, S1–S7 unchanged. |

Verdict: APPROVE

## Questions
