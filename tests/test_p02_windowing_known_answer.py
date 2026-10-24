"""P02 known-answer tests (synthetic-tester): legacy gate, condition windows, PSD features, script.

Every input is built inside the test with a fixed seed (never from data/); fs is the
header rate 256 Hz that P02 uses (decisions.md 2026-10-24, mas/01_DATA_SPEC.md section 5.1).
Expected values come from the specification and from analytic facts:
a full-period sinusoid of amplitude A has ptp = 2A and std = A / sqrt(2); a +-A square
wave has ptp = 2A and std = A exactly; a periodogram of N samples at fs has bin spacing
fs / N, and a sinusoid of amplitude A on an exact bin has one-sided density A**2 * N / (2 fs).
"""

import importlib
import struct

import numpy as np
import pytest
from scipy.signal import periodogram

from src.features.ssvep import psd_extraction as pe
from src.preprocessing.signal import quality_check as qc
from src.preprocessing.signal.filters import apply_iir_bandpass

FS = 256
N = 256  # int(1.0 * FS)
ORDER = (201, 202, 101, 102, 103, 104, 105)
TARGETS = (101, 102, 103, 104, 105)
FILE_CHANNELS = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2", "TIMESTAMP",
                 "FLASHINGTIME", "MARK"]
SCALP = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]  # config v1, PO7 excluded
WIDE = dict(vpp_thresh=1e12, std_range=(0.0, 1e12), vpp_min=0.0)  # gate off (layout tests)


# --- helpers --------------------------------------------------------------------

def _square(a, n=N):
  """+-a alternating samples: ptp = 2a and std = a exactly in float64."""
  return a * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)


def _sine(a, f, n=N, fs=FS, phase=0.0):
  return a * np.sin(2 * np.pi * f * np.arange(n) / fs + phase)


