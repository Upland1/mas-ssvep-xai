# P10 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Audited: `git diff main...HEAD` at `db72b7f` (code: `src/preprocessing/dataset/augmentation.py` NEW, `src/models/cnn/eegnet_cv.py`, `src/models/cnn/benchmark_common.py`, the three `benchmark_*.py` docstrings, `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py` NEW, `tests/test_p10_augmentation.py` NEW, `tests/test_p10_augmentation_known_answer.py` NEW, `tests/test_p08_eegnet.py`, `tests/test_p09_compact_shallow.py`), against `mas/03_ROADMAP.md` P10 (lines 355–381), `mas/02_REQUIREMENTS.md` §6 line 201, `mas/04_REFERENCE_RESULTS.md` tolerance rules (line 12) and R-9 (lines 126–176), `mas/05_PITFALLS.md` PF-01/02/28/29/30/31 (lines 9, 16, 149–164), `decisions.md` P08–P10 rows. ACK 02_plan.md scientific-reviewer 2026-10-26.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) | `StratifiedKFold(5, shuffle, 42)` over windows, `src/models/classical/legacy_eval.py:35-37`, used at `src/models/cnn/eegnet_cv.py:111`; both arms share the same split (same `seed`, same `yi`). Era matrix: R1 legacy P04–P10. Labelled in console (`benchmark_nn_augmentation.py:113`) and `.meta.txt` (`:146`, plus `cv=` line from `benchmark_common.py:89`). Outputs frozen under `reports/legacy_leaky/` (`:151-156`) |
| R2 Fit only in-fold | PASS | No fitted statistic crosses windows: z-score per window/channel (`eegnet_cv.py:41-46`), noise std per channel of the current window (`augmentation.py:29-31`), one scale per window (`:37`). The dataset is built from `train_model`'s own `X` = `Xz[tr]` (`eegnet_cv.py:112`, `:78`), so mixup partners come from the training fold only (`augmentation.py:70`, `:81-82`). Test pass and train-accuracy pass call `predict_proba` on `Xz[te]`/`Xz[tr]` in eval/no-grad (`eegnet_cv.py:49-55`, `:115`, `:117`) |
| R3 Filter continuous, then window | N/A | No filtering added; the networks take raw legacy windows. Circular roll (`augmentation.py:44`) is the prescribed op, not a filter. |
| R4 Estimator small-sample bias | N/A | no coherence/PLV |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) | P07 two-tier gate via the shared network driver `gated_windows` (`benchmark_nn_augmentation.py:119`; same call as the P09 driver), era matrix R5 legacy until P16; gate run once per subject and shared by both arms (`:119-129`) |
| R6 Index layouts verified | PASS | Axis conventions `(C, T)` / `(n, C, T)`: per-channel std on `axis=-1` proven with channel stds 1/7/40 (`tests/test_p10_augmentation_known_answer.py:22-34`); roll along time proven on a ramp with exact `np.roll` match (`:61-74`; builder `tests/test_p10_augmentation.py:43-51`); scale ratio identical across channels (`known_answer.py:48-58`) |
| R7 Honest statistics | N/A | no inferential statistics in P10; see the pre-committed noise rule below |
| R8 Smoothing respects trials | LEGACY (by design) | `i % 5` reset on the clean array (`legacy_eval.py:30`), the roadmap convention for legacy folders (`03_ROADMAP.md:18-19`) and era-matrix legacy until P11; same ruling as P09 (`mas/state/phases/P09-compact-shallow-cnn/07_review.md:31`); labelled `benchmark_common.py:90`, `benchmark_nn_augmentation.py:146` |
| R9 Per-subject reporting with data source | PASS | one row per discovered `S\d+` folder (`benchmark_nn_augmentation.py:57-60`, `:118-136`), 1.0 s and 2.0 s for both arms + Clean Windows; data source line and `n_channels` in console and `.meta.txt` (`:111-114`, `:144-146`); device in the header line. The CSV has no Device column (not in §6); the meta carries it |
| R10 Every change and test cites a source that exists and says what is claimed | PASS (note N5) | Module and script docstrings cite P10.1/P10.3 and PF-28/29/30 (`augmentation.py:1-11`, `benchmark_nn_augmentation.py:1-14`); test tables cite roadmap/analytic/PF (04_tests.md). PF and roadmap lines checked: they say what is claimed |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no copied code (03 and 04: reference not opened) |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | 03 and 04 list none; the last entries of `mas/state/scratch/reference_access.log` are 2026-10-25 ml-engineer (P06) and my own P09 privacy scan (2026-10-26T00:25, logged because of the pattern text); no P10 entry |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS | P10 fixes nothing; OFF is the default in every driver (`benchmark_common.py:57`) and the OFF code path is byte-identical to main: own check, `git show main:src/models/cnn/eegnet_cv.py` exec'd as a module vs the branch, same synthetic data (`make_windows(n_trials=4, seed=0)`, 3 epochs, CPU) → both `adf2cc7d…5322c` = pinned `EEGNET_SMOKE_PROBA_SHA256`; branch ON ≠ OFF (command in the note below). OFF header text unchanged (`AUGMENT_NOTE["off"] = ""`, `benchmark_common.py:45`, `:97`); OFF CSV name unchanged (`:141`) |
| Tests cover every change; at least one fails on the historical bug | PASS | PF-29 cross-class mixup: `known_answer.py:141-148` and builder negative control `test_p10_augmentation.py:91-97`; PF-29/PF-30 augmentation in the test or train-accuracy pass: marker test `known_answer.py:151-182` (+1000 offset never in the 10 eval calls, always in training batches); PF-28 same init: `test_p10_augmentation.py:165-182`, generator seeds 42..46 and torch RNG untouched `known_answer.py:185-201`; order/p/independence `:97-128`; folded Beta mean by quadrature `:77-88`; A/B values, delta sign, column swap, arm order, freeze `:233-258`; warning boundary `:269-275`. 15 mutants listed by the tester. My run of the P08–P10 files: `71 passed, 1 warning in 34.49s` |
| Changes match 02_plan.md and the roadmap tasks | PASS | P10.1 signatures and defaults = roadmap (`augmentation.py:27`, `:34`, `:40`, `:47`, `:64-65`); order `OP_ORDER` (`:20`, `:77-88`); λ = max(λ, 1−λ) (`:51-52`); class lookup precomputed (`:70`); float32/long (`:92`). P10.2 `--augment {off,on}`, default off (`benchmark_common.py:57-58`). P10.3 `--model` choices incl. alias (`benchmark_nn_augmentation.py:49-51`, `:65`), `--epochs` default 150, OFF then ON (`:125`), train acc = final model, eval mode, un-augmented `Xz[tr]` (`eegnet_cv.py:117`), warning on OFF train < 40 % (`:133`), §6 columns (`:52-53` vs `02_REQUIREMENTS.md:201`), Mean row, `.meta.txt`, `--freeze-legacy`. Builder deviations judged in N1–N3 |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git diff main...HEAD --name-only` has no `data/`, `reports/`, `outputs/`, `baselines/`, answer-key, recording-suffix or local-tooling path. Fragment-built case-insensitive vendor/assistant pattern (+ the co-author trailer): `git grep` over all of HEAD = 0 (main still has 1, the P09.md line corrected on this branch, `decisions.md` P09 privacy row); `git log main..HEAD` messages, author and e-mail = 0. 11 commits, author Sebastian Oliva |

### Required fixes

None.

### Non-blocking notes

- **N1 Mixup partner may be the anchor itself** (`augmentation.py:81-82`). The roadmap asks for a same-class partner and does not exclude the anchor. With about 32 training windows per class (`python3 -c "print(0.8*197/5)"` → 31.52), a self-pair (identity) happens in about 1/32 of mixups, so the effective mixup rate is about 0.484 instead of 0.5 (`python3 -c "print(0.5*(1-1/32))"` → 0.484375). Accepted as a reading of the spec, not a deviation from it; no change before the run.
- **N2 `*_aug_benchmark_<device>.csv`** for single-subject ON runs (`benchmark_common.py:141`). Accepted: it keeps the P08/P09 OFF CSVs (`reports/eegnet_benchmark_cpu.csv`, the regression basis) from being overwritten. These files are not a roadmap output and are not produced by the P10 run commands.
- **N3 P08/P09 test edits** (`test_p08_eegnet.py:114`, `:128`; `test_p09_compact_shallow.py:138`). The old assertion encoded "only `off` before P10", which P10.2 supersedes. The new one still checks that argparse rejects invalid values. Accepted; no assertion was weakened beyond that.
- **N4 Untested but correct by inspection.** (a) The ON arm uses the same seeded DataLoader generator as OFF (`eegnet_cv.py:74`, `:79`, one line shared by both arms), so batch order is identical. A variant that drops `generator=` only for ON would pass every test (init equality and ON determinism still hold) and would confound the A/B. (b) The augmented dataset is built from `train_model`'s argument (`Xz[tr]`). No test asserts that its rows equal `Xz[tr]`. A variant passing all of `Xz` (test windows in training) would get through the marker test. Both are out of reach of a single-line slip in the current structure. Recommended for P11, where the A/B is rerun leak-free: assert `len(dataset) == len(tr)` and that the loader's generator is seeded for both arms.
- **N5 Handoff hygiene.** `03_changes_deep-learning.md` has no numbered Sources list and no `## Questions` ACK line, and `04_tests.md` has no ACK line (`PROCEDURES.md` "Every agent"). Not a correctness issue.
- **N6 Header rewrite** (`benchmark_nn_augmentation.py:110`) rewrites `augment=on` into `augment=OFF then ON …` by string replacement, so it depends on the line position. It is covered by `test_p10_augmentation.py:232` ("OFF then ON" in the output).

