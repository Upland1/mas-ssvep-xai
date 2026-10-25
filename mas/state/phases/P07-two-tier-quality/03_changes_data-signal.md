# P07 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/01_DATA_SPEC.md §5.1, mas/02_REQUIREMENTS.md §3-§4, mas/05_PITFALLS.md PF-05..PF-10, decisions.md P02-P07
Branch: phase/P07-two-tier-quality (from main @ 201f85c)
Commit(s): 076375e (bookkeeping), 999fc88, 0bd7429, ddbed31, b4efa31, a2ff2e9

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| src/preprocessing/signal/quality_check.py | MODIFIED | `compute_channel_quality_stats`, `identify_noisy_channels`, `drop_noisy_channels`, `apply_artifact_quality_pipeline`, `LIMIT_KEYS` | P07.1 | [1], PF-06, PF-10 |
| src/io/channels.py | NEW | `FULL_MONTAGE`, `resolve_channel_names(n)`, `legacy_scalp(names)` | P07.3 | [1], PF-05 |
| configs/pipeline_config.yaml | MODIFIED | v2: 8 scalp channels (montage order), `excluded: []`, version comment on line 1 | P07.3 | [2] §3 |
| scripts/preprocessing/run_preprocessing.py | MODIFIED | tier-1 detection, flags, ungated summary, stale removal, `channels.json` | P07.4, P07.5 | [1], PF-07, PF-09 |
| src/features/ssvep/harmonic_psd.py | MODIFIED | `check_keep_channels` reduces an 8-name list to the 7 legacy names | P07.3 | PF-06 |
| scripts/benchmarks/feature_based/{benchmark_5_subjects,benchmark_cross_validation,benchmark_feature_selection,benchmark_harmonic_fbcca}.py, scripts/evaluation/{evaluate_confusion_matrix,test_sklearn_models}.py, scripts/exploration/{diagnose_occipital_spectra,visualize_data}.py | MODIFIED | one line each: `scalp = legacy_scalp(cfg[...])` (legacy 7-channel arrays under config v2); ml-engineer replaces with `resolve_channel_names(X.shape[1])` / saved names in its 4-value rework | P07.3 | PF-05 |
| tests/test_p07_quality_signal.py | NEW | 13 fast tests (see below) | all | — |
| tests/test_p01_config_known_answer.py, test_p01_ebr_known_answer.py, test_p01_parser_smoke.py, test_p02_preprocessing_smoke.py, test_p02_windowing_known_answer.py, test_p03_exploration_known_answer.py | MODIFIED | follow config v2 (8 channels; legacy 7-name lists where they test the legacy arrays) | — | — |

## APIs (for the ml-engineer)

`src/preprocessing/signal/quality_check.py` (windows `(n, C, T)`, channels by name, PF-06):

- `compute_channel_quality_stats(windows, channel_names, limits) -> {name: {fail_fraction, n_failed, mean_vpp, mean_std}}`; `limits` = dict with all of `vpp_min, vpp_max, std_min, std_max` (missing key -> ValueError, R5).
- `identify_noisy_channels(windows, channel_names, limits, fail_fraction_thresh=0.5) -> [names]`, strictly `>` (exactly 50 % keeps the channel).
- `drop_noisy_channels(windows, channel_names, noisy) -> (windows_kept, kept_names, kept_idx)`.
- `apply_artifact_quality_pipeline(windows, y, channel_names, vpp_min=5.0, vpp_max=120.0, std_min=1.0, std_max=35.0, channel_fail_fraction_thresh=0.5, verbose=True, precomputed=None) -> dict` with keys `windows_clean (n_valid, C', T)`, `y_clean`, `valid_mask (n,)` int 1/0 over the INPUT windows, `channels_kept`, `channels_kept_idx` (input positions), `channels_dropped`, `channel_stats`. Tier 1 judges all windows on all channels; tier 2 judges windows on kept channels only. All channels dropped -> ValueError. `precomputed=<earlier result>` reuses `channels_kept` and `valid_mask` (length-checked) for another block (PF-10); the reused `channel_stats` are those of the producing call. `verbose` prints the per-channel report (fail %, mean Vpp/std, DROPPED).

`src/io/channels.py`: `resolve_channel_names(n)` (8 full montage, 7 without PO7, else None); `legacy_scalp(cfg_scalp)` (config list minus PO7); `FULL_MONTAGE`.

