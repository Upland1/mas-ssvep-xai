# 04 — Reference results from the original project

These are the numbers the original project measured. Use them to **diagnose** your
implementation, never to tune it (AGENTS.md rule 5).

## Tolerance rules

| Kind of result | Expected agreement | Must be explained if |
|---|---|---|
| Window counts, channels kept, rejected windows, parameter counts | exact | any difference |
| Deterministic classical pipelines (CSP, FBCCA, scaler, LDA) | per subject ±1.5 pp, cohort mean ±1.0 pp | outside that range |
| Neural networks (seeded, but GPU / library nondeterminism) | per subject ±5 pp, cohort mean ±3 pp | outside that range, or a sign flip of an A/B delta at cohort level |
| Permutation statistics (Monte Carlo) | same qualitative pattern; FDR-edge totals per subject within ±25 % or ±5 edges | a subject switches between "no effect" and "effect" for 24 Hz |
| Descriptive statistics (r, SNR dB, reliability) | ±0.05 (r, reliability), ±0.5 dB | outside that range |

A deviation can be accepted when the Scientific Reviewer signs an explanation in the
phase report (e.g. library version, documented ambiguity). Record every accepted
deviation in `mas/state/decisions.md`.

---

## R-1 · Legacy window counts (P02)

All windows (`201 + 202 + 101–105`) per subject in `data/processed/<S>/y_labels.npy`:

| S01 | S02 | S03 | S04 | S05 |
|---|---|---|---|---|
| 320 | 318 | 317 | 317 | 320 |

Stimulus windows before the two-tier gate (from R-6 clean + rejected): S01 200, S02 199,
S03 200, S04 198, S05 200. Legacy arrays have 7 channels × 256 samples; PSD features 217.

Graph datasets (P15, clean stimulus windows): S01 200, S02 196, S03 197, S04 197, S05 200.

## R-2 · Early hybrid models (P04)

The original saved `outputs/reports/s01_model_evaluation.csv` (columns `Subject,
Classifier, Accuracy, Recall per Class`), confusion-matrix figures for Shrinkage-LDA,
Linear SVM, RBF SVM, Random Forest and an MLP (64-32), the XAI heatmaps and the
exported S01/S04 models. Their numeric values were not preserved — record yours.

## R-3 · S03 flagship, legacy leaky CV (P05)

FBCSP (m=1, 5 bands, in-fold) + FBCCA (3 harmonics) → StandardScaler →
Shrinkage-LDA, `StratifiedKFold(5, shuffle, 42)`, `fs=250`:
**90.36 % (1.0 s) / 95.43 % (2.0 s smoothed)**, 197 clean windows, 3 rejected.

Qualitative: perfect precision on 24 Hz; residual confusion concentrated on the
10.9091 / 8.5714 Hz pair. Feature-space ranking: FBCSP+FBCCA hybrid best with
Shrinkage-LDA (lsqr); every supervised configuration on the hybrid beats the
zero-training FBCCA argmax.

## R-4 · Feature-selection ablation, S03, leaky (P06)

| Selection method | p | 1.0 s (%) | 2.0 s smoothed (%) |
|---|---|---|---|
| Full baseline | 55 | 90.36 | 95.43 |
| Sub-band pruning (drop 38–52 Hz) | 45 | 87.31 | 94.92 |
| ANOVA F-score | 25 | 86.29 | 94.42 |
| Mutual information | 25 | 87.82 | 93.40 |
| Sequential forward selection | 20 | 84.77 | 93.40 |

## R-5 · Five-subject cohort, legacy leaky CV (P06) — superseded

`reports/five_subjects_benchmark.csv`:

| Subject | Clean | Rejected | 1.0 s (%) | 2.0 s smoothed (%) |
|---|---|---|---|---|
| S01 | 200 | 0 | 64.50 | 75.50 |
| S02 | 196 | 3 | 66.33 | 71.94 |
| S03 | 197 | 3 | 90.36 | 95.43 |
| S04 | 197 | 1 | 98.98 | 98.48 |
| S05 | 200 | 0 | 96.50 | 96.50 |
| **Mean** | | | **83.33** | **87.57** |

## R-6 · Flagship, leak-free (P11) — the headline classical result

