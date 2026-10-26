# P09 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify_P09` @ edd476edb1294004a0dd2eaf91ed70301208d8d2 (removed after use)

Verdict: PASS

## Tests on the clean checkout

```bash
python -m pytest -o addopts="" -q     # worktree, CPU
```
Summary line verbatim: `573 passed, 21 warnings in 219.21s (0:03:39)`; exit 0. Log: `reports/logs/P09/pytest_20261026T002847.log`.

## Acceptance

| Criterion (verbatim) | Re-run command | Obtained | Reference (R-x) | Tolerance | Met? | Log |
|---|---|---|---|---|---|---|
| parameter counts equal R-8 exactly | `python -m scripts.benchmarks.neural_networks.count_parameters` | exit 0; CSV `eegnet 2349, shallow_convnet 14485, compact_cnn 56021`; benchmark CSV Params 56021 / 14485 | R-8: 2,349 / 14,485 / 56,021 | exact | yes | `count_parameters_run1_20261026T003236.log`, `network_parameter_counts_run1.csv` |
| benchmarks run | the two benchmark commands (07_review.md) | both exit 0, both runs | — | — | yes | `benchmark_*_run{1,2}_*.log` |

### Per-model table (S03, CPU, run 1; legacy leaky R1/PF-01 CV, i%5 smoothing R8/PF-02, fs 250 label)

| Model | Clean / rejected | Channels | 1.0 s | 2.0 s smoothed | Train acc | Params |
|---|---|---|---|---|---|---|
| compact_cnn | 197 / 3 | 7 [PO3, POz, PO4, PO8, O1, Oz, O2], dropped none | 54.31 % = 107/197 | 62.94 % = 124/197 | 100.00 % | 56021 |
| shallow_convnet | 197 / 3 | 7 (same), dropped none | 86.80 % = 171/197 | 92.89 % = 183/197 | 100.00 % | 14485 |

k derived with `python3 -c "round(v*197/100)"` and re-checked with `round(100*k/197,2)`: 107, 124, 171, 183 reproduce 54.31, 62.94, 86.8, 92.89 exactly.

Per-fold test accuracy (train 100.00 % in every fold): compact 55.00 / 52.50 / 48.72 / 56.41 / 58.97; shallow 85.00 / 87.50 / 89.74 / 79.49 / 92.31.

### Run 1 vs run 2 (determinism)

| Model | CSV | .meta.txt | per-fold and summary lines |
|---|---|---|---|
| compact_cnn | `cmp` identical | `cmp` identical | identical (diff of fold/summary lines, runtime stripped) |
| shallow_convnet | `cmp` identical | `cmp` identical | identical |

## Pre-committed checks (07_review.md, results-review list)

1. Counts: met (above).
2. Gate: both logs print `S03: 200 stimulus, 197 clean, 3 rejected; channels kept 7 ...; dropped [none]` (= R-3, = P08). Met.
3. k/197: met (107, 124, 171, 183).
4. PF-30: train accuracy 100.00 % in all 10 folds next to test 48.72-58.97 % (compact) and 79.49-92.31 % (shallow): a generalization gap in both; not an optimization failure.
5. Diagnostic comparisons (never targets, not R-6), in windows of 197 (1.0 s / 2.0 s). Leaky flagship 178 / 188: compact -71 / -64, shallow -7 / -5. EEGNet P08 CPU 149 / 169: compact -42 / -45, shallow +22 / +14. R-7 (augmentation ON) shallow 176 (1.0 s): shallow here -5; R-7 compact 124: compact 1.0 s here -17 (its 2.0 s value is also 124, numerically coincident). R-9b OFF shallow 169 / 180: here +2 / +3; R-9b OFF compact 84 / 92: here 107 / 124. Leaky numbers below the leak-free flagship are "unexpected under PF-01"; against R-9b OFF the differences are small (shallow) or compact is above, which cannot be separated from model, seed and device effects in one subject: inconclusive.
6. Noise: shallow vs R-7/R-9b differences of 2-5 windows are within the few-window noise band (P08 CPU-CUDA gap 9/197). The compact vs shallow gap (64 windows at 1.0 s) is far above that on this subject, but no ranking or "best network" claim is made from S03 alone.
7. Labels: CSV/meta name `compact_cnn` (PF-31); meta states fs 250 -> K = 29 (PF-04), leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02), data-source line, `n_channels (after the gate): S03=7`. Met.

## Numbers in the handoffs vs logs

Every number in 05_run.md is copied from the logs listed there. No draft report existed to check.

## Sources spot-check

Opened `mas/04_REFERENCE_RESULTS.md` R-8 (counts 2,349 / 14,485 / 56,021) and the P09 acceptance line in 00_assignment.md (`parameter counts equal R-8 exactly; benchmarks run`); the logs match both. The cited papers were not re-opened by the builders (stated in 03) and are not required.

## Reference consultations check

Builder and tester list none. `mas/state/scratch/reference_access.log` has no P09 builder entry (its last lines are P03-era entries and the reviewer's privacy-scan command, which opened no reference file). Consistent. R11: met.

## Privacy and git

Tree clean before and after the runs (`git status --porcelain` empty). No recordings folder read or listed; no preprocessing run; benchmarks read the legacy processed arrays through project scripts only. `git log main..HEAD` messages: 0 hits for vendor/tool names. Worktree removed (`git worktree list` shows only the main checkout).

## Reasons (if FAIL)

None.
