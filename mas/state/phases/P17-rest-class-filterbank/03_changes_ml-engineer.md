# P17 · 03 · Changes — ml-engineer

Status: READY
Author: ml-engineer
Branch: phase/P17-rest-class-filterbank
Tasks: P17.3, settled points 2–7 (C-2)

## Files

| Path | | What |
|---|---|---|
| `scripts/benchmarks/feature_based/benchmark_n_subjects.py` | MODIFIED | `--bank {base,harm,harm+mid}`, `--classes {5,6}`, `--allow-fs-override`; `make_model` (uniform priors 1/6 for 6 classes); `bank_bands_text`; `feature_blocks(d, m, bank)`; 6-class columns, SD columns, `confusion_frame` -> `<csv>_confusion.csv`; derived suffix parts `harm`/`harmmid`, `6class`; C-2 (no `GATE_THRESHOLDS`; `thresholds=None` raises; `--fs` on a built root raises) |
| `src/models/classical/rest_metrics.py` | NEW | `rest_metrics` (BalAcc, FalseAct, Missed, StimCorrect, %), `confusion_counts` |
| `tests/test_p17_benchmark.py` | NEW | 21 tests |
| `tests/test_p16_independent_known_answer.py` | MODIFIED | 3 calls of `evaluate_subject` now pass `thresholds=` (they relied on the removed fallback) |

Commits: `20a7607 feat: --bank and --classes 6 in the n-subjects benchmark, rest metrics, no threshold fallback`; a later commit for the header-line change and this file.

## Behaviour

- **Banks.** Loader reads `fbcca`, `fbcsp` + `harmonic` (`harm`) + `intermediate` (`harm+mid`). CSP sub-bands = `fbcsp` (5) ‖ `harmonic` (14) ‖ `intermediate` (4), concatenated on the band axis in that order (R6); counts and edges from `windows_meta.json["bands"]`, mismatch raises. FBCSP m = 1 per band, in-fold; FBCCA unchanged. `Bank` column: `fbcca` (base, as P16), `fbcca+harm`, `fbcca+harm+mid`; `CSP Bands` lists every band `low-high`.
- **6 classes.** Conditions 101–105 + 201 (`load_subject` conditions; 202 never selected, asserted); legacy root raises `ValueError` (main prints `[x]` and returns 1); LDA `priors = 1/6`; groups `cv_groups` (== `trial_ids`, asserted), `assert_no_shared_trials` per repeat (R1); R8 smoothing resets at each trial id, 201 trials included (2 windows each). `Clean Windows` includes rest windows; `Rest Windows` = clean 201 count.
- **Columns** (after the SD block): `Rest Windows, 1.0s BalAcc (%), 2.0s BalAcc (%), 1.0s FalseAct (%), 2.0s FalseAct (%), 1.0s Missed (%), 2.0s Missed (%), 2.0s StimCorrect (%)`, then under `--cv-repeats>1` the SD (ddof 1) of each: `1.0s BalAcc SD, 2.0s BalAcc SD, 1.0s FalseAct SD, 2.0s FalseAct SD, 1.0s Missed SD, 2.0s Missed SD, 2.0s StimCorrect SD`. Mean row: mean of the rounded subject values.
- **Definitions** (settled point 4): FalseAct = rest windows predicted as any stimulus, % of rest; Missed = stimulus windows predicted as rest, % of stimulus; StimCorrect = stimulus windows predicted as their own stimulus, % of stimulus; BalAcc = sklearn balanced accuracy (mean per-class recall).
- **Confusion** (6 classes only): `<csv stem>_confusion.csv`, columns `Subject, True, 101, 102, 103, 104, 105, 201, CV repeats`; rows = true class, columns = predicted; 2.0 s predictions, summed over the CV repeats of a subject; block `Sum` = over subjects.
- **C-2.** `evaluate_subject` raises if `thresholds` is None; `--fs` on a built root raises (main: `[x]`, rc 1) unless `--allow-fs-override` (diagnostic only). `fail_fraction` keeps its default `CHANNEL_FAIL_FRACTION` (not asked).
- **Legacy default unchanged.** Old (5e248a0) and new script run on a synthetic legacy root and a synthetic built root (`--cv-repeats 2`): CSV and `.meta.txt` byte-identical (4 of 4). The P16 legacy test `tests/test_p16_flagship_port.py` passes (73 tests with the independent known-answer file).

