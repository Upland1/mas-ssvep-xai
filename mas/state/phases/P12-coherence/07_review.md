# P12 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00_assignment.md, 02_plan.md, 03_changes_connectivity-stats.md, 04_tests.md, decisions.md (P12 row), mas/RULES.md, mas/03_ROADMAP.md P12 (+ P13 task 4), mas/04_REFERENCE_RESULTS.md (tolerance table, R-1, R-11), mas/05_PITFALLS.md (PF-04, PF-15, PF-16), mas/01_DATA_SPEC.md §5.1, `git diff main..HEAD -- src scripts tests` (65836ae..0b18892)

## Pre-run audit, Round 1

Verdict: FAIL

Commands I ran (tests, synthetic only, no real-data run):
- `.venv/bin/python -m pytest tests/test_p12_coherence.py tests/test_p12_known_answer.py -o addopts="" -q` → `25 passed in 5.09s`.
- Legacy input shapes and counts only (no estimator run): S03 `(317, 7, 256)` {101: 40, 102: 40, 103: 40, 104: 40, 105: 40, 201: 78, 202: 39}; S04 `(317, 7, 256)` {101: 38, 102: 40, 103: 40, 104: 40, 105: 40, 201: 79, 202: 40}; totals equal R-1 (317/317). sha256 before the run: S03 `X_time_windows.npy` 88e9a294…a972, `y_labels.npy` 112c8507…5c4c; S04 `X_time_windows.npy` d9dbca88…85c1, `y_labels.npy` cebc9c58…f44ac.
- Synthetic junction simulations (stdin Python, below, finding F2).

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no classifier, no split |
| R2 Fit only in-fold | N/A | nothing fitted; no labels enter an estimator except as the condition selector |
| R3 Filter continuous, then window | LEGACY (by design) | raw legacy windows (P02 continuous 1–60 Hz then cut), no sub-band filtering; `src/features/connectivity/connectivity_extraction.py:3-5`, `scripts/connectivity/analysis/analyze_connectivity.py:3-4` |
| R4 Estimator small-sample bias | PASS (reported path), CONCERN (window-boundary junctions, F2) | reported values come only from `compute_condition_coherence` (`connectivity_extraction.py:98-101`, used in `:120`, `:130`); the per-window estimator lives only in `compute_coherence_matrix`/`per_window_mean_matrix` (`:87-95`, `:139-141`), labelled DIAGNOSTIC, used only for the `mean_baseline_perwindow` column (`:161`). Mutant M1 (reported path averaged) killed by 6 tests (04_tests.md). Residual: concatenation splices Welch segments across trial junctions, unequally for stimulus and baseline (F2) |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) + PASS on thresholds | P07 per-script gate, one call over 101–105 + 201, 202 excluded (`connectivity_extraction.py:183-186`), all five thresholds explicit (`:34`); spy test `test_gate_single_call_explicit_thresholds` |
| R6 Index layouts verified | PASS | mirror fill `out[i, j] = out[j, i]` (`connectivity_extraction.py:73`); names follow `channels_kept`, windows sliced with `kept_idx` (`src/preprocessing/signal/quality_check.py:291-294`); tests `test_r6_pair_layout_argmax_and_symmetry` (3 pairs), `test_r6_dropped_channel_names_follow` (Oz dropped → POz–O2 found by name); mutants M3/M3b killed |
| R7 Honest statistics | N/A | descriptive only; P13 tests |
| R8 Smoothing respects trials | N/A | no smoothing |
| R9 Per-subject reporting with data source | PASS with note | meta states data root, fs 250 legacy, gate, channels, counts (`analyze_connectivity.py:80-83`); label gaps in F3 |
| R10 Sources exist and say what is claimed | PASS | 02_plan.md sources [1] roadmap P12, [2] R-11/PF-15/PF-16 (opened by me in this audit) |
| R10 Copied lines marked, license | N/A | no copied code |
| R11 Reference after an attempt | PASS | 03/04 list no consultation; `mas/state/scratch/reference_access.log` has no P12 entry after the phase opened (last entries 2026-10-26T12:05, P11 deep-learning; P12 commits start 14:16) |
| Golden rule 3: legacy labelled and reachable | PASS | per-window estimator and broadband baseline kept and labelled (`connectivity_extraction.py:10-11`, `:29`, `:112`); fs 250 labelled (`:3-4`, `:23`), `--fs` flag in both scripts |
| Tests cover every change; one fails on the historical bug | PASS for the code under review; new code from fixes 2–3 needs tests | PF-15 (M1), PF-16 (M2), per-band re-selection (M4) killed (04_tests.md) |
| Changes match 02_plan.md and the roadmap tasks | FAIL | settled point 2 is not a faithful operationalisation of R-11 and the outputs lack the quantity R-11 reports (F1) |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | fragment-built vendor/trailer scan over `git diff main..HEAD` and commit messages: no hits |

