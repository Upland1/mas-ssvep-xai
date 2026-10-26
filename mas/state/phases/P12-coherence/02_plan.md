# P12 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md (R4, era matrix), mas/04_REFERENCE_RESULTS.md R-11 and tolerances, mas/05_PITFALLS.md PF-04, PF-15, PF-16, decisions.md P07–P11 rows, src/preprocessing/signal/quality_check.py (function list)
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Build the condition-level coherence estimator, the matched baseline and the circle-plot
panels. Reproduce first the two historical bugs (PF-15, PF-16) in a kept diagnostic,
then show the fix on S03/S04 against R-11.

## Data source

Legacy 7-channel `data/processed/<S>/` (P02, OO), conditions 101–105 and 201, fs 250 as
the feature sampling rate (legacy PF-04, labelled). No preprocessing is run. Two-tier
gate as in P07 (`apply_artifact_quality_pipeline`; vpp 5–120 µV, std 1–35 µV, channel
dropped if it fails in > 50 % of windows; every threshold passed explicitly, R5 style).

## Settled points (inferred; recorded in decisions.md)

1. **Gate scope.** One gate decision per subject over the union of the stimulus
   (101–105) and baseline (201) windows (202 excluded), so stimulus and baseline
   matrices share the same channels. Per-condition clean and rejected counts are printed
   and saved in the meta.
2. **Summary statistic for R-11 (amended after pre-run audit Round 1, finding F1).**
   "Baseline coherence" = one number per subject: the mean off-diagonal upper-triangle
   coherence of the gated 201 windows in `BASELINE_BAND` (5, 35) Hz. "Before the fix" =
   per-window coherence (`compute_coherence_matrix`, nperseg = min(T, 128)) averaged
   over the 201 windows; "after" = `compute_condition_coherence` on the same windows
   (nperseg 256). The five per-band matched-baseline values (before/after) are reported
   descriptively (A3), and their mean is a labelled secondary diagnostic only. The
   difference per condition is the mean off-diagonal stimulus − matched-baseline value
   (REPORTED); the per-pair matrix is also saved. *Superseded reading:* R-11's range
   applied band by band (the original settled point 2).
3. **Tolerance.** R-11's ranges carry "≈". Accept within ±0.05 of each range edge
   (tolerance table, descriptive statistics row). The 24/20 Hz "consistently positive"
   claim is checked as a sign over S03 and S04 for both conditions. The 10.91/8.57 Hz
   claim is "inconsistent" (sign or size differs between subjects); it is recorded, not
   tested (P13 tests it).
4. **Band edges.** `band_for_condition(c) = (f_c − 1, f_c + 1)` on the fs-250 frequency
   axis; inclusive bin selection; band-average = mean of the coherence bins inside. The
   baseline band (5, 35) is used only as the PF-16 "before" side.
5. **Kept diagnostic.** `scripts/connectivity/diagnostics/demo_coherence_bias.py`
   (synthetic part (a) + real-data part (b) for `--subjects`), labelled DIAGNOSTIC;
   outputs `reports/connectivity/coherence_bias_demo*.csv`.
6. **Outputs.** Analysis CSVs go under `reports/connectivity/` (`coherence_<S>_matrices.npz`,
   `coherence_<S>_summary.csv` + `.meta.txt`). Figures go under
   `outputs/figures/connectivity/`. The console table lists per condition: band, n
   windows, mean raw, mean matched baseline, mean difference.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| connectivity-stats | NEW `src/features/connectivity/__init__.py`, `connectivity_extraction.py` | task 1 exactly; per-pair coherence via `scipy.signal.coherence(x, y, fs, nperseg)` on the concatenated condition signal; symmetric matrix with NaN (or 1) diagonal, documented; `compute_coherence_matrix` labelled DIAGNOSTIC (PF-15); a loader helper that applies the P07 gate per settled point 1 | P12.1 | [1], PF-15, PF-16 |
| connectivity-stats | NEW `scripts/connectivity/diagnostics/demo_coherence_bias.py` (+ `__init__`s) | task 2 (a) synthetic: independent white noise vs a shared-source coupled pair, 256-sample windows, nperseg 128 vs concatenated nperseg 256, ≥ 40 windows, fixed seed; (b) real data: broadband-baseline difference vs matched-baseline difference per condition | P12.2 | [1], R-11 |
| connectivity-stats | NEW `src/visualization/connectivity_plots.py` | task 3 with `mne_connectivity.viz.plot_connectivity_circle` (installed 0.9.0); `CONDITION_LABELS`; difference panel `RdBu_r`, vmin = −vmax shared across conditions; `plot_permutation_null_distributions` stub only if trivial (P13 completes it) | P12.3 | [1] |
| connectivity-stats | NEW `scripts/connectivity/analysis/analyze_connectivity.py` | `--subject`, `--method coherence` (only choice now), `--fs` (default 250, legacy label), `--reports-dir`, `--figures-dir`, `--no-figures`; raw panel + difference panel + console table + CSV/npz/meta | P12.4 | [1] |

