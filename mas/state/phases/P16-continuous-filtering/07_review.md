# P16 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_data-signal / ml-engineer / connectivity-stats, 04, decisions.md (P02 carry-forwards, P11 N1/D-2, P16 rows 132–133), and the code of every changed file in `git diff main..HEAD` (branch head 78a56ce)

## Pre-run audit — Round 1

Verdict: **FAIL** (6 required fixes, all small; no run before Round 2)

The core of the phase is sound. Continuous filtering, the window index, the guard, the loader, the flagship port and the connectivity port are correct where they will be exercised in this run. The FAIL comes from four things. (i) R5 is enforced from this phase, but the connectivity path inherits gate thresholds from a loader default, which is the PF-07 pattern. (ii) The PF-13 grouping key misses jittered cue windows. (iii) The v1/v2 table does not separate two effects that task 8 requires, or that the 2.0 s column needs before its direction can be explained. (iv) The run list is not complete or explicit.

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | CONCERN (fix 1) | Flagship: groups are `cv_groups` (built) or reconstructed ids (legacy), and `assert_no_shared_trials` runs on every grouped split (`scripts/benchmarks/feature_based/benchmark_n_subjects.py:142`). Only stimulus windows are selected, so `cv_groups == trial_ids` in every P16 run. **Latent bug:** the 202→201 twin map matches on the exact start sample (`src/io/subject_data.py:178-181`). In real data 21 of 199 cue windows are shifted by 8 samples (decisions.md P02 row 29), and those fall back to their own id. I reproduced this in memory with the real `build_subject`, after moving one 202 mark of `tests/p16_synth.make_block(10)` 8 samples later: "202 windows 10, grouped with a 201 id: 9". The tests use exact starts only (`tests/test_p16_subject_data.py:62`, `tests/test_p16_independent_known_answer.py:245`). Rows ordered by trial and offset are enforced (`subject_data.py:75-84`). Continuous filtering cannot leak across trials: the longest ringing time is 0.902 s, and consecutive stimulus segments are separated by the fixation and cue periods (≥ 2 s). |
| R2 Fit only in-fold | PASS | The saved bands come from fixed filters with no data-dependent fit. CSP and the scaler are still fitted inside `oof_space` folds. The built path passes `sub = cs_bands` and never refilters (`benchmark_n_subjects.py:131`; tester mutants "CSP bands always re-filtered" and "FBCCA ignores subband_windows" were killed). |
| R3 Filter continuous, then window | PASS | `band_windows` continuous = `sosfiltfilt` on the whole recording, then cut (`src/preprocessing/windowing.py:220`). per_window = cut, then `filtfilt(b, a)` with default padding, as the P05 extractors did (`:222`). The broadband 1–90 Hz + notch is applied continuously in both modes (`scripts/build_windows.py:116`). The exact equality is tested. per_window is reachable and labelled legacy in the module docs. Note N3: the flagship console and meta do not say "legacy" for a per_window build. |
| R4 Estimator small-sample bias | PASS | The connectivity estimators are unchanged. Concatenation and baseline re-scoring are as in P13. |
| R5 Shared quality decision, explicit thresholds | **FAIL** (fix 2) | Built folders: one decision per subject from the config `quality:` block. `subject_quality_gate` has no defaults and a missing key raises (`src/preprocessing/window_quality.py:55-59`, tested for 8 keys). **But** `load_subject` defaults `thresholds=None → GATE_THRESHOLDS` and `channel_fail_fraction=CHANNEL_FAIL_FRACTION` (`src/io/subject_data.py:90,97`), and `load_condition_windows` calls it without them (`src/features/connectivity/connectivity_extraction.py:312`). Every connectivity script on the legacy root, which includes the blocking `v1check` regression, therefore runs a gate whose limits come from a shared default. The values are equal today (`GATE`, `connectivity_extraction.py:36`, equals `GATE_THRESHOLDS`, `window_mask.py:22`), so no number changes. It is still the PF-07 mechanism, and R5 is enforced from P16. The flagship passes its thresholds explicitly (`benchmark_n_subjects.py:277`). Guard `auto` = ringing time, see the guard section below. |
| R6 Index layouts verified | PASS | The `(n, B, C, T)` layout is proven by planted tones per (band, channel) (tester `test_band_layout_tone_...`). Row order (condition, onset, offset) is checked at load time. |
| R7 Honest statistics | PASS | Trial-level permutations now use true ids on built roots (tester spy test). The FDR family is the (method, condition) cell (`src/features/connectivity/permutation.py:169-178`), and seeds are keyed by (subject, method, condition). |
| R8 Smoothing respects trials | PASS | Built: `smooth_probabilities_by_trial` over `trial_ids` on rows ordered by (trial, offset). The loader refuses any other order (`subject_data.py:75-84`), and the parser default stays `mod5` on legacy roots only (`benchmark_n_subjects.py:204`). The tester's smoothing test plants confident scores so that the trial, mod5 and cross-trial rules give three different values. That fixes the "smoothed = raw" weakness from my memory notes. |
| R9 Per-subject reporting with data source | PASS | Per-subject rows, a Mean row, and a `.meta.txt` that names the build, fs and fs source, and quality mode. The table script reports per subject. |
| R10 Sources | PASS | Handoffs cite the spec sections and Chen et al. 2015 (already cited in the FBCCA module). No external code was adapted. |
| R10 Copied lines / license | N/A | None claimed. None found. |
| R11 Reference consulted only after an attempt | PASS | All three builders and the tester report no consultation. `mas/state/scratch/reference_access.log` has 0 entries dated 2026-10-27 (`grep -c "2026-10-27"` → 0). The last entries are my own P15 verification on 2026-10-26. |
| Golden rule 3: legacy labelled and reachable | PASS (note N3) | Reachable: `--filter-mode per_window`, `--fs 250/256`, `--quality per-script`, the default legacy root with `mod5`, and `run_preprocessing` pinned to 60 Hz (`scripts/preprocessing/run_preprocessing.py:86-88,146`). No other script reads `preprocessing.highcut_hz` (`grep -rn highcut_hz` finds `build_windows.py:96` only). |
| Tests cover every change; at least one fails on the historical bug | PASS with gaps | PF-14, PF-04 (tone bin and token grep), R5 missing-key, R8 order and PF-13 twin tests exist. The 15 tester mutants were killed. Gaps: no jittered twin case (fix 1); nothing checks that the loader raises without thresholds (fix 2); the `LEGACY_HIGHCUT_HZ` pin is untested (N2). |
| Changes match 02_plan.md and the roadmap tasks | **FAIL** (fixes 3, 4, 5, 6) | Task 8 asks for connectivity "on (a), (b), (c), separating the effect of fs, of filtering mode and of the guard". The connectivity filter-mode effect is n/a by construction (accepted, decisions row 133). However, no connectivity a′ row exists, so `d_*_build = b − a` mixes fs with build (`scripts/diagnostics/compare_v1_v2.py:43,107`). The flagship 2.0 s `d_build = b − a′` also includes a change of smoothing rule (mod5 → trial) and of ids (reconstructed → true). P11 showed that rule alone moves the legacy 2.0 s mean by −1.22 pp (decisions.md P11 row 103: 81.39 vs 82.61). `--check-regression` compares only the two summary CSVs, not `_details.csv` (`compare_v1_v2.py:147`). The plan defers the v1/v2 flags to the handoffs instead of listing them. |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git diff main..HEAD` and `git log main..HEAD --format=%B`: 0 hits for the vendor/trailer fragments (pattern built from fragments). No path under `data/`, no dot-folder, no recording suffix in `--name-only`. |

### Unplanned deviations: judgement

| Deviation | Judgement |
|---|---|
| `cv_groups` key computed by the loader instead of shared ids at build time | **Accepted in principle.** Spec §5.2 says one id per segment, and sharing ids broke the (trial, offset) order check because the 202 window sits at offset 0 inside the 201 run. A derived R1 key is the cleaner design. The exact-start match must become an overlap match (fix 1). |
| `LEGACY_HIGHCUT_HZ = 60` pin in `run_preprocessing.py` | **Accepted, necessary.** Without it, `make preprocess` would silently build 1–90 Hz "legacy" arrays (the P07 orphaned-producer pattern). The CLI `--highcut` still overrides it, and the help text says so. Add a test (N2). |
| ml-engineer edited data-signal's `subject_data.py` (2 lines, `channel_stats`) | **Accepted.** The change is additive and only affects the legacy per-script quality dict. The content is harmless. Process note: cross-owner edits should be acked by the owner in the handoff. |
| Freeze copies `configs/pipeline_config.yaml` from the merge-base git rev | **Accepted.** `git show 97a29be:configs/pipeline_config.yaml | sha256sum` = `3b3f3aa9…a5dc`, which equals the pre-hash list entry. The merge-base is 97a29be today. The default depends on `main` not moving, so the run command must pass `--configs-git-rev 97a29be` (fix 6). Only that one file differs between the live tree and the pre-hash list (`sha256sum -c --quiet mas/state/scratch/p16_v1_pre_hashes.txt` → only `configs/pipeline_config.yaml: FAILED`). The other 406 v1 files are intact now. |
| Guard `auto` measured on broadband + all bank filters in **both** modes (data-signal deviation 3) | **Accepted, and it is what makes c − b interpretable.** Ringing times at 256 Hz (command and output in the guard section below): broadband + notch 0.301 s, Chebyshev 0.234–0.262 s, Butterworth 7–12 0.750, **13–17 0.902**, 18–26 0.457, 27–36 0.398, 38–52 0.203 s. The literal roadmap reading ("filters applied continuously") would give per_window a 0.301 s guard. b and c would then differ in their masks, and c − b would mix filter mode with guard size. With one guard, b and c have identical masks and windows, and c − b is the sub-band filtering alone. The orchestrator records this in decisions.md, and the report states it. |
| Ringing-time definition | **Accepted.** The guard is the largest one-sided distance from the impulse at which \|h\| exceeds 1 % of its peak, measured on the zero-phase response (`window_quality.py:62-86`). That is the right dilation radius for a symmetric (filtfilt) response. Counting all samples above 1 % would double it (1.80 s). Record it with the previous row. |

### Is the fs effect of row a′ (+~9 pp) plausible from the code?

Yes, and its size is expected, not suspicious. Of the flagship's two blocks, FBCSP and FBCCA, only FBCCA depends strongly on fs. The flagship has no PSD block (`benchmark_n_subjects.py` docstring: 55 columns = 5 CSP bands × 5 × 2 + 5 FBCCA scores).

- **FBCCA references** (`fbcca_extraction.py:35-41`) use `t = n / fs`. On 256 Hz data with fs 250, every reference runs at f·256/250, so it drifts by 0.21 (8.57 Hz) to 0.58 (24 Hz) cycles over a 1 s window, and more for harmonics 2–3. CCA of a clean 256 Hz tone with the fs-250 references (command below) gives r = 0.529 / 0.654 / 0.794 / 0.889 / 0.929 for 24 / 20 / 15 / 10.91 / 8.57 Hz, against 1.000 with fs 256. The score uses r², so the fs-250 score keeps 0.28 / 0.43 / 0.63 / 0.79 / 0.86 of its value, and the loss is strongly class-dependent (101/102 lose most).
- **FBCSP band edges** shift by +2.4 % only (18–26 → 18.4–26.6 Hz, and so on). Every target fundamental and the harmonics the bands were built for stay inside their bands, so this effect is small.
- **Chebyshev FBCCA bank:** the upper edge is `min(90, fs/2 − 1)` = 90 at both rates. The legacy windows are 1–60 Hz, so this does not change.
- **Splits:** a and a′ use the same windows, labels, groups and seeds, so the splits are identical and the comparison is paired (a′ − a is a pure feature change).

The preview's per-subject gains over R-6 follow the ceiling (command below): S01 +12.00 / +9.80, S02 +22.96 / +24.29, S03 +7.72 / +7.10, S04 +2.24 / 0.00, S05 +2.90 / +2.40 (1.0 s / 2.0 s). The mean is +9.56 / +8.72, or +8.40 / +7.40 for seed 42 alone. Gains are largest where R-6 is low and FBCCA can still add information. That is consistent with the mechanism. A per-class check is not required, but it would confirm the mechanism (N4).

```
.venv/bin/python -c "... canonical_correlation(x, generate_reference_signals(f, fs, 256, 3).T) for fs in (250., 256.) ..."
 24.000 Hz  ref drift 0.576 Hz  r(fs250)=0.529 r(fs256)=1.000
 20.000 Hz  ref drift 0.480 Hz  r(fs250)=0.654 r(fs256)=1.000
 15.000 Hz  ref drift 0.360 Hz  r(fs250)=0.794 r(fs256)=1.000
 10.909 Hz  ref drift 0.262 Hz  r(fs250)=0.889 r(fs256)=1.000
  8.571 Hz  ref drift 0.206 Hz  r(fs250)=0.929 r(fs256)=1.000
