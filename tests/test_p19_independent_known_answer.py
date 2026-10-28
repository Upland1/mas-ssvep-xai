"""P19 independent known-answer tests (synthetic-tester): raw-signal quality source, reason 3, guard, C-a, skip."""

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
W = 256
NAMES = ["A", "B", "C", "D"]
P = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0, "channel_fail_fraction": 0.5,
     "artifact_block_sec": 0.25, "guard_sec": 0.5, "guard_rel_amplitude": 0.01, "source": "filtered"}
SOS = butter(4, [1.0, 90.0], btype="band", fs=FS, output="sos")
EXT = "eb" + "r"                                                  # synthetic recording extension


def noise(T=40 * 256, C=4, seed=11, std=5.0):
  return np.random.default_rng(seed).normal(0, std, size=(C, T))


def alt(n):
  """Alternating +-1 sequence of length n (a 128 Hz square wave: Vpp = 2 * amplitude inside any block)."""
  return np.where(np.arange(n) % 2, 1.0, -1.0)


def gate(raw, filt, source, labels=None, names=NAMES, **over):
  starts = np.arange(0, raw.shape[1] - W + 1, W)
  p = {**P, "source": source, **over}
  q = WQ.subject_quality_gate(cut_windows(filt, starts, W), starts, filt, FS, list(names), [], p, labels,
                              raw_windows=cut_windows(raw, starts, W), raw=raw)
  return starts, q


def slow_drift_pair(ch=2, a=10, b=18, amp=1000.0):
  """Raw = noise + 0.2 Hz sine (amp 800 uV, slope ~1000 uV/s) in channel `ch`, seconds a..b; 1-90 Hz removes it."""
  x = noise()
  t = np.arange(x.shape[1]) / FS
  env = np.sin(np.pi * (t[a * W:b * W] - a) / (b - a)) ** 2         # smooth taper: no step at the edges
  x[ch, a * W:b * W] += amp * env * np.sin(2 * np.pi * 0.2 * (t[a * W:b * W] - a))
  return x, sosfiltfilt(SOS, x, axis=-1)


def test_planted_slow_drift_is_removed_by_filter_and_rejected_only_on_raw_sources():
  raw, filt = slow_drift_pair()
  starts, qf = gate(raw, filt, "filtered")
  assert (qf["reason"] == 0).all() and qf["valid_mask"].all()          # the filter really removed it
  vpp = np.ptp(raw[2][starts[:, None] + np.arange(W)], axis=1)
  inside = np.flatnonzero(vpp > 150.0)                                 # raw windows clearly above vpp_max
  assert len(inside) >= 3 and inside.min() >= 10 and inside.max() < 18
  for src in ("raw", "both"):
    _, q = gate(raw, filt, src)
    assert (q["reason"][inside] == 3).all() and (q["valid_mask"][inside] == 0).all(), src
    assert q["n_raw_gate"] >= 4
    assert set(np.unique(q["reason"])) <= {0, 3}
    assert (q["reason"][:8] == 0).all() and (q["reason"][20:] == 0).all()


def test_raw_artifact_guard_covers_exactly_block_plus_minus_guard():
  """64-sample block at 20*256+100 on raw only; guard 0.5 s = 128 samples; dilated span [4972, 5412);
  window k overlaps iff k*256 < 5412 and k*256+256 > 4972, i.e. k = 19, 20, 21."""
  raw = noise()
  filt = raw.copy()
  s0 = 20 * W + 100
  raw[0, s0:s0 + 64] += 400.0 * alt(64)
  _, qb = gate(raw, filt, "both")
  _, qf = gate(raw, filt, "filtered")
  _, qr = gate(raw, filt, "raw")
  lo, hi = s0 - 128, s0 + 64 + 128
  want = [k for k in range(len(qb["reason"])) if k * W < hi and k * W + W > lo]
  assert want == [19, 20, 21]
  assert np.flatnonzero(qb["reason"] == 3).tolist() == want
  assert np.flatnonzero(qr["reason"] == 3).tolist() == want
  assert (qf["reason"] == 0).all() and qf["valid_mask"].all()
  assert qb["valid_mask_no_guard"][[19, 21]].tolist() == [1, 1]        # 19 and 21 are guard-only
  _, q0 = gate(raw, filt, "both", guard_sec=0.0)
  assert np.flatnonzero(q0["reason"] == 3).tolist() == [20]            # no guard: only the window holding the block


