# P16 · 00 · Assignment — Baseline freeze, edge effects, continuous filtering, 256 Hz, shared quality

Status: READY
Author: orchestrator
Branch: phase/P16-continuous-filtering (from main @ 97a29be, tag p15-done)
Era: C. Legacy behaviours required in this phase: **none** (`team.yaml`). From this phase the era matrix enforces R3 (filter continuous, then window), R5 (one shared quality decision, explicit thresholds) and fs from metadata (256 Hz), on top of R1, R2, R4, R6–R11. The legacy paths (per_window filtering, fs 250, per-script gate, legacy folders with `i % 5` smoothing) must stay reachable behind flags and be labelled `legacy`; they are the "before" side of the v1/v2 table.
Owners (agents): data-signal (Signal Processing, Data Engineer); ml-engineer (Evaluation Lead); connectivity-stats (Connectivity & Stats); scientific-reviewer; verifier
Depends on: P15 (passed; merged 97a29be)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Professor's change list (Oct 2026), branch `fix/signal-filtering-edge-effects`:
research edge effects; filter the raw continuous signal instead of each window; only
valid windows go into frequency analyses; and the discovery that the recordings are
**256 Hz**, not the 250 Hz assumed in feature code.
**Depends on:** P15. **Owners:** Signal Processing, Evaluation lead, Connectivity &
Stats, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `scripts/freeze_baseline.py --tag v1 --note "…"`: copy `data/processed`, `reports`,
   `outputs/reports`, `configs` into `baselines/v1_<date>/` (read-only, refuse to
   overwrite), file pre-leak reports (`five_subjects_benchmark.csv`) under
   `superseded/`, write `MANIFEST.json` (git commit, dirty flag, python, platform, pip
   freeze, per-subject channel audit, sha256/shape/rows per file) and
   `baseline_summary.csv` (long format `pipeline, subject, metric, value` + `MEAN`
   rows, from the n-subject, augmentation, GNN, gate and connectivity CSVs). **Run it
   before any other change in this phase.**
2. `src/preprocessing/windowing.py`: `load_session(path, scalp_channels, mark)`;
   `event_onsets(mark, code)`; `WindowIndex(starts, labels, trial_ids, sub_idx,
   offsets)`; `segment_starts`; `windows_per_segment`; `build_window_index(mark, fs,
   stim_conditions, cross_condition=201, cue_condition=202, sub_window_sec=1.0,
   stim_duration_sec=5.0, cross_duration_sec=2.0, cue_lookback_sec=1.0,
   stride_sec=None)` — segments: cross `[onset, onset+2 s)`, cue `[onset−1 s, onset)`,
   stimulus `[onset, onset+5 s)` complete trials only; windows every `stride` fully
   inside the segment; one trial id per segment. `stride=None` reproduces the legacy
   windows exactly. `cut_windows`; filter banks `fbcca_filter_bank(fs)` (Chebyshev as
   P05) and `fbcsp_filter_bank(fs)` (Butterworth order 4, P05 bands);
   `band_windows(broadband, starts, n, bank, mode)` with modes **continuous** (filter
   whole recording, then cut) and **per_window** (cut, then filter — legacy);
   `select_clean_bands`.
3. `scripts/diagnostics/demo_edge_effects.py --subject S03`: every FBCSP/FBCCA band
   computed both ways on stimulus windows; relative error |pw − cont| / RMS(cont);
   edge (first/last 100 ms) vs centre; 3-panel figure (example trace at 15 Hz on Oz in
   the 13–17 Hz band, error profile over the window for a narrow and a wide band, every
   band edge vs centre) → `outputs/figures/edge_effects/edge_effects_S03.png`; table
   `reports/edge_effects_summary.csv`.
4. `src/preprocessing/window_quality.py::subject_quality_gate(windows, starts,
   broadband, fs, channel_names, filters, params)`: channel tier and window tier as P07
   (limits from config `quality:`); plus an **artifact guard**: mark 0.25 s blocks of
   the continuous filtered signal whose Vpp exceeds `vpp_max` on any kept channel,
   dilate by `guard_sec` (`auto` = longest ringing time of all filters applied
   continuously, measured by the samples where |impulse response| > 1 % of its peak),
   and reject windows overlapping it (reason 2). Returns `valid_mask`,
   `valid_mask_no_guard`, `reason`, kept/dropped channels, fail fractions, guard,
   artifact fraction, params.
