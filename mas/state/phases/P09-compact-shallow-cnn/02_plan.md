# P09 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/02_REQUIREMENTS.md §4, §5, §7, mas/04_REFERENCE_RESULTS.md R-7, R-8, R-9, mas/05_PITFALLS.md PF-01/02/04/28/30/31, P08 rows of decisions.md, mas/state/reports/P08.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Add Compact-CNN and ShallowConvNet with R-8's exact parameter counts and benchmark them
on S03 with the P08 EEGNet protocol unchanged.

## Data source

As P08: legacy 7-channel `data/processed/<S>/X_time_windows.npy` (P02, OO), stimulus
windows, P07 two-tier gate, `subject_channel_names`. No preprocessing is run.

## Scope

**In:** P09.1–P09.4; P08 carry-forwards on the shared benchmark code (data-source line +
`n_channels` in `.meta.txt`, unused import). **Out:** augmentation (P10), grouped CV (P11).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| deep-learning | NEW `src/models/cnn/compact_cnn.py` | `CompactCNN` per [2] P09.1; K = clamp(round(fs / lowest_freq), 4, n_samples) with fs 250 default (legacy, labelled; K = 29); accepts `(B,C,T)`/`(B,1,C,T)` | P09.1 | [2], R-8, PF-04 |
| deep-learning | NEW `src/models/cnn/shallow_conv_net.py` | `ShallowConvNet` per [2] P09.2; temporal and spatial convs `bias=False`; square → AvgPool(75, stride 15) → log(clamp 1e-6); kernel/pool clamped to the window (e.g. 128 samples) | P09.2 | [2], R-8 |
| deep-learning | NEW `scripts/benchmarks/neural_networks/benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py`; MODIFIED `src/models/cnn/eegnet_cv.py` (or a shared network-agnostic CV/training module) and `benchmark_eegnet.py` only if refactored to share code | mirror `benchmark_eegnet.py` exactly (same CLI, gate, legacy folds, z-score, AdamW 1e-2, cosine eta_min 1e-5, CE 0.05, seeds 42+fold, 150 epochs, OOF 1.0 s + `i % 5`, train acc, CSV `reports/<model>_benchmark_<device>.csv` + `.meta.txt` with legacy labels, data source and `n_channels`); EEGNet outputs and numbers must stay identical (regression test) | P09.3 | [2] |
| deep-learning | NEW `scripts/benchmarks/neural_networks/count_parameters.py` (or a `--count-params` mode) | prints the three counts at 7 × 256 and writes `reports/network_parameter_counts.csv` (`Model, Channels, Samples, Params`) | P09.4 | [2], R-8 |

## Legacy behaviour in this phase

R1, R8, fs 250 (Compact-CNN kernel), P07 per-script gate — labelled as in P08.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R-8 | biases, K or pooling off by one | exact-count tests; K = 29 at fs 250 and 30 at fs 256 (PF-04 shown) |
| PF-31 | naming collision with the later `compact` | class and table name `CompactCNN` / `compact_cnn` |
| Mirror | the two scripts drift from P08's protocol | shared code path or a test that the training config/folds/seeds equal EEGNet's |
| Regression | refactor changes EEGNet results | EEGNet synthetic smoke CSV byte-identical before/after |
| ShallowConvNet log | log of zero/negative | clamp 1e-6; test |
| PF-28/30 | as P08 | seeds per fold; train acc on the training fold |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| param counts | default constructors at 7 × 256 | Compact-CNN 56,021; ShallowConvNet 14,485; EEGNet 2,349; conv biases None | exact | R-8 |
| Compact-CNN K | fs 250, 256; lowest 8.5714 | K = 29, 30; clamp to [4, n_samples] at extreme fs | exact | [2] |
| ShallowConvNet pooling | 256 and 128 samples | pooled length 11 at 256; clamped kernel/pool at 128 run | exact | [2] |
| log clamp | zero input | finite output | — | [2] |
| shapes / grads | 7 and 8 channels; 128/256/512 samples; both input forms | `(B,5)`; gradients reach all params | — | [1] §7 |
| mirror protocol | benchmark configs | identical folds, seeds, optimizer, schedule, loss, epochs to EEGNet | exact | [2] P09.3 |
| EEGNet regression | P08 synthetic smoke | identical CSV | exact | P08 |
| scripts smoke | synthetic tree, 2 epochs, CPU | exit 0, CSV columns, `.meta.txt` data-source + `n_channels` | — | [own] |

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.count_parameters
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_compact_cnn --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_shallow_convnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
```

CPU per the P08 device decision. Runtime: builder measures (P08 EEGNet ≈ 35 s on CPU;
Compact-CNN and ShallowConvNet are larger but small). The verifier also saves the
pytest log under `reports/logs/P09/` (decisions.md P09+).

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| parameter counts equal R-8 exactly | `reports/network_parameter_counts.csv` and log: 2,349 / 14,485 / 56,021 | R-8 exact |
| benchmarks run | both commands exit 0; per-model table S03 197/3, 1.0 s, 2.0 s (k/197), train acc | — (no target; R-7/R-9 diagnostic only) |

## Sources

1. `mas/02_REQUIREMENTS.md` §4, §5, §7 (opened in this run).
2. `mas/03_ROADMAP.md` P09 (opened in this run).
3. `mas/04_REFERENCE_RESULTS.md` R-7, R-8, R-9; `mas/05_PITFALLS.md` (opened in this run).

## Questions
