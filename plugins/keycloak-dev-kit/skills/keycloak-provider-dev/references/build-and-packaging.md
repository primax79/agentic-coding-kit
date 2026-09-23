# Build and packaging

Template: [../templates/pom.xml](../templates/pom.xml). Verified on 26.7.4.

## Dependencies

All Keycloak artifacts `provided`, same `${keycloak.version}` as the server
you deploy to (a patch mismatch usually works, a minor mismatch is a gamble):

| Artifact | Module in the source tree | Holds |
| --- | --- | --- |
| `keycloak-core` | `core` | JOSE (`JWSBuilder`, JWK), representations |
| `keycloak-common` | `common` | `Profile` (features), utils (transitive) |
| `keycloak-server-spi` | `server-spi` | public SPIs, `KeycloakSession`, models |
| `keycloak-server-spi-private` | `server-spi-private` | private SPIs: `RealmResourceProviderFactory`, `TimerProvider`, `SignatureProvider`, `KeyProviderFactory`, IdP SPI |
| `keycloak-services` | `services` | `WellKnownProviderFactory`, `AdminRealmResourceProviderFactory`, DCR, `DefaultKeyManager` |
| `keycloak-model-storage-private` | `model/storage-private` | `ClusterAwareScheduledTaskRunner`, `ClientStorageProviderFactory` |

Add only what you import. `keycloak-services` pulls a large transitive tree,
all provided; don't let any of it reach the shaded JAR.

## Java level

`maven.compiler.release` = Keycloak's own (`pom.xml` of the tag: 17 on 26.7).
The `keycloak/keycloak:26.7` image runs JDK 21. Build with a JDK ≥ the
release (a `maven:3.9-eclipse-temurin-21` container avoids host JDK drift).

## Registration

One file per implemented factory interface:
`src/main/resources/META-INF/services/<factory interface FQN>`, one
implementation FQN per line. A missing or misspelled file fails **silently**:
the server starts and your provider simply isn't there - hence the
`serverinfo` check in [verification.md](verification.md).

## Third-party libraries

- Shade them into the JAR **and relocate** them under your own package
  (`<relocation><pattern>com.nimbusds</pattern><shadedPattern>your.pkg.shaded.nimbusds</shadedPattern></relocation>`).
  Keycloak on Quarkus puts all providers and its own libraries on one
  classpath; an unrelocated copy of a library Keycloak also ships (Nimbus,
  Jackson modules, BouncyCastle, Guava...) shadows or is shadowed by it.
- Exclude signature files from shaded JARs (`META-INF/*.SF`, `*.DSA`, `*.RSA`).
- Merge `META-INF/services` of shaded libraries with
  `ServicesResourceTransformer`, or their own SPIs vanish.
- Before adding a library, check whether Keycloak already provides the
  capability (JOSE, JSON, HTTP client: `session.getProvider(HttpClientProvider.class)`).

## Deploy

- Dev: copy the JAR into `providers/`; `start-dev` re-augments at every start,
  so a container **restart** picks it up.
- Production: `kc.sh build` after changing providers (or build a derived image
  with `RUN /opt/keycloak/bin/kc.sh build`), then `start --optimized`. A
  `start` without `--optimized` re-augments automatically (slower start).
- Build-time options (`--spi-<spi>--provider=...`, `--features`) need a
  rebuild; runtime `spi-<spi>--<provider>--<prop>` options don't.
