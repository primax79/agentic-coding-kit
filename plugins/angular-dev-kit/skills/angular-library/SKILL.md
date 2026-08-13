---
name: angular-library
description: >-
  Author and package a reusable Angular library (v20+) shipped as an npm package
  built with ng-packagr. Covers the configuration surface a library exposes
  (provideX() returning EnvironmentProviders), peerDependencies vs dependencies,
  what belongs in public-api.ts, secondary entry points, environment-safe code,
  and the build-from-dist release loop. Use this whenever the code being written
  lives in a library project rather than an application - creating a library,
  adding or changing anything consumers can import, deciding whether something
  should be configurable, resolving an ng-packagr build failure, or preparing a
  release. Triggers on ng-packagr, ng-package.json, public-api.ts, peerDependencies
  errors, "make this configurable", provideX/makeEnvironmentProviders, breaking
  changes, or publishing to an npm registry. For application-side wiring and CLI
  usage see the sibling angular-di and angular-tooling skills instead.
metadata:
  category: development
---

# Angular library authoring

Everything here follows from one constraint: **the consuming application is
unknown and out of your control.** It may be on a different Angular minor, use
a different state library, render on a server, or be built by a team that will
never read your source - only your types and your README.

That single fact is what separates library code from app code. App code can
reach for a global, hardcode an endpoint, or import a sibling feature, and be
corrected next sprint. Library code that does the same becomes someone else's
runtime error, discovered after publish, at which point the fix costs a version
bump and a coordinated upgrade. Most of the rules below are just this constraint
applied to a specific decision.

The sibling `angular-*` skills (component, di, signals, http, routing, testing,
ssr) describe how to write Angular. They assume an application. Use them for the
mechanics, and use this skill for the decisions that change because the code
ships as a package.

## Decide first: does this belong in the library at all?

Before adding anything, ask what happens to a consumer that doesn't want it.

| Signal | What it means |
|---|---|
| You're about to import an app's DI token, route, or feature module | Stop - invert it into an injection token or a config field the app fills in |
| A domain-specific type is appearing in a generic interface | The behaviour belongs in the app; the library should take a strategy |
| The feature is useful to exactly one consumer today | Ship it in that consumer until a second one needs it |
| It only makes sense with a specific backend/deployment | Make it opt-in configuration, not a default |

Adding to a library is cheap; removing is a breaking change. Bias toward
extension points over features.

## Package manifest: dependencies are a contract

The library's own `package.json` (in the library project directory, *not* the
workspace root) is what consumers install. Three buckets, three meanings:

- **`peerDependencies`** - everything you `import` that the app also uses:
  `@angular/core`, `@angular/common`, and any third-party runtime library.
  Declared as a *range*, so the app resolves one shared copy. Two copies of
  Angular, or of an auth SDK holding a singleton, is a class of bug that only
  reproduces in the consumer's build.
- **`dependencies`** - only things safe to duplicate, with no shared state and
  no framework identity. ng-packagr treats this bucket as suspect: any entry
  not in `allowedNonPeerDependencies` **fails the build** with
  `Dependency X must be explicitly allowed using the "allowedNonPeerDependencies" option`.
  `tslib` is the one always-allowed exception.
- **`devDependencies`** - stripped from the published manifest entirely, so
  it's the right home for anything used only to build or test.

Peer ranges are a compatibility promise, not a version pin. `>=20.3.0 <22.0.0`
says "works on Angular 20.3 through 21". Widen it only when you've actually
built against the upper bound; narrow it and you force consumers to upgrade in
lockstep.

## The generated manifest is not the one you wrote

`ng build <lib>` emits a package into the destination folder, and that package's
`package.json` is *derived* from the library's. It keeps your fields and adds
`module`, `typings`, `exports`, `name`, and `sideEffects` (defaulting to
`false`). It also deletes `devDependencies`, `scripts`, `ngPackage`, and a few
tool sections (`prettier`, `browserslist`, `jest`, `workspaces`, `husky`,
`stylelint`).

Two consequences worth internalising:

1. **Publish the built output, never the library source folder or the repo
   root.** The manifest npm reads is the generated one.
2. **Anything that must reach consumers has to live in the library's
   `package.json`** - `publishConfig`, `repository`, `license`, `keywords`,
   `exports` additions. Putting `publishConfig.registry` only at the workspace
   root is a common and expensive mistake: the build succeeds, the publish goes
   to the default public registry.

`references/packaging.md` has the full transformation, `ng-package.json`
options, secondary entry points, and what each ng-packagr error actually means.

## Configuration surface: `provideX()`, not hardcoding

This is the pattern the app-oriented skills don't cover, and the one libraries
need most. A library exposes configuration as a function returning
`EnvironmentProviders`:

