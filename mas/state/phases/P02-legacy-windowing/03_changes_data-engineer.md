# P02 · 03 · Changes — data-engineer

Status: READY
Author: data-engineer
Reads: 00_assignment.md, 02_plan.md, 03_changes_signal-processing.md, mas/RULES.md, mas/state/decisions.md (P02 rows), mas/01_DATA_SPEC.md §1, §5.1, mas/02_REQUIREMENTS.md §3, §4, mas/04_REFERENCE_RESULTS.md R-1, mas/05_PITFALLS.md PF-07, PF-09
Branch: phase/P02-legacy-windowing
Commit(s): 5d6767e (feat: script + Makefile target, P02.3), 7c49aad (test: smoke tests); this handoff in the docs commit that follows

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `scripts/preprocessing/run_preprocessing.py` | NEW | P02.3 script. It reads `<raw-dir>/<S>/<session>.ebr` (default `OO`), selects the config scalp channels by name and MARK, and takes fs from the header. It band-passes the continuous signal once with `apply_iir_bandpass` (config 1–60 Hz, order 4) and calls `process_condition_windows_with_baseline` with every threshold passed explicitly. It then runs `prepare_feature_matrix`, checks shapes, labels and order (failing loudly), prints per-subject counts and a cohort line, saves the three arrays, writes the S03 root copy from the same arrays and saves the figures | P02.3 | [1], [2], [3], [4], PF-07, PF-09, R3, R5, R9 |
| `Makefile` | MODIFIED | `preprocess` target (`$(PYTHON) -m scripts.preprocessing.run_preprocessing --all`) and a help line | P02.3 | [2] |
| `tests/test_p02_preprocessing_smoke.py` | NEW | 4 smoke tests on synthetic EBR files written to `tmp_path`. They cover `--all` (arrays, root copy equal to S03, figures, skip line, cohort line, one spike-rejected window), the default subject S03, R3 (saved windows equal slices of the continuous filtered recording, atol 1e-12, `vpp_min` 0.5 resolved) and `check_arrays` failures | P02.3 | [own], R3, PF-09 |

## Script interface

- Subject selection (mutually exclusive): `--subject S` (default `S03`), `--subjects S01 S04 …`, or `--all` (folders matching `^S\d+$`, numeric order) [3].
- Paths: `--config` (default `configs/pipeline_config.yaml`), `--raw-dir`, `--processed-dir` and `--figures-dir`. Their defaults are `<root>/` plus `paths.data_raw_dir`, `data_processed_dir` and `figures_dir`. `--session` defaults to `OO` [5]. `--no-figures` skips the figures.
- Config overrides (default `None`, meaning the config value): `--lowcut`, `--highcut`, `--order`, `--sub-window-sec`, `--vpp-max` (`vpp_thresh_uv`), `--std-min`, `--std-max`, `--stim-duration-sec`, `--cross-duration-sec` (`baseline.pre_stim_cross_sec`), `--cue-lookback-sec`.
- `--vpp-min` defaults to `LEGACY_VPP_MIN_UV = 0.5`. It is a module constant labelled `legacy` because config v1 has no such key, and it is always passed explicitly (PF-07).
- Outputs:
  - Arrays: `<processed>/<S>/{X_psd_features,X_time_windows,y_labels}.npy`. For S03 the same three arrays are also written to the `<processed>/` root from the same in-memory arrays. `save_arrays` refuses to write when the lengths differ (PF-09).
  - Figures: `<figures>/spectra/<S>/average_psd_by_condition.png` and `<figures>/spectra/<S>/stimulus_vs_baseline_psd.png`. For S03 there is also `<figures>/spectra/average_psd_by_condition.png` (decisions.md Q1).
- Console output, per subject:
  - the header fs, channel count and duration;
  - `format_quality_stats` (totals, per condition, every rejected sub-window with its channels, every skipped segment);
  - `summarize_window_quality` over the accepted windows (observed Vpp/std against the limits);
  - windows per condition;
  - `n` with the stimulus count;
  - the saved paths.
  It then prints a cohort line, `Cohort: k subjects processed, m skipped (…); N windows; gated …, accepted …, rejected …, skipped segments …`, and `Saved: <processed>`. The first lines state the data source (`legacy windows from OO.ebr`, R9), the filter and the gate.
- Skips: a missing recording, a parse error (strict parser), a missing channel or MARK, or zero accepted windows prints `[-] Skipping <S>: <reason>` and the run continues. A shape, label or order violation in `check_arrays` raises `RuntimeError`, which is a bug and is meant to stop the run. If S03 was requested but not processed, a `[!]` line says that the root arrays were not written. The exit code is 1 when no subject was processed, otherwise 0.

### For the tester (R3 known-answer)

Every step is importable from `scripts.preprocessing.run_preprocessing`:

- `load_recording(path, scalp, mark_channel) -> (x, mark, fs)`
- `resolve_params(load_config(DEFAULT_CONFIG), build_parser().parse_args([...]))`
- `preprocess_recording(x, mark, fs, params)`, which returns `x_filtered`, `records`, `X_psd`, `X_time`, `y`, `quality_stats` and `starts`
- `window_starts(records, conditions)`
- `check_arrays(...)`, `save_arrays(...)`, `condition_counts(...)`, `discover_subjects(...)`
- `main(argv)`

