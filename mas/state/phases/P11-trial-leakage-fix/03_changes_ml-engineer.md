# P11 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Branch: phase/P11-trial-leakage-fix

## Files
- NEW `src/preprocessing/dataset/cv_utils.py` — trial ids, grouped CV, helpers (API below).
- MODIFIED `src/preprocessing/dataset/smoothing.py` — `smooth_probabilities_by_trial(proba, trial_ids)`; `smooth_probabilities_legacy` and `_mod5` untouched.
- MODIFIED `src/models/classical/legacy_eval.py` — `accuracies(..., trial_ids=None, rule=None)`, `smooth_scores`, `splits_for`, `cv_label`, `smooth_label`, labels `GROUPED_CV_LABEL`, `TRIAL_SMOOTH_LABEL`; `legacy_cv`, `CV_LABEL`, `SMOOTH_LABEL` unchanged (legacy stays reachable).
- MODIFIED `src/models/classical/benchmark_runner.py` — `prepare_subject` adds `trial_ids` (pre-gate, then `[mask]`), `trial_block_report`, `trial_ids_approximate`, `n_trials`; `add_protocol_args`, `protocol_labels`, `trial_ids_header`, `print_trial_report`; re-exports `output_dir`.
- MODIFIED `src/models/classical/sklearn_models.py` — `random_state=seed` on the two saga LogReg models (see Deviations 1).
- MODIFIED `scripts/benchmarks/feature_based/benchmark_n_subjects.py`, `benchmark_cross_validation.py`, `benchmark_feature_selection.py` (grouped SFS inner CV: `inner_sfs_splits`, `column_sets(..., ids_tr=)`), `benchmark_harmonic_fbcca.py`, `scripts/evaluation/evaluate_confusion_matrix.py` — `--cv`, `--smoothing`, output dir, meta lines, per-subject block report.
- NEW `scripts/diagnostics/demo_cv_leakage.py` (`scripts/diagnostics/__init__.py` already existed).
- NEW `tests/test_p11_cv.py` (21 tests). MODIFIED `tests/test_no_leakage.py` (registry: `cv_utils` leak-free, grouped splitters, SFS inner splits, legacy `splits_for`), and `tests/test_p05_feature_benchmark.py`, `test_p05_known_answer.py`, `test_p06_feature_selection.py`, `test_p06_known_answer.py`, `test_p07_ml_engineer.py` (these pin the P05-P07 legacy protocol: they now pass `--cv legacy --smoothing mod5` and read `legacy_leaky/`; the P06 mutant spy follows the `splits_for` rename; no tolerance changed).

## Commits
03df48c library; 1278d9b scripts; cffdc6a demo; b5182db tests (after 2d562cf chore: phase files).

## CLI (for the verifier; the commands of 02_plan.md "Run commands" are CONFIRMED unchanged)
Every classical script: `--cv {grouped,legacy}` (default grouped), `--smoothing {trial,mod5}` (default trial). `--cv legacy` writes to `<reports-dir>/legacy_leaky/` (and `<figures-dir>/legacy_leaky/` for figures); `grouped` to `<reports-dir>/`. An explicit `--reports-dir X` still gets `X/legacy_leaky/` for legacy (never overwrites grouped files).
- `python -m scripts.benchmarks.feature_based.benchmark_n_subjects [--subjects ..] [--data-root ..] [--n-jobs N] [--out-suffix ..] --cv .. --smoothing ..` -> `n_subjects_benchmark[_suffix].csv` + `.meta.txt`.
- `... benchmark_cross_validation --subject S03 --cv .. --smoothing ..` -> `feature_space_benchmark_S03.csv`.
- `... benchmark_feature_selection --subject S03 --k-features 20 [--sfs-features 15] [--n-jobs N] --cv .. --smoothing ..` -> `feature_selection_ablation_S03.csv` (`--sfs-diagnostics` keeps its labelled P06 inner CVs).
- `... benchmark_harmonic_fbcca`, `scripts.evaluation.evaluate_confusion_matrix` (same two flags; `flagship_<S>.csv`, classification reports incl. `_smoothed_trial.txt` in grouped runs).
- `python -m scripts.diagnostics.demo_cv_leakage [--subjects ..] [--data-root ..] [--reports-dir ..]` -> `reports/cv_leakage_demo.csv` (+ `.meta.txt`), columns `Subject, Clean, Approximate ids, 1.0s leaky (%), 1.0s grouped (%), Delta 1.0 (pp), 2.0s leaky mod5 (%), 2.0s grouped trial (%), Delta 2.0 (pp), 2.0s grouped mod5 (%)` + Mean row. Network section (no training) reads `reports/legacy_leaky/augmentation_ab_<model>.csv` (frozen P10) and `reports/augmentation_ab_<model>.csv` (P11) and writes `reports/cv_leakage_demo_networks.csv` (extra file, not in the plan); a missing pair is skipped with a printed line. So the second demo run (step 2) must come after the DL builder's A/B runs.

