# Changelog

All notable changes, one section per phase (filled by the scribe).

## P00 — Bootstrap and data intake

2026-10-24, branch `phase/P00-bootstrap`. Report: `mas/state/reports/P00.md`.

Added
- Specification and MAS tooling (`AGENTS.md`, `mas/`), `README.md`.
- Repository skeleton: `src/**/__init__.py`, `scripts/**/__init__.py`, `tests/__init__.py`.
- `requirements.txt`, `environment.yml`, `Makefile` (targets `help`, `venv`, `test`, `inventory`), `pytest.ini`.
- `scripts/exploration/inventory_raw.py`: header and MARK inventory of the raw recordings, writes `reports/raw_inventory.csv`, exit 1 on any deviation.
- `tests/test_p00_inventory_smoke.py` (2 tests) and `tests/test_p00_inventory_known_answer.py` (61 tests); suite `63 passed`.

Changed
- `.gitignore`: `SSVEPs_OO_mOO/` named explicitly; `/outputs/`, `/reports/`, `/baselines/` anchored at the repository root so `mas/state/reports/` is tracked.
- `scripts/exploration/inventory_raw.py`: subject folders matched with `fullmatch`.

Result and scope
- Inventory run: exit 0, `10 files, 5 subjects, 0 deviations`; all 10 delivered rows match `mas/01_DATA_SPEC.md` §4.
- Only 10 of the 23 §4 rows were delivered (`OO`, `mOO` of S01–S05). Absent: S01 `C`, `mC`; S02 `C`, `mC`, `online_C`; S03 `C`, `mC`, `cb_mas_mcb`; S04 `C`, `mC`; S05 `C`, `mC`, `online_OO`. Deviation recorded in `mas/state/decisions.md` and blocker B005, signed by the scientific reviewer.

## P01 — EBR parser and configuration v1

2026-10-24, branch `phase/P01-ebr-parser`. Report: `mas/state/reports/P01.md`.

Added
- `src/io/ebr_parser.py`: `load_ebr_file(path, strict=True)`, `resolve_recording_path`, `select_scalp_channels`, `get_mark_channel_index`, `extract_scalp_signal`.
- `configs/pipeline_config.yaml` v1 (PO7 hard-excluded, labelled legacy).
- `src/preprocessing/signal/filters.py`: `apply_iir_bandpass(data, fs, lowcut=1.0, highcut=60.0, order=4)`.
- `tests/test_p01_*.py` (smoke, parser, config, filters, strict); suite `248 passed`.

Changed
- `scripts/exploration/inventory_raw.py`: reads through the parser; new `--strict` flag (default off); `--raw-dir` default from the config.

Result and scope
- Default and `--strict` inventories: exit 0, `10 files, 5 subjects, 0 deviations`, both byte-identical to the P00 CSV (sha256 `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14`).
- Applies to the 10 of 23 §4 rows delivered (blocker B005). Seven accepted deviations are in `mas/state/decisions.md`.

## P02 — Legacy preprocessing and windowing

2026-10-24, branch `phase/P02-legacy-windowing`. Report: `mas/state/reports/P02.md`.

Added
- `src/preprocessing/signal/quality_check.py`: `validate_eeg_windows`, `filter_dataset`, `summarize_window_quality`, `window_quality_flags`, `segment_and_validate_eeg`, `quality_stats` helpers.
- `src/features/ssvep/psd_extraction.py`: `extract_clean_subwindows_psd`, `process_condition_windows_with_baseline`, `prepare_feature_matrix`.
- `src/visualization/signal_plots.py`: `plot_eeg_window`, `plot_average_psd_by_condition`, `plot_stimulus_vs_baseline_psd`.
- `scripts/preprocessing/run_preprocessing.py` (`--subject`, `--all`, `--vpp-min`, `--raw-dir`, `--processed-dir`, `--figures-dir`) and `make preprocess`.
- `tests/test_p02_signal_smoke.py`, `tests/test_p02_preprocessing_smoke.py`, `tests/test_p02_windowing_known_answer.py`; suite `283 passed`.

Changed
- `Makefile`: target `preprocess`.
- `mas/state/team.yaml`: P02 legacy flags set to `[]` (header fs 256 Hz is used for windows and PSD).

Result and scope
- Run: exit 0, 5 s; `Cohort: 5 subjects processed, 0 skipped (none); 1592 windows; gated 1600, accepted 1592, rejected 8, skipped segments 0`. Window counts equal R-1 exactly (320 / 318 / 317 / 317 / 320; stimulus 200 / 199 / 200 / 198 / 200).
- Figure criterion: S04 and S05 5/5, S03 4/5 (8.57 Hz partial).
- On real data 178 of 199 legacy 202 windows are bit-identical to a 201 window and 21 are shifted by 8 samples; 201 and 202 are never to be used together.

## P03 — Exploration and signal verification

2026-10-24, branch `phase/P03-exploration`. Report: `mas/state/reports/P03.md`.

Added
- `scripts/exploration/diagnose_occipital_spectra.py` (`--subject`, `--subjects`, `--all`, `--fs`, `--out-suffix`, `--processed-dir`, `--figures-dir`, `--config`, `--no-figures`): occipital `O1, Oz, O2` (by name) spectra per class, response-bin power and specificity ratio.
- `scripts/exploration/visualize_data.py`: legacy quality mask with explicit thresholds, per-class PSD plots, check of the recomputed PSD against the saved one; marked extension points for FBCCA/FBCSP (P05).
- `src/features/ssvep/spectral_power.py` (`response_bin`, `spectrum_peaks`, `fft_power`, `psd_features`, `select_channels_by_name`); `LEGACY_FS_HZ = 250`.
- `tests/test_p03_exploration_smoke.py` (10) and `tests/test_p03_exploration_known_answer.py` (18); suite `311 passed`.

