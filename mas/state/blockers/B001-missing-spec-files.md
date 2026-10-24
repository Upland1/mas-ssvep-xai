# Blocker B001: four specification files and phases.yaml were not delivered

- Opened: 2026-10-24 by orchestrator (setup)
- Phase: setup
- blocking: all
- Status: resolved 2026-10-24

## Question

`AGENTS.md` §1 lists the inputs of the rebuild. These are missing from the
package that was delivered (`agents_/`), from the original repository and
from Drive:

| File | Used by | Why it cannot be invented |
|---|---|---|
| `mas/01_DATA_SPEC.md` | P00 inventory (§4 row-for-row), P01 parser (§2 format, dtype table), P02/P16 layouts (§5.1, §5.2) | binary format, the 11 channel names, the 23 files and their sample counts are facts about the recordings |
| `mas/02_REQUIREMENTS.md` | P00 skeleton (§2), config v1/final (§3), smoothing (§5.6), CSV schemas (§6) | defines interfaces every phase is checked against |
| `mas/04_REFERENCE_RESULTS.md` | every acceptance with R-x, and the tolerance rules | the roadmap quotes some R-x values inline, but not R-1, R-2, R-4, R-7, R-10, R-13, R-16, nor any tolerance |
| `mas/05_PITFALLS.md` | PF-07, PF-17, PF-20, PF-22, PF-27, PF-31 and others cited by the roadmap | the reviewer's checklist for historical bugs |

`mas/phases.yaml` was also missing; it has been derived from the roadmap
(see `decisions.md`), which is safe because the roadmap states every
dependency and owner explicitly.

## What was tried

Searched the delivered folder, the original repository
(`reference/ssvep-eeg-xai/`, all branches), the home folder and Google Drive.

## Options and consequences

| Option | Consequence |
|---|---|
| A. Sebastian drops the four files into `mas/` (from the chat that produced the roadmap) | the rebuild runs as specified |
| B. Agents reverse-engineer them from the reference repo | violates R11 and golden rule 10 (inventing specifications); the rebuild would no longer be independent |
| C. Run P00 with only the parts that need no spec | P00 acceptance compares with `01_DATA_SPEC.md` §4, so its gate cannot pass |

## Recommendation

A. Then run `python mas/tools/mas_status.py check` and close this blocker.

## Resolution (Sebastian)

2026-10-24, partial: `01_DATA_SPEC.md`, `04_REFERENCE_RESULTS.md` and
`05_PITFALLS.md` delivered and placed in `mas/`. The delivered
`02_REQUIREMENTS.md` was a byte-identical copy of `01_DATA_SPEC.md` (same
md5) and was discarded. **Still missing: the real `02_REQUIREMENTS.md`**
(repository layout §2, config v1/final §3, smoothing §5.6, CSV schemas §6).
Optional: the updated `03_ROADMAP.md` that adds P03 to the dependencies of
later phases (`SCHEDULING: sequential` already covers it).

2026-10-24, complete: the real `02_REQUIREMENTS.md` and the updated
`03_ROADMAP.md` (P05 now depends on P02, P03) were delivered into `mas/`;
`phases.yaml` updated to match. Two minor spec inconsistencies noted for the
phases concerned: `02_REQUIREMENTS.md` §2 says `docs/` is created in P23 (the
roadmap says P24; the roadmap wins), and config v1 `saved_models_dir:
outputs/saved_models` differs from the roadmap's `outputs/models/` in P04 (to be
settled in the P04 plan).
