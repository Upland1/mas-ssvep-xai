"""P17.1-2: harmonic / intermediate narrow banks, skip rule, overlaps, build identity, C-1 and the legacy label.

Known answers only: centres from the target list, a planted tone landing in the band of its own centre, a
hand-computed overlap, a synthetic fake recording built with two and with four banks.
"""

import csv
import hashlib
import json

import numpy as np
import pytest

from scripts import build_windows as bw
from scripts import freeze_baseline as fb
from src.preprocessing.windowing import (BANK_NAMES, STIM_FREQS, BandFilter, band_overlaps, band_windows,
                                         build_bank, harmonic_centers, intermediate_centers, narrow_filter_bank)
from tests import p16_synth as S
from tests.test_p16_freeze_baseline import tree  # noqa: F401  (fixture)


def test_centres_known_answer():
  h = harmonic_centers(3)
  assert len(h) == 15
  assert h[:6] == [24.0, 48.0, 72.0, 20.0, 40.0, 60.0]
  assert [round(c, 2) for c in h[9:]] == [10.91, 21.82, 32.73, 8.57, 17.14, 25.71]
  assert harmonic_centers(1) == list(STIM_FREQS)
  assert intermediate_centers() == pytest.approx([(8.57 + 10.91) / 2, (10.91 + 15) / 2, 17.5, 22.0])
  assert intermediate_centers([5.0, 1.0, 3.0]) == [2.0, 4.0]        # sorted before the midpoints
  with pytest.raises(ValueError):
    harmonic_centers(0)


def test_skip_rule_notch_and_nyquist():
  bank, sk = narrow_filter_bank(256.0, harmonic_centers(3), 1.0, 2, 90.0, (60.0,))
  assert len(bank) == 14 and [s["center"] for s in sk] == [60.0] and "60" in sk[0]["why"]
  assert not any(f.low <= 60.0 <= f.high for f in bank)
  # fs 128: nyq - 1 = 63 Hz caps the bands: 72 (above), 60 (notch) are skipped, 48 is kept
  bank, sk = narrow_filter_bank(128.0, harmonic_centers(3), 1.0, 2, 90.0, (60.0,))
  assert sorted(s["center"] for s in sk) == [60.0, 72.0] and max(f.high for f in bank) <= 63.0
  # max_hz below a band; an edge touching the notch counts as containing it
  _, sk = narrow_filter_bank(256.0, [30.0, 59.0, 40.0], 1.0, 2, 35.0, (60.0,))
  assert [s["center"] for s in sk] == [59.0, 40.0]
  # no notch: the 60 Hz band is built
  bank, sk = narrow_filter_bank(256.0, [60.0], 1.0, 2, 90.0, ())
  assert len(bank) == 1 and not sk
  assert narrow_filter_bank(256.0, [0.5], 1.0)[1][0]["why"] == "lower edge not positive"


def test_second_harmonic_tone_lands_in_its_band():
  fs = 256.0
  bank, _ = build_bank("harmonic", fs)
  t = np.arange(int(20 * fs)) / fs
  f0 = STIM_FREQS[3]                                          # 10.91 Hz
  x = np.sin(2 * np.pi * 2 * f0 * t)[None]                    # 2 * f0 only, no fundamental
  w = band_windows(x, np.array([int(5 * fs)]), int(fs), bank, "continuous")   # (1, B, 1, n)
  power = (w[0, :, 0] ** 2).mean(axis=-1)
  best = int(np.argmax(power))
  assert abs((bank[best].low + bank[best].high) / 2 - 2 * f0) < 1e-9
  assert power[best] > 0.4 and np.sort(power)[-2] < 0.02 * power[best]
  # R6: the saved band order is the order of the centres (60 Hz removed)
  centres = [c for c in harmonic_centers(3) if c != 60.0]
  assert [(f.low + f.high) / 2 for f in bank] == pytest.approx(centres)


def test_overlaps_known_answer():
  def band(lo, hi):
    return BandFilter(f"b{lo}", lo, hi, None, None)
  ov = band_overlaps([band(9.0, 11.0), band(10.5, 12.5), band(12.5, 14.0), band(20.0, 21.0)])
  assert len(ov) == 1                                          # touching edges (12.5) are not an overlap
  assert (ov[0]["a"], ov[0]["b"], ov[0]["low"], ov[0]["high"], ov[0]["width_hz"]) == ("b9.0", "b10.5", 10.5, 11.0, 0.5)
  inter, _ = build_bank("intermediate", 256.0)
  assert band_overlaps(inter) == []                            # +-1 Hz around 9.74, 12.96, 17.5, 22 are disjoint
  assert any(o["width_hz"] > 0 for o in band_overlaps(build_bank("harmonic", 256.0)[0]))   # 8.57 and 10.91 bands


# --- build ------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def raw(tmp_path_factory):
  root = tmp_path_factory.mktemp("raw17")
  S.write_raw_subject(root, "S01", n_trials=10, seed=3)
  return root


def _build(raw, out, *extra):
  assert bw.main(["--raw-dir", str(raw), "--out-root", str(out), "--subjects", "S01", *extra]) == 0
  return out / "S01"


def _sha(p):
  return hashlib.sha256(p.read_bytes()).hexdigest()


