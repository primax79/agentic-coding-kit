# Quickstart: Claude Code environment setup

Installation-only guide, Claude Code side, using Claude's own native
`/plugin` mechanism - fully independent of `kilo-plugin-manager`. See
`QUICKSTART-KILO.md` for the Kilo side.

`/plugin` requires an actual terminal `claude` session - it is not
available in every embedding of Claude Code (e.g. some IDE-extension
contexts). If you're setting up Kilo and Claude from the same script
non-interactively, use `kilo-plugin-manager`'s `install` without
`--no-claude` instead (see `QUICKSTART-KILO.md`'s note) - it writes both
sides in one call and doesn't need `/plugin` at all.

## Topology: what goes where

| Repo | Scope | Why |
| --- | --- | --- |
| `agentic-coding-kit` | **Global** | Generic - no project coupling, useful everywhere |
| `ai-architect-executor` | **Global** | Protocol-agnostic orchestration methodology; the Architect role can be Claude itself, so it belongs everywhere |
| `kilo-mcp` | MCP server registration only | The skills in this plugin are Kilo-specific (installed Kilo-side, see `QUICKSTART-KILO.md`); Claude's involvement is the MCP server connection itself |
| `adk-agentic-coding-kit` | **Local only**, per ADK project | ADK-specific reference knowledge - no reason to load it elsewhere |
| `gcube-ai-toolkit` | **Local only**, per gCube/D4Science project | gCube-specific - install per project, never globally |

## 1. Add the marketplaces

```
claude plugin marketplace add https://github.com/primax79/agentic-coding-kit
claude plugin marketplace add https://github.com/primax79/ai-architect-executor
```

## 2. Global installs

```
/plugin install agent-tooling-meta
/plugin install common-tools
/plugin install third-party-skills
/plugin install architect-executor
```

(no `--scope` flag = global; add `--scope project` to any of these to
scope to the current workspace instead - see step 4 for the two plugins
that should *only* ever be installed that way.)

## 3. Register the `kilo-mcp` MCP server

The server itself is a standalone process, not a Claude plugin - registered
via `claude mcp add`, separately from the skills above:

```bash
git clone https://github.com/primax79/kilo-mcp.git ~/devel/kilo-mcp-server
claude mcp add kilo-mcp --scope user -- uv run --no-project --with mcp python ~/devel/kilo-mcp-server/server.py
claude mcp list   # kilo-mcp must show "✔ Connected" - only in a NEW session, not this one
```

See `kilo-mcp/INSTALL.md` for the optional RAG/Qdrant setup and the
unattended-install checklist.

## 4. Per-project installs (local only - never global)

```
claude plugin marketplace add git@github.com:primax79/adk-agentic-coding-kit.git
/plugin install adk-tools --scope project   # only inside an ADK project

claude plugin marketplace add https://code-repo.d4science.org/gCubeSystem/gcube-ai-toolkit.git
/plugin install gcube-core --scope project   # only inside a gCube/D4Science project
```

## Verification

```
/plugin list
claude mcp list
```

Expect: `agent-tooling-meta`, `common-tools`, `third-party-skills`,
`architect-executor` installed globally; `adk-tools`/`gcube-core` present
only in project-scoped installs where you actually ran step 4;
`kilo-mcp` connected.
