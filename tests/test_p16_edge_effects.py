"""P16.3 edge-effect demo: error definition, edge/centre split and the table on a fake recording (PF-14)."""

import csv

import numpy as np
import pytest

from scripts.diagnostics import demo_edge_effects as D
from tests import p16_synth as S

FS = 256.0


def test_relative_error_and_edge_centre_known_answer():
  """cont = unit-RMS square; pw = cont + 0.5 on the first and last 26 samples only: error 0.5 at edges, 0 centre."""
  cont = np.ones((4, 1, 2, 256))
  pw = cont.copy()
  pw[..., :26] += 0.5
  pw[..., -26:] += 0.5
  err = D.relative_error(pw, cont)
  assert err[0, 0, 0, 0] == pytest.approx(0.5) and err[0, 0, 0, 100] == 0
  edges, centre = D.edge_centre(err, FS)
  assert edges[0] == pytest.approx(0.5, abs=1e-12) and centre[0] == 0
  rows = D.summary_rows("S99", {"fbcsp": err}, {"fbcsp": [type("F", (), {"low": 13.0, "high": 17.0})()]}, FS)
  assert rows[0]["band"] == "13-17" and rows[0]["rel_error_edges_pct"] == pytest.approx(50.0)
  assert np.isnan(rows[0]["edge_to_centre_ratio"])                      # centre 0 -> ratio undefined, not inf
  with pytest.raises(ValueError):
    D.relative_error(pw, cont[:2])
  with pytest.raises(ValueError):
    D.edge_centre(err[..., :60], FS)


def test_demo_on_fake_recording_edges_exceed_centre_for_narrow_band(tmp_path, capsys):
  S.write_raw_subject(tmp_path / "raw", "S03", n_trials=10, seed=3)
  rc = D.main(["--subject", "S03", "--raw-dir", str(tmp_path / "raw"), "--reports-dir", str(tmp_path / "rep"),
               "--figures-dir", str(tmp_path / "fig")])
  assert rc == 0
  rows = list(csv.DictReader(open(tmp_path / "rep" / "edge_effects_summary.csv")))
  assert list(rows[0]) == D.COLUMNS and len(rows) == 5 + 3
  narrow = [r for r in rows if r["filter"] == "fbcsp" and r["band"] == "13-17"][0]
  assert float(narrow["edge_to_centre_ratio"]) > 3.0                     # PF-14: edges are the damaged part
  assert float(narrow["rel_error_edges_pct"]) > float(narrow["rel_error_centre_pct"])
  assert (tmp_path / "fig" / "edge_effects" / "edge_effects_S03.png").stat().st_size > 5000
  assert "[-] Skipping" not in capsys.readouterr().out


def test_missing_subject_is_skipped_not_fatal(tmp_path, capsys):
  (tmp_path / "raw" / "S09").mkdir(parents=True)
  assert D.main(["--subject", "S09", "--raw-dir", str(tmp_path / "raw"), "--reports-dir", str(tmp_path / "r"),
                 "--figures-dir", str(tmp_path / "f")]) == 1
  assert "[-] Skipping S09" in capsys.readouterr().out