### Findings on the specific checks

**PF-15 / R4 (reported path).** PASS. Every matrix in the npz, CSV columns `mean_raw`, `mean_matched_baseline`, `mean_difference` and both panels come from the concatenated estimator. The biased per-window value appears only as `mean_baseline_perwindow` (the "before" side of R-11), which is acceptable but must be labelled DIAGNOSTIC in the meta (F3).

**PF-16 (same 201 windows).** PASS. `compute_baseline_matched_connectivity` selects `idx = flatnonzero(y == 201)` once, runs one spectral estimate on their concatenation, and band-averages it per stimulus band (`connectivity_extraction.py:127-131`); `summary_rows` uses the same `idx` for the "before" column (`:161`). `test_same_201_windows_in_every_band` checks the indices and that every band is a band average of one estimate; M2 and M4 killed.

**R6 after a dropped channel.** PASS (see table). Minor: the dropped-channel test passes `channel_names` explicitly, so the default name path (`subject_channel_names` → `resolve_channel_names(7)`) is not exercised with a drop; it is exercised without a drop by the builder's gate test. Non-blocking.

**Band selection on the fs-250 axis (PF-04).** PASS, labelled legacy. I enumerated every band (`np.fft.rfftfreq(256, 1/250)`, inclusive edges):

| cond | f_c | band (fs-250 axis) | bins k | fs-250 Hz | true Hz (fs 256) |
|---|---|---|---|---|---|
| 101 | 24 | 23–25 | 24, 25 | 23.438, 24.414 | 24, 25 |
| 102 | 20 | 19–21 | 20, 21 | 19.531, 20.508 | 20, 21 |
| 103 | 15 | 14–16 | 15, 16 | 14.648, 15.625 | 15, 16 |
| 104 | 10.91 | 9.91–11.91 | 11, 12 | 10.742, 11.719 | 11, 12 |
| 105 | 8.57 | 7.57–9.57 | 8, 9 | 7.812, 8.789 | 8, 9 |

Each band contains the bin nearest the true stimulus frequency, but on the true axis it is shifted upward (f_c and f_c + 1 Hz instead of f_c ± 1 Hz). Stimulus and matched baseline use the same bins, so PF-04 does not bias the difference. The fs-256 guard test shows the 3-bin selection at fs 256. The meta must say that the band is on the fs-250 axis and give the true bins (F3).

**Gate scope (settled point 1).** PASS. One P07 decision over the union of 101–105 and 201 (202 excluded, which also avoids the 201/202 near-duplicate segment noted in P02) means that stimulus and baseline share the same channels, which a difference matrix needs. This matches the later roadmap design (P13 task 4: "one shared quality gate for all conditions"). Tier 1 now sees the 201 windows as well, so a channel-drop decision can differ from the classification phases. Pre-committed check below: the window counts are exact.

