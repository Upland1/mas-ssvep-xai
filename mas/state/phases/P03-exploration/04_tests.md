# P03 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_signal-processing.md, mas/RULES.md, mas/state/decisions.md (P02, P03 rows), mas/01_DATA_SPEC.md §5.1, §6, mas/05_PITFALLS.md PF-04/05/06/07/09
Branch: phase/P03-exploration (builder HEAD 1ce4892)

## Tests added

All in NEW `tests/test_p03_exploration_known_answer.py` (12 tests). Signals sampled at
256 Hz on 256-sample windows; analysed at fs 250 (legacy) unless stated. Inputs built in
the test with fixed seeds; legacy folders written to `tmp_path` with `X_psd_features`
produced by the P02 extractor (`extract_clean_subwindows_psd` + `prepare_feature_matrix`),
not by the code under test.

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `::test_fft_power_peak_15hz_exact_bin` | 6 × 7 × 256 windows, 15 Hz sines + noise, fs 256 | argmax bin 15 everywhere, label 15.0 Hz; unit sine |rfft|² = (N/2)² = 16384 | exact bin; rtol 1e-9 | DFT | rfft over the channel axis (variant run, fails) | PASS |
| `::test_legacy_fs_shift_24hz` | 24 Hz sine at 256 Hz, analysed fs 250 and 256; 5 planted classes (bins 24/20/15/11/9) | bin 24, label 23.4375 Hz (fs 256: 24.0); powers identical across fs; every class at k·250/256; nearest-target bin for 101 is 25 (24.4140625 Hz), for 102–105 bins 20/15/11/9 | 1e-9 | PF-04, DFT | analysis ignoring `--fs`, always 256 (variant run, fails) | PASS |
| `::test_occipital_by_name_reordered` | names `O1, PO3, Oz, O2, POz, PO4, PO8`; classes on O1/Oz/O2 (positions 0, 2, 3); 33 Hz decoy (3× amplitude) on positions 4, 5, 6 | channels [0, 2, 3]; each class at its planted bin | exact | PF-06, 01_DATA_SPEC §6 | positional `[4, 5, 6]` (variant run: every class peaks at 33 Hz, fails) | PASS |
| `::test_occipital_by_name_through_config` | same array; config with the reordered `channels.scalp`; script `--fs 256` | console `channels [0, 2, 3] = ['O1', 'Oz', 'O2']`, maxima 24/20/15/11/9.000 Hz, no 33 Hz | exact | PF-06 | — | PASS |
| `::test_per_class_panels_planted_and_rest_excluded` | legacy folder: 8 × 201 + 4 × 202 with 80 µV 30 Hz on all channels; 10 rows per class at planted bins | plot called once with 5 spectra in order 101..105, counts 10 each, each argmax at its bin, title contains `fs=250 (legacy)`, console maxima at k·250/256, no `S01 201`/`S01 202` line, PNG non-empty | exact | 02_plan P03.1, 01_DATA_SPEC §6 | classes from `target_conditions` without removing 201/202 (variant run: 7 classes, fails) | PASS |
| `::test_quality_mask_planted_counts_and_thresholds_as_passed` | 60 stimulus windows; planted 3 × 103 +500 µV spike (PO4), 2 × 105 flat PO3, 1 × 101 +150 µV spike (POz) | legacy limits: 5 rejected = the planted rows (103: vpp_high 3; 105: vpp_low 2, std_low 2), 150 µV row kept; `vpp_max=100`: 6 rejected (101: vpp_high 1); `thresholds` equal the values passed | exact | 02_plan P03.2, Q2; R5 | — | PASS |
| `::test_quality_mask_vpp_min_is_explicit` | 20 windows of 1.5 µV sines (0.5 < Vpp < 5 µV) | legacy mask keeps 20/20; shared default `vpp_min=5.0` rejects all 20; `quality_mask` without `vpp_min` → TypeError; script default thresholds = vpp [0.5, 200], std [0.5, 60]; console `kept 20/20, rejected 0` | exact | PF-07, 02_plan Q2, R5 | mask forwarding every threshold except `vpp_min` (variant run, fails) | PASS |
| `::test_psd_features_layout_217_210_and_p02_equality` | 9 × 7 × 256 windows, channel c at bin 6 + 3c | fs 256: (9, 217), bins 5..35; fs 250: (9, 210), bins k = 6..35 labelled k·250/256; channel-major argmax per block; fs 256 equals the P02 extractor + `prepare_feature_matrix`; values = 2 |rfft|²/(fs N) | exact shapes; rtol 1e-12 (P02 equality), 1e-9 (density) | 01_DATA_SPEC §5.1, PF-04, periodogram definition, R6 | — | PASS |
| `::test_visualize_explore_subject_psd_matches_saved_at_header_fs` | 60 windows, P02-built saved PSD | fs 256: X (60, 217), `psd_check == 0.0`, counts 12; fs 250: X (60, 210), `psd_check` None | exact | P02 layout, PF-04 | — | PASS |
| `::test_channel_count_mismatch_fails_loudly` | 8 names (PO7 + config v1) for 7 channels; 7 names for 8 | ValueError in name lookup, per-class spectra, `explore_subject`; both scripts print `[-] Skipping S01: 8 channel names`, exit 1, no PNG | — | 02_plan, PF-05/06 | — | PASS |
| `::test_scripts_smoke_tree_root_arrays_ignored` | tree: S01 (planted), S02 (empty), S04 (X 320 / y 317), `S03_backup` (arrays), root arrays of another subject (125 windows, all at 33 Hz) | `--all`: S01 from its folder (62 windows, planted maxima), skip lines for S02 (no file) and S04 (length mismatch), `S03_backup` not discovered, no 33 Hz; `fs=250 (legacy)` in console and both figure titles; both PNGs non-empty; `visualize_data` kept 62/62, 10 per class, X (50, 210); `--fs 256`: `fs=256 (header)`, X (50, 217), `max |computed - saved| = 0` | exact | PF-09, 02_plan script smoke, 02_REQUIREMENTS §4 | loader reading the root arrays (variant run, fails) | PASS |
| `::test_script_module_entry_point` | same tree, `python -m scripts.exploration.diagnose_occipital_spectra --all` in a subprocess | exit 0, same console checks, PNG written | exact | 02_REQUIREMENTS §4 | — | PASS |

