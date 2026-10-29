"""P22.4 tests: warm-up study (`scripts/benchmarks/benchmark_loso_warmup.py`) with known answers.

Planted data as in P21: class c = extra variance in channel c; a subject gain adds a constant to log-variance features, which
per-subject normalization removes. Each fix test names the bug it guards.
"""

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_loso_warmup as WU
from tests.test_p21_loso import C, FS, gain_cohort, make_subject


def with_starts(d, rec_rank, stride=64, gap=10_000):
  """Give subject `d` absolute window starts: trial t is recorded at position rec_rank[t] (a permutation of its trial ids), so
  the recording order differs from the id order. Windows of a trial follow `offsets`."""
  d["window_starts"] = np.asarray(rec_rank)[d["trial_ids"]] * gap + np.asarray(d["offsets"])
  return d


def shifted_cohort(n_trials=20, seed=0):
  subs = gain_cohort()
  rng = np.random.default_rng(seed)
  out = []
  for d in subs:
    d = make_subject(d["subject"], 40 + len(out), n_trials=n_trials, wpt=6, snr=0.35, fb_sinus=False,
                     chan_gain=(np.array([0.15, 4.0, 0.2, 3.5, 0.3, 5.0]) if not out else np.random.default_rng(len(out)).uniform(0.3, 3, C)))
    out.append(with_starts(d, rng.permutation(n_trials)))
  return out


def pooled(subs):
  return L.pool(subs, ["fbcsp"])


def run_probas(P, k, ks, yi=None):
  yi = P["yi"] if yi is None else yi
  tr, te = L.loso_split(P["subj"], k)
  csp, F = L.lda_features(P["bands"]["fbcsp"], P["fb"], yi, tr)
  trial_te = P["trial"][te] - L.TRIAL_OFFSET * k
  return tr, te, F, trial_te, WU.warmup_probas(F, P["subj"], tr, te, yi[tr], trial_te, P["starts"][te], ks)


# recording order (PF-36) ---------------------------------------------------------------------------------------------

def test_recording_order_follows_first_window_start_not_the_trial_id():
  """Planted: ids 0..5 are in class order; recorded in the order 3, 0, 5, 1, 4, 2. Known first-K sets for K = 1, 2, 4."""
  trial = np.repeat(np.arange(6), 3)
  rank = np.array([1, 3, 5, 0, 4, 2])                       # trial t is the rank[t]-th recorded
  starts = rank[trial] * 1000 + np.tile([0, 64, 128], 6)
  ids, first = WU.recording_order(trial, starts)
  assert list(ids) == [3, 0, 5, 1, 4, 2] and list(first) == [0, 1000, 2000, 3000, 4000, 5000]
  for k, expect in ((1, {3}), (2, {3, 0}), (4, {3, 0, 5, 1})):
    assert set(np.unique(trial[WU.warmup_rows(trial, starts, k)])) == expect
  # the bug: ordering by id would warm up on trials {0, 1}
  assert set(np.unique(trial[np.isin(trial, np.arange(2))])) != {3, 0}
  # a rejected first window does not move a trial: its earliest remaining window ranks it
  keep = ~((trial == 3) & (np.tile([0, 64, 128], 6) == 0))
  assert list(WU.recording_order(trial[keep], starts[keep])[0]) == [3, 0, 5, 1, 4, 2]
  assert list(WU.recording_order(np.array([5, 5, 2, 2]), np.array([100, 90, 100, 90]))[0]) == [2, 5]     # tie -> smaller id


def test_pool_carries_absolute_starts_and_they_come_from_window_starts():
  subs = [with_starts(make_subject(f"S0{i + 1}", i, n_trials=6, wpt=3), np.arange(6)[::-1]) for i in range(2)]
  P = pooled(subs)
  assert np.array_equal(P["starts"], np.concatenate([d["window_starts"] for d in subs]))
  del subs[0]["window_starts"]
  assert L.pool([make_subject("S01", 1, n_trials=6, wpt=3)], ["fbcsp"])["starts"] is None    # no starts: warm-up refuses


# statistics and guards -----------------------------------------------------------------------------------------------

def test_warmup_stats_are_label_free_and_guard_small_warmups():
  assert "y" not in inspect.signature(WU.warmup_stats).parameters and "labels" not in inspect.signature(WU.warmup_stats).parameters
  rng = np.random.default_rng(0)
  F = rng.normal(3.0, 2.0, (50, 4))
  mu, sd, g = WU.warmup_stats(F)
  assert np.allclose(mu, F.mean(0)) and np.allclose(sd, F.std(0)) and g == "none"
  mu1, sd1, g1 = WU.warmup_stats(F[:1])                     # K = 1 trial with 1 window: std 0 -> guarded
  assert np.array_equal(sd1, np.ones(4)) and np.allclose(mu1, F[0]) and "mean-only" in g1
  assert np.isfinite(WU.apply_stats(F, mu1, sd1)).all()
  Fc = F.copy()
  Fc[:, 2] = 7.0                                            # a constant feature: std 0 -> 1, no division by zero
  _, sdc, gc = WU.warmup_stats(Fc)
  assert sdc[2] == 1.0 and "1 of 4 features floored" in gc and np.isfinite(WU.apply_stats(Fc, *WU.warmup_stats(Fc)[:2])).all()
  with np.errstate(all="raise"):                            # the bug: dividing by std 0
    with pytest.raises(FloatingPointError):
      (Fc - Fc.mean(0)) / Fc.std(0)


