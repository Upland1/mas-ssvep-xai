# P21 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify/P21` @ e349656ad8cbc78c1e68dfe3212b2a3bc551dcc1 (removed after the run)

Verdict: PASS

Scope. Cohort 5 (S01-S05) is verified in full. The 40-subject cohort is not available (command 1 printed `Cohort: 5 subjects built (S01, S02, S03, S04, S05), 0 skipped (none)`, B2), so commands 5, 6, B5 and 7 are a human-run request (`05_run.md`, section "Human run requests"). No stop condition fired (P1, B3 pass; B8 does not apply because command 5 did not run).

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests/ -q -o addopts=""     # alone, nothing else running
```

`1360 passed, 22 warnings in 783.33s (0:13:03)`, exit 0 (`reports/logs/P21/pytest_full.log`). `torch.get_num_threads()` = 12 (same log, line 2). Count equals the synthetic-tester's figure (04_tests.md: 1360 passed).

## Acceptance

| # | Criterion | Re-run command | Obtained | Met? | Log |
|---|---|---|---|---|---|
| 1 | Classical LOSO runs end-to-end on CPU | command 2 with `CUDA_VISIBLE_DEVICES=""` | exit 0, 15 folds, 8.92 s wall, peak RSS 633960 KB; B3 identical to the builder smoke (max abs diff of `Acc (%)` over 21 rows = 0.0) | yes (cohort 5; cohort 40 pending) | `loso_cmd2.log`, `b3_compare.txt` |
| 2 | Interrupt and rerun skips finished folds | `timeout -s INT 300` on command 3; rerun; command 4 | after the interrupt 6 network folds + 15 classical on disk, 0 `.tmp`; rerun printed exactly 6 `[skip]`; command 4 printed 15 `[skip]`; the four CSV hashes after command 3 equal those after command 4 | yes | `loso_cmd3a_interrupted.log`, `loso_cmd3b_resume.log`, `loso_cmd4_rerun.log`, `hash_after_cmd3.txt`, `hash_after_cmd4.txt` |
| 3 | Notebook structure tests pass; Colab manual steps documented | included in the full suite (`tests/test_p21_notebook.py`, 8 tests) | pass; manual steps in `03_changes_data-signal.md` and `05_run.md` HR-4. The notebook was not run on Colab (no access; human run) | yes for the structure; top-to-bottom T4 run pending (human) | `pytest_full.log` |
| 4 | Within vs LOSO per subject and as cohort mean, with data source | tables below | cohort 5 done (`built continuous folders processed_continuous/w1_s0.25, session OO, cohort 5 subjects (S01-S05)`); cohort 40 pending | yes for cohort 5; pending for cohort 40 | `reports/loso_w1_s01-s05*/summary.csv` |
| 5 | R-16 directions | P1-P3 below | all hold on cohort 5 | yes for cohort 5 | `p1_p2_calc.txt`, `p2p3p4_b10.txt` |
| 6 | S01-S05 built folders unchanged; suite alone, threads recorded | B1 hash | before and after both `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4` (65 files); suite passed alone, 12 threads | yes | `hash_before.txt`, `hash_after.txt` |
| 7 | R11 log and privacy scan clean | below | clean | yes | below |

## Within vs LOSO, cohort 5 (acceptance 4)

Data sources. LOSO: `built continuous folders processed_continuous/w1_s0.25, session OO, cohort 5 subjects (S01-S05), LOSO, channels common` (7 channels PO3, POz, PO4, PO8, O1, Oz, O2) or `channels all` (8 channels), window 1 s, stride 0.25 s, seed 42, 1 run per held-out subject. Within: P20 `reports/window_sweep/summary.csv` (lda, 5-fold x 5 repeats, trial-grouped; fbcca) and `reports/nn_sweep/summary.csv` (networks), 1 s rows, continuous build, each subject on its own gate-kept channels. Accuracies are unsmoothed `Acc (%)`; LOSO 2-tap values are in `summary.csv`. Matched = same channels in both runs (S01, S03, S04 for `common`; S02, S05 for `all`; plan P-section). Source: `p2p3p4_b10.txt`, `p1_p2_calc.txt`.

| Subject | within fbcca | LOSO fbcca (common / all) | within lda | LOSO lda (common / all) | LOSO lda_subjnorm (common / all) |
|---|---|---|---|---|---|
| S01 | 58.68 | 58.68 / 55.88 | 75.88 | 69.26 / 67.65 | 74.85 / 73.24 |
| S02 | 64.60 | 68.01 / 64.60 | 77.36 | 76.24 / 70.03 | 83.07 / 78.73 |
| S03 | 91.07 | 91.07 / 90.77 | 97.31 | 96.07 / 96.07 | 95.61 / 95.46 |
| S04 | 98.80 | 98.80 / 99.10 | 99.79 | 99.55 / 99.70 | 99.70 / 99.70 |
| S05 | 95.43 | 95.43 / 95.43 | 99.09 | 96.91 / 98.23 | 96.91 / 96.61 |
| Mean | 81.72 | 82.40 / 81.16 | 89.89 | 87.61 / 86.34 | 90.03 / 88.75 |
| 2-tap mean | | 82.72 / 81.25 | | 88.64 / 87.29 | 90.75 / 89.84 |

Cohort SD (LOSO, common, `Acc (%)`): fbcca 17.91, lda 13.84, lda_subjnorm 10.62.

Networks, LOSO `common`, seed 42, vs P20 within (`nn_sweep`, 1 s, own channels):

| Subject | ccnn LOSO / within | compact_eegnet LOSO / within | eegnet LOSO / within |
|---|---|---|---|
| S01 | 71.76 / 80.29 | 60.29 / 84.12 | 57.94 / 77.94 |
| S02 | 71.27 / 77.02 | 63.35 / 77.48 | 70.50 / 71.43 |
| S03 | 91.38 / 99.24 | 85.02 / 98.94 | 87.44 / 99.24 |
| S04 | 99.70 / 100.00 | 99.55 / 99.85 | 99.70 / 100.00 |
| S05 | 96.76 / 99.71 | 87.33 / 100.00 | 83.21 / 99.85 |
| Mean | 86.17 / 91.25 | 79.11 / 92.08 | 79.76 / 89.69 |
| 2-tap mean (LOSO) | 88.31 | 80.19 | 80.47 |

S02 and S05 are unmatched for networks (LOSO 7 channels vs within 8 channels).

## Binding items B1-B11

| Item | Result |
|---|---|
| B1 | Pre-state clean (no `loso_w1*`, `window_sweep_w1_all` before the commands). Hash before = after = pinned value, 65 files. PASS |
| B2 | `Cohort: 5 subjects built (S01, S02, S03, S04, S05), 0 skipped (none)`. Commands 5, 6, B5 and 7 not run; command 6 never ran on this root. Human-run request written. Skipped subjects: none. PASS (branch taken: N = 5) |
| B3 | 21 summary rows, max abs diff of `Acc (%)` against `mas/state/scratch/p21_loso_c5/summary.csv` = 0.0. fbcca 58.68, 68.01, 91.07, 98.80, 95.43; lda 69.26, 76.24, 96.07, 99.55, 96.91; lda_subjnorm 74.85, 83.07, 95.61, 99.70, 96.91. PASS |
| B4 | `--channels all` ran (exit 0, 12 s); `Channels (all): PO7, PO3, POz, PO4, PO8, O1, Oz, O2 (gate channel drops ignored)`. Used for P1 on S02/S05. PASS |
| B5 | Not run (N = 5); human-run request HR-2 |
| B6 | Recorded in `05_run.md`: fs 256 and `quality.source` both for all five; gate-kept equals `common` in 3 subjects (S01, S03, S04), equals the full montage in 2 (S02, S05). 3/5 = 60 % >= 50 %, so the full classical `--channels all` run is not required by the rule (and N = 5 anyway). PASS |
| B7 | Real interrupt at 300 s: 6 network folds on disk, 0 `.tmp`; rerun skipped exactly 6; four CSV hashes after command 3 equal those after command 4. PASS |
| B8 | Not applicable (command 5 did not run). Pending for the human run (post-run check 2) |
| B9 | Classical runs with `CUDA_VISIBLE_DEVICES=""`; suite alone, `torch.get_num_threads()` = 12. Command 6 not run (no first-3-folds time to measure; the cohort-5 `lda` folds took 0.6-0.7 s each, `folds.csv`). Local time about 46 min of 120; GPU about 0.53 h of 2. D1 executed (more than 40 min remained). PASS |
| B10 | Out-dirs `loso_w1_s01-s05` (30 folds), `_all` (15), `_seed43` (10), `_seed44` (10): in every fold `test_subject` is not in `train_subjects`; for every (method) `n_train` = (sum of the cohort's test windows) - `n_windows_test` (`True` for all methods and out-dirs); `git_head` set = {e349656ad8cbc78c1e68dfe3212b2a3bc551dcc1} in every out-dir (one revision, no diff needed). PASS |
| B11 | Written into the human-run request (whole `LOSO_OUT` and `window_sweep_colab/` into `reports/loso_w1_colab/` and `reports/window_sweep_colab/`; data source "Colab build"). PASS |

## Pre-registered predictions (cohort 5; consistency checks, the smoke numbers were seen first)

- **P1 (identity, bug check). HOLDS.** Join on (subject, trial_id, offset_sec) of LOSO `fbcca` `predictions.csv` and the P20 within `fbcca` predictions (1 s): S01 680/680 rows joined, 0 mismatches; S03 661/661, 0; S04 665/665, 0 (all `common`); S02 644/644, 0; S05 679/679, 0 (both `all`, B4). True labels agree on every joined row. Negative control (unmatched channel set) mismatches: S02 55 and S05 7 with `common`; S01 59, S03 14, S04 2 with `all`, so the test discriminates. Source `p1_p2_calc.txt`.
- **P2 (LOSO below within, trained methods). HOLDS on matched subjects.**
  - `lda` (S01, S03 common; S02, S05 all; S04 common; all five matched): matched mean LOSO 86.63 vs within 89.89; LOSO - within = -6.62, -7.33, -1.24, -0.24, -0.86 (S01..S05); 5/5 subjects at LOSO <= within + 1 pp; no subject above within + 5 pp, so no B10 "unexplained" trigger.
  - `ccnn` (S01, S03, S04): matched mean 87.61 vs 93.18; deltas -8.53, -7.86, -0.30; 3/3.
  - `compact_eegnet`: matched mean 81.62 vs 94.30; deltas -23.83, -13.92, -0.30; 3/3.
  - `eegnet`: matched mean 81.69 vs 92.39; deltas -20.00, -11.80, -0.30; 3/3.
  - Unmatched network subjects (S02, S05) also have LOSO below within (deltas -0.93 to -16.64). `lda_subjnorm` above within on unmatched S02 (83.07 vs 77.36) is reported, not a violation (transductive, unmatched channels).
- **P3 (`lda_subjnorm` >= `lda`). HOLDS.** `common`: deltas +5.59, +6.83, -0.46, +0.15, 0.00; mean +2.42; 0 % of subjects below -2 pp. `all`: +5.59, +8.70, -0.61, 0.00, -1.62; mean +2.41; 0 % below -2 pp. Source `p2p3p4_b10.txt`.
- **P4 (networks, degenerate folds). HOLDS.** 0 degenerate folds for ccnn, compact_eegnet and eegnet in `folds.csv` (best epochs: ccnn 31, 47, 46, 18, 19; compact_eegnet 70, 88, 91, 96, 38; eegnet 44, 137, 88, 102, 79; train accuracy >= 96.33 % everywhere). Seeds 43 and 44: 0 degenerate folds each.
- **P5 (exploratory, full cohort).** Not evaluable (N = 5). Human-run post-check 5.

D1 (P20 C-3, `--seed 43` and `44`, `reports/loso_w1_s01-s05_seed43`, `_seed44`; the harness `Acc (%)` per subject, S01..S05):

| Method | seed 42 | seed 43 | seed 44 | cohort mean 42 / 43 / 44 | spread of means |
|---|---|---|---|---|---|
| ccnn | 71.76, 71.27, 91.38, 99.70, 96.76 | 69.12, 67.24, 94.55, 99.55, 96.32 | 72.65, 72.36, 92.59, 99.40, 95.88 | 86.17 / 85.36 / 86.58 | 1.22 pp |
| eegnet | 57.94, 70.50, 87.44, 99.70, 83.21 | 61.18, 62.27, 86.69, 100.00, 82.77 | 58.24, 65.37, 83.36, 99.85, 87.04 | 79.76 / 78.58 / 78.77 | 1.18 pp |

Per-subject range across seeds is up to 8.2 pp (eegnet S02: 62.27 to 70.50) while the cohort-mean spread is about 1.2 pp. Reference for ranking: classical LOSO `lda` mean 87.61 and `lda_subjnorm` 90.03 vs `ccnn` mean over three seeds 86.04 and `eegnet` 79.04. This is reported, not interpreted (P20 C-3 satisfied for ccnn and eegnet; `compact_eegnet` has a single seed).

## Numbers in the handoffs vs logs

Every number in 05_run.md and in this file comes from `summary.csv`, `folds.csv`, `loso_config.json` of the out-dirs above, from the logs in `reports/logs/P21/`, or from the shown scripts (`mas/state/scratch/p21_verify/p1p2p3.py`, `p2p3b10.py`; outputs saved as `p1_p2_calc.txt` and `p2p3p4_b10.txt`). Means of three seeds: 86.04 = (86.17 + 85.36 + 86.58) / 3 and 79.04 = (79.76 + 78.58 + 78.77) / 3 as printed by `p2p3p4_b10.txt`. Builder figures: suite time 788.91 s (data-signal) and 787.55 s (tester) vs 783.33 s here; classical LOSO 11.7 s (plan) vs 8 s here (script runtime). The builders' 15-min cohort-5 network estimate vs 773.66 s (command 3b, with 6 folds already done) plus about 300 s in 3a, about 18 min in total, is consistent.

## Sources spot-check

- `mas/04_REFERENCE_RESULTS.md` R-16 (line 303): "Era C (P16-P23): no preserved numbers ... no numeric target: run them, record them, and have the Reviewer check direction". Matches the plan's use (direction only).
- `mas/05_PITFALLS.md` PF-35 (line 180): `lda_subjnorm` is transductive and must be labelled "unsupervised per-subject normalization". Matches: the label appears in `summary.csv`, `per_subject.csv`, `folds.csv` and the console.

## Reference consultations check

`03_changes_ml-engineer.md`, `03_changes_deep-learning.md`, `03_changes_data-signal.md`: all "None". `mas/state/scratch/reference_access.log` has 42 lines; the last entries are dated 2026-10-28T07:06 and 07:41 (P19/P18 reviewer, verifier and scribe), none after the P21 branch work and none from this run (`awk` on timestamps after 2026-10-28T08 returned nothing). The verifier did not open `reference/`. No unlisted access. PASS

## Privacy scan

- Commit messages of `main..HEAD` (22 commits): `git log main..HEAD --format='%an|%ae|%cn|%B'` searched for claude, anthropic, co-authored, assistant, generated: 0 hits.
- Added lines of `git diff main...HEAD` (24 files, 3340 insertions) searched for claude, anthropic, co-authored, noreply@, copilot, chatgpt, openai: 0 hits.
- Changed paths of the branch diff contain no `CLAUDE`, `.claude/`, `data/` or recording files: 0 hits.
- This verification commit stages only `05_run.md` and `06_verify.md`.

## Human-run section

Pending (see `05_run.md`, "Human run requests" HR-0 to HR-4, with exact commands for the local terminal and for the Colab notebook, expected runtimes, the note that Sebastian must push the branch for Colab, the B11 drop locations and the post-run checks). Required to close the full-cohort rows: S06-S40 raw data in place, then commands 1, 5, 6, B5 and 7. Nothing in the cohort-5 results is changed by them; the 40-subject rows will be a separate data source (B003 option B).

## Reasons (if FAIL)

None. The partial status is only the unavailable cohort (B2).

---

# Full cohort — part 1 (appended 2026-10-28)

Verdict stays `PASS (partial; network run in progress)`: no stop condition failed. Details, commands, exit codes, times and the per-subject table (cohort 39 subjects, S01-S040 without S020) are in `05_run.md`, section "Full cohort — part 1". Analysis script `mas/state/scratch/p21_verify/full1.py`, output `reports/logs/P21/full_part1_checks.txt`.

| Item | Result |
|---|---|
| HR-0 / B2 | `Cohort: 39 subjects built (...), 1 skipped (S020)`; S020 "all channels dropped (source=both)". N = 39 > 5, gate opened. The S06-S040 folders pre-existed (mtime 18:47-18:48, built outside this run); `--resume` confirmed identical build parameters. |
| B1 hash | `e7f55081...bebab4` before and after part 1. PASS |
| B8 | 10/10 S01-S05 fbcca and lda rows (Acc and Acc SD) equal to P20. PASS |
| P1 (stop condition) | 32 matched subjects (gate-kept = full montage), `loso_w1_fbcca_all` and `loso_w1_all`: 0 prediction and 0 label mismatches; negative control 238 mismatches in 6 of 7 unmatched subjects. HOLDS |
| B6 / B5 | `common` = POz, PO4, O1; 0 of 39 equal `common`, 32 of 39 equal the full montage; < 50 % so the full classical `--channels all` run was required and done (`reports/loso_w1_all`). |
| B9 | First 3 `lda` folds 6.1, 6.0, 7.0 s (limit 60 s): no stop. `CUDA_VISIBLE_DEVICES=""` on all classical commands. Budget beyond `LOCAL_RUN_BUDGET_MIN` used under Sebastian's authorisation. PASS |
| B10 (classical) | No test subject in train_subjects; n_train identity True; one git_head f0fa371 per out-dir; one fold config per out-dir. PASS. Networks pending. |
| P2 `lda` (32 matched, all channels) | Mean LOSO 85.67 < within 86.51 but only 22/32 (68.8 %) at LOSO <= within + 1 pp (rule: >= 80 %): **direction not observed**. No subject > within + 5 pp, no B10 audit trigger. Reported per subject in `05_run.md` item 5, not a FAIL (consequence rule), no setting changed. |
| P3 | `common` mean delta +2.62, 0 % below -2 pp; `all` +2.72, 2.6 % (S039 -2.99). HOLDS |
| P5 | Not evaluable: `common` is 3 channels, not the cohort-5 7. |
| Privacy | This commit stages only `05_run.md` and `06_verify.md`. |

Reasons (if FAIL): none so far. Open: HR-4 networks (ccnn, eegnet, compact) running as PID 3604944; P2 for networks (against P20 `nn_sweep` is cohort-5 only, so the full-cohort network P2 reference must be a within network run on the same channels, not available), P4 degenerate folds, network B10 and post-run 6 will be added when `mas/state/scratch/p21_hr4/DONE` exists.

---

# Full cohort — part 2 (stopped) (appended 2026-10-28, verifier)

Final verdict: `Verdict: PASS` (line 8). Networks are judged on cohort 5 per Sebastian's decision (decisions.md P21 row, 2026-10-28). Numbers, table and commands: `05_run.md`, section "Full cohort — part 2 (stopped)"; script `mas/state/scratch/p21_verify/full2.py`, output `reports/logs/P21/full_part2_checks.txt`. No training run was started in this step.

| Item | Result |
|---|---|
| Stop left no `.tmp` or partial fold | PASS: empty list; folds fbcca/lda/lda_subjnorm/ccnn 39 each, eegnet 2 (not a result), compact_eegnet 0 |
| `summary.csv` provenance | last rebuilt 21:02:41 by the ccnn run (exit 0 at 21:02:44); methods fbcca, lda, lda_subjnorm, ccnn; no eegnet rows |
| B10 on ccnn cohort 39 | PASS: 0 test-in-train, n_train identity True, one fold config; git_head 35 x da92a47 and 4 x f0fa371, diff between them is documentation only |
| P4 | PASS: 0 degenerate folds for ccnn cohort 39 (0 with best epoch <= 5, 0 with train acc < 30 %) and for ccnn, eegnet, compact_eegnet cohort 5 (seeds 42/43/44 included) |
| Post-run check 6 (C-3), descriptive | ccnn 71.58 vs lda 72.54 vs lda_subjnorm 75.16 vs fbcca 64.56 (cohort 39, 3 common channels); single repeat, no ranking claim |
| Network P2 cohort 39 | not evaluable (no within network reference on those channels) |
| Stop conditions P1, B3, B8 | met in part 1 (P1 0 mismatches on 32 matched subjects; B3 hash equal; B8 10/10 equal); nothing in part 2 changes them |
| Acceptance items 1-7 | met: cohort-5 items verified in the first section (tests, runs, networks on cohort 5 with D1 seeds), classical full cohort in part 1, ccnn cohort 39 here as an extra data source |

Open (non-blocking, recorded): P2 `lda` direction on the full cohort was not observed by the pre-registered rule (22/32 at LOSO <= within + 1 pp; part 1), reported without changing settings; P5 not evaluable; eegnet and compact_eegnet on cohort 39 not run by decision.

Reasons (if FAIL): none.
