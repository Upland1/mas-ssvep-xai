"""Pseudo-online detector (P20.6, PF-38, PF-39, R2, R3, R5): train on one run, replay another as a causal stream.

Per subject:
1. Training run (`--train-session`, default OO): the recording is filtered CAUSALLY in one pass (`src.online.causal_filter`:
   Butterworth band-pass + notch from the config, `sosfilt` with `zi = sosfilt_zi * x[0]`), stimulus windows
   (`--window-sec`, `--stride-sec`; labels 101-105 -> classes 0-4) and, with `--rest-class`, rest windows from the
   `REST_SEC = 5 s` before every target onset (fixation + cue + preparation; class 5 = the 6th "rest" class) are cut,
   and the quality decision is taken on the causal-filtered and the raw windows (`--quality-source`, config default
   `both`; every limit from the config `quality:` block, R5): channel tier (a channel failing in more than
   `channel_fail_fraction` of the windows is dropped) and window tier. There is NO artifact guard: the guard needs
   future samples (decisions 2026-10-28 P20). The network is trained with `src.models.cnn.training.fit_network` (grouped
   20 % validation on the training trials, early stopping, R2: everything fitted on the training run only).
2. Test run (`--test-session`, default mOO) is replayed in chunks of one stride through a stateful causal filter; windows
   are evaluated on a FIXED CLOCK (window `k` = samples `[k*stride, k*stride + window)` of the stream) and predicted
   (batch prediction is allowed because each window holds past samples only). The MARK channel of the test run is read
   AFTER the predictions exist and is used for scoring only (grouping windows into stimulus periods, the true label).
3. Label-free channel check on the first `--check-sec` (30 s) of the test stream (no MARK, no labels): a channel kept by
   the training gate that fails the channel tier on these windows is dropped from the test AND from the model (the model
   is trained once without it, the same result as training first and retraining).
4. Fallback: if the validation accuracy of the network is below `--min-val-acc` (50 %), everything is redone with
   `--fallback-window-sec` (1 s) windows (`Window (s)` of the summary tells which was used).
5. Decision per stimulus period (target onset `o`, 5 s): the windows fully inside the period that start at or after
   `o + --skip-sec` and pass the window tier; cumulative mean of the class probabilities in time order; the decision is
   taken at the first window whose cumulative-mean maximum over the 5 TARGET classes is >= `--threshold`
   (`time = start - o + window`); the rest class never decides. 5 classes: if no window reaches the threshold the decision
   is FORCED at the last window (`Forced (%)`). With `--rest-class` (6 classes) there is no forcing: no window reaching
   it is "no target" (`Missed (%)`, counted wrong). Rest periods `[o - 5 s, o)` give the false activations: the share of
   rest periods in which the same rule fires. Rejected windows (window tier) are counted in `Windows rejected (%)`
   over all scored windows.
6. PF-39: a warning when the train and test paradigm families differ (O-type `OO`/`mOO` vs checkerboard `C`/`mC`).

Output (`--out-dir`, default reports/pseudo_online): `summary_<tag>.csv` (one row per subject + `Mean`: Subject, Trials,
Acc (%), Time (s), Forced (%) | Missed (%), ITR (bits/min), False act. (%), Windows rejected (%), Window (s), Channels kept,
Dropped at check, Train windows, Val acc (%), and extras Classes, Rest periods, Trials undecided, Trials before check,
Fallback, Data source) and `decisions_<tag>.csv` (one row per scored period). Wolpaw ITR: N = 5, accuracy over all
scored trials (missed = wrong), T = mean decision time + 0.5 s. `--resume` skips subjects whose part files exist.
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
  return here.parents[2]


ROOT = _find_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from scripts import build_windows as bw  # noqa: E402
from scripts.benchmarks.simulate_dynamic_stopping import itr_bits_per_min  # noqa: E402
from src.io import ebr_parser  # noqa: E402
from src.models.cnn.training import (MODELS, ALIASES, fit_network, model_factory, normalise,  # noqa: E402
                                     predict_proba)
from src.online.causal_filter import design_sos, filter_causal, replay_windows  # noqa: E402
from src.preprocessing.signal.quality_check import compute_channel_quality_stats, validate_eeg_windows  # noqa: E402
from src.preprocessing.windowing import cut_windows, event_onsets, load_session  # noqa: E402

REST_SEC = 5.0                 # fixation + cue + preparation before each target (the rest segment)
STIM_SEC = 5.0                 # length of a target segment
GAZE_SEC = 0.5
TARGETS = (101, 102, 103, 104, 105)
REST_CLASS_INDEX = 5
EPS = 1e-9
SUMMARY_BASE = ["Subject", "Trials", "Acc (%)", "Time (s)"]
SUMMARY_TAIL = ["ITR (bits/min)", "False act. (%)", "Windows rejected (%)", "Window (s)", "Channels kept",
                "Dropped at check", "Train windows", "Val acc (%)", "Classes", "Rest periods", "Trials undecided",
                "Trials before check", "Fallback", "Data source"]
DECISION_COLUMNS = ["Subject", "period", "onset_sec", "true", "pred", "correct", "time_sec", "forced", "missed",
                    "false_activation", "n_windows", "n_rejected", "before_check", "window_sec"]


# --- paradigm (PF-39) ------------------------------------------------------------------

def paradigm_family(session: str) -> str:
  """`"O"` for OO / mOO, `"C"` for C / mC (checkerboard), `"?"` otherwise. A leading `m` marks a second run and an
  `online_` prefix an online run (01_DATA_SPEC section 1)."""
  s = str(session).lower()
  if s.startswith("online_"):
    s = s[len("online_"):]
  if s.startswith("m") and s[1:] in ("oo", "c"):
    s = s[1:]
  return {"oo": "O", "c": "C"}.get(s, "?")


def paradigm_warning(train_session: str, test_session: str) -> Optional[str]:
  """PF-39 warning text when the paradigm families differ (checkerboard responses sit at twice the stimulation
  frequency); None when they match or one is unknown."""
  a, b = paradigm_family(train_session), paradigm_family(test_session)
  if "?" in (a, b) or a == b:
    return None
  return (f"[!] PF-39: training on {train_session} ({'checkerboard' if a == 'C' else 'OO'}) and testing on {test_session} "
          f"({'checkerboard' if b == 'C' else 'OO'}): checkerboard responses appear at twice the stimulation frequency, "
          "the detector is not expected to transfer")


# --- quality (explicit limits, R5) ------------------------------------------------------

def limits_of(q: dict) -> dict:
  """The four Vpp/std limits of a quality params dict."""
  return {k: float(q[k]) for k in ("vpp_min", "vpp_max", "std_min", "std_max")}


def _signals(Xf: np.ndarray, Xr: np.ndarray, source: str) -> list:
  if source not in ("filtered", "raw", "both"):
    raise ValueError(f"quality source must be filtered, raw or both, got {source!r}")
  return ([Xf] if source in ("filtered", "both") else []) + ([Xr] if source in ("raw", "both") else [])


def channel_tier(Xf: np.ndarray, Xr: np.ndarray, names: Sequence[str], q: dict) -> set:
  """Channels failing the limits in strictly more than `channel_fail_fraction` of the windows on any checked signal."""
  dropped = set()
  for w in _signals(Xf, Xr, q["source"]):
    st = compute_channel_quality_stats(w, list(names), limits_of(q))
    dropped |= {n for n, s in st.items() if s["fail_fraction"] > q["channel_fail_fraction"]}
  return dropped


def window_tier(Xf: np.ndarray, Xr: np.ndarray, kept_idx: Sequence[int], q: dict) -> np.ndarray:
  """Boolean `(n,)`: the window passes the Vpp/std limits on the kept channels of every checked signal. No artifact
  guard (needs future samples)."""
  ok = np.ones(len(Xf), dtype=bool)
  for w in _signals(Xf, Xr, q["source"]):
    ok &= np.asarray(validate_eeg_windows(w[:, list(kept_idx)], **limits_of(q))).astype(bool)
  return ok


# --- training set -----------------------------------------------------------------------

def training_windows(x: np.ndarray, mark: np.ndarray, fs: float, sos: np.ndarray, n_win: int, stride: int,
                     rest_class: bool) -> dict:
  """Windows of the training run: causal-filtered (`Xf`) and raw (`Xr`), `y` class index (0-4 targets, 5 rest),
  `groups` (one trial id per segment: a target and its rest segment get different ids), `starts`.

  Target segment = `[o, o + 5 s)` of every complete 101-105 onset, windows every `stride` fully inside; rest
  segment = `[o - REST_SEC, o)` of the same onsets. The causal filter runs once over the whole run (its start-up
  transient is the one of the online filter, and the same in the test stream)."""
  xf = filter_causal(x, sos)
  T = x.shape[1]
  starts, ys, gs = [], [], []
  gid = 0
  segs = []
  for ci, code in enumerate(TARGETS):
    for o in event_onsets(mark, code):
      segs.append((int(o), ci, True))
      if rest_class:
        segs.append((int(o - REST_SEC * fs), REST_CLASS_INDEX, False))
  for a, cls, _ in sorted(segs):
    L = int(STIM_SEC * fs)
    if a < 0 or a + L > T or L < n_win:
      continue
    ks = np.arange(0, (L - n_win) // stride + 1) * stride + a
    starts += list(ks)
    ys += [cls] * len(ks)
    gs += [gid] * len(ks)
    gid += 1
  starts = np.asarray(starts, dtype=np.int64)
  if len(starts) == 0:
    raise ValueError("no complete target segment in the training run")
  return {"Xf": cut_windows(xf, starts, n_win), "Xr": cut_windows(x, starts, n_win), "y": np.asarray(ys, dtype=np.int64),
          "groups": np.asarray(gs, dtype=np.int64), "starts": starts}


# --- stream (no MARK anywhere below) ----------------------------------------------------

def check_channels(Xf: np.ndarray, Xr: np.ndarray, starts: np.ndarray, n_win: int, fs: float, names: Sequence[str],
                   q: dict, check_sec: float) -> set:
  """Label-free channel check: the channels failing the channel tier on the stream windows that END within the first
  `check_sec` seconds (windows of the fixed clock; nothing but signal is used)."""
  sel = starts + n_win <= int(round(check_sec * fs))
  if sel.sum() == 0:
    return set()
  return channel_tier(Xf[sel], Xr[sel], names, q)


def predict_stream(model, mean, std, Xf: np.ndarray, kept_idx: Sequence[int], valid: np.ndarray, device: str,
                   n_classes: int) -> np.ndarray:
  """Class probabilities `(n, n_classes)` of the windows of the stream (NaN rows where the window tier rejected
  the window). Takes no MARK."""
  out = np.full((len(Xf), n_classes), np.nan)
  idx = np.flatnonzero(valid)
  if len(idx):
    out[idx] = predict_proba(model, normalise(Xf[idx][:, list(kept_idx)], mean, std), torch.device(device))
  return out


# --- scoring (the only place MARK is read) --------------------------------------------------

def decide_period(proba: np.ndarray, offsets_sec: np.ndarray, window_sec: float, threshold: float, n_target: int,
                  forced_allowed: bool) -> Optional[dict]:
  """Threshold rule on one period. `proba (k, K)` valid windows IN TIME ORDER (K >= n_target; columns after
  `n_target` are the rest class), `offsets_sec (k,)` window start minus period start.

  Cumulative mean over the windows; hit = first window whose cumulative-mean maximum over the first `n_target` classes
  is >= threshold (rest class excluded). Returns `{pred (class index), time_sec, forced}` or None: no window at all, or
  (without forcing) the threshold was never reached."""
  p = np.asarray(proba, dtype=np.float64)
  if len(p) == 0:
    return None
  cum = np.cumsum(p, axis=0) / np.arange(1, len(p) + 1)[:, None]
  tgt = cum[:, :n_target]
  hit = np.flatnonzero(tgt.max(axis=1) >= threshold - EPS)
  if len(hit):
    k = int(hit[0])
    return {"pred": int(tgt[k].argmax()), "time_sec": float(offsets_sec[k] + window_sec), "forced": 0}
  if not forced_allowed:
    return None
  k = len(p) - 1
  return {"pred": int(tgt[k].argmax()), "time_sec": float(offsets_sec[k] + window_sec), "forced": 1}


def score_stream(mark: np.ndarray, fs: float, starts: np.ndarray, proba: np.ndarray, valid: np.ndarray, n_win: int,
                 window_sec: float, skip_sec: float, threshold: float, n_classes: int, check_sec: float,
                 subject: str = "") -> pd.DataFrame:
  """Decisions per stimulus period and false activations per rest period (module docstring, item 5).

  `starts (n,)`, `proba (n, K)`, `valid (n,)` describe the fixed-clock windows of the stream; `mark` (the MARK channel of
  the test run) is used only here, to place the periods and to know the true label."""
  rest_class = n_classes == REST_CLASS_INDEX + 1
  rows = []
  L = int(STIM_SEC * fs)
  skip = int(round(skip_sec * fs))

  def eligible(a: int) -> np.ndarray:
    return np.flatnonzero((starts >= a + skip) & (starts + n_win <= a + L))

  for ci, code in enumerate(TARGETS):
    for o in event_onsets(mark, code):
      o = int(o)
      for kind, a in (("stimulus", o), ("rest", int(o - REST_SEC * fs))):
        if a < 0 or a + L > len(mark):
          continue
        el = eligible(a)
        ok = el[valid[el]]
        dec = decide_period(proba[ok], (starts[ok] - a) / fs, window_sec, threshold, len(TARGETS),
                            forced_allowed=(kind == "stimulus" and not rest_class))
        before = bool(a + L <= int(round(check_sec * fs)))
        if kind == "stimulus":
          pred = TARGETS[dec["pred"]] if dec else 0
          rows.append({"Subject": subject, "period": kind, "onset_sec": a / fs, "true": code, "pred": pred,
                       "correct": int(dec is not None and pred == code), "time_sec": dec["time_sec"] if dec else np.nan,
                       "forced": dec["forced"] if dec else 0, "missed": int(dec is None and len(ok) > 0),
                       "false_activation": 0, "n_windows": len(el), "n_rejected": int(len(el) - len(ok)),
                       "before_check": int(before), "window_sec": window_sec})
        else:
          rows.append({"Subject": subject, "period": kind, "onset_sec": a / fs, "true": 0,
                       "pred": TARGETS[dec["pred"]] if dec else 0, "correct": 0,
                       "time_sec": dec["time_sec"] if dec else np.nan, "forced": 0, "missed": 0,
                       "false_activation": int(dec is not None), "n_windows": len(el),
                       "n_rejected": int(len(el) - len(ok)), "before_check": int(before), "window_sec": window_sec})
  out = pd.DataFrame(rows, columns=DECISION_COLUMNS)
  return out.sort_values(["onset_sec", "period"]).reset_index(drop=True)


def summarize(dec: pd.DataFrame, subject: str, rest_class: bool, info: dict) -> dict:
  """One summary row (module docstring) from the decisions of a subject and run info (`window_sec`, `channels_kept`,
  `dropped_at_check`, `train_windows`, `val_acc`, `fallback`, `source`)."""
  st, rs = dec[dec["period"] == "stimulus"], dec[dec["period"] == "rest"]
  scored = st[(st["n_windows"] - st["n_rejected"]) > 0]            # periods with at least one valid window
  n = len(scored)
  decided = scored[scored["missed"] == 0]
  acc = float(scored["correct"].mean()) if n else np.nan
  t = float(decided["time_sec"].mean()) if len(decided) else np.nan
  scored_rs = rs[(rs["n_windows"] - rs["n_rejected"]) > 0]
  all_w = int(dec["n_windows"].sum())
  row = {"Subject": subject, "Trials": n, "Acc (%)": 100 * acc, "Time (s)": t,
         ("Missed (%)" if rest_class else "Forced (%)"):
           100 * float(scored["missed"].mean() if rest_class else scored["forced"].mean()) if n else np.nan,
         "ITR (bits/min)": itr_bits_per_min(acc, len(TARGETS), t + GAZE_SEC) if n and not np.isnan(t) else np.nan,
         "False act. (%)": 100 * float(scored_rs["false_activation"].mean()) if len(scored_rs) else np.nan,
         "Windows rejected (%)": 100 * float(dec["n_rejected"].sum()) / all_w if all_w else np.nan,
         "Window (s)": info["window_sec"], "Channels kept": info["channels_kept"],
         "Dropped at check": info["dropped_at_check"], "Train windows": info["train_windows"],
         "Val acc (%)": 100 * info["val_acc"], "Classes": 6 if rest_class else 5, "Rest periods": len(scored_rs),
         "Trials undecided": int(len(st) - n), "Trials before check": int(scored["before_check"].sum()),
         "Fallback": int(info["fallback"]), "Data source": info["source"]}
  return row


# --- one subject --------------------------------------------------------------------------

def resolve_device(name: str) -> str:
  if name == "auto":
    return "cuda" if torch.cuda.is_available() else "cpu"
  if name == "cuda" and not torch.cuda.is_available():
    raise RuntimeError("--device cuda requested but CUDA is not available")
  return name


def run_window_length(tr: tuple, te: tuple, window_sec: float, stride_sec: float, sos: np.ndarray, names: list, q: dict,
                      rest_class: bool, args, device: str, subject: str) -> dict:
  """Train and replay at one window length: returns the fitted bundle, stream windows, probabilities and masks."""
  x_tr, mark_tr, fs = tr
  x_te, _mark_te, _ = te                                  # the test MARK is NOT used here (scoring only)
  n_win, stride = int(round(window_sec * fs)), int(round(stride_sec * fs))
  ts = training_windows(x_tr, mark_tr, fs, sos, n_win, stride, rest_class)
  drop_train = channel_tier(ts["Xf"], ts["Xr"], names, q)
  starts, Wf, Wr = replay_windows(x_te, sos, n_win, stride)         # stateful causal replay, fixed clock
  drop_check = check_channels(Wf, Wr, starts, n_win, fs, names, q, args.check_sec) - drop_train
  kept = [c for c in names if c not in drop_train and c not in drop_check]
  if not kept:
    raise ValueError(f"{subject}: every channel is dropped (training gate {sorted(drop_train)}, check {sorted(drop_check)})")
  kept_idx = [names.index(c) for c in kept]
  ok_tr = window_tier(ts["Xf"], ts["Xr"], kept_idx, q)
  X, y, g = ts["Xf"][ok_tr][:, kept_idx], ts["y"][ok_tr], ts["groups"][ok_tr]
  n_classes = REST_CLASS_INDEX + 1 if rest_class else len(TARGETS)
  if len(np.unique(y)) < n_classes:
    raise ValueError(f"{subject}: training windows hold {len(np.unique(y))} classes, expected {n_classes}")
  fit = fit_network(X, y, g, model_factory(args.model, fs), seed=args.seed, device=device, augment=not args.no_augment,
                    max_epochs=args.max_epochs, patience=args.patience)
  valid = window_tier(Wf, Wr, kept_idx, q)
  proba = predict_stream(fit["model"], fit["mean"], fit["std"], Wf, kept_idx, valid, device, n_classes)
  return {"fit": fit, "starts": starts, "proba": proba, "valid": valid, "n_win": n_win, "kept": kept,
          "dropped_check": sorted(drop_check), "dropped_train": sorted(drop_train), "n_train": int(len(y)),
          "n_classes": n_classes}


def run_subject(subject: str, args, cfg: dict, q: dict, raw_dir: Path, device: str, sos_of) -> tuple:
  """`(summary_row, decisions)` of one subject."""
  loaded = {}
  for role, sess in (("train", args.train_session), ("test", args.test_session)):
    loaded[role] = load_session(ebr_parser.resolve_recording_path(raw_dir, subject, sess), cfg["channels"]["scalp"],
                                cfg["channels"]["mark_channel"])
  (x_tr, mark_tr, fs), (x_te, mark_te, fs_te) = loaded["train"], loaded["test"]
  if fs != fs_te:
    raise ValueError(f"{subject}: sampling rates differ, {fs} vs {fs_te}")
  sos = sos_of(fs)
  names = list(cfg["channels"]["scalp"])
  fallback = False
  w = args.window_sec
  for attempt in (0, 1):
    res = run_window_length((x_tr, mark_tr, fs), (x_te, mark_te, fs), w, args.stride_sec, sos, names, q, args.rest_class,
                            args, device, subject)
    if res["fit"]["val_acc"] * 100 >= args.min_val_acc or attempt == 1 or w == args.fallback_window_sec:
      break
    print(f"  [!] {subject}: validation accuracy {100 * res['fit']['val_acc']:.1f} % < {args.min_val_acc:g} % at "
          f"{w:g} s windows: fallback to {args.fallback_window_sec:g} s")
    w, fallback = args.fallback_window_sec, True
  dec = score_stream(mark_te, fs, res["starts"], res["proba"], res["valid"], res["n_win"], w, args.skip_sec,
                     args.threshold, res["n_classes"], args.check_sec, subject)
  src = f"{args.train_session}->{args.test_session} ({'causal-filtered stream replay, shared quality tier w/o guard'}), session files"
  info = {"window_sec": w, "channels_kept": len(res["kept"]), "dropped_at_check": len(res["dropped_check"]),
          "train_windows": res["n_train"], "val_acc": res["fit"]["val_acc"], "fallback": fallback, "source": src}
  row = summarize(dec, subject, args.rest_class, info)
  print(f"  {subject}: window {w:g} s, channels kept {res['kept']}, dropped at check {res['dropped_check']}, "
        f"training windows {res['n_train']}, val acc {100 * res['fit']['val_acc']:.1f} %, best epoch "
        f"{res['fit']['best_epoch']}/{res['fit']['epochs_run']} epochs")
  return row, dec


# --- CLI ------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--train-session", default="OO", help="training run (file stem), default OO")
  p.add_argument("--test-session", default="mOO", help="test run replayed as a stream, default mOO")
  p.add_argument("--model", default="ccnn", choices=sorted(set(MODELS) | set(ALIASES)), help="network (default ccnn)")
  p.add_argument("--window-sec", type=float, default=0.5)
  p.add_argument("--stride-sec", type=float, default=0.25)
  p.add_argument("--skip-sec", type=float, default=0.5, help="windows of a period starting before this offset are not used")
  p.add_argument("--threshold", type=float, default=0.6)
  p.add_argument("--rest-class", action="store_true", help="6 classes: rest windows from the 5 s before each target")
  p.add_argument("--check-sec", type=float, default=30.0, help="label-free channel check on the first seconds of the test stream")
  p.add_argument("--fallback-window-sec", type=float, default=1.0)
  p.add_argument("--min-val-acc", type=float, default=50.0, help="validation accuracy (%%) below which the fallback runs")
  p.add_argument("--quality-source", choices=bw.SOURCES, default=None,
                 help="filtered | raw | both (default: config quality.source)")
  p.add_argument("--subjects", nargs="+", default=None, help="default: every S<k> folder of the raw directory")
  p.add_argument("--max-epochs", type=int, default=150)
  p.add_argument("--patience", type=int, default=25)
  p.add_argument("--no-augment", action="store_true")
  p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
  p.add_argument("--seed", type=int, default=42)
  p.add_argument("--tag", default=None, help="file suffix (default: <model>_<5|6>class)")
  p.add_argument("--out-dir", type=Path, default=Path("reports/pseudo_online"))
  p.add_argument("--raw-dir", type=Path, default=None, help="default: config paths.data_raw_dir")
  p.add_argument("--config", type=Path, default=bw.DEFAULT_CONFIG)
  p.add_argument("--resume", action="store_true", help="skip subjects whose part files exist in --out-dir")
  return p


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = build_parser().parse_args(argv)
  try:
    cfg = bw.load_build_config(args.config)
    q = bw.quality_params_from_config(cfg)
    if args.quality_source:
      q["source"] = args.quality_source
  except (OSError, ValueError) as exc:
    print(f"[x] Config: {exc}")
    return 1
  pre = cfg["preprocessing"]
  raw_dir = args.raw_dir or ROOT / cfg.get("paths", {}).get("data_raw_dir", "data/raw")
  if not Path(raw_dir).is_dir():
    print(f"[x] Raw folder not found: {raw_dir}")
    return 1
  subjects = args.subjects or sorted((p.name for p in Path(raw_dir).iterdir()
                                      if p.is_dir() and bw.SUBJECT_PATTERN.fullmatch(p.name)), key=lambda s: int(s[1:]))
  if not subjects:
    print(f"[x] No subject folders matching ^S\\d+$ in {raw_dir}")
    return 1
  tag = args.tag or f"{args.model}_{6 if args.rest_class else 5}class"
  device = resolve_device(args.device)
  if device == "cuda":                                    # same seed -> same training trajectory (P24 verify)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
  warn = paradigm_warning(args.train_session, args.test_session)
  print(f"Pseudo-online: {args.model}, {6 if args.rest_class else 5} classes, train {args.train_session} -> test "
        f"{args.test_session}, window {args.window_sec:g} s, stride {args.stride_sec:g} s, skip {args.skip_sec:g} s, "
        f"threshold {args.threshold:g}, device {device}, seed {args.seed}")
  print(f"Filter: causal Butterworth {pre['lowcut_hz']:g}-{pre['highcut_hz']:g} Hz order {pre['filter_order']} + notch "
        f"{pre['notch_hz']} Hz Q {pre['notch_q']:g}, stateful (zi = sosfilt_zi * x[0]); quality source {q['source']}, "
        f"limits {limits_of(q)}, channel fail fraction {q['channel_fail_fraction']:g}, no artifact guard (online)")
  print(f"Data source: {args.train_session}.ebr (train) and {args.test_session}.ebr (test stream), {subjects}")
  if warn:
    print(warn)
  sos_of = lambda fs: design_sos(fs, float(pre["lowcut_hz"]), float(pre["highcut_hz"]), int(pre["filter_order"]),
                                 None if pre["notch_hz"] is None else float(pre["notch_hz"]), float(pre["notch_q"]))
  out = Path(args.out_dir)
  out.mkdir(parents=True, exist_ok=True)
  rows, decs = [], []
  for s in subjects:
    pr, pd_ = out / f"summary_{tag}.part_{s}.csv", out / f"decisions_{tag}.part_{s}.csv"
    if args.resume and pr.is_file() and pd_.is_file():
      print(f"[=] {s}: part files found, skipped (--resume)")
      rows.append(pd.read_csv(pr).iloc[0].to_dict())
      decs.append(pd.read_csv(pd_))
      continue
    t0 = time.time()
    try:
      row, dec = run_subject(s, args, cfg, q, Path(raw_dir), device, sos_of)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    row["Seconds"] = round(time.time() - t0, 1)
    print(f"  {s}: {row['Seconds']} s")
    pd.DataFrame([row]).to_csv(pr, index=False)
    dec.to_csv(pd_, index=False)
    rows.append(row)
    decs.append(dec)
  if not rows:
    print("[x] no subject finished")
    return 1
  summ = pd.DataFrame(rows)
  num = summ.select_dtypes("number").columns.difference(["Window (s)", "Classes"])
  mean = {c: summ[c].mean() for c in num}
  mean.update({"Subject": "Mean", "Window (s)": summ["Window (s)"].iloc[0], "Classes": summ["Classes"].iloc[0],
               "Data source": summ["Data source"].iloc[0]})
  summ = pd.concat([summ, pd.DataFrame([mean])], ignore_index=True)
  summ.to_csv(out / f"summary_{tag}.csv", index=False, float_format="%.6g")
  pd.concat(decs, ignore_index=True).to_csv(out / f"decisions_{tag}.csv", index=False, float_format="%.6g")
  for f in out.glob(f"*_{tag}.part_*.csv"):
    f.unlink()
  show = [c for c in summ.columns if c not in ("Data source",)]
  print(summ[show].to_string(index=False, float_format=lambda v: f"{v:.2f}"))
  print(f"Saved: {out / ('summary_' + tag + '.csv')} and {out / ('decisions_' + tag + '.csv')}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
