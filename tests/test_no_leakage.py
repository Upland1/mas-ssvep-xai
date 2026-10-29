"""No-leakage guard (R1, R8) that every later phase must keep green.

`assert_no_shared_groups` is the check: for every (train, test) split, no group (trial id or
subject) appears on both sides. Every splitter of the repository is registered below with its
era status:

- `legacy`: window-level `StratifiedKFold` (P04-P10; from P11 reachable only with `--cv legacy`). The test
  documents the leak (trials DO straddle train/test) so the legacy number is never mistaken for a clean one.
- `LEAK_FREE`: `StratifiedGroupKFold(5, shuffle, 42)` over trial ids (the R1 target; P11: `cv_utils`
  `grouped_cv` / `make_splits("grouped")` / `legacy_eval.splits_for("grouped")` and the grouped SFS inner CV
  of `benchmark_feature_selection`), whose first entry also proves the helper detects a leak (a mutated
  split fails it). `tests/test_p11_cv.py` runs the five classical scripts' own split code on a synthetic
  tree and applies the same check.

`test_every_splitter_in_the_repo_is_registered` scans src/ and scripts/ for sklearn splitter
imports: adding an unregistered splitter fails until it is listed with its status here.
"""

import re
from pathlib import Path

import numpy as np
import pytest
from sklearn.model_selection import StratifiedGroupKFold

from scripts.training import train_models as tm
from scripts.benchmarks.feature_based import benchmark_feature_selection as bfs
from scripts.benchmarks import benchmark_loso as L
from src.models.classical import legacy_eval as le
from src.preprocessing.dataset import cv_utils

ROOT = Path(__file__).resolve().parents[1]


def trial_layout(n_trials_per_class: int = 8, windows_per_trial: int = 5) -> tuple:
  """`(y, groups)`: 5 classes in condition order, 5 windows per trial (legacy layout), ids unique per trial."""
  y = np.repeat(np.arange(101, 106), n_trials_per_class * windows_per_trial)
  groups = np.repeat(np.arange(5 * n_trials_per_class), windows_per_trial)
  return y, groups


def shared_groups(splits, groups) -> list:
  """Groups present on both sides of any split: `[(fold, sorted shared ids)]` (empty = clean)."""
  bad = []
  for i, (tr, te) in enumerate(splits):
    both = set(np.asarray(groups)[tr]) & set(np.asarray(groups)[te])
    if both:
      bad.append((i, sorted(both)))
  return bad


def assert_no_shared_groups(splits, groups) -> None:
  bad = shared_groups(splits, groups)
  assert not bad, f"groups shared between train and test: fold {bad[0][0]} shares {bad[0][1][:5]}"


