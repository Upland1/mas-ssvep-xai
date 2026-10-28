# P20 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, 03_changes_deep-learning.md, mas/RULES.md
Branch: phase/P20-detection-online
Commit(s): ab72a51 (feat: sweep, vectorized FBCCA), 397fac1 (fix: C-b, C-c), 4d5c681 (test), 54c6fc3 (docs)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `scripts/benchmarks/benchmark_window_sweep.py` | NEW | window sweep CLI: methods `fbcca`, `lda`, `cnn (compact_eegnet)`; trial-grouped CV; `summary.csv`, `predictions.csv`, `confusion.csv`, `timing.csv`, `sweep_config.json`; method-split merge | P20.2 | R1, R2, R8, R9, PF-31, [own] |
| `src/features/ssvep/fbcca_extraction.py` | MODIFIED | added `reference_bases` (QR-orthonormal mean-centred sin/cos, `(K, T, 2H)`) and `fbcca_scores_vectorized` (batched QR + SVD, top singular value of `Qx^T Qy` clipped to [0,1], weighted squared sum); legacy functions untouched | P20.2 | [own] (CCA via QR/SVD, Bjorck-Golub equivalence) |
| `scripts/benchmarks/feature_based/benchmark_n_subjects.py` | MODIFIED | P17 C-b: `evaluate_subject(fail_fraction=None)` raises ValueError when not passed (the unused `CHANNEL_FAIL_FRACTION` import removed); P17 C-c: with `--classes 6` a console line `Data source (6 classes): ...` | carry-forwards | R5, decisions P17 |
| `tests/test_p20_window_sweep.py` | NEW | 14 tests (below) | plan tests 1-3, C-b | [own] |
| `tests/test_p16_flagship_port.py`, `tests/test_p16_independent_known_answer.py`, `tests/test_p17_benchmark.py`, `tests/test_p17_independent_known_answer.py`, `tests/test_p17_leak_controls.py` | MODIFIED | existing `evaluate_subject(...)` calls now pass `fail_fraction=0.5` (the old default value) because of C-b; nothing else changed | C-b | |

The new script reaches splitters only through `cv_utils.make_splits` (registered, `tests/test_no_leakage.py`); the CNN fold is `src.models.cnn.training.cnn_fold` (deep-learning).

## Legacy behaviour implemented

None.

## Differences from the cited examples

No external example. Existing legacy `canonical_correlation` (sklearn `CCA`, NIPALS) is not used by the sweep; the vectorized version computes the same first canonical correlation by orthonormalising both sides and taking the top singular value (equal to 1e-10 against an independent covariance-eigenvalue reference, test 1).

## Deviations from the plan

- Reference bases: QR of the mean-centred references per target (K = 5), as in the roadmap; data side: batched QR, with an SVD fallback only for rank-deficient window/band pairs (flat band or duplicated channel; zero-variance directions are dropped, so r = 0 for a flat band, not NaN).
- `lda`'s model is the flagship `Pipeline(StandardScaler, Shrinkage-LDA lsqr auto)` with `FeatureSpace(..., fbcsp_m=1)` features (CSP block first, then the 5 FBCCA scores; 55 columns for 5 bands), the same `fold_matrices` the benchmark uses.
- Method labels in every table: `fbcca`, `lda`, `cnn (compact_eegnet)` (CLI names `fbcca`, `lda`, `cnn`). data-signal's dynamic stopping should match `method != "fbcca"` or the exact labels `lda` / `cnn (compact_eegnet)`.
- CNN seeds follow `benchmark_nn_sweep`: splits `StratifiedGroupKFold(5, shuffle, seed + r)`, fold seed `seed + r + k`, so `cnn (compact_eegnet)` at 1 s reproduces the NN sweep's `compact_eegnet` (same data, same folds, same seeds).
- FBCCA has no CV: evaluated once on every window (Runs 1, SD 0, Train Acc empty, `p_*` empty); its predictions rows still carry `run 0`, trial id, offset.
- Extra outputs beyond the plan: `timing.csv`, `sweep_config.json`; extra summary column `Data source` (R9).
- `--max-folds k` (smoke) applies to every method.

## How to run / reproduce

