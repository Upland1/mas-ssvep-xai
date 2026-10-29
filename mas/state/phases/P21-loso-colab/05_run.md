# P21 · 05 · Run

Status: PARTIAL (cohort-5 and full-cohort classical runs done; full-cohort network run in progress)
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

---

# Full cohort — part 1 (appended 2026-10-28, verifier)

Authorisation: last P21 row of `mas/state/decisions.md` (Sebastian, local route, beyond `LOCAL_RUN_BUDGET_MIN` and `MAX_GPU_HOURS_PER_PHASE`). Run from the main tree on `phase/P21-loso-colab` @ f0fa3716a82cdd8dab7be5394bdc1435e19be67f (working tree clean; `git diff --stat e349656 HEAD -- src scripts tests` is empty, so the code equals the cohort-5 run). `.venv/bin/python -m scripts...`, classical commands with `CUDA_VISIBLE_DEVICES=""`. Disk 28 GB free before (the 17 GB of the first run is stale), 40 GB after; no abort.

Data source: built continuous folders `data/processed_continuous/w1_s0.25/<S>/`, session OO, quality source both, banks fbcca fbcsp; **cohort 39 subjects (S01-S040 without S020)**, every row below. The cohort-5 results above are a separate data source.

## HR-0

- Pre-state: `reports/loso_w1`, `reports/loso_w1_fbcca_all`, `reports/window_sweep_w1_all`, `reports/loso_w1_all` absent (`ls` error for each). Hash of S01-S05 before: `e7f55081705d9a0e9a528b93885925dd8cbfe354f44406c04fedc88e14bebab4`, equal to the pin.
- Command 1 (`build_windows ... --resume`, exit 0, 1 s, `reports/logs/P21/build_windows_human.log`). **Disclosure:** all folders S06-S040 already existed when I ran it (directory mtimes 2026-10-28 18:47-18:48, built before my session by a command I did not run; this command only printed `[=] ... already built with the same parameters (--resume)` for 39 subjects, so the build parameters equal the S01-S05 ones; I did not rebuild).
- Quoted verbatim (last lines of the log):
```
[-] Skipping S020: all channels dropped (source=both)
Cohort: 39 subjects built (S01, S02, S03, S04, S05, S06, S07, S08, S09, S010, S011, S012, S013, S014, S015, S016, S017, S018, S019, S021, S022, S023, S024, S025, S026, S027, S028, S029, S030, S031, S032, S033, S034, S035, S036, S037, S038, S039, S040), 1 skipped (S020); 0.2 s
```
  N = 39 (not 5), so the gate opens. Skipped: S020 only, reason "all channels dropped (source=both)". Folder names are `S01..S09` and `S010..S040` (no `S10`; the harness refuses duplicate numbers and none occur).

## Commands executed

| # | Command | Start | Wall | Exit | Log / out-dir |
|---|---|---|---|---|---|
| HR-0 | `build_windows ... --resume` | 19:00:54 | 1 s | 0 | `build_windows_human.log` |
| HR-1 | `benchmark_window_sweep --windows 1 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep_w1_all` | 19:01:05 | 188 s (script runtime 187 s; fbcca 17.6 s, lda 168.0 s per subject x window x method summed over the cohort) | 0 | `window_sweep_w1_all.log`, `reports/window_sweep_w1_all/` |
| HR-2 | `benchmark_loso ... --methods fbcca --channels all --out-dir reports/loso_w1_fbcca_all` | 19:04:17 | 15 s | 0 | `loso_w1_fbcca_all.log` |
| HR-3 | `benchmark_loso ... --methods fbcca lda lda_subjnorm --channels common --out-dir reports/loso_w1` | 19:04:38 | 589 s (script runtime) | log ends with `Saved:`; the exit code was not captured (job sent to the background by the tool; log complete, 117 folds) | `loso_w1_classical.log` |
| B5-full | same, `--channels all --out-dir reports/loso_w1_all` | 19:16:34 | 1221 s (script runtime) | 0 | `loso_w1_all.log` |
| Checks | `mas/state/scratch/p21_verify/full1.py` | 19:38 | seconds | 0 | `full_part1_checks.txt` |
| Hash after | S01-S05 sha256 | 19:40 | <1 s | 0 | `hash_after_full1.txt` = `e7f55081...bebab4`, equal |

An aborted attempt to start B5-full (a stray `pkill` in my own wait loop killed my shell, exit 144) wrote nothing: `reports/loso_w1_all` was absent before the real run. No other command was repeated.

