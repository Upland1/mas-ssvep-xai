# P11 · 00 · Assignment — Discover and fix trial leakage

Status: READY
Author: orchestrator
Branch: phase/P11-trial-leakage-fix (from main @ 829602c, tag p10-done)
Era: B — **R1** (trial-grouped CV) and **R8** (smoothing respects trials) are enforced from this phase. Legacy behaviours still required (`team.yaml`, `RULES.md` era matrix): **R3** per-window sub-band filtering; **fs250** in features and in Compact-CNN (K = 29); the P07 per-script two-tier gate (R5 enforced from P16; decisions.md P10 Era-A close row). The leaky splitter and the `i % 5` smoothing must stay reachable behind a flag (era matrix: "must stay reachable behind a flag or a frozen snapshot after the fix lands"); the P04–P10 network CSVs are already frozen under `reports/legacy_leaky/`.
Owners (agents): ml-engineer (Evaluation lead, Classical ML); deep-learning (Deep Learning); scientific-reviewer; verifier
Depends on: P10 (passed; merged 829602c)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** The critical finding of the project: every benchmark used
`StratifiedKFold` on 1 s sub-windows, so the 5 sub-windows of one 5 s trial landed in
both train and test. Fixed with `build_trial_ids` + `StratifiedGroupKFold` in all 9
benchmark scripts.
**Depends on:** P10. **Owners:** Evaluation lead, Classical ML, Deep Learning,
Scientific Reviewer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

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

## Run (verbatim)

The roadmap gives no separate run line; task 5 lists the re-runs. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/preprocessing/dataset/cv_utils.py`, `scripts/diagnostics/demo_cv_leakage.py`, `reports/n_subjects_benchmark.csv`, `reports/augmentation_ab_<model>.csv`

## Acceptance (verbatim)

Acceptance: flagship = **R-6** (S01 61.00/67.50, S02 56.12/61.73, S03 86.80/90.36,
S04 97.46/97.97, S05 95.00/95.50; mean 79.28/82.61); augmentation A/B = **R-9b**;
the before/after table shows the classical pipeline dropping ~4–5 pp and the CNNs
dropping much more (Compact-CNN up to ~20 pp on single subjects); the EEGNet cohort
augmentation gain shrinks from +7.34 pp (last leaky run) to +2.01 pp, while
Compact-CNN (+17.16 pp) and ShallowConvNet (+2.53 pp) keep theirs.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-01 | mas/05_PITFALLS.md | the fix; "inner validation splits grouped too"; test: no trial id in both train and test, for every split helper |
| PF-02 | mas/05_PITFALLS.md | `i % 5` of the clean array is misaligned once a window was rejected; reset at the first window of each true trial |
| PF-03 | mas/05_PITFALLS.md | ids on **pre-gate** labels, indexed with the same `valid_mask`; chained masks `ids[mask1][mask2]`; report `trial_ids_approximate` |
| PF-04, PF-31 | mas/05_PITFALLS.md | fs 250 legacy (K = 29); `compact_cnn` naming |
| PF-28, PF-29, PF-30 | mas/05_PITFALLS.md | A/B seeds, training-fold augmentation, un-augmented train accuracy (unchanged from P10) |
| R-6 | mas/04_REFERENCE_RESULTS.md | flagship target; deterministic classical: per subject ±1.5 pp, cohort mean ±1.0 pp; window counts exact (clean 200/196/197/197/200, rejected 0/3/3/1/0) |
| R-7, R-9b | mas/04_REFERENCE_RESULTS.md | leak-free NN A/B; NN tolerance per subject ±5 pp, cohort ±3 pp, cohort-level sign flip of a Δ must be explained |
| R-5, R-9a, P10 CSVs | mas/04_REFERENCE_RESULTS.md, `reports/legacy_leaky/` | the "before" side of the before/after table |
| R1, R8 | mas/RULES.md | enforced from P11 |
| R2, R6, R9, R10, R11 | mas/RULES.md | in-fold fits; the (trial id ↔ window) index layout proven synthetically; per-subject with data source; cite; `after-attempt` |
| decisions.md P05/P06 | | P06 report open item 3: the legacy-folder 2.0 s smoothing rule for R-6 is open (`i % 5` vs pre-gate trial ids); differs only on S02, S03, S04 |
| decisions.md P10 | | N4 carry-forward: tests that the training dataset length equals the training fold, and that the loader generator is seeded in both arms |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| ml-engineer | P11.1, P11.2, P11.3 (classical scripts + shared splitter/smoothing), P11.4 | `03_changes_ml-engineer.md` |
| deep-learning | P11.3 (network scripts and driver), N4 tests | `03_changes_deep-learning.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | P11.5 runs + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report, README/RESEARCH_LOG/CHANGELOG (P11.5 write-up) | `mas/state/reports/P11.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
