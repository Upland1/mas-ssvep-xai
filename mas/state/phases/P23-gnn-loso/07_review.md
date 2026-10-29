# P23 · 07 · Scientific review

Status: READY (pre-run audit round 1)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_* (4), 04, log.md; `git diff main -- src scripts tests configs notebooks` (branch head 4a4799f); mas/RULES.md; PF-28, PF-30, PF-32..PF-37; R-15, R-16; decisions.md P20 C-2/C-3, P21 C-1..C-6, P22 C-1..C-6, P23 rows; mas/state/reports/P21.md, P22.md; `reports/loso_w1_p22_common/`, `reports/loso_w1_s01-s05{,_seed43,_seed44}/` (summary.csv, loso_config.json, read only)

## Pre-run audit — Round 1

Builder numbers seen before writing the predictions (so these predictions are plausibility checks, not blind tests): the real single-fold previews in `03_changes_deep-learning.md` (LOSO held-out S01, nodes+coh+F pooled 70.88 %, seeds 69.7 / 70.3 / 66.5, train 98.3 %, best epoch 81; within S01 fold 0 69.93 %, train 90.0 %), the synthetic smoke (87.97 %), and the per-subject FBCCA argmax accuracies in `03_changes_connectivity-stats.md` (0.587 / 0.680 / 0.911 / 0.988 / 0.954; these equal the P22 `fbcca` LOSO rows 58.68 / 68.01 / 91.07 / 98.80 / 95.43, so the `F` input is the same FBCCA score).

