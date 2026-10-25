# Research log

The research history of the rebuild, phase by phase: each stage, its numbers,
each discovered problem, each fix and its before/after (filled by the scribe).

## P00 — Bootstrap and data intake

Full report: `mas/state/reports/P00.md`. Date of all steps: 2026-10-24.

**Aim.** Set up the repository and make first contact with the recordings: reproduce the measured inventory of `mas/01_DATA_SPEC.md` §4 from the files with a script that fails loudly on any deviation.

**Scope.** P00 reproduced **10 of the 23 §4 rows**, not the full §4 inventory. The delivered raw data are `OO` and `mOO` of S01–S05. The 13 absent rows are S01 `C` and `mC`; S02 `C`, `mC` and `online_C`; S03 `C`, `mC` and `cb_mas_mcb`; S04 `C` and `mC`; S05 `C`, `mC` and `online_OO` (blocker `mas/state/blockers/B005-inventory-10-of-23-files.md`; `mas/state/phases/P00-bootstrap/06_verify.md`).

**Build.** The environment is a `.venv` (Python 3.12.3) with the full `requirements.txt`. The skeleton of `02_REQUIREMENTS.md` §2, `Makefile`, `pytest.ini` and the two logs were created, and `scripts/exploration/inventory_raw.py` reads the `.ebr` header and the MARK, TIMESTAMP and EEG rows through a memory map. Beyond the specified checks (fs, channel list, 40 trials of 8 per target) it fails on unreadable files, channel-count mismatch, trailing bytes and non-integer MARK values (`03_changes_data-engineer.md`).

**Tests and first review.** The synthetic-tester wrote 58 known-answer tests on synthetic `.ebr` files (suite `60 passed in 2.42s`, `04_tests.md`); a naive onset counter gives 120 stim events instead of 40 on plateau pulses, so the plateau test guards the onset rule. The pre-run audit Round 1 returned FAIL: the unanchored `reports/` pattern in `.gitignore` also ignored `mas/state/reports/`, where phase reports are committed (`07_review.md`). Fix: `/outputs/`, `/reports/`, `/baselines/` anchored at the root (`9d5c5a9`); the subject regex now uses `fullmatch`, with three further tests (suite `63 passed in 3.67s`). Round 2 returned PASS.

**Run.** `.venv/bin/python scripts/exploration/inventory_raw.py` at `042e1b2f5b727e310777b41f600e84abf940b97a`, exit 0, `10 files, 5 subjects, 0 deviations` (`reports/logs/P00/inventory_raw_20261024_141334.log`, `reports/raw_inventory.csv`). All 10 delivered rows match §4: samples, stim events and session start exactly, duration to 0.1 s, p99 within 0.043 µV (`07_review.md`). Per row, all with 40 stim events, fs 256.0 and 11 channels (`reports/raw_inventory.csv`):

| Subject | File | Samples | p99 abs EEG (µV) |
|---|---|---|---|
| S01 | OO | 154904 | 785.129522094725 |
| S01 | mOO | 154912 | 187.5906661987305 |
| S02 | OO | 154912 | 40.06002101898197 |
| S02 | mOO | 154912 | 37.48278903961185 |
| S03 | OO | 154896 | 331.4067117309576 |
| S03 | mOO | 154896 | 1013.7993548584035 |
| S04 | OO | 154896 | 481.5410757446289 |
| S04 | mOO | 154912 | 24.943459510803237 |
| S05 | OO | 154912 | 24.585167598724375 |
| S05 | mOO | 154904 | 23.802621860504146 |

**Deviation.** Because 13 of the 23 §4 rows were not delivered, Sebastian chose option B of B005 (accept the 10-file inventory). The scientific reviewer signed the deviation on the conditions that this log and the phase report state "10 of 23 §4 rows" and name the absent ones, and that the inventory be re-run and checked against §4 before any phase uses the `C`, `mC`, online or joined recordings if they arrive (`07_review.md`, `mas/state/decisions.md`). The verifier passed the phase (`06_verify.md`) and the reviewer approved the results (`07_review.md`).