def test_binomial_se():
  assert WU.binom_se_pp(0.5, 100) == pytest.approx(5.0) and WU.binom_se_pp(1.0, 50) == 0.0 and np.isnan(WU.binom_se_pp(0.5, 0))


# known answers on planted subjects -----------------------------------------------------------------------------------

def test_warmup_with_every_trial_equals_full_exactly():
  """K = all trials: the first-K statistics ARE the whole-session statistics, so `warmup` == `full` bit for bit."""
  P = pooled(shifted_cohort())
  tr, te, F, trial_te, res = run_probas(P, 0, [20])
  assert res["mask"][20].all()
  mu, sd = res["stats"][20]
  zf = L.subject_zscore(F[te], np.zeros(len(te), int))
  assert np.allclose(WU.apply_stats(F[te], mu, sd), zf, atol=1e-12, rtol=0)
  assert np.allclose(res["warmup"][20], res["full"], atol=1e-12)
  _, _, _, _, small = run_probas(P, 0, [3])
  assert not np.allclose(small["warmup"][3], small["full"])                  # a 3-trial warm-up is not the whole session


def test_with_standardized_features_all_three_variants_coincide():
  """Features already z-scored per subject: the normalization is the identity, so `none` == `full`, and the warm-up
  statistics of the whole session (K = all) change nothing either."""
  P = pooled(shifted_cohort())
  P["fb"] = L.subject_zscore(P["fb"], P["subj"])
  tr, te = L.loso_split(P["subj"], 0)
  csp, F = L.lda_features(P["bands"]["fbcsp"], P["fb"], P["yi"], tr)
  F = L.subject_zscore(F, P["subj"])
  trial_te = P["trial"][te]
  res = WU.warmup_probas(F, P["subj"], tr, te, P["yi"][tr], trial_te, P["starts"][te], [20])
  assert np.allclose(res["none"], res["full"], atol=1e-9) and np.allclose(res["warmup"][20], res["none"], atol=1e-9)


def test_gain_shifted_subject_warmup_beats_none_and_stays_below_or_at_full():
  """Known answer: a held-out subject with a very different channel gain. Plain `lda` is thrown off; first-K statistics with K
  large enough (10 of 20 trials, 5 classes seen) recover most of it. Margins in binomial-SE units (P21 C-3)."""
  P = pooled(shifted_cohort())
  tr, te, F, trial_te, res = run_probas(P, 0, [10])
  yi = P["yi"][te]
  warm = res["mask"][10]
  sc = ~warm
  acc = lambda p: float(np.mean(p[sc].argmax(1) == yi[sc]))
  a_none, a_warm, a_full = acc(res["none"]), acc(res["warmup"][10]), acc(res["full"])
  se = WU.binom_se_pp(a_none, int(sc.sum())) / 100
  assert a_warm >= a_none + 3 * se and a_full >= a_none + 3 * se
  assert a_warm <= a_full + 3 * se                                           # the online variant does not beat the offline bound
  assert len(np.unique(P["y"][te][warm])) == 5


def test_warmup_statistics_ignore_labels_and_every_window_after_k():
  """PF-35 / R2: (a) permuting the held-out labels changes nothing (probabilities and statistics identical); (b) altering the
  features of the windows after the first K trials leaves the warm-up statistics unchanged. A whole-session estimator (the
  `full` statistics) fails (b)."""
  P = pooled(shifted_cohort())
  tr, te, F, trial_te, base = run_probas(P, 1, [2, 5])
  perm = P["yi"].copy()
  perm[te] = np.random.default_rng(0).permutation(perm[te])
  _, _, _, _, shuf = run_probas(P, 1, [2, 5], yi=perm)
  for k in (2, 5):
    assert np.array_equal(base["warmup"][k], shuf["warmup"][k]) and np.array_equal(base["stats"][k][0], shuf["stats"][k][0])
  assert np.array_equal(base["none"], shuf["none"]) and np.array_equal(base["full"], shuf["full"])
  for k in (2, 5):
    warm = base["mask"][k]
    F2 = F.copy()
    F2[te[~warm]] += np.random.default_rng(1).normal(5.0, 3.0, F2[te[~warm]].shape)
    res2 = WU.warmup_probas(F2, P["subj"], tr, te, P["yi"][tr], trial_te, P["starts"][te], [k])
    assert np.array_equal(res2["stats"][k][0], base["stats"][k][0]) and np.array_equal(res2["stats"][k][1], base["stats"][k][1])
    assert np.array_equal(res2["warmup"][k][warm], base["warmup"][k][warm])
    assert not np.allclose(res2["full"][warm], base["full"][warm])           # whole-session statistics DO move
  assert not np.array_equal(base["mask"][2], base["mask"][5])


