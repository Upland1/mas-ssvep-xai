"""P20 independent known-answer tests (synthetic-tester; the builders' own tests are not reused).

(a) end to end on a synthetic built folder: window sweep predictions.csv -> simulate_dynamic_stopping (seconds,
    (trial, offset) order, decision time = offset + window, forced flag, ITR T = time + 0.5 s); NN sweep `compact` equals the
    window-sweep `cnn (compact_eegnet)` at the same seeds;
(b) R1 / PF-32: no trial on both sides of a fold, validation trials inside the training trials, normalisation statistics
    from the fitting windows only (a test-only perturbation leaves the training and the other predictions unchanged);
(c) vectorized FBCCA against an independent CCA (principal angles), Wolpaw ITR;
(d) pseudo-online causality: future samples, chunk size, MARK erasure, the rest class never decides;
(e) CCNN spectral input: bin of a planted tone, [real | imag] / T scaling, nfft.
"""

import numpy as np
import pandas as pd
import pytest
import torch
from scipy.linalg import subspace_angles
from scipy.signal import sosfilt, sosfilt_zi

from tests import p16_synth as S

FS = 256.0


# ---------------------------------------------------------------- helpers

def itr_ref(p, n, t):
  """Wolpaw, written out independently."""
  if p <= 1.0 / n:
    return 0.0
  bits = np.log2(n) if p >= 1.0 else np.log2(n) + p * np.log2(p) + (1 - p) * np.log2((1 - p) / (n - 1))
  return bits * 60.0 / t


@pytest.fixture(scope="module")
def built(tmp_path_factory):
  root = tmp_path_factory.mktemp("built")
  S.write_built_subject(root / "w1_s0.25", "S01", n_trials=20)
  return root


@pytest.fixture(scope="module")
def sweep_out(built, tmp_path_factory):
  from scripts.benchmarks import benchmark_window_sweep as W
  out = tmp_path_factory.mktemp("sweep")
  rc = W.main(["--data-root", str(built), "--windows", "1", "--methods", "fbcca", "lda", "cnn", "--cv-repeats", "2",
               "--cnn-repeats", "1", "--max-epochs", "2", "--device", "cpu", "--out-dir", str(out)])
  assert rc == 0
  return out


@pytest.fixture(scope="module")
def loaded(built):
  from src.io.subject_data import load_subject
  return load_subject(built / "w1_s0.25" / "S01", quality_mode="shared", bands=("fbcca", "fbcsp"))


# ---------------------------------------------------------------- (a) cross-module contracts

def test_sweep_predictions_are_in_seconds_and_cover_each_window_once_per_run(sweep_out, loaded):
  pr = pd.read_csv(sweep_out / "predictions.csv")
  assert set(np.round(pr["offset_sec"], 6)) == set(np.round(np.unique(loaded["offsets"]) / FS, 6)) == {0, 1, 2, 3, 4}
  assert (pr["offset_sec"] + pr["window_sec"] <= 5.0 + 1e-9).all()
  for (m, r), g in pr.groupby(["method", "run"]):
    assert len(g) == len(loaded["y"]) and not g.duplicated(["trial_id", "offset_sec"]).any()
  fb = pr[pr["method"] == "fbcca"]
  assert fb[[c for c in pr.columns if c.startswith("p_")]].isna().all().all()      # correlations, not probabilities
  for m in ("lda", "cnn (compact_eegnet)"):
    p = pr[pr["method"] == m][[c for c in pr.columns if c.startswith("p_")]].to_numpy()
    assert np.allclose(p.sum(1), 1.0, atol=1e-6)


def decide_ref(g, th, skip, win):
  """Independent re-implementation of the stopping rule on the rows of one trial."""
  g = g.sort_values("offset_sec")
  g = g[g["offset_sec"] >= skip - 1e-9]
  pc = [c for c in g.columns if c.startswith("p_")]
  P = g[pc].to_numpy()
  cm = np.cumsum(P, 0) / np.arange(1, len(P) + 1)[:, None]
  for k in range(len(P)):
    if cm[k].max() >= th - 1e-9:
      return int(pc[cm[k].argmax()][2:]), g["offset_sec"].iloc[k] + win, 0
  k = len(P) - 1
  return int(pc[cm[k].argmax()][2:]), g["offset_sec"].iloc[k] + win, 1


