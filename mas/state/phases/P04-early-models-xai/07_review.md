# P04 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Opened in this run: `00_assignment.md`, `02_plan.md`, `03_changes_ml-engineer.md`,
`03_changes_deep-learning.md`, `04_tests.md`, `log.md`, decisions.md P02–P04 rows,
`mas/RULES.md`, `mas/01_DATA_SPEC.md` §5.1/§6, `mas/02_REQUIREMENTS.md` §2/§4–§6,
`mas/04_REFERENCE_RESULTS.md` R-2/R-8, B004, `mas/05_PITFALLS.md` PF-01/02/04/06/11/14/28/30,
and every changed file in `git diff --stat main..HEAD` (22 files). P04 tests re-run:
`.venv/bin/python -m pytest tests/test_p04_early_models_known_answer.py tests/test_p04_cnn_smoke.py tests/test_p04_ml_smoke.py -o addopts="" -q`
→ `38 passed, 10 warnings in 55.65s`.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) — the prescribed `StratifiedKFold(5, shuffle, 42)` over windows, labelled in code, console, CSV `cv` column and figure titles; LDA/sklearn and CNN use identical splits (codes vs 0..4 indices are order-preserving encodings) | `scripts/training/train_models.py:231-233`, `:78`, `:294`, `:321`; `src/models/cnn/spatial_spectral_cnn.py:135`, `:149`; test `test_legacy_cv_splits_equal_stratified_kfold_5_true_42` + seed mutant |
| R2 Fit only in-fold | PASS for every CV number: each classifier is a cloned `Pipeline(StandardScaler, clf)` fitted on the training fold (`:218-228`, `:245-248`); CNN per-branch scalers on `X[tr]` only (`spatial_spectral_cnn.py:137-139`); fixed 140 epochs, no early stopping, no validation split, no model selection on test folds (`:96-117`); MLP has `early_stopping` off (default), SVC Platt CV runs inside the training fold. Harmonic PSD and FBCCA are per-window, unsupervised, no cross-window fit (`train_models.py:106-179`). LEGACY (by design) R2 exception: full-data scaler + LDA and full-data CNN only for export/XAI, labelled `FIT_LABEL` in the bundles, console and figure captions; CNN full-fit accuracy printed as "not a test score" | `train_final_model.py:60-64`, `:85-105`; `train_models.py:80`; `run_xai.py:61-63`, `:136-138`; tests `test_in_fold_scaling_matches_hand_per_fold`, `test_cnn_scalers_fitted_on_training_fold_only` + leaked-scaler mutants |
| R3 Filter continuous, then window | LEGACY (by design) — FBCCA `filtfilt` on each 256-sample window (PF-14), added to P04 legacy flags in decisions.md; docstring and console say so. `filtfilt` padlen 21 < 256, so no crash path | `train_models.py:142-156`, `:360`; `train_final_model.py:131-132` |
| R4 Estimator small-sample bias | N/A — no coherence/PLV in P04 | — |
| R5 Shared quality decision, explicit thresholds | N/A here (no gate re-run in P04; P02 per-script gate is LEGACY, decisions.md P02 (d)). `batch_run_subjects` calls `run_preprocessing` only for a missing subject; all five P02 folders exist, so the path should not trigger (verifier checks the log) | `batch_run_subjects.py:45-56` |
| R6 Index layouts verified | PASS — `(n, 7, 31)` channel-major reshape matches 01_DATA_SPEC §5.1; kept bins 4, 6, 10, 12, 15, 17, 19, 25 = 9, 11, 15, 17, 20, 22, 24, 30 Hz (re-derived with `.venv/bin/python`); feature `8r + c`; CNN tensor `(n,1,4,8)` with conv (4,1) over channels and (1,3) over bins (8−3+1 = 6 → `32·6`); XAI `coef_[:, :32].reshape(5,4,8)` same order; feature names built in the same order. Each has a known-answer test and a frequency-major mutant | `train_models.py:96-120`; `spatial_spectral_cnn.py:65-69`, `:42-45`; `run_xai.py:48-54`; `train_final_model.py:53-57`; tests rows 1–6, 26–27 of 04_tests.md |
| R7 Honest statistics | N/A — no permutation statistics in P04 | — |
| R8 Smoothing respects trials | LEGACY (by design) — 2-window causal average over array order with no reset, for sklearn and CNN (single implementation reused), labelled in docstrings, console and CSV `smoothing` column. Pinned by a test that fails on the trial-aware (`j % 5`) variant | `train_models.py:252-271`, `:79`, `:295`; `spatial_spectral_cnn.py:152-156`; tests `test_smoothing_legacy_no_reset`, `test_mutant_trial_aware_smoothing_fails`, `test_cnn_temporal_smoothing_is_legacy` |
| R9 Per-subject reporting with data source | PASS — per-subject CSV and console rows with 1.0 s and smoothed accuracy and per-class recall; batch CSV has a `Data source` column; console header states legacy folders, OO session, stimulus-only. CONCERN (minor): the batch `Data source` string echoes `--paradigm` without checking which session produced existing arrays (`batch_run_subjects.py:68`); harmless with the plan's `OO.ebr` | `train_models.py:356-361`, `:386-393`; `batch_run_subjects.py:68-76` |
| R10 Every change and test cites a source that exists and says what is claimed | PASS — handoffs cite 03_ROADMAP P04, R-8, B004, PF ids, decisions.md; spot-checked R-8 (10,005, conv `bias=False`), PF-28 (seed 42 + fold before model, seeded generator) and decisions.md P04 rows — they say what is claimed | `03_changes_*.md`; `mas/04_REFERENCE_RESULTS.md` R-8 |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A — both builders state nothing adapted; no external code pattern found in the diff | `03_changes_ml-engineer.md` "Differences", `03_changes_deep-learning.md` "Deviations" |
| R11 Reference consulted only after an attempt, every consultation listed | PASS — no P04 agent lists a consultation and the access log has no entry between P04 open (54cdf48, 21:47) and now; the last entries (21:27:47–48, agent `main`, the original's README) precede P04 and are the orchestrator's, to be listed in its own log, not a P04 builder access | `mas/state/scratch/` access log tail; `log.md` "Reference consultations" column |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS — every legacy behaviour sits behind a named function/constant (`legacy_cv`, `smooth_probabilities_legacy`, `LEGACY_FS_HZ` default, per-window FBCCA) that P11/P16 can keep beside the fixed versions | `train_models.py:142`, `:231`, `:252`; `src/features/ssvep/spectral_power.py:18` |
| Tests cover every change; at least one fails on the historical bug | PASS — PF-01/PF-02/PF-04 are reproduced, not fixed; their tests pin the legacy behaviour and fail on the fixed variant (seed-0 CV, trial-aware smoothing, fs 256 default), plus leaked-scaler, conv-bias (10,053) and reshape mutants. CONCERN (test strength, non-blocking): (a) `test_cnn_cv_deterministic_and_seed_sensitive` changes the CV split together with the seed, so a "seed once globally" or "seed without `+ fold`" variant also passes; PF-28 per-fold seeding is confirmed by inspection only (`spatial_spectral_cnn.py:99`, `:104`, `:140`); (b) FBCCA tests check ranking/bounds/fs only: a `w·r` (instead of `w·r²`) score, a wrong high cut or missing cos columns would still rank correctly — confirmed correct by inspection (`train_models.py:133-167`); (c) the missing-arrays branch of `batch_run_subjects` is untested (would read recordings) | `tests/test_p04_early_models_known_answer.py:123-171`, `:251-305`, `:333-338`, `:363-371`, `:418-446` |
| Changes match 02_plan.md and the roadmap tasks | PASS with notes — FBCCA: 3 order-3 Butterworth bands [6/14/22, 55] Hz, harmonics `min(3, 55 // f)` = 2, 2, 3, 3, 3, `t = arange(T)/fs`, sklearn `CCA(n_components=1)`, r of the first canonical pair, score `Σ w_b r_b²`, `w_b` = 1.25, 0.6704, 0.5033 (re-derived), all 7 channels (decisions.md P04); classifier settings = decisions.md; `DualBranchFusionCNN` = roadmap P04.2 layer by layer, 10,005 parameters re-counted by instantiation; training = AdamW 1e-3/1e-2, cosine `T_max=epochs`, label smoothing 0.1, batch 16, 140 epochs default; exports carry the P04.3 keys. Deviations judged in the notes below (none blocking) | `train_models.py:70-77`, `:123-168`, `:218-228`; `spatial_spectral_cnn.py:37-52`, `:96-117`; `train_final_model.py:73-105` |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS — `git ls-files` has no data, recording, local-tooling, answer-key, `outputs/` or `reports/` paths; `git grep -i` on HEAD and `git log main..HEAD` messages (12 commits) with fragment-built vendor/assistant/co-author patterns: 0 hits | shown commands in this run |

### Required fixes

None (no FAIL).

### Non-blocking notes

1. **src → scripts lazy imports (judged, CONCERN).** `src/models/cnn/spatial_spectral_cnn.py:67` and `:154` import `scripts.training.train_models` inside two functions. It works (scripts are packages, every entry point puts the root on `sys.path`) and it avoids a second copy of the harmonic-bin/smoothing code, which would be a worse R6 risk; the roadmap itself places `extract_harmonic_features` in `train_models.py`. But it inverts the layering of 02_REQUIREMENTS §2 (library depending on a CLI module) and importing `train_models` has process-wide side effects (`sys.path` insert `:46`, global `warnings.filterwarnings` `:64`), against §4 "no side effects at import" for library code. Acceptable for P04; recommended for the phase that next touches these helpers (P05 or P11): move `extract_harmonic_features`, `harmonic_bin_indices`, `smooth_probabilities_legacy` into `src/` and re-export them from `train_models.py` (signatures unchanged).
2. **Extra CSV columns / joblib keys (accepted).** The four R-2 columns lead the CSV exactly (`train_models.py:291-295`, test asserts); extra columns are appended, the joblib/`.pt` dicts are supersets of P04.3. File name is `S01_model_evaluation.csv` (roadmap `<subject>`); R-2 mentions the original's lowercase `s01_…` — record as a naming note in the report, not a deviation.
3. **Six confusion matrices (accepted).** The roadmap says "per model" over six models; R-2 lists five saved by the original (no Logistic Regression). The report should say the LR matrix is extra relative to R-2.
4. **Docstring vs code (ml-engineer, cosmetic).** `scripts/xai/compare_subject_xai.py:6` says "Colour scale shared by all panels", but FBCCA panels use their own scale (`:52`). Fix the docstring when next touched; the scribe must describe the figure as code does (spatial panels shared across subjects, FBCCA panels own shared scale).
5. **02_REQUIREMENTS §4 CLI (CONCERN).** No `--seed` in the training scripts (seed fixed at 42) and `train_models` takes `--subject/--all` (decisions.md) rather than `--subjects`. Fine for reproducing the reference run; add `--seed` when P08–P10 A/B comparisons need it.
6. **Device.** CPU and CUDA give different but individually deterministic numbers; decisions.md fixes the verifier on `--device cpu`. Defaults are `auto`, so the flag must be passed explicitly in both CNN commands.

### Run commands for the verifier (from the clean checkout, CPU)

```bash
.venv/bin/python -m scripts.training.train_models --all
.venv/bin/python -m scripts.training.train_final_model --subject S01 --device cpu
.venv/bin/python -m scripts.training.train_final_model --subject S04 --device cpu
.venv/bin/python -m scripts.training.batch_run_subjects --subjects S01 S02 S03 S04 S05 --paradigm OO.ebr --device cpu
.venv/bin/python -m scripts.xai.run_xai --subject S04
.venv/bin/python -m scripts.xai.compare_subject_xai
.venv/bin/python -c "from src.models.cnn.spatial_spectral_cnn import DualBranchFusionCNN, count_parameters; print(count_parameters(DualBranchFusionCNN()))"
```

Default `--epochs 140` (never pass a smaller value in the acceptance run). Order matters:
`compare_subject_xai` needs both joblib files. Runtime estimate (builders' CPU timings,
`.venv/bin/python` shown in this run): CNN CV 5 × 73.7 s = 6.14 min, + 2 full fits ≈ 6.81
min, + FBCCA/LDA in four scripts ≈ 8.97 min total — far inside `LOCAL_RUN_BUDGET_MIN` 120;
no human run needed. Expected outputs: `outputs/reports/S0{1..5}_model_evaluation.csv`,
`outputs/reports/batch_run_subjects.csv`, 6 `cm_*.png` per subject under
`outputs/figures/confusion_matrices/<S>/` plus 6 at the root (S01),
`outputs/figures/xai_heatmaps/{xai_spatial_spectral_weights,xai_fbcca_weights,compare_S01_S04}.png`,
`outputs/models/{S01,S04}_{shrinkage_lda.joblib,fusion_cnn.pt}`; parameter print `10005`.
The batch log must contain no "arrays missing, running run_preprocessing" line (P02 arrays
exist; otherwise recordings were re-read and the arrays may differ — anomaly).

### Pre-committed checks for the results review

1. **Leaky-CV / no-reset note (acceptance).** Every P04 accuracy is labelled leaky (R1/PF-01, window-level StratifiedKFold) and its smoothing no-reset (R8/PF-02); none is compared with R-6 as an equal. R-6 is used only diagnostically: leaky ≥ R-6 is expected; S01/S02 far above R-6 (61.00/56.12 % at 1.0 s) is read as leakage (decisions.md P03: no clear SSVEP peaks), not as signal.
2. **Smoothing reading.** Legacy arrays are ordered by condition, then time (01_DATA_SPEC §5.1), so the no-reset average crosses about 39 trial boundaries per subject of which only 4 are class changes; it mostly averages with a same-class window of another trial. A smoothed gain is therefore partly label-order leakage; the report states this and does not call it a 2 s decision gain.
3. **Train vs test (PF-30).** For each subject, `CNN train acc` (eval mode, training fold) next to `CNN 1.0 s`. High train + high test on weak responders = trial leakage suspect; high train + near-chance test = generalization problem; low train = optimization problem. The full-data `.pt` `train_accuracy` is never quoted as a test score.
4. **Consistency.** `batch_run_subjects.csv` `LDA 1.0 s`/`LDA smoothed` must equal the Shrinkage-LDA rows of `<S>_model_evaluation.csv` exactly (same splits, same fits); any difference is a bug. Window counts must equal R-1 stimulus counts (200/199/200/198/200, decisions.md P02).
5. **FBCCA under fs 250 (PF-04).** References run at f·256/250 in data time: mismatch 0.576/0.48/0.36/0.262/0.206 Hz at h = 1 and 1.152/0.96/0.72/0.524/0.411 Hz at h = 2 (shown command). Over a 1 s window the 101/102 second harmonics drift by about one cycle, so a weaker FBCCA contribution for 101/102 is expected and is not tuned away (golden rule 5).
6. **XAI reading (descriptive only).** Full-data fit; weights are on z-scored features and describe the fit, not generalization. For S04 I will check, per class, whether the largest positive spatial weight lies on a bin of the class's own f0/2f0 (9/11/15/17/20/22/24/30 Hz mapping) and report the count; S01 diffuse or alpha-centred is the expected low-SNR picture. No acceptance depends on it.
7. **Numbers.** Every number in 05/06 and the report traced to a log under `reports/logs/P04/` or a CSV; device `cpu` and the commit stated.

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
