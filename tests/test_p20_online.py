"""P20 data-signal tests: dynamic stopping (plan test 6), the causal filter (7) and the pseudo-online clock, scoring and
CLI (8), all on synthetic data built inside the tests (tiny fake recordings, never a real file)."""

import numpy as np
import pandas as pd
import pytest
from scipy.signal import sosfilt, sosfilt_zi, sosfiltfilt

from scripts.benchmarks import benchmark_window_sweep as WS
from scripts.benchmarks import pseudo_online as P
from scripts.benchmarks import simulate_dynamic_stopping as DS
from src.online import causal_filter as CF
from tests import p16_synth as S

CLASSES = [101, 102, 103, 104, 105]
# windows of one trial of 0.5 s, GIVEN OUT OF ORDER. In time order (offset, probabilities):
#   0.00 (before the skip, a trap: 0.9 on class 105), 0.50 [.4 .3 .1 .1 .1], 0.75 [.6 .2 .1 .05 .05],
#   1.00 [.9 .05 .02 .02 .01]
TRIAL = {0.75: [.6, .2, .1, .05, .05], 1.00: [.9, .05, .02, .02, .01], 0.00: [.025, .025, .025, .025, .9],
         0.50: [.4, .3, .1, .1, .1]}


def _trial_frame(subject="S01", method="lda", run=0, trial_id=7, true=101, window=0.5, trial=TRIAL):
  rows = [{"subject": subject, "window_sec": window, "method": method, "run": run, "trial_id": trial_id,
           "offset_sec": o, "true": true, "pred": 0, **{f"p_{c}": p for c, p in zip(CLASSES, ps)}}
          for o, ps in trial.items()]
  return pd.DataFrame(rows)


# --- P20.5 dynamic stopping (plan test 6) ------------------------------------------------

def test_dynamic_stopping_known_decisions_with_out_of_order_windows():
  """Cumulative means after the skip (0.5): 0.4, 0.5, 0.6333 (class 101). Known answer (hand arithmetic):
  threshold 0.5 -> decided at the 0.75 window, time 0.75 + 0.5 = 1.25, not forced; 0.6 -> at 1.0, time 1.5;
  0.7 / 0.95 -> forced at the last window, time 1.5, pred 101. The windows arrive unsorted and the offset-0 window
  (class 105 at 0.9) lies before the skip: ignoring the sort or the skip changes the answer (R8)."""
  df = _trial_frame()
  dec, skipped = DS.simulate(df, [0.5, 0.6, 0.7, 0.95], 0.5)
  assert len(skipped) == 0
  got = {r.threshold: (r.pred, r.time_sec, r.forced) for r in dec.itertuples()}
  assert got == {0.5: (101, 1.25, 0), 0.6: (101, 1.5, 0), 0.7: (101, 1.5, 1), 0.95: (101, 1.5, 1)}
  rev = DS.simulate(df.iloc[::-1], [0.5, 0.6, 0.7, 0.95], 0.5)[0]
  assert rev.equals(dec)                                              # the input order is irrelevant
  p = df[[f"p_{c}" for c in CLASSES]].to_numpy()                      # file order = 0.75, 1.0, 0.0, 0.5
  buggy = DS.decide_trial(p, np.arange(4.0), 0.5, [0.5], 0.0, CLASSES)[0]      # offsets ignored (file order): other time
  assert (buggy["time_sec"], buggy["pred"]) != (1.25, 101)
  noskip = DS.decide_trial(p, df["offset_sec"].to_numpy(), 0.5, [0.5], 0.0, CLASSES)[0]   # skip 0 keeps the trap window
  assert (noskip["time_sec"], noskip["pred"]) != (1.25, 101)


