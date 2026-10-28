# P20 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK; B003 decided for P20 (S01–S05 under both options), open for P21 | 1 | mas_status, B003 | none | |
| 1 Open | orchestrator | 2026-10-28 | branch phase/P20-detection-online from main e4978f5 | 1 | README | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY; tasks P20.1–P20.6 + carry-forwards | 1 | 03_ROADMAP P20 | none | |
| 3 Research | orchestrator | 2026-10-28 | skipped (CCNN, FBCCA, dynamic stopping specified in the roadmap) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); settled 1–12; build order deep-learning → ml-engineer ∥ data-signal | 1 | PF-31/32/38/39 | none | CNN parts may become a human run |
| 5 Build (deep-learning) | orchestrator | 2026-10-28 | deep-learning builder started (row 1) | 1 | 02_plan.md | | ml-engineer and data-signal follow in parallel |
| 5 Build (deep-learning) | deep-learning | 2026-10-28 | 03_changes READY (54bc298, a30a9de, 6893adc, 4312d41); suite `1249 passed` (13.7 min); measured s/epoch per window; cmd 3 ≈ 20–31 min, sweep cnn part ≈ 80–120 min → cnn parts ≈ 100–150 min (> budget) | 1 | PF-31/32 | none | sweep cnn part is the human-run candidate; val-loss for selection = plain CE (builder choice) |
