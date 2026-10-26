# P13 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md (R3, R4, R6, R7, era matrix), mas/02_REQUIREMENTS.md §6 (`connectivity_cohort_summary` and `connectivity_edges` schemas), mas/04_REFERENCE_RESULTS.md R-12 and the tolerance table, mas/05_PITFALLS.md PF-03, PF-04, PF-17–PF-20, decisions.md P11–P12 rows, mas/state/reports/P12.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Add PLV/wPLI (from the CSD) and PDC (MVAR) to the P12 coherence module. Reproduce the
Hilbert and MVAR-slicing bugs in kept diagnostics. Build the permutation and BH-FDR
framework with trial-level permutations, and run the five-subject cohort: first
window-level (recorded), then trial-level at 100 and 200 permutations. Compare with R-12.

## Data source

Legacy 7-channel `data/processed/<S>/` (P02, OO), S01–S05, conditions 101–105 and 201,
fs 250 as the feature axis (PF-04, labelled). One shared P07 gate per subject over
101–105 and 201 (P12 settled point 1, every threshold explicit). Trial ids come from
`cv_utils.build_trial_ids(y_full, LEGACY_TRIAL_LENGTHS)` on the pre-gate labels, then the
stimulus/baseline selection and the gate mask (PF-03). S02/S04 have approximate ids (P11
D-2), flagged in the meta and the summary.

## Settled points (inferred; recorded in decisions.md)

1. **Bands** are those of P12: f_c ± 1 Hz on the fs-250 axis, the same 201 windows
   re-scored per band (matched baseline). The R-12 frequencies are the five stimulus
   bands.
2. **Global statistic and edges.** For the symmetric methods (coherence, PLV, wPLI), the
   global statistic is the mean upper-triangle difference and FDR runs over C(C−1)/2 = 21
   edges. For PDC (directed, `[i, j]` = j → i), the global statistic is the mean over all
   C(C−1) off-diagonal entries and FDR runs over those 42 directed edges. That is the
   reading of the roadmap's "21/28" for the directed case at 7 channels; `total_edges` in
   the summary states which. R11 may verify this against the original after the attempt.
3. **Permutation estimator for coherence** is the concatenated estimator (R4), recomputed
   on each permuted group. The P12 D-2 junction re-check is a DIAGNOSTIC. For one
   subject (S03), the cohort script can run coherence with the aligned estimator
   (`--coherence-estimator aligned`, default `concatenated`); the verifier runs it once
   at 200 trial-level permutations. Reported numbers stay concatenated.
4. **Runs.** (a) The window-level run uses 200 permutations, labelled
   `permutation_unit = window` (R7 first run, legacy), with suffix `_window200`. (b) The
   trial-level run uses 100 permutations, suffix `_trial100`. (c) The trial-level run
   uses 200 permutations: the final unsuffixed `reports/connectivity_cohort_summary.csv`
   and `reports/connectivity_edges/`. The (b)/(c) flip list (cells that cross α = 0.05
   on either criterion) is printed by a comparison step of the script or a small
   diagnostic and saved as `reports/connectivity_cohort_flips.csv`.
5. **Alpha hypotheses (P12 D-3).** A DIAGNOSTIC CSV
   `reports/connectivity_alpha_diagnostic.csv`, per subject × method × 104/105, holds
   the matched-baseline mean, the stimulus mean, the difference, and the trial-level
   global p. The script prints, descriptively, the cross-subject relation between
   baseline level and difference (n = 5; no inference claimed).
6. **Figures.** None are required beyond the existing panels. Any cross-subject panel
   shares one colour limit (P12 D-4).
7. **Seeds.** `random_state = 42` per (subject, method, frequency) through a documented
   derivation, so runs are reproducible and independent of `n_jobs`.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| connectivity-stats | MODIFIED `src/features/connectivity/connectivity_extraction.py` (or NEW sibling modules `phase_connectivity.py`, `mvar_pdc.py`, `permutation.py` under `src/features/connectivity/`) | tasks 1–4 exactly; `benjamini_hochberg`; `_trial_permutation_split`; the result dict incl. `permutation_unit`; `n_jobs` via joblib with deterministic seeds | P13.1–P13.4 | [1], PF-17–19 |
| connectivity-stats | NEW `scripts/connectivity/diagnostics/demo_hilbert_edges.py`, `demo_mvar_slicing.py` | PF-18 and PF-17 bug reproductions (DIAGNOSTIC, kept) with the numbers of tasks 1–2; outputs under `reports/connectivity/` | P13.1, P13.2 | [1] |
| connectivity-stats | NEW `scripts/connectivity/analysis/analyze_connectivity_cohort.py` | task 5 + settled points 2–5; §6 schema; edge npz; console (A) and (B) separately (PF-20); flags `--methods`, `--permutations`, `--permutation-unit {trial,window}`, `--n-jobs`, `--out-suffix`, `--subjects`, `--coherence-estimator`, `--compare <suffixA> <suffixB>` (flip list) | P13.5 | [1], §6 |

## Legacy behaviour in this phase

