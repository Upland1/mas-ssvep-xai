# P19 · 00 · Assignment — Quality check on the raw segmented signal

Status: READY
Author: orchestrator
Branch: phase/P19-raw-quality (from main @ 86d7d47, tag p18-done)
Era: C. Legacy behaviours required: **none**. Enforced: R3 (continuous filtering, then window; raw windows are cut at the same starts, never filtered per window), R5 (one shared quality decision, every threshold explicit), R6 (window/start layouts), R8, R9 (per subject, with data source), fs from metadata.
Owners (agents): data-signal (Signal Processing); scientific-reviewer; verifier
Depends on: P16 (passed)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Commit "validate windows on the raw segmented signal": filtering can hide
artifacts, so limits may also be checked on unfiltered windows cut at the same
positions.

## Tasks (verbatim from mas/03_ROADMAP.md)

Tasks: `subject_quality_gate(..., raw_windows, raw)` with `params["source"] ∈
{filtered, raw, both}` — a channel or window must pass on every checked signal;
artifact blocks searched on each checked continuous signal; windows failing only on raw
get reason 3; `build_windows.py --quality-source`; config default becomes `both`;
`rejected_by_label` reports reasons 1/2/3.

Numbered for this phase: P19.1 gate (`src/preprocessing/window_quality.py`); P19.2 `scripts/build_windows.py --quality-source`; P19.3 config default `both` (`configs/pipeline_config.yaml`, `02_REQUIREMENTS.md` §3); P19.4 `rejections_by_label` with reasons 1/2/3.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`build_windows.py --quality-source {filtered,raw,both}`, reject reason 3

## Acceptance (verbatim)

Acceptance: per-subject rejection breakdown by reason for filtered/raw/both; flagship
re-run on `both` vs `filtered` (record the difference).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-05 | mas/05_PITFALLS.md | channel tier may drop channels per subject; never hardcode the channel count |
| PF-07 | mas/05_PITFALLS.md | an inherited threshold that rejects everything; raw windows carry slow drifts of ±1,000–5,800 µV (01_DATA_SPEC §4), so the filtered limits applied to raw may reject most windows — report it, never tune limits to the result |
| PF-14 | mas/05_PITFALLS.md | artifact guard and ringing time; the raw continuous signal has no filter, its guard is a design decision (02_plan.md) |
| R-16 | mas/04_REFERENCE_RESULTS.md | no preserved raw-quality numbers; record, reviewer checks direction and plausibility |
| §5.2 | mas/01_DATA_SPEC.md | `X_raw_windows.npy` = unfiltered windows at the same starts; `reject_reason` 3 = failed raw Vpp/std gate |
| §3 | mas/02_REQUIREMENTS.md | `quality.source: filtered` → `both` from P19 |
| decisions P17 C-a | | build_windows refuses to overwrite a folder with different build_params without `--overwrite` (data-signal); P16 masks reproduce only with `--banks fbcca fbcsp` |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-signal | P19.1–P19.4, P17 C-a | `03_changes_data-signal.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | builds, rejection breakdown, flagship re-run | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P19.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