def test_end_to_end_sweep_to_dynamic_stopping_matches_independent_rule(sweep_out, tmp_path, capsys):
  from scripts.benchmarks import simulate_dynamic_stopping as D
  pr = pd.read_csv(sweep_out / "predictions.csv")
  shuffled = pr.sample(frac=1.0, random_state=3).reset_index(drop=True)          # (trial, offset) order must be rebuilt
  src = tmp_path / "pred.csv"
  shuffled.to_csv(src, index=False)
  ths = [0.3, 0.5, 0.6, 0.9, 0.95]
  assert D.main([str(src), "--thresholds", *map(str, ths), "--skip-sec", "0.5", "--out-dir", str(tmp_path / "o")]) == 0
  assert "fbcca" in capsys.readouterr().out
  dec = pd.read_csv(tmp_path / "o" / "decisions.csv")
  assert set(dec["method"]) == {"lda", "cnn (compact_eegnet)"}                    # fbcca skipped
  assert dec["time_sec"].between(1.5, 5.0).all()                                   # offset in 1..4 plus 1 s window
  n = 0
  for (m, run, tid), g in pr[pr["method"] != "fbcca"].groupby(["method", "run", "trial_id"]):
    for th in ths:
      row = dec[(dec["method"] == m) & (dec["run"] == run) & (dec["trial_id"] == tid) & (dec["threshold"] == th)]
      assert len(row) == 1
      pred, t, forced = decide_ref(g, th, 0.5, 1.0)
      assert (int(row["pred"].iloc[0]), row["time_sec"].iloc[0], int(row["forced"].iloc[0])) == (pred, t, forced)
      n += 1
  assert n == 3 * 20 * len(ths)                      # lda runs 0,1 and cnn run 0
  assert (dec["forced"] == 1).any() and (dec["forced"] == 0).any()
  ps = pd.read_csv(tmp_path / "o" / "per_subject.csv")
  for _, r in ps.iterrows():
    assert r["ITR (bits/min)"] == pytest.approx(itr_ref(r["Acc (%)"] / 100, 5, r["Mean Time (s)"] + 0.5), rel=1e-4, abs=1e-6)


def test_threshold_is_inclusive_forced_flag_and_time_rule():
  from scripts.benchmarks.simulate_dynamic_stopping import decide_trial
  cls = [101, 102]
  # window at offset 0.5 has max exactly 0.6 -> hit with ">=" (a ">" rule would wait for the next window)
  p = np.array([[0.6, 0.4], [0.9, 0.1], [0.9, 0.1]])
  o = np.array([0.5, 0.75, 1.0])
  r = decide_trial(p, o, 0.5, [0.6], 0.5, cls)[0]
  assert (r["pred"], r["time_sec"], r["forced"]) == (101, 1.0, 0)
  # never reached: forced at the last window, time = last offset + window
  r = decide_trial(np.array([[0.55, 0.45]] * 3), o, 0.5, [0.9], 0.5, cls)[0]
  assert (r["time_sec"], r["forced"]) == (1.5, 1)
  # windows given in reverse order, plus one before the skip
  p2 = np.array([[0.1, 0.9], [0.9, 0.1], [0.9, 0.1], [0.2, 0.8]])
  o2 = np.array([1.0, 0.5, 0.75, 0.25])
  r = decide_trial(p2, o2, 0.5, [0.8], 0.5, cls)[0]          # sorted: 0.5 (0.9/0.1) hits at once
  assert (r["pred"], r["time_sec"], r["forced"]) == (101, 1.0, 0)


