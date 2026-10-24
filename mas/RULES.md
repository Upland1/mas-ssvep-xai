# Project rules R1–R11, era matrix and reference targets

Every agent applies these rules and cites them by number (`R3`). The rules
come from the original project's bug history; `AGENTS.md` golden rules 1–10
take precedence, and `mas/05_PITFALLS.md` (`PF-x`) documents each historical
bug in detail.

## Era matrix

The scientific reviewer checks every phase against these, by number. Golden
rule 3 of `AGENTS.md` makes some of them **deliberately violated in early
phases** to reproduce history. The era matrix below says from which phase each
rule is enforced. Before that phase, the legacy behaviour is *required*, must
be labelled `legacy` in code and reports, and must stay reachable behind a
flag or a frozen snapshot after the fix lands. The reviewer marks such rows
`LEGACY (by design)`, not `FAIL`; a legacy violation that is *not* the one the
roadmap prescribes is still a `FAIL`.

| Rule | Enforced from | Legacy behaviour before that (prescribed by the roadmap) |
|---|---|---|
| R1 Trial-grouped CV | P11 | plain `StratifiedKFold(5, shuffle, 42)` over windows (P04–P10) |
| R2 Fit only in-fold | always | full-data fits allowed only for visualization/export (P04 XAI and final models, P05 `extract_fbcsp_features`), labelled as such |
| R3 Filter continuous, then window | P16 (P13 for phase) | per-window sub-band filtering; Hilbert phase reproduced as a bug demo in P13 |
| R4 Estimator small-sample bias | P12 | averaged per-window coherence, only inside the P12 bug diagnostic |
| R5 Shared quality decision | P16 | per-script gates; `vpp_min` regression reproduced in P07 (PF-07) |
| R6 Index layouts verified | always | contiguous MVAR slicing only inside the P13 bug diagnostic |
| R7 Honest statistics | P13 (trial-level permutations at the end of P13) | window-level permutations, first P13 run only |
| R8 Smoothing respects trials | P11 | 2-tap smoothing without trial reset (P04–P10) |
| R9 Per-subject reporting with data source | always | — |
| R10 Cite every source | always | — |
| R11 Reference code after an attempt | always | — |
| fs from metadata (not a numbered rule) | P16 | `fs=250` assumed in features |

## Rules

**R1. Trial-grouped CV.** `StratifiedGroupKFold(n_splits=5, shuffle=True,
random_state=42)` with `groups=trial_ids` (true ids in built folders;
`build_trial_ids` on legacy folders, computed before QC rejection and indexed
with the same mask as the windows). Never `StratifiedKFold`, `KFold` or
`train_test_split` over windows outside the legacy phases. In LOSO the group
is the subject, and nothing from the held-out subject reaches any `.fit()`.

**R2. Fit only in-fold.** Scalers, CSP filters, feature selection, PCA,
normalization statistics, early-stopping validation splits, hyperparameter
choices and augmentation use the training fold only.
*Exception — unsupervised test-time normalization* (`lda_subjnorm`, the GNN
`_subjnorm` variants, P21–P23): allowed only if (a) no test labels are used,
(b) the method name and write-up label it as test-time normalization, and
(c) the write-up states where the statistics came from (whole session =
offline upper bound; first K trials = online, `benchmark_loso_warmup.py`).

**R3. Filter continuous signals, then window.** From P16, new work uses built
folders with `filter_mode = continuous` and passes saved bands
(`subband_windows=...`) to extractors. No `filtfilt` or Hilbert on short
windows outside the legacy path. Phase connectivity takes phase from the
cross-spectral density.

**R4. Small-sample bias.** Concatenate a condition's clean windows and
estimate once; never average per-window coherence/PLV. Stimulus-vs-baseline
uses the baseline re-scored in the stimulus band.

**R5. One quality decision, explicit thresholds.** From P16:
`load_subject(..., quality_mode="shared")` and `quality=d["quality"]` to the
extractors. Always pass every threshold of a shared helper explicitly.

**R6. Verify index layouts.** Every flatten/reshape of parameters (MVAR
coefficients, CSP filters, adjacency matrices, `(window, band, channel, time)`
arrays) is proven by a synthetic case with a known answer.

**R7. Honest statistics.** Trial-level permutations with observed group sizes;
global p, edge-level FDR and NBS reported as separate criteria; a result that
flips across p = 0.05 between permutation counts is inconclusive.

**R8. Smoothing respects trials.** The 2-tap causal smoothing only averages a
window with the previous window of the same trial (`trial_ids` in built
folders; `i % 5` on legacy). Built-folder window offsets restart at 0 in each
trial: sort by (trial, offset), never by offset alone.

**R9. Per subject, with data source.** Report 1.0 s and 2.0 s smoothed
accuracy for every subject, never only the mean, and state the data source
(legacy, per_window build, continuous build, window sweep; session file).

**R10. Cite every source** per `mas/CITING.md`.
Only cite what was opened in this run.

**R11. Reference code after an attempt.** `reference/ssvep-eeg-xai/` is
governed by `REFERENCE_POLICY` in `mas/state/config.yaml` and `AGENTS.md`
rule 8. Default `after-attempt`: open it only after your own implementation
and synthetic test exist and the test fails or the result deviates beyond
tolerance after one investigation round, or to verify a finished, passing
implementation. List every consultation in your handoff file. Never copy
whole functions; never write inside `reference/`. Every access is logged to
`mas/state/scratch/reference_access.log`; the verifier cross-checks it.

## Reference targets

The original's leak-free flagship (FBCSP m=1 + FBCCA → in-fold scaler →
Shrinkage-LDA, legacy folders, fs 250) is **R-6**, the P11 acceptance
target, not a baseline of this repository:

| Subject | 1.0 s | 2.0 s |
|---|---|---|
| S01 | 61.00% | 67.50% |
| S02 | 56.12% | 61.73% |
| S03 | 86.80% | 90.36% |
| S04 | 97.46% | 97.97% |
| S05 | 95.00% | 95.50% |
| Mean | 79.28% | 82.61% |

All reference numbers and tolerances: `mas/04_REFERENCE_RESULTS.md`. They are
targets for diagnosis, never for tuning (golden rule 5). Nobody edits them
except Sebastian.
