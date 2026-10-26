"""Size of the trial leak per subject (P11.4, R1/PF-01, R8/PF-02): the flagship under both splitters.

Data source: legacy folders <data-root>/<S>/ (P02, OO session), stimulus windows only, two-tier quality
gate once per subject (vpp 5-120 uV, std 1-35 uV, channel dropped if it fails in > 50 % of the windows; R5
per-script gate). Model: the P05 flagship, FBCSP m = 1 (in-fold, R2/PF-11) + FBCCA -> StandardScaler ->
Shrinkage-LDA (lsqr, auto), fs 250 (legacy PF-04). The SAME arrays go through (a) the legacy window-level
StratifiedKFold(5, shuffle, 42) with the i%5 smoothing (leaky) and (b) StratifiedGroupKFold(5, shuffle, 42)
over reconstructed trial ids (R1). The REPORTED 2.0 s rule on legacy folders is i%5 (R8 legacy-folder clause)
in both; the trial-reset rule is given as the PF-02 diagnostic column, so the effect of the smoothing rule
is separated from that of the split.

Output: <reports-dir>/cv_leakage_demo.csv (Subject, Clean, Approximate ids, 1.0s leaky, 1.0s grouped,
Delta 1.0, 2.0s leaky (mod5), 2.0s grouped (mod5, REPORTED), Delta 2.0, 2.0s grouped (trial, PF-02 diagnostic); Mean row) and a
.meta.txt. Network section (no training): if the frozen P10 A/B <reports-dir>/legacy_leaky/
augmentation_ab_<model>.csv and the P11 <reports-dir>/augmentation_ab_<model>.csv exist, per-subject
OFF/ON leaky vs grouped deltas are printed and saved to <reports-dir>/cv_leakage_demo_networks.csv.
"""

import argparse
import contextlib
import io
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


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

from src.features.ssvep.spectral_power import LEGACY_FS_HZ  # noqa: E402
from src.models.classical.benchmark_runner import (  # noqa: E402
  discover_subjects, legacy_header_lines, load_config, prepare_subject)
from src.models.classical.feature_spaces import benchmark_spaces  # noqa: E402
from src.models.classical.legacy_eval import (  # noqa: E402
  CV_LABEL, GROUPED_CV_LABEL, GROUPED_MOD5_SMOOTH_LABEL, SEED, SMOOTH_LABEL, TRIAL_SMOOTH_LABEL, accuracies, oof_space, splits_for)
from src.models.classical.sklearn_models import get_sklearn_model_suite  # noqa: E402

DEFAULT_CONFIG = ROOT / "configs" / "pipeline_config.yaml"
MODEL = "Shrinkage-LDA lsqr"
SPACE = "FBCSP + FBCCA (in-fold)"
COLUMNS = ["Subject", "Clean", "Approximate ids", "1.0s leaky (%)", "1.0s grouped (%)", "Delta 1.0 (pp)",
           "2.0s leaky mod5 (%)", "2.0s grouped mod5 REPORTED (%)", "Delta 2.0 (pp)",
           "2.0s grouped trial DIAGNOSTIC (%)"]
NET_MODELS = ("eegnet", "compact_cnn", "shallow_conv_net")
NET_COLUMNS = ["Model", "Subject", "1.0s OFF leaky", "1.0s OFF grouped", "Delta OFF 1.0", "1.0s ON leaky",
               "1.0s ON grouped", "Delta ON 1.0", "Augmentation gain 1.0 leaky", "Augmentation gain 1.0 grouped"]


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--subjects", nargs="*", default=None, help="subject folders (default: discover S<digits> folders)")
  p.add_argument("--data-root", type=Path, default=None,
                 help="folder with <S>/ arrays (default: <root>/ + paths.data_processed_dir)")
  p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
  p.add_argument("--reports-dir", type=Path, default=None, help="default: <root>/reports")
  p.add_argument("--m", type=int, default=1, help="CSP components per side (default 1)")
  p.add_argument("--fs", type=float, default=LEGACY_FS_HZ, help=f"feature sampling rate (default {LEGACY_FS_HZ:g}, legacy PF-04)")
  p.add_argument("--seed", type=int, default=SEED, help=f"CV shuffle seed (default {SEED})")
  return p


