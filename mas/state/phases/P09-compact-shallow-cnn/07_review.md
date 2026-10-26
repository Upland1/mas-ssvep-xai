# P09 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_deep-learning.md, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Audited at `eff3782` (`git diff main...HEAD`, 21 files) against `mas/03_ROADMAP.md` P09, `mas/04_REFERENCE_RESULTS.md` R-7/R-8/R-9, `mas/05_PITFALLS.md` PF-01/02/04/28/30/31, `mas/RULES.md` era matrix, decisions.md P08/P09 rows, `mas/state/reports/P08.md`.

### Own checks (commands shown, synthetic or no data)

1. **R-8 counts by instantiation** (`.venv/bin/python -c "...CompactCNN(); ShallowConvNet(); EEGNetSSVEP(n_channels=7,n_samples=256)..."`):
   `compact 56021 29` (K = 29; params: spatial (16,1,7,1), bn1 2×16, temporal (32,16,1,29), bn2 2×32, head (5,8192)+5; no conv bias), `compact fs256 56693`, `shallow 14485 25 75 15` (temporal (40,1,1,25), spatial (40,40,7,1), bn 2×40, head (5,440)+5; no conv bias), `eegnet 2349`. Feature widths `[1, 8192]` (Compact, 32 × 256: pad 14 keeps T) and `[1, 440]` (Shallow, 40 × 11). Hand arithmetic `print(16*7+32+32*16*29+64+32*256*5+5, 40*25+40*40*7+80+40*11*5+5)` → `56021 14485`. All three equal R-8 exactly.
