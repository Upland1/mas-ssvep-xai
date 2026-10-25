"""P07 tests (ml-engineer): extractors on the two-tier gate (4 return values, one decision, names after a drop),
consumers, `benchmark_n_subjects`. Synthetic data only (tests/p05_synth.py, fixed seeds); fs 250 as in Era A.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks.feature_based import benchmark_5_subjects as b5
from scripts.benchmarks.feature_based import benchmark_harmonic_fbcca as bhf
from scripts.benchmarks.feature_based import benchmark_n_subjects as bns
from scripts.evaluation import evaluate_confusion_matrix as ecm
from src.features.ssvep import fbcca_extraction as fb
from src.features.ssvep import fbcsp_extraction as csp
from src.features.ssvep.harmonic_psd import VISUAL_CLUSTER
from src.features.ssvep.psd_extraction import continuous_psd_freqs, extract_continuous_psd_features
from src.features.ssvep.window_mask import (
  GATE_THRESHOLDS, NO_CHANNEL_DROP, P05_MASK_THRESHOLDS, resolve_window_mask)
from src.io.channels import FULL_MONTAGE, resolve_channel_names, subject_channel_names
from src.models.classical.benchmark_runner import prepare_subject
from src.models.classical.feature_spaces import build_feature_blocks
from tests.p05_synth import FS, SCALP, keep_all, make_windows, write_subject

ROOT = Path(__file__).resolve().parents[1]
T = 256


def _noisy(n_trials=2, seed=0, bad=("POz",), names=SCALP):
  """Synthetic stimulus windows (n, 7, T) where the channels in `bad` carry a 400 uV-Vpp square wave in every window."""
  X, y = make_windows(n_trials=n_trials, seed=seed)
  X = X.copy()
  for c in bad:
    X[:, list(names).index(c)] += 200.0 * np.sign(np.sin(2 * np.pi * 7 * np.arange(T) / FS))
  return X, y


# --- extractors: arity, one decision, names after a drop ---------------------------------------

def test_extractors_return_four_values_with_one_shared_decision():
  """PF-08 / PF-10 known answer: PSD, FBCCA and FBCSP each return exactly 4 values; with POz noisy in every window
  (tier 1 drops it) and one artefact on PO3 in window 7 (tier 2 rejects it) all three give the same `valid_mask`
  (49 of 50 windows) and the same `channels_kept` (6 names, POz absent); an artefact on the dropped POz in window 9
  does not reject that window. PSD has 6 * 30 columns."""
  X, y = _noisy(bad=("POz",), seed=1)
  X[7, SCALP.index("PO3")] += 300.0 * np.sign(np.sin(np.arange(T)))
  outs = [extract_continuous_psd_features(X, y, SCALP), fb.extract_fbcca_features(X, y, SCALP),
          csp.extract_fbcsp_features(X, y, SCALP, m=1)]
  assert all(len(o) == 4 for o in outs)
  masks = [o[2] for o in outs]
  assert all(np.array_equal(masks[0], m) for m in masks[1:])
  assert masks[0].sum() == len(X) - 1 and masks[0][7] == 0 and masks[0][9] == 1
  for _, yc, _, rep in outs:
    assert len(yc) == len(X) - 1
    assert rep["channels_kept"] == [c for c in SCALP if c != "POz"] and rep["channels_dropped"] == ["POz"]
    assert rep["channels_kept_idx"].tolist() == [0, 2, 3, 4, 5, 6]
  assert outs[0][0].shape == (len(X) - 1, 6 * 30) and outs[1][0].shape == (len(X) - 1, 5)
  assert outs[2][0].shape == (len(X) - 1, 50)


def test_psd_columns_follow_kept_names_after_a_middle_drop():
  """PF-06 known answer: a 20 uV on-bin tone (bin k = 10) only in Oz on top of N(0, 3) noise; POz (a middle channel)
  is dropped, so Oz sits at kept position 4: the PSD argmax is column 4 * 30 + (k - 6) = 124 and `channels_kept`
  names it; the positional layout of the input (Oz at 5 -> column 154) is the mutant."""
  rng = np.random.default_rng(3)
  tt = np.arange(T) / FS
  X = rng.normal(0, 3.0, (30, 7, T))
  X[:, SCALP.index("Oz")] += 20.0 * np.sin(2 * np.pi * 10 * FS / T * tt)
  X[:, SCALP.index("POz")] += 200.0 * np.sign(np.sin(2 * np.pi * 7 * tt))
  P, _, m, rep = extract_continuous_psd_features(X, np.repeat(np.arange(101, 106), 6), SCALP)
  kept = rep["channels_kept"]
  assert kept == ["PO3", "PO4", "PO8", "O1", "Oz", "O2"] and m.all()
  assert int(np.argmax(P.mean(axis=0))) == kept.index("Oz") * 30 + 4 == 124
  assert int(np.argmax(P.mean(axis=0))) != SCALP.index("Oz") * 30 + 4


def test_blocks_after_dropping_a_cluster_channel_use_the_remaining_names():
  """PF-06 / PF-10 known answer: PO8 (visual cluster member) noisy in every window -> dropped; the harmonic PSD uses
  O1, Oz, O2 only (3 * 8 = 24 columns), the FBCCA input of `fbcca_channels=VISUAL_CLUSTER` is O1, Oz, O2, the FBCSP
  sub-band windows have 6 channels, and every block has the same rows. Dropping a non-cluster channel (PO3) leaves the
  4-channel cluster intact (32 columns)."""
  X, y = _noisy(bad=("PO8",), seed=2)
  b = build_feature_blocks(X, y, SCALP, fbcca_channels=VISUAL_CLUSTER)
  assert b["channels_dropped"] == ["PO8"] and b["fbcca_channels"] == ["O1", "Oz", "O2"]
  assert b["harmonic"].shape == (len(X), 24) and b["subbands"].shape[2] == 6 and b["psd"].shape[1] == 6 * 30
  assert all(len(b[k]) == len(X) for k in ("y", "psd", "harmonic", "fbcca", "subbands"))
  X3, y3 = _noisy(bad=("PO3",), seed=2)
  b3 = build_feature_blocks(X3, y3, SCALP, fbcca_channels=VISUAL_CLUSTER)
  assert b3["channels_dropped"] == ["PO3"] and b3["fbcca_channels"] == list(VISUAL_CLUSTER)
  assert b3["harmonic"].shape == (len(X3), 32)


def test_precomputed_decision_is_not_regated():
  """PF-10 known answer: a window with an artefact in a second block is still kept when the decision of the first
  block is handed in (`precomputed`); a fresh call on the same data rejects it, so the blocks would misalign."""
  X, y = make_windows(n_trials=2, seed=4)
  _, _, mask, rep = extract_continuous_psd_features(X, y, SCALP)
  assert mask.all()
  X2 = X.copy()
  X2[5, 2] += 400.0 * np.sign(np.sin(np.arange(T)))
  fresh, _, m_fresh, _ = fb.extract_fbcca_features(X2, y, SCALP)
  shared, _, m_shared, _ = fb.extract_fbcca_features(X2, y, SCALP, precomputed=rep)
  assert m_fresh[5] == 0 and len(fresh) == len(X) - 1
  assert m_shared.all() and len(shared) == len(X)
  with pytest.raises(ValueError):
    fb.extract_fbcca_features(X2[:-1], y[:-1], SCALP, precomputed=rep)     # decision of another length


def test_thresholds_explicit_and_layout_names_required():
  """R5 / PF-06 known answer: a thresholds dict missing a limit raises; 6 channels without names raise; 7 and 8
  channels resolve to the legacy names / the full montage; the extractor gate defaults are the P07 limits."""
  X, y = make_windows(n_trials=1, seed=5)
  with pytest.raises(ValueError, match="explicitly"):
    extract_continuous_psd_features(X, y, SCALP, thresholds={"vpp_min": 5.0})
  with pytest.raises(ValueError, match="layout unknown"):
    fb.extract_fbcca_features(X[:, :6], y)
  _, _, _, rep = fb.extract_fbcca_features(X, y)                              # 7 channels -> legacy names
  assert rep["channels_kept"] == SCALP == resolve_channel_names(7)
  X8, y8 = make_windows(n_trials=1, seed=5, n_ch=8)
  _, _, _, rep8 = extract_continuous_psd_features(X8, y8)
  assert rep8["channels_kept"] == list(FULL_MONTAGE)
  assert GATE_THRESHOLDS == {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}


def test_legacy_p05_gate_reachable_and_single_tier():
  """Legacy (R5) known answer: `thresholds=P05_MASK_THRESHOLDS, channel_fail_fraction=NO_CHANNEL_DROP` is the
  single-tier P05 gate: a chronically noisy channel (POz) is kept and rejects every window (mask equals
  `resolve_window_mask`, 0 rows, 210 columns), whereas the P07 two-tier default drops POz and keeps all 50 windows."""
  X, y = _noisy(bad=("POz",), seed=6)
  P, _, mask, rep = extract_continuous_psd_features(X, y, SCALP, thresholds=P05_MASK_THRESHOLDS,
                                                    channel_fail_fraction=NO_CHANNEL_DROP)
  assert rep["channels_dropped"] == [] and P.shape == (0, 7 * 30)
  assert np.array_equal(mask, resolve_window_mask(X)) and mask.sum() == 0
  P7, _, mask7, rep7 = extract_continuous_psd_features(X, y, SCALP)
  assert rep7["channels_dropped"] == ["POz"] and mask7.sum() == len(X) and P7.shape == (len(X), 6 * 30)


def test_p05_row_of_the_gate_table_is_not_inherited_from_a_default():
  """PF-07 known answer: with Vpp 2 uV windows (fail vpp_min 5) the default extractor gate rejects them and the legacy
  limits keep them; the extractor takes no hidden default from `validate_eeg_windows` for the legacy path."""
  X, y = make_windows(n_trials=1, seed=7)
  X = X.copy()
  X[:, :, :32], X[:, :, 32:64], X[:, :, 64:] = 1.0, -1.0, 0.0
  _, _, m_default, _ = fb.extract_fbcca_features(X, y, SCALP, channel_fail_fraction=NO_CHANNEL_DROP)
  _, _, m_legacy, _ = fb.extract_fbcca_features(X, y, SCALP, thresholds=P05_MASK_THRESHOLDS,
                                                channel_fail_fraction=NO_CHANNEL_DROP)
  assert m_default.sum() == 0 and m_legacy.all()


# --- channel names of saved arrays -------------------------------------------------------------

def test_subject_channel_names_json_beats_count(tmp_path):
  """PF-05 / PF-06 known answer: channels.json `kept` wins; without it 7 -> legacy names, 8 -> montage, 6 -> error;
  a json whose length differs from the array raises with the name count in the message."""
  write_subject(tmp_path, "S01", n_trials=1)
  assert subject_channel_names(tmp_path, "S01", 7) == SCALP
  assert subject_channel_names(tmp_path, "S01", 8) == list(FULL_MONTAGE)
  with pytest.raises(ValueError, match="layout unknown"):
    subject_channel_names(tmp_path, "S01", 6)
  (tmp_path / "S01" / "channels.json").write_text(json.dumps({"kept": SCALP[::-1]}))
  assert subject_channel_names(tmp_path, "S01", 7) == SCALP[::-1]
  with pytest.raises(ValueError, match="7 channel names"):
    subject_channel_names(tmp_path, "S01", 6)


def test_prepare_subject_reads_8_channel_arrays_and_reports_the_drop(tmp_path):
  """Known answer: an 8-channel folder with PO7 noisy in every window -> kept = the 7 legacy names, dropped = [PO7],
  X_time of the blocks has 7 channels; clean + rejected = stimulus windows."""
  write_subject(tmp_path, "S02", n_trials=2, seed=8, n_ch=8, bad_channels=("PO7",))
  b = prepare_subject(tmp_path, "S02")
  assert b["channels_dropped"] == ["PO7"] and b["channels_kept"] == SCALP
  assert b["subbands"].shape[2] == 7 and b["n_clean"] + b["n_rejected"] == b["n_stimulus"] == 50


def test_no_script_keeps_the_interim_legacy_scalp_lines():
  """PF-05 known answer: no consumer script still reduces the config list with `legacy_scalp` (the interim lines
  of the data-signal builder are replaced by `resolve_channel_names` / `channels.json` lookups)."""
  hits = [str(p.relative_to(ROOT)) for p in (ROOT / "scripts").rglob("*.py")
          if re.search(r"legacy_scalp\(", p.read_text())]
  assert hits == []


# --- consumers on a tree with a dropped channel (PF-08) ----------------------------------------

@pytest.fixture(scope="module")
def tree(tmp_path_factory):
  root = tmp_path_factory.mktemp("p07")
  write_subject(root / "processed", "S01", n_trials=3, seed=21)                                # clean, 7 channels
  write_subject(root / "processed", "S02", n_trials=3, seed=22, n_ch=8, bad_channels=("PO7",))  # 8 channels, PO7 dropped
  write_subject(root / "processed", "S05", n_trials=3, seed=23, bad_channels=("PO8",))          # cluster channel dropped
  (root / "processed" / "S03").mkdir()                                                          # no arrays: skipped
  return root


def _flags(root, subject, *extra):
  return ["--subject", subject, "--processed-dir", str(root / "processed"), "--reports-dir", str(root / "reports"), *extra]


def test_flagship_and_harmonic_scripts_run_after_a_drop(tree, capsys):
  """PF-08 smoke: the flagship script (8-channel subject with PO7 dropped) and the harmonic script (PO8 dropped, so the
  FBCCA cluster is O1, Oz, O2) exit 0, print the channel summary and write their reports."""
  assert ecm.main(_flags(tree, "S02", "--no-figures", "--figures-dir", str(tree / "fig"))) == 0
  out = capsys.readouterr().out
  assert "dropped 1 [PO7]" in out and "channels kept 7" in out
  assert bhf.main(_flags(tree, "S05", "--no-figures", "--figures-dir", str(tree / "fig"))) == 0
  out = capsys.readouterr().out
  assert "dropped 1 [PO8]" in out and "O1, Oz, O2" in out
  assert (tree / "reports" / "flagship_S02.csv").is_file()


def test_five_subject_script_runs_with_mixed_layouts(tree):
  """PF-08 smoke: the legacy cohort script handles the 7-channel, the 8-channel (PO7 dropped) and the PO8-dropped
  subjects in one run; the empty S03 folder is not discovered."""
  assert b5.discover_subjects(tree / "processed") == ["S01", "S02", "S05"]
  assert b5.main(["--processed-dir", str(tree / "processed"), "--reports-dir", str(tree / "r5")]) == 0
  df = pd.read_csv(tree / "r5" / "five_subjects_benchmark.csv")
  assert df["Subject"].tolist() == ["S01", "S02", "S05", "Mean"]


# --- benchmark_n_subjects ----------------------------------------------------------------------

def test_n_subjects_schema_channels_and_parallel_equals_serial(tree, capsys):
  """Known answer (02_REQUIREMENTS section 6): columns exactly Subject, Channels Kept, Channels Dropped, Clean Windows,
  Rejected Windows, 1.0s Acc (%), 2.0s Smoothed (%); one row per subject + a Mean row of the accuracy columns; S01
  keeps 7 channels (dropped none), S02 keeps 7 and drops PO7, S05 keeps 6 and drops PO8; clean + rejected = 75
  stimulus windows; the per-subject channel report (`-> DROPPED`) is printed; the S01 accuracies equal the flagship
  script's on the same tree (same code path); `--n-jobs 2` writes the same CSV as `--n-jobs 1`; meta file labels the
  legacy behaviours."""
  args = ["--data-root", str(tree / "processed")]
  assert bns.main(args + ["--reports-dir", str(tree / "rn1"), "--n-jobs", "1"]) == 0
  out = capsys.readouterr().out
  assert "PO7: fail 100.0%" in out and "-> DROPPED" in out and "[-] Skipping" not in out
  df = pd.read_csv(tree / "rn1" / "n_subjects_benchmark.csv")
  assert list(df.columns) == ["Subject", "Channels Kept", "Channels Dropped", "Clean Windows", "Rejected Windows",
                              "1.0s Acc (%)", "2.0s Smoothed (%)"]
  assert df["Subject"].tolist() == ["S01", "S02", "S05", "Mean"]
  assert df["Channels Kept"].iloc[:3].tolist() == [7, 7, 6]
  assert df["Channels Dropped"].iloc[:3].tolist() == ["none", "PO7", "PO8"]
  assert (df["Clean Windows"].iloc[:3] + df["Rejected Windows"].iloc[:3]).tolist() == [75, 75, 75]
  for c in ("1.0s Acc (%)", "2.0s Smoothed (%)"):
    assert df[c].iloc[3] == pytest.approx(round(df[c].iloc[:3].mean(), 2), abs=1e-9)
  assert ecm.main(_flags(tree, "S01", "--no-figures", "--figures-dir", str(tree / "fig"))) == 0
  fl = pd.read_csv(tree / "reports" / "flagship_S01.csv").iloc[0]
  assert df.iloc[0]["1.0s Acc (%)"] == fl["1.0s Acc (%)"] and df.iloc[0]["2.0s Smoothed (%)"] == fl["2.0s Smoothed (%)"]
  meta = (tree / "rn1" / "n_subjects_benchmark.meta.txt").read_text()
  assert "StratifiedKFold" in meta and "legacy" in meta and "S02: kept" in meta and "dropped PO7" in meta
  assert bns.main(args + ["--reports-dir", str(tree / "rn2"), "--n-jobs", "2"]) == 0
  pd.testing.assert_frame_equal(df, pd.read_csv(tree / "rn2" / "n_subjects_benchmark.csv"))


def test_n_subjects_subjects_flag_skip_and_exit_codes(tree, capsys):
  """Known answer: `--subjects S01 S09` skips S09 with `[-] Skipping S09` and still writes one row + Mean; an empty
  or missing data root exits 1."""
  assert bns.main(["--data-root", str(tree / "processed"), "--reports-dir", str(tree / "rs"),
                   "--subjects", "S01", "S09", "--out-suffix", "x"]) == 0
  assert "[-] Skipping S09" in capsys.readouterr().out
  df = pd.read_csv(tree / "rs" / "n_subjects_benchmark_x.csv")
  assert df["Subject"].tolist() == ["S01", "Mean"]
  assert bns.main(["--data-root", str(tree / "nowhere"), "--reports-dir", str(tree / "rs")]) == 1
  (tree / "empty").mkdir(exist_ok=True)
  assert bns.main(["--data-root", str(tree / "empty"), "--reports-dir", str(tree / "rs")]) == 1