`reports/n_subjects_benchmark.csv`, `StratifiedGroupKFold(5, shuffle, 42)` grouped by
trial, legacy windows, `fs=250` in features, two-tier gate (vpp 5–120, std 1–35, channel
fail > 50 %):

| Subject | Channels kept | Dropped | Clean | Rejected | 1.0 s (%) | 2.0 s smoothed (%) |
|---|---|---|---|---|---|---|
| S01 | 7 | none | 200 | 0 | 61.00 | 67.50 |
| S02 | 7 | none | 196 | 3 | 56.12 | 61.73 |
| S03 | 7 | none | 197 | 3 | 86.80 | 90.36 |
| S04 | 7 | none | 197 | 1 | 97.46 | 97.97 |
| S05 | 7 | none | 200 | 0 | 95.00 | 95.50 |
| **Mean** | | | | | **79.28** | **82.61** |

(7 channels because these arrays predate the PO7 restoration; P16 rebuilds with 8.)
Leak effect: −4.05 pp (1.0 s) / −4.96 pp (2.0 s) on the cohort mean; S02 becomes the
hardest subject.

## R-7 · Deep learning per subject, augmentation ON, leak-free (P11)

1.0 s accuracy (%), 150 epochs/fold:

| Model | S01 | S02 | S03 | S04 | S05 |
|---|---|---|---|---|---|
| ShallowConvNet | 56.50 | 35.20 | 89.34 | 98.98 | 98.50 |
| EEGNet | 34.50 | 26.02 | 79.19 | 99.49 | 92.00 |
| Compact-CNN | 27.50 | 19.39 | 62.94 | 97.97 | 62.00 |

## R-8 · Parameter counts (7 channels × 256 samples, 5 classes)

| EEGNet | ShallowConvNet | Compact-CNN (`CompactCNN` class) | DualBranchFusionCNN | ConnectivityGNN nodes+F | nodes+coh+F |
|---|---|---|---|---|---|
| 2,349 | 14,485 | 56,021 | 10,005 | 5,150 | 5,534 |

Counts assume the original layer choices: every convolution followed by BatchNorm has
`bias=False` (EEGNet, Compact-CNN, ShallowConvNet temporal and spatial convs, both
DualBranchFusionCNN convs); Linear layers keep their bias. With conv biases,
ShallowConvNet and the fusion CNN come out larger — that is a spec deviation, not a
pass.

Era-C sweep networks (256 samples at 256 Hz, `kernel = fs // 2 = 128`), verified by
instantiating the original classes:

| Network | 7 channels | 8 channels |
|---|---|---|
| CCNN (`f 3–50 Hz, 0.25 Hz`) | 27,977 | 32,309 |
| `compact` = EEGNetSSVEP(F1=96, D=1, F2=96, dropout 0.5) | 28,133 | 28,229 |
| `eegnet` = EEGNetSSVEP(defaults, kernel 128) | — | 2,389 |

## R-9 · Augmentation A/B

**R-9a (leaky, P10):** EEGNet first cohort run +3.00 pp (1.0 s) / +1.79 pp (2.0 s),
4/5 subjects improved, S02 regressed, S01/S02 ≈ 27–28 % while the classical flagship
had 64–66 % for them. The last leaky run before the fix: EEGNet +7.34 pp (1.0 s).

**R-9b (leak-free, P11)** — `reports/augmentation_ab_<model>.csv`:

EEGNet

| Subject | 1.0s OFF | 1.0s ON | Δ | 2.0s OFF | 2.0s ON | Δ | Train OFF | Train ON |
|---|---|---|---|---|---|---|---|---|
| S01 | 34.50 | 34.50 | 0.00 | 35.50 | 34.50 | −1.00 | 86.42 | 78.26 |
| S02 | 27.04 | 26.02 | −1.02 | 29.08 | 30.10 | 1.02 | 83.17 | 73.97 |
| S03 | 73.60 | 79.19 | 5.58 | 82.23 | 85.28 | 3.05 | 98.86 | 97.59 |
| S04 | 98.98 | 99.49 | 0.51 | 98.48 | 98.98 | 0.51 | 100.00 | 100.00 |
| S05 | 87.00 | 92.00 | 5.00 | 92.50 | 95.00 | 2.50 | 99.87 | 99.74 |
| Mean | 64.22 | 66.24 | +2.01 | 67.56 | 68.77 | +1.22 | 93.66 | 89.91 |

Compact-CNN (`CompactCNN` class)

