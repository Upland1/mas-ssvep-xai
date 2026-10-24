# P01 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00_assignment.md, 02_plan.md, 03_changes_data-engineer.md, 04_tests.md, mas/state/decisions.md (P01 row), mas/state/blockers/B005-inventory-10-of-23-files.md, mas/RULES.md, mas/01_DATA_SPEC.md §1–§4, mas/02_REQUIREMENTS.md §3, §4, §7, mas/05_PITFALLS.md PF-04/05/06; code: src/io/ebr_parser.py, src/preprocessing/signal/filters.py, configs/pipeline_config.yaml, scripts/exploration/inventory_raw.py, tests/test_p01_*.py
Audited commit: 2897767 (branch phase/P01-ebr-parser)

## Pre-run audit — Round 1

Verdict: FAIL

Suite re-run by the reviewer: `.venv/bin/python -m pytest tests/ -p no:cacheprovider` → `198 passed in 3.53s`.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no CV in P01 |
| R2 Fit only in-fold | N/A | nothing fitted |
| R3 Filter continuous, then window | N/A | `apply_iir_bandpass` is a plain filter with no windowing (`src/preprocessing/signal/filters.py:22-23`); where it is applied is decided from P02 on |
| R4 Estimator small-sample bias | N/A | no estimator |
| R5 Shared quality decision, explicit thresholds | N/A | no quality gate; `vpp_thresh_uv`/`std_range` are only config values (`configs/pipeline_config.yaml:20-21`) |
| R6 Index layouts verified | PASS | C-order reshape `src/io/ebr_parser.py:225`; known answer with code `1000t+100c+10b+s` on `(2,3,2,5)` `tests/test_p01_ebr_known_answer.py:137-143`; Fortran, `(ns,nc)` and band/sample swap variants fail the assertion `:146-163`; a Fortran reshape inside the parser fails it `:166-185`; the struct-based writer does not depend on numpy's reshape `:54-78`. Round trip with 11 channels × 1000 samples `:107-126` |
| R7 Honest statistics | N/A | no statistics |
| R8 Smoothing respects trials | N/A | no smoothing |
| R9 Per-subject reporting with data source | PASS | per-file rows, data source raw `data/raw`, the 10 delivered files (B005); run output `reports/P01/raw_inventory_parser.csv` (`02_plan.md` run commands) |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | `03_changes_data-engineer.md` Sources 1–6 and `04_tests.md` Sources 1–6 cite the specs opened and the SciPy 1.18.1 docstrings; test docstrings tag `[spec §2]`, `[plan]`, `[roadmap]`, `[own]` (`tests/test_p01_ebr_known_answer.py:4-8`, `tests/test_p01_filters_known_answer.py:3-9`) |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no copied code declared; `reference/` not opened |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | both handoffs: "None"; `mas/state/scratch/reference_access.log` has no P01 entry (its only line is a P00 verifier command, 2026-10-24T15:07:09) |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | LEGACY (by design) | PF-05: `configs/pipeline_config.yaml:11-12` keeps `# PO7 hard-excluded (legacy)` verbatim and `excluded: ["PO7"]`; guarded by `tests/test_p01_config_known_answer.py:83-99` (text equals the §3 block, label present); the parser stays montage-agnostic (`tests/test_p01_ebr_known_answer.py:409-413`). Reachable after P07 through git (`p01-done`) |
| PF-06 channels by name | PASS | `src/io/ebr_parser.py:249-266` (`channels.index(name)`, order of `scalp_names`), `:281-301`; shuffled montage tests `tests/test_p01_ebr_known_answer.py:344-352`, `:390-406` |
| PF-04 fs | PASS | `src/preprocessing/signal/filters.py:7` has no `fs` default; `tests/test_p01_filters_known_answer.py:118-127` checks no default, `TypeError`, and that 256 vs 250 changes the output. The Era A `fs=250` assumption belongs to later feature code, not to P01. The parser returns the header's fs as a float (`src/io/ebr_parser.py:107`; `tests/test_p01_ebr_known_answer.py:129-132`) |
| Tests cover every change; at least one fails on the historical bug | PASS | no PF entry belongs to P01 (plan). Mutation checks: layout (above), plain-`fromfile` truncation `tests/test_p01_ebr_known_answer.py:249-259`, causal filter `tests/test_p01_filters_known_answer.py:66-73`, flattened axis `:88-95`. I checked other buggy variants by hand: `float` read as 8 bytes (caught by the size check and the value comparison, `:200-206`); trailing bytes consumed in non-strict mode (the reshape breaks, `:311-317`); big-endian read (`:216-222`); `fs` ignored (`:118-127`) |
| Changes match 02_plan.md and the roadmap tasks | **FAIL** | the run does not test the parser in its default mode on real data. The roadmap contract is `load_ebr_file(path)`, whose default is `strict=True` (`src/io/ebr_parser.py:190`), and P02 onward will call it that way. The only real-data run reads with `strict=False` (`scripts/exploration/inventory_raw.py:180`). So `cmp` can pass while the parser as delivered rejects every real file. Details in Judgement 1 and required fix 1. Minor, not blocking: `data_type` is matched case-insensitively (`src/io/ebr_parser.py:54`), but the spec says "any other value raises `ValueError`" and `03_changes` does not list this as a deviation (note 3) |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | **FAIL** | no tracked file is data-like: `git ls-files` (103 files) has nothing matching the recording suffix, `data/`, `reports/`, `outputs/`, `baselines/`, the answer-key folder, the local tooling folder, or `npz/npy/mat/edf/csv/pkl/pt`. Branch commit messages contain no vendor name and no co-author line. **But** `mas/state/phases/P01-ebr-parser/00_assignment.md:6` (committed in 5863a12) names the local, git-excluded agent-instructions file (`.git/info/exclude:9`), and that file name contains the assistant vendor name. Found with a case-insensitive `git grep` over HEAD, using a pattern assembled from fragments; this is the only hit in the tree |

