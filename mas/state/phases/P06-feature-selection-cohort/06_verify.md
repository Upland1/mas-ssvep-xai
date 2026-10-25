# P06 · 06 · Verification

Status: READY
Author: verifier
Reads: 05_run.md, logs, CSVs, 07_review.md pre-committed checks, mas/04_REFERENCE_RESULTS.md R-4/R-5

Verdict: FAIL

Commit verified: 7575405d2bffccc326a715b16644085cfb30898f. Nothing was changed or fixed.

## Numbered reasons

1. **R-4 missed on one row (Sequential forward selection, p=20).** Obtained 89.85 % (1.0 s) / 95.94 % (2.0 s) = 177 / 189 windows of 197; accepted ranges 165-169 / 182-186; target 84.77 / 93.40. Delta +5.08 pp / +2.54 pp (both outside the +-1.5 pp tolerance). Counts first: Clean 197 / Rejected 3 on all five rows, as required. The pre-committed miss procedure in `07_review.md` (investigation round with labelled diagnostics, then R11) now applies; the verifier did not run it.
2. The other four R-4 rows are within tolerance and exact to the target (Delta 0.00 pp), p exact on all five rows (55, 45, 25, 25, 20).
3. The Full row equals `reports/flagship_S03.csv` (m=1) exactly (90.36 / 95.43).
4. R-5 passes: counts exact, all ten values equal P05's (Delta 0.00), mean 83.33 / 87.57 equals the mean of the rounded rows (83.334 / 87.57).
5. Qualitative R-4 reading: SFS obtained 2.0 s (95.94) is above the Full row (95.43); the 1.0 s value (89.85) is below Full (90.36). The reviewer's rule (a subset beating Full is checked as a possible leak) is relevant to this row and is left to the investigation round.
6. Report v1 (P06.4): pending, written by the scribe after this run; not a failure.

## R-4 (S03), commands: pre-committed ranges `math.ceil((p-1.5)*1.97)`, `math.floor((p+1.5)*1.97)`; counts `round(acc*1.97)` from `reports/feature_selection_ablation_S03.csv`

| Method | p (exp/obs) | 1.0 s obs (count) | range | 2.0 s obs (count) | range | Clean/Rej | Result |
|---|---|---|---|---|---|---|---|
| Full baseline | 55/55 | 90.36 (178) | 178 only; 176-180 by tolerance | 95.43 (188) | 188 | 197/3 | OK |
| Sub-band pruning | 45/45 | 87.31 (172) | 170-174 | 94.92 (187) | 185-189 | 197/3 | OK |
| ANOVA F-score | 25/25 | 86.29 (170) | 168-172 | 94.42 (186) | 184-188 | 197/3 | OK |
| Mutual information | 25/25 | 87.82 (173) | 171-175 | 93.40 (184) | 182-186 | 197/3 | OK |
| Sequential forward selection | 20/20 | 89.85 (177) | 165-169 | 95.94 (189) | 182-186 | 197/3 | **MISS** (+5.08 / +2.54 pp) |

Full == flagship_S03.csv (m=1): 1.0 s equal True, 2.0 s equal True.

## R-5 (`reports/five_subjects_benchmark.csv` vs P05 / mas/04 R-5)

| Subject | Clean/Rej obs (exp) | 1.0 s obs (exp) | 2.0 s obs (exp) | Delta | Result |
|---|---|---|---|---|---|
| S01 | 200/0 (200/0) | 64.50 (64.50) | 75.50 (75.50) | 0.00 / 0.00 | OK |
| S02 | 196/3 (196/3) | 66.33 (66.33) | 71.94 (71.94) | 0.00 / 0.00 | OK |
| S03 | 197/3 (197/3) | 90.36 (90.36) | 95.43 (95.43) | 0.00 / 0.00 | OK |
| S04 | 197/1 (197/1) | 98.98 (98.98) | 98.48 (98.48) | 0.00 / 0.00 | OK |
| S05 | 200/0 (200/0) | 96.50 (96.50) | 96.50 (96.50) | 0.00 / 0.00 | OK |
| Mean | | 83.33 (83.33) | 87.57 (87.57) | 0.00 / 0.00 | OK (mean of rounded rows 83.334 / 87.57) |

Console states the CV is leaky. Python command and output are reproduced from the verifier session (pandas over the two CSVs).

## Other checks

- Tests: `455 passed, 10 warnings in 264.82s (0:04:24)` in the clean worktree.
- Logs: headers show command, HEAD 7575405, start time; exit codes 0 and 0.
- Privacy/git: tree clean before and after the runs (`git status --porcelain` empty); 0 tracked paths under `data/`; 0 tracked local-instruction/tooling paths. Vendor-name scan of the diff is the reviewer's pre-run result (0 hits); not repeated. One guard block occurred (a grep pattern naming raw-data/recording paths); the command was rewritten without that pattern, no path was split or obfuscated.
- R11: `mas/state/scratch/reference_access.log` still has 14 lines, last entry 2026-10-24T23:49:50 (P05); no new access in P06.
- Sources: R-4/R-5 targets opened in `mas/04_REFERENCE_RESULTS.md` and matched to the pre-committed table in `07_review.md`.
