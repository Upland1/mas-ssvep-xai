# P01 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §2–§3, mas/02_REQUIREMENTS.md §3, §4, §7, mas/05_PITFALLS.md PF-04/05/06
Approved by Sebastian: [x]   Date:2026-10-24        (required only if PLAN_APPROVAL: required)

## Goal

Provide the project's `.ebr` reader, the v1 configuration and the legacy band-pass
filter, and show that the reader reproduces the P00 inventory byte for byte.

## Data source

Raw recordings `data/raw/S*/*.ebr`: the 10 delivered files (OO, mOO of S01–S05;
B005). fs from each header. No windows, no quality decision.

## Scope

**In:** `src/io/ebr_parser.py`, `configs/pipeline_config.yaml` v1,
`src/preprocessing/signal/filters.py`, the switch of
`scripts/exploration/inventory_raw.py` to the parser (announced in the P00 plan:
"P01 replaces it with `src/io/ebr_parser.py`"), Makefile target.

**Out:** windowing, preprocessing script, quality gates (P02); any change to the
P00 inventory's columns, checks or output format.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| data-engineer | NEW `src/io/ebr_parser.py` | `load_ebr_file(path) -> dict` per [3] §2: header lines until `end_header`, blank lines skipped, unknown keys ignored, magic case-insensitive after strip, `marks` lines `mark_<k> <sample_index> <label>`, block of `nt*nc*nb*ns` elements in the dtype table, reshaped `(nt, nc, nb, ns)` C order, real types cast to float64, complex128 kept; returns exactly the 14 keys of [3] §2. Unknown `data_type` → `ValueError`; truncated block → `ValueError` (no silent short read). Helpers with the roadmap signatures (below) | P01.1 | [3] §2 |
| data-engineer | NEW `configs/pipeline_config.yaml` | v1 copied verbatim from [1] §3, comment `# PO7 hard-excluded (legacy)` kept | P01.2 | [1] §3, PF-05 |
| data-engineer | NEW `src/preprocessing/signal/filters.py` | `apply_iir_bandpass` exactly as the roadmap formula (`iirfilter` b/a + `filtfilt`, `axis=-1`, scipy default padding) | P01.3 | [2] P01.3 |
| data-engineer | MODIFIED `scripts/exploration/inventory_raw.py` | read files with `load_ebr_file` instead of the private memmap reader; keep every check, column and the public function names the P00 tests import (thin wrappers allowed); root discovery via `configs/pipeline_config.yaml` now that it exists | acceptance | P00 `02_plan.md` |
| data-engineer | MODIFIED `Makefile` | target `inventory` unchanged; nothing else unless needed | — | [own] |

Helper semantics (the roadmap gives signatures only; first attempt, R11 allows a
check against the original afterwards):

- `resolve_recording_path(raw_root, session, filename) -> Path`: `raw_root /
  session / filename`, where `session` is the subject folder (e.g. `S01`) and
  `filename` the run file (`OO.ebr`; a stem without suffix gets `.ebr`). Raises
  `FileNotFoundError` naming the path when absent.
- `select_scalp_channels(channels, scalp_names) -> list[int]`: indices of
  `scalp_names` **in the order of `scalp_names`**, looked up by name (PF-06);
  a missing name raises `ValueError`.
- `get_mark_channel_index(channels, mark_name="MARK") -> int`: index or −1.
- `extract_scalp_signal(recording, scalp_names) -> (np.ndarray (C, T), list[str])`:
  `recording["data"][0, idx, 0, :]` for the selected indices, float64, names in
  the same order.

## Legacy behaviour in this phase

Config v1 excludes PO7 (`channels.scalp` = 7 names, `excluded: ["PO7"]`), labelled
by the comment `# PO7 hard-excluded (legacy)`. It stays reachable after P07 because
P07 changes the config, and git keeps v1 (tag `p01-done`). The parser itself is
montage-agnostic: it returns all 11 channels.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R6 | wrong reshape order (e.g. `(nc, ns)` Fortran, or `(ns, nc)`) silently mixes channels | round-trip test with a distinct planted pattern per channel and per sample |
| PF-06 | positional channel selection | lookup by name; test with a shuffled channel list |
| PF-05 | PO7 exclusion leaks into the parser | parser returns all channels; only the config excludes PO7 |
| PF-04 | an `fs=250` default sneaks into the filter | `fs` is required; test at fs 256 |
| Silent truncation | `np.fromfile` returns fewer elements on a short file | explicit size check, `ValueError`; test |
| Inventory regression | switching readers changes a number | P00 tests unchanged and passing; real-data CSV byte-identical to P00's |
| R11 | `after-attempt` | consult `reference/` only after own implementation + tests; log it |

## Tests required

Synthetic only.

