# P03 · 07 · Scientific review

Status: READY
Author: scientific-reviewer
Reads: 00_assignment.md, 02_plan.md, 03_changes_signal-processing.md, 04_tests.md, mas/RULES.md, mas/state/decisions.md (P02, P03 rows), mas/01_DATA_SPEC.md §6, mas/02_REQUIREMENTS.md §4, mas/05_PITFALLS.md PF-04/05/06; every changed file at 56ff93e (`git diff main..HEAD`)

## Pre-run audit — Round 1

Verdict: FAIL (one reporting FAIL, PF-04 consequence; code otherwise sound)

Suite at 56ff93e: `.venv/bin/python -m pytest tests/ -p no:cacheprovider -o addopts="" -q` → `303 passed in 19.96s`; P03 files alone `20 passed in 9.96s`.

| Rule | Result | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A | no split, no model |
| R2 Fit only in-fold | N/A | nothing fitted; P05 extension note keeps FBCSP in-fold `scripts/exploration/visualize_data.py:108-111` |
| R3 Filter continuous, then window | N/A | no filtering or Hilbert on windows; plain `rfft`/periodogram of P02 windows `src/features/ssvep/spectral_power.py:66`, `:128` |
| R4 Estimator small-sample bias | N/A | mean power per class, no coherence/PLV `spectral_power.py:77-84` |
| R5 Shared quality decision, explicit thresholds | LEGACY (by design) | per-script mask before P16; all four thresholds keyword-only and forwarded `visualize_data.py:59-73`, `vpp_min` legacy constant labelled `:52-53`, config values `:185-194`; test proves no inherited `vpp_min` (`tests/test_p03_exploration_known_answer.py` `test_quality_mask_vpp_min_is_explicit`, mutant fails) |
| R6 Index layouts verified | PASS | channel-major PSD flatten `spectral_power.py:131` proven by `test_psd_features_layout_217_210_and_p02_equality` (per-channel planted bins, equality with the P02 extractor) |
| R7 Honest statistics | N/A | no test statistic |
| R8 Smoothing respects trials | N/A | no smoothing |
| R9 Per-subject reporting with data source | FAIL | per-subject console block and figure, data source in titles `diagnose_occipital_spectra.py:269-279` (PASS), **but** the printed "target-bin power" at the default fs 250 is read at the bin nearest h·f0 on the mislabelled axis `spectral_power.py:111`, which is not the bin a true response occupies for 3 of the 8 in-band targets (computation below). Required fix 1 |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | sources in 03/04 opened; PF-04/06/07/09, §5.1, §6, §5.4 say what is cited |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | nothing copied (03, 04: "None copied") |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | 03 and 04: "None" |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | LEGACY (by design) / PASS | `LEGACY_FS_HZ = 250` with `# legacy:` `spectral_power.py:17-18`; default `--fs` `diagnose_occipital_spectra.py:206`, `visualize_data.py:169`; label `fs=250 (legacy)` / `fs=256 (header)` in console and titles `diagnose_occipital_spectra.py:267`, `:275`; header fs derived (samples / `sub_window_sec`), not a literal `:131-133` |
| Tests cover every change; at least one fails on the historical bug | PASS (CONCERN) | PF-04 (`test_legacy_fs_shift_24hz`, ignore-`--fs` mutant fails), PF-06 (positional mutant → 33 Hz decoy), PF-09 (root-array mutant), PF-07 `vpp_min`; gap: 2f0 bins untested, which hid the two extra mismatches below |
| Changes match 02_plan.md and the roadmap tasks | PASS | P03.1, P03.2 as planned; deviations accepted below |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | `git ls-files` filtered for data/npy/outputs/reports/local tooling: 0; fragment-built vendor/co-author grep over `HEAD` (all paths incl. `mas/state/phases`) and `git log --format=%B main..HEAD`: 0 hits |

### Judgement (1): fs 250 reproduction and the "nearest target bin"