Changed
- `src/visualization/signal_plots.py`: + `plot_class_spectra_panels`, `plot_psd_by_class_per_channel`.
- `Makefile`: target `explore`.

Result and scope
- Four runs, 3 to 5 s each; the verifier re-ran them with exit 0. Mask `rejected 0` (kept 1592, consistency check); `max |computed - saved| = 0` at fs 256; legacy fs 250 relabels the axis only (25 of 25 rows).
- Clear fundamentals: S03 5/5, S04 5/5, S05 5/5 (104 and 105 via the second harmonic); S01 only a weak 10.91 Hz response; S02 none.
- The pre-run audit Round 1 failed on the nearest-labelled target bin at the legacy axis (wrong for 24, 2·15, 2·8.57 Hz); fixed with response bins and a specificity ratio.

## P04 — Early hybrid models, fusion CNN and first explainability

2026-10-24, branch `phase/P04-early-models-xai`, code at `552029a`. Report: `mas/state/reports/P04.md`.

Added
- `scripts/training/train_models.py` (`--subject`, `--all`): harmonic-PSD and FBCCA hybrid (37 features), six classifiers under the legacy CV, legacy no-reset smoothing, confusion matrices, per-subject CSV.
- `scripts/training/train_final_model.py` (`--subject`, `--device`, `--epochs`, `--skip-cnn`): full-data Shrinkage-LDA and fusion-CNN exports, labelled as export and XAI only.
- `scripts/training/batch_run_subjects.py` (`--subjects`, `--paradigm`, `--device`): per-subject LDA and fusion-CNN summary CSV.
- `scripts/xai/run_xai.py`, `scripts/xai/compare_subject_xai.py`: LDA-weight heatmaps and the S01 versus S04 comparison.
- `src/models/cnn/spatial_spectral_cnn.py`: `DualBranchFusionCNN` (10,005 parameters, convolutions without bias), tensor builder, CNN cross-validation, legacy smoothing.
- `tests/test_p04_early_models_known_answer.py` (32 tests with mutant checks), `tests/test_p04_cnn_smoke.py`, `tests/test_p04_ml_smoke.py` (4); suite `349 passed`.

Changed
- `mas/state/team.yaml`: P04 legacy flags gain R3 (per-window FBCCA filtering).

Result and scope
- Seven runs on CPU at 140 epochs, all exit 0, 9.07 min in total.
- Every accuracy is legacy leaky CV (R1, PF-01) with no-reset smoothing (R8, PF-02); not comparable with R-6. Trial-grouped CV and trial-reset smoothing come in P11; the FBCCA sampling rate and filtering come in P16.
- Shrinkage-LDA 1.0 s: 50.00, 51.26, 83.00, 97.98, 95.50 % for S01–S05; fusion CNN 1.0 s: 51.50, 53.77, 89.00, 99.49, 100.00 %.

## P05 — Feature extractors and feature-space / model benchmark

2026-10-24 (Round 1) and 2026-10-25 (Round 2), branch `phase/P05-feature-benchmark`, code at `edcc177`. Report: `mas/state/reports/P05.md`.

Added
- `src/features/ssvep/fbcca_extraction.py`, `fbcsp_extraction.py`, `window_mask.py`, `harmonic_psd.py`: FBCCA, FBCSP (in-fold `FBCSPTransformer`; full-data `extract_fbcsp_features` for visualization only) and the explicit window mask.
- `src/models/classical/` (`sklearn_models.py` ten-model suite; `legacy_eval.py`, `feature_spaces.py`, `benchmark_runner.py`); `src/preprocessing/dataset/smoothing.py`, `legacy_windows.py`.
- `scripts/benchmarks/feature_based/benchmark_cross_validation.py`, `benchmark_harmonic_fbcca.py`; `scripts/evaluation/test_sklearn_models.py`, `evaluate_confusion_matrix.py` (`--subject`, `--m`, `--seed`, `--fs`, `--no-figures`).
- Tests: `tests/test_p05_known_answer.py` (30), `tests/test_p05_feature_benchmark.py` (31), `tests/test_p05_round2_known_answer.py` (10), `tests/test_no_leakage.py` (6); suite `426 passed`.

Changed
- `src/features/ssvep/psd_extraction.py`: continuous PSD `(n, 210)` with `valid_mask` and `thresholds`.
- `scripts/training/train_models.py`: P04 helpers moved to `src/` and re-exported; `--seed` added.
- `scripts/exploration/visualize_data.py`: FBCCA and FBCSP blocks.
- `mas/RULES.md`: R8 era row corrected (P04 no-reset; P05–P10 `i % 5` on the clean array).

Result and scope
- Ten benchmark and evaluation commands per round, all exit 0; 74 s (Round 1) and 53 s (Round 2).
- S03 flagship: 197 / 3; 1.0 s 90.36 %; 2.0 s 95.43 % (`i % 5`, reported); no-reset 95.94 % (diagnostic only).
- S01–S05 flagship, 1.0 s / 2.0 s: 64.50 / 75.50, 66.33 / 71.94, 90.36 / 95.43, 98.98 / 98.48, 96.50 / 96.50.
- Legacy (window-level CV, `i % 5` after rejections, fs 250, per-window filtering); not comparable with R-6. The 24 Hz precision is 0.9750 (deviation D-1, accepted).
