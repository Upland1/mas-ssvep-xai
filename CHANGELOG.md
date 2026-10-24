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
