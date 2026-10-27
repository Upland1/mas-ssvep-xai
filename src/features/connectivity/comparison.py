"""Cross-frequency comparison of connectivity deltas (P14, R4, R6, R7, PF-19, PF-21 to PF-26).

Everything here works on DELTA matrices (stimulus minus matched baseline, PF-24), never on raw ones.

- `embed_to_montage`: a `(C, C)` matrix over `channels_kept` goes into the 8 x 8 montage with NaN for
  missing channels (PF-26); `symmetrize` turns the directed PDC into `(M + M.T) / 2` (PF-25).
- `qap_pvalue`: one-tailed node-label permutation test of the Pearson r between two matrices; rows and
  columns are permuted together and only among the channels present in both (index layout proven in tests, R6).
- `responders_from_benchmark`: responders from classifier accuracy only (PF-21).
- `split_half_delta_reliability`: trial-level halves, Fisher-mean r, Spearman-Brown only if r > 0 (PF-22).
- `pairwise_permutation_test`: trials of conditions a and b are exchanged at trial level with the OBSERVED
  group sizes (`_trial_permutation_split`, PF-19); each relabelled group is scored in its own band and
  against its own matched baseline; the 201 baseline windows stay fixed. Magnitude and pattern statistics
  share the same null draws.

Legacy: bands live on the fs-250 axis (PF-04).
"""

from typing import Callable, Optional, Sequence

import numpy as np
from scipy.stats import chi2

from src.features.connectivity.permutation import (
  _trial_permutation_split, benjamini_hochberg, derive_seed, edge_mask)
from src.io.channels import FULL_MONTAGE

MONTAGE = tuple(FULL_MONTAGE)
SEED = 42
MIN_PAIRS = 6
MIN_SHARED_CHANNELS = 4
_Z_CLIP = 1.0 - 1e-9


# ------------------------------------------------------------------ embedding, symmetrization, summaries

def embed_to_montage(matrix: np.ndarray, channels_kept: Sequence[str], montage: Sequence[str] = MONTAGE) -> np.ndarray:
  """`(C, C)` over `channels_kept` -> `(M, M)` in `montage` order, NaN where a channel is missing (PF-26).

  Entry `[i, j]` of the result is the entry of the pair (montage[i], montage[j]) of the input, found by NAME.
  """
  m = np.asarray(matrix, dtype=float)
  names = [str(c) for c in channels_kept]
  if m.shape != (len(names), len(names)):
    raise ValueError(f"matrix {m.shape} does not match {len(names)} channels")
  unknown = [c for c in names if c not in montage]
  if unknown:
    raise ValueError(f"channels outside the montage: {unknown}")
  out = np.full((len(montage), len(montage)), np.nan)
  pos = [montage.index(c) for c in names]
  out[np.ix_(pos, pos)] = m
  return out


def symmetrize(matrix: np.ndarray) -> np.ndarray:
  """`(M + M.T) / 2` (PF-25); identity on a symmetric matrix. NaN stays NaN."""
  m = np.asarray(matrix, dtype=float)
  return 0.5 * (m + m.T)


def with_nan_diagonal(matrix: np.ndarray) -> np.ndarray:
  m = np.array(matrix, dtype=float)
  np.fill_diagonal(m, np.nan)
  return m


def undirected_delta(diff: np.ndarray, channels_kept: Sequence[str], directed: bool) -> np.ndarray:
  """Embedded, symmetrized (PDC), NaN-diagonal `(8, 8)` delta matrix used by every undirected statistic."""
  m = embed_to_montage(diff, channels_kept)
  if directed:
    m = symmetrize(m)
  return with_nan_diagonal(m)


def node_strength(matrix: np.ndarray) -> np.ndarray:
  """Mean of the off-diagonal entries of each row (to the other channels); NaN for a missing channel."""
  m = with_nan_diagonal(matrix)
  with np.errstate(invalid="ignore"):
    cnt = np.isfinite(m).sum(axis=1)
    tot = np.where(np.isfinite(m), m, 0.0).sum(axis=1)
  return np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)


def mean_upper(matrix: np.ndarray) -> float:
  """Mean of the finite upper-triangle entries (global delta of a symmetric or symmetrized matrix)."""
  m = np.asarray(matrix, dtype=float)
  v = m[np.triu_indices(m.shape[0], k=1)]
  v = v[np.isfinite(v)]
  return float(v.mean()) if len(v) else float("nan")


def fisher_z(r) -> np.ndarray:
  return np.arctanh(np.clip(np.asarray(r, dtype=float), -_Z_CLIP, _Z_CLIP))