def test_block_straddling_a_window_boundary_flags_both_neighbours_without_guard():
  raw = noise()
  filt = raw.copy()
  s0 = 25 * W - 32                                                     # 64 samples across the 24|25 boundary
  raw[1, s0:s0 + 64] += 400.0 * alt(64)
  _, q = gate(raw, filt, "both", guard_sec=0.0)
  assert np.flatnonzero(q["reason"] == 3).tolist() == [24, 25]


def test_channel_bad_only_on_one_signal_is_dropped_only_when_that_signal_is_checked():
  raw, filt = noise(), noise()
  raw[3] = raw[3] * 30.0                                               # D: std 150 uV on raw only
  assert gate(raw, filt, "filtered")[1]["channels_dropped"] == []
  for src in ("raw", "both"):
    q = gate(raw, filt, src)[1]
    assert q["channels_dropped"] == ["D"] and q["channels_kept"] == ["A", "B", "C"]
    assert (q["reason"] == 0).all()
  raw2, filt2 = noise(), noise()
  filt2[0] = filt2[0] * 30.0                                           # A bad on filtered only
  assert gate(raw2, filt2, "both")[1]["channels_dropped"] == ["A"]
  assert gate(raw2, filt2, "raw")[1]["channels_dropped"] == []


def test_precedence_1_over_2_over_3():
  # window 5: filtered gate fails (flat) and raw gate fails -> 1; window 20: raw gate only -> 3
  raw, filt = noise(), noise(seed=12)
  filt[:, 5 * W:6 * W] = 0.0
  raw[1, 5 * W:6 * W] += np.linspace(-500, 500, W)
  raw[0, 20 * W:21 * W] += np.linspace(-300, 300, W)
  r = gate(raw, filt, "both", guard_sec=0.0)[1]["reason"]
  assert r[5] == 1 and r[20] == 3 and r[30] == 0
  assert np.flatnonzero(r).tolist() == [5, 20]
  # window 9: raw gate fails, and a filtered artifact in window 8 puts window 9 inside the filtered guard -> 2 (not 3)
  raw2, filt2 = noise(), noise(seed=13)
  filt2[2, 8 * W + 200:8 * W + 256] += 300.0 * alt(56)
  raw2[0, 9 * W:10 * W] += np.linspace(-300, 300, W)
  q2 = gate(raw2, filt2, "both", guard_sec=0.5)[1]
  assert q2["reason"][9] == 2 and q2["valid_mask"][9] == 0
  q3 = gate(raw2, filt2, "raw", guard_sec=0.5)[1]                      # raw only: no filtered check -> 3
  assert q3["reason"][9] == 3 and set(np.unique(q3["reason"])) <= {0, 3}


def test_filtered_source_byte_identical_to_pre_p19_gate_with_hostile_raw():
  raw, filt = slow_drift_pair()
  filt[1, 3 * W + 7] += 500.0
  filt[2, 30 * W:31 * W] *= 0.0
  starts = np.arange(0, filt.shape[1] - W + 1, W)
  w = cut_windows(filt, starts, W)
  ref = apply_artifact_quality_pipeline(w, np.zeros(len(w), int), NAMES, vpp_min=5.0, vpp_max=120.0, std_min=1.0,
                                        std_max=35.0, channel_fail_fraction_thresh=0.5, verbose=False)
  junk = noise(seed=99) * 100.0
  g0 = WQ.subject_quality_gate(w, starts, filt, FS, NAMES, [], P)
  for kw in ({}, {"raw_windows": cut_windows(junk, starts, W), "raw": junk}):
    g = WQ.subject_quality_gate(w, starts, filt, FS, NAMES, [], P, **kw)
    assert g["valid_mask_no_guard"].tobytes() == np.asarray(ref["valid_mask"]).astype(np.int8).tobytes()
    assert g["channels_kept"] == ref["channels_kept"]
    for k in ("valid_mask", "reason", "valid_mask_no_guard"):
      assert g[k].tobytes() == g0[k].tobytes() and g[k].dtype == np.int8
    assert set(np.unique(g["reason"])) <= {0, 1, 2}
  with pytest.raises(WQ.AllChannelsDropped):                           # the gate does look at source
    gate(junk, filt, "both")


