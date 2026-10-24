# P00 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §1–§4, mas/02_REQUIREMENTS.md §1, §2, §4, §7
Approved by Sebastian: [x]   Date:2026-10-24        (required only if PLAN_APPROVAL: required)

## Goal

Create the empty repository skeleton and a Python environment, and reproduce the
23-row recording inventory of `01_DATA_SPEC.md` §4 from the files with a script
that fails loudly on any deviation.

## Data source

Raw recordings `data/raw/S*/*.ebr` (all sessions, all subjects found by `^S\d+$`;
`config.yaml` lists S01–S05). No windows, no filtering, no quality decision.
fs read from each header (it is what is being checked).

## Scope

**In:** skeleton of `02_REQUIREMENTS.md` §2 (directories + `__init__.py` only),
`requirements.txt`, `environment.yml`, `Makefile`, `pytest.ini`, stub
`CHANGELOG.md` / `RESEARCH_LOG.md`, `.venv`, `scripts/exploration/inventory_raw.py`,
gitignore check.

**Out:** `src/io/ebr_parser.py` and `configs/pipeline_config.yaml` (P01); any
filtering or windowing (P02). `mas/state/phase_status.yaml` and `decisions.md`
already exist (orchestrator, `mas_status.py init`), so P00.1 does not recreate them.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| data-engineer | NEW `src/**/__init__.py`, `scripts/**/__init__.py`, `tests/__init__.py` (or none, see below) | empty packages for every directory of §2 that holds Python; `configs/`, `notebooks/`, `docs/` are not created until a phase needs them | P00.1 | [1] §2 |
| data-engineer | NEW `requirements.txt`, `environment.yml` | versions of `02_REQUIREMENTS.md` §1 (conda env targets 3.11) | P00.1 | [1] §1 |
| data-engineer | NEW `.venv/` (ignored) | `python3 -m venv .venv` + `.venv/bin/pip install -r requirements.txt` (see Q1) | P00.1 | [1] §1; the local test hook expects `.venv/bin/python` |
| data-engineer | NEW `Makefile` | `PYTHON ?= .venv/bin/python`; targets `venv`, `test`, `inventory` | P00.1 | [2] P00.1 |
| data-engineer | NEW `pytest.ini` | `testpaths = tests`, `-q` | P00.1 | [2] |
| data-engineer | NEW `CHANGELOG.md`, `RESEARCH_LOG.md` | headings only; the scribe fills P00 at step 11 | P00.1 | [2] |
| data-engineer | NEW `scripts/exploration/inventory_raw.py` | see design below | P00.2 | [3] §2–§4 |
| data-engineer | — | `git check-ignore -v data/raw/S01/OO.ebr` (and a `.jpg`, `.mp4`, a `.npy` under `data/processed/`) recorded in the handoff | P00.3 | [2] |

### Inventory script design

- `argparse`, module docstring as description; `--raw-dir` (default
  `<root>/data/raw`), `--out` (default `<root>/reports/raw_inventory.csv`),
  `--subjects` (default: discovered). Root: upward search for
  `configs/pipeline_config.yaml`, falling back to `Path(__file__).parents[2]`
  until P01 creates the config. Runs as file and as module (§4 of [1]).
- Self-contained minimal `.ebr` reader per [3] §2 (header lines until
  `end_header`, dtype table, `(nt, nc, nb, ns)` C-order) using `np.memmap`, so
  only MARK, the first TIMESTAMP sample and the EEG channels are touched. P01
  replaces it with `src/io/ebr_parser.py`; P00 does not create that module.
- Subjects by `^S\d+$`; only `*.ebr` files; everything else ignored. A folder
  with no `.ebr` → `[-] Skipping <S>: no .ebr files`.
- Onsets: `(mark == code) & (diff(mark, prepend=0) != 0)` [3] §3.
- One row per file. Columns: `subject, file, samples, duration_s, stim_events,
  session_start_utc, p99_abs_eeg_uv` (the §4 columns, in that order) +
  `fs, n_channels, channels` (`;`-joined) + `event_counts` (`code:n;…`,
  sorted) + `kind` + `deviations` (empty when clean).
  - `duration_s = samples / fs`, printed to 0.1 s.
  - `session_start_utc` = first TIMESTAMP sample (ms since epoch) as
    `YYYY-MM-DD HH:MM` UTC.
  - `p99_abs_eeg_uv` = 99th percentile of `|x|` pooled over the 8 EEG channels
    (idx 0–7) of the whole file. The pooling is not stated in [3]; this is the
    first attempt (see risks).
  - `stim_events` = onsets of 101–105 for calibration/joined runs, of
    1001–1005 for online runs.
- `kind` from the file stem: `OO, mOO, C, mC` → `calibration`; `online_*` →
  `online`; `cb_mas_mcb` → `joined`; otherwise `unknown`.
- Checks (any failure → listed in `deviations`, script exits 1 after writing
  the CSV and printing every deviation):
  - all files: magic, `fs == 256`, channels == the 11 names of [3] §2 in order,
    `nt == nb == 1`;
  - calibration: onsets `201, 202, 203, 200` = 40 each and `101…105` = 8 each,
    no other nonzero code;
  - online: only codes 1001–1005;
  - joined: stim events = 80 (from [3] §4); per-code counts reported, not checked
    (not specified);
  - unknown kind: warning only, not a deviation (the cohort will grow).
- Console ends with a summary line (`23 files, 5 subjects, 0 deviations`) and the
  CSV path.

## Legacy behaviour in this phase

