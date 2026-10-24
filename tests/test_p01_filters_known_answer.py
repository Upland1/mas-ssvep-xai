"""Known-answer tests for src/preprocessing/signal/filters.py (P01.3).

`apply_iir_bandpass(data, fs, lowcut=1.0, highcut=60.0, order=4)` must be
`filtfilt(*iirfilter(order, [low/nyq, high/nyq], btype="bandpass",
ftype="butter"), data)` along the last axis (roadmap P01.3, quoted in
00_assignment.md, [roadmap]). Gains follow from the Butterworth magnitude
response squared by the forward-backward pass ([own], analytic); zero phase from
`filtfilt` (SciPy docs, [scipy]). fs = 256 Hz, the recordings' header rate
(mas/01_DATA_SPEC.md §2); fs is an argument, never a default (PF-04).
"""

import inspect

import numpy as np
import pytest
from scipy.signal import filtfilt, iirfilter, lfilter

from src.preprocessing.signal.filters import apply_iir_bandpass

FS = 256.0
T = np.arange(int(10 * FS)) / FS                     # 10 s
CENTRAL = slice(int(2.5 * FS), int(7.5 * FS))        # central 5 s, away from edges


def _rms(x):
  return float(np.sqrt(np.mean(np.square(x))))


@pytest.mark.parametrize("f0, lo, hi", [(10.0, 0.98, 1.02), (24.0, 0.98, 1.02),
                                        (0.2, 0.0, 0.05), (100.0, 0.0, 0.05)])
def test_bandpass_gain(f0, lo, hi):
  """Known answer [own, analytic]: 1-60 Hz order-4 Butterworth applied forward and
  backward at fs 256 has gain |H|^2 ~ 1 at 10 and 24 Hz (+-0.02) and < 0.05 at 0.2 Hz
  and 100 Hz. Measured as central-segment RMS ratio of a unit sinusoid."""
  x = np.sin(2 * np.pi * f0 * T)
  y = apply_iir_bandpass(x, FS)
  g = _rms(y[CENTRAL]) / _rms(x[CENTRAL])
  assert lo <= g <= hi, g


def _peak_lag(x, y, max_lag, margin=100):
  """Lag k (samples) maximising sum x[n] * y[n + k] over a central segment."""
  c = x[margin:len(x) - margin]
  lags = np.arange(-max_lag, max_lag + 1)
  cc = [np.dot(c, y[margin + k:len(y) - margin + k]) for k in lags]
  return int(lags[int(np.argmax(cc))])


@pytest.mark.parametrize("f0", [10.0, 24.0])
def test_zero_phase_lag_sinusoid(f0):
  """Known answer [scipy filtfilt]: the cross-correlation of output and input for a
  10 Hz (plan) and a 24 Hz sinusoid peaks at lag 0 (tolerance 0 samples)."""
  x = np.sin(2 * np.pi * f0 * T)
  y = apply_iir_bandpass(x, FS)
  assert _peak_lag(x, y, max_lag=int(FS / f0 / 2) - 1) == 0


def test_zero_phase_lag_broadband():
  """Known answer [scipy filtfilt]: forward-backward filtering has a symmetric
  effective impulse response, so for white noise the input-output cross-correlation
  peaks at lag 0 (tolerance 0 samples)."""
  x = np.random.default_rng(0).standard_normal(int(10 * FS))
  assert _peak_lag(x, apply_iir_bandpass(x, FS), max_lag=20) == 0


def test_zero_phase_check_rejects_causal_variant():
  """Mutation check: a causal one-pass `lfilter` with the same b, a peaks at a
  nonzero lag on white noise (2 samples here), so the broadband test catches it.
  The 10 Hz sinusoid alone would not: the causal phase there is only -5.6 deg
  (0.39 samples), which rounds to lag 0."""
  b, a = iirfilter(4, [1 / 128, 60 / 128], btype="bandpass", ftype="butter")
  x = np.random.default_rng(0).standard_normal(int(10 * FS))
  assert _peak_lag(x, lfilter(b, a, x), max_lag=20) != 0


