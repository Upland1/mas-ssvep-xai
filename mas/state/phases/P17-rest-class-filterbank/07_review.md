# P17 · 07 · Scientific review

Status: READY (pre-run audit PASS; results review APPROVE)
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Audited at `a1e49e4` (`git diff main..HEAD`, 23 files). The six P17 test files plus the two edited P16 files run here:
`.venv/bin/python -m pytest tests/test_p17_windowing.py tests/test_p17_benchmark.py tests/test_p17_independent_known_answer.py tests/test_p17_leak_controls.py tests/test_p16_freeze_baseline.py tests/test_p16_independent_known_answer.py -q -o addopts=""` -> `127 passed, 1 warning in 82.68s`.
Era C: no legacy behaviour is prescribed for P17, so every violation would be FAIL; none found. The verdict
holds only if the run-list additions below are made (they add commands, no code).

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | PASS | `scripts/benchmarks/feature_based/benchmark_n_subjects.py:199` groups = `cv_groups`; `:204` `assert_no_shared_trials` every repeat; `:299` 6 classes: no 202 rows and `cv_groups == trial_ids`. Rest (201) segments carry their own trial ids, disjoint from the stimulus ids (`04_tests.md`, `independent::test_six_classes_use_201_only...`). A 201 window and the stimulus windows of the same 15 s trial can fall in different folds; they are different classes and 3 s apart (D1 below checks the real gap) |
| R2 Fit only in-fold | PASS | CSP fitted on `subbands[tr]` only, `src/models/classical/legacy_eval.py:95`; scaler in the per-fold Pipeline (`oof_space`); FBCCA has no fit; priors fixed (1/6), not estimated, `benchmark_n_subjects.py:186-191`. Tester's `leaky_csp` mutant gives 60-87 % on a null recording, so this path is sensitive |
| R3 Filter continuous, then window | PASS | narrow bands go through the same `band_windows(broadband, ..., filter_mode)` as the P16 banks, `scripts/build_windows.py:163-166`; the benchmark only reads saved bands, `benchmark_n_subjects.py:171-178` |
| R4 Estimator small-sample bias | N/A | no coherence/PLV estimator |
| R5 Shared quality decision, explicit thresholds | PASS (CONCERN, carry-forward C-b, C-a) | `--quality shared` on built roots: the loader ignores `thresholds` and `channel_fail_fraction` (they feed only the per-script gate, `src/io/subject_data.py:115`, `:162`); `thresholds=None` now raises, `benchmark_n_subjects.py:265`; the CLI passes the config `channel_fail_fraction` 0.5 explicitly (`:394`, `configs/pipeline_config.yaml:35`). The `fail_fraction` default at `:257` is the same pattern C-2 removed for thresholds: ruled below |
| R6 Index layouts verified | PASS | bank concatenation `fbcsp ‖ harmonic ‖ intermediate` on the band axis, count checked against the metadata, `benchmark_n_subjects.py:171-182`; loader slices every bank with the same `sel`/`kept_idx`, `src/io/subject_data.py:194`; tests: 2·f0 tone lands in its own band for all 5 targets (R6), meta order = array order, k-major mutant caught |
| R7 Honest statistics | N/A | no tests of significance; SDs over repeats are descriptive (pre-commit below forbids "significant") |
| R8 Smoothing respects trials | PASS | `smooth_scores(..., trial_ids, "trial")` for both the accuracy and the kept 2.0 s predictions, `benchmark_n_subjects.py:211` and `legacy_eval.accuracies`; rows checked in (trial, offset) order, `src/io/subject_data.py:180`; 201 trials (2 windows) smoothed by the same rule, test `201 smoothing restarts per trial` |
| R9 Per-subject reporting with data source | PASS (CONCERN C-c) | per-subject rows, SD columns, `.meta.txt` header carries bank and the `classes 6: 101-105 + rest 201` line. The console line at `benchmark_n_subjects.py:405` still says "stimulus windows only" in a 6-class run: the scribe takes the data source from `.meta.txt`, not that line |
| R10 Every change and test cites a source that exists and says what is claimed | PASS | handoffs cite §3, §5.7, §6, PF-04/13, DATA_SPEC §3 (spacing of control b), all present |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A | no copied code |
| R11 Reference consulted only after an attempt, every consultation listed | PASS | both handoffs and 04 list none; `mas/state/scratch/reference_access.log` has no 2026-10-28 entry (`grep -c "2026-10-28"` -> 0). Not opened by me |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS (CONCERN C-a) | per_window builds labelled `legacy` in meta and console (C-2). P16 masks remain reachable only with `--banks fbcca fbcsp`: see C-a |
| Tests cover every change; at least one fails on the historical bug | PASS | PF-13 (`rest202` mutant), frequency priors, swapped FalseAct/Missed, notch removal, k-major order, full-data CSP: each caught (`04_tests.md` mutants); C-2 fallback test fails on the old code |
| Changes match 02_plan.md and the roadmap tasks | PASS | P17.1-P17.3, settled points 1-7; the byte-identity route replaced by the `_p17` root under the rule decided before any number (decisions.md P17 row 2) |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS | vendor/co-author scan of `git diff main..HEAD` and of the commit messages main..HEAD: 0 and 0 (pattern built from fragments); no file under data/, no recording, no local tooling file in `git diff --name-only` (0) |

