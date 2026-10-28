# P17 · 03 · Changes — data-signal

Status: READY
Author: data-signal
Branch: phase/P17-rest-class-filterbank
Tasks: P17.1, P17.2, settled points 1 and 7 (C-1, per_window legacy label), ringing-time check of "Data source"

## Files

| Path | | What |
|---|---|---|
| `src/preprocessing/windowing.py` | MODIFIED | `STIM_FREQS`, `NARROW_DEFAULTS`, `BASE_BANKS`, `NARROW_BANKS`, `BANK_NAMES` (now 4), `harmonic_centers`, `intermediate_centers`, `narrow_filter_bank` (returns `(bank, bands_skipped)`), `band_overlaps`, `build_bank` (`(bank, skipped)`), `filter_bank` (optional `narrow` argument) |
| `scripts/build_windows.py` | MODIFIED | banks `harmonic`, `intermediate`; `--banks` default = `fbcca fbcsp` + banks enabled in config `filter_bank:`; `load_build_config` requires the `filter_bank:` keys; meta `bands_skipped`, `band_overlaps`, `data_source`, `legacy` (replaces the empty `skipped_bands`); console line `bands skipped`; per_window prints `Data source: legacy per_window build` |
| `scripts/freeze_baseline.py` | MODIFIED | C-1: `summary_rows(snapshot, skip_mean_row)`; `freeze` skips the CSV `Mean` row unless the tag is in `LEGACY_MEAN_ROW_TAGS = ("v1",)` |
| `tests/test_p17_windowing.py` | NEW | 10 tests (below) |
| `tests/test_p16_freeze_baseline.py` | MODIFIED | the monkeypatched `summary_rows` stub accepts the new keyword (one line) |

Commits: `d162ccc chore: P17 phase files, decisions and status`; `709615a feat: harmonic and intermediate narrow banks in windowing and build_windows`; this file in a later `docs:` commit.

## Bands (fs 256, config `filter_bank:`, Butterworth order 2, +-1 Hz, max 90 Hz, notch 60 Hz)

- `harmonic`: 15 centres target-major (24, 48, 72, 20, 40, 60, 15, 30, 45, 10.91, 21.82, 32.73, 8.57, 17.14, 25.71); 60 Hz skipped (contains the notch) -> **14 bands**, in centre order. Meta name `butter2_<low>-<high>` (two decimals).
- `intermediate`: 9.74, 12.955, 17.5, 22.0 -> **4 bands**, none skipped, no overlaps within the bank.
- Overlaps: meta `band_overlaps` = `{fbcca, fbcsp, harmonic, intermediate: pairs inside the bank; combined: pairs between different banks among fbcsp/harmonic/intermediate}`. S03: harmonic 2 pairs, combined 24 pairs (fbcca Chebyshev bands nest by design, 3 pairs).

## Ringing times and the guard decision (measured before building; existing `ringing_time_sec`, rel 0.01, fs 256)

| Filter | Ringing (s) |
|---|---|
| broadband (1-90 Hz order 4 + notch) | 0.301 |
| fbcca bands | 0.234 / 0.262 / 0.242 |
| fbcsp bands | 0.750 / **0.902** / 0.457 / 0.398 / 0.203 |
| harmonic bands (14) | 1.012 - 1.043 (max 1.043, band 23-25 Hz) |
| intermediate bands (4) | 1.035 - 1.047 (max **1.047**, band 21-23 Hz) |

**Guard `auto` over all continuous filters changes: 0.902 s -> 1.047 s** (S03 smoke prints `guard 1.047 s`). Per the plan's "Data source" rule the rebuild goes to **`data/processed_continuous_p17/`**; the P16 root stays untouched. Only `valid_mask` and `reject_reason` can differ from P16 (`valid_mask_no_guard`, X arrays, labels, ids, starts do not depend on the guard); the mask change (more `guard` rejections) is for the report. A two-bank build still gets 0.902 s.

Consequence for the byte-identity requirement: with `guard_sec: auto` a four-bank build differs from a two-bank build in `valid_mask.npy`, `reject_reason.npy` and `windows_meta.json` (guard) besides the new band files. With the guard fixed (`--guard-sec 1.5`) everything else is byte-identical; both facts are tests.

## Verifier build command

```bash
.venv/bin/python -m scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO \
  --banks fbcca fbcsp harmonic intermediate --out-root data/processed_continuous_p17
```

(the plan's command without `--out-root` would write to the P16 root; `--banks` may be omitted, the default is the same four.) Everything else (`--guard-sec`, window, stride) at defaults, as in P16. The ml-engineer's benchmark must therefore read `data/processed_continuous_p17` for the new banks (via the root argument of `load_subject`/the benchmark).

## Tests (`tests/test_p17_windowing.py`, 10 pass)

centres (15 harmonic values, 4 midpoints, sorting); skip rule (fs 256: only 60 Hz; fs 128: 60 and 72; max_hz; edge touching the notch; no notch; lower edge); tone at 2*10.91 Hz only lands in the 21.82 Hz harmonic band, other bands < 2 % of its power, band order = centre order (R6); overlaps (hand case, touching edges not counted, intermediate disjoint, harmonic overlapping); build identity (two vs four banks, fixed guard: every file byte-identical except `windows_meta.json` and the two new `X_bands_*`; shapes `(n,14,8,256)`, `(n,4,8,256)`; meta skipped/overlaps); auto guard grows and only masks change; default banks follow config, explicit wins; per_window meta `legacy: true`, `data_source`, console label; missing `filter_bank` key raises; C-1 (v1 keeps its Mean row, `v3` has none and MEAN averages S01, S02 only; fails on the old code because `summary_rows` had no such option).

Runs: `pytest tests/test_p16_* tests/test_p17_windowing.py -o addopts=""`: P16 + P17 all pass (the P16 freeze test needed the stub signature, above).
Full suite (`pytest tests/ -q -o addopts=""`, log mas/state/scratch/p17_suite_ds.log): `1112 passed, 21 warnings in 592.87s (0:09:52)`

## Smoke (S03, one subject, `--out-root mas/state/scratch/p17_ds`, deleted afterwards)

`fs 256, 154896 samples, 320 windows, 120 trial ids; valid 310 (no guard 313); guard 1.047 s, artifact blocks 14`; PO7 dropped. Skipped: `bands skipped S03 harmonic: 60 Hz [59, 61] (contains excluded 60 Hz)`; intermediate none. Files saved 15 (13 of P16 + 2 new), `X_bands_harmonic (320, 14, 8, 256)`, `X_bands_intermediate (320, 4, 8, 256)`, 0.7 s. Not compared with P16 data (generated folders are not read); the verifier hashes.

## For the ml-engineer

- Bank names: `fbcca`, `fbcsp`, `harmonic`, `intermediate`; files `X_bands_<bank>.npy`, layout `(window, band, channel, time)`.
- Band order in meta (`windows_meta.json["bands"][bank]`, list of `{name, low, high}`) is the column order of the array; `harmonic` has 14 (60 Hz removed), `intermediate` 4. `--bank harm` = fbcsp + harmonic, `harm+mid` = + intermediate, concatenated in that order.
- `bands_skipped[bank]` lists `{center, low, high, why}`; code must take band counts from the array / meta, never 15.
- Valid windows are those of `valid_mask` of the `_p17` root (guard 1.047 s).

## R11 consultations

None (reference code not opened).