def test_warmup_set_is_the_first_k_in_recording_order_not_in_id_order():
  P = pooled(shifted_cohort())
  tr, te, F, trial_te, res = run_probas(P, 0, [3])
  rank = {int(t): r for r, t in enumerate(WU.recording_order(trial_te, P["starts"][te])[0])}
  assert set(np.unique(trial_te[res["mask"][3]])) == {t for t, r in rank.items() if r < 3}
  assert set(np.unique(trial_te[res["mask"][3]])) != set(np.unique(trial_te)[:3])      # differs from the id-order set


def test_k_row_columns_counts_span_and_margins():
  P = pooled(shifted_cohort())
  tr, te, F, trial_te, res = run_probas(P, 0, [2, 40])
  st, y, off = P["starts"][te], P["y"][te], P["offsets"][te]
  r = WU.k_row("S01", 2, res, y, trial_te, off, st, P["classes"], 256, 256.0, "ch", "src")
  warm = res["mask"][2]
  assert r["Warm-up windows"] == warm.sum() == 12 and r["Scored windows"] == len(te) - 12
  assert r["Warm-up classes"] == len(np.unique(y[warm]))
  assert r["Warm-up span (s)"] == round((st[warm].max() + 256 - st[warm].min()) / 256.0, 2)
  assert r["warmup - full (pp)"] == round(r["warmup (%)"] - r["full (%)"], 2)
  assert r["full SE (pp)"] == round(WU.binom_se_pp(r["full (%)"] / 100, r["Scored windows"]), 2)
  none_scored = ~warm
  yi = np.searchsorted(P["classes"], y)
  assert r["none (%)"] == round(100 * np.mean(res["none"][none_scored].argmax(1) == yi[none_scored]), 2)
  e = WU.k_row("S01", 40, res, y, trial_te, off, st, P["classes"], 256, 256.0, "ch", "src")      # K beyond the session
  assert e["Scored windows"] == 0 and np.isnan(e["warmup (%)"]) and np.isnan(e["warmup - full (pp)"])


# end to end on built synthetic folders --------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def built(tmp_path_factory):
  from tests import p16_synth as S
  root = tmp_path_factory.mktemp("wu") / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    S.write_built_subject(root, s, n_trials=10, seed=i + 1)
  return root.parent


def test_end_to_end_tables_and_recording_order_from_the_folder_files(built, tmp_path, capsys):
  out = tmp_path / "w"
  assert WU.main(["--data-root", str(built), "--out-dir", str(out), "--warmup-trials", "1", "2", "20"]) == 0
  s = pd.read_csv(out / "summary.csv")
  assert list(s.columns[:9]) == ["Subject", "Warm-up trials", "Warm-up windows", "Warm-up classes", "Warm-up span (s)",
                                 "Scored windows", "full (%)", "warmup (%)", "none (%)"]
  subj = s[s["Subject"].str.fullmatch(r"S\d+")]
  assert len(subj) == 9 and set(s["Subject"]) == {"S01", "S02", "S03", "Mean", "SD"}
  assert (subj[subj["Warm-up trials"] == 20]["Scored windows"] == 0).all()
  coh = pd.read_csv(out / "cohort.csv")
  assert list(coh["Warm-up trials"]) == [1, 2] and "warmup - full (pp) Mean" in coh.columns
  # recording order recomputed from the folder's own files (absolute window_starts), never from the id order
  o = pd.read_csv(out / "recording_order.csv")
  for sname in ("S01", "S02", "S03"):
    d = built / "w1_s0.25" / sname
    y, tid, st, ok = (np.load(d / f"{n}.npy") for n in ("y_labels", "trial_ids", "window_starts", "valid_mask"))
    m = np.isin(y, [101, 102, 103, 104, 105]) & (ok == 1)
    ids = np.unique(tid[m])
    first = np.array([st[m & (tid == t)].min() for t in ids])
    expect = ids[np.argsort(first, kind="stable")]
    got = o[o["Subject"] == sname].sort_values("Recording rank")
    assert list(got["Trial id"]) == list(expect) and list(got["First window start (sample)"]) == sorted(first)
  assert (out / "warmup_config.json").is_file()


def test_end_to_end_explicit_names_and_the_warmup_set_matches_the_order_file(built, tmp_path):
  out = tmp_path / "w2"
  assert WU.main(["--data-root", str(built), "--out-dir", str(out), "--warmup-trials", "3", "--channels", "O1", "Oz", "POz"]) == 0
  s = pd.read_csv(out / "summary.csv")
  assert (s["Channels"] == "O1, Oz, POz").all()
  o = pd.read_csv(out / "recording_order.csv")
  for sname in ("S01", "S02", "S03"):
    n_win = o[(o["Subject"] == sname)].shape[0]
    row = s[(s["Subject"] == sname)].iloc[0]
    assert row["Warm-up trials"] == 3 and row["Warm-up windows"] + row["Scored windows"] == 50 and n_win == 10
  with pytest.raises(SystemExit):
    WU.main(["--data-root", str(built), "--out-dir", str(tmp_path / "x"), "--warmup-trials", "0"])
