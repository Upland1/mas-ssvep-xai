# P15 · 02 · Plan

Status: READY
Author: orchestrator
Reads: 00_assignment.md, mas/RULES.md, mas/02_REQUIREMENTS.md §2/§6 (`connectivity_gate_benchmark`, `gnn_benchmark` schemas), mas/04_REFERENCE_RESULTS.md R-1, R-8, R-14, R-15 and tolerances, mas/05_PITFALLS.md PF-01/03/04/28/30, decisions.md P08–P14 rows
Approved by Sebastian: n/a   Date:        (PLAN_APPROVAL: auto)

## Goal

Build per-window graph features (node power, edge coherence, edge phase), test whether
the edges add information over power + FBCCA with Shrinkage-LDA (the gate), then train a
small edge-gated GNN. Compare with R-14 and R-15.

## Data source

- Legacy 7-channel `data/processed/<S>/` (P02, OO), S01–S05, **stimulus windows only**
  (101–105).
- Gate: the P07 two-tier gate as in the flagship (`benchmark_n_subjects` path; vpp 5–120
  µV, std 1–35 µV, channel fail > 50 %). R-1 requires 200/196/197/197/200 clean windows.
- fs 250 feature axis (PF-04, labelled).
- FBCCA: the existing extractor with the flagship settings.
- Trial ids: pre-gate via `cv_utils.build_trial_ids` and the gate mask (PF-03).
- The cache `data/processed/<S>/graph_dataset.npz` is a NEW file. Existing legacy arrays
  are never modified; the verifier checks their hashes.

## Settled points (inferred; recorded in decisions.md)

1. **CV.**
   - Gate: `StratifiedGroupKFold(5, shuffle=True, random_state=42 + r)` over trial ids,
     r = 0..4.
   - GNN: the same splitter at random_state 42 + r, r = 0..2. Model, loader and dropout
     seeds are `1000·r + fold`.
   - Seeds are recorded per row.
2. **Metrics.** 1.0 s accuracy, plus 2.0 s accuracy with the legacy-folder `i % 5`
   smoothing (P11 decision) on the out-of-fold scores in clean-array order. Train
   accuracy (GNN) uses the un-augmented training fold in eval mode (PF-30). §6 schemas.
3. **Gate verdict.**
   - Responders are those from P14: S03, S04, S05.
   - "Edge features add ≥ 2 pp on average" is the cohort-mean Δ of the best edge-augmented
     Base set vs Base.
   - "In ≥ 2/3 of responders" means Δ ≥ 2 pp in at least 2 of S03/S04/S05.
   - Both conditions are required for a pass. Computed at k = 0, and reported at k = 30.
4. **GNN variants run.** `nodes+F` and `nodes+coh+F` (R-15) on all five subjects, 3
   repeats, 150 epochs, CPU (decisions P08: comparisons on one device). Other variants
   are not run.
5. **Multi-seed rule (decisions P11).** The 3 repeats are 3 seed bases on folds that also
   change with r. The reviewer pre-commits how the spread is judged against R-15.
6. **Parameter counts (R-8, exact).** If the literal reading of task 5 does not give
   5,150 / 5,534, the deep-learning builder documents the gap and may consult the
   original's class definition after the attempt (R11). The B004 precedent applies:
   counts are exact and layer choices follow the original.
7. **Outputs.**
   - `reports/connectivity_gate_benchmark.csv` and `reports/gnn_benchmark.csv`, with
     `.meta.txt`.
   - The sanity report `reports/graph_dataset_sanity.csv`.
   - Logs under `reports/logs/P15/`.
8. **Tests** never read generated or git-ignored files (P14 D-5).

## Work split

| Agent | Files (NEW / MODIFIED) | What | Roadmap task | Source |
|---|---|---|---|---|
| connectivity-stats | NEW `src/features/connectivity/connectivity_graph_features.py` | task 1 exactly, harmonic-major node layout and the R6 layout proof | P15.1 | [1] |
| connectivity-stats | NEW `scripts/connectivity/graph_modeling/build_graph_dataset.py` (+ `__init__`) | task 2, `--rebuild`, sanity report | P15.2 | [1] |
| connectivity-stats | NEW `scripts/connectivity/graph_modeling/benchmark_connectivity_gate.py` | task 3 + settled points 1–3; in-fold scaler/SelectKBest/Shrinkage-LDA (R2) | P15.3 | [1] |
| deep-learning (after connectivity-stats) | NEW `src/features/connectivity/graph_inputs.py`, `src/models/graph/__init__.py`, `connectivity_gnn.py`, `scripts/connectivity/graph_modeling/benchmark_gnn.py` | tasks 4–6 + settled points 1, 2, 4, 6 | P15.4–P15.6 | [1], R-8 |

