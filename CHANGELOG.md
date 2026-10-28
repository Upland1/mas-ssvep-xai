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

2026-10-26, branch `phase/P10-augmentation-ab`. Code, tests and runs at `5f2d5eb`; results review at `2080b68`. Phase report: `mas/state/reports/P10.md` (on main with the P10 merge, `829602c`).

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

## P11 — Discover and fix trial leakage

2026-10-26, branch `phase/P11-trial-leakage-fix`. Code and runs at `aedf8a8`; Round 2b diagnostic at `0b96524`; results review at `50d9d01`. Phase report: `mas/state/reports/P11.md`.

Added
- `src/preprocessing/dataset/cv_utils.py`: `build_trial_ids` (pre-gate labels, then the valid mask), `make_splits` (`grouped` / `legacy`), `assert_no_shared_trials`.
- `scripts/diagnostics/demo_cv_leakage.py` (before/after table, classical and network) and `scripts/diagnostics/network_seed_spread.py` (DIAGNOSTIC; outputs only under `reports/diagnostics/`).
- `tests/test_p11_cv.py`, `tests/test_p11_known_answer.py`, `tests/test_p11_networks.py`, `tests/test_p11_seed_spread.py`; suite `678 passed` (`reports/logs/P11/pytest_20261026_110219.log`) and `687 passed` at `0b96524` (`reports/logs/P11/pytest_2b_20261026_124231.log`).

Changed
- All nine benchmark scripts: `--cv {grouped,legacy}` (default grouped) and `--smoothing {trial,mod5}` (default mod5 on legacy folders); `--cv legacy` writes under `reports/legacy_leaky/` and reproduces R-5, R-4 and R-3.
- `src/models/classical/legacy_eval.py`, `benchmark_runner.py`, `smoothing.py`, `src/models/cnn/eegnet_cv.py` (the seed-spread argument `model_seed` defaults to the reported path); the saga LogReg models are seeded.
- Legacy-pinned tests (P05–P10) now name their protocol explicitly.

Result (legacy folders, 7 channels, CPU, seed 42; not comparable with later phases)
- Flagship R-6 reproduced exactly: 79.28 % (1.0 s) and 82.61 % (2.0 s, legacy `i % 5`; `reports/n_subjects_benchmark.csv`). Trial-reset 2.0 s diagnostic 81.39 % (`reports/cv_leakage_demo.csv`).
- Classical leak −4.06 pp (1.0 s) and −4.96 pp (2.0 s) on the mean; S02 −10.21 pp (approximate ids, residual leak possible until P16).
- Networks, seed 42 versus the frozen P10 run (`reports/cv_leakage_demo_networks.csv`): EEGNet OFF −5.57 pp, Compact-CNN OFF −5.56 pp, ShallowConvNet OFF −3.04 pp at 1.0 s. The EEGNet S03 training-seed range (16.75 pp, DIAGNOSTIC) is of the same order as its seed-42 drop (−20.81 pp).
- Augmentation A/B vs R-9b: 13 of 14 out-of-band cells explained by training-seed variance (D-4). Compact-CNN S03 2.0 s ON not reproduced within tolerance (129 / 127 / 129 of 197 windows; smallest in-band count 131), accepted as a documented deviation by Sebastian (D-8, B006).
- Reference consultation: one, under R11 (deep-learning, Round 2; no code copied; RNG stream not adopted).
- Frozen P10 CSVs (`reports/legacy_leaky/`) are the "before" side. Next phase: P12, after the orchestrator's gate.

## P12 — Functional connectivity v1: coherence, bias fix, matched baseline

2026-10-26, branch `phase/P12-coherence`. Code and runs at `cb446b0`; results review at `66f3346`. Phase report: `mas/state/reports/P12.md`.

Added
- `src/features/connectivity/connectivity_extraction.py`: coherence estimators (per-window DIAGNOSTIC; concatenated, reported), the same-window matched baseline, difference matrices, the 5–35 Hz baseline statistic and the window-aligned junction diagnostic.
- `src/visualization/connectivity_plots.py`: circle plots, raw and difference panels (`RdBu_r`, symmetric per subject).
- `scripts/connectivity/diagnostics/demo_coherence_bias.py` (PF-15 and PF-16, synthetic and real) and `scripts/connectivity/analysis/analyze_connectivity.py --subject --method coherence`.
- `tests/test_p12_coherence.py` and `tests/test_p12_known_answer.py`; suite `723 passed, 21 warnings` (`reports/logs/P12/pytest_20261026_151109.log`).

