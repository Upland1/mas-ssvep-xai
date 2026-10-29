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

### Pre-run audit additions (07_review.md c8ae9b7, round 2 PASS 1be5e3c; copied verbatim)

#### Noise units for the results review (P21 C-3, C-4)

The noise unit for subject s and accuracies A, B (1.0 s, `Acc (%)`) is SE_Δ = sqrt(SE_A² + SE_B²), with SE = 100·sqrt(p(1−p)/n) and n = windows (S01 680, S02 644, S03 661, S04 665, S05 679, identical to P22 `Windows`).

- **Material.** A difference is material only if |Δ| > 2·SE_Δ **and** |Δ| > the GNN cell's per-subject seed range (max − min of the three per-seed `Acc (%)` in `seeds.csv`). For a comparison with a P21 network, |Δ| must also exceed that network's per-subject range over seeds 42/43/44 (ccnn ≤ 5.12, eegnet ≤ 8.23 pp, P21 report §seed spread).
- **Tie.** Anything that is not material.
- **Scale.** At P22 lda accuracies, SE is 1.77 / 1.68 / 0.76 / 0.26 / 0.66 pp, so 2·SE_Δ ≈ 5.0 / 4.7 / 2.1 / 0.7 / 1.9 pp. Command: `.venv/bin/python -c` over `reports/loso_w1_p22_common/summary.csv` (the session above). S01 preview: GNN − lda = +1.62 pp, SE_Δ 2.48, seed range 3.8, so a tie. GNN − fbcca = +12.2 pp, SE_Δ 2.57, so material.

#### Pre-registered directional predictions (results review; written after seeing the previews above)

- **PR-1 (fbcca floor; F is an input).** No GNN LOSO method (4) is materially below `fbcca` LOSO on any subject. Each of the 4 cohort means is ≥ 82.40 % (P22 fbcca mean). nodes+F and nodes+coh+F pooled are materially above fbcca on S01 and S02.
- **PR-2 (vs lda LOSO).** No GNN LOSO pooled method is materially above `lda` on more than 1 subject. S03–S05 are ties or material losses of ≤ 3 pp (ceiling).
- **PR-3 (R-16, subjnorm ≥ pooled; paired: same seeds, same validation splits).** For each variant, `_subjnorm − pooled` is not materially negative on any subject, and the cohort-mean Δ is ≥ 0. A material gain appears on at least one of S01, S02 (lda_subjnorm − lda there: +5.59, +6.83). Every such gain is worded "offline upper bound".
- **PR-4 (R-15, coherence edges).** `nodes+coh+F − nodes+F` is a tie on ≥ 4 of 5 subjects in each protocol × norm. No material gain of the same sign appears on ≥ 3 subjects.
- **PR-5 (R-16, LOSO below within: not expected to hold uniformly for this model).** For each variant (pooled), within GNN is materially above LOSO GNN on at most 2 of 5 subjects, and S01 is a tie or LOSO ≥ within. If ≥ 3 subjects show a material within > LOSO, this prediction missed and the report says so. A tie is reported as "direction not observed; the within GNN is data-limited (N8)", never as "the GNN generalizes across subjects".
- **PR-6 (within GNN vs within_lda, common channels, matched).** `within_lda` is not materially below within GNN on any subject, and is materially above it on ≥ 2 subjects (expected S01, S02).
- **PR-7 (PF-30).** Every LOSO fold (20) has mean train accuracy ≥ 90 %. `Diagnosis` is "OVERFITTING" (train − test > 15 pp) on the S01 and S02 LOSO folds of every method. On S01/S02 LOSO folds, validation accuracy is above test accuracy. Any fold with train < 70 % (UNDERFITTING) is a bug candidate and is investigated before interpretation.
- **PR-8 (degenerate).** 0 degenerate LOSO folds (P21 networks: 0). Degenerate within folds, if any, occur only on S01/S02 and are listed with their flag.
- **PR-9 (seeds).** The per-subject seed range of every GNN LOSO cell is ≤ 8.23 pp. The ensemble `Acc (%)` is ≥ the mean per-seed accuracy − 1 pp in every cell.

#### Binding run-list items for the verifier (copy verbatim into 02_plan.md)

- **V1.** Before step 1: `reports/loso_gnn` and `reports/within_gnn` are absent. The run uses a clean verifier checkout at the post-F1 head, and its `git status --porcelain -- src scripts configs` is empty. The S01–S05 hash equals `e7f55081…bebab4` before and after (steps 0, 5).
- **V2.** All 70 fold configs (50 within + 20 LOSO) have `hyper.threads == 2`, `device == "cpu"` and `git_dirty == false`. There is exactly one `git_head` value across both out-dirs. Each command's log has exactly one invocation header (`GNN within:` / `GNN loso:` line). The suite runs alone, with `torch.get_num_threads()` recorded.
- **V3.** Counts:
  - `folds/`: 50 files in `reports/within_gnn` and 20 in `reports/loso_gnn`, and no `*.tmp`;
  - `folds.csv`: 50 and 20 rows;
  - within `summary.csv`: 2 methods × (5 subjects + Mean + SD);
  - LOSO `summary.csv`: 4 methods × 7 rows;
  - `seeds.csv`: 3 rows (seeds 42, 43, 44) per (method, subject).
