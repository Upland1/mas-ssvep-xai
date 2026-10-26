"""EEGNet on raw legacy windows (P08.2, legacy Era A, numbers are leaky).

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows only,
gated once by the P07 two-tier gate (vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the
windows; R5 per-script gate) exactly as the classical flagship; no preprocessing is run. Each window is
z-scored per channel over its own samples; EEGNetSSVEP is trained from scratch per fold.

Legacy behaviours (labelled, fixed in P11): R1/PF-01 StratifiedKFold(5, shuffle, 42) over windows (leaky,
NOT comparable with the leak-free R-6); R8/PF-02 "2.0 s smoothed" = legacy i%5 trial smoothing. Fixed
epochs, no validation split, no early stopping, augmentation off (P10). Train accuracy = un-augmented
training fold (PF-30). CPU and CUDA give different but individually deterministic numbers: the device is
stated with every number and in the CSV name (reports/eegnet_benchmark_<device>.csv; `auto` -> resolved device).

Output: <reports-dir>/eegnet_benchmark_<device>.csv (Subject, Device, Clean Windows, Rejected, 1.0s Acc (%),
2.0s Smoothed (%), Train Acc (%), Params) + .meta.txt with the protocol labels.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else three levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import torch  # noqa: E402

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, GATE_THRESHOLDS, MASK_LABEL, quality_gate  # noqa: E402
from src.io.channels import subject_channel_names  # noqa: E402
from src.models.classical.benchmark_runner import discover_subjects, load_config  # noqa: E402
from src.models.classical.legacy_eval import CV_LABEL, SEED, SMOOTH_LABEL  # noqa: E402
from src.models.cnn.eegnet_cv import (  # noqa: E402
  BATCH_SIZE, EPOCHS, LABEL_SMOOTHING, LR, WEIGHT_DECAY, ETA_MIN, train_and_eval_eegnet_cv)
from src.models.cnn.spatial_spectral_cnn import resolve_device  # noqa: E402
from src.preprocessing.dataset.legacy_windows import arrays_exist, load_stimulus_windows  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
DEFAULT_SUBJECT = "S03"
COLUMNS = ["Subject", "Device", "Clean Windows", "Rejected", "1.0s Acc (%)", "2.0s Smoothed (%)",
           "Train Acc (%)", "Params"]


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default {DEFAULT_SUBJECT})")
  p.add_argument("--subjects", nargs="*", default=None, help="several subject folders (overrides --subject)")
  p.add_argument("--epochs", type=int, default=EPOCHS)
  p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
  p.add_argument("--lr", type=float, default=LR)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--augment", choices=["off"], default="off", help="augmentation arrives in P10; only 'off' here")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV seed; fold k seeds the model with seed+k (default {SEED})")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--data-root", "--processed-dir", dest="data_root", type=Path, default=None,
                 help="legacy folders; default: <root>/ + paths.data_processed_dir")
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
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


def header_lines(seed: int, device: str, args) -> list:
  th = GATE_THRESHOLDS
  return [
    f"device={device} (CPU and CUDA numbers differ; each is deterministic)",
    f"cv={CV_LABEL}; seed={seed}",
    f"smoothing: {SMOOTH_LABEL}",
    f"quality gate (R5 per-script, {MASK_LABEL}, as the classical flagship): vpp [{th['vpp_min']:g}, {th['vpp_max']:g}] uV, "
    f"std [{th['std_min']:g}, {th['std_max']:g}] uV, channel dropped if it fails in > {CHANNEL_FAIL_FRACTION:.0%} of the windows",
    f"input: raw clean windows, per-window per-channel z-score (own mean/std over time, R2); fs {LEGACY_FS_HZ:g} Hz legacy "
    f"label (not used by EEGNet)",
    f"training: epochs={args.epochs} (fixed, no early stopping, no validation split), batch={args.batch_size}, "
    f"AdamW lr={args.lr:g} wd={WEIGHT_DECAY:g}, CosineAnnealingLR eta_min={ETA_MIN:g}, CE label_smoothing={LABEL_SMOOTHING:g}, "
    f"manual_seed(seed+fold) per fold, seeded DataLoader generator, max-norm 1.0 on the spatial depthwise filters, augment=off",
    "train accuracy: mean over folds, eval mode on the un-augmented training fold (PF-30)",
  ]


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = Path(args.data_root or ROOT / cfg["paths"]["data_processed_dir"])
  reports = Path(args.reports_dir or ROOT / "reports")
  subjects = args.subjects or [args.subject]
  dev = resolve_device(args.device)
  if dev.type == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  t0 = time.time()
  header = header_lines(args.seed, dev.type, args)
  print(f"Data source: legacy windows, {_rel(processed)}/<S>/ (P02, OO session), stimulus windows only; "
        f"subjects {', '.join(subjects)}")
  print("\n".join(header))
  rows = []
  for s in subjects:
    try:
      g = gated_windows(processed, s)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    print(f"  {s}: {g['n_stimulus']} stimulus, {g['n_clean']} clean, {g['n_stimulus'] - g['n_clean']} rejected; "
          f"channels kept {len(g['kept'])} [{', '.join(g['kept'])}]; dropped [{', '.join(g['dropped']) or 'none'}]", flush=True)
    t1 = time.time()
    r = train_and_eval_eegnet_cv(g["X"], g["y"], args.epochs, args.batch_size, args.lr, dev.type, args.seed, verbose=True)
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
  csv = reports / f"eegnet_benchmark_{dev.type}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text("\n".join(header) + "\nmodel: EEGNetSSVEP(n_classes=5, F1=8, D=2, F2=16, kernel_length=125, dropout=0.25)\n")
  print("\n" + df.to_string(index=False))
  print(f"\nLegacy leaky CV (R1/PF-01) and i%5 smoothing (R8/PF-02): not comparable with R-6; runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
