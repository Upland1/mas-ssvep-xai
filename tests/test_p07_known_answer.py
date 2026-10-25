"""P07 independent known-answer tests (synthetic-tester): two-tier gate boundaries, dropped-channel handling,
consumer arity (PF-08), one shared decision (PF-10), config montage (PF-05), ungated quality summary, CSV schema.

Expected values come from the roadmap (P07 tasks 1-6) and analytic construction, not from the builders' code.
Synthetic arrays only (fixed seeds); fs 250 (Era A).
"""

import ast
from pathlib import Path
import re

import numpy as np
import pandas as pd
import yaml

from scripts.benchmarks.feature_based import benchmark_n_subjects as bns
from scripts.exploration import visualize_data as vd
from scripts.preprocessing import run_preprocessing as rp
from src.io.channels import resolve_channel_names
from src.models.classical import benchmark_runner as br
from src.preprocessing.signal import quality_check as qc
from tests.p05_synth import write_subject
from tests.test_p02_preprocessing_smoke import _signal, _write_ebr

ROOT = Path(__file__).resolve().parents[1]
NAMES = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
LIM = dict(vpp_min=5.0, vpp_max=120.0, std_min=1.0, std_max=35.0)
T = 64


def _sq(amp, n=T):
  return amp * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)


def _good(n):
  w = np.zeros((n, 8, T))
  w[:] = _sq(10.0)                       # vpp 20, std 10: inside 5-120 / 1-35
  return w


def test_tier1_boundary_at_100_windows():
  """Roadmap P07.1: dropped only if it fails in > 50 % of windows. 100 windows: channel 3 (PO4) fails in exactly 50,
  channel 5 (O1) in 51, channel 1 (PO3) in 49 -> only O1 dropped. Exact. A `>=` mutant also drops PO4."""
  w = _good(100)
  w[:50, 3] = 0.0
  w[:51, 5] = 0.0
  w[:49, 1] = 0.0
  assert qc.identify_noisy_channels(w, NAMES, LIM, 0.5) == ["O1"]
  out = qc.apply_artifact_quality_pipeline(w, np.zeros(100), NAMES, verbose=False)
  assert out["channels_dropped"] == ["O1"]
  assert out["channel_stats"]["PO4"]["fail_fraction"] == 0.5 and out["channel_stats"]["O1"]["fail_fraction"] == 0.51


def test_tier2_ignores_bad_samples_on_dropped_channel_only():
  """Roadmap P07.1 (tier 1 = subject, tier 2 = windows on surviving channels). PO8 is bad in every window (dropped),
  so windows bad ONLY on PO8 must stay valid; a bad window on kept Oz (4) is rejected. Exact.
  A tier 2 that judges the dropped channel rejects every window."""
  w = _good(10)
  w[:, 4] = 0.0
  w[4, 6] = _sq(500.0)
  out = qc.apply_artifact_quality_pipeline(w, np.arange(10), NAMES, **LIM, verbose=False)
  assert out["channels_dropped"] == ["PO8"]
  assert out["valid_mask"].tolist() == [1, 1, 1, 1, 0, 1, 1, 1, 1, 1]


def test_config_restores_po7_in_montage_order():
  """PF-05 / roadmap P07.3: configs/pipeline_config.yaml scalp = full 8-channel montage in order, excluded empty;
  resolve_channel_names(8) equals it and (7) equals it without PO7, in order; other counts give None."""
  cfg = yaml.safe_load((ROOT / "configs" / "pipeline_config.yaml").read_text())
  assert cfg["channels"]["scalp"] == NAMES and cfg["channels"]["excluded"] == []
  assert resolve_channel_names(8) == NAMES
  assert resolve_channel_names(7) == [c for c in NAMES if c != "PO7"]
  assert resolve_channel_names(0) is None and resolve_channel_names(1) is None


def test_every_extractor_call_unpacks_four_values():
  """PF-08: each assignment from extract_fbcca_features / extract_fbcsp_features / extract_continuous_psd_features in
  src/, scripts/ must unpack exactly 4 targets. Static AST scan (the roadmap's 4-value contract); exact.
  A consumer still unpacking 3 values (or assigning the tuple to one name) fails."""
  fn = {"extract_fbcca_features", "extract_fbcsp_features", "extract_continuous_psd_features"}
  bad, seen = [], 0
  for base in ("src", "scripts"):
    for p in (ROOT / base).rglob("*.py"):
      for node in ast.walk(ast.parse(p.read_text())):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
          f = node.value.func
          name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
          if name in fn:
            seen += 1
            t = node.targets[0]
            if not (isinstance(t, ast.Tuple) and len(t.elts) == 4):
              bad.append(f"{p.relative_to(ROOT)}:{node.lineno}")
  assert seen >= 3 and bad == []


