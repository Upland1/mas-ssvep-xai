"""Legacy preprocessing and windowing (P02, mas/01_DATA_SPEC.md section 5.1).

For each subject: read <raw-dir>/<S>/<session>.ebr (default OO.ebr) with
src/io/ebr_parser.load_ebr_file, take the config scalp channels (by name) and
MARK, take fs from the header, band-pass the continuous scalp signal once
(config 1-60 Hz, Butterworth order 4, filtfilt), then cut and gate the condition
windows with the legacy limits (vpp <= 200 uV, std 0.5-60 uV, vpp_min 0.5 uV):
202 = the 1.0 s before each onset, 101-105 = the 5.0 s after each onset
(5 sub-windows), 201 = the 2.0 s after each onset (2 sub-windows).

Saves <processed-dir>/<S>/{X_psd_features,X_time_windows,y_labels}.npy
(conditions in the order 201, 202, 101..105, time order within; PSD 5-35 Hz,
channel-major) and <figures-dir>/spectra/<S>/{average_psd_by_condition,
stimulus_vs_baseline_psd}.png. The S03 arrays are also written to the
<processed-dir> root and the S03 PSD figure to
<figures-dir>/spectra/average_psd_by_condition.png, from the same in-memory
arrays (PF-09). Data source: legacy folders.

Paths and thresholds come from configs/pipeline_config.yaml; every CLI flag
overrides its config key. A subject that cannot be processed is skipped with
`[-] Skipping <S>: <reason>`.
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

from src.features.ssvep.psd_extraction import (  # noqa: E402  (needs ROOT on sys.path)
  prepare_feature_matrix, process_condition_windows_with_baseline)
from src.io import ebr_parser  # noqa: E402
from src.preprocessing.signal.filters import apply_iir_bandpass  # noqa: E402
from src.preprocessing.signal.quality_check import (  # noqa: E402
  format_quality_stats, merge_quality_stats, new_quality_stats, summarize_window_quality)

SUBJECT_PATTERN = re.compile(r"^S\d+$")
DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
DEFAULT_SUBJECT = "S03"
DEFAULT_SESSION = "OO"
# The subject whose arrays/figure also go to the root locations (original single-subject default).
ROOT_SUBJECT = "S03"
# legacy: lower Vpp limit of the P02 raw gate (roadmap P02.3). Config v1 has no key for it;
# passed explicitly so the shared default vpp_min=5.0 never reaches the legacy gate (PF-07).
LEGACY_VPP_MIN_UV = 0.5
ARRAY_FILES = ("X_psd_features", "X_time_windows", "y_labels")
PSD_FIGURE = "average_psd_by_condition.png"
STIM_FIGURE = "stimulus_vs_baseline_psd.png"


# --- Configuration -------------------------------------------------------------

def load_config(path: Path) -> dict:
  """Parsed YAML config; ValueError naming the key if a required v1 key is missing."""
  with open(path) as f:
    cfg = yaml.safe_load(f) or {}
  required = {
    "project": ("target_conditions",),
    "paths": ("data_raw_dir", "data_processed_dir", "figures_dir"),
    "channels": ("scalp", "mark_channel"),
    "preprocessing": ("lowcut_hz", "highcut_hz", "filter_order", "sub_window_sec",
                      "vpp_thresh_uv", "std_range", "baseline"),
    "features": ("psd_range_hz", "plotting_range_hz"),
  }
  for section, keys in required.items():
    for k in keys:
      if k not in (cfg.get(section) or {}):
        raise ValueError(f"{path}: missing config key {section}.{k}")
  for k in ("cross_condition", "cue_condition", "stimulus_duration_sec",
            "pre_stim_cross_sec", "cue_lookback_sec"):
    if k not in (cfg["preprocessing"]["baseline"] or {}):
      raise ValueError(f"{path}: missing config key preprocessing.baseline.{k}")
  return cfg


def resolve_params(cfg: dict, args: argparse.Namespace) -> dict:
  """Windowing/gate/filter parameters: config values, each overridden by its CLI flag if given."""
  pre, base = cfg["preprocessing"], cfg["preprocessing"]["baseline"]

  def pick(cli, value):
    return value if cli is None else cli

  conds = [int(c) for c in cfg["project"]["target_conditions"]]
  cross, cue = int(base["cross_condition"]), int(base["cue_condition"])
  std_lo, std_hi = (float(v) for v in pre["std_range"])
  psd_lo, psd_hi = (float(v) for v in cfg["features"]["psd_range_hz"])
  plot_lo, plot_hi = (float(v) for v in cfg["features"]["plotting_range_hz"])
  return {
    "scalp": list(cfg["channels"]["scalp"]),
    "mark_channel": str(cfg["channels"]["mark_channel"]),
    "feature_conditions": tuple(conds),
    "stim_conditions": tuple(c for c in conds if c not in (cross, cue)),
    "cross_condition": cross,
    "cue_condition": cue,
    "lowcut": float(pick(args.lowcut, pre["lowcut_hz"])),
    "highcut": float(pick(args.highcut, pre["highcut_hz"])),
    "order": int(pick(args.order, pre["filter_order"])),
    "sub_window_sec": float(pick(args.sub_window_sec, pre["sub_window_sec"])),
    "vpp_thresh": float(pick(args.vpp_max, pre["vpp_thresh_uv"])),
    "vpp_min": float(args.vpp_min),
    "std_range": (float(pick(args.std_min, std_lo)), float(pick(args.std_max, std_hi))),
    "stim_duration_sec": float(pick(args.stim_duration_sec, base["stimulus_duration_sec"])),
    "cross_duration_sec": float(pick(args.cross_duration_sec, base["pre_stim_cross_sec"])),
    "cue_lookback_sec": float(pick(args.cue_lookback_sec, base["cue_lookback_sec"])),
    "psd_range": (psd_lo, psd_hi),
    "plot_range": (plot_lo, plot_hi),
  }


# --- Per-subject processing (importable; no file output) ----------------------

def discover_subjects(raw_dir: Path) -> list:
  """Subject folders of raw_dir matching ^S\\d+$, in numeric order."""
  found = [p.name for p in Path(raw_dir).iterdir() if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name)]
  return sorted(found, key=lambda s: int(s[1:]))


def load_recording(path: Path, scalp: Sequence[str], mark_channel: str) -> tuple:
  """`(x, mark, fs)` of one EBR file: scalp signal `(C, T)` by name, MARK `(T,)`, header fs.

  Raises ValueError (missing MARK, unreadable file, missing scalp channel).
  """
  rec = ebr_parser.load_ebr_file(path)
  fs = float(rec["sampling_rate"])
  x, _ = ebr_parser.extract_scalp_signal(rec, scalp)
  mi = ebr_parser.get_mark_channel_index(rec["channels"], mark_channel)
  if mi < 0:
    raise ValueError(f"no {mark_channel} channel in {path.name}")
  mark = np.asarray(rec["data"][0, mi, 0, :], dtype=np.float64)
  return x, mark, fs


def window_starts(records: dict, conditions: Sequence[int]) -> np.ndarray:
  """Absolute start sample of every record in the row order of `prepare_feature_matrix`.

  Row i of X_time_windows equals `x_filtered[:, s[i]:s[i] + n_samples]` (R3 check).
  """
  return np.asarray([int(r["start"]) for c in conditions for r in records.get(c, [])],
                    dtype=np.int64)


def preprocess_recording(x: np.ndarray, mark: np.ndarray, fs: float, params: dict) -> dict:
  """Filter the continuous signal once, cut and gate the condition windows, build the arrays.

  Returns a dict: `x_filtered (C, T)`, `records` ({code: [record]}), `X_psd (n, C*F)`,
  `X_time (n, C, n_sub)`, `y (n,)`, `starts (n,)` (absolute start samples, same row
  order), `quality_stats`. Raises RuntimeError if a shape or label violates
  mas/01_DATA_SPEC.md section 5.1.
  """
  x_f = apply_iir_bandpass(x, fs, params["lowcut"], params["highcut"], params["order"])  # R3
  qs = new_quality_stats()
  records = process_condition_windows_with_baseline(
    x_f, mark, fs, target_conditions=params["stim_conditions"],
    cue_condition=params["cue_condition"], cross_condition=params["cross_condition"],
    sub_window_sec=params["sub_window_sec"], vpp_thresh=params["vpp_thresh"],
    std_range=params["std_range"], stim_duration_sec=params["stim_duration_sec"],
    cue_lookback_sec=params["cue_lookback_sec"], quality_stats=qs,
    vpp_min=params["vpp_min"], cross_duration_sec=params["cross_duration_sec"])  # PF-07
  X_psd, X_time, y = prepare_feature_matrix(records, target_conditions=params["feature_conditions"],
                                            freq_range=params["psd_range"])
  starts = window_starts(records, params["feature_conditions"])
  check_arrays(X_psd, X_time, y, starts, n_channels=x.shape[0],
               n_samples=int(params["sub_window_sec"] * fs),
               conditions=params["feature_conditions"])
  return {"x_filtered": x_f, "records": records, "X_psd": X_psd, "X_time": X_time, "y": y,
          "starts": starts, "quality_stats": qs}


def check_arrays(X_psd: np.ndarray, X_time: np.ndarray, y: np.ndarray, starts: np.ndarray,
                 n_channels: int, n_samples: int, conditions: Sequence[int]) -> None:
  """Fail loudly (RuntimeError) unless the arrays have the section-5.1 layout.

  Equal lengths (PF-09); `X_time (n, n_channels, n_samples)`; `X_psd (n, n_channels * F)`;
  labels only from `conditions`, grouped in that order; starts increasing within a condition.
  """
  n = len(y)
  if not (len(X_psd) == len(X_time) == n == len(starts)):
    raise RuntimeError(f"length mismatch: X_psd {len(X_psd)}, X_time {len(X_time)}, "
                       f"y {n}, starts {len(starts)}")
  if n == 0:
    return
  if X_time.shape[1:] != (n_channels, n_samples):
    raise RuntimeError(f"X_time {X_time.shape}, expected (n, {n_channels}, {n_samples})")
  if X_psd.ndim != 2 or X_psd.shape[1] % n_channels:
    raise RuntimeError(f"X_psd {X_psd.shape} is not (n, {n_channels} * n_bins)")
  bad = sorted(set(y.tolist()) - set(int(c) for c in conditions))
  if bad:
    raise RuntimeError(f"unexpected labels {bad}")
  rank = {int(c): k for k, c in enumerate(conditions)}
  r = np.asarray([rank[int(v)] for v in y])
  if np.any(np.diff(r) < 0):
    raise RuntimeError("labels are not grouped in the condition order")
  same = np.diff(r) == 0
  if np.any(np.diff(starts)[same] <= 0):
    raise RuntimeError("windows of a condition are not in time order")


# --- Output -------------------------------------------------------------------

def save_arrays(out_dir: Path, X_psd: np.ndarray, X_time: np.ndarray, y: np.ndarray) -> list:
  """Write the three legacy arrays to out_dir after checking equal lengths (PF-09)."""
  if not (len(X_psd) == len(X_time) == len(y)):
    raise RuntimeError(f"refusing to save {out_dir}: X_psd {len(X_psd)}, X_time {len(X_time)}, "
                       f"y {len(y)} rows")
  out_dir = Path(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)
  paths = []
  for name, arr in zip(ARRAY_FILES, (X_psd, X_time, y)):
    p = out_dir / f"{name}.npy"
    np.save(p, arr)
    paths.append(p)
  return paths


def condition_counts(y: np.ndarray, conditions: Sequence[int]) -> dict:
  """Windows per condition code, in the order of `conditions` (zeros included)."""
  return {int(c): int(np.sum(y == c)) for c in conditions}


def save_figures(records: dict, fig_dir: Path, subject: str, params: dict) -> list:
  """Per-subject PSD-by-condition and stimulus-vs-baseline figures; the root PSD figure for S03."""
  from src.visualization.signal_plots import (  # imported here: matplotlib only when plotting
    plot_average_psd_by_condition, plot_stimulus_vs_baseline_psd)
  spectra = Path(fig_dir) / "spectra"
  title = f"{subject} average PSD by condition (legacy, {params['session']}.ebr)"
  out = [plot_average_psd_by_condition(records, spectra / subject / PSD_FIGURE,
                                       freq_range=params["plot_range"], title=title),
         plot_stimulus_vs_baseline_psd(records, spectra / subject / STIM_FIGURE,
                                       baseline_condition=params["cross_condition"],
                                       target_conditions=params["stim_conditions"],
                                       freq_range=params["plot_range"],
                                       title=f"{subject} stimulus vs {params['cross_condition']} PSD")]
  if subject == ROOT_SUBJECT:
    out.append(plot_average_psd_by_condition(records, spectra / PSD_FIGURE,
                                             freq_range=params["plot_range"], title=title))
  return out


# --- CLI ----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  who = p.add_mutually_exclusive_group()
  who.add_argument("--subject", default=None,
                   help=f"one subject folder (default: {DEFAULT_SUBJECT})")
  who.add_argument("--subjects", nargs="+", default=None, help="several subject folders")
  who.add_argument("--all", action="store_true", help="every subject folder matching ^S\\d+$")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                 help="pipeline config (default: <root>/configs/pipeline_config.yaml)")
  p.add_argument("--raw-dir", type=Path, default=None, help="default: <root>/ + paths.data_raw_dir")
  p.add_argument("--processed-dir", type=Path, default=None,
                 help="default: <root>/ + paths.data_processed_dir")
  p.add_argument("--figures-dir", type=Path, default=None, help="default: <root>/ + paths.figures_dir")
  p.add_argument("--session", default=DEFAULT_SESSION, help="recording file stem (default: OO)")
  p.add_argument("--no-figures", action="store_true", help="skip the figures")
  g = p.add_argument_group("overrides of configs/pipeline_config.yaml")
  g.add_argument("--lowcut", type=float, default=None, help="preprocessing.lowcut_hz")
  g.add_argument("--highcut", type=float, default=None, help="preprocessing.highcut_hz")
  g.add_argument("--order", type=int, default=None, help="preprocessing.filter_order")
  g.add_argument("--sub-window-sec", type=float, default=None, help="preprocessing.sub_window_sec")
  g.add_argument("--vpp-max", type=float, default=None, help="preprocessing.vpp_thresh_uv")
  g.add_argument("--std-min", type=float, default=None, help="preprocessing.std_range[0]")
  g.add_argument("--std-max", type=float, default=None, help="preprocessing.std_range[1]")
  g.add_argument("--stim-duration-sec", type=float, default=None,
                 help="preprocessing.baseline.stimulus_duration_sec")
  g.add_argument("--cross-duration-sec", type=float, default=None,
                 help="preprocessing.baseline.pre_stim_cross_sec")
  g.add_argument("--cue-lookback-sec", type=float, default=None,
                 help="preprocessing.baseline.cue_lookback_sec")
  p.add_argument("--vpp-min", type=float, default=LEGACY_VPP_MIN_UV,
                 help=f"legacy lower Vpp limit in uV, not in config v1 (default: {LEGACY_VPP_MIN_UV}, "
                      "PF-07)")
  return p


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
  params = resolve_params(cfg, args)
  params["session"] = args.session
  paths = cfg["paths"]
  raw_dir = args.raw_dir or ROOT / paths["data_raw_dir"]
  processed_dir = args.processed_dir or ROOT / paths["data_processed_dir"]
  figures_dir = args.figures_dir or ROOT / paths["figures_dir"]

  if not Path(raw_dir).is_dir():
    print(f"[x] Raw folder not found: {raw_dir}")
    return 1
  if args.all:
    subjects = discover_subjects(raw_dir)
  elif args.subjects:
    subjects = list(args.subjects)
  else:
    subjects = [args.subject or DEFAULT_SUBJECT]
  if not subjects:
    print(f"[x] No subject folders matching ^S\\d+$ in {raw_dir}")
    return 1

  print(f"Data source: legacy windows from {args.session}.ebr -> {_rel(processed_dir)}/<S>/")
  print(f"Filter: Butterworth band-pass {params['lowcut']:g}-{params['highcut']:g} Hz, order "
        f"{params['order']}, filtfilt on the continuous signal; channels {params['scalp']}")
  print(f"Gate: vpp [{params['vpp_min']:g}, {params['vpp_thresh']:g}] uV, std "
        f"[{params['std_range'][0]:g}, {params['std_range'][1]:g}] uV; sub-window "
        f"{params['sub_window_sec']:g} s; 202 lookback {params['cue_lookback_sec']:g} s, "
        f"201 {params['cross_duration_sec']:g} s, stimulus {params['stim_duration_sec']:g} s")

  cohort_qs = new_quality_stats()
  done, skipped, total = [], [], 0
  for subject in subjects:
    try:
      path = ebr_parser.resolve_recording_path(raw_dir, subject, args.session)
      x, mark, fs = load_recording(path, params["scalp"], params["mark_channel"])
      out = preprocess_recording(x, mark, fs, params)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      skipped.append(subject)
      continue
    X_psd, X_time, y, qs = out["X_psd"], out["X_time"], out["y"], out["quality_stats"]
    if len(y) == 0:
      print(f"[-] Skipping {subject}: no window accepted\n{format_quality_stats(qs, params['scalp'])}")
      skipped.append(subject)
      continue

    print(f"\n[+] {subject}/{path.name}: fs {fs:g} Hz (header), {x.shape[0]} channels, "
          f"{x.shape[1]} samples ({x.shape[1] / fs:.1f} s)")
    print(format_quality_stats(qs, params["scalp"]))
    summarize_window_quality(X_time, vpp_min=params["vpp_min"], vpp_max=params["vpp_thresh"],
                             std_min=params["std_range"][0], std_max=params["std_range"][1],
                             label=f"{subject} accepted windows")
    counts = condition_counts(y, params["feature_conditions"])
    n_stim = sum(counts[c] for c in params["stim_conditions"])
    print("  windows per condition: " + ", ".join(f"{c}: {n}" for c, n in counts.items()))
    print(f"  {subject}: n = {len(y)} windows (stimulus {n_stim}); accepted {qs['n_accepted']}, "
          f"rejected {qs['n_rejected']}, skipped segments {len(qs['skipped_segments'])}; "
          f"X_time {X_time.shape}, X_psd {X_psd.shape}")

    saved = save_arrays(Path(processed_dir) / subject, X_psd, X_time, y)
    print(f"  Saved: {', '.join(_rel(p) for p in saved)}")
    if subject == ROOT_SUBJECT:  # PF-09: same in-memory arrays as the per-subject folder
      saved = save_arrays(Path(processed_dir), X_psd, X_time, y)
      print(f"  Saved ({ROOT_SUBJECT} root copy): {', '.join(_rel(p) for p in saved)}")
    if not args.no_figures:
      figs = save_figures(out["records"], figures_dir, subject, params)
      print(f"  Figures: {', '.join(_rel(p) for p in figs)}")
    merge_quality_stats(cohort_qs, qs)
    done.append(subject)
    total += len(y)

  if ROOT_SUBJECT in subjects and ROOT_SUBJECT not in done:
    print(f"[!] {ROOT_SUBJECT} was not processed: the root arrays in {_rel(processed_dir)} were not written")
  print(f"\nCohort: {len(done)} subjects processed, {len(skipped)} skipped "
        f"({', '.join(skipped) or 'none'}); {total} windows; gated {cohort_qs['n_total']}, "
        f"accepted {cohort_qs['n_accepted']}, rejected {cohort_qs['n_rejected']}, "
        f"skipped segments {len(cohort_qs['skipped_segments'])}")
  print(f"Saved: {_rel(processed_dir)}")
  return 0 if done else 1


if __name__ == "__main__":
  sys.exit(main())
