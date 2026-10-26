# P10 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: `phase/P10-augmentation-ab` @ `5f2d5eb856ba480455a1babd96c1d1edc27e0a0d`; benchmark logs show an empty `git status --porcelain`; the pytest log shows only `?? .venv` (the symlink to the project environment placed in the worktree)
Machine: Linux 7.0.0-38-generic, CPU only (`--device cpu`), Python 3.12.3, project environment `.venv`

## Questions

ACK 07_review.md verifier 2026-10-26

## Commands executed

Pytest ran in a clean worktree of HEAD at `mas/state/scratch/verify_P10` (removed afterwards). The three benchmark commands ran once each, sequentially, from the repository root at the same HEAD with a clean tree. They read the legacy processed windows only through the project script; no preprocessing was run and the raw recordings were not touched.

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 0 | `.venv/bin/python -m pytest -o addopts="" -q` (worktree) | 2026-10-26 (log stamp 011732) | 219.16 s (pytest) | 0 (`EXIT 0`; `604 passed, 21 warnings`) | `reports/logs/P10/pytest_20261026_011732.log` | none |
| 1 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model eegnet --epochs 150 --device cpu --freeze-legacy` | 2026-10-26T01:21:20-06:00 | 389 s (01:21:20-01:27:49) | 0 | `reports/logs/P10/benchmark_nn_augmentation_eegnet_20261026_012120.log` | `reports/augmentation_ab_eegnet.csv` (+`.meta.txt`), `reports/legacy_leaky/augmentation_ab_eegnet.csv` (+`.meta.txt`) |
| 2 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model compact_cnn --epochs 150 --device cpu --freeze-legacy` | 2026-10-26T01:27:49-06:00 | 497 s (01:27:49-01:36:06) | 0 | `reports/logs/P10/benchmark_nn_augmentation_compact_cnn_20261026_012749.log` | `reports/augmentation_ab_compact_cnn.csv` (+`.meta.txt`), `reports/legacy_leaky/augmentation_ab_compact_cnn.csv` (+`.meta.txt`) |
| 3 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model shallow_conv_net --epochs 150 --device cpu --freeze-legacy` | 2026-10-26T01:36:06-06:00 | 609 s (01:36:06-01:46:15) | 0 | `reports/logs/P10/benchmark_nn_augmentation_shallow_conv_net_20261026_013606.log` | `reports/augmentation_ab_shallow_conv_net.csv` (+`.meta.txt`), `reports/legacy_leaky/augmentation_ab_shallow_conv_net.csv` (+`.meta.txt`) |

Total benchmark runtime 1495 s (about 25 min), inside `LOCAL_RUN_BUDGET_MIN` 120. Each log starts with the command, the HEAD sha, the porcelain status (empty), the start time and the Python version, and ends with `EXIT <code>` and the end time. Exit codes were captured with `$?` right after the run command inside the logging block.

## Human run requests

None.

## Produced files

- `reports/logs/P10/pytest_20261026_011732.log`
- `reports/logs/P10/benchmark_nn_augmentation_eegnet_20261026_012120.log`, `..._compact_cnn_20261026_012749.log`, `..._shallow_conv_net_20261026_013606.log`
- `reports/augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` and `.meta.txt`
- `reports/legacy_leaky/augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` and `.meta.txt`

## Anomalies

None: no warning lines in any benchmark log (the OFF-train < 40 % warning never fired), three exit codes 0, window counts 200 / 196 / 197 / 197 / 200 in all three models, 7 channels after the gate for every subject (`.meta.txt`). The pytest log has 21 warnings, the same count as in `04_tests.md` / `log.md` (`604 passed`).

## Console output, verbatim (everything after the command header of each log)

### EEGNet (`reports/logs/P10/benchmark_nn_augmentation_eegnet_20261026_012120.log`)

```text
Augmentation A/B, model eegnet [cpu], legacy leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02)
Data source: legacy windows, data/processed/<S>/ (P02, OO session), stimulus windows only; subjects S01, S02, S03, S04, S05
device=cpu (CPU and CUDA numbers differ; each is deterministic)
cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky); seed=42
smoothing: legacy i%5 trial smoothing (R8 legacy, PF-02): 2-window average, reset at i % 5 == 0 of the clean array
quality gate (R5 per-script, two-tier gate (P07), as the classical flagship): vpp [5, 120] uV, std [1, 35] uV, channel dropped if it fails in > 50% of the windows
input: raw clean windows, per-window per-channel z-score (own mean/std over time, R2); fs 250 Hz legacy label (not used by EEGNet)
training: epochs=150 (fixed, no early stopping, no validation split), batch=32, AdamW lr=0.001 wd=0.01, CosineAnnealingLR eta_min=1e-05, CE label_smoothing=0.05, manual_seed(seed+fold) per fold, seeded DataLoader generator, max-norm 1.0 on the spatial depthwise filters, augment=OFF then ON (A/B, same folds and seeds) (mixup, scale, shift, noise at p=0.5 on the z-scored training fold only, own numpy generator seeded seed+fold, PF-28/PF-29)
train accuracy: mean over folds, eval mode on the un-augmented training fold (PF-30)
  S01 augment OFF
    fold 0: train acc 90.00%  test acc 45.00%
    fold 1: train acc 85.00%  test acc 22.50%
    fold 2: train acc 81.25%  test acc 25.00%
    fold 3: train acc 80.62%  test acc 22.50%
    fold 4: train acc 79.38%  test acc 25.00%
