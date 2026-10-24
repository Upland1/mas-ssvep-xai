# P02 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Audited: branch `phase/P02-legacy-windowing` @ 1497da2 (`git diff --stat main...HEAD`: 21 files). Code read in full: `src/preprocessing/signal/quality_check.py`, `src/features/ssvep/psd_extraction.py`, `src/visualization/signal_plots.py`, `scripts/preprocessing/run_preprocessing.py`, the `Makefile` diff and the three `tests/test_p02_*.py`. Read against `mas/03_ROADMAP.md` P02, `mas/01_DATA_SPEC.md` §3, §4, §5.1, §6, `mas/02_REQUIREMENTS.md` §5.4, §7, `mas/04_REFERENCE_RESULTS.md` R-1/R-3, `mas/05_PITFALLS.md` PF-04/05/06/07/09/13/14, `mas/RULES.md` (era matrix), `mas/state/decisions.md` lines 24–26, `configs/pipeline_config.yaml`. Suite re-run: `.venv/bin/python -m pytest tests/ -q -o addopts=""` → `283 passed in 12.78s`.

Verdict: PASS

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no CV in P02 (no `.fit`, no splitter in the diff) |
| R2 Fit only in-fold | N/A | the gate is fixed thresholds (`quality_check.py:49-62`); the filter has fixed coefficients (`run_preprocessing.py:167`); nothing is fitted |
| R3 Filter continuous, then window | PASS | one `apply_iir_bandpass` over the whole `(C, T)` recording (`run_preprocessing.py:167`), windows sliced from it (`psd_extraction.py:142`); the extractor never filters. Tested: saved rows equal slices of the filtered recording at atol 1e-12 with starts from the spec, not the script (`tests/test_p02_windowing_known_answer.py:489-511`), and the same check fails on per-window filtering, max error > 1e-3 (`:514-543`) |
| R4 Estimator small-sample bias | N/A | no coherence/PLV |
| R5 Shared quality decision, explicit thresholds | PASS (explicit thresholds) / LEGACY (by design) (per-script gate) | Era matrix row R5: per-script gates before P16, which is what P02 builds (module labelled "the legacy per-window Vpp/std gate", `quality_check.py:1`). Every threshold is passed explicitly: script `run_preprocessing.py:169-175`, `LEGACY_VPP_MIN_UV = 0.5` labelled legacy (`:60-62`, CLI `:287-289`); `process_condition_windows_with_baseline` forwards `vpp_min` (`psd_extraction.py:144-146`); `extract_clean_subwindows_psd` gates with all four limits as keywords (`:73-74`); new helpers take thresholds as required keywords (`quality_check.py:37-38, 94-96, 118-119`). Shared default `vpp_min=5.0` verbatim (`:66-67`). See note 4 on the team.yaml label |
| R6 Index layouts verified | PASS | `(n, C, T)` via `reshape(C, n_sub, n).transpose(1, 0, 2)` (`psd_extraction.py:72`, `quality_check.py:112`), proved with a channel-tagged ramp (`test_p02_windowing_known_answer.py:179-189, 351-363`); channel-major flatten `psd[:, sel].reshape(-1)` (`psd_extraction.py:181`) proved with planted 5 + 3c Hz and a failing frequency-major variant (`:437-462`) |
| R7 Honest statistics | N/A | no statistics |
| R8 Smoothing respects trials | N/A | no smoothing |
| R9 Per-subject reporting with data source | PASS (script) | first line states the source, `Data source: legacy windows from OO.<suffix> -> data/processed/<S>/` (`run_preprocessing.py:327`); per-subject header fs, per-condition counts, `n`, stimulus count, every rejected sub-window and skipped segment (`:352-363`, `quality_check.py:264-285`). Accuracy rows are N/A in P02; the report must give the five subjects' counts, not a mean |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | spot-checked: `02_REQUIREMENTS.md` §7 has the "event onsets" plateau row and the "vpp_min pinned in the legacy raw gate" row; `01_DATA_SPEC.md` §5.1 has the 202/201/stimulus segments and the 7 × 31 = 217 rule; SciPy is 1.18.1 in `.venv` (`python -c "import scipy; print(scipy.__version__)"` → `1.18.1`), as the handoffs cite |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no external code; CLI style reused from this repository's `scripts/exploration/inventory_raw.py`, declared in `03_changes_data-engineer.md` |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | all three handoffs list none; `mas/state/scratch/reference_access.log` has 2 lines, both verifier privacy greps from earlier phases (16:27 and 15:07), no P02 entry |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS | P02 has no era-matrix legacy row besides the per-script gate (labelled). The 7-channel config v1 is labelled `# PO7 hard-excluded (legacy)` (`configs/pipeline_config.yaml`). The PF-07 regression stays reachable with `--vpp-min 5.0` (`run_preprocessing.py:287`) |
| Tests cover every change; at least one fails on the historical bug | PASS | PF-07: legacy extractor keeps Vpp 1.5–4.9 µV and a non-forwarding variant fails the same check, at function and condition level (`test_p02_windowing_known_answer.py:207-275`); PF-13 202 position with the last sample at onset − 1 (`:325-348`); PF-09 root = S03, not the last subject S04 (`:546-575`); PF-04 bin count (`:465-474`); PF-06 shuffled channel order in the file (`:489-492`). Buggy variants I checked by hand: strict `<` bounds and any-channel gate (`:137-165`); 202 after the pulse / off by one (ramp content, `:345-348`); partial stimulus trial and negative-index wrap (`:366-392`); dict-order concatenation (`:437-453`). Not covered: a re-run where S03 is skipped leaves earlier root arrays (note 3) |
| Changes match 02_plan.md and the roadmap tasks | PASS | segment definitions `psd_extraction.py:126-141` = plan and §5.1; order 201, 202, 101–105 from config `project.target_conditions` (`run_preprocessing.py:100, 176`); fs from header (`:141`); Q1 figure paths (`:237-253`); Q2 gate on filtered windows (`:167-175`). Listed deviations accepted (point 4 below); one unlisted, behaviour-identical deviation (note 5) |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git ls-files` filtered for `data/`, `reports/`, `outputs/`, `baselines/`, the recording suffix, the local tooling folder/file and `scratch` → only non-matches; case-insensitive `git grep -c` over HEAD with the fragment-built vendor pattern → exit 1 (no hit); `git log --format=%B main..HEAD` count `0`; single author (Sebastian). Wording note 7 |

### Judgements requested

**1. fs-250 correction — correct.** The two shape criteria of the acceptance can only hold together at fs 256. `int(1.0 * fs)` must be 256 samples for `X_time (n, 7, 256)`, and a 256-sample periodogram gives 31 bins in 5–35 Hz at fs 256 and 30 at fs 250. Command: `.venv/bin/python -c "from scipy.signal import periodogram; import numpy as np` + `for fs in (256,250): f,_=periodogram(np.zeros(256),fs=fs); print(fs, ((f>=5)&(f<=35)).sum())"` → `256 31`, `250 30`. No P02 task, acceptance row or R-1 entry needs 250 Hz. P02 has no sub-band filtering, so the old `per-window-subbands` flag had nothing to apply to either. One text conflict remains. `mas/02_REQUIREMENTS.md` §5.4 says "Legacy reproduction (P02–P15) uses the original hard-coded `fs=250.0` in feature extractors and must say so in its report". `01_DATA_SPEC.md` §5.1 and R-1 (217 features) settle it for the P02 periodogram (decisions.md line 24). §5.4 only tells P02 to state its fs, so the P02 report must say "fs = header 256 Hz, PF-04 not reproduced here; it enters with the P03–P05 extractors" (team.yaml P03 is the first `fs250` phase). Consequence for later phases: the legacy `X_psd_features` are on the true frequency axis. Any Era-A result read from those 217 columns is not affected by PF-04. Only extractors that recompute from `X_time_windows` with `fs=250` are.

**2. Segments and the 202 = second-201-sub-window observation — consistent with PF-13 and §5.1, by design; flagged, not to be fixed.** §3 timing puts 202 at t + 2 s, so `[onset202 − 256, onset202)` is `[t + 1 s, t + 2 s)`, the second 201 sub-window. The tester proves exact equality under exact synthetic timing (`test_p02_windowing_known_answer.py:346-348`). Real onsets jitter by ≤ 0.04 s = 10.24 samples (`python -c "print(0.04*256)"`), so in the real arrays the 40 202 rows are near-duplicates (≥ ~245 of 256 samples shared) of 40 of the 80 201 rows, not exact copies. Consequences:
- *R-1 counts.* Gate outcomes of the twins are strongly correlated. R-1 implies the windows lost from 201 + 202 are S01 0, S02 1, S03 3, S04 1, S05 0, and from the stimulus S01 0, S02 1, S03 0, S04 2, S05 0. (`python -c` over R-1: lost 201/202 = 120 − (total − stimulus).) If S02 and S04 each lose exactly one non-stimulus window, it is most likely a first 201 sub-window, or an artifact that falls inside the ~10-sample offset between the twins. In the results review I will check each rejected 201/202 window against its twin, using the printed `onset`/`start`, as a consistency test of the 202 definition. A run where 202 rejections do not track their 201 twins means the 202 window is cut elsewhere.
- *Later phases (for the orchestrator to carry into the relevant assignments).* (a) Any analysis that uses both 201 and 202 rows, as two classes or as a pooled "no-stimulus" set, double-counts about 40 seconds of signal. Under window-level CV (P04–P10) it also gives near-identical inputs with different labels, or the same signal in train and test. (b) P11 legacy trial ids come from contiguous same-label blocks (§5.1), and P16 `build_window_index` gives "one trial id per segment" (roadmap P16.2). Both put a 202 window in a different group from its 201 twin, so trial-grouped CV would leak if 201 and 202 are ever used together. (c) Connectivity baselines and the P17 rest class use 201 only (§6, PF-13), which avoids the issue. Keep it that way.
- Stimulus windows are unaffected: `[onset, onset + 1280)` does not overlap 201/202 (203 sits between).

**3. PF-07, PF-09, R3, R6.**
- PF-07 is pinned at both levels (table above).
- PF-09: the root copy is written from the same in-memory arrays right after the S03 folder (`run_preprocessing.py:365-369`), and `save_arrays` refuses unequal lengths (`:217-221`). `data/processed` and `outputs/figures` do not exist yet (`ls` → "No such file or directory"), so this run cannot mix in stale files.
- R3 and R6: PASS (table).

**4. Builders' deviations — all accepted.**
- Extra trailing kwargs `vpp_min=0.5` and `cross_duration_sec=2.0`: defaults equal the roadmap values, so a verbatim call is unchanged (`psd_extraction.py:92`).
- Extra record keys `sub_index`, `condition`, `onset`, `start`: additive. They are what makes the R3 check and the 202/201 twin check possible.
- Extra figure `stimulus_vs_baseline_psd.png`: uses 201 as the baseline (`run_preprocessing.py:245-249`), as §6/PF-13 require.
- Extra CLI flags: defaults reproduce the config run (`:93-124`, `:265-289`).
- `summarize_window_quality` over accepted windows only: acceptable for P02, because `format_quality_stats` printed just above it gives the full rejection picture. It is a weak PF-07 diagnostic, though: it always prints "0 rejected", and a subject with zero accepted windows is skipped before it runs (`:347-357`). See note 2.
- Plateau fallback unreachable under the §3 rule: agreed (`psd_extraction.py:41-44`).

**5. Run command, outputs, acceptance.** The run command `.venv/bin/python -m scripts.preprocessing.run_preprocessing --all` (= `make preprocess`) matches the roadmap. Runtime < 2 min on CPU is plausible: 5 files, one filtfilt each. Expected outputs:
- `data/processed/S0{1..5}/{X_psd_features,X_time_windows,y_labels}.npy`;
- the S03 root copy `data/processed/*.npy`;
- `outputs/figures/spectra/S0{1..5}/{average_psd_by_condition,stimulus_vs_baseline_psd}.png` plus `outputs/figures/spectra/average_psd_by_condition.png` (S03);
- stdout teed to `reports/logs/P02/run_preprocessing_<timestamp>.log`.

Skipped segments should be 0 for every subject: the last stimulus ends at 600 s of ≈605.1 s (`python -c "print(5+39*15+5+5)"` → `600`). Acceptance as I will judge it:
- (i) Shapes, labels and caps from the saved arrays.
- (ii) R-1 **exact**:
  - totals S01 320, S02 318, S03 317, S04 317, S05 320;
  - stimulus (101–105) S01 200, S02 199, S03 200, S04 198, S05 200;
  - plus per-condition counts.

  Any difference must be explained from the printed rejected/skipped lists (which window, which reason, which channel). Likely sources are the gate input (Q2: filtered), inclusive bounds and the filtfilt padding. A difference is never closed by changing a threshold, the bound type or the filter (golden rule 5). An unexplained difference is a REJECT.
- (iii) Figure. I open the per-subject `average_psd_by_condition.png` for every subject; the criterion is judged on S03, S04, S05. For each target I check whether its mean curve has a local maximum at the bin nearest f0 (24, 20, 15, 11, 9 Hz) and lies above the 201 curve there. The criterion is met for a subject when this holds for all five targets. Any target without a peak is named and reported as not met for that target, not explained away. The 8.57 Hz target keeps only `sinc²(0.43)` = 0.524 of its power in bin 9 (`python -c` loop over f0: `d = f0 - round(f0)`, `np.sinc(d)**2` → `8.571 9 -0.429 0.524`; 10.909 Hz → bin 11, 0.973), and 8.57/10.91 Hz overlap alpha in the all-channel average, so a weak low-frequency peak is plausible and is reported as such. The verifier's supplementary ratio can be computed from the saved `X_psd_features` without raw data: column `c*31 + (f − 5)`, f ∈ {24, 20, 15, 11, 9}. The channels must be named, preferably all 7 (what the figure shows) and the §6 visual cluster `PO8, O1, Oz, O2` resolved by name from config `scalp`. The `stimulus_vs_baseline_psd.png` panels are used as supporting evidence only.

**6. Privacy — PASS** (table). The commands used fragment-built patterns.

### Required fixes

None.

### Non-blocking notes

1. *Runner (PF-09):* record in `05_run.md` that `data/processed/` and `outputs/figures/` did not exist before the run. Run once with `--all` and do not re-run single subjects before the verifier checks the root copy.
2. *For P07 (PF-07 diagnostic):* `summarize_window_quality` should receive the ungated windows, so that the observed Vpp/std ranges include the rejected ones. Today it prints `0 rejected` by construction (`run_preprocessing.py:355-357`), and it never runs for an all-rejected subject. That is exactly the PF-07 situation it was added to diagnose.
3. *PF-09 on re-runs:* when S03 (or any subject) is skipped, the files a previous run wrote stay on disk. Only a `[!]` line is printed (`run_preprocessing.py:377-378`). This is harmless now, but P07 re-runs this script with 8 channels: there a stale 7-channel root could survive a skipped S03. Suggest that P07 deletes or refuses stale outputs, with a test.
4. *team.yaml label:* the era matrix lists per-script gates as the R5 legacy behaviour before P16. P02 builds such a gate, so `legacy: []` (decisions.md line 24) is slightly too strict. P07 is the first phase that lists `R5`. No action needed beyond the scribe naming the R5 row LEGACY (by design) in the P02 report.
5. *Unlisted deviation (behaviour-identical):* `extract_clean_subwindows_psd` gates with `window_quality_flags(...)["valid"]` (`psd_extraction.py:73-74`) rather than calling `validate_eeg_windows`. The roadmap words it as a `validate_eeg_windows` call. The latter is exactly that expression (`quality_check.py:76-77`), so results are identical. One consequence: the legacy extractor is insulated from later edits of `validate_eeg_windows`, so P07 must reproduce PF-07 by passing `vpp_min=5.0` (`--vpp-min 5.0`), not through a changed shared default. The P07 plan should state this.
6. *No fs/217 assertion:* `check_arrays` only checks that `X_psd` columns are a multiple of C (`run_preprocessing.py:201`). A non-256 Hz file would pass silently with 210 or another width. The verifier's shape check (acceptance i) covers this run. P00's inventory already fails loudly on fs deviations.
7. *Wording (privacy hygiene):* `03_changes_signal-processing.md:73` refers to a local tooling "skill" for the palette validator. It is not a vendor name and not a tracked tooling file, but the orchestrator may reword it to "a palette validator" in the scribe's report.
8. *For P03/P04 assignments:* see judgement 2 (201/202 twins) and judgement 1 (legacy PSD columns are on the true 256 Hz axis).

## Results review

Reads: `05_run.md` (194d23b), `06_verify.md` (3ac714c, PASS), `reports/logs/P02/run_preprocessing_20261024_171759.log` (112 lines), the saved arrays `data/processed/<S>/*.npy` (processed arrays only; nothing raw opened), and all 11 figures under `outputs/figures/spectra/`. Data source (R9): legacy windows, `OO` session file, header fs 256 Hz, 7 channels (config v1), continuous 1–60 Hz filter, legacy gate on filtered windows.

Verdict: APPROVE

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-1 total windows | S01 320, S02 318, S03 317, S04 317, S05 320 | 320 / 318 / 317 / 317 / 320 (log `n =` lines; `05_run.md` table) | 0 for every subject | yes (exact) | — | — |
| R-1 stimulus windows | S01 200, S02 199, S03 200, S04 198, S05 200 | 200 / 199 / 200 / 198 / 200 | 0 | yes (exact) | — | — |
| R-1 shapes | 7 × 256; 217 | `(n, 7, 256)`, `(n, 217)` for all 5 (log; verifier acceptance) | 0 | yes | — | — |
| P02 acceptance: figure peaks, S03–S05 | peak at each f0 in the per-subject PSD figure (pre-run definition (iii)) | S04 5/5, S05 5/5, S03 4/5 (8.57 Hz not a local max in the 7-channel mean) | S03 105 | partially | see "Figure criterion" below; not a counting or frequency-axis error | yes, recorded as partial (decision 1) |

### Twin check (202 vs second 201 sub-window) and the rejected counts

- **Rejections vs twins** (log lines 36–37, 56–58, 78–80):
  - S03 rejects `201 onset 1280 sub 1 start 1536` and `202 onset 1792 start 1536`. Both are on PO8. Same start sample, so this pair is the exact twin, rejected together as predicted. The third S03 rejection is `201 sub 0 start 1280`, also PO8: a single artifact over 5–7 s at the start of the first trial (`1280/256` = 5.0 s).
  - S02's one non-stimulus loss is `201 onset 5128 sub 0` (O2) and S04's is `201 onset 8960 sub 0` (O2). Both are first sub-windows, so they have no 202 twin, matching the prediction in judgement 2.
  - No 201 sub-1 window was rejected while its 202 twin was kept, or the other way round.
  - Stimulus losses: S02 `103 onset 10248 sub 3` (O2), S04 `101 onset 2560 sub 0` and `sub 2` (O2). All are `vpp_high` (plus `std_high` in S02/S03). There is no `vpp_low`, so the explicit `vpp_min = 0.5` played no role (observed min Vpp 19.8–31.2 µV, log `[quality]` lines).
- **Explaining R-1 from these rejections.** Every count difference from 320 is a listed gate rejection, and there are 0 skipped segments.
  - Totals: S02 1 + 1, S03 3 + 0, S04 1 + 2 (non-stimulus + stimulus).
  - These equal R-1's implied losses (S01 0/0, S02 1/1, S03 3/0, S04 1/2, S05 0/0) per subject and per class group.
- **Twins in the saved arrays.** For every 202 row I searched the 201 rows of the same subject, first for an identical window, then for one shifted by 1–15 samples (command in this session, `np.array_equal` over `X_time_windows`).
  - Results: S01 40 exact; S02 35 exact + 5 shifted; S03 36 + 3; S04 33 + 7; S05 34 + 6. No 202 row lacks a twin.
  - Totals: 178 exact + 21 shifted = 199 rows. Every shift is 8 samples = 0.03125 s, inside the §3 jitter of ≤ 0.04 s.
  - So 178 of the 199 saved 202 windows are bit-identical copies of a 201 window, and the other 21 share 248 of 256 samples. This confirms PF-13 on real data. It is why 201 and 202 must never be used together (decision 2).
- **Hypothesis, not checkable here:** the S03 PO8 rejections at 5–7 s are the first seconds after the recording start. Part of the excursion could be the start-up transient of the 1 Hz high-pass on a drifting raw signal (§4 notes large drifts) rather than EEG. Checking it needs raw-signal access, which is out of my role. P16 (edge guards) is the place to look. It does not affect R-1, which matches.

### Figure criterion (pre-run definition (iii))

I opened `outputs/figures/spectra/S0{1..5}/average_psd_by_condition.png` and `.../stimulus_vs_baseline_psd.png`. The root `outputs/figures/spectra/average_psd_by_condition.png` is byte-identical to the S03 one (`cmp` → identical), as Q1 decided. All curves are the 7-channel mean, and n per condition in the legends matches the log.

- **S04: met, 5/5.** Sharp peaks at 24, 20, 15, 11 Hz (104 reaches ~15 µV²/Hz against a fixation ~2) and at 9 Hz for 105. 105 also has its 2f0 at 17 Hz.
- **S05: met, 5/5.** Peaks at 24, 20 (moderate), 15, 11 and 9 Hz. The 9 Hz peak is small: the 7-channel ratio is 1.118 (verifier table), with bin 9 = 1.863 above bins 8 = 1.681 and 10 = 1.212 (command in this session). 2f0 harmonics are clear (40, 30, 22, 17 Hz).
- **S03: 4/5, partial.** Clear peaks at 24, 20, 15, 11 Hz, with 2f0 at 48, 40, 30, 22 Hz. **8.57 Hz (105) is not met in the figure as drawn.** The 105 curve has an 8–9 Hz plateau (bin 8 = 2.481, bin 9 = 2.458). That plateau is above fixation (201 bins 8/9 = 2.017/1.731, ratios 1.23/1.42), but bin 9 is not a local maximum. Over the visual cluster `PO8, O1, Oz, O2` it is a local maximum with ratio 1.918 (verifier). Bin-split arithmetic: 8.57 Hz leaves sinc² = 0.295 in bin 8 and 0.524 in bin 9, so with 1 Hz bins a split peak in the alpha range is expected. It is reported as not met for this target, not explained away.
- The frequency axis is correct. All three subjects show peaks at the true 24/20/15 Hz bins and harmonics at exact multiples, which would be off by 250/256 if fs were wrong (PF-04 not present in P02).

Reading for the phase: the criterion's purpose (stimulation responses visible at the right frequencies in S03–S05) is met. The single partial target is a resolution/alpha-overlap effect, not a defect in the arrays. I approve with the partial recorded, and Sebastian can overrule. No parameter (channels, window, range) was changed to obtain a peak (golden rule 5).

### Interpretation check

- **Per subject, S01 and S02 (observations, not tuning; not required by the criterion):**
  - S01 shows no peak at 24, 20 or 15 Hz.
  - S01's 101 (24 Hz) curve has a strong 10 Hz peak instead (bin 10: 5.613 vs 201 1.968; at 24 Hz 0.659 vs 0.497; command in this session). 104 has a weak 11 Hz bump.
  - S02 is flat: no clear peak at any f0 (verifier: ratios 0.95–1.43, several not local maxima).
  - In both subjects the 201/202 curves lie above the stimulus curves at 30–55 Hz, which suggests more broadband/muscle activity during fixation.
  - This is consistent with S01/S02 being the weak subjects of R-6 (61.00 / 56.12 % at 1.0 s), which P11 targets and does not change here.
  - The S01 101 → 10 Hz peak is unexplained at this stage. Possible causes are alpha modulation, a subharmonic, or a label/stimulus mismatch in that session. It is flagged for P03 (signal verification), which owns this question. It must not be "fixed" in P02.
- **Leakage / fitting / statistics:** none in P02. Nothing is fitted (no CV, no normalization, no statistics). The PF-09 root copy equals S03 bit-for-bit (verifier). The verifier's independent re-run reproduced all 18 arrays bit-identically.
- **Inconclusive:** nothing statistical is claimed. The f0 ratios are descriptive means without uncertainty, and no p-values are attached.

### Decisions for decisions.md

1. P02 figure criterion: S04 and S05 met (5/5 f0 peaks in the 7-channel PSD-by-condition figure). S03 met for 24/20/15/10.91 Hz. S03 8.57 Hz shows an 8–9 Hz plateau above fixation (ratios 1.23/1.42), but no local maximum at bin 9 in the 7-channel mean (local maximum over PO8/O1/Oz/O2, ratio 1.918). Accepted as partial: a 1 Hz-bin split and alpha overlap, not an array defect. No parameter was changed.
2. Real-data PF-13 twins: 178 of 199 legacy 202 windows are bit-identical to a 201 second sub-window, and the other 21 are shifted by 8 samples. Later phases must not use 201 and 202 together (classes, pooled baseline, trial groups).
3. R-1 reproduced exactly (totals 320/318/317/317/320, stimulus 200/199/200/198/200). All 8 losses are `vpp_high` gate rejections (O2 in S02/S04, PO8 in S03), with 0 skipped segments.
4. Carry to P03: S01 101 (24 Hz) trials show a 10 Hz peak and no 24 Hz peak, and S01/S02 show no clear SSVEP peaks. These are observations to verify there, not tuned.
5. Carry to P16: the S03 first-trial PO8 rejections at 5–7 s could include a high-pass start-up transient; check with the edge-guard work.

## Sources spot-check

- `mas/04_REFERENCE_RESULTS.md` R-1: the totals and stimulus counts cited above are those of the table (opened in the pre-run pass and re-read here). R-6 per-subject 1.0 s values (61.00 / 56.12 %) are quoted from `mas/RULES.md` (reference targets table).
- `mas/01_DATA_SPEC.md` §3: the jitter ≤ 0.04 s and 202 at t + 2 s used for the twin check say what is claimed. §4 notes the large raw drifts.
- `06_verify.md` f0 table: the S03/S05 values I re-derived from `X_psd_features` (bins 7–11 Hz) agree with the verifier's locmax flags (S03 105 all-7 False, S05 105 all-7 True).

## Questions
