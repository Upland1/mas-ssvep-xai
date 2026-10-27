# P14 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/02_REQUIREMENTS.md §6, mas/04_REFERENCE_RESULTS.md R-13, mas/05_PITFALLS.md (PF-03, PF-04, PF-19, PF-21–PF-27), decisions.md P12–P14 rows, mas/state/reports/P13.md
Branch: phase/P14-cross-frequency-confounds (from main 997635a)
Commit(s): da0cf64 (chore, orchestrator files), b705d73 (feat, library), ae547e0 (feat, scripts), ece4cb5 (test)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/connectivity/comparison.py` | NEW | Library: `embed_to_montage` (by name, NaN for missing channels), `symmetrize` / `undirected_delta` (PDC `(M+Mᵀ)/2`), `node_strength`, `mean_upper`, `fisher_mean`, `qap_pvalue`, `responders_from_benchmark`, `spearman_brown`, `reliability_ceiling`, `disattenuate`, `split_half_delta_reliability`, `fisher_combined_p`, `pairwise_permutation_test`. Reuses `_trial_permutation_split`, `benjamini_hochberg`, `derive_seed`, `edge_mask` from `permutation.py` and the per-window CSD fast path of PLV/wPLI. | P14.1, P14.2 | PF-19, PF-21, PF-22, PF-25, PF-26, R4, R6, R7 |
| `scripts/connectivity/comparison/compare_connectivity_frequencies.py` | NEW | Task 1: reads only `diff_`, `fdr_`, `channels_kept` from the P13 final edge files; similarity r + QAP p, node strength, global delta and FDR count per frequency; group summaries (all / responders / non-responders, Fisher-z); figures with one colour limit per method. | P14.1 | PF-21, PF-24, PF-25, PF-26 |
| `scripts/connectivity/comparison/test_connectivity_frequency_differences.py` | NEW | Task 2: split-half reliability, 10 pairwise trial-level tests per subject and method (coherence, PLV, wPLI), ceilings, disattenuation, BH across pairs, Fisher-combined p, `--compare`. | P14.2 | PF-19, PF-22 |
| `scripts/connectivity/diagnostics/check_power_alpha_confound.py` | NEW | Task 3: O1/Oz/O2 Hann periodograms, target SNR, alpha change without f0 ± 1.5 Hz, merge with `<m>_global_delta.csv`, Spearman (all / centred), OLS R², in-alpha vs out-of-alpha, S05 table, scatter figure. Only the correctly spelled name exists. | P14.3 | PF-23, PF-27 |
| `tests/test_p14_connectivity_comparison.py` | NEW | 30 builder tests covering the plan's "Tests required" table (below). | all | R6, R7 |

## Legacy behaviour implemented

fs-250 frequency axis (PF-04) in every script; labelled in `*_split_half_details*.csv` (`fs`, `source` columns), in every console header and in the docstrings. Per-script shared gate (one P07 gate over 101–105 and 201 via the P13 loader). Trial ids from the pre-gate labels (PF-03); `trial_ids_approximate` is a column of the pairwise CSV (S02/S04 approximate, P11 D-2). No other legacy behaviour is introduced, and no historical-bug diagnostic is added: PF-21–PF-27 are pitfalls of new code, each guarded by a test (below), not behaviours reproduced.

## Differences from the cited examples

None cited. The design follows 02_plan.md "Settled points" 1–9.

## Deviations from the plan

1. **Extra CSVs** (schemas of §6 unchanged): `<m>_frequency_similarity_groups.csv`, `<m>_node_strength_groups.csv`, `<m>_global_delta_groups.csv` (group summaries), `<m>_split_half_details[_s].csv` (uncorrected Fisher-mean r, `spearman_brown_applied`, label "not reliable (r <= 0, uncorrected)", window counts, fs, source), `<m>_pairwise_combined[_s].csv` (Fisher-combined p per group and pair, magnitude and pattern), `pairwise_flips.csv`, and for task 3 `power_confound_{correlations,ols,alpha_split,s05}.csv`.
2. **PO7 rows in node strength.** `<m>_node_strength.csv` has all 8 montage channels per cell; the missing channel (PO7 in every legacy subject) has `node_strength = NaN` (PF-26, explicit rather than silently dropped).
3. **Reliability and BH conventions the plan left open.** Halves are `k // 2` trials / the rest (stimulus and baseline halved independently in each split, baseline halves are drawn per condition). BH across the 10 pairs runs per subject and method, separately for `p_mag` and `p_pat`. `r_disattenuated` is not clipped to 1. Groups with no member (no non-responders in a subset run) produce no combined rows.
4. **Flip criteria** in `--compare`: `p_mag < 0.05`, `p_pat < 0.05`, `n_edges_fdr >= 1`, `sig_bh_mag`, `sig_bh_pat`; any change marks the cell inconclusive. The unsuffixed `pairwise_flips.csv` is the (`p500`, "") pair.
5. **Task 3 tables.** OLS is also reported on within-subject centred variables, and with SNR-only and alpha-only R², besides the plan's `delta ~ SNR + alpha`. With 25 cells from 5 subjects the p-values are descriptive.
6. **Responders** are not re-derived from connectivity anywhere; `--responders` overrides.

