# P13 · 00 · Assignment — Phase and autoregressive connectivity with permutation statistics

Status: READY
Author: orchestrator
Branch: phase/P13-phase-pdc-permutations (from main @ fa9d663, tag p12-done)
Era: B. Enforced from this phase: **R3 for phase** (phase from the cross-spectral density; filtfilt + Hilbert on short windows only as the PF-18 bug demo) and **R7** (honest statistics, with trial-level permutations as the final unit). Legacy behaviours required (`team.yaml`, era matrix): **R7-first-run**, meaning the first cohort run uses window-level permutations and is recorded and labelled; **fs250** in features (PF-04, labelled). The MVAR contiguous slicing (R6) is allowed only inside the PF-17 bug diagnostic. The per-script P07 gate (R5 from P16) continues as one shared gate per subject (P12 settled point 1). R4 is enforced: coherence is the concatenated condition estimator.
Owners (agents): connectivity-stats (Connectivity & Stats); scientific-reviewer; verifier
Depends on: P12 (passed; merged fa9d663)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** PLV/wPLI, PDC and a permutation + Benjamini-Hochberg framework were added;
a correctness review found two implementation bugs; the cohort script had a display
bug; permutations were later moved from window level to trial level.
**Depends on:** P12. **Owners:** Connectivity & Stats, Scientific Reviewer, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. Phase connectivity from the **cross-spectral density**, not time-domain Hilbert:
   `compute_phase_connectivity(windows, fs, band, metric, nperseg=min(T,128))` — per
   window one band-averaged complex CSD value per pair (`scipy.signal.csd`); PLV =
   `|mean(exp(i·angle))|`; wPLI = `|mean(Im)| / mean(|Im|)` (0 if the denominator
   is 0). `compute_condition_plv`, `compute_condition_wpli`.
   **Reproduce the bug first**: a filtfilt + Hilbert implementation on 256-sample
   windows with a ±1 Hz band has amplitude envelopes at 5–70 % of truth in the first/last
   ~15 samples and unstable instantaneous frequency; padding/order/bandwidth do not fix
   it; the CSD version is unchanged (0.998 → 0.998) when edge samples are corrupted.
2. PDC: `fit_mvar_ols(windows, p=10)` — design matrix rows from each window without
   crossing window boundaries, columns **channel-major** (`window[:, t-p:t][:, ::-1]`
   flattened), ridge `1e-4·tr(G)/dim`; coefficients per lag = `weights[lag::p, :].T`
   (**strided**, PF-17); `compute_condition_pdc(windows, fs, band, order=10)`:
   15 frequencies across the band, `A(f) = I − Σ_l A_l e^{−2πi f l/fs}`, column-normalized
   magnitude, zero diagonal, averaged; entry `[i, j]` = flow j → i.
   **Reproduce the bug first**: contiguous slicing `weights[lag*C:(lag+1)*C]` gives
   ~150–200 % coefficient error on an identifiable synthetic VAR; strided gives ~5–10 %.
3. Permutation test `compute_permutation_test(stim, base, band, fs, n_permutations=200,
   method_fn, n_jobs=-1, random_state=42, alpha=0.05, stim_trial_ids=None,
   baseline_trial_ids=None)`: observed diff matrix; pool windows; per permutation
   split into groups with the **observed group sizes**; with trial ids, permute whole
   trials (`_trial_permutation_split`: greedy fill in random trial order, at most one
   trial split to match the count exactly); global statistic = mean upper-triangle
   difference, one- and two-tailed p with +1 pseudo-count, null mean/std/95 % CI;
   edge p-values one/two-tailed; BH-FDR (`benjamini_hochberg`) across the 21/28 edges;
   return `permutation_unit` "trial" or "window".
4. `extract_connectivity_by_condition(windows, y, fs, method_fn, conditions,
   channel_names, limits…, n_permutations=0, trial_ids=None, quality=None)`: one
   shared quality gate for all conditions, then by-condition matrices, matched baseline,
   differences, optional permutation tests per frequency.
5. `scripts/connectivity/analysis/analyze_connectivity_cohort.py --methods coherence
   plv wpli pdc --permutations 100|200 --n-jobs -1`: every subject × method; trial ids
   from `build_trial_ids(y, {201: 2, 101..105: 5})`; summary CSV (§6 schema) and
   per-subject edge files `reports/connectivity_edges/<S>_<method>.npz`; console
   reports **both** criteria separately: (A) subjects with ≥1 FDR edge, (B) subjects
   with global p < α — never one merged star (PF-20).
6. Run first with window-level permutations (record), then trial-level (final).

## Run (verbatim)

Task 6. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`analyze_connectivity_cohort.py`, `reports/connectivity_cohort_summary.csv`, `reports/connectivity_edges/<S>_<method>.npz`

## Acceptance (verbatim)

Acceptance: synthetic tests (MVAR recovery, edge immunity, trial split sizes);
cohort result = **R-12** (S01/S02 null on essentially everything; 24 Hz the only
frequency robust across S03–S05 in both coherence and wPLI; FDR edge totals per
subject coherence 0/0/65/51/15, wPLI 0/3/38/33/18 at 200 trial-level permutations
within tolerance); borderline cells that flip between 100 and 200 permutations are
listed as inconclusive.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| PF-17 | mas/05_PITFALLS.md | strided MVAR coefficients; contiguous slicing only in the bug demo |
| PF-18 | mas/05_PITFALLS.md | phase from the CSD; Hilbert only in the bug demo |
| PF-19 | mas/05_PITFALLS.md | trial-level permutations with the observed group sizes; window-level is the recorded first run |
| PF-20 | mas/05_PITFALLS.md | criteria (A) FDR edges and (B) global p reported separately |
| PF-03 | mas/05_PITFALLS.md | trial ids on pre-gate labels, then the gate mask; S02/S04 approximate (P11 D-2) |
| PF-04 | mas/05_PITFALLS.md | fs 250 legacy axis |
| R-12 | mas/04_REFERENCE_RESULTS.md | global p and FDR edges; tolerance "Permutation statistics": same qualitative pattern; FDR totals per subject within ±25 % or ±5 edges; a 24 Hz effect/no-effect switch must be explained |
| R3, R4, R6, R7 | mas/RULES.md | phase via CSD; concatenated coherence; layouts proven; honest statistics |
| decisions.md P12 | | one shared gate; D-2: re-check the junction bias when permuted windows are re-concatenated; D-3: test both alpha hypotheses; D-4: shared colour limits across subjects or say not |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| connectivity-stats | P13.1–P13.5 (+ bug demos) | `03_changes_connectivity-stats.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | P13.6 runs + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P13.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
