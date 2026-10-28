# P19 · 06 · Verify

Status: READY
Author: verifier
Reads: 05_run.md (logs in `reports/logs/P19/`), 02_plan.md, 00_assignment.md, 03_changes_data-signal.md, 04_tests.md, 07_review.md (pre-run audit), decisions.md P19 rows
Commit verified: 2994599191e6f6b2df1e3270c68c6fab6977bcab

Verdict: PASS

## Numbered reasons

1. Suite: `pytest tests/ -q -o addopts=""` in the clean worktree: 1231 passed, 22 warnings, 0 failed, 0 skipped, 738.35 s (`reports/logs/P19/01_pytest.log`).
2. Commands 1-7 exit 0; total 19.8 min against `LOCAL_RUN_BUDGET_MIN` 120; no human-run request. No subject skipped under any source.
3. Acceptance check 2 (regression): check B shows, for S01-S05, `same_file_list True`, `npy_differ []`, `meta_top_differ []`, `quality_differ []`, `rejections_ok True`, `build_params_ok True`, `params_ok True`, new quality fields None/0 with source `filtered`. `p19_filtered` equals `_p17` file by file (arrays byte-identical). Protected roots: `data/processed_continuous` 65 files and `data/processed_continuous_p17` 75 files, hashes identical before and after (diff empty).
4. Check C: for every subject `nonmask_differ []`, `channels_equal True`, the three identities True (`vb==vf&vr`, `rb(3->0)==rf`, `vb subset vf`), `gained []`, raw-root reason codes within [3], raw blocks non-None, guard_sec 1.046875 for f/r/b. Pinned `raw_gate` counts match: S01 0, S02 0, S03 1 (row 160, condition 102, trial 88, offset 0, reason 3), S04 0, S05 0. The only mask change under `both` is that one S03 window; `raw_guard` is 0 in every subject under `both`.
5. Check D: `X_raw_windows` 95th percentiles of max-channel Vpp 75.3/111.3/64.0/90.1/62.1 uV for S01-S05, equal to the expected values.
6. Acceptance check 4 / check E: `cmp` of `p19_filtered_{base,harm}` vs `p17_{base,harm}_5class` CSVs is silent (byte-identical); the `.meta.txt` diffs differ only on the `quality:` line (gains `, quality source filtered`). `p19_both` rows equal `p19_filtered` rows in every column for S01, S02, S04, S05, in both banks; only S03 differs (Clean Windows 194 -> 193, one stimulus row removed by check C, matching the minus-gained rule).
7. Acceptance check 5: `configs/pipeline_config.yaml:39` is `source: both`; `build_params.quality.source` is `raw` / `both` in every subject of the new roots and `filtered` in `p19_filtered`; the data-source string carries it (`continuous build, quality source both|raw|filtered`). `_p17` keeps its original build_params (no `source`), as decided.
8. Acceptance check 1 (breakdown): tables below (also in 05_run.md, `reports/logs/P19/12_tables.txt`). Reason-1/2 counts under `filtered` and `both` are identical in every subject; the raw-root reason 3 counts are 0/19/11/13/1 for S01-S05 (raw_gate/raw_guard 0/0, 12/7, 8/3, 7/6, 0/1). `raw` is not stricter or looser than `filtered`: it runs no filtered check, so it replaces the filtered-only decision.
9. Acceptance check 3 (flagship, material = abs(d) >= max(2 SD, 2 windows)): no cell is material. Largest absolute differences: base S03 1.0 s -0.24 points (threshold 2.40) and 2.0 s -0.09 (2.32); harm S03 +0.00 at both horizons; every other subject +0.00.
10. R11: one line of `mas/state/scratch/reference_access.log` mentions P19 (07:06:19), written by this verifier's own directory-metadata listing, disclosed in 05_run.md; no builder consultation is logged for P19. Nothing in the answer-key tree was written. A privacy scan of the 05/06 files for vendor tokens returned nothing.
11. Not interpreted here: what the near-null means (reviewer; pre-committed wording in decisions.md). No threshold was changed.

### Rejection table (copy of 12_tables.txt part 1)

### Rejection table (per subject x source; root, quality source)

