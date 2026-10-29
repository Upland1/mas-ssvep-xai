# P22 · 00 · Assignment — LOSO extensions: within reference, explicit channels, resume guard, warm-up

Status: READY
Author: orchestrator
Branch: phase/P22-loso-extensions (from main @ 62213dc, tag p21-done)
Era: C. Legacy behaviours required: **none**. Enforced: R1 (subject as LOSO group; trial-grouped within CV), R2 (incl. the test-time-normalization exception: warm-up statistics from the first K unlabeled trials = online variant), R5, R8, R9, fs from metadata.
Owners (agents): ml-engineer (Evaluation Lead, Classical ML); synthetic-tester; scientific-reviewer; verifier
Depends on: P21 (passed)
Cohort: S01–S05 (B003 as amended by Sebastian, 2026-10-28: P22–P23 on S01–S05 only).

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Branch `feature/window-size-online-detection` (Oct 15).

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `benchmark_loso.py`: method `within_lda` (within-subject grouped CV on exactly the
   LOSO channels; `--folds 5 --within-repeats 5`); `--channels common | all | <names>`
   (explicit names keep only subjects whose gate accepted every named channel; print
   who is left out and what the gate dropped); saved folds record `channels` and
   `train_subjects`; `check_fold` refuses to mix configurations ("use a new --out-dir").
2. `scripts/benchmarks/benchmark_loso_warmup.py --warmup-trials 1 2 5 10 --channels`:
   for each held-out subject, sort its trials by first window start (recording order);
   use the first K trials (unlabeled) to estimate normalization statistics; score only
   trials after K with: `full` (whole-session statistics = lda_subjnorm), `warmup`
   (first-K statistics), `none` (plain lda); report warm-up windows, classes seen, span
   in seconds; cohort table with `warmup − full`.

Numbered for this phase: P22.1 `within_lda`; P22.2 explicit `--channels <names>`; P22.3 fold config record and `check_fold` refusal; P22.4 `benchmark_loso_warmup.py`.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`benchmark_loso.py within_lda/--channels/check_fold`, `benchmark_loso_warmup.py`

## Acceptance (verbatim)

Acceptance: both scripts run; a changed configuration on an existing out-dir is
refused; warm-up table produced (record).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-34 | mas/05_PITFALLS.md | explicit channel lists leave out subjects whose gate rejected a named channel |
| PF-35 | mas/05_PITFALLS.md | `full` = whole-session test-time normalization (offline upper bound); `warmup` = first K trials (online) |
| PF-36 | mas/05_PITFALLS.md | trial ids follow class order in built folders; recording order = sort by first window start |
| PF-37 | mas/05_PITFALLS.md | saved folds store config; a rerun with different settings refuses ("use a new --out-dir") |
| R-16 | mas/04_REFERENCE_RESULTS.md | no numeric target; record; reviewer checks direction (`warmup` between `none` and `full` as K grows) |
| R1, R2, R8, R9 | mas/RULES.md | grouping, in-fold fits, smoothing, per-subject reporting |
| decisions P21 C-1..C-6 | mas/state/decisions.md | git_head at process start + dirty flag, refusal on src/scripts head differences; flag/refuse methods with fewer folds than the cohort; noise-sized prediction margins; matched channel sets; provenance record; privacy-scan wording |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| ml-engineer | P22.1–P22.4, P21 C-1, C-2 | `03_changes_ml-engineer.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | runs, acceptance, refusal check | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P22.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
