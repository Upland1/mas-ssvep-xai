# P02 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 00_assignment.md, 02_plan.md, 03_changes_signal-processing.md, 03_changes_data-engineer.md, mas/state/decisions.md (P02 rows), mas/RULES.md, mas/01_DATA_SPEC.md §2, §3, §5.1, §6, mas/02_REQUIREMENTS.md §7, mas/05_PITFALLS.md PF-07, PF-09, PF-13
Branch: phase/P02-legacy-windowing @ 9d8c52b (builders' last commit); tests in a45f955

## Tests added

NEW `tests/test_p02_windowing_known_answer.py`, with 23 tests. All inputs are built inside the tests with fixed seeds at fs 256, which is the header rate P02 uses (decisions.md 2026-10-24). Nothing is read from `data/`. Synthetic EBR files are written to `tmp_path` by the test's own writer (`_write_ebr`, following the header layout in [3] §2). Expected values come from the specification or from analytic facts. None of them was taken from builder output.

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `::test_gate_sinusoid_analytic_ptp_std` | 3 ch × 256, 8 Hz sine (8 full periods), A ∈ {0.25, 1, 10, 50} | ptp = 2A, std = A/√2; limits 1 % around them give mask 1; each limit moved 1 % beyond gives 0 | rtol 1e-12 (ptp), 1e-9 (std) | analytic; [1] P02.1 | wrong statistic (e.g. ddof, abs max) | PASS |
| `::test_gate_bounds_inclusive_and_every_channel` | ±10 square waves, ptp 20 and std 10 exactly; one channel moved one float ulp in or out, or failing only on std | limits equal to the values give 1 (inclusive); any single channel beyond gives 0; the mask is int with one entry per window; shared defaults (5, 120, 1, 35) are inclusive at 5 | exact | [1] P02.1 | strict `<`, any-channel instead of every-channel | PASS |
| `::test_filter_dataset_keeps_mask_one_rows_in_order` | 6 rows, mask `[1,0,1,1,0,1]` | rows [0, 2, 3, 5]; length mismatch raises | exact | [own] | — | PASS |
| `::test_segment_and_validate_layout_window_channel_time` | ramp t + 1e6·c, 1000 samples | 3 windows `(3, 4, 256)`; window k, channel c = `arange(256k, 256k+256) + 1e6c` | exact | R6, [own] | wrong reshape axis | PASS |
| `::test_summarize_window_quality_known_ranges` | square windows A = 1, 2, 3 | 2 valid, 1 `vpp_low`; observed vpp 2..6, std 1..3 | exact | [own] | — | PASS |
| `::test_pf07_shared_defaults_reject_but_legacy_extractor_keeps_low_vpp` | 1 s sines with Vpp 2 µV (std 0.707) and 4 µV (std 1.41) | rejected by the `validate_eeg_windows` defaults; at Vpp 4 µV the rejection is caused by `vpp_min` 5 alone. Vpp 1.5/2/4/4.9 µV are kept by `extract_clean_subwindows_psd` and Vpp 0.4 µV is dropped. With `vpp_min=5.0` forwarded, Vpp 2 µV is dropped | exact | PF-07, [1] P02.2 | PF-07 | PASS |
| `::test_pf07_check_fails_on_extractor_that_does_not_forward_vpp_min` | the same check on a variant that calls `validate_eeg_windows` without `vpp_min` | the check raises `AssertionError` ("PF-07") | exact | PF-07 | **PF-07, demonstrated** | PASS |
| `::test_pf07_condition_pipeline_forwards_vpp_min` | 2 protocol trials, every channel a 10 Hz sine with Vpp 3 µV | legacy call: 2 × (2 + 1 + 5) = 16 windows; with the PF-07 variant monkeypatched in as the extractor: 0 | exact | PF-07, plan | **PF-07 at the condition level, demonstrated** | PASS |
| `::test_subwindows_psd_peak_and_density` | 5 s, 7 ch, 10 Hz, A = 10, fs 256 (+ a 5.5 s variant) | 5 records `(7, 256)`, `sub_index` 0..4, each equal to its slice; `freqs` = 0..128 with step fs/N = 1 Hz; argmax at 10 Hz; PSD[10] = A²N/(2fs) = 50 µV²/Hz; vpp = ptp(time_data) ≈ 20; std = A/√2; the 0.5 s remainder is dropped | rtol 1e-9 (PSD, std); 1e-2 for vpp ≈ 2A (sampled peaks) | analytic periodogram [5]; plan | wrong bin spacing, overlapping windows | PASS |
| `::test_subwindow_spike_rejected_and_counted` | 300 µV spike in sub-window 2, channel 3 | `sub_index` [0, 1, 3, 4]; `quality_stats` 5/4/1, `vpp_high` 1, channel [3], sub 2 | exact | plan, [1] P02.2 | — | PASS |
| `::test_segments_sample_index_ramp_protocol_40_trials` | §3 MARK, 40 trials (8 per target, seeded order), 154,880 samples, EEG = ramp t + 1e6·c, gate off | counts {201: 80, 202: 40, 101–105: 40 each}. Starts are read from the window content: 201 = onset + {0, 256}; 202 = onset − 256, with the last sample at onset − 1; stimulus = onset + 256k, k = 0..4. Each 202 window equals the second 201 sub-window of its trial | exact | [3] §3, §5.1; plan; PF-13 | PF-13 (cue after pulse), off-by-one | PASS |
| `::test_prepare_feature_matrix_on_protocol_ramp_row_order` | the same ramp recording | `X_time (320, 7, 256)`, `X_psd (320, 217)`, y int64 in blocks 80/40/40×5 in the order 201, 202, 101–105; `X_time[:, 0, 0]` equals the spec start sequence (time order within a condition); channel axis 1 | exact | [3] §5.1, R6 | unsorted, `(n, T, C)` | PASS |
| `::test_edge_segments_are_dropped_exactly` | recording cut 3 s after the last stimulus onset; 202 pulse at sample 100; single-pulse boundaries | the last trial's 5 stimulus windows are dropped (no partial trial) while its 201/202 stay; no cue window for the 202 at sample 100. Boundaries: stimulus at T − 1280 kept and at T − 1279 dropped; 202 at 256 kept and at 255 dropped; 201 at T − 512 kept and at T − 511 dropped | exact | plan, [1] P02.2 | partial segments, negative-index wrap | PASS |
| `::test_plateau_pulses_give_same_windows_as_single_sample_pulses` | the same MARK with 3-sample plateaus | `X_psd`, `X_time` and `y` identical to the single-sample case; `find_event_onsets` gives the first plateau sample | exact | [2] §7, [3] §3 | 3 onsets per plateau | PASS |
| `::test_feature_matrix_order_and_channel_major_flatten` | 3 records per code, dict in shuffled order plus an unlisted 203; channel c = sine at 5 + 3c Hz | y in the order 201, 202, 101–105 regardless of dict order, 203 ignored; rows in list order; `X_psd[i, 31c + j] = psd[c, 5 + j]` (5–35 Hz inclusive); argmax of block c = 3c | exact | [3] §5.1, R6 | dict-order concatenation | PASS |
| `::test_channel_major_check_fails_on_frequency_major_flatten` | the same records flattened frequency-major (`psd[:, sel].T`) | the R6 check raises | exact | R6 | **frequency-major flatten, demonstrated** | PASS |
| `::test_psd_bins_depend_on_fs_pf04` | one 256-sample window at fs 256 and labelled fs 250 | 31 bins (217 features) vs 30 bins (210) | exact | [5] bin spacing fs/N; decisions.md 2026-10-24 | PF-04 (fs 250 in P02) | PASS |
| `::test_script_windows_equal_slices_of_continuous_filtered_recording` | 10-trial EBR with the 11 channels in shuffled file order, run through `main` | every saved `X_time` row equals `apply_iir_bandpass(full recording, 256, 1, 60, 4)[name-selected scalp, s:s+256]`, with s from the spec definitions (not from the script); `X_psd` equals the periodogram of those slices, 5–35 Hz, channel-major; y order as spec | atol 1e-12 | R3, PF-06, [1] P02.3 | PF-06 (channels by position) | PASS |
| `::test_r3_check_fails_on_per_window_filtering` | the same check with the continuous filter replaced by identity and each 1 s window filtered on its own (monkeypatch) | the 1e-12 comparison raises; max abs error > 1e-3 | — | R3, PF-14 | **per-window filtering, demonstrated** | PASS |
| `::test_script_tree_all_subjects_root_copy_skip_and_figures` | raw tree S01 (400 µV spike in one stimulus second), S02 (no recording), S03, S04, `misc/`; `--all` | n = 79 (S01), 80 (S03), 80 (S04), with shapes `(n, 7, 256)`/`(n, 217)`; `[-] Skipping S02: ` printed and `misc` ignored; root arrays equal S03, while `X_*` differ from S04, the last subject processed (PF-09); no S02 output; per-subject and root `average_psd_by_condition.png` are valid PNGs | exact | [1] P02.3, plan Q1, PF-09 | PF-09 (root = last subject) | PASS |
| `::test_script_default_subject_is_s03` | S01 and S03 present, no subject flag | only S03 plus the root arrays (40 windows for 5 trials); no S01 folder | exact | [1] P02.3 | — | PASS |
| `::test_script_single_non_root_subject_does_not_write_root` | `--subject S01` | S01 arrays written; no root arrays | exact | PF-09 | root written by a non-S03 run | PASS |
| `::test_plots_written_under_agg` | planted records, one condition empty | the backend is `agg`; the three PNGs have the PNG signature and are larger than 1 kB; no figure left open | — | [1] P02.4, [own] | — | PASS |

Bug variants were checked by running the tests against them. All four checks are permanent tests in the file:

- the PF-07 extractor that does not forward `vpp_min`, at function level and at condition level;
- the frequency-major flatten;
- the per-window filtering.

## Command

```bash
.venv/bin/python -m pytest tests/
```

(`pytest.ini` adds `-q`.)

## Output summary

Full suite: `283 passed in 12.37s`

New file alone (`-v -o addopts=""`): `23 passed in 5.11s`

Before this file the suite had 260 tests (data-engineer handoff), and 260 + 23 = 283. No failures.

## Bugs found

None. Every planned known answer holds on the builders' code at 9d8c52b.

Observation (not a bug, documented by a test): under the spec definitions the 202 window `[onset − 256, onset)` is the same samples as the second 201 sub-window of the same trial, because 202 comes 2 s after 201. Every 202 row of `X_time_windows` therefore duplicates a 201 row. This is the PF-13 definition and is kept by design. It matters for any later analysis that treats 201 and 202 as independent samples.

## Coverage gaps

- Real recordings are not tested (by rule). R-1 counts are for the runner, verifier and reviewer.
- `merge_quality_stats` cohort aggregation and `format_quality_stats` text are tested only indirectly, through the script run that prints them. Neither is a roadmap API.
- The plateau fallback in `find_event_onsets` (no edge for a code) cannot occur under the §3 rule, as the builder's deviation 5 notes, so it is not tested.
- The plan tolerances were not loosened. One expectation of my own was relaxed and is stated in its docstring: the recorded `vpp` ≈ 2A within 1 % for phase-shifted sines whose samples miss the peak. `vpp == ptp(time_data)` is still checked exactly.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

1. REQUEST — `mas/03_ROADMAP.md` P02 tasks 1–4 as copied verbatim in `00_assignment.md`, and `02_plan.md` (Tests required, segment definitions, Q1/Q2) (opened in this run).
2. RULE — `mas/02_REQUIREMENTS.md` §7 testing requirements (event onsets, window index, quality gate `vpp_min` pinned) (opened in this run).
3. RULE — `mas/01_DATA_SPEC.md` §2 (EBR header layout for the test writer), §3 (onset rule, timing, 40 trials), §5.1 (segments, order, 217 features), §6 (opened in this run).
4. RULE — `mas/05_PITFALLS.md` PF-07, PF-09, PF-13; `mas/RULES.md` R3, R6; `mas/state/decisions.md` 2026-10-24 P02 rows (fs 256, figure paths, gate on filtered windows) (opened in this run).
5. DOCS — SciPy 1.18.1 `scipy.signal.periodogram` (defaults: boxcar, constant detrend, density, onesided). The analytic density A²N/(2fs) for an on-bin sine follows from those defaults (version checked in `.venv`).
6. HANDOFF — `03_changes_signal-processing.md`, `03_changes_data-engineer.md` (APIs, deviations, script importables).

## Questions

ACK 02_plan.md synthetic-tester 2026-10-24