def _rel(path: Path) -> str:
  try:
    return str(Path(path).resolve().relative_to(ROOT))
  except ValueError:
    return str(path)


def leak_row(b: dict, subject: str, m: int = 1, seed: int = SEED) -> dict:
  """Flagship accuracies of one prepared subject under both splitters (same arrays, same seed)."""
  y, ids = b["y"], b["trial_ids"]
  space = [s for s in benchmark_spaces(b, m) if s.name == SPACE][0]
  model = {MODEL: get_sklearn_model_suite(seed)[MODEL]}
  out = {}
  for cv in ("legacy", "grouped"):
    res, errs = oof_space(space, b["subbands"], y, model, seed, splits_for(cv, y, ids, seed))
    if errs:
      raise RuntimeError(f"{subject} {cv}: {errs[MODEL]}")
    out[cv] = res[MODEL]
  a1_l, a2_l = accuracies(y, out["legacy"]["pred"], out["legacy"]["scores"], None, "mod5")
  a1_g, a2_g = accuracies(y, out["grouped"]["pred"], out["grouped"]["scores"], None, "mod5")
  _, a2_gt = accuracies(y, out["grouped"]["pred"], out["grouped"]["scores"], ids, "trial")
  r = lambda v: round(100 * v, 2)  # noqa: E731
  return {"Subject": subject, "Clean": b["n_clean"], "Approximate ids": "yes" if b["trial_ids_approximate"] else "no",
          "1.0s leaky (%)": r(a1_l), "1.0s grouped (%)": r(a1_g), "Delta 1.0 (pp)": round(r(a1_g) - r(a1_l), 2),
          "2.0s leaky mod5 (%)": r(a2_l), "2.0s grouped mod5 REPORTED (%)": r(a2_g),
          "Delta 2.0 (pp)": round(r(a2_g) - r(a2_l), 2), "2.0s grouped trial DIAGNOSTIC (%)": r(a2_gt)}


def with_mean_row(rows: list) -> pd.DataFrame:
  df = pd.DataFrame(rows, columns=COLUMNS)
  mean = {c: "" for c in COLUMNS}
  mean["Subject"] = "Mean"
  for c in COLUMNS[3:7] + COLUMNS[7:10]:
    mean[c] = round(float(df[c].mean()), 2)
  return pd.concat([df, pd.DataFrame([mean], columns=COLUMNS)], ignore_index=True)


