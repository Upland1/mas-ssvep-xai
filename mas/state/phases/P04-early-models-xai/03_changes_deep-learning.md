# P04 · 03 · Changes — deep-learning

Status: READY
Author: deep-learning
Reads: 00_assignment.md, 02_plan.md, 03_changes_ml-engineer.md, mas/RULES.md, R-8, B004, PF-01/02/28
Branch: phase/P04-early-models-xai
Commit(s): see git log (feat: fusion CNN module; feat: CNN export and batch columns; test: CNN smoke)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| src/models/cnn/spatial_spectral_cnn.py | NEW | `DualBranchFusionCNN` (10,005 params, convs bias=False), `prepare_spatial_spectral_tensors`, `train_and_eval_fusion_cnn_cv`, `evaluate_temporal_smoothing`, scaler/predict helpers | P04.2 | R-8, B004, PF-28 |
| scripts/training/train_final_model.py | MODIFIED | `export_fusion_cnn` -> `<S>_fusion_cnn.pt`; `--device`, `--epochs`, `--skip-cnn` | P04.3 | R2 exception |
| scripts/training/batch_run_subjects.py | MODIFIED | columns `CNN 1.0 s`, `CNN train acc`, `CNN smoothed`; same flags | P04.4 | — |
| tests/test_p04_cnn_smoke.py | NEW | 10,005 + bias None, forward shape, 2-epoch CV determinism, train acc reported | — | R-8, PF-28 |
| tests/test_p04_ml_smoke.py | MODIFIED | pass `--epochs 2` to the two script calls (keeps the suite fast) | — | — |

## Legacy behaviour implemented
R1/PF-01 (`StratifiedKFold(5, shuffle, 42)` over windows, labelled in the result `cv` string), R8/PF-02 (`evaluate_temporal_smoothing` reuses `smooth_probabilities_legacy` from train_models, no reset), R2 exception (full-data CNN export carries `fit = FIT_LABEL`; its `train_accuracy` is on the fitted windows, not a test score).

## Details
- Training: AdamW 1e-3 wd 1e-2, CosineAnnealingLR(T_max=epochs, 140 default), label smoothing 0.1, batch 16. `torch.manual_seed(42 + fold)` immediately before the model, DataLoader `generator` seeded identically. Final model uses seed 42.
- Scalers: one StandardScaler on the flattened 32 spatial features, one on the 5 FBCCA scores, fitted on the training fold only; the FBCCA input is `hybrid[:, -5:]`.
- Result dict: out-of-fold `pred`, `proba`, pooled test `accuracy`, mean fold `train_accuracy` (eval mode on the training fold), per-fold lists, `classes` (codes 101..105), `cv`.
- `.pt` dict keys: state_dict, scalers (spatial, fbcca), classes, label_map (code->index), subject_id, architecture, n_parameters, fit, data_source, n_windows, epochs, train_accuracy. Contains sklearn scalers, so reload with `torch.load(..., weights_only=False)`. Reload verified on CPU and CUDA exports.

## Deviations
- A training batch of a single row is skipped (BatchNorm cannot train on one row); with ~160 training rows and batch 16 it never occurs.
- `src` imports `scripts.training.train_models` lazily inside two functions (harmonic features, smoothing) as the plan asks to reuse them; works when the repo root is on `sys.path` (all entry points do this).
- GPU and CPU runs give slightly different numbers (different kernels); each device is deterministic with its own seed. Verifier should state the device in the report.
- R11: reference repo not consulted.

## How I verified
- `pytest tests -q`: all pass (about 44 s, CPU).
- Parameter count by test: 10005, both conv biases None.
- Synthetic timing (200 windows, 5 classes, 140 epochs, 5 folds; script mas/state/scratch/p04dl/time.py): CPU 73.7 s, CUDA 20.8 s per subject CV; per-fold train acc 97.5-99.4 % against test 60-72 % on weak synthetic features (shows the gap is reported).
- Full-data export fit: about 1/4 of a CV on 125 % data, estimated 15-20 s CPU, 5 s GPU.

## Runtime estimate for the verifier (5 subjects x 5 folds x 140 epochs, 2 full fits, batch run)
CNN CV per subject 74 s CPU or 21 s GPU, so batch run 6.2 min CPU / 1.8 min GPU (plus LDA/FBCCA about 1 min); 2 exports about 0.5 min CPU. Total CNN work about 7 min CPU, about 3 min GPU, well inside the 120 min budget and the 30 min plan target. (Real windows have about 200 per subject, same size as the synthetic timing.)

## Questions
ACK 02_plan.md deep-learning 2026-10-24
