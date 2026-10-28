"""Stateful causal SOS filtering and fixed-clock window replay for the pseudo-online detector (P20.6, PF-38, R3).

The offline pipeline filters the whole recording zero-phase (`filtfilt`), which uses future samples. A detector
that runs online may only use the past, so the same filter family is applied causally:

- `design_sos(fs, lowcut, highcut, order, notch_hz, notch_q)`: Butterworth band-pass (`butter(..., output="sos")`)
  followed by the `iirnotch` section(s) (`tf2sos`), one cascade `sos (n_sections, 6)`; every parameter explicit (R5).
- `CausalSOSFilter(sos, n_channels)`: keeps the filter state `zi` between calls. The state is initialised on the
  FIRST sample seen, `zi = sosfilt_zi(sos) * x[0]` per channel (the response of the cascade to a constant input
  equal to the first sample, so a DC offset does not ring), and then carried: `process(chunk)` returns the same
  samples as one `sosfilt` over the concatenation of all chunks (to round-off), whatever the chunk sizes. An output
  sample depends only on samples at or before it (causality).
- `filter_causal(x, sos)`: the one-pass equivalent (training recordings).
- `replay_windows(x, sos, n_win, stride, chunk)`: feeds `x (C, T)` to a `CausalSOSFilter` in `chunk`-sample pieces
  and, on a FIXED CLOCK, emits the window `k` covering samples `[k*stride, k*stride + n_win)` as soon as its last
  sample has arrived (the clock starts at sample 0 of the stream and never depends on events or on the MARK
  channel). Returns the window starts, the filtered windows and the raw windows cut from the same samples.
"""

from typing import Optional

import numpy as np
from scipy.signal import butter, iirnotch, sosfilt, sosfilt_zi, tf2sos


def design_sos(fs: float, lowcut: float, highcut: float, order: int, notch_hz: Optional[float],
               notch_q: float) -> np.ndarray:
  """Band-pass (+ notch) cascade as `sos (n_sections, 6)`. `notch_hz=None` skips the notch.

  Raises ValueError unless `fs > 0` and `0 < lowcut < highcut < fs/2`, and (with a notch) `0 < notch_hz < fs/2`,
  `notch_q > 0`.
  """
  if not fs > 0:
    raise ValueError(f"fs must be positive, got {fs}")
  nyq = 0.5 * fs
  if not 0 < lowcut < highcut < nyq:
    raise ValueError(f"need 0 < lowcut < highcut < fs/2 = {nyq:g} Hz, got {lowcut}, {highcut}")
  sos = butter(int(order), [lowcut / nyq, highcut / nyq], btype="bandpass", output="sos")
  if notch_hz is None:
    return sos
  if not 0 < notch_hz < nyq or not notch_q > 0:
    raise ValueError(f"need 0 < notch_hz < fs/2 and notch_q > 0, got {notch_hz}, {notch_q}")
  b, a = iirnotch(notch_hz, notch_q, fs=fs)
  return np.vstack([sos, tf2sos(b, a)])


class CausalSOSFilter:
  """Stateful causal SOS filter over `n_channels` channels (module docstring)."""

  def __init__(self, sos: np.ndarray, n_channels: int):
    self.sos = np.asarray(sos, dtype=np.float64)
    if self.sos.ndim != 2 or self.sos.shape[1] != 6:
      raise ValueError(f"sos must be (n_sections, 6), got {self.sos.shape}")
    self.n_channels = int(n_channels)
    self.zi: Optional[np.ndarray] = None            # (n_sections, C, 2) after the first sample
    self.n_seen = 0

  def reset(self) -> None:
    self.zi, self.n_seen = None, 0

  def process(self, chunk: np.ndarray) -> np.ndarray:
    """Filter `chunk (C, n)` (n >= 0) and carry the state; the output has the same shape."""
    x = np.asarray(chunk, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] != self.n_channels:
      raise ValueError(f"chunk must be ({self.n_channels}, n), got {x.shape}")
    if x.shape[1] == 0:
      return x.copy()
    if self.zi is None:
      self.zi = sosfilt_zi(self.sos)[:, None, :] * x[:, 0][None, :, None]     # zi * x[0], per channel
    y, self.zi = sosfilt(self.sos, x, axis=-1, zi=self.zi)
    self.n_seen += x.shape[1]
    return y


def filter_causal(x: np.ndarray, sos: np.ndarray) -> np.ndarray:
  """One-pass causal filtering of `x (C, T)` with `zi = sosfilt_zi * x[0]` (= `CausalSOSFilter.process(x)`)."""
  x = np.asarray(x, dtype=np.float64)
  return CausalSOSFilter(sos, x.shape[0]).process(x)


def replay_windows(x: np.ndarray, sos: np.ndarray, n_win: int, stride: int, chunk: Optional[int] = None) -> tuple:
  """Stream `x (C, T)` through a stateful causal filter in `chunk`-sample pieces (default `stride`) and cut the
  fixed-clock windows `[k*stride, k*stride + n_win)` as they complete.

  Returns `(starts (n,), X_filtered (n, C, n_win), X_raw (n, C, n_win))`; `n = (T - n_win) // stride + 1`
  (0 windows if the stream is shorter than one window). Window `k` is built from the samples received up to its
  last sample only: nothing after the end of the window is read when it is emitted.
  """
  x = np.asarray(x, dtype=np.float64)
  if x.ndim != 2:
    raise ValueError(f"x must be (C, T), got {x.shape}")
  if n_win < 1 or stride < 1:
    raise ValueError(f"n_win and stride must be >= 1, got {n_win}, {stride}")
  chunk = stride if chunk is None else int(chunk)
  if chunk < 1:
    raise ValueError(f"chunk must be >= 1, got {chunk}")
  flt = CausalSOSFilter(sos, x.shape[0])
  buf_f = np.zeros((x.shape[0], 0))
  buf_r = np.zeros((x.shape[0], 0))
  offset = 0                                   # stream index of the first sample held in the buffers
  next_k, starts, wf, wr = 0, [], [], []
  for a in range(0, x.shape[1], chunk):
    piece = x[:, a:a + chunk]
    buf_f = np.concatenate([buf_f, flt.process(piece)], axis=1)
    buf_r = np.concatenate([buf_r, piece], axis=1)
    total = offset + buf_f.shape[1]
    while next_k * stride + n_win <= total:
      s = next_k * stride - offset
      wf.append(buf_f[:, s:s + n_win].copy())
      wr.append(buf_r[:, s:s + n_win].copy())
      starts.append(next_k * stride)
      next_k += 1
    drop = max(next_k * stride - offset, 0)   # samples before the next window start are never needed again
    if drop:
      buf_f, buf_r, offset = buf_f[:, drop:], buf_r[:, drop:], offset + drop
  empty = np.empty((0, x.shape[0], n_win))
  return (np.asarray(starts, dtype=np.int64), np.stack(wf) if wf else empty, np.stack(wr) if wr else empty)