### Points the orchestrator asked to rule on

1. **201-only rest (PF-13, P16 C-5).** Satisfied: the loader is asked for `CLASS_CODES + (201,)` (`:282`), 202 is
   asserted absent (`:299`), and the tester's `rest202` mutant is caught by the 6-class null. Because no 202 is
   selected, `cv_groups == trial_ids` is correct and the P16 overlap twin map is not needed here.
2. **Uniform priors.** `set_params(priors=1/6)` on the LDA (`:191`); the tester spies on fitted `priors_` (all 1/6).
   Uniform priors reduce rest predictions relative to its frequency (rest = 80 of 280 windows, 0.29): this
   pushes errors towards FalseAct and away from Missed. Stated as a design fact for the report.
3. **Metric definitions vs §5.7.** `src/models/classical/rest_metrics.py:35-38`: FalseAct = rest windows predicted
   as any stimulus / rest windows; Missed = stimulus windows predicted as rest / stimulus windows; matches §5.7
   wording exactly. StimCorrect (in §6, defined in the plan) = own-stimulus / stimulus windows. BalAcc = sklearn
   mean per-class recall. Note for the report: the 6-class CSV's `1.0s Acc (%)`/`2.0s Smoothed (%)` are 6-class
   accuracies over stimulus + rest windows (not comparable with 5-class accuracy). The like-for-like 5 vs 6 quantity
   is `2.0s StimCorrect (%)` (6) vs `2.0s Smoothed (%)` (5): the same stimulus windows, same denominator.
4. **R5: must `channel_fail_fraction` be explicit now?** Ruling: yes in principle (R5 "always pass every threshold
   of a shared helper explicitly"; the P16 C-2 reasoning applies word for word), but not blocking for P17: (a) on
   built roots with `--quality shared` neither value is read by `load_subject`; (b) the CLI passes the config
   value 0.5 explicitly; (c) default and config are equal (0.5, `src/features/ssvep/window_mask.py:23`). No P17
   number can depend on it. Carry-forward C-b.
5. **Builders' edits to tester-owned / P16 test files.** `tests/test_p16_independent_known_answer.py` (3 calls now
   pass `thresholds=GATE["thresholds"]`, values identical to the removed `GATE_THRESHOLDS`, `:172` vs
   `window_mask.py:22`; assertions unchanged) and `tests/test_p16_freeze_baseline.py` (stub accepts `**kw`;
   assertion unchanged). Both are forced by C-2/C-1, weaken nothing, and pass. Accepted. Process note: a builder
   editing another owner's test should name it in its handoff (both did) and the tester should acknowledge it in
   04 (it did not); non-blocking.
6. **Guard 1.047 s and P17 `base` ≠ P16 row c.** The rule was decided in 02_plan.md before any number and applied
   by decisions.md P17 row 2; sound: all six runs share one mask, so bank and class comparisons are not confounded
   by QC. P16 guard 231 samples (0.902 s), new 268 samples (1.046875 s; `268/256`). A longer guard can only remove
   windows, so P17 valid ⊆ P16 valid. On S03 the smoke reports 310 valid, equal to P16 `n_valid` 310
   (`data/processed_continuous/S03/windows_meta.json`), so S03's stimulus mask is likely unchanged; D0 turns that
   into a binding identity check for every subject.

### The S03 gain: what accepts or rejects it (pre-committed)

Seen before writing this: the ml-engineer's S03 smoke table (all six cells, `03_changes_ml-engineer.md`) and the
P16 row c CSV (`reports/n_subjects_benchmark_v2cont.csv`: S01 72.8/77.9, S02 72.42/75.26, S03 93.61/93.92,
S04 99.49/99.49, S05 98.59/98.79). S03 therefore cannot confirm any direction below; only S01, S02, S04, S05 count
as confirming.

