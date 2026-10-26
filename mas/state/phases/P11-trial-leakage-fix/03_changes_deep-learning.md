# P11 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md, 03_changes_ml-engineer.md (incl. Round 1 orchestrator change), mas/RULES.md, decisions.md P10/P11 rows, 05_PITFALLS PF-01–03, PF-28–31
Branch: phase/P11-trial-leakage-fix
Commit(s): see `git log` (feat: network protocol; test: P11 network tests; docs: this file)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/models/cnn/eegnet_cv.py` | MODIFIED | `train_and_eval_cv(..., groups=None, cv="grouped", smoothing="mod5")`: splits from `cv_utils.make_splits`, `assert_no_shared_trials` in grouped mode, 2.0 s via `legacy_eval.accuracies(y, pred, proba, groups, smoothing)`; result adds `smoothing` label and `splits`; `cv` is the label of the splitter used. `train_and_eval_eegnet_cv` forwards the same arguments. Training convention unchanged (PF-28) | P11.3 | R1, R8, PF-01 |
| `src/models/cnn/benchmark_common.py` | MODIFIED | `--cv`/`--smoothing` via `add_protocol_args`; `gated_windows` returns `trial_ids` (ids of the full `y_labels.npy` with `LEGACY_TRIAL_LENGTHS`, stimulus rows, then the gate's `valid_mask`; PF-03), `trial_block_report`, `trial_ids_approximate`, `n_trials`; `trial_line`, `approximate_line`; header lines from `protocol_labels`; output dir `output_dir(reports, cv)`; meta adds the trial-id source and the approximate-id subjects | P11.3 | R1, R8, PF-03 |
| `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py` | MODIFIED | same flags; OFF and ON share the split, seeds, init and loader generator; legacy outputs under `reports/legacy_leaky/`; `--freeze-legacy` only valid with `--cv legacy` (parser error otherwise; with legacy it is redundant because the file is already written there); meta names splitter, rule, approximate-id subjects | P11.3 | PF-28, decisions P10 |
| `scripts/benchmarks/neural_networks/benchmark_eegnet.py`, `benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py` | MODIFIED | docstrings only (flags come from the shared parser) | P11.3 | — |
| `tests/test_p11_networks.py` | NEW | 14 tests (below) | P11.3, N4 | PF-01, PF-03, PF-28 |
| `tests/test_p08_eegnet.py`, `test_p08_eegnet_known_answer.py`, `test_p09_compact_shallow.py`, `test_p09_known_answer.py`, `test_p10_augmentation.py`, `test_p10_augmentation_known_answer.py` | MODIFIED | these pin the P08–P10 protocol: direct calls pass `cv="legacy"`, script runs pass `--cv legacy --smoothing mod5` and read `legacy_leaky/`; the fold spy of the mirror test follows `make_splits`; the stub of the A/B trainer accepts the new keywords. No tolerance or hash pin changed | P11 | — |

## Legacy behaviour implemented

`--cv legacy --smoothing mod5` = the P08–P10 protocol (window-level StratifiedKFold, `i % 5`), labelled "legacy R1/PF-01, leaky" in the meta, written under `<reports-dir>/legacy_leaky/`. Byte-identity: on a synthetic 2-subject tree (S01, S02, `write_subject(n_trials=3)`, 2 epochs, CPU) the CSVs of EEGNet (two subjects), EEGNet `--augment on`, Compact-CNN, ShallowConvNet and the Compact-CNN A/B have identical sha256 to the pre-P11 code (scratch worktree at 829602c), pins:

| CSV | sha256 |
|---|---|
| eegnet_benchmark_cpu.csv | 11c5402857c5e433761be2a4e37ff39382c58e0a273e0f9494ab8db1d3c9bd91 |
| eegnet_aug_benchmark_cpu.csv | 157adbbf464a01bb0b295e4618ca720d2d5e0b5b1cd08aebc3e1be1a8cf5bb24 |
| compact_cnn_benchmark_cpu.csv | 658100294111444f4d0b10f2eb3bd9a20a818e8951bbf66171c13736ca4b083d |
| shallow_convnet_benchmark_cpu.csv | ddcca6c2510eefc3b8b4681a0b19f845344161b304be63817dfffaec9b1d9b51 |
| augmentation_ab_compact_cnn.csv | 8f16e9ee639d810a68254ba55bdd8a723b2b06a6473b5b85fef65e375c78e002 |

(The existing P09 pins `EEGNET_SMOKE_PROBA_SHA256` and `EEGNET_SMOKE_CSV_SHA256` still pass with `cv="legacy"`.) `.meta.txt` files gain the trial-id lines and are not pinned.

## Differences from the cited examples
None; no external example used.

## Deviations from the plan
1. Default `--smoothing` is `mod5` (not `trial`), per the last P11 decisions row; `trial` is the PF-02 diagnostic, selectable.
2. `--freeze-legacy`: kept for the P10 command line, valid only with `--cv legacy` (error otherwise), where it prints a note and copies nothing, because `--cv legacy` already writes under `legacy_leaky/`. The frozen P10 CSVs already in `reports/legacy_leaky/` stay the "before" side; a legacy re-run would rewrite them with identical content.
3. `train_and_eval_cv` defaults `cv="grouped"`, so a caller without `groups` gets a ValueError instead of a silent leaky split.

## How to run / reproduce (verifier; confirms 02_plan.md step 1, unchanged)

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model eegnet --epochs 150 --device cpu
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model compact_cnn --epochs 150 --device cpu
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model shallow_conv_net --epochs 150 --device cpu
```
Defaults are `--cv grouped --smoothing mod5`, subjects discovered (S01–S05), outputs `reports/augmentation_ab_<model>.csv` (+ `.meta.txt`; file name `shallow_conv_net`). Optional legacy re-run (not needed; the P10 copies are frozen): add `--cv legacy` → `reports/legacy_leaky/`. Single-network benchmarks: `python -m scripts.benchmarks.neural_networks.benchmark_{eegnet,compact_cnn,shallow_convnet} [--subject S03] [--cv ..] [--smoothing ..]`. Expected runtime about 25 min (P10: 1495 s); grouped folds have the same sizes.