`scripts/preprocessing/run_preprocessing.py` (importable): `detect_noisy_channels(x_filtered, fs, names, limits, fail_fraction)`, `ungated_windows(...)`, `preprocess_recording` now also returns `channels_kept`, `channels_dropped`, `channel_report`, `ungated`; `save_channels`, `remove_stale_outputs`, `format_channel_report`. Outputs per subject: the three arrays plus `channels.json` ({kept, dropped, fs}); `X_time` has only the kept channels, in montage order.

## Flags of run_preprocessing

- `--vpp-min` (default 0.5, pinned; `5.0` prints `[!] legacy regression demo (PF-07)`).
- `--no-channel-drop`; `--chan-vpp-min/-max` (5/200), `--chan-std-min/-max` (0.5/60), `--chan-fail-fraction` (0.5), window 1 s non-overlapping on the whole filtered recording.
- `--no-figures` already existed; with it, writes happen only under `--processed-dir`. Without it figures go to `--figures-dir` (default `outputs/figures`).

## Legacy behaviour implemented

PF-07 regression behind `--vpp-min 5.0` (labelled in the console). Legacy 7-channel arrays are read through `legacy_scalp`/`resolve_channel_names(7)`. `data/processed/` is not touched; no run of mine targets it.

## Differences from the cited examples

None (no reference code opened).

## Deviations from the plan

1. Config v2 has no new key (thresholds of tier 1 are CLI defaults/constants in run_preprocessing, since `mas/02_REQUIREMENTS.md` §3 P07 only specifies the channel change).
2. I changed 8 consumer scripts by one line each (`legacy_scalp`) and six existing tests, because config v2 (8 names) would otherwise break every consumer of the 7-channel legacy arrays (19 test failures observed before the fix). This is not the 4-value rework.
3. `test_channel_count_mismatch_fails_loudly` (P03) now builds a real mismatch (6 names) because 8 config names are reduced to 7 by design.

## How to run / reproduce

```bash
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --processed-dir data/processed_p07_demo/vppmin5 --no-figures
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --no-channel-drop --processed-dir data/processed_p07_demo/vppmin5_nodrop --no-figures
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --processed-dir data/processed_p07_demo/pinned --no-figures
```

Caution for the verifier: with tier 1 active, the `--vpp-min 5.0` run may no longer reject all 320 windows (a chronically low-Vpp channel is dropped first, or, if every channel is low, the subject is skipped with `every channel is chronically noisy`). The original PF-07 regression had no tier 1; the exact reproduction is the `--no-channel-drop` command. Report both. Do not point `--processed-dir` at `data/processed` (a skipped subject has its old arrays removed there).

## How I verified

- `tests/test_p07_quality_signal.py` (13 tests, about 0.3 s): strict 50 % boundary (5/10 kept, 6/10 dropped), analytic channel stats (1e-9), tier 2 ignores a dropped channel while a bad window on a kept channel is rejected, return-dict keys and `channels_kept_idx` layout with a dropped middle channel (PF-06/R6), `precomputed` reuse on a different block (PF-10), `resolve_channel_names` 8/7/6/9, PF-07 (Vpp 2 uV kept at 0.5, rejected at 5.0, default pinned), end-to-end chronic-noise drop with `channels.json`, ungated summary `39/40 windows valid, 1 rejected`, stale-output removal, no writes outside `--processed-dir`.
- The PF-07 and PF-09 tests fail on the historical behaviour (extractor not forwarding `vpp_min`; stale arrays remaining).
- Full suite `.venv/bin/python -m pytest tests -q` at commit a2ff2e9: no failures (log `mas/state/scratch/p07_ds_suite2.log`, 100 % progress, zero FAILED lines). Runtime about 8 min (the cut is the ml-engineer's task).

## Left to do / known limitations

- No real-data run (verifier). Real S03/S04 behaviour of tier 1 limits 5-200/0.5-60 is unmeasured.
- Extractors still return 3 values and consumers still use the P05 gate; the ml-engineer does P07.2, P07.6 and the runtime cut.
- `ungated_windows` re-runs the segmentation (periodograms included); cost is small.

## Reference consultations (R11)

None.

## Sources

1. `mas/03_ROADMAP.md` P07 tasks 1, 3, 4, 5 (as quoted verbatim in 00_assignment.md, opened in this run).
2. `mas/02_REQUIREMENTS.md` §3 (config v1, P07 override) and §4 (opened in this run).
3. `mas/05_PITFALLS.md` PF-05 to PF-10 (opened in this run).

## Questions

ACK 02_plan.md data-signal 2026-10-25
