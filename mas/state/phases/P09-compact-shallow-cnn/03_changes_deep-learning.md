# P09 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md
Branch: phase/P09-compact-shallow-cnn
Commit(s): 7cb9e1b, 5968142, 3cd7d7f, 4e59c32, e3124d6, dd85999 (after bookkeeping ce5d715)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/models/cnn/compact_cnn.py` | NEW | `CompactCNN`; spatial (C,1) conv + BN, temporal (1,K) conv pad K//2 + BN + ELU + Dropout, Linear; both convs `bias=False`; `fs=250.0` legacy default, K = 29; head sized by dummy forward | P09.1 | [2], R-8, PF-04, PF-31 |
| `src/models/cnn/shallow_conv_net.py` | NEW | `ShallowConvNet`; temporal (1,25) + spatial (C,1) convs `bias=False`, BN, square, AvgPool(75, stride 15), `log(clamp(x, 1e-6))`, Dropout, Linear; kernel/pool/stride clamped to the window | P09.2 | [2], R-8 |
| `src/models/cnn/eegnet_cv.py` | MODIFIED | network-agnostic `train_model(..., build_model)` and `train_and_eval_cv(X, y, build_model, ...)`; `train_and_eval_eegnet_cv` kept as thin wrapper; max-norm only if the model has `apply_max_norm`. EEGNet numbers unchanged | P09.3 | [2] |
| `src/models/cnn/benchmark_common.py` | NEW | shared driver (`NetSpec`, parser, P07 gate, header, loop, CSV + `.meta.txt`); meta now has the data-source line and `n_channels (after the gate)` (P08 carry-forward) | P09.3 | [2] |
| `scripts/benchmarks/neural_networks/benchmark_eegnet.py` | MODIFIED | thin wrapper over the driver (same CLI, `COLUMNS`, `gated_windows`, `main`); unused `discover_subjects` import gone with the refactor | P08 carry-forward | — |
| `scripts/benchmarks/neural_networks/benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py` | NEW | same wrapper, own `NetSpec`; outputs `reports/compact_cnn_benchmark_<device>.csv`, `reports/shallow_convnet_benchmark_<device>.csv` | P09.3 | [2] |
| `scripts/benchmarks/neural_networks/count_parameters.py` | NEW | counts at 7 x 256, checks R-8, writes `reports/network_parameter_counts.csv` (Model, Channels, Samples, Params); exit 1 on mismatch | P09.4 | R-8 |
| `tests/test_p09_compact_shallow.py` | NEW | 25 tests (see below) | — | [own] |

## Legacy behaviour implemented

R1/PF-01 `StratifiedKFold(5, shuffle, 42)`, R8/PF-02 `i % 5` smoothing, P07 per-script gate (all via the shared driver, labelled in stdout and `.meta.txt`), and PF-04: `CompactCNN(fs=250.0)` default gives K = 29 (fs 256 gives K = 30, 56,693 params; test shows the difference). Named `compact_cnn` everywhere (PF-31).

## Differences from the cited examples

None adapted from code; architectures built from the roadmap specification.

## Deviations from the plan

- Shared driver lives in `src/models/cnn/benchmark_common.py` (plan allowed "a shared network-agnostic module"). `--config` default is now resolved inside the driver (None -> `<root>/configs/pipeline_config.yaml`); behaviour identical.
- The EEGNet `.meta.txt` changed (carry-forward lines added); CSV and stdout results are byte/number identical.
- count_parameters adds an exit-1 check against R-8 (extra).

## How to run / reproduce

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.count_parameters
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_compact_cnn --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_shallow_convnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
```

## How I verified

- Counts: `count_parameters` prints eegnet 2,349 / shallow_convnet 14,485 / compact_cnn 56,021, all OK vs R-8; layer arithmetic in the tests (16*7 + 2*16 + 32*16*29 + 2*32 + 32*256*5 + 5 = 56,021; ShallowConvNet pooled length 11, head 40*11).
- EEGNet regression: before the refactor a synthetic smoke (3 trials/class, 2 epochs, CPU) CSV had sha256 6dbbe4aa...bd478 and `proba` (4 trials, 3 epochs) sha256 adf2cc7d...5322c; after the refactor both identical, pinned in `test_eegnet_regression_after_refactor`.
- `.venv/bin/python -m pytest tests/test_p09_compact_shallow.py -o addopts="" -q`: 25 passed in 14.60 s.
- Full suite: `.venv/bin/python -m pytest tests/ -o addopts="" -q` -> `553 passed, 21 warnings in 204.47s (0:03:24)`.
- Tests cover: counts and bias None, K = 29/30 and [4, n_samples] clamp, pooling at 256/128/40/10 samples, log clamp finite on zero input, shapes for 5/7/8 channels and 128/256/512 samples with both input forms, gradients on all params, wrong layout rejected, mirror protocol (identical cv/smoothing/gate/training/train-accuracy meta lines across the three scripts, shared `gated_windows`), gate drops a bad channel, scripts smoke (columns, params, 75 windows, meta data source + `n_channels`), `--augment on` rejected, CV deterministic and learnable (train >= test).
- CPU smoke timing (synthetic 200 windows x 7 x 256, 5 folds, 5 epochs, 12 CPU threads, warm), extrapolated x30 to 150 epochs: EEGNet 1.0 s -> ~31 s; Compact-CNN 1.1 s -> ~33 s; ShallowConvNet 1.4 s -> ~42 s. CUDA (same smoke): EEGNet 0.8 s (~23 s), Compact-CNN 0.2 s (~7 s), ShallowConvNet 0.3 s (~8 s). Extrapolation is rough (S03 has 197 clean windows, similar size); expected verifier CPU runs under ~1 min each.

## Left to do / known limitations

- Real S03 runs are the verifier's; no accuracy claimed. Smoke accuracies on synthetic data are not results.
- ShallowConvNet is linear-pool-then-log with dropout after the log, as specified; no max-norm (not in the roadmap).

## Reference consultations (R11)

None.

## Sources

1. `mas/03_ROADMAP.md` P09 (opened); `mas/04_REFERENCE_RESULTS.md` R-8; `mas/05_PITFALLS.md` PF-04/28/30/31.
2. Waytowich et al. 2018; Schirrmeister et al. 2017 (named in the roadmap; not re-opened in this run, architecture taken from the roadmap text).

## Questions

ACK 02_plan.md deep-learning 2026-10-26
