# P19 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK; B003 (decide before P20) open | 1 | mas_status | none | |
| 1 Open | orchestrator | 2026-10-28 | branch phase/P19-raw-quality from main 86d7d47 | 1 | README | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY; tasks P19.1–P19.4 + P17 C-a | 1 | 03_ROADMAP P19 | none | |
| 3 Research | orchestrator | 2026-10-28 | skipped (no new method) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); settled points 1–9 in decisions.md | 1 | PF-05/07/14 | none | raw drifts may reject most windows (record, not tune) |
| 5 Build (data-signal) | data-signal | 2026-10-28 | 03_changes READY (e090d20, ff638a3, 6d470d2); suite `1 failed, 1217 passed` (12.6 min), the failure (exact data_source string in test_p17_windowing.py) fixed, file re-run 10 passed, full suite not re-run; S01 smoke: filtered/raw/both all 320/320 valid, PO7 dropped in all, raw 11 artifact blocks; filtered smoke cmp-identical to _p17 S01; ≈ 1 s per subject per build | 1 | 02_plan.md | none | loader rejections_by_label gains a `raw` count (beyond "string only"; needed for sums) |
