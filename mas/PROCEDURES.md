# Procedures per agent kind

Each agent follows the section for its kind, plus the prompts of its roles in
`06_AGENT_ROLES.md`. Every agent starts by reading `AGENTS.md`, `RULES.md`,
`README.md` (this folder), its phase's `00_assignment.md`, and the roadmap,
spec, reference and pitfall sections named there. Everyone writes only its own
file (README §3) and stops with `Status: BLOCKED` rather than guess.

Paths below are relative to the phase folder `mas/state/phases/Pxx-<slug>/`
unless they start with a top-level folder.

## Every agent

- Your first line in your own file's `## Questions` section is
  `ACK <file you started from> <agent> <YYYY-MM-DD>`. Questions for another
  agent also go in your own file, as `to <agent>: …`; the orchestrator relays
  them and the answer is appended under the question.
- Cite as in `CITING.md`; run its checklist before setting `Status: READY`.
- Open `reference/ssvep-eeg-xai/` only as R11 and `REFERENCE_POLICY` allow,
  and list every consultation. Other branches are read with
  `git -C reference/ssvep-eeg-xai show <branch>:<path>`, never by checkout.
- Never touch `data/raw/` or `.ebr` files except by launching project scripts.

## Builder (data-engineer, signal-processing, classical-ml, deep-learning, connectivity-stats, evaluation-lead; scribe for document deliverables)

1. Start only when `02_plan.md` is `Status: READY` (and, with
   `PLAN_APPROVAL: required`, ticked "Approved by Sebastian: [x]").
2. `git status` must show no modified tracked files. Switch to the phase
   branch (`git switch phase/Pxx-<slug>`, or create it from `main` if you
   are the first builder: `git switch -c phase/Pxx-<slug> main`).
3. Implement only your rows of the plan's work split, exactly as the roadmap
   task specifies (signatures, defaults, shapes). Legacy behaviour required by
   the era matrix is implemented as specified, labelled `legacy`, and kept
   reachable behind a flag after any later fix.
4. Write unit tests for your own code in `tests/test_pxx_<topic>.py`
   (the synthetic-tester adds independent known-answer tests afterwards).
   The test hook runs `pytest tests/` after each edit; never loosen a
   tolerance silently.
5. Smoke-test only (synthetic data or one fold/subject, under ~5 minutes).
   Real phase runs belong to the runner.
6. Commit on the phase branch, one logical change per commit, with a
   conventional prefix. Never push; never commit on `main`.
7. Write `03_changes_<agent>.md` and set `Status: READY`. On a fix round, fix
   only the required items from `07_review.md` and append `## Round N`.

## synthetic-tester

1. Start when every `03_changes_*.md` of the phase is `READY`; work on the
   branch they name.
2. Write `tests/test_pxx_<topic>_known_answer.py`: data built inside the
   test with a fixed seed, never from `data/`; the sampling rate the phase
   uses (250 Hz assumed before P16, 256 Hz from P16); realistic shapes.
3. Each test's docstring states its known answer, its tolerance and the
   source of the answer. At least one test per fix fails on the historical
   bug (the PF entry) or on a plausible buggy variant: cross-trial, unsorted,
   wrong axis, no-op, leaked fit. Prove it by running the test against that
   variant (a temporary monkeypatch inside the test file is fine) and say so.
4. Run `python -m pytest tests/ -q`; the whole suite stays under about a
   minute on CPU.
5. Never edit `src/`, `scripts/` or `configs/`. A test that exposes a bug is
   reported in `04_tests.md` with `Status: BLOCKED`.

## runner

1. Start when `07_review.md` has a pre-run audit with `Verdict: PASS`.
2. Check out the phase branch at the commit in the builders' handoffs; the
   tree must be clean.
3. For each command in `02_plan.md` "Run commands": if its expected runtime
   exceeds `LOCAL_RUN_BUDGET_MIN` or it needs GPU hours beyond
   `MAX_GPU_HOURS_PER_PHASE`, do not run it; write a human run request.
   Otherwise run it as
   `{ echo "$ <cmd>"; git rev-parse HEAD; git status --porcelain; python -V; <cmd>; } 2>&1 | tee reports/logs/Pxx/<script>_<timestamp>.log`
   (naming per `02_REQUIREMENTS.md` §4).
4. Never edit code, configs, CSVs or logs. Record exit codes, runtimes and
   produced files in `05_run.md`; do not interpret numbers.
5. With pending human runs, set `Status: BLOCKED` and list exactly what
   Sebastian must run and where to drop the outputs.

## verifier

1. Start when `05_run.md` is `READY`. You never built this phase.
2. Clean checkout: `git worktree add mas/state/scratch/verify/Pxx <commit>`;
   inside it, symlink only what the phase needs from the main checkout
   (`data/`, never by copying recordings), and set up the environment from
   `requirements.txt`.
3. Run `python -m pytest -q`. Re-run every acceptance command that fits the
   budget; for human-run outputs, check that the logs exist and their headers
   show the phase commit.
4. Compare every acceptance criterion and every number in the handoffs with
   the logs and with `04_REFERENCE_RESULTS.md`, applying its tolerance rules.
5. Open at least two cited sources; check every reference consultation has a
   valid R11 trigger and matches `mas/state/scratch/reference_access.log`.
6. Write `06_verify.md` with `Verdict: PASS` or `Verdict: FAIL` and numbered
   reasons. Never fix code. Remove the worktree when done
   (`git worktree remove mas/state/scratch/verify/Pxx`).

## scientific-reviewer

Two passes per phase, both in `07_review.md`.

1. **Pre-run audit** (after `04_tests.md` is `READY`). Read the plan, the
   handoffs and every changed file (the code, not the summary). Start with
   your memory folder of bug patterns. For every rule give PASS / FAIL /
   CONCERN / LEGACY (by design) / N/A with `path:line` evidence you opened.
   FAIL = a rule is broken or a result could be wrong without an error;
   CONCERN = correct but fragile or untested; LEGACY only for a violation the
   era matrix prescribes for this phase. Check the tests against plausible
   buggy variants, not only the one the tester chose. `Verdict: PASS` only
   without FAIL.
2. **Results review** (after `06_verify.md`). Every deviation from an R-x
   reference is explained or rejected; per-subject reading; inconclusive
   results stated as such; leakage in any fitted object, normalization or
   validation set; permutation unit and multiple comparisons.
   `Verdict: APPROVE` or `Verdict: REJECT`; accepted deviations listed for
   `decisions.md`.
3. Record each new bug pattern (one line, rule number, date) in your memory.
   You never edit code or other handoff files.

## scribe

1. Start after both verdicts exist. Write `mas/state/reports/Pxx.md` from
   `templates/PHASE_REPORT.md`, copying numbers from CSVs and logs with their
   paths, and the verdicts of `06_verify.md` and `07_review.md` into §11.
2. Append the phase to `RESEARCH_LOG.md` (story, before/after) and
   `CHANGELOG.md`. In P06 and P24 also write the documents the roadmap
   lists, as a builder with `03_changes_scribe.md`.
3. Concise academic prose; numbers never retyped from memory; arithmetic
   only via a shown Python command.

## literature-scout

Called only when a phase introduces a method new to the team. Write
`01_brief.md` from the template: questions, findings with sources you opened,
reference implementations with licenses and differences from our setup,
options without choosing. Never run code; never open `data/` or `reference/`.
