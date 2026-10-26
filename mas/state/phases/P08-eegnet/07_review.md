# P08 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Reviewed: `git diff main...HEAD` at 0ddfa37 (9 commits c04329b..0ddfa37) against `mas/03_ROADMAP.md` P08, `mas/02_REQUIREMENTS.md` §4/§5/§7, `mas/04_REFERENCE_RESULTS.md` R-7/R-8/R-9, `mas/05_PITFALLS.md` PF-01/02/28/30, `mas/state/decisions.md` P04–P08 rows.

Verdict: PASS

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) | `src/models/cnn/eegnet_cv.py:88` uses `legacy_cv(seed)` = `StratifiedKFold(5, shuffle=True, 42)` (`src/models/classical/legacy_eval.py:35-37`), the same split object as the flagship; labelled in `CV_LABEL`, console, `.meta.txt` (`benchmark_eegnet.py:98`, `:152`). Era row R1 P04–P10 and roadmap "same CV scheme as the classical benchmark". Folds pinned to sklearn by `tests/test_p08_eegnet_known_answer.py:126` |
| R2 Fit only in-fold | PASS | Nothing is fitted on test rows: z-score is per window and channel over its own time axis (`eegnet_cv.py:32-37`, §5.2 allowed), computed before the split but uses no other window (test `test_p08_eegnet_known_answer.py:89`, builder `test_p08_eegnet.py:70`); model, BN running statistics and optimizer see `Xz[tr]` only (`eegnet_cv.py:89`); test rows only through `predict_proba` in eval mode (`:91`); fixed `epochs`, no validation split, no early stopping, no checkpoint or epoch selection (`:61-72`); `label_maps(y)` is a code→index map, not a fit. No unprescribed leak found |
| R3 Filter continuous, then window | N/A | No filtering in P08; raw windows from `load_stimulus_windows` (`benchmark_eegnet.py:87`) |
| R4 Estimator small-sample bias | N/A | no coherence/PLV |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) | Per-script P07 gate. `gated_windows` (`benchmark_eegnet.py:83-91`) makes the same calls as the flagship's `prepare_subject` → `build_feature_blocks` (`src/models/classical/benchmark_runner.py:49-53`, `feature_spaces.py:44-47`): `subject_channel_names(processed, S, C, None)`, then `quality_gate(X_time, y, names, GATE_THRESHOLDS, CHANNEL_FAIL_FRACTION)` with all four limits explicit (`window_mask.py:22-23`: vpp 5–120, std 1–35, fail 0.5). Same inputs, same function, same thresholds → same `valid_mask` and kept channels; `windows_clean` = accepted rows on kept channels in original order (`quality_check.py:294`). By inspection; no equality test (note 3) |
| R6 Index layouts verified | PASS | `(B,C,T)`→`(B,1,C,T)` by `unsqueeze(1)`, layout check raises on `(B,T,C)` (`eegnet.py:51-56`); both forms equal for 7/8 ch and 128/256/512 samples (`test_p08_eegnet.py:23-36`); grouped spatial conv acts over channels only within its group (`test_p08_eegnet_known_answer.py:47`); max-norm flattens `(16,1,C,1)` per output filter (`eegnet.py:61-63`, test `:58`) |
| R7 Honest statistics | N/A | no inference in P08 |
| R8 Smoothing respects trials | LEGACY (by design) | `accuracies` → `smooth_probabilities_mod5` (`legacy_eval.py:117-122`, `smoothing.py:25-37`), reset at `j % 5 == 0` of the clean array, out-of-fold probabilities in original (condition) order (`eegnet_cv.py:91`). Matches the corrected era row (decisions.md P05, i%5 for P05–P10) and the roadmap "smoothing" convention; labelled `SMOOTH_LABEL`. Test with smoothed ≠ raw-no-reset (1.0 vs 0.9): `test_p08_eegnet_known_answer.py:159` |
| R9 Per-subject reporting with data source | PASS / note | Per-subject CSV row with device, counts and both accuracies; data source printed on the console (`benchmark_eegnet.py:123-124`), so it is in the runner's log; not in `.meta.txt` (note 1) |
| R10 Every change and test cites a source that exists and says what is claimed | CONCERN | The spec followed is the roadmap P08.1/P08.2 (opened). Lawhern et al. 2018 and the PyTorch API are named but "not opened in this run" (`03_changes_deep-learning.md` Sources); the docstring claim "post-step renorm = Keras `max_norm`" (`eegnet.py:9-11`, 03 "Differences") is unverified by an opened source. Acceptable as attribution; the report must cite the roadmap as the specification and must not present the paper as consulted (note 2) |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no copied code claimed; R11 none |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | 03 and 04 list none; last line of `mas/state/scratch/reference_access.log` is 2026-10-25T04:48:46 (ml-engineer, an earlier phase), before c04329b (13:44:40 −0600); no P08 access |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS | R1/R8/R5 legacy labelled in console, `.meta.txt` and `cv` field; reachability after the P11 fix is P11's obligation (`legacy_cv` must stay callable) |
| Tests cover every change; at least one fails on the historical bug | PASS | 25 P08 tests pass (`.venv/bin/python -m pytest tests/test_p08_eegnet.py tests/test_p08_eegnet_known_answer.py -o addopts="" -q` → `25 passed, 1 warning in 8.26s`, this audit). PF-28: per-fold seeds 42..46 checked by a spy on a fixed split (`known_answer.py:126`), so it cannot be passed by one global seed (my P04 pattern); PF-30 train accuracy on training rows (`:143`); PF-02 legacy i%5 reset (`:159`); R-8 conv-bias mutant (`:19`); 11 tester mutants fail (04_tests.md) |
| Changes match 02_plan.md and the roadmap tasks | PASS | see "Explicit judgements" 1–4 |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | fragment-built case-insensitive pattern over `git grep HEAD` and `git log main..HEAD` bodies: 0 hits; `git ls-files` has no `data/`, recording, local-instructions, tooling or answer-key path |

