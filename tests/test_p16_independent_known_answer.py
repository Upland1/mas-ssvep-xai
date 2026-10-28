"""P16 synthetic-tester: independent known-answer tests (window index, bands, quality, loader, freeze, ports).

Written from the plan's risk table, not from the builders' tests. Synthetic data only; no generated or
git-ignored file is read. `tests/p16_synth.py` is used only as a fake-recording writer.
"""

import hashlib
import io
import json
import os
import stat
import tokenize
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.signal import butter, sosfiltfilt, sosfreqz

from scripts import freeze_baseline as fb
from scripts.benchmarks.feature_based import benchmark_n_subjects as B
from scripts.connectivity.analysis import analyze_connectivity_cohort as cohort
from scripts.diagnostics import compare_v1_v2 as cmp
from src.features.ssvep.fbcca_extraction import TARGET_FREQS, extract_fbcca_features
from src.io import subject_data as SD
from src.preprocessing import window_quality as wq
from src.preprocessing import windowing as W
from tests import p05_synth, p16_synth as S

FS = 256
STIM = [101, 102, 103, 104, 105]
ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- window index

def legacy_starts(mark, fs):
  """The P02 legacy starts, written out by hand from the data spec (not via the module under test)."""
  L = lambda s: int(s * fs)
  on = lambda c: np.flatnonzero(mark == c)
  out = {201: [], 202: []}
  for o in on(201):
    out[201] += [o, o + L(1)] if o + L(2) <= len(mark) else []
  for o in on(202):
    out[202] += [o - L(1)] if o - L(1) >= 0 else []
  for c in STIM:
    out[c] = []
    for o in on(c):
      if o + L(5) <= len(mark):
        out[c] += [o + k * L(1) for k in range(5)]
  return out


@pytest.mark.parametrize("fs", [256, 250])
def test_window_index_equals_hand_written_legacy_starts_with_truncated_trial(fs):
  mark = S.make_block(n_trials=10, seed=4, fs=fs, truncate_last=True)[10]
  idx = W.build_window_index(mark, fs, STIM)
  exp = legacy_starts(mark, fs)
  for c, st in exp.items():
    got = idx.starts[idx.labels == c]
    assert np.array_equal(np.sort(got), np.sort(np.array(st, dtype=np.int64))), c
  assert len(idx.skipped) == 1 and idx.skipped[0]["onset"] in np.flatnonzero(mark)    # the truncated stimulus only
  assert idx.skipped[0]["condition"] in STIM
  # 9 complete stimulus trials * 5 windows, 10 fixation * 2, 10 cue * 1
  assert (idx.labels >= 101).sum() - (idx.labels >= 201).sum() == 45
  assert (idx.labels == 201).sum() == 20 and (idx.labels == 202).sum() == 10


def test_full_session_counts_80_40_200():
  mark = S.make_block(n_trials=40, seed=1)[10]
  idx = W.build_window_index(mark, FS, STIM)
  assert ((idx.labels == 201).sum(), (idx.labels == 202).sum(), np.isin(idx.labels, STIM).sum()) == (80, 40, 200)


def test_stride_half_second_offsets_restart_per_segment_and_one_id_per_segment():
  mark = S.make_block(n_trials=10, seed=2)[10]
  idx = W.build_window_index(mark, FS, STIM, stride_sec=0.5)
  per = {201: 3, 202: 1, **{c: 9 for c in STIM}}                 # (len - 256) // 128 + 1
  n_seg = 10 + 10 + 10
  assert len(np.unique(idx.trial_ids)) == n_seg
  assert len(idx) == 10 * 3 + 10 * 1 + 10 * 9
  for t in np.unique(idx.trial_ids):
    r = idx.trial_ids == t
    lab = np.unique(idx.labels[r])
    assert len(lab) == 1 and r.sum() == per[int(lab[0])]
    assert np.array_equal(idx.sub_idx[r], np.arange(r.sum()))          # 0..k-1
    assert np.array_equal(idx.offsets[r], 128 * np.arange(r.sum()))     # restart at 0 in every segment
    assert np.array_equal(np.diff(idx.starts[r]), np.full(r.sum() - 1, 128))
  assert np.all(np.diff(idx.trial_ids) >= 0)
  # sorting by offset alone would interleave trials: it is not the row order
  assert not np.array_equal(np.argsort(idx.offsets, kind="stable"), np.arange(len(idx)))


def test_window_index_uses_the_fs_given_not_a_literal():
  mark = np.zeros(20000)
  mark[1000] = 101
  a, b = W.build_window_index(mark, 250, [101]), W.build_window_index(mark, 256, [101])
  assert np.diff(a.starts[a.labels == 101]).tolist() == [250] * 4
  assert np.diff(b.starts[b.labels == 101]).tolist() == [256] * 4


# ---------------------------------------------------------------- band_windows

def _recording(seed=0, C=2, T=30 * FS):
  rng = np.random.default_rng(seed)
  t = np.arange(T) / FS
  return rng.normal(0, 3, (C, T)) + 8 * np.sin(2 * np.pi * 15 * t)[None]