CPU time of part 1: about 36 min (188 + 15 + 589 + 1221 s + build); disk and GPU not used (GPU idle until HR-4).

## B6 channel record

`Channels (common)`: **POz, PO4, O1** (3 channels; the intersection over 39 subjects). `Channels (all)`: PO7, PO3, POz, PO4, PO8, O1, Oz, O2. Gate-kept lists (every `[+] <S>: ... gate kept [...]` line is in `loso_w1_fbcca_all.log` / `loso_w1_classical.log`): gate-kept == `common`: **0 of 39**; == full montage: **32 of 39** (82.1 %). Others: S01, S03, S04 lose PO7; S013 loses PO8; S019 loses PO3 and PO8; S029 loses O2; S040 loses Oz. All 39 subjects have fs 256 (log `fs 256 (meta)`). Because 0 of 39 equal `common` (< 50 %), B5 requires the full classical `--channels all` run: done (`loso_w1_all`). `windows_meta.json` read-only for all 39 built subjects (`reports/logs/P21/b6_meta_full.txt`): fs 256.0 and `quality.source` = `both` in 39 of 39. The 5-subject `common` of the first report was 7 channels; with the full cohort `common` is 3 channels, so every cohort-39 `common` row is a 3-channel result.

## Results (Acc % at 1 s, LOSO; within = P20-style sweep run on the same built folders)

Per-subject table, from `full_part1_checks.txt` (source: `reports/window_sweep_w1_all/summary.csv`, `reports/loso_w1/summary.csv`, `reports/loso_w1_all/summary.csv`). `kept` = channels kept by the gate (within used these), `common` = 3 channels, `all` = 8.