[+] S01 OFF: 1.0 s 28.00%  2.0 s smoothed 31.50%  train 83.25%  (32 s)
  S01 augment ON
    fold 0: train acc 83.12%  test acc 57.50%
    fold 1: train acc 68.12%  test acc 27.50%
    fold 2: train acc 72.50%  test acc 22.50%
    fold 3: train acc 70.62%  test acc 32.50%
    fold 4: train acc 75.00%  test acc 37.50%
[+] S01 ON: 1.0 s 35.50%  2.0 s smoothed 42.00%  train 73.88%  (37 s)
  S02 augment OFF
    fold 0: train acc 85.90%  test acc 25.00%
    fold 1: train acc 84.08%  test acc 23.08%
    fold 2: train acc 82.17%  test acc 35.90%
    fold 3: train acc 72.61%  test acc 20.51%
    fold 4: train acc 82.17%  test acc 30.77%
[+] S02 OFF: 1.0 s 27.04%  2.0 s smoothed 31.12%  train 81.38%  (30 s)
  S02 augment ON
    fold 0: train acc 78.85%  test acc 37.50%
    fold 1: train acc 68.79%  test acc 23.08%
    fold 2: train acc 72.61%  test acc 23.08%
    fold 3: train acc 63.06%  test acc 17.95%
    fold 4: train acc 68.79%  test acc 25.64%
[+] S02 ON: 1.0 s 25.51%  2.0 s smoothed 29.59%  train 70.42%  (45 s)
  S03 augment OFF
    fold 0: train acc 95.54%  test acc 77.50%
    fold 1: train acc 96.18%  test acc 55.00%
    fold 2: train acc 100.00%  test acc 74.36%
    fold 3: train acc 100.00%  test acc 79.49%
    fold 4: train acc 100.00%  test acc 92.31%
[+] S03 OFF: 1.0 s 75.63%  2.0 s smoothed 85.79%  train 98.34%  (34 s)
  S03 augment ON
    fold 0: train acc 91.08%  test acc 77.50%
    fold 1: train acc 96.82%  test acc 82.50%
    fold 2: train acc 100.00%  test acc 71.79%
    fold 3: train acc 97.47%  test acc 76.92%
    fold 4: train acc 98.73%  test acc 94.87%
[+] S03 ON: 1.0 s 80.71%  2.0 s smoothed 88.32%  train 96.82%  (46 s)
  S04 augment OFF
    fold 0: train acc 100.00%  test acc 100.00%
    fold 1: train acc 100.00%  test acc 100.00%
    fold 2: train acc 100.00%  test acc 94.87%
    fold 3: train acc 100.00%  test acc 97.44%
    fold 4: train acc 100.00%  test acc 100.00%
