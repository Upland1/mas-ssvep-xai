# P07 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Audited `git diff main...HEAD` at 2a3fa20 against mas/03_ROADMAP.md P07, mas/01_DATA_SPEC.md
§5.1/§6, mas/02_REQUIREMENTS.md §3/§4/§6, mas/04_REFERENCE_RESULTS.md R-1/R-5/R-6,
mas/05_PITFALLS.md PF-05–PF-10 and decisions.md P05–P07. P07 test files re-run here:
`.venv/bin/python -m pytest tests/test_p07_known_answer.py tests/test_p07_quality_signal.py tests/test_p07_ml_engineer.py -q -p no:cacheprovider`
→ 35 passed. No raw data read, no real-data run, no reference access.

Verdict: FAIL

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | LEGACY (by design) | `src/models/classical/legacy_eval.py:29,35-37` `StratifiedKFold(5, shuffle, 42)` over windows, labelled; roadmap P07.6 "Still `StratifiedKFold` here"; `benchmark_n_subjects.py:12-13,172` says "NOT comparable with the leak-free R-6" |
| R2 Fit only in-fold | PASS | CSP fitted per fold `legacy_eval.py:63`, scaler+LDA per fold `:109`; the gate fits nothing (fixed limits, no labels: `quality_check.py:235-313`); full-data CSP only in `extract_fbcsp_features` (visualization, labelled `fbcsp_extraction.py:130-132`) |
| R3 Filter continuous, then window | LEGACY (by design) | preprocessing filters the continuous recording before tier 1 and windows (`run_preprocessing.py:235`, `apply_iir_bandpass` then `detect_noisy_channels`); extractor sub-bands per window (`fbcsp_extraction.py:45`, FBCCA cheby1 per window), labelled R3/PF-14 |
| R4 Estimator small-sample bias | N/A | no coherence/PLV in P07 |
| R5 Shared quality decision, explicit thresholds | PASS (per-script gate = LEGACY (by design)) | every limit explicit: `window_mask.py:22-27`, `quality_check.py:169-174` (missing key → ValueError), tier-1 limits `run_preprocessing.py:81` passed by name; PF-07 pin `run_preprocessing.py:78,253` and `psd_extraction.py:53`; tier 1 strictly `>` over all windows on all channels `quality_check.py:283`, tier 2 on kept channels only `:288-289`; one decision per script handed to every block via `precomputed` (`feature_spaces.py:46-65`), spy test `test_p07_known_answer.py:96-111` |
| R6 Index layouts verified | **FAIL** | new code: `channels_kept_idx` (`quality_check.py:291`), PSD column `c*F+j` on kept channels (test `test_p07_ml_engineer.py:64`), harmonic/FBCCA by name after a drop (`feature_spaces.py:56-64`) — all proven. But the P04 positional selection `harmonic_psd.py:24,55-68` (`KEEP_CHANNELS=(1,4,5,6)`) is now checked only against the **config** list, which `check_keep_channels` reduces from 8 to 7 names (`harmonic_psd.py:37-38`); callers `scripts/training/train_models.py:306`, `batch_run_subjects.py:96`, `scripts/xai/run_xai.py:130`, `train_final_model.py:123` never look at the subject's array names. On a P07-built folder with one tier-1 drop (7 channels, e.g. PO8 dropped) the positions select `['PO3', 'O1', 'Oz', 'O2']` instead of POz/O1/Oz/O2 with no error (shown: `.venv/bin/python -c "n=['PO7','PO3','POz','PO4','PO8','O1','Oz','O2']; k=[c for c in n if c!='PO8']; print([k[i] for i in (1,4,5,6)])"`) — PF-06, fix 2 |
| R7 Honest statistics | N/A | no permutation statistics |
| R8 Smoothing respects trials | LEGACY (by design) | `legacy_eval.py:30` i%5 on the clean array (roadmap "smoothing" convention §5.6 on legacy folders; decisions.md P05 carry-forward to P11) |
| R9 Per-subject reporting with data source | PASS | per-subject row with kept count and dropped names `benchmark_n_subjects.py:108-111`, per-channel report printed per subject (`quality_check.py:302-312`, `verbose=True` at `:94`), data source line `:142` and `.meta.txt` `:167`; preprocessing prints the tier-1 report per subject (`run_preprocessing.py:334-343,499`) and saves `channels.json` |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | handoffs cite 03_ROADMAP P07, 02_REQUIREMENTS §3/§4/§6, 05_PITFALLS PF-05–PF-10; spot-checked: roadmap P07.1 "> 50 %", P07.4 limits 5–200/0.5–60, REQ §3 "P07: scalp = all 8 channels in montage order, excluded: []", §6 column names — all as quoted |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no copied code; no reference opened in P07 |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | all three handoffs list "None"; `mas/state/scratch/reference_access.log` (26 lines) has no entry after the P06 consultations (last 2026-10-25T04:48, P07 opened 09:00 -0600) |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | **FAIL** | the 7-channel P02 arrays — the inputs of R-1, R-5 and R-6 (decisions.md P07 row 1: "NOT regenerated") — can no longer be produced from this branch: `run_preprocessing.py:128` takes the 8-name config v2, tier 1 is on by default (`:140`), and there is no PO7-excluded switch. The default command still writes to `data/processed` (`:442`), and `Makefile:12,26-27` (`make preprocess`, help text "P02: legacy windows ... -> data/processed/<S>/") would now overwrite the R-6 inputs with 8-channel, tier-1 arrays plus `channels.json`; every later benchmark reads them through `subject_channel_names` without error, so P11 could be scored on different arrays silently. A subject skipped there also has its legacy arrays deleted (`_drop_stale`, `:423-428,485,492`). `data/processed/` is git-ignored and has no frozen copy (`baselines/` does not exist). Fix 1. The P05 single-tier gate is reachable only through the Python API (`window_mask.py:9-11,26-27`) and the p05-done/p06-done tags — CONCERN, note 3 |
| Tests cover every change; at least one fails on the historical bug | PASS (with notes) | PF-07: `test_p07_quality_signal.py:129-169` (pinned 0.5 keeps Vpp 2 µV windows, 5.0 rejects; parser default 0.5) fails on the inherited-5.0 mutant (04_tests.md); PF-08: AST scan `test_p07_known_answer.py:76-93` and script smokes; PF-10 spy; PF-09 stale removal `test_p07_quality_signal.py:210-221`; tier-1 boundary 50/51 of 100 (`>=` mutant). Weak spots in notes 5–6. No test covers the gap of fix 1 (all P02 smoke tests now assert 8 channels, `test_p02_windowing_known_answer.py:508,566`) or fix 2 |
| Changes match 02_plan.md and the roadmap tasks | PASS (with fixes 1–2) | P07.1–P07.6 present; deviations judged in "Builders' deviations" below |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git diff main...HEAD --name-only` has no `data/`, `reports/`, `outputs/`, `baselines/` or local tooling path; fragment-built vendor/assistant pattern: 0 files at HEAD (`git grep -c -i -E`), 0 hits in `git log main..HEAD` messages; answer-key folder path: no added line in the diff (it appears only in the pre-existing spec files AGENTS.md:71, 06_AGENT_ROLES.md:14, CITING.md:64) |

### Judgements requested by the orchestrator

1. **Tiers and return dict (P07.1).** As specified: tier 1 judges every window on every
   channel, drop iff fail fraction strictly > 0.5 (`quality_check.py:283`; exactly 50 %
   kept, tests at 5/10 and 50/100); tier 2 judges windows on the kept channels only
   (`:288-289`; a dropped channel cannot reject a window, tested). Return dict has the
   seven roadmap keys (`:293-301`); `valid_mask` is over the input windows,
   `channels_kept_idx` the input positions. Thresholds are required (R5). PASS.
2. **PF-05/06/08/10.** PF-05: `resolve_channel_names` 8 → montage, 7 → montage without
   PO7, else None (`src/io/channels.py:18-27`, tested 8/7/6/9/0/1). PF-06: new code is by
   name everywhere; the P04 positional path is the exception (fix 2). PF-08: every
   extractor call site unpacks 4 values (`feature_spaces.py:51,64`,
   `visualize_data.py:131,141`); the signature change (`channel_names` third positional,
   `valid_mask=` removed) makes stale calls fail loudly. PF-10: one `quality_gate` per
   subject, reused by PSD, harmonic, FBCCA and the sub-band block (`feature_spaces.py:46-65`;
   FBCSP uses `q["windows_clean"]` of the same decision). PASS except fix 2.
3. **PF-07 demo design.** Two runs (tier 1 on / `--no-channel-drop`) is the right design:
   the original had no channel tier, so only the `--no-channel-drop` run is the historical
   reproduction; the tier-1-on run shows how the P07 fix interacts with it. The default
   stays pinned (`run_preprocessing.py:78,401`; test). Tier 1 in preprocessing cannot affect
   R-6 **as long as nothing rewrites `data/processed/`** — the planned commands do not
   (all four target `data/processed_p07_demo/` or only read `data/processed`), but the
   default command and `make preprocess` would (fix 1).
4. **`data/processed` and the benchmark.** The planned commands never write it
   (`--processed-dir` given in all three preprocessing runs; `benchmark_n_subjects` writes
   only `reports/`). The legacy folders hold no `channels.json`, so names come from the
   count: `subject_channel_names` → `resolve_channel_names(7)` (`channels.py:40-57`).
   Shapes checked read-only: `(320|318|317|317|320, 7, 256)`; stimulus windows
   200/199/200/198/200 = R-1. Changed tests that pinned config v1
   (`test_p01_config_known_answer.py`, `test_p01_ebr_known_answer.py`,
   `test_p01_parser_smoke.py`, `test_p02_*`, `test_p03_*`): adapted legitimately — the new
   expectation is the REQ §3 P07 override (v1 text with exactly the two channel lines
   replaced, checked line by line), and the tests that exercise the legacy 7-channel arrays
   now derive the 7-name list explicitly. They no longer test any 7-channel production path,
   which is the gap of fix 1.
5. **Builders' deviations.** (a) `Channels Kept` as a count, `Channels Dropped` as names:
   accepted — §6 fixes only column names and R-6's own table has "Channels kept 7 /
   Dropped none". (b) `visualize_data` keeps its P02 mask and bypasses the extractor gate
   with an all-ones decision (`visualize_data.py:112-114`): accepted as an exploration
   script under the legacy per-script gate (R5 legacy); its header must keep saying so
   (it does, `:306`). (c) P05/P06 scripts now default to the two-tier gate (decisions.md P07
   row 2): accepted as decided; P05/P06 numbers stand at their tags. Expected effect is nil
   on the legacy arrays because R-6's two-tier counts equal R-5's counts (check D2 below).
   (d) `discover_subjects` moved into `benchmark_runner`, `subject_channel_names` added:
   fine. (e) Config v2 without tier-1 keys (CLI constants): accepted, REQ §3 adds `quality:`
   only in P16.
6. **Run commands, runtime, outputs.** See "Run commands" below; ≈ 3 × 10 s + ≈ 1 min,
   well inside `LOCAL_RUN_BUDGET_MIN`. Pre-committed checks below.
7. **Suite runtime.** 224 s (04_tests.md `493 passed, 10 warnings in 223.90s`) < 5 min
   threshold of decisions.md P07 row; carry-forward closed. PASS.
8. **Privacy.** PASS (table row above).

### Required fixes

1. **data-signal — golden rule 3, R-6 integrity (`scripts/preprocessing/run_preprocessing.py:128,140,442`, `_drop_stale` `:423-428`; `Makefile:12,26-27`).**
   Make the P02 legacy arrays reachable again and stop the default path from silently
   replacing the R-6 inputs. Minimum: (a) a labelled legacy switch (e.g.
   `--legacy-montage`: PO7 excluded by name, tier 1 off, no `channels.json`) that gives the
   P02 layout `(n, 7, 256)` / 217 PSD columns; (b) `make preprocess` either runs that legacy
   switch (help text kept true) or targets a non-legacy folder, and the new 8-channel path is
   a separately named target or explicit command; (c) the script refuses (exit 1, printed
   reason) to write into — or delete stale files from — a folder holding 7-channel arrays
   without `channels.json` unless the legacy switch or an explicit overwrite flag is given.
   Test (synthetic tree): legacy switch → 7 channels, PO7 absent, rows equal to the
   8-channel run's rows without PO7 and with tier 1 off; default run into a folder with
   legacy arrays → refused, arrays byte-identical afterwards. No change to the planned P07
   commands.
2. **ml-engineer — R6/PF-06 (`src/features/ssvep/harmonic_psd.py:30-41`; `scripts/training/train_models.py:306,319-323`, `scripts/training/batch_run_subjects.py:96`, `scripts/xai/run_xai.py:130`, `scripts/training/train_final_model.py:123`).**
   The P04 positional `KEEP_CHANNELS=(1,4,5,6)` must be checked against each subject's array
   names, not the config list: resolve names with `subject_channel_names` per subject and
   either select POz/O1/Oz/O2 by name or skip with `[-] Skipping <S>: ...` when the positions
   do not name them. Test: a 7-channel folder with `channels.json` (PO8 dropped) → skip or
   correct by-name selection (not PO3); a legacy 7-channel folder → unchanged output.

### Non-blocking notes

1. `apply_artifact_quality_pipeline(..., precomputed=...)` prints the thresholds passed to
   the reusing call although they are not applied (`quality_check.py:303-305`); harmless
   while every caller passes the same `th`, but the "(reused decision)" line should print
   the producing call's limits if they are ever stored.
2. Tier 1 in preprocessing uses the whole filtered recording, including pre-session and
   inter-trial segments and the filtfilt ends (`run_preprocessing.py:186-197`). One or two
   edge windows cannot move a 50 % fraction, but a long un-instrumented period at the start
   or end could; the tier-1 log line gives `n_windows`, so the verifier can see it.
3. The P05 single-tier gate (golden rule 3) is reachable only through the Python API
   (`thresholds=P05_MASK_THRESHOLDS, channel_fail_fraction=NO_CHANNEL_DROP`) and the tags;
   a CLI flag on the P05/P06 scripts at the next touch would make a before/after table a
   one-line command.
4. Feature width now depends on tier 1 (harmonic `8 × |surviving cluster|`, PSD `C' × F`,
   FBCSP unaffected): across subjects with different drops, columns are not comparable; fine
   per subject, must be stated if any pooled (LOSO) use appears before P16.