| Subject | 1.0s OFF | 1.0s ON | Δ | 2.0s OFF | 2.0s ON | Δ | Train OFF | Train ON |
|---|---|---|---|---|---|---|---|---|
| S01 | 20.50 | 27.50 | 7.00 | 21.00 | 31.00 | 10.00 | 100 | 100 |
| S02 | 26.53 | 19.39 | −7.14 | 27.04 | 19.39 | −7.65 | 100 | 100 |
| S03 | 42.64 | 62.94 | 20.30 | 46.70 | 71.07 | 24.37 | 100 | 100 |
| S04 | 54.82 | 97.97 | 43.15 | 61.93 | 98.98 | 37.06 | 100 | 100 |
| S05 | 39.50 | 62.00 | 22.50 | 49.50 | 68.00 | 18.50 | 100 | 100 |
| Mean | 36.80 | 53.96 | +17.16 | 41.23 | 57.69 | +16.46 | 100 | 100 |

ShallowConvNet

| Subject | 1.0s OFF | 1.0s ON | Δ | 2.0s OFF | 2.0s ON | Δ | Train OFF | Train ON |
|---|---|---|---|---|---|---|---|---|
| S01 | 53.50 | 56.50 | 3.00 | 57.50 | 67.00 | 9.50 | 100 | 99.88 |
| S02 | 32.14 | 35.20 | 3.06 | 37.24 | 36.73 | −0.51 | 100 | 100 |
| S03 | 85.79 | 89.34 | 3.55 | 91.37 | 92.89 | 1.52 | 100 | 100 |
| S04 | 97.97 | 98.98 | 1.02 | 98.98 | 98.98 | 0.00 | 100 | 100 |
| S05 | 96.50 | 98.50 | 2.00 | 97.50 | 99.00 | 1.50 | 100 | 100 |
| Mean | 73.18 | 75.70 | +2.53 | 76.52 | 78.92 | +2.40 | 100 | 99.98 |

Interpretation recorded by the original project: augmentation helps every architecture
on average, Compact-CNN most; no network beats the classical flagship on the cohort
mean; the gap comes from S01/S02, where EEGNet reaches 78–86 % training accuracy but
near-chance test accuracy (generalization, not optimization).

## R-11 · Coherence v1 bug fix (P12)

- Independent synthetic signals, 256-sample windows, nperseg 128: per-window
  coherence averaged ≈ 0.32–0.35; condition-level (concatenated) ≈ 0.01–0.02; coupled
  signals ≈ 0.98–0.99.
- S03/S04 real data (7 channels): baseline coherence ≈ 0.68–0.73 before the fix,
  ≈ 0.59–0.66 after. Differences: 24 Hz and 20 Hz consistently positive in both
  subjects (+0.11 to +0.25); 10.91 / 8.57 Hz near zero/negative in S03 but positive in
  S04.

## R-12 · Connectivity cohort statistics (P13), 200 trial-level permutations

Global one-tailed p (stimulus − matched baseline, mean over edges); the minimum
attainable is 1/201 = 0.005:

| method | freq | S01 | S02 | S03 | S04 | S05 |
|---|---|---|---|---|---|---|
| coherence | 24 Hz | 1.000 | 1.000 | 0.005 | 0.010 | 0.010 |
| coherence | 20 Hz | 0.975 | 0.851 | 0.005 | 0.005 | 0.527 |
| coherence | 15 Hz | 1.000 | 0.980 | 0.005 | 0.104 | 0.239 |
| coherence | 10.91 Hz | 0.139 | 0.746 | 0.776 | 0.005 | 1.000 |
| coherence | 8.57 Hz | 0.716 | 0.995 | 0.095 | 0.005 | 0.990 |
| wPLI | 24 Hz | 1.000 | 0.323 | 0.005 | 0.005 | 0.015 |
| wPLI | 20 Hz | 1.000 | 0.144 | 0.055 | 0.005 | 0.070 |
| wPLI | 15 Hz | 0.816 | 0.493 | 0.065 | 0.030 | 0.398 |
| wPLI | 10.91 Hz | 0.149 | 0.662 | 0.015 | 0.015 | 0.005 |
| wPLI | 8.57 Hz | 0.915 | 0.498 | 0.005 | 0.025 | 0.010 |

BH-FDR significant edges (21 per frequency, 7 channels):

