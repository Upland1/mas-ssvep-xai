# P22 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK; cohort S01–S05 (B003 amended) | 1 | mas_status | none | |
| 1 Open | orchestrator | 2026-10-28 | branch phase/P22-loso-extensions from main 62213dc | 1 | README | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY; P22.1–P22.4 + P21 C-1, C-2 | 1 | 03_ROADMAP P22 | none | |
| 3 Research | orchestrator | 2026-10-28 | skipped (specified in roadmap, PF-34..37) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); settled 1–7; single builder ml-engineer | 1 | PF-34..37, R-16 | none | classical only, minutes on CPU |
| 5 Build (ml-engineer) | ml-engineer | 2026-10-28 | 03_changes READY (efe635c..669a61f); suite `1403 passed` (14.2 min); runs 6.7–36 s on S01–S05; refusal check works | 1 | PF-34..37, P21 C-1/C-2 | none | recording order from window_starts; deviations: --partial-mean, Folds column, warm-up not resumable, dirty same-head accepted |
