# P08 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md
Branch: phase/P08-eegnet
Commit(s): c04329b (bookkeeping), 799c81e (model), 94a2131 (CV helper), 87ed216 (script + tests)

## Questions
ACK 02_plan.md deep-learning 2026-10-25

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/models/cnn/eegnet.py` | NEW | `EEGNetSSVEP`, 4 convs `bias=False`, 2,349 params, head 128 -> 5 by dummy forward; `apply_max_norm()` renorms the 16 depthwise spatial filters (L2 over channels) to <= 1.0 | P08.1 | R-8, [2], Lawhern et al. 2018 |
| `src/models/cnn/eegnet_cv.py` | NEW | per-window z-score, `train_model` (AdamW wd 1e-2, Cosine eta_min 1e-5, CE ls 0.05, seeds, max-norm after each step), legacy-CV loop, train acc | P08.2 | PF-28, PF-30, R1/R8 legacy |
| `scripts/benchmarks/neural_networks/benchmark_eegnet.py` | NEW | CLI, same two-tier gate (`quality_gate`, `GATE_THRESHOLDS`, fail 0.5) and `legacy_cv` as the flagship, CSV + `.meta.txt` | P08.2 | decisions.md P08 |
| `tests/test_p08_eegnet.py` | NEW | 15 tests (count, shapes both forms, spatial axis, max-norm, gradients, z-score, determinism/seed, learnable, CV protocol, script smoke) | — | [own] |

## Legacy behaviours implemented

R1/PF-01 window-level `StratifiedKFold(5, shuffle, 42)` (`legacy_cv`), R8/PF-02 `i % 5` smoothing (`accuracies`), R5 per-script P07 gate. Labelled in console, `.meta.txt` and the `cv` field.

## Differences from the cited examples

The original EEGNet uses a Keras max_norm constraint; here it is a post-step renorm (equivalent), also applied once before training.

## Deviations from the plan

1. CSV is always `reports/eegnet_benchmark_<device>.csv` (device resolved; no unsuffixed file).
2. Uses `quality_gate` directly (not `prepare_subject`) to avoid computing unused FBCSP/FBCCA/PSD blocks; same function and thresholds as `build_feature_blocks`, so the same decision. Windows are on the kept channels (model `n_channels` follows tier 1).
3. A last mini-batch of size 1 is skipped (BatchNorm), as in P04.
4. `--data-root` has alias `--processed-dir`; cudnn deterministic is set on CUDA.

## How to run / reproduce

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cuda --augment off
```

## How I verified

- `.venv/bin/python -m pytest tests/ -o addopts="" -q`: `518 passed, 21 warnings in 189.89s (0:03:09)`; new file 15 passed in ~8 s.
- Param count 2,349 = 1000+16+112+32+256+256+32+645; flatten 128.
- Smoke on a synthetic 200-window tree (scratchpad), 20 epochs, 5 folds: CPU 4 s, CUDA 4 s (includes first-call overhead). Extrapolated 150 epochs on S03 (~197 windows): about 30 s per device, far below `LOCAL_RUN_BUDGET_MIN` and `MAX_GPU_HOURS_PER_PHASE`. Smoke accuracies are synthetic and say nothing about S03.
- R11: the reference repository was not opened.

## Sources
Lawhern et al. 2018 (EEGNet) as named by the roadmap task; not opened in this run. PyTorch API used as documented, not opened.
