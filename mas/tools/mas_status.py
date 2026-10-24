"""Phase bookkeeping for the multi-agent rebuild (see mas/README.md §5).

Usage:
  python mas/tools/mas_status.py check
  python mas/tools/mas_status.py init
  python mas/tools/mas_status.py next
  python mas/tools/mas_status.py open Pxx
  python mas/tools/mas_status.py set Pxx {pending,in_progress,blocked,passed} [--commit SHA]
  python mas/tools/mas_status.py show
"""

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

MAS = Path(__file__).resolve().parents[1]
STATE = MAS / "state"
STATUS_FILE = STATE / "phase_status.yaml"
SPEC_FILES = ["01_DATA_SPEC.md", "02_REQUIREMENTS.md", "03_ROADMAP.md", "04_REFERENCE_RESULTS.md",
              "05_PITFALLS.md", "06_AGENT_ROLES.md", "RULES.md", "CITING.md", "phases.yaml"]
STATUSES = ("pending", "in_progress", "blocked", "passed")
SHARED_TEMPLATES = ["00_assignment.md", "01_brief.md", "02_plan.md", "04_tests.md", "05_run.md",
                    "06_verify.md", "07_review.md", "log.md"]


def die(msg: str) -> None:
  print(f"error: {msg}", file=sys.stderr)
  sys.exit(1)


def load_yaml(path: Path) -> dict:
  return yaml.safe_load(path.read_text()) or {}


def team() -> dict:
  return load_yaml(STATE / "team.yaml")


def phases() -> list[dict]:
  """Spec phases (mas/phases.yaml) merged with the team data (state/team.yaml).

  depends_on is the union of phases.yaml and the roadmap, so a dependency
  stated in either source is honoured.
  """
  tm = team()
  road = roadmap_phases()
  out = []
  for p in load_yaml(MAS / "phases.yaml")["phases"]:
    extra = tm["phases"].get(p["id"])
    if extra is None:
      die(f"{p['id']} has no entry in state/team.yaml")
    unknown = [o for o in p["owners"] if o not in tm["roles"]]
    if unknown:
      die(f"{p['id']}: roles {unknown} are not mapped in state/team.yaml")
    owners = list(dict.fromkeys(tm["roles"][o] for o in p["owners"]))
    builders = [a for a in owners if a not in tm["checkers"]]
    agents = list(dict.fromkeys(owners + tm["always"]))
    deps = sorted(set(p["depends_on"]) | set(road.get(p["id"], {}).get("depends_on", [])))
    out.append({**p, **extra, "agents": agents, "builders": builders, "depends_on": deps,
                "spec_depends_on": p["depends_on"]})
  return out


def config() -> dict:
  return load_yaml(STATE / "config.yaml")


def status() -> dict:
  if not STATUS_FILE.exists():
    die("state/phase_status.yaml does not exist; run `init` (P00 task 1)")
  return load_yaml(STATUS_FILE)


def save_status(st: dict) -> None:
  STATUS_FILE.write_text(yaml.safe_dump(st, sort_keys=False))


def roadmap_phases() -> dict[str, dict]:
  """Title and dependencies of each phase, parsed from 03_ROADMAP.md."""
  text = (MAS / "03_ROADMAP.md").read_text()
  out = {}
  blocks = re.split(r"^### (P\d\d) — ", text, flags=re.M)
  for pid, body in zip(blocks[1::2], blocks[2::2]):
    title = body.splitlines()[0].strip()
    dep = re.search(r"\*\*Depends on:\*\*(.*?)\*\*Owners", body, flags=re.S)
    # "P16 (uses the P13/P14 machinery)": parentheticals are notes, not dependencies
    deps = re.findall(r"P\d\d", re.sub(r"\(.*?\)", "", dep.group(1), flags=re.S)) if dep else []
    out[pid] = {"title": title, "depends_on": sorted(set(deps))}
  return out


