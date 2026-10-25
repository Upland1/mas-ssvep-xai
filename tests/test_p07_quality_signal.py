"""P07 builder tests (data-signal): two-tier quality pipeline, resolve_channel_names,
chronic-noise channel drop, PF-07 regression flag, ungated summary, stale outputs.

Synthetic arrays and tiny fake recordings in tmp_path only (never data/). Fast by design.
"""

import json

import numpy as np
import pytest

from scripts.preprocessing import run_preprocessing as rp
from src.io.channels import FULL_MONTAGE, resolve_channel_names
from src.features.ssvep.psd_extraction import extract_clean_subwindows_psd
from src.preprocessing.signal import quality_check as qc
from tests.test_p02_preprocessing_smoke import FS, _signal, _write_ebr

NAMES = list(FULL_MONTAGE)
LIM = dict(vpp_min=5.0, vpp_max=120.0, std_min=1.0, std_max=35.0)
T = 64


def _square(amp, n=T):
  """Square wave +-amp: vpp = 2 amp, std = amp exactly."""
  return amp * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)


def _windows(n=10, amp=10.0):
  """(n, 8, T): channel c has amplitude amp * (c + 1) / 2 ... kept inside 5-120 / 1-35."""
  w = np.zeros((n, 8, T))
  for c in range(8):
    w[:, c, :] = _square(amp + c)       # vpp 20..34, std 10..17
  return w


# --- tier 1 ------------------------------------------------------------------

def test_tier1_strictly_more_than_half():
  """Channel 3 fails in exactly 5/10 windows (kept), channel 5 in 6/10 (dropped)."""
  w = _windows(10)
  w[:5, 3, :] = 0.0       # vpp 0 < 5
  w[:6, 5, :] = 0.0
  assert qc.identify_noisy_channels(w, NAMES, LIM, 0.5) == ["O1"]
  out = qc.apply_artifact_quality_pipeline(w, np.arange(10), NAMES, verbose=False)
  assert out["channels_dropped"] == ["O1"] and "PO4" in out["channels_kept"]


def test_channel_stats_analytic():
  w = _windows(4)
  w[:1, 2, :] = _square(0.1)           # fails (std 0.1 < 1) in 1/4 windows
  s = qc.compute_channel_quality_stats(w, NAMES, LIM)
  assert list(s) == NAMES
  assert s["POz"]["fail_fraction"] == 0.25 and s["POz"]["n_failed"] == 1
  assert s["POz"]["mean_vpp"] == pytest.approx((0.2 + 3 * 2 * 12.0) / 4, abs=1e-9)
  assert s["POz"]["mean_std"] == pytest.approx((0.1 + 3 * 12.0) / 4, abs=1e-9)
  assert s["O2"]["fail_fraction"] == 0.0 and s["O2"]["mean_vpp"] == pytest.approx(34.0, abs=1e-9)


def test_limits_must_be_explicit():
  with pytest.raises(ValueError, match="std_max"):
    qc.identify_noisy_channels(_windows(2), NAMES, {k: v for k, v in LIM.items() if k != "std_max"})


# --- tier 2 and return dict ----------------------------------------------------

def test_tier2_judges_only_surviving_channels_and_dict_layout():
  n = 20
  w = _windows(n)
  y = np.arange(n) % 5
  w[:15, 3, :] = 0.0          # PO4 (index 3) chronically bad -> dropped; includes windows 0..14
  w[17, 3, :] = 0.0           # PO4 bad in window 17 as well (would reject it if still judged)
  w[3, 6, :] = _square(300.0)  # Oz (kept) too large in window 3 -> rejected
  out = qc.apply_artifact_quality_pipeline(w, y, NAMES, **LIM, verbose=False)
  assert set(out) == {"windows_clean", "y_clean", "valid_mask", "channels_kept",
                      "channels_kept_idx", "channels_dropped", "channel_stats"}
  assert out["channels_dropped"] == ["PO4"]
  assert out["channels_kept"] == [c for c in NAMES if c != "PO4"]
  np.testing.assert_array_equal(out["channels_kept_idx"], [0, 1, 2, 4, 5, 6, 7])
  assert out["valid_mask"].shape == (n,) and out["valid_mask"][3] == 0
  assert out["valid_mask"].sum() == n - 1          # only window 3 rejected; 17 kept
  assert out["windows_clean"].shape == (n - 1, 7, T) and len(out["y_clean"]) == n - 1
  # PF-06 / R6: column j of the clean windows is the input channel kept_idx[j]
  keep = out["valid_mask"] == 1
  for j, i in enumerate(out["channels_kept_idx"]):
    np.testing.assert_array_equal(out["windows_clean"][:, j], w[keep][:, i])
  np.testing.assert_array_equal(out["y_clean"], y[keep])


