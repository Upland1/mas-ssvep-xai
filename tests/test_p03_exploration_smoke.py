"""P03 builder smoke tests (signal-processing): exploration scripts and spectral helpers.

Synthetic legacy folders written to tmp_path only (never data/); the known-answer suite is
the synthetic-tester's.
"""

import numpy as np
import pytest

from scripts.exploration import diagnose_occipital_spectra as dos
from scripts.exploration import visualize_data as vd
from src.features.ssvep import spectral_power as sp

FS_TRUE = 256
SCALP = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
PLANT = {101: 24.0, 102: 20.0, 103: 15.0, 104: 11.0, 105: 9.0}  # integer bins at fs 256


def _legacy_arrays(seed=0, per_class=10, bad_rows=0, names=SCALP):
  """Legacy-layout arrays: 201/202 rows with 30 Hz on O1/Oz/O2, stimulus rows with PLANT on them."""
  rng = np.random.default_rng(seed)
  t = np.arange(FS_TRUE) / FS_TRUE
  occ = [names.index(c) for c in ("O1", "Oz", "O2")]
  X, y = [], []
  for code, n, f in [(201, 8, 30.0), (202, 4, 30.0)] + [(c, per_class, PLANT[c]) for c in PLANT]:
    for _ in range(n):
      w = rng.normal(0, 1.0, (len(names), FS_TRUE))
      w[occ] += 10 * np.sin(2 * np.pi * f * t)
      X.append(w)
      y.append(code)
  X, y = np.stack(X), np.asarray(y, dtype=np.int64)
  stim = np.flatnonzero(y == 103)[:bad_rows]
  X[stim, 2, 10] += 500.0  # vpp_high on PO4
  return X, y


def _write(folder, X, y, fs=FS_TRUE):
  folder.mkdir(parents=True, exist_ok=True)
  Xp, _, _ = sp.psd_features(X, fs, (5.0, 35.0))
  np.save(folder / "X_time_windows.npy", X)
  np.save(folder / "y_labels.npy", y)
  np.save(folder / "X_psd_features.npy", Xp)


def test_fft_power_peak_and_legacy_label():
  t = np.arange(256) / 256
  w = np.sin(2 * np.pi * 24 * t)[None, None]
  f, p = sp.fft_power(w, 250.0)
  k = int(np.argmax(p[0, 0]))
  assert k == 24 and f[k] == pytest.approx(24 * 250 / 256, abs=1e-9)
  f, p = sp.fft_power(w, 256.0)
  assert f[int(np.argmax(p[0, 0]))] == 24.0


def test_select_by_name_and_count_check():
  assert sp.select_channels_by_name(SCALP, ("O1", "Oz", "O2"), 7) == [4, 5, 6]
  with pytest.raises(ValueError):
    sp.select_channels_by_name(["PO7"] + SCALP, ("O1",), 7)
  with pytest.raises(ValueError):
    sp.select_channels_by_name(SCALP, ("PO7",), 7)


def test_fs_label():
  assert sp.fs_label(250, 256) == "fs=250 (legacy)"
  assert sp.fs_label(256, 256) == "fs=256 (header)"
  assert sp.fs_label(300, 256) == "fs=300 (override)"


def test_psd_feature_widths():
  X = np.random.default_rng(0).normal(size=(3, 7, 256))
  assert sp.psd_features(X, 256, (5, 35))[0].shape == (3, 217)
  assert sp.psd_features(X, 250, (5, 35))[0].shape == (3, 210)


def test_occipital_class_spectra_by_name_reordered():
  names = list(reversed(SCALP))
  X, y = _legacy_arrays(names=names)
  res = dos.occipital_class_spectra(X, y, 256.0, names, tuple(PLANT), (5.0, 35.0))
  assert set(res["spectra"]) == set(PLANT)
  for c, f in PLANT.items():
    assert res["peaks"][c]["f_max"] == f
    assert res["counts"][c] == 10


def test_quality_mask_counts():
  X, y = _legacy_arrays(bad_rows=3)
  q = vd.quality_mask(X, y, vpp_min=0.5, vpp_max=200.0, std_min=0.5, std_max=60.0)
  assert q["n_rejected"] == 3
  assert q["by_label"][103]["rejected"] == 3 and q["by_label"][103]["reasons"]["vpp_high"] == 3


