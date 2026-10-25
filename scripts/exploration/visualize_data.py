"""Per-class features of the legacy windows (P03.2): quality mask, stimulus windows, PSD by class.

For each subject: read <processed-dir>/<S>/{X_time_windows,y_labels,
X_psd_features}.npy (P02, never the root arrays: PF-09), run the quality mask
`validate_eeg_windows` with every threshold passed explicitly (R5 legacy
per-script gate; default the P02 legacy limits: vpp 0.5-200 uV, std 0.5-60 uV,
`vpp_max` and `std_range` from the config, `vpp_min` the legacy constant), keep
the accepted stimulus windows (101-105), compute periodogram PSD features
(5-35 Hz, P02 layout: channel-major, 31 bins at fs 256, 30 at fs 250) and plot
the per-class mean PSD, one panel per channel (names from config
`channels.scalp`, length checked against the array).

Prints windows kept/rejected by the mask (per label and reason), the per-class
counts and, when the PSD is computed at the header fs, the largest difference
from the saved X_psd_features (consistency check).

fs: default `--fs 250` (legacy, PF-04); `--fs 256` = header rate. Printed and
in the figure title. Figures: <figures-dir>/exploration/<S>/
psd_features_by_class[_<suffix>].png. P05 adds the blocks fbcca and fbcsp (`--features`, default psd fbcca fbcsp):
fbcca_features_by_class[_<suffix>].png (mean FBCCA score per class and target, fs given by
`--fs`, per-window Chebyshev sub-bands: legacy R3/PF-14) and fbcsp_features_by_class
[_<suffix>].png (mean FBCSP feature per class). The FBCSP block fits the CSP filters on ALL
accepted stimulus windows and labels shown, so it is a full-data fit for visualization only
(R2 exception, PF-11; the caption of the figure says so); never feed it to a model. Both blocks
use the windows already accepted by the mask above (no second gate, PF-10).
Data source: legacy, data/processed/<S>/ from P02.
"""

import argparse
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

from scripts.exploration.diagnose_occipital_spectra import (  # noqa: E402
  DATA_SOURCE, DEFAULT_CONFIG, DEFAULT_SUBJECT, figure_path, header_fs, load_config,
  load_legacy_windows, resolve_subjects, stimulus_conditions)
from src.io.channels import legacy_scalp  # noqa: E402
from src.features.ssvep.fbcca_extraction import TARGET_FREQS, extract_fbcca_features  # noqa: E402
from src.features.ssvep.fbcsp_extraction import extract_fbcsp_features  # noqa: E402
from src.features.ssvep.spectral_power import (  # noqa: E402
  LEGACY_FS_HZ, fs_label, psd_features, select_channels_by_name)
from src.preprocessing.signal.quality_check import (  # noqa: E402
  REJECT_REASONS, validate_eeg_windows, window_quality_flags)

# legacy: lower Vpp limit of the P02 raw gate; config v1 has no key for it (PF-07, as P02).
LEGACY_VPP_MIN_UV = 0.5
FIGURE_STEM = "psd_features_by_class"


# --- Quality mask --------------------------------------------------------------

def quality_mask(X_time: np.ndarray, y: np.ndarray, *, vpp_min: float, vpp_max: float,
                 std_min: float, std_max: float) -> dict:
  """`validate_eeg_windows` with every threshold explicit, plus rejections per label and reason.

  Returns `mask (n,) int`, `n_kept`, `n_rejected`, `by_label` {code: {n, kept,
  rejected, reasons {reason: rejected windows failing it on any channel}}} and
  `thresholds`. Raises ValueError on a length mismatch.
  """
  X = np.asarray(X_time, dtype=np.float64)
  y = np.asarray(y).reshape(-1)
  if len(X) != len(y):
    raise ValueError(f"length mismatch: X_time {len(X)}, y {len(y)}")
  th = {"vpp_min": float(vpp_min), "vpp_max": float(vpp_max),
        "std_min": float(std_min), "std_max": float(std_max)}
  mask = validate_eeg_windows(X, **th)  # R5: no inherited default
  flags = window_quality_flags(X, **th)
  rejected = mask == 0
  by_label = {}
  for code in sorted(set(int(v) for v in y)):
    rows = y == code
    by_label[code] = {
      "n": int(rows.sum()), "kept": int((rows & ~rejected).sum()),
      "rejected": int((rows & rejected).sum()),
      "reasons": {r: int(np.sum(np.any(flags[r], axis=-1) & rows & rejected))
                  for r in REJECT_REASONS}}
  return {"mask": mask, "n_kept": int((~rejected).sum()), "n_rejected": int(rejected.sum()),
          "by_label": by_label, "thresholds": th}


