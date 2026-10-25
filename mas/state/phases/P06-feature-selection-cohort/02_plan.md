# P06 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md (corrected R8 row), mas/02_REQUIREMENTS.md §4–§6, mas/04_REFERENCE_RESULTS.md R-4, R-5, mas/05_PITFALLS.md PF-01/02/11, P05 rows of decisions.md, mas/state/reports/P05.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Reproduce the original's feature-selection ablation on S03 (R-4) and its legacy
5-subject cohort table (R-5), and write the historical technical report v1 with its
methodology infographic.

## Data source

Legacy folders `data/processed/<S>/` (P02), stimulus windows, the P05 extractors and
definitions unchanged (fs 250, mask vpp 0.5–120 / std 0.1–35, FBCSP m=1 on 5 bands +
FBCCA on all 7 channels, scaler + Shrinkage-LDA lsqr, window-level
`StratifiedKFold(5, shuffle, 42)`, reported 2.0 s = `i % 5` trial smoothing).

## Scope

**In:** P06.1–P06.4. **Out:** two-tier gate / 8 channels (P07), trial-grouped CV (P11).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| ml-engineer | NEW `src/features/selection/__init__.py` (if missing), `src/features/selection/feature_selection.py` | `select_k_best_fbcsp_features(X_tr, y_tr, n_features_to_select=15, method="anova"|"mutual_info", random_state=42)` → indices of the selected FBCSP columns, fitted on the training fold only (`SelectKBest(f_classif)` / `mutual_info_classif(random_state=42)`); a helper that returns the FBCSP-subset + all 5 FBCCA columns | P06.1 | [2] |
| ml-engineer | NEW `scripts/benchmarks/feature_based/benchmark_feature_selection.py` | `--subject S03 --k-features 20`; five rows, each → scaler + Shrinkage-LDA inside the same legacy folds as the P05 flagship: full (55); sub-band pruning (FBCSP bands without (38, 52) → 40 + 5 = 45); ANOVA top-k + FBCCA (20 + 5 = 25); MI top-k + FBCCA (25); SFS: `SequentialFeatureSelector(Shrinkage-LDA, n_features_to_select=15, direction="forward")` on the 50 FBCSP columns of the training fold (its inner CV default), + 5 FBCCA = 20. All selection in-fold. CSV `reports/feature_selection_ablation_<S>.csv` (`Subject, Method, p, 1.0s Acc (%), 2.0s Smoothed (%), Clean Windows, Rejected`) | P06.2 | [2], R-4 |
| ml-engineer | NEW `scripts/benchmarks/feature_based/benchmark_5_subjects.py` | the P05 flagship (reuse its code path, no re-implementation) for every discovered subject → `reports/five_subjects_benchmark.csv` with the 02_REQUIREMENTS §6 columns + a `Mean` row; console states the legacy labels | P06.3 | [2], [1] §6 |
| scribe (builder) | NEW `docs/report/v1/report.md`, `docs/report/v1/methodology_infographic_v1.svg` | written **after** the verifier's run from its CSVs/logs; academic structure per [2] P06.4, ~5 pages, ablation + cohort tables verbatim from the CSVs; the historical title kept with a boxed note under it: "Historical document (P06). Its 'leakage-free' claim was later shown wrong: window-level CV leaks trials (P11)". References only to sources opened in this run (R10). Infographic: the pipeline flow (OO recording → 1–60 Hz filter → 1 s windows → mask → FBCSP + FBCCA → scaler → Shrinkage-LDA → i%5 smoothing) as a hand-written SVG, labelled v1/historical | P06.4 | [2], R10 |

Settled points (decisions.md): SFS uses the function default 15 FBCSP columns (+ 5 FBCCA
= 20, R-4's p); ANOVA and MI use `--k-features 20` (+ 5 = 25); sub-band pruning drops
the (38, 52) band only; report v1 as Markdown + SVG; v1 keeps its historical title with
the correction note.

## Legacy behaviour in this phase

As P05 (R1, R3, R5 per-script mask, R8 `i % 5`, fs 250), labelled in code, console and
CSV/`.meta.txt`; report v1 states them as the methods of that time and carries the
correction note.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R2/PF-11 | selection (ANOVA/MI/SFS) or CSP fitted on all windows | fit inside each training fold; test with a planted test-only feature |
| R6 | FBCSP column → band mapping wrong for sub-band pruning | known-answer test: dropping band 5 removes exactly columns 40–49 (layout from P05) |
| R-4/R-5 | numbers off | ±1.5 pp; one investigation round; R11 after it (diagnostics first, then the reference) |
| R10 | report v1 cites unopened papers | scribe cites only opened sources |
| Interpretation | report v1 repeats the leakage-free claim as true | correction note mandatory, reviewer checks |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| ANOVA selection | 50 FBCSP columns, columns 7 and 31 class-informative | both selected for k ≥ 2; indices within 0–49; FBCCA always appended | exact | [2] P06.1 |
| MI selection | as above, `random_state=42` twice | identical indices | exact | [2] |
| in-fold | informative column only in test rows | not selected; full-data fit would select it | exact | PF-11 |
| sub-band pruning | 55-column layout | drop indices 40–49, keep 0–39 + 50–54 → 45 | exact | R6, P05 layout |
| SFS | small synthetic | `n_features_to_select=15` → 15 + 5 = 20 columns, chosen on training rows only | exact | [2], R-4 p |
| p values | script on synthetic tree | 55, 45, 25, 25, 20 | exact | R-4 |
| cohort CSV | script on synthetic tree | §6 columns, one row per subject + Mean = column means | exact | [1] §6 |
| smoothing | as P05 | `i % 5` reported | exact | decisions.md P05 |

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_5_subjects
```

Runtime: SFS is the cost (15 forward steps × up to 50 candidates × inner 5-fold LDA ×
5 outer folds ≈ 25k LDA fits on ~160 × ≤ 20 features); builder measures. Expected
≪ 120 min.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| ablation = **R-4** | `reports/feature_selection_ablation_S03.csv` vs R-4 row by row: p exact, 1.0 s and 2.0 s ±1.5 pp (also as window counts of 197) | R-4 |
| cohort = **R-5** (leaky: 83.33 % / 87.57 %) | `reports/five_subjects_benchmark.csv` vs R-5: counts exact, per subject ±1.5 pp, mean ±1.0 pp | R-5 |
| report v1 + infographic exist (P06.4) | files present, sections present, tables equal the CSVs, correction note present | [2] P06.4 |

## Sources

1. `mas/02_REQUIREMENTS.md` §4–§6 (opened in this run).
2. `mas/03_ROADMAP.md` P06 (opened in this run).
3. `mas/04_REFERENCE_RESULTS.md` R-4, R-5; `mas/05_PITFALLS.md`; `mas/state/reports/P05.md` (opened in this run).
4. scikit-learn `SelectKBest`, `f_classif`, `mutual_info_classif`, `SequentialFeatureSelector` docs (builder opens and cites).

## Questions
