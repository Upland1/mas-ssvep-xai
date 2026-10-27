# P15 · 06 · Verification

Status: READY
Reads: 00_assignment.md (acceptance), 02_plan.md, 05_run.md, 07_review.md (A1-A8), the phase branch
Clean checkout: main repository at HEAD 2392299 (porcelain empty before every command; the run and the verification are the same execution)

All arithmetic: `.venv/bin/python mas/state/scratch/p15_verify.py`, output in `mas/state/scratch/p15_verify.out`. Source CSVs: `reports/connectivity_gate_benchmark.csv` (gate), `reports/gnn_benchmark.csv` (GNN). Data source for every number: legacy 7-channel OO folders, stimulus windows, two-tier gate, fs 250 label, per-window features; trial ids approximate on S02 and S04 (P11 D-2). 2.0 s columns use the legacy i%5 smoothing (decisions P11 rows 103-104; the era-matrix R8 reading is open, P11 C1).

## Tests on the clean checkout

`.venv/bin/python -m pytest tests -o addopts="" -q` gave `948 passed, 21 warnings in 432.56s`, EXIT 0 (`reports/logs/P15/pytest_full.log`).

## A8 run hygiene

- Legacy-array hash before: `6120eb9ce5770a71c16016cfb02830472d9e44672ff4a7a150bb48c8821d559e`; after: `6120eb9ce5770a71c16016cfb02830472d9e44672ff4a7a150bb48c8821d559e` (`reports/logs/P15/a8_hash_before.txt`, `a8_hash_after.txt`). Identical. Met.
- `git diff --stat 1d1bdca HEAD -- src scripts tests configs` and the same against 73a7e9e: empty (0 lines). Met.
- Order of execution: build, gate, smoke, GNN. The gate runs before the GNN. Met.

## Acceptance (A1-A7)

### A1 R-14 gate table (`reports/connectivity_gate_benchmark.csv`, mean of 5 repeats, 1.0 s): MET

- k=0: all 45 subject x set cells are within ±1.5 pp of R-14 (largest |Δ| 0.06 pp, `p15_verify.out`). The 9 cohort means are within ±1.0 pp (largest |Δ| 0.06 pp, Base+Ep 73.44 vs 73.5). 0 cells to explain.
- k=30 cohort means vs R-14: Base 74.02 (74.0), Base+Ec 77.53 (77.5), Base+Ec+Ep 77.46 (77.5), Base+Ep 76.03 (76.0), N 64.88 (64.9), Ec 46.73 (46.7), Ep 35.52 (35.5), Ec+Ep 46.00 (46.0). All within 0.04 pp. F at k=30 equals k=0 (True).
- Best set: at k=0 the best of nine and the best edge-augmented set is Base+Ec, mean 77.57, inside [76.6, 78.6]. At k=30 the best edge-augmented set is Base+Ec (77.53; Base+Ec+Ep 77.46).
- Verdict k=0 (`cmd2_gate.log`): Base+Ec Δ vs Base S01 +16.30, S02 +3.16, S03 +1.22, S04 +0.10, S05 -1.70; cohort mean +3.82; responders with Δ ≥ 2 pp 0/3; "gate does NOT pass" because of the responder criterion (cohort Δ ≥ 2 pp, S01 and S02 ≥ 2 pp). Matches R-14 and the reviewer's wording.
- Verdict k=30: Δ S01 +10.30, S02 +8.06, S03 -0.91, S04 +0.10, S05 +0.00; cohort +3.51; responders 0/3; does NOT pass, same reason.

### A2/A3 R-15 GNN cells (`reports/gnn_benchmark.csv`, mean of 3 repeats; ±5 pp per subject, ±3 pp cohort)

Within window (obtained, R-15 in brackets): nodes+F S02 1.0 s 34.18 (38.6); S03 76.82 (77.8) / 82.57 (82.2); S05 89.50 (90.0) / 94.17 (95.0). nodes+coh+F S02 36.22 (37.2) / 39.80 (40.1); S03 76.48 (77.5) / 83.59 (82.9); S05 91.00 (90.5) / 95.17 (95.3). S01 and S04 have no reference (1.0 / 2.0 s): nodes+F S01 34.00 / 37.67, S04 87.14 / 92.39; nodes+coh+F S01 36.50 / 37.67, S04 88.66 / 93.23.

Out of window (1 of 12 graded subject cells):
- **nodes+F S02 2.0 s**: obtained 37.07 vs R-15 46.1, Δ -9.03 (window [41.1, 51.1]). Repeats 37.76, 34.18, 39.29 (SD 2.62). R-15 is above all three repeats, so A3(b) applies: systematic, "not reproduced within tolerance, cause not established". The gap is 3.45 × SD (> 3), so seed variance is not the cause. It goes to Sebastian as a deviation (B006 precedent).

Cohort (S02/S03/S05):
- nodes+F 1.0 s 66.83 vs 68.80 (Δ -1.97), nodes+coh+F 1.0 s 67.90 vs 68.40 (Δ -0.50) and 2.0 s 72.85 vs 72.77 (Δ +0.08) are in window.
- **nodes+F 2.0 s cohort**: 71.27 vs 74.43 (Δ -3.16, window [71.43, 77.43]), outside by 0.16 pp. Its driving cell is S02 2.0 s, which is systematic under A3(b), so A3(c) does not explain it.

Sign tally of the 12 graded differences (obtained minus R-15): 9 negative, 3 positive. Not 11-12, so not one-sided under the A3 rule.

