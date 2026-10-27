"""Descriptive cross-frequency comparison of connectivity DELTA matrices (P14.1, PF-24 to PF-26).

Data source: the P13 final edge files `reports/connectivity_edges/<S>_<method>.npz` (keys `diff_<c>`,
`fdr_<c>`, `channels_kept`); only the delta matrices are read (PF-24). Every matrix is embedded in the 8 x 8
montage with NaN for missing channels (PF-26); the directed PDC is symmetrized `(M + M.T) / 2` before every
undirected statistic (PF-25), while its FDR count stays over the 42 directed edges.

Per subject and method:
- Pearson r between the off-diagonal entries of every frequency pair, with a one-tailed QAP node-label
  permutation p (2,000 permutations, >= 6 finite pairs, >= 4 shared channels; seeds derived from 42 per
  (subject, method, pair), so nothing depends on any parallelism);
- node strength per channel (mean to the others), global mean delta and FDR-edge count per frequency.
Group summaries (all / responders / non-responders) use Fisher-z averaging of r. Responders come from the
classifier benchmark only (2.0 s smoothed >= 80 %, `reports/n_subjects_benchmark.csv`, or `--responders`),
never from connectivity (PF-21). Frequencies are on the fs-250 axis (legacy, PF-04). With five subjects every
group number is descriptive.

Output: reports/connectivity_comparison/<m>_{frequency_similarity,node_strength,global_delta}.csv (section 6
schemas), <m>_{frequency_similarity,node_strength,global_delta}_groups.csv (group summaries), and figures in
outputs/figures/connectivity_comparison/ (one colour limit per method shared by every panel, P12 D-4).
"""

import argparse
import itertools
import re
import sys
import warnings
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

from src.features.connectivity.comparison import (  # noqa: E402
  MONTAGE, SEED, fisher_mean, mean_upper, node_strength, qap_pvalue, responders_from_benchmark, undirected_delta)
from src.features.connectivity.connectivity_extraction import CONDITION_FREQS  # noqa: E402
from src.features.connectivity.permutation import derive_seed  # noqa: E402

METHODS = ("coherence", "plv", "wpli", "pdc")
DIRECTED = {"pdc"}
CONDITIONS = tuple(CONDITION_FREQS)
SIM_COLUMNS = ["subject", "method", "freq_a", "freq_b", "r", "p_qap"]
NODE_COLUMNS = ["subject", "method", "condition", "frequency", "channel", "node_strength"]
GLOBAL_COLUMNS = ["subject", "method", "condition", "frequency", "mean_delta", "n_fdr_edges"]
SOURCE = "P13 final edge files (trial-level), legacy windows, fs-250 axis (PF-04)"


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--methods", nargs="+", choices=list(METHODS), default=list(METHODS))
  p.add_argument("--subjects", nargs="+", default=None, help="default: every <S>_<method>.npz in the edges dir")
  p.add_argument("--qap-permutations", type=int, default=2000)
  p.add_argument("--responders", nargs="*", default=None,
                 help="explicit responder list; default: 2.0 s smoothed >= 80 %% in the benchmark CSV (PF-21)")
  p.add_argument("--benchmark", type=Path, default=ROOT / "reports" / "n_subjects_benchmark.csv")
  p.add_argument("--threshold", type=float, default=80.0)
  p.add_argument("--edges-dir", type=Path, default=ROOT / "reports" / "connectivity_edges")
  p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
  p.add_argument("--figures-dir", type=Path, default=ROOT / "outputs" / "figures" / "connectivity_comparison")
  p.add_argument("--no-figures", action="store_true")
  p.add_argument("--random-state", type=int, default=SEED)
  return p


def discover_subjects(edges_dir: Path, methods: Sequence[str]) -> list:
  found = None
  for m in methods:
    s = {re.match(r"(S\d+)_", f.name).group(1) for f in Path(edges_dir).glob(f"S*_{m}.npz")}
    found = s if found is None else found & s
  return sorted(found or [])


def load_deltas(edges_dir: Path, subject: str, method: str) -> dict:
  """`{condition: (8, 8) delta}` embedded and symmetrized, plus FDR counts, from one edge file (PF-24/25/26)."""
  d = np.load(Path(edges_dir) / f"{subject}_{method}.npz", allow_pickle=False)
  kept = [str(c) for c in d["channels_kept"]]
  deltas, fdr = {}, {}
  for c in CONDITIONS:
    if f"diff_{c}" not in d.files:
      continue
    deltas[c] = undirected_delta(d[f"diff_{c}"], kept, method in DIRECTED)
    fdr[c] = int(np.asarray(d[f"fdr_{c}"]).sum())
  return dict(deltas=deltas, fdr=fdr, channels_kept=kept)