## Methodological risks

| Rule | Risk | Prevention |
|---|---|---|
| R1 / PF-03 | leaky split, ids after the gate | reuse `cv_utils`; no-shared-trial test |
| R2 | scaler, SelectKBest or standardizer fitted on all windows | train-fold-only tests with a planted test-fold outlier |
| R6 | node/edge layouts (harmonic-major; upper-triangle order) | synthetic: a planted tone at one target in one channel lands in the expected (channel, feature) cell; a planted coupled pair lands in the expected upper-tri index |
| Phase | phasor is not unit-norm or the sum is taken over the wrong bins | test |gp| = 1 and a known phase lag |
| PF-28 | GNN seeds | determinism test |
| R-8 | parameter counts | exact count test |
| Cache | stale `graph_dataset.npz` reused after a code change | the meta stores a code hash or a `--rebuild` default in the verifier run |

## Tests required

| Test | Simulated input | Expected result | Tolerance | Source |
|---|---|---|---|---|
| node power layout | tone at 15 Hz in channel 2 | max in [2, idx(15 Hz, harmonic 1)] | exact | task 1, R6 |
| harmonic bins | tone at 2 × 10.91 Hz | 2nd-harmonic column | exact | task 1 |
| edge coherence | coupled pair (1, 4) at 20 Hz | edge (1, 4) band 20 Hz is the max; Welch 3 segments | | task 1 |
| edge phase | known lag | unit phasor equals (cos φ, sin φ) | 1e-6 | task 1 |
| dims | 7 channels | N 70, F 5, Ec 105, Ep 210, Base+Ec+Ep 390 | exact | task 3 |
| gate R2 | outlier in a test fold | scaler/selector unaffected | exact | R2 |
| gate split | trial ids | no shared ids | exact | R1 |
| gate verdict | constructed deltas | pass/fail per rule | exact | settled point 3 |
| standardizer | train/test | statistics from train only | exact | task 4 |
| variants | names | must start with `nodes`; dims | exact | task 4 |
| GNN | random input | output shape; counts 5,150 / 5,534 | exact | R-8 |
| edge gate | gate input zeros vs ones | messages scaled by sigmoid | 1e-6 | task 5 |
| determinism | same seeds | identical | exact | PF-28 |
| smoke | `--smoke-test` on a synthetic tree | runs, writes the schema | exact | task 6 |

## Run commands (for the verifier, in order)

```bash
.venv/bin/python -m scripts.connectivity.graph_modeling.build_graph_dataset --rebuild
.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_connectivity_gate --repeats 5 --k-select 0 30
.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_gnn --smoke-test
.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_gnn --repeats 3 --epochs 150 --device cpu
```

The builders confirm the flags and measure runtimes on one subject. If the total exceeds
120 min, the orchestrator issues a human-run request.

## Acceptance checks (for the verifier)

| Criterion (verbatim) | How it is checked | Reference |
|---|---|---|
| gate table = R-14 (Base+Ec best mean 77.6 %, gate does not pass) | `reports/connectivity_gate_benchmark.csv` per subject ±1.5 pp, mean ±1.0 pp, k = 0 and k = 30; the best set; the verdict | R-14 |
| GNN = R-15 (nodes+F ≈ nodes+coh+F; coherence edges do not help) | `reports/gnn_benchmark.csv` S02/S03/S05 ±5 pp per subject; the variant gap; the reviewer's pre-committed spread rule | R-15 |
| smoke test passes | exit 0 and schema | task 6 |
| (R-8, R-1) | parameter counts exact; graph dataset counts exact | R-8, R-1 |

The reviewer pre-commits the exact windows in the pre-run audit.

## Sources

1. `mas/03_ROADMAP.md` P15 (opened in this run).
2. `mas/04_REFERENCE_RESULTS.md` R-1, R-8, R-14, R-15; `mas/02_REQUIREMENTS.md` §6 lines 212–213 (opened in this run).

## Questions