Reading of the mechanism. `harm` adds 14 ±1 Hz bands at k·f, k = 1..3: it includes the five **fundamentals** as
narrow bands, not only harmonics. The tester's control (c) shows the narrow CSP gains SNR on weak harmonic content
in-fold; the null (a) stays at chance; carry-over (b) is ≤ 6.5e-6 at the protocol spacing. The remaining risk is a
real-data path the synthetic null did not exercise (it has no rejected windows and no dropped channel) or a
real-data timing closer than the protocol spacing. The new P17 code is data-independent (bank concatenation and
row selection are the same `sel`/`kept_idx` for every bank, `subject_data.py:194`), so I do not require a
label-permutation flag before the run; I require the cheap real-data checks D0-D2 and pre-commit a trigger.

Accept "the harm gain is consistent with a genuine in-fold SNR gain of the narrow bands" if all hold:

- G1. The verifier's suite run passes `tests/test_p17_leak_controls.py` (12 tests) unchanged.
- G2. D0 identity holds, D1 minimum cross-trial gap ≥ 2.0 s on every subject (tester table: worst leak 6.4e-5 at
  2 s, 1.0e-6 at 3 s), D2 non-guard files byte-identical.
- G3. No leak signature: for every subject whose `base` 5-class 1.0 s is below 90 %, `harm` 1.0 s < 97 % **and**
  `harm − base` (1.0 s) < +20 pp. (A leak lifts weak subjects to the ceiling irrespective of SNR; the synthetic
  2·f0 control gained +14.5 pp at near-chance SNR, so +20 pp is beyond what the mechanism has shown.)
- G4. Internal 5/6 consistency on `harm`: per subject, 2.0 s StimCorrect(6) + Missed(6) ≥ 2.0 s Smoothed(5) − 3
  pp (stimulus-vs-stimulus discrimination should not collapse when rest is added; a leak specific to the 5-class
  label set would show as a 6-class drop beyond the rest confusions).

Outcomes. G1-G4 met: accept, worded "consistent with an SNR gain of narrow bands at k·f (fundamentals
included)"; no attribution to harmonics alone (the bank cannot separate k = 1 from k = 2, 3; C-d). G3 or G4
triggered: results review REJECT, diagnostic round with a trial-level label-permutation control on real data
(ml-engineer flag; whole trials permuted within subject, groups unchanged; `harm` and `base`, 5 classes, all
subjects, 10 repeats; expected 1.0 s accuracy < 20 + 4·sqrt(16/n) % per subject) before any claim. G1 or G2
failing: REJECT. Diagnostics I considered and do not require: a per_window `harm` control (order-2 ±1 Hz bands
ring 1.05 s on 1 s windows, so its outcome would be dominated by edge transients and is not interpretable either
way); per-band contribution (needs code; carry-forward C-d as an open question).

### Pre-committed comparison rules (results review applies these verbatim)

Per subject, metric X, arms a and b with 10-repeat means `m_a, m_b` and SDs `s_a, s_b` (CSV columns): Δ = m_a − m_b,
σ = sqrt(s_a² + s_b²), w = one window of the metric's denominator in pp (accuracy, StimCorrect, Missed: 100/n of
the stimulus (or all, for 6-class accuracy) windows; FalseAct: 100/rest windows; BalAcc: 100/(K·n_min), K classes,
n_min the smallest class count).

- material: |Δ| ≥ max(2σ, 2w);
- tie: |Δ| < max(σ, w);
- otherwise: small (direction may be described, no claim).

The SDs measure split variability on fixed data (seeds 42..51; within one class count the splits are identical
across banks, so bank comparisons are paired; 5 vs 6 splits differ). No p-values, no "significant". A cohort
claim ("harm > base") needs a material difference of the same sign in ≥ 3 of 5 subjects and no material
difference of the opposite sign; subjects with both arms ≥ 99 % count as ties at ceiling, not against. Otherwise
"subject-dependent" or "no difference". The Mean row never decides alone (§5.9, R9).

5 vs 6 classes is compared only as 2.0 s StimCorrect(6) vs 2.0 s Smoothed(5), same bank, after the verifier
confirms `Clean Windows(6) − Rest Windows = Clean Windows(5)`. 6-class accuracy and BalAcc are reported, not
compared with 5-class accuracy (different chance levels: 16.7 % vs 20 %).

### A-priori directions (S03 excluded as seen)

