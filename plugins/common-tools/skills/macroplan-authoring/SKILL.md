---
name: macroplan-authoring
description: "Author and maintain a durable, resumable development pipeline as a `tasks/` tree - raw input (`_inbox/`) distilled into structured specs (`specs/`, many-to-many with initiatives), each generating or updating an initiative (`NN-<slug>/plan.md`, tasks sized one-per-commit) that ships with a `summary.md` and moves to `done/`, over a shared `CONTEXT.md` and a live `00-INDEX.md` registry. Also the place where work that EMERGES during a conversation is captured (`<category>/T###-<slug>/` with README/CONTEXT/PROGRESS, unique ids, priority with a reason, any executor: this session, a delegated agent, a person), so it never lives only in a session's context. Use when planning work too large for one sitting, spanning multiple sessions or dependent features, or delegated piecemeal to another agent (e.g. Kilo), and whenever a new to-do, follow-up or finding appears mid-session. Not for a single-session, single-file change - use a normal plan for that."
---

# Task pipeline authoring (`tasks/` tree)

## Purpose

Produce a durable, resumable home for development work too large for one
sitting or one agent invocation - refactors, feature rollouts, anything meant
to be picked up across sessions or delegated one piece at a time. The format
survives context loss: a fresh session or a delegated agent with zero
conversational memory must read the files and continue correctly, without
re-deriving decisions already made or silently re-answering a resolved
ambiguity.

It models the whole flow, not just the plan: **raw input → structured spec →
initiative plan → completion summary**. Raw notes and transcripts are
first-class (they arrive before anyone knows which initiative they feed), specs
are first-class (one spec can drive several initiatives), and completion is
visible at the folder level.

## When to use

- The work has multiple dependent or independent pieces, each big enough to
  need its own verification step.
- It will span more than one session, or be picked up by a different agent
  instance (fresh Claude session, or Kilo) with no memory of the design
  conversation.
- Real design ambiguities were resolved through back-and-forth with the user
  that must not be re-litigated or silently re-decided later.
- You have raw material (notes, call transcripts, dumps) to turn into specs and
  tasks.
- **A new piece of work emerges mid-conversation** (a request aside from the
  current one, a finding, a follow-up, a decision waiting on someone). Capture
  it as an emergent task - see "Emergent tasks" below. This applies even when
  you will do it yourself.

Do not force this onto a single small change one agent finishes and verifies in
one pass - that's a normal plan. The ceremony pays off only at scale.

## Structure

```text
task/
  AGENTS.md          the convention (a copy of this skill's rules, so the repo
                     is self-contained for agents/teammates without the skill)
  CONTEXT.md         SHARED context - durable, project-wide facts read first:
                     codebase map, command/API surface, cross-cutting locked-in
                     decisions & conventions every initiative relies on
  00-INDEX.md        live REGISTRY - every initiative, its priority, its status,
                     and the spec→initiative map
  _inbox/            RAW input - no structure rules; split by analysis state:
    to-analyze/        not yet analyzed (the "hand off for analysis" queue)
    analyzed/          already distilled into specs/tasks (kept for provenance)
  specs/             structured specs; each may drive ONE or MANY initiatives
    <slug>.md
  NN-<slug>/         an ACTIVE initiative
    plan.md            task breakdown; tasks NN.T, each sized for one commit
    NN.T-<name>.md     (only when expanded - see "Task packaging" below)
    summary.md         completion record (added when the initiative ships)
  <category>/        EMERGENT tasks, grouped by kind of work (see "Emergent tasks")
    README.md          goal, scope, owner session, start prompt, shared notes
    notes/             the category's working notes
    T###-<slug>.md     a small task
    T###-<slug>/       a task with context: README.md, CONTEXT.md, PROGRESS.md
  done/              COMPLETE on a branch, awaiting merge (moved here unchanged)
    NN-<slug>/
    <category>/        finished emergent tasks (same names)
  merged/            MERGED into the integration branch (final)
    NN-<slug>/
```

Three terminal states, folder-visible (name/id preserved, only the path prefix
changes): **active** (`tasks/NN-<slug>/`) → **`done/`** (implemented + verified on
its branch, `summary.md` written, not yet merged) → **`merged/`** (branch merged
into the integration branch, e.g. `development`). Completion delegated to
another agent lands in `done/`; the orchestrator promotes it to `merged/` after
merging.

Three top-level docs, deliberately split by what changes and when - read
top-down, stop when you have enough:

- **`AGENTS.md`** - *how the system works* (this convention). Stable across
  projects; rarely changes.
