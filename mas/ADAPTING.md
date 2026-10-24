# Adapting this package to an existing MAS

> **Applied.** The mapping for this repository is in `mas/state/team_mapping.md`;
> the resulting workflow is `mas/README.md`.

This package is framework-agnostic. Only two files assume a particular team:
`mas/06_AGENT_ROLES.md` (13 roles) and the `owners:` fields of `mas/phases.yaml`.
Everything else (mission, data spec, requirements, roadmap, references, pitfalls) is
what the work *is*, independent of who does it, and must not be changed by the
adaptation.

## Prompt to give your MAS orchestrator (copy as-is)

> You are taking over an existing project specification in this repository. Read
> `AGENTS.md`, then every file in `mas/`. Do not start any phase yet.
>
> Your task is to adapt the specification to **our existing agent team**, not to create
> the team it proposes:
>
> 1. List our current agents, their capabilities and tools.
> 2. Map each of the 13 roles in `mas/06_AGENT_ROLES.md` to one of our agents. Several
>    roles may go to one agent, **except** that the Verifier and the Scientific Reviewer
>    must never review work produced by the agent they are mapped to. If no agent can
>    hold a role, say so and propose the smallest change to our team.
> 3. For each of our agents, write the combined system-prompt addition: the shared
>    preamble of `06_AGENT_ROLES.md` plus the prompts of every role mapped to it.
> 4. Translate the hand-off protocol and `mas/state/` files into our framework's native
>    mechanism (messages, shared memory, task board…). If our framework already has an
>    equivalent, use it and record the mapping; the information content of the phase
>    report, hand-off and blocker templates must be preserved.
> 5. Rewrite only the `owners:` fields of `mas/phases.yaml` with our agent names and
>    write the mapping to `mas/state/team_mapping.md`.
> 6. Do not modify `AGENTS.md` golden rules, `01`–`05`, or acceptance criteria. If our
>    framework makes a rule impossible to follow (e.g. no independent verifier, no git
>    access, no GPU), write a blocker in `mas/state/blockers/` with options instead of
>    weakening the rule.
> 7. Stop and present `team_mapping.md` and any blockers for human approval before P00.

## What the operator should check before approving

- Verifier and Reviewer are independent of builders for every phase.
- Some agent can run Python, git, and long jobs (or the Colab path of P21 is assigned).
- The data folder is reachable by the agents but excluded from anything they publish.
- `REFERENCE_POLICY` is set the way you want in `mas/state/config.yaml`, and every agent
  follows `mas/CITING.md`.