def _protocol_mark(n_trials, seed=0, pulse_len=1):
  """MARK of mas/01_DATA_SPEC.md section 3: first 201 at 5 s, 15 s trials, 8 per target.

  Returns (mark, onsets) with onsets {code: [samples]} and the randomized target order.
  """
  rng = np.random.default_rng(seed)
  targets = rng.permutation(np.repeat(TARGETS, n_trials // 5))
  T = 5 * FS + n_trials * 15 * FS
  mark = np.zeros(T)
  onsets = {c: [] for c in (201, 202, 203, 200) + TARGETS}
  for i, tgt in enumerate(targets):
    t = 5 * FS + i * 15 * FS
    for off, code in ((0, 201), (2, 202), (4, 203), (5, int(tgt)), (10, 200)):
      s = t + off * FS
      mark[s:s + pulse_len] = code
      onsets[code].append(s)
  return mark, onsets


def _ramp(n_ch, T):
  """Channel c, sample t carries t + 1e6 * c (exact in float64): the content names its index."""
  return np.arange(T, dtype=np.float64)[None, :] + 1e6 * np.arange(n_ch)[:, None]


def _expected_starts(onsets, n_sub=N):
  """Start samples per condition from the spec definitions (section 5.1, plan)."""
  return {
    201: [o + k * n_sub for o in onsets[201] for k in range(2)],
    202: [o - n_sub for o in onsets[202]],
    **{c: [o + k * n_sub for o in onsets[c] for k in range(5)] for c in TARGETS},
  }


def _write_ebr(path, block, channels, fs=FS):
  """Own minimal EBR 1.0 writer (mas/01_DATA_SPEC.md section 2): header lines + <f8 block."""
  nc, ns = block.shape
  head = ["ebr binary 1.0", "data_type double", f"sampling_rate {fs}", f"samples {ns}",
          "bands 1", "band_1 Raw Data", f"channels {nc}"]
  head += [f"channel_{k} {c}" for k, c in enumerate(channels, 1)]
  head += ["trials 1", "trial_1 EEG Register", "comments 1", "comment_1 Sample selection",
           "marks 0", "end_header"]
  path.parent.mkdir(parents=True, exist_ok=True)
  payload = struct.pack(f"<{nc * ns}d", *np.ascontiguousarray(block, dtype=np.float64).ravel())
  path.write_bytes(("\n".join(head) + "\n").encode("ascii") + payload)
  return path


def _recording(n_trials=10, seed=0, spike_trial=None, channels=FILE_CHANNELS):
  """(len(channels), T) block: protocol MARK; scalp channel k = 10 uV sine at 5 + 3k Hz + noise.

  Returns (block, onsets). `spike_trial` adds a 400 uV spike to O1 in the first stimulus
  second of that trial (one sub-window rejected, vpp_high).
  """
  mark, onsets = _protocol_mark(n_trials, seed)
  T = mark.size
  rng = np.random.default_rng(100 + seed)
  tt = np.arange(T) / FS
  block = np.zeros((len(channels), T))
  for name in FILE_CHANNELS[:8]:
    k = FILE_CHANNELS.index(name)
    block[channels.index(name)] = 10 * np.sin(2 * np.pi * (5 + 3 * k) * tt) + rng.normal(0, 2, T)
  block[channels.index("TIMESTAMP")] = 1.637e12 + 1000 * tt
  block[channels.index("FLASHINGTIME")] = 0.005
  block[channels.index("MARK")] = mark
  if spike_trial is not None:
    stim = sorted(o for c in TARGETS for o in onsets[c])[spike_trial]
    block[channels.index("O1"), stim + 100:stim + 105] += 400.0
  return block, onsets


# --- P02.1 gate bounds --------------------------------------------------------------

def test_gate_sinusoid_analytic_ptp_std():
  """Known answer: 8 Hz sine, 256 samples at fs 256 (8 full periods): ptp = 2A, std = A/sqrt(2).

  Gate with limits 1 % around those values keeps it; limits 1 % beyond reject it.
  Tolerance 1e-9 on ptp/std. Source: analytic; roadmap P02.1.
  """
  for a in (0.25, 1.0, 10.0, 50.0):
    w = np.stack([_sine(a, 8.0), _sine(a, 8.0, phase=0.3), _sine(a, 8.0, phase=1.1)])
    flags = qc.window_quality_flags(w, vpp_min=0, vpp_max=1e9, std_min=0, std_max=1e9)
    np.testing.assert_allclose(np.ptp(w[0]), 2 * a, rtol=1e-12)
    np.testing.assert_allclose(flags["vpp"][0][0], 2 * a, rtol=1e-12)
    np.testing.assert_allclose(flags["std"][0], a / np.sqrt(2), rtol=1e-9)
    inside = qc.validate_eeg_windows(w, vpp_min=1.9 * a, vpp_max=2.01 * a,
                                     std_min=0.99 * a / np.sqrt(2), std_max=1.01 * a / np.sqrt(2))
    assert inside.tolist() == [1]
    for kw in (dict(vpp_min=2.02 * a), dict(vpp_max=1.98 * a),
               dict(std_min=1.01 * a / np.sqrt(2)), dict(std_max=0.99 * a / np.sqrt(2))):
      lim = dict(vpp_min=0.0, vpp_max=1e9, std_min=0.0, std_max=1e9)
      lim.update(kw)
      assert qc.validate_eeg_windows(w, **lim).tolist() == [0], (a, kw)


def test_gate_bounds_inclusive_and_every_channel():
  """Known answer: 3 ch x 256 square waves of A = 10 (ptp 20, std 10 exactly).

  Limits equal to the values are accepted (inclusive); the next float beyond any limit,
  on any single channel, rejects the window (1 only if every channel is inside). The mask
  is int, one entry per window. Exact. Source: roadmap P02.1 (inclusive, every channel).
  """
  ok = np.stack([_square(10.0)] * 3)
  lim = dict(vpp_min=20.0, vpp_max=20.0, std_min=10.0, std_max=10.0)
  m = qc.validate_eeg_windows(ok[None], **lim)
  assert m.tolist() == [1] and np.issubdtype(m.dtype, np.integer)
  stack = [ok]
  for c in range(3):
    for a in (np.nextafter(10.0, 0.0), np.nextafter(10.0, 20.0)):  # ptp and std both move
      w = ok.copy()
      w[c] = _square(a)
      stack.append(w)
  mask = qc.validate_eeg_windows(np.stack(stack), **lim)
  assert mask.tolist() == [1] + [0] * 6
  # one channel failing only std (ptp kept at 20 by two extreme samples, std lowered)
  for c in range(3):
    w = ok.copy()
    w[c] = 0.0
    w[c, 0], w[c, 1] = 10.0, -10.0  # ptp 20, std = 10 * sqrt(2/256) < 10
    assert qc.validate_eeg_windows(w, **lim).tolist() == [0]
  # defaults are the shared gate's (5, 120, 1, 35), inclusive at 5 and 120
  assert qc.validate_eeg_windows(np.stack([_square(2.5)] * 3)).tolist() == [1]   # ptp 5, std 2.5
  assert qc.validate_eeg_windows(np.stack([_square(60.0)] * 3)).tolist() == [0]  # std 60 > 35
  assert qc.validate_eeg_windows(np.stack([_square(2.4)] * 3)).tolist() == [0]   # ptp 4.8 < 5


def test_filter_dataset_keeps_mask_one_rows_in_order():
  """Known answer: X rows 0..5, mask [1,0,1,1,0,1] -> rows [0,2,3,5], y likewise. Exact. [own]"""
  X = np.arange(6 * 2 * 4, dtype=float).reshape(6, 2, 4)
  y = np.array([201, 202, 101, 102, 103, 104])
  Xk, yk = qc.filter_dataset(X, y, np.array([1, 0, 1, 1, 0, 1]))
  np.testing.assert_array_equal(Xk, X[[0, 2, 3, 5]])
  assert yk.tolist() == [201, 101, 102, 104]
  with pytest.raises(ValueError):
    qc.filter_dataset(X, y[:5], np.ones(6))


def test_segment_and_validate_layout_window_channel_time():
  """Known answer (R6): ramp t + 1e6 c, 1000 samples, n = 256 -> 3 windows (remainder dropped),
  window k channel c = arange(256k, 256(k+1)) + 1e6 c; layout (window, channel, time). Exact.
  """
  x = _ramp(4, 1000)
  W, mask = qc.segment_and_validate_eeg(x, FS, 1.0, vpp_min=0, vpp_max=1e12, std_min=0,
                                        std_max=1e12)
  assert W.shape == (3, 4, 256) and mask.tolist() == [1, 1, 1]
  for k in range(3):
    for c in range(4):
      np.testing.assert_array_equal(W[k, c], np.arange(256 * k, 256 * (k + 1)) + 1e6 * c)


def test_summarize_window_quality_known_ranges(capsys):
  """Known answer: square windows A = 1, 2, 3 (ptp 2/4/6, std 1/2/3); limits vpp [3, 200],
  std [0.5, 60] -> 2 valid, 1 rejected (vpp_low); observed vpp 2..6, std 1..3. Exact. [own]
  """
  W = np.stack([np.stack([_square(a)] * 2) for a in (1.0, 2.0, 3.0)])
  out = qc.summarize_window_quality(W, vpp_min=3.0, vpp_max=200.0, std_min=0.5, std_max=60.0,
                                    label="t")
  assert (out["n_windows"], out["n_valid"], out["n_rejected"]) == (3, 2, 1)
  assert out["reasons"]["vpp_low"] == 1 and out["reasons"]["vpp_high"] == 0
  assert (out["vpp_min_obs"], out["vpp_max_obs"]) == (2.0, 6.0)
  assert (out["std_min_obs"], out["std_max_obs"]) == (1.0, 3.0)
  assert "[3, 200]" in capsys.readouterr().out


# --- PF-07 -----------------------------------------------------------------------

def _buggy_extract_no_vpp_min(segment, fs, sub_window_sec=1.0, vpp_thresh=200.0,
                              std_range=(0.5, 60.0), quality_stats=None, vpp_min=0.5):
  """Historical PF-07 variant: gates with validate_eeg_windows but does not forward vpp_min."""
  x = np.asarray(segment, dtype=float)
  n = int(sub_window_sec * fs)
  k = x.shape[1] // n
  wins = x[:, :k * n].reshape(x.shape[0], k, n).transpose(1, 0, 2)
  mask = qc.validate_eeg_windows(wins, vpp_max=vpp_thresh, std_min=std_range[0],
                                 std_max=std_range[1])
  out = []
  for i in np.flatnonzero(mask == 1):
    f, p = periodogram(wins[i], fs=fs, axis=-1)
    out.append({"time_data": wins[i].copy(), "vpp": np.ptp(wins[i], -1),
                "std": np.std(wins[i], -1), "psd": p, "freqs": f, "sub_index": int(i)})
  return out


def _check_pf07(extract):
  """PF-07 known answer for an extractor: 1 s sines with Vpp 1.5, 2, 4, 4.9 uV (std = Vpp/(2 sqrt 2)
  = 0.53..1.73, inside std 0.5-60) are all kept by the legacy gate (vpp_min 0.5); Vpp 0.4 uV
  (below 0.5; std_min lowered to 0.1 so only vpp_min decides) is dropped."""
  for vpp in (1.5, 2.0, 4.0, 4.9):
    seg = np.stack([_sine(vpp / 2, 10.0)] * 7)
    np.testing.assert_allclose(np.ptp(seg, axis=-1), vpp, rtol=1e-9)
    assert len(extract(seg, FS)) == 1, f"Vpp {vpp} uV rejected by the legacy gate (PF-07)"
  seg = np.stack([_sine(0.2, 10.0)] * 7)
  assert len(extract(seg, FS, std_range=(0.1, 60.0))) == 0


def test_pf07_shared_defaults_reject_but_legacy_extractor_keeps_low_vpp():
  """Known answer (PF-07): a 1 s sine with Vpp 2 uV (std 0.707) is rejected by
  validate_eeg_windows defaults (vpp_min 5) and kept by extract_clean_subwindows_psd
  (legacy vpp_min 0.5); Vpp 4 uV, std 1.41 passes every default except vpp_min 5, so the
  default mask is 0 only because of vpp_min. Exact. Source: PF-07, roadmap P02.2.
  """
  w2 = np.stack([_sine(1.0, 10.0)] * 7)
  np.testing.assert_allclose(np.std(w2, axis=-1), 1 / np.sqrt(2), rtol=1e-9)
  assert qc.validate_eeg_windows(w2).tolist() == [0]
  w4 = np.stack([_sine(2.0, 10.0)] * 7)
  assert qc.validate_eeg_windows(w4).tolist() == [0]
  assert qc.validate_eeg_windows(w4, vpp_min=0.5).tolist() == [1]
  _check_pf07(pe.extract_clean_subwindows_psd)
  assert len(pe.extract_clean_subwindows_psd(w2, FS, vpp_min=5.0)) == 0  # forwarded


def test_pf07_check_fails_on_extractor_that_does_not_forward_vpp_min():
  """The PF-07 check above fails on the historical variant (vpp_min not forwarded), proving
  the test bites. Source: PF-07."""
  with pytest.raises(AssertionError, match="PF-07"):
    _check_pf07(_buggy_extract_no_vpp_min)


def test_pf07_condition_pipeline_forwards_vpp_min(monkeypatch):
  """Known answer: a protocol recording whose every channel is a 1.5 uV-amplitude 10 Hz sine
  (Vpp 3 uV, std 1.06) gives all 16 windows of 2 trials with the legacy call, and 0 when the
  PF-07 variant is patched in as the extractor. Exact. Source: PF-07, plan PF-07 row.
  """
  mark, _ = _protocol_mark(5, seed=1)
  mark = mark[:5 * FS + 2 * 15 * FS]
  x = np.stack([_sine(1.5, 10.0, n=mark.size)] * 7)
  args = dict(vpp_thresh=200.0, std_range=(0.5, 60.0), vpp_min=0.5)
  recs = pe.process_condition_windows_with_baseline(x, mark, FS, **args)
  assert sum(len(v) for v in recs.values()) == 2 * (2 + 1 + 5)
  monkeypatch.setattr(pe, "extract_clean_subwindows_psd", _buggy_extract_no_vpp_min)
  recs = pe.process_condition_windows_with_baseline(x, mark, FS, **args)
  assert sum(len(v) for v in recs.values()) == 0


# --- P02.2 sub-windows and PSD ---------------------------------------------------------

def test_subwindows_psd_peak_and_density():
  """Known answer: 5 s, 7 ch, 10 Hz sine A = 10 at fs 256 -> 5 records of (7, 256), sub_index
  0..4, time_data = consecutive slices; freqs = 0..128 step fs/N = 1 Hz; PSD argmax 10 Hz with
  density A**2 * N / (2 fs) = 50 uV^2/Hz (rtol 1e-9); vpp = ptp(time_data) ~ 20 (rtol 1e-2,
  phase-shifted samples miss the peak), std = 10/sqrt(2) (rtol 1e-9).
  A 5.5 s segment also gives 5 records (remainder dropped). Source: periodogram docs, analytic.
  """
  seg = np.stack([_sine(10.0, 10.0, n=5 * N, phase=0.2 * c) for c in range(7)])
  recs = pe.extract_clean_subwindows_psd(seg, FS)
  assert len(recs) == 5 and [r["sub_index"] for r in recs] == [0, 1, 2, 3, 4]
  for k, r in enumerate(recs):
    assert r["time_data"].shape == (7, 256)
    np.testing.assert_array_equal(r["time_data"], seg[:, k * N:(k + 1) * N])
    np.testing.assert_array_equal(r["freqs"], np.arange(129, dtype=float))
    assert r["psd"].shape == (7, 129)
    assert np.all(np.argmax(r["psd"], axis=-1) == 10)
    np.testing.assert_allclose(r["psd"][:, 10], 50.0, rtol=1e-9)
    np.testing.assert_array_equal(r["vpp"], np.ptp(r["time_data"], axis=-1))
    np.testing.assert_allclose(r["vpp"], 20.0, rtol=1e-2)  # sampled peaks: 1 - cos(pi/25.6) < 1 %
    np.testing.assert_allclose(r["std"], 10 / np.sqrt(2), rtol=1e-9)
  longer = np.concatenate([seg, seg[:, :N // 2]], axis=1)
  assert len(pe.extract_clean_subwindows_psd(longer, FS)) == 5


def test_subwindow_spike_rejected_and_counted():
  """Known answer: a 300 uV spike (> vpp_thresh 200) in sub-window 2 of channel 3 -> 4 records
  with sub_index [0, 1, 3, 4]; quality_stats n_total 5, n_accepted 4, n_rejected 1, reason
  vpp_high 1, failing channel [3]. Exact. Source: plan, roadmap P02.2.
  """
  seg = np.stack([_sine(10.0, 10.0, n=5 * N)] * 7)
  seg[3, 2 * N + 50] += 300.0
  qs = qc.new_quality_stats()
  recs = pe.extract_clean_subwindows_psd(seg, FS, vpp_thresh=200.0, std_range=(0.5, 60.0),
                                         quality_stats=qs, vpp_min=0.5)
  assert [r["sub_index"] for r in recs] == [0, 1, 3, 4]
  assert (qs["n_total"], qs["n_accepted"], qs["n_rejected"]) == (5, 4, 1)
  assert qs["reasons"]["vpp_high"] == 1 and qs["reasons"]["vpp_low"] == 0
  assert len(qs["rejected"]) == 1 and qs["rejected"][0]["channels"] == [3]
  assert qs["rejected"][0]["sub_index"] == 2


# --- P02.2 segment definitions -------------------------------------------------------------

def _records_by_start(recs):
  return {c: [int(r["time_data"][0, 0]) for r in recs[c]] for c in recs}


def test_segments_sample_index_ramp_protocol_40_trials():
  """Known answer (section 3 timing, 40 trials = 8 per target, ramp EEG t + 1e6 c, gate off):
  80 windows of 201 = [onset, onset+512) in 2; 40 of 202 = [onset-256, onset) (PF-13);
  40 per target = [onset, onset+1280) in 5. The content of each window names its own
  samples, so starts are read from the data, not from record metadata. Each 202 window equals
  the second 201 sub-window of its trial (the cue window lies in the fixation period, PF-13).
  Exact. Source: mas/01_DATA_SPEC.md sections 3 and 5.1, plan segment definitions.
  """
  mark, onsets = _protocol_mark(40, seed=7)
  assert mark.size == 154880
  x = _ramp(7, mark.size)
  recs = pe.process_condition_windows_with_baseline(x, mark, FS, **WIDE)
  counts = {c: len(recs[c]) for c in ORDER}
  assert counts == {201: 80, 202: 40, 101: 40, 102: 40, 103: 40, 104: 40, 105: 40}
  got = _records_by_start(recs)
  exp = _expected_starts(onsets)
  for c in ORDER:
    assert got[c] == exp[c], c
    for r in recs[c]:
      s = int(r["time_data"][0, 0])
      np.testing.assert_array_equal(r["time_data"], _ramp(7, mark.size)[:, s:s + N])
  for k, o in enumerate(onsets[202]):
    assert int(recs[202][k]["time_data"][0, -1]) == o - 1  # ends just before the pulse
    np.testing.assert_array_equal(recs[202][k]["time_data"], recs[201][2 * k + 1]["time_data"])


def test_prepare_feature_matrix_on_protocol_ramp_row_order():
  """Known answer: on the 40-trial ramp, X_time (320, 7, 256), y = 80x201, 40x202, then
  40 each of 101..105; within a condition X_time[:, 0, 0] (the start sample) increases;
  X_time[i, c, 0] - X_time[i, 0, 0] = 1e6 c (channel axis 1, R6). Exact. Source: section 5.1.
  """
  mark, onsets = _protocol_mark(40, seed=7)
  recs = pe.process_condition_windows_with_baseline(_ramp(7, mark.size), mark, FS, **WIDE)
  X_psd, X_time, y = pe.prepare_feature_matrix(recs)
  assert X_time.shape == (320, 7, 256) and X_psd.shape == (320, 217) and y.dtype == np.int64
  assert y.tolist() == [201] * 80 + [202] * 40 + sum(([c] * 40 for c in TARGETS), [])
  exp = _expected_starts(onsets)
  assert X_time[:, 0, 0].astype(int).tolist() == sum((exp[c] for c in ORDER), [])
  np.testing.assert_array_equal(X_time[:, :, 0] - X_time[:, :1, 0], np.tile(1e6 * np.arange(7), (320, 1)))


def test_edge_segments_are_dropped_exactly():
  """Known answer: recording cut 3 s after the last stimulus onset -> that trial's 5 stimulus
  windows are dropped (no partial trial), its 201/202 kept; a 202 pulse at sample 100 -> no
  cue window; boundaries exact: stimulus onset at T - 1280 kept, T - 1279 dropped; 202 onset at
  256 kept, at 255 dropped; 201 at T - 512 kept, T - 511 dropped. Exact. Source: plan, P02.2.
  """
  mark, onsets = _protocol_mark(5, seed=3)
  last = max(o for c in TARGETS for o in onsets[c])
  last_code = [c for c in TARGETS if last in onsets[c]][0]
  mark = mark[:last + 3 * FS].copy()
  mark[100] = 202
  recs = pe.process_condition_windows_with_baseline(_ramp(7, mark.size), mark, FS, **WIDE)
  assert len(recs[last_code]) == 5 * (len(onsets[last_code]) - 1)
  assert sum(len(recs[c]) for c in TARGETS) == 5 * 4
  assert len(recs[201]) == 10 and len(recs[202]) == 5
  assert 100 - N not in _records_by_start(recs)[202]

  def one(code, onset, T=4000):
    m = np.zeros(T)
    m[onset] = code
    r = pe.process_condition_windows_with_baseline(_ramp(2, T), m, FS, **WIDE)
    return len(r[code])

  T = 4000
  assert (one(101, T - 1280), one(101, T - 1279)) == (5, 0)
  assert (one(202, 256), one(202, 255)) == (1, 0)
  assert (one(201, T - 512), one(201, T - 511)) == (2, 0)


def test_plateau_pulses_give_same_windows_as_single_sample_pulses():
  """Known answer: 3-sample MARK plateaus give exactly the windows (count, order, content) of
  single-sample pulses; one onset per event at the plateau's first sample. Exact.
  Source: mas/02_REQUIREMENTS.md section 7 (event onsets), section 3 onset rule.
  """
  m1, on1 = _protocol_mark(10, seed=5, pulse_len=1)
  m3, on3 = _protocol_mark(10, seed=5, pulse_len=3)
  assert on1 == on3 and np.count_nonzero(m3) == 3 * np.count_nonzero(m1)
  x = _ramp(7, m1.size)
  a = pe.prepare_feature_matrix(pe.process_condition_windows_with_baseline(x, m1, FS, **WIDE))
  b = pe.prepare_feature_matrix(pe.process_condition_windows_with_baseline(x, m3, FS, **WIDE))
  for u, v in zip(a, b):
    np.testing.assert_array_equal(u, v)
  assert len(a[2]) == 80
  for c in ORDER:
    assert pe.find_event_onsets(m3, c).tolist() == on1[c]


# --- P02.2 feature matrix (R6) -----------------------------------------------------------

def _planted_records(seed=0):
  """Records of all 7 conditions (plus an unlisted 203), dict in shuffled order, 3 per code;
  channel c carries a 10 uV sine at 5 + 3c Hz; record j of code k has noise seed (k, j)."""
  rng = np.random.default_rng(seed)
  codes = list(rng.permutation(list(ORDER) + [203]))
  recs = {}
  for code in codes:
    recs[int(code)] = []
    for j in range(3):
      g = np.random.default_rng([int(code), j])
      w = np.stack([_sine(10.0, 5 + 3 * c, phase=g.uniform(0, 6)) for c in range(7)])
      w = w + g.normal(0, 0.5, w.shape)
      f, p = periodogram(w, fs=FS, axis=-1)
      recs[int(code)].append({"time_data": w, "psd": p, "freqs": f, "id": (int(code), j)})
  return recs


def _check_channel_major(X_psd, n_ch=7):
  for c in range(n_ch):
    assert np.all(np.argmax(X_psd[:, 31 * c:31 * c + 31], axis=1) == 3 * c), f"channel {c}"


def test_feature_matrix_order_and_channel_major_flatten():
  """Known answer: y = [201]*3, [202]*3, [101..105]*3 each, regardless of dict order; 203
  ignored; X_time rows are the records in list order; X_time (21, 7, 256), X_psd (21, 217);
  X_psd[i, 31c + j] = psd[c, 5 + j] (bins 5..35 Hz inclusive); argmax of block c is 3c
  (planted 5 + 3c Hz). Exact. Source: mas/01_DATA_SPEC.md section 5.1, R6.
  """
  recs = _planted_records()
  assert list(recs)[:7] != list(ORDER)
  X_psd, X_time, y = pe.prepare_feature_matrix(recs, target_conditions=ORDER, freq_range=(5, 35))
  assert X_time.shape == (21, 7, 256) and X_psd.shape == (21, 217)
  assert y.tolist() == sum(([c] * 3 for c in ORDER), [])
  rows = [r for c in ORDER for r in recs[c]]
  for i, r in enumerate(rows):
    np.testing.assert_array_equal(X_time[i], r["time_data"])
    for c in range(7):
      np.testing.assert_array_equal(X_psd[i, 31 * c:31 * (c + 1)], r["psd"][c, 5:36])
  _check_channel_major(X_psd)


def test_channel_major_check_fails_on_frequency_major_flatten():
  """The R6 check above fails on the plausible bug: frequency-major flatten psd[:, sel].T."""
  recs = _planted_records()
  rows = [r for c in ORDER for r in recs[c]]
  X_bad = np.stack([r["psd"][:, 5:36].T.reshape(-1) for r in rows])
  with pytest.raises(AssertionError, match="channel"):
    _check_channel_major(X_bad)


def test_psd_bins_depend_on_fs_pf04():
  """Known answer (PF-04): 256-sample windows at fs 256 give 31 bins in 5..35 Hz (217 for 7 ch);
  the same windows labelled fs 250 give bins k * 250/256 -> k = 6..35, 30 bins (210). Exact.
  Source: periodogram bin spacing fs/N; decisions.md 2026-10-24 (P02 uses header fs)."""
  seg = np.stack([_sine(10.0, 10.0)] * 7)
  for fs, nbins in ((256, 31), (250, 30)):
    recs = {201: pe.extract_clean_subwindows_psd(seg, fs, sub_window_sec=N / fs)}
    assert len(recs[201]) == 1
    X_psd, X_time, _ = pe.prepare_feature_matrix(recs)
    assert X_time.shape == (1, 7, 256) and X_psd.shape == (1, 7 * nbins)


# --- P02.3 script ---------------------------------------------------------------------

@pytest.fixture
def rp():
  return importlib.import_module("scripts.preprocessing.run_preprocessing")


def _main(rp, root, *extra):
  return rp.main(["--raw-dir", str(root / "raw"), "--processed-dir", str(root / "proc"),
                  "--figures-dir", str(root / "fig"), *extra])


def test_script_windows_equal_slices_of_continuous_filtered_recording(tmp_path, rp):
  """Known answer (R3): channels stored in shuffled file order; each saved X_time row equals
  apply_iir_bandpass(full continuous recording, 256, 1, 60, 4)[name-selected scalp, start:start+256]
  with starts from the spec definitions (not from the script), atol 1e-12; X_psd equals the
  periodogram of those slices, channel-major, 5..35 Hz. Source: R3, PF-06, roadmap P02.3.
  """
  chans = ["MARK", "O2", "TIMESTAMP", "PO4", "PO7", "Oz", "FLASHINGTIME", "PO3", "O1", "PO8", "POz"]
  block, onsets = _recording(n_trials=10, seed=4, channels=chans)
  _write_ebr(tmp_path / "raw" / "S03" / "OO.ebr", block, chans)
  assert _main(rp, tmp_path, "--no-figures") == 0
  X_time = np.load(tmp_path / "proc" / "S03" / "X_time_windows.npy")
  X_psd = np.load(tmp_path / "proc" / "S03" / "X_psd_features.npy")
  y = np.load(tmp_path / "proc" / "S03" / "y_labels.npy")
  x = block[[chans.index(c) for c in SCALP]]
  x_f = apply_iir_bandpass(x, FS, 1.0, 60.0, 4)
  exp = _expected_starts(onsets)
  starts = sum((exp[c] for c in ORDER), [])
  assert y.tolist() == sum(([c] * len(exp[c]) for c in ORDER), [])
  expected = np.stack([x_f[:, s:s + N] for s in starts])
  assert X_time.shape == expected.shape == (80, 7, 256)
  np.testing.assert_allclose(X_time, expected, rtol=0, atol=1e-12)
  _, p = periodogram(expected, fs=FS, axis=-1)
  np.testing.assert_allclose(X_psd, p[:, :, 5:36].reshape(80, -1), rtol=1e-12, atol=1e-12)


def test_r3_check_fails_on_per_window_filtering(tmp_path, rp, monkeypatch):
  """The R3 comparison above fails on the plausible bug: no continuous filter, each 1 s window
  filtered on its own (edge distortion; max abs error far above 1e-12)."""
  block, onsets = _recording(n_trials=5, seed=4)
  _write_ebr(tmp_path / "raw" / "S03" / "OO.ebr", block, FILE_CHANNELS)
  orig = pe.extract_clean_subwindows_psd

  def per_window(segment, fs, sub_window_sec=1.0, **kw):
    n = int(sub_window_sec * fs)
    s = np.asarray(segment, dtype=float)
    k = s.shape[1] // n
    s = np.concatenate([apply_iir_bandpass(s[:, i * n:(i + 1) * n], fs, 1.0, 60.0, 4)
                        for i in range(k)], axis=1)
    return orig(s, fs, sub_window_sec=sub_window_sec, **kw)

  monkeypatch.setattr(rp, "apply_iir_bandpass", lambda d, *a, **k: np.asarray(d, dtype=float))
  monkeypatch.setattr(pe, "extract_clean_subwindows_psd", per_window)
  assert _main(rp, tmp_path, "--no-figures") == 0
  X_time = np.load(tmp_path / "proc" / "S03" / "X_time_windows.npy")
  x_f = apply_iir_bandpass(block[[FILE_CHANNELS.index(c) for c in SCALP]], FS, 1.0, 60.0, 4)
  exp = _expected_starts(onsets)
  expected = np.stack([x_f[:, s:s + N] for c in ORDER for s in exp[c]])
  assert X_time.shape == expected.shape
  with pytest.raises(AssertionError):
    np.testing.assert_allclose(X_time, expected, rtol=0, atol=1e-12)
  assert np.max(np.abs(X_time - expected)) > 1e-3


def _png_ok(path):
  return path.is_file() and path.stat().st_size > 1000 and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_script_tree_all_subjects_root_copy_skip_and_figures(tmp_path, rp, capsys):
  """Known answer: raw tree S01 (spike in one stimulus second), S02 (no recording), S03, S04,
  plus a non-subject folder. --all: per-subject arrays with n = 80 for S03/S04 and 79 for S01
  (one 103/.. window rejected), the line `[-] Skipping S02: ...`, root arrays equal to S03
  (not S04, the last subject processed; PF-09), PSD figures per subject and the verbatim root
  figure. Exact. Source: roadmap P02.3, plan Q1 (decisions.md), PF-09.
  """
  for s, seed, spike in (("S01", 1, 3), ("S03", 3, None), ("S04", 9, None)):
    block, _ = _recording(n_trials=10, seed=seed, spike_trial=spike)
    _write_ebr(tmp_path / "raw" / s / "OO.ebr", block, FILE_CHANNELS)
  (tmp_path / "raw" / "S02").mkdir()
  (tmp_path / "raw" / "misc").mkdir()
  assert _main(rp, tmp_path, "--all") == 0
  out = capsys.readouterr().out
  assert "[-] Skipping S02: " in out
  assert "misc" not in out
  arrays = ("X_psd_features", "X_time_windows", "y_labels")
  n_exp = {"S01": 79, "S03": 80, "S04": 80}
  for s, n in n_exp.items():
    X_psd, X_time, y = (np.load(tmp_path / "proc" / s / f"{a}.npy") for a in arrays)
    assert X_psd.shape == (n, 217) and X_time.shape == (n, 7, 256) and y.shape == (n,)
    assert set(np.unique(y)) <= set(ORDER)
    assert _png_ok(tmp_path / "fig" / "spectra" / s / "average_psd_by_condition.png")
  for a in arrays:
    root = np.load(tmp_path / "proc" / f"{a}.npy")
    np.testing.assert_array_equal(root, np.load(tmp_path / "proc" / "S03" / f"{a}.npy"))
    if a != "y_labels":  # S03 and S04 have the same label sequence (nothing rejected)
      assert not np.array_equal(root, np.load(tmp_path / "proc" / "S04" / f"{a}.npy"))
  assert not (tmp_path / "proc" / "S02").exists()
  assert _png_ok(tmp_path / "fig" / "spectra" / "average_psd_by_condition.png")


def test_script_default_subject_is_s03(tmp_path, rp):
  """Known answer: with no subject flag only S03 is processed (its folder and the root
  arrays exist, S01 does not). Exact. Source: roadmap P02.3 (`--subject` default S03)."""
  for s in ("S01", "S03"):
    block, _ = _recording(n_trials=5, seed=int(s[1:]))
    _write_ebr(tmp_path / "raw" / s / "OO.ebr", block, FILE_CHANNELS)
  assert _main(rp, tmp_path, "--no-figures") == 0
  assert (tmp_path / "proc" / "S03" / "y_labels.npy").is_file()
  assert (tmp_path / "proc" / "y_labels.npy").is_file()
  assert not (tmp_path / "proc" / "S01").exists()
  assert len(np.load(tmp_path / "proc" / "y_labels.npy")) == 40


def test_script_single_non_root_subject_does_not_write_root(tmp_path, rp):
  """Known answer (PF-09): `--subject S01` writes S01 only; no root arrays appear. Exact."""
  block, _ = _recording(n_trials=5, seed=1)
  _write_ebr(tmp_path / "raw" / "S01" / "OO.ebr", block, FILE_CHANNELS)
  assert _main(rp, tmp_path, "--subject", "S01", "--no-figures") == 0
  assert (tmp_path / "proc" / "S01" / "X_time_windows.npy").is_file()
  assert not (tmp_path / "proc" / "X_time_windows.npy").exists()


# --- P02.4 plots -------------------------------------------------------------------------

def test_plots_written_under_agg(tmp_path):
  """Known answer: the three figures are PNG files (signature, > 1 kB) under the Agg backend,
  including an empty condition, and no figure stays open. Source: roadmap P02.4, [own]."""
  import matplotlib
  import matplotlib.pyplot as plt
  from src.visualization import signal_plots as sp
  assert matplotlib.get_backend().lower() == "agg"
  recs = {k: v for k, v in _planted_records().items() if k != 104}
  recs[104] = []
  paths = [
    sp.plot_eeg_window(recs[101][0]["time_data"], FS, tmp_path / "a" / "w.png",
                       channel_names=SCALP),
    sp.plot_average_psd_by_condition(recs, tmp_path / "b" / "psd.png"),
    sp.plot_stimulus_vs_baseline_psd(recs, tmp_path / "c" / "svb.png"),
  ]
  for p in paths:
    assert _png_ok(p)
  assert plt.get_fignums() == []
