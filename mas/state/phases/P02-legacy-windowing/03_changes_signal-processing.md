# P02 · 03 · Changes — signal-processing

Status: READY
Author: signal-processing
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/state/decisions.md (P02 rows), mas/01_DATA_SPEC.md §3, §5.1, §6, mas/02_REQUIREMENTS.md §3, §4, §7, mas/04_REFERENCE_RESULTS.md R-1, mas/05_PITFALLS.md PF-04/05/06/07/09/13
Branch: phase/P02-legacy-windowing (from main @ f2b74ae)
Commit(s): 4ad76e9 (chore: bookkeeping), 00da841 (P02.1), 464af9a (P02.2), 1285293 (P02.4), 08bb4c2 (smoke tests)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/preprocessing/signal/quality_check.py` | NEW | `validate_eeg_windows` (signature/defaults verbatim, inclusive bounds, int mask), `filter_dataset`, `summarize_window_quality`, legacy helpers `window_quality_flags`, `segment_and_validate_eeg`; `quality_stats` accumulator helpers `new_quality_stats`, `ensure_quality_stats`, `update_quality_stats`, `merge_quality_stats`, `format_quality_stats` | P02.1 | [1], [3], PF-07, R5 |
| `src/features/ssvep/psd_extraction.py` | NEW | `find_event_onsets` (§3 rule + plateau fallback), `extract_clean_subwindows_psd` (forwards `vpp_min` explicitly), `process_condition_windows_with_baseline`, `prepare_feature_matrix` (order 201, 202, 101–105; 5–35 Hz inclusive; channel-major) | P02.2 | [1], [2], [4], PF-07, PF-13, R6 |
| `src/visualization/signal_plots.py` | NEW | `plot_eeg_window`, `plot_average_psd_by_condition` (default 1–60 Hz), `plot_stimulus_vs_baseline_psd`; `matplotlib.use("Agg")`, saved and closed, never shown | P02.4 | [1], [3] §4 |
| `tests/test_p02_signal_smoke.py` | NEW | 8 builder smoke tests (gate bounds, PF-07, sub-windows/PSD/stats, segments with 1- and 3-sample pulses, edges, helpers, plots) | P02.1/2/4 | [3] §7, [own] |

## API for `scripts/preprocessing/run_preprocessing.py` (data-engineer)

```python
from src.preprocessing.signal.filters import apply_iir_bandpass
from src.features.ssvep.psd_extraction import process_condition_windows_with_baseline, prepare_feature_matrix
from src.preprocessing.signal.quality_check import new_quality_stats, merge_quality_stats, format_quality_stats, summarize_window_quality
from src.visualization.signal_plots import plot_average_psd_by_condition, plot_stimulus_vs_baseline_psd

x_f = apply_iir_bandpass(x, fs, lowcut, highcut, order)          # continuous (C, T), R3
qs = new_quality_stats()
records = process_condition_windows_with_baseline(
  x_f, mark, fs, target_conditions=(101, 102, 103, 104, 105), cue_condition=202,
  cross_condition=201, sub_window_sec=1.0, vpp_thresh=200.0, std_range=(0.5, 60.0),
  stim_duration_sec=5.0, cue_lookback_sec=1.0, quality_stats=qs,
  vpp_min=0.5, cross_duration_sec=2.0)          # pass all from config / CLI (R5, PF-07)
