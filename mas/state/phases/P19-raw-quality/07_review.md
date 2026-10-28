# P19 · 07 · Scientific review

Status: READY (pre-run audit); results review pending
Author: scientific-reviewer
Reads: 00, 02, 03_changes_*, 04 and every changed file (pre-run); 05, 06 and the CSVs (results)

## Pre-run audit — Round 1

Verdict: PASS

Audited: `git diff main...HEAD -- src scripts configs tests` at ba55bf1 (code commits e090d20, ff638a3,
e0a79f9), 00/02/03/04, decisions.md row 147. Era C, no legacy behaviour required; no row is LEGACY.

| Rule | Result (PASS / FAIL / CONCERN / LEGACY (by design) / N/A) | Evidence (`path:line`) |
|---|---|---|
| R1 Trial-grouped CV | N/A (benchmark code unchanged; `git diff --stat p17-done main` touches only `src/features/connectivity/`) | `scripts/benchmarks/feature_based/benchmark_n_subjects.py` unchanged |
| R2 Fit only in-fold | N/A (no fitted object changed) | — |
| R3 Filter continuous, then window | PASS. Raw windows are `cut_windows(x, idx.starts, n)` on the loaded scalp array, the same starts as the filtered windows, with no per-window filtering or detrending. On the stored _p17 arrays (same code path), raw windows keep the DC (S01 max \|window mean\| 829.7 µV raw vs 209.64 filtered) and about 1.8–1.9× the 1 Hz amplitude, so they are unfiltered. | `scripts/build_windows.py:162`, `:175`; command 6 below |
| R4 Estimator small-sample bias | N/A | — |
| R5 Shared quality decision, explicit thresholds | PASS. `source` is a required key (raises if missing or unknown), read from the config, recorded in build_params, meta and the loader string. There is one `guard_sec` per subject for both signals. CONCERN (note 1): `demo_edge_effects.py` inherits the new config default. | `src/preprocessing/window_quality.py:60`, `:77`, `:199`, `:215`; `scripts/build_windows.py:128`; `scripts/diagnostics/demo_edge_effects.py:184-187` |
| R6 Index layouts verified | PASS. The guard overlap is tight to the sample at both window edges, the straddling-block case is covered, and the hand-computed windows 19/20/21 match. The tester killed the mutants that drop the first or last sample of `overlaps_mask` and the guard−1 mutant. | `tests/test_p19_independent_known_answer.py:65`, `:86`, `:264` |
| R7 Honest statistics | N/A (no tests of significance; materiality rule from P17) | `02_plan.md` acceptance 3 |
| R8 Smoothing respects trials | N/A (unchanged) | — |
| R9 Per-subject reporting with data source | PASS. The data-source string ends with `, quality source <s>`, and `windows_meta.json` `quality.source` is written. CONCERN (note 2): the loader's per-label `raw` count is wrong under `shared-no-guard`. | `scripts/build_windows.py:225`; `src/io/subject_data.py:173`, `:202` |
| R10 Every change and test cites a source that exists and says what is claimed | PASS (02_plan settled points, 01_DATA_SPEC §5.2, 02_REQUIREMENTS §3) | `03_changes_data-signal.md` |
| R10 Copied lines marked `# adapted from [n]`, license compatible | N/A (no copied lines) | — |
| R11 Reference consulted only after an attempt, every consultation listed | PASS: no access-log entry dated 2026-10-28 (`grep -c` = 0), and none listed | `mas/state/scratch/reference_access.log` |
| Golden rule 3: legacy behaviour labelled and still reachable after fixes | PASS. `--quality-source filtered` reproduces P16/P17. I checked it myself: I exec'd `git show main:src/preprocessing/window_quality.py` and compared it with HEAD on 40 synthetic subjects (channel drops, artifacts, guard `auto` and 0.5 s, hostile raw = 100×). There were 0 mismatches in valid_mask, valid_mask_no_guard, reason (bytes and dtype), kept/dropped channels, channel_stats, guard, block counts and fractions. | command in note 5 |
| Tests cover every change; at least one fails on the historical bug | PASS. All 9 plan items are covered, plus the independent file. 15/15 mutants were killed, including "gate ignores source" (PF-07 style: silently inheriting the filtered decision). 42 P19 + adapted P16 tests pass in 5.42 s (`pytest tests/test_p19_*.py tests/test_p16_window_quality.py tests/test_p16_build_windows.py`). Gap: no test covers the loader's `rejections_by_label` under `shared-no-guard` (note 2). | `tests/test_p19_raw_quality.py:105`, `tests/test_p19_independent_known_answer.py:128`, `:198` |
| Changes match 02_plan.md and the roadmap tasks | PASS. P19.1–P19.4 and C-a are done. The reason-3 split goes to meta `n_reason3_raw_gate/_guard`. The loader `raw` count goes slightly beyond "string only"; it is disclosed and needed for the sums. | `src/preprocessing/window_quality.py:207-231`; `scripts/build_windows.py:487-495` |
| No data, `.ebr`, local tooling files or tool/vendor names in the diff | PASS. Privacy scan: 0 hits in `git diff main...HEAD`. Changed paths are only configs/, mas/, scripts/, src/, tests/. | — |