Own regression command (no files written):
`.venv/bin/python - <<EOF` … exec `git show main:src/models/cnn/eegnet_cv.py` as a module; `train_and_eval_cv(make_windows(n_trials=4, seed=0), epochs=3, device="cpu")` for main, branch OFF and branch ON → `main adf2cc7d6252d06f2bcd70ce15d14d118a5816061c64e1ec5145f3836e75322c`, `branch OFF adf2cc7d…5322c`, `pinned adf2cc7d…5322c`, `OFF==main True ON==OFF False`.

### Run commands (approved as in 02_plan.md)

```bash
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model eegnet --epochs 150 --device cpu --freeze-legacy
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model compact_cnn --epochs 150 --device cpu --freeze-legacy
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model shallow_conv_net --epochs 150 --device cpu --freeze-legacy
```

All subjects are discovered (`data/processed/S01…S05`), batch 32, lr 1e-3 and seed 42 by default (`eegnet_cv.py:32-34`), which are the P08/P09 settings. Runtime: P08/P09 CPU per subject-arm took 32 / 43 / 57–59 s (EEGNet / Compact / Shallow; `mas/state/reports/P08.md:81`, `P09.md:97-98`). 10 subject-arms each gives about 5.5 + 7 + 10 ≈ 23 min, plus an ON overhead under 10 % (03). That fits within `LOCAL_RUN_BUDGET_MIN` 120 (`mas/state/config.yaml:21`). No human run is needed. The run writes `reports/augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` (+ `.meta.txt`) and the `reports/legacy_leaky/` copies. It does not touch the P08/P09 CSVs. The verifier saves one log per command and the pytest log under `reports/logs/P10/`.

