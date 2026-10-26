"""Circle plots of channel connectivity per condition (P12.3), MNE-style via mne_connectivity.

Raw panel: one circle per condition (0 .. shared max). Difference panel (the primary output): stimulus
minus matched baseline, diverging `RdBu_r`, colour limits symmetric around 0 and shared by all
conditions. Matrices are `(C, C)` with a NaN diagonal; NaN is drawn as 0.
"""

from pathlib import Path
from typing import Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import cm, colors  # noqa: E402
from mne_connectivity.viz import plot_connectivity_circle  # noqa: E402

CONDITION_LABELS = {101: "24 Hz (101)", 102: "20 Hz (102)", 103: "15 Hz (103)",
                    104: "10.91 Hz (104)", 105: "8.57 Hz (105)", 201: "No stimulus (201)\n5-35 Hz broadband, not band-matched"}
RAW_CMAP = "viridis"
DIFF_CMAP = "RdBu_r"


def _clean(m: np.ndarray) -> np.ndarray:
  return np.nan_to_num(np.asarray(m, dtype=float), nan=0.0)


def symmetric_limit(matrices: dict) -> float:
  """Largest absolute off-diagonal value over all matrices (the shared `vmax` of a difference panel)."""
  v = max((np.abs(_clean(m)).max() for m in matrices.values()), default=0.0)
  return float(v) if v > 0 else 1.0


def _circle(m, names, ax, vmin, vmax, cmap, title):
  plot_connectivity_circle(_clean(m), list(names), n_lines=None, vmin=vmin, vmax=vmax, colormap=cmap,
                           colorbar=False, title=title, ax=ax, facecolor="white", textcolor="black",
                           node_edgecolor="gray", interactive=False, show=False, fontsize_title=10)


def plot_condition_connectivity(matrix: np.ndarray, names: Sequence[str], title: str = "", vmin: float = 0.0,
                                vmax: Optional[float] = None, cmap: str = RAW_CMAP, path: Optional[Path] = None):
  """One circle plot; returns the figure (saved to `path` if given)."""
  vmax = float(np.nanmax(_clean(matrix))) if vmax is None else vmax
  fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
  _circle(matrix, names, ax, vmin, vmax, cmap, title)
  if path is not None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
  return fig


def _panel(matrices, names, titles, vmin, vmax, cmap, label, suptitle, path):
  conds = list(matrices)
  fig, axes = plt.subplots(1, len(conds), figsize=(4.2 * len(conds), 4.8), subplot_kw=dict(polar=True), squeeze=False)
  for ax, c in zip(axes[0], conds):
    _circle(matrices[c], names, ax, vmin, vmax, cmap, titles.get(c, str(c)))
  fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin, vmax), cmap=cmap), ax=list(axes[0]),
               orientation="horizontal", fraction=0.04, pad=0.08, label=label)
  fig.suptitle(suptitle)
  if path is not None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
  return fig


def plot_all_conditions_panel(matrices: dict, names: Sequence[str], suptitle: str = "Coherence per condition",
                              path: Optional[Path] = None):
  """Raw panel: one circle per condition, shared colour range `[0, max]`."""
  vmax = max(float(np.nanmax(_clean(m))) for m in matrices.values())
  return _panel(matrices, names, CONDITION_LABELS, 0.0, vmax, RAW_CMAP, "coherence", suptitle, path)


def plot_difference_panel(diffs: dict, names: Sequence[str], suptitle: str = "Stimulus minus matched baseline",
                          path: Optional[Path] = None):
  """Difference panel (primary output): `RdBu_r`, `vmin = -vmax`, shared by all conditions."""
  vmax = symmetric_limit(diffs)
  return _panel(diffs, names, CONDITION_LABELS, -vmax, vmax, DIFF_CMAP, "coherence difference", suptitle, path)


def plot_permutation_null_distributions(*args, **kwargs):
  """Completed in P13 (permutation nulls); not part of P12."""
  raise NotImplementedError("P13")
