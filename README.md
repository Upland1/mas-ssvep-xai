# mas-ssvep-eeg-xai

A from-zero, multi-agent rebuild of an SSVEP brain-computer-interface research
pipeline (5-class decoding from 8-channel parieto-occipital EEG). The rebuild
replays the original project's history in 26 gated phases, P00–P25: legacy
pipeline, the trial-leakage discovery and fix, connectivity statistics and
graph models, continuous filtering at the true 256 Hz, detection and
pseudo-online decoding, and leave-one-subject-out evaluation. Every result is
backed by a logged run, and every fix ships with a before/after table.

This README is the operator's guide; phase P24 replaces it with the full
project documentation.

## Where to start

| Read | For |
|---|---|
| `AGENTS.md` | mission and golden rules |
| `mas/README.md` | team, phase workflow, hand-off contract, human gates |
| `mas/RULES.md` | methodological rules R1–R11 and when each is enforced |
| `mas/03_ROADMAP.md` | the 26 phases, their tasks and acceptance criteria |
| `mas/state/` | live state: phase status, hand-offs, reports, decisions, blockers |

## Status

```bash
python mas/tools/mas_status.py check   # preflight
python mas/tools/mas_status.py show    # phase table (after P00 init)
```

Open blockers are in `mas/state/blockers/`.

## Data policy

The recordings are private human-subject data and are never committed.
`data/`, generated arrays, models, reports and outputs are git-ignored; see
`.gitignore`.