Own checks, read only: the P23 test files plus the P21/P22 tests they touch, `pytest tests/test_p23_*.py tests/test_p21_notebook.py tests/test_p22_loso_extensions.py -q -o addopts="" -p no:cacheprovider` gave `110 passed in 42.16s`. `reports/loso_gnn` and `reports/within_gnn` do not exist. `mas/state/scratch/reference_access.log` has no entry after 2026-10-28T07:41 (P19 scribe), so there was no R11 access in P23. Privacy scan of `git diff main..HEAD`, every branch commit and the commit messages, using the guard's term list built from fragments: 1 hit, in 1519dd5. It is the template checklist row of this file, which names the recording-file suffix. This rewrite removes it (see N7).

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | LOSO: `L.loso_split` + assert of disjoint offset groups `benchmark_gnn_loso.py:289-291`; validation never contains the held-out subject `:294-296`; within: `L.within_splits` (StratifiedGroupKFold(5, shuffle, 42) on `P["groups"]`, offset `cv_groups`, `benchmark_loso.py:240,318-323`) `benchmark_gnn_loso.py:507-511`, assert `:287`; early-stopping split `training.split_validation` = first split of StratifiedGroupKFold(5) over the training rows' groups `src/models/cnn/training.py:79-84`, disjointness asserted `benchmark_gnn_loso.py:171-173`. Tests: `test_validation_excludes_heldout_subject_and_splits_by_trial_in_every_loso_fold`, `test_within_folds_never_split_a_trial_and_cover_each_window_once`. |
| R2 Fit only in-fold (incl. test-time exception) | PASS | pooled: `standardize_fold(inp, tr, te)` fits on `tr` only (`graph_inputs.py:86-105`, `benchmark_gnn_loso.py:140-141`); subject: `subject_standardize` per subject over its own rows with no labels (`:123-133`). It is labelled in the method name (`_subjnorm`, `:107-108`), in `NORM_LABEL["subject"]` ("test-time normalization, offline upper bound: the held-out session is in the statistics; R2 exception, PF-35", `:96-100`), in the `Normalization` column (`:414,433`) and in the fold config `:268`. Refused under within `:624-625`. Sentinel / label-permutation tests are bit-exact (`04_tests.md` rows 7-9). Pooled statistics include the training subjects' validation rows (N1; not a test leak). |
| R3 Filter continuous, then window | PASS | `graph_features_for_subject` refuses non-built folders, `fs_source == "legacy-assumed"` and `filter_mode != "continuous"` (`src/features/connectivity/graph_features_subject.py:59-67`), and filters nothing. The P15 estimators only apply a Hann window and FFT/Welch (`connectivity_graph_features.py:56-112`, no `filtfilt`/Hilbert). Phase = angle of the band-summed cross-spectrum `sum X_i conj(X_j)` (`:96-112`). fs = `d["fs"]` (`graph_features_subject.py:68`); FBCCA references from `d["fs"]` (`:44`); fs 250 mutants killed (`04_tests.md`, mutation table). |
| R4 Estimator small-sample bias | N/A (as stated) | Per-window 3-segment Welch MSC is a model-input edge feature, not a stimulus-vs-baseline coherence estimate. The module docstring says so and states the upward bias (`graph_features_subject.py:16-17`), and the harness docstring repeats it (`benchmark_gnn_loso.py:7`). No connectivity claim is made from these numbers. If the write-up interprets coherence values (rather than accuracies), R4 applies again (RR-7). |
| R5 Shared quality decision, explicit thresholds | PASS | `L.load_cohort(..., thresholds, channel_fail_fraction, ...)` and the second read `load_subject(root/S, CLASS_CODES, "shared", bands=("fbcca",), thresholds=thresholds, channel_fail_fraction=..., channels=chosen)` take every threshold from the config (`benchmark_gnn_loso.py:527-536`). Row equality of y, trial ids and FBCCA between the two reads is asserted (`:538-539`). |
| R6 Index layouts verified | PASS | `(n, C, C, 5[, 2])` and `upper_tri_flat` order `(pair*5+k)*2+c` are proven with coded values and a coupled edge (`tests/test_p23_graph_features.py:96`, independent `test_upper_tri_layout_flat_columns_follow_triu_pair_major_order`). Row alignment with `load_subject` is tested on a real synthetic build (`:120`). Pooled row order = `L.pool` order, asserted `benchmark_gnn_loso.py:497-498`. Within re-assembly checks coverage `:339-344`. |
| R7 Honest statistics | N/A | No hypothesis test. Directional margins in noise units below (P21 C-3). |
| R8 Smoothing respects trials | PASS | `L.smooth_two_tap(proba, trial_id, offset)` per fold/subject (`benchmark_loso.py:551`, used via `fold_rows` and `seed_table` `benchmark_gnn_loso.py:391`). Brute-force test with shuffled rows and trials of unequal length (`test_two_tap_smoothing_...whatever_the_row_order`). |
| R9 Per-subject reporting with data source | CONCERN → see F1 | The harness writes per-subject rows with `Data source`, `Protocol` and `Normalization`. Within rows go through `within_source` (`:632`). In the notebook route, however, the per-subject table of three of the four LOSO methods is lost (F1). |
| R10 Sources cited | PASS | Each handoff lists only files opened in its run; no external source claimed. |
| R10 Copied lines marked | N/A | No copied code. |
| R11 Reference after an attempt | PASS | All four handoffs and 04 say "none". The access log has no P23 entries. |
| Golden rule 3: legacy labelled, reachable | PASS (no legacy prescribed) | `connectivity_graph_features.py`, `graph_dataset.py`, `graph_inputs.py`, `benchmark_gnn.py` are unchanged vs main (empty `git diff --stat`). The 250 Hz default is pinned by `test_legacy_cache_default_stays_250` (`tests/test_p23_graph_features.py:170`). |
| Tests cover every change; ≥ 1 fails on the historical bug | PASS with one gap | 22 + 9 + 8 + 8 builder tests and 21 independent tests. 18/18 independent mutants and every builder mutant were killed (fs 250, pooled over all rows, last-seed proba, per-window val groups, StratifiedKFold within, dropped config keys, within Data source says LOSO, trial ids to within_lda). Gap: no test runs two invocations with different `--variants/--norm` into one out-dir (F1). |
| Changes match 02_plan.md and the roadmap tasks | FAIL (F1) | Settled 1-8 are implemented as written, and the accepted deviations (threads/device in the config, `--only-test/--only-fold`, the second read, Acc SD = Seed SD, seeds.csv) are harmless. Settled 9 (notebook 10b, "one variant × norm per cell, resumable") does not produce the result tables the section promises (F1). |
| No data, recording files, local tooling files or tool/vendor names in the diff | PASS after this commit | The only hit is the template row in 1519dd5 (N7). The code, tests and notebook are clean. |

