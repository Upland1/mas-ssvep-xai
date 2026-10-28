# P17 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_data-signal.md, 03_changes_ml-engineer.md, decisions.md (P17 rows), mas/RULES.md, mas/05_PITFALLS.md (PF-02/03/13)

No leak found. The 93.9 -> 99.5 % gain on S03 is reproduced in mechanism on synthetic data (control c) and a leaky variant is detected by the null control (a).

## Tests added (all synthetic, no generated or ignored file read)

NEW `tests/test_p17_independent_known_answer.py` (22 tests) and NEW `tests/test_p17_leak_controls.py` (12 tests). The builders' own files (`test_p17_windowing.py`, `test_p17_benchmark.py`) are untouched.

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `independent::test_centres_are_multiples_and_midpoints...` | centre lists | 15 values k x {24, 20, 15, 10.91, 8.57}, target-major; midpoints 9.74, 12.955, 17.5, 22.0 | 1e-9 | arithmetic on DATA_SPEC section 2 | band order changed to k-major (mutant `kmajor`) | PASS |
| `independent::test_skip_rule[5 cases]` | fs 256/200/128/100, max_hz 90/45, notch 60 | skipped sets {60}, {60}, {60,72}, {60,72}, {60,72,48,45}; kept bands <= min(max, nyq-1), none containing 60 | exact | arithmetic on band edges | notch not excluded (mutant `no_notch`) | PASS |
| `independent::test_double_frequency_tone_lands_in_its_own_harmonic_band[101..105]` | pure tone at 2 f0 for each target, continuous bank | maximum power in the band centred on 2 f0, others < 5 % of it; bank centres = the 14 expected in order | 1e-9 on centre | analytic | band order / index shift (R6); no-notch mutant shifts the order | PASS |
| `independent::test_meta_order_is_array_order_and_banks_concatenate...` | built folder, all banks | meta edges = `build_bank` edges; `harm` = fbcsp (5) + harmonic (14), `harm+mid` = + intermediate (4), concatenated on the band axis exactly | exact | construction | misordered concatenation | PASS |
| `independent::test_four_banks_do_not_touch_two_bank_files...` | same recording, two vs four banks, `guard_sec=1.5` | extra files only the 2 new `X_bands_*`; every other file byte-identical except meta; fbcca/fbcsp meta equal | sha256 | the plan's byte-identity rule | silent change of P16 files | PASS |
| `independent::test_six_classes_use_201_only_with_uniform_priors_and_true_trial_groups` | built folder with 202 windows, spy on LDA `fit` and on `assert_no_shared_trials` | confusion classes 101..105, 201 (no 202); every fitted `priors_` = 1/6; guard runs once per repeat on groups == loader `trial_ids`; rest rows <= 2 per rest trial | allclose | PF-13, C-5, R1 | frequency priors (mutant `freq_priors`); 202 as rest (mutant `rest202`) | PASS |
| `independent::test_five_classes_keep_the_default_prior` | 5-class run | priors vector of length 5 | exact | — | 5-class path altered | PASS |
| `independent::test_six_classes_on_a_legacy_root_raise` | legacy synthetic folder | ValueError | — | settled point 3 | — | PASS |
| `independent::test_metrics_on_a_hand_built_confusion` | confusion [[6,2,2],[1,7,2],[3,1,6]] on 101, 102, 201 | FalseAct 40.0, Missed 20.0, StimCorrect 65.0, BalAcc 63.33, confusion matrix returned unchanged | 1e-9 | hand arithmetic | FalseAct/Missed swapped (mutant `swap_rates`) | PASS |
| `independent::test_row_metrics_are_the_definitions_applied_to_the_summed_confusion` | one-repeat 6-class run | row FalseAct/Missed/StimCorrect/BalAcc recomputed from the returned confusion matrix | 0.006 (rounding) | definitions | wrong column mapping | PASS |
| `independent::test_confusion_file_is_the_sum_of_the_subject_matrices` | `main` on two subjects | `Sum` block = S01 + S02 | exact | construction | — | PASS |
| `independent::test_c1_mean_row_skipped_unless_requested` | CSV with Mean row | no `Mean` subject for new tags; `MEAN` = 50.0; kept with `skip_mean_row=False`; only `v1` legacy | exact | C-1 | — | PASS |
| `independent::test_c2_no_threshold_fallback_and_fs_override_guard` | built / legacy root | `thresholds=None` raises; `fs` on built raises, CLI rc 1; with `allow_fs_override` runs; legacy `fs` still runs | — | C-2 | — | PASS |
| `independent::test_c2_per_window_build_meta_is_legacy` | per_window vs continuous meta | `legacy` True / False | exact | C-2 | — | PASS |
| `leak::test_null_recording_five_classes_is_at_chance[base,harm,harm+mid]` | 40 trials, noise only, labels from marks, real build + benchmark, 3 repeats | 1.0 s accuracy < 0.2 + 4 sqrt(0.2 x 0.8 / 200) = 31.3 %; 2.0 s < same bound with n = 100 (36.0 %); not below 8.7 % | binomial 4 sd, one-sided | binomial | in-fold CSP fit replaced by a full-data fit (mutant `leaky_csp`: 60-87 %) | PASS |
| `leak::test_null_recording_six_classes_balanced_accuracy_is_at_chance[3 banks]` | same, 6 classes | BalAcc < 1/6 + 4 sd (sd from the per-class window counts of the confusion matrix) | binomial 4 sd | binomial | rest label from 202 (mutant `rest202`) | PASS |
| `leak::test_tone_does_not_carry_into_other_trials_windows[4 banks]` | noise-free block of the real protocol, neighbouring trials with different tones (class 101 + i mod 5), window index from the real code, continuous filtering of fbcca, fbcsp, harmonic, intermediate | max |fixation + cue windows| < 1e-4 x max |stimulus windows|; fixation onsets 15 s apart | 1e-4 | DATA_SPEC section 3 spacing (below) | tone carried into other trials | PASS |
| `leak::test_the_leak_measure_has_power_at_a_short_spacing` | single tone, window starting 0.5, 2, 5 s after it ends, all 14 harmonic bands | worst relative leak > 1e-2 at 0.5 s, < 1e-3 at 2 s, < 1e-8 at 5 s | decades | control for the test above | — | PASS |
| `leak::test_second_harmonic_only_tone_is_found_by_harm_not_by_base` | tone at 2 f0 only, 0.4 uV against noise std 5 uV | base 1.0 s accuracy < 31.3 %; harm and harm+mid above it and > 8 pp above base | binomial + 8 pp | gain mechanism | — | PASS |

