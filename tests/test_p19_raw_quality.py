"""P19 quality check on the raw segmented signal: source in {filtered, raw, both}, reason 3, C-a (known answers)."""

import json

import numpy as np
import pytest
from scipy.signal import butter, sosfiltfilt

from scripts import build_windows as bw
from src.preprocessing import window_quality as WQ
from src.preprocessing.signal.quality_check import apply_artifact_quality_pipeline
from src.preprocessing.windowing import cut_windows
from tests import p16_synth as S

FS = 256.0
NAMES = ["A", "B", "C"]
PARAMS = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0, "channel_fail_fraction": 0.5,
          "artifact_block_sec": 0.25, "guard_sec": 1.0, "guard_rel_amplitude": 0.01, "source": "filtered"}
SOS = butter(4, [1.0, 90.0], btype="band", fs=FS, output="sos")


def _noise(T=60 * 256, C=3, seed=0, std=5.0):
  return np.random.default_rng(seed).normal(0, std, size=(C, T))


def _gate(raw, filt, source, labels=None, names=NAMES, **over):
  starts = np.arange(0, raw.shape[1] - 255, 256)
  p = {**PARAMS, "source": source, **over}
  return starts, WQ.subject_quality_gate(cut_windows(filt, starts, 256), starts, filt, FS, list(names), [], p,
                                         labels, raw_windows=cut_windows(raw, starts, 256), raw=raw)


def _drift_pair():
  """Raw with a slow offset in channel B: +400 uV on seconds 20-30 with a 0.5 s ramp in and out. Inside a window the
  raw is a plain ramp or a constant; the std of the (noise + step) raw windows at the ramps is large. The
  zero-phase 1-90 Hz filter removes the constant part, so the filtered windows of seconds 21-28 stay within limits
  while the raw windows keep Vpp ~ noise (no gate failure) -> use a drift whose raw Vpp exceeds the limit instead:
  a 0.1 Hz sine of 600 uV amplitude (period 10 s) has raw Vpp ~ 100-190 uV per 1 s window near the zero crossing
  slope 2*pi*0.1*600 = 377 uV/s, i.e. above vpp_max 120 uV, while the filtered 0.1 Hz part is attenuated to < 1 uV."""
  x = _noise()
  t = np.arange(x.shape[1]) / FS
  drift = np.zeros_like(x)
  drift[1, 20 * 256:30 * 256] = 600.0 * np.sin(2 * np.pi * 0.1 * (t[20 * 256:30 * 256] - 20.0))
  raw = x + drift
  return raw, sosfiltfilt(SOS, raw, axis=-1)


def test_raw_only_drift_valid_on_filtered_rejected_reason3_on_raw_and_both():
  raw, filt = _drift_pair()
  starts = np.arange(0, raw.shape[1] - 255, 256)
  steep = np.array([k for k in range(22, 29) if np.ptp(raw[1, starts[k]:starts[k] + 256]) > 130.0])   # raw Vpp > limit
  assert len(steep) >= 3
  _, qf = _gate(raw, filt, "filtered")
  assert (qf["reason"] == 0).all() and qf["valid_mask"][steep].all()
  for src in ("raw", "both"):
    _, q = _gate(raw, filt, src)
    assert (q["reason"][steep] == 3).all(), src
    assert (q["valid_mask"][steep] == 0).all() and (q["valid_mask_no_guard"][steep] == 0).all()
    assert (q["reason"][:18] == 0).all() and (q["reason"][40:] == 0).all()
    assert q["n_raw_gate"] >= len(steep) and q["n_raw_gate"] + q["n_raw_guard"] == int((q["reason"] == 3).sum())


def test_filtered_only_failure_keeps_reason1_under_both():
  """Window 10 is flat (std 0) on the filtered signal only; raw passes."""
  raw = _noise()
  filt = raw.copy()
  filt[:, 10 * 256:11 * 256] = 0.0
  for src in ("filtered", "both"):
    _, q = _gate(raw, filt, src)
    assert q["reason"][10] == 1 and q["valid_mask"][10] == 0
    assert (q["reason"][np.arange(len(q["reason"])) != 10] == 0).all()
  _, qr = _gate(raw, filt, "raw")
  assert (qr["reason"] == 0).all()


