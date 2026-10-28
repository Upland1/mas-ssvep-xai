# P16 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, 03_changes_data-signal.md, mas/RULES.md
Branch: phase/P16-continuous-filtering
Commit(s): see `git log` (ml-engineer commits: extractors + N1, flagship port, compare_v1_v2, handoff)

## Questions

ACK 02_plan.md ml-engineer 2026-10-27

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `scripts/benchmarks/feature_based/benchmark_n_subjects.py` | MODIFIED | ported to `load_subject`; legacy root + defaults = R-6 exactly; built roots use the saved `fbcca`/`fbcsp` bands, true-id trial-reset smoothing, `cv_groups`; `--quality`, `--fs`, `--cv-repeats`, derived suffix, Bank/CSP Bands and SD columns | P16.7 | R1, R2, R3, R5, R8, PF-02/04 |
| `src/features/ssvep/fbcca_extraction.py` | MODIFIED | `subband_windows=`, `quality=`; `fbcca_band_scores` (scores from already-filtered bands) | P16.7 | R3, R5 |
| `src/features/ssvep/fbcsp_extraction.py` | MODIFIED | `subband_windows=`, `quality=` | P16.7 | R3, R5 |
| `src/features/ssvep/window_mask.py` | MODIFIED | `loader_decision(quality, n, C, names)`: applies a `load_subject` decision to full or already-selected rows/channels, raises on misaligned shapes | P16.7 | R5, PF-10 |
| `src/io/subject_data.py` | MODIFIED | two lines: `quality["channel_stats"]` for per-script decisions (data-signal's file; needed for the printed per-channel report) | P16.7 | P07 |
| `src/models/classical/legacy_eval.py` | MODIFIED | `oof_space(splits=None)` raises ValueError (P11 N1) | P16.7 / 9b | R1 |
| `scripts/benchmarks/feature_based/benchmark_5_subjects.py`, `scripts/evaluation/test_sklearn_models.py` | MODIFIED | the two frozen P05 callers that relied on the silent fallback pass `splits_for("legacy", ...)` explicitly (same numbers) | 9b | PF-01 |
| `scripts/diagnostics/compare_v1_v2.py` | NEW | joins frozen v1 and rows a, a', b, c, c' into `reports/v1_vs_v2/{flagship,connectivity}.csv` + `v1_vs_v2.md`; `--check-regression` compares the `v1check` CSVs with the frozen ones exactly | P16.8 | own |
| `tests/test_p16_flagship_port.py`, `tests/test_p16_compare_v1_v2.py` | NEW | known-answer tests (below) | P16.7/8 | own |

## Legacy behaviour implemented

Legacy root (`data/processed`, the default): fs 250 assumed (`fs_source legacy-assumed`, PF-04), per-window sub-band filtering (R3/PF-14), reconstructed trial ids, per-script two-tier gate, `i % 5` smoothing (R8 era clause); labelled `legacy` in the console header and `.meta.txt`. `--cv legacy` (leaky window-level split, `legacy_leaky/` output) and `--smoothing trial|mod5` remain. `--fs 256` on a legacy root is row a'.

## Design notes

- `load_subject` is the only data entry. `thresholds` and `channel_fail_fraction` come from the config `quality:` block via `quality_params_from_config` and are passed explicitly (R5).
- `quality=d["quality"]`: the extractors accept the windows either as all selected rows (`len(valid_mask)`) or as the already-kept rows of `load_subject` (`valid_mask.sum()`); other lengths raise. The script passes the loader's already-clean `X` with an all-ones decision.
- Smoothing key: `trial_ids` (R8); CV group key: `d["cv_groups"]` on built roots, reconstructed ids on legacy. `run_cv` asserts `assert_no_shared_trials` on every grouped split (R1 runtime guard).
- `--smoothing` default is `trial` on built roots and `mod5` on legacy roots. The root must not mix built and legacy subject folders.
- Output suffix rule: `--out-suffix` is used verbatim; when absent, a non-default run gets `<filter_mode>_<quality without dashes>_fs<fs>_rep<N>` (only the parts that apply); the legacy default has no suffix.
- `--cv-repeats N`: seeds `--seed + r`; CSV `1.0s Acc (%)`/`2.0s Smoothed (%)` are the mean over repeats, `1.0s SD`/`2.0s SD` the sample SD (ddof 1), `CV repeats` = N; the seed-42 values are printed per subject on the console (`seed 42 alone ...`). Mean row = mean of the rounded columns.
- Built roots add columns `Bank` (fbcca) and `CSP Bands` (7-12 13-17 18-26 27-36 38-52) before the accuracy columns.

## Differences from the cited examples

None.

## Deviations from the plan

1. `oof_space(splits=None)` now raises, which required explicit legacy splits in two frozen P05 scripts (same numbers).
2. The v1/v2 table includes an `a` row (legacy, fs 250) rerun with `--cv-repeats 5` next to the frozen seed-42 `v1_frozen` column so that every row has a repeat SD.

## How to run / reproduce (verifier; flags and suffixes agreed with connectivity-stats)

Flagship (each writes `reports/n_subjects_benchmark_<suffix>.csv` and `.meta.txt`; measured runtimes below):

```bash
# regression, settled point 4 (seed 42, 1 repeat, defaults; ~15 s)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --out-suffix v1check
# row a  (legacy, fs 250, 5 repeats)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --cv-repeats 5 --out-suffix v1rep5
# row a' (legacy folders, fs 256: the fs effect)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --fs 256 --cv-repeats 5 --out-suffix v1fs256
# row b  (per_window build, shared quality)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed_per_window --quality shared --cv-repeats 5 --out-suffix v2pw
# row c  (continuous build, shared quality)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed_continuous --quality shared --cv-repeats 5 --out-suffix v2cont
# row c' (continuous build, no guard)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed_continuous --quality shared-no-guard --cv-repeats 5 --out-suffix v2cont_noguard
```

Connectivity rows use `analyze_connectivity_cohort` (connectivity-stats handoff gives flags): a = the frozen `baselines/v1_*/reports/connectivity_cohort_summary.csv` (also `--out-suffix v1check` for the regression), b = `--out-suffix v2pw`, c = `--out-suffix v2cont`, c' = `--out-suffix v2cont_noguard`. The table script reads `reports/connectivity_cohort_summary_<suffix>.csv` with exactly these suffixes (override with `--conn-b-suffix`, `--conn-c-suffix`, `--conn-c-prime-suffix`; flagship `--flagship-{a,a-prime,b,c,c-prime}-suffix`).

Then:

```bash
.venv/bin/python -m scripts.diagnostics.compare_v1_v2 --check-regression   # exact vs the frozen v1 CSVs (flagship and connectivity v1check), exit 1 on any difference
.venv/bin/python -m scripts.diagnostics.compare_v1_v2                      # -> reports/v1_vs_v2/flagship.csv, connectivity.csv, v1_vs_v2.md
```

Row a' is flagship only (the connectivity decomposition has rows a, b, c, c').

