# P24 · 07 · Scientific review

Status: DRAFT
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS / FAIL

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | | |
| R2 Fit only in-fold | | |
| R3 Filter continuous, then window | | |
| R4 Estimator small-sample bias | | |
| R5 Shared quality decision, explicit thresholds | | |
| R6 Index layouts verified | | |
| R7 Honest statistics | | |
| R8 Smoothing respects trials | | |
| R9 Per-subject reporting with data source | | |
| R10 Every change and test cites a source that exists and says what is claimed | | |
| R10 Copied lines marked `# adapted from [n]`, license compatible | | |
| R11 Reference consulted only after an attempt, every consultation listed | | |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | | |
| Tests cover every change; at least one fails on the historical bug | | |
| Changes match 02_plan.md and the roadmap tasks | | |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | | |

### Required fixes

<!-- Only if FAIL. Each names its rule and exact location. -->

1.

### Non-blocking notes

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
