"""In-fold feature selection on the FBCSP block of the flagship feature matrix (P06.1, legacy Era A).

Layout (R6, P05): the flagship matrix is `[FBCSP block | FBCCA block]`; the FBCSP block is band-major
(`FBCSPTransformer.transform`): band b owns columns `b*per_band .. (b+1)*per_band - 1` with
`per_band = n_classes * 2m` (10 for m = 1), so the 50 FBCSP columns are followed by the 5 FBCCA
columns. Selection acts on the FBCSP columns only; the FBCCA columns are always kept.

R2 / PF-11: every function here is meant to be called on the TRAINING rows of one fold. The
returned indices are applied unchanged to the test rows. Nothing is fitted on labels outside `X_tr`.

Methods: `SelectKBest(f_classif)` (ANOVA F-score), `mutual_info_classif(random_state)` (mutual
information; its jitter is seeded) and `SequentialFeatureSelector(forward)` (inner 5-fold CV of
the estimator, scikit-learn defaults).
"""

from typing import Optional, Sequence

import numpy as np
from sklearn.base import clone
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.feature_selection import SelectKBest, SequentialFeatureSelector, f_classif, mutual_info_classif
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

METHODS = ("anova", "mutual_info")


def select_k_best_fbcsp_features(X_tr: np.ndarray, y_tr: np.ndarray, n_features_to_select: int = 15,
                                 method: str = "anova", random_state: int = 42) -> np.ndarray:
  """Sorted indices (into the columns of `X_tr`) of the `n_features_to_select` best FBCSP columns.

  `X_tr` is the FBCSP block of the training fold only, `(n_train, 50)` for m = 1 (the FBCCA
  columns are not passed: they are always kept, see `with_fbcca`). `method` is "anova"
  (`f_classif`) or "mutual_info" (`mutual_info_classif`, seeded with `random_state`).
  """
  X_tr = np.asarray(X_tr, dtype=float)
  if X_tr.ndim != 2 or len(X_tr) != len(y_tr):
    raise ValueError(f"X_tr {X_tr.shape} and y_tr {np.shape(y_tr)} do not match")
  k = min(int(n_features_to_select), X_tr.shape[1])
  if method == "anova":
    score = f_classif
  elif method == "mutual_info":
    def score(X, y):
      return mutual_info_classif(X, y, random_state=random_state)
  else:
    raise ValueError(f"method must be one of {METHODS}, got {method!r}")
  return np.flatnonzero(SelectKBest(score, k=k).fit(X_tr, y_tr).get_support())


def select_sfs_fbcsp_features(X_tr: np.ndarray, y_tr: np.ndarray, n_features_to_select: int = 15,
                              estimator=None, n_jobs: Optional[int] = None) -> np.ndarray:
  """Sorted indices of the FBCSP columns chosen by forward sequential selection on the training fold.

  Default estimator: `Pipeline(StandardScaler, Shrinkage-LDA lsqr)`; scikit-learn's default inner
  5-fold stratified CV (no shuffle, deterministic) and accuracy scoring run inside `X_tr`.
  """
  est = clone(estimator) if estimator is not None else Pipeline([
    ("scaler", StandardScaler()), ("clf", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))])
  sfs = SequentialFeatureSelector(est, n_features_to_select=int(n_features_to_select), direction="forward",
                                  n_jobs=n_jobs)
  return np.flatnonzero(sfs.fit(np.asarray(X_tr, dtype=float), y_tr).get_support())


def with_fbcca(X: np.ndarray, fbcsp_idx: Sequence[int], n_fbcsp: int) -> np.ndarray:
  """Selected FBCSP columns of `X` followed by all remaining (FBCCA) columns `n_fbcsp ..`."""
  X = np.asarray(X)
  return X[:, np.concatenate([np.asarray(fbcsp_idx, dtype=int), np.arange(n_fbcsp, X.shape[1])])]


def band_columns(band: int, per_band: int = 10) -> np.ndarray:
  """FBCSP column indices of one band in the band-major layout (R6)."""
  return np.arange(band * per_band, (band + 1) * per_band)


def subband_pruned_columns(n_columns: int, drop_bands: Sequence[int], n_bands: int = 5) -> np.ndarray:
  """Kept column indices of the full matrix after removing whole FBCSP bands; FBCCA columns stay.

  `n_columns` = FBCSP + FBCCA width (55 for m = 1); `per_band = (n_columns - n_fbcca) / n_bands`
  is inferred with 5 FBCCA columns. Dropping band 4 (38-52 Hz) of 55 columns leaves 45.
  """
  n_fbcca = 5
  per_band = (n_columns - n_fbcca) // n_bands
  drop = np.concatenate([band_columns(b, per_band) for b in drop_bands]) if len(drop_bands) else np.array([], int)
  return np.setdiff1d(np.arange(n_columns), drop)
