# 03 — Compatibility, Distribution & Marketplace Setup

Read [`01-concepts.md`](01-concepts.md) first — this doc assumes you already
know the difference between the three "marketplace" mechanisms it describes.

## Table of Contents

- [Part 1: Claude Code](#part-1-claude-code)
- [Part 2: Kilo Code — `kilo-plugin-manager`](#part-2-kilo-code--kilo-plugin-manager)
- [Kilo-native Skill URLs (`index.json`)](#kilo-native-skill-urls-indexjson)
- [Official `Kilo-Org/kilo-marketplace` (community catalog, not used by this repo)](#official-kilo-orgkilo-marketplace-community-catalog-not-used-by-this-repo)
- [Release Workflow](#release-workflow)

---

## Part 1: Claude Code

> Prerequisite: [Claude Code CLI/VS Code install guide](https://code.claude.com/docs/en/vs-code).

### Marketplace architecture

This repo's root `.claude-plugin/marketplace.json`:

```json
{
  "name": "agentic-coding-kit",
  "owner": { "name": "Alfredo Oliviero" },
  "plugins": [
    { "name": "common-tools", "source": "./plugins/common-tools", "description": "..." },
    { "name": "agent-tooling-meta", "source": "./plugins/agent-tooling-meta", "description": "..." },
    { "name": "third-party-skills", "source": "./plugins/third-party", "description": "..." }
  ]
}
```

This one file is enough to make the repo a working Claude Code marketplace —
no `kilo-plugin-manager` or any other tooling involved for the Claude side.

### Install

```bash
claude plugin marketplace add https://github.com/primax79/agentic-coding-kit.git
```

Then, **global scope** (every project on the machine):

```text
/plugin install common-tools
/plugin install agent-tooling-meta
/plugin install third-party-skills
```

Or **workspace scope** (this repo checkout only, saved to `.claude/settings.json`):

```text
/plugin install common-tools --scope project
```

### Command reference

| Command | Purpose |
| --- | --- |
| `claude plugin marketplace add <URL>` | Register a remote git repo as a marketplace source. |
| `/plugin search <query>` | Search plugins across registered marketplaces. |
| `/plugin list` | List installed plugins, versions, source marketplace. |
| `/plugin marketplace list` | List configured marketplace sources. |
| `/plugin install <plugin>[@marketplace]` | Install a plugin (suite or standalone skill). |
| `/plugin update` | Update all installed plugins to latest remote. |
| `/plugin marketplace remove <name>` | Unregister a marketplace source. |
| `/plugin uninstall <plugin>` | Remove an installed plugin. |

---

## Part 2: Kilo Code — `kilo-plugin-manager`

> Prerequisite: [Kilo Code install guide](https://kilo.ai/install).

Kilo Code has no single native equivalent of `/plugin marketplace add` that
also handles **agents** (its native Skill URLs mechanism, below, only
covers skills). `kilo-plugin-manager` (this repo's own `agent-tooling-meta`
plugin) fills that gap: it reads the *same* `.claude-plugin/marketplace.json`
Claude Code uses and installs both skills and agents from it, translating
agent frontmatter on the way in.

### Bootstrap `kilo-plugin-manager` itself

One-time, per machine — no manual download needed, it bootstraps itself via
Kilo's native Skill URLs mechanism:

1. Open Kilo Settings UI → **Agent Behaviour → Skills** → click **Local
   Config** (top-right) to edit `.kilo/kilo.jsonc`, or edit it directly.
2. Add:

   ```jsonc
   {
     "skills": {
       "urls": [
         "https://raw.githubusercontent.com/primax79/agentic-coding-kit/main/plugins/agent-tooling-meta/skills/kilo-plugin-manager/"
       ]
     }
   }
   ```

3. Save, then `/reload` in Kilo chat.

> **Global vs. Local config, a real gotcha**: pasting a URL into the
> Settings UI's graphical **Skill URLs** field writes to **Global Config**
> (`~/.config/kilo/kilo.jsonc`) — but globally configured skill URLs are
> currently **ignored during prompt sessions**. You must use **Local
> Config** (the button, or editing `.kilo/kilo.jsonc` / `./kilo.json`
> directly) for the URL to actually take effect.

### `kilo-plugin-manager` command reference

| Goal | Command |
| --- | --- |
| Register a marketplace | `python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py add <git-url> --name <name>` |
| List plugins/skills | `... plugin_manager.py list` |
| Check install status | `... plugin_manager.py status` |
| Install suite, global | `... plugin_manager.py install common-tools@agentic-coding-kit` |
| Install suite, per-project | `... plugin_manager.py install common-tools@agentic-coding-kit --project .` |
| Install one skill, global | `... plugin_manager.py install gitignore@agentic-coding-kit` |
| Update everything installed | `... plugin_manager.py update` |
| Uninstall (global / project) | `... plugin_manager.py uninstall common-tools@agentic-coding-kit [--project .]` |

### Moving items between scopes (`kilo-scope-manager`)

| Action | Command |
| --- | --- |
| Promote skill, local → global | `python3 ~/.kilo/skills/kilo-scope-manager/scripts/move_item.py promote --type skill --name <name>` |
| Promote agent, local → global | `... move_item.py promote --type agent --name <name>` |
| Localize skill, global → local | `... move_item.py localize --type skill --name <name>` |
| Localize agent, global → local | `... move_item.py localize --type agent --name <name>` |

### Ask Kilo directly

Once `kilo-plugin-manager` is bootstrapped, plain-language requests work
too — Kilo runs the equivalent commands itself:

> *"Use kilo-plugin-manager to add marketplace https://github.com/primax79/agentic-coding-kit.git with name agentic"*
> *"Install plugin common-tools"*

---

## Kilo-native Skill URLs (`index.json`)

The mechanism from the bootstrap step above, generalized: Kilo can install
skills (only skills — not agents/commands) directly from any URL serving an
`index.json` manifest, with **zero** extra tooling — no
`kilo-plugin-manager`, no marketplace registration.

This repo generates `index.json` at three path depths under every plugin
(plugin level, `skills/` level, per-skill level — point Kilo's Skill URLs
field at any of the three, it resolves the same set either way):

```bash
python3 scripts/generate_skill_indices.py
```

Example, for the whole `agent-tooling-meta` plugin:

```text
https://raw.githubusercontent.com/primax79/agentic-coding-kit/main/plugins/agent-tooling-meta/skills/
```

**Re-run the script and commit the regenerated files** any time a skill is
added, removed, or renamed under `plugins/*/skills/` — they're generated,
not hand-maintained, and go silently stale otherwise (a renamed/deleted
skill stays listed; a new one doesn't show up).

---

## Official `Kilo-Org/kilo-marketplace` (community catalog, not used by this repo)

Worth naming explicitly so it isn't confused with the mechanism above: Kilo
also curates its own official community marketplace at
[`Kilo-Org/kilo-marketplace`](https://github.com/kilocode/marketplace) on
GitHub — a *separate* repo, contributed to via pull request, using yet a
*third* manifest format (one YAML file per category: `skills/marketplace.yaml`,
`agents/marketplace.yaml`, `mcps/marketplace.yaml`). This repo (and the
other repos in this family) are **not** listed there — self-hosting via the
mechanisms above is a fully independent, equally valid distribution path,
just a different audience (your own team / anyone with the repo URL, vs.
Kilo's own curated public catalog).

---

## Release Workflow

1. Bump versions in the relevant `plugin.json` file(s) and `CHANGELOG.md`
   (manual for now — see the note in
   [`02-authoring-and-maintenance.md`](02-authoring-and-maintenance.md#managing-releases--updates)).
2. `python3 scripts/generate_skill_indices.py` if any skill changed.
3. `python3 plugins/agent-tooling-meta/skills/kilo-claude-sync/scripts/sync.py` if any agent changed.
4. `git add . && git commit && git push origin main`.
5. Consumers update: `/plugin update` (Claude Code) or
   `python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py update` (Kilo Code).
