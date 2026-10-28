# 02 — Requirements

## 1. Environment

- Python **3.12** (3.11 must also work; `environment.yml` targets conda 3.11).
- Core: `numpy>=1.26, scipy>=1.11, pandas>=2.0, scikit-learn>=1.3, joblib>=1.3,
  torch>=2.2, pyyaml>=6.0, matplotlib>=3.8, seaborn>=0.13`.
- Connectivity plots: `mne`, `mne-connectivity` (circular diagrams).
- Optional: `shap>=0.45`, `jupyter>=1.0`, `pytest`.
- Original hardware reference: one NVIDIA RTX 3050 Laptop GPU (4 GB), Linux. Every
  network must also run on CPU; device = `cuda` if available, else `cpu`, overridable
  with `--device`.
- Colab: never `pip install -r requirements.txt` on Colab (it can replace the GPU
  build of PyTorch); install only `pyyaml joblib`.
- scikit-learn API note: the classical suite uses `LogisticRegression(l1_ratio=…)`
  (≥1.8 style). If the installed version rejects it, use the equivalent `penalty=`
  form and record it in `decisions.md`.

## 2. Repository layout (final state)

```
configs/pipeline_config.yaml
src/
  io/              ebr_parser.py, subject_data.py
  preprocessing/
    signal/        filters.py, quality_check.py
    dataset/       cv_utils.py, augmentation.py
    windowing.py, window_quality.py
  features/
    ssvep/         fbcsp_extraction.py, fbcca_extraction.py, psd_extraction.py
    selection/     feature_selection.py
    connectivity/  connectivity_extraction.py, connectivity_graph_features.py, graph_inputs.py
  models/
    classical/     sklearn_models.py
    cnn/           eegnet.py, compact_cnn.py, shallow_conv_net.py, ccnn.py, spatial_spectral_cnn.py
    graph/         connectivity_gnn.py
  stats/           nbs.py
  visualization/   signal_plots.py, connectivity_plots.py
scripts/
  build_windows.py, freeze_baseline.py
  preprocessing/   run_preprocessing.py
  exploration/     inventory_raw.py, visualize_data.py, diagnose_occipital_spectra.py
  diagnostics/     demo_edge_effects.py, demo_cv_leakage.py
  training/        train_models.py, train_final_model.py, batch_run_subjects.py
  evaluation/      evaluate_confusion_matrix.py, test_sklearn_models.py
  xai/             run_xai.py, compare_subject_xai.py
  benchmarks/
    feature_based/   benchmark_n_subjects.py, benchmark_cross_validation.py,
                     benchmark_feature_selection.py, benchmark_harmonic_fbcca.py
    neural_networks/ benchmark_eegnet.py, benchmark_compact_cnn.py,
                     benchmark_shallow_convnet.py, benchmark_nn_augmentation.py
    benchmark_window_sweep.py, benchmark_nn_sweep.py, simulate_dynamic_stopping.py,
    pseudo_online.py, benchmark_loso.py, benchmark_loso_warmup.py
  connectivity/
    analysis/        analyze_connectivity.py, analyze_connectivity_cohort.py
    comparison/      compare_connectivity_frequencies.py, test_connectivity_frequency_differences.py
    diagnostics/     check_power_alpha_confound.py
    graph_modeling/  build_graph_dataset.py, benchmark_connectivity_gate.py,
                     benchmark_gnn.py, benchmark_gnn_loso.py
notebooks/         loso_colab.ipynb
tests/             one test module per src module (synthetic data only)
docs/              report/, infographic/, progress_report/  (P23)
mas/               this specification + mas/state/
README.md  RESEARCH_LOG.md  CHANGELOG.md  requirements.txt  environment.yml  Makefile
```

Files and folders that do not exist yet are created by the phase that introduces
them (see the roadmap). `scripts/exploration/inventory_raw.py` and
`scripts/diagnostics/demo_cv_leakage.py` are additions of this rebuild; everything
else mirrors the original project.

## 3. Configuration (`configs/pipeline_config.yaml`)

The config evolves; each version is committed by the phase that introduces it.

