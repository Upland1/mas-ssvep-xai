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

## Round 1 — investigation

Status: READY

Trigger: 06_verify.md (b695b9a): only the SFS row misses R-4 (89.85 / 95.94 vs 84.77 / 93.40). Procedure (07_review.md pre-run): one investigation round with labelled DIAGNOSTIC variants only; R11 only afterwards. **No reported definition changed; the reference was not consulted.**

Commits: a5bdafb (diagnostics), then the registry fix (see below, `git log` of the branch for its SHA); suite: full `pytest tests -q -p no:warnings` all pass (exit 0, ~3 min) after registering the new inner-CV use in `tests/test_no_leakage.py`.

### What was added (MODIFIED)
- `scripts/benchmarks/feature_based/benchmark_feature_selection.py`: `--sfs-diagnostics` (off by default; the reported CSV is byte-identical with and without it, tested).
- `src/features/selection/feature_selection.py`: `select_sfs_fbcsp_features(..., cv=None)`; None keeps scikit-learn's default 5, i.e. the reported behaviour.
- `tests/test_p06_feature_selection.py`: variant coverage, diagnostics script smoke (reported row reproduced by the "reported" variant, audit disjoint), planted-overlap audit failure.
- `tests/test_no_leakage.py`: the script is registered as `legacy` (the shuffled inner `StratifiedKFold` of the diagnostic is applied to training rows only).

### Variants (one factor at a time around the reported SFS; final classifier of every variant = reported scaler + Shrinkage-LDA, only the SFS configuration changes)
reported (cv 5, unshuffled, scaler+Shrinkage-LDA, 50 FBCSP cols + FBCCA, n=15); inner cv 3 and 10; inner shuffled StratifiedKFold(seed 42) with cv 3, 5, 10; estimator plain LDA svd; Shrinkage-LDA lsqr without scaler; all 55 columns with n=20; 50 FBCSP columns with n=20 (p = 25). Scoring is accuracy throughout. Output `reports/feature_selection_sfs_diagnostics_<S>.csv` (columns `Subject, Variant, Inner CV, Inner shuffle, Estimator, Candidates, n_features, p, 1.0s Acc (%), 2.0s Smoothed (%), Clean Windows, Rejected, Label`).

### Leak audit (reported variant, per outer fold; assertions fail the run)
Prints and writes `reports/feature_selection_sfs_audit_<S>.csv`: rows the SFS fit receives (must equal the training count), outer test count, outer train/test index sets disjoint, number of outer test rows whose FBCSP feature vector equals any row of the SFS input (must be 0), and the selected FBCSP column indices.

### Exact verifier command
```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20 --sfs-diagnostics --n-jobs 8
```
It re-runs the five reported rows (identical to the earlier run; compare with the first `feature_selection_ablation_S03.csv`) and then the ten variants. Runtime: synthetic 200-window smoke at `--n-jobs 1` was 909 s wall in total (reported part ~77 s; the variants 21 s to 149 s each, cv=10 slowest, console `runtime 909 s`); with `--n-jobs 8` expect roughly 3–4 min; real data is the same shape. This exceeds the 5-minute smoke limit only on real data, so the verifier runs it.

