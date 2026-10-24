# P03 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/01_DATA_SPEC.md §5.1, §6, mas/02_REQUIREMENTS.md §4, §5.4, mas/05_PITFALLS.md PF-04/06/09, P02 rows of mas/state/decisions.md
Approved by Sebastian: [x]   Date:2026-10-24        (required only if PLAN_APPROVAL: required)

## Goal

Two exploration scripts that show, per subject and per class, whether the legacy
stimulus windows carry SSVEP peaks at the target frequencies, before any model is
trained.

## Data source

Legacy folders `data/processed/<S>/{X_time_windows,y_labels,X_psd_features}.npy`
from P02 (OO, 7 channels, 256 samples per window), S01–S05 discovered. No raw
data is read. fs: legacy 250 Hz assumed (Q1), header value 256 reachable by flag.

## Scope

**In:** P03.1, P03.2 (PSD features only; FBCCA/FBCSP hooks left for P05), figures;
P03.3 is written by the scribe from the reviewer's findings.

**Out:** FBCCA, FBCSP (P05), any model, any change to P02 arrays.

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| signal-processing | NEW `scripts/exploration/diagnose_occipital_spectra.py` | per subject: stimulus windows (101–105), occipital channels `O1, Oz, O2` by name, FFT power (`|rfft|²` of each 256-sample window, mean over windows and the three channels), 5–35 Hz, one panel per class with the target frequency marked; `--subject`, `--all`, `--subjects`, `--fs` (default legacy 250, Q1), figures under `outputs/figures/exploration/<S>/occipital_spectra.png`; prints per class the frequency of the maximum in 5–35 Hz and the power at the bin nearest the target | P03.1 | [2] P03.1, [3] §6 |
| signal-processing | NEW `scripts/exploration/visualize_data.py` | `--subject` (default S03), `--all`, `--subjects`; load windows, run `validate_eeg_windows` with every threshold passed explicitly (Q2), select stimulus windows, compute periodogram PSD features (5–35 Hz, same layout as P02), plot per-class mean PSD per channel, `outputs/figures/exploration/<S>/psd_features_by_class.png`; prints windows kept/rejected by the mask and per-class counts; a clearly marked extension point for FBCCA/FBCSP (P05) | P03.2 | [2] P03.2 |
| signal-processing | MODIFIED `Makefile` | `explore` target running both with `--all` | — | [own] |

Both scripts: matplotlib Agg, figures saved, never shown; channel names from config
v1 `channels.scalp`, failing loudly if their count differs from the array's channel
axis; `[-] Skipping <S>: <reason>` for a subject without arrays; the fs in use
printed and written into each figure title (`fs=250 (legacy)` or `fs=256 (header)`).

## Legacy behaviour in this phase

`fs250`: frequency axes computed with fs = 250 by default, labelled `legacy` in the
console and figure titles. Reachable afterwards via the default; the corrected value
via `--fs 256` (P16 makes header fs the only source). Per-script quality mask (R5
legacy before P16), thresholds explicit. 7 channels (config v1).

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| PF-04 | 250/256 shift misread as "no peak" or silently mixed with 256 | fs printed and in titles; the reviewer judges peaks knowing the legacy shift; both modes run (Q1) |
| PF-06 | occipital set by position (the 7-channel layout puts O1, Oz, O2 at 4, 5, 6) | lookup by name; test with a reordered name list |
| PF-09 | root arrays read instead of `<S>/` | per-subject paths only; length check |
| R5 | inherited defaults in the mask | thresholds explicit, printed |
| R9 | cohort-only statement | one figure and one console block per subject |
| Interpretation | a peak at an alpha frequency read as SSVEP (P02: S01 101 → 10 Hz) | reviewer records f0, 2f0 and alpha separately; no tuning |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source of the answer |
|---|---|---|---|---|
| FFT power peak | 256-sample windows, 15 Hz sinusoid sampled at 256 Hz, analysed with fs 256 | maximum at the 15 Hz bin | exact bin | DFT, [own] |
| legacy fs shift | 24 Hz sinusoid sampled at 256 Hz, analysed with fs 250 | maximum at bin 24, labelled 24 × 250/256 = 23.4375 Hz | 1e-9 | PF-04 |
| occipital by name | 7-channel array where only the channels named O1, Oz, O2 carry a sinusoid; name list reordered | spectrum shows the sinusoid; with positions instead of names it would not | exact | PF-06 |
| per class panels | synthetic legacy folder, 5 stimulus classes with distinct planted frequencies, plus 201/202 rows | 5 panels; each class's maximum at its planted frequency; 201/202 rows excluded | exact | [2] P03.1 |
| quality mask | windows with one out-of-range channel | rejected count = planted count; thresholds as passed | exact | [2] P03.2 |
| PSD features layout | as P02 (5–35 Hz, 31 bins at fs 256; 30 at fs 250) | shapes `(n, 217)` / `(n, 210)` | exact | P02, PF-04 |
| channel-count check | names list of 8 for a 7-channel array | fails loudly | — | [own] |
| script smoke | synthetic `data/processed/S0x/` tree via a path override | figures written, skip line for a missing subject | — | [own] |

## Run commands (for the runner)

```bash
.venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --all
.venv/bin/python -m scripts.exploration.diagnose_occipital_spectra --all --fs 256 --out-suffix header
.venv/bin/python -m scripts.exploration.visualize_data --all
```

(The second line is for comparison only; the flag names are fixed by the builder
and copied into `05_run.md`.) Expected runtime: < 1 min, CPU. Over
`LOCAL_RUN_BUDGET_MIN`? no. Logs `reports/logs/P03/<script>_<timestamp>.log`.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| figures exist | every expected PNG present and non-empty, per subject | — |
| the Reviewer confirms visible fundamental peaks for the strong responders and records what is seen for S01/S02 | reviewer opens the figures (results review); the verifier re-runs and tabulates the printed per-class maximum and target-bin power per subject | P02 observations (decisions.md) |

## Sources

1. `mas/02_REQUIREMENTS.md` §4, §5.4 (opened in this run).
2. `mas/03_ROADMAP.md` P03 (opened in this run).
3. `mas/01_DATA_SPEC.md` §5.1, §6 (opened in this run).
4. `mas/05_PITFALLS.md` PF-04, PF-06, PF-09 (opened in this run).

## Questions

Q1 (fs). Era A assumes 250 Hz in feature code (`02_REQUIREMENTS` §5.4) and
`team.yaml` lists `fs250` for P03; the legacy arrays store no fs, so a hard-coded 250
is the likely original. That moves every peak down by 2.3 % (24 → 23.44 Hz), so
it lands about half a bin left of a target line drawn at 24 Hz.
Default: 250 Hz (legacy, labelled), and the runner also runs the occipital script
once with `--fs 256` for comparison. Alternative: use 256 now and record P03 as
not reproducing the legacy axis.

Q2 (quality mask). P02 already gated the windows with the legacy limits (vpp ≤ 200,
std 0.5–60, vpp_min 0.5). The roadmap says "run the quality mask" again; it does not
say with which thresholds. Default: the same legacy limits, passed explicitly (so
the mask should reject 0 windows and acts as a check). Alternative: the shared
defaults of `validate_eeg_windows` (5–120 µV, std 1–35), which would reject more.
