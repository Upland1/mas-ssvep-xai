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

# [REQ §3] v1, typed by hand; from P07 the file is v1 with the P07 override (8 scalp channels,
# excluded []): V1 below is the v1 block, V2 the expected committed file.
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


V2 = {**V1, "channels": {**V1["channels"], "excluded": [],
                         "scalp": ["PO7", "PO3", "POz", "PO4", "PO8", "O1", "Oz", "O2"]}}

# P16 (final config, mas/02_REQUIREMENTS.md section 3): highcut 90, notch, quality and filter_bank blocks.
V3 = {**V2, "preprocessing": {**V2["preprocessing"], "highcut_hz": 90.0, "notch_hz": 60.0, "notch_q": 30.0},
      "quality": {"vpp_range_uv": [5.0, 120.0], "std_range_uv": [1.0, 35.0], "channel_fail_fraction": 0.5,
                  "artifact_block_sec": 0.25, "guard_sec": "auto", "guard_rel_amplitude": 0.01,
                  "source": "both"},
      "filter_bank": {"harmonics": {"enabled": True, "n_harmonics": 3, "half_width_hz": 1.0, "order": 2},
                      "intermediate": {"enabled": True, "half_width_hz": 1.0, "order": 2}}}


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


@pytest.mark.parametrize("key", sorted(_flatten(V3)))
def test_config_v1_key_by_key(key):
  """Known answer [REQ §3]: each leaf of v1 has the spec value and YAML type
  (int vs float preserved, e.g. lowcut_hz 1.0 float, cv_splits 5 int). Exact."""
  got = _flatten(_loaded())
  exp = _flatten(V3)[key]
  assert key in got
  assert got[key] == exp
  assert type(got[key]) is type(exp)
  if isinstance(exp, list):
    assert [type(v) for v in got[key]] == [type(v) for v in exp]


def test_config_v1_no_extra_keys():
  """Known answer [REQ §3]: no key beyond v1 (P07/P16 keys absent)."""
  assert set(_flatten(_loaded())) == set(_flatten(V3))
  assert _loaded() == V3


def test_config_v3_text_is_v2_plus_the_p16_lines():
  """Known answer [REQ §3] 'P16 (final) adds/changes': dropping the P16 additions and restoring highcut 60
  gives the v2 dict (P07 channel lines); the header names the version."""
  got = CONFIG.read_text(encoding="utf-8").splitlines()
  assert got[0].startswith("# config v3 (P16")
  cfg = _loaded()
  for k in ("quality", "filter_bank"):
    cfg.pop(k)
  for k in ("notch_hz", "notch_q"):
    cfg["preprocessing"].pop(k)
  cfg["preprocessing"]["highcut_hz"] = 60.0
  assert cfg == V2


def test_config_v2_po7_restored_pf05():
  """PF-05: the montage legend and the pipeline agree: 8 scalp channels incl. PO7, none excluded."""
  ch = _loaded()["channels"]
  assert ch["scalp"][0] == "PO7" and len(ch["scalp"]) == 8 and ch["excluded"] == []
