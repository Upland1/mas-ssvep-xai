"""Dynamic stopping on window-level probabilities (P20.5, R8, PF-38).

Input: one or more `predictions.csv` of the window sweep (`scripts.benchmarks.benchmark_window_sweep`; columns
`subject, window_sec, method, run, trial_id, offset_sec, true, pred, p_<class>...`). Methods without probabilities
(`fbcca`: correlations, all `p_*` empty) are skipped with a console line.

Rule, per (subject, method, window, run, trial), for every threshold:
1. windows sorted by (trial, offset) (R8: offsets restart at 0 in each trial; the input order is never trusted);
2. windows with `offset_sec < --skip-sec` are dropped (evoked-response onset);
3. cumulative mean of the class probabilities over the remaining windows, in time order;
4. the decision is taken at the first window whose cumulative-mean maximum is >= threshold: `pred` = its argmax,
   `time_sec = offset_sec + window_sec` (the end of that window); if no window reaches it, the decision is forced
   at the last window (`forced = 1`, same time rule). A trial with no window after the skip gets no decision and is
   counted in `Skipped trials`.

Output (`--out-dir`, default reports/dynamic_stopping):
- `decisions.csv`: `subject, method, window_sec, run, trial_id, threshold, true, pred, time_sec, forced`;
- `per_subject.csv`: `Subject, Method, Window (s), Threshold, Runs, Trials, Skipped trials, Acc (%), Mean Time (s),
  Forced (%), ITR (bits/min), Best (ITR), Data source`; accuracy pooled over the runs of a subject, ITR = Wolpaw with
  N = number of classes and T = mean decision time + `--gaze-sec` (0.5 s); `Best (ITR)` marks, per subject, method and
  window, the threshold of highest ITR (ties: the lowest threshold);
- `cohort.csv`: per method, window and threshold the mean over subjects (and SD over subjects) of the per-subject values,
  `Best (ITR)` on the threshold of highest mean ITR;
- `best_threshold.csv`: the `Best (ITR)` rows of `cohort.csv`. The threshold is selected on the same data it is
  reported on, over the number of thresholds given: descriptive, not a held-out claim.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence


def _find_root() -> Path:
  """Repository root: upward search for configs/pipeline_config.yaml, else three levels up."""
  here = Path(__file__).resolve()
  for parent in here.parents:
    if (parent / "configs" / "pipeline_config.yaml").is_file():
      return parent
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

GAZE_SEC = 0.5
STIMULUS_SEC = 5.0                 # length of a target segment (config baseline.stimulus_duration_sec)
KEYS = ["subject", "method", "window_sec", "run", "trial_id"]
DECISION_COLUMNS = ["subject", "method", "window_sec", "run", "trial_id", "threshold", "true", "pred", "time_sec",
                    "forced"]
PER_SUBJECT_COLUMNS = ["Subject", "Method", "Window (s)", "Threshold", "Runs", "Trials", "Skipped trials", "Acc (%)",
                       "Mean Time (s)", "Forced (%)", "ITR (bits/min)", "Best (ITR)", "Data source"]
COHORT_COLUMNS = ["Method", "Window (s)", "Threshold", "Subjects", "Acc (%)", "Acc SD", "Mean Time (s)", "Forced (%)",
                  "ITR (bits/min)", "ITR SD", "Best (ITR)", "Data source"]
EPS = 1e-9


def itr_bits_per_min(acc: float, n_classes: int, seconds: float) -> float:
  """Wolpaw ITR in bits/min; 0 for acc <= 1/N, log2(N) bits for acc = 1 (the limit)."""
  if acc <= 1.0 / n_classes:
    return 0.0
  bits = np.log2(n_classes) if acc >= 1.0 else (
    np.log2(n_classes) + acc * np.log2(acc) + (1 - acc) * np.log2((1 - acc) / (n_classes - 1)))
  return float(bits * 60.0 / seconds)


def decide_trial(proba: np.ndarray, offsets: np.ndarray, window_sec: float, thresholds: Sequence[float],
                 skip_sec: float, classes: Sequence[int]) -> list:
  """Decisions of ONE trial for every threshold, from its windows in ANY order.

  `proba (k, C)` class probabilities, `offsets (k,)` window offsets in seconds (start of the window inside the
  trial), `classes (C,)` the class code of each column. Windows are sorted by offset first (R8), those with
  `offset < skip_sec` are dropped, the cumulative mean is taken in time order. Returns one dict per threshold
  `{threshold, pred, time_sec, forced}`; an empty list when no window is left after the skip.
  """
  p = np.asarray(proba, dtype=np.float64)
  o = np.asarray(offsets, dtype=np.float64)
  if p.ndim != 2 or len(p) != len(o) or p.shape[1] != len(classes):
    raise ValueError(f"proba {p.shape}, offsets {o.shape}, classes {len(classes)}: shapes do not fit")
  if not np.all(np.isfinite(p)):
    raise ValueError("non-finite probabilities")
  if len(np.unique(o)) != len(o):
    raise ValueError("two windows of one trial share an offset")
  order = np.argsort(o, kind="stable")
  p, o = p[order], o[order]
  keep = o >= skip_sec - EPS
  p, o = p[keep], o[keep]
  if len(p) == 0:
    return []
  cum = np.cumsum(p, axis=0) / np.arange(1, len(p) + 1)[:, None]
  hit = cum.max(axis=1)
  out = []
  for th in thresholds:
    idx = np.flatnonzero(hit >= th - EPS)
    forced = len(idx) == 0
    k = len(p) - 1 if forced else int(idx[0])
    out.append({"threshold": float(th), "pred": int(classes[int(cum[k].argmax())]),
                "time_sec": float(o[k] + window_sec), "forced": int(forced)})
  return out


def prob_columns(df: pd.DataFrame) -> list:
  """`p_<class>` columns of a predictions frame, ordered by class code."""
  cols = [c for c in df.columns if c.startswith("p_")]
  if not cols:
    raise ValueError("no p_<class> columns in the predictions")
  return sorted(cols, key=lambda c: int(c[2:]))


def check_offsets(df: pd.DataFrame, stimulus_sec: float = STIMULUS_SEC) -> None:
  """Fail loudly when `offset_sec` cannot be seconds: a window must end inside the stimulus segment, so
  `offset_sec + window_sec <= stimulus_sec`. Offsets stored in samples (64, 128, ...) violate it."""
  bad = df[df["offset_sec"] + df["window_sec"] > stimulus_sec + EPS]
  if len(bad):
    r = bad.iloc[0]
    raise ValueError(f"{len(bad)} rows end after the {stimulus_sec:g} s stimulus segment (first: subject {r['subject']}, "
                     f"method {r['method']}, window {r['window_sec']:g}, offset_sec {r['offset_sec']:g}): is "
                     "`offset_sec` in samples instead of seconds?")


def simulate(pred: pd.DataFrame, thresholds: Sequence[float], skip_sec: float) -> tuple:
  """`(decisions, skipped)` for a concatenated predictions frame: `decisions` has `DECISION_COLUMNS`, `skipped` is a
  DataFrame of `KEYS` of the trials without a window after the skip. Rows without probabilities must be removed first."""
  cols = prob_columns(pred)
  classes = [int(c[2:]) for c in cols]
  need = KEYS + ["offset_sec", "true"] + cols
  miss = [c for c in need if c not in pred.columns]
  if miss:
    raise ValueError(f"predictions lack columns {miss}")
  check_offsets(pred)
  rows, skipped = [], []
  for key, g in pred.groupby(KEYS, sort=True):
    true = g["true"].unique()
    if len(true) != 1:
      raise ValueError(f"trial {key} has several true labels {true}")
    dec = decide_trial(g[cols].to_numpy(), g["offset_sec"].to_numpy(), float(key[2]), thresholds, skip_sec, classes)
    if not dec:
      skipped.append(dict(zip(KEYS, key)))
    for d in dec:
      rows.append({"subject": key[0], "method": key[1], "window_sec": float(key[2]), "run": int(key[3]),
                   "trial_id": int(key[4]), "true": int(true[0]), **d})
  frame = pd.DataFrame(rows, columns=DECISION_COLUMNS)
  return frame, pd.DataFrame(skipped, columns=KEYS)


def per_subject_table(dec: pd.DataFrame, skipped: pd.DataFrame, n_classes: int, gaze_sec: float, source: str) -> pd.DataFrame:
  """Accuracy, mean time, forced share and ITR per subject, method, window and threshold; `Best (ITR)` flag."""
  rows = []
  for (s, m, w, th), g in dec.groupby(["subject", "method", "window_sec", "threshold"], sort=True):
    acc = float((g["pred"] == g["true"]).mean())
    t = float(g["time_sec"].mean())
    sk = skipped[(skipped["subject"] == s) & (skipped["method"] == m) & (skipped["window_sec"] == w)]
    rows.append({"Subject": s, "Method": m, "Window (s)": w, "Threshold": th, "Runs": int(g["run"].nunique()),
                 "Trials": int(len(g)), "Skipped trials": int(len(sk)),
                 "Acc (%)": 100 * acc, "Mean Time (s)": t, "Forced (%)": 100 * float(g["forced"].mean()),
                 "ITR (bits/min)": itr_bits_per_min(acc, n_classes, t + gaze_sec), "Data source": source})
  out = pd.DataFrame(rows)
  out["Best (ITR)"] = 0
  for _, g in out.groupby(["Subject", "Method", "Window (s)"]):
    out.loc[g.sort_values(["ITR (bits/min)", "Threshold"], ascending=[False, True]).index[0], "Best (ITR)"] = 1
  return out[PER_SUBJECT_COLUMNS]


def cohort_table(ps: pd.DataFrame, source: str) -> pd.DataFrame:
  """Mean over subjects (SD over subjects) of the per-subject values; `Best (ITR)` on the highest mean ITR."""
  rows = []
  for (m, w, th), g in ps.groupby(["Method", "Window (s)", "Threshold"], sort=True):
    rows.append({"Method": m, "Window (s)": w, "Threshold": th, "Subjects": int(g["Subject"].nunique()),
                 "Acc (%)": g["Acc (%)"].mean(), "Acc SD": g["Acc (%)"].std(ddof=0),
                 "Mean Time (s)": g["Mean Time (s)"].mean(), "Forced (%)": g["Forced (%)"].mean(),
                 "ITR (bits/min)": g["ITR (bits/min)"].mean(), "ITR SD": g["ITR (bits/min)"].std(ddof=0),
                 "Data source": source})
  out = pd.DataFrame(rows)
  out["Best (ITR)"] = 0
  for _, g in out.groupby(["Method", "Window (s)"]):
    out.loc[g.sort_values(["ITR (bits/min)", "Threshold"], ascending=[False, True]).index[0], "Best (ITR)"] = 1
  return out[COHORT_COLUMNS]


def load_predictions(paths: Sequence[Path]) -> pd.DataFrame:
  """Concatenated predictions of several files; ValueError on a missing file or on a duplicated window row."""
  frames = []
  for p in paths:
    if not Path(p).is_file():
      raise FileNotFoundError(f"{p} not found (run scripts.benchmarks.benchmark_window_sweep first)")
    frames.append(pd.read_csv(p))
  df = pd.concat(frames, ignore_index=True)
  dup = df.duplicated(KEYS + ["offset_sec"]).sum()
  if dup:
    raise ValueError(f"{dup} duplicated (subject, method, window, run, trial, offset) rows across the inputs")
  return df


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("predictions", nargs="+", type=Path, help="predictions.csv of the window sweep (one or more)")
  p.add_argument("--thresholds", type=float, nargs="+", default=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
  p.add_argument("--skip-sec", type=float, default=0.5, help="windows starting before this offset are dropped")
  p.add_argument("--gaze-sec", type=float, default=GAZE_SEC, help="gaze-shift time added to T of the ITR (default 0.5)")
  p.add_argument("--out-dir", type=Path, default=Path("reports/dynamic_stopping"))
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  try:
    df = load_predictions(args.predictions)
  except (OSError, ValueError) as exc:
    print(f"[x] {exc}")
    return 1
  cols = prob_columns(df)
  has_p = df[cols].notna().all(axis=1)
  for m in sorted(df.loc[~has_p, "method"].unique()):
    print(f"[-] Skipping method {m!r}: no class probabilities (correlation scores, not probabilities)")
  df = df[has_p].copy()
  if df.empty:
    print("[x] no row with probabilities")
    return 1
  source = "window sweep " + ", ".join(str(p) for p in args.predictions) + " (continuous build, shared quality)"
  print(f"Data source: {source}")
  try:
    dec, skipped = simulate(df, args.thresholds, args.skip_sec)
  except ValueError as exc:
    print(f"[x] {exc}")
    return 1
  ps = per_subject_table(dec, skipped, len(cols), args.gaze_sec, source)
  co = cohort_table(ps, source)
  out = Path(args.out_dir)
  out.mkdir(parents=True, exist_ok=True)
  dec.to_csv(out / "decisions.csv", index=False)
  ps.to_csv(out / "per_subject.csv", index=False, float_format="%.6g")
  co.to_csv(out / "cohort.csv", index=False, float_format="%.6g")
  best = co[co["Best (ITR)"] == 1]
  best.to_csv(out / "best_threshold.csv", index=False, float_format="%.6g")
  print(f"Skipped trials (no window after {args.skip_sec:g} s): {len(skipped)}")
  print(f"Best threshold per method and window by cohort ITR (selected over {len(args.thresholds)} thresholds on the "
        "same data: descriptive):")
  print(best[["Method", "Window (s)", "Threshold", "Acc (%)", "Mean Time (s)", "Forced (%)", "ITR (bits/min)"]]
        .to_string(index=False, float_format=lambda v: f"{v:.2f}"))
  print(f"Saved: {out}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
