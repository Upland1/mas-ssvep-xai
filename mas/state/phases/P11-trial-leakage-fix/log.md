# P11 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-26 | check OK (B003 non-blocking) | 1 | mas_status.py | none | |
| 1 Open | orchestrator | 2026-10-26 | opened P11 from main 829602c | 1 | | none | |
| 2 Assignment | orchestrator | 2026-10-26 | 00_assignment.md READY | 1 | 03_ROADMAP P11, phases.yaml, team.yaml | none | |
| 3 Research | orchestrator | 2026-10-26 | skipped (StratifiedGroupKFold and trial ids are not new methods to the team) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-26 | 02_plan.md READY (auto); settled points in decisions.md | 1 | 04_REFERENCE R-5/6/7/9, PF-01–04, 01_DATA_SPEC | none | smoothing rule for R-6 2.0 s chosen per R8/PF-02 with mod5 printed alongside |
| 5 Build (ml-engineer) | ml-engineer | 2026-10-26 | 03_changes_ml-engineer.md READY (2d562cf…18a6792); 631 tests pass (count from dots, -q suppresses the summary); grouped 1.0 s = R-6 exactly; 2.0 s matches R-6 only with mod5 | 1 | R-6, R8 | none | orchestrator corrected settled point 1 (R8 text: i%5 on legacy); default change sent back to the ml-engineer |
| 5 Build (ml-engineer, round 1 orchestrator change) | ml-engineer | 2026-10-26 | 31d6f8e; default --smoothing mod5 on legacy, trial = PF-02 diagnostic; suite `632 passed, 21 warnings in 281.95s`; smoke demo grouped 2.0 s = R-6 on all subjects | 1 | R8 | none | |
| 5 Build (deep-learning) | deep-learning | 2026-10-26 | 03_changes_deep-learning.md READY (d810553, f81c907, 5e4fc3c); suite `646 passed, 21 warnings in 295.41s`; legacy smoke CSVs sha256-identical to 829602c; N4 tests added | 1 | R-7, R-9b, PF-01–03, PF-28 | none | builder left a detached scratch worktree (wt829) it was denied permission to remove; left for Sebastian |
| 6 Test | synthetic-tester | 2026-10-26 | 04_tests.md READY (1aaf36e, e361166); +30 tests; 5 mutants (M1–M5) caught; suite `676 passed, 21 warnings in 337.92s` | 1 | PF-01–03, R6, R8 | none | |
| 7 Pre-run audit | scientific-reviewer | 2026-10-26 | FAIL Round 1 (32461e2): demo network section pairs CSVs without checking the splitter label; C1 decision row required before results review; acceptance windows P1–P7 pre-committed | 1 | R1, R8, PF-01–03, R-6, R-9b | none | C1 written by orchestrator; fix 1 sent to ml-engineer (Round 1) |
| 5 Build (Round 1 fix) | ml-engineer | 2026-10-26 | bb4d2ea: demo pairs A/B CSVs only when meta splitter labels are leaky/grouped; N2 wording; N1 documented; suite `677 passed, 21 warnings in 339.01s` | 2 | 07_review.md R1 fix | none | |
| 6 Test (Round 1) | synthetic-tester | 2026-10-26 | 567a98a: demo splitter-pairing known-answer test; mutant M6 caught; suite `678 passed, 21 warnings in 365.55s` | 2 | 07_review.md R1 fix | none | |
| 7 Pre-run audit (Round 2) | scientific-reviewer | 2026-10-26 | PASS (d7e2952); fix verified; C1 satisfied; P1–P7 unchanged; suite `678 passed` | 2 | R1, R8, PF-01–03 | none | carry: N1 (P16), N3 network legacy pin test (deep-learning), N4 residual leak S02/S04 stated in report; step-1 demo prints three network skips by design |
