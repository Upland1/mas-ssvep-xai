# P14 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (Round 1 criteria, Round 2), the phase branch
Clean checkout: `mas/state/scratch/verify/P14` @ 6b4ec212a0bb536e16e16c238fe672f9ffbcd31f (suite); pipeline in the main repository, same HEAD, porcelain-empty

Numbers come from `mas/state/scratch/p14_analysis.out` (script `mas/state/scratch/p14_analysis.py`, reading the CSVs below `reports/connectivity_comparison/`) and from `reports/logs/P14/*.log`. Everything is descriptive at 5 subjects (25 cells).

Verdict: PASS

## Tests on the clean checkout

`.venv/bin/python -m pytest tests -o addopts="" -q` → `2 failed, 871 passed, 1 skipped, 21 warnings in 402.78s (0:06:42)`, exit 1 (`reports/logs/P14/pytest_full.log`).
Failed: `tests/test_p14_connectivity_comparison.py::test_null_diagnostic_csv_leaves_primary_csvs_untouched` and `::test_random_state_and_suffix_for_diag_e3`. Both raise `FileNotFoundError: .../reports/n_subjects_benchmark.csv`: `run()` reads the responders from this ignored, generated file (`tests/test_p14_connectivity_comparison.py:137,500,522` pass no `--responders`). Re-run in the main repository, where the file exists, they pass (`2 passed in 4.95s`, `reports/logs/P14/pytest_two_failed_in_main.log`). Hence: a test-isolation defect, not a scientific one.

## Acceptance

Input integrity: pre-check hash `804b1ced…e697` before the run and again after it (identical to the pinned value). Legacy arrays: sha256 of the 18 `data/processed/**/*.npy` files, before and after: file lists `mas/state/scratch/p14_legacy_before.txt` / `_after.txt` are byte-identical (`cmp`), sha256 of each list `6120eb9ce5770a71c16016cfb02830472d9e44672ff4a7a150bb48c8821d559e`.

### Integrity (A0–A2)

| Check | Result | Met? |
|---|---|---|
| A0 `t_mag` = `mean_delta(freq_a) − mean_delta(freq_b)` for every row of the 3 final and 3 p500 pairwise CSVs | max abs diff = 1.94e-16 (≤ 1e-9) | yes |
| A1 `t_mag, d_pat, r_obs, reliability_ceiling, split_half_reliability` identical p500 vs final | max abs diff 0.0 for all three methods; `r_disattenuated` equal (NaN-aware) | yes |
| A2 §6 CSVs with exact columns; 50 pairwise and 25 reliability rows per method; roadmap figures | all column lists equal §6 (`pairwise_null` equals the F2 list); 50 / 25 rows per method; 21 figures including `connectivity_delta_vs_power.png`; `pdc` has similarity, node strength, global delta (PDC excluded from tasks 2) | yes |

### Qualitative comparisons with R-13 (E1–E5)

| Item | Obtained | R-13 | Consistent? |
|---|---|---|---|
| E1 Fisher-mean r / share p_qap < 0.05 (50 cells) | coherence 0.629 / 0.66; wPLI 0.1629 / 0.32; (PLV 0.510 / 0.62). Arithmetic mean r: coherence 0.5354, wPLI 0.1429 | 0.54 / 64 %; 0.14 / 32 % | consistent (coherence > wPLI on both) |
| E2a median reliability | coherence 0.9239; wPLI 0.5165 (PLV 0.6819) | 0.92 vs 0.54 | consistent |
| E2b cells ≥ 0.75 | coherence 20; wPLI 4 (PLV 11) | 22 vs 3 | consistent |
| E2c non-positive (uncorrected) cells | wPLI 3 (min −0.252); coherence 2 (min −0.163); PLV 0 | 0 vs 3 | consistent as pre-committed (wPLI ≥ 1 and coherence < wPLI); coherence 2 vs R-13 0 noted |
| E2d three lowest coherence cells | S01 10.91 (−0.163), S02 10.91 (−0.003), S02 8.57 (0.549): all in-alpha of S01/S02 | S01/S02 in-alpha | yes (descriptive) |
| E3 counts, p500, p_mag<.05 / p_pat<.05 of 50 | coherence 11 / 1; wPLI 6 / 2 (PLV 14 / 2); final: 10 / 1, 6 / 2, 14 / 2 | 6 / 1; 6 / 2 | consistent (p_mag ≥ p_pat both); margins 10 and 4 > 1 |
| E3 trigger (margin ≤ 1 cell) | not fired (margins 10 coherence, 4 wPLI) → DIAG-E3 not run | | n/a |
| E4 per-subject mean SNR (dB), coherence cells | S01 0.053, S02 0.282, S03 5.594, S04 8.234, S05 4.295 | 0.05, 0.28, 5.59, 8.23, 4.29 | consistent (S03–S05 > 3, S01–S02 < 1) |
| E4 in-alpha < out-of-alpha SNR | 5 of 5 subjects; cohort 2.017 vs 4.808 dB | 5 of 5; 2.02 vs 4.81 | consistent |
| E5 alpha change | 23 of 25 cells < 0; mean −1.0005 dB; S05 −1.900 (most negative subject) | 23 of 25; −1.0; −1.90 | consistent |

