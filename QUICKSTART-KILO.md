# Quickstart: Kilo Code environment setup

Installation-only guide, Kilo side, fully independent of Claude Code. It
touches only `~/.kilo/*` (or `<project>/.kilo/*`) - see
`QUICKSTART-CLAUDE.md` for the Claude side.

## Topology: what goes where

| Repo | Scope | Why |
| --- | --- | --- |
| `agentic-coding-kit` | **Global** | Generic - no project coupling, useful everywhere |
| `ai-architect-executor` | **Global** | Protocol-agnostic orchestration methodology; the Architect role can be Kilo itself, so it belongs everywhere. The Executor-side contract (`headless-executor-contract`) ships in the same plugin but is only *exercised* when Kilo is acting as executor |
| `kilo-mcp` | **Global** (skills) + MCP server registration | Kilo-specific binding of the same pattern |
| `adk-agentic-coding-kit` | **Local only**, per ADK project | ADK-specific reference knowledge - no reason to load it elsewhere |
| `gcube-ai-toolkit` | **Local only**, per gCube/D4Science project | gCube-specific - install per project, never globally |

## 0. Prerequisites

```bash
which uv
which kilo
```

## 1. Install the plugins

Install with the AI Swissknife VS Code extension (or its CLI), one
marketplace/repo at a time, **globally**:

- `agentic-coding-kit` plugins: `agent-tooling-meta`, `common-tools`,
  `third-party-skills`
- `ai-architect-executor`: `architect-executor`
- `kilo-mcp`: `kilo-mcp`

Alternatively, for skills only and with zero extra tooling, use Kilo's native
**Skill URLs** (`skills.urls` in `~/.config/kilo/kilo.jsonc` or
`.kilo/kilo.jsonc`, then `/reload`), see
[`docs/03-compatibility-and-distribution.md`](docs/03-compatibility-and-distribution.md#part-2-kilo-code).

## 2. Register the `kilo-mcp` MCP server

Clone the server once, then add it under the `mcp` key in
`~/.config/kilo/kilo.jsonc` (shared by the CLI and the IDE extension),
alongside whatever else is already registered there (`playwright`,
`mcp-redmine`, etc.):

```bash
git clone https://github.com/primax79/kilo-mcp.git ~/devel/kilo-mcp-server
```

```jsonc
"mcp": {
  "kilo-mcp": {
    "type": "local",
    "command": [
      "uv", "run", "--no-project", "--with", "mcp",
      "python", "~/devel/kilo-mcp-server/server.py"
    ]
  }
}
```

See `kilo-mcp/INSTALL.md` for the optional RAG/Qdrant setup.

## 3. Per-project installs (local only - never global)

With the AI Swissknife VS Code extension (or its CLI), install into the
project only:

- **ADK project**: `adk-tools` from `adk-agentic-coding-kit`
- **gCube/D4Science project**: `gcube-core` from `gcube-ai-toolkit`

## Verification

```bash
ls ~/.kilo/agent ~/.kilo/skills
kilo mcp list   # or check kilo.jsonc's "mcp" key directly
```
