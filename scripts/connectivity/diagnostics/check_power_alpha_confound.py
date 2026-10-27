"""How much of the connectivity delta follows target SSVEP power and alpha change? (P14.3, PF-23, PF-27)

Data source: legacy folders <data-root>/<S>/ (P02, raw windows), conditions 101-105 and 201 after ONE P07
two-tier gate per subject (the P13 loader, PF-03); fs-250 axis (legacy, PF-04). Hann periodograms per window on
the occipital channels O1, Oz, O2 that survive the gate, averaged over windows and channels (linear power).

Per subject and frequency (stimulus vs the SAME gated 201 baseline windows):
- `target_snr_db = 10 log10(P_stim / P_base)` in f0 +- 1 Hz;
- `alpha_change_db` in 8-13 Hz EXCLUDING f0 +- 1.5 Hz for stimulus and baseline alike, so the target of 10.91 and
  8.57 Hz does not contaminate the alpha measure (PF-23).
The cells are merged with `<method>_global_delta.csv` of the task-1 script (all four methods). Per method:
Spearman of delta vs SNR and vs alpha change over all cells and within-subject centred, OLS R^2 of
`delta ~ SNR + alpha`, in-alpha (10.91, 8.57 Hz) vs out-of-alpha means. 25 cells come from five subjects, so the
cells are not independent and every p-value is descriptive. The S05 pattern flagged in P13 (D-3: coherence and
PLV below baseline, wPLI above) is examined against S05's own SNR and alpha change, exploratory only.

Output: reports/connectivity_comparison/{power_confound_table,power_vs_connectivity_cells,
power_confound_correlations,power_confound_ols,power_confound_alpha_split,power_confound_s05}.csv and
outputs/figures/connectivity_comparison/connectivity_delta_vs_power.png. The misspelled duplicate of the
original (`..._cofound`) is deliberately not created (PF-27).
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from scipy.signal import periodogram
from scipy.stats import spearmanr


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.features.connectivity.connectivity_extraction import (  # noqa: E402
  BASELINE_CONDITION, CONDITION_FREQS, LEGACY_FS_HZ, load_gated_conditions)

METHODS = ("coherence", "plv", "wpli", "pdc")
OCCIPITAL = ("O1", "Oz", "O2")
TARGET_HALF_WIDTH = 1.0
ALPHA_BAND = (8.0, 13.0)
ALPHA_EXCLUDE = 1.5
IN_ALPHA = (104, 105)   # 10.91 and 8.57 Hz lie inside 8-13 Hz
_EPS = 1e-9
TABLE_COLUMNS = ["subject", "condition", "frequency", "target_snr_db", "alpha_change_db", "n_stim_windows",
                 "n_base_windows", "channels_used"]
SOURCE = "legacy windows (P02), raw, fs-250 axis (PF-04)"


def mean_psd(windows: np.ndarray, channel_idx: Sequence[int], fs: float) -> tuple:
  """`(freqs, psd)`: Hann periodogram of each window and selected channel, averaged over both (linear power)."""
  x = np.asarray(windows, dtype=np.float64)[:, list(channel_idx), :]
  f, p = periodogram(x, fs=fs, window="hann", axis=-1)
  return f, p.mean(axis=(0, 1))


def target_mask(freqs: np.ndarray, f0: float, half_width: float = TARGET_HALF_WIDTH) -> np.ndarray:
  """Bins inside f0 +- half_width; the nearest bin if none falls inside."""
  m = np.abs(freqs - f0) <= half_width + _EPS
  if not m.any():
    m = np.zeros(len(freqs), dtype=bool)
    m[int(np.argmin(np.abs(freqs - f0)))] = True
  return m


def alpha_mask(freqs: np.ndarray, f0: float) -> np.ndarray:
  """8-13 Hz bins without f0 +- 1.5 Hz (PF-23); the same mask serves stimulus and baseline."""
  return (freqs >= ALPHA_BAND[0] - _EPS) & (freqs <= ALPHA_BAND[1] + _EPS) & (np.abs(freqs - f0) > ALPHA_EXCLUDE + _EPS)


def db_ratio(p_stim: float, p_base: float) -> float:
  return float(10.0 * np.log10(p_stim / p_base)) if p_stim > 0 and p_base > 0 else float("nan")


def power_metrics(w_stim: np.ndarray, w_base: np.ndarray, channel_idx: Sequence[int], f0: float, fs: float) -> dict:
  """`target_snr_db` and `alpha_change_db` of one condition against the baseline windows."""
  f, ps = mean_psd(w_stim, channel_idx, fs)
  _, pb = mean_psd(w_base, channel_idx, fs)
  tm, am = target_mask(f, f0), alpha_mask(f, f0)
  alpha = db_ratio(ps[am].mean(), pb[am].mean()) if am.any() else float("nan")
  return dict(target_snr_db=db_ratio(ps[tm].mean(), pb[tm].mean()), alpha_change_db=alpha)


def subject_rows(data_root: Path, subject: str, fs: float) -> list:
  d = load_gated_conditions(data_root, subject)
  kept = list(d["channels_kept"])
  idx = [kept.index(c) for c in OCCIPITAL if c in kept]
  used = [kept[i] for i in idx]
  w, y = d["windows"], d["y"]
  base = w[y == BASELINE_CONDITION]
  rows = []
  for c, f0 in CONDITION_FREQS.items():
    stim = w[y == c]
    if not idx or len(stim) == 0 or len(base) == 0:
      m = dict(target_snr_db=float("nan"), alpha_change_db=float("nan"))
    else:
      m = power_metrics(stim, base, idx, f0, fs)
    rows.append(dict(subject=subject, condition=c, frequency=f0, **m, n_stim_windows=len(stim),
                     n_base_windows=len(base), channels_used=";".join(used)))
  return rows


# ------------------------------------------------------------------ statistics

def centre_within_subject(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
  out = df.copy()
  for c in cols:
    out[c] = df[c] - df.groupby("subject")[c].transform("mean")
  return out


def ols_r2(y: np.ndarray, X: np.ndarray) -> tuple:
  """`(r2, coefficients)` of y ~ 1 + X by least squares."""
  y = np.asarray(y, dtype=float)
  A = np.column_stack([np.ones(len(y)), np.asarray(X, dtype=float).reshape(len(y), -1)])
  beta, *_ = np.linalg.lstsq(A, y, rcond=None)
  ss_res = float(((y - A @ beta) ** 2).sum())
  ss_tot = float(((y - y.mean()) ** 2).sum())
  return (1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")), beta


def spearman(x: np.ndarray, y: np.ndarray) -> tuple:
  x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
  ok = np.isfinite(x) & np.isfinite(y)
  if ok.sum() < 3 or np.ptp(x[ok]) == 0 or np.ptp(y[ok]) == 0:
    return float("nan"), float("nan")
  r = spearmanr(x[ok], y[ok])
  return float(r[0]), float(r[1])


def confound_statistics(cells: pd.DataFrame) -> dict:
  """Correlation, OLS and in/out-of-alpha tables from the merged cells (one row per subject x condition x method)."""
  corr, ols, split = [], [], []
  for m, g in cells.groupby("method", sort=False):
    g = g.dropna(subset=["mean_delta", "target_snr_db", "alpha_change_db"]).reset_index(drop=True)
    for scope, d in (("all", g), ("centred", centre_within_subject(g, ["mean_delta", "target_snr_db", "alpha_change_db"]))):
      for pred in ("target_snr_db", "alpha_change_db"):
        rho, p = spearman(d[pred].values, d["mean_delta"].values)
        corr.append(dict(method=m, scope=scope, predictor=pred, n_cells=len(d), spearman_rho=rho, spearman_p=p))
      r2, beta = ols_r2(d["mean_delta"].values, d[["target_snr_db", "alpha_change_db"]].values)
      r2s, _ = ols_r2(d["mean_delta"].values, d[["target_snr_db"]].values)
      r2a, _ = ols_r2(d["mean_delta"].values, d[["alpha_change_db"]].values)
      ols.append(dict(method=m, scope=scope, n_cells=len(d), r2=r2, r2_snr_only=r2s, r2_alpha_only=r2a,
                      intercept=beta[0], coef_snr=beta[1], coef_alpha=beta[2]))
    cen = centre_within_subject(g, ["mean_delta"])
    for name, sel in (("in_alpha", g["condition"].isin(IN_ALPHA)), ("out_of_alpha", ~g["condition"].isin(IN_ALPHA))):
      split.append(dict(method=m, group=name, n_cells=int(sel.sum()), mean_delta=float(g.loc[sel, "mean_delta"].mean()),
                        mean_delta_centred=float(cen.loc[sel, "mean_delta"].mean()),
                        mean_target_snr_db=float(g.loc[sel, "target_snr_db"].mean()),
                        mean_alpha_change_db=float(g.loc[sel, "alpha_change_db"].mean())))
  return dict(correlations=pd.DataFrame(corr), ols=pd.DataFrame(ols), alpha_split=pd.DataFrame(split))


def s05_table(cells: pd.DataFrame, subject: str = "S05") -> pd.DataFrame:
  """S05 delta per method and frequency next to S05's own SNR and alpha change (P13 D-3, exploratory)."""
  g = cells[cells["subject"] == subject].copy()
  rows = []
  for m, x in g.groupby("method", sort=False):
    rho_s, _ = spearman(x["target_snr_db"].values, x["mean_delta"].values)
    rho_a, _ = spearman(x["alpha_change_db"].values, x["mean_delta"].values)
    for _, r in x.iterrows():
      rows.append(dict(subject=subject, method=m, condition=int(r["condition"]), frequency=r["frequency"],
                       mean_delta=r["mean_delta"], target_snr_db=r["target_snr_db"],
                       alpha_change_db=r["alpha_change_db"], n_freq_delta_below_zero=int((x["mean_delta"] < 0).sum()),
                       spearman_delta_snr_within_subject=rho_s, spearman_delta_alpha_within_subject=rho_a))
  return pd.DataFrame(rows)