**Checks requested by the orchestrator.**
- *Precedence and the reason-3 split.* `reason = 1 if filtered gate, else 2 if filtered guard, else 3 if raw gate or
  raw guard` (`window_quality.py:231`). `n_raw_guard = reason 3 & ~raw gate`. Correct per settled point 3. A window
  that fails the filtered guard and the raw gate stays 2. On real data this happens once: S02 row 200 (103, P17
  reason 2) also fails the raw gate.
- *Channel tier.* It is the union of the per-signal drops (`:207`). Under `both`, a raw-only channel drop can change
  the kept set. The filtered window tier then runs on fewer channels and can *gain* windows that _p17 rejected.
  Run-list check B reports gains explicitly.
- *C-a.* The refusal happens before any subject is built and names the differing keys. Folders from before P19 lack
  `quality.source`, so a default-root rebuild of `data/processed_continuous` or `_p17` is refused without
  `--overwrite`. That protects both roots against the new default.
- *Config default `both`, downstream.* Existing roots are untouched, and every loader reads the recorded masks. The
  only other config consumer of `source` is `demo_edge_effects.py` (note 1). `benchmark_n_subjects.quality_arguments`
  reads only thresholds. P20 builds sweep folders with `build_windows.py` and will get `both` unless its command says
  otherwise (note 3).

**Pre-run expectation (disclosed, computed read-only from the stored _p17 `X_raw_windows.npy`, same code path and
float64).** I ran the raw window gate (`validate_eeg_windows`, limits 5–120 / 1–35 µV) on the union-kept channels.
It adds **exactly one reason-3 raw_gate window cohort-wide: S03 row 160 (condition 102, trial 88, offset 0)**.
The other raw-gate failures already have reason 1, or 2 (S02 row 200). Raw channel fail fractions predict no change
in the channel tier: PO7 fails 100 % on raw in S01/S03/S04, where it is already dropped, and nothing else exceeds
3.1 %. The raw guard cannot be predicted (it needs the continuous raw signal). Margins: the 95th percentile of the
per-window max-channel raw Vpp is 75.3/111.3/64.0/90.1/62.1 µV (S01–S05). Raw is only 2–4 µV above filtered at the
median. The ±1,000–5,800 µV drifts of 01_DATA_SPEC §4 are slow against 1 s windows and 0.25 s blocks, so they do not
produce within-window Vpp. The builder's S01 null (0/0/0) agrees with this.

**Reporting adequacy for a null and pre-committed interpretation.** The plan's acceptance table alone cannot tell
"raw checked and found clean" from "raw path not executed". Checks A–F below close that gap. The results review will
read the outcomes as follows:
- **Null or near-null** (stimulus masks equal, or differing by ≤ a few windows), with checks C–E passing. Report:
  "on the five OO recordings, with these limits and 1 s windows, the raw-signal check adds k reason-3 windows (raw
  gate g, raw guard h); filtering did not hide artifacts that these limits detect". Forbidden: any general claim
  that filtering never hides artifacts, and any claim that `both` changes accuracy, unless Δ is material.
- Subjects whose stimulus `valid_mask` and kept channels are identical between _p17 and _p19_both must give
  **identical CSV rows** (check E). Any difference there is a bug (non-determinism or a root difference), not an
  effect.
- **Direct-effect bound.** For a subject with k stimulus windows removed and equal channels, the window-removal
  effect on 1.0 s accuracy lies in [−(1−acc)·k/(n−k), acc·k/(n−k)]. For S03 base (acc 93.76 %, n 194, k 1) that is
  [−0.03, +0.49] pp. Any larger |Δ| is fold or training variation from the changed row set. It is judged only by the
  P17 materiality rule max(2σ, 2 windows), which is 2.40 pp for S03 base 1.0 s (σ 1.20; 2 windows = 1.03 pp).
