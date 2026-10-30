# P24 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (Run commands, settled 7 and 8, Review additions V-1..V-8), 03_changes_data-signal.md (targets, runtime table, Fix round 1), 07_review.md (round 2 PASS)
Branch / commit: `phase/P24-documentation` @ `bb9c0913624238310b8b7f6d7b543c18e495b624` (`mas/state/scratch/p24_make/clone_head`)
Machine: Linux 7.0.0-38-generic, 16 CPU cores, NVIDIA GeForce RTX 3050 Laptop GPU, torch 2.14.1+cu130, CUDA available, `torch.get_num_threads()` = 12 (`mas/state/scratch/p24_make/torch_threads.txt`, V-1). Interpreter `.venv/bin/python` of the main tree.

A first launch (clone at 46c6441) was stopped by the orchestrator in p06 because the Makefile was wrong (07_review.md round 1 F1/F2); its clone and scratch folder were deleted. Everything below is the second, complete run on the fixed head. Nothing was run twice and no code was edited.

## Commands executed

Clean clone: `git clone --no-hardlinks <main tree> mas/state/scratch/clean_clone`, checkout of `phase/P24-documentation`, `git rev-parse HEAD` = bb9c0913624238310b8b7f6d7b543c18e495b624. The clone holds committed files only (before the run: no `data/`, `reports/`, `outputs/`, `baselines/`; no symlink to the main tree; empty `mas/state/scratch/make_stamps/`; free disk 36 GB before the launch, threshold 15 GB). The recordings were passed only through `RAW_DIR`; the verifier never read, listed or copied them.

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 1 | `bash mas/state/scratch/p24_make/run_all.sh`, which runs `make -C mas/state/scratch/clean_clone all PYTHON=<main>/.venv/bin/python RAW_DIR=<main raw folder> NN_DEVICES="cpu cuda"` under `nohup setsid`, `tee` to the log | 2026-10-29T08:14:06 | wall 08:14:06 to 17:41:42 = 9 h 27 min 36 s, including a laptop suspend inside p18 (below); sum of the 24 stamps 34055 s = 567.6 min | 0 (`mas/state/scratch/p24_make/DONE`: `DONE rc=0 2026-10-29T17:41:42`) | `mas/state/scratch/p24_make/make_all.log` (10024 lines) | `mas/state/scratch/clean_clone/{reports,data,outputs,baselines}/` |
| 2 | `make_stamps/p00.done ... p23.done` (written by `make all`) | | per phase below | 0 each | `mas/state/scratch/clean_clone/mas/state/scratch/make_stamps/` | |
| 3 | `.venv/bin/python mas/state/scratch/p24_make/compare.py` (read-only comparison, reports CSV/TXT) | 2026-10-29 | seconds | 0 | `compare_reports.csv` | |
| 4 | `.venv/bin/python mas/state/scratch/p24_make/hash_data.py` (sha256 of every `.npy`) | 2026-10-29 | minutes | 0 | `hash_data.txt` | |
| 5 | npz comparison (inline, output saved) | 2026-10-29 | seconds | 0 | `compare_npz.txt` | |
| 6 | `.venv/bin/python mas/state/scratch/p24_make/xcheck.py` and `xcheck2.py` (document-number cross-check) | 2026-10-29 | seconds | 0 | `xcheck_unmatched.txt`, `xcheck2_unmatched.txt` | |
| 7 | `.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider` inside the clone | 2026-10-29 | see 06_verify.md | see 06_verify.md | `pytest_clone.log`, `pytest_time.txt` | |

Exits inside command 1 (V-7). The `make` process ended with exit 0 and no recipe other than the p07 demo failed: `grep -n -i -E "\*\*\*|ignored|Traceback"` on the log gives one hit, `make[1]: [Makefile:153: p07] Error 1 (ignored)` (log line 1673; the `-` prefixed `--no-channel-drop` demo, exit 1 by design). `compare_v1_v2 --check-regression` (log line 6094) is not prefixed and did not stop `make`, so it exited 0. The two "QDA failed: LinAlgError" lines (log lines 686, 706) are caught and printed inside the p05 model comparison (`test_sklearn_models`); the run continued.

