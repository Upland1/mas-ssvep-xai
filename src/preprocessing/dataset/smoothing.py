"""Probability smoothing over consecutive windows (2.0 s decision from 1.0 s windows).

`smooth_probabilities_legacy` is the P04 legacy behaviour (R8, PF-02): it averages a window with
the previous row of the array whatever trial it belongs to. It moved here from
`scripts/training/train_models.py` in P05 (re-exported there); from P05 on it is a labelled
DIAGNOSTIC only. `smooth_probabilities_mod5` is the legacy i%5 trial smoothing of P05-P10
(R8 legacy, PF-02; the original's "2.0s Trial Smoothed"): a reset at `i % 5 == 0` of the
clean array, the reported "2.0 s smoothed" of P05 (decisions.md P05, R11 round 2).
"""

import numpy as np


def smooth_probabilities_legacy(proba: np.ndarray) -> np.ndarray:
  """legacy (R8, PF-02; P04 rule, DIAGNOSTIC from P05): `p_0` unchanged, `p_j = (p_{j-1} + p_j) / 2`.

  No trial reset: a window is averaged with the previous row even across trial boundaries.
  """
  p = np.asarray(proba, dtype=float)
  out = p.copy()
  out[1:] = (p[:-1] + p[1:]) / 2.0
  return out


def smooth_probabilities_mod5(proba: np.ndarray, block: int = 5) -> np.ndarray:
  """legacy i%5 trial smoothing (R8 legacy, PF-02; reported in P05-P10): rows with `j % block == 0`
  stay unchanged, every other row is `(p_{j-1} + p_j) / 2`.

  Legacy folders have 5 windows per trial in condition order, so `j % 5 == 0` approximates the
  first window of a trial (02_REQUIREMENTS section 5.6); rejected windows shift the blocks (the
  legacy flaw, fixed in P11 by true trial ids).
  """
  p = np.asarray(proba, dtype=float)
  out = p.copy()
  for j in range(1, len(p)):
    if j % block != 0:
      out[j] = (p[j - 1] + p[j]) / 2.0
  return out