### Judgements requested by the orchestrator

1. **Builder deviations.**
   - *`strict=True` default.* Justified. The spec gives the magic rule and the `_1..n` numbering (`mas/01_DATA_SPEC.md` §2). Bytes after the block contradict "block size is `nt*nc*nb*ns` elements". All three checks fail loudly. A spec-conformant header passes strict mode: the writer in the tests follows §2 literally, and `tests/test_p01_ebr_known_answer.py:334-339` shows that strict and non-strict give identical results on such a file.
   - *Could strict mode reject a real file?* The P00 run checked the magic, the channel count and the trailing bytes on the 10 files (`reports/logs/P00/inventory_raw_20261024_141334.log`: `10 files, 5 subjects, 0 deviations`). It never checked the `band_k`, `trial_k` and `comment_k` numbering (`scripts/exploration/inventory_raw.py:192-204`). §2 lists only the sampling rate and the channel list as "observed in all 23 files". So strict mode can still reject a real file on a fact nobody has measured.
   - *Decision.* The run must **also** exercise strict mode on the 10 delivered files, in this phase. Otherwise a P02 failure would force a P01 parser change inside P02. **Required fix 1** (data-engineer), **2** (synthetic-tester), **3** (orchestrator, run commands).
   - *Extra public functions.* Justified. The P00 tests need the header with `magic` and `data_offset`, and a memmap in the file's dtype (`03_changes` deviation 2). The 14-key contract of `load_ebr_file` is unchanged (`src/io/ebr_parser.py:228-230`; `tests/test_p01_ebr_known_answer.py:113`).
   - *Stricter helper errors.* Justified. Each raises loudly in a case where a name lookup is ambiguous, or where `data[0, c, 0, :]` is undefined (§2). None of them changes a result on spec-conformant input.
   - *Full reads.* Justified. They match the plan (≈ 136 MB), and the full read is what lets the run exercise `load_ebr_file` itself.
