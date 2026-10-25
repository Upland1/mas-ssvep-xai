# P05 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §5.1, §6, mas/02_REQUIREMENTS.md §1, §4–§7, mas/04_REFERENCE_RESULTS.md R-3, mas/05_PITFALLS.md PF-01/02/04/06/10/11/12/14, P02–P04 rows of decisions.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Build the project's three feature extractors (continuous PSD, FBCCA, FBCSP) and the
10-model sklearn suite, benchmark six feature spaces on S03 under the legacy protocol,
and reproduce the R-3 flagship (90.36 % / 95.43 %, 197 / 3).

## Data source

Legacy folders `data/processed/<S>/` from P02 (OO, 7 channels, 256 samples); stimulus
windows (101–105) of `X_time_windows`; fs = 250 (legacy) in every extractor. Each
extractor applies the legacy window mask (below) and returns the mask; feature blocks
are aligned to one final mask (PF-10). Acceptance subject S03; the benchmark scripts
take `--subject`, and the verifier also runs the flagship script on S01–S05 for the
record (cheap; feeds P06).

## Scope

**In:** P05.1–P05.5; extend `scripts/exploration/visualize_data.py` with FBCCA/FBCSP
blocks at its P05 extension point (roadmap "extends P03's visualize_data.py");
P04 carry-forward: move `extract_harmonic_features` and `smooth_probabilities_legacy`
(and their constants) from `scripts/training/train_models.py` into `src/` (e.g.
`src/features/ssvep/harmonic_psd.py`, `src/preprocessing/dataset/smoothing.py` — builder's
choice, documented), re-exported from `train_models.py` so P04 tests and imports keep
working; `--seed` on the new scripts.
**Out:** feature selection (P06), two-tier gate (P07), trial-grouped CV (P11).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| ml-engineer | NEW `src/features/ssvep/fbcca_extraction.py` | per [2] P05.1; Chebyshev-I `cheby1(4, 3, [low, min(90, nyq−1)], btype="band", fs=fs)` + `filtfilt` per window (legacy R3); references sin/cos at h·f for h = 1…n_harmonics (3), `t = arange(T)/fs`; CCA(1) on all window channels; `r_b` = Pearson of the canonical variates, 0 on failure; weights b^-1.25+0.25 = 1.25, 0.6704, 0.5033; returns `(X, y_clean, valid_mask)` in P05 | P05.1 | [2] |
| ml-engineer | NEW `src/features/ssvep/fbcsp_extraction.py` | per [2] P05.2; `MulticlassCSP(n_components=m)` with `fit/transform`; `extract_fbcsp_features` full-data, labelled visualization-only; an in-fold helper for the benchmarks | P05.2 | [2] |
| ml-engineer | MODIFIED `src/features/ssvep/psd_extraction.py` | `extract_continuous_psd_features(windows, y, fs=250, freq_range=(5,35), use_db=False)` → `(n, 7·30 = 210)` at fs 250 | P05.3 | [2] |
| ml-engineer | NEW `src/models/classical/sklearn_models.py` | `get_sklearn_model_suite()`, 10 models as [2] P05.4; LogReg via `l1_ratio` (L2 → 0, L1 → 1, EN → 0.5) as 02_REQUIREMENTS §1 says for ≥ 1.8 | P05.4 | [2], [1] §1 |
| ml-engineer | NEW `scripts/benchmarks/feature_based/benchmark_cross_validation.py`, `benchmark_harmonic_fbcca.py`, NEW `scripts/evaluation/test_sklearn_models.py`, `evaluate_confusion_matrix.py` | per [2] P05.5; scaler (and CSP) inside each fold via a Pipeline / fold loop; legacy CV, legacy no-reset smoothing for "2.0 s smoothed", fs 250; CSVs (below), figures `outputs/figures/confusion_matrices/cm_*_cv[_S].png` | P05.5 | [2] |
| ml-engineer | MODIFIED `scripts/exploration/visualize_data.py`, `scripts/training/train_models.py`, NEW `src/…` helper modules, MODIFIED `src/models/cnn/spatial_spectral_cnn.py` (import path only) | P03 extension; P04 carry-forward moves | — | decisions.md P04 |