**Findings for later phases.** The p99 pooled over the 8 EEG channels reproduces §4 on 10/10 files; session start is truncated to the minute (rounding is not excluded by the data). The raw p99 ranges from 23.8 to 1013.8 µV across the delivered files, in line with §4's remark that quality decisions must use filtered signals. No reference consultation was made. Next: P01.

## P01 — EBR parser and configuration v1

Full report: `mas/state/reports/P01.md`. Date of all steps: 2026-10-24.

**Aim.** Replace the P00 private reader with a parser written from `mas/01_DATA_SPEC.md` §2, add configuration v1 (PO7 hard-excluded, legacy, PF-05) and the legacy zero-phase Butterworth band-pass, and show that the parser reproduces the P00 inventory.

**Scope.** As in P00, acceptance was applied to the **10 of 23 §4 rows** delivered (`OO`, `mOO` of S01–S05; blocker B005). The 13 absent rows are unchanged.

**Build.** `src/io/ebr_parser.py` (`load_ebr_file(path, strict=True)` plus four name-based helpers), `configs/pipeline_config.yaml` v1, `src/preprocessing/signal/filters.py` (`apply_iir_bandpass`, `fs` required), and the inventory script switched to the parser (`03_changes_data-engineer.md`).

**Tests and review.** Round 1 suite `198 passed in 3.94s` (`04_tests.md`). The pre-run audit Round 1 returned FAIL: the planned run read with `strict=False` only, so the default mode that P02 will call was never tried on real headers, and a committed handoff named a local tool file (`07_review.md`). Fixes: an inventory `--strict` flag, exact `data_type` matching, a strict repeated-line check, a plan amendment with a strict run, and a reworded assignment. Final suite `248 passed in 4.92s` (`04_tests.md` Round 2); Round 2 returned PASS.

**Run.** At `477550967a7d04aab2ceb217d47c59735c992dd0`, default and `--strict` inventories both printed `10 files, 5 subjects, 0 deviations` with exit 0, `cmp` against `reports/raw_inventory.csv` was silent for both, and the sha256 was `e134a372b164bf42b4911c56ca98be47742f45442f0bad37f9923ed4d1b16c14` before and after (`mas/state/phases/P01-ebr-parser/05_run.md`; `reports/logs/P01/inventory_raw_default_20261024T162513.log`, `reports/logs/P01/inventory_raw_strict_20261024T162517.log`). The verifier reproduced both from a clean checkout (`248 passed in 7.26s`, `06_verify.md`).

**Deviations.** Seven accepted deviations (strict default and its extra checks, extra public parser names, stricter helper errors, exact `data_type`, header count defaults, whole-file reads with `--strict` flag, plan amendment); see `mas/state/decisions.md` and the report, section 9.

**Findings for later phases.** All 10 delivered headers pass the strict checks, so P02 can call `load_ebr_file(path)` with its default. Strict mode also rejects a repeated unknown header key; if a future file trips it, the stop/blocker rule applies. Config v1 keeps the 7-channel montage until P07. No reference consultation was made (the two access-log lines are logged privacy greps, not reads). Next: P02.

## P02 — Legacy preprocessing and windowing

Full report: `mas/state/reports/P02.md`. Date of all steps: 2026-10-24.

**Aim.** Rebuild the first data-bearing step of the original project: broadband-filter each continuous `OO` recording (1–60 Hz, order 4), cut condition windows (201, 202, 101–105), apply the legacy Vpp/std gate, and save `X_time_windows (n, 7, 256)`, `X_psd_features (n, 217)` and `y_labels` per subject (roadmap P02; `00_assignment.md`).

**Build.** `src/preprocessing/signal/quality_check.py`, `src/features/ssvep/psd_extraction.py`, `src/visualization/signal_plots.py`, `scripts/preprocessing/run_preprocessing.py` and a `make preprocess` target (`03_changes_signal-processing.md`, `03_changes_data-engineer.md`). The gate passes `vpp_min=0.5` explicitly (PF-07). Windows and periodogram use the header fs 256 Hz: 217 = 7 × 31 bins needs it, so PF-04's `fs = 250` is not reproduced here and enters with the P04/P05 extractors (decisions.md).

