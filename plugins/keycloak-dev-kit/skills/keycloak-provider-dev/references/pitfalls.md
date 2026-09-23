# Pitfalls (each one observed, on 26.7.x unless stated)

## Well-known media types

`RealmsResource.getWellKnown` is annotated
`@Produces({application/json, application/jwt})`, and `getWellKnownResponse`
types a `String` result as `application/jwt`, anything else as JSON. So:

- you **cannot** choose another media type from a `WellKnownProvider`
  (e.g. `application/entity-statement+jwt` for OpenID Federation);
- a client sending a strict `Accept: <your type>` gets **406 before your
  provider runs**.

Observed (no provider deployed): direct, no `Accept` → `404 application/json`;
direct, strict `Accept` → `406`. Setting `Content-Type` through
`session.getContext().getHttpResponse().setHeader(...)` from `getConfig()`
does not help: RESTEasy Reactive re-applies the JAX-RS response headers
afterwards. Workarounds: a reverse-proxy rule that rewrites `Accept` to
`application/jwt` and replaces `Content-Type`
(`proxy_set_header Accept "application/jwt"; proxy_hide_header Content-Type;
add_header Content-Type "<type>" always;`), or a `@PreMatching` request filter
(with `META-INF/beans.xml`) that rewrites the path to your own
`RealmResourceProvider` resource with the right `@Produces`. Report upstream.
Also: the well-known response is `Cache-Control: no-cache, no-store` and
`getConfig()` runs on every request - any caching is yours.

## Silent non-loading

- Missing/misspelled `META-INF/services` file → provider absent, no error.
- Exception in `init`/`postInit` → may abort startup or only disable the
  provider depending on the SPI; read the log.
- `EnvironmentDependentProviderFactory.isSupported` false → absent from
  `serverinfo`.

## Classpath

- Unrelocated shaded libraries clash with Keycloak's own (flat Quarkus
  classpath). Relocate always.
- Private classes move between modules: e.g. `ClusterAwareScheduledTaskRunner`
  is in `keycloak-model-storage-private`, not `keycloak-services`. Compile
  errors after a Keycloak bump usually mean "moved", check with
  `scripts/check-spi-surface.sh`.

## Cluster

- `TimerProvider.scheduleTask` runs on every node; use
  `schedule(new ClusterAwareScheduledTaskRunner(...))` for mutual exclusion -
  which is still **not** once-per-interval (see the SPI catalog), and locks on
  the task's class simple name. Idempotent tasks only.
- Per-entity timers (one timer per client/session) don't survive restarts and
  need cluster messaging to cancel; prefer one periodic sweep over persisted
  state (expiry timestamps in attributes).
- Two nodes starting on an empty DB race on Liquibase; stagger them.

## Keys

- `getKeysStream(realm)` returns keys of **all** statuses; filter yourself.
- Signing with `signer()` (no arg) uses the realm's active OIDC key; for a
  key reserved to another purpose use `signer(KeyWrapper)` with the key picked
  by `kid`.
- A low priority does **not** keep an active key out of token signing:
  selection is per `(use, alg)`. Reserve keys with a DISABLED component (see
  the SPI catalog).

## Admin REST / JAX-RS

- `RealmResourceProvider` endpoints are public: authenticate/authorise
  yourself (`AppAuthManager`/bearer token, realm role checks), and enforce the
  realm's SSL requirement yourself.
- The request transaction commits after your method returns: a unique
  constraint violation surfaces as a 500 after you built a 201, unless you
  `flush()` first.
- JAX-RS filters/interceptors in providers are not officially supported.
  `@Provider @PreMatching` request filters do load with an empty
  `META-INF/beans.xml` in the JAR (Keycloak's own dist test relies on it), but
  keep them to what cannot be done in a resource (e.g. `Accept` rewriting) and
  re-test them on every Keycloak upgrade.

## When you patch Keycloak itself (fork, rebased PR)

These don't hit a plugin, but bite as soon as you touch Keycloak's tree:

- **spotless** formatting runs in the build: `mvn spotless:apply` in the
  touched modules.
- **Wildcard imports were removed** in 26.7: code from older branches fails
  on missing explicit imports.
- **db-compatibility-verifier** (26.7): every new Liquibase changeSet must be
  classified for rolling upgrades (e.g. listed in
  `rolling-upgrades-supported-changes.json`) and live in the changelog of the
  target version (`jpa-changelog-26.7.0.xml`), or the build fails.
- **ProtoStream type ids**: `@ProtoTypeId` values are global, unique and
  append-only (Keycloak's own are > 65535 and grow sequentially: max 65656 on
  26.7.4). A PR picking "the next free id" collides with the next upstream
  release; reserve a **distant, documented block** (e.g. 90000-90099) instead.
  A plugin that marshals its own types into Infinispan has the same problem.
