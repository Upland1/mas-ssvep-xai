# P00 · 03 · Changes — data-engineer

Status: READY
Author: data-engineer
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/01_DATA_SPEC.md §1–§4, mas/02_REQUIREMENTS.md §1, §2, §4, §7, mas/state/decisions.md (P00 rows)
Branch: phase/P00-bootstrap (from main @ d9da2ff)
Commit(s): ed92001, 1cc8359, 127ba13, 5671854, ebaf5ec, b7cd495, 40a0d68, 5e4c162 (this file in the next commit)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `AGENTS.md`, `mas/` (minus `mas/state/scratch/` and `mas/state/phases/P00-bootstrap/02_plan.md`, see Deviations 1), `.gitignore`, `README.md` | NEW / MODIFIED (README) | first commit `chore: add specification and MAS tooling` (ed92001) | — | [5] Q2 |
| `.gitignore` | MODIFIED | `SSVEPs_OO_mOO/` named explicitly (1cc8359), comment reworded so it claims nothing about the folder's contents (127ba13) | — | [5] Q3 |
| `src/**/__init__.py` (15), `scripts/**/__init__.py` (15), `tests/__init__.py` | NEW | empty packages for every directory of §2 that holds Python; `configs/`, `notebooks/`, `docs/` not created | P00.1 | [1] §2, [4] |
| `requirements.txt` | NEW | §1 core versions; `mne`, `mne-connectivity` unpinned (§1 gives no minimum); optional `shap>=0.45`, `jupyter>=1.0`, `pytest`; Colab warning from §1 in the header | P00.1 | [1] §1 |
| `environment.yml` | NEW | conda-forge, `python=3.11`, pip `-r requirements.txt` | P00.1 | [1] §1 |
| `Makefile` | NEW | `PYTHON ?= .venv/bin/python`; targets `help` (default), `venv`, `test`, `inventory` | P00.1 | [4] |
| `pytest.ini` | NEW | `testpaths = tests`, `addopts = -q` | P00.1 | [4] |
| `CHANGELOG.md`, `RESEARCH_LOG.md` | NEW | title, one-line purpose, empty `## P00` heading for the scribe | P00.1 | [4] |
| `.venv/` (ignored) | NEW | `python3 -m venv .venv` + `.venv/bin/pip install -r requirements.txt` (exit 0) | P00.1 | [5] Q1, [6] |
| `scripts/exploration/inventory_raw.py` | NEW | header + memory-mapped MARK/TIMESTAMP/EEG inventory, checks, CSV, exit 1 on any deviation | P00.2 | [3] §1–§4, [4] |
| `tests/test_p00_inventory_smoke.py` | NEW | 2 builder smoke tests (clean calibration run → exit 0 and the §4 values; one missing 103 pulse → exit 1). The known-answer suite is the synthetic-tester's | P00.2 | [3] §3–§4 |

### `inventory_raw.py` interface (for the synthetic-tester)

CLI: `--raw-dir` (default `<root>/data/raw`), `--out` (default `<root>/reports/raw_inventory.csv`), `--subjects S01 S02 …` (default: discovered by `^S\d+$`). Runs as `python scripts/exploration/inventory_raw.py` and as `python -m scripts.exploration.inventory_raw`. Root = upward search for `configs/pipeline_config.yaml`, fallback `Path(__file__).parents[2]` [4].

Importable functions (module `scripts.exploration.inventory_raw`):

