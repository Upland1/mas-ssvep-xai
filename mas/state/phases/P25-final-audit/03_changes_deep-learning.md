# P25 fix round 1 - deep-learning handoff

Status: READY

## Files
- MODIFIED `src/models/cnn/ccnn.py` - single input map `[real | imag] / T`, convolutions with bias, docstring and parameter formula updated.
- MODIFIED `tests/test_p20_networks.py` - count test now pins R-8; new `test_ccnn_parameter_count_matches_r8`, `test_ccnn_single_map_real_then_imag_layout`; `test_ccnn_spectrum_known_answer` reads real at `k`, imag at `n_bins + k`.
- MODIFIED `tests/test_p20_independent_known_answer.py` - `test_ccnn_spectrum_bin_scaling_and_nfft` pinned the old `(B, 2, C, n_bins)` layout; it now splits the new `(B, 1, C, 2*n_bins)` map back into real and imag halves (assertions otherwise unchanged).

## Diagnosis
P20.3 stacked real and imaginary parts as two input maps `(B, 2, C, n_bins)` and used bias-free convs (B004 applied to a class it does not cover), giving 14,817 / 17,285. The roadmap writes `[real | imag] / T` (concatenation along frequency) and R-8 counts the original classes with conv biases.
Independent arithmetic (n_bins = 189, K = 10, 5 classes, F = 2C, one map of width 378):
C=7, F=14: spatial 14*7+14 = 112; BN 28; spectral 14*14*10+14 = 1,974; BN 28; head 14*369*5+5 = 25,835; total 27,977.
C=8, F=16: 144 + 32 + 2,576 + 32 + 29,525 = 32,309. Both equal R-8 exactly; no R11 consultation was needed (reference not opened).
B004 note: convs keep bias here because the R-8 Era-C count includes it; BN after the conv makes the bias redundant but harmless. The B004 bias-free rule covers the first R-8 table.

## Tests
- Fail on old code (verified by restoring the HEAD version of ccnn.py): 4 in `test_p20_networks.py` (shape/params, spectrum known answer, R-8 count, single-map layout) and 4 parametrised in `test_p20_independent_known_answer.py`.
- With the fix: `pytest tests/test_p20_networks.py tests/test_p20_independent_known_answer.py tests/test_p21_loso_networks.py tests/test_p21_independent_known_answer.py tests/test_p20_online.py -q`: all pass (85 tests, none failed). Full suite: see commit message / below.
- CPU/CUDA: forward is device-agnostic (`bin_idx` is a buffer); CPU tested.

## Consumers checked
`training.py` (`fit_network`/`cnn_fold`), `benchmark_loso.py`, `pseudo_online.py`, `benchmark_nn_sweep.py` build CCNN through the constructor only; none touches `spectrum`, `spatial` or the input shape, and their tests pass.
`benchmark_window_sweep.py` `cnn` = compact_eegnet only; `simulate_dynamic_stopping.py` reads `reports/window_sweep/predictions.csv` (no CCNN). Neither needs regeneration. `make loso-all` has no network rows (`tests/test_p24_make_all.py` asserts it).

## Outputs to regenerate (verifier; commands from Makefile and P21 05_run.md; runtimes from logs)
1. P20 NN sweep (944 s, reports/logs/P20/nn_sweep.log; all three models run, only ccnn rows change, resumable per cell):
   `python -m scripts.benchmarks.neural_networks.benchmark_nn_sweep S01 S02 S03 S04 S05 --data-root data/processed_continuous --windows 1 --models ccnn compact eegnet --out-dir reports/nn_sweep` (use the Makefile line 269 `$(S)` expansion; ccnn-only: `--models ccnn`, a different cell set from the committed run may require `--overwrite`).
2. Pseudo-online (33 s and 63 s): Makefile lines 271-272, tags `ccnn_5class` and `ccnn_6class` (`--model ccnn --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 [--rest-class] --quality-source both $(RAW)`).
3. P21 cohort-5: Makefile line 282 `--methods ccnn compact eegnet --channels common --out-dir reports/loso_w1_s01-s05` (ccnn rows only change; ccnn fold about 1 min on GPU) and line 284 for k = 43, 44: `--methods ccnn eegnet --seed $(k) --out-dir reports/loso_w1_s01-s05_seed$(k)` (412 s and 438 s for both networks, reports/logs/P21/loso_D1_seed43.log, loso_D1_seed44.log). Old ccnn folds in `folds/` must be removed first or the harness prints `[skip]` and reuses them.
4. P21 39-subject ccnn (05_run.md line 116, about 85 min: 19:37 to 21:02 on 2026-10-28, reports/logs/P21/loso_w1_ccnn.log): `python -m scripts.benchmarks.benchmark_loso --data-root data/processed_continuous --window 1 --stride-sec 0.25 --methods ccnn --channels common --out-dir reports/loso_w1`. Delete the 39 ccnn `.npz` folds in `reports/loso_w1/folds/` first (resumable skip), then the harness rebuilds `summary.csv`, `per_subject.csv`, `predictions.csv`, `folds.csv`, `confusion.csv`; the classical rows are rebuilt from their folds unchanged.
Total GPU estimate: about 16 min + 1 min + 14 min + 85 min, roughly 2.0 h, within a standing local-run authorisation; the 39-subject run exceeds `LOCAL_RUN_BUDGET_MIN` but not `MAX_GPU_HOURS_PER_PHASE` in the P21 precedent.
Downstream: any table that quotes ccnn numbers (README, RESEARCH_LOG, docs/report/v2, progress report, P20/P21 reports) must be re-copied by the scribe. Expect the numbers to change.

## Open points
- Seeds: the layout change alters initialisation shapes; results are not comparable seed-by-seed with the old ones.
- R-8 first-table classes (EEGNet etc.) untouched.
