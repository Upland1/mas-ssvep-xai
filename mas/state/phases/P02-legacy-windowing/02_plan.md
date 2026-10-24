# P02 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §3, §5.1, §6, mas/02_REQUIREMENTS.md §3, §4, §7, mas/04_REFERENCE_RESULTS.md R-1, mas/05_PITFALLS.md PF-04/05/06/07/09/13
Approved by Sebastian: [x]   Date:2026-10-24        (required only if PLAN_APPROVAL: required)

## Goal

Build the legacy condition windows (201, 202, 101–105) of every subject's `OO.ebr`
with the legacy raw-stage gate and periodogram features, saved in the layout every
Era-A/B script consumes, and match R-1's window counts exactly.

## Data source

Raw `data/raw/<S>/OO.ebr`, S01–S05 (discovered, `^S\d+$`). Continuous broadband
filter (config v1: 1–60 Hz, Butterworth order 4, `filtfilt`), then 1.0 s windows.
fs from the header (256); window = `int(1.0 * fs)` = 256 samples. Channels: config v1
`scalp` (7, PO7 excluded). Quality: the legacy per-script raw gate (vpp ≤ 200 µV,
std 0.5–60 µV, vpp_min 0.5 µV) on the filtered windows. Output = **legacy folders**
`data/processed/<S>/` (R9 data source "legacy").

## Scope

**In:** the four roadmap tasks.

**Out:** the two-tier gate and 8 channels (P07), trial ids (P11), built folders (P16),
any feature beyond the periodogram.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| signal-processing | NEW `src/preprocessing/signal/quality_check.py` | `validate_eeg_windows` (signature and defaults verbatim, incl. the shared default `vpp_min=5.0`; bounds inclusive; returns an int mask, one per window), `filter_dataset`, `summarize_window_quality`, `window_quality_flags`, `segment_and_validate_eeg` | P02.1 | [2] P02.1 |
| signal-processing | NEW `src/features/ssvep/psd_extraction.py` | `extract_clean_subwindows_psd` (passes `vpp_min` explicitly, PF-07), `process_condition_windows_with_baseline`, `prepare_feature_matrix` (order 201, 202, 101–105; time order within; PSD masked to 5–35 Hz inclusive and flattened channel-major, 7 × 31 = 217) | P02.2 | [2] P02.2, [3] §5.1 |
| signal-processing | NEW `src/visualization/signal_plots.py` | `plot_eeg_window`, `plot_average_psd_by_condition` (1–60 Hz), `plot_stimulus_vs_baseline_psd`; `matplotlib.use("Agg")`, saved, never shown | P02.4 | [2] P02.4, [1] §4 |
| data-engineer | NEW `scripts/preprocessing/run_preprocessing.py`, MODIFIED `Makefile` (`preprocess` target) | script of P02.3; reads paths and thresholds from config v1, CLI overrides; fs from `load_ebr_file(...)["sampling_rate"]`; prints accepted/rejected and per-condition counts per subject and a cohort summary line; writes per-subject arrays, the S03 root arrays (same run, PF-09), the figure(s) (Q1) | P02.3 | [2] P02.3, [1] §4 |

Segment definitions (from [2] P02.2 and [3] §3, §5.1; onsets by the §3 rule):

- 202: samples `[onset − 256, onset)` — kept only if `onset ≥ 256` (PF-13: this lies in the fixation period; documented in the docstring).
- 101–105: `[onset, onset + 1280)`, kept only if it fits; 5 sub-windows. Fallback (no rising edge found for a code): contiguous plateaus of that code, each plateau's first sample taken as the onset.
- 201: `[onset, onset + 512)`, kept only if it fits; 2 sub-windows.
- Each sub-window is gated independently; rejected sub-windows are dropped, the rest kept in time order.

## Legacy behaviour in this phase

None from the era matrix. The 7-channel montage of config v1 (PO7 excluded) carries
over (PF-05, labelled in the config). The shared gate default `vpp_min=5.0` is the
regression state of the original; the legacy path is immune because it passes
`vpp_min=0.5` explicitly (PF-07; P07 reproduces the regression).

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| PF-07 | legacy gate inherits `vpp_min=5.0`, rejects low-amplitude subjects | explicit pass; test with Vpp 2 µV windows |
| PF-09 | root S03 arrays from another run or length mismatch | root written from the same in-memory arrays; script asserts equal lengths; test |
| PF-13 | cue window taken after the 202 pulse | sample-index test |
| R3 | windows filtered one by one | filter the continuous signal once; test that windows equal slices of the filtered recording |
| R6 | wrong PSD flatten (frequency-major) or `(n, T, C)` layout | planted per-channel frequencies → known flat index; shapes asserted |
| PF-04 | 250 Hz slips into windowing/PSD | fs from header; 217 features only at fs 256 |
| PF-06 | channels by position | `select_scalp_channels` by name (P01) |
| R-1 | counts differ | exact comparison; any difference explained (reviewer), never tuned (golden rule 5) |
| R11 | reference read too early | `after-attempt`; logged |

## Tests required

Synthetic only.

