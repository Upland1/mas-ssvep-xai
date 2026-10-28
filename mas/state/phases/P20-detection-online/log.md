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
| 5 Build (ml-engineer) | orchestrator | 2026-10-28 | ml-engineer started (row 2); data-signal after it (sequential, same checkout) | 1 | 02_plan.md | | |
| 5 Build (ml-engineer) | ml-engineer | 2026-10-28 | 03_changes READY (ab72a51, 397fac1, 4d5c681, 54c6fc3, 09bb55d); suite `1263 passed` (13.4 min); C-b, C-c done; sweep split 2a (fbcca lda, ≈ 2 min) / 2b (cnn, human-run candidate) merging deterministically into one out-dir | 1 | R1, R2, PF-31 | none | |
| 5 Build (data-signal) | data-signal | 2026-10-28 | 03_changes READY (7e9cdef, 718705c, a358dc8, 0081e31); suite `1274 passed` (12.7 min); C-1, C-2 done; sweep data ≈ 4.3 GB, < 1 min; pseudo-online ≈ 2.5 min GPU | 1 | PF-38/39 | none | found unit defect: window sweep writes offset_sec in samples (load_subject offsets are samples) → ml-engineer fix |
| 5 Build fix | ml-engineer, deep-learning | 2026-10-28 | offset_sec samples→seconds in window sweep (54156df, suite `1275 passed`) and NN sweep (adf9f2d, suite `1276 passed`), each with a test failing on the old line | 1 | R8, §6 schema | none | caught by data-signal's input check, before any audit |
| 6 Test | synthetic-tester | 2026-10-28 | 04_tests.md READY (bdf317a); +21 independent tests; 18/18 mutants killed; suite `1297 passed, 22 warnings in 781.21s` | 1 | R1, R2, PF-32, PF-38 | none | gaps: stride-0.25 fixture, CCNN learning on GPU, fallback/channel-drop only in builders' tests |
| 4 Plan (run list) | orchestrator | 2026-10-28 | 02_plan.md run commands: final CLIs, sweep split 2a/2b, measured estimates and verifier order | 1 | handoffs | none | |
| 7 Pre-run audit | scientific-reviewer | 2026-10-28 | PASS (db474b6), no fixes; A–I, S, P1–P6, R-P1–R-P12 copied into 02_plan.md | 1 | R1–R9, PF-31/32/38/39 | none | budget 106–160 min with 2b → 2b probably a human run |
