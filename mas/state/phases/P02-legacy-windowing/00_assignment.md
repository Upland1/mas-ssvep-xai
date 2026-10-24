# P02 · 00 · Assignment — Legacy preprocessing and windowing

Status: READY
Author: orchestrator
Branch: phase/P02-legacy-windowing (from main @ f2b74ae, tag p01-done)
Era: A — legacy behaviours required in this phase: none of the `mas/RULES.md` era-matrix rows (R1/R3/R5/R8 start with the consumers in P04+); the 7-channel montage of config v1 (PO7 excluded, PF-05) carries over. `team.yaml` flags corrected to `[]` (decisions.md 2026-10-24)
Owners (agents): signal-processing (Signal Processing), data-engineer (Data Engineer) — `mas/state/team_mapping.md`; verifier
Depends on: P01 (passed, cf1372b; merged to main f2b74ae)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** `run_preprocessing.py` + `psd_extraction.py`: condition windows with a
raw-stage quality gate and PSD features; the arrays every Era-A/B script consumes.
**Depends on:** P01. **Owners:** Signal Processing, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/preprocessing/signal/quality_check.py` (legacy part):
   - `validate_eeg_windows(windows, vpp_min=5.0, vpp_max=120.0, std_min=1.0,
     std_max=35.0) -> int mask` (1 if **every** channel has `vpp_min ≤ ptp ≤ vpp_max`
     and `std_min ≤ std ≤ std_max`);
   - `filter_dataset(X, y, mask)`;
   - `summarize_window_quality(...)` (prints observed Vpp/std ranges vs thresholds);
   - legacy helpers `window_quality_flags`, `segment_and_validate_eeg`.
2. `src/features/ssvep/psd_extraction.py`:
   - `extract_clean_subwindows_psd(segment, fs, sub_window_sec=1.0, vpp_thresh=200.0,
     std_range=(0.5, 60.0), quality_stats=None, vpp_min=0.5)`: slice the segment into
     `int(sub_window_sec*fs)` sub-windows, gate them with `validate_eeg_windows(...,
     vpp_min=vpp_min, vpp_max=vpp_thresh, std_min, std_max)` — **pass `vpp_min`
     explicitly** (PF-07) — and return records `{time_data, vpp, std, psd, freqs}`
     using `scipy.signal.periodogram`;
   - `process_condition_windows_with_baseline(eeg, mark, fs, target_conditions=(101..105),
     cue_condition=202, cross_condition=201, sub_window_sec=1.0, vpp_thresh=200.0,
     std_range=(0.5,60.0), stim_duration_sec=5.0, cue_lookback_sec=1.0,
     quality_stats=None)`: 202 → the `cue_lookback_sec` before each onset (only if
     complete); 101–105 → `stim_duration_sec` after each onset if it fits (fallback:
     contiguous plateaus if no rising edges are found); 201 → the 2.0 s after each onset;
   - `prepare_feature_matrix(records, target_conditions=(201,202,101,...,105),
     freq_range=(5,35)) -> (X_psd, X_time, y)` concatenating conditions in that order.
3. `scripts/preprocessing/run_preprocessing.py` with `--subject` (default S03) and
   `--all`: load `<subject>/OO.ebr`, take config scalp channels + MARK, broadband
   filter the **continuous** signal (config 1–60 Hz, order 4), extract condition
   windows with the legacy limits (vpp ≤ 200, std 0.5–60, vpp_min 0.5), print
   accepted/rejected counts and per-condition window counts, save
   `data/processed/<subject>/{X_psd_features,X_time_windows,y_labels}.npy`, and plot
   `outputs/figures/spectra/average_psd_by_condition.png`
   (`src/visualization/signal_plots.py::plot_average_psd_by_condition`, 1–60 Hz).
   Also write the S03 arrays to `data/processed/` root (the original's single-subject
   default location, used by early scripts).
4. `src/visualization/signal_plots.py`: `plot_eeg_window`, `plot_average_psd_by_condition`,
   `plot_stimulus_vs_baseline_psd`.

## Run (verbatim)

```bash
python -m scripts.preprocessing.run_preprocessing --all
```

## Outputs (verbatim, mas/phases.yaml)

`scripts/preprocessing/run_preprocessing.py`, `data/processed/<S>/{X_time_windows,X_psd_features,y_labels}.npy`, `outputs/figures/spectra/average_psd_by_condition.png`

## Acceptance (verbatim)

- Per subject: `X_time_windows` `(n, 7, 256)`, `X_psd_features` `(n, 217)`, `y` in
  `{201,202,101..105}`, `n ≤ 320`, label counts ≤ `{201: 80, 202: 40, 101–105: 40}`.
- Compare `n` with **R-1** (317–320 per subject); explain any difference.
- The PSD-by-condition figure shows peaks at the stimulation frequencies for at least
  S03–S05.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-1 | mas/04_REFERENCE_RESULTS.md | windows per subject S01 320, S02 318, S03 317, S04 317, S05 320; stimulus windows S01 200, S02 199, S03 200, S04 198, S05 200; 7 × 256; 217 PSD features. Tolerance: **exact** (window counts) |
| 01_DATA_SPEC §3, §5.1, §6 | mas/01_DATA_SPEC.md | onset rule; segment definitions; condition order 201, 202, 101–105, time order within; PSD 5–35 Hz inclusive, 31 bins, channel-major |
| PF-07 | mas/05_PITFALLS.md | the shared gate's default `vpp_min=5.0` must not reach the legacy gate: `vpp_min=0.5` passed explicitly; test: windows with Vpp 0.5–5 µV kept |
| PF-09 | mas/05_PITFALLS.md | the S03 root arrays must come from the same run as `data/processed/S03/`; lengths checked |
| PF-13 | mas/05_PITFALLS.md | the 202 "cue" window is the second *before* the 202 onset (end of fixation); keep and document it |
| PF-04 | mas/05_PITFALLS.md | P02 uses the header fs (256): 217 = 7 × 31 needs it; fs 250 enters with the P04/P05 extractors |
| PF-05, PF-06 | mas/05_PITFALLS.md | 7 channels from config v1, selected by name |
| R2 | mas/RULES.md | no fitting in P02 (the gate is fixed thresholds) |
| R3 | mas/RULES.md | already satisfied for the broadband filter: continuous, then window |
| R6 | mas/RULES.md | `(window, channel, time)` and channel-major PSD flatten proven by synthetic cases |
| R9, R10, R11 | mas/RULES.md | per-subject counts with data source (legacy, `OO.ebr`); cite; `after-attempt` |
| B005 | mas/state/blockers/ | `OO.ebr` is delivered for all five subjects; nothing missing for P02 |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| signal-processing | P02.1, P02.2, P02.4 (library functions) — first builder, creates the branch | `03_changes_signal-processing.md` |
| data-engineer | P02.3 (script), after signal-processing is READY | `03_changes_data-engineer.md` |
| synthetic-tester | known-answer tests of the plan | `04_tests.md` |
| scientific-reviewer | pre-run audit and results review (incl. the figure) | `07_review.md` |
| runner | run command | `05_run.md` |
| verifier | gate check | `06_verify.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