| Function | Returns |
|---|---|
| `main(argv=None) -> int` | 0 clean, 1 on any deviation, on a missing raw folder, or when no `.ebr` file is found; CSV is written before returning 1 when rows exist |
| `parse_ebr_header(path) -> dict` | spec keys of [3] §2 plus `magic`, `data_offset`; `ValueError` without `end_header` or a required key (`data_type`, `sampling_rate`, `samples`, `channels`) |
| `ebr_dtype(data_type) -> np.dtype` | table of [3] §2, little-endian; `ValueError` for anything else (e.g. `bogus`) |
| `open_ebr_data(path, header) -> np.memmap` | `(nt, nc, nb, ns)` C order; `ValueError` if the file is shorter than the declared block |
| `event_onset_counts(mark) -> dict[int, int]` | onsets per nonzero code, rule of [3] §3 applied to all codes at once |
| `classify_kind(stem) -> str` | `calibration` (OO, mOO, C, mC), `online` (`online_*`), `joined` (`cb_mas_mcb`), `unknown` |
| `stim_event_count(counts, kind)`, `protocol_deviations(counts, kind)`, `session_start_utc(ms)`, `format_counts(counts)` | helpers used by `inventory_file` |
| `inventory_file(path, subject) -> dict` | one row with keys `CSV_COLUMNS` |
| `discover_subjects(raw_dir)`, `run_inventory(raw_dir, subjects=None)`, `write_csv(rows, out)` | discovery, all rows, CSV |

CSV columns, in order: `subject, file, samples, duration_s, stim_events, session_start_utc, p99_abs_eeg_uv, fs, n_channels, channels, event_counts, kind, deviations`. `file` is the stem (`OO`, `online_C`) as in [3] §4. `duration_s = round(samples / fs, 1)` (the §4 precision; `samples` keeps the exact value). `p99_abs_eeg_uv` = `np.percentile(|x|, 99)` pooled over the EEG channels present among the 8 names (full precision in the CSV, 0.1 on the console). `channels` and `event_counts` are `;`-joined; `deviations` items are joined with ` | `.

## Legacy behaviour implemented

None. The era matrix has no row for P00 [2].

## Differences from the cited examples

No external code example was used. The EBR reader follows [3] §2 directly; it memory-maps the block, so only the MARK, TIMESTAMP and 8 EEG rows of the C-ordered `(nt, nc, nb, ns)` array are read.

## Deviations from the plan

1. **`02_plan.md` is not in the first commit.** Its lines 37 and 93 name the local agent-tooling paths that are excluded through `.git/info/exclude`. The guard refuses those names in committed files, and builders may not edit the plan, so I left the file untracked (`git status`: `?? mas/state/phases/P00-bootstrap/02_plan.md`). **to orchestrator:** reword those two cells, then commit the plan.
2. **Checks added beyond the plan's list.** Each one becomes a deviation (exit 1), in the fail-loudly spirit of PF-09 [7]. (a) A file that cannot be read (truncated, unsupported `data_type`, missing `end_header`/required key) is reported as `unreadable: …` instead of crashing. (b) The header's channel count differs from the number of `channel_k` lines. (c) Bytes remain after the declared block (§2 defines the block size exactly). (d) MARK values are not integers or not finite. (c) is the strictest. If the real files carry trailing bytes, the runner will see it, and the fix is an orchestrator decision, not tuning.
3. `stim_events` for `kind = unknown` counts both 101–105 and 1001–1005 [own: the plan does not say; unknown files get a warning only, no protocol check].
4. Exit 1 also when `--raw-dir` does not exist or holds no `.ebr` file [own: an empty inventory must not pass silently]. A subject named in `--subjects` with no folder prints `[-] Skipping <S>: folder not found` [1] §4.
5. `tests/__init__.py` was created (the plan allowed "or none"). It lets the tests import `scripts.exploration.inventory_raw` under pytest's rootdir insertion.
6. Extra target `make help` (the default goal). Extra commit 127ba13 rewords my own `.gitignore` comment, which had wrongly said that `SSVEPs_OO_mOO/` holds recordings.
7. P00.3: the guard accepts a command that mentions `data/raw` only when it starts literally with `git check-ignore` (no `git -C`, no `cd …&&`). Verifiers and runners need to know this.

## How to run / reproduce

```bash
make venv                                   # once: .venv + requirements.txt
.venv/bin/python scripts/exploration/inventory_raw.py          # runner only: real data
.venv/bin/python -m scripts.exploration.inventory_raw --raw-dir <synthetic dir> --out <csv>
.venv/bin/python -m pytest -q               # or: make test
```

## How I verified

