# P16 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md (era matrix), mas/01_DATA_SPEC.md §3, §5, mas/02_REQUIREMENTS.md §2, §3 (final config), §5, §6, mas/04_REFERENCE_RESULTS.md R-6, R-12, R-16, mas/05_PITFALLS.md PF-02/03/04/05/07/13/14, decisions.md carry-forwards (P02, P07, P11 N1/D-2)
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Freeze the Era A/B outputs as baseline v1, then build the Era C data path: one window index
with true trial ids, continuous zero-phase filtering before cutting, one shared quality
decision with an artifact guard, fs from metadata (256 Hz), and one loader. Port the
flagship and the connectivity scripts to it. Quantify how much of the change from v1 to
v2 is due to fs, to the filtering mode and to the guard.

## Data source

- Raw: `OO.ebr` per subject (B005: OO/mOO only; this phase uses OO), read **only** by
  project scripts (`build_windows.py`, `demo_edge_effects.py`, the legacy-starts check)
  launched with `python -m scripts...`.
- v1: the legacy folders `data/processed/<S>/` (7 channels, fs 250 feature axis) and the
  current `reports/`, `outputs/reports/`, `configs/`, frozen by task 1 before any v2
  output is written. Orchestrator pre-build hash list: `mas/state/scratch/p16_v1_pre_hashes.txt`
  (407 files, written from main 97a29be before the branch existed).
- v2: `data/processed_per_window/<S>/` and `data/processed_continuous/<S>/` (§5.2 files, 8 channels).
  The legacy folders are never modified.

## Settled points (inferred; recorded in decisions.md)

1. **"Run it before any other change."** Only the verifier runs phase commands, so
   `freeze_baseline` is **run command 1**. Builders write no file under `data/processed/`,
   `reports/`, `outputs/reports/` or `configs/` outputs during smoke runs (smoke runs use
   `--out-root`/`--reports-dir` in `mas/state/scratch/`). The verifier proves that the
   snapshot equals v1 by checking the MANIFEST sha256 values against
   `p16_v1_pre_hashes.txt`. `configs/pipeline_config.yaml` moves to the final version in
   this phase, so the freeze copies `configs/` **from git at the pre-phase commit**
   (`git show 97a29be:configs/pipeline_config.yaml`), not from the working tree. The
   MANIFEST records which commit the config came from.
2. **Read-only snapshot.** `chmod -R a-w` on `baselines/v1_<date>/`; a second run with the
   same tag refuses (exit ≠ 0) and changes nothing.
3. **Legacy reachability.** `--filter-mode per_window`, `--fs 250`,
   `--quality per-script` and the default legacy root `data/processed` stay available.
   On a legacy root, `load_subject` reports fs 250 (meta legacy), reconstructs ids with
   `build_trial_ids` (approximate flag) and the flagship keeps the `i % 5` smoothing. On a
   built root it uses the meta fs, true ids and trial-reset smoothing ordered by
   (trial, offset) (R8).
4. **Regression (blocking).** The ported `benchmark_n_subjects` on the default legacy root
   with defaults (seed 42, 1 repeat) reproduces R-6 exactly (P11 numbers, 0.00 pp). The
   ported `analyze_connectivity_cohort` on the legacy root reproduces the P13 final
   `connectivity_cohort_summary.csv` exactly. These two runs write with a `_v1check`
   suffix and are compared with the frozen baseline.
5. **v1/v2 decomposition (task 8).** Rows, each S01–S05 + mean, 1.0 s and 2.0 s:
   - (a) v1 frozen: legacy folders, fs 250, per-script gate (from `baselines/v1_*/`);
   - (a′) legacy folders, `--fs 256`: the **fs effect** alone;
   - (b) per_window build, fs 256, shared quality: adds 8 channels, the 1–90 Hz + notch
     broadband filter and the shared gate (not separable here; stated);
   - (c) continuous build, shared quality: the **filtering-mode effect** is (c) − (b);
   - (c′) continuous build, `--quality shared-no-guard`: the **guard effect** is (c) − (c′).
   Flagship: `--cv-repeats 5` (seeds 42+r) on every row so that differences are judged
   against the repeat SD; seed 42 alone is printed too. Connectivity: cohort summary
   (coherence, PLV, wPLI, PDC; trial-level, 200 permutations, as P13 final) on (a), (b),
   (c) and (c′); the table reports FDR edge counts and global p per method and frequency.
   The table script only joins CSVs (no computation beyond differences), writes
   `reports/v1_vs_v2/flagship.csv`, `connectivity.csv` and a markdown table.
   `scripts/diagnostics/compare_v1_v2.py` is an addition of this rebuild (the roadmap names
   a table, not a script).
