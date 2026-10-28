# P19 · 04 · Tests — synthetic-tester

Status: READY
Author: synthetic-tester
Branch: phase/P19-raw-quality

## Files
- NEW `tests/test_p19_independent_known_answer.py` (13 tests, about 3 s). The builder's `tests/test_p19_raw_quality.py` is untouched.

## Tests (known answers, independent of the builder's)
| Plan item | Test | Known answer |
|---|---|---|
| 1 raw-only drift | `test_planted_slow_drift_...` | tapered 0.2 Hz, 1000 uV sine on one channel: valid on `filtered` (all reasons 0), reason 3 on `raw`/`both` for every window with raw Vpp > 150 uV, nothing outside the drift |
| 3 raw guard (R6) | `test_raw_artifact_guard_covers_exactly_block_plus_minus_guard`, `..._straddling_a_window_boundary...`, `test_raw_guard_window_boundaries_are_tight_to_the_sample` | block at sample 5220, guard 128 -> windows 19/20/21 (hand-computed overlap); guard 0 -> only 20; straddling block -> 24, 25; the guarded span ends/starts one sample from a window edge: flagged at g and not at g-1 (both edges); none under `filtered` |
| 4 channel tier | `test_channel_bad_only_on_one_signal_...` | bad on raw only: dropped under raw/both, kept under filtered; bad on filtered only: dropped under both, kept under raw |
| precedence | `test_precedence_1_over_2_over_3` | window with filtered gate fail and raw fail -> 1; filtered-guard window that also fails the raw gate -> 2; raw-only -> 3; under `raw` the same window -> 3 |
| 5 byte identity | `test_filtered_source_byte_identical_...` | `filtered` equals `apply_artifact_quality_pipeline` bytes (mask, dtype int8, channels) with no raw, and with hostile raw (x100 noise) |
| 7 counts | `test_rejection_counts_by_label_...` | per label total - valid = own_gate + guard + raw; sums to the rejected total; raw = 0 under filtered; own_gate = guard = 0 under raw |
| 6 source | `test_missing_or_unknown_source_...` | missing key, 5 unknown values, and raw/both without raw arrays raise `ValueError` |
| wiring end to end | `test_build_raw_drift_is_rejected_...` | synthetic recording with a 1500 uV, 0.2 Hz drift on one channel for 20 s: `build_windows` gives >= 5 reason-3 windows on raw and both, none on filtered; every raw-source rejection is 3; rejected windows lie within drift +- 4 s; meta `n_reason3_raw_gate + _guard` equals the count; window arrays identical across sources. This answers the S01 smoke question: the raw path rejects when a raw window exceeds `vpp_max`. |
| 8 C-a | `test_c_a_refusal_resume_overwrite_independent`, `..._before_any_subject_is_built` | different source or banks refused (nonzero, meta mtime unchanged); identical + `--resume` skipped; `--overwrite` rewrites with `source=raw`; refusal happens before a second subject is built |
| 9 skip | `test_all_channels_dropped_is_skipped_and_other_subject_still_built` | S01 with 3000 uV tone: `[-] Skipping S01: all channels dropped (source=raw)`, no `.npy`; S02 built, exit 0 |

## Mutants (run in a scratch copy `mas/state/scratch/p19_mut`, source tree untouched)
| Mutant | Killed by |
|---|---|
| `use_f, use_r = True, False` (gate ignores source) | yes (drift test) |
| raw guard not applied (`r_over = none`) | yes |
| raw gate not applied | yes |
| precedence 3 over 2 | yes |
| precedence 3 over 1 | yes |
| channel tier on the first signal only | yes |
| `valid_mask_no_guard` includes guards | yes |
| unknown source accepted | yes |
| `overlaps_mask` drops the last sample of a window | yes (tight-edge test; first version of my guard test did not, so it was tightened) |
| `overlaps_mask` drops the first sample | yes |
| guard samples minus one | yes |
| C-a never refuses | yes |
| `--resume` never skips | yes |
| skip message changed | yes |
| label counts drop reason 3 | yes |

15 of 15 killed. No bug found in the builder's code.

## Suite
`.venv/bin/python -m pytest tests/ -q -o addopts=""`:
- Run 1 (without the new file, after the builder's one-line fix): `1218 passed, 22 warnings in 780.11s (0:13:00)` (`mas/state/scratch/p19_suite.log`).
- Run 2 (with the new file, 13 more tests): `1231 passed, 22 warnings in 732.68s (0:12:12)` (`mas/state/scratch/p19_suite2.log`).
