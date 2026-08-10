# Designing a library's configuration and extension API

How a library lets an application configure it, extend it, and replace parts of
it — without the library knowing anything about that application.

## Contents

- [The provideX() function](#the-providex-function)
- [Composable features: withX()](#composable-features-withx)
- [Configuration tokens and defaults](#configuration-tokens-and-defaults)
- [Extension points consumers implement](#extension-points-consumers-implement)
- [Multi-provider registries](#multi-provider-registries)
- [Initialisation that must run at startup](#initialisation-that-must-run-at-startup)
- [Injecting browser globals](#injecting-browser-globals)
- [Route- and component-scoped configuration](#route--and-component-scoped-configuration)
- [Testing the configuration API](#testing-the-configuration-api)
- [Evolving the API without breaking consumers](#evolving-the-api-without-breaking-consumers)

## The provideX() function

The entry point of a modern Angular library is a function returning
`EnvironmentProviders`:

```typescript
import { InjectionToken, makeEnvironmentProviders } from '@angular/core';

export interface DataAccessConfig {
  baseUrl: string;
  retries?: number;
  timeoutMs?: number;
}

type ResolvedConfig = Required<DataAccessConfig>;

export const DATA_ACCESS_CONFIG = new InjectionToken<ResolvedConfig>('DATA_ACCESS_CONFIG');

const DEFAULTS = { retries: 3, timeoutMs: 30_000 } satisfies Omit<ResolvedConfig, 'baseUrl'>;

export function provideDataAccess(config: DataAccessConfig) {
  return makeEnvironmentProviders([
    { provide: DATA_ACCESS_CONFIG, useValue: { ...DEFAULTS, ...config } },
    DataAccessClient,
  ]);
}
```

Consumer side, one line:

```typescript
bootstrapApplication(App, {
  providers: [provideHttpClient(), provideDataAccess({ baseUrl: '/api' })],
});
```

Design notes:

- **Return `EnvironmentProviders`, not `Provider[]`.** `makeEnvironmentProviders`
  produces an opaque value accepted only where environment providers are valid —
  `bootstrapApplication`, a `Route`'s `providers`, `TestBed.configureTestingModule`.
  A raw array can be spread into a component's `providers`, which quietly turns
  root singletons into per-component instances. Making the mistake unrepresentable
  is cheaper than documenting it.
- **Don't use `providedIn: 'root'` for services that need config.** Tree-shaking
  is not worth the failure mode: the service becomes injectable before
  `provideDataAccess()` has run, so the first consumer who forgets the call gets
  an obscure missing-token error deep in your code instead of at bootstrap.
  Services with no configuration are fine as `providedIn: 'root'`.
- **Resolve defaults inside the function.** The consumer passes the minimum; the
  token always holds a fully populated object, so nothing downstream deals with
  `undefined`.

## Composable features: withX()

When parts of a library are optional, mirror Angular's own
`provideHttpClient(withInterceptors(...))` shape rather than growing a config
object with boolean flags:

```typescript
export interface DataAccessFeature {
  readonly kind: symbol;
  readonly providers: Provider[];
}

const CACHING = Symbol('caching');
const LOGGING = Symbol('logging');

export function withCaching(options: CacheOptions = {}): DataAccessFeature {
  return { kind: CACHING, providers: [{ provide: CACHE_OPTIONS, useValue: options }, CacheLayer] };
}

export function withRequestLogging(): DataAccessFeature {
  return { kind: LOGGING, providers: [{ provide: HTTP_LOGGER, useClass: ConsoleLogger }] };
}

export function provideDataAccess(config: DataAccessConfig, ...features: DataAccessFeature[]) {
  return makeEnvironmentProviders([
    { provide: DATA_ACCESS_CONFIG, useValue: { ...DEFAULTS, ...config } },
    DataAccessClient,
    ...features.flatMap(f => f.providers),
  ]);
}
```

```typescript
provideDataAccess({ baseUrl: '/api' }, withCaching({ ttlMs: 60_000 }))
```

Why this beats `{ caching: true, cacheTtl: 60000, logging: false }`: unused
features are never referenced, so they tree-shake away; each feature owns its own
options type instead of flattening everything into one interface; and adding a
feature later is additive rather than another optional field. The `kind` symbol
lets `provideDataAccess` detect duplicates or incompatible combinations and throw
a clear error at bootstrap.

## Configuration tokens and defaults

```typescript
// Simple value, with a factory default so it's always injectable.
export const API_TIMEOUT = new InjectionToken<number>('API_TIMEOUT', {
  providedIn: 'root',
  factory: () => 30_000,
});
```

A token with a `factory` default never fails to inject, which suits genuinely
optional knobs. A token without one fails loudly when `provideX()` wasn't called —
the better choice for configuration that has no sensible default, because the
error arrives at startup rather than as wrong behaviour later.

Always pass the description string (`'API_TIMEOUT'`): it's what appears in
injector error messages, and a consumer debugging a `NullInjectorError` from a
library they didn't write needs that name.

## Extension points consumers implement

When behaviour depends on the application's domain, the library defines the
*shape* and the app supplies the implementation. This is what keeps a generic
interface generic.

```typescript
// In the library — no domain types anywhere.
export interface PermissionChecker<TResource> {
  canAccess(resource: TResource, action: string): boolean;
}

export const PERMISSION_CHECKER = new InjectionToken<PermissionChecker<unknown>>(
  'PERMISSION_CHECKER',
);
```

```typescript
// In the consuming app.
providers: [{ provide: PERMISSION_CHECKER, useClass: AppPermissionChecker }]
```

The pressure to add a concrete domain type to an interface like this is the
clearest signal that a change belongs in the app, not the library. If a specific
consumer's rule is creeping into the library's types, the extension point is
doing its job by making that visible — take the hint.

Decide explicitly whether the token is required or optional:

```typescript
private readonly checker = inject(PERMISSION_CHECKER, { optional: true }) ?? PERMISSIVE_DEFAULT;
```

Optional-with-fallback keeps the library usable out of the box; required forces a
decision. Pick one deliberately and say which in the README.

## Multi-provider registries

For extension points that accept several contributions:

```typescript
export const REQUEST_ENRICHERS = new InjectionToken<RequestEnricher[]>('REQUEST_ENRICHERS');

export function withRequestEnricher(enricher: Type<RequestEnricher>): DataAccessFeature {
  return {
    kind: ENRICHER,
    providers: [{ provide: REQUEST_ENRICHERS, useClass: enricher, multi: true }],
  };
}
```

Inject as an array; note it's absent (not empty) when nothing registered, so
either provide a `[]` default or inject with `{ optional: true }`. Order follows
provider registration order — if that matters to your semantics, document it,
because consumers cannot easily reason about it otherwise.

## Initialisation that must run at startup

```typescript
import { provideAppInitializer, inject } from '@angular/core';

export function provideDataAccess(config: DataAccessConfig) {
  return makeEnvironmentProviders([
    { provide: DATA_ACCESS_CONFIG, useValue: { ...DEFAULTS, ...config } },
    DataAccessClient,
    provideAppInitializer(() => inject(DataAccessClient).warmUp()),
  ]);
}
```

`provideAppInitializer` returns `EnvironmentProviders` and composes directly into
the array. Use it sparingly: every initializer delays the consumer's first paint,
and a library that blocks bootstrap on a network call it didn't warn about is a
poor citizen. Prefer lazy initialisation on first use; reserve initializers for
things that genuinely must be settled before the app renders (session restore,
runtime config fetch), and make them opt-in via a feature when there's any doubt.

## Injecting browser globals

Referencing `window`, `document`, or `localStorage` directly makes the library
unusable server-side and awkward to test. Route them through tokens:

```typescript
export const WINDOW = new InjectionToken<Window | null>('WINDOW', {
  providedIn: 'root',
  factory: () => (typeof window === 'undefined' ? null : window),
});
```

Consumers rendering on a server get `null` and code that checks; tests provide a
stub. For work that only makes sense once the DOM exists, `afterNextRender`
combined with an `isPlatformBrowser` guard is the safest pairing — see the
`angular-ssr` skill for the wider set of patterns.

## Route- and component-scoped configuration

`EnvironmentProviders` also work in a route's `providers`, giving one lazily
loaded area its own configured instance:

```typescript
export const routes: Routes = [
  {
    path: 'reports',
    providers: [provideDataAccess({ baseUrl: '/reports-api' })],
    loadChildren: () => import('./reports/routes'),
  },
];
```

If your library is meant to support this, say so in the README and avoid module-level
mutable state — two configured instances must not interfere. If it isn't meant to,
say that too; consumers will otherwise assume it works.

## Testing the configuration API

Test `provideX()` the way a consumer uses it, not by instantiating services by
hand — that's the only way the wiring itself is covered:

```typescript
TestBed.configureTestingModule({
  providers: [provideDataAccess({ baseUrl: '/test-api' })],
});

const client = TestBed.inject(DataAccessClient);
expect(TestBed.inject(DATA_ACCESS_CONFIG).retries).toBe(3);   // default applied
```

Worth covering explicitly:

- defaults are applied when optional fields are omitted
- each `withX()` feature actually registers what it claims
- a required extension-point token missing produces a comprehensible error
- the library works with only its documented peers present

## Evolving the API without breaking consumers

- **Adding an optional config field with a default** — safe.
- **Adding a required field** — breaking, even though nothing was removed. Add it
  as optional with a default and tighten in the next major.
- **Renaming a token** — breaking, including when the string description is
  unchanged: identity is the token object, so a consumer providing the old one
  silently stops taking effect. That silence is why token renames deserve a major
  bump even when they look cosmetic.
- **Changing a default** — a behaviour change; treat as breaking if consumers
  could reasonably depend on the old value.
- **Deprecating** — mark with `@deprecated` naming the replacement, keep both
  working for at least one minor, remove in the next major.