5. The AST arity scan (`test_p07_known_answer.py:76-93`) sees only `ast.Assign`; a
   `return extract_...(...)`, a subscripted call (`extract_...(...)[0]`) or a `for` target
   escapes it. Covered today by the script smokes; keep the smokes.
6. `test_pf07_pinned_default_and_regression_flag` checks the parser default and the
   segment helper; the end-to-end flag forwarding is shown by
   `test_pf07_demo_rejects_low_amplitude_windows` (`--vpp-min 5.0` → "no window accepted").
   Good; together they fail on both historical variants (helper default 5.0; flag not
   forwarded).

### Run commands (unchanged from 02_plan.md; verifier, after the fixes)

```bash
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --processed-dir data/processed_p07_demo/vppmin5 --no-figures
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --vpp-min 5.0 --no-channel-drop --processed-dir data/processed_p07_demo/vppmin5_nodrop --no-figures
.venv/bin/python -m scripts.preprocessing.run_preprocessing --subject S03 --processed-dir data/processed_p07_demo/pinned --no-figures
.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed --n-jobs 5
```

Expected outputs: three logs with the tier-1 report (or "channel drop disabled"), the
ungated `[quality] S03 ungated windows` block and per-condition counts; arrays +
`channels.json` under `data/processed_p07_demo/{vppmin5,vppmin5_nodrop,pinned}/S03/` (and
the S03 root copy) for every run that accepts windows; `reports/n_subjects_benchmark.csv`
and `.meta.txt`. Runtime ≈ 10 s per preprocessing run, ≈ 1 min benchmark.