[+] S04 OFF: 1.0 s 98.48%  2.0 s smoothed 98.48%  train 100.00%  (35 s)
  S04 augment ON
    fold 0: train acc 100.00%  test acc 100.00%
    fold 1: train acc 100.00%  test acc 100.00%
    fold 2: train acc 100.00%  test acc 97.44%
    fold 3: train acc 100.00%  test acc 100.00%
    fold 4: train acc 100.00%  test acc 100.00%
[+] S04 ON: 1.0 s 99.49%  2.0 s smoothed 98.48%  train 100.00%  (47 s)
  S05 augment OFF
    fold 0: train acc 97.50%  test acc 80.00%
    fold 1: train acc 97.50%  test acc 85.00%
    fold 2: train acc 100.00%  test acc 97.50%
    fold 3: train acc 99.38%  test acc 97.50%
    fold 4: train acc 100.00%  test acc 92.50%
[+] S05 OFF: 1.0 s 90.50%  2.0 s smoothed 94.00%  train 98.87%  (33 s)
  S05 augment ON
    fold 0: train acc 97.50%  test acc 87.50%
    fold 1: train acc 98.75%  test acc 90.00%
    fold 2: train acc 100.00%  test acc 97.50%
    fold 3: train acc 98.75%  test acc 97.50%
    fold 4: train acc 100.00%  test acc 97.50%
[+] S05 ON: 1.0 s 94.00%  2.0 s smoothed 97.00%  train 99.00%  (46 s)

Subject  Clean Windows  1.0s OFF (%)  1.0s ON (%)  1.0s Delta  2.0s OFF (%)  2.0s ON (%)  2.0s Delta  Train Acc OFF (%)  Train Acc ON (%)
    S01          200.0         28.00        35.50        7.50         31.50        42.00       10.50              83.25             73.88
    S02          196.0         27.04        25.51       -1.53         31.12        29.59       -1.53              81.38             70.42
    S03          197.0         75.63        80.71        5.08         85.79        88.32        2.53              98.34             96.82
    S04          197.0         98.48        99.49        1.01         98.48        98.48        0.00             100.00            100.00
    S05          200.0         90.50        94.00        3.50         94.00        97.00        3.00              98.87             99.00
   Mean          198.0         63.93        67.04        3.11         68.18        71.08        2.90              92.37             88.02

Legacy leaky CV: not comparable with R-6; runtime 386 s
Saved: reports/augmentation_ab_eegnet.csv
Frozen: reports/legacy_leaky/augmentation_ab_eegnet.csv
EXIT 0
end 2026-10-26T01:27:49-06:00
```

### Compact-CNN (`reports/logs/P10/benchmark_nn_augmentation_compact_cnn_20261026_012749.log`)

```text
Augmentation A/B, model compact_cnn [cpu], legacy leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02)
Data source: legacy windows, data/processed/<S>/ (P02, OO session), stimulus windows only; subjects S01, S02, S03, S04, S05
device=cpu (CPU and CUDA numbers differ; each is deterministic)
cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky); seed=42
smoothing: legacy i%5 trial smoothing (R8 legacy, PF-02): 2-window average, reset at i % 5 == 0 of the clean array
quality gate (R5 per-script, two-tier gate (P07), as the classical flagship): vpp [5, 120] uV, std [1, 35] uV, channel dropped if it fails in > 50% of the windows
input: raw clean windows, per-window per-channel z-score (own mean/std over time, R2); fs 250 Hz legacy label (sets the temporal kernel K = 29, PF-04 legacy)
training: epochs=150 (fixed, no early stopping, no validation split), batch=32, AdamW lr=0.001 wd=0.01, CosineAnnealingLR eta_min=1e-05, CE label_smoothing=0.05, manual_seed(seed+fold) per fold, seeded DataLoader generator, augment=OFF then ON (A/B, same folds and seeds) (mixup, scale, shift, noise at p=0.5 on the z-scored training fold only, own numpy generator seeded seed+fold, PF-28/PF-29)
train accuracy: mean over folds, eval mode on the un-augmented training fold (PF-30)
  S01 augment OFF
    fold 0: train acc 100.00%  test acc 25.00%
    fold 1: train acc 100.00%  test acc 22.50%
    fold 2: train acc 100.00%  test acc 25.00%
    fold 3: train acc 100.00%  test acc 22.50%
    fold 4: train acc 100.00%  test acc 25.00%
