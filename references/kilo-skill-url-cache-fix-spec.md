# Fix spec: `skills.urls` caching, precedence, and removal

Companion to [`kilo-skill-url-cache-bug-summary.md`](kilo-skill-url-cache-bug-summary.md)
(incident) and [`kilo-skill-url-cache-bug-issue.md`](kilo-skill-url-cache-bug-issue.md)
(upstream report). This describes the *intended* behavior and prioritizes
which parts are worth fixing first. Verified against
`Kilo-Org/kilocode` @ `1a3c719175` (v7.4.15).

## Priority order

Ranked by severity - P0 is silent data corruption (a skill silently
becomes the wrong one), P3 is a cosmetic edge case:

| # | Problem | Fix |
| - | --- | --- |
| P0 | Stale cache entry silently overrides a correctly-installed skill of the same name | Collision precedence: don't let a less-trusted match overwrite a more-trusted one |
| P1 | No supported way to delete a cache-backed skill | Let `skill-remove.ts` actually delete cache directories |
| P2 | Cache never invalidates even when the source changes | Conditional re-fetch (ETag/Last-Modified), not "exists on disk" |
| P3 | Cache keyed by name only, not by source | Key by `(url, name)` - lower priority, has UX tradeoffs |

## P0 - Collision precedence

**Current behavior** (`packages/opencode/src/skill/index.ts`): `discoverSkills`
scans sources in a fixed order (external dirs → config dirs, i.e.
`~/.kilo/skills/` and friends → `skills.paths` → `skills.urls` last).
`loadSkills`/`add()` walks matches in that order and does
`state.skills[name] = {...}` unconditionally on every match; a name
collision only logs a warning, never skips the overwrite. Net effect:
`skills.urls` entries always win any name collision, silently, because
they're scanned last.

**Intended behavior**: a skill loaded from a directory-based source
(built-in, project/global `skills/` directories, explicit `skills.paths`)
should never be silently replaced by a same-named entry pulled from
`skills.urls` - the whole point of `skills.urls` is a *lightweight
bootstrap*, not a mechanism that should be able to shadow deliberate,
tracked installs. Concretely: track which "trust tier" produced each
loaded skill, and on a name collision, keep the existing entry unless the
new match is at least as trusted.

**Note on a tempting but wrong shortcut**: `Match` already carries a
`trusted: boolean`. It's tempting to reuse it for this, but `trusted` means
something unrelated - whether `{file:}`/`{env:}` substitutions in the
skill's own markdown may read outside its directory. A project's own
`.kilo/skills/<name>/SKILL.md` is `trusted: false` under that definition,
exactly like a `skills.urls` cache entry - gating on `trusted` would also
block a legitimate local project skill from overriding a cache entry,
which is not the bug being fixed here.

