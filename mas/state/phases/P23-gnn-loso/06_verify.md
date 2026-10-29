# P23 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (acceptance checks, V1..V12 with the round 2 amended V8/V10, PR-1..PR-9, RR-1..RR-7), 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify/P23` @ a9ba18b230e751de5b590c0f59cfb96311be9c8d (HEAD "chore: P23 pre-run checks in plan"; contains 02_plan.md "Pre-run audit additions"), `git status --porcelain` empty before and after the run.

Verdict: PASS

All numbers below are copied from `reports/logs/P23/analysis.txt`, `rr2_tables.md`, `v8_hashes.txt`, `v12.txt`, `steps.txt` and the CSVs in `reports/within_gnn/` and `reports/loso_gnn/`, unless stated. Where a prediction missed or a binding item deviated, it is stated plainly; none of the misses is an acceptance criterion.

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider    # alone, nothing else running
```

`1513 passed, 22 warnings in 870.26s (0:14:30)`, exit 0 (`reports/logs/P23/pytest_full.log`; 1512 + the F1 test, as in `03_changes_deep-learning.md`). `torch.get_num_threads()` = 12 (`torch_threads.txt`); the GNN runs were pinned to 2 threads and `cpu` in the command and in every fold config.

## Acceptance

| # | Criterion | Re-run command | Obtained | Met? | Log |
|---|---|---|---|---|---|
| 1 | Smoke test: > 40 % mean synthetic LOSO, every fold skipped on rerun, within runs | step 1 | `[smoke] loso: 16 folds run, rerun skipped 16 and ran 0; outputs identical True`; `within: 40 folds run, rerun skipped 40 and ran 0; outputs identical True`; mean synthetic LOSO 87.97 %; `[smoke] PASS`; exit 0, 37 s | yes | `smoke.log` |
| 2 | Within and LOSO tables, both variants, both norms (within pooled only), per subject with data source, Normalization, Protocol | steps 2, 3; tables below | within 2 methods x (5 subjects + Mean + SD), LOSO 4 methods x 7 rows (V3, V7) | yes | `within.log`, `loso.log` |
| 3 | Next to `benchmark_loso.py` rows on the same channels (P22 `loso_w1_p22_common`, P21 networks) | RR-2 tables below | present, same 7 channels | yes | `rr2_tables.md` |
| 4 | Train ~ 100 % / test ~ chance patterns listed per fold (PF-30) | `folds.csv` of both out-dirs | all 70 rows in `05_run.md` (V9); interpretation under PF-30 below | yes | `v9_folds_table.md` |
| 5 | A config change on an existing out-dir is refused; the resume check passes | 8b, 8c, 10b, 8e | unchanged rerun: exit 0, 20 `[skip]`, 0 `[+] gnn_`, six CSV hashes identical; `--seeds 2`: exit 1, "use a new --out-dir" | yes | `loso_rerun_same.log`, `loso_rerun_seeds2.log` |
| 6 | S01-S05 hash unchanged; suite passes alone; R11 log; privacy scan | steps 0, 5, T | `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4` before and after (`cmp` identical, 65 files); suite 1513 passed; R11 and privacy below | yes | `hash_*.txt` |

## Binding items V1..V12

| Item | Result | Evidence |
|---|---|---|
| V1 | met | `reports/loso_gnn` and `reports/within_gnn` absent before step 1 (`v1_ls_before.txt`); `git status --porcelain -- src scripts configs` empty; hash `e7f55081...bebab4` before and after |
| V2 | met | 70 fold configs: threads != 2: 0, device != cpu: 0, git_dirty true: 0; exactly one `git_head` value (a9ba18b230e751de5b590c0f59cfb96311be9c8d). One `GNN within:` header in `within.log` and one `GNN loso:` header in `loso.log`. Suite alone with `torch.get_num_threads()` recorded (12) |
| V3 | met | `folds/`: 50 and 20 npz, 0 `*.tmp`; `folds.csv` 50 and 20 rows; within `summary.csv` 14 rows (2 methods x 7); LOSO `summary.csv` 28 rows (4 x 7); `seeds.csv` 30 and 60 rows, seeds (42, 43, 44) in every (method, subject), 3 rows each |
| V4 | met | for every method and out-dir the `(trial_id, offset_sec)` set equals the P22 `fbcca` set, counts 680 / 644 / 661 / 665 / 679 (6 method-protocol cells, all True) |
| V5 | met, one wording note | LOSO test-S01 pooled and subjnorm: `fs` 256.0; channels PO3, POz, PO4, PO8, O1, Oz, O2; `n_windows_train` {S02 644, S03 661, S04 665, S05 679} = expected; 5 `build_git_commits`; `config_hash` = sha256 of `configs/pipeline_config.yaml`; seeds [42, 43, 44], `val_frac` 0.2, `max_epochs` 150, `patience` 25. Within S01 fold 0: same values with `n_windows_train` {S01: 680} and 1 `build_git_commits` entry (the training subject only; the literal "5 entries" cannot apply to a within fold) |
| V6 | met | max abs(proba - proba_seed.mean(0)) = 0.0 for all 20 LOSO folds of the 4 methods (limit 1e-6) |
| V7 | met | every `_subjnorm` row: Normalization contains "test-time" and "offline upper bound"; pooled rows say "pooled: z-scored with the statistics of the training windows only (R2)"; within Data source contains "within-subject" and not ", LOSO,"; LOSO Data source contains ", LOSO,"; Protocol `within` / `loso` |
| V8 (amended) | met | six-CSV sha256 identical after step 3, 8b, 8c, 10a, 8d, 10b, 8e (table in `05_run.md`); 8b exit 0 with 20 `[skip]`, 0 `[+] gnn_`; 8c exit 1, message contains "use a new --out-dir". Optional interrupt check not done |
| V9 | met | all 70 rows in `05_run.md`; no degenerate row (listed separately: none) |
| V10 (amended) | met after a verifier error | 10b (`--variants nodes+F --norm pooled`): 5 `[skip]`, 0 `[+] gnn_`, no `left out`, exit 0, six CSV hashes equal to the V8 hashes, `summary.csv` holds all 4 methods (28 rows). The first V10 attempt (10a) used both variants by mistake: 10 `[skip]`, no refusal, hashes unchanged (05_run.md Anomalies 1). Final unchanged rerun 8e after 10b: 20 `[skip]`, exit 0, hashes unchanged |
| V11 | met | `reference_access.log`: 42 lines before and after, no line dated 2026-10-29, none naming P23; privacy scan below |
| V12 | done | `cv_groups == trial_ids` is True for S01-S05 (`v12.txt`, windows 680 / 644 / 661 / 665 / 679), so the GNN within test folds coincide with `within_lda` repeat 0 (N9) |

## RR-1 / RR-2 tables (common, 7 channels; "1.0 s / 2-tap smoothed", in %)

Data source of the GNN rows: built continuous folders `processed_continuous/w1_s0.25`, session OO, cohort 5 subjects (S01-S05), channels common. LOSO table: Protocol `loso`; within table: Protocol `within`, Data source "within-subject (trial-grouped CV)". Normalization: pooled rows "pooled: z-scored with the statistics of the training windows only (R2)"; `_subjnorm` and `lda_subjnorm` rows are **test-time normalization, offline upper bound** (the held-out whole session is in the statistics; R2 exception, PF-35); there is no online GNN claim (RR-3). In parentheses: per-seed mean of the 1.0 s accuracy and seed range (`seeds.csv`) for the GNN; seed range for P21 networks over seeds 42/43/44 (`loso_w1_s01-s05`, `_seed43`, `_seed44`); `compact_eegnet` is a single seed. P22 rows from `reports/loso_w1_p22_common/summary.csv` (`within_lda` = 5 split repeats, relabelled within-subject, N4/N9).


| Method | S01 | S02 | S03 | S04 | S05 | Mean |
|---|---|---|---|---|---|---|
| gnn_nodes+F [GNN, LOSO] | 70.15 / 72.94 (68.34, r 5.59) | 80.90 / 82.45 (79.51, r 4.50) | 96.37 / 96.82 (96.12, r 1.06) | 99.70 / 99.85 (99.45, r 0.15) | 98.97 / 99.56 (98.92, r 0.30) | 89.22 / 90.32 |
| gnn_nodes+F_subjnorm [GNN, LOSO] | 75.15 / 78.38 (74.75, r 1.77) | 81.99 / 84.78 (81.78, r 1.39) | 96.07 / 96.22 (95.66, r 1.21) | 99.55 / 99.40 (99.50, r 0.30) | 98.82 / 99.41 (98.97, r 0.00) | 90.32 / 91.64 |
| gnn_nodes+coh+F [GNN, LOSO] | 70.88 / 73.38 (68.82, r 3.82) | 79.35 / 81.83 (78.11, r 5.13) | 96.22 / 96.37 (95.41, r 2.72) | 99.55 / 99.85 (99.45, r 0.30) | 98.82 / 99.56 (98.77, r 0.44) | 88.96 / 90.20 |
| gnn_nodes+coh+F_subjnorm [GNN, LOSO] | 74.71 / 78.38 (74.66, r 1.77) | 82.61 / 83.23 (81.57, r 1.71) | 95.76 / 95.61 (95.77, r 1.06) | 99.55 / 99.70 (99.50, r 0.15) | 98.82 / 99.56 (98.77, r 0.30) | 90.29 / 91.30 |
| fbcca [P22] | 58.68 / 60.15 | 68.01 / 67.70 | 91.07 / 90.32 | 98.80 / 98.65 | 95.43 / 96.76 | 82.40 / 82.72 |
| lda [P22] | 69.26 / 74.12 | 76.24 / 76.71 | 96.07 / 96.07 | 99.55 / 99.55 | 96.91 / 96.76 | 87.61 / 88.64 |
| lda_subjnorm [P22, offline upper bound] | 74.85 / 77.50 | 83.07 / 84.16 | 95.61 / 95.31 | 99.70 / 99.85 | 96.91 / 96.91 | 90.03 / 90.75 |
| ccnn [P21, mean of seeds 42/43/44, range] | 71.18 / 74.66 (r 3.53) | 70.29 / 73.71 (r 5.12) | 92.84 / 94.20 (r 3.17) | 99.55 / 99.70 (r 0.30) | 96.32 / 97.55 (r 0.88) | 86.04 / 87.96 (r 1.22) |
| eegnet [P21, mean of seeds 42/43/44, range] | 59.12 / 61.13 (r 3.24) | 66.05 / 66.56 (r 8.23) | 85.83 / 86.64 (r 4.08) | 99.85 / 99.85 (r 0.30) | 84.34 / 85.47 (r 4.27) | 79.04 / 79.93 (r 1.18) |
| compact_eegnet [P21, single seed 42] | 60.29 / 61.32 | 63.35 / 65.22 | 85.02 / 85.78 | 99.55 / 99.70 | 87.33 / 88.95 | 79.11 / 80.19 |

Within-subject (common, 7 channels, trial-grouped 5-fold). Same cell format

| Method | S01 | S02 | S03 | S04 | S05 | Mean |
|---|---|---|---|---|---|---|
| gnn_nodes+F [GNN, within] | 70.88 / 74.56 (68.28, r 1.03) | 76.55 / 80.12 (74.54, r 2.64) | 90.32 / 91.83 (89.51, r 0.60) | 98.50 / 98.20 (97.89, r 0.91) | 97.79 / 98.97 (97.50, r 0.89) | 86.81 / 88.74 |
| gnn_nodes+coh+F [GNN, within] | 70.74 / 74.85 (68.72, r 2.50) | 75.62 / 80.90 (73.96, r 3.11) | 90.92 / 92.74 (90.47, r 1.97) | 98.80 / 98.65 (98.45, r 1.36) | 98.82 / 99.41 (98.33, r 1.03) | 86.98 / 89.31 |
| within_lda [P22, 5 split repeats] | 75.88 / 77.26 | 82.02 / 82.73 | 97.31 / 97.37 | 99.79 / 99.79 | 98.97 / 98.97 | 90.79 / 91.22 |

## Predictions PR-1..PR-9 (values per subject; noise unit SE_Δ = sqrt(SE_A² + SE_B²), SE = 100·sqrt(p(1-p)/n), n = windows; material = |Δ| > 2·SE_Δ and |Δ| > the GNN cell's seed range (both cells' ranges for GNN-vs-GNN); source `analysis.txt`)

Each tuple is (subject, Δ in pp, SE_Δ in pp, material). Data source: built continuous folders (continuous build), session OO, common channels; LOSO unless stated.

| PR | Values | Status |
|---|---|---|
| PR-1 (vs `fbcca`) | nodes+F: S01 +11.47 (2.58, material), S02 +12.89 (2.40, material), S03 +5.30 (1.33, material), S04 +0.90 (0.47, tie), S05 +3.54 (0.89, material). nodes+F_subjnorm: +16.47, +13.98, +5.00, +0.75 (tie), +3.39. nodes+coh+F: +12.20, +11.34, +5.15, +0.75 (tie), +3.39. nodes+coh+F_subjnorm: +16.03, +14.60, +4.69, +0.75 (tie), +3.39. Cohort means 89.22 / 90.32 / 88.96 / 90.29, all >= 82.40 | holds (no material loss anywhere; pooled variants materially above on S01 and S02) |
| PR-2 (vs `lda`, pooled) | nodes+F: S01 +0.89 (2.49, tie), S02 +4.66 (2.28, material), S03 +0.30 (1.05, tie), S04 +0.15 (0.34, tie), S05 +2.06 (0.77, material): materially above on 2 subjects. nodes+coh+F: +1.62 (2.48, tie), +3.11 (2.31, tie), +0.15, +0.00, +1.91 (0.78, material): 1 subject | missed for nodes+F (2 subjects above, not <= 1; S05 is a material gain, not a tie or a loss); holds for nodes+coh+F on the count, S05 again a material gain |
| PR-3 (`_subjnorm` - pooled, paired) | nodes+F: S01 +5.00 (2.41, tie: seed ranges 5.59 and 1.77), S02 +1.09 (2.17, tie), S03 -0.30, S04 -0.15, S05 -0.15 (ties); cohort-mean Δ +1.10. nodes+coh+F: +3.83 (2.41, tie), +3.26 (2.19, tie; range 5.13), -0.46, 0.00, 0.00; cohort-mean Δ +1.33. Reference `lda_subjnorm - lda`: +5.59, +6.83, -0.46, +0.15, 0.00 | partly: no material loss, mean Δ >= 0 hold; the required material gain on S01 or S02 did not appear (missed). All subjnorm statements are "test-time normalization, offline upper bound" |
| PR-4 (`nodes+coh+F - nodes+F`) | within: S01 -0.14, S02 -0.93, S03 +0.60, S04 +0.30, S05 +1.03 (5 ties). LOSO pooled: +0.73, -1.55, -0.15, -0.15, -0.15 (5 ties). LOSO subjnorm: -0.44, +0.62, -0.31, 0.00, 0.00 (5 ties). Material gains 0 in each | holds (5 of 5 ties in each protocol x norm) |
| PR-5 (within - LOSO, pooled) | nodes+F: S01 +0.73 (2.47, tie), S02 -4.35 (2.28, tie), S03 -6.05 (1.36, LOSO material), S04 -1.20 (0.52, LOSO material), S05 -1.18 (0.68, tie). nodes+coh+F: -0.14 (tie), -3.73 (2.33, tie), -5.30 (1.34, LOSO material), -0.75 (tie), 0.00 (tie). Material within > LOSO on 0 subjects | holds as stated (<= 2; S01 tie): the direction "LOSO below within" is not observed; wording per N8: "direction not observed; the within GNN is data-limited" |
| PR-6 (`within_lda` - within GNN) | nodes+F: S01 +5.00 (2.39, material), S02 +5.47 (2.25, material), S03 +6.99 (1.31, material), S04 +1.29 (0.50, material), S05 +1.18 (tie): above on 4, below on 0. nodes+coh+F: +5.14, +6.40, +6.39 (material), +0.99, +0.15 (ties): above on 3, below on 0 | holds |
| PR-7 (PF-30) | 20 LOSO folds: train 93.20 to 98.71 (min 93.20, none < 90, none < 70). OVERFITTING on S01 for 4 of 4 methods; on S02 for 2 of 4 (pooled nodes+F train - test 15.42, pooled nodes+coh+F 17.58); the two `_subjnorm` S02 folds are "no strong gap" (13.93, 13.83). Validation above test on all 8 S01/S02 folds (val 92.39 to 95.13 vs test 70.15 to 82.61) | partly: train >= 90 holds, no UNDERFITTING, val > test holds; OVERFITTING on S01 and S02 of every method missed on 2 folds (S02 subjnorm) |
| PR-8 | degenerate LOSO folds: 0. Degenerate within folds: 0 | holds |
| PR-9 | max LOSO seed range 5.59 pp (nodes+F S01) <= 8.23. Ranges: nodes+F 5.59 / 4.50 / 1.06 / 0.15 / 0.30; nodes+F_subjnorm 1.77 / 1.39 / 1.21 / 0.30 / 0.00; nodes+coh+F 3.82 / 5.13 / 2.72 / 0.30 / 0.44; nodes+coh+F_subjnorm 1.77 / 1.71 / 1.06 / 0.15 / 0.30. Ensemble >= per-seed mean - 1 pp in all 20 cells | holds |

## PF-30 summary (interpretation left to the results review)

- LOSO (20 folds): train 93.20 to 98.71 %, val (inner, training subjects) 88.33 to 95.13 %, test 70.15 to 99.70 %. S01 held-out folds: train 97.99 / 98.07 / 98.30 / 98.71, test 70.15 / 75.15 / 70.88 / 74.71 (Train - Test 22.92 to 27.84 pp, OVERFITTING). S02: train 95.91 to 96.92, test 79.35 to 82.61. S03-S05: test 95.76 to 99.70, "no strong gap".
- Within (50 folds): train 88.39 to 100.00 %, 17 folds with Train - Test > 15 pp (OVERFITTING), 33 "no strong gap"; per-subject mean train / val / test: S01 90.22 / 66.23 / 70.83, S02 95.31 / 75.30 / 76.08, S03 99.38 / 90.22 / 90.70, S04 100.00 / 98.59 / 98.60, S05 100.00 / 98.37 / 98.31 (pooled over variants, from `folds.csv`).
- No fold has test accuracy near chance (20 %); the minimum test accuracies are 70.15 % (LOSO) and 68.38 % (within). No fold is degenerate. In the within runs the validation fold (20 % of the training trials of the same subject) tracks test; in LOSO the validation trials come from the training subjects, so a high validation accuracy does not contradict the subject shift (N3, RR-4).

## Numbers in the handoffs vs logs

Every number in `05_run.md` (times, counts, exit codes, hashes) comes from `steps.txt`, `pytest_full.log/.time`, `v8_hashes.txt`, `hash_*.txt` or the logs; the PF-30 table is generated from the two `folds.csv` by `p23_analysis.py` (rounded to 2 decimals). The measured times (within 472 s, LOSO 721 s, smoke 37 s, suite 870 s) compare with the plan's measured 7.4 min, 12.2 min, 35 s and 14.3 min.

## Sources spot-check

- `mas/RULES.md` R2 exception text (unsupervised test-time normalization labelled, statistics source stated): the `_subjnorm` Normalization string carries all three elements (unlabeled whole-session statistics, "test-time normalization, offline upper bound", "R2 exception, PF-35"). Matches.
- `02_plan.md` V4/V5: the window sets and fold-config fields were checked against the P22 `predictions.csv` and `configs/pipeline_config.yaml` as written above. Matches, with the within-fold exception noted in V5.

## Reference consultations check

The access log under `mas/state/scratch/` has 42 lines, last modified 2026-10-28 07:41, no line dated 2026-10-29, none naming P23. The handoffs 03_changes_*.md and 04_tests.md declare no consultation (deep-learning: "None"). No unlisted access: pass. I did not open the answer-key folder in this run.

## Privacy scan

Staged diff (the two phase files only) scanned with `mas/state/scratch/p23_scan.py`, which applies the guard's term list by reference: 0 hits (helper exit 0, no term index reported), also 0 hits on the staged diff after the final edit.

## Reasons (if FAIL)

None. Acceptance 1-6 are met and V1-V12 are met (V5 and V10 with the notes above). Pre-registered directional predictions that missed or held only in part (PR-2 for nodes+F, PR-3 material gain on S01/S02, PR-7 OVERFITTING on two S02 subjnorm folds) are not acceptance criteria; they go to the results review as stated.