The legacy reproduction itself is correct and well labelled: with fs 250 the power values
are unchanged and only the axis is scaled by 250/256 (`spectral_power.py:55-67`;
test `test_legacy_fs_shift_24hz`). The problem is the printed target-bin line. On
256-sample windows a true response at h·f0 lands in bin `round(h·f0·T/fs_header)`,
but `spectrum_peaks` takes the bin nearest h·f0 on the analysis (fs 250) axis.
Computation (`.venv/bin/python -c "N=256; f=np.fft.rfftfreq(N,1/250); k_lab=argmin|f-h·f0|; k_true=round(h·f0·N/256)"`):

```
24 1 nearest-labelled bin 25 true-response bin 24 MISMATCH
20 1 nearest-labelled bin 20 true-response bin 20
15 1 nearest-labelled bin 15 true-response bin 15
15 2 nearest-labelled bin 31 true-response bin 30 MISMATCH
10.91 1 nearest-labelled bin 11 true-response bin 11
10.91 2 nearest-labelled bin 22 true-response bin 22
8.57 1 nearest-labelled bin 9 true-response bin 9
8.57 2 nearest-labelled bin 18 true-response bin 17 MISMATCH
```

Builder and tester found the 101 fundamental; the 2f0 lines of 103 (bin 31 vs 30) and
105 (bin 18 vs 17) are also wrong and untested. The plan's acceptance has the verifier
tabulate the printed target-bin power, and reports copy numbers verbatim from logs,
so the default run would put "24 Hz: ×~1 median" for S03–S05 into the log, i.e. a
result that could be wrong without an error (FAIL, not a note). The band maximum plus
the `--fs 256` run does not suffice by itself, because the misleading number is still
the default output. Decision: **fix** — keep the nearest-labelled bin (it is the legacy
reading of the axis) and add the true-response bin next to it. The legacy figure is
not changed.

### Judgement (2): occipital set, loader, mask

- Name-based selection: PASS. `O1, Oz, O2` by name, count checked against the array,
  missing/duplicate name raises (`spectral_power.py:36-52`, `diagnose_occipital_spectra.py:53`, `:155`);
  positional mutant caught by a decoy at positions 4–6. Note: in config v1 the names sit at
  positions 4, 5, 6 (`configs/pipeline_config.yaml:11`), so the real run cannot distinguish name
  from position; the reordered-names test is what proves it.
- PF-09 loader: PASS. Only `<dir>/<S>/`, missing file → skip, length and ndim checks
  (`diagnose_occipital_spectra.py:104-128`); root-array and `S03_backup` traps tested.
- Mask: LEGACY (by design), thresholds explicit (above). The mask re-runs on windows P02
  already gated with the same limits, so "rejected 0" is a consistency check, not a
  data-quality figure (bug pattern P02: diagnostics on filtered subsets). The scribe must
  not report it as a rejection rate; the P02 losses (8 `vpp_high`) remain the quality record.
  The mask is also applied to 201/202 rows before they are dropped (`visualize_data.py:138-139`); harmless.

### Judgement (3): deviations

1. NEW `src/features/ssvep/spectral_power.py` and MODIFIED `src/visualization/signal_plots.py`: accepted.
   No import side effects, type hints, docstrings (02_REQ §4); P02 plot functions untouched; Agg at
   `signal_plots.py:13`. The P02 `spectra` figures cannot change.
2. `visualize_data.py` importing helpers from the other script (`visualize_data.py:44-46`): accepted
   for P03, CONCERN for later phases: P05/P07 extend `visualize_data.py`, and any edit to the
   occipital script's loader or `stimulus_conditions` silently changes it. Move the loader to `src/`
   when P05 touches it (non-blocking).
3. Extra flags (`--out-suffix`, `--features`, `--no-figures`, `--processed-dir`, `--figures-dir`, four
   threshold flags): accepted; defaults reproduce the planned run.
4. `format_peaks` TypeError for a code without f0 (`diagnose_occipital_spectra.py:181-182`, `f0:.2f` on
   None): unreachable today via `stimulus_conditions` (`:81-85`), but the function is being edited for
   fix 1 anyway and P17 adds 201 as a class; fix it in the same change.

### Required fixes