### Explicit judgements

1. **Architecture = roadmap P08.1; R-8 exact.** Layers as prescribed (`eegnet.py:30-44`): temporal Conv2d(1→8,(1,125),pad 62), BN, depthwise Conv2d(8→16,(7,1),groups 8), BN, ELU, AvgPool(1,4), Dropout 0.25; depthwise Conv2d(16,(1,16),pad 8,groups 16) + pointwise 1×1 → 16, BN, ELU, AvgPool(1,8), Dropout; Linear head from a dummy forward in eval mode (no RNG consumed, BN untouched). Lengths 256 → 64 → 65 → 8; flatten 16 × 8 = 128. Re-derived in this audit: `.venv/bin/python -c "...count_parameters(EEGNetSSVEP())..."` → `params 2349`, shapes temporal (8,1,1,125), spatial (16,1,7,1), depthwise2 (16,1,1,16), pointwise (16,16,1,1), head (5,128)+5; all four conv biases None. 1000+16+112+32+256+256+32+645 = 2,349 = R-8.
   **Max-norm:** on `self.spatial` only (the (C,1) depthwise spatial conv the roadmap marks), L2 norm per output filter over the channel axis, clipped to 1.0, direction kept, smaller filters untouched (`eegnet.py:58-63`). Applied once after construction and after **every** `opt.step()` (`eegnet_cv.py:60, 70`), as a Keras-style constraint. Initial renorm is a no-op at seed 42 (max initial filter norm 0.7154, this audit), so it does not perturb the init. Pointwise/depthwise2/head unconstrained (tests `known_answer.py:58, 79`).
