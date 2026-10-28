# P16 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_data-signal.md, 03_changes_ml-engineer.md, 03_changes_connectivity-stats.md, mas/RULES.md, mas/05_PITFALLS.md (PF-02/03/04/14)

## Tests added

NEW `tests/test_p16_independent_known_answer.py` (37 test cases, 17 s). Written independently of the builders' tests; `tests/p16_synth.py` is used only as a fake-recording writer. Synthetic data only; no generated or ignored file read. Every expected value is written by hand or computed with scipy/numpy independently of the module under test.

| Test | Simulates | Known answer | Catches |
|---|---|---|---|
| `test_window_index_equals_hand_written_legacy_starts_with_truncated_trial[256,250]` | MARK with 10 trials, last stimulus truncated | starts equal the hand-written P02 legacy starts per condition; one skipped (truncated) stimulus; 45 stim / 20 / 10 windows | PF-04 literal, wrong stride |
| `test_full_session_counts_80_40_200` | 40 trials | 80 / 40 / 200 | stride bug |
| `test_stride_half_second_...` | stride 0.5 s | 3 / 1 / 9 windows per segment, offsets 128*k restart at 0 per segment, sub_idx 0..k-1, one id per segment, row order is not offset order | ids per window, offsets not restarting |
| `test_window_index_uses_the_fs_given_not_a_literal` | fs 250 vs 256 | spacing 250 vs 256 samples | PF-04 |
| `test_band_windows_continuous_is_filter_then_cut_exactly_...` | 15 Hz tone + noise, Butterworth 13-17 | continuous = `sosfiltfilt` whole then cut (<1e-9); per_window edge/centre error ratio > 3 | PF-14 / R3 (per_window used as continuous) |
| `test_band_layout_tone_...` | 9 Hz on ch 0, 30 Hz on ch 2 | energy only in (band 0, ch 0) and (band 3, ch 2) | R6 layout |
| `test_ringing_time_equals_one_percent_span_...[13-17, 7-12]`, `..._takes_the_longest_filter` | Butterworth band-passes | equals span of irfft(abs(H)^2) at 1 % within 1 sample (independent of `sosfiltfilt`) | wrong guard |
| `test_artifact_inside_guard_gives_reason_2_...` | 500 uV spike at 30.5 s, guard 2 s | window 30 reason 1; windows 28,29,31,32 reason 2; `valid_mask_no_guard` loses only window 30; 55 vs 59 valid | guard off |
| `test_guard_auto_equals_ringing_time_of_the_filters` | `guard_sec="auto"` | equals `ringing_time_sec` | auto guard |
| `test_every_threshold_must_be_explicit[8 keys]` | each key removed | ValueError | R5 defaults |
| `test_channel_tier_drops_the_bad_channel_...` | O1 noisy; spike on O1 (ignored) and on PO3 (counted) | O1 dropped, window 10 valid, window 20 reason 1, 18/19/21/22 reason 2 | tier-1 order |
| `test_one_true_id_per_segment_and_cv_groups_twin_of_202` | built folder, 101-105+201+202 | 10 ids per 201 / 202; every 202 window shares `cv_groups` with the 201 window at the same start but not `trial_ids`; stimulus groups disjoint from 201/202 | PF-03/PF-13 |
| `test_loader_fs_meta_vs_legacy_vs_override` | built vs legacy folders | 256 meta / 250 legacy-assumed / override; `mod5` vs `trial`; legacy `bands=` raises | PF-04 |
| `test_quality_modes_shared_nogaurd_perscript` | spike at 57.5 s + bad O2 | shared < shared-no-guard, lost windows within guard distance of the spike, per-script source text, guard 0.902 s | R5 modes |
| `test_freeze_read_only_refusal_manifest_hashes_superseded_and_summary` | temp tree, CLI `main` | every MANIFEST sha256 equals recomputed source hash; superseded/ holds the five-subject CSV; second run (other date) exit != 0 and MANIFEST bytes unchanged; no write bit and PermissionError on write; summary long format with MEAN = 65.0 | overwrite, mutable snapshot |
| `test_flagship_features_come_from_the_saved_bands_...` | saved bands tampered (x3 FBCSP, FBCCA bands rolled) | CSP bands = 3x original; FBCCA scores change | refiltering (R3) |
| `test_flagship_smoothing_resets_per_true_trial_...` | planted confident scores, S02 with rejected windows | 2.0 s accuracy equals hand-written per-trial smoothing (100.0); mod5 and cross-trial rules give lower values | PF-02 / R8 |
| `test_flagship_cv_repeats_columns_...` | `repeats=3` vs seeds 42..44 alone | mean and sample SD (ddof 1), `CV repeats`=3; suffix rule | SD columns |
| `test_pf04_24hz_tone_at_256hz_needs_the_metadata_fs` | 24 Hz at 256 Hz | argmax = 24 Hz target at fs 256; score at fs 250 is below 1/1.5 of it | PF-04 literal |
| `test_no_fs_literal_in_the_v2_code[6 files]` | tokenize of the new/ported modules | no numeric token 250/256 | PF-04 |
| `test_connectivity_port_uses_meta_fs_and_true_ids_and_fs_override` | cohort on built folder (spy on estimator) | fs 256; `trial_ids` = loader ids, 2 true trials per class, none shared with 201; `--fs 250` gives 250 | PF-03, PF-04 |
| `test_compare_v1_v2_labels_connectivity_filter_mode_not_applicable` | planted CSVs | d_fs 10, d_build 5, d_filter_mode 5, d_guard 2, d_total 20 (flagship); connectivity filter-mode columns "not applicable (same input)", guard difference numeric | table semantics |

