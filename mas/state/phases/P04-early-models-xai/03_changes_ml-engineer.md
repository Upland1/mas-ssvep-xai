# P04 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md
Branch: phase/P04-early-models-xai
Commit(s): 54cdf48 (bookkeeping), ad8f3be (train_models), 3612774 (final LDA + XAI), 9e5caba (batch + smoke tests); a warning-filter tweak to train_models is inside 3612774

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| scripts/training/train_models.py | NEW | features (harmonic PSD, FBCCA), 6 Pipeline(StandardScaler, clf) classifiers, legacy CV, no-reset smoothing, CM plots, CSV | P04.1 | R1/R2/R8, PF-01/02/04/06/14 |
| scripts/training/train_final_model.py | NEW | full-data scaler + Shrinkage-LDA -> joblib dict (LDA part) | P04.3 | R2 exception |
| scripts/training/batch_run_subjects.py | NEW | preprocess missing subjects, LDA 1.0 s / smoothed CSV (LDA part) | P04.4 | — |
| scripts/xai/run_xai.py | NEW | coef_ (5,4,8) and (5,5) heatmaps | P04.5 | R6 |
| scripts/xai/compare_subject_xai.py | NEW | S01 vs S04 from joblib | P04.5 | — |
| tests/test_p04_ml_smoke.py | NEW | 4 smoke tests (synthetic tree in tmp_path) | — | — |

## Legacy behaviour implemented
R1 (`legacy_cv()`, header `cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky)`), R8 (`smooth_probabilities_legacy`, over array order, no reset), fs250 (`LEGACY_FS_HZ`, printed), R3/PF-14 (per-window filtfilt in `compute_fbcca_correlations`), R2 exception (joblib key `fit` = full data export/XAI only; figure captions). CSV columns also carry `cv` and `smoothing`.

## Differences from the cited examples
None adapted; R11 reference repo not consulted.

## Deviations from the plan
- Harmonic bin order is sorted index (9,11,15,17,20,22,24,30 Hz), matching the plan's test row.
- Extra CSV columns after the four R-2 ones: Smoothed Accuracy, Smoothed Recall per Class, n_windows, cv, smoothing. Accuracy/recall come from fold `predict`; smoothing uses `predict_proba` of the same fits.
- Joblib dict has extra keys (fit, data_source, feature_names, n_windows). XAI for a subject other than S04 writes files with suffix `_<S>`. FBCCA panels use their own colour scale in the comparison figure (PSD weights dwarf FBCCA ones on a shared scale).
- Confusion matrices: 6 models (incl. Logistic Regression), per subject plus S01 at the root path.
- SVC(probability=True) FutureWarning silenced (setting fixed by decisions.md).

## Hook points for deep-learning
- train_final_model.py: `load_subject_inputs(processed, S)` returns (X_psd, X_time, y, hybrid); add `export_fusion_cnn(...)` writing `<models-dir>/<S>_fusion_cnn.pt` at the marked `HOOK(deep-learning)` line in `main` (models dir = `<out>/models`). `fit_full_lda`, `FIT_LABEL` reusable.
- batch_run_subjects.py: `evaluate_subject` returns the row dict; add CNN columns at the `HOOK` comment (hybrid[:, -5:] = FBCCA).
- train_models.py exports `extract_harmonic_features`, `build_hybrid`, `legacy_cv`, `smooth_probabilities_legacy`, `load_stimulus_windows`, `CLASS_CODES` (labels are codes 101..105; subtract 101 for indices).

## How to run / reproduce
Plan run commands; all accept `--processed-dir` and `--out-dir` (smoke: synthetic tree under mas/state/scratch/p04smoke/).

## How I verified
`.venv/bin/python -m pytest tests/test_p04_ml_smoke.py -q`: 4 passed. Synthetic smoke (200 stimulus windows, no real data): train_models --subject S01 total 6.5 s wall (all 6 classifiers + 12 CM figures). Estimate on ~200 real stimulus windows per subject (same size, as per R-1: 198-200): about 7-15 s per subject, ~1-2 min for `--all`; final model, XAI, batch each ~10 s per subject (FBCCA recomputed per script). LDA/classical part far below the 30 min target; the CNN CV (25 folds x 140 epochs) dominates. Figures inspected on synthetic data (class-diagonal weights as planted).

## Questions
ACK 02_plan.md ml-engineer 2026-10-24
