# P21 · 00 · Assignment — Leave-one-subject-out (LOSO) generalization + Colab

Status: READY
Author: orchestrator
Branch: phase/P21-loso-colab (from main @ add8ea1, tag p20-done)
Era: C. Legacy behaviours required: **none**. Enforced: R1 (in LOSO the group is the subject; nothing from the held-out subject reaches any `.fit()`), R2 (incl. the test-time-normalization exception for `lda_subjnorm`), R3, R5, R8 (2-tap smoothing within trial), R9 (per subject, with data source and cohort), fs from metadata.
Owners (agents): ml-engineer (Evaluation Lead, Classical ML); deep-learning (Deep Learning); data-signal (Infra); synthetic-tester; scientific-reviewer; verifier
Depends on: P20 (passed)
Cohort: B003 option B (Sebastian, 2026-10-28) — S01–S05 through P20; all subjects present (40 delivered by Sebastian) for P21–P23, reported as a separate data source next to the S01–S05 rows.

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Professor (Oct 13): subject generalization, "con todos menos con uno";
run on Google Colab (new user, credits provided).

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `scripts/benchmarks/benchmark_loso.py --window 1 --stride-sec 0.25 --methods fbcca
   lda lda_subjnorm ccnn compact eegnet --channels common|all`: `choose_channels`
   (montage identical for all subjects; `common` = channels kept by the gate in every
   subject); `load_subject` (clean stimulus windows, chosen channels, FBCCA scores);
   methods: `fbcca` (normalized scores, no training — the calibration-free floor),
   `lda` (CSP per band fitted on pooled training subjects + FBCCA → scaler →
   Shrinkage-LDA), `lda_subjnorm` (each subject's features z-scored with its **own
   unlabeled** mean/std before pooling — report as "unsupervised per-subject
   normalization"), networks via `fit_network` on pooled subjects (trial ids offset per
   subject; validation never from the test subject); **resumable**: each (method, test
   subject) fold saved to `<out-dir>/folds/<method>__test-<S>.npz` and skipped on rerun;
   `--save-models`; summary with 2-tap smoothed accuracy, per-subject pivot, cohort
   mean ± SD, `predictions.csv`, `confusion.csv`.
2. `notebooks/loso_colab.ipynb`: GPU check; mount Drive; settings cell (`RAW_DIR`,
   `DRIVE_DIR`, repo URL, branch, `LOSO_OUT`) that lists subjects and checks `OO.ebr`;
   fresh clone per session; install only `pyyaml joblib`; symlink `data/raw`,
   `reports`, `outputs/models` to Drive; build windows; within-subject reference
   (`benchmark_window_sweep.py --windows 1 --methods fbcca lda --cv-repeats 5`); LOSO
   classical; LOSO networks; results comparison table (within vs LOSO); release the
   runtime. Written for a first-time Colab user.

Numbered for this phase: P21.1 `benchmark_loso.py` harness, channel choice, classical methods, resumable folds, outputs; P21.2 network methods in the LOSO harness (`fit_network`, pooled subjects); P21.3 `notebooks/loso_colab.ipynb`.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`benchmark_loso.py`, `notebooks/loso_colab.ipynb`, `reports/loso_w1/`

## Acceptance (verbatim)

Acceptance: classical LOSO runs end-to-end on CPU; interrupting and rerunning skips
finished folds; the notebook runs top to bottom on a T4 (or the Infra agent documents
the exact manual steps it could not automate). Record within vs LOSO (R-16).

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-31 | mas/05_PITFALLS.md | `compact` in the LOSO CLI is `compact_eegnet`; name it so in every table |
| PF-32 | mas/05_PITFALLS.md | early-stopping validation = training subjects' trials only, grouped; never the held-out subject |
| PF-33 | mas/05_PITFALLS.md | trial ids restart at 0 per subject; offset before pooling |
| PF-34 | mas/05_PITFALLS.md | CSP filters and CNN inputs need the same channels for all subjects (`common` / `all`) |
| PF-35 | mas/05_PITFALLS.md | `lda_subjnorm` is transductive: label "unsupervised per-subject normalization", state the statistics come from the whole session (offline upper bound) |
| PF-37 | mas/05_PITFALLS.md | saved folds store their configuration; full refusal of mixed configs is P22, but P21 folds must already record it |
| PF-40 | mas/05_PITFALLS.md | Colab: results on Drive, fresh clone, resumable folds, new `LOSO_OUT` per configuration, never `pip install -r requirements.txt`, release the runtime |
| R-16 | mas/04_REFERENCE_RESULTS.md | no numeric target; reviewer checks direction: LOSO below within-subject; `fbcca` LOSO = within value; `lda_subjnorm` ≥ `lda` |
| R1, R2, R8, R9 | mas/RULES.md | subject-level grouping, in-fold fits, trial-aware smoothing, per-subject reporting with cohort/data source |
| B003 | mas/state/blockers/ | cohort option B: 40-subject runs are a separate data source; S01–S05 rows kept comparable with P20 |
| decisions P20 C-1..C-3 | mas/state/decisions.md | thread-pinned hash tests; flag degenerate early-stopping folds (best epoch ≤ 5 or train acc < chance + 10 pp); ≥ 3 repeats before interpreting a single CNN cell that moves a cohort by > 5 pp |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| ml-engineer | P21.1 | `03_changes_ml-engineer.md` |
| deep-learning | P21.2, P20 C-1 (thread pinning in the P09/P10 hash-pinned tests), P20 C-2 (degenerate-fold flag) | `03_changes_deep-learning.md` |
| data-signal | P21.3 | `03_changes_data-signal.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | builds, within reference, LOSO runs within budget; human-run request for the rest | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P21.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