Window-level permutations in the first run (R7 first run, labelled `window`); fs 250 axis
(PF-04); MVAR contiguous slicing and Hilbert phase only in the kept bug demos (R6, R3).

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R6 / PF-17 | coefficient layout | recover a known VAR(2)/VAR(10) within about 10 %; the contiguous variant errs about 150–200 % (demo) |
| PDC orientation | `[i, j]` read as i → j | synthetic: only 0 drives 3 → PDC[3, 0] ≫ PDC[0, 3] |
| R3 / PF-18 | Hilbert phase in the reported path | edge-corruption test: CSD PLV unchanged (about 0.998); Hilbert demo degraded |
| R7 / PF-19 | window permutations reported as final; group sizes not matched; more than one trial split | split test: exact observed sizes, at most one split trial, whole trials otherwise; unit label in every row |
| PF-20 | merged star | console and summary carry two separate fields; test on a case where (A) and (B) disagree |
| BH | wrong monotonicity | hand-computed BH on a known p vector |
| p-values | missing +1 pseudo-count | the minimum p at 200 permutations is 1/201 |
| PF-03 | ids after the gate | reuse the P11 helper; test with a gate-rejected window |
| R4 / D-2 | junction bias in permuted coherence | aligned diagnostic run (settled point 3) |
| Determinism | results depend on `n_jobs` | test: n_jobs 1 vs 2 identical |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| MVAR recovery | identifiable VAR(p) | strided relative error ≤ 15 %; contiguous ≥ 100 % | as stated | PF-17 |
| PDC direction | 0 → 3 coupling | PDC[3, 0] > PDC[0, 3] by a margin; zero diagonal; columns normalised | | task 2 |
| edge immunity | coupled sinusoids with the first/last 15 samples corrupted | CSD PLV change ≤ 0.005; Hilbert PLV degraded | | PF-18 |
| wPLI | zero-lag coupling (volume conduction) | wPLI ≈ 0, PLV ≈ 1 | | task 1 |
| trial split sizes | trials of 5 and 2 windows | group sizes equal the observed sizes; at most one trial split | exact | PF-19 |
| null calibration | stimulus and baseline from the same process | global p roughly uniform over seeds (e.g. ≤ 2/10 below 0.05 at 10 seeds × 50 perms) | loose | R7 |
| planted effect | stimulus coupling added at f_c | p = 1/(n+1), FDR edges on the planted pairs only | | task 3 |
| BH | known p vector | hand result | exact | task 3 |
| (A) vs (B) | constructed case | the two fields differ | exact | PF-20 |
| determinism | same seed, n_jobs 1/2 | identical | exact | settled point 7 |
| schema | cohort on a synthetic tree | §6 columns; npz keys | exact | §6 |

## Run commands (for the verifier, in order)

```bash
.venv/bin/python -m scripts.connectivity.diagnostics.demo_hilbert_edges
.venv/bin/python -m scripts.connectivity.diagnostics.demo_mvar_slicing
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit window --n-jobs -1 --out-suffix window200
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 100 --permutation-unit trial --n-jobs -1 --out-suffix trial100
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --compare trial100 ""
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence --subjects S03 --permutations 200 --permutation-unit trial --coherence-estimator aligned --n-jobs -1 --out-suffix aligned_S03
```

The builder confirms the exact flags and measures a runtime from a one-subject smoke. If
the total exceeds `LOCAL_RUN_BUDGET_MIN` (120), the builder says so, and the orchestrator
turns the over-budget runs into a human-run request (hard stop 3). 16 cores are available.
The verifier saves the pytest log under `reports/logs/P13/`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| synthetic tests (MVAR recovery, edge immunity, trial split sizes) | the tests above pass; demo numbers printed (Hilbert envelope 5–70 % at the edges; CSD 0.998 → 0.998; contiguous error about 150–200 % vs strided about 5–10 %) | PF-17, PF-18, PF-19 |
| S01/S02 null on essentially everything | trial200: S01/S02 coherence and wPLI FDR totals and global p | R-12 |
| 24 Hz the only frequency robust across S03–S05 in both coherence and wPLI | trial200 global p < 0.05 at 24 Hz for S03–S05 in both methods; no other frequency significant in all three for both | R-12 |
| FDR edge totals per subject coherence 0/0/65/51/15, wPLI 0/3/38/33/18 at 200 trial-level permutations within tolerance | ±25 % or ±5 edges per subject (tolerance table) | R-12 |
| borderline cells that flip between 100 and 200 permutations are listed as inconclusive | `connectivity_cohort_flips.csv` | R-12 |
| task 6 | window200 recorded and labelled; window vs trial p-value comparison printed | PF-19 |

The reviewer pre-commits the exact windows in the pre-run audit.

## Sources

1. `mas/03_ROADMAP.md` P13 (opened in this run).
2. `mas/02_REQUIREMENTS.md` §6 schema lines; `mas/04_REFERENCE_RESULTS.md` R-12 and the tolerance table; `mas/05_PITFALLS.md` PF-17–PF-20 (opened in this run).

## Questions
