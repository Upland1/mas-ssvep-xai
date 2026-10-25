# P04 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §5.1, §6, mas/02_REQUIREMENTS.md §4, §5, §6, mas/04_REFERENCE_RESULTS.md R-2, R-8, mas/05_PITFALLS.md PF-01/02/04/06/11/14/28, B004, P02/P03 rows of decisions.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Reproduce the original's first model benchmark — a 37-feature hybrid (32 harmonic-PSD
+ 5 FBCCA), six sklearn classifiers, a 10,005-parameter dual-branch fusion CNN — under
the legacy leaky CV and no-reset smoothing, plus exported S01/S04 models and LDA-weight
heatmaps.

## Data source

Legacy folders `data/processed/<S>/{X_psd_features,X_time_windows,y_labels}.npy` from
P02 (OO, 7 channels, 256 samples), **stimulus windows only** (101–105; 5 classes,
chance 20 %), S01–S05 discovered. FBCCA on `X_time_windows` with legacy fs 250. No
raw data is read except through `run_preprocessing` when a subject's arrays are
missing (P04.4).

## Scope

**In:** the five roadmap tasks. **Out:** the P05 extractors and benchmark, trial-grouped
CV (P11), any change to P02 arrays.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| ml-engineer | NEW `scripts/training/train_models.py` | `extract_harmonic_features` (verbatim signature; positions (1,4,5,6) asserted to be POz, O1, Oz, O2 by name from config v1; bins nearest to the 8 targets on `linspace(5,35,31)` = 9, 11, 15, 17, 20, 22, 24, 30 Hz; channel-major `(4, 8)` flatten); `compute_fbcca_correlations(window, fs=250, …)` (all 7 channels of the window; `scipy.signal.butter(3, [low, 55], btype="band", fs=fs)` + `filtfilt` per sub-band; references sin/cos at h·f, h = 1…`min(3, 55 // f)`, `t = arange(T)/fs`; `CCA(n_components=1)`, r = corr of the first canonical pair; score `Σ_b w_b r_b²`, `w_b = b^-1.25 + 0.25`, b = 1, 2, 3); `extract_all_fbcca_features`; `run_evaluation` (each classifier in a `Pipeline(StandardScaler, clf)`, `StratifiedKFold(5, shuffle=True, random_state=42)`, out-of-fold predictions and probabilities); `run_temporal_integration_evaluation` (legacy 2-window average over the out-of-fold probability array in window order, no reset); confusion matrices; CSV | P04.1 | [2] P04.1, [3] §6 |
| ml-engineer | NEW `scripts/training/train_final_model.py` (LDA part), NEW `scripts/training/batch_run_subjects.py` (LDA part) | full-data Shrinkage-LDA on the scaled hybrid (labelled R2 exception: export only) → joblib dict of P04.3; batch script: `--subjects`, `--paradigm OO.ebr`, preprocess missing subjects via `scripts.preprocessing.run_preprocessing`, LDA 1.0 s / smoothed (leaky CV) per subject, CSV `outputs/reports/batch_run_subjects.csv` | P04.3, P04.4 | [2] |
| ml-engineer | NEW `scripts/xai/run_xai.py`, `scripts/xai/compare_subject_xai.py` | full-data LDA (labelled) on the scaled hybrid of `--subject` (default S04); heatmaps `coef_[:, :32] → (5, 4, 8)` and `coef_[:, -5:]`; comparison S01 vs S04 from the joblib files → `outputs/figures/xai_heatmaps/compare_S01_S04.png` | P04.5 | [2] P04.5 |
| deep-learning | NEW `src/models/cnn/spatial_spectral_cnn.py` | `DualBranchFusionCNN` exactly per [2] P04.2 (convs `bias=False`, R-8 10,005); `prepare_spatial_spectral_tensors(X_psd)` via `extract_harmonic_features` → `(n, 1, 4, 8)`; `train_and_eval_fusion_cnn_cv` (StratifiedKFold 5 shuffle 42; 140 epochs; batch 16; AdamW 1e-3 / wd 1e-2; `CosineAnnealingLR(T_max=140)`; `CrossEntropyLoss(label_smoothing=0.1)`; per-fold StandardScalers fitted on the training fold for each branch; `torch.manual_seed(42 + fold)` before building each fold's model, seeded DataLoader generator; `--device` auto); `evaluate_temporal_smoothing` (legacy, no reset) | P04.2 | [2] P04.2, R-8, PF-28 |
| deep-learning | MODIFIED `scripts/training/train_final_model.py`, `scripts/training/batch_run_subjects.py` (CNN parts) | full-data fusion-CNN fit (labelled) → `.pt` dict of P04.3; batch script adds fusion CNN 1.0 s / smoothed | P04.3, P04.4 | [2] |

Settled ambiguities (recorded in decisions.md): FBCCA uses all 7 channels of the
window; Linear SVM = `SVC(kernel="linear", C=1)`, RBF = `SVC(kernel="rbf", C=2,
gamma="scale")`, both `probability=True, random_state=42`; MLP =
`MLPClassifier((64, 32), max_iter=1000, random_state=42)`; LogisticRegression C=1,
max_iter 1000, other defaults; `train_models.py` takes `--subject` (default S01, the
subject of R-2's saved CSV) and `--all`; confusion matrices per subject under
`outputs/figures/confusion_matrices/<S>/cm_<model>.png`, with the verbatim
path holding S01 (as the P02 figure rule).

## Legacy behaviour in this phase

| Rule | Behaviour | Label / flag |
|---|---|---|
| R1 | `StratifiedKFold(5, shuffle, 42)` over windows | `# legacy (R1, PF-01): fixed in P11` in code; CSV/console header says `cv=StratifiedKFold (legacy, leaky)` |
| R8 | 2-window average without trial reset | function docstrings + console `smoothing: legacy no-reset (PF-02)` |
| fs250 | FBCCA filters and references with fs 250 | `LEGACY_FS_HZ`, printed |
| R3 | FBCCA sub-bands filtered per 1 s window | docstring `legacy (PF-14)` |
| R2 exception | full-data LDA / CNN for export and XAI | file metadata `fit: full data (export/XAI only)` |

All stay reachable after P11/P16 because the functions keep the legacy defaults and
the fixed versions are added beside them.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R2 | scaler or CNN scalers fitted on all windows for CV numbers | `Pipeline` in folds; per-fold scalers; test with a planted leak |
| R6 | harmonic features or LDA `coef_` reshaped frequency-major | channel-major known-answer tests on `(4, 8)` and `(5, 4, 8)` |
| R-8 | conv biases or wrong layer sizes | exact parameter count test 10,005 |
| PF-04 | FBCCA silently at fs 256 | fs printed; test: reference at fs 250 vs 256 differ |
| PF-06 | positional channels pointing elsewhere | names asserted for (1,4,5,6) |
| PF-28 | nondeterministic CNN | seeds per fold; two smoke runs equal |
| Interpretation | leaky accuracies read as real | reviewer and report state leaky + no-reset; R-6 not used as a target |
| R9 | cohort-only numbers | per-subject CSVs and console |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source of the answer |
|---|---|---|---|---|
| harmonic features | `X_psd (n, 217)` with value `100·c + j` at channel c, bin j | 32 features = channels (1,4,5,6) × bins (4,6,10,12,15,17,19,25) in channel-major order | exact | [2] P04.1, R6 |
| FBCCA known answer | window = sinusoid at target k sampled at 250 Hz (fs consistent) + noise, 7 channels | target k has the highest score; scores in [0, Σ w_b] | — | [2] P04.1 |
| FBCCA legacy fs | 24 Hz sinusoid sampled at 256 Hz, scored with fs 250 vs fs 256 | scores differ; with fs 256 class 101 wins with a higher r | — | PF-04 |
| FBCCA weights / harmonics | `w_b` for b=1..3; harmonics per target | 1.25, 0.6704, 0.5033 (b^-1.25+0.25; `.venv/bin/python` in log.md step 4); harmonics 2, 2, 3, 3, 3 | 1e-4 | [2] |
| in-fold scaling | features with a constant offset only in test-fold rows | pipeline result unchanged vs a scaler fitted per fold by hand | — | R2 |
| legacy CV | `run_evaluation` splits | equal to `StratifiedKFold(5, True, 42).split` | exact | R1 legacy |
| no-reset smoothing | probabilities of 10 windows | `p̄_0 = p_0`, `p̄_j = (p_{j−1}+p_j)/2` for all j ≥ 1 (no reset at j % 5) | exact | [2] P04.1, PF-02 |
| fusion CNN params | instantiate | 10,005 trainable parameters; conv biases None | exact | R-8 |
| fusion CNN forward | `(B,1,4,8)`, `(B,5)` | output `(B,5)`, gradients flow to both branches | — | [2] P04.2 |
| tensor builder | `X_psd` as in row 1 | `(n,1,4,8)` with `[i,0,r,c]` = harmonic feature `8r + c` | exact | R6 |
| per-fold scalers | planted offset in test fold | CNN scalers' means equal the training-fold means | 1e-12 | R2 |
| determinism | 2 short CV runs (2 epochs, CPU) | identical predictions | exact | PF-28 |
| XAI reshape | LDA with known `coef_` | heatmap arrays `(5,4,8)` and `(5,5)` equal the slices | exact | R6 |
| exports | train_final_model on synthetic arrays | joblib/pt dicts have the P04.3 keys; reload predicts the same | exact | [2] P04.3 |
| CSV schema | run_evaluation | columns `Subject, Classifier, Accuracy, Recall per Class` | exact | [1] §6 |
| scripts smoke | synthetic legacy tree | every script exits 0, figures and CSVs written | — | [own] |

Historical bug: PF-01/PF-02 are reproduced, not fixed; the no-reset test pins the
legacy behaviour (it fails on a trial-aware implementation), and P11 adds the fix.

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.training.train_models --all
.venv/bin/python -m scripts.training.train_final_model --subject S01
.venv/bin/python -m scripts.training.train_final_model --subject S04
.venv/bin/python -m scripts.training.batch_run_subjects --subjects S01 S02 S03 S04 S05 --paradigm OO.ebr
.venv/bin/python -m scripts.xai.run_xai --subject S04
.venv/bin/python -m scripts.xai.compare_subject_xai
```

Expected runtime: FBCCA 15 CCA fits × 3 bands per window (≈ 1,000 stimulus windows per
pass, two passes); fusion CNN 25 folds × 140 epochs × ~10 batches. Builders give a
measured smoke estimate in their handoff; target < 30 min total on CPU, GPU optional.
Over `LOCAL_RUN_BUDGET_MIN` (120)? no (to be confirmed by the builders' estimate).
Logs `reports/logs/P04/<script>_<timestamp>.log`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| all scripts run | six commands exit 0 (return codes captured) | — |
| figures and CSV exist | `cm_<model>.png` (6 models × subjects), XAI heatmaps (2 + comparison), `<S>_model_evaluation.csv` per subject, `batch_run_subjects.csv`, models `{S01,S04}_{shrinkage_lda.joblib,fusion_cnn.pt}` | R-2 |
| DualBranchFusionCNN has 10,005 parameters (R-8) | instantiate and count | R-8, exact |
| numbers recorded in the phase report | per-subject accuracies and recalls tabulated from the CSVs | R-2 (none) |
| The Reviewer notes … leaky … ignores trial boundaries | results review | PF-01/02 |

## Sources

1. `mas/02_REQUIREMENTS.md` §4–§6 (opened in this run).
2. `mas/03_ROADMAP.md` P04 (opened in this run).
3. `mas/01_DATA_SPEC.md` §5.1, §6 (opened in this run).
4. `mas/04_REFERENCE_RESULTS.md` R-2, R-8; `mas/05_PITFALLS.md`; B004 (opened in this run).
5. scikit-learn `CCA`, `LinearDiscriminantAnalysis`; SciPy `signal.butter`/`filtfilt`; PyTorch `nn.Conv2d`, `CosineAnnealingLR` documentation (builders open and cite).

## Questions
