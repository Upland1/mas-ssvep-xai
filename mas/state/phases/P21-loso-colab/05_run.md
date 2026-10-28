# P21 · 05 · Run

Status: BLOCKED (cohort-5 runs done; full-cohort runs are a human-run request)
Author: verifier
Reads: 02_plan.md (Run commands, Measured, Budget, Pre-run audit additions B1-B11, P1-P5), 07_review.md (pre-run audit PASS, round 2, 8cfa30b)
Branch / commit: phase/P21-loso-colab @ e349656ad8cbc78c1e68dfe3212b2a3bc551dcc1 (clean detached worktree `mas/state/scratch/verify/P21`; `data/`, `reports/`, `outputs/`, `reference/`, `.venv` symlinked to the main tree, so outputs land in the main tree)
Machine: Linux 7.0.0-38-generic x86_64, Python 3.12.3, torch 2.14.1+cu130, CUDA available, GPU NVIDIA GeForce RTX 3050 Laptop (4096 MiB), CPU 12th Gen Intel Core i5-12500H. `torch.get_num_threads()` = 12 (first lines of `reports/logs/P21/pytest_full.log`). `DEVICE: auto`.

Data source: built continuous folders `data/processed_continuous/w1_s0.25/<S>/`, session OO, quality source both, banks fbcca fbcsp; cohort 5 (S01-S05). The raw folder holds no other subject (B2, below).

## Pre-run checks

- B1 pre-state: `ls reports | grep -E "loso|window_sweep_w1"` returned nothing before command 1 (no stale out-dir). `df -h .`: 17 GB free.
- B1 hash before command 1 (`reports/logs/P21/hash_before.txt`): `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4`, 65 files. Equals the pinned value.
- B1 hash after the last command (`reports/logs/P21/hash_after.txt`): `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4`, 65 files. Equal.

## Commands executed

All via `.venv/bin/python -m ...` from the worktree. Logs by `tee`/redirection inside the run command, in `reports/logs/P21/`. Start times local, 2026-10-28. `CUDA_VISIBLE_DEVICES=""` on every classical command (B9).

| # | Command (arguments as in 02_plan.md) | Start | Wall | Exit | Log |
|---|---|---|---|---|---|
| T | `pytest tests/ -q -o addopts=""`, alone | 15:24:00 | 783.33 s (0:13:03) | 0: `1360 passed, 22 warnings` | `pytest_full.log` |
| 0/B1 | sha256 of S01-S05 built folders | 15:37:21 | <1 s | 0 | `hash_before.txt` |
| 1 | `scripts.build_windows --filter-mode continuous --session OO --banks fbcca fbcsp --quality-source both --window-sec 1 --stride-sec 0.25 --resume` | 15:37:24 | 3.52 s | 0 | `build_windows_all.log` |
| 2 | `scripts.benchmarks.benchmark_loso ... --subjects S01 S02 S03 S04 S05 --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1_s01-s05` | 15:37:35 | 8.92 s (script 8 s) | 0 | `loso_cmd2.log` |
| B3 | compare `reports/loso_w1_s01-s05/summary.csv` with `mas/state/scratch/p21_loso_c5/summary.csv` | 15:37 | <1 s | 0: 21 rows, max abs diff of Acc = 0.0 | `b3_compare.txt` |
| B4 | same as 2 with `--channels all --out-dir reports/loso_w1_s01-s05_all` | ~15:37:50 | script 12 s | 0 | `loso_B4_all.log` |
| 3a (B7) | `timeout -s INT 300` + command 3 (`--methods ccnn compact eegnet --channels common --out-dir reports/loso_w1_s01-s05`) | 15:38:08 | 300 s | `timeout` 124 (KeyboardInterrupt traceback in the log) | `loso_cmd3a_interrupted.log` |
| 3b (B7) | command 3 rerun to completion | 15:43:16 | 773.66 s | 0 | `loso_cmd3b_resume.log` |
| 4 | rerun of command 2 (same out-dir) | 15:56:21 | 4.33 s | 0 | `loso_cmd4_rerun.log` |
| D1 | command 3 with `--methods ccnn eegnet --seed 43` / `--seed 44`, out-dirs `reports/loso_w1_s01-s05_seed43`, `..._seed44` | 15:56:33 | 412.21 s + 438.26 s | 0, 0 | `loso_D1_seed43.log`, `loso_D1_seed44.log` |
| 8/B1 | sha256 of S01-S05 built folders (after) | 16:10:49 | <1 s | 0 | `hash_after.txt` |

