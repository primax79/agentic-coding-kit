# agentic-coding-kit

Generic, project-agnostic skills, agents, and meta-tooling for AI-assisted
software development — Claude Code and Kilo Code today, source-verified
rather than guessed where it matters (API surfaces, marketplace mechanics).

## Why this exists

Coding-agent tools (Claude Code, Kilo Code, whatever comes next) all
converge on the same three needs: reusable domain knowledge that loads only
when relevant (**skills**), specialized personas for isolated sub-tasks
(**agents**), and a way to install/update/share both across a team without
copy-pasting files by hand (**plugins + marketplace**). This repo is the
generic layer of that — the skills, agents, and install mechanics that
don't assume gCube/D4Science (see [`gcube-ai-toolkit`](https://github.com/primax79/gcube-ai-toolkit)
for that) and don't assume you're delegating work to another AI (see
[`ai-architect-executor`](https://github.com/primax79/ai-architect-executor)/[`kilo-mcp`](https://github.com/primax79/kilo-mcp)
for that). If a skill or tool is useful on *any* project regardless of
domain, it belongs here.

**Typical use cases**: bootstrap a new project's `.gitignore` correctly for
its actual stack; keep Markdown docs formatted consistently; plan
multi-session work as a resumable task tree (`macroplan-authoring`); install
or move your own Kilo/Claude skills and agents without hand-editing config
files; pull in a curated, vetted third-party skill instead of writing one
from scratch.

## What's in each plugin

| Plugin | Contains | Concern |
| --- | --- | --- |
| [`common-tools`](plugins/common-tools) | `gitignore`, `markdown-formatter`, `macroplan-authoring` (skills), `merge-resolver` (agent) | Generic dev utilities, zero AI-tooling-config coupling |
| [`agent-tooling-meta`](plugins/agent-tooling-meta) | `kilo-plugin-manager`, `kilo-scope-manager`, `kilo-claude-sync`, `roocode-migrator`, `framework-skillset-generator` (skills); `skill-writer`, `mode-writer`, `kilo-customizer`, `roocode-migrator`, `framework-topic-drafter` (agents); `/generate-skillset` (command) | Managing Kilo Code/Claude Code themselves — installing, syncing, authoring, migrating their configuration, and generating a grounded reference skillset for a framework/library from its source/docs/spec. Not delegation — see relationship section below. |
| [`third-party`](plugins/third-party) | 10 curated external skills (`frontend-design`, `mcp-builder`, `skill-creator`, `theme-factory`, `agent-md-refactor`, `file-organizer`, `changelog-generator`, `grill-me`, `terraform`, `playwright`) | Vetted, license-preserved imports |
| [`angular-dev-kit`](plugins/angular-dev-kit) | `angular-library` (ours: authoring/packaging a publishable Angular library, `provideX()`/ng-packagr); 10 vendored references — `angular-component`, `-di`, `-directives`, `-forms`, `-http`, `-routing`, `-signals`, `-ssr`, `-testing`, `-tooling` — from [analogjs/angular-skills](https://github.com/analogjs/angular-skills) (MIT, Brandon Roberts) | Angular v20+ knowledge, library-authoring and application-side kept distinct — see the plugin's own README for which is which |

Full concepts/authoring/distribution documentation: [`docs/00-INDEX.md`](docs/00-INDEX.md).

## Install

### Generic (works either way)

Register this repo as a marketplace, then install whichever plugin(s) you
need — the *how* differs by tool, covered next.

### Claude Code

```bash
claude plugin marketplace add https://github.com/primax79/agentic-coding-kit.git
```

```text
/plugin install common-tools
/plugin install agent-tooling-meta
/plugin install third-party-skills
```

Add `--scope project` to any install to scope it to the current repo
instead of globally. Full command reference:
[`docs/03-compatibility-and-distribution.md`](docs/03-compatibility-and-distribution.md#part-1-claude-code).

### Kilo Code

Two independent options — pick one, or use both:

- **`kilo-plugin-manager`** (covers skills *and* agents):

  ```bash
  python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py add https://github.com/primax79/agentic-coding-kit.git --name agentic-coding-kit
  python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py install common-tools@agentic-coding-kit
  ```

- **Native Skill URLs** (skills only, zero extra tooling — paste into
  Kilo's Settings UI, **Local Config**, or `.kilo/kilo.jsonc`'s
  `skills.urls`):

  ```text
  https://raw.githubusercontent.com/primax79/agentic-coding-kit/main/plugins/common-tools/skills/
  ```

  Regenerate `index.json` after any skill change:
  `python3 scripts/generate_skill_indices.py`.

Full walkthrough, including the Global-vs-Local-Config gotcha and the
scope-management commands: [`docs/03-compatibility-and-distribution.md`](docs/03-compatibility-and-distribution.md#part-2-kilo-code--kilo-plugin-manager).

## Relationship with the other repos in this family

- **[`gcube-ai-toolkit`](https://github.com/primax79/gcube-ai-toolkit)** —
  no dependency either way. Same repo layout conventions (this doc set is
  itself adapted from that repo's, generalized), disjoint content: gCube/D4Science
  domain skills there, everything domain-agnostic here.
- **[`ai-architect-executor`](https://github.com/primax79/ai-architect-executor)** —
  no dependency either way. Its content is about *delegating* work to
  another AI/agent (the Architect/Executor pattern); this repo's
  `agent-tooling-meta` is about *configuring* Kilo/Claude as installed tools.
  Related domain (both are "meta" to actual application code), genuinely
  different concern — see
  [`docs/01-concepts.md`](docs/01-concepts.md) if the boundary isn't
  obvious from that description alone.
- **[`kilo-mcp`](https://github.com/primax79/kilo-mcp)** — no dependency
  either way, same distinction as above (delegation runtime vs. tool
  configuration).

None of the four repos depend on each other at install time — the split is
organizational (what belongs together conceptually), not a dependency
graph.

## Deliberately not here

- **`toolkit-release-manager`** — stays in `gcube-ai-toolkit` for now; its
  current implementation has a hardcoded path to that repo and needs a
  genericizing rewrite (config-driven, targets any repo in this family)
  before it belongs in a shared bucket. Not yet done.
- **`kilo-task-delegation`** — went to `ai-architect-executor` instead: it's
  the manual (non-MCP) hand-off method for the Architect/Executor pattern,
  same concern as that repo's other content, not a Kilo/Claude
  config-management tool.

## License

[MIT](LICENSE)
