# P20 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Reads: 00_assignment.md, 02_plan.md, 03_changes_deep-learning.md, 03_changes_ml-engineer.md, mas/RULES.md
Branch: phase/P20-detection-online
Commit(s): 7e9cdef (fix: P19 C-1, C-2), 718705c (feat: causal filter, dynamic stopping, pseudo-online), a358dc8 (test)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/online/__init__.py` | NEW | package marker | P20.6 | [own] |
| `src/online/causal_filter.py` | NEW | `design_sos` (Butterworth band-pass + `iirnotch` as one SOS cascade), `CausalSOSFilter` (stateful, `zi = sosfilt_zi * x[0]` on the first sample, carried), `filter_causal` (one pass), `replay_windows` (chunked stream, fixed-clock windows `[k*stride, k*stride+n)`, filtered and raw) | P20.6 | PF-38, R3 |
| `scripts/benchmarks/simulate_dynamic_stopping.py` | NEW | dynamic stopping on the sweep's `predictions.csv` | P20.5 | R8, PF-38 |
| `scripts/benchmarks/pseudo_online.py` | NEW | pseudo-online detector (train OO causal, replay mOO as a stream), 5 and 6 classes | P20.6 | PF-38, PF-39, R2, R3, R5 |
| `scripts/diagnostics/demo_edge_effects.py` | MODIFIED | passes `--quality-source filtered` explicitly to the build parser | P19 C-1 | R5 |
| `src/io/subject_data.py` | MODIFIED | `rejections_by_label[...]["raw"]` now `(reason == 3) & ~keep_local` | P19 C-2 | R5 |
| `tests/test_p20_data_signal.py` | NEW | C-1 and C-2 tests (3 tests) | P19 C-1, C-2 | [own] |
| `tests/test_p20_online.py` | NEW | dynamic stopping, causal filter, replay clock, pseudo-online scoring and CLI (8 tests) | plan tests 6-8 | [own] |

P20.1 needed no new code (below).

## Legacy behaviour implemented

None.

## Differences from the cited examples

No external example. The plan's `train/test` order in item 6 is "train, then check, then retrain"; here the label-free channel check runs on the replayed test stream first and the network is trained once without the dropped channels (same fitted model, no wasted fit). Output of the check is identical either way.

## Deviations from the plan

1. **P20.1 command works unchanged.** `scripts.build_windows --window-sec W --stride-sec 0.25` without `--out-root` writes `data/processed_continuous/w<W>_s0.25/<S>/` (name from `built_dir_name`: `w0.5_s0.25`, `w1_s0.25`, `w1.5_s0.25`, `w2_s0.25`, `w3_s0.25`, `w4_s0.25`), which is what the sweep reads. The only flag I would add is already in the plan (`--quality-source both`, P19 C-3). `--resume` skips finished subjects.
2. **`offset_sec` unit defect in the sweep (ml-engineer's file; I did not touch it).** `benchmark_window_sweep._prediction_frame` writes `offset_sec = d["offsets"]`, but `load_subject` returns `offsets` in SAMPLES (`window_offsets.npy` is `idx.offsets`, int64 samples, 0, 64, 128 at 256 Hz and stride 0.25 s). The ml-engineer's synthetic fixture uses seconds (`np.arange(wpt) * 0.25`), so the tests do not see it. On the real data `predictions.csv` would carry samples under the name `offset_sec`. `simulate_dynamic_stopping.py` therefore refuses such input (`offset_sec + window_sec` must end inside the 5 s stimulus; error text names the samples-for-seconds suspect) instead of mis-scaling. Required fix, one line in `benchmark_window_sweep.py`: `offset_sec = d["offsets"] / d["fs"]` (and a test on a fixture with sample-valued offsets). `benchmark_nn_sweep.py` line 103 reads `d["offsets"]` as well; it should be checked by deep-learning.
3. **Online quality tier without guard** (settled point 2): the decision uses only the channel tier and the window tier (Vpp/std) on the causal-filtered and the raw window (`--quality-source`, default config `both`), with every limit passed explicitly from the config; no artifact guard.
4. **Channel check timing.** The label-free check uses the first 30 s of the stream but the model without the dropped channel is applied to the whole replay, so trials ending within the first 30 s use a channel decision that a real online system would not yet have. The decisions file flags them (`before_check`), the summary counts them (`Trials before check`; 1 per subject for S01 in the smoke).
5. Summary columns: those of `02_REQUIREMENTS.md` §6 plus `Classes, Rest periods, Trials undecided, Trials before check, Fallback, Data source, Seconds` and a `Mean` row; the per-subject rows carry the data source (R9).
6. Decision semantics: 5 classes: first window whose cumulative-mean maximum over the five target classes is >= threshold, else forced at the last window; 6 classes (`--rest-class`): the rest class never decides, nothing reaching the threshold is "no target" (no forcing, `Missed (%)`, counted wrong in `Acc (%)`). `False act. (%)` = share of rest periods `[onset - 5 s, onset)` in which the same rule fires. Windows of a period: fully inside the period, `start >= period start + skip`; `time = start - period start + window` (the dynamic-stopping convention).
7. Dynamic stopping extra outputs: `best_threshold.csv` (the `Best (ITR)` rows of `cohort.csv`); `per_subject.csv` and `cohort.csv` carry every threshold with a `Best (ITR)` flag (ties: lowest threshold) and the data source. ITR uses accuracy pooled over the runs of a subject and T = mean decision time + 0.5 s.

## How to run / reproduce

Final CLIs (all from the repository root, `.venv/bin/python -m ...`):

```bash
# 1. sweep data, one command per window length (plan command, unchanged)
for W in 0.5 1 1.5 2 3 4; do .venv/bin/python -m scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp --quality-source both --window-sec $W --stride-sec 0.25; done