Command 2 as in the plan works unchanged:

```bash
.venv/bin/python -m scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous \
  --windows 0.5 1 1.5 2 3 4 --stride 0.25 --methods fbcca lda cnn --cv-repeats 5 --cnn-repeats 1 --out-dir reports/window_sweep
```

Options: `--subjects`, `--no-augment` (cnn), `--max-epochs 150`, `--patience 25`, `--device auto|cpu|cuda`, `--seed 42`, `--max-folds k` (smoke), `--overwrite`, `--config`.

**Method split (recommended for the budget).** Run the two parts into the same `--out-dir`, in any order, on any machine:

```bash
# 2a. local, about 2-3 min of compute on S01-S05 (measured below)
.venv/bin/python -m scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous \
  --windows 0.5 1 1.5 2 3 4 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep
# 2b. CNN part (about 80-120 min on the RTX 3050 per deep-learning's estimate); human run if over budget
.venv/bin/python -m scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous \
  --windows 0.5 1 1.5 2 3 4 --stride 0.25 --methods cnn --cnn-repeats 1 --out-dir reports/window_sweep
```

Merge rule: each run replaces only the rows of its own (method, window, subject) cells in `summary.csv`, `predictions.csv`, `timing.csv`, then sorts all rows canonically (method order fbcca, lda, cnn, then window, subject, run, trial_id, offset_sec); `confusion.csv` (pooled over subjects and runs) is recomputed from the merged `predictions.csv`, so partial reruns cannot double count. The combined `summary/predictions/confusion/sweep_config` files are byte-identical for a, b order and for one single run (test). `sweep_config.json` stores per method its settings plus the shared ones (stride, seed, classes 5, quality shared); a run whose shared settings differ from those stored for another method exits with an error unless `--overwrite`. For the human run of 2b, drop the folder `reports/window_sweep/` produced locally on the CNN machine's checkout (or copy the two CNN-run files over) and rerun 2b there: it merges into whatever is present. `timing.csv` is the only non-deterministic file (seconds).