**Concatenation without tapering (roadmap-prescribed).** CONCERN, which makes the result interpretation unsafe without a diagnostic (F2). Legacy windows are cut from a continuous recording and saved in time order (01_DATA_SPEC §5.1). The 5 sub-windows of a stimulus trial and the 2 of a fixation trial are contiguous, so a junction is a true discontinuity only between trials. With nperseg 256 and the default 50 % overlap, one Welch segment in every pair is centred on a junction. For S03 101 that gives 7 discontinuous junctions in 79 segments (8.9 %); for 201 it gives about 38 in 155 (24.5 %) (`python3 -c "print(7/79, 38/155)"`). A step at the centre of a Hann segment leaks low-frequency content, which is strongly coherent across occipital channels (common reference, 1–60 Hz legacy filter), into every band, so the matched baseline is inflated more than the stimulus side. Synthetic check (stdin Python, 7 channels: a common component low-passed at 4 Hz plus independent white noise, 1–60 Hz filtered, fs 256; stimulus = 8 trials × 5 contiguous windows, baseline = 40 × 2 contiguous windows, both cut at random from the same process, so the true difference is 0; mean over seeds):

| common amp | band | stim − base, prescribed concatenation | same, junction-free contiguous control |
|---|---|---|---|
| 20 (15 seeds) | 105 | −0.1540 | +0.0067 |
| 50 (15 seeds) | 101 / 103 / 105 | −0.0900 / −0.1991 / −0.1871 | +0.0059 / +0.0066 / +0.0080 |
| 50 (10 seeds) | 105, aligned segments (nperseg 256, noverlap 0) | −0.2183 | +0.0112 |

So the bias has a known sign: it pushes stimulus − baseline downward, and it grows toward low frequencies. Those are the 10.91/8.57 Hz bands, where R-11 expects "inconsistent" signs and the plan records an alpha-ceiling hypothesis. With frequency-flat coherence the effect was below noise (|Δ| ≤ 0.013, 20 seeds). The real magnitude depends on how strong the low-frequency coherence of S03/S04 is, which I may not measure here. Aligning Welch segments to window boundaries (noverlap 0) removes it. Unequal counts (40 vs 78) leave a separate, small positive bias of the concatenated estimator: +0.006 (amp 0, prescribed) to +0.012 (aligned), which is negligible next to +0.11. The roadmap fixes the reported estimator, so it stays. A labelled sensitivity diagnostic is required (F2).

**Settled point 2 vs R-11 "baseline coherence".** Not faithful. FAIL (F1). R-11 gives one range per side (before ≈ 0.68–0.73, after ≈ 0.59–0.66) for two subjects. A range with two endpoints and a width of 0.05 to 0.07 most naturally spans one number per subject. The S03 smoke alone spans 0.643–0.800 before and 0.526–0.739 after across the five bands (03_changes table), so per-band values cannot be what R-11 summarises. The per-band reading tests ten numbers against a two-number range, and it predictably fails the bands inside alpha (105: 0.800 / 0.739 in the smoke). In this phase's own vocabulary, "baseline coherence" without a qualifier is the coherence of `BASELINE_CONDITION = 201` in `BASELINE_BAND = (5, 35)`, the 201 matrix of `compute_condition_connectivity` (task 1). The band-matched quantity is always called "matched baseline" (task 1, PF-16), and the acceptance reports it separately as "differences". **Primary reading (pre-committed, chosen on the text):** one number per subject = mean off-diagonal coherence of the gated 201 windows in 5–35 Hz. Before = per-window coherence (nperseg 128) averaged over the windows. After = concatenated (nperseg 256). The "after" side exists (`mean_baseline_broadband`, `connectivity_extraction.py:155`), but the "before" broadband side is not computed anywhere. So the verifier commands cannot produce what the acceptance needs. Disclosure: the mean of the five matched per-band smoke values for S03 is 0.6986 before / 0.6008 after (`python3 -c` on the 03_changes table). That alternative is kept as a labelled secondary reading. I have not seen the broadband values, and I do not choose the reading by closeness to the target.

**Per-band application of R-11's range (the 105 smoke).** Not the right reading, as argued above. The per-band values stay descriptive. The only per-band criterion is the direction (after < before in every band), because the PF-15 bias is systematic and positive in every band.