2. **Clamps**: `ShallowConvNet(n_samples=128)` → kernel 25, pool 75, stride 15, output `(2, 5)`; `n_samples=10` → kernel 10, pool 1, stride 1, output `(2, 5)`.
3. **EEGNet regression, independent of the builder's hash**: I executed `git show main:src/models/cnn/eegnet_cv.py` (P08 code) and the branch version on the same synthetic set (`make_windows(n_trials=4, seed=0)`, 3 epochs, CPU). Both `proba` sha256 = `adf2cc7d…75322c`, the value pinned in `tests/test_p09_compact_shallow.py:23`. The training path is unchanged for EEGNet.
4. **Batch-size-1 skip** (`eegnet_cv.py:76-77`): S03 train folds 157/158 rows, `python3 -c "print(157%32,158%32)"` → `29 30`; never triggers (same as P08), so BatchNorm sees no size-1 batch in either new network.
5. **Tests**: `.venv/bin/python -m pytest tests/test_p09_compact_shallow.py tests/test_p09_known_answer.py tests/test_p08*.py -o addopts="" -q` → `70 passed, 1 warning in 37.49s`.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) | `StratifiedKFold(5, shuffle, 42)` over windows via `legacy_cv` (`src/models/classical/legacy_eval.py:35-37`, used at `src/models/cnn/eegnet_cv.py:102`); prescribed for P04–P10; labelled in stdout and `.meta.txt` (`src/models/cnn/benchmark_common.py:84`, `:141`) |
| R2 Fit only in-fold | PASS | z-score per window and channel over its own time axis, no cross-window statistics (`eegnet_cv.py:38-43`, applied once at `:99`); model built and trained on `Xz[tr]` only (`:103`); fixed epochs, no early stopping, no validation split, no model selection on test folds (`benchmark_common.py:90`); test fold used only for `predict_proba` (`eegnet_cv.py:105`) |
| R3 Filter continuous, then window | N/A | raw windows, no filtering in this phase |
| R4 Estimator small-sample bias | N/A | no coherence/PLV |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) | per-script P07 two-tier gate, thresholds passed explicitly (`benchmark_common.py:75`: `GATE_THRESHOLDS, CHANNEL_FAIL_FRACTION`); identity with the classical `prepare_subject` now tested with 0/1/2 bad channels (`tests/test_p09_known_answer.py:228-239`) |
| R6 Index layouts verified | PASS | `(B,C,T)`/`(B,1,C,T)` axes checked and wrong layout rejected (`compact_cnn.py:56-59`, `shallow_conv_net.py:53-56`); known-answer layout tests: one-hot spatial + centred-delta temporal reproduces x[ch 3] without shift (Compact) and log of 75-sample mean of x² at 11 positions (Shallow) (`04_tests.md`, `tests/test_p09_known_answer.py`) |
| R7 Honest statistics | N/A | no significance tests |
| R8 Smoothing respects trials | LEGACY (by design) | `i % 5` reset on the clean array (`legacy_eval.py:30`, `accuracies` at `:117`); roadmap/era matrix legacy until P11 (PF-02); labelled (`benchmark_common.py:85`) |
| R9 Per-subject reporting with data source | PASS | per-subject CSV rows; data-source line printed and written to `.meta.txt` with `n_channels (after the gate)` (`benchmark_common.py:109-111`, `:138-139`) — P08 carry-forward closed. Only S03 is prescribed (plan run commands) |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | roadmap P09, R-8, PF-04/31 cited in module docstrings (`compact_cnn.py:1-11`, `shallow_conv_net.py:1-10`) and handoffs; papers named as in the roadmap and stated as not re-opened (`03_changes_deep-learning.md` Sources 2), correct under R10 |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | nothing adapted ("built from the roadmap specification") |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | builder and tester list none; `mas/state/scratch/reference_access.log` has no P09 consultation (its last line is my own privacy-scan command, logged because the pattern text contains the folder name; no reference file was opened) |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS | fs 250 → K = 29 is the labelled default (`compact_cnn.py:9-10`, `:21`; `benchmark_compact_cnn.py:13`, `:43`), fs 256 reachable by argument (K = 30, 56,693, tested); `compact_cnn` naming per PF-31 in CSV name, `NetSpec` and count table (`benchmark_compact_cnn.py:42`, `count_parameters.py:34`) |
| Tests cover every change; at least one fails on the historical bug | PASS | 25 builder + 20 tester tests; tester mutants (conv bias, default fs 256, pool 50/10, log without clamp, count script exit 0, gate keeping bad channels, seed drift) each fail ≥1 test (`04_tests.md`); fs-256 default (PF-04) fails 5 tests |
| Changes match 02_plan.md and the roadmap tasks | PASS | P09.1/P09.2 architectures match the roadmap text layer by layer (no ELU after the first BN in Compact; dropout after the log in Shallow; both convs `bias=False`); P09.3 via one shared driver (mirror by construction); P09.4 script; deviations below accepted |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | fragment-built pattern over `git grep -i HEAD` and `git log main..HEAD` messages: 0 vendor/tool hits; only pre-existing recording-suffix mentions in spec docs (`.gitignore:15`, `AGENTS.md`, `mas/01_DATA_SPEC.md`, `RESEARCH_LOG.md`), no recording file; `git diff --name-only main...HEAD` contains no data, reports, local tooling or answer-key paths |

### Judgements requested

1. **Architectures and counts.** Compact-CNN: spatial Conv2d(1→16,(C,1),no bias)+BN → temporal Conv2d(16→32,(1,K),pad K//2,no bias)+BN+ELU+Dropout → Flatten → Linear, `K = clamp(round(fs/lowest),4,n_samples)` (`compact_cnn.py:25-27`, `:39-53`) = roadmap P09.1. ShallowConvNet: temporal(1,25) → spatial(C,1) → BN → square → AvgPool(75,15) → `log(clamp(x,1e-6))` → Dropout → Linear (`shallow_conv_net.py:35-50`) = roadmap P09.2; kernel clamped to T, pool to T−k+1, stride to pool (`:31-34`). Counts exact (own check 1). PF-04 label and PF-31 naming correct.
2. **Shared driver.** `run_benchmark` is the single path for all three scripts; the network is the only varying input (`NetSpec.build`, `model_line`, `fs_note`, `training_extra`). EEGNet's training path is bit-identical to P08 (own check 3); max-norm still runs before training and after every `opt.step()` for EEGNet only (`eegnet_cv.py:64`, `:71-72`, `:82-83`); the new networks get none, as the roadmap prescribes none. Seeds `manual_seed(seed+fold)` before each model plus seeded DataLoader generator (`:62`, `:68`; recorded 42..46 in the tester's mirror test). No unprescribed leak.
3. **Gate-equality carry-forward.** Closed by `test_network_gate_equals_classical_prepare_subject[no bad, O2, PO4+Oz]` (kept, dropped, n_clean, n_stimulus, clean labels).
4. **Builder deviations — all accepted.** (a) Driver in `src/models/cnn/benchmark_common.py`: plan allowed a shared module; it is src, not a src→scripts import (no layering issue). (b) `--config` default None → `<root>/configs/pipeline_config.yaml` with the same root as P08's `DEFAULT_CONFIG`; no caller used the removed constant (grep). (c) Extra `.meta.txt` lines = the P08 carry-forward; CSV bytes unchanged (pinned hash). (d) `count_parameters` exit 1 on mismatch: loud, matches the acceptance criterion, tested both ways; it writes the CSV before checking, so a mismatch still leaves the file — the verifier must read the exit code, not only the CSV.

