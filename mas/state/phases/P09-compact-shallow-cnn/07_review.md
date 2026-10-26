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

Read: `05_run.md`, `06_verify.md` (7ced253, PASS), `reports/network_parameter_counts.csv`, `reports/{compact_cnn,shallow_convnet}_benchmark_cpu.{csv,meta.txt}`, `reports/logs/P09/` (count, run-1 benchmark logs, pytest log tail). Runs were made at `edd476e`; `git diff --stat 15aaa5d edd476e -- src scripts tests configs` is empty, so the audited code is the code that ran. `cmp` of the run-1 CSV copies against the final CSVs: identical (run 2 = run 1 for both networks; the verifier also checked meta and fold lines).

### Acceptance (verbatim: "parameter counts equal R-8 exactly; benchmarks run")

Met. `count_parameters_run1_20261026T003236.log`: `eegnet 2,349 … OK`, `shallow_convnet 14,485 … OK`, `compact_cnn 56,021 … OK`, `exit=0`; benchmark CSV `Params` 56021 and 14485. Both benchmarks `exit=0` in both runs. Pytest on the clean checkout `573 passed, 21 warnings in 219.21s` (`reports/logs/P09/pytest_20261026T002847.log`, saved per decisions.md P09+).

### Pre-committed checks 1–7

| # | Check | Obtained (source) | Result |
|---|---|---|---|
| 1 | Counts exit 0, 2349/14485/56021; CSV Params | as above | met |
| 2 | Gate S03 200/197/3, 7 kept, none dropped | both run-1 logs: `S03: 200 stimulus, 197 clean, 3 rejected; channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped [none]` | met (= R-3, = P08) |
| 3 | Percentages = k/197 | `python3 -c` → 107 → 54.31, 124 → 62.94, 171 → 86.8, 183 → 92.89; per-fold k (fold sizes 40/40/39/39/39): compact 22, 21, 19, 22, 23 (sum 107), shallow 34, 35, 35, 31, 36 (sum 171) | met |
| 4 | PF-30 train next to test, per fold | train 100.00 % in all 10 folds; test compact 48.72–58.97 %, shallow 79.49–92.31 % (logs) | met; reading below |
| 5 | Diagnostic comparisons only | table below | met |
| 6 | Noise rule | binomial SE (`python3 -c`, sqrt(p(1−p)/197)): compact 3.55 / 3.44 pp, shallow 2.41 / 1.83 pp; per-fold test SD compact 3.91 pp, shallow 4.90 pp | applied below |
| 7 | Labels | both `.meta.txt`: leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02), per-script gate, data source line, `n_channels (after the gate): S03=7`; compact: `fs 250 Hz legacy label (sets the temporal kernel K = 29, PF-04 legacy)`, file name `compact_cnn` (PF-31) | met |

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-8 EEGNet / ShallowConvNet / Compact-CNN | 2,349 / 14,485 / 56,021 | 2,349 / 14,485 / 56,021 (`count_parameters_run1_…log`) | 0 | exact | — | n/a (no deviation) |
| R-3 S03 clean / rejected | 197 / 3 | 197 / 3, 7 channels (both logs) | 0 | exact | — | n/a |

No accuracy target exists for P09 (acceptance has none); the accuracies below are diagnostics, not deviations.

### Diagnostic comparisons (S03, CPU, windows of 197, 1.0 s / 2.0 s; `python3 -c` differences shown in the review session)

| Comparison | Reference | compact_cnn 107 / 124 | shallow_convnet 171 / 183 | Reading (pre-committed rule) |
|---|---|---|---|---|
| Leaky flagship (same leak, gate, folds) | 178 / 188 | −71 / −64 | −7 / −5 | both leaky; not a model ranking (PF-01); never R-6 |
| EEGNet P08 CPU (same driver, device) | 149 / 169 | −42 / −45 | +22 / +14 | same protocol; see noise reading |
| R-9b OFF, leak-free, no augmentation | compact 84 / 92; shallow 169 / 180 | +23 / +32 | +2 / +3 | leaky above leak-free: inconclusive (inflation not separable from model/seed/device/implementation in one subject); no "unexpected under PF-01" case occurs |
| R-7, leak-free, augmentation ON (1.0 s only) | compact 124; shallow 176 | −17 | −5 | different condition (augmentation ON, P10/P11); quoted only as later numbers. The compact 2.0 s value 124 equals R-7 compact 1.0 s 124 by coincidence — different quantities, not a reproduction |

### Interpretation check

