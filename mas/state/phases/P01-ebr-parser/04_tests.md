# P01 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 00_assignment.md, 02_plan.md, 03_changes_data-engineer.md, mas/RULES.md, mas/01_DATA_SPEC.md §2–§3, mas/02_REQUIREMENTS.md §3, §4, §7, mas/05_PITFALLS.md PF-04/05/06 (as named in 00_assignment.md)
Branch: phase/P01-ebr-parser @ 8227957 (builder handoff); tests committed in 6ad6175

## Tests added

All inputs are built inside the tests (tmp_path files, fixed seeds). No real data is read.
The EBR writer in `tests/test_p01_ebr_known_answer.py` uses its own 20-row dtype table typed from [1] §2 and packs the block with `struct`, so it does not rely on the parser's `EBR_DTYPES` or on a numpy reshape. Gains are measured at fs 256 Hz, the header rate [1] §2.

NEW `tests/test_p01_ebr_known_answer.py` (58 cases), NEW `tests/test_p01_config_known_answer.py` (33 cases), NEW `tests/test_p01_filters_known_answer.py` (15 cases).

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_p01_ebr_known_answer.py::test_roundtrip_keys_shape_values` | nt=1, nc=11 (montage), nb=1, ns=1000 doubles, `x[c,t]=1000c+t`, 2 comments, 2 marks | exactly the 14 keys; shape (1,11,1,1000) float64; `data[0,c,0,t]==1000c+t`; channels, fs 256.0 (float), counts, bands, trials, comments, marks equal what was written | exact | [1] §2 | wrong key set, channel/sample mix-up | PASS |
| `…::test_roundtrip_fractional_fs` | `sampling_rate 250.5` | 250.5 | exact | [1] §2 (fs is a float) | int-cast fs | PASS |
| `…::test_layout_nt_nb_gt_1` | (2,3,2,5) C-order block, value `1000t+100c+10b+s` | `data[t,c,b,s]` == its code for all 60 elements | exact | [1] §2, R6 | wrong reshape order | PASS |
| `…::test_layout_check_rejects_wrong_reshape[fortran / ns_nc / nc_ns_bands_last]` | same file read with `order="F"`, as `(nt,nb,ns,nc)`→transpose, and bands-fastest | the R6 assertion **fails** on each variant | — | mutation check | Fortran, `(ns,nc)`, band/sample swap | PASS (3) |
| `…::test_layout_buggy_parser_monkeypatched` | parser with its `np.fromfile` result monkeypatched to reshape in Fortran order | the R6 assertion fails on the parser's output | — | mutation check | Fortran reshape inside `load_ebr_file` | PASS |
| `…::test_dtype_table[<20 strings>]` | one file per data_type string, 5 values at the type's limits (e.g. int8 −128/127, uint32 2^32−1, int64 ±2^53, float32-exact values, complex with nonzero imaginary parts) | on-disk block = n × width bytes; parsed dtype float64 (real) / complex128 (both complex strings); values identical | exact | [1] §2 | wrong width, signedness, lost imaginary part, cast of complex | PASS (20) |
| `…::test_dtype_table_has_exactly_20_strings` | — | 20 strings; `ebr_dtype(s).itemsize` = spec width | exact | [1] §2 | missing alias | PASS |
| `…::test_little_endian_bytes` | int16 513 written as bytes `01 02` | 513 (big-endian would give 258) | exact | [1] §2 | wrong endianness | PASS |
| `…::test_unsupported_dtype_raises[bogus, float16, long double, complex64 × strict True/False]` | data_type outside the table | `ValueError` in both modes | — | [1] §2 | silent fallback to double | PASS (8) |
| `…::test_truncated_block_raises[cut 8, 88, 3 bytes × strict True/False]` | ns=1000 declared, nc=11; one double short, one full sample (999 samples) short, partial element | `ValueError` matching `truncat`, both modes | — | [own], plan | silent short read; unhelpful reshape error | PASS (6) |
| `…::test_truncated_plain_fromfile_variant_is_not_caught` | the plain `np.fromfile(...).reshape(...)` reader | raises a reshape `ValueError` with no "truncat" in the message (so the match above tells it apart); a whole-file read returns 10999 elements silently | — | mutation check | plain-fromfile reader | PASS |
| `…::test_header_rules` | blank lines (incl. between marks), unknown keys `operator`, `weird_key`, magic `"  EBR Binary 1.0  "`, `marks 2` with `mark_1 10 stim on`, `mark_2 300 201` | parses; marks `[(10,"stim on"),(300,"201")]`; lists and data exact | exact | [1] §2 | strict magic compare, unknown-key error | PASS |
| `…::test_marks_zero_is_empty_list` | `marks 0` | 0, `[]` | exact | [1] §2 | — | PASS |
| `…::test_binary_starts_right_after_end_header` | uint8 block starting with bytes 0x0A 0x0A 0x31 0x0D | `[10,10,49,13]` | exact | [1] §2 | blank-line skipping eating binary bytes | PASS |
| `…::test_strict_wrong_magic` | magic `ebr binary 2.0` | strict: `ValueError`; non-strict: data parsed | exact | 03_changes deviation 1 | — | PASS |
| `…::test_strict_trailing_bytes` | 8 extra bytes | strict: `ValueError`; non-strict: declared block | exact | 03_changes deviation 1 | — | PASS |
| `…::test_strict_channel_name_count` | `channels 3`, two `channel_k` lines | strict: `ValueError`; non-strict: shape (1,3,1,2), 2 names, data exact | exact | 03_changes deviation 1 | — | PASS |
| `…::test_strict_well_formed_file_passes` | spec-conformant file | both modes give identical dicts | exact | [own] | — | PASS |
| `…::test_select_scalp_channels_shuffled` | montage shuffled (seed 0); v1 scalp names; `["O2","PO7"]` | indices in `scalp_names` order by name; `[7,0]` | exact | plan, PF-06 | positional selection | PASS |
| `…::test_select_scalp_channels_missing_name` | PO7 requested, absent | `ValueError` | — | plan | — | PASS |
| `…::test_get_mark_channel_index` | montage; MARK first; MARK absent; `mark_name="TIMESTAMP"` | 10; 0; −1; 8 | exact | plan | hardcoded index 10 | PASS |
| `…::test_resolve_recording_path` | tmp tree `S03/mOO.ebr` | `raw_root/S03/mOO.ebr` for `"mOO.ebr"` and bare `"mOO"`; `FileNotFoundError` naming `OO.ebr`; absent session → `FileNotFoundError` | exact | plan, [5] | — | PASS |
| `…::test_extract_scalp_signal_config_v1[False / True]` | 11-channel file (montage order, then shuffled with seed 1); channel X planted as `1000·montage_index(X)+t`; v1 `scalp` read from `configs/pipeline_config.yaml` | shape (7,T) float64, names = v1 list, no PO7, row r = planted signal of `scalp[r]` | exact | [3] §3, [1] §2 | positional selection, PO7 leak | PASS (2) |
| `…::test_parser_returns_all_channels_po7_included` | 11-channel file | PO7 at index 0, 11 data channels | exact | PF-05, plan | exclusion leaking into the parser | PASS |
| `test_p01_config_known_answer.py::test_hand_typed_matches_spec_block` | v1 YAML block regex-extracted from `mas/02_REQUIREMENTS.md` §3 | equals the hand-typed dict (guards the test itself) | exact | [3] §3 | — | PASS |
| `…::test_config_v1_key_by_key[<30 leaves>]` | committed config | each leaf equals [3] §3, same Python type (float vs int), list element types too | exact | [3] §3 | `1` vs `1.0`, a changed value | PASS (30) |
| `…::test_config_v1_no_extra_keys` | committed config | leaf set equal; whole dict equal | exact | [3] §3 | P07/P16 keys early | PASS |
| `…::test_config_v1_text_equals_spec_block` | committed file text | equals the spec block line by line (trailing whitespace ignored) | exact | [3] §3 ("verbatim") | lost comment, reformatting | PASS |
| `…::test_config_v1_po7_legacy_label` | committed file | `scalp:` line holds `# PO7 hard-excluded (legacy)`; 7 scalp names, no PO7; scalp ∪ excluded = 8-channel montage | exact | [3] §3, PF-05 | unlabelled legacy | PASS |
| `test_p01_filters_known_answer.py::test_bandpass_gain[10, 24, 0.2, 100 Hz]` | unit sinusoids, fs 256, 10 s; RMS ratio over central 5 s | 10, 24 Hz in [0.98, 1.02]; 0.2, 100 Hz < 0.05 (measured: 1.0, 0.99994, 2e-05, 0.00021) | ±0.02 / < 0.05 | [own] Butterworth \|H\|² | no-op filter, wrong band, fs mix-up | PASS (4) |
| `…::test_zero_phase_lag_sinusoid[10, 24 Hz]` | sinusoid | cross-correlation peak at lag 0 | 0 samples | [4] | — | PASS (2) |
| `…::test_zero_phase_lag_broadband` | white noise (seed 0) | peak at lag 0 | 0 samples | [4] (symmetric effective response) | causal filter | PASS |
| `…::test_zero_phase_check_rejects_causal_variant` | `lfilter` with the same b, a | peak at a nonzero lag (2 samples) | — | mutation check | one-pass causal filtering | PASS |
| `…::test_filter_axis_last` | (2,3,1024) noise | each row equals filtering that row alone; shape kept, float64 | 1e-12 | [2] P01.3, [4] axis=−1 | wrong axis | PASS |
| `…::test_filter_axis_check_rejects_flattened_variant` | filtfilt on the flattened array | differs from the parser output by > 1e-3 | — | mutation check | flattening across rows | PASS |
| `…::test_filter_equals_roadmap_formula` | (8,2560) noise × 50 | equals `filtfilt(*iirfilter(4,[1/128,60/128],btype="bandpass",ftype="butter"),x)` | 1e-12 | [2] P01.3 | any formula drift | PASS |
| `…::test_filter_formula_nondefault_arguments` | fs 512, (5, 40, order 2) | equals the formula with `[5/256, 40/256]`, order 2 | 1e-12 | [2] P01.3 | ignored keyword arguments | PASS |
| `…::test_fs_is_required_and_used` | signature; call without fs; outputs at fs 256 vs 250 | no default; `TypeError`; outputs differ by > 1e-6 | — | PF-04 | `fs=250` default | PASS |
| `…::test_defaults_are_roadmap_defaults` | signature | lowcut 1.0, highcut 60.0, order 4 | exact | [2] P01.3 | — | PASS |
| `…::test_input_not_modified` | (3,1024) noise | input unchanged | exact | [3] §4 (no side effects) | in-place filtering | PASS |
| P00 regression: `tests/test_p00_inventory_known_answer.py`, `tests/test_p00_inventory_smoke.py` | unchanged P00 suite | all pass | — | P00 | inventory regression after the reader switch | PASS (61 + 2) |

