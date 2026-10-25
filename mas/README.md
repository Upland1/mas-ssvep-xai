# mas/ — Multi-agent system: architecture and handoff contract

This folder holds everything that defines the rebuild, independent of the agent
framework that executes it: the specification (`01`–`06`, `phases.yaml`), the
templates, a small status tool, and the shared state the agents write.

```
mas/
  README.md               this file: team, workflow, handoff contract
  01_DATA_SPEC.md         data format, events, protocol, layouts      (MISSING, see blockers)
  02_REQUIREMENTS.md      invariants, repo layout, config, schemas     (MISSING, see blockers)
  03_ROADMAP.md           26 phases: tasks, run, acceptance
  04_REFERENCE_RESULTS.md R-x reference numbers and tolerances         (MISSING, see blockers)
  05_PITFALLS.md          PF-x known traps and fixes                   (MISSING, see blockers)
  06_AGENT_ROLES.md       the 13 roles and their prompts
  RULES.md                methodological rules R1–R11 and the era matrix
  PROCEDURES.md           step-by-step procedure per agent kind
  ADAPTING.md             how roles were mapped onto the team
  CITING.md               how every agent cites sources (R10)
  phases.yaml             machine-readable phase graph (spec; not edited)
  templates/              phase handoff files, phase report, blocker
  tools/mas_status.py     preflight, phase status, open/close phases
  state/
    config.yaml           human-owned settings (policies, budget)
    team.yaml             role -> agent map, phase slugs, legacy flags
    phase_status.yaml     one entry per phase (created at P00)
    team_mapping.md       role -> agent mapping
    decisions.md          append-only decision log (orchestrator)
    blockers/             open questions for Sebastian
    phases/Pxx-<slug>/    the handoff files of one phase
    reports/Pxx.md        final phase reports (scribe)
    scratch/              git-ignored: clean checkouts, hook logs
```

## 1. Team

The orchestrator is the main session that Sebastian talks to (start or resume
with `/phase`; it runs phases back to back until a hard stop). Every other
member is a subagent with its own instructions, tools and model. From P04 the
13 roles of `06_AGENT_ROLES.md` map to 7 agents plus an added independent
tester (P00–P03 used 11 agents; their handoffs keep those names). See
`state/team_mapping.md`.

| Agent | Roles held | Kind | Model tier | Writes |
|---|---|---|---|---|
| orchestrator (main session) | Orchestrator; research when needed | gate | session | `00_assignment.md`, `01_brief.md`, `02_plan.md`, `log.md`, `phase_status.yaml`, `decisions.md`, blockers |
| data-signal | Data Engineer, Infra, Signal Processing, Online/Real-time | builder | mid | code + `03_changes_data-signal.md` |
| ml-engineer | Classical ML, XAI, Evaluation Lead | builder | mid | code + `03_changes_ml-engineer.md` |
| deep-learning | Deep Learning | builder | mid | code + `03_changes_deep-learning.md` |
| connectivity-stats | Connectivity & Stats | builder | mid | code + `03_changes_connectivity-stats.md` |
| synthetic-tester | (added; independent known-answer tests) | checker | mid | `tests/` + `04_tests.md` |
| verifier | Runner, Verifier | independent executor and checker | mid | `reports/logs/` + `05_run.md` + `06_verify.md` |
| scientific-reviewer | Scientific Reviewer (+ the former methods-auditor) | independent checker | strongest | `07_review.md` |
| scribe | Scribe | writer | light | `reports/Pxx.md`, `RESEARCH_LOG.md`, `CHANGELOG.md`, docs |

Builders whose work fails review twice are re-called on the strongest tier for
their last fix round.

Each agent's procedure is in `PROCEDURES.md`. Independence: builders never verify or review; the verifier, the reviewer and
the tester never edit pipeline code (`src/`, `scripts/`, `configs/`). The
guard hook enforces the write boundaries.

## 2. One phase, end to end