def test_dynamic_stopping_groups_by_subject_run_and_trial_and_summarises(tmp_path, capsys):
  """Two subjects share trial id 7; S01 has two runs; fbcca rows without probabilities are skipped. Known answer: S01
  decides correctly in both runs, S02's trial (true 101, probabilities favour 102) is wrong; at threshold 0.7 all are
  forced, mean time 1.5 s, ITR(S01) = log2(5) * 60 / 2.0; cohort accuracy = mean over subjects = 50 %."""
  wrong = {o: [pp[1], pp[0], *pp[2:]] for o, pp in TRIAL.items()}      # swap 101/102 -> class 102 wins
  frames = [_trial_frame("S01", run=0), _trial_frame("S01", run=1), _trial_frame("S02", true=101, trial=wrong)]
  fb = _trial_frame("S01", method="fbcca")
  fb[[f"p_{c}" for c in CLASSES]] = np.nan
  path = tmp_path / "predictions.csv"
  pd.concat(frames + [fb]).to_csv(path, index=False)
  rc = DS.main([str(path), "--thresholds", "0.5", "0.7", "--skip-sec", "0.5", "--out-dir", str(tmp_path / "ds")])
  assert rc == 0 and "Skipping method 'fbcca'" in capsys.readouterr().out
  out = tmp_path / "ds"
  dec = pd.read_csv(out / "decisions.csv")
  assert list(dec.columns) == DS.DECISION_COLUMNS and set(dec["method"]) == {"lda"} and len(dec) == 3 * 2
  ps = pd.read_csv(out / "per_subject.csv")
  r = ps[(ps["Subject"] == "S01") & (ps["Threshold"] == 0.7)].iloc[0]
  assert (r["Trials"], r["Runs"], r["Acc (%)"], r["Mean Time (s)"], r["Forced (%)"]) == (2, 2, 100.0, 1.5, 100.0)
  assert r["ITR (bits/min)"] == pytest.approx(np.log2(5) * 60 / 2.0)
  assert ps[ps["Subject"] == "S02"]["Acc (%)"].eq(0.0).all()
  co = pd.read_csv(out / "cohort.csv")
  assert list(co.columns) == DS.COHORT_COLUMNS and (out / "best_threshold.csv").is_file()
  assert co.groupby(["Method", "Window (s)"])["Best (ITR)"].sum().eq(1).all()
  assert co[co["Threshold"] == 0.7]["Acc (%)"].iloc[0] == pytest.approx(50.0)


def test_dynamic_stopping_itr_matches_sweep_and_offsets_in_samples_fail_loudly():
  """ITR equals the sweep's helper on a grid; offsets stored in samples (64, 128 ...) are refused, not mis-scaled."""
  for acc in (0.2, 0.35, 0.8, 1.0):
    assert DS.itr_bits_per_min(acc, 5, 1.5) == pytest.approx(WS.itr_bits_per_min(acc, 5, 1.5), abs=1e-12)
  bad = _trial_frame(trial={64.0: TRIAL[0.5], 128.0: TRIAL[0.75]})
  with pytest.raises(ValueError, match="samples"):
    DS.simulate(bad, [0.6], 0.5)


# --- P20.6 causal filter (plan test 7) ---------------------------------------------------

FS = 256.0
SOS = CF.design_sos(FS, 1.0, 90.0, 4, 60.0, 30.0)


