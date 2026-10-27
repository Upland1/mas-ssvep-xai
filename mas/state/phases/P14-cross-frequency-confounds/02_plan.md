# P14 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/02_REQUIREMENTS.md §6 (`connectivity_comparison` schemas), mas/04_REFERENCE_RESULTS.md R-13, mas/05_PITFALLS.md PF-21–PF-27, decisions.md P11–P13 rows, mas/state/reports/P13.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Compare connectivity deltas across the five stimulation frequencies (similarity, node
strength, reliability, pairwise permutation tests). Quantify how much of the delta
follows target SSVEP power and alpha change.

## Data source

- **Task 1:** the P13 final edge files `reports/connectivity_edges/<S>_<method>.npz`
  (trial-level 200 permutations; keys `diff_<cond>`, `fdr_<cond>`, `channels_kept`),
  plus `reports/connectivity_cohort_summary.csv`.
- **Tasks 2–3:** legacy 7-channel `data/processed/<S>/` (P02, OO), S01–S05, through the
  P13 loader (one shared P07 gate over 101–105 and 201; pre-gate trial ids, PF-03),
  on the fs-250 axis (PF-04, labelled).
- **Responders:** from `reports/n_subjects_benchmark.csv` (P11, leak-free), 2.0 s
  smoothed ≥ 80 %, which gives S03, S04, S05; non-responders are S01, S02. `--responders`
  overrides this.

## Settled points (inferred; recorded in decisions.md)

1. **Methods.**
   - Task 1 covers coherence, PLV, wPLI and PDC. PDC is symmetrized `(M + Mᵀ)/2` before
     every undirected statistic (similarity r, node strength), per PF-25, and its FDR
     count is reported over the 42 directed edges as in P13.
   - Task 2 covers coherence, PLV and wPLI.
   - Task 3 merges `<method>_global_delta.csv` for all four methods.
2. **Montage.** Every matrix is embedded into the 8 × 8 montage
   `PO7, PO3, POz, PO4, PO8, O1, Oz, O2` with NaN for missing channels (PF-26). PO7 is
   absent in all legacy subjects, so QAP permutes only the channels present.
3. **QAP.**
   - 2,000 node-label permutations, one-tailed (r_perm ≥ r_obs), +1 pseudo-count.
   - Applicability: at least 6 finite pairs and at least 4 shared channels.
   - The seed is derived per (subject, method, pair) from 42, independent of `n_jobs`.
4. **Pairwise permutation design (task 2).** For a pair (a, b), trials of conditions a
   and b are exchanged at trial level with the observed group sizes (PF-19, the P13
   splitter). Each relabelled group is scored in its own band against its own matched
   baseline. The baseline 201 windows are fixed, not permuted, and the null keeps
   their per-band matched scores. Within a pair, a and b use the same permutations, so
   magnitude and pattern share the null draws.
5. **Permutation counts.**
   - A 500-permutation run is suffixed `_p500`.
   - The final run uses 1000 permutations, unsuffixed.
   - A flip list (cells crossing 0.05 on any criterion) is produced in the P13 style.
   - The 500 and 1000 nulls are nested (P13 D-4), and that is stated.
6. **Split-half reliability.** 10 random trial-level halves per subject and condition;
   the 201 baseline trials are also split in halves. The seed is derived from 42.
   Spearman-Brown is applied only if r > 0 (PF-22); otherwise r is reported uncorrected
   and labelled "not reliable".
7. **Confound script.**
   - Hann periodograms per window on O1, Oz and O2 (channels kept), on the fs-250 axis,
     averaged over windows and channels.
   - Target f0 ± 1 Hz.
   - Alpha 8–13 Hz excluding f0 ± 1.5 Hz for both stimulus and baseline (PF-23).
   - The baseline is the same gated 201 windows.
   - Spearman is computed on all cells and within-subject centred; OLS R² of
     `delta ~ SNR + alpha` is fitted per method.
   - In-alpha means (10.91, 8.57) are compared with out-of-alpha means.
   - n = 25 cells per method; all inferential numbers are descriptive at n = 5 subjects.
8. **P13 D-3 carry-forward.** The S05 pattern (coherence and PLV below baseline, wPLI
   above) is examined descriptively against S05's alpha change and SNR. It stays
   exploratory.
9. **Figures.** Cross-subject panels share one colour limit per method (P12 D-4).
   Outputs go to `outputs/figures/connectivity_comparison/`; CSVs to
   `reports/connectivity_comparison/` with the §6 names.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| connectivity-stats | NEW `scripts/connectivity/comparison/compare_connectivity_frequencies.py` (+ library code under `src/features/connectivity/comparison.py` if shared) | task 1 + settled points 1–3, 9 | P14.1 | [1], PF-21/24/25/26 |
| connectivity-stats | NEW `scripts/connectivity/comparison/test_connectivity_frequency_differences.py` | task 2 + settled points 4–6; `--permutations`, `--n-jobs`, `--out-suffix`, `--subjects`, `--methods`, `--compare` | P14.2 | [1], PF-19/22 |
| connectivity-stats | NEW `scripts/connectivity/diagnostics/check_power_alpha_confound.py` | task 3 + settled points 7–8 | P14.3 | [1], PF-23/27 |

## Legacy behaviour in this phase

