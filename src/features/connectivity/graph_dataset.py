"""Cache of the P15 per-window graph dataset: `<processed>/<S>/graph_dataset.npz` (a NEW file; the legacy
arrays of the folder are never touched).

Contents (stimulus windows 101-105 that pass the two-tier P07 gate, clean-array order):
`node (n, C, 10)`, `edge_coh (n, C, C, 5)`, `edge_phase (n, C, C, 5, 2)`, `X_fbcca (n, 5)`, `y (n,)` (codes
101-105), `trial_ids (n,)` (built on the PRE-gate labels, then masked, PF-03), `channels_kept (C,)` and the
provenance `fs`, `code_hash`, `trial_ids_approximate`, `channels_dropped`.

Loader API for consumers (the GNN builder):
    ds = load_graph_dataset("S03")              # default data/processed; `processed_dir=` overrides
    ds.node, ds.edge_coh, ds.edge_phase, ds.X_fbcca, ds.y, ds.trial_ids, ds.channels_kept
    ds.classes -> (101, ..., 105); ds.y_index -> y mapped to 0..4
The loader raises `FileNotFoundError` if the cache is missing and `StaleGraphDataset` if the stored
`code_hash` differs from the current feature code (rebuild with `build_graph_dataset --rebuild`).
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

import src.features.connectivity.connectivity_graph_features as _cgf
from src.features.ssvep.window_mask import CHANNEL_FAIL_FRACTION, GATE_THRESHOLDS

CACHE_NAME = "graph_dataset.npz"
CLASS_CODES = (101, 102, 103, 104, 105)
ARRAY_KEYS = ("node", "edge_coh", "edge_phase", "X_fbcca", "y", "trial_ids", "channels_kept")
_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROCESSED = _ROOT / "data" / "processed"


class StaleGraphDataset(RuntimeError):
  """The cache was built by different feature code or parameters than the current ones."""


def code_fingerprint(fs: float, thresholds: Optional[dict] = None,
                     channel_fail_fraction: float = CHANNEL_FAIL_FRACTION) -> str:
  """sha256 of the graph-feature source file plus the build parameters (stale-cache guard)."""
  th = dict(GATE_THRESHOLDS if thresholds is None else thresholds)
  h = hashlib.sha256(Path(_cgf.__file__).read_bytes())
  h.update(repr((float(fs), sorted(th.items()), float(channel_fail_fraction))).encode())
  return h.hexdigest()


@dataclass
class GraphDataset:
  """One subject's cached graph dataset (see the module docstring)."""
  subject: str
  node: np.ndarray
  edge_coh: np.ndarray
  edge_phase: np.ndarray
  X_fbcca: np.ndarray
  y: np.ndarray
  trial_ids: np.ndarray
  channels_kept: list
  channels_dropped: list
  fs: float
  code_hash: str
  trial_ids_approximate: bool

  classes = CLASS_CODES

  @property
  def y_index(self) -> np.ndarray:
    """`y` as class indices 0..4 (position in `CLASS_CODES`)."""
    return np.searchsorted(np.asarray(CLASS_CODES), self.y)

  def __len__(self) -> int:
    return len(self.y)


def cache_path(subject: str, processed_dir: Optional[Path] = None) -> Path:
  return Path(processed_dir or DEFAULT_PROCESSED) / subject / CACHE_NAME


def save_graph_dataset(path: Path, arrays: dict, fs: float, code_hash: str, channels_dropped: Sequence[str],
                       trial_ids_approximate: bool) -> Path:
  """Write the npz (only a new file; refuses to overwrite anything that is not a graph_dataset.npz)."""
  path = Path(path)
  if path.name != CACHE_NAME:
    raise ValueError(f"cache file must be named {CACHE_NAME}, got {path.name}")
  missing = [k for k in ARRAY_KEYS if k not in arrays]
  if missing:
    raise ValueError(f"missing arrays {missing}")
  np.savez(path, **{k: np.asarray(arrays[k]) for k in ARRAY_KEYS}, fs=np.float64(fs),
           code_hash=np.array(code_hash), channels_dropped=np.array(list(channels_dropped), dtype=str),
           trial_ids_approximate=np.bool_(trial_ids_approximate))
  return path


def load_graph_dataset(subject: str, processed_dir: Optional[Path] = None, check_hash: bool = True) -> GraphDataset:
  """Load `<processed_dir>/<subject>/graph_dataset.npz` (default `data/processed`)."""
  p = cache_path(subject, processed_dir)
  if not p.is_file():
    raise FileNotFoundError(f"{p} missing; run `python -m scripts.connectivity.graph_modeling.build_graph_dataset`")
  with np.load(p, allow_pickle=False) as z:
    d = {k: z[k] for k in z.files}
  if check_hash:
    now = code_fingerprint(float(d["fs"]))
    if str(d["code_hash"]) != now:
      raise StaleGraphDataset(f"{p} was built by other feature code; rebuild with --rebuild")
  return GraphDataset(subject=subject, node=d["node"], edge_coh=d["edge_coh"], edge_phase=d["edge_phase"],
                      X_fbcca=d["X_fbcca"], y=d["y"], trial_ids=d["trial_ids"],
                      channels_kept=[str(c) for c in d["channels_kept"]],
                      channels_dropped=[str(c) for c in d["channels_dropped"]], fs=float(d["fs"]),
                      code_hash=str(d["code_hash"]), trial_ids_approximate=bool(d["trial_ids_approximate"]))


def discover_graph_subjects(processed_dir: Optional[Path] = None) -> list:
  """Subject folders (S<digits>, numeric order) that hold a `graph_dataset.npz`."""
  root = Path(processed_dir or DEFAULT_PROCESSED)
  found = [p.name for p in root.iterdir() if p.is_dir() and p.name[:1] == "S" and p.name[1:].isdigit()
           and (p / CACHE_NAME).is_file()] if root.is_dir() else []
  return sorted(found, key=lambda s: int(s[1:]))