python3 -c "... ap[s][k] - r6[s][k] ..."   -> S01 12.0 9.8 | S02 22.96 24.29 | S03 7.72 7.1 | S04 2.24 0.0 | S05 2.9 2.4 | mean 9.56 8.72 | seed42 8.4 7.4
```

### Guard: ringing times (command shown)

```
.venv/bin/python -c "from src.preprocessing.window_quality import ringing_time_sec; ... fs=256 ..."
broadband+notch 0.30078125 | bandpass only 0.1328125 | cheb_6-90 0.2344 | cheb_14-90 0.2617 | cheb_22-90 0.2422
butter_7-12 0.75 | butter_13-17 0.9023 | butter_18-26 0.457 | butter_27-36 0.3984 | butter_38-52 0.2031
```

`auto` = 0.9023 s = 231 samples at 256 Hz (`0.9023·256 = 230.99`), set by the FBCSP 13–17 Hz band. The data-signal handoff's "230 samples" is a misquote; the code stores `guard_samples = round(guard·fs)` = 231 (`window_quality.py:173`). The run log is authoritative.

### Required fixes

1. **data-signal — R1 / PF-13 (`src/io/subject_data.py:178-181`).** Assign each 202 window the id of the 201 segment it **overlaps most**. `build_window_index(cue_shares_cross_id=True)` already does this (`windowing.py:131-134`). Do not match on the exact start sample. Add a test with a cue mark shifted by 8 samples (the P02 real jitter): every 202 window must share `cv_groups` with a 201 window of the same trial, and `trial_ids` must stay one per segment. (No P16 number changes: 202 is never selected.)
2. **data-signal + connectivity-stats — R5.**
   - data-signal: `load_subject` must raise `ValueError` when a per-script gate runs (legacy folders, or `quality_mode="per-script"`) and `thresholds` or `channel_fail_fraction` is not given. Remove the silent `GATE_THRESHOLDS` / `CHANNEL_FAIL_FRACTION` defaults from the call path. Add a test.
   - connectivity-stats: `load_condition_windows` passes the connectivity `GATE` limits and its `channel_fail_fraction_thresh` explicitly. Apply this to every caller, and list them in the handoff.
   - The legacy numbers must stay equal. The existing legacy-equality tests prove this.
3. **ml-engineer + connectivity-stats — task 8 (fs effect for connectivity).**
   - Add a connectivity row a′: legacy root, `--fs 256`, `--out-suffix v1fs256`, same flags as row b.
   - In `compare_v1_v2.py`, add `d_*_fs = a′ − a` and redefine `d_*_build = b − a′` for connectivity.
   - Update the table test.
4. **ml-engineer — 2.0 s smoothing-rule confound.**
   - Add a flagship row a′t: legacy root, `--fs 256 --smoothing trial --cv-repeats 5 --out-suffix v1fs256trial`.
   - Report `d_smoothing_rule = a′t − a′`, and compute the 2.0 s build effect as b − a′t. The 1.0 s value of a′t must equal a′; assert this in the script.
   - Reconstructed ids remain approximate on S02/S04 (P11 D-2), so the residual id change is stated, not separated.
5. **ml-engineer — regression scope (`compare_v1_v2.py:147`).** `--check-regression` also compares `connectivity_cohort_summary_details` and `connectivity_alpha_diagnostic` (`_v1check` vs frozen), and prints a byte-level verdict (equal bytes / equal values only / different) next to the frame check.
6. **orchestrator — run list in `02_plan.md`.** Replace "exact flags: fixed by the handoffs" with the full ordered command list:
   - `freeze_baseline ... --configs-git-rev 97a29be`, with its log written outside `reports/` until it exits, and then moved to `reports/logs/P16/`. Otherwise the snapshot copies its own partial log and n_files ≠ 407.
   - demo, the two builds, the two `v1check` runs, flagship a, a′, a′t, b, c, c′, connectivity a′, b, c, c′, then `compare_v1_v2 --check-regression` and `compare_v1_v2`.
   - The optional connectivity downstream commands in the connectivity handoff are **not** part of the run (the pairwise test at the default 1000 permutations is about 16 min per subject).

### Non-blocking notes

- N1 (connectivity counts across channel counts): row b keeps up to 8 channels (S03 smoke: 7, PO7 dropped), while the legacy rows keep 7 on every subject (`reports/n_subjects_benchmark.csv`). `n_edges_sig_fdr` is therefore not comparable in absolute terms between a and b. The table and report must give FDR counts as a fraction of `total_edges` whenever the channel sets differ.
- N2: add a test that `run_preprocessing.resolve_params` returns highcut 60 with the v3 config (90 Hz).
- N3: label per_window builds "legacy (PF-14)" in the flagship header/meta and in `windows_meta.json`.
- N4 (optional diagnostic): per-class recall for a vs a′ would confirm that the fs gain sits in 101/102.
- N5: `freeze_baseline.summary_rows` also ingests the CSV's own `Mean` row as a subject "Mean". The MEAN value is unchanged (the mean of five values and their mean equals the mean), but the row is redundant. Skip `Mean`/`MEAN` subjects.
- N6: on a built root, `--fs` changes only the FBCCA references, because the saved bands were designed at the metadata fs. Either forbid `--fs` on built roots or say so in the help text. It is not used in this run.
- N7: the full suite takes 10–12 min (602.73 s in my run). The plan's "~7 min" is out of date.

### Pre-committed criteria for the run (fixed before any number of the run exists)

Disclosure: I have seen the builders' smoke numbers in the handoffs: the edge ratios for S03, the row a′ preview, the S01 connectivity equality, and the S03 built connectivity counts. The criteria below are fixed by reasoning from the code. Where a smoke value bears on a threshold, I say so.

**(1) Edge effects, "edge error ≫ centre error for narrow FBCSP bands" (`reports/edge_effects_summary.csv`, S03).**
- Narrow FBCSP bands are those with absolute width ≤ 8 Hz: **7–12, 13–17, 18–26**. Their ringing times are 0.750 / 0.902 / 0.457 s, at least 0.45 of the window. The bands 27–36 and 38–52 ring for 0.398 / 0.203 s.
- **Met** if, for each of the three narrow bands, `edge_to_centre_ratio ≥ 5` **and** `rel_error_edges_pct ≥ 20`. Every one of the eight bands must also have edges > centre.
- Why 5 rather than 10: in the two narrowest bands the ringing is longer than the half window (0.5 s), so per-window distortion reaches the centre itself. The ratio is therefore capped, and it is not a monotone measure of edge damage. The absolute ≥ 20 % clause carries the "large" part.
- The order-of-magnitude reading (ratio ≥ 10) is reported beside it as information. On the smoke values (7–12: 8.17, 13–17: 7.45) it would not be met, and the report must say so.
- Any narrow band below 5 or below 20 % means **not met**. No threshold change.

**(2) Exactness of the v1check regressions (settled point 4, blocking).**
- Flagship: `cmp reports/n_subjects_benchmark_v1check.csv baselines/v1_<date>/reports/n_subjects_benchmark.csv` returns exit 0 (byte-identical).
- Connectivity: `cmp` returns exit 0 for `connectivity_cohort_summary_v1check.csv` and `..._v1check_details.csv` against the frozen unsuffixed files, and for `connectivity_alpha_diagnostic_v1check.csv`. The 20 `connectivity_edges_v1check/S0x_<m>.npz` files are `np.array_equal` per key with `connectivity_edges/`.
- `compare_v1_v2 --check-regression` returns exit 0.
- The console line "seed 42 alone" of row a equals R-6 per subject exactly.
- Byte-different but value-equal (`assert_frame_equal(check_exact=True)`) = CONCERN, to be explained (formatting). Any value difference = FAIL.

**(3) Snapshot.**
- (a) `baselines/v1_<date>/MANIFEST.json` has `n_files == 407`. Every (path, sha256) pair equals `mas/state/scratch/p16_v1_pre_hashes.txt`: no path missing, no extra path. This includes `configs/pipeline_config.yaml` = `3b3f3aa9b617404e4583aa28d69f6ca5cc7a5720a91ac9396354d7c7aac2a5dc`, with `from_git_commit` / `configs_from_commit` = `97a29bed3f6d90ca4ce0aec3392640fd23a85871`. Check with a shown Python one-liner that loads both and compares the sets.
- (b) `superseded/five_subjects_benchmark.csv` and `.meta.txt` exist, their MANIFEST rows carry `stored_as`, and the files are absent from `baselines/v1_*/reports/`.
- (c) Read-only: `find baselines/v1_* -perm /222 | wc -l` = 0, and `touch baselines/v1_*/probe` fails with "Permission denied".
- (d) Refusal: rerun command 1 verbatim. It must exit 1 and print "Refusing to overwrite". `sha256sum` of `MANIFEST.json` must be the same before and after, and `ls baselines` must show one `v1_*` folder.
- (e) `baseline_summary.csv` has the header `pipeline,subject,metric,value`, contains `MEAN` rows, and gives flagship_n_subjects MEAN `1.0s Acc (%)` = 79.28 and `2.0s Smoothed (%)` = 82.61 (within 0.005: a float mean of the CSV values).

**(4) Legacy starts.** In both builds, the `legacy-starts` lines show `n_legacy == n_built == n_equal` and `max|d| 0` for every subject S01–S05 and every condition (201, 202, 101–105). No subject is skipped. Counts are 80 / 40 / 200 per subject (01_DATA_SPEC: complete sessions). The `trial-ids` lines are information only: they must restate S02 39 and S04 38 inconsistent windows and 0 for the others. A difference from the smoke is an anomaly to explain.

**(5) Direction of every change (R-16) and a-priori expectations.** Every cell of `reports/v1_vs_v2/flagship.csv` (per subject and Mean, 1.0 s and 2.0 s, for d_fs, d_smoothing_rule, d_build, d_filter_mode, d_guard and d_total) and every connectivity method × condition cell must get a stated direction with its mechanism. Unit rule: a flagship difference is a "change" only if |Δ| ≥ 1.0 pp **and** |Δ| > the larger repeat SD of the two rows. Otherwise it reads "no material change", with the sign given but not interpreted. One window is 0.50 pp at about 200 clean windows; the results review converts each Δ to windows.

*Determinism checks (any failure = FAIL; these are consequences of the code, not of the data):*
- a vs a′: Clean and Rejected Windows are identical per subject, because the gate does not depend on fs.
- b vs c: Clean and Rejected Windows are identical per subject, because the masks are identical (one guard, the same broadband). Connectivity b vs c is identical in every numeric column, per decisions row 133.
- c vs c′: any subject whose built meta shows `n_valid == n_valid_no_guard` must have d_guard = 0.00 exactly, in both flagship windows and in every connectivity cell. From the smoke, S01 is the expected case.
- Connectivity a vs a′ (fix 3): PLV and wPLI (CSD at nperseg 128) use the same true bins at fs 250 and 256 for 101 (24 Hz), 102 (20 Hz) and 105 (8 Hz). Coherence (nperseg 256) uses the same true bins for 105 (8, 9 Hz) only (command and output below). In those cells `obs_diff`, `p_one_tailed` and `n_edges_sig_fdr` must be identical between a and a′. PDC is evaluated on a continuous grid and differs everywhere.

*Expected directions (to be confirmed or explained, not tuned to):*
- **fs effect, flagship (a′ − a):** positive at 1.0 s for every subject. The size is inversely related to the subject's a-row accuracy, because of the ceiling: largest in S01/S02, smallest in S04/S05. Mean ≥ +3 pp. 2.0 s also positive or zero where it is at the ceiling. Mechanism: the FBCCA reference drift above. A negative fs effect in any subject = anomaly to explain.
- **fs effect, connectivity (a′ − a):** zero in the identity cells above. Coherence 101–103 moves from 2 true bins (f, f+1) to 3 (f−1, f, f+1): expect dilution, so a small decrease or no change in obs_diff. For 104, coherence moves from true 11–12 Hz to 10–11 Hz, and PLV/wPLI from 12 Hz to 10 Hz, into the alpha peak of the fixation baseline. Expect obs_diff to decrease, possibly to become negative (alpha desynchronisation; the P12 results review noted a negative S03 104 value). PDC: no prediction of sign.
- **Smoothing rule (a′t − a′, 2.0 s only):** S01 and S05 have 0 rejected windows (`reports/n_subjects_benchmark.csv`), and their reconstructed ids are exact (smoke: 0 inconsistent windows). On those two subjects, i%5 and trial reset are the same rule, so **d_smoothing_rule = 0.00 exactly** (binding determinism check). On S02/S03/S04 (3/3/1 rejected), the shift can go either way; P11 at fs 250 gave S02 −2.55 and S03 −3.56 (decisions.md P11 row 103). No sign is predicted there.
- **Build effect (b − a′, b − a′t at 2.0 s):** no sign predicted. It combines (i) the 8th channel when the tier-1 tier keeps PO7 (S03 drops it); (ii) 60–90 Hz content plus the 60 Hz notch: the FBCCA 3rd harmonic of 24 Hz (72 Hz) becomes available, and the notch removes the 3rd harmonic of 20 Hz (60 Hz); (iii) the shared gate and guard (fewer clean windows: S03 smoke 310 of 320 on all conditions); (iv) true ids on S02/S04, which removes the residual leak of P11 D-2, so a decrease is expected on S02/S04 if anything. Expected |Mean| ≤ 3 pp. Larger = explain.
- **Filter-mode effect (c − b, flagship only):** ≥ 0 or no material change. Mean within [−1, +2] pp. Mechanism: per-window filtering adds a transient of 23–57 % of band RMS in the first and last 100 ms (smoke). That transient is the same for all classes, so it mostly adds variance to CSP log-variance and to the CCA of the narrow bands; it does not bias the classes. A negative Mean below −1 pp needs an explanation. Candidate to check: acausal continuous filtering lets the first stimulus window borrow pre-onset (cue) activity.
- **Guard effect (c − c′):** small. |Δ| per subject ≤ 100 · (stimulus windows rejected only by the guard) / (clean windows of c′) + 1 SD. Expected sign ≥ 0 (the guard removes windows next to artifacts). Connectivity: no sign predicted. Only the identity cases are binding.

```
.venv/bin/python -c "from src.features.connectivity.connectivity_extraction import band_bins, band_for_condition, CONDITION_FREQS; ..."
nperseg 256 (coherence), true bins fs250 | fs256:  101 [24,25] | [23,24,25];  102 [20,21] | [19,20,21];  103 [15,16] | [14,15,16];  104 [11,12] | [10,11];  105 [8,9] | [8,9]
nperseg 128 (PLV/wPLI),  true bins fs250 | fs256:  101 [24] | [24];  102 [20] | [20];  103 [16] | [14,16];  104 [12] | [10];  105 [8] | [8]
```

### Run commands and budget

Measured runtimes from the handoffs:
- Builds: about 1 s per subject.
- Edge demo: 2 s.
- Flagship: 15–25 s per legacy run. Built runs are of the same order, because the bands are read rather than filtered.
- Connectivity cohort: 82.6 s per subject → about 7 min per 5-subject run.

After fixes 3–4 the run is: freeze (< 1 min, 39 MB copied), demo, 2 builds, flagship v1check + a, a′, a′t, b, c, c′ (7 runs, about 3 min), connectivity v1check + a′, b, c, c′ (5 runs, about 35 min), 2 table commands. That totals about 40 min, plus the suite at 10–12 min (measured below), so about 52 min, inside `LOCAL_RUN_BUDGET_MIN` 120. The plan's "~60 min" estimate holds. Disk: 31 GB free, and the two builds are tens of MB.

Suite on the branch head (78a56ce), run by me: `.venv/bin/python -m pytest tests -o addopts="" -q -p no:cacheprovider` → `1072 passed, 21 warnings in 602.73s (0:10:02)`. That equals the tester's count (04_tests.md).

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

### Decisions for decisions.md

- (pre-run, for the orchestrator now) Guard `auto` = one-sided 1 % span of the zero-phase impulse response, measured on the broadband filter and all bank filters in **both** build modes (0.902 s, FBCSP 13–17 Hz). This deliberately departs from the literal "filters applied continuously" for per_window builds, so that b and c share one mask and c − b is the sub-band filtering alone.
- (pre-run) `cv_groups` is the R1 key for any analysis selecting 202. It is derived by overlap (after fix 1). `trial_ids.npy` stays one id per segment (spec §5.2).
- (pre-run) The `LEGACY_HIGHCUT_HZ = 60` pin, the configs-from-git freeze (`--configs-git-rev 97a29be`) and the ml-engineer's 2-line edit of `subject_data.py` are accepted.

## Sources spot-check

- `mas/04_REFERENCE_RESULTS.md` R-16 (opened): no numeric target; the reviewer checks direction and plausibility; the two historical facts (fs 250, per-window filtering) must be stated in the report. The handoffs quote it correctly.
- `mas/05_PITFALLS.md` PF-14 (opened): "distorts its first/last ~100 ms, worst for narrow FBCSP bands … guard windows near artifacts by the filters' ringing time". The implementation matches.
- `mas/state/decisions.md` P02 row 29 (opened): "21 shifted by 8 samples". This is the basis of fix 1.

## Questions
