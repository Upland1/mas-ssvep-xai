"""Legacy-protocol evaluation helpers of the P05 feature benchmarks.

legacy (R1, PF-01): `StratifiedKFold(5, shuffle, seed 42)` over windows; windows of one trial
land in train and test, so accuracies are leaky and are not comparable with the leak-free
R-6. legacy (R8, PF-02): "2.0 s smoothed" is the legacy i%5 trial smoothing of the out-of-fold
scores in clean-array order (reset at `i % 5 == 0`, the original's "2.0s Trial Smoothed"); the
P04 no-reset average is a labelled DIAGNOSTIC only. Fixed in P11 (trial-grouped CV, true trial ids).

R2 / PF-11: `fold_matrices` builds the feature matrices of one fold with the CSP filters
fitted on the training rows only; the scaler is the first step of every model Pipeline.
"""

import warnings
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
from sklearn.base import clone
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.features.ssvep.fbcsp_extraction import FBCSPTransformer
from src.preprocessing.dataset.smoothing import smooth_probabilities_mod5

N_FOLDS = 5
SEED = 42
CV_LABEL = "StratifiedKFold(5, shuffle, 42) over windows (legacy R1/PF-01, leaky)"
SMOOTH_LABEL = "legacy i%5 trial smoothing (R8 legacy, PF-02): 2-window average, reset at i % 5 == 0 of the clean array"
DIAG_SMOOTH_LABEL = "no-reset 2-window average (P04 rule), DIAGNOSTIC only"
smooth_reported = smooth_probabilities_mod5   # the reported "2.0 s smoothed" rule of P05-P10


def legacy_cv(seed: int = SEED) -> StratifiedKFold:
  """legacy (R1, PF-01): fixed in P11 by StratifiedGroupKFold over trial ids."""
  return StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)


@dataclass
class FeatureSpace:
  """A feature matrix recipe: optional in-fold FBCSP block (first columns) + static blocks.

  `static` blocks are per-window features computed without fitting anything on labels
  (PSD, harmonic PSD, FBCCA), row-aligned with `y`. `fbcsp_m` not None adds the FBCSP block
  of `FBCSPTransformer(fbcsp_m)` fitted per fold on the training rows (PF-11).
  """
  name: str
  static: list = field(default_factory=list)
  fbcsp_m: Optional[int] = None


def space_width(space: FeatureSpace, n_bands: int = 5, n_classes: int = 5) -> int:
  w = sum(b.shape[1] for b in space.static)
  return w + (n_classes * 2 * space.fbcsp_m * n_bands if space.fbcsp_m else 0)


def fold_matrices(space: FeatureSpace, subbands: Optional[np.ndarray], y: np.ndarray,
                  tr: np.ndarray, te: np.ndarray) -> tuple:
  """`(X_train, X_test)` of one fold; the CSP (if any) is fitted on `subbands[tr], y[tr]` only."""
  parts_tr, parts_te = [], []
  if space.fbcsp_m:
    csp = FBCSPTransformer(space.fbcsp_m).fit(subbands[tr], y[tr])
    parts_tr.append(csp.transform(subbands[tr]))
    parts_te.append(csp.transform(subbands[te]))
  for b in space.static:
    parts_tr.append(b[tr])
    parts_te.append(b[te])
  return np.hstack(parts_tr), np.hstack(parts_te)


def _softmax(z: np.ndarray) -> np.ndarray:
  z = z - z.max(axis=1, keepdims=True)
  e = np.exp(z)
  return e / e.sum(axis=1, keepdims=True)


def class_scores(model, X: np.ndarray) -> np.ndarray:
  """Per-class scores `(n, K)` in `classes_` order: `predict_proba` if available, else softmax of `decision_function`."""
  if hasattr(model, "predict_proba"):
    return model.predict_proba(X)
  return _softmax(np.asarray(model.decision_function(X), dtype=float))


def oof_space(space: FeatureSpace, subbands: Optional[np.ndarray], y: np.ndarray, models: dict,
              seed: int = SEED, splits: Optional[Sequence] = None) -> tuple:
  """Out-of-fold predictions and scores of every model on one feature space.

  Returns `(results, errors)`: `results[name] = {"pred": (n,), "scores": (n, K)}` with classes in
  sorted label order, each window predicted exactly once by a model that never saw it; `errors[name]`
  holds the first exception text of a model that failed in some fold (that model has no result).
  Each model is a `Pipeline(StandardScaler, clone(model))` fitted on the training fold only.
  """
  y = np.asarray(y)
  classes = np.unique(y)
  if splits is None:
    splits = list(legacy_cv(seed).split(np.zeros((len(y), 1)), y))
  out = {n: {"pred": np.zeros(len(y), dtype=y.dtype), "scores": np.zeros((len(y), len(classes)))}
         for n in models}
  errors: dict = {}
  for tr, te in splits:
    Xtr, Xte = fold_matrices(space, subbands, y, tr, te)
    for name, model in models.items():
      if name in errors:
        continue
      try:
        with warnings.catch_warnings():
          warnings.simplefilter("ignore")
          pipe = Pipeline([("scaler", StandardScaler()), ("clf", clone(model))]).fit(Xtr, y[tr])
          out[name]["pred"][te] = pipe.predict(Xte)
          out[name]["scores"][te] = class_scores(pipe, Xte)
      except Exception as exc:  # e.g. QDA rank failure (PF-12)
        errors[name] = f"{type(exc).__name__}: {exc}"
  return {n: r for n, r in out.items() if n not in errors}, errors


def accuracies(y: np.ndarray, pred: np.ndarray, scores: np.ndarray) -> tuple:
  """`(1.0 s accuracy, 2.0 s smoothed accuracy)` in [0, 1], smoothing = legacy i%5 trial smoothing
  (R8 legacy, PF-02); classes = sorted labels of `y`."""
  classes = np.unique(y)
  sm = classes[np.argmax(smooth_reported(scores), axis=1)]
  return float(accuracy_score(y, pred)), float(accuracy_score(y, sm))


def fbcca_argmax_baseline(fbcca: np.ndarray, y: np.ndarray, target_codes: Sequence[int]) -> tuple:
  """Zero-training baseline: predicted class = argmax of the FBCCA scores, on every clean window.

  Returns `(pred, scores)`; `scores` are the FBCCA scores divided by their row sum, so the legacy
  2.0 s smoothing can be applied (no fitting, hence no folds).
  """
  s = np.asarray(fbcca, dtype=float)
  pred = np.asarray(target_codes)[np.argmax(s, axis=1)]
  return pred, s / np.maximum(s.sum(axis=1, keepdims=True), 1e-12)