How the mutation checks work: each "mutation check" row runs the test's own assertion on the buggy variant, built inside the test file (a reshape variant, or a monkeypatch of `ep.np.fromfile` restored with `monkeypatch.undo()`, or an `lfilter`/flattened filtering variant). It then asserts that the assertion fails. No PF entry belongs to P01 (plan). The plan requires that the layout test fails on a Fortran-order or `(ns, nc)` reshape, and that the truncation test fails on a plain `np.fromfile(...).reshape(...)` reader. Both are shown by these rows.

## Command

```bash
.venv/bin/python -m pytest tests/
```

## Output summary

Verbatim summary line of the full suite: `198 passed in 3.94s` (tests: 63 P00 + 29 builder smoke + 106 new).
Per file, verbatim: `33 passed in 0.08s` (config), `58 passed in 0.17s` (ebr), `15 passed in 0.65s` (filters), `61 passed in 2.53s` (P00 known-answer), `2 passed in 0.21s` (P00 smoke).
`git diff --stat main -- tests/test_p00_*.py` is empty, so the P00 tests are unchanged.
No failures.

The first attempt of the test files had 2 failures. Both were mistakes in my tests, not in the builder's code:
1. `test_binary_starts_right_after_end_header` used a hand-made header without `bands`/`trials` lines. Strict mode rejected it (see observation 1), so the test now uses the full writer.
2. The first version of the causal-variant check used a 10 Hz sinusoid. There the causal phase is only −5.6° (0.39 samples), so lag 0 was found even for `lfilter`. Measured with `freqz(b, a, worN=[10,24,40], fs=256)`: phase −5.55°, −45.24°, −91.03°. The zero-phase claim is therefore also tested on broadband noise, and the mutation check uses that.

