# P20 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Treat SSVEP as detection:

- accuracy and ITR against window length (0.5–4 s, stride 0.25 s) for FBCCA, in-fold
  FBCSP+FBCCA LDA and a CNN;
- an NN sweep at 1 s (CCNN, compact_eegnet, eegnet) with grouped early stopping;
- dynamic stopping on the window-level probabilities;
- a causal pseudo-online detector trained on OO and replayed on mOO, for 5 and 6 classes.

R-16: no numeric target. The reviewer checks direction: accuracy rises with window length,
and ITR peaks at short windows.

## Data source

- Sweep: `data/processed_continuous/w<len>_s0.25/<S>/` (roadmap path). Each folder is built
  by `scripts.build_windows`:
  - `--filter-mode continuous --banks fbcca fbcsp --quality-source both --stride-sec 0.25`;
  - one command per window length 0.5, 1, 1.5, 2, 3, 4 s.
  - The subject folders `data/processed_continuous/S0*` (P16) stay untouched. The verifier
    hashes `data/processed_continuous/S0*` only (65 files) before and after.
- Pseudo-online:
  - recordings `OO` (train) and `mOO` (test) of each subject, read only by the project
    script;
  - MARK channel only for scoring (PF-38).
- Subjects: S01–S05 (B003; see settled point 1).

## Settled points (inferred; recorded in decisions.md)

1. **B003.** Options A and B both use S01–S05 up to P20, so P20 proceeds on S01–S05. B003
   stays open for Sebastian and must be resolved before P21 opens.
2. **Quality source (P19 C-3).**
   - Every `build_windows` command passes `--quality-source both`, the config default since
     P19; P19 showed it differs from `filtered` by one borderline window.
   - Pseudo-online test windows are judged by the window-tier Vpp/std limits on the
     checked signals (causal-filtered and raw window). There is no artifact guard online,
     because the guard needs future samples.
   - Rejected test windows are counted in `Windows rejected (%)`.
3. **Classes.**
   - The sweep, NN sweep and dynamic stopping use the 5 stimulus classes 101–105.
   - 201/202 are excluded there.
   - The 6-class variant is pseudo-online `--rest-class` only.
4. **CV (R1, R2).**
   - `StratifiedGroupKFold(5, shuffle=True, random_state=42+r)` with `groups` = true trial
     ids. Overlapping stride-0.25 windows of one trial never split across folds.
   - FBCCA does not train: it is evaluated once on all windows, reported with `Runs = 1`
     and SD 0. `Train Acc` stays empty for FBCCA.
   - `lda` runs `--cv-repeats 5`; `cnn` runs `--cnn-repeats 1` (5 folds).
   - No smoothing in the sweep (roadmap).
5. **ITR.**
   - Wolpaw, N = 5, with T = window + 0.5 s gaze shift.
   - P ≤ 1/N gives 0; P = 1 uses the limit (log2 N bits).
   - Dynamic stopping uses T = decision time + 0.5 s.
6. **Sweep `cnn` = `compact_eegnet`.** That is `EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2,
   dropout=0.5)` at the real fs. It is labelled `cnn (compact_eegnet)` in every table
   (PF-31), and P09's `CompactCNN` is labelled `compact_cnn`.
7. **`fit_network` (PF-32, R2).**
   - Validation: inner `StratifiedGroupKFold(round(1/0.2) = 5)` on the training trials;
     the first split is the 20 % validation set.
   - Augmentation on training windows only, reusing the P10 augmentations; `--no-augment`
     turns it off.
   - Optimiser: AdamW (lr 0.001 and batch 16 from `configs/pipeline_config.yaml`; weight
     decay at the torch default 0.01).
   - Schedule: cosine over max 150 epochs, label smoothing 0.1, patience 25, keep the
     state with the best validation loss.
   - Input normalisation statistics come from training windows only.
   - Report train/val accuracy and best epoch.
   - The roadmap leaves weight decay and the label-smoothing amount unspecified; the
     values above are the inferred defaults.
8. **Channels.** Use the channels kept by each subject's shared gate. PO7 is dropped for
   S01/S03/S04, so never hardcode the count.