2. **Missing `bands`/`trials` line** (tester observation 1). No fix required. Every §2 header has both lines. Strict mode rejects such a file loudly. Non-strict mode is the inventory's documented tolerant path, and the inventory still checks `trials == bands == 1` (`scripts/exploration/inventory_raw.py:200-201`). The strict run of fix 1 will show whether the real headers have the lines. Optional (note 2): document the defaults `trials = bands = 1`, `comments = marks = 0` in the `read_ebr_header` docstring.
3. **Legacy labels and layout.** PF-05 is labelled and guarded by a text-equality test. PF-06 selects by name, tested with shuffled montages. PF-04: no fs default anywhere in P01. The R6 layout is proven, and wrong layouts fail the proof (table above).
4. **Run and acceptance.** The plan's command writes to `reports/P01/`, so it does not overwrite the P00 CSV, and `cmp` against `reports/raw_inventory.csv` is the right exact check. That CSV is still the file of the P00 run (2098 bytes, mtime 14:13, the same time as the P00 log). Its sha256 now is `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14` (`sha256sum reports/raw_inventory.csv`). The runner should record it before and after the run. The run is incomplete without the strict pass (fix 3).
5. **Privacy.** See the last table row. One committed vendor-name mention, owned by the orchestrator (required fix 4).

### Required fixes

1. **data-engineer — "Changes match plan" row; `scripts/exploration/inventory_raw.py:180`, `:289-298`.** Add a `--strict` flag, default off. With it, `inventory_file` calls `ebr_parser.load_ebr_file(path, strict=True)`. A strict `ValueError` goes to the existing `unreadable: <message>` deviation path, so the run exits 1. Without the flag, behaviour, CSV and console output stay exactly as now (the P00 tests must still pass unchanged). Thread the flag through `run_inventory`/`inventory_file` with a keyword whose default is `False`. Add one smoke test. Record it in `03_changes_data-engineer.md` (Round 2). Also list the case-insensitive `data_type` match as a deviation there, or make the match exact; either is acceptable (note 3).
2. **synthetic-tester — tests for fix 1.** (a) On a spec-conformant synthetic tree (the P00 writers), the CSV with `--strict` is byte-identical to the CSV without it, and both exit 0. (b) A file with `comments 1` and no `comment_1` line (and, as a second case, `bands 1` without `band_1`): `--strict` exits 1 with an `unreadable:` deviation naming the list, while the run without the flag exits 0. Case (b) must fail on a variant that parses `--strict` but does not pass it to the parser.
3. **orchestrator — `02_plan.md` "Run commands" and "Acceptance checks".** Add the strict pass. The runner then runs exactly:
   ```bash
   sha256sum reports/raw_inventory.csv
   .venv/bin/python scripts/exploration/inventory_raw.py --out reports/P01/raw_inventory_parser.csv
   cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser.csv
   .venv/bin/python scripts/exploration/inventory_raw.py --strict --out reports/P01/raw_inventory_parser_strict.csv
   cmp reports/raw_inventory.csv reports/P01/raw_inventory_parser_strict.csv
   sha256sum reports/raw_inventory.csv
   ```
   Expected: both runs print `10 files, 5 subjects, 0 deviations` and exit 0; both `cmp` are silent; the sha256 is unchanged (`e134a372…6c14`). Each run is logged to `reports/logs/P01/inventory_raw_<timestamp>.log`. Before the run, write this pre-recorded decision: if the strict pass fails on a real file, the runner stops. The orchestrator then opens a blocker that records the header fact for `mas/01_DATA_SPEC.md` §2. Nobody edits `_check_consistency` (`src/io/ebr_parser.py:177-187`) just to make the run pass.
4. **orchestrator — privacy row; `mas/state/phases/P01-ebr-parser/00_assignment.md:6`.** Replace the reference to the local agent-instructions file with a committed source for the same fact: `mas/01_DATA_SPEC.md` §2 (the montage) and `mas/02_REQUIREMENTS.md` §3 v1 (the exclusion). Commit with a `docs:` prefix. After the fix, a case-insensitive `git grep` over HEAD, with the pattern assembled from fragments, must return nothing.

### Non-blocking notes

