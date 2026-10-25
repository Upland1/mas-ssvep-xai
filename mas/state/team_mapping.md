# Team mapping

Produced by following `mas/ADAPTING.md`. Agent definitions are local
configuration of the agent framework and are not committed; their content is
the shared preamble of `06_AGENT_ROLES.md` plus the prompts of the roles below,
the rules of `RULES.md`, and the hand-off contract of `mas/README.md`.

## Roles → agents

From P04 (decision 2026-10-24: fewer agents, lighter models, autonomous
loop). P00–P03 used 11 agents (data-engineer, signal-processing,
classical-ml, evaluation-lead, runner, literature-scout as separate agents);
their handoffs keep those names.

| Role (06_AGENT_ROLES.md) | Agent | Model tier |
|---|---|---|
| Orchestrator | orchestrator (main session) | session |
| Data Engineer | data-signal | mid |
| Infra | data-signal | mid |
| Signal Processing | data-signal | mid |
| Online / Real-time | data-signal | mid |
| Classical ML | ml-engineer | mid |
| XAI | ml-engineer | mid |
| Evaluation Lead | ml-engineer | mid |
| Deep Learning | deep-learning | mid |
| Connectivity & Stats | connectivity-stats | mid |
| Runner | verifier | mid |
| Verifier | verifier | mid |
| Scientific Reviewer | scientific-reviewer | strongest |
| Scribe | scribe | light |
| (added) independent known-answer tests | synthetic-tester | mid |
| (added) literature research | orchestrator | session |

A builder whose work fails review twice is re-called on the strongest tier.

Machine-readable form: `team.yaml` (the spec's `phases.yaml` keeps role names in
`owners:`; ADAPTING.md step 5 is applied there instead of rewriting the spec).

Independence check (ADAPTING.md step 2): verifier and scientific-reviewer hold
no builder role; synthetic-tester holds no builder role. Merging Runner into
the verifier keeps independence (neither builds) and removes the duplicate run. Phases where the
scientific reviewer is also an owner (P03, P10–P14, P24, P25) are reviewing,
not building, so no conflict arises.

## Hand-off protocol translation (ADAPTING.md step 4)

| Original mechanism | Here |
|---|---|
| `handoffs/Pxx-orchestrator-to-<role>.md` | `phases/Pxx-<slug>/00_assignment.md` (+ `02_plan.md`) |
| `handoffs/Pxx-<builder>-to-<next>.md` | `phases/Pxx-<slug>/03_changes_<agent>.md`, `04_tests.md`, `05_run.md` (verifier) |
| `reports/Pxx-verifier.md` | `phases/Pxx-<slug>/06_verify.md` |
| Reviewer verdict appended to the report | `phases/Pxx-<slug>/07_review.md`, copied into report §11 by the scribe |
| `ACK <role> <date>` and `## Questions` | same, in the `## Questions` section of the file being received |
| `reports/Pxx.md`, `blockers/`, `decisions.md`, `phase_status.yaml` | unchanged |

Every field of the original HANDOFF template (done, branch/commit, how to run,
left to do, known issues with PF-x, files touched, reference consultations,
sources, questions, ACK) exists in the `03_changes` template.

## Framework constraints (ADAPTING.md step 6)

| Rule | Constraint | Handling |
|---|---|---|
| Golden rule 7 (independent verifier) | none | the verifier re-runs from a clean `git worktree` under `state/scratch/verify/` |
| AGENTS.md §6 GPU | local laptop GPU only | `MAX_GPU_HOURS_PER_PHASE: 2`, `LOCAL_RUN_BUDGET_MIN: 120`; longer runs and LOSO-scale jobs go to Sebastian / Colab as human-run requests |
| Golden rule 4 (no numbers without a run) | long runs happen outside the agents | the human run's console log and CSVs are dropped into `reports/logs/Pxx/` and cited like any other log |