def test_itr_wolpaw_values_across_modules():
  from scripts.benchmarks import benchmark_window_sweep as W
  from scripts.benchmarks import simulate_dynamic_stopping as D
  from scripts.benchmarks import pseudo_online as P
  from scripts.benchmarks.neural_networks import benchmark_nn_sweep as N
  assert itr_ref(0.8, 5, 2.0) == pytest.approx(36.0, abs=1e-3)                  # 1.2 bits x 30 per min
  for f in (W.itr_bits_per_min, D.itr_bits_per_min, P.itr_bits_per_min, N.itr_bits_per_min):
    assert f(1.0, 5, 1.5) == pytest.approx(np.log2(5) * 40)
    assert f(0.2, 5, 1.5) == 0.0 and f(0.05, 5, 1.5) == 0.0
    assert f(0.8, 5, 2.0) == pytest.approx(36.0, abs=1e-3)
    for acc in (0.21, 0.4, 0.6, 0.95, 0.999):
      assert f(acc, 5, 2.5) == pytest.approx(itr_ref(acc, 5, 2.5), rel=1e-12)
    assert f(0.6, 5, 1.5) > f(0.6, 5, 2.5) > 0                                     # longer T -> lower rate


def test_nn_sweep_compact_equals_window_sweep_cnn_at_identical_seeds(built, sweep_out, tmp_path):
  from scripts.benchmarks.neural_networks import benchmark_nn_sweep as N
  assert N.main(["--data-root", str(built), "--windows", "1", "--models", "compact", "--max-epochs", "2", "--device", "cpu",
                 "--out-dir", str(tmp_path)]) == 0
  a = pd.read_csv(tmp_path / "predictions.csv")
  b = pd.read_csv(sweep_out / "predictions.csv")
  b = b[b["method"] == "cnn (compact_eegnet)"]
  key = ["trial_id", "offset_sec"]
  m = a.merge(b, on=key, suffixes=("_nn", "_ws"))
  assert len(m) == len(a) == len(b)
  for c in [c for c in a.columns if c.startswith("p_")]:
    assert np.allclose(m[c + "_nn"], m[c + "_ws"], atol=1e-5), c
  assert (m["true_nn"] == m["true_ws"]).all()
  s = pd.read_csv(tmp_path / "summary.csv")
  assert list(s["Method"]) == ["compact_eegnet"]


# ---------------------------------------------------------------- (b) R1 / PF-32 / R2

def test_cnn_cv_never_puts_a_trial_in_train_and_test_and_validation_inside_training(loaded, monkeypatch):
  from scripts.benchmarks import benchmark_window_sweep as W
  from src.models.cnn import training as T
  X, g = loaded["X"], np.asarray(loaded["cv_groups"])
  row_of = {X[i].tobytes(): i for i in range(len(X))}
  calls = []

  def fake(X_tr, y_tr, groups_tr, X_te, fs, n_classes, **kw):
    te_rows = np.array([row_of[x.tobytes()] for x in X_te])
    calls.append((np.asarray(groups_tr), g[te_rows]))
    # the real validation split on these training trials
    fi, vi = T.split_validation(np.asarray(y_tr), np.asarray(groups_tr), 0.2, kw.get("seed", 42))
    calls[-1] += (np.asarray(groups_tr)[fi], np.asarray(groups_tr)[vi])
    return {"proba": np.full((len(X_te), n_classes), 1.0 / n_classes), "train_acc": 1.0, "val_acc": 1.0, "best_epoch": 1, "epochs_run": 1}

  monkeypatch.setattr(T, "cnn_fold", fake)
  args = W.build_parser().parse_args(["--cnn-repeats", "2"])
  W.run_cell(loaded, 1.0, W.CNN, args, "cpu", np.zeros((len(X), 5)))
  assert len(calls) == 10
  for gtr, gte, gfit, gval in calls:
    assert not set(gtr) & set(gte)
    assert set(gval) <= set(gtr) and not set(gval) & set(gte) and not set(gval) & set(gfit)
    assert len(set(gval)) >= 1 and len(set(gfit)) > len(set(gval))
    assert len(set(gtr) | set(gte)) == 20                                        # every trial is somewhere


def planted(n_trials=20, per=4, C=3, n=256, seed=0):
  rng = np.random.default_rng(seed)
  t = np.arange(n) / FS
  fr = [8.0, 10.0, 12.0, 15.0, 20.0]
  X, y, g = [], [], []
  for tr in range(n_trials):
    for _ in range(per):
      X.append(30 * np.sin(2 * np.pi * fr[tr % 5] * t + rng.uniform(0, 6.28))[None] + 5 * rng.standard_normal((C, n)) + 100)
      y.append(tr % 5)
      g.append(tr)
  return np.array(X), np.array(y), np.array(g)