## How I verified

- `tests/test_p16_flagship_port.py` (13 tests): legacy root defaults equal the pre-port flow (`prepare_subject` + `benchmark_spaces` + `oof_space`) for a clean and a bad-channel subject, accuracies, row counts and the feature matrices bit for bit; `--cv legacy`/`trial` equal too; main writes the unsuffixed legacy CSV with the legacy columns; a built root never refilters (the filtering functions are patched to raise) and its 2.0 s accuracy equals an independent trial-reset recomputation (S02 has guard rejections that make the legacy `i % 5` rule differ, asserted); FBCCA from saved bands equals `fbcca_band_scores`; quality layouts and misalignment raising; `--cv-repeats` mean/SD/seed columns against separately computed seeds 42..44; suffix rules; N1 raises; PF-04: a 24 Hz tone sampled at 256 Hz scores 2.29 for target 24 with fs 256 and 0.79 with 250 (fails on the historical literal); R1 groups never straddle a fold.
- `tests/test_p16_compare_v1_v2.py` (3): planted values give the exact differences, a missing variant leaves empty columns, `--check-regression` is exact and flags a 0.01 change.
- Suite: `pytest tests -q -o addopts=""` summary line in the section "Suite result" below.
- Real-data smoke on the legacy root (project script, `--reports-dir mas/state/scratch/p16_ml`, deleted afterwards; nothing written to `data/processed`, `reports`, `outputs`, `baselines`):
  - `benchmark_n_subjects --subjects S03 S01 --out-suffix v1check` (6 s): S03 86.80 / 90.36, S01 61.00 / 67.50 = R-6.
  - Full cohort `--out-suffix v1check` (16 s wall): S01 61.00/67.50, S02 56.12/61.73, S03 86.80/90.36, S04 97.46/97.97, S05 95.00/95.50, Mean 79.28/82.61; `diff` of the CSV with the current `reports/n_subjects_benchmark.csv` (the P11 file; `baselines/v1_*` does not exist yet) printed nothing: byte-identical.
  - Row a' preview `--fs 256 --cv-repeats 5` (20 s): Mean 88.84 / 91.33 (SD 1.40 / 1.17); S01 73.00/77.30, S02 79.08/86.02, S03 94.52/97.46, S04 99.70/97.97, S05 97.90/97.90. Seed 42 alone (`--fs 256`, 14 s): Mean 87.68 / 90.01. The gain of about +9 pp 1.0 s over fs 250 is the fs effect on the legacy windows; it is large but consistent with the PF-04 test (references at 250 Hz drift by 0.56 cycle per second at 24 Hz). The reviewer should read it as the fs effect, not as a result to tune on.
  - Built roots could not be smoked: `data/processed_per_window|continuous` do not exist until the verifier builds them. The built path is covered by the synthetic built folders of `tests/p16_synth.write_built_subject`.
