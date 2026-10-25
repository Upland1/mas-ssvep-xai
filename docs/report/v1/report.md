# A Leakage-Free Classical Pipeline for 5-Class SSVEP Decoding Under a 1.0-Second Constraint

> **Historical document (P06).** Its 'leakage-free' claim was later shown wrong: window-level cross-validation lets windows of the same trial fall in training and test folds (corrected in P11).

*Historical technical report v1 of the mas-ssvep-eeg-xai rebuild (phase P06, 2026-10-25). Every number below is copied from a CSV or log in the repository, with its path. Verification status: the sequential forward selection row (ours 89.85 / 95.94; R-4 84.77 / 93.40) differs from the reference by more than the tolerance. The scientific reviewer accepted this as deviation D-1 with conditions (07_review.md, results review part 1, commit 637dad6). The verifier's numeric verdict on that row is FAIL (06_verify.md) and is restated with D-1 by the verifier. The numbers are reported as produced.*

## Abstract

This report documents the first classical pipeline of the rebuild, reproduced under the legacy protocol of the original project. It has two parts: a feature-selection ablation on one subject (S03) and a five-subject cohort table (S01–S05) for a 5-class SSVEP decoder with a 1.0 s window. The decoder uses FBCSP (five sub-bands, one component per class side) and FBCCA features from seven parieto-occipital channels, a scaler, and Shrinkage-LDA. Evaluation uses window-level five-fold stratified cross-validation with seed 42, and the 2.0 s column uses the legacy `i % 5` trial smoothing. On S03 the 55-column baseline reaches 90.36 % at 1.0 s and 95.43 % at 2.0 s smoothed on 197 clean windows (reports/feature_selection_ablation_S03.csv). Four ablation rows match the reference targets exactly. The sequential forward selection row (89.85 % / 95.94 %) lies outside the ±1.5 pp tolerance; the scientific reviewer accepted it as deviation D-1 with conditions (07_review.md, commit 637dad6), and no ranking claim rests on it. Per-subject 1.0 s accuracy in the cohort ranges from 64.5 % (S01) to 98.98 % (S04), with means of 83.33 % at 1.0 s and 87.57 % at 2.0 s (reports/five_subjects_benchmark.csv). These are legacy values. The cross-validation places windows of one trial in both training and test folds, so they are not estimates of accuracy on unseen trials. The historical title's 'leakage-free' claim is wrong; the correction is made in P11.

## 1. Introduction

Steady-state visually evoked potential (SSVEP) brain–computer interfaces decode the frequency of a flickering stimulus from the scalp EEG. The paradigm of this study has five targets at 24.0, 20.0, 15.0, 10.9091 and 8.5714 Hz, shown in 5.0 s segments, with a fixation cross (code 201) and a cue (code 202) around each trial (mas/01_DATA_SPEC.md §3, [2]). The recordings are sampled at 256 Hz [2]. The title states a 1.0-second constraint. The original project's reference table reports a feature-selection ablation and a five-subject table for the same stage [4, 5]. This report reproduces the cohort table and four of the five ablation rows; the sequential forward selection row is ours, not reproduced (deviation D-1). It gives accuracies at 1.0 s and at 2.0 s smoothed.

The rebuild reproduces that stage in the order of the project's history, including its known errors [1, 3]. This report is the version-1 write-up of that stage. It states the legacy protocol as it was, and its numbers come from the runs of the phase. It does not change any number to match a reference. The historical title is kept because the roadmap asks for it, with a correction note [4, 1]. Later phases replace the protocol: trial-grouped cross-validation in P11 and the corrected report in P24 [1, 4].

## 2. Materials and Methods

### 2.1 Data source

Subjects are the folders matching `S\d+` under the legacy processed tree, discovered rather than listed (mas/01_DATA_SPEC.md §1, [2]). The cohort is S01–S05. The analysis uses the OO session, the main calibration recording with the on-off flicker paradigm, and stimulus windows only (codes 101–105) [2]. The ablation and the cohort both read the legacy folders written in P02 (data/processed/<S>/) [12, 13].

