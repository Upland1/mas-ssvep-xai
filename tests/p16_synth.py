"""Synthetic raw recordings and built folders for the P16 tests (a tiny fake .ebr; never a real recording).

`make_block` returns the 11-channel block `(8 scalp, TIMESTAMP, FLASHINGTIME, MARK)` of the protocol of
01_DATA_SPEC section 3: 15 s per trial, 201 at t, 202 at t+2, 10x at t+5, first 201 at 5 s; each stimulus
trial carries a sinusoid at its target frequency on top of Gaussian noise (std 5 uV), so amplitudes sit
inside the shared gate. `write_raw_subject` writes it as `<raw>/<S>/<session>.ebr`; `write_built_subject`
runs the real `build_subject`/`save_built` into `<root>/<S>/` (what ml-engineer / connectivity tests load).
"""

from pathlib import Path
from typing import Optional

import numpy as np

FS = 256
SCALP = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
CHANNELS = SCALP + ["TIMESTAMP", "FLASHINGTIME", "MARK"]
TARGETS = {101: 24.0, 102: 20.0, 103: 15.0, 104: 10.9091, 105: 8.5714}


def make_block(n_trials: int = 10, seed: int = 0, fs: int = FS, tone_amp: float = 6.0, spike_s: Optional[float] = None,
               bad_channel: Optional[str] = None, truncate_last: bool = False) -> np.ndarray:
  """`(11, T)` float64 block. `spike_s`: a 500 uV one-sample spike on PO3 at that second; `bad_channel`: that
  channel gets noise of std 80 uV (fails the shared gate in every window)."""
  rng = np.random.default_rng(seed)
  codes = rng.permutation(np.tile(np.arange(101, 106), int(np.ceil(n_trials / 5))))[:n_trials]
  T = int((5 + 15 * n_trials + 6) * fs)
  t = np.arange(T) / fs
  x = rng.normal(0, 5.0, size=(8, T))
  mark = np.zeros(T)
  for i, c in enumerate(codes):
    s = 5 + 15 * i
    for off, code in ((0, 201), (2, 202), (5, int(c))):
      mark[int((s + off) * fs)] = code
    a, b = int((s + 5) * fs), int((s + 10) * fs)
    x[:, a:b] += tone_amp * np.sin(2 * np.pi * TARGETS[int(c)] * t[a:b])[None]
  if spike_s is not None:
    x[1, int(spike_s * fs)] += 500.0
  if bad_channel is not None:
    x[SCALP.index(bad_channel)] = rng.normal(0, 80.0, T)
  if truncate_last:
    cut = int((5 + 15 * (n_trials - 1) + 5 + 3) * fs)
    x, mark, T = x[:, :cut], mark[:cut], cut
  block = np.zeros((11, T))
  block[:8], block[8], block[9], block[10] = x, 1.6e12 + np.arange(T) * 1000.0 / fs, 0.005, mark
  return block


def write_ebr(path: Path, block: np.ndarray, fs: int = FS) -> Path:
  nc, ns = block.shape
  lines = ["ebr binary 1.0", "data_type double", f"sampling_rate {fs}", f"samples {ns}", "bands 1", "band_1 Raw Data",
           f"channels {nc}"] + [f"channel_{k} {c}" for k, c in enumerate(CHANNELS, 1)] + [
           "trials 1", "trial_1 EEG Register", "comments 1", "comment_1 Sample selection", "marks 0", "end_header"]
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(("\n".join(lines) + "\n").encode("ascii")
                   + np.ascontiguousarray(block.reshape(1, nc, 1, ns), dtype="<f8").tobytes())
  return path


def write_raw_subject(raw_root: Path, subject: str = "S01", session: str = "OO", **kw) -> Path:
  return write_ebr(Path(raw_root) / subject / f"{session}.ebr", make_block(**kw))


def build_params(filter_mode: str = "continuous", banks=("fbcca", "fbcsp"), guard_sec="auto", stride_sec=None) -> dict:
  """Parameters as `scripts.build_windows.resolve_params` produces them from the committed config."""
  from scripts import build_windows as bw
  args = bw.build_parser().parse_args(["--filter-mode", filter_mode, "--banks", *banks])
  args.stride_sec = stride_sec
  if guard_sec != "auto":
    args.guard_sec = str(guard_sec)
  return bw.resolve_params(bw.load_build_config(bw.DEFAULT_CONFIG), args)


def write_built_subject(root: Path, subject: str = "S01", filter_mode: str = "continuous", **kw) -> Path:
  """Build the synthetic recording with the real code and save it as `<root>/<subject>/`."""
  from scripts import build_windows as bw
  block = make_block(**{k: v for k, v in kw.items() if k in ("n_trials", "seed", "spike_s", "bad_channel", "tone_amp")})
  params = build_params(filter_mode, banks=kw.get("banks", ("fbcca", "fbcsp")), guard_sec=kw.get("guard_sec", "auto"))
  built = bw.build_subject(block[:8], block[10], float(FS), params)
  meta = bw.build_meta(built, params, float(FS), subject, "OO.ebr", "test")
  out = Path(root) / subject
  bw.save_built(out, built, meta)
  return out
