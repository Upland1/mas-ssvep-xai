# P24 · 00 · Assignment — Documentation and deliverables

Status: READY
Author: orchestrator
Branch: phase/P24-documentation (from main @ 4c95386, tag p23-done)
Era: D (close-out). Legacy behaviours required: **none**. Enforced: R9 (per-subject numbers with data source), R10 (cite every source; only what was opened), R11, golden rule 5 (numbers exactly from CSVs, never tuned).
Owners (agents): scribe (documents); data-signal (Infra: `make all`); scientific-reviewer; verifier
Depends on: P23 (passed)
Cohort: S01–S05 for every main result; the P21 39-subject classical LOSO is a separate data source (B003 as amended).

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** The project's written outputs: README with results, the academic technical
report, the methodology infographic/poster, the consolidated progress report for the
professor.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `README.md` (replaces the operator README): overview, task table (conditions and
   frequencies), results (flagship corrected table, NN augmentation A/B with parameter
   counts, connectivity gate, GNN, connectivity statistics, Era-C results), models
   table with references, deep-learning training convention, pipeline diagram,
   preprocessing/quality description, trial-grouped CV, features, augmentation,
   connectivity workflow, repository structure, usage for every script, trial-grouping
   fix section (before/after), interpretation notes and open questions, environment,
   dataset policy.
2. `RESEARCH_LOG.md`: chronological narrative P00 → P23 with every before/after.
3. `docs/report/`: updated academic report (Abstract, Introduction, Materials and
   Methods, Results, Discussion, Conclusion, References; ~5 pages; concise journal
   style; confusion matrices only in Results/Discussion; numbers exactly from CSVs;
   corrected leak-free numbers; reference: Chailloux Peguero et al. 2023).
4. `docs/infographic/`: one-page methodology infographic (pipeline, protocol, key
   numbers).
5. `docs/progress_report/`: consolidated report for the professor covering every
   assignment (edge effects, continuous filtering, valid windows, 6th class, harmonic /
   intermediate bands, NBS vs FDR graph sizes, detection/window sweep, pseudo-online,
   LOSO, GNN LOSO) with results and open questions.
6. `make all` (or `scripts/run_all.sh`) regenerating every CSV from `data/raw/`.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`README.md`, `RESEARCH_LOG.md`, `docs/report/`, `docs/infographic/`, `docs/progress_report/`, `Makefile all`

## Acceptance (verbatim)

Acceptance: the Reviewer checks every number in the documents against a CSV;
`make all` succeeds on a clean clone with only `data/raw/` added.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R9, R10, R11 | mas/RULES.md | per-subject numbers with data source; cite only opened sources; reference consultations listed |
| PF-31 | mas/05_PITFALLS.md | `compact_cnn` vs `compact_eegnet` named distinctly in every table |
| R-1..R-16 | mas/04_REFERENCE_RESULTS.md | reference numbers quoted as targets for diagnosis, never as this repository's results |
| mas/CITING.md | | source formats; the reference paper as given in `mas/01_DATA_SPEC.md` §3 |
| decisions (all phases) | mas/state/decisions.md | accepted deviations and carry-forwards to state as open questions; the per-phase wording rulings (offline upper bound, "direction not observed", "GNN ≥ lda on S02/S05", PF-30 readings) |
| AGENTS.md, project Git rules | | no tool or vendor mention in any committed document |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-signal | task 6 (`make all` and per-phase targets, runtime table) | `03_changes_data-signal.md` |
| scribe | tasks 1–5 | `03_changes_scribe.md` |
| scientific-reviewer | pre-run audit; number check of every document | `07_review.md` |
| verifier | `make all` on a clean clone; document-number cross-check | `05_run.md`, `06_verify.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