Each stimulus trial yields five 1.0 s sub-windows of 256 samples at 256 Hz, on seven channels (PO3, POz, PO4, PO8, O1, Oz, O2). PO7 is excluded in the legacy configuration [2, 13]. The original preprocessing applied a 1–60 Hz Butterworth band-pass of order 4 (zero-phase) to the continuous signal, cut the 1.0 s windows, and gated them with the P02 raw limits (vpp ≤ 200 µV, std 0.5–60 µV, vpp minimum 0.5 µV) [16]. The per-script extractor mask of this phase is then applied to every feature block: vpp 0.5–120 µV and std 0.1–35 µV (src/features/ssvep/window_mask.py:17) [12, 13]. The clean and rejected counts in Tables 1 and 3 are the result of these two gates. The P05 decision that attributes the three S03 rejections to the extractor mask rests on P02 keeping all 200 S03 windows [10].

### 2.2 Legacy protocol as it was

The following behaviours are inherited from the original project and are labelled `legacy` in the code and in each output's `.meta.txt` [9, 12, 13]:

- **Cross-validation** (R1, PF-01): `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` over windows, not over trials. Windows of one trial can sit in both the training and the test fold. This is the leak that P11 corrects [1, 3].
- **Smoothing** (R8, PF-02): the 2.0 s value averages each window with the previous one, reset at `i % 5 == 0` of the clean array. After a rejected window the reset falls on the wrong trial boundary [1, 3, 10].
- **Sampling rate** (PF-04): the features assume fs = 250 Hz on 256 Hz recordings [3, 12].
- **Filtering** (R3, PF-14): sub-band filtering of each 1.0 s window separately, which distorts the window edges [1, 3, 9].
- **Mask** (R5): one per-script mask with the limits above, shared by all blocks [1, 12].

### 2.3 Features

The FBCSP block uses five sub-bands, (7, 12), (13, 17), (18, 26), (27, 36) and (38, 52) Hz, with one component per side (m = 1), giving 5 classes × 2 × 5 bands = 50 columns (src/features/ssvep/fbcsp_extraction.py:31) [16]. The one-vs-rest CSP filters are fitted on the training rows of each fold only (R2, PF-11) [1, 3]. The FBCCA block gives five canonical-correlation scores on all seven channels, with three harmonics and Chebyshev-I sub-bands of order 4 [11]. The flagship matrix therefore has 55 columns, with the 5 FBCCA columns last (src/features/selection/feature_selection.py:1–9) [16].

### 2.4 Classifier and evaluation

A `StandardScaler` and a Shrinkage-LDA classifier (`LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")`) are fitted per fold on the training rows [11, 15]. With `shrinkage="auto"`, the covariance shrinkage uses the Ledoit–Wolf lemma [15]. The 1.0 s value is the accuracy per clean window. The 2.0 s smoothed value is the accuracy after the legacy `i % 5` smoothing [12, 13].

### 2.5 Feature-selection ablation (S03)

Five rows are evaluated inside the same five folds [9, 12]:

1. Full baseline: 55 columns.
2. Sub-band pruning: the (38, 52) Hz band is removed, which drops columns 40–49 and leaves 45 (R6) [9].
3. ANOVA F-score: `SelectKBest(f_classif)` keeps 20 of the 50 FBCSP columns, plus the 5 FBCCA columns (p = 25) [9, 10].
4. Mutual information: `mutual_info_classif(random_state=42)` keeps 20 of the 50 FBCSP columns, plus the 5 FBCCA columns (p = 25) [9, 10].
5. Sequential forward selection (SFS): `SequentialFeatureSelector` (direction forward) over the pipeline of scaler and Shrinkage-LDA, selecting 15 of the 50 FBCSP columns plus the 5 FBCCA columns (p = 20). The inner cross-validation is scikit-learn's default, 5 folds, unshuffled, with accuracy scoring [9, 10, 15].

All selection uses the training rows of its fold only, and the selected indices are applied unchanged to the test rows (R2, PF-11) [9, 14]. The SFS row is this rebuild's in-fold implementation. The original repository available to this rebuild contains no sequential forward selection code. This was checked by a read-only consultation recorded in the P06 handoff [9]. Whether the original project ran a selection of this kind, and how, cannot be determined from the repository, so the SFS definition is a reading of the reference table's p = 20 and of the roadmap [5, 4]. The scientific reviewer accepted its deviation from the reference as D-1 [8, 10], on three conditions: the value is reported as ours beside R-4's value with the reason, never as reproduced; the SFS definition is named wherever the row appears; and the original configuration is an open question for the human operator.