### Results-review checks, committed before the run

- **D0 — legacy arrays untouched.** `sha256sum data/processed/S0*/*.npy data/processed/*.npy`
  before and after all four runs, in 05_run.md. Prefixes now (read-only, this audit):
  S01 45a9b0332d257a73 / 241adcdcc438fe3f / 1846c4e5b4faabb3; S02 9c2ff184b6c0791e /
  1ad628ad2119e36b / 37c0f53c5c4a9949; S03 51262dccc970a5d1 / 88e9a294b668e5b5 /
  112c8507c38f2193; S04 eb6ef0fbc96c47df / d9dbca887edfdd82 / cebc9c5858b6f90f; S05
  9400ebfd5057a223 / d41793f3ed5a6e35 / 1846c4e5b4faabb3; root = S03 (order X_psd, X_time,
  y). Any change → REJECT.
- **P1 — pinned run, "S03 still produces windows".** Total > 0 and every condition
  (201, 202, 101–105) > 0. A skipped S03 is an acceptance failure, investigated, never fixed
  by changing limits. Report kept/dropped channels. If the kept set is exactly the legacy
  seven (PO7 dropped by tier 1), the rows must reproduce the legacy arrays:
  `np.array_equal(y, data/processed/S03/y_labels.npy)` and `X_time` equal within 1e-9
  (channels are filtered independently); a mismatch then is a bug. If PO7 is kept, report
  the count against R-1's 317 and the per-reason rejections, no equality expected.