1. **signal-processing — R9 / PF-04, `src/features/ssvep/spectral_power.py:105-113`,
   `scripts/exploration/diagnose_occipital_spectra.py:138-188`, `:258`.**
   (a) Give `spectrum_peaks` (or `occipital_class_spectra`) the header fs and the window length,
   and add per harmonic the **response bin** `k_resp = round(h·f0·T/header_fs)`, its label on the
   analysis axis `f[k_resp]`, its power and its ratio to the band median; keep the existing
   nearest-labelled bin, named as such. Print both, e.g. `1f0 response bin 24 (23.438 Hz) P=… (×… median);
   nearest-labelled bin 25 (24.414 Hz) P=…`. When fs equals header fs they coincide; print one.
   (b) Print per class a **specificity ratio**: power of the class spectrum at its own 1f0
   response bin divided by the median, over the other stimulus classes, of their spectra at that
   same bin (all from `res["spectra"]`, no new data). It separates an SSVEP peak from alpha that
   every class shares (104 at 10.91 Hz, 105 at 8.57 Hz, P02 S01 101 → 10 Hz) and is used in the
   criterion below.
   (c) `format_peaks`: a code without an entry in `STIM_FREQS_HZ` prints the maximum line only.
   No change to the figures, the default fs, the axis or the PSD script is required.
2. **synthetic-tester — tests for fix 1, `tests/test_p03_exploration_known_answer.py`.**
   (a) fs 250, header 256: sinusoids sampled at 256 Hz at 24, 30 (2·15) and 17.1429 (2·60/7) Hz →
   response bins 24, 30, 17 vs nearest-labelled bins 25, 31, 18; the response bin is the argmax of
   the planted spectrum (for the integer-bin 24 and 30 Hz cases its power equals (N/2)²·A², rtol 1e-9)
   and the nearest-labelled bin is not; a mutant reading the nearest-labelled bin as the response
   must fail. (b) fs 256: response bin = nearest bin for all eight in-band harmonics.
   (c) Specificity: f0 planted only in its own class (noise-free or fixed-seed noise) → ratio ≫ 1
   (state the analytic value); the same 10.909 Hz sinusoid (response bin 11) in all five classes →
   ratio ≈ 1 for 104 (tolerance derived in the test). (d) `format_peaks` with 201 in `conditions`
   does not raise.
