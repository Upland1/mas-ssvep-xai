"""Occipital FFT power per class (P03.1): does each stimulus class peak at its target frequency?

For each subject: read the legacy windows <processed-dir>/<S>/{X_time_windows,
y_labels}.npy (P02, never the root arrays: PF-09), keep the stimulus windows
(101-105), select the occipital channels O1, Oz, O2 by name (config
`channels.scalp`, PF-06), compute `|rfft|^2` of each window, average over the
windows and the three channels and plot 5-35 Hz (config `features.psd_range_hz`),
one panel per class, with the target frequency (solid) and its 2nd harmonic
(dotted) marked. Prints per class the frequency of the maximum in the range and
the power at the bin nearest the target (and 2f0).

fs: the legacy arrays store no sampling rate. Default `--fs 250` reproduces the
Era-A assumption (legacy, PF-04: every peak sits at f * 250/256, e.g. 24 -> 23.44
Hz); `--fs 256` uses the header rate (= samples per window / sub-window
seconds). The mode is printed and written into each figure title. Use
`--out-suffix` to keep the figures of a comparison run apart.

Figures: <figures-dir>/exploration/<S>/occipital_spectra[_<suffix>].png.
A subject without arrays is skipped with `[-] Skipping <S>: <reason>`.
Data source: legacy, data/processed/<S>/ from P02.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import yaml


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

from src.features.ssvep.spectral_power import (  # noqa: E402  (needs ROOT on sys.path)
  LEGACY_FS_HZ, fft_power, fs_label, mean_spectrum, select_channels_by_name, spectrum_peaks)
from src.visualization.signal_plots import STIM_FREQS_HZ  # noqa: E402

SUBJECT_PATTERN = re.compile(r"^S\d+$")
DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
DEFAULT_SUBJECT = "S03"
OCCIPITAL = ("O1", "Oz", "O2")  # 01_DATA_SPEC section 6: occipital set for power checks
FIGURE_STEM = "occipital_spectra"
DATA_SOURCE = "legacy, data/processed/<S>/ from P02 (OO.ebr)"


# --- Configuration and data ---------------------------------------------------

def load_config(path: Path) -> dict:
  """Parsed YAML config; ValueError naming the key if a key used by P03 is missing."""
  with open(path) as f:
    cfg = yaml.safe_load(f) or {}
  required = {
    "project": ("target_conditions",),
    "paths": ("data_processed_dir", "figures_dir"),
    "channels": ("scalp",),
    "preprocessing": ("sub_window_sec", "vpp_thresh_uv", "std_range", "baseline"),
    "features": ("psd_range_hz",),
  }
  for section, keys in required.items():
    for k in keys:
      if k not in (cfg.get(section) or {}):
        raise ValueError(f"{path}: missing config key {section}.{k}")
  for k in ("cross_condition", "cue_condition"):
    if k not in (cfg["preprocessing"]["baseline"] or {}):
      raise ValueError(f"{path}: missing config key preprocessing.baseline.{k}")
  return cfg


def stimulus_conditions(cfg: dict) -> tuple:
  """Config target conditions without the fixation and cue codes (101-105 in config v1)."""
  base = cfg["preprocessing"]["baseline"]
  skip = {int(base["cross_condition"]), int(base["cue_condition"])}
  return tuple(int(c) for c in cfg["project"]["target_conditions"] if int(c) not in skip)


def discover_subjects(processed_dir: Path) -> list:
  """Subject folders of processed_dir matching ^S\\d+$, in numeric order."""
  found = [p.name for p in Path(processed_dir).iterdir()
           if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name)]
  return sorted(found, key=lambda s: int(s[1:]))


def resolve_subjects(args: argparse.Namespace, processed_dir: Path) -> list:
  """Subjects from --all / --subjects / --subject (default DEFAULT_SUBJECT)."""
  if args.all:
    return discover_subjects(processed_dir)
  if args.subjects:
    return list(args.subjects)
  return [args.subject or DEFAULT_SUBJECT]


def load_legacy_windows(processed_dir: Path, subject: str, with_psd: bool = False) -> dict:
  """`{X_time (n, C, T), y (n,)[, X_psd (n, D)]}` from <processed_dir>/<subject>/ (PF-09).

  Only the per-subject folder is read, never the root arrays. Raises
  FileNotFoundError for a missing file and ValueError when the arrays differ
  in length or X_time is not 3-D.
  """
  folder = Path(processed_dir) / subject
  names = ["X_time_windows", "y_labels"] + (["X_psd_features"] if with_psd else [])
  arrays = {}
  for name in names:
    p = folder / f"{name}.npy"
    if not p.is_file():
      raise FileNotFoundError(f"no {name}.npy in {folder}")
    arrays[name] = np.load(p)
  out = {"X_time": np.asarray(arrays["X_time_windows"], dtype=np.float64),
         "y": np.asarray(arrays["y_labels"]).astype(np.int64).reshape(-1)}
  if with_psd:
    out["X_psd"] = np.asarray(arrays["X_psd_features"], dtype=np.float64)
  if out["X_time"].ndim != 3:
    raise ValueError(f"X_time_windows has shape {out['X_time'].shape}, expected (n, C, T)")
  lengths = {k: len(v) for k, v in out.items()}
  if len(set(lengths.values())) != 1:
    raise ValueError(f"length mismatch in {folder}: {lengths}")
  return out


def header_fs(n_samples: int, sub_window_sec: float) -> float:
  """True sampling rate of legacy windows: `int(sub_window_sec * fs)` samples per window (5.1)."""
  return float(n_samples) / float(sub_window_sec)


# --- Per-subject computation (importable; no file output) ---------------------

def occipital_class_spectra(X_time: np.ndarray, y: np.ndarray, fs: float,
                            channel_names: Sequence[str], conditions: Sequence[int],
                            freq_range: tuple = (5.0, 35.0),
                            occipital: Sequence[str] = OCCIPITAL) -> dict:
  """FFT power per class over the occipital channels (by name) and its peaks.

  Returns `freqs (F,)`, `channels` (indices of `occipital` in `channel_names`),
  `spectra` {code: (F,) mean |rfft|^2 over the class windows and the occipital
  channels}, `counts` {code: windows}, `peaks` {code: `spectrum_peaks` output
  with the code's stimulation frequency}. Classes with no window are left out
  of `spectra` and `peaks` (count 0). Rows of other labels (201, 202) are ignored.
  Raises ValueError when the names do not match the channel axis (PF-06).
  """
  X = np.asarray(X_time, dtype=np.float64)
  y = np.asarray(y).reshape(-1)
  if len(X) != len(y):
    raise ValueError(f"length mismatch: X_time {len(X)}, y {len(y)}")
  chans = select_channels_by_name(channel_names, occipital, X.shape[1])
  out = {"channels": chans, "spectra": {}, "counts": {}, "peaks": {}, "freqs": None}
  freqs = np.fft.rfftfreq(X.shape[-1], d=1.0 / float(fs))
  out["freqs"] = freqs
  for code in conditions:
    rows = X[y == code]
    out["counts"][int(code)] = int(len(rows))
    if not len(rows):
      continue
    _, power = fft_power(rows[:, chans, :], fs)
    s = mean_spectrum(power)
    out["spectra"][int(code)] = s
    out["peaks"][int(code)] = spectrum_peaks(freqs, s, freq_range,
                                             target_hz=STIM_FREQS_HZ.get(int(code)))
  return out


def format_peaks(subject: str, result: dict, conditions: Sequence[int]) -> str:
  """Console block: one line per class with the maximum and the target-bin powers."""
  lines = []
  for code in conditions:
    n = result["counts"].get(int(code), 0)
    if int(code) not in result["peaks"]:
      lines.append(f"  {subject} {code}: n=0, no windows")
      continue
    pk = result["peaks"][int(code)]
    f0 = STIM_FREQS_HZ.get(int(code))
    parts = [f"  {subject} {code}: n={n}, target {f0:.2f} Hz; max in band at {pk['f_max']:.3f} Hz "
             f"(bin {pk['k_max']}, P={pk['p_max']:.4g}); band median P={pk['band_median']:.4g}"]
    for h in pk["harmonics"]:
      parts.append(f"; {h['h']}f0 nearest bin {h['k']} ({h['f_bin']:.3f} Hz) P={h['power']:.4g}"
                   f" (x{h['power'] / pk['band_median']:.2f} median)")
    lines.append("".join(parts))
  return "\n".join(lines)


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
                 help=f"sampling rate for the frequency axis (default: {LEGACY_FS_HZ:g}, legacy "
                      "PF-04; 256 = header)")
  p.add_argument("--out-suffix", default="",
                 help="appended to the figure name as _<suffix> (e.g. header for a --fs 256 run)")
  p.add_argument("--no-figures", action="store_true", help="print only")
  return p


def figure_path(figures_dir: Path, subject: str, stem: str, suffix: str = "") -> Path:
  """<figures_dir>/exploration/<S>/<stem>[_<suffix>].png."""
  name = f"{stem}_{suffix}.png" if suffix else f"{stem}.png"
  return Path(figures_dir) / "exploration" / subject / name


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
  scalp = list(cfg["channels"]["scalp"])
  conds = stimulus_conditions(cfg)
  freq_range = tuple(float(v) for v in cfg["features"]["psd_range_hz"])
  sub_sec = float(cfg["preprocessing"]["sub_window_sec"])

  print(f"Data source: {DATA_SOURCE} -> {_rel(processed_dir)}/<S>/")
  print(f"Occipital channels {list(OCCIPITAL)} by name from {scalp}; |rfft|^2 per window, mean "
        f"over windows and channels; {freq_range[0]:g}-{freq_range[1]:g} Hz; classes {list(conds)}")

  done, skipped = [], []
  for subject in subjects:
    try:
      d = load_legacy_windows(processed_dir, subject)
      hfs = header_fs(d["X_time"].shape[-1], sub_sec)
      res = occipital_class_spectra(d["X_time"], d["y"], args.fs, scalp, conds, freq_range)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      skipped.append(subject)
      continue
    if not res["spectra"]:
      print(f"[-] Skipping {subject}: no stimulus windows")
      skipped.append(subject)
      continue
    label = fs_label(args.fs, hfs)
    df = float(res["freqs"][1] - res["freqs"][0])
    print(f"\n[+] {subject}: {len(d['y'])} windows, X_time {d['X_time'].shape}; {label}, "
          f"header fs {hfs:g} Hz; bin spacing {df:.6g} Hz; channels {res['channels']} = "
          f"{[scalp[c] for c in res['channels']]}")
    print(format_peaks(subject, res, conds))
    if not args.no_figures:
      from src.visualization.signal_plots import plot_class_spectra_panels  # matplotlib on demand
      title = (f"{subject} occipital (O1, Oz, O2) FFT power per class, {label}\n"
               f"data: {DATA_SOURCE.replace('<S>', subject)}")
      fig = plot_class_spectra_panels(res["freqs"], res["spectra"],
                                      figure_path(figures_dir, subject, FIGURE_STEM, args.out_suffix),
                                      freq_range=freq_range, counts=res["counts"], title=title)
      print(f"  Figure: {_rel(fig)}")
    done.append(subject)

  print(f"\nCohort: {len(done)} subjects plotted, {len(skipped)} skipped "
        f"({', '.join(skipped) or 'none'}); frequency axis fs {args.fs:g} Hz"
        f"{' (legacy)' if args.fs == LEGACY_FS_HZ else ''}")
  print(f"Figures: {_rel(Path(figures_dir) / 'exploration')}")
  return 0 if done else 1


if __name__ == "__main__":
  sys.exit(main())
