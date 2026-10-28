"""P17 leak controls for the harmonic / intermediate banks, on synthetic recordings through the real build and
benchmark code (synthetic-tester; the real-data smoke showed 93.9 % -> 99.5 % with the harmonic bands).

(a) null recording (noise only, labels from the event marks): every bank scores at chance within a binomial bound;
(b) a trial's tone does not reach another trial's fixation / cue windows through the continuous narrow filters, at the
    protocol's own spacing (01_DATA_SPEC section 3: 201 at t, 202 at t+2, stimulus t+5..t+10, next 201 at t+15, so
    5 s of silence after a stimulus and 3 s before the next one); control: the same measure at 0.5 s is large;
(c) tone planted only at 2 f0: base stays at chance, harm and harm+mid beat it (the gain mechanism is real).
"""

import numpy as np
import pytest

from scripts import build_windows as bw
from scripts.benchmarks.feature_based import benchmark_n_subjects as B
from src.preprocessing.windowing import band_windows, build_bank, build_window_index
from tests import p16_synth as S

TH = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}
ALL = ("fbcca", "fbcsp", "harmonic", "intermediate")
Z = 4.0                      # one-sided 4 sd: false failure probability about 3e-5 per check
REPEATS = 3


def bound(p0, n):
  """Upper limit (fraction) of an accuracy at chance level `p0` on `n` independent windows."""
  return p0 + Z * np.sqrt(p0 * (1 - p0) / n)


def write_recording(root, name, mult, amp, n_trials=40, seed=3):
  """Built folder of a recording whose only signal is a tone at `mult` x the class frequency (none if amp = 0),
  Gaussian noise (std 5 uV) everywhere; the real build code, the protocol's event marks."""
  block = S.make_block(n_trials=n_trials, seed=seed, tone_amp=0.0)
  x, mark = block[:8], block[10]
  t = np.arange(x.shape[1]) / S.FS
  for code, f in S.TARGETS.items():
    for on in np.flatnonzero(mark == code):
      sl = slice(on, on + 5 * S.FS)
      x[:, sl] += amp * np.sin(2 * np.pi * mult * f * t[sl])[None]
  params = S.build_params("continuous", banks=ALL)
  built = bw.build_subject(x, mark, float(S.FS), params)
  bw.save_built(root / name, built, bw.build_meta(built, params, float(S.FS), name, "synthetic", "test"))


def run(root, name, bank, classes):
  out = B.evaluate_subject(root, name, thresholds=TH, fail_fraction=0.5, bank=bank, classes=classes, repeats=REPEATS)
  r = out["row"]
  assert r is not None, out["log"]
  return r, out


@pytest.fixture(scope="module")
def null_root(tmp_path_factory):
  root = tmp_path_factory.mktemp("null17")
  write_recording(root, "S01", 1, 0.0)
  return root


@pytest.fixture(scope="module")
def h2_root(tmp_path_factory):
  root = tmp_path_factory.mktemp("h2_17")
  write_recording(root, "S01", 2, 0.4)       # 2 f0 only, amplitude 0.4 uV against noise std 5 uV
  return root