Every "variant run" is executed inside the test (monkeypatch) and asserted to fail the
same check (`pytest.raises(AssertionError)`; for the 201/202 variant also `TypeError`).

## Command

```bash
.venv/bin/python -m pytest tests/
```

## Output summary

```
303 passed in 20.02s
```

(291 before this phase's known-answer suite + 12 new; P03 file alone: slowest test 4.38 s.)

## Findings for the builder / reviewer

No bug found in the P03 code. Observations, none blocking:

1. `format_peaks` raises `TypeError` for a condition with no entry in `STIM_FREQS_HZ`
   (201/202). Not reachable with `stimulus_conditions`, but a future caller that
   passes all target conditions crashes instead of printing a line (seen in the
   201/202 variant).
2. Confirmed by an independent computation: at fs 250 the printed "1f0 nearest bin"
   for 101 is bin 25 (24.414 Hz), while a 24 Hz response sits in bin 24 (23.4375 Hz),
   as the builder notes. The reviewer should read the band-maximum line for 101 in
   the legacy run, or the `--fs 256` run.

## Coverage gaps

- PNG content is not inspected (panel count and titles are checked on the arguments
  passed to the plotting functions, through a pass-through spy; the files are checked
  to exist and be non-empty).
- `--subjects` selection and `--features` choices are not exercised.
- Stale figures of a later-skipped subject are not removed (builder's known limitation);
  not tested.
- No tolerance loosened from the plan.

## Reference consultations (R11)

None.

## Sources

1. REQUEST — `mas/state/phases/P03-exploration/02_plan.md` "Tests required", Q1, Q2.
2. RULE — `mas/01_DATA_SPEC.md` §5.1 (256-sample windows, 217 = 7 × 31 layout), §6 (occipital set by name, 5-class = stimulus windows).
3. RULE — `mas/05_PITFALLS.md` PF-04, PF-05, PF-06, PF-07, PF-09.
4. RULE — `mas/RULES.md` R5, R6.
5. REQUEST — `mas/state/phases/P03-exploration/03_changes_signal-processing.md` (APIs, flags, bin-25 note).

## Questions