Result (S03 and S04, legacy 7-channel folders, raw windows, descriptive; `reports/connectivity/`)
- PF-15 reproduced: independent noise 0.3373 per-window averaged against 0.0180 concatenated (`reports/connectivity/coherence_bias_demo.csv`). Fixed on the reported path.
- Baseline coherence (201, 5–35 Hz, R-11): S03 0.6836 → 0.5871, S04 0.7291 → 0.6589 (before → after). Per-band matched baseline falls in 10 of 10 cells.
- Differences, prescribed estimator: 24/20 Hz positive in both subjects (S03 +0.2494 / +0.2511; S04 +0.1281 / +0.1105). 10.91/8.57 Hz: S03 −0.0366 / +0.0414; S04 +0.1934 / +0.1286.
- PF-16 changes conclusions: S03 105 +0.1934 broadband against +0.0414 matched; S04 103 sign flip (−0.0048 against +0.0554).
- Junction diagnostic: S03 105 estimator-sensitive (|Δ| = 0.0565, sign opposite to the junction prediction); no other band flagged.
- Alpha-band ceiling and alpha-desynchronisation hypotheses recorded for P13; no p-values in P12.

Review
- Pre-run audit Round 1 FAIL (`84406bc`), amended settled point 2, Round 2 PASS (`35a1f29`). Verifier PASS (`b68f5eb`). Results review APPROVE (`66f3346`), D-1 to D-4. No reference consultation.
- Suite runtime about 6 min against "about a minute" (noted, not blocking).

Next phase: P13, after the orchestrator's gate.

## P13 — Phase and autoregressive connectivity with permutation statistics

2026-10-26, branch `phase/P13-phase-pdc-permutations`. Code and main run at `7f6cabb`; DIAG-A2 verifier `3865ba6`; results review at `a010a0d`. Phase report: `mas/state/reports/P13.md`.

Added
- `src/features/connectivity/phase_connectivity.py` (PLV and wPLI from the band-averaged CSD), `mvar_pdc.py` (strided MVAR coefficients, PDC over 42 directed edges), `permutation.py` (trial-level permutations with observed group sizes; BH over one-tailed edge p; `p_lower_tailed`).
- `scripts/connectivity/analysis/analyze_connectivity_cohort.py`: all subjects and methods, window-level and trial-level runs, `--compare`, aligned coherence diagnostic (DIAGNOSTIC).
- `scripts/connectivity/diagnostics/demo_hilbert_edges.py` (PF-18) and `demo_mvar_slicing.py` (PF-17).
- `tests/test_p13_connectivity.py` (27) and `tests/test_p13_known_answer.py` (37); suite `796 passed, 21 warnings` (`reports/logs/P13/pytest_full.log`).

Changed
- `src/features/connectivity/connectivity_extraction.py`: the shared P07 gate per subject, with trial ids built on pre-gate labels (PF-03).

Result (S01–S05, legacy 7-channel windows, raw; `reports/connectivity_cohort_summary.csv`; R-12 reference)
- FDR totals (coherence / wPLI, S01–S05): 0 / 0 / 64 / 49 / 12 and 4 / 0 / 42 / 28 / 5 (R-12: 0 / 0 / 65 / 51 / 15 and 0 / 3 / 38 / 33 / 18). Nine of ten cells inside their windows.
- The S05 wPLI total of 5 (window 13–23) is an accepted deviation (D-1): DIAG-A2 bases 1–5 give 7 / 14 / 12 / 7 / 12 (`reports/connectivity_cohort_summary_diagA2_rs<B>.csv`, DIAGNOSTIC). The reported value stays 5. Not reproduced by R-12.
- 24 Hz significant in S03–S05 for coherence and wPLI; S01 and S02 null at 24 Hz for coherence and wPLI. S05 wPLI 20 Hz inconclusive.
- S03 coherence 8.57 Hz estimator-dependent (8 FDR edges concatenated, 0 aligned); inconclusive.
- Window-level p ≤ trial-level p in 71 of 100 cells; 11 flip-list cells inconclusive (BH resolution), 14 cells change verdict between the two units.
- Alpha hypotheses from P12 tested: ceiling consistent for S03 coherence only; S03 suppression not supported; S05 exploratory lower-tail pattern carried to P14.

Review
- Pre-run audit Round 1 FAIL (`934cc2f`), fixes, Round 2 PASS. Main run verifier FAIL on A2 (`57e5fbd`); results review Round 1 REJECT (`cec7dca`); DIAG-A2 PASS (`3865ba6`); results review Round 2 APPROVE (`a010a0d`).
- Suite runtime about 6 min against "about a minute" (noted, not blocking). No reference consultation.

