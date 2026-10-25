"""Probability smoothing over consecutive windows (2.0 s decision from 1.0 s windows).

`smooth_probabilities_legacy` is the legacy behaviour of P04-P10 (R8, PF-02): it averages a
window with the previous row of the array whatever trial it belongs to. It moved here from
`scripts/training/train_models.py` in P05 (re-exported there). `smooth_probabilities_mod5`
is the legacy-folder approximation of R8 (`j % 5 == 0` starts a trial), used in P05 only as
a labelled diagnostic.
"""

import numpy as np


def smooth_probabilities_legacy(proba: np.ndarray) -> np.ndarray:
  """legacy (R8, PF-02): `p_0` unchanged, `p_j = (p_{j-1} + p_j) / 2` over the array order.

  No trial reset: a window is averaged with the previous row even across trial boundaries.
  """
  p = np.asarray(proba, dtype=float)
  out = p.copy()
  out[1:] = (p[:-1] + p[1:]) / 2.0
  return out


def smooth_probabilities_mod5(proba: np.ndarray, block: int = 5) -> np.ndarray:
  """Diagnostic variant: like the legacy average but rows with `j % block == 0` stay unchanged.

  Legacy folders have 5 windows per trial in condition order, so `j % 5 == 0` approximates the
  first window of a trial (02_REQUIREMENTS section 5.6); rejected windows shift the blocks.
  """
  p = np.asarray(proba, dtype=float)
  out = p.copy()
  for j in range(1, len(p)):
    if j % block != 0:
      out[j] = (p[j - 1] + p[j]) / 2.0
  return out