def subject_tables(subject: str, method: str, loaded: dict, n_qap: int, random_state: int) -> tuple:
  """`(similarity_rows, node_rows, global_rows)` for one subject and method."""
  deltas, fdr = loaded["deltas"], loaded["fdr"]
  sim, node, glob = [], [], []
  for a, b in itertools.combinations([c for c in CONDITIONS if c in deltas], 2):
    q = qap_pvalue(deltas[a], deltas[b], n_qap, derive_seed(random_state, subject, method, a, b))
    sim.append(dict(subject=subject, method=method, freq_a=CONDITION_FREQS[a], freq_b=CONDITION_FREQS[b],
                    r=q["r"], p_qap=q["p"]))
  for c, m in deltas.items():
    ns = node_strength(m)
    for ch, v in zip(MONTAGE, ns):
      node.append(dict(subject=subject, method=method, condition=c, frequency=CONDITION_FREQS[c],
                       channel=ch, node_strength=v))
    glob.append(dict(subject=subject, method=method, condition=c, frequency=CONDITION_FREQS[c],
                     mean_delta=mean_upper(m), n_fdr_edges=fdr[c]))
  return sim, node, glob


def group_members(subjects: Sequence[str], responders: Sequence[str]) -> dict:
  resp = [s for s in subjects if s in set(responders)]
  return {"all": list(subjects), "responders": resp, "non_responders": [s for s in subjects if s not in resp]}


def group_similarity(sim: pd.DataFrame, groups: dict, alpha: float = 0.05) -> pd.DataFrame:
  """Per group and frequency pair: Fisher-mean r, subjects, subjects with p_qap < alpha."""
  rows = []
  for g, subs in groups.items():
    sub = sim[sim["subject"].isin(subs)]
    for (fa, fb), x in sub.groupby(["freq_a", "freq_b"], sort=False):
      rows.append(dict(group=g, freq_a=fa, freq_b=fb, n_subjects=int(x["r"].notna().sum()),
                       r_fisher_mean=fisher_mean(x["r"].values), n_p_qap_lt_05=int((x["p_qap"] < alpha).sum())))
  return pd.DataFrame(rows, columns=["group", "freq_a", "freq_b", "n_subjects", "r_fisher_mean", "n_p_qap_lt_05"])


def group_means(df: pd.DataFrame, groups: dict, keys: list, value: str) -> pd.DataFrame:
  rows = []
  for g, subs in groups.items():
    x = df[df["subject"].isin(subs)]
    if len(x):
      mean = x.groupby(keys, sort=False)[value].agg(lambda v: float(np.nanmean(v)) if np.isfinite(v).any() else np.nan)
      out = mean.rename(f"{value}_mean").reset_index()
      out.insert(0, "group", g)
      out["n_subjects"] = len(subs)
      rows.append(out)
  return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def summary_lines(method: str, sim: pd.DataFrame) -> list:
  """Console lines: Fisher-mean r over subject-pair cells and the share of QAP p < 0.05 (R-13 comparison)."""
  ok = sim["p_qap"].notna()
  n = int(ok.sum())
  share = float((sim.loc[ok, "p_qap"] < 0.05).mean()) if n else float("nan")
  return [f"  {method}: Fisher-mean r {fisher_mean(sim['r'].values):.3f} over {n} subject x pair cells, "
          f"{100 * share:.0f} % with QAP p < 0.05 (descriptive, n subjects = {sim['subject'].nunique()})"]


# ------------------------------------------------------------------ figures

def _heat(ax, m, labels, vmin, vmax, cmap, title):
  im = ax.imshow(m, vmin=vmin, vmax=vmax, cmap=cmap)
  ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=6)
  ax.set_yticks(range(len(labels)), labels, fontsize=6)
  ax.set_title(title, fontsize=7)
  return im


