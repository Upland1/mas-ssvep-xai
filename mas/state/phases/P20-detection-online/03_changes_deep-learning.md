# P20 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md
Branch: phase/P20-detection-online
Commit(s): 54bc298 (feat: CCNN, fit_network/cnn_fold, NN sweep, tests), a30a9de (test: enough trials per class), 6893adc (test: leakage-guard registry)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/models/cnn/ccnn.py` | NEW | `CCNN(n_classes, n_channels, n_samples, fs=256, f_min=3, f_max=50, resolution_hz=0.25, n_filters=2C, spectral_kernel=10, dropout=0.25)`; zero-padded rFFT (nfft = max(T, round(fs/res))), bins in [3, 50] Hz, `[real, imag]/T` -> spatial Conv2d (C,1) + BN + ReLU + Dropout -> spectral Conv2d (1,10) + BN + ReLU + Dropout -> Linear; convs bias-free (B004) | P20.3 | roadmap spec, [own] |
| `src/models/cnn/training.py` | NEW | `fit_network`, `cnn_fold`, `model_factory`, normalisation and predict helpers | P20.4, settled 7, 11 | PF-32, R2, PF-31, [own] |
| `scripts/benchmarks/neural_networks/benchmark_nn_sweep.py` | NEW | NN sweep CLI (reads built folders through `load_subject`) | P20.4 | 02_REQUIREMENTS §6 |
| `tests/test_p20_networks.py` | NEW | 18 tests (CCNN, fit_network, cnn_fold, ITR, CLI on a synthetic built folder) | tests 4, 5 | [own] |
| `tests/test_no_leakage.py` | MODIFIED | one registry line: `src/models/cnn/training.py` = `leak-free` (the guard `test_every_splitter_in_the_repo_is_registered` failed on the new inner `StratifiedGroupKFold` import) | R1 | [own] |

Reused: `EEGNetSSVEP` (`src/models/cnn/eegnet.py`, unchanged), `SSVEPAugmentedDataset` (P10, `src/preprocessing/dataset/augmentation.py`), `make_splits`/`assert_no_shared_trials` (`cv_utils`), `label_maps`/`resolve_device`, `load_subject`, `quality_params_from_config`.

## API (final; ml-engineer imports this)

```python
from src.models.cnn.training import cnn_fold, fit_network, model_factory, MODELS  # MODELS = ("ccnn","compact_eegnet","eegnet")

cnn_fold(X_tr, y_tr, groups_tr, X_te, fs, n_classes, model="compact_eegnet", seed=42, device="cpu", augment=True,
         **fit_kwargs)  # fit_kwargs: val_frac=0.2, max_epochs=150, patience=25, batch_size=16, lr=1e-3, weight_decay=0.01, label_smoothing=0.1
  -> dict(proba (n_te, n_classes) float64 softmax, train_acc, val_acc, best_epoch (1-based),
          n_params, epochs_run, val_loss)        # the 4 required keys plus 3 extras

fit_network(X, y, groups, build_model, seed=42, device="cpu", augment=True, val_frac=0.2, max_epochs=150, patience=25, ...)
  -> dict(model (best-val-loss state restored, eval), mean, std, fit_idx, val_idx, train_acc, val_acc, val_loss,
          best_epoch, epochs_run, n_params, history)
