# AGENTS.md — Mission brief for the multi-agent system

> Every agent reads this file first, before any other file and before writing any code.
> If you are the **Orchestrator**, you also own `mas/state/` and the phase gates.

## 1. Mission

Rebuild, **from zero**, a complete Python research pipeline for **5-class SSVEP
(Steady-State Visually Evoked Potential) brain-computer interface decoding** from
8-channel parieto-occipital EEG, and walk it through **every research stage the
original project went through**, in the same order, until you reach the project's
latest approach (leave-one-subject-out evaluation of a connectivity graph neural
network).

You are not asked to "get a good model". You are asked to **reproduce a research
history**: build each stage, run it, record its numbers, discover (or deliberately
demonstrate) the problems the original project discovered, fix them the way they
were fixed, and show the before/after. The end state is a repository equivalent in
capability to the original one, plus a reproducible record of how it got there.

Inputs you receive:

| Input | Where | What |
|---|---|---|
| Raw recordings | `data/raw/S01 … S05/*.ebr` (delivered out-of-band, never committed) | binary EEG, see `mas/01_DATA_SPEC.md` |
| Format specification | `mas/01_DATA_SPEC.md` | file format, event codes, protocol, quirks |
| Requirements | `mas/02_REQUIREMENTS.md` | engineering + scientific invariants, layout, output schemas |
| Work plan | `mas/03_ROADMAP.md` + `mas/phases.yaml` | 26 phases, each with tasks and acceptance criteria |
| Reference numbers | `mas/04_REFERENCE_RESULTS.md` | what the original project measured at each stage |
| Known traps | `mas/05_PITFALLS.md` | every bug the original project hit, and its fix |
| Rules | `mas/RULES.md` | methodological rules R1–R11, era matrix |
| Team | `mas/06_AGENT_ROLES.md` + `mas/README.md` | roles, prompts, team, hand-off contract |

## 2. Golden rules (non-negotiable)

1. **Never commit raw or processed data.** `.ebr`, `.npy`, `.npz`, `.pt`, `.joblib`,
   videos, photos, `data/`, `reports/`, `outputs/`, `baselines/` stay git-ignored. The
   recordings are private human-subject data; the repository is public.
2. **Phases run in order.** A phase starts only when every phase it depends on
   (`mas/phases.yaml`) has passed its gate. No skipping ahead "because the final
   version is known".
3. **Historical stages are reproduced, not skipped.** When a phase says *legacy*,
   implement the legacy behavior (e.g. `fs=250` assumption, plain `StratifiedKFold`,
   per-window filtering), freeze its numbers, and only then implement the fix in the
   later phase that introduces it. Every fix must ship with a **before/after table**.
   Legacy behavior must stay reachable behind a flag or a frozen snapshot — never by
   deleting the fix.
4. **No numbers without a run.** Every number in a report comes from a script run
   whose command line, git commit and console log are saved under `reports/logs/`.
   Agents never type, estimate or "round toward" a reference number.
5. **Reference numbers are targets for diagnosis, not for tuning.** If your number
   differs from `mas/04_REFERENCE_RESULTS.md`, investigate and explain the difference
   in the phase report (see the tolerance rules there). Do not tune hyperparameters,
   seeds or thresholds to hit a reference number.
6. **Leakage is a blocking defect.** Anything fitted on data (CSP filters, scalers,
   feature selection, standardization statistics, early-stopping validation sets,
   per-subject normalization statistics in LOSO) is fitted on training data only.
   From phase P11 onward, every split of windows is grouped by trial.
7. **The verifier is independent.** The agent that produced a phase never approves
   it. The Verifier re-runs the acceptance commands from a clean checkout.
8. **Cite every source; use the original code only as an answer key.**
   - Every decision, formula, parameter, architecture, test answer and borrowed code
     pattern cites its source (paper with DOI, documentation with version, code
     example with repo/commit/`path:line`/license, the spec in `mas/`, a rule), using
     `mas/CITING.md`. Each phase report and hand-off ends with
     a numbered `## Sources` list. Agents are encouraged to study code examples
     (the papers' own code, MNE, mne-connectivity, scikit-learn, SciPy, braindecode,
     pyRiemann) and re-implement them; at most a few lines are copied, only under a
     compatible license, marked `# adapted from [n]`.
   - Sebastian's original repository is available read-only at
     `reference/ssvep-eeg-xai/` (git-ignored; never write there). An agent may open it
     **only after its own attempt**: (a) its implementation and synthetic test exist
     and the test fails, or its result deviates from `04_REFERENCE_RESULTS.md` beyond
     tolerance after one investigation round; or (b) to verify a finished, passing
     implementation. Each consultation is listed in the hand-off or phase report
     under "Reference consultations" (trigger, files and lines at the reference
     commit, what was learned, what changed) and counted in the phase report.
     Never copy whole functions or files from it.
   - `REFERENCE_POLICY` in `mas/state/config.yaml` controls this: `after-attempt`
     (default, rule above), `closed` (no access until P25), `open` (anytime).
