# P11 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md (R1, R8, era matrix), mas/01_DATA_SPEC.md (legacy layout, lines 170–190), mas/02_REQUIREMENTS.md §5–§7, mas/04_REFERENCE_RESULTS.md R-5, R-6, R-7, R-9 and tolerances, mas/05_PITFALLS.md PF-01–PF-04, PF-28–PF-31, decisions.md P05–P10 rows, mas/state/reports/P06.md §9 item 3, P10.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Replace the window-level `StratifiedKFold` by `StratifiedGroupKFold(5, shuffle, 42)` over
reconstructed trial ids in the nine benchmark scripts, make the 2.0 s smoothing respect
trials, show the size of the leak per subject, and reproduce R-6 (flagship) and R-9b / R-7
(network A/B) under the leak-free protocol.

## Data source

Legacy 7-channel `data/processed/<S>/` (P02, OO), S01–S05, stimulus windows (101–105),
P07 two-tier gate applied per script (vpp 5–120 µV, std 1–35 µV, channel fail > 50 %),
fs 250 in features (legacy, PF-04). No preprocessing is run; the legacy arrays are not
regenerated (D0 sha256 guard).

## Scope

**In:** P11.1–P11.5; grouped inner splits where a script has one (PF-01); trial-aware
smoothing (R8). **Out:** built folders and true trial ids (P16); fs fix (P16); the shared
quality decision (P16). Scripts not in the roadmap's list of nine (`benchmark_5_subjects`,
`train_models`, `test_sklearn_models`, `batch_run_subjects`, `spatial_spectral_cnn`) stay
frozen legacy-leaky snapshots of P04–P06, already labelled; they are not re-run.

## Settled points (inferred; recorded in decisions.md)

1. **Smoothing on legacy folders (P06 open item 3).** From P11 the reported "2.0 s
   smoothed" resets at the first window of each reconstructed trial
   (`smooth_probabilities_by_trial(scores, trial_ids)`, windows in clean-array order),
   because R8 is enforced from P11 and PF-02 names the `i % 5`-of-the-clean-array rule
   as the flaw. The two rules agree on S01 and S05 (0 rejected) and can differ on S02,
   S03, S04. The `i % 5` rule stays reachable (`--smoothing mod5`). The demo prints both
   2.0 s columns, so whichever rule reproduces R-6's 2.0 s column is visible. If R-6's
   2.0 s deviates beyond ±1.5 pp on S02–S04 after one investigation round, R11 permits
   consulting the original's P11-stage smoothing; the outcome is a decision row, not a
   tuning.
2. **Splitter API.** `cv_utils.grouped_cv(seed=42)` returns
   `StratifiedGroupKFold(5, shuffle=True, random_state=seed)`; every script gets
   `--cv {grouped,legacy}` (default `grouped`) and `--smoothing {trial,mod5}` (default
   `trial`). `legacy` reproduces the P05–P10 split exactly (regression-tested by hash).
3. **Legacy snapshots stay reproducible and separate.** With `--cv legacy`, a script
   writes its CSV/meta under `reports/legacy_leaky/` (same file name); with `grouped`,
   under `reports/`. Nobody copies files by hand. The CSV `.meta.txt` names the splitter,
   the smoothing rule, and `trial_ids_approximate` subjects.
4. **Inner splits grouped (PF-01).** The SFS inner CV of `benchmark_feature_selection`
   (P06: scikit-learn default 5-fold over windows) becomes a
   `StratifiedGroupKFold(5, shuffle=True, random_state=42)` over the training-fold trial
   ids in `grouped` mode; legacy mode keeps the P06 inner default. No reference number
   exists for the leak-free ablation; the rows are recorded, not targeted.
5. **Trial ids.** `build_trial_ids(y_prefilter, {201: 2, 202: 1, 101..105: 5})` on the
   label array *before* the two-tier gate (stimulus rows selected first, the same
   selection applied to the ids), then `ids[valid_mask]`; chained masks if two masks
   apply (PF-03). A truncated block (e.g. 39 = 7 × 5 + 4) gives a short last trial with
   its own id and a printed warning; the subject is flagged `trial_ids_approximate`.
6. **Networks.** The "before" side of the network before/after table is the frozen P10
   A/B (`reports/legacy_leaky/augmentation_ab_<model>.csv`); the networks are not re-run
   leaky.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| ml-engineer | NEW `src/preprocessing/dataset/cv_utils.py` | `build_trial_ids(y, sub_windows_per_trial=5 \| dict)` per task 1 (contiguous same-label blocks, consecutive chunks, remainder → own id + warning, return also the list of truncated blocks); `grouped_cv(seed)`; `trial_block_report(y, ids)` (block lengths per label, approximate flag); `assert_no_shared_trials(splits, groups)` helper used by tests | P11.1, P11.2 | [1], PF-01, PF-03 |
