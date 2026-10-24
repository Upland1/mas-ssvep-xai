# 05 — Pitfalls: every trap the original project hit

Each entry: **symptom → cause → fix → phase → test that guards it.** Where the roadmap
says "reproduce the bug first", build the faulty variant behind a flag or in a
diagnostic script, show its effect with numbers, then fix it.

## Evaluation and data handling

**PF-01 · Trial leakage in cross-validation** (P11)
Symptom: inflated accuracy, much more for CNNs than for LDA. Cause: `StratifiedKFold`
on 1 s sub-windows; the 5 sub-windows of one 5 s trial share artifacts, electrode state
and background, so a model can "recognize the trial". Fix: `build_trial_ids` +
`StratifiedGroupKFold(groups=trial_ids)` in every benchmark, inner validation splits
grouped too. Test: no trial id in both train and test, for every split helper.

**PF-02 · Smoothing across trial boundaries** (P04, P11, P16)
The earliest temporal integration averaged consecutive windows with no reset. The legacy
rule `i % 5 == 0` resets every 5 windows of the *clean* array — misaligned once a window
of a trial was rejected. Fix: reset at the first window of each true trial, windows
ordered by offset (built folders).

**PF-03 · Approximate trial ids in legacy folders** (P11, P13, P14)
`build_trial_ids` infers trials from contiguous same-label blocks; a block whose length is
not a multiple of the trial length (a window lost to the raw gate) yields a short
"trial". Always compute ids on the **pre-gate** labels and index them with the same
`valid_mask` as `y_clean`; when two gates are chained, chain the masks
(`ids[mask1][mask2]`). Report affected subjects (`trial_ids_approximate`). Built folders
store true ids.

**PF-04 · Wrong sampling rate** (P16)
Feature code defaulted to `fs = 250` while the recordings are 256 Hz: every frequency
axis is scaled by 250/256 (a "24 ± 1 Hz" band is really 23.4–25.4 Hz; reference
sinusoids are off-frequency). Fix: always use the header/meta fs. Era A/B reproduce the
error deliberately and say so.

**PF-05 · Missing channel (PO7)** (P07)
The config hard-excluded PO7, so legacy arrays have 7 channels while the montage has 8.
Fix: keep all 8 and let the quality gate decide; `resolve_channel_names` maps 8 → full
montage, 7 → montage without PO7, else None.

**PF-06 · Positional channel indices** (P07)
Index lists such as `[3, 4, 5, 6]` silently point at other electrodes after the montage
changes or after a subject-specific channel drop. Select channels by **name**.

**PF-07 · Inherited default threshold rejects everything** (P07)
After the shared `validate_eeg_windows` default changed to `vpp_min = 5.0`, the raw
preprocessing gate (which never passed `vpp_min`) rejected all 320 windows of S03. Fix:
pin `vpp_min = 0.5` explicitly in `extract_clean_subwindows_psd`; add
`summarize_window_quality` diagnostics. Test: legacy raw gate keeps windows with
Vpp between 0.5 and 5 µV.

**PF-08 · Changing a function's return arity** (P07)
Extractors went from 3 to 4 return values; six consumer scripts broke. Fix: update every
consumer in the same change; a smoke test imports and runs each script on synthetic data.

**PF-09 · Stale root arrays** (all)
The legacy `data/processed/` root held S03 arrays from different runs (`X_time_windows`
with 320 rows vs `y_labels` with 317). Never mix root and per-subject arrays; scripts
check that lengths match and fail loudly.

**PF-10 · Double gating** (P05, P07)
`benchmark_cross_validation` runs the gate inside the PSD extractor and again inside the
FBCCA extractor; `benchmark_harmonic_fbcca` computes harmonic PSD on all windows and must
then align it with FBCCA's `valid_mask`. Align every feature block with the final mask.

**PF-11 · Full-data CSP** (P05)
`extract_fbcsp_features` fits CSP on all windows — only valid for visualization.
Benchmarks fit CSP inside each training fold.

**PF-12 · QDA rank failure** (P05)
QDA fails on high-dimensional spaces with few windows per class; exclude it from those
benchmarks (keep it in the suite).

**PF-13 · Cue windows lie in the fixation period** (data spec)
The 202 "cue" window is the second *before* the 202 pulse, i.e. the end of fixation.
Keep this definition (it is what all reported numbers used) and document it; never use
202 as the no-stimulus baseline.

## Signal processing and connectivity

**PF-14 · Edge effects of per-window filtering** (P16)
Filtering each 1 s window separately distorts its first/last ~100 ms, worst for narrow
FBCSP bands. Fix: filter the continuous recording, then cut (`--filter-mode continuous`),
and guard windows near artifacts by the filters' ringing time.

**PF-15 · Coherence small-sample bias** (P12)
Coherence per 1 s window then averaged is biased upward (~0.32–0.35 for independent
noise) — systematic, so averaging does not remove it. Fix: concatenate the condition's
windows and run Welch once (`compute_condition_coherence`).

**PF-16 · Apples-to-oranges baseline** (P12)
Broadband (5–35 Hz) baseline vs ±1 Hz stimulus band. Fix: re-score the same 201 windows
in each stimulus band (`baseline_matched`) and report stimulus − matched baseline as the
primary result.

**PF-17 · MVAR coefficient slicing** (P13)
The design matrix is channel-major (`column = c·p + (lag−1)`), but coefficients were read
as contiguous lag blocks (`weights[lag*C:(lag+1)*C]`) — ~150–200 % error, PDC/Granger
meaningless. Fix: strided `weights[lag::p, :].T`. Test: recover a synthetic VAR(p).