- **V4 (window identity vs P22).** For each subject and GNN method, the set of `(trial_id, offset_sec)` in `predictions.csv` equals the `fbcca` set in `reports/loso_w1_p22_common/predictions.csv`, with counts 680 / 644 / 661 / 665 / 679. This holds for both out-dirs.
- **V5 (fold-config content).** Check one LOSO fold per norm and one within fold:
  - `fs == 256.0`;
  - `channels` equals the 7 `common` names in P22 order (PO3, POz, PO4, PO8, O1, Oz, O2);
  - `n_windows_train` equals the 4 training subjects' counts;
  - `build_git_commits` has 5 entries;
  - `config_hash` equals the sha256 of `configs/pipeline_config.yaml`;
  - `seeds == [42, 43, 44]`, `hyper.val_frac == 0.2`, `max_epochs == 150`, `patience == 25`.
- **V6 (seed mean).** For one LOSO fold npz per method, `max |proba − proba_seed.mean(0)| < 1e-6`.
- **V7 (labels).** Every `_subjnorm` row's `Normalization` contains "test-time" and "offline upper bound". Every within row's `Data source` contains "within-subject" and not ", LOSO,". `Protocol` is `within` / `loso` respectively.
- **V8 (resume and refusal, LOSO).**
  - After step 3, record the sha256 of the six CSVs and `gnn_loso_config.json`. This is the hash after the last write into `reports/loso_gnn`.
  - Rerun step 3 unchanged. Expected: exit 0, 20 `[skip]` and 0 `[+]` lines, identical hashes.
  - Then rerun step 3 with `--seeds 2`. Expected: non-zero exit, the message contains "use a new --out-dir", identical hashes.
  - If an interrupt check is done (optional, on step 2): after SIGINT, count the N fold files present. The resumed run must print N `[skip]` and 50 − N `[+]` lines, with no `*.tmp` left.
- **V9 (PF-30 table).** `05_run.md` lists all 70 `folds.csv` rows (Train, Val, Test, Train − Test, Best Epoch, Epochs Run, degenerate, Diagnosis) and the degenerate rows separately.
- **V10 (F1 check, at most 2 min).** After step 3, run `benchmark_gnn_loso` once more on `reports/loso_gnn` with the step-3 arguments but `--variants nodes+F --norm pooled`. Every fold must be `[skip]` and nothing may be refused. With fix (a), `summary.csv` must still hold all 4 methods; with fix (b), the notebook's final all-methods cell is the one that restores them. Then rerun step 3 unchanged, so that the final tables are the all-methods ones. The V8 hashes apply after this rerun: record them after it, not before.
- **V11.** The R11 log has no new P23 lines. The privacy scan of the staged diff and of each verify commit uses the guard's term list (by reference only).
- **V12 (optional, read-only on built folders).** For S01–S05, `load_subject(..., CLASS_CODES, "shared", ...)["cv_groups"] == ["trial_ids"]`. If they are equal, the GNN within test folds coincide with `within_lda` repeat 0 (N9).

Order: 0, 1, 2, 3, V8, V10, then the final unchanged rerun of 3 and the V8 hashes, then 5. Measured total ≈ 20 min, worst case ≈ 28 min, within budget.

#### Reporting rules for the results review and the scribe

- **RR-1.** Per subject, report 1.0 s and 2-tap smoothed accuracy with `Data source`, `Protocol` and `Normalization`. LOSO and within go in separate tables (R9).
- **RR-2.** The comparison table, all on `common` (7 channels):
  - GNN rows: the seed ensemble, plus the per-seed mean and range from `seeds.csv`;
  - P22 `reports/loso_w1_p22_common/summary.csv`: `fbcca`, `lda`, `lda_subjnorm`, `within_lda`;
  - P21 `reports/loso_w1_s01-s05{,_seed43,_seed44}/summary.csv`: `ccnn` and `eegnet`, mean and range over seeds 42/43/44, and `compact_eegnet` labelled as a single seed.
  - Network-vs-GNN claims use per-seed means (N2).
- **RR-3.** `_subjnorm` and `lda_subjnorm` are always "test-time normalization, offline upper bound". There is no online GNN claim (P22 C-4: K ≤ 2 loses 17–25 pp, and K = 10 is the first tie).
- **RR-4 (PF-30).**
  - Chance is 20 %.
  - High train with low test is a generalization problem (subject shift). Since the validation trials come from the training subjects (N3), high val accuracy does not contradict it.
  - Train < 70 % would be an optimization problem.
  - Never present a high training accuracy as evidence of model quality.