### A4 nodes+F ≈ nodes+coh+F; coherence edges do not help (3-repeat means, 1.0 s)

Δ (coh minus base): S01 +2.50, S02 +2.04, S03 -0.34, S04 +1.52, S05 +1.50; cohort (S02/S03/S05) +1.07; cohort (5 subjects) +1.45.
- ≈: |Δ| ≤ 5 on S02/S03/S05 and |cohort Δ| 1.07 ≤ 3. Met.
- Do not help: cohort Δ 1.07 < 2.0 and 1 of 3 subjects (S02, +2.04) has Δ ≥ 2.0, fewer than 2. Met. The five-subject version is cohort +1.45 with 2 of 5 (S01, S02) at Δ ≥ 2.0; neither reading reaches the gate threshold. The three-subject reading is graded.
- 2.0 s Δ (reported only): S01 0.00, S02 +2.72, S03 +1.02, S04 +0.85, S05 +1.00; cohort (3) +1.58. R-15: -6.0 / +0.7 / +0.3; cohort -1.67.
- **Sign-flip clause: not met.** Cohort Δ1.0 s is +1.07 (R-15 -0.40, a flip). Per-repeat cohort (3) Δ: repeat 0 +0.50, repeat 1 +1.18, repeat 2 +1.52. Zero is not within [0.50, 1.52], so the flip is not explained as noise and must be explained.

### A5 train column (diagnostic only, does not decide)

Obtained vs R-15 (window ±5 pp): nodes+F S02 75.43 vs 56.4 (+19.03, out), S03 95.31 vs 86.8 (+8.51, out), S05 99.75 vs 96.1 (+3.65). nodes+coh+F S02 78.02 vs 57.7 (+20.32, out), S03 96.11 vs 87.8 (+8.31, out), S05 100.00 vs 96.6 (+3.40). Positive on all six cells, outside the window on four (SDs 0.25 to 1.48, so A3(b) systematic). To record in decisions.md as "not reproduced within tolerance, cause not established (candidates: device, RNG stream, split variance)". Cohort train: nodes+F 90.16 vs 79.77, nodes+coh+F 91.38 vs 80.70. The excess is on all three subjects and both variants: a systematic difference, open for Sebastian (non-blocking). The over/under-fitting hints in `cmd4_gnn.log` flag OVERFITTING on S01, S02 and S03 (gaps +36.5 to +41.8, +18.5, +19.6).

### A6 exact: MET

- Parameter counts: meta line `params: nodes+F=5150, nodes+coh+F=5534` (`reports/gnn_benchmark.meta.txt`).
- R-1 (`cmd1_build.log`): clean windows S01 200, S02 196, S03 197, S04 197, S05 200; 7 channels kept (PO3 POz PO4 PO8 O1 Oz O2) for all; `trial_ids_approximate` True only for S02 and S04; every subject built fresh (`[+]`), 0 occurrences of "cache valid".

### A7 smoke: MET

Exit 0 (`cmd3_smoke.log`); header `SMOKE TEST: 3 epochs, 1 repeat`; `reports/gnn_benchmark_smoke.csv` has columns `variant,repeat,acc_1s,acc_2s,train_acc,subject` and 2 rows (nodes+F, nodes+coh+F; repeat 0; S01). `reports/gnn_benchmark.csv` did not exist after step 3 (only the smoke CSV was listed) and was created by step 4.

## Numbers in the handoffs vs logs

The gate k=0 and k=30 tables and verdicts in `cmd2_gate.log` agree with the CSV recomputation (`p15_verify.out`). The GNN summary table in `cmd4_gnn.log` agrees with the CSV means. Builder handoff numbers were not traced beyond these.

## Sources spot-check

Opened `mas/04_REFERENCE_RESULTS.md` (R-8, R-14, R-15) and `07_review.md`; the reference values used above are as printed there.

## Reference consultations check

`mas/state/scratch/reference_access.log` has 40 lines. The P15 deep-learning entries are lines 32-33, listed in the Round 2 handoff row. The reviewer's lines 34-40 are listed in 07_review.md. No access was added after line 40, and the verifier opened nothing under `reference/`. No unlisted access.

## Reasons (FAIL)

1. A2/A3: nodes+F S02 2.0 s is 37.07 vs R-15 46.1 (Δ -9.03, outside ±5 pp). R-15 lies above all three repeats (37.76, 34.18, 39.29), so it is systematic under A3(b), with the gap 3.45 × SD (2.62). Not reproduced within tolerance, cause not established; to Sebastian as a deviation.
2. A2/A3(c): the nodes+F cohort 2.0 s is 71.27 vs 74.43 (Δ -3.16, window [71.43, 77.43]). Its driving cell (reason 1) is not explained under A3(a), so the cohort cell is not explained.
3. A4 sign-flip clause: cohort Δ1.0 s is +1.07 vs R-15 -0.40. The three per-repeat cohort Δ (+0.50, +1.18, +1.52) are all positive, so 0 is outside their range and the flip is unexplained. The substantive A4 claims (≈ and "do not help") are met on the thresholds.
4. A5 (diagnostic, not a FAIL reason by itself): train accuracy exceeds R-15 on all six cells, outside ±5 pp on four.

Everything else is met: tests 948 passed; A1 (45 cells, 9 means, 8 k=30 means, best set, verdict and its reason), A6, A7 and A8.

Verdict: FAIL
