# P07 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Reads: 00_assignment.md, 02_plan.md, 03_changes_data-signal.md, mas/RULES.md, mas/02_REQUIREMENTS.md §4 §6, mas/04_REFERENCE_RESULTS.md R-6, mas/05_PITFALLS.md PF-06/08/10, decisions.md P05-P07
Branch: phase/P07-two-tier-quality (on top of data-signal's b586e49)
Commit(s): 020ebc9 (extractors + every consumer), 317a995 (benchmark_n_subjects + P07 ml tests), 7588a25 (suite runtime cut, P06 test cleanup)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| src/features/ssvep/window_mask.py | MODIFIED | `GATE_THRESHOLDS` (5/120/1/35, explicit), `CHANNEL_FAIL_FRACTION` 0.5, `NO_CHANNEL_DROP` 1.0, `quality_gate`, `channel_report`, `names_for`; legacy `P05_MASK_THRESHOLDS` and `resolve_window_mask` kept | P07.2 | PF-10, R5 |
| src/features/ssvep/{fbcca,fbcsp,psd}_extraction.py | MODIFIED | run the pipeline, return `(X, y_clean, valid_mask, channel_report)`; new signature below | P07.2 | PF-08, PF-10 |
| src/io/channels.py | MODIFIED | `subject_channel_names(dir, subject, n, scalp=None)`: `channels.json` `kept`, else `scalp`, else `resolve_channel_names(n)`; error text `"<k> channel names ... for an array with <n> channels"` | P07.2 | PF-05, PF-06 |
| src/models/classical/feature_spaces.py | MODIFIED | `build_feature_blocks`: one `quality_gate`, `channel_report` handed to every extractor; harmonic cluster / FBCCA channels = requested names that survive the drop (error if none); new keys `channel_report, channels_kept, channels_dropped, channel_fail_fraction` | P07.2 | PF-06, PF-10 |
| src/models/classical/benchmark_runner.py | MODIFIED | `prepare_subject(..., scalp=None, ..., channel_fail_fraction, verbose)`, `channel_summary`, `discover_subjects` (moved here), `legacy_header_lines(..., channel_fail_fraction)` | P07.2 | PF-06 |
| scripts/benchmarks/feature_based/{benchmark_5_subjects,benchmark_cross_validation,benchmark_feature_selection,benchmark_harmonic_fbcca}.py, scripts/evaluation/{evaluate_confusion_matrix,test_sklearn_models}.py | MODIFIED | interim `legacy_scalp` lines removed, names from `channels.json` / count; channel summary printed per subject; docstrings state the two-tier gate | P07.2 | PF-08 |
| scripts/exploration/{visualize_data,diagnose_occipital_spectra}.py | MODIFIED | per-subject `subject_channel_names`; visualize blocks call the 4-value extractors with an all-ones decision (`precomputed`, windows already accepted by the script's own P02-legacy mask) | P07.2 | PF-08 |
| scripts/benchmarks/feature_based/benchmark_n_subjects.py | NEW | see Flags | P07.6 | 02_REQUIREMENTS §4, §6 |
| tests/p05_synth.py | MODIFIED | `keep_all(n)`, `write_subject(..., bad_channels=)`, 8-channel support | — | — |
| tests/test_p07_ml_engineer.py | NEW | 14 tests (below) | — | — |
| tests/test_p03_exploration_known_answer.py, test_p05_known_answer.py, test_p05_feature_benchmark.py, test_p05_round2_known_answer.py | MODIFIED | follow the 4-value API and the P07 default gate; P03 "names through config" tests now write `channels.json` | — | PF-08 |
| tests/test_p06_feature_selection.py, tests/test_p06_known_answer.py | MODIFIED | runtime cut, vacuous layout test replaced, tester docstring corrected | — | decisions.md P06/P07 |

## Extractor API

```
extract_fbcca_features(windows, y, channel_names=None, fs=250.0, target_freqs=..., n_harmonics=3,
                       precomputed=None, thresholds=None, channel_fail_fraction=0.5, verbose=False)
extract_fbcsp_features(windows, y, channel_names=None, fs=250.0, subbands=..., m=1, <same four kwargs>)
extract_continuous_psd_features(windows, y, channel_names=None, fs=250.0, freq_range=(5, 35), use_db=False, <same four kwargs>)
  -> (X, y_clean, valid_mask (n,), channel_report)
```

`channel_names=None` resolves by count (`resolve_channel_names`; ValueError for an unknown layout). `thresholds=None` is the P07 gate, a dict must name all four limits. `channel_report` = `channels_kept`, `channels_kept_idx`, `channels_dropped`, `channel_stats`, `valid_mask`; passed back as `precomputed=` it reuses the decision (PF-10). Features cover the kept channels only (PSD column `c*F + j` = kept channel c); fs is still 250 (legacy PF-04). The old `valid_mask=` kwarg is gone: a stale call fails loudly (a float as third positional raises). Legacy single-tier P05 gate: `thresholds=P05_MASK_THRESHOLDS, channel_fail_fraction=NO_CHANNEL_DROP`. An all-rejected input yields an empty `(0, C'*F)` matrix instead of crashing.

## Flags of benchmark_n_subjects

`--data-root` (default `paths.data_processed_dir` = data/processed), `--subjects`, `--n-jobs` (joblib over subjects; console text collected per subject and printed in order), `--m`, `--out-suffix`, `--reports-dir`, `--config`, `--fs` (250), `--seed` (42). Output `reports/n_subjects_benchmark[_suffix].csv` with exactly `Subject, Channels Kept, Channels Dropped, Clean Windows, Rejected Windows, 1.0s Acc (%), 2.0s Smoothed (%)` plus a `Mean` row of the two accuracy columns (other cells blank), and `.meta.txt` (cv/smoothing/features/gate lines with the legacy labels, model, data source, kept/dropped names per subject). `Channels Kept` is the count, `Channels Dropped` the names joined by a space (`none` if empty). Per subject the per-channel report of the pipeline is printed (`-> DROPPED` marks tier-1 drops) followed by the channel summary; unreadable subjects print `[-] Skipping <S>: <reason>`. Exit 1 for a missing/empty data root or no evaluable subject. Cohort line and `Saved:` path close the log.

## Legacy behaviour implemented

R1 `StratifiedKFold(5, shuffle, 42)` over windows, R8 `i % 5` smoothing, R3 per-window sub-bands and fs 250 (all labelled in the header lines, `.meta.txt` and docstring); R5 per-script gate with explicit limits; the P05 gate stays reachable by flags.

## Verification

- `tests/test_p07_ml_engineer.py` (14 tests): 4 return values and one shared decision across PSD/FBCCA/FBCSP with a dropped middle channel and a tier-2 window (PF-08/PF-10); PSD column layout follows kept names after dropping POz (argmax column 124, positional mutant 154; PF-06); cluster channel PO8 dropped -> harmonic 24 columns, FBCCA on O1/Oz/O2, aligned rows; `precomputed` not re-gated (a fresh call rejects the window, the shared one keeps it); explicit thresholds and unknown layouts; legacy P05 gate reachable (rejects all 50 windows of the noisy-channel tree, P07 keeps all 50 and drops POz); PF-07 default vs legacy Vpp 2 uV windows; `subject_channel_names`; 8-channel folder with PO7 dropped; no script keeps `legacy_scalp(`; flagship, harmonic and five-subject scripts on a 7-/8-channel tree with drops; `benchmark_n_subjects` schema, counts, kept/dropped, accuracies equal to the flagship script on the same tree, `--n-jobs 2` CSV identical to `--n-jobs 1`, `--subjects` skip, exit codes.
- Mutants checked: ignoring `precomputed`, and taking the PSD from the undropped windows, each fail several of these tests.
- Every consumer script runs (`--help` and the smoke tests above): benchmark_5_subjects, benchmark_cross_validation, benchmark_feature_selection, benchmark_harmonic_fbcca, evaluate_confusion_matrix, test_sklearn_models, visualize_data, diagnose_occipital_spectra, benchmark_n_subjects. `grep` finds no `valid_mask=` or `legacy_scalp(` call left in `src/` or `scripts/`.
- Full suite `.venv/bin/python -m pytest tests -q`: 485 passed, no failure.

## Test runtime (before / after)

| | tests | wall |
|---|---|---|
| before (b586e49 plus my first edits; 18 tests failed on the not-yet-adapted P03/P05 tests; mas/state/scratch/p07_ml_suite_before.log) | 471 | 7 min 49 s (469 s) |
| after (mas/state/scratch/p07_ml_suite_after.log) | 485 | 227 s (3 min 47 s) |

Largest cuts (before -> after, s): P06 SFS diagnostics script test 188 -> 26 (50-window tree, `--sfs-features 2`, one variant, shares the plain run with the ablation script test); ablation script test 85 -> 14 (shared fixture, p = 55/45/25/25/7); `test_sfs_selects_planted_columns_and_count` 20 -> 6; selector-input checks (`test_ablation_selection_sees_training_rows_only`, `test_ablation_rejects_selection_on_all_windows`) 19 + 13.5 -> about 1.5 each (SFS stubbed; they assert the rows given, the real SFS is in the other tests); `test_p_values_...` 14 -> about 2 (stub; arithmetic p = n + 5). The P04 script smoke (31.6 s before, 39.7 s after: machine noise) was left as is: it is 5 subprocess starts and I judged a smaller tree would not help. Known-answer strength kept: planted columns, counts, leak audit (disjoint 40/10 rows per fold), p values, i % 5.

## Deviations from the plan

1. Extractor signature: `channel_names` is the third positional (before `fs`), `valid_mask=` replaced by `precomputed=`, so every old call site breaks loudly (PF-08); I updated all of them in 020ebc9.
2. P05/P06 numbers are not reproducible with the new default gate (by decision, decisions.md P07); reproduction needs the legacy flags above. No P05/P06 report was regenerated (no real-data run).
3. `Channels Kept` is a count, `Channels Dropped` names: the schema (02_REQUIREMENTS §6) fixes only the column names.
4. `subject_channel_names` lives in `src/io/channels.py` (data-signal's module) and `discover_subjects` moved from `benchmark_5_subjects` to `benchmark_runner` (re-imported there; name unchanged for callers).
5. Scripts no longer read `channels.scalp` from the config for the legacy arrays: names come from `channels.json` or the channel count. The two P03 tests that fed a reordered name list through the config now write a `channels.json` into the subject folder; `test_channel_count_mismatch_fails_loudly` plants a 6-name `channels.json`.
6. `visualize_data` keeps its own P02-legacy mask (config thresholds) and bypasses the extractor gate with an all-ones decision on all channels; it does not run tier 1 (an exploration script of the legacy arrays).
7. The vacuous P06 layout test (`test_band_major_layout_matches_fbcsp_transformer`, scaling a band changes nothing because the CSP covariance is trace-normalised, so it asserted over an empty set) is replaced by a content-swap test that requires a non-empty change confined to `fs.band_columns(4)` with columns 0-39 bit-identical; the tester docstring of `test_ablation_rejects_selection_on_all_windows` now says it checks row counts only (disjointness is the leak audit).
8. The default `--sfs-features 15` of the ablation script and all scripts are unchanged; only the tests use 2.

## Left to do / limits

- No real-data run (verifier): the effect of the P07 gate on S01-S05 counts (R-6: 200/196/197/197/200 clean) is unmeasured here; `data/processed/` untouched.
- Parallel joblib uses the default (loky) backend; with `--n-jobs -1` on a laptop, memory is per-subject windows only.
- Run for the verifier: `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed --n-jobs 5`.

## Reference consultations (R11)

None.

## Sources

1. `mas/RULES.md` R1, R2, R5, R8; `mas/02_REQUIREMENTS.md` §4, §6; `mas/05_PITFALLS.md` PF-06, PF-08, PF-10; `mas/state/decisions.md` P05-P07 rows (opened in this run).
2. `mas/state/phases/P07-two-tier-quality/03_changes_data-signal.md` (pipeline and channel API).

## Questions

ACK 02_plan.md ml-engineer 2026-10-25

## Round 1 fixes

Required fix 2 of `07_review.md` (P04 positional `keep_channels` vs a subject's real names).

- NEW `check_subject_keep_channels(processed_dir, subject)` in `src/features/ssvep/harmonic_psd.py`: names from `subject_channel_names` (`channels.json`, else channel count); raises ValueError unless positions (1, 4, 5, 6) select POz, O1, Oz, O2 in that subject's arrays. On the legacy 7-channel arrays behaviour is identical to before. The config-level `check_keep_channels` is kept.
- Callers: `train_models.py` (per-subject loop prints `[-] Skipping <S>: ...`), `batch_run_subjects.py` (same, before `evaluate_subject`), `train_final_model.py` and `run_xai.py` (print `[x] ...`, exit 1).
- Test `test_p04_positional_keep_channels_checked_against_subject_names` (tests/test_p07_ml_engineer.py): a 7-channel folder with `channels.json` = PO7, PO3, POz, PO4, O1, Oz, O2 (PO8 dropped) passes the old config-only check but raises in the new one (would have picked PO3/O1/Oz/O2); the three scripts skip/refuse it, the legacy folder passes. It fails on the previous code (function absent; S02 would be trained).
- `test_no_script_keeps_the_interim_legacy_scalp_lines` now excludes `scripts/preprocessing/` (the producer, data-signal's file, legitimately uses `legacy_scalp`).
- Suite: `.venv/bin/python -m pytest tests -q`: no failure, 486 tests collected, 3m49s wall (real 3m49.057s). The `N passed` line is not printed in this configuration; the progress output ended with no F/E.
- Commits: see git log (fix: P04 positional channels against subject names).
