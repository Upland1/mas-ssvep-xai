# P03 · 00 · Assignment — Exploration and signal verification

Status: READY
Author: orchestrator
Branch: phase/P03-exploration (from main @ df229bd, tag p02-done)
Era: A — legacy behaviours required in this phase: `fs250` (`team.yaml`; `02_REQUIREMENTS.md` §5.4, PF-04): the scripts read legacy arrays that store no sampling rate and assume 250 Hz, labelled `legacy` (see `02_plan.md` Q1); 7 channels from config v1 (PF-05)
Owners (agents): signal-processing (Signal Processing); scientific-reviewer (owner per roadmap: confirms peaks); verifier
Depends on: P02 (passed, 214d7c9; merged to main df229bd)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** `visualize_data.py`, `diagnose_occipital_spectra.py`: sanity checks
before modelling.
**Depends on:** P02. **Owners:** Signal Processing, Scientific Reviewer.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `scripts/exploration/diagnose_occipital_spectra.py`: occipital (by name) FFT power
   per class, 5–35 Hz, with the target frequency marked; one panel per class.
2. `scripts/exploration/visualize_data.py --subject`: load windows, run the quality
   mask, select stimulus windows, compute PSD / FBCCA / FBCSP features (FBCCA/FBCSP
   arrive in P05 — extend this script then) and plot them per class.
3. Write the first `RESEARCH_LOG.md` entry: which subjects show clear SSVEP peaks.

## Run (verbatim)

The roadmap gives no run line for P03. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`scripts/exploration/diagnose_occipital_spectra.py`, `scripts/exploration/visualize_data.py`

## Acceptance (verbatim)

Acceptance: figures exist; the Reviewer confirms visible fundamental peaks for the
strong responders and records what is seen for S01/S02.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-04 | mas/05_PITFALLS.md | legacy `fs=250` on 256 Hz data scales the frequency axis by 250/256 (24 → 23.44, 20 → 19.53, 15 → 14.65, 10.91 → 10.65, 8.57 → 8.37 Hz; `.venv/bin/python` arithmetic in log.md step 2); reproduced and labelled, never silently mixed with header fs |
| PF-06 | mas/05_PITFALLS.md, 01_DATA_SPEC §6 | occipital set `O1, Oz, O2` selected **by name** (names from config v1 `scalp`, length checked against the array) |
| PF-09 | mas/05_PITFALLS.md | read `data/processed/<S>/`, never the root arrays; lengths of X and y checked |
| R5 | mas/RULES.md | per-script quality mask is LEGACY (by design) before P16; every threshold passed explicitly |
| R9 | mas/RULES.md | per-subject figures and statements; data source "legacy, data/processed/<S>/ from P02, OO" |
| P02 carry-forward | mas/state/decisions.md | S01 101 trials peak at 10 Hz with no 24 Hz peak; S01/S02 no clear peaks; S03 8.57 Hz plateau in 7-channel mean; 201/202 twins (P03 uses stimulus windows only) |
| R-x | mas/04_REFERENCE_RESULTS.md | no numeric target for P03 |
| R10, R11 | mas/RULES.md | cite; `after-attempt` |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| signal-processing | P03.1, P03.2 | `03_changes_signal-processing.md` |
| synthetic-tester | known-answer tests of the plan | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review = the roadmap acceptance (peaks per subject, S01/S02 observations) | `07_review.md` |
| runner | plan run commands | `05_run.md` |
| verifier | gate check | `06_verify.md` |
| scribe | P03.3 (RESEARCH_LOG entry from the reviewer's findings) with the phase report | `mas/state/reports/P03.md`, `RESEARCH_LOG.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
