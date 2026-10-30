# P25 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Audit the whole rebuild: reproducible from the raw recordings, free of leakage outside the
labelled legacy paths, every reference target accounted for, every consultation and source
listed, and the capability gap with the original repository stated. Then close the project.

## Settled points (inferred; recorded in decisions.md)

1. **Clean-machine rebuild (task 1).**
   - Sebastian chose that the P24 `make all` run also serves as the P25 clean-machine
     rebuild (decisions, 2026-10-29). It ran on a fresh clone at bb9c091, and the two
     pseudo-online tags were rerun at afcd417 (P24 fix round 2).
   - Since bb9c091 the only code change under `src/`, `scripts/`, `configs/` and
     `Makefile` is `scripts/benchmarks/pseudo_online.py` (+3 lines; `git diff --stat
     bb9c091 main`). No new rebuild is run. The verifier re-checks that statement and
     cites the P24 evidence: `mas/state/scratch/p24_make/` (log, stamps,
     `compare_reports.csv`), `p24_fix2/`, P24 `05_run.md` and `06_verify.md`.
   - The full test suite runs once on a fresh clean checkout of `phase/P25-final-audit`
     under `mas/state/scratch/verify/P25` (about 15 min on CPU plus the CUDA case).
2. **Leakage audit (task 2, reviewer).**
   - Enumerate every script and module that splits data: any use of
     `StratifiedGroupKFold`, `StratifiedKFold`, `KFold`, `GroupKFold`,
     `train_test_split`, `LeaveOneGroupOut`, LOSO subject loops, early-stopping
     validation splits and warm-up splits.
   - For each one give: file:line of the split, groups used, whether every `.fit` of
     scalers, CSP, selection, normalization or networks is in-fold, its era status (legacy
     by design, with flag, or enforced), and the test that guards it (file::test).
   - A split without a guarding test is a finding. A legacy split is acceptable only if
     the era matrix prescribes it and it is labelled.
3. **Reference comparison (task 3, verifier).**
   - One row per R-x in `mas/04_REFERENCE_RESULTS.md`: target, obtained value with
     CSV/log path, tolerance, and status (within tolerance / explained deviation with its
     decisions row or blocker / unexplained).
   - Accepted deviations (B006, B007, P24 A-1..A-6 and the per-phase decisions rows)
     count as explained.
4. **Autonomy report (task 3, verifier).**
   - Every line of `mas/state/scratch/reference_access.log` and every "reference
     consultation" entry in the handoffs and phase reports P00–P24, with phase, agent,
     date, trigger and whether a file was opened.
   - The share of phases completed without any consultation, with a shown Python
     command.
   - Log lines that only name the folder in an exclusion argument are listed separately,
     not counted as consultations.
   - P25 task 4 is itself a consultation to verify finished work (R11) and is listed.
5. **Sources report (task 3, verifier).** For `mas/state/reports/P00.md`–`P24.md`: a
   `## Sources` section exists, every numbered citation in the body resolves to an
   entry, and every cited repository path exists.
6. **Module diff (task 4, reviewer).**
   - Compare module by module with the original's three branches: `main`,
     `feature/window-size-online-detection` and `test/GNN-testing-LOSO`.
   - Read only through `git -C reference/ssvep-eeg-xai show <branch>:<path>` and
     `ls-tree`, as the guard requires; every access is logged. Never write inside
     `reference/`.
   - Output a table: module or capability, original (branch:path), rebuild (path),
     present on both / missing in the rebuild / missing in the original, and a note.
   - No code is copied.
7. **Deviations.**
   - "No unexplained deviations" covers results (R-x), not runtimes. P24 A-5 (the p19
     clone runtime) is reported as an unexplained runtime observation with no effect on
     any result. The reviewer rules on this reading.
   - Open items that are not deviations stay listed in P25.md as open questions:
     - the Colab notebook sections not run;
     - carry-forwards;
     - P17 C-d/C-e;
     - the P22 `within_lda` label in the old main-tree CSVs.
8. **Close.**
   - The scribe writes `mas/state/reports/P25.md`, which includes the history-squash
     list for Sebastian.
   - At the gate the orchestrator sets P25 passed, merges with `--no-ff`, and tags
     `p25-done` and `v1.0` on the merge commit.
   - Nothing is pushed: pushing is Sebastian's.

## Work split (verifier and reviewer in parallel; then scribe)

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | verifier | `05_run.md`, `06_verify.md` | settled 1, 3, 4, 5 |
| 2 | scientific-reviewer | `07_review.md` (sections "Leakage audit", "Module diff", then "Results review") | settled 2, 6, 7 |
| 3 | scribe | `mas/state/reports/P25.md`, `RESEARCH_LOG.md`, `CHANGELOG.md` | task 5 |

There are no builders and no synthetic-tester rows: P25 changes no code. If the audit
finds a defect, it becomes a fix round with the owning builder.

## Run commands (for the verifier)

```bash
# 0. clean checkout: git worktree add mas/state/scratch/verify/P25 phase/P25-final-audit (or git clone --no-hardlinks)
# 1. .venv/bin/python -m pytest tests/ -q  (in the checkout, with the main tree's .venv)  ~15 min
# 2. git diff --stat bb9c091 main -- src scripts configs Makefile
# 3. tables for settled 3-5 from CSVs, logs and reports (shown commands)
```

## Acceptance checks

1. Every phase P00–P24 is `passed` in `mas/state/phase_status.yaml`, and no blocker is
   open.
2. The suite passes on a clean checkout. The rebuild evidence is cited.
3. Every split has a guarding test, or a finding.
4. Every R-x row is within tolerance or explained.
5. Autonomy and sources reports are complete.
6. The module-diff table exists.
7. The privacy scan of the net diff with the guard's term list is clean.

## Sources

- `mas/03_ROADMAP.md` P25.
- `mas/phases.yaml`.
- `mas/04_REFERENCE_RESULTS.md`.
- `mas/RULES.md`.
- `mas/state/decisions.md`.
- `mas/state/reports/P24.md`.
- `mas/state/blockers/`.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