def make_figures(method: str, all_deltas: dict, sim: pd.DataFrame, nodes: pd.DataFrame, groups: dict,
                 fig_dir: Path) -> list:
  """Similarity matrices, node strength and delta matrices per group; one colour limit per method."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  fig_dir = Path(fig_dir)
  fig_dir.mkdir(parents=True, exist_ok=True)
  saved = []
  subjects = list(all_deltas)
  freqs = [CONDITION_FREQS[c] for c in CONDITIONS]
  flab = [f"{f:.2f}" for f in freqs]
  # shared limits: one symmetric range per method over every subject and condition (P12 D-4)
  allv = np.concatenate([m[np.isfinite(m)] for s in subjects for m in all_deltas[s].values()])
  lim = float(np.nanmax(np.abs(allv))) if len(allv) else 1.0
  # 1. similarity matrices (r), one panel per subject, shared [-1, 1]
  fig, axes = plt.subplots(1, len(subjects), figsize=(2.6 * len(subjects), 3), squeeze=False)
  for ax, s in zip(axes[0], subjects):
    mat = np.full((5, 5), np.nan)
    np.fill_diagonal(mat, 1.0)
    for _, r in sim[sim["subject"] == s].iterrows():
      i, j = freqs.index(r["freq_a"]), freqs.index(r["freq_b"])
      mat[i, j] = mat[j, i] = r["r"]
    im = _heat(ax, mat, flab, -1, 1, "RdBu_r", s)
  fig.colorbar(im, ax=axes[0].tolist(), shrink=0.7, label="Pearson r of delta matrices")
  p = fig_dir / f"{method}_frequency_similarity.png"
  fig.savefig(p, dpi=130, bbox_inches="tight")
  plt.close(fig)
  saved.append(p)
  # 2. node strength: channel x frequency per group, shared limit
  nlim = float(np.nanmax(np.abs(nodes["node_strength"]))) if len(nodes) else 1.0
  gl = [g for g, subs in groups.items() if subs]
  fig, axes = plt.subplots(1, len(gl), figsize=(3.2 * len(gl), 3.2), squeeze=False)
  for ax, g in zip(axes[0], gl):
    x = nodes[nodes["subject"].isin(groups[g])].groupby(["channel", "condition"])["node_strength"].mean()
    mat = np.array([[x.get((ch, c), np.nan) for c in CONDITIONS] for ch in MONTAGE])
    im = ax.imshow(mat, vmin=-nlim, vmax=nlim, cmap="RdBu_r", aspect="auto")
    ax.set_xticks(range(5), flab, fontsize=6)
    ax.set_yticks(range(len(MONTAGE)), MONTAGE, fontsize=6)
    ax.set_title(f"{g} (n={len(groups[g])})", fontsize=7)
  fig.colorbar(im, ax=axes[0].tolist(), shrink=0.7, label="node strength (delta)")
  p = fig_dir / f"{method}_node_strength.png"
  fig.savefig(p, dpi=130, bbox_inches="tight")
  plt.close(fig)
  saved.append(p)
  # 3. delta matrices per group (mean over subjects), shared limit
  for g in gl:
    fig, axes = plt.subplots(1, 5, figsize=(11, 2.6))
    for ax, c in zip(axes, CONDITIONS):
      stack = np.stack([all_deltas[s][c] for s in groups[g] if c in all_deltas[s]])
      with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # PO7 is NaN in every legacy subject
        mean = np.nanmean(stack, axis=0)
      im = _heat(ax, mean, MONTAGE, -lim, lim, "RdBu_r", f"{CONDITION_FREQS[c]:.2f} Hz")
    fig.colorbar(im, ax=axes.tolist(), shrink=0.8, label=f"delta ({method}, shared limit +-{lim:.3f})")
    fig.suptitle(f"{method}: {g} (n={len(groups[g])})", fontsize=8)
    p = fig_dir / f"{method}_delta_matrices_{g}.png"
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    saved.append(p)
  return saved


def run(args) -> dict:
  reports = Path(args.reports_dir) / "connectivity_comparison"
  reports.mkdir(parents=True, exist_ok=True)
  subjects = args.subjects or discover_subjects(args.edges_dir, args.methods)
  if not subjects:
    raise SystemExit(f"no edge files for methods {args.methods} in {args.edges_dir}")
  if args.responders is not None:
    resp, src = list(args.responders), "--responders"
  else:
    resp, _ = responders_from_benchmark(args.benchmark, args.threshold)
    src = f"{args.benchmark.name}, 2.0 s smoothed >= {args.threshold:g} %"
  groups = group_members(subjects, resp)
  print(f"Data source: {SOURCE}; subjects {subjects}; methods {list(args.methods)}; QAP {args.qap_permutations} "
        f"permutations; responders {groups['responders']} (from {src}); non-responders {groups['non_responders']}")
  out = {}
  for m in args.methods:
    sims, nodes, globs, deltas = [], [], [], {}
    for s in subjects:
      loaded = load_deltas(args.edges_dir, s, m)
      deltas[s] = loaded["deltas"]
      a, b, c = subject_tables(s, m, loaded, args.qap_permutations, args.random_state)
      sims += a
      nodes += b
      globs += c
    sim = pd.DataFrame(sims, columns=SIM_COLUMNS)
    nd = pd.DataFrame(nodes, columns=NODE_COLUMNS)
    gd = pd.DataFrame(globs, columns=GLOBAL_COLUMNS)
    sim.to_csv(reports / f"{m}_frequency_similarity.csv", index=False)
    nd.to_csv(reports / f"{m}_node_strength.csv", index=False)
    gd.to_csv(reports / f"{m}_global_delta.csv", index=False)
    group_similarity(sim, groups).to_csv(reports / f"{m}_frequency_similarity_groups.csv", index=False)
    group_means(nd, groups, ["channel", "condition", "frequency"], "node_strength").to_csv(
      reports / f"{m}_node_strength_groups.csv", index=False)
    group_means(gd, groups, ["condition", "frequency"], "mean_delta").to_csv(
      reports / f"{m}_global_delta_groups.csv", index=False)
    print("\n".join(summary_lines(m, sim)))
    if not args.no_figures:
      make_figures(m, deltas, sim, nd, groups, args.figures_dir)
    out[m] = dict(similarity=sim, node=nd, global_delta=gd)
  print(f"saved CSVs in {reports}; figures in {args.figures_dir}")
  return out


def main(argv: Optional[Sequence[str]] = None) -> int:
  run(build_parser().parse_args(argv))
  return 0


if __name__ == "__main__":
  sys.exit(main())