## How to run / reproduce

Verifier commands (02_plan.md confirmed, no change; flags checked against `--help`):

```bash
.venv/bin/python -m scripts.connectivity.comparison.compare_connectivity_frequencies
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --permutations 500 --n-jobs -1 --out-suffix p500
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --permutations 1000 --n-jobs -1
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --compare p500 ""
.venv/bin/python -m scripts.connectivity.diagnostics.check_power_alpha_confound
```

Order matters: the confound script reads `reports/connectivity_comparison/<m>_global_delta.csv` written by the first command (it stops with a message if they are missing). Outputs: `reports/connectivity_comparison/` and `outputs/figures/connectivity_comparison/`.

## How I verified

- `.venv/bin/python -m pytest tests -o addopts="" -q` → `826 passed, 21 warnings in 399.06s (0:06:39)` (`mas/state/scratch/p14_full_suite.log`; 796 before P14 + 30 new). The new file alone: `30 passed in 33.44s`.
- Tests against the plan's table: QAP (identical structure p ≤ 0.01, 150 independent pairs mean p in (0.4, 0.6) and < 12 % below 0.05; agreement with the exhaustive 7! node relabelling, tolerance 0.03; mutation check: permuting rows only makes it fail), embedding with Oz missing (exact, by name), node strength and PDC symmetrization (hand values), Fisher-z (1e-12), responders (synthetic CSV; real CSV gives S03, S04, S05), split-half (strong planted pattern r > 0.8, SB applied; r ≤ 0 left uncorrected), pairwise (identical processes: mean p in (0.35, 0.65) over 40 repetitions for both statistics; planted coupling vs noise p_mag ≤ 0.02; different patterns with equal magnitude p_pat ≤ 0.02; observed group sizes and at most one split trial verified by a spy on the splitter; determinism; `n_jobs` 1 vs 2 byte-identical; nested seeds), ceiling and disattenuation, Fisher-combined (closed form, 1e-12), SNR/alpha (planted ±6.02 dB within 0.2 dB; a 10.91 Hz target gives |alpha change| < 0.2 dB while the unexcluded 8–13 Hz measure gives > 1 dB), OLS R² = 1 on linear data, in/out-of-alpha split, no `cofound` file, no raw-data access in the scripts.
- Real-data, task 1 (scratchpad outputs, not in `reports/`): 6 s for all four methods with figures. Fisher-mean r over 50 subject × pair cells: coherence 0.629 (66 % with p_qap < 0.05), PLV 0.510 (62 %), wPLI 0.163 (32 %), PDC 0.480 (64 %). R-13 reports coherence 0.54 / 64 % and wPLI 0.14 / 32 %: qualitatively the same ordering (coherence ≫ wPLI); the coherence r is 0.09 higher, inside "qualitative", not a target.
- Real-data, task 3 (scratchpad, 2 s): S05 coherence deltas 0.137, 0.006, 0.021, −0.084, −0.097 at 24, 20, 15, 10.91, 8.57 Hz equal the R-13 S05 coherence row (24 Hz 0.137, 10.91 Hz −0.084, 8.57 Hz −0.097). These are an input check of the merge, not a P14 result.