Next phase: P14, after the orchestrator's gate.

## P14 — Cross-frequency comparison, reliability, and power/alpha confounds

2026-10-26, branch `phase/P14-cross-frequency-confounds`. Pipeline at `6b4ec21`; restatement at `8356a04` (PASS); results review at `878e96e`. Phase report: `mas/state/reports/P14.md`.

Added
- `scripts/connectivity/comparison/compare_connectivity_frequencies.py` (similarity, node strength, global delta, groups; QAP p).
- `scripts/connectivity/comparison/test_connectivity_frequency_differences.py` (split-half reliability; pairwise trial-level tests at 500 and 1000 permutations; `--compare`).
- `scripts/connectivity/diagnostics/check_power_alpha_confound.py` (target SNR, alpha change, OLS R², in-alpha versus out-of-alpha).
- `src/features/connectivity/comparison.py`; `tests/test_p14_connectivity_comparison.py` and `tests/test_p14_known_answer.py`; suite `873 passed, 1 skipped, 21 warnings in 405.69s` (`reports/logs/P14/pytest_full_round2.log`).
- Outputs: `reports/connectivity_comparison/` (61 CSVs), `outputs/figures/connectivity_comparison/` (21 PNG).

Changed
- Tests only, after the first run failed: two P14 tests now pass explicit responders instead of reading the git-ignored `reports/n_subjects_benchmark.csv` (`b4806cc`, `32a649f`).

Result (S01–S05, legacy 7-channel windows, descriptive; R-13 qualitative)
- Frequency similarity (Fisher mean r): coherence 0.629, PLV 0.510, wPLI 0.163, PDC 0.480 (R-13 coherence 0.54, wPLI 0.14). Coherence exceeds wPLI on both the mean and the share of p_qap < .05 (0.66 and 0.32).
- Split-half reliability medians: coherence 0.924, wPLI 0.517 (R-13 0.92 and 0.54).
- Target SNR and alpha change tables equal R-13 to two decimals.
- R² of delta on SNR and alpha, all cells 0.675 and within-subject 0.540 for coherence (largely explained, SNR-dominated); PLV and PDC partly explained, SNR-dominated; wPLI explained between subjects only (0.0014 within-subject). Alpha adds little everywhere (ΔR² ≤ 0.059).
- No consistent in-alpha difference for coherence, PLV or wPLI; PDC differs raw but is consistent with its lower SNR.
- Pairwise exchangeability null is off-centre on real data (13 cells labelled "null off-centre"; 8 of 150 flips inconclusive).
- S05 alpha-blocking pattern carried as an exploratory hypothesis, with its lower-SNR alternative and the 20 Hz counter-example.
- Unexplained R-13 differences reported, not graded: coherence similarity 0.629 against 0.54; coherence magnitude count 11 against 6; two non-positive coherence reliabilities against none.

Review
- Pre-run audit Round 1 FAIL (`34301f7`), Round 2 PASS (`82255b7`). First verifier run FAIL (`b2478a9`, test hygiene), restatement PASS (`8356a04`); results review APPROVE (`878e96e`), D-1 to D-5.
- Pipeline runtime 67.55 min against an 18–34 min estimate; suite about 6.7 min against "about a minute". No reference consultation.

Next phase: P15, after the orchestrator's gate.

## P15 — Per-window graphs, the connectivity gate, and a GNN

2026-10-27, branch `phase/P15-graph-gnn`. Code at `2392299`; first verifier run `87ed7af` (FAIL); results review at `5bd9240` (APPROVE); verifier restatement at `6e55897` (PASS). Phase report: `mas/state/reports/P15.md`.

Added
- `src/features/connectivity/connectivity_graph_features.py` (node band power, edge coherence and edge phase, flattening), `graph_dataset.py` (cached dataset loader), `graph_inputs.py` (input variants and the train-fold standardizer).
- `src/models/graph/connectivity_gnn.py`: `ConnectivityGNN` with edge-gated layers.
- `scripts/connectivity/graph_modeling/build_graph_dataset.py` (cache and sanity report), `benchmark_connectivity_gate.py` (R-14 gate), `benchmark_gnn.py` (R-15 benchmark with a smoke test).
- `tests/test_p15_gnn.py`, `tests/test_p15_graph_features.py`, `tests/test_p15_known_answer.py`; suite `948 passed, 21 warnings` (`reports/logs/P15/pytest_full.log`).