**v1 (P01, legacy):**
```yaml
project:
  name: "ssvep-eeg-xai"
  target_conditions: [201, 202, 101, 102, 103, 104, 105]
paths:
  data_raw_dir: "data/raw"
  data_processed_dir: "data/processed"
  figures_dir: "outputs/figures"
  reports_dir: "outputs/reports"
  saved_models_dir: "outputs/saved_models"
channels:
  scalp: ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]   # PO7 hard-excluded (legacy)
  excluded: ["PO7"]
  mark_channel: "MARK"
  auxiliary: ["TIMESTAMP", "FLASHINGTIME"]
preprocessing:
  lowcut_hz: 1.0
  highcut_hz: 60.0
  filter_order: 4
  sub_window_sec: 1.0
  vpp_thresh_uv: 200.0
  std_range: [0.5, 60.0]
  baseline:
    cross_condition: 201
    cue_condition: 202
    stimulus_duration_sec: 5.0
    pre_stim_cross_sec: 2.0
    cue_lookback_sec: 1.0
features:
  psd_range_hz: [5.0, 35.0]
  plotting_range_hz: [1.0, 60.0]
training:
  cv_splits: 5
  random_state: 42
  batch_size: 16
  learning_rate: 0.001
  epochs: 100
```

**P07:** `scalp` = all 8 channels in montage order, `excluded: []`.

**P16 (final):** adds/changes
```yaml
preprocessing:
  highcut_hz: 90.0     # keep harmonics up to 72 Hz
  notch_hz: 60.0       # mains
  notch_q: 30.0
quality:
  vpp_range_uv: [5.0, 120.0]
  std_range_uv: [1.0, 35.0]
  channel_fail_fraction: 0.5
  artifact_block_sec: 0.25
  guard_sec: auto                # = longest filter ringing time
  guard_rel_amplitude: 0.01
  source: both                   # P19: filtered | raw | both
filter_bank:                     # P17
  harmonics:    {enabled: true, n_harmonics: 3, half_width_hz: 1.0, order: 2}
  intermediate: {enabled: true, half_width_hz: 1.0, order: 2}
```

Scripts read paths and thresholds from the config; CLI flags override it. No script
hard-codes an absolute path.

## 4. Engineering conventions

- Run every script **from the repository root as a module** (`python -m
  scripts.benchmarks.feature_based.benchmark_n_subjects`) or as a file; both must
  work (scripts find the root by searching upward for `configs/pipeline_config.yaml`
  and insert it into `sys.path`).
- Every script has `argparse` with a module docstring as `--help` description, sensible
  defaults that reproduce the reference run, `--subjects`, and (where it trains)
  `--device`, `--seed`.
- Subjects are auto-discovered (`^S\d+$`); scripts skip a subject with a printed
  `[-] Skipping <S>: <reason>` instead of crashing.
- Per-subject jobs support `--n-jobs` (joblib) where the original did.
- Library code in `src/` has no side effects at import, no prints except behind
  `verbose`, type hints, and a docstring per public function.
- Console output of every benchmark ends with a cohort summary line and the path of
  the saved CSV. The Runner saves the full console log to
  `reports/logs/<phase>/<script>_<timestamp>.log` together with the command and
  `git rev-parse HEAD`.
- Two-space or four-space indentation is fine; be consistent per file.
- Plots: `matplotlib.use("Agg")`, saved under `outputs/figures/<topic>/`, never shown.

## 5. Scientific invariants (from P11 onward these are blocking)

1. **Trial-grouped splits.** Every split of windows uses `StratifiedGroupKFold(n_splits=5,
   shuffle=True, random_state=seed)` with `groups=trial_ids`. Inner validation splits
   (early stopping) are also grouped by trial. LOSO validation splits never contain the
   test subject; trial ids are offset per subject so groups never collide.
2. **In-fold fitting.** CSP filters, StandardScaler, feature selection, per-fold
   standardization of graph inputs, augmentation (training fold only) are fitted
   inside the fold. Per-window/per-channel z-scoring of raw windows uses only that
   window's own statistics (allowed: it uses no other window).
3. **Shared quality decision.** From P16, every analysis of a subject uses the same
   valid windows and kept channels (`valid_mask`, `channels_kept_idx` from the built
   folder). Scripts may offer `--quality per-script` only for comparison.
