# P17 · 00 · Assignment — Sixth (rest) class and the harmonic / intermediate filter bank

Status: READY
Author: orchestrator
Branch: phase/P17-rest-class-filterbank (from main @ d52a5d5, tag p16-done)
Era: C. Legacy behaviours required in this phase: **none** (`team.yaml`). Enforced: R1 (StratifiedGroupKFold over true trial ids), R2, R3 (new banks filtered on the continuous signal), R5 (shared quality, explicit thresholds), R6 (band layout), R8 (trial-reset smoothing on built folders), R9, fs from metadata.
Owners (agents): data-signal (Signal Processing); ml-engineer (Classical ML); scientific-reviewer; verifier
Depends on: P16 (passed; merged d52a5d5)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Branch `feature/rest-class-harmonic-filterbank`: add the fixation cross as
a 6th class (detecting "no stimulus"), and add harmonic and between-frequency bands to
the filter bank.
**Depends on:** P16. **Owners:** Signal Processing, Classical ML, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `windowing.py`: `STIM_FREQS`, `harmonic_centers(n_harmonics=3)` (k·f for k=1..3),
   `intermediate_centers()` (midpoints of sorted neighbouring targets),
   `narrow_filter_bank(fs, centers, half_width=1, order=2, max_hz, exclude_hz=[notch])`
   skipping bands above `min(max_hz, nyq−1)` or containing the notch (recorded in
   `bands_skipped`), `band_overlaps` (recorded in meta).
2. `build_windows.py` builds `harmonic` and `intermediate` banks when enabled.
3. `benchmark_n_subjects.py --bank {base, harm, harm+mid}` (extra narrow bands
   appended to the FBCSP bands) and `--classes {5,6}`: 6 classes = stimuli + 201,
   uniform LDA priors, extra metrics (balanced accuracy, false activation, missed
   stimulus, stimulus-correct), summed 2.0 s confusion matrices saved to
   `<csv>_confusion.csv`; 6 classes require built folders (true trial ids).

## Run (verbatim)

Run: `--cv-repeats 10` for {base, harm, harm+mid} × {5, 6} classes.

## Outputs (verbatim, mas/phases.yaml)

`benchmark_n_subjects.py --bank --classes 6 --cv-repeats`, `reports/n_subjects_benchmark_*_6class*.csv`

## Acceptance (verbatim)

Acceptance: all combinations produce CSVs; the report compares banks and 5 vs 6
classes with SDs over repeats (no preserved reference — record).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-13 | mas/05_PITFALLS.md, decisions P02 (a), P16 C-5 | the rest class is 201 only; 202 never enters as rest; any 202 use goes through `cv_groups` |
| PF-02, PF-03 | mas/05_PITFALLS.md | 6 classes need true trial ids (built folders only); smoothing by (trial, offset) |
| PF-04, PF-14 | mas/05_PITFALLS.md | narrow bands from meta fs, filtered on the continuous recording |
| R-16 | mas/04_REFERENCE_RESULTS.md | no preserved numbers; record and have the reviewer check direction and plausibility |
| §3, §5.7, §6 | mas/02_REQUIREMENTS.md | `filter_bank:` config block; 6-class metrics definitions; `n_subjects_benchmark` 6-class columns and `_confusion.csv` |
| decisions P16 C-1, C-2 | | freeze skips the redundant Mean row for later tags; remove the GATE_THRESHOLDS fallback in `benchmark_n_subjects`, label per_window builds legacy, forbid or document `--fs` on built roots |
| decisions P11 | | multi-seed: `--cv-repeats 10` with seeds 42+r, SDs reported |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-signal | P17.1, P17.2, C-1, C-2 (per_window label) | `03_changes_data-signal.md` |
| ml-engineer | P17.3, C-2 (fallback, `--fs` on built roots) | `03_changes_ml-engineer.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P17.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
