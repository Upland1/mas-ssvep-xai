"""Known-answer tests for configs/pipeline_config.yaml v1 (P01.2).

The expected config is (a) the v1 YAML block extracted from
mas/02_REQUIREMENTS.md section 3 ([REQ §3]) and (b) an independent hand-typed
dict of the same block. Both must equal the committed file key by key.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pipeline_config.yaml"
REQ = ROOT / "mas" / "02_REQUIREMENTS.md"

# [REQ §3] v1, typed by hand.
V1 = {
  "project": {"name": "ssvep-eeg-xai", "target_conditions": [201, 202, 101, 102, 103, 104, 105]},
  "paths": {"data_raw_dir": "data/raw", "data_processed_dir": "data/processed",
            "figures_dir": "outputs/figures", "reports_dir": "outputs/reports",
            "saved_models_dir": "outputs/saved_models"},
  "channels": {"scalp": ["PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"], "excluded": ["PO7"],
               "mark_channel": "MARK", "auxiliary": ["TIMESTAMP", "FLASHINGTIME"]},
  "preprocessing": {"lowcut_hz": 1.0, "highcut_hz": 60.0, "filter_order": 4,
                    "sub_window_sec": 1.0, "vpp_thresh_uv": 200.0, "std_range": [0.5, 60.0],
                    "baseline": {"cross_condition": 201, "cue_condition": 202,
                                 "stimulus_duration_sec": 5.0, "pre_stim_cross_sec": 2.0,
                                 "cue_lookback_sec": 1.0}},
  "features": {"psd_range_hz": [5.0, 35.0], "plotting_range_hz": [1.0, 60.0]},
  "training": {"cv_splits": 5, "random_state": 42, "batch_size": 16, "learning_rate": 0.001,
               "epochs": 100},
}


def _spec_v1_text():
  text = REQ.read_text(encoding="utf-8")
  m = re.search(r"\*\*v1 \(P01, legacy\):\*\*\s*```yaml\n(.*?)```", text, re.S)
  assert m, "v1 block not found in mas/02_REQUIREMENTS.md"
  return m.group(1)


def _flatten(d, prefix=""):
  out = {}
  for k, v in d.items():
    key = f"{prefix}{k}"
    if isinstance(v, dict):
      out.update(_flatten(v, key + "."))
    else:
      out[key] = v
  return out


def _loaded():
  return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_hand_typed_matches_spec_block():
  """Sanity: the hand-typed dict equals the [REQ §3] v1 block (guards this test)."""
  assert yaml.safe_load(_spec_v1_text()) == V1


@pytest.mark.parametrize("key", sorted(_flatten(V1)))
def test_config_v1_key_by_key(key):
  """Known answer [REQ §3]: each leaf of v1 has the spec value and YAML type
  (int vs float preserved, e.g. lowcut_hz 1.0 float, cv_splits 5 int). Exact."""
  got = _flatten(_loaded())
  exp = _flatten(V1)[key]
  assert key in got
  assert got[key] == exp
  assert type(got[key]) is type(exp)
  if isinstance(exp, list):
    assert [type(v) for v in got[key]] == [type(v) for v in exp]


def test_config_v1_no_extra_keys():
  """Known answer [REQ §3]: no key beyond v1 (P07/P16 keys absent)."""
  assert set(_flatten(_loaded())) == set(_flatten(V1))
  assert _loaded() == V1


def test_config_v1_text_equals_spec_block():
  """Known answer [REQ §3] 'v1 copied verbatim': file text equals the spec block,
  ignoring only trailing whitespace per line and blank lines at the end."""
  norm = lambda s: [l.rstrip() for l in s.strip("\n").splitlines()]
  assert norm(CONFIG.read_text(encoding="utf-8")) == norm(_spec_v1_text())


def test_config_v1_po7_legacy_label():
  """PF-05 legacy label: the scalp line carries '# PO7 hard-excluded (legacy)';
  scalp (7 names) + excluded == the 8-channel montage of [spec §2]."""
  text = CONFIG.read_text(encoding="utf-8")
  scalp_line = [l for l in text.splitlines() if l.strip().startswith("scalp:")]
  assert len(scalp_line) == 1 and "# PO7 hard-excluded (legacy)" in scalp_line[0]
  ch = _loaded()["channels"]
  assert "PO7" not in ch["scalp"] and len(ch["scalp"]) == 7
  assert sorted(ch["scalp"] + ch["excluded"]) == sorted(
    ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"])