- **Large difference.** Many reason-3 windows, a dropped channel, or a material Δ. (a) If reason 3 is dominated by
  raw_gate beyond the pinned count, that contradicts my recomputation, and the result is a wiring FAIL until it is
  explained. (b) If it comes from raw_guard, report the raw block counts, artifact/guarded fractions and the removed
  rows, and check `guard_sec` equality (1.046875 s). That is a legitimate finding, never a reason to tune (PF-07).
  (c) If a channel is dropped, the Δ is attributed to the channel tier, and the gained windows are reported. (d) A
  material accuracy *gain* on S01/S02 with few windows removed is treated as a bug until D and E pass and the direct
  bound is computed. (e) For every non-zero reason-3 count, report the cause per signal (raw gate vs raw guard) and
  per label, not only the count (P07 lesson).

### Required fixes

None.

### Non-blocking notes

1. **R5 / PF-07 pattern, data-signal.** `scripts/diagnostics/demo_edge_effects.py:184-187` builds through
   `resolve_params` with no `--quality-source`, so it now uses `both`. A re-run of the P16 edge-effect command would
   select windows with a different gate than P16 did, without saying so. Fix: pass `"--quality-source", "filtered"`
   in its parse list (or a CLI flag) and print the source. Until then, the P19 report states it. If check B shows no
   stimulus window removed under `both`, the P16 outputs are unaffected in fact.
2. **R9, data-signal.** `src/io/subject_data.py:202` counts `raw` as `reason == 3` without `& ~keep_local`. Under
   `quality_mode="shared-no-guard"`, raw-guard-only windows (reason 3, `valid_mask_no_guard` = 1) are kept but
   counted as rejected, so `own_gate + guard + raw ≠ total − valid`. The `guard` count has the mask. Fix: add
   `& ~keep_local`, with a test on a `both` root under `shared-no-guard`. No P19 run command uses that mode.
3. **P20 plan.** Every build command from P20 on should pass `--quality-source` explicitly (golden rule 5: the
   default changed in this phase). I recommend a decisions.md row: "From P20, build commands name
   `--quality-source`; P20's choice is recorded with its reason."
4. The guard on the raw signal uses the filters' ringing time. That is defensible (a raw step attenuated below
   `vpp_max` still rings into the filtered windows for that long), but it is a design choice, not a physical guard
   of the raw signal. The report should say so under PF-14.
5. Identity command (read-only, reproducible): exec `git show main:src/preprocessing/window_quality.py` as a module
   and call both gates on 40 seeded synthetic subjects (`default_rng(0)`, 6 ch, 120 s, 80 windows, 1–40 Hz
   order-4 sos). Result: `cases 40 mismatches 0`.

### Run-list additions (binding for the verifier; copy verbatim into 02_plan.md)

Roots: `F=data/processed_continuous_p17`, `R=data/processed_continuous_p19_raw`,
`B=data/processed_continuous_p19_both`, `N=mas/state/scratch/p19_filtered`. Every check below is read-only. I
dry-ran A–C on fake P19-format roots (symlinked _p17 arrays) to confirm that they execute. Paste every output
verbatim into 05_run.md.

**A. Hashes (commands 0 and 8).** Before and after:
`for r in data/processed_continuous data/processed_continuous_p17; do echo $r $(find $r -type f | wc -l) $(find $r -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum); done`.
Expected: identical before and after.

