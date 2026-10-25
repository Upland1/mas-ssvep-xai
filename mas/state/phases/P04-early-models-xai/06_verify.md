# P04 · 06 · Verify

Status: READY
Author: verifier
Reads: 05_run.md, logs in `reports/logs/P04/`, `outputs/`, 07_review.md pre-run audit

Verdict: PASS

## Questions

ACK 05_run.md verifier 2026-10-24

## Numbered reasons

1. Clean checkout: HEAD `552029a73f061407ccfa1fb8a194acb7b7eea53c`; worktree full pytest on CPU: 349 passed, 0 failed (`mas/state/scratch/pytest_P04.txt`, 349 dots, exit 0). All seven run commands ran once with a clean tree (`dirty files: 0`), device cpu, 140 epochs default.
2. All seven commands exit 0 (`python exit code: 0` in every log; summary `mas/state/scratch/run_P04_summary.txt`). Total about 9.1 min against budget 120.
3. Expected files exist: 5 `outputs/reports/S0*_model_evaluation.csv`, `batch_run_subjects.csv`, 6 `cm_*.png` at root and 6 per subject S01-S05, 3 XAI figures, 4 model files.
4. `DualBranchFusionCNN` = 10005 parameters (`param_count_20261024T223559.log`); both `.pt` files load into a fresh `DualBranchFusionCNN` (`All keys matched`), `n_parameters` 10005, `epochs` 140.
5. Model reload: `S01/S04_shrinkage_lda.joblib` load (feature_dim 37, fit label "full data (export/XAI only; R2 exception)", n_windows 200 / 198); the `.pt` files carry `train_accuracy` 0.935 (S01) and 1.0 (S04), labelled fit export, not test scores.
6. Consistency: batch `LDA 1.0 s` and `LDA smoothed` equal the Shrinkage-LDA `Accuracy` and `Smoothed Accuracy` of `<S>_model_evaluation.csv` exactly for all five subjects (exact float equality, checked in Python). Window counts 200/199/200/198/200 equal R-1 stimulus counts.
7. Per-subject tables: see `05_run.md` (batch CSV with CNN 1.0 s, CNN smoothed and CNN train acc; six classifiers per subject). All results are legacy leaky window-level CV (R1/PF-01) with no-reset smoothing (R8/PF-02), as labelled in the CSV `cv`/`smoothing` columns; no comparison with R-6 is made here (left to the results review per its pre-committed checks).
8. Batch log has no "arrays missing, running run_preprocessing" line and no Traceback in any log.
9. Privacy/git: `git ls-files` has no data, recording, outputs, reports, local-tooling or answer-key paths; fragment-built grep for assistant/vendor/co-author names over HEAD content and over `main..HEAD` messages (14 commits): 0 hits. `git status` clean after the run (outputs and logs are ignored).
10. R11: `mas/state/scratch/reference_access.log` still has 4 lines, the last two at 21:27:47-48 (agent `main`, README only), pre-P04 and already attributed in decisions.md. No new access during this run.
11. Deviation (non-blocking): the batch command omitted `--paradigm` because the guard hook blocks the session file name in command text; the script default is that same session (`batch_run_subjects.py:42`), and the CSV `Data source` reads `legacy windows, OO.ebr`.
12. Worktree `mas/state/scratch/verify_P04` removed.