9. **Dynamic stopping (R8).**
   - Input is the per-window class probabilities of `lda` and `cnn` from the sweep's
     `predictions.csv`, one row per test window per run, with trial id and offset.
   - Per run and trial, windows are ordered by (trial, offset) and those with
     offset < skip are dropped.
   - The decision is taken at the first cumulative mean max ≥ threshold, otherwise forced
     at the last window; time = offset + window length.
   - FBCCA is skipped because it gives correlations, not probabilities.
   - The best threshold per method and window is chosen by ITR and reported as a
     selection over 6 thresholds (no held-out claim).
10. **Pseudo-online (PF-38, PF-39).**
    - Training:
      - causal SOS band-pass 1–90 Hz order 4, plus a 60 Hz notch with Q 30 (config), on the
        OO run;
      - windows and the shared quality gate (source `both`);
      - CCNN with `fit_network`.
    - The rest class (`--rest-class`) is trained on `REST_SEC = 5 s` before each target.
    - Test:
      - mOO is replayed in stride-sized chunks through the same SOS cascade with carried
        `zi`, initialised as `sosfilt_zi · x[0]`;
      - windows on a fixed clock;
      - label-free channel check on the first 30 s: a channel failing the channel tier is
        dropped and the model retrained without it;
      - fallback retrain at 1 s if val acc < 50 %.
    - A train/test paradigm warning is printed when the paradigms differ; OO → mOO prints
      none unless the paradigm family differs.
    - Output: `summary_<tag>.csv` and `decisions_<tag>.csv` (`02_REQUIREMENTS.md` §6).
11. **Device and seeds.** `DEVICE: auto` (local RTX 3050, 4 GB), seed 42, CNN seeds 42+r.
12. **Carry-forwards.**
    - ml-engineer:
      - P17 C-b: `fail_fraction` required in `evaluate_subject`;
      - P17 C-c: 6-class data-source console line.
    - data-signal:
      - P19 C-1: `demo_edge_effects.py` passes `--quality-source filtered` explicitly;
      - P19 C-2: `src/io/subject_data.py` raw count `& ~keep_local`, plus a
        `shared-no-guard` test.
    - P17 C-d (ablation) and C-e (rates by position) stay open questions.

## Work split (order: 1 first; then 2 and 3 in parallel, disjoint files)

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | deep-learning | NEW `src/models/cnn/ccnn.py`, NEW `src/models/cnn/training.py` (`fit_network`, `cnn_fold(X_tr, y_tr, groups_tr, X_te, fs, n_classes, model, seed, device, augment) -> dict(proba, train_acc, val_acc, best_epoch)`), NEW `scripts/benchmarks/neural_networks/benchmark_nn_sweep.py` | P20.3, P20.4; settled 6–8, 11 |
| 2 | ml-engineer | NEW `scripts/benchmarks/benchmark_window_sweep.py`, MODIFIED `src/features/ssvep/fbcca*.py` (vectorized `reference_bases`/FBCCA) as needed, MODIFIED `benchmark_n_subjects.py` (C-b, C-c) | P20.2; settled 3–6; imports `cnn_fold` |
| 3 | data-signal | NEW `scripts/benchmarks/simulate_dynamic_stopping.py`, NEW `scripts/benchmarks/pseudo_online.py`, NEW `src/online/causal_filter.py` (stateful SOS), MODIFIED `scripts/diagnostics/demo_edge_effects.py`, `src/io/subject_data.py` | P20.1 (commands only), P20.5, P20.6; settled 2, 9, 10; C-1, C-2 |

Each builder does a smoke run of under 5 min (one subject, one fold, or synthetic) and
gives **measured** per-unit times, so the verifier's runtime table is real.

## Methodological risks

- **R1 leak through overlap.** At stride 0.25 s, windows of one trial overlap by up to
  94 %. A window-level split would leak. Grouped folds by true trial id are required, and
  the test proves no trial id spans train/test.
- **PF-32.** The early-stopping validation set is drawn from training trials only.
- **R2.** CSP, scaler and normalisation statistics are fitted in-fold.
- **ITR selection bias.** The best threshold or window is chosen on the same data. Report
  it as descriptive.
