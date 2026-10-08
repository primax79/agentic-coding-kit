# AGENTS.md format reference

Source: <https://agents.md/> - "a simple, open format for guiding coding agents",
stewarded by the Agentic AI Foundation (Linux Foundation). Check the site before
relying on the list of supporting tools below; it changes.

## What it is

A plain Markdown file at the repository root with the project-specific context
that would clutter a human README: build, test, conventions, gotchas.

- Standard Markdown, no required fields, no frontmatter, no schema.
- Location: repository root. In monorepos, subprojects may have their own; agents
  read the nearest file up the tree and the closest one wins. A user's chat
  instruction overrides everything.
- When it lists test or lint commands, agents are expected to run them and fix
  failures before finishing: list only commands that work.
- A living document: update it when the project changes. An existing doc can be
  renamed to `AGENTS.md` with a compatibility symlink.
- Read natively by many tools (Codex, Cursor, Copilot coding agent, Gemini CLI,
  Kilo Code, Zed, Windsurf and more). Claude Code reads `CLAUDE.md`: keep one
  source in `AGENTS.md` and put `@AGENTS.md` in `CLAUDE.md`.

## Sections that usually earn their place

None is mandatory. Skip any with nothing specific to say.

| Section | Content |
| --- | --- |
| Project overview | 1-3 sentences: what it is, key technology |
| Setup and build | Install, build, run; verified commands only |
| Testing | All tests, a single test, where CI is defined, required setup (tokens, containers) |
| Code style | Language level, formatter and linter, idioms, "do not reformat whole files" |
| Project structure | Where source, tests, resources, docs, generated files live |
| Security | Secrets handling, files never to commit, destructive or costly commands |
| Commit and PR | Message format, checks required before committing, changelog rules |
| Deployment | Only if agents may be asked to release or deploy |

## Minimal example

```markdown
# AGENTS.md

## Setup commands
- Install deps: `pnpm install`
- Start dev server: `pnpm dev`
- Run tests: `pnpm test`

## Code style
- TypeScript strict mode
- Single quotes, no semicolons
```

## Skeletons by ecosystem

Fill from the analyzer JSON; delete every line you cannot source.

### Maven / Java library

```markdown
# AGENTS.md

## Project overview
<artifactId>: <description>. Java <version>, built with Maven.

## Build and test
- Build: `mvn clean install`
- Tests: `mvn test`; one class: `mvn test -Dtest=<ClassName>`
- CI: `<file>` runs `<command from ci_commands>`

## Code style
- Java <version>. <javax or jakarta namespace if it matters>
- Follow the formatting of the file being edited; do not reformat whole files.

## Structure
- `src/main/java`, `src/main/resources`, `src/test/java`

## Commit and PR
- The build must pass before committing.
- Never commit credentials or token files.
```

### Node / TypeScript

```markdown
# AGENTS.md

## Build and test
- Install: `<pm> install`
- Build: `<pm> run build`; typecheck: `<pm> run typecheck`
- Tests: `<pm> run test`; lint: `<pm> run lint`

## Code style
- TypeScript strict. <formatter and linter config files found>

## Structure
- `src/` sources, `out/` or `dist/` generated (not edited by hand)
```

### Python

```markdown
# AGENTS.md

## Setup and test
- Install: `<uv sync | poetry install | pip install -e .>` (per the lockfile found)
- Tests: `<pytest ...>`; lint: `<ruff check .>` if configured

## Code style
- Python <requires-python>. <formatter config found>
```

## Rules of thumb

1. Never invent commands: each one comes from a build file, a script, a Makefile
   target, a CI step, or was run.
2. Complement the README, do not duplicate it.
3. Shorter is better: 30-80 lines for a library; every line costs context on every task.
4. Monorepo: shared rules at the root, per-module files only where they differ.
5. Merging existing agent files: fold the tool-agnostic content in; replace the
   originals with pointers only with the user's consent.