def format_quality(subject: str, q: dict) -> str:
  """Console block of `quality_mask`: totals, thresholds, per label and reason."""
  th = q["thresholds"]
  lines = [f"  {subject} quality mask: kept {q['n_kept']}/{q['n_kept'] + q['n_rejected']}, "
           f"rejected {q['n_rejected']} (vpp [{th['vpp_min']:g}, {th['vpp_max']:g}] uV, "
           f"std [{th['std_min']:g}, {th['std_max']:g}] uV)"]
  for code, c in q["by_label"].items():
    reasons = ", ".join(f"{r} {c['reasons'][r]}" for r in REJECT_REASONS)
    lines.append(f"    {code}: kept {c['kept']}/{c['n']}, rejected {c['rejected']} ({reasons})")
  return "\n".join(lines)


# --- Feature blocks --------------------------------------------------------------

def psd_block(X_stim: np.ndarray, fs: float, freq_range: tuple, y: Optional[np.ndarray] = None) -> dict:
  """Periodogram block: `X (n, C*F)`, `freqs (F,)`, `per_window (n, C, F)`."""
  X, freqs, psd = psd_features(X_stim, fs, freq_range)
  return {"X": X, "freqs": freqs, "per_window": psd}


def fbcca_block(X_stim: np.ndarray, fs: float, freq_range: tuple, y: Optional[np.ndarray] = None) -> dict:
  """FBCCA block (P05.1): `X (n, 5)` scores per target, `freqs` = the 5 targets, `per_window` = X.

  The windows are already accepted by the script's mask, so the extractor gate is bypassed with an
  all-ones mask (PF-10). legacy (R3/PF-14): per-window sub-band filtering.
  """
  X, _, _ = extract_fbcca_features(X_stim, np.zeros(len(X_stim)), fs, valid_mask=np.ones(len(X_stim), int))
  return {"X": X, "freqs": np.asarray(TARGET_FREQS), "per_window": X}


def fbcsp_block(X_stim: np.ndarray, fs: float, freq_range: tuple, y: Optional[np.ndarray] = None) -> dict:
  """FBCSP block (P05.2, m = 1): `X (n, 50)`, `per_window` = X. FULL-DATA CSP fit: visualization only (R2 exception, PF-11)."""
  if y is None:
    raise ValueError("the FBCSP block needs the class labels")
  X, _, _ = extract_fbcsp_features(X_stim, y, fs, m=1, valid_mask=np.ones(len(X_stim), int))
  return {"X": X, "freqs": np.arange(X.shape[1]), "per_window": X}


FEATURE_BLOCKS: dict = {"psd": psd_block, "fbcca": fbcca_block, "fbcsp": fbcsp_block}


def class_means(per_window: np.ndarray, y: np.ndarray, conditions: Sequence[int]) -> tuple:
  """`({code: mean over the class windows (C, F)}, {code: count})`; empty classes left out."""
  means, counts = {}, {}
  for code in conditions:
    rows = np.asarray(y) == code
    counts[int(code)] = int(rows.sum())
    if rows.any():
      means[int(code)] = per_window[rows].mean(axis=0)
  return means, counts


def explore_subject(d: dict, fs: float, channel_names: Sequence[str], conditions: Sequence[int],
                    freq_range: tuple, thresholds: dict,
                    blocks: Sequence[str] = ("psd",)) -> dict:
  """Mask, stimulus selection and feature blocks of one subject (no file output).

  `d` is the output of `load_legacy_windows(..., with_psd=True)` (X_psd optional).
  Returns `quality` (`quality_mask`), `keep` (bool rows of the input used:
  accepted and stimulus), `y` (their labels), `features` {block: block dict
  plus `class_means`, `counts`} and `psd_check` (max |computed - saved| over the
  kept rows when the saved X_psd has the same width, else None).
  """
  X, y = d["X_time"], d["y"]
  select_channels_by_name(channel_names, list(channel_names), X.shape[1])  # count check (PF-06)
  q = quality_mask(X, y, **thresholds)
  keep = (q["mask"] == 1) & np.isin(y, list(conditions))
  y_k = y[keep]
  out = {"quality": q, "keep": keep, "y": y_k, "features": {}, "psd_check": None}
  for name in blocks:
    b = FEATURE_BLOCKS[name](X[keep], fs, freq_range, y_k)
    b["class_means"], b["counts"] = class_means(b["per_window"], y_k, conditions)
    out["features"][name] = b
  saved = d.get("X_psd")
  if "psd" in out["features"] and saved is not None:
    comp = out["features"]["psd"]["X"]
    if saved.ndim == 2 and saved.shape[1] == comp.shape[1] and keep.any():
      out["psd_check"] = float(np.max(np.abs(saved[keep] - comp)))
  return out


