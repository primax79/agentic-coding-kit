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
| public realm REST resource | `org.keycloak.services.resource.RealmResourceProviderFactory` (server-spi-private) | `/realms/{realm}/{providerId}/...` | `getResource()` returns a JAX-RS object; do auth yourself |
| admin REST resource | `org.keycloak.services.resources.admin.ext.AdminRealmResourceProviderFactory` (services) | `/admin/realms/{realm}/{providerId}/...` | gets `AdminPermissionEvaluator`; internal API |
| admin console page | `org.keycloak.services.ui.extend.UiPageProvider(Factory)` (server-spi-private) | admin console | component-backed config UI without writing React |

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
  `ecdsa-generated`); keys used for another protocol than realm OIDC must not
  leak into the realm JWKS - select them by `kid` / component id, and verify
  what `getProviders(realm)` returns for disabled components on your tag
  before relying on a "disabled = private" trick.

## Scheduling

- `TimerProvider` (`session.getProvider(TimerProvider.class)`), obtained in
  `postInit` with a short-lived session.
- Once-per-cluster: `timer.schedule(new ClusterAwareScheduledTaskRunner(sessionFactory, task, intervalMillis), intervalMillis, taskName)`.
  `ClusterAwareScheduledTaskRunner` is in **`model/storage-private`**
  (artifact `keycloak-model-storage-private`), package
  `org.keycloak.services.scheduled`.
- `scheduleTask(ScheduledTask, ...)` wraps in a plain `ScheduledTaskRunner`
  (`services/.../timer/basic/BasicTimerProvider.java`): it runs on **every**
  node. Fine for node-local caches, wrong for DB sweeps.
- Scheduling the same `taskName` again cancels the previous task.

## Clients, registration, identity brokering

| Need | Where |
| --- | --- |
| hook into dynamic client registration | `ClientRegistrationPolicy(Factory)`; `ClientRegistrationPolicyManager.triggerBeforeRegister` runs in `ClientRegistrationAuth.requireCreate`, `triggerAfterRegister` in `AbstractClientRegistrationProvider.create` |
| a new registration endpoint type | `ClientRegistrationProviderFactory` → `/realms/{realm}/clients-registrations/{id}` |
| OIDC metadata → `ClientRepresentation` | `org.keycloak.services.clientregistration.oidc.DescriptionConverter.toInternal` (public static, internal) |
| virtual / external clients | `org.keycloak.storage.client.ClientStorageProviderFactory` (model/storage-private) |
| client_id as URL (CIMD) | `org.keycloak.protocol.oauth2.cimd.provider.ClientIdMetadataDocumentProviderSpi` (26.7) |
| extra checks at the authorization endpoint | `org.keycloak.protocol.oidc.endpoints.AuthorizationEndpointCheckSpi` (26.7) |
| upstream IdP (broker) | `IdentityProviderFactory` / `AbstractIdentityProviderFactory` |
| JWT authorization grant, token exchange v2 | features `JWT_AUTHORIZATION_GRANT`, `TOKEN_EXCHANGE_STANDARD_V2` (DEFAULT on 26.7), contract `JWTAuthorizationGrantProvider` |
| RFC 8414 AS metadata | `org.keycloak.protocol.oauth2.OAuth2WellKnownProviderFactory` (id `oauth-authorization-server`) |

## Storage

- Realm attributes (`realm.setAttribute`) - simplest per-realm config.
- Components (`ComponentModel`, `ConfiguredProvider`) - typed, admin-console
  editable, multiple instances per realm.
- `JpaEntityProviderFactory` (artifact `keycloak-model-jpa`) - own tables + Liquibase changelog; **documented
  as unsupported**, and couples you to the DB schema lifecycle. Last resort.

## Support status reminders

Documented as unsupported/internal (re-check for your version): JPA entity
providers, `AdminRealmResourceProvider`, JAX-RS filters/interceptors shipped
in providers, `TimerProvider` / `ClusterAwareScheduledTaskRunner`.
