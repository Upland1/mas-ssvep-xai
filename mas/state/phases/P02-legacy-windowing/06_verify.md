# P02 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md, 02_plan.md (Acceptance checks), 03_changes (both), 04_tests.md, 05_run.md, 07_review.md, log.md, decisions.md, R-1, 01_DATA_SPEC §5.1
Clean checkout: `mas/state/scratch/verify_P02` @ ada370633360b1231a91c9fbd3889b3c25e1907f (removed afterwards)

Verdict: PASS

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests/      # run from the worktree
283 passed in 11.00s
```

## Independent re-run of the phase command

Launched through a python subprocess wrapper (`mas/state/scratch/runp02.py`) from the clean checkout:
`<repo>/.venv/bin/python -m scripts.preprocessing.run_preprocessing --all --raw-dir <repo raw dir> --processed-dir <scratch>/processed --figures-dir <scratch>/figures` -> `exit 0`.

- 18 `.npy` files written (5 subjects x 3 + 3 root). `np.array_equal` against the runner's `data/processed/` for every file: all `EQ`, `all equal: True` (runner has 18 files; `mas/state/scratch/accept_p02.out`).
- Console counts (per-subject header, `gated`, per-condition `accepted k/m`, `rejected:` lines, `n =` lines, `windows per condition`, `Cohort:` line) diffed against `reports/logs/P02/run_preprocessing_20261024_171759.log` after stripping paths: identical (`COUNTS_IDENTICAL`).

## Acceptance

Command: `.venv/bin/python mas/state/scratch/accept_p02.py` (processed arrays only; output `mas/state/scratch/accept_p02.out`).

| Criterion (verbatim) | Obtained | Reference | Met? |
|---|---|---|---|
| shapes `(n,7,256)`, `(n,217)`, labels in {201,202,101..105}, n <= 320, counts <= {201:80,202:40,101-105:40} | all 5 subjects: shape, labels, caps `True` | 01_DATA_SPEC §5.1 | yes |
| n vs R-1 | 320/318/317/317/320, all `n_ok True` | R-1 exact | yes |
| stimulus windows vs R-1 | 200/199/200/198/200, all `stim_ok True` | R-1 exact | yes |
| condition order, contiguous | block sequence `[201,202,101,102,103,104,105]` for every subject | plan | yes |
| root arrays = S03 (PF-09) | `root==S03` True for X_psd_features, X_time_windows, y_labels | exact | yes |
| PSD figure peaks at f0 (S03-S05) | numeric support below; figures judged by the reviewer | visual + ratio > 1 | numeric: yes for S03-S05 |

Per-subject label counts (verbatim): S01 {201:80,202:40,101-105:40}; S02 {201:79,202:40,101:40,102:40,103:39,104:40,105:40}; S03 {201:78,202:39,101-105:40}; S04 {201:79,202:40,101:38,102-105:40}; S05 {201:80,202:40,101-105:40}.

## Figure criterion support (supplementary numeric check)

Visual channels resolved by name from config v1 scalp order `['PO3','POz','PO4','PO8','O1','Oz','O2']`: PO8, O1, Oz, O2 (indices 3-6). Spectrum `X_psd[:, c*31 + (f-5)]` (reshape `(n,7,31)`). Columns: stimulus mean PSD (visual channels) at the f0 bin, 201 mean at that bin, ratio, whether the bin is a local maximum of the stimulus mean spectrum (greater than both neighbours), then the same ratio and flag over all 7 channels.

```
sub target f0 | stim mean | 201 mean | ratio | locmax | ratio_all7 | locmax_all7
S01 101 24 0.7468 | 0.5495 | 1.359 | True | 1.326 | True
S01 102 20 1.426 | 0.8578 | 1.662 | True | 1.598 | True
S01 103 15 2.02 | 2.125 | 0.950 | True | 0.930 | True
S01 104 11 4.483 | 2.203 | 2.035 | True | 2.201 | True
S01 105 9 1.923 | 2.183 | 0.881 | False | 0.869 | False
S02 101 24 0.7972 | 0.7656 | 1.041 | True | 1.080 | True
S02 102 20 0.6766 | 0.5462 | 1.239 | False | 1.196 | False
S02 103 15 2.33 | 1.628 | 1.432 | True | 1.387 | True
S02 104 11 3.19 | 2.932 | 1.088 | False | 1.061 | False
S02 105 9 5.943 | 6.279 | 0.946 | True | 0.964 | True
S03 101 24 3.849 | 0.3084 | 12.481 | True | 9.977 | True
S03 102 20 7.376 | 0.4623 | 15.957 | True | 13.362 | True
S03 103 15 5.985 | 0.6414 | 9.330 | True | 8.591 | True
S03 104 11 3.245 | 1.549 | 2.094 | True | 1.594 | True
S03 105 9 2.479 | 1.293 | 1.918 | True | 1.420 | False
S04 101 24 7.645 | 0.4733 | 16.151 | True | 14.051 | True
S04 102 20 10.53 | 0.6356 | 16.573 | True | 13.202 | True
S04 103 15 13.73 | 1.622 | 8.467 | True | 6.615 | True
S04 104 11 18.07 | 1.779 | 10.159 | True | 7.777 | True
S04 105 9 5.375 | 1.435 | 3.747 | True | 2.976 | True
S05 101 24 3.145 | 0.3028 | 10.389 | True | 8.777 | True
S05 102 20 1.718 | 0.4044 | 4.247 | True | 3.409 | True
S05 103 15 2.737 | 0.7407 | 3.695 | True | 2.904 | True
S05 104 11 3.447 | 1.937 | 1.780 | True | 1.661 | True
S05 105 9 1.752 | 1.31 | 1.338 | True | 1.118 | True
```

S03-S05: all 15 targets have ratio > 1 and a local maximum at f0 over the visual cluster. One point for the reviewer: S03 105 (9 Hz) is a local maximum over the visual channels but not in the 7-channel average (the figure shows 7 channels); ratio 1.420 is still > 1. S01 and S02 (not required) miss several targets (S01 103, 105; S02 102, 104, 105); not interpreted here.

## Numbers in the handoffs vs logs

`05_run.md` per-subject counts, rejected lists and Cohort line match both the runner log and my independent console (diff above). n, stimulus counts and exit 0 match `log.md` row 8.

## Sources spot-check

The `02_plan.md` acceptance rows cite 01_DATA_SPEC §5.1 and R-1; the shape rule (7 x 31 = 217) and the R-1 counts (320/318/317/317/320; 200/199/200/198/200) were reproduced exactly.

## Privacy / git

- `git ls-files` filtered for data/, reports/, outputs/, baselines/, the recording suffix, local-tooling folder/file and scratch: no hits.
- Case-insensitive `git grep` over HEAD with a fragment-built vendor/co-author pattern: no hits; `git log --format=%B main..HEAD` match count `0`; single author (17 commits).
- `git check-ignore -v data/processed/S01/y_labels.npy` -> `.gitignore:14:data/	data/processed/S01/y_labels.npy`.

## Reference consultations check

`mas/state/scratch/reference_access.log` has 2 lines: 2026-10-24T15:07:09 and 16:27:04, both verifier privacy-grep commands from earlier phases whose patterns mention the answer-key folder; no P02-era (17:xx) access. The handoffs list no consultation. Consistent; no unlisted access.

## Reasons (if FAIL)

None.
