# Templates — `tasks/` pipeline file skeletons

Copy-paste skeletons for every file kind. Keep the cross-links (`Drives` /
`Derived from`) current, and apply progressive disclosure — don't repeat
shared-context content inside a spec or task.

---

## `tasks/AGENTS.md` (the convention, dropped once per project)

A project-local copy of the task-management convention so the repo is
self-contained for agents/teammates without this skill. Mirror the
`macroplan-authoring` SKILL: the structure, the raw→spec→plan→summary pipeline,
the task-packaging rule (inline vs one-file-per-task by size), the core rules,
and the delegation rules. Keep it short and point to `00-INDEX.md` for live
state and `CONTEXT.md` for project facts.

---

## `tasks/CONTEXT.md` (shared, project-wide durable context — read first)

```markdown
# Project context (shared)

Durable, project-wide grounding shared by every initiative. Read before any
spec or plan. Re-verify anything load-bearing against the real files — this
drifts between sessions.

## Codebase map
- <top-level layout: which dir does what; key entry points>
- <annotate additions: "added by initiative NN">

## Command / API / data surface
- Build/test/run: `<commands>`
- <key services/tokens/endpoints/schemas an initiative will reuse>

## Cross-cutting locked-in decisions
- **<decision that spans initiatives>** — *why* (constraint/trade-off).
- <e.g. "dynamic-viewer stays 100% domain-agnostic — never import @is/*">

## Conventions
- <repo-wide norms: language for code/strings, commit style, verification gate>
```

---

## `tasks/00-INDEX.md` (live registry)

```markdown
# Task Index

Live registry of planned and in-progress development. For how this directory
works see [`AGENTS.md`](AGENTS.md); for shared project facts see
[`CONTEXT.md`](CONTEXT.md). This file is the state: what exists, priority, status.

## Initiatives

`#` is the stable id (folder/task prefix, e.g. `04.2`); it is NOT reading
order — `Priority` is.

| Priority | # | Initiative | Status | Depends on | Size |
| --- | --- | --- | --- | --- | --- |
| 1 | 01 | [<name>](01-<slug>/plan.md) | open / partial / ✅ done → `done/` | — | M |

## Specs

| Spec | Drives |
| --- | --- |
| [<slug>](specs/<slug>.md) | 01, 03 |

## Dependency graph

​```text
01 ──► 03 ──► 04
02 (independent)
​```

---

Delegation rules, the pipeline, and the folder convention live in [`AGENTS.md`](AGENTS.md).
```

---

## `tasks/specs/<slug>.md` (structured spec — the *what & why*)

```markdown
# <Title> (spec & context)

> **Drives initiative(s):** [NN](../NN-<slug>/plan.md)  ·  raw sources: `../_inbox/`

## Goal
<the outcome, grounded in a concrete problem — quote the real offending
code/data, don't describe it abstractly>

## Current state (verified <date> — re-check before starting)
<what exists today: files, behaviour, the real symbols involved>

## Locked-in decisions
- **<decision>** — *why* (the trade-off/constraint that drove it).
- <open forks stay as `[DECISION] …` and name the task that must resolve them>

## Non-goals
- <what this explicitly does NOT do, and why — prevents scope creep>
```

---

## `tasks/NN-<slug>/plan.md` — INLINE form (small/medium initiative)

```markdown
# <Title> — Implementation plan

> **Derived from spec:** [../specs/<slug>.md](../specs/<slug>.md)

## Tasks

### NN.1 — <task name>
**Goal**: <one sentence>.
Steps:
1. <real file/function names, real snippets — not "update the parser somehow">
2. ...
Verification: <runnable check; specific inputs/outputs or command>.

### NN.2 — <task name>
...
```

---

## `tasks/NN-<slug>/plan.md` — EXPANDED form (large / delegated initiative)

`plan.md` becomes the index; each task is its own file.

```markdown
# <Title> — Implementation plan

> **Derived from spec:** [../specs/<slug>.md](../specs/<slug>.md)

Tasks (each = one commit; hand one file at a time to a delegated agent):

1. [NN.1 — <task name>](NN.1-<name>.md)
2. [NN.2 — <task name>](NN.2-<name>.md)

Shared decisions for this initiative that every task must honour:
- <initiative-local locked-in decision — *why*>
```

### `tasks/NN-<slug>/NN.T-<name>.md` (one expanded task)

```markdown
# NN.T — <task name>

> Part of [<Title>](plan.md) · spec: [../specs/<slug>.md](../specs/<slug>.md)

**Goal**: <one sentence>.

Steps:
1. <concrete, grounded steps>
2. ...

Verification: <runnable check>.
```

---

## `tasks/NN-<slug>/summary.md` (completion record)

```markdown
# NN — <Title> (completion summary)

**Status:** ✅ Completed and merged into `<branch>`.

- Implementation commit(s): `<sha>` (<message>)
- Merged via: `<sha>` (if applicable)

## What landed
<net effect on the branch: files, key changes; `git diff --stat A B` figures>

## Deviations from the plan
<anything done differently and why; conflicts resolved; tasks dropped/added>

## Verification
<what was run/checked; what to spot-check when next running the app>
```
