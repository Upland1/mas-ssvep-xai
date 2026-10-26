"""Shared legacy benchmark driver for the raw-window networks (P08 EEGNet, P09 Compact-CNN and ShallowConvNet).

One code path so the three scripts cannot drift: same CLI, P07 two-tier gate on the legacy 7-channel arrays,
legacy leaky folds (R1/PF-01), `i % 5` smoothing (R8/PF-02), per-window z-score, training convention of
`eegnet_cv`, train accuracy next to test accuracy (PF-30). Each script supplies a `NetSpec`.

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session), stimulus windows only; no preprocessing is run.
Output: <reports-dir>/<name>_benchmark_<device>.csv (Subject, Device, Clean Windows, Rejected, 1.0s Acc (%),
2.0s Smoothed (%), Train Acc (%), Params) + .meta.txt with the protocol labels, the data source and n_channels.
"""

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

import pandas as pd
import torch

from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, GATE_THRESHOLDS, MASK_LABEL, quality_gate
from src.io.channels import subject_channel_names
from src.models.classical.benchmark_runner import load_config
from src.models.classical.legacy_eval import CV_LABEL, SEED, SMOOTH_LABEL
from src.models.cnn.eegnet_cv import (
  BATCH_SIZE, EPOCHS, ETA_MIN, LABEL_SMOOTHING, LR, WEIGHT_DECAY, train_and_eval_cv)
from src.models.cnn.spatial_spectral_cnn import resolve_device
from src.preprocessing.dataset.legacy_windows import arrays_exist, load_stimulus_windows

DEFAULT_SUBJECT = "S03"
COLUMNS = ["Subject", "Device", "Clean Windows", "Rejected", "1.0s Acc (%)", "2.0s Smoothed (%)",
           "Train Acc (%)", "Params"]


@dataclass(frozen=True)
class NetSpec:
  name: str  # CSV prefix, e.g. "eegnet"
  build: Callable  # (n_classes, n_channels, n_samples) -> nn.Module
  model_line: str  # "model: ..." line of the .meta.txt
  fs_note: str  # how the legacy fs label relates to the network
  training_extra: str  # extra training facts (e.g. max-norm)


