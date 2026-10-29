# P22 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Branch: phase/P22-loso-extensions; commits efe635c (feat loso), 9665181 (test), 63b1527 (feat warm-up), e1d696c (test)

## Files

| Path | State | What |
|---|---|---|
| `scripts/benchmarks/benchmark_loso.py` | MODIFIED | `within_lda`; `--channels common\|all\|<names>`; `--folds`, `--within-repeats`, `--partial-mean`; `check_fold`/`fold_problem`/`code_changed`; git head + dirty flag once per process (`capture_run_state`); fold-count guard (`Folds` column); `--allow-config-mismatch` removed; helpers `lda_features`, `lda_pipeline`, `within_splits`, `parse_channels`, `leave_out_for_names`; `pool` also returns `starts` |
| `scripts/benchmarks/benchmark_loso_warmup.py` | NEW | warm-up study |
| `tests/test_p22_loso_extensions.py` | NEW | 30 tests |
| `tests/test_p22_warmup.py` | NEW | 12 tests |
| `tests/test_no_leakage.py` | MODIFIED | R1 registry: `within_splits` added to LEAK_FREE, benchmark_loso.py registered as leak-free splitter file |
| `tests/test_p21_loso.py` | MODIFIED | removed-flag use: the old "reuse with flag" assert became "argparse rejects the flag" |
| `tests/test_p21_independent_known_answer.py` | MODIFIED | the planted `git_head = "deadbeef"` is now refused (P22.3, by design); then the current head is accepted |

## Final CLIs

```
python -m scripts.benchmarks.benchmark_loso --data-root D --window 1 --stride-sec 0.25 --subjects S01 .. \
  --methods fbcca lda lda_subjnorm within_lda [ccnn compact eegnet] --channels common | all | NAME [NAME ...] \
  --folds 5 --within-repeats 5 [--partial-mean] --out-dir OUT [--seed 42 ...]
python -m scripts.benchmarks.benchmark_loso_warmup --data-root D --window 1 --stride-sec 0.25 --subjects S01 .. \
  --warmup-trials 1 2 5 10 --channels common | all | NAME ... --out-dir OUT [--seed 42 --config ...]
```

## Behaviour (as settled)

- `within_lda`: per subject, `StratifiedGroupKFold(5, shuffle, 42+r)`, r<5, groups = true trial ids (`within_splits`, asserts R1); each fold = the `lda` pipeline (`lda_loso_fold`: CSP m=1 in-fold + FBCCA, scaler, shrinkage LDA). The fold file stores `proba_rep` (repeats, n, K); summary Acc = mean over repeats, Acc SD = SD (ddof 1), Runs = repeats; predictions/confusion use repeat 0. Config `train_subjects = [S]`, same `channels` as LOSO.
- `--channels <names>`: validated against the montage; subjects whose gate dropped any named channel are left out and printed (`[-] Leaving out S01: gate dropped PO7`, `[=] Keeping ...: gate dropped ...`); fewer than 2 left is an error (SystemExit). Order kept; `loso_config.json` and fold configs carry the cohort actually used.
- Fold config adds `git_head`, `git_dirty` (src/scripts/configs), recorded once at process start. `check_fold` refuses any key difference except `data_root`; a head difference is refused only if `git diff --stat h1 h2 -- src scripts` is non-empty or a head cannot be resolved; equal heads with a different dirty flag are refused (both dirty at the same head: accepted, cannot be decided). Message: "...configuration differs {diff}...; use a new --out-dir".
- Fold-count guard: a method with fewer fold files than the cohort gets `[warn]`, `Folds` below the cohort, empty Mean/SD, "INCOMPLETE" in Data source (per_subject Mean/SD NaN as well). `--partial-mean` overrides.
- Warm-up std guard: fewer than 2 warm-up windows gives std 1 for all features (centring only); features with std < 1e-12 get 1; reported in `Std guard`. Extra columns after the section 6 ones: 2-tap accuracies, binomial SE of each accuracy (P21 C-3), `warmup - full`, `warmup - none`, class codes.

## How the recording order is obtained

