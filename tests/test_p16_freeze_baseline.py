"""P16.1 freeze_baseline on a temporary tree: copy, read-only, refusal, MANIFEST hashes, superseded, summary."""

import csv
import hashlib
import json
import os
import subprocess

import numpy as np
import pytest

from scripts import freeze_baseline as fb


def _git(root, *a):
  subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)


@pytest.fixture
def tree(tmp_path):
  r = tmp_path
  (r / "data/processed/S01").mkdir(parents=True)
  np.save(r / "data/processed/S01/X_time_windows.npy", np.zeros((4, 7, 256)))
  np.save(r / "data/processed/S01/y_labels.npy", np.array([101, 102, 103, 104]))
  (r / "reports").mkdir()
  (r / "reports/n_subjects_benchmark.csv").write_text(
    "Subject,Channels Kept,Channels Dropped,Clean Windows,Rejected Windows,1.0s Acc (%),2.0s Smoothed (%)\n"
    "S01,7,none,200,0,60.0,70.0\nS02,7,none,196,3,50.0,60.0\n")
  (r / "reports/five_subjects_benchmark.csv").write_text("Subject,Clean Windows\nS01,200\n")
  (r / "reports/gnn_benchmark.csv").write_text(
    "variant,repeat,acc_1s,acc_2s,train_acc,subject\nnodes,0,30,40,70,S01\nnodes,1,40,50,80,S01\n")
  (r / "outputs/reports").mkdir(parents=True)
  (r / "outputs/reports/x.csv").write_text("a\n1\n")
  (r / "configs").mkdir()
  (r / "configs/pipeline_config.yaml").write_text("v: 1\n")
  _git(r, "init", "-q", "-b", "main")
  _git(r, "-c", "user.email=a@b", "-c", "user.name=t", "add", "configs")
  _git(r, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "v1 config")
  (r / "configs/pipeline_config.yaml").write_text("v: 2\n")   # the working tree has moved on
  return r


def test_freeze_known_answers(tree):
  snap = fb.freeze(tree, "v1", "note", date="2026-10-27", with_pip=False)
  assert snap.name == "v1_2026-10-27"
  # copies, same relative paths
  assert (snap / "data/processed/S01/X_time_windows.npy").is_file()
  assert (snap / "outputs/reports/x.csv").is_file()
  # configs come from git at the merge-base (v1), not the working tree
  assert (snap / "configs/pipeline_config.yaml").read_text().strip() == "v: 1"
  # superseded
  assert (snap / "superseded/five_subjects_benchmark.csv").is_file()
  assert not (snap / "reports/five_subjects_benchmark.csv").exists()
  man = json.loads((snap / "MANIFEST.json").read_text())
  by = {e["path"]: e for e in man["files"]}
  e = by["reports/five_subjects_benchmark.csv"]
  assert e["stored_as"] == "superseded/five_subjects_benchmark.csv"
  # sha256 / shape / rows
  raw = (tree / "reports/n_subjects_benchmark.csv").read_bytes()
  assert by["reports/n_subjects_benchmark.csv"]["sha256"] == hashlib.sha256(raw).hexdigest()
  assert by["reports/n_subjects_benchmark.csv"]["rows"] == 2
  assert by["data/processed/S01/X_time_windows.npy"]["shape"] == [4, 7, 256]
  assert by["configs/pipeline_config.yaml"]["from_git_commit"] == man["configs_from_commit"]
  assert man["channel_audit"]["S01"]["n_channels"] == 7
  assert man["git_dirty"] is True            # the config edit is uncommitted
  assert "commit" not in man or man["git_commit"]
  # summary: long format with MEAN rows
  rows = list(csv.DictReader(open(snap / "baseline_summary.csv")))
  assert list(rows[0]) == ["pipeline", "subject", "metric", "value"]
  d = {(r["pipeline"], r["subject"], r["metric"]): float(r["value"]) for r in rows}
  assert d[("flagship_n_subjects", "S01", "1.0s Acc (%)")] == 60.0
  assert d[("flagship_n_subjects", "MEAN", "1.0s Acc (%)")] == 55.0
  assert d[("gnn_nodes", "S01", "acc_1s_mean_over_repeats")] == 35.0


def test_read_only_and_refuses_second_run(tree):
  snap = fb.freeze(tree, "v1", "", date="2026-10-27", with_pip=False)
  if os.geteuid() != 0:   # root ignores permission bits
    for p in snap.rglob("*"):
      assert not (p.stat().st_mode & 0o222), p
    with pytest.raises(PermissionError):
      (snap / "MANIFEST.json").write_text("x")
  before = sorted((p.relative_to(snap).as_posix(), p.stat().st_size) for p in snap.rglob("*") if p.is_file())
  rc = fb.main(["--root", str(tree), "--tag", "v1", "--date", "2030-01-01"])
  assert rc == 1                                           # same tag, another date: still refused
  assert not (tree / "baselines/v1_2030-01-01").exists()
  after = sorted((p.relative_to(snap).as_posix(), p.stat().st_size) for p in snap.rglob("*") if p.is_file())
  assert before == after


def test_failed_freeze_leaves_no_snapshot(tree, monkeypatch):
  monkeypatch.setattr(fb, "summary_rows", lambda s: (_ for _ in ()).throw(RuntimeError("boom")))
  with pytest.raises(RuntimeError):
    fb.freeze(tree, "v1", "", date="2026-10-27", with_pip=False)
  assert fb.existing_snapshots(tree, "v1") == []