### Era C specifics checked

- **Graph features.** They are the same three P15 estimators, with no new code path. The windows are `d["X"]`, the continuously filtered clean stimulus windows of the chosen channels (classes 101–105, `load_subject(..., CLASS_CODES, "shared", ...)`). At fs 256 the Welch grid is 2 Hz (nperseg 128). For 10.91 Hz and 8.57 Hz the ±1 Hz band holds a single bin (10 Hz and 8 Hz). This is coarse but is the P15 definition, and the node and phase features use the 1 Hz full-window grid.
- **`fit_gnn`.** The validation split depends on the seed (`split_validation(yi, groups, val_frac, seed)`), so the seed spread includes validation-partition variance. It is identical across variants and norms for the same seed and fold, which makes variant/norm comparisons paired (PF-28). `torch.manual_seed(seed)` comes before `make_model`, and batches use their own `Generator(seed)` (`:178-185`). The best-val-loss state is restored, and train accuracy is measured in eval mode on the fitting rows only (PF-30 asks for un-augmented training accuracy; there is no augmentation). Degenerate flag P20 C-2 (`L.is_degenerate`, `:248`).
- **Provenance / resume.** `capture_run_state()` runs once at process start (`:703`). The fold config carries threads, device, seeds, every hyperparameter, `n_windows_train`, `build_git_commits`, `config_hash`, `git_head`, `git_dirty` (`:257-277`). `L.check_fold`/`fold_problem` are reused (`:322,374`); `CODE_PATHS = DIRTY_PATHS = (src, scripts, configs)` (`benchmark_loso.py:109-110`). Saves are atomic (`save_fold`). The interrupt test leaves no `.tmp`.
- **ml-engineer carry-forwards.** P22 C-1 fields are in `benchmark_loso.fold_config`. N2: `within_lda_fold` receives `P["groups"]`. For classes 101–105 `cv_groups == trial_ids` (the PF-13 merge only touches 202 windows, `src/io/subject_data.py:195-201`), so the within_lda splits are unchanged. N8: the docstring is fixed. C-3: the warm-up `Normalization` column says "test-time … offline upper bound / online". C-6: the within_lda `Data source` goes through `within_source`. Side effect, intended: existing P21/P22 `benchmark_loso` out-dirs are now refused on resume because of the new config keys (N5).
- **Notebook 10b.** It is placed between step 10 and step 11, has no outputs, uses its own out-dirs asserted ≠ the P21 ones, and pins `--threads 2 --device cpu`. The `_subjnorm` cells are labelled offline upper bound. Defect F1.

### Required fixes

1. **F1 (deep-learning; data-signal for the notebook text and test). R9 / settled 9 / P20 out-dir lesson.**
   - **Bug.** `run_and_report` builds outputs only for the methods of the current invocation, and `write_outputs` then overwrites `summary.csv`, `per_subject.csv`, `predictions.csv`, `confusion.csv`, `folds.csv` and `seeds.csv`:
     - `make_specs(args.variants, args.norm)` at `scripts/connectivity/graph_modeling/benchmark_gnn_loso.py:629`;
     - `collect` iterates `specs` only, `:361-384`;
     - `write_outputs` overwrites the six CSVs, `:476-482`.
   - **Effect in the notebook.** Cells 10b.3 (`notebooks/loso_colab.ipynb`, cells 30–33) run one variant × norm each into the shared `GNN_LOSO_OUT`. After the four cells, `summary.csv` holds only the last cell's method. Cell 10b.4 still tells the user to "Open `summary.csv` (accuracy per subject and method …)". This is unlike `benchmark_loso.build_summary` (`benchmark_loso.py:613-630`), which rebuilds from every stored method's folds and leaves out mismatching ones with a warning. The P21 notebook cells rely on that behaviour.
   - **Not affected.** The verifier's commands (one invocation per protocol with every variant and norm) and the smoke test (both norms in one invocation, so it cannot catch this).
   - **Fix, either way.**
     - (a) Preferred. `build_outputs`/`collect` take every known method spec (`make_specs(VARIANTS ∪ variants found in folds/, NORMS)`) whose fold files exist in the out-dir. Requested methods must pass `check_fold`. Others are included only if `fold_problem` returns None, and are otherwise left out with a `[warn]`, exactly as in `benchmark_loso.build_summary`.
     - (b) Data-signal adds a final 10b.3 cell running all four variant × norm combinations (every fold `[skip]`, full tables rebuilt) and changes 10b.4 to read the tables only after that cell.
   - **Required test, both routes.** Two synthetic invocations into one out-dir (`--norm pooled`, then `--norm subject`, one variant) must leave a `summary.csv` that holds both methods with their per-subject rows. With (b), the notebook structure test must also assert that the all-methods cell is last in 10b.3. The test must fail on the current code.
   - **Gate.** Full suite alone after the fix. The verifier runs at the fix head.