- **P2 — PF-07 demo.** Report both counts verbatim. Judgement on the
  `--no-channel-drop` run (the historical reproduction):
  "reproduced" if S03 is skipped with "no window accepted" (PF-07's "all 320": 320 is
  S03's pre-gate count, R-1 note — compare with the ungated summary's `n_windows`);
  "mechanism reproduced, magnitude not" if it rejects more windows than the pinned
  configuration on the same channels but not all — reported with the per-channel mean Vpp
  of the tier-1 report as the explanation and listed as an open point for Sebastian, not a
  failure; **FAIL** if `--vpp-min 5.0` rejects no more windows than 0.5 (flag not forwarded).
  The tier-1-on run is explanatory only: state which channels tier 1 dropped and whether
  that removed the regression. Expectation, stated now: R-6's two-tier gate (vpp_min 5) on
  the 7 legacy channels rejects only 3 of S03's 200 stimulus windows, so a total rejection
  can only come from PO7 (or another channel) being chronically below 5 µV; the per-channel
  report must show which.
- **P3 — channel report per subject.** Present in the three preprocessing logs and for each
  of S01–S05 in the benchmark log (lines with `fail ...%`, `channels kept`).
- **D1 — benchmark CSV complete.** Rows S01–S05 + Mean; `Channels Kept` and
  `Channels Dropped` filled for every subject; R-6 expects 7 / none for all five. A drop
  in any subject is a deviation to explain from its report (not tuned).