```

- `X_*` are the raw (continuous-filtered) windows `(n, C, T)` of the subject's kept channels, in µV; `fs` = `load_subject(...)["fs"]`. Do NOT z-score first: normalisation is done inside (per-channel mean/std of the fitting windows only).
- `y_tr` must be class **indices 0..n_classes-1** (ValueError otherwise); map codes with `label_maps(y)`; the columns of `proba` follow that order. `groups_tr` = the true trial ids (use `cv_groups`) of the training windows. Test windows never enter `fit_network`.
- `model` accepts `ccnn`, `compact_eegnet`, `eegnet`; aliases `compact` and `cnn` -> `compact_eegnet`. The sweep `cnn` label is `cnn (compact_eegnet)` (PF-31) — the label is the caller's job.
- `device` is a string `"cpu"`/`"cuda"` (no `auto` inside; `resolve_device(...).type` outside). Seed: `torch.manual_seed(seed)` before the model; the sweep passes `seed = 42 + r + fold` (as `benchmark_nn_sweep` does).

## Decisions (not fixed by the plan)

1. **Normalisation**: per-channel mean/std over windows and time of the fitting windows (training minus validation); this keeps the amplitude information CCNN needs (a per-window z-score would erase it). Plan point 7 says training windows only; this implements that literally.
2. **Validation loss** for model selection = plain cross-entropy (no label smoothing); training loss uses smoothing 0.1.
3. **`train_acc`** = eval mode, un-augmented fitting windows (training minus the validation windows), PF-30. `val_acc` and `best_epoch` are of the restored state.
4. **Max-norm** of `EEGNetSSVEP` applied after each step (existing convention). `eegnet` = `F1=8, D=2, F2=16, kernel=fs//2, dropout=0.25`; `compact_eegnet` = `F1=96, D=1, F2=96, kernel=fs//2, dropout=0.5` (kernel 128 at fs 256). Parameter counts (tested): compact_eegnet 28,229 at 8 channels / 1 s (matches PF-31), 28,133 at 7; eegnet 2,389 (8) / 2,373 (7); ccnn 17,285 (8) / 14,817 (7), closed form in the test (bias-free convs, B004).
5. Inner split: `StratifiedGroupKFold(5, shuffle, random_state=seed)` first split (seed = the fold seed); the function raises if a trial is in both fitting and validation windows.
6. Augmentation seed = fold seed (separate numpy generator, torch RNG untouched, PF-28).

## Legacy behaviour implemented

None.

## Deviations from the plan

- None in behaviour. Extras: `folds.csv` per-fold table, `--repeats`, `--max-folds` (smoke), `--max-epochs`, `--patience` in the sweep CLI; `Params`, `Augment`, `Device`, `Data source` columns appended after the §6 columns of `summary.csv`.
- `itr_bits_per_min` (Wolpaw, N=5, T = window + 0.5 s) is defined locally in `benchmark_nn_sweep.py`; ml-engineer's `summarize` has its own (not imported, to keep the files disjoint). The two should agree; the synthetic-tester can cross-check.
- Acc SD of `summary.csv` = SD over CV repeats (0 when Runs = 1), as for the window sweep; Train/Val Acc and Best Epoch are means over folds; Acc is pooled over all test windows.

## How to run / reproduce