| method | freq | S01 | S02 | S03 | S04 | S05 |
|---|---|---|---|---|---|---|
| coherence | 24 / 20 / 15 / 10.91 / 8.57 Hz | 0/0/0/0/0 | 0/0/0/0/0 | 20/21/16/0/8 | 12/11/7/12/9 | 12/3/0/0/0 |
| wPLI | 24 / 20 / 15 / 10.91 / 8.57 Hz | 0/0/0/0/0 | 0/3/0/0/0 | 17/0/3/3/15 | 12/17/0/4/0 | 0/0/0/13/5 |
| **Totals** coherence | | 0 | 0 | 65 | 51 | 15 |
| **Totals** wPLI | | 0 | 3 | 38 | 33 | 18 |

Pattern that must reproduce: S01/S02 essentially null; 24 Hz the only frequency
significant in all of S03–S05 for both methods; several cells near p = 0.05 flip
between 100 and 200 permutations (inconclusive at n = 5).

## R-13 · Cross-frequency comparison and confounds (P14)

Global mean delta (stimulus − matched baseline):

| method | subject | 10.91 | 15 | 20 | 24 | 8.57 Hz |
|---|---|---|---|---|---|---|
| coherence | S01 | 0.032 | −0.061 | −0.042 | −0.084 | −0.007 |
| coherence | S02 | −0.015 | −0.050 | −0.025 | −0.158 | −0.029 |
| coherence | S03 | −0.037 | 0.163 | 0.251 | 0.249 | 0.041 |
| coherence | S04 | 0.193 | 0.055 | 0.110 | 0.128 | 0.129 |
| coherence | S05 | −0.084 | 0.021 | 0.006 | 0.137 | −0.097 |
| wPLI | S01 | 0.163 | −0.073 | −0.418 | −0.295 | −0.093 |
| wPLI | S02 | −0.024 | 0.005 | 0.122 | 0.061 | 0.001 |
| wPLI | S03 | 0.350 | 0.341 | 0.226 | 0.558 | 0.466 |
| wPLI | S04 | 0.304 | 0.319 | 0.657 | 0.552 | 0.286 |
| wPLI | S05 | 0.374 | 0.058 | 0.156 | 0.372 | 0.305 |

Frequency similarity (QAP, 2,000 permutations): coherence mean r = 0.54 with 64 % of
pairs p < 0.05; wPLI mean r = 0.14 with 32 % p < 0.05.

Split-half reliability (Spearman-Brown):

| method | subject | 10.91 | 15 | 20 | 24 | 8.57 Hz |
|---|---|---|---|---|---|---|
| coherence | S01 | 0.02 | 0.96 | 0.95 | 0.94 | 0.93 |
| coherence | S02 | 0.34 | 0.78 | 0.75 | 0.96 | 0.42 |
| coherence | S03 | 0.78 | 0.93 | 0.96 | 0.93 | 0.81 |
| coherence | S04 | 0.91 | 0.95 | 0.96 | 0.95 | 0.92 |
| coherence | S05 | 0.87 | 0.87 | 0.83 | 0.84 | 0.94 |
| wPLI | S01 | 0.74 | 0.67 | 0.51 | 0.41 | 0.82 |
| wPLI | S02 | −0.75 | 0.42 | 0.72 | −0.02 | 0.58 |
| wPLI | S03 | 0.59 | 0.63 | 0.43 | 0.72 | 0.67 |
| wPLI | S04 | 0.54 | −0.25 | 0.83 | 0.70 | 0.48 |
| wPLI | S05 | 0.52 | 0.10 | 0.15 | 0.39 | 0.86 |

Pairwise between-frequency tests (500 permutations, 10 pairs × 5 subjects = 50 rows per
method): coherence 6 magnitude / 1 pattern differences with p < 0.05; wPLI 6 / 2. Some
subjects flagged with approximate trial ids (legacy folders).

Power confound (O1/Oz/O2): target SNR (dB)

| subject | 10.91 | 15 | 20 | 24 | 8.57 Hz |
|---|---|---|---|---|---|
| S01 | 0.10 | −0.50 | 0.36 | 1.54 | −1.23 |
| S02 | 0.43 | 0.42 | 0.78 | 0.06 | −0.27 |
| S03 | 1.85 | 6.96 | 9.62 | 7.81 | 1.72 |
| S04 | 7.74 | 7.91 | 9.63 | 10.16 | 5.73 |
| S05 | 1.82 | 4.07 | 5.46 | 7.83 | 2.29 |