- **D2 — counts (diagnostic vs R-6).** Clean/Rejected = 200/0, 196/3, 197/3, 197/1, 200/0
  (R-6); their sums 200/199/200/198/200 equal the stimulus counts of the legacy arrays
  (`.venv/bin/python -c "c=[200,196,197,197,200]; r=[0,3,3,1,0]; print([a+b for a,b in zip(c,r)])"`
  → `[200, 199, 200, 198, 200]`). Integers, exact.
- **D3 — accuracies (diagnostic vs R-5 only, never R-6's leak-free values).** Same code
  path, model, CV and smoothing as `benchmark_5_subjects` (R-5: 64.50/75.50, 66.33/71.94,
  90.36/95.43, 98.98/98.48, 96.50/96.50; mean 83.33/87.57, recomputed with
  `.venv/bin/python -c "print(round(sum([64.50,66.33,90.36,98.98,96.50])/5,2), round(sum([75.50,71.94,95.43,98.48,96.50])/5,2))"` → `83.33 87.57`).
  If D2 holds and no channel is dropped, a per-subject difference means the rejected window
  set differs from P06's (same size, other windows) or the code path differs: before any interpretation
  the rejected window indices under both gates (P07 gate vs `P05_MASK_THRESHOLDS`) are
  listed by a labelled mask-only diagnostic. No reference target in P07 (roadmap: "Record
  numbers").

## Pre-run audit — Round 2

Audited `git diff 5be728b..cacb9bd` (fixes 1083862, 5bc3fba, a3870b1; tests e7b48cf).
Re-run here: `.venv/bin/python -m pytest tests/test_p07_round1_known_answer.py tests/test_p07_known_answer.py tests/test_p07_quality_signal.py tests/test_p07_ml_engineer.py -o addopts="" -q -p no:cacheprovider`
→ `45 passed, 10 warnings in 22.41s`. Full suite per 04_tests.md Round 1: `503 passed, 20 warnings in 199.89s` (< 5 min).

Verdict: PASS

| Item | Result | Evidence |
|---|---|---|
| Fix 1 — legacy P02 path reachable (golden rule 3) | PASS | `--legacy-p02` sets `scalp = legacy_scalp(...)` (PO7 removed by name) and `channel_drop = False` (`run_preprocessing.py` main, after `resolve_params`); writes no `channels.json` and removes a stale one beside the 7-channel arrays. Test `test_legacy_switch_reproduces_p02_arrays`: `X_time` (n, 7, 256) `array_equal` to the 8-channel `--no-channel-drop` run with PO7 deleted, `y` equal, PSD (n, 217) equal to the 5–35 Hz periodogram. Equality is the right known answer: the band-pass is applied per channel, so dropping PO7 cannot change the other rows |
| Fix 1 — default path cannot overwrite the R-6 inputs | PASS | `holds_legacy_arrays` (7-channel `X_time_windows.npy`, no `channels.json`) checked for every target folder (and the S03 root copy) **before** the subject loop, so neither `save_arrays` nor `_drop_stale` runs: exit 1 with a printed reason unless `--legacy-p02` or `--overwrite-legacy-arrays`. Test `test_refuses_to_touch_legacy_arrays_and_flag_lifts_it`: byte-identical tree after the refusal (skipped subject's arrays and root copy included) |
| Fix 1 — Makefile | PASS | `Makefile:12,27` `make preprocess` → `--all --legacy-p02`, help text true; test `test_makefile_preprocess_uses_legacy_switch` |
| Fix 2 — P04 positions checked against the subject's arrays (R6/PF-06) | PASS | `check_subject_keep_channels` (`src/features/ssvep/harmonic_psd.py:45-59`) takes names from `channels.json` or the array channel count (`subject_channel_names`) and raises unless positions (1,4,5,6) name POz/O1/Oz/O2; called per subject before loading in `train_models.py` (skip), `batch_run_subjects.py` (skip, inside the existing `except (ValueError, RuntimeError)`), `train_final_model.py` and `run_xai.py` (exit 1). Those four are the only users of `KEEP_CHANNELS` (grep, Round 1). Test `test_p04_scripts_refuse_subject_whose_positions_shifted` (PO8 dropped → PO3 would be selected): every script skips or refuses and writes no S02 output; the legacy 7-channel folder passes. An 8-channel folder also fails the check (positions give PO3/PO8/O1/Oz) |
| Planned run commands never write `data/processed` | PASS | unchanged commands: three preprocessing runs with `--processed-dir data/processed_p07_demo/...` (those folders get 8-channel arrays + `channels.json`, so the refusal does not trigger there), benchmark reads `--data-root data/processed` and writes only `reports/`. Even a mistyped default target is now refused. `sha256sum` of the 18 legacy files re-checked here: prefixes identical to D0's |
| Tests | PASS (note) | 5 new tests, 5 mutants fail (04_tests.md Round 1). Note: `test_legacy_switch_has_no_tier1` also passes when no arrays are written (`not x.exists() or ...`); the tier-1-on mutant is still caught (it writes 6-channel arrays and `channels.json`), and the equality test above pins the switch, so not blocking |
| Privacy | PASS | fragment-built vendor/assistant pattern: 0 files at HEAD, 0 hits in `main..HEAD` messages; no `data/`, `reports/`, `outputs/`, `baselines/` or local tooling path in `git diff main...HEAD --name-only`; 0 added lines with the answer-key path; no reference-access log entry after the P06 consultations |
| R1–R11 rows of Round 1 | unchanged | the fixes touch no CV, fitting, filtering, statistics or smoothing code |

Non-blocking: with `--legacy-p02`, a subject that is skipped still has its arrays removed
(PF-09 fix, by design since P02). `make preprocess` should therefore not be run before P11
unless the R-6 inputs are meant to be regenerated. If it is run, the output must hash to D0.

The results-review checks committed in Round 1 (D0, P1, P2, P3, D1, D2, D3) stand
unchanged. D0 now has a second baseline: the hashes re-checked in this round.

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