# --- CLI ----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  who = p.add_mutually_exclusive_group()
  who.add_argument("--subject", default=None, help=f"one subject folder (default: {DEFAULT_SUBJECT})")
  who.add_argument("--subjects", nargs="+", default=None, help="several subject folders")
  who.add_argument("--all", action="store_true", help="every subject folder matching ^S\\d+$")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                 help="pipeline config (default: <root>/configs/pipeline_config.yaml)")
  p.add_argument("--processed-dir", type=Path, default=None,
                 help="legacy arrays (default: <root>/ + paths.data_processed_dir)")
  p.add_argument("--figures-dir", type=Path, default=None,
                 help="figure root (default: <root>/ + paths.figures_dir); figures go to "
                      "<figures-dir>/exploration/<S>/")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ,
                 help=f"sampling rate for the PSD (default: {LEGACY_FS_HZ:g}, legacy PF-04; "
                      "256 = header)")
  p.add_argument("--out-suffix", default="", help="appended to the figure name as _<suffix>")
  p.add_argument("--features", nargs="+", default=["psd", "fbcca", "fbcsp"], choices=sorted(FEATURE_BLOCKS),
                 help="feature blocks to compute and plot (P03: psd; P05: fbcca, fbcsp)")
  p.add_argument("--no-figures", action="store_true", help="print only")
  g = p.add_argument_group("quality mask thresholds (all passed explicitly, R5)")
  g.add_argument("--vpp-min", type=float, default=LEGACY_VPP_MIN_UV,
                 help=f"legacy lower Vpp limit in uV (default: {LEGACY_VPP_MIN_UV}, PF-07)")
  g.add_argument("--vpp-max", type=float, default=None, help="default: preprocessing.vpp_thresh_uv")
  g.add_argument("--std-min", type=float, default=None, help="default: preprocessing.std_range[0]")
  g.add_argument("--std-max", type=float, default=None, help="default: preprocessing.std_range[1]")
  return p


def resolve_thresholds(cfg: dict, args: argparse.Namespace) -> dict:
  """Mask thresholds: config v1 values (vpp_max, std_range), the legacy vpp_min, CLI overrides."""
  pre = cfg["preprocessing"]
  std_lo, std_hi = (float(v) for v in pre["std_range"])

  def pick(cli, value):
    return float(value if cli is None else cli)

  return {"vpp_min": float(args.vpp_min), "vpp_max": pick(args.vpp_max, pre["vpp_thresh_uv"]),
          "std_min": pick(args.std_min, std_lo), "std_max": pick(args.std_max, std_hi)}


def plot_blocks(res: dict, subject: str, label: str, channel_names: Sequence[str],
                figures_dir: Path, suffix: str) -> list:
  """One figure per computed block (P03: PSD by class, one panel per channel)."""
  from src.visualization.signal_plots import plot_psd_by_class_per_channel  # matplotlib on demand
  out = []
  if "psd" in res["features"]:
    b = res["features"]["psd"]
    title = (f"{subject} periodogram PSD by class (accepted stimulus windows), {label}\n"
             f"data: {DATA_SOURCE.replace('<S>', subject)}")
    out.append(plot_psd_by_class_per_channel(
      b["freqs"], b["class_means"], channel_names,
      figure_path(figures_dir, subject, FIGURE_STEM, suffix), counts=b["counts"], title=title))
  for name in ("fbcca", "fbcsp"):
    if name in res["features"]:
      out.append(_plot_class_feature_heatmap(res["features"][name], name, subject, label,
                                             figure_path(figures_dir, subject, f"{name}_features_by_class", suffix)))
  return out