- **PF-38.**
  - The online filter must be causal and stateful.
  - Chunked filtering must equal one-pass `sosfilt` on the whole stream (this is the
    causal-filter test in the acceptance).
  - No zero-phase filtering on the test stream; no future samples in any window.
- **Class balance.** Windows per trial fall with length (17 at 1 s, 5 at 4 s). Report
  `Windows`, `Trials` and balanced accuracy.
- **GPU memory.** 4 GB: the batch size and windows at 4 s must fit.

## Tests required (known answers)

1. **FBCCA vectorized.**
   - A planted sinusoid at each stimulus frequency is classified correctly.
   - It equals the loop reference (per-band CCA, sklearn or a direct SVD) to 1e-10.
   - Correlations lie in [0, 1]; the references are orthonormal (QᵀQ = I).
2. **ITR.**
   - Known values: N = 5, P = 1, T = 1.5 s gives log2(5) · 60 / 1.5.
   - P ≤ 0.2 gives 0.
3. **Grouped CV.** No trial id appears in both train and test, for every fold and repeat,
   on overlapping synthetic windows.
4. **CCNN.**
   - Output shape and nfft = max(T, fs/0.25).
   - The bins span [3, 50] Hz.
   - Learns planted sinusoids on synthetic data above chance in a few epochs (CPU).
5. **`fit_network`.**
   - The validation trials are a subset of the training trials and disjoint from the test
     set.
   - The best-validation-loss state is restored (planted loss curve).
6. **Dynamic stopping.** Hand-built probability sequences give the known decision window,
   time and forced flag. Windows are given out of order to check the (trial, offset) sort.
7. **Causal filter.**
   - Chunked `sosfilt` with carried `zi` equals one-pass `sosfilt` (≤ 1e-10).
   - An impulse at t0 leaves every sample before t0 untouched.
8. **Pseudo-online clock.** On a synthetic stream with a known MARK, the window starts are
   on the fixed grid and decisions fall in the right stimulus periods.
9. **C-1, C-2.** The demo passes `filtered`; the counts under `shared-no-guard` sum to
   total − valid.

## Run commands (for the verifier, in order; runtimes from the builders' smoke runs)

```bash
P=".venv/bin/python -m"
# 0. hash data/processed_continuous/S0* (before)
# 1. sweep data (one per window length)
for W in 0.5 1 1.5 2 3 4; do $P scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp --quality-source both --window-sec $W --stride-sec 0.25; done
# 2a. window sweep, classical part (≈ 2 min)
$P scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 0.5 1 1.5 2 3 4 --stride 0.25 --methods fbcca lda --cv-repeats 5 --out-dir reports/window_sweep
# 2b. window sweep, cnn part (≈ 80–120 min GPU; human-run candidate) — merges into the same out-dir
$P scripts.benchmarks.benchmark_window_sweep --data-root data/processed_continuous --windows 0.5 1 1.5 2 3 4 --stride 0.25 --methods cnn --cnn-repeats 1 --out-dir reports/window_sweep
# 3. NN sweep at 1 s
$P scripts.benchmarks.neural_networks.benchmark_nn_sweep --data-root data/processed_continuous --windows 1 --models ccnn compact eegnet --out-dir reports/nn_sweep
# 4. dynamic stopping
$P scripts.benchmarks.simulate_dynamic_stopping reports/window_sweep/predictions.csv --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5 --out-dir reports/dynamic_stopping
# 5-6. pseudo-online, 5 and 6 classes
$P scripts.benchmarks.pseudo_online --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --tag ccnn_5class
$P scripts.benchmarks.pseudo_online --train-session OO --test-session mOO --model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --rest-class --tag ccnn_6class
# 7. hash data/processed_continuous/S0* (after)
```

Final CLIs copied from the three handoffs (2026-10-28). Measured estimates: builds < 1 min (≈ 4.3 GB), 2a ≈ 2 min, 2b ≈ 80–120 min, 3 ≈ 20–31 min, 4 seconds, 5–6 ≈ 2.5 min, suite ≈ 13.5 min. Order for the verifier: 0, 1, 2a, 3, 4 (on lda; re-run after 2b), 5, 6, 7; 2b and the dynamic-stopping re-run are the human-run request if 2b does not fit the remaining budget.

