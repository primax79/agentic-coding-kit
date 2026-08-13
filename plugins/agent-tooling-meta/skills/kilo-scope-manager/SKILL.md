---
name: kilo-scope-manager
description: "Moves or copies Kilo customization items - skills, agents, and commands/workflows - between global scope (~/.kilo, ~/.config/kilo) and project-local scope (.kilo), handling name shadowing, duplicate global directories, and Claude Code mirroring. Also covers maintaining and fixing global definitions. Use when the user asks to promote an item to global, localize a global item, resolve duplicate copies, or update global agents/skills."
---

# Skill: kilo-scope-manager

Relocates skills, agents and commands between scopes, and keeps global definitions maintained. All mechanical moves are done by the bundled script - do not hand-move files.

## Scope model (Kilo docs)

| Kind | Local (project, wins on name collision) | Global (primary) | Other global dir (legacy/alternate) |
| --- | --- | --- | --- |
| skill | `<repo>/.kilo/skills/<name>/` | `~/.kilo/skills/<name>/` | `~/.config/kilo/skills/` |
| agent | `<repo>/.kilo/agent/<name>.md` | `~/.config/kilo/agent/<name>.md` | `~/.kilo/agent/` |
| command | `<repo>/.kilo/command/<name>.md` | `~/.config/kilo/command/<name>.md` | `~/.kilo/command/` |

The script warns whenever a twin of the moved item exists in the alternate global dir - stale twins are the main source of "why is the old version still loading" confusion.

## Usage

```bash
# skills
python3 scripts/move_item.py skill to-global <name> --repo <project>
python3 scripts/move_item.py skill to-local  <name> --repo <project> [--copy]

# agents and commands/workflows
python3 scripts/move_item.py agent   to-global <name> --repo <project>
python3 scripts/move_item.py command to-local  <name> --repo <project> --copy

# overwrite an existing destination
python3 scripts/move_item.py ... --force
```

The script validates the item (SKILL.md `name:` frontmatter for skills, `description:` for agents/commands), refuses to clobber without `--force`, and prints the follow-up steps.

## Decision guide

- **to-global** when the item is project-agnostic (generic tooling, org-wide workflows) and other repos benefit. Before promoting, make sure its body has no repo-relative references (`migration-notes/...`, `./scripts/...` outside the skill dir): convert them to absolute paths or move the referenced material too.
- **to-local (move)** when it only matters to one project - keeps the global namespace clean.
- **to-local (copy)** for a project-specific variant of a global item: the local copy shadows the global by name. If the divergence is permanent, prefer a renamed fork (`<name>-<project>`) over silent shadowing.
- An agent should live in the same scope as the skills it references: a global agent referencing project-local skills breaks in every other repo.

## Maintaining / fixing GLOBAL definitions

Global agents/skills rot when their project-local counterparts are fixed (or vice versa). Maintenance procedure:

1. **Inventory both scopes**: `ls ~/.kilo/skills ~/.config/kilo/agent ~/.config/kilo/command` vs the project `.kilo/`. List name collisions - for each, the LOCAL one wins inside the project, the GLOBAL one is what every other repo gets.
2. **Diff the twins** (`diff <local> <global>`). Decide which side is authoritative (usually the most recently fixed one), then align the other with `move_item.py ... --copy --force` or by editing the global file directly.
3. **Fix in place**: global definitions are ordinary markdown - apply the same quality rules as local ones (verified class names/paths, correct frontmatter, English content). Never leave a known-wrong mapping in a global file: it silently poisons every other project.
4. **Retire superseded globals** into an attic dir (`~/.config/kilo/_attic/`, `~/.kilo/_attic/`) rather than deleting - global dirs are not under version control, an attic is the only undo.
5. **Re-mirror Claude agents only**: `python3 ~/.kilo/skills/kilo-claude-sync/scripts/sync.py --scope global` after touching global *agents*. Skills need nothing: Claude Code installs those through its own marketplace plus `enabledPlugins`, and must never be pointed at Kilo's skill directories.
6. `/reload` in open Kilo sessions.
