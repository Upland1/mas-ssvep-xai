# P15 · 00 · Assignment — Per-window graphs, the connectivity gate, and a GNN

Status: READY
Author: orchestrator
Branch: phase/P15-graph-gnn (from main @ a5e0d19, tag p14-done)
Era: B. Legacy behaviours required (`team.yaml`): **R3** (per-window features on the raw legacy windows; the in-window Welch/FFT features are window-level by design, and no continuous filtering exists before P16), and **fs250** (the feature frequency axis, PF-04, labelled). These are enforced: R1 (StratifiedGroupKFold over trial ids), R2 (in-fold scaler, SelectKBest and standardizer), R8 (2.0 s smoothing on legacy folders uses the `i % 5` rule; P11 decision), R6 (feature layouts proven) and R9. The per-script P07 gate continues (R5 from P16). Trial ids on S02/S04 are approximate (P11 D-2).
Owners (agents): connectivity-stats (Connectivity & Stats); deep-learning (Deep Learning); scientific-reviewer; verifier
Depends on: P14 (passed; merged a5e0d19)

## Origin (verbatim from mas/03_ROADMAP.md)

**Origin.** Professor's assignment: model connectivity with graph neural networks to
classify the stimulation frequency. Plan: first test whether connectivity features add
information to power features (a "gate"), then a GNN.
**Depends on:** P14. **Owners:** Connectivity & Stats, Deep Learning, Verifier.

## Tasks (verbatim from mas/03_ROADMAP.md)

1. `src/features/connectivity/connectivity_graph_features.py`:
   `node_band_power(windows, fs)` = log10 Hann-FFT power per channel at the 5 targets
   and 2nd harmonics, ±1 Hz bins (nearest bin if none), harmonic-major → `(n, C, 10)`;
   `edge_coherence` = in-window Welch (nperseg 128, step 64 → 3 Hann segments for 256
   samples), MSC band-averaged → `(n, C, C, 5)`; `edge_phase` = unit phasor
   (cos, sin) of the full-window cross-spectrum summed over band bins →
   `(n, C, C, 5, 2)`; `upper_tri_flat`; `build_graph_features`.
2. `scripts/connectivity/graph_modeling/build_graph_dataset.py [--rebuild]`: per
   subject, quality gate + FBCCA + graph features + trial ids → cached
   `data/processed/<S>/graph_dataset.npz` (`node, edge_coh, edge_phase, X_fbcca, y,
   trial_ids, channels_kept`); sanity report of own-band minus other-class differences
   for node power, coherence and phase consistency.
3. `benchmark_connectivity_gate.py --repeats 5 --k-select 0 30`: feature sets `N`
   (70), `F` (5), `N+F` (= Base, 75), `Ec` (105), `Ep` (210), `Ec+Ep`, `Base+Ec` (180),
   `Base+Ep`, `Base+Ec+Ep` (390); pipeline scaler → optional in-fold `SelectKBest(f_classif,
   k)` → Shrinkage-LDA; grouped CV repeats with seeds 42+r; per-subject deltas vs Base;
   gate verdict: **pass if edge features add ≥ 2 pp on average and in ≥ 2/3 of
   responders** (descriptive heuristic).
4. `src/features/connectivity/graph_inputs.py`: variants `nodes[+coh][+phase][+F]`
   (must start with `nodes`), `build_inputs`, train-fold-only `fit_standardizer` /
   `apply_standardizer` / `standardize_fold`.
5. `src/models/graph/connectivity_gnn.py::ConnectivityGNN(n_nodes, n_node_feats,
   n_edge_feats=0, n_graph_feats=0, n_classes=5, hidden=32, n_layers=2, dropout=0.3)`:
   node encoder Linear+ELU + learned channel embedding (init N(0, 0.1)); `EdgeGatedLayer`
   = residual `LayerNorm(h + Dropout(ELU(W_self h + agg)))` where `agg` averages
   messages `W_msg h_j` from the other nodes, optionally gated by `sigmoid(Linear(e_ij))`;
   readout = concat(mean, max) over nodes → dropout → concat graph features (FBCCA) →
   Linear.
6. `benchmark_gnn.py [--smoke-test] --repeats 3 --epochs 150`: AdamW 1e-3/1e-2,
   cosine (eta_min 1e-5), label smoothing 0.05, batch 32, seeds `1000·r + fold`;
   prints LDA gate rows alongside and a train-accuracy diagnostic with
   over/under-fitting hints.

## Run (verbatim)

The roadmap gives no separate run line. Commands: `02_plan.md`.

## Outputs (verbatim, mas/phases.yaml)

`connectivity_graph_features.py`, `graph_inputs.py`, `src/models/graph/connectivity_gnn.py`, `build_graph_dataset.py`, `benchmark_connectivity_gate.py`, `benchmark_gnn.py`

## Acceptance (verbatim)

Acceptance: gate table = **R-14** (Base+Ec best mean 77.6 %, gate does **not** pass);
GNN = **R-15** (nodes+F ≈ nodes+coh+F; coherence edges do not help); smoke test passes.

## Pitfalls and references that apply

| Id | Where | Why it matters here |
|---|---|---|
| R-14 | mas/04_REFERENCE_RESULTS.md | gate table; deterministic classical tolerance per subject ±1.5 pp, mean ±1.0 pp; the verdict must match |
| R-15 | mas/04_REFERENCE_RESULTS.md | GNN, mean of 3 repeats; NN tolerance per subject ±5 pp, cohort ±3 pp; the original ran S02, S03, S05 only, so run all subjects and compare those three |
| R-8 | mas/04_REFERENCE_RESULTS.md | ConnectivityGNN parameter counts nodes+F 5,150, nodes+coh+F 5,534 — exact |
| R-1 | mas/04_REFERENCE_RESULTS.md | graph datasets 200/196/197/197/200 clean stimulus windows — exact |
| PF-01, PF-03 | mas/05_PITFALLS.md | grouped CV over pre-gate trial ids |
| PF-04 | mas/05_PITFALLS.md | fs 250 legacy axis |
| PF-28, PF-30 | mas/05_PITFALLS.md | seeds per fold; train accuracy next to test |
| R1, R2, R6, R8, R9 | mas/RULES.md | see Era |
| decisions.md P11 | | multi-seed rule for networks compared with a reference: ≥ 3 seed bases on fixed folds, judged by a pre-committed spread rule (the GNN's 3 repeats are seed bases); i%5 smoothing on legacy |
| decisions.md P13 D-4, P14 D-5 | | pre-commit seed-base diagnostics where counts are graded; tests must not read generated, git-ignored files |

## Assignment per agent

| Agent | Tasks | Handoff file |
|---|---|---|
| connectivity-stats | P15.1–P15.3 | `03_changes_connectivity-stats.md` |
| deep-learning | P15.4–P15.6 | `03_changes_deep-learning.md` |
| synthetic-tester | known-answer tests | `04_tests.md` |
| scientific-reviewer | pre-run audit; results review | `07_review.md` |
| verifier | run + acceptance | `05_run.md`, `06_verify.md` |
| scribe | report | `mas/state/reports/P15.md` |

## Questions
<!-- receivers append: ACK <agent> <YYYY-MM-DD>, then questions; answers appended, never deleted -->
