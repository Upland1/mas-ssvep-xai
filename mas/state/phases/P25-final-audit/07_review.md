# P25 · 07 · Scientific review

Status: RESULTS REVIEW DONE (APPROVE)
Author: scientific-reviewer
Reads: 00, 02 (settled 2, 6, 7), mas/RULES.md, mas/state/decisions.md, src/, scripts/, tests/ at a4520ec; the original repository through `git ls-tree` / `git show` only (R11, listed below)

P25 changes no code, so the per-rule pre-run table of the template does not apply. This file holds the
P25 audit (tasks 2 and 4, settled point 7). The results review follows after 06_verify.md.

## Leakage audit

Scope: every place in `src/` and `scripts/` that splits windows, trials, subjects or sessions into fitted and
evaluated parts. Enumeration: grep of the splitter names in settled point 2 plus every call site of the split
helpers (`make_splits`, `splits_for`, `grouped_cv`, `legacy_cv`, `loso_split`, `within_splits`,
`split_validation`, `warmup_rows`) and every file with a `.fit(` / `fit_network` / `fit_gnn` / `train_model`
call. Permutation resampling for statistics (P13/P14/P18, `src/features/connectivity/permutation.py`) is R7, not a
fitted/evaluated split, and is out of this table. Every cited test was verified to exist with
`grep -c "^def <name>(" tests/<file>` (every cited name, each count 1; parametrised tests run under the bare name).

Era key: R1 enforced from P11 (legacy `StratifiedKFold` over windows prescribed for P04–P10); R2 always (full-data
fits only for export/visualization; unsupervised test-time normalization only when labelled). Decision
2026-10-26 P11 (5): scripts outside the roadmap's nine stay frozen legacy snapshots.

### A. Split primitives

| # | Split (file:line) | Groups | In-fold fits | Era status | Guarding test |
|---|---|---|---|---|---|
| A1 | `src/preprocessing/dataset/cv_utils.py:96-99` `grouped_cv`; `:109` `make_splits("grouped")` | trial ids (legacy: `build_trial_ids` on pre-gate labels, masked, PF-03; built: `cv_groups`) | n/a (splitter) | enforced (R1) | `tests/test_no_leakage.py::test_leak_free_splitters_share_no_group`, `::test_helper_detects_a_leak`; `tests/test_p11_cv.py::test_grouped_splits_share_no_trial_and_are_stratified_within_one_trial` |
| A2 | `cv_utils.py:112` `make_splits("legacy")` → `src/models/classical/legacy_eval.py:67-69` `legacy_cv`; `legacy_eval.py:162-167` `splits_for` | none (windows) | n/a | LEGACY (by design), reachable with `--cv legacy`, labelled `CV_LABEL` `legacy_eval.py:29`, outputs under `legacy_leaky/` (`cv_utils.py:129-131`) | `tests/test_no_leakage.py::test_legacy_splitters_leak_by_design_and_say_so`; `tests/test_p11_cv.py::test_legacy_mode_is_byte_identical_to_pre_p11_and_writes_under_legacy_leaky` |
| A3 | `src/models/classical/legacy_eval.py:128-137` `oof_space` (consumer of every classical split) | explicit `splits` required (raises without, `:128-130`) | scaler + model in a `Pipeline` per fold; CSP/FBCSP via `fold_matrices` on `tr` only | enforced | `tests/test_p05_feature_benchmark.py::test_fold_matrices_never_see_test_rows`, `::test_oof_pipeline_fits_scaler_on_training_fold_only` |
| A4 | `src/models/cnn/training.py:79-84` `split_validation` (early stopping, used at `:104` by `fit_network`) | trial ids of the TRAINING windows only; first split of `StratifiedGroupKFold(round(1/val_frac))` | normalisation `fit_stats` on fitting windows (`:107`); augmentation on fitting windows; best-val state | enforced (PF-32, P20) | `tests/test_p20_networks.py::test_validation_is_subset_of_training_trials_and_disjoint_from_test`; `tests/test_p20_independent_known_answer.py::test_normalisation_statistics_come_from_fitting_windows_only` |

### B. Era A/B within-subject benchmarks (legacy folders)

| # | Split (file:line) | Groups | In-fold fits | Era status | Guarding test |
|---|---|---|---|---|---|
| B1 | `scripts/benchmarks/feature_based/benchmark_n_subjects.py:201` (also built folders P16–P19, 6-class P17) | `cv_groups` (built; 202 merged with its overlapping 201, `src/io/subject_data.py:195-201`) else reconstructed ids; runtime `assert_no_shared_trials` `:203` | via `oof_space` | enforced, `--cv legacy` labelled | `tests/test_p11_known_answer.py::test_classical_script_default_split_is_grouped_with_true_ids`; `tests/test_p16_flagship_port.py::test_r1_built_cv_groups_never_straddle_a_fold`; `tests/test_p17_benchmark.py::test_six_classes_select_201_and_never_202_and_groups_are_true_ids` |
| B2 | `scripts/benchmarks/feature_based/benchmark_cross_validation.py:90` | trial ids | `oof_space` | enforced, `--cv legacy` labelled | `tests/test_p11_cv.py::test_every_classical_script_uses_trial_grouped_splits`; `tests/test_p11_known_answer.py::test_negative_control_the_spy_sees_the_window_level_split_in_legacy_mode` |
| B3 | `scripts/benchmarks/feature_based/benchmark_feature_selection.py:149` (outer), `:117` (SFS inner) | outer trial ids; inner = training-fold trial ids | ANOVA/MI/SFS on `Xtr` only (`column_sets`) | enforced (PF-01 inner grouped) | `tests/test_p11_known_answer.py::test_feature_selection_sfs_inner_cv_is_grouped_and_shares_no_id`; `tests/test_p11_cv.py::test_sfs_inner_splits_share_no_trial_and_legacy_is_none`; `tests/test_p06_feature_selection.py::test_selection_is_infold_only`; `tests/test_p06_known_answer.py::test_sfs_infold_only` |
| B4 | `benchmark_feature_selection.py:211` (`_sfs_columns`, inner `StratifiedKFold` over windows), `:242` outer | windows (inner), outer per `--cv` | inner selection inside the outer training fold | LEGACY (by design): P06 SFS diagnostic variants only, behind `--sfs-diagnostics` (`:94`, `:299`), labelled in the header (`:23`, `:283`) and registered `legacy` in `tests/test_no_leakage.py` `KNOWN_SPLITTER_FILES` | `tests/test_no_leakage.py::test_every_splitter_in_the_repo_is_registered`; `tests/test_p11_known_answer.py::test_feature_selection_sfs_inner_cv_is_grouped_and_shares_no_id` (asserts no window-level inner split in the reported row) |
| B5 | `scripts/benchmarks/feature_based/benchmark_harmonic_fbcca.py:105`; `scripts/evaluation/evaluate_confusion_matrix.py:160` | trial ids | `oof_space` | enforced, `--cv legacy` labelled | `tests/test_p11_known_answer.py::test_classical_script_default_split_is_grouped_with_true_ids` (both parametrised) |
| B6 | `scripts/diagnostics/demo_cv_leakage.py:90` | both arms by design (before/after demo) | `oof_space` | demo of PF-01, arms labelled from the meta splitter (`:120-122`) | `tests/test_p11_cv.py::test_demo_cv_leakage_columns_mean_row_and_network_section` |
| B7 | `src/models/cnn/eegnet_cv.py:119` (EEGNet, Compact-CNN, ShallowConvNet, A/B: `src/models/cnn/benchmark_common.py:166`, `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py:143`; seed spread `scripts/diagnostics/network_seed_spread.py:76`) | trial ids, runtime assert `:120-121` | per-window z-score (no fitted statistics, `:44-49`); model per fold; augmentation on the training fold (N4) | enforced, `--cv legacy` labelled | `tests/test_p11_networks.py::test_every_network_script_split_shares_no_trial_id`, `::test_legacy_split_does_share_trials_negative_control`, `::test_n4_training_dataset_is_training_fold_and_generator_seeded_in_both_arms`; `tests/test_p11_known_answer.py::test_network_script_default_split_is_grouped_with_true_ids`; `tests/test_p11_seed_spread.py::test_folds_identical_across_seed_bases_and_the_base_changes_training` |
| B8 | `scripts/training/train_models.py:178-180`, `:192` (P04) | windows | whole `Pipeline` cloned per fold | LEGACY (by design), frozen snapshot (decision P11 (5)); labelled `CV_LABEL` `:80`, header `:12` | `tests/test_no_leakage.py::test_legacy_splitters_leak_by_design_and_say_so`; `tests/test_p04_early_models_known_answer.py::test_legacy_cv_splits_equal_stratified_kfold_5_true_42`, `::test_in_fold_scaling_matches_hand_per_fold`, `::test_mutant_scaler_fit_on_all_windows_fails` |
| B9 | `src/models/cnn/spatial_spectral_cnn.py:137-138` (fusion CNN, called by `scripts/training/batch_run_subjects.py:72`) | windows | scalers per training fold (`:139`) | LEGACY (by design), frozen snapshot; labelled `:125`, `:137`, `:151`, `batch_run_subjects.py:6` | `tests/test_p04_early_models_known_answer.py::test_cnn_scalers_fitted_on_training_fold_only`, `::test_mutant_cnn_scalers_fitted_on_all_windows_fails` (these recompute `StratifiedKFold(5, shuffle, 42)` and match the fold scalers, which pins the split) — see note N1 |
| B10 | `scripts/benchmarks/feature_based/benchmark_5_subjects.py:107`; `scripts/evaluation/test_sklearn_models.py:96` (P05) | windows, passed explicitly `splits_for("legacy", …)` | `oof_space` | LEGACY (by design), frozen snapshot; labelled headers `:9` / `:10` | `tests/test_no_leakage.py::test_legacy_splitters_leak_by_design_and_say_so` (`splits_for('legacy')` entry) |
| B11 | `scripts/training/train_final_model.py:62` | none: full-data fit | n/a | R2 exception, export/XAI only, labelled `:1-5` ("fit: full data (export/XAI only; R2 exception)"); same for `extract_fbcsp_features` (`src/features/ssvep/fbcsp_extraction.py:131`, visualization only) | not a split; labelling is the control |
| B12 | `scripts/connectivity/graph_modeling/benchmark_connectivity_gate.py:88` (P15) | pre-gate trial ids, runtime assert | SelectKBest + LDA in `oof_space` | enforced | `tests/test_p15_known_answer.py::test_gate_r1_no_trial_shared_for_every_repeat`, `::test_gate_scaler_is_in_fold_shifted_test_rows_do_not_move_the_others` |
| B13 | `scripts/connectivity/graph_modeling/benchmark_gnn.py:115` (P15) | pre-gate trial ids, runtime assert `:116` | standardizer on training rows; fixed epochs, no validation split | enforced | `tests/test_p15_known_answer.py::test_gnn_r1_no_shared_trial_and_fold_seeds`, `::test_gnn_standardizer_fitted_on_train_rows_in_the_benchmark`; `tests/test_p15_gnn.py::test_splits_of_every_repeat_share_no_trial_ids` |

