# P18 · 06 · Verification

Status: READY
Author: verifier
Reads: 00_assignment.md (acceptance), 02_plan.md (V0-V8), 05_run.md, the phase branch
Clean checkout: `mas/state/scratch/verify/P18` @ 32738ccaf768a087073942e680ee5e0f6fda2891 (tests only; worktree removed). Commands 1-5 ran from the repository root at the same HEAD (clean tree).

Verdict: PASS

## Tests on the clean checkout

`.venv/bin/python -m pytest tests -o addopts="" -q` -> `1204 passed, 1 skipped, 22 warnings in 749.44s (0:12:29)`, exit 0 (`reports/logs/P18/01_pytest.log`).

## Pre-committed checks V0-V8

| Check | Evidence | Met? |
|---|---|---|
| V0 budget | cumulative 49.9 min after command 3 (limit 69); commands 4-5 run; total 92.5 min (limit 120); no human-run request (`05_run.md`) | yes |
| V1 pre-state | `find reports -name "*p18*" \| wc -l` = 0 before; root hash before and after: `c59c94b8ac90a77f57148f057698411f97690ec1174b1202237b37624144a54e`, 65 files both times (`00_hash_before.txt`, `99_hash_after.txt`) | yes |
| V2 columns, npz | both summaries: 33 columns equal to the 15 pre-P18 + 18 listed (exact order), 100 rows, fs 256.0 in all; 20 npz per run, each with `channels_kept` and `stim/base/diff/p/fdr/nbs_<c>` for 101-105, `nbs_<c>` bool (C, C), symmetric, False diagonal, C = n_channels of the summary row, `sum/2 == nbs_n_sig_edges` for all 100 cells; pairwise CSVs: 20 columns, 50 rows per method, 150 total (`11_check_cohort.txt`, `10_check_pairwise.txt`) | yes |
| V3 settled point 6 | `p18_nbs_p200` vs `v2cont`, sorted by (subject, method, condition): 15 columns, max float \|d\| = 0, NaN aligned, strings equal; `_details.csv` 17/17 shared columns, max \|d\| = 0; `stim/base/diff/p/fdr` arrays, 500 comparisons (20 files x 5 conditions x 5 keys), `np.array_equal(equal_nan=True)` all True | yes |
| V4 tables | graph-size 100 rows and sweep 400 rows in both runs; `possible_edges_nbs` 21 (S01/S03/S04), 28 (S02/S05) for all four methods incl. PDC; `total_edges_fdr` 21/28 and 42/56 for PDC; thresholds 1.5/2/2.5/3; "Graph sizes:" and "NBS threshold sweep:" printed in logs 02 and 03 | yes |
| V5 consistency | all 100 rows of both runs: `nbs_size_z2 == nbs_max_size`, `nbs_p_z2 == nbs_p`, `nbs_significant == (nbs_p < 0.05)`, `fraction x possible == max_size`, p >= 1/(n+1) (n = 200 / 1000), `nbs_n_sig_edges == 0` when not significant else >= max_size, npz sum/2 == `nbs_n_sig_edges`; sweep `max_size` non-increasing with threshold in every cell; 0 violations | yes |
| V6 flips | file has 17 rows; recomputed set of cells where A-FDR (>= 1 edge), B (`p_one_tailed` < 0.05) or A-NBS (`nbs_p` < 0.05) differ between the two summaries = 17 cells, identical set | yes |
| V7 pairwise | `nbs_p` min 0.003996 / 0.000999 / 0.000999 (coherence / plv / wpli) >= 1/1001; `n_edges` 21/28 by subject; `n_edges_nbs == 0` whenever `nbs_p >= 0.05` and >= `nbs_max_size` otherwise; all 13 summary lines of command 5 (`==` headers, p_mag, responders, non_responders, split-half) appear verbatim in command 4's log | yes |
| V8 | no hand edits; every output written by the run commands; verification scripts were read-only and their stdout is kept under `reports/logs/P18/` | yes |
| R11 / regression | `reference_access.log` has 40 lines before and after the run (no P18 access); no raw recording was opened by the verifier | yes |

## Key numbers (verbatim from `11_check_cohort.txt`, `12_directions.txt`, `10_check_pairwise.txt`; no interpretation)

Cohort, 1000 permutations (`reports/connectivity_cohort_summary_p18_nbs.csv`), cells per subject over 20 cells (4 methods x 5 conditions):

| | S01 | S02 | S03 | S04 | S05 | total /100 |
|---|---|---|---|---|---|---|
| A-FDR (>= 1 edge) | 4 | 0 | 16 | 20 | 8 | 48 |
| A-NBS (`nbs_p` < 0.05) | 1 | 0 | 16 | 18 | 8 | 43 |
| B (global p < 0.05) | 1 | 1 | 12 | 11 | 7 | 32 |

