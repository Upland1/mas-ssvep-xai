# P20 · 07 · Scientific review

Status: READY (pre-run audit PASS; results review APPROVE)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_* (incl. "Build fix" sections), 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Audited at 092cced (branch phase/P20-detection-online; code last changed at bdf317a; 092cced only touches 02_plan.md and log.md).
Diff main...HEAD for src/, scripts/, tests/, configs/: 23 files, +2903/−23 (`git diff --stat main...HEAD`), configs/ unchanged.
P20 test files re-run by me: `.venv/bin/python -m pytest tests/test_p20_online.py tests/test_p20_window_sweep.py tests/test_p20_independent_known_answer.py tests/test_p20_data_signal.py tests/test_p20_networks.py -q -o addopts=""` → `66 passed in 14.90s`. Full suite per 04_tests.md: `1297 passed, 22 warnings in 781.21s` (log mas/state/scratch/p20_full_suite.log), 18/18 mutants killed.

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | `scripts/benchmarks/benchmark_window_sweep.py:153,167-168` (`groups = d["cv_groups"]`, `make_splits("grouped", ...)`, runtime `assert_no_shared_trials` every repeat); same in `scripts/benchmarks/neural_networks/benchmark_nn_sweep.py` (`run_subject_model`, splits + assert). Stride-0.25 windows of one trial stay in one fold; windows never cross trials (5 s target segments separated by ≥ 10 s of 200/201/202/203, `mas/01_DATA_SPEC.md:97-107`). Tests: window-level `StratifiedKFold` shares trials in 5/5 folds (`tests/test_p20_window_sweep.py`), mutant M1 killed. FBCCA has no fit, so no CV is needed (labelled Runs 1). |
| R2 Fit only in-fold | PASS | CSP in fold `src/models/classical/legacy_eval.py:95` via `lda_fold` (`benchmark_window_sweep.py:104-113`), scaler + LDA in a Pipeline fitted on `tr`. Network: validation = first split of an inner `StratifiedGroupKFold` on training trials (`src/models/cnn/training.py:79-84,104-106`, PF-32); normalisation from fitting windows only (`training.py:107`); augmentation on `Xf` only (`training.py:118`); test windows only normalised and predicted (`training.py:170-173`). Tests: fit-stats spy, test-perturbation invariance, `cnn_fold` spy (04_tests.md rows 6-9), mutants M4/M4b/M4c killed. Pseudo-online: model, normalisation and fallback decision from the training run only (`scripts/benchmarks/pseudo_online.py:310-324,348`). The label-free channel check on the first 30 s of the TEST stream (`pseudo_online.py:180-187,313`) is a test-time, label-free decision: allowed, but must be labelled as such (reporting rule R-P7). |
| R3 Filter continuous, then window | PASS | Sweep and NN sweep read only built `continuous` folders through `load_subject` (`benchmark_window_sweep.py:288`); FBCCA and CSP use saved banks (`:99,164`); CCNN takes an rFFT, no filtering (`src/models/cnn/ccnn.py:41-44`). Pseudo-online (PF-38): causal one-pass SOS on the training run (`pseudo_online.py:152`), stateful chunked SOS with carried `zi` on the test stream (`src/online/causal_filter.py:61-72,81-117`); no `filtfilt`/`sosfiltfilt` in either path. Tests: chunked = one-pass ≤ 1e-10, impulse causality, future-sample replacement leaves earlier windows bit-identical, `sosfiltfilt` fails the causality test (04_tests.md, mutants M2, M13). |
| R4 Estimator small-sample bias | N/A | no coherence/PLV in P20. |
| R5 Shared quality decision, explicit thresholds | PASS (binding run-list item A) | Builds pass `--quality-source both` (02_plan.md command 1). Sweeps: `load_subject(..., "shared", thresholds=..., channel_fail_fraction=...)` (`benchmark_window_sweep.py:288-289`). Pseudo-online passes all four limits explicitly (`pseudo_online.py:113-139`) but commands 5-6 rely on the config default for `--quality-source` (`pseudo_online.py:380,401-402`): item A makes it explicit. P17 C-b (`benchmark_n_subjects.py` `fail_fraction` required) and P19 C-1/C-2 done with tests. |
| R6 Index layouts verified | PASS | CCNN `(B, 2, C, n_bins)`, `[real, imag]/T`, nfft, bin span tested against `np.fft` (04_tests.md, mutants M9, M9b, M10); window `(n, C, T)` and channel subsetting `[:, kept_idx]` (`pseudo_online.py:319,197`). |
| R7 Honest statistics | N/A | no hypothesis tests in P20; all comparisons are descriptive (reporting rules R-P4, R-P5). |
| R8 Smoothing respects trials | PASS | No smoothing in the sweeps (roadmap). Dynamic stopping groups by (subject, method, window, run, trial) and sorts by offset inside the trial, never trusts input order (`scripts/benchmarks/simulate_dynamic_stopping.py:88-91,136-140`); duplicate offsets refused (`:86`). `offset_sec` samples→seconds fixed in both producers (`benchmark_window_sweep.py:141`, NN sweep `run_subject_model`), with tests failing on the old line; the consumer refuses sample-valued offsets (`simulate_dynamic_stopping.py:114-122`). Mutants M3, M3b, M6 killed. |
| R9 Per-subject reporting with data source | PASS (reporting rule R-P1) | `Data source` column in every summary (`benchmark_window_sweep.py:202`, `pseudo_online.py:355`, `simulate_dynamic_stopping.py:223`). R9's 1.0/2.0 s *smoothed* accuracy does not apply: P20 is unsmoothed by roadmap; the 1 s and 2 s rows must be stated as unsmoothed. |
| R10 Every change and test cites a source | PASS (note 4) | Handoff tables cite roadmap/PF/[own]. |
| R10 Copied lines marked, license compatible | N/A | no copied code declared; none seen. |
| R11 Reference consulted only after an attempt | PASS | all four handoffs list "none"; `mas/state/scratch/reference_access.log` has 42 lines, the last from the P19 scribe (07:41), no P20 entry. |
| Golden rule 3: legacy labelled and reachable | N/A | era C, no legacy behaviour prescribed for P20 (00_assignment.md). Legacy FBCCA functions untouched (`src/features/ssvep/fbcca_extraction.py`, additions only). |
| Tests cover every change; ≥ 1 fails on the historical bug | PASS | window-level split, `sosfiltfilt`, zi not carried, offsets in samples, validation from the test fold, last-state restore, `>` vs `>=` (04_tests.md mutants M1-M13). Gaps (04_tests.md): stride-0.25 fixture, fallback/channel-drop only in builders' tests; accepted. |
| Changes match 02_plan.md and roadmap | PASS | P20.1-P20.6 present; deviations declared: 2a/2b method split with deterministic merge; channel check before the single training (equivalent model, `before_check` flag); extra columns. |
| No data, recordings, local tooling or vendor names in the diff | PASS | privacy scan (fragment-built patterns) over `git diff main...HEAD` and `git log main..HEAD` messages: 0 and 0; no data/recording/local-tooling paths among the changed files: 0. |