Final CLI (the plan's command 3 works as written):

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_sweep --data-root data/processed_continuous --windows 1 \
  --models ccnn compact eegnet --out-dir reports/nn_sweep
# options: --stride 0.25 (folder w<len>_s<stride>) --subjects S01 .. --no-augment --repeats 1 --max-folds k --max-epochs 150 --patience 25 --device auto|cpu|cuda --seed 42
```
Outputs in `reports/nn_sweep/`: `summary.csv` (Subject, Window (s), Method, Windows, Trials, Acc (%), Acc SD, BalAcc (%), ITR (bits/min), Train Acc (%), Runs, Val Acc (%), Best Epoch, Params, Augment, Device, Data source), `folds.csv`, `predictions.csv` (subject, window_sec, method, run, trial_id, offset_sec, true, pred, p_101..p_105), `confusion.csv`. Method labels: `ccnn`, `compact_eegnet`, `eegnet`.

## How I verified

Tests (`tests/test_p20_networks.py`, 18):
- CCNN: output shape; `nfft = max(T, fs/0.25) = 1024` at T 128/256/1024 and 2048 at 8 s; 189 bins spanning [3, 50] Hz; parameter closed form; spectrum known answer (cosine amplitude 3 at 12 Hz gives real part 1.5 at that bin, imag 0); wrong shape raises.
- PF-31 counts: compact_eegnet 28,229, eegnet 2,389; unknown name (`compact_cnn`) raises.
- Planted sinusoids at 5 frequencies: `cnn_fold` (ccnn, CPU, 12 epochs) test accuracy > 0.6 (chance 0.2); CUDA run for the 3 models (skipped without CUDA); all 3 models run at T = 128/256/512.
- `fit_network` (PF-32, R2): `cnn_fold` receives only the training groups (spy); validation windows are whole trials, a subset of the training trials, disjoint from the test trials and from the fitting trials, ~20 % of the windows; normalisation mean equals the fitting-window mean.
- Best-state restore with a planted loss curve [3, 2, 1, 2, 3, 4]: best epoch 3, patience 3 stops at epoch 6, restored weights equal the epoch-3 snapshot and differ from epoch 6.
- Label range check; `--no-augment` leaves the split unchanged; ITR known values (N=5, P=1, T=1.5 s: log2(5)·60/1.5; P <= 0.2 gives 0); CLI on a synthetic built folder (3 models, summary/predictions columns).
- At least one test fails on the historical bug: validation drawn from the test fold would fail the spy/disjointness test; restoring the last (not best) state fails the planted-curve test.

Suite (`.venv/bin/python -m pytest tests/ -q -o addopts=""`, log `mas/state/scratch/suite_p20_dl.log`):
`1249 passed, 22 warnings in 823.95s (0:13:43)` (full suite, includes the other builders' files present in the working tree at that time)

## Measured runtimes (RTX 3050 laptop 4 GB, CUDA, batch 16, augmentation on, 7 channels, fs 256)

Method: `cnn_fold` on synthetic windows of the exact sweep shape (40 trials per subject, 32 training trials, windows per trial = (5-L)/0.25+1, 4 epochs with no early stop; script outside the repo), seconds per epoch including validation each epoch. Augmentation adds < 0.1 s/epoch except ccnn (0.074 vs 0.050 at 1 s). Real-data smoke (existing 1 s build `data/processed_continuous/S01,S04`, 160 train windows, one fold, up to 150 epochs, patience 25): epochs run 26–105 (best epoch 1–80); S01 ccnn 3.4 s, compact_eegnet 1.9 s, eegnet 1.0 s; S04 ccnn 2.1 s, compact_eegnet 7.4 s, eegnet 2.7 s per fold (19 s for the 6 folds). Small real-data numbers (S01 chance-level at 1 s, S04 100 %) are smoke only, not results.

Seconds per epoch (aug on) and per fold at the 150-epoch worst case:

| L (s) | windows/trial | train windows/fold | ccnn s/epoch | compact_eegnet s/epoch | eegnet s/epoch |
|---|---|---|---|---|---|
| 0.5 | 19 | 608 | 0.05 (*) | 0.191 | 0.098 |
| 1 | 17 | 544 | 0.074 | 0.274 | 0.145 |
| 1.5 | 15 | 480 | 0.076 | 0.356 | 0.165 |
| 2 | 13 | 416 | 0.069 | 0.395 | 0.174 |
| 3 | 9 | 288 | 0.052 | 0.404 | 0.198 |
| 4 | 5 | 160 | 0.031 | 0.296 | 0.141 |

(*) the measured 0.424 s/epoch for ccnn at 0.5 s included CUDA/cuFFT warm-up (first call); 0.05 is an estimate, not measured.

Estimates for 5 subjects x 5 folds = 25 folds (windows per trial before quality rejection; early stopping shortens real runs, 100 epochs is the typical-case column, observed 26–105 on the small smoke):

| Command | Models | 150-epoch worst case | 100-epoch typical |
|---|---|---|---|
| 3 (NN sweep, 1 s) | ccnn / compact_eegnet / eegnet | 4.6 / 17.1 / 9.1 min = **30.8 min** | 3.1 / 11.4 / 6.0 = **20.5 min** |
| 2, cnn part (`compact_eegnet`, 0.5-4 s, 1 repeat) | per L: 11.9, 17.1, 22.2, 24.7, 25.2, 18.5 min | **119.8 min** | **79.8 min** |
| (for reference) ccnn at all L | | 22.0 min | 14.7 min |
| (for reference) eegnet at all L | | 57.6 min | 38.4 min |

Budget consequence: commands 2-cnn + 3 = about 150 min worst case (100 min typical) against `LOCAL_RUN_BUDGET_MIN` 120 and `MAX_GPU_HOURS_PER_PHASE` 2 (GPU hours: 2.5 worst, 1.7 typical), before the LDA/FBCCA part and the builds. The plan's budget clause applies: the CNN part of the window sweep is a candidate human run; command 3 alone fits (20-31 min). compact_eegnet is GPU-bound (96 filters, batch 16, small kernels); lowering batch count is not possible without changing the settled batch 16.