**Correct approach**: add a dedicated `fromCache?: boolean` on `Match`,
set only where `skills.urls` results are scanned, plus a parallel
`fromCache: Record<string, boolean>` on `State` (internal only - no change
to the public `Info` schema or to `kilo.jsonc`'s config shape). On a name
collision, only refuse the overwrite when the *existing* entry is
non-cache and the *new* match *is* cache-sourced - every other
combination (including two non-cache sources colliding, which is
unaffected by this bug) keeps today's last-scanned-wins behavior:

```ts
type State = {
  skills: Record<string, Info>
  dirs: Set<string>
  fromCache: Record<string, boolean>   // NEW
}

type Match = {
  path: string
  trusted: boolean
  root?: string
  sourceRoot?: string
  fromCache?: boolean                  // NEW - set only for skills.urls matches
}
```

```ts
// in add():
const existing = state.skills[md.data.name]
if (existing) {
  const existingFromCache = state.fromCache[md.data.name] ?? false
  if (!existingFromCache && match.fromCache) {
    yield* Effect.logWarning(
      "duplicate skill name - ignoring skills.urls cache match, keeping existing non-cache entry",
      { name: md.data.name, kept: existing.location, ignored: match.path },
    )
    return
  }
  yield* Effect.logWarning("duplicate skill name", {
    name: md.data.name, existing: existing.location, duplicate: match.path,
  })
}
state.dirs.add(path.dirname(match.path))
state.fromCache[md.data.name] = match.fromCache ?? false
state.skills[md.data.name] = { name: md.data.name, description: md.data.description, location: match.path, content: md.content }
```

```ts
// in discoverSkills(), the skills.urls loop:
for (const url of cfg.skills?.urls ?? []) {
  const pulledDirs = yield* discovery.pull(url)
  for (const dir of pulledDirs) {
    yield* scan(state, dir, SKILL_PATTERN, { root: dir, fromCache: true })
  }
}
```

This is backward compatible: no config format change, no schema change to
anything that gets serialized, and every non-cache collision case behaves
exactly as before. The only observable behavior change is that a
`skills.urls` entry can no longer clobber an already-loaded non-cache
skill - exactly the fix needed, nothing more. Implemented and verified
locally against `Kilo-Org/kilocode` @ `1a3c719175`
(`packages/opencode/src/skill/index.ts`).

## P1 - Real removal for cache-backed skills

**Current behavior** (`packages/opencode/src/kilocode/skill-remove.ts`):
`target()` throws `"remove URL-backed skills from configuration"` for any
skill whose `location` resolves inside `~/.cache/kilo/skills/`. `remove()`
only ever `unlink()`s the single `SKILL.md` file for everything else
(deliberately, to avoid recursively deleting a local/project directory
that might hold unrelated user files alongside the skill).

**Intended behavior**: a cache-backed skill's entire directory was written
exclusively by the `skills.urls` downloader (`discovery.ts`'s `download()`
writes every file the manifest lists into `cache/<name>/`) - there is
nothing else in there to preserve, unlike a hand-authored local skill
directory. Removal should delete that whole directory, not refuse.

```ts
import { rm, unlink } from "node:fs/promises"

function cacheRootFor(file: string): string | undefined {
  const cache = path.join(Global.Path.cache, "skills")
  const relative = path.relative(cache, file)
  const insideCache = relative !== "" && !relative.startsWith("..") && !path.isAbsolute(relative)
  return insideCache ? path.dirname(file) : undefined
}

export async function remove(location: string, skills: readonly Info[]) {
  const file = target(location, skills)
  const cacheDir = cacheRootFor(file)
  if (cacheDir) {
    await rm(cacheDir, { recursive: true, force: true })
    return
  }
  await unlink(file)
}
```

`target()` keeps all its existing validation (builtin check, must be
absolute, must reference `SKILL.md`) - only the final cache-dir branch
changes, from "throw" to "compute the directory to recursively remove".

## P2 - Cache invalidation (lower priority, more invasive)

Two options, in order of preference:

1. **Conditional HTTP requests**: on every `pull(url)`, still re-fetch
   `index.json` (cheap - it's small), and for each listed file, issue the
   download request with `If-None-Match`/`If-Modified-Since` from a
   locally-stored ETag/Last-Modified (recorded alongside the cached file,
   e.g. a sibling `.meta.json`). A `304` means the local copy is current;
   anything else means re-download. Works with any static host that
   supports conditional requests (GitHub raw URLs do). No manifest schema
   change required.
2. **Manifest-declared content hash**: extend `IndexSkill` in
   `discovery.ts` with a per-file hash, and compare against a locally
   stored hash before skipping. More precise, but a breaking-ish schema
   addition - every `index.json` generator (including this repo's
   `scripts/generate_skill_indices.py`) would need updating, and older
   manifests without hashes would need a defined fallback (e.g. treat
   "no hash present" as "always re-fetch", degrading gracefully rather
   than silently staying wrong).

Recommend (1): no format break, works with the hosting this mechanism
already assumes (raw file URLs), and directly fixes the reported
staleness without asking every downstream manifest generator to change.

## P3 - Cache keying by source (optional, has tradeoffs)

Currently `root = path.join(cache, skill.name)` - two different
`skills.urls` sources publishing a skill under the same name collide in
the same directory. Keying by `(url, name)` instead
(`path.join(cache, shortHash(baseUrl), skill.name)`) would fix this, but
makes the cache path unpredictable from the skill name alone - every
existing doc/script in this family that references
`~/.cache/kilo/skills/kilo-plugin-manager/...` directly would need the
hash to look it up. Given collisions require two *different* marketplaces
independently choosing the identical skill name, and P0's trust-precedence
fix already prevents the dangerous case (an untrusted cache entry
silently beating a trusted one), this is a nice-to-have, not urgent -
worth revisiting only if upstream considers the predictable path a
non-goal anyway.

## Out of scope for this spec

- Changing `skills.urls` to also support Agents/Commands (a real
  limitation, but unrelated to the caching/precedence bugs here - see
  `kilo-plugin-manager/SKILL.md` §2 for why `kilo-plugin-manager` remains
  necessary regardless of any fix here).
- Any change to `kilo-plugin-manager`'s own behavior - it already sidesteps
  all of this by installing into `~/.kilo/skills/` with real tracking.
