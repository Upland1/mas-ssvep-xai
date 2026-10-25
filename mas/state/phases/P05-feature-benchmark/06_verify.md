# P05 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify_P05` @ e47e799e779a718945398274e67a130ec698c57f (worktree removed)

Verdict: FAIL

Reasons (numbered):

1. FAIL, qualitative R-3 (the only miss). Source: `reports/classification_report_evaluate_confusion_matrix_S03.txt` and the cell counts read from `outputs/figures/confusion_matrices/cm_fbcsp_m1_fbcca_cv_S03.png`. Class 101 (24 Hz) precision is 0.8537 (35 of 41 windows predicted 101; 6 false: 5 from true 102, 1 from true 104), not 1.0 ("perfect precision on 24 Hz"). R-3 names the 10.91 / 8.57 Hz pair as the main residual confusion; here the largest single off-diagonal cell is 102 -> 101 = 5, and two pairs tie at 6 windows (101<->102: 1 + 5; 104<->105: 3 + 3). Nothing was changed.
2. PASS, R-3 counts: S03 200 stimulus, 197 clean, 3 rejected (exact), identical in `flagship_S03.csv`, both benchmark CSVs and the console.
3. PASS, R-3 1.0 s: 90.36 % = 178/197, exact match.
4. PASS (within tolerance, not exact), R-3 2.0 s: 95.94 % = 189/197 vs 95.43 % = 188/197, +0.51 pp (tolerance ±1.5 pp; 186-190 windows). The log also prints `DIAGNOSTIC only ... trial-aware j%5 smoothing 95.43%`, equal to the reference value; reported as observed, no interpretation here.
5. PASS, the hybrid beats every single-domain space (best of 9 models, 1.0 s, strict).
6. PASS, FBCCA argmax (48.73 %) is below all 18 supervised rows of the two hybrid spaces (minimum 70.05 %); it is rank 55 of 55 rows.
7. PASS, QDA presence as pre-committed: absent for Continuous PSD and FBCSP (printed `LinAlgError ... class 101 has 31 samples and 210 / 50 features`), present for FBCCA (70.56 / 81.73). Not in the benchmark CSV (55 rows = 6 x 9 + 1).
8. PASS, flagship rows S01-S05 produced with the expected counts (table below).
9. PASS, privacy/git and R11 (details below).

Reason 1 is a stated R-3 qualitative criterion, so the verdict is FAIL; the quantitative R-3 numbers (reasons 2-4) pass. The pre-run review (`07_review.md`, check 5) says a qualitative miss is explained rather than an automatic reject; that decision is left to the orchestrator and the results review.

## Tests on the clean checkout

`python -m pytest tests/ -p no:warnings -o addopts="" -q` in the worktree: `413 passed in 120.23s (0:02:00)` (exit 0; `mas/state/scratch/pytest_P05_verify.txt`). A first run with default options also finished without failures (about 2 min).

## Acceptance criteria

### R-3, S03 FBCSP(m=1) + FBCCA -> Shrinkage-LDA (`reports/flagship_S03.csv`, log `evaluate_confusion_matrix_S03_20261024T234506.log`)

| Quantity | Reference | Obtained | Delta (pp) | Windows (ref / obtained) | Within ±1.5 pp |
|---|---|---|---|---|---|
| Clean / rejected | 197 / 3 | 197 / 3 | 0 | exact | yes |
| 1.0 s | 90.36 | 90.36 | 0.00 | 178 / 178 | yes |
| 2.0 s smoothed (legacy no-reset) | 95.43 | 95.94 | +0.51 | 188 / 189 | yes |
| 2.0 s, j%5 diagnostic (not the reported number) | 95.43 | 95.43 | 0.00 | 188 / 188 | - |

(`python3 -c`: 178/197 = 90.36, 188/197 = 95.43, 189/197 = 95.94.) `flagship_S03.csv` also holds m = 2: 92.89 / 96.95 (j%5 diagnostic 95.94).

### Qualitative R-3

Source: `reports/classification_report_evaluate_confusion_matrix_S03.txt` (precision, recall, support) and cell counts read from `outputs/figures/confusion_matrices/cm_fbcsp_m1_fbcca_cv_S03.png` (no text output holds the matrix).

Confusion (rows true, columns predicted):

