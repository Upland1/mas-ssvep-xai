# P23 · 03 · Changes — connectivity-stats

Status: READY
Author: connectivity-stats
Reads: 00_assignment.md, 02_plan.md (settled 1, row 1, risks, test 1), mas/RULES.md
Branch: phase/P23-gnn-loso
Commit(s): see `git log` (feat: entry point; test: known-answer tests; docs: this file)

## Files

| Path | NEW / MODIFIED | Summary | Roadmap task | Source |
|---|---|---|---|---|
| `src/features/connectivity/graph_features_subject.py` | NEW | `graph_features_for_subject(d, channels, chunk)`: P15 node / coherence / phase features on the clean continuous windows of a loaded built subject, fs from metadata, + FBCCA scores | P23.1 | R3, R6, own |
| `tests/test_p23_graph_features.py` | NEW | 9 known-answer tests (below) | P23.1 | R3, R4, R6 |

`connectivity_graph_features.py`, `graph_dataset.py` and `graph_inputs.py` are NOT modified (frozen P15 behaviour, 250 Hz default kept; a test pins it). Nothing is written to disk.

## API for the deep-learning builder

```python
from src.io.subject_data import load_subject
from src.features.connectivity.graph_features_subject import graph_features_for_subject
from src.features.connectivity.graph_inputs import build_inputs

d  = load_subject(folder, bands=("fbcca",), channels=CH)      # built folder, quality_mode shared (default)
ds = graph_features_for_subject(d, CH)                         # GraphDatasetEraC
inp = build_inputs(ds, "nodes+coh+F")                          # P15 GraphInputs, unchanged
```

- `ds` is a `GraphDataset` subclass: `node (n, C, 10)`, `edge_coh (n, C, C, 5)`, `edge_phase (n, C, C, 5, 2)`, `X_fbcca (n, 5)`, `y` (codes 101-105), `trial_ids`, `channels_kept` (= `CH`, in order), `fs` (256.0), `y_index`; plus `offsets` and `cv_groups` (R1 key) of `load_subject`. Row i is row i of `d["X"]`, `d["y"]`, `d["trial_ids"]`.
- `bands=("fbcca",)` is required on `load_subject` (FBCCA scores = `fbcca_scores_vectorized` on the saved continuous bank, same as `benchmark_window_sweep.fbcca_features`). Pass the same `channels` list to both calls (a mismatch raises ValueError).
- ValueError for a legacy folder, `fs_source == "legacy-assumed"`, `filter_mode != continuous`, or a missing bank.
- Windows are the continuously filtered `d["X"]` (R3); nothing is filtered here; the phase is the CSD phase of the Hann-windowed 256-sample window. `fs` is `d["fs"]`.
- Coherence is a per-window edge feature (3-segment Welch, E[MSC] about 1/3 for independent channels), not a stimulus-vs-baseline estimate; R4 concatenation does not apply (stated in the module docstring). Standardization stays with `graph_inputs.fit_standardizer` / the harness (R2).
- Features are deterministic and label-free, so computing them per subject up front leaks nothing; pooled / subject z-scoring is the harness's job.

## Legacy behaviour implemented

None.

## Differences from the cited examples

The P15 `GraphDataset` cache needed `data/processed` and fs 250; here the same dataclass is filled in memory from `load_subject` output.

## Deviations from the plan

- New file name `graph_features_subject.py` (not `graph_inputs.py`, which already exists as the P15 model-input module).
- Added an optional `chunk` argument (default 128) bounding the complex temporaries; results do not depend on it (tested with 16).

## How to run / reproduce

```bash
.venv/bin/python -m pytest tests/test_p23_graph_features.py -q -o addopts=""
```

## How I verified

- `tests/test_p23_graph_features.py`: 9 passed. Known answers: a 23 Hz tone (bin 23 at fs 256) lies in the 24 Hz band and the fs-250 assumption moves it out (log10 gap > 0.3); a 15 Hz tone peaks in column 2 of its own channel, harmonic column 7 empty; a coupled pair (phase lag pi/3) gives coherence > 0.95 on edge (1,3) band 2 only, other edges and bands < 0.5, mean cos/sin = (0.5, 0.866) and conjugate at (3,1); independent noise E[MSC] in (0.25, 0.45), diagonal 1; `upper_tri_flat` index `(pair*5+k)*2+c` proven by coded values, coupled edge lands at flat column `pair(1,3)*5+2`, `build_inputs` edge layouts; row alignment with `load_subject` on a synthetic built folder (y, trial ids, offsets, cv groups, FBCCA, chunk borders); permuted channel subset order; refusals.
- Mutation: replacing `fs = float(d["fs"])` by `250.0` fails the tone test and the row-alignment test.
- Full suite once alone: see the line below (filled after the run).
- Timing on built `data/processed_continuous/w1_s0.25`, channels common (7), measured with a scratch script (nothing written to reports/):

| Subject | rows n | load_subject (s) | features (s) | FBCCA argmax acc (diagnostic only) |
|---|---|---|---|---|
| S01 | 680 | 0.0 | 0.3 | 0.587 |
| S02 | 644 | 0.0 | 0.2 | 0.680 |
| S03 | 661 | 0.0 | 0.2 | 0.911 |
| S04 | 665 | 0.0 | 0.3 | 0.988 |
| S05 | 679 | 0.0 | 0.2 | 0.954 |

All arrays finite, fs 256.0, shapes (n, 7, 10), (n, 7, 7, 5), (n, 7, 7, 5, 2). Features cost about 1 s for the whole cohort, so no cache is needed.

## Left to do / known limitations

Standardization, variants and the harness are deep-learning's. Channel set `all` (8, with PO7) is supported by the same call.

## Reference consultations (R11)

None.

## Sources

1. `mas/RULES.md` R3, R4, R6; `src/features/connectivity/connectivity_graph_features.py` docstring (P15 layouts).

## Questions
