# P14 · 00 · Assignment — Cross-frequency comparison, reliability, and power/alpha confounds

Status: READY
Author: orchestrator
Branch: phase/P14-cross-frequency-confounds (from main @ 997635a, tag p13-done)
Era: B. Legacy behaviour required (`team.yaml`): **fs250**, the feature frequency axis, including the confound periodograms (PF-04, labelled). These are enforced: R1–R4, R6, R7 (trial-level permutations), R8 and R3 for phase. The per-script shared gate continues (R5 from P16). Trial ids on S02/S04 are approximate (P11 D-2) and are flagged.
Owners (agents): connectivity-stats (Connectivity & Stats); scientific-reviewer; verifier
Depends on: P13 (passed; merged 997635a)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Professor's follow-up: how to compare connectivity across stimulation
frequencies; then whether the deltas are just SSVEP power or alpha blocking.
**Depends on:** P13. **Owners:** Connectivity & Stats, Scientific Reviewer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `scripts/connectivity/comparison/compare_connectivity_frequencies.py`
   (descriptive, on **delta** matrices only): load edge files, embed each subject's
   matrix into the 8×8 montage with NaN for missing channels; per subject and method:
   Pearson r between off-diagonal entries of every frequency pair with a one-tailed
   **QAP** node-label permutation p (2,000 permutations, ≥6 finite pairs, ≥4 shared
   channels); node strength per channel (symmetrized, mean to others); global mean
   delta and FDR-edge count per frequency. Group summaries for all / responders /
   non-responders, where **responders are defined from classifier performance**
   (2.0 s smoothed accuracy ≥ 80 % in `n_subjects_benchmark.csv`, or `--responders`),
   never from connectivity (circular). Fisher-z averaging of r across subjects.
   Figures: similarity matrices, node strength, delta matrices per group. CSVs per §6.
2. `scripts/connectivity/comparison/test_connectivity_frequency_differences.py`
   (coherence, PLV, wPLI; PDC excluded): per subject, trial-level split-half
   reliability of each delta matrix (random halves of trials, 10 splits, Fisher-mean r,
   Spearman-Brown `2r/(1+r)` only if r > 0, else report r uncorrected — PF-22);
   pairwise test per frequency pair with trial-level permutations (500, ≥1000 for
   final): magnitude statistic = mean upper-triangle (Δa − Δb), two-sided; pattern
   statistic = 1 − r(Δa, Δb), one-sided; edge-level two-sided p + BH-FDR; reliability
   ceiling `sqrt(rel_a·rel_b)`, disattenuated r (only if ceiling > 0.1); BH across pairs
   per subject; Fisher-combined p across responders; flag approximate trial ids.
3. `scripts/connectivity/diagnostics/check_power_alpha_confound.py`: per subject and
   frequency on O1/Oz/O2 Hann periodograms: `target_snr_db = 10 log10(P_stim/P_base)`
   in f0 ± 1 Hz; `alpha_change_db` in 8–13 Hz **excluding f0 ± 1.5 Hz**; merge with
   `<method>_global_delta.csv`; Spearman (all cells, and within-subject centered), OLS
   R² of `delta ~ SNR + alpha`; in-alpha (10.91, 8.57) vs out-of-alpha means; scatter
   figure `connectivity_delta_vs_power.png`. (The original has a misspelled duplicate
   `check_power_alpha_cofound.py`; create only the correct name — PF-27.)

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`compare_connectivity_frequencies.py`, `test_connectivity_frequency_differences.py`, `check_power_alpha_confound.py`, `reports/connectivity_comparison/`

## Acceptance (verbatim)

Acceptance: CSVs and figures per §6; the report states, with numbers, how much of
the delta is explained by target SNR and alpha change and whether 10.91/8.57 Hz
behave differently (no fixed numeric target; compare qualitatively with R-13).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-21 | mas/05_PITFALLS.md | responders from `reports/n_subjects_benchmark.csv`, 2.0 s ≥ 80 % (S03, S04, S05), never from connectivity |
| PF-22 | mas/05_PITFALLS.md | Spearman-Brown only for r > 0 |
| PF-23 | mas/05_PITFALLS.md | alpha band excludes f0 ± 1.5 Hz for stimulus and baseline |
| PF-24 | mas/05_PITFALLS.md | delta matrices only; read QAP p, not raw r; no path-length measures on signed deltas |
| PF-25 | mas/05_PITFALLS.md | PDC symmetrized before node strength |
| PF-26 | mas/05_PITFALLS.md | embed into the 8 × 8 montage with NaN via `channels_kept` |
| PF-27 | mas/05_PITFALLS.md | only `check_power_alpha_confound.py` |
| PF-03, PF-04, PF-19 | mas/05_PITFALLS.md | pre-gate ids; fs 250 axis; trial-level permutations with matched sizes |
| R-13 | mas/04_REFERENCE_RESULTS.md | qualitative comparison only (no fixed numeric target) |
| decisions.md P12–P13 | | shared gate; nested nulls and BH resolution (P13 D-4); the S05 exploratory pattern (P13 D-3); shared colour limits across subjects (P12 D-4) |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| connectivity-stats | P14.1–P14.3 | `03_changes_connectivity-stats.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P14.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
