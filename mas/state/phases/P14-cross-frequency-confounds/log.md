# P14 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-26 | check OK | 1 | mas_status.py | none | |
| 1 Open | orchestrator | 2026-10-26 | opened P14 from main 997635a | 1 | | none | |
| 2 Assignment | orchestrator | 2026-10-26 | 00_assignment.md READY | 1 | 03_ROADMAP P14 | none | |
| 3 Research | orchestrator | 2026-10-26 | skipped (QAP, split-half and periodogram SNR are specified by the roadmap) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-26 | 02_plan.md READY (auto) | 1 | R-13, PF-21–27 | none | runtime risk in the pairwise test; over budget → human run |
| 5 Build | connectivity-stats | 2026-10-26 | 03_changes READY (da0cf64…68d94c9); suite `826 passed, 21 warnings in 399.06s`; runtime est. 18–34 min total (no human run); task-1 smoke: Fisher-mean r coherence 0.629 (66 % QAP p<0.05), wPLI 0.163 (32 %) vs R-13 0.54 (64 %) / 0.14 (32 %) | 1 | R-13, PF-21–27 | none | Hann leakage past the f0 ± 1.5 Hz exclusion flagged (−28 dB); suite runtime ~6.6 min |
| 6 Test | synthetic-tester | 2026-10-26 | 04_tests.md READY (884dae3, e4c9817); +40 tests; 8 mutants caught; suite `866 passed, 21 warnings in 396.98s` | 1 | PF-19, PF-21–27 | none | |
| 7 Pre-run audit | scientific-reviewer | 2026-10-26 | FAIL Round 1 (34301f7): F1 empty 04_tests.md; F2 pairwise null reading (exchangeability, off-centre) needs labels + centred diagnostic + tests; F3 plan bindings; A0–A2, E1–E5, R²/in-alpha rules pre-committed; Hann leakage negligible (≤ 0.05 dB) | 1 | PF-21–27, R7, R-13 | none | F3 done by the orchestrator; F2 code to connectivity-stats, then F1+F2 tests to synthetic-tester |
