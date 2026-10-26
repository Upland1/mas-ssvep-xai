# P12 · 00 · Assignment — Functional connectivity v1: coherence, bias fix, matched baseline

Status: READY
Author: orchestrator
Branch: phase/P12-coherence (from main @ 4c5aa5e, tag p11-done)
Era: B — **R4** (estimator small-sample bias) is enforced from this phase; the averaged per-window coherence is allowed only inside the P12 bug diagnostic (era matrix). Legacy behaviours still required (`team.yaml`): **R3** (no continuous filtering yet; coherence is computed on the raw legacy windows), **fs250** (the frequency axis of the features assumes 250 Hz, PF-04, labelled); the P07 per-script two-tier gate (R5 from P16). R1 and R8 are enforced but do not apply: there is no classifier in this phase.
Owners (agents): connectivity-stats (Connectivity & Stats); scientific-reviewer; verifier
Depends on: P11 (passed; merged 4c5aa5e)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** New work stream: connectivity between channels, stimulus vs no stimulus,
one averaged diagram per condition, MNE-style. Coherence chosen first. The first real
run (S03, S04) exposed two methodological bugs.
**Depends on:** P11. **Owners:** Connectivity & Stats, Scientific Reviewer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/features/connectivity/connectivity_extraction.py` (part 1):
   `CONDITION_FREQS = {101: 24, 102: 20, 103: 15, 104: 10.9091, 105: 8.5714}`,
   `BASELINE_CONDITION = 201`, `BASELINE_BAND = (5, 35)`, half-width 1 Hz;
   `compute_coherence_matrix(window, fs, band, nperseg=min(T,128))` (per-window,
   **diagnostic only**); `compute_condition_coherence(windows, fs, band, nperseg=256)`
   = concatenate the condition's windows per channel and run `scipy.signal.coherence`
   once per pair, band-average; `band_for_condition`; `compute_condition_connectivity`;
   `compute_baseline_matched_connectivity` (re-score the **same 201 windows** in each
   stimulus band); `compute_difference_matrices` (stimulus − matched baseline).
2. **Reproduce both bugs first** (in a notebook-style diagnostic script, kept):
   (a) per-window coherence averaged over windows gives ≈0.32–0.35 for independent
   noise at 256 samples / nperseg 128, vs ≈0.01–0.02 with the concatenated estimator,
   while coupled signals stay ≈0.98–0.99; (b) broadband baseline vs narrow stimulus
   band is not apples-to-apples → matched-baseline difference.
3. `src/visualization/connectivity_plots.py` (mne-connectivity circle plots):
   `plot_condition_connectivity`, `plot_all_conditions_panel` (raw per condition),
   `plot_difference_panel` (diverging `RdBu_r`, symmetric around 0 — the primary
   output), later `plot_permutation_null_distributions`. `CONDITION_LABELS` with
   "No stimulus (201)".
4. `scripts/connectivity/analysis/analyze_connectivity.py --subject S03 --method
   coherence`: raw panel + difference panel + console table.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/features/connectivity/connectivity_extraction.py`, `src/visualization/connectivity_plots.py`, `scripts/connectivity/analysis/analyze_connectivity.py`

## Acceptance (verbatim)

Acceptance: synthetic tests of task 2; S03/S04 baseline coherence drops after the fix
(R-11: from ≈0.68–0.73 to ≈0.59–0.66); differences show 24 Hz and 20 Hz consistently
positive in S03/S04 (≈+0.11 to +0.25) and 10.91/8.57 Hz inconsistent (alpha-band
ceiling hypothesis recorded, to be tested statistically in P13).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-15 | mas/05_PITFALLS.md | per-window coherence averaged is biased upward; fix = concatenate then estimate once |
| PF-16 | mas/05_PITFALLS.md | broadband baseline vs ±1 Hz stimulus band; fix = matched baseline (same 201 windows re-scored in each stimulus band) |
| PF-04 | mas/05_PITFALLS.md | fs 250 legacy in features: bands are on a 250/256-scaled axis; labelled |
| R-11 | mas/04_REFERENCE_RESULTS.md | synthetic and S03/S04 targets; descriptive tolerance ±0.05 on coherence (tolerance table "descriptive statistics" row) |
| R4 | mas/RULES.md | enforced from P12 |
| R2, R6, R9, R10, R11 | mas/RULES.md | no labels fitted; (pair ↔ matrix index) layout proven synthetically; per subject with data source; cite; after-attempt |
| decisions.md P11 | | multi-seed rule applies only to networks (none here); approximate ids on S02/S04 (not used here) |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| connectivity-stats | P12.1–P12.4 | `03_changes_connectivity-stats.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P12.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
