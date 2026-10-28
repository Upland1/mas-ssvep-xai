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

## P07 — Two-tier artifact quality gate and the 8-channel montage

2026-10-25, branch `phase/P07-two-tier-quality`. Code and reported run at `fa5dade`; results review at `8b6262f`. Report: `mas/state/reports/P07.md`.

**Aim.** Roadmap P07: a two-tier quality gate (subject-level channel drop, then window rejection on the surviving channels), PO7 restored in the configuration (8 channels), the PF-07 `vpp_min` regression reproduced and pinned, and the first `reports/n_subjects_benchmark.csv`. The protocol stays legacy: window-level `StratifiedKFold(5, shuffle, 42)` (R1, PF-01), per-window sub-band filtering (R3, PF-14), `i % 5` smoothing (R8, PF-02), fs 250 (PF-04), per-script gates (R5). The legacy 7-channel arrays of `data/processed/` are not regenerated (R-6 is defined on them).

**Build.** Tier 1 (`identify_noisy_channels`, `drop_noisy_channels`) and the two-tier pipeline `apply_artifact_quality_pipeline` in `src/preprocessing/signal/quality_check.py`; `resolve_channel_names` and `legacy_scalp` in `src/io/channels.py` (NEW); config v2 with the 8-channel montage; extractors return `(X, y_clean, valid_mask, channel_report)` and share one gate decision across blocks (PF-10); `scripts/benchmarks/feature_based/benchmark_n_subjects.py` (NEW). Preprocessing gains `--no-channel-drop`, `--vpp-min` (pinned 0.5; 5.0 labelled as the PF-07 demo), `--legacy-p02` (reproduces the P02 arrays) and a refusal to write into legacy 7-channel folders. Six code and test files are NEW and 35 MODIFIED.

**Results (legacy, leaky, not comparable with R-6 accuracies).** Clean and rejected windows equal R-6 exactly for all five subjects: 200/0, 196/3, 197/3, 197/1, 200/0; channels kept 7, dropped none. 1.0 s / 2.0 s smoothed accuracy: S01 64.50 / 75.50, S02 66.33 / 71.94, S03 90.36 / 95.43, S04 98.98 / 98.48, S05 96.50 / 96.50; mean 83.33 / 87.57, equal to the P06 cohort (R-5, superseded) to two decimals. Sources: `reports/n_subjects_benchmark.csv`, `reports/logs/P07/benchmark_n_subjects_20261025_133213.log`.

**PF-07 (accepted deviation D-1).** The count is reproduced: with `--vpp-min 5.0 --no-channel-drop`, S03 rejects 320 of 320 windows and is skipped (`reports/logs/P07/run_preprocessing_vppmin5_nodrop_20261025_133206.log`). The mechanism is not: every one of the 320 rejections is a `vpp_high` on PO7 (mean Vpp 797.56 µV over 605 one-second windows; `reports/logs/P07/run_preprocessing_vppmin5_20261025_133201.log`), and `vpp_low` is 0 in every real-data run. With PO7 removed by tier 1, `vpp_min` 5.0 and 0.5 give the same 317 accepted / 3 rejected (`reports/logs/P07/run_preprocessing_vppmin5_20261025_133201.log`, `reports/logs/P07/run_preprocessing_pinned_20261025_133207.log`). The `vpp_min` mechanism is shown only by synthetic tests. The 0.5 pin stays as the R5 defence. Open question for Sebastian: did the original's P07 restore PO7 and change `vpp_min` together, so that PF-07 names the wrong cause?

**Legacy check.** The pinned S03 run keeps the legacy seven channels and yields 317 windows, identical to `data/processed/S03` in labels and in `X_time` (maximum absolute difference 0.0; `mas/state/phases/P07-two-tier-quality/06_verify.md`). The legacy arrays were not regenerated: SHA-256 prefixes of the 18 files match before and after the runs (`mas/state/scratch/d0_before.txt`).

**Tests and runtime.** 503 passed in 191.73 s on a clean checkout at `fa5dade` (`mas/state/phases/P07-two-tier-quality/06_verify.md`), down from 469 s before the runtime cut (`mas/state/phases/P07-two-tier-quality/03_changes_ml-engineer.md`).

**Review.** The pre-run audit failed in Round 1 on two points: the legacy 7-channel path was gone (golden rule 3, with the risk of overwriting the R-6 inputs), and the P04 positional channel selection was not checked against each subject's names (R6, PF-06). Both were fixed (`1083862`, `5bc3fba`, `a3870b1`); Round 2 passed (`10b8765`). The verifier passed (`0d20904`), and the results review approved with D-1 (`8b6262f`).

**Interpretation.** Only S03 was preprocessed with 8 channels in this phase; the 8-channel path for S01, S02, S04 and S05 has not been run. On the legacy arrays tier 1 drops nothing (largest channel fail fraction 1.5 %, S02 O2, `reports/logs/P07/benchmark_n_subjects_20261025_133213.log`). The accuracies are leaky and carry no method claim.

**Open.** Carried forward: print the ungated quality summary before a subject is skipped (data-signal, next touch of `run_preprocessing.py`); do not run `make preprocess` or any run over `data/processed/` before P11; the P11 smoothing rule for legacy folders (open since P05). Feature width now depends on the tier-1 drop, so per-subject feature sets must not be pooled before P16. Next phase: P08.

## P08 — EEGNet on raw windows

2026-10-25 to 2026-10-26, branch `phase/P08-eegnet`. Code and reported run at `cf62bb3`; results review at `ef124c1`. Report: `mas/state/reports/P08.md`.

**Aim.** Roadmap P08: the first network of the project, `EEGNetSSVEP` (2,349 parameters at 7 channels × 256 samples, R-8), trained on the S03 raw legacy windows under the classical benchmark's gate and leaky CV, on CPU and on CUDA. Everything stays legacy: window-level `StratifiedKFold(5, shuffle, 42)` (R1, PF-01), `i % 5` smoothing (R8, PF-02), the P07 gate applied per script (R5 legacy), and fs 250 as a label only.

**Build.** `src/models/cnn/eegnet.py` (NEW): four bias-free convolutions, max-norm 1.0 on the depthwise spatial filters, renormed after every optimizer step. `src/models/cnn/eegnet_cv.py` (NEW): per-window z-score, AdamW, cosine schedule, label smoothing 0.05, seed 42 + fold, 150 fixed epochs, train accuracy on the un-augmented training fold (PF-30). `scripts/benchmarks/neural_networks/benchmark_eegnet.py` (NEW): CLI, device-suffixed CSV and `.meta.txt`. Tests: 25 P08 cases in `tests/test_p08_eegnet.py` and `tests/test_p08_eegnet_known_answer.py` (NEW). Suite `528 passed, 21 warnings in 190.59s (0:03:10)` (`mas/state/phases/P08-eegnet/06_verify.md`), up from 518 before the known-answer tests.

**Results (legacy, leaky, S03; not comparable with R-6).** Clean / rejected 197 / 3, 7 channels kept, none dropped, 2,349 parameters on both devices.

| Device | 1.0 s (%) | k/197 | 2.0 s smoothed (%) | k/197 | Train, mean over folds (%) |
|---|---|---|---|---|---|
| cpu | 75.63 | 149 | 85.79 | 169 | 98.34 |
| cuda | 71.07 | 140 | 81.22 | 160 | 98.60 |

Sources: `reports/eegnet_benchmark_cpu.csv`, `reports/eegnet_benchmark_cuda.csv` (and `.meta.txt`); logs `reports/logs/P08/benchmark_eegnet_{cpu,cuda}_run{1,2}_*.log`. Each device repeated itself exactly over two runs.

**CPU–CUDA gap.** 9 windows on both metrics (4.56 pp at 1.0 s, 4.57 pp at 2.0 s). This is a device-associated difference, not nondeterminism within a device and not a model effect. Neither number is "the" P08 result, and they are not averaged. Later A/B comparisons fix the device (CPU) and the seeds, and treat differences of a few windows as noise.

