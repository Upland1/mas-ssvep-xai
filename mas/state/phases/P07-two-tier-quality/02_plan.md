# P07 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §5.1, §6, mas/02_REQUIREMENTS.md §3, §4, §6, mas/04_REFERENCE_RESULTS.md R-6, mas/05_PITFALLS.md PF-05–PF-10, P02–P06 rows of decisions.md
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Add the two-tier quality gate (subject-level channel drop, then window rejection on the
surviving channels), restore PO7 in the configuration without breaking the 7-channel
legacy arrays, reproduce and pin the PF-07 `vpp_min` regression, and produce the first
`reports/n_subjects_benchmark.csv`.

## Data source

Legacy 7-channel folders `data/processed/<S>/` (P02, OO) for the benchmark — **not
regenerated** (R-6 is defined on them; P16 rebuilds with 8). Channel names resolved by
`resolve_channel_names(7)` = montage without PO7. The PF-07 demonstration and the
8-channel preprocessing path run on S03's `OO.ebr` into a separate output folder
(`data/processed_p07_demo/`, git-ignored), never over `data/processed/`. fs 250 in
features (legacy).

## Scope

**In:** P07.1–P07.6; P02/P05/P06 carry-forward items listed below.
**Out:** trial-grouped CV (P11), built folders and shared quality decision (P16).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| data-signal | MODIFIED `src/preprocessing/signal/quality_check.py` | `compute_channel_quality_stats`, `identify_noisy_channels(windows, channel_names, limits, fail_fraction_thresh=0.5)` (strictly > 50 %), `drop_noisy_channels`, `apply_artifact_quality_pipeline(...)` with the roadmap signature/defaults and return dict; `precomputed=` lets a caller reuse one decision (PF-10); `summarize_window_quality` fed the **ungated** windows (P02 carry-forward) | P07.1 | [2], decisions.md P02 |
| data-signal | MODIFIED `configs/pipeline_config.yaml` (v2: 8 scalp channels, `excluded: []`), `src/io/` or `src/preprocessing/` helper `resolve_channel_names(n_channels)` | 8 → full montage, 7 → without PO7, else None; config version noted | P07.3 | [1] §3, PF-05 |
| data-signal | MODIFIED `scripts/preprocessing/run_preprocessing.py` | chronic-noise channel detection on non-overlapping 1 s windows of the filtered recording (vpp 5–200, std 0.5–60, > 50 %) before window extraction; drop + report; raw gate keeps `vpp_min=0.5` pinned; `--vpp-min 5.0` reproduces PF-07 (labelled `legacy regression demo`); `summarize_window_quality` printed in the log; stale-output handling for skipped subjects (P02 carry-forward: remove or refuse to leave old arrays for a skipped subject); `--processed-dir` already exists | P07.4, P07.5 | [2], PF-07 |
| ml-engineer | MODIFIED `src/features/ssvep/{fbcca,fbcsp,psd}_extraction.py`, `window_mask.py` | extractors run `apply_artifact_quality_pipeline` (vpp 5–120, std 1–35, fail 0.5, explicit) and return `(X, y_clean, valid_mask, channel_report)`; one decision shared across blocks (PF-10) | P07.2 | [2], PF-08 |
| ml-engineer | MODIFIED every consumer: `benchmark_harmonic_fbcca`, `benchmark_feature_selection`, `benchmark_cross_validation`, `visualize_data`, `test_sklearn_models`, `evaluate_confusion_matrix` (+ `benchmark_5_subjects`, shared runner modules) | 4-value returns; channel subsets by name after drops (PF-06); smoke test runs each script (PF-08) | P07.2 | PF-06, PF-08 |
| ml-engineer | NEW `scripts/benchmarks/feature_based/benchmark_n_subjects.py` | `--data-root` (default `data/processed`), `--n-jobs`, flagship P05 path with the two-tier gate, legacy `StratifiedKFold(5, shuffle, 42)`, `i % 5` smoothing, §6 columns `Subject, Channels Kept, Channels Dropped, Clean Windows, Rejected Windows, 1.0s Acc (%), 2.0s Smoothed (%)`, channel report per subject, `reports/n_subjects_benchmark.csv` | P07.6 | [2], [1] §6 |
| ml-engineer | tests | cut the suite runtime below 5 min (P06 76 s SFS smoke → `--sfs-features 2`, expected p 55/45/25/25/7; P04 39.6 s script smoke and other slow smokes on smaller trees); remove/replace the vacuous P06 layout test | — | decisions.md P06/P07 |