## Tests (`tests/test_p17_benchmark.py`, 21 pass; synthetic folders only)

Bank band counts 5/19/23 and column order `fbcsp ‖ harmonic ‖ intermediate` against the saved arrays; band text from meta edges (23-25 first harmonic, 8.74-10.74 first midpoint); row labels and `p=` width; bank/6 classes on a legacy root raise; 6 classes select 101–105 + 201 and exclude 202 (the folder has 202), groups = true ids, rest ids disjoint from stimulus ids; priors 1/6 and the fitted `priors_` (201 has 20 windows vs 16); 201 smoothing restarts per trial; 6-class row columns, SD columns, summed confusion (every window once per repeat); metrics against a constructed confusion (FalseAct 50, Missed 25, StimCorrect 75, BalAcc 66.67; swap-detecting); stimulus-to-other-stimulus is neither Missed nor correct; C-2 (no `GATE_THRESHOLDS` in the source, `thresholds` required, `--fs` raises without the flag, legacy `--fs` allowed); suffix names; `main` 6-class writes both CSVs; 5-class built run has no 6-class columns or confusion file. Failing on the old code: C-2 test (fallback existed), metric tests (module absent).

Suite: `pytest tests/ -q -o addopts=""` (log mas/state/scratch/p17_suite_ml.log): `1133 passed, 22 warnings in 608.73s (0:10:08)`

## Smoke (S03 only, `--quality shared --cv-repeats 10`, built with the data-signal command to `mas/state/scratch/p17_ml/`, folder deleted afterwards; shared guard 1.046875 s)

Runtime is the console `wall` of one subject (build 1.5 s).

| bank | classes | 1.0 s | 2.0 s | features p | wall |
|---|---|---|---|---|---|
| base | 5 | 93.76 | 93.92 | 55 | 4.4 s |
| base | 6 | 92.73 | 93.51 | 65 | 6.0 s |
| harm | 5 | 99.38 | 99.48 | 195 | 9.9 s |
| harm | 6 | 94.39 | 95.24 | 233 | 14.3 s |
| harm+mid | 5 | 99.33 | 99.43 | 235 | 11.6 s |
| harm+mid | 6 | 94.35 | 95.42 | 281 | 16.5 s |

6-class (2.0 s mean over 10 repeats): base BalAcc 92.64 / FalseAct 1.17 / Missed 5.36 / StimCorrect 91.39; harm 94.50 / 0.13 / 6.55 / 93.40; harm+mid 94.69 / 0.00 / 6.34 / 93.61. Clean windows S03: 194 (5 classes), 271 (6 classes; 77 rest). Estimate for 5 subjects serial: 20–85 s per command, whole set about 6 min (`--n-jobs` available).

Flag for the reviewer: S03 5-class accuracy rises 93.9 -> 99.5 % with the harmonic bands. All fits are in-fold (CSP in `oof_space`/`fold_matrices`, scaler in the Pipeline), `assert_no_shared_trials` runs every repeat; no leak found, but by golden rule 5 treat as unexplained until the reviewer's checks (one subject, 1 s windows, narrow +-1 Hz bands at the stimulus frequencies and their harmonics). Base here is 93.76 vs the P16 row c because of the `_p17` mask (guard 1.047 s), not compared (generated files not read).

## Verifier commands (all read the `_p17` root; build per `03_changes_data-signal.md`; add `--n-jobs 5` optionally, it does not change results)

```bash
P=".venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects"
R="--data-root data/processed_continuous_p17 --quality shared --cv-repeats 10"
$P $R --bank base     --classes 5 --out-suffix p17_base_5class
$P $R --bank base     --classes 6 --out-suffix p17_base_6class
$P $R --bank harm     --classes 5 --out-suffix p17_harm_5class
$P $R --bank harm     --classes 6 --out-suffix p17_harm_6class
$P $R --bank harm+mid --classes 5 --out-suffix p17_harmmid_5class
$P $R --bank harm+mid --classes 6 --out-suffix p17_harmmid_6class
```

Outputs `reports/n_subjects_benchmark_<suffix>.csv` (+ `.meta.txt`) for the six suffixes, and `reports/n_subjects_benchmark_p17_{base,harm,harmmid}_6class_confusion.csv`. Without `--out-suffix` the derived names would be `continuous_rep10`, `continuous_harm_rep10`, `continuous_harmmid_6class_rep10`, etc.

## R11 consultations

None (reference code not opened).
