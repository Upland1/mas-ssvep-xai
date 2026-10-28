# P16 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/01_DATA_SPEC.md §3/§5, mas/02_REQUIREMENTS.md §3/§6
Branch: phase/P16-continuous-filtering
Commit(s): ce017ea (orchestrator files), b6b58e5 freeze_baseline, d51ab6b windowing, b010141 window_quality, 7925a53 config, 4b06b4d build_windows + load_subject, f0b1239 edge-effect demo, a242a9b grep fix, plus the handoff commit

## Questions

ACK 02_plan.md data-signal 2026-10-27

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `scripts/freeze_baseline.py` | NEW | snapshot of data/processed, reports, outputs/reports, configs into `baselines/<tag>_<date>/`; read-only; refuses a repeated tag; MANIFEST.json; baseline_summary.csv; `superseded/`; configs read from git at the merge-base of HEAD and main (`--configs-git-rev` overrides) | P16.1 | own |
| `src/preprocessing/windowing.py` | NEW | `load_session`, `event_onsets`, `WindowIndex`, `windows_per_segment`, `segment_starts`, `build_window_index`, `cut_windows`, `fbcca_filter_bank`, `fbcsp_filter_bank`, `filter_bank`, `band_windows` (continuous / per_window), `select_clean_bands`, `compare_trial_ids` | P16.2 | R3, PF-14, PF-04 |
| `src/preprocessing/signal/filters.py` | MODIFIED | + `apply_notch`, `broadband_filter` | P16.5 | own |
| `src/preprocessing/window_quality.py` | NEW | `subject_quality_gate`, `ringing_time_sec`, `artifact_mask`, `quality_params_from_config` | P16.4 | R5, PF-14 |
| `scripts/diagnostics/demo_edge_effects.py` | NEW | both-ways bands, error table (schema §6), 3-panel figure | P16.3 | PF-14 |
| `scripts/build_windows.py` | NEW | builds §5.2 folders; `--check-legacy-starts`; `--resume`; atomic folder write | P16.5 | spec §5.2 |
| `configs/pipeline_config.yaml` | MODIFIED | final config §3 (highcut 90, notch, `quality:`, `filter_bank:`) | P16.5 | spec §3 |
| `scripts/preprocessing/run_preprocessing.py` | MODIFIED | pins the legacy highcut (`LEGACY_HIGHCUT_HZ = 60`) so the config change does not alter legacy builds | P16.5 | own |
| `src/io/subject_data.py` | NEW | `find_project_root`, `discover_subjects`, `is_built`, `built_dir_name`, `resolve_channel_names` (re-export), `load_subject` | P16.6 | R1, R3, R5, R8 |
| `tests/test_p16_freeze_baseline.py`, `test_p16_windowing.py`, `test_p16_window_quality.py`, `test_p16_build_windows.py`, `test_p16_subject_data.py`, `test_p16_edge_effects.py`, `tests/p16_synth.py` | NEW | known-answer tests on synthetic data and a fake .ebr; `p16_synth.write_built_subject(root, subject, filter_mode, ...)` builds a synthetic built folder for other builders' tests | all | own |
| `tests/test_p01_config_known_answer.py` | MODIFIED | expected config is now v3 (P16) | P16.5 | spec §3 |

## `load_subject` API (for ml-engineer and connectivity-stats)

`load_subject(sub_dir, conditions=(101..105), quality_mode="shared"|"shared-no-guard"|"per-script", bands=(), fs_override=None, scalp=None, thresholds=None, channel_fail_fraction=0.5)` takes the subject folder (`<root>/<S>`), not the root. Returned dict keys:

- `X (n, C', T)` windows of kept channels, `y`, `trial_ids` (one per segment; the R8 smoothing key), `cv_groups` (the R1 group key: equal to `trial_ids` except that a 202 window gets the id of its 201 twin, PF-13; only differs when 202 is selected), `window_starts`, `sub_idx`, `offsets` (None on legacy), `bands {bank: (n, B, C', T)}` (built only; legacy raises ValueError), `channel_names` (kept), `channels_dropped`, `channels_all`.
- `fs`, `fs_source` (`meta` | `legacy-assumed` (250) | `override`), `built`, `source` (text for headers), `filter_mode`, `smoothing` (`"trial"` on built, `"mod5"` on legacy), `trial_ids_approximate`, `n_trials`, `n_selected`, `n_rejected`, `quality` (mode, source, valid_mask over selected rows, rows, channels, `rejections_by_label`, guard_sec, artifact_fraction, params), `meta`.
- Built rows are ordered by condition, trial, offset; the loader raises RuntimeError if a trial id is split or offsets do not increase (R8). Smoothing: reset where `trial_ids` changes.
- Legacy folders: all three quality modes mean the P07 two-tier per-script gate on the selected windows (equals `prepare_subject`; tested); channels from `channels.json` / `scalp` / count.
- `per-script` on a built folder reruns the P07 two-tier gate on the selected windows of that folder (explicit `GATE_THRESHOLDS`).
- The saved `trial_ids.npy` is one id per event segment as in spec §5.2; 201 and 202 get different ids. Use `cv_groups` for `StratifiedGroupKFold` whenever both are selected.