### Run commands for the verifier (CPU, S03)

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.count_parameters
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_compact_cnn --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_shallow_convnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
```

Expected runtime: < 1 s for the counts; builder's CPU extrapolation ~33 s (Compact-CNN) and ~42 s (ShallowConvNet), within `LOCAL_RUN_BUDGET_MIN`. Outputs (git-ignored): `reports/network_parameter_counts.csv`, `reports/compact_cnn_benchmark_cpu.{csv,meta.txt}`, `reports/shallow_convnet_benchmark_cpu.{csv,meta.txt}`; logs and the full pytest log under `reports/logs/P09/` (decisions.md P09+). Recommended (not required): run each benchmark twice and `cmp` the CSVs, as in P08, to confirm per-device determinism for the new networks.

### Pre-committed results-review checks

1. **Counts**: `count_parameters` exit 0 and CSV `eegnet 2349, shallow_convnet 14485, compact_cnn 56021`; benchmark CSV `Params` 56021 and 14485. Any other value → REJECT.
2. **Gate**: S03 `200 stimulus, 197 clean, 3 rejected; channels kept 7, dropped none` in both logs (= R-3, = P08). Otherwise REJECT (gate divergence).
3. **Accuracies read as k/197**: every 1.0 s and 2.0 s value must equal `round(100*k/197, 2)` for an integer k; I re-derive k with a shown command.
4. **PF-30**: train accuracy (eval mode, un-augmented training fold) reported next to test, per fold from the log; high train + lower test = generalization gap, low train = optimization problem; stated as such.
5. **Diagnostic comparisons only, never targets, never R-6**: leaky flagship S03 178/197 (1.0 s) and 188/197 (2.0 s); EEGNet P08 CPU 149/169; later leak-free numbers R-7 ShallowConvNet 89.34 % = 176/197, R-7 Compact-CNN 62.94 % = 124/197 (both augmentation ON); R-9b OFF ShallowConvNet 85.79/91.37 % = 169/180, R-9b OFF Compact-CNN 42.64/46.70 % = 84/92 (`python3 -c` conversion in this audit). Leaky numbers below the leak-free OFF numbers are "unexpected under PF-01", not a failure; above them, inflation cannot be separated from model/seed/device effects in one subject — call it inconclusive.
6. **Noise**: differences of a few windows (≲ 9/197, the P08 CPU–CUDA gap, ~5 pp) between networks are noise; no ranking from S03 alone; no "best network" claim.
7. **Labels**: CSV/meta name `compact_cnn` (PF-31); meta states fs 250 → K = 29 (PF-04), leaky CV, i%5 smoothing, data source, `n_channels S03=7`.

### Required fixes

None.

### Non-blocking notes

- N1 (R2 test strength): the tester's mirror test records optimizer, scheduler, loss, seeds, DataLoader and splitter calls but not the z-score; identity there holds by construction (one `train_and_eval_cv` path). Acceptable while the driver is shared; if a script ever stops using it, add a z-score spy.
- N2: the gate-equality test compares channels, counts and labels but not the window values `X`; both sides call the same `quality_gate`, so low risk.
- N3: `count_parameters.py:50-52` writes the CSV before the R-8 check; consider writing only on success or adding a status column (see deviation (d)).

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