### 2.6 Cohort benchmark

The cohort script runs the flagship code path (`prepare_subject`, `benchmark_spaces`, `oof_space`, `accuracies`) for each discovered subject, with the same protocol as above, and writes the columns of requirements §6 with a Mean row [6, 13]. The Mean row is the mean of the rounded CSV values, with the count cells left blank (Table 3; shown script in Section 6) [13].

### 2.7 Reproduction and checks

The reported runs were executed at commit 7575405 with an empty `git status` and Python 3.12.3, and each log records the command, the commit and the exit code [7, 12, 13]. The later commits of the phase added diagnostic options only, and the reported rows of the ablation CSV are identical with and without them [7, 9]. The test suite ran as `455 passed, 10 warnings` in a clean worktree [7]. The reference numbers of the ablation (R-4) and the cohort (R-5) are taken from the reference table, with tolerances of ±1.5 pp per row and ±1.0 pp for the cohort mean [5, 4].

## 3. Results

### 3.1 Feature-selection ablation, S03

**Table 1.** Ablation on S03, verbatim from reports/feature_selection_ablation_S03.csv (command and log in reports/logs/P06/benchmark_feature_selection_20261025_035546.log [12]).

| Subject | Method | p | 1.0s Acc (%) | 2.0s Smoothed (%) | Clean Windows | Rejected |
|---|---|---|---|---|---|---|
| S03 | Full baseline | 55 | 90.36 | 95.43 | 197 | 3 |
| S03 | Sub-band pruning (drop 38-52 Hz) | 45 | 87.31 | 94.92 | 197 | 3 |
| S03 | ANOVA F-score | 25 | 86.29 | 94.42 | 197 | 3 |
| S03 | Mutual information | 25 | 87.82 | 93.4 | 197 | 3 |
| S03 | Sequential forward selection | 20 | 89.85 | 95.94 | 197 | 3 |

**Table 2.** Comparison with the reference targets of R-4 (mas/04_REFERENCE_RESULTS.md, R-4 table, lines 53–74 [5]). Deltas are CSV minus reference, computed by the shown script (Section 6).

| Method | p (CSV / R-4) | 1.0 s (CSV / R-4) | Delta 1.0 s (pp) | 2.0 s (CSV / R-4) | Delta 2.0 s (pp) |
|---|---|---|---|---|---|
| Full baseline | 55 / 55 | 90.36 / 90.36 | +0.00 | 95.43 / 95.43 | +0.00 |
| Sub-band pruning (drop 38-52 Hz) | 45 / 45 | 87.31 / 87.31 | +0.00 | 94.92 / 94.92 | +0.00 |
| ANOVA F-score | 25 / 25 | 86.29 / 86.29 | +0.00 | 94.42 / 94.42 | +0.00 |
| Mutual information | 25 / 25 | 87.82 / 87.82 | +0.00 | 93.4 / 93.40 | +0.00 |
| Sequential forward selection | 20 / 20 | 89.85 / 84.77 | +5.08 | 95.94 / 93.40 | +2.54 |

The p values and the four rows of the full baseline, pruning, ANOVA and mutual information agree with the reference exactly. The sequential forward selection row does not. Its 1.0 s value is 5.08 pp above the reference, which is 177 windows of 197 against an accepted range of 165–169, and its 2.0 s value is 2.54 pp above, 189 windows against 182–186 [7]. The verifier's numeric verdict is therefore FAIL on this row [7], and the scientific reviewer accepted the deviation as D-1 [8]. One window of 197 is 0.5076 pp (shown script). The sequential forward selection row is the only one whose 2.0 s value exceeds the full baseline (95.94 against 95.43, Table 1). That difference is one window, a tie within the noise of this subject and not a gain. The row is ours, reported as 89.85 / 95.94 with R-4's 84.77 / 93.40 beside it. Its definition is a scikit-learn `SequentialFeatureSelector` in forward mode over scaler plus Shrinkage-LDA (lsqr, auto), with an unshuffled stratified inner 5-fold cross-validation and accuracy scoring, selecting 15 of the 50 FBCSP columns plus the 5 FBCCA columns, fitted in-fold [8, 9]. Its value is configuration-sensitive (Table 5), so no conclusion should be drawn from this row. The per-fold audit of its selection does not show test rows in the selection input: five folds with 157–158 selection rows, 39–40 disjoint test rows, and 0 test rows found in the selection input (reports/feature_selection_sfs_audit_S03.csv) [14].