1. Order of checks: strict consistency runs before the truncation check (`src/io/ebr_parser.py:211-216`). A truncated file with a bad header therefore reports the header error first. Both errors are loud, so this is fine.
2. Tester observation 1: the defaults `trials = bands = 1` and `comments = marks = 0` (`src/io/ebr_parser.py:115-124`) are the builder's own and are not documented. Add one docstring line.
3. `data_type` match (`src/io/ebr_parser.py:54`): `.strip().lower()` accepts `DOUBLE`, but §2 says any other string raises. It is harmless on the delivered files (`double`), but it is an undeclared deviation; see fix 1.
4. A duplicated `channel_k` line overwrites the earlier one silently (`src/io/ebr_parser.py:84`), and the strict index check does not see it. Not plausible in the delivered data. Strict mode could flag it later; not required now.
5. The 10 Hz zero-phase test is weak against a causal filter. The tester replaced it with a broadband check, which is correct (`tests/test_p01_filters_known_answer.py:58-73`).

## Pre-run audit — Round 2

Verdict: PASS

Audited commit: dd8b3f0. Round 2 commits: 21f9d87, b7bc198, 73498f5, ba39d8b, 3752d34, 42b56fa, e419ea7, 97e46b5, dd8b3f0.
Suite re-run by the reviewer: `.venv/bin/python -m pytest tests/ -p no:cacheprovider` → `248 passed in 4.71s`. `git diff --stat main -- tests/test_p00_*.py` is empty, so the P00 tests are unchanged.

| Round 1 fix | Result | Evidence (`path:line` / command) |
|---|---|---|
| 1 data-engineer: `--strict` flag | PASS | `scripts/exploration/inventory_raw.py`: `--strict` uses `store_true` (default off) and is passed through `run_inventory(..., strict=args.strict)` → `inventory_file(path, subject, strict=strict)` → `load_ebr_file(path, strict=strict)`. A strict `ValueError` lands in the existing `unreadable:` branch. Without the flag the call is `strict=False`, identical to Round 1. Round 2 is recorded in `03_changes_data-engineer.md`. Exact `data_type` match (`src/io/ebr_parser.py` `ebr_dtype`, no `strip`/`lower`) now follows §2 ("any other value raises") |
| 2 synthetic-tester: tests (a), (b), mutation | PASS | `tests/test_p01_strict_known_answer.py:60-84`: (a) byte-identical CSVs, both exit 0, in process and as a subprocess. `:92-109`, `:128-138`: (b) a missing `comment_1` or `band_1` line exits 0 without the flag, and exits 1 with it, giving an `unreadable:` deviation that names the list; a clean second file stays clean. `:112-125`: the flag-not-forwarded variant exits 0 with no deviation, so (b) fails on it. Exact dtype `:143-172`. Repeated lines `:187-217`, with a no-repeat control |
| 3 orchestrator: run commands and pre-recorded decision | PASS | `02_plan.md` "Amendment — pre-run audit Round 1" holds the six commands of fix 3 verbatim, the expected output and the added acceptance check. `mas/state/decisions.md`, new P01 row: a strict failure means stop and open a blocker, and the checks are never relaxed. The current `sha256sum reports/raw_inventory.csv` is `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14`, which matches the amendment |
| 4 orchestrator: privacy | PASS | `00_assignment.md:6` now cites `mas/02_REQUIREMENTS.md` §3 v1 and `mas/01_DATA_SPEC.md` §2. A case-insensitive `git grep -c` over HEAD with the fragment-built vendor/co-author pattern finds no hit. `git log main..HEAD` messages and authors: 0 hits. `git ls-files` (104 files) has nothing data-like or local-tooling. Working tree clean. `mas/state/scratch/reference_access.log` is unchanged (1 line, P00) |

Rows of the Round 1 table not listed above are unchanged: R6, PF-04/05/06, R9–R11 PASS; golden rule 3 LEGACY (by design); the rest N/A.

### Non-blocking notes (Round 2)

