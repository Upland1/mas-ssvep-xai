# P22 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK; cohort S01–S05 (B003 amended) | 1 | mas_status | none | |
| 1 Open | orchestrator | 2026-10-28 | branch phase/P22-loso-extensions from main 62213dc | 1 | README | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY; P22.1–P22.4 + P21 C-1, C-2 | 1 | 03_ROADMAP P22 | none | |
| 3 Research | orchestrator | 2026-10-28 | skipped (specified in roadmap, PF-34..37) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); settled 1–7; single builder ml-engineer | 1 | PF-34..37, R-16 | none | classical only, minutes on CPU |
| 5 Build (ml-engineer) | ml-engineer | 2026-10-28 | 03_changes READY (efe635c..669a61f); suite `1403 passed` (14.2 min); runs 6.7–36 s on S01–S05; refusal check works | 1 | PF-34..37, P21 C-1/C-2 | none | recording order from window_starts; deviations: --partial-mean, Folds column, warm-up not resumable, dirty same-head accepted |
| 6 Test | synthetic-tester | 2026-10-28 | 04_tests.md READY (431208e, 4d14bb0); +30 independent tests; 17/18 mutants killed (labels-in-warm-up not constructible: no label argument); suite `1433 passed` (15.8 min) | 1 | R1, R2, PF-34..37 | none | gap: check_fold accepts a configs/ change between heads (CODE_PATHS = src, scripts) — flagged for the audit |
| 7 Pre-run audit | scientific-reviewer | 2026-10-28 | FAIL (581ab9a): F1 dirty-flag hole when heads differ, F2 add configs to CODE_PATHS (ml-engineer); T1 tests for F1/F2, T2 rejected-first-window recording rank, T3 suite count (tester); PR-1..PR-7, V1..V11 to copy | 1 | PF-36, PF-37, P21 C-1 | none | predictions written after the builder smoke: labelled plausibility checks |
| 5 Fix round 1 | ml-engineer | 2026-10-28 | F1 dirty-flag rules, F2 configs in CODE_PATHS (101a0f7, daadad8, cbced17); suite `1434 passed` (14 min) | 1 | PF-37 | none | |
| 6 Fix round 1 | synthetic-tester | 2026-10-28 | T1 six-row table (F1, F2 reverts killed), T2 masked-first-window rank, T3 suite `1441 passed` (13.6 min) (3cf689c, 6cc1674) | 1 | PF-36, PF-37 | none | |
| 7 Pre-run audit round 2 | scientific-reviewer | 2026-10-28 | PASS (a120f0b); PR-1..PR-7, V1..V11 copied verbatim into 02_plan.md | 2 | PF-36, PF-37 | none | N8 code_changed docstring, N9 P21 folds now refused (fresh out-dirs used) |
| 8 Run + verify | verifier | 2026-10-28 | PASS (f5700bd, 5f73505); clean worktree 461ef33; suite `1433 passed, 8 skipped` (CUDA hidden); commands < 30 s each; V1..V11 met; PR-1..PR-7 hold (PR-5 4/5, S05 −2.16 SE_Δ) | 1 | V1–V11, PR-1–PR-7 | none | warm-up mean warmup−full −27.27/−19.16/−5.46/−0.91 at K 1/2/5/10 |
