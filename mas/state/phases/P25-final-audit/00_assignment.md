# P25 · 00 · Assignment — Final audit

Status: READY
Author: orchestrator
Branch: phase/P25-final-audit (from main @ 845a453, tag p24-done)
Era: D (close-out). Legacy behaviours required: **none**. Every rule R1–R11 is audited across all phases, with legacy rows checked against the era matrix of `mas/RULES.md`.
Owners (agents): verifier; scientific-reviewer; orchestrator (scribe for the report)
Depends on: P24 (passed)
Cohort: S01–S05 for every main result; the P21 39-subject classical LOSO is a separate data source (B003 as amended).

## Origin (verbatim from mas/03_ROADMAP.md)

The roadmap gives no separate origin line for P25: "### P25 — Final audit. **Depends on:** P24. **Owners:** Verifier, Scientific Reviewer, Orchestrator."

## Tasks (verbatim from mas/03_ROADMAP.md)

1. Clean-machine rebuild and full test suite.
2. Leakage audit: for every script that splits data, show the split code and the test
   that guards it.
3. Reference comparison: table of every R-x target vs obtained value, status
   (within tolerance / explained deviation / unexplained).
   Autonomy report: every reference consultation (rule 8) across all phases, with
   its trigger, and the share of phases completed without any consultation.
   Sources report: every phase report has a complete `## Sources` list.
4. Diff module by module against `Upland1/ssvep-eeg-xai` (main + `feature/window-size-online-detection` +
   `test/GNN-testing-LOSO`) and list capabilities missing on either side.
5. Final report `mas/state/reports/P25.md` and tag `v1.0`.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`mas/state/reports/P25.md`, tag `v1.0`

## Acceptance (verbatim)

Acceptance: no unexplained deviations; no open blockers; all phases `passed`.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R1, R2, PF-01, PF-32–PF-35 | mas/RULES.md, mas/05_PITFALLS.md | leakage audit: grouped splits, in-fold fitting, LOSO groups, test-time normalization labels |
| R-1..R-16 | mas/04_REFERENCE_RESULTS.md | the comparison table; targets for diagnosis, never tuned |
| R10, mas/CITING.md | | the sources report |
| R11, AGENTS.md rule 8 | `mas/state/scratch/reference_access.log`, every handoff | the autonomy report; P25 task 4 is a consultation to verify finished, passing work, and is logged |
| decisions (all phases) | mas/state/decisions.md | accepted deviations (B006, B007, P24 A-1..A-6) count as explained |
| AGENTS.md, project Git rules | | no tool or vendor mention in any committed file |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| verifier | 1 (clean checkout, full suite, rebuild evidence), 3 (reference table, autonomy report, sources report) | `05_run.md`, `06_verify.md` |
| scientific-reviewer | 2 (leakage audit), 4 (module diff against the reference repository), results review | `07_review.md` |
| scribe | 5 (`mas/state/reports/P25.md`) | `mas/state/reports/P25.md` |
| orchestrator | 5 (gate, merge, tags `p25-done` and `v1.0`) | `log.md`, `decisions.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
