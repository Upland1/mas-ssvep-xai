"""Build the per-subject graph dataset cache of P15 (legacy Era B; R3 and PF-04 labelled).

Data source: legacy folders <data-root>/<S>/ (P02, OO session, 7 channels), stimulus windows 101-105 only.
Per subject, through the flagship path (`prepare_subject`): the two-tier P07 gate once (vpp 5-120 uV,
std 1-35 uV, channel dropped if it fails in > 50 % of the windows; R5 per-script, every threshold explicit),
FBCCA on the kept channels (as the flagship), trial ids built on the PRE-gate labels and masked (PF-03,
R1). Graph features (node power, coherence, phase) are computed on the gated raw windows of the kept
channels at the legacy feature axis fs = 250 (PF-04). Output: <data-root>/<S>/graph_dataset.npz (a NEW
file; the legacy arrays are never opened for writing) and <reports-dir>/graph_dataset_sanity.csv:
per subject and target, own-band minus other-class differences of node power (fundamental, 2nd harmonic),
coherence and phase consistency (mean resultant length of the unit phasors over windows and edges: own
class vs the mean of the other four classes).

An existing cache is reused unless `--rebuild` is given or its code hash differs from the current code.
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

from src.features.connectivity.connectivity_graph_features import build_graph_features  # noqa: E402
from src.features.connectivity.graph_dataset import (  # noqa: E402
  CACHE_NAME, CLASS_CODES, GraphDataset, StaleGraphDataset, cache_path, code_fingerprint, load_graph_dataset,
  save_graph_dataset)
from src.features.ssvep.spectral_power import LEGACY_FS_HZ, select_channels_by_name  # noqa: E402
from src.models.classical.benchmark_runner import discover_subjects, load_config, prepare_subject  # noqa: E402
from src.preprocessing.dataset.legacy_windows import load_stimulus_windows  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
SANITY_COLUMNS = ["subject", "target_hz", "n_own", "node_f1_diff", "node_f2_diff", "coh_diff",
                  "phase_consistency_own", "phase_consistency_other", "phase_consistency_diff"]
TARGETS = (24.0, 20.0, 15.0, 10.9091, 8.5714)


def build_subject(processed: Path, subject: str, fs: float = LEGACY_FS_HZ) -> tuple:
  """`(arrays dict, blocks)` of one subject: gate + FBCCA via `prepare_subject`, graph features on the gated raw windows."""
  b = prepare_subject(processed, subject, None, fs, verbose=False)
  _, X_time, _ = load_stimulus_windows(processed, subject)
  mask = np.asarray(b["mask"]).astype(bool)
  idx = select_channels_by_name(b["channel_names"], b["channels_kept"], X_time.shape[1])
  Xg = X_time[mask][:, idx]
  g = build_graph_features(Xg, fs)
  arrays = dict(g, X_fbcca=b["fbcca"], y=b["y"], trial_ids=b["trial_ids"], channels_kept=np.array(b["channels_kept"], dtype=str))
  n = len(b["y"])
  if not all(len(arrays[k]) == n for k in ("node", "edge_coh", "edge_phase", "X_fbcca", "trial_ids")):
    raise RuntimeError(f"{subject}: graph blocks misaligned")
  return arrays, b


def _resultant(ph: np.ndarray) -> float:
  """Mean over edges of the resultant length over windows of unit phasors `ph (n, E, 2)`."""
  z = ph[..., 0] + 1j * ph[..., 1]
  return float(np.abs(z.mean(axis=0)).mean())


def sanity_rows(ds: GraphDataset) -> list:
  """Own-band minus other-class differences per target (node power, coherence, phase consistency)."""
  C = ds.node.shape[1]
  iu, ju = np.triu_indices(C, 1)
  rows = []
  for k, code in enumerate(CLASS_CODES):
    own = ds.y == code
    oth = ~own
    row = {"subject": ds.subject, "target_hz": TARGETS[k], "n_own": int(own.sum())}
    for h, name in ((0, "node_f1_diff"), (1, "node_f2_diff")):
      col = h * 5 + k
      row[name] = float(ds.node[own][:, :, col].mean() - ds.node[oth][:, :, col].mean())
    row["coh_diff"] = float(ds.edge_coh[own][:, iu, ju, k].mean() - ds.edge_coh[oth][:, iu, ju, k].mean())
    ph = ds.edge_phase[:, iu, ju, k]
    row["phase_consistency_own"] = _resultant(ph[own])
    row["phase_consistency_other"] = float(np.mean([_resultant(ph[ds.y == c]) for c in CLASS_CODES if c != code]))
    row["phase_consistency_diff"] = row["phase_consistency_own"] - row["phase_consistency_other"]
    rows.append(row)
  return rows


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="default: discover S<digits> folders")
  p.add_argument("--data-root", type=Path, default=None, help="folder with <S>/ arrays (default data/processed)")
  p.add_argument("--reports-dir", type=Path, default=None, help="default <root>/reports")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature axis (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--rebuild", action="store_true", help="recompute even if a valid cache exists")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  cfg = load_config(args.config)
  processed = Path(args.data_root or ROOT / cfg["paths"]["data_processed_dir"])
  reports = Path(args.reports_dir or ROOT / "reports")
  if not processed.is_dir():
    print(f"[x] Data root not found: {processed}")
    return 1
  subjects = args.subjects or discover_subjects(processed)
  if not subjects:
    print("[-] No subject folders with arrays")
    return 1
  t0 = time.time()
  print(f"Data source: legacy windows {processed}/<S>/ (P02, OO session), stimulus windows only, two-tier gate (P07); "
        f"feature axis fs={args.fs:g} (legacy PF-04); R3 legacy: per-window features on raw windows")
  rows = []
  for s in subjects:
    t1 = time.time()
    h = code_fingerprint(args.fs)
    if not args.rebuild and cache_path(s, processed).is_file():
      try:
        ds = load_graph_dataset(s, processed)
        print(f"[=] {s}: cache valid ({len(ds)} windows)")
        rows += sanity_rows(ds)
        continue
      except StaleGraphDataset:
        print(f"[!] {s}: stale cache, rebuilding")
    arrays, b = build_subject(processed, s, args.fs)
    save_graph_dataset(cache_path(s, processed), arrays, args.fs, h, b["channels_dropped"], b["trial_ids_approximate"])
    ds = load_graph_dataset(s, processed)
    print(f"[+] {s}: {b['n_stimulus']} stimulus, {len(ds)} clean, {b['n_rejected']} rejected; kept {' '.join(ds.channels_kept)}; "
          f"dropped {' '.join(ds.channels_dropped) or 'none'}; trials {len(np.unique(ds.trial_ids))}; "
          f"trial_ids_approximate={ds.trial_ids_approximate}; node {ds.node.shape} edge_coh {ds.edge_coh.shape} "
          f"edge_phase {ds.edge_phase.shape}; {time.time() - t1:.0f} s -> {cache_path(s, processed)}")
    rows += sanity_rows(ds)
  df = pd.DataFrame(rows, columns=SANITY_COLUMNS)
  out = reports / "graph_dataset_sanity.csv"
  out.parent.mkdir(parents=True, exist_ok=True)
  df.round(5).to_csv(out, index=False)
  print("\n" + df.round(4).to_string(index=False))
  print(f"\nSaved: {out}; runtime {time.time() - t0:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
