# P06 · 00 · Assignment — Feature-selection ablation, legacy 5-subject cohort, report v1

Status: READY
Author: orchestrator
Branch: phase/P06-feature-selection-cohort (from main @ 1929b8d, tag p05-done)
Era: A — legacy behaviours required (`team.yaml`, corrected `RULES.md` era matrix): **R1** window-level `StratifiedKFold(5, shuffle, 42)`; **R3** per-window sub-band filtering; **R8** legacy `i % 5` trial smoothing on the clean array (P05–P10 row); **fs250**; **R5** per-script extractor mask (vpp 0.5–120 µV, std 0.1–35 µV, as P05). 7 channels (config v1).
Owners (agents): ml-engineer (Classical ML), scribe (Scribe, as builder for P06.4); verifier
Depends on: P05 (passed, e444893; merged 1929b8d)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** "finalize methodology report, 5-subject benchmark and infographic"; the
technical report *A Leakage-Free Classical Pipeline for 5-Class SSVEP Decoding Under
a 1.0-Second Constraint* (its "leakage-free" claim was later shown wrong — P11).
**Depends on:** P05. **Owners:** Classical ML, Scribe, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

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

## Run (verbatim)

The roadmap gives no run line for P06. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/features/selection/feature_selection.py`, `benchmark_feature_selection.py`, `reports/five_subjects_benchmark.csv`, `docs/report/v1/`

## Acceptance (verbatim)

Acceptance: ablation = **R-4**; cohort = **R-5** (leaky: 83.33 % / 87.57 %).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-4 | mas/04_REFERENCE_RESULTS.md | S03 ablation: 55 → 90.36/95.43; 45 → 87.31/94.92; ANOVA 25 → 86.29/94.42; MI 25 → 87.82/93.40; SFS 20 → 84.77/93.40. Tolerance ±1.5 pp (deterministic classical; MI and SFS randomness fixed by `random_state=42`), p exact |
| R-5 | mas/04_REFERENCE_RESULTS.md | cohort CSV, counts exact, accuracies ±1.5 pp per subject, mean ±1.0 pp; P05 already reproduced all ten values exactly |
| 02_REQUIREMENTS §6 | | `reports/five_subjects_benchmark.csv` columns `Subject, Clean Windows, Rejected, 1.0s Acc (%), 2.0s Smoothed (%)` |
| PF-01/02 | mas/05_PITFALLS.md | leaky CV and `i % 5` smoothing reproduced (fixed P11); the report v1 title's "leakage-free" claim is historical and wrong |
| PF-11 | mas/05_PITFALLS.md | feature selection (ANOVA, MI, SFS) and CSP fitted inside each training fold only |
| R2, R9, R10, R11 | mas/RULES.md | in-fold selection; per-subject cohort with data source; cite in report v1 only opened sources; `after-attempt` |
| decisions.md P05 | | definitions inherited: i%5 smoothing, mask limits, FBCCA on all 7 channels in the flagship; open: name FBCCA channels in benchmark headers when touched |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| ml-engineer | P06.1–P06.3 — first builder | `03_changes_ml-engineer.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review incl. report v1 | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | P06.4 report v1 + infographic v1 (after the verifier's run, before the results review); then the phase report | `03_changes_scribe.md`, `mas/state/reports/P06.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
