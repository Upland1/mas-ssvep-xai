# P10 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Branch: phase/P10-augmentation-ab

## Files
- NEW `src/preprocessing/dataset/augmentation.py` — `add_gaussian_noise`, `scale_amplitude`, `time_shift`, `mixup_intra_class`, `SSVEPAugmentedDataset` (order mixup, scale, shift, noise; p = 0.5 each; own `numpy.random.Generator`; class-to-indices lookup; float32 / long).
- MODIFIED `src/models/cnn/eegnet_cv.py` — `train_model(augment_seed=None)`, `train_and_eval_cv(augment=False)`: ON swaps only the training DataLoader dataset (after z-scoring) for `SSVEPAugmentedDataset(seed=42+fold)`; test pass and train-accuracy pass untouched. OFF code path unchanged.
- MODIFIED `src/models/cnn/benchmark_common.py` — `--augment {off,on}`; ON writes `<name>_aug_benchmark_<device>.csv`; OFF header/CSV unchanged.
- MODIFIED the three `benchmark_*.py` (docstring line only).
- NEW `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py` — `--model {eegnet,compact_cnn,shallow_conv_net|shallow_convnet}`, `--epochs`, `--subjects`, `--device` (default cpu), `--freeze-legacy`; OFF then ON per subject; section 6 columns + Mean row + `.meta.txt`; per-fold console lines; warning when OFF train < 40 %.
- NEW `tests/test_p10_augmentation.py` (15 tests); MODIFIED `tests/test_p08_eegnet.py`, `tests/test_p09_compact_shallow.py` (the P09 assertion "`--augment on` is rejected" became "an invalid value is rejected").

## Commits
8d872f0 chore bookkeeping; 75b2557 augmentation module; 66400a0 --augment in driver; f95a0bc A/B script; 6f04a77 tests; plus the commit "test: --augment accepts on, rejects other values" (see `git log`).

## Verification
- `pytest tests/ -o addopts="" -q`: `588 passed, 21 warnings in 214.34s (0:03:34)`.
- OFF regression: the P09 hashes (`EEGNET_SMOKE_PROBA_SHA256`, `EEGNET_SMOKE_CSV_SHA256`) still pass unchanged; `test_off_path_identical_to_p09`.
- PF-28 test: initial weights per fold identical OFF/ON. PF-29: evaluated rows are exact z-scored windows; mixup partner same class (negative control: cross-class pool detected). PF-30: train pass on un-augmented fold. Parameter counts unchanged (R-8 tests of P09 pass).

## Smoke runtimes (CPU, 16 cores, synthetic S03-like, 200 windows, 15 epochs, 5 folds; scratchpad, not real data)
| model | OFF s | ON s |
|---|---|---|
| eegnet | 4 | 4 |
| compact_cnn | 4 | 5 |
| shallow_conv_net | 6 | 5 |

Augmentation cost isolated: 150 epochs x 160 windows = 0.7 s per fold (about 3.5 s per subject-arm). Extrapolation x10 epochs: about 40 / 45-50 / 60 s per subject-arm, so 10 subject-arms = about 7 / 8 / 10 min, about 25 min for the three models (ON overhead < 10 %). Even if real subjects have twice the windows, about 50-60 min < 120 min. Consistent with the plan's P08/P09 timings (35 / 45 / 60 s).

## Deviations / notes
- ON benchmark scripts write `*_aug_benchmark_*.csv` to avoid overwriting OFF (my choice; the plan did not name it).
- Noise is `std_frac` times each channel's std in the z-scored window (equals 0.05 there, per decisions.md).
- Mixup partner may be the anchor itself (uniform draw from the class); alpha 0.4.
- Real-data checks (EEGNet OFF S03 = 149/169; R-9a comparison) are the verifier's. No real data was run.
- R11: the reference repo was not opened.