- Runtime estimate for the verifier: each flagship run 15-25 s legacy; built roots add no filtering (bands are read), so the same order. The five-run decomposition plus the check is about two minutes, far inside the plan's 15 min estimate.

## Left to do / known limitations

- Rows b, c, c' were not run on real built folders (not built yet).
- `Bank` is constant (`fbcca`); it exists for the schema and for P17 banks.
- Per-script quality on a built root reruns the P07 gate on the selected built windows (loader behaviour); that mode is not part of the decomposition.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

| # | Trigger (failed test / deviation / verification) | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| - | - | - | - | - |

## Sources

1. `mas/02_REQUIREMENTS.md` section 6 (schema), `mas/04_REFERENCE_RESULTS.md` R-6 via `mas/RULES.md` (opened in this run).
2. Chen et al. 2015, J. Neural Eng. 12:046008 (FBCCA weights and bank), as cited in `src/features/ssvep/fbcca_extraction.py`.
3. `mas/state/phases/P16-continuous-filtering/03_changes_data-signal.md` (loader API).

## Suite result

Full suite `pytest tests -q -o addopts=""` on the tree at commit c931e11 (log kept in the agent scratchpad): `3 failed, 1032 passed, 21 warnings in 1377.84s (0:22:57)` (the run was slowed by a second suite running at the same time). The three failures were all caused by this port and are fixed in the commit after c931e11:
- `test_p05_feature_benchmark.py::test_qda_rank_failure_is_caught_and_other_models_survive` called `oof_space` without splits (N1): the test now passes `splits_for("legacy", ...)` explicitly (committed in 9c63e9a).
- `test_p07_ml_engineer.py::test_n_subjects_schema_channels_and_parallel_equals_serial` expects the per-channel gate report in the console: `print_channel_report` restores it (the loader now also returns `quality["channel_stats"]` for per-script decisions, a two-line addition to `src/io/subject_data.py`).
- `test_p11_cv.py::test_defaults_are_grouped_cv_and_mod5_smoothing...` expects the parser default `--smoothing mod5`: the parser default is mod5 again and the script switches to `trial` on built roots only when `--smoothing` is not given on the command line.
After the fixes the three tests plus `test_p16_subject_data.py`, `test_p16_flagship_port.py`, `test_p16_compare_v1_v2.py`, `test_p07_ml_engineer.py` and `test_p11_cv.py` pass (32 + 3 passed); the full suite was not rerun a second time (23 min under load).

## Round 1 follow-up

Decision (decisions.md, P16): connectivity reads the broadband windows, filtered continuously in both build modes, so (c) - (b) is zero by construction. `compare_v1_v2.py` now writes the string "not applicable (same input)" in the connectivity filter-mode columns of `connectivity.csv` and "n/a (same input)" in the markdown; the flagship keeps the numeric c - b, and the guard effect c - c' stays numeric for both. `test_effects_are_plain_differences` asserts it. Commit 416ab9e.

Full suite, `.venv/bin/python -m pytest tests -o addopts="" -q`: `1035 passed, 21 warnings in 699.45s (0:11:39)`.

## Round 1 fixes (pre-run audit 07_review.md, fixes 3, 4, 5)

