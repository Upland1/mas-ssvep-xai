# P17 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (pre-run section), the phase branch
Clean checkout: `mas/state/scratch/verify/P17` @ 59b0f10261f3dea48934d23fff05d306979144a8 (suite only; removed). Runs from the repository root at the same HEAD with an empty porcelain status.

Verdict: PASS

Numbers below come from the CSVs in `reports/` (`n_subjects_benchmark_p17_*`) and the logs in `reports/logs/P17/`; arithmetic from `mas/state/scratch/` scripts of this run (deleted). Nothing is interpreted beyond the pre-committed criteria; the reviewer applies the comparison rules.

## Tests on the clean checkout

`.venv/bin/python -m pytest tests/ -q -o addopts=""` -> `1166 passed, 1 skipped, 22 warnings in 674.59s`, exit 0 (`pytest_full_20261028T081533Z.log`). `tests/test_p17_leak_controls.py` (12 tests) is part of that run and passed. G1 met.

## Acceptance

| Criterion | Obtained | Met? |
|---|---|---|
| All combinations produce CSVs (six + three `_confusion.csv`, 10 repeats) | six CSVs + `.meta.txt`, three confusion files, D0 CSV exist; `CV repeats` = 10 on every row | yes |
| Report compares banks and 5 vs 6 classes with SDs | per-subject values and SDs below; comparison done by the reviewer | yes (data provided) |
| No preserved reference (R-16) | recorded | n/a |
| Data source: P16 files byte-identical or guard rule | guard rule applied (231 -> 268 samples); D2 non-guard files identical; P16 root hash unchanged | yes |

## Verifier checks (07_review.md list)

1. Files: six CSVs + six `.meta.txt`, three `_6class_confusion.csv`, D0 CSV; no other new file under `reports/` except logs (`ls reports | grep p17` lists exactly these 16 files). Met.
2. Schema: 5-class columns = 12 (Subject ... CV repeats); 6-class = 12 + 8 + 7 SD = 27 columns, order as §6 (printed from the CSV header). One `Mean` row per file, 6 rows. `Bank`: base `fbcca`, harm `fbcca+harm`, harmmid `fbcca+harm+mid` on all subjects. `len(CSP Bands.split())` = 5 / 19 / 23 on every subject. Met.
3. One mask: `Clean Windows` equal across the three banks (5 class: S01 200, S02 190, S03 194, S04 195, S05 199; 6 class: 280, 264, 271, 270, 279). `Clean Windows(6) - Rest Windows = Clean Windows(5)` True for all subjects and all three banks. Met.
4. Confusion files: classes 101..105 and 201 only; `CV repeats` = 10; per subject entries sum to 10 x `Clean Windows` and the 201 row to 10 x `Rest Windows` (True, 15 of 15 subject-bank blocks); `Sum` = sum of the five blocks (True, 3 of 3). 2.0 s FalseAct, Missed, StimCorrect, BalAcc and the 6-class `2.0s Smoothed (%)` re-derived from the summed matrix: maximum absolute difference to the CSV 0.0050 (tolerance 0.005; the printed values are round-off at the 2-decimal CSV precision). Met.
5. P16 root hash: pre `c59c94b8ac90a77f57148f057698411f97690ec1174b1202237b37624144a54e`, post identical, pinned value identical (65 files). Met.
6. D0, D1, D2 quoted verbatim in `05_run.md`.

## D0 (base, 5 class, 5 repeats, `_p17` root vs `reports/n_subjects_benchmark_v2cont.csv`)

All five subjects have `stim mask equal True` (D2). For `Clean Windows`, `1.0s Acc (%)`, `2.0s Smoothed (%)`, `1.0s SD`, `2.0s SD` all 25 values are exactly equal (S01 72.80/77.90, S02 72.42/75.26, S03 93.61/93.92, S04 99.49/99.49, S05 98.59/98.79). No regression. Met.

## G2

D0 identity met; D1 minimum cross-trial gap 2.969 s on every subject (>= 2.0 s); D2 non-guard files byte-identical (no `DIFF` line), `p17-only` 0, stimulus masks equal on all subjects. Met.

## Results per subject (10 repeats, seeds 42..51; mean over repeats, SD in parentheses)

5-class, CSV `reports/n_subjects_benchmark_p17_{base,harm,harmmid}_5class.csv`:

| Subject | base 1.0 s | base 2.0 s | harm 1.0 s | harm 2.0 s | harmmid 1.0 s | harmmid 2.0 s |
|---|---|---|---|---|---|---|
| S01 | 73.15 (1.93) | 78.85 (2.04) | 85.50 (1.97) | 91.45 (1.85) | 85.55 (2.15) | 90.05 (1.74) |
| S02 | 73.05 (2.49) | 76.63 (3.05) | 86.74 (1.57) | 88.16 (0.90) | 86.32 (2.11) | 87.84 (1.20) |
| S03 | 93.76 (1.20) | 93.92 (1.13) | 99.38 (0.22) | 99.48 (0.00) | 99.33 (0.25) | 99.43 (0.16) |
| S04 | 99.38 (0.40) | 99.38 (0.40) | 100.00 (0.00) | 100.00 (0.00) | 100.00 (0.00) | 100.00 (0.00) |
| S05 | 98.89 (0.62) | 99.05 (0.60) | 99.85 (0.34) | 99.90 (0.32) | 99.95 (0.16) | 99.95 (0.16) |
| Mean | 87.65 | 89.57 | 94.29 | 95.80 | 94.23 | 95.45 |