def test_filter_axis_last():
  """Known answer [roadmap]: a (2, 3, T) array is filtered along the last axis; each
  row equals filtering that row alone (1e-12); shape preserved, float64."""
  rng = np.random.default_rng(7)
  x = rng.standard_normal((2, 3, 1024))
  y = apply_iir_bandpass(x, FS)
  assert y.shape == x.shape and y.dtype == np.float64
  for i in range(2):
    for j in range(3):
      np.testing.assert_allclose(y[i, j], apply_iir_bandpass(x[i, j], FS), rtol=0, atol=1e-12)


def test_filter_axis_check_rejects_flattened_variant():
  """Mutation check: filtering the flattened array (rows concatenated) differs from
  per-row filtering by far more than 1e-12, so the axis test catches it."""
  rng = np.random.default_rng(7)
  x = rng.standard_normal((2, 3, 1024))
  b, a = iirfilter(4, [1 / 128, 60 / 128], btype="bandpass", ftype="butter")
  bad = filtfilt(b, a, x.reshape(-1)).reshape(x.shape)
  assert np.max(np.abs(bad - apply_iir_bandpass(x, FS))) > 1e-3


def test_filter_equals_roadmap_formula():
  """Known answer [roadmap]: on random input at fs 256 the output equals
  filtfilt(*iirfilter(4, [1/128, 60/128], btype='bandpass', ftype='butter'), x)
  within 1e-12."""
  rng = np.random.default_rng(42)
  x = rng.standard_normal((8, 2560)) * 50.0
  b, a = iirfilter(4, [1.0 / 128.0, 60.0 / 128.0], btype="bandpass", ftype="butter")
  np.testing.assert_allclose(apply_iir_bandpass(x, FS), filtfilt(b, a, x), rtol=0, atol=1e-12)


def test_filter_formula_nondefault_arguments():
  """Known answer [roadmap]: lowcut/highcut/order are passed through: (5, 40, 2) at
  fs 512 equals filtfilt(*iirfilter(2, [5/256, 40/256], ...), x) within 1e-12."""
  rng = np.random.default_rng(3)
  x = rng.standard_normal(4096)
  b, a = iirfilter(2, [5.0 / 256.0, 40.0 / 256.0], btype="bandpass", ftype="butter")
  y = apply_iir_bandpass(x, 512.0, lowcut=5.0, highcut=40.0, order=2)
  np.testing.assert_allclose(y, filtfilt(b, a, x), rtol=0, atol=1e-12)


def test_fs_is_required_and_used():
  """PF-04: fs has no default; and fs actually matters (fs 256 vs a 250 assumption
  give outputs that differ by >1e-6, so the formula test is sensitive to fs)."""
  sig = inspect.signature(apply_iir_bandpass)
  assert sig.parameters["fs"].default is inspect.Parameter.empty
  with pytest.raises(TypeError):
    apply_iir_bandpass(np.zeros(512))
  rng = np.random.default_rng(5)
  x = rng.standard_normal(2560)
  assert np.max(np.abs(apply_iir_bandpass(x, 256.0) - apply_iir_bandpass(x, 250.0))) > 1e-6


def test_defaults_are_roadmap_defaults():
  """Known answer [roadmap]: defaults lowcut=1.0, highcut=60.0, order=4."""
  p = inspect.signature(apply_iir_bandpass).parameters
  assert (p["lowcut"].default, p["highcut"].default, p["order"].default) == (1.0, 60.0, 4)


def test_input_not_modified():
  """Library code without side effects ([REQ §4]): the input array is unchanged."""
  rng = np.random.default_rng(9)
  x = rng.standard_normal((3, 1024))
  x0 = x.copy()
  apply_iir_bandpass(x, FS)
  np.testing.assert_array_equal(x, x0)