- **`CONTEXT.md`** - *what this project is*. Durable project-wide grounding:
  file layout, the real command/API/data surface (annotated with which
  initiative added what), and cross-cutting **locked-in decisions** that span
  initiatives. Evolves as the codebase does; explicitly marked as needing
  re-verification against the real files, since it drifts between sessions.
- **`00-INDEX.md`** - *current state*. The registry of initiatives with a
  Priority column (priority ≠ the stable `NN` id), a Status column, the
  spec→initiative map, and the **task queue** (one line per emergent task, the
  next-up list on top). This is the "what's left / what's done" source of truth.

Copy-paste skeletons for every file kind are in
[`references/template.md`](references/template.md).

## The pipeline: raw → spec → plan → summary

1. **Capture.** Drop unstructured material into `_inbox/to-analyze/`. No format
   required; a date prefix helps (`2026-07-20-call-luca.md`).
2. **Analyze.** Distil it into one or more `specs/<slug>.md`. The spec is the
   *what & why* and becomes the source of truth for implementation - not the
   raw note. Move the processed raw file to `_inbox/analyzed/`, noting which
   spec(s)/initiative(s) it produced.
3. **Plan.** Each spec **generates new** initiatives or **updates/restructures
   existing** ones. `NN-<slug>/plan.md` is the *how*.
4. **Ship.** On completion add `NN-<slug>/summary.md`, `git mv` the folder into
   `done/`, fix the handful of links the move shifts, and update `00-INDEX.md`.

## Emergent tasks: capture work the moment it appears

Work rarely arrives only through planning. Mid-conversation, the user asks for
something aside from the current task, a review turns up a defect out of scope,
a "next step" comes up, a decision waits on someone, a peer session hands
something over. If that work lives only in the conversation, it is lost when
the session ends or is compacted, nobody else can pick it up, and it keeps
occupying the session's context while it waits.

**Rule: capture first, then continue.** As soon as new work appears and will
not be finished and verified in the current turn, write it down as a task,
then go back to what you were doing. In the reply, cite the task by id and
path. A "next steps" paragraph in the chat is not a substitute.

### Where and how

- **Initiative or emergent task.** If the work belongs to an existing
  initiative, add it to that plan as a task `NN.T`. Otherwise it is an
  emergent task in `tasks/<category>/`. A task that grows into several
  dependent pieces is promoted to an initiative; its `T###` id stays in the
  initiative's `Derived from`.
- **Id.** `T###`, unique across the whole tree including `done/`, never reused.
  Take the highest existing id plus one. Reserve it by creating the file at
  once, and re-check right before creating it: parallel sessions create tasks
  in the same repository at the same time, and id collisions do happen.
- **Shape.** A small task is one file, `T###-<slug>.md`. A task with context or
  progress worth keeping is a folder, `T###-<slug>/`, so that the definition,
  context and progress live in the task and not in a session:
  - `README.md`: the definition (header, goal, steps, verification);
  - `CONTEXT.md`: everything needed to resume without the original session:
    where the work is, how to build and check it, rules the user gave, facts
    already established (each with the command or file that established it).
    Write it while the context is still fresh: that is its point;
  - `PROGRESS.md`: a log, newest first, and the checklist of open items.
    Update it in the same change as any work on the task.
  A file is promoted to a folder, with the same id, when it gets progress worth
  keeping.
- **Header.** One `key: value` line per field, so the headers can be grepped:
  - `id`, `title`, `category`;
  - `priority` (P0–P3) and `priority-reason` (one line);
  - `next-up` (yes/no);
  - `state`, `executor`;
  - `depends-on`: task ids, or `-`;
  - `decider`: who must decide, when a decision is open;
  - `sources`: where it emerged (conversation date, file, finding, raw row id);
  - `paths`: the repositories and paths the task touches;
  - `handoff`: the one-line prompt that starts a fresh session or agent on the
    task, i.e. what to read, what to do and what to update.

  Then the sections Goal, Steps and **Verification**.

### States

`open`, `in progress`, `waiting` (on an external party: name who and what),
`blocked` (on an unresolved question or task: name it), `delivered`,
`verified`, `done` (or `done with a caveat`: name the caveat), `dropped` (say
why).

- `delivered` means the executor finished and checked its own work. Nobody else
  has checked it yet.
- **Only someone other than the executor sets `verified`**: another session,
  the orchestrator, or the user, after re-running the Verification. When nobody
  else is available, the task stays `delivered`, and `PROGRESS.md` records the
  self-check.

### Executor-agnostic