6. **Built-window parameters.** Session OO; `window_sec 1.0`, `stride=None` (legacy starts)
   for all reported builds; banks `fbcca fbcsp`; guard `auto`; broadband 1–90 Hz order 4
   + 60 Hz notch Q 30, zero-phase, continuous in both modes (per_window mode differs only
   in the sub-bands). Config final per §3 (`filter_bank:` block present but used from P17).
7. **Legacy-starts check (acceptance 3).** `build_windows.py --check-legacy-starts`
   recomputes the legacy pre-gate starts with the P02 code path
   (`scripts/preprocessing/run_preprocessing.window_starts`) on the same recording and
   prints, per subject and condition, `n_legacy, n_built, n_equal` and the max |Δ|. It is
   a project script, so no agent reads the recording.
8. **Edge-effect ratio.** `edge_to_centre_ratio` = mean rel. error in the first and last
   100 ms / mean rel. error in the centre. The reviewer pre-commits the ratio that counts
   as "≫" in the pre-run audit, before the run.
9. **Carry-forwards.** (a) P02: the S03 first-trial PO8 rejections are checked for a filter
   start-up transient (continuous vs legacy rejection of that window, in the
   data-signal handoff and the run log). (b) P11 N1: `oof_space(splits=None)` raises.
   (c) P11 D-2: report how many trial ids differ between the legacy reconstruction and
   the true ids per subject (S02/S04 expected).
10. **Tests** never read generated or git-ignored files (P14 D-5); they use synthetic
    recordings (planted sinusoids, a planted artifact, known event marks).

## Work split

| Order | Agent | Files (NEW / MODIFIED) | What | Roadmap task |
|---|---|---|---|---|
| 1 | data-signal | NEW `scripts/freeze_baseline.py` | task 1, settled points 1–2 | P16.1 |
| 1 | data-signal | NEW `src/preprocessing/windowing.py` | task 2; `stride=None` = legacy starts | P16.2 |
| 1 | data-signal | NEW `scripts/diagnostics/demo_edge_effects.py` | task 3, schema §6 | P16.3 |
| 1 | data-signal | NEW `src/preprocessing/window_quality.py` | task 4, every threshold explicit (R5) | P16.4 |
| 1 | data-signal | NEW `scripts/build_windows.py`; MODIFIED `configs/pipeline_config.yaml` (final, §3) | task 5, settled points 6–7 | P16.5 |
| 1 | data-signal | NEW `src/io/subject_data.py` | task 6 | P16.6 |
| 2 (parallel) | ml-engineer | MODIFIED `scripts/benchmarks/feature_based/benchmark_n_subjects.py`, `src/features/ssvep/fbcca_extraction.py`, `fbcsp_extraction.py`, `src/models/classical/*` as needed; NEW `scripts/diagnostics/compare_v1_v2.py` | task 7 (flagship, extractors `subband_windows=`, `quality=`), task 8, settled points 3–5, 9b | P16.7, P16.8 |
| 2 (parallel) | connectivity-stats | MODIFIED `scripts/connectivity/analysis/analyze_connectivity_cohort.py`, `analyze_connectivity.py`, `scripts/connectivity/comparison/*.py`, `scripts/connectivity/diagnostics/check_power_alpha_confound.py`, `src/features/connectivity/*` as needed | task 7 (connectivity: true ids, real fs, shared quality via `load_subject`) | P16.7 |

The ml-engineer and connectivity-stats start after data-signal is READY (they need
`load_subject`). They touch disjoint files.

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R3 / PF-14 | per_window path silently used, or continuous filtering applied after cutting | `band_windows` mode test: continuous output equals filtering the whole recording then cutting (exact); per_window differs at the edges |
| PF-04 | a literal 250/256 left in v2 code | fs flows from `load_subject(...)["fs"]`; grep test; a 256 Hz planted tone at 24 Hz lands in the 24 Hz bin only with fs 256 |
| R5 | per-script thresholds or defaults | `subject_quality_gate` takes `params` with no defaults for limits; test that a missing key raises |
| Guard | `auto` ringing time wrong or blocks misaligned | impulse-response test with a known filter; planted spike → windows within guard rejected with reason 2, others kept |
| R8 / PF-02 | smoothing by offset alone across trials | test with interleaved trials: reset at offset 0 of each true trial, ordered by (trial, offset) |
| R1 / PF-03 | true ids not one per segment; 202 and its 201 twin in different folds | test: one id per segment; the 202 window shares a group with its trial's 201 windows, or 202 is excluded where stimulus-only (PF-13) |
| R6 | `(n, band, channel, time)` layout | planted tone per (band, channel) lands in the right slot |
| R2 | CSP / scaler on continuous bands fitted on all windows | reuse the in-fold tests with `subband_windows=` |
| Snapshot | baseline taken after a v2 output overwrote v1 | settled point 1 hash check |
| Legacy regression | port changes v1 numbers | settled point 4 (exact) |

