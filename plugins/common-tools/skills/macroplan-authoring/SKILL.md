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
    README.md          scope of the category, owner session, shared notes
    T###-<slug>/       one task: README.md (definition), CONTEXT.md, PROGRESS.md
  done/              COMPLETE on a branch, awaiting merge (moved here unchanged)
    NN-<slug>/
    <category>/T###-<slug>/   finished emergent tasks
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
the session ends or is compacted, it cannot be picked up by anyone else, and
it keeps occupying the session's context while waiting.

**Rule: capture first, then continue.** As soon as new work appears and will
not be finished and verified in the current turn, write it as a task file,
then go back to what you were doing. In the reply, cite the task by id and
path. Do not leave the task only in a "next steps" paragraph of the chat.

- **Where.** If it belongs to an existing initiative, add it to that plan as a
  task `NN.T`. Otherwise it is an emergent task:
  `tasks/<category>/T###-<slug>/`. Categories are kinds of work chosen per
  project (e.g. `porting/`, `maintenance/`, `release/`, `decisions/`); create a
  new one only when no existing one fits, with a `README.md` stating its
  scope and owner. A task that grows into several dependent pieces is
  promoted to an initiative; its `T###` id stays in the initiative's
  `Derived from`.
- **Id.** `T###`, unique across the whole tree including `done/`, never reused.
  Take the highest existing id plus one. Check it again right before
  creating the folder: parallel sessions may be creating tasks in the same
  repository at the same time.
- **Files.** A task is a folder, so that its definition, context and progress
  live in the task and not in a session:
  - `README.md`: the definition. The header lists id, title, category,
    priority with a one-line reason (P0 now / P1 next / P2 later / P3 someday),
    state, executor, depends-on, decider (who must decide, if a decision is
    open) and sources (where it emerged: conversation date, file, finding).
    Then goal, steps and **Verification**.
  - `CONTEXT.md`: everything needed to resume without the original session:
    where the work is, how to build and check it, rules the user gave, key
    facts already established (with the command or file that established
    each). Write it while the context is still fresh: that is its point.
  - `PROGRESS.md`: a log, newest first, and the checklist of open items.
    Update it in the same change as any work on the task.
  A small task may start as one file, `T###-<slug>.md`, with the same header;
  convert it into a folder once it has progress worth keeping.
- **State.** One of: `open`, `in progress`, `delivered` (done by its executor,
  not yet checked by anyone else), `verified`, `done` (or `done with a caveat`,
  naming the caveat), `blocked` (naming the question), `dropped` (saying why).
- **Executor-agnostic.** The executor is `self` (the session that captured it),
  a delegated agent, or a person. The lifecycle is the same for all three: a
  task you do yourself still moves through its states, and is not done until
  its Verification has been run. Writing it down is what lets it change hands
  later.
- **Registry.** Add one line to the task queue in `00-INDEX.md`: id, title,
  category, priority, state, executor, link to the task's `README.md`. Keep a
  short next-up list (about five) at the top.
- **Done.** When verified, update `PROGRESS.md`, `git mv` the folder to
  `tasks/done/<category>/`, and update its line in `00-INDEX.md`, in one
  change.

**Keep the context clean.** Capturing a task moves it out of the session's
working memory. The session keeps only the one-line registry entry, not the
details. Read a task's folder only when you pick it up; when someone else
will execute it, the folder is the whole hand-off, so a fresh session or
agent can start with an empty context and the task files.

**Several sessions on one repository.**
- The state of a task is in its folder, never in conversation memory.
- A session that stops leaves `PROGRESS.md` current.
- Only a category's owner session edits its task files and `README.md`. Others
  add notes under "Shared notes" in the category `README.md`, or create new
  `T###` tasks.
- Re-check facts with git before acting on a task file: other sessions edit the
  repository too.

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
