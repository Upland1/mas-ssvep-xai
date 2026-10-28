"""Freeze the Era A/B outputs as a read-only baseline snapshot (P16.1, plan settled points 1-2).

Copies `data/processed`, `reports`, `outputs/reports` and `configs` into
`baselines/<tag>_<date>/` (same relative paths), sets every file and folder read-only, and writes

- `MANIFEST.json`: git commit, dirty flag, python, platform, pip freeze, the per-subject channel audit
  of `data/processed`, and sha256 / bytes / shape / rows of every file, keyed by its repository path
  (so the list can be compared with `sha256sum` of the live tree before the phase);
- `baseline_summary.csv`: long format `pipeline, subject, metric, value` with `MEAN` rows, from the
  n-subject benchmark, the augmentation A/B, GNN, connectivity-gate and connectivity-cohort CSVs;
- `superseded/`: the pre-leak reports (`five_subjects_benchmark.csv` and its meta file), stored there
  instead of under `reports/` (their MANIFEST rows keep the repository path and a `stored_as` field).

`configs/` is copied from git at the pre-phase commit (`--configs-git-rev`, default the merge-base of HEAD
and `main`), because the config moves to its final version in P16 and the snapshot must hold v1; the
MANIFEST records the commit it came from. A second run with the same tag refuses (exit 1) and changes
nothing. Run it before any other output of the phase is written. Data source: legacy folders and the
reports as they stand.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else two levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[1]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

TREES = ("data/processed", "reports", "outputs/reports", "configs")
SUPERSEDED = ("reports/five_subjects_benchmark.csv", "reports/five_subjects_benchmark.meta.txt")
SUPERSEDED_DIR = "superseded"
CONFIG_REL = "configs/pipeline_config.yaml"
SUMMARY_COLUMNS = ["pipeline", "subject", "metric", "value"]


# --- git helpers ---------------------------------------------------------------

def git(root: Path, *args: str, check: bool = True) -> str:
  """Stdout of `git -C root args` (stripped); RuntimeError on failure when `check`."""
  r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
  if check and r.returncode != 0:
    raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
  return r.stdout.strip()


def git_state(root: Path) -> dict:
  """`{commit, dirty}` of the working tree (dirty = any tracked file modified; untracked ignored)."""
  commit = git(root, "rev-parse", "HEAD", check=False) or "unknown"
  dirty = bool(git(root, "status", "--porcelain", "--untracked-files=no", check=False))
  return {"commit": commit, "dirty": dirty}


def resolve_configs_rev(root: Path, rev: Optional[str]) -> Optional[str]:
  """Commit the config is taken from: `rev`, else the merge-base of HEAD and `main`; None if neither resolves."""
  if rev:
    return git(root, "rev-parse", "--verify", f"{rev}^{{commit}}")
  base = git(root, "merge-base", "HEAD", "main", check=False)
  return base or None


# --- files ---------------------------------------------------------------------

def sha256_file(path: Path) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def file_info(path: Path) -> dict:
  """`{bytes, sha256, shape?, rows?}`: array shape for .npy, per-array shapes for .npz, data rows for .csv."""
  info = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
  suffix = path.suffix.lower()
  try:
    if suffix == ".npy":
      info["shape"] = list(np.load(path, mmap_mode="r").shape)
    elif suffix == ".npz":
      with np.load(path) as z:
        info["shape"] = {k: list(z[k].shape) for k in z.files}
    elif suffix == ".csv":
      with open(path, newline="") as f:
        info["rows"] = max(sum(1 for _ in f) - 1, 0)
  except (OSError, ValueError) as exc:   # unreadable array: recorded, not fatal
    info["note"] = f"{type(exc).__name__}: {exc}"
  return info


def list_files(root: Path, tree: str) -> list:
  """Repository-relative posix paths of every file under `root/tree`, sorted."""
  base = root / tree
  if not base.exists():
    return []
  return sorted(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())


def make_read_only(path: Path) -> None:
  """Remove every write bit under `path` (files first, then folders, so the walk still works)."""
  dirs = []
  for p in sorted(path.rglob("*")):
    if p.is_dir():
      dirs.append(p)
    else:
      p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
  for d in dirs + [path]:
    d.chmod(d.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def channel_audit(root: Path, processed: str = "data/processed") -> dict:
  """Per subject folder of `processed`: channel count of `X_time_windows.npy`, window count, saved names if any."""
  out = {}
  base = root / processed
  if not base.is_dir():
    return out
  for d in sorted(p for p in base.iterdir() if p.is_dir()):
    f = d / "X_time_windows.npy"
    if not f.is_file():
      continue
    shape = np.load(f, mmap_mode="r").shape
    names = None
    cj = d / "channels.json"
    if cj.is_file():
      names = json.loads(cj.read_text()).get("kept")
    out[d.name] = {"n_windows": int(shape[0]), "n_channels": int(shape[1]), "channel_names": names,
                   "layout": "channels.json" if names else "none (legacy 7-channel arrays, PO7 excluded)"
                   if shape[1] == 7 else "none"}
  return out


# --- baseline_summary.csv -------------------------------------------------------

def _num(v) -> Optional[float]:
  try:
    x = float(v)
  except (TypeError, ValueError):
    return None
  return x if np.isfinite(x) else None


LEGACY_MEAN_ROW_TAGS = ("v1",)   # tags frozen with the CSV "Mean" row kept as a subject (C-1); later tags skip it


def summary_rows(snapshot: Path, skip_mean_row: bool = False) -> list:
  """Long-format rows `(pipeline, subject, metric, value)` from the CSVs inside the snapshot, plus MEAN rows.

  Flagship: n_subjects_benchmark; augmentation: augmentation_ab_<model>; GNN: gnn_benchmark (mean over
  repeats per subject and variant); gate: connectivity_gate_benchmark (mean over repeats per subject, set,
  k_select); connectivity: connectivity_cohort_summary (per method, condition: obs_diff and n_edges_sig_fdr).
  A missing CSV is skipped. `MEAN` = mean over subjects of each (pipeline, metric) (NaN values ignored).
  `skip_mean_row=True` (C-1) drops the CSV's own `Mean` row, which is redundant with `MEAN` and was averaged in
  as a subject by the v1 freeze; v1 keeps its frozen behaviour (`LEGACY_MEAN_ROW_TAGS`).
  """
  import pandas as pd
  rep = snapshot / "reports"
  rows = []

  def add(pipeline, subject, metric, value):
    v = _num(value)
    if skip_mean_row and str(subject) == "Mean":
      return
    if v is not None:
      rows.append((pipeline, str(subject), str(metric), v))

  f = rep / "n_subjects_benchmark.csv"
  if f.is_file():
    for r in pd.read_csv(f).to_dict("records"):
      for m in ("Clean Windows", "Rejected Windows", "1.0s Acc (%)", "2.0s Smoothed (%)"):
        if m in r:
          add("flagship_n_subjects", r["Subject"], m, r[m])
  for f in sorted(rep.glob("augmentation_ab_*.csv")):
    model = f.stem[len("augmentation_ab_"):]
    for r in pd.read_csv(f).to_dict("records"):
      for m, v in r.items():
        if m != "Subject":
          add(f"augmentation_{model}", r["Subject"], m, v)
  f = rep / "gnn_benchmark.csv"
  if f.is_file():
    d = pd.read_csv(f).groupby(["variant", "subject"], sort=False)[["acc_1s", "acc_2s", "train_acc"]].mean()
    for (variant, subject), r in d.iterrows():
      for m in d.columns:
        add(f"gnn_{variant}", subject, f"{m}_mean_over_repeats", r[m])
  f = rep / "connectivity_gate_benchmark.csv"
  if f.is_file():
    d = pd.read_csv(f).groupby(["set", "k_select", "subject"], sort=False)[["acc_1s", "acc_2s"]].mean()
    for (s, k, subject), r in d.iterrows():
      for m in d.columns:
        add(f"gate_{s}_k{int(k)}", subject, f"{m}_mean_over_repeats", r[m])
  f = rep / "connectivity_cohort_summary.csv"
  if f.is_file():
    for r in pd.read_csv(f).to_dict("records"):
      tag = f"{int(r['condition'])}@{r['frequency_hz']:g}Hz"
      for m in ("obs_diff", "n_edges_sig_fdr"):
        add(f"connectivity_{r['method']}", r["subject"], f"{m}[{tag}]", r[m])
  means: dict = {}
  for p, s, m, v in rows:
    if s != "MEAN":
      means.setdefault((p, m), []).append(v)
  rows += [(p, "MEAN", m, float(np.mean(v))) for (p, m), v in means.items()]
  return rows


def write_summary(rows: Sequence, path: Path) -> None:
  with open(path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(SUMMARY_COLUMNS)
    w.writerows(rows)


# --- freeze --------------------------------------------------------------------

def snapshot_dir(root: Path, tag: str, date: str, out_base: str = "baselines") -> Path:
  return root / out_base / f"{tag}_{date}"


def existing_snapshots(root: Path, tag: str, out_base: str = "baselines") -> list:
  """Folders `<out_base>/<tag>_*` already present (a tag is frozen once, whatever the date)."""
  base = root / out_base
  return sorted(base.glob(f"{tag}_*")) if base.is_dir() else []


def pip_freeze() -> list:
  r = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
  return r.stdout.splitlines() if r.returncode == 0 else [f"pip freeze unavailable: {r.stderr.strip()[:200]}"]


def freeze(root: Path, tag: str, note: str, date: Optional[str] = None, out_base: str = "baselines",
           configs_rev: Optional[str] = None, trees: Sequence[str] = TREES,
           superseded: Sequence[str] = SUPERSEDED, with_pip: bool = True) -> Path:
  """Write the snapshot and return its folder. Raises FileExistsError if the tag was frozen before.

  Order: refuse -> copy trees (configs from git at the pre-phase commit when it resolves) -> move the
  superseded reports -> summary and MANIFEST -> read-only.
  """
  root = Path(root)
  old = existing_snapshots(root, tag, out_base)
  if old:
    raise FileExistsError(f"tag {tag!r} already frozen: {', '.join(str(p.relative_to(root)) for p in old)}")
  date = date or dt.date.today().isoformat()
  snap = snapshot_dir(root, tag, date, out_base)
  state = git_state(root)
  cfg_commit = resolve_configs_rev(root, configs_rev) if (root / ".git").exists() else None
  files = []   # (repo path, stored path inside the snapshot)
  snap.mkdir(parents=True)
  try:
    for tree in trees:
      for rel in list_files(root, tree):
        dest_rel = f"{SUPERSEDED_DIR}/{Path(rel).name}" if rel in superseded else rel
        dest = snap / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if rel == CONFIG_REL and cfg_commit:
          dest.write_bytes(subprocess.run(["git", "-C", str(root), "show", f"{cfg_commit}:{rel}"],
                                          capture_output=True, check=True).stdout)   # exact blob bytes
        else:
          shutil.copy2(root / rel, dest)
        files.append((rel, dest_rel))
    entries = []
    for rel, dest_rel in files:
      e = {"path": rel, **file_info(snap / dest_rel)}
      if dest_rel != rel:
        e["stored_as"] = dest_rel
      if rel == CONFIG_REL:
        e["from_git_commit"] = cfg_commit or "working tree"
      entries.append(e)
    rows = summary_rows(snap, skip_mean_row=tag not in LEGACY_MEAN_ROW_TAGS)
    write_summary(rows, snap / "baseline_summary.csv")
    manifest = {
      "tag": tag, "date": date, "note": note,
      "git_commit": state["commit"], "git_dirty": state["dirty"],
      "configs_from_commit": cfg_commit or "working tree",
      "python": sys.version, "platform": platform.platform(),
      "pip_freeze": pip_freeze() if with_pip else [],
      "channel_audit": channel_audit(root),
      "n_files": len(entries), "files": entries,
      "summary_rows": len(rows),
    }
    (snap / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
  except BaseException:
    shutil.rmtree(snap, ignore_errors=True)   # never leave a half snapshot that blocks the tag
    raise
  make_read_only(snap)
  return snap


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--tag", required=True, help="baseline tag, e.g. v1 (a tag is frozen once)")
  p.add_argument("--note", default="", help="free text stored in MANIFEST.json")
  p.add_argument("--date", default=None, help="YYYY-MM-DD in the folder name (default: today)")
  p.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repository)")
  p.add_argument("--out-base", default="baselines", help="folder under the root receiving the snapshot")
  p.add_argument("--configs-git-rev", default=None,
                 help="commit the config is read from (default: merge-base of HEAD and main)")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  try:
    snap = freeze(args.root, args.tag, args.note, args.date, args.out_base, args.configs_git_rev)
  except FileExistsError as exc:
    print(f"[x] Refusing to overwrite: {exc}")
    return 1
  except (RuntimeError, OSError) as exc:
    print(f"[x] Freeze failed: {exc}")
    return 1
  man = json.loads((snap / "MANIFEST.json").read_text())
  print(f"Baseline {args.tag} frozen: {snap}")
  print(f"  files {man['n_files']}, summary rows {man['summary_rows']}, git {man['git_commit'][:8]} "
        f"(dirty={man['git_dirty']}), configs from {str(man['configs_from_commit'])[:8]}")
  print(f"  subjects audited: {', '.join(man['channel_audit']) or 'none'}; read-only")
  return 0


if __name__ == "__main__":
  sys.exit(main())
