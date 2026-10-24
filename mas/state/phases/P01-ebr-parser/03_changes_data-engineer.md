# P01 · 03 · Changes — data-engineer

Status: READY
Author: data-engineer
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/01_DATA_SPEC.md §2–§3, mas/02_REQUIREMENTS.md §3, §4, §7, mas/05_PITFALLS.md PF-04/05/06, mas/state/decisions.md (P01 Q1)
Branch: phase/P01-ebr-parser (from main @ b502144)
Commit(s): 5863a12 (chore: bookkeeping), b86c8f9 (config v1), 7eeff83 (filter), 5be6c0c (parser + smoke tests), 6659a12 (inventory switch), 8227957 (this file); Round 2: b7bc198, 73498f5, ba39d8b, this file in the next commit

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/io/ebr_parser.py` | NEW | `load_ebr_file(path, strict=True) -> dict` with exactly the 14 keys of [1] (`RECORDING_KEYS`); header rules of [1] (blank lines skipped, unknown keys ignored, magic case-insensitive after strip, `mark_<k> <index> <label>` → `(int, str)`); block of `nt*nc*nb*ns` elements in the 20-string dtype table, reshaped `(nt, nc, nb, ns)` C order, real → float64, complex128 kept; `ValueError` on unknown dtype, missing `end_header`/required key, short block (size checked before reading, plus an element-count check after `np.fromfile`). Also `read_ebr_header`, `open_ebr_block` (lazy memmap, file dtype), `block_shape`, `trailing_bytes`, `ebr_dtype`, and the four helpers with the roadmap signatures and the plan's semantics | P01.1 | [1], [2], [6], PF-06 |
| `configs/pipeline_config.yaml` | NEW | v1 extracted verbatim from [3] §3 (36 lines, comment `# PO7 hard-excluded (legacy)` kept) | P01.2 | [3] §3, PF-05 |
| `src/preprocessing/signal/filters.py` | NEW | `apply_iir_bandpass(data, fs, lowcut=1.0, highcut=60.0, order=4)`: `iirfilter(order, [low/nyq, high/nyq], btype="bandpass", ftype="butter")` + `filtfilt(b, a, x, axis=-1)`, scipy default padding; `fs` required (no default); `ValueError` unless `fs > 0` and `0 < lowcut < highcut < fs/2` | P01.3 | [2] P01.3, [5], PF-04 |
| `scripts/exploration/inventory_raw.py` | MODIFIED | the private reader is gone; `ebr_dtype`, `parse_ebr_header`, `open_ebr_data`, `trailing_bytes` are thin wrappers over the parser; `inventory_file` reads data with `load_ebr_file(path, strict=False)` and keeps every P00 check as a deviation; `--raw-dir` default = ROOT / `paths.data_raw_dir` of the config (same value `data/raw`); root found by the existing upward search for `configs/pipeline_config.yaml`, which now exists | acceptance | P00 `02_plan.md`, [3] §3–§4 |
| `tests/test_p01_parser_smoke.py` | NEW | builder smoke tests (29 cases): 14 keys + coded `(2,3,2,5)` layout, every dtype string, loud failures (bogus dtype, truncated, magic, name count, trailing bytes; non-strict tolerance), helpers, `extract_scalp_signal` with config v1, filter = formula, `fs` required | P01.4 (smoke only) | [1], [2] |
| `Makefile` | unchanged | target `inventory` already runs the script | — | — |

## Legacy behaviour implemented

Config v1 excludes PO7 (`channels.scalp` = 7 names, `excluded: ["PO7"]`), labelled by
the verbatim comment `# PO7 hard-excluded (legacy)` (PF-05). Stays reachable after P07
through git (tag `p01-done`). The parser is montage-agnostic: it returns all 11 channels;
only `extract_scalp_signal(rec, cfg["channels"]["scalp"])` drops PO7.

## Differences from the cited examples

None. The filter is the roadmap formula [2] with the SciPy calls as documented [5].

## Deviations from the plan

