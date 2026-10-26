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

## P06 — Feature-selection ablation, legacy 5-subject cohort, report v1

2026-10-25, branch `phase/P06-feature-selection-cohort`, code and reported run at `7575405`, diagnostic run at `7de11ce`. Report: `mas/state/reports/P06.md`.

Added
- `src/features/selection/feature_selection.py`: `select_k_best_fbcsp_features` (ANOVA or mutual information, in-fold), `select_sfs_fbcsp_features` (forward SFS), `with_fbcca`, `band_columns`, `subband_pruned_columns`.
- `scripts/benchmarks/feature_based/benchmark_feature_selection.py` (five rows; `--sfs-diagnostics` off by default) and `benchmark_5_subjects.py` (cohort, `reports/five_subjects_benchmark.csv`).
- `tests/test_p06_feature_selection.py` and `tests/test_p06_known_answer.py`; suite `455 passed`.
- `docs/report/v1/report.md` (historical technical report v1) and `docs/report/v1/methodology_infographic_v1.svg`.

Changed
- `src/models/classical/benchmark_runner.py`: `legacy_header_lines(..., fbcca_channels=None)` names the FBCCA channels.
- `scripts/benchmarks/feature_based/benchmark_cross_validation.py`: passes the FBCCA channels to the header.
- `tests/test_no_leakage.py`: the diagnostic splitter is registered as legacy.

Result and scope
- S03 ablation, 1.0 s / 2.0 s smoothed: full 90.36 / 95.43; pruning (p 45) 87.31 / 94.92; ANOVA (p 25) 86.29 / 94.42; mutual information (p 25) 87.82 / 93.40; SFS (p 20) 89.85 / 95.94.
- Four R-4 rows and all R-5 values exact. The SFS row is not reproduced (the original has no SFS); accepted as D-1, reported as ours.
- Cohort S01–S05 at R-5 exactly; mean 83.33 / 87.57. Legacy and leaky; not comparable with R-6.

## P07 — Two-tier artifact quality gate and the 8-channel montage

2026-10-25, branch `phase/P07-two-tier-quality`. Code and run at `fa5dade`; results review at `8b6262f`. Report: `mas/state/reports/P07.md`.

Added
- `src/io/channels.py`: `FULL_MONTAGE`, `resolve_channel_names(n)` (8 full montage, 7 without PO7, else None), `legacy_scalp`, `subject_channel_names`.
- `scripts/benchmarks/feature_based/benchmark_n_subjects.py`: five-subject benchmark on the two-tier gate, `--n-jobs`, `reports/n_subjects_benchmark.csv` and `.meta.txt`.
- Tier-1 channel drop, `apply_artifact_quality_pipeline`, `compute_channel_quality_stats`, `identify_noisy_channels`, `drop_noisy_channels` in `src/preprocessing/signal/quality_check.py`.
- Tests: `tests/test_p07_quality_signal.py` (17), `tests/test_p07_ml_engineer.py` (15), `tests/test_p07_known_answer.py` (8), `tests/test_p07_round1_known_answer.py` (5); suite `503 passed`.

Changed
- `configs/pipeline_config.yaml`: config v2, 8 scalp channels in montage order, `excluded: []`.
- `src/features/ssvep/{fbcca,fbcsp,psd}_extraction.py`, `window_mask.py`, `harmonic_psd.py`, `src/models/classical/{feature_spaces,benchmark_runner}.py`: four-value extractor returns, one shared gate decision (`precomputed=`), names resolved by name, P04 positions checked against each subject's names.
- `scripts/preprocessing/run_preprocessing.py`: tier-1 detection (`--chan-*`, `--no-channel-drop`), `channels.json`, raw gate `vpp_min` pinned at 0.5 with `--vpp-min 5.0` as the labelled PF-07 demo, ungated summary, `--legacy-p02`, refusal to write into legacy 7-channel folders (`--overwrite-legacy-arrays`).
- Every feature-based and evaluation script updated to the new API; `Makefile` `preprocess` uses `--legacy-p02`.
- Six P01, P02, P03, P05 and P06 test files and `tests/p05_synth.py` follow config v2; the vacuous P06 layout test is replaced and the suite cut from 469 s to 191.73 s.

Result and scope
- Benchmark (legacy leaky CV): clean/rejected 200/0, 196/3, 197/3, 197/1, 200/0 (R-6 exact); channels kept 7, dropped none. 1.0 s / 2.0 s: 64.50 / 75.50, 66.33 / 71.94, 90.36 / 95.43, 98.98 / 98.48, 96.50 / 96.50; mean 83.33 / 87.57 (equal to R-5 to two decimals; not comparable with R-6 accuracies).
- S03 pinned run: 317 windows, equal to the legacy arrays; PO7 dropped by tier 1 (100 % fail).
- PF-07: `--vpp-min 5.0 --no-channel-drop` rejects 320 of 320 S03 windows, all by PO7 `vpp_high`; with PO7 dropped, 5.0 and 0.5 both give 317/3. Accepted deviation D-1; open question for Sebastian on the cause.
- Legacy 7-channel arrays not regenerated (SHA-256 unchanged); `make preprocess` must not run before P11.

## P08 — EEGNet on raw windows

2026-10-25 to 2026-10-26, branch `phase/P08-eegnet`. Code and run at `cf62bb3`; results review at `ef124c1`. Report: `mas/state/reports/P08.md`.

