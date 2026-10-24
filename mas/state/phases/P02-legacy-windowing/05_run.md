# P02 · 05 · Run

Status: READY
Author: runner
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: phase/P02-legacy-windowing / adbc5a01f098daf7eefb214174777a0f27c90797
Machine: Linux 7.0.0-38-generic, Python 3.12.3, CPU only

## Commands executed

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 1 | `.venv/bin/python -m scripts.preprocessing.run_preprocessing --all` | 2026-10-24T17:17:59-06:00 | 5 s | 0 | `reports/logs/P02/run_preprocessing_20261024_171759.log` | see Produced files |

Run once, no single-subject re-runs (07_review.md note 1).

Pre-run existence check (PF-09): `test -d data/processed` -> absent; `test -d outputs/figures` -> absent. Both created by this run.

## Human run requests

None.

## Per-subject printed output (verbatim from the log)

```
[+] S01/OO.ebr: fs 256 Hz (header), 7 channels, 154904 samples (605.1 s)
gated 320: accepted 320, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  101: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  102: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  103: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  104: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  105: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  201: accepted 80/80, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  202: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
[quality] S01 accepted windows: 320/320 windows valid, 0 rejected
  Vpp observed 26.952 / 50.538 / 89.068 uV (min/median/max) vs limits [0.5, 200]
  std observed 4.856 / 7.186 / 15.216 uV (min/median/max) vs limits [0.5, 60]
  rejected by reason: vpp_low 0, vpp_high 0, std_low 0, std_high 0
  windows per condition: 201: 80, 202: 40, 101: 40, 102: 40, 103: 40, 104: 40, 105: 40
  S01: n = 320 windows (stimulus 200); accepted 320, rejected 0, skipped segments 0; X_time (320, 7, 256), X_psd (320, 217)
  Saved: data/processed/S01/X_psd_features.npy, data/processed/S01/X_time_windows.npy, data/processed/S01/y_labels.npy
  Figures: outputs/figures/spectra/S01/average_psd_by_condition.png, outputs/figures/spectra/S01/stimulus_vs_baseline_psd.png

[+] S02/OO.ebr: fs 256 Hz (header), 7 channels, 154912 samples (605.1 s)
gated 320: accepted 318, rejected 2 (vpp_low 0, vpp_high 2, std_low 0, std_high 2)
  101: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  102: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  103: accepted 39/40, rejected 1 (vpp_low 0, vpp_high 1, std_low 0, std_high 1)
  104: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  105: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  201: accepted 79/80, rejected 1 (vpp_low 0, vpp_high 1, std_low 0, std_high 1)
  202: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  rejected: condition 201 onset 5128 start 5128 sub 0 reasons ['vpp_high', 'std_high'] channels ['O2']
  rejected: condition 103 onset 10248 start 11016 sub 3 reasons ['vpp_high', 'std_high'] channels ['O2']
[quality] S02 accepted windows: 318/318 windows valid, 0 rejected
  Vpp observed 31.170 / 55.239 / 186.940 uV (min/median/max) vs limits [0.5, 200]
  std observed 5.261 / 8.444 / 46.655 uV (min/median/max) vs limits [0.5, 60]
  rejected by reason: vpp_low 0, vpp_high 0, std_low 0, std_high 0
  windows per condition: 201: 79, 202: 40, 101: 40, 102: 40, 103: 39, 104: 40, 105: 40
  S02: n = 318 windows (stimulus 199); accepted 318, rejected 2, skipped segments 0; X_time (318, 7, 256), X_psd (318, 217)
  Saved: data/processed/S02/X_psd_features.npy, data/processed/S02/X_time_windows.npy, data/processed/S02/y_labels.npy
  Figures: outputs/figures/spectra/S02/average_psd_by_condition.png, outputs/figures/spectra/S02/stimulus_vs_baseline_psd.png

[+] S03/OO.ebr: fs 256 Hz (header), 7 channels, 154896 samples (605.1 s)
gated 320: accepted 317, rejected 3 (vpp_low 0, vpp_high 3, std_low 0, std_high 3)
  101: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  102: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  103: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  104: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  105: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  201: accepted 78/80, rejected 2 (vpp_low 0, vpp_high 2, std_low 0, std_high 2)
  202: accepted 39/40, rejected 1 (vpp_low 0, vpp_high 1, std_low 0, std_high 1)
  rejected: condition 201 onset 1280 start 1280 sub 0 reasons ['vpp_high', 'std_high'] channels ['PO8']
  rejected: condition 201 onset 1280 start 1536 sub 1 reasons ['vpp_high', 'std_high'] channels ['PO8']
  rejected: condition 202 onset 1792 start 1536 sub 0 reasons ['vpp_high', 'std_high'] channels ['PO8']
[quality] S03 accepted windows: 317/317 windows valid, 0 rejected
  Vpp observed 20.547 / 35.546 / 166.231 uV (min/median/max) vs limits [0.5, 200]
  std observed 3.863 / 6.551 / 30.424 uV (min/median/max) vs limits [0.5, 60]
  rejected by reason: vpp_low 0, vpp_high 0, std_low 0, std_high 0
  windows per condition: 201: 78, 202: 39, 101: 40, 102: 40, 103: 40, 104: 40, 105: 40
  S03: n = 317 windows (stimulus 200); accepted 317, rejected 3, skipped segments 0; X_time (317, 7, 256), X_psd (317, 217)
  Saved: data/processed/S03/X_psd_features.npy, data/processed/S03/X_time_windows.npy, data/processed/S03/y_labels.npy
  Saved (S03 root copy): data/processed/X_psd_features.npy, data/processed/X_time_windows.npy, data/processed/y_labels.npy
  Figures: outputs/figures/spectra/S03/average_psd_by_condition.png, outputs/figures/spectra/S03/stimulus_vs_baseline_psd.png, outputs/figures/spectra/average_psd_by_condition.png

[+] S04/OO.ebr: fs 256 Hz (header), 7 channels, 154896 samples (605.1 s)
gated 320: accepted 317, rejected 3 (vpp_low 0, vpp_high 3, std_low 0, std_high 0)
  101: accepted 38/40, rejected 2 (vpp_low 0, vpp_high 2, std_low 0, std_high 0)
  102: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  103: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  104: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  105: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  201: accepted 79/80, rejected 1 (vpp_low 0, vpp_high 1, std_low 0, std_high 0)
  202: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  rejected: condition 201 onset 8960 start 8960 sub 0 reasons ['vpp_high'] channels ['O2']
  rejected: condition 101 onset 2560 start 2560 sub 0 reasons ['vpp_high'] channels ['O2']
  rejected: condition 101 onset 2560 start 3072 sub 2 reasons ['vpp_high'] channels ['O2']
[quality] S04 accepted windows: 317/317 windows valid, 0 rejected
  Vpp observed 19.791 / 38.604 / 152.862 uV (min/median/max) vs limits [0.5, 200]
  std observed 3.810 / 7.357 / 32.411 uV (min/median/max) vs limits [0.5, 60]
  rejected by reason: vpp_low 0, vpp_high 0, std_low 0, std_high 0
  windows per condition: 201: 79, 202: 40, 101: 38, 102: 40, 103: 40, 104: 40, 105: 40
  S04: n = 317 windows (stimulus 198); accepted 317, rejected 3, skipped segments 0; X_time (317, 7, 256), X_psd (317, 217)
  Saved: data/processed/S04/X_psd_features.npy, data/processed/S04/X_time_windows.npy, data/processed/S04/y_labels.npy
  Figures: outputs/figures/spectra/S04/average_psd_by_condition.png, outputs/figures/spectra/S04/stimulus_vs_baseline_psd.png

[+] S05/OO.ebr: fs 256 Hz (header), 7 channels, 154912 samples (605.1 s)
gated 320: accepted 320, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  101: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  102: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  103: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  104: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  105: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  201: accepted 80/80, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
  202: accepted 40/40, rejected 0 (vpp_low 0, vpp_high 0, std_low 0, std_high 0)
[quality] S05 accepted windows: 320/320 windows valid, 0 rejected
  Vpp observed 20.565 / 34.951 / 76.799 uV (min/median/max) vs limits [0.5, 200]
  std observed 4.139 / 6.854 / 14.815 uV (min/median/max) vs limits [0.5, 60]
  rejected by reason: vpp_low 0, vpp_high 0, std_low 0, std_high 0
  windows per condition: 201: 80, 202: 40, 101: 40, 102: 40, 103: 40, 104: 40, 105: 40
  S05: n = 320 windows (stimulus 200); accepted 320, rejected 0, skipped segments 0; X_time (320, 7, 256), X_psd (320, 217)
  Saved: data/processed/S05/X_psd_features.npy, data/processed/S05/X_time_windows.npy, data/processed/S05/y_labels.npy
  Figures: outputs/figures/spectra/S05/average_psd_by_condition.png, outputs/figures/spectra/S05/stimulus_vs_baseline_psd.png

Cohort: 5 subjects processed, 0 skipped (none); 1592 windows; gated 1600, accepted 1592, rejected 8, skipped segments 0
Saved: data/processed
```