3. **runner (via orchestrator, `05_run.md`) — add the fourth run line already offered by the builder:**
   `.venv/bin/python -m scripts.exploration.visualize_data --all --fs 256 --out-suffix header`
   (expected `max |computed - saved| = 0` for every subject; this is the only real-data check that
   the recomputed PSD equals P02's arrays).

### Non-blocking notes

- The legacy figures draw the target line at f0 while the energy sits at f0·250/256, half a
  bin left for 24 Hz. That is the legacy look and stays; the criterion below reads the header figure.
- Stale figures of a later-skipped subject are not removed (03 known limitation); the verifier
  should check figure mtimes against the run log.
- `fs_label` prints `override` for any fs other than 250/header; fine.

### Pre-committed criterion for the results review (fixed before the run)

Primary evidence: `outputs/figures/exploration/<S>/occipital_spectra_header.png` (fs 256, true
axis, mean `|rfft|²` over O1/Oz/O2, log y, shared y across the five panels) and the console
block of the `--fs 256` run in its log. Secondary: the legacy `occipital_spectra.png` and
`psd_features_by_class.png`. Response bins at fs 256: 101→24, 102→20, 103→15, 104→11, 105→9 (1 Hz bins).

Per subject × class, the fundamental is graded:

| Grade | Rule (all parts must hold) |
|---|---|
| clear | band maximum (5–35 Hz) at the response bin, **and** response-bin power ≥ 2× band median, **and** specificity ratio ≥ 1.5 |
| visible | response bin is a local maximum in the figure (above both neighbours), **and** ≥ 2× band median, **and** specificity ≥ 1.5 |
| partial | ≥ 1.5× median with local maximum or a two-bin plateau with a neighbour (for 105 the 8.57 Hz power splits between bins 8 and 9: a local maximum at bin 8 or 9 counts here, P02 precedent), or ≥ 2× median but specificity < 1.5 (labelled "alpha-confounded" for 104/105) |
| absent | none of the above |

- 2f0 (response bins 30 for 103, 22 for 104, 17 for 105; 40/48 Hz out of band) and the alpha
  peak (8–12 Hz) are recorded separately and never count towards the fundamental.
- **Strong responders** are fixed a priori as S03, S04, S05 (P02 figure review, R-6 levels).
  Acceptance "visible fundamental peaks for the strong responders" holds for a subject with
  ≥ 4/5 classes clear or visible; 3/5 is accepted as partial and recorded per class (as P02 S03
  8.57 Hz); ≤ 2/5 in any of S03–S05 → REJECT and investigate channels, labels and fs before any
  interpretation (a pipeline error is likelier than a lost responder).
- **S01, S02**: every class graded and recorded (including where the maximum is, e.g. P02's
  S01 101 → 10 Hz); no threshold, no tuning.
- **Legacy identity check**: for every subject × class, the band-maximum bin index in the
  fs 250 run equals that of the fs 256 run, and the label equals k·250/256; any difference → REJECT.
- Mask: `rejected 0` for every subject expected (same limits as P02); any rejection is an anomaly
  to explain before APPROVE. `max |computed - saved| = 0` expected in the fix-3 run.
- Nothing is re-run with other parameters to reach a grade (golden rule 5).

## Pre-run audit — Round 2

Verdict: PASS

Reviewed at 629e22b: `git diff b4bc757..HEAD` (1869c0a, 78ea210, 89d2b9e, d7a7cac, ee17403, 639ac72).
Suite: `.venv/bin/python -m pytest tests/ -p no:cacheprovider -o addopts="" -q` → `311 passed in 20.51s`.

| Round-1 fix | Result | Evidence |
|---|---|---|
| 1(a) response bin | PASS | `response_bin` = `floor(f·T/header_fs + 0.5)` `src/features/ssvep/spectral_power.py:87-96`; `spectrum_peaks` keeps `k/f_bin/power` (nearest-labelled) and adds `k_resp/f_resp/power_resp`, raises if the response bin falls off the axis `:98-134`; header fs (samples / `sub_window_sec`) passed from `main` `scripts/exploration/diagnose_occipital_spectra.py:304-305`; nearest-labelled bin printed only when it differs `:224-227` |
| 1(b) specificity | PASS | `specificity_ratio` own / median of other stimulus classes at the 1f0 response bin, 201/202 excluded `diagnose_occipital_spectra.py:186-200`; computed from `res["spectra"]` only `:179-182`; printed per class `:228-232` |
| 1(c) rest codes | PASS | `format_peaks` omits target, harmonics and specificity for codes without f0 `:203-218`; figures, default fs, axis and `visualize_data.py` unchanged (no diff) |
| 2(a) 24/30/17 vs 25/31/18 | PASS | `test_response_bins_legacy_axis_24_30_17`: argmax = response bin ≠ nearest-labelled; exact-bin power (N/2)²A² = 65536; mutant `round(f·T/250)` asserted to fail; console line check incl. 105 `2f0 response bin 17 (16.602 Hz)` in `test_response_bins_through_class_spectra_and_console` |
| 2(b) coincidence at fs 256 | PASS | `test_response_bin_equals_nearest_at_header_fs`: all eight in-band harmonics 24, 20, 15, 30, 11, 22, 9, 17; no nearest-labelled text |
| 2(c) specificity known answers | PASS | analytic 1 + (AN/2B)² checked by `.venv/bin/python -c "print(1+(10*256/(2*50))**2)"` → `656.3600000000001`; nearest-bin mutant fails; shared 120/11 Hz rhythm → 104 ratio within 0.02 of 1 (tolerance derived from noise variance in the docstring), noise-free exactly 1 |
| 2(d) format_peaks with 201/202 | PASS | `test_format_peaks_with_rest_codes`: exact rest lines, `n_others` 4 |
| 3 fourth run command | PASS | `02_plan.md` "Amendment — pre-run audit Round 1" lists `visualize_data --all --fs 256 --out-suffix header`, expected `max |computed - saved| = 0`, and points to the criterion above |
| Privacy | PASS | `git ls-files` filtered for data/npy/outputs/reports/local tooling: 0; fragment-built vendor/co-author grep over `HEAD` (all paths) and `git log --format=%B main..HEAD`: 0 hits |

Rule table of Round 1 stands, with R9 now PASS and the test-coverage CONCERN (2f0 untested)
resolved. No new FAIL or CONCERN. Hand-checked variants: response bin taken on the labelled
axis (caught by 2a), specificity read at the nearest-labelled bin (caught by 2c), 201/202
counted among the other classes (caught by 2d, `n_others` 4).

Non-blocking: `specificity_ratio` returns `inf` when the other classes' median is exactly 0
(only on synthetic zero spectra); not reachable on real data.

The pre-committed criterion (Round 1) is unchanged and governs the results review; the
console line now gives response-bin power, ratio to the band median and specificity directly.
The runner may proceed with the four commands of `02_plan.md` (amendment).

## Results review

Verdict: APPROVE

Reviewed: `05_run.md` (7405cd1), `06_verify.md` (e9c9ae6, PASS); logs
`reports/logs/P03/diagnose_occipital_spectra_header_20261024T180126.log` (primary),
`diagnose_occipital_spectra_fs250_20261024T180123.log`, `visualize_data_fs250_20261024T180129.log`,
`visualize_data_header_20261024T180134.log`; figures `outputs/figures/exploration/S0{1..5}/occipital_spectra_header.png`
opened (all five). Data source (R9): legacy, `data/processed/<S>/` from P02, session OO; occipital mean O1/Oz/O2
(channels `[4, 5, 6]` by name, log). Criterion applied exactly as pre-committed (Round 1); nothing re-run.

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-x | none for P03 (`04_REFERENCE_RESULTS.md`) | — | — | — | acceptance is the figure criterion below | — |
| Mask consistency | rejected 0 (same limits as P02) | `kept 320/320, 318/318, 317/317, 317/317, 320/320, rejected 0` (both `visualize_data` logs; `grep -c "rejected [1-9]"` = 0, 0) | 0 | yes | — | yes |
| PSD consistency (fix 3) | `max |computed - saved| = 0` | `= 0` for S01–S05 (`visualize_data_header_…log`) | 0 | yes | — | yes |
| Legacy identity | band-max bin equal at fs 250 and 256; label = k·250/256 | 25 / 25 rows (my own regex over both occipital logs, `.venv/bin/python -c "…re.findall(r'max in band at ([\d.]+) Hz \(bin (\d+)'…)"` → `25 25 25`; verifier 25/25) | 0 | yes | PF-04 shift only relabels the axis | yes |

### Grades (pre-committed criterion; numbers verbatim from the fs-256 occipital log)

Columns: band max (bin) | 1f0 response bin, ×band median | specificity | local max at response bin in the
figure | grade.

| S | Class | Band max | 1f0 ×median | Spec. | Local max | Grade |
|---|---|---|---|---|---|---|
| S01 | 101 24 Hz | 10 Hz (10) | bin 24 ×0.88 | ×1.48 | small bump | absent |
| S01 | 102 20 Hz | 8 Hz (8) | bin 20 ×1.41 | ×1.42 | small bump | absent (< 1.5× median) |
| S01 | 103 15 Hz | 8 Hz (8) | bin 15 ×2.10 | ×0.99 | marginal | partial (non-specific: spec < 1.5) |
| S01 | 104 10.91 Hz | 11 Hz (11) | bin 11 ×4.28 | ×1.78 | yes | clear by the rule (see caveat) |
| S01 | 105 8.57 Hz | 8 Hz (8) | bin 9 ×2.05 | ×0.87 | no (bin 9 below bins 8 and 10) | partial (alpha-confounded) |
| S02 | 101 24 Hz | 6 Hz (6) | bin 24 ×1.04 | ×1.29 | no | absent |
| S02 | 102 20 Hz | 6 Hz (6) | bin 20 ×1.00 | ×1.19 | no | absent |
| S02 | 103 15 Hz | 6 Hz (6) | bin 15 ×3.64 | ×1.49 | yes | partial (spec 1.49 < 1.5) |
| S02 | 104 10.91 Hz | 6 Hz (6) | bin 11 ×4.89 | ×1.24 | no (falling slope after bin 10) | partial (alpha-confounded) |
| S02 | 105 8.57 Hz | 6 Hz (6) | bin 9 ×8.87 | ×1.01 | yes | partial (alpha-confounded: 9 Hz peak in every class) |
| S03 | 101 24 Hz | 24 Hz (24) | ×5.97 | ×12.12 | yes | clear |
| S03 | 102 20 Hz | 20 Hz (20) | ×12.93 | ×15.73 | yes | clear |
| S03 | 103 15 Hz | 15 Hz (15) | ×14.32 | ×9.33 | yes | clear |
| S03 | 104 10.91 Hz | 11 Hz (11) | ×6.94 | ×2.17 | yes | clear |
| S03 | 105 8.57 Hz | 9 Hz (9) | ×4.63 | ×2.43 | yes | clear |
| S04 | 101 24 Hz | 24 Hz (24) | ×9.59 | ×20.92 | yes | clear |
| S04 | 102 20 Hz | 20 Hz (20) | ×14.68 | ×20.17 | yes | clear |
| S04 | 103 15 Hz | 15 Hz (15) | ×29.56 | ×14.55 | yes | clear |
| S04 | 104 10.91 Hz | 11 Hz (11) | ×31.47 | ×16.37 | yes | clear |
| S04 | 105 8.57 Hz | 9 Hz (9) | ×9.55 | ×4.73 | yes | clear |
| S05 | 101 24 Hz | 24 Hz (24) | ×8.74 | ×19.54 | yes | clear |
| S05 | 102 20 Hz | 20 Hz (20) | ×5.46 | ×6.78 | yes | clear |
| S05 | 103 15 Hz | 15 Hz (15) | ×10.87 | ×6.59 | yes | clear |
| S05 | 104 10.91 Hz | 22 Hz (22, = 2f0) | ×8.22 | ×3.53 | yes | visible |
| S05 | 105 8.57 Hz | 17 Hz (17, = 2f0) | ×5.01 | ×2.48 | yes (bin 9 just above bin 8 on the log axis) | visible (partial at worst under the 8/9 plateau clause; decision unchanged) |

**Strong responders (fixed a priori):** S03 5/5 clear; S04 5/5 clear; S05 3 clear + 2 visible = 5/5.
All ≥ 4/5 → acceptance met: visible fundamental peaks confirmed for S03, S04, S05.

**S01, S02 (recorded, no threshold):** S01: 1 clear (104), 2 partial (103 non-specific, 105
alpha-confounded), 2 absent (101, 102); band maxima at 8–11 Hz in every class (101 → 10 Hz, as
P02). S02: 0 clear/visible, 3 partial (103, 104, 105; all fail specificity), 2 absent (101, 102);
band maximum at 6 Hz in every class, with a second 9 Hz peak in every class.
Caveat on S01 104: it passes the rule (×4.28, spec ×1.78), but 11 Hz is inside S01's alpha
range (the other classes peak at 8–10 Hz) and the specificity is the lowest among the "clear"
cells; read it as a weak, possibly alpha-assisted 10.91 Hz response, not as a responder.

**2f0 (separate, response bins 30/22/17):** S03 ×1.92 / ×1.60 / ×0.93; S04 ×1.03 / ×1.67 / ×5.71;
S05 ×4.42 / ×11.11 / ×13.50 (2f0 is the band maximum for S05 104 and 105); S01 ×0.22 / ×0.88 / ×1.90;
S02 ×0.97 / ×0.85 / ×1.50 (log). Ratios checked: `.venv/bin/python -c "print(round(1.527e5/1.374e4,2), round(1.71e5/1.266e4,2))"` → `11.11 13.51`
(log prints ×13.50 from unrounded values).

**Alpha / low band (separate):** S01 8–11 Hz maxima in all classes; S02 6 Hz maximum and 9 Hz peak in all
classes; S03 101 and S05 101 show secondary peaks near 10–11 Hz in the figures.

### Interpretation check

- Per-subject reading (R9) above; no cohort-only statement.
- The S03 8.57 Hz target, partial in P02's 7-channel mean, is clear in the occipital O1/Oz/O2 mean
  (bin-9 maximum, spec ×2.43): the channel set, not the data, explains the P02 plateau.
- S05's low-frequency classes are dominated by the 2nd harmonic: feature sets with harmonics (FBCCA,
  P05) should help S05 104/105 more than fundamental-only PSD.
