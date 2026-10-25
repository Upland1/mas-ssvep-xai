"""P06 independent known-answer tests (synthetic-tester): in-fold selection, pruning layout, ablation p values,
smoothing i % 5 and the cohort CSV. Synthetic data only, fixed seeds, fs 250 (legacy Era A).

Mutants (PF-11 selection on all windows, wrong pruned band, unseeded MI, FBCCA not appended, wrong cohort
columns / Mean row) are injected by monkeypatch inside the tests and must be detected by the same assertions.
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import f_oneway

from scripts.benchmarks.feature_based import benchmark_5_subjects as b5
from scripts.benchmarks.feature_based import benchmark_feature_selection as bfs
from scripts.evaluation import evaluate_confusion_matrix as ecm
from src.features.selection import feature_selection as fs
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS, FBCSPTransformer, filter_subbands
from src.models.classical.feature_spaces import build_feature_blocks
from tests.p05_synth import SCALP, make_windows, write_subject


def _blocks(snr=1.0, seed=5, n_trials=4):
  X, y = make_windows(n_trials=n_trials, snr=snr, seed=seed)
  b = build_feature_blocks(X, y, SCALP)
  b.update(n_stimulus=len(y), n_clean=len(b["y"]), n_rejected=len(y) - len(b["y"]))
  return b


def _graded(n=200, seed=0, strengths=None):
  """50 noise columns; column c shifts linearly with the class by strengths[c]."""
  strengths = strengths or {7: 2.0, 31: 1.0}
  rng = np.random.default_rng(seed)
  y = np.tile(np.arange(101, 106), n // 5)
  X = rng.normal(size=(n, 50))
  for c, s in strengths.items():
    X[:, c] += s * (y - 103)
  return X, y


# --- ANOVA / MI ------------------------------------------------------------------------------------------------

def test_anova_ranking_matches_scipy_f_oneway():
  """Known answer: ANOVA picks the k columns with the largest one-way F (scipy.stats.f_oneway, independent of sklearn);
  planted strengths give column 7 > 31 so k=1 -> [7]; exact."""
  X, y = _graded()
  F = np.array([f_oneway(*[X[y == c, j] for c in np.unique(y)]).statistic for j in range(50)])
  for k in (1, 2, 10):
    assert fs.select_k_best_fbcsp_features(X, y, k, "anova").tolist() == sorted(np.argsort(-F)[:k].tolist())
  assert fs.select_k_best_fbcsp_features(X, y, 1, "anova").tolist() == [7]


def test_mi_ranks_strong_planted_first():
  """Known answer: with strengths 2.0 (col 7) and 1.0 (col 31) MI k=1 -> [7], k=2 -> [7, 31]."""
  X, y = _graded()
  assert fs.select_k_best_fbcsp_features(X, y, 1, "mutual_info").tolist() == [7]
  assert fs.select_k_best_fbcsp_features(X, y, 2, "mutual_info").tolist() == [7, 31]


def test_mi_seed_passed_and_deterministic(monkeypatch):
  """MI jitter is seeded: two calls identical on pure noise, the seed reaches mutual_info_classif (42 default).
  Mutant (random_state dropped; the jitter is ~1e-10 so selections rarely change, hence the seed itself is asserted) fails the kwargs check."""
  rng = np.random.default_rng(3)
  y = np.tile(np.arange(101, 106), 40)
  X = rng.normal(size=(200, 50))
  calls = []
  real = fs.mutual_info_classif
  monkeypatch.setattr(fs, "mutual_info_classif", lambda X, y, **k: (calls.append(k), real(X, y, **k))[1])
  a = fs.select_k_best_fbcsp_features(X, y, 10, "mutual_info")
  b = fs.select_k_best_fbcsp_features(X, y, 10, "mutual_info")
  assert a.tolist() == b.tolist() and calls[0] == {"random_state": 42}
  # mutant: seed dropped -> the recorded call kwargs no longer equal {"random_state": 42}
  calls.clear()
  monkeypatch.setattr(fs, "mutual_info_classif", lambda X, y, **k: (calls.append({}), real(X, y, random_state=None))[1])
  fs.select_k_best_fbcsp_features(X, y, 10, "mutual_info")
  assert calls[0] != {"random_state": 42}
  # an explicit different seed is forwarded too
  calls.clear()
  monkeypatch.setattr(fs, "mutual_info_classif", lambda X, y, **k: (calls.append(k), real(X, y, **k))[1])
  fs.select_k_best_fbcsp_features(X, y, 10, "mutual_info", random_state=7)
  assert calls[0] == {"random_state": 7}


@pytest.mark.parametrize("method", ["anova", "mutual_info"])
def test_columns_returned_are_input_columns_not_positions_of_a_subset(method):
  """Known answer: indices refer to the columns of the 50-column input (planted 49 and 0 are returned as 49 and 0)."""
  X, y = _graded(strengths={0: 2.0, 49: 2.0})
  assert fs.select_k_best_fbcsp_features(X, y, 2, method).tolist() == [0, 49]


# --- PF-11 in-fold ---------------------------------------------------------------------------------------------

def _leaky_fixture():
  rng = np.random.default_rng(1)
  y = np.tile(np.arange(101, 106), 40)
  X = rng.normal(size=(200, 50))
  te = np.arange(100, 200)
  X[te, 3] += 3.0 * (y[te] - 103)          # informative only in held-out rows
  return X, y


def test_sfs_infold_only():
  """PF-11: SFS(k=1) on training rows ignores the test-only column 3; SFS fitted on all rows (the leak) picks it."""
  X, y = _leaky_fixture()
  assert 3 not in fs.select_sfs_fbcsp_features(X[:100], y[:100], 1)
  assert fs.select_sfs_fbcsp_features(X, y, 1).tolist() == [3]


def test_sfs_count_and_cca_tail_via_column_sets():
  """Known answer: SFS n=4 -> 4 FBCSP + 5 tail columns; selected < 50, tail = 50..54, nothing else (exact)."""
  X, y = _graded(n=100, seed=4)
  Xf = np.hstack([X, np.random.default_rng(0).normal(size=(100, 5))])
  sel = bfs.column_sets(Xf, y, 50, 6, 4, 42)
  assert [len(sel[m]) for m in bfs.METHODS] == [55, 45, 11, 11, 9]
  for m in (bfs.ANOVA, bfs.MI, bfs.SFS):
    assert sel[m][-5:].tolist() == [50, 51, 52, 53, 54] and sel[m][:-5].max() < 50
  assert {7, 31} <= set(sel[bfs.ANOVA]) and 7 in set(sel[bfs.SFS])


def test_ablation_rejects_selection_on_all_windows(monkeypatch):
  """PF-11 at script level: every selector call sees exactly the training rows (80 of 100) and none of the test rows
  (rows are matched by value against the fold's test matrix). Mutant: legacy_cv hands the whole set as training ->
  the same assertions fail (sizes 100)."""
  b = _blocks()
  seen = []
  orig_k, orig_s = bfs.select_k_best_fbcsp_features, bfs.select_sfs_fbcsp_features
  monkeypatch.setattr(bfs, "select_k_best_fbcsp_features", lambda X, y, *a, **k: (seen.append(len(X)), orig_k(X, y, *a, **k))[1])
  monkeypatch.setattr(bfs, "select_sfs_fbcsp_features", lambda X, y, *a, **k: (seen.append(len(X)), orig_s(X, y, *a, **k))[1])
  bfs.run_ablation(b, "S03", k=6, sfs_k=2, verbose=False)
  assert seen == [80] * 15
  # mutant
  real_cv = bfs.legacy_cv

  class AllRows:
    def split(self, X, y):
      for tr, te in real_cv(42).split(X, y):
        yield np.arange(len(y)), te
  seen.clear()
  monkeypatch.setattr(bfs, "legacy_cv", lambda seed: AllRows())
  bfs.run_ablation(b, "S03", k=6, sfs_k=2, verbose=False, include_sfs=False)
  assert seen != [80] * 10 and set(seen) == {100}


# --- pruning (R6) ----------------------------------------------------------------------------------------------

def test_pruning_exact_columns_and_wrong_band_mutants():
  """R6: dropped = 40..49 exactly; keep = 0..39 + 50..54 (45). Dropping the first band (10..54 kept) or a class-major
  slice (every 5th-class interleave) gives a different set -> the equality fails on those mutants."""
  b = DEFAULT_SUBBANDS
  assert b.index((38, 52)) == 4 and len(b) == 5
  expected = np.array(list(range(40)) + list(range(50, 55)))
  Xtr = np.random.default_rng(0).normal(size=(30, 55))
  y = np.tile(np.arange(101, 106), 6)
  sel = bfs.column_sets(Xtr, y, 50, 20, 15, 42, include_sfs=False)
  assert sel[bfs.PRUNED].tolist() == expected.tolist()
  first_band = np.setdiff1d(np.arange(55), np.arange(0, 10))
  class_major = np.setdiff1d(np.arange(55), np.arange(50).reshape(5, 10)[:, 4])  # drop one column per band
  assert first_band.tolist() != expected.tolist() and class_major.tolist() != expected.tolist()


@pytest.mark.parametrize("band", [0, 2, 4])
def test_band_major_layout_against_transformer(band):
  """R6: replacing only sub-band `band`'s content before the transformer changes columns inside 10*band .. 10*band+9 and only there
  (and at least one of them) -> drop of band 4 removes the 38-52 Hz features and nothing else."""
  X, y = make_windows(n_trials=4, seed=2)
  sw = filter_subbands(X, 250.0, DEFAULT_SUBBANDS)
  sw2 = sw.copy()
  sw2[:, band] = sw[:, (band + 1) % 5]   # scaling is a no-op (normalised CSP covariance): swap content instead
  f1 = FBCSPTransformer(1).fit(sw, y).transform(sw)
  f2 = FBCSPTransformer(1).fit(sw2, y).transform(sw2)
  changed = set(np.flatnonzero(~np.isclose(f1, f2, atol=1e-6).all(axis=0)))
  assert f1.shape[1] == 50
  assert changed and changed <= set(range(10 * band, 10 * band + 10))


# --- p values / FBCCA tail --------------------------------------------------------------------------------------

def test_p_values_55_45_25_25_20_and_tail_mutant(monkeypatch):
  """R-4: p = 55, 45, 25, 25, 20 with k = 20 and SFS 15 FBCSP columns (the synthetic tree has the same 50 + 5 columns).
  The 15-step SFS is the slow part (~90 s), so here its selector is replaced by a stub returning the first n columns (the
  real SFS count is checked in test_sfs_count_and_cca_tail_via_column_sets and the builder's tests); the p = k + 5 / sfs + 5
  arithmetic is also checked with k = 4, sfs = 2 -> 55, 45, 9, 9, 7 and the real SFS. Mutant: FBCCA tail not appended to ANOVA -> that row's p is 20, not 25."""
  b = _blocks()
  real = bfs.column_sets
  real_sfs = bfs.select_sfs_fbcsp_features
  monkeypatch.setattr(bfs, "select_sfs_fbcsp_features", lambda X, y, n, **k: np.arange(n))
  rows = bfs.run_ablation(b, "S03", k=20, sfs_k=15, verbose=False)
  monkeypatch.setattr(bfs, "select_sfs_fbcsp_features", real_sfs)
  assert [r["p"] for r in rows] == [55, 45, 25, 25, 20] and [r["Method"] for r in rows] == list(bfs.METHODS)
  assert [r["p"] for r in bfs.run_ablation(b, "S03", k=4, sfs_k=2, verbose=False)] == [55, 45, 9, 9, 7]

  def no_tail(*a, **k):
    s = real(*a, **k)
    s[bfs.ANOVA] = s[bfs.ANOVA][:-5]
    return s
  monkeypatch.setattr(bfs, "column_sets", no_tail)
  rows = bfs.run_ablation(b, "S03", k=20, sfs_k=2, verbose=False, include_sfs=False)
  assert [r["p"] for r in rows] != [55, 45, 25, 25]


# --- Full row = flagship, smoothing i % 5 -----------------------------------------------------------------------

def test_full_row_equals_flagship_on_hard_tree_and_smoothing_is_mod5(tmp_path, monkeypatch):
  """Low-SNR tree (accuracy well below 100 %, so equality is not vacuous): Full row == P05 flagship CSV row, and the
  reported 2.0 s value equals an independent i % 5 smoothing of the captured out-of-fold scores (row i averaged with
  row i-1 unless i % 5 == 0). Mutant: smoothing without trial reset gives a different accuracy on these scores."""
  write_subject(tmp_path / "processed", "S03", n_trials=6, snr=0.12, seed=21)
  flags = ["--subject", "S03", "--processed-dir", str(tmp_path / "processed"), "--reports-dir", str(tmp_path / "reports")]
  captured = []
  real = bfs.accuracies
  monkeypatch.setattr(bfs, "accuracies", lambda y, p, s: (captured.append((y, p, s)), real(y, p, s))[1])
  assert bfs.main(flags + ["--k-features", "20", "--skip-sfs"]) == 0
  assert ecm.main(flags + ["--figures-dir", str(tmp_path / "fig"), "--no-figures"]) == 0
  df = pd.read_csv(tmp_path / "reports" / "feature_selection_ablation_S03.csv")
  fl = pd.read_csv(tmp_path / "reports" / "flagship_S03.csv").iloc[0]
  assert df.iloc[0]["1.0s Acc (%)"] < 95
  assert df.iloc[0]["1.0s Acc (%)"] == fl["1.0s Acc (%)"] and df.iloc[0]["2.0s Smoothed (%)"] == fl["2.0s Smoothed (%)"]
  y, p, s = captured[0]
  cls = np.unique(y)

  def smooth(reset):
    out = s.copy()
    for i in range(1, len(s)):
      if not reset or i % 5 != 0:
        out[i] = (s[i - 1] + s[i]) / 2
    return out
  acc = lambda sc: round(100 * float(np.mean(cls[np.argmax(sc, axis=1)] == y)), 2)
  assert acc(smooth(True)) == df.iloc[0]["2.0s Smoothed (%)"]
  assert acc(smooth(False)) != acc(smooth(True))   # the no-reset mutant is distinguishable on this tree


# --- cohort CSV -------------------------------------------------------------------------------------------------

COHORT_COLS = ["Subject", "Clean Windows", "Rejected", "1.0s Acc (%)", "2.0s Smoothed (%)"]


def _check_cohort(df, subjects):
  assert list(df.columns) == COHORT_COLS
  assert df["Subject"].tolist() == list(subjects) + ["Mean"]
  for c in COHORT_COLS[3:]:
    assert df[c].iloc[-1] == pytest.approx(round(df[c].iloc[:-1].astype(float).mean(), 2), abs=1e-9)
  assert df[COHORT_COLS[1:3]].iloc[-1].isna().all()


def test_with_mean_row_known_numbers():
  """Known answer: rows (61.0, 67.5), (56.12, 61.73), (86.8, 90.36) -> Mean (67.97, 73.2), computed by hand."""
  rows = [{"Subject": s, "Clean Windows": 100, "Rejected": 1, "1.0s Acc (%)": a, "2.0s Smoothed (%)": c}
          for s, a, c in (("S01", 61.0, 67.5), ("S02", 56.12, 61.73), ("S03", 86.8, 90.36))]
  df = b5.with_mean_row(rows)
  assert df["Subject"].tolist() == ["S01", "S02", "S03", "Mean"] and list(df.columns) == COHORT_COLS
  assert df.iloc[-1]["1.0s Acc (%)"] == 67.97 and df.iloc[-1]["2.0s Smoothed (%)"] == 73.2


def test_cohort_csv_from_script_and_checker_rejects_mutants(tmp_path):
  """Script on three synthetic subjects (numeric order S2 < S10): schema, one row per subject, Mean row, per-subject
  counts 100/0. The checker rejects: a renamed column, a median Mean row, a missing Mean row, a swapped subject order."""
  proc = tmp_path / "processed"
  for s, sd in (("S10", 31), ("S02", 32), ("S03", 33)):
    write_subject(proc, s, n_trials=4, snr=0.3, seed=sd)
  assert b5.main(["--processed-dir", str(proc), "--reports-dir", str(tmp_path / "reports")]) == 0
  df = pd.read_csv(tmp_path / "reports" / "five_subjects_benchmark.csv")
  _check_cohort(df, ["S02", "S03", "S10"])
  assert df["Clean Windows"].iloc[:3].tolist() == [100] * 3 and df["Rejected"].iloc[:3].tolist() == [0] * 3
  bad = df.rename(columns={"1.0s Acc (%)": "Acc"})
  with pytest.raises(AssertionError):
    _check_cohort(bad, ["S02", "S03", "S10"])
  bad = df.copy()
  bad.loc[3, "1.0s Acc (%)"] = df["1.0s Acc (%)"].iloc[:3].median() + 1
  with pytest.raises(AssertionError):
    _check_cohort(bad, ["S02", "S03", "S10"])
  with pytest.raises(AssertionError):
    _check_cohort(df.iloc[:3], ["S02", "S03", "S10"])
  with pytest.raises(AssertionError):
    _check_cohort(df, ["S10", "S02", "S03"])
