"""P06 tests (ml-engineer): in-fold FBCSP feature selection, sub-band pruning layout, ablation and cohort scripts.

Synthetic data only (tests/p05_synth.py, fixed seeds); fs 250 as the legacy Era A extractors assume.
"""

import numpy as np
import pandas as pd
import pytest

from scripts.benchmarks.feature_based import benchmark_5_subjects as b5
from scripts.benchmarks.feature_based import benchmark_feature_selection as bfs
from scripts.evaluation import evaluate_confusion_matrix as ecm
from src.features.selection import feature_selection as fs
from src.features.ssvep.fbcsp_extraction import DEFAULT_SUBBANDS, FBCSPTransformer, filter_subbands
from tests.p05_synth import make_windows, write_subject


def _planted(n=200, seed=0, informative=(7, 31)):
  rng = np.random.default_rng(seed)
  y = np.repeat(np.arange(101, 106), n // 5)
  X = rng.normal(size=(n, 50))
  for c in informative:
    X[:, c] += 1.5 * (y - 103)
  return X, y


@pytest.mark.parametrize("method", ["anova", "mutual_info"])
def test_selection_finds_planted_columns(method):
  """Known answer: columns 7 and 31 carry the class; with k = 2 both are selected, indices lie in 0-49 and are sorted."""
  X, y = _planted()
  idx = fs.select_k_best_fbcsp_features(X, y, 2, method)
  assert idx.tolist() == [7, 31]
  idx = fs.select_k_best_fbcsp_features(X, y, 20, method)
  assert len(idx) == 20 and {7, 31} <= set(idx) and idx.min() >= 0 and idx.max() < 50
  assert idx.tolist() == sorted(idx.tolist())


def test_mi_is_seeded_and_bad_method_rejected():
  X, y = _planted()
  a = fs.select_k_best_fbcsp_features(X, y, 10, "mutual_info", random_state=42)
  b = fs.select_k_best_fbcsp_features(X, y, 10, "mutual_info", random_state=42)
  assert a.tolist() == b.tolist()
  with pytest.raises(ValueError):
    fs.select_k_best_fbcsp_features(X, y, 5, "chi2")


def test_selection_is_infold_only():
  """PF-11: a column informative only in the held-out rows is not selected when selection sees the training rows only,
  and would be selected by a full-data fit (the leak)."""
  rng = np.random.default_rng(1)
  y = np.tile(np.arange(101, 106), 40)
  X = rng.normal(size=(200, 50))
  te = np.arange(100, 200)
  X[te, 3] += 3.0 * (y[te] - 103)
  for method in ("anova", "mutual_info"):
    assert 3 not in fs.select_k_best_fbcsp_features(X[:100], y[:100], 1, method)
    assert fs.select_k_best_fbcsp_features(X, y, 1, method).tolist() == [3]


def test_ablation_selection_sees_training_rows_only(monkeypatch):
  """PF-11: spy on the selectors inside the ablation; each call gets exactly the training rows of its fold (40 of 50)."""
  X, y = make_windows(n_trials=2, seed=5)
  seen = []
  orig_k = bfs.select_k_best_fbcsp_features
  monkeypatch.setattr(bfs, "select_k_best_fbcsp_features", lambda Xt, yt, *a, **k: (seen.append(len(Xt)), orig_k(Xt, yt, *a, **k))[1])
  # the SFS itself is slow (500 inner fits per fold) and covered by test_sfs_* and the script tests; here only its input matters
  monkeypatch.setattr(bfs, "select_sfs_fbcsp_features", lambda Xt, yt, n, *a, **k: (seen.append(len(Xt)), np.arange(n))[1])
  from src.models.classical.feature_spaces import build_feature_blocks
  from tests.p05_synth import SCALP
  blocks = build_feature_blocks(X, y, SCALP)
  blocks.update(n_stimulus=len(y), n_clean=len(blocks["y"]), n_rejected=len(y) - len(blocks["y"]))
  bfs.run_ablation(blocks, "S03", k=6, sfs_k=2, verbose=False)
  assert len(seen) == 5 * 3 and set(seen) == {40}   # ANOVA, MI, SFS x 5 folds


def test_subband_pruning_layout():
  """R6: the FBCSP block is band-major, 10 columns per band. Dropping band (38, 52) removes exactly columns 40-49 -> 45 of 55."""
  assert DEFAULT_SUBBANDS.index((38, 52)) == 4
  keep = fs.subband_pruned_columns(55, [4])
  assert keep.tolist() == list(range(40)) + list(range(50, 55)) and len(keep) == 45
  assert fs.band_columns(4).tolist() == list(range(40, 50))
  assert fs.subband_pruned_columns(55, [0]).tolist() == list(range(10, 55))


def test_band_major_layout_matches_fbcsp_transformer():
  """R6 known answer (replaces a vacuous check, P07): the CSP features are scale-invariant, so scaling a band changes
  nothing; instead the content of sub-band 5 (38-52 Hz) is replaced by that of sub-band 1. Exactly the columns that
  `fs.band_columns(4)` names (40-49) change, at least one of them does, and columns 0-39 are bit-identical, so the
  pruning helper removes the 38-52 Hz features and nothing else."""
  X, y = make_windows(n_trials=2, seed=2)
  sw = filter_subbands(X, 250.0, DEFAULT_SUBBANDS)
  sw2 = sw.copy()
  sw2[:, 4] = sw[:, 0]
  f1 = FBCSPTransformer(1).fit(sw, y).transform(sw)
  f2 = FBCSPTransformer(1).fit(sw2, y).transform(sw2)
  changed = set(np.flatnonzero(~np.isclose(f1, f2, atol=1e-6).all(axis=0)).tolist())
  assert f1.shape[1] == 50 and changed
  assert changed <= set(fs.band_columns(4).tolist())
  assert np.array_equal(f1[:, :40], f2[:, :40])
  assert set(fs.subband_pruned_columns(55, [4]).tolist()) == set(range(55)) - set(fs.band_columns(4).tolist())


def test_with_fbcca_keeps_all_tail_columns():
  X = np.arange(55 * 3, dtype=float).reshape(3, 55)
  out = fs.with_fbcca(X, [2, 9], 50)
  assert out.shape == (3, 7) and np.array_equal(out, X[:, [2, 9, 50, 51, 52, 53, 54]])


def test_sfs_selects_planted_columns_and_count():
  """Known answer: SFS on the planted data returns exactly n columns (3, then 2) from 0-49 and includes both informative ones."""
  X, y = _planted(n=100, seed=3)
  idx = fs.select_sfs_fbcsp_features(X, y, 3)
  assert len(idx) == 3 and {7, 31} <= set(idx) and idx.max() < 50
  assert len(fs.select_sfs_fbcsp_features(X, y, 2)) == 2


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
  root = tmp_path_factory.mktemp("p06")
  write_subject(root / "processed", "S03", n_trials=2, seed=11)    # 50 stimulus windows: the smallest tree that
  write_subject(root / "processed", "S04", n_trials=2, seed=12)    # keeps 8 windows per class in each inner SFS fold
  return root


@pytest.fixture(scope="module")
def ablation_plain(tree):
  """One ablation run (k = 20, SFS 2 FBCSP columns) shared by the script test and the diagnostics test."""
  assert bfs.main(_flags(tree, "S03", "--k-features", "20", "--sfs-features", "2")) == 0
  return pd.read_csv(tree / "reports" / "feature_selection_ablation_S03.csv")


def _flags(root, subject="S03", *extra):
  return ["--subject", subject, "--processed-dir", str(root / "processed"), "--reports-dir", str(root / "reports"), *extra]


def test_ablation_script_rows_and_flagship_equivalence(tree, ablation_plain):
  """Smoke: five rows with p = 55, 45, 25, 25, 7 (k = 20, `--sfs-features 2` to keep the suite fast; the default 15 gives
  20, checked on the arithmetic p = n + 5 in test_p06_known_answer), schema columns; the Full row equals the P05 flagship."""
  df = ablation_plain
  assert list(df.columns) == bfs.COLUMNS and df["p"].tolist() == [55, 45, 25, 25, 7]
  assert df["Method"].tolist() == list(bfs.METHODS)
  assert set(df["Clean Windows"]) == {50} and set(df["Rejected"]) == {0}
  assert ecm.main(_flags(tree, "S03", "--figures-dir", str(tree / "fig"), "--no-figures")) == 0
  fl = pd.read_csv(tree / "reports" / "flagship_S03.csv").iloc[0]
  assert df.iloc[0]["1.0s Acc (%)"] == fl["1.0s Acc (%)"] and df.iloc[0]["2.0s Smoothed (%)"] == fl["2.0s Smoothed (%)"]
  meta = (tree / "reports" / "feature_selection_ablation_S03.meta.txt").read_text()
  assert "FBCCA channels (7)" in meta and "legacy" in meta


def test_cohort_script_schema_and_mean_row(tree, ablation_plain):
  """Known answer: columns of 02_REQUIREMENTS section 6, one row per discovered subject (S03, S04) + Mean = mean of the accuracy columns."""
  assert b5.main(["--processed-dir", str(tree / "processed"), "--reports-dir", str(tree / "reports")]) == 0
  df = pd.read_csv(tree / "reports" / "five_subjects_benchmark.csv")
  assert list(df.columns) == ["Subject", "Clean Windows", "Rejected", "1.0s Acc (%)", "2.0s Smoothed (%)"]
  assert df["Subject"].tolist() == ["S03", "S04", "Mean"]
  for c in ("1.0s Acc (%)", "2.0s Smoothed (%)"):
    assert df[c].iloc[2] == pytest.approx(round(df[c].iloc[:2].mean(), 2), abs=1e-9)
  fl = pd.read_csv(tree / "reports" / "flagship_S03.csv").iloc[0]
  assert df.iloc[0]["1.0s Acc (%)"] == fl["1.0s Acc (%)"]          # same code path as the flagship


def test_cohort_discovers_numeric_order(tmp_path):
  write_subject(tmp_path, "S10", n_trials=1)
  write_subject(tmp_path, "S02", n_trials=1)
  (tmp_path / "notes").mkdir()
  assert b5.discover_subjects(tmp_path) == ["S02", "S10"]


def test_missing_subject_exit_code(tree):
  assert bfs.main(_flags(tree, "S09")) == 1


# --- Round 1: SFS diagnostics (labelled DIAGNOSTIC, reported rows unchanged) ---------------------

def test_sfs_variants_cover_the_requested_factors():
  v = bfs.sfs_variants()
  names = [x[0] for x in v]
  assert names[0] == "reported" and v[0][1:] == (5, False, bfs.EST_SCALED, bfs.CAND_FBCSP, 15)
  assert {x[1] for x in v} == {3, 5, 10} and {x[2] for x in v} == {False, True}
  assert {x[3] for x in v} == {bfs.EST_SCALED, bfs.EST_SVD, bfs.EST_NOSCALE}
  assert {x[4] for x in v} == {bfs.CAND_FBCSP, bfs.CAND_ALL} and {x[5] for x in v} == {15, 20}


def test_sfs_diagnostics_script_leaves_reported_rows_and_audits(tree, ablation_plain, monkeypatch, capsys):
  """Smoke: with a reduced variant list the diagnostic CSV and audit CSV are written, the reported CSV is identical
  with and without the flag (`ablation_plain` is the run without it), the reported variant reproduces the reported SFS
  row, and the audit shows disjoint rows (40 training / 10 test rows per fold of the 50-window tree)."""
  small = [v for v in bfs.sfs_variants(2) if v[0] == "reported"]
  monkeypatch.setattr(bfs, "sfs_variants", lambda k=15: small)
  capsys.readouterr()
  assert bfs.main(_flags(tree, "S03", "--k-features", "20", "--sfs-features", "2", "--sfs-diagnostics")) == 0
  with_diag = pd.read_csv(tree / "reports" / "feature_selection_ablation_S03.csv")
  assert ablation_plain.equals(with_diag)
  d = pd.read_csv(tree / "reports" / "feature_selection_sfs_diagnostics_S03.csv")
  assert list(d.columns) == bfs.DIAG_COLUMNS and len(d) == 1 and set(d["Label"]) == {bfs.DIAG_LABEL}
  rep = d[d["Variant"] == "reported"].iloc[0]
  sfs_row = with_diag[with_diag["Method"] == bfs.SFS].iloc[0]
  assert rep["1.0s Acc (%)"] == sfs_row["1.0s Acc (%)"] and rep["p"] == sfs_row["p"] == 7
  a = pd.read_csv(tree / "reports" / "feature_selection_sfs_audit_S03.csv")
  assert list(a.columns) == bfs.AUDIT_COLUMNS and a["Fold"].tolist() == [1, 2, 3, 4, 5]
  assert a["Train rows"].tolist() == [40] * 5 and a["Test rows"].tolist() == [10] * 5
  assert a["Disjoint indices"].all() and (a["Test rows found in SFS input"] == 0).all()
  assert all(len(s.split()) == 2 for s in a["Selected FBCSP columns"])
  assert "DIAGNOSTIC" in capsys.readouterr().out


def test_leak_audit_detects_overlap():
  """The audit assertion fails when a test row is part of the SFS input (planted leak)."""
  rng = np.random.default_rng(0)
  Xall = rng.normal(size=(20, 55))
  tr, te = np.arange(16), np.arange(16, 20)
  ok = bfs.leak_audit_row("S", 0, tr, te, Xall[tr], Xall[te], np.array([1, 2]), 50)
  assert ok["Test rows found in SFS input"] == 0
  with pytest.raises(AssertionError):
    bfs.leak_audit_row("S", 0, tr, te, Xall[:18], Xall[te], np.array([1, 2]), 50)