def test_blocks_share_one_gate_decision(tmp_path, monkeypatch):
  """PF-10: preparing a subject runs the two-tier pipeline once without `precomputed`; every later call (PSD, FBCCA,
  FBCSP blocks) reuses it. Exact count 1. Gating each extractor separately gives >= 3 fresh decisions."""
  import src.features.ssvep.window_mask as wm
  write_subject(tmp_path, "S01", n_trials=2, seed=3, bad_channels=("POz",))
  calls = []
  real = qc.apply_artifact_quality_pipeline

  def spy(*a, **k):
    calls.append(k.get("precomputed") is None)
    return real(*a, **k)
  monkeypatch.setattr(qc, "apply_artifact_quality_pipeline", spy)
  monkeypatch.setattr(wm, "apply_artifact_quality_pipeline", spy, raising=False)
  b = br.prepare_subject(tmp_path, "S01")
  assert b["channels_dropped"] == ["POz"]
  assert sum(calls) == 1 and len(calls) >= 2


def test_summarize_window_quality_sees_rejected_windows(tmp_path, capsys):
  """P02 carry-forward / PF-07: the preprocessing log summary is fed the UNGATED windows. A 400 uV spike trial gives
  observed Vpp max >= 400 (the gate's limit is 200) and a non-zero rejected count; the saved clean windows never
  exceed the gate. Exact bounds. Gated input would show max < 200 and 0 rejected."""
  _write_ebr(tmp_path / "raw" / "S03" / "OO.ebr", _signal(5, seed=4, spike_trial=1))
  assert rp.main(["--raw-dir", str(tmp_path / "raw"), "--processed-dir", str(tmp_path / "proc"),
                  "--no-figures", "--no-channel-drop"]) == 0
  out = capsys.readouterr().out
  i = out.index("ungated windows")
  m = re.search(r"Vpp observed [\d.]+ / [\d.]+ / ([\d.]+) uV", out[i:i + 700])
  assert m and float(m.group(1)) >= 400.0
  assert re.search(r"(\d+)/(\d+) windows valid, (\d+) rejected", out[i:i + 200]).group(3) != "0"
  X = np.load(tmp_path / "proc" / "S03" / "X_time_windows.npy")
  assert (X.max(-1) - X.min(-1)).max() < 200.0


def test_visualize_runs_on_8_channel_tree(tmp_path):
  """PF-08 / PF-05: visualize_data (a consumer) runs on an 8-channel folder, names by channel count; exit 0."""
  write_subject(tmp_path / "proc", "S01", n_trials=1, seed=5, n_ch=8)
  assert vd.main(["--subject", "S01", "--no-figures", "--processed-dir", str(tmp_path / "proc")]) == 0


def test_n_subjects_csv_rows_and_mean_blank_cells(tmp_path):
  """Roadmap P07.6 / 02_REQUIREMENTS section 6: one row per discovered subject plus Mean; Mean row has blank
  non-accuracy cells; Channels Kept is the count (8-channel subject with PO7 and PO8 noisy -> 6), Channels Dropped the
  names ('none' if empty); Clean + Rejected = stimulus windows (50); accuracies in [0, 100]."""
  write_subject(tmp_path / "p", "S01", n_trials=2, seed=1, n_ch=8, bad_channels=("PO7", "PO8"))
  write_subject(tmp_path / "p", "S02", n_trials=2, seed=2)
  assert bns.main(["--data-root", str(tmp_path / "p"), "--reports-dir", str(tmp_path / "r")]) == 0
  df = pd.read_csv(tmp_path / "r" / "n_subjects_benchmark.csv")
  assert df["Subject"].tolist() == ["S01", "S02", "Mean"]
  r = df.iloc[0]
  assert r["Channels Kept"] == 6 and set(r["Channels Dropped"].split()) == {"PO7", "PO8"}
  assert df.iloc[1]["Channels Kept"] == 7 and df.iloc[1]["Channels Dropped"] == "none"
  assert df[["Clean Windows", "Rejected Windows"]].iloc[:2].sum(axis=1).tolist() == [50, 50]
  assert df.iloc[2][["Channels Kept", "Channels Dropped", "Clean Windows", "Rejected Windows"]].isna().all()
  assert df[["1.0s Acc (%)", "2.0s Smoothed (%)"]].iloc[:2].stack().between(0, 100).all()