def test_all_channels_dropped_raises():
  with pytest.raises(ValueError, match="all 8 channels"):
    qc.apply_artifact_quality_pipeline(np.zeros((4, 8, T)), np.zeros(4), NAMES, verbose=False)


def test_precomputed_decision_is_reused_for_another_block():
  """PF-10: a second feature block (different values, same rows/channels) gets the same decision."""
  n = 12
  a = _windows(n)
  a[:8, 1, :] = 0.0           # PO3 dropped
  a[2, 5, :] = _square(300.0)  # window 2 rejected
  y = np.arange(n)
  first = qc.apply_artifact_quality_pipeline(a, y, NAMES, **LIM, verbose=False)
  b = np.full_like(a, 0.001)  # would fail everything if gated on its own
  second = qc.apply_artifact_quality_pipeline(b, y, NAMES, **LIM, verbose=False, precomputed=first)
  np.testing.assert_array_equal(second["valid_mask"], first["valid_mask"])
  assert second["channels_kept"] == first["channels_kept"]
  assert second["channels_dropped"] == ["PO3"]
  assert second["windows_clean"].shape == first["windows_clean"].shape
  with pytest.raises(ValueError, match="entries"):
    qc.apply_artifact_quality_pipeline(b[:5], y[:5], NAMES, verbose=False, precomputed=first)


def test_drop_noisy_channels_by_name():
  w = _windows(3)
  kept, names, idx = qc.drop_noisy_channels(w, NAMES, ["PO7", "Oz"])
  assert names == ["PO3", "POz", "PO4", "PO8", "O1", "O2"] and list(idx) == [1, 2, 3, 4, 5, 7]
  np.testing.assert_array_equal(kept[:, 0], w[:, 1])
  with pytest.raises(ValueError):
    qc.drop_noisy_channels(w, NAMES, ["Cz"])


def test_resolve_channel_names():
  assert resolve_channel_names(8) == ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  assert resolve_channel_names(7) == ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  assert resolve_channel_names(6) is None and resolve_channel_names(9) is None


# --- PF-07 ---------------------------------------------------------------------

def test_pf07_pinned_default_and_regression_flag():
  seg = np.stack([_square(1.0, FS)] * 3)               # vpp 2 uV, std 1 uV, three channels
  seg = np.tile(seg, (1, 2))                           # two 1 s sub-windows
  assert len(extract_clean_subwindows_psd(seg, FS, std_range=(0.5, 60.0))) == 2     # default 0.5
  assert len(extract_clean_subwindows_psd(seg, FS, std_range=(0.5, 60.0), vpp_min=5.0)) == 0
  args = rp.build_parser().parse_args([])
  assert args.vpp_min == 0.5 and rp.LEGACY_VPP_MIN_UV == 0.5


# --- run_preprocessing end to end ----------------------------------------------

def _low_signal(n_trials=5, amp=1.0):
  b = _signal(n_trials, seed=5)
  rng = np.random.default_rng(6)
  tt = np.arange(b.shape[1]) / FS
  for k in range(8):
    b[k] = amp * np.sin(2 * np.pi * (5 + 3 * k) * tt) + rng.normal(0, 0.1, b.shape[1])
  return b


def _run(tmp, *extra):
  return rp.main(["--raw-dir", str(tmp / "raw"), "--processed-dir", str(tmp / "proc"),
                  "--no-figures", *extra])


