# 01 — Concepts: Skills, Agents, Commands, MCP

This is the primer to read before touching anything else in this repo (or in
[`ai-architect-executor`](https://github.com/primax79/ai-architect-executor),
[`kilo-mcp`](https://github.com/primax79/kilo-mcp),
[`gcube-ai-toolkit`](https://github.com/primax79/gcube-ai-toolkit) — same
vocabulary everywhere in this family of repos). It explains what each building block
*is*, independent of any specific tool, then how Claude Code and Kilo Code
each implement it — what's genuinely identical, what's just renamed, and
what's a real difference.

## The building blocks, tool-agnostic

- **Skill** — a self-contained package of instructions + optional scripts/
  references that extends what an agent can do for a *specific kind of
  task*. Loaded **on demand**: the tool matches the user's request against
  each installed skill's `description` and pulls in the matching one's full
  content only when relevant. Not loaded into every conversation — that's
  the point, it keeps unrelated context out until it's needed. Follows the
  open [Agent Skills specification](https://agentskills.io/): a folder with
  a `SKILL.md` (YAML frontmatter + Markdown body), optionally alongside
  `scripts/`, `references/`, `assets/`.
- **Agent** (Claude Code) / **Mode** (Kilo Code, inherited from Roocode's
  terminology — Kilo's own UI and config now mostly say "agent" too, but
  you'll still see "mode" in older docs/skills) — a *persona*: a system
  prompt plus its own tool permissions and (for Kilo) model choice, dispatched
  to handle a task in relative isolation from the main conversation. Unlike a
  skill, an agent isn't "loaded" into an existing conversation — it's a
  separate run with its own context, invoked by name.
- **Command / Workflow** — a saved, reusable prompt (usually multi-step)
  triggered explicitly by the user, typically via a `/name` slash command.
  Not loaded automatically like a skill; not a separate persona like an
  agent — just a canned instruction sequence.
- **MCP (Model Context Protocol)** — a protocol for exposing *tools* (and
  optionally resources/prompts) from an external server to any MCP-capable
  client. This is how an AI gets capabilities beyond its built-in tool set —
  e.g. [`kilo-mcp`](https://github.com/primax79/kilo-mcp) in this family of repos exposes `kilo_implement`,
  `kilo_rag_search`, etc. as MCP tools so any MCP client (Claude Code today)
  can delegate work to Kilo Code. Orthogonal to skills/agents/commands: MCP
  is about *what tools exist*, the other three are about *how the AI decides
  to use its existing tools and knowledge*.
- **Plugin** — a packaged, installable bundle of the above (skills and/or
  agents and/or commands), the unit you actually `install`/`uninstall`.
- **Marketplace** — a repository (or, for Kilo, optionally just a URL
  serving an index) listing one or more plugins for discovery/installation.
  This repo, [`ai-architect-executor`](https://github.com/primax79/ai-architect-executor),
  [`kilo-mcp`](https://github.com/primax79/kilo-mcp), and
  [`gcube-ai-toolkit`](https://github.com/primax79/gcube-ai-toolkit) are
  each a marketplace.

## What's identical vs. tool-specific

| Concept | Claude Code | Kilo Code | Identical? |
| --- | --- | --- | --- |
| Skill format | `SKILL.md`, Agent Skills spec | `SKILL.md`, same spec | **Yes** — same file works unmodified in both |
| Skill loading | On-demand by description match | On-demand by description match | Yes, same model |
| Agent/mode frontmatter | Flat `tools: Bash, Read, ...` string | Structured `mode:`/`permissions:` map | **No** — incompatible, needs translation (see `kilo-claude-sync` in `agentic-coding-kit`'s own `kilo-claude-tools` plugin) |
| Marketplace manifest | `.claude-plugin/marketplace.json` | No single native format — see below | Partial |
| Install command | `/plugin install <name>@<marketplace>` | No single equivalent — see below | No |
| MCP | Native client support (`/plugin`-adjacent MCP config) | Also a full native MCP client — its own Settings UI has a dedicated MCP section, and `kilo.jsonc`'s `mcp: {}` block configures servers it connects to, same as Claude Code | **Yes** — both are full MCP clients. `kilo-mcp` in this family uses Kilo as the *server* side (exposed to an external orchestrator) by deliberate design for the Architect/Executor pattern, not because Kilo lacks client support — see [`ai-architect-executor`](https://github.com/primax79/ai-architect-executor) |

### Marketplace: three different mechanisms, not one

This trips people up, so it gets its own subsection. There isn't one
"Kilo marketplace format" — there are three separate things that all get
called that:

1. **Claude Code's native format** — `.claude-plugin/marketplace.json` at a
   repo's root, listing `plugins[]` each with a `source` path. This is what
   every repo in this family actually uses as its *primary* manifest, because
   Kilo can consume it too (see next point) — one manifest, both tools.
2. **Kilo's native "Skill URLs" mechanism** — a completely different,
   simpler thing: point `skills.urls` (in `kilo.jsonc`, or the Skills tab
   in Kilo's Settings UI) at a URL serving an `index.json` (`{"skills": [{"name":
   ..., "files": [...]}]}`). No `.claude-plugin/` involved at all, no
   `kilo-plugin-manager` needed — Kilo fetches the manifest and the listed
   files directly. This repo ships `index.json` at every plugin level for
   exactly this (see `scripts/generate_skill_indices.py`). **Skills only** —
   agents/commands aren't covered by this mechanism.
3. **The official community `Kilo-Org/kilo-marketplace`** — a *different*,
   separate GitHub repo curated by Kilo itself, using yet another format
   (`skills/marketplace.yaml`, `agents/marketplace.yaml`, `mcps/marketplace.yaml`,
   one YAML file per category, contributed via PR to that one repo). This
   family of repos does **not** use this mechanism — it's for getting listed
   in Kilo's own official catalog, a separate concern from self-hosting your
   own marketplace.

`kilo-plugin-manager` (this repo's `kilo-claude-tools` plugin) is what
bridges mechanism 1 into something Kilo can install from, including agents
(which mechanism 2 can't touch) — see
[`03-compatibility-and-distribution.md`](03-compatibility-and-distribution.md)
for the full install/distribution walkthrough of all three.