X_psd, X_time, y = prepare_feature_matrix(records, target_conditions=(201, 202, 101, 102, 103, 104, 105), freq_range=(5.0, 35.0))
print(format_quality_stats(qs, channel_names))   # per condition, per reason, each rejected window
plot_average_psd_by_condition(records, out_png, freq_range=(1.0, 60.0))
```

- **records**: `{code: [record, ...]}`, keys 201, 202, then the targets (empty lists kept), each list in time order. A record is `time_data (C, n)`, `vpp (C,)`, `std (C,)`, `psd (C, F)`, `freqs (F,)`, `sub_index`, `condition`, `onset` (event onset sample), `start` (absolute start sample of the sub-window in the continuous recording). `start` lets the script test R3 (`X_time[i] == x_f[:, start:start+n]`).
- **prepare_feature_matrix** returns `X_psd (n, C*F)` float64, `X_time (n, C, T)` float64, `y (n,)` int64; at fs 256 and 7 channels `F = 31`, 217 features; feature `c*31 + j` = channel c, `5 + j` Hz. With no records it returns `(0, 0)`, `(0, 0, 0)`, `(0,)` rather than raising (P07 reproduces a run where every window is rejected).
- **quality_stats** (dict, updated in place): `n_total`, `n_accepted`, `n_rejected`; `reasons` {`vpp_low`, `vpp_high`, `std_low`, `std_high`}: rejected windows failing each reason on any channel, so one window can count under more than one reason; `by_condition` {code: the same four keys}; `rejected`, a list of `{condition, onset, start, sub_index, reasons, channels}` with channels as indices that `format_quality_stats(qs, channel_names)` turns into names; `skipped_segments`, a list of `{condition, onset, why}` for segments that fall outside the recording. For a cohort line, merge per-subject accumulators with `merge_quality_stats(cohort, qs)`. For R-1, rejected sub-windows (`rejected`) and segments that do not fit (`skipped_segments`) are listed separately.
- `summarize_window_quality(X_time_all, vpp_min=, vpp_max=, std_min=, std_max=, label=S)` prints the observed Vpp/std ranges against the limits (PF-07 diagnostic). To include rejected windows, give it the ungated windows. `segment_and_validate_eeg` cuts non-overlapping windows if you need them.
- Config v1 has no `vpp_min` key. The roadmap value 0.5 has to come from a CLI default or a script constant labelled legacy, and must be passed explicitly.

## Legacy behaviour implemented

None from the era matrix. The shared default `validate_eeg_windows(vpp_min=5.0, …)` is in place verbatim (PF-07 regression state). The legacy path is immune to it because `extract_clean_subwindows_psd` passes `vpp_min=vpp_min` (default 0.5) and `process_condition_windows_with_baseline` forwards its own `vpp_min` explicitly. P07 can reproduce the regression by passing `vpp_min=5.0` (no extra flag is needed in P02). The channel count is never hardcoded: everything follows `C` of the input.

## Differences from the cited examples

`scipy.signal.periodogram(x, fs=fs, axis=-1)` uses the library defaults (boxcar window, constant detrend, density scaling, onesided) [5]. At n = fs = 256 the bins are 1 Hz apart and 5–35 Hz inclusive gives 31 bins.

## Deviations from the plan

1. `process_condition_windows_with_baseline` gains two trailing keyword arguments after the verbatim ones. `vpp_min=0.5` is forwarded explicitly (R5, PF-07). `cross_duration_sec=2.0` is the 201 duration, config `pre_stim_cross_sec`. Both defaults equal the roadmap values, so a verbatim call behaves the same [own: every threshold reachable from the config].
2. Records carry extra keys `sub_index` (also from `extract_clean_subwindows_psd`), `condition`, `onset` and `start`. They are additive and used for the R3/PF-13 checks and the R-1 explanation [own].
3. These extra public names are not in the roadmap: `find_event_onsets`, the `quality_stats` helpers, `REJECT_REASONS`, `STIM_FREQS_HZ`, `CONDITION_NAMES`. The new helpers (`window_quality_flags`, `segment_and_validate_eeg`, `summarize_window_quality`) take their thresholds as **required** keywords, so nothing can inherit one (R5).
4. The plot functions take a required `save_path` and return the saved `Path`. The roadmap gives names only.
5. Fallback onset rule: under the §3 rule (`diff(mark, prepend=0) != 0`), every plateau starts with an edge, so the plateau fallback runs only for a MARK that has `code` samples but no edge. That case cannot occur, and the fallback is kept only for roadmap fidelity (documented in the docstring).

## How to run / reproduce

```bash
.venv/bin/python -m pytest tests/test_p02_signal_smoke.py -q
.venv/bin/python -m pytest tests/ -q
```

## How I verified

- `.venv/bin/python -m pytest tests/ -rN` → `256 passed in 6.56s`. `tests/test_p02_signal_smoke.py -rA` → `8 passed in 1.77s`.
- Synthetic recording with the §3 timing (40 trials, 8 per target, fs 256, 7 channels, channel c = 10 µV sine at 5 + 3c Hz). Counts were `{201: 80, 202: 40, 101: 40, 102: 40, 103: 40, 104: 40, 105: 40}`, shapes `(320, 217) (320, 7, 256) (320,) int64`, and the per-channel PSD argmax `[0, 3, 6, 9, 12, 15, 18]` (channel-major, R6). For the 202 window, `onset - start = 256` (PF-13), and its `time_data` equals the slice of the input.
- PF-07: a 1 s sine with Vpp ≈ 2 µV is rejected by `validate_eeg_windows` defaults (mask `[0]`). It is kept by `extract_clean_subwindows_psd` (1 record) and dropped when `vpp_min=5.0` is forwarded (0 records).
- A 300 µV spike in sub-window 2 of a 5 s, 10 Hz segment gives records `[0, 1, 3, 4]` and `n_rejected == 1` (reason `vpp_high`, channel 0). Freq step 1.0 Hz, peak 10.0 Hz.
- Figures were rendered from synthetic records (noise plus planted f0 sinusoids) and inspected by eye. Peaks sit at 24/20/15/10.91/8.57 Hz on the dotted f0 lines and the legend is readable. The categorical colours passed a colour-contrast/colour-vision palette check (7 slots, light mode): all hard checks passed. Contrast against the white background was below 3:1 for three of the colours, so a legend and linestyles provide secondary encoding.
- Nothing ran on real data.

## Left to do / known limitations

- The PSD-by-condition figure averages over all channels (`channels=None`); a visual-cluster subset can be passed by index. The figure is not split per channel.
- `summarize_window_quality` computes its observed ranges over the windows it is given. It does not see segments that were skipped for not fitting the recording (those are in `quality_stats["skipped_segments"]`).

## Reference consultations (R11)

None. `reference/ssvep-eeg-xai/` was not opened.

## Sources

1. REQUEST — `mas/03_ROADMAP.md` P02 tasks 1, 2, 4 (as copied in `00_assignment.md`), signatures and defaults.
2. REQUEST — `02_plan.md` work split and segment definitions.
3. RULE — `mas/02_REQUIREMENTS.md` §4 (library conventions, Agg plots), §7 (tests); `mas/RULES.md` R3, R5, R6; `mas/05_PITFALLS.md` PF-07, PF-13.
4. RULE — `mas/01_DATA_SPEC.md` §3 (onset rule, timing, stimulation frequencies), §5.1 (segments, order, 217 features).
5. DOCS — SciPy v1.18.1, `scipy.signal.periodogram` docstring (signature `(x, fs=1.0, window='boxcar', nfft=None, detrend='constant', return_onesided=True, scaling='density', axis=-1)`), read via `inspect` in `.venv`. Used for: PSD defaults and the 1 Hz bin spacing.

## Questions

ACK 02_plan.md signal-processing 2026-10-24

to data-engineer: config v1 has no `vpp_min` key (see the API notes). Please expose it as a CLI default of 0.5 labelled legacy and pass it explicitly. Pass `cross_duration_sec` from `preprocessing.baseline.pre_stim_cross_sec`.

Answer (data-engineer, 2026-10-24): done in `scripts/preprocessing/run_preprocessing.py` @ 5d6767e. `--vpp-min` defaults to `LEGACY_VPP_MIN_UV = 0.5` (module constant labelled legacy, PF-07) and is passed as `vpp_min=params["vpp_min"]`. `cross_duration_sec` comes from `preprocessing.baseline.pre_stim_cross_sec` (CLI `--cross-duration-sec`).
