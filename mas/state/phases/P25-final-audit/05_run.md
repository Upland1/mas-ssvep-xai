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

## Fix round 1 rerun (CCNN regeneration)

Author: verifier. Binding items: `07_review.md` "Fix round 1 audit (CCNN)" G-0..G-7 (they replace the handoff's rerun plan). Code under test: CCNN fix 987742b; HEAD at start 463c793bcba5ade6c2c0b1bfaf107b3be511ac81 (`mas/state/scratch/p25_fix1/head.txt`). Later commits changed only documents: `git diff --stat 463c793 HEAD -- src scripts configs Makefile tests` is empty. `git status --porcelain -- src scripts configs Makefile` was empty at start and in every step log header (dirty count 0). Fold configs: `git_dirty` False in all 206 new network and classical fold files, `git_head` 81e32794 (the head at the LOSO invocations; src/scripts identical to 463c793).

### Commands executed

| # | Command | Start | Runtime | Exit | Log |
|---|---|---|---|---|---|
| G-0 | detached clean checkout at 463c793, `<main>/.venv/bin/python -m pytest tests/ -q -rs` | 2026-10-29T21:53:09-06:00 | 14 min 54 s | 0 failures | `mas/state/scratch/p25_fix1/g0_pytest.log` |
| G-1 | `cp -a` of the six trees to `mas/state/scratch/p25_fix1/old/`, `sha256sum` manifest, `sha256sum -c` on the copies | 21:55 | seconds | 240 OK, 0 not OK | `old_manifest.sha256`, `old_manifest_copy.sha256` |
| G-3 | `mas/state/scratch/p25_fix1/run_fix1.sh` (detached, stamped, resumable): nn_sweep (ccnn compact eegnet), pseudo-online 5/6 class and repeat of both, cohort-5 classical, networks (ccnn compact eegnet), classical again, seeds 43 and 44 (ccnn eegnet), cohort-39 classical, ccnn, classical again, G-4 | 2026-10-29T22:08:15-06:00 | to 2026-10-30T00:53:23-06:00 (wall 2 h 45 min; step sum 9907 s) | every step rc=0 | `reports/logs/P25/fix1_<step>.log`, `mas/state/scratch/p25_fix1/steps.txt`, marker `DONE` |
| G-5/G-6 | `.venv/bin/python mas/state/scratch/p25_fix1/check_fix1.py` | after DONE | seconds | 0 (no G-5 failure) | `mas/state/scratch/p25_fix1/check_fix1.out` |
| G-2 swap | `mv reports/<t> mas/state/scratch/p25_fix1/replaced/<t>; mv reports/<t>__p25fix1 reports/<t>` for the six trees | after checks | seconds | 0 | (console) |
| G-7 | `find ... | sha256sum > new_manifest.sha256` | after swap | seconds | 238 files | `mas/state/scratch/p25_fix1/new_manifest.sha256` |

Step runtimes (`steps.txt`): nn_sweep 975 s; po5 31 s; po6 81 s; po5_repeat 30 s; po6_repeat 63 s; c5_classical 12 s; c5_networks 1028 s; c5_classical2 6 s; seed43 428 s; seed44 440 s; c39_classical 488 s; c39_ccnn 5308 s; c39_classical2 18 s; g4_rs1..5 197, 202, 201, 202, 197 s. GPU steps sum to 8384 s = 2.33 h (`.venv/bin/python -I -c` over steps.txt), above `MAX_GPU_HOURS_PER_PHASE` 2 (`mas/state/config.yaml`). **Overrun stated:** the run was done locally, detached, under the standing authorisation for long local runs (decisions 2026-10-28/29, G-3). The cohort-39 eegnet run was not made (G-3e: only if asked); its 2 abandoned old folds are in `old/` only.

### Produced files

New canonical trees (swapped in): `reports/nn_sweep/`, `reports/pseudo_online/`, `reports/loso_w1_s01-s05/`, `reports/loso_w1_s01-s05_seed43/`, `reports/loso_w1_s01-s05_seed44/`, `reports/loso_w1/` (156 folds, 117 classical and 39 ccnn). Old trees: `mas/state/scratch/p25_fix1/old/` (copy, verified) and `mas/state/scratch/p25_fix1/replaced/` (the moved originals, identical to `old/` by `diff -rq` for nn_sweep and loso_w1). G-4 outputs: `reports/connectivity_comparison/*_diag_r13_rs{1..5}.csv`. Logs: `reports/logs/P25/fix1_*.log`. Manifests: `old_manifest.sha256`, `new_manifest.sha256`, `reports_other_before.sha256`, `reports_other_after_g3.sha256`.

### Anomalies

1. Two background wait loops (watching for the marker) were stopped by the session for low memory; the detached driver was not affected.
2. `loso_w1` now has 156 folds against 158 before, because the 2 abandoned eegnet folds are not recreated (G-3e).
3. `Folds` column drift in three `summary.csv` files and `Data source` / `Seconds` differences are the known P24 A-2 schema drift, reported as soft.
