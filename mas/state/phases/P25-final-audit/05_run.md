# P25 · 05 · Run

Status: READY
Author: verifier
Reads: 02_plan.md (settled 1, 3, 4, 5; Run commands; Acceptance checks), 00_assignment.md, mas/state/decisions.md (newest rows), 07_review.md (written in parallel, not relied on)
Branch / commit: `phase/P25-final-audit` @ `6490a6c` (`chore: P25 log dispatch`) for the clean checkout. The branch head moved to `c809f65` while the suite ran (reviewer commits `3f779c0`, `c809f65`); `git diff --stat 6490a6c HEAD -- src scripts configs Makefile tests` is empty, so the code under test is unchanged.
Machine: Linux 7.0.0-38-generic, 16 CPU cores, Python 3.12.3, torch 2.14.1+cu130, CUDA available (`torch.cuda.is_available()` True), interpreter `.venv/bin/python` of the main tree.

## Commands executed

| # | Command | Start | Runtime | Exit | Log | Outputs |
|---|---|---|---|---|---|---|
| 1 | `git worktree add --detach mas/state/scratch/verify/P25 HEAD` (the branch name is checked out in the main tree, so the clean checkout is detached at the same commit) | 2026-10-29 20:55 | seconds | 0 | (console) | worktree `mas/state/scratch/verify/P25`, committed files only |
| 2 | in the worktree: `<main>/.venv/bin/python -m pytest tests/ -q` (detached, `tee` into the log) | 2026-10-29T20:55:17-06:00 | 14 min 50 s (end 21:10:07-06:00) | see Anomalies | `mas/state/scratch/verify/P25_pytest.log` | none (git status of the worktree empty after the run) |
| 3 | `git diff --stat bb9c091 main -- src scripts configs Makefile` | 20:55 | seconds | 0 | (console) | `scripts/benchmarks/pseudo_online.py | 3 +++`, `1 file changed, 3 insertions(+)` |
| 4 | `.venv/bin/python mas/state/scratch/p25_ref_table.py` | 21:00 | seconds | 0 | `mas/state/scratch/p25_ref_table.out` | numbers for the R-x table |
| 5 | `.venv/bin/python mas/state/scratch/p25_sources_check.py` | 21:00 | seconds | 0 | (console, quoted in 06_verify.md) | sources report |
| 6 | read-only greps and `cut` over `mas/state/scratch/reference_access.log` and `mas/state/reports/P*.md` | 20:57-21:10 | seconds | 0 | (console) | autonomy report |

Rebuild evidence (settled 1, not rerun): `mas/state/scratch/p24_make/` (`make_all.log`, `DONE` = `DONE rc=0 2026-10-29T17:41:42`, `clone_head` = `bb9c0913624238310b8b7f6d7b543c18e495b624`, `compare_reports.csv`, `compare_npz.txt`, `hash_data.txt`), `mas/state/scratch/p24_fix2/` (`exits.txt`, `tables.md`, `run_fix2.sh`), `mas/state/phases/P24-documentation/05_run.md` and `06_verify.md`, `mas/state/reports/P24.md`.

## Human run requests

None.

## Produced files

- `mas/state/scratch/verify/P25_pytest.log`, `mas/state/scratch/p25_ref_table.py`, `mas/state/scratch/p25_ref_table.out`, `mas/state/scratch/p25_sources_check.py` (git-ignored).
- `mas/state/phases/P25-final-audit/05_run.md`, `06_verify.md`.

## Anomalies

1. The suite log has no final pytest summary line. `pytest.ini` has `addopts = -q`, and `-q` on the command line makes it `-qq`, which prints no totals. Counts are taken from the progress characters of the log: `1563` dots (passed), `6` `s` (skipped), `0` `F`, `0` `E`, `grep -c "FAILED|ERROR"` gives 0; total 1569. The command was run once, as required, and was not repeated to get a summary line. Command: `grep -E "^[.sFExX]+ *(\[ *[0-9]+%\])?$" mas/state/scratch/verify/P25_pytest.log | sed 's/\[.*//' | tr -d ' \n' | fold -w1 | sort | uniq -c`.
2. For comparison, the P24 clean-clone suite had `4 failed, 1561 passed, 22 warnings in 855.25s (0:14:15)` (`mas/state/scratch/p24_make/pytest_clone.log`), the 4 failures being `test_cited_reports_paths_exist` after `make all`, fixed in P24 fix round 2. The P25 checkout has no `make all` outputs.
3. `reports/nn_sweep/summary.csv` (CCNN) and the R-8 table disagree on the CCNN parameter count; see 06_verify.md reason 1.

## Questions