### Inferred settings and design decisions (checked)

1. **Weight decay 0.01, label smoothing 0.1** (`training.py:37,39`): roadmap gives AdamW and label smoothing without values; 0.01 is the torch AdamW default, 0.1 the common value. Not tuned on test data. Accepted, labelled "inferred" (R-P10).
2. **Validation loss = plain CE** (`training.py:87-90,139`) while training uses smoothing: model selection on the unsmoothed NLL of the training trials' validation split. Sound (the smoothed loss has a floor that blurs the minimum); no leak. Accepted.
3. **Normalisation per channel over fitting windows** (not per window): keeps amplitude for CCNN; R2-correct. Accepted.
4. **Pseudo-online: 30 s check, then one training**: identical to "train, check, retrain" when no channel is dropped at the check; when one is, periods during the first 30 s use a channel decision a live system would not have yet. The script flags only periods that END before 30 s (`pseudo_online.py:251`); a period that starts before 30 s and ends after it also used pre-check windows. Rule R-P8 sets the sensitivity on `onset_sec < check_sec`. Non-blocking.
5. **6-class "no target"**: rest never decides, no forcing, missed counted wrong, Wolpaw N = 5 (`pseudo_online.py:203-223,269-291`). Matches roadmap.
6. **Rest segment = [o − 5 s, o)** = 201 fixation (2 s) + 202 cue "target presentation" (2 s) + 203 preparation (1 s) (`mas/01_DATA_SPEC.md:97-99`). This is the roadmap's REST_SEC and differs from P17's rest class (201 only). The cue may already carry target-related activity; rule R-P9 adds the read-only diagnostic.
7. **Online quality without guard**: required (the guard needs future samples); window tier on causal-filtered and raw windows with explicit limits. Accepted.
8. **ITR**: Wolpaw, N = 5, P ≤ 1/N → 0, P = 1 → log2 N, T = window + 0.5 s (sweeps), T = mean decision time + 0.5 s (dynamic stopping, pseudo-online); four helpers agree (04_tests.md `test_itr_wolpaw_values_across_modules`). Known value checked: `python3 -c` gives log2(5)·60/1.5 = 92.88 bits/min.