- Environment: `.venv/bin/pip install -r requirements.txt` exited 0 (log `mas/state/scratch/pip_install_P00.log`). Imported versions [6]: Python 3.12.3, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0, scikit-learn 1.9.1, joblib 1.6.0, torch 2.14.1+cu130 (`torch.cuda.is_available()` True, CUDA 13.0, RTX 3050 Laptop GPU), pyyaml 6.0.3, matplotlib 3.11.2, seaborn 0.13.2, mne 1.13.2, mne-connectivity 0.9.0, shap 0.54.1, pytest 9.1.1.
- `.venv/bin/python -m pytest -q` → `..  [100%]` (2 passed); `make -s test` gives the same.
- CLI smoke run on synthetic files only (generator `mas/state/scratch/P00_synth/make_synth.py`, output under `mas/state/scratch/P00_synth/`):
  - `raw/`: S01 {OO clean, mOO with 3-sample plateau pulses, C as a float32 block, online_OO with 7 codes in 1001–1005, cb_mas_mcb 309,816 samples / 80 stim}, `S01/photo.jpg`, S02/OO with `sampling_rate 250`, an empty S03, and the decoys `S1x/`, `notes/`. Console: `[-] Skipping S03: no .ebr files`; 6 rows (S1x, notes and the .jpg ignored); mOO counts identical to OO (plateau = one onset); stim 40/40/40/7/80; 154,904 samples → 605.1 s; session start `2021-10-28 21:34` from TIMESTAMP[0] = 1635456840000 ms (the float32 file shows 21:32 because float32 cannot hold a 1.6e12 ms value, an artifact of that synthetic file); `[x] DEVIATION S02/OO: fs 250, expected 256`; `6 files, 2 subjects, 1 deviations`; exit 1. Run as a module with `--subjects S01 S09`: `[-] Skipping S09: folder not found …`, `5 files, 1 subjects, 0 deviations`, exit 0.
  - `bad/S07`: renamed PO7, truncated file, `data_type bogus`, wrong magic, online run containing code 202. Each was reported as a deviation (`unreadable: … truncated, 13631810 bytes < 13631910 declared`, `unsupported EBR data_type 'bogus'`, channel list, magic, `unexpected codes [202] in an online run`); `5 files, 1 subjects, 14 deviations`; exit 1. A missing `--raw-dir` gives `[x] Raw folder not found`, exit 1.
- P00.3: `git check-ignore -v --no-index` on path strings only:
  `data/raw/S01/OO.ebr`, `data/raw/S02/photo.jpg`, `data/raw/S02/video.mp4`, `data/processed/S01/X.npy`, `data/processed_continuous/S01/y.npz` → `.gitignore:14:data/`; `outputs/m.pt` → `.gitignore:28:outputs/`; `reports/raw_inventory.csv` → `.gitignore:29:reports/`; `SSVEPs_OO_mOO/` → `.gitignore:21`; `.venv/` → `.gitignore:9`; `mas/state/scratch/x` → `.gitignore:39`; the local agent files → `.git/info/exclude:9` and `:11`. Data-like tracked files on the branch (`git ls-files | grep -ciE '^data/|\.(npy|npz|pt|joblib|mp4|jpe?g)$'`): 0. Commit messages on `main..HEAD` contain no vendor or co-author mention (grep count 0).
- Nothing under `data/raw/` was read, listed or run. `reference/` was not opened.

## Left to do / known limitations

- Real-data run (`reports/raw_inventory.csv`, log under `reports/logs/P00/`) belongs to the runner.
- How `p99_abs_eeg_uv` pools the channels is not stated in [3]. The plan's first attempt is used here (8 EEG channels pooled, whole file). A mismatch with §4 beyond ±0.1 µV is a reference-consultation trigger (R11), not a tuning target.
- `.venv` is not reproducible bit-for-bit: `requirements.txt` sets only lower bounds, as [1] §1 does. The installed versions are listed above.
- The minimal reader is temporary; P01 replaces it with `src/io/ebr_parser.py`.

## Reference consultations (R11)

None.

| # | Trigger (failed test / deviation / verification) | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| — | — | — | — | — |