def network_section(reports: Path) -> Optional[pd.DataFrame]:
  """Per-subject OFF/ON leaky (frozen P10, reports/legacy_leaky) vs grouped (P11) from the A/B CSVs; None if no pair exists."""
  rows = []
  for model in NET_MODELS:
    old = Path(reports) / "legacy_leaky" / f"augmentation_ab_{model}.csv"
    new = Path(reports) / f"augmentation_ab_{model}.csv"
    if not (old.is_file() and new.is_file()):
      print(f"  [-] network section: {model} skipped ({'no frozen P10 CSV' if not old.is_file() else 'no P11 CSV yet'})")
      continue
    a = pd.read_csv(old).set_index("Subject")
    g = pd.read_csv(new).set_index("Subject")
    for s in [s for s in g.index if s in a.index]:
      rows.append({"Model": model, "Subject": s,
                   "1.0s OFF leaky": a.loc[s, "1.0s OFF (%)"], "1.0s OFF grouped": g.loc[s, "1.0s OFF (%)"],
                   "Delta OFF 1.0": round(g.loc[s, "1.0s OFF (%)"] - a.loc[s, "1.0s OFF (%)"], 2),
                   "1.0s ON leaky": a.loc[s, "1.0s ON (%)"], "1.0s ON grouped": g.loc[s, "1.0s ON (%)"],
                   "Delta ON 1.0": round(g.loc[s, "1.0s ON (%)"] - a.loc[s, "1.0s ON (%)"], 2),
                   "Augmentation gain 1.0 leaky": round(a.loc[s, "1.0s ON (%)"] - a.loc[s, "1.0s OFF (%)"], 2),
                   "Augmentation gain 1.0 grouped": round(g.loc[s, "1.0s ON (%)"] - g.loc[s, "1.0s OFF (%)"], 2)})
  return pd.DataFrame(rows, columns=NET_COLUMNS) if rows else None


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
    print(f"[-] No subject folders with arrays in {_rel(processed)}")
    return 1
  t0 = time.time()
  print(f"Data source: legacy windows, {_rel(processed)}/<S>/ (P02, OO session), stimulus windows only; "
        f"subjects {', '.join(subjects)}")
  rows, header = [], None
  for s in subjects:
    buf = io.StringIO()
    try:
      with contextlib.redirect_stdout(buf):
        b = prepare_subject(processed, s, None, args.fs)
    except (FileNotFoundError, ValueError) as exc:
      print(f"[-] Skipping {s}: {exc}")
      continue
    header = header or legacy_header_lines(args.fs, b["thresholds"], args.seed, "see columns", "see columns",
                                           b["fbcca_channels"], b["channel_fail_fraction"])
    rep = b["trial_block_report"]
    r = leak_row(b, s, args.m, args.seed)
    rows.append(r)
    print(f"[+] {s}: {b['n_clean']} clean, trial blocks {sorted(set(n for v in rep['blocks'].values() for n in v))}, "
          f"ids {'APPROXIMATE' if rep['approximate'] else 'exact'}; 1.0 s leaky {r['1.0s leaky (%)']:.2f} -> grouped "
          f"{r['1.0s grouped (%)']:.2f} ({r['Delta 1.0 (pp)']:+.2f} pp); 2.0 s leaky mod5 {r['2.0s leaky mod5 (%)']:.2f} -> "
          f"grouped mod5 REPORTED {r['2.0s grouped mod5 REPORTED (%)']:.2f} ({r['Delta 2.0 (pp)']:+.2f} pp); "
          f"trial-reset DIAGNOSTIC {r['2.0s grouped trial DIAGNOSTIC (%)']:.2f}")
  if not rows:
    print("[-] No subject evaluated")
    return 1
  df = with_mean_row(rows)
  csv = reports / "cv_leakage_demo.csv"
  csv.parent.mkdir(parents=True, exist_ok=True)
  df.to_csv(csv, index=False)
  meta = (header or []) + [
    f"leaky: {CV_LABEL}; smoothing: {SMOOTH_LABEL}",
    f"grouped: {GROUPED_CV_LABEL}; reported 2.0 s: {GROUPED_MOD5_SMOOTH_LABEL}",
    f"diagnostic column: {TRIAL_SMOOTH_LABEL}",
    f"model: {SPACE} -> {MODEL}; same arrays, same seed {args.seed} in both columns",
    f"data source: legacy windows, {_rel(processed)}/<S>/",
    "approximate ids: " + (" ".join(r["Subject"] for r in rows if r["Approximate ids"] == "yes") or "none")]
  csv.with_suffix(".meta.txt").write_text("\n".join(meta) + "\n")
  print("\n" + df.to_string(index=False))
  mean = df.iloc[-1]
  print(f"\nMean: 1.0 s {mean['1.0s leaky (%)']:.2f} -> {mean['1.0s grouped (%)']:.2f} ({mean['Delta 1.0 (pp)']:+.2f} pp); "
        f"2.0 s {mean['2.0s leaky mod5 (%)']:.2f} -> {mean['2.0s grouped mod5 REPORTED (%)']:.2f} ({mean['Delta 2.0 (pp)']:+.2f} pp); "
        f"runtime {time.time() - t0:.0f} s")
  print(f"Saved: {_rel(csv)}")
  net = network_section(reports)
  if net is not None:
    ncsv = reports / "cv_leakage_demo_networks.csv"
    net.to_csv(ncsv, index=False)
    print("\nNetworks (no training; frozen P10 leaky vs P11 grouped A/B):\n" + net.to_string(index=False))
    print(f"Saved: {_rel(ncsv)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
