"""Model inputs of the P15 GNN from a cached `GraphDataset`, and the train-fold-only standardizer (R2).

Variants `nodes[+coh][+phase][+F]` (canonical order; the name must start with `nodes`):
  nodes  -> node features `(n, C, 10)` (log10 band power, harmonic-major)
  +coh   -> edge features `(n, C, C, 5)` (band-averaged coherence)
  +phase -> edge features `(n, C, C, 10)` (unit phasor (cos, sin) per band, band-major then cos/sin)
  +F     -> graph features `(n, 5)` (FBCCA scores)
`+coh+phase` concatenates the edge features (15 per edge).

Standardizer: mean and std from the TRAINING rows only, per (channel, feature) for nodes, per (i, j, feature) for
edges and per feature for graph features; a constant column (std < 1e-8, e.g. the unit diagonal) is left
unscaled. Applying it to any rows never changes the stored statistics.
"""

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

PARTS = ("coh", "phase", "F")
STD_FLOOR = 1e-8


@dataclass
class GraphInputs:
  """Arrays of one variant: `node (n, C, Fn)`, `edge (n, C, C, Fe)` or None, `graph (n, Fg)` or None."""
  node: np.ndarray
  edge: Optional[np.ndarray] = None
  graph: Optional[np.ndarray] = None

  def __len__(self) -> int:
    return len(self.node)

  def take(self, idx) -> "GraphInputs":
    return GraphInputs(self.node[idx], None if self.edge is None else self.edge[idx],
                       None if self.graph is None else self.graph[idx])


@dataclass
class Standardizer:
  node_mean: np.ndarray
  node_std: np.ndarray
  edge_mean: Optional[np.ndarray] = None
  edge_std: Optional[np.ndarray] = None
  graph_mean: Optional[np.ndarray] = None
  graph_std: Optional[np.ndarray] = None


def parse_variant(variant: str) -> tuple:
  """`(use_coh, use_phase, use_F)`; raises ValueError unless the name starts with `nodes` and adds known parts once."""
  toks = variant.split("+")
  if toks[0] != "nodes":
    raise ValueError(f"variant {variant!r} must start with 'nodes'")
  rest = toks[1:]
  bad = [t for t in rest if t not in PARTS]
  if bad or len(set(rest)) != len(rest):
    raise ValueError(f"variant {variant!r}: unknown or repeated part(s) {bad or rest}; parts {PARTS}")
  return tuple(p in rest for p in PARTS)


def variant_name(use_coh: bool = False, use_phase: bool = False, use_F: bool = False) -> str:
  return "+".join(["nodes"] + [p for p, u in zip(PARTS, (use_coh, use_phase, use_F)) if u])


def build_inputs(ds, variant: str) -> GraphInputs:
  """Inputs of `variant` from a `GraphDataset` (float32). Layouts: `connectivity_graph_features` docstring (R6)."""
  coh, phase, f = parse_variant(variant)
  node = np.asarray(ds.node, dtype=np.float32)
  edges = []
  if coh:
    edges.append(np.asarray(ds.edge_coh, dtype=np.float32))
  if phase:
    ep = np.asarray(ds.edge_phase, dtype=np.float32)
    edges.append(ep.reshape(*ep.shape[:3], -1))
  edge = np.concatenate(edges, axis=-1) if edges else None
  graph = np.asarray(ds.X_fbcca, dtype=np.float32) if f else None
  return GraphInputs(node, edge, graph)


def _stats(a: np.ndarray) -> tuple:
  mu = a.mean(axis=0)
  sd = a.std(axis=0)
  return mu, np.where(sd < STD_FLOOR, 1.0, sd)


def fit_standardizer(inputs: GraphInputs, train_idx: Sequence[int]) -> Standardizer:
  """Statistics from `inputs` rows `train_idx` only (R2)."""
  tr = inputs.take(np.asarray(train_idx))
  nm, ns = _stats(tr.node)
  em, es = _stats(tr.edge) if tr.edge is not None else (None, None)
  gm, gs = _stats(tr.graph) if tr.graph is not None else (None, None)
  return Standardizer(nm, ns, em, es, gm, gs)


def apply_standardizer(inputs: GraphInputs, st: Standardizer) -> GraphInputs:
  node = ((inputs.node - st.node_mean) / st.node_std).astype(np.float32)
  edge = None if inputs.edge is None else ((inputs.edge - st.edge_mean) / st.edge_std).astype(np.float32)
  graph = None if inputs.graph is None else ((inputs.graph - st.graph_mean) / st.graph_std).astype(np.float32)
  return GraphInputs(node, edge, graph)


def standardize_fold(inputs: GraphInputs, train_idx: Sequence[int], test_idx: Sequence[int]) -> tuple:
  """`(train, test)` standardized with statistics of the training rows only."""
  st = fit_standardizer(inputs, train_idx)
  return apply_standardizer(inputs.take(np.asarray(train_idx)), st), apply_standardizer(inputs.take(np.asarray(test_idx)), st)
