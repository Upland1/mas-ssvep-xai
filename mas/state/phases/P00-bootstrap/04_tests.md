# P00 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_data-engineer.md, mas/RULES.md, mas/01_DATA_SPEC.md §1–§4, mas/02_REQUIREMENTS.md §7 (via plan), mas/05_PITFALLS.md (PF-09, PF-13 named in 00_assignment.md; no PF entry applies to a known-answer bug in P00)
Branch: phase/P00-bootstrap
Commit: 9d39ec9 (`test: add known-answer tests for the raw inventory script (P00)`), code under test at 110e90c

## Tests added

All in NEW `tests/test_p00_inventory_known_answer.py`. Inputs are synthetic EBR files written in `tmp_path` by an EBR writer in the test module, which uses its own dtype table copied from [1] §2, not the script's. fs 256 (the value being checked). Calibration MARK: 40 trials, 8 per target (seeded shuffle), timing of [1] §3 (201 at t, 202 t+2, 203 t+4, 10x t+5, 200 t+10, first 201 at 5.0 s, trials every 15 s). No real data read.

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `::test_clean_calibration_run` | `S01/OO.ebr`, ns 154,904, single-sample pulses | 13 CSV columns in plan order; samples 154904, duration 605.1, stim 40, counts `101–105:8; 200–203:40`, channels = the 11 names, kind calibration, no deviation, exit 0 | exact | [1] §2–§4, [2] | wrong column order, wrong count | PASS |
| `::test_all_calibration_stems_are_checked[OO,mOO,C,mC]` | each stem with one 101 pulse missing | kind calibration, deviation, exit 1 | exact | [1] §3 | stem not classified as calibration | PASS (4) |
| `::test_plateau_pulses_count_once` | same run, every pulse 3 samples long | counts identical to single-sample run, stim 40, exit 0 | exact | [1] §3 onset rule, [2] Tests | naive counter | PASS |
| `::test_plateau_test_fails_on_naive_counter` | plateau file with `event_onset_counts` monkeypatched to `(mark == code).sum()` | stim 120, `201:120`, non-empty deviations, i.e. the plateau test fails on the naive variant | exact (3 × 40) | analytic | naive `(mark == code).sum()` (proven) | PASS |
| `::test_onset_rule_on_small_arrays` | `[0,5,5,5,0,5,0]`, `[7,7,8,8,0]`, pulse at sample 0, all zeros | `{5:2}`, `{7:1, 8:1}`, `{201:1}`, `{}` | exact | [1] §3 (`diff(mark, prepend=0)`) | back-to-back codes merged; first sample missed | PASS |
| `::test_wrong_fs_is_deviation_and_csv_written` | S01 clean + S02 `sampling_rate 250` | exit 1; CSV has both rows; S01 clean, S02 deviation names fs 250 | exact | [3] P00.2 | deviation only printed / CSV not written | PASS |
| `::test_renamed_channel_is_deviation` | channel 1 `Fp1` | channel-list deviation, exit 1, CSV written | exact | [1] §2, [3] | — | PASS |
| `::test_ten_channels_is_deviation` | FLASHINGTIME removed (10 consistent channels) | n_channels 10, channel deviation, MARK still found by name (counts 40/8), exit 1 | exact | [1] §2 | MARK read by fixed index | PASS |
| `::test_missing_trial_is_deviation` | 7 pulses of 103 | `103:7`, stim 39, `code 103` deviation, exit 1 | exact | [1] §3 | — | PASS |
| `::test_unexpected_code_in_calibration_is_deviation` | extra 1001 pulse in a calibration run | deviation naming 1001, exit 1 | exact | [1] §3 | extra codes ignored | PASS |
| `::test_cli_exit_codes_as_subprocess` | script run as file, clean tree / fs 250 tree | return code 0 / 1, CSV written both times | exact | [3] P00.2 | `main()` value not passed to `sys.exit` | PASS |
| `::test_online_run` | `S05/online_OO.ebr`, ns 16,728, 7 pulses in 1001–1005 | kind online, stim 7, duration 65.3, counts `1001:2;1002:1;1003:2;1004:1;1005:1`, exit 0 | exact | [1] §3, §4 | — | PASS |
| `::test_online_run_with_cue_code_is_deviation` | online run with a 202 pulse | deviation naming 202, exit 1 | exact | [1] §3 | — | PASS |
| `::test_joined_run` | `S03/cb_mas_mcb.ebr`, two calibration runs, ns 309,816 | kind joined, stim 80, duration 1210.2, exit 0 | exact | [1] §4 | — | PASS |
| `::test_duration_to_0p1_s[...]` | kind-unknown files with each §4 sample count | 154896/154904/154912 → 605.1, 154920 → 605.2, 30088 → 117.5, 16728 → 65.3 | exact at 0.1 s | [1] §4; arithmetic below | truncation instead of rounding (154920) | PASS (6) |
| `::test_discovery` | folders S01, S2, S10, S1x, notes, s03 (each with a valid OO.ebr), empty S04, stray file `S99.ebr`; `S01/photo.jpg`, `video.mp4`, `notes.txt` | rows `(S01,OO), (S2,OO), (S10,OO)` in numeric order; `Skipping S04` printed; exit 0 | exact | [1] §1 | glob `S*`, case-insensitive match, lexical order | PASS |
| `::test_subjects_flag_and_empty_tree` | `--subjects S02`; raw dir with only an empty S01; missing raw dir | only S02; exit 1; exit 1 | exact | [2] CLI; [4] deviation 4 | empty inventory passing | PASS |
| `::test_session_start` | `session_start_utc(1635456840000)`, +59 s; file with TIMESTAMP[0] = 1635456840000 | `2021-10-28 21:34` in all three | exact | [1] §4 (S01 mC); arithmetic below | — | PASS |
| `::test_p99_pooled_over_eeg_only` | EEG \|x\| = permutation of 0..N−1 (N = 8 × 2048), random signs; TIMESTAMP ≈ 1.6e12 | p99 = 0.99 × (N − 1) | rel 1e-9 | analytic [own] | non-EEG channels in the pool | PASS |
| `::test_p99_includes_po7` | only PO7 nonzero (−1000) | p99 = 1000 (a 7-channel pool gives 0) | 1e-9 | analytic, [2] pooling over idx 0–7 | PO7 excluded | PASS |
| `::test_dtype_table[...]` | every data_type string of [1] §2 | listed numpy dtype and byte size | exact | [1] §2 | — | PASS (20) |
| `::test_bogus_dtype_raises` | `ebr_dtype("bogus")` | `ValueError` | exact | [1] §2 | — | PASS |
| `::test_float32_block_parsed` | `data_type float` block, TIMESTAMP 1635456909312 ms (= 12477973 × 2^17, exact in float32) | shape (1,11,1,154904), dtype float32, values equal, counts 40/8, session `2021-10-28 21:35`, exit 0 | exact | [1] §2; arithmetic below | float block read as double | PASS |
| `::test_bogus_dtype_file_is_unreadable_deviation` | file with `data_type bogus` | `unreadable … bogus` deviation, exit 1, CSV written | exact | [1] §2, [4] deviation 2a | crash instead of deviation | PASS |
| `::test_header_layout_c_order` | channel c planted as c·1000 + sample index | `data[0, c, 0, :]` returns it for every c; header fields parsed | exact | [1] §2, R6 | wrong reshape order | PASS |
| `::test_header_blank_lines_unknown_keys_and_magic_case` | magic `EBR Binary 1.0  `, blank lines, unknown key `operator X`; then magic `foo binary 2.0` | clean, exit 0; then magic deviation, exit 1 | exact | [1] §2 | case-sensitive magic | PASS |
| `::test_trailing_bytes_is_deviation` | 8 bytes appended after the block | deviation `8 bytes …`, exit 1 | exact | [4] deviation 2c | — | PASS |
| `::test_channel_count_mismatch_is_deviation` | `channels 11` with 10 `channel_k` lines | deviation `declares 11 channels`, exit 1 | exact | [4] deviation 2b | — | PASS |
| `::test_non_integer_mark_is_deviation` | one MARK sample = 0.5 | `non-integer` deviation, exit 1 | exact | [4] deviation 2d | silent rounding | PASS |
| `::test_unreadable_file_is_deviation[truncated,no_end_header]` | S01 clean + S02 truncated by 100 bytes / without `end_header` | exit 1; both rows in CSV; S02 `unreadable` | exact | [1] §2, [4] deviation 2a | crash, lost rows | PASS (2) |

