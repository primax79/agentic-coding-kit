#!/usr/bin/env bash
# Locate Keycloak types in a source checkout of the target tag, and print the
# module (Maven artifact) each one lives in. A type that moved or vanished
# shows up here before it breaks a compile.
#
# Usage: check-spi-surface.sh <keycloak-src> [SimpleName|FQN ...]
#   With no names, checks the default set used by the keycloak-provider-dev skill.
# Exit status: number of types not found (capped at 255).
set -euo pipefail

src="${1:?usage: $0 <keycloak-src> [type ...]}"
shift || true
[ -f "$src/pom.xml" ] || { echo "not a Keycloak source root: $src" >&2; exit 2; }

defaults=(
  org.keycloak.provider.ProviderFactory
  org.keycloak.provider.EnvironmentDependentProviderFactory
  org.keycloak.provider.ServerInfoAwareProviderFactory
  org.keycloak.wellknown.WellKnownProviderFactory
  org.keycloak.services.resource.RealmResourceProviderFactory
  org.keycloak.services.resources.admin.ext.AdminRealmResourceProviderFactory
  org.keycloak.services.ui.extend.UiPageProviderFactory
  org.keycloak.timer.TimerProvider
  org.keycloak.services.scheduled.ClusterAwareScheduledTaskRunner
  org.keycloak.keys.KeyProviderFactory
  org.keycloak.keys.DefaultKeyManager
  org.keycloak.crypto.SignatureProvider
  org.keycloak.jose.jws.JWSBuilder
  org.keycloak.services.clientregistration.policy.ClientRegistrationPolicyFactory
  org.keycloak.services.clientregistration.ClientRegistrationProviderFactory
  org.keycloak.services.clientregistration.oidc.DescriptionConverter
  org.keycloak.storage.client.ClientStorageProviderFactory
  org.keycloak.broker.provider.AbstractIdentityProviderFactory
  org.keycloak.connections.jpa.entityprovider.JpaEntityProviderFactory
)
names=("$@")
[ "${#names[@]}" -gt 0 ] || names=("${defaults[@]}")

echo "Keycloak source: $src ($(git -C "$src" describe --tags --always 2>/dev/null || echo 'no git'))"
missing=0
for n in "${names[@]}"; do
  simple="${n##*.}"
  if [[ "$n" == *.* ]]; then
    rel="$(echo "$n" | tr . /).java"
    hits=$(cd "$src" && find . -path "*/src/main/java/$rel" -not -path "*/test*" 2>/dev/null)
  else
    hits=$(cd "$src" && grep -rlE --include="$simple.java" "(interface|class|enum|record) $simple\b" . 2>/dev/null | grep '/src/main/java/' || true)
  fi
  if [ -z "$hits" ]; then
    printf '%-80s MISSING\n' "$n"; missing=$((missing + 1)); continue
  fi
  while IFS= read -r f; do
    mod="${f%%/src/main/java/*}"; mod="${mod#./}"
    art=$(sed -n '/<parent>/,/<\/parent>/d; s:.*<artifactId>\(.*\)</artifactId>.*:\1:p' "$src/$mod/pom.xml" 2>/dev/null | head -1)
    printf '%-80s %s (%s)\n' "$n" "${art:-?}" "$mod"
  done <<< "$hits"
done
exit $(( missing > 255 ? 255 : missing ))