Note on limits: from P07 the extractor gate is the two-tier pipeline with the roadmap's
vpp 5–120 µV / std 1–35 µV (and channel fail > 50 %), replacing P05's original-extractor
limits (0.5–120 / 0.1–35) — the "new default" of PF-07's story. P05/P06 numbers remain
as recorded (tags p05-done, p06-done).

## Legacy behaviour in this phase

R1 (window-level CV in `benchmark_n_subjects`), R3 (per-window sub-bands), R8 (`i % 5`),
fs 250, R5 (per-script gates; the PF-07 regression is reproduced behind `--vpp-min 5.0`
and labelled, then the default stays pinned at 0.5). All labelled in code, console and
`.meta.txt`.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| PF-08 | a consumer still unpacks 3 values | every consumer changed in one change; each script smoke-run; grep for call sites |
| PF-06 | positions after a tier-1 drop | names everywhere; test with a dropped middle channel |
| PF-10 | blocks gated separately | `precomputed=` decision shared; test |
| R-6 integrity | `data/processed/` regenerated as 8-channel before P11 | run commands never target `data/processed/` with `run_preprocessing`; demo dir separate |
| PF-07 | regression demo leaks into defaults | default pinned 0.5; test |
| R5 | thresholds inherited | all explicit; printed |
| Test runtime | suite > 5 min | reduce smoke sizes; verifier still runs the whole suite |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| tier 1 boundary | 8 channels; channel 3 fails in exactly 50 % of windows, channel 5 in 51 % | only channel 5 dropped (strict > 50 %) | exact | [2] P07.1 |
| tier 2 | single bad window on a kept channel; bad samples only on a dropped channel | first rejected; second kept (dropped channel not judged) | exact | [2] |
| return dict | pipeline output | the 7 keys; `channels_kept_idx` positions of kept names; `windows_clean.shape[1] == len(channels_kept)` | exact | [2], R6 |
| channel stats | known Vpp/std per channel | fail fraction, mean Vpp, mean std equal analytic values | 1e-9 | [2] |
| `resolve_channel_names` | 8, 7, 6 | full montage; without PO7; None | exact | PF-05 |
| extractor arity | each extractor | 4 values; same mask across FBCCA/FBCSP/PSD | exact | PF-08, PF-10 |
| by-name subsets | visual cluster after dropping PO8 | cluster uses remaining names; no positional shift | exact | PF-06 |
| PF-07 | windows with Vpp 2 µV | kept with `vpp_min=0.5`; rejected with `vpp_min=5.0` | exact | PF-07 |
| chronic-noise detection | synthetic recording with one channel noisy in > 50 % of 1 s non-overlapping windows | that channel dropped before window extraction; report printed | exact | [2] P07.4 |
| `summarize_window_quality` | ungated windows | ranges include rejected windows; non-zero rejected count | exact | P02 carry-forward |
| benchmark_n_subjects | synthetic tree with a 7-channel and an 8-channel subject | §6 columns; channels kept/dropped filled; one row per subject | exact | [1] §6 |
| every consumer | scripts smoke on synthetic trees | exit 0 | — | PF-08 |

Historical bug: PF-07 (test fails if the raw gate inherits 5.0) and PF-08 (a consumer
with 3-value unpacking fails the smoke test).

## Run commands (for the verifier)

```bash
# PF-07 regression demo and the 8-channel path, S03 only, separate output folder
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --processed-dir data/processed_p07_demo/vppmin5 --no-figures
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --processed-dir data/processed_p07_demo/pinned --no-figures
# two-tier benchmark on the legacy 7-channel arrays
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed --n-jobs 5
```

(Flag names fixed by the builders and copied into `05_run.md`; `--no-figures` only if it
exists.) Runtime: preprocessing ~10 s per run; benchmark ~1 min. ≪ 120 min.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| tests for both tiers | named tests in `04_tests.md`; full suite passes | [2] |
| S03 still produces windows | pinned run: S03 window count > 0 (and per condition); demo run: count with `vpp_min=5.0` reported (PF-07 says all 320 rejected — compare and explain) | PF-07 |
| channel report printed per subject | in both preprocessing logs and the benchmark log | [2] |
| benchmark CSV produced for every subject (channels kept/dropped column filled) | `reports/n_subjects_benchmark.csv`: 5 rows + columns filled | [1] §6 |
| Record numbers | per-subject table in 06_verify.md (diagnostic comparison with R-5 counts/accuracies; no target) | — |

## Sources

1. `mas/02_REQUIREMENTS.md` §3, §4, §6 (opened in this run).
2. `mas/03_ROADMAP.md` P07 (opened in this run).
3. `mas/04_REFERENCE_RESULTS.md` R-6; `mas/05_PITFALLS.md` PF-05–PF-10 (opened in this run).

## Questions