**Diagnostics (not targets).** The leaky classical flagship on S03 is 90.36 / 95.43 (178 / 188 of 197); EEGNet is 19 to 38 windows lower, so no CNN advantage from the leak appears under this protocol. This is not a model ranking. Leak-free R-9b without augmentation is 73.60 / 82.23 (145 / 162); EEGNet is −5 to +4 windows across devices, which is inconclusive. R-7 (79.19, augmentation on) is a later target, quoted as such. R-6 is not compared.

**PF-30 reading.** Train 98.34 % (cpu) and 98.60 % (cuda); test 75.63 % and 71.07 %. This is a generalization gap, not an optimization problem. The test accuracy is leaky, so a leak-free gap would be larger, to be measured in P11.

**Review.** Pre-run audit PASS in Round 1 (`2543a33`), no required fixes, four non-blocking notes. Results review APPROVE (`ef124c1`), no deviations to accept. Verifier PASS (`ac856ad`). The original repository was not consulted (R11).

**Open.** Carried forward: data-source line and `n_channels` in the EEGNet `.meta.txt` (R9); unused `discover_subjects` import; a test that the EEGNet gate matches `prepare_subject` on a tree with a bad channel (P09 or P10); a saved pytest log under `reports/logs/P08/`; the equivalence of the max-norm to the original constraint is not verified. The reviewer's note that quotes R-6 (+7 windows) is not carried here, pending the orchestrator's decision. Next phase: P09.

## P09 — Compact-CNN and ShallowConvNet

2026-10-26, branch `phase/P09-compact-shallow-cnn`. Code and reported runs at `edd476e`; pre-run audit `15aaa5d`; verifier `7ced253`; results review `f20ea80`. Phase report: `mas/state/reports/P09.md` (on main with the P09 merge, `8430cb9`).

**Aim.** Roadmap P09: two more networks on the S03 raw legacy windows, `CompactCNN` (named `compact_cnn`, PF-31) and `ShallowConvNet`, with R-8 parameter counts exact (2,349 / 14,485 / 56,021) and benchmarks that mirror the P08 EEGNet protocol. Everything stays legacy: window-level `StratifiedKFold(5, shuffle, 42)` (R1, PF-01), `i % 5` smoothing (R8, PF-02), the P07 gate applied per script (R5 legacy). Compact-CNN's temporal kernel uses the legacy 250 Hz label, K = 29 (PF-04); at 256 Hz it would be K = 30 and 56,693 parameters.

**Build.** `src/models/cnn/compact_cnn.py` and `src/models/cnn/shallow_conv_net.py` (NEW). `src/models/cnn/benchmark_common.py` (NEW) is one shared driver for the three benchmark scripts; `benchmark_eegnet.py` became a thin wrapper and `src/models/cnn/eegnet_cv.py` takes a network builder (both MODIFIED). The P08 carry-forwards are done: data-source line and `n_channels` in `.meta.txt`, unused import removed. `scripts/benchmarks/neural_networks/count_parameters.py` (NEW) exits 1 on any R-8 mismatch. Tests: `tests/test_p09_compact_shallow.py` (25) and `tests/test_p09_known_answer.py` (20), both NEW; full suite `573 passed, 21 warnings` (`reports/logs/P09/pytest_20261026T002847.log`), up from 528 at P08.

**Results (legacy, leaky, S03, CPU; not comparable with R-6).** Clean / rejected 197 / 3, 7 channels kept, none dropped, for both networks.

| Model | Params | 1.0 s (%) | k/197 | 2.0 s smoothed (%) | k/197 | Train, mean over folds (%) |
|---|---|---|---|---|---|---|
| compact_cnn | 56,021 | 54.31 | 107 | 62.94 | 124 | 100.00 |
| shallow_convnet | 14,485 | 86.80 | 171 | 92.89 | 183 | 100.00 |

Sources: `reports/compact_cnn_benchmark_cpu.csv`, `reports/shallow_convnet_benchmark_cpu.csv` (and `.meta.txt`); logs `reports/logs/P09/benchmark_{compact_cnn,shallow_convnet}_run{1,2}_*.log`. Each network repeated itself exactly over two runs (CSV, `.meta.txt`, fold and summary lines).

**Diagnostics (not targets).** Against the leaky classical flagship on S03 (178 / 188): compact −71 / −64, shallow −7 / −5. Against the P08 EEGNet CPU run (149 / 169): compact −42 / −45, shallow +22 / +14. Against leak-free R-9b without augmentation (compact 84 / 92, shallow 169 / 180): compact +23 / +32, inconclusive; shallow +2 / +3, within noise. Against R-7 (augmentation on, 1.0 s: compact 124, shallow 176): compact −17, shallow −5. The compact 2.0 s value (124) equals R-7's compact 1.0 s value by coincidence; they are different quantities.

**Reading.** On S03, under the legacy leaky protocol on CPU, the only accepted ordering is ShallowConvNet > EEGNet > Compact-CNN (`decisions.md` P09 row). It is one subject, one device and one seed set: not a cohort ranking and not a best-network claim. Train accuracy is 100 % in all ten folds for both networks, against test 48.72–58.97 % (compact) and 79.49–92.31 % (shallow): a generalization gap, not an optimization failure (PF-30). The gap is larger for Compact-CNN, whose linear head holds 73 % of its parameters; that is a hypothesis and is not tested here.

**Review.** Pre-run audit PASS in Round 1, no required fixes, three non-blocking notes. Results review APPROVE; acceptance met, no deviations to accept. Verifier PASS. Decisions rows 88–90 in `mas/state/decisions.md`.

**Open.** The EEGNet S03 benchmark was not re-run after the refactor; its identity rests on the synthetic hash pin (`tests/test_p09_compact_shallow.py:23`) and on the reviewer's comparison with the P08 code. Non-blocking notes N1–N3 (z-score spy in the mirror test; gate-equality test does not compare window values; `count_parameters` writes its CSV before the R-8 check). Test suite runtime 219 s against the "about a minute" target. The max-norm equivalence claim from P08 remains unverified.

## P10 — Data augmentation and the A/B protocol

2026-10-26, branch `phase/P10-augmentation-ab`. Code, tests and runs at `5f2d5eb`; pre-run audit `75b77fd`; verifier `4d403a4`; results review `2080b68`. Phase report: `mas/state/reports/P10.md` (on main with the P10 merge, `829602c`).

