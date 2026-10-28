"""Signal filters (P01: the legacy zero-phase broadband band-pass)."""

from typing import Optional

import numpy as np
from scipy.signal import filtfilt, iirfilter, iirnotch


def apply_iir_bandpass(data: np.ndarray, fs: float, lowcut: float = 1.0,
                       highcut: float = 60.0, order: int = 4) -> np.ndarray:
  """Zero-phase Butterworth band-pass along the last axis.

  `b, a = iirfilter(order, [lowcut/nyq, highcut/nyq], btype="bandpass",
  ftype="butter")` with `nyq = fs / 2`, applied with `filtfilt(b, a, data,
  axis=-1)` and scipy's default padding (roadmap P01.3). `fs` is required (no
  sampling-rate default, PF-04). Returns a new float64 array of the input shape.
  Raises ValueError unless `fs > 0` and `0 < lowcut < highcut < fs / 2`.
  """
  if not fs > 0:
    raise ValueError(f"fs must be positive, got {fs}")
  nyq = 0.5 * fs
  if not 0 < lowcut < highcut < nyq:
    raise ValueError(f"need 0 < lowcut < highcut < fs/2 = {nyq:g} Hz, got {lowcut}, {highcut}")
  b, a = iirfilter(order, [lowcut / nyq, highcut / nyq], btype="bandpass", ftype="butter")
  return filtfilt(b, a, np.asarray(data, dtype=np.float64), axis=-1)


def apply_notch(data: np.ndarray, fs: float, notch_hz: float = 60.0, q: float = 30.0) -> np.ndarray:
  """Zero-phase IIR notch (`iirnotch(notch_hz, q, fs)`, `filtfilt`) along the last axis (P16, mains).

  Raises ValueError unless `fs > 0`, `0 < notch_hz < fs / 2` and `q > 0`.
  """
  if not fs > 0 or not 0 < notch_hz < 0.5 * fs or not q > 0:
    raise ValueError(f"need fs > 0, 0 < notch_hz < fs/2 and q > 0, got fs={fs}, notch_hz={notch_hz}, q={q}")
  b, a = iirnotch(notch_hz, q, fs=fs)
  return filtfilt(b, a, np.asarray(data, dtype=np.float64), axis=-1)


def broadband_filter(data: np.ndarray, fs: float, lowcut: float, highcut: float, order: int,
                     notch_hz: Optional[float] = None, notch_q: float = 30.0) -> np.ndarray:
  """The P16 continuous broadband filter: Butterworth band-pass (`apply_iir_bandpass`), then the notch.

  Apply it to the whole recording and cut windows afterwards (R3). `notch_hz=None` skips the notch.
  """
  out = apply_iir_bandpass(data, fs, lowcut, highcut, order)
  return out if notch_hz is None else apply_notch(out, fs, notch_hz, notch_q)