def load_global_deltas(comp_dir: Path, methods: Sequence[str]) -> pd.DataFrame:
  parts = []
  for m in methods:
    p = Path(comp_dir) / f"{m}_global_delta.csv"
    if not p.is_file():
      raise SystemExit(f"{p} is missing: run compare_connectivity_frequencies first")
    parts.append(pd.read_csv(p))
  return pd.concat(parts, ignore_index=True)


def merge_cells(power: pd.DataFrame, deltas: pd.DataFrame) -> pd.DataFrame:
  return power.merge(deltas[["subject", "method", "condition", "mean_delta"]], on=["subject", "condition"],
                     how="inner", validate="one_to_many")


def scatter_figure(cells: pd.DataFrame, path: Path) -> Path:
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  methods = list(dict.fromkeys(cells["method"]))
  subjects = sorted(cells["subject"].unique())
  colors = plt.get_cmap("tab10")
  fig, axes = plt.subplots(len(methods), 2, figsize=(7.5, 2.4 * len(methods)), squeeze=False)
  for i, m in enumerate(methods):
    g = cells[cells["method"] == m]
    for j, (xcol, xlab) in enumerate((("target_snr_db", "target SNR (dB)"), ("alpha_change_db", "alpha change (dB)"))):
      ax = axes[i, j]
      for k, s in enumerate(subjects):
        x = g[g["subject"] == s]
        ina = x["condition"].isin(IN_ALPHA)
        ax.scatter(x.loc[~ina, xcol], x.loc[~ina, "mean_delta"], color=colors(k), marker="o", s=18, label=s)
        ax.scatter(x.loc[ina, xcol], x.loc[ina, "mean_delta"], color=colors(k), marker="s", s=26,
                   edgecolor="k", linewidth=0.6)
      ax.axhline(0, color="0.7", lw=0.6)
      ax.set_xlabel(xlab, fontsize=7)
      ax.set_ylabel(f"{m} mean delta", fontsize=7)
      ax.tick_params(labelsize=6)
  h, l = axes[0, 0].get_legend_handles_labels()
  fig.legend(h, l, loc="upper right", fontsize=6, ncol=len(subjects), title="squares with edge: 10.91 / 8.57 Hz", title_fontsize=6)
  fig.tight_layout(rect=(0, 0, 1, 0.97))
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  fig.savefig(path, dpi=130)
  plt.close(fig)
  return Path(path)


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="+", default=None, help="default: every S<digits> folder in the data root")
  p.add_argument("--methods", nargs="+", choices=list(METHODS), default=list(METHODS))
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help="frequency axis, legacy 250 (PF-04)")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  p.add_argument("--figures-dir", type=Path, default=ROOT / "outputs" / "figures" / "connectivity_comparison")
  p.add_argument("--no-figures", action="store_true")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  comp = Path(args.reports_dir) / "connectivity_comparison"
  comp.mkdir(parents=True, exist_ok=True)
  subjects = args.subjects or sorted(d.name for d in Path(args.data_root).iterdir()
                                     if d.is_dir() and re.fullmatch(r"S\d+", d.name))
  print(f"Data source: {SOURCE}; subjects {subjects}; O1/Oz/O2 Hann periodograms; target f0 +- {TARGET_HALF_WIDTH:g} Hz; "
        f"alpha {ALPHA_BAND[0]:g}-{ALPHA_BAND[1]:g} Hz without f0 +- {ALPHA_EXCLUDE:g} Hz (PF-23)")
  power = pd.DataFrame([r for s in subjects for r in subject_rows(args.data_root, s, args.fs)], columns=TABLE_COLUMNS)
  power.to_csv(comp / "power_confound_table.csv", index=False)
  deltas = load_global_deltas(comp, args.methods)
  cells = merge_cells(power, deltas[deltas["subject"].isin(subjects)])
  cells.to_csv(comp / "power_vs_connectivity_cells.csv", index=False)
  st = confound_statistics(cells)
  st["correlations"].to_csv(comp / "power_confound_correlations.csv", index=False)
  st["ols"].to_csv(comp / "power_confound_ols.csv", index=False)
  st["alpha_split"].to_csv(comp / "power_confound_alpha_split.csv", index=False)
  s05 = s05_table(cells)
  s05.to_csv(comp / "power_confound_s05.csv", index=False)
  fmt = {"float_format": lambda v: f"{v:.3f}"}
  print(power.drop(columns=["channels_used"]).to_string(index=False, **fmt))
  print("\nSpearman (descriptive; cells are not independent):")
  print(st["correlations"].to_string(index=False, **fmt))
  print("\nOLS delta ~ SNR + alpha:")
  print(st["ols"].to_string(index=False, **fmt))
  print("\nIn-alpha (10.91, 8.57 Hz) vs out-of-alpha:")
  print(st["alpha_split"].to_string(index=False, **fmt))
  if len(s05):
    print("\nS05 (P13 D-3, exploratory):")
    print(s05.drop(columns=["subject"]).to_string(index=False, **fmt))
  if not args.no_figures:
    print(f"saved {scatter_figure(cells, Path(args.figures_dir) / 'connectivity_delta_vs_power.png')}")
  print(f"saved CSVs in {comp}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