def test_four_bank_build_leaves_the_two_bank_files_identical(raw, tmp_path):
  two = _build(raw, tmp_path / "two", "--banks", "fbcca", "fbcsp", "--guard-sec", "1.5")
  four = _build(raw, tmp_path / "four", "--banks", "fbcca", "fbcsp", "harmonic", "intermediate", "--guard-sec", "1.5")
  n2, n4 = {p.name for p in two.iterdir()}, {p.name for p in four.iterdir()}
  assert n4 - n2 == {"X_bands_harmonic.npy", "X_bands_intermediate.npy"} and n2 <= n4
  for name in sorted(n2 - {"windows_meta.json"}):
    assert _sha(two / name) == _sha(four / name), name
  n = len(np.load(four / "y_labels.npy"))
  assert np.load(four / "X_bands_harmonic.npy").shape == (n, 14, 8, 256)
  assert np.load(four / "X_bands_intermediate.npy").shape == (n, 4, 8, 256)
  m2, m4 = (json.loads((d / "windows_meta.json").read_text()) for d in (two, four))
  assert m4["bands"]["fbcsp"] == m2["bands"]["fbcsp"] and list(m4["bands"]) == ["fbcca", "fbcsp", "harmonic", "intermediate"]
  assert [s["center"] for s in m4["bands_skipped"]["harmonic"]] == [60.0] and m4["bands_skipped"]["intermediate"] == []
  assert m4["bands_skipped"]["fbcsp"] == []
  assert len(m4["bands"]["harmonic"]) == 14
  assert m4["band_overlaps"]["intermediate"] == [] and m4["band_overlaps"]["harmonic"]
  assert m4["band_overlaps"]["combined"]                       # e.g. fbcsp 7-12 with harmonic 7.57-9.57
  assert all(o["a"].startswith(("butter_", "butter2_")) for o in m4["band_overlaps"]["combined"])


def test_auto_guard_grows_with_narrow_banks_and_only_masks_change(raw, tmp_path):
  two = _build(raw, tmp_path / "two", "--banks", "fbcca", "fbcsp")
  four = _build(raw, tmp_path / "four", "--banks", "fbcca", "fbcsp", "harmonic", "intermediate")
  g2, g4 = (json.loads((d / "windows_meta.json").read_text())["quality"]["guard_sec"] for d in (two, four))
  assert g4 > g2                                               # narrow order-2 bands ring longer (~1.05 s vs 0.90 s)
  for name in ("X_time_windows", "X_raw_windows", "X_bands_fbcca", "X_bands_fbcsp", "y_labels", "trial_ids",
               "window_starts", "valid_mask_no_guard"):
    assert _sha(two / f"{name}.npy") == _sha(four / f"{name}.npy"), name


def test_default_banks_follow_the_config_and_explicit_banks_win(raw, tmp_path):
  d = _build(raw, tmp_path / "def", "--guard-sec", "1.5")
  assert {p.name for p in d.iterdir() if p.name.startswith("X_bands")} == {f"X_bands_{b}.npy" for b in BANK_NAMES}
  cfg = bw.load_build_config(bw.DEFAULT_CONFIG)
  assert bw.default_banks(cfg) == list(BANK_NAMES)
  cfg["filter_bank"]["harmonics"]["enabled"] = False
  assert bw.default_banks(cfg) == ["fbcca", "fbcsp", "intermediate"]
  d1 = _build(raw, tmp_path / "one", "--banks", "harmonic", "--guard-sec", "1.5")
  assert {p.name for p in d1.iterdir() if p.name.startswith("X_bands")} == {"X_bands_harmonic.npy"}


def test_per_window_build_is_labelled_legacy(raw, tmp_path, capsys):
  d = _build(raw, tmp_path / "pw", "--filter-mode", "per_window", "--banks", "fbcsp", "--guard-sec", "1.5")
  out = capsys.readouterr().out
  m = json.loads((d / "windows_meta.json").read_text())
  assert m["legacy"] is True and "legacy" in m["data_source"] and "Data source: legacy per_window" in out
  c = json.loads((_build(raw, tmp_path / "ct", "--banks", "fbcsp", "--guard-sec", "1.5") / "windows_meta.json").read_text())
  assert c["legacy"] is False and c["data_source"] == "continuous build"


def test_missing_filter_bank_config_raises(tmp_path):
  import yaml
  cfg = yaml.safe_load(bw.DEFAULT_CONFIG.read_text())
  del cfg["filter_bank"]["harmonics"]["order"]
  p = tmp_path / "c.yaml"
  p.write_text(yaml.safe_dump(cfg))
  with pytest.raises(ValueError, match="filter_bank.harmonics.order"):
    bw.load_build_config(p)


# --- C-1 ---------------------------------------------------------------------------------

def test_freeze_skips_the_mean_row_for_new_tags_only(tree):  # noqa: F811
  with open(tree / "reports/n_subjects_benchmark.csv", "a") as f:
    f.write("Mean,,,,,55.0,65.0\n")

  def summary(tag):
    snap = fb.freeze(tree, tag, "n", date="2026-10-28", with_pip=False)
    rows = list(csv.DictReader(open(snap / "baseline_summary.csv")))
    return {(r["pipeline"], r["subject"], r["metric"]): float(r["value"]) for r in rows}

  v1 = summary("v1")
  assert ("flagship_n_subjects", "Mean", "1.0s Acc (%)") in v1                       # v1 stays as frozen
  assert v1[("flagship_n_subjects", "MEAN", "1.0s Acc (%)")] == pytest.approx((60 + 50 + 55) / 3)
  v3 = summary("v3")
  assert not any(k[1] == "Mean" for k in v3)
  assert v3[("flagship_n_subjects", "MEAN", "1.0s Acc (%)")] == 55.0                 # mean of S01, S02 only
