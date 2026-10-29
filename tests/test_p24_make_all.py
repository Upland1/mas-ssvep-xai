"""P24: the Makefile (`make all`, p00 ... p23, loso-all) lists only commands the real argparse parsers accept.

Nothing here runs a pipeline command: `make -n` prints the recipes and the parsers are called on the printed
arguments (`parse_args` only). Checks:
  1. every phase target p00 ... p23 and `loso-all` lists commands; `all` is exactly the phase targets in order;
  2. every `python -m scripts...` command parses against the script's own parser;
  3. every command of a script that would discover subjects names them (`--subjects`), except the
     documented exemptions (`--compare`, `--summary-only`, `--smoke-test`, and the `loso-all` target);
  4. every command of a script that reads recordings carries `--raw-dir <RAW_DIR>`, and every script that reads
     recordings has that option;
  5. every out-dir / out-root / out-suffix / data-root quoted in the phase run records is produced by some target;
  6. `PYTHON` and `RAW_DIR` are overridable, and a dry run writes no stamp.
"""
import argparse
import contextlib
import importlib
import io
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASES = [f"p{i:02d}" for i in range(24)]
FAKE_PY = "fakepython"
FAKE_RAW = "FAKE_RAW_DIR"
SUBJECT_COHORT = ["S01", "S02", "S03", "S04", "S05"]

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")


def make_listing(target: str, extra=()) -> list:
  """Lines `make -n <target>` prints (the recipes), with the sentinel PYTHON and RAW_DIR."""
  cmd = ["make", "-n", "--no-print-directory", target, f"PYTHON={FAKE_PY}", f"RAW_DIR={FAKE_RAW}", *extra]
  out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
  return [ln for ln in out.stdout.splitlines() if ln.strip()]


@pytest.fixture(scope="module")
def listings(tmp_path_factory):
  stamps = tmp_path_factory.mktemp("stamps") / "s"
  extra = (f"STAMPS={stamps}",)
  data = {t: make_listing(t, extra) for t in PHASES + ["loso-all", "all"]}
  assert not stamps.exists(), "a dry run of `make all` must not write stamps"
  return data


