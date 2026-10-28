"""Edge effects of per-window sub-band filtering (P16.3, PF-14, R3).

For one subject: every FBCSP (Butterworth, 5 bands) and FBCCA (Chebyshev I, 3 bands) band is computed both
ways on the same stimulus windows (101-105) of the OO recording: `continuous` (filter the whole broadband
recording, then cut: the reference) and `per_window` (cut, then filter each window alone: legacy). Both start
from the same continuous 1-90 Hz + notch broadband signal, so the difference is the sub-band filtering only.

relative error = |per_window - continuous| / RMS(continuous), RMS over all windows, channels and samples of
that band. Per band the table gives the mean relative error (%) in the first and last 100 ms ("edges"),
and in the middle half of the window ("centre"), and `edge_to_centre_ratio` = edges / centre. Only windows
that pass the shared quality gate are used, so artifacts do not set the RMS.

Outputs: `reports/edge_effects_summary.csv` (subject, band, filter, rel_error_edges_pct,
rel_error_centre_pct, edge_to_centre_ratio) and a 3-panel figure
`outputs/figures/edge_effects/edge_effects_<S>.png`: (1) an example trace of a 15 Hz window on Oz in the
13-17 Hz band, both ways; (2) the error profile over the window for a narrow (13-17 Hz) and a wide (6-90 Hz)
band; (3) edge and centre error of every band. Data source: continuous 1-90 Hz build of <session>.ebr.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else two levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from scripts import build_windows as bw  # noqa: E402
from src.io import ebr_parser  # noqa: E402
from src.preprocessing.windowing import band_windows, filter_bank, load_session  # noqa: E402

COLUMNS = ["subject", "band", "filter", "rel_error_edges_pct", "rel_error_centre_pct", "edge_to_centre_ratio"]
EDGE_SEC = 0.1
NARROW = ("fbcsp", "13-17")
WIDE = ("fbcca", "6-90")
EXAMPLE_FREQ_CODE = 103          # 15.00 Hz
EXAMPLE_CHANNEL = "Oz"


def relative_error(pw: np.ndarray, cont: np.ndarray) -> np.ndarray:
  """|pw - cont| / RMS(cont) with one RMS per band: `(n, B, C, T)` inputs -> `(n, B, C, T)` errors.

  Raises ValueError for shape mismatches and for a band whose continuous RMS is zero.
  """
  if pw.shape != cont.shape or cont.ndim != 4:
    raise ValueError(f"need two (n, B, C, T) arrays of equal shape, got {pw.shape} and {cont.shape}")
  rms = np.sqrt((cont ** 2).mean(axis=(0, 2, 3)))
  if np.any(rms == 0):
    raise ValueError("a band has zero RMS")
  return np.abs(pw - cont) / rms[None, :, None, None]


def edge_centre(err: np.ndarray, fs: float, edge_sec: float = EDGE_SEC) -> tuple:
  """`(edges (B,), centre (B,))` mean relative error in the first+last `edge_sec` and in the middle half."""
  T = err.shape[-1]
  e = int(round(edge_sec * fs))
  if 2 * e >= T // 2:
    raise ValueError(f"edge of {edge_sec} s overlaps the centre of a {T}-sample window")
  edges = np.concatenate([err[..., :e], err[..., T - e:]], axis=-1).mean(axis=(0, 2, 3))
  centre = err[..., T // 4: T - T // 4].mean(axis=(0, 2, 3))
  return edges, centre


def band_label(f) -> str:
  return f"{f.low:g}-{f.high:g}"


def summary_rows(subject: str, errs: dict, banks: dict, fs: float) -> list:
  """Table rows (`COLUMNS`) from `errs[bank] = (n, B, C, T)` relative errors and `banks[bank]` filter lists."""
  rows = []
  for name, err in errs.items():
    edges, centre = edge_centre(err, fs)
    for f, a, c in zip(banks[name], edges, centre):
      rows.append({"subject": subject, "band": band_label(f), "filter": name,
                   "rel_error_edges_pct": 100 * float(a), "rel_error_centre_pct": 100 * float(c),
                   "edge_to_centre_ratio": float(a / c) if c > 0 else float("nan")})
  return rows


def compute(x: np.ndarray, mark: np.ndarray, fs: float, params: dict) -> dict:
  """Both-ways bands of the valid stimulus windows of a recording: `{windows, cont, pw, errs, banks, idx}`."""
  built = bw.build_subject(x, mark, fs, {**params, "banks": []})
  idx, q = built["idx"], built["quality"]
  sel = np.flatnonzero(np.isin(idx.labels, params["stim_conditions"]) & (q["valid_mask"] == 1))
  if len(sel) == 0:
    raise ValueError("no valid stimulus window")
  starts, n = idx.starts[sel], built["n_samples"]
  keep = q["channels_kept_idx"]
  banks, cont, pw, errs = {}, {}, {}, {}
  for name in ("fbcsp", "fbcca"):
    banks[name] = filter_bank(name, fs)
    cont[name] = band_windows(built["broadband"], starts, n, banks[name], "continuous")[:, :, keep, :]
    pw[name] = band_windows(built["broadband"], starts, n, banks[name], "per_window")[:, :, keep, :]
    errs[name] = relative_error(pw[name], cont[name])
  return {"sel": sel, "idx": idx, "cont": cont, "pw": pw, "errs": errs, "banks": banks, "built": built,
          "channels": [params["scalp"][i] for i in keep]}


def make_figure(res: dict, subject: str, fs: float, path: Path) -> Path:
  """The 3-panel figure (module docstring)."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  fig, ax = plt.subplots(1, 3, figsize=(17, 4.6))
  labels = [band_label(f) for f in res["banks"][NARROW[0]]]
  b = labels.index(NARROW[1])
  ch = res["channels"].index(EXAMPLE_CHANNEL) if EXAMPLE_CHANNEL in res["channels"] else 0
  y = res["idx"].labels[res["sel"]]
  w = int(np.flatnonzero(y == EXAMPLE_FREQ_CODE)[0]) if (y == EXAMPLE_FREQ_CODE).any() else 0
  T = res["cont"][NARROW[0]].shape[-1]
  t = np.arange(T) / fs * 1000.0
  ax[0].plot(t, res["cont"][NARROW[0]][w, b, ch], label="continuous (reference)")
  ax[0].plot(t, res["pw"][NARROW[0]][w, b, ch], "--", label="per window (legacy)")
  e = EDGE_SEC * 1000
  for lo, hi in ((0, e), (t[-1] - e, t[-1])):
    ax[0].axvspan(lo, hi, color="grey", alpha=0.2)
  ax[0].set(title=f"{subject}: 15 Hz window, {res['channels'][ch]}, {NARROW[1]} Hz band", xlabel="time in window (ms)",
            ylabel="amplitude (uV)")
  ax[0].legend(loc="upper right", fontsize=8)
  for (bank, band), style in ((NARROW, "-"), (WIDE, "--")):
    k = [band_label(f) for f in res["banks"][bank]].index(band)
    prof = 100 * res["errs"][bank][:, k].mean(axis=(0, 1))
    ax[1].plot(t, prof, style, label=f"{bank} {band} Hz")
  ax[1].set(title="relative error over the window", xlabel="time in window (ms)", ylabel="|pw - cont| / RMS(cont) (%)")
  ax[1].legend(fontsize=8)
  names, edge_v, centre_v = [], [], []
  for bank in ("fbcsp", "fbcca"):
    a, c = edge_centre(res["errs"][bank], fs)
    names += [f"{bank}\n{band_label(f)}" for f in res["banks"][bank]]
    edge_v += list(100 * a)
    centre_v += list(100 * c)
  xs = np.arange(len(names))
  ax[2].bar(xs - 0.2, edge_v, 0.4, label="first/last 100 ms")
  ax[2].bar(xs + 0.2, centre_v, 0.4, label="centre")
  ax[2].set_xticks(xs)
  ax[2].set_xticklabels(names, fontsize=7)
  ax[2].set(title="edge vs centre error per band", ylabel="mean relative error (%)")
  ax[2].legend(fontsize=8)
  fig.tight_layout()
  fig.savefig(path, dpi=130)
  plt.close(fig)
  return path