def test_pf07_demo_rejects_low_amplitude_windows(tmp_path, capsys):
  """Vpp ~2.4 uV recording: windows kept with the pinned 0.5, none with --vpp-min 5.0 (PF-07)."""
  _write_ebr(tmp_path / "raw" / "S03" / "OO.ebr", _low_signal())
  assert _run(tmp_path, "--no-channel-drop") == 0
  assert np.load(tmp_path / "proc" / "S03" / "y_labels.npy").size > 0
  capsys.readouterr()
  assert _run(tmp_path, "--no-channel-drop", "--vpp-min", "5.0") == 1
  out = capsys.readouterr().out
  assert "legacy regression demo (PF-07)" in out and "no window accepted" in out
  # the stale arrays of the first run were removed, not left behind (PF-09)
  assert not (tmp_path / "proc" / "S03" / "y_labels.npy").exists()
  assert not (tmp_path / "proc" / "y_labels.npy").exists()
  assert "removed stale output of skipped S03" in out
  # with tier 1 active, the same low recording loses every channel (vpp < 5 in all 1 s windows)
  assert _run(tmp_path) == 1
  assert "every channel is chronically noisy" in capsys.readouterr().out


def test_chronic_noise_channel_dropped_before_windows(tmp_path, capsys):
  b = _signal(5, seed=2)
  rng = np.random.default_rng(9)
  b[2] = rng.normal(0, 100.0, b.shape[1])              # POz: vpp ~ 700 uV in every 1 s window
  _write_ebr(tmp_path / "raw" / "S03" / "OO.ebr", b)
  assert _run(tmp_path) == 0
  out = capsys.readouterr().out
  assert "POz" in out and "-> DROPPED" in out and "dropped ['POz']" in out
  X = np.load(tmp_path / "proc" / "S03" / "X_time_windows.npy")
  assert X.shape[1] == 7 and np.load(tmp_path / "proc" / "S03" / "X_psd_features.npy").shape[1] == 7 * 31
  ch = json.loads((tmp_path / "proc" / "S03" / "channels.json").read_text())
  assert ch["dropped"] == ["POz"] and ch["kept"] == [c for c in NAMES if c != "POz"]
  assert json.loads((tmp_path / "proc" / "channels.json").read_text()) == ch
  assert not (tmp_path / "fig").exists()               # only --processed-dir is written
  # by name (PF-06): kept row j is the filtered input row of that channel
  from src.preprocessing.signal.filters import apply_iir_bandpass
  xf = apply_iir_bandpass(b[:8], FS, 1.0, 60.0, 4)
  y = np.load(tmp_path / "proc" / "S03" / "y_labels.npy")
  assert X.shape[0] == len(y)
  idx = [NAMES.index(c) for c in ch["kept"]]
  assert xf[idx].shape[0] == 7
  assert np.isfinite(X).all()


def test_no_channel_drop_keeps_all_and_reports_ungated_range(tmp_path, capsys):
  b = _signal(5, seed=4, spike_trial=1)
  _write_ebr(tmp_path / "raw" / "S03" / "OO.ebr", b)
  assert _run(tmp_path, "--no-channel-drop") == 0
  out = capsys.readouterr().out
  assert "channel drop disabled" in out
  # ungated summary: counts every sub-window (40 here = 10 x 201 + 5 x 202 + 25 x stim) and
  # sees the 400 uV spike that the gate rejects
  assert "[quality] S03 ungated windows" in out
  line = [l for l in out.splitlines() if "ungated windows" in l][0]
  assert "39/40 windows valid, 1 rejected" in line
  assert np.load(tmp_path / "proc" / "S03" / "y_labels.npy").size == 39


def test_stale_outputs_removed_for_skipped_subject(tmp_path, capsys):
  _write_ebr(tmp_path / "raw" / "S01" / "OO.ebr", _signal(5, seed=1))
  (tmp_path / "raw" / "S02").mkdir(parents=True)       # no recording -> skipped
  stale = tmp_path / "proc" / "S02"
  stale.mkdir(parents=True)
  for k in rp.ARRAY_FILES:
    np.save(stale / f"{k}.npy", np.zeros(3))
  assert _run(tmp_path, "--all") == 0
  out = capsys.readouterr().out
  assert "Skipping S02" in out and "removed stale output of skipped S02" in out
  assert not any(stale.glob("*.npy"))
  assert (tmp_path / "proc" / "S01" / "y_labels.npy").is_file()