# name -> factory returning splits for (y, groups). Window-level splitters ignore the groups.
LEGACY = {
  "scripts.training.train_models.legacy_cv": lambda y, g: list(tm.legacy_cv().split(np.zeros(len(y)), y)),
  "src.models.classical.legacy_eval.legacy_cv": lambda y, g: list(le.legacy_cv().split(np.zeros(len(y)), y)),
  "src.models.classical.legacy_eval.splits_for('legacy')": lambda y, g: le.splits_for("legacy", y, g),
  "src.preprocessing.dataset.cv_utils.make_splits('legacy')": lambda y, g: cv_utils.make_splits("legacy", y, g),
}
LEAK_FREE = {
  "StratifiedGroupKFold(5, shuffle, 42) over trial ids (R1 target)":
    lambda y, g: list(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y, g)),
  "src.preprocessing.dataset.cv_utils.grouped_cv": lambda y, g: list(cv_utils.grouped_cv().split(np.zeros(len(y)), y, g)),
  "src.preprocessing.dataset.cv_utils.make_splits('grouped')": lambda y, g: cv_utils.make_splits("grouped", y, g),
  "src.models.classical.legacy_eval.splits_for('grouped')": lambda y, g: le.splits_for("grouped", y, g),
  "benchmark_feature_selection.inner_sfs_splits (SFS inner CV, PF-01)": lambda y, g: bfs.inner_sfs_splits(y, g),
  # P21: the LOSO outer split is the subject; the 40 trials of this layout are grouped 10 per subject, so a trial belongs to one subject
  "scripts.benchmarks.benchmark_loso.loso_split (outer split = subject, P21)":
    lambda y, g: [L.loso_split(np.asarray(g) // 10, k) for k in range(len(np.unique(g)) // 10)],
}
# Files that import an sklearn splitter, with their era status (update when a phase changes it).
KNOWN_SPLITTER_FILES = {
  "scripts/benchmarks/feature_based/benchmark_feature_selection.py": "legacy",   # DIAGNOSTIC SFS variants only (P06); reported SFS inner CV is grouped (P11)
  "src/preprocessing/dataset/cv_utils.py": "leak-free",
  "scripts/training/train_models.py": "legacy",
  "src/models/cnn/spatial_spectral_cnn.py": "legacy",
  "src/models/cnn/training.py": "leak-free",   # P20 inner grouped validation split of fit_network (PF-32); test in test_p20_networks.py
  "src/models/classical/legacy_eval.py": "legacy",
}
SPLITTER_NAMES = r"(StratifiedKFold|KFold|ShuffleSplit|StratifiedShuffleSplit|GroupKFold|StratifiedGroupKFold|" \
                 r"LeaveOneGroupOut|LeaveOneOut|train_test_split|GroupShuffleSplit)"


@pytest.mark.parametrize("name", sorted(LEAK_FREE))
def test_leak_free_splitters_share_no_group(name):
  y, g = trial_layout()
  assert_no_shared_groups(LEAK_FREE[name](y, g), g)


def test_helper_detects_a_leak():
  """Known answer: moving one test window's trial-mate into the training side is flagged."""
  y, g = trial_layout()
  splits = LEAK_FREE[next(iter(LEAK_FREE))](y, g)
  tr, te = splits[0]
  mate = np.flatnonzero(g == g[te[0]])
  bad_tr = np.union1d(tr, mate)
  assert shared_groups([(bad_tr, te)], g)
  with pytest.raises(AssertionError):
    assert_no_shared_groups([(bad_tr, te)], g)


@pytest.mark.parametrize("name", sorted(LEGACY))
def test_legacy_splitters_leak_by_design_and_say_so(name):
  """R1 LEGACY (by design, PF-01): window-level StratifiedKFold puts windows of one trial on both sides; this
  documents the leak (all legacy accuracies are leaky). When P11 fixes a splitter this test must move to LEAK_FREE."""
  y, g = trial_layout()
  splits = LEGACY[name](y, g)
  assert len(splits) == 5
  assert shared_groups(splits, g), "the legacy splitter unexpectedly became trial-grouped: move it to LEAK_FREE"


def test_legacy_splitters_partition_every_window_once():
  """Known answer: test folds are disjoint and cover every window exactly once (out-of-fold probabilities, R2)."""
  y, g = trial_layout()
  for f in LEGACY.values():
    te = np.concatenate([t for _, t in f(y, g)])
    assert np.array_equal(np.sort(te), np.arange(len(y)))


def test_every_splitter_in_the_repo_is_registered():
  """Guard: any file under src/ or scripts/ importing an sklearn splitter must be in KNOWN_SPLITTER_FILES."""
  found = {}
  pat = re.compile(r"^\s*from\s+sklearn\.model_selection\s+import\s+(\([^)]*\)|[^\n]*)", re.M)
  for d in ("src", "scripts"):
    for p in (ROOT / d).rglob("*.py"):
      for m in pat.finditer(p.read_text()):
        if re.search(SPLITTER_NAMES, m.group(1)):
          found[str(p.relative_to(ROOT))] = True
  unknown = sorted(set(found) - set(KNOWN_SPLITTER_FILES))
  assert not unknown, f"unregistered splitter use in {unknown}: add to KNOWN_SPLITTER_FILES (and a leak test)"
  missing = sorted(set(KNOWN_SPLITTER_FILES) - set(found))
  assert not missing, f"registered files no longer import a splitter: {missing}"
