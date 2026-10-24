# P00 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (Acceptance checks), 03, 04, 05, 07, log.md, decisions.md, blocker B005
Clean checkout: `mas/state/scratch/verify_P00` @ f3958a8 (git worktree, removed afterwards; no data copied)

Verdict: PASS

Scope (blocker B005, option B): the delivered dataset is OO and mOO of S01-S05 (10 files). Acceptance = every delivered file matches its `01_DATA_SPEC.md` §4 row; the 13 absent rows are listed below.

## Tests on the clean checkout

```bash
cd mas/state/scratch/verify_P00 && <repo>/.venv/bin/python -m pytest tests/ -q
```

Output: `...............................................................          [100%]` (63 dots, no failure). A filtered run (`-k "cli or deviation"`) printed `15 passed, 48 deselected in 1.62s`.

## Acceptance

| Criterion (verbatim) | Re-run command | Obtained | Reference | Tolerance | Met? |
|---|---|---|---|---|---|
| inventory matches §4 row for row (samples, duration, stim events) | `<repo>/.venv/bin/python <worktree>/scripts/exploration/inventory_raw.py --raw-dir <repo>/data/raw --out <repo>/mas/state/scratch/verify_P00_out/raw_inventory.csv` (wrapped in a `python -c subprocess.run(...)` to capture the exit code, because the guard rejects a trailing `; echo`) | `EXIT= 0`; summary `10 files, 5 subjects, 0 deviations` | 01_DATA_SPEC §4 | samples, stim exact; duration 0.1 s; start to the minute; p99 +-0.1 uV | yes (10 of 10 delivered rows) |
| `git status` shows no data files | `git ls-files` filtered for data extensions, data/, reports/ and local-tooling paths (case-insensitive grep) | no output (0 hits); `git status --porcelain` empty | P00.3 | exact | yes |
| `pytest -q` runs | above | 63 passed | | | yes |
| exit 1 on a synthetic deviation | `test_cli_exit_codes_as_subprocess`, `test_cli_module_form`, wrong-fs / channel / missing-trial tests (inside the 63) | passed | P00.2 | exact | yes |

CSV comparison: `cmp reports/raw_inventory.csv mas/state/scratch/verify_P00_out/raw_inventory.csv` printed `IDENTICAL` (byte-identical to the runner's CSV).

### Join with the §4 table

Command: `<repo>/.venv/bin/python mas/state/scratch/join_P00.py` (regex-parses the §4 markdown rows; `9 (100x)` style cells parse to the integer; outer merge on (subject, file)).

```
spec rows 23
CSV rows 10 ; unmatched CSV rows: 0
S01 OO 154904.0 154904 605.1 605.1 40.0 40 2021-10-28 21:57 785.13 785.1 OK
S01 mOO 154912.0 154912 605.1 605.1 40.0 40 2021-10-28 21:47 187.59 187.6 OK
S02 OO 154912.0 154912 605.1 605.1 40.0 40 2021-11-18 17:45 40.06 40.1 OK
S02 mOO 154912.0 154912 605.1 605.1 40.0 40 2021-11-18 18:20 37.48 37.5 OK
S03 OO 154896.0 154896 605.1 605.1 40.0 40 2021-11-20 00:36 331.41 331.4 OK
S03 mOO 154896.0 154896 605.1 605.1 40.0 40 2021-11-20 00:51 1013.8 1013.8 OK
S04 OO 154896.0 154896 605.1 605.1 40.0 40 2021-11-25 01:23 481.54 481.5 OK
S04 mOO 154912.0 154912 605.1 605.1 40.0 40 2021-11-25 00:47 24.94 24.9 OK
S05 OO 154912.0 154912 605.1 605.1 40.0 40 2021-11-26 16:42 24.59 24.6 OK
S05 mOO 154904.0 154904 605.1 605.1 40.0 40 2021-11-26 16:30 23.8 23.8 OK
matched 10 all ok True
absent from delivery (13): S01/C, S01/mC, S02/C, S02/mC, S02/online_C, S03/C, S03/cb_mas_mcb, S03/mC, S04/C, S04/mC, S05/C, S05/mC, S05/online_OO
```

Columns: subject, file, CSV samples, spec samples, CSV duration, spec duration, CSV stim, spec stim, CSV start, CSV p99, spec p99.
Per subject (R9): S01-S05 each have OO and mOO, all matched; data source is `.ebr` headers plus the MARK channel (no accuracy is reported in this phase).

### Synthetic module-form run

Covered by `tests/test_p00_inventory_known_answer.py::test_cli_module_form` and `test_cli_exit_codes_as_subprocess` (subprocess on synthetic `.ebr`: exit 0 clean, 1 on deviation), both inside the 63 passed.

## Numbers in the handoffs vs logs

The 05_run.md console table and CSV match the verifier's re-run (CSV byte-identical). The runner ran at 042e1b2; `git diff --stat 042e1b2 f3958a8` shows only B005, decisions.md, 05_run.md and log.md changed (4 files, bookkeeping only), so the run is valid for HEAD.

## Privacy and git

- Tracked data-like / local-tooling filter: 0 hits. `git status --porcelain` empty.
- Commit messages and author fields on `d9da2ff..HEAD` (20 commits): vendor / co-author grep returned nothing.
- `git check-ignore -v <repo>/data/raw/S01/OO.ebr` gave `.gitignore:14:data/` (ignored).
- `git check-ignore -v mas/state/reports/P00.md` exited 1 (not ignored; the file does not exist yet, the scribe writes it). `reports/raw_inventory.csv` is ignored (`.gitignore:29:/reports/`), as intended.
- No commit on main, no push.

Observation (non-blocking): a case-insensitive `git grep` in HEAD for the assistant/vendor names matches only lines 35 and 89 of `mas/state/phases/P00-bootstrap/07_review.md`, where the reviewer quotes the audit grep pattern itself. No attribution or tool trace; a strict reading of "no mention in committed files" would prefer those two lines reworded before the public merge. Suggest the orchestrator or reviewer reword them.

## Sources spot-check

The only source is `mas/01_DATA_SPEC.md` §4, opened and parsed in this run; every compared value traces to its table.

## Reference consultations check

`mas/state/scratch/reference_access.log` does not exist (no access logged). 03_changes states `reference/` was not opened; 04_tests lists "None". Consistent.

## Reasons (if FAIL)

None.
