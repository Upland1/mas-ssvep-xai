# P20 · 00 · Assignment — Detection: window length, ITR, CCNN, NN sweep, dynamic stopping, pseudo-online

Status: READY
Author: orchestrator
Branch: phase/P20-detection-online (from main @ e4978f5, tag p19-done)
Era: C. Legacy behaviours required: **none**. Enforced: R1 (trial-grouped CV; true trial ids — essential with overlapping stride-0.25 windows), R2 (scaler, CSP, early-stopping validation and augmentation in-fold only), R3 (continuous filtering then window; online: stateful causal filter), R5 (shared quality, explicit thresholds, explicit `--quality-source`), R6, R8 (no smoothing in the sweep; dynamic stopping orders windows by (trial, offset)), R9, fs from metadata.
Owners (agents): deep-learning (Deep Learning), ml-engineer (Classical ML), data-signal (Online / Real-time); scientific-reviewer; verifier
Depends on: P17, P18, P19 (all passed)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Professor (Oct 11): treat it as a **detection** problem, test different
window sizes, identify which frequency it is, and run online with a neural network.

## Tasks (verbatim from mas/03_ROADMAP.md)

Tasks
1. Build sweep data: `build_windows.py --window-sec 0.5 1 1.5 2 3 4 --stride-sec 0.25
   --banks fbcca fbcsp` → `data/processed_continuous/w<len>_s0.25/`.
2. `scripts/benchmarks/benchmark_window_sweep.py --windows … --methods fbcca lda cnn
   --cv-repeats 5 --cnn-repeats 1`: vectorized FBCCA (`reference_bases`: orthonormalized
   (QR) mean-centred sin/cos references, 3 harmonics; per band QR of the centred window,
   top singular value of `Qxᵀ Qy` = first canonical correlation, clipped to [0,1],
   weighted squared sum); `lda_fold` (in-fold CSP per band + FBCCA → scaler →
   Shrinkage-LDA); `cnn_fold` (Compact-CNN, real fs); trial-grouped CV; no smoothing;
   `summarize` (accuracy, SD over runs, balanced accuracy, ITR with `T = window +
   0.5 s`, train accuracy); `predictions.csv` (offset per window) and pooled
   `confusion.csv`.
3. `src/models/cnn/ccnn.py::CCNN(n_classes, n_channels, n_samples, fs=256, f_min=3,
   f_max=50, resolution_hz=0.25, n_filters=2C, spectral_kernel=10, dropout=0.25)`:
   zero-padded rFFT (nfft = max(T, fs/resolution)), bins in [3, 50] Hz, `[real | imag]
   / T`, spatial Conv2d (C,1) + BN + ReLU + Dropout → spectral Conv2d (1, 10) + BN +
   ReLU + Dropout → Linear.
4. `scripts/benchmarks/benchmark_nn_sweep.py --windows 1 --models ccnn compact eegnet
   [--no-augment]`: `fit_network` = inner `StratifiedGroupKFold(round(1/val_frac))`
   on training trials for validation (20 %), augmentation on by default, AdamW/cosine/
   label smoothing, keep the best validation-loss state, patience 25, max 150 epochs;
   report train/val accuracy and best epoch. **Note:** here `compact` is the
   EEGNet-based Compact-CNN (`EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2,
   dropout=0.5)`) and `eegnet` uses `kernel=fs//2` — different from P09's `CompactCNN`
   class (PF-31). Keep both and label them unambiguously in reports.
5. `scripts/benchmarks/simulate_dynamic_stopping.py <predictions.csv …>
   --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5`: per trial, windows in time
   order after `skip`, cumulative mean probabilities, decide at the first window whose
   max ≥ threshold, else forced final decision; time = window offset + window length;
   accuracy, mean time, forced %, ITR (time + gaze); best threshold per method/window by
   ITR; FBCCA skipped (not probabilities).
6. `scripts/benchmarks/pseudo_online.py --train-session OO --test-session mOO --model
   ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6
   [--rest-class]`: train on one run (causal filter, windows, quality gate, network with
   early stopping), replay the other run in stride-sized chunks through a **stateful
   causal** SOS filter (Butterworth band-pass + notch, `sosfilt` with carried `zi`),
   evaluate windows on a fixed clock, predict valid windows; decide per stimulus period
   with the threshold rule (rest class excluded from the decision; with `--rest-class`,
   no threshold → "no target"); false activations in the no-stimulus period before
   each target (`REST_SEC = 5 s` = fixation + cue + preparation, used as the rest
   segment when training the 6th class); label-free channel check on the first
   `--check-sec 30` s of the test stream; fallback retrain with `--fallback-window-sec 1`
   if validation accuracy < `--min-val-acc 50`; warn when train/test paradigms differ
   (OO vs C); save `summary_<tag>.csv` and `decisions_<tag>.csv`. The MARK channel of
   the test run is used only for scoring.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

benchmark_window_sweep.py, src/models/cnn/ccnn.py, benchmark_nn_sweep.py, simulate_dynamic_stopping.py, pseudo_online.py

## Acceptance (verbatim)

Acceptance: sweep summary for all window lengths × methods; NN sweep at 1 s; dynamic
stopping best-threshold table; pseudo-online summary for 5 and 6 classes; causal-filter
test passes. No preserved reference numbers (R-16) — record and interpret
(accuracy/ITR trade-off vs window length).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-31 | mas/05_PITFALLS.md | `compact_cnn` (P09 class) vs `compact_eegnet` (`EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2)`): distinct names in every table |
| PF-32 | mas/05_PITFALLS.md | early-stopping validation = 20 % of the training trials (grouped), never the test fold |
| PF-38 | mas/05_PITFALLS.md | pseudo-online: stateful causal SOS filter with carried `zi`, fixed-clock windows, MARK only for scoring |
| PF-39 | mas/05_PITFALLS.md | warn on OO vs C paradigm mismatch (here OO → mOO) |
| R-16 | mas/04_REFERENCE_RESULTS.md | no preserved numbers; reviewer checks direction (accuracy rises with window length, ITR peaks at short windows) |
| §2, §6 | mas/02_REQUIREMENTS.md | module paths; CSV schemas of `reports/window_sweep/`, `nn_sweep/`, `dynamic_stopping/`, `pseudo_online/` |
| B003 | mas/state/blockers/ | cohort: P20 uses S01–S05 under both options (decision row) |
| decisions P17 C-b, C-c; P19 C-1, C-2, C-3 | mas/state/decisions.md | carry-forwards assigned below |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| deep-learning | P20.3, P20.4, `fit_network` and `cnn_fold` used by P20.2 | `03_changes_deep-learning.md` |
| ml-engineer | P20.2 (FBCCA vectorized, `lda_fold`, `summarize`, predictions/confusion), P17 C-b, C-c | `03_changes_ml-engineer.md` |
| data-signal | P20.1 (sweep data via `build_windows`, no new code expected), P20.5, P20.6, P19 C-1, C-2 | `03_changes_data-signal.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P20.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
