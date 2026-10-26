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