**Budget.** `LOCAL_RUN_BUDGET_MIN` 120 and `MAX_GPU_HOURS_PER_PHASE` 2.
- The sweep CNN (6 lengths × 5 subjects × 5 folds) and the NN sweep (3 models × 5 × 5)
  dominate.
- If the measured estimate exceeds the budget, the verifier runs commands 0–1, the sweep
  without `cnn`, dynamic stopping on `lda`, and pseudo-online. The CNN parts become a
  human-run request (local terminal, exact commands, expected runtime, outputs into
  `reports/window_sweep/` and `reports/nn_sweep/`).

### Pre-run audit additions (07_review.md db474b6, copied verbatim)

#### Binding run-list items (copy verbatim into 02_plan.md, "Run commands" / "Acceptance checks")

> **A (R5).** Commands 5 and 6 pass the quality source explicitly: append `--quality-source both` to both `scripts.benchmarks.pseudo_online` commands. 05_run.md quotes the console line `quality source both, limits {...}, channel fail fraction ...` of each run.
>
> **B (disk, stale outputs).** Before command 1: `df -h` of the run checkout shows ≥ 8 GB free; `reports/window_sweep/`, `reports/nn_sweep/`, `reports/dynamic_stopping*/`, `reports/pseudo_online/` and `data/processed_continuous/w*_s0.25/` do not exist in the run checkout (the window sweep MERGES into existing files and would keep stale cells). If any exists, stop and report; do not delete by hand.
>
> **C (order and dynamic stopping out-dirs).** Order: 0, 1, 2a, 3, 4a, 5, 6, [S], 2b, 4b, 7. Command 4a = command 4 with `--out-dir reports/dynamic_stopping_lda` (run after 2a, lda only). Command 4b = command 4 as written (`--out-dir reports/dynamic_stopping`), run only after 2b has merged all six cnn windows. The rows with `Method == lda` of `per_subject.csv` must be identical between `reports/dynamic_stopping_lda/` and `reports/dynamic_stopping/` (pandas `equals` after sorting; quote the command and `True`).
>
> **S (stop rule for 2b, binding).** After command 6, compute (shown Python command, numbers in 05_run.md): `T_A` = cumulative wall minutes of all commands run so far (from their logs); `P_2b` = 7.0 × (sum of `Seconds` of the `compact_eegnet` rows of `reports/nn_sweep/folds.csv`) / 60. Run 2b locally only if `T_A + P_2b + 3 ≤ 120`. If run locally, run 2b as six invocations, one per window length in the order 0.5, 1, 1.5, 2, 3, 4 (same flags, `--windows <L>`; the merge is per cell), and before each invocation check `elapsed + P_2b × share_L ≤ 117` with share_L = 0.099, 0.143, 0.186, 0.207, 0.211, 0.155; on the first failed check stop. Every window length not run locally, plus command 4b, becomes the human-run request (local terminal, RTX-class GPU; exact per-window commands; expected runtime = P_2b × remaining shares; outputs dropped into the same `reports/window_sweep/`, then 4b). No local run may push the cumulative time past 120 min or the GPU time past 2 h. While 2b or 4b is pending, acceptance checks 1 and the cnn part of 3 are marked PENDING-HUMAN, not PASS.
>
> **D (merge integrity).** Before the first 2b invocation and after the last, record the sha256 of the `fbcca`+`lda` rows of `reports/window_sweep/summary.csv` and `predictions.csv` (pandas: filter `Method`/`method` != `cnn (compact_eegnet)`, sort by all key columns, `to_csv(index=False)` → sha256). Both hashes unchanged.
>
> **E (cnn = compact_eegnet at 1 s).** If 2b's 1 s cell runs on the same machine as command 3: per subject, `Acc (%)` of `cnn (compact_eegnet)` at 1 s in `reports/window_sweep/summary.csv` equals `compact_eegnet` in `reports/nn_sweep/summary.csv`, and the max |Δp| of the joined predictions (subject, trial_id, offset_sec) is ≤ 1e-4. Any difference on the same machine is an anomaly in 05_run.md. On different machines, report the difference as cross-machine non-determinism.
>
> **F (sweep invariants).** From `reports/window_sweep/summary.csv`: Runs = 1 (fbcca), 5 (lda), 1 (cnn); per subject and window, `Windows` and `Trials` equal across the three methods; `Windows ≤ Trials × ((5 − L)/0.25 + 1)`. From the build logs: channels kept per subject at each of the six lengths (list them); a subject whose kept channels differ between lengths is flagged in 05_run.md.
>
> **G (dynamic-stopping invariants).** Per (Subject, Method, Window): `Mean Time (s)` and `Forced (%)` are non-decreasing in the threshold; the minimum `time_sec` in `decisions.csv` is ≥ 0.5 + L; `fbcca` absent; `Skipped trials` total quoted.
>
> **H (causal-filter test named).** `.venv/bin/python -m pytest tests/test_p20_online.py -v -o addopts="" -k causal_filter` shows `test_causal_filter_chunked_equals_one_pass_and_is_causal PASSED`; quote the line (acceptance check 5; `-q` does not name tests).
>
> **I (pseudo-online consistency).** Per subject, `Channels kept` equal in `summary_ccnn_5class.csv` and `summary_ccnn_6class.csv` (else flag the subject); `Fallback`, `Dropped at check`, `Trials before check` quoted per subject; no PF-39 warning line in either log (OO → mOO).