- S01/S02 have no class-specific fundamental peaks except S01 104 (weak); their low R-6 accuracies
  (61.00/67.50 %, 56.12/61.73 %) are consistent with this and are not a pipeline defect.
- The quality mask's "rejected 0" is a consistency check on already-gated windows, not a rejection
  rate (pre-run note); P02's 8 `vpp_high` losses remain the quality record.
- `06_verify.md` §3 prose quotes S05 2f0 ratios as ×11.3 / ×14.5; the log says ×11.11 / ×13.50. The
  verifier's table is correct; the scribe must take these numbers from the log, not the prose.
- No fitted object, normalization, split or statistic exists in P03 (no leakage path).

### Carry-forward for RESEARCH_LOG (P03.3) and later phases

- P03.3: clear SSVEP fundamentals in S03, S04 (5/5) and S05 (5/5, 104/105 via strong 2f0);
  none in S02; S01 only a weak 10.91 Hz response; S01/S02 spectra dominated by 8–11 Hz (S01) and
  6/9 Hz (S02) activity in every class.
- P04/P05: expect S01/S02 near chance-to-moderate and S05 104/105 to gain from harmonics; any S01/S02
  accuracy far above R-6 is a leakage suspect (golden rule: surprising gains are bugs).
- P16 (fs fix): legacy fs 250 only relabels the axis on these arrays (identity 25/25); the effect of
  PF-04 appears where 250 Hz enters filters and reference sinusoids (P04/P05), not here.