4. **Sampling rate.** From P16, `fs` always comes from the file header/metadata (256).
   Legacy reproduction (P02–P15) uses the original hard-coded `fs=250.0` in feature
   extractors and must say so in its report.
5. **Out-of-fold probabilities.** Classifiers produce probabilities for every window
   exactly once (out-of-fold), mapped to the fixed class order.
6. **Smoothing (2.0 s decision).** 2-tap causal average of consecutive window
   probabilities **within the same trial only**: `p̄_j = p_j` at the first window of a
   trial, else `(p_{j-1} + p_j)/2`. Legacy folders define "first window of a trial" as
   `j % 5 == 0` on the clean array (a known approximation); built folders use true
   trial ids, ordered by window offset.
7. **Metrics.** Accuracy (%), balanced accuracy, per-class recall, confusion matrices;
   6-class adds false-activation rate (rest windows predicted as a stimulus) and
   missed-stimulus rate (stimulus windows predicted as rest). ITR (Wolpaw):
   `bits = log2 N + p log2 p + (1−p) log2((1−p)/(N−1))` (0 if `p ≤ 1/N`; drop the
   last term if `p = 1`), `ITR = bits · 60 / T` with `T = window (or decision time) +
   gaze_sec (0.5 s)`.
8. **Permutation tests** permute **whole trials** with matched group window counts
   (P13+). p-values use the +1 pseudo-count: `(1 + #{null ≥ obs}) / (n_perm + 1)`.
9. **Reporting.** Report per-subject tables next to cohort means (between-subject
   variability dominates). Never report a single cohort number alone.

## 6. Output schemas (keep column names exactly)

| CSV | Columns |
|---|---|
| `reports/five_subjects_benchmark.csv` (P06, legacy) | `Subject, Clean Windows, Rejected, 1.0s Acc (%), 2.0s Smoothed (%)` |
| `reports/n_subjects_benchmark[_suffix].csv` | `Subject, Channels Kept, Channels Dropped, Clean Windows, Rejected Windows, [Bank, CSP Bands,] 1.0s Acc (%), 2.0s Smoothed (%)` (+ `1.0s SD, 2.0s SD, CV repeats` with `--cv-repeats>1`; + 6-class columns `Rest Windows, 1.0s BalAcc (%), 2.0s BalAcc (%), 1.0s FalseAct (%), 2.0s FalseAct (%), 1.0s Missed (%), 2.0s Missed (%), 2.0s StimCorrect (%)`) |
| `reports/augmentation_ab_<model>.csv` | `Subject, Clean Windows, 1.0s OFF (%), 1.0s ON (%), 1.0s Delta, 2.0s OFF (%), 2.0s ON (%), 2.0s Delta, Train Acc OFF (%), Train Acc ON (%)` |
| `outputs/reports/<s>_model_evaluation.csv` (P04) | `Subject, Classifier, Accuracy, Recall per Class` |
| `reports/connectivity_cohort_summary[_suffix].csv` | `subject, method, condition, frequency_hz, label, obs_diff, p_one_tailed, significant_uncorrected, n_edges_sig_uncorrected, n_edges_sig_fdr, total_edges, n_channels, channels_dropped, permutation_unit, fdr_backed` (+ from P18: `nbs_threshold, nbs_max_size, nbs_size_fraction, nbs_p, nbs_n_sig_edges, nbs_significant, nbs_size_z<t>, nbs_p_z<t>, n_stim_windows, n_baseline_windows, fs, source`) |
| `reports/connectivity_edges/<S>_<method>.npz` | `channels_kept`, and per condition c: `stim_c, base_c, diff_c, p_c, fdr_c` (+ `nbs_c` from P18) |
| `reports/connectivity_comparison/<m>_frequency_similarity.csv` | `subject, method, freq_a, freq_b, r, p_qap` |
| `…/<m>_node_strength.csv` | `subject, method, condition, frequency, channel, node_strength` |
| `…/<m>_global_delta.csv` | `subject, method, condition, frequency, mean_delta, n_fdr_edges` |
| `…/<m>_split_half_reliability.csv` | `subject, method, condition, frequency, split_half_reliability` |
| `…/<m>_pairwise_tests.csv` | `subject, method, freq_a, freq_b, t_mag, p_mag, d_pat, p_pat, r_obs, n_edges_fdr, n_edges, reliability_ceiling, r_disattenuated, trial_ids_approximate, sig_bh_mag, sig_bh_pat` (+ `nbs_max_size, nbs_p, n_edges_nbs, fs` from P18) |
| `…/power_confound_table.csv` | `subject, condition, frequency, target_snr_db, alpha_change_db, n_stim_windows, n_base_windows, channels_used` |
| `…/power_vs_connectivity_cells.csv` | the above + `mean_delta, method` |
| `reports/connectivity_gate_benchmark.csv` | `subject, set, k_select, repeat, dim, acc_1s, acc_2s` |
| `reports/gnn_benchmark.csv` | `variant, repeat, acc_1s, acc_2s, train_acc, subject` |
| `reports/edge_effects_summary.csv` (P16) | `subject, band, filter, rel_error_edges_pct, rel_error_centre_pct, edge_to_centre_ratio` |
| `reports/window_sweep/summary.csv`, `nn_sweep/summary.csv`, `loso*/summary.csv` | `Subject, Window (s), Method, Windows, Trials, Acc (%), Acc SD, BalAcc (%), ITR (bits/min), Train Acc (%), Runs` (+ `Val Acc (%), Best Epoch`, LOSO adds `2-tap Smoothed (%), Channels`, GNN LOSO adds `Protocol`) |
| `…/predictions.csv` | `subject, window_sec, method, run, trial_id, offset_sec, true, pred, p_101 … p_105` |
| `…/confusion.csv` | `[window_sec,] method, true, pred, count` |
| `reports/dynamic_stopping/{decisions,per_subject,cohort}.csv` | decisions: `subject, method, window_sec, run, trial_id, threshold, true, pred, time_sec, forced` |
| `reports/pseudo_online/summary_<tag>.csv` | `Subject, Trials, Acc (%), Time (s), Forced (%)` or `Missed (%)`, `ITR (bits/min), False act. (%), Windows rejected (%), Window (s), Channels kept, Dropped at check, Train windows, Val acc (%)` |
| `reports/loso_warmup/summary.csv` | `Subject, Warm-up trials, Warm-up windows, Warm-up classes, Warm-up span (s), Scored windows, full (%), warmup (%), none (%)` |