def open_blockers() -> list[tuple[str, str]]:
  found = []
  for f in sorted((STATE / "blockers").glob("*.md")):
    text = f.read_text()
    state = re.search(r"^- Status:\s*(\w+)", text, flags=re.M)
    scope = re.search(r"^- blocking:\s*(.+)$", text, flags=re.M)
    if state and state.group(1) == "open":
      found.append((f.name, scope.group(1).strip() if scope else "all"))
  return found


def blocked_by(pid: str) -> list[str]:
  hits = []
  for name, scope in open_blockers():
    words = scope.split("(")[0]
    if words.strip().startswith("all") or pid in re.findall(r"P\d\d", words):
      hits.append(name)
  return hits


def cmd_check(_args) -> None:
  ok = True
  missing = [f for f in SPEC_FILES if not (MAS / f).exists()]
  for f in missing:
    print(f"MISSING  mas/{f}")
  ok &= not missing
  road = roadmap_phases()
  for p in phases():
    r = road.get(p["id"])
    if r is None:
      print(f"MISMATCH {p['id']} is in phases.yaml but not in 03_ROADMAP.md")
      ok = False
    elif sorted(r["depends_on"]) != sorted(p["spec_depends_on"]):
      print(f"NOTE     {p['id']} depends_on: phases.yaml {p['spec_depends_on']} vs roadmap "
            f"{r['depends_on']}; using the union {p['depends_on']}")
  extra = set(road) - {p["id"] for p in phases()}
  for pid in sorted(extra):
    print(f"MISMATCH {pid} is in 03_ROADMAP.md but not in phases.yaml")
    ok = False
  for name, scope in open_blockers():
    print(f"BLOCKER  {name} (blocking: {scope})")
  cfg = config()
  print(f"config   REFERENCE_POLICY={cfg.get('REFERENCE_POLICY')} SCHEDULING={cfg.get('SCHEDULING')} "
        f"PLAN_APPROVAL={cfg.get('PLAN_APPROVAL')} MERGE_POLICY={cfg.get('MERGE_POLICY')}")
  print(f"phases   {len(phases())} in phases.yaml, {len(road)} in roadmap")
  print("OK" if ok else "NOT READY")
  sys.exit(0 if ok else 1)


def cmd_init(_args) -> None:
  if STATUS_FILE.exists():
    die("state/phase_status.yaml already exists; refusing to overwrite")
  st = {"phases": {p["id"]: {"slug": p["slug"], "status": "pending", "owner": "orchestrator",
                             "branch": None, "commit": None, "opened": None, "passed": None}
                   for p in phases()}}
  save_status(st)
  print(f"wrote {STATUS_FILE.relative_to(MAS.parent)} with {len(st['phases'])} pending phases")


def eligible(pid: str, st: dict) -> list[str]:
  """Reasons why `pid` cannot be opened now (empty = allowed)."""
  by_id = {p["id"]: p for p in phases()}
  if pid not in by_id:
    return [f"unknown phase {pid}"]
  entries = st["phases"]
  reasons = []
  if entries[pid]["status"] != "pending":
    reasons.append(f"{pid} is {entries[pid]['status']}")
  for dep in by_id[pid]["depends_on"]:
    if entries[dep]["status"] != "passed":
      reasons.append(f"dependency {dep} is {entries[dep]['status']}")
  if config().get("SCHEDULING", "sequential") == "sequential":
    for p in phases():
      if p["id"] < pid and entries[p["id"]]["status"] != "passed":
        reasons.append(f"sequential scheduling: {p['id']} is {entries[p['id']]['status']}")
        break
  reasons += [f"open blocker {b}" for b in blocked_by(pid)]
  return reasons


def cmd_next(_args) -> None:
  st = status()
  for p in phases():
    if st["phases"][p["id"]]["status"] == "in_progress":
      print(f"{p['id']} is in progress")
  for p in phases():
    if not eligible(p["id"], st):
      print(f"next: {p['id']} {p['slug']}")
      return
  pending = [p["id"] for p in phases() if st["phases"][p["id"]]["status"] == "pending"]
  if not pending:
    print("all phases passed")
    return
  first = pending[0]
  print(f"no phase can open; {first} is waiting on: " + "; ".join(eligible(first, st)))