### What the verifier should look for
(1) audit: all folds disjoint, 0 test rows in the SFS input, 160ish rows per fit; (2) whether any variant lands in the accepted R-4 window (165–169 / 182–186 windows) — a single variant that does (e.g. plain LDA svd or an unshuffled/shuffled cv difference) points at a definition deviation to report to the orchestrator; (3) if all variants stay near 177/197 and the audit is clean, the miss is not a leak in this code and R11 is the next step (orchestrator's decision).

### Reference consultations (R11)
None in Round 1.

## Round 1 — R11 consultation

Trigger: the verifier's diagnostic run (06_verify.md "Diagnostic run", log `reports/logs/P06/benchmark_feature_selection_diag_20261025_043543.log`) is clean on the leak audit and no SFS variant falls inside both R-4 ranges; the pre-committed procedure then allows R11. No code was changed in this step.

Consultations (all read-only `git -C <reference clone> ...` calls, logged in `mas/state/scratch/reference_access.log`, 2026-10-25T04:4x). "Ref" below is the reference clone at the original's commits.

| # | Command (on Ref) | What for | Result |
|---|---|---|---|
| 1 | `log --oneline` (53 commits on main, 60 with `--all`) and `show --stat 277ddab` | find the P06-stage commit | 277ddab "finalize methodology report, 5-subject benchmark and infographic" adds `scripts/benchmarks/benchmark_5_subjects.py`, `scripts/benchmarks/benchmark_feature_selection.py`, `src/features/feature_selection.py` (plus file moves); branch `origin/feature/feature-selection-and-eegnet` ends at the same 277ddab |
| 2 | `show 277ddab:src/features/feature_selection.py` | ANOVA/MI selector | l.8-54: only `f_classif` (NaN to 0) and `mutual_info_classif(random_state)`, ranking by `np.argsort(scores)[::-1][:k]`, sorted indices; no SFS function. Docstring l.22: input is the "in-fold scaled" FBCSP matrix (N_train, 50) |
| 3 | `show 277ddab:scripts/benchmarks/benchmark_feature_selection.py` | the ablation script | (a)-(c) below |
| 4 | `show 277ddab:scripts/benchmarks/benchmark_5_subjects.py` | cohort script | (c) below |
| 5 | `log --all -S SequentialFeatureSelector`; `-i -S "forward selection"`; `-i -S forward`/`Sequential`/`sfs`; `show 277ddab:README.md` and `show HEAD:README.md` (grep); `show HEAD:scripts/benchmarks/feature_based/benchmark_feature_selection.py` and `show HEAD:src/features/selection/feature_selection.py` (grep) | find any SFS anywhere in the history | `SequentialFeatureSelector` and "forward selection": no commit on any branch. "forward"/"Sequential"/"sfs" hits are only neural-network commits (a266bb8, bd50298, 0466fad, 1b98fb7, dd139b2, cdeb0d5, e40eeec: `forward()` / `nn.Sequential`) or image/doc commits. README at HEAD l.221-222 lists the module as "ANOVA F-score or mutual-information ranking, fitted strictly in-fold" only |
| 6 | `show 7cad759 --stat` (documentation branch) | the report | contains `documentation/SSVEP_Technical_Report.docx` (binary). NOT inspected: the guard blocks piping the object into an interpreter and the binary cannot be grepped |

### (a) Sequential forward selection
**The original code at 277ddab, and at every later commit on every branch, contains no sequential forward selection.** `benchmark_feature_selection.py` at 277ddab has exactly four methods (l.59-64: "1. Full Baseline (p=55)", "2. ANOVA F-Score (p=k+5)", "3. Mutual Info (p=k+5)", "4. Subband Pruning (p=45)"). So library/class, estimator, candidate columns, n_features, inner CV, scoring, scaling and in-fold vs full-data cannot be read from the reference. R-4's SFS row (p=20, 84.77 / 93.40) came from something not in the repository (an unrecorded or deleted run, or only the .docx report, not inspected). I did not guess a definition.

### (b) ANOVA / MI / pruning (script 277ddab)
- Folds: `StratifiedKFold(5, shuffle=True, random_state=42)` over clean windows (l.55, 67-69), as ours.
- Selection in-fold on the training rows (l.101-116), applied to the **scaled** FBCSP block (`StandardScaler` fitted on the training FBCSP, l.88-91; a second scaler for the 5 FBCCA columns, l.93-95). Ours selects on the unscaled FBCSP block: ANOVA is scale invariant, MI nearly so. Our ANOVA/MI rows are in range (06_verify), so no change is indicated.
- ANOVA/MI keep `--k-features` FBCSP columns (script default 15, l.28-31; R-4's p=25 implies the run used 20) + the 5 FBCCA columns; MI `random_state=42`.
- Pruning: `list(range(40))` + FBCCA (l.118-122), i.e. columns 40-49 dropped, as ours.
- Final model: `LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")` on the scaled matrix (l.131-137), equivalent to ours (per-column scaling is the same fitted per block or jointly).

### (c) Other differences from our ablation path
- Sub-bands: `butter_bandpass_filter(windows, low, high, fs=250.0, order=4)` per window on train and test (l.74-80), the legacy per-window filtering that P05 already reproduces (R-3 exact).
- Window gate: `extract_fbcca_features(windows, y_stim, fs=250.0)` returns the mask (l.50-51), the same mask selects the FBCSP windows (`windows[valid_mask == 1]`); counts equal R-3/R-5 in our P05.
- Smoothing: `if i % 5 == 0: avg_p = probs[i] else mean(probs[i-1:i+1])` on the clean array (l.145-151), the reported i%5 rule we use.
- Cohort script (277ddab l.46-101): same flagship (m=1, per-window filtering, scaler + Shrinkage-LDA lsqr, StratifiedKFold 5/42, i%5), output columns `Subject, Clean Windows, Rejected, 1.0s Acc (%), 2.0s Smoothed (%)` (l.103-109), no Mean row. Ours matches R-5.

### What changed in my code
Nothing. Conclusion: the SFS row of R-4 cannot be reproduced from reference code because the reference has no SFS; the plan's SFS definition (scikit-learn SFS, Shrinkage-LDA, 15 FBCSP + 5 FBCCA, in-fold) is a reading of R-4's p=20 and the roadmap text, and our 177/189 with a clean leak audit stays a legitimate, correctly in-fold result. Whether the original SFS ran in-fold or on all windows cannot be decided from the reference. Suggested disposition: accepted deviation for the SFS row with this evidence, or Sebastian supplies the original SFS run or the report's description (the .docx was not inspected).
