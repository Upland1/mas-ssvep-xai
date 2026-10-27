"""Permutation statistics for connectivity differences (P13, R7, PF-19, PF-20).

Stimulus-minus-baseline difference per edge; the null pools the two groups of windows and
re-splits them with the OBSERVED group sizes (matched counts also cancel the estimator's
size-dependent bias, PF-19). With trial ids whole trials are permuted (`_trial_permutation_split`,
at most one trial split to hit the count exactly); without ids windows are shuffled individually
(`permutation_unit = "window"`, the legacy R7 first run, labelled). Every permutation uses its own
seed spawned from `random_state`, so results do not depend on `n_jobs`.

Global statistic = mean difference over the edges (upper triangle for symmetric methods, all
off-diagonal entries for the directed PDC). p-values carry the +1 pseudo-count, so the smallest
attainable value is 1 / (n_permutations + 1). Edge-wise Benjamini-Hochberg FDR uses the one-tailed
edge p-values. The global p (criterion B) and the FDR edge count (criterion A) stay separate (PF-20).
"""

import zlib
from typing import Callable, Optional, Sequence

import numpy as np
from joblib import Parallel, delayed

from src.features.connectivity.connectivity_extraction import (
  BASELINE_CONDITION, CONDITION_FREQS, GATE, band_for_condition, compute_condition_coherence)
from src.preprocessing.signal.quality_check import apply_artifact_quality_pipeline

SEED = 42


def edge_mask(n_channels: int, directed: bool) -> np.ndarray:
  """Boolean `(C, C)` of the edges: upper triangle (21 at C=7) or all off-diagonal entries (42)."""
  if directed:
    return ~np.eye(n_channels, dtype=bool)
  return np.triu(np.ones((n_channels, n_channels), dtype=bool), k=1)


def benjamini_hochberg(p_values: np.ndarray, alpha: float = 0.05) -> np.ndarray:
  """BH step-up: boolean mask (shape of `p_values`) of the rejected hypotheses at level `alpha`."""
  p = np.asarray(p_values, dtype=float)
  flat = p.reshape(-1)
  m = len(flat)
  order = np.argsort(flat, kind="stable")
  ok = flat[order] <= alpha * np.arange(1, m + 1) / m
  reject = np.zeros(m, dtype=bool)
  if ok.any():
    k = int(np.flatnonzero(ok).max())
    reject[order[:k + 1]] = True
  return reject.reshape(p.shape)


def derive_seed(random_state: int, *keys) -> int:
  """Deterministic 32-bit seed from `random_state` and (subject, method, condition, ...) keys."""
  parts = [int(random_state)] + [zlib.crc32(str(k).encode()) for k in keys]
  return int(np.random.SeedSequence(parts).generate_state(1)[0])


def _trial_permutation_split(trial_ids: np.ndarray, n_first: int, rng: np.random.Generator) -> tuple:
  """`(idx_first, idx_second)` over the pooled windows; `len(idx_first) == n_first` exactly.

  Greedy fill in random trial order: whole trials go to the first group while they fit; the first
  trial that does not fit is split to complete the count, then filling stops (at most one split).
  """
  ids = np.asarray(trial_ids)
  uniq = np.unique(ids)
  members = {u: np.flatnonzero(ids == u) for u in uniq}
  first, filled = [], 0
  for u in uniq[rng.permutation(len(uniq))]:
    m = members[u]
    if filled + len(m) <= n_first:
      first.append(m)
      filled += len(m)
    else:
      need = n_first - filled
      if need > 0:
        first.append(rng.permutation(m)[:need])
        filled += need
      break
    if filled == n_first:
      break
  idx_first = np.sort(np.concatenate(first)) if first else np.array([], dtype=int)
  mask = np.zeros(len(ids), dtype=bool)
  mask[idx_first] = True
  return idx_first, np.flatnonzero(~mask)


def _window_permutation_split(n_total: int, n_first: int, rng: np.random.Generator) -> tuple:
  """Window-level split (legacy R7 first run): shuffle windows individually."""
  perm = rng.permutation(n_total)
  return np.sort(perm[:n_first]), np.sort(perm[n_first:])


def _diff_matrix(pool: np.ndarray, cache: Optional[np.ndarray], idx_a: np.ndarray, idx_b: np.ndarray,
                 method_fn: Callable, fs: float, band: tuple) -> np.ndarray:
  if cache is not None:
    return method_fn.reduce(cache[idx_a]) - method_fn.reduce(cache[idx_b])
  return method_fn(pool[idx_a], fs, band) - method_fn(pool[idx_b], fs, band)


