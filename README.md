# mas-ssvep-eeg-xai

A from-zero rebuild of an SSVEP brain–computer-interface research pipeline: five-class
decoding of steady-state visually evoked potentials from eight parieto-occipital EEG channels
recorded at 256 Hz. The rebuild replays the original project's history in 26 gated phases
(P00–P25), bugs included, up to its latest approach (a graph neural network under
leave-one-subject-out). Every number below comes from a CSV or log under `reports/`, with its path.
Correctness of the evaluation outranks speed or headline accuracy.

Written results: the academic report `docs/report/v2/report.md`, the one-page methodology infographic
`docs/infographic/methodology_infographic.svg`, the progress report for the professor
`docs/progress_report/progress_report.md`, and the chronological research history `RESEARCH_LOG.md`.
The earlier history stays in `docs/report/v1/` (historical, P06).

## 1. Overview

- **Task.** Decode which of five flicker targets (24.00, 20.00, 15.00, 10.9091 and 8.5714 Hz) a
  5-second stimulus segment shows. A sixth class (fixation, code 201) is added in P17.
- **Data.** Two calibration sessions per subject (`OO`, the main on-off session, and `mOO`, a second run used
  for the pseudo-online test). The delivered recordings are S01–S05 (10 of the 23 recordings of the
  measured inventory; see §12).
- **Protocol.** Legacy windows (P02–P15) are reproduced as they were, including the trial leak
  (window-level cross-validation). The corrected protocol (P16 onward) uses trial-grouped cross-validation,
  continuous filtering before windowing, the recorded 256 Hz, and one shared quality decision.
- **Status.** Phases P00–P23 have passed their gates. P24 (this documentation) and P25 (audit) close the project.

## 2. Task table: conditions and frequencies

| Code | Meaning | Frequency | Windows per trial (legacy) |
|---|---|---|---|
| 101 | Target 1 | 24.00 Hz | 5 |
| 102 | Target 2 | 20.00 Hz | 5 |
| 103 | Target 3 | 15.00 Hz | 5 |
| 104 | Target 4 | 10.9091 Hz (120/11) | 5 |
| 105 | Target 5 | 8.5714 Hz (60/7) | 5 |
| 201 | Fixation cross, "no stimulus" (sixth "rest" class from P17) | — | 2 |
| 202 | Cue (target presentation); not a class | — | 1 |

Source: `mas/01_DATA_SPEC.md` §3 and §6. One trial lasts 15 s; each run has 40 trials (8 per target,
randomized order). Chance is 20 % for five classes and 16.67 % for six. Connectivity baselines always use
201, never 202 (201 and 202 are near-duplicate windows, PF-13).

## 3. Results

Every table states its data source (R9). Reference values of the original project are labelled **R-x** and
are targets for diagnosis, never results of this repository (`mas/04_REFERENCE_RESULTS.md`). Legacy values
are leaky (window-level cross-validation) and are not comparable with the corrected ones.

### 3.1 Flagship classical pipeline, corrected (leak-free)

FBCSP (m = 1, five sub-bands, in-fold) and FBCCA features → StandardScaler → Shrinkage-LDA, five-fold
trial-grouped cross-validation, seed 42. Data source: legacy folders `data/processed/<S>/` (seven
channels, fs 250 in features, per-script gate), `reports/n_subjects_benchmark.csv`.

| Subject | Channels kept | Clean | Rejected | 1.0 s (%) | 2.0 s smoothed (%) | R-6 1.0 s / 2.0 s (original) |
|---|---|---|---|---|---|---|
| S01 | 7 | 200 | 0 | 61.00 | 67.50 | 61.00 / 67.50 |
| S02 | 7 | 196 | 3 | 56.12 | 61.73 | 56.12 / 61.73 |
| S03 | 7 | 197 | 3 | 86.80 | 90.36 | 86.80 / 90.36 |
| S04 | 7 | 197 | 1 | 97.46 | 97.97 | 97.46 / 97.97 |
| S05 | 7 | 200 | 0 | 95.00 | 95.50 | 95.00 / 95.50 |
| **Mean** | | | | **79.28** | **82.61** | 79.28 / 82.61 |

Reproduced exactly on every cell. The 2.0 s column uses the legacy `i % 5` smoothing (R8, PF-02): the
legacy-folder rule that R-6 defines. The trial-reset rule is reported beside it as a diagnostic (§9).

Corrected continuous pipeline (P16 onward; 8-channel montage with the tier-1 channel drop, fs 256 from the
header, continuous filtering, true trial ids). Data source: `data/processed_continuous/` (`reports/v1_vs_v2/flagship.csv`,
column c, five seeds 42–46; `reports/n_subjects_benchmark_v2cont.csv`).

| Subject | Clean | Rejected | 1.0 s (%) | 2.0 s smoothed (%) |
|---|---|---|---|---|
| S01 | 200 | 0 | 72.80 | 77.90 |
| S02 | 190 | 10 | 72.42 | 75.26 |
| S03 | 194 | 6 | 93.61 | 93.92 |
| S04 | 195 | 5 | 99.49 | 99.49 |
| S05 | 199 | 1 | 98.59 | 98.79 |
| **Mean** | | | **87.38** | **89.07** |

Five-class results with the six-class and harmonic bank (§3.4) are higher (harm bank: 94.29 / 95.80).
The flagship and the continuous build differ in fs, filtering, channels and the number of clean windows, so
the step from 79.28 to 87.38 is a decomposition, not one effect (§9).

### 3.2 Neural networks: augmentation A/B and parameter counts

Leak-free augmentation A/B on the grouped folds, seed 42 (P11). Data source: legacy folders, CPU, 7 channels,
`reports/augmentation_ab_<model>.csv`. Parameter counts at 7 channels × 256 samples, five classes:
`reports/network_parameter_counts.csv`.

| Network | Params | 1.0 s OFF / ON (%) | 1.0 s Δ (pp) | 2.0 s OFF / ON (%) | 2.0 s Δ (pp) | R-9b Δ 1.0 s (original) |
|---|---|---|---|---|---|---|
| EEGNet | 2,349 | 58.36 / 63.21 | +4.85 | 61.28 / 65.94 | +4.65 | +2.01 |
| Compact-CNN (`compact_cnn`, class `CompactCNN`) | 56,021 | 37.09 / 50.65 | +13.56 | 41.21 / 56.28 | +15.07 | +17.16 |
| ShallowConvNet (`shallow_convnet`) | 14,485 | 72.67 / 75.30 | +2.63 | 75.50 / 78.33 | +2.83 | +2.53 |