Outputs: `summary.csv` (Subject, Window (s), Method, Windows, Trials, Acc (%), Acc SD, BalAcc (%), ITR (bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch, Data source), `predictions.csv` (subject, window_sec, method, run, trial_id, offset_sec, true, pred, p_101 .. p_105), `confusion.csv` (window_sec, method, true, pred, count), `timing.csv`, `sweep_config.json`.

## Decisions

1. FBCCA features come from the saved continuous `fbcca` bank (3 Chebyshev sub-bands, R3), computed once per subject and window (label-free, no fitting) and reused by `lda` folds.
2. In-fold (R2): CSP (per band, m = 1), scaler and LDA are fitted on the training rows of each fold; the test says replacing the test windows by noise changes neither the fitted filters nor the training accuracy, and that the CSP receives exactly the training rows.
3. R1 runtime guard `assert_no_shared_trials` on every fold, groups = `cv_groups` (true trial ids).
4. ITR: Wolpaw, N = 5, T = window + 0.5 s, accuracy pooled over runs; identical to the NN sweep's helper (test compares 18 accuracy/time pairs for equality).
5. C-b: the loader call in `evaluate_subject` already received `fail_fraction`; the default is removed, callers in the repo (`main`) already pass it.

## How I verified

`tests/test_p20_window_sweep.py` (14 tests, `.venv/bin/python -m pytest tests/test_p20_window_sweep.py -q -o addopts=""`: `14 passed in 5.74s`):
1. vectorized FBCCA equals an independent loop reference (covariance-eigenvalue canonical correlation per window, band, target) to 1e-10 (chunking 3 on 7 windows); bases `Q^T Q = I`, mean-centred; with one band and weight 1 the score lies in [0,1] and equals 1 for a window inside the reference span; planted sinusoids at each of the 5 stimulus frequencies are classified correctly at 0.5, 1, 2 s; a flat band gives finite scores (r = 0) and a duplicated channel (rank deficient) equals the score without the duplicate.
2. ITR known values (P = 1, T = 1.5 s: log2(5)*60/1.5; P <= 0.2 gives 0; P = 0.5 hand formula) and equality with `benchmark_nn_sweep.itr_bits_per_min` and `folder_name`.
3. no trial id (and no row) shared between train and test of any fold or repeat on overlapping windows (15 folds); the historical window-level `StratifiedKFold` on the same windows shares trials in all 5 folds (the check fails on that bug).
4. `lda_fold` in-fold (spy on `FBCSPTransformer.fit`, noise-replaced test windows); `lda` learns a planted per-class variance signal (> 60 %); FBCCA cell has empty `p_*`, Runs 1, SD 0, no train accuracy.
5. CLI on a synthetic built folder: `fbcca lda` then `cnn`, `cnn` then `lda fbcca`, and all three in one run produce byte-identical summary/predictions/confusion/sweep_config; method labels and column order; confusion counts per method equal prediction rows; a rerun with a different seed is refused and passes with `--overwrite`.
6. C-b: `evaluate_subject` without `fail_fraction` raises ValueError. C-c checked by a console smoke on `data/processed_continuous_p17` S04 (`--classes 6`, output in `mas/state/scratch/p20_ml/rep`, deleted): the `Data source (6 classes): ...` line prints once after the first Data source line.

Real-data smoke (existing 1 s, stride-1 build `data/processed_continuous` through a scratch symlink named `w1_s0.25`; this is NOT a sweep result, only a smoke; output in scratch, deleted): `fbcca lda`, S01-S05, 5 repeats, 5 s wall. Subjects load with 7 or 8 channels; e.g. S01 fbcca 58.50 %, lda 72.80 % (SD 1.20); S04 fbcca 95.90 %, lda 99.49 % (windows 195-200 per subject, no overlap in that build).

Suite (`.venv/bin/python -m pytest tests/ -q -o addopts=""`, log `mas/state/scratch/suite_p20_ml.log`):
`1263 passed, 22 warnings in 802.25s (0:13:22)`

## Measured runtimes (this machine, CPU, one process)

Real-data smoke, 1 s stride-1 build (about 200 windows per subject): per subject 0.1 s load + FBCCA, `lda` 5 repeats x 5 folds 0.8-1.0 s.

Sweep shape (stride 0.25, 40 trials of 5 s per subject, 7 channels, fs 256; random data of the exact array shapes through `run_cell`, script outside the repo `mas/state/scratch/p20_ml/timing.py`; seconds per subject; `lda` = 5 repeats x 5 folds):

| Window (s) | windows | FBCCA features (s) | lda (s) |
|---|---|---|---|
| 0.5 | 760 | 0.11 | 1.7 |
| 1 | 680 | 0.23 | 3.5 |
| 1.5 | 600 | 0.28 | 4.1 |
| 2 | 520 | 0.33 | 5.2 |
| 3 | 360 | 0.33 | 5.3 |
| 4 | 200 | 0.25 | 4.0 |
| sum over 6 windows | | 1.5 | 23.8 |

So command 2a for 5 subjects is about 5 x 25 s = 2 min plus reading the arrays (a few seconds per folder); the CNN part (2b) is deep-learning's 80-120 min estimate for `compact_eegnet`. The real run writes the measured per-cell seconds to `reports/window_sweep/timing.csv` and prints a per-window table.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->

## Build fix

`benchmark_window_sweep.py` wrote `offset_sec` from `load_subject(...)["offsets"]`, which are in samples (`window_offsets.npy`), not seconds. Fixed: `offset_sec = offsets / d["fs"]`. The earlier fixture used seconds and hid it; `fake_subject` now uses sample offsets (multiples of 64 at fs 256) and the new test `test_offset_sec_is_in_seconds_while_loader_offsets_are_samples` checks a real built-style folder (`offset_sec == offsets / fs`) and that the fake subject gives {0, 0.25, ..., 1.75} s (fails on the old line). Window-sweep tests: `15 passed`. Suite (log `mas/state/scratch/suite_p20_ml_fix.log`):
`1275 passed, 22 warnings in 804.48s (0:13:24)`
Note: `scripts/benchmarks/neural_networks/benchmark_nn_sweep.py` (deep-learning) writes `"offset_sec": offs[ok]` from the same samples array (line 132) and has the same defect; not touched.
