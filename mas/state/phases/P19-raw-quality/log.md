# P19 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK; B003 (decide before P20) open | 1 | mas_status | none | |
| 1 Open | orchestrator | 2026-10-28 | branch phase/P19-raw-quality from main 86d7d47 | 1 | README | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY; tasks P19.1–P19.4 + P17 C-a | 1 | 03_ROADMAP P19 | none | |
| 3 Research | orchestrator | 2026-10-28 | skipped (no new method) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); settled points 1–9 in decisions.md | 1 | PF-05/07/14 | none | raw drifts may reject most windows (record, not tune) |
| 5 Build (data-signal) | data-signal | 2026-10-28 | 03_changes READY (e090d20, ff638a3, 6d470d2); suite `1 failed, 1217 passed` (12.6 min), the failure (exact data_source string in test_p17_windowing.py) fixed, file re-run 10 passed, full suite not re-run; S01 smoke: filtered/raw/both all 320/320 valid, PO7 dropped in all, raw 11 artifact blocks; filtered smoke cmp-identical to _p17 S01; ≈ 1 s per subject per build | 1 | 02_plan.md | none | loader rejections_by_label gains a `raw` count (beyond "string only"; needed for sums) |
| 6 Test | synthetic-tester | 2026-10-28 | 04_tests.md READY (e0a79f9); +13 independent tests; 15/15 mutants killed; suite `1231 passed, 22 warnings in 732.68s` (builder fix confirmed: `1218 passed` without the new file) | 1 | R5, R6, PF-07 | none | raw path proven wired end to end (synthetic 1500 µV drift → reason 3) |
| 7 Pre-run audit | scientific-reviewer | 2026-10-28 | PASS (2928ddb), no fixes; A–F copied into 02_plan.md; notes C-1..C-4 to decisions.md | 1 | R3, R5, R6, R9, PF-07/14 | none | reviewer pinned the expected raw_gate count from _p17 raw windows (S03 row 160) |
| 8 Run + verify | verifier | 2026-10-28 | PASS (20ab583); suite 1231 passed; commands 0–8 exit 0, 19.8 min; A–F met; raw_gate pinned (S03 row 160 only), raw_guard 0 under both; flagship filtered vs both identical except S03 base (−0.24 / −0.09, not material) | 1 | A–F | one directory-metadata listing of the answer key (no content), disclosed in 05_run.md | null result as pre-committed |
| 9 Results review | scientific-reviewer | 2026-10-28 | APPROVE (5be0674); D-1..D-3, C-1..C-6 copied to decisions.md; scribe items 1–6 | 1 | R9, R11 | none | null wording amended for one borderline window |
