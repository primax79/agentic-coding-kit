#!/usr/bin/env bash
# Run kcadm.sh inside the dev Keycloak container, already logged in as admin.
# Example:
#   scripts/kcadm.sh update realms/test -s 'attributes."my.flag"=true'
#   scripts/kcadm.sh get realms/test --fields attributes
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
cd "$here"
docker compose exec -T keycloak /bin/bash -c '
  /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 \
    --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" \
    --config /tmp/kcadm.config >/dev/null &&
  /opt/keycloak/bin/kcadm.sh "$@" --config /tmp/kcadm.config' -- "$@"