9. **Small, reviewable commits.** One logical change per commit, on a phase branch
   (`phase/Pxx-<slug>`), merged to `main` only after the gate passes. Commit messages
   use the conventional prefixes `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
10. **When blocked, stop and write it down.** If a requirement is ambiguous or a
    result is inexplicable after a time-boxed investigation, write
    `mas/state/blockers/Pxx-<slug>.md` and escalate to the human operator. Do not
    invent missing specifications.

## 3. Workflow per phase

```
Orchestrator ── opens phase Pxx ──► mas/state/phase_status.yaml (status: in_progress)
     │
     ├─► Builder agent(s)        implement tasks on branch phase/Pxx-*, write unit tests
     ├─► Runner                  executes the phase's run commands, saves logs + CSVs
     ├─► Verifier (independent)  clean checkout → tests → re-run acceptance → compare
     │                            with 04_REFERENCE_RESULTS → PASS / FAIL with reasons
     ├─► Scientific Reviewer     checks leakage, statistics, interpretation
     └─► Scribe                  writes mas/state/reports/Pxx.md from the template,
                                 updates CHANGELOG.md and RESEARCH_LOG.md
Orchestrator ── gate decision ──► merge to main, tag `pxx-done`, open next phase
```

A phase **passes** only when all of the following hold:

- every task in its roadmap entry is done or explicitly marked out of scope by the
  human operator;
- `pytest -q` passes on a clean checkout;
- every acceptance criterion in the roadmap entry is met (or, for numeric targets,
  the deviation is inside tolerance or explained and accepted by the Reviewer);
- the phase report exists and links the logs and CSVs that back every number.

## 4. Shared state (`mas/state/`)

| File | Owner | Content |
|---|---|---|
| `config.yaml` | human operator | `REFERENCE_POLICY`, `DEVICE`, compute budget, which subjects exist |
| `phase_status.yaml` | Orchestrator | one entry per phase: `pending / in_progress / blocked / passed`, owner, commit, date |
| `reports/Pxx.md` | Scribe | phase report (template in `mas/templates/PHASE_REPORT.md`) |
| `phases/Pxx-<slug>/` | one file per agent | the phase's hand-off files (`00_assignment.md` … `07_review.md`, `log.md`; templates in `mas/templates/phase/`, contract in `mas/README.md`). They replace the `handoffs/Pxx-<from>-to-<to>.md` notes and preserve their content (see `team_mapping.md`) |
| `team_mapping.md` | Orchestrator | role → agent mapping |
| `blockers/*.md` | any agent | open questions for the human |
| `decisions.md` | Orchestrator | append-only log of decisions and why |

Agents communicate through these files and through git, never through unstated
assumptions. If it is not written in `mas/state/`, it did not happen.

## 5. Definition of done (whole project)

The project is done when phase **P25** passes, which requires:

1. Every phase P00–P24 is `passed` in `phase_status.yaml`.
2. `README.md` documents the pipeline, all results tables (legacy and corrected),
   models, usage for every script, and the dataset policy.
3. `RESEARCH_LOG.md` tells the full story in order: each stage, its numbers, each
   discovered problem, each fix, each before/after.
4. The written deliverables of P24 exist (academic report, methodology infographic,
   professor progress report).
5. A full clean-machine rebuild (`make all` or the documented command sequence)
   regenerates every CSV from `data/raw/` without manual steps.

## 6. Compute and environment notes

- Development target: Linux, Python 3.12, a single small CUDA GPU (4 GB class) or CPU.
  Every neural benchmark must run on CPU too (slower), and pick CUDA automatically.
- Long jobs (LOSO networks, NN sweeps, GNN LOSO) must be **resumable**: each finished
  fold is saved and skipped on rerun. A Google Colab notebook is part of the
  deliverables (phase P21) for running them on a hosted GPU.
- Default seeds: `42` everywhere unless the roadmap says otherwise.