**Labels in CSV and meta.** CONCERN (F3).
- The summary meta (`analyze_connectivity.py:80-83`) does not describe the columns. `mean_baseline_perwindow` (the biased PF-15 estimator) and `mean_baseline_broadband` / `mean_difference_broadband` (the PF-16 bug) sit next to the reported columns without a DIAGNOSTIC label. The demo meta does this right (`demo_coherence_bias.py:103-104`).
- The meta hard-codes "7 ch" (`analyze_connectivity.py:81`) while channels can be dropped.
- The raw panel draws 201 in 5–35 Hz under the title "No stimulus (201)" (`src/visualization/connectivity_plots.py:20`, `:67-71`) next to ±1 Hz stimulus circles. That is the PF-16 comparison shown without a warning. The title must say "5–35 Hz broadband, not band-matched".
- Neither meta states the true bins of the fs-250 bands.

**Verifier commands.** The three commands produce the synthetic demo, the per-band before/after values, the differences, matrices and figures. They do not produce the primary R-11 "before" number (F1) or the junction diagnostic (F2). Flags are confirmed (`demo_coherence_bias.py:68-74`, `analyze_connectivity.py:39-48`). No stale outputs exist: `reports/connectivity/` and `outputs/figures/connectivity/` are absent.

### Required fixes

1. **orchestrator: F1, settled point 2 and acceptance table (golden rule 5, R-11).** Amend `02_plan.md` settled point 2 and the P12 row of `mas/state/decisions.md`: R-11 "baseline coherence" = per subject, mean off-diagonal of the gated 201 windows in BASELINE_BAND 5–35 Hz; before = per-window (nperseg min(T,128)) averaged, after = concatenated (nperseg 256). The per-band matched before/after values stay as secondary, with the direction required and the values descriptive. The 5-band mean is a labelled secondary diagnostic only. Replace the acceptance table with the pre-committed windows below.
2. **connectivity-stats: F1/F3, outputs and labels (R4, R9).** (a) Compute and save the per-subject broadband baseline before (per-window averaged, 5–35 Hz, 201 `idx`) and after (concatenated) in both the demo and the analysis outputs (CSV column or a per-subject row, printed on the console). (b) Summary meta: one line per column saying REPORTED or DIAGNOSTIC (PF-15/PF-16). Channel count from `len(channels)`, not a literal. The fs-250 band and its true bins. (c) Raw-panel 201 title: "No stimulus (201), 5–35 Hz broadband, not band-matched". Add a known-answer test for (a): independent noise gives before in [0.27, 0.40] and after ≤ 0.05, and the value equals `mean_offdiag(per_window_mean_matrix(w[idx], fs, BASELINE_BAND))`.
3. **connectivity-stats: F2, junction sensitivity diagnostic (R4).** In demo part (b), add a DIAGNOSTIC column `mean_difference_aligned` per stimulus band: the matched difference recomputed with Welch segments aligned to the window boundaries (`nperseg = T`, `noverlap = 0`) on both sides. Also add the aligned broadband baseline after. The reported estimator is unchanged. Add a synthetic test: a common component low-passed at 4 Hz plus independent noise, stimulus 8 × 5 contiguous windows vs baseline 40 × 2 cut from the same process. Expected: prescribed 8.57 Hz difference < −0.10 and aligned |difference| ≤ 0.03 (my simulation at amplitude 50: −0.218 vs +0.011).
4. **synthetic-tester: independent tests for fixes 2(a) and 3**, each including a mutant that fails: the broadband "before" computed concatenated, and aligned segments with the default overlap.

### Pre-committed acceptance windows (fixed now; the results review cannot move them)

Tolerance: the descriptive-statistics row (±0.05) on each R-11 edge. Window counts must be exact.

