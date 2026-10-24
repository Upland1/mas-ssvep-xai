# P00 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: FAIL

Scope read (code, not summaries): `scripts/exploration/inventory_raw.py` (all 411 lines), `tests/test_p00_inventory_known_answer.py`, `tests/test_p00_inventory_smoke.py`, `requirements.txt`, `environment.yml`, `Makefile`, `pytest.ini`, `.gitignore`, `CHANGELOG.md`, `RESEARCH_LOG.md`, the 31 `__init__.py` of `git ls-files`, against [1] §1–§4, [2] §1, §2, §4, §7, [3], [4], [5], [6] P00 rows. Branch `phase/P00-bootstrap` @ 4c9ed38. Nothing under `data/raw/` was opened, listed or run; `reference/` not opened; `mas/state/scratch/reference_access.log` does not exist (no consultation by anyone).

Suite re-run by the reviewer: `.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider` → `60 passed in 2.39s`.

Era A, P00: the era matrix [7] prescribes no legacy behaviour here, so no row can be `LEGACY (by design)`.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no split, no model |
| R2 Fit only in-fold | N/A | nothing is fitted |
| R3 Filter continuous, then window | N/A | no filtering or windowing; p99 is on the raw signal, as [1] §4 states ("raw signal is unfiltered") |
| R4 Estimator small-sample bias | N/A | no estimator |
| R5 Shared quality decision, explicit thresholds | N/A | no quality decision, no shared helper |
| R6 Index layouts verified | PASS | memmap shape `(nt, nc, nb, ns)` C order `scripts/exploration/inventory_raw.py:167-173`; channel `c` read as `data[0, c, 0, :]` `:290-293`, `:316`; proven by planting `c*1000 + s` per channel `tests/test_p00_inventory_known_answer.py:469-480` (an F-order or `(ns, nc)` reshape fails it) |
| R7 Honest statistics | N/A | no statistics |
| R8 Smoothing respects trials | N/A | no smoothing |
| R9 Per-subject reporting with data source | PASS | one row per file with `subject` and session `file` stem `inventory_raw.py:255-256`, `:344-348`; console prints every row `:389-392` |
| fs from metadata (era-matrix row) | PASS | fs comes from the header `:265`; `256` appears only as the expected value `:46`, `:274-275`; duration uses the header fs `:269-270` |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | spot-checked: [1] §3 onset rule matches `:186-194`; [1] §2 dtype table matches `:63-75` and the tester's independent table `tests/…known_answer.py:28-35`; [2] §7 "event onsets" row exists; PF-09 at `mas/05_PITFALLS.md:56-59` says "fail loudly", as cited |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no external code used (03 "Differences from the cited examples"); the test dtype table is copied from the spec, not from code |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | both handoffs list none; no `reference_access.log` in `mas/state/scratch/` |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | N/A | no legacy behaviour in P00 |
| Tests cover every change; at least one fails on the historical bug | PASS | no PF entry applies; the plateau guard is proven against the naive `(mark == code).sum()` counter by monkeypatch `tests/…known_answer.py:146-174`. Every acceptance item and every builder check has a test (table in `04_tests.md`); gaps in the notes below |
| Changes match 02_plan.md and the roadmap tasks | PASS (with CONCERN 1) | plan design items all present: CLI `:369-377`, root search `:30-36`, columns in plan order `:77-79`, kind rule `:197-205`, checks `:272-304`, summary line and CSV path `:403-405`, exit 1 after writing the CSV `:402-406`, `sys.exit(main())` `:410`. Four extra hard checks (03 Deviations 2): see CONCERN 1 |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git ls-files` filtered case-insensitively for `data/`, the data extensions (`.ebr`, `.npy`, `.npz`, `.pt`, `.joblib`, `.mp4`, `.jpg`, `.jpeg`, `.csv`, `.log`) and the locally excluded agent-tooling paths → `0` hits; commit messages `main..HEAD` filtered for the assistant/vendor names and co-author trailers → `0`; `git grep` of HEAD for the assistant/vendor names → no match |
| `.gitignore` keeps the committed state committed | **FAIL** | `.gitignore:29` `reports/` is unanchored and also matches `mas/state/reports/`: `git check-ignore -v --no-index mas/state/reports/P00.md` → `.gitignore:29:reports/	mas/state/reports/P00.md`. See Required fix 1 |

### Spec conformance of the checks (task-specific)

| Spec item [1] | Implementation | Fails loudly? | Test |
|---|---|---|---|
| §2 fs 256 | `:274-275` exact float compare on the parsed header value | yes, named deviation, exit 1 | `…known_answer.py:190-201`, `:251-262` (as subprocess) |
| §2 11 channel names in order | `:276-277` tuple equality, case-sensitive | yes | `:204-225` (rename; 10 channels, MARK still found by name) |
| §2 `nt = nb = 1` | `:280-281` | yes | not tested (trivial; 04 coverage gap) |
| §3 calibration onsets 40 × {201, 202, 203, 200}, 8 × {101..105}, nothing else | `:56-57`, `:222-228` (`!=`, both directions; extra codes flagged) | yes | `:132-141`, `:228-248`; over-count of an expected code only indirectly (note 6) |
| §3 online: only 1001–1005 | `:229-232` | yes | `:267-296` |
| §4 joined run: 80 stim | `:233-236` | yes | `:299-309` |
| §3 onset rule `(mark == code) & (diff(mark, prepend=0) != 0)` | `:192-194`, applied to all codes at once; equivalent per code (a code-to-code step counts the new code, which the per-code form also does) | — | `:177-185` incl. back-to-back codes and a pulse at sample 0 |
| §4 duration to 0.1 s | `round(ns / fs, 1)` `:270`; reviewer check `python3 -c "print(round(154896/256,1), round(154920/256,1), round(30088/256,1), round(16728/256,1), round(309816/256,1))"` → `605.1 605.2 117.5 65.3 1210.2`, all equal to §4 | — | `:314-327` every §4 sample count |
| §4 session start | first TIMESTAMP sample, UTC, `%H:%M` (truncated) `:245-247`, `:306-312` | non-finite → deviation | `:368-377`; truncation vs rounding is untestable synthetically (note 2) |
| §4 p99 of abs(EEG) | `np.percentile(|x|, 99)` over the 8 EEG channels pooled, whole file `:314-317` | — | `:382-415` (non-EEG excluded; PO7 included) |
| §1 subjects `^S\d+$`, only `.ebr` | `:50`, `:325-328` numeric order, `:340` | empty subject → `[-] Skipping` `:341-343`; empty tree / missing folder → exit 1 `:379-385` | `:332-363` (`S1x`, `s03`, `notes`, stray `S99.ebr`, `.jpg/.mp4/.txt`) |

Run command and outputs: `python scripts/exploration/inventory_raw.py` (as `.venv/bin/python …` per [6] row 1) writes `reports/raw_inventory.csv` (default `:373-374`, root `parents[2]` until P01 creates `configs/pipeline_config.yaml`) and ends with `N files, M subjects, K deviations` and `Saved: <path>` `:403-405`; the runner adds `reports/logs/P00/inventory_raw_<timestamp>.log` with the header of [2] §4. `make inventory` is the same command `Makefile:21-22`. Correct and inside budget (plan: < 1 min).

### Required fixes

1. **data-engineer — `.gitignore:28-30` (rule: AGENTS.md §4 and `mas/README.md` §3 item 9, "`mas/state/` is committed as the reproducibility record").** `reports/` (and likewise `outputs/`, `baselines/`) is unanchored, so `mas/state/reports/Pxx.md` — the scribe's phase report, committed state per AGENTS.md §4 — is silently ignored: `git status` would never show it and the record would be lost without an error. Anchor the generated folders at the root (`/reports/`, `/outputs/`, `/baselines/`) or add `!mas/state/reports/` after them. Keep `data/` and the data extensions unanchored (privacy wants the broad match). Prove it in `03_changes` Round 2 with `git check-ignore -v --no-index` on path strings: `mas/state/reports/P00.md` → not ignored (exit 1); `reports/raw_inventory.csv`, `reports/logs/P00/x.log`, `outputs/m.pt`, `outputs/reports/x.csv`, `baselines/x.csv`, `data/raw/S01/OO.ebr`, `data/processed/S01/X.npy` → still ignored. Fix it before the run so the run commit is also the gate commit. No code or test change is needed; the tester's Round 2 is a no-op (suite unchanged).

### Non-blocking notes

1. **CONCERN — the four extra hard checks (03 Deviations 2).** Judged from the spec only:
   (a) *unreadable file* `:258-263` — justified: [1] §2 says an unsupported `data_type` raises `ValueError`, and a truncated block or a header without `end_header` cannot be parsed as §2 defines; turning a crash into a named deviation with the other rows kept is strictly better (PF-09 spirit). No false failure possible on a §2-conformant file.
   (b) *channel count mismatch* `:278-279` — justified: §2 defines `channels <nc>` followed by `channel_1 … channel_<nc>`; a conformant file cannot trip it.
   (c) *non-integer / non-finite MARK* `:299-300` — justified: §3 defines MARK as 0 plus integer event codes; integers are exact in the delivered `double` type, and the 1e-6 tolerance only matters for float-typed files. A conformant file cannot trip it.
   (d) *trailing bytes* `:176-181`, `:282-284` — **not stated by the spec.** §2 fixes the block size (`nt*nc*nb*ns` elements, starting right after `end_header`) but does not say the file ends there. A file that is otherwise §2-conformant with, e.g., a final newline or footer would fail. The failure is loud (named deviation, exit 1, CSV still written), so it cannot corrupt a number silently; that is why it is a CONCERN and not a FAIL. If it fires on the real data, the runner reports it and stops; the orchestrator escalates (downgrade to a warning vs investigate the header offset) — nobody edits the check to make the run pass. Note that a constant small trailing count across all 23 files would point to a footer; a count that varies with `ns` would point to a wrong `samples` or offset and must not be waved through.
2. **Session start: truncated, not rounded** (`strftime("%H:%M")` `:247`). [1] §4 does not say which; the tolerance is "to the minute" (00_assignment). Session start is not in the verbatim acceptance (samples, duration, stim events). Verifier: report any ±1 min differences as a truncation/rounding question, not as a failed acceptance.
3. **p99 pooling is a first attempt** (plan risk). Informational ±0.1 µV; a mismatch triggers R11 consultation after one investigation round, never a tuning of the pooling to match.
4. **Completeness is not checked by the script.** A missing session file, a missing subject, or online runs with other than 9 / 7 events ([1] §3) pass the script with exit 0 (`:229-232` only rejects foreign codes). The roadmap's script requirements do not ask for this, so it is not a defect, but the acceptance then rests entirely on the verifier's 23-row join on (subject, file) with samples, duration and stim events exact. The verifier must not skip that join; the §4 stim column for online runs reads `9 (100x)` / `7 (100x)` and has to be parsed to the integer.
5. **Hidden companion files.** `:340` accepts any `*.ebr`, case-insensitively, so AppleDouble files such as `._OO.ebr` (if the data was ever copied through macOS) would become `unreadable` rows and exit 1. Loud, so harmless for correctness; mentioned so the runner recognises it if it appears.
6. **Test strength, buggy variants checked by hand.** (a) A `counts[code] < expected` variant (missing pulses only) passes every direct test, because no test plants an over-count of an expected code; it is caught only indirectly by the naive-counter guard (`:165-174`, which asserts non-empty deviations at 3× counts). The code uses `!=` `:224`, so the script is correct. (b) Module invocation (`python -m scripts.exploration.inventory_raw`, required by [2] §4) is untested; the builder smoke-ran it (03, "How I verified"). Verifier: run the module form once on a synthetic tree. (c) `nt/nb != 1` untested (one line). None of these changes a P00 number.
7. **Nit.** `SUBJECT_PATTERN.match` with `$` `:50`, `:327` also accepts a name ending in a newline; `fullmatch` is the literal reading of `^S\d+$`. Not reachable with real folder names; for `src/io/subject_data.py` (P16) prefer `fullmatch`.
8. **Era-A reminder for later phases.** The inventory reads fs from the header; the deliberate `fs=250` assumption of Era A belongs to the feature code (P02 onward), not here. P00 must not be cited later as evidence that fs was "handled" in Era A.

## Pre-run audit — Round 2

Verdict: PASS

Scope: commits 9d5c5a9, c7697c0 (data-engineer), e807e33 (synthetic-tester), handoff rounds 66e2fac and 0cec390; branch `phase/P00-bootstrap` @ 0cec390. `git diff 4c9ed38..HEAD -- .gitignore scripts/ tests/` read in full. Nothing under `data/raw/` or `reference/` opened; script not run on real data.

| Item | Result | Evidence |
|---|---|---|
| Required fix 1 (`.gitignore`, committed state) | PASS | `.gitignore:28-30` now `/outputs/`, `/reports/`, `/baselines/`; `data/` and data extensions unchanged (`.gitignore:14-18`, `:24-27`). Reviewer's own `git check-ignore -v --no-index` on path strings: `mas/state/reports/P00.md` → no match, rc=1 (not ignored); `reports/raw_inventory.csv`, `reports/logs/P00/x.log` → `.gitignore:29:/reports/`; `outputs/m.pt`, `outputs/reports/x.csv` → `.gitignore:28:/outputs/`; `baselines/x.csv` → `.gitignore:30:/baselines/`; `data/raw/S01/OO.ebr`, `data/processed/S01/X.npy`, `data/processed_continuous/S01/y.npz` → `.gitignore:14:data/`; `SSVEPs_OO_mOO/x` → `.gitignore:21`; `mas/state/scratch/x` → `.gitignore:39` |
| Nit 7 (subject regex) | PASS | `scripts/exploration/inventory_raw.py:327` `SUBJECT_PATTERN.fullmatch`; only change in `scripts/` |
| New test `test_decoy_subject_folders_not_discovered` | PASS | decoys `S01x`, `S01_old`, `S01 copy`, `xS01`, `S01\n` each hold a valid `OO.ebr`; only S01, S02 discovered and inventoried. Hand-checked against the Round 1 code: `re.match("^S\d+$")` accepts `S01\n` and `int("01\n") == 1`, so discovery would return 3 names and the test fails, i.e. it pins the fix |
| New test `test_decoy_folders_catch_unanchored_and_dollar_variants` | PASS | proves the decoy set separates the unanchored `re.match("S\d+")` and `$` variants from `fullmatch` |
| New test `test_cli_module_form` | PASS | closes Round 1 note 6(b): `python -m scripts.exploration.inventory_raw` from the repo root, exit 0 clean / 1 on fs 250, CSV written both times |
| Suite | PASS | `.venv/bin/python -m pytest tests/ -q -o addopts="" -p no:cacheprovider` → `63 passed in 3.44s` |
| No data, local tooling files or vendor names | PASS | tracked data-like / local-tooling file count `0`; `git log --format=%B 4c9ed38..HEAD` vendor/co-author count `0`; `git grep` of HEAD for the assistant/vendor names → no match |
| Rule table of Round 1 | unchanged | no other code changed; all Round 1 PASS/N/A rows stand |

Remaining non-blocking notes from Round 1: 1 (trailing-bytes check strictness; decision to pre-record), 2 (session-start truncation), 3 (p99 pooling), 4 (completeness rests on the verifier's 23-row join), 5 (hidden `._*.ebr`), 6(a) (no direct over-count test), 6(c) (`nt/nb != 1` untested). None blocks the run. The runner may start.

## Results review

Verdict: APPROVE

Read: `05_run.md` (9d4de50), `06_verify.md` (b9cea91, Verdict PASS), blocker B005 (resolved, option B) [9], `decisions.md` rows 14–15 [6], the log `reports/logs/P00/inventory_raw_20261024_141334.log` (header `HEAD: 042e1b2…`, `DIRTY: 0`) and `reports/raw_inventory.csv` [10]. No raw file opened.

Independent join by the reviewer (CSV vs the §4 markdown table [1], one regex per §4 row, `9 (100x)` cells parsed to the integer): `.venv/bin/python -I -c "…"` (inline script reading only `mas/01_DATA_SPEC.md` and `reports/raw_inventory.csv`) → `spec rows 23`; `all ok 10 of 10` (samples exact, duration exact at 0.1 s, stim exact, start string equal, p99 rounded to 0.1 equal, `deviations` empty, fs `256.0`); `absent 13`. Same result as the verifier's join and the 13 absent rows it lists. Run valid for the gate: the verifier showed `git diff --stat 042e1b2 f3958a8` is bookkeeping only, and its CSV re-run is byte-identical.

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| 01_DATA_SPEC §4, rows delivered (10: OO, mOO × S01–S05) | samples, duration, stim, start, p99 per §4 row | identical on all 10 [10] | samples, stim 0; duration 0; start 0 min; p99 per-row Δ (CSV full precision − §4) `0.03, -0.009, -0.04, -0.017, 0.007, -0.001, 0.041, 0.043, -0.015, 0.003` µV (S01 OO … S05 mOO) | yes (exact / 0.1 s / minute / ±0.1 µV) | — | — |
| 01_DATA_SPEC §4, all 23 rows | 23 rows | 10 rows; absent: S01–S05 `C`, `mC`; S02 `online_C`; S03 `cb_mas_mcb`; S05 `online_OO` | −13 rows | no (as written) | not delivered (B005 [9]); no input failed a check. `grep -nwE "mC\|online_C\|online_OO\|cb_mas_mcb"` over `mas/03_ROADMAP.md`, `mas/04_REFERENCE_RESULTS.md`, `mas/02_REQUIREMENTS.md` → no match; the only `--session` in the roadmap is `--session OO` (`03_ROADMAP.md:649`); §1 says `C`/`mC` are used "only where a phase says so", and §3 says no phase uses the online runs | **yes, signed** (see below) |

**Signature, B005 deviation (`decisions.md` row 15).** Accepted by the scientific reviewer, 2026-10-24. Reasons: (1) the 10 delivered files match §4 on every column with zero deviations, so the absence is a delivery scope fact, not a measurement disagreement; (2) no roadmap phase, reference result or requirement consumes the 13 absent sessions; (3) nothing was tuned or relaxed to get here — the script's checks are unchanged and would still fail loudly on a delivered file that deviates. Conditions: (a) the phase report and `RESEARCH_LOG.md` state that P00 reproduced 10 of the 23 §4 rows and name the 13 absent ones, never "the §4 inventory"; (b) the code paths for `online` and `joined` kinds and for `C`/`mC` stems are validated on synthetic files only (`04_tests.md`); if those recordings are delivered later, the inventory is re-run and the new rows are checked against §4 before any phase uses them; (c) B003 (cohort beyond S05) is unaffected.

### Interpretation check

- **Per subject (R9).** S01–S05 each have OO and mOO, all 40 stim onsets with the full calibration pattern `101–105:8; 200–203:40` [10]; fs 256 and the 11 channel names in every file. Data source: `.ebr` headers + MARK/TIMESTAMP/EEG channels of the delivered OO/mOO sessions. No accuracy in P00.
- **Pre-run note 1 (trailing bytes).** Did not fire (0 deviations [10]); decision row 14 stays as a standing rule.
- **Pre-run note 2 (session start truncated to the minute): settled as consistent, not as proven.** All 10 start strings equal §4. Truncation and rounding give the same minute whenever the seconds are < 30, so 10/10 agreement does not by itself exclude rounding; it does show the implemented rule reproduces the reference on every delivered file, which is all the tolerance ("to the minute") asks. No action. If a later file disagrees by exactly one minute, check the seconds first.
- **Pre-run note 3 (p99 pooled over the 8 EEG channels, whole file): settled.** All 10 values round to the §4 value; max |Δ| before rounding is 0.043 µV, across references spanning 23.8 to 1013.8 µV. A different pooling (7 channels without PO7, per-channel mean, filtered signal) would be very unlikely to land within 0.05 µV on all ten. The plan's first attempt is accepted as the §4 definition; no R11 consultation was needed or made.
- **Leakage / statistics.** N/A: nothing is fitted, no test statistic.
- **What this phase does not show.** It does not validate PO7 exclusion, the `fs=250` legacy assumption, or any window count; those start in P01–P02.

### Decisions for decisions.md

1. Row 15 (B005 deviation): signed by the scientific reviewer 2026-10-24 under conditions (a)–(c) above; replace "pending reviewer signature" with "signed, 07_review.md results review".
2. `p99_abs_eeg_uv` definition = 99th percentile of |x| pooled over the 8 EEG channels (PO7…O2) of the whole raw file, `np.percentile` default interpolation; reproduces §4 on 10/10 delivered files (max |Δ| 0.043 µV before rounding).
3. `session_start_utc` = first TIMESTAMP sample, UTC, truncated to the minute; matches §4 on 10/10 delivered files (rounding not excluded by the data).

## Sources spot-check

Results review: [1] §4 table parsed and joined with [10] by the reviewer (10/10 match); [9] resolution text read (option B, reviewer to sign); verifier's join output in `06_verify.md` agrees.

Pre-run, opened in this run: [1] §2 dtype table and §3 onset rule compared line by line with `inventory_raw.py:63-75` and `:186-194` (match); [5] PF-09 lines 56–59 (says "fail loudly", as cited by the builder); [2] §7 "event onsets" row (exists, asserts single-sample and plateau pulses give one onset).

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Sources

1. RULE — `mas/01_DATA_SPEC.md` §1 (layout, `^S\d+$`, non-`.ebr` ignored), §2 (header, dtype table, block size and `(nt, nc, nb, ns)`, 11 channels), §3 (onset rule, protocol, online codes), §4 (inventory). Opened in this run.
2. RULE — `mas/02_REQUIREMENTS.md` §1 (environment), §2 (layout), §4 (conventions: module run, `[-] Skipping`, log naming), §7 (event-onset test). Opened in this run.
3. REQUEST — `mas/state/phases/P00-bootstrap/00_assignment.md` and `02_plan.md` (approved 2026-10-24). Opened in this run.
4. HANDOFF — `mas/state/phases/P00-bootstrap/03_changes_data-engineer.md` (Deviations 1–7) and `04_tests.md` (coverage gaps). Opened in this run.
5. RULE — `mas/05_PITFALLS.md` PF-09 (lines 56–59), PF-13 (lines 74–77). Opened in this run.
6. REQUEST — `mas/state/decisions.md` P00 rows (lines 11–13). Opened in this run.
7. RULE — `mas/RULES.md` R1–R11 and era matrix; `AGENTS.md` golden rules 1, 3, 8 and §4 (state files committed); `mas/README.md` §3 item 9. Opened in this run.
8. HANDOFF — `03_changes_data-engineer.md` Round 2 (66e2fac) and `04_tests.md` Round 2 (0cec390); diffs of 9d5c5a9, c7697c0, e807e33. Opened in this run (Round 2).
9. REQUEST — `mas/state/blockers/B005-inventory-10-of-23-files.md`, resolution (Sebastian, 2026-10-24, option B). Opened in this run (results review).
10. DATA — `reports/raw_inventory.csv` and `reports/logs/P00/inventory_raw_20261024_141334.log`, `.venv/bin/python scripts/exploration/inventory_raw.py`, commit 042e1b2; with `05_run.md` (9d4de50) and `06_verify.md` (b9cea91). Opened in this run (results review).

## Questions

ACK 04_tests.md scientific-reviewer 2026-10-24

- to orchestrator: Required fix 1 is a one-line `.gitignore` change for the data-engineer; Round 2 of the audit only needs the `git check-ignore` evidence listed there.
- to orchestrator: please record in advance (decisions.md) what happens if the trailing-bytes check (note 1d) fires on the real data: runner stops and reports; Sebastian decides; the check is not edited to make the run pass.
