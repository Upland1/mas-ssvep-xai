"""P03 known-answer tests (synthetic-tester): occipital FFT power, legacy fs, quality mask, scripts.

Every input is built inside the test with a fixed seed (never from data/). Signals are
sampled at the true rate 256 Hz (mas/01_DATA_SPEC.md section 5.1: 256-sample windows)
and analysed at the legacy fs 250 (Era A, PF-04) unless a test says fs 256.
Expected values come from the DFT and the specification, not from the code under test:
an N-sample window of a sinusoid at k * 256 / N Hz puts all its power in rfft bin k, and
bin k is labelled k * fs / N, so at fs 250 bin 24 is 24 * 250 / 256 = 23.4375 Hz;
|rfft|^2 of A sin at an exact bin is (A N / 2)^2; the scipy periodogram density of an
interior bin is 2 |rfft|^2 / (fs N); channels are selected by name (01_DATA_SPEC section 6,
PF-06); per-subject arrays only (PF-09); thresholds explicit (R5, PF-07).
Each "variant" block re-runs a check against a plausible buggy implementation
(monkeypatched inside the test) and asserts that the check would fail on it.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from scripts.exploration import diagnose_occipital_spectra as dos
from scripts.exploration import visualize_data as vd
from src.features.ssvep import psd_extraction as pe
from src.features.ssvep import spectral_power as sp
from src.preprocessing.signal import quality_check as qc
from src.visualization import signal_plots

ROOT = Path(__file__).resolve().parents[1]
FS_TRUE = 256
N = 256
FS_LEGACY = 250.0
SCALP = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]  # config v1 (PO7 excluded)
STIM = (101, 102, 103, 104, 105)
# planted true frequencies on exact 1 Hz bins of a 256-sample window at 256 Hz
PLANT_BIN = {101: 24, 102: 20, 103: 15, 104: 11, 105: 9}
LEGACY = dict(vpp_min=0.5, vpp_max=200.0, std_min=0.5, std_max=60.0)  # P02 legacy limits (Q2)


# --- helpers ------------------------------------------------------------------------

def _sine(f, a=10.0, phase=0.0, n=N, fs=FS_TRUE):
  return a * np.sin(2 * np.pi * f * np.arange(n) / fs + phase)


def _windows(names, rows, seed=0, noise=1.0, decoy=None):
  """Stack legacy windows: rows = [(code, count, f_true_hz, amp, carriers)].

  `carriers` lists the channel names that carry the sinusoid; every channel gets
  N(0, noise) noise; `decoy = (positions, f, amp)` adds a sinusoid on channel positions.
  """
  rng = np.random.default_rng(seed)
  X, y = [], []
  for code, count, f, amp, carriers in rows:
    for _ in range(count):
      w = rng.normal(0.0, noise, (len(names), N))
      for c in carriers:
        w[names.index(c)] += _sine(f, amp, rng.uniform(0, 2 * np.pi))
      if decoy is not None:
        pos, fd, ad = decoy
        for p in pos:
          w[p] += _sine(fd, ad, rng.uniform(0, 2 * np.pi))
      X.append(w)
      y.append(code)
  return np.stack(X), np.asarray(y, dtype=np.int64)


def _legacy_subject(names=SCALP, seed=0, per_class=10, rest_amp=50.0, rest_hz=30.0, decoy=None):
  """Legacy layout (ordered 201, 202, 101..105): 201/202 carry a strong rest_hz on every
  channel; class c carries PLANT_BIN[c] Hz on O1, Oz, O2 only."""
  rows = [(201, 8, rest_hz, rest_amp, list(names)), (202, 4, rest_hz, rest_amp, list(names))]
  rows += [(c, per_class, float(PLANT_BIN[c]), 10.0, ["O1", "Oz", "O2"]) for c in STIM]
  return _windows(names, rows, seed=seed, decoy=decoy)


def _p02_psd(X, y):
  """X_psd as P02 builds it: P02 extractor periodograms + prepare_feature_matrix layout."""
  recs = {}
  for i in range(len(y)):
    r = pe.extract_clean_subwindows_psd(X[i], FS_TRUE, vpp_thresh=1e12, std_range=(0.0, 1e12),
                                        vpp_min=0.0)
    assert len(r) == 1
    recs.setdefault(int(y[i]), []).append(r[0])
  order = [c for c in (201, 202) + STIM if c in recs]
  X_psd, X_time, y_out = pe.prepare_feature_matrix(recs, target_conditions=order, freq_range=(5, 35))
  return X_psd, X_time, y_out


def _write_subject(folder, X, y, y_len=None):
  folder.mkdir(parents=True, exist_ok=True)
  X_psd, X_time, y_out = _p02_psd(X, y)
  np.testing.assert_array_equal(X_time, X)  # input already in legacy condition order
  np.save(folder / "X_time_windows.npy", X_time)
  np.save(folder / "y_labels.npy", y_out if y_len is None else y_out[:y_len])
  np.save(folder / "X_psd_features.npy", X_psd)


def _config(tmp_path, scalp):
  cfg = yaml.safe_load((ROOT / "configs" / "pipeline_config.yaml").read_text())
  cfg["channels"]["scalp"] = list(scalp)
  p = tmp_path / "cfg.yaml"
  p.write_text(yaml.safe_dump(cfg))
  return p


def _legacy_label(k):
  return k * FS_LEGACY / N


# --- FFT power peak -----------------------------------------------------------------

def _check_fft_peak(fft_fn):
  t_rng = np.random.default_rng(1)
  w = np.stack([np.stack([_sine(15.0, 1.0, t_rng.uniform(0, 6)) for _ in range(7)])
                for _ in range(6)])
  w = w + t_rng.normal(0, 0.05, w.shape)
  f, p = fft_fn(w, 256.0)
  assert p.shape == (6, 7, 129) and f.shape == (129,)
  assert np.all(np.argmax(p, axis=-1) == 15)
  assert f[15] == 15.0
  pure = sp.fft_power(_sine(15.0, 1.0)[None, None], 256.0)[1]
  np.testing.assert_allclose(pure[0, 0, 15], (1.0 * N / 2) ** 2, rtol=1e-9)


def test_fft_power_peak_15hz_exact_bin(monkeypatch):
  """Known answer: 15 Hz sinusoids sampled at 256 Hz, analysed at fs 256 -> argmax bin 15 on
  every window and channel, labelled 15.0 Hz; |rfft|^2 of a unit sine = (N/2)^2 = 16384.
  Exact bin, rtol 1e-9 on the power. Source: DFT.
  Variant: rfft over the channel axis instead of time -> the check fails.
  """
  _check_fft_peak(sp.fft_power)

  def wrong_axis(windows, fs):
    w = np.asarray(windows, dtype=np.float64)
    return np.fft.rfftfreq(w.shape[1], 1 / fs), np.abs(np.fft.rfft(w, axis=1)) ** 2

  with pytest.raises(AssertionError):
    _check_fft_peak(wrong_axis)


# --- legacy fs shift ----------------------------------------------------------------

def _check_legacy_shift(class_spectra):
  X, y = _legacy_subject()
  res = class_spectra(X, y, FS_LEGACY, SCALP, STIM, (5.0, 35.0))
  for c, k in PLANT_BIN.items():
    assert res["peaks"][c]["k_max"] == k
    assert abs(res["peaks"][c]["f_max"] - _legacy_label(k)) <= 1e-9
  assert abs(res["peaks"][101]["f_max"] - 23.4375) <= 1e-9
  return res


def test_legacy_fs_shift_24hz(monkeypatch):
  """Known answer: a 24 Hz sinusoid sampled at 256 Hz analysed with fs 250 has its maximum at
  bin 24, labelled 24 * 250 / 256 = 23.4375 Hz; with fs 256 the same bin is 24.0 Hz. Every
  planted class (bins 24, 20, 15, 11, 9) is labelled k * 250 / 256. The bin nearest the
  24 Hz target on the legacy axis is 25 (24.4140625 Hz: |24.414 - 24| < |23.4375 - 24|).
  Tolerance 1e-9. Source: PF-04, DFT.
  Variant: an analysis that ignores --fs and always uses the header rate 256 -> fails.
  """
  w = _sine(24.0, 1.0)[None, None]
  f, p = sp.fft_power(w, FS_LEGACY)
  k = int(np.argmax(p[0, 0]))
  assert k == 24 and abs(f[k] - 23.4375) <= 1e-9
  f256, p256 = sp.fft_power(w, 256.0)
  assert int(np.argmax(p256[0, 0])) == 24 and f256[24] == 24.0
  np.testing.assert_array_equal(p, p256)  # fs only relabels the axis

  res = _check_legacy_shift(dos.occipital_class_spectra)
  h1 = [h for h in res["peaks"][101]["harmonics"] if h["h"] == 1][0]
  assert h1["k"] == 25 and abs(h1["f_bin"] - 25 * 250 / 256) <= 1e-9
  for c, k in [(102, 20), (103, 15), (104, 11), (105, 9)]:  # nearest bins to 20, 15, 10.91, 8.57
    assert [h for h in res["peaks"][c]["harmonics"] if h["h"] == 1][0]["k"] == k

  orig = dos.occipital_class_spectra

  def header_only(X, y, fs, *a, **kw):
    return orig(X, y, 256.0, *a, **kw)

  with pytest.raises(AssertionError):
    _check_legacy_shift(header_only)


# --- occipital by name ----------------------------------------------------------------

REORDERED = ["O1", "PO3", "Oz", "O2", "POz", "PO4", "PO8"]  # O1, Oz, O2 at 0, 2, 3


def _check_by_name(class_spectra):
  # positions 4, 5, 6 (O1, Oz, O2 in config v1) carry a 33 Hz decoy; the named ones the classes
  X, y = _legacy_subject(names=REORDERED, decoy=([4, 5, 6], 33.0, 30.0))
  res = class_spectra(X, y, 256.0, REORDERED, STIM, (5.0, 35.0))
  for c, k in PLANT_BIN.items():
    assert res["peaks"][c]["k_max"] == k and res["peaks"][c]["f_max"] == float(k)
  return res


def test_occipital_by_name_reordered(monkeypatch):
  """Known answer: with names O1, Oz, O2 at positions 0, 2, 3 (reordered list), the channels
  used are [0, 2, 3] and each class peaks at its planted bin (24/20/15/11/9 Hz at fs 256),
  although positions 4, 5, 6 carry a 33 Hz decoy of 3x the amplitude. Exact.
  Source: PF-06, 01_DATA_SPEC section 6.
  Variant: positional selection [4, 5, 6] -> every class peaks at 33 Hz -> the check fails.
  """
  res = _check_by_name(dos.occipital_class_spectra)
  assert res["channels"] == [0, 2, 3]
  assert sp.select_channels_by_name(SCALP, ("O1", "Oz", "O2"), 7) == [4, 5, 6]
  with monkeypatch.context() as m:
    m.setattr(dos, "select_channels_by_name", lambda names, wanted, n: [4, 5, 6])
    with pytest.raises(AssertionError):
      _check_by_name(dos.occipital_class_spectra)


def test_occipital_by_name_through_config(tmp_path, capsys):
  """Known answer: the script takes names from the subject's `channels.json` (P07: the scripts no
  longer read config `channels.scalp`); with the reordered list and the decoy array it reports channels [0, 2, 3] = ['O1', 'Oz', 'O2'] and the planted
  maxima (fs 256: 24.000, 20.000, 15.000, 11.000, 9.000 Hz). Exact. Source: PF-06.
  """
  X, y = _legacy_subject(names=REORDERED, decoy=([4, 5, 6], 33.0, 30.0))
  _write_subject(tmp_path / "proc" / "S01", X, y)
  (tmp_path / "proc" / "S01" / "channels.json").write_text(json.dumps({"kept": REORDERED}))
  rc = dos.main(["--subject", "S01", "--fs", "256", "--no-figures", "--config",
                 str(_config(tmp_path, REORDERED)), "--processed-dir", str(tmp_path / "proc")])
  out = capsys.readouterr().out
  assert rc == 0
  assert "channels [0, 2, 3] = ['O1', 'Oz', 'O2']" in out
  for c, k in PLANT_BIN.items():
    assert f"S01 {c}: n=10, " in out and f"max in band at {k:.3f} Hz (bin {k}," in out
  assert "33.000 Hz" not in out


# --- per-class panels ---------------------------------------------------------------

def _spy(monkeypatch, name, store):
  orig = getattr(signal_plots, name)

  def wrapper(*a, **kw):
    store.append({"args": a, "kwargs": kw})
    return orig(*a, **kw)

  monkeypatch.setattr(signal_plots, name, wrapper)


def _run_panels(tmp_path, monkeypatch, capsys):
  X, y = _legacy_subject(rest_amp=80.0)
  _write_subject(tmp_path / "proc" / "S01", X, y)
  calls = []
  _spy(monkeypatch, "plot_class_spectra_panels", calls)
  rc = dos.main(["--subject", "S01", "--processed-dir", str(tmp_path / "proc"),
                 "--figures-dir", str(tmp_path / "figs")])
  return rc, calls, capsys.readouterr().out


def _check_panels(rc, calls, out, tmp_path):
  assert rc == 0 and len(calls) == 1
  spectra = calls[0]["args"][1]
  assert list(spectra) == list(STIM)  # 5 panels, class order 101..105
  assert calls[0]["kwargs"]["counts"] == {c: 10 for c in STIM}
  assert "fs=250 (legacy)" in calls[0]["kwargs"]["title"]
  freqs = calls[0]["args"][0]
  for c, k in PLANT_BIN.items():
    s = np.asarray(spectra[c])
    band = (freqs >= 5) & (freqs <= 35)
    assert int(np.flatnonzero(band)[np.argmax(s[band])]) == k
    assert f"max in band at {_legacy_label(k):.3f} Hz (bin {k}," in out
  assert "S01 201" not in out and "S01 202" not in out
  png = tmp_path / "figs" / "exploration" / "S01" / "occipital_spectra.png"
  assert png.stat().st_size > 0


def test_per_class_panels_planted_and_rest_excluded(tmp_path, monkeypatch, capsys):
  """Known answer: legacy folder with 8 x 201 and 4 x 202 rows carrying an 80 uV 30 Hz sine on
  every channel and 10 rows per stimulus class at bins 24/20/15/11/9: exactly 5 panels
  (101..105, counts 10), each maximum at its planted bin (labelled k * 250 / 256 at the legacy
  fs), no 201/202 line, title with `fs=250 (legacy)`, PNG non-empty. Exact.
  Source: 02_plan P03.1, 01_DATA_SPEC section 6 (5-class = stimulus windows only).
  Variant: classes taken from config target_conditions without removing 201/202 -> 7 classes
  -> the run or the check fails.
  """
  rc, calls, out = _run_panels(tmp_path, monkeypatch, capsys)
  _check_panels(rc, calls, out, tmp_path)

  monkeypatch.setattr(dos, "stimulus_conditions",
                      lambda cfg: tuple(int(c) for c in cfg["project"]["target_conditions"]))
  with pytest.raises((AssertionError, TypeError)):  # 7 classes; 201/202 have no f0 to print
    rc, calls, out = _run_panels(tmp_path / "v", monkeypatch, capsys)
    _check_panels(rc, calls, out, tmp_path / "v")


# --- quality mask -------------------------------------------------------------------

def _mask_subject(seed=3):
  """60 stimulus windows (12 per class), 10 uV sines on O1-O2 + N(0, 2) on all channels
  (vpp ~ 30 uV, std ~ 2-8 uV: inside the legacy limits). Planted: 3 x 103 with a +500 uV
  spike on PO4 (vpp_high), 2 x 105 with a flat PO3 (vpp 0, std 0: vpp_low and std_low),
  1 x 101 with a +150 uV spike on POz (kept at vpp_max 200, rejected at vpp_max 100)."""
  rows = [(c, 12, float(PLANT_BIN[c]), 10.0, ["O1", "Oz", "O2"]) for c in STIM]
  X, y = _windows(SCALP, rows, seed=seed, noise=2.0)
  i103 = np.flatnonzero(y == 103)[[1, 4, 7]]
  X[i103, SCALP.index("PO4"), 100] += 500.0
  i105 = np.flatnonzero(y == 105)[[0, 11]]
  X[i105, SCALP.index("PO3"), :] = 3.0
  i101 = np.flatnonzero(y == 101)[5]
  X[i101, SCALP.index("POz"), 50] += 150.0
  return X, y, set(i103) | set(i105), int(i101)


def test_quality_mask_planted_counts_and_thresholds_as_passed():
  """Known answer: legacy limits -> rejected = 5 planted (103: 3 vpp_high; 105: 2 vpp_low and
  2 std_low), the 150 uV window kept; vpp_max = 100 passed -> 6 rejected (101: 1 vpp_high);
  thresholds returned exactly as passed; the mask equals the rows planted. Exact.
  Source: 02_plan P03.2 and Q2, R5; ptp of a +A spike over a +-30 uV background > A - 30.
  """
  X, y, bad, mid = _mask_subject()
  q = vd.quality_mask(X, y, **LEGACY)
  assert q["thresholds"] == LEGACY
  assert q["n_rejected"] == 5 and q["n_kept"] == 55
  assert set(np.flatnonzero(q["mask"] == 0)) == bad
  assert q["by_label"][103]["rejected"] == 3 and q["by_label"][103]["reasons"]["vpp_high"] == 3
  assert q["by_label"][105]["reasons"] == {"vpp_low": 2, "vpp_high": 0, "std_low": 2, "std_high": 0}
  assert q["by_label"][101]["rejected"] == 0
  for c in (102, 104):
    assert q["by_label"][c] == {"n": 12, "kept": 12, "rejected": 0,
                                "reasons": {r: 0 for r in qc.REJECT_REASONS}}
  tight = dict(LEGACY, vpp_max=100.0)
  q2 = vd.quality_mask(X, y, **tight)
  assert q2["thresholds"] == tight and q2["n_rejected"] == 6
  assert set(np.flatnonzero(q2["mask"] == 0)) == bad | {mid}
  assert q2["by_label"][101]["reasons"]["vpp_high"] == 1


def _check_vpp_min_explicit(qmask):
  rng = np.random.default_rng(4)
  # 1.5 uV sines: vpp ~ 3 uV (0.5 < vpp < 5), std ~ 1.06 uV (>= 0.5): legacy keeps them all
  X = np.stack([np.stack([_sine(10.0, 1.5, rng.uniform(0, 6)) for _ in range(7)]) for _ in range(20)])
  y = np.repeat(np.asarray(STIM), 4)
  vpp = np.ptp(X, axis=-1)
  assert np.all((vpp > 0.5) & (vpp < 5.0))
  q = qmask(X, y, **LEGACY)
  assert q["n_rejected"] == 0 and q["n_kept"] == 20


def test_quality_mask_vpp_min_is_explicit(monkeypatch, tmp_path, capsys):
  """Known answer (PF-07): windows with 0.5 < Vpp < 5 uV are kept by the legacy mask
  (vpp_min 0.5 passed); the shared default vpp_min 5.0 rejects all of them; `quality_mask`
  without vpp_min is a TypeError (no inherited default); the script's default thresholds are
  exactly vpp [0.5, 200], std [0.5, 60] (config v1 + legacy constant) and keep all 20. Exact.
  Source: PF-07, 02_plan Q2, R5.
  Variant: a mask that forwards every threshold except vpp_min (inherits 5.0) -> fails.
  """
  _check_vpp_min_explicit(vd.quality_mask)
  rng = np.random.default_rng(4)
  X = np.stack([np.stack([_sine(10.0, 1.5, rng.uniform(0, 6)) for _ in range(7)]) for _ in range(20)])
  assert qc.validate_eeg_windows(X, vpp_max=200.0, std_min=0.5, std_max=60.0).sum() == 0
  with pytest.raises(TypeError):
    vd.quality_mask(X, np.full(20, 101), vpp_max=200.0, std_min=0.5, std_max=60.0)

  cfg = dos.load_config(ROOT / "configs" / "pipeline_config.yaml")
  assert vd.resolve_thresholds(cfg, vd.build_parser().parse_args([])) == LEGACY

  _write_subject(tmp_path / "proc" / "S01", X, np.repeat(np.asarray(STIM), 4))
  rc = vd.main(["--subject", "S01", "--no-figures", "--processed-dir", str(tmp_path / "proc")])
  out = capsys.readouterr().out
  assert rc == 0 and "kept 20/20, rejected 0 (vpp [0.5, 200] uV, std [0.5, 60] uV)" in out

  orig = qc.validate_eeg_windows

  def inherits_default(windows, vpp_min=None, **kw):
    return orig(windows, **kw)

  monkeypatch.setattr(vd, "validate_eeg_windows", inherits_default)
  with pytest.raises(AssertionError):
    _check_vpp_min_explicit(vd.quality_mask)


# --- PSD features layout ------------------------------------------------------------

def test_psd_features_layout_217_210_and_p02_equality():
  """Known answer: 256-sample windows -> 31 bins (5..35 Hz) and 217 features at fs 256, 30 bins
  (k = 6..35, labelled k * 250/256) and 210 features at fs 250; channel-major (channel c planted
  at bin 6 + 3c peaks in column block c, offset 1 + 3c at fs 256 / 3c at fs 250); at fs
  256 the features equal the P02 extractor + prepare_feature_matrix output (rtol 1e-12); every
  interior value equals the periodogram density 2 |rfft|^2 / (fs N) (rtol 1e-9).
  Source: 01_DATA_SPEC 5.1, PF-04, DFT/periodogram definition, R6.
  """
  rng = np.random.default_rng(5)
  X = np.stack([np.stack([_sine(6 + 3 * c, 10.0, rng.uniform(0, 6)) for c in range(7)])
                for _ in range(9)]) + rng.normal(0, 0.5, (9, 7, N))
  y = np.repeat([101, 102, 103], 3)
  X256, f256, psd256 = sp.psd_features(X, 256.0, (5.0, 35.0))
  X250, f250, psd250 = sp.psd_features(X, 250.0, (5.0, 35.0))
  assert X256.shape == (9, 217) and X250.shape == (9, 210)
  np.testing.assert_array_equal(f256, np.arange(5, 36, dtype=float))
  np.testing.assert_allclose(f250, np.arange(6, 36) * 250 / 256, rtol=0, atol=1e-12)
  for c in range(7):
    assert np.all(np.argmax(X256[:, 31 * c:31 * (c + 1)], axis=1) == 6 + 3 * c - 5)
    assert np.all(np.argmax(X250[:, 30 * c:30 * (c + 1)], axis=1) == 6 + 3 * c - 6)
  X_p02, _, _ = _p02_psd(X, y)
  assert X_p02.shape == (9, 217)
  np.testing.assert_allclose(X256, X_p02, rtol=1e-12, atol=0)
  P = np.abs(np.fft.rfft(X - X.mean(-1, keepdims=True), axis=-1)) ** 2
  np.testing.assert_allclose(X250, (2 * P[:, :, 6:36] / (250 * N)).reshape(9, 210), rtol=1e-9)
  np.testing.assert_allclose(X256, (2 * P[:, :, 5:36] / (256 * N)).reshape(9, 217), rtol=1e-9)


def test_visualize_explore_subject_psd_matches_saved_at_header_fs():
  """Known answer: explore_subject at fs 256 on a P02-built folder gives psd_check = 0 (same
  layout as the saved X_psd_features), X (60, 217), class counts 12; at fs 250 X (60, 210) and
  psd_check None (widths differ, not compared). Exact. Source: P02 layout, PF-04.
  """
  X, y, _, _ = _mask_subject()
  X_psd, _, _ = _p02_psd(X, y)
  d = {"X_time": X, "y": y, "X_psd": X_psd}
  wide = dict(vpp_min=0.0, vpp_max=1e12, std_min=0.0, std_max=1e12)
  r = vd.explore_subject(d, 256.0, SCALP, STIM, (5.0, 35.0), wide)
  assert r["features"]["psd"]["X"].shape == (60, 217) and r["psd_check"] == 0.0
  assert r["features"]["psd"]["counts"] == {c: 12 for c in STIM}
  r = vd.explore_subject(d, 250.0, SCALP, STIM, (5.0, 35.0), wide)
  assert r["features"]["psd"]["X"].shape == (60, 210) and r["psd_check"] is None


# --- channel-count check ------------------------------------------------------------

def test_channel_count_mismatch_fails_loudly(tmp_path, capsys):
  """Known answer: 8 names (PO7 + config v1) for a 7-channel array raise ValueError in the
  name lookup, the per-class spectra and explore_subject (no positional fallback); 7 names for
  an 8-channel array too; both scripts print `[-] Skipping S01: 8 channel names ...`, write no
  figure and exit 1. Source: 02_plan (fail loudly), PF-05/PF-06.
  """
  eight = ["PO7"] + SCALP
  X, y = _legacy_subject()
  with pytest.raises(ValueError, match="8 channel names"):
    sp.select_channels_by_name(eight, ("O1", "Oz", "O2"), 7)
  with pytest.raises(ValueError):
    sp.select_channels_by_name(SCALP, ("O1", "Oz", "O2"), 8)
  with pytest.raises(ValueError):
    dos.occipital_class_spectra(X, y, FS_LEGACY, eight, STIM)
  with pytest.raises(ValueError):
    vd.explore_subject({"X_time": X, "y": y}, FS_LEGACY, eight, STIM, (5.0, 35.0), LEGACY)

  _write_subject(tmp_path / "proc" / "S01", X, y)
  # P07: the scripts take names from channels.json (else by channel count), so a real mismatch
  # is a channels.json with 6 names for the 7-channel array
  (tmp_path / "proc" / "S01" / "channels.json").write_text(json.dumps({"kept": SCALP[:-1]}))
  cfg = str(_config(tmp_path, SCALP))
  for mod in (dos, vd):
    rc = mod.main(["--subject", "S01", "--config", cfg, "--processed-dir", str(tmp_path / "proc"),
                   "--figures-dir", str(tmp_path / "figs")])
    out = capsys.readouterr().out
    assert rc == 1 and "[-] Skipping S01: 6 channel names" in out
  assert not (tmp_path / "figs").exists() or not any((tmp_path / "figs").rglob("*.png"))


# --- script smoke on a synthetic legacy tree (PF-09) -------------------------------

def _tree(tmp_path):
  """proc/S01 (planted classes), proc/S02 (empty), proc/S04 (X 320 rows vs y 317: PF-09),
  proc/S03_backup (arrays, not a subject name), and root arrays from a *different* subject
  (every class at 33 Hz, 25 windows per class) that must never be read."""
  proc = tmp_path / "proc"
  X, y = _legacy_subject()
  _write_subject(proc / "S01", X, y)
  (proc / "S02").mkdir(parents=True)
  X4, y4 = _windows(SCALP, [(201, 80, 30.0, 10.0, SCALP), (202, 40, 30.0, 10.0, SCALP)]
                    + [(c, 40, float(PLANT_BIN[c]), 10.0, ["O1", "Oz", "O2"]) for c in STIM], seed=9)
  _write_subject(proc / "S04", X4, y4, y_len=317)
  Xb, yb = _legacy_subject(seed=7)
  _write_subject(proc / "S03_backup", Xb, yb)
  Xr, yr = _windows(SCALP, [(c, 25, 33.0, 40.0, SCALP) for c in STIM], seed=8)
  _write_subject(proc, Xr, yr)
  return proc


def _check_smoke(out, rc, figs):
  assert rc == 0
  assert "[-] Skipping S02: no X_time_windows.npy" in out
  assert "[-] Skipping S04: length mismatch" in out
  assert "S03_backup" not in out
  assert "fs=250 (legacy)" in out
  assert "[+] S01: 62 windows, X_time (62, 7, 256)" in out
  for c, k in PLANT_BIN.items():
    assert f"S01 {c}: n=10, " in out and f"max in band at {_legacy_label(k):.3f} Hz (bin {k}," in out
  assert f"{_legacy_label(33):.3f} Hz (bin 33" not in out
  assert "Cohort: 1 subjects plotted, 2 skipped (S02, S04)" in out
  assert (figs / "exploration" / "S01" / "occipital_spectra.png").stat().st_size > 0
  assert not (figs / "exploration" / "S02").exists()


def test_scripts_smoke_tree_root_arrays_ignored(tmp_path, monkeypatch, capsys):
  """Known answer (PF-09): on the synthetic tree, --all discovers S01, S02, S04 (not
  S03_backup); S01 is plotted from its own folder (62 windows, planted maxima at the legacy
  labels, no 33 Hz from the root arrays); S02 and S04 are skipped with a reason; fs label in
  the console and in both figure titles; both PNGs non-empty; at fs 256 the header label and
  `max |computed - saved| = 0`. Source: PF-09, 02_plan script smoke, 02_REQUIREMENTS section 4.
  Variant: a loader that reads the root arrays -> the check fails.
  """
  proc, figs = _tree(tmp_path), tmp_path / "figs"
  titles = []
  _spy(monkeypatch, "plot_class_spectra_panels", titles)
  _spy(monkeypatch, "plot_psd_by_class_per_channel", titles)
  rc = dos.main(["--all", "--processed-dir", str(proc), "--figures-dir", str(figs)])
  _check_smoke(capsys.readouterr().out, rc, figs)

  rc = vd.main(["--all", "--processed-dir", str(proc), "--figures-dir", str(figs)])
  out = capsys.readouterr().out
  assert rc == 0 and "[-] Skipping S02" in out and "[-] Skipping S04: length mismatch" in out
  assert "S01 quality mask: kept 62/62, rejected 0" in out
  assert "stimulus windows per class: 101: 10, 102: 10, 103: 10, 104: 10, 105: 10" in out
  assert "psd: X (50, 210) (30 bins" in out
  assert (figs / "exploration" / "S01" / "psd_features_by_class.png").stat().st_size > 0
  assert len(titles) == 2 and all("fs=250 (legacy)" in t["kwargs"]["title"] for t in titles)

  rc = vd.main(["--subject", "S01", "--fs", "256", "--out-suffix", "header",
                "--processed-dir", str(proc), "--figures-dir", str(figs)])
  out = capsys.readouterr().out
  assert rc == 0 and "fs=256 (header)" in out and "max |computed - saved| = 0" in out
  assert "psd: X (50, 217) (31 bins" in out
  assert (figs / "exploration" / "S01" / "psd_features_by_class_header.png").stat().st_size > 0

  orig = dos.load_legacy_windows
  monkeypatch.setattr(dos, "load_legacy_windows",
                      lambda processed_dir, subject, with_psd=False: orig(Path(processed_dir).parent,
                                                                          Path(processed_dir).name,
                                                                          with_psd))
  rc = dos.main(["--all", "--processed-dir", str(proc), "--figures-dir", str(tmp_path / "f2")])
  with pytest.raises(AssertionError):
    _check_smoke(capsys.readouterr().out, rc, tmp_path / "f2")


def test_script_module_entry_point(tmp_path):
  """Known answer: `python -m scripts.exploration.diagnose_occipital_spectra` on the tree exits
  0, prints the skip lines and `fs=250 (legacy)`, writes the figure. Source: 02_REQUIREMENTS 4.
  """
  proc, figs = _tree(tmp_path), tmp_path / "figs"
  r = subprocess.run([sys.executable, "-m", "scripts.exploration.diagnose_occipital_spectra",
                      "--all", "--processed-dir", str(proc), "--figures-dir", str(figs)],
                     cwd=ROOT, capture_output=True, text=True, timeout=120)
  assert r.returncode == 0, r.stdout + r.stderr
  _check_smoke(r.stdout, r.returncode, figs)


# --- Round 2: response bins, specificity, format_peaks (07_review pre-run audit fix 2) ------

# In-band (5-35 Hz) harmonics h * f0, h = 1, 2, of the five targets (STIM_FREQS_HZ):
# 101: 24 (48 out); 102: 20 (40 out); 103: 15, 30; 104: 120/11 = 10.909, 240/11 = 21.818;
# 105: 60/7 = 8.571, 120/7 = 17.143 -> eight harmonics. With T = 256 samples at header fs 256
# the response bin is round(f * 256 / 256) = round(f): 24, 20, 15, 30, 11, 22, 9, 17.
# The bin nearest f on the legacy axis k * 250 / 256 is round(f * 256 / 250):
# 24.576 -> 25, 20.48 -> 20, 15.36 -> 15, 30.72 -> 31, 11.17 -> 11, 22.34 -> 22, 8.78 -> 9,
# 17.55 -> 18: they differ for 24, 30 and 120/7 Hz only.
HARMONICS = {  # code -> [(h, f_hz, response bin, nearest-labelled bin at fs 250)]
  101: [(1, 24.0, 24, 25)],
  102: [(1, 20.0, 20, 20)],
  103: [(1, 15.0, 15, 15), (2, 30.0, 30, 31)],
  104: [(1, 120 / 11, 11, 11), (2, 240 / 11, 22, 22)],
  105: [(1, 60 / 7, 9, 9), (2, 120 / 7, 17, 18)],
}


def _check_response_bins(peaks_fn):
  """24, 30 and 120/7 Hz sinusoids (A = 2) sampled at 256 Hz, axis labelled at fs 250."""
  a = 2.0
  for code, h, f_hz, k_resp, k_near in [(101, 1, 24.0, 24, 25), (103, 2, 30.0, 30, 31),
                                        (105, 2, 120 / 7, 17, 18)]:
    freqs, p = sp.fft_power(_sine(f_hz, a)[None, None], FS_LEGACY)
    s = p[0, 0]
    pk = peaks_fn(freqs, s, (5.0, 35.0), target_hz=STIM_FREQS[code], header_fs=256.0,
                  n_samples=N)
    hh = [x for x in pk["harmonics"] if x["h"] == h][0]
    assert hh["k_resp"] == k_resp and hh["k"] == k_near
    assert int(np.argmax(s)) == k_resp != k_near
    assert abs(hh["f_resp"] - k_resp * 250 / 256) <= 1e-9
    assert abs(hh["f_bin"] - k_near * 250 / 256) <= 1e-9
    assert hh["power_resp"] == s[k_resp] and hh["power"] == s[k_near]
    if f_hz == int(f_hz):  # exact bin: all power in k_resp, none in its neighbour
      np.testing.assert_allclose(hh["power_resp"], (N / 2) ** 2 * a ** 2, rtol=1e-9)
      assert hh["power"] <= 1e-12 * hh["power_resp"]
    else:  # 120/7 Hz sits 0.143 bin above 17: leakage, still argmax at 17
      assert hh["power_resp"] > 10 * hh["power"]


STIM_FREQS = signal_plots.STIM_FREQS_HZ


def test_response_bins_legacy_axis_24_30_17(monkeypatch):
  """Known answer (PF-04, audit fix 2a): fs 250 labels, header 256, T = 256. Sinusoids at 24,
  2*15 = 30 and 2*60/7 = 17.143 Hz -> response bins 24, 30, 17 (= argmax of the planted
  spectrum), nearest-labelled bins 25, 31, 18 (not the argmax); labels k * 250/256 (1e-9);
  for 24 and 30 Hz power_resp = (N/2)^2 A^2 = 65536 at A = 2 (rtol 1e-9) and the
  nearest-labelled bin holds <= 1e-12 of it. Source: DFT, 07_review fix 1/2.
  Variant: a response bin computed on the labelled axis (round(f * T / 250), i.e. the
  nearest-labelled bin) -> the check fails.
  """
  _check_response_bins(sp.spectrum_peaks)
  monkeypatch.setattr(sp, "response_bin",
                      lambda f_hz, n_samples, header_fs: int(np.floor(f_hz * n_samples / 250.0 + 0.5)))
  with pytest.raises(AssertionError):
    _check_response_bins(sp.spectrum_peaks)


def test_response_bins_through_class_spectra_and_console(capsys, tmp_path):
  """Known answer: the script at the default fs 250 on 256-sample windows (header fs 256)
  prints for 101 `1f0 response bin 24 (23.438 Hz)` followed by `nearest-labelled bin 25
  (24.414 Hz)`, for 103 `2f0 response bin 30 (29.297 Hz)` + `nearest-labelled bin 31
  (30.273 Hz)`; 102 and 104 print no nearest-labelled bin (they coincide). Exact.
  Source: HARMONICS derivation above, 03_changes Round 2 console format.
  """
  X, y = _legacy_subject()
  res = dos.occipital_class_spectra(X, y, FS_LEGACY, SCALP, STIM, (5.0, 35.0), header_fs=256.0)
  for code, rows in HARMONICS.items():
    got = {x["h"]: (x["k_resp"], x["k"]) for x in res["peaks"][code]["harmonics"]}
    assert got == {h: (kr, kn) for h, _, kr, kn in rows}
  _write_subject(tmp_path / "proc" / "S01", X, y)
  assert dos.main(["--subject", "S01", "--no-figures", "--processed-dir", str(tmp_path / "proc")]) == 0
  lines = {ln.split(":")[0].strip(): ln for ln in capsys.readouterr().out.splitlines()
           if ln.startswith("  S01 1")}
  assert "1f0 response bin 24 (23.438 Hz)" in lines["S01 101"]
  assert ", nearest-labelled bin 25 (24.414 Hz)" in lines["S01 101"]
  assert "2f0 response bin 30 (29.297 Hz)" in lines["S01 103"]
  assert ", nearest-labelled bin 31 (30.273 Hz)" in lines["S01 103"]
  assert "2f0 response bin 17 (16.602 Hz)" in lines["S01 105"]
  assert ", nearest-labelled bin 18 (17.578 Hz)" in lines["S01 105"]
  for c in ("S01 102", "S01 104"):
    assert "nearest-labelled" not in lines[c]


def test_response_bin_equals_nearest_at_header_fs(capsys, tmp_path):
  """Known answer (audit fix 2b): at fs 256 = header fs, response bin = nearest bin for all
  eight in-band harmonics: 24, 20, 15, 30, 11, 22, 9, 17 (list derived above), labels k Hz;
  the console prints no nearest-labelled bin. Exact.
  """
  X, y = _legacy_subject()
  res = dos.occipital_class_spectra(X, y, 256.0, SCALP, STIM, (5.0, 35.0), header_fs=256.0)
  seen = []
  for code, rows in HARMONICS.items():
    hs = res["peaks"][code]["harmonics"]
    assert [x["h"] for x in hs] == [h for h, _, _, _ in rows]
    for x, (h, f_hz, kr, _) in zip(hs, rows):
      assert x["k_resp"] == x["k"] == kr and x["f_resp"] == x["f_bin"] == float(kr)
      assert abs(x["f_target"] - f_hz) <= 1e-12
      seen.append(kr)
  assert seen == [24, 20, 15, 30, 11, 22, 9, 17]
  _write_subject(tmp_path / "proc" / "S01", X, y)
  assert dos.main(["--subject", "S01", "--fs", "256", "--no-figures",
                   "--processed-dir", str(tmp_path / "proc")]) == 0
  out = capsys.readouterr().out
  assert "fs=256 (header)" in out and "nearest-labelled" not in out


def _specific_subject(shared_hz=None, seed=None, n_win=1):
  """Classes 101..105. O1/Oz/O2 of every window = B * delta[n] (flat |rfft|^2 = B^2 floor)
  plus, by default, A sin(2 pi k t) at the class's own response bin k (24, 20, 15, 11, 9 Hz,
  exact bins at 256 Hz, phase 0). With shared_hz: the same A sin(2 pi shared_hz t) in every
  class instead, plus N(0, 1) noise from `seed`."""
  rng = np.random.default_rng(seed)
  X, y = [], []
  for code in STIM:
    for _ in range(n_win):
      w = np.zeros((7, N))
      for c in ("O1", "Oz", "O2"):
        i = SCALP.index(c)
        if shared_hz is None:
          w[i] = _sine(float(PLANT_BIN[code]), SPEC_A)
          w[i, 0] += SPEC_B
        else:
          w[i] = _sine(shared_hz, SPEC_A) + rng.normal(0, 1.0, N)
      X.append(w)
      y.append(code)
  return np.stack(X), np.asarray(y, dtype=np.int64)


SPEC_A, SPEC_B = 10.0, 50.0


def _check_specificity(class_spectra):
  X, y = _specific_subject()
  res = class_spectra(X, y, FS_LEGACY, SCALP, STIM, (5.0, 35.0), header_fs=256.0)
  expected = 1.0 + (SPEC_A * N / (2 * SPEC_B)) ** 2  # 1 + 25.6^2 = 656.36
  for code in STIM:
    s = res["specificity"][code]
    assert s["k"] == PLANT_BIN[code] and s["n_others"] == 4
    np.testing.assert_allclose(s["own"], SPEC_B ** 2 + (SPEC_A * N / 2) ** 2, rtol=1e-9)
    np.testing.assert_allclose(s["others_median"], SPEC_B ** 2, rtol=1e-9)
    np.testing.assert_allclose(s["ratio"], expected, rtol=1e-9)


def test_specificity_class_specific_analytic(monkeypatch):
  """Known answer (audit fix 2c): each class carries A = 10 at its own exact response bin k
  (phase 0, rfft = -i A N / 2) on top of B = 50 * delta[n] (|rfft|^2 = B^2 at every bin), so at
  k the own power is |B - i A N/2|^2 = B^2 + (A N/2)^2 = 2500 + 1638400 and every other class
  has B^2 = 2500 (its sine sits on another exact bin: no leakage). Ratio = 1 + (A N / 2B)^2 =
  656.36 for every class at the legacy fs 250 with header 256, 4 other classes. rtol 1e-9.
  Source: DFT of a sinusoid and of an impulse.
  Variant: specificity read at the nearest-labelled bin (25 for 101) -> ratio 1 -> fails.
  """
  _check_specificity(dos.occipital_class_spectra)
  orig = dos.specificity_ratio

  def at_nearest(spectra, code, k):
    near = {24: 25}.get(k, k)
    return orig(spectra, code, near)

  monkeypatch.setattr(dos, "specificity_ratio", at_nearest)
  with pytest.raises(AssertionError):
    _check_specificity(dos.occipital_class_spectra)


def test_specificity_shared_rhythm_near_one():
  """Known answer (audit fix 2c): the same 120/11 = 10.909 Hz sinusoid (A = 10, phase 0,
  response bin 11) in all five classes plus N(0, 1) noise (seed 11), 20 windows per class.
  Signal power at bin 11 is identical across classes, S = |DFT|^2 ~ (A N / 2)^2 = 1.6e6; noise
  adds sigma^2 N = 256 on average and a cross term of std ~ 2 sqrt(S sigma^2 N / 2) ~ 2.9e4 per
  window-channel, i.e. ~1.8 % of S, averaged over 60 window-channels -> ~0.23 %; own vs median
  of 4 others differ by ~0.33 % (1 sigma). Ratio of 104 = 1 within 2 % (> 6 sigma).
  Noise-free, every class's ratio is exactly 1 (checked, 1e-12).
  Source: DFT, sample-mean variance.
  """
  X, y = _specific_subject(shared_hz=120 / 11, seed=11, n_win=20)
  res = dos.occipital_class_spectra(X, y, FS_LEGACY, SCALP, STIM, (5.0, 35.0), header_fs=256.0)
  s = res["specificity"][104]
  assert s["k"] == 11 and s["n_others"] == 4
  assert abs(s["ratio"] - 1.0) <= 0.02
  assert res["peaks"][101]["k_max"] == 11  # the shared rhythm is every class's maximum
  X0 = np.zeros_like(X)
  for c in ("O1", "Oz", "O2"):
    X0[:, SCALP.index(c)] = _sine(120 / 11, SPEC_A)
  res0 = dos.occipital_class_spectra(X0, y, FS_LEGACY, SCALP, STIM, (5.0, 35.0), header_fs=256.0)
  for code in STIM:
    assert abs(res0["specificity"][code]["ratio"] - 1.0) <= 1e-12


def test_format_peaks_with_rest_codes():
  """Known answer (audit fix 2d): conditions (201, 202, 101..105) -> format_peaks does not raise;
  the 201 and 202 lines are exactly `  S01 <code>: n=<n>, max in band at 29.297 Hz (bin 30, P=..);
  band median P=..` (30 Hz rest rhythm, bin 30 on the legacy axis) with no target, response bin
  or specificity; 201/202 are not counted among the 'other classes' (101: n_others 4).
  Source: 07_review fix 1c; 01_DATA_SPEC section 6.
  """
  X, y = _legacy_subject()
  conds = (201, 202) + STIM
  res = dos.occipital_class_spectra(X, y, FS_LEGACY, SCALP, conds, (5.0, 35.0), header_fs=256.0)
  text = dos.format_peaks("S01", res, conds)
  lines = text.splitlines()
  assert len(lines) == 7
  for ln, code, n in [(lines[0], 201, 8), (lines[1], 202, 4)]:
    pk = res["peaks"][code]
    assert ln == (f"  S01 {code}: n={n}, max in band at 29.297 Hz (bin 30, P={pk['p_max']:.4g}); "
                  f"band median P={pk['band_median']:.4g}")
  assert 201 not in res["specificity"] and 202 not in res["specificity"]
  assert res["specificity"][101]["n_others"] == 4
  assert "vs median of 4 other classes" in lines[2]
