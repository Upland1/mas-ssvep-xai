# P04 · 00 · Assignment — Early hybrid models, fusion CNN and first explainability

Status: READY
Author: orchestrator
Branch: phase/P04-early-models-xai (from main @ c52df7e, tag p03-done)
Era: A — legacy behaviours required in this phase (`team.yaml` + `RULES.md` era matrix): **R1** plain `StratifiedKFold(5, shuffle, 42)` over windows; **R8** 2-window causal smoothing without trial reset; **fs250** in FBCCA filters and reference sinusoids; **R3** per-window FBCCA sub-band filtering (inherent to `compute_fbcca_correlations(window, …)`; added to `team.yaml`, decisions.md); **R2 exception** full-data fits for the exported final models and the XAI heatmaps, labelled. 7 channels (config v1).
Owners (agents): ml-engineer (Classical ML, XAI), deep-learning (Deep Learning) — `mas/state/team_mapping.md`; verifier (runs and checks)
Depends on: P02 (passed); sequential scheduling — P03 passed (merged c52df7e)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** `train_models.py`, `spatial_spectral_cnn.py`, `train_final_model.py`,
`batch_run_subjects.py`, `run_xai.py`, `compare_subject_xai.py`: the first model
benchmark on a harmonic-PSD + FBCCA hybrid, a dual-branch CNN, exported per-subject
models and LDA-weight heatmaps. (Its chronology relative to P05 is approximate; it
uses only legacy arrays and leaky CV.)
**Depends on:** P02. **Owners:** Classical ML, Deep Learning, XAI, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `scripts/training/train_models.py`:
   - `extract_harmonic_features(X_psd, n_channels=7, freq_start=5, freq_end=35,
     keep_channels=(1,4,5,6))`: reshape `(n, 7, 31)` on the grid `linspace(5,35,31)`,
     keep channels POz, O1, Oz, O2, keep the nearest bins to `[8.57, 10.91, 15, 20, 24,
     17.14, 21.82, 30]` (deduplicated) → 32 features;
   - `compute_fbcca_correlations(window, fs=250, ...)`: 3 Butterworth order-3
     sub-bands (low cut 6/14/22 Hz, high 55 Hz), references with
     `min(3, 55 // f)` harmonics, sklearn `CCA(n_components=1)`, score
     `Σ_b w_b r_b²` with `w_b = b^-1.25 + 0.25`; `extract_all_fbcca_features`;
   - `run_evaluation`: StandardScaler + {Shrinkage-LDA (lsqr, auto), LogisticRegression
     (C=1, max_iter 1000), Linear SVM (C=1), RBF SVM (C=2, gamma scale), Random Forest
     (150 trees, depth 6, rs 42)} and an MLP (hidden 64-32), `StratifiedKFold(5,
     shuffle, 42)`, accuracy + per-class recall;
   - `run_temporal_integration_evaluation` (2-window causal average **without** trial
     reset — the original early behavior) and confusion-matrix plots per model
     (`outputs/figures/confusion_matrices/cm_<model>.png`);
   - save `outputs/reports/<subject>_model_evaluation.csv`.
2. `src/models/cnn/spatial_spectral_cnn.py`: `DualBranchFusionCNN` — branch 1: input
   `(B,1,4,8)` (4 occipital channels × 8 harmonic bins) → Conv2d(1→16, (4,1)) + BN +
   ELU + Dropout2d(0.3) → Conv2d(16→32, (1,3)) + BN + ELU + Dropout2d → Flatten →
   Linear(32·6→32) + ELU + Dropout (both convolutions **without bias**); branch 2: FBCCA (5) → Linear(5→16) + BN1d + ELU +
   Dropout → Linear(16→16) + ELU; head: concat 48 → Linear(48→32) + ELU + Dropout →
   Linear(32→5). `prepare_spatial_spectral_tensors(X_psd)` builds the input;
   `train_and_eval_fusion_cnn_cv` (StratifiedKFold 5, 140 epochs, batch 16, AdamW lr
   1e-3 wd 1e-2, cosine, label smoothing 0.1, per-fold StandardScalers per branch);
   `evaluate_temporal_smoothing`.