| true \ pred | 101 | 102 | 103 | 104 | 105 |
|---|---|---|---|---|---|
| 101 | 35 | 1 | 0 | 1 | 2 |
| 102 | 5 | 34 | 0 | 0 | 0 |
| 103 | 0 | 0 | 38 | 2 | 0 |
| 104 | 1 | 0 | 1 | 35 | 3 |
| 105 | 0 | 0 | 0 | 3 | 36 |

Precision: 101 0.8537, 102 0.9714, 103 0.9744, 104 0.8537, 105 0.8780. Largest off-diagonal cell: 102 -> 101 = 5. Pair totals: 101<->102 = 6, 104<->105 = 6 (tie). Shrinkage-LDA lsqr and eigen are tied best on the hybrid (90.36; next LogReg L2 89.85). Reference expected precision 1.0 on 24 Hz and the 104/105 pair dominant: not met (reason 1).

### Feature-space x model table (`reports/feature_space_benchmark_S03.csv`, 1.0 s / 2.0 s smoothed, %)

Shown Python: `mas/state/scratch/check_P05.py` (pandas `groupby("Feature space")` maximum of `1.0s Acc (%)`, strict comparison).

| Model | PSD 210 | Harm PSD 32 | FBCCA 5 | Harm+FBCCA 37 | FBCSP 50 | FBCSP+FBCCA 55 |
|---|---|---|---|---|---|---|
| Ridge | 65.48 / 78.17 | 70.56 / 84.77 | 68.53 / 82.74 | 74.62 / 90.86 | 76.14 / 86.29 | 83.25 / 92.39 |
| LogReg L2 | 78.17 / 92.39 | 69.54 / 82.74 | 70.05 / 81.73 | 73.10 / 84.77 | 84.77 / 92.39 | 89.85 / 96.45 |
| LogReg L1 | 82.23 / 93.40 | 71.57 / 85.79 | 70.56 / 82.23 | 75.13 / 85.28 | 81.22 / 89.85 | 87.31 / 96.45 |
| LogReg ElasticNet | 81.73 / 93.40 | 70.05 / 84.26 | 71.07 / 81.73 | 74.11 / 85.28 | 82.74 / 92.89 | 88.32 / 96.95 |
| SGD log-loss | 76.65 / 83.25 | 70.05 / 76.14 | 71.57 / 76.65 | 70.05 / 77.66 | 83.76 / 88.32 | 87.31 / 93.40 |
| SGD PA | 84.26 / 93.40 | 62.94 / 74.62 | 63.45 / 73.10 | 70.56 / 84.26 | 80.71 / 86.80 | 85.28 / 95.94 |
| LDA svd | 71.57 / 81.73 | 70.05 / 81.73 | 69.04 / 82.74 | 74.11 / 88.83 | 78.68 / 83.76 | 81.22 / 91.88 |
| Shrinkage-LDA lsqr | 84.26 / 90.86 | 64.47 / 75.63 | 70.56 / 85.79 | 74.11 / 86.29 | 84.77 / 91.37 | 90.36 / 95.94 |
| Shrinkage-LDA eigen | 84.26 / 90.86 | 64.47 / 75.63 | 70.56 / 85.79 | 74.11 / 86.29 | 84.77 / 91.37 | 90.36 / 95.94 |
| QDA (suite CSV only) | failed | not run | 70.56 / 81.73 | not run | failed | not run |
| Best of 9 (1.0 s) | 84.26 | 71.57 | 71.57 | 75.13 | 84.77 | **90.36** |

FBCCA argmax (zero-training, p=5): 48.73 / 51.78. The benchmark table is 6 x 9 + 1 = 55 rows, p = 210, 32, 5, 37, 50, 55, 5; 197 clean, 3 rejected on every row.

Hybrid vs single-domain (strict, 1.0 s best of 9): 90.36 > PSD 84.26, Harmonic PSD 71.57, FBCCA 71.57, FBCSP 84.77: True (margin to the next best, FBCSP, 5.59 pp). Harmonic PSD + FBCCA (75.13) is the other hybrid space. FBCCA argmax 48.73 < minimum of the 18 hybrid rows (70.05): True; it is the lowest of 55 rows, so no single-domain row falls below it.

### S01-S05 flagship rows (`reports/flagship_S0x.csv`, m = 1, legacy leaky CV; 1.0 s / 2.0 s smoothed legacy no-reset; for P06)