## 7. Testing requirements

`tests/` uses synthetic data only (no recordings in CI). Minimum tests — each was a
real bug or a real requirement in the original project:

| Test | Asserts |
|---|---|
| EBR round-trip | write a synthetic `.ebr` (header + doubles), parse, shapes/channels/fs/marks match; unsupported dtype raises |
| event onsets | single-sample pulses and multi-sample plateaus both give one onset per event |
| window index | 1 synthetic trial → 5 stimulus windows, 2 cross windows, 1 cue window; stride < window gives overlap counts from `windows_per_segment` |
| `build_trial_ids` | contiguous blocks split into chunks; per-label dict lengths; warning on a remainder |
| quality gate | a channel failing in >50 % of windows is dropped; a single bad window is rejected; `vpp_min` pinned in the legacy raw gate |
| no leakage | for every benchmark's split helper: no trial id appears in both train and test |
| CSP | filters shape `(C, 2m)` per class, 50 features for m=1 × 5 bands × 5 classes |
| FBCCA | a clean sinusoid at target k gives the highest score for k |
| coherence bias | two independent noise signals: per-window-averaged coherence ≈0.3; concatenated condition coherence < 0.05; coupled signals > 0.95 |
| PLV/wPLI edge immunity | corrupting the first/last 15 samples of every window changes CSD-based PLV by < 0.01 |
| MVAR | synthetic VAR(p) with distinct coefficients recovered within ~10 % relative error |
| trial permutation split | groups keep whole trials, at most one trial split, sizes match |
| NBS | a planted connected component is found, p small; pure noise gives p ≥ 0.05 in most seeds |
| networks | every CNN/GNN forward pass for 7 and 8 channels and 128/256/512 samples, output `(B, n_classes)`, gradients flow |
| causal filter | chunked `sosfilt` with carried state equals one-shot `sosfilt` on the full signal |
| ITR | known values (e.g. N=5, p=1, T=1.5 s → 92.88 bits/min) |