[+] S01 OFF: 1.0 s 24.00%  2.0 s smoothed 30.50%  train 100.00%  (48 s)
  S01 augment ON
    fold 0: train acc 100.00%  test acc 22.50%
    fold 1: train acc 100.00%  test acc 35.00%
    fold 2: train acc 100.00%  test acc 35.00%
    fold 3: train acc 100.00%  test acc 32.50%
    fold 4: train acc 100.00%  test acc 32.50%
[+] S01 ON: 1.0 s 31.50%  2.0 s smoothed 34.00%  train 100.00%  (46 s)
  S02 augment OFF
    fold 0: train acc 100.00%  test acc 32.50%
    fold 1: train acc 100.00%  test acc 28.21%
    fold 2: train acc 100.00%  test acc 46.15%
    fold 3: train acc 100.00%  test acc 35.90%
    fold 4: train acc 100.00%  test acc 20.51%
[+] S02 OFF: 1.0 s 32.65%  2.0 s smoothed 35.20%  train 100.00%  (44 s)
  S02 augment ON
    fold 0: train acc 100.00%  test acc 20.00%
    fold 1: train acc 100.00%  test acc 28.21%
    fold 2: train acc 100.00%  test acc 33.33%
    fold 3: train acc 100.00%  test acc 10.26%
    fold 4: train acc 100.00%  test acc 17.95%
[+] S02 ON: 1.0 s 21.94%  2.0 s smoothed 20.92%  train 100.00%  (52 s)
  S03 augment OFF
    fold 0: train acc 100.00%  test acc 55.00%
    fold 1: train acc 100.00%  test acc 52.50%
    fold 2: train acc 100.00%  test acc 48.72%
    fold 3: train acc 100.00%  test acc 56.41%
    fold 4: train acc 100.00%  test acc 58.97%
[+] S03 OFF: 1.0 s 54.31%  2.0 s smoothed 62.94%  train 100.00%  (45 s)
  S03 augment ON
    fold 0: train acc 100.00%  test acc 65.00%
    fold 1: train acc 100.00%  test acc 62.50%
    fold 2: train acc 100.00%  test acc 69.23%
    fold 3: train acc 100.00%  test acc 56.41%
    fold 4: train acc 100.00%  test acc 74.36%
[+] S03 ON: 1.0 s 65.48%  2.0 s smoothed 73.10%  train 100.00%  (59 s)
  S04 augment OFF
    fold 0: train acc 100.00%  test acc 50.00%
    fold 1: train acc 100.00%  test acc 65.00%
    fold 2: train acc 100.00%  test acc 48.72%
    fold 3: train acc 100.00%  test acc 56.41%
    fold 4: train acc 100.00%  test acc 46.15%
[+] S04 OFF: 1.0 s 53.30%  2.0 s smoothed 57.87%  train 100.00%  (43 s)
  S04 augment ON
    fold 0: train acc 100.00%  test acc 100.00%
    fold 1: train acc 100.00%  test acc 97.50%
    fold 2: train acc 100.00%  test acc 87.18%
    fold 3: train acc 100.00%  test acc 100.00%
    fold 4: train acc 100.00%  test acc 97.44%
[+] S04 ON: 1.0 s 96.45%  2.0 s smoothed 97.46%  train 100.00%  (55 s)
  S05 augment OFF
    fold 0: train acc 100.00%  test acc 55.00%
    fold 1: train acc 100.00%  test acc 55.00%
    fold 2: train acc 100.00%  test acc 32.50%
    fold 3: train acc 100.00%  test acc 47.50%
    fold 4: train acc 100.00%  test acc 55.00%
[+] S05 OFF: 1.0 s 49.00%  2.0 s smoothed 59.50%  train 100.00%  (46 s)
  S05 augment ON
    fold 0: train acc 100.00%  test acc 82.50%
    fold 1: train acc 100.00%  test acc 75.00%
    fold 2: train acc 100.00%  test acc 57.50%
    fold 3: train acc 100.00%  test acc 65.00%
    fold 4: train acc 100.00%  test acc 62.50%
