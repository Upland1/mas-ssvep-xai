# P01 · 00 · Assignment — EBR parser and configuration v1

Status: READY
Author: orchestrator
Branch: phase/P01-ebr-parser (from main @ b502144, tag p00-done)
Era: A — legacy behaviours required in this phase: no numbered rule of the `mas/RULES.md` era matrix applies; the config v1 hard-excludes PO7 (legacy until P07: `mas/02_REQUIREMENTS.md` §3 v1, `mas/01_DATA_SPEC.md` §2 montage, PF-05) and must be labelled `legacy`
Owners (agents): data-engineer (Data Engineer, `mas/state/team_mapping.md`); verifier (gate check)
Depends on: P00 (passed, 754c418; merged to main b502144)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** First module of the original project: read the binary format directly.
**Depends on:** P00. **Owners:** Data Engineer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/io/ebr_parser.py`: `load_ebr_file(path) -> dict` exactly per
   `01_DATA_SPEC.md` §2; helpers `resolve_recording_path(raw_root, session, filename)`,
   `select_scalp_channels(channels, scalp_names) -> list[int]`,
   `get_mark_channel_index(channels, mark_name="MARK") -> int` (−1 if absent),
   `extract_scalp_signal(recording, scalp_names) -> (matrix (C, T), names)`.
2. `configs/pipeline_config.yaml` **v1** (`02_REQUIREMENTS.md` §3) — PO7 excluded.
3. `src/preprocessing/signal/filters.py`: `apply_iir_bandpass(data, fs, lowcut=1.0,
   highcut=60.0, order=4)` = `scipy.signal.iirfilter(order, [low/nyq, high/nyq],
   btype="bandpass", ftype="butter")` + `filtfilt` along the last axis.
4. Tests: EBR round-trip, dtype table, unsupported dtype error.

## Run (verbatim)

The roadmap gives no run line for P01. See `02_plan.md` for the run that checks the acceptance.

## Outputs (verbatim, from mas/phases.yaml)

`src/io/ebr_parser.py`, `configs/pipeline_config.yaml (v1)`, `src/preprocessing/signal/filters.py`

## Acceptance (verbatim)

Acceptance: parsing all 23 files gives the inventory of P00; tests pass.

Applied with blocker B005 (resolved, option B, `mas/state/decisions.md`): the
delivered dataset is the 10 files OO, mOO of S01–S05. "All 23 files" is read as
"all delivered files (10)"; "the inventory of P00" is `reports/raw_inventory.csv`
of the P00 run (log `reports/logs/P00/inventory_raw_20261024_141334.log`).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| 01_DATA_SPEC §2 | mas/01_DATA_SPEC.md | the parser contract: header keys, dtype table, `(nt, nc, nb, ns)` C order, real types cast to float64, complex not cast, returned dict keys, `ValueError` on unknown dtype |
| 02_REQUIREMENTS §3, §4, §7 | mas/02_REQUIREMENTS.md | config v1 verbatim; root found via `configs/pipeline_config.yaml`; library code without side effects, type hints, docstrings; EBR round-trip test |
| PF-05 | mas/05_PITFALLS.md | PO7 excluded in v1 on purpose (legacy); fixed in P07 |
| PF-06 | mas/05_PITFALLS.md | channels selected by **name**, never by position |
| PF-04 | mas/05_PITFALLS.md | `apply_iir_bandpass` takes `fs` as an argument; no 250 default here (the 250 assumption lives in Era A feature code, not in P01) |
| R6 | mas/RULES.md | the `(nt, nc, nb, ns)` reshape is proven by a synthetic case with a known answer |
| R9, R10, R11 | mas/RULES.md | per-file rows; sources cited; `REFERENCE_POLICY: after-attempt` |
| B005 | mas/state/blockers/ | 10 delivered files, not 23 |
| No R-x target | mas/04_REFERENCE_RESULTS.md | the reference is the P00 inventory |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-engineer | P01.1–P01.3, and the inventory switch to the parser described in `02_plan.md` | `03_changes_data-engineer.md` |
| synthetic-tester | P01.4 and the plan's known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit and results review | `07_review.md` |
| runner | the plan's run command | `05_run.md` |
| verifier | gate check | `06_verify.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
