# P13 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (A1-A8, FDR windows, E1-E5), the phase branch
Clean checkout: `mas/state/scratch/verify/P13` @ 7f6cabb30d63d4059898fa3b4437d922960c58f6

All numbers come from the CSVs and logs named. Arithmetic: `mas/state/scratch/verify/analyze.py` (run with `.venv/bin/python`; its output is the source of the tables below). BH-FDR is over one-tailed (stimulus > baseline) edge p; npz `p_<cond>` are one-tailed. PDC uses 42 directed edges (`total_edges` = 42 in `reports/connectivity_cohort_summary.csv`; our choice, the roadmap's 21/28 are 7/8-channel undirected counts); coherence, PLV and wPLI use 21.

## Checks against the pre-committed criteria

### A1 Synthetic and demos: PASS
- Full suite: `796 passed, 21 warnings in 363.52s`, exit 0 (`reports/logs/P13/pytest_full.log`).
- `demo_mvar_slicing` exit 0, "in range" True (`reports/logs/P13/c2_demo_mvar.log`): strided 6.6 % (limit <= 15 %), contiguous 129.7 % (limit >= 100 %).
- `demo_hilbert_edges` exit 0, "in range" True (`reports/logs/P13/c1_demo_hilbert.log`): CSD PLV 1.0000 -> 0.9999 (change 0.0001, limit <= 0.005); Hilbert PLV 0.9793 -> 0.9530; Hilbert edge envelope 0.394-0.762 (first 15 samples) and 0.019-0.166 (last 15) of the centre for the bug variant (limit < 80 %).

Demo numbers next to the roadmap's (system-dependent; the qualitative claim is reproduced, not the magnitudes):

| Quantity | Roadmap | This run |
|---|---|---|
| Hilbert edge envelope | 5-70 % of truth, first/last ~15 samples | 39-76 % (first), 2-17 % (last) |
| CSD PLV, clean -> corrupted edges | 0.998 -> 0.998 | 1.0000 -> 0.9999 |
| MVAR contiguous slicing error | ~150-200 % | 129.7 % |
| MVAR strided error | ~5-10 % | 6.6 % |

### A2 FDR totals (trial200 final, concatenated coherence): FAIL (1 of 10 cells outside)
Source: `reports/connectivity_cohort_summary.csv` summed over the five conditions per subject x method (`analyze.py`).

| Method | Subject | Observed | R-12 | Window (07_review) | Inside? |
|---|---|---|---|---|---|
| coherence | S01 | 0 | 0 | 0-5 | yes |
| coherence | S02 | 0 | 0 | 0-5 | yes |
| coherence | S03 | 64 | 65 | 49-81 | yes |
| coherence | S04 | 49 | 51 | 39-63 | yes |
| coherence | S05 | 12 | 15 | 10-20 | yes |
| wPLI | S01 | 4 | 0 | 0-5 | yes |
| wPLI | S02 | 0 | 3 | 0-8 | yes |
| wPLI | S03 | 42 | 38 | 29-47 | yes |
| wPLI | S04 | 28 | 33 | 25-41 | yes |
| wPLI | S05 | 5 | 18 | 13-23 | **NO (5 < 13)** |

Per frequency (24 / 20 / 15 / 10.91 / 8.57 Hz), observed FDR edges, with R-12 in brackets:
- coherence S01 0/0/0/0/0 (0/0/0/0/0); S02 0/0/0/0/0 (0/0/0/0/0); S03 20/21/15/0/8 (20/21/16/0/8); S04 12/11/7/12/7 (12/11/7/12/9); S05 12/0/0/0/0 (12/3/0/0/0).
- wPLI S01 0/0/0/4/0 (0/0/0/0/0); S02 0/0/0/0/0 (0/3/0/0/0); S03 17/0/5/5/15 (17/0/3/3/15); S04 12/16/0/0/0 (12/17/0/4/0); S05 0/0/0/0/5 (0/0/0/13/5).
- The cells that make up the S05 wPLI deficit are 10.91 Hz (13 in R-12, 0 observed, global p 0.015 in both). Flip-list membership (A6) for S05 wPLI: not in the trial100-vs-final file; in `connectivity_cohort_flips_window200_vs_final.csv` as 24 Hz (10 -> 0 edges) and 10.91 Hz (3 -> 0 edges, window p 0.005, trial p 0.015). Approximate trial ids apply to S02 and S04 only, not S05 (`reports/connectivity_cohort_summary_details.csv`: S05 `trial_ids_approximate` False, clean 280/280 in the log). No E2 estimator dependence applies (S05 is not S03, wPLI has no estimator flag). This is a recorded deviation candidate for the results review; A2 as worded accepts it only with a mechanism shown by an output, and none of the three listed mechanisms is shown by the files for this cell. No re-run was made.

### A3 24 Hz pattern (criterion B, global p < 0.05): PASS
`reports/connectivity_cohort_summary.csv`, condition 101:

| Method | S01 | S02 | S03 | S04 | S05 |
|---|---|---|---|---|---|
| coherence | 1.000 | 1.000 | 0.005 | 0.005 | 0.005 |
| wPLI | 0.995 | 0.318 | 0.005 | 0.005 | 0.040 |
| R-12 coherence | 1.000 | 1.000 | 0.005 | 0.010 | 0.010 |
| R-12 wPLI | 1.000 | 0.323 | 0.005 | 0.005 | 0.015 |

All six S03-S05 cells significant; S01/S02 non-significant in both methods. No 24 Hz switch. Criterion A at 24 Hz: S05 wPLI has 0 FDR edges (R-12 0).

### A4 Only 24 Hz: PASS
Frequencies with p < 0.05 in all of S03-S05: coherence {24 Hz}; wPLI {24, 10.91, 8.57 Hz}; intersection of the two methods {24 Hz} (`analyze.py`). wPLI-only (descriptive, same as R-12): 10.91 Hz p 0.020/0.010/0.015, 8.57 Hz p 0.005/0.010/0.010 (S03/S04/S05).

### A5 S01/S02 null: PASS on the cells, FDR totals in window
Cells with p < 0.05 among each subject's 10 coherence + wPLI cells: S01 0, S02 0 (limit 1; none at 24 Hz). FDR totals inside the window (A2 table).

### A6 Flips trial100 vs final: PASS (file exists; listing below; not graded by count)
`reports/connectivity_cohort_flips.csv`; `reports/logs/P13/c6_compare_trial100.log`: "100 cells compared, 11 flip across alpha=0.05". All 11 carry `inconclusive` True. flip_B (global p crosses 0.05): 1. flip_A (any FDR edge appears or disappears): 10.

| Subject | Method | Cond (Hz) | p trial100 -> final | FDR edges trial100 -> final | flip_B | flip_A |
|---|---|---|---|---|---|---|
| S01 | wPLI | 104 (10.91) | 0.158 -> 0.154 | 0 -> 4 | no | yes |
| S02 | PDC | 101 (24) | 0.020 -> 0.015 | 0 -> 5 | no | yes |
| S03 | wPLI | 103 (15) | 0.069 -> 0.050 | 5 -> 5 | yes | no |
| S03 | PDC | 101 (24) | 0.010 -> 0.005 | 0 -> 5 | no | yes |
| S03 | PDC | 102 (20) | 0.010 -> 0.005 | 0 -> 5 | no | yes |
| S04 | PDC | 101 (24) | 0.010 -> 0.005 | 0 -> 5 | no | yes |
| S04 | PDC | 102 (20) | 0.079 -> 0.055 | 0 -> 5 | no | yes |
| S04 | PDC | 103 (15) | 0.317 -> 0.279 | 0 -> 5 | no | yes |
| S04 | PDC | 104 (10.91) | 0.040 -> 0.025 | 0 -> 6 | no | yes |
| S04 | PDC | 105 (8.57) | 0.257 -> 0.254 | 0 -> 5 | no | yes |
| S05 | PDC | 102 (20) | 0.040 -> 0.025 | 0 -> 5 | no | yes |

BH resolution mechanism (from 07_review: minimum non-zero FDR count 3 at 200 and 5 at 100 for 21 edges; 5 at 200 and 9 at 100 for 42 PDC edges): every flip_A row has 0 edges at 100 and 4 (S01 wPLI) or 5-6 at 200 (maximum of the two runs per row: 4, 5, 5, 5, 5, 5, 5, 6, 5, 5). The 100-permutation null is the first 100 draws of the 200-permutation null (07_review, `generate_state` prefix check), so the comparison is of nested draws. FDR totals of the trial100 run per method x subject (`connectivity_cohort_summary_trial100.csv`): coherence 0/0/63/48/14, wPLI 0/0/38/28/5, PLV 0/0/43/19/0, PDC 0/0/0/0/0.

### A7 Task 6, window200: PASS
- `reports/connectivity_cohort_summary_window200.csv`: 100 rows, `permutation_unit` = window in every row (unique values: window). trial100 and final: trial in every row.
- Window-level FDR totals (`..._window200.csv`): coherence 3/0/66/58/15, wPLI 0/3/46/37/20, PLV 0/0/47/24/0, PDC 0/0/15/27/0 (S01..S05).
- Comparison `reports/connectivity_cohort_flips_window200_vs_final.csv`, `c7_compare_window200.log`: "100 cells compared, 14 flip" (flip_B 4, flip_A 11). Cells: S01 coherence 104 (FDR 3 -> 0), S01 wPLI 104 (0 -> 4), S01 PDC 105 (p 0.035 -> 0.085, flip_B), S02 wPLI 102 (3 -> 0), S02 PDC 101 (0 -> 5), S03 wPLI 102 (p 0.020 -> 0.060, 5 -> 0, flip_B and flip_A), S04 PLV 102 (3 -> 0), S04 wPLI 104 (5 -> 0), S04 wPLI 105 (3 -> 0), S04 PDC 102 (p 0.035 -> 0.055, flip_B, 5 -> 5), S05 wPLI 101 (p 0.005 -> 0.040, 10 -> 0), S05 wPLI 102 (p 0.045 -> 0.065, flip_B), S05 wPLI 104 (3 -> 0), S05 PDC 102 (0 -> 5).
- Descriptive (not graded): window-level p <= trial-level p in 71 of 100 cells (coherence 18/25, wPLI 19/25, PLV 16/25, PDC 18/25). The window null has its own junction imbalance (+0.098) per 07_review C1.
- The file `connectivity_cohort_flips.csv` (trial100 vs final) was not overwritten by command 7 (11 rows before and after; the order of 6 and 7 follows the plan).

### A8 PLV and PDC: PASS (reported, no reference)
Global one-tailed p and FDR edges per frequency, trial200 (`connectivity_cohort_summary.csv`; PDC 42 directed edges); no reference values:

| Method | Subject | p (24/20/15/10.91/8.57 Hz) | FDR edges (same order) |
|---|---|---|---|
| PLV | S01 | 0.980/0.995/0.383/0.687/0.905 | 0/0/0/0/0 |
| PLV | S02 | 1.000/0.846/0.184/0.955/0.821 | 0/0/0/0/0 |
| PLV | S03 | 0.005/0.005/0.005/0.522/0.274 | 18/14/12/0/0 |
| PLV | S04 | 0.194/0.567/0.229/0.005/0.144 | 0/0/7/16/0 |
| PLV | S05 | 0.060/0.950/0.184/0.990/1.000 | 0/0/0/0/0 |
| PDC | S01 | 0.015/0.433/0.303/0.741/0.085 | 0/0/0/0/0 |
| PDC | S02 | 0.015/0.100/0.040/0.955/0.945 | 5/0/0/0/0 |
| PDC | S03 | 0.005/0.005/0.005/0.333/0.214 | 5/5/0/0/0 |
| PDC | S04 | 0.005/0.055/0.279/0.025/0.254 | 5/5/5/6/5 |
| PDC | S05 | 0.015/0.025/0.428/0.025/0.413 | 0/5/0/0/0 |

## Estimator rules E1-E5 (S03 coherence, concatenated trial200 vs aligned_S03)
Sources: `reports/connectivity_cohort_summary.csv`, `reports/connectivity_cohort_summary_aligned_S03.csv`, `reports/connectivity_alpha_diagnostic_aligned_S03.csv`, `c8_aligned_S03.log`.

| Frequency | p conc / aligned | FDR edges conc / aligned | A conc / aligned | B conc / aligned | Estimator-dependent (E2) | Aligned more significant (E3) |
|---|---|---|---|---|---|---|
| 24 Hz | 0.005 / 0.005 | 20 / 17 | yes / yes | yes / yes | no | no |
| 20 Hz | 0.005 / 0.005 | 21 / 19 | yes / yes | yes / yes | no | no |
| 15 Hz | 0.005 / 0.005 | 15 / 12 | yes / yes | yes / yes | no | no |
| 10.91 Hz | 0.786 / 0.637 | 0 / 0 | no / no | no / no | no | (not applicable) |
| 8.57 Hz | 0.104 / 0.697 | 8 / 0 | yes / no | no / no | **yes (criterion A)** | no |

- E1: all R-12 comparisons above use the concatenated run. The aligned total is 48 against 64 concatenated; it is not compared with R-12.
- E2: S03 coherence 8.57 Hz is estimator-dependent (criterion A: 8 edges vs 0). No other cell.
- E3: at 8.57 Hz the aligned estimator is the LESS significant one (p 0.697 vs 0.104; 0 vs 8 edges), so the mechanical label is "estimator-sensitive (not junction-biased)". No cell is labelled "junction-consistent".
- E4: the 8.57 Hz cell is inconclusive with both values (above). S03 24 Hz is not estimator-dependent, so no 24 Hz switch arises from E2.
- E5: S03 coherence lower-tail p (stimulus below baseline), concatenated / aligned (`connectivity_alpha_diagnostic.csv` / `_aligned_S03.csv`): 10.91 Hz 0.2189 / 0.3682; 8.57 Hz observed difference +0.0414 (concatenated) vs -0.0151 (aligned), `p_lower_tailed` 0.9005 / 0.3085. Neither is below 0.05 in either estimator. Coherence lower-tail values below 0.05 for S01, S02, S04, S05 are not cross-checked for junction effects: S02 coherence 8.57 Hz `p_lower_tailed` 0.0249; S05 coherence 10.91 Hz 0.0050 and 8.57 Hz 0.0348 (same file).

## Other checks
- Schemas: summary columns in the §6 order (`subject, method, condition, frequency_hz, label, obs_diff, p_one_tailed, significant_uncorrected, n_edges_sig_uncorrected, n_edges_sig_fdr, total_edges, n_channels, channels_dropped, permutation_unit, fdr_backed`); 20 npz files in `reports/connectivity_edges/` (4 methods x 5 subjects). Criteria (A) and (B) are printed on separate lists per frequency in the console (`c5_trial200_final.log`).
- Gate and ids (`..._details.csv`, `c5_trial200_final.log`): all 7 channels kept for every subject; clean windows 280/280 (S01), 272/278 (S02), 275/278 (S03), 274/277 (S04), 280/280 (S05); trial ids exact for S01, S03, S05 and APPROXIMATE for S02 and S04.
- Alpha diagnostic: `reports/connectivity_alpha_diagnostic.csv` has 40 rows (5 subjects x 4 methods x 104/105) with `p_one_tailed` and `p_lower_tailed`; printed Spearman rho (n = 5, descriptive) between matched baseline and difference: coherence 10.91 Hz -0.10, 8.57 Hz -0.30; PLV -0.60, -0.40; wPLI -0.90, -0.80; PDC -0.70, -0.40.
- Legacy arrays: sha256 identical before and after for all 15 files (`05_run.md`).
- R11: no reference consultation by this run; `mas/state/scratch/reference_access.log` last entry is 2026-10-26T12:05:15 (before P13 started).
- Reproducibility: all eight commands exit 0 on the first and only execution; no re-runs, no seed or permutation changes.

## Verdict reasons
1. A1, A3, A4, A5, A6, A7, A8: met as worded (above).
2. A2: 9 of 10 FDR-total cells inside the pre-committed window; wPLI S05 total is 5 against the window 13-23 (R-12 18). No mechanism listed in A2 (flip-list membership in the trial100 file, approximate ids, E2) is shown for it by the outputs. Per A2 this cell is "not within tolerance" unless the results review records it as a deviation.
3. E2: S03 coherence 8.57 Hz is estimator-dependent (inconclusive; "estimator-sensitive (not junction-biased)" by E3); it does not affect 24 Hz.

Verdict: FAIL