| Subj | source (root) | windows | valid | valid no guard | r1 gate | r2 guard | r3 total (raw_gate/raw_guard) | kept | dropped |
|---|---|---|---|---|---|---|---|---|---|
| S01 | filtered (`data/processed_continuous_p17`) | 320 | 320 | 320 | 0 | 0 | 0 (-/-) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S01 | raw (`data/processed_continuous_p19_raw`) | 320 | 320 | 320 | 0 | 0 | 0 (0/0) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S01 | both (`data/processed_continuous_p19_both`) | 320 | 320 | 320 | 0 | 0 | 0 (0/0) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S02 | filtered (`data/processed_continuous_p17`) | 320 | 301 | 309 | 11 | 8 | 0 (-/-) | PO7,PO3,POz,PO4,PO8,O1,Oz,O2 | none |
| S02 | raw (`data/processed_continuous_p19_raw`) | 320 | 301 | 308 | 0 | 0 | 19 (12/7) | PO7,PO3,POz,PO4,PO8,O1,Oz,O2 | none |
| S02 | both (`data/processed_continuous_p19_both`) | 320 | 301 | 308 | 11 | 8 | 0 (0/0) | PO7,PO3,POz,PO4,PO8,O1,Oz,O2 | none |
| S03 | filtered (`data/processed_continuous_p17`) | 320 | 310 | 313 | 7 | 3 | 0 (-/-) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S03 | raw (`data/processed_continuous_p19_raw`) | 320 | 309 | 312 | 0 | 0 | 11 (8/3) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S03 | both (`data/processed_continuous_p19_both`) | 320 | 309 | 312 | 7 | 3 | 1 (1/0) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S04 | filtered (`data/processed_continuous_p17`) | 320 | 307 | 313 | 7 | 6 | 0 (-/-) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S04 | raw (`data/processed_continuous_p19_raw`) | 320 | 307 | 313 | 0 | 0 | 13 (7/6) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S04 | both (`data/processed_continuous_p19_both`) | 320 | 307 | 313 | 7 | 6 | 0 (0/0) | PO3,POz,PO4,PO8,O1,Oz,O2 | PO7 |
| S05 | filtered (`data/processed_continuous_p17`) | 320 | 319 | 320 | 0 | 1 | 0 (-/-) | PO7,PO3,POz,PO4,PO8,O1,Oz,O2 | none |
| S05 | raw (`data/processed_continuous_p19_raw`) | 320 | 319 | 320 | 0 | 0 | 1 (0/1) | PO7,PO3,POz,PO4,PO8,O1,Oz,O2 | none |

### By label: r1/r2/r3 (valid/total)


### By label: own_gate(r1)/guard(r2)/raw(r3) per label, valid/total