def test_raw_artifact_guard_known_windows():
  """A +-300 uV square wave in the 64-sample block starting at 30*256+64 of one raw channel (filtered clean).
  Dilated by the 256-sample guard: [29*256+64, 31*256+128), overlapped by windows 29, 30, 31 and no other.
  Window 30 holds the block, so it also fails the raw gate; 29 and 31 are guard-only."""
  raw = _noise()
  filt = raw.copy()
  s0 = 30 * 256 + 64
  raw[1, s0:s0 + 64] += 300.0 * np.sign(np.sin(np.arange(64) + 0.5))
  _, qb = _gate(raw, filt, "both")
  _, qf = _gate(raw, filt, "filtered")
  assert (qf["reason"] == 0).all()
  assert np.flatnonzero(qb["reason"] == 3).tolist() == [29, 30, 31]
  assert qb["n_artifact_blocks_raw"] == 1 and qb["n_artifact_blocks"] == 0
  assert qb["n_raw_gate"] == 1 and qb["n_raw_guard"] == 2
  assert qb["valid_mask_no_guard"][[29, 31]].tolist() == [1, 1] and qb["valid_mask_no_guard"][30] == 0


def test_channel_bad_only_on_raw_is_dropped_under_raw_and_both_kept_under_filtered():
  raw = _noise()
  raw[2] *= 20.0                                                   # std 100 uV on raw in every window
  filt = _noise()                                                  # the filtered copy of C is clean
  _, qf = _gate(raw, filt, "filtered")
  assert qf["channels_dropped"] == []
  for src in ("raw", "both"):
    _, q = _gate(raw, filt, src)
    assert q["channels_dropped"] == ["C"] and q["channels_kept"] == ["A", "B"], src
    assert (q["reason"] == 0).all()                                # the window tier ignores the dropped channel


def test_filtered_source_is_byte_identical_to_the_p16_pipeline_and_ignores_raw():
  raw, filt = _drift_pair()
  filt[0, 5 * 256 + 3] += 400.0
  starts = np.arange(0, raw.shape[1] - 255, 256)
  w = cut_windows(filt, starts, 256)
  ref = apply_artifact_quality_pipeline(w, np.zeros(len(w), int), NAMES, vpp_min=5.0, vpp_max=120.0, std_min=1.0,
                                        std_max=35.0, channel_fail_fraction_thresh=0.5, verbose=False)
  g1 = WQ.subject_quality_gate(w, starts, filt, FS, NAMES, [], PARAMS)
  g2 = WQ.subject_quality_gate(w, starts, filt, FS, NAMES, [], PARAMS, raw_windows=cut_windows(raw, starts, 256), raw=raw)
  assert g1["valid_mask_no_guard"].tobytes() == np.asarray(ref["valid_mask"]).astype(np.int8).tobytes()
  assert g1["channels_kept"] == ref["channels_kept"]
  for k in ("valid_mask", "reason", "valid_mask_no_guard"):
    assert g1[k].tobytes() == g2[k].tobytes()
  assert set(np.unique(g1["reason"])) <= {0, 1, 2}
  # a gate that ignored `source` would give the drift windows of `both` the filtered answer (no reason 3)
  _, qb = _gate(raw, filt, "both")
  assert (qb["reason"] == 3).any() and not (g1["reason"] == 3).any()


def test_missing_or_unknown_source_raises():
  x = _noise(T=5 * 256)
  w = cut_windows(x, np.array([0]), 256)
  bad = {k: v for k, v in PARAMS.items() if k != "source"}
  with pytest.raises(ValueError, match="explicitly"):
    WQ.subject_quality_gate(w, np.array([0]), x, FS, NAMES, [], bad)
  with pytest.raises(ValueError, match="source"):
    WQ.subject_quality_gate(w, np.array([0]), x, FS, NAMES, [], {**PARAMS, "source": "unfiltered"})
  with pytest.raises(ValueError, match="raw_windows"):
    WQ.subject_quality_gate(w, np.array([0]), x, FS, NAMES, [], {**PARAMS, "source": "both"})
  cfg = {"quality": {"vpp_range_uv": [5, 120], "std_range_uv": [1, 35], "channel_fail_fraction": 0.5,
                     "artifact_block_sec": 0.25, "guard_sec": "auto", "guard_rel_amplitude": 0.01}}
  with pytest.raises(ValueError, match="source"):
    WQ.quality_params_from_config(cfg)


def test_config_default_is_both():
  import yaml
  cfg = yaml.safe_load(bw.DEFAULT_CONFIG.read_text())
  assert cfg["quality"]["source"] == "both"
  assert WQ.quality_params_from_config(cfg)["source"] == "both"


