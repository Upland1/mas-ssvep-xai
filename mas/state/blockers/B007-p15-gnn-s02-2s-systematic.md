# B007 — P15: one R-15 GNN cell systematically below tolerance, plus a sign flip of the coherence-edge Δ

Status: RESOLVED 2026-10-27 — Sebastian: "Accept as documented deviations for B007" (option 1)
Raised by: orchestrator, 2026-10-27
Phase: P15-graph-gnn (branch `phase/P15-graph-gnn`, verify commit 87ed7af, run at 2392299)

## What happened

Sources: `mas/state/phases/P15-graph-gnn/06_verify.md`, `reports/gnn_benchmark.csv`, `reports/connectivity_gate_benchmark.csv`, `mas/state/scratch/p15_verify.out`.

**Met:**
- **R-14 gate (A1):** reproduced. All 45 cells are within 0.06 pp. Base+Ec is best at 77.57. The gate does not pass, for the right reason: 0/3 responders gain ≥ 2 pp, while S01 +16.30 and S02 +3.16.
- **Exact counts (A6):** R-8 counts 5,150 / 5,534; R-1 counts 200/196/197/197/200.
- **Smoke test and run hygiene (A7, A8):** pass. Legacy arrays are unchanged.

**R-15 GNN (S02/S03/S05; reviewer windows A2–A4, pre-committed):**
- 11 of 12 graded subject cells are inside ±5 pp, including both variants at 1.0 s.
- **Systematic miss:** nodes+F S02 at 2.0 s is 37.07 vs 46.1 (Δ −9.03).
  - All 3 repeats are below: 37.76 / 34.18 / 39.29.
  - The gap is 3.45 × SD (2.62), so per A3 it is "not seed variance".
- **Unexplained:** the nodes+F cohort at 2.0 s is 71.27, 0.16 pp outside its window [71.43, 77.43]. It is driven by the S02 cell above.
- **A4 claims:**
  - "nodes+F ≈ nodes+coh+F" holds: cohort Δ +1.07, every subject |Δ| ≤ 5.
  - "Coherence edges do not help" holds: 1/3 subjects with Δ ≥ 2.
  - The sign of the cohort Δ flips relative to R-15 (+1.07 vs −0.40). All three per-repeat Δ are positive (+0.50 / +1.18 / +1.52), so the flip is not seed noise under A4.
- **Train accuracy (diagnostic only):** above R-15 in all 6 cells and outside ±5 pp in 4 (e.g. nodes+F S02 75.43 vs 56.4).
  - The original measures train accuracy the same way (eval mode, training fold; verified by the reviewer in the R11 check), so this is not a definition difference.
  - Candidates, not testable here: the original ran on CUDA by default, while this run used CPU and no CUDA device is available; a different random-number stream; single-split variance.
- **R11:** the original GNN class was consulted once (count fix, `bias=False`). Nothing else was adopted.

## Decision needed

How should P15 treat the S02 2.0 s miss, the cohort 2.0 s cell it drives, and the sign flip of the small coherence-edge Δ?

## Options

1. **Accept as documented deviations (recommended).** The reviewer signs explanations in the results review. The report states:
   - the gate (R-14) is reproduced exactly;
   - both GNN claims of the roadmap acceptance hold;
   - one S02 2.0 s cell is systematically low (not seed variance, cause not established);
   - the coherence-edge Δ is +1.07 instead of −0.40 but stays inside "≈" and "does not help";
   - train accuracy is consistently higher than the original's.

   The verifier then restates PASS with these deviations, as in P06/P07/P11. P15 merges.
2. **Diagnose first.** For example, run the GNN on a CUDA device (Colab or a local GPU; a human run) to test the device hypothesis, as a diagnostic only. Reported numbers stay CPU.
3. **Keep P15 open** and mark the GNN comparison "not reproduced". This blocks P16 onward, because phases are scheduled sequentially.

## Recommendation

Option 1. The purpose of P15 is the gate and whether coherence edges help the GNN. The gate reproduces exactly and both GNN claims hold. The misses are one 2.0 s cell of the weakest subject and the sign of a small Δ between two variants of equal accuracy. Option 2 is worth doing later if Sebastian wants the train-accuracy pattern explained before Era C's GNN work (P21–P23).
