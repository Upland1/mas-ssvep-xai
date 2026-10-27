# P14 · 07 · Scientific review

Status: READY (pre-run audit Round 1: FAIL)
Author: scientific-reviewer
Reads: 00_assignment.md, 02_plan.md, 03_changes_connectivity-stats.md, 04_tests.md, decisions.md P12–P14 rows, mas/state/reports/P13.md, mas/RULES.md, mas/03_ROADMAP.md P14, mas/02_REQUIREMENTS.md §6, mas/04_REFERENCE_RESULTS.md R-13, mas/05_PITFALLS.md PF-19, PF-21–PF-27, `git diff main..HEAD -- src scripts tests` (HEAD 79bd81f)

## Pre-run audit — Round 1

Audited commit: 79bd81f (code b705d73, ae547e0; tests ece4cb5, 884dae3). Line numbers come from `cat -n` on single files.

Verdict: FAIL

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A (no classifier CV). The responders come from the R1-compliant P11 benchmark: `reports/n_subjects_benchmark.meta.txt` line 1 reads "cv=StratifiedGroupKFold(5, shuffle, 42) over reconstructed trial ids (R1, leak-free)". | `src/features/connectivity/comparison.py:160-171` |
| R2 Fit only in-fold | PASS. Nothing is fitted for prediction. The OLS and Spearman fits are descriptive over all 25 cells, and they are labelled that way. | `scripts/connectivity/diagnostics/check_power_alpha_confound.py:124-163` |
| R3 Filter continuous, then window | PASS. The P13 machinery is reused: coherence from Welch on concatenated windows, PLV and wPLI phase from the CSD. There is no filtfilt or Hilbert on windows. The confound script uses unfiltered Hann periodograms. | `comparison.py:276-285`; `check_power_alpha_confound.py:62-66` |
| R4 Estimator small-sample bias | PASS. Coherence uses the concatenated estimator per group. The split halves have equal sizes, so the size bias is common to both halves. The pairwise null keeps the observed sizes. | `comparison.py:197-235`, `:298-304`; `permutation.py:56-82` |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design; R5 is enforced from P16). One P07 gate per subject over 101–105 and 201, with every threshold explicit (`GATE`). Tasks 2 and 3 use the same gate. | `connectivity_extraction.py:35`, `:265-287`; `test_connectivity_frequency_differences.py:119-127` |
| R6 Index layouts verified | PASS. Embedding is by name (PF-26). QAP permutes rows and columns with the same permutation, and this is checked against exhaustive 5!, 6! and 7! relabellings (a rows-only mutant fails). PDC is symmetrized before every undirected statistic (PF-25). | `comparison.py:37-52`, `:143-144`; `tests/test_p14_known_answer.py:188-224` |
| R7 Honest statistics | **FAIL** (F2). The permutations are trial-level with the observed sizes (PF-19), and the null draws are shared and nested. The nesting is stated and BH runs per subject and method. But the magnitude and pattern tests do not test the hypothesis their labels state; see "Pairwise design" below. | `comparison.py:250-316`; `test_connectivity_frequency_differences.py:11-15` |
| R8 Smoothing respects trials | N/A (no smoothing; the 2.0 s column is read from P11) | — |
| R9 Per-subject reporting with data source | PASS. Every table is per subject. Consoles and docstrings label the source and fs-250. `split_half_details` carries `fs` and `source`. The pairwise CSV flags approximate ids. | `test_connectivity_frequency_differences.py:72`, `:201-209`; `compare_connectivity_frequencies.py:58` |
| R10 Every change and test cites a source that exists and says what is claimed | PASS. Spot-checked: R-13 smoke numbers against `04_REFERENCE_RESULTS.md` (0.54 / 64 %, 0.14 / 32 %); the S05 coherence row matches R-13. | `03_changes_connectivity-stats.md` "How I verified" |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A (no copied code) | — |
| R11 Reference consulted only after an attempt, every consultation listed | PASS. The handoff lists none, and `mas/state/scratch/reference_access.log` has no P14 entries (last entries are from 2026-10-26T12:05, deep-learning, an earlier phase). | access log tail |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | LEGACY (by design): fs-250 axis via `--fs` (default `LEGACY_FS_HZ`), labelled; fs from metadata is enforced from P16 | `test_connectivity_frequency_differences.py:109`; `check_power_alpha_confound.py:231` |
| Tests cover every change; at least one fails on the historical bug | **FAIL** (F1). 70 P14 tests pass (`pytest tests/test_p14_connectivity_comparison.py tests/test_p14_known_answer.py -q` → `70 passed in 34.96s`). PF-22, PF-23, PF-25, PF-26, PF-27 and PF-19 each have a failing-on-bug test. However, the committed tester handoff `04_tests.md` (e4c9817) is the empty template: no test table, no mutants, no command output, no coverage gaps. The log's "8 mutants caught" therefore cannot be checked. A coverage gap: no test has a pairwise null that is off-centre (F2). | `04_tests.md` (e4c9817); `log.md` step 6 |
| Changes match 02_plan.md and the roadmap tasks | PASS. The extra CSVs leave the §6 schemas unchanged, and every §6 column list matches exactly: `SIM/NODE/GLOBAL_COLUMNS`, `PAIRWISE/RELIABILITY_COLUMNS`, `TABLE_COLUMNS`, and the merge adds `method, mean_delta`. | `compare_connectivity_frequencies.py:55-57`; `test_connectivity_frequency_differences.py:64-67`; `check_power_alpha_confound.py:57-58`, `:191-193` |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS. A fragment-built `git grep`/`git log` vendor and trailer scan of `main..HEAD` returns nothing. The diff touches no data, reference or local-tooling path. | `git diff --stat main..HEAD -- data reference` (empty) |