2. **Training convention = roadmap P08.2.** z-score `(x − mean_t)/(std_t + 1e-6)` per window and channel (`eegnet_cv.py:32-37`); AdamW(lr, weight_decay 1e-2); CosineAnnealingLR(T_max = epochs, eta_min 1e-5) stepped per epoch; CrossEntropyLoss(label_smoothing 0.05); `torch.manual_seed(42 + fold)` immediately before the fold's model (`:52-53`, seed = CV seed + fold, default 42) and a DataLoader generator seeded with the same value (`:57`); 150 fixed epochs; no validation split, early stopping or selection on test folds. Train accuracy (PF-30) in eval mode on the fold's un-augmented training rows, mean over folds (`:93`). PASS.
3. **Gate and folds identical to the flagship.** Same function, arguments and thresholds (R5 row); S03 legacy arrays are the R-3/R-5/R-6 basis (197 clean / 3 rejected, 7 channels, none dropped). Folds = the same `StratifiedKFold(5, True, 42)` on the same 197 rows in the same order, so the fold membership equals the flagship's. R1/R8 labelled legacy. PASS.
4. **Deviations — all accepted.** (a) CSV always `reports/eegnet_benchmark_<device>.csv`: inside the plan's `[_<device>]` option, and it prevents the CPU run overwriting the CUDA run; accepted. (b) Size-1 batch skip: never triggers on S03 — train folds have 157 or 158 rows (test 40/40/39/39/39), last batches 29 and 30 (`157 % 32`, `158 % 32` computed in this audit); accepted, it only guards BN. (c) `cudnn.deterministic = True, benchmark = False` on CUDA (`benchmark_eegnet.py:118-120`): helps PF-28 and changes no prescribed hyper-parameter; accepted. `use_deterministic_algorithms` is not set; whether CUDA is run-to-run identical on this network is an empirical question (run command 3). (d) `quality_gate` directly instead of `prepare_subject`: same decision (point 3); accepted.

