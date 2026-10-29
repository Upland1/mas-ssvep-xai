"""Structure tests of notebooks/loso_colab.ipynb (P21.3, PF-40): committed clean, ordered cells, safe install,
every shell command parses against the real argparse parser of its script. Nothing is executed on Colab."""
import contextlib
import importlib
import io
import json
import re
import shlex
from pathlib import Path

import nbformat
import pandas as pd
import pytest

NB_PATH = Path(__file__).resolve().parents[1] / "notebooks" / "loso_colab.ipynb"
SETTINGS = ["RAW_DIR", "DRIVE_DIR", "REPO_URL", "BRANCH", "LOSO_OUT"]


@pytest.fixture(scope="module")
def nb():
  return nbformat.read(NB_PATH, as_version=4)


def code_cells(nb):
  return [c.source for c in nb.cells if c.cell_type == "code"]


def first_index(sources, needle):
  for i, s in enumerate(sources):
    if needle in s:
      return i
  raise AssertionError(f"no code cell contains {needle!r}")


def test_valid_nbformat_and_no_outputs(nb):
  nbformat.validate(nb)
  raw = json.loads(NB_PATH.read_text())
  assert raw["nbformat"] == 4
  for c in raw["cells"]:
    if c["cell_type"] == "code":
      assert c["outputs"] == [] and c["execution_count"] is None


def test_required_cells_in_order(nb):
  src = code_cells(nb)
  order = ["nvidia-smi", "drive.mount", "RAW_DIR =", "git clone", "pip install", "os.symlink",
           "scripts.build_windows", "benchmark_window_sweep", "--methods fbcca lda lda_subjnorm",
           "--methods ccnn", "--methods eegnet", "--methods compact", "pd.read_csv", "runtime.unassign"]
  idx = [first_index(src, k) for k in order]
  assert idx == sorted(idx) and len(set(idx)) == len(idx), dict(zip(order, idx))


def test_settings_cell_names_and_checks(nb):
  cell = code_cells(nb)[first_index(code_cells(nb), "RAW_DIR =")]
  for name in SETTINGS:
    assert re.search(rf"^{name} = ", cell, re.M), name
  assert 'REPO_URL = "https://github.com/Upland1/mas-ssvep-xai.git"' in cell
  assert "OO.ebr" in cell and "os.listdir" in cell


def test_install_is_only_pyyaml_joblib(nb):
  alltext = "\n".join(code_cells(nb))
  pips = [ln for ln in alltext.splitlines() if "pip install" in ln]
  assert pips == ["!pip install -q pyyaml joblib"]
  assert not re.search(r"pip\s+install\s+(-\S+\s+)*-r\b", alltext)
  assert "requirements.txt" not in alltext


def test_symlinks_cover_reports_models_and_raw(nb):
  cell = code_cells(nb)[first_index(code_cells(nb), "os.symlink")]
  for key in ('"reports"', '"outputs/models"', "RAW_DIR", "data/processed_continuous"):
    assert key in cell


def _commands(nb):
  out = []
  for s in code_cells(nb):
    if "benchmark_gnn_loso" in s:  # section 10b (P23): tests/test_p23_notebook.py
      continue
    for ln in s.splitlines():
      m = re.match(r"!python -m (scripts[\w.]*)\s*(.*)$", ln.strip())
      if m:
        out.append((m.group(1), m.group(2)))
  return out


def _parse(module, rest):
  parser = importlib.import_module(module).build_parser()
  return parser.parse_args(shlex.split(re.sub(r"\{\w+\}", "x", rest)))  # SystemExit on an unknown option


def test_every_cli_line_parses_with_the_real_parser(nb):
  cmds = _commands(nb)
  assert {m for m, _ in cmds} == {"scripts.build_windows", "scripts.benchmarks.benchmark_window_sweep",
                                  "scripts.benchmarks.benchmark_loso"}
  assert len(cmds) == 6
  for module, rest in cmds:
    args = _parse(module, rest)
    if module.endswith("build_windows"):
      assert args.resume and args.filter_mode == "continuous" and args.quality_source == "both"
      assert args.banks == ["fbcca", "fbcsp"] and args.window_sec == 1 and args.stride_sec == 0.25
    if module.endswith("window_sweep"):
      assert args.windows == [1] and args.methods == ["fbcca", "lda"] and args.cv_repeats == 5


def test_network_cells_are_one_method_each_and_write_to_loso_out(nb):
  nets = [r for m, r in _commands(nb) if m.endswith("benchmark_loso") and "--device" in r]
  assert len(nets) == 3
  for rest in nets:
    assert len(_parse("scripts.benchmarks.benchmark_loso", rest).methods) == 1
    assert "--out-dir {LOSO_OUT}" in rest


def test_comparison_cell_runs_on_synthetic_summaries(nb, tmp_path):
  cols = ["Subject", "Method", "Acc (%)", "Data source"]
  (tmp_path / "w").mkdir()
  (tmp_path / "l").mkdir()
  pd.DataFrame([["S01", "fbcca", 60.0, "w"], ["S02", "fbcca", 70.0, "w"], ["S01", "lda", 80.0, "w"],
                ["S02", "lda", 90.0, "w"]], columns=cols).to_csv(tmp_path / "w" / "summary.csv", index=False)
  pd.DataFrame([["S01", "fbcca", 60.0, "l"], ["S02", "fbcca", 70.0, "l"], ["S01", "lda", 70.0, "l"],
                ["S02", "lda", 85.0, "l"], ["Mean", "lda", 77.5, "l"], ["SD", "lda", 10.0, "l"],
                ["S10", "lda", 50.0, "l"]], columns=cols).to_csv(tmp_path / "l" / "summary.csv", index=False)
  cell = code_cells(nb)[first_index(code_cells(nb), "pd.read_csv")]
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf):
    exec(cell, {"WITHIN_OUT": str(tmp_path / "w"), "LOSO_OUT": str(tmp_path / "l")})
  out = buf.getvalue()
  assert "Mean (subjects)" in out and "LOSO lda" in out and "within lda" in out
  assert out.index("S02") < out.index("S10")
