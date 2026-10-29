"""P22 independent known-answer tests (synthetic-tester): within_lda, explicit channels, check_fold, fold-count guard, warm-up.

Every expected value is computed here from first principles (numpy / sklearn / git), not by calling the code under test.
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import StratifiedGroupKFold

from scripts.benchmarks import benchmark_loso as L
from scripts.benchmarks import benchmark_loso_warmup as WU
from src.features.ssvep.fbcsp_extraction import FBCSPTransformer
from tests.test_p21_loso import make_subject

MONTAGE = ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]


def ref_within(bands, fb, yi, groups, folds, repeats, seed, K):
  """Independent grouped-CV LDA: manual z-scoring with numpy, bare sklearn LDA (lsqr, auto shrinkage)."""
  out = np.zeros((repeats, len(yi), K))
  for r in range(repeats):
    cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed + r)
    for tr, te in cv.split(np.zeros(len(yi)), yi, groups):
      csp = FBCSPTransformer(1).fit(bands[tr], yi[tr])
      Ftr, Fte = (np.hstack([csp.transform(bands[i]), fb[i]]) for i in (tr, te))
      mu, sd = Ftr.mean(0), Ftr.std(0)
      lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit((Ftr - mu) / sd, yi[tr])
      out[r, te] = lda.predict_proba((Fte - mu) / sd)
  return out


# --- within_lda ------------------------------------------------------------------------------------------------------

def test_within_lda_matches_independent_grouped_cv_on_planted_subject():
  d = make_subject("S01", 11, n_trials=20, wpt=4, snr=0.6)
  P = L.pool([d], ["fbcsp"])
  res = L.within_lda_fold(P["bands"]["fbcsp"], P["fb"], P["yi"], P["groups"], folds=4, repeats=2, seed=42, n_classes=5)
  ref = ref_within(P["bands"]["fbcsp"], P["fb"], P["yi"], P["groups"], 4, 2, 42, 5)
  assert np.array_equal(res["proba"].argmax(2), ref.argmax(2))
  assert np.allclose(res["proba"], ref, atol=1e-6)
  assert res["proba"].shape == (2, 80, 5) and np.allclose(res["proba"].sum(2), 1)
  assert np.mean(res["proba"][0].argmax(1) == P["yi"]) > 0.6          # planted variance: far above 20 % chance
  # repeats use different seeds (42 + r): the two repeats are different partitions
  s0 = [te.tolist() for _, te in L.within_splits(P["yi"], P["groups"], 4, 42)]
  s1 = [te.tolist() for _, te in L.within_splits(P["yi"], P["groups"], 4, 43)]
  assert s0 != s1


def test_within_folds_never_split_a_trial_and_cover_each_window_once():
  d = make_subject("S01", 5, n_trials=25, wpt=7)                       # heavily overlapping windows of a trial
  g, yi = np.asarray(d["trial_ids"]), np.searchsorted(np.unique(d["y"]), d["y"])
  for seed in range(42, 47):
    splits = L.within_splits(yi, g, 5, seed)
    seen = np.concatenate([te for _, te in splits])
    assert sorted(seen) == list(range(len(yi)))
    for tr, te in splits:
      assert not set(g[tr]) & set(g[te])
      assert len(set(g[te])) >= 1 and len(te) % 7 == 0               # whole trials only
  # a window-level splitter is able to violate the invariant on the same data
  from sklearn.model_selection import StratifiedKFold
  tr, te = next(iter(StratifiedKFold(5, shuffle=True, random_state=0).split(np.zeros(len(yi)), yi)))
  assert set(g[tr]) & set(g[te])


def test_within_lda_uses_exactly_the_loso_channels_and_data_of_those_channels(tmp_path):
  from tests import p16_synth as S
  root = tmp_path / "d" / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    S.write_built_subject(root, s, n_trials=10, seed=i + 1)
  out = tmp_path / "o"
  names = ["Oz", "O1", "POz"]                                          # order differs from the montage on purpose
  argv = ["--data-root", str(root.parent), "--out-dir", str(out), "--methods", "lda", "within_lda", "--folds", "2",
          "--within-repeats", "2", "--channels", *names]
  assert L.main(argv) == 0
  for s in ("S01", "S02", "S03"):
    for m in ("lda", "within_lda"):
      assert L.load_fold(L.fold_path(out, m, s))[1]["channels"] == names
  # independent recomputation from the built folder with exactly those channels
  from src.io.subject_data import load_subject
  from src.models.classical.benchmark_runner import load_config
  from src.preprocessing.window_quality import quality_params_from_config
  q = quality_params_from_config(load_config(L.ROOT / "configs" / "pipeline_config.yaml"))
  thr = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  d = load_subject(root / "S02", [101, 102, 103, 104, 105], "shared", bands=("fbcca", "fbcsp"), thresholds=thr,
                   channel_fail_fraction=q["channel_fail_fraction"], channels=names)
  d["fb"] = L.fbcca_features(d)
  yi = np.searchsorted(np.unique(d["y"]), d["y"])
  ref = ref_within(d["bands"]["fbcsp"], d["fb"], yi, np.asarray(d["cv_groups"]), 2, 2, 42, 5)
  arrays, _ = L.load_fold(L.fold_path(out, "within_lda", "S02"))
  assert arrays["proba_rep"].shape == ref.shape
  assert np.allclose(arrays["proba_rep"], ref, atol=1e-6)
  # the same recomputation on a different channel list does not reproduce the stored folds
  d2 = load_subject(root / "S02", [101, 102, 103, 104, 105], "shared", bands=("fbcca", "fbcsp"), thresholds=thr,
                    channel_fail_fraction=q["channel_fail_fraction"], channels=["O1", "Oz"])
  d2["fb"] = L.fbcca_features(d2)
  ref2 = ref_within(d2["bands"]["fbcsp"], d2["fb"], yi, np.asarray(d2["cv_groups"]), 2, 2, 42, 5)
  lg = lambda a: np.log(a + 1e-300)                                  # probabilities saturate: compare log-probabilities
  assert not np.allclose(lg(arrays["proba_rep"]), lg(ref2), rtol=1e-3)
  assert np.allclose(lg(arrays["proba_rep"]), lg(ref), rtol=1e-3)


# --- explicit channel names -------------------------------------------------------------------------------------------

def test_explicit_names_leave_out_subjects_with_planted_drops_and_error_paths(tmp_path, capsys):
  from tests import p16_synth as S
  root = tmp_path / "d" / "w1_s0.25"
  S.write_built_subject(root, "S01", n_trials=10, seed=1, bad_channel="Oz")
  S.write_built_subject(root, "S02", n_trials=10, seed=2)
  S.write_built_subject(root, "S03", n_trials=10, seed=3)
  S.write_built_subject(root, "S04", n_trials=10, seed=4)
  base = ["--data-root", str(root.parent), "--methods", "fbcca", "--folds", "2", "--within-repeats", "2"]
  out = tmp_path / "a"
  assert L.main(base + ["--out-dir", str(out), "--channels", "Oz", "O1"]) == 0
  txt = capsys.readouterr().out
  assert "Leaving out S01: gate dropped Oz" in txt
  assert "Leaving out S02" not in txt and "Leaving out S03" not in txt
  cfg = json.loads((out / "loso_config.json").read_text())
  assert cfg["cohort"] == ["S02", "S03", "S04"] and cfg["channels"] == ["Oz", "O1"]
  assert set(pd.read_csv(out / "summary.csv")["Subject"]) == {"S02", "S03", "S04", "Mean", "SD"}
  # a channel not named does not exclude S01
  out2 = tmp_path / "b"
  assert L.main(base + ["--out-dir", str(out2), "--channels", "O1", "POz"]) == 0
  assert json.loads((out2 / "loso_config.json").read_text())["cohort"] == ["S01", "S02", "S03", "S04"]
  # unknown name
  with pytest.raises(SystemExit) as e:
    L.main(base + ["--out-dir", str(tmp_path / "c"), "--channels", "O1", "XX9"])
  assert "XX9" in str(e.value) and not (tmp_path / "c" / "summary.csv").exists()
  # parse errors
  for bad in (["common", "O1"], ["O1", "O1"], []):
    with pytest.raises(ValueError):
      L.parse_channels(bad)
  assert L.parse_channels(["O2", "O1"]) == ("names", ["O2", "O1"])
  # fewer than 2 left: drop Oz in S01 and S02, then only S03 and S04 remain (ok); drop in three subjects -> error
  S.write_built_subject(root, "S02", n_trials=10, seed=2, bad_channel="Oz")
  S.write_built_subject(root, "S03", n_trials=10, seed=3, bad_channel="Oz")
  with pytest.raises(SystemExit, match="2 subjects"):
    L.main(base + ["--out-dir", str(tmp_path / "d2"), "--channels", "Oz", "O1"])
  assert not (tmp_path / "d2" / "summary.csv").exists()


def test_leave_out_pure_function_planted():
  m = {s: MONTAGE for s in ("S01", "S02", "S03", "S04")}
  kept = {"S01": MONTAGE, "S02": [c for c in MONTAGE if c != "PO8"], "S03": [c for c in MONTAGE if c not in ("PO8", "O2")],
          "S04": MONTAGE}
  rem, left = L.leave_out_for_names(m, kept, ["O2", "PO8", "Oz"])
  assert rem == ["S01", "S04"] and left == {"S02": ["PO8"], "S03": ["O2", "PO8"]}
  assert L.leave_out_for_names(m, kept, ["Oz"])[0] == ["S01", "S02", "S03", "S04"]
  with pytest.raises(ValueError):
    L.leave_out_for_names(m, kept, ["Fz"])


# --- check_fold --------------------------------------------------------------------------------------------------------

def git(repo, *a):
  return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, capture_output=True, text=True,
                        check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
  r = tmp_path / "rp"
  for d in ("src", "scripts", "docs", "reports"):
    (r / d).mkdir(parents=True)
    (r / d / "f.txt").write_text("0\n")
  git(r, "init", "-q")
  git(r, "add", "-A")
  git(r, "commit", "-qm", "base")
  heads = {"base": git(r, "rev-parse", "HEAD")}
  (r / "docs" / "f.txt").write_text("1\n")
  (r / "reports" / "f.txt").write_text("1\n")
  git(r, "commit", "-qam", "docs")
  heads["docs"] = git(r, "rev-parse", "HEAD")
  (r / "scripts" / "f.txt").write_text("1\n")
  git(r, "commit", "-qam", "scripts")
  heads["scripts"] = git(r, "rev-parse", "HEAD")
  (r / "src" / "f.txt").write_text("1\n")
  git(r, "commit", "-qam", "src")
  heads["src"] = git(r, "rev-parse", "HEAD")
  return r, heads


CFG = {"method": "lda", "test_subject": "S02", "train_subjects": ["S01", "S03"], "cohort": ["S01", "S02", "S03"],
       "channels_mode": "names", "channels": ["O1", "Oz"], "window_sec": 1.0, "stride_sec": 0.25, "fs": 256.0,
       "classes": [101, 102, 103, 104, 105], "quality": "shared", "seed": 42, "trial_offset": 10000,
       "hyper": {"folds": 5, "within_repeats": 5}, "n_windows_test": 321, "git_head": "x", "git_dirty": False,
       "data_root": "/a"}
ALT = {"method": "within_lda", "test_subject": "S01", "train_subjects": ["S01"], "cohort": ["S01", "S02"],
       "channels_mode": "common", "channels": ["Oz", "O1"], "window_sec": 2.0, "stride_sec": 0.5, "fs": 250.0,
       "classes": [101, 102], "quality": "per_script", "seed": 7, "trial_offset": 1000, "hyper": {"folds": 4, "within_repeats": 5},
       "n_windows_test": 320}


def test_alt_covers_every_config_key():
  assert set(ALT) | {"git_head", "git_dirty", "data_root"} == set(CFG)


@pytest.mark.parametrize("key", sorted(ALT))
def test_check_fold_refuses_each_key_but_not_data_root(key, tmp_path):
  with pytest.raises(SystemExit) as e:
    L.check_fold(tmp_path / "f.npz", CFG, {**CFG, key: ALT[key]})
  assert "use a new --out-dir" in str(e.value) and key in str(e.value)
  L.check_fold(tmp_path / "f.npz", CFG, dict(CFG))
  L.check_fold(tmp_path / "f.npz", CFG, {**CFG, "data_root": "/moved"})


def test_check_fold_head_rules(repo, tmp_path):
  r, h = repo
  mk = lambda head, dirty=False: {**CFG, "git_head": head, "git_dirty": dirty}
  f = tmp_path / "f.npz"
  L.check_fold(f, mk(h["base"]), mk(h["docs"]), r)                    # only docs/reports differ: accepted
  L.check_fold(f, mk(h["docs"]), mk(h["base"]), r)                    # symmetric
  for a, b in (("docs", "scripts"), ("scripts", "src"), ("base", "src"), ("src", "base")):
    with pytest.raises(SystemExit, match="use a new --out-dir"):
      L.check_fold(f, mk(h[a]), mk(h[b]), r)
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    L.check_fold(f, mk(h["base"]), mk("0123456789abcdef0123456789abcdef01234567"), r)
  with pytest.raises(SystemExit, match="use a new --out-dir"):
    L.check_fold(f, mk("0123456789abcdef0123456789abcdef01234567"), mk(h["base"]), r)
  L.check_fold(f, mk(h["src"]), mk(h["src"]), r)
  with pytest.raises(SystemExit):
    L.check_fold(f, mk(h["src"], False), mk(h["src"], True), r)       # uncommitted code vs clean at the same head


# --- fold-count guard --------------------------------------------------------------------------------------------------

def test_fold_count_guard_cohort_rows_and_end_to_end(tmp_path, capsys):
  from tests import p16_synth as S
  root = tmp_path / "d" / "w1_s0.25"
  for i, s in enumerate(["S01", "S02", "S03"]):
    S.write_built_subject(root, s, n_trials=10, seed=i + 1)
  out = tmp_path / "o"
  argv = ["--data-root", str(root.parent), "--out-dir", str(out), "--methods", "fbcca", "lda", "--folds", "2",
          "--within-repeats", "2"]
  assert L.main(argv) == 0
  full = pd.read_csv(out / "summary.csv")
  assert full[(full["Method"] == "lda") & (full["Subject"] == "Mean")]["Acc (%)"].notna().all()
  # remove one lda fold file and rebuild the summary from the fold files only
  cfg_of = lambda m, s: L.load_fold(L.fold_path(out, m, s))[1]
  L.fold_path(out, "lda", "S03").unlink()
  capsys.readouterr()
  res = L.build_summary(out, ["S01", "S02", "S03"], np.array([101, 102, 103, 104, 105]), ["fbcca", "lda"], cfg_of, "src")
  txt = capsys.readouterr().out
  assert "[warn]" in txt and "2 fold files for a cohort of 3" in txt
  s = res["summary"]
  mean_lda = s[(s["Method"] == "lda") & (s["Subject"] == "Mean")].iloc[0]
  mean_cca = s[(s["Method"] == "fbcca") & (s["Subject"] == "Mean")].iloc[0]
  assert pd.isna(mean_lda["Acc (%)"]) and mean_lda["Folds"] == 2 and "INCOMPLETE" in mean_lda["Data source"]
  assert pd.notna(mean_cca["Acc (%)"]) and mean_cca["Folds"] == 3 and "INCOMPLETE" not in mean_cca["Data source"]
  assert res["per_subject"].loc["Mean"].filter(like="lda").isna().all()
  # --partial-mean overrides
  res2 = L.build_summary(out, ["S01", "S02", "S03"], np.array([101, 102, 103, 104, 105]), ["fbcca", "lda"], cfg_of, "src", True)
  m2 = res2["summary"].query("Method == 'lda' and Subject == 'Mean'").iloc[0]
  assert m2["Acc (%)"] == pytest.approx(np.mean(res2["summary"].query("Method == 'lda' and Subject in ['S01','S02']")["Acc (%)"]), abs=0.01)


# --- warm-up ----------------------------------------------------------------------------------------------------------

def planted_starts(n_trials, wpt, order, gap=5000, stride=64):
  """order[i] = trial id recorded i-th. Returns trial ids per row and absolute starts."""
  tid = np.repeat(np.arange(n_trials), wpt)
  pos = np.empty(n_trials, int)
  pos[np.asarray(order)] = np.arange(n_trials)
  return tid, 100000 + pos[tid] * gap + np.tile(np.arange(wpt) * stride, n_trials)


def test_recording_order_planted_layout_differs_from_id_order():
  order = [4, 1, 7, 0, 5, 2, 6, 3]
  tid, st = planted_starts(8, 3, order)
  perm = np.random.default_rng(0).permutation(len(tid))              # row order must not matter
  ids, first = WU.recording_order(tid[perm], st[perm])
  assert list(ids) == order and list(first) == sorted(first) and first[0] == 100000
  assert list(ids) != sorted(ids)
  for k in (1, 3, 5, 8):
    m = WU.warmup_rows(tid, st, k)
    assert set(tid[m]) == set(order[:k]) and m.sum() == 3 * k


def feats(n_rows, d=5, seed=0):
  return np.random.default_rng(seed).normal(2.0, 3.0, (n_rows, d))


def test_warmup_stats_exact_values_and_std_guards():
  F = feats(40)
  mu, sd, g = WU.warmup_stats(F)
  assert np.allclose(mu, F.mean(0)) and np.allclose(sd, F.std(0, ddof=0)) and g == "none"
  mu1, sd1, g1 = WU.warmup_stats(F[:1])
  assert np.allclose(mu1, F[0]) and np.array_equal(sd1, np.ones(5)) and g1 != "none"
  Z = WU.apply_stats(F[:1], mu1, sd1)
  assert np.array_equal(Z, np.zeros((1, 5)))
  twin = np.vstack([F[:1], F[:1]])                                   # 2 identical rows: std 0 everywhere
  _, sd2, g2 = WU.warmup_stats(twin)
  assert np.array_equal(sd2, np.ones(5)) and "5 of 5" in g2
  assert np.isfinite(WU.apply_stats(F, *WU.warmup_stats(twin)[:2])).all()


def test_binomial_se_values():
  assert WU.binom_se_pp(0.5, 100) == pytest.approx(5.0)
  assert WU.binom_se_pp(0.9, 400) == pytest.approx(1.5)
  assert WU.binom_se_pp(0.0, 10) == 0.0 and WU.binom_se_pp(1.0, 10) == 0.0
  assert WU.binom_se_pp(0.2, 25) == pytest.approx(8.0)
  assert np.isnan(WU.binom_se_pp(0.5, 0))


def gain_world(n_trials=20, wpt=6, seed=3, order=None):
  """3 training subjects (mild gains) + a held-out subject with a large per-channel gain; the held-out subject is recorded in
  a permuted order. Returns pooled arrays."""
  rng = np.random.default_rng(seed)
  subs = []
  for i, g in enumerate([np.ones(6) * 0.8, np.linspace(0.7, 1.3, 6), np.linspace(1.4, 0.6, 6)]):
    subs.append(make_subject(f"S0{i + 2}", 30 + i, n_trials=n_trials, wpt=wpt, snr=0.4, fb_sinus=False, chan_gain=g))
  ho = make_subject("S01", 50, n_trials=n_trials, wpt=wpt, snr=0.4, fb_sinus=False,
                    chan_gain=np.array([0.15, 4.0, 0.2, 3.5, 0.3, 5.0]))
  order = rng.permutation(n_trials) if order is None else order
  allsubs = [ho] + subs
  for j, d in enumerate(allsubs):
    o = order if j == 0 else np.arange(n_trials)
    _, d["window_starts"] = planted_starts(n_trials, wpt, o)
  return L.pool(allsubs, ["fbcsp"]), np.asarray(order)


def probas(P, ks, mut=None):
  tr, te = L.loso_split(P["subj"], 0)
  bands = P["bands"]["fbcsp"] if mut is None else mut
  _, F = L.lda_features(bands, P["fb"], P["yi"], tr)
  trial_te = P["trial"][te]
  return te, F, trial_te, WU.warmup_probas(F, P["subj"], tr, te, P["yi"][tr], trial_te, P["starts"][te], ks)


def test_first_k_stats_are_those_of_the_first_recorded_trials_and_ignore_labels_and_later_windows():
  P, order = gain_world()
  ks = (1, 3, 6)
  te, F, trial, res = probas(P, ks)
  Fte = F[te]
  for k in ks:
    rows = np.isin(trial, order[:k])
    assert np.array_equal(res["mask"][k], rows)
    mu, sd = res["stats"][k]
    assert np.allclose(mu, Fte[rows].mean(0))
    if rows.sum() >= 2:
      assert np.allclose(sd, np.where(Fte[rows].std(0) < 1e-12, 1.0, Fte[rows].std(0)))
    # not the id-order set
    assert not np.array_equal(rows, np.isin(trial, np.unique(trial)[:k])) or k == 20
  # labels of the held-out subject permuted: identical stats and identical probabilities
  P2 = dict(P)
  yi2 = P["yi"].copy()
  yi2[P["subj"] == 0] = np.random.default_rng(1).permutation(yi2[P["subj"] == 0])
  P2["yi"] = yi2
  _, F2, _, res2 = probas(P2, ks)
  for k in ks:
    assert np.array_equal(res["stats"][k][0], res2["stats"][k][0]) and np.array_equal(res["stats"][k][1], res2["stats"][k][1])
    assert np.array_equal(res["warmup"][k], res2["warmup"][k])
  # alter every window recorded after the first k=3 trials (huge distortion): the k=3 stats do not move
  bands = P["bands"]["fbcsp"].copy()
  te_idx = np.flatnonzero(P["subj"] == 0)
  post = te_idx[~np.isin(trial, order[:3])]
  bands[post, :, 0, :] *= 7.0
  _, F3, _, res3 = probas(P, ks, mut=bands)
  assert not np.allclose(F3[post], F[post])
  assert np.array_equal(res["stats"][3][0], res3["stats"][3][0]) and np.array_equal(res["stats"][3][1], res3["stats"][3][1])
  # statistic of K=6 DOES move only if a window within the first 6 changed: here it is allowed to equal or differ, but k=1 is fixed
  assert np.array_equal(res["stats"][1][0], res3["stats"][1][0])


def test_k_equal_all_trials_gives_warmup_equal_full_and_none_differs():
  P, order = gain_world(n_trials=20)
  te, F, trial, res = probas(P, (20,))
  assert np.allclose(res["warmup"][20], res["full"], atol=1e-10)
  assert not np.allclose(res["none"], res["full"], atol=1e-3)


def test_warmup_recovers_toward_full_as_k_grows_on_a_gain_shifted_subject():
  accs = {"none": [], "warm": {}, "full": []}
  for seed in range(4):                                              # several recording orders
    P, order = gain_world(n_trials=30, wpt=6, seed=seed, order=np.random.default_rng(seed).permutation(30))
    ks = (1, 15)
    te, F, trial, res = probas(P, ks)
    score = ~np.isin(trial, order[:15])                              # same windows for every variant
    yi = P["yi"][te][score]
    a = lambda p: float(np.mean(p[score].argmax(1) == yi))
    accs["none"].append(a(res["none"]))
    accs["full"].append(a(res["full"]))
    for k in ks:
      accs["warm"].setdefault(k, []).append(a(res["warmup"][k]))
  m = lambda v: float(np.mean(v))
  assert m(accs["full"]) > m(accs["none"]) + 0.15                     # the planted shift hurts plain lda
  assert m(accs["warm"][15]) > m(accs["warm"][1]) + 0.10              # more warm-up -> better
  assert m(accs["warm"][15]) > m(accs["none"]) + 0.10
  assert m(accs["warm"][15]) >= m(accs["full"]) - 0.08                # close to the offline upper bound


def test_k_row_scores_only_post_k_windows_with_counts():
  P, order = gain_world(n_trials=12, wpt=4)
  te, F, trial, res = probas(P, (3,))
  y, off, st = P["y"][te], P["offsets"][te], P["starts"][te]
  row = WU.k_row("S01", 3, res, y, trial, off, st, P["classes"], 256, 256.0, "ch", "src")
  assert row["Warm-up windows"] == 12 and row["Scored windows"] == 36 and row["Warm-up windows"] + row["Scored windows"] == len(te)
  sc = ~np.isin(trial, order[:3])
  yi = P["yi"][te][sc]
  assert row["warmup (%)"] == round(100 * float(np.mean(res["warmup"][3][sc].argmax(1) == yi)), 2)
  assert row["none (%)"] == round(100 * float(np.mean(res["none"][sc].argmax(1) == yi)), 2)
  assert row["warmup - full (pp)"] == round(row["warmup (%)"] - row["full (%)"], 2)
  assert row["Warm-up classes"] == len(set(y[np.isin(trial, order[:3])]))


# --- fix round 1 (audit F1, F2, T1) ------------------------------------------------------------------------------------

@pytest.fixture()
def repo2(tmp_path):
  """base -> docs-only head -> configs-only head."""
  r = tmp_path / "rp2"
  for d in ("src", "scripts", "configs", "docs"):
    (r / d).mkdir(parents=True)
    (r / d / "f.txt").write_text("0\n")
  git(r, "init", "-q")
  git(r, "add", "-A")
  git(r, "commit", "-qm", "base")
  h = {"base": git(r, "rev-parse", "HEAD")}
  (r / "docs" / "f.txt").write_text("1\n")
  git(r, "commit", "-qam", "docs")
  h["docs"] = git(r, "rev-parse", "HEAD")
  (r / "configs" / "f.txt").write_text("1\n")
  git(r, "commit", "-qam", "configs")
  h["configs"] = git(r, "rev-parse", "HEAD")
  return r, h


# (head before, head now, dirty before, dirty now, accepted)
ROUND1_TABLE = [
  ("base", "docs", False, True, False),
  ("base", "docs", True, False, False),
  ("base", "docs", True, True, False),
  ("base", "docs", False, False, True),
  ("docs", "configs", False, False, False),
  ("docs", "docs", True, True, True),
]


@pytest.mark.parametrize("a,b,da,db,ok", ROUND1_TABLE)
def test_round1_dirty_and_configs_table(repo2, tmp_path, a, b, da, db, ok):
  r, h = repo2
  saved, mine = {**CFG, "git_head": h[a], "git_dirty": da}, {**CFG, "git_head": h[b], "git_dirty": db}
  if ok:
    L.check_fold(tmp_path / "f.npz", saved, mine, r)
  else:
    with pytest.raises(SystemExit, match="use a new --out-dir"):
      L.check_fold(tmp_path / "f.npz", saved, mine, r)


# --- T2: a rejected first window keeps the trial's recording rank (PF-36), through load_subject ---------------------------

def test_masked_first_window_keeps_rank_and_first_k_set_through_load_subject(tmp_path):
  from tests import p16_synth as S
  from src.io.subject_data import load_subject
  from src.models.classical.benchmark_runner import load_config
  from src.preprocessing.window_quality import quality_params_from_config
  root = tmp_path / "w1_s0.25"
  S.write_built_subject(root, "S01", n_trials=10, seed=4)
  q = quality_params_from_config(load_config(L.ROOT / "configs" / "pipeline_config.yaml"))
  thr = {k: q[k] for k in ("vpp_min", "vpp_max", "std_min", "std_max")}
  load = lambda: load_subject(root / "S01", [101, 102, 103, 104, 105], "shared", thresholds=thr,
                              channel_fail_fraction=q["channel_fail_fraction"])
  before = load()
  tb, sb = np.asarray(before["trial_ids"]), np.asarray(before["window_starts"])
  ids0, first0 = WU.recording_order(tb, sb)
  assert list(ids0) != sorted(ids0)                                   # the built layout is not in id order
  victim = int(ids0[2])                                               # a trial that is warm-up for K >= 3
  d = root / "S01"
  ok = np.load(d / "valid_mask.npy")
  y, tid, st = (np.load(d / f"{n}.npy") for n in ("y_labels", "trial_ids", "window_starts"))
  rows = np.flatnonzero((tid == victim) & np.isin(y, [101, 102, 103, 104, 105]) & (ok == 1))
  first_row = rows[np.argmin(st[rows])]
  second_start = np.sort(st[rows])[1]
  ok[first_row] = 0                                                   # earliest window of the trial rejected
  np.save(d / "valid_mask.npy", ok)
  after = load()
  ta, sa = np.asarray(after["trial_ids"]), np.asarray(after["window_starts"])
  assert len(ta) == len(tb) - 1
  ids1, first1 = WU.recording_order(ta, sa)
  assert list(ids1) == list(ids0)                                     # same rank for every trial
  assert first1[list(ids1).index(victim)] == second_start > first0[2]  # starts from its second window
  for k in (1, 2, 3, 5, 8):
    assert set(ta[WU.warmup_rows(ta, sa, k)]) == set(ids0[:k]) == set(tb[WU.warmup_rows(tb, sb, k)])
