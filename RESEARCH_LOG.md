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

## P02 — Legacy preprocessing and windowing

Full report: `mas/state/reports/P02.md`. Date of all steps: 2026-10-24.

**Aim.** Rebuild the first data-bearing step of the original project: broadband-filter each continuous `OO` recording (1–60 Hz, order 4), cut condition windows (201, 202, 101–105), apply the legacy Vpp/std gate, and save `X_time_windows (n, 7, 256)`, `X_psd_features (n, 217)` and `y_labels` per subject (roadmap P02; `00_assignment.md`).

**Build.** `src/preprocessing/signal/quality_check.py`, `src/features/ssvep/psd_extraction.py`, `src/visualization/signal_plots.py`, `scripts/preprocessing/run_preprocessing.py` and a `make preprocess` target (`03_changes_signal-processing.md`, `03_changes_data-engineer.md`). The gate passes `vpp_min=0.5` explicitly (PF-07). Windows and periodogram use the header fs 256 Hz: 217 = 7 × 31 bins needs it, so PF-04's `fs = 250` is not reproduced here and enters with the P04/P05 extractors (decisions.md).

**Tests and review.** Final suite `283 passed in 12.37s` (`04_tests.md`); 23 known-answer tests, with variants that fail on PF-07, PF-13, PF-09, PF-04, R3 and R6. Pre-run audit PASS, no required fixes (`07_review.md`).

**Run.** `python -m scripts.preprocessing.run_preprocessing --all` at `adbc5a01f098daf7eefb214174777a0f27c90797`: exit 0, 5 s. Log line: `Cohort: 5 subjects processed, 0 skipped (none); 1592 windows; gated 1600, accepted 1592, rejected 8, skipped segments 0` (`reports/logs/P02/run_preprocessing_20261024_171759.log`; `05_run.md`). The verifier re-ran from a clean checkout (`283 passed in 11.00s`), all 18 arrays bit-identical (`06_verify.md`).

**Result.** R-1 reproduced exactly: n 320 / 318 / 317 / 317 / 320 and stimulus windows 200 / 199 / 200 / 198 / 200 for S01–S05 (data source: legacy, `data/processed/<S>/`, session `OO`). All 8 losses are `vpp_high` rejections (O2 in S02 and S04, PO8 in S03); none is `vpp_low`. Figure criterion: S04 and S05 5/5; S03 4/5, the 8.57 Hz target is partial (plateau at bins 8–9 in the 7-channel mean, local maximum over PO8, O1, Oz, O2 with ratio 1.918); the reviewer approved with the partial recorded (`07_review.md`).

**Finding.** 178 of the 199 saved 202 windows are bit-identical to the second 201 sub-window of their trial and the other 21 are shifted by 8 samples (PF-13 on real data). 201 and 202 must never be used together as independent samples or in different CV groups.

**Deviations and legacy.** PO7 excluded (config v1) and the per-script gate (R5 LEGACY by design) are the legacy behaviours; builder deviations accepted (extra kwargs and record keys, extra figure and CLI flags). `team.yaml` P02 flags corrected to `[]`.

**Findings for later phases.** P03: S01 101 (24 Hz) shows a 10 Hz peak and S01/S02 show no clear SSVEP peaks. P07: `summarize_window_quality` must see ungated windows, stale outputs on skipped subjects need handling, PF-07 is reproduced with `--vpp-min 5.0`. P16: check S03 first-trial PO8 rejections for a filter start-up transient. No reference consultation was made (the two access-log lines are privacy greps from earlier phases). Next: P03.