| Test | Simulated input | Expected result | Tolerance | Source of the answer |
|---|---|---|---|---|
| EBR round-trip | header + doubles, nt=1, nc=11, nb=1, ns=1000, channel c sample t = `1000*c + t` | the 14 keys; `data.shape == (1, 11, 1, 1000)`; `data[0, c, 0, t] == 1000*c + t`; channels, fs, comments, marks equal what was written | exact | [3] §2 |
| layout nt, nb > 1 | nt=2, nc=3, nb=2, ns=5, value encodes (t, c, b, s) | `data[t, c, b, s]` equals its code (R6) | exact | [3] §2 |
| dtype table | one file per dtype string of [3] §2 (20 strings) | parsed dtype float64 for real types, complex128 for both complex strings; values preserved | exact | [3] §2 |
| unsupported dtype | `data_type bogus` | `ValueError` | — | [3] §2 |
| truncated block | header says ns=1000, 999 written | `ValueError` | — | [own] |
| header rules | blank lines, unknown key, `EBR Binary 1.0` magic, `marks 2` with two mark lines | parsed; marks list of (index, label) | exact | [3] §2 |
| helpers | shuffled channel list; MARK absent; missing scalp name; missing file | name-ordered indices; −1; `ValueError`; `FileNotFoundError` | exact | [own] |
| extract_scalp_signal with config v1 | 11-channel recording, v1 `scalp` | shape `(7, T)`, names = v1 list, PO7 absent, rows equal planted channels | exact | [1] §3 |
| config v1 | load YAML | equals [1] §3 v1 verbatim (key by key) | exact | [1] §3 |
| band-pass gain | fs 256, 10 s; sinusoids 0.2 Hz, 10 Hz, 24 Hz, 100 Hz | central-segment RMS gain ≈ 1 at 10 and 24 Hz; < 0.05 at 0.2 and 100 Hz | ±0.02 (pass band) | Butterworth response, [own] |
| zero phase | 10 Hz sinusoid | filtered vs input cross-correlation peak at lag 0 | 0 samples | `filtfilt` [4] |
| filter axis | `(2, 3, T)` array | each row equals filtering that row alone | 1e-12 | [2] P01.3 |
| filter equals formula | random input | equals `filtfilt(*iirfilter(4, [1/128, 60/128], btype="bandpass", ftype="butter"), x)` | 1e-12 | [2] P01.3 |
| P00 regression | the P00 test suite | all pass unchanged | — | P00 |

Historical-bug requirement: no PF entry belongs to P01. The layout test fails on a
Fortran-order or `(ns, nc)` reshape, and the truncated-block test fails on a plain
`np.fromfile(...).reshape(...)` that would raise an unhelpful error or misread.

## Run commands (for the runner)

```bash
.venv/bin/python scripts/exploration/inventory_raw.py --out reports/P01/raw_inventory_parser.csv
cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv
```

The first command reads the 10 delivered files through `load_ebr_file`; the
second compares with the P00 inventory (must print nothing, exit 0). Expected
runtime and device: < 1 min, CPU (full reads, ≈ 136 MB). Over
`LOCAL_RUN_BUDGET_MIN` (30)? no. Console log to
`reports/logs/P01/inventory_raw_<timestamp>.log` with command and HEAD.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference (R-x, tolerance) |
|---|---|---|
| parsing all 23 files gives the inventory of P00 (B005: the 10 delivered files) | re-run the first command from a clean checkout; `cmp` against `reports/raw_inventory.csv` of P00 → identical; summary `10 files, 5 subjects, 0 deviations` | P00 CSV, exact |
| tests pass | full `pytest -q` in the clean checkout, including the unchanged P00 tests | — |
| config v1 | YAML equals `02_REQUIREMENTS.md` §3 v1 | exact |

## Amendment — pre-run audit Round 1 (2026-10-24)

`07_review.md` required fix 3 replaces the run commands above. The amendment adds a
strict-mode pass and changes neither scope nor compute (< 1 min, CPU). The
roadmap's contract `load_ebr_file(path)` defaults to `strict=True`, so the real
headers must pass it in P01, not first in P02.

```bash
sha256sum reports/raw_inventory.csv
.venv/bin/python scripts/exploration/inventory_raw.py --out reports/P01/raw_inventory_parser.csv
cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv
.venv/bin/python scripts/exploration/inventory_raw.py --strict --out reports/P01/raw_inventory_parser_strict.csv
cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser_strict.csv
sha256sum reports/raw_inventory.csv
```

Expected: both runs print `10 files, 5 subjects, 0 deviations` and exit 0, both
`cmp` print nothing, and the two sha256 lines are identical
(`e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14`, the P00 file).
If strict mode fails on a real file, the runner stops (`05_run.md` BLOCKED) and the
orchestrator opens a blocker; `_check_consistency` is never relaxed to make the run
pass (`decisions.md`).

Added acceptance check: "both inventory runs (default and `--strict`) are
byte-identical to the P00 inventory".

## Sources

1. `mas/02_REQUIREMENTS.md` §3, §4, §7 (opened in this run).
2. `mas/03_ROADMAP.md` P01 (opened in this run).
3. `mas/01_DATA_SPEC.md` §2–§3 (opened in this run).
4. SciPy `signal.filtfilt` / `signal.iirfilter` documentation (for the builder and tester to open and cite).

## Questions

Q1. The roadmap leaves `resolve_recording_path`'s semantics open. The plan reads
`session` as the subject folder and `filename` as the run file. OK, or do you
remember a different meaning (e.g. `session` = `OO`)?
