# SPI catalog (verified on 26.7.4)

Paths are relative to the Keycloak source root. "Public" = module
`server-spi` (documented, relatively stable); "private" = `server-spi-private`,
`services`, `model/storage-private` (usable, but may change in any minor).

## Lifecycle and cross-cutting interfaces

| Type | Module | Use |
| --- | --- | --- |
| `org.keycloak.provider.ProviderFactory<T>` | server-spi | `create(session)`, `init(Config.Scope)`, `postInit(KeycloakSessionFactory)`, `close()`, `getId()`; defaults `order()`, `getConfigMetadata()`, `dependsOn()` |
| `org.keycloak.provider.EnvironmentDependentProviderFactory` | server-spi-private | `isSupported(Config.Scope)` - disable a factory by config/feature flag |
| `org.keycloak.provider.ServerInfoAwareProviderFactory` | server-spi-private | expose operational info in `/admin/serverinfo` |
| `org.keycloak.provider.ConfiguredProvider` | server-spi | config properties shown in the admin console (components) |
| `org.keycloak.provider.ProviderEvent` | server-spi | listen in `postInit` via `factory.register(event -> ...)` (e.g. realm removed) |

`init(Config.Scope)` receives the provider's `spi-<spi-id>--<provider-id>--<property>`
options (26.x syntax with double dashes; the single-dash form still works but
breaks re-augmentation detection - `docs/guides/server/configuration-provider.adoc`).

## HTTP surface

| Need | SPI (factory) | URL | Notes |
| --- | --- | --- | --- |
| realm `.well-known/<alias>` document | `org.keycloak.wellknown.WellKnownProviderFactory` (module **services**) | `/realms/{realm}/.well-known/{alias}` | `getAlias()` defaults to `getId()`; with several factories on one alias the one with the **lowest `getPriority()`** wins (default 1), so you can override `openid-configuration`. Served by `RealmsResource.getWellKnownResponse`: a `String` result is typed `application/jwt`, anything else JSON. See pitfalls for media types |
| public realm REST resource | `org.keycloak.services.resource.RealmResourceProviderFactory` (server-spi-private) | `/realms/{realm}/{providerId}/...` | `getResource()` returns a JAX-RS object. Keycloak only sets the realm in the context (`RealmsResource.java:277-285`): **no** SSL check (copy `RealmsResource.checkSsl`), no CORS, no client, no `EventBuilder` - do auth, SSL and events yourself. The request transaction commits after the method returns: `flush()` inside it if you must catch `ModelDuplicateException` |
| admin REST resource | `org.keycloak.services.resources.admin.ext.AdminRealmResourceProviderFactory` (services) | `/admin/realms/{realm}/{providerId}/...` | gets `AdminPermissionEvaluator`; internal API |
| admin console page | `org.keycloak.services.ui.extend.UiPageProvider(Factory)` (server-spi-private) | admin console | component-backed config UI without writing React |
| rewrite/inspect requests before matching | JAX-RS `@Provider @PreMatching ContainerRequestFilter` in the JAR, with an empty `META-INF/beans.xml` | any path | not officially supported, but Keycloak's own dist test does exactly this (`quarkus/tests/integration/.../jaxrs/filter/TestFilter.java`, `JaxRsDistTest`); the only way to change `Accept` handling or reroute a path to your own resource |

## Keys and signing

- `session.keys()` = `KeyManager` (`services/.../keys/DefaultKeyManager.java`):
  - `getActiveKey(realm, use, alg)` - filters `KeyStatus.isActive()`;
  - `getKey(realm, kid, use, alg)` and `getKeysStream(realm, use, alg)` -
    filter `isEnabled()`;
  - `getKeysStream(realm)` - **no status filter** (all keys of all providers);
  - the realm JWKS (`JWKSServerUtils`) and the OIDC token signer only see
    enabled/active keys.