| Test | Simulated input | Expected result | Tolerance | Source of the answer |
|---|---|---|---|---|
| gate bounds | windows (3 ch × 256) of sinusoids with amplitude A: ptp = 2A, std = A/√2; one channel out of range | 1 only if every channel is inside; bounds inclusive | exact | [2] P02.1 |
| PF-07 | 1 s windows with Vpp = 2 µV, std ≈ 0.7 µV | kept by `extract_clean_subwindows_psd` (vpp_min 0.5); rejected by `validate_eeg_windows` defaults (vpp_min 5); the test fails if `vpp_min` is not forwarded | exact | PF-07 |
| sub-windows + PSD | 5 s segment, 10 Hz sinusoid, fs 256 | 5 records of 256 samples; `freqs` step 1 Hz; PSD peak at 10 Hz; one sub-window with a 300 µV spike → 4 records, `quality_stats` counts 1 rejected | exact | periodogram, [own] |
| segments | MARK with the §3 timing, 40 trials (8 × 5 targets), EEG = sample index ramp per channel | 80 (201), 40 (202), 200 (101–105) windows; 202 window = `[onset−256, onset)`; stimulus = `[onset, onset+1280)` split in 5; 201 = `[onset, onset+512)` | exact | [3] §3, §5.1 |
| edges | a stimulus onset 3 s before the end; a 202 onset at sample 100 | that trial and that cue are dropped | exact | [2] P02.2 |
| plateaus | 3-sample pulses | same windows as single-sample pulses | exact | [1] §7 |
| feature matrix | records of all 7 conditions in shuffled order; channel c carries a sinusoid at 5 + 3c Hz | y order 201, 202, 101…105, time order within; `X_time (n, 7, 256)`, `X_psd (n, 217)`; `argmax(X_psd[i, 31c:31c+31]) == 3c` | exact | [3] §5.1, R6 |
| continuous filtering | synthetic recording through the script | each saved window equals the slice of `apply_iir_bandpass(full recording)` | 1e-12 | R3, [2] P02.3 |
| script tree | synthetic `S01`, `S03` folders with `OO.ebr`; `S02` without | per-subject arrays; root arrays equal `S03` arrays; `[-] Skipping S02: …`; figure files exist; default subject S03 | exact | [2] P02.3, [1] §4 |
| plots | small records | PNG written under Agg, non-empty | — | [own] |

Historical bug: PF-07 — the PF-07 test fails on a `extract_clean_subwindows_psd`
that does not forward `vpp_min`.

## Run commands (for the runner)

```bash
.venv/bin/python -m scripts.preprocessing.run_preprocessing --all
```

Expected runtime and device: < 2 min, CPU (5 files, one filter pass each).
Over `LOCAL_RUN_BUDGET_MIN` (30)? no. Outputs: `data/processed/<S>/{X_psd_features,X_time_windows,y_labels}.npy`,
`data/processed/{…}.npy` (S03), figure(s) under `outputs/figures/spectra/`, log
`reports/logs/P02/run_preprocessing_<timestamp>.log`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference (R-x, tolerance) |
|---|---|---|
| Per subject: `X_time_windows` `(n, 7, 256)`, `X_psd_features` `(n, 217)`, `y` in `{201,202,101..105}`, `n ≤ 320`, label counts ≤ `{201: 80, 202: 40, 101–105: 40}` | shown Python command loading the saved arrays (processed arrays only) | [3] §5.1 |
| Compare `n` with **R-1** (317–320 per subject); explain any difference | per-subject `n` vs 320/318/317/317/320 and stimulus windows vs 200/199/200/198/200 | R-1, exact |
| The PSD-by-condition figure shows peaks at the stimulation frequencies for at least S03–S05 | reviewer opens the figures; supplementary numeric check: for each stimulus code, mean PSD at the nearest bin to f0 (24, 20, 15, 11, 9 Hz) over the visual channels vs the 201 mean at that bin | visual + ratio > 1 reported per subject |
| root arrays (PF-09) | `data/processed/*.npy` equal `data/processed/S03/*.npy` | exact |

## Sources

1. `mas/02_REQUIREMENTS.md` §3, §4, §7 (opened in this run).
2. `mas/03_ROADMAP.md` P02 (opened in this run).
3. `mas/01_DATA_SPEC.md` §3, §5.1, §6 (opened in this run).
4. `mas/04_REFERENCE_RESULTS.md` R-1; `mas/05_PITFALLS.md` PF-04/05/06/07/09/13 (opened in this run).
5. SciPy `signal.periodogram` documentation (builders and tester open and cite it).

## Questions

Q1 (figure path). The roadmap names one figure,
`outputs/figures/spectra/average_psd_by_condition.png`; with `--all` it would be
overwritten by each subject, yet acceptance needs S03–S05. Default: also write
`outputs/figures/spectra/<S>/average_psd_by_condition.png` per subject, and keep the
verbatim path for S03 (the default subject, like the root arrays). Alternative: one
multi-panel figure at the verbatim path with one panel per subject.

Q2 (gate input). Task P02.3 filters first, then extracts windows "with the legacy
limits", so the "raw-stage" gate runs on the **filtered** windows (as in §5.1:
filter, cut, gate). OK?
