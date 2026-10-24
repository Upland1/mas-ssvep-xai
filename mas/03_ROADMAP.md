# 03 — Roadmap: from zero to the latest approach

26 phases, **P00–P25**, in the order the original project lived them. Each phase
lists: *Origin* (what happened and why), *Depends on*, *Owners*, *Tasks*
(implementation spec), *Run*, *Outputs*, *Acceptance*. Reference numbers live in
`04_REFERENCE_RESULTS.md` (cited as **R-x**); known traps in `05_PITFALLS.md`
(cited as **PF-x**).

Three eras:

| Era | Phases | Data / protocol |
|---|---|---|
| **A. Legacy pipeline** | P00–P10 | legacy windows (§5.1 of the data spec), `fs=250` assumed in features, 7 channels until P07, **plain `StratifiedKFold`** (leaky — on purpose, to reproduce history) |
| **B. Leak-free + connectivity + graphs** | P11–P15 | legacy windows, trial-grouped CV, connectivity statistics, GNN |
| **C. Professor's revision and detection** | P16–P23 | built windows (§5.2), continuous filtering, `fs=256`, shared quality decision, 6 classes, NBS, window sweeps, pseudo-online, LOSO, GNN LOSO |
| **D. Close-out** | P24–P25 | documentation, deliverables, audit |

Conventions used below: "subject loop" = auto-discovered `S\d+` folders; "smoothing"
= the 2-tap trial-aware rule of `02_REQUIREMENTS.md` §5.6; all scripts save CSVs under
`reports/` (Era A legacy model outputs under `outputs/reports/`) and figures under
`outputs/figures/`.

---

## ERA A — Legacy pipeline (reproduce as it was)

### P00 — Bootstrap and data intake

**Origin.** Repository setup and first contact with the recordings.
**Depends on:** —. **Owners:** Orchestrator, Data Engineer, Verifier.

Tasks
1. Create the repository skeleton of `02_REQUIREMENTS.md` §2 (empty packages with
   `__init__.py`), `requirements.txt`, `environment.yml`, `Makefile` (targets added
   per phase), `pytest.ini`, `CHANGELOG.md`, `RESEARCH_LOG.md`, and `mas/state/`
   (`phase_status.yaml` with all 26 phases `pending`, `decisions.md`).
2. `scripts/exploration/inventory_raw.py`: walk `data/raw/S*/`, parse every `.ebr`
   header only (fast path) and the MARK channel, print and save
   `reports/raw_inventory.csv` with the columns of `01_DATA_SPEC.md` §4 plus channel
   list and event-code counts. Exit non-zero on any deviation from the spec (fs ≠ 256,
   channel list ≠ the 11 names, calibration runs without 40 trials of 8 × 5 targets).
3. Confirm `.gitignore` covers all data (`git check-ignore data/raw/S01/OO.ebr`).

Run: `python scripts/exploration/inventory_raw.py`
Outputs: skeleton, `reports/raw_inventory.csv`.
Acceptance: inventory matches `01_DATA_SPEC.md` §4 row for row (samples, duration,
stim events); `git status` shows no data files; `pytest -q` runs (zero tests is OK).

### P01 — EBR parser and configuration v1

**Origin.** First module of the original project: read the binary format directly.
**Depends on:** P00. **Owners:** Data Engineer, Verifier.

Tasks
1. `src/io/ebr_parser.py`: `load_ebr_file(path) -> dict` exactly per
   `01_DATA_SPEC.md` §2; helpers `resolve_recording_path(raw_root, session, filename)`,
   `select_scalp_channels(channels, scalp_names) -> list[int]`,
   `get_mark_channel_index(channels, mark_name="MARK") -> int` (−1 if absent),
   `extract_scalp_signal(recording, scalp_names) -> (matrix (C, T), names)`.
2. `configs/pipeline_config.yaml` **v1** (`02_REQUIREMENTS.md` §3) — PO7 excluded.
3. `src/preprocessing/signal/filters.py`: `apply_iir_bandpass(data, fs, lowcut=1.0,
   highcut=60.0, order=4)` = `scipy.signal.iirfilter(order, [low/nyq, high/nyq],
   btype="bandpass", ftype="butter")` + `filtfilt` along the last axis.
4. Tests: EBR round-trip, dtype table, unsupported dtype error.

Acceptance: parsing all 23 files gives the inventory of P00; tests pass.

### P02 — Legacy preprocessing and windowing

**Origin.** `run_preprocessing.py` + `psd_extraction.py`: condition windows with a
raw-stage quality gate and PSD features; the arrays every Era-A/B script consumes.
**Depends on:** P01. **Owners:** Signal Processing, Verifier.

Tasks
1. `src/preprocessing/signal/quality_check.py` (legacy part):
   - `validate_eeg_windows(windows, vpp_min=5.0, vpp_max=120.0, std_min=1.0,
     std_max=35.0) -> int mask` (1 if **every** channel has `vpp_min ≤ ptp ≤ vpp_max`
     and `std_min ≤ std ≤ std_max`);
   - `filter_dataset(X, y, mask)`;
   - `summarize_window_quality(...)` (prints observed Vpp/std ranges vs thresholds);
   - legacy helpers `window_quality_flags`, `segment_and_validate_eeg`.
2. `src/features/ssvep/psd_extraction.py`:
   - `extract_clean_subwindows_psd(segment, fs, sub_window_sec=1.0, vpp_thresh=200.0,
     std_range=(0.5, 60.0), quality_stats=None, vpp_min=0.5)`: slice the segment into
     `int(sub_window_sec*fs)` sub-windows, gate them with `validate_eeg_windows(...,
     vpp_min=vpp_min, vpp_max=vpp_thresh, std_min, std_max)` — **pass `vpp_min`
     explicitly** (PF-07) — and return records `{time_data, vpp, std, psd, freqs}`
     using `scipy.signal.periodogram`;
   - `process_condition_windows_with_baseline(eeg, mark, fs, target_conditions=(101..105),
     cue_condition=202, cross_condition=201, sub_window_sec=1.0, vpp_thresh=200.0,
     std_range=(0.5,60.0), stim_duration_sec=5.0, cue_lookback_sec=1.0,
     quality_stats=None)`: 202 → the `cue_lookback_sec` before each onset (only if
     complete); 101–105 → `stim_duration_sec` after each onset if it fits (fallback:
     contiguous plateaus if no rising edges are found); 201 → the 2.0 s after each onset;
   - `prepare_feature_matrix(records, target_conditions=(201,202,101,...,105),
     freq_range=(5,35)) -> (X_psd, X_time, y)` concatenating conditions in that order.
3. `scripts/preprocessing/run_preprocessing.py` with `--subject` (default S03) and
   `--all`: load `<subject>/OO.ebr`, take config scalp channels + MARK, broadband
   filter the **continuous** signal (config 1–60 Hz, order 4), extract condition
   windows with the legacy limits (vpp ≤ 200, std 0.5–60, vpp_min 0.5), print
   accepted/rejected counts and per-condition window counts, save
   `data/processed/<subject>/{X_psd_features,X_time_windows,y_labels}.npy`, and plot
   `outputs/figures/spectra/average_psd_by_condition.png`
   (`src/visualization/signal_plots.py::plot_average_psd_by_condition`, 1–60 Hz).
   Also write the S03 arrays to `data/processed/` root (the original's single-subject
   default location, used by early scripts).
