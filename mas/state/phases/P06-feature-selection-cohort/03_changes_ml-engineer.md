# P06 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/02_REQUIREMENTS.md §4-§6, mas/04_REFERENCE_RESULTS.md R-4/R-5, mas/05_PITFALLS.md, mas/state/reports/P05.md, decisions.md P05/P06 rows
Branch: phase/P06-feature-selection-cohort
Commit(s): a8ff6f2 (bookkeeping), 31bdaec, c25e850, f721883, 3d17a12, ed7e36b

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/selection/feature_selection.py` | NEW | `select_k_best_fbcsp_features(X_tr, y_tr, n_features_to_select=15, method="anova"/"mutual_info", random_state=42)` -> sorted FBCSP column indices (SelectKBest f_classif / mutual_info_classif seeded); `select_sfs_fbcsp_features` (forward SFS of scaler+Shrinkage-LDA, sklearn inner 5-fold); `with_fbcca`, `band_columns`, `subband_pruned_columns` (band-major layout, R6) | P06.1 | [4], R2, PF-11, R6 |
| `src/features/selection/__init__.py` | existing (P05) | unchanged | P06.1 | |
| `scripts/benchmarks/feature_based/benchmark_feature_selection.py` | NEW | five rows in the legacy folds of the flagship; CSP once per fold from training rows, all selectors on the training rows; `reports/feature_selection_ablation_<S>.csv` + `.meta.txt` | P06.2 | [4], R-4 |
| `scripts/benchmarks/feature_based/benchmark_5_subjects.py` | NEW | flagship via `prepare_subject` + `benchmark_spaces` + `oof_space` (same path as `evaluate_confusion_matrix`) for every discovered `S\d+` folder; `reports/five_subjects_benchmark.csv` + `.meta.txt` | P06.3 | [1] §6, R-5 |
| `src/models/classical/benchmark_runner.py` | MODIFIED | `legacy_header_lines(..., fbcca_channels=None)` adds a line "FBCCA channels (n): ..." when given | P05 open item | decisions.md P05 |
| `scripts/benchmarks/feature_based/benchmark_cross_validation.py` | MODIFIED | passes `blocks["fbcca_channels"]` to the header (names the 7 FBCCA channels in the six-space CSV `.meta.txt`) | P05 open item | same |
| `tests/test_p06_feature_selection.py` | NEW | 13 tests (below) | all | |

## Legacy behaviour implemented

Inherited unchanged from P05 and labelled in code, console and `.meta.txt`: R1/PF-01 window-level `StratifiedKFold(5, shuffle, 42)`; R8/PF-02 `i % 5` trial smoothing for the reported 2.0 s; R3/PF-14 and PF-04 per-window filtering at fs 250; R5 per-script mask (vpp 0.5-120, std 0.1-35 uV); FBCCA on all 7 channels. No new legacy behaviour.

## Differences from the cited examples

None (scikit-learn estimators used through their public API).

## Deviations from the plan

1. `select_k_best_fbcsp_features` receives the FBCSP block only `(n_train, 50)` and returns indices into it; "FBCCA always kept" is done by `with_fbcca` / the script (the roadmap signature has no FBCCA argument).
2. SFS estimator is `Pipeline(StandardScaler, Shrinkage-LDA lsqr auto)` (scaler refit in each inner fold); sklearn defaults for the inner CV (`cv=5`, unshuffled stratified) and accuracy scoring. `--n-jobs` (default 1) does not change results.
3. `Mean` row of the cohort CSV: mean of the CSV's rounded accuracy values (2 decimals); Clean Windows / Rejected are blank in it (as R-5 shows). Plan test "Mean = column means" therefore applies to the two accuracy columns.
4. Extra flags: `--skip-sfs` (smoke only), `--sfs-features` (default 15), `--subjects` (cohort, default = discover), `--m`, `--seed`.

## How to run / reproduce

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_5_subjects
```

## How I verified

- `pytest tests -q -p no:warnings`: all pass (exit 0; the run is ~2-3 min, above the 1 min target, as P05 already recorded).
- Tests (`tests/test_p06_feature_selection.py`): ANOVA and MI find planted columns 7 and 31 (exact indices at k=2, k=20 subset, sorted, in 0-49); MI seeded repeatable; invalid method rejected; in-fold test (a column informative only in held-out rows is not selected from training rows, is selected by a full-data fit, both methods); spy test (inside the ablation every ANOVA/MI/SFS call receives exactly the 80 training rows of 100, 15 calls); pruning layout (band (38,52) is index 4, drop columns 40-49, 45 kept; band-major layout checked against `FBCSPTransformer` by inflating band 5 only: changed columns are within 40-49); `with_fbcca`; SFS picks planted columns and returns exactly 3 / 15; ablation script p = 55, 45, 25, 25, 20, columns, and its Full row equals the `evaluate_confusion_matrix` flagship row on the same tree; cohort script schema, S10 > S2 numeric order discovery, Mean row, same numbers as the flagship; missing subject exit 1.
- Smoke on synthetic trees under `mas/state/scratch/p06smoke/` (5 subjects x 200 windows, 7 channels, accuracy 100 % so only runtimes are meaningful): ablation one subject 77 s wall (`runtime 77 s`, console), cohort 5 subjects 13 s.

Runtime estimate for the verifier: real data has the same shape (about 197-200 windows x 7 x 256), so the ablation should take about 1.5-3 min on one core (SFS about 14 s per fold, the other four methods and CSP the rest) and the cohort about 0.5-1 min including loading. Both far under `LOCAL_RUN_BUDGET_MIN`. Unmeasured on real data; this is an extrapolation.

## Left to do / known limitations

- R-4 / R-5 numbers are not yet produced (no real-data runs by the builder). If R-4 is missed beyond 1.5 pp: first diagnostics (counts, folds, SFS inner-CV default, MI seed), then R11.
- SFS inner-CV defaults and the MI seed are the plan's settled points, but the original's exact estimator inside SFS (scaled or not) is unknown until an R11 consultation; Shrinkage-LDA lsqr auto is nearly scale invariant, so the difference should be small.
- `benchmark_harmonic_fbcca.py`, `test_sklearn_models.py`, `evaluate_confusion_matrix.py` headers do not yet print the FBCCA channels (not touched).

## Reference consultations (R11)

None. `mas/state/scratch/reference_access.log` untouched by me.

| # | Trigger | Files and lines @ commit | What I learned | What changed |
|---|---|---|---|---|
| | | | | |

## Sources

1. `mas/02_REQUIREMENTS.md` §6 (opened in this run).
2. `mas/03_ROADMAP.md` P06, `mas/04_REFERENCE_RESULTS.md` R-4/R-5, `mas/05_PITFALLS.md` PF-11, `mas/RULES.md` R2/R6 (opened in this run).
3. scikit-learn `SelectKBest`, `f_classif`, `mutual_info_classif`, `SequentialFeatureSelector` (API as installed in `.venv`; docs not fetched online in this run).

## Questions
