"""Network-Based Statistic on permutation nulls (P18, R4, R6, R7, PF-19, PF-20, PF-25).

Edges are vectors in upper-triangle order (`np.triu_indices(C, 1)`, row-major); `C` follows from the
length `E = C (C - 1) / 2`. `edge_pseudo_z` standardizes the observed statistic and every permutation by
the null mean and std of each edge (std 0 or non-finite gives z 0, never infinite). Supra-threshold edges
(`z > t`; `|z| > t` if two-tailed) form an undirected graph; connected components come from
`scipy.sparse.csgraph.connected_components` and a component's size is its NUMBER OF EDGES. The null is the
largest component of each permutation's own z-map (same mean/std, same threshold):
`p = (1 + #{null_max >= size}) / (n + 1)`. Components with p < alpha are the significant mask. The test is on
the trial-level permutation null of the caller (PF-19); it never builds a null of its own. Directed matrices
(PDC) are symmetrized `(M + M.T) / 2` with their nulls before the edge vector is taken (PF-25).
This is the NBS idea of graph-level inference on connected supra-threshold components; no external source
was opened for this implementation (R10).
"""

from typing import Optional, Sequence

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

DEFAULT_THRESHOLDS = (1.5, 2.0, 2.5, 3.0)


def n_channels_from_edges(n_edges: int) -> int:
  """`C` with `C (C - 1) / 2 == n_edges`; raises if `n_edges` is not a triangular number."""
  c = int(round((1 + np.sqrt(1 + 8 * n_edges)) / 2))
  if c * (c - 1) // 2 != n_edges:
    raise ValueError(f"{n_edges} is not a number of undirected edges C (C - 1) / 2")
  return c


def matrix_to_edges(matrix: np.ndarray, directed: bool = False) -> np.ndarray:
  """Upper-triangle edge vector(s) of `(..., C, C)`; directed matrices are symmetrized first (PF-25)."""
  m = np.asarray(matrix, dtype=float)
  if directed:
    m = (m + np.swapaxes(m, -1, -2)) / 2.0
  iu = np.triu_indices(m.shape[-1], k=1)
  return m[..., iu[0], iu[1]]


def edges_to_matrix(edges: np.ndarray, n_channels: Optional[int] = None) -> np.ndarray:
  """Symmetric `(C, C)` from an edge vector (zero diagonal); inverse of `matrix_to_edges` on symmetric input."""
  e = np.asarray(edges)
  c = n_channels or n_channels_from_edges(len(e))
  out = np.zeros((c, c), dtype=e.dtype)
  iu = np.triu_indices(c, k=1)
  out[iu] = e
  return out + out.T


def edge_pseudo_z(obs: np.ndarray, null: np.ndarray, two_tailed: bool = False) -> tuple:
  """`(z_obs (E,), z_null (n, E))` standardized by each edge's null mean and std; std 0 / non-finite -> z 0.

  Two-tailed returns absolute values.
  """
  obs, null = np.asarray(obs, dtype=float), np.asarray(null, dtype=float)
  mu, sd = null.mean(axis=0), null.std(axis=0)
  ok = np.isfinite(sd) & (sd > 0)
  safe = np.where(ok, sd, 1.0)
  z_obs = np.where(ok, (obs - mu) / safe, 0.0)
  z_null = np.where(ok[None], (null - mu[None]) / safe[None], 0.0)
  z_obs, z_null = np.nan_to_num(z_obs, nan=0.0, posinf=0.0, neginf=0.0), np.nan_to_num(z_null, nan=0.0, posinf=0.0, neginf=0.0)
  if two_tailed:
    return np.abs(z_obs), np.abs(z_null)
  return z_obs, z_null


def edge_components(supra: np.ndarray, n_channels: int) -> tuple:
  """`(edge_component (E,) int, sizes)`: component label per edge (-1 if not supra-threshold), edge count per label."""
  supra = np.asarray(supra, dtype=bool)
  iu = np.triu_indices(n_channels, k=1)
  i, j = iu[0][supra], iu[1][supra]
  lab_e = np.full(len(supra), -1, dtype=int)
  if len(i) == 0:
    return lab_e, np.zeros(0, dtype=int)
  g = coo_matrix((np.ones(len(i)), (i, j)), shape=(n_channels, n_channels))
  _, lab = connected_components(g, directed=False)
  _, compact = np.unique(lab[i], return_inverse=True)  # components with at least one edge only
  lab_e[supra] = compact
  return lab_e, np.bincount(compact)


def max_component_size(supra: np.ndarray, n_channels: int) -> int:
  return int(edge_components(supra, n_channels)[1].max(initial=0))


def nbs_from_z(z_obs: np.ndarray, z_null: np.ndarray, threshold: float, alpha: float = 0.05) -> dict:
  """NBS on precomputed pseudo-z maps (see `nbs_test`)."""
  z_obs, z_null = np.asarray(z_obs, dtype=float), np.asarray(z_null, dtype=float)
  e = len(z_obs)
  c = n_channels_from_edges(e)
  n = len(z_null)
  lab_e, sizes = edge_components(z_obs > threshold, c)
  null_max = np.array([max_component_size(z > threshold, c) for z in z_null], dtype=int)
  comp_p = (1 + (null_max[None, :] >= sizes[:, None]).sum(axis=1)) / (n + 1) if len(sizes) else np.zeros(0)
  sig_comp = comp_p < alpha
  mask = np.zeros(e, dtype=bool)
  if len(sizes):
    mask = (lab_e >= 0) & sig_comp[np.clip(lab_e, 0, None)]
  max_size = int(sizes.max()) if len(sizes) else 0
  p_largest = float((1 + np.sum(null_max >= max_size)) / (n + 1))
  return dict(threshold=float(threshold), mask=mask, max_size=max_size, p=p_largest,
              n_sig_edges=int(mask.sum()), possible_edges=int(e), size_fraction=max_size / e if e else float("nan"),
              significant=bool(p_largest < alpha), null_max=null_max, component_sizes=sizes,
              component_p=comp_p, n_channels=int(c))


def nbs_test(z_obs: np.ndarray, z_null: np.ndarray, threshold: float = 2.0, alpha: float = 0.05) -> dict:
  """NBS for pseudo-z maps `z_obs (E,)` and `z_null (n, E)` in upper-triangle order.

  Returns `mask (E,)` (edges of components with p < alpha), `max_size`, `p` (of the largest component),
  `n_sig_edges`, `possible_edges`, `size_fraction`, `significant`, `null_max (n,)` and per-component sizes / p.
  """
  return nbs_from_z(z_obs, z_null, threshold, alpha)


def nbs_sweep(obs: np.ndarray, null: np.ndarray, thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
              alpha: float = 0.05, two_tailed: bool = False) -> dict:
  """`{threshold: nbs result}` on the SAME permutations; `obs (E,)`, `null (n, E)` are raw statistics."""
  z_obs, z_null = edge_pseudo_z(obs, null, two_tailed)
  return {float(t): nbs_from_z(z_obs, z_null, t, alpha) for t in thresholds}