1. **`strict` keyword on `load_ebr_file`** [own]. Default `True` adds three loud checks
   the spec implies but does not list as errors: magic ≠ `ebr binary 1.0`, a
   channel/band/trial/comment/mark list not numbered exactly `_1..n` as declared, and
   bytes after the declared block. The inventory calls `strict=False` because P00 reports
   these as row deviations with the other columns filled (P00 tests
   `test_header_blank_lines_unknown_keys_and_magic_case`, channel-count and
   trailing-bytes tests); raising would have changed P00 rows. Unknown dtype, missing
   `end_header`/required key and a short block raise in both modes.
2. **Extra public functions** in the parser (`read_ebr_header`, `open_ebr_block`,
   `block_shape`, `trailing_bytes`, `ebr_dtype`, constants `EBR_DTYPES`, `EBR_MAGIC`,
   `RECORDING_KEYS`) [own]: the inventory's P00 names need a header with `magic` and
   `data_offset` and a lazy memmap in the file dtype (P00 test `test_float32_block_parsed`
   asserts `float32`), which the 14-key dict cannot give.
3. **Helper strictness beyond the plan** [own]: `select_scalp_channels` also raises on
   a name repeated in `scalp_names` or present twice in `channels`;
   `get_mark_channel_index` raises if `MARK` appears twice; `extract_scalp_signal` raises
   for complex data, `nt != 1` or `nb != 1` (the continuous signal `data[0, c, 0, :]` is
   only defined for nt = nb = 1 [1]) and for a name list whose length differs from the
   data channel axis.
4. **Inventory reads whole files** instead of three channels via memmap (≈ 136 MB for 10
   files, per plan). Header is parsed twice per file (once for `magic`/`data_offset`).
