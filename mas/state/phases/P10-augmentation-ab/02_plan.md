# P10 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/02_REQUIREMENTS.md §4–§7, mas/04_REFERENCE_RESULTS.md R-7, R-9 and tolerances, mas/05_PITFALLS.md PF-01/02/28/29/30/31, P08–P10 rows of decisions.md, mas/state/reports/P08.md, P09.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Add training-fold augmentation (noise, scale, shift, intra-class mixup) and an OFF/ON
A/B across all subjects and the three networks under the legacy leaky protocol, with
the un-augmented training accuracy as the PF-30 diagnostic; compare the EEGNet cohort
gain with R-9a.

## Data source

Legacy 7-channel `data/processed/<S>/X_time_windows.npy` (P02, OO), S01–S05, stimulus
windows, P07 two-tier gate via the shared driver, CPU, seeds 42 + fold. No
preprocessing is run.

## Scope

**In:** P10.1–P10.3, the legacy-leaky freeze. **Out:** grouped CV and the leak-free A/B
(P11).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| deep-learning | NEW `src/preprocessing/dataset/augmentation.py` (+ `__init__.py` if needed) | the four functions and `SSVEPAugmentedDataset` exactly per [2] P10.1: noise ∝ per-channel std of that window (`std_frac` 0.05); one scale factor per window U(0.9, 1.1); circular roll by an integer shift ≤ 10 % of samples; mixup λ ~ Beta(0.4, 0.4), λ = max(λ, 1 − λ), partner drawn from the same class via a precomputed class→indices lookup; each op applied with probability 0.5 in the order mixup → scale → shift → noise; own `numpy.random.Generator(seed)` (does not touch the torch RNG); float32 / long tensors | P10.1 | [2], PF-29 |
| deep-learning | MODIFIED `src/models/cnn/benchmark_common.py`, `eegnet_cv.py`, the three `benchmark_*.py` | `--augment {off,on}` (default off): ON wraps only the **training fold** (after z-scoring, matching the order the network sees) in `SSVEPAugmentedDataset(seed=42+fold)`; test fold and train-accuracy pass untouched; OFF path byte-identical to P09 | P10.2 | [2] |
| deep-learning | NEW `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py` | `--model {eegnet,compact_cnn,shallow_conv_net}` (alias `shallow_convnet`), `--epochs 150`, `--subjects` (default all discovered), `--device` (default cpu), `--freeze-legacy` (also write `reports/legacy_leaky/augmentation_ab_<model>.csv`); per subject: OFF then ON with identical folds and `torch.manual_seed(42+fold)` before each model; final-epoch train accuracy on the un-augmented training fold (eval mode); warning line when OFF train < 40 %; CSV with the §6 columns + a Mean row + `.meta.txt` (legacy labels, data source, device, n_channels); per-fold lines in the console | P10.3 | [2], [1] §6, PF-28, PF-30 |

Settled (decisions.md): augmentation is applied after per-window z-scoring (the
network's input space; noise ∝ each channel's std then equals `std_frac`); the
augmentation generator is seeded per fold (42 + fold) and separate from the torch
RNG, so the OFF and ON arms start from the same model weights; device CPU; the
script writes the legacy-leaky copies itself (no hand copying into `reports/`).

## Legacy behaviour in this phase

