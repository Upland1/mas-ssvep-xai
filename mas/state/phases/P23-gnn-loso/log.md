# P23 · Run log  (written by: orchestrator)

| Step | Agent | Date | Outcome | Round | Sources cited | Reference consultations (R11) | Notes (cost, loops, what was caught) |
|------|-------|------|---------|-------|---------------|-------------------------------|--------------------------------------|
| 0 Preflight | orchestrator | 2026-10-28 | check OK; cohort S01–S05 (B003 amended) | 1 | mas_status | none | |
| 1 Open | orchestrator | 2026-10-28 | branch phase/P23-gnn-loso from main 3afc0a7 | 1 | README | none | |
| 2 Assignment | orchestrator | 2026-10-28 | 00_assignment.md READY; P23.1–P23.3 + P22 C-1, C-3, C-6 | 1 | 03_ROADMAP P23 | none | ml-engineer added for the benchmark_loso carry-forwards |
| 3 Research | orchestrator | 2026-10-28 | skipped (P15 definitions, roadmap) | 1 | | none | |
| 4 Plan | orchestrator | 2026-10-28 | 02_plan.md READY (auto); settled 1–9; order connectivity-stats → ml-engineer → deep-learning → data-signal | 1 | PF-28/30/32..37, R-15, R-16 | none | roadmap budget ≈ 75 min CPU for cohort 5 |
| 5 Build (connectivity-stats) | connectivity-stats | 2026-10-29 | 03_changes READY (7349b5b, e1fd733, 47768d4); suite `1450 passed` (13.5 min); features ≈ 0.2–0.3 s per subject, no cache | 1 | R3, R4, R6 | none | NEW graph_features_subject.py (graph_inputs.py name taken); legacy 250 Hz path pinned by a test |
| 5 Build (ml-engineer) | ml-engineer | 2026-10-29 | 03_changes READY (271a1f4, 06cd42d, 605f944, e463111); suite `1461 passed`; P22 C-1 (n_windows_train, build_git_commits, config_hash), C-3 Normalization column, C-6 within Data source, groups, docstring | 1 | PF-37, R2 | none | reusable API: cohort_provenance, provenance_fields, within_source, check_fold |
| 5 Build (deep-learning) | deep-learning | 2026-10-29 | 03_changes READY (bd6379e, 1912c73, 86079df); suite `1483 passed` (14.3 min); smoke 87.97 % synthetic LOSO, rerun skips all; 6/6 mutants killed; full within + LOSO ≈ 20–28 min CPU 2 threads | 1 | R1, R2, PF-28/30/32/37 | none | deviations: --threads (default 2) and device in fold config, --only-test/--only-fold debug, subject read twice for FBCCA bank |
| 5 Build (data-signal) | data-signal | 2026-10-29 | 03_changes READY (cfdcec7, c384dc7, de6b98d); suite `1491 passed` (14.2 min); notebook 10b: 11 cells, own out-dirs asserted ≠ P21, --threads 2 --device cpu fixed | 1 | PF-40, R2 | none | not run on Colab |
