# P13 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md (R3, R4, R6, R7), mas/02_REQUIREMENTS.md §6, mas/04_REFERENCE_RESULTS.md R-12, mas/05_PITFALLS.md PF-03, PF-04, PF-17–PF-20, decisions.md P12–P13, mas/state/reports/P12.md
Branch: phase/P13-phase-pdc-permutations (from main fa9d663)
Commit(s): 6b03ae8 (plan files), 4d59878 (src), bb6a61f (demos), e4e7583 (cohort script), 7ad9983 (tests); this file in the docs commit that follows

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/connectivity/phase_connectivity.py` | NEW | `window_csd` (per-window band-averaged complex CSD, `csd(..., nperseg=min(T,128))`), `compute_phase_connectivity(windows, fs, band, metric, nperseg)`, `compute_condition_plv`, `compute_condition_wpli`; PLV/wPLI reducers; fast-path attributes `per_window`/`reduce` | P13.1 | [1], R3, PF-18 |
| `src/features/connectivity/mvar_pdc.py` | NEW | `fit_mvar_ols(windows, p=10)` (channel-major columns, ridge `1e-4 tr(G)/dim`, rows never cross a window), `mvar_coefficients` (strided `weights[lag::p].T`), `pdc_from_coefficients`, `compute_condition_pdc(windows, fs, band, order=10)` (15 freqs, column-normalised, zero diagonal; `.directed = True`) | P13.2 | [1], R6, PF-17 |
| `src/features/connectivity/permutation.py` | NEW | `benjamini_hochberg`, `_trial_permutation_split`, `_window_permutation_split`, `derive_seed`, `edge_mask`, `compute_permutation_test`, `extract_connectivity_by_condition` | P13.3, P13.4 | [1], R7, PF-19 |
| `src/features/connectivity/connectivity_extraction.py` | MODIFIED | added `load_legacy_selection` (PRE-gate windows, labels, trial ids, approximate flag) and `gate_selection`; `load_gated_conditions` now delegates to them and additionally returns `trial_ids` and `trial_ids_approximate` (existing keys and numbers unchanged; the 36 P12 tests still pass) | P13.4 | PF-03, P12 |
| `scripts/connectivity/analysis/analyze_connectivity_cohort.py` | NEW | cohort driver, `--compare`, §6 CSV, per-subject edge npz, alpha diagnostic CSV, separate (A)/(B) console | P13.5 | [1], [2] §6, PF-20 |
| `scripts/connectivity/diagnostics/demo_hilbert_edges.py` | NEW | PF-18 bug demo (kept DIAGNOSTIC) | P13.1 | [1], PF-18 |
| `scripts/connectivity/diagnostics/demo_mvar_slicing.py` | NEW | PF-17 bug demo (kept DIAGNOSTIC) | P13.2 | [1], PF-17 |
| `tests/test_p13_connectivity.py` | NEW | 27 builder tests | all | plan "Tests required" |

## Legacy behaviour implemented

- Window-level permutations: `--permutation-unit window` (no trial ids passed); every result row carries `permutation_unit = window` (R7 first run, labelled).
- fs-250 axis (PF-04): `--fs` default `LEGACY_FS_HZ = 250`, bands from P12.
- Contiguous MVAR slicing and filtfilt + Hilbert exist only in the two demo scripts (`contiguous_coefficients`, `hilbert_analytic`); the library paths use the fixes.
- Aligned coherence (P12 D-2 diagnostic): `--coherence-estimator aligned`, prints a NOTE; default is concatenated (R4).

## Differences from the cited examples

None borrowed. Choices not fixed by the plan, recorded here:
1. Edge p-values for BH-FDR are the ONE-tailed edge p-values (stimulus > baseline), the same direction as the global one-tailed p; two-tailed edge p-values are computed and kept in the result dict but not in the CSV.
2. In the trial-level test the baseline trial ids are offset so they never collide with stimulus ids (ids from `build_trial_ids` are already unique; the offset protects callers with separate numbering).
3. PLV/wPLI permutation fast path: the per-window CSD does not depend on the grouping, so it is computed once on the pooled windows and each permutation reduces a subset. `test_fast_path_equals_direct_call` proves equality with the direct call.
4. Seeds: cell seed = `derive_seed(42, subject, method, condition)` (SeedSequence over crc32 of the strings); permutation `i` uses the i-th state of `SeedSequence(cell seed).generate_state(n)`. The permutation index, not the worker, owns the seed, so `n_jobs` cannot matter (`test_determinism_across_n_jobs`). The aligned-coherence diagnostic uses the same cell seeds as the concatenated run, so both use identical permutations.
5. The §6 summary CSV has exactly the §6 (pre-P18) columns; extra columns (`p_two_tailed`, null mean/std/CI, window counts, fs, source, `trial_ids_approximate`, `coherence_estimator`, `random_state`) go to the sidecar `connectivity_cohort_summary[_s]_details.csv`. `significant_uncorrected` = global p < alpha (criterion B); `fdr_backed` = at least one FDR edge (criterion A); `frequency_hz` is the target frequency, `label` e.g. "24 Hz".
6. Suffixed edge files go to `reports/connectivity_edges_<suffix>/<S>_<method>.npz`; the final run writes `reports/connectivity_edges/`.
7. The PDC difference matrix has 0 on the diagonal (not NaN); the symmetric methods keep NaN, as in P12. Edge masks make this irrelevant to the statistics.

## Deviations from the plan

- None in the settled points (42 directed edges for PDC, estimator flag, suffixes and `--compare`, alpha CSV, seeds all as written).
- `--compare` writes only the flipping cells to `reports/connectivity_cohort_flips.csv` (columns `p_one_tailed_a/_b`, FDR counts, `flip_B`, `flip_A`, `inconclusive`, suffixes) and prints the count out of all cells. The call `--compare trial100 ""` works (`""` = unsuffixed final run).
- The PF-17 demo gives contiguous error 129.7 % (roadmap "~150–200 %") and strided 6.6 % ("~5–10 %"). The PF-18 demo gives CSD PLV 1.0000 -> 0.9999 (roadmap "0.998 -> 0.998", which depends on the noise level) and Hilbert edge envelope 0.39–0.76 (first 15 samples) and 0.02–0.17 (last 15) of the centre value. The synthetic systems are mine and were not tuned to hit those numbers; the qualitative claims hold and the demos' exit tests use the plan's windows (strided <= 15 %, contiguous >= 100 %; CSD change <= 0.005).

## How to run / reproduce

Verifier commands: the seven in `02_plan.md` are correct as written; every flag exists. Each form was run (smoke, scratchpad outputs):

```bash
.venv/bin/python -m scripts.connectivity.diagnostics.demo_hilbert_edges
.venv/bin/python -m scripts.connectivity.diagnostics.demo_mvar_slicing
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit window --n-jobs -1 --out-suffix window200
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 100 --permutation-unit trial --n-jobs -1 --out-suffix trial100
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --compare trial100 ""
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence --subjects S03 --permutations 200 --permutation-unit trial --coherence-estimator aligned --n-jobs -1 --out-suffix aligned_S03
```

Notes for the verifier: subjects default to every `S\d+` folder in `data/processed` (S01–S05). Outputs: `reports/connectivity_cohort_summary[_s].csv` (+ `_details.csv`), `reports/connectivity_alpha_diagnostic[_s].csv`, `reports/connectivity_edges[_s]/`, `reports/connectivity/hilbert_edges_demo.csv`, `reports/connectivity/mvar_slicing_demo.csv`, `reports/connectivity_cohort_flips.csv`. The window-versus-trial comparison (plan task 6) is available as `--compare window200 ""`; it overwrites `connectivity_cohort_flips.csv`, so save that file (or run it before the trial100 comparison). The required flip file is the `trial100` vs final one, run last.

## Runtime (measured and extrapolated, 16 cores)

Measured: one subject (S03), all four methods, 200 permutations, `--n-jobs -1`, scratchpad outputs, wall time from `/usr/bin/time`:

| Run | Wall | Per method (printed) |
|---|---|---|
| trial-level, 200 perms | 68.8 s | coherence 62.5 s, PLV 0.4 s, wPLI 0.3 s, PDC 3.9 s |
| window-level, 200 perms | 71.6 s | coherence 65.4 s, PLV 0.3 s, wPLI 0.2 s, PDC 4.0 s |
| aligned coherence only, trial 200 | 38.1 s | coherence 36.5 s |
| 20-permutation smoke, trial, per single method | 1.0 s (PLV), 1.0 s (wPLI), 9.9 s (coherence), 4.1 s (PDC) | |

Extrapolation (five subjects of similar size; S03 has 275 clean windows):

| Command | Estimate |
|---|---|
| two demos | under 15 s |
| window200 | 5 x 71.6 s = 358 s (about 6.0 min) |
| trial100 | about 5 x 38 s = about 3 min (coherence scales with permutations) |
| trial200 (final) | 5 x 68.8 s = 344 s (about 5.7 min) |
| `--compare` | seconds |
| aligned S03 | 38 s |
| **Total** | **about 16 min**, far below `LOCAL_RUN_BUDGET_MIN` = 120. No split or human run is needed. Permutations and methods are not reduced. |

Coherence is about 90 % of the time; PLV and wPLI are near-free through the fast path.

## How I verified

- `.venv/bin/python -m pytest tests -o addopts="" -q` -> `750 passed, 21 warnings in 366.32s (0:06:06)` (723 before P13, plus 27 new).
- `tests/test_p13_connectivity.py` covers the plan's table: MVAR recovery (strided <= 15 %, contiguous >= 100 %, i.e. it fails on PF-17 slicing), design rows never crossing windows, PDC direction (0 -> 3: `PDC[3,0] > PDC[0,3] + 0.3`), column normalisation, edge immunity (CSD change <= 0.005, Hilbert drop larger), wPLI vs PLV on zero lag, BH on hand cases, trial-split exact sizes and at most one split (4 parametrised cases x 30 seeds), seed derivation, planted effect (`p = 1/(n+1)` and FDR on exactly the planted pairs), null calibration (<= 2 of 10 below 0.05), fast path equals direct, determinism n_jobs 1 vs 2 (coherence, PDC), 42 vs 21 edges, window unit label, (A) vs (B) disagreement, PF-03 (a gate-rejected window: ids masked like the windows), cohort schema / npz keys / alpha CSV on a synthetic tree, `--compare` flips. One extra: window-level permutations reject a trial-dependent null in 5 of 40 repeats against 0 of 40 at trial level (PF-19).
- Demos: `demo_mvar_slicing`: strided 6.6 %, contiguous 129.7 %. `demo_hilbert_edges`: Hilbert PLV 0.9793 -> 0.9530, CSD PLV 1.0000 -> 0.9999 (smoke, scratchpad).

### Smoke numbers (SMOKE: S03 only, scratchpad `reports/`, not the verifier's run, not reportable)

S03, trial-level, 200 permutations, global one-tailed p at 24 / 20 / 15 / 10.91 / 8.57 Hz (R-12 in brackets):

| Method | Global p | FDR edges per frequency (total) |
|---|---|---|
| coherence | 0.005 / 0.005 / 0.005 / 0.786 / 0.104 (0.005 / 0.005 / 0.005 / 0.776 / 0.095) | 20 / 21 / 15 / 0 / 8 (64; R-12 20 / 21 / 16 / 0 / 8, 65) |
| wPLI | 0.005 / 0.060 / 0.050 / 0.020 / 0.005 (0.005 / 0.055 / 0.065 / 0.015 / 0.005) | 17 / 0 / 5 / 5 / 15 (42; R-12 17 / 0 / 3 / 3 / 15, 38) |
| PLV | 0.005 / 0.005 / 0.005 / 0.522 / 0.274 | 18 / 14 / 12 / 0 / 0 (44) |
| PDC (42 edges) | 0.005 / 0.005 / 0.005 / 0.333 / 0.214 | 5 / 5 / 0 / 0 / 0 (10) |

Window-level (same S03): FDR totals coherence 66, PLV 47, wPLI 46, PDC 15; `--compare` of window vs trial lists one flip (S03 wPLI 20 Hz: p 0.020 -> 0.060, FDR edges 5 -> 0). Aligned coherence diagnostic (S03, trial 200): FDR total 48 against 64 concatenated; global p 0.005 / 0.005 / 0.005 / 0.637 / 0.697. The S03 wPLI 15 Hz value (p 0.050 at 200 permutations) sits on the alpha boundary and is a likely flip candidate.

## Left to do / known limitations

- The D-2 junction question is answered by the verifier's aligned run; my S03 smoke shows fewer FDR edges with the aligned estimator (48 vs 64) and different 10.91 / 8.57 Hz p, so those cells are estimator-dependent and the reviewer should read them.
- The alpha-hypothesis relation (Spearman, n = 5) prints only when 3 or more subjects are run.
- No figures were added (plan settled point 6: none required).
- Tested on legacy 7-channel data only; the code takes the channel count from the data.

## Reference consultations (R11)

None. The original repository was not opened; the 42-edge reading of the directed case rests on the plan's settled point and may be verified after the attempt if the reviewer wants it.

| # | Trigger | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| | none | | | |

## Sources

1. `mas/03_ROADMAP.md` P13 (opened in this run).
2. `mas/02_REQUIREMENTS.md` §6; `mas/04_REFERENCE_RESULTS.md` R-12 and tolerance table; `mas/05_PITFALLS.md` PF-03, PF-04, PF-17–PF-20; `mas/RULES.md` (opened in this run).
3. SciPy 1.18.1 `scipy.signal.csd`, `coherence`, `sosfiltfilt`, `hilbert`; joblib 1.6.0 (installed versions).
4. Benjamini and Hochberg (1995), J. R. Stat. Soc. B 57:289-300, doi:10.1111/j.2517-6161.1995.tb02031.x (step-up rule only, implemented independently).

## Questions

None.

## Round 1 audit fix

Status: READY

Commits: fix (code), test, and this docs commit, after `e80cfad`. No number-producing path changed; the new key `p_lower_tailed` is an addition.

1. **F1, `--compare` independent of run order** (`analyze_connectivity_cohort.py`, `flips_path`, `compare_runs`). The pair (`trial100`, `""`) writes `reports/connectivity_cohort_flips.csv`; any other pair writes `reports/connectivity_cohort_flips_<a>_vs_<b>.csv` with `final` for `""` (for example `connectivity_cohort_flips_window200_vs_final.csv`). The console prints the compared suffixes and `N cells compared`. `compare_runs` raises `ValueError` if the two summaries do not hold the same (subject, method, condition) rows (the merge is also `one_to_one`). Tests: `test_compare_is_order_independent` (both orders, both files kept, the required file not overwritten), `test_compare_raises_on_missing_rows`.
2. **N2, `p_lower_tailed`**: `compute_permutation_test` returns `p_lower_tailed = (1 + #{null <= obs}) / (n + 1)` from the null counts, and the alpha diagnostic CSV has the column (`connectivity_alpha_diagnostic[_s].csv`: subject, method, condition, frequency_hz, mean_baseline_matched, mean_stimulus, mean_difference, p_one_tailed, p_lower_tailed, permutation_unit). Tests: `test_lower_tail_p_from_null_counts`, `test_alpha_csv_has_lower_tail`.
3. **N3, rationale corrected**: "21/28" in the roadmap means C(7,2) = 21 and C(8,2) = 28, the 7- and 8-channel undirected counts. It does not fix the directed case. PDC uses 42 directed edges as this rebuild's own choice (each direction is a separate hypothesis; R-12 has no PDC row, so acceptance is unaffected). This replaces the earlier wording that read "21/28" as the directed case.

Full command list (confirmed against the amended `02_plan.md`; flags unchanged):

```bash
.venv/bin/python -m scripts.connectivity.diagnostics.demo_hilbert_edges
.venv/bin/python -m scripts.connectivity.diagnostics.demo_mvar_slicing
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit window --n-jobs -1 --out-suffix window200
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 100 --permutation-unit trial --n-jobs -1 --out-suffix trial100
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --compare trial100 ""
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --compare window200 ""
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence --subjects S03 --permutations 200 --permutation-unit trial --coherence-estimator aligned --n-jobs -1 --out-suffix aligned_S03
```

Suite: `.venv/bin/python -m pytest tests -o addopts="" -q` -> `792 passed, 21 warnings in 352.67s (0:05:52)`.