### Acceptance question 1 (`power_confound_ols.csv`, `power_confound_correlations.csv`)

Attribution: `snr_share = r2_snr_only / r2`; `alpha_add = r2 − r2_snr_only` (command: `mas/state/scratch/p14_analysis.py`, section Q1).

| Method | Scope | R² | SNR only | alpha only | alpha_add | snr_share | Wording |
|---|---|---|---|---|---|---|---|
| coherence | all | 0.6750 | 0.6681 | 0.0179 | 0.0069 | 0.990 | largely explained; SNR-dominated; alpha adds little |
| coherence | centred | 0.5400 | 0.5251 | 0.0104 | 0.0149 | 0.972 | largely explained; SNR-dominated; alpha adds little |
| PLV | all | 0.4293 | 0.3852 | 0.0016 | 0.0441 | 0.897 | partly explained; SNR-dominated; alpha adds little |
| PLV | centred | 0.2995 | 0.2991 | 0.0343 | 0.0005 | 0.9985 | partly explained; SNR-dominated; alpha adds little |
| wPLI | all | 0.5299 | 0.4708 | 0.1716 | 0.0591 | 0.889 | largely explained; SNR-dominated; alpha adds little |
| wPLI | centred | 0.0014 | 0.0002 | 0.0008 | 0.0012 | 0.162 | not explained; all ≥ 0.5 and centred < 0.2: "the relation is between subjects (responders vs non-responders), not across frequencies within a subject" |
| PDC | all | 0.4346 | 0.3891 | 0.0018 | 0.0455 | 0.895 | partly explained; SNR-dominated; alpha adds little |
| PDC | centred | 0.3650 | 0.3275 | 0.1274 | 0.0375 | 0.897 | partly explained; SNR-dominated; alpha adds little |

Spearman (SNR / alpha, all; centred): coherence 0.7069 / −0.1238; 0.5531 / 0.1146. PLV 0.5338 / 0.0238; 0.3954 / 0.2285. wPLI 0.7392 / −0.3208; 0.0369 / 0.1985. PDC 0.5646 / 0.0715; 0.5777 / 0.2346.
R-13 consistency: coherence consistent (all 0.675 ≥ 0.5; centred 0.540 ≥ 0.3; SNR-dominated in both; ρ_SNR > |ρ_alpha| in both). wPLI consistent (all-cells ρ_SNR 0.7392 > 0.4; centred R² 0.0014 < 0.2). PLV and PDC have no reference.

### Acceptance question 2 (in-alpha minus out-of-alpha, per subject; `power_vs_connectivity_cells.csv`, SNR adjustment by residuals of centred `mean_delta ~ centred SNR`)

| Method | Raw in − out (S01..S05) | positive | SNR-adjusted in − out (S01..S05) | positive | Reading |
|---|---|---|---|---|---|
| coherence | +0.075, +0.056, −0.219, +0.063, −0.145 | 3 | +0.103, +0.065, −0.045, +0.131, −0.043 | 3 | no consistent in-alpha difference (positive S01, S02, S04; negative S03, S05); equals R-13-implied |
| PLV | +0.010, +0.009, −0.093, +0.043, −0.075 | 3 | +0.020, +0.012, −0.030, +0.067, −0.039 | 3 | no consistent in-alpha difference (positive S01, S02, S04; negative S03, S05) |
| wPLI | +0.297, −0.074, +0.033, −0.214, +0.144 | 3 | +0.298, −0.074, +0.040, −0.211, +0.148 | 3 | no consistent in-alpha difference (positive S01, S03, S05; negative S02, S04); equals R-13-implied |
| PDC | −0.006, −0.035, −0.026, −0.008, −0.008 | 0 (5 of 5 negative) | −0.001, −0.034, +0.001, +0.003, +0.008 | 3 | only (i) holds → "differ, but consistent with their lower SNR" |

Group means (`power_confound_alpha_split.csv`): in-alpha vs out-of-alpha mean_delta: coherence 0.013 vs 0.047, PLV −0.005 vs 0.016, wPLI 0.213 vs 0.176, PDC 0.008 vs 0.025; mean alpha change −1.175 vs −0.884 dB. The in-alpha alpha measure rests on 2 bins (10.91 Hz) or 3 bins (8.57 Hz) against 5 for the others.

### P13 D-3 (S05, exploratory, not graded; `power_confound_s05.csv`)

S05 coherence delta < 0 at 10.91 (−0.084) and 8.57 (−0.097) Hz; PLV −0.071 and −0.060; wPLI +0.374 and +0.305. S05 in-alpha mean alpha change −2.260 dB, the most negative of the cohort (others: S01 −0.966, S02 −0.156, S03 −1.099, S04 −1.393); in-alpha SNR 1.816 and 2.291 dB. So the "consistent with alpha blocking lowering amplitude-sensitive measures" hypothesis wording is admissible, as a hypothesis only.