Cohort means over S01–S05 (per-subject values in the CSVs). Three-base EEGNet drop from the leaky run is
−2.71 pp (OFF). One network cell is not reproduced within tolerance (Compact-CNN S03 2.0 s ON: 65.48 %, against
the original's 71.07 % with a window of ±5 pp); Sebastian accepted it as a documented deviation (D-8, B006).
The EEGNet training-seed range on S03 (16.75 pp) is of the same order as its seed-42 leak effect.

Note the naming (PF-31): `compact_cnn` is the P09 `CompactCNN` (56,021 parameters). `compact_eegnet` is the
`EEGNetSSVEP(F1=96, D=1, F2=96, dropout 0.5)` network of the P20 sweep and the P21 LOSO; the two are not
the same model.

### 3.3 Connectivity gate (P15)

Does per-window edge information add to node power and FBCCA features? Shrinkage-LDA, 1.0 s accuracy, mean of five
repeats per subject; cohort mean of subject means. Data source: legacy folders (`reports/connectivity_gate_benchmark.csv`,
`k_select = 0`; cohort means computed for the documents).

| Feature set | S01 | S02 | S03 | S04 | S05 | Cohort |
|---|---|---|---|---|---|---|
| Base (N+F, 75 features) | 41.20 | 47.96 | 82.74 | 97.97 | 98.90 | 73.75 |
| Base + Ec (coherence edges) | 57.50 | 51.12 | 83.96 | 98.07 | 97.20 | **77.57** |
| Ec (coherence edges only) | 48.30 | 36.12 | 45.48 | 62.44 | 50.60 | 48.59 |

Reproduced: all 45 subject × set cells within 0.05 pp of R-14 and the cohort means within 0.06 pp. Verdict: the gate does not pass (0 of 3 responders gain at least
2 pp; S01 +16.30 and S02 +3.16 gain). Descriptive heuristic on five subjects.

### 3.4 Filter bank and six classes (P17)

Cohort means over S01–S05, ten CV repeats, `reports/n_subjects_benchmark_p17_*`.

| Bank | 5 classes 1.0 s / 2.0 s (%) | 6 classes 2.0 s: StimCorrect / FalseAct / Missed (%) |
|---|---|---|
| base (five FBCSP sub-bands) | 87.65 / 89.57 | 85.63 / 7.85 / 8.67 |
| harm (base + k·f harmonics, k = 1..3) | 94.29 / 95.80 | 88.39 / 2.10 / 10.15 |
| harm + mid (+ midpoints) | 94.23 / 95.45 | 88.52 / 2.05 / 9.93 |

The harmonic gain is worded "consistent with an SNR gain of the ±1 Hz bands at k·f, fundamentals included".
Six classes are not comparable with five-class accuracy.

### 3.5 Connectivity statistics (P13, P14, P18)

Cohort, 200 (P13) and 1000 (P18) trial-level permutations, S01–S05 (`reports/connectivity_cohort_summary.csv`,
`reports/connectivity_cohort_summary_p18_nbs.csv`). FDR totals are the number of edges significant after
Benjamini–Hochberg (BH) over edges, per subject.

| Method | S01 | S02 | S03 | S04 | S05 | R-12 totals (original) |
|---|---|---|---|---|---|---|
| Coherence | 0 | 0 | 64 | 49 | 12 | 0 / 0 / 65 / 51 / 15 |
| wPLI | 4 | 0 | 42 | 28 | 5 | 0 / 3 / 38 / 33 / 18 |

Cells (100 = 5 subjects × 4 methods × 5 frequencies) with A-FDR (at least one edge), A-NBS (Network-Based Statistic,
p < 0.05) and B (global p < 0.05) at 1000 permutations: 48, 43, 32. NBS and FDR are reported as separate criteria (R7).
Mean largest component as a share of possible edges: S03 38.8 %, S04 32.1 %, S05 12.1 %, S01 2.6 %, S02 1.6 %
(`reports/connectivity_graph_size_p18_nbs.csv`). The S05 wPLI total is an accepted deviation from R-12 (D-1, P13).

Frequency comparison (P14, `reports/connectivity_comparison/`): coherence similarity across frequencies, Fisher mean r
0.629 (R-13: 0.54); coherence largely explained by SNR (R² 0.675). No consistent in-alpha difference for coherence, PLV or wPLI (3 of 5 subjects).

### 3.6 Within-subject and leave-one-subject-out (P21–P23)

Cohort S01–S05, 1 s windows, stride 0.25 s, channels `common` (7). Data source: built continuous folders
`processed_continuous/w1_s0.25`, session OO (`reports/loso_w1_s01-s05/summary.csv`,
`reports/loso_w1_p22_common/summary.csv`, `reports/loso_gnn/summary.csv`, `reports/within_gnn/summary.csv`).

| Method | Protocol | Cohort mean (%) | Normalization |
|---|---|---|---|
| fbcca | LOSO | 82.40 | none (no training) |
| lda | LOSO | 87.61 | pooled CSP and scaler, in-fold |
| lda_subjnorm | LOSO | 90.03 | test-time, whole-session statistics (offline upper bound) |
| within_lda | within-subject (trial-grouped 5-fold) | 90.79 | in-fold |
| ccnn | LOSO, seed 42 (three-seed cohort means 85.36–86.58) | 86.17 | in-fold |
| eegnet (sweep network, kernel 128) | LOSO, seed 42 (three-seed cohort means 78.58–79.76) | 79.76 | in-fold |
| GNN nodes+F | LOSO, three seeds, pooled | 89.22 | in-fold (z-scored on training windows) |
| GNN nodes+F | LOSO, subject normalization | 90.32 | test-time (offline upper bound) |
| GNN nodes+F | within-subject, three seeds | 86.81 | in-fold |

The within-subject `within_lda` rows are within-subject results; the `Data source` text in the P22 CSV still reads
"LOSO" (labelling defect W-1, carried). For the GNN, "LOSO below within" is **direction not observed** (LOSO 89.22
against within 86.81). The GNN is at or above `lda` on S02 and S05, which is reported as "GNN ≥ lda on S02/S05",
never as "beats".

Cohort 39 (39 subjects, S01–S040 without S020; `reports/loso_w1_all/summary.csv`, `reports/loso_w1/summary.csv`):
`all` (8 channels) fbcca 75.80, lda 83.42, lda_subjnorm 86.13 (32 matched subjects, the comparable classical result).
`common` (POz, PO4, O1; three channels) fbcca 64.56, lda 72.54, lda_subjnorm 75.16; ccnn 71.58 (one repeat). The `common`
rows are three-channel results, not comparable with cohort 5 or with within-subject results.

### 3.7 Detection and window length (P20)

Cohort S01–S05, OO session (`reports/window_sweep/summary.csv`, `reports/nn_sweep/summary.csv`,
`reports/pseudo_online/summary_ccnn_{5class,6class}.csv`, `reports/dynamic_stopping/best_threshold.csv`).

| Window (s) | LDA Acc (%) / ITR (bits/min) | FBCCA Acc (%) / ITR | compact_eegnet Acc (%) / ITR |
|---|---|---|---|
| 0.5 | 81.80 / 84.37 | 69.16 / 57.50 | 80.75 / 87.25 |
| 1.0 | 89.89 / 70.03 | 81.72 / 56.56 | 92.08 / 74.53 |
| 2.0 | 95.63 / 48.82 | 92.11 / 44.60 | 95.51 / 48.43 |
| 4.0 | 98.03 / 28.93 | 96.86 / 28.15 | 83.10 / 21.56 |

Window-level ITR is highest at 0.5 s for every method; accuracy rises with length, except the `compact_eegnet` value at 4 s,
which is driven by S02 (early-stopping failures in single-repeat folds, §9). One-second networks: ccnn 91.25, compact_eegnet
92.08, eegnet 89.69 %, a single repeat; all differences below 3 pp, not distinguishable.

Pseudo-online (trained on OO, replayed on mOO as a causal stream): 89.00 % accuracy and 27.5 % false activations with five
classes; 74.00 % and 5.0 % with six classes (the rest class absorbs false activations; two runs, not a before/after pair).
Dynamic stopping: LDA reaches 61.53 bits/min at 0.5 s (`reports/dynamic_stopping/best_threshold.csv`) against 60.23 for the time-matched single window (`mas/state/reports/P20.md`; thresholds chosen in-sample, descriptive).

### 3.8 Era-C checks (P16, P19)

| Check | Result | Source |
|---|---|---|
| Edge effects of per-window filtering (S03, 7–12 / 13–17 / 18–26 Hz) | edge-to-centre ratios 8.17 / 7.45 / 21.00 | `reports/edge_effects_summary.csv` |
| Raw-signal quality (P19, rejected of 1600 windows: filtered / both / raw) | 43 / 44 / 44; flagship change not material | `reports/n_subjects_benchmark_p19_*` |
| Legacy starts of built windows (P16) | 70 of 70 equal | `reports/logs/P16/` |

## 4. Models

| Model | Where used | Reference |
|---|---|---|
| FBCCA (zero-training canonical correlation), FBCSP (common spatial patterns on sub-bands) | flagship, all phases | method names; primary papers not opened in this run |
| StandardScaler + Shrinkage-LDA (lsqr, automatic shrinkage) | flagship, LOSO `lda`, `lda_subjnorm` | scikit-learn documentation as cited in `mas/state/reports/P06.md`; not reopened in this run |
| Linear and RBF SVM, MLP, random forest, logistic regression | P04–P06 comparisons (`test_sklearn_models`) | scikit-learn defaults as set in `mas/state/decisions.md` (P04) |
| Dual-branch fusion CNN (10,005 parameters) | P04 legacy | reference model, R-8 |
| EEGNet (legacy, kernel 125, 2,349 parameters at 7 × 256) | P08, P10, P11 | module docstring names the EEGNet architecture; paper not opened in this run |
| `eegnet` (sweep and LOSO network, kernel 128, 2,389 parameters at 8 channels) | P20 sweep, P21 LOSO | reference network R-8 (sweep table); not the legacy EEGNet above |
| Compact-CNN (`compact_cnn`, 56,021) | P09, P10, P11 | module docstring names Waytowich et al. (2018); paper not opened in this run |
| ShallowConvNet (`shallow_convnet`, 14,485) | P09, P10, P11 | module docstring names Schirrmeister et al. (2017); paper not opened in this run |
| `compact_eegnet` (`EEGNetSSVEP(F1=96, D=1, F2=96, dropout 0.5)`) | P20 sweep, P21 LOSO | reference network R-8 (sweep table) |
| `ccnn` (CCNN, filter bank 3–50 Hz at 0.25 Hz steps) | P20, P21 | reference network R-8 |
| Edge-gated connectivity GNN (`nodes+F`, `nodes+coh+F`) | P15 within, P23 LOSO and within | reference class, R-8 and R-15; consultation under R11 (`mas/state/reports/P15.md`) |

The paradigm (the on-off and checkerboard flicker and their frequencies) is described in Chailloux Peguero et al. (2023),
cited as given in `mas/01_DATA_SPEC.md` §3 (see Sources).

## 5. Deep-learning training convention

- Per-window, per-channel z-scoring (each window's own mean and standard deviation over time).
- AdamW (weight decay 1e-2), cosine annealing (minimum learning rate 1e-5), label smoothing 0.05 (P08); 150 fixed epochs
  for the legacy networks (no validation split, no early stopping) and grouped early stopping for the P20–P23 networks
  (20 % of training trials as validation, patience 25, maximum 150 epochs, best validation-loss state).
- `torch.manual_seed(42 + fold)` before each fold's model; several training seeds where a difference is interpreted (at least
  three bases, P11 and P20 rules).
- Augmentation (P10) is applied to the training fold only, after z-scoring; its generator is seeded separately from the torch RNG.
- Train accuracy is measured on the un-augmented training fold (PF-30). Training accuracy far above test accuracy is a
  generalization problem, not an optimization one.
- Device: CPU for every reported A/B; the GPU runs (P08 CUDA row, P20 sweep, P21 networks, P23) are labelled by device.

## 6. Pipeline

```
data/raw/S<nn>/OO.ebr, mOO.ebr                          (recordings, git-ignored, never committed)
  │  src/io/ebr_parser.py, load_ebr_file (strict header checks, sample rate from the header)
  ▼
continuous signal, 8 channels (PO7 restored in P07), 256 Hz
  │  filter continuously, then cut (P16+: R3)   zero-phase broadband 1–90 Hz + notch 60 Hz (legacy P02: 1–60 Hz)
  ▼
windows: 1.0 s, stride 0.25 s, trial ids (true, P16+), codes 101–105 and 201
  │  one shared quality decision (P16+: R5): channel drop (tier 1, > 50 % fail) and window gate
  │  vpp 5–120 µV, std 1–35 µV; artifact guard = filter ringing time; P19 adds the raw-signal check
  ▼
features:  FBCSP (m = 1, in-fold; five sub-bands in the base bank, more in P17), FBCCA (three harmonics), harmonic PSD
  │  scaler (in-fold) → Shrinkage-LDA; or networks (§5); or graph features (§7)
  ▼
evaluation:  trial-grouped CV (R1), smoothing per trial (R8), LOSO over subjects (P21–P23), within-subject reference
  ▼
reports/*.csv  →  README, RESEARCH_LOG, report v2, progress report
```

## 7. Preprocessing and quality

- **Recording.** 256 Hz (from the header, `load_subject(...)["fs"]`, never a literal, P16+). Eight EEG channels of the
  montage `PO7, PO3, POz, PO4, PO8, O1, Oz, O2`; PO7 is excluded before P07 (seven channels, legacy).
- **Legacy (P02–P15).** Broadband 1–60 Hz zero-phase band-pass (order 4) on the continuous recording, then 1.0 s windows, then the
  per-script gate (R5 legacy, by design). Features assume fs 250 (PF-04), per-window sub-band filtering (R3 legacy, PF-14).
- **Corrected (P16+).** Continuous filtering of every band, then cutting (R3); fs from metadata; one quality decision shared by all
  features (R5) with explicit thresholds: vpp 5–120 µV, std 1–35 µV, channel fail fraction above 0.5 for tier 1;
  artifact guard `auto` (ringing time of the continuous filters, 0.902 s for the broadband bank, 1.047 s for the narrow
  harmonic bank in P17); P19 adds the raw-signal check (`quality.source = both`).
- **Two-tier gate (P07).** Tier 1 drops a channel for the whole subject when it fails the limits in more than 50 % of windows;
  tier 2 rejects individual windows on the surviving channels. Legacy 7-channel arrays are not regenerated (R-6 is defined on them).

## 8. Trial-grouped cross-validation, features, augmentation, connectivity

- **Trial-grouped CV (R1, P11+).** `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)` with `groups` = trial ids.
  Trial ids on legacy folders are reconstructed from the pre-gate labels (`201:2, 202:1, 101–105:5`) and then indexed with the
  gate's `valid_mask` (PF-03). In LOSO the group is the subject; nothing from the held-out subject reaches any fit (R1, B10).
  Approximate trial ids remain on S02 and S04 in legacy folders (39 of 199 and 38 of 198 stimulus windows, P16).
- **Features.** FBCSP: five bands (7, 12), (13, 17), (18, 26), (27, 36), (38, 52) Hz, one component per side (m = 1), 50 columns;
  FBCCA: five canonical scores on the channel set, three harmonics; harmonic PSD: 32 features on `PO8, O1, Oz, O2` (P05).
  Feature selection (ANOVA, mutual information, sequential forward selection, pruning) is in-fold (R2; P06).
- **Augmentation (P10).** Gaussian noise proportional to each channel's standard deviation, one amplitude factor per window, circular
  time shift and intra-class mixup, each applied with probability 0.5 on the training fold only; the mixup partner may be the
  anchor itself (effective rate about 0.484, accepted by the reviewer).
- **Connectivity workflow (P12–P18).** Per-window coherence is replaced by the concatenated estimator (R4: one estimate per
  condition, not an average of per-window coherence; PF-15). The baseline is the matched 201 windows in the stimulus band (PF-16).
  Phase connectivity (PLV, wPLI) comes from the cross-spectral density (R3); PDC from a strided MVAR fit (PF-17, R6). Statistics:
  trial-level permutations with observed group sizes (R7), BH over edges and the Network-Based Statistic, reported as separate
  criteria; cross-frequency comparison, split-half reliability and a pairwise exchange test (P14).
- **Graph models (P15, P23).** Nodes are electrodes with spectral power and FBCCA features; edges are per-window coherence (`nodes+coh+F`)
  or none (`nodes+F`). Within-subject and LOSO protocols with the same windows and channels.

## 9. Trial-grouping fix: before and after

The leak is in the legacy window-level cross-validation (PF-01): windows of one trial sit in both training and test folds. The fix (P11)
groups windows by trial. Before → after, cohort mean (`reports/n_subjects_benchmark.csv`, `reports/cv_leakage_demo.csv`):

| Protocol | 1.0 s (%) | 2.0 s smoothed (%) |
|---|---|---|
| Leaky, window-level (P06–P10, legacy) | 83.33 | 87.57 |
| Trial-grouped (P11, R-6 reproduced) | 79.28 | 82.61 |
| Change | −4.06 pp | −4.96 pp |

Per subject the change at 1.0 s is −3.50, −10.21, −3.56, −1.52 and −1.50 pp (S01–S05). The networks lose 5.6 pp on EEGNet and
Compact-CNN at seed 42 (`reports/cv_leakage_demo_networks.csv`), within the training-seed range; the CNN-specific inflation of the
original is not reproduced. Smoothing: the 2.0 s column uses `i % 5` on legacy folders; the trial-reset rule (diagnostic) is 3.56 pp
lower on S03 (86.80 against 90.36 at 2.0 s, `reports/cv_leakage_demo.csv`). Which rule is leak-free on legacy folders is an open
question until true trial ids arrive (P16). **Other before → after steps:** the sampling rate 250 → 256 Hz (+8.04 / +6.91 pp, fs
effect), the filter (per-window → continuous, no accuracy effect), the guard (negative on S02 only), the montage (PO7 restored), the
two-tier gate; the decomposition is in `reports/v1_vs_v2/flagship.csv` (`docs/report/v2/report.md`, §3.1).

## 10. Interpretation notes and open questions

- Legacy numbers (P02–P10) are leaky and are not generalization estimates. The P11 grouped rows and the P16 continuous rows are the
  closest estimates of generalization to unseen trials (the P11 rows still carry approximate trial ids on S02 and S04); the P21–P23
  LOSO rows estimate generalization across subjects.
- S01 and S02 are the hard subjects under every legacy and corrected classifier; S04 and S05 are close to ceiling. Cohort means
  hide this spread: per-subject values are always shown.
- Several differences are a few windows. One window is 0.51 pp at 197 windows, so small differences are not findings without an interval.
- **Open:** whether the original's sequential forward selection (R-4) was configured as in our SFS row (D-1, P06); whether PO7 and `vpp_min`
  changed together in the original's P07 (D-1, P07); the 2.0 s smoothing rule on legacy folders (P11); the cause of the Compact-CNN S03
  2.0 s and the GNN S02 2.0 s cells (accepted deviations, B006 and B007); the within-subject GNN reached the 150-epoch cap in 19 of 50 folds (P23 D-3);
  the fundamentals-only ablation of the filter bank (P17 C-d) and per-offset Missed and FalseAct (P17 C-e).
- The notebook sections for Colab (P21 `notebooks/loso_colab.ipynb`, 10b in P23) have not been run on a T4 GPU (human run).

## 11. Environment

- Python 3.12.3 in a project `.venv` with the full `requirements.txt` (`scikit-learn` 1.9.1 in the P05 runs). `make venv` creates it.
- Tests: `.venv/bin/python -m pytest tests/ -q -o addopts=""` runs on CPU without any recording (about 15 minutes for the full suite at P24).
- GPU: optional. The P08 EEGNet CUDA row, the P20 sweep networks and the P21 and P23 network runs use CUDA when available (`--device`);
  reported A/Bs use CPU.
- Workstation of the verifier: 16 cores; the GPU runs of P20 and P21 are recorded in their phase reports.

## 12. Dataset policy

- The recordings are private human-subject data. They are never committed; `data/raw/` and every generated folder (`data/processed*`,
  `reports/`, `outputs/`, `baselines/`) are git-ignored (`.gitignore`).
- Delivered: 10 of the 23 recordings of `mas/01_DATA_SPEC.md` §4 (OO and mOO of S01–S05). The other 13 (`C`, `mC`, `online_C`, `online_OO`,
  `cb_mas_mcb`) are absent and listed in `mas/state/blockers/B005-inventory-10-of-23-files.md`; no phase uses them.
- Cohort: S01–S05 for every main result. The P21 cohort of 39 subjects (S01–S040 without S020) is a separate data source (B003, R9);
  `make all` does not run it (`make loso-all` does).
- Raw files are read only by the project's scripts, launched through `python -m scripts...` or `make`.

## 13. Repository structure

| Path | Content |
|---|---|
| `src/io/` | recording parser (`ebr_parser.py`), channel helpers, `subject_data.py` (`load_subject`, the single loader from P16) |
| `src/preprocessing/` | filters, windowing (`windowing.py`), quality gates (`quality_check.py`, `window_quality.py`), datasets and augmentation, trial ids (`cv_utils.py`) |
| `src/features/` | FBCSP, FBCCA, PSD and harmonic features (`ssvep/`), feature selection (`selection/`), connectivity (`connectivity/`: coherence, phase, MVAR PDC, permutations, NBS, graph features) |
| `src/models/` | EEGNet, Compact-CNN, ShallowConvNet, shared network driver (`cnn/`), connectivity GNN (`graph/`) |
| `src/visualization/` | figure helpers |
| `scripts/` | command-line entry points (§14) |
| `configs/` | `pipeline_config.yaml` (final configuration, P16) |
| `tests/` | known-answer and regression tests, one file group per phase (`test_pNN_*.py`) |
| `notebooks/` | Colab notebook of the LOSO runs (P21) |
| `docs/` | `report/v1` (historical, P06), `report/v2` (academic report, P24), `infographic/`, `progress_report/` |
| `mas/` | specification, phase workflow and the agent team's state (`mas/state/`, `mas/README.md`) |
| `reports/`, `outputs/`, `baselines/`, `data/` | generated and git-ignored (`baselines/v1_2026-10-27/` is the frozen v1 snapshot) |

## 14. Usage: every script

Targets are the phase runs of the project. `make all` runs them in order (`p00` to `p23`) with explicit `--subjects S01 … S05`; `make -n all`
lists every command without running it. A direct call reads the recordings only when it is run without `--help`.

Argparse descriptions are empty in every script, so the purpose column is the first line of each module docstring; the options column is
taken from the parser. Wrappers `benchmark_eegnet`, `benchmark_compact_cnn` and `benchmark_shallow_convnet` take their options from the shared
driver `src/models/cnn/benchmark_common.py`.

| Script (module) | Purpose (module docstring) | Run through | Direct usage (reads no recordings) | Main options |
|---|---|---|---|---|
| `scripts.benchmarks.benchmark_loso` | Leave-one-subject-out (LOSO) generalization (P21.1): train on every subject but one, test on the held-out one. | p21, loso-all | `.venv/bin/python -m scripts.benchmarks.benchmark_loso --help` | --data-root --window --stride-sec --subjects |
| `scripts.benchmarks.benchmark_loso_warmup` | Warm-up study of the unsupervised per-subject normalization (P22.4, PF-35, PF-36, R2 exception). | p22 | `.venv/bin/python -m scripts.benchmarks.benchmark_loso_warmup --help` | --data-root --window --stride-sec --subjects |
| `scripts.benchmarks.benchmark_window_sweep` | Window-length sweep (P20.2): accuracy and ITR against window length for FBCCA, in-fold FBCSP+FBCCA LDA and a CNN. | p20, loso-all | `.venv/bin/python -m scripts.benchmarks.benchmark_window_sweep --help` | --data-root --windows --stride --methods |
| `scripts.benchmarks.feature_based.benchmark_5_subjects` | Legacy cohort benchmark of the P05 flagship (P06.3, legacy Era A; superseded by benchmark_n_subjects in P11). | p06 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_5_subjects --help` | --subjects --m --config --processed-dir |
| `scripts.benchmarks.feature_based.benchmark_cross_validation` | Feature-space x model benchmark on one subject (P05.5, legacy Era A). | p05, p11 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --help` | --subject --config --processed-dir --reports-dir |
| `scripts.benchmarks.feature_based.benchmark_feature_selection` | Feature-selection ablation on one subject (P06.2, legacy Era A). | p06, p11 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --help` | --subject --k-features --sfs-features --m |
| `scripts.benchmarks.feature_based.benchmark_harmonic_fbcca` | Occipital harmonic PSD + FBCCA -> Shrinkage-LDA on one subject (P05.5, legacy Era A). | p05 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_harmonic_fbcca --help` | --subject --config --processed-dir --reports-dir |
| `scripts.benchmarks.feature_based.benchmark_n_subjects` | Cohort benchmark of the flagship on legacy or built windows (P07.6 legacy Era A; ported to `load_subject` in P16.7; | p07, p11, p16, p17, p19 | `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --help` | --subjects --data-root --n-jobs --m |
| `scripts.benchmarks.neural_networks.benchmark_compact_cnn` | Compact-CNN (spatial -> temporal, Waytowich et al. 2018) on raw legacy windows (P09.3, legacy Era A, numbers are leaky). | p09 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_compact_cnn --help` | (shared driver, src/models/cnn/benchmark_common.py) |
| `scripts.benchmarks.neural_networks.benchmark_eegnet` | EEGNet on raw legacy windows (P08.2, legacy Era A, numbers are leaky). | p08 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_eegnet --help` | (shared driver, src/models/cnn/benchmark_common.py) |
| `scripts.benchmarks.neural_networks.benchmark_nn_augmentation` | Augmentation A/B (P10.3; P11 protocol): every subject, augmentation OFF then ON, per network. | p10, p11 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --help` | --model --epochs --subjects --device |
| `scripts.benchmarks.neural_networks.benchmark_nn_sweep` | NN sweep (P20.4): CCNN, compact_eegnet and eegnet on built continuous windows, trial-grouped CV, no smoothing. | p20 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_sweep --help` | --data-root --windows --stride --models |
| `scripts.benchmarks.neural_networks.benchmark_shallow_convnet` | ShallowConvNet (Schirrmeister et al. 2017) on raw legacy windows (P09.3, legacy Era A, numbers are leaky). | p09 | `.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_shallow_convnet --help` | (shared driver, src/models/cnn/benchmark_common.py) |
| `scripts.benchmarks.neural_networks.count_parameters` | Trainable parameter counts of the raw-window networks at 7 channels x 256 samples (P09.4, R-8). | p09 | `.venv/bin/python -m scripts.benchmarks.neural_networks.count_parameters --help` | --reports-dir |
| `scripts.benchmarks.pseudo_online` | Pseudo-online detector (P20.6, PF-38, PF-39, R2, R3, R5): train on one run, replay another as a causal stream. | p20 | `.venv/bin/python -m scripts.benchmarks.pseudo_online --help` | --train-session --test-session --model --window-sec |
| `scripts.benchmarks.simulate_dynamic_stopping` | Dynamic stopping on window-level probabilities (P20.5, R8, PF-38). | p20 | `.venv/bin/python -m scripts.benchmarks.simulate_dynamic_stopping --help` | --thresholds --skip-sec --gaze-sec --out-dir |
| `scripts.build_windows` | Build the P16 windows of every subject (P16.5, 01_DATA_SPEC 5.2, R3, R5, PF-04, PF-14). | p16, p17, p19, p20, p21, loso-all | `.venv/bin/python -m scripts.build_windows --help` | --filter-mode --subjects --session --guard-sec |
| `scripts.connectivity.analysis.analyze_connectivity` | Per-subject connectivity analysis (P12.4): coherence, stimulus vs matched baseline. | p12 | `.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity --help` | --subject --method --fs --quality |
| `scripts.connectivity.analysis.analyze_connectivity_cohort` | Cohort connectivity with permutation statistics (P13.5): coherence, PLV, wPLI, PDC. | p13, p18 | `.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --help` | --methods --subjects --permutations --stats |
| `scripts.connectivity.comparison.compare_connectivity_frequencies` | Descriptive cross-frequency comparison of connectivity DELTA matrices (P14.1, PF-24 to PF-26). | p14 | `.venv/bin/python -m scripts.connectivity.comparison.compare_connectivity_frequencies --help` | --methods --subjects --qap-permutations --responders |
| `scripts.connectivity.comparison.test_connectivity_frequency_differences` | Split-half reliability and pairwise frequency tests of connectivity deltas (P14.2, R4, R7, PF-19, PF-22). | p14, p18 | `.venv/bin/python -m scripts.connectivity.comparison.test_connectivity_frequency_differences --help` | --methods --subjects --permutations --splits |
| `scripts.connectivity.diagnostics.check_power_alpha_confound` | How much of the connectivity delta follows target SSVEP power and alpha change? (P14.3, PF-23, PF-27) | p14 | `.venv/bin/python -m scripts.connectivity.diagnostics.check_power_alpha_confound --help` | --subjects --methods --fs --quality |
| `scripts.connectivity.diagnostics.demo_coherence_bias` | DIAGNOSTIC (kept, P12.2): reproduce the two coherence bugs before the fix (PF-15, PF-16). | p12 | `.venv/bin/python -m scripts.connectivity.diagnostics.demo_coherence_bias --help` | --subjects --data-root --reports-dir --fs |
| `scripts.connectivity.diagnostics.demo_hilbert_edges` | DIAGNOSTIC (kept, P13.1): reproduce the filtfilt + Hilbert edge bug (PF-18) before the CSD fix (R3). | p13 | `.venv/bin/python -m scripts.connectivity.diagnostics.demo_hilbert_edges --help` | --reports-dir --fs |
| `scripts.connectivity.diagnostics.demo_mvar_slicing` | DIAGNOSTIC (kept, P13.2): reproduce the MVAR coefficient-slicing bug (PF-17, R6) before the fix. | p13 | `.venv/bin/python -m scripts.connectivity.diagnostics.demo_mvar_slicing --help` | --reports-dir |
| `scripts.connectivity.graph_modeling.benchmark_connectivity_gate` | Connectivity gate of P15: do per-window edge features add information over node power + FBCCA? (legacy Era B) | p15 | `.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_connectivity_gate --help` | --subjects --data-root --reports-dir --repeats |
| `scripts.connectivity.graph_modeling.benchmark_gnn` | Within-subject edge-gated GNN of P15 (legacy Era B): variants nodes+F and nodes+coh+F (R-15). | p15 | `.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_gnn --help` | --subjects --variants --repeats --epochs |
| `scripts.connectivity.graph_modeling.benchmark_gnn_loso` | Edge-gated connectivity GNN under leave-one-subject-out (P23.2), with a within-subject reference on the same windows. | p23 | `.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_gnn_loso --help` | --data-root --window --stride-sec --subjects |
| `scripts.connectivity.graph_modeling.build_graph_dataset` | Build the per-subject graph dataset cache of P15 (legacy Era B; R3 and PF-04 labelled). | p15 | `.venv/bin/python -m scripts.connectivity.graph_modeling.build_graph_dataset --help` | --subjects --data-root --reports-dir --fs |
| `scripts.diagnostics.compare_v1_v2` | v1 vs v2 tables of P16.8 (an addition of this rebuild; joins CSVs, computes differences only). | p16 | `.venv/bin/python -m scripts.diagnostics.compare_v1_v2 --help` | --baselines-dir --baseline-tag --reports-dir --out-dir |
| `scripts.diagnostics.demo_cv_leakage` | Size of the trial leak per subject (P11.4, R1/PF-01, R8/PF-02): the flagship under both splitters. | p11 | `.venv/bin/python -m scripts.diagnostics.demo_cv_leakage --help` | --subjects --data-root --config --reports-dir |
| `scripts.diagnostics.demo_edge_effects` | Edge effects of per-window sub-band filtering (P16.3, PF-14, R3). | p16 | `.venv/bin/python -m scripts.diagnostics.demo_edge_effects --help` | --subject --session --raw-dir --reports-dir |
| `scripts.diagnostics.network_seed_spread` | DIAGNOSTIC (P11 results review, required step 1): training-seed spread of a network on the fixed seed-42 grouped folds. | none (P11 diagnostic, by hand) | `.venv/bin/python -m scripts.diagnostics.network_seed_spread --help` | --model --seed-bases --epochs --subjects |
| `scripts.evaluation.evaluate_confusion_matrix` | Flagship hybrid: FBCSP (in-fold) + FBCCA -> StandardScaler -> Shrinkage-LDA (P05.5, legacy Era A). | p05 | `.venv/bin/python -m scripts.evaluation.evaluate_confusion_matrix --help` | --subject --m --config --processed-dir |
| `scripts.evaluation.test_sklearn_models` | The 10-model sklearn suite on PSD, FBCCA and FBCSP features of one subject (P05.5, legacy Era A). | p05 | `.venv/bin/python -m scripts.evaluation.test_sklearn_models --help` | --subject --config --processed-dir --reports-dir |
| `scripts.exploration.diagnose_occipital_spectra` | Occipital FFT power per class (P03.1): does each stimulus class peak at its target frequency? | p03 | `.venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --help` | --subject --subjects --all --config |
| `scripts.exploration.inventory_raw` | Inventory of the raw recordings (P00). | p00, p01 | `.venv/bin/python -m scripts.exploration.inventory_raw --help` | --raw-dir --out --subjects --strict |
| `scripts.exploration.visualize_data` | Per-class features of the legacy windows (P03.2): quality mask, stimulus windows, PSD by class. | p03, p05 | `.venv/bin/python -m scripts.exploration.visualize_data --help` | --subject --subjects --all --config |
| `scripts.freeze_baseline` | Freeze the Era A/B outputs as a read-only baseline snapshot (P16.1, plan settled points 1-2). | p16 | `.venv/bin/python -m scripts.freeze_baseline --help` | --tag --note --date --root |
| `scripts.preprocessing.run_preprocessing` | Legacy preprocessing and windowing (P02, mas/01_DATA_SPEC.md section 5.1; P07 tier-1 channel drop). | preprocess, p07 | `.venv/bin/python -m scripts.preprocessing.run_preprocessing --help` | --subject --subjects --all --config |
| `scripts.training.batch_run_subjects` | Per-subject LDA summary over several subjects (P04.4, legacy Era A). | p04 | `.venv/bin/python -m scripts.training.batch_run_subjects --help` | --subjects --paradigm --config --raw-dir |
| `scripts.training.train_final_model` | Export the full-data final models of one subject (P04.3, legacy Era A). | p04 | `.venv/bin/python -m scripts.training.train_final_model --help` | --subject --config --processed-dir --out-dir |
| `scripts.training.train_models` | First model benchmark on the harmonic-PSD + FBCCA hybrid (P04.1, legacy Era A). | p03, p04 | `.venv/bin/python -m scripts.training.train_models --help` | --subject --all --config --processed-dir |
| `scripts.xai.compare_subject_xai` | Side-by-side LDA weights of two subjects from their exported joblib files (P04.5, legacy Era A). | p04 | `.venv/bin/python -m scripts.xai.compare_subject_xai --help` | --subjects --out-dir |
| `scripts.xai.run_xai` | Shrinkage-LDA weight heatmaps of one subject (P04.5, legacy Era A). | p04 | `.venv/bin/python -m scripts.xai.run_xai --help` | --subject --config --processed-dir --out-dir |

### 14.1 Make targets and runtime

Measured minutes come from the "Commands executed" tables of each `mas/state/phases/Pxx/05_run.md`
(`mas/state/phases/P24-documentation/03_changes_data-signal.md`, runtime table). The verifier's run is on the 16-core workstation.

| Target | Main outputs | CPU min | GPU min | Total min |
|---|---|---|---|---|
| p00 | `reports/raw_inventory.csv` | 0.0 | | 0.0 |
| p01 | `reports/P01/raw_inventory_parser*.csv` | 0.0 | | 0.0 |
| p02 (= `preprocess`) | `data/processed/<S>/`, `outputs/figures/spectra/` | 0.1 | | 0.1 |
| p03 | `outputs/figures/exploration/` | 0.3 | | 0.3 |
| p04 | `outputs/` (per-subject models, XAI) | 9.1 | | 9.1 |
| p05 | `reports/flagship_S01.csv` to `reports/flagship_S05.csv`, `reports/feature_space_benchmark_S03.csv` | 1.2 | | 1.2 |
| p06 | `reports/feature_selection_*`, `reports/five_subjects_benchmark.csv` | 12.8 | | 12.8 |
| p07 | `reports/n_subjects_benchmark.csv` | 0.2 | | 0.2 |
| p08 | `reports/eegnet_benchmark_<device>.csv` | 0.6 | (0.4) | 0.6 |
| p09 | `reports/network_parameter_counts.csv`, `*_benchmark_cpu.csv` | 1.8 | | 1.8 |
| p10 | `reports/augmentation_ab_*.csv`, `reports/legacy_leaky/` | 24.9 | | 24.9 |
| p11 | leak-free A/B and classical rerun (overwrites p10 outputs) | 40.9 | | 40.9 |
| p12 | `reports/connectivity/` | 0.6 | | 0.6 |
| p13 | `reports/connectivity_cohort_summary*.csv`, `connectivity_edges*/` | 15.3 | | 15.3 |
| p14 | `reports/connectivity_comparison/` | 67.5 | | 67.5 |
| p15 | `data/processed/S0x/graph_dataset.npz`, `reports/gnn_benchmark*.csv` | 5.5 | | 5.5 |
| p16 | `data/processed_per_window`, `data/processed_continuous`, `reports/*_v1*`, `*_v2*` | 32.5 | | 32.5 |
| p17 | `data/processed_continuous_p17`, `reports/n_subjects_benchmark_p17_*.csv` | 5.5 | | 5.5 |
| p18 | `reports/connectivity_*_p18_nbs*`, `connectivity_comparison/` | 79.4 | | 79.4 |
| p19 | `data/processed_continuous_p19_*`, `reports/n_subjects_benchmark_p19_*.csv` | 2.5 | | 2.5 |
| p20 | `reports/window_sweep`, `nn_sweep`, `dynamic_stopping*`, `pseudo_online` | 2.9 | 78.1 | 81.0 |
| p21 | `reports/loso_w1_s01-s05*` | 0.6 | 32.0 | 32.6 |
| p22 | `reports/loso_w1_p22_*`, `reports/loso_warmup` | 1.1 | | 1.1 |
| p23 | `reports/within_gnn`, `reports/loso_gnn` | 20.5 | | 20.5 |
| **Total `make all`** | | **325.6 (5.43 h)** | **110.5 (1.84 h)** | **436.1 (7.27 h)** |
| `loso-all` (outside `all`) | `reports/window_sweep_w1_all`, `loso_w1_fbcca_all`, `loso_w1`, `loso_w1_all` | | | 33.6 min CPU (P21 record, classical) |

The total exceeds the 4 h limit of the project's run policy, so the orchestrator asks Sebastian before a full local run. `make all` writes a
`.done` stamp per phase under `mas/state/scratch/make_stamps/` and resumes at the first unstamped phase. The 39-subject networks (ccnn, eegnet,
compact_eegnet on the 39-subject cohort) are not in any target (about 1.5 h GPU, limited by Sebastian on 2026-10-28).

## 15. Development process

The rebuild is run by a team of agents through gated phases. Their roles, hand-off contract and gates are in `mas/README.md`; the
methodological rules R1–R11 are in `mas/RULES.md`; the phase roadmap is `mas/03_ROADMAP.md`. Live state (phase status, reports,
decisions, blockers) is under `mas/state/`. `python mas/tools/mas_status.py check` runs the preflight.

## Sources

1. DATA — `mas/01_DATA_SPEC.md` §3 (event protocol, paradigms; opened) and §6 (class conventions; opened); the inventory (§4) as quoted in `mas/state/blockers/B005-inventory-10-of-23-files.md`.
2. DATA — `mas/04_REFERENCE_RESULTS.md` R-1 to R-16 and tolerance table: reference values of the original project (labelled R-x).
3. RULE — `mas/RULES.md` R1–R11 and the era matrix (loaded in the project instructions; opened).
4. DATA — `reports/n_subjects_benchmark.csv`, `reports/cv_leakage_demo.csv`, `reports/five_subjects_benchmark.csv`: flagship and leak values (P06–P11).
5. DATA — `reports/augmentation_ab_eegnet.csv`, `reports/augmentation_ab_compact_cnn.csv`, `reports/augmentation_ab_shallow_conv_net.csv`, `reports/network_parameter_counts.csv`: augmentation A/B and counts (P11).
6. DATA — `reports/connectivity_gate_benchmark.csv`, `reports/gnn_benchmark.csv`: gate and within GNN (P15); cohort means computed for these documents.
7. DATA — `reports/v1_vs_v2/flagship.csv`, `reports/n_subjects_benchmark_v2cont.csv`, `reports/edge_effects_summary.csv`: continuous build and decomposition (P16).
8. DATA — `reports/n_subjects_benchmark_p17_*.csv`, `reports/n_subjects_benchmark_p19_*.csv`: filter bank, six classes, raw-signal check (P17, P19).
9. DATA — `reports/connectivity_cohort_summary.csv`, `reports/connectivity_cohort_summary_p18_nbs.csv`, `reports/connectivity_graph_size_p18_nbs.csv`: connectivity statistics (P13, P18).
10. DATA — `reports/window_sweep/summary.csv`, `reports/nn_sweep/summary.csv`, `reports/pseudo_online/summary_ccnn_*.csv`, `reports/dynamic_stopping/best_threshold.csv`: detection (P20).
11. DATA — `reports/loso_w1_s01-s05/summary.csv`, `reports/loso_w1_all/summary.csv`, `reports/loso_w1/summary.csv`, `reports/loso_w1_p22_*/summary.csv`, `reports/loso_warmup/cohort.csv`, `reports/loso_gnn/summary.csv`, `reports/within_gnn/summary.csv`: LOSO and GNN (P21–P23).
12. DECISION — `mas/state/decisions.md` (rows 2026-10-24 to 2026-10-29): settled definitions, accepted deviations (D-x), wording rulings, carry-forwards.
13. RULE — `mas/state/blockers/B001`–`B007`: the recording inventory (B005), the cohort decision (B003), accepted deviations (B006, B007).
14. REQUEST — `mas/03_ROADMAP.md` (P24 tasks 1–6): the content of this README.
15. OWN-CODE — ssvep-eeg-xai (the original project), read under R11 by the phases that record it; definitions only, nothing copied (`mas/state/reports/P05.md`, `P06.md`, `P11.md`, `P15.md`).
16. PAPER — Chailloux Peguero et al. (2023). SSVEP detection assessment by combining visual stimuli paradigms and no-training detection methods. Frontiers in Neuroscience 17:1142892. DOI not given in the spec. The spec `mas/01_DATA_SPEC.md` §3 was opened; the paper itself was not opened in this run. Used for: the paradigms.
17. DOCS — not opened in this run: FBCSP and FBCCA primary papers, the EEGNet, Compact-CNN and ShallowConvNet papers. Methods are named as they appear in the code docstrings and the phase reports; no claim relies on a paper that was not opened.