def test_rejection_counts_by_label_sum_to_total_rejected_for_every_source():
  raw, filt = slow_drift_pair()
  filt[0, 30 * W + 3] += 500.0
  n = raw.shape[1] // W
  labels = np.array([(101, 102, 103, 104, 105, 201, 202, 101)[k % 8] for k in range(n)])
  raw_counts = {}
  for src in ("filtered", "raw", "both"):
    _, q = gate(raw, filt, src, labels=labels)
    r = q["rejections_by_label"]
    rej = int((q["valid_mask"] == 0).sum())
    assert sum(v["total"] for v in r.values()) == n
    assert sum(v["total"] - v["valid"] for v in r.values()) == rej
    for lab, v in r.items():
      assert v["total"] - v["valid"] == v["own_gate"] + v["guard"] + v["raw"], (src, lab)
      assert v["raw"] == int(((q["reason"] == 3) & (labels == lab)).sum())
    raw_counts[src] = sum(v["raw"] for v in r.values())
    if src == "raw":
      assert sum(v["own_gate"] + v["guard"] for v in r.values()) == 0 and rej > 0
  assert raw_counts["filtered"] == 0 and raw_counts["both"] >= 4 and raw_counts["raw"] >= 4


def test_missing_or_unknown_source_raises_and_raw_inputs_required():
  x = noise(T=5 * W)
  w = cut_windows(x, np.array([0]), W)
  with pytest.raises(ValueError):
    WQ.subject_quality_gate(w, np.array([0]), x, FS, NAMES, [], {k: v for k, v in P.items() if k != "source"})
  for bad in ("Raw", "unfiltered", "", None, "filtered,raw"):
    with pytest.raises(ValueError):
      WQ.subject_quality_gate(w, np.array([0]), x, FS, NAMES, [], {**P, "source": bad})
  for src in ("raw", "both"):
    with pytest.raises(ValueError):                                    # raw arrays missing
      WQ.subject_quality_gate(w, np.array([0]), x, FS, NAMES, [], {**P, "source": src})


# --- build_windows end to end on synthetic recordings -----------------------------------------

def _write_with_raw_drift(root, ch=2, amp=1500.0):
  """Channel `ch` gets a 0.2 Hz, `amp` uV drift over seconds 20-40 (under the channel-drop fraction)."""
  blk = S.make_block(n_trials=10, seed=5)
  t = np.arange(blk.shape[1]) / S.FS
  seg = slice(20 * S.FS, 40 * S.FS)
  blk[ch, seg] += amp * np.sin(2 * np.pi * 0.2 * (t[seg] - 20.0))
  S.write_ebr(root / "S01" / f"OO.{EXT}", blk)


def _run(raw, out, *extra, subj=("S01",)):
  return bw.main(["--raw-dir", str(raw), "--out-root", str(out), "--subjects", *subj, *extra])


def test_build_raw_drift_is_rejected_on_raw_and_both_not_on_filtered(tmp_path):
  """The raw path is truly wired end to end: raw-drift windows exceed vpp_max and are rejected with reason 3."""
  root = tmp_path / "rec"
  _write_with_raw_drift(root)
  res = {}
  for src in ("filtered", "raw", "both"):
    assert _run(root, tmp_path / src, "--quality-source", src) == 0
    d = tmp_path / src / "S01"
    res[src] = (np.load(d / "reject_reason.npy"), np.load(d / "valid_mask.npy"),
                json.loads((d / "windows_meta.json").read_text()))
  rf, rr, rb = res["filtered"][0], res["raw"][0], res["both"][0]
  assert (rf == 3).sum() == 0
  assert (rr == 3).sum() >= 5 and ((rr != 0) == (rr == 3)).all()      # raw: every rejection is reason 3
  assert (rb == 3).sum() >= 5
  assert res["raw"][1].sum() < res["filtered"][1].sum()
  q = res["both"][2]["quality"]
  assert q["n_reason3_raw_gate"] >= 1 and q["n_reason3_raw_gate"] + q["n_reason3_raw_guard"] == int((rb == 3).sum())
  starts = np.load(tmp_path / "both" / "S01" / "window_starts.npy")
  bad = starts[rb == 3]
  assert bad.min() >= 20 * S.FS - 4 * S.FS and bad.max() <= 40 * S.FS + 4 * S.FS    # near the drift, within guard
  for name in ("X_time_windows", "X_raw_windows", "window_starts"):                  # same windows on every source
    assert np.array_equal(np.load(tmp_path / "filtered" / "S01" / f"{name}.npy"),
                          np.load(tmp_path / "both" / "S01" / f"{name}.npy"))