### 3.2 Cohort, S01–S05

**Table 3.** Cohort, verbatim from reports/five_subjects_benchmark.csv (log reports/logs/P06/benchmark_5_subjects_20261025_035706.log [13]). Every row is the legacy protocol of Section 2.2, on the legacy folders of Section 2.1 [13].

| Subject | Clean Windows | Rejected | 1.0s Acc (%) | 2.0s Smoothed (%) |
|---|---|---|---|---|
| S01 | 200 | 0 | 64.5 | 75.5 |
| S02 | 196 | 3 | 66.33 | 71.94 |
| S03 | 197 | 3 | 90.36 | 95.43 |
| S04 | 197 | 1 | 98.98 | 98.48 |
| S05 | 200 | 0 | 96.5 | 96.5 |
| Mean |  |  | 83.33 | 87.57 |

The per-subject values are reported because the mean hides a range of 64.5 % to 98.98 % at 1.0 s. The legacy smoothing adds 11.00 pp for S01, 5.61 pp for S02 and 5.07 pp for S03 (Table 4). It lowers S04 by 0.50 pp and leaves S05 unchanged. The mean of the rounded rows reproduces as 83.334 and 87.570 (shown script).

**Table 4.** Smoothing gain per subject (2.0 s smoothed minus 1.0 s), computed from Table 3 by the shown script.

| Subject | 1.0 s (%) | 2.0 s smoothed (%) | Difference (pp) |
|---|---|---|---|
| S01 | 64.5 | 75.5 | +11.00 |
| S02 | 66.33 | 71.94 | +5.61 |
| S03 | 90.36 | 95.43 | +5.07 |
| S04 | 98.98 | 98.48 | -0.50 |
| S05 | 96.5 | 96.5 | +0.00 |

### 3.3 Diagnostic variants of the selection row

Because the SFS row missed its reference, one investigation round ran labelled diagnostic variants of the same selection, one factor at a time. These variants are not reported results and do not replace Table 1 [7, 9]. The table below is copied from reports/feature_selection_sfs_diagnostics_S03.csv (log reports/logs/P06/benchmark_feature_selection_diag_20261025_043543.log [14]). Window counts are round(accuracy × 197 / 100).

**Table 5.** SFS diagnostics (DIAGNOSTIC, not reported). The first row is the reported configuration.

| Variant | p | 1.0 s (%) | 2.0 s smoothed (%) | 1.0 s windows | 2.0 s windows |
|---|---|---|---|---|---|
| reported | 20 | 89.85 | 95.94 | 177 | 189 |
| cv=3 | 20 | 87.82 | 93.91 | 173 | 185 |
| cv=10 | 20 | 88.32 | 94.92 | 174 | 187 |
| cv=3 shuffled | 20 | 87.82 | 95.43 | 173 | 188 |
| cv=5 shuffled | 20 | 87.82 | 95.43 | 173 | 188 |
| cv=10 shuffled | 20 | 88.83 | 95.43 | 175 | 188 |
| plain LDA svd | 20 | 87.31 | 95.94 | 172 | 189 |
| Shrinkage-LDA no scaler | 20 | 89.85 | 95.94 | 177 | 189 |
| all 55 columns, n=20 | 20 | 84.26 | 90.86 | 166 | 179 |
| n=20 FBCSP columns | 25 | 89.85 | 94.92 | 177 | 187 |

No variant falls inside both accepted ranges. The inner cross-validation setting changes the 1.0 s value by up to 2.03 pp (reported 89.85 against cv=3, 87.82). The round establishes that the SFS value depends on the selector's configuration, and that the reported configuration was fixed before the diagnostics ran [7, 8].

## 4. Discussion

**What the legacy numbers support.** The cohort table and four of the five ablation rows reproduce the reference values numerically; the SFS row does not (D-1). The cohort table shows a large spread between subjects: S01 reaches 64.5 % at 1.0 s and S04 98.98 %. They are a record of the original project's protocol. They are not evidence of performance on new trials. Each test fold holds windows from trials that also have windows in the training folds, and the five sub-windows of one five-second trial share its artifacts and electrode state [2, 3]. The size of the inflation is not measured in this phase. P11 measures the grouped version against the corrected reference [1, 4].

