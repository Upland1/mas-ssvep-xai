"""Augmentation A/B (P10.3; P11 protocol): every subject, augmentation OFF then ON, per network.

Data source: legacy folders <processed-dir>/<S>/ (P02, OO session, 7 channels), stimulus windows only, gated by the
P07 two-tier gate through the shared driver (src/models/cnn/benchmark_common.py); no preprocessing is run.
`--cv grouped` (default, R1): StratifiedGroupKFold(5, shuffle, 42) over trial ids reconstructed on the pre-gate
labels (PF-03); `--cv legacy`: the P10 window-level StratifiedKFold (R1/PF-01, leaky), outputs under
<reports-dir>/legacy_leaky/. `--smoothing mod5` (default, R8 legacy-folder clause) or `trial` (PF-02 diagnostic).
Both arms use the same folds (one split per subject, computed from the labels and ids only), the same
`torch.manual_seed(seed + fold)` before each model (identical initial weights, PF-28; the augmentation generator is a
separate numpy stream seeded seed + fold), the same seeded DataLoader generator and the same smoothing rule. ON augments
the z-scored training fold only (PF-29). Train accuracy = final model, eval mode, un-augmented training fold, mean
over folds (PF-30); it is a diagnostic and never enters a gradient.
A warning is printed when the OFF train accuracy is below 40 % (optimization problem, not generalization).

Output: <reports-dir>[/legacy_leaky]/augmentation_ab_<model>.csv (Subject, Clean Windows, 1.0s OFF (%), 1.0s ON (%),
1.0s Delta, 2.0s OFF (%), 2.0s ON (%), 2.0s Delta, Train Acc OFF (%), Train Acc ON (%)) + Mean row + .meta.txt (splitter,
smoothing rule, approximate-id subjects). `--freeze-legacy` (P10) is meaningful only with `--cv legacy`: the legacy
files are then written under legacy_leaky/ directly, so the flag is accepted and redundant; with `--cv grouped` it is an
error (a grouped file must never be frozen as legacy).
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Optional, Sequence


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

import pandas as pd  # noqa: E402
import torch  # noqa: E402

from scripts.benchmarks.neural_networks import benchmark_compact_cnn, benchmark_eegnet, benchmark_shallow_convnet  # noqa: E402
from src.models.classical.benchmark_runner import add_protocol_args, load_config  # noqa: E402
from src.models.classical.legacy_eval import SEED  # noqa: E402
from src.models.cnn.benchmark_common import (  # noqa: E402
  BATCH_SIZE, EPOCHS, LR, NetSpec, approximate_line, gated_windows, header_lines, rel, trial_line)
from src.models.cnn.eegnet_cv import train_and_eval_cv  # noqa: E402
from src.models.cnn.spatial_spectral_cnn import resolve_device  # noqa: E402
from src.preprocessing.dataset.cv_utils import output_dir  # noqa: E402

MODELS = {"eegnet": benchmark_eegnet.SPEC, "compact_cnn": benchmark_compact_cnn.SPEC,
          "shallow_conv_net": benchmark_shallow_convnet.SPEC, "shallow_convnet": benchmark_shallow_convnet.SPEC}
CANONICAL = {"shallow_convnet": "shallow_conv_net"}
COLUMNS = ["Subject", "Clean Windows", "1.0s OFF (%)", "1.0s ON (%)", "1.0s Delta", "2.0s OFF (%)", "2.0s ON (%)",
           "2.0s Delta", "Train Acc OFF (%)", "Train Acc ON (%)"]
TRAIN_WARN_PCT = 40.0


def discover(processed: Path) -> list:
  """Subject folders `S\\d+` under the processed directory, natural order."""
  found = [p.name for p in processed.iterdir() if p.is_dir() and re.fullmatch(r"S\d+", p.name)] if processed.is_dir() else []
  return sorted(found, key=lambda n: int(n[1:]))


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--model", choices=sorted(MODELS), required=True)
  p.add_argument("--epochs", type=int, default=EPOCHS)
  p.add_argument("--subjects", nargs="*", default=None, help="default: every S<k> folder found")
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="cpu", help="default cpu (decisions P08)")
  p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
  p.add_argument("--lr", type=float, default=LR)
  p.add_argument("--seed", type=int, default=SEED)
  add_protocol_args(p)
  p.add_argument("--freeze-legacy", action="store_true",
                 help="P10 flag, only with --cv legacy (legacy outputs already go to <reports-dir>/legacy_leaky/)")
  p.add_argument("--config", type=Path, default=None)
  p.add_argument("--data-root", "--processed-dir", dest="data_root", type=Path, default=None)
  p.add_argument("--reports-dir", type=Path, default=None)
  return p


def ab_row(subject: str, n_clean: int, off: dict, on: dict) -> dict:
  r = lambda v: round(100 * v, 2)  # noqa: E731
  return {"Subject": subject, "Clean Windows": n_clean,
          "1.0s OFF (%)": r(off["accuracy"]), "1.0s ON (%)": r(on["accuracy"]),
          "1.0s Delta": round(r(on["accuracy"]) - r(off["accuracy"]), 2),
          "2.0s OFF (%)": r(off["smoothed_accuracy"]), "2.0s ON (%)": r(on["smoothed_accuracy"]),
          "2.0s Delta": round(r(on["smoothed_accuracy"]) - r(off["smoothed_accuracy"]), 2),
          "Train Acc OFF (%)": r(off["train_accuracy"]), "Train Acc ON (%)": r(on["train_accuracy"])}


def with_mean(rows: list) -> pd.DataFrame:
  df = pd.DataFrame(rows, columns=COLUMNS)
  mean = {c: round(float(df[c].mean()), 2) for c in COLUMNS[1:]}
  return pd.concat([df, pd.DataFrame([{"Subject": "Mean", **mean}], columns=COLUMNS)], ignore_index=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)
  if args.freeze_legacy and args.cv != "legacy":
    parser.error("--freeze-legacy is only meaningful with --cv legacy")
  model = CANONICAL.get(args.model, args.model)
  spec: NetSpec = MODELS[args.model]
  cfg = load_config(args.config or ROOT / "configs" / "pipeline_config.yaml")
  processed = Path(args.data_root or ROOT / cfg["paths"]["data_processed_dir"])
  reports = output_dir(args.reports_dir or ROOT / "reports", args.cv)
  subjects = args.subjects or discover(processed)
  dev = resolve_device(args.device)
  if dev.type == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  t0 = time.time()
  hargs = argparse.Namespace(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, augment="on",
                            cv=args.cv, smoothing=args.smoothing)
  header = header_lines(spec, args.seed, dev.type, hargs)
  header = [h.replace("augment=on", "augment=OFF then ON (A/B, same folds and seeds)") for h in header]
  source = (f"Data source: legacy windows, {rel(processed, ROOT)}/<S>/ (P02, OO session), stimulus windows only; "
            f"subjects {', '.join(subjects)}")
  print(f"Augmentation A/B, model {model} [{dev.type}], cv {args.cv} ({'leaky, R1/PF-01' if args.cv == 'legacy' else 'trial-grouped, R1'}), "
        f"2.0 s rule {args.smoothing}")
  print(source)
  print("\n".join(header))
  rows, n_channels, approx = [], [], {}
  for s in subjects:
    try:
      g = gated_windows(processed, s)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    print(trial_line(s, g), flush=True)
    n_channels.append(f"{s}={len(g['kept'])}")
    approx[s] = g["trial_ids_approximate"]
    res = {}
    for arm in ("OFF", "ON"):
      t1 = time.time()
      print(f"  {s} augment {arm}", flush=True)
      res[arm] = train_and_eval_cv(g["X"], g["y"], spec.build, args.epochs, args.batch_size, args.lr, dev.type, args.seed,
                                   verbose=True, augment=arm == "ON", groups=g["trial_ids"], cv=args.cv,
                                   smoothing=args.smoothing)
      r = res[arm]
      print(f"[+] {s} {arm}: 1.0 s {100 * r['accuracy']:.2f}%  2.0 s smoothed {100 * r['smoothed_accuracy']:.2f}%  "
            f"train {100 * r['train_accuracy']:.2f}%  ({time.time() - t1:.0f} s)", flush=True)
    if 100 * res["OFF"]["train_accuracy"] < TRAIN_WARN_PCT:
      print(f"[!] WARNING {s}: OFF train accuracy {100 * res['OFF']['train_accuracy']:.2f}% < {TRAIN_WARN_PCT:g}%: "
            f"the network did not fit its own training fold (optimization problem, not overfitting; PF-30)")
    rows.append(ab_row(s, g["n_clean"], res["OFF"], res["ON"]))
  if not rows:
    print("[-] No subject evaluated")
    return 1
  df = with_mean(rows)
  csv = reports / f"augmentation_ab_{model}.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  meta = ("\n".join(header) + f"\n{source}\nn_channels (after the gate): {', '.join(n_channels)}\n"
          f"{approximate_line(subjects, approx)}\n{spec.model_line}\n"
          f"columns: Delta = ON - OFF (percentage points); Mean row = unweighted mean over subjects\n"
          f"labels: cv={args.cv} ({'legacy leaky, R1/PF-01, frozen P10 protocol' if args.cv == 'legacy' else 'trial-grouped, R1'}); "
          f"2.0 s rule={args.smoothing}; OFF and ON share one fold split per subject, seeds and initial weights (PF-28)\n")
  csv.with_suffix(".meta.txt").write_text(meta)
  print("\n" + df.to_string(index=False))
  print(f"\n{'Legacy leaky CV: not comparable with the leak-free numbers' if args.cv == 'legacy' else 'Trial-grouped CV'}; "
        f"runtime {time.time() - t0:.0f} s")
  print(f"Saved: {rel(csv, ROOT)}")
  if args.freeze_legacy:
    print(f"Frozen: {rel(csv, ROOT)} (--cv legacy writes under legacy_leaky/ directly)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