| Subject | Stimulus | Clean | Rejected | 1.0 s | 2.0 s | R-5 1.0 s / 2.0 s | j%5 diagnostic | Counts as expected |
|---|---|---|---|---|---|---|---|---|
| S01 | 200 | 200 | 0 | 64.50 | 77.00 | 64.50 / 75.50 | 75.50 | yes |
| S02 | 199 | 196 | 3 | 66.33 | 71.94 | 66.33 / 71.94 | 71.94 | yes |
| S03 | 200 | 197 | 3 | 90.36 | 95.94 | 90.36 / 95.43 | 95.43 | yes |
| S04 | 198 | 197 | 1 | 98.98 | 98.48 | 98.98 / 98.48 | 98.48 | yes |
| S05 | 200 | 200 | 0 | 96.50 | 98.00 | 96.50 / 96.50 | 96.50 | yes |

All five 1.0 s values equal R-5 exactly. 2.0 s: S02 and S04 exact, S03 +0.51, S01 +1.50 and S05 +1.50 pp (at the tolerance edge, 3 windows each). In all five subjects the j%5 diagnostic equals the R-5 2.0 s value. Data source in every log: legacy windows `data/processed/S0x/`, OO session, stimulus windows, `StratifiedKFold(5, shuffle, 42)` over windows (R1 legacy, leaky), seed 42, fs 250 (PF-04), per-window sub-band filtering (R3 legacy), window mask vpp [5, 120] uV, std [1, 35] uV. Not comparable with R-6.

### Other checks

- `visualize_data` log: the FBCSP line says `full-data CSP, visualization only` (R2 exception labelled); psd, fbcca and fbcsp figures written.
- Log headers: each of the 10 logs starts with the command, commit e47e799 and an empty `porcelain:` block.
- Harmonic PSD + FBCCA, Shrinkage-LDA lsqr: 74.11 / 86.29 (`classification_report_benchmark_harmonic_fbcca_S03.txt`), equal to the CSV row.

## Privacy, git, R11

- `git status --porcelain` is empty after all runs; deliverables are in the git-ignored `reports/` and `outputs/`. `git ls-files` shows no tracked raw recordings, `.npy`, `.csv`, `.png`, `data/`, `reports/` or `outputs/` entries. A check of tracked paths for the answer-key directory was blocked by the guard hook (the pattern contained its path) and was not repeated in another form; the pre-run review reports 0 hits.
- `mas/state/scratch/reference_access.log`: 5 lines before and after the runs; no new access. Existing lines: two earlier verifier entries, two main-session entries at 21:27 (README, settled as pre-P04 in decisions.md) and one scribe grep. No P05 consultation; the builders' handoffs state "None". R11 clean.
- Sources opened: `mas/04_REFERENCE_RESULTS.md` (R-3, R-5, tolerance rules) and the logs/CSVs cited above.

---

## Round 2

Status: READY
Clean checkout: `mas/state/scratch/verify_P05_r2` @ edcc17747d0ce57f17d880da24ee3bda1e5bf7a4 (worktree removed). Run record: `05_run.md` "Round 2".

Verdict: FAIL

Reasons (numbered; the pre-committed re-run checks 1-6 of `07_review.md` "Pre-run audit — Round 2" applied as written):

1. Check 1, counts: PASS. S03 200/197/3, S01 200/200/0, S02 199/196/3, S04 198/197/1, S05 200/200/0, identical to Round 1 and to R-3/R-5 (exact), under the 0.5/0.1 limits.
2. Check 2, same rejected set: PASS. 1.0 s unchanged from Round 1 in every subject (S03 90.36, S01 64.50, S02 66.33, S04 98.98, S05 96.50); the 55 1.0 s values of the benchmark CSV are identical to Round 1 (`True`, `mas/state/scratch/check_P05_r2.py`).
3. Check 3, 2.0 s equals the former j%5 diagnostic: PASS (table below). The printed no-reset DIAGNOSTIC lines repeat the Round 1 reported values in all five subjects.
4. Check 4, qualitative R-3 read only from `reports/classification_report_evaluate_confusion_matrix_S03_smoothed_mod5.txt` (m=1): half FAIL, half PASS. Class-101 precision is 0.9750 (39 of 40 predicted 101; recall 1.0000), not 1.0000: FAIL on that part. Largest two-way off-diagonal total is 104<->105 = 6 (3 + 3); every other pair is 1: PASS on that part. Per the pre-commitment this is a qualitative deviation with checks 1-3 exact; no definition was changed and the explanation or rejection is left to the results review.
5. Check 5, benchmark table: PASS. 1.0 s columns equal Round 1 (hybrid best-of-9 90.36 strictly above PSD 84.26, Harmonic PSD 71.57, FBCCA 71.57, FBCSP 84.77; argmax 48.73 below all 18 hybrid-space supervised rows, minimum 70.05, rank 55 of 55). The 2.0 s column changed in 49 of 55 rows, the argmax row included (51.78 -> 52.28). The table has 55 rows.
6. Check 6, two Harmonic PSD + FBCCA numbers: reported below under distinct names; they differ as expected (75.63 vs 74.11 at 1.0 s; 2.0 s both 84.77).
7. QDA as pre-committed: absent for Continuous PSD and FBCSP (two printed `LinAlgError` failures), present for FBCCA (2.0 s 80.20).
8. Privacy/git and R11: PASS (below).