def _plot_class_feature_heatmap(b: dict, name: str, subject: str, label: str, path: Path) -> Path:
  """Heatmap of the class-mean feature (rows = classes in code order, columns = features)."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  codes = sorted(b["class_means"])
  M = np.stack([b["class_means"][c] for c in codes])
  fig, ax = plt.subplots(figsize=(7.5 if name == "fbcsp" else 5.5, 3.6))
  im = ax.imshow(M, aspect="auto", cmap="viridis")
  ax.set_yticks(range(len(codes)), [f"{c} (n={b['counts'][c]})" for c in codes])
  if name == "fbcca":
    ax.set_xticks(range(M.shape[1]), [f"{f:g}" for f in b["freqs"]])
    ax.set_xlabel("target frequency (Hz)")
    cap = "FBCCA score (legacy: per-window Chebyshev sub-bands, R3/PF-14)"
  else:
    ax.set_xlabel("feature index: band x class x component (5 x 5 x 2)")
    cap = "FBCSP feature (CSP fitted on ALL shown windows: full-data fit, visualization only, R2 exception/PF-11)"
  fig.colorbar(im, ax=ax, label=f"class mean of {name} feature")
  ax.set_title(f"{subject} {cap}, {label}\ndata: {DATA_SOURCE.replace('<S>', subject)}", fontsize=7)
  fig.tight_layout()
  Path(path).parent.mkdir(parents=True, exist_ok=True)
  fig.savefig(path, dpi=150)
  plt.close(fig)
  return Path(path)


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  try:
    cfg = load_config(args.config)
  except (OSError, ValueError) as exc:
    print(f"[x] Config: {exc}")
    return 1
  processed_dir = args.processed_dir or ROOT / cfg["paths"]["data_processed_dir"]
  figures_dir = args.figures_dir or ROOT / cfg["paths"]["figures_dir"]
  if not Path(processed_dir).is_dir():
    print(f"[x] Processed folder not found: {processed_dir}")
    return 1
  subjects = resolve_subjects(args, processed_dir)
  if not subjects:
    print(f"[x] No subject folders matching ^S\\d+$ in {processed_dir}")
    return 1
  scalp = legacy_scalp(cfg["channels"]["scalp"])  # legacy 7-channel arrays (config v2 has PO7)
  conds = stimulus_conditions(cfg)
  freq_range = tuple(float(v) for v in cfg["features"]["psd_range_hz"])
  sub_sec = float(cfg["preprocessing"]["sub_window_sec"])
  th = resolve_thresholds(cfg, args)

  print(f"Data source: {DATA_SOURCE} -> {_rel(processed_dir)}/<S>/")
  print(f"Quality mask (legacy per-script gate, R5): vpp [{th['vpp_min']:g}, {th['vpp_max']:g}] uV, "
        f"std [{th['std_min']:g}, {th['std_max']:g}] uV; channels {scalp}")
  print(f"Features: {args.features}, {freq_range[0]:g}-{freq_range[1]:g} Hz; classes {list(conds)}")

  done, skipped, kept_total, rej_total = [], [], 0, 0
  for subject in subjects:
    try:
      d = load_legacy_windows(processed_dir, subject, with_psd=True)
      res = explore_subject(d, args.fs, scalp, conds, freq_range, th, blocks=args.features)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      skipped.append(subject)
      continue
    if not len(res["y"]):
      print(f"[-] Skipping {subject}: no accepted stimulus windows\n"
            f"{format_quality(subject, res['quality'])}")
      skipped.append(subject)
      continue
    hfs = header_fs(d["X_time"].shape[-1], sub_sec)
    label = fs_label(args.fs, hfs)
    print(f"\n[+] {subject}: {len(d['y'])} windows, X_time {d['X_time'].shape}; {label}, "
          f"header fs {hfs:g} Hz")
    print(format_quality(subject, res["quality"]))
    for name, b in res["features"].items():
      counts = ", ".join(f"{c}: {n}" for c, n in b["counts"].items())
      what = (f"{len(b['freqs'])} bins {b['freqs'][0]:.3f}-{b['freqs'][-1]:.3f} Hz" if name == "psd"
              else f"{b['X'].shape[1]} features" + (" (full-data CSP, visualization only)" if name == "fbcsp" else ""))
      print(f"  {name}: X {b['X'].shape} ({what}); stimulus windows per class: {counts}")
    if res["psd_check"] is None:
      print(f"  saved X_psd_features {d['X_psd'].shape}: not comparable at {label}")
    else:
      print(f"  saved X_psd_features {d['X_psd'].shape}: max |computed - saved| = "
            f"{res['psd_check']:.3g}")
    if not args.no_figures:
      for fig in plot_blocks(res, subject, label, scalp, figures_dir, args.out_suffix):
        print(f"  Figure: {_rel(fig)}")
    done.append(subject)
    kept_total += res["quality"]["n_kept"]
    rej_total += res["quality"]["n_rejected"]

  print(f"\nCohort: {len(done)} subjects plotted, {len(skipped)} skipped "
        f"({', '.join(skipped) or 'none'}); mask kept {kept_total}, rejected {rej_total}; "
        f"PSD fs {args.fs:g} Hz{' (legacy)' if args.fs == LEGACY_FS_HZ else ''}")
  print(f"Figures: {_rel(Path(figures_dir) / 'exploration')}")
  return 0 if done else 1


if __name__ == "__main__":
  sys.exit(main())