| # | Comparison | Expected | Reason |
|---|---|---|---|
| P1 | harm vs base, 5-class, 1.0 s and 2.0 s | harm ≥ base: material gain on S01 and S02 (≈ 27 pp headroom), tie at ceiling on S04, S05 | narrow ±1 Hz CSP at f, 2f, 3f vs 4 Hz-wide fbcsp bands; tester control (c) |
| P2 | harm+mid vs harm | tie on ≥ 4 of 5 subjects | midpoints carry no stimulus energy; 3 of 4 overlap harmonic or target skirts (21-23 ⊃ 21.82, 16.5-18.5 ⊃ 17.14, 8.74-10.74 between 8.57 and 10.91) |
| P3 | 6 vs 5, same bank: StimCorrect(6) vs Smoothed(5) at 2.0 s | StimCorrect(6) ≤ Smoothed(5) on every subject (material loss or tie), the loss ≈ Missed | rest absorbs weak stimulus windows |
| P4 | Missed vs FalseAct, 2.0 s, base | Missed > FalseAct on ≥ 3 of 5 subjects (rule above with w of each) | low-SNR stimulus windows (S01, S02) resemble fixation; uniform priors lower rest predictions |
| P5 | harm vs base, 6-class | BalAcc harm ≥ base (gain or tie); FalseAct harm ≤ base (tie allowed); Missed no direction | same SNR argument; rest has no narrow-band SSVEP power |
| P6 | 2.0 s vs 1.0 s | 2.0 s ≥ 1.0 s (gain or tie) for 5-class accuracy and 6-class BalAcc on every subject | R8 2-tap smoothing |
| P7 | base 5-class on `_p17` vs P16 row c | D0 identity on subjects with an equal stimulus mask; elsewhere Δ ≤ k(1−acc)/n directly plus split variation | one mask, same bands (byte-identical) |

A refuted direction is reported as refuted, with the subject, not re-explained after the fact; it is not a FAIL
by itself (R-16: no numeric target). P1 refuted by a material loss on ≥ 2 subjects would be read as a
dimensionality cost (195 features, ~155 training rows per fold), to be stated as an open question, not tuned.

### Required before the run (orchestrator: copy into 02_plan.md "Run commands"; no code change)

1. **Pre-run state** (before step 1): `data/processed_continuous_p17` must not exist and `ls reports | grep -c p17`
   must print 0 (stale same-name outputs). Pinned hash of the P16 root, computed here at `a1e49e4`:
   `find data/processed_continuous -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum` ->
   `c59c94b8ac90a77f57148f057698411f97690ec1174b1202237b37624144a54e` (65 files). The verifier runs the same command
   before step 1 and after the last step; all three values must be equal.
2. **D2 (after step 1, before the benchmarks): non-guard files and masks.**
   ```bash
   for s in S01 S02 S03 S04 S05; do for f in X_time_windows X_raw_windows X_bands_fbcca X_bands_fbcsp y_labels trial_ids window_starts sub_idx window_offsets valid_mask_no_guard; do cmp -s data/processed_continuous/$s/$f.npy data/processed_continuous_p17/$s/$f.npy || echo "DIFF $s $f"; done; done; echo done
   .venv/bin/python -c "
   import json, numpy as np
   for s in ['S01','S02','S03','S04','S05']:
     a, b = [f'data/{r}/{s}' for r in ('processed_continuous', 'processed_continuous_p17')]
     y = np.load(a + '/y_labels.npy'); va = np.load(a + '/valid_mask.npy').astype(bool); vb = np.load(b + '/valid_mask.npy').astype(bool)
     ga, gb = [json.load(open(p + '/windows_meta.json'))['quality']['guard_samples'] for p in (a, b)]
     st, re = np.isin(y, [101, 102, 103, 104, 105]), y == 201
     print(s, 'guard', ga, gb, 'valid', int(va.sum()), int(vb.sum()), 'stim', int(va[st].sum()), int(vb[st].sum()), 'rest', int(va[re].sum()), int(vb[re].sum()), 'p17-only', int((vb & ~va).sum()), 'stim mask equal', bool(np.array_equal(va[st], vb[st])))
   "
   ```
   Expected: only `done` from the loop; guard 231 -> 268 on every subject; `p17-only 0`. The printed table is the
   "valid counts p17 vs P16" of the report.
