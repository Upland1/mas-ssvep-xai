# P08 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/02_REQUIREMENTS.md §4, §5, §7, mas/04_REFERENCE_RESULTS.md R-8, mas/05_PITFALLS.md PF-01/02/28/30, P04–P07 rows of decisions.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Implement EEGNet-SSVEP with exactly R-8's 2,349 parameters and benchmark it on S03's
raw legacy windows under the classical benchmark's gate and leaky CV, on CPU and GPU.

## Data source

Legacy 7-channel folders `data/processed/<S>/X_time_windows.npy` (P02, OO), stimulus
windows, the P07 two-tier gate (vpp 5–120, std 1–35, fail > 50 %) via the shared
pipeline (same decision as the classical benchmark), channel names from
`subject_channel_names`. No preprocessing is run (P07 rule).

## Scope

**In:** P08.1, P08.2. **Out:** augmentation (P10; `--augment` accepts only `off` here),
Compact-CNN/ShallowConvNet (P09), trial-grouped CV (P11).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| deep-learning | NEW `src/models/cnn/eegnet.py` | `EEGNetSSVEP` exactly per [2] P08.1: block-1 temporal conv `bias=False`, BN, depthwise spatial conv `bias=False` with max-norm 1.0 (renorm of the depthwise weights after each optimizer step, or a parametrization — documented), BN, ELU, AvgPool(1,4), Dropout; block-2 depthwise (1,16) pad 8 `bias=False` + pointwise 1×1 `bias=False`, BN, ELU, AvgPool(1,8), Dropout; Linear head sized by a dummy forward; accepts `(B,C,T)` and `(B,1,C,T)` | P08.1 | [2], R-8 |
| deep-learning | NEW `scripts/benchmarks/neural_networks/benchmark_eegnet.py` (+ `__init__.py` if needed), shared training helper in `src/` if useful | CLI `--subject` (default S03), `--subjects`, `--epochs 150`, `--batch-size 32`, `--lr 1e-3`, `--device auto|cpu|cuda`, `--augment off` (only value in P08), `--seed 42`, `--data-root`, `--reports-dir`; same gate (`prepare_subject`/two-tier pipeline) and `legacy_cv` folds as the flagship; per-window per-channel z-score `(x − mean_t)/std_t` with an epsilon; AdamW(lr, wd 1e-2); CosineAnnealingLR(T_max=epochs, eta_min=1e-5); CE(label_smoothing=0.05); `torch.manual_seed(42+fold)` before each fold's model; seeded DataLoader generator; no validation split, no early stopping (fixed epochs); out-of-fold probabilities → 1.0 s and `i % 5` smoothed accuracy; mean final training accuracy on the un-augmented training fold (PF-30); CSV `reports/eegnet_benchmark[_<device>].csv` (`Subject, Device, Clean Windows, Rejected, 1.0s Acc (%), 2.0s Smoothed (%), Train Acc (%), Params`) + `.meta.txt` with legacy labels | P08.2 | [2], PF-28, PF-30 |

## Legacy behaviour in this phase

R1 window-level CV, R8 `i % 5` smoothing, P07 per-script two-tier gate (R5 legacy),
labelled in console, CSV `.meta.txt`; fixed in P11/P16.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R-8 | biases or wrong padding change the count | exact 2,349 test; flatten size 128 |
| max-norm | constraint not applied or applied to the wrong layer | test: after a step with large gradients, every depthwise filter norm ≤ 1.0 + 1e-6; other layers unconstrained |
| R2 | z-score with dataset statistics | per-window statistics only; test that scaling one window does not change another's input |
| PF-28 | nondeterminism | seeds; two short runs identical on CPU |
| R6 | `(B,C,T)` vs `(B,1,C,T)` mix-up or channel/time swap | test both shapes give identical output; spatial filter acts over channels |
| PF-30 | train acc on augmented data | augmentation off; train acc on the training fold |
| Device | CPU vs GPU differ | numbers always labelled with device (decisions.md P04) |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| param count | `EEGNetSSVEP()` | 2,349 trainable; conv biases None | exact | R-8 |
| shapes | `(B,7,256)`, `(B,1,7,256)`, 8 channels, 128/512 samples | output `(B,5)`; head sized automatically; same output for the two input forms | exact / 1e-6 | [2], [1] §7 "networks" |
| max-norm | depthwise weights scaled ×10 then one step | every depthwise filter L2 norm ≤ 1.0 | 1e-6 | [2] |
| gradients flow | one backward pass | all parameters receive gradients | — | [1] §7 |
| z-score | windows with offsets/gains per channel | each window-channel has mean 0, std 1; independent of other windows | 1e-6 | [2] |
| seed per fold | two 2-epoch CPU runs | identical predictions; different seed → different | exact | PF-28 |
| learnable task | synthetic tree with planted class sinusoids, few epochs | test accuracy well above chance | > 0.6 | [own] |
| CV / smoothing | as P05 | `StratifiedKFold(5, True, 42)`; `i % 5` | exact | R1, R8 legacy |
| script smoke | synthetic legacy tree, `--epochs 2 --device cpu` | CSV with the columns, exit 0 | — | [own] |

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cuda --augment off
```

Runtime: 5 folds × 150 epochs × ~5 batches of 32 on a 2.3k-parameter network — builder
measures (expected minutes on CPU, less on GPU). GPU use well under
`MAX_GPU_HOURS_PER_PHASE` (2). Over budget? no.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| trains on CPU and GPU | both commands exit 0 with `Device` cpu / cuda in the CSV and log | — |
| numbers recorded (Era-A leaky) | per-device table: clean/rejected (S03 197/3), 1.0 s, 2.0 s, train acc, params 2,349 | R-8 exact; no accuracy target |

## Sources

1. `mas/02_REQUIREMENTS.md` §4, §5, §7 (opened in this run).
2. `mas/03_ROADMAP.md` P08 (opened in this run).
3. `mas/04_REFERENCE_RESULTS.md` R-7, R-8, R-9; `mas/05_PITFALLS.md` (opened in this run).
4. PyTorch `nn.Conv2d` (groups), `torch.renorm`/max-norm, `AdamW`, `CosineAnnealingLR`, `CrossEntropyLoss(label_smoothing)` docs — builder opens and cites.

## Questions
