# Kilo Skill URLs: stale, unremovable cache — problem summary

## Symptom

A fresh, empty test workspace (`/Users/Alfredo/works/test_agent-tooling-meta_kilo`,
no local `.kilo/` at all) listed 11 "available skills" via Kilo that did
not match the actual global `~/.kilo/skills/` state (~28 skills, rebuilt
earlier the same day from `agent-tooling-meta`, `common-tools`,
`third-party-skills`, `architect-executor`, `kilo-mcp`). The list included
skills under their **old, pre-rename names/content** — `kilo-task-delegation`
(now `task-delegation`, moved to `ai-architect-executor`'s
`architect-executor` plugin) and `toolkit-release-manager` (gcube-specific,
deliberately never installed globally) — alongside real current skills like
`kilo-plugin-manager`. One entry, `kilo-config`, matched nothing in any of
our marketplaces — likely a Kilo built-in, unrelated to this bug.

## Root cause

Kilo maintains a **second, separate skill location**:
`~/.cache/kilo/skills/<name>/`, populated only by the native **Skill URLs**
mechanism (`kilo.jsonc`'s `skills.urls` array — the zero-tooling,
skills-only fetch path documented as the bootstrap step for
`kilo-plugin-manager` itself). This is distinct from `~/.kilo/skills/`,
where `kilo-plugin-manager`'s own tracked `install` places content.

Found 19 stale entries in `~/.cache/kilo/skills/` — an accumulation from
every Skill-URL fetch ever performed on this machine, including from before
this session's repo restructuring:

```text
agent-md-refactor  changelog-generator  file-organizer  frontend-design
gitignore  grill-me  kilo-claude-sync  kilo-plugin-manager
kilo-scope-manager  kilo-task-delegation  macroplan-authoring
markdown-formatter  mcp-builder  playwright  roocode-migrator
skill-creator  terraform  theme-factory  toolkit-release-manager
```

Kilo surfaces skills from **both** locations when listing what's
"available". The exact precedence, characterized in a follow-up session
against `packages/opencode/src/skill/index.ts`: `discoverSkills` scans
sources in a fixed order — external dirs (`.claude`/`.agents`) → config
dirs (this is where `~/.kilo/skills/` is scanned) → `skills.paths` →
**`skills.urls` last** (the cache). `loadSkills`/`add()` then walks the
matches in that same order and does `state.skills[name] = {...}`
**unconditionally** — a name collision only logs a warning, it never skips
the overwrite. Net effect: this is not merely "both locations show up
side by side" — a stale cache entry **silently wins over and replaces** a
correctly-installed skill of the same name, because the cache is always
scanned last. In this incident most stale names didn't collide with
current ones (hence extra/wrong entries rather than silent shadowing), but
a same-name collision would have been strictly worse and gone unnoticed
past the easy-to-miss duplicate-name warning log.

**Why the cache never self-heals**: Kilo's Skill-URL downloader
(`discovery.ts`'s `download()`) skips fetching a file if one already
exists at the destination path — no ETag check, no content hash, no
version comparison. Once a skill is pulled via `skills.urls`, it is frozen
at that exact version forever; a later change to the source repo is never
picked up by re-adding the same URL.

**Why it can't be cleaned up through Kilo itself**: Kilo's own
skill-removal code (`skill-remove.ts`) explicitly does not delete files
under `~/.cache/kilo/skills/` for URL-backed skills — it only removes the
URL from `skills.urls` in config ("remove URL-backed skills from
configuration"), leaving the stale files in place indefinitely.

## Fix applied

```bash
rm -rf ~/.cache/kilo/skills
```

Direct filesystem removal — the only way, since no Kilo command reaches
this path. Confirmed empty afterward; skill availability should now
resolve purely from `~/.kilo/skills/` (the properly tracked, correct set).

## Recommendation for the docs — implemented

Done, in a follow-up session:

- [`QUICKSTART-KILO.md`](../QUICKSTART-KILO.md) step 1 — bootstrap note
  extended with the write-once-cache/no-removal warning.
- [`docs/03-compatibility-and-distribution.md`](../docs/03-compatibility-and-distribution.md#kilo-native-skill-urls-indexjson) —
  "Why this should only ever be used for the one-time bootstrap above",
  the canonical full writeup (cache semantics + this doc's precedence
  finding).
- [`plugins/agent-tooling-meta/skills/kilo-plugin-manager/SKILL.md`](../plugins/agent-tooling-meta/skills/kilo-plugin-manager/SKILL.md) §3 —
  same analysis, read directly by the agent before it would otherwise reach
  for `skills.urls` as a shortcut.

All three now say the same thing: `skills.urls` is bootstrap-only,
single-use, fine only for fetching `kilo-plugin-manager` itself before any
tracked mechanism exists (`QUICKSTART-KILO.md` step 1) — every other
install goes through `kilo-plugin-manager`'s own `install`
(trackable, updatable, actually uninstallable).

Still worth doing by hand on any older machine that used Skill URLs before
this convention existed: `ls ~/.cache/kilo/skills/` and
`rm -rf ~/.cache/kilo/skills` if it's not currently needed as a bootstrap
trampoline — it has no version guarantee and, per the precedence finding
above, can silently shadow a correctly-installed skill of the same name
rather than just sitting there unused.

## Upstream

Filed: [`Kilo-Org/kilocode#12907`](https://github.com/Kilo-Org/kilocode/issues/12907)
(text drafted in [`kilo-skill-url-cache-bug-issue.md`](kilo-skill-url-cache-bug-issue.md)).
See [`kilo-skill-url-cache-fix-spec.md`](kilo-skill-url-cache-fix-spec.md)
for the fix design, and [`kilo-skill-url-cache-fix.patch`](kilo-skill-url-cache-fix.patch)
for a working patch (P0 collision precedence + P1 real cache removal,
implemented and typechecked against `packages/opencode` — 0 errors —
but not run through the actual test suite: this machine has no `bun`
installed, and the tests use `bun:test`). Not yet opened as a PR — that
needs a fork + push + `gh pr create` (or the GitHub web UI).
