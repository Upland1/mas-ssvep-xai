# P23 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Reads: 00_assignment.md, 02_plan.md (settled 9, row 4), 03_changes_deep-learning.md, mas/state/phases/P21-loso-colab/03_changes_data-signal.md, mas/RULES.md
Branch: phase/P23-gnn-loso
Commit(s): see `git log` (feat: notebook section 10b; test: notebook structure; docs: this file)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `notebooks/loso_colab.ipynb` | MODIFIED | section "10b" inserted between the network cells (step 10) and the comparison table (step 11): intro, settings cell, smoke, within, four LOSO cells, reading note. 11 cells added, no existing cell changed, no outputs | P23.3 | PF-40, R2, R9, [own] |
| `tests/test_p23_notebook.py` | NEW | 8 structure tests of section 10b | P23.3 | PF-40 |
| `tests/test_p21_notebook.py` | MODIFIED | `_commands` skips the 10b cells (they are checked in the P23 test); the P21 assertions (3 modules, 6 commands) are unchanged | P23.3 | - |

## Section 10b

- Intro for a first-time user: what the GNN is, the two variants, 3 seeds, early stopping on training trials; `pooled` vs `subject` (`_subjnorm` = test-time whole-session normalization, labels not used, offline upper bound, R2 exception); expected runtimes for S01-S05 from the measured figures (smoke ~1 min, within ~7-9 min, each LOSO cell ~3 min, four ~12-13 min; x8 for 40 subjects); resumption; a note that `BRANCH` must name a branch containing `benchmark_gnn_loso`.
- Settings cell: `GNN_LOSO_OUT = "reports/loso_gnn_w1_colab"`, `GNN_WITHIN_OUT = "reports/within_gnn_w1_colab"`, asserted different from the P21 `LOSO_OUT` and `WITHIN_OUT`, so a P21 folder is never resumed into. `reports` is the Drive symlink of step 6.
- Cells: smoke (`--smoke-test --threads 2 --device cpu`, no `--out-dir`, temp dir); within (`--protocol within`, both variants, `--norm pooled`, `--seeds 3`); LOSO x4 (`nodes+F` and `nodes+coh+F`, each `pooled` and `subject`, `--seeds 3`). All use `--channels common --window 1 --stride-sec 0.25 --threads 2 --device cpu`, fixed because both are part of the fold config and a change would be refused. CPU is fixed (the GPU is not faster for this network, deep-learning timings).
- Step 11 (comparison) is unchanged: it reads the P21 folders only. GNN tables are read from `summary.csv` / `folds.csv` of the two new folders (cell 10b.4 says so); joining them is left to the phase report.

## Deviations from the plan

1. A new test file instead of extending the P21 one (the plan allowed either); the only P21 test edit is the skip of 10b cells.
2. `BRANCH` in the P21 settings cell is not changed (P21 tests assert only the repo URL); the intro tells the user to set it.

## Verification

- `.venv/bin/python -m pytest tests/test_p21_notebook.py tests/test_p23_notebook.py -q -o addopts=""` -> 16 passed. The tests check: no outputs and unique ids; 10b after the last network cell and before the comparison and release cells; intro mentions `_subjnorm`, test-time normalization, offline upper bound; command order smoke, within, 4 LOSO; every `python -m scripts...` line parses with the real `benchmark_gnn_loso.build_parser`; no `pip install` / requirements in 10b; within = pooled, both variants, 3 seeds; each LOSO cell has exactly one variant and one norm and all four combinations are present; `--threads 2 --device cpu` everywhere; LOSO cells share one out-dir, within another, smoke none; out-dirs differ from the P21 ones.
- Full suite once, alone: `.venv/bin/python -m pytest tests/ -q -o addopts=""` -> `1491 passed, 22 warnings in 854.49s (0:14:14)` (log `mas/state/scratch/p23_ds_suite.log`, run after the two commits above, no other job running).

## Manual steps (Colab)

1. Set `BRANCH` in step 3 to the branch that holds `benchmark_gnn_loso` (after the merge, `main` or the P23 branch), rerun steps 3-7.
2. Run 10b in order: settings, smoke (must print PASS), within, then the four LOSO cells in any order; rerun a cell after a disconnect.
3. Keep `--threads` and `--device` unchanged within an out-dir; use new out-dir names after changing any setting.

Not run on Colab by this agent.

## Reference consultations (R11)

None. The original repository was not opened.

## Sources

1. `mas/RULES.md` R2, R9, R11; `mas/05_PITFALLS.md` PF-40; `03_changes_deep-learning.md` (CLI, timings).

## Questions

None.
