# P25 fix round 1 - scribe handoff (CCNN current-state documents, historical notes, sources defects)

Status: READY

## Questions

ACK 07_review.md "Fix round 1 audit (CCNN)" (S-1 to S-4, sources defects), 06_verify.md and 05_run.md "Fix round 1 rerun" scribe 2026-10-30

Scope: S-1 (label), S-2 (current-state documents), S-3 (dated notes in historical reports), S-4 (re-test of every CCNN claim), the verifier's round 1 sources defects, and the numbers of this handoff. Not done here, by design: `mas/state/reports/P25.md` (after the results review), `mas/state/phases/P25-final-audit/log.md` (orchestrator), `reports/`, logs, `reference/`, data. No consultation of the original project's code (R11 not triggered; no reference access).

## Files changed

| File | NEW / MODIFIED | Change |
|---|---|---|
| `README.md` | MODIFIED | CCNN row of the LOSO table (85.88; range 83.45–85.88); note 1 on the CCNN deviation (S-1 wording); cohort-39 `common` ccnn 72.08; one-second networks 90.53; pseudo-online paragraph and per-subject paragraph with P25 values and provenance. |
| `RESEARCH_LOG.md` | MODIFIED | Current-state pointer after the intro; one-line dated pointers after each P20, P21 and P24 paragraph that quotes ccnn; new P25 entry (before → after table, re-tested claims); status note under "Status at the end of P23"; Sources items 19 and 20. |
| `CHANGELOG.md` | MODIFIED | Pointers under the P20 and P21 bullets (lines 495, 497, 523) and the P24 bullet (line 611); new P25 section at the end. |
| `docs/report/v2/report.md` | MODIFIED | §2: ccnn parameter counts (27,977 / 32,309) and S-1 paragraph; §3.7: one-second ccnn value 90.53 with pre-P25 value marked; pseudo-online paragraph with P25 values. No new numbered source. |
| `docs/progress_report/progress_report.md` | MODIFIED | Pseudo-online result paragraph (line 131) with P25 values; ccnn LOSO row (83.45–85.88; 85.88); S-1 note above the `within_lda` paragraph. |
| `docs/infographic/methodology_infographic.svg` | MODIFIED | Pseudo-online headline 88.50 % → 90.50 %; footnote † updated to the P25 rerun; second footnote line carries the S-1 label. SVG parses (checked). |
| `notebooks/loso_colab.ipynb` | MODIFIED | "ccnn about 2.2 h" → "about 1.5 h" in three places (markdown table, expected-time cell, code comment). JSON parses (checked). Estimate method in §"Numbers" below. |
| `mas/state/reports/P11.md` | MODIFIED | Dated note appended: the access-log path is `mas/state/scratch/reference_access.log` (verifier round 1 defect). |
| `mas/state/reports/P20.md` | MODIFIED | Dated note appended: CCNN regeneration, every superseded ccnn line listed with its CSV, S-4 re-tests. |
| `mas/state/reports/P21.md` | MODIFIED | Dated notes appended: (1) `reports/window_sweep_colab` does not exist (verifier round 1 defect); (2) CCNN regeneration with per-section replacement values and CSVs. |
| `mas/state/reports/P22.md` | MODIFIED | Dated note appended: citation [23] resolved to the repository history entry `32dbde8` (verifier round 1 defect). |
| `mas/state/reports/P23.md` | MODIFIED | Dated note appended: lines 214, 218, 220 and 325 replacement values. |
| `mas/state/reports/P24.md` | MODIFIED | Dated note appended: pseudo-online values superseded, P25 values and decision counts. |
| `mas/state/phases/P25-final-audit/03_changes_scribe.md` | NEW | This handoff. |

Commits: see the scribe's final report (one commit per logical group, explicit paths, `docs:` prefix).

## S-1 label (verbatim, used in every current-state document)

"CCNN spec deviation, fixed in P25 (fix round 1, code in 987742b). From P20 to P24 the CCNN stacked [real, imag] as two input maps with bias-free convolutions (pre-P25 layout, non-conforming: 14,817 / 17,285 parameters). The roadmap and R-8 require one `[real | imag] / T` map with convolution biases (27,977 / 32,309 parameters). Every CCNN value produced before P25 is non-conforming and superseded."