```typescript
import { InjectionToken, makeEnvironmentProviders, Provider } from '@angular/core';

export interface DataAccessConfig {
  baseUrl: string;
  /** Optional: consumers that don't set it get the default below. */
  retries?: number;
}

export const DATA_ACCESS_CONFIG = new InjectionToken<Required<DataAccessConfig>>(
  'DATA_ACCESS_CONFIG',
);

export function provideDataAccess(config: DataAccessConfig) {
  return makeEnvironmentProviders([
    {
      provide: DATA_ACCESS_CONFIG,
      useValue: { retries: 3, ...config },
    },
    DataAccessClient,
  ]);
}
```

The app writes one line - `provideDataAccess({ baseUrl: '/api' })` - in its
`ApplicationConfig`, and gets a correctly wired subtree it cannot accidentally
half-configure.

Why `makeEnvironmentProviders` rather than exporting a `Provider[]`: it returns
an opaque `EnvironmentProviders` that is only accepted where environment
providers are legal (`bootstrapApplication`, route `providers`,
`TestBed.configureTestingModule`). Exporting a raw array invites consumers to
spread it into a *component's* `providers`, where your root-scoped services
would silently become per-component instances. The opaque type makes the wrong
usage a compile error instead of a support ticket.

Two habits that keep this honest:

- **Defaults live in the provider, not at the call site.** Consumers should be
  able to pass the minimum and get something that works.
- **Every configuration field gets a copy-pasteable snippet in the README.**
  Configurable but undocumented is functionally the same as hardcoded - nobody
  finds it.

For optional features (`withInterceptor()`, `withDebugLogging()`), consumer-supplied
strategies via injection tokens, multi-provider extension points, and how to test
a `provideX()` function, read `references/configuration-api.md`.

## Public API surface: what you export is what you owe

`public-api.ts` is the contract. Anything reachable through it is something you
cannot rename, retype, or remove without a major bump - including types reached
*indirectly*, e.g. an exported function whose return type is an unexported
interface.

- Export the types consumers need to *name* things (config interfaces, tokens,
  public service classes, strategy interfaces). Keep internals unexported so
  you stay free to refactor them.
- Prefer `export { Thing } from './lib/thing'` over `export *` once the library
  grows past a handful of files - `export *` re-exports tomorrow's accidental
  additions too.
- An interface is a safer public type than a class: it lets consumers implement
  or mock without inheriting your constructor.
- Deprecate before deleting. `@deprecated` with the replacement named, one minor
  of overlap, removal in the next major.

## Environment safety

A library gets loaded in environments its author never ran: server-side
rendering, a test runner without a DOM, a web worker. Touching `window`,
`document`, `localStorage`, or `navigator` at module load or in a constructor
turns into a crash the *consumer* has to debug.

```typescript
import { PLATFORM_ID, inject, afterNextRender } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Injectable({ providedIn: 'root' })
export class TokenStore {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  read(key: string): string | null {
    return this.isBrowser ? localStorage.getItem(key) : null;
  }
}
```

Guard with `isPlatformBrowser`, defer genuinely browser-only initialisation with
`afterNextRender`, and inject browser globals through tokens so tests can
substitute them. The sibling `angular-ssr` skill's token patterns apply here even
when the library will never be server-rendered by *you* - you don't get to decide
that. Third-party SDKs that touch `window` on import are the usual culprit and
need lazy, guarded initialisation.

## Build and release loop

```bash
ng build <lib>              # emits the package into the dest folder
cd <dest>                   # publish from there, never from the source project
npm publish
```

- **Versions are immutable.** Bump before every publish. Unpublishing leaves
  anyone who already installed with a lockfile pointing at a missing tarball.
- **Verify before publishing** - `npm pack --dry-run` in the dest folder lists
  exactly what ships. Check the manifest's `name`, `version`, `peerDependencies`,
  `exports`, and `publishConfig`.
- **Test against the built package, not the source.** A local install
  (`npm pack` then install the tarball, or `npm link`) is the only way to catch
  a missing export or a wrong peer range before a consumer does.
- If the build injects a `prepublishOnly` guard that refuses to publish, the
  library was compiled in full rather than partial mode - rebuild, don't work
  around it. Partial compilation is what lets one published artifact work across
  Angular versions.

## Traps worth re-reading before a release

- A runtime `import` that isn't in `peerDependencies` or `dependencies` - builds
  fine locally because the workspace has it hoisted, explodes for consumers.
- `publishConfig` at the workspace root instead of the library's `package.json`.
- Publishing from the source project directory instead of the built output.
- A type exported indirectly, quietly widening the public API.
- A new required config field added without a default - a breaking change even
  though nothing was removed.
- `providedIn: 'root'` on a service that needs configuration: it becomes
  reachable *before* `provideX()` runs. Provide it from `provideX()` instead.
