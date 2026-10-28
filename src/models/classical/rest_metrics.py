"""Six-class (stimulus + rest) metrics of P17 (02_REQUIREMENTS 5.7), all in percent.

Rest = the fixation cross, condition 201. With `rest` the rest label and "stimulus" every other window:
- `FalseAct`: rest windows predicted as ANY stimulus, % of rest windows;
- `Missed`: stimulus windows predicted as rest, % of stimulus windows;
- `StimCorrect`: stimulus windows predicted as their OWN stimulus, % of stimulus windows;
- `BalAcc`: mean per-class recall over the classes present in `y` (sklearn `balanced_accuracy_score`).
Confusion matrices have rows = true class and columns = predicted class, in the order of `classes`.
"""

from typing import Sequence

import numpy as np
from sklearn.metrics import balanced_accuracy_score

REST_LABEL = 201
METRICS = ("BalAcc", "FalseAct", "Missed", "StimCorrect")


def confusion_counts(y: np.ndarray, pred: np.ndarray, classes: Sequence[int]) -> np.ndarray:
  """`(K, K)` integer counts, rows = true class, columns = predicted class, in the order of `classes`."""
  idx = {int(c): i for i, c in enumerate(classes)}
  cm = np.zeros((len(idx), len(idx)), dtype=np.int64)
  for t, p in zip(np.asarray(y), np.asarray(pred)):
    cm[idx[int(t)], idx[int(p)]] += 1
  return cm


def rest_metrics(y: np.ndarray, pred: np.ndarray, rest: int = REST_LABEL) -> dict:
  """`{"BalAcc", "FalseAct", "Missed", "StimCorrect"}` in percent (NaN where the denominator is empty)."""
  y, pred = np.asarray(y), np.asarray(pred)
  is_rest, stim = y == rest, y != rest
  nan = float("nan")
  return {
      "BalAcc": 100.0 * float(balanced_accuracy_score(y, pred)),
      "FalseAct": 100.0 * float((pred[is_rest] != rest).mean()) if is_rest.any() else nan,
      "Missed": 100.0 * float((pred[stim] == rest).mean()) if stim.any() else nan,
      "StimCorrect": 100.0 * float((pred[stim] == y[stim]).mean()) if stim.any() else nan,
  }
