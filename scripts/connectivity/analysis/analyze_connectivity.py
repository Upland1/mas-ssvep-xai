"""Per-subject connectivity analysis (P12.4): coherence, stimulus vs matched baseline.

Data source: legacy folder <data-root>/<S>/ (P02, 7 channels, raw windows, no continuous filtering,
R3 era B), conditions 101-105 and 201; fs 250 on the frequency axis (legacy, PF-04). One P07 two-tier
gate (vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of windows) over the union of
101-105 and 201. Estimator: concatenated windows, one Welch coherence per pair (R4); bands f_c +- 1 Hz;
baseline = the same 201 windows re-scored in each stimulus band (PF-16). Descriptive only (P13 tests).

Output: <reports-dir>/connectivity/coherence_<S>_matrices.npz, coherence_<S>_summary.csv (+ .meta.txt);
<figures-dir>/coherence_<S>_raw_panel.png and coherence_<S>_difference_panel.png.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


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
  BASELINE_CONDITION, CONDITION_FREQS, GATE, LEGACY_FS_HZ, compute_baseline_matched_connectivity,
  compute_condition_connectivity, compute_difference_matrices, load_gated_conditions, summary_rows)


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", required=True)
  p.add_argument("--method", choices=["coherence"], default="coherence")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help="frequency axis, legacy 250 (PF-04)")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  p.add_argument("--figures-dir", type=Path, default=ROOT / "outputs" / "figures" / "connectivity")
  p.add_argument("--no-figures", action="store_true")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  s = args.subject
  g = load_gated_conditions(Path(args.data_root), s)
  w, y, names = g["windows"], g["y"], g["channels_kept"]
  print(f"Data source: legacy windows {args.data_root}/{s} (P02), fs {args.fs:g} (legacy, PF-04), "
        f"method {args.method}")
  print(f"Channels kept {names}; dropped {g['channels_dropped'] or 'none'}; gate {GATE}")
  for c, n in g["counts"].items():
    print(f"  {c}: total {n['total']}, clean {n['clean']}, rejected {n['rejected']}")
  stim = compute_condition_connectivity(w, y, args.fs)
  matched, idx = compute_baseline_matched_connectivity(w, y, args.fs)
  diffs = compute_difference_matrices(stim, matched)
  rows = summary_rows(w, y, args.fs)
  df = pd.DataFrame(rows)
  df.insert(0, "subject", s)
  print(df[["condition", "band_lo", "band_hi", "n_windows", "mean_raw", "mean_matched_baseline",
            "mean_difference", "mean_baseline_perwindow"]].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
  out = Path(args.reports_dir) / "connectivity"
  out.mkdir(parents=True, exist_ok=True)
  save = {"channels": np.array(names), "baseline_window_idx": idx}
  for c in CONDITION_FREQS:
    if c in stim:
      save[f"raw_{c}"], save[f"matched_{c}"], save[f"diff_{c}"] = stim[c], matched[c], diffs[c]
  if BASELINE_CONDITION in stim:
    save["raw_201_broadband"] = stim[BASELINE_CONDITION]
  np.savez(out / f"coherence_{s}_matrices.npz", **save)
  csv = out / f"coherence_{s}_summary.csv"
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text(
    f"subject={s} method={args.method} data={args.data_root} (legacy, 7 ch, raw windows, R3 era B)\n"
    f"fs={args.fs:g} (legacy PF-04) bands=f_c+-1 Hz nperseg=256 concatenated (R4), matched baseline (PF-16)\n"
    f"gate=P07 two-tier {GATE}\nchannels={names} dropped={g['channels_dropped']}\ncounts={g['counts']}\n")
  if not args.no_figures:
    from src.visualization.connectivity_plots import plot_all_conditions_panel, plot_difference_panel
    fd = Path(args.figures_dir)
    plot_all_conditions_panel(stim, names, f"{s} coherence per condition", fd / f"coherence_{s}_raw_panel.png")
    plot_difference_panel(diffs, names, f"{s} stimulus minus matched baseline", fd / f"coherence_{s}_difference_panel.png")
  print(f"saved {csv}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