### C. Era C (built folders, true ids, fs from metadata)

| # | Split (file:line) | Groups | In-fold fits | Era status | Guarding test |
|---|---|---|---|---|---|
| C1 | `scripts/benchmarks/benchmark_window_sweep.py:167` (P20, overlapping windows) | `cv_groups` | CSP + scaler + LDA on `tr` (`lda_fold`); CNN via `cnn_fold` → A4 | enforced | `tests/test_p20_window_sweep.py::test_no_trial_id_shared_between_train_and_test_on_overlapping_windows` (with the window-level negative control), `::test_lda_fold_fits_csp_and_scaler_on_training_rows_only`; `tests/test_p20_independent_known_answer.py::test_cnn_cv_never_puts_a_trial_in_train_and_test_and_validation_inside_training`, `::test_lda_fold_scaler_and_csp_ignore_test_rows` |
| C2 | `scripts/benchmarks/neural_networks/benchmark_nn_sweep.py:109` (P20) | `cv_groups`, runtime assert `:110` | `cnn_fold` → A4 | enforced | `tests/test_p20_independent_known_answer.py::test_nn_sweep_compact_equals_window_sweep_cnn_at_identical_seeds` (per-window identity with C1, whose split is spied) — see note N2 |
| C3 | `scripts/benchmarks/pseudo_online.py:310-323` (P20): train run `--train-session` vs replayed test run | session (OO → mOO) | network, normalisation, channel tier on the training run; label-free channel check on the first 30 s of the test stream (disclosed, `Trials before check`, P20.md:295) | enforced | `tests/test_p20_independent_known_answer.py::test_pseudo_online_stream_probabilities_ignore_mark_and_future_samples` (altering the test stream after 100 s leaves earlier probabilities identical, so nothing of the test run is fitted); `tests/test_p20_online.py::test_pseudo_online_cli_mark_only_for_scoring_channel_check_and_paradigm`, `::test_pseudo_online_channel_check_uses_only_the_first_seconds` |
| C4 | `scripts/benchmarks/benchmark_loso.py:270-274` `loso_split`, used `:519` (P21) | subject; pooled trial ids offset per subject | CSP on `tr` (`:291`); scaler + LDA on `tr` (`:313`); networks A4 with offset groups and an assert that no validation window is from the held-out subject (`:364-367`); `lda_subjnorm` z-scores each subject with its own unlabeled whole-session statistics (`:279-286`) = R2 test-time exception, labelled | enforced | `tests/test_no_leakage.py::test_leak_free_splitters_share_no_group` (`loso_split` entry); `tests/test_p21_loso.py::test_loso_split_refuses_nothing_shared_and_flags_a_leak`, `::test_replacing_the_test_subject_by_a_sentinel_changes_no_fitted_parameter`, `::test_subject_normalization_ignores_the_held_out_labels`, `::test_network_fold_never_sees_the_test_subject_in_training_or_validation`, `::test_pooled_groups_are_unique_per_subject_and_trial_and_the_test_subject_stays_out_of_training`; `tests/test_p21_loso_networks.py::test_validation_windows_exclude_the_held_out_subject_and_the_raw_id_bug_is_caught`, `::test_normalisation_statistics_ignore_the_held_out_subject`; `tests/test_p21_independent_known_answer.py::test_sentinel_in_the_held_out_subject_changes_no_training_side_output`, `::test_labels_of_the_held_out_subject_reach_no_classical_prediction` |
| C5 | `benchmark_loso.py:318-324` `within_splits`, used `:338` (`within_lda`, P22) | the subject's `cv_groups` | `lda_loso_fold` on each fold's `tr` | enforced | `tests/test_no_leakage.py::test_leak_free_splitters_share_no_group` (`within_splits` entry); `tests/test_p22_loso_extensions.py::test_within_splits_never_share_a_trial_and_cover_every_window_once`, `::test_within_lda_is_grouped_by_trial_and_the_window_level_variant_leaks`; `tests/test_p22_independent_known_answer.py::test_within_folds_never_split_a_trial_and_cover_each_window_once`; `tests/test_p23_loso_carryforwards.py::test_within_lda_gets_cv_groups_not_trial_ids_when_they_differ` |
| C6 | `scripts/benchmarks/benchmark_loso_warmup.py:220` (LOSO) and `:71`/`:115` `warmup_rows` (first K trials in recording order) (P22) | subject; warm-up = first K held-out trials, scored only on later trials | CSP on `tr` (`:221`); scaler + LDA on training subjects (`:109-110`); `full` = whole-session test statistics (offline upper bound), `warmup` = first-K unlabeled statistics (online); no test label is an argument (`:104`) | enforced; R2 exception labelled (`Normalization` column) | `tests/test_p22_warmup.py::test_warmup_statistics_ignore_labels_and_every_window_after_k`, `::test_warmup_set_is_the_first_k_in_recording_order_not_in_id_order`, `::test_warmup_with_every_trial_equals_full_exactly`; `tests/test_p22_independent_known_answer.py::test_first_k_stats_are_those_of_the_first_recorded_trials_and_ignore_labels_and_later_windows`; `tests/test_p23_loso_carryforwards.py::test_warmup_csvs_carry_the_normalization_label` |
| C7 | `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py:289` (LOSO), `:533` (within, via `within_splits`), `:171` (early-stopping split) (P23) | subject / the subject's `cv_groups` / training trials | pooled standardizer on `tr` rows (`fold_inputs` `:135-146`); `_subjnorm` = per-subject unlabeled whole-session statistics (R2 exception, labelled; refused under `within`); validation never holds the held-out subject (assert `:293-295`) | enforced | `tests/test_p23_gnn_loso.py::test_pooled_sentinel_in_heldout_subject_leaves_training_and_weights_bit_identical`, `::test_sentinel_test_detects_statistics_fitted_on_all_rows`, `::test_validation_never_contains_heldout_subject_and_is_trial_grouped`, `::test_within_never_splits_a_trial_covers_every_window_once_and_window_level_cv_is_caught`, `::test_within_refuses_subject_norm_and_default_out_dirs`; `tests/test_p23_independent_known_answer.py::test_validation_excludes_heldout_subject_and_splits_by_trial_in_every_loso_fold`, `::test_strings_normalization_protocol_data_source_in_loso_and_within` |

### Result

- Every split has a guarding test, and every legacy split is one the era matrix prescribes (R1 P04–P10, kept as
  `--cv legacy` or as a frozen P04/P05 snapshot under the P11 (5) decision), labelled in code and outputs.
- No `.fit` outside a training fold was found except the two labelled R2 exceptions (export/visualization, B11) and
  the labelled unsupervised test-time normalizations (C4 `lda_subjnorm`, C6 `full`/`warmup`, C7 `_subjnorm`).
- The registry guard `tests/test_no_leakage.py::test_every_splitter_in_the_repo_is_registered` covers every file that
  imports an sklearn splitter (7 files; `grep` above finds the same 7).

Non-blocking notes:

- **N1.** The fusion-CNN legacy splitter (B9) is inline and not an entry of the `LEGACY` dict in
  `tests/test_no_leakage.py`. Its identity is pinned indirectly (fold scalers matched to recomputed
  `StratifiedKFold(5, shuffle, 42)` training folds), but no test asserts that it leaks, as the registry does for the
  other legacy splitters. No number depends on this. It is a coverage gap in a frozen snapshot only.
- **N2.** The NN-sweep split (C2) has no spy test of its own. It is guarded by the runtime assert and by per-window
  probability identity with the window-sweep CNN cell, whose split and validation are spied (C1). This is accepted
  as a guard: equal probabilities at identical seeds require identical training sets.

## Module diff

R11 consultation to verify finished, passing work (P25 task 4, `REFERENCE_POLICY after-attempt`). Access was only
through `git -C reference/ssvep-eeg-xai ls-tree -r --name-only <branch>` and `git … show <branch>:<path>` piped to
`grep` for `def`/`class`/`add_argument` lines (one `show … | sed -n 60,70p` for the method tuples, one heading grep of
the notebook). Nothing was written inside `reference/`. No code was copied. The 12 consultations are logged in
`mas/state/scratch/reference_access.log` at 2026-10-29T20:58:14, 20:58:27, 20:58:29, 20:59:00, 20:59:04, 20:59:08,
20:59:19, 20:59:28, 20:59:33, 20:59:43, 20:59:47 and 20:59:52 (scientific-reviewer). These were:

1. `ls-tree` of `main`, `feature/window-size-online-detection` and `test/GNN-testing-LOSO`.
2. `show main:scripts/benchmarks/benchmark_loso.py`, `show test/GNN-testing-LOSO:` and
   `show feature/window-size-online-detection:` of the same file.
3. `show feature/window-size-online-detection:scripts/benchmarks/benchmark_loso_warmup.py`.
4. `show test/GNN-testing-LOSO:scripts/connectivity/graph_modeling/benchmark_gnn_loso.py`.
5. `show main:` of `src/preprocessing/dataset/cv_utils.py`, `src/io/subject_data.py`,
   `src/preprocessing/window_quality.py`, `src/features/connectivity/connectivity_extraction.py`,
   `scripts/benchmarks/pseudo_online.py`, `scripts/benchmarks/simulate_dynamic_stopping.py`,
   `scripts/xai/run_xai.py`, `src/preprocessing/dataset/augmentation.py` and `scripts/build_windows.py`.