The verdict stays FAIL on the same single criterion as Round 1 (a stated qualitative R-3 item: "perfect precision on 24 Hz"), now narrower: 0.9750 instead of 0.8537, and the 104/105 pair now dominates. All quantitative R-3 items pass exactly.

### R-3, S03 FBCSP(m=1) + FBCCA -> Shrinkage-LDA (`reports/flagship_S03.csv`, log `evaluate_confusion_matrix_S03_r2_20261025T024450.log`)

| Quantity | Reference | Obtained | Delta (pp) | Windows (ref / obtained) |
|---|---|---|---|---|
| Clean / rejected | 197 / 3 | 197 / 3 | 0 | exact |
| 1.0 s | 90.36 | 90.36 | 0.00 | 178 / 178 |
| 2.0 s smoothed (i%5 trial smoothing, reported) | 95.43 | 95.43 | 0.00 | 188 / 188 |
| 2.0 s no-reset (DIAGNOSTIC) | - | 95.94 | - | 189 |

`flagship_S03.csv` m=2: 92.89 / 95.94 (no-reset diagnostic 96.95). Round 1 vs Round 2 for S03 m=1: 2.0 s 95.94 -> 95.43.

### Qualitative R-3 (source: `reports/classification_report_evaluate_confusion_matrix_S03_smoothed_mod5.txt`, titled REPORTED, accuracy 95.43%)

Confusion counts from the file (rows true, columns predicted, 101..105):

| true \ pred | 101 | 102 | 103 | 104 | 105 |
|---|---|---|---|---|---|
| 101 | 39 | 0 | 0 | 0 | 0 |
| 102 | 1 | 38 | 0 | 0 | 0 |
| 103 | 0 | 1 | 39 | 0 | 0 |
| 104 | 0 | 0 | 1 | 36 | 3 |
| 105 | 0 | 0 | 0 | 3 | 36 |

Precision: 101 0.9750, 102 0.9744, 103 0.9750, 104 0.9231, 105 0.9231; recall 101 1.0000. Shrinkage-LDA lsqr/eigen tied best on the hybrid (90.36 / 95.43), LogReg L2 95.43 at 2.0 s.

### Feature-space x model, Round 2 2.0 s columns (1.0 s identical to Round 1, see Round 1 table)

| Model | Harm+FBCCA 37 (six-space, FBCCA all channels) | FBCSP+FBCCA 55 |
|---|---|---|
| Ridge | 74.62 / 89.34 | 83.25 / 91.88 |
| LogReg L2 | 73.10 / 84.26 | 89.85 / 95.43 |
| LogReg L1 | 75.13 / 83.76 | 87.31 / 94.42 |
| LogReg ElasticNet | 74.11 / 84.26 | 88.32 / 94.92 |
| SGD log-loss | 70.05 / 77.16 | 87.31 / 91.88 |
| SGD PA | 70.56 / 82.23 | 85.28 / 94.42 |
| LDA svd | 74.11 / 87.82 | 81.22 / 89.85 |
| Shrinkage-LDA lsqr / eigen | 74.11 / 84.77 | 90.36 / 95.43 |

