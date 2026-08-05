# Issue text for Kilo-Org/kilocode

Posted as [`Kilo-Org/kilocode#12907`](https://github.com/Kilo-Org/kilocode/issues/12907).
Field names below match the bug-report template. The fix/PR offer is
intentionally left out for now — planned as a follow-up comment once we
get back to it.

---

**Title**: `skills.urls` cache never invalidates and can silently shadow a
correctly-installed skill of the same name

## Description

Skills fetched via the native `skills.urls` config mechanism
(`kilo.jsonc`'s `{"skills": {"urls": [...]}}`, and the equivalent Skills
tab in Settings) are cached under `~/.cache/kilo/skills/<name>/` and never
refreshed after the first fetch — there is no ETag check, content hash, or
version comparison. Re-adding the same URL later (e.g. after the source
repo changed) silently keeps serving the stale copy.

This is worse than a "just re-fetch to update" inconvenience: because
`skills.urls` is discovered *after* every other skill source (project/
global skill directories), and skill discovery resolves name collisions by
unconditional last-write-wins (only a warning is logged, the write is
never skipped), **a stale cache entry silently overrides a
properly-installed skill of the same name** picked up from
`~/.kilo/skills/` or a project's `.kilo/skills/`. There's no error, no
visible indication in the UI — only an easy-to-miss log line
("duplicate skill name").

On top of that, there is no supported way to clear a cached entry: the
skill-removal code path explicitly refuses to delete anything under
`~/.cache/kilo/skills/`, throwing "remove URL-backed skills from
configuration" instead of removing the files. Removing the URL from config
only stops future *loading* — the stale files remain on disk indefinitely,
still eligible to be picked up again if the URL (or another URL serving a
skill with the same declared `name`) is ever re-added.

### Root cause (source-verified against `Kilo-Org/kilocode` @ `1a3c719175`, v7.4.15)

- `packages/opencode/src/skill/discovery.ts`, `download()`: skips the HTTP
  fetch entirely if the destination file already exists — no cache
  invalidation of any kind.
- `packages/opencode/src/skill/index.ts`, `discoverSkills()`: scans
  sources in a fixed order — external dirs (`.claude`/`.agents`) → config
  dirs (`~/.kilo`, project `.kilo`/`.kilocode`, etc.) → `skills.paths` →
  **`skills.urls` last**.
- Same file, `loadSkills()`/`add()`: iterates matches in that same order
  and does `state.skills[name] = {...}` unconditionally on every match —
  a name collision only calls `Effect.logWarning("duplicate skill name",
  ...)`, it never skips the overwrite. Because `skills.urls` is scanned
  last, its entries always win any name collision.
- `packages/opencode/src/kilocode/skill-remove.ts`, `target()`: explicitly
  throws `"remove URL-backed skills from configuration"` for any skill
  whose location resolves inside `~/.cache/kilo/skills/`, so the normal
  skill-removal path cannot clean these up.

### Impact observed in practice

A team using `skills.urls` once (as a bootstrapping mechanism for an
internal plugin manager skill, since Kilo has no other zero-tooling way to
fetch a first skill onto a fresh machine) accumulated 19 stale cached
skills over time, including renamed/superseded ones. A brand-new,
completely empty test workspace (no local `.kilo/` at all) still listed
those 19 stale skills as "available", several under names/content that no
longer matched any current source — pure cache contamination, invisible
without manually inspecting `~/.cache/kilo/skills/`.

## Steps to reproduce

1. Add a Skill URL pointing at an `index.json`-serving skill (any repo
   using Kilo's Skill URL manifest format) to `skills.urls` in `kilo.jsonc`.
   `/reload`. Confirm the skill is now available.
2. Separately install a skill with the **same declared `name`** into
   `~/.kilo/skills/<name>/` (e.g. via a proper marketplace-based installer,
   or just by hand) with **different content**.
3. `/reload` again, or start a fresh session. Ask which version of the
   skill is loaded / check its content via the skill's own location field.
4. Observe: the `skills.urls`-cached copy is the one loaded, silently
   overriding the one just installed in step 2 — with only a
   `duplicate skill name` log line as evidence, nothing user-facing.
5. Separately: edit the source the URL in step 1 points to (change the
   skill's content), keep the URL in `skills.urls` unchanged, `/reload`.
   Observe the old content is still served — no re-fetch ever happens.
6. Try to remove the cached skill through any normal Kilo removal path
   (Settings UI skill list, if exposed, or the underlying skill-remove
   code path). Observe it's refused / doesn't delete the cache files.

## Suggested fix direction

- **Cache invalidation**: check the manifest's declared file list/hash (or
  at minimum a `Last-Modified`/`ETag` from the HTTP response) before
  skipping a download, instead of "exists on disk" being sufficient.
- **Collision precedence**: don't let a `skills.urls` cache entry win a
  name collision against a skill loaded from any other source (or at
  minimum surface the collision somewhere more visible than a debug-level
  log line).
- **Real removal support**: `skill-remove.ts` should be able to actually
  delete a cache-backed skill's directory under `~/.cache/kilo/skills/`,
  not just refuse and point at "remove URL-backed skills from
  configuration" — which doesn't clean up anything on disk.
- **Cache keying**: consider keying the cache by `(source URL, skill
  name)` rather than skill `name` alone, since two different `skills.urls`
  sources publishing a skill under the same name currently collide in the
  same `~/.cache/kilo/skills/<name>/` directory regardless of origin.

## Kilo version

v7.4.15 (`Kilo-Org/kilocode` @ commit `1a3c719175`)

## Plugins

N/A — reproducible with `skills.urls` alone, no third-party plugin
required.

## Operating System

macOS (reported); nothing in the code path is OS-specific — XDG cache dir
resolution (`~/.cache/kilo` via `xdg-basedir`) applies the same way on
Linux, and the equivalent Windows path should exhibit identical behavior.

## Terminal

N/A — not terminal-specific; reproducible via `kilo run` from any shell or
via the VS Code extension's Settings UI.
