"""DIAGNOSTIC (P11 results review, required step 1): training-seed spread of a network on the fixed seed-42 grouped folds.

Not a reported result. The reported P11 network numbers stay `reports/augmentation_ab_<model>.csv` (seed 42); this script
never writes those files and changes no default of the training path.

Data source: legacy folders <data-root>/<S>/ (P02, OO session, 7 channels), stimulus windows only, P07 two-tier gate and
pre-gate trial ids through `benchmark_common.gated_windows` (as the A/B benchmark). Folds: StratifiedGroupKFold(5, shuffle,
random_state=42) over the trial ids, the SAME folds for every seed base (the splitter seed stays 42). For each seed base b
only the model init (`torch.manual_seed(b + fold)`), the DataLoader generator (b + fold) and, in the ON arm, the
augmentation generator (b + fold) change; OFF and ON share the per-fold seeds within a base. Training through
`eegnet_cv.train_and_eval_cv(..., seed=42, model_seed=b)`: same convention as the A/B benchmark (150 epochs, AdamW,
cosine, label smoothing 0.05, per-window z-score). 2.0 s rule: the reported legacy-folder i%5 rule (`--smoothing mod5`).
Base 42 reproduces the A/B benchmark exactly.

Output: <reports-dir>/diagnostics/p11_seed_spread_<model>.csv (Subject, Seed base, Clean Windows, 1.0s OFF (%), 1.0s ON (%),
1.0s Delta, 2.0s OFF (%), 2.0s ON (%), 2.0s Delta, Train Acc OFF (%), Train Acc ON (%); a Mean row per base) + .meta.txt.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence


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

import pandas as pd  # noqa: E402
import torch  # noqa: E402

from scripts.benchmarks.neural_networks.benchmark_nn_augmentation import (  # noqa: E402
  CANONICAL, COLUMNS as AB_COLUMNS, MODELS, ab_row, discover)
from src.models.classical.benchmark_runner import load_config, protocol_labels  # noqa: E402
from src.models.cnn.benchmark_common import BATCH_SIZE, EPOCHS, LR, approximate_line, gated_windows, rel, trial_line  # noqa: E402
from src.models.cnn.eegnet_cv import train_and_eval_cv  # noqa: E402
from src.models.cnn.spatial_spectral_cnn import resolve_device  # noqa: E402

SPLIT_SEED = 42  # the folds of the reported run; never varied here
SMOOTHING = "mod5"
DIAG_DIR = "diagnostics"
LABEL = "DIAGNOSTIC (P11 seed spread; not a reported result)"
COLUMNS = ["Subject", "Seed base"] + AB_COLUMNS[1:]
MODEL_CHOICES = ("eegnet", "compact_cnn", "shallow_conv_net")


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--model", choices=MODEL_CHOICES, required=True)
  p.add_argument("--seed-bases", nargs="+", type=int, required=True, help="model/loader/augmentation seed bases, e.g. 1042 2042")
  p.add_argument("--epochs", type=int, default=EPOCHS)
  p.add_argument("--subjects", nargs="*", default=None, help="default: every S<k> folder found")
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="cpu")
  p.add_argument("--config", type=Path, default=None)
  p.add_argument("--data-root", "--processed-dir", dest="data_root", type=Path, default=None)
  p.add_argument("--reports-dir", type=Path, default=None, help="default <root>/reports; output goes to <reports-dir>/diagnostics/")
  return p


def output_path(reports_dir: Path, model: str) -> Path:
  return Path(reports_dir) / DIAG_DIR / f"p11_seed_spread_{model}.csv"


def run_subject(g: dict, spec, base: int, args, dev: str) -> dict:
  """OFF and ON arms of one subject on the seed-42 grouped folds with seed base `base`."""
  return {arm: train_and_eval_cv(g["X"], g["y"], spec.build, args.epochs, BATCH_SIZE, LR, dev, SPLIT_SEED,
                                 verbose=True, augment=arm == "ON", groups=g["trial_ids"], cv="grouped",
                                 smoothing=SMOOTHING, model_seed=base)
          for arm in ("OFF", "ON")}


def mean_row(rows: list, base: int) -> dict:
  df = pd.DataFrame(rows, columns=COLUMNS)
  return {"Subject": "Mean", "Seed base": base, **{c: round(float(df[c].mean()), 2) for c in COLUMNS[2:]}}


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  model = CANONICAL.get(args.model, args.model)
  spec = MODELS[args.model]
  cfg = load_config(args.config or ROOT / "configs" / "pipeline_config.yaml")
  processed = Path(args.data_root or ROOT / cfg["paths"]["data_processed_dir"])
  csv = output_path(args.reports_dir or ROOT / "reports", model)
  subjects = args.subjects or discover(processed)
  dev = resolve_device(args.device)
  if dev.type == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  cv_text, smooth_text = protocol_labels("grouped", SMOOTHING)
  header = [
    LABEL,
    f"model={model}; device={dev.type}; epochs={args.epochs}; batch={BATCH_SIZE}; lr={LR:g}",
    f"folds: {cv_text}; splitter random_state={SPLIT_SEED} fixed for every seed base (identical folds)",
    f"seed bases: {', '.join(str(b) for b in args.seed_bases)}; per fold: torch.manual_seed(base + fold), DataLoader "
    f"generator base + fold, augmentation generator base + fold (ON arm); OFF and ON share the per-fold seeds",
    f"smoothing: {smooth_text}",
    "reported P11 numbers: reports/augmentation_ab_<model>.csv (seed base 42); base 42 here reproduces them",
  ]
  source = (f"Data source: legacy windows, {rel(processed, ROOT)}/<S>/ (P02, OO session), stimulus windows only; "
            f"subjects {', '.join(subjects)}")
  print(f"[DIAGNOSTIC] network seed spread, model {model} [{dev.type}]")
  print(source)
  print("\n".join(header), flush=True)
  t0 = time.time()
  gated, approx = {}, {}
  for s in subjects:
    try:
      gated[s] = gated_windows(processed, s)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    approx[s] = gated[s]["trial_ids_approximate"]
    print(trial_line(s, gated[s]), flush=True)
  if not gated:
    print("[-] No subject evaluated")
    return 1
  out = []
  for base in args.seed_bases:
    rows = []
    for s, g in gated.items():
      t1 = time.time()
      print(f"  [DIAGNOSTIC] {s} seed base {base}", flush=True)
      res = run_subject(g, spec, base, args, dev.type)
      row = ab_row(s, g["n_clean"], res["OFF"], res["ON"])
      row = {"Subject": s, "Seed base": base, **{c: row[c] for c in AB_COLUMNS[1:]}}
      rows.append(row)
      print(f"[+] {s} base {base}: 1.0 s OFF {row['1.0s OFF (%)']:.2f}%  ON {row['1.0s ON (%)']:.2f}%  "
            f"2.0 s OFF {row['2.0s OFF (%)']:.2f}%  ON {row['2.0s ON (%)']:.2f}%  train OFF {row['Train Acc OFF (%)']:.2f}%  "
            f"ON {row['Train Acc ON (%)']:.2f}%  ({time.time() - t1:.0f} s)", flush=True)
    out += rows + [mean_row(rows, base)]
  df = pd.DataFrame(out, columns=COLUMNS)
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  csv.with_suffix(".meta.txt").write_text(
    "\n".join(header) + f"\n{source}\n{approximate_line(list(gated), approx)}\n{spec.model_line}\n"
    "columns: Delta = ON - OFF (percentage points); Mean row = unweighted mean over subjects of that seed base\n")
  print("\n" + df.to_string(index=False))
  print(f"\n[DIAGNOSTIC] not a reported result; runtime {time.time() - t0:.0f} s")
  print(f"Saved: {rel(csv, ROOT)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
