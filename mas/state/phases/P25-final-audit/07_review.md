# P25 · 07 · Scientific review

Status: AUDIT DONE (results review pending 06_verify.md)
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

Verdict: pending (after 06_verify.md)

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

### Decisions for decisions.md

## Sources spot-check

## Questions
