# P16 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md, 02_plan.md, 05_run.md, 07_review.md (criteria (1)-(5) of Round 1, additions A and B of Round 2), 03_changes_*.md, 04_tests.md, decisions.md P16 rows
Clean checkout: `git worktree` at `mas/state/scratch/verify/P16` @ bb8c999 (removed after the suite; the 18 commands ran at the repository root at the same HEAD, tree clean)

Verdict: FAIL

The phase run is complete and almost every pre-committed criterion is met. One binding criterion is not: criterion (2) requires `compare_v1_v2 --check-regression` to exit 0 and it exits 1 (reason 1). The underlying data are equal; the exit code comes from the script comparing NaN entries with plain `array_equal`. Per the pre-committed text ("exit 0"), this is a miss, not a CONCERN. I do not fix code.

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests -o addopts="" -q -p no:cacheprovider     # log reports/logs/P16/00_pytest_full.log
```

`1088 passed, 1 skipped, 21 warnings in 614.28s (0:10:14)`. The skip is `test_responders_real_benchmark_if_present` (needs ignored `reports/n_subjects_benchmark.csv`, absent in a clean checkout). The tester's 1089 passed = 1088 + this test, which passes where `reports/` exists. The CUDA-skip tests ran (CUDA available).

## Acceptance (plan table)

| Criterion (verbatim) | Re-run command | Obtained | Reference | Tolerance | Met? | Log |
|---|---|---|---|---|---|---|
| snapshot exists and is read-only | cmd 1 + checks below | see (3) | `p16_v1_pre_hashes.txt` | exact | yes | `01_freeze_baseline.log` |
| edge-effect table shows edge error >> centre error for narrow FBCSP bands | cmd 2 | see (1) | reviewer (1) | ratio >= 5 and edges >= 20 % | yes | `02_...demo_edge_effects.log` |
| `stride=None` per_window build reproduces the legacy window starts | cmd 3, 4 | see (4) | n_equal = n_legacy | exact | yes | `03_`, `04_...build_windows.log` |
| v1/v2 table complete with every number backed by a log | cmd 18 | see (5) | - | - | yes (completeness); directions in the section below | `18_...compare_v1_v2.log` |
| (settled point 4) `_v1check` CSVs equal the frozen v1 ones exactly | cmd 5, 6, 17 | CSV values equal; cmd 17 exit 1 | exact | exact | **no** (exit code), see (2) | `17_...`, `05_`, `06_` |
| (R-16) | - | no numeric target; reviewer interprets | - | - | n/a | - |

## Pre-committed criteria of 07_review.md

### (1) Edge effects (`reports/edge_effects_summary.csv`, S03; log 02)

| Band (Hz) | edges % | centre % | ratio | narrow | edges >= 20 and ratio >= 5 |
|---|---|---|---|---|---|
| 7-12 | 53.236 | 6.512 | 8.17 | yes | yes |
| 13-17 | 56.684 | 7.604 | 7.45 | yes | yes |
| 18-26 | 33.097 | 1.576 | 21.00 | yes | yes |
| 27-36 | 33.756 | 1.082 | 31.20 | no | edges > centre |
| 38-52 | 23.007 | 0.153 | 150.00 | no | edges > centre |
| FBCCA 6-90 / 14-90 / 22-90 | 28.252 / 26.169 / 24.493 | 7.420 / 2.912 / 1.390 | 3.81 / 8.99 / 17.62 | no | edges > centre |

Met. Information item: the order-of-magnitude reading (ratio >= 10) is not met for 7-12 (8.17) and 13-17 (7.45), as the reviewer anticipated.

### (2) v1check regressions (blocking)

- Flagship: `cmp reports/n_subjects_benchmark_v1check.csv baselines/v1_2026-10-27/reports/n_subjects_benchmark.csv` exit 0. Met.
- Connectivity: `cmp` exit 0 for `connectivity_cohort_summary_v1check.csv`, `..._v1check_details.csv` and `connectivity_alpha_diagnostic_v1check.csv` against the frozen unsuffixed files. Met.
- 20 npz files: with plain `np.array_equal` per key, 5 of 20 equal (all PDC files) and 15 differ (coherence, PLV, wPLI). My own check (`np.array_equal(..., equal_nan=True)` on float keys) gives 20 of 20 equal; each differing key has 7 NaN entries (the diagonal of a 7x7 matrix) and max abs difference 0.0 elsewhere. Values equal, so the plain `array_equal` clause as literally written is not satisfiable for NaN matrices; the data criterion is met with NaN-aware equality.
- **`compare_v1_v2 --check-regression` exit 0: NOT met.** Log 17: four CSV lines `byte-equal`, then `[x] connectivity_edges: 5/20 npz files equal per key; different or missing: ['S01_coherence.npz', 'S01_plv.npz', 'S01_wpli.npz', 'S02_coherence.npz', 'S02_plv.npz']`, `EXIT: 1`. Cause (my reading of the output, not tested further): NaN entries compare unequal. Not a value difference; the reviewer's text makes the exit code binding, so this is reported as a miss.
- "seed 42 alone" of row a (log 07) equals R-6 per subject: S01 61.00/67.50, S02 56.12/61.73, S03 86.80/90.36, S04 97.46/97.97, S05 95.00/95.50. Met. Log 05 prints the same numbers (61.00 ... 95.50 as 1.0 s/2.0 s).

### (3) Snapshot (`baselines/v1_2026-10-27/`)

- (a) `MANIFEST.json` n_files 407 (407 file rows); the set of (path, sha256) pairs equals the set of the 407 lines of `mas/state/scratch/p16_v1_pre_hashes.txt` (Python set comparison: `True`; missing none, extra none); every file on disk (at `stored_as` where present) re-hashes to its MANIFEST value (0 mismatches). `configs/pipeline_config.yaml` sha256 `3b3f3aa9b617404e4583aa28d69f6ca5cc7a5720a91ac9396354d7c7aac2a5dc`; `configs_from_commit` `97a29bed3f6d90ca4ce0aec3392640fd23a85871`. Met. (MANIFEST `git_commit` is bb8c999c, `git_dirty` False.)
- (b) MANIFEST rows for `reports/five_subjects_benchmark.csv` and `.meta.txt` carry `stored_as` = `superseded/five_subjects_benchmark.csv` and `.meta.txt`; `ls baselines/v1_2026-10-27/reports | grep five` is empty. Met.
- (c) `find baselines/v1_* -perm /222 | wc -l` = 0; `touch baselines/v1_2026-10-27/probe` -> `Permission denied` (exit 1). Met. (The parent `baselines/` is writable by design.)
- (d) Command 1 rerun verbatim: `[x] Refusing to overwrite: tag 'v1' already frozen: baselines/v1_2026-10-27`, exit 1; `sha256sum MANIFEST.json` identical before and after; `ls baselines` = `v1_2026-10-27` only. Met.
- (e) `baseline_summary.csv` header `pipeline,subject,metric,value`; MEAN rows present (subjects: MEAN, Mean, S01..S05; the redundant `Mean` row is the reviewer's note N5, not fixed). flagship_n_subjects MEAN `1.0s Acc (%)` 79.27666666666666, `2.0s Smoothed (%)` 82.61166666666666: within 0.005 of 79.28 / 82.61. Met.

### (4) Legacy starts (logs 03, 04)

Both builds, S01-S05, conditions 201, 202, 101-105: `n_legacy == n_built == n_equal`, `max|d| 0` in all 70 lines; counts 80 / 40 / 40 x5 per subject. No subject skipped. Met. `trial-ids` lines (information): S01 0, S02 39, S03 0, S04 38, S05 0 windows in inconsistent groups (legacy stimulus windows 200/199/200/198/200; true trials 40 each). Equal to the expected S02 39 and S04 38; no anomaly. Carry-forward P02 (S03 first-trial PO8): log lines `startup S03:` show continuous vs 30 s-extended difference <= 1.79e-06 of window std on every channel (PO8 9.96e-08), first-trial windows' built reasons [3, 5, 0] (valid, own gate, guard), mean Vpp PO7 543.5, PO8 325.4 uV; legacy gate rejected 3 of 8 (starts 1280, 1536, 1536).

### (5) Determinism checks and directions

Determinism checks (all from the run CSVs):

| Check | Result |
|---|---|
| a vs a' vs a't: Clean/Rejected Windows equal per subject | yes (200/0, 196/3, 197/3, 197/1, 200/0) |
| A: a't 1.0 s Acc and 1.0 s SD equal a' per subject | yes (all five) |
| d_smoothing = 0.00 on S01 and S05 | yes (0.00, 0.00) |
| b vs c Clean/Rejected equal | yes (200/0, 190/10, 194/6, 195/5, 199/1) |
| connectivity b vs c identical in every numeric column | yes (100 rows; max abs difference 0.0 in obs_diff, p_one_tailed, n_edges_sig_fdr, total_edges, n_channels) |
| c vs c': S01 `n_valid == n_valid_no_guard` (320/320 in `windows_meta.json`) => d_guard exactly 0 | flagship 0.00 / 0.00; connectivity S01: max abs difference 0.0 in all three columns. Met |
| B: connectivity a' vs a `n_stim_windows`, `n_baseline_windows`, `trial_ids_approximate` equal in every row | yes (approximate True only for S02, S04) |
| Identity cells a vs a' (PLV, wPLI at 101/102/105; coherence at 105; 35 cells): `p_one_tailed`, `n_edges_sig_fdr` identical | yes (0 differences). `obs_diff`: 28 of 35 cells differ in the last bits, max abs difference 2.44e-16 (floating-point round-off; the rest identical). Reported as CONCERN for the reviewer: not bit-identical, not value-different |

Flagship directions (file `reports/v1_vs_v2/flagship.csv`, md `reports/v1_vs_v2/v1_vs_v2.md`; unit rule: change if |D| >= 1.0 pp and |D| > larger repeat SD; one window about 0.5 pp). pp; `none` = no material change (sign given only).

| Effect | Subject | 1.0 s | 2.0 s |
|---|---|---|---|
| fs (a' - a) | S01 | +11.30 change | +8.90 change |
| | S02 | +18.47 change | +18.16 change |
| | S03 | +6.30 change | +5.18 change |
| | S04 | +1.22 change | -0.41 none |
| | S05 | +2.90 change | +2.70 change |
| | Mean | +8.04 change | +6.91 change |
| smoothing rule (a't - a', 2.0 s) | S01 / S05 | 0.00 / 0.00 | |
| | S02 / S03 / S04 | | -2.55 none / -2.64 change / +2.03 change |
| | Mean | | -0.63 none |
| build (b - a' at 1.0 s; b - a't at 2.0 s) | S01 | -0.30 none | +0.40 none |
| | S02 | -8.03 change | -7.79 change |
| | S03 | -1.12 none | -0.59 none |
| | S04 | -0.11 none | -0.41 none |
| | S05 | +0.39 none | +0.49 none |
| | Mean | -1.83 change | -1.58 change |
| filter mode (c - b) | S01..S05 | +0.10, +1.37, +0.21, -0.10, +0.30 (all none) | +0.20, -0.42, -0.31, -0.10, +0.40 (all none) |
| | Mean | +0.37 none | -0.05 none |
| guard (c - c') | S01..S05 | 0.00, -4.50 change, +0.04, -0.10, -0.41 | 0.00, -3.30 none, -0.06, -0.10, -0.31 (none except as noted) |
| | Mean | -1.00 none | -0.76 none |
| total (c - a) | Mean | +6.58 change | +4.65 change |

Rows (mean over 5 seeds; SD in `flagship.csv`): Mean 1.0 s / 2.0 s: v1 79.28 / 82.61; a 80.80 / 84.42; a' 88.84 / 91.33; a't 88.84 / 90.70; b 87.01 / 89.12; c 87.38 / 89.07; c' 88.38 / 89.83.

Guard bound `|d_guard| <= 100 * guard-only stimulus rejections / clean windows of c' + larger SD` (guard-only stimulus rejections from `valid_mask` vs `valid_mask_no_guard`: S01 0/200, S02 5/195, S03 2/196, S04 2/197, S05 1/200): holds in all 10 cells (S02 4.50 <= 5.90 and 3.30 <= 7.52; others far inside).