[+] S05 ON: 1.0 s 68.50%  2.0 s smoothed 77.50%  train 100.00%  (56 s)

Subject  Clean Windows  1.0s OFF (%)  1.0s ON (%)  1.0s Delta  2.0s OFF (%)  2.0s ON (%)  2.0s Delta  Train Acc OFF (%)  Train Acc ON (%)
    S01          200.0         24.00        31.50        7.50         30.50        34.00        3.50              100.0             100.0
    S02          196.0         32.65        21.94      -10.71         35.20        20.92      -14.28              100.0             100.0
    S03          197.0         54.31        65.48       11.17         62.94        73.10       10.16              100.0             100.0
    S04          197.0         53.30        96.45       43.15         57.87        97.46       39.59              100.0             100.0
    S05          200.0         49.00        68.50       19.50         59.50        77.50       18.00              100.0             100.0
   Mean          198.0         42.65        56.77       14.12         49.20        60.60       11.39              100.0             100.0

Legacy leaky CV: not comparable with R-6; runtime 494 s
Saved: reports/augmentation_ab_compact_cnn.csv
Frozen: reports/legacy_leaky/augmentation_ab_compact_cnn.csv
EXIT 0
end 2026-10-26T01:36:06-06:00
```

### ShallowConvNet (`reports/logs/P10/benchmark_nn_augmentation_shallow_conv_net_20261026_013606.log`)

```text
Augmentation A/B, model shallow_conv_net [cpu], legacy leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02)
Data source: legacy windows, data/processed/<S>/ (P02, OO session), stimulus windows only; subjects S01, S02, S03, S04, S05
device=cpu (CPU and CUDA numbers differ; each is deterministic)
cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky); seed=42
smoothing: legacy i%5 trial smoothing (R8 legacy, PF-02): 2-window average, reset at i % 5 == 0 of the clean array
quality gate (R5 per-script, two-tier gate (P07), as the classical flagship): vpp [5, 120] uV, std [1, 35] uV, channel dropped if it fails in > 50% of the windows
input: raw clean windows, per-window per-channel z-score (own mean/std over time, R2); fs 250 Hz legacy label (not used by ShallowConvNet)
training: epochs=150 (fixed, no early stopping, no validation split), batch=32, AdamW lr=0.001 wd=0.01, CosineAnnealingLR eta_min=1e-05, CE label_smoothing=0.05, manual_seed(seed+fold) per fold, seeded DataLoader generator, augment=OFF then ON (A/B, same folds and seeds) (mixup, scale, shift, noise at p=0.5 on the z-scored training fold only, own numpy generator seeded seed+fold, PF-28/PF-29)
train accuracy: mean over folds, eval mode on the un-augmented training fold (PF-30)
  S01 augment OFF
    fold 0: train acc 100.00%  test acc 62.50%
    fold 1: train acc 100.00%  test acc 55.00%
    fold 2: train acc 100.00%  test acc 50.00%
    fold 3: train acc 100.00%  test acc 62.50%
    fold 4: train acc 100.00%  test acc 60.00%
[+] S01 OFF: 1.0 s 58.00%  2.0 s smoothed 67.00%  train 100.00%  (61 s)
  S01 augment ON
    fold 0: train acc 100.00%  test acc 67.50%
    fold 1: train acc 100.00%  test acc 57.50%
    fold 2: train acc 100.00%  test acc 50.00%
    fold 3: train acc 100.00%  test acc 75.00%
    fold 4: train acc 100.00%  test acc 65.00%
[+] S01 ON: 1.0 s 63.00%  2.0 s smoothed 73.00%  train 100.00%  (71 s)
  S02 augment OFF
    fold 0: train acc 100.00%  test acc 45.00%
    fold 1: train acc 100.00%  test acc 38.46%
    fold 2: train acc 100.00%  test acc 35.90%
    fold 3: train acc 100.00%  test acc 30.77%
    fold 4: train acc 100.00%  test acc 35.90%
[+] S02 OFF: 1.0 s 37.24%  2.0 s smoothed 38.27%  train 100.00%  (61 s)
  S02 augment ON
    fold 0: train acc 100.00%  test acc 42.50%
    fold 1: train acc 100.00%  test acc 38.46%
    fold 2: train acc 100.00%  test acc 41.03%
    fold 3: train acc 100.00%  test acc 28.21%
    fold 4: train acc 100.00%  test acc 35.90%
