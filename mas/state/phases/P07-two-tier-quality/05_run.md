# P07 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: phase/P07-two-tier-quality @ fa5dadeec71561725efd72c493ee22c5edf1946f (clean tree, `git status --porcelain` empty in every log header)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (`.venv`), CPU

Commands were run once each from the repo root, in the order below. Log header: command, HEAD, start time, porcelain status, Python version; the last line is `EXIT_CODE=<n>`.

## Commands executed

| # | Command (`.venv/bin/python -m ...`) | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 1 | `scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --processed-dir data/processed_p07_demo/vppmin5 --no-figures` | 2026-10-25T13:32:01-06:00 | 1 s | 0 | `reports/logs/P07/run_preprocessing_vppmin5_20261025_133201.log` | `data/processed_p07_demo/vppmin5/S03/` (3 arrays + channels.json) + root copy |
| 2 | `scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --no-channel-drop --processed-dir data/processed_p07_demo/vppmin5_nodrop --no-figures` | 2026-10-25T13:32:06-06:00 | 1 s | 1 (S03 skipped, "no window accepted") | `reports/logs/P07/run_preprocessing_vppmin5_nodrop_20261025_133206.log` | no arrays |
| 3 | `scripts.preprocessing.run_preprocessing --subject S03 --processed-dir data/processed_p07_demo/pinned --no-figures` | 2026-10-25T13:32:07-06:00 | 1 s | 0 | `reports/logs/P07/run_preprocessing_pinned_20261025_133207.log` | `data/processed_p07_demo/pinned/S03/` + root copy |
| 4 | `scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed --n-jobs 5` | 2026-10-25T13:32:13-06:00 | 6 s (script: "runtime 5 s") | 0 | `reports/logs/P07/benchmark_n_subjects_20261025_133213.log` | `reports/n_subjects_benchmark.csv` (+ .meta.txt) |

Runtimes measured with `date +%s` around each command; far below `LOCAL_RUN_BUDGET_MIN` 120.

D0 (legacy arrays, first 16 hex of sha256, 18 files) recorded before (`mas/state/scratch/d0_before.txt`) and after all four runs: identical to each other and to the list in 07_review.md (S01 45a9b0332d257a73/241adcdcc438fe3f/1846c4e5b4faabb3; S02 9c2ff184b6c0791e/1ad628ad2119e36b/37c0f53c5c4a9949; S03 51262dccc970a5d1/88e9a294b668e5b5/112c8507c38f2193; S04 eb6ef0fbc96c47df/d9dbca887edfdd82/cebc9c5858b6f90f; S05 9400ebfd5057a223/d41793f3ed5a6e35/1846c4e5b4faabb3; root = S03). `diff` printed no difference.

## Human run requests

None.

## Console numbers (verbatim from the logs)

### Run 1 (vpp_min 5.0, tier 1 on)
- `[!] legacy regression demo (PF-07): raw gate vpp_min 5 uV instead of the pinned 0.5; expect most windows rejected`
- `Tier 1: ... vpp [5, 200] uV, std [0.5, 60] uV, drop if fail fraction > 0.5`; `fs 256 Hz (header), 8 channels, 154896 samples (605.1 s)`
- Channel report (605 non-overlapping 1 s windows): PO7 fail 100.0% (605/605), mean Vpp 797.56 uV, mean std 150.01 uV -> DROPPED; PO3 0.0% (0/605) 40.57/7.97; POz 0.0% 40.01/7.84; PO4 0.0% 37.82/7.36; PO8 0.3% (2/605) 37.77/7.09; O1 0.0% 42.21/7.15; Oz 0.0% 37.14/6.54; O2 0.0% 36.21/6.27 (mean Vpp / mean std, uV). `channels kept ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2']; dropped ['PO7']`
- `gated 320: accepted 317, rejected 3 (vpp_low 0, vpp_high 3, std_low 0, std_high 3)`; per condition accepted: 101-105 40/40 each, 201 78/80, 202 39/40. Rejections: 201 sub 0 and sub 1 (onset 1280), 202 (onset 1792), all channel PO8.
- `[quality] S03 ungated windows, gate raw: 317/320 windows valid, 3 rejected`; Vpp observed 20.547 / 35.638 / 753.541 uV (min/median/max) vs limits [5, 200]; std observed 3.863 / 6.577 / 181.639 uV vs [0.5, 60]; windows per condition `201: 78, 202: 39, 101: 40, 102: 40, 103: 40, 104: 40, 105: 40`.
- `S03: n = 317 windows (stimulus 200); accepted 317, rejected 3, skipped segments 0; X_time (317, 7, 256), X_psd (317, 217)`

