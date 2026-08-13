---
name: markdown-formatter
description: "Use this skill to format Markdown (`.md`) files in the workspace. This skill strictly delegates all formatting tasks to David Anson's `markdownlint` library (via `markdownlint --fix` or `npx --yes markdownlint-cli --fix`). The agent MUST NOT spend time performing manual formatting edits."
---

# Skill: markdown-formatter

## When to use
Use this skill to format Markdown (`.md`) files in the workspace. This skill strictly delegates all formatting tasks to David Anson's `markdownlint` library (via `markdownlint --fix` or `npx --yes markdownlint-cli --fix`). The agent MUST NOT spend time performing manual formatting edits.

## Workflow

### 1. Never create a `.markdownlint.json` in the target project

**Do not scatter config files across projects.** The rule config lives
**once**, bundled next to this `SKILL.md` (`.markdownlint.json` in this
same skill directory):

```json
{
  "default": true,
  "MD013": false,
  "MD024": {
    "siblings_only": true
  },
  "MD051": false
}
```

`MD051` (link-fragments) is disabled because this pipeline always
regenerates the TOC via `scripts/update-toc.js` before linting - its own
slug algorithm guarantees valid fragments, so MD051 only ever fires as a
transient false positive on an in-progress edit (heading text changed,
TOC not yet regenerated), never on a real broken link.

Always invoke `markdownlint-cli` with `--config` pointing at **this
skill's own** `.markdownlint.json` - never write one into the workspace
being formatted:

```bash
npx --yes markdownlint-cli --fix --config ~/.kilo/skills/markdown-formatter/.markdownlint.json <file_paths>
```

### 2. Delegate Formatting to markdownlint
- **CRITICAL:** DO NOT perform manual edits or string replacements to fix formatting issues.
- **CRITICAL:** DO NOT create a `.markdownlint.json` (or any dotfile) inside the target project - always pass `--config` pointing at this skill's own copy (step 1).
- Let the official CLI handle the rewrite of the files.

### 3. Format Tables

`markdownlint --fix` formats everything EXCEPT tables. Run the bundled table
formatter (a faithful, dependency-free port of the "Markdown All in One" VS Code
extension's algorithm) AFTER markdownlint, so the pair reproduces the full
two-plugin editor workflow (markdownlint + Markdown All in One) from the CLI:

```bash
node "$(dirname SKILL.md)/scripts/format-tables.js" <file_paths>
```

Concretely, from the skill directory:

```bash
node scripts/format-tables.js <file_paths>
```

It rewrites only GFM table blocks (aligned columns, alignment markers, padded
delimiter rows; CJK/emoji counted as double-width), skips fenced code blocks, and
is idempotent. Everything outside tables is left byte-for-byte untouched.

### 4. Update Tables of Contents (optional)

For files that use an explicit TOC block, refresh it with the bundled generator (a
dependency-free port of "Markdown All in One"'s TOC, GitHub slug mode):

```bash
node scripts/update-toc.js [--levels 2-6] [--marker -] <file_paths>
```

It regenerates the list ONLY between `<!-- toc -->` and `<!-- /toc -->` markers
(creating the closing marker if missing); files without a `<!-- toc -->` marker are
left untouched. GitHub-compatible anchor slugs, duplicate `-1`/`-2` suffixes,
skips code fences, and honours `<!-- omit in toc -->` on a heading. Default levels
are H2-H6 (pass `--levels 1-6` to include the H1 title).

### 5. Full pipeline

Run in this order (each step is idempotent and conflict-free):

```bash
node scripts/update-toc.js <files>          # only affects files with a TOC marker
npx --yes markdownlint-cli --fix --config "$(pwd)/.markdownlint.json" <files>  # run from this skill's directory, or use its absolute path
node scripts/format-tables.js <files>
```

### 6. Providing Rule Explanations
- When a user asks for information or explanations about specific markdown rules, consult `Rules.md` within this skill directory.
- Provide clear and concise summaries based on the rule definitions found in `Rules.md`.