def fill(text: str, pid: str, slug: str, title: str) -> str:
  return (text.replace("Pxx-<slug>", f"{pid}-{slug}").replace("Pxx", pid)
          .replace("<title>", title).replace("<slug>", slug))


def cmd_open(args) -> None:
  pid = args.phase.upper()
  st = status()
  reasons = eligible(pid, st)
  if reasons:
    die(f"cannot open {pid}: " + "; ".join(reasons))
  p = next(p for p in phases() if p["id"] == pid)
  title = roadmap_phases()[pid]["title"]
  folder = STATE / "phases" / f"{pid}-{p['slug']}"
  if folder.exists():
    die(f"{folder.relative_to(MAS.parent)} already exists")
  folder.mkdir(parents=True)
  tpl = MAS / "templates" / "phase"
  for name in SHARED_TEMPLATES:
    (folder / name).write_text(fill((tpl / name).read_text(), pid, p["slug"], title))
  for agent in p["builders"]:
    text = fill((tpl / "03_changes.md").read_text(), pid, p["slug"], title).replace("<agent>", agent)
    (folder / f"03_changes_{agent}.md").write_text(text)
  entry = st["phases"][pid]
  entry.update(status="in_progress", branch=f"phase/{pid}-{p['slug']}", opened=str(dt.date.today()))
  save_status(st)
  print(f"opened {pid} — {title}")
  print(f"folder  {folder.relative_to(MAS.parent)}")
  print(f"branch  {entry['branch']}")
  print(f"builders {', '.join(p['builders']) or 'none'}; legacy: {', '.join(p['legacy']) or 'none'}")


def verdict(path: Path, pattern: str) -> bool:
  return path.exists() and re.search(pattern, path.read_text(), flags=re.M) is not None


def cmd_set(args) -> None:
  pid = args.phase.upper()
  st = status()
  if pid not in st["phases"]:
    die(f"unknown phase {pid}")
  entry = st["phases"][pid]
  if args.status == "passed":
    folder = STATE / "phases" / f"{pid}-{entry['slug']}"
    missing = []
    if not verdict(folder / "06_verify.md", r"^Verdict:\s*PASS\s*$"):
      missing.append("06_verify.md has no 'Verdict: PASS'")
    if not verdict(folder / "07_review.md", r"^Verdict:\s*APPROVE\s*$"):
      missing.append("07_review.md has no 'Verdict: APPROVE'")
    if not (STATE / "reports" / f"{pid}.md").exists():
      missing.append(f"state/reports/{pid}.md does not exist")
    if blocked_by(pid):
      missing.append("open blockers: " + ", ".join(blocked_by(pid)))
    if not args.commit:
      missing.append("--commit is required")
    if missing:
      die(f"gate for {pid} not met: " + "; ".join(missing))
    entry["passed"] = str(dt.date.today())
  if args.commit:
    entry["commit"] = args.commit
  entry["status"] = args.status
  save_status(st)
  print(f"{pid} -> {args.status}")


def cmd_show(_args) -> None:
  st = status()
  print(f"{'id':4} {'status':12} {'opened':10} {'passed':10} {'commit':9} slug")
  for p in phases():
    e = st["phases"][p["id"]]
    print(f"{p['id']:4} {e['status']:12} {e['opened'] or '-':10} {e['passed'] or '-':10} "
          f"{(e['commit'] or '-')[:9]:9} {p['slug']}")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  sub = ap.add_subparsers(dest="cmd", required=True)
  for name, fn in (("check", cmd_check), ("init", cmd_init), ("next", cmd_next), ("show", cmd_show)):
    sub.add_parser(name).set_defaults(fn=fn)
  op = sub.add_parser("open")
  op.add_argument("phase")
  op.set_defaults(fn=cmd_open)
  sp = sub.add_parser("set")
  sp.add_argument("phase")
  sp.add_argument("status", choices=STATUSES)
  sp.add_argument("--commit")
  sp.set_defaults(fn=cmd_set)
  args = ap.parse_args()
  args.fn(args)


if __name__ == "__main__":
  main()
