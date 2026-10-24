"""Signal filters (P01: the legacy zero-phase broadband band-pass)."""

import numpy as np
from scipy.signal import filtfilt, iirfilter


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