def fisher_mean(r) -> float:
  """Fisher-z average of correlations: `tanh(mean(arctanh(r)))`, NaNs ignored."""
  z = fisher_z(r)
  z = z[np.isfinite(z)]
  return float(np.tanh(z.mean())) if len(z) else float("nan")


def pearson(x: np.ndarray, y: np.ndarray) -> float:
  x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
  xc, yc = x - x.mean(), y - y.mean()
  den = np.sqrt((xc ** 2).sum() * (yc ** 2).sum())
  return float((xc * yc).sum() / den) if den > 0 else float("nan")


# ------------------------------------------------------------------ QAP

def _shared_channels(a: np.ndarray, b: np.ndarray) -> np.ndarray:
  """Indices of the channels with at least one finite off-diagonal entry in both matrices."""
  fa = np.isfinite(with_nan_diagonal(a)).any(axis=1)
  fb = np.isfinite(with_nan_diagonal(b)).any(axis=1)
  return np.flatnonzero(fa & fb)


def qap_pvalue(a: np.ndarray, b: np.ndarray, n_permutations: int = 2000, seed: int = SEED) -> dict:
  """Pearson r between the upper triangles of `a` and `b` and its one-tailed QAP p (`r_perm >= r_obs`, +1).

  Node labels of `b` are permuted (rows and columns with the SAME permutation) among the shared channels
  only. Not applicable (NaN r and p) with fewer than `MIN_PAIRS` finite pairs or `MIN_SHARED_CHANNELS`
  shared channels. Returns `r, p, n_pairs, n_shared`.
  """
  a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
  s = _shared_channels(a, b)
  out = dict(r=float("nan"), p=float("nan"), n_pairs=0, n_shared=int(len(s)))
  if len(s) < MIN_SHARED_CHANNELS:
    return out
  asub, bsub = a[np.ix_(s, s)], b[np.ix_(s, s)]
  iu = np.triu_indices(len(s), k=1)
  av = asub[iu]
  fin = np.isfinite(av) & np.isfinite(bsub[iu])
  out["n_pairs"] = int(fin.sum())
  if out["n_pairs"] < MIN_PAIRS:
    return out
  r_obs = pearson(av[fin], bsub[iu][fin])
  out["r"] = r_obs
  if not np.isfinite(r_obs):
    return out
  rng = np.random.default_rng(int(seed))
  perms = np.stack([rng.permutation(len(s)) for _ in range(n_permutations)])
  bp = bsub[perms[:, :, None], perms[:, None, :]][:, iu[0], iu[1]]   # (n, pairs): b[perm[i], perm[j]]
  ok = np.isfinite(av)[None, :] & np.isfinite(bp)                   # pairs finite in both after permuting
  n_ok = np.maximum(ok.sum(axis=1), 1)
  a_ = np.where(ok, av[None, :], 0.0)
  b_ = np.where(ok, bp, 0.0)
  ac = np.where(ok, a_ - (a_.sum(1) / n_ok)[:, None], 0.0)
  bc = np.where(ok, b_ - (b_.sum(1) / n_ok)[:, None], 0.0)
  den = np.sqrt((ac ** 2).sum(1) * (bc ** 2).sum(1))
  with np.errstate(invalid="ignore", divide="ignore"):
    r_perm = np.where(den > 0, (ac * bc).sum(1) / den, np.nan)
  out["p"] = float((1 + np.sum(r_perm >= r_obs)) / (n_permutations + 1))
  return out


# ------------------------------------------------------------------ responders (PF-21)

def responders_from_benchmark(path, threshold: float = 80.0, column: str = "2.0s Smoothed (%)") -> tuple:
  """`(responders, non_responders)` from the classifier benchmark CSV only (2.0 s smoothed >= threshold).

  Never from connectivity (circular, PF-21). The summary row `Mean` is ignored.
  """
  import pandas as pd
  df = pd.read_csv(path)
  df = df[df["Subject"].astype(str).str.fullmatch(r"S\d+")]
  acc = pd.to_numeric(df[column], errors="coerce")
  resp = sorted(df.loc[acc >= threshold, "Subject"].astype(str))
  non = sorted(df.loc[~(acc >= threshold), "Subject"].astype(str))
  return resp, non


# ------------------------------------------------------------------ reliability (PF-22)

def spearman_brown(r: float) -> tuple:
  """`(value, corrected)`: `2r/(1+r)` only for r > 0, else r unchanged and `corrected = False` (PF-22)."""
  if np.isfinite(r) and r > 0:
    return float(2 * r / (1 + r)), True
  return float(r), False