def test_normalisation_statistics_come_from_fitting_windows_only(monkeypatch):
  from src.models.cnn import training as T
  X, y, g = planted()
  seen = []
  real = T.fit_stats
  monkeypatch.setattr(T, "fit_stats", lambda a: (seen.append(np.array(a)), real(a))[1])
  r = T.fit_network(X, y, g, T.model_factory("eegnet", FS), seed=1, max_epochs=1, augment=False)
  assert len(seen) == 1 and seen[0].shape[0] == len(r["fit_idx"]) < len(X)
  assert np.array_equal(seen[0], X[r["fit_idx"]])
  assert not set(g[r["fit_idx"]]) & set(g[r["val_idx"]])
  mean, std = real(X[r["fit_idx"]])
  assert np.allclose(r["mean"], mean) and np.allclose(r["std"], std)


def test_test_only_perturbation_does_not_change_training_or_other_predictions():
  from src.models.cnn import training as T
  X, y, g = planted()
  tr, te = g < 15, g >= 15
  Xte = X[te].copy()
  a = T.cnn_fold(X[tr], y[tr], g[tr], Xte, FS, 5, model="eegnet", seed=3, max_epochs=2)
  Xte2 = Xte.copy()
  Xte2[5:] = Xte2[5:] * 50 + 1e3                           # change the OTHER test windows only
  b = T.cnn_fold(X[tr], y[tr], g[tr], Xte2, FS, 5, model="eegnet", seed=3, max_epochs=2)
  for k in ("train_acc", "val_acc", "best_epoch", "val_loss"):
    assert a[k] == b[k], k
  assert np.allclose(a["proba"][:5], b["proba"][:5], atol=1e-7)                    # per-window inference, no test statistics
  assert not np.allclose(a["proba"][5:], b["proba"][5:])