**Tests and review.** Final suite `283 passed in 12.37s` (`04_tests.md`); 23 known-answer tests, with variants that fail on PF-07, PF-13, PF-09, PF-04, R3 and R6. Pre-run audit PASS, no required fixes (`07_review.md`).

**Run.** `python -m scripts.preprocessing.run_preprocessing --all` at `adbc5a01f098daf7eefb214174777a0f27c90797`: exit 0, 5 s. Log line: `Cohort: 5 subjects processed, 0 skipped (none); 1592 windows; gated 1600, accepted 1592, rejected 8, skipped segments 0` (`reports/logs/P02/run_preprocessing_20261024_171759.log`; `05_run.md`). The verifier re-ran from a clean checkout (`283 passed in 11.00s`), all 18 arrays bit-identical (`06_verify.md`).

**Result.** R-1 reproduced exactly: n 320 / 318 / 317 / 317 / 320 and stimulus windows 200 / 199 / 200 / 198 / 200 for S01–S05 (data source: legacy, `data/processed/<S>/`, session `OO`). All 8 losses are `vpp_high` rejections (O2 in S02 and S04, PO8 in S03); none is `vpp_low`. Figure criterion: S04 and S05 5/5; S03 4/5, the 8.57 Hz target is partial (plateau at bins 8–9 in the 7-channel mean, local maximum over PO8, O1, Oz, O2 with ratio 1.918); the reviewer approved with the partial recorded (`07_review.md`).

**Finding.** 178 of the 199 saved 202 windows are bit-identical to the second 201 sub-window of their trial and the other 21 are shifted by 8 samples (PF-13 on real data). 201 and 202 must never be used together as independent samples or in different CV groups.

**Deviations and legacy.** PO7 excluded (config v1) and the per-script gate (R5 LEGACY by design) are the legacy behaviours; builder deviations accepted (extra kwargs and record keys, extra figure and CLI flags). `team.yaml` P02 flags corrected to `[]`.

**Findings for later phases.** P03: S01 101 (24 Hz) shows a 10 Hz peak and S01/S02 show no clear SSVEP peaks. P07: `summarize_window_quality` must see ungated windows, stale outputs on skipped subjects need handling, PF-07 is reproduced with `--vpp-min 5.0`. P16: check S03 first-trial PO8 rejections for a filter start-up transient. No reference consultation was made (the two access-log lines are privacy greps from earlier phases). Next: P03.

## P03 — Exploration and signal verification

Full report: `mas/state/reports/P03.md`. Date of all steps: 2026-10-24.

**Aim.** Before any model, show per subject and per class whether the legacy stimulus windows carry spectral peaks at the stimulation frequencies (roadmap P03): occipital (`O1, Oz, O2`, by name) `|rfft|²` per class, 5–35 Hz, and a PSD/quality-mask exploration script. Data source: legacy, `data/processed/<S>/` from P02, session `OO`.

**Build.** `scripts/exploration/diagnose_occipital_spectra.py`, `scripts/exploration/visualize_data.py`, `src/features/ssvep/spectral_power.py`, two plot functions and a `make explore` target (`03_changes_signal-processing.md`). Legacy fs 250 is the default and labelled; `--fs 256` gives the header axis.