## Bugs found

None blocking. Observations for the builder (no change required by the spec):

1. With no `bands` (or `trials`) line, the parser defaults the count to 1. `strict=True` then raises "declares 1 band(s) but has band_k lines for k = []". A header that omits both lines is therefore rejected in strict mode, but accepted with an empty `bands` list when `strict=False`. Every header in [1] §2 has these lines, so this does not affect the delivered data. If the default exists to tolerate such headers, strict mode contradicts it.
2. The plan's 10 Hz zero-phase test is weak against a causal filter because 10 Hz is close to the band's geometric centre (√60 ≈ 7.7 Hz). The broadband test covers this.

## Coverage gaps

- Every row of the plan's table is covered. No tolerance was loosened.
- Not tested: the `data_type` string is matched case-insensitively (builder choice; the spec does not say), the header-size cap (`_MAX_HEADER_BYTES`), negative-count errors, a missing `end_header` / missing required key, `select_scalp_channels` duplicate-name errors and the `extract_scalp_signal` complex / nt>1 / nb>1 errors (03_changes deviation 3). The builder's smoke tests cover some of these. None is a spec requirement.
- The inventory switch (`scripts/exploration/inventory_raw.py`) on real data is the runner's `cmp` acceptance check. On synthetic data it is covered only by the unchanged P00 suite.

