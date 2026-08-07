# Task: generate an official-format Agent marketplace feed

## Goal

Port `Kilo-Org/kilo-marketplace`'s `bin/generate-agents-marketplace.ts` into
`kilo-plugin-manager` as `generate_agent_marketplace.py`, mirroring
`generate_skill_marketplace.py` (same directory) — same repo, same script
pair pattern, same JSON-not-YAML output. Generates
`marketplace-agents.json` at the repo root, in the shape kilocode's
`AgentMarketplaceItem`/`installAgent()` already consumes.

## Why this task exists

`agentic-coding-kit` (and the other repos in this family) ship agents
alongside skills - `plugins/agent-tooling-meta/agents/kilo-customizer.md`,
`mode-writer.md`, `roocode-migrator.md`, `skill-writer.md`,
`framework-topic-drafter.md`, and `plugins/architect-executor/agents/`,
`plugins/kilo-mcp/agents/` in the other two repos. `generate_skill_marketplace.py`
(shipped, verified, published for real via GitHub Releases) only covers
skills. Agents currently have **no path into kilocode's multi-source
Marketplace UI** at all - they're only installable via `kilo-plugin-manager`'s
own git-clone-and-translate mechanism, which works fine but is a different,
separate install surface from the one being built.

## Why this one is easier than it sounds

Unlike skills, agents need **no packaging step** - no tarball, no `gh
release`. `AgentMarketplaceItem.content` is inline structured JSON
(`{mode, description, prompt, options?, permission?, requirements?}`),
parsed straight from the agent `.md`'s own frontmatter + body. Verified
against the real official generator:

```ts
// Kilo-Org/kilo-marketplace/bin/generate-agents-marketplace.ts
type AgentContent = {
  mode: "primary" | "subagent" | "all"
  description: string
  prompt: string
  options: Record<string, unknown>
  requirements?: MarketplaceRequirements
  model?: string
  variant?: string
  temperature?: number
  top_p?: number
  permission?: Record<string, unknown>
  color?: string
  steps?: number
  hidden?: boolean
}
```

And confirmed on the *consuming* side, `installAgent()`
(`packages/kilo-vscode/src/services/marketplace/installer.ts`) does the
exact inverse - splits `content` back into frontmatter + prompt and writes
the `.md` file:

```ts
const { prompt, ...front } = item.content
const frontmatter = yaml.stringify(front).trimEnd()
const content = `---\n${frontmatter}\n---\n\n${prompt}\n`
await fs.writeFile(filepath, content, "utf-8")
```

So the whole task is: parse our agent `.md` frontmatter into that same
shape, emit JSON. No new kilocode-side code needed at all (unlike the
skill work, which needed a whole new install path) - `installAgent()`
already does exactly the right thing, verified by reading its source, not
assumed.

## Concrete steps

1. **New script**: `plugins/agent-tooling-meta/skills/kilo-plugin-manager/scripts/generate_agent_marketplace.py`,
   same CLI shape as `generate_skill_marketplace.py`
   (`<repo-root> [--output PATH]`), same frontmatter parser reused
   (`from plugin_manager import parse_fm`).
2. Walk `plugins/*/agents/*.md` (mirrors `find_skills()`'s
   `plugins/*/skills/*/SKILL.md` glob - note agents in this repo are flat
   `.md` files directly under `agents/`, not one subdirectory per agent
   like skills).
3. For each agent file, build:
   - `id` = filename without `.md` (must match the frontmatter's own name
     field if one exists - check what `kilo-claude-sync`/`plugin_manager.py`
     already assume here before inventing a new rule; don't duplicate an
     existing convention if `is_kilo_shaped()`/`to_kilo_agent()` already
     encode one).
   - `category` = plugin directory name (same convention as the skill
     generator - `agent-tooling-meta`, `architect-executor`, `kilo-mcp`).
   - `content` = `{mode, description, prompt, permission, ...}` parsed
     from frontmatter + body. `plugin_manager.py`'s existing `parse_fm()`
     and `is_kilo_shaped()` already parse Kilo-shaped agent frontmatter
     (`mode:`, `permission:`) for the `convert` subcommand - reuse that
     parsing, don't reimplement it.
   - `mode` **must** be `"primary" | "subagent" | "all"` - validate and
     fail loudly (matching `generate_skill_marketplace.py`'s `die()` style)
     if a frontmatter's `mode` value doesn't match, rather than silently
     emitting an invalid item.
4. Sort/write JSON the same way `generate_skill_marketplace.py` does
   (`{"items": [...]}`, sorted by category then id).
5. Wire into `actions.ts`'s `fetchCustomMarketplaceSkills()`-equivalent -
   either extend that function to also fetch `marketplace-agents.json` and
   push `AgentMarketplaceItem`s into the merged list, or add a sibling
   `fetchCustomMarketplaceAgents()` following the exact same pattern
   (per-source try/catch, errors accumulated not thrown, `.marketplace`
   tagged). This part touches `kilocode-dev`, not `agentic-coding-kit`.

## Acceptance criteria

- `python3 generate_agent_marketplace.py <repo-root>` produces valid JSON
  for all three repos with agents (`agentic-coding-kit`,
  `ai-architect-executor`, `kilo-mcp`) with zero manual fixups to any
  existing agent `.md` file.
- Round-trip check: take one generated item's `content`, feed it through
  the same frontmatter-rebuild logic `installAgent()` uses
  (`yaml.stringify` the non-prompt fields + `---` fence + prompt), and diff
  against the original `.md` - should match modulo YAML key ordering.
- `tsc --noEmit` clean on whatever `actions.ts` changes are made in
  `kilocode-dev`, same bar as the skill work.

## Explicitly out of scope for this task

- MCP feed generation - separate open decision, see the options
  comparison this doc's companion conversation already worked through
  (recommendation: don't build it yet, only one MCP server exists across
  this repo family today).
- Any change to `kilo-plugin-manager`'s existing git-clone-and-symlink
  agent install path - stays as-is, this is an additional install surface,
  not a replacement.