def build_parser(doc: str = __doc__) -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default {DEFAULT_SUBJECT})")
  p.add_argument("--subjects", nargs="*", default=None, help="several subject folders (overrides --subject)")
  p.add_argument("--epochs", type=int, default=EPOCHS)
  p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
  p.add_argument("--lr", type=float, default=LR)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--augment", choices=["off"], default="off", help="augmentation arrives in P10; only 'off' here")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV seed; fold k seeds the model with seed+k (default {SEED})")
  p.add_argument("--config", type=Path, default=None, help="default: <root>/configs/pipeline_config.yaml")
  p.add_argument("--data-root", "--processed-dir", dest="data_root", type=Path, default=None,
                 help="legacy folders; default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  return p


def rel(path: Path, root: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(root))
  except ValueError:
    return str(path)


def gated_windows(processed: Path, subject: str) -> dict:
  """Clean raw windows `(n, C', T)` on the kept channels of the P07 two-tier gate (same decision as the flagship)."""
  if not arrays_exist(processed, subject):
    raise FileNotFoundError(f"arrays missing in {processed / subject}")
  _, X_time, y = load_stimulus_windows(processed, subject)
  names = subject_channel_names(processed, subject, X_time.shape[1], None)
  q = quality_gate(X_time, y, names, GATE_THRESHOLDS, CHANNEL_FAIL_FRACTION)
  return {"X": q["windows_clean"], "y": q["y_clean"], "kept": list(q["channels_kept"]),
          "dropped": list(q["channels_dropped"]), "n_stimulus": int(len(y)), "n_clean": int(len(q["y_clean"]))}


def header_lines(spec: NetSpec, seed: int, device: str, args) -> list:
  th = GATE_THRESHOLDS
  return [
    f"device={device} (CPU and CUDA numbers differ; each is deterministic)",
    f"cv={CV_LABEL}; seed={seed}",
    f"smoothing: {SMOOTH_LABEL}",
    f"quality gate (R5 per-script, {MASK_LABEL}, as the classical flagship): vpp [{th['vpp_min']:g}, {th['vpp_max']:g}] uV, "
    f"std [{th['std_min']:g}, {th['std_max']:g}] uV, channel dropped if it fails in > {CHANNEL_FAIL_FRACTION:.0%} of the windows",
    f"input: raw clean windows, per-window per-channel z-score (own mean/std over time, R2); fs {LEGACY_FS_HZ:g} Hz legacy "
    f"label ({spec.fs_note})",
    f"training: epochs={args.epochs} (fixed, no early stopping, no validation split), batch={args.batch_size}, "
    f"AdamW lr={args.lr:g} wd={WEIGHT_DECAY:g}, CosineAnnealingLR eta_min={ETA_MIN:g}, CE label_smoothing={LABEL_SMOOTHING:g}, "
    f"manual_seed(seed+fold) per fold, seeded DataLoader generator, {spec.training_extra}augment=off",
    "train accuracy: mean over folds, eval mode on the un-augmented training fold (PF-30)",
  ]


def run_benchmark(spec: NetSpec, root: Path, argv: Optional[Sequence[str]] = None, doc: str = __doc__) -> int:
  args = build_parser(doc).parse_args(argv)
  cfg = load_config(args.config or root / "configs" / "pipeline_config.yaml")
  processed = Path(args.data_root or root / cfg["paths"]["data_processed_dir"])
  reports = Path(args.reports_dir or root / "reports")
  subjects = args.subjects or [args.subject]
  dev = resolve_device(args.device)
  if dev.type == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  t0 = time.time()
  header = header_lines(spec, args.seed, dev.type, args)
  source = (f"Data source: legacy windows, {rel(processed, root)}/<S>/ (P02, OO session), stimulus windows only; "
            f"subjects {', '.join(subjects)}")
  print(source)
  print("\n".join(header))
  rows, n_channels = [], []
  for s in subjects:
    try:
      g = gated_windows(processed, s)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    print(f"  {s}: {g['n_stimulus']} stimulus, {g['n_clean']} clean, {g['n_stimulus'] - g['n_clean']} rejected; "
          f"channels kept {len(g['kept'])} [{', '.join(g['kept'])}]; dropped [{', '.join(g['dropped']) or 'none'}]", flush=True)
    n_channels.append(f"{s}={len(g['kept'])}")
    t1 = time.time()
    r = train_and_eval_cv(g["X"], g["y"], spec.build, args.epochs, args.batch_size, args.lr, dev.type, args.seed, verbose=True)
    rows.append({"Subject": s, "Device": dev.type, "Clean Windows": g["n_clean"],
                 "Rejected": g["n_stimulus"] - g["n_clean"],
                 "1.0s Acc (%)": round(100 * r["accuracy"], 2), "2.0s Smoothed (%)": round(100 * r["smoothed_accuracy"], 2),
                 "Train Acc (%)": round(100 * r["train_accuracy"], 2), "Params": r["n_params"]})
    print(f"[+] {s} [{dev.type}]: 1.0 s {100 * r['accuracy']:.2f}%  2.0 s smoothed {100 * r['smoothed_accuracy']:.2f}%  "
          f"train {100 * r['train_accuracy']:.2f}%  params {r['n_params']}  ({time.time() - t1:.0f} s)")
  if not rows:
    print("[-] No subject evaluated")
    return 1
  df = pd.DataFrame(rows, columns=COLUMNS)
  csv = reports / f"{spec.name}_benchmark_{dev.type}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text(
    "\n".join(header) + f"\n{source}\nn_channels (after the gate): {', '.join(n_channels)}\n{spec.model_line}\n")
  print("\n" + df.to_string(index=False))
  print(f"\nLegacy leaky CV (R1/PF-01) and i%5 smoothing (R8/PF-02): not comparable with R-6; runtime {time.time() - t0:.0f} s")
  print(f"Saved: {rel(csv, root)}")
  return 0