### Per-phase wall time from the stamps (V-8)

Stamps in `mas/state/scratch/clean_clone/mas/state/scratch/make_stamps/p*.done` (seconds). "Recorded" is the total-minutes column of the runtime table in `03_changes_data-signal.md` (sum of the recorded runs). p18 includes the laptop suspend (between the p17 stamp at 11:34 and the p18 stamp at 15:10; the orchestrator's log row 598e98e records it), so its 216.1 min is not a computing time.

| Phase | Stamp (s) | Stamp (min) | Recorded (min) |
|---|---|---|---|
| p00 | 0 | 0.0 | 0.0 |
| p01 | 1 | 0.0 | 0.0 |
| p02 | 5 | 0.1 | 0.1 |
| p03 | 42 | 0.7 | 0.3 |
| p04 | 274 | 4.6 | 9.1 |
| p05 | 60 | 1.0 | 1.2 |
| p06 | 790 | 13.2 | 12.8 |
| p07 | 9 | 0.1 | 0.2 |
| p08 | 58 | 1.0 | 1.0 (0.6 CPU + 0.4 CUDA) |
| p09 | 100 | 1.7 | 1.8 |
| p10 | 1348 | 22.5 | 24.9 |
| p11 | 1556 | 25.9 | 40.9 |
| p12 | 36 | 0.6 | 0.6 |
| p13 | 985 | 16.4 | 15.3 |
| p14 | 3780 | 63.0 | 67.5 |
| p15 | 439 | 7.3 | 5.5 |
| p16 | 2067 | 34.5 | 32.5 |
| p17 | 456 | 7.6 | 5.5 |
| p18 | 12967 | 216.1 (suspend inside) | 79.4 |
| p19 | 614 | 10.2 | 2.5 |
| p20 | 5009 | 83.5 | 81.0 |
| p21 | 2046 | 34.1 | 32.6 |
| p22 | 96 | 1.6 | 1.1 |
| p23 | 1317 | 21.9 | 20.5 |
| Sum | 34055 | 567.6 (9.46 h) | 436.1 (7.27 h) |

Arithmetic: `.venv/bin/python` over the stamp seconds printed `34055 567.58 9.4597`; start 08:14:06 to end 17:41:42 printed `9:27:36`. Without the 216.1 - 79.4 = 136.7 min excess of p18 the sum is 430.9 min (7.18 h).

## Human run requests

None. Everything ran locally under Sebastian's authorisation of 2026-10-29 (decisions.md).

## Produced files

Paths only, in the clone (`mas/state/scratch/clean_clone/`): `reports/` (769 files in total; CSV, `.meta.txt`, npz, txt), `data/{processed,processed_per_window,processed_continuous,processed_continuous_p17,processed_continuous_p19_raw,processed_continuous_p19_both,processed_p07_demo}/`, `outputs/` (136 files), `baselines/v1_2026-10-29/` (its own freeze, 303 files). Verifier files in `mas/state/scratch/p24_make/`: `run_all.sh`, `make_all.log`, `started`, `clone_head`, `torch_threads.txt`, `pid`, `DONE`, `nohup.out`, `clone_files.txt`, `main_files.txt`, `compare.py`, `compare_reports.csv`, `compare_npz.txt`, `hash_data.py`, `hash_data.txt`, `xcheck.py`, `xcheck2.py`, `xcheck_unmatched.txt`, `xcheck2_unmatched.txt`, `pytest_clone.log`, `pytest_time.txt`.

## Anomalies

1. p18 wall time inflated by a laptop suspend (above).
2. p07 second demo exits 1 by design and is ignored by `make` (V-7).
3. p16 freezes a new baseline tag in the clone (`baselines/v1_2026-10-29`) because the clone has no `baselines/`; V-6 says its byte content is not compared.
4. First launch stopped by the orchestrator in p06 (see top).
5. Differences found by the comparison are listed in 06_verify.md, not interpreted here.

## Questions

None.
