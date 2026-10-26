# P10 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (pre-committed checks), the phase branch
Clean checkout: `mas/state/scratch/verify_P10` @ `5f2d5eb856ba480455a1babd96c1d1edc27e0a0d` (removed after the run)

Verdict: PASS

## Questions

ACK 05_run.md verifier 2026-10-26

## First fact: S03 OFF regression rows (checked before reading the A/B)

All three match the P08/P09 CPU values exactly (same code path, device, seeds). Sources: A/B logs `reports/logs/P10/benchmark_nn_augmentation_<model>_*.log` and the P08/P09 CSVs `reports/{eegnet,compact_cnn,shallow_convnet}_benchmark_cpu.csv`.

| Model | Required | A/B OFF, S03 (log) | k / n | P08/P09 CSV row | Match |
|---|---|---|---|---|---|
| EEGNet | 75.63 / 85.79 (149 / 169 of 197) | 75.63 / 85.79, train 98.34 | 149 / 169 of 197 | `S03,cpu,197,3,75.63,85.79,98.34,2349` | yes |
| Compact-CNN | 54.31 / 62.94 (107 / 124) | 54.31 / 62.94, train 100.00 | 107 / 124 of 197 | `S03,cpu,197,3,54.31,62.94,100.0,56021` | yes |
| ShallowConvNet | 86.80 / 92.89 (171 / 183) | 86.80 / 92.89, train 100.00 | 171 / 183 of 197 | `S03,cpu,197,3,86.8,92.89,100.0,14485` | yes |