Result (S01–S05, legacy 7-channel windows, descriptive; `reports/connectivity_gate_benchmark.csv`, `reports/gnn_benchmark.csv`)
- Gate, R-14 reproduced: 45 cells within 0.05 pp and nine cohort means within 0.06 pp; Base+Ec best at 77.57. The gate does not pass: 0 of 3 responders gain ≥ 2 pp.
- GNN, R-15: within tolerance for 11 of 12 graded subject cells, and for the 1.0 s cohort cells. Not reproduced within tolerance, accepted as a documented deviation (B007), cause not established: nodes+F S02 at 2.0 s (37.07 against 46.1), the nodes+F cohort 2.0 s it drives (71.27 against 74.43), and the coherence-edge cohort sign (+1.07 against −0.40).
- The "nodes+F ≈ nodes+coh+F" and "coherence edges do not help" claims hold. The GNN is below the LDA gate rows on every subject at 1.0 s.
- Train accuracy above R-15 on six of six graded cells (diagnostic; cause open).

Review
- Pre-run audit Round 1 FAIL (`2bc973a`, documentation only), Round 2 PASS (`1d1bdca`). Blocker B007 resolved by Sebastian, option 1 (`79870ad`). Results review APPROVE (`5bd9240`), D-1 to D-6.
- R11: deep-learning consultation (whole original file displayed; only `bias=False` adopted) and the reviewer's verification consultation; both listed in the report.
- Suite runtime about 7.2 min against "about a minute" (noted, not blocking).

Next phase: P16, after the orchestrator's gate.

## P16 — Baseline freeze, edge effects, continuous filtering, 256 Hz, shared quality

2026-10-27 to 2026-10-28, branch `phase/P16-continuous-filtering`. Run state `bb8c999`; re-verified at `215bf44`; results review `928ae8c` (APPROVE). Phase report: `mas/state/reports/P16.md`.

Added
- `scripts/freeze_baseline.py`: read-only snapshot `baselines/v1_<date>/` with MANIFEST, `baseline_summary.csv` and `superseded/`; refuses a repeated tag.
- `src/preprocessing/windowing.py`: window index (`stride=None` reproduces the legacy starts), `band_windows` in `continuous` and `per_window` modes, filter banks.
- `src/preprocessing/window_quality.py`: `subject_quality_gate` (channel and window tiers, artifact guard by ringing time, every threshold explicit).
- `src/io/subject_data.py`: `load_subject` (fs from metadata, true or reconstructed trial ids, saved bands, one quality decision).
- `scripts/build_windows.py`: builds `data/processed_<mode>/<S>/`; `--check-legacy-starts`.
- `scripts/diagnostics/demo_edge_effects.py` and `reports/edge_effects_summary.csv`.
- `scripts/diagnostics/compare_v1_v2.py`: joins the CSVs into `reports/v1_vs_v2/`; `--check-regression`.
- Tests: `tests/p16_synth.py`, `tests/test_p16_*.py` (nine builder files and one independent known-answer file with 59 cases).

Changed
- `configs/pipeline_config.yaml`: final version (1–90 Hz broadband, notch 60 Hz, `quality:`, `filter_bank:`).
- `scripts/benchmarks/feature_based/benchmark_n_subjects.py`: port to `load_subject`; `--data-root`, `--quality`, `--fs`, `--smoothing`, `--cv-repeats`.
- `src/features/ssvep/fbcca_extraction.py`, `fbcsp_extraction.py`: `subband_windows=` and `quality=`.
- `src/models/classical/legacy_eval.py`: `oof_space` requires explicit splits (P11 N1).
- `src/features/connectivity/connectivity_extraction.py`: loader `load_condition_windows` through `load_subject` with the connectivity gate passed explicitly.
- Connectivity scripts (`analyze_connectivity_cohort.py`, `analyze_connectivity.py`, comparison and confound scripts): ported to the loader; `--out-suffix`, `--fs`, `--data-root`, `--quality`.
- `scripts/preprocessing/run_preprocessing.py`: pins the legacy highcut at 60 Hz.
- `src/preprocessing/signal/filters.py`: `apply_notch`, `broadband_filter`.
- `src/features/ssvep/window_mask.py`: `loader_decision`.
- Follow-on updates in `tests/test_p01_config_known_answer.py`, `test_p05_feature_benchmark.py`, `test_p14_known_answer.py`, and `benchmark_5_subjects.py`, `test_sklearn_models.py`.