### Run 2 (vpp_min 5.0, `--no-channel-drop`)
- `Tier 1: channel drop disabled (--no-channel-drop)`; `Gate: vpp [5, 200] uV, std [0.5, 60] uV`
- `[-] Skipping S03: no window accepted`
- `gated 320: accepted 0, rejected 320 (vpp_low 0, vpp_high 320, std_low 0, std_high 317)`; per condition: 101-105 `accepted 0/40, rejected 40 (vpp_low 0, vpp_high 40, std_low 0, std_high 40)`; 201 `accepted 0/80, rejected 80 (... vpp_high 80, ... std_high 78)`; 202 `accepted 0/40, rejected 40 (... vpp_high 40, ... std_high 39)`. Listed rejections name channels ['PO7', 'PO8'] then ['PO7'].
- `Cohort: 0 subjects processed, 1 skipped (S03); 0 windows; gated 0, accepted 0, rejected 0`. Exit 1. No ungated summary line printed (subject skipped).

### Run 3 (pinned default)
- `Gate: vpp [0.5, 200] uV, std [0.5, 60] uV`; same channel report and kept/dropped as run 1 (PO7 dropped).
- `gated 320: accepted 317, rejected 3 (vpp_low 0, vpp_high 3, std_low 0, std_high 3)`; per condition identical to run 1.
- `[quality] S03 ungated windows, gate raw: 317/320 windows valid, 3 rejected`; Vpp 20.547 / 35.638 / 753.541 uV vs limits [0.5, 200]; std 3.863 / 6.577 / 181.639 uV vs [0.5, 60].
- `S03: n = 317 windows (stimulus 200); ... X_time (317, 7, 256), X_psd (317, 217)`; `channels.json`: kept PO3, POz, PO4, PO8, O1, Oz, O2; dropped PO7; fs 256.0.

### Run 4 (benchmark)
Header: `Data source: legacy windows, data/processed/<S>/ (P02, session file), stimulus windows only; ... cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky)`; `quality gate ... vpp [5, 120] uV, std [1, 35] uV, channel dropped if it fails in > 50% of the windows`. Per-subject channel report printed for S01-S05 (all channels fail <= 1.5%; `channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped 0 [none]` for every subject).

```
Subject Channels Kept Channels Dropped Clean Windows Rejected Windows  1.0s Acc (%)  2.0s Smoothed (%)
    S01             7             none           200                0         64.50              75.50
    S02             7             none           196                3         66.33              71.94
    S03             7             none           197                3         90.36              95.43
    S04             7             none           197                1         98.98              98.48
    S05             7             none           200                0         96.50              96.50
   Mean                                                                       83.33              87.57
```
Per-subject lines: S01 `200 stimulus, 200 clean, 0 rejected`; S02 `199 stimulus, 196 clean, 3 rejected`; S03 `200, 197, 3`; S04 `198, 197, 1`; S05 `200, 200, 0`. `Cohort: 5 subjects, mean 1.0 s 83.33%, 2.0 s smoothed 87.57% (legacy leaky CV, not comparable with R-6); runtime 5 s`.

## Produced files

- `reports/logs/P07/` the four logs above
- `reports/n_subjects_benchmark.csv` (and `.meta.txt`)
- `data/processed_p07_demo/vppmin5/{S03/, root copy}` and `data/processed_p07_demo/pinned/{S03/, root copy}` (X_psd_features.npy, X_time_windows.npy, y_labels.npy, channels.json); nothing under `vppmin5_nodrop`
- `mas/state/scratch/d0_before.txt`

## Anomalies

None unexpected. Exit code 1 of run 2 is the skip of S03 (PF-07 demo). Main tree `git status --porcelain` empty after the runs.

## Questions

None.
