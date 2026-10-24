# P03 · 03 · Changes — signal-processing

Status: READY
Author: signal-processing
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/state/decisions.md (P02, P03 rows), mas/01_DATA_SPEC.md §5.1, §6, mas/02_REQUIREMENTS.md §4, §5.4, mas/05_PITFALLS.md PF-04/06/07/09
Branch: phase/P03-exploration (from main @ df229bd)
Commit(s): 44e87e7 (bookkeeping), e788ee9, 8b2c493, 320faa0, b8cb194, 0512094 (HEAD)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/ssvep/spectral_power.py` | NEW | importable helpers: `LEGACY_FS_HZ = 250` (legacy), `fs_label`, `select_channels_by_name` (fails if names ≠ channel axis), `fft_power` (`|rfft|²`, axis `rfftfreq(T, 1/fs)`), `band_mask`, `mean_spectrum`, `spectrum_peaks` (max in band, bin nearest h·f0, band median), `psd_features` (periodogram, P02 layout) | P03.1, P03.2 | [1], [2], [3], [own] (DFT definitions) |
| `src/visualization/signal_plots.py` | MODIFIED | + `plot_class_spectra_panels` (one panel per class, f0 solid, 2f0 dotted), + `plot_psd_by_class_per_channel` (one panel per channel, one line per class); P02 functions untouched; same palette | P03.1, P03.2 | [2], [own] |
| `scripts/exploration/diagnose_occipital_spectra.py` | NEW | P03.1 script; also hosts the shared `load_config`, `load_legacy_windows` (per-subject folder only, length check), `discover_subjects`, `header_fs`, `figure_path`, `occipital_class_spectra`, `format_peaks` | P03.1 | [2], [3], PF-09 |
| `scripts/exploration/visualize_data.py` | NEW | P03.2 script: `quality_mask` (`validate_eeg_windows`, 4 thresholds explicit; rejected per label and reason), stimulus selection, `FEATURE_BLOCKS = {"psd": psd_block}` with marked P05 extension points, `explore_subject`, saved-PSD consistency check | P03.2 | [2], R5, PF-07 |
| `Makefile` | MODIFIED | `explore` target (both scripts `--all`, default legacy fs) | — | [own] |
| `tests/test_p03_exploration_smoke.py` | NEW | 8 builder smoke tests on synthetic arrays in `tmp_path` | — | [own] |

## Legacy behaviour implemented

- `fs250` (PF-04, `02_REQUIREMENTS` §5.4, decisions.md P03 Q1): both scripts default
  to `--fs 250`, constant `LEGACY_FS_HZ` labelled `# legacy:`; console and every
  figure title say `fs=250 (legacy)`. `--fs 256` gives `fs=256 (header)`. The
  header value is not a literal: it is derived per subject as samples per window /
  `preprocessing.sub_window_sec` (256 / 1.0, §5.1) and printed as `header fs`.
  Any other value is labelled `(override)`.
- Per-script quality mask (R5 LEGACY before P16): `visualize_data.py` calls
  `validate_eeg_windows` with `vpp_min=0.5` (legacy constant `LEGACY_VPP_MIN_UV`, no
  config key, PF-07), `vpp_max` = `preprocessing.vpp_thresh_uv` (200), `std_min/max`
  = `preprocessing.std_range` (0.5, 60); each overridable (`--vpp-min`, `--vpp-max`,
  `--std-min`, `--std-max`) and printed. Expected to reject 0 windows (Q2).
- 7 channels from config v1 `channels.scalp` (PF-05); never hard-coded.

Note for the reviewer (PF-04 consequence, not a bug): under fs 250 the "bin nearest
the target" for 101 is bin 25 (24.41 Hz), while a 24 Hz response sits in bin 24
(labelled 23.44 Hz). The printed target-bin power at fs 250 therefore misses the
24 Hz response; the band maximum line shows where the power is. Seen in the
synthetic smoke run (101: max at 23.438 Hz bin 24; nearest-target bin 25, ×1.13
median). Other targets are nearest to their own bin at fs 250 (20→bin 20, 15→15,
10.91→11, 8.57→9). Compare with the `--fs 256` run.

## Differences from the cited examples