#### A-priori directions (pre-committed; copy verbatim into 02_plan.md)

Each is checked per subject and on the cohort mean; "holds", "fails" or "inconclusive" is reported, never re-worded after the numbers exist. Single-repeat CNN cells carry no seed-variance estimate.

> **P1 (accuracy vs window length).** For `fbcca` and `lda`, the cohort-mean accuracy rises strictly from 0.5 to 1 to 1.5 to 2 s, and from 2 to 3 to 4 s does not fall by more than 1 pp (ceiling). Per subject and method, at most one decrease > 2 pp between consecutive lengths. For `cnn (compact_eegnet)` only the endpoints are committed: cohort Acc(4 s) > Acc(0.5 s) (training windows per trial fall from 19 to 5, so no monotonicity is claimed).
>
> **P2 (ITR peak).** For every method, cohort-mean ITR at 4 s is below its maximum over lengths; for `lda` the cohort maximum lies at L ≤ 1.5 s; per subject (lda) the ITR peak of S03, S04, S05 lies at L ≤ 1.5 s, and the peaks of S01 and S02 lie at a length ≥ the shortest peak among S03–S05 (lower SNR shifts the optimum to longer windows).
>
> **P3 (methods).** `lda` ≥ `fbcca` on the cohort mean at every length, and in ≥ 4 of 5 subjects at 1 s and at 2 s. No direction between `cnn (compact_eegnet)` and `lda`; `cnn` above `lda` by ≥ 5 pp on the cohort mean at any length is a surprising gain and triggers a leak check (R1 guard logs, validation-trial disjointness) before it is reported.
>
> **P4 (NN sweep, 1 s).** Every model above chance (20 %) on the cohort mean. Committed ordering: `ccnn` ≥ `eegnet` on the cohort mean (0.25 Hz complex spectrum vs a 2,389-parameter temporal model). No ordering committed for `compact_eegnet`. Mean `Train Acc (%)` ≥ mean `Val Acc (%)` for every model.
>
> **P5 (dynamic stopping).** Invariants G hold. For `lda`, at `Threshold` 0.5, `Forced (%)` ≤ 10 % for S03, S04, S05 (confident probabilities at high SNR). Against the roadmap's fixed-window ITR at the same L: no direction (that ITR uses T = L + 0.5 s although its accuracy pools windows at every offset 0…5 − L, while dynamic stopping cannot decide before 0.5 + L). Committed direction only against the time-matched comparator (R-P6): for `lda` at L = 0.5 s and 1 s, the cohort best-threshold ITR ≥ the time-matched single-window ITR.
>
> **P6 (pseudo-online, 5 vs 6 classes).** (a) `False act. (%)` lower with 6 classes than with 5 in every subject with ≥ 1 scored rest period. (b) `Acc (%)` with 6 classes ≤ 5 classes in ≥ 4 of 5 subjects. (c) The 5-class accuracy ranks S03, S04, S05 above S01 and S02 (each of S03-S05 above each of S01-S02). No direction for `Time (s)`.