## Spacing used for control (b), and its source

`mas/01_DATA_SPEC.md` section 3: one trial lasts 15 s, 201 at t, 202 at t+2, 203 at t+4, stimulus at t+5 for 5 s, 200 at t+10, next 201 at t+15. The synthetic block (`tests/p16_synth.make_block`, the same marks) therefore has 5 s of silence after a stimulus before the next trial's fixation window, and 3 s between the cue/fixation windows and the tone onset of the same trial (zero-phase filtering also acts backwards). The tone sits exactly in the 5 s stimulus segment, the windows are those of `build_window_index` (fixation 2 windows, cue 1, stimulus 5).

## Leak-control results (numbers from the runs of this session; script outputs reproduced by the tests' fixtures, recording seed 3, 3 CV repeats)

(a) Null recording, 200 clean windows (5 classes), 280 (6 classes). Chance bound 31.3 % (5-class 1.0 s).

| bank | 5-class 1.0 s | 5-class 2.0 s | 6-class BalAcc 1.0 s | 6-class BalAcc 2.0 s |
|---|---|---|---|---|
| base | 20.00 | 20.83 | 18.54 | 19.72 |
| harm | 23.67 | 25.17 | 19.51 | 20.97 |
| harm+mid | 22.67 | 24.67 | 20.35 | 22.22 |

