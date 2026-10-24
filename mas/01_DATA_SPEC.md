# 01 — Data and format specification

Everything here was measured on the actual delivered files. Where something is
unknown, it says so; do not fill gaps with assumptions — open a blocker instead.

## 1. Delivery and layout

The human operator places the recordings in the working copy (never in git):

```
data/raw/
  S01/  OO.ebr  mOO.ebr  C.ebr  mC.ebr
  S02/  OO.ebr  mOO.ebr  C.ebr  mC.ebr  online_C.ebr   (+ photos .jpg, video .mp4)
  S03/  OO.ebr  mOO.ebr  C.ebr  mC.ebr  cb_mas_mcb.ebr (+ photos .jpg, video .mp4)
  S04/  OO.ebr  mOO.ebr  C.ebr  mC.ebr                 (+ photos .jpg, video .mp4)
  S05/  OO.ebr  mOO.ebr  C.ebr  mC.ebr  online_OO.ebr  (+ photos .jpg)
```

- Subject folders match the regex `^S\d+$`. **Code must discover subjects by that
  pattern**, never by a hard-coded list: the cohort is planned to grow to about
  40–45 subjects.
- Photos and videos document the recording sessions (electrode placement). They are
  not inputs to any analysis; code must ignore non-`.ebr` files.
- The main analysis session is **`OO.ebr`** (default `--session OO`). `mOO` is the
  default *test* run for the pseudo-online detector (P20). `C`/`mC` are used only
  where a phase says so.
- Literature PDFs (8 papers, including the reference paper) may be delivered for
  context. They are copyrighted: keep them out of git (e.g. `docs/literature/`,
  git-ignored).

## 2. The `.ebr` binary format ("EBR binary 1.0")

An ASCII header of `\n`-terminated lines, then a raw little-endian binary block.

```
ebr binary 1.0                  <- magic, compare case-insensitively after strip
data_type double                <- element type of the binary block
sampling_rate 256               <- Hz (float)
samples 154896                  <- ns, samples per channel
bands 1                         <- nb
band_1 Raw Data                 <- band_<k> <name>, 1-based
channels 11                     <- nc
channel_1 PO7                   <- channel_<k> <name>, 1-based
...
channel_11 MARK
trials 1                        <- nt
trial_1 EEG Register            <- trial_<k> <name>
comments 1
comment_1 Sample selection      <- comment_<k> <text>
marks 0                         <- nmarks; when >0, lines "mark_<k> <sample_index> <label>"
end_header                      <- binary data starts right after this line
```

Rules for the parser:

- Blank header lines are skipped. Unknown keys are ignored.
- Binary block size is `nt * nc * nb * ns` elements, read with the dtype below, then
  reshaped to **`(nt, nc, nb, ns)`** (C order). Real numeric types are cast to
  `float64`.
- Supported `data_type` strings → numpy dtype (bytes):
  `int8`/`char`→int8(1), `uint8`/`unsigned char`→uint8(1), `int16`/`short`→int16(2),
  `uint16`/`unsigned short`→uint16(2), `int32`/`int`→int32(4),
  `uint32`/`unsigned int`→uint32(4), `int64`/`__int64`→int64(8),
  `uint64`/`unsigned __int64`→uint64(8), `float`→float32(4), `double`→float64(8),
  `complex`/`class std::complex<double>`→complex128(16, not cast).
  Any other value raises `ValueError`.
- Every delivered file has `nt=1`, `nb=1`, `data_type double`. The continuous
  signal of channel `c` is `data[0, c, 0, :]`.
- The parser returns a dict with: `data_type, sampling_rate, number_of_trials,
  trials, number_of_channels, channels, number_of_bands, bands, number_of_samples,
  number_of_comments, comments, number_of_marks, marks, data`.

Header facts observed in all 23 files: `sampling_rate 256`, 11 channels in this order:

| idx | name | role |
|---|---|---|
| 0–7 | `PO7, PO3, POz, PO4, PO8, O1, Oz, O2` | scalp EEG (assumed µV) |
| 8 | `TIMESTAMP` | wall-clock time in ms since Unix epoch (≈1.637e12, recordings from Oct–Nov 2021) |
| 9 | `FLASHINGTIME` | stimulus-display timing value, small positive floats (~0.004–0.007); unused by the pipeline |
| 10 | `MARK` | event codes (section 3) |

`cb_mas_mcb.ebr` (S03 only) has a second comment `Data Manipulation - Join
Time-Series`: it is the concatenation of two runs (it starts at the same wall-clock
time as S03 `C.ebr` and is twice as long). Never use it together with the runs it
contains; no phase requires it.

## 3. Event protocol (MARK channel)

The MARK channel is 0 except for **single-sample pulses** carrying an event code.
An event onset is a sample where MARK equals the code and differs from the previous
sample (`(mark == code) & (diff(mark, prepend=0) != 0)`).

Codes in the calibration runs (OO, mOO, C, mC):