3. **D1 (after step 1): real cross-trial gap.**
   ```bash
   .venv/bin/python -c "
   import json, numpy as np
   for s in ['S01','S02','S03','S04','S05']:
     d = f'data/processed_continuous_p17/{s}'; m = json.load(open(d + '/windows_meta.json'))
     y, ids, st = (np.load(f'{d}/{k}.npy') for k in ('y_labels', 'trial_ids', 'window_starts')); v = np.load(d + '/valid_mask.npy').astype(bool)
     k = v & np.isin(y, [101, 102, 103, 104, 105, 201]); o = np.argsort(st[k], kind='stable'); s2, i2 = st[k][o], ids[k][o]
     g = (s2[1:] - s2[:-1] - m['n_samples']) / m['fs']; ch = i2[1:] != i2[:-1]
     print(s, 'min gap between windows of different trials (s):', round(float(g[ch].min()), 3))
   "
   ```
   Expected ≥ 2.0 s on every subject (protocol: 3 s, 201 end to stimulus onset). Below 2.0 s: G2 fails.
   Dry run of the same snippet on the P16 root (path `data/processed_continuous`): 2.969 s on all five subjects.
   Starts are byte-identical (D2) and P17 valid ⊆ P16 valid, so the `_p17` value can only be ≥ 2.969 s; the run
   confirms it.
4. **D0 (after step 1): base regression on the new root.**
   `.venv/bin/python -m scripts.benchmarks.feature_based.benchmark_n_subjects --data-root data/processed_continuous_p17 --quality shared --cv-repeats 5 --bank base --classes 5 --out-suffix p17_diag_base_5class_rep5`
   Expected: for every subject with `stim mask equal True` in D2, `1.0s Acc (%)`, `2.0s Smoothed (%)`, `1.0s SD`,
   `2.0s SD` and `Clean Windows` equal `reports/n_subjects_benchmark_v2cont.csv` exactly (CSV values identical).
   A mismatch on such a subject is a regression: verifier FAIL. Subjects with a changed mask: report k removed
   stimulus windows and Δ. Runtime ≈ 15 s.

Budget: build ~1 min, D0-D2 < 1 min, six benchmarks ~6 min (smoke estimate), suite ~11 min: well inside 120 min.

### Verifier checks (in 06_verify.md)

- Six CSVs `reports/n_subjects_benchmark_p17_{base,harm,harmmid}_{5,6}class.csv` + `.meta.txt`, three
  `..._6class_confusion.csv`, plus the D0 CSV; nothing else new under `reports/` except logs.
- Schema: §6 column order; 5-class files have no 6-class columns; 6-class files have the 8 columns + 7 SD columns;
  `CV repeats` = 10 on every row; one Mean row; `Bank` = `fbcca` / `fbcca+harm` / `fbcca+harm+mid`;
  `len(CSP Bands.split())` = 5 / 19 / 23 on every subject.
- One mask: `Clean Windows` equal across the three banks for each class count; `Clean Windows(6) − Rest Windows =
  Clean Windows(5)` per subject.
- Confusion files: classes `101..105, 201` only; per subject entries sum to 10 × `Clean Windows`, the 201 row to
  10 × `Rest Windows`; `Sum` = sum of the subject blocks; 2.0 s FalseAct, Missed, StimCorrect, BalAcc and the 6-class
  `2.0s Smoothed (%)` re-derived from the summed matrix equal the CSV within 0.005 (denominators are fixed across
  repeats, so the mean over repeats equals the pooled rate; e.g. FalseAct = 100·Σ(201 row, stimulus columns)/(10·Rest Windows)).
- P16 root hash unchanged (item 1); D0, D1, D2 outputs quoted verbatim.

### Required fixes

None for the builders. Items 1-4 above are run-list additions (orchestrator).

### Non-blocking notes (carry-forwards for decisions.md)

- **C-a (data-signal; before any phase rebuilds `data/processed_continuous`).** `--banks` now defaults to the four
  config-enabled banks (`scripts/build_windows.py:136`, `:413`), so the P16 documented build command
  (`mas/state/reports/P16.md:74`, no `--banks`) now yields guard 1.047 s masks, and `save_built` replaces an existing
  subject folder without a check (`scripts/build_windows.py:256-258`): re-running it would silently overwrite the
  P16 root with different masks (a defaulted parameter changing the shared decision, the PF-07 pattern). Fix: refuse
  to overwrite a folder whose `build_params` differ unless an explicit `--overwrite` is given. The P17 report must
  state that the P16 masks are reproduced with `--banks fbcca fbcsp`. Also: 02_plan's rationale "P18+ read the
  default built root, which must carry all banks" no longer holds; any later phase needing the narrow banks reads
  `data/processed_continuous_p17/` and its masks (orchestrator, decisions.md).
- **C-b (ml-engineer; next phase that touches `benchmark_n_subjects`).** Make `fail_fraction` in `evaluate_subject`
  required (no `CHANNEL_FAIL_FRACTION` default, `:257`), as C-2 did for `thresholds`.
- **C-c (ml-engineer; same).** The console `Data source` line (`:405`) says "stimulus windows only" also under
  `--classes 6`.