Not called "bug demo" or "legacy". Every old value that appears in a current document carries "pre-P25 layout, non-conforming" in the same sentence. Results are not comparable seed by seed.

## S-2 current-state documents: what changed

- `README.md`: lines of the LOSO table (ccnn), the cohort-39 `common` sentence, the one-second networks sentence, the pseudo-online cohort paragraph and the per-subject paragraph. Line "reference network R-8" for `ccnn` (line 264) kept, as the review asked.
- `docs/report/v2/report.md`: §2 (ccnn counts added, S-1 paragraph), §3.7 one-second values and pseudo-online paragraph.
- `docs/progress_report/progress_report.md`: lines 131 and 149 and the S-1 note.
- `docs/infographic/methodology_infographic.svg`: headline value (line 121) and both footnote lines (162–163). Every pseudo-online number in the figure was checked against the CSV; the six-class headline 75.50 % is unchanged in the CSV.
- Colab runtime: `notebooks/loso_colab.ipynb`, "ccnn about 2.2 h" → "about 1.5 h". Recomputed from the regenerated per-fold `Seconds` of the 39-subject ccnn run (`reports/loso_w1/folds.csv`): sum 5297.87 s over 39 folds, mean 135.84 s, times 40 subjects = 5433.7 s = 1.51 h (shown command below). The estimate is for the same command shape (`--channels common`, 3 channels), on the RTX 3050-class GPU the old estimate used; a T4 was not measured, the existing sentence "a T4 is of similar order" is unchanged.

## S-3 historical records: dated notes only

Appended at the end of each file under a "Dated note, 2026-10-30" heading. No line was rewritten. Covered lines (each replacement value is in the note itself):
- P20.md: 187, 191–195, 207, 209, 265–267, 278–280, 293, 315, 317, 319, 345 (per-subject ccnn table, cohort means, pairwise differences, pseudo-online, R-P9, R-P12, claim table, NN sweep text). Also the S-4 re-tests.
- P21.md: §4.3 (178–198), §4.4 `common ccnn` column (206–252, superseded by `reports/loso_w1/per_subject.csv`), §4.5 (298–300), §4 P4 row and §5 (339, 345, 351), §7 (365, 375). The `window_sweep_colab` defect note.
- P23.md: 214, 218, 220, 325.
- P24.md: pseudo-online values and decision counts (sections 4.7 and the run-A values at line 200, the A-4 row at 323).
- The RESEARCH_LOG and CHANGELOG pointers are listed under "Files changed".

## S-4 re-test of the CCNN claims