## Sources

1. RULE — `mas/02_REQUIREMENTS.md` §1 (environment), §2 (layout), §4 (conventions), §7 (event-onset test). Opened in this run.
2. RULE — `mas/RULES.md` era matrix; `AGENTS.md` golden rule 1 (no data in git).
3. RULE — `mas/01_DATA_SPEC.md` §1 (layout, `^S\d+$`, non-`.ebr` ignored), §2 (header, dtype table, `(nt, nc, nb, ns)`, the 11 channels), §3 (onset rule, calibration counts, online codes 1001–1005), §4 (inventory, joined run 80 stim events).
4. REQUEST — `mas/state/phases/P00-bootstrap/02_plan.md`, work split and "Inventory script design"; `00_assignment.md` tasks P00.1–P00.3.
5. REQUEST — `02_plan.md` Questions Q1–Q3 (Sebastian's answers) and `mas/state/decisions.md` P00 rows, 2026-10-24.
6. DATA — `mas/state/scratch/pip_install_P00.log` (`.venv/bin/pip install -r requirements.txt`, exit 0) and the `__version__` import check, run on 2026-10-24.
7. RULE — `mas/05_PITFALLS.md` PF-09 (lines 56–59: "scripts check that lengths match and fail loudly"; used in spirit only, as `00_assignment.md` states).

## Questions

ACK 02_plan.md data-engineer 2026-10-24

- to orchestrator: `02_plan.md` left untracked (Deviations 1). Please reword lines 37 and 93 and commit the plan.
- to orchestrator: should trailing bytes after the data block (Deviations 2c) stay a hard deviation, or become a warning? It is a hard deviation for now.

## Round 2

Trigger: `07_review.md` pre-run audit Round 1, Required fix 1 [8]. Status stays READY.

| Path | NEW / MODIFIED | Summary | Commit | Source |
|---|---|---|---|---|
| `.gitignore` | MODIFIED | `outputs/`, `reports/`, `baselines/` anchored at the root (`/outputs/`, `/reports/`, `/baselines/`), so committed phase reports under `mas/state/reports/` are no longer ignored. `data/` and the data extensions (`*.ebr`, `*.npy`, `*.npz`, `*.pt`, `*.joblib`, `*.mp4`, `*.jpg`, `*.jpeg`) still match at any depth | 9d5c5a9 `fix: anchor generated-output ignore patterns at the repo root` | [8], [2] |
| `scripts/exploration/inventory_raw.py` | MODIFIED | optional review nit: subject discovery uses `SUBJECT_PATTERN.fullmatch` instead of `match`, so `$` can no longer accept a name with a trailing newline | c7697c0 `fix: match subject folders with fullmatch in the inventory` | [8], [3] §1 |

Evidence (path strings only), `git check-ignore -v --no-index mas/state/reports/P00.md reports/raw_inventory.csv reports/logs/P00/x.log outputs/m.pt outputs/reports/x.csv baselines/x.csv data/raw/S01/OO.ebr data/processed/S01/X.npy`, verbatim:

```
.gitignore:29:/reports/	reports/raw_inventory.csv
.gitignore:29:/reports/	reports/logs/P00/x.log
.gitignore:28:/outputs/	outputs/m.pt
.gitignore:28:/outputs/	outputs/reports/x.csv
.gitignore:30:/baselines/	baselines/x.csv
.gitignore:14:data/	data/raw/S01/OO.ebr
.gitignore:14:data/	data/processed/S01/X.npy
```

`mas/state/reports/P00.md` is absent from that output. Checked alone, `git check-ignore -v --no-index mas/state/reports/P00.md` prints nothing and exits 1 (not ignored).

Tests after both commits: `.venv/bin/python -m pytest tests/ -p no:cacheprovider -o addopts=""` → `60 passed in 2.60s`.

Sources (Round 2): 8. HANDOFF — `mas/state/phases/P00-bootstrap/07_review.md`, pre-run audit Round 1, Required fix 1 (line 36) and the fullmatch nit, as relayed by the orchestrator.
