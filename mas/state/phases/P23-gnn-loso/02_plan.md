# P23 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Train the edge-gated connectivity GNN of P15 under leave-one-subject-out, with a
within-subject reference on exactly the same windows and channels. Report it next to the
`benchmark_loso.py` rows (fbcca, lda, lda_subjnorm, networks) and interpret
train-high / test-near-chance patterns (PF-30).

## Data source

- Built folders `data/processed_continuous/w1_s0.25/<S>/`: session OO, quality source both,
  banks fbcca and fbcsp. These are the P20–P22 folders, hash pin `e7f55081…bebab4`, unchanged.
- Cohort S01–S05, given explicitly with `--subjects` (B003 amended). The cohort-5 channel
  choice of P21/P22 applies:
  - `common` = 7 channels without PO7;
  - `all` = 8 channels.
- The P15 legacy cache (`data/processed/<S>/graph_dataset.npz`, fs 250) is **not** used.

## Settled points (inferred; recorded in decisions.md)

1. **Era C graph features (P23.1, connectivity-stats).**
   - Same definitions as P15 (`src/features/connectivity/connectivity_graph_features.py`):
     - node band power, 10 per node: fundamental and 2nd harmonic × 5 targets;
     - edge coherence, 5 per edge;
     - edge phase as cos/sin of the cross-spectral phase, 5 × 2.
   - Computed **in memory per subject**, on the built folder's clean stimulus windows of
     the chosen channels, i.e. the continuously filtered windows `X_windows` (R3).
   - fs comes from `load_subject(...)["fs"]` (256), never `LEGACY_FS_HZ`. The phase is
     taken from the windowed cross-spectrum (R3).
   - A new entry point (e.g. `graph_features_for_subject(d, channels)`) returns arrays
     aligned row by row with `load_subject`'s windows, trial ids and offsets, plus the
     FBCCA scores from the built folder.
   - The legacy cache path and its 250 Hz default stay untouched (frozen P15 behaviour).
   - Layout `(n, C, C, 5[, 2])` and the upper-triangle flattening are proven by a
     synthetic test (R6).
   - Coherence here is a per-window edge **feature**, not a stimulus-vs-baseline estimate,
     so R4 concatenation does not apply. The write-up states this.
2. **Variants and norms.**
   - Variants as P15. The default is `nodes+F nodes+coh+F` (F = FBCCA scores).
   - `--norm pooled`: each input array is z-scored with statistics of the training
     subjects' windows only (R2).
   - `--norm subject`: each subject's arrays are z-scored with that subject's own
     statistics, without labels. That includes the held-out subject's whole session, so
     it is the offline upper bound (PF-35, P22 C-4).
   - Method names are `gnn_<variant>` and `gnn_<variant>_subjnorm`. Each CSV row carries
     a `Normalization` column with the R2 label (P22 C-3).
   - Under `--protocol within` only `pooled` runs, because subject normalization is a
     no-op there.
3. **`fit_gnn` (deep-learning).**
   - Early stopping on 20 % of the training **trials**, grouped by offset trial ids
     (PF-32, PF-33). It never uses the held-out subject.
   - `--val-frac 0` gives fixed epochs.
   - Patience 25, max 150 epochs, AdamW (lr 1e-3, wd 1e-2), cosine schedule, label
     smoothing as in P15.
   - `--seeds 3` per fold: seeds 42, 43, 44, deterministic per (fold, seed) (PF-28).
     Fold probability = mean of the seeds' softmax. Per-seed accuracies are kept too
     (P21 C-4 noise floor).
   - Per-seed train/val accuracy, best epoch and epochs run are logged. A fold is flagged
     degenerate by P20 C-2: best epoch ≤ 5, or train accuracy < chance + 10 pp.
4. **Protocols.**
   - `--protocol loso`: the subject is held out; training uses the other 4 subjects.
   - `--protocol within`: `StratifiedGroupKFold(5, shuffle, 42)` over true trial ids
     inside each subject, on the same windows and channels. Validation for early
     stopping uses 20 % of that fold's training trials.
   - Summary column `Protocol`. Within rows' `Data source` says "within-subject" (P22 C-6).