- **C-d (open question for the report).** The `harm` bank mixes fundamentals (k = 1) and harmonics (k = 2, 3); an
  ablation (narrow fundamentals only vs k = 2, 3 only) would be needed to attribute any gain to harmonics.
- `assert 202 not in d["y"]` (`:299`) is a Python `assert` (removed under `-O`); fine for the scripts as run.

## Results review

Verdict: APPROVE

Inputs: `06_verify.md` (d7daf81, PASS), `05_run.md`, `reports/n_subjects_benchmark_p17_{base,harm,harmmid}_{5,6}class.csv`,
the three `_6class_confusion.csv`, D0 CSV `reports/n_subjects_benchmark_p17_diag_base_5class_rep5.csv`. The pre-run
rules were applied unchanged with this read-only command (output quoted below; σ = sqrt(SD_a² + SD_b²), w = one
window of the denominator, BalAcc w = 100/(6·n_min) with n_min from the confusion row sums / 10):

```bash
.venv/bin/python - <<'EOF'
import pandas as pd, numpy as np
R='reports/n_subjects_benchmark_p17_'
L=lambda n: pd.read_csv(R+n+'.csv').set_index('Subject').drop('Mean')
c5={b:L(b+'_5class') for b in ('base','harm','harmmid')}
c6={b:L(b+'_6class') for b in ('base','harm','harmmid')}
cf={b:pd.read_csv(R+b+'_6class_confusion.csv') for b in ('base','harm','harmmid')}
def nmin(b,s):
  c=cf[b]; return int(c[c.Subject==s][[str(k) for k in (101,102,103,104,105,201)]].sum(axis=1).min()/10)
def cls(ma,sa,mb,sb,w):
  d=ma-mb; sg=np.hypot(sa,sb)
  if abs(d)>=max(2*sg,2*w): k='MAT'
  elif abs(d)<max(sg,w): k='tie'
  else: k='small'
  return f"{d:+6.2f} s{sg:4.2f} w{w:4.2f} {k}"
# ... per comparison: 5-class acc (1.0 s: '1.0s Acc (%)','1.0s SD'; 2.0 s: '2.0s Smoothed (%)','2.0s SD', w=100/Clean Windows);
# 6-class columns with their ' SD' twin (w: stim = Clean-Rest, rest = Rest Windows, bal = 6*n_min);
# 6 vs 5 = 2.0s StimCorrect(6) vs 2.0s Smoothed(5), w=100/Clean(5); Missed vs FalseAct w = max of the two windows
EOF
```

(Full script as run in this session; the elided lines are the loops printing each comparison.) Ceiling = both arms ≥ 99 %.

G1-G4 (pre-committed acceptance of the gain) are all met per `06_verify.md`: suite with the 12 leak controls
passed; D0 25/25 values identical to P16 row c; D1 min cross-trial gap 2.969 s on all subjects; D2 non-guard files
byte-identical, `p17-only 0`; G3 S01 +12.35 pp to 85.50 %, S02 +13.69 pp to 86.74 % (< +20 pp, < 97 %); G4 met on
5/5. The gain is accepted under the pre-committed wording.

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| R-16 | no numeric target; direction and plausibility | directions below | — | n/a | — | yes |
| P16 row c (D0 identity) | equal on subjects with an equal stimulus mask (5/5) | 25/25 values equal (`06_verify.md` D0) | 0 | yes (exact) | same bands, same mask, same seeds | yes |

### Per-subject comparisons (rule output, Δ in pp)

**P1 harm − base, 5 classes** (`..._harm_5class.csv` vs `..._base_5class.csv`):

| Subject | 1.0 s Δ (σ) | class | 2.0 s Δ (σ) | class |
|---|---|---|---|---|
| S01 | +12.35 (2.76) | material | +12.60 (2.75) | material |
| S02 | +13.69 (2.94) | material | +11.53 (3.18) | material |
| S03 (seen) | +5.62 (1.22) | material | +5.56 (1.13) | material |
| S04 | +0.62 (0.40) | small, ceiling | +0.62 (0.40) | small, ceiling |
| S05 | +0.96 (0.71) | small | +0.85 (0.68) | small, ceiling |

Confirmed on S01 and S02 (material gains, the pre-committed direction). S04 is a ceiling tie as predicted; S05 is
"small" at 1.0 s (base 98.89 < 99 so the ceiling clause does not apply), positive direction, no claim. Cohort rule:
3/5 material same sign (S01, S02, S03), none opposite: **"harm > base" holds at 1.0 s and 2.0 s**. S03 is counted
by the rule but is the observation that prompted the check; the independent confirmation is S01 and S02.

