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

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

### Decisions for decisions.md

## Sources spot-check

1. RULE — `mas/RULES.md` era matrix (R5 from P16, fs from metadata from P16), R6, R9 (opened in this run).
2. RULE — `mas/05_PITFALLS.md` PF-04, PF-05, PF-06 (opened in this run).
3. RULE — `mas/01_DATA_SPEC.md` §6 (occipital set `O1, Oz, O2` by name; 5-class = stimulus windows) (opened in this run).
4. RULE — `mas/02_REQUIREMENTS.md` §4 (CLI, skip line, Agg, no side effects in `src/`) (opened in this run).
5. DECISION — `mas/state/decisions.md` P02 carry-forward rows and P03 Q1/Q2 rows (opened in this run).

## Questions