Local budget used: about 13.1 (suite) + 5.0 + 12.9 (networks) + 14.2 (D1) + <1 = about 46 min of `LOCAL_RUN_BUDGET_MIN` 120. GPU time (3a + 3b + D1) = 300 + 774 + 850 s = about 0.53 h of `MAX_GPU_HOURS_PER_PHASE` 2. D1 ran because more than 40 min of budget remained.

### B2 cohort gate (command 1, last lines quoted verbatim from `build_windows_all.log`)

```
[=] S01: already built with the same parameters (--resume)
[=] S02: already built with the same parameters (--resume)
[=] S03: already built with the same parameters (--resume)
[=] S04: already built with the same parameters (--resume)
[=] S05: already built with the same parameters (--resume)

Cohort: 5 subjects built (S01, S02, S03, S04, S05), 0 skipped (none); 0.0 s
```

N = 5, 0 skipped subjects. Per B2, commands 5, 6, B5 and 7 were **not run locally** and command 6 never ran on this 5-subject root. They are in the human-run request below.

### B6 channel and build record

Harness log lines (`loso_cmd2.log`):

```
[+] S01: 680 windows of 40 trials, fs 256 (meta), gate kept [PO3, POz, PO4, PO8, O1, Oz, O2], continuous build (w1_s0.25/S01), session OO
[+] S02: 644 windows of 39 trials, fs 256 (meta), gate kept [PO7, PO3, POz, PO4, PO8, O1, Oz, O2], continuous build (w1_s0.25/S02), session OO
[+] S03: 661 windows of 40 trials, fs 256 (meta), gate kept [PO3, POz, PO4, PO8, O1, Oz, O2], continuous build (w1_s0.25/S03), session OO
[+] S04: 665 windows of 40 trials, fs 256 (meta), gate kept [PO3, POz, PO4, PO8, O1, Oz, O2], continuous build (w1_s0.25/S04), session OO
[+] S05: 679 windows of 40 trials, fs 256 (meta), gate kept [PO7, PO3, POz, PO4, PO8, O1, Oz, O2], continuous build (w1_s0.25/S05), session OO
Channels (common): PO3, POz, PO4, PO8, O1, Oz, O2
```

`loso_B4_all.log`: `Channels (all): PO7, PO3, POz, PO4, PO8, O1, Oz, O2 (gate channel drops ignored)`.

`windows_meta.json` (read-only; `b6_meta.txt`): fs 256.0 and `quality.source` = `both` for S01-S05; `channels_dropped`: S01 [PO7], S02 [], S03 [PO7], S04 [PO7], S05 []. Subjects whose gate-kept list equals `common`: 3 (S01, S03, S04); equal to the full montage: 2 (S02, S05).

### B7 interrupt and resume

- After 3a (SIGINT at 300 s): `folds/` held 21 `.npz` = 15 classical (from commands 2) + 6 network folds (ccnn S01-S05, compact_eegnet S01); `*.tmp` files: 0.
- 3b printed exactly 6 `[skip]` lines (ccnn test-S01..S05, compact_eegnet test-S01), then computed compact_eegnet S02-S05 and eegnet S01-S05. Final `folds/` = 30 `.npz`, 0 `.tmp`.
- sha256 of `summary.csv`, `per_subject.csv`, `predictions.csv`, `confusion.csv` after 3b (`hash_after_cmd3.txt`) and after command 4 (`hash_after_cmd4.txt`): identical (`diff` printed IDENTICAL). summary: `16c97375...d5ce`, per_subject `cda19464...b412f1`, predictions `6793eec1...ae412b`, confusion `034d4f9d...f2b8`. Command 4 printed 15 `[skip]` and computed 0 folds.

## Human run requests

Why: B2 (N = 5) and the budget. Sebastian places S06-S40 in the raw-data folder; agents do not touch them. Everything below is run from a clean checkout of the phase branch (`phase/P21-loso-colab`), after the raw folders are present.

