"""P16.7 connectivity port: legacy regression against the pre-port flow, and a built folder with a known answer.

Legacy part: a synthetic legacy tree (bad channel, bad windows, one short block so the ids are approximate) is
loaded by the pre-P16 functions (`load_legacy_selection`, `gate_selection`, `load_gated_conditions`, kept as the
reference) and by the ported `load_condition_windows`; every script must give the same numbers (settled point 4).
Built part: `tests/p16_synth.write_built_subject` (a tone common to all channels in the stimulus window = a
coupled pair at the target frequency, independent noise elsewhere): real fs, true trial ids and the shared
mask reach the permutation code; `shared-no-guard` keeps at least as many windows.
"""

import numpy as np
import pandas as pd
import pytest

from scripts.connectivity.analysis import analyze_connectivity as single
from scripts.connectivity.analysis import analyze_connectivity_cohort as cohort
from scripts.connectivity.comparison import compare_connectivity_frequencies as cmpf
from scripts.connectivity.comparison import test_connectivity_frequency_differences as pair
from scripts.connectivity.diagnostics import check_power_alpha_confound as pw
from src.features.connectivity import connectivity_extraction as ce
from src.features.connectivity import permutation as pm
from src.io.subject_data import load_subject
from tests import p16_synth


def _legacy_tree(root, short_block=False, seed=0):
  """S01: 4 cycles of 201 x2, class x5 (and a 202), 7 channels, PO3 noisy, two windows large."""
  rng = np.random.default_rng(seed)
  labels = []
  for rep in range(4):
    for c in (201, 101, 201, 102, 201, 103, 201, 104, 201, 105):
      labels += [c] * (2 if c == 201 else 5)
    labels += [202]
  if short_block:
    del labels[3]                              # a 201/101 block no longer a multiple of its trial length
  y = np.array(labels)
  X = 10.0 * rng.standard_normal((len(y), 7, 256))
  X[:, 1, :] *= 30.0                             # one channel fails the gate in every window
  X[14] *= 100.0
  X[40, 3] += 400.0
  d = root / "S01"
  d.mkdir(parents=True)
  np.save(d / "X_time_windows.npy", X)
  np.save(d / "y_labels.npy", y)
  return y


@pytest.mark.parametrize("short_block", [False, True])
def test_legacy_loader_equals_pre_port_loader(tmp_path, short_block):
  _legacy_tree(tmp_path, short_block)
  old = ce.load_gated_conditions(tmp_path, "S01")
  new = ce.load_condition_windows(tmp_path, "S01")
  assert np.array_equal(old["windows"], new["windows"]) and old["windows"].dtype == new["windows"].dtype
  assert np.array_equal(old["y"], new["y"]) and np.array_equal(old["trial_ids"], new["trial_ids"])
  assert old["channels_kept"] == new["channels_kept"] and old["channels_dropped"] == new["channels_dropped"]
  assert old["counts"] == new["counts"] and old["n_total_windows"] == new["n_total_windows"]
  assert old["trial_ids_approximate"] == new["trial_ids_approximate"] == short_block
  assert new["fs"] == 250.0 and new["fs_source"] == "legacy-assumed" and not new["built"]
  assert len(new["channels_dropped"]) == 1 and len(new["y"]) < new["n_total_windows"]


@pytest.mark.parametrize("unit", ["trial", "window"])
def test_legacy_cohort_equals_pre_port_flow(tmp_path, unit):
  _legacy_tree(tmp_path / "root", short_block=True)
  args = cohort.build_parser().parse_args(
    ["--methods", "coherence", "plv", "--permutations", "15", "--n-jobs", "1", "--permutation-unit", unit,
     "--data-root", str(tmp_path / "root"), "--reports-dir", str(tmp_path / "rep")])
  new = cohort.run_cohort(args)
  sel = ce.load_legacy_selection(tmp_path / "root", "S01")
  gate = ce.gate_selection(sel)
  for m in ("coherence", "plv"):
    res = pm.extract_connectivity_by_condition(
      sel["windows"], sel["y"], 250.0, cohort.METHODS[m], list(ce.CONDITION_FREQS), sel["channel_names"],
      n_permutations=15, trial_ids=sel["trial_ids"] if unit == "trial" else None, quality=gate, n_jobs=1,
      random_state=cohort.SEED, alpha=0.05, seed_keys=("S01", m))
    got = new["summary"][new["summary"]["method"] == m].set_index("condition")
    det = new["details"][new["details"]["method"] == m].set_index("condition")
    for c in ce.CONDITION_FREQS:
      assert got.loc[c, "obs_diff"] == res[c]["obs_diff"]
      assert got.loc[c, "p_one_tailed"] == res[c]["p_one_tailed"]
      assert got.loc[c, "n_edges_sig_fdr"] == res[c]["n_edges_sig_fdr"]
      assert det.loc[c, "n_stim_windows"] == res[c]["n_stim"] and det.loc[c, "fs"] == 250.0
      assert det.loc[c, "source"] == cohort.SOURCE and bool(det.loc[c, "trial_ids_approximate"])
    assert got["channels_dropped"].iloc[0] == ";".join(gate["channels_dropped"])