**Tests and review.** Final suite `311 passed in 20.72s` (`04_tests.md`), verifier `311 passed in 22.46s` on a clean checkout (`06_verify.md`). The pre-run audit Round 1 returned FAIL: the printed target-bin power read the bin nearest f0 on the relabelled fs-250 axis, which is the wrong bin for 24 Hz (bin 25 instead of 24), 2·15 Hz (31 vs 30) and 2·8.57 Hz (18 vs 17). It would have recorded a false "no 24 Hz response" (S03 101 ×0.52 median at the nearest-labelled bin vs ×6.09 at the response bin, `reports/logs/P03/diagnose_occipital_spectra_fs250_20261024T180123.log`). Fix: response bins plus a specificity ratio (power at the class's own bin over the median of the other classes); Round 2 returned PASS (`07_review.md`).

**Run.** Four commands at `8adcb4d2f99cdafe8abe119d464cadc6e7b441fb`, 3, 3, 5 and 4 s (`05_run.md`; logs `reports/logs/P03/*.log`). The runner did not capture the Python exit codes; the verifier re-ran all four from a clean checkout, exit 0 each, numeric lines identical. Legacy fs 250 only relabels the axis (band-maximum bin equal at 250 and 256 and label = bin × 250/256 in 25 of 25 subject × class rows). The quality mask rejected 0 windows (kept 1592); this is a consistency check on windows already gated in P02, not a rejection rate. The recomputed PSD equals the saved `X_psd_features`, `max |computed - saved| = 0`, for S01–S05.

**Which subjects show clear SSVEP peaks (P03.3).** Criterion fixed by the reviewer before the run (clear: band maximum at the response bin, ≥ 2× band median, specificity ≥ 1.5), figures `outputs/figures/exploration/S0{1..5}/occipital_spectra_header.png`, numbers from `reports/logs/P03/diagnose_occipital_spectra_header_20261024T180126.log`:

| Subject | Fundamentals at 24 / 20 / 15 / 10.91 / 8.57 Hz | Reading |
|---|---|---|
| S03 | 5/5 clear (×5.97, ×12.93, ×14.32, ×6.94, ×4.63 median) | strong responder |
| S04 | 5/5 clear (×9.59, ×14.68, ×29.56, ×31.47, ×9.55) | strongest responder |
| S05 | 3 clear (24, 20, 15 Hz) + 2 visible (10.91, 8.57 Hz) | 104 and 105 are carried by the second harmonic: band maximum at 22 Hz (2f0 ×11.11) and 17 Hz (2f0 ×13.50) |
| S01 | 1 clear by the rule (104, ×4.28, specificity ×1.78), 2 partial, 2 absent | no clear fundamental at 24 or 20 Hz (×0.88, ×1.41); 104 is alpha-adjacent, a weak response at best |
| S02 | 0 clear or visible, 3 partial (alpha-confounded), 2 absent | no SSVEP peak |

S01 and S02 are dominated by non-stimulus activity in every class: S01 band maxima at 8–11 Hz (101 at 10 Hz, as seen in P02), S02 at 6 Hz with a second peak at 9 Hz. The P02 partial S03 8.57 Hz target (plateau in the 7-channel mean) is clear in the O1/Oz/O2 mean (bin 9, ×4.63, specificity ×2.43); the channel set, not the data, explains it. This is spectral evidence only: no accuracy was computed, and the statements are descriptive means without uncertainty.

**Findings for later phases.** Expect S01 and S02 to stay low under any classifier; an accuracy far above R-6 (61.00 % and 56.12 % at 1.0 s) is a leakage suspect. S05 104 and 105 should gain from harmonic features (FBCCA, P05). In P05 the loader of `visualize_data.py` moves to `src/`. The effect of PF-04 appears where 250 Hz enters filters and reference sinusoids (P04/P05), not in these spectra. No reference consultation was made. Next: P04.

## P04 — Early hybrid models, fusion CNN and first explainability

Full report: `mas/state/reports/P04.md`. Code and runs at `552029a`. Date of all steps: 2026-10-24.

**Aim.** The original's first model benchmark (roadmap P04): a 37-feature hybrid (32 harmonic-PSD features plus 5 FBCCA scores), six sklearn classifiers, a 10,005-parameter dual-branch fusion CNN, exported S01 and S04 models and LDA-weight heatmaps. Data source: legacy `data/processed/<S>/`, OO session, stimulus windows only (200, 199, 200, 198, 200 windows for S01–S05).

**Build.** `scripts/training/train_models.py`, `train_final_model.py`, `batch_run_subjects.py`, `scripts/xai/run_xai.py`, `compare_subject_xai.py`, `src/models/cnn/spatial_spectral_cnn.py` and three test files. The legacy behaviours are labelled and kept reachable: leaky `StratifiedKFold(5, shuffle, 42)` over windows (R1/PF-01), 2-window smoothing without trial reset (R8/PF-02), FBCCA at fs 250 (PF-04) and per-window sub-band filtering (PF-14). Full-data LDA and CNN fits are exports and XAI only (R2 exception).

**Tests and review.** Suite `349 passed, 10 warnings in 83.06s` (`mas/state/phases/P04-early-models-xai/04_tests.md`); the verifier re-ran it in a clean worktree, 349 passed (`mas/state/scratch/pytest_P04.txt`). Nine mutant checks reject the buggy variants, including conv biases (10,053 instead of 10,005). Pre-run audit PASS in Round 1 with no FAIL; results review APPROVE (`07_review.md`).

**Run.** Seven commands on CPU at 140 epochs, all exit 0, 544 s in total (9.07 min against a 120 min budget) (`05_run.md`; `reports/logs/P04/`). The batch command omitted `--paradigm`; the script default is the same OO session. Parameter count of `DualBranchFusionCNN`: 10005 (`reports/logs/P04/param_count_20261024T223559.log`).

**Results (legacy, leaky, not comparable with R-6).** Shrinkage-LDA at 1.0 s and smoothed: S01 50.00 and 55.50 %, S02 51.26 and 63.82 %, S03 83.00 and 95.00 %, S04 97.98 and 97.98 %, S05 95.50 and 97.50 % (`outputs/reports/S0{1..5}_model_evaluation.csv`). Fusion CNN at 1.0 s: 51.50, 53.77, 89.00, 99.49 and 100.00 %; its training-fold accuracy: 95.38, 98.12, 98.75, 100.00 and 100.00 % (`outputs/reports/batch_run_subjects.csv`). Leaky LDA on S01 and S02 sits 11.00 and 4.86 points below R-6 (61.00 and 56.12 %). The reviewer reads this as no leakage-driven inflation for the linear models.

**Findings.** (a) The fusion CNN's training-fold accuracy exceeds its test accuracy by 43.875 points on S01 and 44.348 on S02 (PF-30 reading: a generalization problem); the gap is 9.75 on S03 and about 0.5 or 0 on S04 and S05. (b) The smoothed gains cross trial boundaries and are not 2 s decisions: LDA +0.00 to +12.56 points, CNN −1.52 to +11.50 points; S04 and S05 CNN smoothing loses 3 windows each. (c) The pre-committed PF-04 expectation (weaker FBCCA for classes 101 and 102) is not supported in this descriptive reading. (d) XAI: for S04, 5 of 5 classes have their largest positive spatial-spectral weight on their own f0 bin, all on Oz; S01 weights are about an order of magnitude smaller. These describe full-data fits, not generalization.

**Next.** P11 measures the leak size with grouped CV on the same features and resets smoothing per trial; P16 fixes the FBCCA sampling rate and filtering and quantifies PF-04. Open items: the `src` to `scripts` lazy imports, a `--seed` option and a colourbar overlap in `compare_S01_S04.png`. No reference consultation was made in P04 (two access-log lines at 21:27 predate the phase, see `mas/state/decisions.md`). Next phase: P05.

## P05 — Feature extractors and feature-space / model benchmark

Full report: `mas/state/reports/P05.md`. Round 1 run at `e47e799`, Round 2 code and run at `edcc177`. Dates: 2026-10-24 (Round 1), 2026-10-25 (Round 2).

**Aim.** The original's feature stage (roadmap P05): continuous PSD, FBCCA and FBCSP extractors, a ten-model sklearn suite, six feature spaces on S03 under the legacy protocol, and the R-3 flagship (FBCSP m=1 + FBCCA → Shrinkage-LDA: 90.36 % at 1.0 s, 95.43 % at 2.0 s, 197 clean and 3 rejected windows). Data source: legacy `data/processed/<S>/`, OO session, stimulus windows only.

**Build.** Three extractors, the suite, the benchmark runner, four benchmark and evaluation scripts, the FBCCA and FBCSP blocks of `visualize_data`, and the P04 carry-forward moves into `src/` (24 code and test files, `mas/state/reports/P05.md` §2). The legacy behaviours are labelled and reachable: window-level `StratifiedKFold(5, shuffle, 42)` (R1, PF-01), per-window sub-band filtering (R3, PF-14), fs 250 (PF-04), and the full-data CSP for visualization only (R2 exception). Each benchmark fits CSP, scaler and LDA per training fold (R2, PF-11); one window mask is shared by every block (PF-10).

**Tests.** Round 1 suite `413 passed` (120.23 s, clean worktree); Round 2 suite `426 passed` (107.32 s, clean worktree). The mutant checks fail as designed (Butterworth for Chebyshev, un-normalised CSP, leaky CSP at 0.67 against 0.23 in-fold, fs 256, the P04 POz cluster, separate gates).

**Round 1 (FAIL).** On S03 the counts (197 / 3) and the 1.0 s accuracy (90.36 %) matched R-3 exactly. The 2.0 s value under the planned no-reset rule was 95.94 % (+0.51 pp, inside tolerance); the printed `i % 5` diagnostic gave 95.43 %, equal to R-3. The verifier returned FAIL on one qualitative item: 24 Hz precision 0.8537 against "perfect".

**Round 2 (investigation and corrections).** Four R11 consultations of the original repository (its P05-stage commit) gave three changes, each recorded in `mas/state/decisions.md`: (1) the reported 2.0 s rule is `i % 5` on the clean array, as the roadmap convention and the original code define it, with no-reset kept as a labelled diagnostic; (2) the mask limits are the original extractors' 0.5–120 µV and 0.1–35 µV; (3) the harmonic script gives FBCCA the visual cluster PO8, O1, Oz, O2 by name. The reviewer judged each demonstrated, not tuned; counts and 1.0 s values were unchanged in all subjects. The first consultation came 30 s before the diagnostics were committed, recorded as a sequencing concern: diagnostics come before the answer key from now on.

**Results (legacy, leaky, not comparable with R-6).** Round 2 S03: 197 / 3, 1.0 s 90.36 %, 2.0 s 95.43 % (both exact to R-3; `reports/flagship_S03.csv`). The hybrid FBCSP + FBCCA with Shrinkage-LDA (lsqr) is the best space at 1.0 s (90.36 %, 5.59 pp above FBCSP at 84.77 %); FBCCA argmax (48.73 %) is the lowest reference. All ten R-5 values reproduce exactly: S01 64.50 / 75.50, S02 66.33 / 71.94, S03 90.36 / 95.43, S04 98.98 / 98.48, S05 96.50 / 96.50 (1.0 s / 2.0 s %; cohort mean 83.33 / 87.57). The 24 Hz precision is 0.9750 (39 of 40 windows), not "perfect": deviation D-1, accepted by the reviewer. Harmonic PSD + FBCCA is reported under two names, 74.11 % (all channels) and 75.63 % (PO8, O1, Oz, O2); both give 84.77 % at 2.0 s.

**Verdict.** Verifier PASS with D-1 (restated); reviewer APPROVE with D-1. The S01 and S02 values stay low under every model, and S04 and S05 are near ceiling. The 2.0 s gains (+11.00, +5.61, +5.07 pp on S01–S03) are partly a label-order effect of the legacy arrays and are not decision gains.

**Open.** P06 reproduces R-5 (cohort, leaky). P11 must state the legacy-folder smoothing rule for R-6 (`i % 5` on the clean array or pre-gate trial ids). FBCCA channel names are missing from the six-space header and `.meta.txt`. The three papers named in the ml-engineer handoff are not opened (R10). The `visualize_data` gate (vpp 0.5–200 µV, std 0.5–60 µV) differs from the benchmark mask. Next phase: P06.

## P06 — Feature-selection ablation, legacy 5-subject cohort, report v1

2026-10-25, branch `phase/P06-feature-selection-cohort`. Code and reported run at `7575405`; diagnostic run at `7de11ce`. Report: `mas/state/reports/P06.md`.

**Aim.** The original's feature-selection ablation on S03 (roadmap P06; R-4) and the five-subject legacy cohort table (R-5, leaky), with the historical technical report v1 and its methodology infographic. ANOVA, mutual information, sequential forward selection (SFS) and sub-band pruning are fitted on the training rows of each fold only (R2, PF-11). The protocol is the P05 legacy protocol: window-level `StratifiedKFold(5, shuffle, 42)` (R1), per-window sub-band filtering (R3), `i % 5` smoothing (R8), fs 250 (PF-04), mask vpp 0.5–120 µV and std 0.1–35 µV (R5).

**Build.** `src/features/selection/feature_selection.py` and the scripts `benchmark_feature_selection.py` and `benchmark_5_subjects.py` (NEW); two test files (NEW); FBCCA channel names in the classical header (MODIFIED). Report v1 and infographic v1 in `docs/report/v1/` (NEW).

**Results (legacy, leaky, not comparable with R-6).** S03 ablation (`reports/feature_selection_ablation_S03.csv`), 1.0 s / 2.0 s smoothed: full baseline (p 55) 90.36 / 95.43; sub-band pruning (p 45) 87.31 / 94.92; ANOVA (p 25) 86.29 / 94.42; mutual information (p 25) 87.82 / 93.40; SFS (p 20) 89.85 / 95.94. Cohort (`reports/five_subjects_benchmark.csv`): S01 64.50 / 75.50, S02 66.33 / 71.94, S03 90.36 / 95.43, S04 98.98 / 98.48, S05 96.50 / 96.50; mean 83.33 / 87.57. All ten R-5 values, and four of the five R-4 rows, reproduce exactly.

**The SFS row (accepted deviation D-1).** Our SFS misses R-4 (84.77 / 93.40) by +5.08 / +2.54 pp. The original repository has no sequential forward selection in any commit or branch; its P06-stage ablation has four methods (full, ANOVA, MI, pruning). The R-4 SFS row therefore cannot be reproduced from reference code. The procedure ran in order: verifier FAIL, then labelled diagnostics (ten variants; leak audit clean, 0 test rows in any SFS input; `reports/feature_selection_sfs_diagnostics_S03.csv`, `reports/feature_selection_sfs_audit_S03.csv`), then six consultation rows of read-only reference queries (12 logged commands, `mas/state/scratch/reference_access.log` lines 15–26). No variant lands in both R-4 ranges. The row is reported as ours, with R-4 beside it. The original report (.docx) is an open question for Sebastian.

**Interpretation.** SFS and the full baseline differ by one window (0.51 pp). Within the leaky protocol every reduced set is at or below the full baseline at 1.0 s, by 0.51–4.07 pp (one to eight windows); with one subject, a leaky split and no interval, no reduction is singled out. The SFS row moves between 172 and 177 windows across the inner-CV and estimator variants with 15 selected columns (166 with the 55-column candidate set), so its position is not a finding. The 2.0 s gains of 11.00, 5.61 and 5.07 pp on S01–S03 are partly the legacy `i % 5` label-order effect (P05), not decision gains.

**Verdicts.** Verifier: FAIL on the SFS row (`mas/state/phases/P06-feature-selection-cohort/06_verify.md`, `b695b9a`), restated PASS with D-1 (`d905194`). Reviewer: pre-run PASS (`3030a25`); results review D-1 (`637dad6`); report v1 REJECT on text (`9473718`), then APPROVE (`870932d`).

**Report v1.** `docs/report/v1/report.md` keeps the historical title "A Leakage-Free Classical Pipeline for 5-Class SSVEP Decoding Under a 1.0-Second Constraint" with a boxed correction: window-level CV leaks trials (P11). `docs/report/v1/methodology_infographic_v1.svg` is labelled "v1 — historical". Both are kept as history and are superseded in P24.

**Open.** Carried to P07: the vacuous R6 layout test (`tests/test_p06_feature_selection.py:84`), the 76.10 s ablation smoke test (`:123`) and suite runtime (264.82 s in the verifier run, 274.37 s in the tester run). Carried to P11: the legacy-folder smoothing rule for R-6 (open since P05). Next phase: P07.