def _perm_chunk(pool, cache, ids, n_first, seeds, method_fn, fs, band):
  """Null difference matrices `(k, C, C)` for the given per-permutation seeds."""
  out = []
  for s in seeds:
    rng = np.random.default_rng(int(s))
    if ids is None:
      a, b = _window_permutation_split(len(pool), n_first, rng)
    else:
      a, b = _trial_permutation_split(ids, n_first, rng)
    out.append(_diff_matrix(pool, cache, a, b, method_fn, fs, band))
  return np.stack(out)


def compute_permutation_test(stim: np.ndarray, base: np.ndarray, band: tuple, fs: float,
                             n_permutations: int = 200, method_fn: Callable = compute_condition_coherence,
                             n_jobs: int = -1, random_state: int = SEED, alpha: float = 0.05,
                             stim_trial_ids: Optional[np.ndarray] = None,
                             baseline_trial_ids: Optional[np.ndarray] = None,
                             directed: Optional[bool] = None) -> dict:
  """Permutation test of `method_fn(stim) - method_fn(base)` in `band`.

  `method_fn(windows, fs, band) -> (C, C)`; `directed` defaults to `method_fn.directed` (PDC).
  Trial-level when both id arrays are given (`permutation_unit = "trial"`), else window-level.
  Returns observed matrices, global and edge p-values (one- and two-tailed, +1 pseudo-count),
  the null summary, BH-FDR edge mask and the unit label.
  """
  stim, base = np.asarray(stim), np.asarray(base)
  ns, nb = len(stim), len(base)
  if ns == 0 or nb == 0:
    raise ValueError("stim and base need at least one window each")
  if (stim_trial_ids is None) != (baseline_trial_ids is None):
    raise ValueError("pass both stim_trial_ids and baseline_trial_ids, or neither")
  directed = bool(getattr(method_fn, "directed", False)) if directed is None else bool(directed)
  pool = np.concatenate([stim, base])
  ids = None
  if stim_trial_ids is not None:
    s_ids, b_ids = np.asarray(stim_trial_ids), np.asarray(baseline_trial_ids)
    if len(s_ids) != ns or len(b_ids) != nb:
      raise ValueError("trial ids must match the window counts")
    # stimulus and baseline trials are different trials even if their labels collide
    ids = np.concatenate([s_ids, b_ids + (int(s_ids.max()) + 1 - int(b_ids.min()))])
  cache = method_fn.per_window(pool, fs, band) if hasattr(method_fn, "per_window") else None

  if cache is not None:
    stim_m, base_m = method_fn.reduce(cache[:ns]), method_fn.reduce(cache[ns:])
  else:
    stim_m, base_m = method_fn(stim, fs, band), method_fn(base, fs, band)
  obs = stim_m - base_m
  emask = edge_mask(obs.shape[0], directed)
  obs_global = float(obs[emask].mean())

  seeds = np.random.SeedSequence(int(random_state)).generate_state(n_permutations)
  if cache is not None or n_jobs == 1:
    null = _perm_chunk(pool, cache, ids, ns, seeds, method_fn, fs, band)
  else:
    n_chunks = max(1, min(n_permutations, (abs(n_jobs) if n_jobs > 0 else 16) * 4))
    chunks = np.array_split(seeds, n_chunks)
    res = Parallel(n_jobs=n_jobs)(
      delayed(_perm_chunk)(pool, cache, ids, ns, c, method_fn, fs, band) for c in chunks if len(c))
    null = np.concatenate(res)
  null_global = null[:, emask].mean(axis=1)
  n = n_permutations
  p_one = (1 + np.sum(null_global >= obs_global)) / (n + 1)
  p_low = (1 + np.sum(null_global <= obs_global)) / (n + 1)  # lower tail, from the null counts
  p_two = (1 + np.sum(np.abs(null_global) >= abs(obs_global))) / (n + 1)
  edge_obs = obs[emask]
  edge_null = null[:, emask]
  pe_one = (1 + np.sum(edge_null >= edge_obs[None], axis=0)) / (n + 1)
  pe_two = (1 + np.sum(np.abs(edge_null) >= np.abs(edge_obs)[None], axis=0)) / (n + 1)
  p_mat_one, p_mat_two = np.ones(obs.shape), np.ones(obs.shape)
  p_mat_one[emask], p_mat_two[emask] = pe_one, pe_two
  fdr = np.zeros(obs.shape, dtype=bool)
  fdr[emask] = benjamini_hochberg(pe_one, alpha)
  lo, hi = np.percentile(null_global, [2.5, 97.5])
  return dict(
    observed_diff=obs, stim_matrix=stim_m, base_matrix=base_m, obs_diff=obs_global,
    p_one_tailed=float(p_one), p_lower_tailed=float(p_low), p_two_tailed=float(p_two), significant_uncorrected=bool(p_one < alpha),
    null_mean=float(null_global.mean()), null_std=float(null_global.std()), null_ci=(float(lo), float(hi)),
    null_distribution=null_global, edge_p_one_tailed=p_mat_one, edge_p_two_tailed=p_mat_two,
    fdr_significant=fdr, n_edges_sig_uncorrected=int((pe_one < alpha).sum()),
    n_edges_sig_fdr=int(fdr.sum()), total_edges=int(emask.sum()), directed=directed,
    permutation_unit="window" if ids is None else "trial", n_permutations=int(n),
    n_stim=int(ns), n_base=int(nb))