Built folders store `window_starts.npy` = start sample of every window in the continuous recording (01_DATA_SPEC 5.2; `load_subject` returns it as `window_starts`). A trial's recording rank = the smallest `window_starts` among its loaded (valid) windows; ties by id. Trial ids are never used for the order. Proof: a planted layout where ids are in class order and the recording order is 3,0,5,1,4,2 (`test_recording_order_...`); the K-set equals the first K recorded trials and differs from the first K ids; the end-to-end test recomputes the order from the synthetic folder's own `y_labels/trial_ids/window_starts/valid_mask` files. On the real S01-S05 folders the order differs from the id order (`recording_order.csv`; S01 recording ids 88, 89, 96, 104, 80, 112 vs ids 80, 81, ...). Caveat: if a trial's first window was rejected, its rank uses its first valid window (a shift of at most a few windows; trials are at least 15 s apart).

## Measured times (this machine, CPU, S01-S05, w1_s0.25)

| Command | Wall |
|---|---|
| LOSO fbcca lda lda_subjnorm within_lda, `--channels common` -> `mas/state/scratch/p22/common` | 31.4 s (within_lda 3.3-3.9 s per subject) |
| same, `--channels all` -> `.../all2` | 36.2 s |
| same, `--channels PO7 PO3 POz PO4 PO8 O1 Oz O2` -> `.../names` | 10.7 s (keeps S02, S05; leaves out S01, S03, S04, gate dropped PO7) |
| refusal: rerun of common with `--seed 43` into the same out-dir | exit 1 at the first fold, "configuration differs {'seed': (42, 43)} ...; use a new --out-dir"; md5 of the fold files unchanged; rerun with the same settings: 20 `[skip]` |
| `benchmark_loso_warmup --warmup-trials 1 2 5 10 --channels common` -> `.../warmup` | 6.7 s |
| `pytest tests/ -q -o addopts=""` alone | 1403 passed in 849 s (0:14:09); log `mas/state/scratch/p22/full_suite.log` |
| the two P22 test files | about 5 s each |

Smoke numbers (records, not targets): common cohort Mean Acc fbcca 82.40, lda 87.61, lda_subjnorm 90.03, within_lda 90.79 (SD over repeats 0.41, cohort row). Warm-up (common), cohort Mean `warmup - full` pp: K=1 -27.27, K=2 -19.16, K=5 -5.46, K=10 -0.91; `warmup - none`: -25.03, -16.95, -3.11, +1.59 (`mas/state/scratch/p22/warmup/cohort.csv`). K=1 warm-up contains one class only, hence the large loss.

## Mutation checks (bug -> test that fails)

Whole-session stats as "warm-up" stats -> 2 warm-up tests; id order instead of recording order -> 3; `code_changed` always False -> check_fold head test; window-level splitter in `within_splits` -> 8 tests; dirty flag ignored -> check_fold head test.

## Deviations and notes

1. P21 tests changed in two places (flag removal; `deadbeef` head now refused by design). The `test_no_leakage.py` registry was extended (the splitter import in benchmark_loso.py requires it).
2. `--partial-mean` is an addition (settled point 4 says "by default").
3. `Folds` column added to summary.csv (SUMMARY_COLUMNS changed).
4. The dirty flag looks at `src scripts configs` only; two runs from the same dirty head are accepted (content may differ): run from the clean verifier worktree (P21 C-1).
5. Smoothed and SE columns are appended after the section 6 columns. `loso_config.json` gains git_head, git_dirty, folds, within_repeats.
6. The warm-up script is single-pass, not resumable (6.7 s).
7. End-to-end tests use `--folds 2 --within-repeats 2` on 10-trial synthetic subjects.

## R11 consultations

None. The reference directory was not opened.

## Sources opened

mas/03_ROADMAP.md P22, mas/05_PITFALLS.md PF-34..37, mas/02_REQUIREMENTS.md section 6, mas/state/decisions.md P21 rows, 00_assignment.md, 02_plan.md, scripts/benchmarks/benchmark_loso.py, src/io/subject_data.py, P21 tests, tests/test_no_leakage.py. No raw recording or .ebr access; only built folders, read by project scripts.