## Legacy behaviour in this phase

fs 250 in the coherence frequency axis (PF-04); raw legacy windows, no continuous
filtering (R3, era B); per-script P07 gate (R5). Per-window averaged coherence only in the
diagnostic (R4).

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R4 / PF-15 | averaged per-window coherence used in reported matrices | the reported path calls only `compute_condition_coherence`; test: independent noise → concatenated ≤ 0.05, per-window averaged ≈ 0.3 (fails on the bug) |
| PF-16 | broadband baseline subtracted | test: planted narrowband coupling only at f_c in both stimulus and baseline gives difference ≈ 0 with the matched baseline but ≠ 0 with the broadband one |
| R6 | pair ↔ matrix index swapped; matrix not symmetric; channel order lost after a dropped channel | synthetic: couple only channels (1, 4) → only entry [1, 4] = [4, 1] high; with a dropped channel, names follow |
| Band | off-by-one bins; fs 256 used by mistake | test the selected frequencies for fs 250 and the 24 Hz band; the meta states fs |
| Concatenation | windows of different conditions mixed; 202 included | test the condition filter; the meta lists counts per condition |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| bias (a) | independent Gaussian noise, 7 ch, 40 × 256 samples | per-window averaged (nperseg 128) in [0.30, 0.37]; concatenated (nperseg 256) ≤ 0.03 | as stated | R-11, PF-15 |
| coupled | shared sinusoid + small noise | both ≥ 0.95 | | R-11 |
| matched baseline (b) | stimulus and baseline with identical narrowband coupling at f_c | matched difference ≈ 0 (|d| ≤ 0.05); broadband difference clearly ≠ 0 | | PF-16 |
| pair layout | coupling only on (1, 4) | argmax off-diagonal = (1, 4); symmetric | exact | R6 |
| band | fs 250, f_c 24 | bins within [23, 25]; band-average equals a hand mean | exact | task 1 |
| same 201 windows | baseline re-scored per band | the same window indices in every band | exact | PF-16 |
| plots | small synthetic matrices | figures written; difference colour limits symmetric | exact | task 3 |

Historical bugs: PF-15 (averaged per-window) and PF-16 (broadband baseline); the bias and
matched-baseline tests fail on them.

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.connectivity.diagnostics.demo_coherence_bias --subjects S03 S04
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity --subject S03 --method coherence
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity --subject S04 --method coherence
```

The builder confirms the flags. Runtime: seconds to about 2 min each (Welch on about 40 ×
256 samples × 21 pairs × 6 conditions). Total under 10 min, inside the 120-min budget. The
verifier saves the pytest log under `reports/logs/P12/`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| synthetic tests of task 2 | the bias and matched-baseline tests pass; demo (a) numbers printed in range | R-11 |
| S03/S04 baseline coherence drops after the fix (R-11: from ≈0.68–0.73 to ≈0.59–0.66) | the windows A0–A3 pre-committed in 07_review.md (pre-run audit Round 1). A2: per subject, the broadband (5–35 Hz) 201 baseline before in [0.63, 0.78] and after in [0.54, 0.71], with after < before. A3: after < before in all 10 per-band cells (values descriptive). A0: clean stimulus windows S03 197, S04 197 | R-11 |
| differences show 24 Hz and 20 Hz consistently positive in S03/S04 (≈+0.11 to +0.25) | A4: the 101/102 differences each > 0 and inside [0.06, 0.30]. A6: the window-aligned diagnostic difference within 0.05 of the prescribed one per band; otherwise the band is flagged estimator-sensitive, and a differing aligned 101/102 sign makes A4 "not robust" | R-11 |
| 10.91/8.57 Hz inconsistent (alpha-band ceiling hypothesis recorded, to be tested statistically in P13) | A5: 104/105 are descriptive (R-11: S03 ≤ +0.05, S04 > 0); the reviewer records the hypothesis next to the A6 junction-bias diagnostic | R-11 |
| synthetic tests of task 2 (numbers) | A1: per-window averaged in [0.27, 0.40], concatenated ≤ 0.07, coupled ≥ 0.93 | R-11 |

## Sources

1. `mas/03_ROADMAP.md` P12 (opened in this run).
2. `mas/04_REFERENCE_RESULTS.md` R-11 and the tolerance table; `mas/05_PITFALLS.md` PF-15, PF-16 (opened in this run).

## Questions