**How to read the ablation.** All ablation values are for one subject and one split of its windows. One window is 0.51 pp at 197 windows, so the differences between the rows of Table 1 are at most a few windows. Pruning costs 3.05 pp at 1.0 s, about six windows (shown script). No uncertainty interval was computed, so the rows are not ranked by significance. Every reduced set is at or below the full baseline at 1.0 s, by 0.51–4.07 pp (1–8 windows; shown script); with one subject, a leaky split and no interval, no reduction is singled out. This reading depends on one subject and on the legacy window-level protocol.

**The sequential forward selection row (deviation D-1).** Ours is 89.85 % at 1.0 s and 95.94 % at 2.0 s smoothed; R-4 gives 84.77 % and 93.40 %, and the difference is outside the ±1.5 pp tolerance [5, 7]. The leak audit shows no test rows in the selection input [14]. The reference repository contains no sequential forward selection, so the row cannot be matched to a reference implementation [9]. The original project's technical report, which may describe such a run, was not inspected in this rebuild [9]. The scientific reviewer accepted the deviation as D-1 on three conditions: the value is reported as ours beside R-4's value with the reason, never as reproduced; the SFS definition is named wherever the row appears; and the original configuration (the original report or the run) is an open question for the human operator [8]. Its 2.0 s value exceeds the full baseline by one window, a tie and not a gain [Table 1]. Its 1.0 s value spans 172–177 windows across the inner cross-validation and estimator variants (185–189 at 2.0 s; the all-55-column variant is excluded), so neither the reference's order of methods nor ours is a finding [8, 14].

**Cohort and the smoothing rule.** The 2.0 s column is the legacy `i % 5` rule, which is misaligned after a rejected window [3, 10]. Its gains differ by subject (Table 4), so the cohort mean at 2.0 s is not a per-window decision gain. R9 requires that the per-subject values be read beside the mean. S02 and S03 have three rejected windows each and S04 one, so the `i % 5` resets of these three subjects, including every S03 ablation row, are misaligned after their rejections [13, 3].

**Status of the title.** The original title claims a leakage-free pipeline. The cross-validation of this report is window-level and the claim is therefore wrong. The title is kept here as history, with the correction note at the top, as the roadmap requires [4, 10].

## 5. Conclusion