def write_summary(rows: list, path: Path) -> Path:
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS)
    w.writeheader()
    w.writerows(rows)
  return path


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", nargs="+", default=["S03"], help="subject folder(s) (default: S03)")
  p.add_argument("--session", default="OO", help="recording file stem (default: OO)")
  p.add_argument("--raw-dir", type=Path, default=None, help="default: <root>/ + paths.data_raw_dir")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports", help="folder of edge_effects_summary.csv")
  p.add_argument("--figures-dir", type=Path, default=ROOT / "outputs" / "figures", help="folder holding edge_effects/")
  p.add_argument("--config", type=Path, default=bw.DEFAULT_CONFIG)
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  # P19 C-1: the source is explicit (`filtered`, the P16 decision this demo reports), not the config default `both`
  ba = bw.build_parser().parse_args(["--session", args.session, "--banks", "fbcca", "fbcsp",
                                     "--quality-source", "filtered"])
  try:
    cfg = bw.load_build_config(args.config)
    params = bw.resolve_params(cfg, ba)
  except (OSError, ValueError) as exc:
    print(f"[x] Config: {exc}")
    return 1
  raw_dir = args.raw_dir or ROOT / cfg.get("paths", {}).get("data_raw_dir", "data/raw")
  rows, done = [], []
  for subject in args.subject:
    try:
      path = ebr_parser.resolve_recording_path(raw_dir, subject, args.session)
      x, mark, fs = load_session(path, params["scalp"], params["mark_channel"])
      res = compute(x, mark, fs, params)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      continue
    r = summary_rows(subject, res["errs"], res["banks"], fs)
    rows += r
    done.append(subject)
    print(f"[+] {subject}/{path.name}: fs {fs:g} Hz, {len(res['sel'])} valid stimulus windows, channels {res['channels']}")
    print(f"  {'filter':6s} {'band':>7s} {'edges %':>9s} {'centre %':>9s} {'ratio':>8s}")
    for row in r:
      print(f"  {row['filter']:6s} {row['band']:>7s} {row['rel_error_edges_pct']:9.3f} "
            f"{row['rel_error_centre_pct']:9.3f} {row['edge_to_centre_ratio']:8.2f}")
    fig = make_figure(res, subject, fs, Path(args.figures_dir) / "edge_effects" / f"edge_effects_{subject}.png")
    print(f"  Figure: {fig}")
  if not done:
    return 1
  out = write_summary(rows, Path(args.reports_dir) / "edge_effects_summary.csv")
  narrow = [r for r in rows if r["filter"] == "fbcsp"]
  print(f"Cohort: {len(done)} subject(s); fbcsp edge/centre ratio {min(r['edge_to_centre_ratio'] for r in narrow):.2f}"
        f"-{max(r['edge_to_centre_ratio'] for r in narrow):.2f}")
  print(f"Saved: {out}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