# --- (a) null recording -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bank", ["base", "harm", "harm+mid"])
def test_null_recording_five_classes_is_at_chance(null_root, bank):
  r, _ = run(null_root, "S01", bank, 5)
  n = r["Clean Windows"]
  assert n == 200                                                      # 40 trials x 5 windows
  assert r["1.0s Acc (%)"] / 100 < bound(0.2, n)                       # 0.313
  assert r["2.0s Smoothed (%)"] / 100 < bound(0.2, n // 2)             # smoothing pairs windows: half the information
  assert r["1.0s Acc (%)"] > 100 * (0.2 - Z * np.sqrt(0.16 / n))       # and not far below either (no label inversion)


@pytest.mark.parametrize("bank", ["base", "harm", "harm+mid"])
def test_null_recording_six_classes_balanced_accuracy_is_at_chance(null_root, bank):
  r, out = run(null_root, "S01", bank, 6)
  _, cm = out["confusion"]
  n_c = cm.sum(1) / REPEATS                                            # windows per class
  sd = np.sqrt(sum((1 / 6) * (5 / 6) / n for n in n_c)) / 6            # sd of mean recall at recall 1/6
  assert r["1.0s BalAcc (%)"] / 100 < 1 / 6 + Z * sd
  assert r["2.0s BalAcc (%)"] / 100 < 1 / 6 + Z * sd * np.sqrt(2)
  assert r["2.0s FalseAct (%)"] + r["2.0s StimCorrect (%)"] < 100 + 1e-9


# --- (b) no carry-over between neighbouring trials --------------------------------------------------------------------

def protocol_windows(n_trials=12, tone_amp=1.0):
  """Noise-free block of the protocol with a different class in neighbouring trials, its window index, and the
  tone amplitude. Returns (x, idx, tone_slices)."""
  block = S.make_block(n_trials=n_trials, seed=7, tone_amp=0.0)
  x, mark = block[:8] * 0.0, block[10]
  t = np.arange(x.shape[1]) / S.FS
  onsets = sorted((on, int(mark[on])) for on in np.flatnonzero(np.isin(mark, list(S.TARGETS))))
  # neighbouring trials must carry different tones
  codes = [101 + (i % 5) for i in range(len(onsets))]
  tones = []
  for (on, _), c in zip(onsets, codes):
    sl = slice(on, on + 5 * S.FS)
    x[:, sl] += tone_amp * np.sin(2 * np.pi * S.TARGETS[c] * t[sl])[None]
    tones.append((c, sl))
  idx = build_window_index(mark, float(S.FS), [101, 102, 103, 104, 105])
  return x, idx, tones


@pytest.mark.parametrize("bank_name", ["fbcca", "fbcsp", "harmonic", "intermediate"])
def test_tone_does_not_carry_into_other_trials_windows(bank_name):
  x, idx, tones = protocol_windows()
  bank, _ = build_bank(bank_name, float(S.FS))
  n = S.FS
  w = band_windows(x, idx.starts, n, bank, "continuous")                # (n_win, B, C, T)
  own = np.abs(w[np.isin(idx.labels, [101, 102, 103, 104, 105])]).max()
  assert own > 0.3                                                      # the tone is seen inside the stimulus windows
  quiet = np.isin(idx.labels, [201, 202])
  spacing = np.diff(sorted(idx.starts[(idx.labels == 201) & (idx.sub_idx == 0)])) / S.FS
  assert np.allclose(spacing, 15.0, atol=1e-9)                          # 15 s between fixation onsets (DATA_SPEC section 3)
  leak = np.abs(w[quiet]).max()
  assert leak < 1e-4 * own, (bank_name, leak / own)                     # measured ~1e-6 or less


def test_the_leak_measure_has_power_at_a_short_spacing():
  """Control: with a window starting 0.5 s after the tone ends the same measure sees a clear leak, so the 1e-4 limit
  above would catch a spacing shorter than about 2 s (ringing of the order-2 narrow bands, ~1.05 s to 1 %)."""
  fs = float(S.FS)
  bank, _ = build_bank("harmonic", fs)
  t = np.arange(int(40 * fs)) / fs
  worst = {}
  for b in bank:
    f = (b.low + b.high) / 2
    x = np.zeros((1, t.size))
    a, e = int(10 * fs), int(15 * fs)
    x[0, a:e] = np.sin(2 * np.pi * f * t[a:e])
    for gap in (0.5, 2.0, 5.0):
      s = e + int(gap * fs)
      w = band_windows(x, np.array([s]), int(fs), [b], "continuous")
      worst[gap] = max(worst.get(gap, 0.0), np.abs(w).max())
  assert worst[0.5] > 1e-2 and worst[2.0] < 1e-3 and worst[5.0] < 1e-8


# --- (c) the gain mechanism is real ------------------------------------------------------------------------------------

def test_second_harmonic_only_tone_is_found_by_harm_not_by_base(h2_root):
  base, _ = run(h2_root, "S01", "base", 5)
  harm, _ = run(h2_root, "S01", "harm", 5)
  mid, _ = run(h2_root, "S01", "harm+mid", 5)
  n = base["Clean Windows"]
  chance = bound(0.2, n)
  assert base["1.0s Acc (%)"] / 100 < chance                            # the broad bands and the CCA cannot see it
  assert harm["1.0s Acc (%)"] / 100 > chance
  assert mid["1.0s Acc (%)"] / 100 > chance
  assert harm["1.0s Acc (%)"] - base["1.0s Acc (%)"] > 8.0              # a clear gain, in percentage points
  assert mid["1.0s Acc (%)"] - base["1.0s Acc (%)"] > 8.0