Three other noise seeds (4, 5, 6; 5-class 1.0 s, base / harm / harm+mid): 13.83 / 16.50 / 14.17; 17.00 / 17.33 / 16.17; 22.33 / 21.83 / 22.33. The harm - base difference over the four seeds is +3.67, +2.67, +0.33, -0.50 pp (mean +1.5, spread comparable to the 2.8 pp sd of one run): no systematic excess. The same control run with the in-fold CSP fit replaced by a full-data fit (mutant) gives 60.17 / 85.33 / 87.17 % (1.0 s) and 72.17 / 92.33 / 94.83 % (2.0 s), so a leak of the kind that fits the CSP outside the fold would show as a jump of 40-65 pp at chance level.

(b) Carry-over at the protocol spacing, tone amplitude 1 (peak inside stimulus windows: fbcca 0.998, fbcsp 1.069, harmonic 1.034, intermediate 0.480). Maximum over fixation and cue windows, relative to the stimulus-window peak: fbcca 6.5e-6, fbcsp 2.9e-7, harmonic 9.3e-7, intermediate 2.6e-6 (limit 1e-4). Control: worst relative leak over the 14 harmonic bands at a gap after the tone of 0.5 s 3.4e-2, 1.0 s 1.8e-3, 2 s 6.4e-5, 3 s 1.0e-6, 5 s 3.0e-10 (before onset, 3 s: 9.4e-7). The ringing (about 1.05 s to 1 %) cannot carry one trial's class into another trial's windows at a 5 s / 3 s spacing; it would at gaps below about 2 s.

(c) Tone at 2 f0 only (0.4 uV, noise std 5 uV), 5-class, 3 repeats, 1.0 s / 2.0 s: base 28.67 / 31.00 (SD of 1.0 s over repeats 3.51); harm 43.17 / 47.83 (3.55); harm+mid 42.17 / 48.67 (1.26). Chance bound 31.3 %. Base is inside the bound, harm is +14.5 pp above it. At 0.8 uV base reaches 86.5 %: the base CCA (3 harmonics) and the broad CSP bands do see a larger second-harmonic tone; the narrow bank wins by SNR (it is a gain on weak harmonic content, not a free gain).

Interpretation: the narrow +-1 Hz bands raise the SNR of tones at 2 f0 and 3 f0 in the CSP stage, in-fold; with noise only they stay at chance, and the filters do not couple trials. The S03 gain is therefore plausible without a leak, but these controls do not prove that real S03 has no other leak (for the reviewer: real data have 8 trials per class and genuine harmonic content).

## Mutants (monkeypatched at test time through a scratch plugin; no `src/` file edited; each caught, then nothing to revert)

| Mutant | First failing test |
|---|---|
| CSP fitted on all windows instead of the training fold (`legacy_eval.fold_matrices`) | `leak::test_null_recording_five_classes_is_at_chance[base]` |
| rest label 202 instead of 201 (`B.REST_LABEL`) | `leak::test_null_recording_six_classes_balanced_accuracy_is_at_chance[base]` |
| LDA priors from class frequencies in 6 classes | `independent::test_six_classes_use_201_only_with_uniform_priors...` |
| FalseAct and Missed swapped | `independent::test_metrics_on_a_hand_built_confusion` |
| harmonic centres k-major | `independent::test_centres_are_multiples_and_midpoints...` |
| notch exclusion removed | `independent::test_double_frequency_tone_lands_in_its_own_harmonic_band[101]` |

(Each run used `-x`, so only the first failure is listed.)

## Command

```bash
.venv/bin/python -m pytest tests/test_p17_independent_known_answer.py tests/test_p17_leak_controls.py -q -o addopts=""
.venv/bin/python -m pytest tests/ -q -o addopts=""
```

Suite (`pytest tests/ -q -o addopts=""`, log mas/state/scratch/p17_suite_tester.log): `1167 passed, 22 warnings in 682.49s (0:11:22)`
