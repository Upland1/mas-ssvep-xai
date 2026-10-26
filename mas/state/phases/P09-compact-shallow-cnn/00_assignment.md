# P09 · 00 · Assignment — Compact-CNN and ShallowConvNet

Status: READY
Author: orchestrator
Branch: phase/P09-compact-shallow-cnn (from main @ eaabd9f, tag p08-done)
Era: A — legacy behaviours required (`team.yaml`, `RULES.md` era matrix): **R1** window-level `StratifiedKFold(5, shuffle, 42)`; **R8** `i % 5` smoothing; **fs250** in Compact-CNN's kernel (`fs=250.0` default → K = 29); the P07 two-tier gate on the legacy 7-channel arrays. Benchmarks mirror P08's `benchmark_eegnet.py` exactly.
Owners (agents): deep-learning (Deep Learning); verifier
Depends on: P08 (passed; merged eaabd9f)

## Origin (verbatim from mas/03_ROADMAP.md)

The roadmap gives no Origin paragraph for P09.
**Depends on:** P08. **Owners:** Deep Learning, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/models/cnn/compact_cnn.py::CompactCNN(n_classes=5, n_channels=7,
   n_samples=256, fs=250.0, lowest_freq_hz=8.5714, F1=16, F2=32, dropout_rate=0.5)`
   (Waytowich et al. 2018, faithful in spirit): spatial Conv2d(1→F1, (C,1), no bias) +
   BN → temporal Conv2d(F1→F2, (1,K), pad K//2, no bias) + BN + ELU + Dropout, with
   `K = clamp(round(fs / lowest_freq), 4, n_samples)` (one cycle of the slowest
   target) → Flatten → Linear.
2. `src/models/cnn/shallow_conv_net.py::ShallowConvNet(n_classes=5, n_channels=7,
   n_samples=256, F1=40, temporal_kernel_length=25, pool_kernel_length=75,
   pool_stride=15, dropout_rate=0.5)` (Schirrmeister et al. 2017): temporal Conv2d(1→F1, (1,25), **no bias**) →
   spatial Conv2d(F1→F1, (C,1), **no bias**) → BN → square → AvgPool → `log(clamp(x, 1e-6))` → Dropout →
   Linear; clamp kernel/pool sizes to the window.
3. `benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py`: mirror
   `benchmark_eegnet.py` exactly.
4. Report parameter counts for 7 channels × 256 samples (**R-8**: EEGNet 2,349,
   ShallowConvNet 14,485, Compact-CNN 56,021).

## Run (verbatim)

The roadmap gives no run line. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`src/models/cnn/compact_cnn.py`, `src/models/cnn/shallow_conv_net.py`, `benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py`

## Acceptance (verbatim)

Acceptance: parameter counts equal R-8 exactly; benchmarks run.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-8, B004 | mas/04_REFERENCE_RESULTS.md, mas/state/blockers/ | exact counts with BN-followed convs `bias=False`; orchestrator check in PyTorch (log.md step 2): Compact-CNN K = 29 → 56,021; ShallowConvNet pooled length 11 → 14,485; EEGNet 2,349 (P08) |
| PF-31 | mas/05_PITFALLS.md | `CompactCNN` (spatial → temporal, 56,021, P09–P11) is not the P20 `compact` EEGNet variant; name it `compact_cnn` in every table |
| PF-04 | mas/05_PITFALLS.md | Compact-CNN's `fs=250.0` default sets K from the legacy 250 Hz (K = 29; at 256 Hz K = 30 → different count); legacy, labelled |
| PF-28, PF-30 | mas/05_PITFALLS.md | seeds per fold; train accuracy next to test |
| PF-01, PF-02 | mas/05_PITFALLS.md | leaky CV and `i % 5` smoothing (fixed P11) |
| R-7, R-9 | mas/04_REFERENCE_RESULTS.md | later leak-free / augmentation numbers, diagnostic only |
| decisions.md P08 | | A/B and comparisons on one fixed device (CPU) with fixed seeds; differences of a few windows are noise; verifier saves the pytest log; EEGNet carry-forwards (meta data-source line, unused import, gate-equality test) |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| deep-learning | P09.1–P09.4 + P08 carry-forwards for the shared benchmark code | `03_changes_deep-learning.md` |
| synthetic-tester | known-answer tests incl. the gate-equality test (P08 carry-forward) | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P09.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