### Decisions for decisions.md

- P03 | Figure criterion (pre-committed, 07_review Round 1) met: S03 5/5 clear, S04 5/5 clear, S05 3 clear + 2 visible (104/105 band maxima at 2f0); acceptance confirmed. No parameter changed | `P03-exploration/07_review.md` results review
- P03 | S01: 104 clear by rule but alpha-adjacent (spec ×1.78), 103/105 partial, 101/102 absent, maxima 8–11 Hz; S02: no clear/visible class, maxima at 6 Hz, 9 Hz peak in every class — carried to P04/P05 interpretation and RESEARCH_LOG | same
- P03 | S03 8.57 Hz (partial in P02 7-channel mean) is clear in the O1/Oz/O2 mean (bin 9, spec ×2.43); P02 partial attributed to the channel set | same
- P03 | Legacy fs 250 identity 25/25, mask rejected 0, PSD recomputation = saved (0) for S01–S05 | logs `reports/logs/P03/*`
- P03 | `06_verify.md` §3 prose S05 2f0 ratios (×11.3/×14.5) superseded by the log values ×11.11/×13.50 | `diagnose_occipital_spectra_header_20261024T180126.log`

## Sources spot-check

1. RULE — `mas/RULES.md` era matrix (R5 from P16, fs from metadata from P16), R6, R9 (opened in this run).
2. RULE — `mas/05_PITFALLS.md` PF-04, PF-05, PF-06 (opened in this run).
3. RULE — `mas/01_DATA_SPEC.md` §6 (occipital set `O1, Oz, O2` by name; 5-class = stimulus windows) (opened in this run).
4. RULE — `mas/02_REQUIREMENTS.md` §4 (CLI, skip line, Agg, no side effects in `src/`) (opened in this run).
5. DECISION — `mas/state/decisions.md` P02 carry-forward rows and P03 Q1/Q2 rows (opened in this run).

## Questions