def test_causal_filter_chunked_equals_one_pass_and_is_causal():
  """CAUSAL-FILTER TEST (PF-38). Known answers: (a) feeding the stream in irregular chunks through the stateful
  filter equals one `sosfilt` with `zi = sosfilt_zi * x[0]` over the whole stream, max |diff| <= 1e-10; (b) an impulse at
  t0 leaves every output sample before t0 equal to the output without the impulse (an output depends on the past only);
  (c) `zi = sosfilt_zi * x[0]` removes the start-up transient of a constant offset, zero state does not; (d) the
  zero-phase `sosfiltfilt` is NOT causal (it responds before the impulse), i.e. (b) fails on that historical path."""
  rng = np.random.default_rng(0)
  x = rng.normal(0, 5, (3, 4000)) + np.array([[300.0], [-120.0], [0.0]])
  one = sosfilt(SOS, x, axis=-1, zi=sosfilt_zi(SOS)[:, None, :] * x[:, 0][None, :, None])[0]
  flt = CF.CausalSOSFilter(SOS, 3)
  cuts = [0, 1, 7, 64, 65, 1000, 1001, 3999, 4000]
  y = np.concatenate([flt.process(x[:, a:b]) for a, b in zip(cuts[:-1], cuts[1:])], axis=1)
  assert np.abs(y - one).max() <= 1e-10
  assert np.abs(CF.filter_causal(x, SOS) - one).max() <= 1e-10 and flt.n_seen == 4000
  t0 = 2000                                                          # (b) impulse causality
  imp = x.copy()
  imp[:, t0] += 500.0
  d = CF.filter_causal(imp, SOS) - CF.filter_causal(x, SOS)
  assert np.abs(d[:, :t0]).max() <= 1e-10 and np.abs(d[:, t0:t0 + 5]).max() > 1.0
  dz = sosfiltfilt(SOS, imp, axis=-1) - sosfiltfilt(SOS, x, axis=-1)  # (d) the zero-phase path leaks the future
  assert np.abs(dz[:, :t0 - 10]).max() > 1e-8
  const = np.full((1, 600), 1000.0)                                  # (c) start-up
  assert np.abs(CF.filter_causal(const, SOS)).max() < 1e-6
  assert np.abs(sosfilt(SOS, const, axis=-1)).max() > 100.0


def test_replay_windows_fixed_clock_and_chunk_independent():
  """Window k = samples [k*stride, k*stride + n) of the causal-filtered stream, whatever the chunk size; the raw
  windows are cut from the same samples; the number of windows is (T - n)//stride + 1."""
  rng = np.random.default_rng(1)
  x = rng.normal(0, 5, (2, 1500))
  ref = CF.filter_causal(x, SOS)
  for chunk in (64, 37, 500):
    st, wf, wr = CF.replay_windows(x, SOS, 128, 64, chunk)
    assert np.array_equal(st, np.arange(len(st)) * 64) and len(st) == (1500 - 128) // 64 + 1
    for k in (0, 5, len(st) - 1):
      assert np.abs(wf[k] - ref[:, st[k]:st[k] + 128]).max() <= 1e-10
      assert np.array_equal(wr[k], x[:, st[k]:st[k] + 128])


# --- P20.6 pseudo-online clock and decisions (plan test 8) -------------------------------------

def _stream_probas(mark, fs, starts, n_win, rest_trap=None):
  """Planted probabilities: windows fully inside a target period -> 0.9 on its class; windows STARTING before the onset
  but overlapping it -> 0.9 on class 101 (trap); everything else uniform 0.2. `rest_trap` = onset sample whose rest
  period gets 0.9 on class 102 in its windows."""
  p = np.full((len(starts), 5), 0.2)
  L = int(5 * fs)
  for ci, code in enumerate(P.TARGETS):
    for o in P.event_onsets(mark, code):
      for k, s in enumerate(starts):
        if o <= s and s + n_win <= o + L:
          p[k] = 0.025
          p[k, ci] = 0.9
        elif s < o < s + n_win:
          p[k] = [0.9, 0.025, 0.025, 0.025, 0.025]
        if rest_trap is not None and o == rest_trap and o - L <= s and s + n_win <= o:
          p[k] = [0.025, 0.9, 0.025, 0.025, 0.025]
  return p


