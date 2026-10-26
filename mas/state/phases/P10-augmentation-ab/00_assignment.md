# P10 · 00 · Assignment — Data augmentation and the A/B protocol

Status: READY
Author: orchestrator
Branch: phase/P10-augmentation-ab (from main @ 8430cb9, tag p09-done)
Era: A — legacy behaviours required (`team.yaml`, `RULES.md` era matrix): **R1** window-level `StratifiedKFold(5, shuffle, 42)` ("Era-A, leaky CV"); **R8** `i % 5` smoothing; **fs250** where it enters (Compact-CNN K = 29); the P07 two-tier gate on the legacy 7-channel arrays. Outputs frozen as `reports/legacy_leaky/` (they are superseded in P11).
Owners (agents): deep-learning (Deep Learning); scientific-reviewer (owner per roadmap: interprets the A/B); verifier
Depends on: P09 (passed; merged 8430cb9)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Roadmap items "implement simple EEG data augmentation" and "networks +
augmentation". The first A/B showed EEGNet near chance on S01/S02 → a train-accuracy
diagnostic was added to tell non-convergence from overfitting.
**Depends on:** P09. **Owners:** Deep Learning, Scientific Reviewer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/preprocessing/dataset/augmentation.py`: `add_gaussian_noise(window,
   std_frac=0.05)` (noise ∝ each channel's std), `scale_amplitude(window, (0.9, 1.1))`
   (one factor per window), `time_shift(window, max_shift_frac=0.1)` (circular roll),
   `mixup_intra_class(a, b, alpha=0.4)` (λ ~ Beta(α,α), `λ = max(λ, 1−λ)`, **same
   class only**). `SSVEPAugmentedDataset(X, y, p_noise=p_scale=p_shift=p_mixup=0.5,
   seed)`: training fold only, on the fly, order mixup → scale → shift → noise,
   precomputed class→indices lookup, returns float32/long tensors.
2. `--augment` flag in the three single-subject NN benchmarks (off by default).
3. `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py --model
   {eegnet,compact_cnn,shallow_conv_net} --epochs 150`: every subject, OFF then ON,
   same seeds; final-epoch **training accuracy** on the un-augmented training fold
   (diagnostic; never used for gradients); warn when OFF train accuracy < 40 %; save
   `reports/augmentation_ab_<model>.csv`.

## Run (verbatim)

Run (Era-A, leaky CV): all three models. Freeze the CSVs as
`reports/legacy_leaky/augmentation_ab_<model>.csv`.

## Outputs (verbatim, mas/phases.yaml)

`src/preprocessing/dataset/augmentation.py`, `benchmark_nn_augmentation.py`, `reports/legacy_leaky/augmentation_ab_<model>.csv`

## Acceptance (verbatim)

Acceptance: EEGNet cohort augmentation gain in the range recorded by **R-9a** (first
leaky run +3.00 pp 1.0 s / +1.79 pp 2.0 s with 4/5 subjects improved and S02
regressed; the last leaky run before the fix +7.34 pp 1.0 s) — explain where yours
falls; S01/S02 near chance with high training accuracy is reproduced and interpreted
(generalization failure, not optimization failure).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-9a | mas/04_REFERENCE_RESULTS.md | EEGNet leaky cohort gain +3.00 pp (1.0 s) / +1.79 pp (2.0 s), 4/5 improved, S02 regressed, S01/S02 ≈ 27–28 % vs classical 64–66 %; last leaky run +7.34 pp (1.0 s). Neural networks: per subject ±5 pp, cohort mean ±3 pp, "a sign flip of an A/B delta at cohort level" must be explained (tolerance table) |
| R-9b, R-7 | mas/04_REFERENCE_RESULTS.md | leak-free A/B and ON numbers — P11 targets, diagnostic only here |
| PF-28 | mas/05_PITFALLS.md | OFF and ON with the same seeds: same model init per fold; augmentation RNG separate so it does not shift model init |
| PF-29 | mas/05_PITFALLS.md | augmentation on the training fold only, on the fly; mixup same class only |
| PF-30 | mas/05_PITFALLS.md | train accuracy on the **un-augmented** training fold, never used for gradients; warn OFF train < 40 % |
| PF-01, PF-02 | mas/05_PITFALLS.md | leaky CV and `i % 5` smoothing (fixed P11) |
| PF-31 | mas/05_PITFALLS.md | `compact_cnn` naming |
| 02_REQUIREMENTS §6 | | `augmentation_ab_<model>.csv` columns `Subject, Clean Windows, 1.0s OFF (%), 1.0s ON (%), 1.0s Delta, 2.0s OFF (%), 2.0s ON (%), 2.0s Delta, Train Acc OFF (%), Train Acc ON (%)` |
| decisions.md P08/P09 | | CPU device for A/B, fixed seeds, few-window differences are noise; EEGNet OFF on S03 must equal P08 (149/169) — regression check of the P09 refactor; P07: no preprocessing over data/processed |
| R2, R9, R10, R11 | mas/RULES.md | augmentation statistics from the window/training fold only; per-subject; cite; `after-attempt` |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| deep-learning | P10.1–P10.3 | `03_changes_deep-learning.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review = the acceptance interpretation | `07_review.md` |
| verifier | run (three models, all subjects, CPU) + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P10.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
