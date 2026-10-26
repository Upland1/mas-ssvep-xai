"""Shared benchmark driver for the raw-window networks (P08 EEGNet, P09 Compact-CNN and ShallowConvNet; P11 protocol).

One code path so the three scripts cannot drift: same CLI, P07 two-tier gate on the legacy 7-channel arrays,
`--cv {grouped,legacy}` (default grouped: StratifiedGroupKFold over trial ids, R1; legacy: the P05-P10 window-level
StratifiedKFold, leaky, PF-01), `--smoothing {mod5,trial}` (default mod5: R8 legacy-folder clause; trial = PF-02
diagnostic), per-window z-score, training convention of `eegnet_cv`, train accuracy next to test accuracy (PF-30).
Each script supplies a `NetSpec`.

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session), stimulus windows only; no preprocessing is run.
Trial ids (PF-03): `build_trial_ids` on the full `y_labels.npy` (201/202 rows walked), the stimulus rows, then the valid
mask of the gate; subjects with a block that is not a multiple of its trial length are flagged `trial_ids_approximate`.
Output: <reports-dir>[/legacy_leaky for --cv legacy]/<name>_benchmark_<device>.csv (Subject, Device, Clean Windows,
Rejected, 1.0s Acc (%), 2.0s Smoothed (%), Train Acc (%), Params) + .meta.txt with the splitter, the smoothing rule,
the approximate-id subjects, the data source and n_channels.
"""

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np
import pandas as pd
import torch

from src.features.ssvep.spectral_power import LEGACY_FS_HZ
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, GATE_THRESHOLDS, MASK_LABEL, quality_gate
from src.io.channels import subject_channel_names
from src.models.classical.benchmark_runner import add_protocol_args, load_config, protocol_labels
from src.models.classical.legacy_eval import SEED
from src.models.cnn.eegnet_cv import (
  BATCH_SIZE, EPOCHS, ETA_MIN, LABEL_SMOOTHING, LR, WEIGHT_DECAY, train_and_eval_cv)
from src.models.cnn.spatial_spectral_cnn import resolve_device
from src.preprocessing.dataset.cv_utils import (
  LEGACY_TRIAL_LENGTHS, build_trial_ids, format_block_report, output_dir, trial_block_report)
from src.preprocessing.dataset.legacy_windows import CLASS_CODES, arrays_exist, load_stimulus_windows

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


AUGMENT_NOTE = {"off": "", "on": " (mixup, scale, shift, noise at p=0.5 on the z-scored training fold only, own numpy "
                "generator seeded seed+fold, PF-28/PF-29)"}


def build_parser(doc: str = __doc__) -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subject", default=DEFAULT_SUBJECT, help=f"subject folder (default {DEFAULT_SUBJECT})")
  p.add_argument("--subjects", nargs="*", default=None, help="several subject folders (overrides --subject)")
  p.add_argument("--epochs", type=int, default=EPOCHS)
  p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
  p.add_argument("--lr", type=float, default=LR)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--augment", choices=["off", "on"], default="off",
                 help="training-fold augmentation (P10, PF-29); fold k seeds its generator with seed+k (default off)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV seed; fold k seeds the model with seed+k (default {SEED})")
  add_protocol_args(p)
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
  """Clean raw windows `(n, C', T)` on the kept channels of the P07 two-tier gate (same decision as the flagship).

  Also `trial_ids` of the clean windows (PF-03: ids of the pre-gate labels, stimulus rows, then the valid mask),
  `trial_block_report` and `trial_ids_approximate` (a block not a multiple of its trial length)."""
  if not arrays_exist(processed, subject):
    raise FileNotFoundError(f"arrays missing in {processed / subject}")
  _, X_time, y = load_stimulus_windows(processed, subject)
  names = subject_channel_names(processed, subject, X_time.shape[1], None)
  q = quality_gate(X_time, y, names, GATE_THRESHOLDS, CHANNEL_FAIL_FRACTION)
  y_all = np.load(Path(processed) / subject / "y_labels.npy")
  ids_all = build_trial_ids(y_all, LEGACY_TRIAL_LENGTHS, warn=False)
  ids_stim = ids_all[np.isin(y_all, CLASS_CODES)]
  rep = trial_block_report(y, ids_stim, LEGACY_TRIAL_LENGTHS)
  ids = ids_stim[np.asarray(q["valid_mask"]).astype(bool)]
  return {"X": q["windows_clean"], "y": q["y_clean"], "kept": list(q["channels_kept"]),
          "dropped": list(q["channels_dropped"]), "n_stimulus": int(len(y)), "n_clean": int(len(q["y_clean"])),
          "trial_ids": ids, "trial_block_report": rep, "trial_ids_approximate": rep["approximate"],
          "n_trials": int(len(np.unique(ids)))}


