# 03 — Compatibility, Distribution & Marketplace Setup

Read [`01-concepts.md`](01-concepts.md) first — this doc assumes you already
know the difference between the three "marketplace" mechanisms it describes.

## Table of Contents

- [Part 1: Claude Code](#part-1-claude-code)
- [Part 2: Kilo Code — `kilo-plugin-manager`](#part-2-kilo-code--kilo-plugin-manager)
- [Kilo-native Skill URLs (`index.json`)](#kilo-native-skill-urls-indexjson)
- [Official `Kilo-Org/kilo-marketplace` (community catalog, not used by this repo)](#official-kilo-orgkilo-marketplace-community-catalog-not-used-by-this-repo)
- [Self-hosted official-format skill feed (`marketplace-skills.json`)](#self-hosted-official-format-skill-feed-marketplace-skillsjson)
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

3. Save, then `/reload` in Kilo chat — required either way: without it the
   new URL isn't picked up yet. Global Config (`~/.config/kilo/kilo.jsonc`)
   works fine for this, same as Local — confirmed live, no scoping
   restriction actually applies (an earlier version of this note claimed
   global-scoped URLs were ignored during prompt sessions; that wasn't
   true, or is no longer true, in current Kilo).

> **Note**: skills fetched via a Skill URL are cached under
> `~/.cache/kilo/skills/<name>/` — a different location from
> `~/.kilo/skills/`, where `kilo-plugin-manager`'s own `install` places
> properly tracked installs. Don't be surprised seeing two different paths
> for what looks like "the same skill" during the bootstrap step; the
> cache one is just the temporary trampoline. See
> [below](#kilo-native-skill-urls-indexjson) for why this trampoline should
> never be used for anything beyond this one bootstrap step.

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

> *"Use kilo-plugin-manager to add marketplace `https://github.com/primax79/agentic-coding-kit.git` with name agentic"*
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

### Why this should only ever be used for the one-time bootstrap above

It's tempting to use Skill URLs as a general lightweight distribution
channel — no marketplace registration, no `kilo-plugin-manager` — but
verified directly against Kilo's source
(`packages/opencode/src/skill/discovery.ts` and `skill-remove.ts`), the
mechanism has three properties that make it unsuitable for anything
recurring:

- **The cache never refreshes.** The downloader skips fetching a file
  entirely if it already exists at the destination — no ETag, no hash, no
  version check. A skill pulled this way is frozen at whatever version was
  live at pull time, forever, even after the source repo changes and the
  same URL is re-added.
- **Cache keys are the skill's declared `name`, not the source URL.** Two
  different marketplaces publishing a skill under the same name collide in
  the same `~/.cache/kilo/skills/<name>/` folder.
- **There is no supported removal.** Kilo's own skill-removal code
  explicitly refuses to delete anything under `~/.cache/kilo/skills/`
  (it throws "remove URL-backed skills from configuration") — dropping the
  URL from config only stops future loading, it does not clean up or
  invalidate the stale copy already on disk. Skills loaded this way are
  also untrusted by design (`{file:}`/`{env:}` substitutions confined to
  their own folder), appropriate for code of unknown provenance, not for
  routine trusted installs.
- **A stale cache entry silently wins over a correctly-installed skill of
  the same name — it doesn't just sit there unused.** `discoverSkills`
  scans sources in a fixed order (external dirs → config dirs, which is
  where `~/.kilo/skills/` gets picked up → `skills.paths` →
  **`skills.urls` last**), and `loadSkills`/`add()` walks the matches in
  that same order doing `state.skills[name] = {...}` unconditionally — a
  name collision only logs a warning, never skips the overwrite. Because
  the cache is scanned last, an old cached copy of a skill you've since
  properly reinstalled via `kilo-plugin-manager` shadows the new one, with
  only an easy-to-miss log line as evidence. See
  [`references/kilo-skill-url-cache-bug-summary.md`](../references/kilo-skill-url-cache-bug-summary.md)
  for a real incident this caused.

If you ever update a skill distributed this way and need to re-bootstrap a
machine, `rm -rf ~/.cache/kilo/skills/<name>/` first, or the trampoline
silently keeps serving the stale copy. Past this repo's one-time
`kilo-plugin-manager` bootstrap, every install/update/uninstall should go
through `kilo-plugin-manager` instead, which has none of these failure
modes (tracked in `~/.kilo/plugin-manager.json`, real `update`/`uninstall`,
symlinked so updates propagate).

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

We don't submit to their catalog, but we do generate a feed in the *same
shape* their client already knows how to consume — see the next section.

---

## Self-hosted official-format skill feed (`marketplace-skills.json`)

Kilo's own Marketplace UI (the standalone panel, and the Settings tab where
embedded) talks to `api.kilo.ai`, which serves skills as
`{id, description, category, githubUrl, content}` — where `content` is a
**tarball URL**, fetched and extracted directly by Kilo's installer. That's
a third, incompatible shape on top of the two above: not raw files +
`index.json` (Skill URLs), not a git-clone-and-symlink install
(`kilo-plugin-manager`).

Rather than invent this packaging step, `kilo-plugin-manager` ports the
*exact* toolchain `Kilo-Org/kilo-marketplace` uses to build its own official
feed (`bin/generate-skill-marketplace.ts` +
`.github/workflows/package-skills.yml` — tar each skill, publish to a GitHub
Release, generate the JSON pointing at those release URLs) — see
[`kilo-plugin-manager/SKILL.md` §4](../plugins/agent-tooling-meta/skills/kilo-plugin-manager/SKILL.md)
for the two scripts and the constraints (no per-item version field — the
official installer has no update-in-place logic to read one anyway; Skills
only, Agents/MCPs need a smaller follow-up; and nothing in Kilo fetches this
file yet, since `MarketplaceApiClient` is still hardcoded to one source —
that's the still-open multi-marketplace work on `kilocode-dev`).

`marketplace-skills.json` is generated and published for this repo,
`ai-architect-executor`, and `kilo-mcp` — correct, ready to be consumed the
moment Kilo supports pointing its Marketplace UI at more than one source.

---

## Release Workflow

1. Bump versions in the relevant `plugin.json` file(s) and `CHANGELOG.md`
   (manual for now — see the note in
   [`02-authoring-and-maintenance.md`](02-authoring-and-maintenance.md#managing-releases--updates)).
2. `python3 scripts/generate_skill_indices.py` if any skill changed.
3. `python3 plugins/agent-tooling-meta/skills/kilo-claude-sync/scripts/sync.py` if any agent changed.
4. If any skill was added/removed/renamed, also regenerate the official-format
   feed: `python3 .../kilo-plugin-manager/scripts/package_and_publish_skills.py .`
   then `.../generate_skill_marketplace.py .` (see the section above).
5. `git add . && git commit && git push origin main`.
6. Consumers update: `/plugin update` (Claude Code) or
   `python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py update` (Kilo Code).