The executor is the session that captured the task (`self`), a delegated agent,
a dedicated session, or a person (`user-decision` when the task is a decision).
The lifecycle is the same for all of them. A task you do yourself still moves
through its states, and is not done until its Verification has been run.
Writing it down is what lets it change hands later.

### The registry: `tasks/00-INDEX.md`

The single dashboard of the tree, next to the tasks. Next to the initiatives
table it holds:
- **next-up**: at most five tasks, each with its handoff prompt;
- **one table per category**, sorted by priority then id: id, priority, title
  (linked to the task file or its `README.md`), state, executor, depends-on;
- **decisions waiting**: the exact question, who decides, and the task it
  blocks;
- **done**: finished tasks, newest first.

**Update the task and the registry in the same change**, every time.

**Done.** When the task is done, update `PROGRESS.md`, move the task with
`git mv` to `tasks/done/<category>/` (same name), and update the registry, in
one change. Then check the Markdown links: a move breaks relative links in
both directions, and every link in `tasks/` must still resolve.

### Categories and priority

Recommended when more than one session works on the queue; optional otherwise.

- **Categories** are kinds of work chosen per project (e.g. `porting/`,
  `maintenance/`, `release/`, `decisions/`). Create one only when no existing
  one fits. `tasks/done/<category>/` mirrors them. Each category has:
  - a `README.md`: the goal and scope of the category, the `owner-session`, the
    rules, a **start prompt** for a session that takes over the whole category,
    and "Shared notes";
  - a `notes/` folder for its working notes.
- **Priority** always carries a written reason:
  - **P0**: security exposure, or it blocks a release in progress or many tasks;
  - **P1**: needed for the project goal;
  - **P2**: important, off the critical path;
  - **P3**: nice to have.

### Keep the context clean

Capturing a task moves it out of the session's working memory. The session
keeps only its one-line registry entry, not the details. Read a task's files
only when you pick it up. When someone else will execute it, the task is the
whole hand-off: a fresh session or agent starts with an empty context and the
task files.

### Several sessions on one repository

- The state of a task is in its file or folder, never in conversation memory.
  A session that stops leaves its tasks current.
- Only a category's owner session edits that category's task files and
  `README.md`. Other sessions add dated notes under "Shared notes", or create
  new `T###` tasks.
- Re-check facts with git before acting on a task file: other sessions edit the
  repository too.
- **Validation round.** When the queue is built in bulk from documents (notes,
  old hand-offs, a sweep of a repository), its states and dependencies are
  guesses. Ask each session that holds live knowledge of an area to confirm or
  correct the tasks of that area before anyone works from the queue. Each
  session reports the corrections in its own task files. Keep the raw material
  the queue came from, and cite its row ids in `sources`.

**Never in a task file:** secrets, tokens, personal data, or details of
undisclosed vulnerabilities. Point to where they are kept instead. A claim
that something does not exist cites the command that searched for it.

## Task packaging: one file, or one file per task (by size)

`plan.md` always exists. The tasks inside can be packaged two ways - pick by
size; the logical granularity is identical either way (**one task `NN.T` = one
independently-verifiable unit = one commit**):

- **Inline (default).** Small/medium initiative: tasks `NN.T` are sections
  inside the single `plan.md`. Compact, read in one pass.
- **Expanded (large / delegated).** Each task `NN.T` becomes its own
  `NN.T-<name>.md` file; `plan.md` becomes the initiative index (goal, shared
  decisions, links to each task file). Use this when tasks exceed ~5-6, when a
  single task's grounding/steps/verification is too big to sit inline, or when
  tasks will be delegated one-by-one to separate agents/worktrees (one file =
  one task = one hand-off = one commit).

Converting inline → expanded (or back) is cheap; do it when an initiative
grows. Whichever form, keep each task's **Verification** section with it.

## Core principles

- **Ground everything in real code, not descriptions of it.** Before writing a
  spec or task, grep/read the actual files and quote them. "Tags follow
  `r<major>.<minor>.<patch>`" is trustworthy only once checked against real
  tags - wrong grounding is exactly what sends a delegated agent down the wrong
  path with total confidence.
- **Locked-in decisions are durable memory for resolved ambiguities.** Every
  real design fork resolved via a clarifying question becomes one bullet: the
  decision, then *why* (the trade-off/constraint that drove it). Cross-cutting
  ones live in `CONTEXT.md`; spec-specific ones in that `spec.md`. A fresh
  agent must never re-derive or re-guess what a human already decided. If a
  question is still open, say so and flag which task must resolve it before
  starting - never silently pick.
