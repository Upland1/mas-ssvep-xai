# P18 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK | 1 | mas_status.py | none | |
| 1 Open | orchestrator | 2026-10-28 | opened P18 from main 0038eec | 1 | | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY | 1 | 03_ROADMAP P18 | none | |
| 3 Research | orchestrator | 2026-10-28 | skipped (NBS fully specified in the roadmap task 1; no external source opened) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); budget ≈ 100 / 120 min, human-run rule for the pairwise run | 1 | §6, PF-19/20/25/26 | none | |
| 5 Build (connectivity-stats) | connectivity-stats | 2026-10-28 | 03_changes READY (2df7341, 529e5f8, 882fdc9); suite `1184 passed` (12.2 min); S01 smoke: 15 pre-P18 columns equal P16 v2cont; projected 5-subject run ≈ 76 min + suite ≈ 89 min (< 110) | 1 | §6, PF-19/20/25 | none | no mutation check by the builder; S01 200 vs 1000 permutations: 4/20 cells flip (R7 inconclusive); P13/P14 schema-pin tests extended |
| 6 Test | synthetic-tester | 2026-10-28 | 04_tests.md READY; +21 independent tests; type-I 3/400 (bound ≤ 37), pairwise null 1/40, power 10/10; 6 mutants killed; suite `1205 passed, 22 warnings in 749.59s` | 1 | R6, R7, PF-20/25/26 | none | planted-subnetwork masks larger than the planted edges (tone-driven PLV on non-planted channels) |
| 4 Plan (run list) | orchestrator | 2026-10-28 | 02_plan.md run commands copied from the handoff (5 commands incl. --compare) | 1 | handoff | none | |
| 7 Pre-run audit | scientific-reviewer | 2026-10-28 | PASS (0044229), no fixes; V0–V8 copied into 02_plan.md; concerns C1–C4 non-blocking (threshold-boundary NBS flips, centred pairwise NBS, no second pairwise count, budget ≈ 96–102 min) | 1 | R7, PF-20/25/26 | none | |
| 8 Run + verify | verifier | 2026-10-28 | PASS (b96d5df); 5 commands exit 0, 92.5 min total (49.9 min after cmd 3 < 69); V0–V8 met; 1000 perms: FDR 48, NBS 43, global p 32 of 100 cells; flips 17 (FDR 14, NBS 6 all threshold-boundary, global 0) | 1 | R7, V0–V8 | none | P2 direction not met (NBS 43 < FDR 48); p_mag_centred agreement not computed (column absent from tests CSV) |
| 9 Results review | scientific-reviewer | 2026-10-28 | APPROVE (3db9410); D-1..D-6 and C-1..C-6 copied to decisions.md; scribe items S1–S9 | 1 | R7, R9, F1/F2 | none | P2 refuted, P6 partly refuted (recorded) |
