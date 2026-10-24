# P01 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (+ Amendment, audit Round 1), 05_run.md, 07_review.md, B005, the phase branch
Clean checkout: `mas/state/scratch/verify_P01` @ 8d29fd7c03559d96e5b27c068c1c9bdd09aaff33 (removed after use)

Verdict: PASS

## 1. Tests on the clean checkout

```bash
git worktree add --detach mas/state/scratch/verify_P01 HEAD
cd mas/state/scratch/verify_P01 && <repo>/.venv/bin/python -m pytest
```
Output: `248 passed in 7.26s` (0 failed).

## 2. Inventory re-run from the clean checkout (default and --strict)

Run via `<repo>/.venv/bin/python mas/state/scratch/run_inv.py <repo>` (a subprocess wrapper that
launches `scripts/exploration/inventory_raw.py [--strict] --raw-dir <repo>/data/raw --out
mas/state/scratch/verify_P01_out/<name>.csv` from the worktree and prints the exit code).

```
default exit 0 [... '10 files, 5 subjects, 0 deviations', 'Saved: .../verify_P01_out/default.csv']
strict  exit 0 [... '10 files, 5 subjects, 0 deviations', 'Saved: .../verify_P01_out/strict.csv']
```
```
cmp reports/raw_inventory.csv verify_P01_out/default.csv -> identical
cmp reports/raw_inventory.csv verify_P01_out/strict.csv  -> identical
cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv        -> identical
cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser_strict.csv -> identical
e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14  reports/raw_inventory.csv (and both re-runs)
```
Acceptance applies to the 10 delivered files (B005); met.

## 3. Config v1

Python command: parse the yaml block after `**v1 (P01, legacy):**` in `mas/02_REQUIREMENTS.md` and
`configs/pipeline_config.yaml` with `yaml.safe_load`, compare (`mas/state/scratch/cfg.py`).
Output: `equal: True top keys ['channels', 'features', 'paths', 'preprocessing', 'project', 'training']`.

## 4. Roadmap tasks P01.1-P01.4

- `src/io/ebr_parser.py`: `load_ebr_file(path, strict=True)`, `resolve_recording_path(raw_root, session, filename)`,
  `select_scalp_channels(channels, scalp_names) -> list`, `get_mark_channel_index(channels, mark_name="MARK")`
  (`return channels.index(mark_name) if n else -1`), `extract_scalp_signal(recording, scalp_names) -> tuple`. Present.
- `src/preprocessing/signal/filters.py::apply_iir_bandpass(data, fs, lowcut=1.0, highcut=60.0, order=4)`:
  `iirfilter(order, [lowcut/nyq, highcut/nyq], btype="bandpass", ftype="butter")` + `filtfilt(..., axis=-1)`. Matches.
- Tests (round-trip, dtype table, unsupported dtype) in `tests/test_p01_*.py`; included in the 248 passed.
- `git diff main -- tests/test_p00_*`: 0 bytes (P00 tests unchanged).

## 5. Privacy / git

- Tracked data-like or local-tooling files (recording/image/video/array/csv/model extensions, `data/`, `reports/`, local tooling dirs, reference/): none.
- Vendor/assistant names and co-author lines (pattern assembled from fragments) in author fields and commit messages main..HEAD (22 commits): 0 matches. In committed content at HEAD: 0 matches.
- `git check-ignore -v data/raw/S01/OO.ebr` -> `.gitignore:14:data/	data/raw/S01/OO.ebr`.
- `git status --short` clean at start.

## 6. R11 reference consultations

`mas/state/scratch/reference_access.log`: the known 15:07:09 line (P00 verifier privacy grep) plus one new
line at 2026-10-24T16:27:04 (verifier, Bash), which is this verification's own logged privacy grep (it matches
the vendor-name pattern; it is not a read of `reference/`). No P01 builder, tester or runner access is logged.

## Reasons (if FAIL)

None.