**PF-18 · Hilbert phase on short windows** (P13)
filtfilt + Hilbert on 256-sample windows with a ±1 Hz band corrupts the edges (envelope
5–70 % of truth, unstable instantaneous frequency); padding, lower order or a wider band
do not fix it. Fix: phase from the band-averaged cross-spectral density (one complex value
per window). Test: corrupting edge samples leaves PLV unchanged.

**PF-19 · Window-level permutations** (P13)
Shuffling sub-windows individually ignores their dependence within a trial → null too
narrow, p-values too small. Fix: permute whole trials with matched group window counts
(at most one trial split). Matching counts also cancels the estimator's size-dependent
bias.

**PF-20 · Two criteria collapsed into one star** (P13)
The cohort console flagged significance from the FDR-edge count instead of the global
p-value. Report (A) ≥ 1 FDR/NBS edge and (B) global p < α separately; they can disagree
both ways.

**PF-21 · Circular responder definition** (P14)
Responders are defined from classifier accuracy (2.0 s smoothed ≥ 80 % or explicit
list), never from connectivity.

**PF-22 · Spearman-Brown on non-positive r** (P14)
`2r/(1+r)` for r ≤ 0 can go below −1. Report non-positive split-half r uncorrected
("not reliable").

**PF-23 · Alpha measure contaminated by the target** (P14)
For 10.91 and 8.57 Hz the target lies inside 8–13 Hz; exclude f0 ± 1.5 Hz from the alpha
band (for stimulus and baseline alike).

**PF-24 · Comparing raw connectivity across frequencies** (P14)
Each frequency is scored in its own band; resting alpha lifts 8–13 Hz. Compare
**delta** matrices only; nearby electrodes always correlate, so read QAP p-values and
differences between pairs, not raw r. Do not compute path-length/efficiency measures on
signed deltas.

**PF-25 · Directed PDC in undirected statistics** (P14, P18)
Symmetrize PDC (`(M + Mᵀ)/2`, nulls likewise) before node strength or NBS.

**PF-26 · Missing channels across subjects** (P14)
Store `channels_kept` in every edge file and embed each matrix into the 8 × 8 montage
with NaN for missing channels before averaging across subjects.

**PF-27 · Misspelled duplicate script** (P14)
The original kept both `check_power_alpha_confound.py` and `check_power_alpha_cofound.py`.
Create only the correctly spelled one.

## Deep learning

**PF-28 · Nondeterministic A/B comparisons** (P08–P10)
Two runs of the same command differed by several points. Seed `torch.manual_seed(42 +
fold)` **before** building each fold's model; seed the DataLoader generator.

**PF-29 · Augmentation scope** (P10)
Augmentation only on the training fold, on the fly; mixup only between windows of the
**same class** (mixing classes blends two frequencies that match neither label).

**PF-30 · Misreading near-chance test accuracy** (P10)
Measure final training accuracy on the **un-augmented** training fold: low train acc =
optimization problem; high train acc + chance test = generalization problem (S01/S02).

**PF-31 · Two different "Compact" networks** (P09 vs P20)
`CompactCNN` (spatial → temporal, 56,021 params) in P09–P11, and `compact` =
`EEGNetSSVEP(F1=96, D=1, F2=96, kernel=fs//2)` in the sweeps/LOSO (28,229 params at 8
channels). Name them distinctly in every table (`compact_cnn` vs `compact_eegnet`).

**PF-32 · Early stopping on test data** (P20–P23)
Validation for early stopping = 20 % of the **training trials** (grouped), never the test
fold and never the held-out subject.

## Generalization (LOSO) and online

**PF-33 · Trial-id collisions across subjects** (P21)
Trial ids restart at 0 per subject; offset them before pooling.

**PF-34 · Unequal channel sets** (P21)
CSP filters and CNN inputs need the same channels for all subjects: use channels kept
in every subject (`common`), `all`, or an explicit list (leaving out subjects whose gate
rejected one of them).

**PF-35 · Per-subject normalization is transductive** (P21–P23)
`lda_subjnorm` / `_subjnorm` use the test subject's unlabeled statistics from the whole
session. Label it "unsupervised per-subject normalization"; P22's warm-up variant
estimates it from the first K trials only.

**PF-36 · Trial order ≠ recording order** (P22)
Trial ids follow class order in built folders; sort trials by their first window start
to get the recording order for warm-up.

**PF-37 · Mixing configurations in resumable runs** (P21–P23)
Saved folds must store their configuration (channels, training subjects, hyperparameters)
and a rerun with different settings must refuse to reuse them.

**PF-38 · Non-causal processing in "online" evaluation** (P20)
Use a stateful causal SOS filter carried across chunks (initialize `zi` from the first
sample), windows on a fixed clock, MARK channel only for scoring. Batch prediction is
allowed only because each window contains past samples only.

**PF-39 · Paradigm mismatch** (P20)
Checkerboard responses appear at twice the stimulation frequency; warn when training on
OO and testing on C (or vice versa).

**PF-40 · Colab** (P21)
The runtime is wiped on disconnect → results on Drive, code re-cloned each session,
resumable folds, a new `LOSO_OUT` per configuration; never `pip install -r
requirements.txt` (it can replace the GPU PyTorch); release the runtime at the end.
