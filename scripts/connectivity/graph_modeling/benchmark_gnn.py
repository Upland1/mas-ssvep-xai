"""Within-subject edge-gated GNN of P15 (legacy Era B): variants nodes+F and nodes+coh+F (R-15).

Data source: cached graph datasets <data-root>/<S>/graph_dataset.npz (build_graph_dataset; legacy 7-channel folders,
stimulus windows only, two-tier P07 gate, FBCCA of the flagship, pre-gate trial ids; fs = 250 label PF-04; R3 legacy:
per-window features).
CV (R1, PF-03): StratifiedGroupKFold(5, shuffle, 42 + r) over the trial ids, repeat r = 0..R-1. Fold k of repeat r
seeds the model init, the dropout RNG (global torch seed set before the model) and the DataLoader generator with
1000*r + k (PF-28). Inputs are standardized with train-fold statistics only (R2). Training: AdamW lr 1e-3, wd 1e-2,
CosineAnnealingLR(eta_min 1e-5), CE label smoothing 0.05, batch 32, fixed epochs, no validation split, no
augmentation. 1.0 s = out-of-fold window accuracy; 2.0 s = legacy i%5 smoothing of the out-of-fold softmax in
clean-array order (R8 legacy-folder clause). Train accuracy (PF-30) = mean over folds, eval mode, un-augmented
training fold, after the last epoch.
The gate rows (P15.3) are printed next to the GNN rows when <reports-dir>/connectivity_gate_benchmark.csv exists.
Output: <reports-dir>/gnn_benchmark.csv (variant, repeat, acc_1s, acc_2s, train_acc, subject; percent) + .meta.txt.
`--smoke-test`: 3 epochs, 1 repeat, first subject (or an in-memory synthetic dataset when no cache exists); writes
gnn_benchmark_smoke.csv, never gnn_benchmark.csv.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _find_root() -> Path:
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[3]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from torch import nn  # noqa: E402
from torch.utils.data import DataLoader, TensorDataset  # noqa: E402

from src.features.connectivity.graph_dataset import GraphDataset, discover_graph_subjects, load_graph_dataset  # noqa: E402
from src.features.connectivity.graph_inputs import build_inputs, parse_variant, standardize_fold  # noqa: E402
from src.models.classical.legacy_eval import SEED, accuracies  # noqa: E402
from src.models.cnn.eegnet_cv import BATCH_SIZE, EPOCHS, ETA_MIN, LABEL_SMOOTHING, LR, WEIGHT_DECAY  # noqa: E402
from src.models.cnn.spatial_spectral_cnn import resolve_device  # noqa: E402
from src.models.graph.connectivity_gnn import ConnectivityGNN, count_parameters  # noqa: E402
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials, make_splits  # noqa: E402

VARIANTS = ("nodes+F", "nodes+coh+F")
COLUMNS = ["variant", "repeat", "acc_1s", "acc_2s", "train_acc", "subject"]
SMOKE_EPOCHS = 3
GAP_OVERFIT_PP = 15.0     # train - test above this: generalization problem (PF-30)
UNDERFIT_TRAIN = 70.0     # train accuracy below this: optimization problem
GATE_SETS = ("N", "F", "Base", "Base+Ec")


def make_model(inputs, n_classes: int = 5, dropout: float = 0.3) -> ConnectivityGNN:
  """Network sized for `inputs` (a `GraphInputs`)."""
  return ConnectivityGNN(inputs.node.shape[1], inputs.node.shape[2], 0 if inputs.edge is None else inputs.edge.shape[-1],
                         0 if inputs.graph is None else inputs.graph.shape[-1], n_classes, dropout=dropout)


def _tensors(inp, device):
  return (torch.from_numpy(inp.node).to(device), None if inp.edge is None else torch.from_numpy(inp.edge).to(device),
          None if inp.graph is None else torch.from_numpy(inp.graph).to(device))


def predict_proba(model: nn.Module, inp, device, chunk: int = 256) -> np.ndarray:
  model.eval()
  x, e, g = _tensors(inp, device)
  out = []
  with torch.no_grad():
    for i in range(0, len(x), chunk):
      out.append(torch.softmax(model(x[i:i + chunk], None if e is None else e[i:i + chunk],
                                    None if g is None else g[i:i + chunk]), dim=1).cpu().numpy())
  return np.concatenate(out)


def train_fold(train_inp, yi: np.ndarray, seed: int, device, epochs: int = EPOCHS, batch_size: int = BATCH_SIZE,
               lr: float = LR) -> nn.Module:
  """Train one network on a standardized training fold; `torch.manual_seed(seed)` precedes the model (init and
  dropout RNG) and seeds the DataLoader generator (PF-28)."""
  torch.manual_seed(seed)
  model = make_model(train_inp).to(device)
  opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
  sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=ETA_MIN)
  crit = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
  x, e, g = _tensors(train_inp, device)
  y = torch.from_numpy(yi.astype(np.int64)).to(device)
  idx = torch.arange(len(y))
  gen = torch.Generator().manual_seed(seed)
  loader = DataLoader(TensorDataset(idx), batch_size=batch_size, shuffle=True, generator=gen)
  for _ in range(epochs):
    model.train()
    for (b,) in loader:
      b = b.to(device)
      opt.zero_grad()
      loss = crit(model(x[b], None if e is None else e[b], None if g is None else g[b]), y[b])
      loss.backward()
      opt.step()
    sched.step()
  return model


def evaluate_variant(ds, variant: str, repeat: int, epochs: int, device, seed: int = SEED, batch_size: int = BATCH_SIZE,
                     lr: float = LR) -> dict:
  """One repeat (splitter seed + r; fold seeds 1000 r + k): percent `acc_1s`, `acc_2s`, `train_acc` + `n_params`."""
  parse_variant(variant)
  inputs = build_inputs(ds, variant)
  yi = ds.y_index
  splits = make_splits("grouped", ds.y, ds.trial_ids, seed + repeat)
  assert_no_shared_trials(splits, ds.trial_ids)
  scores = np.zeros((len(yi), 5))
  pred = np.zeros(len(yi), dtype=int)
  train_accs = []
  n_params = 0
  for k, (tr, te) in enumerate(splits):
    tr_inp, te_inp = standardize_fold(inputs, tr, te)
    model = train_fold(tr_inp, yi[tr], 1000 * repeat + k, device, epochs, batch_size, lr)
    n_params = count_parameters(model)
    p = predict_proba(model, te_inp, device)
    scores[te] = p
    pred[te] = p.argmax(1)
    train_accs.append(float((predict_proba(model, tr_inp, device).argmax(1) == yi[tr]).mean()))
  a1, a2 = accuracies(ds.y, np.asarray(ds.classes)[pred], scores, ds.trial_ids, "mod5")
  return {"variant": variant, "repeat": repeat, "acc_1s": round(100 * a1, 4), "acc_2s": round(100 * a2, 4),
          "train_acc": round(100 * float(np.mean(train_accs)), 4), "subject": ds.subject, "n_params": n_params}


def diagnosis(train: float, test: float) -> str:
  """PF-30 hint from mean train and 1.0 s test accuracy (percent)."""
  if train < UNDERFIT_TRAIN:
    return "UNDERFITTING (low train accuracy: optimization problem; more epochs, larger lr or capacity)"
  if train - test > GAP_OVERFIT_PP:
    return "OVERFITTING (high train, low test: generalization problem; regularize, fewer inputs)"
  return "no strong gap"


def synthetic_dataset(seed: int = 0, n_trials: int = 20, C: int = 7) -> GraphDataset:
  """In-memory stand-in for the smoke test: the class is planted in the node features."""
  rng = np.random.default_rng(seed)
  n = n_trials * 5
  y = np.repeat(np.arange(101, 106), n // 5)
  node = rng.normal(size=(n, C, 10)) + 0.8 * (y[:, None, None] - 103)
  return GraphDataset("Ssynth", node, rng.uniform(0, 1, (n, C, C, 5)), rng.normal(size=(n, C, C, 5, 2)),
                      rng.uniform(0, 1, (n, 5)), y, np.arange(n) // 5, [f"c{i}" for i in range(C)], [], 250.0, "synthetic", False)


def gate_rows(reports: Path, subject: str) -> Optional[str]:
  """One printed line of the gate CSV for `subject` (k = 0, mean over repeats), or None when the CSV is absent."""
  p = Path(reports) / "connectivity_gate_benchmark.csv"
  if not p.is_file():
    return None
  df = pd.read_csv(p)
  d = df[(df.subject == subject) & (df.k_select == 0) & (df.set.isin(GATE_SETS))]
  if d.empty:
    return None
  m = d.groupby("set")[["acc_1s", "acc_2s"]].mean()
  return "; ".join(f"{s} {m.loc[s, 'acc_1s']:.1f}/{m.loc[s, 'acc_2s']:.1f}" for s in GATE_SETS if s in m.index)


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="default: subjects with a graph_dataset.npz")
  p.add_argument("--variants", nargs="+", default=list(VARIANTS), help=f"default {' '.join(VARIANTS)}")
  p.add_argument("--repeats", type=int, default=3, help="CV repeats, splitter seeds 42 + r (default 3)")
  p.add_argument("--epochs", type=int, default=EPOCHS)
  p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
  p.add_argument("--lr", type=float, default=LR)
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="cpu", help="default cpu (comparisons on one device)")
  p.add_argument("--seed", type=int, default=SEED, help=f"splitter base seed (default {SEED})")
  p.add_argument("--smoke-test", action="store_true", help=f"{SMOKE_EPOCHS} epochs, 1 repeat, first subject")
  p.add_argument("--data-root", type=Path, default=None, help="default data/processed")
  p.add_argument("--reports-dir", type=Path, default=None, help="default <root>/reports")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  for v in args.variants:
    parse_variant(v)
  processed = Path(args.data_root or ROOT / "data" / "processed")
  reports = Path(args.reports_dir or ROOT / "reports")
  dev = resolve_device(args.device)
  if dev.type == "cuda":
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  epochs, repeats = (SMOKE_EPOCHS, 1) if args.smoke_test else (args.epochs, args.repeats)
  subjects = args.subjects or discover_graph_subjects(processed)
  datasets = []
  if subjects:
    datasets = [load_graph_dataset(s, processed) for s in (subjects[:1] if args.smoke_test else subjects)]
    source = f"graph datasets {processed}/<S>/graph_dataset.npz (legacy windows, stimulus only, two-tier gate)"
  elif args.smoke_test:
    datasets = [synthetic_dataset()]
    source = "in-memory SYNTHETIC dataset (no cache found); not data"
  else:
    print(f"[-] No graph_dataset.npz under {processed}; run build_graph_dataset first")
    return 1
  t0 = time.time()
  header = [
    f"SMOKE TEST: {epochs} epochs, {repeats} repeat; numbers are not results" if args.smoke_test else "full run",
    f"Data source: {source}; fs=250 legacy (PF-04), R3 legacy per-window features",
    f"device={dev.type}; cv=StratifiedGroupKFold(5, shuffle, {args.seed}+r) over pre-gate trial ids, r=0..{repeats - 1} (R1, PF-03)",
    "seeds: model init, dropout and DataLoader generator = 1000*r + fold (PF-28)",
    "smoothing: legacy i%5 of the out-of-fold softmax in clean-array order (R8 legacy-folder clause)",
    f"training: epochs={epochs} (fixed, no validation split, no augmentation), batch={args.batch_size}, AdamW lr={args.lr:g} "
    f"wd={WEIGHT_DECAY:g}, CosineAnnealingLR eta_min={ETA_MIN:g}, CE label_smoothing={LABEL_SMOOTHING:g}; "
    "standardizer fitted on the training fold only (R2)",
    "train accuracy: mean over folds, eval mode, un-augmented training fold (PF-30)",
  ]
  print("\n".join(header))
  rows, params = [], {}
  for ds in datasets:
    print(f"\n{ds.subject}: {len(ds)} windows, {len(np.unique(ds.trial_ids))} trials, channels {' '.join(ds.channels_kept)}, "
          f"trial_ids_approximate={ds.trial_ids_approximate}", flush=True)
    for v in args.variants:
      t1 = time.time()
      for r in range(repeats):
        res = evaluate_variant(ds, v, r, epochs, dev, args.seed, args.batch_size, args.lr)
        params[v] = res.pop("n_params")
        rows.append(res)
        print(f"  {v} r={r}: 1.0 s {res['acc_1s']:.2f}  2.0 s {res['acc_2s']:.2f}  train {res['train_acc']:.2f}  "
              f"({time.time() - t1:.0f} s)", flush=True)
    g = gate_rows(reports, ds.subject)
    if g:
      print(f"  gate rows (LDA, k=0, 1.0 s/2.0 s, mean of repeats): {g}")
  df = pd.DataFrame(rows, columns=COLUMNS)
  out = reports / ("gnn_benchmark_smoke.csv" if args.smoke_test else "gnn_benchmark.csv")
  out.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(out, index=False)
  summ = df.groupby(["subject", "variant"])[["acc_1s", "acc_2s", "train_acc"]].mean()
  print("\nMean over repeats (percent)")
  print(summ.round(2).to_string())
  print("\nTrain-accuracy diagnostic (PF-30)")
  diag = []
  for (s, v), row in summ.iterrows():
    line = f"{s} {v}: train {row.train_acc:.1f} vs test {row.acc_1s:.1f} (gap {row.train_acc - row.acc_1s:+.1f}) -> {diagnosis(row.train_acc, row.acc_1s)}"
    diag.append(line)
    print(line)
  lines = header + [f"params: " + ", ".join(f"{v}={n}" for v, n in params.items()), "", summ.round(2).to_string(), ""] + diag
  out.with_suffix(".meta.txt").write_text("\n".join(lines) + "\n")
  print(f"\nSaved: {out}; runtime {time.time() - t0:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