**P2 harm+mid − harm, 5 classes:** tie on 10/10 subject × time cells (largest |Δ| S01 2.0 s −1.40, σ 2.54).
Confirmed. 6 classes: tie on all 25 subject × metric cells (BalAcc 1.0/2.0 s, FalseAct, Missed, StimCorrect).
The intermediate bands add nothing measurable.

**P3 6 vs 5 classes, 2.0 s StimCorrect(6) − Smoothed(5):** negative on 15/15 subject-bank cells; material on 12,
small on base S02 (−6.10, σ 3.68) and base S03 (−2.53, σ 1.63). Direction confirmed (no gain anywhere; "small" is a
loss below the material bar, not a contradiction). The second half, "loss ≈ Missed", is **refuted on the low-SNR
subjects**: base S01 loss 6.45 vs Missed 14.25, S02 6.10 vs 18.26; harm S01 15.20 vs 20.00, S02 11.48 vs 20.00. It
holds on S03–S05 (e.g. harm S04 1.38 vs 1.38, S05 2.92 vs 2.81). Reason (arithmetic, not a new hypothesis): loss =
Missed − (5-class stimulus errors − 6-class stimulus-to-other-stimulus errors); on S01/S02 many windows that rest
absorbs were already 5-class errors (base S01: 5-class error 21.15, 6-class stimulus-to-stimulus error
100 − 72.40 − 14.25 = 13.35).

**P4 Missed − FalseAct, 2.0 s, base:** S01 −7.75 (σ 3.84) material **opposite**; S02 +2.18 tie; S03 +4.19
material; S04 +2.51 small; S05 +2.96 material. 2 material in the predicted direction and 1 opposite: **P4 refuted
for base** (S01 has FalseAct 22.00 % > Missed 14.25 %). With the narrow banks it holds: harm and harm+mid material
Missed > FalseAct on S01, S02, S03, S05, small on S04.

**P5 harm − base, 6 classes:** 2.0 s BalAcc S01 +5.69 material, S02 +7.01 material, S03 +1.86 small, S04 +0.95
small, S05 +0.55 tie — direction confirmed (no loss), but only 2/5 material, so **no cohort claim** by the rule;
"BalAcc gain on S01 and S02" only. FalseAct S01 −14.88 and S02 −12.84 material, ties elsewhere (S04, S05 0.00 in
both): confirmed. Missed (no direction pre-committed): S01 +5.75 material, others tie/small. So in 6 classes the
narrow bands mainly move rest errors: far fewer false activations, somewhat more misses on S01.

**P6 2.0 s vs 1.0 s:** no material or small negative cell in 15 (5-class accuracy) + 15 (6-class BalAcc); minimum
−0.04 (base S04 BalAcc, tie). Confirmed. Material smoothing gains only on S01 (5-class base +5.70, harm +5.95).

**P7:** D0 exact. Confirmed.

### Interpretation check

- **Leakage.** No fitted object sees test rows (pre-run R2), splits are trial-grouped with the runtime guard, priors
  are fixed, the mask is shared by all six runs, and the pre-committed leak signature (G3) did not fire. Weak
  subjects did not jump to the ceiling: S01/S02 harm 85.50/86.74 % (1.0 s). The gain is accepted as **consistent
  with an SNR gain of the ±1 Hz bands at k·f**, not proven genuine; the real-data label-permutation control was not
  required by the outcome and was not run.
- **What the bank is (C-d).** `harm` = 14 narrow bands at k·f, k = 1..3, **including the five fundamentals** (60 Hz
  skipped). The data cannot say whether the gain comes from the narrow fundamentals or from the harmonics. The report
  must not write "harmonic bands improve" or "harmonics carry the gain"; write "the narrow bank at the stimulus
  frequencies and their 2nd/3rd multiples".
- **6-class accuracy columns.** `1.0s Acc (%)`/`2.0s Smoothed (%)` in the 6-class CSVs are over stimulus + rest
  windows; never compare them with 5-class accuracy. Use StimCorrect(6) vs Smoothed(5).
- **Uniform priors.** Rest has 74-80 windows vs 36-40 per stimulus class; with priors 1/6 the classifier is not
  pushed towards rest by frequency. The S01 base FalseAct 22 % shows rest is not easy to separate for low-SNR
  subjects with the broad bands; the narrow banks cut it to 7.12 %.