def extract_connectivity_by_condition(windows: np.ndarray, y: np.ndarray, fs: float, method_fn: Callable,
                                      conditions: Sequence[int] = tuple(CONDITION_FREQS),
                                      channel_names: Optional[Sequence[str]] = None,
                                      vpp_min: float = GATE["vpp_min"], vpp_max: float = GATE["vpp_max"],
                                      std_min: float = GATE["std_min"], std_max: float = GATE["std_max"],
                                      channel_fail_fraction_thresh: float = GATE["channel_fail_fraction_thresh"],
                                      n_permutations: int = 0, trial_ids: Optional[np.ndarray] = None,
                                      quality: Optional[dict] = None, n_jobs: int = -1,
                                      random_state: int = SEED, alpha: float = 0.05,
                                      seed_keys: Sequence = ()) -> dict:
  """One shared gate for every condition, then stimulus, matched baseline, differences, optional tests.

  `windows (n, C, T)`, `y`, `trial_ids` are PRE-gate (PF-03: ids from the pre-gate labels). The gate is
  `quality` if given (a dict of `apply_artifact_quality_pipeline`, reused as is) or is computed once here
  from the explicit thresholds. The baseline (201) is the same windows re-scored in each band (PF-16).
  Returns `{condition: dict}` (the `compute_permutation_test` dict when `n_permutations > 0`, else matrices
  only) plus `"_meta"` (channels kept/dropped, window counts).
  """
  w, y = np.asarray(windows), np.asarray(y)
  if quality is None:
    if channel_names is None:
      raise ValueError("channel_names is required when quality is not given")
    quality = apply_artifact_quality_pipeline(
      w, y, channel_names, verbose=False, vpp_min=vpp_min, vpp_max=vpp_max, std_min=std_min,
      std_max=std_max, channel_fail_fraction_thresh=channel_fail_fraction_thresh)
  mask = np.asarray(quality["valid_mask"]).astype(bool)
  wc, yc = quality["windows_clean"], quality["y_clean"]
  ids = None if trial_ids is None else np.asarray(trial_ids)[mask]  # same mask as the windows (PF-03)
  base_sel = yc == BASELINE_CONDITION
  if not base_sel.any():
    raise ValueError("no clean baseline (201) windows")
  directed = bool(getattr(method_fn, "directed", False))
  out = {}
  for c in conditions:
    sel = yc == c
    if not sel.any():
      continue
    band = band_for_condition(c)
    if n_permutations > 0:
      out[c] = compute_permutation_test(
        wc[sel], wc[base_sel], band, fs, n_permutations, method_fn, n_jobs,
        derive_seed(random_state, *seed_keys, c), alpha,
        None if ids is None else ids[sel], None if ids is None else ids[base_sel], directed)
    else:
      s, b = method_fn(wc[sel], fs, band), method_fn(wc[base_sel], fs, band)
      out[c] = dict(stim_matrix=s, base_matrix=b, observed_diff=s - b)
    out[c].update(n_stim=int(sel.sum()), n_base=int(base_sel.sum()))
  out["_meta"] = dict(channels_kept=list(quality["channels_kept"]),
                      channels_dropped=list(quality["channels_dropped"]),
                      n_windows_clean=int(len(yc)), n_windows_total=int(len(y)))
  return out