- Signing with a key you chose, instead of the realm default:
  `session.getProvider(SignatureProvider.class, alg).signer(keyWrapper)` and
  `new JWSBuilder().type(...).jsonContent(...).sign(signer)`. The no-arg
  `signer()` uses the realm's active key for `alg`.
- Key providers are **components** (`KeyProviderFactory`, e.g. `rsa-generated`,
  `ecdsa-generated`). **Priority does not isolate a key**: `getActiveKey`
  takes the first ACTIVE key per `(use, alg)` across providers, so an active
  ES256 key you meant for something else signs tokens of any ES256 client,
  and ENABLED keys are published in `/certs`.
- **A key reserved to another protocol** (e.g. OpenID Federation Entity
  Keys): create its component with `enabled=false`, `active=false` (status
  DISABLED). It is then neither used, nor published, nor resolvable by
  `getKey(kid)`; find it with `getKeysStream(realm)` and sign with
  `signer(keyWrapper)` (`SignatureProvider.checkKeyForSignature` checks only
  type and alg). Name the component `...-DO-NOT-ENABLE` and refuse to use it
  if an admin enables it. No automatic key rotation exists on 26.7.4.

## Scheduling

- `TimerProvider` (`session.getProvider(TimerProvider.class)`), obtained in
  `postInit` with a short-lived session.
- Cluster-safe: `timer.schedule(new ClusterAwareScheduledTaskRunner(sessionFactory, task, intervalMillis), intervalMillis, taskName)`.
  `ClusterAwareScheduledTaskRunner` is in **`model/storage-private`**
  (artifact `keycloak-model-storage-private`), package
  `org.keycloak.services.scheduled`. It gives **mutual exclusion, not
  once-per-interval**: every node's timer fires, the lock is held only while
  the task runs, and the lock key is `task.getClass().getSimpleName()`
  (`ClusterAwareScheduledTaskRunner.java:49`), not `taskName`. So: make the
  task idempotent, and a **named top-level class with a unique simple name**
  (an anonymous class has simple name `""`).
- Schedule on `PostMigrationEvent` (register a listener in `postInit`; fires
  after DB migration and realm import) and declare
  `dependsOn(TimerProvider.class)`. Core precedent:
  `WorkflowsEventListenerFactory`. One daemon `Timer` thread serves all tasks:
  keep runs short.
- `scheduleTask(ScheduledTask, ...)` wraps in a plain `ScheduledTaskRunner`
  (`services/.../timer/basic/BasicTimerProvider.java`): it runs on **every**
  node. Fine for node-local caches, wrong for DB sweeps.
- Scheduling the same `taskName` again cancels the previous task.

## Clients, registration, identity brokering

