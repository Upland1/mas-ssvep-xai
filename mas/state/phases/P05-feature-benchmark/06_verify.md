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
