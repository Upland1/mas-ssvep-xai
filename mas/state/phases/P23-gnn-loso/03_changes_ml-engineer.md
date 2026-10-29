# P23 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Branch: phase/P23-gnn-loso
Scope: settled point 8 of `02_plan.md` (P22 carry-forwards C-1, C-3, C-6; review N2, N8; report W-1). P22 outputs are not regenerated.

## Files

| Path | | Change |
|---|---|---|
| `scripts/benchmarks/benchmark_loso.py` | MODIFIED | `code_changed` docstring names `src/`, `scripts/`, `configs/` (N8). `run_fold` passes `P["groups"]` to `within_lda_fold` (N2). `within_lda` rows get `within_source(...)` as `Data source` (W-1: "..., within-subject (trial-grouped CV), channels ..."; LOSO rows unchanged). Fold config gains `n_windows_train`, `build_git_commits`, `config_hash` (C-1). New helpers `file_sha256`, `cohort_provenance`, `provenance_fields`, `within_source`; module docstring updated; `import hashlib`. |
| `scripts/benchmarks/benchmark_loso_warmup.py` | MODIFIED | New last column `Normalization` in `summary.csv` (every row incl. Mean/SD) and in `cohort.csv`; also `warmup_config.json["normalization"]`. Text (constant `NORMALIZATION`): full = whole-session unlabeled statistics (test-time normalization, offline upper bound); warmup = first K unlabeled trials (test-time, online); none = no normalization (R2 exception, PF-35). |
| `tests/test_p22_loso_extensions.py` | MODIFIED | `BASE`/`CHANGES` extended with the three new keys (the "every config key is covered" test requires it). |
| `tests/test_p23_loso_carryforwards.py` | NEW | 8 tests, one per fix; all 8 fail on the P22 code (checked by stashing `scripts/`). |

`check_fold` / `fold_problem` need no change: they already compare every config key except `git_head`, `git_dirty`, `data_root`, so the new keys are compared (the key name appears in the refusal message).

## Reusable API for the GNN harness (deep-learning)

All in `scripts.benchmarks.benchmark_loso` (import as `L`):

- `L.cohort_provenance(loaded, config_path) -> {"n_windows": {S: int}, "build_commits": {S: str}, "config_hash": str}`; `loaded` = the `load_subject` dicts (needs `subject`, `y`, `meta`). Call once per process, before the dicts are dropped; merge into your `ctx` (`ctx = {..., **prov}`).
- `L.provenance_fields(prov, train_subjects, test) -> {"n_windows_train", "build_git_commits", "config_hash"}`; splat into the fold config (`build_git_commits` covers the training subjects and the test subject).
- `L.file_sha256(path)`.
- `L.check_fold(path, saved, mine, repo=L.ROOT)`, `L.fold_problem`, `L.config_diff`, `L.save_fold`, `L.load_fold`, `L.capture_run_state()`, `L.RUN_STATE`: unchanged and generic over any config dict. The config must carry `git_head`/`git_dirty` (from `RUN_STATE`) plus the harness's own keys (variant, norm, protocol, seeds, val_frac, epochs, patience ...); any difference of a key other than `git_head`, `git_dirty`, `data_root` is refused.
- `L.within_source(source)` replaces ", LOSO," by ", within-subject (trial-grouped CV),": use it for the `Data source` of `--protocol within` rows.
- The R2 label for GNN `_subjnorm` outputs (P22 C-3) stays with the GNN harness; `benchmark_loso_warmup.NORMALIZATION` is reusable wording.

## Tests and run

- `.venv/bin/python -m pytest tests/test_p23_loso_carryforwards.py tests/test_p22_loso_extensions.py tests/test_p22_warmup.py -q -o addopts=""`: 54 passed.
- Equality of `groups` and `trial_ids` for classes 101-105 is asserted on a built synthetic folder (`load_subject`); a second test plants `cv_groups != trial_ids` and shows `within_lda_fold` receives `P["groups"]`.
- Full suite: result line below.

## Deviations

- `Normalization` is one text per row (a warm-up row holds `full`, `warmup`, `none` side by side, so a per-variant value cannot be one cell); it is the last column (after `Data source`) of `summary.csv` and `cohort.csv`.
- The `Data source` of the cohort Mean/SD rows of `within_lda` also says within-subject (derived from the subject rows).

## R11

No consultation of the answer-key repository.

Full suite (`.venv/bin/python -m pytest tests/ -q -o addopts=""`, run alone-ish; other builders were active): 1461 passed, 22 warnings in 820.39 s.
