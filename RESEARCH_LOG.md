# Research log

The research history of the rebuild, phase by phase: each stage, its numbers,
each discovered problem, each fix and its before/after (filled by the scribe).

## P00 — Bootstrap and data intake

Full report: `mas/state/reports/P00.md`. Date of all steps: 2026-10-24.

**Aim.** Set up the repository and make first contact with the recordings: reproduce the measured inventory of `mas/01_DATA_SPEC.md` §4 from the files with a script that fails loudly on any deviation.

**Scope.** P00 reproduced **10 of the 23 §4 rows**, not the full §4 inventory. The delivered raw data are `OO` and `mOO` of S01–S05. The 13 absent rows are S01 `C` and `mC`; S02 `C`, `mC` and `online_C`; S03 `C`, `mC` and `cb_mas_mcb`; S04 `C` and `mC`; S05 `C`, `mC` and `online_OO` (blocker `mas/state/blockers/B005-inventory-10-of-23-files.md`; `mas/state/phases/P00-bootstrap/06_verify.md`).

**Build.** The environment is a `.venv` (Python 3.12.3) with the full `requirements.txt`. The skeleton of `02_REQUIREMENTS.md` §2, `Makefile`, `pytest.ini` and the two logs were created, and `scripts/exploration/inventory_raw.py` reads the `.ebr` header and the MARK, TIMESTAMP and EEG rows through a memory map. Beyond the specified checks (fs, channel list, 40 trials of 8 per target) it fails on unreadable files, channel-count mismatch, trailing bytes and non-integer MARK values (`03_changes_data-engineer.md`).

**Tests and first review.** The synthetic-tester wrote 58 known-answer tests on synthetic `.ebr` files (suite `60 passed in 2.42s`, `04_tests.md`); a naive onset counter gives 120 stim events instead of 40 on plateau pulses, so the plateau test guards the onset rule. The pre-run audit Round 1 returned FAIL: the unanchored `reports/` pattern in `.gitignore` also ignored `mas/state/reports/`, where phase reports are committed (`07_review.md`). Fix: `/outputs/`, `/reports/`, `/baselines/` anchored at the root (`9d5c5a9`); the subject regex now uses `fullmatch`, with three further tests (suite `63 passed in 3.67s`). Round 2 returned PASS.

**Run.** `.venv/bin/python scripts/exploration/inventory_raw.py` at `042e1b2f5b727e310777b41f600e84abf940b97a`, exit 0, `10 files, 5 subjects, 0 deviations` (`reports/logs/P00/inventory_raw_20261024_141334.log`, `reports/raw_inventory.csv`). All 10 delivered rows match §4: samples, stim events and session start exactly, duration to 0.1 s, p99 within 0.043 µV (`07_review.md`). Per row, all with 40 stim events, fs 256.0 and 11 channels (`reports/raw_inventory.csv`):

| Subject | File | Samples | p99 abs EEG (µV) |
|---|---|---|---|
| S01 | OO | 154904 | 785.129522094725 |
| S01 | mOO | 154912 | 187.5906661987305 |
| S02 | OO | 154912 | 40.06002101898197 |
| S02 | mOO | 154912 | 37.48278903961185 |
| S03 | OO | 154896 | 331.4067117309576 |
| S03 | mOO | 154896 | 1013.7993548584035 |
| S04 | OO | 154896 | 481.5410757446289 |
| S04 | mOO | 154912 | 24.943459510803237 |
| S05 | OO | 154912 | 24.585167598724375 |
| S05 | mOO | 154904 | 23.802621860504146 |

**Deviation.** Because 13 of the 23 §4 rows were not delivered, Sebastian chose option B of B005 (accept the 10-file inventory). The scientific reviewer signed the deviation on the conditions that this log and the phase report state "10 of 23 §4 rows" and name the absent ones, and that the inventory be re-run and checked against §4 before any phase uses the `C`, `mC`, online or joined recordings if they arrive (`07_review.md`, `mas/state/decisions.md`). The verifier passed the phase (`06_verify.md`) and the reviewer approved the results (`07_review.md`).

**Findings for later phases.** The p99 pooled over the 8 EEG channels reproduces §4 on 10/10 files; session start is truncated to the minute (rounding is not excluded by the data). The raw p99 ranges from 23.8 to 1013.8 µV across the delivered files, in line with §4's remark that quality decisions must use filtered signals. No reference consultation was made. Next: P01.

## P01 — EBR parser and configuration v1

Full report: `mas/state/reports/P01.md`. Date of all steps: 2026-10-24.

**Aim.** Replace the P00 private reader with a parser written from `mas/01_DATA_SPEC.md` §2, add configuration v1 (PO7 hard-excluded, legacy, PF-05) and the legacy zero-phase Butterworth band-pass, and show that the parser reproduces the P00 inventory.

**Scope.** As in P00, acceptance was applied to the **10 of 23 §4 rows** delivered (`OO`, `mOO` of S01–S05; blocker B005). The 13 absent rows are unchanged.

**Build.** `src/io/ebr_parser.py` (`load_ebr_file(path, strict=True)` plus four name-based helpers), `configs/pipeline_config.yaml` v1, `src/preprocessing/signal/filters.py` (`apply_iir_bandpass`, `fs` required), and the inventory script switched to the parser (`03_changes_data-engineer.md`).

**Tests and review.** Round 1 suite `198 passed in 3.94s` (`04_tests.md`). The pre-run audit Round 1 returned FAIL: the planned run read with `strict=False` only, so the default mode that P02 will call was never tried on real headers, and a committed handoff named a local tool file (`07_review.md`). Fixes: an inventory `--strict` flag, exact `data_type` matching, a strict repeated-line check, a plan amendment with a strict run, and a reworded assignment. Final suite `248 passed in 4.92s` (`04_tests.md` Round 2); Round 2 returned PASS.

**Run.** At `477550967a7d04aab2ceb217d47c59735c992dd0`, default and `--strict` inventories both printed `10 files, 5 subjects, 0 deviations` with exit 0, `cmp` against `reports/raw_inventory.csv` was silent for both, and the sha256 was `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14` before and after (`mas/state/phases/P01-ebr-parser/05_run.md`; `reports/logs/P01/inventory_raw_default_20261024T162513.log`, `reports/logs/P01/inventory_raw_strict_20261024T162517.log`). The verifier reproduced both from a clean checkout (`248 passed in 7.26s`, `06_verify.md`).

**Deviations.** Seven accepted deviations (strict default and its extra checks, extra public parser names, stricter helper errors, exact `data_type`, header count defaults, whole-file reads with `--strict` flag, plan amendment); see `mas/state/decisions.md` and the report, section 9.

**Findings for later phases.** All 10 delivered headers pass the strict checks, so P02 can call `load_ebr_file(path)` with its default. Strict mode also rejects a repeated unknown header key; if a future file trips it, the stop/blocker rule applies. Config v1 keeps the 7-channel montage until P07. No reference consultation was made (the two access-log lines are logged privacy greps, not reads). Next: P02.