4. `src/visualization/signal_plots.py`: `plot_eeg_window`, `plot_average_psd_by_condition`,
   `plot_stimulus_vs_baseline_psd`.

Run: `python -m scripts.preprocessing.run_preprocessing --all`
Acceptance
- Per subject: `X_time_windows` `(n, 7, 256)`, `X_psd_features` `(n, 217)`, `y` in
  `{201,202,101..105}`, `n ≤ 320`, label counts ≤ `{201: 80, 202: 40, 101–105: 40}`.
- Compare `n` with **R-1** (317–320 per subject); explain any difference.
- The PSD-by-condition figure shows peaks at the stimulation frequencies for at least
  S03–S05.

### P03 — Exploration and signal verification

**Origin.** `visualize_data.py`, `diagnose_occipital_spectra.py`: sanity checks
before modelling.
**Depends on:** P02. **Owners:** Signal Processing, Scientific Reviewer.

Tasks
1. `scripts/exploration/diagnose_occipital_spectra.py`: occipital (by name) FFT power
   per class, 5–35 Hz, with the target frequency marked; one panel per class.
2. `scripts/exploration/visualize_data.py --subject`: load windows, run the quality
   mask, select stimulus windows, compute PSD / FBCCA / FBCSP features (FBCCA/FBCSP
   arrive in P05 — extend this script then) and plot them per class.
3. Write the first `RESEARCH_LOG.md` entry: which subjects show clear SSVEP peaks.

Acceptance: figures exist; the Reviewer confirms visible fundamental peaks for the
strong responders and records what is seen for S01/S02.

### P04 — Early hybrid models, fusion CNN and first explainability

**Origin.** `train_models.py`, `spatial_spectral_cnn.py`, `train_final_model.py`,
`batch_run_subjects.py`, `run_xai.py`, `compare_subject_xai.py`: the first model
benchmark on a harmonic-PSD + FBCCA hybrid, a dual-branch CNN, exported per-subject
models and LDA-weight heatmaps. (Its chronology relative to P05 is approximate; it
uses only legacy arrays and leaky CV.)
**Depends on:** P02. **Owners:** Classical ML, Deep Learning, XAI, Verifier.

Tasks
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

Acceptance: all scripts run; figures and CSV exist; DualBranchFusionCNN has 10,005
parameters (R-8); numbers recorded in the phase report (no reference targets — R-2 lists what the original saved). The Reviewer notes
in the report that this phase's CV is leaky and its smoothing ignores trial
boundaries (fixed in P11).

### P05 — Feature extractors and feature-space / model benchmark