| Subj | kept | within fbcca | within lda | common fbcca | common lda | common subjn | all fbcca | all lda | all subjn |
|---|---|---|---|---|---|---|---|---|---|
| S01 | 7 | 58.68 | 75.88 | 43.24 | 47.65 | 48.38 | 55.88 | 64.56 | 75.00 |
| S02 | 8 | 64.60 | 77.36 | 47.20 | 61.02 | 66.46 | 64.60 | 81.06 | 81.99 |
| S03 | 7 | 91.07 | 97.31 | 80.94 | 89.11 | 89.71 | 90.77 | 95.16 | 95.01 |
| S04 | 7 | 98.80 | 99.79 | 97.14 | 99.10 | 99.40 | 99.10 | 99.55 | 99.70 |
| S05 | 8 | 95.43 | 99.09 | 93.23 | 98.82 | 99.26 | 95.43 | 99.26 | 99.12 |
| S06 | 8 | 77.50 | 95.44 | 64.26 | 77.79 | 84.26 | 77.50 | 92.35 | 95.00 |
| S07 | 8 | 72.21 | 81.53 | 58.53 | 72.06 | 71.91 | 72.21 | 84.26 | 85.00 |
| S08 | 8 | 95.32 | 99.82 | 64.80 | 78.55 | 82.33 | 95.32 | 98.94 | 99.85 |
| S09 | 8 | 50.36 | 81.07 | 38.20 | 53.28 | 65.21 | 50.36 | 82.73 | 89.29 |
| S010 | 8 | 76.04 | 88.72 | 64.39 | 70.72 | 70.38 | 76.04 | 87.85 | 89.18 |
| S011 | 8 | 85.01 | 92.58 | 67.08 | 74.81 | 80.53 | 85.01 | 91.81 | 95.05 |
| S012 | 8 | 71.18 | 77.06 | 50.74 | 48.38 | 53.09 | 71.18 | 75.59 | 81.03 |
| S013 | 7 | 89.46 | 96.79 | 70.40 | 80.10 | 83.44 | 88.63 | 90.47 | 94.65 |
| S014 | 8 | 95.13 | 96.95 | 79.87 | 92.21 | 90.26 | 95.13 | 98.70 | 98.38 |
| S015 | 8 | 51.15 | 47.46 | 54.17 | 56.13 | 59.86 | 51.15 | 52.40 | 54.71 |
| S016 | 8 | 99.26 | 99.71 | 93.82 | 96.18 | 96.76 | 99.26 | 99.26 | 99.71 |
| S017 | 8 | 71.18 | 87.03 | 69.13 | 61.23 | 72.38 | 71.18 | 69.30 | 84.73 |
| S018 | 8 | 63.71 | 67.41 | 46.50 | 49.34 | 54.63 | 63.71 | 68.24 | 73.35 |
| S019 | 6 | 53.53 | 54.71 | 58.53 | 60.59 | 61.18 | 51.91 | 51.18 | 60.88 |
| S021 | 8 | 80.74 | 94.35 | 79.12 | 87.65 | 89.56 | 80.74 | 88.97 | 94.56 |
| S022 | 8 | 94.97 | 98.61 | 86.24 | 95.71 | 94.08 | 94.97 | 98.37 | 98.08 |
| S023 | 8 | 83.53 | 91.21 | 78.09 | 85.59 | 85.00 | 83.53 | 91.32 | 93.24 |
| S024 | 8 | 83.44 | 92.64 | 55.21 | 66.05 | 66.67 | 83.44 | 91.82 | 91.62 |
| S025 | 8 | 39.71 | 72.68 | 32.06 | 36.62 | 50.74 | 39.71 | 63.38 | 73.24 |
| S026 | 8 | 72.06 | 94.47 | 68.38 | 82.79 | 86.47 | 72.06 | 88.97 | 92.79 |
| S027 | 8 | 98.52 | 99.94 | 94.98 | 99.70 | 99.26 | 98.52 | 100.00 | 99.85 |
| S028 | 8 | 89.06 | 93.10 | 49.63 | 65.97 | 67.92 | 89.06 | 95.65 | 95.35 |
| S029 | 7 | 51.91 | 65.13 | 50.48 | 58.28 | 63.54 | 51.91 | 67.20 | 73.57 |
| S030 | 8 | 92.61 | 98.85 | 75.26 | 88.39 | 86.58 | 92.61 | 99.10 | 98.64 |
| S031 | 8 | 86.91 | 88.85 | 67.79 | 71.32 | 73.82 | 86.91 | 90.74 | 92.50 |
| S032 | 8 | 87.46 | 97.46 | 68.58 | 87.76 | 89.53 | 87.46 | 96.90 | 98.08 |
| S033 | 8 | 78.49 | 93.09 | 66.62 | 78.34 | 78.49 | 78.49 | 92.73 | 93.77 |
| S034 | 8 | 72.76 | 78.14 | 60.99 | 73.84 | 73.53 | 72.76 | 82.82 | 82.51 |
| S035 | 8 | 61.17 | 71.93 | 59.48 | 70.42 | 69.65 | 61.17 | 75.65 | 76.27 |
| S036 | 8 | 91.47 | 98.24 | 54.26 | 61.18 | 70.15 | 91.47 | 96.62 | 96.76 |
| S037 | 8 | 80.24 | 90.35 | 85.10 | 91.15 | 91.45 | 80.24 | 88.20 | 87.76 |
| S038 | 8 | 81.91 | 91.47 | 71.47 | 83.97 | 83.68 | 81.91 | 93.09 | 93.38 |
| S039 | 8 | 24.92 | 31.69 | 19.60 | 18.27 | 23.26 | 24.92 | 25.25 | 22.26 |
| S040 | 7 | 50.00 | 47.56 | 52.35 | 58.97 | 58.53 | 49.85 | 43.82 | 53.38 |
| Mean | | 75.94 | 84.76 | 64.56 | 72.54 | 75.16 | 75.80 | 83.42 | 86.13 |
| SD | | 18.15 | 16.83 | 17.59 | 18.60 | 16.64 | 18.27 | 17.64 | 16.16 |

Harness `Mean` rows (`summary.csv`), 2-tap smoothed (R8, within trial) mean: common fbcca 65.52, lda 74.12, lda_subjnorm 77.27; all fbcca 76.57, lda 84.47, lda_subjnorm 87.34. `lda_subjnorm` is unsupervised per-subject (test-time, whole-session, offline upper-bound) normalization (PF-35). Within `fbcca` was evaluated once (Acc SD 0); within `lda` Acc SD is in `window_sweep_w1_all/summary.csv` (mean 0.87). R9: 1.0 s per subject; the 2.0 s smoothed value is the P20 sweep's (not repeated here).

Fold seconds (`folds.csv`): `loso_w1` lda mean 6.7 s (first 3 folds 6.1, 6.0, 7.0 s: B9 stop rule not triggered, limit 60 s), lda_subjnorm 8.1 s, fbcca <0.1 s; `loso_w1_all` lda 14.9 s, lda_subjnorm 15.8 s. Builder projection was 22 s.

## Post-run checks (classical parts)