6-class (2.0 s unless stated), CSV `..._p17_{base,harm,harmmid}_6class.csv`:

| Bank | Subject | Acc 1.0 s | Acc 2.0 s | BalAcc 2.0 s | FalseAct 2.0 s | Missed 2.0 s | StimCorrect 2.0 s |
|---|---|---|---|---|---|---|---|
| base | S01 | 69.61 | 74.00 | 73.33 | 22.00 | 14.25 | 72.40 |
| base | S02 | 71.10 | 74.28 | 72.91 | 16.08 | 18.26 | 70.53 |
| base | S03 | 92.73 | 93.51 | 92.64 | 1.17 | 5.36 | 91.39 |
| base | S04 | 98.22 | 98.19 | 97.86 | 0.00 | 2.51 | 97.49 |
| base | S05 | 96.56 | 97.38 | 96.95 | 0.00 | 2.96 | 96.33 |
| harm | S01 | 76.11 | 81.00 | 79.02 | 7.12 | 20.00 | 76.25 |
| harm | S02 | 79.85 | 82.31 | 79.92 | 3.24 | 20.00 | 76.68 |
| harm | S03 | 94.39 | 95.24 | 94.50 | 0.13 | 6.55 | 93.40 |
| harm | S04 | 99.00 | 99.00 | 98.81 | 0.00 | 1.38 | 98.62 |
| harm | S05 | 96.92 | 97.85 | 97.50 | 0.00 | 2.81 | 96.98 |
| harmmid | S01 | 76.54 | 81.14 | 79.46 | 8.75 | 19.20 | 77.10 |
| harmmid | S02 | 79.55 | 82.65 | 80.02 | 1.49 | 19.63 | 76.47 |
| harmmid | S03 | 94.35 | 95.42 | 94.69 | 0.00 | 6.34 | 93.61 |
| harmmid | S04 | 98.81 | 98.81 | 98.60 | 0.00 | 1.64 | 98.36 |
| harmmid | S05 | 96.92 | 97.89 | 97.54 | 0.00 | 2.86 | 97.04 |

The 6-class CSVs also hold the SD columns (`2.0s BalAcc SD`, `2.0s FalseAct SD`, `2.0s Missed SD`, `2.0s StimCorrect SD`, accuracy SDs), 1.0 s BalAcc/FalseAct/Missed and `Rest Windows` (S01 80, S02 74, S03 77, S04 75, S05 80); not repeated here.

Valid counts `_p17` vs P16 (D2): only S04 changes (valid 309 -> 307, rest 76 -> 75 and 2 windows of other classes, none stimulus); all other subjects equal.

## G3 (base 5-class 1.0 s below 90 %: S01 73.15, S02 73.05)

| Subject | base 1.0 s | harm 1.0 s | harm - base (pp) | harm < 97 % and gain < 20 pp? |
|---|---|---|---|---|
| S01 | 73.15 | 85.50 | +12.35 | yes |
| S02 | 73.05 | 86.74 | +13.69 | yes |

S03, S04, S05 have base >= 90 % (93.76, 99.38, 98.89) and are outside the rule. G3 met (no trigger).

## G4 (harm: StimCorrect(6) + Missed(6) >= Smoothed(5) - 3 pp)

| Subject | StimCorrect(6) + Missed(6) | Smoothed(5) - 3 | Met |
|---|---|---|---|
| S01 | 76.25 + 20.00 = 96.25 | 88.45 | yes |
| S02 | 76.68 + 20.00 = 96.68 | 85.16 | yes |
| S03 | 93.40 + 6.55 = 99.95 | 96.48 | yes |
| S04 | 98.62 + 1.38 = 100.00 | 97.00 | yes |
| S05 | 96.98 + 2.81 = 99.79 | 96.90 | yes |

G4 met (no trigger).

## Numbers in the handoffs vs logs

The ml-engineer's S03 smoke (`03_changes_ml-engineer.md`) agrees with this run: base 5-class 93.76 / 93.92, harm 99.38 / 99.48, harm+mid 99.33 / 99.43; harm 6-class 94.39 / 95.24, FalseAct 0.13, Missed 6.55, StimCorrect 93.40; clean windows S03 194 and 271 (77 rest). The data-signal guard 1.047 s and the 60 Hz skip match the build log (`bands skipped ... 60 Hz [59, 61]`, `guard 1.047 s`, 15 files per subject). Every number in `05_run.md` is from the logs listed there.

## Sources spot-check

Opened `mas/state/phases/P17-rest-class-filterbank/07_review.md` (G1-G4, comparison rules, verifier checks) and `02_plan.md` (run commands, items 1-4); both say what the handoffs cite for the guard rule (decided before any number) and the run list. `.meta.txt` of the 6-class base run states `classes 6: 101-105 + rest 201 (202 excluded, PF-13); uniform LDA priors 1/6; CV groups = true trial ids (R1)`, consistent with the plan's settled point 3.

## Reference consultations check

Both handoffs and `04_tests.md` list none. `mas/state/scratch/reference_access.log` has 0 lines dated 2026-10-28. Met.

## Reasons (if FAIL)

None.