def test_rejections_by_label_reasons_1_2_3_sum_to_rejected():
  raw, filt = _drift_pair()
  filt[0, 40 * 256 + 5] += 400.0                                   # reason 1 at window 40, guard 2 around it
  starts = np.arange(0, raw.shape[1] - 255, 256)
  labels = np.where(starts < 30 * 256, 101, 102)
  _, q = _gate(raw, filt, "both", labels=labels)
  r = q["rejections_by_label"]
  tot = {k: sum(v[k] for v in r.values()) for k in ("total", "valid", "own_gate", "guard", "raw")}
  assert tot["own_gate"] >= 1 and tot["guard"] >= 1 and tot["raw"] >= 1
  assert tot["total"] - tot["valid"] == tot["own_gate"] + tot["guard"] + tot["raw"] == int((q["valid_mask"] == 0).sum())
  assert tot["raw"] == int((q["reason"] == 3).sum())


def test_all_channels_dropped_raises_dedicated_error():
  raw = _noise() * 40.0
  with pytest.raises(WQ.AllChannelsDropped):
    _gate(raw, raw.copy(), "raw")


# --- build_windows: source in build_params, C-a, skip message ---------------------------------

@pytest.fixture(scope="module")
def rawdir(tmp_path_factory):
  root = tmp_path_factory.mktemp("raw19")
  S.write_raw_subject(root, "S01", n_trials=10, seed=1)
  return root


def _run(raw, out, *extra):
  return bw.main(["--raw-dir", str(raw), "--out-root", str(out), "--subjects", "S01", *extra])


def test_c_a_refuse_resume_skip_overwrite(rawdir, tmp_path, capsys):
  out = tmp_path / "c"
  assert _run(rawdir, out, "--quality-source", "filtered") == 0
  meta = json.loads((out / "S01" / "windows_meta.json").read_text())
  assert meta["build_params"]["quality"]["source"] == "filtered" and meta["quality"]["source"] == "filtered"
  assert "quality source filtered" in meta["data_source"]
  mtime = (out / "S01" / "windows_meta.json").stat().st_mtime_ns
  capsys.readouterr()
  assert _run(rawdir, out, "--quality-source", "both") == 1                       # differing params: refused
  msg = capsys.readouterr().out
  assert "Refusing to overwrite" in msg and "quality.source" in msg
  assert (out / "S01" / "windows_meta.json").stat().st_mtime_ns == mtime
  assert _run(rawdir, out, "--quality-source", "filtered", "--resume") == 0       # identical: skipped
  assert "already built" in capsys.readouterr().out
  assert (out / "S01" / "windows_meta.json").stat().st_mtime_ns == mtime
  assert _run(rawdir, out, "--quality-source", "both", "--overwrite") == 0        # rewritten
  meta = json.loads((out / "S01" / "windows_meta.json").read_text())
  assert meta["build_params"]["quality"]["source"] == "both"
  assert meta["quality"]["reason_codes"]["3"].startswith("raw")


def test_build_filtered_vs_both_on_a_clean_subject_and_meta_counts(rawdir, tmp_path):
  assert _run(rawdir, tmp_path / "f", "--quality-source", "filtered") == 0
  assert _run(rawdir, tmp_path / "b", "--quality-source", "both") == 0
  for name in ("X_time_windows", "X_raw_windows", "window_starts", "X_bands_fbcca"):
    assert np.array_equal(np.load(tmp_path / "f" / "S01" / f"{name}.npy"), np.load(tmp_path / "b" / "S01" / f"{name}.npy"))
  q = json.loads((tmp_path / "b" / "S01" / "windows_meta.json").read_text())["quality"]
  rb = np.load(tmp_path / "b" / "S01" / "reject_reason.npy")
  assert q["n_reason3_raw_gate"] + q["n_reason3_raw_guard"] == int((rb == 3).sum())


def test_all_channels_dropped_prints_skip_and_writes_nothing(tmp_path, capsys):
  root = tmp_path / "raw"
  S.write_raw_subject(root, "S01", n_trials=10, seed=3, tone_amp=2000.0)   # stimulus windows (5/8) far above Vpp max
  out = tmp_path / "out"
  assert _run(root, out, "--quality-source", "raw") == 1                         # no subject built
  assert "[-] Skipping S01: all channels dropped (source=raw)" in capsys.readouterr().out
  assert not list(out.rglob("*.npy")) and not (out / "S01").exists()