5. **`--raw-dir` default from config** `paths.data_raw_dir` ([3] §3 "scripts read paths
   from the config"); value identical to P00's default.

## How to run / reproduce

```bash
.venv/bin/python -m pytest tests/ -q
# runner only (real data):
.venv/bin/python scripts/exploration/inventory_raw.py --out reports/P01/raw_inventory_parser.csv
cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv
```

## How I verified

- `.venv/bin/python -m pytest tests/ -q` → 92 passed (P00 tests unchanged, 63 P00 cases + 29 new smoke cases).
- Old-vs-new inventory on a synthetic tree (`mas/state/scratch/p01_de/make_synth.py`, built
  with the P00 test writers: 15 files over S01–S05 incl. float32, wrong magic, 8 trailing
  bytes, truncated by 100 bytes, 10 names for 11 declared channels, `data_type bogus`).
  The P00 script (`git show HEAD:...` before the switch, saved as
  `mas/state/scratch/p01_de/inventory_raw_p00.py`) and the new script, both as a file and as
  `python -m scripts.exploration.inventory_raw`, give **byte-identical CSVs** (`cmp`
  silent) and identical console output except the CSV path; both exit 1 with
  `15 files, 5 subjects, 16 deviations`. A first round differed only in the truncated
  message text; the parser now checks the size up front with P00's message.
- Real data not read (runner's job).
- SciPy 1.18.1 docstrings of `filtfilt` and `iirfilter` opened: default `axis=-1`,
  `padtype='odd'`, `padlen = 3*max(len(a), len(b))`, `Wn` normalized to Nyquist [5].

## Left to do / known limitations

- Known-answer suite (P01.4: round-trip 1×11×1×1000, layout, 20 dtypes, band-pass gain,
  zero phase, axis) belongs to the synthetic-tester.
- `strict=True` has not seen the real headers; the P00 run (0 deviations on 10 files,
  `reports/raw_inventory.csv`) covers magic, channel count and trailing bytes, but
  not the band/trial/comment numbering. If a real file fails strict mode in P02, it
  is a header fact to document, not something to relax silently.
- `mark_<k>` labels are stripped (P00 kept internal spacing after the first space);
  no delivered file has marks (`marks 0` [1]).

## Reference consultations (R11)

None. `reference/` was not opened.

| # | Trigger (failed test / deviation / verification) | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| — | — | — | — | — |

## Sources

1. RULE — `mas/01_DATA_SPEC.md` §2–§3 (opened in this run). Used for: header keys, dtype table, `(nt, nc, nb, ns)` C order, cast rules, the 14 returned keys, magic rule, channel table.
2. RULE — `mas/03_ROADMAP.md` P01 tasks, as quoted verbatim in `00_assignment.md` (opened in this run). Used for: function signatures and the filter formula.
3. RULE — `mas/02_REQUIREMENTS.md` §3, §4, §7 (opened in this run). Used for: config v1 text, root discovery, library conventions, EBR round-trip test.
4. RULE — `mas/05_PITFALLS.md` PF-04, PF-05, PF-06 (opened in this run). Used for: required `fs`, PO7 legacy exclusion, name-based selection.
5. DOCS — SciPy v1.18.1, `scipy.signal.filtfilt` and `scipy.signal.iirfilter` docstrings (read via the installed package in this run). Used for: axis, default padding, normalized `Wn`.
6. RULE — `mas/state/decisions.md`, P01 row on `resolve_recording_path` (opened in this run). Used for: `session` = subject folder, `filename` = run file, `.ebr` appended to a bare stem.

## Questions

None.

## Round 2 — pre-run audit Round 1 fixes

Reads: 07_review.md (Round 1, commit 1aa8cf6), 02_plan.md amendment (commit 21f9d87).

| Fix | Path | NEW / MODIFIED | What | Commit | Source |
|---|---|---|---|---|---|
| Required fix 1 | `scripts/exploration/inventory_raw.py` | MODIFIED | `--strict` flag (default off), passed as keyword `strict=False` through `run_inventory` → `inventory_file` → `ebr_parser.load_ebr_file(path, strict=strict)`. A strict `ValueError` goes to the existing `unreadable: <message>` deviation, so the run exits 1. Without the flag the call is the Round 1 call (`strict=False`) | b7bc198 | 07_review fix 1 |
| Note 3 (fix 1) | `src/io/ebr_parser.py` `ebr_dtype` | MODIFIED | `data_type` now matched **exactly** (no `strip`/`lower`): `Double`, `DOUBLE`, ` double` raise `ValueError`. Reasoning: §2 [1] says "any other value raises `ValueError`", and §2 states every delivered file has `data_type double` (measured), so exact matching follows the spec and should not reject a delivered file. If one does, the run fails loudly and that becomes a header fact to record, not something to hide | 73498f5 | [1], 07_review note 3 |
| Note 2 | `src/io/ebr_parser.py` `read_ebr_header` docstring | MODIFIED | documents the defaults `trials = bands = 1`, `comments = marks = 0` [own] and that a repeated line keeps its last value | 73498f5 | 07_review note 2 |
| Note 4 | `src/io/ebr_parser.py` `_check_consistency` | MODIFIED | strict mode now raises on any repeated header line (`channel_3` twice, `channel_3` and `channel_03`, or two `samples` lines), listed in the message. Non-strict keeps the last value (P00 behaviour) | 73498f5 | 07_review note 4, [own] |
| Fix 1 test | `tests/test_p01_parser_smoke.py` | MODIFIED | 3 smoke tests. (1) `--strict` on a spec-conformant synthetic file gives a CSV byte-identical to the one without it, both exit 0. Dropping `comment_1` gives exit 0 without the flag and exit 1 with it, with an `unreadable:` deviation that names `comment`. (2) Exact dtype matching. (3) A repeated `channel_3` raises in strict mode and keeps the last value in non-strict mode | ba39d8b | [own] |

The non-strict path is unchanged and the P00 tests still pass unchanged. On the Round 1
synthetic tree (`mas/state/scratch/p01_de/synth`, 15 files), the CSV without the flag is
again byte-identical to the P00 script's CSV (`cmp` silent, exit 1 as before). With
`--strict` the same tree gives `15 files, 5 subjects, 5 deviations`, exit 1. The 5
deviations are all `unreadable:`, one each for the trailing-bytes, truncated,
wrong-magic, channel-count and bogus-dtype files. The clean double and float32 files
pass strict mode.

Suite (verbatim): `============================= 201 passed in 3.64s ==============================`
(`.venv/bin/python -m pytest tests/ -v`). It includes the synthetic-tester's P01
known-answer modules.

Reference consultations (R11) in Round 2: none.

No questions.
