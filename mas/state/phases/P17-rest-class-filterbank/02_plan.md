# P17 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/02_REQUIREMENTS.md §3 (`filter_bank:`), §5.6–5.7, §6 (`n_subjects_benchmark` 6-class columns), mas/04_REFERENCE_RESULTS.md R-16, mas/05_PITFALLS.md PF-02/03/13, decisions.md P16 rows (C-1, C-2, C-5)
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Add harmonic and intermediate narrow-band banks to the built folders, and evaluate the
flagship with three banks (base, harm, harm+mid) and with 5 or 6 classes (the sixth being
the fixation cross, "no stimulus"), each over 10 CV repeats with SDs.

## Data source

- `data/processed_continuous/<S>/` (P16 continuous build, OO, 1.0 s, stride None, shared
  quality with guard), **rebuilt** in this phase with banks `fbcca fbcsp harmonic
  intermediate`. The rebuild must leave every P16 file byte-identical (X_time, X_raw,
  X_bands_fbcca, X_bands_fbcsp, labels, ids, starts, masks, reasons) except
  `windows_meta.json` (which gains the new banks, `bands_skipped`, `band_overlaps`) and
  the two new `X_bands_*` files. The verifier hashes before and after.
  Rationale: P18+ read the default built root, which must carry all banks.
- Guard `auto` is recomputed over all filters applied continuously (P16 deviation a). If
  the new order-2 narrow filters ring longer than 0.902 s the guard, and so the masks,
  change. The data-signal builder measures the new ringing times first and reports them.
  If the guard changes, the rebuild goes to `data/processed_continuous_p17/` instead, the
  P16 root stays untouched, and the phase reports the mask change (decided now, before any
  number).

## Settled points (inferred; recorded in decisions.md)

1. **Bands.** `harmonic_centers(3)` = k·f for k = 1..3 of the 5 targets (15 centres);
   `intermediate_centers()` = the 4 midpoints of the sorted targets; half-width 1 Hz,
   Butterworth order 2 (config `filter_bank:`), `max_hz` = config highcut 90, notch 60 Hz
   excluded: a band is skipped if its upper edge exceeds `min(max_hz, nyq − 1)` or it
   contains the notch (20 Hz × 3 = 60 Hz is skipped). Skips and overlaps go to meta.
2. **`--bank`.** `base` = the 5 FBCSP bands (P16 flagship); `harm` = base + harmonic bands;
   `harm+mid` = base + harmonic + intermediate. CSP m = 1 per band as the flagship; FBCCA
   features unchanged (Chebyshev bank) in all three.
3. **6 classes.** Classes 101–105 + 201 (201 only; 202 never enters, PF-13, C-5). Uniform
   LDA priors (`priors = 1/6`). Built folders only; a legacy root raises. Groups =
   true trial ids (`trial_ids`; no 202 selected, so `cv_groups == trial_ids`). The 201
   trials have 2 windows, so 2.0 s smoothing applies to their second window, same rule as
   stimuli (R8).
4. **Metrics** (§5.7). 5-class: accuracy at 1.0 s and 2.0 s. 6-class adds balanced accuracy,
   false activation (rest windows predicted as any stimulus, % of rest windows), missed
   stimulus (stimulus windows predicted as rest, % of stimulus windows) and stimulus-correct
   (stimulus windows predicted as their own stimulus, % of stimulus windows) at 2.0 s;
   summed 2.0 s confusion matrices (over folds, per repeat summed over repeats, labelled)
   to `<csv>_confusion.csv`.
5. **Repeats.** `--cv-repeats 10`, seeds 42+r; SD (ddof 1) over repeats; seed 42 printed.
6. **Outputs.** `reports/n_subjects_benchmark_<suffix>.csv` with the suffix rule of P16;
   the six suffixes are fixed by the ml-engineer and listed in the handoff; 6-class names
   contain `6class`.
7. **Carry-forwards.** C-1 (data-signal): `freeze_baseline` skips the redundant `Mean`
   subject row for later tags (v1 stays as frozen). C-2: `benchmark_n_subjects` loses the
   `GATE_THRESHOLDS` fallback (ml-engineer); `build_windows --filter-mode per_window`
   labels its output and meta `legacy` (data-signal); `--fs` on a built root raises unless
   `--allow-fs-override` is given, documented as diagnostic only (ml-engineer).
8. **Tests** never read generated or git-ignored files.

## Work split