Settled points (recorded in decisions.md):

- **Window mask** inside the extractors: `validate_eeg_windows` with the shared defaults
  passed explicitly (vpp 5–120 µV, std 1–35 µV) on the stimulus windows; the R-3
  count (197 kept, 3 rejected on S03) is the check. If it does not match, the builder
  investigates once (thresholds, input = filtered windows, per channel), then may
  consult the reference (R11) and documents it.
- **Harmonic PSD (benchmark):** visual cluster `PO8, O1, Oz, O2` by name, 8 bins nearest
  `[8.57, 10.91, 15, 17.14, 20, 21.82, 24, 30]` on the fs-250 periodogram grid of the
  continuous PSD (bin spacing 250/256 Hz), channel-major → 32. (P04's train_models
  harmonic features on `linspace(5,35,31)` stay as they were.)
- **"2.0 s smoothed"** = legacy 2-window average without trial reset over the
  out-of-fold probability array in window order (R8 legacy; same helper as P04).
  If R-3's 95.43 % is not reproduced, the trial-aware `j % 5` variant is computed as
  a diagnostic only and reported (no switch of definition).
- **Outputs:** `reports/feature_space_benchmark_<S>.csv` (columns `Subject, Feature
  space, p, Model, 1.0s Acc (%), 2.0s Smoothed (%), Clean Windows, Rejected`) plus the
  FBCCA argmax row; `reports/flagship_<S>.csv` from `evaluate_confusion_matrix.py`
  (`Subject, Clean Windows, Rejected, m, 1.0s Acc (%), 2.0s Smoothed (%)`);
  classification reports printed and saved as `reports/classification_report_<script>_<S>.txt`.
  QDA excluded from `benchmark_cross_validation` (PF-12) but run, and its failures
  reported, in `test_sklearn_models.py`.

## Legacy behaviour in this phase

