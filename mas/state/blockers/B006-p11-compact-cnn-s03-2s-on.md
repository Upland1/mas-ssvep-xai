# B006 — P11: one R-9b cell systematically outside tolerance (Compact-CNN S03 2.0 s ON)

Status: OPEN (blocking P11 gate)
Raised by: orchestrator, 2026-10-26
Phase: P11-trial-leakage-fix (branch `phase/P11-trial-leakage-fix`, HEAD after 909b67a)

## What happened

- Every classical acceptance check of P11 passes exactly (`06_verify.md`, `07_review.md`):
  - R-6 is reproduced to 0.00 pp on every cell (mean 79.28 / 82.61).
  - The leak is −4.06 / −4.96 pp (R-6: −4.05 / −4.96).
  - The legacy re-run reproduces R-5, R-4 and R-3.
  - Approximate trial ids occur on S02 and S04 only.
  - Provenance is clean.
- The network A/B (R-9b, pre-committed window P4 = ±5 pp per subject, ±3 pp cohort) had 14 cells outside the window on seed 42.
- The deep-learning investigation (fix round 2) found no bug:
  - the network folds, ids and mask are identical to the classical path;
  - the leaky mode still reproduces P10;
  - the init seed alone moves EEGNet S03 by about 17 pp.
- The reviewer pre-committed rule D-4 (decisions.md): run two extra seed bases on the same folds. A cell is explained if one base lands inside the window. All three runs outside on the same side counts as **systematic, which means REJECT plus a blocker for Sebastian.**
- Result (`06_verify.md` Round 2b, `reports/diagnostics/p11_seed_spread_*.csv`, `mas/state/scratch/d4_rule.out`): 13 of 14 cells are explained, including every cohort cell. The one systematic cell:

| Cell | Seed 42 | Base 1042 | Base 2042 | R-9b | Window (±5 pp) |
|---|---|---|---|---|---|
| Compact-CNN S03 2.0 s ON | 65.48 (129/197) | 64.47 | 65.48 | 71.07 | 66.07–76.07 |

The best run is 0.59 pp below the lower edge (`python -c "print(round(66.07-65.48,2))"`).
The edge corresponds to 130.16 of 197 windows (`python -c "print(round(66.07*197/100,2))"`), so the best run is about one window short. The 1.0 s cell for the same subject and arm is explained (57.87 / 59.90 / 59.39), and the A/B sign rule holds for all three models.

## Decision needed

How should P11 treat this single cell?

## Options

1. **Accept as a documented deviation (recommended).**
   - The scientific reviewer signs an explanation in the report: one Compact-CNN 2.0 s cell, about one window below the ±5 pp edge on all three seeds, with all cohort cells and the same cell's 1.0 s value explained.
   - The miss is recorded in decisions.md as D-x and stated in the P11 report. The verifier then restates PASS with D-x, as in P06 and P07.
   - P11 then closes, and P12 starts.
2. **More diagnosis first.** For example, run the original's RNG stream (seeds 43–47, unseeded loader; found in the R11 consultation) as a *diagnostic only* on Compact-CNN S03. Reported numbers stay seed 42. Cost: about 15 min of runs plus a review round. It may still not move the cell, and it edges toward tuning toward the reference (golden rule 5).
3. **Keep P11 open** and treat the Compact-CNN 2.0 s result as "not reproduced" without a deviation. This blocks P12 onwards, because SCHEDULING is sequential.

## Recommendation

Option 1. The miss is one smoothed cell of one diagnostic network, about one window. Every acceptance item tied to the phase's purpose (the leak fix and R-6) is exact. The tolerance table allows a signed explanation.

## Also open for Sebastian (non-blocking)

- Era-matrix R8 row reading (decisions.md, P11 C1 row).
- B003 (cohort beyond S05, before P20).
- P06 D-1 and P07 D-1 questions.
- A detached scratch worktree `wt829` left by the deep-learning builder, safe to remove with `git worktree remove --force`.
