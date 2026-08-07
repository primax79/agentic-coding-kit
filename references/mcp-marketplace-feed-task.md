# Task: generate an official-format MCP marketplace feed

## Goal

Port `Kilo-Org/kilo-marketplace`'s `bin/generate-mcps-marketplace.ts` into
`kilo-plugin-manager` as `generate_mcp_marketplace.py`, same script-pair
pattern as `generate_skill_marketplace.py`/`generate_agent_marketplace.py`.
Author one real `MCP.yaml` for `kilo-mcp` (this family's own MCP server) so
the generator has something real to run against, not just a stub.

## Framing correction

An earlier pass at this recommended skipping MCP feed generation because
this repo family only has one MCP server (`kilo-mcp` itself) today. That's
the wrong measure - **this is a capability for whoever adopts
`kilo-plugin-manager`, not a count of what we personally have to expose
right now.** Anyone self-hosting a marketplace with MCP servers benefits
from the same generator; `kilo-mcp` having exactly one entry just means our
own dogfood test is small, not that the feature is unjustified. Proceed on
that basis, same priority as the agent feed task.

## The real shape (verified against two live examples in
`references/kilocode/kilo-marketplace/mcps/`)

```yaml
# mcps/context7/MCP.yaml
id: context7
name: Context7
description: Up-to-date code documentation for LLMs and AI code editors...
author: upstash
url: https://github.com/upstash/context7
category: search
content:
  - name: NPX
    content: |
      {
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"],
        "env": { "DEFAULT_MINIMUM_TOKENS": "{{DEFAULT_MINIMUM_TOKENS}}" }
      }
    parameters:
      - name: Default Minimum Tokens
        key: DEFAULT_MINIMUM_TOKENS
        placeholder: "6000"
        optional: true
    prerequisites:
      - Node.js
  - name: Remote Server
    content: |
      { "type": "streamable-http", "url": "https://mcp.context7.com/mcp" }
```

Multiple `content[]` entries are alternative installation methods (NPX vs.
remote server here) - the installer picks one (`options.parameters.__method`,
or the first if unspecified). `{{KEY}}` placeholders in `content` get
substituted from `parameters[].key` at install time.

## Zero new kilocode-side code needed - verified, not assumed

Read `installer.ts`'s `installMcp()`/`resolveMcpContent()`/`buildMcpEntry()`/
`normalizeMcpEntry()`: this already fully handles the shape above -
multi-method `content[]`, `{{param}}` substitution, and both the
`command`/`args`/`env` and `type`/`url` content forms, normalizing either
into the CLI's `mcp.json` schema. This is the exact same situation as the
agent feed task: the consuming side was built against the official format
already, so a faithful port of the generator is the entire task.

## The one real design snag: `kilo-mcp` is a "local" server with no package

`context7`'s NPX example works because `npx -y @upstash/context7-mcp`
fetches and runs a published package - nothing to clone first.  `kilo-mcp`
is different: it's a script (`server.py`) run from a **cloned copy of this
repo**, per `QUICKSTART-KILO.md` step 3:

```jsonc
"kilo-mcp": {
  "type": "local",
  "command": ["uv", "run", "--no-project", "--with", "mcp", "python", "~/devel/kilo-mcp-server/server.py"]
}
```

The marketplace installer only writes this JSON into `kilo.json`'s `mcp`
key - it does **not** clone anything for you (unlike `kilo-plugin-manager`'s
own `add`/`install`, which does). So `kilo-mcp`'s `MCP.yaml` needs a
`{{KILO_MCP_PATH}}`-style parameter for the script path, with a
`prerequisites` note telling the installer to clone the repo first - same
pattern as `context7`'s `DEFAULT_MINIMUM_TOKENS` parameter, just for a path
instead of a tuning value. Document this explicitly in `MCP.yaml`'s
`prerequisites` field; don't silently assume a fixed path.

## Concrete steps

1. Author `plugins/kilo-mcp/mcp/kilo-mcp/MCP.yaml` (mirrors
   `plugins/kilo-mcp/skills/*/SKILL.md`'s per-item directory convention),
   with a `{{KILO_MCP_PATH}}` parameter for the script location and
   `prerequisites: ["uv", "clone this repo first"]`.
2. New script `generate_mcp_marketplace.py`, same CLI shape as the skill/
   agent generators, walking `plugins/*/mcp/*/MCP.yaml` (glob mirrors
   `plugins/*/skills/*/SKILL.md`). Parse with a YAML lib if available in
   this environment, else reuse the existing hand-rolled parsing approach
   already used elsewhere in this toolchain rather than adding a new
   dependency - check what's already imported across `kilo-plugin-manager`'s
   scripts before deciding.
3. Validate `category` against the same fixed set the official generator
   enforces (`business, data, development, observability, productivity,
   search, web-automation`) - `Kilo-Org/kilo-marketplace/bin/marketplace-generator-utils.ts`'s
   `MARKETPLACE_CATEGORIES`. Fail loudly on an unrecognized category
   (`die()`, matching the skill/agent generators' style) rather than
   passing it through unchecked.
4. Output `marketplace-mcps.json` at the repo root (`{"items": [...]}`,
   `McpMarketplaceItem`-shaped, same JSON-not-YAML rationale as the other
   two feeds).
5. Wire into `actions.ts` the same way as skills/agents - fetch, tag
   `.marketplace`, merge, per-source error isolation.

## Acceptance criteria

- `python3 generate_mcp_marketplace.py <repo-root>` produces valid JSON for
  `kilo-mcp` with the real `MCP.yaml` authored in step 1.
- Manually verify the round-trip: install the generated item via the
  Marketplace UI with a test value for `{{KILO_MCP_PATH}}`, confirm the
  resulting `kilo.json` `mcp.kilo-mcp` entry matches what
  `QUICKSTART-KILO.md` documents by hand today.
- `tsc --noEmit` clean on any `actions.ts` changes.

## Explicitly out of scope

- Cloning `kilo-mcp` automatically as part of MCP install - not something
  `installMcp()` does for any MCP today (see the design snag above); if
  that's wanted later it's a kilocode-side feature, not something this
  generator can paper over.
- Any change to the existing manual MCP registration instructions in
  `QUICKSTART-KILO.md` - this is an additional install surface, not a
  replacement.