5. `scripts/build_windows.py --filter-mode {continuous,per_window} --subjects
   --session OO --guard-sec --window-sec … --stride-sec --banks … --out-root`: per
   subject, load, broadband filter (config: 1–90 Hz order 4, + 60 Hz notch Q 30,
   continuous zero-phase), window index, cut filtered and raw windows, filter banks,
   quality gate, save every file of `01_DATA_SPEC.md` §5.2 into
   `data/processed_<mode>/[w<len>_s<stride>/]<S>/`, print a one-line summary per
   subject. Config moves to the **final** version (`02_REQUIREMENTS.md` §3).
6. `src/io/subject_data.py`: `find_project_root`, `discover_subjects`,
   `resolve_channel_names`, `is_built`, `load_subject(sub_dir, conditions,
   quality_mode="shared"|"shared-no-guard"|"per-script", bands=(), fs_override=None)`
   returning windows, y, trial ids (true ids for built folders, reconstructed for
   legacy), bands, fs (meta, legacy 250), channel names, quality decision, `built`,
   `source`.
7. Port to built windows (default `--data-root data/processed`, accept built roots,
   `--quality`, `--fs` override): `benchmark_n_subjects.py` (FBCCA from the continuous
   `fbcca` bands, CSP on continuous `fbcsp` bands, smoothing by true trial id,
   `--cv-repeats N` with seeds 42+r and SD columns, output suffix rules), the
   connectivity cohort and between-frequency scripts (true trial ids, real fs, shared
   quality). Extractors gain `subband_windows=` and `quality=` parameters.
8. **v1 vs v2 table**: flagship and connectivity on (a) frozen v1, (b) per_window
   built windows at 256 Hz, (c) continuous built windows — separating the effect of fs,
   of filtering mode and of the guard (`--quality shared-no-guard`).

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`scripts/freeze_baseline.py`, `src/preprocessing/windowing.py`, `src/preprocessing/window_quality.py`, `scripts/build_windows.py`, `src/io/subject_data.py`, `scripts/diagnostics/demo_edge_effects.py`, `reports/edge_effects_summary.csv`, v1-vs-v2 table

## Acceptance (verbatim)

Acceptance: snapshot exists and is read-only; edge-effect table shows edge error
≫ centre error for narrow FBCSP bands; `stride=None` per_window build reproduces
the legacy window starts; v1/v2 table complete with every number backed by a log. No
fixed numeric target for v2 (none was preserved — see R-16); the Reviewer must explain
the direction of every change.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-04 | mas/05_PITFALLS.md | fs from the header/meta (256); fs 250 only on the legacy path, labelled |
| PF-14 | mas/05_PITFALLS.md | edge effects of per-window filtering; continuous mode + artifact guard by ringing time |
| PF-02, PF-03 | mas/05_PITFALLS.md | built folders carry true trial ids: smoothing by true trial ordered by offset (R8); legacy ids stay approximate on S02/S04 (P11 D-2) |
| PF-05, PF-07 | mas/05_PITFALLS.md | 8 channels, the gate decides; every threshold passed explicitly (R5) |
| PF-13 | mas/05_PITFALLS.md, decisions P02 (a) | the 202 window lies inside the fixation period and duplicates a 201 sub-window; never treat them as independent samples |
| R-16 | mas/04_REFERENCE_RESULTS.md | no numeric target for v2; the reviewer explains the direction of every change |
| R-6, R-12 | mas/RULES.md, mas/04_REFERENCE_RESULTS.md | regression: the ported scripts on the default legacy root must still reproduce the frozen v1 numbers |
| R3, R5, R8, R9, fs | mas/RULES.md | enforced from this phase |
| §5.2, §3, §6 | mas/01_DATA_SPEC.md, mas/02_REQUIREMENTS.md | built-folder files, final config, `edge_effects_summary.csv` and `n_subjects_benchmark` schemas |
| decisions P02 | | carry-forward: check S03 first-trial PO8 rejections for a filter start-up transient |
| decisions P11 N1 | | make `oof_space(splits=None)` raise at this refactor |
| decisions P11 D-2 | | true trial ids replace the approximate ones in built folders |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| data-signal | P16.1–P16.6 | `03_changes_data-signal.md` |
| ml-engineer | P16.7 (flagship + extractors), P16.8 | `03_changes_ml-engineer.md` |
| connectivity-stats | P16.7 (connectivity scripts) | `03_changes_connectivity-stats.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P16.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