## Reference consultations (R11)

None. `reference/` was not opened.

## Sources

1. RULE — `mas/01_DATA_SPEC.md` §2–§3 (opened in this run). Used for: header format, dtype table and widths, little-endian, `(nt, nc, nb, ns)` C order, cast rules, the 14 keys, magic rule, montage order.
2. RULE — `mas/03_ROADMAP.md` P01 tasks, as quoted verbatim in `00_assignment.md` (opened in this run). Used for: the filter formula, the defaults and the helper signatures.
3. RULE — `mas/02_REQUIREMENTS.md` §3, §4, §7 (opened in this run). Used for: config v1 (extracted by the test itself), no side effects, the EBR round-trip requirement.
4. DOCS — SciPy 1.18.1, `scipy.signal.filtfilt` and `scipy.signal.iirfilter` docstrings (read through the installed package in this run). Used for: zero phase and doubled order of the forward-backward pass, default `axis=-1`, `Wn` normalized to Nyquist.
5. RULE — `mas/state/decisions.md`, P01 row on `resolve_recording_path` (opened in this run). Used for: `session` = subject folder, a bare stem gets `.ebr`.
6. RULE — `mas/state/phases/P01-ebr-parser/02_plan.md` "Tests required" and helper semantics; `03_changes_data-engineer.md` deviations 1–3 (opened in this run). Used for: the test specification and the strict/non-strict behaviour.

## Questions

ACK 03_changes_data-engineer.md synthetic-tester 2026-10-24

## Round 2 — tests for 07_review.md required fix 2

Status: READY
Reads: 07_review.md (Round 1, required fix 2), 03_changes_data-engineer.md "Round 2" (commits b7bc198, 73498f5, ba39d8b, 3752d34)
Tests committed in 42b56fa. NEW `tests/test_p01_strict_known_answer.py` (47 cases).

Synthetic trees are written into tmp_path with the P00 known-answer writers (`write_ebr`, `recording`: 11-channel calibration runs, 154904 samples, 40 trials, the protocol of [1] §3). A list line is removed by editing header bytes before `end_header` only. No real data is read.