```
 orchestrator  mas_status.py open Pxx ──► state/phases/Pxx-<slug>/00_assignment.md
      │                                   (tasks + acceptance copied verbatim from the roadmap,
      │                                    PF/R entries, owners, branch phase/Pxx-<slug>)
      ├─► orchestrator       01_brief.md (only for methods new to the team), 02_plan.md
      │                      (STOP for Sebastian only if PLAN_APPROVAL: required)
      ├─► builders           code on phase/Pxx-<slug> + 03_changes_<agent>.md
      ├─► synthetic-tester   tests/test_pxx_*.py + 04_tests.md
      ├─► scientific-reviewer 07_review.md  "## Pre-run audit"   (code vs R1–R11, era matrix)
      │        FAIL → builders fix (Round N; round 2 on the strongest tier) → tester → reviewer;
      │        2 failed rounds → blocker
      ├─► verifier           clean checkout → pytest → run commands once → reports/logs/Pxx/
      │                      + 05_run.md → acceptance vs R-x → 06_verify.md
      │        over budget → "human run" request → STOP for Sebastian
      ├─► scientific-reviewer 07_review.md  "## Results review"  (deviations vs R-x, interpretation)
      ├─► scribe             state/reports/Pxx.md, RESEARCH_LOG.md, CHANGELOG.md
      └─► orchestrator gate  PASS: merge/tag per MERGE_POLICY, status passed, decisions.md,
                             next phase if AUTO_CONTINUE: true
                             FAIL: reasons back to builders
```

A phase **passes** only when: every roadmap task is done (or ruled out of scope
by Sebastian in `decisions.md`); `pytest -q` passes on a clean checkout; every
acceptance criterion is met or its deviation is explained and accepted by the
reviewer; `06_verify.md` says PASS; `07_review.md` says APPROVE; the phase
report links the log or CSV behind every number.

## 3. Handoff rules

1. **Write only your own file.** File ownership is in the table above; the
   guard hook blocks writes to another agent's handoff file.
2. **Every handoff file starts with a status line:** `Status: DRAFT`, `READY`
   or `BLOCKED`. The next agent starts only from `READY`. On `BLOCKED`, explain
   why under "Open questions" and stop.
3. **Acknowledge in your own file.** The first line of your file's
   `## Questions` section is `ACK <file you started from> <agent> <date>`.
   Questions for another agent go there too, as `to <agent>: …`; the
   orchestrator relays them and answers are appended, never edited away.
4. **Cite rules by number and every source** (R10): `R1`–`R11`, `PF-x`, `R-x`,
   and the formats in `CITING.md`, with a `## Sources` list at the end.
5. **Evidence over claims.** "Verified" means a command was run and its output
   is summarized. Code claims carry `path:line`.
6. **Fix loop.** On `FAIL`, builders append `## Round N` to their
   `03_changes_*.md`; tester and reviewer append their own `## Round N`. After
   two failed rounds the orchestrator writes a blocker and stops.
7. **Numbers come from runs.** Only the verifier's `05_run.md` (and human-run outputs dropped
   into `reports/logs/Pxx/`) introduce numbers; everyone else copies them
   with the path.
8. **Log every step.** The orchestrator adds one row per agent step to the
   phase's `log.md`: outcome, round, what was caught, sources cited,
   reference consultations (R11), anything that reached a run broken.
9. **Committed, but free of tool names.** `mas/state/` is committed as the
   reproducibility record; never name the agent framework or model vendor in
   it. Agent names are role names.

## 4. Human gates (Sebastian)

| Gate | When | Controlled by |
|---|---|---|
| Plan approval (off by default) | after `02_plan.md` | `PLAN_APPROVAL` (`auto` / `required`) |
| Human run | verifier request over budget or needing Colab | `LOCAL_RUN_BUDGET_MIN`, `MAX_GPU_HOURS_PER_PHASE` |
| Blockers | ambiguous spec, unexplained deviation, missing input | `state/blockers/` |
| Merge to `main` | after a passed gate | `MERGE_POLICY` (`human` / `orchestrator`) |
| Push | always | Sebastian only |

## 5. Status tool

```bash
python mas/tools/mas_status.py check          # preflight: spec files, phase graph, blockers
python mas/tools/mas_status.py init           # create state/phase_status.yaml (P00)
python mas/tools/mas_status.py next           # next phase allowed to open
python mas/tools/mas_status.py open P03       # create state/phases/P03-<slug>/ from templates
python mas/tools/mas_status.py set P03 passed --commit <sha>
python mas/tools/mas_status.py show           # table of all phases
```

`open` refuses a phase whose dependencies have not passed, or (with
`SCHEDULING: sequential`) any phase while a lower-numbered one has not passed,
or any phase while a blocker marked `blocking: all` or `blocking: Pxx` is open.