### Cells labelled "null off-centre" (`p_mag` and `p_mag_centred` on different sides of 0.05; reported only)

Final run (1000 permutations; `<m>_pairwise_tests.csv` joined with `<m>_pairwise_null.csv`; columns: subject, freq_a, freq_b, t_mag, p_mag, p_mag_centred, t_null_mean, t_null_sd):
- coherence (4): S01 24/20 (−0.0418, 0.029, 0.0669, −0.0086, 0.0186); S01 20/8.57 (−0.0353, 0.042, 0.0559, −0.0021, 0.0175); S03 15/10.91 (0.1992, 0.039, 0.0799, 0.1256, 0.0415); S05 24/8.57 (0.2343, 0.035, 0.0819, 0.1636, 0.0411).
- PLV (4): S01 15/8.57 (0.0087, 0.973, 0.0470, 0.0147, 0.0034); S03 24/10.91 (0.1056, 0.042, 0.0839, 0.0662, 0.0232); S04* 20/8.57 (−0.0355, 0.3506, 0.0070, 0.0260, 0.0233); S05 15/10.91 (0.0996, 0.028, 0.0619, 0.0418, 0.0301).
- wPLI (5): S01 24/8.57 (−0.2020, 0.1828, 0.0110, 0.0847, 0.1244); S02* 24/8.57 (0.0596, 0.6424, 0.0330, −0.0797, 0.0675); S03 24/20 (0.3320, 0.028, 0.1059, 0.1978, 0.0908); S05 20/8.57 (−0.1488, 0.037, 0.0549, −0.0367, 0.0586); S05 15/8.57 (−0.2464, 0.023, 0.0549, −0.0641, 0.0961).
(* = approximate trial ids, S02/S04.) The p500 run lists coherence 5, PLV 2, wPLI 3 such cells (full tables in `mas/state/scratch/p14_analysis.out`). Flip list (cells crossing 0.05 on any criterion, p500 vs final): 150 compared, 8 flip, inconclusive (R7; nested nulls, P13 D-4), `reports/connectivity_comparison/pairwise_flips.csv`.

## Numbers in the handoffs vs logs

The numbers in `05_run.md` (hash, exit codes, runtimes, counts 5 of 75 and 150/8) were read from the logs `reports/logs/P14/*.log`. The builder's task-1 smoke figures in `log.md` (coherence 0.629 / 66 %, wPLI 0.163 / 32 %) equal the full run (0.629 / 0.66; 0.1629 / 0.32). The runtime estimate of 18–34 min in `02_plan.md` and `log.md` was low: 67.55 min measured.

## Sources spot-check

`mas/04_REFERENCE_RESULTS.md` R-13 opened: the E1/E2/E4/E5 reference values quoted by the reviewer (0.54 / 64 %, 0.14 / 32 %, 23 of 25, −1.0 dB, SNR means 0.05 … 4.29) are the values compared here. `mas/02_REQUIREMENTS.md` §6 opened: column lists compared in A2.

## Reference consultations check

`03_changes_connectivity-stats.md` and `04_tests.md` list none. `mas/state/scratch/reference_access.log` has no P14 entry (last entries 2026-10-26T12:05, deep-learning). No unlisted access.

## Reasons (if FAIL)

1. The full suite on the clean checkout is red: `2 failed, 871 passed, 1 skipped` (`reports/logs/P14/pytest_full.log`, exit 1). `test_null_diagnostic_csv_leaves_primary_csvs_untouched` and `test_random_state_and_suffix_for_diag_e3` read the generated, git-ignored `reports/n_subjects_benchmark.csv` through `responders_from_benchmark` because they pass no `--responders`/`--benchmark`. This breaks the verification standard (`pytest tests/` runs with no generated or real data). Fix is tests-only (pass `--responders` or a synthetic benchmark CSV in `tmp_path`); `src/` and `scripts/` are unchanged, so no pipeline rerun should be needed, and a re-run of the suite on a clean checkout would settle it.

Everything else passed: A0–A2 met; E1–E5 consistent with R-13; DIAG-E3 not triggered; inputs and legacy arrays unchanged; nothing else blocks the phase.

## Round 2 restatement

1. `git diff --stat 6b4ec21 HEAD -- src scripts configs` prints nothing: the code that produced the outputs is unchanged, so the first-run outputs stand and no rerun was needed.
2. Clean-checkout suite at 1e9dcac (`reports/logs/P14/pytest_full_round2.log`, exit 0), summary verbatim: `873 passed, 1 skipped, 21 warnings in 405.69s (0:06:45)`. The two tests that failed in Round 1 now pass without generated files. Reason 1 above is closed.
3. Outputs: all 82 files in `reports/connectivity_comparison/` and `outputs/figures/connectivity_comparison/` have mtimes at or before 21:13:46 (end of the confound run); the verifier's analysis script gives output identical to the first run (`mas/state/scratch/p14_analysis_round2.out`), so A0–A2, E1–E5, the R² bands, the in-alpha rule and the "null off-centre" lists stand as stated above. Sha256 manifest: `mas/state/scratch/p14_outputs_round2.txt`.

Verdict: PASS