**B. Regression build (`N` vs `F`, command 8).** Expected for every subject: `same_file_list True`,
`npy_differ []`, `meta_top_differ []`, `quality_differ []`, `rejections_ok True`, `build_params_ok True`,
`params_ok True`, `new_quality_fields` all None/0 with source `filtered`. Any other output is a FAIL of settled
point 3.
```bash
.venv/bin/python -c "
import json, filecmp, os
A, N = 'data/processed_continuous_p17', 'mas/state/scratch/p19_filtered'
IGN_TOP = {'git_commit', 'data_source', 'build_params', 'quality'}
NEW_Q = {'source', 'channel_stats_raw', 'n_artifact_blocks_raw', 'artifact_fraction_raw', 'guarded_fraction_raw', 'n_reason3_raw_gate', 'n_reason3_raw_guard'}
for s in ['S01', 'S02', 'S03', 'S04', 'S05']:
  fa, fn = sorted(os.listdir(f'{A}/{s}')), sorted(os.listdir(f'{N}/{s}'))
  bad = [f for f in fa if f.endswith('.npy') and not filecmp.cmp(f'{A}/{s}/{f}', f'{N}/{s}/{f}', shallow=False)]
  a, n = json.load(open(f'{A}/{s}/windows_meta.json')), json.load(open(f'{N}/{s}/windows_meta.json'))
  qa, qn = a['quality'], n['quality']
  top = sorted(k for k in set(a) | set(n) if k not in IGN_TOP and a.get(k) != n.get(k))
  qd = sorted(k for k in set(qa) | set(qn) if k not in NEW_Q | {'params', 'reason_codes', 'rejections_by_label'} and qa.get(k) != qn.get(k))
  newq = {k: qn.get(k) for k in NEW_Q}
  rl = all({k: v for k, v in qn['rejections_by_label'][l].items() if k != 'raw'} == {k: v for k, v in qa['rejections_by_label'][l].items() if k != 'raw_gate'} and qn['rejections_by_label'][l]['raw'] == 0 for l in qa['rejections_by_label'])
  bp = {k: v for k, v in n['build_params'].items() if k != 'quality'} == {k: v for k, v in a['build_params'].items() if k != 'quality'} and {k: v for k, v in n['build_params']['quality'].items() if k != 'source'} == a['build_params']['quality'] and n['build_params']['quality'].get('source') == 'filtered'
  pr = {k: v for k, v in qn['params'].items() if k != 'source'} == qa['params'] and qn['params'].get('source') == 'filtered'
  print(s, 'same_file_list', fa == fn, 'npy_differ', bad, 'meta_top_differ', top, 'quality_differ', qd, 'rejections_ok', rl, 'build_params_ok', bp, 'params_ok', pr, 'new_quality_fields', newq, 'data_source', n['data_source'])
"
```

**C. Raw/both roots vs `F`: identities, removed rows and pinned count (after commands 2–3).** Expected for every
subject:
- `nonmask_differ []`: X, bands, starts, labels, trial ids, offsets and sub_idx are identical, so the Δ is only the
  mask.
- If `channels_equal True`: all three identities are `True` (`vb==vf&vr`, `rb(3->0)==rf`, `vb subset vf`) and
  `gained: []`.
- `raw-root reason codes used` ⊆ `[3]`.
- `raw blocks` non-None in both roots, `guard_sec` 1.046875 for f/r/b.
- `raw_gate` count pinned: **S01 0, S02 0, S03 1 (row 160, condition 102, trial 88, offset 0), S04 0, S05 0**.
  Any other `raw_gate` count, or a False identity with equal channels, stops the interpretation. Record it as a
  finding for the review, and do not re-run with other settings.
```bash
.venv/bin/python -c "
import json, filecmp, numpy as np
F, R, B = 'data/processed_continuous_p17', 'data/processed_continuous_p19_raw', 'data/processed_continuous_p19_both'
SAME = ['X_time_windows', 'X_raw_windows', 'X_bands_fbcca', 'X_bands_fbcsp', 'X_bands_harmonic', 'X_bands_intermediate', 'window_starts', 'y_labels', 'trial_ids', 'window_offsets', 'sub_idx']
for s in ['S01', 'S02', 'S03', 'S04', 'S05']:
  m = {k: json.load(open(f'{d}/{s}/windows_meta.json'))['quality'] for k, d in (('f', F), ('r', R), ('b', B))}
  ld = lambda d, n: np.load(f'{d}/{s}/{n}.npy')
  nd = [f'{x}:{n}' for x, d in (('raw', R), ('both', B)) for n in SAME if not filecmp.cmp(f'{F}/{s}/{n}.npy', f'{d}/{s}/{n}.npy', shallow=False)]
  y, tid, off = ld(F, 'y_labels'), ld(F, 'trial_ids'), ld(F, 'window_offsets'); st = np.isin(y, [101, 102, 103, 104, 105])
  vf, vr, vb = (ld(d, 'valid_mask').astype(bool) for d in (F, R, B)); rf, rr, rb = (ld(d, 'reject_reason') for d in (F, R, B))
  ch = [m[k]['channels_kept'] for k in 'frb']; eq = ch[0] == ch[1] == ch[2]
  print(s, 'nonmask_differ', nd, 'channels_equal', eq, ch[2] if eq else ch)
  print('  valid f/r/b', int(vf.sum()), int(vr.sum()), int(vb.sum()), '| stimulus', int(vf[st].sum()), int(vr[st].sum()), int(vb[st].sum()))
  print('  both reasons 1/2/3', [int((rb == c).sum()) for c in (1, 2, 3)], 'raw_gate/raw_guard', m['b']['n_reason3_raw_gate'], m['b']['n_reason3_raw_guard'], '| raw-root reason codes used', sorted(set(rr[rr > 0].tolist())))
  if eq: print('  identities vb==vf&vr', bool(np.array_equal(vb, vf & vr)), 'rb(3->0)==rf', bool(np.array_equal(np.where(rb == 3, 0, rb), rf)), 'vb subset vf', bool(not (vb & ~vf).any()))
  print('  removed by both (row, label, trial, offset, reason):', [(int(i), int(y[i]), int(tid[i]), int(off[i]), int(rb[i])) for i in np.flatnonzero(vf & ~vb)], 'gained:', [int(i) for i in np.flatnonzero(vb & ~vf)])
  print('  raw blocks/artifact/guarded', m['b']['n_artifact_blocks_raw'], m['b']['artifact_fraction_raw'], m['b']['guarded_fraction_raw'], '| guard_sec f/r/b', m['f']['guard_sec'], m['r']['guard_sec'], m['b']['guard_sec'])
"
```