| Code | Meaning | Segment that follows the pulse |
|---|---|---|
| 201 | fixation cross (no stimulus) — the **rest / no-stimulus baseline** | 2.0 s |
| 202 | cue: target presentation | 2.0 s |
| 203 | preparation | 1.0 s |
| 101 | SSVEP stimulus, target 1 — **24.0 Hz** | 5.0 s |
| 102 | SSVEP stimulus, target 2 — **20.0 Hz** | 5.0 s |
| 103 | SSVEP stimulus, target 3 — **15.0 Hz** | 5.0 s |
| 104 | SSVEP stimulus, target 4 — **10.9091 Hz** (= 120/11) | 5.0 s |
| 105 | SSVEP stimulus, target 5 — **8.5714 Hz** (= 60/7) | 5.0 s |
| 200 | end of stimulation / inter-trial rest | 5.0 s |

One trial lasts 15 s: `201 (t) → 202 (t+2) → 203 (t+4) → 10x (t+5) → 200 (t+10) →
next 201 (t+15)`. The first 201 is at 5.0 s. Each run has **40 trials = 8 per target,
in randomized order**, for ≈605 s and ≈154,900 samples. Observed onset counts per
run: `201: 40, 202: 40, 203: 40, 200: 40, 101–105: 8 each`. Onset jitter is ≤ 0.04 s.

Online runs (`online_C.ebr` 117.5 s, `online_OO.ebr` 65.3 s) contain only codes
**1001–1005** (online-mode targets 1–5, 9 and 7 events respectively) and no
fixation/cue codes. No phase uses them; keep them parseable.

Paradigms: **OO = On-Off** flicker, **C = Checkerboard** (pattern reversal; its
response is expected at **twice** the stimulation frequency, so OO-trained models are
not expected to transfer to C). The meaning of the `m` prefix (mOO, mC) is not
documented in the project; treat each as a second run of the same paradigm. The
reference paper for the paradigms is Chailloux Peguero et al. (2023), *SSVEP
detection assessment by combining visual stimuli paradigms and no-training detection
methods*, Frontiers in Neuroscience 17:1142892.

## 4. Recording inventory (measured)

| Subj | File | Samples | Duration | Stim events | Session start (UTC) | 99th pct of abs(EEG), µV |
|---|---|---|---|---|---|---|
| S01 | mC | 154,896 | 605.1 s | 40 | 2021-10-28 21:34 | 138.6 |
| S01 | mOO | 154,912 | 605.1 s | 40 | 2021-10-28 21:47 | 187.6 |
| S01 | OO | 154,904 | 605.1 s | 40 | 2021-10-28 21:57 | 785.1 |
| S01 | C | 154,896 | 605.1 s | 40 | 2021-10-28 22:09 | 424.2 |
| S02 | OO | 154,912 | 605.1 s | 40 | 2021-11-18 17:45 | 40.1 |
| S02 | mC | 154,904 | 605.1 s | 40 | 2021-11-18 18:04 | 35.9 |
| S02 | mOO | 154,912 | 605.1 s | 40 | 2021-11-18 18:20 | 37.5 |
| S02 | C | 154,896 | 605.1 s | 40 | 2021-11-18 18:35 | 37.2 |
| S02 | online_C | 30,088 | 117.5 s | 9 (100x) | 2021-11-18 18:47 | 35.1 |
| S03 | mC | 154,896 | 605.1 s | 40 | 2021-11-20 00:21 | 43.0 |
| S03 | OO | 154,896 | 605.1 s | 40 | 2021-11-20 00:36 | 331.4 |
| S03 | mOO | 154,896 | 605.1 s | 40 | 2021-11-20 00:51 | 1013.8 |
| S03 | C | 154,920 | 605.2 s | 40 | 2021-11-20 01:06 | 864.0 |
| S03 | cb_mas_mcb | 309,816 | 1210.2 s | 80 | 2021-11-20 01:06 | 658.6 |
| S04 | mOO | 154,912 | 605.1 s | 40 | 2021-11-25 00:47 | 24.9 |
| S04 | C | 154,896 | 605.1 s | 40 | 2021-11-25 01:01 | 90.8 |
| S04 | OO | 154,896 | 605.1 s | 40 | 2021-11-25 01:23 | 481.5 |
| S04 | mC | 154,896 | 605.1 s | 40 | 2021-11-25 01:36 | 1063.0 |
| S05 | C | 154,904 | 605.1 s | 40 | 2021-11-26 16:01 | 23.5 |
| S05 | mC | 154,896 | 605.1 s | 40 | 2021-11-26 16:16 | 24.8 |
| S05 | mOO | 154,904 | 605.1 s | 40 | 2021-11-26 16:30 | 23.8 |
| S05 | OO | 154,912 | 605.1 s | 40 | 2021-11-26 16:42 | 24.6 |
| S05 | online_OO | 16,728 | 65.3 s | 7 (100x) | 2021-11-26 16:55 | 33.0 |