# 4. dynamic stopping (after the sweep; fix item 2 of the deviations first)
.venv/bin/python -m scripts.benchmarks.simulate_dynamic_stopping reports/window_sweep/predictions.csv \
  --thresholds 0.5 0.6 0.7 0.8 0.9 0.95 --skip-sec 0.5 --out-dir reports/dynamic_stopping
#    options: several predictions files, --gaze-sec 0.5

# 5-6. pseudo-online
.venv/bin/python -m scripts.benchmarks.pseudo_online --train-session OO --test-session mOO --model ccnn \
  --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --tag ccnn_5class
.venv/bin/python -m scripts.benchmarks.pseudo_online --train-session OO --test-session mOO --model ccnn \
  --window-sec 0.5 --stride-sec 0.25 --skip-sec 0.5 --threshold 0.6 --rest-class --tag ccnn_6class
#    options: --subjects, --check-sec 30, --fallback-window-sec 1, --min-val-acc 50, --quality-source,
#    --max-epochs 150, --patience 25, --no-augment, --device auto|cpu|cuda, --seed 42, --out-dir, --resume
```

Outputs: `reports/dynamic_stopping/{decisions,per_subject,cohort,best_threshold}.csv`; `reports/pseudo_online/summary_<tag>.csv`, `decisions_<tag>.csv` (part files `*.part_<S>.csv` exist only while a run is unfinished; `--resume` reuses them).

### Measured times (smoke runs, this machine, RTX 3050 4 GB; scratch outputs deleted)

P20.1, one subject (S01, OO), one build per window length into a scratch out-root, wall clock of the whole `python -m` call including start-up, `--banks fbcca fbcsp --quality-source both --stride-sec 0.25`:

| window (s) | wall (s) | build time in the log (s) | size S01 (MB) | size for 5 subjects (GB, estimate = 5 x S01; all recordings are ~154.9k samples) |
|---|---|---|---|---|
| 0.5 | 1.49 | 0.4 | 90.7 | 0.44 |
| 1 | 1.50 | not read | 143.8 | 0.70 |
| 1.5 | 1.60 | not read | 168.8 | 0.82 |
| 2 | 1.71 | not read | 175.1 | 0.85 |
| 3 | 1.72 | not read | 168.8 | 0.82 |
| 4 | 3.53 | 0.8 | 125.1 | 0.61 |

Total for six roots and five subjects: about 4.3 GB (`du` of the six S01 folders: 873 MB; 4.26 GB from the table) and well under one minute of compute. (Sizes: `du -sk`; S01 build logs `mas/state/scratch/p20ds/build_*.log`, deleted with the scratch.)

P20.6 pseudo-online, S01 only, 5 classes, defaults (`--window-sec 0.5`, up to 150 epochs, patience 25, GPU): `S01: 9.8 s` (wall 12.0 s with start-up and imports; best epoch 88 of 113 epochs run; 760 training windows; val acc 71.7 %); 6 classes `--rest-class`: `17.6 s` (wall 19.9 s; 1520 training windows; 111 epochs). With `--max-epochs 3` and `10` (fallback triggered, two fits): 2.2 s and 3.1 s. CPU (`--device cpu --max-epochs 5`, fallback triggered, two fits): 2.5 s. Extrapolation to the phase run (5 subjects x 2 variants, full epochs, GPU): 5 x 9.8 + 5 x 17.6 = 137 s of compute plus 2 start-ups, about 2.5 min; a fallback retrain at 1 s windows adds one more fit per affected subject (a few seconds). On CPU about 0.25 s per epoch per fit in the 5-epoch smoke, so at most about 40 s per fit, 2 x 5 x ~40 s ~ 7 min, plus fallbacks. Both variants are far inside the budget; nothing is a human-run candidate.

Dynamic stopping: pure pandas, a few seconds on the sweep's `predictions.csv` (not run on the real file, which does not exist yet).

## Decisions

1. Causal filter: the cascade is the config band-pass (order 4, 1-90 Hz) followed by the 60 Hz notch (Q 30) as SOS; `zi = sosfilt_zi * x[0]` per channel initialised on the first sample of the stream; used identically on the training run (one pass) and on the test stream (chunks of one stride).
2. Fixed clock: window `k` = stream samples `[k*stride, k*stride + n)`, independent of events; the replay hands out a window the moment its last sample has arrived. Predictions are made in batch afterwards, which is allowed because every window holds past samples only (PF-38).
3. The test run's MARK is read only in `score_stream`; `predict_stream` and `run_window_length` take no MARK (test: predictions identical when the MARK is erased).
4. Training set: causal-filtered target windows of every complete 5 s target segment (`--window-sec`, `--stride-sec`); with `--rest-class` also windows of `[onset - 5 s, onset)` as class 5; trial ids are one per segment; validation by `fit_network` (grouped, 20 %, PF-32). Channel and window tiers on filtered and raw windows with the config limits, no guard.
5. Fallback: `Window (s)` of the summary says which window length produced the row; the checks and replay are redone at the fallback length.
6. Dynamic stopping fails loudly on `offset_sec` that cannot be seconds (deviation 2), on duplicate window rows across input files, on several `true` labels in a trial, and on non-finite probabilities.
7. Reference consultations (R11): none. `reference/ssvep-eeg-xai/` was not opened.

## How I verified

`.venv/bin/python -m pytest tests/test_p20_online.py tests/test_p20_data_signal.py -q -o addopts=""`: `11 passed in 4.34s`.

- **C-1** (`test_demo_edge_effects_passes_quality_source_filtered_explicitly`): the params that reach `build_subject` carry `quality.source == "filtered"` while the config default is `both` (the historical call gives `both`).
- **C-2** (`test_rejection_counts_sum_to_total_minus_valid[shared, shared-no-guard]`): on a built folder whose reasons are planted (raw-guard-only kept without guard, raw gate, own gate, filtered guard), `own_gate + guard + raw == total - valid` per label in both modes, and the counts are the planted ones. The test failed on the historical code before the fix (`(1 + 0) + 2 == 10 - 8`).
- **Plan test 6** (`test_dynamic_stopping_*`): hand-built windows given out of order and with a before-skip trap give decisions 101 at 1.25 s (threshold 0.5), 101 at 1.5 s (0.6), forced 1.5 s (0.7, 0.95); reversed input identical; the unsorted and the no-skip variants give other answers; per-subject / run / trial grouping with a shared trial id, fbcca skipped, ITR = log2(5)*60/2.0, cohort mean 50 %; ITR equals the sweep's helper; sample-valued offsets are refused.
- **Plan test 7 (the causal-filter test, `test_causal_filter_chunked_equals_one_pass_and_is_causal`)**: chunked stateful filtering equals one-pass `sosfilt` with `zi = sosfilt_zi * x[0]` (max |diff| <= 1e-10, 9 irregular chunks incl. size 1 and 7); an impulse at t0 changes no output before t0 (<= 1e-10) and changes the next samples; `zi * x[0]` removes the transient of a 1000 uV offset (< 1e-6) while zero state rings (> 100); `sosfiltfilt` (the zero-phase historical path) responds before the impulse, so the test fails on it. `test_replay_windows_fixed_clock_and_chunk_independent`: window starts `k*64`, windows equal the causal-filtered slices (<= 1e-10), raw windows equal the raw slices, for chunks 64, 37, 500.
- **Plan test 8** (`test_pseudo_online_fixed_clock_and_decisions_in_the_right_periods`): on a synthetic stream with a known MARK, the clock equals `k*64`, every stimulus period is decided correctly at 1.0 s, trap windows starting before the onset never enter, the single planted rest period is the only false activation and each rest period ends at its onset; uniform probabilities give forced decisions at 5.0 s with 5 classes and "no target" with 6; rejected windows are skipped and the period is undecided (counted in `Trials undecided`). `test_pseudo_online_cli_*`: end to end on fake recordings (CPU, 3 epochs): predictions identical with the test MARK erased; a channel bad only in the test stream is dropped by the check (`Dropped at check` 1, `Channels kept` 7); PF-39 warning for OO -> C, none for OO -> mOO; columns and `Mean` row; no part files left. `test_pseudo_online_channel_check_uses_only_the_first_seconds`: a channel bad only after 30 s is kept, one bad inside is dropped.

Full suite, `.venv/bin/python -m pytest tests/ -q -o addopts=""` (log `mas/state/scratch/p20ds/suite.log`):

```
1274 passed, 22 warnings in 759.26s (0:12:39)
```

Smoke on real S01 (project script only; outputs in `mas/state/scratch/p20ds/`, deleted): 5 classes, window 0.5 s, GPU, full epochs: `S01: window 0.5 s, channels kept ['PO3', 'POz', 'PO4', 'PO8', 'O1', 'Oz', 'O2'], dropped at check [], training windows 760, val acc 71.7 %, best epoch 88/113 epochs`, 40 trials, Acc 57.5 %, Time 2.43 s, Forced 30 %, False act. 57.5 %, Windows rejected 0.55 %. These are smoke numbers on one subject, reported for timing only; no interpretation (R-16, golden rule 5).

## Questions
ACK 00_assignment.md data-signal 2026-10-28

to orchestrator / ml-engineer: deviation 2 (`offset_sec` in samples in `benchmark_window_sweep.py`) must be fixed before the sweep run, otherwise dynamic stopping on the real `predictions.csv` refuses to run. To deep-learning: check `benchmark_nn_sweep.py:103` for the same unit.