Buggy-variant proof: the naive counter was run against the plateau file inside `test_plateau_test_fails_on_naive_counter` (monkeypatch) and produces 120 stim events and deviations, so `test_plateau_pulses_count_once` fails on it. P00 has no PF entry to replay [2].

Arithmetic (shown command): `.venv/bin/python -c "from datetime import datetime,timezone; print(datetime.fromtimestamp(1635456840,tz=timezone.utc)); [print(n, n/256) for n in (154896,154904,154912,154920,309816,30088,16728)]"` → `2021-10-28 21:34:00+00:00`; 605.0625, 605.09375, 605.125, 605.15625, 1210.21875, 117.53125, 65.34375. Float32 timestamp: `(1635456840000//2**17+1)*2**17` = 1635456909312, `float(np.float32(.)) == .` True, UTC `2021-10-28 21:35:09.312`.

## Command

```bash
.venv/bin/python -m pytest tests/ -q
```

## Output summary

Full suite (2 builder smoke tests + 58 known-answer tests), with `-o addopts=""` to get the summary line under the `-q` of `pytest.ini`:

```
60 passed in 2.42s
```

Known-answer file alone: `58 passed in 2.38s`. No failures. No bug found in `scripts/exploration/inventory_raw.py`.

One first-run failure was my own test arithmetic (float32 timestamp claimed to round into 21:34; the representable value is 21:35:09), corrected in the test before commit; the script was right.

## Coverage gaps

