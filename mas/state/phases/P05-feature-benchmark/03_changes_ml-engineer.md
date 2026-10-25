# P05 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md
Branch: phase/P05-feature-benchmark (from main @ 6e627d9)
Commit(s): b6f0235 (bookkeeping), 031f926, ae09593, 12ae977, 2ec98b2, 54f2b4f, deb6597, 1491170, 1b6c3de, c9cc631 (HEAD)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/ssvep/window_mask.py` | NEW | `P05_MASK_THRESHOLDS` (vpp 5-120, std 1-35, written out) and `resolve_window_mask(windows, valid_mask, thresholds)`: a passed mask is used as given (length-checked), otherwise the explicit gate runs | P05 mask (decisions.md) | R5, PF-10, [own] |
| `src/features/ssvep/fbcca_extraction.py` | NEW | `TARGET_FREQS`, `generate_reference_signals` `(2H, T)`, `get_chebyshev_subbands(fs)` (cheby1 order 4, 3 dB, `[low, min(90, nyq-1)]`), `canonical_correlation` (CCA(1), r = 0 on failure), `extract_fbcca_features(...) -> (X, y_clean, valid_mask)` | P05.1 | [2], [5] |
| `src/features/ssvep/fbcsp_extraction.py` | NEW | `DEFAULT_SUBBANDS`, `butter_bandpass_filter`, `filter_subbands`, `MulticlassCSP(n_components=m)`, `FBCSPTransformer` (per-band CSP, fit on rows given), `extract_fbcsp_features` (full-data fit, visualization only) | P05.2 | [2], [6], [7] |
| `src/features/ssvep/psd_extraction.py` | MODIFIED | `continuous_psd_freqs`, `extract_continuous_psd_features(windows, y, fs=250, freq_range=(5,35), use_db=False, valid_mask=, thresholds=) -> (X, y_clean, valid_mask)`, `(n, 210)` | P05.3 | [2] |
| `src/features/ssvep/harmonic_psd.py` | NEW | P04 `extract_harmonic_features` etc. moved here; P05 `visual_cluster_harmonic_psd` (PO8, O1, Oz, O2 by name, nearest-bin on the continuous-PSD grid), `nearest_bin_indices` | carry-forward + P05.5 | decisions.md P04/P05, PF-06 |
| `src/preprocessing/dataset/smoothing.py` | NEW | `smooth_probabilities_legacy` (moved), `smooth_probabilities_mod5` (diagnostic only) | carry-forward | R8, PF-02 |
| `src/preprocessing/dataset/legacy_windows.py` | NEW | `arrays_exist`, `load_stimulus_windows`, `CLASS_CODES` (moved from train_models) | carry-forward | [own] |
| `src/models/classical/sklearn_models.py` | NEW | `get_sklearn_model_suite(seed=42)`: 10 models, `l1_ratio` style, `QDA_NAME`, `MODEL_NAMES` | P05.4 | [2], [1] §1, [8] |
| `src/models/classical/legacy_eval.py` | NEW | `legacy_cv(seed)`, `FeatureSpace`, `fold_matrices` (CSP fitted on training rows), `oof_space` (Pipeline(StandardScaler, model) per fold, failures caught), `class_scores` (proba or softmax of decision function), `accuracies`, `fbcca_argmax_baseline` | P05.5 | R1/R2/R8 legacy, PF-11/12 |
| `src/models/classical/feature_spaces.py` | NEW | `build_feature_blocks` (mask once, all blocks on that mask, alignment check), `benchmark_spaces` (6 spaces) | P05.5 | PF-10 |
| `src/models/classical/benchmark_runner.py` | NEW | config/subject loading, header lines, classification report, confusion-matrix figure, figure paths | P05.5 | [own] |
| `scripts/benchmarks/feature_based/benchmark_cross_validation.py` | NEW | 6 spaces x 9 models (no QDA) + FBCCA argmax; `reports/feature_space_benchmark_<S>.csv` + `.meta.txt` | P05.5 | [2] |
| `scripts/benchmarks/feature_based/benchmark_harmonic_fbcca.py` | NEW | harmonic PSD + FBCCA -> Shrinkage-LDA, `cm_harmonic_fbcca_cv[_S].png`, classification report | P05.5 | [2] |
| `scripts/evaluation/test_sklearn_models.py` | NEW | suite (incl. QDA, failures caught and printed) on PSD, FBCCA, FBCSP; `reports/sklearn_suite_<S>.csv` | P05.5 | [2], PF-12 |
| `scripts/evaluation/evaluate_confusion_matrix.py` | NEW | flagship FBCSP(m, in-fold) + FBCCA -> scaler -> Shrinkage-LDA lsqr; `flagship_<S>.csv` (one row per m), `cm_fbcsp_m<m>_fbcca_cv[_S].png`; j%5 smoothing printed as a labelled diagnostic | P05.5 | [2], R-3 |
| `scripts/exploration/visualize_data.py` | MODIFIED | blocks `fbcca`, `fbcsp` (block call gets `y`); default `--features psd fbcca fbcsp`; heatmaps `fbcca_features_by_class.png`, `fbcsp_features_by_class.png` whose caption states the full-data CSP fit | P03 extension | R2 exception, PF-11 |
| `scripts/training/train_models.py` | MODIFIED | helpers removed and re-exported from src (`extract_harmonic_features`, `harmonic_bin_indices`, `check_keep_channels`, constants, `load_stimulus_windows`, `arrays_exist`, `smooth_probabilities_legacy`); `--seed` (default 42) | carry-forward | decisions.md P04 |
| `src/models/cnn/spatial_spectral_cnn.py` | MODIFIED | import path only (src, no lazy `scripts.*` import) | carry-forward | decisions.md P04 |
| `tests/test_p04_early_models_known_answer.py` | MODIFIED | one line: the monkeypatch of the smoothing helper now targets `cnn` (name is bound in the module after the move) | carry-forward | [own] |
| `tests/p05_synth.py` | NEW | synthetic legacy subject folder (seeded) | tests | [own] |
| `tests/test_p05_feature_benchmark.py` | NEW | 28 tests (below) | tests | [own] |
| `tests/test_no_leakage.py` | NEW | R1/R8 no-leakage registry: `assert_no_shared_groups`, leak-free splitters, legacy splitters documented as leaky, repo scan so an unregistered splitter fails | R1, R8 | [own] |

## Legacy behaviours implemented

- R1 / PF-01: `legacy_cv()` = `StratifiedKFold(5, shuffle, seed 42)` over windows; label `legacy (R1, PF-01)` in docstrings, console header and the `.meta.txt` sidecar.
- R8 / PF-02: "2.0 s smoothed" = `smooth_probabilities_legacy` (no reset) over the out-of-fold scores; `smooth_probabilities_mod5` only as the printed DIAGNOSTIC in `evaluate_confusion_matrix.py`.
- R3 / PF-14: Chebyshev (FBCCA) and Butterworth (FBCSP) sub-bands filtered on each 1 s window.
- PF-04: every extractor and script defaults to `fs = LEGACY_FS_HZ = 250` (printed; `--fs` exists).
- R5: per-script mask with the shared limits written out (vpp 5-120 uV, std 1-35 uV), printed.
- R2 exception / PF-11: `extract_fbcsp_features` (full-data CSP) is used only in `visualize_data` (caption says so); all benchmarks fit the CSP in each training fold.

## Differences from the cited examples

- CSP feature normalisation: `log10(var_j / sum_j var_j)` is normalised per class over that class's `2m` projections (Ramoser form). The spec text ("`Σ var`") does not say whether the sum runs over the `2m` components of one class or all `5 x 2m`. I implemented the per-class form; this is the one place where R-3 could move.
- FBCCA references use 3 harmonics for every target (spec), unlike P04's `min(3, 55 // f)`; sub-band filters are Chebyshev-I order 4 (P04: Butterworth order 3). P04 code is untouched.
- sklearn `CCA(n_components=1)` (as P04) rather than a closed-form canonical correlation.

## Deviations from the plan

1. `visualize_data.py` default `--features` is now `psd fbcca fbcsp` (the plan run line has no flag); the P03 tests (28) still pass.
2. One P04 test line edited (see table); behaviour asserted is unchanged.
3. Models without `predict_proba` (Ridge, SGD PA) get a softmax of the decision function for the 2.0 s smoothing (not in the plan; labelled in `sklearn_models.py` and `class_scores`).
4. FBCCA argmax row: no folds (nothing fitted), evaluated on all clean windows; its 2.0 s value smooths row-normalised scores.
5. `--seed` was added to `train_models.py` only; `batch_run_subjects`, `train_final_model` and `run_xai` keep their fixed seed 42 (the R-8 parameter count and P04 CNN numbers depend on it).
6. The `compare_subject_xai` colourbar/docstring fix was not done (script not touched).
7. Extra outputs not in the plan: `reports/feature_space_benchmark_<S>.meta.txt`, `reports/sklearn_suite_<S>.csv`.

## How to run / reproduce

Flags are the defaults; subject default is S03. All write under `reports/` and `outputs/figures/`.

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_harmonic_fbcca --subject S03
.venv/bin/python -m scripts.evaluation.test_sklearn_models --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03
.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject S03 --m 2
for S in S01 S02 S04 S05; do .venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --subject $S; done
.venv/bin/python -m scripts.exploration.visualize_data --subject S03
```

Optional on every new script: `--seed` (42), `--fs` (250), `--processed-dir`, `--reports-dir`, `--figures-dir`; flagship also `--m`, `--no-figures`.

Runtime estimate (synthetic S03-sized tree, 200 stimulus windows, CPU, 2-min `time` readings): benchmark_cross_validation 22 s, harmonic_fbcca 8 s, test_sklearn_models 15 s, evaluate_confusion_matrix 6 s (m=1; m=2 similar), visualize_data a few seconds. Real data converges more slowly for the saga models; I budget 3x: all seven plan commands plus the four extra subjects well under 5 min total, far below `LOCAL_RUN_BUDGET_MIN` (120). Full suite `pytest tests` took 111 s (383 passed), 28 s of it P05 tests.

## How I verified

- `pytest tests`: `383 passed in 111.41s`. P03 (28) and P04 tests pass after the moves; `tests/test_p05_feature_benchmark.py` 28 passed, `tests/test_no_leakage.py` 6 passed.
- Synthetic smoke of all four scripts and `visualize_data` under `mas/state/scratch/p05/` (seeded tree from `tests/p05_synth.py`): exit 0, 55-row benchmark CSV, `flagship_S03.csv` rows m = 1, 2, the three `cm_*` figures (suffixed and roadmap path), QDA rank failure reported by `test_sklearn_models` on PSD (210) and FBCSP (50) and not on FBCCA (5).
- Known-answer tests: references, Chebyshev design and gain, FBCCA argmax on planted sinusoids, FBCCA CCA-failure path, CSP aligned with a planted spatial vector (|cos| > 0.95), CSP eigenvalues in (0, 1) and features recomputed independently (1e-9), `(n, 50)` band/class/component layout with a source planted in one band only (R6), continuous PSD 30 bins 5.859-34.180 Hz, visual cluster by name under three name orders, harmonic bins k = 9, 11, 15, 18, 20, 22, 25, 31, single mask over all blocks (PF-10), no second gate when a mask is given, suite parameters, QDA failure caught (PF-12), legacy CV and smoothing definitions, P04 re-exports.
- Historical-bug test (PF-11): `test_fold_matrices_never_see_test_rows` asserts the training matrix is unchanged by test-only content; the same test shows a CSP fitted on all rows does change it (the leaky variant fails the assertion).
- I could not and did not run real data: the 197 kept / 3 rejected counts and the R-3 accuracies are NOT checked. If the verifier finds the counts differ, the plan prescribes one investigation round on the mask (thresholds, input windows, per channel) before any R11 consultation.

## Left to do / known limitations

- R-3 reproduction is open until the verifier's run (counts exact, accuracy +-1.5 pp). The mask input is the P02 saved `X_time_windows` (already 1-60 Hz filtered); the CSP normalisation choice above is the other risk.
- `fs` default 250 is applied to the 256 Hz arrays by design (PF-04).
- `train_final_model`, `batch_run_subjects`, `run_xai` have no `--seed`.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

| # | Trigger (failed test / deviation / verification) | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| - | - | - | - | - |

## Sources

1. `mas/02_REQUIREMENTS.md` §1, §4-§7 (opened in this run).
2. `mas/03_ROADMAP.md` P05 tasks (via 00_assignment.md verbatim) and `02_plan.md` (opened in this run).
3. `mas/01_DATA_SPEC.md` §5.1, §6; `mas/04_REFERENCE_RESULTS.md` R-3; `mas/05_PITFALLS.md` PF-06/10/11/12 (opened in this run).
4. `mas/RULES.md` R1-R11 and era matrix; `mas/state/decisions.md` rows P02-P05 (opened in this run).
5. Chen X, Wang Y, Gao S, Jung T-P, Gao X. Filter bank canonical correlation analysis for implementing a high-speed SSVEP-based brain-computer interface. J Neural Eng 2015;12:046008. doi:10.1088/1741-2560/12/4/046008 (weights `b^-1.25 + 0.25`; cited from the spec, paper not opened in this run).
6. Ramoser H, Muller-Gerking J, Pfurtscheller G. Optimal spatial filtering of single trial EEG during imagined hand movement. IEEE Trans Rehabil Eng 2000;8:441-446. doi:10.1109/86.895946 (CSP form; cited from the spec, not opened in this run).
7. Ang KK et al. Filter bank common spatial pattern (FBCSP) in brain-computer interface. IJCNN 2008. doi:10.1109/IJCNN.2008.4634130 (cited from the spec, not opened in this run).
8. scikit-learn 1.9.1 `LogisticRegression` (`l1_ratio`), `SGDClassifier`, `LinearDiscriminantAnalysis`, `QuadraticDiscriminantAnalysis`; SciPy `cheby1`, `butter`, `filtfilt`, `periodogram`, `linalg.eigh`: behaviour checked by running them in this environment (`.venv`, sklearn 1.9.1, no warnings under `-W error` for the suite constructors), documentation pages not opened.

## Questions

ACK 02_plan.md ml-engineer 2026-10-24