5. **Resumable folds (PF-37, P21 C-1, P22 C-1).**
   - Folds are saved to `<out-dir>/folds/<method>__<protocol>__test-<S>[__fold-k].npz`
     with a JSON `config`.
   - The config holds:
     - channels, subjects, variant, norm, protocol, seeds, hyperparameters, val-frac;
     - training-subject window counts;
     - each built folder's meta `git_commit`;
     - the `--config` file hash;
     - git head and dirty flag, recorded once at process start.
   - A mismatch is refused with "use a new --out-dir". The `check_fold` and
     `code_changed` logic of `benchmark_loso.py` is reused, not duplicated.
6. **Outputs.**
   - Files: `summary.csv` (columns as `benchmark_loso.py` plus `Protocol`,
     `Normalization`, `Seeds`, `Seed SD`), `per_subject.csv`, `predictions.csv`,
     `confusion.csv`, `folds.csv`.
   - 2-tap smoothing within trial (R8); ITR with N = 5 and T = 1.5 s.
   - Default out-dirs: `reports/loso_gnn/` and `reports/within_gnn/`.
   - Never resume into P21 out-dirs (P22 C-5).
7. **Smoke test (`--smoke-test`).**
   - 4 synthetic subjects with different gain and noise; 2 variants × 2 norms.
   - The within protocol also runs.
   - A rerun must skip every fold, and the mean synthetic LOSO accuracy must be > 40 %.
   - It writes to a scratch out-dir, never to the default out-dirs.
8. **ml-engineer carry-forwards (P22 C-1, C-3, C-6), small and isolated in
   `benchmark_loso.py` / `benchmark_loso_warmup.py`:**
   - fix the `code_changed` docstring (it now covers configs);
   - pass `P["groups"]` to `within_lda`;
   - add the R2 `Normalization` label to the warm-up CSV;
   - make the `within_lda` Data source say within-subject.
   - Outputs of P22 are not regenerated. The changed strings apply from P23 runs on.
9. **Notebook section 10b (data-signal).**
   - Cells in `notebooks/loso_colab.ipynb`: GNN smoke test, within reference and LOSO,
     one variant × norm per cell, resumable, with expected runtimes from the measured smoke.
   - The structure test is extended.
   - The notebook is committed without outputs.

## Work split (sequential: same checkout, shared files)

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | connectivity-stats | MODIFIED `src/features/connectivity/connectivity_graph_features.py` and/or NEW `src/features/connectivity/graph_inputs.py`, NEW `tests/test_p23_graph_features.py` | P23.1; settled 1 |
| 2 | ml-engineer | MODIFIED `scripts/benchmarks/benchmark_loso.py`, `scripts/benchmarks/benchmark_loso_warmup.py`, their tests | settled 8 |
| 3 | deep-learning | NEW `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py`, MODIFIED `src/models/graph/` only if needed, NEW `tests/test_p23_gnn_loso.py` | P23.2; settled 2–7 |
| 4 | data-signal | MODIFIED `notebooks/loso_colab.ipynb`, `tests/test_p21_notebook.py` (or NEW `tests/test_p23_notebook.py`) | P23.3; settled 9 |

Each builder smoke-runs (synthetic, or one fold, under 5 min), measures, and runs the
full suite alone.

## Methodological risks

| Rule / PF | Risk | Guard |
|---|---|---|
| R1, PF-32/33 | held-out subject in validation or pooled stats | offset ids; sentinel test on the held-out subject; asserts |
| R2, PF-35 | `pooled` stats include the test subject; `_subjnorm` mislabelled | sentinel/permutation tests; Normalization column |
| R3 / fs | legacy 250 Hz or unfiltered per-window path reused silently | test: a planted 15 Hz sinusoid at fs 256 lands in the 15 Hz band bins; fs read from meta |
| R6 | edge-array layout or flattening wrong | synthetic coupling: coupled pair → coherence ≈ 1 at that edge only; upper-tri index proof |
| PF-28 | nondeterministic variant comparison | same seeds per (fold, seed) across variants; bit-identical rerun test on CPU |
| PF-30 | train ≈ 100 % / test ≈ chance read as success | report train/val/test per fold and the diagnosis column |
| PF-37 | mixed configs | refusal tests for every config key |

## Tests required (known answers)

1. Graph features at fs 256:
   - a planted frequency lands in its band bins;
   - a coupled pair gives coherence ≈ 1 and a known phase lag gives a known cos/sin,
     on that edge only;
   - independent channels give coherence near the small-sample floor;
   - rows are aligned with `load_subject`'s windows and trial ids.