| # | Quantity | Window | Grade |
|---|---|---|---|
| A0 | Gate (no channel dropped expected) | clean stimulus windows S03 197 (smoke 1/40, 1/40, 0, 0, 1/40), S04 197 (R-1 graph-dataset counts); 201 clean counts printed | exact; any difference must be explained by the reason tally (vpp/std, channel) before any number is read |
| A1 | Synthetic demo (a), seed 0, 40 × 256 | independent: per-window averaged in [0.27, 0.40], concatenated ≤ 0.07; coupled: both ≥ 0.93 | PASS/FAIL (pytest thresholds [0.30, 0.37] / ≤ 0.03 stay as test gates) |
| A2 | Primary baseline coherence, 5–35 Hz, per subject (S03, S04) | before ∈ [0.63, 0.78], after ∈ [0.54, 0.71], after < before | all four values in their windows and both drops: PASS; a value outside but a drop present: "drop reproduced, level not within tolerance" (a deviation needing explanation, not PASS); no drop: FAIL |
| A3 | Per-band matched baseline, 5 bands × 2 subjects | after < before in all 10 | required. Values are descriptive; the 5-band mean is reported as a secondary diagnostic and cannot replace A2 |
| A4 | 24/20 Hz differences (101, 102) × (S03, S04), prescribed estimator | each > 0 and in [0.06, 0.30] | 4/4: PASS; sign positive but a value outside: partial (deviation); any sign ≤ 0: FAIL |
| A5 | 10.91/8.57 Hz differences | R-11: S03 near zero/negative (≤ +0.05), S04 positive (> 0) | descriptive: "consistent with R-11" or "not consistent". The alpha-ceiling hypothesis is recorded either way; tested in P13 |
| A6 | Junction diagnostic, per subject and band, Δ = prescribed − aligned difference | \|Δ\| ≤ 0.05: negligible | \|Δ\| > 0.05 in any band: the report flags that band as estimator-sensitive and records junction leakage next to the alpha-ceiling hypothesis for P13. If an aligned 101/102 sign differs from the prescribed sign, A4 is graded "not robust" (CONCERN). The reported estimator is never switched in P12 |

### Non-blocking notes

- N1: unequal counts (40 vs about 78 windows) leave a small positive bias in the concatenated difference (about +0.006 in the simulation). Mention it in the report beside A4/A5.
- N2: `band_average` falls back to the nearest bin when a band holds no bin (`connectivity_extraction.py:51-53`). It is not triggered at fs 250 / nperseg 256, but it would be with the per-window nperseg 128 if a band ever narrowed. Fine as is.
- N3: suite runtime (12.5 min builder, 6.1 min tester) is far above "about a minute". Carry to the scribe, as the orchestrator noted.

Verdict: FAIL

1. orchestrator: amend settled point 2, the decisions.md P12 row and the acceptance table (fix 1).
2. connectivity-stats: per-subject broadband baseline before/after, column labels in the meta, raw-panel 201 title, plus a test (fix 2).
3. connectivity-stats: junction-aligned sensitivity diagnostic plus a test (fix 3).
4. synthetic-tester: independent tests and mutants for fixes 2(a) and 3 (fix 4).

## Pre-run audit, Round 2

Reviewed: `git diff 84406bc..HEAD` (26d0a74, a801952, 45289bf, 6c6a152, dde02b4, 0d46099, b9d9d3e, db83896).

Commands I ran:
- `.venv/bin/python -m pytest tests/test_p12_coherence.py tests/test_p12_known_answer.py -o addopts="" -q` → `36 passed in 15.22s`.
- In-memory mutant (no file changed): `baseline_broadband_stats` returns the concatenated value as `before`. Three tests fail: `test_r1_broadband_baseline_hand_built_uses_only_201`, `test_r1_broadband_baseline_independent_noise` and `test_broadband_baseline_before_after_known_answer`. This is the mutant I asked for in fix 4; the tester's M5 is the reverse swap.
- Privacy scan (fragment-built vendor/trailer pattern) over the diff and commit messages since 84406bc: no hits, and no data or tooling files. `reports/connectivity/` is still absent, so no stale outputs. The reference access log has no entry after the P11 entries (12:05).

