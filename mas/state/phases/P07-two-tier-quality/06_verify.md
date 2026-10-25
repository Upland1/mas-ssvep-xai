# P07 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (pre-committed checks), the phase branch
Clean checkout: `mas/state/scratch/verify_P07` @ fa5dadeec71561725efd72c493ee22c5edf1946f (removed after the run)

Verdict: PASS

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests -o addopts="" -q -p no:cacheprovider
```
Summary line verbatim: `503 passed, 20 warnings in 191.73s (0:03:11)` (< 5 min). Named tests for both tiers: `tests/test_p07_quality_signal.py` (tier 1 boundary 50/51 of 100, tier 2 on kept channels only, PF-07 pinned default and rejection with `--vpp-min 5.0`, PF-09 stale removal), `tests/test_p07_known_answer.py` (PF-08 arity scan, PF-10 single decision spy), `tests/test_p07_ml_engineer.py` (PSD columns on kept channels, P04 positions), `tests/test_p07_round1_known_answer.py` (legacy switch, legacy-array protection, Makefile, P04 per-subject channel check).

## Acceptance

| Criterion | Re-run | Obtained | Reference | Met? | Log |
|---|---|---|---|---|---|
| D0 legacy arrays untouched | sha256 of 18 files before/after | identical, equal to 07_review.md D0 | D0 | yes | 05_run.md; `mas/state/scratch/d0_before.txt` |
| P1 S03 still produces windows (pinned) | run 3 | 317 windows, every condition > 0: 101-105 40 each, 201 78, 202 39. Kept = legacy seven (PO7 dropped, 100.0% fail, mean Vpp 797.56 uV). `np.array_equal(y, data/processed/S03/y_labels.npy)` -> `True` (317 each); X_time shapes `(317, 7, 256)` both, `np.abs(x-y).max()` -> `0.0` (within 1e-9) | P1 | yes | run_preprocessing_pinned_20261025_133207.log |
| P2 PF-07 demo | runs 1 and 2 | `--no-channel-drop`: `accepted 0, rejected 320` (S03 skipped, "no window accepted"); 320 equals the ungated `n_windows` of runs 1/3 (`317/320 windows valid`). Tier-1-on: `accepted 317, rejected 3` (tier 1 dropping PO7 removes the regression). Pinned 0.5, same channels: 317/3 | PF-07 "all 320 rejected" | yes: "reproduced" per the pre-committed rule. Not the FAIL case (5.0 without drop rejects 320 vs 3 under 0.5) | nodrop and vppmin5 logs |
| P3 channel report per subject | runs 1, 3, 4 | printed in runs 1 and 3 (PO7 DROPPED) and for each of S01-S05 in run 4 (`fail ...%`, `channels kept`) | P3 | yes | logs |
| D1 CSV complete | `reports/n_subjects_benchmark.csv` | S01-S05 + Mean rows; Channels Kept 7 and Dropped `none` for all five; Mean row has accuracy columns only | R-6: 7 / none | yes | benchmark log |
| D2 counts vs R-6 | CSV | Clean/Rejected 200/0, 196/3, 197/3, 197/1, 200/0 | R-6 200/0, 196/3, 197/3, 197/1, 200/0 | exact, yes | CSV |
| D3 accuracies (diagnostic vs R-5 only) | CSV | 1.0 s / 2.0 s: S01 64.50/75.50, S02 66.33/71.94, S03 90.36/95.43, S04 98.98/98.48, S05 96.50/96.50, mean 83.33/87.57 | R-5 identical per subject | diagnostic: equal to R-5 to two decimals; nothing to explain | CSV |

Notes: the PF-07 mechanism seen here is `vpp_high` driven by PO7 (mean Vpp 797.56 uV), not `vpp_low`; the pre-committed rule judges the outcome (all 320 rejected, S03 skipped), which is reproduced. The pre-run expectation (a total rejection can only come from PO7 chronically out of range) is borne out by the per-channel report. The benchmark uses the legacy leaky CV (R1 LEGACY); no comparison with R-6 accuracies.

## Numbers in the handoffs vs logs

All numbers in 05_run.md are copied from the four logs; counts and table match the CSV. The 503-passed count matches 04_tests.md Round 1.

## Sources spot-check

Opened: `mas/state/phases/P07-two-tier-quality/07_review.md` (pre-committed checks, D0 list) and `mas/RULES.md` R-6 table / counts (200/0, 196/3, 197/3, 197/1, 200/0); both say what the handoffs claim.

## Reference consultations check

The 03_changes files list "None". `mas/state/scratch/reference_access.log` has 26 lines, last at 2026-10-25T04:48:46 (P06), no entry during P07. I opened no reference code.

## Privacy and git

Main tree clean after the runs (outputs are under git-ignored `reports/` and `data/`). I read no raw recordings; only project scripts did. `--processed-dir` never pointed at `data/processed`. No vendor/tool names in `main..HEAD` commit messages (0 hits).

## Reasons (if FAIL)

None.
