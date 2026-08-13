# 02 — Authoring: Skills, Agents, and Your Own Plugin/Marketplace

Read [`01-concepts.md`](01-concepts.md) first if the vocabulary here
(skill/agent/plugin/marketplace) isn't already clear.

## Table of Contents

- [Creating a New Skill](#creating-a-new-skill)
- [Packaging: Suite Plugin vs. Standalone vs. Both](#packaging-suite-plugin-vs-standalone-vs-both)
- [Creating Your Own Claude Plugin + Kilo Marketplace in One Repo](#creating-your-own-claude-plugin--kilo-marketplace-in-one-repo)
- [Skill Authoring Standards](#skill-authoring-standards)
- [The Deterministic Script Priority Rule](#the-deterministic-script-priority-rule)
- [Bundled Third-Party Skills & Local Patches](#bundled-third-party-skills--local-patches)
- [Agent Authoring & Synchronization](#agent-authoring--synchronization)
- [Slash Command / Workflow Authoring](#slash-command--workflow-authoring)
- [Managing Releases & Updates](#managing-releases--updates)

---

## Creating a New Skill

1. **Choose (or create) a destination plugin directory** — group by concern,
   not by convenience. In this repo: `plugins/common-tools/` (generic,
   no Kilo/Claude-config coupling), `plugins/agent-tooling-meta/` (manages
   Kilo/Claude's own configuration), `plugins/third-party/` (imported
   external skills). A genuinely new concern gets its own plugin folder
   rather than being wedged into an existing one — see
   [Packaging](#packaging-suite-plugin-vs-standalone-vs-both) below.

2. **Scaffold the directory:**

   ```text
   plugins/<plugin-name>/skills/my-new-skill/
   ├── SKILL.md                # Main skill specification (mandatory)
   ├── config/                 # Declarative JSON configuration (recommended)
   │   └── config.json
   ├── scripts/                 # Deterministic executable scripts (recommended)
   │   └── my_helper.py
   └── references/              # Detailed reference docs (optional)
       └── detailed_guide.md
   ```

3. **Author `SKILL.md`** with valid YAML frontmatter — this is mandatory,
   not a formality: without a `name`/`description` pair, Kilo's skill
   loader silently skips the whole skill (no error, it just never fires).

   ```yaml
   ---
   name: my-new-skill
   description: Concise description of what the skill does and when to use it.
   ---
   ```

---

## Packaging: Suite Plugin vs. Standalone vs. Both

| Strategy | Setup | User experience | Use when |
| --- | --- | --- | --- |
| **Suite plugin** | Skill folder under `plugins/<plugin-name>/skills/`, described inside that plugin's `.claude-plugin/plugin.json`. | `/plugin install <plugin-name>` installs the whole suite together. | The skill is one of several related tools that make sense installed as a set. |
| **Standalone entry** | Add a *separate* entry to the root `.claude-plugin/marketplace.json` with `"source": "./plugins/<plugin-name>/skills/<skill-name>"`. | `/plugin install <skill-name>` installs just that one skill. | A general-purpose utility useful on its own, without the rest of its suite. |
| **Both (hybrid, common)** | Skill lives inside a suite directory *and* gets its own root-level marketplace entry. | Users can install the suite or the single skill, either way. | Default choice for anything reusable outside its suite's specific context. |

### Registering a standalone entry

```json
{
  "name": "my-new-skill",
  "source": "./plugins/common-tools/skills/my-new-skill",
  "description": "Concise description of my new skill."
}
```

Add this to the `plugins[]` array in the root `.claude-plugin/marketplace.json`
alongside the suite entries, and update the suite's own `plugin.json`
description to mention the skill is part of it.

---

## Creating Your Own Claude Plugin + Kilo Marketplace in One Repo

This is the actual mechanics behind every repo in this family
(`agentic-coding-kit`, `ai-architect-executor`, `kilo-mcp`,
`gcube-ai-toolkit`) — one repo, both tools, no duplication.

1. **Root manifest** — `.claude-plugin/marketplace.json`:

   ```json
   {
     "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
     "name": "your-repo-name",
     "owner": { "name": "Your Name" },
     "plugins": [
       {
         "name": "your-plugin",
         "description": "What this plugin does.",
         "source": "./plugins/your-plugin"
       }
     ]
   }
   ```

   This alone makes the repo a working **Claude Code marketplace** —
   `claude plugin marketplace add <repo-url>` then `/plugin install
   your-plugin@your-repo-name` works immediately, no extra files needed.

2. **Per-plugin manifest** — `plugins/your-plugin/.claude-plugin/plugin.json`:

   ```json
   {
     "name": "your-plugin",
     "version": "0.1.0",
     "description": "What this plugin does.",
     "author": { "name": "Your Name" }
   }
   ```

3. **That's the whole Claude Code side.** For Kilo Code, you get it two ways
   simultaneously, no extra manifest format to author:
   - `kilo-plugin-manager` (this repo's own `agent-tooling-meta` plugin)
     reads the *same* `.claude-plugin/marketplace.json` and translates
     agent frontmatter on install — nothing to write twice.
   - Kilo's native Skill URLs mechanism needs `index.json` files, which are
     **generated**, not hand-authored — run
     `python3 scripts/generate_skill_indices.py` (see
     [`03-compatibility-and-distribution.md`](03-compatibility-and-distribution.md#kilo-native-skill-urls-indexjson)
     for how it works and when to re-run it) after adding/removing/renaming
     any skill.

You do **not** need to touch the separate official `Kilo-Org/kilo-marketplace`
community repo/YAML format to do any of this — that's for getting listed in
Kilo's own curated catalog, a distribution channel, not a requirement for
your repo to work as a marketplace. See
[`01-concepts.md`](01-concepts.md#marketplace-three-different-mechanisms-not-one)
if that distinction isn't clear.

---

## Skill Authoring Standards

### Directory structure

```text
skills/<skill-name>/
├── SKILL.md                  # Main entry point (mandatory)
├── config/                   # Declarative JSON/YAML config (recommended)
├── scripts/                  # Deterministic executable scripts (recommended)
├── references/               # Detailed docs, loaded on-demand (optional)
├── LICENSE / LICENSE.txt     # Upstream license (mandatory for 3rd-party skills)
├── local.patch               # Diff of local modifications (3rd-party skills only)
└── assets/                   # Templates, images, static resources (optional)
```

### Progressive disclosure

Keep `SKILL.md` itself concise (roughly under 150 lines) — high-level
workflow, script invocation, parameters. Push detailed specs, long code
samples, or big checklists into `references/`, loaded by the agent only
when it actually needs that depth. The point is context budget: don't make
every skill invocation pay for content most invocations won't use.

---

## The Deterministic Script Priority Rule

Prefer a real script (`scripts/*.py`, `*.js`, `*.sh`) over an LLM prompt for
anything that has one correct, reproducible answer.

- **LLM's job**: understanding intent, picking parameters, deciding *when*
  to invoke the skill, interpreting results.
- **Script's job**: file parsing, API calls, regex/text transforms,
  anything where "the same input always produces the same output" matters.

Extract paths/rules/overrides into `config/*.json` rather than hardcoding
them in the script — and if the config is missing or invalid, **fail
loudly**, don't silently fall back to guessed defaults baked into the code.

---

## Bundled Third-Party Skills & Local Patches

When importing a skill from an external open-source repo or community
marketplace:

- **Preserve the license** — keep the original `LICENSE`/`LICENSE.txt`
  inside the skill's own directory, attribute the author.
- **Record local modifications as a patch** — if you adapt an upstream
  skill to local conventions, keep the diff in `local.patch` inside that
  skill's directory, so upstream updates can be re-applied without losing
  the local customization.

---

## Agent Authoring & Synchronization

Claude Code and Kilo Code use genuinely incompatible agent frontmatter —
see [`01-concepts.md`](01-concepts.md#whats-identical-vs-tool-specific).

**Claude Code** (`agents/<name>.md`):

```yaml
---
name: custom-agent
description: Expert assistant for specific tasks.
tools: Bash, Read, Edit, Write, Grep, Glob
---
```

**Kilo Code** (`agents/<name>.md` in a Kilo-side location, or
`agents_kilo/<name>.md` alongside the Claude version in the same plugin —
both conventions exist across this family of repos, check what the
specific plugin already uses):

```yaml
---
name: custom-agent
description: Expert assistant for specific tasks.
mode: primary
permission:
  edit: allow
  bash: allow
---
```

Run the sync script whenever an agent changes, so both variants stay
identical on everything except the frontmatter shape:

```bash
python3 plugins/agent-tooling-meta/skills/kilo-plugin-manager/scripts/plugin_manager.py sync-agents
```

It keeps `name:` identical across variants and mirrors files between the
project-local and global (`~/.kilo/agent/`, `~/.claude/agents/`) locations.

---

## Slash Command / Workflow Authoring

Kilo slash commands live under `workflows/kilo/<command-name>.md`:

```markdown
---
description: Short description shown in Kilo's autocomplete menu.
agent: general
---

High-level instructions for the command.

1. Load the required skill.
2. Run the deterministic helper: `python3 ~/.kilo/skills/<skill>/scripts/<script>.py`.
3. Offer to commit/clean up.
```

Once installed to `~/.config/kilo/command/<name>.md`, it's available as
`/<name>`.

---

## Managing Releases & Updates

1. **Bump version** across `plugin.json` files and `CHANGELOG.md` — no
   automated bump script exists yet in this repo (unlike `gcube-ai-toolkit`'s
   `toolkit-release-manager`, which is repo-specific and not yet
   generalized for reuse here — see that repo if you need the pattern).
2. **Regenerate skill indices** (if any skill was added/removed/renamed):

   ```bash
   python3 scripts/generate_skill_indices.py
   ```

3. **Sync agents** (if any agent frontmatter changed):

   ```bash
   python3 plugins/agent-tooling-meta/skills/kilo-plugin-manager/scripts/plugin_manager.py sync-agents
   ```

4. **Commit and push.**
5. **Client update, on the consuming side**: Claude Code users run
   `/plugin update`; Kilo Code users run
   `python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py update`.
