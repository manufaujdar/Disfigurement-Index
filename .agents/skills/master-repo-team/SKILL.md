---
name: master-repo-team
description: Select a shared planning, building, review, QA, documentation, security or synchronization role for an authorized repository task; load the project-specific context and prefer its existing specialist team.
---

Read repository-root `AGENTS.md`, `MASTER_AI_AGENTS.md` and
`.ai/master-agents/PROFILE.md`. Nearest project instructions retain authority.
For a task already covered by the native team, use that team.

Choose only the relevant prompt under `.ai/master-agents/roles/`:
`planner.md`, `builder.md`, `reviewer.md`, `qa.md`, `docs.md`, `security.md`, or
`synchronizer.md`. State the active role and use the existing tracker/handoff.
Run sequentially by default. Role files do not launch agents, grant tools,
provider budgets, publication rights, parallelism or release approval.

Use the pinned master catalog for additional task-relevant definitions.
Repository-scoped sources stay in their owning repository. Archived definitions
remain inactive. Preserve privacy, independent-review and local release gates.
Return verified results and explicit unknowns; self-review is not independent approval.
