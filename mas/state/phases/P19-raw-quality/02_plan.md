# P19 · 02 · Plan

Status: READY
Author: orchestrator
Approval: PLAN_APPROVAL auto

## Goal

Make the shared quality decision optionally check the unfiltered ("raw") signal as well as
the broadband-filtered one: `params["source"] ∈ {filtered, raw, both}`, reason 3 for windows
that fail only on raw, `build_windows.py --quality-source`, config default `both`. Record the
per-subject rejection breakdown by reason for each source and the flagship difference
`both` vs `filtered`. R-16: no numeric target.

## Data source

- Recordings: `OO` session of every discovered subject (S01–S05), read only by
  `scripts.build_windows`.
- Raw signal = the scalp channels of the unfiltered recording as loaded by `build_windows`
  (the same array the filters are applied to, DC and drift included); raw windows =
  `X_raw_windows.npy`, cut at `window_starts` (01_DATA_SPEC §5.2). No per-window detrending,
  no per-window filtering (R3).
- Filtered reference root: `data/processed_continuous_p17` (all four banks, guard 1.047 s,
  `source: filtered` implied). It and `data/processed_continuous` (P16) stay untouched; the
  verifier hashes both before and after.

## Settled points (inferred; recorded in decisions.md)

1. **Channel tier.** A channel is dropped if it exceeds `channel_fail_fraction` on *any*
   checked signal (the existing rule applied to filtered windows, raw windows, or both).
   Window tier and guard then use the surviving channels only, on every checked signal.
2. **Artifact guard per signal.** For each checked continuous signal, blocks of
   `artifact_block_sec` with Vpp > `vpp_max` on any kept channel are artifacts. Both use
   the same `guard_sec`. `auto` is the ringing time of the continuously applied filters,
   which is what can spread an artifact into the filtered windows. One guard per subject
   (R5).
3. **Reason codes (precedence).**
   - 1 = fails the Vpp/std gate on the filtered window.
   - 2 = overlaps the guard of a filtered-signal artifact.
   - 3 = passes every filtered check but fails a raw check (raw window gate or raw-artifact
     guard).
   - With `source=raw` no filtered check runs, so every rejection is 3.
   - With `source=filtered` the decision is byte-identical to P16/P17.
   - `windows_meta.json` `quality` also splits reason 3 into `raw_gate` and `raw_guard`
     counts.
   - `valid_mask_no_guard` = the decision without any guard (filtered or raw).
4. **`source` is a required param** (R5, no default inside the gate).
   - `quality_params_from_config` reads `quality.source`.
   - `build_params` records it, so P17 C-a can tell the folders apart.
   - `windows_meta.json` and the loader's data-source string carry it (R9).
5. **Empty subject.** If every channel is dropped, `build_windows` prints
   `[-] Skipping <S>: all channels dropped (source=<s>)`, writes nothing for that subject and
   continues. This is a recorded result, not an error (PF-07).
6. **Thresholds unchanged** (5–120 µV Vpp, 1–35 µV std, fail fraction 0.5, block 0.25 s).
   Raw windows carry drifts of up to ±1,000–5,800 µV (01_DATA_SPEC §4), so `raw`/`both` may
   reject many windows. That is the phase's finding, never a reason to tune (golden rule 5,
   PF-07).
7. **Config default `both`** (`quality.source: both`, `02_REQUIREMENTS.md` §3).
   - Existing roots keep their recorded `build_params`.
   - Later phases choose their root explicitly; P20's choice is the P20 plan's.
8. **P17 C-a.** `build_windows` refuses to write into a subject folder whose
   `windows_meta.json` `build_params` differ from the requested ones, unless `--overwrite`
   is given. `--resume` still skips identical ones. The message names the differing keys.
9. **Roots.**
   - `data/processed_continuous_p19_raw`, `data/processed_continuous_p19_both`: all four
     banks, so the guard matches the _p17 root.
   - A regression build with `--quality-source filtered` goes to
     `mas/state/scratch/p19_filtered`. It is compared with _p17 (all files byte-identical
     except `windows_meta.json` git/commit/source fields), then deleted at the merge (disk:
     about 0.7 GB per root, 22 GB free).

## Work split

| # | Agent | Files | Tasks |
|---|---|---|---|
| 1 | data-signal | MODIFIED `src/preprocessing/window_quality.py`, `scripts/build_windows.py`, `configs/pipeline_config.yaml`, `src/io/subject_data.py` (data-source string only) | P19.1–P19.4, settled points 1–9, P17 C-a |

## Methodological risks

- **R5.** `source` and every threshold passed explicitly. The gate raises on a missing key.
- **R3.** Raw windows must be the stored unfiltered windows, not re-filtered.
- **PF-07.** A raw check that rejects almost everything is reported per subject with counts
  by reason and label. Limits are not changed.
