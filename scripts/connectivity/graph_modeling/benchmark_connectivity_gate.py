"""Connectivity gate of P15: do per-window edge features add information over node power + FBCCA? (legacy Era B)

Data source: the cached graph datasets <data-root>/<S>/graph_dataset.npz (build_graph_dataset; legacy
7-channel folders, stimulus windows only, two-tier P07 gate, FBCCA of the flagship, pre-gate trial ids;
feature axis fs = 250, PF-04 labelled; R3 legacy: per-window features).

Feature sets (7 channels): N (node power, 70), F (FBCCA, 5), Base = N + F (75), Ec (upper-triangle coherence
x 5 bands, 105), Ep (upper-triangle phasor cos/sin, 210), Ec+Ep, Base+Ec (180), Base+Ep, Base+Ec+Ep (390).
Classifier: StandardScaler -> optional in-fold SelectKBest(f_classif, k) (k = 0 means none) -> Shrinkage-LDA
(lsqr, auto); every fitted object sees the training fold only (R2). CV: StratifiedGroupKFold(5, shuffle,
42 + r) over the pre-gate trial ids, repeat r = 0..R-1 (R1, PF-03). 1.0 s = out-of-fold window accuracy;
2.0 s = legacy i%5 smoothing of the out-of-fold scores in clean-array order (R8 legacy-folder clause).

Gate verdict (descriptive heuristic, per k): the best edge-augmented set (Base+Ec, Base+Ep, Base+Ec+Ep, by
cohort-mean 1.0 s accuracy) minus Base; PASS iff the cohort-mean delta >= 2 pp AND the delta >= 2 pp in at
least ceil(2/3) of the responders present (S03, S04, S05 from P14, i.e. 2 of 3). k = 0 decides; k = 30 is reported.

Output: <reports-dir>/connectivity_gate_benchmark.csv (subject, set, k_select, repeat, dim, acc_1s, acc_2s;
percent) and .meta.txt with the protocol labels, per-set means and the verdicts.
"""

import argparse
import math
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

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.feature_selection import SelectKBest, f_classif  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402

from src.features.connectivity.connectivity_graph_features import upper_tri_flat  # noqa: E402
from src.features.connectivity.graph_dataset import discover_graph_subjects, load_graph_dataset  # noqa: E402
from src.models.classical.legacy_eval import FeatureSpace, SEED, accuracies, oof_space  # noqa: E402
from src.preprocessing.dataset.cv_utils import assert_no_shared_trials, make_splits  # noqa: E402

RESPONDERS = ("S03", "S04", "S05")   # P14 (classifier accuracy only)
EDGE_SETS = ("Base+Ec", "Base+Ep", "Base+Ec+Ep")
SET_NAMES = ("N", "F", "Base", "Ec", "Ep", "Ec+Ep", "Base+Ec", "Base+Ep", "Base+Ec+Ep")
DELTA_PP = 2.0
COLUMNS = ["subject", "set", "k_select", "repeat", "dim", "acc_1s", "acc_2s"]
LDA_PARAMS = dict(solver="lsqr", shrinkage="auto")


def feature_sets(ds) -> dict:
  """The nine feature matrices of a `GraphDataset` (index layouts: `connectivity_graph_features` docstring, R6)."""
  n = len(ds)
  N = ds.node.reshape(n, -1)
  F = np.asarray(ds.X_fbcca)
  Ec = upper_tri_flat(ds.edge_coh)
  Ep = upper_tri_flat(ds.edge_phase)
  base = np.hstack([N, F])
  return {"N": N, "F": F, "Base": base, "Ec": Ec, "Ep": Ep, "Ec+Ep": np.hstack([Ec, Ep]),
          "Base+Ec": np.hstack([base, Ec]), "Base+Ep": np.hstack([base, Ep]),
          "Base+Ec+Ep": np.hstack([base, Ec, Ep])}


def make_model(k: int, dim: int):
  """Shrinkage-LDA, behind an in-fold SelectKBest(f_classif, min(k, dim)) when k > 0 (the scaler is added by `oof_space`)."""
  lda = LinearDiscriminantAnalysis(**LDA_PARAMS)
  if not k:
    return lda
  return Pipeline([("select", SelectKBest(f_classif, k=min(int(k), dim))), ("lda", lda)])


def evaluate_subject(ds, repeats: int, ks: Sequence[int], sets: Sequence[str] = SET_NAMES, seed: int = SEED) -> list:
  """Rows (COLUMNS, percent) of one subject: every set x k x repeat; splits seed + r shared by all sets and ks."""
  mats = feature_sets(ds)
  rows = []
  for r in range(repeats):
    splits = make_splits("grouped", ds.y, ds.trial_ids, seed + r)
    assert_no_shared_trials(splits, ds.trial_ids)
    for name in sets:
      X = mats[name]
      space = FeatureSpace(name, [X])
      for k in ks:
        models = {"m": make_model(k, X.shape[1])}
        res, errs = oof_space(space, None, ds.y, models, seed + r, splits)
        if errs:
          raise RuntimeError(f"{ds.subject} {name} k={k} r={r}: {errs['m']}")
        a1, a2 = accuracies(ds.y, res["m"]["pred"], res["m"]["scores"], ds.trial_ids, "mod5")
        rows.append({"subject": ds.subject, "set": name, "k_select": int(k), "repeat": r, "dim": int(X.shape[1]),
                     "acc_1s": round(100 * a1, 4), "acc_2s": round(100 * a2, 4)})
  return rows