2. Pooled normalization: a sentinel in the held-out subject leaves training statistics
   and weights bit-identical (CPU, 1 thread).
3. `_subjnorm`: permuting the held-out subject's labels leaves its normalized arrays and
   probabilities unchanged.
4. Validation groups never contain the held-out subject, and the within protocol never
   splits a trial.
5. Seed averaging: fold probability = mean of the per-seed softmax; a rerun is
   bit-identical (CPU).
6. Resume: interrupt, then rerun skips the finished folds; a config change is refused.
7. Smoke test acceptance (> 40 % mean synthetic LOSO, every fold skipped on rerun).
8. Each fix test fails on the bug it guards.

## Run commands (for the verifier; runtimes to be replaced by measurements)

```bash
P=".venv/bin/python -m"
S="--subjects S01 S02 S03 S04 S05"
# 0. hash S01–S05 built folders (must equal e7f55081…bebab4); out-dirs absent; clean worktree
# 1. smoke test
$P scripts.connectivity.graph_modeling.benchmark_gnn_loso --smoke-test --out-dir <scratch>
# 2. within reference, pooled, both variants, 3 seeds
$P scripts.connectivity.graph_modeling.benchmark_gnn_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --channels common --variants nodes+F nodes+coh+F --norm pooled --protocol within --seeds 3 --threads 2 --device cpu --out-dir reports/within_gnn
# 3. LOSO, both variants × both norms, 3 seeds
$P scripts.connectivity.graph_modeling.benchmark_gnn_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 $S --channels common --variants nodes+F nodes+coh+F --norm pooled subject --protocol loso --seeds 3 --threads 2 --device cpu --out-dir reports/loso_gnn
# 4. resume check on 3 (interrupt + rerun; summary/per_subject/predictions/confusion hashes unchanged)
# 5. hash S01–S05 (after)
```

**Measured (builders' handoffs, 2026-10-29).**
- Graph features: 0.2–0.3 s per subject.
- Smoke test: 35 s on 2 threads.
- One fold, `--threads 2` on CPU: LOSO 36.7 s; within 8.9 s.
- Full run, CPU, 2 threads: within ≈ 7.4 min (50 folds), LOSO ≈ 12.2 min (20 folds), so
  ≈ 20 min in total; worst case (every seed at 150 epochs) ≈ 28 min.
- Every run is pinned to `--threads 2 --device cpu`, since both are part of the fold
  config.
- Suite ≈ 14.3 min, run alone.

**Budget.**
- The roadmap gives about 45 min (LOSO) + 30 min (within) on 2 CPU cores for 5 subjects,
  3 seeds and 2 variants. With the local GPU or 12 cores it should be less.
- The deep-learning builder measures one fold per protocol. If the estimate exceeds 120
  min, the verifier runs within and one variant × norm locally, and records the rest
  under Sebastian's standing preference: over-budget local runs go detached and
  resumable, with his authorisation recorded per phase.

## Acceptance checks (for the verifier)

1. The smoke test passes: > 40 % mean synthetic LOSO, every fold skipped on rerun, the
   within protocol runs.
2. Within and LOSO tables for both variants and both norms (within: pooled only), per
   subject, with data source, Normalization and Protocol.
3. They are placed next to `benchmark_loso.py` rows on the same channels: P22
   `reports/loso_w1_p22_common` for fbcca, lda, lda_subjnorm and within_lda; P21
   `reports/loso_w1_s01-s05` and seeds for the networks.
4. Train ≈ 100 % / test ≈ chance patterns are listed per fold (PF-30).
5. A config change on an existing out-dir is refused; the resume check passes.
6. S01–S05 hash unchanged; suite passes alone; R11 log; privacy scan of the staged diff
   with the guard's term list (by reference only).

## Sources

- `mas/03_ROADMAP.md` P23 and P15.
- `mas/05_PITFALLS.md` PF-28, PF-30, PF-32..PF-37.
- `mas/04_REFERENCE_RESULTS.md` R-15, R-16.
- `mas/state/decisions.md` P21 and P22 carry-forwards.
- `src/features/connectivity/connectivity_graph_features.py`, `src/features/connectivity/graph_dataset.py`.
- `scripts/connectivity/graph_modeling/benchmark_gnn.py`.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
