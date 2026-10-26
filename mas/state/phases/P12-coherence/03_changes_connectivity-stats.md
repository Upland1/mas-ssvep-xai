# P12 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Branch: phase/P12-coherence

## Files

| Status | Path | What |
|---|---|---|
| NEW | `src/features/connectivity/connectivity_extraction.py` (the package `__init__.py` already existed) | task 1: constants, `band_for_condition`, `compute_coherence_matrix` (DIAGNOSTIC, PF-15), `compute_condition_coherence` (R4), `compute_condition_connectivity`, `compute_baseline_matched_connectivity` (returns `(matrices, idx)`), `compute_difference_matrices`, `summary_rows`, `load_gated_conditions` (one P07 gate over 101-105 + 201, explicit thresholds) |
| NEW | `src/visualization/connectivity_plots.py` | `CONDITION_LABELS`, `plot_condition_connectivity`, `plot_all_conditions_panel`, `plot_difference_panel` (RdBu_r, vmin = -vmax shared), `plot_permutation_null_distributions` (stub, raises NotImplementedError; P13) |
| NEW | `scripts/connectivity/diagnostics/demo_coherence_bias.py` | kept diagnostic (a) synthetic, (b) real per `--subjects` |
| NEW | `scripts/connectivity/analysis/analyze_connectivity.py` | `--subject --method coherence --fs --data-root --reports-dir --figures-dir --no-figures` |
| NEW | `tests/test_p12_coherence.py` | 10 builder tests (plan "Tests required" table) |

## Verifier commands (plan confirmed; flags verified)

```bash
.venv/bin/python -m scripts.connectivity.diagnostics.demo_coherence_bias --subjects S03 S04
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity --subject S03 --method coherence
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity --subject S04 --method coherence
```
Runtime: about 6-7 s each (S03 smoke), well under the 2 min estimate. Outputs: `reports/connectivity/coherence_bias_demo*.csv`, `coherence_<S>_{matrices.npz,summary.csv,summary.meta.txt}`, `outputs/figures/connectivity/coherence_<S>_{raw,difference}_panel.png`.

## Smoke numbers (S03 only, scratchpad outputs; SMOKE, not results)

Synthetic (a), seed 0: independent noise per-window averaged 0.3373, concatenated 0.0180; coupled 0.9814 / 0.9824.
S03 gate: no channel dropped; rejected 1/40 (101), 1/40 (102), 0 (103), 0 (104), 1/40 (105), 0/78 (201).

| cond | baseline before (per-window) | baseline after (matched) | difference (matched) | difference (broadband, PF-16) |
|---|---|---|---|---|
| 101 | 0.6433 | 0.5461 | +0.2494 | +0.2084 |
| 102 | 0.6720 | 0.5500 | +0.2511 | +0.2141 |
| 103 | 0.6625 | 0.5256 | +0.1626 | +0.1012 |
| 104 | 0.7152 | 0.6435 | -0.0366 | +0.0198 |
| 105 | 0.8000 | 0.7390 | +0.0414 | +0.1934 |

Observations for the verifier (no tuning done): 105 before/after (0.800 / 0.739) sit just above the plan's check windows [0.63, 0.78] / [0.54, 0.71]; after < before in every band; 24/20 Hz differences positive and in [0.06, 0.30]; 104/105 near zero/negative as R-11 says for S03. S04 not run.

## Deviations / notes

- `connectivity_extraction.py` has extra helpers beyond task 1 (`summary_rows`, `load_gated_conditions`, `per_window_mean_matrix`, `mean_offdiag`, `band_average`, `pairwise_coherence`).
- Concatenation joins windows without tapering, so a Welch segment (nperseg 256, 50 % overlap) may straddle a window boundary; this is the roadmap's prescribed estimator.
- A band with no bin inside falls back to the nearest bin (not triggered at fs 250 / nperseg 256).
- `compute_condition_connectivity` also returns 201 in the broadband (5-35 Hz) band as the PF-16 "before" side.
- Matrix diagonal is NaN (documented).
- `plot_permutation_null_distributions` is a stub.

## Reference consultations (R11)

None. The original repository under `reference/` was not opened.

## Full suite

`.venv/bin/python -m pytest tests -o addopts="" -q` -> `697 passed, 21 warnings in 751.78s (0:12:31)` (builder tests alone: 10 passed in 2.63 s). The full suite takes about 12.5 min on this machine.