| Subj | source | 101 | 102 | 103 | 104 | 105 | 201 | 202 |
|---|---|---|---|---|---|---|---|---|
| S01 | filtered | 0/0/- (40/40) | 0/0/- (40/40) | 0/0/- (40/40) | 0/0/- (40/40) | 0/0/- (40/40) | 0/0/- (80/80) | 0/0/- (40/40) |
| S01 | raw | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (80/80) | 0/0/0 (40/40) |
| S01 | both | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (80/80) | 0/0/0 (40/40) |
| S02 | filtered | 0/0/- (40/40) | 2/2/- (36/40) | 3/2/- (35/40) | 0/1/- (39/40) | 0/0/- (40/40) | 4/2/- (74/80) | 2/1/- (37/40) |
| S02 | raw | 0/0/0 (40/40) | 0/0/4 (36/40) | 0/0/5 (35/40) | 0/0/1 (39/40) | 0/0/0 (40/40) | 0/0/6 (74/80) | 0/0/3 (37/40) |
| S02 | both | 0/0/0 (40/40) | 2/2/0 (36/40) | 3/2/0 (35/40) | 0/1/0 (39/40) | 0/0/0 (40/40) | 4/2/0 (74/80) | 2/1/0 (37/40) |
| S03 | filtered | 1/1/- (38/40) | 2/0/- (38/40) | 0/0/- (40/40) | 0/0/- (40/40) | 1/1/- (38/40) | 2/1/- (77/80) | 1/0/- (39/40) |
| S03 | raw | 0/0/2 (38/40) | 0/0/3 (37/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/2 (38/40) | 0/0/3 (77/80) | 0/0/1 (39/40) |
| S03 | both | 1/1/0 (38/40) | 2/0/1 (37/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 1/1/0 (38/40) | 2/1/0 (77/80) | 1/0/0 (39/40) |
| S04 | filtered | 3/1/- (36/40) | 0/0/- (40/40) | 0/0/- (40/40) | 0/1/- (39/40) | 0/0/- (40/40) | 3/2/- (75/80) | 1/2/- (37/40) |
| S04 | raw | 0/0/4 (36/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/1 (39/40) | 0/0/0 (40/40) | 0/0/5 (75/80) | 0/0/3 (37/40) |
| S04 | both | 3/1/0 (36/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/1/0 (39/40) | 0/0/0 (40/40) | 3/2/0 (75/80) | 1/2/0 (37/40) |
| S05 | filtered | 0/0/- (40/40) | 0/0/- (40/40) | 0/0/- (40/40) | 0/0/- (40/40) | 0/1/- (39/40) | 0/0/- (80/80) | 0/0/- (40/40) |
| S05 | raw | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/1 (39/40) | 0/0/0 (80/80) | 0/0/0 (40/40) |
| S05 | both | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/0/0 (40/40) | 0/1/0 (39/40) | 0/0/0 (80/80) | 0/0/0 (40/40) |

### Flagship (5-class, cv-repeats 10, per subject)


Bank base: filtered = `data/processed_continuous_p17` (quality source filtered, csv `n_subjects_benchmark_p19_filtered_base.csv`); both = `data/processed_continuous_p19_both` (quality source both, csv `n_subjects_benchmark_p19_both_base.csv`)

| Subj | clean f/b | 1.0s filtered (SD) | 1.0s both (SD) | d1.0 | 2.0s filtered (SD) | 2.0s both (SD) | d2.0 | material? (abs(d) >= max(2*maxSD, 2 windows = 200/clean)) |
|---|---|---|---|---|---|---|---|---|
| S01 | 200/200 | 73.15 (1.93) | 73.15 (1.93) | +0.00 | 78.85 (2.04) | 78.85 (2.04) | +0.00 | 1.0s no (thr 3.86); 2.0s no (thr 4.08) |
| S02 | 190/190 | 73.05 (2.49) | 73.05 (2.49) | +0.00 | 76.63 (3.05) | 76.63 (3.05) | +0.00 | 1.0s no (thr 4.98); 2.0s no (thr 6.10) |
| S03 | 194/193 | 93.76 (1.2) | 93.52 (1.13) | -0.24 | 93.92 (1.13) | 93.83 (1.16) | -0.09 | 1.0s no (thr 2.40); 2.0s no (thr 2.32) |
| S04 | 195/195 | 99.38 (0.4) | 99.38 (0.4) | +0.00 | 99.38 (0.4) | 99.38 (0.4) | +0.00 | 1.0s no (thr 1.03); 2.0s no (thr 1.03) |
| S05 | 199/199 | 98.89 (0.62) | 98.89 (0.62) | +0.00 | 99.05 (0.6) | 99.05 (0.6) | +0.00 | 1.0s no (thr 1.24); 2.0s no (thr 1.20) |

Bank harm: filtered = `data/processed_continuous_p17` (quality source filtered, csv `n_subjects_benchmark_p19_filtered_harm.csv`); both = `data/processed_continuous_p19_both` (quality source both, csv `n_subjects_benchmark_p19_both_harm.csv`)

| Subj | clean f/b | 1.0s filtered (SD) | 1.0s both (SD) | d1.0 | 2.0s filtered (SD) | 2.0s both (SD) | d2.0 | material? (abs(d) >= max(2*maxSD, 2 windows = 200/clean)) |
|---|---|---|---|---|---|---|---|---|
| S01 | 200/200 | 85.5 (1.97) | 85.5 (1.97) | +0.00 | 91.45 (1.85) | 91.45 (1.85) | +0.00 | 1.0s no (thr 3.94); 2.0s no (thr 3.70) |
| S02 | 190/190 | 86.74 (1.57) | 86.74 (1.57) | +0.00 | 88.16 (0.9) | 88.16 (0.9) | +0.00 | 1.0s no (thr 3.14); 2.0s no (thr 1.80) |
| S03 | 194/193 | 99.38 (0.22) | 99.38 (0.33) | +0.00 | 99.48 (0.0) | 99.48 (0.24) | +0.00 | 1.0s no (thr 1.04); 2.0s no (thr 1.04) |
| S04 | 195/195 | 100.0 (0.0) | 100.0 (0.0) | +0.00 | 100.0 (0.0) | 100.0 (0.0) | +0.00 | 1.0s no (thr 1.03); 2.0s no (thr 1.03) |
| S05 | 199/199 | 99.85 (0.34) | 99.85 (0.34) | +0.00 | 99.9 (0.32) | 99.9 (0.32) | +0.00 | 1.0s no (thr 1.01); 2.0s no (thr 1.01) |

### Flagship difference arithmetic (Python, `mas/state/scratch/p19_tables.py`)

`d = float(both_csv_value) - float(filtered_csv_value)` per subject, 1.0 s Acc and 2.0 s Smoothed columns; threshold `max(2*max(SD_f, SD_b), 200/Clean Windows)` percentage points (2 windows).

## Sources opened

- `mas/state/phases/P19-raw-quality/02_plan.md`, `00_assignment.md`, `mas/RULES.md` (R5, R9), logs under `reports/logs/P19/`.
