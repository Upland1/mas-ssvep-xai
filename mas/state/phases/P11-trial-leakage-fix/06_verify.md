# P11 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (P1-P7, binding), the phase branch
Clean checkout: pytest in a detached worktree `mas/state/scratch/verify_P11` @ `aedf8a81c581eebc4273181e71fd795df3e5a8bd` (removed after the run). Benchmarks ran at the same HEAD from the repository root with an empty porcelain status.

Verdict: FAIL

## Reasons (numbered)

1. **P4 (augmentation A/B = R-9b) is not met.** Cells outside the pre-committed windows (per subject +-5 pp, cohort mean +-3 pp), all from `reports/augmentation_ab_<model>.csv`:
   - EEGNet: S03 1.0 OFF 54.82 vs 73.60 (-18.78), 1.0 ON 64.47 vs 79.19 (-14.72), 2.0 OFF 59.90 vs 82.23 (-22.33), 2.0 ON 71.07 vs 85.28 (-14.21); S05 2.0 OFF 85.00 vs 92.50 (-7.50). Mean 1.0 OFF 58.36 (window 61.22-67.22), 1.0 ON 63.21 (63.24-69.24, short by 0.03), 2.0 OFF 61.28 (64.56-70.56). Mean Delta 2.0 +4.65 (window -1.78-4.22).
   - Compact-CNN: S03 1.0 ON 57.87 vs 62.94 (-5.07), 2.0 ON 65.48 vs 71.07 (-5.59); S05 1.0 ON 54.50 vs 62.00 (-7.50). Mean 1.0 ON 50.65 (50.96-56.96, short by 0.31). Mean Delta 1.0 +13.56 (window 14.16-20.16).
   - ShallowConvNet: all cells inside (largest per-subject gap S02 2.0 OFF -4.59; cohort gaps -0.4 to -1.02).
   - R-7 cross-check (ON 1.0 s, +-5 per subject): EEGNet S03 -14.72; Compact-CNN S03 -5.07 and S05 -7.50; the other cells inside.
   - Sign rule: every Mean Delta (1.0 and 2.0, three models) is > 0 (4.85/4.65, 13.56/15.07, 2.63/2.83), so no sign flip.
   The reviewer's rule is binding: P4 misses are listed, the results are not re-run with other flags, and the verifier does not interpret them. They are reported for the results review.
2. **P5 CNN qualitative claim is not fully reproduced** (diagnostic, not the gate): see P5 below (overall partial).
3. Everything else (P1, P2, P3, P6, P7, window counts, hashes, tests, run completeness) passes.

## Tests on the clean checkout

```bash
.venv/bin/python -m pytest tests -o addopts="" -q
```
`678 passed, 21 warnings in 393.19s (0:06:33)`, exit 0. Log: `reports/logs/P11/pytest_20261026_110219.log` (the same count as 04_tests.md and 07_review.md Round 2).

## Acceptance