def script_commands(lines):
  """[(module, [args])] for every `<python> -m scripts.<module> args...` on the printed lines."""
  found = []
  for ln in lines:
    lex = shlex.shlex(ln, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
    for i, t in enumerate(toks[:-1]):
      if t == "-m" and toks[i + 1].startswith("scripts."):
        args = []
        for a in toks[i + 2:]:
          if a in (";", "&&", "||", "|", ">", ">>", "2>", "&"):
            break
          args.append(a)
        found.append((toks[i + 1], args))
  return found


class _Parsed(Exception):
  def __init__(self, parser, ns):
    self.parser, self.ns = parser, ns


_PARSERS = {}


def parser_of(module: str):
  """The module's argparse parser: `build_parser()` when it has one, else captured from `main(argv)`."""
  if module in _PARSERS:
    return _PARSERS[module]
  mod = importlib.import_module(module)
  if hasattr(mod, "build_parser"):
    parser = mod.build_parser()
  else:
    real = argparse.ArgumentParser.parse_args

    def capture(self, args=None, namespace=None):
      raise _Parsed(self, None)
    argparse.ArgumentParser.parse_args = capture
    try:
      mod.main([])
      raise AssertionError(f"{module}: main([]) never reached parse_args")
    except _Parsed as got:
      parser = got.parser
    finally:
      argparse.ArgumentParser.parse_args = real
  _PARSERS[module] = parser
  return parser


def parse(module: str, args):
  parser = parser_of(module)
  err = io.StringIO()
  try:
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
      return parser, parser.parse_args(args)
  except SystemExit:
    pytest.fail(f"{module} {' '.join(args)}\n  rejected by its parser: {err.getvalue().strip()}")


def action(parser, flag):
  for a in parser._actions:
    if flag in a.option_strings:
      return a
  return None


def discovers_subjects(parser, ns) -> bool:
  """True if, with this namespace, the script would pick its subjects by discovery instead of the command line."""
  all_a = action(parser, "--all")
  if all_a is not None:
    return bool(getattr(ns, "all", False))
  subs = action(parser, "--subjects")
  if subs is None:
    return False
  one = action(parser, "--subject")
  if one is not None and one.default not in (None, [], ()):
    return False   # a default single subject, not a discovery
  chosen = getattr(ns, "subjects", None)
  return chosen in (None, [])


EXEMPT_FLAGS = ("--compare", "--summary-only", "--smoke-test")


def test_all_targets_list_commands(listings):
  for t in PHASES + ["loso-all"]:
    assert script_commands(listings[t]) or any(ln.startswith(("ls ", "cmp ")) for ln in listings[t]), t


def test_all_is_the_phase_targets_in_order(listings):
  expected = [ln for t in PHASES for ln in listings[t]]
  assert len(expected) > 100
  got = [ln for ln in listings["all"][listings["all"].index(next(l for l in listings["all"] if l.startswith("=== p00"))):]
         if not ln.startswith("=== ")]
  assert got == expected
  heads = [ln.split()[1] for ln in listings["all"] if ln.startswith("=== ")]
  assert heads == PHASES


def out_values(lines) -> set:
  return {val.rstrip("./") for ln in lines for _, val in VALUE.findall(ln)}


def test_loso_all_stays_outside_all(listings):
  in_all = out_values(listings["all"])
  in_loso_all = out_values(listings["loso-all"])
  for out in ("reports/loso_w1", "reports/loso_w1_all", "reports/loso_w1_fbcca_all", "reports/window_sweep_w1_all"):
    assert out in in_loso_all and out not in in_all, out
  # the 39-subject networks are not run anywhere
  assert not any("ccnn" in ln or "eegnet" in ln for ln in listings["loso-all"])


def test_every_command_parses_against_its_parser(listings):
  n = 0
  for t in PHASES + ["loso-all"]:
    for module, args in script_commands(listings[t]):
      parse(module, args)
      n += 1
  assert n > 120


def test_python_is_overridable(listings):
  for t in PHASES + ["loso-all"]:
    for ln in listings[t]:
      if "-m scripts." in ln:
        assert FAKE_PY in ln, (t, ln)
        assert ".venv/bin/python" not in ln


def test_subjects_are_explicit_wherever_a_script_discovers_them(listings):
  seen = 0
  for t in PHASES:
    for ln in listings[t]:
      for module, args in script_commands([ln]):
        if any(f in args for f in EXEMPT_FLAGS):
          continue
        parser, ns = parse(module, args)
        assert not discovers_subjects(parser, ns), f"{t}: {module} discovers subjects: {ln}"
        seen += 1
        chosen = getattr(ns, "subjects", None)
        if chosen and action(parser, "--subjects").default in (None, []):
          assert set(chosen) <= set(SUBJECT_COHORT), (t, module, chosen)
  assert seen > 100
  # the optional target discovers on purpose: at least one of its commands really does
  assert any(discovers_subjects(*parse(m, a)) for m, a in script_commands(listings["loso-all"]))


def test_raw_dir_is_passed_to_every_command_that_reads_recordings(listings):
  readers = set()
  for t in PHASES + ["loso-all"]:
    for module, args in script_commands(listings[t]):
      parser, ns = parse(module, args)
      if action(parser, "--raw-dir") is not None:
        readers.add(module)
        assert str(ns.raw_dir) == FAKE_RAW, f"{t}: {module} does not receive RAW_DIR"
  assert {"scripts.exploration.inventory_raw", "scripts.preprocessing.run_preprocessing", "scripts.build_windows",
          "scripts.diagnostics.demo_edge_effects", "scripts.benchmarks.pseudo_online",
          "scripts.training.batch_run_subjects"} <= readers


def test_every_script_that_opens_a_recording_has_a_raw_dir_option():
  pat = re.compile(r"resolve_recording_path|load_ebr_file|read_ebr")
  for path in sorted((ROOT / "scripts").rglob("*.py")):
    if path.name == "__init__.py" or not pat.search(path.read_text()):
      continue
    module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
    assert action(parser_of(module), "--raw-dir") is not None, f"{module} reads recordings but has no --raw-dir"


OPTS = ("out-dir", "out-root", "processed-dir", "data-root", "out-suffix")
VALUE = re.compile(r"--(%s)[ =]+[\"'`]?([A-Za-z0-9_./-]+)" % "|".join(OPTS))


def quoted_outputs():
  """{(option, value)} quoted in the phase run records and reports (placeholders and scratch folders left out)."""
  files = sorted((ROOT / "mas/state/phases").glob("P*/05_run.md")) + sorted((ROOT / "mas/state/reports").glob("P*.md"))
  got = set()
  for f in files:
    for opt, val in VALUE.findall(f.read_text()):
      val = val.rstrip("./")
      if not val or val.startswith("-") or val in ("OUT", "D") or val.startswith("mas/state/scratch"):
        continue
      got.add((opt, val))
  return got


def test_every_output_dir_quoted_in_the_phase_records_is_produced_by_a_target(listings):
  if not (ROOT / "mas/state/reports/P23.md").is_file():
    pytest.skip("phase records are not in this checkout")
  produced = set()
  for t in PHASES + ["loso-all"]:
    for ln in listings[t]:
      for opt, val in VALUE.findall(ln):
        produced.add((opt, val.rstrip("./")))
  quoted = quoted_outputs()
  assert len(quoted) > 40
  missing = []
  for opt, val in sorted(quoted):
    if (opt, val) in produced:
      continue
    if opt == "out-suffix" and any(o == opt and v.startswith(val) for o, v in produced):
      continue   # e.g. diagA2_rs (+ the seed) in P13
    missing.append((opt, val))
  assert not missing, f"quoted in the phase records but in no target: {missing}"


def test_dry_run_of_all_writes_no_stamp(tmp_path):
  stamps = tmp_path / "st"
  out = subprocess.run(["make", "-n", "--no-print-directory", "all", f"STAMPS={stamps}", f"PYTHON={FAKE_PY}"],
                       cwd=ROOT, capture_output=True, text=True, check=True).stdout
  assert "=== p23" in out and not stamps.exists()


def test_help_and_phase_aliases_exist():
  out = subprocess.run(["make", "help"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
  assert "make all" in out and "RAW_DIR" in out
  for alias in ("inventory", "preprocess", "explore"):
    subprocess.run(["make", "-n", alias, f"PYTHON={FAKE_PY}"], cwd=ROOT, capture_output=True, text=True, check=True)


def test_the_checks_themselves_catch_the_failures_they_guard_against():
  # a command that omits --subjects on a discovering script is flagged; with it, not
  parser, ns = parse("scripts.build_windows", ["--filter-mode", "continuous"])
  assert discovers_subjects(parser, ns)
  parser, ns = parse("scripts.build_windows", ["--subjects", "S01"])
  assert not discovers_subjects(parser, ns)
  parser, ns = parse("scripts.preprocessing.run_preprocessing", ["--all"])
  assert discovers_subjects(parser, ns)
  # a script with a default single subject does not discover
  parser, ns = parse("scripts.benchmarks.neural_networks.benchmark_eegnet", [])
  assert not discovers_subjects(parser, ns)
  # an unknown flag is rejected by the real parser, and a missing --raw-dir shows as the default (None)
  with pytest.raises(pytest.fail.Exception):
    parse("scripts.build_windows", ["--no-such-flag"])
  _, ns = parse("scripts.build_windows", ["--subjects", "S01"])
  assert ns.raw_dir is None


def test_all_writes_a_stamp_per_finished_phase_and_skips_it_next_time(tmp_path):
  """Real (not dry) run of one harmless phase with `true` as the interpreter: stamp, skip, FORCE."""
  stamps = tmp_path / "st"
  base = ["make", "--no-print-directory", "all", "PHASES=p09", "PYTHON=true", f"STAMPS={stamps}"]
  first = subprocess.run(base, cwd=ROOT, capture_output=True, text=True, check=True).stdout
  assert "=== p09" in first and (stamps / "p09.done").read_text().strip().endswith(" s")
  second = subprocess.run(base, cwd=ROOT, capture_output=True, text=True, check=True).stdout
  assert "[skip] p09" in second and "=== p09" not in second
  forced = subprocess.run(base + ["FORCE=1"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
  assert "=== p09" in forced


# --- Era-A defaults (review F1-F3) -------------------------------------------------------------

ERA_A = ["p04", "p05", "p06", "p07", "p08", "p09", "p10"]


def test_era_a_commands_of_scripts_with_a_cv_option_pass_cv_legacy_and_mod5(listings):
  """Since P11 the default is --cv grouped; P05-P10 recorded the leaky protocol, so each command must say so."""
  n = 0
  for t in ERA_A:
    for module, args in script_commands(listings[t]):
      parser, ns = parse(module, args)
      if action(parser, "--cv") is None:
        continue
      n += 1
      assert ns.cv == "legacy" and "--cv" in args, f"{t}: {module} runs with cv={ns.cv}"
      assert ns.smoothing == "mod5" and "--smoothing" in args, f"{t}: {module} smoothing {ns.smoothing}"
  assert n == 17   # p05 8, p06 2, p07 1, p08 1, p09 2, p10 3


def test_freeze_legacy_implies_cv_legacy_in_every_command(listings):
  seen = 0
  for t in PHASES:
    for module, args in script_commands(listings[t]):
      parser, ns = parse(module, args)
      if action(parser, "--freeze-legacy") is not None and ns.freeze_legacy:
        seen += 1
        assert ns.cv == "legacy", f"{t}: --freeze-legacy without --cv legacy ({module})"
  assert seen == 3


def test_p10_commands_pass_the_scripts_own_post_parse_validation(listings, tmp_path):
  """main() up to the data-loading step: `parser.error` (SystemExit 2) must not fire; the empty folders then end it."""
  seen = 0
  for module, args in script_commands(listings["p10"]):
    mod = importlib.import_module(module)
    args = [a for a in args]
    args += ["--processed-dir", str(tmp_path / "none"), "--reports-dir", str(tmp_path / "rep")]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
      try:
        mod.main(args)
      except SystemExit as exc:
        assert exc.code != 2, f"{module}: rejected by its own validation"
      except Exception:   # noqa: BLE001 - missing data after validation is the expected end here
        pass
    seen += 1
  assert seen == 3


def test_builds_of_p16_and_p17_pin_quality_source_and_banks(listings):
  """The config default became `both` in P19; P16/P17 were built on the filtered gate."""
  for t in ("p16", "p17"):
    for module, args in script_commands(listings[t]):
      if module == "scripts.build_windows":
        _, ns = parse(module, args)
        assert ns.quality_source == "filtered" and "--quality-source" in args, t
        assert ns.banks is not None, t


def test_final_regression_check_is_not_silenced(listings):
  for t in PHASES:
    for ln in listings[t]:
      if "compare_v1_v2 --check-regression" in ln:
        assert not ln.startswith("-")
  text = (ROOT / "Makefile").read_text()
  assert not re.search(r"^\t-.*check-regression", text, re.M)
