"""Build the P16 windows of every subject (P16.5, 01_DATA_SPEC 5.2, R3, R5, PF-04, PF-14).

Per subject: read `<raw-dir>/<S>/<session>.ebr` (default OO), take the 8 scalp channels by name and the
header fs (256 Hz), filter the continuous signal once (config: Butterworth 1-90 Hz order 4 + 60 Hz notch
Q 30, zero-phase), build the window index (`stride=None`: the legacy window starts; one true trial id per
segment), cut the filtered and the raw windows, compute the sub-band windows of the requested banks, take
the shared quality decision (`subject_quality_gate`, thresholds from the config `quality:` block) and save
every file of 01_DATA_SPEC 5.2 into `<out-root>[/w<len>_s<stride>]/<S>/` (default out-root
`data/processed_<filter-mode>`).

Banks: `fbcca`, `fbcsp` (P05) and, from P17, `harmonic` (k*f, k = 1..3, 15 centres) and `intermediate` (4 midpoints
of neighbouring targets), narrow Butterworth bands from the config `filter_bank:` block, filtered on the
continuous signal like the others. By default `--banks` is `fbcca fbcsp` plus every narrow bank whose config
block has `enabled: true`; naming a bank explicitly builds it whatever the flag. A narrow band above
`min(highcut, fs/2 - 1)` or containing the notch is not built; `windows_meta.json` records `bands_skipped` and
`band_overlaps` per bank. The artifact guard `auto` is the longest ringing time of every filter applied, the
narrow bands included, so a build with narrow banks can have a longer guard (hence different masks) than a
two-bank build; every other file of a build is independent of the set of banks.

`--filter-mode continuous` filters each sub-band over the whole recording and then cuts (R3);
`--filter-mode per_window` (legacy, PF-14) cuts first and filters each window alone: the broadband filter
is continuous in both, so the two builds differ only in the sub-bands.

`--check-legacy-starts` also recomputes, with the P02 code path, the pre-gate legacy window starts and the
post-gate legacy windows and prints per subject and condition `n_legacy, n_built, n_equal, max|d|`, how
many reconstructed legacy trial ids differ from the true ones (P11 D-2), and the filter start-up report of the
first trial (P02 carry-forward). The script never writes into the legacy folder `data/processed`; a subject
whose raw file is missing is skipped with `[-] Skipping <S>: <reason>`. `--resume` skips subjects whose folder
was built with the same parameters (the files are written to a temporary folder and renamed, so a crash
leaves no half subject).
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import yaml


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else one level up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[1]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.io import ebr_parser  # noqa: E402
from src.io.channels import LEGACY_EXCLUDED  # noqa: E402
from src.io.subject_data import built_dir_name  # noqa: E402
from src.preprocessing.dataset.cv_utils import LEGACY_TRIAL_LENGTHS, build_trial_ids  # noqa: E402
from src.preprocessing.signal.filters import broadband_filter  # noqa: E402
from src.preprocessing.window_quality import (SOURCES, AllChannelsDropped, quality_params_from_config,  # noqa: E402
                                              subject_quality_gate)
from src.preprocessing.windowing import (BANK_NAMES, BASE_BANKS, MODES, NARROW_BANKS, BandFilter,  # noqa: E402
                                         band_overlaps, band_windows, build_bank, build_window_index, compare_trial_ids,
                                         cut_windows, load_session, windows_per_segment)

SUBJECT_PATTERN = re.compile(r"^S\d+$")
DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
DEFAULT_SESSION = "OO"
STARTUP_PAD_SEC = 30.0
FIRST_TRIAL_SEC = 15.0
LEGACY_ARRAY = "X_psd_features.npy"   # a folder holding it is a legacy folder: never written to


# --- configuration -------------------------------------------------------------------

def load_build_config(path: Path) -> dict:
  """Parsed config; ValueError naming the first missing P16 key."""
  cfg = yaml.safe_load(Path(path).read_text()) or {}
  need = {"channels": ("scalp", "mark_channel"), "project": ("target_conditions",),
          "filter_bank": ("harmonics", "intermediate"),
          "preprocessing": ("lowcut_hz", "highcut_hz", "notch_hz", "notch_q", "filter_order", "sub_window_sec",
                            "baseline"), "quality": ("vpp_range_uv",)}
  for sec, keys in need.items():
    for k in keys:
      if k not in (cfg.get(sec) or {}):
        raise ValueError(f"{path}: missing config key {sec}.{k}")
  for blk, keys in (("harmonics", ("enabled", "n_harmonics", "half_width_hz", "order")),
                    ("intermediate", ("enabled", "half_width_hz", "order"))):
    for k in keys:
      if k not in (cfg["filter_bank"][blk] or {}):
        raise ValueError(f"{path}: missing config key filter_bank.{blk}.{k}")
  return cfg


def narrow_params(cfg: dict) -> dict:
  """`{bank: kwargs of build_bank}` for the narrow banks from the config: `filter_bank:` widths and orders,
  `max_hz` = broadband highcut, `exclude_hz` = the notch (none if the notch is off)."""
  fb, pre = cfg["filter_bank"], cfg["preprocessing"]
  common = {"max_hz": float(pre["highcut_hz"]),
            "exclude_hz": () if pre["notch_hz"] is None else (float(pre["notch_hz"]),)}
  return {"harmonic": {**common, "n_harmonics": int(fb["harmonics"]["n_harmonics"]),
                       "half_width_hz": float(fb["harmonics"]["half_width_hz"]), "order": int(fb["harmonics"]["order"])},
          "intermediate": {**common, "half_width_hz": float(fb["intermediate"]["half_width_hz"]),
                           "order": int(fb["intermediate"]["order"])}}


def default_banks(cfg: dict) -> list:
  """`fbcca fbcsp` plus the narrow banks enabled in the config `filter_bank:` block (harmonic first)."""
  fb = cfg["filter_bank"]
  return list(BASE_BANKS) + [b for b, k in (("harmonic", "harmonics"), ("intermediate", "intermediate"))
                             if fb[k]["enabled"]]


def resolve_params(cfg: dict, args: argparse.Namespace) -> dict:
  """Build parameters: config values, each overridden by its CLI flag. Thresholds are read, never defaulted."""
  pre, base = cfg["preprocessing"], cfg["preprocessing"]["baseline"]
  conds = [int(c) for c in cfg["project"]["target_conditions"]]
  cross, cue = int(base["cross_condition"]), int(base["cue_condition"])
  q = quality_params_from_config(cfg)
  if args.guard_sec is not None:
    q["guard_sec"] = "auto" if args.guard_sec == "auto" else float(args.guard_sec)
  if args.quality_source is not None:
    q["source"] = args.quality_source
  return {
    "scalp": list(cfg["channels"]["scalp"]), "mark_channel": str(cfg["channels"]["mark_channel"]),
    "feature_conditions": tuple(conds), "stim_conditions": tuple(c for c in conds if c not in (cross, cue)),
    "cross_condition": cross, "cue_condition": cue,
    "lowcut": float(pre["lowcut_hz"]), "highcut": float(pre["highcut_hz"]), "order": int(pre["filter_order"]),
    "notch_hz": None if pre["notch_hz"] is None else float(pre["notch_hz"]), "notch_q": float(pre["notch_q"]),
    "window_sec": float(args.window_sec if args.window_sec is not None else pre["sub_window_sec"]),
    "stride_sec": None if args.stride_sec is None else float(args.stride_sec),
    "stim_duration_sec": float(base["stimulus_duration_sec"]), "cross_duration_sec": float(base["pre_stim_cross_sec"]),
    "cue_lookback_sec": float(base["cue_lookback_sec"]), "quality": q,
    "filter_mode": args.filter_mode, "banks": list(args.banks or default_banks(cfg)), "session": args.session,
    "narrow": narrow_params(cfg)}


# --- one subject (importable, no file output) ----------------------------------------

def build_subject(x: np.ndarray, mark: np.ndarray, fs: float, params: dict) -> dict:
  """Windows, sub-bands and the shared quality decision of one recording (`x (C, T)` raw scalp channels).

  Returns `broadband (C, T)`, `idx` (WindowIndex), `X_time`, `X_raw` `(n, C, n_samples)`, `bands`
  `{bank: (n, B, C, n_samples)}`, `banks_meta`, `bands_skipped` / `band_overlaps` `{bank: list}` (P17), `quality` (`subject_quality_gate` result), `n_samples`.
  """
  names = list(params["scalp"])
  if len(names) != x.shape[0]:
    raise ValueError(f"{len(names)} channel names for {x.shape[0]} channels")
  broadband = broadband_filter(x, fs, params["lowcut"], params["highcut"], params["order"],
                               params["notch_hz"], params["notch_q"])           # R3: continuous, once
  idx = build_window_index(mark, fs, params["stim_conditions"], params["cross_condition"],
                           params["cue_condition"], params["window_sec"], params["stim_duration_sec"],
                           params["cross_duration_sec"], params["cue_lookback_sec"], params["stride_sec"])
  if len(idx) == 0:
    raise ValueError("no complete segment in the MARK channel")
  n = int(params["window_sec"] * fs)
  X_time, X_raw = cut_windows(broadband, idx.starts, n), cut_windows(x, idx.starts, n)
  bands, banks_meta, bands_skipped, overlaps, filters = {}, {}, {}, {}, [lambda z: broadband_filter(
    z, fs, params["lowcut"], params["highcut"], params["order"], params["notch_hz"], params["notch_q"])]
  for b in params["banks"]:
    bank, skipped = build_bank(b, fs, params["narrow"].get(b))
    if not bank:
      raise ValueError(f"bank {b!r} has no band left at fs {fs:g} Hz")
    bands[b] = band_windows(broadband, idx.starts, n, bank, params["filter_mode"])
    banks_meta[b] = [{"name": f.name, "low": f.low, "high": f.high} for f in bank]
    bands_skipped[b] = skipped
    overlaps[b] = band_overlaps(bank)
    filters += bank
  quality = subject_quality_gate(X_time, idx.starts, broadband, fs, names, filters, params["quality"],
                                 labels=idx.labels, raw_windows=X_raw, raw=x)
  return {"broadband": broadband, "idx": idx, "X_time": X_time, "X_raw": X_raw, "bands": bands,
          "banks_meta": banks_meta, "bands_skipped": bands_skipped, "band_overlaps": overlaps, "quality": quality, "n_samples": n}


def _jsonable(o):
  if isinstance(o, dict):
    return {str(k): _jsonable(v) for k, v in o.items()}
  if isinstance(o, (list, tuple)):
    return [_jsonable(v) for v in o]
  if isinstance(o, np.ndarray):
    return o.tolist()
  if isinstance(o, np.generic):
    return o.item()
  return o


def _cross_overlaps(built: dict) -> dict:
  """`band_overlaps` of the meta: `{bank: pairs inside the bank}` plus `combined`, the pairs between bands of
  different banks among the banks the benchmark joins (`fbcsp`, `harmonic`, `intermediate`, those built)."""
  out = dict(built["band_overlaps"])
  joined = [(b, BandFilter(f["name"], f["low"], f["high"], None, None)) for b in ("fbcsp",) + NARROW_BANKS
            for f in built["banks_meta"].get(b, [])]
  owner = {f.name: b for b, f in joined}
  out["combined"] = [o for o in band_overlaps([f for _, f in joined]) if owner[o["a"]] != owner[o["b"]]]
  return out


def build_meta(built: dict, params: dict, fs: float, subject: str, recording: str, git_commit: str) -> dict:
  """The `windows_meta.json` content (01_DATA_SPEC 5.2)."""
  idx, q = built["idx"], built["quality"]
  n = built["n_samples"]
  seg_len = {params["cross_condition"]: int(params["cross_duration_sec"] * fs),
             params["cue_condition"]: int(params["cue_lookback_sec"] * fs),
             **{c: int(params["stim_duration_sec"] * fs) for c in params["stim_conditions"]}}
  stride = n if params["stride_sec"] is None else int(params["stride_sec"] * fs)
  labels, counts = np.unique(idx.labels, return_counts=True)
  return _jsonable({
    "subject": subject, "session": params["session"], "recording": recording, "git_commit": git_commit,
    "filter_mode": params["filter_mode"], "fs": float(fs), "channels": params["scalp"],
    "window_sec": params["window_sec"], "stride_sec": params["stride_sec"], "n_samples": n,
    "stride_samples": stride, "overlap_fraction": 1.0 - stride / n if stride < n else 0.0,
    "windows_per_trial": {c: windows_per_segment(L, n, stride) for c, L in seg_len.items()},
    "broadband": {"lowcut_hz": params["lowcut"], "highcut_hz": params["highcut"], "order": params["order"],
                  "notch_hz": params["notch_hz"], "notch_q": params["notch_q"], "zero_phase": True,
                  "applied": "continuous"},
    "filters": {"broadband": "butterworth bandpass + notch", **{b: f"{len(v)} bands" for b, v in
                                                                 built["banks_meta"].items()}},
    "bands": built["banks_meta"], "bands_skipped": built["bands_skipped"], "band_overlaps": _cross_overlaps(built),
    "data_source": ("legacy per_window build (PF-14)" if params["filter_mode"] == "per_window" else "continuous build")
                   + f", quality source {q['source']}",
    "legacy": params["filter_mode"] == "per_window",
    "label_counts": dict(zip(labels.tolist(), counts.tolist())), "n_windows": int(len(idx)),
    "n_trials": int(len(np.unique(idx.trial_ids))), "skipped_segments": idx.skipped,
    "quality": {"channels_kept": q["channels_kept"], "channels_dropped": q["channels_dropped"],
                "channel_stats": q["channel_stats"], "guard_sec": q["guard_sec"],
                "guard_samples": q["guard_samples"], "artifact_fraction": q["artifact_fraction"],
                "guarded_fraction": q["guarded_fraction"], "n_artifact_blocks": q["n_artifact_blocks"],
                "rejections_by_label": q["rejections_by_label"], "params": q["params"], "source": q["source"],
                "channel_stats_raw": q["channel_stats_raw"], "n_artifact_blocks_raw": q["n_artifact_blocks_raw"],
                "artifact_fraction_raw": q["artifact_fraction_raw"], "guarded_fraction_raw": q["guarded_fraction_raw"],
                "n_reason3_raw_gate": q["n_raw_gate"], "n_reason3_raw_guard": q["n_raw_guard"],
                "n_valid": int(q["valid_mask"].sum()), "n_valid_no_guard": int(q["valid_mask_no_guard"].sum()),
                "reason_codes": {"0": "valid", "1": "own_gate", "2": "guard", "3": "raw (gate or guard)"}},
  })


def save_built(out_dir: Path, built: dict, meta: dict) -> list:
  """Write the section 5.2 files into `out_dir` (a temporary folder is renamed over it); returns file names."""
  out_dir = Path(out_dir)
  tmp = out_dir.with_name(out_dir.name + ".partial")
  if tmp.exists():
    shutil.rmtree(tmp)
  tmp.mkdir(parents=True)
  idx, q = built["idx"], built["quality"]
  arrays = {"X_time_windows": built["X_time"].astype(np.float64), "X_raw_windows": built["X_raw"].astype(np.float64),
            "y_labels": idx.labels.astype(np.int64), "trial_ids": idx.trial_ids.astype(np.int64),
            "window_starts": idx.starts.astype(np.int64), "sub_idx": idx.sub_idx.astype(np.int64),
            "window_offsets": idx.offsets.astype(np.int64), "valid_mask": q["valid_mask"].astype(np.int8),
            "valid_mask_no_guard": q["valid_mask_no_guard"].astype(np.int8),
            "reject_reason": q["reason"].astype(np.int8),
            **{f"X_bands_{b}": v.astype(np.float64) for b, v in built["bands"].items()}}
  n = len(idx)
  for name, a in arrays.items():
    if len(a) != n:
      raise RuntimeError(f"{name}: {len(a)} rows for {n} windows")
    np.save(tmp / f"{name}.npy", a)
  (tmp / "windows_meta.json").write_text(json.dumps(meta, indent=1) + "\n")
  if out_dir.exists():
    shutil.rmtree(out_dir)
  tmp.rename(out_dir)
  return sorted(p.name for p in out_dir.iterdir())


# --- legacy comparison (P02 code path) ------------------------------------------------

def legacy_reference(x: np.ndarray, mark: np.ndarray, fs: float, cfg: dict, scalp: Sequence[str]) -> dict:
  """Legacy starts before and after the P02 raw gate, from the P02 code path on the same recording.

  `pre`: `{code: starts}` with the gate opened (every sub-window of every complete segment, as
  `run_preprocessing.ungated_windows`); `post`: `starts (n,)`, `y (n,)` of the saved legacy arrays (PO7
  excluded, 1-60 Hz, legacy gate, `--legacy-p02` parameters).
  """
  from scripts.preprocessing import run_preprocessing as rp
  from src.features.ssvep.psd_extraction import process_condition_windows_with_baseline
  args = rp.build_parser().parse_args([])
  params = rp.resolve_params(cfg, args)
  params["scalp"] = [c for c in params["scalp"] if c not in LEGACY_EXCLUDED]   # legacy: 7 channels
  params["channel_drop"] = False
  rows = [list(scalp).index(c) for c in params["scalp"]]
  inf = float("inf")
  recs = process_condition_windows_with_baseline(
    x[rows], mark, fs, target_conditions=params["stim_conditions"], cue_condition=params["cue_condition"],
    cross_condition=params["cross_condition"], sub_window_sec=params["sub_window_sec"], vpp_thresh=inf,
    std_range=(-inf, inf), stim_duration_sec=params["stim_duration_sec"],
    cue_lookback_sec=params["cue_lookback_sec"], vpp_min=-inf, cross_duration_sec=params["cross_duration_sec"])
  pre = {c: rp.window_starts(recs, [c]) for c in params["feature_conditions"]}
  out = rp.preprocess_recording(x[rows], mark, fs, params)
  return {"pre": pre, "post_starts": out["starts"], "post_y": out["y"]}


def starts_report(subject: str, ref_pre: dict, idx) -> list:
  """Lines `n_legacy, n_built, n_equal, max|d|` per condition (equal = same start sample in both)."""
  lines = []
  for c, leg in ref_pre.items():
    blt = idx.starts[idx.labels == c]
    n_eq = int(len(np.intersect1d(leg, blt)))
    mx = int(np.abs(leg - blt).max()) if len(leg) == len(blt) and len(leg) else (0 if not len(leg) else -1)
    lines.append(f"  legacy-starts {subject} {c}: n_legacy {len(leg)}, n_built {len(blt)}, n_equal {n_eq}, "
                 f"max|d| {mx if mx >= 0 else 'n/a'}")
  return lines


def trial_id_report(subject: str, ref: dict, idx, stim_conditions: Sequence[int]) -> str:
  """P11 D-2: stimulus windows of the legacy arrays (post gate), reconstructed vs true trial ids.

  The reconstruction runs on the whole label array (201/202 blocks included, as `load_subject` does) and the
  comparison is restricted to the stimulus windows: 201 and its 202 twin share one true id on purpose (PF-13),
  which a label-block reconstruction cannot reproduce and no stimulus-only analysis uses.
  """
  pos = {(int(s), int(l)): int(t) for s, l, t in zip(idx.starts, idx.labels, idx.trial_ids)}
  y = ref["post_y"]
  rec = build_trial_ids(y, LEGACY_TRIAL_LENGTHS, warn=False)
  true = np.array([pos.get((int(s), int(l)), -1) for s, l in zip(ref["post_starts"], y)])
  if (true < 0).any():
    return f"  trial-ids {subject}: {int((true < 0).sum())} legacy windows have no built twin"
  stim = np.isin(y, list(stim_conditions))
  r = compare_trial_ids(rec[stim], true[stim])
  return (f"  trial-ids {subject}: legacy stimulus windows {r['n_windows']}, reconstructed trials {r['n_reconstructed']}, "
          f"true trials {r['n_true']}, windows in inconsistent groups {r['n_inconsistent_windows']}")


def startup_report(subject: str, x: np.ndarray, built: dict, params: dict, fs: float, names: Sequence[str],
                   ref: Optional[dict]) -> list:
  """P02 carry-forward: does the filter start-up transient reach the first trial?

  First trial = windows starting within `FIRST_TRIAL_SEC` of the first 201 onset. Reports (a) the largest
  difference, relative to the channel std, between the continuous broadband output and the same filter on the
  recording extended by `STARTUP_PAD_SEC` of odd reflection in front (the transient the zero-phase padding
  leaves), per channel; (b) the built decision of those windows with Vpp per channel (PO8 first); (c) the
  windows of the first trial the legacy gate rejected (when `ref` is given).
  """
  idx, q = built["idx"], built["quality"]
  t0 = int(idx.starts[idx.labels == params["cross_condition"]].min())
  first = (idx.starts >= t0) & (idx.starts < t0 + int(FIRST_TRIAL_SEC * fs))
  pad = int(STARTUP_PAD_SEC * fs)
  ext = np.concatenate([2 * x[:, :1] - x[:, pad:0:-1], x], axis=1)           # odd reflection about x[0]
  full = broadband_filter(ext, fs, params["lowcut"], params["highcut"], params["order"],
                          params["notch_hz"], params["notch_q"])[:, pad:]
  diff = np.abs(full - built["broadband"])
  rel = np.zeros(len(names))
  n = built["n_samples"]
  for s in idx.starts[first]:
    rel = np.maximum(rel, diff[:, s:s + n].max(axis=1) / np.maximum(built["broadband"][:, s:s + n].std(axis=1), 1e-12))
  vpp = np.ptp(built["X_time"][first], axis=-1)
  lines = [f"  startup {subject}: first trial {int(first.sum())} windows (from sample {t0}); max |continuous - "
           f"{STARTUP_PAD_SEC:g} s-extended| / window std per channel: "
           + ", ".join(f"{c} {r:.2e}" for c, r in zip(names, rel)),
           f"  startup {subject}: built reasons of those windows {np.bincount(q['reason'][first], minlength=3).tolist()}"
           f" (0 valid, 1 own gate, 2 guard); mean Vpp uV per channel: "
           + ", ".join(f"{c} {v:.1f}" for c, v in zip(names, vpp.mean(axis=0)))]
  if ref is not None:
    post = set(int(s) for s in ref["post_starts"])
    lo, hi = t0, t0 + int(FIRST_TRIAL_SEC * fs)
    leg_pre = np.concatenate([v for v in ref["pre"].values()]) if ref["pre"] else np.array([])
    leg_first = [int(s) for s in leg_pre if lo <= s < hi]
    rej = [s for s in leg_first if s not in post]
    lines.append(f"  startup {subject}: legacy gate rejected {len(rej)} of {len(leg_first)} first-trial windows"
                 + (f" (starts {rej})" if rej else ""))
  return lines


# --- output formatting ----------------------------------------------------------------

def quality_lines(subject: str, built: dict, fs: float, x: np.ndarray) -> list:
  q, idx = built["quality"], built["idx"]
  n, nv, ng = len(idx), int(q["valid_mask"].sum()), int(q["valid_mask_no_guard"].sum())
  out = [f"[+] {subject}: fs {fs:g} Hz (header), {x.shape[0]} channels, {x.shape[1]} samples ({x.shape[1] / fs:.1f} s); "
         f"{n} windows, {len(np.unique(idx.trial_ids))} trial ids; valid {nv} (no guard {ng}); guard "
         f"{q['guard_sec']:.3f} s, artifact blocks {q['n_artifact_blocks']} ({q['artifact_fraction']:.2%} of the recording, "
         f"{q['guarded_fraction']:.2%} guarded)",
         f"  channels kept {q['channels_kept']}; dropped {q['channels_dropped'] or 'none'}; fail fractions: "
         + ", ".join(f"{c} {s['fail_fraction']:.1%}" for c, s in q["channel_stats"].items())]
  out.append(f"  quality source {q['source']}: reasons 1/2/3 = {int((q['reason'] == 1).sum())}/{int((q['reason'] == 2).sum())}/"
             f"{int((q['reason'] == 3).sum())} (3: raw gate {q['n_raw_gate']}, raw guard {q['n_raw_guard']})"
             + ("" if q["n_artifact_blocks_raw"] is None else f"; raw artifact blocks {q['n_artifact_blocks_raw']} "
                f"({q['artifact_fraction_raw']:.2%}, {q['guarded_fraction_raw']:.2%} guarded)"))
  for lab, r in q["rejections_by_label"].items():
    out.append(f"  rejected {subject} {lab}: total {r['total']}, valid {r['valid']}, own_gate {r['own_gate']}, "
               f"guard {r['guard']}, raw {r['raw']}")
  for b, sk in built["bands_skipped"].items():
    if sk:
      out.append(f"  bands skipped {subject} {b}: " + "; ".join(f"{k['center']:g} Hz [{k['low']:g}, {k['high']:g}] "
                                                              f"({k['why']})" for k in sk))
  if idx.skipped:
    out.append(f"  skipped segments {len(idx.skipped)}: " + "; ".join(f"{s['condition']}@{s['onset']} ({s['why']})"
                                                                       for s in idx.skipped[:6]))
  return out


def output_root(args: argparse.Namespace, root: Path) -> Path:
  """`--out-root` or `<root>/data/processed_<mode>`, plus `w<len>_s<stride>` when the window or stride is given."""
  base = Path(args.out_root) if args.out_root else root / "data" / built_dir_name(args.filter_mode)
  if args.window_sec is not None or args.stride_sec is not None:
    win = args.window_sec if args.window_sec is not None else 1.0
    base = base / f"w{win:g}_s{(args.stride_sec if args.stride_sec is not None else win):g}"
  return base


def git_commit(root: Path) -> str:
  r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
  return r.stdout.strip() if r.returncode == 0 else "unknown"


def discover_raw_subjects(raw_dir: Path) -> list:
  found = [p.name for p in Path(raw_dir).iterdir() if p.is_dir() and SUBJECT_PATTERN.fullmatch(p.name)]
  return sorted(found, key=lambda s: int(s[1:]))


def diff_build_params(old, new: dict) -> list:
  """Keys (`quality` split into `quality.<k>`) whose recorded value differs from the requested one; all keys
  if `old` is not a dict (a folder without recorded build_params)."""
  new = json.loads(json.dumps(new, default=str))
  if not isinstance(old, dict):
    return sorted(new)
  out = []
  for k in sorted(set(old) | set(new)):
    if k == "quality" and isinstance(old.get(k), dict) and isinstance(new.get(k), dict):
      out += [f"quality.{j}" for j in sorted(set(old[k]) | set(new[k])) if old[k].get(j) != new[k].get(j)
              or (j in old[k]) != (j in new[k])]
    elif old.get(k) != new.get(k) or (k in old) != (k in new):
      out.append(k)
  return out


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--filter-mode", choices=MODES, default="continuous",
                 help="continuous = filter the recording, then cut (R3); per_window = cut, then filter (legacy, PF-14)")
  p.add_argument("--subjects", nargs="+", default=None, help="subject folders (default: every S\\d+ in --raw-dir)")
  p.add_argument("--session", default=DEFAULT_SESSION, help="recording file stem (default: OO)")
  p.add_argument("--guard-sec", default=None, help="artifact guard in seconds or 'auto' (default: config quality.guard_sec)")
  p.add_argument("--quality-source", choices=SOURCES, default=None,
                 help="signal the quality gate checks: filtered, raw (unfiltered windows) or both "
                 "(default: config quality.source)")
  p.add_argument("--window-sec", type=float, default=None, help="window length (default: config sub_window_sec); "
                 "giving it or --stride-sec saves under w<len>_s<stride>/")
  p.add_argument("--stride-sec", type=float, default=None, help="window stride (default: none = the legacy starts)")
  p.add_argument("--banks", nargs="+", choices=BANK_NAMES, default=None,
                 help="sub-band banks to save (default: fbcca fbcsp + the narrow banks enabled in config filter_bank:)")
  p.add_argument("--out-root", type=Path, default=None, help="default: <root>/data/processed_<filter-mode>")
  p.add_argument("--raw-dir", type=Path, default=None, help="default: <root>/ + paths.data_raw_dir")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--check-legacy-starts", action="store_true",
                 help="compare with the P02 legacy starts/trial ids and print the first-trial start-up report")
  p.add_argument("--overwrite", action="store_true",
                 help="rewrite a subject folder whose recorded build_params differ from the requested ones (P17 C-a)")
  p.add_argument("--resume", action="store_true", help="skip subjects already built with the same parameters")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  try:
    cfg = load_build_config(args.config)
    params = resolve_params(cfg, args)
  except (OSError, ValueError, TypeError) as exc:
    print(f"[x] Config: {exc}")
    return 1
  raw_dir = args.raw_dir or ROOT / cfg.get("paths", {}).get("data_raw_dir", "data/raw")
  out_root = output_root(args, ROOT)
  if not Path(raw_dir).is_dir():
    print(f"[x] Raw folder not found: {raw_dir}")
    return 1
  if (out_root / "S01" / LEGACY_ARRAY).exists() or out_root.resolve() == (ROOT / "data" / "processed").resolve():
    print(f"[x] Refusing to write built windows into a legacy folder: {out_root}")
    return 1
  subjects = args.subjects or discover_raw_subjects(raw_dir)
  if not subjects:
    print(f"[x] No subject folders matching ^S\\d+$ in {raw_dir}")
    return 1
  sig = {k: params[k] for k in ("scalp", "lowcut", "highcut", "order", "notch_hz", "notch_q", "window_sec",
                                "stride_sec", "filter_mode", "banks", "session", "quality")}
  print(f"Data source: {'legacy per_window' if args.filter_mode == 'per_window' else 'continuous'} build of {args.session}.ebr -> {out_root}/<S>/")
  print(f"Filter: Butterworth {params['lowcut']:g}-{params['highcut']:g} Hz order {params['order']} + notch "
        f"{params['notch_hz']} Hz Q {params['notch_q']:g}, zero-phase on the continuous signal; banks {params['banks']} "
        f"({args.filter_mode}); window {params['window_sec']:g} s, stride {params['stride_sec'] or 'none (legacy starts)'}")
  q = params["quality"]
  print(f"Quality: vpp [{q['vpp_min']:g}, {q['vpp_max']:g}] uV, std [{q['std_min']:g}, {q['std_max']:g}] uV, channel "
        f"fail fraction {q['channel_fail_fraction']:g}, artifact block {q['artifact_block_sec']:g} s, guard "
        f"{q['guard_sec']} (rel {q['guard_rel_amplitude']:g})")
  if not args.overwrite:                                       # P17 C-a: never silently replace a different build
    for subject in subjects:
      mp = out_root / subject / "windows_meta.json"
      if mp.is_file():
        diff = diff_build_params(json.loads(mp.read_text()).get("build_params"), sig)
        if diff:
          print(f"[x] Refusing to overwrite {out_root / subject}: its recorded build_params differ in {diff}; "
                f"use --overwrite to rewrite it")
          return 1
  commit = git_commit(ROOT)
  done, skipped, t_all = [], [], time.time()
  for subject in subjects:
    t0 = time.time()
    out_dir = out_root / subject
    if args.resume and (out_dir / "windows_meta.json").is_file():
      old = json.loads((out_dir / "windows_meta.json").read_text()).get("build_params")
      if old == json.loads(json.dumps(sig, default=str)):
        print(f"[=] {subject}: already built with the same parameters (--resume)")
        done.append(subject)
        continue
    try:
      path = ebr_parser.resolve_recording_path(raw_dir, subject, args.session)
      x, mark, fs = load_session(path, params["scalp"], params["mark_channel"])
      built = build_subject(x, mark, fs, params)
    except AllChannelsDropped:
      print(f"[-] Skipping {subject}: all channels dropped (source={params['quality']['source']})")
      skipped.append(subject)
      continue
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {subject}: {exc}")
      skipped.append(subject)
      continue
    meta = build_meta(built, params, fs, subject, path.name, commit)
    meta["build_params"] = json.loads(json.dumps(sig, default=str))
    files = save_built(out_dir, built, meta)
    for line in quality_lines(subject, built, fs, x):
      print(line)
    if args.check_legacy_starts:
      ref = legacy_reference(x, mark, fs, cfg, params["scalp"])
      for line in starts_report(subject, ref["pre"], built["idx"]):
        print(line)
      print(trial_id_report(subject, ref, built["idx"], params["stim_conditions"]))
      for line in startup_report(subject, x, built, params, fs, params["scalp"], ref):
        print(line)
    print(f"  saved {len(files)} files to {out_dir} ({time.time() - t0:.1f} s)")
    done.append(subject)
  print(f"\nCohort: {len(done)} subjects built ({', '.join(done) or 'none'}), {len(skipped)} skipped "
        f"({', '.join(skipped) or 'none'}); {time.time() - t_all:.1f} s")
  print(f"Saved: {out_root}")
  return 0 if done else 1


if __name__ == "__main__":
  sys.exit(main())