Result (S01–S05, OO session; `reports/n_subjects_benchmark_<suffix>.csv`, `reports/v1_vs_v2/flagship.csv`)
- Regression: the v1 flagship row at seed 42 equals R-6 per subject (mean 79.28 / 82.61); `_v1check` byte-equal to the frozen v1; connectivity cohort summary byte-equal; 20/20 npz equal. The first run failed on NaN diagonals (a checker defect, fixed in `9b297c0`, data identical throughout).
- Edge effects, S03: ratios 8.17 / 7.45 / 21.00 for 7–12 / 13–17 / 18–26 Hz, edge errors ≥ 20 %. Criterion met; the ≥ 10 reading is not met for 7–12 and 13–17 Hz.
- Legacy starts equal on all 70 lines. Trial-id groups inconsistent on S02 (39 of 199) and S04 (38 of 198) as in P11 D-2.
- Flagship cohort mean, 1.0 s / 2.0 s: v1 79.28 / 82.61; a 80.80 / 84.42; a′ 88.84 / 91.33; c (headline v2) 87.38 / 89.07; c′ 88.38 / 89.83. The fs correction (+8.04 / +6.91 pp) explains the v1 → v2 gain; the filter mode is nil, the build is material only on S02, the guard is material only on S02 at 1.0 s.
- No claim that continuous filtering or the guard improves accuracy. R-6 remains the P11 target; v2 has no numeric target (R-16).

Review
- Pre-run audit Round 1 FAIL (`58c578c`), Round 2 PASS (`fe71ffa`, `645312e`). Verifier FAIL (`bd55527`), PASS after Round 2 (`6bb9b81`). Results review APPROVE (`928ae8c`), D-1 to D-8, C-1 to C-5.

Next phase: P17, after the orchestrator's gate.

## P17 — Sixth (rest) class and harmonic / intermediate filter bank

2026-10-28. Branch `phase/P17-rest-class-filterbank`. Run state `59b0f10`; verifier PASS `d7daf81`; results review APPROVE `1eeff88`. Phase report: `mas/state/reports/P17.md`.

Added
- `src/preprocessing/windowing.py`: `harmonic_centers`, `intermediate_centers`, `narrow_filter_bank` (skip rule, `bands_skipped`), `band_overlaps`, `build_bank`; banks `harmonic` and `intermediate`.
- `src/models/classical/rest_metrics.py`: BalAcc, FalseAct, Missed and StimCorrect, and the confusion counts.
- `scripts/build_windows.py`: banks `harmonic` and `intermediate`; meta `bands_skipped`, `band_overlaps`, `data_source`, `legacy`.
- `scripts/benchmarks/feature_based/benchmark_n_subjects.py`: `--bank {base,harm,harm+mid}`, `--classes {5,6}`, `--allow-fs-override`; 6-class columns and SDs; `<csv>_confusion.csv`.
- Tests: `tests/test_p17_windowing.py` (10), `tests/test_p17_benchmark.py` (21), `tests/test_p17_independent_known_answer.py` (22), `tests/test_p17_leak_controls.py` (12).
- Generated (ignored): `data/processed_continuous_p17/`; six `reports/n_subjects_benchmark_p17_*` pairs, three `_6class_confusion.csv`, the D0 CSV; `reports/logs/P17/`.

Changed
- `scripts/freeze_baseline.py`: no `Mean` subject row for new tags (C-1); `v1` unchanged.
- `scripts/build_windows.py`: default `--banks` is the four config-enabled banks; per_window builds labelled legacy (C-2).
- `benchmark_n_subjects.py`: no `GATE_THRESHOLDS` fallback; `--fs` on a built root raises unless `--allow-fs-override` (C-2).
- `tests/test_p16_freeze_baseline.py`, `tests/test_p16_independent_known_answer.py`: follow-on updates (keyword, explicit `thresholds=`).
- Not changed: `configs/` (the `filter_bank:` block exists from P16); the P16 root `data/processed_continuous/` (hash `c59c94b8…a54e`, 65 files, unchanged).

Result (S01–S05, 10 repeats; `reports/n_subjects_benchmark_p17_*.csv`)
- 5 classes, cohort mean 1.0 s / 2.0 s: base 87.65 / 89.57; harm 94.29 / 95.80; harm+mid 94.23 / 95.45.
- Guard 0.902 s → 1.047 s changes only S04 (one rest and one cue window; valid 309 → 307).
- Six classes: StimCorrect(6) < Smoothed(5) in 15 of 15 cells; rest errors fall with the narrow banks on S01 and S02.
- Leak controls and G1–G4 met; no leak trigger. The gain is accepted as consistent with an SNR gain of the narrow bands at k·f, fundamentals included.

Review
- Pre-run audit PASS (`25dca39`); results review APPROVE (`1eeff88`), D-1 to D-6, C-a to C-e.

Next phase: after the orchestrator's gate.