Comparison with the reviewer's a-priori expectations (facts; interpretation left to the reviewer):

- fs 1.0 s positive in every subject: yes. Mean >= +3 pp: yes (+8.04). Size ordering: largest S02 (+18.47) and S01 (+11.30), smallest S04 (+1.22) and S05 (+2.90); the a-row accuracy of S02 (60.61) is lower than S01 (61.70), consistent in direction. 2.0 s: positive except S04 -0.41 (no material change; a' 97.97, SD 0.00).
- Smoothing: S01, S05 exactly 0.00 as required; S02 -2.55 and S03 -2.64 (P11 at fs 250 gave -2.55 and -3.56); S04 +2.03 (a't 100.00, SD 0.00, 4 windows).
- Build: Mean -1.83 / -1.58, inside the expected |Mean| <= 3 pp. S02 is -8.03 / -7.79 with 8 channels kept and 10 rejected windows (190 clean) versus 196 clean in a'; S04 -0.11 / -0.41 (the expectation "decrease if anything on S02/S04": S02 yes, S04 not material). Channel drop: PO7 dropped in S01, S03, S04, kept in S02, S05.
- Filter mode: Mean +0.37 / -0.05, inside [-1, +2]. No negative Mean below -1.
- Guard: expected sign >= 0; observed S02 -4.50 / -3.30, S04 -0.10 / -0.10, S05 -0.41 / -0.31 (negative), S03 +0.04 / -0.06, S01 0.00. Magnitudes within the bound above. Clean windows c vs c': S02 190 vs 195, S03 194 vs 196, S04 195 vs 197, S05 199 vs 200.

Connectivity directions (file `reports/v1_vs_v2/connectivity.csv`: 100 rows = 5 subjects x 4 methods x 5 conditions; columns obs_diff, p_one_tailed, n_edges_sig_fdr for a', b, c, c' and a from the frozen baseline). Mean difference of `obs_diff` per method over its 25 cells and summed FDR edge counts (a, a', b, c, c'):

| Method | mean D fs (a'-a) | mean D build (b-a') | mean D guard (c-c') | FDR edges a / a' / b / c / c' | global p < 0.05 cells a / a' / b / c / c' |
|---|---|---|---|---|---|
| coherence | -0.0079 | +0.0045 | -0.0002 | 125 / 123 / 136 / 136 / 136 | 8 / 8 / 8 / 8 / 8 |
| plv | -0.0063 | +0.0010 | -0.0003 | 67 / 47 / 55 / 55 / 54 | 4 / 4 / 4 / 4 / 4 |
| wpli | -0.0126 | +0.0038 | -0.0040 | 79 / 83 / 91 / 91 / 87 | 12 / 11 / 11 / 11 / 11 |
| pdc | -0.0002 | +0.0058 | +0.0005 | 46 / 42 / 54 / 54 / 50 | 11 / 11 / 9 / 9 / 9 |

Per condition (mean D obs_diff fs; FDR a -> a'): coherence 101 -0.0069 (44 -> 43), 102 -0.0132 (32 -> 31), 103 -0.0092 (22 -> 21), 104 -0.0102 (12 -> 13), 105 0.0000 (15 -> 15); PLV 103 -0.0219 (FDR 19 -> 4), PLV 104 -0.0097 (16 -> 11), PLV 101/102/105 ~0; wPLI 103 -0.0480 (5 -> 3), wPLI 104 -0.0148 (9 -> 15), wPLI 101/102/105 ~0; PDC all |D| <= 0.0007. For condition 104 (coherence a vs a' per subject, obs_diff): S01 0.0323 -> 0.0008, S02 -0.0148 -> -0.0175, S03 -0.0366 -> -0.0406, S04 0.1934 -> 0.1727, S05 -0.0836 -> -0.0759; PLV 104: S01 -0.0027 -> -0.0020, S02 -0.0393 -> -0.0189, S03 0.0024 -> -0.0123, S04 0.0830 -> 0.0491, S05 -0.0706 -> -0.0915.

Global p crossing 0.05 between variants (cells): fs 1 (S03 wPLI 103: 0.05 -> 0.06); build 4 (S02 PDC 103: 0.045 -> 0.109; S04 wPLI 103: 0.05 -> 0.09; S05 PDC 102: 0.02 -> 0.124; S05 wPLI 102: 0.065 -> 0.02); guard 0. The build step changes the channel set for S02 and S05 (`n_channels` 8 vs 7), so FDR counts and `total_edges` are not on the same denominator there (reviewer note N1; counts are not rescaled).

Table completeness: flagship.csv 12 rows (5 subjects + Mean, two windows), connectivity.csv 100 rows; the console reports no missing input. Filter-mode connectivity columns read `not applicable (same input)` (decisions row 133).

## Numbers in the handoffs vs logs

Every number above comes from the CSV or log named in the row: `reports/n_subjects_benchmark_<suffix>.csv`, `reports/connectivity_cohort_summary_<suffix>.csv`, `reports/v1_vs_v2/flagship.csv` and `connectivity.csv`, `baselines/v1_2026-10-27/MANIFEST.json`, `windows_meta.json` and `valid_mask*.npy` of the builds, and `reports/logs/P16/*.log`. Differences, group counts and the unit-rule classification were computed with ad-hoc Python on those files (scripts deleted after use, as scratch). The builders' smoke previews for row a' (Mean 88.84 / 91.33, SD 1.40 / 1.17) equal the run (`n_subjects_benchmark_v1fs256.csv`: 88.84 / 91.33, 1.4 / 1.17).

## Sources spot-check

- `mas/04_REFERENCE_RESULTS.md` R-6 (opened through `mas/RULES.md` table): the row-a seed-42 numbers equal R-6 per subject (S01 61.00/67.50 ... S05 95.00/95.50) and MEAN 79.28 / 82.61.
- `07_review.md` pre-committed criteria (opened and applied verbatim).
- `02_plan.md` run list (opened): flags identical to those executed.

## Reference consultations check

`mas/state/scratch/reference_access.log` has 40 lines, the last timestamped 2026-10-26T23:53:40 (P15, scientific-reviewer). No entry from 2026-10-27 (P16 start) on. The three P16 handoffs state "None" under R11. Consistent.

## Reasons (if FAIL)

1. Criterion (2): `.venv/bin/python -m scripts.diagnostics.compare_v1_v2 --check-regression` exits 1 (log `reports/logs/P16/17_scripts.diagnostics.compare_v1_v2.log`: `[x] connectivity_edges: 5/20 npz files equal per key`), where the pre-committed text requires exit 0. The four CSV comparisons in the same run are byte-equal and my NaN-aware comparison finds all 20 npz files equal, so the data regression is clean and only the check's equality of NaN diagonals (15 coherence/PLV/wPLI files) fails. The required exit code is not met.

Other items for the reviewer (not FAIL reasons): (i) 28 of 35 identity cells have `obs_diff` equal only to 2.44e-16 between a and a', with `p_one_tailed` and `n_edges_sig_fdr` identical; (ii) guard effect sign negative in S02/S04/S05 against the a-priori expectation >= 0; (iii) skipped test in the clean checkout is the one that reads ignored `reports/`; (iv) reviewer note N5 (redundant `Mean` subject in `baseline_summary.csv`) is still present.

## Round 2 re-verification

Verdict: PASS

Branch HEAD 215bf44. Scope per 07_review.md 645312e: full suite plus commands 17-18.

- Suite on a clean worktree: `1101 passed, 1 skipped, 21 warnings in 613.05s (0:10:13)` (`reports/logs/P16/00_pytest_full_r2.log`). The skip is the same ignored-`reports/` test as in the first run.
- Command 17 (`17_scripts.diagnostics.compare_v1_v2_r2.log`): four CSVs `byte-equal`, `[+] connectivity_edges: 20/20 npz files equal per key`, `EXIT: 0`. Criterion (2) is met: exit 0, 20/20 npz equal, four CSVs byte-equal.
- Command 18 (`18_..._r2.log`): exit 0; `flagship.csv` and `connectivity.csv` byte-identical to the first run, so all first-run numbers and directions in this file stand.
- All other criteria (1), (3), (4), (5) are unchanged from the first run (no re-execution of commands 1-16).

The first-run FAIL (reason 1) is kept above as the record; it is resolved by 9b297c0/45a1d79. Verdict restated: PASS.