1. CONCERN, strict repeated-line check (`src/io/ebr_parser.py` `_parse_header_lines`, `duplicates`). The check covers every key, unknown keys included. §2 says unknown keys are ignored, so a real header that repeats an unknown key would follow the spec but still fail strict mode. The failure is loud. It would show up in this run's strict pass, and the pre-recorded decision then stops the phase. Nothing can come out wrong silently, so this is not a FAIL. If it happens, the blocker should consider limiting the repeat check to the §2 keys, rather than accepting a weaker check by default.
2. Exact `data_type` matching also applies in non-strict mode, so it changes the default inventory: a `Double` header is now `unreadable:` (`tests/test_p01_strict_known_answer.py:167-172`). §2 says every delivered file has `data_type double`, so the default run should be unaffected. If it is affected, the default `cmp` fails loudly, and the runner should treat that like a strict failure (stop, blocker).
3. Test (b) checks the list name with a substring match on the message (`:108`). Together with the mutation test this is enough.

## Results review

Verdict: APPROVE

Read: `05_run.md` (48745f3), `06_verify.md` (ad5b51f, PASS), `reports/logs/P01/inventory_raw_default_20261024T162513.log`, `reports/logs/P01/inventory_raw_strict_20261024T162517.log`, `reports/P01/raw_inventory_parser.csv`, `reports/P01/raw_inventory_parser_strict.csv`, `reports/raw_inventory.csv` (P00).
The run used HEAD 4775509 (both logs: `# HEAD: 477550967a7d04aab2ceb217d47c59735c992dd0`). `git diff --stat 4775509..HEAD -- src scripts tests configs Makefile` is empty, so the audited code is the code that ran.

### Deviations from references

The reference is the P00 inventory, `reports/raw_inventory.csv` (log `reports/logs/P00/inventory_raw_20261024_141334.log`), read with B005 option B: "all 23 files" means the 10 delivered files (OO, mOO of S01–S05). P01 has no R-x target.

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| P00 CSV, default mode | byte-identical; `10 files, 5 subjects, 0 deviations`, exit 0 | `10 files, 5 subjects, 0 deviations`, `# exit: 0` (default log); `cmp` silent, exit 0 (re-run by the reviewer: `cmp1 0`) | none | yes (exact) | — | yes |
| P00 CSV, `--strict` | same | same summary and exit (strict log); `cmp` silent (`cmp2 0`) | none | yes (exact) | — | yes |
| sha256 | `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14` for all three CSVs | `sha256sum reports/raw_inventory.csv reports/P01/*.csv` → the same value 3 times (reviewer re-run) | none | yes | the P00 file was not overwritten | yes |
| Clean-checkout reproduction | same | `06_verify.md` §2: both modes reproduced from a worktree at 8d29fd7, `cmp` identical | none | yes | — | yes |
| Config v1 | equals `mas/02_REQUIREMENTS.md` §3 | `06_verify.md` §3 `equal: True`; text-equality test `tests/test_p01_config_known_answer.py:83` passes | none | yes | — | yes |
| 13 absent §4 rows (C, mC, online_*, cb_mas_mcb) | not parsed | absent from the delivered data | — | — | B005 option B (Sebastian, 2026-10-24) | yes (B005) |

### Interpretation check

- **Per file.** Each of the 10 rows matches its `mas/01_DATA_SPEC.md` §4 row in samples, duration, stimulus events, session start and p99. Examples: S01 OO 154904 / 785.1, S03 mOO 154896 / 1013.8, S05 mOO 154904 / 23.8. Every duration rounds to 605.1 s at fs 256 (`python -c "print(154904/256, 154912/256, 154896/256)"` → `605.09375 605.125 605.0625`).
- **The full-precision p99 is identical too** (e.g. `785.129522094725`). That matters: the parser path (full read, cast to float64) gives the same numbers, digit for digit, as P00's memmap path, so the reader switch changed no value.
- **Acceptance.** Both are met: "parsing all files gives the inventory of P00" (applied to the 10 delivered files, B005) and "tests pass" (`248 passed`, reviewer and verifier).
- **Round 2 concern 1, repeated-line check on unknown keys.** Settled for the delivered data. The strict pass gave 0 deviations on all 10 files, so no delivered header repeats any key, known or unknown. The `_1..n` numbering of channel, band, trial, comment and mark lines is also as declared, and the magic and block size are as §2 states. The concern remains for files not yet delivered (C, mC, online_*, cb_mas_mcb, a future cohort): §2 says unknown keys are ignored, but strict mode rejects a repeated one. That would fail loudly, and the decisions.md row (stop, blocker, never relax) covers it. Accepted as a deviation below.
- **Round 2 concern 2, exact `data_type` in default mode.** Settled. The default run read all 10 files without an `unreadable:` deviation, so every delivered header uses a table string exactly. §2 says that string is `double`.
- **Leakage and statistics.** N/A: nothing is fitted, normalized or tested statistically in P01.
- **Legacy.** PF-05 (PO7 excluded in config v1) stays labelled and reachable through git `p01-done`. The parser returns all 11 channels.

