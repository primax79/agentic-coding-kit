# AGENTS.md — agentic-coding-kit

Generic, project-agnostic skills, agents, and meta-tooling for AI-assisted
software development (Claude Code, Kilo Code) — not gCube-specific, not
about agent delegation. Full pitch, plugin table, and install paths:
[`README.md`](README.md). Part of the `primax79/*` family of AI-coding-tool
repos — see the workspace root's `AGENTS.md` (one level up) for how this
repo relates to `gcube-ai-toolkit`, `ai-architect-executor`, and `kilo-mcp`.

## Layout

- `plugins/common-tools/` — generic dev utilities (`gitignore`,
  `markdown-formatter`, `macroplan-authoring` skills; `merge-resolver`
  agent). Zero AI-tooling-config coupling.
- `plugins/agent-tooling-meta/` — tools for configuring Kilo/Claude
  themselves (`kilo-plugin-manager`, `kilo-rag-index-manager`,
  `framework-skillset-generator`; `kilo-customizer`,
  `framework-topic-drafter` agents; `/generate-skillset` command).
- `plugins/third-party/` — 10 curated, license-preserved external skills.
  Don't modify their behavior beyond what's needed to keep them working —
  they track an upstream source.
- `plugins/angular-dev-kit/` — Angular v20+ knowledge, **project-scoped by
  design** (version-specific claims aren't true globally). See its own
  README for the authoring/vendoring split.
- `docs/00-INDEX.md` — the concepts/authoring/distribution reference.
  `docs/01-concepts.md` is duplicated (not linked) into `gcube-ai-toolkit`
  for its own use — if you edit shared concepts, update both copies.
- `scripts/generate_skill_indices.py` — regenerates every `index.json`.

## Mandatory rules

- **Skill manifest.** New/changed skills need valid YAML frontmatter
  (`name`, `description`) in `SKILL.md` — Kilo's loader silently skips a
  skill without it.
- **Regenerate indices.** After adding, removing, or renaming a skill under
  any `plugins/*/skills/`, run `python3 scripts/generate_skill_indices.py`
  and commit the updated `index.json` files alongside the change.
- **Agent sync rule.** Claude Code and Kilo Code agent frontmatter formats
  are not compatible — `agents/` and `agents_kilo/` variants (where both
  exist, e.g. `agent-tooling-meta`) must be kept in sync via the
  `kilo-claude-sync` skill (this repo's own `agent-tooling-meta` plugin).
  Internal `name` fields must match exactly between the two.
- **Scope discipline.** A version-/framework-specific plugin (like
  `angular-dev-kit`) does not belong installed globally — see
  [`docs/03-compatibility-and-distribution.md`](docs/03-compatibility-and-distribution.md#choosing-scope-not-just-install-everywhere-for-convenience)
  before recommending a global install for anything domain-specific.
- **Markdown formatting.** Don't hand-format Markdown tables/TOCs — use
  this repo's own `markdown-formatter` skill (`plugins/common-tools/skills/markdown-formatter/`).
- **No dependency on sibling repos at install time.** This repo, `gcube-ai-toolkit`,
  `ai-architect-executor`, and `kilo-mcp` are organizationally related but
  none require another to be present — don't introduce a hard runtime
  dependency across repos without flagging it (see the README's
  "Relationship with the other repos in this family" and
  `plugins/architect-side/dependencies.json`-style informational records
  used by the sibling repos for this pattern).

## Before committing

Only when explicitly asked to commit: check `git status`/`git diff` for
scope and secrets, and confirm `index.json` was regenerated if any skill
under `plugins/*/skills/` changed.