None. The era matrix has no row that applies to bootstrap.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| Data privacy (AGENTS.md) | an agent lists or prints recordings; data ends up staged | only the runner executes the script; guard hook; P00.3 check; verifier checks `git status` |
| R9 | inventory hides one subject or session | one row per file, subject column; verifier compares all 23 rows |
| R10 | expected values invented | every expected value cites [3] §2–§4 |
| R11 | `REFERENCE_POLICY: after-attempt` | the original repo may be opened only if `p99_abs_eeg_uv` (or any column) disagrees after one investigation round; log it |
| fail-loudly | a deviation only printed, exit 0 | test asserts exit code 1 |
| Event counting | counting pulse *samples* instead of onsets inflates counts on plateaus | onset rule + plateau test |
| Ambiguity | pooling of the 99th percentile not documented | not part of the verbatim acceptance (samples, duration, stim events); compared to ±0.1 µV as information; a mismatch is investigated and reported, not tuned |

## Tests required

Synthetic `.ebr` files written in `tmp_path` by the tests (no real data). The
script needs `--raw-dir`/`--out`, and its functions must be importable.

| Test | Simulated input | Expected result | Tolerance | Source of the answer |
|---|---|---|---|---|
| clean calibration run | 1 subject `S01/OO.ebr`, fs 256, 11 channels, 40 trials (8 × 5 targets) of single-sample pulses with the §3 timing, ns = 154,904 | row: samples 154904, duration 605.1, stim_events 40, counts 201/202/203/200 = 40, 101–105 = 8; exit 0 | exact | [3] §3, §4 |
| plateau pulses | same, each pulse 3 samples long | identical counts (one onset per event) | exact | [3] §3, [1] §7 "event onsets" |
| wrong fs | header `sampling_rate 250` | `deviations` names fs; exit 1; CSV still written | exact | [2] P00.2 |
| wrong channel list | channel 1 renamed / 10 channels | deviation; exit 1 | exact | [2] P00.2 |
| missing trial | 7 pulses of code 103 | deviation; exit 1 | exact | [2] P00.2 |
| online run | `online_OO.ebr` with 7 codes in 1001–1005 | kind online, stim_events 7, exit 0 | exact | [3] §3 |
| discovery | folders `S01`, `S1x`, `notes`; `S01/photo.jpg` | only `S01`, only `.ebr` rows | exact | [3] §1 |
| session start | TIMESTAMP[0] = 1635456840000 ms | `2021-10-28 21:34` | exact | [3] §4 (S01 mC) |
| p99 | EEG = known array (e.g. uniform ramp) | `np.percentile(abs, 99)` of the planted values | 1e-9 | [own] |
| dtype | header `data_type float` (float32 block) | parsed, values equal; `data_type bogus` raises `ValueError` | exact | [3] §2 |

The historical-bug requirement ("at least one test fails on PF-xx") has no PF
entry in P00; the plateau test is the guard that fails on the naive
`(mark == code).sum()` counter.

## Run commands (for the runner)

```bash
python scripts/exploration/inventory_raw.py      # with .venv active, i.e. .venv/bin/python …
```

Expected runtime and device: < 1 min, CPU (23 files ≈ 310 MB memory-mapped).
Over `LOCAL_RUN_BUDGET_MIN` (30)? no.
Outputs expected: `reports/raw_inventory.csv`, console log
`reports/logs/P00/inventory_raw_<timestamp>.log` (with command and `git rev-parse HEAD`).

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference (R-x, tolerance) |
|---|---|---|
| inventory matches `01_DATA_SPEC.md` §4 row for row (samples, duration, stim events) | parse the §4 markdown table and the CSV with a shown Python command; join on (subject, file); 23 rows on both sides; samples and stim events exact, duration to 0.1 s; session start and p99 reported as extra columns (minute; ±0.1 µV) | [3] §4; tolerance "exact" for counts |
| `git status` shows no data files | `git status --porcelain --ignored` in the clean checkout; no `.ebr/.jpg/.mp4/.npy` tracked or staged; `git check-ignore` output of P00.3 | [2] P00.3 |
| `pytest -q` runs (zero tests is OK) | `.venv/bin/python -m pytest -q` in the clean checkout | [2] |
| exit code | script exits 0 on the real data and 1 on a synthetic deviation | [2] P00.2 |

## Sources

1. `mas/02_REQUIREMENTS.md` §1, §2, §4, §7 (opened in this run).
2. `mas/03_ROADMAP.md` P00 (opened in this run).
3. `mas/01_DATA_SPEC.md` §1–§4 (opened in this run).

## Questions

Q1 (environment). There is no `python` on PATH and system Python 3.12.3 has no
numpy. Plan: `.venv` with the full `requirements.txt` (PyTorch from PyPI is the
CUDA build, a few GB; 67 GB free; GPU RTX 3050 present). Alternative: install only
numpy/pandas/pytest now and the rest when P04 needs it. Default: full install.
The runner's `python` = `.venv/bin/python`; recorded in `decisions.md`.
Yeah, install the full process, from venv to all.

Q2 (uncommitted spec). `main` has untracked `AGENTS.md`, `mas/`, `.gitignore` and a
modified `README.md`; agents may not commit on `main`. Default: the data-engineer's
first commit on `phase/P00-bootstrap` is `chore: add specification and MAS
tooling` (those files, excluding `mas/state/scratch/`). Alternative: Sebastian
commits them on `main` first and the branch starts from that commit.
Do whatever you think is better. I think is great start the branch from that commit

Q3 (untracked folder). The repo root holds a folder `SSVEPs_OO_mOO/` that does not
appear in `git status` (ignored or empty; not opened by any agent). The
inventory reads only `data/raw/`. Should it be named in `.gitignore` explicitly,
or moved out of the repo?
Yeah it should be named on .gitignore