Alpha change (dB, 8–13 Hz excluding f0 ± 1.5 Hz; negative = alpha blocking)

| subject | 10.91 | 15 | 20 | 24 | 8.57 Hz |
|---|---|---|---|---|---|
| S01 | −1.40 | −0.27 | −0.94 | 2.25 | −0.53 |
| S02 | −0.54 | −0.98 | −0.97 | −0.46 | 0.23 |
| S03 | −1.37 | −0.75 | −1.51 | −0.71 | −0.83 |
| S04 | −0.86 | −1.80 | −0.97 | −1.19 | −1.93 |
| S05 | −1.84 | −2.00 | −2.48 | −0.50 | −2.68 |

## R-14 · Connectivity gate (P15), Shrinkage-LDA, 1.0 s accuracy, mean of 5 repeats

All features (`k_select = 0`):

| Set | Dim | S01 | S02 | S03 | S04 | S05 | Mean |
|---|---|---|---|---|---|---|---|
| Ec | 105 | 48.3 | 36.1 | 45.5 | 62.4 | 50.6 | 48.6 |
| Ep | 210 | 31.2 | 34.4 | 35.2 | 52.2 | 41.2 | 38.8 |
| Ec+Ep | 315 | 47.9 | 35.2 | 48.3 | 70.7 | 51.1 | 50.6 |
| N | 70 | 31.4 | 24.6 | 79.7 | 96.3 | 94.5 | 65.3 |
| F | 5 | 40.6 | 55.3 | 68.3 | 94.9 | 83.6 | 68.5 |
| N+F (Base) | 75 | 41.2 | 48.0 | 82.7 | 98.0 | 98.9 | 73.8 |
| Base+Ep | 285 | 44.9 | 44.3 | 83.5 | 98.3 | 96.3 | 73.5 |
| Base+Ec+Ep | 390 | 51.1 | 46.5 | 82.2 | 98.9 | 95.8 | 74.9 |
| Base+Ec | 180 | 57.5 | 51.1 | 84.0 | 98.1 | 97.2 | **77.6** |

In-fold ANOVA top-30 (`k_select = 30`): Base 74.0, Base+Ec 77.5, Base+Ec+Ep 77.5,
Base+Ep 76.0, N 64.9, Ec 46.7, Ep 35.5, Ec+Ep 46.0 (means).
Verdict: Base+Ec helps the weak responders (S01 +16.3, S02 +3.1) but not the
responders (S03 +1.3, S04 +0.1, S05 −1.7) → **gate does not pass**.

## R-15 · Within-subject GNN (P15), mean of 3 repeats

| Variant | S02 1.0 s / 2.0 s / train | S03 | S05 |
|---|---|---|---|
| nodes+F | 38.6 / 46.1 / 56.4 | 77.8 / 82.2 / 86.8 | 90.0 / 95.0 / 96.1 |
| nodes+coh+F | 37.2 / 40.1 / 57.7 | 77.5 / 82.9 / 87.8 | 90.5 / 95.3 / 96.6 |

(The original ran S02, S03, S05 only; run all subjects and report these three for
comparison.) Coherence edges do not improve the GNN.

## R-16 · Era C (P16–P23): no preserved numbers

The original project's Era-C reports (edge-effect table, v2 flagship on continuous
windows at 256 Hz, 6-class and filter-bank results, NBS graph sizes, raw-signal
quality, window sweep, NN sweep, dynamic stopping, pseudo-online, LOSO, LOSO warm-up,
GNN LOSO) are git-ignored and were not delivered. For these phases there is **no
numeric target**: run them, record them, and have the Reviewer check direction and
plausibility (e.g. accuracy rising with window length while ITR peaks at short windows;
LOSO below within-subject; `fbcca` LOSO equal to its within-subject value because it
does not train; `lda_subjnorm` ≥ `lda`). If the operator later supplies the original CSVs,
add them here as R-17+ and re-verify.

Two historical facts are known and must be stated in the P16 report: the frozen v1
used `fs = 250` in feature code on 256 Hz data, and per-window sub-band filtering; the
v2 numbers are the first computed with the real sampling rate and continuous filtering.