- `kind = unknown` stim counting of both 101–105 and 1001–1005 ([4] deviation 3) is not asserted beyond "warning only, exit 0".
- `nt != 1` / `nb != 1` deviation not tested (one line of code; trivial).
- Console table formatting and the summary line text (`N files, M subjects, K deviations`) are not asserted; only exit codes, CSV and the `Skipping` message.
- Running as a module (`python -m scripts.exploration.inventory_raw`) is not tested; only as a file and via `main()`.
- Session-start minute is truncated, not rounded (21:34:59 → 21:34); the spec does not say which, and the real-data comparison by the verifier decides. Not asserted beyond +59 s.
- p99 pooling vs §4 real values cannot be tested synthetically (plan risk; informational ±0.1 µV).
- No tolerance loosened from the plan.

## Reference consultations (R11)

None. `reference/` was not opened.

## Sources

1. RULE — `mas/01_DATA_SPEC.md` §1 (layout, `^S\d+$`, non-`.ebr` ignored), §2 (header, dtype table, `(nt, nc, nb, ns)`, 11 channels), §3 (onset rule, protocol, online codes), §4 (inventory values). Opened in this run.
2. REQUEST — `mas/state/phases/P00-bootstrap/02_plan.md`, "Inventory script design" and "Tests required". Opened in this run.
3. RULE — `mas/state/phases/P00-bootstrap/00_assignment.md`, roadmap task P00.2 (verbatim). Opened in this run.
4. REQUEST — `mas/state/phases/P00-bootstrap/03_changes_data-engineer.md`, interface table and "Deviations from the plan" 2–4. Opened in this run.

## Questions

ACK 02_plan.md synthetic-tester 2026-10-24

## Round 2

Trigger: orchestrator re-test request after the Round 1 pre-run audit; the data-engineer's Round 2 commits are 9d5c5a9 (`.gitignore` anchors) and c7697c0 (`SUBJECT_PATTERN.fullmatch` in `discover_subjects`) [4, Round 2]. Status stays READY. Code under test is at 66e2fac. The new tests are in commit e807e33 (`test: pin anchored subject discovery and the module CLI form (P00 round 2)`), MODIFIED `tests/test_p00_inventory_known_answer.py`.

| Test id | Simulates | Expected | Tolerance | Source of the expected answer | Catches bug | Result |
|---|---|---|---|---|---|---|
| `::test_decoy_subject_folders_not_discovered` | folders S01, S02 and the decoys `S01x`, `S01_old`, `S01 copy`, `xS01`, `S01<newline>`, each holding a valid OO run | `discover_subjects` = `["S01", "S02"]`; CSV rows (S01, OO), (S02, OO); exit 0 | exact | [1] §1 (`^S\d+$` on the whole folder name) | unanchored `re.match(r"S\d+")`; pre-Round-2 `re.match(r"^S\d+$")` (accepts `S01\n`) | PASS |
| `::test_decoy_folders_catch_unanchored_and_dollar_variants` | the same decoy folders, discovered with each buggy rule | unanchored rule accepts {S01, S01x, S01_old, `S01 copy`, `S01\n`}; `^S\d+$` with `.match` accepts {S01, `S01\n`}; the script's rule accepts only S01 | exact | analytic (Python `re`: `$` matches before a trailing newline) | proves that the decoy set separates the variants | PASS |
| `::test_cli_module_form` | `python -m scripts.exploration.inventory_raw --raw-dir <tmp> --out <tmp>` run from the repo root, on a clean S01/OO tree and on an fs-250 tree | exit 0 / exit 1; CSV written both times with the row (S01, OO, 154904, 40) | exact | [2] design ("runs as file and as module") | broken module entry point or `sys.path` set-up | PASS |

Buggy-variant proof: I put the old rule (`re.compile(r"^S\d+$").match`) in place of `SUBJECT_PATTERN.fullmatch` and ran the script's own `discover_subjects` on S01, S01x, S01_old and `S01\n` in a temporary folder. It printed `['S01\n', 'S01']`, so `test_decoy_subject_folders_not_discovered` fails on the code before c7697c0. `S01x` and `S01_old` were already rejected by the anchored pattern in Round 1. Only the trailing-newline name depends on `fullmatch`. An unanchored pattern would accept all three.

The guard hook refuses shell heredocs whose text names the recording extension, so the Round 2 tests were appended with the editor tool. The test hook ran in the gap between my two edits and reported a `NameError` (`import re` had not been added yet). That failure was transient; the suite then passed.

### Command and output (Round 2)

```bash
.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider
```

```
63 passed in 3.67s
```

Known-answer file alone: `61 passed in 3.48s` (58 from Round 1 + 3 new). The builder's 2 smoke tests also pass. No failures, and no bug found.

### Coverage gaps (Round 2)

- Running as a module is now covered, so the Round 1 gap "Running as a module … is not tested" is closed.
- `.gitignore` anchoring (9d5c5a9) is a repository-configuration fact, not code. It has no pytest test. The verifier checks it with `git check-ignore` (evidence in [4], Round 2).
- The other Round 1 gaps remain: stim counting for unknown-kind files, the trials/bands ≠ 1 check, console formatting, and truncation of the session minute.

### Sources (Round 2)

Sources [1], [2] and [4] above were reopened in this round (for [4], the Round 2 section). I used no new source.