## Mutation check

Each mutant was planted in `src/` or `scripts/` with a one-line replacement, `tests/test_p16_independent_known_answer.py` was run, and the file restored with `git checkout` (final `git status` clean). All killed:

| Mutant | Killed by |
|---|---|
| `band_windows` continuous branch disabled (per_window path used) | band_windows exact test |
| `int(sub_window_sec * 250)` in `build_window_index` | legacy starts, fs-given, ids/cv_groups, literal grep |
| loader returns 250.0 for meta fs | loader fs, cv_groups test, literal grep, connectivity |
| guard disabled (`over = zeros`) | artifact guard, channel tier, quality modes |
| CSP bands always re-filtered | saved-bands test |
| FBCCA ignores `subband_windows` | saved-bands test |
| flagship smoothing forced to `mod5` on built roots | smoothing test |
| `smooth_probabilities_by_trial` averages across trials | smoothing test |
| `cv_groups` without the 202<->201 twin | twin test |
| default stride halved (legacy starts broken) | index tests |
| one trial id per window | stride, ids, connectivity |
| `freeze` overwrite allowed | freeze test |
| connectivity permutations without ids | connectivity port test |
| connectivity fs literal 250 | connectivity port test, literal grep |
| connectivity filter-mode difference numeric | compare_v1_v2 test |

Two of my first mutants survived and exposed weak tests, now fixed: cross-trial smoothing (random scores made accuracies coincide; fixed with planted confident scores and an assertion that the three rules differ) and a no-op FBCCA mutant (my mutant, not the test).

## Command

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```

## Output summary

`1072 passed, 21 warnings in 697.56s (0:11:37)` (full suite on the phase branch with the new file; log kept outside the repo). New file alone: `37 passed in 17.21s`.

## Coverage gaps

- Built folders are always generated by the real `build_subject`; the builder code itself is not independently re-derived beyond the window index, bands, gate and loader checks above.
- `freeze_baseline` is not exercised with a git repository (configs from git rev); the builders' test covers it.
- The edge/centre ratio threshold of the tests is 3 (synthetic 15 Hz case); the real-data "much greater" threshold is the reviewer's pre-commit.
- Flagship legacy-equals-pre-port and the connectivity legacy regressions rely on the builders' tests (not duplicated).
- Ringing-time tolerance is 1 sample as in the plan.

## Round 1

Fixes covered: 0bd4376 (cv_groups by largest overlap; explicit gate thresholds, R5), 15a601e (connectivity passes GATE), f468113 (a', a't, wider regression check).

Repaired: `test_loader_fs_meta_vs_legacy_vs_override` and `test_quality_modes_shared_nogaurd_perscript` now pass `thresholds` and `channel_fail_fraction` explicitly (shared `GATE` dict). The ml-engineer's 5-line edit to `test_compare_v1_v2_labels_connectivity_filter_mode_not_applicable` was reviewed and kept: with a' = 0.12, b = 0.20 the build step is b - a' = 0.08 and the fs step a' - a = 0.02, which are the correct values under the new table definition; the rest of that test is unchanged.

New tests in `tests/test_p16_independent_known_answer.py` (file now 49 cases, 16 s):

| Test | Known answer | Mutant killed |
|---|---|---|
| `test_cv_groups_pair_a_jittered_cue_window_...[8,-8,3]` | 202 window shifted by +-8/3 samples is grouped with the 201 window of largest hand-computed overlap (overlap = 256 - jitter), not an exact-start twin; stimulus groups stay disjoint | exact-start matching in `cv_groups` |
| `test_r5_per_script_gate_needs_explicit_thresholds_and_fail_fraction` | ValueError for legacy and built per-script without either argument or with only one; shared modes need neither | defaulting thresholds / fail fraction |
| `test_compare_v1_v2_decomposition_arithmetic_with_a_prime_and_a_prime_t` | 1.0 s: fs 20, build 4, filter 6, guard 3, total 30; 2.0 s: fs 15, smoothing 3, build b - a't = 5, filter 7, total 30; steps sum to c - a | build step taken from a' at 2.0 s |
| `test_check_regression_*` (identical; one planted value in each of 4 CSVs; changed npz array; missing file; value-equal vs byte-equal) | exit 0 / 1; verdict text byte-equal vs value-equal only (CRLF copy exits 0) | details CSV skipped; byte-equal shortcut (value differences missed); npz result ignored |

Mutants (one-line, reverted, `git status` clean): `cv_groups` exact start; per-script defaults in `_per_script_gate`; `d_build` from a'; `_verdict` always byte-equal; details CSV skipped; npz status ignored. All killed.

Full suite `.venv/bin/python -m pytest tests -o addopts="" -q`: `1089 passed, 21 warnings in 609.52s (0:10:09)`.

Status: READY
