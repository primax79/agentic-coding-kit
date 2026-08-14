# Quickstart: Kilo Code environment setup

Installation-only guide, Kilo side, fully independent of Claude Code. Every
command here uses `--no-claude` so it touches only `~/.kilo/*` (or
`<project>/.kilo/*`) - see `QUICKSTART-CLAUDE.md` for the Claude side, or
drop `--no-claude` on any `install` call below to populate both at once
(that's what `kilo-plugin-manager` does by default).

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

## 1. Bootstrap `kilo-plugin-manager`

No manual download needed - it bootstraps itself via Kilo's **native Skill
URLs** mechanism (zero extra tooling, skills-only, which is exactly enough
to fetch `kilo-plugin-manager` itself):

1. Edit either Global Config (`~/.config/kilo/kilo.jsonc`) or Local Config
   (`.kilo/kilo.jsonc` in the current directory) - confirmed live, both
   work the same for this - and add:

   ```jsonc
   {
     "skills": {
       "urls": [
         "https://raw.githubusercontent.com/primax79/agentic-coding-kit/main/plugins/agent-tooling-meta/skills/kilo-plugin-manager/"
       ]
     }
   }
   ```

2. Save, then `/reload` in Kilo chat - required either way, this is what
   actually picks up the new URL (skip it and the skill won't be
   available yet).
3. Ask Kilo to use it - *"Use kilo-plugin-manager to add marketplace
   `https://github.com/primax79/agentic-coding-kit.git` with name acp, then
   install agent-tooling-meta@acp"* - which performs a **proper, globally
   tracked** install (recorded in `~/.kilo/plugin-manager.json`), unlike the
   bootstrap fetch itself. You can drop the Skill URL afterward; it was
   only a one-time trampoline.

> **Note**: the bootstrap fetch caches the skill under
> `~/.cache/kilo/skills/kilo-plugin-manager/` - a different location from
> `~/.kilo/skills/`, where step 3's proper install actually lands. Don't
> be surprised seeing two different paths for what looks like "the same
> skill".
>
> **This cache never refreshes itself.** Kilo's `skills.urls` downloader
> skips any file that already exists at the destination - no ETag, no hash,
> no version check (`discovery.ts`'s `download()`). Once
> `kilo-plugin-manager` is pulled this way, it is frozen at that version
> forever, and there's no supported way to remove it either - Kilo's own
> skill-removal code explicitly refuses to touch anything under
> `~/.cache/kilo/skills/` (`skill-remove.ts`: "remove URL-backed skills
> from configuration" - i.e. only unlist the URL, don't expect a delete).
> If you ever update `kilo-plugin-manager` in the marketplace repo and need
> to re-bootstrap a machine, `rm -rf ~/.cache/kilo/skills/kilo-plugin-manager/`
> first, or the trampoline will silently keep serving the stale copy. This
> is exactly why step 1 is the *only* place this repo recommends the raw
> `skills.urls` mechanism - everything else goes through `plugin_manager.py`,
> which has none of these problems (tracked in `~/.kilo/plugin-manager.json`,
> supports `update` and `uninstall` for real).

From here on, use the installed copy: `~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py`.

## 2. Global marketplaces + installs

```bash
PM=~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py

python3 "$PM" add https://github.com/primax79/agentic-coding-kit.git --name acp
python3 "$PM" install common-tools@acp --no-claude
python3 "$PM" install third-party-skills@acp --no-claude
# agent-tooling-meta@acp already installed in step 1

python3 "$PM" add https://github.com/primax79/ai-architect-executor.git --name aae
python3 "$PM" install architect-executor@aae --no-claude

python3 "$PM" add https://github.com/primax79/kilo-mcp.git --name kilo-mcp
python3 "$PM" install kilo-mcp@kilo-mcp --no-claude
```

## 3. Register the `kilo-mcp` MCP server

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

## 4. Per-project installs (local only - never global)

For an **ADK project**:

```bash
python3 "$PM" add git@github.com:primax79/adk-agentic-coding-kit.git --name adk-agentic-coding-kit
python3 "$PM" install adk-tools@adk-agentic-coding-kit --project /path/to/your/adk-project --no-claude
```

For a **gCube/D4Science project**:

```bash
python3 "$PM" add https://code-repo.d4science.org/gCubeSystem/gcube-ai-toolkit.git --name gcube
python3 "$PM" install gcube-core@gcube --project /path/to/your/gcube-project --no-claude
```

## Verification

```bash
python3 "$PM" status
```

Expect every marketplace to show a live `HEAD` commit (no dead paths), and
the global installs to be exactly `agent-tooling-meta@acp`,
`common-tools@acp`, `third-party-skills@acp`, `architect-executor@aae`,
`kilo-mcp@kilo-mcp`.

```bash
ls ~/.kilo/agent ~/.kilo/skills
kilo mcp list   # or check kilo.jsonc's "mcp" key directly
```