- **PF-30.** Train 100.00 % in every fold for both networks (eval mode, un-augmented training fold) with test 48.72–58.97 % (compact) and 79.49–92.31 % (shallow): a generalization gap, not an optimization failure. Compact-CNN fits 56,021 parameters on ~157 training windows per fold (`python3 -c "print(56021/157.4)"` → ≈356 per window; ShallowConvNet ≈92). 40,965 of its 56,021 parameters (73.1 %, `python3 -c`) sit in the Linear head on the unpooled 32 × 256 = 8,192 features (no pooling in the roadmap architecture), against 2,205 (15.2 %) in ShallowConvNet's head. Over-parameterisation of the head is a plausible reading of the larger gap; it is **not tested** here (no ablation), and S01/S02-type near-chance generalization (R-9 text) is not assessable on S03.
- **Noise and ranking.** ShallowConvNet − Compact-CNN = 64 windows at 1.0 s (171 vs 107), with non-overlapping per-fold ranges (79.49–92.31 vs 48.72–58.97 %); ShallowConvNet − EEGNet P08 CPU = 22 windows; Compact-CNN − EEGNet = −42. Each is well beyond the pre-committed few-window band (~9/197, the P08 device gap) and ~2–3 binomial SE. The allowed statement is: **on S03, under the legacy leaky protocol on CPU, ShallowConvNet scored above EEGNet, which scored above Compact-CNN.** It is one subject, one device, one seed set and leaky CV; no cohort ranking and no "best network" claim. The same ordering on S03 appears in the original's later leak-free R-9b OFF (169 > 145 > 84), quoted only as consistent, not as validation. ShallowConvNet vs R-9b OFF (+2 / +3) is within noise.
- **Leak (PF-01).** Compact-CNN is 23 / 32 windows above its leak-free R-9b OFF value. That is in the direction PF-01 predicts, but with K = 29 (fs 250 label), a different implementation and device, it cannot be attributed to the window-level leak from one subject: inconclusive. P11 measures the leak with grouped CV. Not "the leak inflates Compact-CNN by 12–16 pp".
- **Smoothing.** The 2.0 s gains (+17 compact, +12 shallow windows) are legacy i%5 smoothing on the clean array (R8/PF-02), not a clean 2 s decision; no claim about 2 s windows.
- **No other leak path.** Fixed 150 epochs, no early stopping, no validation split, per-window z-score, seeds 42+fold (meta lines; code audited pre-run). Test folds were used only for prediction.
- **R9.** Only S03 was prescribed; the data source (legacy windows, `data/processed/S03/`, P02 OO session) and device are stated in every meta file; the report must state both and that 1.0 s and 2.0 s are given for S03 only.

### Legacy caveats the report must carry

R1/PF-01 window-level StratifiedKFold (leaky); R8/PF-02 i%5 smoothing; R5 per-script P07 gate; PF-04 fs-250 label setting Compact-CNN's K = 29 (56,021; K = 30 and 56,693 at the true 256 Hz); PF-31 `compact_cnn` ≠ the P20 `compact_eegnet`; CPU only (CUDA numbers would differ, P08); not comparable with R-6.

### Decisions for decisions.md

- P09 | R-8 met exactly (2,349 / 14,485 / 56,021, `count_parameters` exit 0); S03 gate 197/3 (= R-3); benchmarks deterministic on CPU (run 1 = run 2). | results review | `reports/logs/P09/`
- P09 | Diagnostic only (S03, CPU, leaky): compact_cnn 107/124, shallow_convnet 171/183 of 197; ordering ShallowConvNet > EEGNet (P08 CPU 149/169) > Compact-CNN is beyond the few-window noise band on S03 but is not a cohort ranking. vs leak-free R-9b OFF: shallow +2/+3 (noise), compact +23/+32 (inconclusive; PF-01 attribution not supported from one subject). The compact 2.0 s value equal to R-7's 124 is a coincidence. | results review | same
- P09 | PF-30: train 100 % in all folds for both networks — generalization gap; Compact-CNN's head holds 73 % of its parameters (8,192 unpooled features); over-parameterisation is a hypothesis, not tested. | results review | same
- P09 | Carry-forward (non-blocking, pre-run N1–N3): z-score spy in the mirror test if a script leaves the shared driver; gate-equality test could compare X values; `count_parameters` writes its CSV before the R-8 check. | pre-run notes | `07_review.md`

## Sources spot-check

Opened in this review: `mas/04_REFERENCE_RESULTS.md` R-7, R-8, R-9b (S03 rows used above), `mas/05_PITFALLS.md` PF-28/30/31, `mas/state/reports/P08.md` §4 (EEGNet CPU 149/169, device gap 9), decisions.md P08 row (leaky flagship 178/188). Numbers in 06_verify.md (table, per-fold lines, differences −71/−64, −7/−5, −42/−45, +22/+14, +2/+3, R-9b compact 107/124 vs 84/92) re-derived from the logs and match.

Verdict: APPROVE

## Questions