### Item-by-item checks requested

- **PF-21 (responders).** These come from the leak-free P11 benchmark only; the 2.0 s values are 67.5, 61.73, 90.36, 97.97 and 95.5, so S03, S04 and S05 are responders. The `Mean` row is ignored, and NaN counts as non-responder (`comparison.py:160-171`). There is no connectivity input. `test_responders_independent_of_connectivity` flips the deltas and the groups stay fixed. PASS.
- **PF-22.** SB is applied only if the Fisher-mean r > 0, else r is left uncorrected and labelled "not reliable" (`comparison.py:176-180`, `test_connectivity_frequency_differences.py:144`). The ceiling is NaN unless both reliabilities are > 0, and the disattenuated r is computed only if the ceiling > 0.1 and is not clipped (`:183-194`). PASS. The §6 `split_half_reliability` column mixes SB values with uncorrected r; the flag lives only in `_details` (N2).
- **PF-23 and the Hann leakage.** One mask is shared by stimulus and baseline (`check_power_alpha_confound.py:78-93`). On the fs-250 axis, the kept alpha bins are 8.789 and 12.695 Hz for 10.91 Hz, and 10.742, 11.719 and 12.695 Hz for 8.57 Hz. The builder's −28.3 dB figure is for a tone simulated at fs 250. In the real geometry, a true 10.91 Hz tone sampled at 256 Hz sits at labelled 10.65 Hz. Its leakage into the kept bins is −35.0 and −37.9 dB re the peak; for 8.57 Hz it is −30.6, −40.5 and −47.5 dB. The bias of `alpha_change_db` is at most +0.016 dB at 10 dB SNR with a flat background, and +0.05 dB if the kept alpha bins carry only 0.3× the target-bin power. R-13's in-alpha alpha changes are −0.53 to −2.68 dB, except S02 8.57 (+0.23), and the observed in-alpha SNRs are ≤ 7.74 dB. **The leakage is immaterial**, and the settled point stands. The f0 ± 1 Hz target band captures 0.83 of a true tone's power at 24, 20 and 15 Hz, 0.78 at 10.91 Hz and 0.96 at 8.57 Hz, so the in-alpha SNR is not systematically under-read by the axis (PF-04, legacy). Command: the inline `periodogram(sin(2π f0 t), t = arange(256)/256, fs=250, window="hann")` computation in this review's session, reproduced in N1.
- **PF-24.** Only `diff_`, `fdr_` and `channels_kept` are read (`compare_connectivity_frequencies.py:86-96`, a spy test at `test_p14_known_answer.py:118`). Similarity is judged on the QAP p (one-tailed `r_perm ≥ r_obs`, +1), and no path-length measures exist. PASS. The report must read QAP p and pair differences, not raw r (E1 below).
- **PF-25.** `(M + Mᵀ)/2` is applied for PDC before the similarity r and node strength. `mean_upper` of the symmetrized matrix equals P13's mean over the 42 directed entries, and the FDR count stays over 42 directed edges (`comparison.py:55-72`). PASS.
- **PF-26.** Embedding is by name with NaN, PO7 is NaN in every legacy subject, and QAP permutes only the shared channels (`comparison.py:112-131`). PASS.
- **PF-27.** `git ls-files | grep -i cofound` is empty; only `scripts/connectivity/diagnostics/check_power_alpha_confound.py` exists; and two tests check this. PASS.
- **Pairwise design (settled point 4).** I checked it by inspection (`comparison.py:274-312`) and with a reviewer synthetic: 60 replicates, 12 trials × 5 windows per condition, 199 permutations. In the synthetic, `fn` scores the first or second half of each window as "band A" or "band B". The command was an inline `.venv/bin/python -` script calling `cmp.pairwise_permutation_test` (output below).
  - *Fixed baseline.* The baseline enters observed and null statistics as the same constant matrices `base_a`, `base_b` (`:279-284`, `:300-304`). Fixing it is therefore correct: the test is conditional on the baseline, which is neither biased nor double-counted. Permuting 201 windows into the pool would test a different hypothesis.
  - *Shared draws.* Magnitude, pattern and edge statistics use the same `(ia, ib)` per draw (`:296-308`; spy test `test_p14_known_answer.py:524-543`). PASS.
  - *Which null.* The re-split exchanges whole trials of a and b, and each group is scored in its own band. The null is therefore **"the trials of a and b are exchangeable"**, not "Δa = Δb". Under that null, `t_mag` is centred at E[t] = [M(pool; band a) − base_a] − [M(pool; band b) − base_b], which is not 0 in general. The two hypotheses part ways in both directions:

    | Synthetic case | mean t_obs | P(p_mag < .05) | mean p_mag | P(p_pat < .05) |
    |---|---|---|---|---|
    | exchangeable a/b, both raise band A only (Δa − Δb = +0.38, a generic band effect) | +0.379 | 0.03 | 0.54 | 0.03 |
    | a raises A, b raises B, equally (Δa = Δb) | −0.000 | 0.00 | 0.56 | 0.00 |
    | Δa = Δb = 0, but b-trials raise band A (cross-band response) | −0.000 | 0.00 | **1.00** | **0.22** |

    The size is valid for the exchangeability null: |t| and d are computed identically on observed and permuted data, so the p-values are not anti-conservative. But three readings are wrong: "p_mag ≥ 0.05 ⇒ Δa ≈ Δb", "two-sided around 0" (the third row's null is centred at +Δ/2, so p_mag = 1.00) and "p_pat < 0.05 ⇒ Δa and Δb have different patterns" (22 % rejections with no delta at all). The prescribed statistic stays primary (roadmap, R-13 comparability). The wording and a null-centre diagnostic are required (F2).
- **BH across the 10 pairs.** BH runs per subject and method, separately for `p_mag` and `p_pat`, and NaN `p_pat` is treated as 1 (`test_connectivity_frequency_differences.py:171-174`). PASS. Resolution: at 500 permutations p_min = 1/501, and the first BH step needs p ≤ 0.005, i.e. ≤ 1 exceedance. At 1000 it needs ≤ 4 exceedances. Edge FDR over 21 edges: ceil(p_min·21/0.05) = 1 at both counts, so no BH minimum-count block arises (cf. P13 D-4).
- **Fisher-combined p.** The closed form is tested to 1e-12 (`comparison.py:240-247`). The responder group has n = 3 and the non-responder group n = 2. The p-values are not corrected across 10 pairs × 2 statistics, and they are pseudo-count discretised. They are descriptive only, and the report must say so with k (N3).
- **Within-subject centred OLS.** All three variables are centred per subject before OLS with an intercept (`check_power_alpha_confound.py:117-121`, `:148-156`). This equals the within (subject fixed-effects) R², with 20 rather than 23 residual df. It is the right companion to the all-cells R²; p-values stay descriptive (N4).
- **Determinism.** The QAP seed is per (subject, method, a, b), the split-half seed per (subject, method, c, "splithalf") and the pairwise seed per (subject, method, "pair", a, b). None depends on `n_jobs` or on the job order. The smoke shows `n_jobs` 1 and −1 to be byte-identical (`cmp`). The 500/1000 nulls are nested, and the docstring at `:24-25` says so. PASS.
- **Schemas.** These are listed in the table above. PASS.
- **Inputs.** The P13 final edge files match `reports/connectivity_cohort_summary.csv` (100 rows, FDR counts and global differences exactly; `permutation_unit` = trial only). They were written at 18:12–18:17, before DIAG-A2, and the DIAG-A2 runs wrote to `connectivity_edges_diagA2_rs<B>/`. The coherence and wPLI global deltas equal the R-13 table in all 25 + 25 cells to 3 decimals (max |diff| 0.000). Pinned: `sha256sum reports/connectivity_edges/*.npz reports/n_subjects_benchmark.csv | sha256sum` → `804b1ced5c949644f22396ca35aa17b5090f2068654ff559c2f7b02a3649e697`. The verifier recomputes this before the first command, and a mismatch stops the run.
- **Run commands vs acceptance.** The order is right: task 1 → p500 → final → compare → confound. The confound script stops with a message if `<m>_global_delta.csv` is missing (`check_power_alpha_confound.py:185-186`). All §6 CSVs and figures are produced, and `reports/connectivity_comparison/` does not exist yet, so no output is stale. Missing: the F2 diagnostic CSV and the conditional DIAG-E3 command (F3).

### Pre-committed criteria for the results review

Written before any real P14 run. Seen beforehand: the P13 deltas, which are inputs (= R-13), and the builder's task-1 smoke (coherence 0.629 / 66 %, wPLI 0.163 / 32 %). For that reason, no numeric band is set on the similarity values. "R-13-implied" values are my arithmetic on the R-13 tables as printed. This is review-only, using numpy `lstsq` and scipy `spearmanr` over the 25 cells; within-subject centring subtracts each subject's mean over its 5 frequencies.

**Integrity (graded; a failure is FAIL):**
- A0. For every row of `<m>_pairwise_tests.csv` and `_p500.csv` (coherence, PLV, wPLI): `t_mag` = `mean_delta(freq_a) − mean_delta(freq_b)` from `<m>_global_delta.csv`, |diff| ≤ 1e-9. This proves that tasks 1 and 2 used the same gate, windows and estimator.
- A1. `t_mag`, `d_pat`, `r_obs`, `reliability_ceiling` and `split_half_reliability` are identical between p500 and final. They do not depend on the permutation count.
- A2. Every §6 CSV and the figures listed in the roadmap exist, with exact columns. There are 50 pairwise rows per method and 25 reliability rows per method.

**Qualitative comparisons with R-13 (graded as consistent / not consistent; a "not consistent" is reported and explained, not a FAIL by itself):**
- E1 Similarity ordering. Across the 50 subject × pair cells, coherence > wPLI on the Fisher-mean r **and** on the share with p_qap < 0.05 (R-13: 0.54 / 64 % vs 0.14 / 32 %). The arithmetic mean r is reported as well, because R-13 does not say which mean it used.
- E2 Reliability pattern, over the 25 cells per method:
  - (a) median coherence reliability > median wPLI reliability (R-13 0.92 vs 0.54);
  - (b) more coherence cells ≥ 0.75 than wPLI cells (R-13 22 vs 3);
  - (c) wPLI has at least one non-positive, uncorrected cell, and coherence has fewer non-positive cells than wPLI (R-13 0 vs 3);
  - (d) descriptive only: the three lowest coherence cells in R-13 are in-alpha cells of S01/S02 (0.02, 0.34, 0.42); I report whether ours are.
  - Each split-half value is a 10-split Monte Carlo estimate, so single cells are not compared.
- E3 Pairwise counts on the p500 run, against R-13's 6 magnitude / 1 pattern (coherence) and 6 / 2 (wPLI) of 50. Consistent if the p_mag < 0.05 count ≥ the p_pat < 0.05 count for both coherence and wPLI. The counts are reported, not graded. If either inequality holds or fails by a margin of ≤ 1 cell, run DIAG-E3 (F3).
  - DIAG-E3 is that method only, 500 permutations, `--random-state` bases 42, 1, 2, 3, 4, 5.
  - R0: base 42 must equal `_p500` exactly; otherwise a determinism investigation follows.
  - The result is consistent if ≥ 4 of 6 bases satisfy the inequality, not consistent if ≤ 2 of 6 do, and inconclusive at 3 of 6. Monte Carlo resolution is an admissible mechanism (P13 D-4).
  - No FDR-edge count and no flip count is graded in P14. Flips are listed and labelled inconclusive (R7).
- E4 SNR, per-subject mean `target_snr_db` over the 5 frequencies:
  - S03, S04 and S05 each > 3 dB, and S01 and S02 each < 1 dB (R-13 means 0.05, 0.28, 5.59, 8.23 and 4.29);
  - the in-alpha mean SNR < the out-of-alpha mean SNR in ≥ 4 of 5 subjects (R-13 5 of 5; cohort 2.02 vs 4.81 dB).
  - Per-cell |ours − R-13| > 1 dB is listed with an explanation; it is not graded.
- E5 Alpha change is mostly negative: ≥ 20 of 25 cells < 0, and the cohort mean < 0 (R-13: 23 of 25, mean −1.0 dB, S05 the most negative subject at −1.90).

**Acceptance question 1, "how much of the delta is explained by target SNR and alpha change".** This is judged per method from `power_confound_ols.csv` (`r2`, `r2_snr_only`, `r2_alpha_only`, scope `all` and `centred`) and `power_confound_correlations.csv`. Every number is descriptive at 5 subjects (25 cells).
- Wording by full-model R²:
  - R² ≥ 0.5 → "largely explained";
  - 0.2 ≤ R² < 0.5 → "partly explained";
  - R² < 0.2 → "not explained".
- Attribution:
  - "SNR-dominated" if `r2_snr_only` ≥ 0.8 × `r2`;
  - "alpha adds" only if `r2 − r2_snr_only` ≥ 0.10;
  - otherwise "alpha adds little".
- Level: if `all` R² ≥ 0.5 and `centred` R² < 0.2, the report says "the relation is between subjects (responders vs non-responders), not across frequencies within a subject".
- Consistency with R-13 (R-13-implied):
  - Coherence: R² 0.675 all / 0.541 centred; SNR-only 0.668 / 0.526; ρ_SNR 0.706 / 0.550; ρ_alpha −0.113 / 0.114. It is consistent if all ≥ 0.5, centred ≥ 0.3, SNR-dominated in both scopes, and ρ_SNR > |ρ_alpha| in both.
  - wPLI: R² 0.530 all / 0.001 centred; SNR-only 0.471 / 0.000; ρ_SNR 0.739 / 0.039. It is consistent if the all-cells ρ_SNR > 0.4 and the centred R² < 0.2, i.e. the between-subject pattern.
  - PLV and PDC have no reference; they are reported with the same wording rules.

**Acceptance question 2, "whether 10.91/8.57 Hz behave differently".** This is judged per method on the per-subject in-alpha minus out-of-alpha mean delta (the mean of 2 cells minus the mean of 3), computed from `power_vs_connectivity_cells.csv` with a shown command, plus `power_confound_alpha_split.csv` (`mean_delta_centred`).
- "Behave differently" requires two conditions:
  - (i) the per-subject in − out has the same sign in ≥ 4 of 5 subjects;
  - (ii) after the within-subject SNR adjustment, the same sign holds in ≥ 4 of 5 subjects. The adjustment uses the residuals of centred `mean_delta ~ centred SNR`, and the measure is the mean in-alpha residual minus the mean out-of-alpha residual.
- Only (i) → "differ, but consistent with their lower SNR". Neither → "no consistent in-alpha difference", with the subjects named.
- R-13-implied: coherence in − out per subject is +0.075, +0.056, −0.219, +0.063, −0.145 (3 of 5 positive), and wPLI +0.297, −0.074, +0.033, −0.214, +0.144 (3 of 5). R-13 therefore reads "no consistent in-alpha difference" for both. Its in-alpha SNR is lower in 5 of 5 subjects, and its in-alpha alpha change is −1.175 vs −0.885 dB out of alpha.
- The in-alpha alpha measure rests on 2 bins (10.91 Hz) or 3 bins (8.57 Hz) against 5 for the other frequencies, and the report says so.

**P13 D-3 (S05).** This is exploratory and not graded. The report places S05's coherence/PLV deltas below 0 at 10.91 and 8.57 Hz, and its wPLI above 0, next to S05's alpha change and SNR (`power_confound_s05.csv`). It may say "consistent with alpha blocking lowering amplitude-sensitive measures" only as a hypothesis, and only if S05's in-alpha alpha change is the most negative of the cohort.

**Pairwise wording (R7, binding after F2).** p_mag < 0.05 reads: "the own-band delta difference is larger than a/b trial exchange produces". p_mag ≥ 0.05 is never "Δa ≈ Δb". Any cell whose `p_mag` and `p_mag_centred` fall on different sides of 0.05 is labelled "null off-centre". p_pat < 0.05 reads: "the a and b trials differ in pattern beyond exchange", not "the delta patterns differ". Approximate-id subjects (S02, S04) are flagged in every pairwise statement.

### Required fixes

1. **F1 (synthetic-tester; tests/R10).** `mas/state/phases/P14-cross-frequency-confounds/04_tests.md` is committed as the empty template (e4c9817). It must have:
   - the table for every test in `tests/test_p14_known_answer.py`, with the buggy variant each catches and the 8 mutants named (which test killed which);
   - the command and its verbatim pass line;
   - coverage gaps (at least: no off-centre pairwise null before F2; no real-data figure test);
   - R11 "none";
   - sources;
   - `Status: READY`.
2. **F2 (connectivity-stats, code; synthetic-tester, test; R7).** The pairwise test needs its null labelled and a null-centre diagnostic. The prescribed statistics stay primary and unchanged.
   - (a) The docstrings of `pairwise_permutation_test` (`src/features/connectivity/comparison.py:253-261`) and of the script (`scripts/connectivity/comparison/test_connectivity_frequency_differences.py:11-15`), and the console header, state the null hypothesis as "the trials of a and b are exchangeable (each group scored in its own band against the fixed 201 baseline)", and state that it is not "Δa = Δb".
   - (b) Return and write a DIAGNOSTIC CSV `reports/connectivity_comparison/<m>_pairwise_null[_<suffix>].csv` with columns `subject, method, freq_a, freq_b, t_null_mean, t_null_sd, p_mag_centred, d_null_mean, d_null_sd`, where `p_mag_centred = (1 + #{|t_null − t_null_mean| ≥ |t_obs − t_null_mean|}) / (n + 1)`. The §6 pairwise CSV stays unchanged.
   - (c) A test with the third case above (Δa = Δb = 0, b-trials raise band a) must show `t_null_mean` clearly > 0 and `p_mag` > 0.5. A test with the first case must show `t_null_mean` ≈ `t_obs` (within 3 `t_null_sd`) and p_mag not small. The tests run the code path, not a rebuilt copy.
3. **F3 (orchestrator; plan/acceptance).**
   - Bind the `02_plan.md` acceptance table to A0–A2, E1–E5 and the rules for acceptance questions 1 and 2 above.
   - Add the sha256 pre-check of the inputs.
   - Add the conditional DIAG-E3 command: `.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --methods <m> --permutations 500 --n-jobs -1 --random-state $B --out-suffix diagE3_rs$B` for B in 42 1 2 3 4 5, run only if E3's trigger fires.
   - Record the pairwise-null reading (F2 wording) in a decisions.md row.

### Non-blocking notes

- N1. Hann leakage (PF-23) in the real fs-250 geometry was computed with `periodogram(np.sin(2*np.pi*f0*np.arange(256)/256.0), fs=250, window="hann")`. The leakage is −35.0/−37.9 dB at 10.91 Hz and −30.6/−40.5/−47.5 dB at 8.57 Hz, and the bias is ≤ 0.05 dB at ≤ 10 dB SNR. It can be stated as immaterial, with these numbers in place of the −28.3 dB fs-250-tone figure.
- N2. In `<m>_split_half_reliability.csv`, SB-corrected and uncorrected values sit in one column (§6 schema). Any table built from it must take the label from `_split_half_details`.
- N3. The Fisher-combined p is computed over k = 3 responders (k = 2 for non-responders). It is uncorrected across 10 pairs × 2 statistics, so it is descriptive.
- N4. Spearman/OLS p-values come from 25 non-independent cells, and the centred R² has 20 effective residual df. These are descriptive, as the script prints.
- N5. The script name `test_connectivity_frequency_differences.py` starts with `test_` (roadmap name). It is not collected because `pytest.ini` sets `testpaths = tests`, and that line must stay.
- N6. The full suite now runs about 6.6 min (log step 5). This is beyond the about-a-minute target, but not a P14 defect.

Verdict: FAIL

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