## How I verified
- Legacy byte-identity (table above): scratch worktree at 829602c vs the branch, same driver script on the same synthetic tree, `--cv legacy --smoothing mod5`.
- Grouped smoke on the synthetic tree (2 epochs, CPU): EEGNet, EEGNet augmented, Compact-CNN, ShallowConvNet and the A/B; files land in `reports/` (grouped) and `reports/legacy_leaky/` (legacy); the meta names `StratifiedGroupKFold(5, shuffle, 42) over reconstructed trial ids`, the smoothing rule and `trial_ids_approximate subjects`.
- `tests/test_p11_networks.py` (14): every network script (EEGNet, Compact-CNN, ShallowConvNet, A/B) calls `make_splits("grouped", ...)` with 15 trial ids and its folds share no id (spy on the script's own split); negative control: `--cv legacy` folds do share ids and the helper raises; grouped without ids raises; PF-03 gate rejection of stimulus window 7 gives `np.delete(pre-gate ids, 7)` (post-gate ids differ), not approximate; truncated block gives approximate; N4: dataset length equals the training-fold length in each fold and arm, DataLoader generator `initial_seed() == 42 + fold` with shuffle on in OFF and ON, identical splits across arms; the A/B script arms share one split and the same ids; smoothing rule and ids reach `accuracies`; output dirs and meta lines for grouped/legacy/trial; `--freeze-legacy` rejected with grouped.
- Full suite: `646 passed, 21 warnings in 295.41s (0:04:55)` (`.venv/bin/python -m pytest tests -o addopts="" -q`; 632 before this row plus 14 new)

## Left to do / known limitations
- Parameter counts unchanged (2,349 / 14,485 / 56,021, R-8; `count_parameters` untouched, its tests pass).
- Synthetic smoke accuracies are meaningless (2 epochs); real numbers are the verifier's run.
- Real S02 and S04 have approximate ids (ml-engineer); the network scripts print the block report for such subjects and list them in the meta.
- Compact-CNN keeps the fs 250 label (PF-04) until P16.

## Reference consultations (R11)

None. The original repository (answer key) was not opened.

| # | Trigger | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| — | — | — | — | — |

## Sources

1. `mas/03_ROADMAP.md` P11, `mas/RULES.md` R1/R8, `mas/05_PITFALLS.md` PF-01–03/PF-28–31, `mas/state/decisions.md` P10/P11 rows (all opened in this run).

## Questions
None.

## Round 2 (post-verify)

Trigger: 06_verify.md FAIL on P4 (R-9b), e85eeda. Question: bug or legitimate variance. Nothing was tuned: no hyperparameter, seed, default or number-producing line changed. Diagnostics and their outputs are in `mas/state/scratch/p11_round2_dl/` (git-ignored): `fold_identity.py` (+`.out`), `classical_folds.py` (+`.out`), `init_only.py`, `run_seeds.sh`, `seeds.log`. All ran with `.venv/bin/python` on CPU at branch HEAD dcc33f0 (plus the new test); nothing was written to `reports/`.

### Findings

1. **Fold identity: no difference.** For S01-S05, the network path (`benchmark_common.gated_windows`, then `make_splits("grouped", yi, ids, 42)` as inside `train_and_eval_cv`) and the classical path (`prepare_subject`, then `splits_for("grouped", y, ids, 42)`, which reproduces R-6 exactly) give the same gate mask, the same labels in the same order, the same trial ids and the same five (train, test) index arrays (`np.array_equal`, all True; `fold_identity.out`, `classical_folds.out`). Kept channels identical (7, none dropped). S03 test-fold sizes 40/39/40/39/39.
2. **Fold composition, S03: balanced.** Each test fold holds 8 trials, 1 or 2 per class (5 or 9-10 windows per class); each training fold 6 or 7 trials per class (`fold_identity.out`). No fold lacks a class.
3. **Data path: nothing changed by the grouped switch besides the split.** Read in `src/models/cnn/eegnet_cv.py` and `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py`: window order is the clean-array order in both modes (sklearn returns sorted indices); z-scoring is per window and channel over its own time axis, so it does not depend on the split; the label map is the sorted-code map and `make_splits` receives `yi` (0-4), an order-preserving encoding, so the split equals the one on the codes (finding 1 confirms it); the train-accuracy pass runs after the test prediction, in eval mode, and draws no random numbers; OFF and ON each call `train_model`, which re-seeds `torch.manual_seed(seed + fold)` and builds a fresh loader generator, so the arms share only the split. The 1.0 s accuracy does not involve the smoothing rule.
4. **Seed sensitivity (diagnostic only; no seed is proposed).** EEGNet, S03, augmentation OFF, 150 epochs, CPU (`seeds.log`):

| Run | Split seed | Model/loader seed base | 1.0 s | Folds (test acc %) | Train |
|---|---|---|---|---|---|
| `benchmark_eegnet --subject S03 --seed 42` | 42 | 42 | 54.82 | 50.00 / 30.77 / 60.00 / 41.03 / 92.31 | 97.46 |
| same, `--seed 43` | 43 | 43 | 71.57 | 45.00 / 80.00 / 58.97 / 92.31 / 82.05 | 98.85 |
| same, `--seed 44` | 44 | 44 | 67.01 | 65.12 / 42.50 / 97.50 / 79.49 / 48.57 | 96.24 |
| `init_only.py` | 42 | 1042 | 71.57 | 50.00 / 71.79 / 72.50 / 87.18 / 76.92 | not measured |
| `init_only.py` | 42 | 2042 | 71.57 | 60.00 / 69.23 / 75.00 / 66.67 / 87.18 | not measured |
| `benchmark_eegnet --subject S03 --seed 42 --cv legacy` | 42 (windows) | 42 | 75.63 | 77.50 / 55.00 / 74.36 / 79.49 / 92.31 | 98.34 |

   - The seed-42 run reproduces the verifier's S03 OFF exactly (54.82, same per-fold values), and `--cv legacy` reproduces P10's 75.63 exactly: the run is deterministic and the legacy path is intact.
   - On the **identical** seed-42 grouped folds, changing only the weight-init and loader seed moves S03 OFF from 54.82 to 71.57 (twice, with different per-fold values): a 16.75 pp range from initialisation alone. Across split+init seeds 42/43/44: mean 64.47, sd 8.66, range 16.75 (`.venv/bin/python -c` with `np.std(ddof=1)` and `np.ptp`). The R-9b gap of the seed-42 run (73.60 - 54.82 = 18.78) is the size of this single-subject spread, and the ±5 pp network tolerance is narrower than the init-only spread of EEGNet on S03 under grouped CV.
   - The classical flagship on the same grouped folds is also weakest on fold 1 (92.50 / 76.92 / 87.50 / 84.62 / 92.31; trials 86, 110, 112 at 0.4-0.5 window accuracy; `classical_folds.out`); EEGNet seed 42 is lowest on fold 1 (30.77). Whole-trial hold-out exposes trial-to-trial variability that the leaky split hid, and the networks amplify it.
   - Smoke total: 99 + 87 + 92 + 81 s (logged) plus about 170 s for the two init-only runs, about 9 min.
5. **R11 consultation** (permitted after findings 1-4 found no bug). Original repository (answer key) at commit `5d6d1c26397a2262e99d9646500030e261a04585` (HEAD; the file's only history entry there is the later folder refactor ce09f1a, so the P11-era text may differ slightly). Every access went through `git -C ... grep/show` and is in `mas/state/scratch/reference_access.log` (12:05:00-12:05:15). No code was copied.

| # | Trigger | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| 1 | R-9b missed beyond tolerance after one investigation round without a bug | `git grep -l` (file names only): `scripts/benchmarks/neural_networks/{benchmark_compact_cnn,benchmark_eegnet,benchmark_nn_augmentation,benchmark_shallow_convnet}.py`, `src/preprocessing/dataset/cv_utils.py` | the network scripts use `StratifiedGroupKFold` and `build_trial_ids` | nothing |
| 2 | same | `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py`: grep hits at lines 22, 29, 65, 68, 78, 82, 86-91, 114, 146, 150, 170-173, 183-185, 237-240; then lines 78-135 and 160-180 read in full | Trial ids: `build_trial_ids(y_stim, 5)` on the pre-gate stimulus labels, indexed by the gate's `valid_mask`; groups = those ids; `StratifiedGroupKFold(5, shuffle=True, random_state=42)`. Same partition as ours (we build ids on the full label array, then take the stimulus rows; on legacy folders the stimulus blocks are contiguous, so the groups match up to an order-preserving relabel, which the splitter ignores). Normalisation: per window and channel over time (eps 1e-8; ours 1e-6): the same. RNG differences: the fold index starts at **1** (`enumerate(..., 1)`), so the original seeds `torch.manual_seed(42 + fold_idx)` = 43..47 and the augmentation generator 43..47, where our written convention (06_AGENT_ROLES, PF-28, roadmap P08) gives 42..46; and its `DataLoader` has no generator, so batch order comes from the global torch RNG after the model is built. Its gate at HEAD is `apply_artifact_quality_pipeline` (a later name). | nothing: split and normalisation match; our RNG streams follow the written convention, and replaying the original's would be tuning toward R-9b (golden rule 5) |

### Outcome

- **No bug found.** Folds, ids, windows, labels and normalisation of the network path are identical to the classical path that reproduces R-6 exactly, and the original builds the same groups and the same normalisation. The R-9b misses are explained by single-seed variance: on identical folds EEGNet S03 OFF moves 16.75 pp with the init seed alone, and the original used a different RNG stream (fold seeds 43-47, unseeded loader).
- **Accepted-deviation request for the reviewer (P4).** Evidence: findings 1-5. Proposed wording: "R-9b network cells (EEGNet S03 all four cells, S05 2.0 OFF, cohort 1.0 OFF / 1.0 ON / 2.0 OFF means, Δ2.0; Compact-CNN S03 ON at 1.0 and 2.0, S05 1.0 ON, mean 1.0 ON, Δ1.0) deviate beyond ±5 / ±3 pp. Cause: variance of single-seed 150-epoch training under trial-grouped CV, measured at 16.75 pp (init seed only, same folds) for EEGNet S03 OFF; the original used a different RNG stream (fold seeds 43-47, unseeded DataLoader). Splits, trial ids and normalisation verified identical to the R-6 path and to the original's construction. The sign rule holds for every model; ShallowConvNet is inside every window." The decision belongs to the reviewer and, through decisions.md, to Sebastian. Whether later phases should report network numbers over several seeds is a planning question, not a change made here.
- **Test added** (regression guard; there was no bug to fix): `tests/test_p11_networks.py::test_network_folds_equal_classical_flagship_folds`. Synthetic tree with a gate rejection inside a block: `gated_windows` and `prepare_subject` give equal labels and ids (74 clean windows), and the five folds of `train_and_eval_cv` equal `splits_for("grouped", ...)` of the flagship. Mutation check: replacing the network ids by post-gate ids (the PF-03 bug) makes it fail (`1 failed`; via a throw-away pytest plugin in the scratchpad, not committed).
- Full suite: `679 passed, 21 warnings in 463.23s (0:07:43)` (`.venv/bin/python -m pytest tests -o addopts="" -q`; 678 + 1).
- R-8 unchanged (params 2349 printed in every EEGNet smoke run).

### Files (Round 2)

| Path | NEW / MODIFIED | Summary |
|---|---|---|
| `tests/test_p11_networks.py` | MODIFIED | + `test_network_folds_equal_classical_flagship_folds` |
| `mas/state/phases/P11-trial-leakage-fix/03_changes_deep-learning.md` | MODIFIED | this section |

## Round 2b (seed-spread diagnostic)

Trigger: results review Round 1 REJECT (07_review.md 3c30c9e), required step 1 (deep-learning part); decisions.md P11 rows D-4 and "Round accounting". This is a DIAGNOSTIC build. No reported number, default or reporting path changes, and no hyperparameter or seed of the reported run changes.

### Files

| Path | NEW / MODIFIED | Summary | Source |
|---|---|---|---|
| `src/models/cnn/eegnet_cv.py` | MODIFIED | `train_and_eval_cv(..., model_seed=None)`: seed base for the model init, DataLoader generator and augmentation generator (`model_seed + fold`); the splitter keeps `seed`. `None` (default) uses `seed`, so every existing caller behaves as before (pins below) | review step 1 |
| `scripts/diagnostics/network_seed_spread.py` | NEW | DIAGNOSTIC in the docstring, console (`[DIAGNOSTIC]` lines) and meta (first line). `--model {eegnet,compact_cnn,shallow_conv_net}`, `--seed-bases` (list), `--epochs` (150), `--device` (cpu), `--subjects` (default: all `S\d+` folders found). It reuses `gated_windows` and `train_and_eval_cv(..., seed=42, cv="grouped", smoothing="mod5", model_seed=b)`, so the seed-42 grouped folds are fixed for every base. OFF and ON run with the same per-fold seeds within a base. Output: `<reports-dir>/diagnostics/p11_seed_spread_<model>.csv` (Subject, Seed base, Clean Windows, 1.0s OFF/ON, 1.0s Delta, 2.0s OFF/ON, 2.0s Delta, Train Acc OFF/ON; a Mean row per base) + `.meta.txt` (folds, random_state 42, bases, seed roles, smoothing rule, data source, approximate-id subjects). Never writes `augmentation_ab_*` | review step 1 |
| `tests/test_p11_seed_spread.py` | NEW | 8 tests (below) | review step 1 |

### Tests (`tests/test_p11_seed_spread.py`, synthetic trees, 2 epochs, CPU)

- `test_folds_identical_across_seed_bases_and_the_base_changes_training`: bases 42, 1042 and 2042 give identical (train, test) arrays. Control: the probabilities differ between bases, so the base reaches training (ON arm, so the augmentation generator is included).
- `test_model_seed_42_and_none_reproduce_the_reported_path_exactly`: `model_seed=42` and the default give equal per-window probabilities and per-fold train accuracies, OFF and ON.
- `test_script_base_42_equals_ab_rows_and_writes_only_diagnostics`: the script with bases 42 and 1042 writes exactly two files, both under `diagnostics/`, and no `augmentation_ab_*`. Its base-42 rows (Mean row included) equal `reports/augmentation_ab_eegnet.csv` of the A/B benchmark on the same tree (`assert_frame_equal`). Columns, row order, base column and the DIAGNOSTIC / `random_state=42` meta text are checked.
- `test_script_rejects_unknown_model`.
- `test_ab_legacy_and_grouped_pins_unchanged` (4 cases): sha256 of the A/B CSV on the 2-subject tree for EEGNet and Compact-CNN under `--cv legacy` and `--cv grouped`. The pins were computed with the code **before** `model_seed` was added (scratch driver, same tree) and recomputed after it: equal. The Compact-CNN legacy pin `8f16e9ee…e002` also equals the pre-P11 pin in the table above. This also closes carry-forward N3 (network legacy pins in a test).

Smoke: synthetic data only (the tests above, which run the script end to end). No real-data run was made in Round 2b.

Full suite: `687 passed, 21 warnings in 524.00s (0:08:44)` (`.venv/bin/python -m pytest tests -o addopts="" -q`; 679 + 8).

### Verifier commands (run once each, from a clean checkout, CPU)

```bash
.venv/bin/python -m scripts.diagnostics.network_seed_spread --model eegnet --seed-bases 1042 2042 --epochs 150 --device cpu
.venv/bin/python -m scripts.diagnostics.network_seed_spread --model compact_cnn --seed-bases 1042 2042 --epochs 150 --device cpu
```

- Subjects: all discovered (S01–S05).
- Outputs: `reports/diagnostics/p11_seed_spread_eegnet.csv` and `reports/diagnostics/p11_seed_spread_compact_cnn.csv`, each with its `.meta.txt`. The seed-42 rows are the existing `reports/augmentation_ab_<model>.csv`, which these commands do not touch. Base 42 is left out because it repeats the reported run (the test above proves the equality).
- Runtime estimate: one base runs both arms on all five subjects, which is what one A/B run did (EEGNet 833 s, Compact-CNN 668 s; 05_run.md). Two bases come to about 2 × 833 ≈ 28 min for EEGNet and 2 × 668 ≈ 22 min for Compact-CNN, about 50 min in total. That is inside `LOCAL_RUN_BUDGET_MIN` 120. (The review's ≈ 30 min figure is low by about this factor.)
- Logs: under `reports/logs/P11/`, as in 05_run.md.

### Reference consultations (R11)

None in Round 2b.
