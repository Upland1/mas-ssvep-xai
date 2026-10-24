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

## Round 2

Trigger: `07_review.md` pre-run audit round 1 (b4bc757), required fix 2. Builder code at
1869c0a / 78ea210 (`response_bin`, `spectrum_peaks` `k_resp`/`f_resp`/`power_resp`,
`specificity_ratio`, `format_peaks` for codes without f0). Six tests appended to
MODIFIED `tests/test_p03_exploration_known_answer.py` (18 tests in the file now).

Analytic bin table used by the tests (T = 256 samples, header fs 256; in-band harmonics
5–35 Hz): response bin = round(f·256/256); nearest-labelled bin on the legacy axis
k·250/256 = round(f·256/250).

| h·f0 (Hz) | 24 | 20 | 15 | 30 | 10.909 | 21.818 | 8.571 | 17.143 |
|---|---|---|---|---|---|---|---|---|
| response bin | 24 | 20 | 15 | 30 | 11 | 22 | 9 | 17 |
| nearest-labelled at fs 250 | 25 | 20 | 15 | 31 | 11 | 22 | 9 | 18 |

(computed with `.venv/bin/python -c` over `np.arange(129)*250/256`; 24.576 → 25, 30.72 → 31, 17.55 → 18.)

| Test id | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `::test_response_bins_legacy_axis_24_30_17` | A = 2 sinusoids at 24, 30, 120/7 Hz sampled at 256 Hz, axis fs 250, header 256 | `k_resp` 24/30/17 = argmax; `k` 25/31/18 ≠ argmax; labels k·250/256; 24 and 30 Hz: `power_resp` = (N/2)²A² = 65536, nearest-labelled bin ≤ 1e-12 of it; 17.143 Hz: response > 10× nearest-labelled | exact bins; 1e-9 labels; rtol 1e-9 power | DFT, audit fix 2a | response bin computed on the labelled axis, round(f·T/250) (variant run, fails) | PASS |
| `::test_response_bins_through_class_spectra_and_console` | legacy subject, default fs 250 | per class `(k_resp, k)` = table; console `1f0 response bin 24 (23.438 Hz)` + `, nearest-labelled bin 25 (24.414 Hz)`; 103 `2f0 response bin 30 (29.297 Hz)` + `31 (30.273 Hz)`; 105 `2f0 response bin 17 (16.602 Hz)` + `18 (17.578 Hz)`; no nearest-labelled for 102, 104 | exact | table, Round 2 console format | — | PASS |
| `::test_response_bin_equals_nearest_at_header_fs` | same, fs 256 | all eight harmonics `k_resp == k` = 24, 20, 15, 30, 11, 22, 9, 17, labels k Hz; console has `fs=256 (header)` and no `nearest-labelled` | exact | table, audit fix 2b | — | PASS |
| `::test_specificity_class_specific_analytic` | each class: A = 10 sine (phase 0) at its own exact response bin (24/20/15/11/9) + B = 50·δ[n] on O1/Oz/O2 | own = B² + (AN/2)² = 1640900, others' median = B² = 2500, ratio = 1 + (AN/2B)² = 656.36 for every class, 4 others (observed 101: 656.3599999999991) | rtol 1e-9 | DFT of a sinusoid and an impulse | specificity read at the nearest-labelled bin (25 for 101; variant run, ratio 1, fails) | PASS |
| `::test_specificity_shared_rhythm_near_one` | same 120/11 Hz sine (A = 10, phase 0) in all classes + N(0, 1), seed 11, 20 windows | 104: k 11, ratio 1 within 2 % (derived: cross-term ≈ 1.8 % per window-channel, /√60 → 0.23 %, own vs median ≈ 0.33 % = 1σ; 2 % > 6σ); observed 0.9987388767116933; every class's maximum at bin 11; noise-free: every ratio = 1 within 1e-12 | 2 %; 1e-12 | DFT, sample-mean variance | — | PASS |
| `::test_format_peaks_with_rest_codes` | conditions (201, 202, 101..105), 201/202 with a 30 Hz rhythm | no exception, 7 lines; 201/202 lines exactly `  S01 <code>: n=<n>, max in band at 29.297 Hz (bin 30, P=…); band median P=…` (no target, response bin or specificity); 201/202 not in `specificity` and not counted as others (101: `n_others` 4) | exact | audit fix 1c, 01_DATA_SPEC §6 | — | PASS |

The Round 1 per-class variant (classes from `target_conditions`) still fails its check
after the `format_peaks` fix: 7 spectra instead of 5 (`AssertionError`).

### Command and output

```bash
.venv/bin/python -m pytest tests/
```

```
311 passed in 20.72s
```

(305 after the builder's Round 2 + 6 new.)

### Findings

No bug found in the Round 2 code. Round 1 observation 1 (`format_peaks` TypeError on
codes without f0) is fixed and covered by `test_format_peaks_with_rest_codes`.

### Coverage gaps (Round 2)

- `specificity n/a` (no other class with windows) and the out-of-axis `ValueError` of
  `spectrum_peaks` are not exercised.

### Reference consultations (R11)

None.

### Sources (Round 2)

6. HANDOFF — `mas/state/phases/P03-exploration/07_review.md`, pre-run audit Round 1, required fixes 1 and 2.
7. HANDOFF — `mas/state/phases/P03-exploration/03_changes_signal-processing.md`, Round 2 (APIs, console format).

Status: READY (Round 2).