| Test id | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_p01_strict_known_answer.py::test_strict_flag_clean_tree_byte_identical` | spec-conformant tree S01/OO, S01/mOO, S02/OO; `main()` with and without `--strict` | both exit 0, 3 rows, no deviations, the two CSVs byte-identical | exact | 07_review fix 2a | strict mode changing rows on good files | PASS |
| `…::test_strict_flag_clean_tree_subprocess` | the same through the command line (script run as a file) | both exit 0, CSVs byte-identical | exact | fix 2a | flag wiring only via `main()` | PASS |
| `…::test_strict_flag_missing_list_line[comment, band]` | S01/OO with `comments 1` but no `comment_1` (and, separately, `bands 1` but no `band_1`), next to a clean S02/OO | without the flag: exit 0, no deviation. With `--strict`: exit 1, S01/OO deviation starts with `unreadable:` and names the list, S02/OO clean | exact | fix 2b, [7] Round 2 | flag not reaching the parser | PASS (2) |
| `…::test_strict_flag_dropped_variant_is_caught[comment, band]` | `inventory_file` monkeypatched to ignore its `strict` argument, so the flag is parsed but never passed | `--strict` exits 0 with no deviation, so the fix-2b assertions fail on it (checked with `pytest.raises(AssertionError)`) | — | mutation check | flag parsed but not passed | PASS (2) |
| `…::test_strict_flag_missing_comment_subprocess` | missing `comment_1`, through the command line | exit 0 without the flag; exit 1 with `--strict`, stdout has `DEVIATION S01/OO: unreadable:` | exact | fix 2b | — | PASS |
| `…::test_ebr_dtype_accepts_every_spec_string[<20>]` | the 20 strings of [1] §2, written exactly | accepted | exact | [1] §2 | over-tight matching | PASS (20) |
| `…::test_ebr_dtype_exact_match[<9>]` | `Double`, `DOUBLE`, ` double`, `double `, `Float`, `INT`, `unsigned  int` (2 spaces), `Complex`, `class std::complex<Double>` | `ValueError` | — | [1] §2 "any other value raises" | case/space-insensitive matching | PASS (9) |
| `…::test_file_with_case_variant_dtype_raises[Double, DOUBLE, unsigned  int × strict True/False]` | file header with that data_type | `ValueError` in both modes | — | [1] §2 | — | PASS (6) |
| `…::test_inventory_case_variant_dtype_is_unreadable` | S01/OO with `data_type Double`, no flag | exit 1, `unreadable:` deviation | exact | [1] §2, [7] | — | PASS |
| `…::test_repeated_channel_line[channel_2 C, channel_02 C]` | `channel_2` given twice (also as `channel_02`, same index) | strict: `ValueError`; non-strict: channels `['A','C']` (last value kept), data exact | exact | [own], 07_review note 4, [7] | silent overwrite in strict mode | PASS (2) |
| `…::test_repeated_scalar_line` | `samples 2` then `samples 3`, 3-sample block | strict: `ValueError`; non-strict: ns 3, data `[[0,1,2],[10,11,12]]` | exact | [own], [7] | — | PASS |
| `…::test_no_repeat_parses_in_strict` | the same header without the repeat | parses in strict mode | exact | control | over-eager duplicate check | PASS |

**Round 1 tests and exact matching.** No Round 1 test relied on case-insensitive `data_type` matching. `SPEC_DTYPES` and `DTYPE_VALUES` use the exact strings of [1] §2, and the bogus cases (`bogus`, `float16`, `long double`, `complex64`) are outside the table under either rule. The only case-insensitive check in Round 1 is the magic (`test_header_rules`), which [1] §2 requires ("compare case-insensitively after strip"). So no Round 1 test was changed. The Round 1 coverage gap "data_type case-insensitive, untested" is now closed in the exact direction.

**Note on whitespace.** Whitespace around a `data_type` *value* can't reach `ebr_dtype` from a file: the header line is stripped, and `split(maxsplit=1)` drops the spaces after the key. The ` double` / `double ` cases are therefore tested on `ebr_dtype` directly. A doubled inner space (`unsigned  int`) survives parsing and is tested in a file too.

**Command and output** (verbatim summary line, `.venv/bin/python -m pytest tests/ -v`):

`============================= 248 passed in 4.92s ==============================`

248 = 201 tests after the builder's Round 2 + 47 new. P00 tests unchanged. No failures; no test needed fixing in this round.

**Bugs found.** None.

**Reference consultations (R11).** None.

**Sources (additional).** 7. RULE — `mas/state/phases/P01-ebr-parser/07_review.md` (Round 1, required fix 2, note 4) and the Round 2 section of `03_changes_data-engineer.md` (opened in this run). Used for: the fix-2 specification, the `--strict` wiring and the repeated-line rule. [1] §2 is as above.