- **R6.** `window_starts` ↔ raw/filtered windows ↔ continuous-sample guard overlap: same
  index conventions as P16. A known-start synthetic case is required.
- **Regression.** `source=filtered` must reproduce the _p17 masks/reasons exactly.
- **R9.** Every flagship row is reported per subject (1.0 s and 2.0 s) with its root and
  `source`.

## Tests required (known answers)

1. A raw-only artifact:
   - setup: a large slow step/drift on raw that the 1–90 Hz filter removes (filtered window
     within limits);
   - `source=filtered`: valid;
   - `source=raw` or `both`: rejected with reason 3.
2. A filtered-only failure, e.g. a window whose filtered std < `std_min` while raw passes,
   keeps reason 1 under `both`.
3. Raw-artifact guard:
   - setup: one 0.25 s raw block > `vpp_max` at a known sample;
   - expected: exactly the windows overlapping block ± guard get reason 3 under `both`, and
     none under `filtered`.
4. Channel tier: a channel bad only on raw is dropped under `raw`/`both`, kept under
   `filtered`.
5. `source=filtered` gives byte-equality with the P16 gate on a synthetic subject. This
   test fails on a gate that ignores `source`.
6. A missing `source` key raises (R5). An unknown value raises.
7. `rejections_by_label` reports counts for reasons 1, 2 and 3 per label, summing to the
   rejected total.
8. C-a:
   - a different `build_params` refuses without `--overwrite`;
   - identical params with `--resume` skip;
   - `--overwrite` rewrites.
9. All channels dropped gives the skip message and no files.

## Run commands (for the verifier, in order)

```bash
P=".venv/bin/python -m"
# 0. hash data/processed_continuous and data/processed_continuous_p17 (before)
# 1-3. builds
$P scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp harmonic intermediate --quality-source filtered --out-root mas/state/scratch/p19_filtered
$P scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp harmonic intermediate --quality-source raw  --out-root data/processed_continuous_p19_raw
$P scripts.build_windows --filter-mode continuous --subjects S01 S02 S03 S04 S05 --session OO --banks fbcca fbcsp harmonic intermediate --quality-source both --out-root data/processed_continuous_p19_both
# 4-7. flagship (5-class), base and harm banks, filtered (_p17 root) vs both
B="$P scripts.benchmarks.feature_based.benchmark_n_subjects --quality shared --cv-repeats 10 --classes 5"
$B --data-root data/processed_continuous_p17      --bank base --out-suffix p19_filtered_base
$B --data-root data/processed_continuous_p19_both --bank base --out-suffix p19_both_base
$B --data-root data/processed_continuous_p17      --bank harm --out-suffix p19_filtered_harm
$B --data-root data/processed_continuous_p19_both --bank harm --out-suffix p19_both_harm
# 8. hash both protected roots (after); compare p19_filtered with _p17; delete nothing
```

- Commands 4 and 6 must equal `reports/n_subjects_benchmark_p17_base_5class.csv` /
  `..._p17_harm_5class.csv` (same root, same arguments): this checks determinism.
- The builder gives the per-subject build time. P17 runs took about 5 min of benchmarks.
  The estimate is suite about 12 min, builds about 3 × (builder's estimate), benchmarks
  about 5 min, well inside `LOCAL_RUN_BUDGET_MIN` 120.
- If a subject is skipped under `raw`/`both` (settled point 5), the benchmark prints its
  `[-] Skipping` line and the report states it.


### Run-list additions from the pre-run audit (07_review.md 2928ddb, copied verbatim)


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

## Acceptance checks (for the verifier)

1. Rejection breakdown table per subject × source (filtered/raw/both):
   - n windows, valid, reasons 1/2/3 (3 split raw_gate/raw_guard), channels kept/dropped;
   - also by label (101–105, 201, 202), from each root's `windows_meta.json`.
2. `p19_filtered` equals _p17 file by file. The protected roots' hashes are unchanged.
3. Flagship 1.0 s and 2.0 s smoothed accuracy per subject, filtered vs both, base and harm,
   with the difference. Material = |Δ| ≥ max(2σ, 2 windows) (P17 rule).
4. Commands 4/6 reproduce the P17 CSVs.
5. Config default is `both`. `build_params.quality.source` is recorded in every new root.

## Sources

- `mas/03_ROADMAP.md` P19; `mas/01_DATA_SPEC.md` §4, §5.2; `mas/02_REQUIREMENTS.md` §3;
  `mas/05_PITFALLS.md` PF-05, PF-07, PF-14.
- `mas/04_REFERENCE_RESULTS.md` R-16; `mas/state/decisions.md` P17 C-a.

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
