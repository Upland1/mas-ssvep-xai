# P09 · 04 · Tests

Status: READY
Author: synthetic-tester
Reads: 02_plan.md, 03_changes_deep-learning.md, mas/RULES.md, mas/05_PITFALLS.md (PF-04, PF-31), decisions.md P08/P09

## Tests added

NEW `tests/test_p09_known_answer.py` (20 tests, 8.4 s). The builder's `tests/test_p09_compact_shallow.py` (25) is untouched. Expected values come from R-8 and hand arithmetic (formulas in the file), not from builder code.

| Test id (`tests/test_p09_known_answer.py::`) | Simulates | Expected | Tolerance | Source | Catches bug | Result |
|---|---|---|---|---|---|---|
| `test_r8_counts_by_hand_arithmetic` | default constructors, hand per-layer formulas | 56,021 / 14,485 | exact | R-8, analytic | conv bias, wrong K, pool | PASS |
| `test_compact_kernel_from_fs[250.0-29, 256.0-30]` | fs 250 / 256 | K 29 / 30; count = formula (56,693 at K=30) | exact | analytic, PF-04 | fs error | PASS |
| `test_compact_default_is_legacy_250_not_256` | default ctor | K=29, count != 56,693 | exact | PF-04 | K from fs 256 at default | PASS |
| `test_shallow_pool_arithmetic[75-15, 50-15, 75-10]` | pool kernel/stride variants | pooled length 11/13/16; only 75/15 gives 14,485 | exact | analytic | pool change | PASS |
| `test_conv_bias_mutants_break_r8` | swap in biased convs | +16 (Compact), +80 (Shallow); shipped convs `bias is None` | exact | analytic | conv bias | PASS |
| `test_compact_spatial_temporal_layout_identity_path` | one-hot spatial (ch 3), centred-delta temporal | feature map 0 = x[ch 3], no shift | rtol 1e-3 | R6, analytic | axis/padding error | PASS |
| `test_shallow_spatial_temporal_layout` | delta temporal, one-hot spatial (ch 5) | features = log of 75-sample mean of x^2 at 11 windows | 1e-3 | R6, analytic | axis/pool error | PASS |
| `test_shallow_zero_input_gives_exactly_log_eps` | zero input | every feature = log(1e-6) = -13.8155; grads finite | 1e-5 | analytic | log without clamp | PASS |
| `test_count_parameters_fails_on_mismatch` | counts +1 for each model | exit 1 each; exit 0 on real counts | exact | R-8 | script not failing | PASS |
| `test_mirror_recorded_training_calls_identical` | records AdamW, Cosine, CE, manual_seed, DataLoader and fold-splitter calls from the three scripts (2 epochs) | AdamW lr 1e-3 wd 1e-2; Cosine T_max 2 eta_min 1e-5; CE ls 0.05; seeds 42..46; StratifiedKFold(5, shuffle, 42); records identical across scripts | exact | roadmap P09.3 | script drift | PASS |
| `test_mirror_recorder_detects_drift[--seed, --epochs, --lr, --batch-size]` | negative control on ShallowConvNet | record differs | exact | — | recorder blind | PASS |
| `test_network_gate_equals_classical_prepare_subject[no bad, O2, PO4+Oz]` | synthetic tree with 0/1/2 bad channels; three scripts' `gated_windows` vs `prepare_subject` | same kept, dropped, n_clean, n_stimulus, clean labels; 7-len(bad) channels | exact | P08 carry-forward | gate divergence | PASS |

## Mutants run (scratch plugin outside the repo, temporary monkeypatches)

| Mutant | Failing tests |
|---|---|
| Compact-CNN convs with bias | counts, kernel[x2], bias, layout, count_parameters (6) |
| ShallowConvNet convs with bias | counts, pool[x3], bias, layout, log, count_parameters (8) |
| Compact default fs 256 (K=30) | counts, default-250, bias, layout, count_parameters (5) |
| Shallow pool stride 10 | counts, bias, layout, count_parameters (4) |
| Shallow pool kernel 50 | same 4 |
| log without clamp | `zero_input_gives_exactly_log_eps` |
| count_parameters always exit 0 | `fails_on_mismatch` |
| gate keeps bad channels (fail fraction 1.0) | gate-equality bad1, bad2 |
| ShallowConvNet script with `--seed 7` | mirror identical, drift[--seed] |

Optimizer/epochs/lr/batch drift are covered by the recorder negative controls (not by a source mutation).

## Bugs found

None. Observation only: the mirror check is on recorded calls, so a drift introduced outside those calls (e.g. a different z-score) is caught only by the builder's shared-driver identity assertion.

## Command

```bash
.venv/bin/python -m pytest tests/ -o addopts="" -q
```

Result (full suite): `573 passed, 21 warnings in 210.47s (0:03:30)`.
New file alone: `20 passed in 8.43s`.

## Sources

R-8 (`mas/04_REFERENCE_RESULTS.md`), `mas/03_ROADMAP.md` P09, PF-04, PF-31, decisions.md P08 carry-forward.