`starts[i]` is the absolute start sample of row i, so the R3 check is `X_time[i] == apply_iir_bandpass(x, fs, 1, 60, 4)[:, starts[i]:starts[i] + 256]`. `tests/test_p02_preprocessing_smoke.py::test_windows_are_slices_of_the_continuous_filtered_signal` is the builder's version, and `_write_ebr` / `_signal` in that file write a synthetic EBR tree.

## Legacy behaviour implemented

None from the era matrix. The constant `LEGACY_VPP_MIN_UV = 0.5` (CLI `--vpp-min`) is labelled `legacy` in the code: it is the P02 gate's lower Vpp limit, and P07 can reproduce PF-07 with `--vpp-min 5.0`. The 7-channel montage comes from config v1 (PO7 excluded, PF-05).

## Differences from the cited examples

The CLI style and root discovery copy `scripts/exploration/inventory_raw.py` (`_find_root`, `discover_subjects`, skip lines) [6].

## Deviations from the plan

1. Additional figure: `stimulus_vs_baseline_psd.png` per subject, made with the P02.4 function, to help the reviewer check acceptance criterion 3. The roadmap figure and the Q1 paths are unchanged [own].
2. Additional CLI flags: `--config`, `--processed-dir`, `--figures-dir`, `--session`, `--no-figures`. They are needed for synthetic smoke runs without touching `data/`, and every default reproduces the reference run [3].
3. `summarize_window_quality` sees only the accepted windows, because the library returns no ungated windows. It therefore always reports 0 rejected. The rejection counts that matter are in the `format_quality_stats` block printed just above it. Its label says `accepted windows` [own].

## How to run / reproduce

```bash
.venv/bin/python -m scripts.preprocessing.run_preprocessing --all      # runner; same as: make preprocess
.venv/bin/python -m scripts.preprocessing.run_preprocessing            # S03 only (default)
.venv/bin/python -m pytest tests/test_p02_preprocessing_smoke.py -q
```

## How I verified

- `.venv/bin/python -m pytest tests/ -o addopts=""` gave `260 passed in 8.20s`, and `tests/test_p02_preprocessing_smoke.py` alone gave `4 passed in 2.95s`.
- Synthetic CLI smoke run in `mas/state/scratch/P02_de/`. The generator `mas/state/scratch/P02_de_make_tree.py` writes S03 and S04 as 40-trial §3-timing recordings at fs 256 with 11 channels, plus an S05 folder with no recording. S04 has a 400 µV spike in trial 7. The command was `.venv/bin/python -m scripts.preprocessing.run_preprocessing --all --raw-dir … --processed-dir … --figures-dir …`, with exit 0 in `real 0m3.041s`. Output:
  - `S03: n = 320 windows (stimulus 200); accepted 320, rejected 0, skipped segments 0; X_time (320, 7, 256), X_psd (320, 217)`
  - `S04: n = 319 windows (stimulus 199); accepted 319, rejected 1, …`, with `103: accepted 39/40, rejected 1 (… vpp_high 1 …)`
  - `[-] Skipping S05: recording not found: …/S05/OO.ebr`
  - `Cohort: 2 subjects processed, 1 skipped (S05); 639 windows; gated 640, accepted 639, rejected 1, skipped segments 0`
  - The S03 root copy and all 5 figures were written. I looked at the S04 PSD figure: the title, the legend counts and the 1–60 Hz range are correct.
- The file form also works: `.venv/bin/python scripts/preprocessing/run_preprocessing.py --raw-dir … --no-figures` processes S03 by default (`320 windows`).
- Nothing ran on real data, and `data/raw` was never read or listed.

## Left to do / known limitations

- The script does not compare against the R-1 counts. The verifier and reviewer do that (exact tolerance), using the per-subject `n`, the stimulus counts and the rejected/skipped lists printed per subject.
- One `.ebr` is loaded at a time. Memory stays at one recording plus its filtered copy.

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

1. REQUEST — `mas/03_ROADMAP.md` P02 task 3 (as copied in `00_assignment.md`): "broadband filter the **continuous** signal (config 1–60 Hz, order 4) … vpp_min 0.5 … Also write the S03 arrays to `data/processed/` root".
2. REQUEST — `02_plan.md` work split row data-engineer and the "Run commands" section; `mas/state/decisions.md` 2026-10-24 P02 rows (figures per subject, verbatim path holds S03; gate on filtered windows; fs from the header).
3. RULE — `mas/02_REQUIREMENTS.md` §3 (scripts read the config, CLI overrides) and §4 (root discovery, argparse, `--subjects`, skip line, cohort summary line, Agg plots).
4. RULE — `mas/01_DATA_SPEC.md` §5.1 (segments, order, shapes, 217 features); `mas/05_PITFALLS.md` PF-07, PF-09; `mas/RULES.md` R3, R5, R9.
5. RULE — `mas/01_DATA_SPEC.md` §1 (subject regex, default session `OO`, ignore non-`.ebr` files).
6. HANDOFF — `mas/state/phases/P02-legacy-windowing/03_changes_signal-processing.md` (API, `start` key, the `vpp_min` and `cross_duration_sec` request); `scripts/exploration/inventory_raw.py` @ 7cc9b73 (CLI style).

## Questions

ACK 02_plan.md data-engineer 2026-10-24

Answer to signal-processing (`vpp_min`): done. It is the CLI `--vpp-min` with default `LEGACY_VPP_MIN_UV = 0.5`, labelled legacy, and it is passed explicitly as `vpp_min=params["vpp_min"]`. `cross_duration_sec` comes from `preprocessing.baseline.pre_stim_cross_sec` (CLI `--cross-duration-sec`). I appended the answer to their file.