R1 window-level CV, R8 `i % 5`, fs 250 in Compact-CNN, P07 per-script gate — labelled;
outputs frozen under `reports/legacy_leaky/` (P11 produces the leak-free A/B).

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| PF-29 | augmentation leaks to the test fold or train-accuracy pass; cross-class mixup | wrap only the training DataLoader; tests: test inputs bit-identical OFF vs ON; mixup partner label equals the anchor label |
| PF-28 | ON arm starts from different weights (augmentation RNG consumes torch RNG) | separate numpy generator; test: initial weights identical OFF/ON per fold |
| PF-30 | train accuracy measured on augmented data or used in training | eval-mode pass on the un-augmented training fold after training; test |
| R2 | augmentation statistics across windows | per-window std; mixup only within the training fold |
| Regression | OFF path differs from P09 | OFF smoke CSV byte-identical to the P09 driver; real-data check: EEGNet OFF S03 = P08 149/169 |
| Interpretation | leaky gains read as real | report and review state leaky; R-9a range comparison per tolerance table |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| noise | window with channel stds (1, 10) | added noise std ≈ 0.05 × each channel's std | 10 % rel. (many draws) | [2] |
| scale | window | output = k × input, one k ∈ [0.9, 1.1] for all channels | 1e-12 | [2] |
| shift | ramp window | circular roll by an integer ≤ floor(0.1 × T) | exact | [2] |
| mixup | two same-class windows | λ ≥ 0.5; output = λ a + (1 − λ) b; λ distribution ~ Beta(0.4,0.4) folded | KS p > 0.01 / exact | [2] |
| same-class | dataset with 5 classes | every mixup partner has the anchor's label | exact | PF-29 |
| order & p | instrumented ops | order mixup → scale → shift → noise; each applied ≈ 50 % | binomial 3σ | [2] |
| dtypes | `__getitem__` | float32 X, long y | exact | [2] |
| fold scope | OFF vs ON CV | test-fold inputs and train-acc inputs identical; only training batches differ | exact | PF-29, PF-30 |
| same init | OFF vs ON | model weights before epoch 1 identical per fold | exact | PF-28 |
| determinism | ON twice | identical | exact | PF-28 |
| OFF regression | P09 synthetic smoke | byte-identical CSV | exact | P09 |
| warning | OFF train < 40 % (forced) | warning line printed | — | [2] |
| CSV schema | script on synthetic tree | §6 columns, deltas = ON − OFF, Mean row | exact | [1] §6 |

Historical bug: PF-29 (cross-class mixup and augmenting the test fold) and PF-30
(train accuracy on augmented data) — the same-class and fold-scope tests fail on them.

## Run commands (for the verifier)

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model eegnet --epochs 150 --device cpu --freeze-legacy
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model compact_cnn --epochs 150 --device cpu --freeze-legacy
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model shallow_conv_net --epochs 150 --device cpu --freeze-legacy
```

Runtime estimate (from P08/P09 CPU timings per subject-arm: EEGNet ≈ 35 s, Compact ≈ 45 s,
Shallow ≈ 60 s; × 10 subject-arms; ON overhead unknown): ≈ 25–45 min total, under
`LOCAL_RUN_BUDGET_MIN` (120). The builder measures the ON overhead. The verifier saves
the pytest log under `reports/logs/P10/`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| EEGNet cohort augmentation gain in the range recorded by R-9a (+3.00 / +1.79 pp first run, 4/5 improved, S02 regressed; +7.34 pp last leaky run) — explain where yours falls | EEGNet Mean row 1.0 s and 2.0 s Delta; number of subjects improved; S02 sign; position relative to [+3.00, +7.34] pp at 1.0 s (cohort NN tolerance ±3 pp) | R-9a |
| S01/S02 near chance with high training accuracy is reproduced and interpreted | per-subject OFF/ON test vs train accuracy for S01, S02 (chance 20 %); reviewer interprets (PF-30) | R-9a, PF-30 |
| CSVs frozen | `reports/legacy_leaky/augmentation_ab_<model>.csv` for the three models, identical to `reports/augmentation_ab_<model>.csv` | [2] Run |
| regression | EEGNet OFF S03 = 75.63 / 85.79 % (149 / 169 of 197), the P08 CPU numbers | decisions.md P09 |

## Sources

1. `mas/02_REQUIREMENTS.md` §4–§7 (opened in this run).
2. `mas/03_ROADMAP.md` P10 (opened in this run).
3. `mas/04_REFERENCE_RESULTS.md` R-7, R-9; `mas/05_PITFALLS.md` PF-28–PF-31 (opened in this run).

## Questions