By method (coherence / pdc / plv / wpli): A-FDR 13 / 14 / 8 / 13; A-NBS 12 / 11 / 9 / 11; B 8 / 9 / 4 / 11. A-FDR and B 27, A-NBS and B 26, A-FDR and A-NBS 39.

At 200 permutations: A-FDR 36 (S01 0, S02 0, S03 13, S04 17, S05 6), A-NBS 45 (2, 1, 17, 17, 8), B 32 (1, 1, 12, 11, 7); A-FDR and B 25.

2 x 2 A-FDR (rows) x A-NBS (columns) at 1000, [FDR-/NBS-, FDR-/NBS+; FDR+/NBS-, FDR+/NBS+]: coherence [12, 0; 1, 12]; pdc [9, 2; 5, 9]; plv [16, 1; 0, 8]; wpli [11, 1; 3, 10]. Disagreeing cells (13) listed in `12_directions.txt`.

Flips 200 vs 1000 (`connectivity_cohort_flips_p18_nbs_p200_vs_p18_nbs.csv`, 17 rows): A-FDR 14 (coherence 1, plv 3, wpli 4, pdc 6), B 0, A-NBS 6 (pdc 2, plv 2, wpli 2). All 6 A-NBS flips have a different `nbs_max_size` between the runs (class threshold-boundary by rule F2; 0 p-resolution). Of the 14 A-FDR flips, 13 go 0 -> >= 1 edge (counts 1 to 6) and 1 goes 3 -> 0 (S05 plv 101). Cell list in `11_check_cohort.txt`. All flips are inconclusive (R7).

Pairwise NBS (two-tailed |z| > 2, 1000 permutations), command 4 and `--summary-only` lines: cells with NBS p < 0.05 of 50: coherence 8, plv 14, wpli 6; responders (30 cells) coherence 1, plv 8, wpli 0; non-responders (20 cells) coherence 7, plv 6, wpli 6. p_mag < 0.05: 11 / 8 / 7. 2 x 2 NBS x `p_mag` (rows NBS-/NBS+, columns p_mag-/p_mag+): coherence [36, 6; 3, 5]; plv [33, 3; 9, 5]; wpli [41, 3; 2, 4]. Borderline cells (0.036 <= p <= 0.064 on `nbs_p`, `p_mag` or `p_pat`): 6 / 8 / 5. The `p_mag_centred` agreement table (R4) is not computed here (the column is not in the tests CSV).

## A-priori directions (values only; the reviewer interprets)

- P1 sweep non-increasing: held in all cells (V5).
- P2 A-NBS cells >= A-FDR cells at 1000: A-NBS 43, A-FDR 48 (not met as stated; at 200: 45 vs 36).
- P3 cells with >= 3 FDR edges at 1000: 37; A-NBS in 36 (97.3 %); the exception is S04 pdc 102 (5 FDR edges, `nbs_max_size` 1, `nbs_p` 0.3506, global p 0.0679).
- P4 non-responders S01/S02: A-NBS 1 of 40 cells (S01 wpli 104, size 4, p 0.034965); A-FDR 4 of 40; responders S03-S05: A-NBS 42 of 60. Mean largest component (% of possible edges) S01 2.6, S02 1.6, S03 38.8, S04 32.1, S05 12.1.
- P5 mean `nbs_max_size`, B negative vs positive: coherence 2.0 vs 14.0; pdc 1.81 vs 4.33; plv 1.0 vs 8.25; wpli 1.36 vs 9.0.
- P6 mean largest component % by method: coherence 26.3, pdc 12.1, plv 10.1, wpli 21.3. PDC smaller than the same cell of coherence in 13 of 25 subject x frequency cells, plv 4, wpli 11 (equal 4 / 6 / 5). PDC A-NBS 11 cells, PDC A-FDR 14.
- P7 mean largest component % at 10.91 Hz (104) and 8.57 Hz (105): coherence 14.0 / 16.9, plv 8.6 / 5.7, wpli 23.1 / 26.9, pdc 10.0 / 9.8; A-NBS counts 104 / 105: coherence 1 / 2, plv 1 / 2, wpli 3 / 3, pdc 2 / 2. One-tailed test only.
- P8: NBS x `p_mag` tables above; `p_mag_centred` table not produced in this verification.

## Numbers in the handoffs vs logs

All numbers above come from the CSVs and logs under `reports/` and `reports/logs/P18/` (script outputs `10_`-`12_`); runtimes from the log headers/footers. The builder's 03/04 numbers were not used.

## Sources spot-check

None needed from this run (no external source cited by the verifier; R10).

## Reference consultations check

`mas/state/scratch/reference_access.log`: 40 lines before and after; no P18 access. 03/04 declare no consultation. No unlisted accesses.

## Reasons (if FAIL)

None.

## Questions