def test_c_a_refusal_resume_overwrite_independent(tmp_path):
  raw = tmp_path / "raw"
  S.write_raw_subject(raw, "S01", n_trials=10, seed=21)
  out = tmp_path / "o"
  meta = out / "S01" / "windows_meta.json"
  assert _run(raw, out, "--quality-source", "both") == 0
  mt = meta.stat().st_mtime_ns
  x0 = np.load(out / "S01" / "X_time_windows.npy").copy()
  assert _run(raw, out, "--quality-source", "raw") != 0                # refused
  assert meta.stat().st_mtime_ns == mt
  assert _run(raw, out, "--quality-source", "both", "--resume") == 0   # identical: skipped
  assert meta.stat().st_mtime_ns == mt
  assert _run(raw, out, "--quality-source", "raw", "--banks", "fbcca") != 0      # other differing param: refused
  assert _run(raw, out, "--quality-source", "raw", "--overwrite") == 0
  assert meta.stat().st_mtime_ns != mt
  assert json.loads(meta.read_text())["build_params"]["quality"]["source"] == "raw"
  assert np.array_equal(np.load(out / "S01" / "X_time_windows.npy"), x0)


def test_c_a_refusal_happens_before_any_subject_is_built(tmp_path):
  raw = tmp_path / "raw"
  S.write_raw_subject(raw, "S01", n_trials=10, seed=22)
  S.write_raw_subject(raw, "S02", n_trials=10, seed=23)
  out = tmp_path / "o"
  assert _run(raw, out, "--quality-source", "both") == 0
  assert _run(raw, out, "--quality-source", "raw", subj=("S01", "S02")) != 0
  assert not (out / "S02").exists()


def test_all_channels_dropped_is_skipped_and_other_subject_still_built(tmp_path, capsys):
  raw = tmp_path / "raw"
  S.write_raw_subject(raw, "S01", n_trials=10, seed=31, tone_amp=3000.0)   # stimulus windows far above vpp_max
  S.write_raw_subject(raw, "S02", n_trials=10, seed=32)
  out = tmp_path / "o"
  rc = _run(raw, out, "--quality-source", "raw", subj=("S01", "S02"))
  txt = capsys.readouterr().out
  assert "[-] Skipping S01: all channels dropped (source=raw)" in txt
  assert not (out / "S01").exists() or not list((out / "S01").rglob("*.npy"))
  assert (out / "S02" / "windows_meta.json").exists() and rc == 0


def test_raw_guard_window_boundaries_are_tight_to_the_sample():
  """Blocks on the 64-sample grid, guard of g samples (guard_sec = g/256). Guarded span = [s0-g, s0+64+g).
  End edge: block 5504..5567 (grid 86), window 22 starts at 5632: g=64 -> span ends at 5632 (exclusive), window 22
  untouched; g=65 -> includes sample 5632, flagged. Start edge: block 4992..5055 (grid 78), window 18 = [4608, 4864):
  g=128 -> span starts at 4864, untouched; g=129 -> includes sample 4863, flagged."""
  def flagged(s0, g):
    raw, filt = noise(), noise()
    raw[0, s0:s0 + 64] += 400.0 * alt(64)
    return np.flatnonzero(gate(raw, filt, "both", guard_sec=g / 256.0)[1]["reason"] == 3).tolist()
  assert 22 not in flagged(5504, 64) and 22 in flagged(5504, 65)
  assert 18 not in flagged(4992, 128) and 18 in flagged(4992, 129)