fs 250 frequency axis (PF-04), labelled in every meta. Per-script shared gate (R5 from P16).

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| PF-21 | responders from connectivity | read only the benchmark CSV; test |
| PF-22 | SB on r ≤ 0 | test with a negative r |
| PF-23 | target inside the alpha band | test: a pure 10.91 Hz target gives alpha change ≈ 0 |
| PF-24 | raw matrices compared | the code reads `diff_` keys only |
| PF-25 | directed PDC in node strength | symmetrize; test |
| PF-26 | channel misalignment | embedding test with a dropped channel |
| R7/PF-19 | permuted windows instead of trials; mismatched sizes | reuse the P13 splitter; test |
| QAP | permuting rows and columns inconsistently | a known-structure test: identical matrices up to relabelling → p small; independent → p roughly uniform |
| Determinism | results depend on `n_jobs` | test |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| QAP | two matrices with identical structure vs independent ones | p ≤ 0.01 vs p roughly uniform | | task 1 |
| embedding | 7-ch with Oz missing | NaN row/column at Oz; names align | exact | PF-26 |
| node strength | known matrix | hand mean per channel; PDC symmetrized | exact | task 1, PF-25 |
| Fisher-z | known r list | hand result | 1e-12 | task 1 |
| responders | benchmark CSV | S03, S04, S05 | exact | PF-21 |
| split-half | two halves from the same process with a strong pattern | r high; SB applied; negative r left uncorrected | | PF-22 |
| pairwise | identical a and b processes vs a planted difference | p roughly uniform vs small | | task 2 |
| ceiling | rel_a, rel_b | sqrt, disattenuation only if > 0.1 | exact | task 2 |
| Fisher combined | known p list | hand χ² p | 1e-12 | task 2 |
| SNR/alpha | synthetic windows with a known target gain and alpha drop | SNR and alpha change in dB as planted; target excluded from alpha | ±0.2 dB | task 3, PF-23 |
| OLS/Spearman | known linear data | R² ≈ 1 | | task 3 |
| PF-27 | file list | no `cofound` file | exact | PF-27 |

## Run commands (for the verifier)

```bash
# 0. input pre-check (pre-run audit F3; corrected per R2-N1): must print
#    804b1ced5c949644f22396ca35aa17b5090f2068654ff559c2f7b02a3649e697, else stop
sha256sum reports/connectivity_edges/*.npz reports/n_subjects_benchmark.csv | sha256sum
.venv/bin/python -m scripts.connectivity.comparison.compare_connectivity_frequencies
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --permutations 500 --n-jobs -1 --out-suffix p500
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --permutations 1000 --n-jobs -1
.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --compare p500 ""
.venv/bin/python -m scripts.connectivity.diagnostics.check_power_alpha_confound
# conditional DIAG-E3 (only if the E3 trigger in 07_review.md fires: magnitude-vs-pattern margin ≤ 1 cell);
# <M> = the triggered method(s) only (R2-N2, keeps it inside the budget)
for B in 42 1 2 3 4 5; do .venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --methods <M> --permutations 500 --n-jobs -1 --random-state $B --out-suffix diagE3_rs$B; done
```

The builder confirms the flags and measures a runtime from a one-subject smoke. The
pairwise test is the expensive part: 3 methods × 10 pairs × up to 1000 permutations per
subject, with the coherence concatenated estimator. If the total exceeds
`LOCAL_RUN_BUDGET_MIN` (120 min, 16 cores), the builder says so and the orchestrator
issues a human-run request. Permutation counts are not reduced.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| CSVs and figures per §6 | files and columns in `reports/connectivity_comparison/` per §6; figures present | §6 |
| the report states, with numbers, how much of the delta is explained by target SNR and alpha change | OLS R² per method, Spearman (all and within-subject centred) | R-13 |
| whether 10.91/8.57 Hz behave differently | in-alpha vs out-of-alpha means per method | R-13 |
| (no fixed numeric target; compare qualitatively with R-13) | the reviewer pre-commits the qualitative comparisons in the pre-run audit | R-13 |

**Binding (amended after the pre-run audit, F3):** the results review grades exactly the
criteria pre-committed in 07_review.md "Pre-run audit, Round 1" (34301f7). These are the
integrity checks A0–A2 (failure means FAIL), the qualitative comparisons E1–E5 (with the
DIAG-E3 trigger and its 4/6 rule), the R² wording bands for "how much of the delta is
explained" (≥ 0.5 / 0.2–0.5 / < 0.2; "SNR-dominated" if SNR alone gives ≥ 0.8 of the
full R²; "alpha adds" only for ΔR² ≥ 0.10), and the 4-of-5 same-sign rule (raw and
SNR-adjusted) for "whether 10.91/8.57 Hz behave differently". Where they are more specific
than the rows above, they prevail. The pairwise p_mag/p_pat are read as tests of a/b trial
exchangeability, not of Δa = Δb (decisions.md P14 row).

## Sources

1. `mas/03_ROADMAP.md` P14 (opened in this run).
2. `mas/04_REFERENCE_RESULTS.md` R-13; `mas/05_PITFALLS.md` PF-21–PF-27; `reports/n_subjects_benchmark.csv`; `reports/connectivity_edges/S03_coherence.npz` keys (opened in this run).

## Questions
