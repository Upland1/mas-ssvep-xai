# Blocker B003: which cohort do P20–P23 (window sweep, LOSO, GNN LOSO) use?

- Opened: 2026-10-24 by orchestrator (setup)
- Phase: P20
- blocking: none (decide before P20)
- Status: open

## Question

The original LOSO results came from a 39-subject window-sweep build
(S01–S040, no S020). This rebuild receives raw data for S01–S05 only, and P23
quotes runtimes "for 5 subjects". LOSO on 5 subjects is a much weaker
generalization test than on 39.

Update 2026-10-24: raw recordings for **40 subjects** (S01–S040, including
S020) exist on this laptop in `../SSVEPs_OO_mOO/`, outside the repository.
The cohort is therefore a decision, not a data-availability limit. Every
reference number (R-1 to R-15) is a 5-subject result, and the P00 inventory
(`01_DATA_SPEC.md` §4) lists S01–S05 only.

## Options and consequences

| Option | Consequence |
|---|---|
| A. S01–S05 only | matches the roadmap text; LOSO numbers not comparable with the original's 39-subject results |
| B. S01–S05 for P00–P20; all 40 for P21–P23 (LOSO) | LOSO comparable with the original's cohort; the extra subjects are added only when P21 opens, so the P00 inventory still matches §4; builds and LOSO become human runs |

## Recommendation

A for the gates, and B as an extra human run if the recordings are
available, reported as a separate data source (R9).

## Resolution (Sebastian)