## Legacy behaviour implemented

`--filter-mode per_window` (cut, then `filtfilt(b, a)` per window, as the P05 extractors; labelled legacy in the module docs and metadata), legacy folders in `load_subject` (fs 250, `mod5`, reconstructed ids), `--quality per-script`, `fs_override`. `run_preprocessing.py` keeps its 1-60 Hz band (pinned constant) after the config moved to 90 Hz.

## Differences from the cited examples

None cited. The sub-band filters reuse the P05 constants (`SUBBAND_LOW_HZ`, `CHEBY_*`, `DEFAULT_SUBBANDS`) with an `sos` form for the continuous mode and the original `(b, a)` form for per-window mode.

## Deviations from the plan / spec

1. Trial ids: spec says one id per segment, kept. PF-13 is handled by the derived `cv_groups` (no new file); `build_window_index(cue_shares_cross_id=True)` exists but is off by default (sharing the id broke the (trial, offset) ordering check because the 202 window sits at offset 0 inside the 201 run).
2. Reason code 3 (raw gate) is never produced (`source: filtered`; P19).
3. Guard `auto` is measured on the zero-phase impulse response of the broadband filter plus all filters of the requested banks, for both filter modes (so per_window and continuous builds share the same guard). Measured: 0.902 s (230 samples at 256 Hz).
4. `--check-legacy-starts` compares reconstructed trial ids on stimulus windows only (the 201/202 twin sharing is by design).
5. Layout of the snapshot: `baselines/v1_<date>/<repo path>`; MANIFEST keys by repo path with `stored_as` for the superseded files. The baseline_summary covers n_subjects, augmentation, GNN, gate and connectivity cohort CSVs.
6. `LEGACY_HIGHCUT_HZ = 60` in `run_preprocessing.py` (not requested): required so that `make preprocess` still reproduces the frozen arrays after the config change.

## How to run / reproduce (verifier)

```bash
.venv/bin/python -m scripts.freeze_baseline --tag v1 --note "Era A/B outputs before P16 (main 97a29be)"   # add --configs-git-rev 97a29be if main moved
.venv/bin/python -m scripts.diagnostics.demo_edge_effects --subject S03
.venv/bin/python -m scripts.build_windows --filter-mode per_window --subjects S01 S02 S03 S04 S05 --session OO --check-legacy-starts
.venv/bin/python -m scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --check-legacy-starts
# the guard-effect row (c') needs no extra build: load_subject(..., quality_mode="shared-no-guard") reads valid_mask_no_guard
```
Flags: `--out-root`, `--window-sec`, `--stride-sec` (saves under `w<len>_s<stride>/`), `--banks`, `--guard-sec auto|<s>`, `--resume`. The script refuses an out-root holding legacy arrays or equal to `data/processed`.

## How I verified

- Tests: `pytest tests/test_p16_*.py` all pass (new: freeze 3, windowing 12, window_quality 10, build_windows 7, subject_data 10, edge_effects 3). Failing-on-bug tests: PF-14 (`test_per_window_edge_error_much_larger_than_centre_pf14`, `test_demo_on_fake_recording_edges_exceed_centre...`: fail if bands are filtered per window and called continuous), PF-04 (`test_fs_override_and_pf04_tone_bin`, `test_window_index_uses_fs_given_not_a_literal`), R5 (`test_every_threshold_is_required`), R8 (`test_rows_not_ordered_by_trial_and_offset_are_refused`), PF-13 (`test_cv_groups_put_the_cue_window_with_its_fixation_twin`).
- Full suite at a242a9b: `pytest tests -q` exit code 0, no failures, ~9 min (the summary line is not printed by the quiet config; log mas/state/scratch/p16_suite_ds.txt).
- Smoke on real data (S03 first, then S01, S02, S04, S05), outputs in `mas/state/scratch/p16_ds/` (deleted afterwards; logs not kept in the repo), commands as above with `--out-root`/`--reports-dir`/`--figures-dir` in scratch; nothing was written to `data/processed`, `reports`, `outputs`, `baselines`.