def reliability_ceiling(rel_a: float, rel_b: float) -> float:
  """`sqrt(rel_a * rel_b)` when both are positive, else NaN."""
  if np.isfinite(rel_a) and np.isfinite(rel_b) and rel_a > 0 and rel_b > 0:
    return float(np.sqrt(rel_a * rel_b))
  return float("nan")


def disattenuate(r_obs: float, ceiling: float, min_ceiling: float = 0.1) -> float:
  """`r_obs / ceiling`, only if the ceiling exceeds `min_ceiling` (else NaN). Not clipped."""
  if np.isfinite(ceiling) and ceiling > min_ceiling and np.isfinite(r_obs):
    return float(r_obs / ceiling)
  return float("nan")


def _half_trials(trial_ids: np.ndarray, rng: np.random.Generator) -> tuple:
  """Boolean masks `(first, second)` over windows: trials shuffled, first `k // 2` trials in the first half."""
  uniq = np.unique(trial_ids)
  perm = uniq[rng.permutation(len(uniq))]
  h = len(uniq) // 2
  first = np.isin(trial_ids, perm[:h])
  return first, ~first


def split_half_delta_reliability(stim: np.ndarray, stim_ids: np.ndarray, base: np.ndarray, base_ids: np.ndarray,
                                 band: tuple, fs: float, method_fn: Callable, n_splits: int = 10,
                                 seed: int = SEED, directed: Optional[bool] = None) -> dict:
  """Trial-level split-half reliability of `method_fn(stim) - method_fn(base)` in `band`.

  Each split halves the stimulus trials AND the baseline trials at random; the two half deltas are
  correlated over the edges (Pearson). Returns `r_fisher` (Fisher mean over the valid splits), `reliability`
  (Spearman-Brown only if `r_fisher > 0`, else `r_fisher` uncorrected), `corrected`, `n_valid`, `r_splits`.
  """
  directed = bool(getattr(method_fn, "directed", False)) if directed is None else bool(directed)
  stim, base = np.asarray(stim), np.asarray(base)
  stim_ids, base_ids = np.asarray(stim_ids), np.asarray(base_ids)
  rng = np.random.default_rng(int(seed))
  emask = None
  rs = []
  for _ in range(n_splits):
    s1, s2 = _half_trials(stim_ids, rng)
    b1, b2 = _half_trials(base_ids, rng)
    if not (s1.any() and s2.any() and b1.any() and b2.any()):
      rs.append(float("nan"))
      continue
    d1 = method_fn(stim[s1], fs, band) - method_fn(base[b1], fs, band)
    d2 = method_fn(stim[s2], fs, band) - method_fn(base[b2], fs, band)
    if emask is None:
      emask = edge_mask(d1.shape[0], directed)
    rs.append(pearson(d1[emask], d2[emask]))
  rs = np.array(rs)
  r_f = fisher_mean(rs)
  rel, corrected = spearman_brown(r_f)
  return dict(r_fisher=r_f, reliability=rel, corrected=corrected, n_valid=int(np.isfinite(rs).sum()), r_splits=rs)


# ------------------------------------------------------------------ pairwise permutation test (task 2)

def fisher_combined_p(p_values) -> tuple:
  """Fisher's method: `(chi2, p, k)` with `chi2 = -2 sum ln p ~ chi2(2k)`; NaNs dropped."""
  p = np.asarray(p_values, dtype=float)
  p = p[np.isfinite(p)]
  if len(p) == 0:
    return float("nan"), float("nan"), 0
  stat = float(-2.0 * np.log(p).sum())
  return stat, float(chi2.sf(stat, 2 * len(p))), int(len(p))