### Run commands (for the verifier) and pre-committed results-review checks

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cpu --augment off
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --subject S03 --epochs 150 --batch-size 32 --lr 1e-3 --device cuda --augment off
```

3 (recommended, about 1 min, not an acceptance criterion): re-run each command once and compare the console `[+] S03 [...]` lines of the two logs; this backs the "each is deterministic" label written into `.meta.txt`. The second run overwrites the CSV; the logs keep both.

Runtime: builder extrapolation about 30 s per device (03, synthetic smoke), far below `LOCAL_RUN_BUDGET_MIN` 120 and `MAX_GPU_HOURS_PER_PHASE` 2 (`mas/state/config.yaml:21-22`); CUDA available in `.venv` (torch 2.14.1+cu130, `cuda.is_available() True`). No human run. Outputs: `reports/eegnet_benchmark_cpu.csv`, `reports/eegnet_benchmark_cuda.csv`, matching `.meta.txt`, logs under `reports/logs/P08/`. Never point `--data-root` at a preprocessing output; no preprocessing is run (decisions.md P07).

Pre-committed checks (results review), fixed before the run:

- **Counts:** S03 `Clean Windows` 197, `Rejected` 3, channels kept 7, dropped none, on both devices (= R-3/R-5/R-6). Any other count → FAIL (gate not the flagship's).
- **Params:** 2,349 on both devices (R-8, exact).
- **Devices:** both commands exit 0; `Device` = `cpu` / `cuda` in the CSV, log header and `.meta.txt`; `nvidia-smi`/torch device name in the CUDA log or 05_run.md.
- **Accuracies as integers:** every % must be k/197 to 2 dp (1.0 s and 2.0 s). No accuracy target exists for P08.
- **CPU vs CUDA:** two different, individually labelled numbers; neither is "the" P08 result, never averaged. |Δ| ≤ 5 windows (2.54 pp) is read as numerical noise of float order; > 10 windows (5.08 pp) on the same seeds → CONCERN, and the repeat runs (command 3) decide whether it is device difference or nondeterminism (PF-28). Any conclusion drawn from the CPU–CUDA gap is not a model effect.
- **Train vs test (PF-30):** report mean train accuracy beside test for each device. Expected train ≥ ~95 % (R-9b leak-free OFF S03 train 98.86 %). Train < 90 % → optimization problem (state it); train high + test far lower → generalization gap; neither is fixed in P08.
- **Comparisons allowed:** only as labelled diagnostics. (a) Leaky classical flagship S03 R-3/R-5: 90.36 / 95.43 (178/188 of 197) — same gate, same folds, same leak; "EEGNet vs LDA" on these numbers is not a model comparison because PF-01 says leaky window-level CV inflates CNNs more than LDA. (b) R-7 (79.19, 156/197) and R-9b OFF (73.60 / 82.23 = 145/162 of 197) are leak-free P11 numbers (R-7 with augmentation) — NOT targets for P08, quote only as "later leak-free"; a P08 leaky number below 145/197 is not a failure but is noted as unexpected under PF-01. (c) Never compare with R-6 (leak-free flagship) as if comparable. The smoothed 2.0 s value is legacy i%5 on condition-ordered arrays, misaligned after S03's 3 rejections; it is not a clean 2 s decision accuracy.
- **Labels in the report:** every number carries "legacy leaky (R1/PF-01), i%5 smoothing (R8/PF-02), device X, legacy 7-channel S03 arrays (P02, OO session)".

### Required fixes

None.

### Non-blocking notes

1. (deep-learning, next touch) R9: add the data-source line (`legacy windows, <processed>/<S>/ (P02, OO), stimulus only`) and `n_channels` to `.meta.txt`; today only the console has it (`benchmark_eegnet.py:123-124`, `:150`). `discover_subjects` is imported but unused (`:46`); the script runs only named subjects (`--subject`/`--subjects`), which is enough for the roadmap's S03 run but not §4's auto-discovered subject loop.
2. (scribe) R10: cite the roadmap P08 as the architecture/training specification; Lawhern et al. 2018 only as the origin named by the roadmap, not as a consulted source; do not claim Keras equivalence of the max-norm as verified.
3. (synthetic-tester, P09/P10) No test asserts that `gated_windows` gives the same `valid_mask`/kept channels as `prepare_subject` on a tree with a bad channel; correct today by inspection. Add one when P09/P10 reuse `gated_windows`, so a later threshold edit in one path cannot drift (PF-07 class of bug).
4. (verifier) The results check of counts is the real-data confirmation of judgement 3; record the console channel line.

## Results review

Read: `05_run.md`, `06_verify.md` (ac856ad, PASS), `reports/eegnet_benchmark_{cpu,cuda}.csv` and `.meta.txt`, the four logs `reports/logs/P08/benchmark_eegnet_{cpu,cuda}_run{1,2}_*.log` and the run copies. The code is unchanged since the pre-run audit: `git diff --stat 0ddfa37 cf62bb3` touches only `mas/state/` files. Every log header shows `HEAD cf62bb3…` and `status: []`. Data source: legacy 7-channel arrays `data/processed/S03/` (P02, OO session), stimulus windows only.

Re-checked in this review:
- The run1 and run2 CSV copies are byte-identical on each device (`cmp`).
- The per-fold lines and the `[+]` line of run1 and run2 are identical on each device, apart from the wall-time field (`diff`).
- I derived fold window counts with `.venv/bin/python -c "..."`, using test-fold sizes 40/40/39/39/39 and training-fold sizes 157/157/158/158/158.

### Acceptance (verbatim): "trains on CPU and GPU; numbers recorded (Era-A leaky)"

**Met.**
- Both devices trained: 4/4 runs ended with `EXIT_CODE=0`. CPU took 32 s and CUDA 20 s (the RTX 3050 Laptop GPU).
- The numbers are recorded per device in the CSV, the log and `.meta.txt`.
- Every artefact carries the Era-A labels: `cv=StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky)`, legacy i%5 smoothing (R8/PF-02) and the per-script gate (R5 legacy).

### Pre-committed checks

| Check (pre-run audit) | Obtained (log/CSV) | Result |
|---|---|---|
| Counts 197 / 3, 7 kept, none dropped | `200 stimulus, 197 clean, 3 rejected; channels kept 7 [PO3, POz, PO4, PO8, O1, Oz, O2]; dropped [none]` on both devices | PASS (= R-3/R-5/R-6; confirms that the gate is the flagship's on real data) |
| Params 2,349 | `params 2349` on both devices | PASS (R-8 exact) |
| Both exit 0, device labelled | CSV `Device` cpu/cuda, `[+] S03 [cpu]` / `[+] S03 [cuda]`, `.meta.txt` line 1 | PASS |
| Accuracies are k/197 | CPU 149 / 169, CUDA 140 / 160 (fold sums 31+22+29+31+36 = 149 and 32+21+29+28+30 = 140) | PASS |
| CPU vs CUDA gap | 9 windows on both 1.0 s and 2.0 s (4.57 pp) | inside the pre-committed "between" band (> 5 and ≤ 10 windows); no CONCERN; read below |
| Train vs test (PF-30) | train CPU 98.34 %, CUDA 98.60 %; test 75.63 % / 71.07 % | PASS; this is a generalization gap |
| Determinism per device (recommended repeat) | run1 = run2 on each device | PASS; the `.meta.txt` label is supported |

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-8 EEGNet params | 2,349 | 2349 (cpu, cuda) | 0 | yes (exact) | — | — |
| R-3/R-5/R-6 S03 counts | 197 clean / 3 rejected, 7 ch | 197 / 3, 7 kept | 0 | yes (exact) | same gate as the flagship | — |
| Accuracy | no P08 target (leaky; R-7/R-9 are later leak-free targets) | CPU 75.63 / 85.79; CUDA 71.07 / 81.22 | n/a | n/a | diagnostic comparisons below | — |

There are no deviations to accept.

### Interpretation check

1. **CPU vs CUDA, 9 windows.** Each device repeats itself exactly, so the gap is a device effect, not run-to-run nondeterminism (PF-28) and not a model effect. Same seeds and same folds on different floating-point kernels lead to different weights after 150 epochs, and that changes some borderline windows.
   - The gap is small next to the uncertainty of the estimate. Per-fold test accuracy ranges from 55.00 % to 92.31 % on CPU (fold SD 13.45 pp) and from 52.50 % to 80.00 % on CUDA (SD 10.84 pp). The binomial SE at p ≈ 0.73 with n = 197 is 3.16 pp (computed). The 4.57 pp gap is about 1.4 SE.
   - Two thirds of the gap comes from one fold: fold 4 differs by 6 windows (36 vs 30). The per-fold differences are −1, +1, 0, +3, +6.
   - Conclusion: on S03, EEGNet's leaky 1.0 s accuracy lies between 140 and 149 of 197, depending on the device. Neither device's number is "the" P08 result, and they must never be averaged. A seed or device change alone moves this estimate by about 5 pp, so later A/B comparisons (P10 augmentation) must use the same device and seeds (PF-28) and should treat effects of a few windows as noise.
2. **PF-30, train vs test.** Training accuracy is about 98 % on both devices: CPU folds 95.54–100 %, CUDA 97.45–100 %. Test accuracy is 71–76 %, so the network optimizes and then fails to generalize to part of the held-out windows; this is not an optimization problem. Fold 1 is hard on both devices (55.00 % / 52.50 % test at 96.18 % / 97.45 % train). With 157–158 training windows and 2,349 parameters, a gap of this size is expected. The leak-free reference without augmentation shows the same pattern (R-9b S03 OFF: train 98.86 %, test 73.60 %).
3. **Diagnostic comparisons, labelled and not targets.**
   - (a) Leaky classical flagship on S03 (R-3/R-5: 90.36 / 95.43 % = 178 / 188 of 197; same gate, same folds, same leak). EEGNet is 29–38 windows lower at 1.0 s (149 / 140 vs 178) and 19–28 windows lower at 2.0 s (169 / 160 vs 188). PF-01 says leaky window-level CV inflates CNNs more than LDA. Here, though, the leaky CNN is still well below the leaky LDA flagship, so no leak-driven CNN advantage appears on S03. This is not a model ranking: both numbers are leaky, it is one subject, and it is one configuration without augmentation.
   - (b) Later leak-free numbers: R-7 (augmentation on) 79.19 % = 156/197; R-9b without augmentation 73.60 / 82.23 % = 145 / 162 of 197. CPU (149 / 169) is above the no-augmentation leak-free reference by 4 / 7 windows. CUDA (140 / 160) is below it by 5 / 2 windows. As pre-committed, a leaky number below 145/197 is not a failure; it is noted as unexpected under PF-01, because leaky CV should not score below leak-free CV.
     - The difference is inside the device spread in point 1, so the leak inflation for EEGNet on S03 is not detectable at this precision. Here EEGNet ranges from −5 to +4 windows against a reference produced by the original's code; LDA shows +7 windows (leaky 178 vs leak-free R-6 171/197).
     - The comparison is inconclusive. It must not be quoted as "no leakage for CNNs"; P11 measures the leak effect with matched code.
   - (c) Not compared with R-6 as if comparable.
4. **Caveats that must accompany every P08 number.**
   - The CV is legacy and leaky: five 1 s sub-windows of one trial land in train and test (PF-01).
   - The "2.0 s smoothed" figure is the legacy i%5 average over the condition-ordered clean array (PF-02). S03's 3 rejected windows shift the 5-blocks after each rejection, so some pairs average windows of adjacent trials. Usually the class is the same, so the effect is small, but it is not a clean 2 s decision. The +20-window smoothing gain on both devices (149→169, 140→160) is a legacy-rule figure, not a measured 2 s improvement.
   - This is not the P04 no-reset rule.
   - Data are the legacy 7-channel arrays (P02, OO session). fs 250 is a label only (EEGNet does not use it).
   - Every number is per device.
5. **Leakage in fitted objects.** This was cleared in the pre-run audit: z-score per window, BN and optimizer on training rows only, fixed epochs, no selection on test folds. The run used the audited code (`git diff --stat 0ddfa37 cf62bb3` touches only `mas/state/`), so nothing new arises.

### Decisions for decisions.md

- 2026-10-25 | P08 | Results accepted: EEGNet S03 (legacy leaky R1/PF-01, i%5 smoothing R8/PF-02, legacy 7-ch arrays, P07 gate) CPU 75.63 / 85.79 % (149 / 169 of 197), train 98.34 %; CUDA 71.07 / 81.22 % (140 / 160), train 98.60 %; 197/3 and 2,349 params exact on both; each device run-to-run identical | results review | `P08-eegnet/07_review.md`, `reports/eegnet_benchmark_{cpu,cuda}.csv`
- 2026-10-25 | P08 | The 9-window CPU–CUDA gap (4.57 pp, 6 of it in one fold) is a device effect, not nondeterminism or a model effect; it is about 1.4 binomial SE, and per-fold test accuracy spans 52.5–92.3 %. P09/P10 A/B comparisons use one fixed device and seeds, state it, and treat differences of a few windows as noise | results review | same
- 2026-10-25 | P08 | Diagnostic only: leaky EEGNet is 29–38 windows below the leaky flagship (178/197), so PF-01's "CNNs inflate more" shows no CNN advantage on S03. EEGNet leaky vs the later leak-free no-augmentation reference (R-9b 145/197) is −5 to +4 windows across devices (inconclusive; never quoted as "no leak for CNNs"; P11 measures it). PF-30 reading: generalization gap (train ~98 %, test 71–76 %) | results review | same
- 2026-10-25 | P08 | Carry-forward (non-blocking): data-source line and `n_channels` in the EEGNet `.meta.txt`; unused `discover_subjects` import (deep-learning, next touch); gate-equality test `gated_windows` vs `prepare_subject` (synthetic-tester, P09/P10); the report cites roadmap P08 as the specification, with Lawhern et al. 2018 only as the origin named there | pre-run audit notes | same

## Sources spot-check

Opened in this review: `05_run.md`, `06_verify.md`, both CSVs and both `.meta.txt`, the four P08 logs (run1 grep and run1/run2 diff), and `mas/04_REFERENCE_RESULTS.md` R-7/R-8/R-9b (read in the pre-run audit of this session). The verifier's numbers (counts, k/197, gap 9, determinism) agree with the logs. 06 quotes my pre-committed rule for numbers below 145/197 accurately. Its prose figures (4.56 / 4.57 pp) match the CSV differences 75.63 − 71.07 and 85.79 − 81.22.

Verdict: APPROVE

## Questions
