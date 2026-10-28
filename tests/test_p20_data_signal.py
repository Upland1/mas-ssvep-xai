"""P20 data-signal tests: carry-forwards P19 C-1 / C-2 (this block); dynamic stopping, causal filter and the
pseudo-online clock are added below."""

import numpy as np
import pytest

from scripts import build_windows as bw
from scripts.diagnostics import demo_edge_effects as D
from src.io import subject_data as SD
from tests import p16_synth as S

ALL = (201, 202, 101, 102, 103, 104, 105)


# --- P19 C-1 ----------------------------------------------------------------------

def test_demo_edge_effects_passes_quality_source_filtered_explicitly(tmp_path, monkeypatch):
  """C-1. Known answer: the params the demo builds with carry `quality.source == "filtered"` even though the
  config default is `both` (P19); the historical call inherited the default."""
  S.write_raw_subject(tmp_path / "raw", "S03", n_trials=6, seed=3)
  seen = []
  orig = bw.build_subject

  def spy(x, mark, fs, params):
    seen.append(params["quality"]["source"])
    return orig(x, mark, fs, params)

  monkeypatch.setattr(bw, "build_subject", spy)
  rc = D.main(["--subject", "S03", "--raw-dir", str(tmp_path / "raw"), "--reports-dir", str(tmp_path / "r"),
               "--figures-dir", str(tmp_path / "f")])
  assert rc == 0 and seen and set(seen) == {"filtered"}
  assert bw.resolve_params(bw.load_build_config(bw.DEFAULT_CONFIG),
                           bw.build_parser().parse_args([]))["quality"]["source"] == "both"   # the inherited default


# --- P19 C-2 ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def planted(tmp_path_factory):
  """A built folder whose reject_reason / masks are rewritten with a known mix of reasons: row a = raw guard only
  (reason 3, kept without the guard), row b = raw gate (reason 3, rejected in both modes), row c = own gate
  (reason 1), row d = filtered guard (reason 2, kept without the guard)."""
  root = tmp_path_factory.mktemp("c2")
  d = S.write_built_subject(root, "S01", n_trials=10, seed=1)
  y = np.load(d / "y_labels.npy")
  rows = np.flatnonzero(y == 101)[:4]
  reason = np.load(d / "reject_reason.npy").copy()
  valid = np.load(d / "valid_mask.npy").copy()
  nog = np.load(d / "valid_mask_no_guard.npy").copy()
  (a, b, c, e) = rows
  reason[[a, b, c, e]] = [3, 3, 1, 2]
  valid[[a, b, c, e]] = 0
  nog[[a, b, c, e]] = [1, 0, 0, 1]
  np.save(d / "reject_reason.npy", reason)
  np.save(d / "valid_mask.npy", valid)
  np.save(d / "valid_mask_no_guard.npy", nog)
  return d


@pytest.mark.parametrize("mode", ["shared", "shared-no-guard"])
def test_rejection_counts_sum_to_total_minus_valid(planted, mode):
  """C-2. Known answer, per label and mode: own_gate + guard + raw == total - valid. In shared-no-guard the
  raw-guard-only window is kept, so it must not be counted as a raw rejection (historical count: no `& ~keep`)."""
  d = SD.load_subject(planted, ALL, quality_mode=mode)
  rej = d["quality"]["rejections_by_label"]
  for lab, r in rej.items():
    assert r["own_gate"] + r["guard"] + r["raw"] == r["total"] - r["valid"], (mode, lab, r)
  r = rej[101]
  if mode == "shared":
    assert (r["own_gate"], r["guard"], r["raw"]) == (1, 1, 2)
  else:
    assert (r["own_gate"], r["guard"], r["raw"]) == (1, 0, 1)