S03 Clean Windows = 197 in all three. The P09 refactor did not change the OFF path on real data.

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest -o addopts="" -q
```

`604 passed, 21 warnings in 219.16s (0:03:39)`, exit 0, log `reports/logs/P10/pytest_20261026_011732.log` (equals the count in `04_tests.md`).

## Acceptance

All values are legacy leaky CV (R1/PF-01), i%5 smoothing (R8/PF-02), CPU, legacy 7-channel arrays, one seed set; no comparison with R-6.

| Criterion | Obtained | Reference | Tolerance / band (pre-committed in `07_review.md`) | Met? | Log |
|---|---|---|---|---|---|
| EEGNet cohort Delta 1.0 s | +3.11 pp (63.93 -> 67.04) | R-9a +3.00 (first run) .. +7.34 (last leaky run) | in range [+3.00, +7.34] | yes, in the recorded range (at the lower edge, +0.11 pp above it) | eegnet log, Mean row |
| EEGNet cohort Delta 2.0 s | +2.90 pp (68.18 -> 71.08) | R-9a +1.79 | [-1.21, +4.79] | yes, within tolerance (+1.11 pp above the reference) | same |
| Subjects improved (1.0 s Delta > 0) | 4 of 5 (S01 +7.50, S03 +5.08, S04 +1.01, S05 +3.50) | R-9a 4/5 | count | yes | same |
| S02 sign | -1.53 pp (1.0 s), -1.53 pp (2.0 s): regressed (-3 windows) | R-9a: S02 regressed | per-subject +-5 pp | yes (same sign; 3 windows is "no detectable effect" under the noise rule) | same |
| S01/S02 near chance with high train accuracy (PF-30) | S01 OFF test 28.00 / train 83.25; S02 OFF test 27.04 / train 81.38 | R-9a about 27-28 % | OFF test <= 40 % and OFF train >= 70 % | yes: generalization failure, not optimization failure; the OFF-train < 40 % warning never fired | same |
| Frozen CSVs identical | `cmp` of `reports/augmentation_ab_<m>.csv` and `.meta.txt` against `reports/legacy_leaky/` for the three models: identical (6 of 6) | - | byte-identical | yes | - |
| Outputs exist | `src/preprocessing/dataset/augmentation.py`, `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py`, `reports/legacy_leaky/augmentation_ab_{eegnet,compact_cnn,shallow_conv_net}.csv` | assignment | - | yes | - |

PF-30 detail, ON arms (same reading): S01 ON test 35.50 / train 73.88; S02 ON test 25.51 / train 70.42. Both arms stay below 40 % test with train >= 70 % for S01 and S02.

Noise reading (pre-committed rule 8): the cohort 1.0 s delta (+3.11 pp) is above the 2 pp inconclusive line, but the P08 CPU-CUDA scale for a 5-subject mean is about 2.04 pp and the lower band edge is 0.11 pp away, so the position inside the band is not resolved by one seed set. Per-subject deltas of 9 windows or fewer (S02 -3, S04 +2, S05 +7 at 1.0 s) are "no detectable effect"; only S01 (+15) and S03 (+10) exceed the 9-window line. No significance claim.

## Per-model, per-subject tables

k/n is round(pct x n / 100); a Python check confirmed every k/n reproduces the CSV value to 2 dp. Delta = ON - OFF in pp; dw = Delta in windows. Train = mean over folds, eval mode, un-augmented training fold. Sources: `reports/augmentation_ab_<model>.csv`, logs in `reports/logs/P10/`.

### EEGNet (acceptance table)

| Subject | n | 1.0 s OFF (k/n) | 1.0 s ON (k/n) | Delta | dw | 2.0 s OFF (k/n) | 2.0 s ON (k/n) | Delta | dw | Train OFF | Train ON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | 200 | 28.00 (56/200) | 35.50 (71/200) | +7.50 | +15 | 31.50 (63/200) | 42.00 (84/200) | +10.50 | +21 | 83.25 | 73.88 |
| S02 | 196 | 27.04 (53/196) | 25.51 (50/196) | -1.53 | -3 | 31.12 (61/196) | 29.59 (58/196) | -1.53 | -3 | 81.38 | 70.42 |
| S03 | 197 | 75.63 (149/197) | 80.71 (159/197) | +5.08 | +10 | 85.79 (169/197) | 88.32 (174/197) | +2.53 | +5 | 98.34 | 96.82 |
| S04 | 197 | 98.48 (194/197) | 99.49 (196/197) | +1.01 | +2 | 98.48 (194/197) | 98.48 (194/197) | 0.00 | 0 | 100.00 | 100.00 |
| S05 | 200 | 90.50 (181/200) | 94.00 (188/200) | +3.50 | +7 | 94.00 (188/200) | 97.00 (194/200) | +3.00 | +6 | 98.87 | 99.00 |
| Mean | 198 | 63.93 | 67.04 | +3.11 | | 68.18 | 71.08 | +2.90 | | 92.37 | 88.02 |

### Compact-CNN (diagnostic; no tolerance verdict)

| Subject | n | 1.0 s OFF (k/n) | 1.0 s ON (k/n) | Delta | dw | 2.0 s OFF (k/n) | 2.0 s ON (k/n) | Delta | dw | Train OFF | Train ON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | 200 | 24.00 (48/200) | 31.50 (63/200) | +7.50 | +15 | 30.50 (61/200) | 34.00 (68/200) | +3.50 | +7 | 100.0 | 100.0 |
| S02 | 196 | 32.65 (64/196) | 21.94 (43/196) | -10.71 | -21 | 35.20 (69/196) | 20.92 (41/196) | -14.28 | -28 | 100.0 | 100.0 |
| S03 | 197 | 54.31 (107/197) | 65.48 (129/197) | +11.17 | +22 | 62.94 (124/197) | 73.10 (144/197) | +10.16 | +20 | 100.0 | 100.0 |
| S04 | 197 | 53.30 (105/197) | 96.45 (190/197) | +43.15 | +85 | 57.87 (114/197) | 97.46 (192/197) | +39.59 | +78 | 100.0 | 100.0 |
| S05 | 200 | 49.00 (98/200) | 68.50 (137/200) | +19.50 | +39 | 59.50 (119/200) | 77.50 (155/200) | +18.00 | +36 | 100.0 | 100.0 |
| Mean | 198 | 42.65 | 56.77 | +14.12 | | 49.20 | 60.60 | +11.39 | | 100.0 | 100.0 |

### ShallowConvNet (diagnostic; no tolerance verdict)

| Subject | n | 1.0 s OFF (k/n) | 1.0 s ON (k/n) | Delta | dw | 2.0 s OFF (k/n) | 2.0 s ON (k/n) | Delta | dw | Train OFF | Train ON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | 200 | 58.00 (116/200) | 63.00 (126/200) | +5.00 | +10 | 67.00 (134/200) | 73.00 (146/200) | +6.00 | +12 | 100.0 | 100.0 |
| S02 | 196 | 37.24 (73/196) | 37.24 (73/196) | 0.00 | 0 | 38.27 (75/196) | 40.82 (80/196) | +2.55 | +5 | 100.0 | 100.0 |
| S03 | 197 | 86.80 (171/197) | 90.86 (179/197) | +4.06 | +8 | 92.89 (183/197) | 96.45 (190/197) | +3.56 | +7 | 100.0 | 100.0 |
| S04 | 197 | 99.49 (196/197) | 99.49 (196/197) | 0.00 | 0 | 98.98 (195/197) | 98.98 (195/197) | 0.00 | 0 | 100.0 | 100.0 |
| S05 | 200 | 97.00 (194/200) | 98.00 (196/200) | +1.00 | +2 | 97.50 (195/200) | 99.00 (198/200) | +1.50 | +3 | 100.0 | 100.0 |
| Mean | 198 | 75.71 | 77.72 | +2.01 | | 78.93 | 81.65 | +2.72 | | 100.0 | 100.0 |

Diagnostic facts only: Compact-CNN cohort Delta +14.12 / +11.39 pp, with S02 negative (-21 / -28 windows) and S04 +85 / +78 windows from a 53.30 / 57.87 % OFF level; train 100.0 % in both arms; legacy leaky CV, so read as legacy-leaky and not as a leak-free gain (R-9b leak-free +17.16 / +16.46 is context, not a target). ShallowConvNet cohort Delta +2.01 / +2.72 pp, all per-subject 1.0 s deltas at or below 10 windows. Coincidence flag (check 6): Compact-CNN S03 2.0 s OFF 62.94 equals the P09 value, which is the regression row itself; S03 1.0 s ON is 65.48 and does not coincide.

## Numbers in the handoffs vs logs

Every number in `05_run.md` is copied from the logs (console blocks verbatim). The per-subject numbers above come from the same logs and from `reports/augmentation_ab_<model>.csv`; console tables and CSVs agree. Frozen copies: 6 of 6 files byte-identical (`cmp`). Meta files carry the data-source line, `n_channels` (7 for every subject), the model line and the legacy labels. No command was skipped; none exceeded the budget.

## Privacy, git, R11

- Branch `phase/P10-augmentation-ab`, HEAD `5f2d5eb`; `git status --porcelain` empty before the benchmark runs; the worktree was removed (`git worktree list` shows only the main checkout).
- The raw recordings were not accessed and no preprocessing ran; only the project script read `data/processed/`. No code, config, CSV or log was edited.
- Case-insensitive `git grep` for the vendor and assistant names over all of HEAD: 0 hits.
- R11: `03_changes_deep-learning.md` and `04_tests.md` list no reference consultation; `mas/state/scratch/reference_access.log` has no P10 entry (last entries 2026-10-25 and the 2026-10-26T00:25 privacy scan during the P09 review). No consultation was needed because R-9a is met.

## Sources spot-check

Opened in this run: `mas/04_REFERENCE_RESULTS.md` R-9a/R-9b (values and tolerance quoted above match the file), `07_review.md` pre-committed checks and run commands, and the P08/P09 CSVs. All match what is claimed.

## Numbered reasons for the verdict

1. Regression rows: S03 OFF equals P08/P09 for all three models (149/169, 107/124, 171/183 of 197).
2. All three commands ran once at HEAD with a clean tree, exit 0, no warnings; 604 tests passed in the clean worktree.
3. EEGNet cohort Delta 1.0 s +3.11 pp is inside the R-9a recorded range [+3.00, +7.34]; 2.0 s +2.90 pp is within [-1.21, +4.79].
4. 4 of 5 subjects improved at 1.0 s; S02 regressed, as in R-9a.
5. S01/S02 OFF test 28.00 / 27.04 % (<= 40 %) with OFF train 83.25 / 81.38 % (>= 70 %): PF-30 generalization failure reproduced.
6. Frozen CSVs and meta files in `reports/legacy_leaky/` are byte-identical to the main outputs.
7. Caveat for the review: the 1.0 s cohort delta sits 0.11 pp above the lower band edge, within single-seed CPU uncertainty; S02, S04 and S05 deltas are 9 windows or fewer.