### Decisions for decisions.md

1. P01 · `load_ebr_file(path, strict=True)`: strict is the default. Beyond §2 it raises on a magic that is not `ebr binary 1.0`, on a channel/band/trial/comment/mark list not numbered `_1..n` as declared, on any repeated header line (unknown keys included), and on bytes after the declared block. `strict=False` is the raw inventory's tolerant path. Builder's own; it passed on all 10 delivered files (`reports/logs/P01/inventory_raw_strict_20261024T162517.log`). The repeat check on unknown keys goes beyond §2 ("unknown keys are ignored"). If a future file trips it, the decisions.md stop/blocker row applies. (`03_changes_data-engineer.md` deviation 1 and Round 2; `07_review.md` results review)
2. P01 · Extra public names in `src/io/ebr_parser.py`: `read_ebr_header`, `open_ebr_block`, `block_shape`, `trailing_bytes`, `ebr_dtype`, `EBR_DTYPES`, `EBR_MAGIC`, `RECORDING_KEYS`. They are needed by the P00 inventory names; the 14-key `load_ebr_file` contract is unchanged. (`03_changes_data-engineer.md` deviation 2)
3. P01 · Helper strictness: `select_scalp_channels` raises on repeated or ambiguous names; `get_mark_channel_index` raises on a duplicated MARK; `extract_scalp_signal` raises for complex data, `nt != 1` or `nb != 1`, and a name/channel count mismatch. (`03_changes_data-engineer.md` deviation 3)
4. P01 · `data_type` is matched exactly, case- and space-sensitive, in both modes, per §2 "any other value raises `ValueError`". All 10 delivered files pass. (`03_changes_data-engineer.md` Round 2, 73498f5)
5. P01 · Header count defaults when a line is missing: `trials = bands = 1`, `comments = marks = 0` (builder's own, documented in `read_ebr_header`). Strict mode rejects a file that relies on them. (`04_tests.md` observation 1; `07_review.md` Round 1 judgement 2)
6. P01 · The inventory reads whole files through `load_ebr_file` instead of three memmapped channels; output is byte-identical to P00. `--raw-dir` defaults to config `paths.data_raw_dir`. The new `--strict` flag (default off) reads in strict mode. (`03_changes_data-engineer.md` deviations 4–5, Round 2)
7. P01 · Plan amendment (pre-run audit Round 1): the run adds a `--strict` inventory pass and an sha256 check before and after. Acceptance is "both default and `--strict` inventories byte-identical to the P00 CSV" over the 10 delivered files (B005). (`02_plan.md` Amendment, 21f9d87)

## Sources spot-check

- `mas/01_DATA_SPEC.md` §2 and §4, opened in this run. The dtype table, the "unknown keys are ignored" and "any other value raises" rules, and the per-file §4 numbers above were checked against it.
- `mas/02_REQUIREMENTS.md` §3, opened in Round 1. Config v1 text; the verifier's equality output agrees.
- `mas/state/blockers/B005-inventory-10-of-23-files.md`, opened in Round 1 ("2026-10-24: option B").
- The logs and CSVs listed under "Read" above, opened in this run. The `cmp` and `sha256sum` results were re-run by the reviewer with the commands shown.
- Privacy: a case-insensitive `git grep -c` over HEAD with the fragment-built vendor/co-author pattern gives no hits, and `git log 4775509..HEAD` messages give 0.

## Questions
