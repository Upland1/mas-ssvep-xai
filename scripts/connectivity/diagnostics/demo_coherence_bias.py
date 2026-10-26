"""DIAGNOSTIC (kept, P12.2): reproduce the two coherence bugs before the fix (PF-15, PF-16).

(a) Synthetic: 7 independent white-noise channels vs a shared-source coupled pair, 40 windows of 256
    samples at fs 250 (legacy, PF-04). Per-window coherence at nperseg 128 averaged over windows (the
    historical estimator, biased, about 0.33) against the concatenated estimator at nperseg 256 (R4,
    about 0.01-0.02). Coupled signals stay near 0.98-0.99 in both.
(b) Real data (--subjects, legacy folders, P07 two-tier gate once per subject over 101-105 + 201): per
    stimulus band, baseline coherence before (per-window average) and after (concatenated, matched),
    and the stimulus difference against the broadband (5-35 Hz) baseline (PF-16, apples-to-oranges)
    against the matched baseline. Statistic: mean of the off-diagonal upper-triangle entries.

Output: <reports-dir>/connectivity/coherence_bias_demo.csv (synthetic) and
coherence_bias_demo_<S>.csv per subject, with .meta.txt. Exit code 0 when the synthetic part is in range.
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
  CONDITION_FREQS, LEGACY_FS_HZ, band_for_condition, compute_condition_coherence, load_gated_conditions,
  mean_offdiag, per_window_mean_matrix, summary_rows)

SEED = 0
N_WINDOWS, T, N_CH = 40, 256, 7
BAND = (23.0, 25.0)


def synthetic_demo(fs: float = LEGACY_FS_HZ, seed: int = SEED, n_windows: int = N_WINDOWS) -> list:
  """Rows for independent noise and a coupled pair: per-window averaged vs concatenated."""
  rng = np.random.default_rng(seed)
  indep = rng.standard_normal((n_windows, N_CH, T))
  shared = rng.standard_normal((n_windows, 1, T))
  coupled = shared + 0.1 * rng.standard_normal((n_windows, N_CH, T))
  rows = []
  for name, w in (("independent noise", indep), ("coupled (shared source)", coupled)):
    rows.append(dict(signal=name, n_windows=n_windows, band_lo=BAND[0], band_hi=BAND[1],
                     perwindow_avg_nperseg128=mean_offdiag(per_window_mean_matrix(w, fs, BAND)),
                     concatenated_nperseg256=mean_offdiag(compute_condition_coherence(w, fs, BAND, 256))))
  return rows


def real_demo(processed: Path, subject: str, fs: float = LEGACY_FS_HZ) -> tuple:
  g = load_gated_conditions(processed, subject)
  rows = summary_rows(g["windows"], g["y"], fs)
  for r in rows:
    r["subject"] = subject
  return rows, g


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=[], help="legacy subject folders for part (b)")
  p.add_argument("--data-root", type=Path, default=ROOT / "data" / "processed")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help="legacy 250 (PF-04)")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  out = Path(args.reports_dir) / "connectivity"
  out.mkdir(parents=True, exist_ok=True)
  print("DIAGNOSTIC (PF-15, PF-16): historical bugs reproduced, not a result. fs "
        f"{args.fs:g} (legacy, PF-04).")
  syn = pd.DataFrame(synthetic_demo(args.fs))
  print("\n(a) synthetic, 40 x 256 samples, band 23-25 Hz")
  print(syn.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
  syn.to_csv(out / "coherence_bias_demo.csv", index=False)
  (out / "coherence_bias_demo.meta.txt").write_text(
    f"synthetic seed={SEED} windows={N_WINDOWS}x{T} channels={N_CH} fs={args.fs:g} (legacy PF-04)\n")
  ind = syn.iloc[0]
  ok = (0.30 <= ind.perwindow_avg_nperseg128 <= 0.37) and ind.concatenated_nperseg256 <= 0.03
  for s in args.subjects:
    rows, g = real_demo(Path(args.data_root), s, args.fs)
    df = pd.DataFrame(rows)
    print(f"\n(b) {s}: channels {g['channels_kept']} (dropped {g['channels_dropped'] or 'none'}); "
          f"gate counts {g['counts']}")
    cols = ["condition", "f_c", "n_windows", "n_baseline", "mean_baseline_perwindow", "mean_matched_baseline",
            "mean_baseline_broadband", "mean_difference_broadband", "mean_difference"]
    print(df[cols].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    df.to_csv(out / f"coherence_bias_demo_{s}.csv", index=False)
    (out / f"coherence_bias_demo_{s}.meta.txt").write_text(
      f"subject={s} data={args.data_root} fs={args.fs:g} (legacy PF-04) channels={g['channels_kept']} "
      f"dropped={g['channels_dropped']} gate=P07 two-tier vpp 5-120 std 1-35 fail>50% counts={g['counts']}\n"
      "columns: mean_baseline_perwindow = before (PF-15); mean_matched_baseline = after; "
      "mean_difference_broadband = PF-16 bug; mean_difference = matched\n")
  print(f"\nsynthetic part in range: {ok}")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
