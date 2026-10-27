"""DIAGNOSTIC (kept, P13.1): reproduce the filtfilt + Hilbert edge bug (PF-18) before the CSD fix (R3).

Synthetic: two channels sharing a 24 Hz sinusoid (random phase per window, fixed 0.5 rad lag) plus small
noise, 60 windows of 256 samples at fs 250 (legacy, PF-04), band 23-25 Hz (f_c +- 1 Hz).
(a) Bug: Butterworth band-pass (zero-phase `sosfiltfilt`) + Hilbert on each short window. The envelope in
    the first/last 15 samples is a fraction of its centre value, and the instantaneous frequency is
    unstable there; other filter orders / paddings / wider bands (rows below) do not remove it.
(b) Edge immunity: the first and last 15 samples of every window are replaced by strong noise. The
    CSD-based PLV (`compute_condition_plv`, the reported path) barely moves; the Hilbert PLV drops.

Output: <reports-dir>/connectivity/hilbert_edges_demo.csv (+ .meta.txt). Exit code 0 when the CSD PLV
change is <= 0.005 and the Hilbert edge envelope is below 80 % of the centre.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from scipy.signal import butter, hilbert, sosfiltfilt


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.features.connectivity.connectivity_extraction import LEGACY_FS_HZ  # noqa: E402
from src.features.connectivity.phase_connectivity import compute_condition_plv  # noqa: E402

F0, T, N_WIN, EDGE = 24.0, 256, 60, 15


def make_windows(seed: int = 0, n: int = N_WIN, fs: float = LEGACY_FS_HZ, noise: float = 0.05) -> np.ndarray:
  """`(n, 2, T)`: two phase-locked 24 Hz channels (lag 0.5 rad), random phase per window, small noise."""
  rng = np.random.default_rng(seed)
  t = np.arange(T) / fs
  ph = rng.uniform(0, 2 * np.pi, (n, 1))
  w = np.stack([np.sin(2 * np.pi * F0 * t + ph), np.sin(2 * np.pi * F0 * t + ph + 0.5)], axis=1)
  return w + noise * rng.standard_normal(w.shape)


def corrupt_edges(w: np.ndarray, seed: int = 1, edge: int = EDGE, amp: float = 3.0) -> np.ndarray:
  """Replace the first and last `edge` samples with white noise of std `amp`."""
  rng = np.random.default_rng(seed)
  out = w.copy()
  out[..., :edge] = amp * rng.standard_normal(out[..., :edge].shape)
  out[..., -edge:] = amp * rng.standard_normal(out[..., -edge:].shape)
  return out


def hilbert_analytic(w: np.ndarray, band: tuple, fs: float, order: int = 4, padlen: Optional[int] = None) -> np.ndarray:
  """BUG (PF-18): zero-phase band-pass then Hilbert on each short window; `(n, C, T)` complex."""
  sos = butter(order, band, btype="band", fs=fs, output="sos")
  kw = {} if padlen is None else {"padlen": padlen}
  return hilbert(sosfiltfilt(sos, w, axis=-1, **kw), axis=-1)


def hilbert_plv(w: np.ndarray, band: tuple, fs: float, **kw) -> float:
  """Hilbert PLV of channels 0 and 1 over every (window, sample) pair (the buggy time-domain path)."""
  h = hilbert_analytic(w, band, fs, **kw)
  return float(abs(np.mean(np.exp(1j * (np.angle(h[:, 0]) - np.angle(h[:, 1]))))))


def edge_envelope_ratio(w: np.ndarray, band: tuple, fs: float, edge: int = EDGE, **kw) -> dict:
  """Envelope of channel 0 relative to its centre value: min/max over the first and the last `edge` samples."""
  env = np.abs(hilbert_analytic(w, band, fs, **kw))[:, 0].mean(axis=0)
  centre = env[T // 2 - 25:T // 2 + 25].mean()
  first, last = env[:edge] / centre, env[-edge:] / centre
  inst = np.diff(np.unwrap(np.angle(hilbert_analytic(w, band, fs, **kw)[:, 0])), axis=-1) * fs / (2 * np.pi)
  return dict(first_min=float(first.min()), first_max=float(first.max()), last_min=float(last.min()),
              last_max=float(last.max()), centre_env=float(centre),
              inst_freq_std_edge=float(np.r_[inst[:, :edge].ravel(), inst[:, -edge:].ravel()].std()),
              inst_freq_std_centre=float(inst[:, T // 2 - 25:T // 2 + 25].std()))


def run(fs: float = LEGACY_FS_HZ, seed: int = 0) -> tuple:
  """Rows `(variants, edge_immunity)` as lists of dicts."""
  w = make_windows(seed, fs=fs)
  wc = corrupt_edges(w)
  variants = []
  for name, band, kw in (("order 4, band 23-25 (bug)", (F0 - 1, F0 + 1), {}),
                         ("order 2, band 23-25", (F0 - 1, F0 + 1), dict(order=2)),
                         ("order 4, padlen 100", (F0 - 1, F0 + 1), dict(padlen=100)),
                         ("order 4, band 20-28 (wider)", (F0 - 4, F0 + 4), {})):
    variants.append(dict(variant=name, **edge_envelope_ratio(w, band, fs, **kw)))
  band = (F0 - 1, F0 + 1)
  edge = dict(hilbert_plv_clean=hilbert_plv(w, band, fs), hilbert_plv_corrupted=hilbert_plv(wc, band, fs),
              csd_plv_clean=float(compute_condition_plv(w, fs, band)[0, 1]),
              csd_plv_corrupted=float(compute_condition_plv(wc, fs, band)[0, 1]))
  edge["hilbert_change"] = edge["hilbert_plv_clean"] - edge["hilbert_plv_corrupted"]
  edge["csd_change"] = edge["csd_plv_clean"] - edge["csd_plv_corrupted"]
  return variants, edge


def main(argv: Optional[Sequence[str]] = None) -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ)
  args = p.parse_args(argv)
  variants, edge = run(args.fs)
  vdf = pd.DataFrame(variants)
  print("(a) Hilbert envelope at the window edges, relative to the centre (1.0 = truth); first/last 15 samples")
  print(vdf.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
  print("(b) edge immunity, first/last 15 samples replaced by noise (PLV of channels 0, 1)")
  print(f"  Hilbert PLV: {edge['hilbert_plv_clean']:.4f} -> {edge['hilbert_plv_corrupted']:.4f}")
  print(f"  CSD PLV (reported path): {edge['csd_plv_clean']:.4f} -> {edge['csd_plv_corrupted']:.4f}")
  out = Path(args.reports_dir) / "connectivity"
  out.mkdir(parents=True, exist_ok=True)
  csv = out / "hilbert_edges_demo.csv"
  pd.concat([vdf.assign(part="a_envelope"), pd.DataFrame([edge]).assign(part="b_edge_immunity")]).to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text(
    f"synthetic: {N_WIN} windows x {T} samples, fs {args.fs:g} (legacy, PF-04), f0 {F0} Hz, band f0 +- 1 Hz, "
    f"seed 0; DIAGNOSTIC (PF-18 bug demo); the reported phase path is the CSD (R3)\n")
  ok = abs(edge["csd_change"]) <= 0.005 and variants[0]["first_min"] < 0.8
  print(f"in range (CSD change <= 0.005 and Hilbert edge envelope < 80 % of centre): {ok}")
  print(f"saved {csv}")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