- **Coincidence flag.** harm 2.0 s Missed is exactly 20.00 % on both S01 and S02: counts 400/2000 (S01: 98 + 91 + 25 +
  36 + 150 in the 201 column) and 380/1900 (S02: 17 + 65 + 76 + 116 + 106), with per-repeat SD 1.97 and 2.11. It is
  not "one window per trial" by construction (it varies per repeat and per class: S01 103 25/400 vs 105 150/400).
  Whether misses concentrate on the first window after onset (narrow-band build-up) is an open question; the
  outputs have no per-offset breakdown. The report must not suggest the 1/5 is structural.
- **Class pattern.** In the summed matrices the rest column is the main error sink for 105 (8.57 Hz) and 104 (10.91
  Hz) on every bank (harm Sum: 280 and 202 of 2000 windows to 201), consistent with alpha-band fixation
  activity overlapping the two lowest targets; descriptive only.
- **S04 mask change.** The longer guard (231 → 268 samples) removes on S04 exactly one 201 window and one 202 window
  (read-only check:
  `.venv/bin/python -c "import numpy as np; a,b='data/processed_continuous/S04','data/processed_continuous_p17/S04'; y=np.load(a+'/y_labels.npy'); va=np.load(a+'/valid_mask.npy').astype(bool); vb=np.load(b+'/valid_mask.npy').astype(bool); print({int(l): int(((va&~vb)&(y==l)).sum()) for l in np.unique(y)})"`
  -> `{101: 0, ..., 105: 0, 201: 1, 202: 1}`). `05_run.md:64` says "2 rest windows removed": wrong, the second is a
  202 cue window, which no P17 run uses. Effect: S04 has 75 rest windows instead of 76 in all three 6-class runs; no
  stimulus window and no 5-class number changes (D0 exact). Other subjects: no change.
- **Statistics.** SDs over 10 repeats are split variability on fixed data; no p-values; nothing called significant.

### What the report must say

1. Data source per run: continuous build at `data/processed_continuous_p17/` (four banks, guard 1.046875 s = 268
   samples) vs P16 `data/processed_continuous/` (two banks, 231 samples), decided before any number; P16 root hash
   unchanged; valid counts table from D2 with the S04 line corrected (−1 rest, −1 cue 202).
2. P16 masks are reproduced only with `build_windows --banks fbcca fbcsp` (C-a).
3. Per-subject tables for 5 and 6 classes with SDs (R9); cohort claims only as ruled above: harm > base (5 classes,
   both times); harm+mid = harm; 6-class costs stimulus accuracy everywhere; BalAcc/FalseAct gains with harm on S01
   and S02 only.
4. The refuted directions verbatim: P4 for base (S01 FalseAct > Missed) and "loss ≈ Missed" on S01/S02.
5. `harm` includes the narrow fundamentals; no attribution to harmonics (C-d).
6. The 6-class accuracy columns are 6-class accuracies; the 20.00 % coincidence; the console "stimulus windows only"
   line of 6-class logs is wrong (C-c), the `.meta.txt` line is the data source.

### Decisions for decisions.md

- D-1 (P17) Narrow-bank gain accepted under the pre-committed G1-G4 (all met): `harm` > `base` in 5 classes, material
  on S01 (+12.35/+12.60), S02 (+13.69/+11.53), S03 (+5.62/+5.56), ceiling/small on S04, S05; worded "consistent with
  an SNR gain of ±1 Hz bands at k·f, fundamentals included"; no real-data permutation control run (not triggered).
- D-2 (P17) Intermediate bands: tie with `harm` on every subject and metric (5 and 6 classes).
- D-3 (P17) 6 vs 5 classes: StimCorrect(6) below Smoothed(5) on 15/15 cells (12 material); loss ≈ Missed only on
  S03-S05.
- D-4 (P17) Pre-committed P4 (Missed > FalseAct, base) refuted: S01 FalseAct 22.00 > Missed 14.25; it holds with
  the narrow banks (4 material, 1 small). 6-class BalAcc gain with harm material on S01, S02 only (no cohort claim).
- D-5 (P17) Guard 1.047 s changes only S04 (−1 rest 201, −1 cue 202); `05_run.md:64` wording corrected in the report.
- D-6 (P17) harm Missed 20.00 % on S01 and S02 recorded as a count coincidence (400/2000, 380/1900).
- Carry-forwards (from the pre-run audit, unchanged): C-a (data-signal: refuse overwriting a built folder with
  different `build_params`; before any phase rebuilds `data/processed_continuous`; later phases needing narrow banks
  read `_p17`), C-b (`fail_fraction` required in `evaluate_subject`), C-c (6-class console data-source line), C-d
  (ablation fundamentals-only vs k = 2, 3 to attribute the gain). New: C-e (optional) per-offset Missed/FalseAct
  breakdown (which window of a trial goes to rest), wherever 6-class work continues.

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