### Disk and budget (arithmetic shown)

- Free disk: `df -h .` → 17G free (95 % used). Builds need ≈ 4.3 GB (data-signal measurement) → ≈ 12.7 GB left. Fits; item B adds a guard.
- Times from the handoffs (min): builds < 1-3, 2a ≈ 2-3, 3 = 20.5-30.8, 4 < 0.5, 5-6 ≈ 2.5; 2b = 79.8-119.8.
  `python3 -c` (scratch arithmetic): non-2b total 26.2-39.8 min; with 2b 106.0-159.6 min against `LOCAL_RUN_BUDGET_MIN` 120; GPU 0.38-0.55 h without 2b, 1.71-2.55 h with 2b against `MAX_GPU_HOURS_PER_PHASE` 2. Ratio (2b total)/(2b 1 s cell) = 119.6/17.1 = 6.994; per-window shares 0.5…4 s = 0.099, 0.143, 0.186, 0.207, 0.211, 0.155.
- The NN sweep's `compact_eegnet` at 1 s is the same computation as 2b's 1 s cell (same data, folds, seeds; tested), so its measured time projects 2b. Stop rule: item S.

### Binding run-list items (copy verbatim into 02_plan.md, "Run commands" / "Acceptance checks")

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

### A-priori directions (pre-committed; copy verbatim into 02_plan.md)

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

### Reporting rules (copy verbatim into 02_plan.md; the scribe applies them)

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

### Required fixes

None (code). Item A is a run-list change.

### Non-blocking notes

1. `pseudo_online.py:251` `before_check` marks only periods that end within the check; see R-P8 (onset-based sensitivity).
2. `benchmark_window_sweep.py:262-265,241-243`: with per-window 2b invocations (item S), `sweep_config.json` keeps only the last invocation's `windows` list for cnn. Provenance lives in 05_run.md; the file is not evidence of which windows ran.
3. `pseudo_online.py:458`: the `Mean` row's `Window (s)` copies the first subject's; with a fallback subject the mean mixes lengths (R-P7).
4. R10: `03_changes_ml-engineer.md` names "Bjorck-Golub equivalence" in a Source cell without a citation per `mas/CITING.md`; the scribe either cites it properly (only if opened) or writes "[own]".
5. Window-sweep `summary.csv` has no `Device` column; for a human-run 2b, 05_run.md records machine, GPU, torch/CUDA.

## Results review

Read: 05_run.md, 06_verify.md (PASS, 8fd6cb0), every log in `reports/logs/P20/` named below, and the CSVs
`reports/window_sweep/{summary,predictions}.csv`, `reports/nn_sweep/folds.csv`,
`reports/dynamic_stopping/{per_subject,best_threshold}.csv`, `reports/pseudo_online/{summary,decisions}_ccnn_*.csv`.
What ran equals what I audited: `git diff --stat db474b6 HEAD -- src scripts tests configs` prints nothing (only
phase-folder markdown changed since the audit). The P09/P10 test files and their model code are untouched by P20
(`git diff --stat main...HEAD -- tests/test_p09_compact_shallow.py tests/test_p10_augmentation.py src/models/cnn/`
lists only the NEW `ccnn.py`, `training.py`).