def set_means(df: pd.DataFrame, k: int) -> pd.DataFrame:
  """Mean 1.0 s accuracy over repeats: rows = sets (SET_NAMES order), columns = subjects + Mean."""
  t = df[df.k_select == k].pivot_table(index="set", columns="subject", values="acc_1s", aggfunc="mean")
  t = t.reindex([s for s in SET_NAMES if s in t.index])
  t["Mean"] = t.mean(axis=1)
  return t


def gate_verdict(df: pd.DataFrame, k: int, responders: Sequence[str] = RESPONDERS, delta_pp: float = DELTA_PP,
                 edge_sets: Sequence[str] = EDGE_SETS) -> dict:
  """Gate rule at one k. `best` = the edge-augmented set with the highest cohort-mean 1.0 s accuracy; `delta[s]` =
  best - Base (mean over repeats, pp); pass iff mean delta >= delta_pp and the delta is >= delta_pp in at least
  ceil(2/3 * n) of the n responders present (n = 0 -> not evaluable, pass False)."""
  t = set_means(df, k)
  subjects = [c for c in t.columns if c != "Mean"]
  avail = [s for s in edge_sets if s in t.index]
  if "Base" not in t.index or not avail:
    raise ValueError("need Base and at least one edge-augmented set")
  best = max(avail, key=lambda s: t.loc[s, subjects].mean())
  delta = {s: float(t.loc[best, s] - t.loc["Base", s]) for s in subjects}
  mean_delta = float(np.mean(list(delta.values())))
  resp = [s for s in responders if s in delta]
  need = math.ceil(2 * len(resp) / 3 - 1e-9)
  n_ok = sum(delta[s] >= delta_pp - 1e-12 for s in resp)
  passed = bool(len(resp) > 0 and mean_delta >= delta_pp - 1e-12 and n_ok >= need)
  return {"k": int(k), "best": best, "delta": delta, "mean_delta": mean_delta, "responders": resp,
          "responders_ok": n_ok, "responders_needed": need, "passed": passed}


def verdict_text(v: dict) -> str:
  ds = ", ".join(f"{s} {d:+.2f}" for s, d in v["delta"].items())
  return (f"k={v['k']}: best edge-augmented set {v['best']}; delta vs Base (pp) {ds}; cohort mean {v['mean_delta']:+.2f}; "
          f"responders with delta >= {DELTA_PP:g} pp: {v['responders_ok']}/{len(v['responders'])} (need {v['responders_needed']}); "
          f"gate {'PASSES' if v['passed'] else 'does NOT pass'}")


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="default: subjects with a graph_dataset.npz")
  p.add_argument("--data-root", type=Path, default=None, help="default data/processed")
  p.add_argument("--reports-dir", type=Path, default=None, help="default <root>/reports")
  p.add_argument("--repeats", type=int, default=5, help="CV repeats, seeds 42 + r (default 5)")
  p.add_argument("--k-select", type=int, nargs="+", default=[0, 30], help="in-fold SelectKBest sizes, 0 = none (default 0 30)")
  p.add_argument("--seed", type=int, default=SEED, help=f"base seed (default {SEED})")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  processed = Path(args.data_root or ROOT / "data" / "processed")
  reports = Path(args.reports_dir or ROOT / "reports")
  subjects = args.subjects or discover_graph_subjects(processed)
  if not subjects:
    print(f"[-] No graph_dataset.npz under {processed}; run build_graph_dataset first")
    return 1
  t0 = time.time()
  print(f"Data source: graph datasets {processed}/<S>/graph_dataset.npz (legacy windows, stimulus only, two-tier gate, fs=250 legacy PF-04, R3 legacy)")
  print(f"CV: StratifiedGroupKFold(5, shuffle, {args.seed}+r) over pre-gate trial ids, r=0..{args.repeats - 1} (R1); "
        f"2.0 s = legacy i%5 smoothing (R8); k_select {args.k_select}")
  rows, meta = [], []
  for s in subjects:
    ds = load_graph_dataset(s, processed)
    t1 = time.time()
    rows += evaluate_subject(ds, args.repeats, args.k_select, seed=args.seed)
    msg = (f"{s}: {len(ds)} clean windows, {len(np.unique(ds.trial_ids))} trials, channels {' '.join(ds.channels_kept)}, "
           f"trial_ids_approximate={ds.trial_ids_approximate}")
    meta.append(msg)
    print(f"[+] {msg}; {time.time() - t1:.0f} s")
  df = pd.DataFrame(rows, columns=COLUMNS)
  out = reports / "connectivity_gate_benchmark.csv"
  out.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(out, index=False)
  lines = [f"cv=StratifiedGroupKFold(5, shuffle, {args.seed}+r) over pre-gate trial ids, repeats {args.repeats} (R1, PF-03)",
           "smoothing: legacy i%5 on the out-of-fold scores in clean-array order (R8 legacy-folder clause)",
           "features: legacy fs=250 (PF-04), per-window features on raw windows (R3 legacy); scaler, SelectKBest and Shrinkage-LDA fitted in-fold (R2)",
           f"data source: legacy windows {processed}/<S>/graph_dataset.npz, stimulus windows, two-tier gate (P07)"] + meta
  for k in args.k_select:
    t = set_means(df, k)
    print(f"\n1.0 s accuracy (%), mean of {args.repeats} repeats, k_select={k}")
    print(t.round(1).to_string())
    lines += ["", f"1.0 s mean accuracy (%), k_select={k}", t.round(2).to_string()]
    try:
      v = gate_verdict(df, k)
      print(verdict_text(v))
      lines.append(verdict_text(v) + ("" if k == min(args.k_select) else " (reported, k=0 decides)"))
    except ValueError as exc:
      print(f"[-] verdict k={k}: {exc}")
  out.with_suffix(".meta.txt").write_text("\n".join(lines) + "\n")
  print(f"\nSaved: {out}; runtime {time.time() - t0:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