6. `show test/GNN-testing-LOSO:notebooks/loso_colab.ipynb`.

Two earlier attempts (a branch listing and a redirect of `ls-tree` output to the scratchpad) were blocked by the
guard and did not run.

File-level result. `main` has 65 tracked files (59 `.py`, 1 notebook, 1 config, 4 environment and docs files). Each branch has the 65
files of `main` plus one more:
- `feature/window-size-online-detection` adds `scripts/benchmarks/benchmark_loso_warmup.py`;
- `test/GNN-testing-LOSO` adds `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py`.

Every original path exists in the rebuild (checked with `[ -e path ]` for all 61 code, notebook and config paths)
except one: `scripts/benchmarks/benchmark_nn_sweep.py`, which the rebuild has at
`scripts/benchmarks/neural_networks/benchmark_nn_sweep.py` (note N3).

| Capability / module | Original (branch:path) | Rebuild path | Status | Note |
|---|---|---|---|---|
| EBR parsing | main:src/io/ebr_parser.py | src/io/ebr_parser.py | both | |
| Raw inventory | — | scripts/exploration/inventory_raw.py | missing in original | P00 addition |
| Unified loader (`load_subject`, `is_built`, `discover_subjects`) | main:src/io/subject_data.py | src/io/subject_data.py (+ src/io/channels.py) | both | rebuild adds the `cv_groups` key (202 merged with its overlapping 201, PF-13) and a trial-order check |
| Legacy preprocessing / windowing | main:scripts/preprocessing/run_preprocessing.py, main:src/preprocessing/windowing.py | same paths + src/preprocessing/dataset/legacy_windows.py | both | |
| Filters, signal QC | main:src/preprocessing/signal/{filters,quality_check}.py | same | both | |
| Shared quality gate (ringing guard, artifact mask, subject gate) | main:src/preprocessing/window_quality.py | src/preprocessing/window_quality.py (+ src/features/ssvep/window_mask.py) | both | rebuild adds `quality_params_from_config`, explicit-threshold checks (R5) |
| Continuous build, sweep folders, banks | main:scripts/build_windows.py | scripts/build_windows.py | both | same CLI surface (`--filter-mode`, `--guard-sec`, `--quality-source`, `--window-sec`, `--stride-sec`, `--banks`) |
| v1 freeze | main:scripts/freeze_baseline.py | scripts/freeze_baseline.py | both | |
| Trial ids, grouped CV helpers | main:src/preprocessing/dataset/cv_utils.py (`build_trial_ids` only) | src/preprocessing/dataset/cv_utils.py | both | rebuild adds `grouped_cv`, `make_splits`, `assert_no_shared_trials`, `output_dir` |
| Trial-aware 2-tap smoothing | inline in scripts | src/preprocessing/dataset/smoothing.py | both | module only in rebuild |
| PSD / harmonic PSD / FBCCA / FBCSP features | main:src/features/ssvep/{psd,fbcca,fbcsp}_extraction.py | same + harmonic_psd.py, spectral_power.py | both | |
| Feature selection | main:src/features/selection/feature_selection.py | same | both | |
| Classical model suite, evaluation helpers | main:src/models/classical/sklearn_models.py | same + legacy_eval.py, feature_spaces.py, benchmark_runner.py, rest_metrics.py | both | helpers only in rebuild |
| Early ML / XAI / final models | main:scripts/training/{train_models,train_final_model,batch_run_subjects}.py, main:scripts/xai/{run_xai,compare_subject_xai}.py | same | both | |
| Classical benchmarks (n subjects, CV, selection, harmonic FBCCA, confusion, sklearn suite) | main:scripts/benchmarks/feature_based/*.py, main:scripts/evaluation/*.py | same | both | |
| P05 five-subject feature benchmark | — | scripts/benchmarks/feature_based/benchmark_5_subjects.py | missing in original | frozen legacy snapshot |
| CNNs (EEGNet, Compact, Shallow, fusion, CCNN) | main:src/models/cnn/{eegnet,compact_cnn,shallow_conv_net,spatial_spectral_cnn,ccnn}.py | same + eegnet_cv.py, training.py, benchmark_common.py | both | shared training loop as modules only in rebuild |
| Network benchmarks, augmentation | main:scripts/benchmarks/neural_networks/*.py, main:src/preprocessing/dataset/augmentation.py | same | both | |
| Parameter counts | — | scripts/benchmarks/neural_networks/count_parameters.py | missing in original | |
| Window sweep, NN sweep, dynamic stopping | main:scripts/benchmarks/{benchmark_window_sweep,benchmark_nn_sweep,simulate_dynamic_stopping}.py | scripts/benchmarks/benchmark_window_sweep.py, scripts/benchmarks/neural_networks/benchmark_nn_sweep.py, scripts/benchmarks/simulate_dynamic_stopping.py | both | N3 path |
| Pseudo-online detector | main:scripts/benchmarks/pseudo_online.py | scripts/benchmarks/pseudo_online.py + src/online/causal_filter.py | both | same options (train/test session, threshold, skip, min-val-acc, fallback, check-sec, rest class); `--gaze-sec` is a constant 0.5 in the rebuild |
| LOSO classical + networks | main:scripts/benchmarks/benchmark_loso.py (`fbcca`, `lda`, `lda_subjnorm`, `ccnn`, `compact`, `eegnet`) | scripts/benchmarks/benchmark_loso.py | both | rebuild adds resumable per-fold store with config/head checks; `--gaze-sec` constant |
| Within-subject LDA reference in LOSO | feature/window-size-online-detection:scripts/benchmarks/benchmark_loso.py (`within_lda`) | scripts/benchmarks/benchmark_loso.py (`within_lda`) | both | absent in `main` and the GNN branch. The original's docstring says it returns mean probabilities over repeats; the rebuild stores repeat-0 probabilities and per-repeat accuracies (P22 decision). Read from def/docstring lines only |
| Channel spec `common`/`all`/names | feature/window-size-online-detection:benchmark_loso.py (`--channels` nargs) | benchmark_loso.py, benchmark_loso_warmup.py, benchmark_gnn_loso.py | both | `main` and GNN branch take `common`/`all` only |
| LOSO warm-up (online normalization) | feature/window-size-online-detection:scripts/benchmarks/benchmark_loso_warmup.py | scripts/benchmarks/benchmark_loso_warmup.py | both | same K default list role; rebuild adds the recording-order file and Std guard |
| GNN LOSO / within | test/GNN-testing-LOSO:scripts/connectivity/graph_modeling/benchmark_gnn_loso.py | same path | both | the original exposes `--hidden`, `--layers`, `--dropout`, `--gaze-sec` as options, which the rebuild fixes at R-8 values (32, 2, 0.3). Default `--norm` differs: original both, rebuild `pooled`. The rebuild adds `--only-test`, `--only-fold`, `--threads`, `--partial-mean`, `--config` |
| Colab notebook | main / test/GNN-testing-LOSO:notebooks/loso_colab.ipynb | notebooks/loso_colab.ipynb | both | same section plan 1–12 incl. 10b GNN; rebuild splits networks and GNN into one method per cell (P23 fix) |
| Coherence, PLV/wPLI, PDC, permutations, BH | main:src/features/connectivity/connectivity_extraction.py (single module) | src/features/connectivity/{connectivity_extraction,phase_connectivity,mvar_pdc,permutation,comparison}.py | both | rebuild split into modules; adds aligned-segment coherence, window-permutation demo split, QAP, split-half reliability |
| NBS | main:src/stats/nbs.py | src/stats/nbs.py | both | |
| Connectivity analysis / comparison / alpha confound scripts | main:scripts/connectivity/{analysis,comparison,diagnostics}/*.py | same | both | |
| Connectivity bug demos (coherence bias, Hilbert edges, MVAR slicing) | — | scripts/connectivity/diagnostics/demo_{coherence_bias,hilbert_edges,mvar_slicing}.py | missing in original | P12/P13 diagnostics |
| Graph features, inputs, GNN model, gate, P15 GNN, graph dataset | main:src/features/connectivity/{connectivity_graph_features,graph_inputs}.py, main:src/models/graph/connectivity_gnn.py, main:scripts/connectivity/graph_modeling/{build_graph_dataset,benchmark_connectivity_gate,benchmark_gnn}.py | same + src/features/connectivity/{graph_dataset,graph_features_subject}.py | both | cache with code fingerprint and Era C in-memory features only in rebuild |
| Edge-effect demo | main:scripts/diagnostics/demo_edge_effects.py | same | both | |
| CV-leakage demo, v1/v2 comparison, network seed spread | — | scripts/diagnostics/{demo_cv_leakage,compare_v1_v2,network_seed_spread}.py | missing in original | P11/P16 diagnostics |
| Exploration figures, occipital spectra | main:scripts/exploration/{visualize_data,diagnose_occipital_spectra}.py | same | both | |
| Plotting | main:src/visualization/{signal_plots,connectivity_plots}.py | same | both | |
| One-command reproduction | — | Makefile | missing in original | P24 |
| Synthetic test suite | — (no `tests/` on any branch) | tests/ (81 `test_*.py` files) | missing in original | |

No capability of the three original branches is missing in the rebuild. The only differences are the CLI options
noted above (`--gaze-sec`, and the GNN `--hidden`/`--layers`/`--dropout`), which the rebuild keeps as constants at
the original defaults.

- **N3 (non-blocking).** `benchmark_nn_sweep.py` lives in `scripts/benchmarks/neural_networks/`, while
  `mas/02_REQUIREMENTS.md` §2 (line 52), the roadmap P20 run line (`mas/03_ROADMAP.md:766`) and the original put it in
  `scripts/benchmarks/`. The P20 plan chose this path (`mas/state/phases/P20-detection-online/02_plan.md:186`), and the
  Makefile follows it (`Makefile:269`). This is a layout difference only and affects no result. P25.md should list
  it, and the orchestrator may record it in decisions.md as an accepted layout deviation.

## Settled point 7: ruling

1. **P24 A-5 (p19 clone runtime 10.2 min against 2.5 min recorded).** I accept the plan's reading. The acceptance
   line "no unexplained deviations" covers results (R-x targets and regenerated outputs), not wall time. A-5 has no
   effect on any result: both p19 roots compared identical, 70/70 `.npy` sha256 for `processed_continuous_p19_raw`
   and for `_p19_both` (P24 `06_verify.md:56`), and the run stayed under the stop rule (P24 `07_review.md:276`).
   P25.md must call it "unexplained runtime observation, results identical", never "explained", and must keep it
   out of the R-x deviation table.
2. **Open questions, not deviations.** These change no reported number, or they concern verification coverage
   rather than a result:
   - the Colab notebook sections that were never run end to end. P21 accepted the documented manual steps, and the
     T4 top-to-bottom run is still open (decisions 2026-10-28 P21 gate). This is a verification gap, so P25.md says
     the sections are untested on Colab;
   - P17 C-d (harmonic attribution not tested; the published wording already avoids it) and P17 C-e (an optional
     metric);
   - the P22 `within_lda` `Data source` label in the old main-tree CSVs. This is string only: the numbers are equal
     and the make-all copies carry "within-subject" (P24 A-2).
3. **Carry-forwards.** These count as open questions only if each one is listed with its owner and the statement
   "changes no published number". A carry-forward that would change a published value if done is a deviation and
   needs its decisions row. The scribe tags every carry-forward this way in P25.md. I found none of the second kind
   among those named in settled point 7.

Verdict: PASS

No finding needs a fix round. N1–N3 are non-blocking and go to the P25.md open-items list (owners: N1
synthetic-tester, N2 synthetic-tester, N3 orchestrator for the decisions row).

## R-13 ruling

Scope: `06_verify.md` reason 2 (split-half reliability cells outside ±0.05: 5 of 25 coherence and 14 of 25 wPLI;
coherence pairwise magnitude count 10 against 6). I read `mas/04_REFERENCE_RESULTS.md` (tolerance rules and R-13),
`mas/03_ROADMAP.md` P14 (lines 525–550), `mas/state/reports/P14.md` §1, §4.2–§4.4, §4.6, §4.12, §5 and §9,
`mas/state/decisions.md` rows 123–126, `src/features/connectivity/comparison.py:206–237` and
`scripts/connectivity/comparison/test_connectivity_frequency_differences.py:113–160, 267–271`. I changed no code and
ran nothing on recordings. All numbers below come from the commands shown, which read the CSVs only.

### 1. Kind of target

R-13 is a **mixed** target. Two documents govern it:

- The roadmap P14 acceptance line says "no fixed numeric target; compare qualitatively with R-13". This is
  the phase acceptance, and P14 was judged on it (decisions row 125, D-1).
- The tolerance table at the top of `mas/04_REFERENCE_RESULTS.md` still applies per kind of number.
  "Descriptive statistics (r, SNR dB, reliability) ±0.05, ±0.5 dB" names reliability explicitly. "Permutation
  statistics (Monte Carlo)" asks for the same qualitative pattern.

The roadmap does not override that table for P25 acceptance 4 ("every R-x row within tolerance or explained").
P14.md §1 and §9 call R-13 "qualitative only, with no numeric tolerance" and report "Deviations from numeric
references: none". That wording is too broad. It held for P14's gate, but it leaves the cell-level reliability
differences outside a band that the reference file sets, with no signed explanation. This is the gap the verifier
found. My ruling for each part:

| R-13 part | Kind | Rule applied | Status |
|---|---|---|---|
| Global mean delta (coherence, wPLI) | deterministic | ±0.05 | W: max abs difference 0.0005 (`06_verify.md` A) |
| Target SNR, alpha change | deterministic | ±0.5 dB | W: 0.004 / 0.005 dB (`06_verify.md` A) |
| Frequency similarity (QAP r, share p < .05) | descriptive r, QAP Monte Carlo share | r ±0.05; share qualitative | coherence: arithmetic mean 0.5354 vs 0.54 (W), Fisher mean 0.629 (aggregation-convention ambiguity, P14 D-4, open question for Sebastian); wPLI: 0.1429 vs 0.14 (W); shares 0.66 / 0.32 vs 64 % / 32 % |
| Split-half reliability cells | descriptive, but **a random-split Monte Carlo estimate** | ±0.05, numeric; deviations need a signed explanation | out of band in 19 of 50 cells. **Explained** below (E, signed here) |
| Pairwise magnitude / pattern counts | permutation Monte Carlo | same qualitative pattern; by analogy to the FDR-total rule, ±25 % or ±5 | coherence 10 / 1 vs 6 / 1 (difference 4 ≤ 5); wPLI 6 / 2 vs 6 / 2. W by analogy; pattern holds |

### 2. Qualitative checks (all hold)

These were recomputed in this review from `reports/connectivity_comparison/{coherence,wpli}_split_half_reliability.csv`
and `{coherence,wpli}_frequency_similarity.csv`:

```
.venv/bin/python -I -c "<median, count >=0.75, count <=0 of split_half_reliability; tanh(mean(arctanh r)), mean r,
                         share p_qap<.05 of frequency_similarity; per method>"
coherence median 0.9239 >=.75 20 <=0 2 sim fisher 0.629 arith 0.5354 share p_qap<.05 0.66
wpli median 0.5165 >=.75 4 <=0 3 sim fisher 0.1629 arith 0.1429 share p_qap<.05 0.32
```

- E1, coherence similarity > wPLI similarity on both the mean r and the share: 0.629 / 0.66 against
  0.163 / 0.32. Holds (R-13: 0.54 / 64 % against 0.14 / 32 %).
- E2a, coherence median reliability > wPLI median: 0.9239 against 0.5165. Holds (R-13 medians 0.92 / 0.54,
  P14.md §4.3).
- E2b, more coherence cells ≥ 0.75: 20 against 4. Holds (R-13 22 / 3).
- E2c, wPLI has non-positive cells and coherence has fewer: 3 against 2. Holds with a margin of 1 (R-13 3 / 0).
- E2d, the lowest coherence cells are the in-alpha cells of S01 and S02 (S01 10.91, S02 10.91, S02 8.57 Hz).
  Holds (the same three cells are R-13's lowest: 0.02, 0.34, 0.42).
- E3, p_mag count ≥ p_pat count (`{coherence,wpli}_pairwise_tests.csv`, final): coherence 10 ≥ 1 and wPLI 6 ≥ 2.
  Holds.
- E4 and E5 (SNR, alpha; `power_confound_table.csv`): equal to R-13 within 0.005 dB. Hold.
- Rank agreement of the reliability cells with R-13 (Spearman over 25 cells): coherence 0.894, wPLI 0.928
  (command in §3).

### 3. Cause of the split-half cell differences

**Not Era, fs or data source.** P14 and the original used the same source: legacy 7-channel OO windows, fs-250
axis, per-script P07 gate (P14.md, Data source). The quantities computed by deterministic estimates on the same
windows and baselines match R-13: global delta within 0.0005 over 50 cells, SNR and alpha within 0.005 dB over 50
cells. A difference in windows, fs, gate, band or baseline would show up in these. It does not. So no recorded
Era/fs/data-source cause applies, and none is claimed.

**The cause is the random split sample.** Each reliability cell is the Fisher mean over 10 random halvings of the
stimulus trials and the baseline trials (`comparison.py:218–234`). In this rebuild every cell takes its seed from
`derive_seed(random_state, subject, method, condition, "splithalf")`, which hashes the keys with crc32 (`src/features/connectivity/permutation.py:50–53`,
`test_connectivity_frequency_differences.py:159–160`). The P14 plan chose this seed scheme (decisions row 123), and
P14 consulted no reference code (P14.md §8). The splits therefore cannot equal the original's, and each cell is an
independent draw of a 10-split estimate. The pattern of the differences is the one sampling variability predicts, not
the one an implementation bias predicts:

```
.venv/bin/python -I -c "<per cell: ours from <m>_split_half_reliability.csv minus the R-13 value (copied from
                         mas/04_REFERENCE_RESULTS.md R-13); count |d|>0.05 split by R-13 value >= 0.75; signs; Spearman>"
coherence n>0.05 5 mean signed -0.015 n pos 14 n neg 11 spearman 0.894
coherence ref>=0.75: cells 22 n>0.05 2 max 0.1 | ref<0.75: cells 3 n>0.05 3 max 0.343
wpli n>0.05 14 mean signed 0.018 n pos 13 n neg 12 spearman 0.928
wpli ref>=0.75: cells 3 n>0.05 0 max 0.017 | ref<0.75: cells 22 n>0.05 14 max 0.498
```

1. **The deviations sit in the low-reliability cells.** Of the 19 out-of-band cells, 17 have an R-13 value below
   0.75. Among the 25 cells with an R-13 value ≥ 0.75, only 2 are out of band: coherence S03 10.91 Hz (0.68 vs 0.78)
   and S05 24 Hz (0.891 vs 0.84, 0.001 beyond the edge). Their maximum difference is 0.10. Low split-half r has the
   largest split-to-split spread. Spearman-Brown `2r/(1+r)` then amplifies it, with slope 2 at r = 0 against
   about 0.55 at r = 0.9. At r ≤ 0 the formula is switched off, which adds a discontinuity: S02 wPLI 10.91 Hz is
   −0.252 against −0.75, and S05 wPLI 15 Hz is −0.198 against 0.10.
2. **The differences have no direction.** Signs split 14 / 11 (coherence) and 13 / 12 (wPLI), with mean signed
   differences of −0.015 and +0.018. The plausible implementation differences would each push every cell the same
   way. Splitting windows instead of trials, leaving the baseline unsplit, or applying Spearman-Brown per split would
   all inflate the estimate. Using arithmetic instead of Fisher averaging would lower it.
3. **The ordering is kept.** The rank correlation with R-13 is 0.894 (coherence) and 0.928 (wPLI). Every E2
   criterion holds.
4. **The worst cells are the weakest signals.** wPLI S02 contributes 5 of the 14 wPLI out-of-band cells. That
   subject's wPLI row has the smallest largest-magnitude global delta of the five subjects (−0.024 to 0.122), and its in-alpha SNRs are below
   0.5 dB (R-13 SNR table). The S02 trial ids are also approximate (P11 D-2). The rebuild and the original therefore
   use different trial groupings in that subject, which is a second, recorded source of split differences there.

**Signed explanation (`mas/04_REFERENCE_RESULTS.md`, tolerance rules).** I accept the 19 split-half cells
outside ±0.05 as a **Monte Carlo deviation**. The split draws cannot match the original's (rebuild-specific
seed stream, decisions row 123). Every deterministic input matches. The differences are confined to low-reliability
cells, show no direction, and keep the ordering. The cell values support no conclusion that the reference values
would change. P14.md §4.3 qualified each finding with the 10-split caveat, and every E2 check holds. P14 D-4's
"two non-positive coherence cells" item falls under the same explanation: S01 −0.163 against 0.02, and S02 −0.003
against 0.34, both cells with R-13 values below 0.35.

**Status of the explanation: probable, from the pattern. It is not demonstrated by seed bases.** If the orchestrator
wants it demonstrated, the confirmatory diagnostic needs no code change. The verifier runs it in about 15 min, and it
writes only suffixed outputs (`test_connectivity_frequency_differences.py:267–271`):

```bash
for B in 1 2 3 4 5; do
  .venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences \
    --methods coherence wpli --random-state $B --permutations 50 --n-jobs -1 --out-suffix diag_r13_rs$B
done
```

Pre-committed reading. Take the 19 cells, with base 42 (the final CSVs) plus bases 1–5, for 6 draws per cell. If
the explanation holds, an R-13 value falls inside the per-cell [min, max] of the 6 draws with probability 5/7 per
cell, so about 13.57 of 19 cells are expected inside. The confirmation rule is **≥ 10 of 19** (P(≤ 9) = 0.0233 under
the explanation). The explanation is **refuted** if **≤ 6 of 19** cells fall inside and the outside cells share one
sign (P(≤ 6) = 0.00036). A refutation is then an implementation difference in the split-half estimator, owned by
connectivity-stats, and P14 D-4 reopens. A count of 7–9 is inconclusive: the deviation stays accepted as probable,
with that wording. Only the split-half CSVs of these runs are read. Their p-values at 50 permutations are not used.
Command for the thresholds: `.venv/bin/python -I -c "from scipy.stats import binom; p=5/7;n=19;
print(round(n*p,2), round(binom.cdf(9,n,p),4), round(binom.cdf(6,n,p),5), round(1343*50/500/60,1))"` →
`13.57 0.0233 0.00036 2.2`. The last value is the minutes per base for the pairwise part, scaled from P14's
1343 s at 500 permutations.

### 4. Pairwise magnitude count (coherence 10 against 6)

Permutation p-values fall under the Monte Carlo row, and that row grades the qualitative pattern. The pattern (E3,
p_mag count ≥ p_pat count, and pattern counts 1 and 2 equal to R-13) holds. The count difference of 4 is inside the
"±5" absolute band, applied here by analogy to the FDR-total rule. Six coherence cells have p < 0.015, which equals
R-13's 6. The surplus is four cells at p = 0.029–0.042 (`coherence_pairwise_tests.csv`, sorted `p_mag`: 0.001,
0.001, 0.002, 0.007, 0.008, 0.014, 0.029, 0.035, 0.039, 0.042, 0.051, …). A second cause is likely and partly
recorded. The exchangeability null was designed in this rebuild (decisions rows 123–124) and was found to be
off-centre (P14 D-2). The original's null construction is unknown. Permutation noise alone (SE about 0.009 at
p = 0.04 and 500 permutations) is unlikely to move all four cells above 0.05. I therefore rule the count **within
the analogous band and pattern-consistent**, with the null design named as a documented ambiguity, not as a fault.

### 5. Verdict on reason 2

Reason 2 **does not stand** as an unexplained deviation. R-13's deterministic parts are within tolerance. Its
qualitative criteria all hold (§2). The split-half cells are a reviewer-signed Monte Carlo deviation (§3). The
pairwise count is within the analogous band (§4). For acceptance 4 this becomes "E", given two conditions:

- **Orchestrator:** add a `decisions.md` row recording the accepted deviation. The tolerance rules require
  it, and the text above is its content. Also decide whether to run the optional diagnostic in §3; if it runs, its
  reading binds.
- **Scribe:** P25.md must not repeat P14.md's "no numeric tolerance" or "Deviations from numeric references: none".
  It states "R-13 split-half: 19 of 50 cells outside ±0.05, accepted Monte Carlo deviation (P25 R-13 ruling),
  probable, not seed-base demonstrated" (or the diagnostic's result), and keeps the Fisher-vs-arithmetic similarity
  question open for Sebastian.

No owner or code fix is required for R-13. Reason 1 (R-8 CCNN count) is unaffected by this ruling and stays
with deep-learning.

## Results review

Written after fix round 1; see "Results review (after fix round 1)" at the end of this file.

## Questions

## Fix round 1 audit (CCNN)

Scope: `03_changes_deep-learning.md` (Status READY, 1a848fa); the code diff, which landed in 987742b (a commit
labelled `docs:`; shared-index accident, recorded in decisions.md 308a610 and the squash list); `mas/03_ROADMAP.md`
P20 task 3; `mas/04_REFERENCE_RESULTS.md` R-8; decisions.md rows 160c2bc and 308a610. No file was changed by me
except this section.

### 1. Layout, tests, consumers

**Layout: matches the roadmap, R-8 and the original exactly.**
- Roadmap P20.3 `[real | imag] / T`: `spectrum` returns `torch.cat([z.real, z.imag], dim=-1).unsqueeze(1)`, one
  map `(B, 1, C, 2·n_bins)`, real at `k`, imag at `n_bins + k` (`src/models/cnn/ccnn.py:43–46`). Spatial
  Conv2d(1 → F, (C, 1)) and spectral Conv2d(F → F, (1, 10)), both with bias, BN/ReLU/Dropout after each, Linear on
  `F·(2·n_bins − K + 1)` (lines 37–41).
- R-8 count, instantiated (own):
  `.venv/bin/python -c "...count(New(5,C,256,fs=256)), count(Old(5,C,256,fs=256))..."` (old class exec'd from
  `git show 987742b^:src/models/cnn/ccnn.py`, nothing written) → `7 new 27977 old 14817`, `8 new 32309 old 17285`.
  Both equal R-8 (27,977 / 32,309), exact tolerance. Old spectrum shape `(1, 2, 3, 189)`, new `(1, 1, 3, 378)`.
- Count-equivalent alternative excluded: an interleaved `[r0, i0, r1, i1, …]` map has the same count, so the count
  alone does not fix the layout. The roadmap notation and the block-position test do. R11 verification of the finished,
  passing implementation (logged in `reference_access.log`): `git show fde4b5a:src/models/cnn/ccnn.py` in the
  reference repo, lines 33, 39, 50–51 (read through `grep`/`sed`, no file opened in the tree): `nn.Conv2d(1, nf,
  kernel_size=(n_channels, 1))`, `nn.Conv2d(nf, nf, kernel_size=(1, spectral_kernel))` (default bias), and
  `torch.cat([z.real, z.imag], dim=-1)`: block concatenation, convolutions with bias. Same structure. The spectral
  kernel crosses the real/imag junction at positions 180–197. The original does the same (its Linear width comes
  from the same 369 positions), so this is by design, not a defect.
- B004 scope: the bias-free rule is written for the first R-8 table ("every convolution followed by BatchNorm has
  `bias=False` (EEGNet, Compact-CNN, ShallowConvNet …, DualBranchFusionCNN …)"). The Era-C table is "verified by
  instantiating the original classes", and the original CCNN keeps conv biases. The ruling in decisions 160c2bc is
  correct.

**Tests (R6): known-answer, and they fail on the old code.**
- `test_ccnn_parameter_count_matches_r8` pins 27,977 / 32,309, copied from R-8. That is an external answer, not one
  derived from the code. Old code gives 14,817 / 17,285, so it fails.
- `test_ccnn_single_map_real_then_imag_layout` uses a sine of amplitude A, whose answer is imag −A/2 at `n_bins + k`,
  real ≈ 0 at `k`, `in_channels == 1`. It fails on the old shape `(B, 2, C, n_bins)`.
- `test_ccnn_spectrum_known_answer` (cos: real A/2 at `k`) and the independent `test_ccnn_spectrum_bin_scaling_and_nfft`
  (4 parametrised cases, shape assertion) also fail on the old layout. They keep their analytic answers.
- `test_ccnn_shape_nfft_bins_and_params` uses a closed formula, so it is a consistency check, not an independent
  answer. The R-8 pin covers that.
- Own run: `.venv/bin/python -m pytest -p no:cacheprovider -q tests/test_p20_networks.py
  tests/test_p20_independent_known_answer.py -k ccnn` → 12 passed. I did not re-verify the full-suite claim (1571
  passed). The verifier's clean-checkout suite run binds (G-0).

**Consumers.** `git grep -i ccnn -- src scripts Makefile notebooks` shows that `CCNN` is built only in
`src/models/cnn/training.py:50–51` (`model_factory`). That factory is reached by `benchmark_nn_sweep`,
`benchmark_loso` and `pseudo_online`. None of them reads `spectrum`, the input shape or a parameter count, except the
nn_sweep `Params` column, which will change (G-6).
- `benchmark_window_sweep.py` `cnn` = `compact_eegnet` only (`CLI_METHODS`, line 73). The handoff's claim that it is
  unaffected holds.
- `simulate_dynamic_stopping` reads only `reports/window_sweep/predictions.csv` (Makefile 270, 274). The claim that it
  is unaffected holds.
- The GNN harnesses (P22–P23) have no CCNN hit.
- `bb9c091..HEAD` changes only `ccnn.py` and `pseudo_online.py` (+3) in src/scripts/configs/Makefile
  (`git diff --stat`). So every non-CCNN output stays covered by the P24 make-all reproduction.

**The handoff's run plan is wrong in three places. Do not follow it. The G-items below replace it.**
1. `benchmark_nn_sweep` is **not resumable and has no `--overwrite`** (`--help` flags: config, data-root, device,
   filter-mode, max-epochs, max-folds, models, no-augment, out-dir, patience, repeats, seed, stride, stride-sec,
   subjects, windows). `main` writes `summary.csv`, `folds.csv`, `predictions.csv` and `confusion.csv` from this
   invocation's rows only (`benchmark_nn_sweep.py:204–211`). So `--models ccnn` into `reports/nn_sweep` would
   **delete the compact_eegnet and eegnet rows**.
2. Deleting only the CCNN folds and rerunning `--methods ccnn` into an existing LOSO dir **silently drops every
   other method's rows**. The P21 folds were saved before 271a1f4 (P23) and lack the keys `n_windows_train`,
   `build_git_commits`, `config_hash` and `git_dirty`. Saved key list of `reports/loso_w1_s01-s05/folds/lda__test-S01.npz`
   (own): channels, channels_mode, classes, cohort, data_root, fs, git_head, hyper, method, n_windows_test, quality,
   seed, stride_sec, test_subject, train_subjects, trial_offset, window_sec. `config_diff` is therefore non-empty for
   every old fold. `build_summary` leaves non-requested methods out with a `[warn]` (`benchmark_loso.py:626–631`), and
   the rewritten `summary.csv` of `reports/loso_w1` would hold ccnn rows only. The fold heads confirm the vintage:
   s01-s05 dirs `e349656` (all methods), `loso_w1` `f0fa371` (classical) and `f0fa371`/`da92a47` (ccnn).
3. Old folds of a *requested* method are not "[skip]"-reused. `check_fold` raises SystemExit ("use a new --out-dir"),
   so stale reuse is impossible at this HEAD. The real hazard is item 2.

### 2. Binding run items for the verifier

Every run starts from the main working tree at the fix HEAD, with `git status --porcelain -- src scripts configs
Makefile` empty. Record that HEAD and `git rev-parse HEAD` in `05_run.md`. New fold configs must show
`git_dirty: false` and that head. New logs go to `reports/logs/P25/fix1_<name>.log`. P20 and P21 logs are never
appended to: the documents cite them as the record of the old runs.

- **G-0 Suite.** Run `pytest tests/ -q` once at the fix HEAD from a clean checkout and record the pass/skip counts.
  Nothing starts if any test fails.
- **G-1 Preserve before running.** Copy (`cp -a`, no move yet) into `mas/state/scratch/p25_fix1/old/` the dirs
  `reports/nn_sweep/`, `reports/pseudo_online/` (the 4 ccnn CSVs), `reports/loso_w1_s01-s05/`,
  `reports/loso_w1_s01-s05_seed43/`, `reports/loso_w1_s01-s05_seed44/` and `reports/loso_w1/`, all `folds/*.npz`
  included (the 39 old ccnn folds and the 2 abandoned eegnet folds too). Write `mas/state/scratch/p25_fix1/old_manifest.sha256`
  (`sha256sum` of every original file, relative paths). Then run `sha256sum -c` on the copies, which must report all
  OK. The rest of the procedure starts only after that.
- **G-2 Fresh staging out-dirs, then swap.** Write every rerun to a new sibling dir `reports/<name>__p25fix1/`.
  Never write to a canonical dir, never resume into an old fold set, never delete single fold files. The documents
  cite the canonical paths. The out-dir is not recorded in fold configs or `loso_config.json` (keys checked:
  cohort, channels_mode, channels, window_sec, stride_sec, seed, trial_offset, source, plus git/folds keys), so
  renaming is safe. After G-5 and G-6 pass for a dir, move the canonical dir aside, which is already copied in G-1,
  and rename the staging dir to the canonical name. If a check fails, do not swap that dir. Stop and report.
- **G-3 Commands** (same recipes as the Makefile and P21 05_run.md, with only the out-dir changed):
  (a) nn_sweep: Makefile 269 with **all three models** `--models ccnn compact eegnet`. That takes about 944 s
      (`reports/logs/P20/nn_sweep.log`).
  (b) pseudo-online: Makefile 271 and 272 (`ccnn_5class`, `ccnn_6class`), `--out-dir reports/pseudo_online__p25fix1`.
      Then run both tags a second time into `mas/state/scratch/p25_fix1/po_repeat/`. This is a determinism check.
  (c) cohort 5: Makefile 280, 282 and 283 into `reports/loso_w1_s01-s05__p25fix1`, which covers all six methods.
  (d) seeds: Makefile 284 for k = 43 and 44 into `reports/loso_w1_s01-s05_seed<k>__p25fix1`.
  (e) cohort 39: Makefile 306 (classical, CPU, about 589 s) and then the P21 05_run.md line 116 ccnn command, both
      into `reports/loso_w1__p25fix1`. Run eegnet only if Sebastian asks: the 2 old eegnet folds were an abandoned
      partial run, they are in no CSV, and they are preserved in G-1.
  Pre-flight for (e): `data/processed_continuous/w1_s0.25/` holds 39 `S*` folders (own count: 39). Estimated GPU
  time: `.venv/bin/python -I -c "g=944+33+63+773.66+412.21+438.26+5126; print(g, round(g/3600,2))"` → `7790.13 2.16`
  h. That is above `MAX_GPU_HOURS_PER_PHASE` 2. Run it locally and detached, under the standing local-run
  authorisation (decisions 160c2bc), and state the overrun in `05_run.md`. CPU parts take about 10 min.
- **G-4 Pre-registered R-13 seed check** (P25 R-13 ruling §3; ordered by decisions 308a610). Run
  `for B in 1 2 3 4 5; do .venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences
  --methods coherence wpli --random-state $B --permutations 50 --n-jobs -1 --out-suffix diag_r13_rs$B; done`
  (CPU, about 15 min). It writes only suffixed outputs. Before the runs, check `git status --porcelain reports/` for
  unsuffixed files, and check the base-42 split-half CSVs against the G-1-style hash taken first.
  - The 19 cells are those with |ours₄₂ − R-13| > 0.05 in `coherence_split_half_reliability.csv` and
    `wpli_split_half_reliability.csv`. Recompute them with a shown command; the count must be 19.
  - For each cell, take [min, max] over the 6 draws (base 42 plus 1–5). Count the cells whose R-13 value lies inside.
  - **Confirmed** if ≥ 10 of 19. **Refuted** if ≤ 6 of 19 and the outside cells share one sign. **Inconclusive** at
    7–9, in which case the deviation stays accepted as "probable".
  - Read only the split-half CSVs; the 50-permutation p-values are not used.
  - If refuted, P14 D-4 reopens with connectivity-stats, and acceptance 4 stays open.
- **G-5 Must stay identical** (compare like `mas/state/scratch/p24_make/compare.py`: keyed rows, numeric columns, and
  `Seconds` / `Data source` / `Folds` schema drift reported but not failing, per P24 A-2):
  - non-CCNN rows of nn_sweep `summary.csv`, `folds.csv` (except Seconds), `predictions.csv` and `confusion.csv`
    (compact_eegnet, eegnet): EXACT. P24 reproduced all of them EXACT on this machine (`compare_reports.csv`).
  - fbcca, lda, lda_subjnorm, compact_eegnet and eegnet rows of the cohort-5 dir, and eegnet rows of both seed dirs:
    EXACT in summary, per_subject, predictions and confusion.
  - fbcca, lda and lda_subjnorm rows of cohort 39: EXACT. This tree was not in the P24 comparison, so a difference
    here is a new finding. Stop and report; do not swap.
  - Also identical: every other file under `reports/`. Take a sha256 manifest of `reports/` excluding the six
    targets before G-3 and after G-3.
- **G-6 Must change, with sanity checks.**
  - nn_sweep `Params` for ccnn equals 27977 (7-channel subjects) and 32309 (8-channel subjects).
  - ccnn rows differ from the old ones. Identical ccnn predictions would mean the old model ran.
  - pseudo-online repeat (G-3b): all non-`Seconds` columns EXACT between the two runs.
  - Report `degenerate` ccnn folds per dir (`folds.csv`), the best-epoch min/median/max, and Train ≥ Val per subject.
  - List every ccnn number in a table with its CSV path, for the scribe.
- **G-7 Close-out.** Write `mas/state/scratch/p25_fix1/new_manifest.sha256` for the swapped canonical dirs. Record
  in `05_run.md` and `06_verify.md`: old and new cohort means for ccnn per tree, both manifests' paths, and the
  G-4 count and reading.

### 3. Binding items for the scribe

- **S-1 Label.** "CCNN spec deviation, fixed in P25 (fix round 1, code in 987742b): from P20 to P24 the CCNN stacked
  [real, imag] as two input maps with bias-free convolutions (14,817 / 17,285 parameters). The roadmap and R-8
  require one `[real | imag] / T` map with conv biases (27,977 / 32,309). Every CCNN value produced before P25 is
  non-conforming and superseded." Do not call it a "bug demo" or "legacy": no era-matrix row prescribes it. Wherever
  an old value is mentioned, it carries "(pre-P25 layout, non-conforming)". Results are not comparable seed by seed
  (handoff, open points).
- **S-2 Current-state documents: update in place with the G-6 values, plus one footnote of S-1.**
  - `README.md` lines 191, 206, 233, 236 and 241 (cohort-5 ccnn and three-seed range, cohort-39 ccnn 71.58, 1 s
    networks, pseudo-online mean and per-subject). Line 264 "reference network R-8" is now true; keep it.
  - `docs/report/v2/report.md` lines 33 and 215. Add the CCNN parameter count if §2 lists counts; check every
    nn_sweep or loso table that the report cites.
  - `docs/progress_report/progress_report.md` lines 131 and 149.
  - `docs/infographic/methodology_infographic.svg` lines 124–125 and 163, plus every pseudo-online number in it.
  - `notebooks/loso_colab.ipynb` "ccnn about 2.2 h": recompute it from the new per-fold `Seconds`, or mark it as a
    pre-fix estimate.
- **S-3 Historical records: append dated notes only, no rewriting.**
  - `RESEARCH_LOG.md`: a new P25 entry with the old and new values side by side. Each old P20/P21/P24 paragraph
    that quotes ccnn (lines 506, 510, 520, 522, 528, 558–560) gets a one-line dated pointer.
  - `CHANGELOG.md`: a P25 "Fixed" entry, with pointers at 495, 497 and 523.
  - `mas/state/reports/P20.md` (187, 207, 209, 315, 317, 345), `P21.md` (339, 345, 351, 365, 375, 116),
    `P23.md` (214, 220, 325) and `P24.md` (pseudo-online values): appended dated notes only.
- **S-4 Re-test every claim made with CCNN, using the new values and the rules the claim was made under.** Report any
  claim that flips as **flipped**. Do not reword it to hold.
  - P20 P4: every model > 20 %; **ccnn ≥ eegnet on the cohort mean**; Train ≥ Val for every model.
  - P20 pairwise ccnn − eegnet and ccnn − compact_eegnet: "not distinguishable" under R-P5 (≥ 3 pp and ≥ 4 of 5
    signs). P20 Q2 "which 1 s network performs best".
  - P20 P6 (a), (b) and (c) on the new pseudo-online CSVs, including the S04 floor note.
  - P21 P2 networks: LOSO below within on the 3 matched subjects, against the new nn_sweep ccnn.
  - P21 P4: 0 degenerate ccnn folds in each cohort-5 seed and 0 of 39.
  - P21 ccnn − lda over three seeds (−1.57 pp), and "tie inside the per-subject seed range".
  - P21 cohort-39 ccnn − lda (−0.96 pp) and "above lda in 19 of 39".
  - P21 C-4, and "no network ranking" (keep it).
  - P23 "GNN per-seed cohort means above the ccnn seed mean (86.04)", the table row at 214, and the ccnn smoothed
    87.96.
  - README and progress report "three-seed range 85.36–86.58".
  - P25.md states each re-test result with its CSV.
- **S-5 R-13.** P25.md uses the G-4 reading: confirmed, inconclusive with "probable", or refuted with acceptance 4
  open. It does not reuse the "probable" wording from the R-13 ruling if G-4 confirmed.
- **S-6 Sources.** P25.md lists this review's R11 consultation (reference `fde4b5a:src/models/cnn/ccnn.py`, verify a
  finished implementation) and the deep-learning statement "reference not opened". Commit 987742b (mislabelled
  `docs:`, carrying the fix) is cited as the CCNN fix commit and stays on the squash list.

### Era matrix

| Rule | Status |
|---|---|
| R2, R1 (in-fold, grouped CV) | PASS: the fix touches only the model; splits and fits are unchanged (`git diff bb9c091 HEAD` above). |
| R6 layout verified | PASS: the single-map position test and the R-8 pin both fail on the old code. |
| R9 per-subject reporting with source | Binding via S-2 to S-4: per-subject rows for every regenerated tree. |
| R10, R11 | PASS: the deep-learning agent did not open the reference. My consultation came after a finished, passing implementation and is listed (S-6). |
| fs from metadata | PASS: `fs` comes from `model_factory(..., fs)`; no literal was added. |

Verdict: PASS

## Results review (after fix round 1)

Reads: `02_plan.md` (settled 1–8, acceptance 1–7); `05_run.md` and `06_verify.md` (round 1 FAIL 5300347; "Fix round 1
rerun" PASS 896288d); my earlier sections of this file; `03_changes_scribe.md` (S-4 table, 42 rows); the last rows
of `mas/state/decisions.md`; `log.md`. I reran nothing on recordings and opened nothing in the reference repository
for this section. Every number below comes from a shown command that reads CSVs only (`.venv/bin/python -I -c ...`,
pandas). Code under test: `git diff --stat 463c793 HEAD -- src scripts configs tests Makefile` and
`git diff --stat 987742b HEAD -- ...` are both empty, so the G-0 suite and the regenerated trees ran the code at HEAD.

### 1. Acceptance

| # | Criterion | Own check | Met? |
|---|---|---|---|
| 1 | P00–P24 `passed`, no open blocker | `yaml.safe_load(mas/state/phase_status.yaml)`: 25 of P00–P24 `passed`, P25 `in_progress`. Blockers B001, B002, B004, B005 `resolved 2026-10-24`; B003 `RESOLVED 2026-10-28`; B006 `RESOLVED 2026-10-26`; B007 `RESOLVED 2026-10-27` (`grep -i status mas/state/blockers/*`) | yes |
| 2 | Suite on a clean checkout; rebuild evidence cited | G-0 at 463c793: 1565 passed, 6 skipped, 0 F/E (`mas/state/scratch/p25_fix1/g0_pytest.log`, per 06). Rebuild evidence: P24 `make all` at bb9c091 plus the P25 regeneration of the six CCNN trees; G-5 shows every non-CCNN row EXACT and `reports/` outside the six trees byte-identical (1154 files) | yes |
| 3 | Every split guarded | my audit section (24 splits, all guarded; N1, N2 open test notes) | yes |
| 4 | Every R-x within tolerance or explained | §2 below | yes |
| 5 | Autonomy and sources reports complete | 06 B and C; the three sources defects are closed by dated notes (§4) | yes |
| 6 | Module diff | my audit section (37 rows) | yes |
| 7 | Privacy scan of the net diff | orchestrator's gate step. Own pre-check of the five scribe commits: `git diff 10c5f70~5 10c5f70` piped through `grep -ciE` with the vendor and tooling terms built from fragments: 0 | gate |

No unexplained result deviation remains. The only runtime items are P24 A-5 and the fix-round GPU overrun (§5),
and neither changes a number.

### 2. R-x table

I read the verifier's table (06 §A, rows R-1 to R-16) together with the fix-round settlement (06, "Settled reasons of
the first verdict"). Rows that were W or E in round 1 are unchanged: G-5 holds every non-CCNN output EXACT, and no
R-x row other than R-8 reads a CCNN output. Two rows changed status.

- **R-8 Era-C sweep networks: W, exact.** Own read of `reports/nn_sweep/summary.csv` `Params`: ccnn 27977 (S01, S03,
  S04) and 32309 (S02, S05); compact_eegnet 28133 / 28229; eegnet 2373 / 2389. This equals R-8 at exact tolerance.
  The old values 14,817 / 17,285 exist only in `mas/state/scratch/p25_fix1/old/` and in historical text, which is
  labelled.
- **R-13 split-half reliability: E, confirmed by the pre-registered seed check.** Own recomputation from the base-42
  CSVs and the five `_diag_r13_rs{1..5}` CSVs, with the R-13 values typed from `mas/04_REFERENCE_RESULTS.md:237–246`:
  19 cells have |ours₄₂ − R-13| > 0.05, and 13 of them have R-13 inside the per-cell [min, max] of the six draws.
  This equals the verifier's count. The six outside cells are coherence S02 10.91 (R 0.34, draws −0.182 to 0.199),
  coherence S03 10.91 (0.78; 0.635 to 0.755), coherence S05 24 (0.84; 0.873 to 0.924), wPLI S02 10.91 (−0.75; −0.466
  to −0.252), wPLI S02 24 (−0.02; 0.139 to 0.315) and wPLI S04 15 (−0.25; −0.071 to 0.404). R-13 lies above the range
  in 2 cells and below it in 4, so the misses do not share one sign.
  Under the pre-registered rule (confirmed ≥ 10), the reading is **confirmed**. The count also matches pure split
  variation: with six draws the chance that a new draw falls inside their range is (k−1)/(k+1) = 0.714, so the
  expected count is 13.57 of 19 (`.venv/bin/python -I -c "k=6;p=(k-1)/(k+1);print(round(p,3),round(19*p,2))"` →
  `0.714 13.57`). Observed: 13.
  - **Ruling on "probable".** The word "probable" is dropped for the split-half cells. P25.md writes: "R-13
    split-half: 19 of 50 cells outside ±0.05; explained as Monte Carlo split variation by the pre-registered seed
    check (13 of 19 inside the six-draw range, rule ≥ 10; expected 13.6 under pure split variation)." It does not
    write "demonstrated identical" or "proven". The six outside cells are reported as a list: three are 10.91 Hz
    cells, and nothing beyond the count is claimed for them.
  - The ruling has two limits. (a) G-4 did not test the coherence pairwise magnitude count (10 against 6). That count
    stays "within the analogous ±5 band, pattern-consistent, null design a documented ambiguity" (R-13 ruling §4),
    not "confirmed". (b) The Fisher-vs-arithmetic similarity question stays open for Sebastian.
  - Wording fix for the orchestrator: decisions row 2026-10-30 says "five-base-seed range". The range is over **six
    draws** (base 42 plus bases 1–5). The new row uses "six-draw range".

All other rows keep their round-1 status, each with its cited explanation: R-3 D-1, R-4 SFS P06 D-1, R-7 and R-9b
P11 D-4 / B006, R-12 S05 wPLI P13 D-1, R-15 B007, R-16 no target. **Acceptance 4 is met.**

### 3. Number check of the regenerated CCNN values (current-state documents and RESEARCH_LOG)

I read every changed line of `git diff 10c5f70~5 10c5f70` in `README.md`, `docs/report/v2/report.md`,
`docs/progress_report/progress_report.md`, `docs/infographic/methodology_infographic.svg` and `RESEARCH_LOG.md`.
Each number was compared with the canonical CSVs:

| Value in the documents | Own CSV read | Match |
|---|---|---|
| nn_sweep ccnn 90.53 (per subject 75.59, 77.95, 99.85, 100.00, 99.26); compact_eegnet 92.08, eegnet 89.69; Val 92.41, best epoch 31.76, ITR 72.16; ccnn − eegnet per subject −2.35, +6.52, +0.61, 0.00, −0.59 | `reports/nn_sweep/summary.csv`, groupby Method | yes |
| LOSO cohort 5 ccnn 85.88 / 2-tap 87.25 (S01–S05 65.29, 73.45, 93.34, 99.70, 97.64); seeds 43 and 44 83.45 / 85.24 and 85.32 / 87.27; range 83.45–85.88; three-seed mean 84.88; 2-tap 86.59 | `reports/loso_w1_s01-s05{,_seed43,_seed44}/summary.csv` Mean rows | yes |
| cohort 39 ccnn 72.08 / 2-tap 73.91 / Val 75.41 / SD 19.53; above lda 21, below 17, equal 1; S015 27.00 against 56.13; folds: 39 ccnn of 156 | `reports/loso_w1/summary.csv`, `folds.csv` (Method counts 39 × 4) | yes |
| pseudo-online 5 classes 90.5 / FA 29.5 / ITR 58.0368; per subject 72.5, 85.0, 95.0, 100, 100 (FA 62.5, 45.0, 20.0, 5.0, 15.0); 6 classes 75.5 / missed 22.0 / FA 5.0 / ITR 46.3065; per subject 35.0, 50.0, 95.0, 100, 97.5 | `reports/pseudo_online/summary_ccnn_{5class,6class}.csv` | yes |
| decompositions: stimulus correct 181 / 151; lost 31 = 30 missed + 1 wrong (S01 15, S02 14, S03 1, S05 1); gained 1; FA 59 / 10 (S01 25, S02 18, S03 8, S04 2, S05 6; S01 6, S02 3, S05 1); 50 of 59 absent with six classes, 1 new (S01, 50.0312 s, pred 102); next target 15 of 59 (p 0.1876), 4 of 10 (p 0.1209); max time 2.4375 s (1 above 2 s, S01, 185.062 s) and 1.46875 s; per-subject Acc5 − Acc6 37.5, 35.0, 0.0, 0.0, 2.5 | merge of `decisions_ccnn_{5class,6class}.csv` on (Subject, onset_sec, period), `validate='1:1'`; `scipy.stats.binomtest(k, n, 0.2, 'greater')` | yes |
| infographic headline 90.50 %, six-class 75.50 %, footnote to the P25 rerun | SVG lines 121, 123, 162–163 | yes |
| Colab estimate 1.5 h | `reports/loso_w1/folds.csv` ccnn `Seconds` sum 5297.87 over 39 → 40 subjects 1.51 h | yes |
| P23 note: GNN per-seed means 88.47 / 88.11 above the ccnn seed mean 84.88 | `reports/loso_gnn/seeds.csv` per-seed cohort means | yes |

No fabricated or mismatched value was found. One like-for-like issue: the P20 and P23 notes say "ccnn 2-tap 86.59 stays
below the GNN LOSO 2-tap 90.32". The 90.32 is the three-seed **ensemble** value, and the ccnn value is a per-seed
mean. The like-for-like GNN per-seed 2-tap value is 89.91 (`nodes+F`) and 89.72 (`nodes+coh+F`) (own, `seeds.csv`
grouped by Method and Seed). The direction holds (89.91 − 86.59 = 3.32 pp), so the appended note can stay. P25.md
must not repeat the 90.32 comparison, and should cite 89.91 if it states one.

**Flipped claims are stated as flipped, not reworded.** In the current-state documents the old sentence "none is new"
is replaced by the true statement ("one six-class false activation (S01) does not occur with five classes"). Updating
a current-state document in place is correct for S-2. The flip itself is recorded in RESEARCH_LOG (P25 entry,
"Flipped: ..."), in CHANGELOG ("Flipped claims (not reworded)"), and in the P20, P21 and P24 dated notes. P6(a)
(fail → holds), the R-P9 next-target p (0.0064 → 0.1209) and the R-P9 five-class timing (one of 59 at 2.4375 s, which
is in the cue part of the rest period: fixation 0–2 s, cue 2–4 s per P20.md:293) are each labelled FLIPPED where they
are restated.

Count consistency: the S-4 table marks 8 rows FLIPPED (#8, #11, #13, #26, #29, #30, #37, #39). #13 and #39 are the
same timing claim (P20 and P24), so there are 7 distinct claims, which matches `log.md`'s "7 flipped". Of these, #26
(train accuracy "about 75–77 %"), #29 (validation mean) and #30 (seed range) are descriptive values, not tested
claims. The RESEARCH_LOG P25 entry lists them as "changed numbers". **P25.md uses one classification:** 4
substantive claim flips (P6(a); R-P9 next-target significance; R-P9 five-class timing; "none is new") plus 3 superseded
descriptive values (#26, #29, #30). It writes "7 flipped" only with that split.

**Ruling on the scribe's caveat (#20, ccnn − lda over three seeds).** The value is −2.73 pp (84.88 − 87.61). P21 had
no pre-registered difference rule (P21.md:351). The only rule in this line is P20's R-P5 (≥ 3 pp and ≥ 4 of 5 signs).
Under it, −2.73 pp is **not a difference**: the magnitude criterion fails (2.73 < 3) and the sign criterion is met
(4 of 5 negative: −0.44, −8.69, −3.99, +0.20, −0.69; own). The qualifier "tie inside the per-subject seed range" is no
longer supported. lda lies outside the ccnn three-seed range on S02 (76.24 against 63.66–73.45) and S03 (96.07 against
91.38–93.34), both above, and on S04 (99.55 against 99.70–99.85), below. ccnn is below lda in 10 of 15 seed × subject
cells (own, three summaries). Ruling:
- the P21 dated note ("weakest reading, not strengthened") is acceptable as an appended note;
- P25.md writes: "ccnn − lda over three seeds: −2.73 pp, not a difference under R-P5 (magnitude below 3 pp; 4 of 5
  subjects negative); no ranking. The P21 wording 'a tie inside the per-subject seed range' is superseded and not
  repeated."
- no current-state document repeats the "tie" wording (`grep` of README, report v2, progress report: none). The
  RESEARCH_LOG P25 entry already gives the sign pattern. Nothing to change there.

### 4. Historical reports P11 and P20–P24

`git diff 10c5f70~5 10c5f70 -- mas/state/reports/P{11,20,21,22,23,24}.md`: one hunk per file, at the end of the
file, with 0 removed lines (added 2, 24, 12, 2, 6 and 8; old lengths 412, 426, 468, 466, 420 and 388 lines). Each hunk
is under a "Dated note(s), 2026-10-30" heading. `RESEARCH_LOG.md` and `CHANGELOG.md` also have 0 removed lines; the
P20/P21/P24 paragraphs get pointer lines inserted after them, and their text is untouched. **Nothing historical was
rewritten.** The three sources defects of round 1 (P22 `[23]`, P11 log path, P21 `window_sweep_colab`) are closed by
these notes.

### 5. Deviations and open items

**Accepted deviations (copy into decisions.md):**
1. **R-8 CCNN layout (P20–P24): spec deviation, fixed in P25.** Code 987742b. Every CCNN output was regenerated
   (G-0..G-7) and R-8 is now exact. The pre-P25 values are labelled "pre-P25 layout, non-conforming" wherever they
   are quoted. This is a fixed deviation, not an open one. 987742b (`docs:` prefix, carries code) stays on the
   squash list.
2. **R-13 split-half (19 of 50 cells outside ±0.05).** Accepted Monte Carlo split variation, confirmed by the
   pre-registered seed check (13 of 19 inside the six-draw range; rule ≥ 10). The pairwise coherence count 10 against
   6 falls within the analogous ±5 band. Fisher similarity stays open.
3. **N3 layout.** `benchmark_nn_sweep.py` sits in `scripts/benchmarks/neural_networks/` instead of
   `scripts/benchmarks/` (P20 plan choice). It has no effect on results (already recorded, decisions 2026-10-29).
4. **P24 A-5.** An unexplained **runtime observation**: the p19 clone ran 10.2 min against 2.5 min recorded, and the
   results were identical. It is kept out of the R-x deviation table.
5. **Fix-round GPU overrun.** 2.33 GPU h against `MAX_GPU_HOURS_PER_PHASE` 2 (`05_run.md` steps.txt sum), run locally
   and detached under Sebastian's standing local-run authorisation. This is a budget observation; no result depends
   on it.
6. **Schema drift in the regenerated trees.** `Seconds`, `Data source` and `Folds` column drift is the known P24 A-2
   type (string or timing only, numbers EXACT per G-5).

**Open questions for P25.md (not deviations; each "changes no published number" unless stated):**
- **N1** (synthetic-tester): the fusion-CNN inline legacy splitter is not in the `tests/test_no_leakage.py`
  registry.
- **N2** (synthetic-tester): the NN-sweep split has no spy test of its own (it is guarded by the runtime assert and
  by probability identity with the window-sweep cell).
- **Colab notebook sections not run end to end on a T4.** This is a verification gap. The 1.5 h ccnn estimate is
  from the local RTX 3050-class GPU and was not measured on a T4.
- **P17 C-d** (harmonic attribution untested; the published wording avoids it) and **P17 C-e** (optional per-offset
  metric).
- **P22 `within_lda` `Data source` label** in the old main-tree CSVs. This is string only (P24 A-2).
- **Cohort-39 eegnet not re-run (G-3e).** The 2 abandoned eegnet folds were in no CSV. They are preserved in
  `mas/state/scratch/p25_fix1/old/` and absent from the canonical tree. A full 39-subject eegnet (and compact_eegnet)
  run is Sebastian's choice.
- **`reports/loso_w1` now holds 156 folds** (117 classical + 39 ccnn) against 158 before. The difference is exactly
  those 2 eegnet folds; no summary row changes because of it.
- The P21 "tie" wording (§3 ruling) and the ensemble-vs-per-seed GNN 2-tap comparison (§3) are wording items for
  P25.md, not deviations.

### 6. Binding items for P25.md (scribe)

- **S-5:** use the R-13 wording of §2 ("confirmed", six-draw range, expected 13.6). Drop "probable" for the
  split-half cells only.
- **S-4 summary:** 4 substantive flips + 3 superseded descriptive values (§3). Use the #20 wording of §3. If a GNN
  2-tap comparison is stated, use the per-seed value 89.91.
- **S-6:** list my R11 verification read (`fde4b5a:src/models/cnn/ccnn.py`) and the 12 task-4 accesses. Add that
  this results review opened nothing in the reference.
- The deviations and open questions of §5, each with its owner.

### Era matrix (results)

| Rule | Status |
|---|---|
| R1, R2 | PASS: since the audit the only code change is the CCNN model (987742b), which touches no split or fit; `git diff --stat 463c793 HEAD -- src scripts configs tests Makefile` is empty. |
| R6 | PASS: the CCNN layout is pinned by known-answer tests, and R-8 is exact on the real outputs. |
| R7 | PASS: the R-13 Monte Carlo reading rests on a pre-registered rule, and the flipped p-value (R-P9) is reported as flipped. |
| R9 | PASS: per-subject values with data source in every regenerated table (README, report v2, P20/P21/P23/P24 notes). |
| R10 | PASS: CSV paths beside every regenerated value; sources defects closed. |
| R11 | PASS: no reference access in fix round 1 except my logged verification read; none in this section. |

Verdict: APPROVE

No fix round is required. The items of §6 bind the P25.md write-up, and the orchestrator's decisions row uses the
"six-draw range" wording of §2.