| Need | Where |
| --- | --- |
| hook into dynamic client registration | `ClientRegistrationPolicy(Factory)`; `ClientRegistrationPolicyManager.triggerBeforeRegister` runs in `ClientRegistrationAuth.requireCreate`, `triggerAfterRegister` in `AbstractClientRegistrationProvider.create`. Default "Max Clients" / "Trusted Hosts" policies apply to the **anonymous** subtype only |
| create/update clients from your own endpoint with DCR parity | template: `AbstractPersistentClientIdMetadataDocumentProvider.java:138-253` (CIMD does it outside `ClientRegistrationAuth`): `DescriptionConverter.toInternal` → `DynamicClientRegisterContext` + `triggerBeforeRegister` → `ClientManager.createClient` → `DynamicClientRegisteredContext` + `triggerAfterRegister` → mappers → `ValidationUtil.validateClient` |
| client policies (executors/conditions) | SPIs `client-policy-executor` / `client-policy-condition`; events such as `PRE_AUTHORIZATION_REQUEST` (fires **before** client lookup at the authorization endpoint, `AuthorizationEndpoint.java:142`), `AUTHORIZATION_REQUEST`, `PUSHED_AUTHORIZATION_REQUEST`, `TOKEN_REQUEST`, `TOKEN_REFRESH`. They fire only if the realm has a matching profile + policy - your setup must install them |
| client keys for `private_key_jwt` | store as `use.jwks.string=true` + `jwks.string`; `jwks.url` makes Keycloak fetch it with its own client (SSRF surface). The key cache is invalidated cluster-wide only on `ClientUpdatedEvent` → call `client.updateClient()` after changing keys |
| strict client-assertion `aud` | `JWTClientValidator` accepts issuer, token, introspection and PAR URLs by default (`JWTClientValidator.java:34`) - add your own check if a spec requires one exact audience |
| request objects | parsed with `allowNone=true` (`AuthzEndpointRequestObjectParser.java:46`): set client attribute `request.object.signature.alg`; Keycloak does not check `aud`/`jti`/`sub` of request objects |
| replay protection | `session.singleUseObjects().putIfAbsent(key, lifespanSecs)` - immediate, cluster-wide, non-transactional; keys ending `.revoked` have special meaning |
| a new registration endpoint type | `ClientRegistrationProviderFactory` → `/realms/{realm}/clients-registrations/{id}` |
| OIDC metadata → `ClientRepresentation` | `org.keycloak.services.clientregistration.oidc.DescriptionConverter.toInternal` (public static, internal) |
| virtual / external clients | `org.keycloak.storage.client.ClientStorageProviderFactory` (model/storage-private) |
| client_id as URL (CIMD) | `org.keycloak.protocol.oauth2.cimd.provider.ClientIdMetadataDocumentProviderSpi` (26.7) |
| extra checks at the authorization endpoint | `org.keycloak.protocol.oidc.endpoints.AuthorizationEndpointCheckSpi` (26.7) |
| upstream IdP (broker) | `IdentityProviderFactory` / `AbstractIdentityProviderFactory`; to inject keys, override `OIDCIdentityProvider.verifySignature(JWSInput)` (protected) or store a JWKS JSON string in `publicKeySignatureVerifier` with `useJwksUrl=false` |
| JWT authorization grant, token exchange v2 | features `JWT_AUTHORIZATION_GRANT`, `TOKEN_EXCHANGE_STANDARD_V2` (DEFAULT on 26.7), contract `JWTAuthorizationGrantProvider` |
| RFC 8414 AS metadata | `org.keycloak.protocol.oauth2.OAuth2WellKnownProviderFactory` (id `oauth-authorization-server`) |

## Storage

- Realm attributes (`realm.setAttribute`) - simplest per-realm config.
  Values are NCLOB since 13.0 (realm), 20.0 (client), 23.0 (component config),
  so a JWKS fits. `CLIENT.CLIENT_ID` and `REDIRECT_URIS.VALUE` are still
  `VARCHAR(255)`: validate URL-shaped client IDs.
- Components (`ComponentModel`, `ConfiguredProvider`) - typed, admin-console
  editable, multiple instances per realm.
- `JpaEntityProviderFactory` (artifact `keycloak-model-jpa`) - own tables + Liquibase changelog; **documented
  as unsupported**, and couples you to the DB schema lifecycle. Last resort.

## Support status reminders

Documented as unsupported/internal (re-check for your version): JPA entity
providers, `AdminRealmResourceProvider`, JAX-RS filters/interceptors shipped
in providers (they do work, see above), `TimerProvider` /
`ClusterAwareScheduledTaskRunner`.

## Outbound HTTP

`session.getProvider(HttpClientProvider.class)` gives one shared
`CloseableHttpClient`: redirects disabled by default, 10 MB response cap,
socket timeout 5 s, **connect timeout -1 (none)** by default
(`DefaultHttpClientFactory.java:177`), and **no DNS hook**. For URLs derived
from untrusted input (SSRF), build your own Apache HttpClient (the classes ship
with Keycloak) with a filtering `DnsResolver`, manual redirects re-checked at
each hop, explicit timeouts and a size cap; reuse only Keycloak's truststore.
Behind `proxy-mappings`/an egress proxy, IP filtering must happen at the proxy.
