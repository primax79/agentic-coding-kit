# keycloak-dev-kit

Keycloak extension (provider JAR) development for Claude Code / Kilo Code.
**Project-scoped by design**: every Keycloak-specific claim is tied to the
version it was verified on (26.7.4, 2026-09-23) and must be re-checked for
the version a project targets.

## Skills

- **[`keycloak-provider-dev`](skills/keycloak-provider-dev)** - writing,
  building, testing and reviewing a Keycloak provider: rule zero (read the
  source of the exact target tag; `scripts/check-spi-surface.sh` locates each
  type and its module), SPI catalog (well-known, realm/admin REST, keys and
  signing, cluster-aware timers, client registration, brokering, storage),
  Maven packaging (provided deps, shading with relocation,
  `META-INF/services`), a Docker dev environment template (verified end to
  end), verification beyond "it compiles", pitfalls observed in practice, and
  how to decide whether a Keycloak fork/PR can become a plugin.

Origin: distilled from the `keycloak-openid-federation` plugin work for the
EOSC AAI WG OpenID Federation pilot. Protocol-specific knowledge
(OpenID Federation, the pilot) deliberately stays in that project.