def test_legacy_single_subject_and_other_scripts_equal_pre_port(tmp_path):
  _legacy_tree(tmp_path / "root")
  root = tmp_path / "root"
  # analyze_connectivity: rows from the pre-port loader
  rc = single.main(["--subject", "S01", "--data-root", str(root), "--reports-dir", str(tmp_path / "rep"), "--no-figures"])
  assert rc == 0
  old = ce.load_gated_conditions(root, "S01")
  exp = pd.DataFrame(ce.summary_rows(old["windows"], old["y"], 250.0))
  exp.insert(0, "subject", "S01")
  got = pd.read_csv(tmp_path / "rep" / "connectivity" / "coherence_S01_summary.csv")
  pd.testing.assert_frame_equal(got, pd.read_csv(pd.io.common.StringIO(exp.to_csv(index=False))))
  assert "(legacy, raw windows, R3 era B)" in (tmp_path / "rep" / "connectivity" / "coherence_S01_summary.meta.txt").read_text()
  # power confound rows
  kept = old["channels_kept"]
  rows = pd.DataFrame(pw.subject_rows(root, "S01"))
  w, y = old["windows"], old["y"]
  idx = [kept.index(c) for c in pw.OCCIPITAL if c in kept]
  m = pw.power_metrics(w[y == 104], w[y == 201], idx, ce.CONDITION_FREQS[104], 250.0)
  assert rows.set_index("condition").loc[104, "target_snr_db"] == m["target_snr_db"]
  # pairwise-test loader
  g = pair.load_subject_groups(root, "S01")
  assert g["fs"] == 250.0 and g["source"] == pair.SOURCE and g["n_total"] == old["n_total_windows"]
  for c, (wc, ids) in g["groups"].items():
    assert np.array_equal(wc, old["windows"][old["y"] == c]) and np.array_equal(ids, old["trial_ids"][old["y"] == c])


def test_legacy_fs_override_changes_only_the_axis(tmp_path):
  _legacy_tree(tmp_path / "root")
  sel = ce.load_condition_windows(tmp_path / "root", "S01", fs_override=256.0)
  base = ce.load_condition_windows(tmp_path / "root", "S01")
  assert sel["fs"] == 256.0 and sel["fs_source"] == "override" and np.array_equal(sel["windows"], base["windows"])
  assert "override" in ce.source_text(sel, "legacy")


# ---------------------------------------------------------------- built folder, known answer

@pytest.fixture(scope="module")
def built_root(tmp_path_factory):
  root = tmp_path_factory.mktemp("built")
  # bad_channel PO8 is dropped by tier 1; the spike (trial 0, stimulus second 2.5) breaks a window and its guard
  p16_synth.write_built_subject(root, "S01", "continuous", n_trials=20, seed=3, spike_s=12.5, bad_channel="PO8")
  return root


def _run(built_root, tmp_path, extra=(), suffix="t", methods=("coherence",), perms="19"):
  calls = []
  real = cohort.extract_connectivity_by_condition

  def spy(*a, **k):
    calls.append((a, k))
    return real(*a, **k)

  cohort.extract_connectivity_by_condition = spy
  try:
    rc = cohort.main(["--methods", *methods, "--permutations", perms, "--n-jobs", "1", "--data-root", str(built_root),
                      "--reports-dir", str(tmp_path / "rep"), "--out-suffix", suffix, *extra])
  finally:
    cohort.extract_connectivity_by_condition = real
  assert rc == 0
  return calls, pd.read_csv(tmp_path / "rep" / f"connectivity_cohort_summary_{suffix}.csv"), \
    pd.read_csv(tmp_path / "rep" / f"connectivity_cohort_summary_{suffix}_details.csv")