## Public API for the deep-learning builder
```python
# src/preprocessing/dataset/cv_utils.py
LEGACY_TRIAL_LENGTHS = {201: 2, 202: 1, 101..105: 5}
build_trial_ids(y, sub_windows_per_trial=5 | dict, return_truncated=False, warn=True) -> ids (or (ids, [(label,start,len)]))
trial_block_report(y, ids, sub_windows_per_trial) -> {"blocks","n_trials","truncated","approximate"}; format_block_report(rep)
grouped_cv(seed=42) -> StratifiedGroupKFold(5, shuffle=True, random_state=seed)   # .split(X, y, groups=ids)
make_splits(cv: "grouped"|"legacy", y, trial_ids, seed=42) -> [(train, test)]    # legacy = P05-P10 StratifiedKFold
assert_no_shared_trials(splits, groups); shared_trials(splits, groups)
output_dir(reports_dir, cv) -> reports_dir[/legacy_leaky]
# src/preprocessing/dataset/smoothing.py
smooth_probabilities_by_trial(proba, trial_ids); smooth_probabilities_mod5(proba)   # legacy
# src/models/classical/legacy_eval.py
accuracies(y, pred, scores, trial_ids=None, rule=None) -> (acc1, acc2)   # rule None: "trial" if trial_ids else "mod5"
smooth_scores(scores, trial_ids=None, rule=None); splits_for(cv, y, trial_ids, seed=42)
cv_label(cv), smooth_label(rule), GROUPED_CV_LABEL, TRIAL_SMOOTH_LABEL, CV_LABEL, SMOOTH_LABEL
# src/models/classical/benchmark_runner.py
add_protocol_args(parser)   # --cv/--smoothing; protocol_labels(cv, smoothing); print_trial_report(subject, blocks)
```
Trial ids for the networks: the DL loader loads `y_labels.npy` (all conditions), `ids_all = build_trial_ids(y_all, LEGACY_TRIAL_LENGTHS, warn=False)`, keeps `ids_all[np.isin(y_all, CLASS_CODES)]`, then indexes with its own valid mask (PF-03). `prepare_subject` does exactly this for the classical side (`blocks["trial_ids"]`); the networks' own mask (P09/P10 window gate) must be applied to the ids the same way. Ids are non-decreasing in array order, so `accuracies(y, pred, scores, ids, "trial")` works on the clean array. The 2.0 s rule and the splitter are independent flags; the DL scripts should pass `cv`/`smoothing` through to `make_splits`/`accuracies`.

## Verification
- Full suite: all tests pass (631 test dots, no F/E; the final summary line is suppressed by `addopts = -q` in `pytest.ini`, runtime about 4.5 min, mostly P05-P10 script tests; `tests/test_p11_cv.py` alone 59 s). Log: scratchpad `full_pytest.log`.
- Legacy regression (`test_legacy_mode_is_byte_identical_to_pre_p11_and_writes_under_legacy_leaky`): the five scripts on a synthetic 2-subject tree with `--cv legacy --smoothing mod5` give sha256-identical CSV/TXT outputs to the pre-P11 code (commit 829602c run in a scratch worktree, saga seeding applied to both; pins in the test). `.meta.txt` files gain trial-id lines (not pinned).
- Tests that fail on the historical bugs: `test_ids_are_built_before_the_gate_then_masked_pf03` (post-gate ids), `test_planted_leak_*`, `test_every_classical_script_uses_trial_grouped_splits` and `test_assert_no_shared_trials_catches_the_window_level_split` (window-level split), `test_smoothing_by_trial_known_answer_and_no_mixing` (i%5 mixes trials), `test_sfs_inner_splits_*` / `test_column_sets_sfs_receives_grouped_inner_cv` (default inner 5-fold). `test_prepare_subject_trial_ids_are_pre_gate_then_masked` plants a gate rejection at stimulus window 7 and checks ids against a hand array.
- Smoke on the real legacy arrays (scratchpad outputs, not in `reports/`): `python -m scripts.diagnostics.demo_cv_leakage` on S01-S05, 6 s:

| Subject | Approx. ids | 1.0 s leaky | 1.0 s grouped | R-6 1.0 s | 2.0 s leaky mod5 | 2.0 s grouped trial | 2.0 s grouped mod5 | R-6 2.0 s |
|---|---|---|---|---|---|---|---|---|
| S01 | no | 64.50 | 61.00 | 61.00 | 75.50 | 67.50 | 67.50 | 67.50 |
| S02 | yes (39+40) | 66.33 | 56.12 | 56.12 | 71.94 | 59.18 | 61.73 | 61.73 |
| S03 | no | 90.36 | 86.80 | 86.80 | 95.43 | 86.80 | 90.36 | 90.36 |
| S04 | yes (38+40) | 98.98 | 97.46 | 97.46 | 98.48 | 97.97 | 97.97 | 97.97 |
| S05 | no | 96.50 | 95.00 | 95.00 | 96.50 | 95.50 | 95.50 | 95.50 |
| Mean | | 83.33 | 79.28 | 79.28 | 87.57 | 81.39 | 82.61 | 82.61 |

  Source: the demo's `cv_leakage_demo.csv` (scratchpad `real_demo2/`). Leak effect 1.0 s -4.06 pp (R-6 -4.05).

## Findings the orchestrator must decide on (acceptance wording, not code)
1. **R-6's 2.0 s column equals the grouped split with the legacy i%5 smoothing, to 0.01 pp, on all five subjects (mean 82.61).** The R8-correct trial-id smoothing (the settled default) gives mean 81.39 (-1.22 pp, outside the +-1.0 pp mean tolerance; S02 -2.55 pp and S03 -3.56 pp, outside +-1.5 pp). S01, S04 and S05 agree within 0.5 pp (S04 +0.00 vs R-6). So with the settled default `--smoothing trial`, `reports/n_subjects_benchmark.csv` fails the plan's R-6 acceptance on the 2.0 s column for S02 and S03, while `--smoothing mod5` reproduces it exactly. The plan's settled point 1 foresees this and wants a decision row; the R11 consultation of the original's P11-stage smoothing was NOT made by me. The verifier should report both columns, as the demo does.
2. S02 and S04 have approximate ids (blocks 39+40 and 38+40: windows lost to the raw gate in the saved arrays); S02 shows the largest trial-vs-mod5 gap.

## Deviations from the plan
1. `src/models/classical/sklearn_models.py`: the saga `LogReg L1` and `LogReg ElasticNet` had no `random_state`, so the P05 benchmark CSV rows of those two models were not reproducible between identical runs (observed on the pre-P11 code: 1-3 pp flips between two runs). Seeded with `seed` so legacy snapshots are reproducible and byte-pinnable. No effect on the flagship (LDA) or any R-5/R-6 number; the saga rows of `feature_space_benchmark_<S>.csv` may differ slightly from the earlier non-reproducible P05 numbers.
2. Library defaults: functions take `cv="grouped", smoothing="trial"` (not legacy), so a new caller is leak-free by default; existing P05-P07 tests were switched to explicit legacy.
3. Extra output `reports/cv_leakage_demo_networks.csv` from the demo's network section.
4. `legacy_eval.accuracies` default `rule=None` (= "trial" when ids are given, else "mod5") instead of the plan's `rule="trial"`, so pre-P11 three-argument calls keep their behaviour.
5. The approximate-ids flag is set only by block lengths that are not a multiple of the trial length in the saved stimulus labels (raw-gate losses, PF-03). A window rejected by the script's own two-tier gate does not make ids approximate, because ids are built before the gate.
6. The resumable-LOSO configuration check named in the role text is not applicable in P11 (no LOSO harness yet); no code written for it.

## Reference consultations (R11)
None. The original repository (answer key) was not opened.

## Not done / hand-off
`benchmark_5_subjects`, `train_models`, `test_sklearn_models`, `batch_run_subjects` and `spatial_spectral_cnn` are untouched (frozen legacy-leaky, as the plan scopes). The network scripts are the deep-learning builder's rows.
