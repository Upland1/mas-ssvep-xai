# P09 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: phase/P09-compact-shallow-cnn @ edd476edb1294004a0dd2eaf91ed70301208d8d2 (clean tree at every run; `git status --porcelain` empty in each log header)
Machine: Linux 7.0.0-38-generic x86_64, Python 3.12.3, torch 2.14.1+cu130, device CPU (`--device cpu`)

## Commands executed

Run from the repo root (`.venv/bin/python`), CPU. Each log begins with the command, HEAD, start time, porcelain status, Python version, and ends with `exit=<code>`.

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 0 | `python -m pytest -o addopts="" -q` (worktree `mas/state/scratch/verify_P09` @ HEAD) | 00:28:47 | 221 s (`real 3m41`) | 0 | `reports/logs/P09/pytest_20261026T002847.log` | none |
| 1 | `.venv/bin/python -m scripts.benchmarks.neural_networks.count_parameters` | 00:32:36 | 1 s | 0 | `reports/logs/P09/count_parameters_run1_20261026T003236.log` | `reports/network_parameter_counts.csv` (copy `reports/logs/P09/network_parameter_counts_run1.csv`) |
| 2 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_compact_cnn --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off` (run 1) | 00:32:37 | 45 s (script 43 s) | 0 | `reports/logs/P09/benchmark_compact_cnn_run1_20261026T003237.log` | `reports/compact_cnn_benchmark_cpu.{csv,meta.txt}`; run-1 copies `reports/logs/P09/compact_cnn_benchmark_cpu_run1.{csv,meta.txt}` |
| 3 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_shallow_convnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off` (run 1) | 00:33:22 | 60 s (script 57 s) | 0 | `reports/logs/P09/benchmark_shallow_convnet_run1_20261026T003322.log` | `reports/shallow_convnet_benchmark_cpu.{csv,meta.txt}`; copies `reports/logs/P09/shallow_convnet_benchmark_cpu_run1.{csv,meta.txt}` |
| 4 | command 2, run 2 (determinism) | 00:34:22 | 40 s (script 38 s) | 0 | `reports/logs/P09/benchmark_compact_cnn_run2_20261026T003422.log` | overwrites `reports/compact_cnn_benchmark_cpu.*` |
| 5 | command 3, run 2 (determinism) | 00:35:02 | 62 s (script 59 s) | 0 | `reports/logs/P09/benchmark_shallow_convnet_run2_20261026T003502.log` | overwrites `reports/shallow_convnet_benchmark_cpu.*` |

## Console numbers (run 1, verbatim)

count_parameters:
```
eegnet             2,349 (R-8 2,349) OK
shallow_convnet   14,485 (R-8 14,485) OK
compact_cnn       56,021 (R-8 56,021) OK
```
Compact-CNN:
```
  S03: 200 stimulus, 197 clean, 3 rejected; channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped [none]
    fold 0: train acc 100.00%  test acc 55.00%
    fold 1: train acc 100.00%  test acc 52.50%
    fold 2: train acc 100.00%  test acc 48.72%
    fold 3: train acc 100.00%  test acc 56.41%
    fold 4: train acc 100.00%  test acc 58.97%
[+] S03 [cpu]: 1.0 s 54.31%  2.0 s smoothed 62.94%  train 100.00%  params 56021  (43 s)
```
ShallowConvNet:
```
  S03: 200 stimulus, 197 clean, 3 rejected; channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped [none]
    fold 0: train acc 100.00%  test acc 85.00%
    fold 1: train acc 100.00%  test acc 87.50%
    fold 2: train acc 100.00%  test acc 89.74%
    fold 3: train acc 100.00%  test acc 79.49%
    fold 4: train acc 100.00%  test acc 92.31%
[+] S03 [cpu]: 1.0 s 86.80%  2.0 s smoothed 92.89%  train 100.00%  params 14485  (57 s)
```
Run 2 per-fold lines and summary lines are identical to run 1 (runtime aside); see 06.

## Human run requests

None.

## Produced files

`reports/network_parameter_counts.csv`, `reports/compact_cnn_benchmark_cpu.{csv,meta.txt}`, `reports/shallow_convnet_benchmark_cpu.{csv,meta.txt}`, and under `reports/logs/P09/`: the pytest log, five run logs, `network_parameter_counts_run1.csv`, `{compact_cnn,shallow_convnet}_benchmark_cpu_run1.{csv,meta.txt}`. All git-ignored.

## Anomalies

None. No warnings in the three phase logs; no recordings folder touched, no preprocessing run.

## Questions
