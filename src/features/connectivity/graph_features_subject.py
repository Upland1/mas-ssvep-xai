"""In-memory Era C graph features of one built subject (P23.1; the P15 definitions on continuous windows).

`graph_features_for_subject(d, channels)` takes the dict of `load_subject(built folder, ..., bands=("fbcca",),
channels=channels)` and computes, for its clean stimulus windows (classes 101-105), the three arrays of
`connectivity_graph_features` (node band power, band-averaged Welch coherence, CSD phase phasor) with
`fs = d["fs"]` from the metadata (256 Hz, never `LEGACY_FS_HZ`; a legacy folder or an assumed fs is refused).
The windows are the continuously filtered `d["X"]` (R3): no filtering happens here. Nothing is written to disk
(the legacy `graph_dataset.npz` cache and its 250 Hz default are untouched).

The result is a `GraphDatasetEraC`, a `GraphDataset` (same field names and array layouts: `node (n, C, 10)`,
`edge_coh (n, C, C, 5)`, `edge_phase (n, C, C, 5, 2)`, `X_fbcca (n, 5)`, `y`, `trial_ids`), so
`graph_inputs.build_inputs(ds, variant)` and the P15 model consume it unchanged. Rows are the rows of
`d["X"]`, in the same order (ordered by (trial, offset), R8), with `offsets`, `cv_groups` (R1 group key) and
`channels_kept` (= the chosen channels, in order) carried along.

Coherence here is a per-window edge FEATURE of the model input, not a stimulus-vs-baseline estimate; the R4
concatenation rule does not apply, and the 3-segment Welch estimate keeps its upward small-sample bias.
"""

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from src.features.connectivity import connectivity_graph_features as cgf
from src.features.connectivity.graph_dataset import CLASS_CODES, GraphDataset, code_fingerprint
from src.features.ssvep.fbcca_extraction import TARGET_FREQS, fbcca_scores_vectorized, reference_bases

CHUNK = 128


@dataclass
class GraphDatasetEraC(GraphDataset):
  """`GraphDataset` plus the row keys of `load_subject`: `offsets (n,)` and `cv_groups (n,)`."""
  offsets: Optional[np.ndarray] = None
  cv_groups: Optional[np.ndarray] = None


def fbcca_scores(d: dict) -> np.ndarray:
  """FBCCA scores `(n, 5)` of the saved continuous `fbcca` bank of the loaded subject (no fitting)."""
  if "fbcca" not in d.get("bands", {}):
    raise ValueError("load_subject(..., bands=('fbcca',)) is needed for the FBCCA scores")
  bands = d["bands"]["fbcca"]
  return fbcca_scores_vectorized(bands, reference_bases(d["fs"], bands.shape[-1], TARGET_FREQS))


def features_from_windows(X: np.ndarray, fs: float, chunk: int = CHUNK) -> dict:
  """`build_graph_features` in chunks of windows (bounds the `(n, C, C, F)` complex temporaries)."""
  parts = [cgf.build_graph_features(X[i:i + chunk], fs) for i in range(0, len(X), chunk)]
  return {k: np.concatenate([p[k] for p in parts]) for k in ("node", "edge_coh", "edge_phase")}


def graph_features_for_subject(d: dict, channels: Optional[Sequence[str]] = None, chunk: int = CHUNK) -> GraphDatasetEraC:
  """Era C graph dataset of a loaded built subject `d` (module docstring).

  `channels`: names that must equal `d["channel_names"]` (the order of the arrays); pass the same list given to
  `load_subject(..., channels=...)`. `None` takes `d["channel_names"]`. Raises ValueError for a legacy folder,
  an assumed fs, a missing FBCCA bank, or channel names that differ from the loaded ones."""
  if not d.get("built", False):
    raise ValueError("graph_features_for_subject needs a built (continuous) folder, not a legacy one (R3)")
  if d.get("fs_source") == "legacy-assumed":
    raise ValueError("fs is the legacy assumption; Era C takes fs from the folder metadata")
  names = list(d["channel_names"])
  if channels is not None and [str(c) for c in channels] != names:
    raise ValueError(f"channels {list(channels)} differ from the loaded channel_names {names}; pass the same list to load_subject")
  if d["filter_mode"] != "continuous":
    raise ValueError(f"filter_mode {d['filter_mode']!r}: Era C graph features need a continuous build (R3)")
  fs = float(d["fs"])
  g = features_from_windows(d["X"], fs, chunk)
  return GraphDatasetEraC(
    subject=d["subject"], node=g["node"], edge_coh=g["edge_coh"], edge_phase=g["edge_phase"],
    X_fbcca=fbcca_scores(d), y=np.asarray(d["y"]), trial_ids=np.asarray(d["trial_ids"]), channels_kept=names,
    channels_dropped=list(d["channels_dropped"]), fs=fs, code_hash=code_fingerprint(fs),
    trial_ids_approximate=bool(d["trial_ids_approximate"]), offsets=np.asarray(d["offsets"]),
    cv_groups=np.asarray(d["cv_groups"]))
