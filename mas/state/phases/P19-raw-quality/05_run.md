# P19 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands 0-8, run-list additions A-F, Acceptance checks 1-5), 07_review.md (pre-run audit PASS 2928ddb)
Branch / commit: `phase/P19-raw-quality` @ 2994599191e6f6b2df1e3270c68c6fab6977bcab, clean worktree `mas/state/scratch/verify/P19` (symlinks to the main tree's `data/`, `reports/`, `.venv`, and `mas/state/scratch` so that `N=mas/state/scratch/p19_filtered` lands in the main tree); tracked files unmodified (`git status --porcelain` shows only the untracked symlinks and `mas/state/scratch`).
Machine: Linux 7.0.0-38, Python 3.12.3 (`.venv`), 16 logical CPUs, no GPU.

## Commands executed

Wall clock from the pre-state hash (07:06:32) to the end of command 7 (07:26:19) = 19.8 min, inside `LOCAL_RUN_BUDGET_MIN` 120. Every log's first line records the command and HEAD (the suite and builds were launched from a wrapper script, so logs carry `cmd:` plus HEAD, not the full porcelain/python header).

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 0 | hashes before (check A) | 07:06 | <1 min | 0 | `reports/logs/P19/00_hash_before.txt` | |
| S | `pytest tests/ -q -o addopts=""` | 07:06:32 | 738.35 s | 0 | `reports/logs/P19/01_pytest.log` | 1231 passed, 22 warnings (no skips, no failures) |
| 1 | `build_windows ... --quality-source filtered --out-root mas/state/scratch/p19_filtered` | 07:23:47 | 5 s (script 4.0 s) | 0 | `reports/logs/P19/02_build_filtered.log` | `mas/state/scratch/p19_filtered/S01..S05` |
| 2 | `... --quality-source raw --out-root data/processed_continuous_p19_raw` | 07:23:52 | 5 s | 0 | `reports/logs/P19/03_build_raw.log` | `data/processed_continuous_p19_raw/S01..S05` |
| 3 | `... --quality-source both --out-root data/processed_continuous_p19_both` | 07:23:57 | 5 s | 0 | `reports/logs/P19/04_build_both.log` | `data/processed_continuous_p19_both/S01..S05` |
| 4 | benchmark `--data-root data/processed_continuous_p17 --bank base --out-suffix p19_filtered_base` | 07:24:02 | 20 s | 0 | `reports/logs/P19/05_bench_p19_filtered_base.log` | `reports/n_subjects_benchmark_p19_filtered_base.{csv,meta.txt}` |
| 5 | `... --data-root data/processed_continuous_p19_both --bank base --out-suffix p19_both_base` | 07:24:22 | 19 s | 0 | `reports/logs/P19/06_bench_p19_both_base.log` | `..._p19_both_base.{csv,meta.txt}` |
| 6 | `... --data-root data/processed_continuous_p17 --bank harm --out-suffix p19_filtered_harm` | 07:24:41 | 49 s | 0 | `reports/logs/P19/07_bench_p19_filtered_harm.log` | `..._p19_filtered_harm.{csv,meta.txt}` |
| 7 | `... --data-root data/processed_continuous_p19_both --bank harm --out-suffix p19_both_harm` | 07:25:30 | 49 s | 0 | `reports/logs/P19/08_bench_p19_both_harm.log` | `..._p19_both_harm.{csv,meta.txt}` |
| 8 | hashes after + checks B, C, D, E; tables | 07:26 | | 0 | `reports/logs/P19/09_hash_after.txt`, `10_check_{B,C,D}.txt`, `11_check_E.txt`, `12_tables.txt` | |

Benchmark common prefix: `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --quality shared --cv-repeats 10 --classes 5`. Build common arguments: `--filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp harmonic intermediate`. No subject was skipped (`grep -ci skipping` = 0 in every log).

## Human run requests

None.

## Check A: protected-root hashes (verbatim)

Before (`reports/logs/P19/00_hash_before.txt`):
```
data/processed_continuous 65 c6e72a797e06ccc7fafe03dde3bb81e9ea07eb863909d6ec6a48a5b011e12aec -
data/processed_continuous_p17 75 c0e9ba84a903118bdc723634b9065e51d47ed659919c39c021d34c8760d3342d -
```
After (`reports/logs/P19/09_hash_after.txt`):
```
data/processed_continuous 65 c6e72a797e06ccc7fafe03dde3bb81e9ea07eb863909d6ec6a48a5b011e12aec -
data/processed_continuous_p17 75 c0e9ba84a903118bdc723634b9065e51d47ed659919c39c021d34c8760d3342d -
```
`diff` of the two files: empty (identical).

## Check B: regression build N vs F (verbatim, `10_check_B.txt`)
```
S01 same_file_list True npy_differ [] meta_top_differ [] quality_differ [] rejections_ok True build_params_ok True params_ok True new_quality_fields {'n_artifact_blocks_raw': None, 'artifact_fraction_raw': None, 'n_reason3_raw_guard': 0, 'n_reason3_raw_gate': 0, 'guarded_fraction_raw': None, 'channel_stats_raw': None, 'source': 'filtered'} data_source continuous build, quality source filtered
S02 same_file_list True npy_differ [] meta_top_differ [] quality_differ [] rejections_ok True build_params_ok True params_ok True new_quality_fields {'n_artifact_blocks_raw': None, 'artifact_fraction_raw': None, 'n_reason3_raw_guard': 0, 'n_reason3_raw_gate': 0, 'guarded_fraction_raw': None, 'channel_stats_raw': None, 'source': 'filtered'} data_source continuous build, quality source filtered
S03 same_file_list True npy_differ [] meta_top_differ [] quality_differ [] rejections_ok True build_params_ok True params_ok True new_quality_fields {'n_artifact_blocks_raw': None, 'artifact_fraction_raw': None, 'n_reason3_raw_guard': 0, 'n_reason3_raw_gate': 0, 'guarded_fraction_raw': None, 'channel_stats_raw': None, 'source': 'filtered'} data_source continuous build, quality source filtered
S04 same_file_list True npy_differ [] meta_top_differ [] quality_differ [] rejections_ok True build_params_ok True params_ok True new_quality_fields {'n_artifact_blocks_raw': None, 'artifact_fraction_raw': None, 'n_reason3_raw_guard': 0, 'n_reason3_raw_gate': 0, 'guarded_fraction_raw': None, 'channel_stats_raw': None, 'source': 'filtered'} data_source continuous build, quality source filtered
S05 same_file_list True npy_differ [] meta_top_differ [] quality_differ [] rejections_ok True build_params_ok True params_ok True new_quality_fields {'n_artifact_blocks_raw': None, 'artifact_fraction_raw': None, 'n_reason3_raw_guard': 0, 'n_reason3_raw_gate': 0, 'guarded_fraction_raw': None, 'channel_stats_raw': None, 'source': 'filtered'} data_source continuous build, quality source filtered
```

## Check C: raw/both roots vs F (verbatim, `10_check_C.txt`)
```
S01 nonmask_differ [] channels_equal True ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  valid f/r/b 320 320 320 | stimulus 200 200 200
  both reasons 1/2/3 [0, 0, 0] raw_gate/raw_guard 0 0 | raw-root reason codes used []
  identities vb==vf&vr True rb(3->0)==rf True vb subset vf True
  removed by both (row, label, trial, offset, reason): [] gained: []
  raw blocks/artifact/guarded 11 0.004544750296958116 0.00627485410318649 | guard_sec f/r/b 1.046875 1.046875 1.046875
S02 nonmask_differ [] channels_equal True ['PO7', 'PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  valid f/r/b 301 301 301 | stimulus 190 190 190
  both reasons 1/2/3 [11, 8, 0] raw_gate/raw_guard 0 0 | raw-root reason codes used [3]
  identities vb==vf&vr True rb(3->0)==rf True vb subset vf True
  removed by both (row, label, trial, offset, reason): [] gained: []
  raw blocks/artifact/guarded 39 0.01611237347655443 0.045290229291468705 | guard_sec f/r/b 1.046875 1.046875 1.046875
S03 nonmask_differ [] channels_equal True ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  valid f/r/b 310 309 309 | stimulus 194 193 193
  both reasons 1/2/3 [7, 3, 1] raw_gate/raw_guard 1 0 | raw-root reason codes used [3]
  identities vb==vf&vr True rb(3->0)==rf True vb subset vf True
  removed by both (row, label, trial, offset, reason): [(160, 102, 88, 0, 3)] gained: []
  raw blocks/artifact/guarded 15 0.006197706848466067 0.02259580621836587 | guard_sec f/r/b 1.046875 1.046875 1.046875
S04 nonmask_differ [] channels_equal True ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  valid f/r/b 307 307 307 | stimulus 195 195 195
  both reasons 1/2/3 [7, 6, 0] raw_gate/raw_guard 0 0 | raw-root reason codes used [3]
  identities vb==vf&vr True rb(3->0)==rf True vb subset vf True
  removed by both (row, label, trial, offset, reason): [] gained: []
  raw blocks/artifact/guarded 19 0.007850428674723686 0.03589505216403264 | guard_sec f/r/b 1.046875 1.046875 1.046875
S05 nonmask_differ [] channels_equal True ['PO7', 'PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']
  valid f/r/b 319 319 319 | stimulus 199 199 199
  both reasons 1/2/3 [0, 1, 0] raw_gate/raw_guard 0 0 | raw-root reason codes used [3]
  identities vb==vf&vr True rb(3->0)==rf True vb subset vf True
  removed by both (row, label, trial, offset, reason): [] gained: []
  raw blocks/artifact/guarded 1 0.0004131377814501136 0.003873166701094815 | guard_sec f/r/b 1.046875 1.046875 1.046875
```

## Check D: margins (verbatim, `10_check_D.txt`)
```
S01 X_time_windows max-channel Vpp p50/p95/max [61.6 73.  89.8] std p95/max [10.4 15.2] n Vpp>120 0 n std>35 0
S01 X_raw_windows max-channel Vpp p50/p95/max [63.9 75.3 98.4] std p95/max [12.  20.8] n Vpp>120 0 n std>35 0
S02 X_time_windows max-channel Vpp p50/p95/max [ 69.   91.  570.4] std p95/max [ 16.3 145.1] n Vpp>120 11 n std>35 8
S02 X_raw_windows max-channel Vpp p50/p95/max [ 71.8 111.3 555.3] std p95/max [ 21.6 166.6] n Vpp>120 12 n std>35 11
S03 X_time_windows max-channel Vpp p50/p95/max [ 43.6  58.8 755.1] std p95/max [ 10.9 182. ] n Vpp>120 7 n std>35 3
S03 X_raw_windows max-channel Vpp p50/p95/max [  46.8   64.  1989.6] std p95/max [ 12.6 761.8] n Vpp>120 8 n std>35 3
S04 X_time_windows max-channel Vpp p50/p95/max [ 47.1  78.7 270.5] std p95/max [14.5 45.7] n Vpp>120 7 n std>35 2
S04 X_raw_windows max-channel Vpp p50/p95/max [ 50.6  90.1 272.2] std p95/max [16.5 47. ] n Vpp>120 7 n std>35 4
S05 X_time_windows max-channel Vpp p50/p95/max [42.1 59.3 76.6] std p95/max [11.2 14.8] n Vpp>120 0 n std>35 0
S05 X_raw_windows max-channel Vpp p50/p95/max [ 45.7  62.1 112.9] std p95/max [13.1 27.1] n Vpp>120 0 n std>35 0
```

## Check E: flagship determinism and unaffected subjects (verbatim, `11_check_E.txt`)
```
== cmp base
CMP_IDENTICAL
== diff meta base
4c4
< quality: shared (shared decision of the built folder (valid_mask), quality source filtered); guard_sec 1.046875; params {'vpp_min': 5.0, 'vpp_max': 120.0, 'std_min': 1.0, 'std_max': 35.0, 'channel_fail_fraction': 0.5, 'artifact_block_sec': 0.25, 'guard_sec': 'auto', 'guard_rel_amplitude': 0.01}
---
> quality: shared (shared decision of the built folder (valid_mask)); guard_sec 1.046875; params {'vpp_min': 5.0, 'vpp_max': 120.0, 'std_min': 1.0, 'std_max': 35.0, 'channel_fail_fraction': 0.5, 'artifact_block_sec': 0.25, 'guard_sec': 'auto', 'guard_rel_amplitude': 0.01}
== diff rows filtered vs both base
3c3
< S03,7,PO7,194,6,fbcca,7-12 13-17 18-26 27-36 38-52,93.76,93.92,1.2,1.13,10
---
> S03,7,PO7,193,7,fbcca,7-12 13-17 18-26 27-36 38-52,93.52,93.83,1.13,1.16,10
== cmp harm
CMP_IDENTICAL
== diff meta harm
4c4
< quality: shared (shared decision of the built folder (valid_mask), quality source filtered); guard_sec 1.046875; params {'vpp_min': 5.0, 'vpp_max': 120.0, 'std_min': 1.0, 'std_max': 35.0, 'channel_fail_fraction': 0.5, 'artifact_block_sec': 0.25, 'guard_sec': 'auto', 'guard_rel_amplitude': 0.01}
---
> quality: shared (shared decision of the built folder (valid_mask)); guard_sec 1.046875; params {'vpp_min': 5.0, 'vpp_max': 120.0, 'std_min': 1.0, 'std_max': 35.0, 'channel_fail_fraction': 0.5, 'artifact_block_sec': 0.25, 'guard_sec': 'auto', 'guard_rel_amplitude': 0.01}
== diff rows filtered vs both harm
3c3
< S03,7,PO7,194,6,fbcca+harm,7-12 13-17 18-26 27-36 38-52 23-25 47-49 71-73 19-21 39-41 14-16 29-31 44-46 9.91-11.91 20.82-22.82 31.73-33.73 7.57-9.57 16.14-18.14 24.71-26.71,99.38,99.48,0.22,0.0,10
---
> S03,7,PO7,193,7,fbcca+harm,7-12 13-17 18-26 27-36 38-52 23-25 47-49 71-73 19-21 39-41 14-16 29-31 44-46 9.91-11.91 20.82-22.82 31.73-33.73 7.57-9.57 16.14-18.14 24.71-26.71,99.38,99.48,0.33,0.24,10
```

## Check F and tables (script `mas/state/scratch/p19_tables.py`, output `12_tables.txt`, verbatim)

Rows name their root and quality source (R9). Under `raw` the filtered gate and filtered guard do not run, so windows that only the filtered signal rejects are valid under `raw`; `raw` is not stricter than `filtered`, only different (the `raw` rows count 19/11/13/1 reason-3 windows in S02/S03/S04/S05 and zero reason 1/2). `-` in the by-label table = the _p17 meta has no raw field. All differences are computed by the script (`d = both - filtered`, Python expression `float(b[..]) - float(f[..])`).

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
| S05 | both (`data/processed_continuous_p19_both`) | 320 | 319 | 320 | 0 | 1 | 0 (0/0) | PO7,PO3,POz,PO4,PO8,O1,Oz,O2 | none |

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

## Produced files

- `data/processed_continuous_p19_raw/S01..S05`, `data/processed_continuous_p19_both/S01..S05` (15 files per subject), `mas/state/scratch/p19_filtered/S01..S05` (kept for the orchestrator to delete at merge).
- `reports/n_subjects_benchmark_p19_{filtered,both}_{base,harm}.{csv,meta.txt}`.
- `reports/logs/P19/*` listed above; `mas/state/scratch/p19_tables.py`.

## Anomalies

- Builds take about 1 s per subject; total run 19.8 min.
- R11 log: `grep -c P19 mas/state/scratch/reference_access.log` returns 1 line, written by this verifier's own first command (07:06:19), which listed the metadata of the answer-key directory (`ls -la ... | head -3`, no file content read) while checking how earlier phases linked their worktrees. No answer-key code was opened for P19. It has no R11 trigger and is disclosed here.
- Only untracked worktree symlinks appear in `git status`; no tracked file was modified.
