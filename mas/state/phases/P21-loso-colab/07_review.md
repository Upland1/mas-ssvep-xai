# P21 · 07 · Scientific review

Status: READY (pre-run audit, round 1)
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