| Criterion | Obtained | Reference | Tolerance | Met? | Log / CSV |
|---|---|---|---|---|---|
| P1 flagship = R-6, default flags, grouped, i%5 reported | S01 61.00/67.50, S02 56.12/61.73, S03 86.80/90.36, S04 97.46/97.97, S05 95.00/95.50; mean 79.28/82.61; clean 200/196/197/197/200, rejected 0/3/3/1/0, 7 channels, none dropped | R-6 | +-1.5 per subject, +-1.0 mean, counts exact | Yes (difference 0.00 on every cell; k = 122/135, 110/121, 171/178, 192/193, 190/191, inside the review's windows) | `reports/n_subjects_benchmark.csv`; `reports/logs/P11/n_subjects_20261026_111119.log` |
| P1 meta labels | `cv=StratifiedGroupKFold(5, shuffle, 42) over reconstructed trial ids`; `2.0 s rule = legacy i%5 smoothing (R8 legacy-folder clause...); trial-reset reported as PF-02 diagnostic`; `trial_ids_approximate subjects: S02 S04` | review P1 | names present | Yes | `reports/n_subjects_benchmark.meta.txt` |
| P2 leaky columns = R-5 | demo 1.0 leaky 64.50/66.33/90.36/98.98/96.50, 2.0 leaky mod5 75.50/71.94/95.43/98.48/96.50, means 83.33/87.57; equal (pandas `==`) to `reports/legacy_leaky/n_subjects_benchmark.csv` and to R-5 | R-5 | exact | Yes | `reports/cv_leakage_demo.csv` |
| P2 grouped columns = n_subjects | demo 1.0 grouped and 2.0 grouped mod5 REPORTED equal (`==`) `reports/n_subjects_benchmark.csv` on all five subjects | review P2 | exact | Yes | same |
| P2 mean deltas | Delta 1.0 -4.06 (R-6 -4.05, diff -0.01); Delta 2.0 -4.96 (R-6 -4.96, diff 0.00) | R-6 | +-1.0 | Yes | same |
| P3 legacy reachable | `reports/legacy_leaky/n_subjects_benchmark.csv` = R-5 exactly (mean 83.33/87.57). Ablation: Full 90.36/95.43, pruning 87.31/94.92, ANOVA 86.29/94.42, MI 87.82/93.40, SFS 89.85/95.94. Feature space: FBCSP + FBCCA Shrinkage-LDA lsqr 90.36/95.43 | R-5, R-4 (SFS: P06 D-1), R-3 | exact | Yes | `reports/legacy_leaky/{n_subjects_benchmark,feature_selection_ablation_S03,feature_space_benchmark_S03}.csv` |
| P3 saga rows (report) | hybrid FBCSP + FBCCA: LogReg L1 87.31/94.42, ElasticNet 88.32/94.92, both below Shrinkage-LDA 90.36/95.43, so no seed-sensitivity note against R-3's ranking. The earlier P05 copy of the saga rows was overwritten by later runs before this run, so a row-by-row difference against it cannot be produced | review P3 | n/a | Reported | `reports/legacy_leaky/feature_space_benchmark_S03.csv` |
| P4 augmentation A/B = R-9b | see reason 1 and the tables below | R-9b | +-5 per subject, +-3 cohort | **No** | `reports/augmentation_ab_*.csv` |
| P4 meta names grouped splitter | all three metas: `cv=StratifiedGroupKFold(5, shuffle, 42) over reconstructed trial ids`, approximate subjects S02, S04 | review P4 | yes | Yes | `reports/augmentation_ab_*.meta.txt` |
| P6 task 2 | block lengths printed per subject and condition; only S02 (condition 103: 39 windows) and S04 (condition 101: 38 windows) are approximate; every other block is 40 | review P6 | S02, S04 only | Yes | `reports/logs/P11/n_subjects_20261026_111119.log`; metas |
| P7 provenance | see below | review P7 | | Yes | |
| Legacy reachable | step-0 CSVs under `reports/legacy_leaky/` equal R-5/R-4/R-3 (P3) | era matrix | | Yes | |

### P1 detail: 2.0 s reported (i%5) beside the trial-reset diagnostic (`reports/cv_leakage_demo.csv`)

| Subject | 1.0 s grouped | R-6 1.0 s | 2.0 s grouped i%5 (reported) | R-6 2.0 s | 2.0 s grouped trial-reset (diagnostic) | diagnostic minus reported |
|---|---|---|---|---|---|---|
| S01 | 61.00 | 61.00 | 67.50 | 67.50 | 67.50 | 0.00 |
| S02 | 56.12 | 56.12 | 61.73 | 61.73 | 59.18 | -2.55 |
| S03 | 86.80 | 86.80 | 90.36 | 90.36 | 86.80 | -3.56 |
| S04 | 97.46 | 97.46 | 97.97 | 97.97 | 97.97 | 0.00 |
| S05 | 95.00 | 95.00 | 95.50 | 95.50 | 95.50 | 0.00 |
| Mean | 79.28 | 79.28 | 82.61 | 82.61 | 81.39 | -1.22 |

R-6's 2.0 s column is reproduced with the legacy-folder i%5 rule (decisions.md C1 reporting rule). The trial-reset diagnostic (mean 81.39) lies outside the R-6 2.0 s mean tolerance on its own; per the review it is reported beside, never substituted, and is not a FAIL. S02 and S04 have approximate ids (PF-03; review N4: a small residual leak can remain on those two subjects until true ids in P16).

### P4 detail (values from `reports/augmentation_ab_<model>.csv`; reference R-9b; arithmetic in `mas/state/scratch/check_p4.py`, run with `.venv/bin/python`)

Mean rows (obtained / R-9b):

| Model | 1.0 OFF | 1.0 ON | 2.0 OFF | 2.0 ON | Delta 1.0 | Delta 2.0 |
|---|---|---|---|---|---|---|
| EEGNet | 58.36 / 64.22 | 63.21 / 66.24 | 61.28 / 67.56 | 65.94 / 68.77 | 4.85 / 2.01 | 4.65 / 1.22 |
| Compact-CNN | 37.09 / 36.80 | 50.65 / 53.96 | 41.21 / 41.23 | 56.28 / 57.69 | 13.56 / 17.16 | 15.07 / 16.46 |
| ShallowConvNet | 72.67 / 73.18 | 75.30 / 75.70 | 75.50 / 76.52 | 78.33 / 78.92 | 2.63 / 2.53 | 2.83 / 2.40 |

Per-subject Delta 1.0 (obtained vs R-9b; listed, not gated): EEGNet S01 +2.00 vs 0.00, S02 +3.06 vs -1.02, S03 +9.65 vs +5.59, S04 +1.52 vs +0.51, S05 +8.00 vs +5.00. Compact-CNN S01 +1.00 vs +7.00, S02 -8.67 vs -7.14, S03 +17.77 vs +20.30, S04 +46.70 vs +43.15, S05 +11.00 vs +22.50. ShallowConvNet S01 +1.50 vs +3.00, S02 +5.10 vs +3.06, S03 +3.04 vs +3.55, S04 +1.01 vs +1.02, S05 +2.50 vs +2.00. Train accuracy OFF/ON (CSV mean row): EEGNet 91.76/88.57, Compact-CNN 100/100, ShallowConvNet 100/100.

### P2/P5 before/after (network table from demo 2: `reports/cv_leakage_demo_networks.csv`, `reports/logs/P11/demo2_20261026_114931.log`; "leaky" = frozen P10 files)

Classical: mean Delta 1.0 -4.06 (window [-5.5, -3.0]) and Delta 2.0 -4.96 (window [-6.0, -3.5]): met.

| Model | Mean drop 1.0 OFF | Mean drop 1.0 ON | Largest per-subject drop (OFF, ON) | Mean aug. gain 1.0 leaky -> grouped |
|---|---|---|---|---|
| EEGNet | -5.57 | -3.83 | -20.81 (S03), -16.24 (S03) | +3.11 -> +4.85 |
| Compact-CNN | -5.56 | -6.12 | -14.21 (S03), -14.00 (S05) | +14.12 -> +13.56 |
| ShallowConvNet | -3.04 | -2.42 | -6.63 (S02), -7.50 (S01) | +2.01 -> +2.63 |

P5 grading (review's wording; classical mean drop 4.06 at 1.0 s):
- CNNs "drop much more (Compact-CNN up to ~20 pp)": Compact-CNN is **partial** (both arms' mean drop, 5.56 and 6.12, exceeds 4.06; its largest per-subject drop is 14.21, below the 15 pp bar). EEGNet: OFF 5.57 exceeds 4.06, ON 3.83 does not (partial; it has a 20.81 pp drop on S03). ShallowConvNet: 3.04 and 2.42 do not exceed 4.06 (not reproduced). Overall **partial**. The review pre-stated about 12 pp as the expected Compact-CNN maximum; 14.21 was observed.
- EEGNet gain: P11 mean Delta 1.0 +4.85 (> 0, inside the 1.0 s window -0.99-5.01; the Delta 2.0 window is exceeded, reason 1). Descriptively: R-9b +2.01, the original's last leaky run +7.34, our P10 +3.11; not presented as the roadmap's shrinkage.
- Compact-CNN "keeps +17.16": obtained +13.56 (window 14.16-20.16, short by 0.60), not reproduced by the gate. ShallowConvNet "keeps +2.53": obtained +2.63, reproduced.
- Coincidence flag: the EEGNet grouped gain +4.85 is a different quantity from any R-x value; no R-x number is claimed reproduced through it.

### P7 provenance and hashes

- Run commit `aedf8a81c581eebc4273181e71fd795df3e5a8bd`; `git diff --stat e86ae3f HEAD -- src scripts tests configs` lists only the demo (fix 1), `evaluate_confusion_matrix.py` (N2 wording), `legacy_eval.py` (docstring) and two test files (05_run.md).
- Legacy arrays: `sha256sum` of `data/processed/S0*/*.npy` and `data/processed/*.npy` before and after the run are identical (`mas/state/scratch/pre_hashes.txt`, `post_hashes.txt`; S01 45a9b033/241adcdc/1846c4e5 as in P07 D0; root `y_labels.npy` 112c8507...).
- Frozen P10 CSVs `reports/legacy_leaky/augmentation_ab_*.csv` after the run: compact_cnn `ad98d5d6...`, eegnet `0efbaaba...`, shallow_conv_net `7a2407fb...`, equal to the prefixes in 07_review.md Round 1 and to the pre-run hashes.
- Reference access: the verifier consulted no reference code. The recordings folder was not opened; `reports/` was written only by project scripts.

## Notes for the results review

- P4 misses are on EEGNet (S03, S05, cohort OFF means, Delta 2.0) and Compact-CNN (S03, S05 ON, Delta 1.0). The classical results P1-P3 are exact. No command was re-run.

Verdict: FAIL
