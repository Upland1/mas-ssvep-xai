# P25 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (settled 1, 3, 4, 5; Run commands; Acceptance checks), 05_run.md, mas/state/decisions.md, the phase branch
Clean checkout: `mas/state/scratch/verify/P25` @ 6490a6c (detached worktree of `phase/P25-final-audit`)

Verdict: FAIL

Scope: acceptance 1, 2, 4 and 5 of `02_plan.md`. Acceptance 3 (every split guarded) and 6 (module diff) belong to `07_review.md`; acceptance 7 (privacy scan of the net diff) is the orchestrator's gate step. The only commands I ran are in `05_run.md`. Nothing was fixed or interpreted beyond comparing numbers with the criteria.

## Reasons (FAIL)

1. **R-8, Era-C sweep network CCNN: parameter counts differ from the reference and nothing explains it.** `mas/04_REFERENCE_RESULTS.md` R-8 lists CCNN 27,977 (7 channels) and 32,309 (8 channels), tolerance exact. The rebuild reports 14,817 (7 ch) and 17,285 (8 ch): `reports/nn_sweep/summary.csv` column `Params` (ccnn rows, e.g. S01 14817) and `mas/state/reports/P20.md` line 187. No P20 handoff, review, report or decisions row compares the CCNN count with R-8 (searched `mas/state/phases/P20-detection-online/`, `mas/state/reports/P20.md`, `mas/state/decisions.md`; the only CCNN count text is in `03_changes_deep-learning.md` line 46 and the test `tests/test_p20_networks.py::test_ccnn_shape_nfft_bins_and_params`, a closed form of the rebuild's own definition). The compact (28,133 / 28,229) and eegnet (2,389 at 8 channels) rows of the same R-8 table match. Acceptance 4 ("every R-x row within tolerance or explained") is not met for this row.
2. **R-13, descriptive tolerance +-0.05 exceeded in 19 split-half reliability cells and one pairwise count, not explained.** `reports/connectivity_comparison/coherence_split_half_reliability.csv` and `wpli_split_half_reliability.csv` against the R-13 tables: max abs difference 0.343 (coherence) and 0.498 (wPLI); cells above 0.05: 5 and 14 of 25 (`mas/state/scratch/p25_ref_table.out`). Coherence pairwise magnitude count 10 (final, `coherence_pairwise_tests.csv`) against R-13's 6. P14 labels R-13 qualitative and records D-4 as "unexplained" for the two non-positive coherence cells, the Fisher similarity 0.629 vs 0.54 and the magnitude count (decisions row P14 2026-10-26, `mas/state/reports/P14.md` sections 4.3-4.5); the cell-level reliability differences are not individually explained. If the reviewer rules R-13 qualitative (as P14 did), this reason falls and reason 1 stands alone.
3. **Sources report: one citation does not resolve and one cited path is wrong.** P22 `[23]` (header table line 5) has no entry (the Sources list ends at 19). P11 cites `mas/state/reference_access.log`; the file is `mas/state/scratch/reference_access.log`. These are documentation defects with no effect on any number; the full list is in section C.

Acceptance 1 (all phases passed, no open blocker) and acceptance 2 (suite on a clean checkout, rebuild evidence cited) are met; see below.

## Tests on the clean checkout

```bash
cd mas/state/scratch/verify/P25 && /home/upland1/Documents/UNIVERSIDAD/Research_AI_EEG/02_data/Datos/mas-ssvep-eeg-xai/.venv/bin/python -m pytest tests/ -q
```

Counts from the progress characters of `mas/state/scratch/verify/P25_pytest.log` (no totals line is printed because `pytest.ini` has `addopts = -q`; `05_run.md` Anomalies 1): `1563 passed, 6 skipped, 0 failed, 0 errors` (1569 collected), wall 14 min 50 s (`2026-10-29T20:55:17-06:00` to `2026-10-29T21:10:07-06:00`, timestamps in the log). Worktree clean after the run (`git status --short` empty).

## Acceptance

| Criterion (verbatim) | Re-run command | Obtained | Reference (R-x) | Tolerance | Met? | Log |
|---|---|---|---|---|---|---|
| 1. Every phase P00-P24 is `passed` in `mas/state/phase_status.yaml`, and no blocker is open. | `grep -c "status: passed" mas/state/phase_status.yaml`; `grep -n Status mas/state/blockers/*` | 25 phases `passed` (P00-P24, dates 2026-10-24 to 2026-10-29); P25 `in_progress` (this phase). Blockers B001, B002, B004, B005 `resolved`; B003 `RESOLVED 2026-10-28`; B006 `RESOLVED 2026-10-26`; B007 `RESOLVED 2026-10-27`; none open | | | yes | `mas/state/phase_status.yaml`, `mas/state/blockers/` |
| 2. The suite passes on a clean checkout. The rebuild evidence is cited. | command above; `git diff --stat bb9c091 main -- src scripts configs Makefile` | suite: 1563 passed, 6 skipped, 0 failed. Diff: `scripts/benchmarks/pseudo_online.py | 3 +++`, `1 file changed, 3 insertions(+)`, the only change since the P24 `make all` clone. Evidence: `make all` exit 0 (`DONE rc=0 2026-10-29T17:41:42`, clone at `bb9c0913624238310b8b7f6d7b543c18e495b624`); 245 CSVs EXACT, 13 BYTES_EQ, 30 NO_MAIN, 22 DIFF, 6 BYTES_DIFF, 3 ROWS of 319 compared (`mas/state/scratch/p24_make/compare_reports.csv`, status column); P24 `06_verify.md` Verdict PASS after fix round 2 (pseudo-online rerun at afcd417: `mas/state/scratch/p24_fix2/exits.txt`, `tables.md`; P24 A-1..A-6 accepted in the decisions row 2026-10-29 P24 results review; `mas/state/reports/P24.md`) | | | yes | `mas/state/scratch/verify/P25_pytest.log`, `mas/state/scratch/p24_make/` |
| 4. Every R-x row is within tolerance or explained. | `.venv/bin/python mas/state/scratch/p25_ref_table.py` | 17 of 20 sub-rows W or W with cited E; 3 sub-rows with unexplained items (section A) | R-1..R-16 | per `mas/04_REFERENCE_RESULTS.md` | **no** (reasons 1, 2) | `mas/state/scratch/p25_ref_table.out` |
| 5. Autonomy and sources reports are complete. | sections B and C | complete; B3 share 21 of 25 = 84.0 %; sources: 25 of 25 sections present, 1 unresolved citation, 1 wrong path | | | yes (reports complete); defects listed as reason 3 | `mas/state/scratch/reference_access.log` |

Settled 1 recheck: `git diff --stat bb9c091 main -- src scripts configs Makefile` prints only `scripts/benchmarks/pseudo_online.py | 3 +++`. Statement in `02_plan.md` settled 1 confirmed. No new rebuild was run.

## Numbers in the handoffs vs logs

Every number in `05_run.md` and in this file comes from `mas/state/scratch/verify/P25_pytest.log`, `mas/state/scratch/p25_ref_table.out`, `mas/state/scratch/p24_make/compare_reports.csv` (`.venv/bin/python -c "import pandas as pd; print(pd.read_csv('mas/state/scratch/p24_make/compare_reports.csv').status.value_counts())"` -> EXACT 245, NO_MAIN 30, DIFF 22, BYTES_EQ 13, BYTES_DIFF 6, ROWS 3), or a shown command. The reference values typed into `p25_ref_table.py` were copied from `mas/04_REFERENCE_RESULTS.md` (R-9b, R-12, R-13, R-14, R-15 tables).

## A. Reference comparison (settled 3)

Rerun: `.venv/bin/python mas/state/scratch/p25_ref_table.py`. Status: W = within tolerance, E = explained deviation (decisions row, blocker or reviewer-signed phase deviation), U = unexplained. `mas/04_REFERENCE_RESULTS.md` has no section headed R-10 (R-9 is followed by R-11).

| R-x | Target (reference file) | Obtained and path | Tolerance | Status |
|---|---|---|---|---|
| R-1 legacy counts | 200/199/200/198/200 stimulus windows; 320/318/317/317/320 all windows; graph datasets 200/196/197/197/200 | clean plus rejected from `reports/n_subjects_benchmark.csv`: 200/199/200/198/200 (script line "R-1 stimulus windows ... equal True"); `reports/logs/P02/run_preprocessing_20261024_171759.log`: n = 320 / 318 / 317 windows for S01-S03; graph clean windows in `reports/connectivity_gate_benchmark.meta.txt`: 200/196/197/197/200 | exact | W |
| R-2 early hybrid models | no numeric values preserved | no target; P04 records its own (`mas/state/reports/P04.md`) | none | W (no target) |
| R-3 S03 flagship, leaky | 90.36 / 95.43, 197 clean, 3 rejected | `reports/flagship_S03.csv`, m=1 row: 197, 3, 90.36, 95.43 | classical +-1.5 pp | W (exact). Qualitative "perfect 24 Hz precision" is 0.9750 (one window): P05 D-1, accepted |
| R-4 ablation S03, leaky | p 55/45/25/25/20; 1.0 s 90.36/87.31/86.29/87.82/84.77; 2.0 s 95.43/94.92/94.42/93.40/93.40 | `reports/legacy_leaky/feature_selection_ablation_S03.csv`: first four rows delta 0.00 pp, p exact; SFS row 89.85 / 95.94 (delta +5.08 / +2.54 pp) | +-1.5 pp | W for 4 rows. E for SFS: P06 D-1 (the original has no SFS on any branch, `mas/state/reports/P06.md` section 8), verifier restated PASS (`d905194`) |
| R-5 five-subject cohort, leaky | 64.50/75.50, 66.33/71.94, 90.36/95.43, 98.98/98.48, 96.50/96.50; mean 83.33/87.57 | `reports/five_subjects_benchmark.csv`: max abs difference over the 12 cells 0.0 | +-1.5 pp, mean +-1.0 | W (exact) |
| R-6 flagship, leak-free | 61.00/67.50, 56.12/61.73, 86.80/90.36, 97.46/97.97, 95.00/95.50; mean 79.28/82.61; clean/rejected 200/0, 196/3, 197/3, 197/1, 200/0 | `reports/n_subjects_benchmark.csv`: max abs difference over the 12 cells 0.0; counts identical | +-1.5 pp, mean +-1.0 | W (exact) |
| R-7 deep learning, aug ON, 1.0 s | ShallowConvNet 56.50/35.20/89.34/98.98/98.50; EEGNet 34.50/26.02/79.19/99.49/92.00; Compact-CNN 27.50/19.39/62.94/97.97/62.00 | `reports/augmentation_ab_<model>.csv`, ON 1.0 s. Obtained minus reference (pp): ShallowConvNet -1.00, +0.51, -1.02, +0.51, -1.00; EEGNet -2.00, +3.06, -14.72, +0.51, -2.00; Compact-CNN -4.00, -0.51, -5.07, +0.51, -7.50 | network +-5 pp per subject | 12 of 15 cells W. E for EEGNet S03, Compact-CNN S03 and S05: P11 D-4 (three-base training-seed spread, `mas/state/reports/P11.md` sections 4.6-4.8, `reports/diagnostics/p11_seed_spread_<model>.csv`) |
| R-8 parameter counts | EEGNet 2,349; ShallowConvNet 14,485; Compact-CNN 56,021; fusion CNN 10,005; GNN 5,150 / 5,534 | `reports/network_parameter_counts.csv`: 2349, 14485, 56021; fusion 10005 (`reports/logs/P04/param_count_20261024T223559.log`; `tests/test_p04_early_models_known_answer.py::test_fusion_cnn_params_10005_no_conv_bias`); GNN 5150 / 5534 (`reports/gnn_benchmark.meta.txt`) | exact | W |
| R-8 Era-C sweep networks | `compact` 28,133 (7 ch) / 28,229 (8 ch); `eegnet` 2,389 (8 ch); CCNN 27,977 (7 ch) / 32,309 (8 ch) | `reports/nn_sweep/summary.csv` Params: compact_eegnet 28133, eegnet 2373 (7 ch); `tests/test_p20_networks.py` lines 74-78: 28,229 and 2,389 at 8 ch; **CCNN 14,817 (7 ch), 17,285 (8 ch)** (`reports/nn_sweep/summary.csv`; `mas/state/reports/P20.md` line 187) | exact | W for compact and eegnet. **U for CCNN** (reason 1) |
| R-9a augmentation A/B, leaky | EEGNet +3.00 pp (first run) to +7.34 pp (last) at 1.0 s | `reports/legacy_leaky/augmentation_ab_eegnet.csv` Mean row: +3.11 (1.0 s), +2.90 (2.0 s) | network mean +-3 pp | W (inside the recorded range, lower edge; P10 section 5) |
| R-9b augmentation A/B, leak-free | mean deltas EEGNet +2.01/+1.22, Compact-CNN +17.16/+16.46, ShallowConvNet +2.53/+2.40, plus 60 accuracy cells | `reports/augmentation_ab_<model>.csv` Mean deltas: EEGNet +4.85/+4.65; Compact-CNN +13.56/+15.07; ShallowConvNet +2.63/+2.83. Accuracy cells outside bands at seed 42 (script lines "R-7/9b ... out-of-band cells"): EEGNet 8, Compact-CNN 4, ShallowConvNet 0; with the two out-of-band delta cells (EEGNet 2.0 s, Compact-CNN 1.0 s) this is the 14 of P11 | +-5 pp subject, +-3 pp mean | E: 13 of 14 by P11 D-4; 1 (Compact-CNN S03 2.0 s ON, 65.48 vs 71.07) by B006 / P11 D-8, RESOLVED by Sebastian 2026-10-26 (`mas/state/blockers/B006-p11-compact-cnn-s03-2s-on.md`) |
| R-11 coherence bug fix | per-window independent noise 0.32-0.35; concatenated 0.01-0.02; coupled 0.98-0.99; S03/S04 baseline 0.68-0.73 before, 0.59-0.66 after; 24 and 20 Hz +0.11 to +0.25 | `reports/connectivity/coherence_bias_demo.csv`: 0.3373 / 0.0180 / 0.9814 (coupled concatenated 0.9824); `coherence_S03_summary.csv`: before 0.6836, after 0.5871; `coherence_S04_summary.csv`: 0.7291 / 0.6589; S03 24 and 20 Hz +0.2494 / +0.2511; S04 +0.1281 / +0.1105 | descriptive +-0.05 | W. S03 after (0.5871) and S03 20 Hz (0.2511) are 0.0029 and 0.0011 beyond the bare edges, inside +-0.05 (P12 D-1) |
| R-12 connectivity statistics | FDR totals coherence 0/0/65/51/15, wPLI 0/3/38/33/18; 24 Hz significant in S03-S05; global p table | `reports/connectivity_cohort_summary.csv` (200 trial permutations): coherence 0/0/64/49/12 (differences 0, 0, 1, 2, 3); wPLI 4/0/42/28/5 (differences 4, 3, 4, 5, 13); 24 Hz p coherence 1.0/1.0/0.005/0.005/0.005, wPLI 0.995/0.318/0.005/0.005/0.040; one cell crosses 0.05: S03 wPLI 15 Hz (0.04975 vs 0.065) | +-25 % or +-5 edges; no 24 Hz effect/no-effect switch | W for 9 of 10 totals and the 24 Hz pattern. E for S05 wPLI (5 vs 18, window 13-23): P13 D-1, results review Round 2 APPROVE (`mas/state/reports/P13.md` section 4.7; DIAG-A2 in `reports/connectivity_cohort_summary_diagA2_rs<B>.csv`) |
| R-13 global mean delta | tables in reference | `reports/connectivity_comparison/{coherence,wpli}_global_delta.csv`: max abs difference 0.0005 for both; 0 cells above 0.05 | +-0.05 | W |
| R-13 SNR and alpha change | tables in reference | `reports/connectivity_comparison/power_confound_table.csv`: max abs difference 0.004 dB (SNR), 0.005 dB (alpha) | +-0.5 dB | W |
| R-13 split-half reliability | tables in reference | `{coherence,wpli}_split_half_reliability.csv`: max abs difference 0.343 (coherence), 0.498 (wPLI); cells above 0.05: 5 (coherence) and 14 (wPLI) of 25 each | +-0.05 | **U** at cell level (reason 2) |
| R-13 pairwise counts | coherence 6 magnitude / 1 pattern; wPLI 6 / 2 | `*_pairwise_tests.csv` (50 rows each), p < 0.05: coherence 10 / 1; wPLI 6 / 2 | descriptive | coherence magnitude 10 vs 6: **U** (P14 D-4, "reported, not explained"); the other three W |
| R-14 connectivity gate | k=0 means (Mean column) Ec 48.6, Ep 38.8, Ec+Ep 50.6, N 65.3, F 68.5, Base 73.8, Base+Ep 73.5, Base+Ec+Ep 74.9, Base+Ec 77.6 | `reports/connectivity_gate_benchmark.csv`, mean over repeats, k=0: 48.6, 38.8, 50.6, 65.3, 68.6, 73.8, 73.4, 74.9, 77.6; max abs difference over all 45 subject cells 0.058 pp | +-1.5 pp | W |
| R-15 within-subject GNN | S02, S03, S05, two variants, 1.0 s / 2.0 s / train | `reports/gnn_benchmark.csv`, mean of 3 repeats. Obtained minus reference (pp), nodes+F: S02 -4.4 / -9.0 / +19.0, S03 -1.0 / +0.4 / +8.5, S05 -0.5 / -0.8 / +3.7; nodes+coh+F: S02 -1.0 / -0.3 / +20.3, S03 -1.0 / +0.7 / +8.3, S05 +0.5 / -0.1 / +3.4 | network +-5 pp per subject | accuracy cells W except nodes+F S02 2.0 s (-9.0); train-accuracy gaps outside. E: B007 (`mas/state/blockers/B007-p15-gnn-s02-2s-systematic.md`, RESOLVED 2026-10-27, accepted as documented deviations) |
| R-16 Era C | no numeric target; direction and plausibility | checked by the P16-P23 reviews (`mas/state/reports/P16.md` to `P23.md`); P24 A-5 (p19 clone runtime 10.2 vs 2.5 min) is a runtime observation, unexplained, no effect on a result (settled 7) | none | W (no target) |

Arithmetic: `.venv/bin/python -I -c "print(round(63.21-58.36,2), round(100*129/197,2), max(0.25*18,5))"` -> `4.85 65.48 5.0` (R-12 S05 wPLI window 18 +- 5 = 13-23).

## B. Autonomy report (settled 4)

Log: `mas/state/scratch/reference_access.log`, 56 lines when last read. Phase reports section 8 (P00-P24) were read for every phase; the handoff consultation sections were read for the phases with entries.

### B1. Consultations (a file or listing under the answer-key repository was opened)

| Phase | Agent | Date | Trigger | Log lines | File opened |
|---|---|---|---|---|---|
| none (pre-P04) | main session | 2026-10-24 21:27:47-48 | README read, settled as pre-P04 in `mas/state/decisions.md`; not attributed to a phase (P04 report section 8) | 3-4 | yes: `README.md` on `main` |
| P05 | ml-engineer | 2026-10-24 23:48:50-23:49:50 | Round 1 verifier FAIL (`ce30892`): R-3 2.0 s 95.94 vs 95.43, 24 Hz precision; 4 rows | 6-14 | yes: `scripts/evaluate_confusion_matrix.py`, `src/features/fbcca_extraction.py`, `fbcsp_extraction.py`, `psd_extraction.py`, `src/preprocessing/quality_check.py`, `scripts/benchmark_harmonic_fbcca.py`, grep of `scripts/benchmark_cross_validation.py` (`69873ea` and `main`). Reviewer CONCERN: first access 5 s after the FAIL record (P05 section 8) |
| P06 | ml-engineer | 2026-10-25 04:48:01-46 | Round 1 verifier FAIL on the SFS row (`b695b9a`) after diagnostics `348f3a4`; 6 rows | 15-26 | yes: `src/features/feature_selection.py`, `scripts/benchmarks/benchmark_feature_selection.py`, `benchmark_5_subjects.py` at `277ddab`; history and README greps; branch `origin/feature/feature-selection-and-eegnet` |
| P11 | deep-learning | 2026-10-26 12:05:00-15 | Round 2: R-9b missed beyond tolerance after one investigation round that found no bug; 1 row | 29-31 | yes: `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py` lines 78-135, 160-180 and grep hits |
| P15 | deep-learning | 2026-10-26 23:14:29-32 | own implementation failed the R-8 count (5,278 / 5,662 vs 5,150 / 5,534); 1 row | 32-33 | yes: `src/models/graph/connectivity_gnn.py` (whole 73-line file displayed; only `bias=False` adopted) |
| P15 | scientific-reviewer | 2026-10-26 23:44:31-23:45:50, 23:53:40 | verification of a finished, passing implementation (train-accuracy question); P15 D-5 | 34-39, 40 | yes: `connectivity_gnn.py`, `scripts/connectivity/graph_modeling/benchmark_gnn.py` lines 30-105, `src/features/connectivity/graph_inputs.py` lines 41-70; line 40 is a `git grep` of the class names |
| P25 | scientific-reviewer | 2026-10-29 20:58:14-20:59:52 | task 4, module diff against three branches: R11 consultation to verify finished work | 45-56 (12 lines, `git show` / `ls-tree` through `git -C`) | yes, per the log (branches `main` and `test/GNN-testing-LOSO` seen); the reviewer lists the details in `07_review.md`; the verifier opened nothing |

Line 41 (verifier, 2026-10-28T07:06:19, P19): `ls -la` of the answer-key directory with `head -3`, directory metadata only; disclosed as P19 D-2 and not counted as a consultation there. Listed here because the command touches the folder; no file inside was opened.

### B2. Log lines that only name the folder in an exclusion or search argument (not consultations)

| Line | Agent | Date | Phase | Command nature |
|---|---|---|---|---|
| 1 | verifier | 2026-10-24T15:07:09 | P00 | tracked-files privacy check whose pattern names the folder |
| 2 | verifier | 2026-10-24T16:27:04 | P01 | same type of check |
| 5 | scribe | 2026-10-24T22:44:39 | P04 | privacy grep of the P04 report |
| 27 | scientific-reviewer | 2026-10-26T00:25:42 | P09 | privacy grep and name-only diff filter |
| 28 | scientific-reviewer | 2026-10-26T10:36:35 | P11 | privacy grep of `07_review.md` |
| 42 | scribe | 2026-10-28T07:41:21 | P19 | privacy scan of the staged diff and path count |
| 43 | scribe | 2026-10-29T20:44:58 | P24 | `find` whose argument excludes the folder (P24 report section 8) |
| 44 | verifier | 2026-10-29T20:57:31 | P25 | grep of the phase reports for this report (pattern text only) |

### B3. Phases without any consultation

Phases with an attributed consultation (B1): P05, P06, P11, P15. Command: `.venv/bin/python -I -c "c={'P05','P06','P11','P15'}; n=25; print(len(c), n-len(c), round(100*(n-len(c))/n,1))"` -> `4 21 84.0`. Share of P00-P24 completed without any consultation: 21 of 25 = 84.0 %. Counting the unattributed pre-P04 README read against P04: 20 of 25 = 80.0 %. Counting P25 (26 phases, its consultation is logged): 21 of 26 = 80.8 % (`.venv/bin/python -I -c "print(round(100*21/26,1))"` -> `80.8`).

Handoff cross-check: handoffs listing consultation rows are P05 `03_changes_ml-engineer.md`, P06 `03_changes_ml-engineer.md`, P11 `03_changes_deep-learning.md`, P15 `03_changes_deep-learning.md` and `07_review.md`. All other handoffs and phase reports P00-P24 state none. Every opened-file access in the log up to line 44 matches a listed consultation; no unlisted access found.

## C. Sources report (settled 5)

Command: `.venv/bin/python mas/state/scratch/p25_sources_check.py` (heuristic: bracket groups of integers in the body against `N.` entries of the Sources section; backtick tokens starting with a repository root checked with `os.path.exists`). Each flagged item was opened.

| Check | Result |
|---|---|
| Sources section present | 25 of 25 (P00-P24) |
| Numbered citations resolve | All resolve except P22 `[23]` (header table, line 5: "This report is committed as `docs: P22 report` [23]"; the P22 Sources list ends at entry 19). Numbers flagged for P04, P05, P06, P07, P08, P09, P10, P11, P13, P18, P19, P20, P23 are arithmetic lists, array indices or table cells inside code or backticks, not citations |
| Cited repository paths exist | Missing paths by kind. (i) git-ignored scratch files removed at phase close: P00 1, P02 1, P04 2, P05 6, P07 2, P15 1, P16 2, P19 3, P24 3 (P05 also cites the removed `mas/state/scratch/r1_outputs/` folder). (ii) paths of the original repository quoted as answers, not of this repository: P06 `scripts/benchmarks/benchmark_5_subjects.py`, `scripts/benchmarks/benchmark_feature_selection.py`, `src/features/feature_selection.py` at `277ddab`. (iii) range placeholders `data/processed_continuous/S01..S05/` (P16, P17, P19). (iv) test names with `::` whose function exists (P16 `test_responders_real_benchmark_if_present`; P20 `test_eegnet_regression_after_refactor`, `test_off_path_identical_to_p09`, `test_causal_filter_chunked_equals_one_pass_and_is_causal`; found by `grep -n` under `tests/`). (v) real defects: P11 cites `mas/state/reference_access.log` (the file is `mas/state/scratch/reference_access.log`); P21 cites `reports/window_sweep_colab` (not present; the name of a Colab output folder in a notebook note) |

## Sources spot-check

Opened in this run: `mas/04_REFERENCE_RESULTS.md` (all of R-1..R-16), `mas/state/reports/P05.md`, `P06.md`, `P11.md` section 8 and 4.5, `P13.md` sections 4.6-4.7, `P14.md` sections 4.3-4.5, `P15.md` section 8, `P20.md` line 187, `P22.md`, `mas/state/blockers/B007-*.md`, `mas/state/phases/P24-documentation/06_verify.md` and `05_run.md`. P11 section 4.5 values agree with `reports/augmentation_ab_<model>.csv`; P13 section 4.6 totals (S01 4, S02 0, S03 42, S04 28, S05 5) agree with `reports/connectivity_cohort_summary.csv`; P20 line 187 agrees with `reports/nn_sweep/summary.csv`.

## Reference consultations check

Each consultation in B1 has an R11 trigger recorded in the phase report (after an implementation, a failing test or a verifier FAIL), except the unattributed pre-P04 README read (settled in `decisions.md`). The P05 sequencing CONCERN (access 5 s after the FAIL record) is on record in P05 section 8. No unlisted opened-file access in log lines 1-44. Lines 45-56 are the reviewer's P25 task 4, announced as an R11 verification consultation in `02_plan.md` settled 6; the reviewer's own listing is in `07_review.md`.

## Not covered

Acceptance 3 and 6 (leakage audit, module diff): reviewer. Acceptance 7 (privacy scan of the net diff): orchestrator. The six skipped tests were not itemised (`-rs` was not given and the suite was not rerun).