1. Hash of S01-S05 built folders after part 1: `e7f55081...bebab4`, equal. `Cohort: 39` and the single skip quoted above; every table says "cohort 39 subjects (S01-S040)" in its Data source column (`summary.csv` last column).
2. **B8 passes:** `window_sweep_w1_all` S01-S05 vs P20 `window_sweep/summary.csv`: fbcca 58.68, 64.60, 91.07, 98.80, 95.43 (SD 0.0) and lda 75.88/0.61, 77.36/0.92, 97.31/0.29, 99.79/0.08, 99.09/0.22: 10/10 equal (Acc and Acc SD).
3. **P1 holds:** matched = gate-kept equal to the full montage = 32 subjects. `loso_w1_fbcca_all` and `loso_w1_all` fbcca predictions joined with `window_sweep_w1_all` fbcca predictions on (subject, trial_id, offset_sec): row counts equal for every subject, **0 prediction mismatches, 0 label mismatches** in both out-dirs (e.g. S02 644/644, S05 679/679, S039 301/301). The `loso_w1_all` and `loso_w1_fbcca_all` fbcca accuracies are equal for every subject. Negative control, the 7 unmatched subjects against the same within predictions: 238 mismatches in 6 of them (S01 59, S03 14, S04 2, S013 15, S019 94, S040 54; S029 0), so the test discriminates. No subject is matched for `common` (0 of 39, the 3-channel set), so `loso_w1` fbcca is not an identity case (5643 mismatches, informational).
4. **B10 (classical):** `loso_w1` 117 classical folds, `loso_w1_all` 117, `loso_w1_fbcca_all` 39: `test_subject` not in `train_subjects` in every fold (38 train subjects each); `n_train` = sum of test windows - `n_windows_test` is True for fbcca, lda, lda_subjnorm in all three; `git_head` set = {f0fa3716a82cdd8dab7be5394bdc1435e19be67f} in each; one distinct fold config (channels, mode, classes, cohort, fs, window, stride) per out-dir. The networks' B10 is re-applied when HR-4 completes (the 2 ccnn folds present at check time are a partial set, so the sum test is not yet meaningful for ccnn).
5. P2 (`lda`, matched = the 32 full-montage subjects, `--channels all`): mean LOSO 85.67 < within 86.51 (the mean condition holds), but LOSO <= within + 1 pp in only 22 of 32 subjects (68.8 % < 80 %): **direction not observed** by the pre-registered rule. No matched subject exceeds within + 5 pp (largest S015 +4.94, S034 +4.68, S02 +3.70, S035 +3.72), so the B10 "unexplained" trigger does not fire. The 10 subjects above within + 1 pp are S02, S07, S09, S014, S015, S028, S031, S034, S035, S038 (deltas in `full_part1_checks.txt`); the largest negatives are S017 -17.73, S025 -9.30, S039 -6.44, S026 -5.50, S021 -5.38. Unmatched `common` 3-channel LOSO `lda` is below within on average (mean difference -12.22; LOSO above within + 5 pp in S015 +8.67, S019 +5.88, S040 +11.41, three subjects whose within run is near chance); this is informational because the channel sets differ. Per the consequence rule this is reported, not explained, and nothing is changed. `lda_subjnorm` on matched subjects is above within lda in 21 of 32 subjects (mean +1.21 pp), reported only (transductive).
6. **P3 holds in both runs:** `common`: mean delta (subjnorm - lda) +2.62 pp, 0 of 39 subjects below -2 pp, 28 subjects with delta > 0. `all`: mean +2.72 pp, 1 of 39 below -2 pp (S039 -2.99; 2.6 %), 28 > 0.
7. P5: not made. `common` is 3 channels (POz, PO4, O1), not the 7 channels of cohort 5, so the S01-S05 comparison with the cohort-5 `lda` is not evaluable (rule in 02_plan.md).

## HR-4 started (part 2)

Runner `mas/state/scratch/p21_hr4/run_hr4.sh` (ccnn, then eegnet, then compact, `--channels common`, `--out-dir reports/loso_w1`, `tee -a reports/logs/P21/loso_w1_<net>.log`, exit codes appended to `mas/state/scratch/p21_hr4/exitcodes`, `DONE` or `FAILED` written at the end). Launched at 19:37 with `nohup setsid bash run_hr4.sh`; real PID 3604944 (pid file corrected after a first wrong value). First folds (`reports/logs/P21/loso_w1_ccnn.log`): `[+] ccnn test-S01: acc 45.88% on 680 windows, train 77.64%, 86.8 s`, `[+] ccnn test-S02: acc 57.45% on 644 windows, train 75.93%, 69.5 s`. Status of the networks: running; the verdict stays partial until DONE and the network checks (P2 networks, P4, B10 networks, C-3 seeds, post-run 6) are applied.