def pairwise_permutation_test(win_a: np.ndarray, ids_a: np.ndarray, win_b: np.ndarray, ids_b: np.ndarray,
                              base: np.ndarray, band_a: tuple, band_b: tuple, fs: float, method_fn: Callable,
                              n_permutations: int, seed: int, alpha: float = 0.05) -> dict:
  """Exchangeability test of the trials of conditions a and b, with statistics on their own-band deltas.

  Observed: `D_a = M(a; band_a) - M(base; band_a)` and `D_b` likewise. Null: the trials of a and b are pooled
  and re-split at trial level with the observed sizes (`_trial_permutation_split`, at most one trial split);
  the first group is scored in `band_a` and the second in `band_b`, each against the FIXED baseline in its own
  band. The null is therefore "the a and b trials are exchangeable", NOT "D_a = D_b": its centre,
  E[t] = [M(pool; band_a) - base_a] - [M(pool; band_b) - base_b], is generally not 0, so p_mag >= 0.05 never
  means D_a ~ D_b and p_pat < 0.05 does not mean the delta patterns differ (P14 audit F2).
  Statistics: `t_mag = mean over edges of (D_a - D_b)`, two-sided; `d_pat = 1 - r(D_a, D_b)` over edges,
  one-sided (large = dissimilar). Both use the same permutations. Edge p-values (two-sided) go through BH-FDR.
  p-values carry the +1 pseudo-count. DIAGNOSTIC (not a test of D_a = D_b by itself): the null mean and SD of
  both statistics and `p_mag_centred = (1 + #{|t_null - mean| >= |t_obs - mean|}) / (n + 1)`.
  Symmetric methods only (upper-triangle edges).
  """
  win_a, win_b, base = np.asarray(win_a), np.asarray(win_b), np.asarray(base)
  ids_a, ids_b = np.asarray(ids_a), np.asarray(ids_b)
  if len(win_a) == 0 or len(win_b) == 0 or len(base) == 0:
    raise ValueError("need windows for a, b and the baseline")
  if len(ids_a) != len(win_a) or len(ids_b) != len(win_b):
    raise ValueError("trial ids must match the window counts")
  if np.intersect1d(ids_a, ids_b).size:                      # different conditions are different trials
    ids_b = ids_b + (int(ids_a.max()) + 1 - int(ids_b.min()))
  directed = bool(getattr(method_fn, "directed", False))
  if directed:
    raise ValueError("pairwise test is for undirected methods (PDC excluded)")
  na = len(win_a)
  pool = np.concatenate([win_a, win_b])
  ids = np.concatenate([ids_a, ids_b])
  fast = hasattr(method_fn, "per_window")
  if fast:
    cache_a, cache_b = method_fn.per_window(pool, fs, band_a), method_fn.per_window(pool, fs, band_b)
    base_a = method_fn.reduce(method_fn.per_window(base, fs, band_a))
    base_b = method_fn.reduce(method_fn.per_window(base, fs, band_b))
    d_a = method_fn.reduce(cache_a[:na]) - base_a
    d_b = method_fn.reduce(cache_b[na:]) - base_b
  else:
    base_a, base_b = method_fn(base, fs, band_a), method_fn(base, fs, band_b)
    d_a, d_b = method_fn(win_a, fs, band_a) - base_a, method_fn(win_b, fs, band_b) - base_b
  emask = edge_mask(d_a.shape[0], False)
  diff_obs = (d_a - d_b)[emask]
  t_obs = float(diff_obs.mean())
  r_obs = pearson(d_a[emask], d_b[emask])
  d_obs = 1.0 - r_obs

  seeds = np.random.SeedSequence(int(seed)).generate_state(n_permutations)
  null_t = np.empty(n_permutations)
  null_d = np.empty(n_permutations)
  null_e = np.empty((n_permutations, int(emask.sum())))
  for k, s in enumerate(seeds):
    rng = np.random.default_rng(int(s))
    ia, ib = _trial_permutation_split(ids, na, rng)
    if fast:
      pa = method_fn.reduce(cache_a[ia]) - base_a
      pb = method_fn.reduce(cache_b[ib]) - base_b
    else:
      pa = method_fn(pool[ia], fs, band_a) - base_a
      pb = method_fn(pool[ib], fs, band_b) - base_b
    e = (pa - pb)[emask]
    null_e[k] = e
    null_t[k] = e.mean()
    null_d[k] = 1.0 - pearson(pa[emask], pb[emask])
  n = n_permutations
  p_mag = (1 + np.sum(np.abs(null_t) >= abs(t_obs))) / (n + 1)
  p_pat = (1 + np.sum(null_d >= d_obs)) / (n + 1) if np.isfinite(d_obs) else float("nan")
  pe = (1 + np.sum(np.abs(null_e) >= np.abs(diff_obs)[None], axis=0)) / (n + 1)
  fdr = benjamini_hochberg(pe, alpha)
  tc = null_t.mean()
  p_cen = (1 + np.sum(np.abs(null_t - tc) >= abs(t_obs - tc))) / (n + 1)
  dn = null_d[np.isfinite(null_d)]
  return dict(t_mag=t_obs, p_mag=float(p_mag), t_null_mean=float(tc), t_null_sd=float(null_t.std()),
              p_mag_centred=float(p_cen), d_null_mean=float(dn.mean()) if len(dn) else float("nan"),
              d_null_sd=float(dn.std()) if len(dn) else float("nan"), d_pat=float(d_obs), p_pat=float(p_pat), r_obs=float(r_obs),
              n_edges_fdr=int(fdr.sum()), n_edges=int(emask.sum()), delta_a=d_a, delta_b=d_b,
              n_permutations=int(n), n_a=int(na), n_b=int(len(win_b)), n_base=int(len(base)))