## Tests required

| Test | Simulated input | Expected result | Tolerance |
|---|---|---|---|
| window index legacy | synthetic MARK with 201/202/101–105 onsets, one truncated last trial | starts = the P02 legacy starts; truncated trial dropped; 80/40/200 counts for a full session | exact |
| stride | stride 0.5 s | windows fully inside segments, offsets restart per trial | exact |
| trial ids | as above | one id per segment; sub_idx 0..k−1 | exact |
| band_windows | 15 Hz tone + noise, Butterworth 13–17 | continuous = filter-then-cut; per_window edge error ≫ centre | exact / ratio |
| ringing time | known Butterworth | `guard_sec` equals the 1 % impulse-response span | 1 sample |
| artifact guard | planted 500 µV spike | reason 2 within guard, valid elsewhere; `valid_mask_no_guard` keeps them | exact |
| tiers | one bad channel (fail > 50 %) | channel dropped, windows judged on kept channels | exact |
| loader | built and legacy fake folders | fs 256 vs 250, true vs reconstructed ids, `built`, `source`; modes shared / shared-no-guard / per-script | exact |
| freeze | temp tree | copies, read-only, refuses overwrite, MANIFEST hashes, `superseded/`, summary long format with MEAN | exact |
| flagship port | synthetic built folder | uses saved `fbcca`/`fbcsp` bands (no refiltering), trial-reset smoothing, `--cv-repeats` SD columns, suffix rules | exact |
| flagship legacy | synthetic legacy folder | identical output to the pre-port code | exact |
| connectivity port | synthetic built folder with coupled pair | real fs, true ids in permutations, shared mask | exact |
| N1 | `oof_space(splits=None)` | raises | exact |
| PF-04 bug test | 24 Hz tone at 256 Hz | fails with fs 250 (wrong bin), passes with meta fs | exact |

## Run commands (for the verifier, in order)

```bash
.venv/bin/python -m scripts.freeze_baseline --tag v1 --note "Era A/B outputs before P16 (main 97a29be)"
.venv/bin/python -m scripts.diagnostics.demo_edge_effects --subject S03
.venv/bin/python -m scripts.build_windows --filter-mode per_window --subjects S01 S02 S03 S04 S05 --session OO --check-legacy-starts
.venv/bin/python -m scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --check-legacy-starts
# regression (settled point 4)
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --out-suffix v1check
.venv/bin/python -m scripts.connectivity.analysis.analyze_connectivity_cohort --methods coherence plv wpli pdc --permutations 200 --permutation-unit trial --n-jobs -1 --out-suffix v1check
# v1/v2 decomposition (settled point 5): flagship rows a′, b, c, c′ (and a with --cv-repeats 5), connectivity b, c, c′
# exact flags and suffixes: fixed by the ml-engineer and connectivity-stats handoffs
.venv/bin/python -m scripts.diagnostics.compare_v1_v2
```

Estimates (from P11/P13 logs): build 2 × ~5 min; flagship 5 runs × ~3 min; connectivity
4 runs × ~6 min; total ~60 min plus the ~7 min suite, inside `LOCAL_RUN_BUDGET_MIN` 120.
The builders measure one subject and confirm. If the total exceeds 120 min the
orchestrator issues a human-run request.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked |
|---|---|
| snapshot exists and is read-only | `baselines/v1_<date>/` with MANIFEST, `baseline_summary.csv`, `superseded/five_subjects_benchmark.csv`; no write bit; second run refuses; sha256 values equal `p16_v1_pre_hashes.txt` |
| edge-effect table shows edge error ≫ centre error for narrow FBCSP bands | `reports/edge_effects_summary.csv`, ratio threshold pre-committed by the reviewer |
| `stride=None` per_window build reproduces the legacy window starts | `--check-legacy-starts` output: `n_equal = n_legacy` for every subject and condition |
| v1/v2 table complete with every number backed by a log | `reports/v1_vs_v2/*`, every cell traceable to a CSV and a log under `reports/logs/P16/` |
| (settled point 4) | `_v1check` CSVs equal the frozen v1 ones exactly |
| (R-16) | no numeric target; the reviewer explains the direction of every change |

## Sources

1. `mas/03_ROADMAP.md` P16 (opened in this run).
2. `mas/01_DATA_SPEC.md` §5; `mas/02_REQUIREMENTS.md` §2, §3, §5, §6; `mas/04_REFERENCE_RESULTS.md` R-16; `mas/05_PITFALLS.md` PF-02/03/04/14 (opened in this run).

## Questions
