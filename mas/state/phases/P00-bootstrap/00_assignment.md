# P00 · 00 · Assignment — Bootstrap and data intake

Status: READY
Author: orchestrator
Branch: phase/P00-bootstrap (from main @ d9da2ff)
Era: A — legacy behaviours required in this phase: none (no rule of the era matrix in `mas/RULES.md` applies to bootstrap or a header inventory)
Owners (agents): data-engineer (roles Data Engineer + Infra, `mas/state/team_mapping.md`); verifier (gate check); orchestrator (bookkeeping)
Depends on: — (first phase)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Repository setup and first contact with the recordings.
**Depends on:** —. **Owners:** Orchestrator, Data Engineer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. Create the repository skeleton of `02_REQUIREMENTS.md` §2 (empty packages with
   `__init__.py`), `requirements.txt`, `environment.yml`, `Makefile` (targets added
   per phase), `pytest.ini`, `CHANGELOG.md`, `RESEARCH_LOG.md`, and `mas/state/`
   (`phase_status.yaml` with all 26 phases `pending`, `decisions.md`).
2. `scripts/exploration/inventory_raw.py`: walk `data/raw/S*/`, parse every `.ebr`
   header only (fast path) and the MARK channel, print and save
   `reports/raw_inventory.csv` with the columns of `01_DATA_SPEC.md` §4 plus channel
   list and event-code counts. Exit non-zero on any deviation from the spec (fs ≠ 256,
   channel list ≠ the 11 names, calibration runs without 40 trials of 8 × 5 targets).
3. Confirm `.gitignore` covers all data (`git check-ignore data/raw/S01/OO.ebr`).

## Run (verbatim)

```bash
python scripts/exploration/inventory_raw.py
```

## Outputs (verbatim)

Outputs: skeleton, `reports/raw_inventory.csv`.

## Acceptance (verbatim)

Acceptance: inventory matches `01_DATA_SPEC.md` §4 row for row (samples, duration,
stim events); `git status` shows no data files; `pytest -q` runs (zero tests is OK).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| 01_DATA_SPEC §1–§4 | mas/01_DATA_SPEC.md | layout, `.ebr` format, MARK onset rule, the 23-row inventory to reproduce; subjects discovered by `^S\d+$`, non-`.ebr` files ignored |
| Tolerance "window counts … exact" | mas/04_REFERENCE_RESULTS.md (tolerance rules) | samples and stim-event counts are integer facts: exact match; duration to 0.1 s; session start to the minute; 99th pct to 0.1 µV |
| PF-09 | mas/05_PITFALLS.md | spirit only: fail loudly on inconsistent inputs instead of continuing |
| PF-13 | mas/05_PITFALLS.md | 202 is a cue code, counted but never treated as a baseline |
| R9 | mas/RULES.md | per-subject rows with the session file named |
| R10 | mas/RULES.md, mas/CITING.md | the data spec is the source of every expected value |
| R11 | mas/RULES.md | `REFERENCE_POLICY: after-attempt`; log any consultation |
| No R-x target | mas/04_REFERENCE_RESULTS.md | the reference for P00 is `01_DATA_SPEC §4` (phases.yaml `references`) |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-engineer | P00.1 (skeleton, env files incl. `.venv`, Makefile, pytest.ini, CHANGELOG, RESEARCH_LOG; `phase_status.yaml` and `decisions.md` already exist — created by the orchestrator via `mas_status.py init`), P00.2 (inventory script), P00.3 (gitignore check) | `03_changes_data-engineer.md` |
| synthetic-tester | known-answer tests for the inventory script on synthetic `.ebr` files | `04_tests.md` |
| scientific-reviewer | pre-run audit and results review | `07_review.md` |
| runner | run command above | `05_run.md` |
| verifier | gate check | `06_verify.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