The raw signal is unfiltered with large slow drifts and artifacts (several runs reach
±1,000–5,800 µV). **Quality decisions must always be made on filtered signals** (and,
from P19, optionally also on raw windows cut at the same positions).

> Phase P00 must reproduce this table from the files with a script
> (`scripts/exploration/inventory_raw.py`) and fail loudly if any file deviates
> (different channel list, sampling rate, event counts).

## 5. Analysis windows (what every later phase consumes)

Two generations of windowing exist; both must be reproducible.

### 5.1 Legacy windows (phases P02–P15)

Produced by `scripts/preprocessing/run_preprocessing.py`, per subject, from `OO.ebr`:

- Continuous broadband filter on the scalp channels, then cut **1.0 s sub-windows of
  `int(1.0 * fs)` = 256 samples**.
- Segments per condition: **202** = 1 window, the second *before* each 202 onset
  (`cue_lookback_sec = 1.0`; note this second lies inside the fixation period);
  **101–105** = the 5.0 s after the onset → 5 sub-windows; **201** = the 2.0 s after
  the onset → 2 sub-windows. A stimulus trial is kept only if all 5 s fit in the
  recording.
- A raw sub-window gate removes windows before saving (legacy limits in P02).
- Saved arrays, ordered **by condition** in the order `201, 202, 101, 102, 103, 104,
  105`, each condition's windows in time order:
  - `X_time_windows.npy` — `(n_windows, 7, 256)` float64 (PO7 excluded in the legacy
    config; becomes 8 channels after P07)
  - `X_psd_features.npy` — `(n_windows, 7 * 31)` = 217: periodogram, 5–35 Hz
    inclusive (31 one-hertz bins), flattened channel-major
  - `y_labels.npy` — `(n_windows,)` int64 condition codes
- With nothing rejected a subject has **320 windows = 80 (201) + 40 (202) + 200
  (101–105)**. Observed legacy counts: 317–320.
- Legacy folders do **not** store trial ids; trial ids are reconstructed from
  contiguous same-label blocks (P11). That reconstruction is *approximate* when the
  raw gate removed a window from the middle of a block — code must report it.

### 5.2 Built windows (phases P16 onward)

Produced by `scripts/build_windows.py` into
`data/processed_<filter_mode>[/w<len>_s<stride>]/<subject>/`:

| File | Shape / type | Content |
|---|---|---|
| `X_time_windows.npy` | `(n, 8, n_samples)` float64 | broadband-filtered windows, all 8 channels |
| `X_raw_windows.npy` | `(n, 8, n_samples)` | unfiltered windows at the same starts |
| `X_bands_<bank>.npy` | `(n, n_bands, 8, n_samples)` | filter-bank sub-bands, `<bank>` ∈ `fbcca, fbcsp, harmonic, intermediate` |
| `y_labels.npy` | `(n,)` int64 | condition codes |
| `trial_ids.npy` | `(n,)` int64 | **true** trial id (one per event segment) |
| `window_starts.npy` | `(n,)` int64 | start sample in the continuous recording |
| `sub_idx.npy` | `(n,)` int64 | position of the window inside its segment (0, 1, …) |
| `window_offsets.npy` | `(n,)` int64 | samples from segment onset to window start |
| `valid_mask.npy` | `(n,)` int8 | shared quality decision (1 = keep) |
| `valid_mask_no_guard.npy` | `(n,)` int8 | same decision without the artifact guard |
| `reject_reason.npy` | `(n,)` int8 | 0 valid, 1 failed own Vpp/std gate, 2 within guard of an artifact, 3 failed raw Vpp/std gate |
| `windows_meta.json` | JSON | fs, channels, window/stride, windows per trial, filters, bands, skipped bands, overlaps, label counts, n_trials, full quality decision (channels kept/dropped, fail fractions, guard, artifact fraction, rejections by label and reason, params) |

All analyses after P16 read these files through one loader
(`src/io/subject_data.py::load_subject`) so that every analysis uses **the same
windows and the same channels**.

## 6. Condition and class conventions

- Class order everywhere: `101, 102, 103, 104, 105` (24, 20, 15, 10.9091, 8.5714 Hz).
  Probability columns are named `p_101 … p_105`.
- 5-class problems use stimulus windows only; chance = 20 %.
- The **6-class** problem (P17) adds 201 as a "rest" class; chance = 16.67 %; 6-class
  LDA uses uniform priors.
- Connectivity baselines always use **201** (fixation), never 202.
- Channel names, not positions, identify channels. Any subset is resolved by name:
  - visual cluster for the feature benchmarks' harmonic PSD = `PO8, O1, Oz, O2`
    (the legacy positional `[3,4,5,6]` was right for the 7-channel layout and silently
    wrong — `PO4, PO8, O1, Oz` — once PO7 was restored as channel 0);
  - the early hybrid/XAI scripts (P04) use `POz, O1, Oz, O2` (positions `(1,4,5,6)` of
    the 7-channel layout);
  - occipital set for power/alpha checks = `O1, Oz, O2`.