def test_band_windows_continuous_is_filter_then_cut_exactly_and_per_window_has_edge_error():
  x = _recording()
  starts = np.arange(3, 25) * FS
  bank = [b for b in W.fbcsp_filter_bank(FS) if (b.low, b.high) == (13.0, 17.0)]
  assert len(bank) == 1
  sos = butter(4, [13, 17], btype="band", fs=FS, output="sos")
  full = sosfiltfilt(sos, x, axis=-1)
  ref = np.stack([full[:, s:s + FS] for s in starts])                     # (n, C, T), by hand
  cont = W.band_windows(x, starts, FS, bank, "continuous")
  assert cont.shape == (len(starts), 1, 2, FS)                            # (window, band, channel, time)
  assert np.max(np.abs(cont[:, 0] - ref)) < 1e-9
  pw = W.band_windows(x, starts, FS, bank, "per_window")[:, 0]
  err = np.abs(pw - ref)
  e = int(0.1 * FS)
  edge = np.concatenate([err[..., :e].ravel(), err[..., -e:].ravel()]).mean()
  centre = err[..., FS // 2 - e // 2: FS // 2 + e // 2].mean()
  assert edge / centre > 3.0, (edge, centre)                              # PF-14: per-window filtering distorts the edges
  assert not np.allclose(pw, ref, atol=1e-3)


def test_band_layout_tone_lands_in_its_band_and_channel():
  T = 20 * FS
  t = np.arange(T) / FS
  x = np.zeros((3, T))
  x[0] = np.sin(2 * np.pi * 9 * t)       # fbcsp band 7-12 (index 0)
  x[2] = np.sin(2 * np.pi * 30 * t)      # fbcsp band 27-36 (index 3)
  bank = W.fbcsp_filter_bank(FS)
  out = W.band_windows(x, np.array([5 * FS]), FS, bank, "continuous")[0]   # (B, C, T)
  rms = np.sqrt((out ** 2).mean(-1))
  assert rms[0, 0] > 0.5 and rms[3, 2] > 0.5
  rms2 = rms.copy()
  rms2[0, 0] = rms2[3, 2] = 0
  assert rms2.max() < 0.05


# ---------------------------------------------------------------- ringing time and the guard

def _zero_phase_ringing_samples(sos, rel=0.01):
  """Independent: zero-phase impulse response = irfft(|H|^2) on a dense grid."""
  n = 2 ** 17
  _, h = sosfreqz(sos, worN=n // 2 + 1, fs=FS)
  imp = np.fft.irfft(np.abs(h) ** 2, n)
  imp = np.fft.fftshift(imp)
  c = n // 2
  above = np.flatnonzero(np.abs(imp) > rel * np.abs(imp).max())
  return int(np.abs(above - c).max())


@pytest.mark.parametrize("band", [(13, 17), (7, 12)])
def test_ringing_time_equals_one_percent_span_of_the_zero_phase_response(band):
  sos = butter(4, band, btype="band", fs=FS, output="sos")
  got = wq.ringing_time_sec([sos], FS) * FS
  assert abs(got - _zero_phase_ringing_samples(sos)) <= 1


def test_ringing_time_takes_the_longest_filter():
  a = butter(4, [13, 17], btype="band", fs=FS, output="sos")
  b = butter(4, [1, 90], btype="band", fs=FS, output="sos")
  assert wq.ringing_time_sec([a, b], FS) == pytest.approx(max(wq.ringing_time_sec([a], FS), wq.ringing_time_sec([b], FS)))
  assert wq.ringing_time_sec([a], FS) > wq.ringing_time_sec([b], FS)         # the narrow band rings longest


GATE = {"thresholds": {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0}, "channel_fail_fraction": 0.5}
PARAMS = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0, "channel_fail_fraction": 0.5,
          "artifact_block_sec": 1.0, "guard_sec": 2.0, "guard_rel_amplitude": 0.01}
NAMES = ["PO3", "POz", "Oz", "O1"]


def _gate_input(seed=0, T=60 * FS, spike=None, bad=None):
  rng = np.random.default_rng(seed)
  x = rng.normal(0, 5.0, (4, T))
  if bad is not None:
    x[bad] = rng.normal(0, 80.0, T)
  for ch, sec in (spike or []):
    x[ch, int(sec * FS)] += 500.0
  starts = np.arange(0, T // FS) * FS
  return x, starts, W.cut_windows(x, starts, FS)


def test_artifact_inside_guard_gives_reason_2_and_no_guard_mask_keeps_them():
  x, starts, w = _gate_input(spike=[(1, 30.5)])
  g = wq.subject_quality_gate(w, starts, x, FS, NAMES, [], PARAMS)
  assert g["guard_sec"] == 2.0 and g["channels_dropped"] == []
  reason = g["reason"]
  assert reason[30] == 1                                            # contains the spike: own gate
  assert set(np.flatnonzero(reason == 2)) == {28, 29, 31, 32}       # block [30,31) dilated by 2 s
  assert np.flatnonzero(g["valid_mask"] == 0).tolist() == [28, 29, 30, 31, 32]
  assert np.flatnonzero(g["valid_mask_no_guard"] == 0).tolist() == [30]
  assert g["valid_mask"].sum() == 55 and g["valid_mask_no_guard"].sum() == 59
  assert g["n_artifact_blocks"] == 1 and g["artifact_fraction"] == pytest.approx(1 / 60)


def test_guard_auto_equals_ringing_time_of_the_filters():
  x, starts, w = _gate_input(seed=2)
  sos = butter(4, [13, 17], btype="band", fs=FS, output="sos")
  g = wq.subject_quality_gate(w, starts, x, FS, NAMES, [sos], {**PARAMS, "guard_sec": "auto"})
  assert g["guard_sec"] == pytest.approx(wq.ringing_time_sec([sos], FS))
  assert g["guard_samples"] == int(round(g["guard_sec"] * FS)) and g["valid_mask"].all()


@pytest.mark.parametrize("key", wq.PARAM_KEYS)
def test_every_threshold_must_be_explicit(key):
  x, starts, w = _gate_input()
  p = {k: v for k, v in PARAMS.items() if k != key}
  with pytest.raises(ValueError):
    wq.subject_quality_gate(w, starts, x, FS, NAMES, [], p)


def test_channel_tier_drops_the_bad_channel_and_judges_windows_on_the_rest():
  # channel 3 (O1) is noisy everywhere; a spike on it in window 10 must be ignored, one on PO3 in window 20 counts
  x, starts, w = _gate_input(seed=3, bad=3, spike=[(3, 10.5), (0, 20.5)])
  g = wq.subject_quality_gate(w, starts, x, FS, NAMES, [], PARAMS)
  assert g["channels_dropped"] == ["O1"] and g["channels_kept"] == ["PO3", "POz", "Oz"]
  assert g["valid_mask_no_guard"][10] == 1 and g["valid_mask"][10] == 1
  assert g["reason"][20] == 1 and g["valid_mask_no_guard"][20] == 0
  assert set(np.flatnonzero(g["reason"] == 2)) == {18, 19, 21, 22}
  assert g["valid_mask"].sum() == 60 - 5


# ---------------------------------------------------------------- loader

@pytest.fixture(scope="module")
def built(tmp_path_factory):
  root = tmp_path_factory.mktemp("ind_built")
  S.write_built_subject(root, "S01", n_trials=10, seed=1)
  S.write_built_subject(root, "S02", n_trials=10, seed=2, spike_s=57.5, bad_channel="O2")
  return root


@pytest.fixture(scope="module")
def legacy(tmp_path_factory):
  root = tmp_path_factory.mktemp("ind_legacy")
  p05_synth.write_subject(root, "S03", n_trials=6)
  return root


def test_one_true_id_per_segment_and_cv_groups_twin_of_202(built):
  d = SD.load_subject(built / "S01", conditions=(101, 102, 103, 104, 105, 201, 202))
  y, ids, grp, st = d["y"], d["trial_ids"], d["cv_groups"], d["window_starts"]
  assert len(np.unique(ids[y == 202])) == 10 and len(np.unique(ids[y == 201])) == 10
  assert not set(ids[y == 201]) & set(ids[y == 202])                     # saved ids: one per segment
  for i in np.flatnonzero(y == 202):
    twin = np.flatnonzero((y == 201) & (st == st[i]))
    assert len(twin) == 1 and grp[twin[0]] == grp[i] and ids[twin[0]] != ids[i]    # PF-13 twin
  stim = np.isin(y, STIM)
  assert not set(grp[stim]) & set(grp[~stim])                              # stimulus trials never share a group with 201/202
  assert np.array_equal(grp[stim], ids[stim])
  assert d["smoothing"] == "trial" and d["built"] and d["fs"] == 256.0 and d["fs_source"] == "meta"


def test_loader_fs_meta_vs_legacy_vs_override(built, legacy):
  b = SD.load_subject(built / "S01")
  assert (b["fs"], b["fs_source"], b["built"]) == (256.0, "meta", True)
  assert SD.load_subject(built / "S01", fs_override=250)["fs"] == 250.0
  l = SD.load_subject(legacy / "S03", **GATE)
  assert (l["fs"], l["fs_source"], l["built"], l["smoothing"]) == (250.0, "legacy-assumed", False, "mod5")
  lo = SD.load_subject(legacy / "S03", fs_override=256, **GATE)
  assert (lo["fs"], lo["fs_source"]) == (256.0, "override") and np.array_equal(lo["X"], l["X"])
  with pytest.raises(ValueError):
    SD.load_subject(legacy / "S03", bands=("fbcca",), **GATE)                    # a legacy folder has no saved bands
  with pytest.raises(ValueError):
    SD.load_subject(built / "S01", quality_mode="bogus")


def test_quality_modes_shared_nogaurd_perscript(built):
  sh = SD.load_subject(built / "S02", quality_mode="shared")
  ng = SD.load_subject(built / "S02", quality_mode="shared-no-guard")
  ps = SD.load_subject(built / "S02", quality_mode="per-script",
                       **GATE)
  assert len(sh["y"]) < len(ng["y"])                                      # the spike at 57.5 s costs guard windows
  lost = set(ng["window_starts"]) - set(sh["window_starts"])
  spike = int(57.5 * FS)
  assert lost and all(abs(s + FS / 2 - spike) < (0.902 + 2.0) * FS for s in lost)
  assert "O2" in sh["channels_dropped"] and "O2" in ng["channels_dropped"]
  assert "per-script" in ps["quality"]["source"] and ps["quality"]["mode"] == "per-script"
  assert sh["quality"]["guard_sec"] == pytest.approx(0.902, abs=0.01)
  assert set(sh["window_starts"]) <= set(ng["window_starts"])


# ---------------------------------------------------------------- freeze_baseline

@pytest.fixture
def tree(tmp_path):
  r = tmp_path / "repo"
  (r / "data/processed/S01").mkdir(parents=True)
  np.save(r / "data/processed/S01/X_time_windows.npy", np.arange(24.0).reshape(2, 3, 4))
  np.save(r / "data/processed/S01/y_labels.npy", np.array([101, 102]))
  (r / "reports").mkdir()
  (r / "reports/n_subjects_benchmark.csv").write_text(
    "Subject,Clean Windows,Rejected Windows,1.0s Acc (%),2.0s Smoothed (%)\nS01,100,0,40.0,50.0\nS02,90,5,60.0,80.0\n")
  (r / "reports/five_subjects_benchmark.csv").write_text("Subject,Clean Windows\nS01,100\n")
  (r / "outputs/reports").mkdir(parents=True)
  (r / "outputs/reports/a.csv").write_text("a\n1\n")
  (r / "configs").mkdir()
  (r / "configs/pipeline_config.yaml").write_text("v: 1\n")
  yield r
  for p in (r / "baselines").rglob("*"):
    p.chmod(p.stat().st_mode | stat.S_IWUSR)
  if (r / "baselines").exists():
    (r / "baselines").chmod(0o755)


def test_freeze_read_only_refusal_manifest_hashes_superseded_and_summary(tree, capsys):
  assert fb.main(["--root", str(tree), "--tag", "v1", "--date", "2026-01-02"]) == 0
  snap = tree / "baselines" / "v1_2026-01-02"
  man = json.loads((snap / "MANIFEST.json").read_text())
  for e in man["files"]:                                                   # hash of every source file
    src = tree / e["path"]
    assert e["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert (snap / e.get("stored_as", e["path"])).read_bytes() == src.read_bytes()
  assert man["n_files"] == 6 and (snap / "superseded/five_subjects_benchmark.csv").is_file()
  assert not (snap / "reports/five_subjects_benchmark.csv").exists()
  before = (snap / "MANIFEST.json").read_bytes()
  assert fb.main(["--root", str(tree), "--tag", "v1", "--date", "2026-03-04"]) != 0     # refuses, any date
  assert not (tree / "baselines" / "v1_2026-03-04").exists()
  assert (snap / "MANIFEST.json").read_bytes() == before
  if os.geteuid() != 0:
    assert all(not (p.stat().st_mode & 0o222) for p in snap.rglob("*"))
    with pytest.raises(PermissionError):
      (snap / "reports/new.csv").write_text("x")
    with pytest.raises(PermissionError):
      (snap / "reports/n_subjects_benchmark.csv").write_text("x")
  rows = pd.read_csv(snap / "baseline_summary.csv")
  assert list(rows.columns) == ["pipeline", "subject", "metric", "value"]
  m = rows[(rows.pipeline == "flagship_n_subjects") & (rows.metric == "2.0s Smoothed (%)")].set_index("subject").value
  assert m["MEAN"] == 65.0 and m["S01"] == 50.0 and m["S02"] == 80.0
  # the source tree is untouched
  assert (tree / "reports/five_subjects_benchmark.csv").is_file()


# ---------------------------------------------------------------- flagship port

def test_flagship_features_come_from_the_saved_bands_not_from_refiltering(built, tmp_path):
  import shutil
  root = tmp_path / "tampered"
  shutil.copytree(built / "S01", root / "S01")
  base = SD.load_subject(root / "S01", bands=("fbcca", "fbcsp"))
  space0, sub0 = B.feature_blocks(base, 1)
  np.save(root / "S01/X_bands_fbcsp.npy", 3.0 * np.load(root / "S01/X_bands_fbcsp.npy"))
  np.save(root / "S01/X_bands_fbcca.npy", np.roll(np.load(root / "S01/X_bands_fbcca.npy"), 1, axis=1))
  tam = SD.load_subject(root / "S01", bands=("fbcca", "fbcsp"))
  space1, sub1 = B.feature_blocks(tam, 1)
  assert np.allclose(sub1, 3.0 * sub0)                                       # CSP bands are the saved ones
  assert not np.allclose(space1.static[0], space0.static[0])                 # FBCCA scores follow the saved bands


def test_flagship_smoothing_resets_per_true_trial_ordered_by_trial_offset(built, monkeypatch):
  d = SD.load_subject(built / "S02", bands=("fbcca", "fbcsp"))
  n, k = len(d["y"]), 5
  rng = np.random.default_rng(7)
  classes = np.unique(d["y"])
  scores = 0.01 * rng.random((n, k)) + (d["y"][:, None] == classes[None]).astype(float)   # confident and correct

  def fake_oof(space, sub, y, models, seed, splits):
    return {B.MODEL: {"pred": classes[scores.argmax(1)], "scores": scores}}, {}

  monkeypatch.setattr(B, "oof_space", fake_oof)
  ids = d["trial_ids"]
  sm = scores.copy()
  for i in range(1, n):                                                     # by hand: average with previous window of the SAME trial
    if ids[i] == ids[i - 1]:
      sm[i] = (scores[i - 1] + scores[i]) / 2
  exp_trial = round(100 * float((classes[sm.argmax(1)] == d["y"]).mean()), 2)
  sm5 = scores.copy()
  for i in range(1, n):
    if i % 5 != 0:
      sm5[i] = (scores[i - 1] + scores[i]) / 2
  exp_mod5 = round(100 * float((classes[sm5.argmax(1)] == d["y"]).mean()), 2)
  smx = scores.copy()
  smx[1:] = (scores[:-1] + scores[1:]) / 2                                  # the bug: smoothing across trial boundaries
  exp_cross = round(100 * float((classes[smx.argmax(1)] == d["y"]).mean()), 2)
  assert exp_trial == 100.0 and exp_mod5 < exp_trial and exp_cross < exp_trial   # the rules differ, so the test can tell
  row = B.evaluate_subject(built, "S02")["row"]
  assert row["2.0s Smoothed (%)"] == exp_trial
  assert row["1.0s Acc (%)"] == round(100 * float((classes[scores.argmax(1)] == d["y"]).mean()), 2)


def test_flagship_cv_repeats_columns_are_mean_and_sample_sd_of_seeds(built):
  r3 = B.evaluate_subject(built, "S01", repeats=3, seed=42)["row"]
  singles = [B.evaluate_subject(built, "S01", repeats=1, seed=42 + r)["row"] for r in range(3)]
  a1 = np.array([s["1.0s Acc (%)"] for s in singles])
  a2 = np.array([s["2.0s Smoothed (%)"] for s in singles])
  assert r3["CV repeats"] == 3
  assert r3["1.0s Acc (%)"] == pytest.approx(a1.mean(), abs=0.011) and r3["2.0s Smoothed (%)"] == pytest.approx(a2.mean(), abs=0.011)
  assert r3["1.0s SD"] == pytest.approx(a1.std(ddof=1), abs=0.02) and r3["2.0s SD"] == pytest.approx(a2.std(ddof=1), abs=0.02)
  assert "1.0s SD" not in singles[0]
  assert B.derived_suffix(True, "continuous", "shared-no-guard", None, 5) == "continuous_sharednoguard_rep5"
  assert B.derived_suffix(False, None, "shared", None, 1) == ""


def test_pf04_24hz_tone_at_256hz_needs_the_metadata_fs():
  fs, T = 256, 256
  t = np.arange(T) / fs
  rng = np.random.default_rng(0)
  X = np.stack([np.sin(2 * np.pi * 24.0 * t + p) + 0.01 * rng.normal(size=T) for p in rng.uniform(0, 1, 7)])[None]
  X = np.repeat(X, 3, axis=0) * 20.0
  y = np.full(3, 101)
  names = ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]
  s256 = extract_fbcca_features(X, y, names, fs=256.0, target_freqs=TARGET_FREQS)[0][0]
  s250 = extract_fbcca_features(X, y, names, fs=250.0, target_freqs=TARGET_FREQS)[0][0]
  assert int(np.argmax(s256)) == int(np.argmin(np.abs(np.array(TARGET_FREQS) - 24.0)))
  assert s256[0] > 1.5 * s250[0]                                             # the 250 literal loses the 24 Hz match


def _numbers(path):
  out = []
  for tok in tokenize.generate_tokens(io.StringIO(path.read_text()).readline):
    if tok.type == tokenize.NUMBER:
      out.append((tok.start[0], tok.string))
  return out


@pytest.mark.parametrize("rel", ["src/preprocessing/windowing.py", "src/preprocessing/window_quality.py",
                                 "src/io/subject_data.py", "scripts/build_windows.py",
                                 "scripts/benchmarks/feature_based/benchmark_n_subjects.py",
                                 "scripts/connectivity/analysis/analyze_connectivity_cohort.py"])
def test_no_fs_literal_in_the_v2_code(rel):
  bad = [(ln, s) for ln, s in _numbers(ROOT / rel) if s in ("250", "250.0", "256", "256.0", "250.", "256.")]
  assert bad == [], bad


# ---------------------------------------------------------------- connectivity port

def _run_cohort(root, tmp_path, extra=(), suffix="ind"):
  calls = []
  real = cohort.extract_connectivity_by_condition

  def spy(*a, **k):
    calls.append((a, k))
    return real(*a, **k)

  cohort.extract_connectivity_by_condition = spy
  try:
    rc = cohort.main(["--methods", "coherence", "--permutations", "9", "--n-jobs", "1", "--data-root", str(root),
                      "--subjects", "S01", "--reports-dir", str(tmp_path / "rep"), "--out-suffix", suffix, *extra])
  finally:
    cohort.extract_connectivity_by_condition = real
  assert rc == 0
  return calls


def test_connectivity_port_uses_meta_fs_and_true_ids_and_fs_override(built, tmp_path):
  d = SD.load_subject(built / "S01", conditions=(101, 102, 103, 104, 105, 201))
  (a, k), = _run_cohort(built, tmp_path)
  assert a[2] == 256.0
  assert np.array_equal(k["trial_ids"], d["trial_ids"]) and len(k["trial_ids"]) == len(a[1]) == len(d["y"])
  per_class = [set(k["trial_ids"][a[1] == c]) for c in STIM]
  assert all(len(s) == 2 for s in per_class)                                  # 10 trials / 5 classes, true trials
  assert not set.union(*per_class) & set(k["trial_ids"][a[1] == 201])
  (a2, _), = _run_cohort(built, tmp_path, extra=("--fs", "250"), suffix="ind250")
  assert a2[2] == 250.0


# ---------------------------------------------------------------- compare_v1_v2

def test_compare_v1_v2_labels_connectivity_filter_mode_not_applicable(tmp_path):
  def flag(vals):
    return pd.DataFrame({"Subject": ["S01", "Mean"], "1.0s Acc (%)": [vals, vals], "1.0s SD": [1.0, 1.0],
                         "2.0s Smoothed (%)": [vals + 5, vals + 5], "2.0s SD": [1.0, 1.0]})

  def conn(v, e):
    return pd.DataFrame({"subject": ["S01"], "method": ["coherence"], "condition": [101], "frequency_hz": [24.0],
                         "obs_diff": [v], "p_one_tailed": [0.1], "n_edges_sig_fdr": [e]})

  base = tmp_path / "baselines/v1_2026-01-01/reports"
  base.mkdir(parents=True)
  flag(60.0).to_csv(base / "n_subjects_benchmark.csv", index=False)
  conn(0.10, 1).to_csv(base / "connectivity_cohort_summary.csv", index=False)
  rep = tmp_path / "reports"
  rep.mkdir()
  for sfx, v in (("v1rep5", 60.0), ("v1fs256", 70.0), ("v2pw", 75.0), ("v2cont", 80.0), ("v2cont_noguard", 78.0)):
    flag(v).to_csv(rep / f"n_subjects_benchmark_{sfx}.csv", index=False)
  for sfx, v, e in (("v1fs256", 0.12, 1), ("v2pw", 0.20, 3), ("v2cont", 0.20, 3), ("v2cont_noguard", 0.15, 2)):
    conn(v, e).to_csv(rep / f"connectivity_cohort_summary_{sfx}.csv", index=False)
  assert cmp.main(["--baselines-dir", str(tmp_path / "baselines"), "--reports-dir", str(rep)]) == 0
  f = pd.read_csv(rep / "v1_vs_v2/flagship.csv")
  r = f[(f.subject == "S01") & (f.window == "1.0s")].iloc[0]
  assert (r.d_fs, r.d_build, r.d_filter_mode, r.d_guard, r.d_total) == (10.0, 5.0, 5.0, 2.0, 20.0)
  c = pd.read_csv(rep / "v1_vs_v2/connectivity.csv").iloc[0]
  assert c.d_obs_diff_filter_mode == "not applicable (same input)"
  assert c.d_n_edges_sig_fdr_filter_mode == "not applicable (same input)"
  assert c.d_obs_diff_guard == pytest.approx(0.05) and c.d_n_edges_sig_fdr_guard == 1
  assert c.d_obs_diff_build == pytest.approx(0.08)      # b - a' (round 1 fix 3), not b - a
  assert c.d_obs_diff_fs == pytest.approx(0.02)
  assert "same input" in (rep / "v1_vs_v2/v1_vs_v2.md").read_text()


# ---------------------------------------------------------------- round 1 fixes

@pytest.mark.parametrize("jitter", [8, -8, 3])
def test_cv_groups_pair_a_jittered_cue_window_with_the_201_window_it_overlaps_most(tmp_path, jitter):
  S.write_built_subject(tmp_path, "S01", n_trials=10, seed=5, cue_jitter=jitter)
  d = SD.load_subject(tmp_path / "S01", conditions=(101, 102, 103, 104, 105, 201, 202))
  y, ids, grp, st = d["y"], d["trial_ids"], d["cv_groups"], d["window_starts"]
  for i in np.flatnonzero(y == 202):
    c = np.flatnonzero(y == 201)
    ov = np.minimum(st[c], st[i]) + FS - np.maximum(st[c], st[i])        # overlap by hand
    best = c[int(np.argmax(ov))]
    assert ov.max() == FS - abs(jitter) and st[i] != st[best]            # not an exact-start twin
    assert grp[i] == ids[best] == grp[best]
  assert not set(grp[np.isin(y, STIM)]) & set(grp[~np.isin(y, STIM)])


def test_r5_per_script_gate_needs_explicit_thresholds_and_fail_fraction(built, legacy):
  th = GATE["thresholds"]
  with pytest.raises(ValueError):
    SD.load_subject(legacy / "S03")                                         # legacy: the gate always runs
  with pytest.raises(ValueError):
    SD.load_subject(legacy / "S03", thresholds=th)
  with pytest.raises(ValueError):
    SD.load_subject(legacy / "S03", channel_fail_fraction=0.5)
  with pytest.raises(ValueError):
    SD.load_subject(built / "S01", quality_mode="per-script")
  with pytest.raises(ValueError):
    SD.load_subject(built / "S01", quality_mode="per-script", thresholds=th)
  SD.load_subject(built / "S01", quality_mode="per-script", **GATE)          # explicit: fine
  SD.load_subject(built / "S01", quality_mode="shared")                       # shared decisions need neither
  SD.load_subject(built / "S01", quality_mode="shared-no-guard")


def _frames(vals):
  return pd.DataFrame({"Subject": ["S01", "Mean"], "1.0s Acc (%)": [vals[0]] * 2, "1.0s SD": [1.0] * 2,
                       "2.0s Smoothed (%)": [vals[1]] * 2, "2.0s SD": [1.0] * 2})


def test_compare_v1_v2_decomposition_arithmetic_with_a_prime_and_a_prime_t(tmp_path):
  base = tmp_path / "baselines/v1_2026-01-01/reports"
  base.mkdir(parents=True)
  _frames((50.0, 60.0)).to_csv(base / "n_subjects_benchmark.csv", index=False)
  rep = tmp_path / "reports"
  rep.mkdir()
  # (1.0 s, 2.0 s) per variant
  for sfx, v in (("v1rep5", (50.0, 60.0)), ("v1fs256", (70.0, 75.0)), ("v1fs256trial", (70.0, 78.0)),
                 ("v2pw", (74.0, 83.0)), ("v2cont", (80.0, 90.0)), ("v2cont_noguard", (77.0, 86.0))):
    _frames(v).to_csv(rep / f"n_subjects_benchmark_{sfx}.csv", index=False)
  assert cmp.main(["--baselines-dir", str(tmp_path / "baselines"), "--reports-dir", str(rep)]) == 0
  f = pd.read_csv(rep / "v1_vs_v2/flagship.csv").set_index(["subject", "window"])
  r1, r2 = f.loc[("S01", "1.0s")], f.loc[("S01", "2.0s")]
  assert (r1.d_fs, r1.d_build, r1.d_filter_mode, r1.d_guard, r1.d_total) == (20.0, 4.0, 6.0, 3.0, 30.0)
  assert pd.isna(r1.d_smoothing)
  # 2.0 s: smoothing rule separated: a' -> a't = +3, build is b - a't = +5 (not b - a' = +8)
  assert (r2.d_fs, r2.d_smoothing, r2.d_build, r2.d_filter_mode, r2.d_guard, r2.d_total) == (15.0, 3.0, 5.0, 7.0, 4.0, 30.0)
  assert r2.d_fs + r2.d_smoothing + r2.d_build + r2.d_filter_mode == r2.d_total      # the steps add up to c - a
  assert r1.d_fs + r1.d_build + r1.d_filter_mode == r1.d_total


def _regression_tree(tmp_path, change=None, bytes_only=False):
  base = tmp_path / "baselines/v1_2026-01-01/reports"
  rep = tmp_path / "reports"
  (base / "connectivity_edges").mkdir(parents=True)
  (rep / "connectivity_edges_v1check").mkdir(parents=True)
  flag = "Subject,Clean Windows,1.0s Acc (%),2.0s Smoothed (%)\nS01,100,61.0,67.5\nMean,,61.0,67.5\n"
  summ = "subject,method,condition,frequency_hz,obs_diff,n_edges_sig_fdr\nS01,coherence,101,24.0,0.1,3\n"
  det = "subject,method,fs\nS01,coherence,250.0\n"
  alpha = "subject,method,mean_difference\nS01,coherence,0.05\n"
  for name, txt in (("n_subjects_benchmark", flag), ("connectivity_cohort_summary", summ),
                    ("connectivity_cohort_summary_details", det), ("connectivity_alpha_diagnostic", alpha)):
    (base / f"{name}.csv").write_text(txt)
    new = name.replace("_details", "_v1check_details") if name.endswith("_details") else f"{name}_v1check"
    t = txt
    if change and change[0] == name:
      t = t.replace(*change[1:])
    if bytes_only and name == "n_subjects_benchmark":
      t = t.replace("\n", "\r\n")                                         # same values, different bytes
    (rep / f"{new}.csv").write_text(t)
  np.savez(base / "connectivity_edges/S01_coherence.npz", a=np.arange(6.0))
  np.savez(rep / "connectivity_edges_v1check/S01_coherence.npz", a=np.arange(6.0))
  return tmp_path


def _check(tmp_path, capsys):
  rc = cmp.main(["--baselines-dir", str(tmp_path / "baselines"), "--reports-dir", str(tmp_path / "reports"),
                 "--check-regression"])
  return rc, capsys.readouterr().out


def test_check_regression_passes_when_identical(tmp_path, capsys):
  rc, out = _check(_regression_tree(tmp_path), capsys)
  assert rc == 0 and out.count("byte-equal") == 4 and "1/1 npz" in out


@pytest.mark.parametrize("name,old,new", [
  ("n_subjects_benchmark", "61.0,67.5\nMean", "61.0,67.51\nMean"),                       # one 0.01 value
  ("connectivity_cohort_summary", "0.1,3", "0.1,4"),
  ("connectivity_cohort_summary_details", "250.0", "256.0"),
  ("connectivity_alpha_diagnostic", "0.05", "0.06")])
def test_check_regression_flags_one_planted_value_in_each_compared_file(tmp_path, capsys, name, old, new):
  rc, out = _check(_regression_tree(tmp_path, (name, old, new)), capsys)
  assert rc == 1 and "different" in out


def test_check_regression_flags_one_changed_edge_array_and_a_missing_file(tmp_path, capsys):
  t = _regression_tree(tmp_path)
  np.savez(t / "reports/connectivity_edges_v1check/S01_coherence.npz", a=np.array([0, 1, 2, 3, 4, 5.5]))
  rc, out = _check(t, capsys)
  assert rc == 1 and "0/1 npz" in out
  t2 = _regression_tree(tmp_path / "b")
  (t2 / "reports/connectivity_alpha_diagnostic_v1check.csv").unlink()
  assert _check(t2, capsys)[0] == 1


def test_check_regression_distinguishes_value_equal_from_byte_equal(tmp_path, capsys):
  rc, out = _check(_regression_tree(tmp_path, bytes_only=True), capsys)
  assert rc == 0 and "value-equal only" in out and out.count("byte-equal") == 3


# ---------------------------------------------------------------- round 2: NaN-aware npz comparison

def _npz_case(tmp_path, old, new):
  t = _regression_tree(tmp_path)
  np.savez(t / "baselines/v1_2026-01-01/reports/connectivity_edges/S01_coherence.npz", **old)
  np.savez(t / "reports/connectivity_edges_v1check/S01_coherence.npz", **new)
  return t


def _nan_matrix():
  m = np.arange(16.0).reshape(4, 4)
  np.fill_diagonal(m, np.nan)                       # the diagonal of a connectivity matrix
  return m


def test_check_regression_npz_with_aligned_nan_diagonals_is_equal(tmp_path, capsys):
  rc, out = _check(_npz_case(tmp_path, {"stim": _nan_matrix(), "p": np.ones(3)},
                             {"stim": _nan_matrix(), "p": np.ones(3)}), capsys)
  assert rc == 0 and "1/1 npz" in out


@pytest.mark.parametrize("label,new", [
  ("nan_vs_number", {"stim": np.where(np.isnan(_nan_matrix()), 0.0, _nan_matrix())}),
  ("number_vs_nan", {"stim": np.where(np.arange(16).reshape(4, 4) == 6, np.nan, _nan_matrix())}),
  ("one_value", {"stim": np.where(np.arange(16).reshape(4, 4) == 6, 6.5, _nan_matrix())}),
  ("tiny_difference", {"stim": np.where(np.arange(16).reshape(4, 4) == 6, 6.0 + 1e-12, _nan_matrix())}),
  ("shape", {"stim": np.full((2, 8), np.nan)}),
  ("dtype", {"stim": _nan_matrix().astype(np.float32)}),
  ("extra_key", {"stim": _nan_matrix(), "extra": np.ones(1)}),
  ("missing_key", {})])
def test_check_regression_npz_mismatches_exit_1(tmp_path, capsys, label, new):
  rc, out = _check(_npz_case(tmp_path, {"stim": _nan_matrix()}, new), capsys)
  assert rc == 1 and "0/1 npz" in out, label


def test_check_regression_npz_all_nan_arrays_of_different_shape_are_different(tmp_path, capsys):
  rc, _ = _check(_npz_case(tmp_path, {"a": np.full((3, 3), np.nan)}, {"a": np.full((3, 4), np.nan)}), capsys)
  assert rc == 1                                    # equal_nan alone would broadcast-compare: the shape must be checked