### Smoke numbers (S03, 20 permutations: SMOKE, not results)

Command: `... test_connectivity_frequency_differences --subjects S03 --permutations 20 --n-jobs {1,-1} --out-suffix smoke --reports-dir <scratchpad>`; S03 kept 7 channels, clean 275/278, trial ids exact.

| Item | Value |
|---|---|
| Reliability (3 methods × 5 conditions × 10 splits, serial) | 16.3 s |
| Pairwise, 30 jobs (3 methods × 10 pairs), `--n-jobs 1` | 39.5 s |
| Pairwise, 30 jobs, `--n-jobs -1` (16 cores) | 11.9 s |
| `--n-jobs 1` vs `-1` CSVs | byte-identical (`cmp`) for coherence, PLV, wPLI |
| Cells with p_mag < 0.05 (smoke, 10 pairs) | coherence 1, PLV 5, wPLI 1 |
| Cells with p_pat < 0.05 (smoke) | coherence 1, PLV 0, wPLI 0 |
| BH-significant cells / cells with ≥ 1 FDR edge (smoke) | 0 / 0 for all three |
| Split-half cells with r ≤ 0 | 0 of 15 |

At 20 permutations the minimum p is 1/21, so BH and FDR counts are not informative here.

## Runtime extrapolation (16 cores, `LOCAL_RUN_BUDGET_MIN` 120)

Serial cost is 39.5 s / 20 = 1.98 s per permutation per subject for the 30 jobs (upper bound: the fixed observed-statistic cost is included). Five subjects: 5 × 1.98 = 9.9 s per permutation, i.e. 9,875 CPU-s at 1000 permutations and 4,938 CPU-s at 500. The smoke speed-up was only 3.3 (30 jobs, joblib start-up, two scheduling waves); the full run has 150 jobs, so 16 cores should give 10–13 times, and I budget with 8 times to be conservative. The reliability step runs serially in the main process: 16.3 s per subject, 82 s per run (assuming the other subjects resemble S03).

| Command | Ideal (÷ 16) | Conservative (÷ 8) |
|---|---|---|
| 1. compare_connectivity_frequencies (4 methods, QAP 2000, figures) | 6 s | 6 s |
| 2. pairwise, 500, `p500` | 5.1 min + 1.4 min = 6.5 min | 10.3 min + 1.4 min = 11.7 min |
| 3. pairwise, 1000, final | 10.3 min + 1.4 min = 11.7 min | 20.6 min + 1.4 min = 22 min |
| 4. `--compare p500 ""` | seconds | seconds |
| 5. check_power_alpha_confound | 2 s | 2 s |
| Total | about 18 min | about 34 min |

The total stays well under 120 min even with the conservative factor; no split or human run is needed, and the permutation counts are untouched. (Arithmetic: `.venv/bin/python -c "print(9.9*1000/16/60, 9.9*500/16/60, 9.9*1000/8/60, 9.9*500/8/60)"` gives 10.3, 5.2, 20.6, 10.3 minutes.) The real subjects S01, S02, S04, S05 have different window counts than S03 (275 clean here); a 30 % larger subject would add about 30 % to its share.

## Left to do / known limitations

- **Hann leakage into the alpha measure.** The exclusion is f0 ± 1.5 Hz as specified (PF-23). A pure 10.91 Hz tone still leaks into the 12.70 Hz bin at −28.3 dB (and 8.79 Hz at −33.7 dB) relative to its peak, because 12.70 Hz is 1.8 bins from the tone (Hann main lobe ±2 bins); for 8.57 Hz the residual bins are at −32.3, −43.1 and −50.5 dB (`scipy.signal.periodogram`, 256 samples, fs 250). With the target SNRs observed (1.7 to 10 dB in the scratchpad run) this is negligible, but a reviewer may want it stated. Not changed, to follow the settled point.
- The fs-250 axis shifts the true frequencies by 2.4 % (24 Hz appears at 23.4 Hz); the confound bands are on the same axis as the connectivity bands (PF-04, labelled).
- p-values of Spearman/OLS over 25 cells from 5 subjects are descriptive (cells share a subject); the statistics script prints this.
- The split-half reliability runs serially in the main process (82 s per run); parallelising it was judged unnecessary at this cost.
- The tests do not cover real-data figures; the verifier should open the PNGs (`outputs/figures/connectivity_comparison/`).
- The full suite takes 6 min 39 s (target "about a minute" already exceeded since P10; the post-edit hook reports it on every edit).

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened; no test failed or deviated after one investigation round.

