# P08 · 00 · Assignment — EEGNet on raw windows

Status: READY
Author: orchestrator
Branch: phase/P08-eegnet (from main @ 5f5b46c, tag p07-done)
Era: A — legacy behaviours required (`team.yaml`, `RULES.md` era matrix): **R1** window-level `StratifiedKFold(5, shuffle, 42)` ("same CV scheme as the classical benchmark"); **R8** `i % 5` smoothing (P05–P10 row); **fs250** where fs enters (it does not enter EEGNet itself); the P07 two-tier gate (vpp 5–120, std 1–35, channel fail > 50 %) on the legacy 7-channel arrays.
Owners (agents): deep-learning (Deep Learning); verifier
Depends on: P07 (passed; merged 5f5b46c)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Roadmap item "try other neural network architectures"; first network.
**Depends on:** P07. **Owners:** Deep Learning, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/models/cnn/eegnet.py::EEGNetSSVEP(n_classes=5, n_channels=7, n_samples=256,
   F1=8, D=2, F2=16, kernel_length=125, dropout_rate=0.25)`: block 1 = Conv2d(1→F1,
   (1,K), pad K//2, no bias) + BN + depthwise Conv2d(F1→F1·D, (C,1), groups F1, no
   bias, **max-norm 1.0**) + BN + ELU + AvgPool(1,4) + Dropout; block 2 = depthwise
   Conv2d(F1·D, (1,16), pad 8) + pointwise 1×1 → F2 + BN + ELU + AvgPool(1,8) +
   Dropout; Linear head sized by a dummy forward pass. Accepts `(B,C,T)` or `(B,1,C,T)`.
2. `scripts/benchmarks/neural_networks/benchmark_eegnet.py --subject S03 --epochs 150
   --batch-size 32 --lr 1e-3 --device --augment(off)`: same quality gate and CV
   scheme as the classical benchmark, **per-window per-channel z-scoring** (each
   window's own mean/std over time), AdamW (wd 1e-2), CosineAnnealingLR (eta_min
   1e-5), `CrossEntropyLoss(label_smoothing=0.05)`, `torch.manual_seed(42+fold)`
   before building each fold's model, 1.0 s and smoothed accuracy.

## Run (verbatim)

The roadmap gives no run line beyond the task's CLI. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/models/cnn/eegnet.py`, `benchmark_eegnet.py`

## Acceptance (verbatim)

Acceptance: trains on CPU and GPU; numbers recorded (Era-A leaky).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-8 | mas/04_REFERENCE_RESULTS.md | EEGNet = 2,349 parameters at 7 channels × 256 samples, 5 classes, every BN-followed conv `bias=False` (orchestrator check: layer sum 2,349, flatten 16 × 8 = 128; log.md step 2) — exact |
| R-7, R-9 | mas/04_REFERENCE_RESULTS.md | leak-free / augmentation numbers for P10–P11; **not** targets for P08 (leaky, augmentation off) |
| PF-28 | mas/05_PITFALLS.md | seed before each fold's model; seeded DataLoader generator |
| PF-30 | mas/05_PITFALLS.md | report final training accuracy on the un-augmented training fold next to test accuracy |
| PF-01, PF-02 | mas/05_PITFALLS.md | leaky CV and `i % 5` smoothing reproduced (fixed P11) |
| PF-06, PF-10 | mas/05_PITFALLS.md | P07 gate and channel names reused, one decision |
| R2 | mas/RULES.md | z-scoring is per window over its own time samples (allowed: uses no other window, 02_REQUIREMENTS §5.2); no early stopping on test folds |
| R6, R9 | mas/RULES.md | input layout `(B,C,T)` → `(B,1,C,T)` proven; per-subject with data source |
| decisions.md P04/P07 | | P04: CPU and CUDA give different but individually deterministic numbers — the device is stated with every number; P07: do not run preprocessing over `data/processed` |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| deep-learning | P08.1, P08.2 — first builder | `03_changes_deep-learning.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run (CPU and GPU) + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P08.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
