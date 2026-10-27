# P15 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Reads: 00_assignment.md, 02_plan.md, mas/RULES.md, mas/03_ROADMAP.md P15, mas/04_REFERENCE_RESULTS.md R-1/R-14, PF-01/03/04
Branch: phase/P15-graph-gnn
Commit(s): d9c8821 (features + loader), 932c882 (build_graph_dataset), 3bbd449 (gate), 74745a3 (tests); handoff commit follows

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/connectivity/connectivity_graph_features.py` | NEW | `node_band_power`, `edge_coherence`, `edge_phase`, `upper_tri_flat`, `build_graph_features`, `band_bins`; layouts documented (R6) | P15.1 | [1], R6, PF-04 |
| `src/features/connectivity/graph_dataset.py` | NEW | cache I/O and the loader for the GNN builder (`load_graph_dataset`, `GraphDataset`, `discover_graph_subjects`, `code_fingerprint`, `StaleGraphDataset`) | P15.2 | [1], plan "Cache" risk |
| `scripts/connectivity/graph_modeling/build_graph_dataset.py` | NEW | gate + FBCCA (via `prepare_subject`) + graph features + pre-gate trial ids -> `<data-root>/<S>/graph_dataset.npz`; sanity CSV | P15.2 | [1], R-1, PF-03 |
| `scripts/connectivity/graph_modeling/benchmark_connectivity_gate.py` | NEW | nine feature sets, in-fold scaler / SelectKBest / Shrinkage-LDA, grouped CV 42+r, verdict | P15.3 | [1], R-14, R1, R2 |
| `tests/test_p15_graph_features.py` | NEW | 17 builder tests for my rows (layouts, cache, pre-gate ids, R2, split, verdict, smoke) | P15.1-3 | plan "Tests required" |

`scripts/connectivity/graph_modeling/__init__.py` already existed. No existing file was modified; legacy arrays are never opened for writing (test: hashes unchanged).

## Legacy behaviour implemented

- R3 legacy: graph features are per-window features on the raw gated legacy windows (no continuous filtering before P16).
- PF-04: feature axis `fs = 250` (default `LEGACY_FS_HZ`, `--fs`), printed in the script header and in the gate meta (`fs=250 legacy`).
- R8 legacy-folder clause: the 2.0 s column uses the `i % 5` smoothing of the out-of-fold scores (`accuracies(..., "mod5")`).
- R5 per-script gate (P07 two-tier, all thresholds explicit via `prepare_subject`).
- Per-window 3-segment Welch coherence is the object under test (small-sample biased, R4 is not enforced here by design).

## Differences from the cited examples

None (no external code adapted). Definitions not fixed by the roadmap and chosen here:
- node power = log10 of the MEAN Hann-FFT power over the bins within +-1 Hz (floor 1e-12 before log); mean-removed, periodic Hann;
- Welch coherence: Hann, constant detrend, segments at 0/64/128 of the 256-sample window, MSC from the segment-averaged spectra, band-averaged over bins within +-1 Hz (nearest bin if none);
- phase: full-window Hann FFT, `G_ij = sum_band X_i conj(X_j)`, phasor `G/|G|`, diagonal and zero cross-spectrum give (1, 0); `[j, i]` is the conjugate of `[i, j]`.
These were not tuned: with them the gate table reproduces R-14 (below), so R11 was not needed.

## Deviations from the plan

1. NEW `src/features/connectivity/graph_dataset.py` (not in the work split): the requested clean loader for the cached dataset lives there, to keep it importable from `src/` by the GNN builder.
2. The cache also stores `fs`, `code_hash`, `channels_dropped`, `trial_ids_approximate` (extra keys beyond the roadmap list). A stale cache (hash of the feature source + fs + gate thresholds) is rejected by the loader; `build_graph_dataset` reuses a valid cache unless `--rebuild`.
3. `--out`/summary: the gate writes only the schema CSV and `.meta.txt` (per-set means and both verdicts in the meta), no separate summary CSV.

## Loader API (for the deep-learning builder)

```python
from src.features.connectivity.graph_dataset import load_graph_dataset, discover_graph_subjects
ds = load_graph_dataset("S03")                      # default data/processed; processed_dir=Path(...) overrides; check_hash=True
ds.node        # (n, C, 10) float64, harmonic-major: column h*5 + k = harmonic h+1 of target k (24, 20, 15, 10.9091, 8.5714 Hz)
ds.edge_coh    # (n, C, C, 5) symmetric, diagonal 1
ds.edge_phase  # (n, C, C, 5, 2) unit phasor (cos, sin) of phase(X_i conj X_j); [j,i] = conjugate; diagonal (1, 0)
ds.X_fbcca     # (n, 5) FBCCA scores (flagship, on the kept channels)
ds.y           # (n,) codes 101..105;  ds.y_index -> 0..4;  ds.classes == (101..105)
ds.trial_ids   # (n,) int64, built on the PRE-gate labels then masked (PF-03); approximate on S02/S04 (ds.trial_ids_approximate)
ds.channels_kept, ds.channels_dropped, ds.fs (250.0), ds.code_hash
```
Rows are in clean-array order (the order the 2.0 s `i % 5` smoothing needs). Use `cv_utils.make_splits("grouped", ds.y, ds.trial_ids, 42 + r)` for folds and `legacy_eval.accuracies(y, pred, scores, trial_ids, "mod5")` for 1.0 s / 2.0 s. Errors: `FileNotFoundError` (no cache), `StaleGraphDataset`. `upper_tri_flat(ds.edge_coh)` gives the 105 coherence features (pair-major from `np.triu_indices(C, 1)`, then band; phase then cos/sin). The channel count C is `len(ds.channels_kept)`; never hardcode 7.

## How to run / reproduce (verifier)

```bash
.venv/bin/python -m scripts.connectivity.graph_modeling.build_graph_dataset --rebuild
.venv/bin/python -m scripts.connectivity.graph_modeling.benchmark_connectivity_gate --repeats 5 --k-select 0 30
```
Outputs: `data/processed/<S>/graph_dataset.npz` (new files), `reports/graph_dataset_sanity.csv`, `reports/connectivity_gate_benchmark.csv` and `.meta.txt`. Optional flags: `--subjects`, `--data-root`, `--reports-dir`, `--fs`, `--seed`. Expected legacy-array hashes unchanged.

Runtimes measured here (scratch tree, not the real folders): build 2 s per subject (11.9 s total for S01-S05, wall); gate 14-15 s per subject (74 s total for 5 subjects x 5 repeats x 9 sets x k in {0, 30}, wall 1m15s; BLAS used all cores). Extrapolated full commands: about 15 s + 2 min on this machine; far below the 120 min bound.

## How I verified

- `.venv/bin/python -m pytest tests -o addopts="" -q` -> `891 passed, 21 warnings in 418.00s (0:06:57)`. New file alone: 17 passed in about 16 s.
- Tests (all synthetic, none reads generated or ignored files): node power layout (15 Hz in channel 2 -> [2, 2]); 2nd harmonic of 10.9091 Hz -> column 8; nearest-bin fallback; planted coupled pair (1, 4) at 20 Hz is the maximum Welch-coherence edge; known phase lag gives (cos, sin) to 1e-6 and unit norm; `upper_tri_flat` order proven on an index-coded array (R6); dims N 70, F 5, Base 75, Ec 105, Ep 210, Ec+Ep 315, Base+Ec 180, Base+Ep 285, Base+Ec+Ep 390; cache is a new file, legacy array hashes unchanged, the overwrite guard refuses a `.npy`, stale hash rejected; pre-gate trial ids (a rejected window mid-trial leaves that trial with 4 windows and does not shift later ids; fails on the PF-03 post-gate bug); R2 (a 1e6 outlier in a test window leaves every other prediction of its fold bit-identical for k = 0 and 30); split has no shared ids and the check catches a window-level StratifiedKFold (PF-01); determinism of the gate rows; verdict rule on constructed deltas (pass, R-14 shape fails, mean-only fails, responders-only fails, exactly 2 of 3 passes, no responder); end-to-end smoke of both scripts on a synthetic tree.
- SMOKE numbers on the real legacy folders (symlinked arrays into the scratchpad, so `data/processed` got no new file; reports into the scratchpad; run by the full commands above with `--data-root`):
  - Clean stimulus windows (R-1, exact): S01 200, S02 196, S03 197, S04 197, S05 200. trial_ids_approximate: S02, S04 only. No channel dropped.
  - Gate, k = 0, 1.0 s, mean of 5 repeats (smoke; R-14 in brackets): Ec 48.3/36.1/45.5/62.4/50.6 mean 48.6 [48.6]; Ep mean 38.8 [38.8]; Ec+Ep 50.6 [50.6]; N 65.3 [65.3]; F 68.6 [68.5]; Base S01 41.2, S02 48.0, S03 82.7, S04 98.0, S05 98.9, mean 73.8 [73.8]; Base+Ep mean 73.4 [73.5]; Base+Ec+Ep 74.9 [74.9]; Base+Ec S01 57.5, S02 51.1, S03 84.0, S04 98.1, S05 97.2, mean 77.6 [77.6].
  - k = 30 means: Base 74.0, Base+Ec 77.5, Base+Ec+Ep 77.5, Base+Ep 76.0, N 64.9, Ec 46.7, Ep 35.5, Ec+Ep 46.0, matching R-14 line "in-fold ANOVA top-30".
  - Verdict k = 0: best edge-augmented set Base+Ec; deltas S01 +16.30, S02 +3.16, S03 +1.22, S04 +0.10, S05 -1.70; cohort mean +3.82; responders (S03-S05) with delta >= 2 pp: 0/3 (need 2); gate does NOT pass. k = 30: Base+Ec, cohort mean +3.51, responders 0/3, does NOT pass.
  - The cohort-mean criterion alone would pass (+3.82 pp, driven by S01 and S02); the verdict is "does not pass" because of the responder criterion. The reviewer should read the rule as the plan settled it (both required).
  - Sanity report (smoke): S03, S04 show positive own-band minus other-class node power for every target (e.g. S03 24 Hz +0.67, S04 24 Hz +0.80 log10 units) and positive coherence differences at the high targets; S01 and S02 are near zero or negative for coherence and phase.
- R11: no reference consultation was needed; the table reproduces R-14 within its tolerance (all per-subject differences <= 0.1 pp).

## Left to do / known limitations

- Real runs belong to the verifier (writes the caches into `data/processed/<S>/`, new files only).
- The deep-learning builder should load through `load_graph_dataset`; `graph_inputs.py` is theirs.
- Test-suite wall time on this machine is 7 min (other phases' tests); P15 tests add about 16 s.
- Gate CV repeats use seeds 42..46 on the same cached features; the gate needs about 2 min, so the verifier may run it as is.

## Reference consultations (R11)

None. `mas/state/scratch/reference_access.log` has no entry from this builder.

| # | Trigger (failed test / deviation / verification) | Files and lines @ commit | What I learned | What changed in my code |
|---|---|---|---|---|
| | none | | | |

## Sources

1. `mas/03_ROADMAP.md` P15 tasks 1-3 (opened in this run).
2. `mas/04_REFERENCE_RESULTS.md` R-1, R-14 (opened in this run); `mas/02_REQUIREMENTS.md` §6 gate schema (opened).

## Questions

ACK 02_plan.md connectivity-stats 2026-10-26