| ml-engineer | MODIFIED `src/preprocessing/dataset/smoothing.py`, `src/models/classical/legacy_eval.py` | `smooth_probabilities_by_trial(proba, trial_ids)` (reset at each id change; no averaging across ids); `oof_space(..., splits)` fed grouped splits by callers; `accuracies(y, pred, scores, trial_ids=None, rule="trial"\|"mod5")`; labels: grouped CV label, trial smoothing label; legacy labels unchanged | P11.3 | [1], R8, PF-02 |
| ml-engineer | MODIFIED `scripts/benchmarks/feature_based/benchmark_n_subjects.py`, `benchmark_cross_validation.py`, `benchmark_feature_selection.py` (incl. grouped SFS inner CV), `benchmark_harmonic_fbcca.py`, `scripts/evaluation/evaluate_confusion_matrix.py` | `--cv`, `--smoothing`, output dir per settled point 3; meta lines; per-subject printed trial-block report (task 2: block lengths, "approximate trial ids" list) | P11.2, P11.3 | [1] |
| ml-engineer | NEW `scripts/diagnostics/demo_cv_leakage.py` (+ `scripts/diagnostics/__init__.py`) | every discovered subject: the flagship (FBCSP m=1 + FBCCA → scaler → Shrinkage-LDA, the `benchmark_n_subjects` path) with both splitters on the same arrays; columns `Subject, Clean, Approximate ids, 1.0s leaky, 1.0s grouped, Δ1.0, 2.0s leaky (mod5), 2.0s grouped (trial), Δ2.0, 2.0s grouped (mod5)` + Mean row → `reports/cv_leakage_demo.csv` + `.meta.txt`; plus a network section that reads the frozen P10 and the new P11 A/B CSVs if present and prints per-subject OFF/ON leaky vs grouped deltas (no training) | P11.4 | [1] |
| deep-learning (after ml-engineer) | MODIFIED `src/models/cnn/eegnet_cv.py`, `benchmark_common.py`, `scripts/benchmarks/neural_networks/benchmark_nn_augmentation.py`, `benchmark_eegnet.py`, `benchmark_compact_cnn.py`, `benchmark_shallow_convnet.py` | `train_and_eval_cv(..., groups, cv="grouped"\|"legacy")` using `cv_utils`; trial ids built in the shared loader per settled point 5; trial smoothing via `legacy_eval.accuracies(..., trial_ids)`; `--cv`, `--smoothing`; `--freeze-legacy` in the A/B script keeps its P10 meaning only with `--cv legacy`; grouped outputs to `reports/`; N4 tests | P11.3 | [1], decisions.md P10 N4 |

Order: ml-engineer first (creates the branch and `cv_utils`), then deep-learning.

## Legacy behaviour in this phase

R3 per-window sub-band filtering, fs 250 in features and Compact-CNN, P07 per-script gate
— labelled. R1/R8 legacy reachable via `--cv legacy --smoothing mod5`, output under
`reports/legacy_leaky/`.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R1 / PF-01 | a trial's windows in train and test; a script missed; inner split leaky | `assert_no_shared_trials` test over the split of every one of the nine scripts (call the scripts' own split code on a synthetic tree); grouped SFS inner CV test |
| PF-03 | ids built after the gate (rejection shifts chunks); wrong mask; 202/201 rows included in the walk differently than in the arrays | ids on pre-gate labels then `[valid_mask]`; synthetic case with a window removed mid-block before and after the gate, known ids |
| R8 / PF-02 | smoothing across trials; `i % 5` kept by accident | known-answer test: two trials of distinct one-hot probabilities, one window rejected → no mix across ids; mod5 differs on that case |
| R6 | ids misaligned with windows after masking/sorting | synthetic arrays where window content encodes its true trial id |
| Regression | legacy mode no longer equals P05–P10 | `--cv legacy --smoothing mod5` on the P05/P09 synthetic smoke trees: CSVs byte-identical to the pre-P11 outputs (hash pins); real-data: legacy flagship re-run equals R-5 / P06 CSV |
| R2 | grouped splitter changes the fit scope | unchanged fold-matrix code; tests that CSP/scaler see only training rows (existing P05/P06 tests still pass) |
| Interpretation | leak-free gains quoted with leaky ones | every CSV/meta labels its splitter; report labels leaky numbers as such |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| ids, clean blocks | labels 201×4, 202×2, 101×10, 102×10 (dict lengths) | ids 0,0,1,1 / 2,3 / 4×5,5×5 / 6×5,7×5 | exact | task 1 |
| ids, remainder | block of 9 windows at trial length 5 | chunks 5 + 4, the 4 has its own id, warning printed, block flagged | exact | task 1, PF-03 |
| ids, pre-gate | window removed by the gate mid-trial | `build_trial_ids(y_pre)[mask]` keeps true ids; `build_trial_ids(y_pre[mask])` (the bug) shifts them — test fails on the bug | exact | PF-03 |
| no shared trials | every one of the nine scripts' split on a synthetic tree | `set(ids[tr]) ∩ set(ids[te]) = ∅` in every fold; each fold stratified within ±1 trial per class | exact | PF-01, task 4 |
| leak demo | synthetic data where each trial has a unique random offset pattern and no class signal | leaky split accuracy ≫ chance, grouped ≈ chance (planted leak) | grouped ≤ chance + 3 binomial σ | PF-01 |
| trial smoothing | known probabilities, ids with a short trial | output matches hand computation; no average across ids; differs from mod5 | exact | R8, PF-02 |
| legacy regression | P05/P06/P09 synthetic smoke with `--cv legacy --smoothing mod5` | byte-identical CSVs to pre-P11 hash pins | exact | regression |
| SFS inner grouped | training fold with known ids | inner splits share no ids | exact | PF-01 |
| N4 | A/B ON arm | training dataset length = training-fold size; loader generator seeded in both arms | exact | decisions.md P10 |
| output dirs | `--cv legacy` vs `grouped` | files under `reports/legacy_leaky/` vs `reports/` | exact | settled point 3 |