**Aim.** Roadmap P10: training-fold augmentation (Gaussian noise proportional to each channel's std, one amplitude factor per window, circular time shift, intra-class mixup) and an OFF/ON A/B for EEGNet, Compact-CNN and ShallowConvNet on S01–S05, with the final training accuracy on the un-augmented training fold as the PF-30 diagnostic. Everything stays legacy and leaky: window-level `StratifiedKFold(5, shuffle, 42)` (R1, PF-01), `i % 5` smoothing (R8, PF-02), the P07 gate applied per script (R5 legacy), and the fs 250 label (K = 29 for Compact-CNN, PF-04). The frozen copies are `reports/legacy_leaky/augmentation_ab_<model>.csv`. The leak-free A/B is P11.

**Build.** NEW `src/preprocessing/dataset/augmentation.py`: `add_gaussian_noise`, `scale_amplitude`, `time_shift`, `mixup_intra_class`, `SSVEPAugmentedDataset` (order mixup, scale, shift, noise; p = 0.5 each; own `numpy` generator; float32 and long outputs). NEW `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py` (`--model`, `--epochs 150`, `--freeze-legacy`). MODIFIED `src/models/cnn/eegnet_cv.py` (ON swaps only the training-fold dataset, seeded 42 + fold) and `src/models/cnn/benchmark_common.py` (`--augment {off,on}`, default off); the three benchmark wrappers changed in their docstrings only. Tests: NEW `tests/test_p10_augmentation.py` (15) and `tests/test_p10_augmentation_known_answer.py` (16); MODIFIED `tests/test_p08_eegnet.py` and `tests/test_p09_compact_shallow.py` (the "`--augment on` is rejected" assertion now checks an invalid value). Suite: `604 passed, 21 warnings in 219.16s (0:03:39)` (`reports/logs/P10/pytest_20261026_011732.log`), up from 573 at P09.

**Results (legacy, leaky, CPU, 7 channels; not comparable with R-6).** Source: `reports/augmentation_ab_<model>.csv` (the `reports/legacy_leaky/` copies are byte-identical). EEGNet cohort mean, 1.0 s: 63.93 → 67.04 %, Δ +3.11 pp; 2.0 s: 68.18 → 71.08 %, Δ +2.90 pp. Per-subject EEGNet Δ at 1.0 s: S01 +7.50 (+15 windows), S02 −1.53 (−3), S03 +5.08 (+10), S04 +1.01 (+2), S05 +3.50 (+7); four of five improved. EEGNet S03 OFF = 75.63 / 85.79 % (149 / 169 of 197), equal to the P08 CPU run (`reports/eegnet_benchmark_cpu.csv`). Compact-CNN cohort Δ +14.12 / +11.39 pp; ShallowConvNet +2.01 / +2.72 pp (diagnostics, same CSVs).

**Reading.** R-9a: the 1.0 s cohort gain of +3.11 pp lies inside the recorded range [+3.00, +7.34] pp, at its lower edge (+0.11 pp above it). The 2.0 s gain of +2.90 pp is within ±3 pp of +1.79. This is one CPU seed set with no significance claim; only S01 and S03 exceed the nine-window noise line. PF-30: EEGNet OFF test accuracy on S01 and S02 is 28.00 / 27.04 % (chance 20 %) with un-augmented training accuracy 83.25 / 81.38 %. That is a generalization failure, not an optimization failure. The Compact-CNN S04 Δ (+43.15 pp, 85 windows) equals R-9b's leak-free S04 Δ, which is a coincidence of two different quantities and not a reproduction.

**Review.** Pre-run audit PASS in Round 1, no required fixes; notes N1–N6, including N1 (a mixup partner may be the anchor itself, effective mixup rate about 0.484) and N4 (the seeded DataLoader generator and the training-fold-only input are correct by inspection but untested; carried to P11). Verifier PASS (`06_verify.md`). Results review APPROVE, both acceptance clauses met, no deviations to accept. The original repository was not consulted (R11).

**Open.** Carried forward to P11: tests that the augmented dataset length equals the training fold and that the loader generator is seeded in both arms (N4). The single-subject ON CSVs are named `*_aug_benchmark_<device>.csv` (not a roadmap output). The P10 suite takes 219 s against the "about a minute" target. Next phase: P11.

## P11 — Discover and fix trial leakage

2026-10-26, branch `phase/P11-trial-leakage-fix`. Code and runs at `aedf8a8`; Round 2b diagnostic at `0b96524`; results review Round 2 `50d9d01`; verifier restatement `f744451`. Phase report: `mas/state/reports/P11.md`.

**Aim.** Roadmap P11: replace the window-level `StratifiedKFold` (R1, PF-01) by `StratifiedGroupKFold` on reconstructed trial ids in the nine benchmark scripts, and measure the inflation the leak caused. Acceptance: the flagship equals R-6, the augmentation A/Bs fall in R-9b, and the before/after table shows the classical drop of about 4–5 pp and the CNN drops that the roadmap predicts.

**Build.** NEW `src/preprocessing/dataset/cv_utils.py` (`build_trial_ids` on pre-gate labels, then the gate's `valid_mask`; `make_splits`; `assert_no_shared_trials`), `scripts/diagnostics/demo_cv_leakage.py`, `scripts/diagnostics/network_seed_spread.py` (DIAGNOSTIC), and four P11 test files. MODIFIED: the nine classical and network scripts, `legacy_eval.py`, `benchmark_runner.py`, `smoothing.py`, `eegnet_cv.py`. Defaults: `--cv grouped`, `--smoothing mod5` on legacy folders; `--cv legacy` writes under `reports/legacy_leaky/` and reproduces R-5, R-4 (with P06 D-1) and R-3 exactly. Suite: `678 passed, 21 warnings in 393.19s` (`reports/logs/P11/pytest_20261026_110219.log`) at `aedf8a8`, `687 passed` at `0b96524`.

**Results (legacy folders, 7 channels, CPU, one training seed 42 on fixed folds; `reports/n_subjects_benchmark.csv`, `reports/cv_leakage_demo.csv`, `reports/augmentation_ab_<model>.csv`).** Flagship grouped: 61.00 / 56.12 / 86.80 / 97.46 / 95.00 % at 1.0 s, mean 79.28 %; 2.0 s with the legacy `i % 5` rule, mean 82.61 %. R-6 is reproduced on every cell. Leak effect, classical: −4.06 pp (1.0 s) and −4.96 pp (2.0 s) on the cohort mean (R-6 −4.05 / −4.96); S02 −10.21 pp at 1.0 s. Networks, seed 42 against the frozen single-seed P10 run (`reports/cv_leakage_demo_networks.csv`): EEGNet OFF 63.93 → 58.36 % (−5.57 pp), Compact-CNN OFF 42.65 → 37.09 % (−5.56 pp), ShallowConvNet OFF 75.71 → 72.67 % (−3.04 pp). EEGNet cohort Δ at 1.0 s: +4.85 pp (R-9b +2.01); Compact-CNN +13.56 pp (R-9b +17.16); ShallowConvNet +2.63 pp (R-9b +2.53).

**Reading.** The classical inflation is reproduced. The CNN-specific inflation of the original is not: the three-base EEGNet drop is −2.71 pp (OFF) and −2.82 pp (ON), and the seed-42 EEGNet S03 drop of −20.81 pp is consistent with a low training-seed draw (three-base range 16.75 pp; `reports/diagnostics/p11_seed_spread_eegnet.csv`, DIAGNOSTIC). Of the 14 seed-42 cells outside R-9b's bands, 13 are explained by training-seed variance, including every cohort cell (D-4). Compact-CNN S03 2.0 s ON is not reproduced within tolerance: 129, 127 and 129 of 197 windows over three seeds, against a smallest in-band count of 131 (D-8, accepted by Sebastian as a documented deviation, B006). The 2.0 s column is the legacy `i % 5` rule, as R-6 defines it; on S03 (exact ids, 3 rejections) the trial-reset rule is 3.56 pp lower (`reports/cv_leakage_demo.csv`). Which rule is leak-free at 2.0 s is an open question for Sebastian (era-matrix R8 row) until true trial ids arrive in P16.

**Review.** Pre-run audit Round 1 FAIL (demo fix, condition C1 on the smoothing chronology); Round 2 PASS. Results review Round 1 REJECT (`3c30c9e`) on the network R-9b misses; the seed-spread diagnostic was run; Round 2 APPROVE with D-8 (`50d9d01`). Verifier: FAIL in its first two rounds, then PASS restated with D-8 (`f744451`). Reference consultation: one, deep-learning, Round 2, under R11 (three logged accesses, 12:05:00–12:05:15); the original's RNG stream was not adopted. The smoothing chronology is on record: the smoke numbers (`18a6792`) were seen before the reversal to `i % 5` (`31d6f8e`).

**Open.** Carried forward: N1 (`oof_space(splits=None)` raises at the P16 refactor); a planning rule from P12 (network results compared with a reference or an A/B delta use at least three training seeds); the residual leak on S02 and S04 (approximate ids) until P16; the grouped feature-space ordering at 2.0 s (hybrid Shrinkage-LDA 90.36 below Continuous PSD SGD PA 92.39 in `reports/feature_space_benchmark_S03.csv`), not an acceptance item and not yet reviewed. Next phase: P12, after the orchestrator's gate.

## P12 — Functional connectivity v1: coherence, bias fix, matched baseline

2026-10-26, branch `phase/P12-coherence`. Code and runs at `cb446b0`; pre-run audit Round 2 `35a1f29`; verifier `b68f5eb`; results review `66f3346`. Phase report: `mas/state/reports/P12.md`.

**Aim.** Roadmap P12: a coherence connectivity estimator for the legacy windows, the two bugs found in the first real run (PF-15: per-window coherence averaged over windows is biased upward; PF-16: a 5–35 Hz broadband baseline against a ±1 Hz stimulus band), and a per-subject matched-baseline difference for S03 and S04. Reproduce both bugs first, then fix them on the reported path. Acceptance A0–A6 was fixed before the run [1, 7].

**Build.** NEW `src/features/connectivity/connectivity_extraction.py` (`compute_coherence_matrix` DIAGNOSTIC; `compute_condition_coherence` concatenated, nperseg 256, the reported estimator; `compute_baseline_matched_connectivity` on the same 201 windows; `compute_difference_matrices`; `baseline_broadband_stats`; `compute_aligned_condition_coherence` as the junction diagnostic). NEW `src/visualization/connectivity_plots.py`, `scripts/connectivity/diagnostics/demo_coherence_bias.py`, `scripts/connectivity/analysis/analyze_connectivity.py`, `tests/test_p12_coherence.py` and `tests/test_p12_known_answer.py`. Suite: `723 passed, 21 warnings in 362.42s` (`reports/logs/P12/pytest_20261026_151109.log`), about 6 min against the "about a minute" target.

**Data source.** Legacy 7-channel folders `data/processed/S03`, `S04` (P02, OO session), raw windows (continuous 1–60 Hz filter, then cut; R3 era B), fs 250 axis labelled (PF-04), one P07 gate over 101–105 and 201, no channel dropped. Only S03 and S04; descriptive; no p-value.

**Results (`reports/connectivity/coherence_{S03,S04}_summary.csv`; `reports/connectivity/coherence_bias_demo.csv`).** PF-15 reproduced on synthetic data: independent noise 0.3373 per-window averaged against 0.0180 concatenated; coupled 0.9814 / 0.9824. Baseline coherence (201, 5–35 Hz, R-11): S03 0.6836 → 0.5871, S04 0.7291 → 0.6589 (before → after); both drops present. Per-band matched baseline falls in 10 of 10 cells. Prescribed 24/20 Hz differences: S03 +0.2494 / +0.2511, S04 +0.1281 / +0.1105 (all positive, aligned signs also positive). 10.91/8.57 Hz: S03 −0.0366 / +0.0414, S04 +0.1934 / +0.1286. PF-16 changes conclusions: S03 105 is +0.1934 under the broadband baseline and +0.0414 matched; S04 103 is −0.0048 broadband and +0.0554 matched (sign flip); S03 104 is +0.0198 broadband and −0.0366 matched (sign flip).

**Reading.** The baseline and the per-band levels fall as PF-15 predicts. The 24/20 Hz gains are consistent with R-11 in both subjects. The 10.91/8.57 Hz results are recorded as two hypotheses for P13: an alpha-band ceiling (the matched baseline is higher in S03, which shows no gain) and alpha desynchronisation (S03 104 stimulus is below its baseline). Junction leakage (F2) is not material here: S03 105 is flagged in the junction diagnostic (|Δ| = 0.0565), but its sign is opposite to the junction prediction, so it is recorded as **estimator-sensitive**, not junction-biased. The baseline "after" value for S03 (0.5871) and S03 102 (+0.2511) sit just outside R-11's bare edges, inside the ±0.05 descriptive tolerance. The colour scales are per subject (S03 ±0.5084, S04 ±0.3807).

**Review.** Pre-run audit Round 1 FAIL (`84406bc`: R-11 operationalisation, junction bias, labels); amended settled point 2 (`26d0a74`); fixes and tests; Round 2 PASS (`35a1f29`). Verifier PASS (`b68f5eb`). Results review APPROVE (`66f3346`) with D-1 to D-4. No reference consultation.

**Open.** P13 tests the two alpha-band hypotheses with trial-level permutations per band and a baseline-level against difference check across the five subjects; re-checks the aligned junction diagnostic on permuted re-concatenations; and uses one shared colour limit or states that none is shared. The suite runtime is noted, not blocking. Next phase: P13, after the orchestrator's gate.

## P13 — Phase and autoregressive connectivity with permutation statistics

2026-10-26, branch `phase/P13-phase-pdc-permutations`. Code and main run at `7f6cabb`; DIAG-A2 verifier `3865ba6`; results review Round 2 `a010a0d`. Phase report: `mas/state/reports/P13.md`.

**Aim.** Roadmap P13: phase connectivity from the cross-spectral density (PLV, wPLI), PDC from a strided MVAR fit, a trial-level permutation test with observed group sizes and Benjamini-Hochberg over edges, and a cohort run of coherence, PLV, wPLI and PDC for S01–S05. The bugs are reproduced first: PF-17 (contiguous MVAR slicing), PF-18 (filtfilt + Hilbert edges), PF-19 (window-level permutations), PF-20 (criteria A and B merged). Acceptance is R-12, with criterion A and B reported separately [1, 7].

**Build.** NEW `src/features/connectivity/phase_connectivity.py`, `mvar_pdc.py`, `permutation.py`; MODIFIED `connectivity_extraction.py`; NEW `scripts/connectivity/analysis/analyze_connectivity_cohort.py`, `scripts/connectivity/diagnostics/demo_hilbert_edges.py`, `demo_mvar_slicing.py`; NEW `tests/test_p13_connectivity.py` (27) and `tests/test_p13_known_answer.py` (37). Suite: `796 passed, 21 warnings in 363.52s` (`reports/logs/P13/pytest_full.log`), about 6 min against the "about a minute" target.

**Data source.** Legacy 7-channel windows (P02, OO session), raw, fs-250 axis (PF-04), one P07 gate per subject, no channel dropped. Trial ids are exact for S01, S03 and S05 and approximate for S02 and S04 (P11 D-2).

**Results (`reports/connectivity_cohort_summary.csv`; p is the one-tailed global p, FDR is the BH count over one-tailed edge p).** FDR totals per subject, coherence 0 / 0 / 64 / 49 / 12 (R-12 0 / 0 / 65 / 51 / 15), wPLI 4 / 0 / 42 / 28 / 5 (R-12 0 / 3 / 38 / 33 / 18). Nine of ten A2 cells are inside their windows. The S05 wPLI total of 5 is outside 13–23 and is an **accepted deviation** (D-1): the same procedure with bases 1–5 gives 7 / 14 / 12 / 7 / 12, with 10.91 Hz counts 0 / 9 / 0 / 0 / 7 (R-12 13). Only one of six draws is inside the window, and the reported value stays 5. This cell is not reproduced by R-12. The 24 Hz pattern holds (coherence p 0.005 in S03–S05; wPLI 0.005 / 0.005 / 0.040), and S01 and S02 are null at 24 Hz for coherence and wPLI (PDC is outside the acceptance; S01 and S02 PDC 24 Hz p 0.015). S05 wPLI 20 Hz is inconclusive (p 0.065; 0.0498–0.090 across the six draws).

**Reading.** Estimator dependence: S03 coherence at 8.57 Hz has 8 FDR edges concatenated and 0 aligned (p 0.104 and 0.697), labelled estimator-sensitive (not junction-biased) and inconclusive (D-2). Window-level p is no larger than trial-level p in 71 of 100 cells (PF-19); 14 cells change verdict between the two units. Eleven flip-list cells between 100 and 200 permutations are inconclusive, and most are BH resolution (minimum non-zero counts 3 and 5 at 200 and 100 permutations for 21 edges; 5 and 9 for 42 PDC edges). The alpha hypotheses from P12 (D-3): the ceiling is consistent for S03 coherence only, with no cohort support; S03 alpha suppression is not supported; an S05 lower-tail pattern (coherence and PLV below baseline, wPLI above) is an exploratory, uncorrected observation (7 of 40 lower-tail p below 0.05), carried to P14 as a hypothesis. The descriptive baseline–difference correlations are negative by construction.

**Review.** Pre-run audit Round 1 FAIL (`934cc2f`: a run-order gap in the window-versus-trial comparison; the criteria were bound to the acceptance table); Round 2 PASS. Main run: verifier FAIL on A2 (`57e5fbd`). Results review Round 1 REJECT (`cec7dca`), which fixed the DIAG-A2 rule before any run. DIAG-A2 verifier PASS (`3865ba6`); results review Round 2 APPROVE (`a010a0d`) with D-1 to D-4. No reference consultation.

**Open.** For Sebastian, not a blocker: the six S05 wPLI draws have mean 9.5 against R-12's 18, and five lie below the window; whether this lean is chance or systematic is not established. P14 carries the S05 lower-tail pattern as a hypothesis only. Any later phase that grades FDR counts pre-commits a seed-base diagnostic (D-4). Two-tailed p (N1) is not used in any claim. Next phase: P14, after the orchestrator's gate.

## P14 — Cross-frequency comparison, reliability, and power/alpha confounds

2026-10-26, branch `phase/P14-cross-frequency-confounds`. Pipeline at `6b4ec21`; first verifier run `b2478a9` (FAIL, test hygiene); fixes `b4806cc`, `32a649f`; verifier restatement `8356a04` (PASS); results review `878e96e` (APPROVE). Phase report: `mas/state/reports/P14.md`.

**Aim.** Roadmap P14, the professor's follow-up: compare connectivity across stimulation frequencies (delta matrices only; similarity, node strength, global delta, split-half reliability and a pairwise test with trial-level exchange), and test whether the deltas are just SSVEP power or alpha blocking (target SNR and alpha change, O1/Oz/O2). Descriptive at five subjects; R-13 is the qualitative reference [1, 3, 7].

**Build.** NEW `scripts/connectivity/comparison/compare_connectivity_frequencies.py`, `scripts/connectivity/comparison/test_connectivity_frequency_differences.py`, `scripts/connectivity/diagnostics/check_power_alpha_confound.py`, `src/features/connectivity/comparison.py`, `tests/test_p14_connectivity_comparison.py`, `tests/test_p14_known_answer.py`. Outputs: `reports/connectivity_comparison/` (61 CSVs), `outputs/figures/connectivity_comparison/` (21 PNG) [6, 10].

**Run.** Pipeline commands 2–6 took 4053 s, **67.55 min**, against an estimate of 18–34 min (about 2–4 times low), inside the 120 min budget (`reports/logs/P14/cmd2_p500.log`, `cmd3_final.log`) [8, 11]. Suite: the first clean-checkout run failed (`2 failed, 871 passed, 1 skipped`; `pytest_full.log`); the restated suite is `873 passed, 1 skipped, 21 warnings in 405.69s (0:06:45)` (`pytest_full_round2.log`), about 6.7 min against the "about a minute" target [9, 11].

**Results (`reports/connectivity_comparison/`).** Integrity: t_mag identity to 1.94e-16; p500 and final identical in every observed column (A0, A1); 50 pairwise and 25 reliability rows per method (A2). Frequency similarity, Fisher mean r: coherence 0.629 (66 % of pairs p_qap < .05), PLV 0.510, wPLI 0.163 (32 %), PDC 0.480; R-13 0.54 and 0.14. Split-half medians: coherence 0.924, wPLI 0.517 (R-13 0.92 and 0.54). Pairwise counts, p500 / final: coherence p_mag 11 / 10 and p_pat 1 / 1; wPLI 6 / 6 and 2 / 2; PLV 14 / 14 and 2 / 2 (R-13 coherence 6 / 1, wPLI 6 / 2). SNR and alpha tables equal R-13 to two decimals, and the coherence and wPLI global deltas equal R-13 to three decimals. Acceptance question 1: coherence largely explained and SNR-dominated (R² 0.675 all, 0.540 within-subject); PLV and PDC partly explained and SNR-dominated; wPLI explained between subjects only (0.530 all, 0.0014 within-subject); alpha adds little (ΔR² ≤ 0.059). Acceptance question 2: no consistent in-alpha difference for coherence, PLV or wPLI (3 of 5 subjects each sign, raw and SNR-adjusted); PDC differs raw (5 of 5 negative) but this is consistent with its lower SNR (3 of 5 adjusted).

**Reading.** The pairwise exchangeability null is off-centre on real data: its median centre is 0.62–0.79 of the observed |t_mag|, and |z| > 2 in 15–20 of 50 cells per method. Most of each own-band difference is reproduced under exchange, so the difference is band-level, not stimulus-specific. Thirteen cells are "null off-centre" and eight of 150 flips are inconclusive. The S05 pattern from P13 D-3 (coherence and PLV below zero at 10.91 and 8.57 Hz, wPLI above) is an exploratory hypothesis only. Its counter-evidence is S05's in-alpha SNR (1.82 and 2.29 dB, its two lowest) and a 20 Hz coherence delta of +0.006 despite an alpha change of −2.48 dB. Unexplained differences from R-13, reported and not graded: coherence Fisher-mean similarity 0.629 against 0.54 (arithmetic mean 0.535), coherence magnitude count 11 against 6, and two non-positive coherence reliabilities against none.

**Review.** Pre-run audit Round 1 FAIL (`34301f7`: empty test template, pairwise-null labelling, plan bindings); Round 2 PASS (`82255b7`). Verifier first run FAIL (`b2478a9`) on test hygiene: two tests read the git-ignored `reports/n_subjects_benchmark.csv`; the tests-only fix and restatement PASS (`8356a04`). The verifier changed the header verdict line from FAIL to PASS in `8356a04`; the original FAIL is in `b2478a9` and `log.md`. Results review APPROVE (`878e96e`), D-1 to D-5. No reference consultation.

**Open.** For Sebastian, non-blocking: whether R-13 used a Fisher-mean or an arithmetic mean of the similarity r (D-4). Later phases that reuse the pairwise test report `<m>_pairwise_null` alongside the p-value (D-2). Tests must not read generated, git-ignored files (D-5). Next phase: P15, after the orchestrator's gate.

## P15 — Per-window graphs, the connectivity gate, and a GNN

2026-10-27, branch `phase/P15-graph-gnn`. Code at `2392299`; first verifier run `87ed7af` (FAIL, scientific); blocker B007 `60a6ac7`, resolved `79870ad`; results review `5bd9240` (APPROVE); verifier restatement `6e55897` (PASS). Phase report: `mas/state/reports/P15.md`.

**Aim.** Roadmap P15, the professor's assignment: model connectivity with graph neural networks to classify the stimulation frequency. First a gate: do edge features (per-window coherence, phase) add information to node power and FBCCA features? Then a within-subject GNN with node and edge features [1, 7].

**Build.** NEW `src/features/connectivity/connectivity_graph_features.py`, `graph_dataset.py`, `graph_inputs.py`; `src/models/graph/connectivity_gnn.py`; `scripts/connectivity/graph_modeling/build_graph_dataset.py`, `benchmark_connectivity_gate.py`, `benchmark_gnn.py`; tests `test_p15_gnn.py`, `test_p15_graph_features.py`, `test_p15_known_answer.py`. Suite `948 passed, 21 warnings in 432.56s` (`reports/logs/P15/pytest_full.log`), about 7.2 min against "about a minute" (noted, not blocking).

**Data source.** Legacy 7-channel OO windows from `data/processed/<S>/graph_dataset.npz` (stimulus only, two-tier P07 gate), fs 250 legacy (PF-04). Trial ids approximate on S02 and S04 (P11 D-2). The 2.0 s column uses the legacy i%5 rule (R8 legacy-folder clause; P11 C1 open).

**Gate (R-14; `reports/connectivity_gate_benchmark.csv`, 5 repeats).** Reproduced: all 45 subject × set cells at k = 0 within 0.05 pp of R-14 and the nine cohort means within 0.06 pp (Base+Ec 77.57 against R-14's 77.6). The gate does not pass for the pre-committed reason: 0 of 3 responders gain ≥ 2 pp (S03 +1.22, S04 +0.10, S05 −1.70), while S01 (+16.30) and S02 (+3.16) gain. Descriptive heuristic on five subjects, not an inferential test.

**GNN (R-15; `reports/gnn_benchmark.csv`, 3 repeats, CPU).** Within tolerance: 11 of 12 graded subject cells at 1.0 s and 2.0 s, and the 1.0 s cohort cells. **Not reproduced within tolerance, accepted as a documented deviation by Sebastian (B007); cause not established:** nodes+F S02 at 2.0 s, 37.07 % against 46.1 % (Δ −9.03; repeats 37.76 / 34.18 / 39.29 %, 3.45 × SD, so not seed variance), and the nodes+F cohort at 2.0 s it drives (71.27 %, 0.16 pp below the window [71.43, 77.43]). Coherence edges: the cohort Δ at 1.0 s is +1.07 against R-15's −0.40 (per repeat +0.50 / +1.18 / +1.52). The "≈" claim (nodes+F ≈ nodes+coh+F) and the "do not help" claim (Δ < 2 pp; one of three subjects reaches 2 pp) hold. The GNN is below the LDA gate rows on every subject at 1.0 s (S03 76.82 against 82.74; S05 89.50 against 98.90; S02 34.18 against 47.96; S01 34.00 against 41.20).

**Diagnostic.** Train accuracy exceeds R-15 in six of six graded cells (four outside ±5 pp). It is not definitional (the original measures it the same way; reviewer's R11 check). Cause not established: device (the original defaults to CUDA; this run is CPU), RNG stream, and single-split variance. The train–test gap is 37–42 pp on S01 and S02 (PF-30): the GNN memorises training windows there (test 34–37 % against train 71–78 %).

**Review.** Pre-run audit Round 1 FAIL (`2bc973a`, documentation only: the R11 listing understated the original-code access); Round 2 PASS (`1d1bdca`). First verifier run FAIL at `87ed7af` on scientific grounds (the three B007 items). Blocker B007 resolved by Sebastian, option 1 (`79870ad`). Restatement PASS (`6e55897`). Results review APPROVE (`5bd9240`), D-1 to D-6.

**R11.** Two consultations: deep-learning (23:14, `git grep` for the two class declarations and a display of the whole 73-line original file; only `bias=False` adopted) and the reviewer (23:44–23:45, verification of the finished implementation and the train-accuracy question; no code change). Both are in `mas/state/scratch/reference_access.log` and listed in the report.

**Open.** For Sebastian: the train-accuracy cause (device or RNG), if he wants a diagnostic before the Era C GNN work (B007 option 2). Carry-forwards: N1 (the cache fingerprint must cover the FBCCA, gate and trial-id sources when P16 reuses the cache), N4 (two untested mutation cases, at P23). Next phase: P16, after the orchestrator's gate. Sebastian asked to be told when P15 is finished, and to stop after P15.

## P16 — Baseline freeze, edge effects, continuous filtering, 256 Hz, shared quality

2026-10-27 to 2026-10-28, branch `phase/P16-continuous-filtering`. Run state (code) `bb8c999`; first verifier run FAIL at `bd55527` (one criterion: the regression-check exit code); checker fix `9b297c0`; re-verification PASS at `215bf44` (`6bb9b81`); results review APPROVE `928ae8c`. Phase report: `mas/state/reports/P16.md`. The first-run FAIL is kept as the record.

**Aim.** Roadmap P16, from the professor's change list: research edge effects of per-window sub-band filtering; filter the continuous recording before cutting; use only valid windows; and correct the sampling rate from 250 to the recorded 256 Hz [1]. Freeze v1 as the baseline first, then build the Era C data path (window index with true trial ids, continuous zero-phase filtering, one shared quality decision with an artifact guard, fs from metadata, one loader) and port the flagship and the connectivity scripts [1, 2].

**Historical facts (R-16).** The frozen v1, and R-6 with it, used fs = 250 in feature code on 256 Hz recordings, and filtered each FBCCA and FBCSP sub-band per 1 s window [4, 5]. The v2 numbers are the first computed with the real sampling rate (256 Hz, from the recording header) and continuous filtering [4, 8].

**Build.** NEW `scripts/freeze_baseline.py`, `src/preprocessing/windowing.py`, `src/preprocessing/window_quality.py`, `src/io/subject_data.py`, `scripts/build_windows.py`, `scripts/diagnostics/demo_edge_effects.py`, `scripts/diagnostics/compare_v1_v2.py`; MODIFIED `configs/pipeline_config.yaml` (final config), the flagship and connectivity scripts and extractors (`subband_windows=`, `quality=`), and `oof_space` (explicit splits, P11 N1). 18 NEW and 19 MODIFIED files under `src`, `scripts`, `tests`, `configs` (`git diff --name-status main..HEAD`), 37 in all [11]. Full list in the report, §2.

**Data source.** OO session, S01–S05 (B005). Legacy folders `data/processed/<S>/` (7 channels, fs 250, per-script gate); built `data/processed_per_window/<S>/` and `data/processed_continuous/<S>/` (8-channel montage; tier 1 dropped PO7 on S01, S03, S04; fs 256 from the header; true trial ids) [8, 10].

**Snapshot and regression.** `baselines/v1_2026-10-27/` read-only, 407 files equal to the pre-run hash list; a repeated tag refuses [9]. The v1 regression is exact: the flagship row at seed 42 equals R-6 per subject (S01 61.00 / 67.50 … S05 95.00 / 95.50; mean 79.28 / 82.61), `reports/n_subjects_benchmark_v1check.csv` byte-equal to the frozen file, and the connectivity cohort summary, details and alpha diagnostic byte-equal [8, 9]. The first run failed `--check-regression` on the 15 NaN-diagonal npz files (plain `array_equal`; a checker defect). The data were equal throughout; the checker was fixed in `9b297c0` (NaN compared at aligned positions only) and re-run: 20/20 npz equal, exit 0 [8, 9].

**Edge effects (S03; `reports/edge_effects_summary.csv`).** The pre-committed criterion (ratio ≥ 5 and edge error ≥ 20 % for 7–12, 13–17 and 18–26 Hz) is **met**: ratios 8.17, 7.45 and 21.00, with edge errors 53.24 %, 56.68 % and 33.10 % against centre errors 6.51 %, 7.60 % and 1.58 %. The order-of-magnitude reading (ratio ≥ 10) is **not** met for 7–12 and 13–17 Hz, and the report says so [8].

**Legacy starts.** `build_windows --check-legacy-starts` (both builds): 70 of 70 lines `n_legacy = n_built = n_equal`, `max|d| 0` [8]. Trial ids: 39 of 199 (S02) and 38 of 198 (S04) stimulus windows are in inconsistent legacy groups, as in P11 D-2; the other subjects have none [8]. The P02 carry-forward is closed: the S03 first-trial PO8 rejections are genuine amplitude (mean Vpp PO8 325.4 µV), not a filter start-up transient [6, 8].

**Flagship (R9; `reports/v1_vs_v2/flagship.csv`, five seeds 42–46).** Cohort means, 1.0 s / 2.0 s: a (legacy, fs 250) 80.80 / 84.42; a′ (fs 256) 88.84 / 91.33; a′t (trial reset, legacy) 88.84 / 90.70; b (per_window build) 87.01 / 89.12; c (continuous, shared gate with guard, the headline v2) 87.38 / 89.07; c′ (no guard) 88.38 / 89.83. Per subject, c at 1.0 s: S01 72.80, S02 72.42, S03 93.61, S04 99.49, S05 98.59 [9, 10].

**Decomposition (c − v1 frozen = +8.10 / +6.46 pp; `.venv/bin/python -c "print(round(87.38-79.28,2), round(89.07-82.61,2))"`).** The fs correction is the one material positive step: a′ − a = +8.04 / +6.91 pp, positive in every subject at 1.0 s and largest where the legacy accuracy is lowest (S02 +18.47, S01 +11.30; S04 +1.22). The v1 frozen run is one seed; the five-seed row a is +1.52 / +1.81 pp above it, which is seed sampling, not pipeline. The other steps are: build b − a′ −1.83 / −1.58 (only S02 is material, −8.03 / −7.79: restored PO7, removal of the approximate-id leak, and six fewer clean windows, not separated); filter mode c − b +0.37 / −0.05 (no material change); smoothing rule a′t − a′ −0.63 at 2.0 s (the legacy `i % 5` misalignment after rejected windows; S01 and S05 exactly 0.00); guard c − c′ −1.00 / −0.76 (only S02 at 1.0 s, −4.50, material; cause not established; the direct test-window bound is 0.71 pp) [9, 7]. **Filtering does not improve accuracy here, and neither does the guard.** Continuous filtering is the correct signal path (R3); its accuracy effect is nil. The guard is kept as the shared default for signal validity (PF-14), not for accuracy [7].

**Connectivity (`reports/v1_vs_v2/connectivity.csv`, 100 rows).** Mean Δobs_diff fs (a′ − a): coherence −0.0079, PLV −0.0063, wPLI −0.0126, PDC −0.0002; the reviewer's dilution and alpha-bin predictions hold at coherence 101–104 Hz [9, 7]. The 35 identity cells give identical p and FDR counts, and obs_diff differs by at most 2.44e-16 (round-off, D-2). Filter mode is "not applicable (same input)" for connectivity (decisions row 133). Five global-p crossings at 0.05 (one fs, four build) are inconclusive under R7. FDR counts are given as fractions of total edges wherever the channel set differs (N1) [10].

**Review.** Pre-run audit Round 1 FAIL (`58c578c`, six fixes: cv_groups by overlap, explicit R5 thresholds, connectivity a′ row, flagship a′t row, wider regression check, a complete run list); Round 2 PASS (`fe71ffa`); post-verify Round 2 PASS (`645312e`). Results review APPROVE (`928ae8c`), D-1 to D-8, C-1 to C-5 [7, 5].

**R11.** None. The builders and the tester report no consultation; the verifier found no entry dated 2026-10-27 or later in `mas/state/scratch/reference_access.log` [6, 9].

**Open.** Carry-forwards for P17 onward: C-1 (freeze skips the redundant `Mean` row for later tags), C-2 (remove the script-local threshold fallback in `benchmark_n_subjects`, label `per_window` builds legacy, forbid or document `--fs` on built roots), C-3 (optional labelled S02 build diagnostic), C-4 (show c′ beside c for S02; FDR as fractions when channel sets differ), C-5 (the P17 rest class uses 201 windows only). Merge per `MERGE_POLICY: orchestrator`. B003 is non-blocking and to be decided before P20.

## P17 — Sixth (rest) class and harmonic / intermediate filter bank

2026-10-28. Branch `phase/P17-rest-class-filterbank`; run state `59b0f10`; verifier PASS `d7daf81`; results review APPROVE `1eeff88`; decisions `471c6a2`. Phase report: `mas/state/reports/P17.md`.

**Aim.** Roadmap P17 [1]: add the fixation cross (201) as a sixth class, and add narrow harmonic (k·f, k = 1..3) and intermediate (midpoint) bands to the filter bank. Evaluate `base` (five FBCSP bands), `harm` and `harm+mid` with 5 and 6 classes over ten CV repeats [1, 2].

**Data source.** OO session, S01–S05 (B005). Continuous build `data/processed_continuous_p17/<S>/` (four banks, fs 256 from the header, guard `auto` 1.046875 s = 268 samples, shared quality) [5, 8]. The guard moved from 0.902 s because the order-2 narrow bands ring to 1.047 s, so the rebuild went to a new root and the P16 root `data/processed_continuous/` stayed unchanged (65 files, hash `c59c94b8…a54e`, equal before and after) [3, 5, 8].

**Result (cohort means, S01–S05, 10 repeats; `reports/n_subjects_benchmark_p17_*_5class.csv`, `reports/n_subjects_benchmark_p17_*_6class.csv`).** 5 classes, 1.0 s / 2.0 s: base 87.65 / 89.57, harm 94.29 / 95.80, harm+mid 94.23 / 95.45. The `harm` gain is material on S01 (+12.35 / +12.60 pp) and S02 (+13.69 / +11.53 pp) and small at ceiling on S04 and S05. `harm+mid` ties `harm` everywhere [7, 8]. The gain is worded "consistent with an SNR gain of the ±1 Hz bands at k·f, fundamentals included". The bank includes the five fundamentals, so no gain is attributed to harmonics alone (C-d) [7].

**Six classes.** Stimulus and rest (chance 16.7 %), not comparable with five-class accuracy. The like-for-like check is StimCorrect(6) against Smoothed(5) at 2.0 s: StimCorrect(6) is below Smoothed(5) in 15 of 15 cells [7, 8]. The narrow banks mainly reduce false activations on S01 and S02 (FalseAct 2.0 s, base → harm: 22.00 → 7.12 %, 16.08 → 3.24 %); Missed rises on S01 (14.25 → 20.00 %) [8].

**Refuted a-priori directions.** P4 for base (S01 FalseAct 22.00 > Missed 14.25); "loss ≈ Missed" on S01 and S02; P1's S05 tie (small positive, no claim). The 6-class BalAcc gain is material on S01 and S02 only, so no cohort claim is made [7].

**Gates.** G1 (leak controls, 1166 passed) met; G2 (D0 25 of 25 equal, D1 gap 2.969 s, D2 non-guard identical) met; G3 and G4 met (not triggered) [7, 9, 10]. Synthetic leak controls: null recording at chance (base 20.00 / 20.83 %, bound 31.3 %), carry-over ≤ 6.5e-6 at the protocol spacing, tone at 2·f0 found by `harm` only [4].

**Caveats.** Uniform priors push errors toward FalseAct (not isolated by a run). The harm Missed 20.00 % on S01 and S02 is a count coincidence (400 of 2000, 380 of 1900). The S04 mask change is one rest and one cue window (`05_run.md:64` corrected in D-5). The 5-class base at 10 repeats is 0.27 / 0.50 pp above P16 row c at 5 repeats, a repeat-count effect [7, 8].

**R11.** None. Zero reference-access lines dated 2026-10-28 [9].

**Open.** Carry-forwards C-a (refuse overwrite of built folders with different `build_params`; open), C-b (`fail_fraction` required), C-c (6-class console line), C-d (fundamentals-only ablation), C-e (per-offset Missed/FalseAct). One skipped test is not identified in the run log. Merge per `MERGE_POLICY: orchestrator`.

## P18 — Network-Based Statistic (NBS) beside edge-wise FDR

2026-10-28. Branch `phase/P18-nbs`; run state `32738cc`; verifier PASS `b96d5df`; results review APPROVE `3db9410`; decisions `c8a894b`. Phase report: `mas/state/reports/P18.md`.

**Aim.** Roadmap P18 [1]: a graph-based statistic (Network-Based Statistic) next to edge-wise FDR in the cohort and between-frequency connectivity tests, and a comparison of significant-graph sizes across subjects and frequencies [1, 2]. FDR is kept and saved beside NBS (settled point 3 [2]).

**Data source.** OO session, S01–S05. Continuous build `data/processed_continuous/<S>/` (P16 root; guard 0.902 s; shared quality; fs 256.0 from metadata; true trial ids). The root is unchanged (65 files, hash `c59c94b8…a54e`, equal before and after) [5, 9, 10]. Responders from `reports/n_subjects_benchmark_v2cont.csv` (PF-21) [11].

**Result (cohort, 1000 permutations; 100 cells = 5 subjects × 4 methods × 5 frequencies; `reports/connectivity_cohort_summary_p18_nbs.csv`).** Cells with A-FDR (at least one edge), A-NBS (p < 0.05) and B (global p < 0.05): 48, 43, 32. NBS-positive cells: S03 16, S04 18, S05 8, S01 1, S02 0. Mean largest component, % of possible edges: S03 38.8, S04 32.1, S05 12.1, S01 2.6, S02 1.6 (`reports/connectivity_graph_size_p18_nbs.csv`) [9].

**Graph sizes across frequencies.** Mean over subjects and methods: 26.4 % at 24 Hz, 19.1 % at 20 Hz, 13.0 % at 15 Hz, 13.9 % at 10.91 Hz, 14.8 % at 8.57 Hz. The alpha-band prediction holds for the means of coherence and PLV only; wPLI is high at 10.91 and 8.57 Hz [9].

**Checks.** V0–V8 met. The 200-permutation FDR columns, global p and edge arrays equal P16 `v2cont` (15 of 15 columns, max abs diff 0) [9, 10]. P18 tests: 17 + 21 = 38; suite `1204 passed, 1 skipped` [3, 4, 10].

**R7.** Seventeen cells flip between 200 and 1000 permutations (A-FDR 14, A-NBS 6, B 0); all are inconclusive. Eleven A-FDR flips are BH-resolution-limited, three are Monte Carlo flips. All six A-NBS flips are threshold-boundary; none is p-resolution [9, 10].

**P2 refuted.** A-NBS 43 < A-FDR 48 at 1000 permutations: 9 FDR-only and 4 NBS-only cells. Neither criterion is uniformly more sensitive [7, 9].

**Pairwise (1000 permutations; first run on the continuous build).** NBS p < 0.05 in 8 / 14 / 6 of 50 cells (coherence / PLV / wPLI), against 11 / 8 / 7 for `p_mag`. Read as an excess beyond the per-edge exchange-null centre, not as a test of Δa = Δb (R3). 26 of 28 NBS-positive cells involve 10.91 or 8.57 Hz; exploratory (D-6) [7, 9, 10].

**R11.** None. Zero reference-access lines dated 2026-10-28 [14].

**Open.** Carry-forwards C-1 (`p_mag_centred` in the pairwise CSV), C-2 (pairwise group labels as edge counts), C-3 (flip sizes), C-4 (lower-tailed NBS, option) and C-5 (second pairwise permutation count before any R7 claim on pairwise tests) are open; C-6 is applied in the report. One skipped test is not identified in the run log. Merge pending, by the orchestrator.

## P19 — Quality check on the raw segmented signal

2026-10-28. Branch `phase/P19-raw-quality`; run state `2994599`; verifier PASS `20ab583`; results review APPROVE `5be0674`; decisions `b5d8e3f`. Phase report: `mas/state/reports/P19.md`.

**Aim.** Roadmap P19 [1]: check the limits also on unfiltered windows cut at the same positions, so that a window or channel must pass on every checked signal. `quality.source` is `filtered`, `raw` or `both`; reason 3 marks raw-only failures; the config default becomes `both` [1, 2].

**Data source.** OO session, S01–S05. Continuous builds `data/processed_continuous_p17` (filtered reference, 75 files, hash `c0e9ba84…d342d`), `data/processed_continuous_p19_raw` and `data/processed_continuous_p19_both` (generated). The P16 root `data/processed_continuous` (65 files, hash `c6e72a79…2aec`) is unchanged before and after [5, 6, 10]. Flagship: 5-class base and harm, `--cv-repeats 10`, `reports/n_subjects_benchmark_p19_*` [9].

**Result (rejections, 320 windows per subject; `reports/logs/P19/12_tables.txt`).** Rejected windows of 1600: filtered 43, both 44, raw 44. Reason 3 under `raw` is 0 / 19 / 11 / 13 / 1 for S01–S05. Under `both` it is one window cohort-wide (S03 row 160, label 102, raw gate). `raw` is different from `filtered`, not stricter [7, 10].

**Flagship (1.0 s / 2.0 s, `both` vs `filtered`).** No cell is material. S03 base Δ −0.24 / −0.09 pp (thresholds 2.40 / 2.32 pp) is split variation from a changed fold partition, not an effect of the raw check (D-1). All other rows are identical [7, 9, 10].

**Checks.** A–F met. `p19_filtered` equals the P17 folder file by file, and the CSVs are byte-identical (`CMP_IDENTICAL`). Suite `1231 passed`, no skipped test (`reports/logs/P19/01_pytest.log`) [6, 10].

**Null wording (amended, D-3).** "filtering hid one borderline window (S03 row 160; PO4 119.4 vs 121.9 µV, limit 120) that these limits detect, and nothing else." The PO4 values are the review's read-only check, not in `reports/` [7, 8].

**R11.** One verifier metadata listing of the read-only answer-key directory, with no content read; disclosed and not an R11 consultation (D-2) [5, 7]. The access log has 41 lines in total, one dated 2026-10-28 [12].

**Open.** C-1 (`scripts/diagnostics/demo_edge_effects.py` now inherits `both`), C-2 (`src/io/subject_data.py:202` raw count needs `& ~keep_local` and a test) and C-3 (P20 build commands name `--quality-source`) are open. C-4 is closed (the raw guard reuses the filters' ringing time, a design choice under PF-14). Blocker B003 is due before P20. Merge pending, by the orchestrator, who also deletes the scratch build `mas/state/scratch/p19_filtered`.

## P20 — Detection: window length, ITR, CCNN, NN sweep, dynamic stopping, pseudo-online

2026-10-28. Branch `phase/P20-detection-online`; run state `5d9326d`; verifier PASS `8fd6cb0`; results review ACCEPT `1ec3c01`; decisions `f9e049e`. Phase report: `mas/state/reports/P20.md`.

**Aim.** Roadmap P20 [1]: treat SSVEP as a detection problem. Accuracy and window-level ITR against window length (0.5–4 s, stride 0.25 s) for FBCCA, in-fold FBCSP+FBCCA LDA and a CNN (`compact_eegnet`); a 1 s comparison of `ccnn`, `compact_eegnet` and `eegnet` under grouped early stopping; dynamic stopping on the window probabilities; a causal pseudo-online detector trained on OO and replayed on mOO at 5 and 6 classes [1, 2]. No numeric target exists (R-16) [2].

**Data source.** OO session, S01–S05 (B003: both options coincide, so S01–S05 are used; B003 stays open [2, 15]). Continuous builds `data/processed_continuous/w<L>_s0.25/` for L = 0.5–4 s, `--quality-source both` [10, 11]. Channels kept: 7 on S01, S03, S04 and 8 on S02, S05, identical at all lengths [10]. Protected root `data/processed_continuous/S0*` (65 files, hash `c6e72a79…2aec`) unchanged before and after [10].

**Result (sweep, cohort mean Acc / window-level ITR, `reports/window_sweep/summary.csv`).** lda 81.80 → 98.03 % and 84.37 → 28.93 bits/min from 0.5 to 4 s; fbcca 69.16 → 96.86 %. The window-level ITR is highest at 0.5 s for all three methods (fbcca 57.50, lda 84.37, cnn 87.25 bits/min) [11]. The cnn cohort value at 4 s (83.10 %) is driven by S02 (39.56 %) and S01 (77.00 %). Two S02 folds at 0.5 s and two at 4 s restored an early-stopping state from epoch 1–3; these single-repeat cells measure an early-stopping failure on S02, not the network's accuracy at those lengths [9, 10].

**Result (1 s networks, `reports/nn_sweep/summary.csv`).** Cohort mean Acc: ccnn 91.25 %, compact_eegnet 92.08 %, eegnet 89.69 %. All differences are below 3 pp: not distinguishable (single repeat) [12].

**Result (dynamic stopping, `reports/dynamic_stopping/best_threshold.csv`).** Thresholds are selected in-sample and are descriptive. lda reaches 61.53 bits/min at 0.5 s against 60.23 for the time-matched single window; the per-subject split is mixed (S04 negative) and several thresholds sit on the grid edge [9, 13].

**Result (pseudo-online, `reports/pseudo_online/summary_ccnn_{5class,6class}.csv`).** Mean accuracy 89.00 % (5 classes) and 74.00 % (6 classes); mean false activations 27.5 % → 5.0 %. The 6-class drop is missed stimulus periods in S01 (50.00 %) and S02 (52.50 %), and the 6-class ITR uses N = 5 [14].

**Checks.** A–I met; acceptance 1–7 met; causal-filter test `PASSED`; protected hashes unchanged; all six cnn windows ran locally (phase commands 80.95 min; GPU 1.30 h; stop rule S: 84.53 ≤ 120) [7–10]. Suite: first run `2 failed, 1295 passed` (two P09/P10 hash-pinned tests, explained by the intra-op thread count, not P20 code); isolated re-run `1297 passed` [8, 9, 10].

**Directions (P1–P6).** P1, P2, P3 (fbcca and lda), P4, P5 (cohort means), P6(b) and P6(c) hold. P6(a) fails as worded (S04 0.0 vs 0.0, floor). P1 cnn endpoints hold but are uninformative about window length [9].

**R11.** None; the access log has no P20 entry [19].

**Open.** B003 must be resolved before P21 opens. Carry-forwards C-1 (hash-pinned tests pin the thread count), C-2 (deep-learning flags folds with restored epoch ≤ 5 or train accuracy below chance + 10 pp; 4 folds flagged in P20), C-3 (≥ 3 repeats before interpreting a single CNN cell that moves a cohort by > 5 pp) and C-5 (P17 C-d, C-e) are open [9]. Merge pending, by the orchestrator.