| Rule | Behaviour | Label |
|---|---|---|
| R1 | window-level `StratifiedKFold(5, shuffle, 42)` | `legacy (R1, PF-01)` in code, console, CSV header |
| R3 | Chebyshev/Butterworth sub-bands filtered per 1 s window | `legacy (PF-14)` docstrings |
| R8 | no-reset 2-window smoothing | `legacy (PF-02)` |
| fs250 | all extractors default to 250 | `LEGACY_FS_HZ`, printed |
| R5 | per-script window mask, thresholds explicit | printed thresholds |
| R2 exception | `extract_fbcsp_features` full-data fit, visualization only | docstring + `visualize_data` caption |

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R2/PF-11 | CSP or scaler fitted on all windows inside a benchmark | fold loop fits CSP and scaler on training rows only; test with a planted test-only pattern |
| PF-10 | PSD and FBCCA masks differ, blocks misaligned | one mask computed once, all blocks indexed with it; test with a bad window rejected by one gate only |
| R6 | CSP features `(5 classes × 2m)` per band flattened in the wrong order; `(n, 50)` wrong layout | known-answer CSP test (planted spatial source), layout test |
| PF-12 | QDA crashes the benchmark | excluded there; caught and reported in the suite script |
| PF-04 | an extractor runs at fs 256 silently | default 250, printed; tests |
| R-3 | flagship off by more than ±1.5 pp or counts differ | exact counts first; one investigation round; R11 consultation allowed afterwards, logged |
| Golden rule 5 | tuning to hit R-3 | nothing changed to reach R-3 beyond correcting a demonstrated spec deviation |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| references | f, fs 250, T 256, 3 harmonics | `(6, 256)` rows sin/cos(2π h f t), t = n/250 | 1e-12 | [2] P05.1 |
| Chebyshev bands | `get_chebyshev_subbands(250)` | 3 filters, order 4, ripple 3 dB, passbands [6,90],[14,90],[22,90]; at fs 256 high = 90 too (nyq−1 = 127) | design params exact; gain ≈ 1 (−3 dB ripple) inside, ≪ 1 at 2 Hz | [2] |
| FBCCA known answer | 7-channel window with a planted sinusoid at each target (sampled at 250 Hz) + noise | argmax = planted target, `(n, 5)` | — | [2], [1] §7 |
| FBCCA failure | constant window | r = 0, no exception | exact | [2] |
| CSP known answer | 2-class-per-OvR synthetic: class k has extra variance along a known spatial vector | first filter aligns with that vector (|cos| > 0.95); features `(n, 5·2m)` per band; `5 × 2 × 5 = 50` for m=1 | — | [1] §7 |
| CSP math | random SPD covariances | `eigh(Σt, Σt+Σr+1e-6I)` eigenvalues in (0, 1); features = log10(var/Σvar) with floor 1e-12 | 1e-9 | [2] |
| continuous PSD | 256-sample windows, fs 250 | `(n, 210)`; 30 bins 5.86…34.18 Hz | exact | [2], PF-04 |
| visual cluster | names reordered | harmonic PSD picks PO8, O1, Oz, O2 by name, 32 features | exact | §6, PF-06 |
| in-fold CSP | planted pattern only in test rows | benchmark result unchanged by it; full-data CSP would change | — | PF-11 |
| single mask | a window failing only the FBCCA path's input | removed from every block | exact | PF-10 |
| suite | `get_sklearn_model_suite()` | 10 named models with the [2] parameters; QDA reg_param 0.5 | exact | [2] P05.4 |
| legacy CV + smoothing | as P04 | StratifiedKFold(5, True, 42); no reset | exact | R1, R8 legacy |
| scripts smoke | synthetic legacy tree | four scripts + visualize_data exit 0, CSVs/figures | — | [own] |
| P04 regression | P04 tests | still pass after the moves | — | P04 |

Historical bug: PF-11 — the in-fold CSP test fails on a full-data CSP benchmark.

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_harmonic_fbcca --subject S03
.venv/bin/python -m scripts.evaluation.test_sklearn_models --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03 --m 2
for S in S01 S02 S04 S05; do .venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject $S; done
.venv/bin/python -m scripts.exploration.visualize_data --subject S03
```

(Flag names fixed by the builder and copied into `05_run.md`.) Runtime: builder
measures; expected ≪ 120 min (FBCCA ≈ 3 bands × 5 targets CCA per window).

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| S03 FBCSP(m=1)+FBCCA → Shrinkage-LDA = **R-3** (90.36 % / 95.43 %, 197 clean windows, 3 rejected) within tolerance | `reports/flagship_S03.csv` and console | R-3: ±1.5 pp; counts exact |
| the hybrid beats every single-domain space | from `feature_space_benchmark_S03.csv`: best FBCSP+FBCCA row vs best of PSD, harmonic PSD, FBCCA, FBCSP | R-3 qualitative |
| FBCCA argmax is the lowest supervised reference | argmax row below every supervised row on the hybrid spaces (R-3 wording) | R-3 |
| Report the full feature-space × model table | CSV complete: 6 spaces × 9 models + argmax | — |

## Sources

1. `mas/02_REQUIREMENTS.md` §1, §4–§7 (opened in this run).
2. `mas/03_ROADMAP.md` P05 (opened in this run).
3. `mas/01_DATA_SPEC.md` §5.1, §6; `mas/04_REFERENCE_RESULTS.md` R-3; `mas/05_PITFALLS.md` (opened in this run).
4. Library docs (scikit-learn CCA, LDA, LogisticRegression `l1_ratio`; SciPy `cheby1`, `butter`, `eigh`) — builder opens and cites.

## Questions
