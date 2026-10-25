# P05 · 00 · Assignment — Feature extractors and feature-space / model benchmark

Status: READY
Author: orchestrator
Branch: phase/P05-feature-benchmark (from main @ 6e627d9, tag p04-done)
Era: A — legacy behaviours required (`team.yaml`, `RULES.md` era matrix): **R1** `StratifiedKFold(5, shuffle, 42)` over windows; **R3** per-window sub-band filtering (FBCCA Chebyshev, FBCSP Butterworth); **R8** no-reset 2-window smoothing; **fs250** in all extractors; **R5** per-script window mask (legacy); **R2 exception** `extract_fbcsp_features` full-data fit for visualization only (benchmarks fit CSP in-fold). 7 channels (config v1).
Owners (agents): ml-engineer (Classical ML); verifier
Depends on: P02, P03 (passed; P04 passed, sequential)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Commits "implement PSD, FBCCA, and FBCSP extractions with quality masking",
"add 5-fold CV benchmark suite, confusion matrix diagnostics", "validate hybrid
FBCSP+FBCCA pipeline on subject (95.43% smoothed CV)".
**Depends on:** P02, P03 (extends P03's `visualize_data.py`). **Owners:** Classical ML, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/features/ssvep/fbcca_extraction.py`:
   `TARGET_FREQS = [24.0, 20.0, 15.0, 10.9091, 8.5714]`;
   `generate_reference_signals(f, fs, n_samples, n_harmonics)` (sin/cos rows);
   `get_chebyshev_subbands(fs)`: 3 Chebyshev-I filters, order 4, 3 dB ripple,
   passband `[low, min(90, nyq-1)]` for low ∈ {6, 14, 22} Hz;
   `extract_fbcca_features(windows, y, fs=250.0, target_freqs, n_harmonics=3, …)` →
   per window, per target, per sub-band: CCA(1) between the filtered window and the
   references, `r_b` = Pearson of the canonical variates (0 on failure); score
   `Σ_b w_b r_b²`, `w_b = b^-1.25 + 0.25` → `(n, 5)`.
   In P05 the function applies only the window mask; P07 adds the channel tier and
   P16 adds `subband_windows=` / `quality=`. Return signature from P07 on:
   `(X, y_clean, valid_mask, channel_report)`.
2. `src/features/ssvep/fbcsp_extraction.py`: `DEFAULT_SUBBANDS = [(7,12), (13,17),
   (18,26), (27,36), (38,52)]`; `butter_bandpass_filter` (Butterworth order 4, filtfilt,
   high capped at nyq−1); `MulticlassCSP(n_components=1)`: one-vs-rest per class;
   trace-normalized covariances `Σ = W Wᵀ / tr(W Wᵀ)` averaged per group; generalized
   eigenproblem `eigh(Σ_target, Σ_target + Σ_rest + 1e-6 I)`; keep the `m` largest and
   `m` smallest eigenvectors; features = `log10(var_k / Σ var)` of the projections
   (variances floored at 1e-12) → `5 classes × 2m` per band; `extract_fbcsp_features`
   (full-data fit, **for visualization only** — benchmarks fit CSP in-fold).
3. `extract_continuous_psd_features(windows, y, fs=250, freq_range=(5,35), use_db=False)`
   → periodogram, flattened.
4. `src/models/classical/sklearn_models.py::get_sklearn_model_suite()` — 10 models:
   RidgeClassifier(α=1, balanced); LogReg L2 (lbfgs, C=1, 1000 it, balanced); LogReg
   L1 (saga, 3000 it, tol 1e-3, balanced); LogReg Elastic-Net (l1_ratio 0.5, saga);
   SGD log-loss (elasticnet, l1_ratio 0.5, α 1e-3, 2000 it, balanced, rs 42); SGD
   passive-aggressive (hinge, no penalty, `learning_rate="pa1"`, eta0 1, 2000 it);
   LDA svd; Shrinkage-LDA lsqr auto; Shrinkage-LDA eigen auto; QDA reg_param 0.5.
5. Benchmarks (legacy: `StratifiedKFold(5, shuffle, 42)`, `fs=250`):
   - `benchmark_cross_validation.py --subject`: 6 feature spaces × suite (QDA
     excluded): continuous PSD (p=210/217), harmonic PSD on the visual cluster
     (8 targeted bins `[8.57, 10.91, 15, 17.14, 20, 21.82, 24, 30]` × 4 ch = 32), FBCCA
     (5), harmonic PSD + FBCCA (37), FBCSP in-fold (50), FBCSP + FBCCA (55); plus the
     zero-training FBCCA argmax baseline;
   - `benchmark_harmonic_fbcca.py --subject`: occipital harmonic PSD + FBCCA →
     Shrinkage-LDA, confusion matrix + classification report
     (`cm_harmonic_fbcca_cv[_S].png`);
   - `scripts/evaluation/test_sklearn_models.py --subject`: the suite on PSD, FBCCA,
     FBCSP features;
   - `scripts/evaluation/evaluate_confusion_matrix.py --subject`: FBCSP (m=1, in-fold) +
     FBCCA → scaler → Shrinkage-LDA, out-of-fold confusion matrix and 1.0 s / 2.0 s
     smoothed accuracy (`cm_fbcsp_m1_fbcca_cv[_S].png`; m=2 variant →
     `cm_fbcsp_m2_fbcca_cv.png`).

## Run (verbatim)

The roadmap gives no run line for P05. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/features/ssvep/fbcca_extraction.py`, `src/features/ssvep/fbcsp_extraction.py`, `src/features/ssvep/psd_extraction.py`, `src/models/classical/sklearn_models.py`, `benchmark_cross_validation.py`, `benchmark_harmonic_fbcca.py`, `test_sklearn_models.py`, `evaluate_confusion_matrix.py`

## Acceptance (verbatim)

Acceptance: S03 FBCSP(m=1)+FBCCA → Shrinkage-LDA = **R-3** (90.36 % / 95.43 %, 197
clean windows, 3 rejected) within tolerance; the hybrid beats every single-domain
space; FBCCA argmax is the lowest supervised reference. Report the full
feature-space × model table.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-3 | mas/04_REFERENCE_RESULTS.md | S03 flagship 90.36 % / 95.43 %, 197 clean / 3 rejected; tolerance: deterministic classical ±1.5 pp per subject, window counts **exact**; qualitative: perfect 24 Hz precision, residual 10.91/8.57 confusion, hybrid + lsqr LDA best, every supervised hybrid config beats FBCCA argmax |
| PF-10 | mas/05_PITFALLS.md | double gating: every feature block aligned with the final mask |
| PF-11 | mas/05_PITFALLS.md | full-data CSP only for visualization; benchmarks fit CSP in each training fold |
| PF-12 | mas/05_PITFALLS.md | QDA excluded from high-dimensional benchmarks, kept in the suite |
| PF-04, PF-14 | mas/05_PITFALLS.md | fs 250 and per-window sub-band filtering, legacy, labelled |
| PF-06, 01_DATA_SPEC §6 | | visual cluster for the benchmark's harmonic PSD = `PO8, O1, Oz, O2` by name (positions 3–6 of the 7-channel layout); P04 used `POz, O1, Oz, O2` — different sets |
| PF-01, PF-02 | mas/05_PITFALLS.md | leaky CV and no-reset smoothing reproduced (fixed P11) |
| R2, R5, R6 | mas/RULES.md | in-fold scaler/CSP; mask thresholds explicit; CSP filter and feature layout `(C, 2m)`, `5 × 2m × 5 bands = 50` proven synthetically |
| 02_REQUIREMENTS §1, §7 | | `LogisticRegression(l1_ratio=…)` style (sklearn 1.9.1: `penalty` deprecated); CSP and FBCCA tests |
| decisions.md P04 | | carry-forward: move `extract_harmonic_features` / smoothing helper out of `scripts/` into `src/`; `--seed` CLI; `compare_subject_xai` colourbar + docstring (only if touched) |
| R9, R10, R11 | mas/RULES.md | per-subject; cite; `after-attempt` (allowed for the R-3 diagnosis after one investigation round) |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| ml-engineer | P05.1–P05.5, the P03 `visualize_data.py` extension, the P04 carry-forward moves — first builder | `03_changes_ml-engineer.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P05.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
