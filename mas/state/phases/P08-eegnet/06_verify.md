# P08 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify_P08` @ cf62bb3005a21c8cc6dafe542c7b42df7075c067 (removed after the run)

Verdict: PASS

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```
Summary line verbatim: `528 passed, 21 warnings in 190.59s (0:03:10)`

The phase commands ran from the repo root at the same HEAD with a clean tree (`status: []` in every log header), as instructed, so the default data root was used.

## Acceptance

Every number is labelled: legacy leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02), legacy 7-channel S03 arrays (P02, OO session), device as shown. Logs: `reports/logs/P08/` (see 05_run.md).

| Criterion (pre-committed in 07_review.md) | Obtained | Met? |
|---|---|---|
| Both commands exit 0 | cpu run1/run2 0/0, cuda run1/run2 0/0 | yes |
| Device labelled in CSV, log, `.meta.txt` | CSV `Device` = cpu / cuda; log header `device cpu` / `device cuda` and `[+] S03 [cpu\|cuda]`; `.meta.txt` line 1 `device=cpu\|cuda` (cuda copy printed: `device=cuda (CPU and CUDA numbers differ; each is deterministic)`) | yes |
| Counts S03: 197 clean / 3 rejected, 7 channels kept, none dropped | both devices: `200 stimulus, 197 clean, 3 rejected; channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped [none]` (= R-3/R-5/R-6) | yes |
| Params 2,349 | 2349 on both devices (CSV `Params`) | yes |
| Accuracies are k/197 | table below, all integer-consistent | yes |
| CPU vs CUDA gap | 9 windows on each of 1.0 s and 2.0 s | between the 5-window noise band and the 10-window CONCERN threshold; reason 6 |
| Train vs test (PF-30) | train 98.34 % (cpu), 98.60 % (cuda), above the ~95 % expectation; test far lower | yes (generalization gap, not fixed in P08) |

Per-device numbers (run1 = run2):

| Device | 1.0 s acc | k/197 | 2.0 s smoothed | k/197 | Train acc (mean over folds) | Params |
|---|---|---|---|---|---|---|
| cpu | 75.63 % | 149 | 85.79 % | 169 | 98.34 % | 2349 |
| cuda | 71.07 % | 140 | 81.22 % | 160 | 98.60 % (CSV 98.6) | 2349 |

k found with a shown Python one-liner, `round(100*k/197, 2) == value` (unique k for each value).

Run1 vs run2 (determinism): the run1 and run2 CSV copies are byte-identical (`cmp`) for cpu and for cuda; per-fold lines and the `[+]` line are identical in the logs of each device (only wall-time fields differ: 32 s vs 31 s cpu, and the `RUNTIME_S` line). Both devices are run-to-run identical on S03.

CPU minus CUDA: 1.0 s 149 - 140 = 9 windows (75.63 - 71.07 = 4.56 pp from the CSV values); 2.0 s 169 - 160 = 9 windows (85.79 - 81.22 = 4.57 pp). Reported separately; neither is "the" P08 result and they are not averaged.

Diagnostic comparisons (labelled, as pre-committed; not targets):
- Leaky classical flagship (R-3/R-5, same gate, folds, leak): 90.36 / 95.43 % = 178 / 188 of 197. EEGNet is lower on both devices (149 / 140 vs 178 at 1.0 s; 169 / 160 vs 188 at 2.0 s). Not a model comparison (PF-01).
- Later leak-free numbers (R-7 79.19 % = 156/197; R-9b OFF 73.60 / 82.23 % = 145 / 162 of 197): not P08 targets. At 1.0 s cpu 149 is above 145 and cuda 140 is below it; the review states that a number below 145/197 "is not a failure but is noted as unexpected under PF-01". Noted here for cuda.
- R-6 not compared.

## Numbers in the handoffs vs logs

Every number in 05_run.md is copied from the four logs and the CSVs listed there. The numbers in 07_review.md (197/3, 7 channels, 2,349 parameters) match the logs. The builder extrapolation of about 30 s per device matches the measured 32 s (cpu) and 20 s (cuda).

## Privacy, git, R11

1. No raw-recording path or recording file was read, listed or passed to a command; no preprocessing was run; the default data root was used.
2. Tracked files: no `data/` or `reports/` path; the `git ls-files` matches for `ebr` are only the P01 parser source, its test and P01 handoff markdown. `git status --porcelain` empty at HEAD before and after the runs (outputs are git-ignored).
3. R11: `03_changes_deep-learning.md` and `04_tests.md` list no reference consultation; `mas/state/scratch/reference_access.log` has 26 lines and its last entry is 2026-10-25T04:48:46 (ml-engineer, earlier phase), before the first P08 commit. No P08 access.

## Sources spot-check

Opened: `mas/state/phases/P08-eegnet/07_review.md` (R-3 counts 197/3, 90.36/95.43 flagship, R-7, R-9b, R-8 2,349 parameters as quoted) and the four logs. The review's numbers agree with the logs. The paper named in 03 is not claimed as consulted (review note 2) and was not opened here.

## Reasons for the verdict

1. Clean checkout of HEAD cf62bb3: 528 passed, 0 failed.
2. Both commands trained and exited 0 on cpu and cuda, device labelled in CSV, log and `.meta.txt`.
3. Counts and channels equal the flagship's (197/3, 7 kept, none dropped); params 2,349 exact.
4. All accuracies are k/197; train accuracy about 98 % on both devices.
5. Run1 equals run2 on each device (the determinism label in `.meta.txt` is supported).
6. CPU vs CUDA gap is 9 windows on both metrics: above the 5-window noise band and not above the 10-window CONCERN threshold. Because each device is deterministic (reason 5), the gap is a device difference and not nondeterminism; it is not a model effect. Recorded for the reviewer.
7. Privacy, git and R11 checks clean.

No acceptance criterion failed.