#### Reporting rules (copy verbatim into 02_plan.md; the scribe applies them)

> **R-P1.** Per-subject tables for every window × method, unsmoothed (roadmap P20.2), with the data source "continuous build `data/processed_continuous/w<L>_s0.25/`, shared quality (source both), OO session"; pseudo-online "OO → mOO, causal stream replay, window tier without guard, session files".
> **R-P2.** `Acc SD` = 0 with `Runs` = 1 (fbcca, cnn, NN sweep) means "not estimated", never "no variance". FBCCA is evaluated without CV because it fits nothing.
> **R-P3.** Sweep ITR is a window-level ITR (Wolpaw, N = 5, T = L + 0.5 s, accuracy pooled over overlapping windows at all offsets); state that it is not a trial-level online rate.
> **R-P4.** The best threshold (6 values) and the best window (6 lengths) are selected on the same data they are reported on: "selected in-sample, descriptive"; never the system's ITR.
> **R-P5.** A difference between methods or models is called a difference only if the cohort means differ by ≥ 3 pp and ≥ 4 of 5 subjects have the same sign; otherwise "not distinguishable (single CNN repeat)".
> **R-P6.** Time-matched comparator for dynamic stopping, computed read-only from `reports/window_sweep/predictions.csv`: per subject, method and L, the accuracy of the windows with `offset_sec == 0.5` and ITR with T = 0.5 + L + 0.5 s; shown next to the dynamic-stopping row.
> **R-P7.** The pseudo-online channel check is named "test-time label-free channel check (first 30 s of the test stream)"; cross-session pseudo-online numbers are not compared with within-session CV numbers as a gain or loss of a method. The `Mean` row is the mean of per-subject values; subjects with `Fallback` = 1 are named (the `Mean` row's `Window (s)` is the first subject's).
> **R-P8.** For subjects with `Dropped at check` > 0: accuracy also reported without the stimulus periods with `onset_sec` < 30 s (read-only from `decisions_<tag>.csv`); for subjects with 0 the check changes nothing.
> **R-P9.** The rest segment is [o − 5 s, o) = fixation + cue (target presentation) + preparation, not P17's fixation-only rest. Report, per subject and pooled, the share of false activations whose `pred` equals the code of the following stimulus period (chance 20 %) and the distribution of their `time_sec` (≤ 2 s fixation, 2–4 s cue, 4–5 s preparation).
> **R-P10.** Weight decay 0.01 and label smoothing 0.1 are "inferred (roadmap unspecified)"; validation loss = plain cross-entropy (builder choice).
> **R-P11.** No R-16 numbers exist; any comparison with P16/P17 numbers names the stride difference (1 s builds vs stride 0.25 s).
> **R-P12.** 5 vs 6 classes accuracy change reported as the decomposition Acc5 − Acc6 = P(correct5, wrong6) − P(wrong5, correct6) over the periods scored in both, with the first term split into "missed" and "wrong class"; never as "≈ Missed".

## Acceptance checks (for the verifier)

1. `reports/window_sweep/summary.csv` has all 6 lengths × 3 methods × 5 subjects, with the
   §6 columns; `predictions.csv` and `confusion.csv` exist.
2. `reports/nn_sweep/summary.csv` at 1 s has 3 models × 5 subjects, with `Val Acc (%)` and
   `Best Epoch`, and the PF-31 names.
3. The dynamic-stopping best-threshold table per method × window, plus
   `decisions/per_subject/cohort.csv`.
4. Pseudo-online `summary_ccnn_5class.csv` and `summary_ccnn_6class.csv` per subject.
5. The causal-filter test passes (named in the suite output).
6. The protected `S0*` hashes are unchanged.
7. Per-subject numbers carry their data source (R9).

## Sources

- `mas/03_ROADMAP.md` P20; `mas/05_PITFALLS.md` PF-31, PF-32, PF-38, PF-39;
  `mas/02_REQUIREMENTS.md` §2, §6.
- `mas/01_DATA_SPEC.md` §5.2; `mas/04_REFERENCE_RESULTS.md` R-16.
- `mas/state/blockers/B003-cohort-beyond-S05.md`; `mas/state/decisions.md` (P17 C-b/C-c,
  P19 C-1..C-3).

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