Smoke numbers (console output of `build_windows --check-legacy-starts` and `demo_edge_effects`, S03 unless stated):

| Item | Value |
|---|---|
| fs from header | 256 Hz, 154,896 samples |
| windows / trial ids | 320 / 120 (all five subjects) |
| valid / valid without guard | 310 / 313 (S01 320/320, S02 301/309, S04 309/313, S05 319/320) |
| channels | S03 kept 7, dropped PO7 (fail 100 %) |
| guard | 0.902 s; 14 artifact blocks (0.58 % of the recording, 1.94 % guarded) |
| rejections S03 | 101: 1 own + 1 guard; 102: 2 own; 105: 1 own + 1 guard; 201: 2 own + 1 guard; 202: 1 own |
| legacy starts | `n_legacy = n_built = n_equal`, max abs diff 0, every condition of S03 (S01, S02, S04, S05 also equal; checked by a script over the output) |
| edge effects S03 (edges % / centre % / ratio) | fbcsp 7-12: 53.2/6.5/8.17; 13-17: 56.7/7.6/7.45; 18-26: 33.1/1.58/21.0; 27-36: 33.8/1.08/31.2; 38-52: 23.0/0.15/150; fbcca 6-90: 28.3/7.4/3.81; 14-90: 26.2/2.9/8.99; 22-90: 24.5/1.4/17.6 |

Runtimes (one machine, CPU): `build_windows` one subject continuous 0.8 s (incl. legacy check 2.0 s wall with imports), per_window 0.3 s; four subjects with the check 2.5 s; `demo_edge_effects` S03 2.0 s wall. Verifier estimate: every build and the demo are under a minute; the plan's "2 x 5 min" for builds is a large overestimate. The full pytest suite takes about 9 minutes on this machine (hook limit of one minute is already exceeded by the earlier phases).

## Carry-forward results

- **9a (P02, S03 first-trial PO8):** the first trial of S03 (8 windows from sample 1280) has built reasons 3 valid / 5 own gate / 0 guard; mean Vpp per channel PO7 543.5, PO8 325.4, PO4 109.2, the others 70-82 uV, so the PO8/PO7 rejections are genuine large amplitudes, not a filter start-up transient. The start-up measure (continuous output versus the same filter on the recording extended by 30 s of odd reflection) is at most 1.8e-06 of the window std on every channel (PO8 9.96e-08). The legacy gate rejected 3 of the 8 first-trial windows (starts 1280, 1536, 1536; the two at 1536 are the 201 second window and its 202 twin, PF-13); the shared gate rejects 5 because its limits are tighter (Vpp 120 vs 200). Conclusion: no start-up transient. Printed in the `startup S03:` lines of the build log.
- **9c (P11 D-2, trial ids legacy reconstruction vs true, stimulus windows, "windows in inconsistent groups"):** S01 0 of 200, S02 39 of 199, S03 0 of 200, S04 38 of 198, S05 0 of 200 (40 reconstructed and 40 true trials in every subject). Printed in the `trial-ids` lines. S02 and S04 are as expected.
- 9b (`oof_space(splits=None)`) is not in my rows.

## Left to do / known limitations

- `freeze_baseline` was not run on the real tree (settled point 1); tests use a temp tree. The `baseline_summary.csv` connectivity rows are keyed `connectivity_<method>`, metrics `obs_diff[cond@freqHz]`, `n_edges_sig_fdr[...]`.
- `load_subject` per-script mode on built folders takes thresholds from `GATE_THRESHOLDS` unless `thresholds=` is passed; the ml-engineer should pass the config values explicitly.
- Window length != 1 s with the 202 lookback of 1 s yields no 202 windows (windows_per_segment 0), by design.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

| # | Trigger | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| - | - | - | - | - |

## Sources

1. `mas/01_DATA_SPEC.md` §3, §5, §6; `mas/02_REQUIREMENTS.md` §3, §6 (opened in this run).
2. `mas/05_PITFALLS.md` PF-04, PF-13, PF-14 (opened via the plan's table) and P05/P07 code in `src/` (opened in this run).
3. Chen et al. 2015, J. Neural Eng. 12:046008 (FBCCA bank), as cited in `src/features/ssvep/fbcca_extraction.py`.