def trial_line(subject: str, g: dict) -> str:
  """Printed one-liner of the trial ids of a subject (task 2); the block lengths follow when they are approximate."""
  line = (f"  {subject}: {g['n_trials']} trials in {g['n_clean']} clean windows; trial ids "
          f"{'APPROXIMATE' if g['trial_ids_approximate'] else 'exact'}")
  return line + "\n" + format_block_report(g["trial_block_report"]) if g["trial_ids_approximate"] else line


def header_lines(spec: NetSpec, seed: int, device: str, args) -> list:
  th = GATE_THRESHOLDS
  cv_text, smooth_text = protocol_labels(args.cv, args.smoothing)
  return [
    f"device={device} (CPU and CUDA numbers differ; each is deterministic)",
    f"cv={cv_text}; seed={seed}",
    f"smoothing: {smooth_text}",
    f"quality gate (R5 per-script, {MASK_LABEL}, as the classical flagship): vpp [{th['vpp_min']:g}, {th['vpp_max']:g}] uV, "
    f"std [{th['std_min']:g}, {th['std_max']:g}] uV, channel dropped if it fails in > {CHANNEL_FAIL_FRACTION:.0%} of the windows",
    f"input: raw clean windows, per-window per-channel z-score (own mean/std over time, R2); fs {LEGACY_FS_HZ:g} Hz legacy "
    f"label ({spec.fs_note})",
    f"training: epochs={args.epochs} (fixed, no early stopping, no validation split), batch={args.batch_size}, "
    f"AdamW lr={args.lr:g} wd={WEIGHT_DECAY:g}, CosineAnnealingLR eta_min={ETA_MIN:g}, CE label_smoothing={LABEL_SMOOTHING:g}, "
    f"manual_seed(seed+fold) per fold, seeded DataLoader generator, {spec.training_extra}augment={args.augment}" + AUGMENT_NOTE[args.augment],
    "train accuracy: mean over folds, eval mode on the un-augmented training fold (PF-30)",
    "trial ids: contiguous same-label blocks of the pre-gate labels (201: 2, 202: 1, 101-105: 5 windows per trial), "
    "indexed by the valid mask (PF-03)",
  ]


def approximate_line(subjects: Sequence[str], flags: dict) -> str:
  """Meta line naming the subjects whose trial ids are approximate (PF-03)."""
  bad = [s for s in subjects if flags.get(s)]
  return f"trial_ids_approximate subjects: {', '.join(bad) if bad else 'none'}"


def run_benchmark(spec: NetSpec, root: Path, argv: Optional[Sequence[str]] = None, doc: str = __doc__) -> int:
  args = build_parser(doc).parse_args(argv)
  cfg = load_config(args.config or root / "configs" / "pipeline_config.yaml")
  processed = Path(args.data_root or root / cfg["paths"]["data_processed_dir"])
  reports = output_dir(args.reports_dir or root / "reports", args.cv)
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
  rows, n_channels, approx = [], [], {}
  for s in subjects:
    try:
      g = gated_windows(processed, s)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    print(f"  {s}: {g['n_stimulus']} stimulus, {g['n_clean']} clean, {g['n_stimulus'] - g['n_clean']} rejected; "
          f"channels kept {len(g['kept'])} [{', '.join(g['kept'])}]; dropped [{', '.join(g['dropped']) or 'none'}]", flush=True)
    print(trial_line(s, g), flush=True)
    n_channels.append(f"{s}={len(g['kept'])}")
    approx[s] = g["trial_ids_approximate"]
    t1 = time.time()
    r = train_and_eval_cv(g["X"], g["y"], spec.build, args.epochs, args.batch_size, args.lr, dev.type, args.seed, verbose=True,
                         augment=args.augment == "on", groups=g["trial_ids"], cv=args.cv, smoothing=args.smoothing)
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
  tag = "_aug" if args.augment == "on" else ""
  csv = reports / f"{spec.name}{tag}_benchmark_{dev.type}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text(
    "\n".join(header) + f"\n{source}\nn_channels (after the gate): {', '.join(n_channels)}\n"
    f"{approximate_line(subjects, approx)}\n{spec.model_line}\n")
  print("\n" + df.to_string(index=False))
  note = ("Legacy leaky CV (R1/PF-01): not comparable with the leak-free numbers" if args.cv == "legacy"
          else "Trial-grouped CV (R1), 7-channel legacy arrays, fs 250 label")
  print(f"\n{note}; 2.0 s rule {args.smoothing}; runtime {time.time() - t0:.0f} s")
  print(f"Saved: {rel(csv, root)}")
  return 0
