# Quickstart: Claude Code + Kilo Code environment setup

How this ecosystem's repos are meant to be installed, validated live during
a full environment reset on 2026-08-05. Covers **installation only** — for
uninstalling or resetting, see each tool's own `uninstall`/`remove` commands
mentioned inline; there's no separate teardown guide.

## Topology: what goes where

| Repo | Scope | Why |
| --- | --- | --- |
| `agentic-coding-kit` | **Global**, both tools | Generic — no project coupling, useful everywhere |
| `ai-architect-executor` | **Global**, both tools | Protocol-agnostic orchestration methodology; the Architect role can be either Claude or Kilo, so it belongs everywhere. The Executor-side contract (`headless-executor-contract`) ships in the same plugin but is only *exercised* when Kilo is acting as executor |
| `kilo-mcp` | **Global**, both tools (skills) + MCP server registration | Kilo-specific binding of the same pattern; the skills are global, the MCP server itself is registered once via `claude mcp add` |
| `adk-agentic-coding-kit` | **Local only**, per ADK project (e.g. `dave_agent`) | ADK-specific reference knowledge — no reason to load it in non-ADK projects |
| `gcube-ai-toolkit` | **Local only**, per gCube/D4Science project | gCube-specific — install into each such project individually as needed, never globally |

## 0. Prerequisites

```bash
which uv        # needed for the MCP server and some skill scripts
which claude    # Claude Code CLI
which kilo      # Kilo Code CLI
```

## 1. Bootstrap `kilo-plugin-manager`

Everything below (Kilo side) runs through this one script. Get it once,
from a repo you'll add as a marketplace anyway:

```bash
git clone https://github.com/primax79/agentic-coding-kit.git /tmp/acp-bootstrap
PM=/tmp/acp-bootstrap/plugins/agent-tooling-meta/skills/kilo-plugin-manager/scripts/plugin_manager.py
python3 "$PM" add https://github.com/primax79/agentic-coding-kit.git --name acp
python3 "$PM" install agent-tooling-meta@acp   # this installs kilo-plugin-manager itself, globally
rm -rf /tmp/acp-bootstrap
```

From here on, use the installed copy: `~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py`.

## 2. Global marketplaces + installs

```bash
PM=~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py

python3 "$PM" add https://github.com/primax79/agentic-coding-kit.git --name acp
python3 "$PM" install common-tools@acp
python3 "$PM" install third-party-skills@acp
# agent-tooling-meta@acp already installed in step 1

python3 "$PM" add https://github.com/primax79/ai-architect-executor.git --name aae
python3 "$PM" install architect-executor@aae

python3 "$PM" add https://github.com/primax79/kilo-mcp.git --name kilo-mcp
python3 "$PM" install kilo-mcp@kilo-mcp
```

Claude Code picks these up automatically — `install` (without `--no-claude`)
writes both `~/.kilo/*` and `~/.claude/agents`/`~/.claude/commands` in one
call, and `~/.claude/skills` is symlinked to `~/.kilo/skills`. No separate
Claude-side step needed.

## 3. Register the `kilo-mcp` MCP server

The MCP server itself (`server.py`) is a standalone process, registered
once, separately from the skills above:

```bash
git clone https://github.com/primax79/kilo-mcp.git ~/devel/kilo-mcp-server
claude mcp add kilo-mcp --scope user -- uv run --no-project --with mcp python ~/devel/kilo-mcp-server/server.py
claude mcp list   # kilo-mcp must show "✔ Connected" — only in a NEW session, not this one
```

See `kilo-mcp/INSTALL.md` for the optional RAG/Qdrant setup and the
unattended-install checklist — this section only covers the minimum to get
`kilo_implement`/`kilo_rag_search` etc. working.

## 4. Per-project installs (local only — never global)

For an **ADK project** (uses `google-adk`):

```bash
python3 "$PM" add git@github.com:primax79/adk-agentic-coding-kit.git --name adk-agentic-coding-kit
python3 "$PM" install adk-tools@adk-agentic-coding-kit --project /path/to/your/adk-project
```

For a **gCube/D4Science project**:

```bash
python3 "$PM" add https://code-repo.d4science.org/gCubeSystem/gcube-ai-toolkit.git --name gcube
python3 "$PM" install gcube-core@gcube --project /path/to/your/gcube-project
```

Both create real symlinks into `<project>/.kilo/skills/` (and mirror to
`.claude/`) pointing at the marketplace checkout under
`~/.kilo/marketplaces/`, plus any bundled agents/commands
(`adk-diff-auditor` + `/adk-upgrade` for ADK projects).

## 5. Claude Code's native path (alternative to `plugin_manager.py`)

Everything above also works through Claude Code's own `/plugin` command,
if you're only setting up Claude (not Kilo):

```
claude plugin marketplace add https://github.com/primax79/agentic-coding-kit
/plugin install agent-tooling-meta --scope project   # or omit --scope for global
```

`/plugin` requires an actual terminal `claude` session — it is not
available inside every embedding of Claude Code (e.g. some IDE-extension
contexts).

## Verification

```bash
python3 "$PM" status
```

Expect: every marketplace shows a live `HEAD` commit (no dead paths), and
the global installs are exactly `agent-tooling-meta@acp`,
`common-tools@acp`, `third-party-skills@acp`, `architect-executor@aae`,
`kilo-mcp@kilo-mcp` — nothing named after a repo/plugin that no longer
exists in that form.

```bash
diff <(ls ~/.claude/agents) <(ls ~/.kilo/agent)   # same file set both sides
claude mcp list                                   # kilo-mcp Connected
```