3. `scripts/training/train_final_model.py --subject` (default S04): fit Shrinkage-LDA
   on the full hybrid (32+5) and the fusion CNN on all windows; save
   `outputs/models/<S>_shrinkage_lda.joblib` (dict: model, scaler, classes,
   subject_id, feature_dim) and `outputs/models/<S>_fusion_cnn.pt` (state dict,
   scalers, label maps, subject_id, architecture). Export S01 and S04.
4. `scripts/training/batch_run_subjects.py --subjects --paradigm OO.ebr`: preprocess
   a subject if its arrays are missing, then report LDA 1.0 s / smoothed and fusion CNN
   1.0 s / smoothed per subject.
5. XAI: `scripts/xai/run_xai.py` — Shrinkage-LDA on the scaled hybrid; heatmaps of
   `coef_[:, :32]` reshaped to (5 classes, 4 channels, 8 frequencies) →
   `outputs/figures/xai_heatmaps/xai_spatial_spectral_weights.png`, and of
   `coef_[:, -5:]` → `xai_fbcca_weights.png`. `scripts/xai/compare_subject_xai.py`:
   the same weights for S01 (low SNR) vs S04 (high SNR) side by side from the exported
   joblib files.

## Run (verbatim)

The roadmap gives no run line for P04. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`scripts/training/train_models.py`, `src/models/cnn/spatial_spectral_cnn.py`, `scripts/training/train_final_model.py`, `scripts/training/batch_run_subjects.py`, `scripts/xai/run_xai.py`, `scripts/xai/compare_subject_xai.py`, `outputs/models/{S01,S04}_{shrinkage_lda.joblib,fusion_cnn.pt}`

## Acceptance (verbatim)

Acceptance: all scripts run; figures and CSV exist; DualBranchFusionCNN has 10,005
parameters (R-8); numbers recorded in the phase report (no reference targets — R-2 lists what the original saved). The Reviewer notes
in the report that this phase's CV is leaky and its smoothing ignores trial
boundaries (fixed in P11).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-2 | mas/04_REFERENCE_RESULTS.md | what the original saved (CSV columns `Subject, Classifier, Accuracy, Recall per Class`, confusion matrices for LDA, linear SVM, RBF SVM, RF, MLP, XAI heatmaps, S01/S04 models); no numeric targets |
| R-8 | mas/04_REFERENCE_RESULTS.md, B004 | DualBranchFusionCNN = 10,005 parameters, exact, both convs `bias=False` (checked: sum of layer counts = 10005, log.md step 2) |
| R-6 | mas/RULES.md | leak-free flagship for later comparison; P04 numbers are leaky by design and must not be compared as equals |
| PF-01, PF-02 | mas/05_PITFALLS.md | leaky CV and smoothing across trials — reproduced here, labelled `legacy`, fixed in P11 |
| PF-04 | mas/05_PITFALLS.md | FBCCA designed with fs 250 on 256 Hz data (references off-frequency by 256/250) |
| PF-14 | mas/05_PITFALLS.md | FBCCA sub-bands filtered on 1 s windows (edge effects; fixed P16) |
| PF-06, 01_DATA_SPEC §6 | | `keep_channels=(1,4,5,6)` = POz, O1, Oz, O2 of the 7-channel layout (positional in the legacy signature; names asserted) |
| PF-11 (spirit) | mas/05_PITFALLS.md | scaler/LDA inside folds for CV numbers; full-data fits only for exported models and XAI, labelled |
| PF-28 | mas/05_PITFALLS.md | seed per fold before building the CNN (good practice already here) |
| R2, R6, R9, R10, R11 | mas/RULES.md | in-fold scaling; `(5, 4, 8)` coefficient reshape proven; per-subject numbers with data source; cite; `after-attempt` |
| decisions.md P02/P03 | | stimulus windows only (no 201/202 twin issue); S01/S02 weak responders; S05 harmonics |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| ml-engineer | P04.1, P04.5, and the LDA parts of P04.3 and P04.4 — first builder, creates the branch | `03_changes_ml-engineer.md` |
| deep-learning | P04.2 and the fusion-CNN parts of P04.3 and P04.4 (after ml-engineer is READY) | `03_changes_deep-learning.md` |
| synthetic-tester | known-answer tests of the plan | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review incl. the leaky-CV / no-reset note | `07_review.md` |
| verifier | run commands from a clean checkout and acceptance | `05_run.md`, `06_verify.md` |
| scribe | phase report | `mas/state/reports/P04.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