- **Spec↔initiative is many-to-many.** Specs live in `specs/`, never inside an
  initiative folder, because one spec can drive several initiatives and one
  initiative can draw on several specs. Every spec lists what it **Drives**;
  every `plan.md` lists what it is **Derived from**. Keep those links current.
- **Explicit non-goals prevent silent scope creep.** State what a spec/initiative
  does *not* do and why. Without this, a delegated agent with less context will
  "helpfully" build the excluded thing.
- **Dependency ordering is explicit, not implied by file order.** Every
  initiative states what it depends on and why (which function/table/module it
  reuses), so independents can run in parallel and dependents are never started
  early. The `NN` number is a **stable id**, not a priority - reprioritizing
  changes the Priority column in `00-INDEX.md`, never the folder numbers.
- **Verification is part of the spec, not an afterthought.** Every task ends
  with concrete, runnable checks. "Done" must be objectively checkable, and
  it's exactly what makes a task safe to hand to another agent.
- **Task granularity = one independently-verifiable unit.** Split an initiative
  into as many tasks as it has verification checkpoints - typically 2-6.
  Don't split finer (interdependent sub-steps stay inline in one task) or
  bundle unrelated checkpoints.
- **Progressive disclosure everywhere.** Convention in `AGENTS.md`; shared
  project facts in `CONTEXT.md` once; live state in `00-INDEX.md`; the *what/why*
  in a spec; only the steps to execute in a task. A reader stops once they have
  enough. Never repeat shared-context content inside a spec or task. Apply the
  same principle when formalizing any agent instructions in a versioned repo:
  brief pointer at the top level, detail in a scoped file close to what it
  governs.
- **Numbering is stable; completion is visible.** `NN` ids never get reused or
  renumbered once work starts - append. A shipped initiative moves to `done/`
  unchanged (id preserved, only a `done/` path prefix added), so `tasks/`'s
  listing separates active vs done at a glance.

## Workflow to produce/extend one

1. Explore the real code/data (grep, read, read-only checks) - never draft a
   "Locked-in decisions" section from assumption.
2. On a genuine design fork, ask the user a concrete question grounded in what
   you found (concrete options + trade-offs, recommended-first, preview
   snippets showing each option's real consequence) - not an abstract "how
   should X work?".
3. Ensure `CONTEXT.md` carries any new cross-cutting fact/decision; create it if
   the project has none yet.
4. Write/extend the `specs/<slug>.md`, then the initiative's `plan.md`
   (inline or expanded per size), following `references/template.md`.
5. Before treating a non-trivial spec/plan as final, if other independent
   AI engines are available in the session (other MCP connectors, CLI
   tools, agents), submit it to them for review and converge on any
   disagreements rather than finalizing from one engine's judgment alone
   - a fresh, context-blind subagent instance of yourself counts too,
   since the bias removed is authorship bias, not model identity - see
   `task-spec-authoring` for the full rationale.
6. Register/refresh the initiative row in `00-INDEX.md` (priority, status,
   spec map). Keep Status current - it is the source of truth for "what's left"
   when picking up cold.
7. When a project first adopts this, drop a `tasks/AGENTS.md` capturing this
   convention so the repo is self-contained for agents/teammates who don't have
   this skill.

## Delegating a task to another agent (e.g. Kilo)

A task is the right unit to hand to `kilo_implement` or an `Agent`/`Workflow`
subagent: scoped, self-contained, with its own objective verification. Prefer
the **expanded** packaging for heavy delegation (one task file per hand-off).
When delegating:

- Point the agent at that **one** task (the `NN.T` section or its
  `NN.T-<name>.md` file), plus the owning `spec.md` (for **Locked-in decisions**
  it must not contradict) and `CONTEXT.md` (global facts) - not the whole
  `tasks/` tree, to keep its context tight.
- After its report, verify against that task's own **Verification** section
  specifically (not a vibe check), then update `00-INDEX.md` status.
- If the delegated agent's environment isn't isolated (no dedicated worktree),
  treat concurrent-writer races as a real risk, not a formality.

See `task-spec-authoring` (in `ai-architect-executor`) for writing the *content*
of individual Kilo tasks and calibrating verification depth.

## Reference

See [`references/template.md`](references/template.md) for copy-paste skeletons
of every file kind (`CONTEXT.md`, `00-INDEX.md`, `specs/<slug>.md`, `plan.md`
inline and expanded, `NN.T-<name>.md`, `summary.md`). A real, in-use `tasks/`
tree looks like: specs driving initiatives, completed initiatives under
`done/`, and an `_inbox/` with analyzed provenance.