**HR-0. Order and gate.** Run command 1 first and read the last lines. The count `Cohort: N subjects built (...)` and every `[-] Skipping <S>: <reason>` line go into the report. If N is still 5, stop: nothing below applies.

Common prefix (local terminal), run from the repository root with the project venv:

```bash
P=".venv/bin/python -m"
find data/processed_continuous/w1_s0.25/S0[1-5] -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum   # must equal e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4
ls -d reports/loso_w1 reports/loso_w1_fbcca_all reports/window_sweep_w1_all reports/loso_w1_all 2>&1   # must all be absent
mkdir -p reports/logs/P21
# 1. build S06-S40 (S01-S05 skipped by --resume), about 1-5 min
$P scripts.build_windows --filter-mode continuous --session OO --banks fbcca fbcsp --quality-source both --window-sec 1 --stride-sec 0.25 --resume 2>&1 | tee reports/logs/P21/build_windows_human.log
```

**HR-1. Within reference, full cohort (command 5).** Expected runtime: not measured; the P20 five-subject 1 s fbcca + lda sweep was a fraction of its 121 s six-window run, so order of 10 min for 40 subjects (estimate).

```bash
$P scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 1 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep_w1_all 2>&1 | tee reports/logs/P21/window_sweep_w1_all.log
```

**HR-2. B5, full-cohort fbcca with all channels** (seconds to minutes):

```bash
CUDA_VISIBLE_DEVICES="" $P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods fbcca --channels all --out-dir reports/loso_w1_fbcca_all 2>&1 | tee reports/logs/P21/loso_w1_fbcca_all.log
```

The full classical `--channels all` run (about 35 min, `--out-dir reports/loso_w1_all`) is required only if fewer than 50 % of the full-cohort subjects have gate-kept channels equal to `common` (B6 count from the HR-0 log).

**HR-3. LOSO classical, full cohort (command 6), about 30-35 min, about 4.5 GB peak (builder projection from a 20-subject replica).** Per B9: stop with Ctrl-C after a fold line if the mean of the first 3 `lda` folds is above 60 s (projected about 22 s); folds resume.

```bash
CUDA_VISIBLE_DEVICES="" $P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1 2>&1 | tee reports/logs/P21/loso_w1_classical.log
```

