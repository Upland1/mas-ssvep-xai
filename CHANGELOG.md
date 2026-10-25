# Changelog

All notable changes, one section per phase (filled by the scribe).

## P00 — Bootstrap and data intake

2026-10-24, branch `phase/P00-bootstrap`. Report: `mas/state/reports/P00.md`.

Added
- Specification and MAS tooling (`AGENTS.md`, `mas/`), `README.md`.
- Repository skeleton: `src/**/__init__.py`, `scripts/**/__init__.py`, `tests/__init__.py`.
- `requirements.txt`, `environment.yml`, `Makefile` (targets `help`, `venv`, `test`, `inventory`), `pytest.ini`.
- `scripts/exploration/inventory_raw.py`: header and MARK inventory of the raw recordings, writes `reports/raw_inventory.csv`, exit 1 on any deviation.
- `tests/test_p00_inventory_smoke.py` (2 tests) and `tests/test_p00_inventory_known_answer.py` (61 tests); suite `63 passed`.

Changed
- `.gitignore`: `SSVEPs_OO_mOO/` named explicitly; `/outputs/`, `/reports/`, `/baselines/` anchored at the repository root so `mas/state/reports/` is tracked.
- `scripts/exploration/inventory_raw.py`: subject folders matched with `fullmatch`.

Result and scope
- Inventory run: exit 0, `10 files, 5 subjects, 0 deviations`; all 10 delivered rows match `mas/01_DATA_SPEC.md` §4.
- Only 10 of the 23 §4 rows were delivered (`OO`, `mOO` of S01–S05). Absent: S01 `C`, `mC`; S02 `C`, `mC`, `online_C`; S03 `C`, `mC`, `cb_mas_mcb`; S04 `C`, `mC`; S05 `C`, `mC`, `online_OO`. Deviation recorded in `mas/state/decisions.md` and blocker B005, signed by the scientific reviewer.

## P01 — EBR parser and configuration v1

2026-10-24, branch `phase/P01-ebr-parser`. Report: `mas/state/reports/P01.md`.

Added
- `src/io/ebr_parser.py`: `load_ebr_file(path, strict=True)`, `resolve_recording_path`, `select_scalp_channels`, `get_mark_channel_index`, `extract_scalp_signal`.
- `configs/pipeline_config.yaml` v1 (PO7 hard-excluded, labelled legacy).
- `src/preprocessing/signal/filters.py`: `apply_iir_bandpass(data, fs, lowcut=1.0, highcut=60.0, order=4)`.
- `tests/test_p01_*.py` (smoke, parser, config, filters, strict); suite `248 passed`.

Changed
- `scripts/exploration/inventory_raw.py`: reads through the parser; new `--strict` flag (default off); `--raw-dir` default from the config.

Result and scope
- Default and `--strict` inventories: exit 0, `10 files, 5 subjects, 0 deviations`, both byte-identical to the P00 CSV (sha256 `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14`).
- Applies to the 10 of 23 §4 rows delivered (blocker B005). Seven accepted deviations are in `mas/state/decisions.md`.

## P02 — Legacy preprocessing and windowing

2026-10-24, branch `phase/P02-legacy-windowing`. Report: `mas/state/reports/P02.md`.

Added
- `src/preprocessing/signal/quality_check.py`: `validate_eeg_windows`, `filter_dataset`, `summarize_window_quality`, `window_quality_flags`, `segment_and_validate_eeg`, `quality_stats` helpers.
- `src/features/ssvep/psd_extraction.py`: `extract_clean_subwindows_psd`, `process_condition_windows_with_baseline`, `prepare_feature_matrix`.
- `src/visualization/signal_plots.py`: `plot_eeg_window`, `plot_average_psd_by_condition`, `plot_stimulus_vs_baseline_psd`.
- `scripts/preprocessing/run_preprocessing.py` (`--subject`, `--all`, `--vpp-min`, `--raw-dir`, `--processed-dir`, `--figures-dir`) and `make preprocess`.
- `tests/test_p02_signal_smoke.py`, `tests/test_p02_preprocessing_smoke.py`, `tests/test_p02_windowing_known_answer.py`; suite `283 passed`.

Changed
- `Makefile`: target `preprocess`.
- `mas/state/team.yaml`: P02 legacy flags set to `[]` (header fs 256 Hz is used for windows and PSD).

Result and scope
- Run: exit 0, 5 s; `Cohort: 5 subjects processed, 0 skipped (none); 1592 windows; gated 1600, accepted 1592, rejected 8, skipped segments 0`. Window counts equal R-1 exactly (320 / 318 / 317 / 317 / 320; stimulus 200 / 199 / 200 / 198 / 200).
- Figure criterion: S04 and S05 5/5, S03 4/5 (8.57 Hz partial).
- On real data 178 of 199 legacy 202 windows are bit-identical to a 201 window and 21 are shifted by 8 samples; 201 and 202 are never to be used together.

## P03 — Exploration and signal verification

2026-10-24, branch `phase/P03-exploration`. Report: `mas/state/reports/P03.md`.

Added
- `scripts/exploration/diagnose_occipital_spectra.py` (`--subject`, `--subjects`, `--all`, `--fs`, `--out-suffix`, `--processed-dir`, `--figures-dir`, `--config`, `--no-figures`): occipital `O1, Oz, O2` (by name) spectra per class, response-bin power and specificity ratio.
- `scripts/exploration/visualize_data.py`: legacy quality mask with explicit thresholds, per-class PSD plots, check of the recomputed PSD against the saved one; marked extension points for FBCCA/FBCSP (P05).
- `src/features/ssvep/spectral_power.py` (`response_bin`, `spectrum_peaks`, `fft_power`, `psd_features`, `select_channels_by_name`); `LEGACY_FS_HZ = 250`.
- `tests/test_p03_exploration_smoke.py` (10) and `tests/test_p03_exploration_known_answer.py` (18); suite `311 passed`.

Changed
- `src/visualization/signal_plots.py`: + `plot_class_spectra_panels`, `plot_psd_by_class_per_channel`.
- `Makefile`: target `explore`.

Result and scope
- Four runs, 3 to 5 s each; the verifier re-ran them with exit 0. Mask `rejected 0` (kept 1592, consistency check); `max |computed - saved| = 0` at fs 256; legacy fs 250 relabels the axis only (25 of 25 rows).
- Clear fundamentals: S03 5/5, S04 5/5, S05 5/5 (104 and 105 via the second harmonic); S01 only a weak 10.91 Hz response; S02 none.
- The pre-run audit Round 1 failed on the nearest-labelled target bin at the legacy axis (wrong for 24, 2·15, 2·8.57 Hz); fixed with response bins and a specificity ratio.
