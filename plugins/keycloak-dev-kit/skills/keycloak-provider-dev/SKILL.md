---
name: keycloak-provider-dev
description: Use when writing, building, testing or reviewing a Keycloak (Quarkus distribution, 26.x) extension - a provider JAR implementing Keycloak SPIs (well-known endpoints, realm/admin REST resources, key providers, client registration policies, scheduled tasks, identity providers, authenticators) - or when deciding whether a Keycloak fork/PR can be turned into a plugin. Covers grounding claims in the Keycloak source of the exact target tag, the Maven packaging (provided deps, shading, META-INF/services), a Docker dev environment (start-dev, reverse proxy, two-node cluster), verification that the provider is really loaded, and known pitfalls. Not for configuring Keycloak as a user (realms, clients, themes only).
metadata:
  verified-on: "Keycloak 26.7.4 (tag commit aa9fe3fba0c6), 2026-09-23"
  origin: "Distilled from the keycloak-openid-federation plugin work (EOSC AAI WG OpenID Federation pilot)"
---

# Keycloak provider (extension) development

A Keycloak extension is a JAR dropped into `/opt/keycloak/providers`. It
implements one or more **SPIs**: a `ProviderFactory` (singleton per server,
lifecycle `init` → `postInit` → `create(session)` per request → `close`)
registered in `META-INF/services/<factory-interface-FQN>`, which creates a
`Provider` bound to one `KeycloakSession`. Nothing else is needed to plug in:
no fork, no patch.

Everything version-specific in this skill was verified on **26.7.4**. Keycloak
moves non-public classes between modules and changes signatures between minor
versions, so treat every class name, method and module below as a *pointer to
re-check*, not as a fact about the version you target.

## Rule zero: read the source of the exact tag you target

Before writing or asserting anything about a Keycloak API:

1. Have a shallow clone of the **exact target tag** next to the project:
   `git clone --depth 1 --branch <tag> https://github.com/keycloak/keycloak.git references/keycloak`
   (record the tag commit in the project's references doc).
2. Run [`scripts/check-spi-surface.sh`](scripts/check-spi-surface.sh)
   `<keycloak-src> [Class ...]` - it locates each interface/class this skill
   (or your code) relies on and prints its module, so a moved or removed type
   shows up before compile time.
3. Quote the real file and line in specs and reviews. Keycloak's own javadoc
   is thin; the behaviour lives in the callers (e.g. how `RealmsResource`
   serves a `WellKnownProvider`, not what `WellKnownProvider` says).

Never trust memory, blog posts or an LLM (yours included) for "Keycloak has /
doesn't have X": check `common/src/main/java/org/keycloak/common/Profile.java`
for features and grep the tag for the SPI.

## Workflow

1. **Map the requirement to SPIs** - [references/spi-catalog.md](references/spi-catalog.md).
   Prefer public SPIs (`server-spi`) over private ones (`server-spi-private`,
   `services`, `model/storage-private`); put every use of an internal class
   behind one adapter package so an upgrade is a local change.
2. **Scaffold the build** - [references/build-and-packaging.md](references/build-and-packaging.md)
   and [templates/pom.xml](templates/pom.xml).
3. **Stand up the dev environment** - [references/dev-environment.md](references/dev-environment.md)
   and [templates/dev-env/](templates/dev-env/): `keycloak/keycloak:<minor>`
   in `start-dev`, behind nginx, providers mounted read-only; optional
   two-node cluster on PostgreSQL.

   [`templates/`](templates/) is itself a complete, buildable project (pom,
   one example `WellKnownProviderFactory`, its `META-INF/services` file,
   `dev-env/`, `gitignore.template`): copy it, rename the coordinates and the
   package, then `dev-env/scripts/build-plugin.sh` and
   `EXPECT="well-known:example-provider" dev-env/scripts/smoke-test.sh`.
   Verified end to end on `keycloak/keycloak:26.7` (26.7.4) on 2026-09-23.
4. **Verify for real** - [references/verification.md](references/verification.md):
   the provider appears in `/admin/serverinfo`, the endpoint answers with the
   expected status *and media type*, cluster-aware code runs once per cluster.
5. **Check the pitfalls** - [references/pitfalls.md](references/pitfalls.md)
   before review.
6. **Fork or plugin?** When starting from an upstream PR or a fork,
   [references/fork-to-plugin.md](references/fork-to-plugin.md): classify
   each change, and rebase the PR onto the target tag to price the fork.

## Non-negotiables

- Keycloak artifacts are `provided`; third-party libraries are **shaded and
  relocated** into the JAR (Quarkus distribution = one flat classpath; a
  clash with a bundled version breaks `kc.sh build` or, worse, runtime).
- Compile with `maven.compiler.release` matching Keycloak's own (17 on 26.7),
  run on the image's JDK (21 on 26.7).
- A periodic job that must run once per cluster uses
  `TimerProvider.schedule(new ClusterAwareScheduledTaskRunner(...), ...)`,
  never `scheduleTask(...)` (which runs on every node).
- Don't add realm DB tables unless unavoidable (`JpaEntityProvider` is
  unsupported); store configuration in realm attributes or components.
- Never claim "done" from a compile: deploy into the container and check
  `serverinfo` plus a real HTTP call.