### Numbers recomputed (read-only)

- Cohort means of `reports/window_sweep/summary.csv` (`groupby(['Method','Window (s)'])` mean): all 36 Acc/ITR
  values of the 06 cohort table reproduce exactly (e.g. lda 81.80 / 84.37 at 0.5 s; cnn 83.10 / 21.56 at 4 s).
- `P_2b = 7.0 × 526.1 / 60 = 61.378` (`.venv/bin/python -c "print(7*526.1/60)"`; sum from `nn_sweep/folds.csv`).
- Pseudo-online summaries: every per-subject and Mean value of the 06 table matches
  `summary_ccnn_{5,6}class.csv`. The 6-class ITR uses N = 5 (S04: 84.96 in both tags at Acc 100 %, Time 1.14 s), so
  missed periods count as errors and the rest class earns no bits; the scribe states this.
- `reports/dynamic_stopping/per_subject.csv`: max `Forced (%)` of lda, threshold 0.5, S03–S05 = 0.0 (P5 holds).
- R-P9: 16/55 = 29.09 % (5 classes).

### Verifier point 1: hash-pinned P09/P10 tests (determinism)

Diagnosis (my commands, synthetic smoke only):
`OMP_NUM_THREADS=$t .venv/bin/python -m pytest tests/test_p09_compact_shallow.py::test_eegnet_regression_after_refactor -q -o addopts=""`
for t = 1, 2, 4, 8, 12, 16 gives hashes `017ccd7b…`, `85bc5950…`, `50934fd3…`, `69bfd29b…`, **pass** (pinned
`adf2cc7d…`), `2ae23a96…`. `torch.get_num_threads()` in this venv = 12. The hash of the failed run
(`2ae23a96…`, `pytest_full.log:32,45`) is exactly the 16-thread hash. So the failure is not load-induced randomness:
the CPU EEGNet smoke output is deterministic for a fixed intra-op thread count and differs bit-wise across thread
counts (float reduction order). The first suite run executed with 16 intra-op threads (mechanism not recoverable from
the logs; nothing in `src/ scripts/ tests/ configs/` sets thread counts, `grep -rn "NUM_THREADS\|set_num_threads"`
empty). The pin is therefore valid only for 12 threads on this machine.

Judgement: a test-design fragility of P09/P10 tests, not a determinism defect of P20 code. P20's own determinism
evidence is check E (GPU, same machine: sweep cnn 1 s vs NN-sweep compact_eegnet, max |Δp| = 0.0 over 3329 rows).
No P20 fix; carry-forward C-1 below.

### Verifier point 3: cnn (compact_eegnet) collapse

Per-fold lines (`window_sweep_2b_w4.log:4-17`, `window_sweep_2b_w0.5.log:11-16`):

| Cell | Fold: train % / val % / best epoch / epochs run |
|---|---|
| S02 4 s (Acc 39.56) | f0 29.31 / 25.00 / **1** / 26; f1 100 / 46.67 / 106 / 131; f2 100 / 43.33 / 35 / 60; f3 95.69 / 46.67 / 20 / 45; f4 42.74 / 26.67 / **2** / 27 |
| S02 0.5 s (Acc 42.96) | f0 30.50 / 15.04 / **2** / 27; f1 87.53 / 48.87 / 44 / 69; f2 66.36 / 45.86 / 20 / 45; f3 96.19 / 65.55 / 74 / 99; f4 29.24 / 23.68 / **3** / 28 |
| S01 4 s (Acc 77.00) | train 100 in all folds; val 88.57, 85.71, **57.14**, 97.14, 94.29 |