**Origin.** Commits "implement PSD, FBCCA, and FBCSP extractions with quality masking",
"add 5-fold CV benchmark suite, confusion matrix diagnostics", "validate hybrid
FBCSP+FBCCA pipeline on subject (95.43% smoothed CV)".
**Depends on:** P02, P03 (extends P03's `visualize_data.py`). **Owners:** Classical ML, Verifier.

Tasks
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

Acceptance: S03 FBCSP(m=1)+FBCCA → Shrinkage-LDA = **R-3** (90.36 % / 95.43 %, 197
clean windows, 3 rejected) within tolerance; the hybrid beats every single-domain
space; FBCCA argmax is the lowest supervised reference. Report the full
feature-space × model table.

### P06 — Feature-selection ablation, legacy 5-subject cohort, report v1

**Origin.** "finalize methodology report, 5-subject benchmark and infographic"; the
technical report *A Leakage-Free Classical Pipeline for 5-Class SSVEP Decoding Under
a 1.0-Second Constraint* (its "leakage-free" claim was later shown wrong — P11).
**Depends on:** P05. **Owners:** Classical ML, Scribe, Verifier.

Tasks
1. `src/features/selection/feature_selection.py::select_k_best_fbcsp_features(X_tr,
   y_tr, n_features_to_select=15, method="anova"|"mutual_info", random_state=42)` —
   in-fold, on the 50 FBCSP columns only (FBCCA always kept).
2. `benchmark_feature_selection.py --subject S03 --k-features 20`: full baseline (55),
   sub-band pruning (drop 38–52 Hz → 45), ANOVA top-k + FBCCA, mutual-information top-k
   + FBCCA, sequential forward selection; each → Shrinkage-LDA, 1.0 s and smoothed.
3. Legacy cohort script `benchmark_5_subjects.py` (later superseded by
   `benchmark_n_subjects.py`): the P05 flagship for S01–S05 →
   `reports/five_subjects_benchmark.csv`.
4. Technical report v1 (`docs/report/v1/`): academic format (Abstract, Introduction,
   Materials and Methods, Results, Discussion, Conclusion, References, ~5 pages),
   with the ablation table and the cohort table; methodology infographic v1. Both
   are superseded in P24 but must exist as history.

Acceptance: ablation = **R-4**; cohort = **R-5** (leaky: 83.33 % / 87.57 %).

### P07 — Two-tier artifact quality gate and the 8-channel montage

**Origin.** Roadmap item "add a criterion to automatically discard noisy channels";
the montage legend showed 8 channels while the pipeline used 7 (PO7 hard-excluded).
**Depends on:** P06. **Owners:** Signal Processing, Classical ML, Verifier.

Tasks
1. `quality_check.py` additions: `compute_channel_quality_stats` (per-channel fail
   fraction, mean Vpp, mean std), `identify_noisy_channels(windows, channel_names,
   limits, fail_fraction_thresh=0.5)` (channel dropped if it fails the limits in
   **> 50 %** of windows), `drop_noisy_channels`, and
   `apply_artifact_quality_pipeline(windows, y, channel_names, vpp 5–120, std 1–35,
   channel_fail_fraction_thresh=0.5, verbose, precomputed=None)` → dict
   `windows_clean, y_clean, valid_mask, channels_kept, channels_kept_idx,
   channels_dropped, channel_stats`. Tier 1 = channel drop for the whole subject;
   tier 2 = window rejection on the surviving channels.
2. All extractors (FBCCA, FBCSP, PSD) run this pipeline and return 4 values.
   Update **every** consumer (`benchmark_harmonic_fbcca`, `benchmark_feature_selection`,
   `benchmark_cross_validation`, `visualize_data`, `test_sklearn_models`,
   `evaluate_confusion_matrix`).
3. Config: restore PO7 (8 scalp channels, `excluded: []`). Add
   `resolve_channel_names(n_channels)`: 8 → full montage, 7 → montage without PO7
   (legacy arrays), else None — so un-regenerated subjects keep working.
4. `run_preprocessing.py`: before window extraction, detect chronically noisy channels
   on non-overlapping 1 s windows of the filtered recording (`vpp 5–200, std 0.5–60`)
   and drop them; keep the raw gate with `vpp_min=0.5` pinned.
5. **Reproduce the regression**: show that letting the raw gate inherit the new
   default `vpp_min=5.0` rejects all 320 windows of S03, then pin it (PF-07). Add
   `summarize_window_quality` output to the preprocessing log.
6. `scripts/benchmarks/feature_based/benchmark_n_subjects.py`: auto-discovers
   subjects under `--data-root` (default `data/processed`), `--n-jobs` (joblib),
   FBCSP(m=1, in-fold) + FBCCA → scaler → Shrinkage-LDA, smoothing, columns of
   `02_REQUIREMENTS.md` §6, saves `reports/n_subjects_benchmark.csv`. (Still
   `StratifiedKFold` here; P11 changes it.)

Acceptance: tests for both tiers; S03 still produces windows; channel report printed
per subject; benchmark CSV produced for every subject (channels kept/dropped column
filled). Record numbers (no reference target for this intermediate state).

### P08 — EEGNet on raw windows

**Origin.** Roadmap item "try other neural network architectures"; first network.
**Depends on:** P07. **Owners:** Deep Learning, Verifier.

Tasks
1. `src/models/cnn/eegnet.py::EEGNetSSVEP(n_classes=5, n_channels=7, n_samples=256,
   F1=8, D=2, F2=16, kernel_length=125, dropout_rate=0.25)`: block 1 = Conv2d(1→F1,
   (1,K), pad K//2, no bias) + BN + depthwise Conv2d(F1→F1·D, (C,1), groups F1, no
   bias, **max-norm 1.0**) + BN + ELU + AvgPool(1,4) + Dropout; block 2 = depthwise
   Conv2d(F1·D, (1,16), pad 8) + pointwise 1×1 → F2 + BN + ELU + AvgPool(1,8) +
   Dropout; Linear head sized by a dummy forward pass. Accepts `(B,C,T)` or `(B,1,C,T)`.
2. `scripts/benchmarks/neural_networks/benchmark_eegnet.py --subject S03 --epochs 150
   --batch-size 32 --lr 1e-3 --device --augment(off)`: same quality gate and CV
   scheme as the classical benchmark, **per-window per-channel z-scoring** (each
   window's own mean/std over time), AdamW (wd 1e-2), CosineAnnealingLR (eta_min
   1e-5), `CrossEntropyLoss(label_smoothing=0.05)`, `torch.manual_seed(42+fold)`
   before building each fold's model, 1.0 s and smoothed accuracy.

Acceptance: trains on CPU and GPU; numbers recorded (Era-A leaky).

### P09 — Compact-CNN and ShallowConvNet

**Depends on:** P08. **Owners:** Deep Learning, Verifier.

Tasks
1. `src/models/cnn/compact_cnn.py::CompactCNN(n_classes=5, n_channels=7,
   n_samples=256, fs=250.0, lowest_freq_hz=8.5714, F1=16, F2=32, dropout_rate=0.5)`
   (Waytowich et al. 2018, faithful in spirit): spatial Conv2d(1→F1, (C,1), no bias) +
   BN → temporal Conv2d(F1→F2, (1,K), pad K//2, no bias) + BN + ELU + Dropout, with
   `K = clamp(round(fs / lowest_freq), 4, n_samples)` (one cycle of the slowest
   target) → Flatten → Linear.
2. `src/models/cnn/shallow_conv_net.py::ShallowConvNet(n_classes=5, n_channels=7,
   n_samples=256, F1=40, temporal_kernel_length=25, pool_kernel_length=75,
   pool_stride=15, dropout_rate=0.5)` (Schirrmeister et al. 2017): temporal Conv2d(1→F1, (1,25), **no bias**) →
   spatial Conv2d(F1→F1, (C,1), **no bias**) → BN → square → AvgPool → `log(clamp(x, 1e-6))` → Dropout →
   Linear; clamp kernel/pool sizes to the window.
3. `benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py`: mirror
   `benchmark_eegnet.py` exactly.
4. Report parameter counts for 7 channels × 256 samples (**R-8**: EEGNet 2,349,
   ShallowConvNet 14,485, Compact-CNN 56,021).

Acceptance: parameter counts equal R-8 exactly; benchmarks run.

### P10 — Data augmentation and the A/B protocol

**Origin.** Roadmap items "implement simple EEG data augmentation" and "networks +
augmentation". The first A/B showed EEGNet near chance on S01/S02 → a train-accuracy
diagnostic was added to tell non-convergence from overfitting.
**Depends on:** P09. **Owners:** Deep Learning, Scientific Reviewer, Verifier.

Tasks
1. `src/preprocessing/dataset/augmentation.py`: `add_gaussian_noise(window,
   std_frac=0.05)` (noise ∝ each channel's std), `scale_amplitude(window, (0.9, 1.1))`
   (one factor per window), `time_shift(window, max_shift_frac=0.1)` (circular roll),
   `mixup_intra_class(a, b, alpha=0.4)` (λ ~ Beta(α,α), `λ = max(λ, 1−λ)`, **same
   class only**). `SSVEPAugmentedDataset(X, y, p_noise=p_scale=p_shift=p_mixup=0.5,
   seed)`: training fold only, on the fly, order mixup → scale → shift → noise,
   precomputed class→indices lookup, returns float32/long tensors.
2. `--augment` flag in the three single-subject NN benchmarks (off by default).
3. `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py --model
   {eegnet,compact_cnn,shallow_conv_net} --epochs 150`: every subject, OFF then ON,
   same seeds; final-epoch **training accuracy** on the un-augmented training fold
   (diagnostic; never used for gradients); warn when OFF train accuracy < 40 %; save
   `reports/augmentation_ab_<model>.csv`.

Run (Era-A, leaky CV): all three models. Freeze the CSVs as
`reports/legacy_leaky/augmentation_ab_<model>.csv`.
Acceptance: EEGNet cohort augmentation gain in the range recorded by **R-9a** (first
leaky run +3.00 pp 1.0 s / +1.79 pp 2.0 s with 4/5 subjects improved and S02
regressed; the last leaky run before the fix +7.34 pp 1.0 s) — explain where yours
falls; S01/S02 near chance with high training accuracy is reproduced and interpreted
(generalization failure, not optimization failure).

---

## ERA B — Leak-free evaluation, connectivity and graphs

### P11 — Discover and fix trial leakage

**Origin.** The critical finding of the project: every benchmark used
`StratifiedKFold` on 1 s sub-windows, so the 5 sub-windows of one 5 s trial landed in
both train and test. Fixed with `build_trial_ids` + `StratifiedGroupKFold` in all 9
benchmark scripts.
**Depends on:** P10. **Owners:** Evaluation lead, Classical ML, Deep Learning,
Scientific Reviewer, Verifier.

Tasks
1. `src/preprocessing/dataset/cv_utils.py::build_trial_ids(y, sub_windows_per_trial=5
   | dict)`: walk contiguous same-label blocks; split each block into consecutive
   chunks of the per-label trial length (dict form: `{201: 2, 101..105: 5}`); a
   non-divisible remainder gets its own id and prints a warning. Compute on the
   **pre-gate** label array, then index with the same `valid_mask` as `y_clean`.
2. Verify on real data that blocks are ~40 windows per condition (8 trials × 5), and
   report subjects with truncated blocks (e.g. 38–39 windows) as "approximate trial
   ids".
3. Switch to `StratifiedGroupKFold(5, shuffle=True, random_state=42)` with
   `groups=trial_ids` in: `benchmark_n_subjects`, `benchmark_nn_augmentation`,
   `benchmark_cross_validation`, `benchmark_feature_selection`,
   `evaluate_confusion_matrix`, `benchmark_harmonic_fbcca`, `benchmark_eegnet`,
   `benchmark_compact_cnn`, `benchmark_shallow_convnet`.
4. `scripts/diagnostics/demo_cv_leakage.py` (new in this rebuild): for every subject,
   run the flagship with both splitters on the same data and print the before/after
   table; add a unit test asserting that no trial id is shared between train and test
   for every benchmark's split.
5. Re-run: flagship cohort, the three augmentation A/Bs, the S03 feature-space and
   ablation benchmarks. Update `README`/`RESEARCH_LOG` with corrected numbers and the
   size of the inflation.

Acceptance: flagship = **R-6** (S01 61.00/67.50, S02 56.12/61.73, S03 86.80/90.36,
S04 97.46/97.97, S05 95.00/95.50; mean 79.28/82.61); augmentation A/B = **R-9b**;
the before/after table shows the classical pipeline dropping ~4–5 pp and the CNNs
dropping much more (Compact-CNN up to ~20 pp on single subjects); the EEGNet cohort
augmentation gain shrinks from +7.34 pp (last leaky run) to +2.01 pp, while
Compact-CNN (+17.16 pp) and ShallowConvNet (+2.53 pp) keep theirs.

### P12 — Functional connectivity v1: coherence, bias fix, matched baseline

**Origin.** New work stream: connectivity between channels, stimulus vs no stimulus,
one averaged diagram per condition, MNE-style. Coherence chosen first. The first real
run (S03, S04) exposed two methodological bugs.
**Depends on:** P11. **Owners:** Connectivity & Stats, Scientific Reviewer, Verifier.

Tasks
1. `src/features/connectivity/connectivity_extraction.py` (part 1):
   `CONDITION_FREQS = {101: 24, 102: 20, 103: 15, 104: 10.9091, 105: 8.5714}`,
   `BASELINE_CONDITION = 201`, `BASELINE_BAND = (5, 35)`, half-width 1 Hz;
   `compute_coherence_matrix(window, fs, band, nperseg=min(T,128))` (per-window,
   **diagnostic only**); `compute_condition_coherence(windows, fs, band, nperseg=256)`
   = concatenate the condition's windows per channel and run `scipy.signal.coherence`
   once per pair, band-average; `band_for_condition`; `compute_condition_connectivity`;
   `compute_baseline_matched_connectivity` (re-score the **same 201 windows** in each
   stimulus band); `compute_difference_matrices` (stimulus − matched baseline).
2. **Reproduce both bugs first** (in a notebook-style diagnostic script, kept):
   (a) per-window coherence averaged over windows gives ≈0.32–0.35 for independent
   noise at 256 samples / nperseg 128, vs ≈0.01–0.02 with the concatenated estimator,
   while coupled signals stay ≈0.98–0.99; (b) broadband baseline vs narrow stimulus
   band is not apples-to-apples → matched-baseline difference.
3. `src/visualization/connectivity_plots.py` (mne-connectivity circle plots):
   `plot_condition_connectivity`, `plot_all_conditions_panel` (raw per condition),
   `plot_difference_panel` (diverging `RdBu_r`, symmetric around 0 — the primary
   output), later `plot_permutation_null_distributions`. `CONDITION_LABELS` with
   "No stimulus (201)".
4. `scripts/connectivity/analysis/analyze_connectivity.py --subject S03 --method
   coherence`: raw panel + difference panel + console table.

Acceptance: synthetic tests of task 2; S03/S04 baseline coherence drops after the fix
(R-11: from ≈0.68–0.73 to ≈0.59–0.66); differences show 24 Hz and 20 Hz consistently
positive in S03/S04 (≈+0.11 to +0.25) and 10.91/8.57 Hz inconsistent (alpha-band
ceiling hypothesis recorded, to be tested statistically in P13).

### P13 — Phase and autoregressive connectivity with permutation statistics

**Origin.** PLV/wPLI, PDC and a permutation + Benjamini-Hochberg framework were added;
a correctness review found two implementation bugs; the cohort script had a display
bug; permutations were later moved from window level to trial level.
**Depends on:** P12. **Owners:** Connectivity & Stats, Scientific Reviewer, Verifier.

Tasks
1. Phase connectivity from the **cross-spectral density**, not time-domain Hilbert:
   `compute_phase_connectivity(windows, fs, band, metric, nperseg=min(T,128))` — per
   window one band-averaged complex CSD value per pair (`scipy.signal.csd`); PLV =
   `|mean(exp(i·angle))|`; wPLI = `|mean(Im)| / mean(|Im|)` (0 if the denominator
   is 0). `compute_condition_plv`, `compute_condition_wpli`.
   **Reproduce the bug first**: a filtfilt + Hilbert implementation on 256-sample
   windows with a ±1 Hz band has amplitude envelopes at 5–70 % of truth in the first/last
   ~15 samples and unstable instantaneous frequency; padding/order/bandwidth do not fix
   it; the CSD version is unchanged (0.998 → 0.998) when edge samples are corrupted.
2. PDC: `fit_mvar_ols(windows, p=10)` — design matrix rows from each window without
   crossing window boundaries, columns **channel-major** (`window[:, t-p:t][:, ::-1]`
   flattened), ridge `1e-4·tr(G)/dim`; coefficients per lag = `weights[lag::p, :].T`
   (**strided**, PF-17); `compute_condition_pdc(windows, fs, band, order=10)`:
   15 frequencies across the band, `A(f) = I − Σ_l A_l e^{−2πi f l/fs}`, column-normalized
   magnitude, zero diagonal, averaged; entry `[i, j]` = flow j → i.
   **Reproduce the bug first**: contiguous slicing `weights[lag*C:(lag+1)*C]` gives
   ~150–200 % coefficient error on an identifiable synthetic VAR; strided gives ~5–10 %.
3. Permutation test `compute_permutation_test(stim, base, band, fs, n_permutations=200,
   method_fn, n_jobs=-1, random_state=42, alpha=0.05, stim_trial_ids=None,
   baseline_trial_ids=None)`: observed diff matrix; pool windows; per permutation
   split into groups with the **observed group sizes**; with trial ids, permute whole
   trials (`_trial_permutation_split`: greedy fill in random trial order, at most one
   trial split to match the count exactly); global statistic = mean upper-triangle
   difference, one- and two-tailed p with +1 pseudo-count, null mean/std/95 % CI;
   edge p-values one/two-tailed; BH-FDR (`benjamini_hochberg`) across the 21/28 edges;
   return `permutation_unit` "trial" or "window".
4. `extract_connectivity_by_condition(windows, y, fs, method_fn, conditions,
   channel_names, limits…, n_permutations=0, trial_ids=None, quality=None)`: one
   shared quality gate for all conditions, then by-condition matrices, matched baseline,
   differences, optional permutation tests per frequency.
5. `scripts/connectivity/analysis/analyze_connectivity_cohort.py --methods coherence
   plv wpli pdc --permutations 100|200 --n-jobs -1`: every subject × method; trial ids
   from `build_trial_ids(y, {201: 2, 101..105: 5})`; summary CSV (§6 schema) and
   per-subject edge files `reports/connectivity_edges/<S>_<method>.npz`; console
   reports **both** criteria separately: (A) subjects with ≥1 FDR edge, (B) subjects
   with global p < α — never one merged star (PF-20).
6. Run first with window-level permutations (record), then trial-level (final).

Acceptance: synthetic tests (MVAR recovery, edge immunity, trial split sizes);
cohort result = **R-12** (S01/S02 null on essentially everything; 24 Hz the only
frequency robust across S03–S05 in both coherence and wPLI; FDR edge totals per
subject coherence 0/0/65/51/15, wPLI 0/3/38/33/18 at 200 trial-level permutations
within tolerance); borderline cells that flip between 100 and 200 permutations are
listed as inconclusive.

### P14 — Cross-frequency comparison, reliability, and power/alpha confounds

**Origin.** Professor's follow-up: how to compare connectivity across stimulation
frequencies; then whether the deltas are just SSVEP power or alpha blocking.
**Depends on:** P13. **Owners:** Connectivity & Stats, Scientific Reviewer, Verifier.

Tasks
1. `scripts/connectivity/comparison/compare_connectivity_frequencies.py`
   (descriptive, on **delta** matrices only): load edge files, embed each subject's
   matrix into the 8×8 montage with NaN for missing channels; per subject and method:
   Pearson r between off-diagonal entries of every frequency pair with a one-tailed
   **QAP** node-label permutation p (2,000 permutations, ≥6 finite pairs, ≥4 shared
   channels); node strength per channel (symmetrized, mean to others); global mean
   delta and FDR-edge count per frequency. Group summaries for all / responders /
   non-responders, where **responders are defined from classifier performance**
   (2.0 s smoothed accuracy ≥ 80 % in `n_subjects_benchmark.csv`, or `--responders`),
   never from connectivity (circular). Fisher-z averaging of r across subjects.
   Figures: similarity matrices, node strength, delta matrices per group. CSVs per §6.
2. `scripts/connectivity/comparison/test_connectivity_frequency_differences.py`
   (coherence, PLV, wPLI; PDC excluded): per subject, trial-level split-half
   reliability of each delta matrix (random halves of trials, 10 splits, Fisher-mean r,
   Spearman-Brown `2r/(1+r)` only if r > 0, else report r uncorrected — PF-22);
   pairwise test per frequency pair with trial-level permutations (500, ≥1000 for
   final): magnitude statistic = mean upper-triangle (Δa − Δb), two-sided; pattern
   statistic = 1 − r(Δa, Δb), one-sided; edge-level two-sided p + BH-FDR; reliability
   ceiling `sqrt(rel_a·rel_b)`, disattenuated r (only if ceiling > 0.1); BH across pairs
   per subject; Fisher-combined p across responders; flag approximate trial ids.
3. `scripts/connectivity/diagnostics/check_power_alpha_confound.py`: per subject and
   frequency on O1/Oz/O2 Hann periodograms: `target_snr_db = 10 log10(P_stim/P_base)`
   in f0 ± 1 Hz; `alpha_change_db` in 8–13 Hz **excluding f0 ± 1.5 Hz**; merge with
   `<method>_global_delta.csv`; Spearman (all cells, and within-subject centered), OLS
   R² of `delta ~ SNR + alpha`; in-alpha (10.91, 8.57) vs out-of-alpha means; scatter
   figure `connectivity_delta_vs_power.png`. (The original has a misspelled duplicate
   `check_power_alpha_cofound.py`; create only the correct name — PF-27.)

Acceptance: CSVs and figures per §6; the report states, with numbers, how much of
the delta is explained by target SNR and alpha change and whether 10.91/8.57 Hz
behave differently (no fixed numeric target; compare qualitatively with R-13).

### P15 — Per-window graphs, the connectivity gate, and a GNN

**Origin.** Professor's assignment: model connectivity with graph neural networks to
classify the stimulation frequency. Plan: first test whether connectivity features add
information to power features (a "gate"), then a GNN.
**Depends on:** P14. **Owners:** Connectivity & Stats, Deep Learning, Verifier.

Tasks
1. `src/features/connectivity/connectivity_graph_features.py`:
   `node_band_power(windows, fs)` = log10 Hann-FFT power per channel at the 5 targets
   and 2nd harmonics, ±1 Hz bins (nearest bin if none), harmonic-major → `(n, C, 10)`;
   `edge_coherence` = in-window Welch (nperseg 128, step 64 → 3 Hann segments for 256
   samples), MSC band-averaged → `(n, C, C, 5)`; `edge_phase` = unit phasor
   (cos, sin) of the full-window cross-spectrum summed over band bins →
   `(n, C, C, 5, 2)`; `upper_tri_flat`; `build_graph_features`.
2. `scripts/connectivity/graph_modeling/build_graph_dataset.py [--rebuild]`: per
   subject, quality gate + FBCCA + graph features + trial ids → cached
   `data/processed/<S>/graph_dataset.npz` (`node, edge_coh, edge_phase, X_fbcca, y,
   trial_ids, channels_kept`); sanity report of own-band minus other-class differences
   for node power, coherence and phase consistency.
3. `benchmark_connectivity_gate.py --repeats 5 --k-select 0 30`: feature sets `N`
   (70), `F` (5), `N+F` (= Base, 75), `Ec` (105), `Ep` (210), `Ec+Ep`, `Base+Ec` (180),
   `Base+Ep`, `Base+Ec+Ep` (390); pipeline scaler → optional in-fold `SelectKBest(f_classif,
   k)` → Shrinkage-LDA; grouped CV repeats with seeds 42+r; per-subject deltas vs Base;
   gate verdict: **pass if edge features add ≥ 2 pp on average and in ≥ 2/3 of
   responders** (descriptive heuristic).
4. `src/features/connectivity/graph_inputs.py`: variants `nodes[+coh][+phase][+F]`
   (must start with `nodes`), `build_inputs`, train-fold-only `fit_standardizer` /
   `apply_standardizer` / `standardize_fold`.
5. `src/models/graph/connectivity_gnn.py::ConnectivityGNN(n_nodes, n_node_feats,
   n_edge_feats=0, n_graph_feats=0, n_classes=5, hidden=32, n_layers=2, dropout=0.3)`:
   node encoder Linear+ELU + learned channel embedding (init N(0, 0.1)); `EdgeGatedLayer`
   = residual `LayerNorm(h + Dropout(ELU(W_self h + agg)))` where `agg` averages
   messages `W_msg h_j` from the other nodes, optionally gated by `sigmoid(Linear(e_ij))`;
   readout = concat(mean, max) over nodes → dropout → concat graph features (FBCCA) →
   Linear.
6. `benchmark_gnn.py [--smoke-test] --repeats 3 --epochs 150`: AdamW 1e-3/1e-2,
   cosine (eta_min 1e-5), label smoothing 0.05, batch 32, seeds `1000·r + fold`;
   prints LDA gate rows alongside and a train-accuracy diagnostic with
   over/under-fitting hints.

Acceptance: gate table = **R-14** (Base+Ec best mean 77.6 %, gate does **not** pass);
GNN = **R-15** (nodes+F ≈ nodes+coh+F; coherence edges do not help); smoke test passes.

---

## ERA C — Professor's revision, detection, generalization

### P16 — Baseline freeze, edge effects, continuous filtering, 256 Hz, shared quality

**Origin.** Professor's change list (Oct 2026), branch `fix/signal-filtering-edge-effects`:
research edge effects; filter the raw continuous signal instead of each window; only
valid windows go into frequency analyses; and the discovery that the recordings are
**256 Hz**, not the 250 Hz assumed in feature code.
**Depends on:** P15. **Owners:** Signal Processing, Evaluation lead, Connectivity &
Stats, Verifier.

Tasks
1. `scripts/freeze_baseline.py --tag v1 --note "…"`: copy `data/processed`, `reports`,
   `outputs/reports`, `configs` into `baselines/v1_<date>/` (read-only, refuse to
   overwrite), file pre-leak reports (`five_subjects_benchmark.csv`) under
   `superseded/`, write `MANIFEST.json` (git commit, dirty flag, python, platform, pip
   freeze, per-subject channel audit, sha256/shape/rows per file) and
   `baseline_summary.csv` (long format `pipeline, subject, metric, value` + `MEAN`
   rows, from the n-subject, augmentation, GNN, gate and connectivity CSVs). **Run it
   before any other change in this phase.**
2. `src/preprocessing/windowing.py`: `load_session(path, scalp_channels, mark)`;
   `event_onsets(mark, code)`; `WindowIndex(starts, labels, trial_ids, sub_idx,
   offsets)`; `segment_starts`; `windows_per_segment`; `build_window_index(mark, fs,
   stim_conditions, cross_condition=201, cue_condition=202, sub_window_sec=1.0,
   stim_duration_sec=5.0, cross_duration_sec=2.0, cue_lookback_sec=1.0,
   stride_sec=None)` — segments: cross `[onset, onset+2 s)`, cue `[onset−1 s, onset)`,
   stimulus `[onset, onset+5 s)` complete trials only; windows every `stride` fully
   inside the segment; one trial id per segment. `stride=None` reproduces the legacy
   windows exactly. `cut_windows`; filter banks `fbcca_filter_bank(fs)` (Chebyshev as
   P05) and `fbcsp_filter_bank(fs)` (Butterworth order 4, P05 bands);
   `band_windows(broadband, starts, n, bank, mode)` with modes **continuous** (filter
   whole recording, then cut) and **per_window** (cut, then filter — legacy);
   `select_clean_bands`.
3. `scripts/diagnostics/demo_edge_effects.py --subject S03`: every FBCSP/FBCCA band
   computed both ways on stimulus windows; relative error |pw − cont| / RMS(cont);
   edge (first/last 100 ms) vs centre; 3-panel figure (example trace at 15 Hz on Oz in
   the 13–17 Hz band, error profile over the window for a narrow and a wide band, every
   band edge vs centre) → `outputs/figures/edge_effects/edge_effects_S03.png`; table
   `reports/edge_effects_summary.csv`.
4. `src/preprocessing/window_quality.py::subject_quality_gate(windows, starts,
   broadband, fs, channel_names, filters, params)`: channel tier and window tier as P07
   (limits from config `quality:`); plus an **artifact guard**: mark 0.25 s blocks of
   the continuous filtered signal whose Vpp exceeds `vpp_max` on any kept channel,
   dilate by `guard_sec` (`auto` = longest ringing time of all filters applied
   continuously, measured by the samples where |impulse response| > 1 % of its peak),
   and reject windows overlapping it (reason 2). Returns `valid_mask`,
   `valid_mask_no_guard`, `reason`, kept/dropped channels, fail fractions, guard,
   artifact fraction, params.
5. `scripts/build_windows.py --filter-mode {continuous,per_window} --subjects
   --session OO --guard-sec --window-sec … --stride-sec --banks … --out-root`: per
   subject, load, broadband filter (config: 1–90 Hz order 4, + 60 Hz notch Q 30,
   continuous zero-phase), window index, cut filtered and raw windows, filter banks,
   quality gate, save every file of `01_DATA_SPEC.md` §5.2 into
   `data/processed_<mode>/[w<len>_s<stride>/]<S>/`, print a one-line summary per
   subject. Config moves to the **final** version (`02_REQUIREMENTS.md` §3).
6. `src/io/subject_data.py`: `find_project_root`, `discover_subjects`,
   `resolve_channel_names`, `is_built`, `load_subject(sub_dir, conditions,
   quality_mode="shared"|"shared-no-guard"|"per-script", bands=(), fs_override=None)`
   returning windows, y, trial ids (true ids for built folders, reconstructed for
   legacy), bands, fs (meta, legacy 250), channel names, quality decision, `built`,
   `source`.
7. Port to built windows (default `--data-root data/processed`, accept built roots,
   `--quality`, `--fs` override): `benchmark_n_subjects.py` (FBCCA from the continuous
   `fbcca` bands, CSP on continuous `fbcsp` bands, smoothing by true trial id,
   `--cv-repeats N` with seeds 42+r and SD columns, output suffix rules), the
   connectivity cohort and between-frequency scripts (true trial ids, real fs, shared
   quality). Extractors gain `subband_windows=` and `quality=` parameters.
8. **v1 vs v2 table**: flagship and connectivity on (a) frozen v1, (b) per_window
   built windows at 256 Hz, (c) continuous built windows — separating the effect of fs,
   of filtering mode and of the guard (`--quality shared-no-guard`).

Acceptance: snapshot exists and is read-only; edge-effect table shows edge error
≫ centre error for narrow FBCSP bands; `stride=None` per_window build reproduces
the legacy window starts; v1/v2 table complete with every number backed by a log. No
fixed numeric target for v2 (none was preserved — see R-16); the Reviewer must explain
the direction of every change.

### P17 — Sixth (rest) class and the harmonic / intermediate filter bank

**Origin.** Branch `feature/rest-class-harmonic-filterbank`: add the fixation cross as
a 6th class (detecting "no stimulus"), and add harmonic and between-frequency bands to
the filter bank.
**Depends on:** P16. **Owners:** Signal Processing, Classical ML, Verifier.

Tasks
1. `windowing.py`: `STIM_FREQS`, `harmonic_centers(n_harmonics=3)` (k·f for k=1..3),
   `intermediate_centers()` (midpoints of sorted neighbouring targets),
   `narrow_filter_bank(fs, centers, half_width=1, order=2, max_hz, exclude_hz=[notch])`
   skipping bands above `min(max_hz, nyq−1)` or containing the notch (recorded in
   `bands_skipped`), `band_overlaps` (recorded in meta).
2. `build_windows.py` builds `harmonic` and `intermediate` banks when enabled.
3. `benchmark_n_subjects.py --bank {base, harm, harm+mid}` (extra narrow bands
   appended to the FBCSP bands) and `--classes {5,6}`: 6 classes = stimuli + 201,
   uniform LDA priors, extra metrics (balanced accuracy, false activation, missed
   stimulus, stimulus-correct), summed 2.0 s confusion matrices saved to
   `<csv>_confusion.csv`; 6 classes require built folders (true trial ids).

Run: `--cv-repeats 10` for {base, harm, harm+mid} × {5, 6} classes.
Acceptance: all combinations produce CSVs; the report compares banks and 5 vs 6
classes with SDs over repeats (no preserved reference — record).

### P18 — Network-Based Statistic replaces FDR

**Origin.** Branch `feature/network-based-statistics`: replace edge-wise FDR with
graph-based statistics and compare the sizes of the significant graphs.
**Depends on:** P16 (uses the P13/P14 machinery). **Owners:** Connectivity & Stats,
Verifier.

Tasks
1. `src/stats/nbs.py`: `edge_pseudo_z(obs, null, two_tailed)` (standardize by each
   edge's null mean/std, infinite std → 0), connected components of supra-threshold
   edges (`scipy.sparse.csgraph`), `nbs_test(z_obs, z_null, threshold, alpha)`
   (component size = number of edges; null = max component size per permutation;
   p = (1 + #{null_max ≥ size})/(n+1); significant mask, max size, p of largest,
   n significant edges, possible edges), `nbs_sweep(obs, null, thresholds=(1.5, 2.0,
   2.5, 3.0), …)` reusing the same permutations.
2. Cohort script: NBS on the existing permutation nulls per condition (PDC symmetrized
   first), `--stats {nbs,fdr}` (default nbs) selects the summary criterion, both always
   saved; `--nbs-thresholds`, `--nbs-primary 2.0`; new CSV columns (§6); `nbs_c` masks
   in the edge files; a **graph-size table** (largest component as % of possible
   edges, * if significant) and a threshold-sweep table.
3. Between-frequency tests: two-tailed NBS at |z| > 2 on the pairwise permutation
   nulls; `--summary-only` re-prints group summaries from saved CSVs.

Acceptance: NBS unit tests; cohort tables with both FDR and NBS; the report compares
graph sizes across subjects and frequencies (record).

### P19 — Quality check on the raw segmented signal

**Origin.** Commit "validate windows on the raw segmented signal": filtering can hide
artifacts, so limits may also be checked on unfiltered windows cut at the same
positions.
**Depends on:** P16. **Owners:** Signal Processing, Verifier.

Tasks: `subject_quality_gate(..., raw_windows, raw)` with `params["source"] ∈
{filtered, raw, both}` — a channel or window must pass on every checked signal;
artifact blocks searched on each checked continuous signal; windows failing only on raw
get reason 3; `build_windows.py --quality-source`; config default becomes `both`;
`rejected_by_label` reports reasons 1/2/3.
Acceptance: per-subject rejection breakdown by reason for filtered/raw/both; flagship
re-run on `both` vs `filtered` (record the difference).

### P20 — Detection: window length, ITR, CCNN, NN sweep, dynamic stopping, pseudo-online

**Origin.** Professor (Oct 11): treat it as a **detection** problem, test different
window sizes, identify which frequency it is, and run online with a neural network.
**Depends on:** P19. **Owners:** Classical ML, Deep Learning, Online/Real-time,
Verifier.

Tasks
1. Build sweep data: `build_windows.py --window-sec 0.5 1 1.5 2 3 4 --stride-sec 0.25
   --banks fbcca fbcsp` → `data/processed_continuous/w<len>_s0.25/`.
2. `scripts/benchmarks/benchmark_window_sweep.py --windows … --methods fbcca lda cnn
   --cv-repeats 5 --cnn-repeats 1`: vectorized FBCCA (`reference_bases`: orthonormalized
   (QR) mean-centred sin/cos references, 3 harmonics; per band QR of the centred window,
   top singular value of `Qxᵀ Qy` = first canonical correlation, clipped to [0,1],
   weighted squared sum); `lda_fold` (in-fold CSP per band + FBCCA → scaler →
   Shrinkage-LDA); `cnn_fold` (Compact-CNN, real fs); trial-grouped CV; no smoothing;
   `summarize` (accuracy, SD over runs, balanced accuracy, ITR with `T = window +
   0.5 s`, train accuracy); `predictions.csv` (offset per window) and pooled
   `confusion.csv`.
3. `src/models/cnn/ccnn.py::CCNN(n_classes, n_channels, n_samples, fs=256, f_min=3,
   f_max=50, resolution_hz=0.25, n_filters=2C, spectral_kernel=10, dropout=0.25)`:
   zero-padded rFFT (nfft = max(T, fs/resolution)), bins in [3, 50] Hz, `[real | imag]
   / T`, spatial Conv2d (C,1) + BN + ReLU + Dropout → spectral Conv2d (1, 10) + BN +
   ReLU + Dropout → Linear.
4. `scripts/benchmarks/benchmark_nn_sweep.py --windows 1 --models ccnn compact eegnet
   [--no-augment]`: `fit_network` = inner `StratifiedGroupKFold(round(1/val_frac))`
   on training trials for validation (20 %), augmentation on by default, AdamW/cosine/
   label smoothing, keep the best validation-loss state, patience 25, max 150 epochs;
   report train/val accuracy and best epoch. **Note:** here `compact` is the
   EEGNet-based Compact-CNN (`EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2,
   dropout=0.5)`) and `eegnet` uses `kernel=fs//2` — different from P09's `CompactCNN`
   class (PF-31). Keep both and label them unambiguously in reports.
5. `scripts/benchmarks/simulate_dynamic_stopping.py <predictions.csv …>
   --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5`: per trial, windows in time
   order after `skip`, cumulative mean probabilities, decide at the first window whose
   max ≥ threshold, else forced final decision; time = window offset + window length;
   accuracy, mean time, forced %, ITR (time + gaze); best threshold per method/window by
   ITR; FBCCA skipped (not probabilities).
6. `scripts/benchmarks/pseudo_online.py --train-session OO --test-session mOO --model
   ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6
   [--rest-class]`: train on one run (causal filter, windows, quality gate, network with
   early stopping), replay the other run in stride-sized chunks through a **stateful
   causal** SOS filter (Butterworth band-pass + notch, `sosfilt` with carried `zi`),
   evaluate windows on a fixed clock, predict valid windows; decide per stimulus period
   with the threshold rule (rest class excluded from the decision; with `--rest-class`,
   no threshold → "no target"); false activations in the no-stimulus period before
   each target (`REST_SEC = 5 s` = fixation + cue + preparation, used as the rest
   segment when training the 6th class); label-free channel check on the first
   `--check-sec 30` s of the test stream; fallback retrain with `--fallback-window-sec 1`
   if validation accuracy < `--min-val-acc 50`; warn when train/test paradigms differ
   (OO vs C); save `summary_<tag>.csv` and `decisions_<tag>.csv`. The MARK channel of
   the test run is used only for scoring.

Acceptance: sweep summary for all window lengths × methods; NN sweep at 1 s; dynamic
stopping best-threshold table; pseudo-online summary for 5 and 6 classes; causal-filter
test passes. No preserved reference numbers (R-16) — record and interpret
(accuracy/ITR trade-off vs window length).

### P21 — Leave-one-subject-out (LOSO) generalization + Colab

**Origin.** Professor (Oct 13): subject generalization, "con todos menos con uno";
run on Google Colab (new user, credits provided).
**Depends on:** P20. **Owners:** Evaluation lead, Classical ML, Deep Learning, Infra,
Verifier.

Tasks
1. `scripts/benchmarks/benchmark_loso.py --window 1 --stride-sec 0.25 --methods fbcca
   lda lda_subjnorm ccnn compact eegnet --channels common|all`: `choose_channels`
   (montage identical for all subjects; `common` = channels kept by the gate in every
   subject); `load_subject` (clean stimulus windows, chosen channels, FBCCA scores);
   methods: `fbcca` (normalized scores, no training — the calibration-free floor),
   `lda` (CSP per band fitted on pooled training subjects + FBCCA → scaler →
   Shrinkage-LDA), `lda_subjnorm` (each subject's features z-scored with its **own
   unlabeled** mean/std before pooling — report as "unsupervised per-subject
   normalization"), networks via `fit_network` on pooled subjects (trial ids offset per
   subject; validation never from the test subject); **resumable**: each (method, test
   subject) fold saved to `<out-dir>/folds/<method>__test-<S>.npz` and skipped on rerun;
   `--save-models`; summary with 2-tap smoothed accuracy, per-subject pivot, cohort
   mean ± SD, `predictions.csv`, `confusion.csv`.
2. `notebooks/loso_colab.ipynb`: GPU check; mount Drive; settings cell (`RAW_DIR`,
   `DRIVE_DIR`, repo URL, branch, `LOSO_OUT`) that lists subjects and checks `OO.ebr`;
   fresh clone per session; install only `pyyaml joblib`; symlink `data/raw`,
   `reports`, `outputs/models` to Drive; build windows; within-subject reference
   (`benchmark_window_sweep.py --windows 1 --methods fbcca lda --cv-repeats 5`); LOSO
   classical; LOSO networks; results comparison table (within vs LOSO); release the
   runtime. Written for a first-time Colab user.

Acceptance: classical LOSO runs end-to-end on CPU; interrupting and rerunning skips
finished folds; the notebook runs top to bottom on a T4 (or the Infra agent documents
the exact manual steps it could not automate). Record within vs LOSO (R-16).

### P22 — LOSO extensions: within reference, explicit channels, resume guard, warm-up

**Origin.** Branch `feature/window-size-online-detection` (Oct 15).
**Depends on:** P21. **Owners:** Evaluation lead, Classical ML, Verifier.

Tasks
1. `benchmark_loso.py`: method `within_lda` (within-subject grouped CV on exactly the
   LOSO channels; `--folds 5 --within-repeats 5`); `--channels common | all | <names>`
   (explicit names keep only subjects whose gate accepted every named channel; print
   who is left out and what the gate dropped); saved folds record `channels` and
   `train_subjects`; `check_fold` refuses to mix configurations ("use a new --out-dir").
2. `scripts/benchmarks/benchmark_loso_warmup.py --warmup-trials 1 2 5 10 --channels`:
   for each held-out subject, sort its trials by first window start (recording order);
   use the first K trials (unlabeled) to estimate normalization statistics; score only
   trials after K with: `full` (whole-session statistics = lda_subjnorm), `warmup`
   (first-K statistics), `none` (plain lda); report warm-up windows, classes seen, span
   in seconds; cohort table with `warmup − full`.

Acceptance: both scripts run; a changed configuration on an existing out-dir is
refused; warm-up table produced (record).

### P23 — GNN under LOSO (the project's latest approach)

**Origin.** Branch `test/GNN-testing-LOSO` (Oct 21): the edge-gated connectivity GNN
trained on all subjects but one, with a within-subject reference on the same windows.
**Depends on:** P22, P15. **Owners:** Deep Learning, Connectivity & Stats, Infra,
Verifier.

Tasks: `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py`:
- data from the same `w1_s0.25` folder and channel choice as `benchmark_loso.py`;
  graph features computed in memory per subject (P15 definitions) + FBCCA scores;
- variants as P15 (default `nodes+F nodes+coh+F`); `--norm pooled subject` →
  method names `gnn_<variant>` and `gnn_<variant>_subjnorm` (subject = z-score each
  subject's arrays with its own statistics, no labels);
- `fit_gnn`: early stopping on 20 % of training **trials** (grouped; `--val-frac 0`
  = fixed epochs), patience 25, max 150 epochs, AdamW/cosine/label smoothing,
  `--seeds 3` per fold (mean of seeds), train/val/epoch diagnostics;
- `--protocol within` = trial-grouped 5-fold CV inside each subject on the same
  windows (per-subject normalization is a no-op there, so only `pooled` runs);
- resumable folds storing a JSON `config`; a saved fold with a different config is
  refused;
- summary/predictions/confusion like `benchmark_loso.py`, plus `Protocol` column;
- `--smoke-test`: 4 synthetic subjects with different gain and noise, 2 variants × 2
  norms, rerun must skip every fold, within protocol run, mean synthetic LOSO
  accuracy > 40 %.
- Notebook section "10b" with smoke test, within reference and LOSO cells (CPU is
  enough: ~45 min LOSO + ~30 min within on 2 cores for 5 subjects, 3 seeds, 2 variants).

Acceptance: smoke test passes; within and LOSO tables for both variants and both norms;
the report puts them next to `benchmark_loso.py` rows (fbcca, lda, lda_subjnorm,
networks) and interprets train ≈ 100 % / test ≈ chance patterns.

---

## ERA D — Close-out

### P24 — Documentation and deliverables

**Origin.** The project's written outputs: README with results, the academic technical
report, the methodology infographic/poster, the consolidated progress report for the
professor.
**Depends on:** P23. **Owners:** Scribe, Scientific Reviewer, Verifier.

Tasks
1. `README.md` (replaces the operator README): overview, task table (conditions and
   frequencies), results (flagship corrected table, NN augmentation A/B with parameter
   counts, connectivity gate, GNN, connectivity statistics, Era-C results), models
   table with references, deep-learning training convention, pipeline diagram,
   preprocessing/quality description, trial-grouped CV, features, augmentation,
   connectivity workflow, repository structure, usage for every script, trial-grouping
   fix section (before/after), interpretation notes and open questions, environment,
   dataset policy.
2. `RESEARCH_LOG.md`: chronological narrative P00 → P23 with every before/after.
3. `docs/report/`: updated academic report (Abstract, Introduction, Materials and
   Methods, Results, Discussion, Conclusion, References; ~5 pages; concise journal
   style; confusion matrices only in Results/Discussion; numbers exactly from CSVs;
   corrected leak-free numbers; reference: Chailloux Peguero et al. 2023).
4. `docs/infographic/`: one-page methodology infographic (pipeline, protocol, key
   numbers).
5. `docs/progress_report/`: consolidated report for the professor covering every
   assignment (edge effects, continuous filtering, valid windows, 6th class, harmonic /
   intermediate bands, NBS vs FDR graph sizes, detection/window sweep, pseudo-online,
   LOSO, GNN LOSO) with results and open questions.
6. `make all` (or `scripts/run_all.sh`) regenerating every CSV from `data/raw/`.

Acceptance: the Reviewer checks every number in the documents against a CSV;
`make all` succeeds on a clean clone with only `data/raw/` added.

### P25 — Final audit

**Depends on:** P24. **Owners:** Verifier, Scientific Reviewer, Orchestrator.

Tasks
1. Clean-machine rebuild and full test suite.
2. Leakage audit: for every script that splits data, show the split code and the test
   that guards it.
3. Reference comparison: table of every R-x target vs obtained value, status
   (within tolerance / explained deviation / unexplained).
   Autonomy report: every reference consultation (rule 8) across all phases, with
   its trigger, and the share of phases completed without any consultation.
   Sources report: every phase report has a complete `## Sources` list.
4. Diff module by module against `Upland1/ssvep-eeg-xai` (main + `feature/window-size-online-detection` +
   `test/GNN-testing-LOSO`) and list capabilities missing on either side.
5. Final report `mas/state/reports/P25.md` and tag `v1.0`.

Acceptance: no unexplained deviations; no open blockers; all phases `passed`.
