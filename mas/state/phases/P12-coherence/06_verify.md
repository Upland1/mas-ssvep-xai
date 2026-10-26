# P12 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (A0-A6), the phase branch
Clean checkout: `mas/state/scratch/verify_P12` @ cb446b0b7a9ad50f7d4482eeb67619043dc5df0f (tests); run commands from the repository root at the same HEAD with an empty porcelain status

Verdict line at the end of this file.

## Tests on the clean checkout

`.venv/bin/python -m pytest tests -o addopts="" -q` -> `723 passed, 21 warnings in 362.42s (0:06:02)`, EXIT 0 (`reports/logs/P12/pytest_20261026_151109.log`). Count 723 matches the tester's count (07_review N4).

## Acceptance (windows A0-A6 as pre-committed in 07_review.md Round 1)

Sources: console logs `reports/logs/P12/{demo_20261026_151720,analyze_S03_20261026_151734,analyze_S04_20261026_151743}.log`; CSVs `reports/connectivity/coherence_{S03,S04}_summary.csv`. Arithmetic was done with `.venv/bin/python -I` on those CSVs (differences below are `mean_difference - mean_difference_aligned`).

| # | Quantity | Obtained | Window | Met? |
|---|---|---|---|---|
| A0 | clean stimulus windows (gate, nothing dropped) | S03: 39+39+40+40+39 = 197 (rejected 1/1/0/0/1); S04: 37+40+40+40+40 = 197 (rejected 1/0/0/0/0). 201 clean: S03 78/78, S04 77/79 (2 rejected). Channels kept: all 7 for both, dropped none | S03 197, S04 197, exact | yes (exact). Reason tally was not needed: counts equal |
| A1 | demo (a), seed 0, 40x256 | independent: per-window averaged 0.3373, concatenated 0.0180; coupled: 0.9814 / 0.9824 (`demo_20261026_151720.log`; "synthetic part in range: True") | per-window in [0.27, 0.40]; concatenated <= 0.07; coupled both >= 0.93 | yes |
| A2 | 201, 5-35 Hz, before (per-window, PF-15) / after (concatenated) | S03: 0.6836 / 0.5871; S04: 0.7291 / 0.6589 (`baseline_broadband_before/after` in the summary CSVs) | before in [0.63, 0.78], after in [0.54, 0.71], after < before | yes, all four values in window and both drops present |
| A3 | per-band matched baseline, before (`mean_baseline_perwindow`) -> after (`mean_matched_baseline`), bands 101..105 | S03: 0.6433->0.5461, 0.6720->0.5500, 0.6625->0.5256, 0.7152->0.6435, 0.8000->0.7390. S04: 0.7371->0.7041, 0.7090->0.6724, 0.7031->0.5986, 0.7106->0.5831, 0.7025->0.6422 | after < before in 10 of 10 | yes (10/10). Secondary diagnostic, 5-band mean before/after: S03 0.6986 / 0.6009, S04 0.7125 / 0.6401 (not used for A2) |
| A4 | prescribed difference, 101 and 102 | S03: +0.2494, +0.2511; S04: +0.1281, +0.1105 | each > 0 and in [0.06, 0.30] | yes, 4/4. Aligned signs also positive in all four (see A6), so not "not robust" |
| A5 | prescribed difference, 104 / 105 (descriptive) | S03: -0.0366 / +0.0414 (R-11 expects <= +0.05); S04: +0.1934 / +0.1286 (R-11 expects > 0) | descriptive | consistent with R-11 in all four values. Alpha-ceiling hypothesis is left to the results review and P13 |
| A6 | junction diagnostic, delta = prescribed - aligned | see table below | abs(delta) <= 0.05 negligible | S03 band 105 flagged (0.0565); no other band flagged |

A6 per band (`mean_difference` / `mean_difference_aligned` / delta, from `coherence_{S03,S04}_summary.csv`):

| Subject | 101 | 102 | 103 | 104 | 105 |
|---|---|---|---|---|---|
| S03 prescribed | 0.2494 | 0.2511 | 0.1626 | -0.0366 | 0.0414 |
| S03 aligned | 0.2258 | 0.2648 | 0.1892 | -0.0233 | -0.0151 |
| S03 delta | +0.0236 | -0.0137 | -0.0265 | -0.0133 | +0.0565 (FLAG) |
| S04 prescribed | 0.1281 | 0.1105 | 0.0554 | 0.1934 | 0.1286 |
| S04 aligned | 0.1203 | 0.0992 | 0.0852 | 0.2081 | 0.1063 |
| S04 delta | +0.0078 | +0.0113 | -0.0298 | -0.0147 | +0.0222 |

Flags (A6 rule): S03 band 105 is flagged as estimator-sensitive (abs delta 0.0565 > 0.05). Per the reviewer's reading rule it is not called junction-biased: the sign of delta (prescribed above aligned) is opposite to the predicted junction direction (negative), and the aligned estimator uses about half as many segments. The aligned sign differs from the prescribed one at S03 105 (+0.0414 vs -0.0151); that band is not a 101/102 band, so A4 robustness is unaffected. No interpretation is given here; the results review does that. The reported estimator is unchanged.

Other observations strictly against the criteria text: the assignment's "(≈+0.11 to +0.25)" is covered by A4's wider window; S04 103 (+0.0554) and S03 103 (+0.1626) are not part of A2-A6.

Overall: A0 yes, A1 yes, A2 yes, A3 yes, A4 yes, A5 consistent, A6 one band flagged (S03 105), nothing else outstanding.

## Legacy array integrity (sha256 before and after the three commands)

`mas/state/scratch/p12_sha_before.txt` vs `mas/state/scratch/p12_sha_after.txt` (`diff` reported identical):

| File | sha256 (before = after) |
|---|---|
| data/processed/S03/X_time_windows.npy | 88e9a294b668e5b5631430ccce2fae1df03b32dc7075e24726eff96a9fe7541e |
| data/processed/S03/y_labels.npy | 112c8507c38f2193a5bd7dbf8fc72d5d46f1662e6b0ecbb6f17442a6525d5c4c |
| data/processed/S04/X_time_windows.npy | d9dbca887edfdd827edec5aa093fb7503fe0958561cff6946d6a27d96dea85c1 |
| data/processed/S04/y_labels.npy | cebc9c5858b6f90f4a53be13f46967929f0419442cf7b1cf70ee5509af5f44ac |

These equal the hashes recorded by the reviewer before the run (07_review.md Round 1).

## Numbers in the handoffs vs logs

05_run.md numbers (exit codes, test count, runtimes) come from the log headers and tails. The builder's S03 smoke values in 03_changes (0.6836 / 0.5871 / 0.6005 and the five prescribed/aligned pairs) equal the verified run (`analyze_S03_20261026_151734.log`), so the smoke was reproduced. The 03/04 suite counts 717 and 723 are consistent with the verified 723.

## Sources spot-check

Opened in this run: `mas/04_REFERENCE_RESULTS.md` R-11 (ranges quoted above match the file: synthetic 0.32-0.35 / 0.01-0.02 / 0.98-0.99, baseline 0.68-0.73 -> 0.59-0.66, 24/20 Hz +0.11 to +0.25) and `mas/state/phases/P12-coherence/07_review.md` (windows A0-A6 quoted verbatim). Both say what is claimed.

## Reference consultations check

03_changes and 04_tests list none. Not re-opened here.

## Notes for the results review (not verdicts)

- Figures exist at `outputs/figures/connectivity/` (not inspected by the verifier).
- No run-time anomalies.

Verdict: PASS
