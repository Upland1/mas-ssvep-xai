"""Structure tests of section 10b (GNN under LOSO) of notebooks/loso_colab.ipynb (P23.3). Nothing is executed on Colab."""
import importlib
import json
import re
import shlex
from pathlib import Path

import nbformat
import pytest

NB_PATH = Path(__file__).resolve().parents[1] / "notebooks" / "loso_colab.ipynb"
MODULE = "scripts.connectivity.graph_modeling.benchmark_gnn_loso"


@pytest.fixture(scope="module")
def nb():
  return nbformat.read(NB_PATH, as_version=4)


def _index(nb, pred):
  for i, c in enumerate(nb.cells):
    if pred(c):
      return i
  raise AssertionError("cell not found")


def _section(nb):
  start = _index(nb, lambda c: c.cell_type == "markdown" and c.source.startswith("## 10b."))
  end = _index(nb, lambda c: c.cell_type == "markdown" and c.source.startswith("## 11."))
  return nb.cells[start:end]


def _parse(rest):
  parser = importlib.import_module(MODULE).build_parser()
  return parser.parse_args(shlex.split(re.sub(r"\{\w+\}", "x", rest)))


def _gnn_commands(nb):
  out = []
  for c in _section(nb):
    if c.cell_type != "code":
      continue
    for ln in c.source.splitlines():
      m = re.match(r"!python -m (scripts[\w.]*)\s*(.*)$", ln.strip())
      if m:
        out.append((m.group(1), m.group(2)))
  return out


def test_clean_and_ordered_after_the_network_cells(nb):
  nbformat.validate(nb)
  raw = json.loads(NB_PATH.read_text())
  assert all(c["outputs"] == [] and c["execution_count"] is None for c in raw["cells"] if c["cell_type"] == "code")
  ids = [c.get("id") for c in nb.cells]
  assert len(ids) == len(set(ids))
  last_net = max(i for i, c in enumerate(nb.cells) if c.cell_type == "code" and "--methods compact" in c.source)
  start = _index(nb, lambda c: c.cell_type == "markdown" and c.source.startswith("## 10b."))
  comp = _index(nb, lambda c: c.cell_type == "code" and "pd.read_csv" in c.source)
  rel = _index(nb, lambda c: c.cell_type == "code" and "runtime.unassign" in c.source)
  assert last_net < start < comp < rel


def test_intro_explains_subjnorm_and_runtimes(nb):
  intro = _section(nb)[0].source
  assert "_subjnorm" in intro and "test-time normalization" in intro and "offline upper bound" in intro
  assert "min" in intro and "BRANCH" in intro


def test_section_order_smoke_within_loso(nb):
  cmds = _gnn_commands(nb)
  assert [m for m, _ in cmds] == [MODULE] * 6
  assert "--smoke-test" in cmds[0][1]
  assert "--protocol within" in cmds[1][1]
  assert all("--protocol loso" in r for _, r in cmds[2:])


def test_every_command_parses_with_the_real_parser(nb):
  for _, rest in _gnn_commands(nb):
    _parse(rest)


def test_no_pip_requirements_in_section(nb):
  text = "\n".join(c.source for c in _section(nb))
  assert "pip install" not in text and "requirements" not in text


def test_within_cell_is_pooled_both_variants_three_seeds(nb):
  a = _parse(_gnn_commands(nb)[1][1])
  assert a.protocol == "within" and a.norm == ["pooled"] and a.variants == ["nodes+F", "nodes+coh+F"] and a.seeds == 3


def test_each_loso_cell_has_one_variant_and_one_norm(nb):
  seen = set()
  for _, rest in _gnn_commands(nb)[2:]:
    a = _parse(rest)
    assert len(a.variants) == 1 and len(a.norm) == 1
    seen.add((a.variants[0], a.norm[0]))
    assert a.seeds == 3
  assert seen == {(v, n) for v in ("nodes+F", "nodes+coh+F") for n in ("pooled", "subject")}


def test_threads_device_fixed_and_own_out_dirs(nb):
  cmds = _gnn_commands(nb)
  for _, rest in cmds[1:]:
    a = _parse(rest)
    assert a.threads == 2 and a.device == "cpu"
  loso_dirs = {re.search(r"--out-dir (\S+)", r).group(1) for _, r in cmds[2:]}
  assert loso_dirs == {"{GNN_LOSO_OUT}"}
  assert "--out-dir {GNN_WITHIN_OUT}" in cmds[1][1]
  # smoke test never writes under reports/
  assert "--out-dir" not in cmds[0][1]
  settings = "\n".join(c.source for c in _section(nb) if c.cell_type == "code")
  assert 'GNN_LOSO_OUT = "reports/' in settings and 'GNN_WITHIN_OUT = "reports/' in settings
  assert "GNN_LOSO_OUT != LOSO_OUT" in settings and "GNN_WITHIN_OUT != WITHIN_OUT" in settings