Historical bug: PF-01 (window-level split) — the no-shared-trials and planted-leak tests
fail on it; PF-02/PF-03 — the trial-smoothing and pre-gate tests fail on them.

## Run commands (for the verifier, in this order, from a clean checkout)

```bash
# 0. legacy snapshot of the classical outputs (Era A, reproducible "before"; ~2 min)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --cv legacy --smoothing mod5
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03 --cv legacy --smoothing mod5
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20 --cv legacy --smoothing mod5
# 1. leak-free re-runs (task 5)
.venv/bin/python -m scripts.diagnostics.demo_cv_leakage
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_cross_validation --subject S03
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_feature_selection --subject S03 --k-features 20
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model eegnet --epochs 150 --device cpu
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model compact_cnn --epochs 150 --device cpu
.venv/bin/python -m scripts.benchmarks.neural_networks.benchmark_nn_augmentation --model shallow_conv_net --epochs 150 --device cpu
# 2. demo again, now with the P11 A/B CSVs present (network section; no training)
.venv/bin/python -m scripts.diagnostics.demo_cv_leakage
```

Builders confirm the exact flags in their handoffs; the verifier uses those. Runtime
estimate: classical ≈ 0.5 min (n_subjects), ≈ 0.3 min (cross_validation), ≈ 1.5 min
(feature selection; grouped SFS similar) each mode; demo ≈ 1 min; A/B ≈ 25 min (P10:
1495 s). Total ≈ 35 min, under `LOCAL_RUN_BUDGET_MIN` 120. The verifier saves the pytest
log under `reports/logs/P11/`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| flagship = R-6 (S01 61.00/67.50, S02 56.12/61.73, S03 86.80/90.36, S04 97.46/97.97, S05 95.00/95.50; mean 79.28/82.61) | `reports/n_subjects_benchmark.csv` per subject ±1.5 pp, mean ±1.0 pp; clean/rejected counts exact; report the mod5 2.0 s column for S02–S04 next to it | R-6 |
| augmentation A/B = R-9b | `reports/augmentation_ab_<model>.csv` per subject ±5 pp, cohort ±3 pp, no unexplained cohort-level sign flip of a Δ; ON 1.0 s vs R-7 | R-9b, R-7 |
| the before/after table shows the classical pipeline dropping ~4–5 pp and the CNNs dropping much more (Compact-CNN up to ~20 pp on single subjects) | demo CSV classical Δ per subject and mean; network section leaky (P10) vs grouped (P11) per subject | R-6 leak effect −4.05 / −4.96 pp |
| the EEGNet cohort augmentation gain shrinks from +7.34 pp (last leaky run) to +2.01 pp, while Compact-CNN (+17.16 pp) and ShallowConvNet (+2.53 pp) keep theirs | Mean-row Δ of the three A/B CSVs vs R-9b (±3 pp) | R-9a, R-9b |
| legacy reachable | legacy snapshot CSVs under `reports/legacy_leaky/`; legacy flagship equals `reports/five_subjects_benchmark.csv` (R-5) | era matrix |
| task 2 | printed block lengths per subject and condition; approximate-id subjects listed | 01_DATA_SPEC |

## Sources

1. `mas/03_ROADMAP.md` P11 (opened in this run).
2. `mas/04_REFERENCE_RESULTS.md` tolerance rules, R-5, R-6, R-7, R-9 (opened in this run).
3. `mas/05_PITFALLS.md` PF-01–PF-04 (opened in this run).
4. `mas/01_DATA_SPEC.md` lines 170–190 (opened in this run).
5. `mas/state/reports/P06.md` §9 item 3; `src/models/classical/legacy_eval.py`; `src/preprocessing/dataset/smoothing.py` (opened in this run).

## Questions