Cohort-wide, only four folds restored a state from epoch ≤ 5 (`grep -c "best epoch [1-5]/"` per 2b log: w0.5 2,
w1 0, w1.5 0, w2 0, w3 0, w4 2), all S02, at the two endpoint lengths. In those folds the validation loss was lowest
after 1–3 epochs, patience 25 then stopped training, and `fit_network` restored a near-untrained network (train acc
29–43 %, chance 20 %). This is an early-stopping / model-selection artefact on a low-SNR subject with small
validation sets (S02 4 s: 182 windows, ~146 training, ~30 validation of ~6 trials), not a capacity limit of
compact_eegnet at 4 s and not a leak (a leak raises accuracy). S01 4 s is ordinary overfitting with 160 training
windows (one fold val 57 %). The S02 0.5 s cell (42.96 %), which the verifier did not flag, has the same cause and
must be worded the same way. Both 4 s logs (w3, w4) also show a CUDA caching-allocator OOM *warning*
(`window_sweep_2b_w3.log:14`, `w4.log:13`); `training.py` has no OOM handler or CPU fallback, so an unrecovered OOM
would have raised; the folds completed, and this is a non-fatal allocator retry.

Wording (binding for the scribe): "cnn (compact_eegnet) cells for S02 at 0.5 s and 4 s include two folds each in
which early stopping restored the epoch-1–3 state (train accuracy 29–43 %); these cells, single-repeat (no seed
variance, R-P2), measure a failure of the validation-loss early-stopping rule on S02, not the network's accuracy
at those lengths. The cohort cnn drop at 4 s is driven by S02 (39.56 %) and S01 (77.00 %)." Never "CNNs degrade
at long windows". Without S02 the cnn cohort mean is 90.19 % at 0.5 s and 93.98 % at 4 s (lda 87.09 / 98.75); this is
a sensitivity line, not a replacement row (`s[s.Method.str.startswith('cnn') & (s.Subject != 'S02')].groupby('Window (s)')['Acc (%)'].mean()` on
`reports/window_sweep/summary.csv`, same for `lda`).

Effect on conclusions:
- P1 cnn endpoint (83.10 > 80.75) holds as worded, but both endpoints carry the S02 failure; report "holds,
  uninformative about window length". It also holds without S02 (93.98 > 90.19).
- P3 cnn vs lda at 4 s: −14.94 pp with per-subject signs −18.00, −55.60, −1.08, 0, 0 (3 negative, 2 zero). By R-P5
  (≥ 4 of 5 same sign) this is **not a difference**; 06's phrase "cnn is 14.94 pp lower" must carry "not
  distinguishable by R-P5 (3 of 5 negative, single CNN repeat)". At 1 s cnn − lda = +2.19 (5 of 5 positive) is < 3 pp:
  not distinguishable.
- P2 for cnn holds regardless (ITR max at 0.5 s); the dynamic-stopping cnn rows at 4 s (82.34 %, Forced 20.28 %)
  and 0.5 s inherit the failure and carry the same note.
- No fbcca, lda, NN-sweep or pseudo-online conclusion depends on these cells.

### A-priori directions (outcomes as pre-committed, not re-worded)

| Prediction | Outcome | Basis (06_verify.md, CSVs) |
|---|---|---|
| P1 fbcca, lda | holds | strict rise 0.5→2 s; 2→3→4 s no fall > 1 pp; 0 per-subject decreases > 2 pp |
| P1 cnn endpoints | holds (uninformative, see point 3) | 83.10 > 80.75 |
| P2 | holds | 4 s below max for all three; lda cohort peak 0.5 s; lda peaks S03–S05 0.5 s, S01/S02 1.0 s |
| P3 lda ≥ fbcca | holds | every length; 5/5 subjects at 1 s and 2 s; no cnn gain ≥ 5 pp (max +2.19), no leak check triggered |
| P4 | holds | all > 20 %; ccnn 91.25 ≥ eegnet 89.69 (not a difference by R-P5: 2 positive, 1 negative, 2 zero); Train ≥ Val for all |
| P5 | holds | G invariants; Forced 0.0 at thr 0.5 for S03–S05; lda best-threshold vs time-matched 61.53 vs 60.23 (0.5 s), 53.73 vs 53.48 (1 s) |
| P6(a) | **fails as worded** (holds in 4 of 5) | S04 0.0 vs 0.0 with 40 scored rest periods: not lower. Floor effect (no 5-class false activation to remove), but the prediction said "in every subject with ≥ 1 scored rest period", so it fails |
| P6(b) | holds | Acc6 ≤ Acc5 in 5/5 (S04 equal) |
| P6(c) | holds | min(S03–S05) 97.50 > max(S01, S02) 90.00 |