### Non-blocking notes

- **N1.** Pooled z-score statistics are fitted on all training rows, including the ~20 % of training trials used for early stopping (`:141` before `fit_gnn`'s split). This is not an R2 breach, because nothing from the test subject or fold is involved. State it once in the report.
- **N2.** The headline GNN `Acc (%)` is the accuracy of the 3-seed softmax ensemble (`fold_rows` with no `proba_rep`, `benchmark_loso.py:567`). The P21 networks are single fits per seed. A fair comparison uses the GNN per-seed mean (`seeds.csv`) against the networks' mean over seeds 42/43/44. The ensemble goes in a separate, labelled column (RR-2).
- **N3.** In LOSO, early-stopping validation comes from the training subjects' own trials. Validation accuracy therefore measures within-pool generalization, and the restored epoch is not selected for cross-subject transfer. High train ≈ val with low test is the expected subject-shift signature, not under-training (RR-4).
- **N4.** The existing `reports/loso_w1_p22_common/summary.csv` still says "…, LOSO, channels common" for `within_lda` (W-1; P22 outputs are not regenerated). The P23 comparison table relabels those rows within-subject and says why.
- **N5.** Because of the C-1 keys, a `benchmark_loso` rerun into any P21/P22 out-dir is refused ("use a new --out-dir"). This is intended (P22 C-5), but the P21 notebook cells resuming a pre-P23 Drive folder will now stop. One sentence in the report or notebook intro is enough.
- **N6.** The window-level binomial SE understates the noise: there are about 17 correlated windows per trial and 39–40 trials per subject. The margins below are lower bounds, so per-subject claims also need the seed-range condition.
- **N7.** The template checklist row of `07_review.md` committed in 1519dd5 named the recording-file suffix, which is a hit of the guard's term list. This file no longer contains it, so the net branch diff is clean after this commit. The history hit is in template text and joins the list already reported to Sebastian (decision row P22 gate).
- **N8.** Within-subject GNN folds train on about 426 fitting windows (~666 × 0.8 outer fold × 0.8 after validation), against about 2131 in LOSO (4 training subjects × ~666 × 0.8 after validation), a factor of 5 (own arithmetic below). The within GNN is therefore data-limited and need not be an upper bound for the LOSO GNN, unlike `within_lda` (PR-5).
- **N9.** `within_lda` `Acc (%)` is the mean over 5 split repeats (seeds 42–46). The GNN within value is 1 split (seed 42) × a 3-seed ensemble. The test folds of GNN within and within_lda repeat 0 coincide only if `cv_groups == trial_ids` (V12).

Arithmetic (own): `python3 -c "print(round(666*4*0.8), round(666*0.8*0.8), round(666*4*0.8)/round(666*0.8*0.8))"` → 2131, 426, 5.00. LOSO starts from ~2660 training windows before the validation split; the deep-learning handoff says "~2700 training windows", consistent with this.

### Noise units for the results review (P21 C-3, C-4)

The noise unit for subject s and accuracies A, B (1.0 s, `Acc (%)`) is SE_Δ = sqrt(SE_A² + SE_B²), with SE = 100·sqrt(p(1−p)/n) and n = windows (S01 680, S02 644, S03 661, S04 665, S05 679, identical to P22 `Windows`).

- **Material.** A difference is material only if |Δ| > 2·SE_Δ **and** |Δ| > the GNN cell's per-subject seed range (max − min of the three per-seed `Acc (%)` in `seeds.csv`). For a comparison with a P21 network, |Δ| must also exceed that network's per-subject range over seeds 42/43/44 (ccnn ≤ 5.12, eegnet ≤ 8.23 pp, P21 report §seed spread).
- **Tie.** Anything that is not material.
- **Scale.** At P22 lda accuracies, SE is 1.77 / 1.68 / 0.76 / 0.26 / 0.66 pp, so 2·SE_Δ ≈ 5.0 / 4.7 / 2.1 / 0.7 / 1.9 pp. Command: `.venv/bin/python -c` over `reports/loso_w1_p22_common/summary.csv` (the session above). S01 preview: GNN − lda = +1.62 pp, SE_Δ 2.48, seed range 3.8, so a tie. GNN − fbcca = +12.2 pp, SE_Δ 2.57, so material.

### Pre-registered directional predictions (results review; written after seeing the previews above)

- **PR-1 (fbcca floor; F is an input).** No GNN LOSO method (4) is materially below `fbcca` LOSO on any subject. Each of the 4 cohort means is ≥ 82.40 % (P22 fbcca mean). nodes+F and nodes+coh+F pooled are materially above fbcca on S01 and S02.
- **PR-2 (vs lda LOSO).** No GNN LOSO pooled method is materially above `lda` on more than 1 subject. S03–S05 are ties or material losses of ≤ 3 pp (ceiling).
- **PR-3 (R-16, subjnorm ≥ pooled; paired: same seeds, same validation splits).** For each variant, `_subjnorm − pooled` is not materially negative on any subject, and the cohort-mean Δ is ≥ 0. A material gain appears on at least one of S01, S02 (lda_subjnorm − lda there: +5.59, +6.83). Every such gain is worded "offline upper bound".
- **PR-4 (R-15, coherence edges).** `nodes+coh+F − nodes+F` is a tie on ≥ 4 of 5 subjects in each protocol × norm. No material gain of the same sign appears on ≥ 3 subjects.
- **PR-5 (R-16, LOSO below within: not expected to hold uniformly for this model).** For each variant (pooled), within GNN is materially above LOSO GNN on at most 2 of 5 subjects, and S01 is a tie or LOSO ≥ within. If ≥ 3 subjects show a material within > LOSO, this prediction missed and the report says so. A tie is reported as "direction not observed; the within GNN is data-limited (N8)", never as "the GNN generalizes across subjects".
- **PR-6 (within GNN vs within_lda, common channels, matched).** `within_lda` is not materially below within GNN on any subject, and is materially above it on ≥ 2 subjects (expected S01, S02).
- **PR-7 (PF-30).** Every LOSO fold (20) has mean train accuracy ≥ 90 %. `Diagnosis` is "OVERFITTING" (train − test > 15 pp) on the S01 and S02 LOSO folds of every method. On S01/S02 LOSO folds, validation accuracy is above test accuracy. Any fold with train < 70 % (UNDERFITTING) is a bug candidate and is investigated before interpretation.
- **PR-8 (degenerate).** 0 degenerate LOSO folds (P21 networks: 0). Degenerate within folds, if any, occur only on S01/S02 and are listed with their flag.
- **PR-9 (seeds).** The per-subject seed range of every GNN LOSO cell is ≤ 8.23 pp. The ensemble `Acc (%)` is ≥ the mean per-seed accuracy − 1 pp in every cell.

### Binding run-list items for the verifier (copy verbatim into 02_plan.md)

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

### Reporting rules for the results review and the scribe

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

Verdict: FAIL

Required fix: F1 (deep-learning, route (a); or data-signal, route (b)). The fix needs its failing-on-bug test and a full suite run alone. Round 2 re-checks only F1, its test, and that nothing else changed (`git diff 4a4799f -- src scripts tests configs notebooks`).

## Results review

Verdict: APPROVE / REJECT