[+] S02 ON: 1.0 s 37.24%  2.0 s smoothed 40.82%  train 100.00%  (68 s)
  S03 augment OFF
    fold 0: train acc 100.00%  test acc 85.00%
    fold 1: train acc 100.00%  test acc 87.50%
    fold 2: train acc 100.00%  test acc 89.74%
    fold 3: train acc 100.00%  test acc 79.49%
    fold 4: train acc 100.00%  test acc 92.31%
[+] S03 OFF: 1.0 s 86.80%  2.0 s smoothed 92.89%  train 100.00%  (55 s)
  S03 augment ON
    fold 0: train acc 100.00%  test acc 90.00%
    fold 1: train acc 100.00%  test acc 92.50%
    fold 2: train acc 100.00%  test acc 87.18%
    fold 3: train acc 100.00%  test acc 84.62%
    fold 4: train acc 100.00%  test acc 100.00%
[+] S03 ON: 1.0 s 90.86%  2.0 s smoothed 96.45%  train 100.00%  (59 s)
  S04 augment OFF
    fold 0: train acc 100.00%  test acc 100.00%
    fold 1: train acc 100.00%  test acc 100.00%
    fold 2: train acc 100.00%  test acc 97.44%
    fold 3: train acc 100.00%  test acc 100.00%
    fold 4: train acc 100.00%  test acc 100.00%
[+] S04 OFF: 1.0 s 99.49%  2.0 s smoothed 98.98%  train 100.00%  (55 s)
  S04 augment ON
    fold 0: train acc 100.00%  test acc 100.00%
    fold 1: train acc 100.00%  test acc 100.00%
    fold 2: train acc 100.00%  test acc 100.00%
    fold 3: train acc 100.00%  test acc 100.00%
    fold 4: train acc 100.00%  test acc 97.44%
[+] S04 ON: 1.0 s 99.49%  2.0 s smoothed 98.98%  train 100.00%  (56 s)
  S05 augment OFF
    fold 0: train acc 100.00%  test acc 97.50%
    fold 1: train acc 100.00%  test acc 100.00%
    fold 2: train acc 100.00%  test acc 95.00%
    fold 3: train acc 100.00%  test acc 97.50%
    fold 4: train acc 100.00%  test acc 95.00%
[+] S05 OFF: 1.0 s 97.00%  2.0 s smoothed 97.50%  train 100.00%  (59 s)
  S05 augment ON
    fold 0: train acc 100.00%  test acc 100.00%
    fold 1: train acc 100.00%  test acc 100.00%
    fold 2: train acc 100.00%  test acc 97.50%
    fold 3: train acc 100.00%  test acc 97.50%
    fold 4: train acc 100.00%  test acc 95.00%
[+] S05 ON: 1.0 s 98.00%  2.0 s smoothed 99.00%  train 100.00%  (62 s)

Subject  Clean Windows  1.0s OFF (%)  1.0s ON (%)  1.0s Delta  2.0s OFF (%)  2.0s ON (%)  2.0s Delta  Train Acc OFF (%)  Train Acc ON (%)
    S01          200.0         58.00        63.00        5.00         67.00        73.00        6.00              100.0             100.0
    S02          196.0         37.24        37.24        0.00         38.27        40.82        2.55              100.0             100.0
    S03          197.0         86.80        90.86        4.06         92.89        96.45        3.56              100.0             100.0
    S04          197.0         99.49        99.49        0.00         98.98        98.98        0.00              100.0             100.0
    S05          200.0         97.00        98.00        1.00         97.50        99.00        1.50              100.0             100.0
   Mean          198.0         75.71        77.72        2.01         78.93        81.65        2.72              100.0             100.0

Legacy leaky CV: not comparable with R-6; runtime 607 s
Saved: reports/augmentation_ab_shallow_conv_net.csv
Frozen: reports/legacy_leaky/augmentation_ab_shallow_conv_net.csv
EXIT 0
end 2026-10-26T01:46:15-06:00
```