This report reproduces the legacy classical stage on S01–S05 and four of the five rows of the S03 feature-selection ablation under the original protocol; the sequential forward selection row is ours (deviation D-1). The full baseline on S03 reaches 90.36 % at 1.0 s and 95.43 % at 2.0 s on 197 clean windows, and four of the five ablation rows match the reference exactly [12, 5]. The sequential forward selection row is outside tolerance and was accepted by the scientific reviewer as deviation D-1 (ours 89.85 / 95.94 against R-4's 84.77 / 93.40). Its value depends on the inner cross-validation, so no conclusion is drawn from it [7, 8, 14]. The cohort table gives 83.33 % and 87.57 % as legacy means, with a per-subject range from 64.5 % to 98.98 % at 1.0 s [13]. None of these values estimates accuracy on unseen trials. P11 replaces the cross-validation with a trial-grouped one, and P24 replaces this report [1, 4].

## 6. Shown script for the tables and arithmetic

The tables above were printed by a script run with `python3 -I` from the repository root, reading only the CSVs (never `data/raw`). Cells are copied from its output, so CSV values keep their written form (for example `93.4`). The only typed values are the R-4 targets from mas/04_REFERENCE_RESULTS.md [5]. The script is in mas/state/phases/P06-feature-selection-cohort/03_changes_scribe.md, "Part C". The arithmetic was run as `python3 -I -c` and printed: pruning vs full 90.36−87.31 = 3.05 pp (6.01 windows at 100/197); ANOVA vs full 4.07 pp (8.02 windows) and mutual information vs full 2.54 pp (5.0 windows), from reports/feature_selection_ablation_S03.csv; SFS vs full 0.51 pp at 1.0 s and 0.51 pp at 2.0 s; SFS vs reference 5.08 and 2.54 pp; cv=3 vs reported 2.03 pp; one window 0.5076 pp; cohort gains 11.0, 5.61, 5.07, −0.5, 0.0 pp; cohort rounded means 83.334 and 87.57.

## References

1. RULE — mas/RULES.md, R1, R2, R3, R5, R6, R8, R9, R10, R11 and the era matrix (R8 row corrected in P05). Used for: the legacy protocol and its labels.
2. DATA — mas/01_DATA_SPEC.md §1 (layout, OO session, subject discovery), §3 (event codes, paradigms; the paradigm reference named there was not opened for this report and is not cited), §5.1 (legacy 1.0 s windows of 256 samples, seven channels, PO7 excluded), and the sampling-rate line (256 Hz). Used for: data source, windows, sampling rate.
3. DATA — mas/05_PITFALLS.md PF-01, PF-02, PF-04, PF-10, PF-11, PF-14. Used for: the legacy flaws and their fixes.
4. REQUEST — mas/03_ROADMAP.md, P06 tasks 1–4 and the acceptance line; the title and the correction note follow the roadmap's Origin paragraph. Used for: the phase scope and the title.
5. DATA — mas/04_REFERENCE_RESULTS.md, R-4 and R-5 tables (lines 53–74) and the R-6 header. Used for: the reference targets and tolerances (R-6 is named as not comparable).
6. REQUEST — mas/02_REQUIREMENTS.md §6, the schema of reports/five_subjects_benchmark.csv (line 199). Used for: the cohort columns.
7. HANDOFF — mas/state/phases/P06-feature-selection-cohort/06_verify.md (verdict FAIL, R-4 and R-5 tables, diagnostic run) and 05_run.md (commit 7575405, test suite, runtimes). Used for: verdicts and run facts.
8. HANDOFF — mas/state/phases/P06-feature-selection-cohort/07_review.md, pre-run audit (PASS), the pre-committed miss procedure, and results review part 1 (D-1, commit 637dad6). Used for: the rules applied and the procedure.
9. HANDOFF — mas/state/phases/P06-feature-selection-cohort/03_changes_ml-engineer.md (implementation, deviations, Round 1 investigation and R11 consultation). Used for: method definitions and the reference read-out; the reference repository was not opened for this report.
10. HANDOFF — mas/state/decisions.md, P05 and P06 rows (2026-10-24, 2026-10-25). Used for: the settled definitions and the open items.
11. HANDOFF — mas/state/reports/P05.md, §2 (extractor definitions: FBCCA with three harmonics and Chebyshev-I order 4; in-fold CSP; P05 mask) and §4. Used for: the feature definitions of the flagship.
12. DATA — reports/feature_selection_ablation_S03.csv, reports/feature_selection_ablation_S03.meta.txt, log reports/logs/P06/benchmark_feature_selection_20261025_035546.log (commit 7575405, exit 0). Used for: Table 1 and the protocol labels.
13. DATA — reports/five_subjects_benchmark.csv, reports/five_subjects_benchmark.meta.txt, log reports/logs/P06/benchmark_5_subjects_20261025_035706.log (commit 7575405, exit 0). Used for: Table 3 and the cohort labels.
14. DATA — reports/feature_selection_sfs_diagnostics_S03.csv, reports/feature_selection_sfs_audit_S03.csv, log reports/logs/P06/benchmark_feature_selection_diag_20261025_043543.log (commit 7de11ce, exit 0). Used for: Table 5 and the audit.
15. DOCS — scikit-learn 1.9.1, installed package, feature_selection/_sequential.py:189–191 (direction forward; scoring default; cv default 5) and discriminant_analysis.py:48 (`shrinkage='auto'`: Ledoit–Wolf lemma). Opened in this run by reading those lines. Used for: the ablation definitions.
16. DATA — project configuration and code at the phase commit: configs/pipeline_config.yaml (preprocessing block: lowcut 1.0 Hz, highcut 60.0 Hz, order 4), scripts/preprocessing/run_preprocessing.py:1–7, 60–61, 116–118 (filter, raw gate, legacy limits), src/features/ssvep/window_mask.py:17 (extractor mask), src/features/ssvep/fbcsp_extraction.py:31, 46–47 (sub-bands; per-window filtering, legacy). Read in this run. Used for: the pipeline description.

Not cited: the primary papers for FBCSP, FBCCA and the Ledoit–Wolf estimator. They were not opened for this report, so no claim relies on them (R10).