P6(a) is recorded as a failed pre-registered prediction with the reason (floor); the report must not reword it to
"lower or equal". P5's time-matched margin (1.30 and 0.25 bits/min) is smaller than the optimism of choosing the
best of 6 thresholds in-sample while the comparator involves no selection: "holds" is reported with that caveat and
is not evidence that dynamic stopping beats a fixed window.

### Interpretation check

- **Sweep (R-P1–R-P3, R-P11).** Directions accuracy↑ with L and ITR peak at short L hold for every method. ITR is a
  window-level rate (T = L + 0.5 s on windows pooled over all offsets), not a trial-level online rate. No R-16
  numbers exist; stride 0.25 s vs earlier 1 s builds named in any comparison. lda vs fbcca is a difference
  (R-P5) at 0.5–2 s only.
- **Dynamic stopping (R-P4, R-P6).** Thresholds are chosen per method and window on the reported data: "selected
  in-sample, descriptive", never the system ITR; the CSV column `Best (ITR)` is an in-sample flag. Several choices
  sit on the grid edge (cnn 0.5 at 0.5–2 s, the grid minimum; lda 0.95 at 1.5–3 s, the grid maximum), so the
  in-sample optimum may lie outside the grid; state it. Against the roadmap fixed-window ITR, dynamic stopping is
  lower (61.53 vs 84.37 at 0.5 s), which is the comparator's time accounting (pre-run note), not a loss.
- **Pseudo-online 5 vs 6 (R-P7, R-P9, R-P12).** The rest class trades stimulus detection for fewer false
  activations: mean False act. 27.5 → 5.0 %, mean Acc 89.0 → 74.0 %. R-P12 pooled: Acc5 − Acc6 = 15.0 pp = 17.5
  (correct5, wrong6; of which 16.0 missed, 1.5 wrong class) − 2.5 (wrong5, correct6). The drop is almost entirely
  stimulus periods absorbed by the rest class, concentrated in S01 (Missed 50.0 %) and S02 (52.5 %); in S03–S05 the
  cost is ≤ 5 pp with false activations → 0. Words: "the 6-class detector converts false activations into missed
  stimulus periods in low-SNR subjects", never "6 classes is worse/better" without both numbers. ITR6 uses N = 5
  (above). R-P9: every false activation in both tags occurs at `time_sec` ≤ 2 s into the [o − 5, o) segment, i.e. in
  the fixation part, not during the cue (2–4 s); the cue-contamination concern of the pre-run audit is therefore not
  supported by timing. The next-target share is 29.1 % (16/55, 5 classes; one-sided binomial vs 20 %, p = 0.069) and
  60 % (6/10, 6 classes; p = 0.0064), `scipy.stats.binomtest(...,alternative='greater')`; post hoc, n = 10:
  descriptive only, no mechanism claimed. Pseudo-online accuracies are cross-session period-level decisions and are
  not compared with within-session window-level CV (R-P7). The channel check dropped nothing (`Dropped at check` 0);
  R-P8 not applicable; no fallback subject.
