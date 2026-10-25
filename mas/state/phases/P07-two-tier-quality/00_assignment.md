# P07 · 00 · Assignment — Two-tier artifact quality gate and the 8-channel montage

Status: READY
Author: orchestrator
Branch: phase/P07-two-tier-quality (from main @ 201f85c, tag p06-done)
Era: A — legacy behaviours required (`team.yaml`, `RULES.md` era matrix): **R1** window-level `StratifiedKFold(5, shuffle, 42)` in `benchmark_n_subjects.py`; **R3** per-window sub-band filtering; **R5** per-script gates (the **PF-07 `vpp_min` regression reproduced**, then pinned); **R8** `i % 5` smoothing (P05–P10 row); **fs250** in features. The legacy 7-channel arrays in `data/processed/` stay as they are (R-6 is computed on them; P16 rebuilds with 8).
Owners (agents): data-signal (Signal Processing), ml-engineer (Classical ML); verifier
Depends on: P06 (passed; merged 201f85c)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Roadmap item "add a criterion to automatically discard noisy channels";
the montage legend showed 8 channels while the pipeline used 7 (PO7 hard-excluded).
**Depends on:** P06. **Owners:** Signal Processing, Classical ML, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `quality_check.py` additions: `compute_channel_quality_stats` (per-channel fail
   fraction, mean Vpp, mean std), `identify_noisy_channels(windows, channel_names,
   limits, fail_fraction_thresh=0.5)` (channel dropped if it fails the limits in
   **> 50 %** of windows), `drop_noisy_channels`, and
   `apply_artifact_quality_pipeline(windows, y, channel_names, vpp 5–120, std 1–35,
   channel_fail_fraction_thresh=0.5, verbose, precomputed=None)` → dict
   `windows_clean, y_clean, valid_mask, channels_kept, channels_kept_idx,
   channels_dropped, channel_stats`. Tier 1 = channel drop for the whole subject;
   tier 2 = window rejection on the surviving channels.
2. All extractors (FBCCA, FBCSP, PSD) run this pipeline and return 4 values.
   Update **every** consumer (`benchmark_harmonic_fbcca`, `benchmark_feature_selection`,
   `benchmark_cross_validation`, `visualize_data`, `test_sklearn_models`,
   `evaluate_confusion_matrix`).
3. Config: restore PO7 (8 scalp channels, `excluded: []`). Add
   `resolve_channel_names(n_channels)`: 8 → full montage, 7 → montage without PO7
   (legacy arrays), else None — so un-regenerated subjects keep working.
4. `run_preprocessing.py`: before window extraction, detect chronically noisy channels
   on non-overlapping 1 s windows of the filtered recording (`vpp 5–200, std 0.5–60`)
   and drop them; keep the raw gate with `vpp_min=0.5` pinned.
5. **Reproduce the regression**: show that letting the raw gate inherit the new
   default `vpp_min=5.0` rejects all 320 windows of S03, then pin it (PF-07). Add
   `summarize_window_quality` output to the preprocessing log.
6. `scripts/benchmarks/feature_based/benchmark_n_subjects.py`: auto-discovers
   subjects under `--data-root` (default `data/processed`), `--n-jobs` (joblib),
   FBCSP(m=1, in-fold) + FBCCA → scaler → Shrinkage-LDA, smoothing, columns of
   `02_REQUIREMENTS.md` §6, saves `reports/n_subjects_benchmark.csv`. (Still
   `StratifiedKFold` here; P11 changes it.)

## Run (verbatim)

The roadmap gives no run line for P07. See `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`apply_artifact_quality_pipeline`, `benchmark_n_subjects.py`, `configs (PO7 restored)`

## Acceptance (verbatim)

Acceptance: tests for both tiers; S03 still produces windows; channel report printed
per subject; benchmark CSV produced for every subject (channels kept/dropped column
filled). Record numbers (no reference target for this intermediate state).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-05 | mas/05_PITFALLS.md | PO7 restored in the config; `resolve_channel_names` 8 → full, 7 → without PO7, else None |
| PF-06 | mas/05_PITFALLS.md | every channel subset by name — after a tier-1 drop the positions move |
| PF-07 | mas/05_PITFALLS.md | reproduce: raw gate inheriting `vpp_min=5.0` rejects S03 windows; then pin 0.5; `summarize_window_quality` in the log (fed the ungated windows — P02 carry-forward) |
| PF-08 | mas/05_PITFALLS.md | extractors 3 → 4 return values; **every** consumer updated in the same change; a smoke test runs each script |
| PF-09, PF-10 | mas/05_PITFALLS.md | no stale/root mixing; one final mask for all blocks |
| R-6 | mas/04_REFERENCE_RESULTS.md | P11 target computed on the 7-channel legacy arrays with the two-tier gate vpp 5–120 / std 1–35 / channel fail > 50 % (counts 200/196/197/197/200 clean); P07 must not regenerate `data/processed/` |
| R5, R6, R9 | mas/RULES.md | explicit thresholds; channel index layouts proven; per-subject channels kept/dropped with data source |
| decisions.md P02/P05/P06 carry-forward | | `summarize_window_quality` on ungated windows; stale outputs on skipped subjects; reproduce PF-07 with `--vpp-min 5.0`; remove the vacuous P06 layout test, fix the P06 tester docstring, cut the suite runtime (gate run 506.72 s > 5 min threshold) |
| R10, R11 | mas/RULES.md | cite; `after-attempt` |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-signal | P07.1, P07.3, P07.4, P07.5 — first builder | `03_changes_data-signal.md` |
| ml-engineer | P07.2, P07.6, the test-runtime cut and P06 test cleanups (after data-signal is READY) | `03_changes_ml-engineer.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | phase report | `mas/state/reports/P07.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