| Fix | Finding | Result | Evidence |
|---|---|---|---|
| 1 (orchestrator) | F1 | PASS | `02_plan.md` settled point 2 now uses one number per subject (201, 5–35 Hz). The superseded per-band reading is kept. The acceptance table cites A0–A6 with the windows unchanged. The decisions.md P12 Round 1 row records F1/F2 |
| 2(a) | F1 outputs | PASS | `baseline_broadband_stats` (`connectivity_extraction.py`) uses the same 201 `idx`: before = `per_window_mean_matrix(…, BASELINE_BAND)` (nperseg min(T,128)), after = `compute_condition_coherence` (nperseg 256). It is printed on the console ("R-11 baseline coherence …") and saved on every CSV row of the demo and the analysis |
| 2(b)–(d) | F3 labels | PASS | `COLUMN_LABELS` marks every column REPORTED/DIAGNOSTIC, and both metas write them through `meta_lines`. The channel count is `len(channels)`. Bands are listed with their fs-250 bins and true Hz via `band_bins` (`f·256/fs`, so bins 24, 25 for 101, matching my Round 1 table). The 5-band mean is labelled "cannot replace the 5–35 Hz baseline, A2" |
| 2(e) | F3 panel | PASS | `CONDITION_LABELS[201]` = "No stimulus (201) / 5-35 Hz broadband, not band-matched" (`connectivity_plots.py:20`), used as the raw-panel title |
| 3 | F2 | PASS | `compute_aligned_condition_coherence` uses nperseg = T and noverlap 0. `pairwise_coherence(noverlap=None)` leaves the scipy default unchanged, and M7 (reported estimator switched to aligned) fails 7 tests. `mean_difference_aligned` is the aligned stimulus minus the aligned baseline on the same 201 `idx`, labelled DIAGNOSTIC |
| 4 (tester) | — | PASS | 6 new cases; mutants M5, M6a–c and M7 are caught, and my in-memory reverse M5 is caught as well |

**Builder notes judged**
- **Junction-test amplitude.** This is not a discrepancy. My "amp 50" scaled white noise *before* a 4 Hz low-pass, which leaves a standard deviation of about 0.18 × 50 ≈ 9. The builder's "8 × unit-std" is the same regime. The builder's scan is non-monotonic (amp 35 gives −0.036). That fits both sides approaching a coherence ceiling when the common power dominates, so the bias is largest at intermediate low-frequency dominance. The tester's own generator gives −0.31 against +0.011, so the mechanism is confirmed by two independent constructions.
- **S03 smoke A6 at band 105.**
  - Δ = prescribed − aligned per band (`python3 -c` on the 03_changes numbers): [0.0236, −0.0137, −0.0266, −0.0133, 0.0565]. The 105 value of 0.0565 exceeds 0.05, so under A6 band 105 will be flagged estimator-sensitive if the verified run confirms it. This is A6 working as designed, not a reason to change it.
  - Reading note for the results review (it does not move A6): the signs of Δ are mixed. For 105 the prescribed value is higher than the aligned one, which is the opposite of the junction-leakage direction. The aligned estimator also uses about half as many segments (40 vs 79 on the stimulus side), so Δ mixes junction bias with estimator variance.
  - A flagged band will be called "estimator-sensitive" and must not be described as "junction-biased" unless the sign agrees with the predicted negative direction. The 101/102 signs agree in the smoke, so A4 robustness is not affected there.
- **A2 in the smoke** (S03 0.6836 before / 0.5871 after) is not a result and is not read here. A0–A6 stay as pre-committed in Round 1.

**Non-blocking**
- N4: the full-suite counts differ between handoffs: 717 (builder, before the tester's 6 cases) and 723 (tester). This is consistent. The verifier quotes its own clean-checkout count.

Verdict: PASS

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

### Decisions for decisions.md

## Sources spot-check

## Questions
