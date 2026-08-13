---
name: kilo-claude-sync
description: "Keeps Kilo Code and Claude Code AGENT definitions aligned, both per-project (.kilo/agent vs .claude/agents) and globally (~/.kilo/agent vs ~/.claude/agents), regenerating the shared description and body on each side while preserving each host's own frontmatter shape. Skills are deliberately out of scope: both hosts install those natively, so mirroring them between the two directories only produced copies neither host's tooling declared. Use whenever an agent .md file is added or edited under .kilo/agent or .claude/agents, before committing or ending the session."
---

# Kilo Code <-> Claude Code agent sync

Kilo Code and Claude Code both use markdown agent definitions, but their
frontmatter is incompatible: Kilo uses `mode`/`model`/`steps`/`color` with
arbitrary model providers (e.g. `google/gemini-3.5-flash`); Claude Code uses
`name`/`tools` and only its own model tiers. The prompt itself is the same
prompt, so it is kept identical on both sides while each host keeps its own
header.

## Skills are not synced, on purpose

Both hosts already install skills themselves:

- **Claude Code** - a marketplace in `extraKnownMarketplaces` plus the plugin
  switched on in `enabledPlugins`, which can live in a project's own
  `.claude/settings.json` and travel with the repo.
- **Kilo Code** - `.kilo/skills/`, populated from a marketplace by the sibling
  `kilo-plugin-manager` skill.

Mirroring one directory into the other - by symlink or by copy - duplicated
those mechanisms, and the duplicate always won: a directory nobody's tool
declares is one that nothing updates and nothing reports as stale. Skills copied
in by hand sat unnoticed for weeks while `update` reported success, because the
installer only touches paths it recorded itself. A symlink was worse still: the
two hosts then shared one directory, so an accidental `rm` on either side took
out both.

If a skill needs to reach both hosts, declare it on both sides rather than
bridging them. `sync_skills()` survives in the script only to migrate a repo off
the old arrangement; nothing calls it.

## What this maintains

- **Agents**: `.kilo/agent/<name>.md` and `.claude/agents/<name>.md` (and their
  `~/.kilo/agent`, `~/.claude/agents` global equivalents) stay as separate files,
  since each side needs its own frontmatter shape. The shared `description` and
  prompt body are kept identical by content-hash comparison against the last
  synced state; each side's tool-specific frontmatter (Kilo's
  `mode`/`model`/`steps`/`color`, Claude's `tools`) is preserved verbatim across
  regenerations.

## When to run it

Run after creating or editing any file under `.kilo/agent/` or `.claude/agents/`
- in the current project and/or in the home directory - before committing:

```bash
python3 ~/.kilo/skills/kilo-claude-sync/scripts/sync.py --scope both --repo <path-to-repo>
```

- `--scope local` - only the given `--repo` (defaults to cwd; resolves to its git root)
- `--scope global` - only `~/.kilo` / `~/.claude`
- `--scope both` (default) - both

## Conflict handling

If an agent's description or body changed on **both** sides since the last sync,
the script reports a conflict for that name and leaves both sides untouched -
resolve by hand (decide which version is correct, or merge), then re-run.

Sync state is cached per root in `<root>/.kilo-claude-sync-state.json`. It's just
a drift-detection cache (content hashes); if it's missing or deleted, already
identical files are left alone and only genuinely differing ones are
reported/synced.