def test_lda_fold_scaler_and_csp_ignore_test_rows(loaded):
  from scripts.benchmarks import benchmark_window_sweep as W
  g = np.asarray(loaded["cv_groups"])
  yi = np.searchsorted(np.unique(loaded["y"]), loaded["y"])
  u = np.unique(g)
  tr, te = np.flatnonzero(np.isin(g, u[:14])), np.flatnonzero(np.isin(g, u[14:]))
  csp, fb = loaded["bands"]["fbcsp"].copy(), W.fbcca_features(loaded)
  p1, t1 = W.lda_fold(csp, fb, yi, tr, te)
  csp2, fb2 = csp.copy(), fb.copy()
  csp2[te[len(te) // 2:]] *= 40.0
  fb2[te[len(te) // 2:]] += 5.0
  p2, t2 = W.lda_fold(csp2, fb2, yi, tr, te)
  assert t1 == t2 and np.allclose(p1[:len(te) // 2], p2[:len(te) // 2], atol=1e-9)


# ---------------------------------------------------------------- (c) FBCCA

def cca_ref(x, f, fs, n_harm=3):
  """First canonical correlation of x (T, C) with sin/cos references, from principal angles."""
  t = np.arange(x.shape[0]) / fs
  y = np.stack([fn(2 * np.pi * h * f * t) for h in range(1, n_harm + 1) for fn in (np.sin, np.cos)], 1)
  return float(np.cos(subspace_angles(x - x.mean(0), y - y.mean(0)).min()))


def test_fbcca_vectorized_matches_independent_principal_angle_cca():
  from src.features.ssvep import fbcca_extraction as F
  rng = np.random.default_rng(11)
  for T in (128, 256, 384):
    bands = rng.normal(size=(6, 3, 5, T))
    got = F.fbcca_scores_vectorized(bands, F.reference_bases(FS, T), chunk=2)
    w = np.arange(1, 4) ** -1.25 + 0.25
    ref = np.array([[sum(w[b] * cca_ref(bands[i, b].T, f, FS) ** 2 for b in range(3)) for f in F.TARGET_FREQS]
                    for i in range(len(bands))])
    assert np.max(np.abs(got - ref)) < 1e-10
    assert got.min() >= 0 and got.max() <= w.sum() + 1e-12
    assert np.allclose(F.fbcca_scores_vectorized(bands[3:4], F.reference_bases(FS, T)), got[3:4], atol=1e-12)  # no cross-window use


def test_fbcca_planted_tone_wins_and_dc_offset_is_ignored():
  from src.features.ssvep import fbcca_extraction as F
  rng = np.random.default_rng(5)
  T = 256
  t = np.arange(T) / FS
  for k, f in enumerate(F.TARGET_FREQS):
    x = np.stack([np.sin(2 * np.pi * f * t + 0.5 * c) + 0.4 * rng.normal(size=T) for c in range(4)])
    bands = np.stack([x, x, x])[None]
    s = F.fbcca_scores_vectorized(bands, F.reference_bases(FS, T))
    assert s.argmax() == k
    assert np.allclose(F.fbcca_scores_vectorized(bands + 1000.0, F.reference_bases(FS, T)), s, atol=1e-8)


# ---------------------------------------------------------------- (d) pseudo-online

def sos():
  from src.online.causal_filter import design_sos
  return design_sos(FS, 1.0, 90.0, 4, 60.0, 30.0)


def test_chunked_filter_equals_independent_one_pass_and_chunk_size_is_irrelevant():
  from src.online.causal_filter import CausalSOSFilter
  rng = np.random.default_rng(0)
  x = rng.normal(size=(3, 3000)) * 5 + 40.0                     # DC offset: zi must be sosfilt_zi * x[0]
  s = sos()
  ref = np.stack([sosfilt(s, row, zi=sosfilt_zi(s) * row[0])[0] for row in x])
  for chunk in (1, 7, 64, 1000, 3000):
    f = CausalSOSFilter(s, 3)
    y = np.concatenate([f.process(x[:, a:a + chunk]) for a in range(0, x.shape[1], chunk)], axis=1)
    assert np.max(np.abs(y - ref)) < 1e-10, chunk


def test_replay_windows_ignore_future_samples_and_chunking():
  from src.online.causal_filter import replay_windows
  rng = np.random.default_rng(1)
  x = rng.normal(size=(2, 6000)) * 5
  n_win, stride, t0 = 128, 64, 4000
  s0, Wf0, Wr0 = replay_windows(x, sos(), n_win, stride)
  assert np.array_equal(s0, np.arange(len(s0)) * stride)                          # fixed clock
  x2 = x.copy()
  x2[:, t0:] = rng.normal(size=(2, 6000 - t0)) * 500 + 300                         # alter only the future
  s1, Wf1, Wr1 = replay_windows(x2, sos(), n_win, stride)
  done = s0 + n_win <= t0
  assert done.sum() > 50
  assert np.array_equal(Wf0[done], Wf1[:len(s0)][done]) and np.array_equal(Wr0[done], Wr1[:len(s0)][done])
  assert not np.array_equal(Wf0[~done][-1], Wf1[~done][-1])
  for chunk in (1, 50, 64, 333, 6000):
    s2, Wf2, _ = replay_windows(x, sos(), n_win, stride, chunk=chunk)
    assert np.array_equal(s2, s0) and np.max(np.abs(Wf2 - Wf0)) < 1e-9, chunk


def test_decide_period_rest_class_never_decides_and_excluded_from_threshold():
  from scripts.benchmarks import pseudo_online as P
  rest_heavy = np.array([[0.02, 0.02, 0.02, 0.02, 0.02, 0.9]] * 6)
  assert P.decide_period(rest_heavy, np.arange(6) * 0.25, 0.5, 0.6, 5, forced_allowed=False) is None
  d = P.decide_period(rest_heavy, np.arange(6) * 0.25, 0.5, 0.6, 5, forced_allowed=True)
  assert d["forced"] == 1 and 0 <= d["pred"] <= 4
  # target 3 reaches 0.65 in the second window only (cumulative mean): time = offset + window, threshold inclusive
  p = np.array([[0, 0, 0.5, 0, 0, 0.5], [0, 0, 0.8, 0, 0, 0.2], [0, 0, 0.9, 0, 0, 0.1]])
  d = P.decide_period(p, np.array([0.5, 0.75, 1.0]), 0.5, 0.65, 5, False)
  assert d == {"pred": 2, "time_sec": 1.25, "forced": 0}
  d = P.decide_period(p, np.array([0.5, 0.75, 1.0]), 0.5, 0.5, 5, False)       # first window max is exactly 0.5
  assert d["time_sec"] == 1.0


def synth_stream(n_trials=6, seed=0):
  b = S.make_block(n_trials=n_trials, seed=seed)
  return b[:8], b[10]


def test_score_stream_decisions_fall_in_the_right_periods_and_never_use_the_future():
  from scripts.benchmarks import pseudo_online as P
  x, mark = synth_stream()
  n_win, stride = 128, 64
  starts = np.arange(0, (x.shape[1] - n_win) // stride + 1) * stride
  rng = np.random.default_rng(0)
  proba = np.full((len(starts), 5), 0.05)
  onsets = {c: P.event_onsets(mark, c) for c in P.TARGETS}
  code_at = {int(o): c for c, v in onsets.items() for o in v}
  for k, st in enumerate(starts):                                # make the true class dominant inside its period only
    for o, c in code_at.items():
      if o + 0.5 * FS <= st and st + n_win <= o + 5 * FS:
        proba[k] = 0.02
        proba[k, c - 101] = 0.92
  dec = P.score_stream(mark, FS, starts, proba, np.ones(len(starts), bool), n_win, 0.5, 0.5, 0.6, 5, 30.0, "S")
  st = dec[dec["period"] == "stimulus"]
  assert len(st) == 6 and (st["correct"] == 1).all() and (st["forced"] == 0).all()
  assert np.allclose(st["time_sec"], 1.0)                                         # first eligible offset 0.5 s + 0.5 s window
  assert (dec[dec["period"] == "rest"]["false_activation"] == 0).all()
  # the decision of a period does not move if later windows of that period or other periods are scrambled
  o0 = int(st.sort_values("onset_sec")["onset_sec"].iloc[1] * FS)
  late = (starts >= o0 + int(1.5 * FS)) & (starts + n_win <= o0 + 5 * FS)
  p2 = proba.copy()
  p2[late] = rng.dirichlet(np.ones(5), late.sum())
  dec2 = P.score_stream(mark, FS, starts, p2, np.ones(len(starts), bool), n_win, 0.5, 0.5, 0.6, 5, 30.0, "S")
  a = dec[(dec["period"] == "stimulus") & (dec["onset_sec"] * FS == o0)].iloc[0]
  b = dec2[(dec2["period"] == "stimulus") & (dec2["onset_sec"] * FS == o0)].iloc[0]
  assert (a["pred"], a["time_sec"], a["forced"]) == (b["pred"], b["time_sec"], b["forced"])


def test_score_stream_six_class_rest_never_decides_and_false_activation_counts():
  from scripts.benchmarks import pseudo_online as P
  x, mark = synth_stream()
  n_win, stride = 128, 64
  starts = np.arange(0, (x.shape[1] - n_win) // stride + 1) * stride
  proba = np.tile([0.02, 0.02, 0.02, 0.02, 0.02, 0.9], (len(starts), 1))
  dec = P.score_stream(mark, FS, starts, proba, np.ones(len(starts), bool), n_win, 0.5, 0.5, 0.6, 6, 30.0, "S")
  assert (dec["pred"] == 0).all() and dec["time_sec"].isna().all()               # rest dominates: no target, no decision
  assert (dec[dec["period"] == "stimulus"]["correct"] == 0).all()
  assert (dec[dec["period"] == "rest"]["false_activation"] == 0).all()
  proba5 = np.tile([0.9, 0.025, 0.025, 0.025, 0.025, 0.0], (len(starts), 1))      # target 101 everywhere, 6 classes
  dec = P.score_stream(mark, FS, starts, proba5, np.ones(len(starts), bool), n_win, 0.5, 0.5, 0.6, 6, 30.0, "S")
  assert (dec[dec["period"] == "rest"]["false_activation"] == 1).all()            # decided during rest: false activation
  assert set(dec["pred"]) <= {101}


@pytest.fixture(scope="module")
def online_runs():
  from types import SimpleNamespace
  from scripts import build_windows as bw
  from scripts.benchmarks import pseudo_online as P
  q = bw.quality_params_from_config(bw.load_build_config(bw.DEFAULT_CONFIG))
  q["source"] = "both"
  xtr, mtr = synth_stream(10, seed=1)
  xte, mte = synth_stream(10, seed=2)
  args = SimpleNamespace(check_sec=30.0, model="ccnn", seed=42, no_augment=True, max_epochs=2, patience=5)
  names = list(S.SCALP)

  def run(x, mark, rest=False):
    return P.run_window_length((xtr, mtr, FS), (x, mark, FS), 0.5, 0.25, sos(), names, q, rest, args, "cpu", "S")

  return run, xte, mte


def test_pseudo_online_stream_probabilities_ignore_mark_and_future_samples(online_runs):
  run, xte, mte = online_runs
  a = run(xte, mte)
  b = run(xte, np.zeros_like(mte))                                                # MARK erased
  assert np.array_equal(a["starts"], b["starts"]) and np.allclose(a["proba"], b["proba"], equal_nan=True, atol=1e-7)
  assert np.array_equal(a["valid"], b["valid"]) and a["kept"] == b["kept"]
  t0 = int(100 * FS)
  x2 = xte.copy()
  x2[:, t0:] += np.random.default_rng(0).normal(0, 30, xte[:, t0:].shape)           # alter the future (after 100 s)
  c = run(x2, mte)
  done = a["starts"] + a["n_win"] <= t0
  assert done.sum() > 100
  assert np.allclose(a["proba"][done], c["proba"][done], equal_nan=True, atol=1e-7)
  assert np.array_equal(a["valid"][done], c["valid"][done])
  assert not np.allclose(a["proba"][~done], c["proba"][~done], equal_nan=True)
  assert a["proba"].shape[1] == 5
  r6 = run(xte, mte, rest=True)
  assert r6["proba"].shape[1] == 6 and r6["n_classes"] == 6


# ---------------------------------------------------------------- (e) CCNN spectral input

@pytest.mark.parametrize("fs,T", [(256.0, 256), (256.0, 512), (250.0, 250), (256.0, 2048)])
def test_ccnn_spectrum_bin_scaling_and_nfft(fs, T):
  from src.models.cnn.ccnn import CCNN
  m = CCNN(5, 3, T, fs=fs)
  nfft = max(T, int(round(fs / 0.25)))
  assert m.nfft == nfft
  hz = np.fft.rfftfreq(nfft, 1 / fs)
  keep = hz[(hz >= 3) & (hz <= 50)]
  assert np.allclose(m.bins_hz, keep) and m.n_bins == len(keep)
  assert m.bins_hz[0] >= 3 and m.bins_hz[-1] <= 50 and m.bins_hz[-1] > 49.5 and m.bins_hz[0] < 3.5
  f = 15.0                                                          # whole cycles in every window above
  t = np.arange(T) / fs
  x = np.zeros((1, 3, T))
  x[0, 0] = 3.0 * np.cos(2 * np.pi * f * t)
  x[0, 1] = 2.0 * np.sin(2 * np.pi * f * t)
  z = m.spectrum(torch.from_numpy(x)).numpy()
  nb = m.n_bins
  assert z.shape == (1, 1, 3, 2 * nb)
  z = np.stack([z[:, 0, :, :nb], z[:, 0, :, nb:]], axis=1)  # split [real | imag] back into (1, 2, 3, n_bins)
  j = int(np.argmin(np.abs(m.bins_hz - f)))
  assert m.bins_hz[j] == pytest.approx(f)
  assert z[0, 0, 0, j] == pytest.approx(1.5, abs=1e-6) and abs(z[0, 1, 0, j]) < 1e-6        # cos amp 3: real = A/2
  assert z[0, 1, 1, j] == pytest.approx(-1.0, abs=1e-6) and abs(z[0, 0, 1, j]) < 1e-6       # sin amp 2: imag = -A/2
  assert np.abs(z[0, :, 0]).max() == pytest.approx(1.5, abs=1e-6)                           # peak is at the tone bin
  assert np.argmax(np.hypot(z[0, 0, 0], z[0, 1, 0])) == j
  assert np.abs(z[0, :, 2]).max() < 1e-9                                                    # empty channel stays empty
  full = np.fft.rfft(x, n=nfft, axis=-1)[..., (hz >= 3) & (hz <= 50)] / T
  assert np.allclose(z[0, 0], full[0].real, atol=1e-6) and np.allclose(z[0, 1], full[0].imag, atol=1e-6)