| # | Trigger | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| | none | | | |

## Sources

1. `mas/03_ROADMAP.md` P14 tasks 1–3 (opened in this run).
2. `mas/02_REQUIREMENTS.md` §6 (output schemas); `mas/04_REFERENCE_RESULTS.md` R-13; `mas/05_PITFALLS.md` PF-03, PF-04, PF-19, PF-21–PF-27 (opened in this run).
3. `src/features/connectivity/{permutation,connectivity_extraction,phase_connectivity,mvar_pdc}.py` and `scripts/connectivity/analysis/analyze_connectivity_cohort.py` (P12/P13 code, reused).
4. `reports/n_subjects_benchmark.csv`, `reports/connectivity_edges/S03_*.npz` keys (opened in this run).

## Questions

None.

## Round 1 audit fix

Status: READY
Commits: fix (null label and diagnostic), test (4 tests), this docs commit.

- **F2 wording.** The docstring of `pairwise_permutation_test` (`src/features/connectivity/comparison.py`), the module docstring and the console header of `test_connectivity_frequency_differences.py` now state the null as exchangeability of the a/b trials (each scored in its own band against the fixed matched baseline), not Δa = Δb, and say that p_mag ≥ 0.05 never means Δa ≈ Δb.
- **Diagnostic CSV (NEW output).** `reports/connectivity_comparison/<m>_pairwise_null[_<suffix>].csv`, columns `subject, method, freq_a, freq_b, t_null_mean, t_null_sd, p_mag_centred, d_null_mean, d_null_sd`. `p_mag_centred = (1 + #{|t_null − t_null_mean| ≥ |t_obs − t_null_mean|}) / (n + 1)`, exactly the review's definition (07_review.md, F2 (b)); `d_null_*` ignore non-finite null draws. The primary `p_mag`, `p_pat` and the §6 CSV are unchanged.
- **Proof of no change.** On a synthetic tree (S01, plv + coherence, 20 permutations, 3 splits, `--out-suffix t`), the code at the pre-fix commit (git worktree) and the fixed code give identical sha256 for `pairwise_tests`, `split_half_reliability`, `split_half_details` and `pairwise_combined` of both methods (8 of 8 files, one unique hash each). The worktree and outputs were removed afterwards.
- **Tests** (`tests/test_p14_connectivity_comparison.py`, now 34): a common band effect (all trials respond in band a) gives t_mag > 0.2 yet p_mag > 0.3, the null mean is off 0 and within 0.1 of t_mag, and p_mag_centred > 0.3; Δa = Δb = 0 with b-trials responding in band a gives |t_mag| < 0.05, p_mag > 0.9, a null mean > 0.1 and p_mag_centred < 0.05; the diagnostic CSV has the F2 columns, 10 rows and leaves the §6 columns exactly as before; `--random-state` and `--out-suffix` produce separate files and different draws.
- **DIAG-E3 flags confirmed.** `--methods <m> --permutations 500 --n-jobs -1 --random-state $B --out-suffix diagE3_rs$B` works (tested with B = 1, 2 on a synthetic tree): outputs are suffixed per base and seeds derive from `--random-state`, so 42, 1, 2, 3, 4, 5 give independent draws. Runtime of one DIAG-E3 base: 1 method at 500 permutations about 1/3 of the 3-method p500 run (coherence is the most expensive method, so up to about 3.5 min at ÷ 8), six bases about 20 min at worst.
- **Full suite:** `870 passed, 21 warnings in 413.43s (0:06:53)`.
