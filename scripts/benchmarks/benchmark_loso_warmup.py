"""Warm-up study of the unsupervised per-subject normalization (P22.4, PF-35, PF-36, R2 exception).

`lda_subjnorm` (P21) z-scores the held-out subject's features with the mean/std of its WHOLE session: an offline upper bound.
Online, only the first trials are available. For every held-out subject and every K in `--warmup-trials`:

1. Recording order (PF-36): trial ids follow class order in built folders, not time. Trials are sorted by the absolute start of
   their first window, `window_starts` = start sample in the continuous recording (01_DATA_SPEC 5.2), read through
   `load_subject`. The ids are never used for the order.
2. The first K trials in that order are the WARM-UP. Their feature rows, WITHOUT labels, give the mean/std (guard: a feature with
   std < 1e-12 gets std 1; with fewer than 2 warm-up windows the std is not estimable and 1 is used for every feature, centring
   only; both are reported in `Std guard`).
3. Only the windows of the trials AFTER the first K are scored, all three variants on the same windows:
   `full` = whole-session statistics (`lda_subjnorm` normalization), `warmup` = first-K statistics, `none` = plain `lda`.
4. One fit per held-out subject on the training subjects (R1, R2): CSP m = 1 per band + FBCCA scores; `none` uses the raw
   training features, `full`/`warmup` the training subjects z-scored with their own whole-session statistics (exactly the `lda`
   and `lda_subjnorm` fits of `benchmark_loso.py`); then scaler + Shrinkage-LDA. Only the test-time normalization changes.

Data: `<data-root>/w<len>_s<stride>/<S>/` (continuous builds), classes 101-105, channels `common | all | names` as in
`benchmark_loso.py`. Outputs (`--out-dir`): `summary.csv` (Subject, Warm-up trials, Warm-up windows, Warm-up classes, Warm-up span
(s), Scored windows, full (%), warmup (%), none (%) + 2-tap columns, binomial SE of each accuracy, `warmup - full`, `Std guard`,
`Warm-up class codes`, Channels, Data source; per K a Mean and SD row over the held-out subjects), `cohort.csv` (per K),
`recording_order.csv` (trial id, class, first window start, recording rank) and `warmup_config.json`. Accuracies are unsmoothed
(per window); the 2-tap columns smooth within trial (R8). The warm-up statistics are test-time normalization from unlabeled data
(first K trials = the online variant; `full` = offline upper bound).
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

ROOT = next((q for q in Path(__file__).resolve().parents if (q / "configs" / "pipeline_config.yaml").is_file()),
            Path(__file__).resolve().parents[2])
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts.benchmarks import benchmark_loso as L  # noqa: E402
from scripts.benchmarks.benchmark_window_sweep import folder_name  # noqa: E402
from src.io.subject_data import discover_subjects, is_built  # noqa: E402
from src.models.classical.benchmark_runner import load_config  # noqa: E402
from src.preprocessing.window_quality import quality_params_from_config  # noqa: E402

STD_FLOOR = 1e-12
KS = (1, 2, 5, 10)
SUMMARY_COLUMNS = ["Subject", "Warm-up trials", "Warm-up windows", "Warm-up classes", "Warm-up span (s)", "Scored windows",
                   "full (%)", "warmup (%)", "none (%)", "full 2-tap (%)", "warmup 2-tap (%)", "none 2-tap (%)",
                   "full SE (pp)", "warmup SE (pp)", "none SE (pp)", "warmup - full (pp)", "warmup - none (pp)", "Std guard",
                   "Warm-up class codes", "Channels", "Data source"]


# --- recording order (PF-36) ---------------------------------------------------------------------------------------

def recording_order(trial: np.ndarray, starts: np.ndarray) -> tuple:
  """`(trial ids in recording order, their first window start)`: each trial ranked by the smallest window start (absolute sample
  of the continuous recording) of its rows; ties by trial id. The id order is not used."""
  trial, starts = np.asarray(trial), np.asarray(starts)
  ids = np.unique(trial)
  first = np.array([starts[trial == t].min() for t in ids])
  o = np.lexsort((ids, first))
  return ids[o], first[o]


def warmup_rows(trial: np.ndarray, starts: np.ndarray, k: int) -> np.ndarray:
  """Boolean mask of the rows that belong to the first `k` trials in recording order."""
  ids, _ = recording_order(trial, starts)
  return np.isin(trial, ids[:k])


# --- statistics ----------------------------------------------------------------------------------------------------

def warmup_stats(F: np.ndarray, floor: float = STD_FLOOR) -> tuple:
  """`(mean, std, guard text)` of the warm-up feature rows `F`. Unlabeled by construction (labels are not an argument).
  < 2 rows: std is not estimable -> 1 for every feature (centring only); features with std < floor get 1."""
  F = np.asarray(F, dtype=np.float64)
  mu = F.mean(axis=0)
  if len(F) < 2:
    return mu, np.ones(F.shape[1]), f"mean-only ({len(F)} warm-up window)"
  sd = F.std(axis=0)
  low = sd < floor
  return mu, np.where(low, 1.0, sd), (f"{int(low.sum())} of {len(sd)} features floored" if low.any() else "none")


def apply_stats(F: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
  return (np.asarray(F, dtype=np.float64) - mu) / sd


def binom_se_pp(acc: float, n: int) -> float:
  """Binomial standard error of an accuracy in percentage points (P21 C-3)."""
  return 100.0 * float(np.sqrt(acc * (1.0 - acc) / n)) if n > 0 else float("nan")


# --- one held-out subject ------------------------------------------------------------------------------------------

def warmup_probas(F: np.ndarray, subj: np.ndarray, tr: np.ndarray, te: np.ndarray, ytr: np.ndarray, trial_te: np.ndarray,
                  starts_te: np.ndarray, ks: Sequence[int], seed: int = L.SEED) -> dict:
  """Class probabilities of the held-out rows `te` for `none`, `full` and, per K, `warmup`. No test label is an argument.

  `F` = features of all rows (CSP fitted on `tr` only), `ytr` = training labels. Returns `{"none", "full", "warmup": {K: proba},
  "mask": {K: warm-up rows}, "guard": {K: text}, "stats": {K: (mu, sd)}}`; every proba is (len(te), classes)."""
  Ftr, Fte = F[tr], F[te]
  none = L.lda_pipeline(seed).fit(Ftr, ytr)
  norm = L.lda_pipeline(seed).fit(L.subject_zscore(Ftr, subj[tr]), ytr)
  zeros = np.zeros(len(te), dtype=int)
  out = {"none": none.predict_proba(Fte), "full": norm.predict_proba(L.subject_zscore(Fte, zeros)),
         "warmup": {}, "mask": {}, "guard": {}, "stats": {}}
  for k in ks:
    m = warmup_rows(trial_te, starts_te, k)
    mu, sd, guard = warmup_stats(Fte[m])
    out["warmup"][k] = norm.predict_proba(apply_stats(Fte, mu, sd))
    out["mask"][k], out["guard"][k], out["stats"][k] = m, guard, (mu, sd)
  return out


def k_row(subject: str, k: int, res: dict, y: np.ndarray, trial: np.ndarray, offset: np.ndarray, starts: np.ndarray,
          classes: np.ndarray, win_samples: int, fs: float, channels: str, source: str) -> dict:
  """Summary row of one (subject, K): the three variants scored on the windows of the trials after the first K only."""
  warm = res["mask"][k]
  sc = ~warm
  yi = np.searchsorted(classes, y)
  n = int(sc.sum())
  row = {"Subject": subject, "Warm-up trials": k, "Warm-up windows": int(warm.sum()),
         "Warm-up classes": int(len(np.unique(y[warm]))),
         "Warm-up span (s)": round(float((starts[warm].max() + win_samples - starts[warm].min()) / fs), 2) if warm.any() else np.nan,
         "Scored windows": n, "Std guard": res["guard"][k], "Warm-up class codes": " ".join(str(c) for c in np.unique(y[warm])),
         "Channels": channels, "Data source": source}
  for name, proba in (("full", res["full"]), ("warmup", res["warmup"][k]), ("none", res["none"])):
    if n == 0:
      row.update({f"{name} (%)": np.nan, f"{name} 2-tap (%)": np.nan, f"{name} SE (pp)": np.nan})
      continue
    p = proba[sc]
    acc = float(np.mean(p.argmax(1) == yi[sc]))
    sm = L.smooth_two_tap(p, trial[sc], offset[sc]).argmax(1)
    row.update({f"{name} (%)": round(100 * acc, 2), f"{name} 2-tap (%)": round(100 * float(np.mean(sm == yi[sc])), 2),
                f"{name} SE (pp)": round(binom_se_pp(acc, n), 2)})
  row["warmup - full (pp)"] = round(row["warmup (%)"] - row["full (%)"], 2) if n else np.nan
  row["warmup - none (pp)"] = round(row["warmup (%)"] - row["none (%)"], 2) if n else np.nan
  return row


def cohort_table(per: pd.DataFrame) -> pd.DataFrame:
  """Per K: Mean and SD (ddof = 1) over the held-out subjects that have scored windows, with `warmup - full` and
  `warmup - none` from the per-subject differences, and the mean binomial SE of the warm-up accuracy."""
  rows = []
  for k, g in per[per["Scored windows"] > 0].groupby("Warm-up trials", sort=True):
    r = {"Warm-up trials": k, "Subjects": len(g)}
    for c in ("full (%)", "warmup (%)", "none (%)", "warmup - full (pp)", "warmup - none (pp)", "warmup SE (pp)"):
      r[f"{c} Mean"] = round(float(g[c].mean()), 2)
      if c != "warmup SE (pp)":
        r[f"{c} SD"] = round(float(g[c].std(ddof=1)), 2) if len(g) > 1 else 0.0
    r["Warm-up windows Mean"] = round(float(g["Warm-up windows"].mean()), 1)
    r["Warm-up span (s) Mean"] = round(float(g["Warm-up span (s)"].mean()), 1)
    rows.append(r)
  return pd.DataFrame(rows)


# --- driver --------------------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--data-root", type=Path, default=Path("data/processed_continuous"))
  p.add_argument("--window", type=float, default=1.0)
  p.add_argument("--stride-sec", type=float, default=0.25)
  p.add_argument("--subjects", nargs="*", default=None, help="default: every built S<k> found")
  p.add_argument("--warmup-trials", nargs="+", type=int, default=list(KS), help="K values (default 1 2 5 10)")
  p.add_argument("--channels", nargs="+", default=["common"], metavar="common|all|NAME", help="as benchmark_loso.py")
  p.add_argument("--out-dir", type=Path, default=Path("reports/loso_warmup"))
  p.add_argument("--seed", type=int, default=L.SEED)
  p.add_argument("--config", type=Path, default=None)
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  L.capture_run_state()
  try:
    mode, names = L.parse_channels(args.channels)
  except ValueError as e:
    raise SystemExit(f"[x] {e}")
  if any(k < 1 for k in args.warmup_trials):
    raise SystemExit("[x] --warmup-trials values must be >= 1")
  ks = sorted(set(args.warmup_trials))
  root = args.data_root / folder_name(args.window, args.stride_sec)
  subjects = L.check_subject_names(args.subjects if args.subjects else discover_subjects(root))
  bad = [s for s in subjects if not is_built(root / s)]
  if bad or len(subjects) < 2:
    raise SystemExit(f"[x] needs >= 2 built subjects in {root}; not built or too few: {bad or subjects}")
  cfg = load_config(args.config or L.ROOT / "configs" / "pipeline_config.yaml")
  q = quality_params_from_config(cfg)
  thresholds = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  t_all = time.time()
  print(f"Warm-up: K {ks}, window {args.window:g} s stride {args.stride_sec:g} s, subjects {subjects}, channels "
        f"{mode if mode != 'names' else names}; recording order = first window start (PF-36); statistics of the first K trials, "
        "no labels (PF-35); one fit per held-out subject on the training subjects (R1, R2)", flush=True)
  try:
    chosen, loaded = L.load_cohort(root, subjects, mode, ("fbcca", "fbcsp"), thresholds, q["channel_fail_fraction"], False, names)
  except ValueError as e:
    raise SystemExit(f"[x] {e}")
  subjects = [d["subject"] for d in loaded]
  sessions = sorted({str(d["meta"].get("session", "?")) for d in loaded})
  P = L.pool(loaded, ["fbcsp"], consume=True)
  del loaded
  if P["starts"] is None:
    raise SystemExit("[x] the folders carry no window_starts; recording order cannot be derived")
  fs = P["fs"]
  win_samples = int(round(args.window * fs))
  chan_txt = ", ".join(chosen)
  source = (f"built continuous folders {root.parent.name}/{root.name}, session {'/'.join(sessions)}, cohort {len(subjects)} subjects "
            f"({', '.join(subjects)}), LOSO, channels {mode}; recording order from window_starts")
  rows, order_rows = [], []
  for k_s, s in enumerate(subjects):
    t0 = time.time()
    tr, te = L.loso_split(P["subj"], k_s)
    csp, F = L.lda_features(P["bands"]["fbcsp"], P["fb"], P["yi"], tr)
    trial_te = P["trial"][te] - L.TRIAL_OFFSET * k_s
    res = warmup_probas(F, P["subj"], tr, te, P["yi"][tr], trial_te, P["starts"][te], ks, args.seed)
    ids, first = recording_order(trial_te, P["starts"][te])
    cls = {int(t): int(P["y"][te][trial_te == t][0]) for t in ids}
    order_rows += [{"Subject": s, "Recording rank": r + 1, "Trial id": int(t), "Class": cls[int(t)], "First window start (sample)": int(f),
                    "First window start (s)": round(float(f) / fs, 3)} for r, (t, f) in enumerate(zip(ids, first))]
    for k in ks:
      rows.append(k_row(s, k, res, P["y"][te], trial_te, P["offsets"][te], P["starts"][te], P["classes"], win_samples, fs, chan_txt, source))
    r0 = rows[-len(ks)]
    print(f"[+] {s}: {len(te)} windows, {len(ids)} trials; id order {[int(t) for t in sorted(ids)[:6]]}... vs recording order "
          f"{[int(t) for t in ids[:6]]}...; K={ks[0]}: full {r0['full (%)']}, warmup {r0['warmup (%)']}, none {r0['none (%)']}; "
          f"{time.time() - t0:.1f} s", flush=True)
  per = pd.DataFrame(rows)
  cohort = cohort_table(per)
  agg = []
  for k in ks:
    g = per[(per["Warm-up trials"] == k) & (per["Scored windows"] > 0)]
    for name, f in (("Mean", lambda a: a.mean()), ("SD", lambda a: a.std(ddof=1) if len(a) > 1 else 0.0)):
      r = {"Subject": name, "Warm-up trials": k, "Channels": chan_txt, "Data source": f"{source} | {len(g)} held-out subjects"}
      for c in SUMMARY_COLUMNS:
        if c.endswith(("(%)", "(pp)", "windows", "classes", "(s)")) and c not in r:
          r[c] = round(float(f(g[c].astype(float))), 2) if len(g) else np.nan
      agg.append(r)
  summary = pd.concat([per, pd.DataFrame(agg)], ignore_index=True)[SUMMARY_COLUMNS]
  out = args.out_dir
  out.mkdir(parents=True, exist_ok=True)
  summary.to_csv(out / "summary.csv", index=False)
  cohort.to_csv(out / "cohort.csv", index=False)
  pd.DataFrame(order_rows).to_csv(out / "recording_order.csv", index=False)
  (out / "warmup_config.json").write_text(json.dumps(
    {"cohort": subjects, "warmup_trials": ks, "channels_mode": mode, "channels": chosen, "window_sec": args.window,
     "stride_sec": args.stride_sec, "fs": fs, "seed": args.seed, "std_floor": STD_FLOOR, "git_head": L.RUN_STATE["git_head"],
     "git_dirty": L.RUN_STATE["git_dirty"], "recording_order": "sort trials by first window start (window_starts, samples)",
     "source": source}, indent=2) + "\n")
  show = ["Subject", "Warm-up trials", "Warm-up windows", "Warm-up classes", "Warm-up span (s)", "Scored windows", "full (%)",
          "warmup (%)", "none (%)", "warmup - full (pp)", "full SE (pp)", "Std guard"]
  print("\n" + summary[show].to_string(index=False))
  print(f"\nCohort (per K):\n{cohort.to_string(index=False)}")
  print(f"\nSaved: {out}/summary.csv, cohort.csv, recording_order.csv, warmup_config.json; runtime {time.time() - t_all:.0f} s")
  return 0


if __name__ == "__main__":
  sys.exit(main())
