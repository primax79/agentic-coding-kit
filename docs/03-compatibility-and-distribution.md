# 03 - Compatibility, Distribution & Marketplace Setup

Read [`01-concepts.md`](01-concepts.md) first - this doc assumes you already
know the difference between the three "marketplace" mechanisms it describes.

## Table of Contents

- [Part 1: Claude Code](#part-1-claude-code)
- [Part 2: Kilo Code](#part-2-kilo-code)
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

This one file is enough to make the repo a working Claude Code marketplace -
no other tooling involved for the Claude side.

### Install

```bash
claude plugin marketplace add https://github.com/primax79/agentic-coding-kit.git
```

Then, **global scope** (every project on the machine - appropriate for
plugins with no stack/version dependency):

```text
/plugin install common-tools
/plugin install agent-tooling-meta
/plugin install third-party-skills
```

Or **workspace scope** (this repo checkout only, saved to `.claude/settings.json`
- required for anything that only applies to, or asserts facts specific to,
one project's stack):

```text
/plugin install angular-dev-kit --scope project
```

### Choosing scope: not just "install everywhere for convenience"

Global scope means "loaded into context on every project this machine
touches." That's fine for a plugin with no opinion about what stack the
current project uses - `common-tools`, `agent-tooling-meta`, and most of
`third-party-skills` genuinely don't care. It's the wrong default for a
plugin that asserts version- or framework-specific facts, because those
facts are only true some of the time:

- **Framework/language reference skills** (`angular-dev-kit` today; the
  pattern generalizes to any future `<framework>-dev-kit`) - install
  **project-scoped**, only in repos that use that framework. Installed
  globally, `angular-di` or `angular-forms` would trigger and offer guidance
  on a Vue or backend repo where it's simply noise, and worse, offer
  version-specific guidance (a skill written against Angular 20 or 21) on
  an Angular project running a different major - actively wrong rather than
  just irrelevant. See each skill's own `metadata.category`/description for
  what it assumes before treating it as a global default.
- **Meta-tooling and generic utilities** (`common-tools`,
  `agent-tooling-meta`, most of `third-party-skills`) - global is the
  sensible default; they operate on the AI tooling itself or on concerns
  (gitignore, markdown formatting, PDF/DOCX handling) that don't vary by
  project stack.

If a plugin's usefulness depends on "is this project built with X", assume
project scope until told otherwise - asserted facts that are project-specific
still are once the plugin is loaded globally, and there's no runtime check to
catch a stale one.

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

## Part 2: Kilo Code

> Prerequisite: [Kilo Code install guide](https://kilo.ai/install).

Kilo Code has no single native equivalent of `/plugin marketplace add` that
also handles **agents** (its native Skill URLs mechanism, below, only
covers skills). Marketplace and plugin management for Kilo is provided by
the **AI Swissknife** VS Code extension (and its CLI): install with the AI
Swissknife VS Code extension (or its CLI), pointing it at this repo, which
uses the same `.claude-plugin/marketplace.json` Claude Code reads. Its own
documentation covers usage; this repo no longer ships a Kilo plugin
manager (`kilo-plugin-manager` was retired on 2026-10-08).

Agents are installed by AI Swissknife too. Keeping a Claude Code agent and
its Kilo variant aligned (frontmatter formats differ, see
[`01-concepts.md`](01-concepts.md#whats-identical-vs-tool-specific)), and
moving a skill/agent/command between global and project scope, are manual
steps.

### Global vs Local Config

Skill URLs (below) can be set in Kilo's Settings UI (**Agent Behaviour →
Skills**, **Local Config** button edits `.kilo/kilo.jsonc`) or directly in
the files. Global Config (`~/.config/kilo/kilo.jsonc`) and Local Config
(`.kilo/kilo.jsonc`) both work for `skills.urls`, confirmed live, no scoping
restriction applies; `/reload` in Kilo chat is required either way, without
it the new URL isn't picked up. Note that the Settings UI's graphical fields
write Global Config, while some settings are only honored from Local.

---

## Kilo-native Skill URLs (`index.json`)

Kilo can install skills (only skills - not agents/commands) directly from
any URL serving an `index.json` manifest, with **zero** extra tooling - no
marketplace registration.

This repo generates `index.json` at three path depths under every plugin
(plugin level, `skills/` level, per-skill level - point Kilo's Skill URLs
field at any of the three, it resolves the same set either way):

```bash
python3 scripts/generate_skill_indices.py
```

Example, for the whole `agent-tooling-meta` plugin:

```text
https://raw.githubusercontent.com/primax79/agentic-coding-kit/main/plugins/agent-tooling-meta/skills/
```

**Re-run the script and commit the regenerated files** any time a skill is
added, removed, or renamed under `plugins/*/skills/` - they're generated,
not hand-maintained, and go silently stale otherwise (a renamed/deleted
skill stays listed; a new one doesn't show up).

### Limits of the Skill URLs mechanism

Verified directly against Kilo's source
(`packages/opencode/src/skill/discovery.ts` and `skill-remove.ts`), the
mechanism has properties that make it unsuitable as a recurring
install/update channel:

- **The cache never refreshes.** The downloader skips fetching a file
  entirely if it already exists at the destination - no ETag, no hash, no
  version check. A skill pulled this way is frozen at whatever version was
  live at pull time, forever, even after the source repo changes and the
  same URL is re-added. Skills are cached under `~/.cache/kilo/skills/<name>/`,
  not `~/.kilo/skills/`.
- **Cache keys are the skill's declared `name`, not the source URL.** Two
  different marketplaces publishing a skill under the same name collide in
  the same `~/.cache/kilo/skills/<name>/` folder.
- **There is no supported removal.** Kilo's own skill-removal code
  explicitly refuses to delete anything under `~/.cache/kilo/skills/`
  (it throws "remove URL-backed skills from configuration") - dropping the
  URL from config only stops future loading, it does not clean up or
  invalidate the stale copy already on disk. Skills loaded this way are
  also untrusted by design (`{file:}`/`{env:}` substitutions confined to
  their own folder), appropriate for code of unknown provenance, not for
  routine trusted installs.
- **A stale cache entry silently wins over a correctly-installed skill of
  the same name - it doesn't just sit there unused.** `discoverSkills`
  scans sources in a fixed order (external dirs → config dirs, which is
  where `~/.kilo/skills/` gets picked up → `skills.paths` →
  **`skills.urls` last**), and `loadSkills`/`add()` walks the matches in
  that same order doing `state.skills[name] = {...}` unconditionally - a
  name collision only logs a warning, never skips the overwrite. Because
  the cache is scanned last, an old cached copy of a skill you've since
  properly reinstalled shadows the new one, with only an easy-to-miss log
  line as evidence. See
  [`references/kilo-skill-url-cache-bug-summary.md`](../references/kilo-skill-url-cache-bug-summary.md)
  for a real incident this caused.

If you update a skill distributed this way, `rm -rf ~/.cache/kilo/skills/<name>/`
first, or the cache silently keeps serving the stale copy. For recurring
installs prefer AI Swissknife.

---

## Official `Kilo-Org/kilo-marketplace` (community catalog, not used by this repo)

Worth naming explicitly so it isn't confused with the mechanism above: Kilo
also curates its own official community marketplace at
[`Kilo-Org/kilo-marketplace`](https://github.com/kilocode/marketplace) on
GitHub - a *separate* repo, contributed to via pull request, using yet a
*third* manifest format (one YAML file per category: `skills/marketplace.yaml`,
`agents/marketplace.yaml`, `mcps/marketplace.yaml`). This repo (and the
other repos in this family) are **not** listed there - self-hosting via the
mechanisms above is a fully independent, equally valid distribution path,
just a different audience (your own team / anyone with the repo URL, vs.
Kilo's own curated public catalog).

We don't submit to their catalog, but we do generate a feed in the *same
shape* their client already knows how to consume - see the next section.

---

## Self-hosted official-format skill feed (`marketplace-skills.json`)

Kilo's own Marketplace UI (the standalone panel, and the Settings tab where
embedded) talks to `api.kilo.ai`, which serves skills as
`{id, description, category, githubUrl, content}` - where `content` is a
**tarball URL**, fetched and extracted directly by Kilo's installer. That's
a third, incompatible shape on top of the two above: not raw files +
`index.json` (Skill URLs), not a git-clone install.

`marketplace-skills.json` in this repo (and in `ai-architect-executor` and
`kilo-mcp`) is a static snapshot of that shape, with `content` pointing at
release tarballs. The tooling that generated it (ported from
`Kilo-Org/kilo-marketplace`) was retired together with the Kilo plugin manager;
this repo no longer regenerates the feed, so it is not updated when skills
change. Only a `kilocode-dev` build consumes it, not a released Kilo
version.

---

## Release Workflow

1. Bump versions in the relevant `plugin.json` file(s) and `CHANGELOG.md`
   (manual for now - see the note in
   [`02-authoring-and-maintenance.md`](02-authoring-and-maintenance.md#managing-releases--updates)).
2. `python3 scripts/generate_skill_indices.py` if any skill changed.
3. If any agent changed, keep its Claude and Kilo variants aligned by hand.
4. `git add . && git commit && git push origin main`.
5. Consumers update: `/plugin update` (Claude Code) or via AI Swissknife
   (Kilo Code).
