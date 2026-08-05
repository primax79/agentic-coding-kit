---
name: kilo-claude-sync
description: Keeps Kilo Code and Claude Code agent/skill definitions aligned, both per-project (.kilo vs .claude) and globally (~/.kilo vs ~/.claude). Use whenever an agent .md file or a SKILL.md is added or edited under .kilo/agent, .kilo/skills, .claude/agents, or .claude/skills, before committing or ending the session.
---

# Kilo Code <-> Claude Code agent/skill sync

Kilo Code and Claude Code both use markdown-based agent and skill definitions, but agents have incompatible frontmatter: Kilo uses `mode`/`model`/`steps`/`color` with arbitrary model providers (e.g. `google/gemini-3.5-flash`); Claude Code uses `name`/`tools` and only its own model tiers. Skills, on the other hand, are structurally compatible (`<name>/SKILL.md` + optional `scripts/`), so they are shared rather than duplicated.

## What this maintains

- **Skills**: `.claude/skills` is a symlink to `.kilo/skills` (per project), and `~/.claude/skills` a symlink to `~/.kilo/skills` (global). One file on disk, read by both tools. Any bare `SKILL.md` missing `name`/`description` frontmatter gets it auto-added (required for Claude Code's skill discovery; inert extra text for Kilo). A legacy singular `.kilo/skill` directory is auto-renamed to `.kilo/skills` if found.
- **Agents**: `.kilo/agent/<name>.md` and `.claude/agents/<name>.md` (and their `~/.kilo/agent`, `~/.claude/agents` global equivalents) stay as separate files, since each side needs its own frontmatter shape. The shared `description` and prompt body are kept identical by content-hash comparison against the last synced state; each side's tool-specific frontmatter (Kilo's `mode`/`model`/`steps`/`color`, Claude's `tools`) is preserved verbatim across regenerations.

## When to run it

Run after creating or editing any file under `.kilo/agent/`, `.kilo/skills/`, `.claude/agents/`, or `.claude/skills/` — in the current project and/or in the home directory — before committing:

```bash
python3 ~/.kilo/skills/kilo-claude-sync/scripts/sync.py --scope both --repo <path-to-repo>
```

- `--scope local` — only the given `--repo` (defaults to cwd; resolves to its git root)
- `--scope global` — only `~/.kilo` / `~/.claude`
- `--scope both` (default) — both

## Conflict handling

If an agent's description/body changed on **both** sides since the last sync, the script reports a conflict for that agent name and leaves both files untouched — resolve by hand (decide which body is correct, or merge), then re-run.

Sync state is cached per root in `<root>/.kilo-claude-sync-state.json`. It's just a drift-detection cache (content hashes); if it's missing or deleted, already-identical files are left alone and only genuinely differing ones are reported/synced.