### Pre-committed results-review checks

Numbers derived with `python3 -c "print([round(100*k/197,2) for k in (149,169,107,124,171,183)]); print(3.00-3, 7.34+3, 1.79-3, 1.79+3)"` → `[75.63, 85.79, 54.31, 62.94, 86.8, 92.89]`, `0.0 10.34 -1.21 4.79` (rounded).

1. **Regression first (decisions.md P09 row).** The OFF arm on S03, read from the A/B CSV and log, must equal P08/P09 CPU exactly. EEGNet: 75.63 / 85.79 (149 / 169 of 197). Additional checks on the same unchanged code path and device: Compact-CNN 54.31 / 62.94 (107 / 124), ShallowConvNet 86.80 / 92.89 (171 / 183). S03 Clean Windows must be 197 for each model. Any mismatch is investigated before the A/B is read, and an unexplained mismatch means REJECT.
2. **R-9a, EEGNet cohort (Mean row).** 1.0 s Delta inside [+3.00, +7.34] pp is "in the recorded range". Inside [0.00, +3.00) or (+7.34, +10.34] it is within the NN cohort tolerance (±3 pp), with the position stated. Below 0.00 (a cohort sign flip) or above +10.34 it is outside tolerance. For 2.0 s, +1.79 ± 3 gives [−1.21, +4.79] (legacy i%5 figure; no 2 s decision claim). For scale: the P08 CPU–CUDA gap of 9/197 windows on one subject corresponds to about 2.04 pp on a 5-subject mean (`9/197/√5`), so values near the band edges are within run-to-run uncertainty.
3. **Outside tolerance: explanation or REJECT.** First do one investigation round on the existing output: per-fold lines, per-subject deltas, train accuracies, and the regression check. Then R11 is allowed (after-attempt, deviation beyond tolerance) to compare augmentation parameters and protocol with the original. Accept only a named, spec-level difference or documented nondeterminism with evidence, recorded for `decisions.md`. REJECT if a defect is found in the ON path (leak, init difference, augmentation reaching evaluation) or if the run was re-done with other seeds, p, α or epochs to land in range (golden rule 5). A spec-conformant, defect-free result outside the band is reported as "R-9a not reproduced", with the explanation.
4. **Subjects improved and S02.** Count subjects with 1.0 s Delta > 0 (0.00 counts as not improved) against R-9a's 4/5, and give S02's sign. The per-subject tolerance is ±5 pp, so a different sign within ±5 pp is reported but is not a deviation.
5. **S01/S02 PF-30 reading.** "Reproduced" means that, for both S01 and S02, OFF 1.0 s test ≤ 40 % (2× chance; R-9a ≈ 27–28 %, ±5 pp → 22–33 % matches) AND OFF train ≥ 70 %. That pattern is a generalization failure, not an optimization failure. OFF train < 40 % (the script's warning) is an optimization failure, and the criterion is then not reproduced. Test > 40 % is a deviation from R-9a that must be explained (leaky CV inflation was not detectable for EEGNet in P08). ON arms are reported the same way.
6. **Compact-CNN and ShallowConvNet.** Per-subject and cohort deltas with sign, plus train OFF/ON. These are diagnostic only, with no tolerance verdict. R-9b leak-free values (Compact +17.16 / +16.46, Shallow +2.53 / +2.40) are context, not targets. A large gain is read as legacy-leaky and is checked against train accuracy and the regression row. Flag coincident numbers (e.g. 62.94 = P09 Compact S03 2.0 s = R-7 Compact 1.0 s).
7. **Per-subject counts.** For every subject and arm, k = round(pct × Clean Windows / 100), with k/n reproducing the CSV value to 2 dp. Deltas are also given in windows.
8. **Noise rule.** A per-subject delta of 9 windows or fewer (the P08 device gap) is "no detectable effect". A cohort delta under about 2 pp is inconclusive. CPU only, one seed set; no significance claim.
9. **Never R-6.** No comparison with R-6 or the leak-free flagship. Every number is labelled legacy leaky CV, i%5 smoothing, CPU, legacy 7-channel arrays.

## Results review

Verdict: APPROVE

Read: `05_run.md`, `06_verify.md` (`4d403a4`, PASS); `reports/augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` (opened) and the console blocks of `reports/logs/P10/benchmark_nn_augmentation_{eegnet_20261026_012120,compact_cnn_20261026_012749,shallow_conv_net_20261026_013606}.log`. What ran is what was audited: `git diff --stat db72b7f 5f2d5eb -- src scripts tests configs` is empty, and every log header names `5f2d5eb` with a clean tree. `cmp` of each CSV and `.meta.txt` against `reports/legacy_leaky/` is identical for 3 of 3 models. `grep -c WARNING` gives 0 in all three logs. Every number below is legacy leaky CV (window-level `StratifiedKFold(5, shuffle, 42)`, R1/PF-01), i%5 smoothing (R8/PF-02), CPU, legacy 7-channel arrays `data/processed/<S>/` (P02, OO session), stimulus windows, P07 per-script gate, one seed set (42 + fold). None of it is compared with R-6.

Arithmetic: `python3 -c` over the CSV values gives EEGNet 1.0 s window deltas `[15, -3, 10, 2, 7]`; mean of deltas `3.11`; mean without S01 `2.02`; position in the band `0.11` above +3.00 and `4.23` below +7.34; Compact-CNN S04 `85` windows, R-9b S04 `85` windows; S01 EEGNet per-fold test deltas `[12.5, 5.0, -2.5, 10.0, 12.5]`; EEGNet train-accuracy drops ON vs OFF `9.37 10.96 4.35` (S01, S02, Mean); differences from R-9b `1.1` (EEGNet), `-0.52` (Shallow), `-3.04` (Compact).

### Pre-committed check 1: regression (read first)

S03 OFF equals P08/P09 CPU exactly for all three models: EEGNet 75.63 / 85.79 (149 / 169), Compact-CNN 54.31 / 62.94 (107 / 124), ShallowConvNet 86.80 / 92.89 (171 / 183) of 197 (`06_verify.md`, and the CSV rows above). This confirms on real data that the P09 refactor and the P10 `augment` plumbing did not change the OFF path. It agrees with my synthetic hash check in the pre-run audit. S03 Clean Windows is 197 for all three models, and the counts are 200 / 196 / 197 / 197 / 200 for S01–S05.

### Deviations from references

| Ref | Expected | Obtained (log/CSV) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-9a EEGNet cohort 1.0 s gain | +3.00 (first leaky run) … +7.34 pp (last leaky run); NN cohort ±3 pp | +3.11 pp (63.93 → 67.04), `augmentation_ab_eegnet.csv` Mean | +0.11 from the first-run value | yes, inside the recorded range | It sits at the lower edge, next to the first-run value. The two original values span 4.34 pp of run-to-run and code-evolution variation. One seed set cannot place our value more precisely within that span (see the interpretation section) | yes |
| R-9a EEGNet cohort 2.0 s gain | +1.79 pp ±3 → [−1.21, +4.79] | +2.90 pp (68.18 → 71.08) | +1.11 | yes | Legacy i%5 figure, not a 2 s decision | yes |
| R-9a subjects improved | 4/5, S02 regressed | 4/5 at 1.0 s (S01 +15, S03 +10, S04 +2, S05 +7 windows); S02 −1.53 pp (−3 of 196) | — | yes | S02's sign matches, but −3 windows is no detectable effect (rule 8) | yes |
| R-9a S01/S02 near chance | ≈ 27–28 % (±5 pp → 22–33 %) | OFF 28.00 / 27.04 %; ON 35.50 / 25.51 % | OFF 0 to −1; S01 ON +7.5 above 28 | OFF yes; S01 ON 35.50 is 2.5 pp above the 33 % edge | R-9a does not say which arm its 27–28 % came from. Our OFF arm matches it. The S01 ON value is 71/200 windows, still below 2× chance, and reflects S01's ON gain | yes (OFF matches; S01 ON reported as its own number) |
| R-9b, R-7 (leak-free, P11) | — | context only | — | not applicable | Different CV; P11 target | — |

No value is outside tolerance, so no investigation round and no R11 consultation was needed. The reference access log has no P10 entry (`06_verify.md`, R11 line).

### Interpretation check

**Acceptance clause 1, verbatim: "EEGNet cohort augmentation gain in the range recorded by R-9a (first leaky run +3.00 pp 1.0 s / +1.79 pp 2.0 s with 4/5 subjects improved and S02 regressed; the last leaky run before the fix +7.34 pp 1.0 s) — explain where yours falls".**
**Met.** The 1.0 s cohort gain is +3.11 pp, inside [+3.00, +7.34] and 0.11 pp above the lower edge, essentially the first-run value. The 2.0 s gain is +2.90 pp against +1.79. 4/5 subjects improved and S02 regressed, as in the first run.
- **Where it falls and why the position is not resolved.** The gain is one deterministic CPU run with one seed set. For scale, the P08 CPU–CUDA gap on one subject (9/197 windows) corresponds to about 2.04 pp on a 5-subject mean. The +0.11 pp margin over the edge and the 4.23 pp distance to +7.34 pp are both within or near that scale. "In the range" is supported. "At the first-run end rather than the last-run end" is not a resolved statement. Nothing here supports a claim that our setup matches the original's first or last code version.
- **Per subject, in windows.** S01 +15/200 and S03 +10/197 exceed the 9-window noise line. S05 +7, S04 +2 and S02 −3 do not. The cohort gain is driven by S01 and S03: without S01 the mean of the four other deltas is +2.02 pp. Within S01, 4 of 5 folds improved (per-fold test deltas +12.5, +5.0, −2.5, +10.0, +12.5 pp), so the S01 gain is not a single-fold artefact. A direction-only reading is also weak: 4/5 positive deltas is p = 0.1875 one-sided under a fair-coin null (`5/32 + 1/32`). This rests on folds and windows that are not independent under leaky CV, so there is no significance claim.
- **Regularisation signature.** ON lowered EEGNet training accuracy on the un-augmented fold (S01 −9.37, S02 −10.96, cohort −4.35 pp). On S01 and S03 test accuracy rose at the same time. That is the expected behaviour of augmentation as a regulariser, and the training-accuracy pass was not augmented (pre-run audit; marker test).

**Acceptance clause 2, verbatim: "S01/S02 near chance with high training accuracy is reproduced and interpreted (generalization failure, not optimization failure)".**
**Reproduced.** OFF test accuracy is S01 28.00 % (56/200) and S02 27.04 % (53/196), against 20 % chance. OFF training accuracy on the un-augmented fold is 83.25 % and 81.38 %, both ≥ 70 %. The script's warning for OFF train < 40 % never fired. Per fold, S01 OFF train is 79.38–90.00 % and test 22.50–45.00 %; S02 OFF train is 72.61–85.90 % and test 20.51–35.90 %.
- **Interpretation.** EEGNet fits most of its training fold, so it does not fail to optimise. It fails to transfer what it fits to held-out windows, which is a generalization failure (PF-30).
- **The leaky protocol makes this sharper.** Under window-level CV, the training fold holds sibling windows of the test trials, which is the easiest possible transfer. EEGNet still stays near chance, so whatever it learns on S01/S02 is not the stimulus response.
- **Comparison with other networks.** ShallowConvNet reaches 58.00 % (S01) and 37.24 % (S02) OFF on the same windows. Compact-CNN reaches 24.00 % and 32.65 % with 100 % train. So the S01/S02 difficulty is shared by all three networks, and ShallowConvNet suffers least on S01.
- **ON arm.** The same pattern holds: S01 35.50 % / train 73.88 %, S02 25.51 % / train 70.42 %. Augmentation does not change the diagnosis.

**Compact-CNN (diagnostic; no tolerance verdict).** Cohort Δ is +14.12 / +11.39 pp. Train accuracy is 100 % in both arms for every subject, so OFF is pure overfitting, and the ON gain comes from regularising that.
- **S04: +43.15 pp (+85 windows) from an OFF level of 53.30 %.** S04 is ≥ 98.48 % for EEGNet and ShallowConvNet, so Compact-CNN OFF failing to generalise on an easy subject is the anomaly, and augmentation removes it. This matches the pattern recorded leak-free in R-9b (S04 OFF 54.82 → ON 97.97).
- **Coincidence flag.** Our leaky S04 Δ (85/197 = 43.15 pp) equals R-9b's leak-free S04 Δ (85/197 = 43.15 pp) exactly, while both arms differ by 3 windows (53.30 vs 54.82; 96.45 vs 97.97). Different CV, different quantities: this is a coincidence and must not be written as "reproduces R-9b".
- **S02.** S02 regresses by −10.71 / −14.28 pp (−21 / −28 windows), with ON 21.94 / 20.92 % at chance. This is larger than the noise line and has the same sign as R-9b S02 (−7.14). It is reported, not explained: one seed set.
- **Context, not a target.** The cohort Δ is 3.04 pp below R-9b's leak-free +17.16. That is context only: no tolerance is applied across protocols.
- **Kernel label.** Compact-CNN is still the fs-250 K = 29 network (PF-04 legacy label, PF-31 naming `compact_cnn`).

**ShallowConvNet (diagnostic).** Cohort Δ is +2.01 / +2.72 pp. Every per-subject 1.0 s delta is ≤ 10 windows (S01 +10, S03 +8, S05 +2, S02 0, S04 0), so no single subject shows a detectable effect. The cohort direction is positive. R-9b's leak-free +2.53 is context only. Train accuracy is 100 % in both arms.

**Legacy leaky caveats.**
1. All A/B numbers use window-level CV. Mixup, shift and scale can let a network memorise trial-specific background shared by sibling windows across the train/test split. The leaky gain may therefore be inflated, or masked, relative to a trial-grouped protocol. The direction cannot be known before P11.
2. The 2.0 s column is the legacy i%5 average over the condition-ordered clean array (PF-02), with 5-blocks misaligned in subjects with rejected windows (S02 196, S03 197, S04 197 clean windows). It is not a 2 s decision accuracy.
3. P11 measures the leak-free A/B (`StratifiedGroupKFold` on trial ids, trial-aware smoothing). R-9b is its target. No P10 delta may be quoted as an augmentation effect without this label.
4. Statistics. The unit is the window. There is no permutation or paired test, and no multiple-comparison correction across 3 models × 5 subjects × 2 horizons. Only the R-9a band comparison is an acceptance criterion; everything else is descriptive.

**Leakage audit of fitted objects.** No new fitted object exists beyond the networks. Per-window z-score uses no other window. The augmentation generator is per fold and draws only from the training fold. There is no validation split and no early stopping, and the epoch count is fixed (150), so no choice was made on test folds. There was no hyperparameter search: p, α, std_frac, scale range and shift fraction are the roadmap values, unchanged between audit and run.

**Era-A close.** P10 is the last phase run under the legacy evaluation protocol of R1 (window-level CV) and R8 (i%5 smoothing); the era matrix enforces both from P11. All P04–P10 network numbers, including these CSVs, are frozen under `reports/legacy_leaky/` and superseded by P11. Three legacy items continue past P11, per the era matrix: the P07 per-script gate (R5, until P16), the fs-250 label that sets Compact-CNN's K = 29 (until P16), and legacy folders as the data source. P11 must state these as well.

### Decisions for decisions.md

- 2026-10-26 | P10 | R-9a accepted. EEGNet cohort augmentation gain +3.11 pp at 1.0 s (inside [+3.00, +7.34], at the lower edge; position not resolved by one seed set) and +2.90 pp at 2.0 s (vs +1.79). 4/5 improved, S02 −3 windows (sign as R-9a, below the noise line). Legacy leaky CV, CPU, `reports/legacy_leaky/augmentation_ab_eegnet.csv`.
- 2026-10-26 | P10 | PF-30 reproduced. S01/S02 EEGNet OFF test 28.00 / 27.04 % with un-augmented train 83.25 / 81.38 %: generalization failure, not optimization failure. The OFF-train < 40 % warning never fired. S01 ON 35.50 % is reported as its own number, not as R-9a's 27–28 %.
- 2026-10-26 | P10 | Real-data regression of the P09 refactor confirmed. S03 OFF equals P08/P09 CPU exactly for EEGNet 149/169, Compact-CNN 107/124 and ShallowConvNet 171/183 of 197.
- 2026-10-26 | P10 | Builder choices accepted (pre-run N1–N3). The mixup partner may be the anchor itself (effective mixup rate about 0.484). Single-subject ON CSVs are named `*_aug_benchmark_<device>.csv`. The P08/P09 `--augment on` rejection tests became invalid-value tests.
- 2026-10-26 | P10 | Compact-CNN (+14.12 / +11.39 pp; S04 +85 windows from 53.30 %; S02 −21 windows) and ShallowConvNet (+2.01 / +2.72 pp; all subjects ≤ 10 windows) are legacy-leaky diagnostics, not effects. The Compact S04 Δ equal to R-9b S04 Δ (85/197) is a coincidence, not a reproduction.
- 2026-10-26 | P10 | Era A closes for R1/R8. All A/B and network numbers P04–P10 stay labelled legacy leaky and frozen. P11 measures the leak-free A/B against R-9b. Carry to P11: assert `len(train dataset) == len(tr)` and a seeded loader generator for both arms (pre-run N4).

### Notes for the report (scribe)

- Do not write "reproduces" for the R-9a position within the band, for the Compact S04 Δ, or for any R-9b comparison. Use "in the recorded range (lower edge)" and "coincides".
- Give per-subject deltas in windows next to pp, and state the 9-window noise line and the one-seed-set caveat beside the cohort numbers.
- 2.0 s values carry the i%5 label. No R-6 comparison anywhere.

Verdict: APPROVE

## Sources spot-check

- `mas/04_REFERENCE_RESULTS.md` lines 12 (NN tolerance ±5 / ±3 pp, sign flip clause) and 126–176 (R-9a text; R-9b EEGNet, Compact-CNN and ShallowConvNet tables, including S04 Compact 54.82 / 97.97 / 43.15 and S02 Compact −7.14): opened; values quoted above match.
- `mas/05_PITFALLS.md` PF-30 (line 157): "low train acc = optimization problem; high train acc + chance test = generalization problem (S01/S02)". Opened; the reading above applies it as written.
- `reports/augmentation_ab_*.csv` (3 files): opened; all numbers above are copied from them or derived with the shown commands. `06_verify.md` k/n tables agree with my window deltas.

## Questions