**D. Margins (makes a null interpretable).** Expected `X_raw_windows` 95th percentiles of 75.3/111.3/64.0/90.1/62.1
µV for S01–S05 (same arrays as _p17).
```bash
.venv/bin/python -c "
import json, numpy as np
B = 'data/processed_continuous_p19_both'
for s in ['S01', 'S02', 'S03', 'S04', 'S05']:
  m = json.load(open(f'{B}/{s}/windows_meta.json')); k = [m['channels'].index(c) for c in m['quality']['channels_kept']]
  for n in ('X_time_windows', 'X_raw_windows'):
    X = np.load(f'{B}/{s}/{n}.npy')[:, k]; v = np.ptp(X, axis=2).max(1); sd = X.std(axis=2).max(1)
    print(s, n, 'max-channel Vpp p50/p95/max', np.round(np.percentile(v, [50, 95, 100]), 1), 'std p95/max', np.round(np.percentile(sd, [95, 100]), 1), 'n Vpp>120', int((v > 120).sum()), 'n std>35', int((sd > 35).sum()))
"
```

**E. Flagship determinism and unaffected subjects (commands 4–7).**
- `cmp reports/n_subjects_benchmark_p19_filtered_base.csv reports/n_subjects_benchmark_p17_base_5class.csv` and
  `cmp reports/n_subjects_benchmark_p19_filtered_harm.csv reports/n_subjects_benchmark_p17_harm_5class.csv`:
  silent (byte-identical).
- `diff` of the two `.meta.txt` pairs: only the `quality:` line differs, gaining `, quality source filtered`. Any
  other differing line is reported.
- For every subject that check C shows with an empty stimulus "removed" list, an empty "gained" list and equal
  channels, the `_p19_both_*` CSV row must equal the `_p19_filtered_*` row in every column. Show it with
  `diff <(grep '^S0' reports/n_subjects_benchmark_p19_filtered_base.csv) <(grep '^S0' reports/n_subjects_benchmark_p19_both_base.csv)`
  (same for harm). Expected: only rows of subjects with a changed stimulus mask differ (S03 at least, from the pinned
  raw_gate window).
- The `Clean Windows` difference per subject equals the number of stimulus rows that check C lists as removed minus
  those gained.

**F. Report wording.** In every flagship table, each row names its root and `quality source` (R9). The rejection
table shows reason 3 split into raw_gate/raw_guard per subject and per label (101–105, 201, 202) for all three
sources. Under `raw`, windows that only the filtered gate rejected become valid, so `raw` can keep more windows than
`filtered`; the table must not describe `raw` as stricter.

## Results review

Verdict: APPROVE / REJECT

### Deviations from references

| Ref | Expected | Obtained (log) | Δ | Within tolerance? | Explanation | Accepted? |
|---|---|---|---|---|---|---|
| | | | | | | |

### Interpretation check

<!-- Per-subject reading; inconclusive results stated as such; leakage in
fitted objects, normalization, validation sets; statistics unit and
multiple comparisons. -->

### Decisions for decisions.md

<!-- Accepted deviations, one line each; the orchestrator copies them. -->

## Sources spot-check

<!-- Fix rounds: append "## Pre-run audit — Round N". After two failed rounds,
set Status: BLOCKED. -->

## Questions
