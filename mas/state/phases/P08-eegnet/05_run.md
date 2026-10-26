# P08 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit PASS)
Branch / commit: `phase/P08-eegnet` @ cf62bb3005a21c8cc6dafe542c7b42df7075c067; `git status --porcelain` empty before every run (printed in each log header)
Machine: Linux 7.0.0-38-generic; project `.venv` Python; GPU 0 NVIDIA GeForce RTX 3050 Laptop GPU (device list); that CUDA device used for the cuda runs

Data source: legacy windows, `data/processed/<S>/` (P02, OO session), stimulus windows only; subject S03. The commands were launched from the repo root (default data root); no raw recording was addressed and no preprocessing was run.

## Commands executed

Common command (device substituted), each run twice (run1 = reported, run2 = determinism check):

`.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device <cpu|cuda> --augment off`

| # | Device | Run | Start | Runtime (wall, incl. start-up) | Exit | Log |
|---|---|---|---|---|---|---|
| 1 | cpu | 1 | 2026-10-25T14:06:06-06:00 | 35 s (script 32 s) | 0 | `reports/logs/P08/benchmark_eegnet_cpu_run1_20261025_140606.log` |
| 2 | cpu | 2 | 2026-10-25T14:06:41 (log name) | 34 s (script 31 s) | 0 | `reports/logs/P08/benchmark_eegnet_cpu_run2_20261025_140641.log` |
| 3 | cuda | 1 | 2026-10-25T14:07:15-06:00 | 22 s (script 20 s) | 0 | `reports/logs/P08/benchmark_eegnet_cuda_run1_20261025_140715.log` |
| 4 | cuda | 2 | 2026-10-25T14:07:37 (log name) | 22 s | 0 | `reports/logs/P08/benchmark_eegnet_cuda_run2_20261025_140737.log` |

Exit codes were captured inside the logged group (`EXIT_CODE=` and `RUNTIME_S=` last lines of each log). Each log starts with the command, HEAD, device, start time and the porcelain status.

Console numbers, verbatim (run1 logs; run2 logs are identical except the wall-time fields).

Channel line (both devices):
`  S03: 200 stimulus, 197 clean, 3 rejected; channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped [none]`

cpu run1:
```
    fold 0: train acc 95.54%  test acc 77.50%
    fold 1: train acc 96.18%  test acc 55.00%
    fold 2: train acc 100.00%  test acc 74.36%
    fold 3: train acc 100.00%  test acc 79.49%
    fold 4: train acc 100.00%  test acc 92.31%
[+] S03 [cpu]: 1.0 s 75.63%  2.0 s smoothed 85.79%  train 98.34%  params 2349  (32 s)
```
cuda run1:
```
    fold 0: train acc 98.09%  test acc 80.00%
    fold 1: train acc 97.45%  test acc 52.50%
    fold 2: train acc 100.00%  test acc 74.36%
    fold 3: train acc 98.73%  test acc 71.79%
    fold 4: train acc 98.73%  test acc 76.92%
[+] S03 [cuda]: 1.0 s 71.07%  2.0 s smoothed 81.22%  train 98.60%  params 2349  (20 s)
```
CSV rows (run1 = run2):
```
S03,cpu,197,3,75.63,85.79,98.34,2349
S03,cuda,197,3,71.07,81.22,98.6,2349
```
Header lines of the logs (and `.meta.txt`) state: `cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky); seed=42`, legacy i%5 smoothing (R8/PF-02), per-script quality gate (R5 legacy) with vpp [5, 120] uV, std [1, 35] uV, channel drop at > 50 %.

## Human run requests

None. Both commands are far below `LOCAL_RUN_BUDGET_MIN` 120 and `MAX_GPU_HOURS_PER_PHASE` 2.

## Produced files

- `reports/eegnet_benchmark_cpu.csv`, `reports/eegnet_benchmark_cpu.meta.txt` (state after run 2)
- `reports/eegnet_benchmark_cuda.csv`, `reports/eegnet_benchmark_cuda.meta.txt` (state after run 4)
- Copies taken after each run, before the next overwrote them: `reports/logs/P08/eegnet_benchmark_{cpu,cuda}_run{1,2}.csv` and `.meta.txt`
- The four logs listed above (all git-ignored)

## Anomalies

None. No warnings or errors in the logs; window counts as expected (197/3).