def test_scripts_smoke(tmp_path, capsys):
  proc, figs = tmp_path / "processed", tmp_path / "figures"
  X, y = _legacy_arrays(bad_rows=2)
  _write(proc / "S01", X, y)
  (proc / "S02").mkdir(parents=True)
  rc = dos.main(["--all", "--processed-dir", str(proc), "--figures-dir", str(figs)])
  out = capsys.readouterr().out
  assert rc == 0 and "[-] Skipping S02" in out and "fs=250 (legacy)" in out
  assert (figs / "exploration" / "S01" / "occipital_spectra.png").stat().st_size > 0
  rc = dos.main(["--subject", "S01", "--fs", "256", "--out-suffix", "header",
                 "--processed-dir", str(proc), "--figures-dir", str(figs)])
  out = capsys.readouterr().out
  assert rc == 0 and "fs=256 (header)" in out
  assert "max in band at 15.000 Hz" in out
  assert (figs / "exploration" / "S01" / "occipital_spectra_header.png").is_file()
  rc = vd.main(["--all", "--fs", "256", "--processed-dir", str(proc), "--figures-dir", str(figs)])
  out = capsys.readouterr().out
  assert rc == 0 and "rejected 2" in out and "max |computed - saved| = 0" in out
  assert (figs / "exploration" / "S01" / "psd_features_by_class.png").stat().st_size > 0
  rc = vd.main(["--subject", "S01", "--no-figures", "--processed-dir", str(proc)])
  assert rc == 0 and "not comparable at fs=250 (legacy)" in capsys.readouterr().out


def test_length_mismatch_fails(tmp_path):
  X, y = _legacy_arrays()
  _write(tmp_path / "S01", X, y[:-1])
  with pytest.raises(ValueError):
    dos.load_legacy_windows(tmp_path, "S01")


def test_response_bin_vs_nearest_labelled():
  assert sp.response_bin(24.0, 256, 256.0) == 24
  t = np.arange(256) / 256
  w = np.sin(2 * np.pi * 24 * t)[None, None] + np.sin(2 * np.pi * 30 * t)[None, None]
  f, p = sp.fft_power(w, 250.0)
  pk = sp.spectrum_peaks(f, p[0, 0], (5, 35), target_hz=15.0, header_fs=256.0, n_samples=256)
  h2 = pk["harmonics"][1]
  assert (h2["k_resp"], h2["k"]) == (30, 31) and h2["power_resp"] > 1e3 * h2["power"]
  pk = sp.spectrum_peaks(f, p[0, 0], (5, 35), target_hz=24.0, header_fs=256.0, n_samples=256)
  assert (pk["harmonics"][0]["k_resp"], pk["harmonics"][0]["k"]) == (24, 25)


def test_specificity_and_format(tmp_path):
  X, y = _legacy_arrays()
  conds = (201,) + tuple(PLANT)
  res = dos.occipital_class_spectra(X, y, 250.0, SCALP, conds, (5.0, 35.0), header_fs=256.0)
  for c in PLANT:
    assert res["specificity"][c]["ratio"] > 100 and res["specificity"][c]["n_others"] == 4
  assert 201 not in res["specificity"]
  out = dos.format_peaks("S01", res, conds)
  assert "S01 201: n=8, max in band at" in out
  assert "1f0 response bin 24 (23.438 Hz)" in out and "nearest-labelled bin 25 (24.414 Hz)" in out
  res = dos.occipital_class_spectra(X, y, 256.0, SCALP, tuple(PLANT), (5.0, 35.0), header_fs=256.0)
  assert "nearest-labelled" not in dos.format_peaks("S01", res, tuple(PLANT))
  shared = X.copy()  # same 10 Hz rhythm in every class -> ratio ~ 1 at bin 10
  t = np.arange(256) / 256
  shared[:, 4:7] = 10 * np.sin(2 * np.pi * 10 * t)
  r = dos.specificity_ratio(dos.occipital_class_spectra(shared, y, 256.0, SCALP, tuple(PLANT))["spectra"],
                            104, 10)
  assert abs(r["ratio"] - 1) < 1e-9