Added
- `src/models/cnn/eegnet.py`: `EEGNetSSVEP` (2,349 parameters at 7 × 256, four bias-free convolutions, head sized by a dummy forward), `apply_max_norm()` (max-norm 1.0 on the depthwise spatial filters), `count_parameters()`.
- `src/models/cnn/eegnet_cv.py`: `zscore_windows` (per window and channel), `train_model` (AdamW, cosine schedule, label smoothing 0.05, `seed + fold`, max-norm after each step), `train_and_eval_eegnet_cv` (legacy leaky CV, train accuracy on the training fold).
- `scripts/benchmarks/neural_networks/benchmark_eegnet.py`: CLI (`--subject`, `--device {auto,cpu,cuda}`, `--augment off`, `--epochs`, `--seed`), P07 gate, `reports/eegnet_benchmark_<device>.csv` and `.meta.txt`.
- `tests/test_p08_eegnet.py` (15 cases) and `tests/test_p08_eegnet_known_answer.py` (10 tests); suite `528 passed, 21 warnings`.

Result and scope
- S03, legacy leaky CV, `reports/eegnet_benchmark_cpu.csv`: 1.0 s 75.63 % (149 / 197), 2.0 s smoothed 85.79 % (169 / 197), train 98.34 %.
- S03, `reports/eegnet_benchmark_cuda.csv`: 1.0 s 71.07 % (140 / 197), 2.0 s smoothed 81.22 % (160 / 197), train 98.60 %.
- Each device identical over two runs; CPU–CUDA gap 9 windows, reported per device, not averaged.
- Legacy throughout (R1, R8, R5 legacy, fs 250 label). Not comparable with R-6; the classical flagship comparison is a labelled diagnostic only.

## P09 — Compact-CNN and ShallowConvNet

2026-10-26, branch `phase/P09-compact-shallow-cnn`. Code and reported runs at `edd476e`; results review at `f20ea80`. Phase report: `mas/state/reports/P09.md` (on main with the P09 merge, `8430cb9`).

Added
- `src/models/cnn/compact_cnn.py`: `CompactCNN` (spatial conv, temporal conv with K = clamp(round(fs / 8.5714), 4, n_samples), legacy fs 250 default, K = 29; 56,021 parameters).
- `src/models/cnn/shallow_conv_net.py`: `ShallowConvNet` (temporal and spatial convs, square, average pool, log with clamp 1e-6; 14,485 parameters).
- `src/models/cnn/benchmark_common.py`: shared benchmark driver (gate, legacy folds, training, CSV and `.meta.txt`).
- `scripts/benchmarks/neural_networks/benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py`, `count_parameters.py` (counts at 7 × 256, exit 1 on an R-8 mismatch; writes `reports/network_parameter_counts.csv`).
- `tests/test_p09_compact_shallow.py` (25) and `tests/test_p09_known_answer.py` (20); suite `573 passed, 21 warnings`.

Changed
- `src/models/cnn/eegnet_cv.py`: network-agnostic training; the EEGNet path is unchanged (synthetic hash pin).
- `scripts/benchmarks/neural_networks/benchmark_eegnet.py`: thin wrapper over the shared driver; `.meta.txt` now has the data-source line and `n_channels` (P08 carry-forward).

Result and scope
- S03, legacy leaky CV, CPU, `reports/compact_cnn_benchmark_cpu.csv`: 1.0 s 54.31 % (107 / 197), 2.0 s smoothed 62.94 % (124 / 197), train 100.00 %.
- S03, legacy leaky CV, CPU, `reports/shallow_convnet_benchmark_cpu.csv`: 1.0 s 86.80 % (171 / 197), 2.0 s smoothed 92.89 % (183 / 197), train 100.00 %.
- Parameter counts equal R-8 (2,349 / 14,485 / 56,021), `reports/network_parameter_counts.csv`.
- Each network identical over two runs. Legacy throughout (R1, R8, R5 legacy, fs 250 label for Compact-CNN). Not comparable with R-6; the ordering on S03 is not a cohort ranking.

## P10 — Data augmentation and the A/B protocol

2026-10-26, branch `phase/P10-augmentation-ab`. Code, tests and runs at `5f2d5eb`; results review at `2080b68`. Phase report: `mas/state/reports/P10.md` (to be filed by the orchestrator from the scribe's hand-back).

Added
- `src/preprocessing/dataset/augmentation.py`: noise, scale, shift and same-class mixup; `SSVEPAugmentedDataset` (training fold only, order mixup, scale, shift, noise; p = 0.5 each).
- `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py`: OFF then ON per subject, `--freeze-legacy` writes `reports/legacy_leaky/augmentation_ab_<model>.csv`.
- `tests/test_p10_augmentation.py` (15) and `tests/test_p10_augmentation_known_answer.py` (16); suite `604 passed, 21 warnings` (`reports/logs/P10/pytest_20261026_011732.log`).

Changed
- `src/models/cnn/eegnet_cv.py` and `src/models/cnn/benchmark_common.py`: `--augment {off,on}` (default off); the OFF path is unchanged (P09 hash pins pass).
- The three `benchmark_*.py` wrappers (docstrings only); two P08/P09 tests now check an invalid `--augment` value.

Result and scope (legacy leaky CV, CPU, `reports/augmentation_ab_<model>.csv`; not comparable with R-6)
- EEGNet cohort 1.0 s 63.93 → 67.04 % (Δ +3.11 pp, inside R-9a's recorded [+3.00, +7.34] at its lower edge); 2.0 s 68.18 → 71.08 % (Δ +2.90 pp). Four of five subjects improved; S02 −3 windows.
- EEGNet S03 OFF 75.63 / 85.79 % equals P08 (regression check). S01 and S02 OFF test 28.00 / 27.04 % with train 83.25 / 81.38 % (PF-30 generalization failure reproduced).
- Compact-CNN Δ +14.12 / +11.39 pp and ShallowConvNet Δ +2.01 / +2.72 pp, diagnostics only.
- Frozen CSVs byte-identical to the main outputs. Next phase: P11.