None copied. `fft_power` is plain `numpy.fft.rfft` power (no window, no scaling),
as the plan specifies; `psd_features` reuses the P02 periodogram call
(`scipy.signal.periodogram` defaults) so that at fs 256 it reproduces the saved
`X_psd_features` (smoke: max |computed − saved| = 0).

## Deviations from the plan

1. Two files beyond the work split: NEW `src/features/ssvep/spectral_power.py` and
   MODIFIED `src/visualization/signal_plots.py`, so the tester can import the
   computation and plotting without the scripts' CLI (task message allowed it).
   `visualize_data.py` imports the loader/config helpers from
   `diagnose_occipital_spectra.py` instead of duplicating them.
2. Figure-name suffix flag is `--out-suffix <s>` (file `<stem>_<s>.png`), on both
   scripts, as named in the plan's run line.
3. Additional console output beyond the plan: band median power, the 2f0 nearest bin
   (when inside 5–35 Hz) and the ratio to the band median, per class; the reviewer
   records f0, 2f0 and alpha separately (plan risk table).
4. `visualize_data.py --features` (choices from `FEATURE_BLOCKS`, P03: `psd` only).

## How to run / reproduce

Runner (plan "Run commands", flags final):

```bash
.venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --all
.venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --all --fs 256 --out-suffix header
.venv/bin/python -m scripts.exploration.visualize_data --all
```

Outputs per subject: `outputs/figures/exploration/<S>/occipital_spectra.png`,
`occipital_spectra_header.png`, `psd_features_by_class.png`. Optional (not in the
plan): `visualize_data --all --fs 256 --out-suffix header` also checks the
recomputed PSD against the saved `X_psd_features` (expected max diff 0).
`make explore` runs lines 1 and 3. Overrides for tests/verifier:
`--processed-dir <dir>` (expects `<dir>/<S>/{X_time_windows,y_labels[,X_psd_features]}.npy`),
`--figures-dir <dir>` (figures under `<dir>/exploration/<S>/`), `--config`,
`--no-figures`. Exit code 1 if no subject was plotted.

## How I verified

- `.venv/bin/python -m pytest tests/ -q` → `291 passed in 13.21s` (8 new in
  `tests/test_p03_exploration_smoke.py`: legacy fs label of a 24 Hz sinusoid
  (bin 24 = 23.4375 Hz), name selection and count check, `fs_label`, PSD widths
  217/210, per-class peaks with a reversed name list, mask rejected-count per label
  and reason, both scripts end-to-end with a skip line, length mismatch fails).
- Smoke runs on a synthetic legacy tree in `mas/state/scratch/P03_smoke/`
  (S03 with 2 planted `vpp_high` rows, S04; planted 24/20/15/11/9 Hz on O1/Oz/O2,
  30 Hz on 201/202): both scripts run as module and as file; fs 250: maxima at
  23.438/19.531/14.648/10.742/8.789 Hz (bins 24/20/15/11/9); fs 256: max |computed −
  saved PSD| = 0; mask `kept 60/62, rejected 2`, `103: ... vpp_high 2`; figures
  opened and checked visually (panels, target lines, titles with fs label and data
  source). No real data read or run.

## Left to do / known limitations

- Known-answer suite (plan "Tests required") is the synthetic-tester's.
- FBCCA/FBCSP blocks: P05 (extension points marked in `visualize_data.py`).
- Stale figures of a subject skipped in a later run are not removed (as P02).

## Reference consultations (R11)

None.

## Sources

1. RULE — `mas/05_PITFALLS.md` PF-04, PF-06, PF-07, PF-09; `mas/RULES.md` R5, R9.
2. REQUEST — `mas/state/phases/P03-exploration/02_plan.md` work split and Q1/Q2; `mas/03_ROADMAP.md` P03 tasks 1–2.
3. RULE — `mas/01_DATA_SPEC.md` §5.1 (256-sample windows, layout), §6 (occipital set `O1, Oz, O2`, names not positions).
4. RULE — `mas/02_REQUIREMENTS.md` §4 (CLI, skip line, Agg), §5.4 (fs 250 in Era A).

## Questions

ACK 02_plan.md signal-processing 2026-10-24
