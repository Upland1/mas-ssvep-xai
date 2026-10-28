# P19 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Branch: phase/P19-raw-quality

## Files
- MODIFIED `src/preprocessing/window_quality.py`: `source` in `PARAM_KEYS` (required, no default; unknown value raises); `quality_params_from_config` reads `quality.source`; `subject_quality_gate(..., raw_windows=None, raw=None)`; `AllChannelsDropped(ValueError)`; `REASONS[3] = "raw"`.
- MODIFIED `scripts/build_windows.py`: `--quality-source {filtered,raw,both}`, `--overwrite` (C-a), `diff_build_params`, skip message, meta fields, per-source console line.
- MODIFIED `configs/pipeline_config.yaml` and `mas/02_REQUIREMENTS.md` §3: `quality.source: both`.
- MODIFIED `src/io/subject_data.py`: data-source string ends `, quality source <s>` (`filtered` for folders without it). One addition beyond the string: the loader's `rejections_by_label` gets a `raw` count (reason 3), otherwise it would not sum to the rejected total.
- NEW `tests/test_p19_raw_quality.py`. Existing tests adapted: `test_p01_config_known_answer.py` (default `both`), `test_p16_window_quality.py`, `test_p16_independent_known_answer.py` (`source` in PARAMS), `test_p16_build_windows.py` (a differing-param rebuild now needs `--overwrite`), `test_p17_windowing.py` (`data_source` string).

## Decisions (settled points 1-9 of 02_plan.md, as implemented)
- Channel tier: stats per checked signal with `compute_channel_quality_stats`, a channel dropped if it exceeds `channel_fail_fraction` on any of them; window tier (`validate_eeg_windows`) and artifact blocks on surviving channels, per checked signal, one `guard_sec` (auto = ringing of the continuous filters; raw has none).
- Reasons: 1 filtered gate, 2 filtered guard, 3 raw gate or raw guard only if no filtered check failed. `valid_mask_no_guard` = all gates pass. With `source=filtered` the code path equals the P16 pipeline.
- Returned: `n_raw_gate`, `n_raw_guard`, `*_raw` artifact stats, `channel_stats_raw`; meta `quality` has `source`, `n_reason3_raw_gate/_guard`, raw artifact stats. With `source=raw`, `channel_stats`/`artifact_*` refer to the raw signal.
- `build_params` includes `quality.source`; C-a refuses upfront (before any subject is built) if any existing folder's recorded params differ (names the keys, e.g. `quality.source`; a folder from before P19 lacks the key so it differs and needs `--overwrite`); identical + `--resume` skips.
- All channels dropped: `[-] Skipping <S>: all channels dropped (source=<s>)`, nothing written; exit 1 only if no subject was built.
- Thresholds unchanged.

## Tests (`tests/test_p19_raw_quality.py`)
1 raw-only drift (valid under filtered, reason 3 under raw/both); 2 filtered-only failure keeps reason 1 under both; 3 raw artifact block: windows 29/30/31 exactly, 1 raw_gate + 2 raw_guard, none under filtered; 4 channel bad only on raw; 5 `filtered` byte-identical to `apply_artifact_quality_pipeline` and ignoring raw (fails on a gate that ignores `source`: `both` must give reason 3 on the drift windows); 6 missing/unknown source, missing raw args, config; config default `both`; 7 `rejections_by_label` 1/2/3 sums to rejected; 8 C-a refuse/resume/overwrite via `main`; 9 skip message and no files; also an all-dropped `AllChannelsDropped` unit test and a clean-subject filtered-vs-both build comparison.

## Suite
`.venv/bin/python -m pytest tests/ -q -o addopts=""`: `1 failed, 1217 passed, 22 warnings in 754.48s (0:12:34)`. The failure was `test_p17_windowing.py::test_per_window_build_is_labelled_legacy` (exact `data_source` string); fixed, that file now `10 passed in 1.90s`. The full suite was not re-run after that one-line test fix.

## Smoke (S01 only, scratch out-root, deleted; four banks)
| source | windows | valid | reasons 1/2/3 | channels dropped | raw artifact blocks | build time |
|---|---|---|---|---|---|---|
| filtered | 320 | 320 | 0/0/0 | PO7 | n/a (filtered 3 blocks, 0.12%) | 0.9 s |
| raw | 320 | 320 | 0/0/0 | PO7 | 11 (0.45%, 0.63% guarded) | 0.8 s |
| both | 320 | 320 | 0/0/0 | PO7 | 11 | 0.8 s |

On S01 the raw check rejects nothing. `source=filtered` files (valid_mask, valid_mask_no_guard, reject_reason, X_time, X_raw, fbcca, harmonic) are `cmp`-identical to `data/processed_continuous_p17/S01`.

## Runtime estimate
About 1 s per subject per build including the read; the 3 builds for S01-S05 about 15 s in total (other subjects may differ). Suite about 12.5 min. Benchmarks about 5 min as in P17.