| Order | Agent | Files (NEW / MODIFIED) | What | Task |
|---|---|---|---|---|
| 1 | data-signal | MODIFIED `src/preprocessing/windowing.py`, `scripts/build_windows.py`, `scripts/freeze_baseline.py` | P17.1, P17.2, settled points 1, 7 (C-1, per_window label), the ringing-time check of "Data source" | P17.1–2 |
| 2 | ml-engineer | MODIFIED `scripts/benchmarks/feature_based/benchmark_n_subjects.py`, `src/features/ssvep/fbcsp_extraction.py` as needed, `src/models/classical/*` as needed | P17.3, settled points 2–7 (C-2) | P17.3 |

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R6 | band order or bank concatenation misaligned | planted tone at 2·f0 lands in the harmonic band of that centre; `harm` band list = base + harmonics in meta order |
| PF-04 | band edges from a literal fs | centres from `STIM_FREQS`, fs from meta; skip rule tested at fs 256 and a lower fs |
| Notch | a band containing 60 Hz kept | test: 60 Hz band skipped and recorded |
| PF-13 | 202 used as rest | test: `--classes 6` selects 201 only |
| R1 | rest windows and stimulus windows from one trial split across folds | groups are true trial ids, `assert_no_shared_trials` |
| Priors | LDA priors from class frequencies (201 has 80 windows vs 40 per stimulus) | test: priors uniform |
| Metrics | false-activation / missed definitions swapped | constructed confusion matrix with known rates |
| Rebuild | P16 files silently changed | byte-identity check (verifier) and the guard rule above |

## Tests required

| Test | Simulated input | Expected result | Tolerance |
|---|---|---|---|
| centres | — | 15 harmonic centres k·f; 4 midpoints | exact |
| skip rule | fs 256, max 90, notch 60 | 60 Hz band and bands above min(90, 127) skipped, listed | exact |
| narrow band | tone at 2·10.91 Hz | max power in the 21.82 Hz band | exact |
| overlaps | neighbouring narrow bands | overlap list in meta | exact |
| build | synthetic recording, banks all four | new X_bands files with (n, B, C, T); old files byte-identical to a two-bank build | exact |
| bank arg | synthetic built folder | harm / harm+mid band counts = base + listed | exact |
| 6 classes | planted 201 vs stimuli | rest windows included, 202 excluded, priors 1/6, legacy root raises | exact |
| metrics | constructed predictions | BalAcc, FalseAct, Missed, StimCorrect equal hand values; confusion summed | exact |
| C-1, C-2 | temp tree / parser | no Mean row; no threshold fallback; `--fs` on built root raises without the flag; per_window meta says legacy | exact |

## Run commands (for the verifier, in order)

Filled in from the two handoffs (the guard rule sends the build to the `_p17` root;
decisions.md P17 row 2).

```bash
P=".venv/bin/python -m"
# 1. build (P16 root untouched; the verifier hashes data/processed_continuous before and after)
$P scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp harmonic intermediate --out-root data/processed_continuous_p17
# 2-7. benchmarks
B="$P scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed_continuous_p17 --quality shared --cv-repeats 10"
$B --bank base     --classes 5 --out-suffix p17_base_5class
$B --bank base     --classes 6 --out-suffix p17_base_6class
$B --bank harm     --classes 5 --out-suffix p17_harm_5class
$B --bank harm     --classes 6 --out-suffix p17_harm_6class
$B --bank harm+mid --classes 5 --out-suffix p17_harmmid_5class
$B --bank harm+mid --classes 6 --out-suffix p17_harmmid_6class
```

Estimate: rebuild ~1 min; P16 5-repeat built runs took < 30 s each; 10 repeats with up to
5 + 15 + 4 bands and 6 classes, maybe 1–3 min each; total < 30 min plus the ~10 min
suite, inside `LOCAL_RUN_BUDGET_MIN` 120.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked |
|---|---|
| all combinations produce CSVs | six `n_subjects_benchmark_*` CSVs (three with `6class`) + three `_confusion.csv`, §6 columns, 10 repeats |
| the report compares banks and 5 vs 6 classes with SDs over repeats | per-subject and mean with SD; the reviewer pre-commits what counts as a bank difference |
| (no preserved reference — record) | R-16: no numeric target; the reviewer checks direction and plausibility |
| (data source) | P16 files byte-identical after the rebuild, or the guard rule applied |

## Sources

1. `mas/03_ROADMAP.md` P17 (opened in this run).
2. `mas/02_REQUIREMENTS.md` §3, §5.7, §6; `mas/04_REFERENCE_RESULTS.md` R-16 (opened in this run).

## Questions