def test_built_cohort_real_fs_true_ids_shared_mask_and_coupled_pair(built_root, tmp_path):
  calls, summ, det = _run(built_root, tmp_path)
  d = load_subject(built_root / "S01", conditions=ce.CONNECTIVITY_CONDITIONS, quality_mode="shared")
  (a, k), = calls
  assert a[2] == 256.0 and (det["fs"] == 256.0).all()                               # real fs from the metadata
  assert "meta" in det["source"].iloc[0] and "quality shared" in det["source"].iloc[0]
  assert np.array_equal(k["trial_ids"], d["trial_ids"]) and len(k["trial_ids"]) == len(a[1]) == len(d["y"])
  stim_ids = {c: set(k["trial_ids"][a[1] == c]) for c in ce.CONDITION_FREQS}
  assert all(len(v) == 4 for v in stim_ids.values())                                # 20 trials / 5 classes: TRUE trials
  assert not set.union(*stim_ids.values()) & set(k["trial_ids"][a[1] == 201])
  assert (summ["permutation_unit"] == "trial").all() and (summ["n_channels"] == 7).all()
  assert (summ["channels_dropped"] == "PO8").all()
  for c in ce.CONDITION_FREQS:                                                        # the shared mask, row by row
    assert det.set_index("condition").loc[c, "n_stim_windows"] == int((d["y"] == c).sum())
  assert det["n_baseline_windows"].iloc[0] == int((d["y"] == 201).sum())
  assert not det["trial_ids_approximate"].any()
  # coupled (tone common to all channels at f_c) against independent noise at baseline
  assert (summ["obs_diff"] > 0.5).all() and (summ["p_one_tailed"] <= 0.1).all()
  assert (summ["n_edges_sig_fdr"] >= 0).all() and (summ["total_edges"] == 21).all()


def test_built_no_guard_keeps_at_least_as_many_windows_and_differs_when_the_guard_bites(built_root, tmp_path):
  _, s_sh, d_sh = _run(built_root, tmp_path, suffix="sh")
  _, s_ng, d_ng = _run(built_root, tmp_path, extra=("--quality", "shared-no-guard"), suffix="ng")
  n_sh = d_sh["n_stim_windows"].sum() + d_sh["n_baseline_windows"].iloc[0]
  n_ng = d_ng["n_stim_windows"].sum() + d_ng["n_baseline_windows"].iloc[0]
  ds = load_subject(built_root / "S01", conditions=ce.CONNECTIVITY_CONDITIONS, quality_mode="shared")
  dn = load_subject(built_root / "S01", conditions=ce.CONNECTIVITY_CONDITIONS, quality_mode="shared-no-guard")
  assert n_sh == len(ds["y"]) and n_ng == len(dn["y"])
  assert n_ng >= n_sh and "shared-no-guard" in d_ng["source"].iloc[0]


def test_built_fs_override_and_single_subject_script(built_root, tmp_path):
  _, _, det = _run(built_root, tmp_path, extra=("--fs", "250"), suffix="fs250")
  assert (det["fs"] == 250.0).all() and "override" in det["source"].iloc[0]
  rc = single.main(["--subject", "S01", "--data-root", str(built_root), "--reports-dir", str(tmp_path / "rep"),
                    "--no-figures", "--out-suffix", "v2"])
  assert rc == 0
  df = pd.read_csv(tmp_path / "rep" / "connectivity" / "coherence_S01_summary_v2.csv")
  assert (df["mean_difference"] > 0.5).all()
  meta = (tmp_path / "rep" / "connectivity" / "coherence_S01_summary_v2.meta.txt").read_text()
  assert "true recording rate" in meta and "continuous build" in meta


def test_built_downstream_scripts_use_suffix_and_responders_from_accuracy_only(built_root, tmp_path):
  _run(built_root, tmp_path, suffix="v2x", methods=("coherence", "plv", "wpli", "pdc"), perms="9")
  rep = tmp_path / "rep"
  bench = tmp_path / "bench.csv"
  pd.DataFrame({"subject": ["S01"], "smoothed_2s": [90.0]}).to_csv(bench, index=False)
  rc = cmpf.main(["--edges-dir", str(rep / "connectivity_edges_v2x"), "--reports-dir", str(rep), "--no-figures",
                  "--qap-permutations", "20", "--responders", "S01", "--out-suffix", "v2x"])
  assert rc == 0
  out = rep / "connectivity_comparison"
  assert (out / "coherence_global_delta_v2x.csv").is_file() and not (out / "coherence_global_delta.csv").exists()
  rc = pw.main(["--data-root", str(built_root), "--reports-dir", str(rep), "--no-figures", "--out-suffix", "v2x",
                "--subjects", "S01"])
  assert rc == 0
  tab = pd.read_csv(out / "power_confound_table_v2x.csv")
  assert set(tab["channels_used"]) == {"O1;Oz;O2"} and tab["n_stim_windows"].min() > 0
  rc = pair.main(["--data-root", str(built_root), "--reports-dir", str(rep), "--methods", "coherence",
                  "--permutations", "9", "--splits", "2", "--n-jobs", "1", "--out-suffix", "v2x", "--responders", "S01"])
  assert rc == 0
  pt = pd.read_csv(out / "coherence_pairwise_tests_v2x.csv")
  assert len(pt) == 10 and not pt["trial_ids_approximate"].any()
  det = pd.read_csv(out / "coherence_split_half_details_v2x.csv")
  assert (det["fs"] == 256.0).all()
