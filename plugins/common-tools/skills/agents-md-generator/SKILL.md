---
name: agents-md-generator
description: "Generates or refreshes the AGENTS.md of a project, library or monorepo module (agents.md open format): a deterministic analyzer collects build tool, commands with their provenance, runtime pins, CI commands, style configs and existing agent files; the skill then writes a short, verified AGENTS.md. Use when asked to create, update, consolidate or audit an AGENTS.md, including making CLAUDE.md and other agent files point to it."
metadata:
  version: "1.0.0"
---

# Skill: agents-md-generator

`AGENTS.md` is the tool-agnostic "README for agents" (<https://agents.md/>): the
operational facts an agent needs and a human README would not carry. Agents run
the commands it lists, so a wrong command costs more than a missing one.

For gCube projects use `gcube-agents-md-updater` instead (it adds the gCube
conventions on top of the same format).

## Workflow

### 1. Collect facts with the analyzer

Run the script bundled in this skill's `scripts/` directory (resolve the path
from where this skill is installed, not from the project) on the target root:

```bash
python3 -I <skill-dir>/scripts/analyze_project.py <project-root>
```

The JSON has: `git`, `build_systems` (Maven, Gradle, Node, Python, Make, Cargo,
Go, ...), `ci` and `ci_commands` (the commands CI really runs), `runtime_pins`
(`.nvmrc`, `.tool-versions`, ...), `code_style_configs`, `docs`,
`existing_agent_files`, `test_layout`, `docker`, `top_level`.

Every command has a `source`:

- `declared`: stated by the project (package.json scripts, Makefile targets, a
  CI step). It can be listed as is.
- `conventional`: the usual command of that tool (`mvn test`, `cargo test`),
  which the project never states. Before listing it, check it against a CI
  step or the build file, run it if that is cheap and safe, or mark it as
  unverified in your summary to the user.

Prefer a `ci_commands` entry over any conventional command: it is what the
project itself runs.

### 2. Read only what the facts point to

`README.md` (overview, not to be copied), the build file for a missing detail
(profiles, required properties), the CI file behind a `ci_commands` entry, and
any existing `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `GEMINI.md`,
`.github/copilot-instructions.md` (content to keep).

### 3. Write `AGENTS.md`

Format and templates: [references/agents-md-spec.md](references/agents-md-spec.md).
Rules:

- English, plain Markdown, no frontmatter, at the project root.
- Only commands you can source (see step 1). Never invent flags or targets.
- Short: 30-80 lines for one library. Every line is read on every task. Leave out
  a section when you have nothing project-specific for it.
- Complement the README, never duplicate it: 1-3 sentences of overview, then
  build, test (all and single), style, layout, commit rules, and the traps an
  agent cannot see from the code (generated files, required env vars, slow or
  destructive commands, "never commit X").
- Monorepo (`modules`, `workspaces`): shared conventions in the root file; a
  nested file only where a module's commands or conventions really differ (the
  nearest file wins).
- Update mode: keep hand-written guidance, change only facts that went stale
  (commands, versions, layout), and say what you changed.

### 4. Make the other agent files point at it

Kilo Code, Codex, Cursor, Copilot and others read `AGENTS.md` directly. Claude
Code reads `CLAUDE.md`, so when one exists or is wanted, the single source stays
`AGENTS.md` and `CLAUDE.md` carries only an import line (`@AGENTS.md`) plus
anything Claude-specific. When other agent files exist, fold their
tool-agnostic content into `AGENTS.md`, then ask the user before replacing
them with pointers or symlinks; never delete them unasked.

### 5. Verify

- Every listed command traces to a `declared` fact, a CI step, or was checked.
- Cheap checks done for real: a named npm script or make target exists, a path
  exists, a test directory is where you said.
- Report to the user in a few lines: what was detected, what was written, which
  commands remain unverified.