Summary of printed counts (copied from the lines above):

| Subject | n | stimulus windows | accepted | rejected | skipped segments |
|---|---|---|---|---|---|
| S01 | 320 | 200 | 320 | 0 | 0 |
| S02 | 318 | 199 | 318 | 2 | 0 |
| S03 | 317 | 200 | 317 | 3 | 0 |
| S04 | 317 | 198 | 317 | 3 | 0 |
| S05 | 320 | 200 | 320 | 0 | 0 |

Cohort line (verbatim): `Cohort: 5 subjects processed, 0 skipped (none); 1592 windows; gated 1600, accepted 1592, rejected 8, skipped segments 0`

## Produced files

Per subject S01..S05: `data/processed/<S>/X_psd_features.npy`, `data/processed/<S>/X_time_windows.npy`, `data/processed/<S>/y_labels.npy`.
S03 root copy: `data/processed/X_psd_features.npy`, `data/processed/X_time_windows.npy`, `data/processed/y_labels.npy`.
Figures per subject: `outputs/figures/spectra/<S>/average_psd_by_condition.png`, `outputs/figures/spectra/<S>/stimulus_vs_baseline_psd.png`; S03 root figure: `outputs/figures/spectra/average_psd_by_condition.png`.
Log: `reports/logs/P02/run_preprocessing_20261024_171759.log`. None of these are committed (git-ignored).

## Anomalies

None: exit 0, no warnings or errors printed. The rejected-window lists above are part of the normal printed output; not interpreted here.

## Questions

None.