- **RR-5.** The P22 `within_lda` rows are relabelled within-subject (N4). `within_lda` is 5 split repeats and the GNN within value is 1 split × 3 seeds (N9).
- **RR-6.** R-15 (legacy, fs 250, legacy folders, S02/S03/S05 only) is quoted for direction only ("coherence edges do not help"), never as a numeric target. R-16 directions are reported as "holds", "tie" or "direction not observed".
- **RR-7.** If any coherence values (not accuracies) are interpreted, R4 applies: per-window 3-segment MSC is biased upward (≈ 1/3 for independent channels).


#### Round 2 amendments (verbatim)


Scope, as set in round 1: F1, its test, and `git diff 4a4799f -- src scripts tests configs notebooks` (head 3b740ed).

What changed since 4a4799f in code and tests:
- `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py`, MODIFIED in fe2bf94;
- `tests/test_p23_gnn_loso.py`, +1 test, in e7c4bf2;
- nothing else in `src/`, `configs/` or `notebooks/`. The notebook is unchanged and needs no change under route (a).

| Item | Result | Evidence |
|---|---|---|
| F1 fix | PASS | `stored_specs(out, protocol)` reads the config of every `*__<protocol>__test-*.npz` in `folds/` (`benchmark_gnn_loso.py`, new function before `collect`). `build_outputs` collects all stored methods. Methods of the current invocation (`requested`) still go through `L.check_fold`, which raises SystemExit. Other stored methods are compared with `L.fold_problem` and left out with `[warn] …; left out` on any difference. This is the same contract as `benchmark_loso.build_summary` (`benchmark_loso.py:613-630`). Fold-count guards unchanged. |
| Configs of non-requested methods | PASS | `config_of(spec, s, f)` builds the expected config from the stored spec (variant, norm, method, normalization label) and the current shared arguments. A stored method made with other seeds, hyperparameters, threads, device or code is therefore refused and left out, not mixed in (PF-37). |
| Side changes | PASS | The `Seeds` cell now comes from the stored fold config, not the current args. That is correct once foreign methods are summarized. `gnn_loso_config.json` drops `variants`/`norms` and adds `methods_in_outputs` and `this_invocation`. It is a run-description file, not read back by any check. No change to fitting, normalization, splits, smoothing or fold configs, so the round-1 rule rows stand. |
| Test fails on the bug | PASS | `test_two_invocations_into_one_out_dir_keep_both_methods_in_every_csv` runs pooled, then subject, into one out-dir. It requires both methods in summary (rows and Mean), predictions, confusion, folds, seeds and per_subject, plus the "use a new --out-dir" refusal for a requested method with another seed count. Builder: 1 failed on the pre-fix script (`03_changes_deep-learning.md`, Fix round 1). Own run: `pytest tests/test_p23_gnn_loso.py tests/test_p23_independent_known_answer.py tests/test_p23_notebook.py -q -o addopts="" -p no:cacheprovider` → `52 passed in 36.49s`. |
| Suite alone | PASS | `1513 passed, 22 warnings in 853.91s (0:14:13)` (last line of `mas/state/scratch/p23_dl_suite2.log`), i.e. 1512 + 1 new test. |
| R11, privacy | PASS | No new reference-access lines. The guard's term list (by reference) gives 0 hits in each of 4db28fc, fe2bf94, e7c4bf2, aff341f, 3b740ed, and 0 in the net `git diff main..HEAD`. |

Non-blocking:
- **N10.** The branch "stored method with another configuration is left out with a warning" has no dedicated test; only the refusal of a requested method is tested. It is a copy of the `benchmark_loso` contract, so the verifier item below covers it on real outputs.
- **N11.** The round-1 V10 is now a positive check. The V8 hashes should cover the six CSVs only, because `gnn_loso_config.json` now records `this_invocation` and legitimately differs between the V10 run and the full rerun.

Amendments to the binding items (copy into 02_plan.md together with round 1's):
- **V8 (amended).** Hashes = sha256 of `summary.csv`, `per_subject.csv`, `predictions.csv`, `confusion.csv`, `folds.csv`, `seeds.csv`. `gnn_loso_config.json` is excluded.
- **V10 (amended).** Run on `reports/loso_gnn` with `--variants nodes+F --norm pooled` and the step-3 arguments otherwise unchanged. Expected:
  - 5 `[skip]`, 0 `[+]`, no `[warn] … left out`, exit 0;
  - the six CSV hashes equal the V8 hashes taken after step 3;
  - `summary.csv` holds all 4 methods.
  Any difference is an anomaly in `05_run.md`. The final unchanged rerun of step 3 then follows as in round 1.

Predictions PR-1..PR-9, binding items V1–V7, V9, V11, V12 and reporting rules RR-1..RR-7 of round 1 stand unchanged. No result has been seen since round 1.

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