- **Fix 3 (connectivity a')**: `compare_v1_v2.py` joins connectivity `--conn-a-prime-suffix` (default `v1fs256`); `connectivity.csv` has `d_<value>_fs` = a' - a and `d_<value>_build` = b - a'; the filter-mode columns stay "not applicable (same input)"; guard = c - c'. Markdown table shows a, a', b, c, c' and dFDR fs/build/guard.
- **Fix 4 (flagship a't)**: new variant `--flagship-a-prime-t-suffix` (default `v1fs256trial`). `flagship.csv` columns: `d_fs` = a' - a, `d_smoothing` = a't - a' (2.0 s only; empty at 1.0 s), `d_build` = b - a' at 1.0 s and b - a't at 2.0 s. Run (legacy root, reconstructed ids, reset at each id): `benchmark_n_subjects --fs 256 --smoothing trial --cv-repeats 5 --out-suffix v1fs256trial`. Tested by `test_smoothing_trial_on_a_legacy_root_is_the_a_prime_t_row` (1.0 s equals a'; 2.0 s equals an independent trial-reset computation).
- **Fix 5 (regression scope)**: `compare_v1_v2 --check-regression` now compares, `_v1check` vs frozen: `n_subjects_benchmark`, `connectivity_cohort_summary`, `connectivity_cohort_summary_v1check_details.csv` vs `connectivity_cohort_summary_details.csv`, `connectivity_alpha_diagnostic_v1check.csv`, and every `reports/connectivity_edges_v1check/*.npz` vs `baselines/v1_*/reports/connectivity_edges/` (`np.array_equal` per key). It prints `byte-equal` / `value-equal only` / `different` per CSV and the number of equal npz files; exit 1 if any is different or a file is missing.
- **R5 confirmation**: `benchmark_n_subjects.evaluate_subject` passes `thresholds` (config `quality:` via `quality_arguments`, else `GATE_THRESHOLDS`) and `channel_fail_fraction` to `load_subject` explicitly (line ~198); verified by the flagship tests against the new loader.
- Exact flags of the flagship rows: unchanged from above plus `a't` (`v1fs256trial`, line above). Tests: `tests/test_p16_flagship_port.py`, `tests/test_p16_compare_v1_v2.py` and the tester's compare test (updated to b - a') pass. `tests/test_p16_independent_known_answer.py::test_loader_fs_meta_vs_legacy_vs_override` and `::test_quality_modes_shared_nogaurd_perscript` still fail because they call `load_subject` on legacy folders without thresholds (data-signal fix 2 now raises); they are the synthetic-tester's calls, not changed here.

## Round 2 fix (verifier FAIL 06_verify.md, criterion (2))

- MODIFIED `scripts/diagnostics/compare_v1_v2.py`: new `_arrays_equal` used for every npz key of `--check-regression`: same shape and dtype required, then `np.array_equal(..., equal_nan=True)` for float/complex arrays and plain equality otherwise; key sets must still match. NaN counts as equal only where both arrays hold NaN at the same position, so the NaN diagonals of coherence/PLV/wPLI no longer report identical files as different, while a NaN against a number still fails. Byte-equal / value-equal only / different reporting unchanged. Commit 9b297c0.
- CSV comparisons: unchanged. `_verdict` reads with `keep_default_na=False` (empty cells stay the string "", never NaN) and `assert_frame_equal` treats aligned NaN as equal anyway, so the value-equal fallback had no NaN issue; now covered by a test.
- MODIFIED `tests/test_p16_compare_v1_v2.py`: `test_regression_check_nan_diagonal_npz_is_equal` (7x7 NaN-diagonal matrix plus int key, exit 0; fails on the old code), `test_regression_check_misplaced_nan_or_changed_layout_fails` (NaN moved off the diagonal, float32 dtype, extra key: each exit 1; identical file exit 0, which also fails on the old code), `test_regression_check_csv_empty_cells_value_equal` (aligned empty cells with CRLF: value-equal only, exit 0; empty vs number: exit 1). Both npz tests fail with the old script (2 failed, 5 passed), all 7 pass with the fix.
- `tests/test_p16_*.py`: `128 passed in 176.13s`. Full suite, `.venv/bin/python -m pytest tests -o addopts="" -q`: `1092 passed, 21 warnings in 597.21s (0:09:57)`.
- No phase command rerun; `compare_v1_v2 --check-regression` on real outputs is left to the verifier.