FBCCA argmax (zero-training): 48.73 / 52.28. Full 55-row table: `reports/feature_space_benchmark_S03.csv` (all 2.0 s values reproduced there; the other four spaces' 2.0 s values also changed, Round 1 values in the Round 1 table above).

### Two "Harmonic PSD + FBCCA" numbers (Shrinkage-LDA lsqr, 1.0 s / 2.0 s i%5)

| Name | FBCCA channels | 1.0 s | 2.0 s | Source |
|---|---|---|---|---|
| Six-space table, "Harmonic PSD + FBCCA" | all 7 channels | 74.11 | 84.77 | `feature_space_benchmark_S03.csv` rows 34-35 |
| Harmonic script, `benchmark_harmonic_fbcca` | PO8, O1, Oz, O2 | 75.63 | 84.77 | `classification_report_benchmark_harmonic_fbcca_S03.txt` header; log `benchmark_harmonic_fbcca_S03_r2_20261025T024437.log` |

Harmonic PSD in both uses the PO8, O1, Oz, O2 cluster (32 features). Round 1 harmonic-script value was 74.11 / 86.29 (no-reset, all channels).

### S01-S05 flagship rows (m=1, legacy leaky CV, i%5 trial smoothing; for P06)

| Subject | Stimulus | Clean | Rejected | 1.0 s | 2.0 s (reported) | R-5 1.0 s / 2.0 s | no-reset diagnostic |
|---|---|---|---|---|---|---|---|
| S01 | 200 | 200 | 0 | 64.50 | 75.50 | 64.50 / 75.50 | 77.00 |
| S02 | 199 | 196 | 3 | 66.33 | 71.94 | 66.33 / 71.94 | 71.94 |
| S03 | 200 | 197 | 3 | 90.36 | 95.43 | 90.36 / 95.43 | 95.94 |
| S04 | 198 | 197 | 1 | 98.98 | 98.48 | 98.98 / 98.48 | 98.48 |
| S05 | 200 | 200 | 0 | 96.50 | 96.50 | 96.50 / 96.50 | 98.00 |

All ten R-5 values (1.0 s and 2.0 s, five subjects) are reproduced exactly. Data source: legacy windows `data/processed/S0x/`, OO session, stimulus windows, `StratifiedKFold(5, shuffle, 42)` over windows (R1 legacy, leaky), fs 250, per-window sub-band filtering (R3 legacy), mask vpp [0.5, 120] uV / std [0.1, 35] uV. The `visualize_data` log still labels the FBCSP figure as a full-data fit (visualization only). Not comparable with R-6.

### Privacy, git, R11

- `git status --porcelain` empty before and after the runs; deliverables are git-ignored. No tracked data or generated files (`git ls-files` filter for raw recordings, `.npy`, `.csv`, `.png`, `data/`, `reports/`, `outputs/`: no hits).
- `mas/state/scratch/reference_access.log` has 14 lines before and after my runs (Round 1 report: 5). Lines 6-14, dated 2026-10-24T23:48:50 to 23:49:50, are all by `ml-engineer`: git queries on the answer-key repository (branch listing, tree listing, history of the confusion-matrix script, and `show` of the original confusion-matrix script, FBCCA and FBCSP extractors, quality check, cross-validation benchmark and harmonic benchmark at commit 69873ea). They match the "Round 2 — implementation" consultation table of the ml-engineer handoff (logged consultations). Trigger: implementation, tests and a FAIL verdict existed beforehand; the reviewer noted the first access preceded the diagnostics commit by 30 s (sequencing CONCERN, not a FAIL). No access by the verifier in this round.
- Sources opened: `mas/state/decisions.md` P05 rows, `07_review.md` Round 2, `reports/classification_report_evaluate_confusion_matrix_S03_smoothed_mod5.txt`, the logs and CSVs cited.

---

## Verdict restatement (after results review)

Verdict: PASS (with one accepted deviation, D-1)

Basis, against the acceptance criteria as written above:

- My FAIL (Round 1 and Round 2) rested on one item only: the R-3 qualitative statement "perfect precision on 24 Hz". Round 2 value: class-101 precision 0.9750 (39 of 40) in `reports/classification_report_evaluate_confusion_matrix_S03_smoothed_mod5.txt`, recall 1.0000.
- The scientific reviewer (`07_review.md`, results review, commit dce6242) accepted this as deviation D-1 with a signed explanation, recorded in `mas/state/decisions.md` (2026-10-25 P05 row). `mas/04_REFERENCE_RESULTS.md` tolerance rules allow a deviation that the reviewer explains and signs.
- My own judgement: the deviation is one window of 40 predictions, it is qualitative (no numeric tolerance exists for it), nothing was tuned, and every count and accuracy of R-3 and R-5 is exact. Round 2 checks 1, 2, 3, 5 and 6, the 104<->105 dominance, the hybrid-vs-single-domain and argmax criteria, QDA presence, privacy/git and R11 all passed as reported. With D-1 accepted, no acceptance criterion remains unmet, so the P05 verification is PASS.
- The Round 1 and Round 2 text above is unchanged and records the FAIL verdicts as issued at the time.
