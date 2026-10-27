# P15 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands), 07_review.md (pre-run audit Round 2 PASS)
Branch / commit: phase/P15-graph-gnn @ 2392299695934f59dfaf3b52d4c485f57baa13c3 (porcelain-empty before every command; each log records HEAD and STATUS_PORCELAIN)
Machine: Linux 7.0.0-38-generic, 12th Gen Intel i5-12500H (16 threads), Python 3.12.3, torch 2.14.1+cu130 (run on CPU, `--device cpu`), scikit-learn 1.9.1

Run location: the main repository checkout (clean worktree at HEAD, as in P14), so that `data/processed/<S>/graph_dataset.npz` and `reports/` land in the main repository. The verifier did not read the participant recordings; only the project scripts did.

## Commands executed

| # | Command | Start (-06:00) | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 0 | `.venv/bin/python -m pytest tests -o addopts="" -q` | 2026-10-26 evening | 432.56 s (948 passed) | 0 | `reports/logs/P15/pytest_full.log` | none |
| 1 | `.venv/bin/python -m scripts.connectivity.graph_modeling.build_graph_dataset --rebuild` | 2026-10-27T00:01:58 | 11 s | 0 | `reports/logs/P15/cmd1_build.log` | `data/processed/S0{1..5}/graph_dataset.npz` (NEW), `reports/graph_dataset_sanity.csv` |
| 2 | `.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_connectivity_gate --repeats 5 --k-select 0 30` | 2026-10-27T00:02:09 | 75 s | 0 | `reports/logs/P15/cmd2_gate.log` | `reports/connectivity_gate_benchmark.csv` (+ `.meta.txt`) |
| 3 | `.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_gnn --smoke-test` | 2026-10-27T00:03:25 | 1 s | 0 | `reports/logs/P15/cmd3_smoke.log` | `reports/gnn_benchmark_smoke.csv` (+ `.meta.txt`) |
| 4 | `.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_gnn --repeats 3 --epochs 150 --device cpu` | ~2026-10-27T00:03:30 | 241 s | 0 | `reports/logs/P15/cmd4_gnn.log` | `reports/gnn_benchmark.csv` (+ `.meta.txt`) |

Each command ran exactly once. The A8 hashes are in `reports/logs/P15/a8_hash_before.txt` and `a8_hash_after.txt`. The analysis script and its output are `mas/state/scratch/p15_verify.py` and `mas/state/scratch/p15_verify.out`.

## Human run requests

None. Total run time of commands 1-4 was about 5.5 min.

## Produced files

- data/processed/S01..S05/graph_dataset.npz (NEW, git-ignored)
- reports/graph_dataset_sanity.csv
- reports/connectivity_gate_benchmark.csv, reports/connectivity_gate_benchmark.meta.txt
- reports/gnn_benchmark_smoke.csv, reports/gnn_benchmark_smoke.meta.txt
- reports/gnn_benchmark.csv, reports/gnn_benchmark.meta.txt
- reports/logs/P15/{pytest_full,cmd1_build,cmd2_gate,cmd3_smoke,cmd4_gnn}.log, a8_hash_before.txt, a8_hash_after.txt

## Anomalies

None in the run itself: all exits 0, no warnings in the command logs beyond the 21 existing pytest warnings. Results deviate from R-15 in places; see 06_verify.md.
