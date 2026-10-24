# P00 · 05 · Run

Status: READY
Author: runner
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: phase/P00-bootstrap, HEAD 042e1b2f5b727e310777b41f600e84abf940b97a (working tree clean before the run)
Machine: Linux 7.0.0-38-generic, Python 3.12.3 (.venv), CPU only, no torch/CUDA used

## Commands executed

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 1 | `.venv/bin/python scripts/exploration/inventory_raw.py` | 2026-10-24 14:13 (-06:00) | about 1 s | 0 | `reports/logs/P00/inventory_raw_20261024_141334.log` | `reports/raw_inventory.csv` |

## Human run requests

None.

## Produced files

- reports/logs/P00/inventory_raw_20261024_141334.log
- reports/raw_inventory.csv (git-ignored, not committed)

## Console summary line (verbatim)

```
10 files, 5 subjects, 0 deviations
```

Full console output:

```
CMD: .venv/bin/python scripts/exploration/inventory_raw.py
HEAD: 042e1b2f5b727e310777b41f600e84abf940b97a
DIRTY: 0
subject  file          samples   dur_s  stim session_start_utc   p99_uV  kind
S01      OO             154904   605.1    40 2021-10-28 21:57     785.1  calibration
S01      mOO            154912   605.1    40 2021-10-28 21:47     187.6  calibration
S02      OO             154912   605.1    40 2021-11-18 17:45      40.1  calibration
S02      mOO            154912   605.1    40 2021-11-18 18:20      37.5  calibration
S03      OO             154896   605.1    40 2021-11-20 00:36     331.4  calibration
S03      mOO            154896   605.1    40 2021-11-20 00:51    1013.8  calibration
S04      OO             154896   605.1    40 2021-11-25 01:23     481.5  calibration
S04      mOO            154912   605.1    40 2021-11-25 00:47      24.9  calibration
S05      OO             154912   605.1    40 2021-11-26 16:42      24.6  calibration
S05      mOO            154904   605.1    40 2021-11-26 16:30      23.8  calibration
10 files, 5 subjects, 0 deviations
Saved: /home/upland1/Documents/UNIVERSIDAD/Research_AI_EEG/02_data/Datos/mas-ssvep-eeg-xai/reports/raw_inventory.csv
EXIT=0
```

## CSV contents (reports/raw_inventory.csv, verbatim)

```
subject,file,samples,duration_s,stim_events,session_start_utc,p99_abs_eeg_uv,fs,n_channels,channels,event_counts,kind,deviations
S01,OO,154904,605.1,40,2021-10-28 21:57,785.129522094725,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S01,mOO,154912,605.1,40,2021-10-28 21:47,187.5906661987305,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S02,OO,154912,605.1,40,2021-11-18 17:45,40.06002101898197,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S02,mOO,154912,605.1,40,2021-11-18 18:20,37.48278903961185,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S03,OO,154896,605.1,40,2021-11-20 00:36,331.4067117309576,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S03,mOO,154896,605.1,40,2021-11-20 00:51,1013.7993548584035,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S04,OO,154896,605.1,40,2021-11-25 01:23,481.5410757446289,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S04,mOO,154912,605.1,40,2021-11-25 00:47,24.943459510803237,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S05,OO,154912,605.1,40,2021-11-26 16:42,24.585167598724375,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
S05,mOO,154904,605.1,40,2021-11-26 16:30,23.802621860504146,256.0,11,PO7;PO3;POz;PO4;PO8;O1;Oz;O2;TIMESTAMP;FLASHINGTIME;MARK,101:8;102:8;103:8;104:8;105:8;200:40;201:40;202:40;203:40,calibration,
```

## Anomalies

- Exit code 0, 0 deviations, no hard check fired (no trailing bytes).
- The task brief said the CSV has 23 rows; the file has a header plus 10 data rows (one per file, 5 subjects x 2 files), consistent with the summary line "10 files". Reported without interpretation.

## Questions

None.