Rule: each claim is re-tested under the rule it was made under. "Flipped" means the claim as worded no longer holds; it is not reworded. Values are from the regenerated CSVs; the old values are from the pre-P25 record (P20/P21/P23/P24 reports and the verifier's table in 06_verify.md, which read the scratch copies).

| # | Claim (where it was made) | Old value (pre-P25) | New value (P25 regenerated) | Holds / flipped | Source CSV |
|---|---|---|---|---|---|
| 1 | P20 P4: every model above 20 % | all above 20 % | min per model: ccnn 75.59, compact_eegnet 77.48, eegnet 71.43 | holds | `reports/nn_sweep/summary.csv` |
| 2 | P20 P4: ccnn ≥ eegnet on the cohort mean | 91.25 vs 89.69 | 90.53 vs 89.69 (+0.84) | holds | `reports/nn_sweep/summary.csv` |
| 3 | P20 P4: Train ≥ Val for every model | all rows | 0 of 15 rows fail | holds | `reports/nn_sweep/summary.csv` |
| 4 | P20 pairwise ccnn − eegnet, "not distinguishable" (R-P5) | +1.56 pp | +0.84 pp (below 3 pp) | holds (number changed) | `reports/nn_sweep/summary.csv` |
| 5 | P20 pairwise ccnn − compact_eegnet, "not distinguishable" | −0.83 pp | −1.55 pp (below 3 pp) | holds (number changed) | `reports/nn_sweep/summary.csv` |
| 6 | P20 "all within 2.4 pp" | 2.39 pp (compact − eegnet, max) | 2.39 pp (max pairwise) | holds | `reports/nn_sweep/summary.csv` |
| 7 | P20 Q2: which 1 s network performs best | not distinguishable, none ranked | compact_eegnet highest mean 92.08, no pair ≥ 3 pp | holds (no ranking) | `reports/nn_sweep/summary.csv` |
| 8 | P20 P6(a): false activations lower with six classes in every subject with ≥ 1 rest period | fails as worded (S04 0.0 vs 0.0; holds 4 of 5) | 5 of 5 lower (S01 62.5→15.0, S02 45.0→7.5, S03 20.0→0.0, S04 5.0→0.0, S05 15.0→2.5) | FLIPPED: fail → holds (as worded) | `reports/pseudo_online/summary_ccnn_{5class,6class}.csv` |
| 9 | P20 P6(b): Acc6 ≤ Acc5 in ≥ 4 of 5 | 5 of 5 | 5 of 5 (S03 95.0 = 95.0; S04 100 = 100) | holds | `reports/pseudo_online/summary_ccnn_{5class,6class}.csv` |
| 10 | P20 P6(c): min(S03–S05) above max(S01, S02) at 5 classes | 97.50 > 90.00 | 95.0 > 85.0 | holds | `reports/pseudo_online/summary_ccnn_5class.csv` |
| 11 | P20 R-P9: six-class share predicting the next target, "6 of 10 (60 %), p = 0.0064" | p = 0.0064 (nominal < 0.05), post hoc | 4 of 10 (40 %), p = 0.1209 | FLIPPED: significance at 0.05 lost; descriptive, post hoc reading unchanged | `reports/pseudo_online/decisions_ccnn_6class.csv` |
| 12 | P20 R-P9: five-class false activations and next-target share | 55; 16 of 55 (29.09 %), p = 0.0691 | 59; 15 of 59 (25.42 %), p = 0.1876 | number changed (descriptive wording holds) | `reports/pseudo_online/decisions_ccnn_5class.csv` |
| 13 | P20 R-P9 timing: all false activations within 2 s (fixation, none in the cue) | max 1.969 s (5 classes); max 1.500 s (6) | 5 classes: max 2.4375 s, one of 59 above 2 s (S01, onset 185.06 s); 6 classes: max 1.46875 s | FLIPPED for five classes; holds for six | `reports/pseudo_online/decisions_ccnn_{5class,6class}.csv` |
| 14 | P20 R-P12: 5 vs 6 change is mostly missed stimulus periods | Acc5−Acc6 15.0 pp; P(c5,w6) 17.5 %, of which missed 16.0 %; P(w5,c6) 2.5 % | Acc5−Acc6 15.0 pp; P(c5,w6) 15.5 %, of which missed 15.0 % (30 of 31 periods); P(w5,c6) 0.5 % | holds (numbers changed) | `reports/pseudo_online/decisions_ccnn_{5class,6class}.csv` |
| 15 | P20 R-P12 per-subject Acc5−Acc6 | 25.0, 42.5, 5.0, 0.0, 2.5 pp | 37.5, 35.0, 0.0, 0.0, 2.5 pp | number changed | `reports/pseudo_online/summary_ccnn_{5class,6class}.csv` |
| 16 | P21 P2 networks, matched S01, S03, S04: LOSO below within (3 of 3) | ccnn LOSO 87.61 vs within 93.18 (−5.57); 3 of 3 | LOSO 86.11 vs within 91.81 (−5.70); 3 of 3 (65.29 < 75.59; 93.34 < 99.85; 99.70 < 100.00) | holds (numbers changed) | `reports/loso_w1_s01-s05/summary.csv`, `reports/nn_sweep/summary.csv` |
| 17 | P21 P4: 0 degenerate ccnn folds per cohort-5 seed and 0 of 39 | 0 / 0 / 0; 0 of 39 | 0 / 0 / 0 (seeds 42, 43, 44); 0 of 39 | holds | `reports/loso_w1_s01-s05*/folds.csv`, `reports/loso_w1/folds.csv` |
| 18 | P21 P4: minimum best epoch (cohort 5, seed 42) | 18 | 29 (ccnn); 29 is the minimum over all networks in seed 42 (compact 38, eegnet 44) | number changed | `reports/loso_w1_s01-s05/folds.csv` |
| 19 | P21: ccnn − lda over three seeds | −1.57 pp (86.04 vs 87.61) | −2.73 pp (84.88 vs 87.61); below the 3 pp rule (R-P5) | holds as "not a difference"; magnitude changed | `reports/loso_w1_s01-s05{,_seed43,_seed44}/summary.csv` |
| 20 | P21: "a tie inside the per-subject seed range" (ccnn) | seed range up to 5.12 pp (S02); gap 1.57 | up to 9.79 pp (S02); gap 2.73; per-subject three-seed differences −0.44, −8.69, −3.99, +0.20, −0.69 (4 of 5 negative) | holds only in the loose wording (no pre-registered rule); flagged as the weakest reading, not strengthened | same |
| 21 | P21: no network ranking | no ranking | no pair of networks reaches 3 pp at 1 s; cohort-5 ccnn and eegnet have three seeds | holds | `reports/nn_sweep/summary.csv`, `reports/loso_w1_s01-s05*/summary.csv` |
| 22 | P21 C-4: three seeds before a network claim (ccnn, eegnet); compact_eegnet one seed | ccnn 3, eegnet 3, compact 1 | unchanged | holds | `reports/loso_w1_s01-s05*/summary.csv` |
| 23 | P21 cohort-39 ccnn − lda, "a tie by any reading" | −0.96 pp (71.58 vs 72.54) | −0.46 pp (72.08 vs 72.54) | holds (tie, below 3 pp) | `reports/loso_w1/summary.csv` |
| 24 | P21 cohort-39 ccnn above lda in "19 of 39" | 19 (18 below, 2 equal) | 21 (17 below, 1 equal) | number changed | `reports/loso_w1/per_subject.csv` |
| 25 | P21 S015: ccnn against lda, "single-repeat cell far larger than 5 pp" | 29.66 vs 56.13 (−26.47) | 27.00 vs 56.13 (−29.13) | holds (number changed) | `reports/loso_w1/per_subject.csv` |
| 26 | P21 §4.5 train accuracy "about 75–77 %" (min 75.05, median 76.81) | 75.05 / 76.81 | min 77.59, median 79.44 | FLIPPED (wording no longer matches; superseded in the note) | `reports/loso_w1/folds.csv` |
| 27 | P21 §4.5 best epoch min / median / max | 6 / 26 / 69 | 7 / 30 / 78 | number changed | `reports/loso_w1/folds.csv` |
| 28 | P21 §4.5 S015 fold (best epoch, train, validation) | 13, 77.11 %, 74.85 % | 15, 79.36 %, 77.42 % | number changed | `reports/loso_w1/folds.csv` |
| 29 | P21 cohort-39 mean validation accuracy | 73.91 % | 75.41 % (the 2-tap mean is now 73.91 %) | FLIPPED (number changed) | `reports/loso_w1/summary.csv` |
| 30 | P21 cohort-5 seed range of the ccnn cohort mean (also README, progress report) | 85.36–86.58 | 83.45–85.88 | FLIPPED (range changed; the claim as worded is replaced) | `reports/loso_w1_s01-s05*/summary.csv` |
| 31 | P21 "not a before/after pair" and the P24 vs P20 draw (pseudo-online) | two draws, one seed | not applicable: P25 rerun is the canonical run; repeat identical in every non-Seconds column (`reports/pseudo_online/`) | holds (the P20 and P24 draws are superseded) | `reports/pseudo_online/`, P25 `06_verify.md` |
| 32 | P23: GNN per-seed cohort means (88.47, 88.11) above the ccnn seed mean | 86.04 | 84.88; margins 3.59 and 3.23 pp | holds | `reports/loso_w1_s01-s05*/summary.csv`, `reports/loso_gnn/summary.csv` |
| 33 | P23: ccnn 2-tap seed mean | 87.96 (88.31 / 87.06 / 88.52) | 86.59 (87.25 / 85.24 / 87.27) | number changed; GNN LOSO 2-tap 90.32 still above | `reports/loso_w1_s01-s05*/summary.csv` |
| 34 | P23 table row, ccnn LOSO seed means per subject and cohort | 71.18, 70.29, 92.84, 99.55, 96.32; 86.04 (r 1.22) | 68.82, 67.55, 92.08, 99.75, 96.22; 84.88 (r 2.43) | number changed | `reports/loso_w1_s01-s05*/summary.csv` |
| 35 | README, RESEARCH_LOG, report v2: "1-s networks, all differences below 3 pp, not distinguishable" | 91.25 / 92.08 / 89.69 | 90.53 / 92.08 / 89.69 | holds | `reports/nn_sweep/summary.csv` |
| 36 | README, RESEARCH_LOG, report v2: "six-class drop is mostly missed periods (30 of 32; 27 of 30 in S01 and S02)" | 30 of 32; 27 of 30 | 30 of 31; 28 of 30 in S01 and S02 (14 + 14) | holds in kind; numbers changed | `reports/pseudo_online/decisions_ccnn_{5class,6class}.csv` |
| 37 | README, RESEARCH_LOG, report v2, progress report: "of the 57 five-class false activations, 46 do not occur with six classes and none is new" | 57; 46; none new | 59; 50; one new six-class false activation (S01, onset 50.03 s) | FLIPPED ("none is new") | `reports/pseudo_online/decisions_ccnn_{5class,6class}.csv` |
| 38 | P24 decision counts: lost periods 32 = 30 missed + 2 wrong (S01); stimulus correct 177 / 151 | 32; 177 | 31 = 30 missed + 1 wrong (S01); stimulus correct 181 / 151; net 30 | number changed | `reports/pseudo_online/decisions_ccnn_{5class,6class}.csv` |
| 39 | P24: rest false activations with 5 classes max time 1.96875 s, 57 of 57 within 2 s; 6 classes 11 of 11 within 2 s | 1.96875 s; 57 of 57 | 2.4375 s, 58 of 59 within 2 s; 6 classes 1.46875 s, 10 of 10 | FLIPPED for five classes (within-2-s claim) | `reports/pseudo_online/decisions_ccnn_5class.csv` |
| 40 | P24 A-4: documents use the afcd417 rerun (88.50 / 75.50) | 88.50 / 75.50 | 90.50 / 75.50 | superseded (number changed) | `reports/pseudo_online/summary_ccnn_{5class,6class}.csv` |
| 41 | README, progress report, infographic: pseudo-online five classes 88.50 % / 28.5 % FA; six classes 75.50 %, 21.00 % missed, 5.5 % FA | 88.50; 28.5; 75.50; 21.00; 5.5 | 90.50; 29.5; 75.50; 22.00; 5.0 | number changed; six-class accuracy holds | `reports/pseudo_online/summary_ccnn_{5class,6class}.csv` |
| 42 | Not affected by the CCNN fix: window sweep, dynamic stopping (P20 4.4), cnn vs lda, window-sweep `cnn` cell, `simulate_dynamic_stopping` input | unchanged | not re-read by the scribe for values; the reviewer checked the consumers (`07_review.md`, "Consumers": the window-sweep `cnn` is compact_eegnet only; the dynamic-stopping input is `reports/window_sweep/predictions.csv`) | holds (by the reviewer's consumer check) | `reports/window_sweep/summary.csv` (not re-read) |

Flipped claims, in short: #8 (P6(a) now holds, fail → holds); #11 (six-class next-target p no longer below 0.05); #13 (five-class timing within 2 s); #26 (train-accuracy wording); #29 (validation mean); #30 (seed range); #37 ("none new"); #39 (five-class within-2-s claim). Holds with changed numbers: #4, #5, #12, #14, #15, #16, #18, #19, #24, #25, #27, #28, #33, #34, #36, #38, #40, #41. Holds: #1–3, #6, #7, #9, #10, #17, #20 (loose wording only), #21–23, #31, #32, #35, #42.

## Sources defects (verifier round 1)

- P22 `[23]` (line 5): resolved in a dated note to the repository history entry `32dbde8` (the commit that added the report), opened as history in this run. The `## Sources` list still ends at 19; the note states the resolution.
- P11 `mas/state/reference_access.log`: dated note gives the real path `mas/state/scratch/reference_access.log` (exists, git-ignored; 40 lines in 2026-10-24 to 2026-10-26).
- P21 `reports/window_sweep_colab`: dated note. The directory does not exist (checked 2026-10-30); no Colab run wrote it; the within reference is `reports/window_sweep_w1_all`.

## Numbers and shown commands

All numbers are copied from the CSVs listed above, read with `.venv/bin/python -I` (pandas 3.1.0). Arithmetic commands (the arithmetic actually used):
- NN sweep means and pairwise differences: `.venv/bin/python -I -c "import pandas as pd; n=pd.read_csv('reports/nn_sweep/summary.csv'); print(n.groupby('Method')[['Acc (%)','Train Acc (%)','Val Acc (%)','Best Epoch','ITR (bits/min)']].mean().round(2))"` → ccnn 90.53, 100.00, 92.41, 31.76, 72.16; compact_eegnet 92.08, 99.91, 93.10, 62.00, 74.53; eegnet 89.69, 98.89, 90.97, 84.72, 71.00. Pairwise: 90.53 − 89.69 = 0.84; 90.53 − 92.08 = −1.55; 92.08 − 89.69 = 2.39.
- Pseudo-online per subject and decompositions: pandas merge of `decisions_ccnn_5class.csv` and `decisions_ccnn_6class.csv` on (Subject, onset_sec), stimulus rows; counts correct5 & not correct6 = 31 (missed 30, wrong class 1); correct5 = 181, correct6 = 151; 200 stimulus periods each tag. Percentages: 31 / 200 = 15.5 %; 30 / 200 = 15.0 %; 1 / 200 = 0.5 %.
- Rest false activations: 59 (5 classes) and 10 (6 classes), linked to the following stimulus by onset − 5 s; predicted next target 15 of 59 (`scipy.stats.binomtest(15, 59, 0.2, alternative='greater')` → p = 0.1876) and 4 of 10 (p = 0.1209). Not false activation with six classes: 50 of 59; new with six classes: 1 (S01, 50.0312 s, pred 102).
- Maximum time_sec of false activations: 2.4375 (5 classes), 1.46875 (6 classes).
- LOSO cohort 5: seed means 85.88, 83.45, 85.32; `.venv/bin/python -I -c "print(round((85.88+83.45+85.32)/3,2), round(85.88-83.45,2))"` → 84.88, 2.43. 2-tap: `.venv/bin/python -I -c "print(round((87.25+85.24+87.27)/3,2))"` → 86.59. Per-subject three-seed means and ranges: S01 (65.29, 67.21, 73.97) → 68.82, range 8.68; S02 (73.45, 63.66, 65.53) → 67.55, 9.79; S03 (93.34, 91.38, 91.53) → 92.08, 1.96; S04 (99.70, 99.85, 99.70) → 99.75, 0.15; S05 (97.64, 95.14, 95.88) → 96.22, 2.50.
- ccnn − lda three-seed: `.venv/bin/python -I -c "print(round(84.88-87.61,2))"` → −2.73; old: `print(round(86.04-87.61,2))` → −1.57.
- P2 networks: `.venv/bin/python -I -c "print(round((65.29+93.34+99.70)/3,2), round((75.59+99.85+100.00)/3,2), round((65.29+93.34+99.70)/3-(75.59+99.85+100.00)/3,2))"` → 86.11, 91.81, −5.70.
- Cohort 39: `.venv/bin/python -I -c "print(round(72.08-72.54,2))"` → −0.46; ccnn above lda 21 of 39 from `reports/loso_w1/per_subject.csv` (ccnn and lda columns), 17 below, 1 equal.
- Cohort 39 folds: `reports/loso_w1/folds.csv`, method ccnn: best epoch min 7, median 30, max 78; train accuracy min 77.59, median 79.44; degenerate False 39 of 39.
- Colab estimate: `.venv/bin/python -I -c "s=5297.87; print(round(s/39,2), round(s/39*40,1), round(s/39*40/3600,2))"` → 135.84, 5433.7 s, 1.51 h.
- GPU budget of the fix round (quoted from the verifier's 05_run.md, not recomputed): 2.33 h, above `MAX_GPU_HOURS_PER_PHASE` 2.

## Open for the results review and the phase report (not the scribe's to decide)

- The R-13 reading (G-4: 13 of 19 cells inside the six-draw range, confirmed at ≥ 10) goes into `mas/state/reports/P25.md` (S-5). The RESEARCH_LOG P25 entry records only that the verifier made the check.
- S-6 (sources of P25.md: this review's R11 consultation of `fde4b5a:src/models/cnn/ccnn.py`; the deep-learning statement that the reference was not opened; 987742b as the fix commit, on the squash list) goes into P25.md.
- Claims #8, #11, #13, #26, #29, #30, #37 and #39 are flipped and are stated as such; the reviewer should check the wording of #20 (the "tie" reading), the weakest of the readings.
- Historical records were appended only. Any reader of the P20/P21/P24 tables must read the dated note at the end of each report to get the current values.

## Sources

1. DATA — `reports/nn_sweep/summary.csv` (P25 fix round 1 canonical; regenerated at 987742b). Used for: the 1 s cohort means, per-subject ccnn values, parameters, pairwise differences, Train ≥ Val check (`.venv/bin/python -I`, commands above).
2. DATA — `reports/pseudo_online/summary_ccnn_5class.csv`, `reports/pseudo_online/summary_ccnn_6class.csv`, `reports/pseudo_online/decisions_ccnn_5class.csv`, `reports/pseudo_online/decisions_ccnn_6class.csv` (P25 canonical). Used for: pseudo-online means, per-subject values, decompositions, false-activation and next-target counts, timing. Repeat identity is recorded by the verifier (`mas/state/phases/P25-final-audit/06_verify.md`, G-6).
3. DATA — `reports/loso_w1_s01-s05/summary.csv`, `reports/loso_w1_s01-s05_seed43/summary.csv`, `reports/loso_w1_s01-s05_seed44/summary.csv` (P25 canonical). Used for: cohort-5 ccnn seed means, 2-tap means, per-subject values, lda and eegnet comparison values.
4. DATA — `reports/loso_w1/summary.csv`, `reports/loso_w1/per_subject.csv`, `reports/loso_w1/folds.csv` (P25 canonical, 39 subjects). Used for: cohort-39 ccnn and lda means, per-subject comparison, fold statistics, Colab time estimate.
5. DATA — `mas/state/phases/P25-final-audit/06_verify.md` ("Fix round 1 rerun (CCNN)") and `05_run.md` ("Fix round 1 rerun"): old and new values table, GPU time 2.33 h, G-5 and G-6 results. Used for: cross-check of the new values and the overrun statement.
6. HANDOFF — `mas/state/phases/P25-final-audit/07_review.md`, "Fix round 1 audit (CCNN)", items S-1 to S-6, G-0 to G-7. Used for: the label, the scope and the rules of this handoff.
7. PLAN — `mas/state/phases/P20-detection-online/02_plan.md`, rule R-P5 (difference = cohort means differ by ≥ 3 pp and ≥ 4 of 5 subjects share the sign), as quoted in `mas/state/reports/P20.md` §5. Used for: the difference rule of the re-tests. R9 (per-subject reporting) applies to the per-subject values given above.
8. RULE — `mas/04_REFERENCE_RESULTS.md` R-8 (parameter counts 27,977 / 32,309) and `mas/03_ROADMAP.md` P20 task 3 (`[real | imag] / T`). Used for: the S-1 label.
9. DATA — `mas/state/reports/P20.md`, `P21.md`, `P23.md`, `P24.md` (pre-P25 values quoted for the "old" column; read as the record). Used for: the old values in the claim table.
10. GIT — repository history: `32dbde8` (P22 report commit; resolves citation [23] in `mas/state/reports/P22.md`). Opened as history metadata in this run.
11. DATA — `reports/pseudo_online/`, `reports/loso_w1_s01-s05/`, `reports/nn_sweep/` directory listing and CSV headers (existence and column names only). Used for: the column names in the commands above.