def test_pseudo_online_fixed_clock_and_decisions_in_the_right_periods():
  """Synthetic 256 Hz stream with a known MARK (10 trials, targets at 10, 25, 40 ... s). Known answers: window starts are
  exactly k*64 (the fixed clock, independent of the MARK); every stimulus period is decided correctly at time
  0.5 + 0.5 = 1.0 s (first window with start >= onset + skip, cumulative mean 0.9 >= 0.6); the traps (windows that start
  before the onset) never enter, a rest period with planted class-102 probabilities is the only false activation; with
  uniform probabilities 5 classes force the decision at the last window (time 5.0, forced) and 6 classes give 'no target'."""
  block = S.make_block(n_trials=10, seed=3)
  mark, fs, n_win = block[10], 256.0, 128
  clock, _, _ = CF.replay_windows(block[:8], SOS, n_win, 64)
  starts = np.arange(0, (block.shape[1] - n_win) // 64 + 1) * 64
  assert np.array_equal(clock, starts)
  onsets = {int(o): code for code in P.TARGETS for o in P.event_onsets(mark, code)}
  trap_onset = sorted(onsets)[3]
  proba = _stream_probas(mark, fs, starts, n_win, rest_trap=trap_onset)
  valid = np.ones(len(starts), bool)
  dec = P.score_stream(mark, fs, starts, proba, valid, n_win, 0.5, 0.5, 0.6, 5, 30.0, "S99")
  st, rs = dec[dec["period"] == "stimulus"], dec[dec["period"] == "rest"]
  assert len(st) == 10 and len(rs) == 10
  assert sorted(st["onset_sec"] * fs) == sorted(onsets) and (st["correct"] == 1).all()
  assert (st["time_sec"] == 1.0).all() and (st["forced"] == 0).all()
  assert [int(t) for t in st.sort_values("onset_sec")["true"]] == [onsets[o] for o in sorted(onsets)]
  hit = rs[rs["false_activation"] == 1]
  assert len(hit) == 1 and hit["onset_sec"].iloc[0] * fs == trap_onset - 5 * fs
  assert np.allclose(rs.sort_values("onset_sec")["onset_sec"].to_numpy() + 5,
                     st.sort_values("onset_sec")["onset_sec"].to_numpy())      # each rest period ends at its onset
  uni5 = np.full((len(starts), 5), 0.2)                                         # uniform: forced / no target
  d5 = P.score_stream(mark, fs, starts, uni5, valid, n_win, 0.5, 0.5, 0.6, 5, 30.0)
  s5 = d5[d5["period"] == "stimulus"]
  assert (s5["forced"] == 1).all() and (s5["time_sec"] == 5.0).all() and (s5["missed"] == 0).all()
  d6 = P.score_stream(mark, fs, starts, np.full((len(starts), 6), 1 / 6), valid, n_win, 0.5, 0.5, 0.6, 6, 30.0)
  s6 = d6[d6["period"] == "stimulus"]
  assert (s6["missed"] == 1).all() and (s6["pred"] == 0).all() and (s6["correct"] == 0).all()
  first = sorted(onsets)[0]                                                     # rejected windows are skipped
  bad = valid & ~((starts >= first) & (starts < first + 5 * fs))
  dr = P.score_stream(mark, fs, starts, proba, bad, n_win, 0.5, 0.5, 0.6, 5, 30.0)
  r0 = dr[(dr["period"] == "stimulus") & (dr["onset_sec"] * fs == first)].iloc[0]
  assert r0["n_rejected"] == r0["n_windows"] > 0 and r0["pred"] == 0 and r0["missed"] == 0
  summ = P.summarize(dr, "S99", False, {"window_sec": 0.5, "channels_kept": 8, "dropped_at_check": 0, "train_windows": 1,
                                        "val_acc": 1.0, "fallback": False, "source": "x"})
  assert summ["Trials"] == 9 and summ["Trials undecided"] == 1 and summ["Windows rejected (%)"] > 0


def test_pseudo_online_cli_mark_only_for_scoring_channel_check_and_paradigm(tmp_path, monkeypatch, capsys):
  """End to end on fake recordings (tiny network, CPU). Known answers: (a) predictions are identical when the test run's
  MARK is erased (the MARK is read only after the probabilities exist); (b) a channel that is bad only in the test
  stream is dropped by the label-free check: `Dropped at check` 1, `Channels kept` 7; (c) OO -> C prints the PF-39
  warning, OO -> mOO does not; summaries carry the columns of 02_REQUIREMENTS section 6."""
  raw = tmp_path / "raw"
  blk = S.make_block(n_trials=10, seed=2)
  nomark = blk.copy()
  nomark[10] = 0.0
  for sub, test_block in (("S01", blk), ("S02", nomark), ("S03", S.make_block(n_trials=10, seed=2, bad_channel="O2"))):
    S.write_ebr(raw / sub / "OO.ebr", S.make_block(n_trials=10, seed=1))
    S.write_ebr(raw / sub / "mOO.ebr", test_block)
  S.write_ebr(raw / "S01" / "C.ebr", blk)
  seen = {}
  orig = P.score_stream

  def spy(mark, fs, starts, proba, valid, *a, **k):
    seen[a[-1]] = (np.array(proba), np.array(valid), float(np.abs(mark).sum()))
    return orig(mark, fs, starts, proba, valid, *a, **k)

  monkeypatch.setattr(P, "score_stream", spy)
  common = ["--raw-dir", str(raw), "--window-sec", "1", "--max-epochs", "3", "--device", "cpu", "--out-dir",
            str(tmp_path / "o")]
  assert P.main(["--subjects", "S01", "S02", "S03", *common]) == 0
  assert "PF-39" not in capsys.readouterr().out
  assert seen["S01"][2] > 0 and seen["S02"][2] == 0                     # the S02 test MARK is erased
  assert np.array_equal(seen["S01"][0], seen["S02"][0], equal_nan=True) and np.array_equal(seen["S01"][1], seen["S02"][1])
  summ = pd.read_csv(tmp_path / "o" / "summary_ccnn_5class.csv").set_index("Subject")
  assert summ.loc["S01", "Dropped at check"] == 0 and summ.loc["S01", "Channels kept"] == 8
  assert summ.loc["S03", "Dropped at check"] == 1 and summ.loc["S03", "Channels kept"] == 7
  assert list(summ.columns[:3]) == P.SUMMARY_BASE[1:] and "Forced (%)" in summ.columns and "Mean" in summ.index
  assert (tmp_path / "o" / "decisions_ccnn_5class.csv").is_file() and not list((tmp_path / "o").glob("*part*"))
  P.main(["--subjects", "S01", "--test-session", "C", *common, "--tag", "c"])
  assert "PF-39" in capsys.readouterr().out
  assert P.paradigm_warning("OO", "mOO") is None and P.paradigm_warning("mOO", "mC") is not None
  assert P.paradigm_warning("OO", "online_OO") is None and P.paradigm_warning("OO", "foo") is None


def test_pseudo_online_channel_check_uses_only_the_first_seconds():
  """The check reads windows that END inside the first 30 s: a channel bad only after 30 s is kept, one bad inside is
  dropped. Known answer on planted windows (no labels exist in this function)."""
  q = {"vpp_min": 5.0, "vpp_max": 120.0, "std_min": 1.0, "std_max": 35.0, "channel_fail_fraction": 0.5, "source": "both"}
  rng = np.random.default_rng(2)
  n, n_win, fs = 200, 128, 256.0
  starts = np.arange(n) * 64
  W = rng.normal(0, 5, (n, 3, n_win))
  late = starts + n_win > 30 * fs
  W[late, 1] = rng.normal(0, 80, (late.sum(), n_win))              # channel 1 bad only after 30 s
  W[~late, 2] = rng.normal(0, 80, ((~late).sum(), n_win))          # channel 2 bad inside the first 30 s
  assert P.check_channels(W, W, starts, n_win, fs, ["a", "b", "c"], q, 30.0) == {"c"}


# --- P24 fix round 2: determinism of the pseudo-online training path ----------------------

def _det_raw(tmp_path):
  raw = tmp_path / "raw"
  S.write_ebr(raw / "S01" / "OO.ebr", S.make_block(n_trials=10, seed=1))
  S.write_ebr(raw / "S01" / "mOO.ebr", S.make_block(n_trials=10, seed=2))
  return raw


def _det_run(tmp_path, raw, device, name, monkeypatch, extra=()):
  seen = {}
  orig = P.score_stream

  def spy(mark, fs, starts, proba, valid, *a, **k):
    seen["proba"] = np.array(proba)
    return orig(mark, fs, starts, proba, valid, *a, **k)

  monkeypatch.setattr(P, "score_stream", spy)
  out = tmp_path / name
  assert P.main(["--subjects", "S01", "--raw-dir", str(raw), "--window-sec", "1", "--max-epochs", "4", "--device",
                 device, "--seed", "42", "--out-dir", str(out), *extra]) == 0
  return seen["proba"], pd.read_csv(out / "decisions_ccnn_5class.csv"), pd.read_csv(out / "summary_ccnn_5class.csv")


def test_pseudo_online_same_seed_gives_identical_probabilities_and_decisions_cpu(tmp_path, monkeypatch):
  """Known answer: two runs with seed 42 on the same fake recordings give bit-identical stream probabilities, decisions
  and summary (CPU; this case also passes without the cudnn flags, the CPU kernels used here are deterministic)."""
  raw = _det_raw(tmp_path)
  p1, d1, s1 = _det_run(tmp_path, raw, "cpu", "a", monkeypatch)
  p2, d2, s2 = _det_run(tmp_path, raw, "cpu", "b", monkeypatch)
  assert np.array_equal(p1, p2, equal_nan=True)
  pd.testing.assert_frame_equal(d1, d2)
  pd.testing.assert_frame_equal(s1.drop(columns="Seconds"), s2.drop(columns="Seconds"))


def test_pseudo_online_sets_cudnn_determinism_when_device_is_cuda(tmp_path, monkeypatch):
  """`main` sets `cudnn.deterministic = True` and `cudnn.benchmark = False` before training on CUDA, as every other
  network script does (P24 verify: the 6-class summary changed between two CUDA runs with seed 42). Device resolution
  and training are stubbed, so this runs without a GPU; it FAILS on the code before the fix (flags left untouched).
  On CPU the flags are not touched."""
  import torch
  raw = _det_raw(tmp_path)
  seen = []

  def fake_subject(subject, args, cfg, q, raw_dir, device, sos_of):
    seen.append((device, torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark))
    raise ValueError("stub: no training")

  monkeypatch.setattr(torch.backends.cudnn, "deterministic", False)
  monkeypatch.setattr(torch.backends.cudnn, "benchmark", True)
  monkeypatch.setattr(P, "run_subject", fake_subject)
  monkeypatch.setattr(P, "resolve_device", lambda name: name)
  P.main(["--subjects", "S01", "--raw-dir", str(raw), "--device", "cpu", "--out-dir", str(tmp_path / "c")])
  P.main(["--subjects", "S01", "--raw-dir", str(raw), "--device", "cuda", "--out-dir", str(tmp_path / "g")])
  assert seen == [("cpu", False, True), ("cuda", True, False)]


@pytest.mark.skipif(not __import__("torch").cuda.is_available(), reason="CUDA not available")
def test_pseudo_online_same_seed_gives_identical_probabilities_cuda(tmp_path, monkeypatch):
  """Known answer on CUDA: two runs with seed 42 give bit-identical probabilities and decisions (needs the flags)."""
  import torch
  monkeypatch.setattr(torch.backends.cudnn, "deterministic", False)
  monkeypatch.setattr(torch.backends.cudnn, "benchmark", False)
  raw = _det_raw(tmp_path)
  extra = ["--max-epochs", "15", "--patience", "15"]
  p1, d1, _ = _det_run(tmp_path, raw, "cuda", "a", monkeypatch, extra)
  p2, d2, _ = _det_run(tmp_path, raw, "cuda", "b", monkeypatch, extra)
  assert np.array_equal(p1, p2, equal_nan=True)
  pd.testing.assert_frame_equal(d1, d2)
