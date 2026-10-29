# P23 · 00 · Assignment — GNN under LOSO (the project's latest approach)

Status: READY
Author: orchestrator
Branch: phase/P23-gnn-loso (from main @ 3afc0a7, tag p22-done)
Era: C. Legacy behaviours required: **none**. P15's GNN was Era B legacy (fs = 250, legacy folders, per-window filtering); P23 recomputes the P15 graph definitions on the Era C built folders. Enforced: R1 (subject as the LOSO group; trial-grouped validation and within CV), R2 (incl. the test-time-normalization exception for `_subjnorm`), R3 (continuous-filtered windows; phase from the cross-spectral density), R5, R6 (graph array layouts), R8, R9, fs from metadata.
Owners (agents): connectivity-stats (Connectivity & Stats); deep-learning (Deep Learning); data-signal (Infra); ml-engineer (P22 carry-forwards in `benchmark_loso.py`); synthetic-tester; scientific-reviewer; verifier
Depends on: P22 (passed), P15 (passed)
Cohort: S01–S05 (B003 as amended by Sebastian, 2026-10-28).

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Branch `test/GNN-testing-LOSO` (Oct 21): the edge-gated connectivity GNN
trained on all subjects but one, with a within-subject reference on the same windows.

## Tasks (verbatim from mas/03_ROADMAP.md)

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

Numbered for this phase: P23.1 in-memory Era C graph features (P15 definitions); P23.2 `benchmark_gnn_loso.py` (`fit_gnn`, variants × norms, protocols, resumable folds, outputs, smoke test); P23.3 notebook section 10b.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`scripts/connectivity/graph_modeling/benchmark_gnn_loso.py`, notebook section 10b, `reports/loso_gnn/`, `reports/within_gnn/`

## Acceptance (verbatim)

Acceptance: smoke test passes; within and LOSO tables for both variants and both norms;
the report puts them next to `benchmark_loso.py` rows (fbcca, lda, lda_subjnorm,
networks) and interprets train ≈ 100 % / test ≈ chance patterns.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-28 | mas/05_PITFALLS.md | deterministic seeds per fold/seed for A/B variant comparisons |
| PF-30 | mas/05_PITFALLS.md | near-chance test accuracy with high train accuracy: interpret, don't hide |
| PF-32 | mas/05_PITFALLS.md | early-stopping validation = 20 % of training trials, grouped; never the held-out subject |
| PF-33, PF-34 | mas/05_PITFALLS.md | trial-id offsets; same channels for all subjects |
| PF-35 | mas/05_PITFALLS.md | `_subjnorm` is transductive: labelled; offline upper bound (P22 C-4) |
| PF-37 | mas/05_PITFALLS.md | config in every fold; mismatches refused |
| R-15 | mas/04_REFERENCE_RESULTS.md | P15 within-subject GNN (legacy, fs 250): diagnosis only, not a target for Era C numbers |
| R-16 | mas/04_REFERENCE_RESULTS.md | no numeric target; direction checks (LOSO below within; subjnorm ≥ pooled) |
| R1–R9 | mas/RULES.md | as listed in Era |
| decisions P21 C-1..C-6, P22 C-1..C-6 | mas/state/decisions.md | git head at process start + clean worktree; noise-sized margins; ≥ 3 seeds; provenance; fold-config fields (training window counts, build git_commit, config hash); R2 labels in CSVs; never resume into P21 out-dirs; within rows labelled within-subject |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| connectivity-stats | P23.1 | `03_changes_connectivity-stats.md` |
| ml-engineer | P22 C-1 (code_changed docstring, groups to within_lda), P22 C-3 (R2 label column in the warm-up CSV), P22 C-6 (within_lda Data source) | `03_changes_ml-engineer.md` |
| deep-learning | P23.2, P22 C-1 config fields in the GNN harness | `03_changes_deep-learning.md` |
| data-signal | P23.3 | `03_changes_data-signal.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | runs, acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P23.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