**HR-4. LOSO networks, 40 subjects (command 7), about 19.6 h on an RTX 3050-class GPU** (builders' ms per training-window-epoch: 0.137 ccnn, 0.456 compact_eegnet, 0.247 eegnet; about 2.2 h + 12.5 h + 4.9 h; `02_plan.md` Measured). It is resumable: re-issue the same command after an interruption. Same out-dir as HR-3 (the harness rebuilds the summary from all folds).

Local terminal route (output to `reports/loso_w1/`):

```bash
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods ccnn --channels common --out-dir reports/loso_w1 2>&1 | tee -a reports/logs/P21/loso_w1_ccnn.log
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods eegnet --channels common --out-dir reports/loso_w1 2>&1 | tee -a reports/logs/P21/loso_w1_eegnet.log
$P scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods compact --channels common --out-dir reports/loso_w1 2>&1 | tee -a reports/logs/P21/loso_w1_compact.log
```

Colab route (`notebooks/loso_colab.ipynb`, committed without outputs):

1. The branch `phase/P21-loso-colab` must be pushed to `REPO_URL` by Sebastian (the agents do not push); the notebook clones `BRANCH` from that remote, and the repository must be public or the clone needs a token the notebook does not handle.
2. Upload the recordings to Drive, one folder per subject (S01/OO.* ... S40), e.g. `MyDrive/ssvep/raw/`.
3. Open the notebook in Colab, Runtime > Change runtime type > GPU (T4). Edit the settings cell (`RAW_DIR`, `DRIVE_DIR`, `REPO_URL`, `BRANCH`, `LOSO_OUT`) if the paths differ; the default `LOSO_OUT` is `reports/loso_w1_colab`.
4. Run the cells in order (GPU check, mount Drive, settings, clone, pip, symlinks, build `--resume`, within reference, LOSO classical, then the three network cells one at a time). After a disconnect run steps 1-6 again, then the interrupted cell. `compact_eegnet` (about 12.5 h on the local GPU; a T4 is of the same order, within about a factor of two) needs several sessions.
5. Run the last cell to release the runtime.

**B11 drop locations.** Return the whole `LOSO_OUT` folder (including `folds/`, `predictions.csv`, `confusion.csv`, `loso_config.json`, `summary.csv`, `per_subject.csv`, `folds.csv`) and `window_sweep_colab/`:
- Colab route: into `reports/loso_w1_colab/` and `reports/window_sweep_colab/`, never into a local out-dir. Their data source is "Colab build" (the session built its own windows from Drive).
- Local route: outputs stay in `reports/loso_w1/`, `reports/window_sweep_w1_all/`, `reports/loso_w1_fbcca_all/` with logs in `reports/logs/P21/`.

**Post-run checks the verifier will apply** (once the outputs are in place):
1. Hash of the S01-S05 built folders still equals `e7f55081...bab4`; the `Cohort: N` line and the skipped-subject list are quoted; N is the cohort of every table (never hardcoded).
2. B8: S01-S05 rows of `window_sweep_w1_all/summary.csv` equal the P20 1 s rows exactly (fbcca 58.68, 64.60, 91.07, 98.80, 95.43; lda 75.88, 77.36, 97.31, 99.79, 99.09, with Acc SD).
3. P1 on the full cohort: per-window `fbcca` identity (joined on subject, trial_id, offset_sec) with the within predictions for every matched subject (gate-kept list equal to `common`), 0 mismatches; unmatched subjects are compared to the `--channels all` fbcca run.
4. B10 for every out-dir: `config.train_subjects` excludes `test_subject`; `n_train` = sum of test windows - `n_windows_test`; the set of `git_head` values (more than one requires an empty `git diff --stat <h1> <h2> -- src scripts`); all folds have the same `config` (channels, window, stride, seed).
5. P2 (LOSO below within for `lda`, networks against a within-subject network run on the same channels), P3 (`lda_subjnorm` - `lda` mean >= 0 and at most 20 % of subjects below -2 pp), P4 (degenerate folds per network, `folds.csv`), P5 (S01-S05 `lda` rows against cohort 5 only if `common` is the same 7 channels).
6. P20 C-3: any single CNN cell that moves a cohort mean by more than 5 pp is repeated with at least 3 seeds before being interpreted (`--seed 43`, `--seed 44` in their own out-dirs).
7. Data source strings: "built continuous folders ... cohort N subjects" for local rows, "Colab build" for the Colab rows; per-subject rows kept.

## Produced files

- `reports/loso_w1_s01-s05/` (summary.csv, per_subject.csv, predictions.csv, confusion.csv, folds.csv, loso_config.json, folds/*.npz x30)
- `reports/loso_w1_s01-s05_all/` (same, classical only, 15 folds)
- `reports/loso_w1_s01-s05_seed43/`, `reports/loso_w1_s01-s05_seed44/` (ccnn, eegnet, 10 folds each)
- `reports/logs/P21/` (logs above, `hash_*.txt`, `b3_compare.txt`, `b6_meta.txt`, `p1_p2_calc.txt`, `p2p3p4_b10.txt`, `*.start`)
- `mas/state/scratch/p21_verify/p1p2p3.py`, `p2p3b10.py` (analysis scripts, scratch)

Not produced (human run): `reports/window_sweep_w1_all/`, `reports/loso_w1/`, `reports/loso_w1_fbcca_all/`, `reports/loso_w1_colab/`, `reports/window_sweep_colab/`.

## Anomalies

1. Cohort is 5, not 40: commands 5, 6, B5, 7 were not run (B2). P5 not evaluable.
2. The `timeout -s INT` interrupt (3a) ends with a Python `KeyboardInterrupt` traceback inside `fit_network` (exit 124). No partial fold or `.tmp` was left. Cosmetic only: the harness does not catch it.
3. compact_eegnet fold seconds vary 76-146 s for 2.6-2.7 k training windows; the plan's per-window-epoch cost (0.456 ms) is consistent with the 63-121 epochs run (`folds.csv`).
4. `folds.csv` was excluded from the hash comparison because of wall-clock `Seconds` (as in the plan).

## Questions

None.