- **R9.** Every per-subject table carries its data source (sweep, NN sweep, dynamic stopping: "continuous build
  (w<L>_s0.25/<S>), session OO"; pseudo-online: "OO->mOO …, session files"); the sweep reports 1.0 s and 2.0 s per
  subject (unsmoothed by roadmap design, which the scribe states instead of "smoothed").
- **R11.** Access log 42 lines, last entry P19 scribe (07:41:21); no P20 entry; handoffs state none. Consistent.
- **Traceability.** Every number above comes from the named CSV/log or a shown command; 06's derived values come
  from `reports/logs/P20/analysis_*.txt`.

### Accepted deviations (copy into decisions.md)

| ID | Deviation | Why accepted |
|---|---|---|
| D-1 | First full-suite run `2 failed, 1295 passed` (P09/P10 EEGNet hash pins); isolated re-run `1297 passed` | Cause shown: the pinned hash is the 12-thread output; the failed run used 16 intra-op threads (hash `2ae23a96…` = 16-thread hash). P09/P10 code unchanged by P20. Not a P20 defect |
| D-2 | P6(a) fails as worded (S04 0.0 vs 0.0) | Pre-registered; recorded as failed with the floor-effect reason; holds in 4 of 5 |
| D-3 | cnn (compact_eegnet) S02 cells at 0.5 s and 4 s are early-stopping failures (two folds each restored epoch 1–3); S01 4 s overfitting | Single-repeat cells reported with the binding wording above; no conclusion rests on them; cnn vs lda at 4 s not a difference by R-P5 |
| D-4 | Dynamic-stopping thresholds selected in-sample, several at the grid edge | Pre-registered as descriptive (R-P4) |
| D-5 | CUDA allocator OOM warnings in 2b w3/w4 logs | Non-fatal allocator retry; no fallback path exists; folds completed, check E exact at 1 s |
| D-6 | `sweep_config.json` holds only the last 2b invocation's window list | Pre-run note 2; provenance in 05_run.md |

### Carry-forwards

| ID | Owner | Lesson / action |
|---|---|---|
| C-1 | synthetic-tester (next phase touching tests) | Bit-exact CPU hash pins (`EEGNET_SMOKE_PROBA_SHA256` and any similar) depend on the intra-op thread count. Pin inside a fixed `torch.set_num_threads(1)` context (restored after), re-derive the hash from `main` code (P09 lesson), and add a tolerance comparison of `proba` as the semantic check. Verifier: run the full suite alone and record `torch.get_num_threads()` |
| C-2 | deep-learning (P21+ CNN/GNN) | Log and flag folds whose restored best epoch ≤ 5 or whose restored train accuracy < chance + 10 pp; report the count per cell. Any rule change (min epochs before selection, larger validation share) is a pre-registered method change, not a retro-fix of P20 |
| C-3 | orchestrator / reviewer | CNN cells with 1 repeat cannot separate an optimisation failure from seed variance; when a single CNN cell drives a cohort change > 5 pp, request ≥ 3 repeats of that cell before interpreting it |
| C-4 | scribe | Dynamic-stopping thresholds at the grid edge are named as such; ITR6 uses N = 5 |
| C-5 | open (P17 C-d, C-e; B003) | P17 ablation and rates-by-position questions stay open; B003 must be resolved before P21 opens |

### Binding items for the scribe (mas/state/reports/P20.md)

1. Point 3 wording verbatim; S02 0.5 s cell named as well as 4 s; sensitivity line without S02 labelled as such.
2. P6(a) "fails as worded (S04 0.0 vs 0.0, floor)"; P1 cnn "holds, uninformative".
3. cnn vs lda at 4 s and ccnn vs eegnet: "not distinguishable (R-P5, single CNN repeat)".
4. Dynamic stopping: "selected in-sample, descriptive", grid-edge thresholds named, time-matched margin caveat.
5. Pseudo-online: both accuracy and false-activation changes, R-P12 decomposition, R-P9 timing result, ITR6 N = 5,
   no cross-session vs within-session comparison.
6. Pre-run note 4 (R10, "Bjorck-Golub equivalence") still applies.

### Sources spot-check

Opened this run: `mas/state/phases/P20-detection-online/02_plan.md` (settled points 4, 5, 7, 9, 10; A–I, S, P1–P6,
R-P1–R-P12), `05_run.md`, `06_verify.md`, `src/models/cnn/training.py:70-176` (`predict_proba`, `fit_network`
best-state restore, no OOM handler), `scripts/benchmarks/benchmark_window_sweep.py:245-262` (device, cudnn
deterministic), `scripts/benchmarks/pseudo_online.py` lines 73, 150-161, 209-223, 244-262 (REST_SEC segment,
`time_sec` = offset + window), `tests/test_p09_compact_shallow.py:23,94-97`. No reference code opened; no external
source cited.

Verdict: APPROVE
ACCEPT in the first commit was the orchestrator's wording; the contract term is APPROVE.

## Questions
