# P20 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify/P20` @ 5d9326d (removed after the run; `data/` and `reports/` kept)

Verdict: PASS

Basis: every command exited 0; all six cnn windows and 4b ran locally (no human run, nothing PENDING-HUMAN); checks A-I and acceptance 1-7 are met; one disclosed suite anomaly (first full-suite run: 2 hash-pinned P09/P10 tests failed under concurrent load; they pass alone and in an isolated full re-run) is listed for the reviewer. Numbers are values only; the directions P1-P6 are reported "holds / fails / inconclusive" without interpretation. Single-repeat CNN cells carry no seed-variance estimate (R-P2).

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests/ -q -o addopts=""
```
- Run 1 (concurrent with builds), `reports/logs/P20/pytest_full.log`: `2 failed, 1295 passed, 22 warnings in 801.98s (0:13:21)`; failures `tests/test_p09_compact_shallow.py::test_eegnet_regression_after_refactor` and `tests/test_p10_augmentation.py::test_off_path_identical_to_p09` (sha256 of `proba` differs from the pinned value).
- The two alone, `pytest_rerun_2failed.log`: `2 passed in 6.87s`.
- Run 2 (nothing else running), `pytest_full_rerun_isolated.log`: `1297 passed, 22 warnings in 768.43s (0:12:48)`.
- Item H, `pytest_H_causal_filter.log`: `tests/test_p20_online.py::test_causal_filter_chunked_equals_one_pass_and_is_causal PASSED [100%]` (`1 passed, 7 deselected in 2.01s`).

## Acceptance

| Criterion (verbatim) | Re-run command | Obtained | Reference (R-x) | Tolerance | Met? | Log |
|---|---|---|---|---|---|---|
| 1. `reports/window_sweep/summary.csv` has all 6 lengths x 3 methods x 5 subjects, with the §6 columns; `predictions.csv` and `confusion.csv` exist | commands 2a + 2b x6 | 90 rows (fbcca, lda, `cnn (compact_eegnet)` x 6 lengths x 5 subjects, 5 rows per cell); columns `Subject, Window (s), Method, Windows, Trials, Acc (%), Acc SD, BalAcc (%), ITR (bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch, Data source`; `predictions.csv` and `confusion.csv` present (also `timing.csv`) | R-16 none | exact | yes | `analysis_sweep.txt` |
| 2. `reports/nn_sweep/summary.csv` at 1 s has 3 models x 5 subjects, with `Val Acc (%)` and `Best Epoch`, and the PF-31 names | command 3 | models `ccnn`, `compact_eegnet`, `eegnet` x S01-S05 = 15 rows; columns include `Val Acc (%)`, `Best Epoch`, `Params`, `Augment`, `Device` | PF-31 | exact | yes | `nn_sweep.log`, `analysis_nn_dynstop.txt` |
| 3. The dynamic-stopping best-threshold table per method x window, plus `decisions/per_subject/cohort.csv` | commands 4a, 4b | `best_threshold.csv` 12 rows (lda, `cnn (compact_eegnet)` x 6 windows); `decisions.csv`, `per_subject.csv`, `cohort.csv` present in both out-dirs | | exact | yes | `dynamic_stopping_4b.log` |
| 4. Pseudo-online `summary_ccnn_5class.csv` and `summary_ccnn_6class.csv` per subject | commands 5, 6 | both present, S01-S05 + Mean | | exact | yes | `pseudo_online_*class.log` |
| 5. The causal-filter test passes (named in the suite output) | item H | `test_causal_filter_chunked_equals_one_pass_and_is_causal PASSED` | PF-38 | exact | yes | `pytest_H_causal_filter.log` |
| 6. The protected `S0*` hashes are unchanged | sha256sum of the 65 files, before and after | `cmp hash_before.txt hash_after.txt` -> `HASHES_IDENTICAL` (65 lines each) | | exact | yes | `hash_before.txt`, `hash_after.txt` |
| 7. Per-subject numbers carry their data source (R9) | read columns | `Data source` column in the window-sweep, NN-sweep and dynamic-stopping tables ("continuous build (w<L>_s0.25/<S>), session OO") and pseudo-online summaries ("OO->mOO (causal-filtered stream replay, shared quality tier w/o guard), session files") | R9 | exact | yes | CSVs |

Note on 6: `sha256sum hash_before.txt hash_after.txt` printed the same digest for both files, `c6e72a797e06ccc7fafe03dde3bb81e9ea07eb863909d6ec6a48a5b011e12aec`.

## Binding checks A-I

- **A** met: both pseudo-online logs quote `quality source both, limits {'vpp_min': 5.0, 'vpp_max': 120.0, 'std_min': 1.0, 'std_max': 35.0}, channel fail fraction 0.5` (05_run.md).
- **B** met: 17 GB free; no stale outputs (05_run.md).
- **C** met: order followed. `a.equals(b)` on the `Method == lda` rows of `per_subject.csv` (sorted by Subject, Method, Window, Threshold) between `reports/dynamic_stopping_lda/` and `reports/dynamic_stopping/` (180 rows): `True` (`analysis_sweep.txt`, script `mas/state/scratch/p20_verify/analysis.py`).
- **S** met: see 05_run.md; `T_A` 20.15 min, `P_2b` 61.378 min, check 84.53 <= 120; six window checks passed; total 80.95 min, GPU 1.30 h.
- **D** met: `.venv/bin/python mas/state/scratch/p20_verify/hash_d.py` (fbcca + lda rows, sorted, `to_csv(index=False)`, sha256), before and after 2b: `summary.csv 60 f65de2e669953eb3ebb0a11bd554773b338dbeb07d708928e2ff2816f829cc00`, `predictions.csv 91356 283fa9fb0680f5f04e5168d126d3b5015a706de35874b042b73dd4cab93b32b1`; identical (`diff` -> `D_UNCHANGED`; `hash_D_before2b.txt`, `hash_D_after.txt`).
- **E** met (same machine, same GPU): per subject `Acc (%)` of `cnn (compact_eegnet)` at 1 s in the sweep equals `compact_eegnet` in the NN sweep: S01 84.12, S02 77.48, S03 98.94, S04 99.85, S05 100.00, difference 0.0 each; joined predictions (subject, trial_id, offset_sec): 3329 rows both sides, max |dp| = 0.0, predicted class equal in 100 %. No anomaly.
- **F** met: Runs fbcca 1, lda 5, cnn 1; `Windows` and `Trials` equal across the three methods in every subject-window cell (0 differences); `Windows > Trials x ((5-L)/0.25+1)`: 0 cells. Channels kept per subject at all six lengths (build logs): S01 7 (PO7 dropped), S02 8, S03 7 (PO7 dropped), S04 7 (PO7 dropped), S05 8; no subject differs between lengths.
- **G** met: per (Subject, Method, Window) `Mean Time (s)` and `Forced (%)` non-decreasing in the threshold: 0 violations of 60 groups; minimum `time_sec` in `decisions.csv` = 1.0 (0 rows below 0.5 + L); `fbcca` absent (methods `cnn (compact_eegnet)`, `lda`); `Skipped trials` total = 0.
- **H** met (above).
- **I** met: `Channels kept` equal in the 5- and 6-class summaries for all subjects. Per subject (identical in both tags): S01 7, `Dropped at check` 0, `Trials before check` 1, `Fallback` 0; S02 8, 0, 2, 0; S03 7, 0, 2, 0; S04 7, 0, 1, 0; S05 8, 0, 1, 0. `grep -c -i "paradigm\|PF-39"` on both pseudo-online logs: 0 and 0 (no PF-39 warning).

## Tables (values from the CSVs; data source per R-P1)

Window-level sweep, unsmoothed, continuous build `data/processed_continuous/w<L>_s0.25/`, shared quality (source both), OO session; ITR = Wolpaw N = 5, T = L + 0.5 s on accuracy pooled over overlapping windows at all offsets (not a trial-level online rate, R-P3). `Acc SD` 0 with `Runs` 1 = not estimated (R-P2). Source `reports/window_sweep/summary.csv`.

Cohort mean (mean of the 5 per-subject values), Acc (%) / ITR (bits/min):

| Method | 0.5 s | 1 s | 1.5 s | 2 s | 3 s | 4 s |
|---|---|---|---|---|---|---|
| fbcca | 69.16 / 57.50 | 81.72 / 56.56 | 87.78 / 49.80 | 92.11 / 44.60 | 95.62 / 34.84 | 96.86 / 28.15 |
| lda | 81.80 / 84.37 | 89.89 / 70.03 | 93.42 / 57.62 | 95.63 / 48.82 | 97.59 / 36.73 | 98.03 / 28.93 |
| cnn (compact_eegnet) | 80.75 / 87.25 | 92.08 / 74.53 | 94.47 / 59.17 | 95.51 / 48.43 | 95.28 / 34.48 | 83.10 / 21.56 |

Per subject Acc (%) at 0.5 / 1 / 1.5 / 2 / 3 / 4 s:

| Subject | fbcca | lda | cnn (compact_eegnet) |
|---|---|---|---|
| S01 | 46.97 / 58.68 / 67.33 / 75.00 / 85.56 / 86.50 | 64.26 / 75.88 / 82.77 / 87.58 / 93.11 / 95.00 | 69.87 / 84.12 / 89.83 / 89.42 / 91.67 / 77.00 |
| S02 | 43.78 / 64.60 / 78.05 / 87.89 / 93.11 / 98.35 | 60.66 / 77.36 / 85.17 / 90.68 / 94.85 / 95.16 | 42.96 / 77.48 / 83.36 / 89.32 / 85.63 / 39.56 |
| S03 | 77.18 / 91.07 / 95.34 / 98.60 / 99.41 / 99.46 | 90.50 / 97.31 / 99.48 / 99.88 / 100.00 / 100.00 | 93.42 / 98.94 / 99.14 / 98.80 / 99.12 / 98.92 |
| S04 | 93.42 / 98.80 / 99.66 / 100.00 / 100.00 / 100.00 | 98.28 / 99.79 / 100.00 / 100.00 / 100.00 / 100.00 | 98.93 / 99.85 / 100.00 / 100.00 / 100.00 / 100.00 |
| S05 | 84.45 / 95.43 / 98.50 / 99.04 / 100.00 / 100.00 | 95.31 / 99.09 / 99.67 / 100.00 / 100.00 / 100.00 | 98.55 / 100.00 / 100.00 / 100.00 / 100.00 / 100.00 |

Per subject ITR (bits/min) at the same lengths:

| Subject | fbcca | lda | cnn (compact_eegnet) |
|---|---|---|---|
| S01 | 15.84 / 20.69 / 22.71 / 24.26 / 24.64 / 19.75 | 40.00 / 41.70 / 39.43 / 36.77 / 31.24 / 25.81 | 50.18 / 54.91 / 49.33 / 38.96 / 29.85 / 14.45 |
| S02 | 12.53 / 27.05 / 33.71 / 37.13 / 31.24 / 28.90 | 34.09 / 43.90 / 42.59 / 40.52 / 33.02 / 25.94 | 11.72 / 44.09 / 40.20 / 38.84 / 24.70 / 1.93 |
| S03 | 65.44 / 68.38 / 58.72 / 52.50 / 38.71 / 30.17 | 100.73 / 83.57 / 67.95 / 55.35 / 39.80 / 30.96 | 110.43 / 88.64 / 67.00 / 52.90 / 38.25 / 29.52 |
| S04 | 110.43 / 88.16 / 68.46 / 55.73 / 39.80 / 30.96 | 129.74 / 91.84 / 69.66 / 55.73 / 39.80 / 30.96 | 132.89 / 92.11 / 69.66 / 55.73 / 39.80 / 30.96 |
| S05 | 83.26 / 78.52 / 65.38 / 53.38 / 39.80 / 30.96 | 117.30 / 89.15 / 68.49 / 55.73 / 39.80 / 30.96 | 131.02 / 92.88 / 69.66 / 55.73 / 39.80 / 30.96 |

`lda` Acc SD over 5 repeats ranges 0.00-1.89 pp (`analysis_sweep.txt`).

NN sweep at 1 s (`reports/nn_sweep/summary.csv`, device cuda, augmentation on, single run per cell; PF-31 names), Acc (%) per subject and cohort means:

| Model | S01 | S02 | S03 | S04 | S05 | Mean Acc | Mean Train Acc | Mean Val Acc | Mean Best Epoch | Mean ITR |
|---|---|---|---|---|---|---|---|---|---|---|
| ccnn | 80.29 | 77.02 | 99.24 | 100.00 | 99.71 | 91.25 | 100.00 | 92.99 | 41.52 | 73.18 |
| compact_eegnet | 84.12 | 77.48 | 98.94 | 99.85 | 100.00 | 92.08 | 99.91 | 93.10 | 62.00 | 74.53 |
| eegnet | 77.94 | 71.43 | 99.24 | 100.00 | 99.85 | 89.69 | 98.89 | 90.97 | 84.72 | 71.00 |

Dynamic stopping, best threshold per method and window by cohort ITR (selected over 6 thresholds on the same data: descriptive, R-P4; `reports/dynamic_stopping/best_threshold.csv`):

| Method | Window (s) | Threshold | Acc (%) | Mean Time (s) | Forced (%) | ITR (bits/min) | time-matched ITR (R-P6) |
|---|---|---|---|---|---|---|---|
| lda | 0.5 | 0.70 | 87.72 | 1.24 | 3.64 | 61.53 | 60.23 |
| lda | 1.0 | 0.80 | 92.29 | 1.67 | 3.15 | 53.73 | 53.48 |
| lda | 1.5 | 0.95 | 94.63 | 2.20 | 5.18 | 45.11 | 44.29 |
| lda | 2.0 | 0.95 | 95.69 | 2.58 | 2.46 | 39.94 | 39.31 |
| lda | 3.0 | 0.95 | 97.44 | 3.52 | 0.91 | 31.86 | 31.47 |
| lda | 4.0 | 0.90 | 98.25 | 4.51 | 0.51 | 26.18 | 26.10 |
| cnn (compact_eegnet) | 0.5 | 0.50 | 86.26 | 1.63 | 13.32 | 61.84 | 61.28 |
| cnn (compact_eegnet) | 1.0 | 0.50 | 94.42 | 1.65 | 1.53 | 56.33 | 54.05 |
| cnn (compact_eegnet) | 1.5 | 0.50 | 95.44 | 2.15 | 2.05 | 46.43 | 46.23 |
| cnn (compact_eegnet) | 2.0 | 0.50 | 95.87 | 2.57 | 1.55 | 39.92 | 38.56 |
| cnn (compact_eegnet) | 3.0 | 0.60 | 97.97 | 3.65 | 7.76 | 31.52 | 29.25 |
| cnn (compact_eegnet) | 4.0 | 0.60 | 82.34 | 4.62 | 20.28 | 19.44 | 19.85 |

The time-matched column (R-P6) is, per subject, the accuracy of the windows with `offset_sec == 0.5` and ITR with T = 0.5 + L + 0.5 s, averaged over subjects, computed read-only from `reports/window_sweep/predictions.csv` (`analysis_nn_dynstop.txt`; cohort time-matched accuracies lda 82.72 / 89.41 / 91.20 / 94.16 / 96.80 / 98.12, cnn 81.45 / 90.55 / 93.18 / 93.70 / 94.28 / 84.73).

Pseudo-online OO -> mOO, causal stream replay, window 0.5 s, stride 0.25 s, skip 0.5 s, threshold 0.6, ccnn, `--quality-source both`; session files; test-time label-free channel check (first 30 s of the test stream), no channel dropped (`Dropped at check` 0 everywhere; R-P8 not applicable); `Mean` = mean of per-subject values; no subject used `Fallback` (R-P7). Source `reports/pseudo_online/summary_ccnn_{5class,6class}.csv`:

| Subject | Acc 5 (%) | Acc 6 (%) | Time 5 / 6 (s) | Forced 5 (%) | Missed 6 (%) | ITR 5 / 6 | False act. 5 / 6 (%) | Windows rejected 5 (%) | Val acc 5 / 6 (%) |
|---|---|---|---|---|---|---|---|---|---|
| S01 | 60.00 | 35.00 | 2.53 / 1.47 | 32.50 | 50.0 | 10.92 / 2.67 | 52.5 / 17.5 | 0.55 | 71.71 / 73.68 |
| S02 | 90.00 | 47.50 | 1.96 / 1.40 | 17.50 | 52.5 | 40.36 / 8.64 | 45.0 / 7.5 | 0.31 | 76.32 / 77.40 |
| S03 | 97.50 | 92.50 | 1.26 / 1.30 | 0.00 | 7.5 | 71.63 / 59.70 | 20.0 / 0.0 | 0.93 | 95.39 / 96.05 |
| S04 | 100.00 | 100.00 | 1.14 / 1.14 | 0.00 | 0.0 | 84.96 / 84.96 | 0.0 / 0.0 | 0.16 | 99.34 / 97.78 |
| S05 | 97.50 | 95.00 | 1.23 / 1.24 | 0.00 | 5.0 | 73.09 / 66.83 | 20.0 / 0.0 | 0.00 | 98.68 / 94.74 |
| Mean | 89.00 | 74.00 | 1.62 / 1.31 | 10.00 | 23.0 | 56.19 / 44.56 | 27.5 / 5.0 | 0.39 | 88.29 / 87.93 |

40 stimulus periods and 40 rest periods per subject in each tag; `Trials undecided` 0. The `Window (s)` of the Mean row is the first subject's (0.5).

R-P12 decomposition over the periods scored in both tags (`analysis_pseudo_online.txt`, `mas/state/scratch/p20_verify/po.py`), n = 40 per subject, percentage points of periods; Acc5 - Acc6 = P(correct5, wrong6) - P(wrong5, correct6); the first term split into "missed" (6-class no target) and "wrong class":

| Subject | Acc5 - Acc6 | P(c5,w6) | of which missed | of which wrong class | P(w5,c6) |
|---|---|---|---|---|---|
| S01 | 25.0 | 35.0 | 27.5 | 7.5 | 10.0 |
| S02 | 42.5 | 42.5 | 42.5 | 0.0 | 0.0 |
| S03 | 5.0 | 7.5 | 7.5 | 0.0 | 2.5 |
| S04 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| S05 | 2.5 | 2.5 | 2.5 | 0.0 | 0.0 |
| pooled (n = 200) | 15.0 | 17.5 | 16.0 | 1.5 | 2.5 |

R-P9 (false activations whose `pred` equals the code of the following stimulus period, chance 20 %; `time_sec` distribution): 5 classes, 55 false activations (S01 21, S02 18, S03 8, S05 8, S04 0): matches S01 6/21, S02 6/18, S03 1/8, S05 3/8, pooled 29.1 %; `time_sec` <= 2 s: 55, 2-4 s: 0, 4-5 s: 0. 6 classes, 10 false activations (S01 7, S02 3): matches S01 4/7, S02 2/3, pooled 60.0 %; `time_sec` <= 2 s: 10, 2-4 s: 0, 4-5 s: 0.

## A-priori directions P1-P6 (values only; "holds / fails / inconclusive" as pre-committed)

- **P1.** fbcca cohort mean 69.16, 81.72, 87.78, 92.11 at 0.5, 1, 1.5, 2 s (strictly rising: holds); 2 -> 3 change +3.51, 3 -> 4 change +1.25 (no fall > 1 pp: holds); decreases > 2 pp between consecutive lengths per subject: 0 in all five (holds). lda cohort mean 81.80, 89.89, 93.42, 95.63 (rising: holds); 2 -> 3 +1.96, 3 -> 4 +0.44 (holds); decreases > 2 pp: 0 in all five (holds). cnn endpoints: Acc(4 s) 83.10 > Acc(0.5 s) 80.75 (holds).
- **P2.** Cohort ITR at 4 s below the maximum over lengths: fbcca 28.15 < 57.50, lda 28.93 < 84.37, cnn 21.56 < 87.25 (holds for all three). lda cohort maximum at 0.5 s (<= 1.5 s: holds). lda per-subject ITR peaks: S01 1.0 s, S02 1.0 s, S03 0.5 s, S04 0.5 s, S05 0.5 s; S03-S05 <= 1.5 s (holds); S01 and S02 (1.0 s) >= the shortest peak among S03-S05 (0.5 s) (holds). fbcca peaks: S01 3.0, S02 2.0, S03 1.0, S04 0.5, S05 0.5 s; cnn peaks: S01 1.0, S02 1.0, S03 0.5, S04 0.5, S05 0.5 s.
- **P3.** lda >= fbcca on the cohort mean at every length (holds: +12.64, +8.17, +5.64, +3.52, +1.98, +1.17 pp for 0.5 ... 4 s); lda >= fbcca in 5 of 5 subjects at 1 s and 5 of 5 at 2 s (holds). cnn minus lda cohort mean (pp): -1.06, +2.19, +1.05, -0.12, -2.31, -14.94 for 0.5, 1, 1.5, 2, 3, 4 s; the largest positive value is +2.19 (< 5 pp: no leak-check trigger). Per R-P5 (>= 3 pp and >= 4 of 5 subjects with the same sign): lda vs fbcca is a difference at 0.5, 1, 1.5, 2 s (means 12.64, 8.17, 5.64, 3.52; positive in 5, 5, 5, 4 of 5 subjects, 0 negative); not at 3 s (1.98) or 4 s (1.17). cnn vs lda: no length has cnn above lda by >= 3 pp (largest +2.19 at 1 s, positive in 5 of 5); at 4 s cnn is 14.94 pp lower, negative in 3 of 5 subjects and zero difference in 2.
- **P4.** Cohort means above chance (20 %): ccnn 91.25, compact_eegnet 92.08, eegnet 89.69 (holds). ccnn >= eegnet: 91.25 >= 89.69 (holds; +1.56 pp, per subject 2 positive, 1 negative, 2 zero, so not a difference by R-P5). Mean Train Acc >= mean Val Acc: ccnn 100.00 >= 92.99, compact_eegnet 99.91 >= 93.10, eegnet 98.89 >= 90.97 (holds).
- **P5.** Invariants G hold. lda at `Threshold` 0.5: `Forced (%)` of S03, S04, S05 = 0.0 at every window length (<= 10 %: holds). Time-matched comparison for lda, cohort best-threshold ITR vs single-window ITR: L = 0.5 s 61.53 vs 60.23 (holds), L = 1 s 53.73 vs 53.48 (holds). Against the roadmap fixed-window ITR at the same L (lda, cohort means above): 0.5 s 61.53 vs 84.37; 1 s 53.73 vs 70.03 (no direction committed).
- **P6.** (a) `False act. (%)` with 6 classes lower than with 5: S01 17.5 < 52.5, S02 7.5 < 45.0, S03 0.0 < 20.0, S05 0.0 < 20.0 hold; S04 0.0 vs 0.0 (equal, 40 rest periods scored): not strictly lower, so fails as worded for S04. (b) Acc 6 <= Acc 5 in 5 of 5 subjects (S04 equal, 100.00 / 100.00) (holds, >= 4). (c) min(S03, S04, S05) 5-class accuracy 97.50 > max(S01, S02) 90.00 (holds); 5-class Acc: S01 60.00, S02 90.00, S03 97.50, S04 100.00, S05 97.50.

## Numbers in the handoffs vs logs

05_run.md and this file take every number from `reports/logs/P20/*` (console output) or the CSVs under `reports/`: window sweep `summary.csv`, `nn_sweep/summary.csv` and `folds.csv`, `dynamic_stopping*/best_threshold.csv` and `per_subject.csv`, `pseudo_online/summary_*.csv` and `decisions_*.csv`. Derived values (time-matched ITR, R-P12, R-P9, P1-P6 comparisons, T_A, P_2b) come from the scripts in `mas/state/scratch/p20_verify/` with printed output in `reports/logs/P20/analysis_*.txt`. The draft report `mas/state/reports/P20.md` does not exist yet.

## Sources spot-check

Opened this run: `mas/state/phases/P20-detection-online/02_plan.md` (settled points 4, 5, 9: grouped folds, Wolpaw ITR with T = L + 0.5 s, dynamic-stopping decision rule) and the console/CSV outputs. Consistency: a perfect 1 s cell gives log2(5) x 60 / 1.5 = 92.88 bits/min (S05 `compact_eegnet` 100.00 % -> 92.88 in `reports/nn_sweep/summary.csv`), matching settled point 5. The dynamic-stopping minimum decision time of 1.0 s at L = 0.5 matches "time = offset + window length" with skip 0.5 s.

## Reference consultations check

`mas/state/scratch/reference_access.log` has 42 lines before and after this run; the last is the P19 scribe entry (2026-10-28T07:41:21); no P20 entry. The four P20 handoffs state "none". No unlisted access. I did not open the answer-key directory, and I did not read or list the raw-recordings directory or any `.ebr` file.

Privacy scan (vendor-token regex) over `git diff main...HEAD` and over the `git log main..HEAD` commit messages: 0 and 0 (the verifier's own commit is scanned before committing).

## Reasons (if FAIL)

None. Items for the reviewer: (1) the first-run suite flake of two hash-pinned tests (05_run.md, anomaly 1); (2) P6(a) for S04 is an equality (0.0 vs 0.0); (3) cnn at 4 s collapses for S02 (39.56 %, Train Acc 73.55 %) and S01 (77.00 %), a single-repeat cell.
