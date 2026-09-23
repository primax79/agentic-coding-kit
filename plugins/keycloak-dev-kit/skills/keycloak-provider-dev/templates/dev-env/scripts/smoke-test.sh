#!/usr/bin/env bash
# Smoke test of the dev environment (default profile):
#   - waits for Keycloak readiness
#   - prints the realm issuer through the proxy and directly
#   - checks that the expected providers are LOADED (GET /admin/serverinfo)
#   - probes endpoints: status + Content-Type, via proxy and direct
#
# Env:
#   REALM          default test
#   EXPECT         space-separated "<spi-id>:<provider-id>" pairs that must be loaded,
#                  e.g. EXPECT="well-known:my-document realm-restapi-extension:my-api"
#   PROBE_PATHS    space-separated paths to probe, e.g. "/realms/test/.well-known/my-document"
#   PROBE_ACCEPT   optional strict Accept header to probe with as well
#   PROXY_URL / DIRECT_URL / MGMT_URL, KC_ADMIN_USER / KC_ADMIN_PASSWORD
# Exit status: 1 if Keycloak is not ready or an EXPECTed provider is missing.
set -euo pipefail

proxy="${PROXY_URL:-http://localhost:8080}"
direct="${DIRECT_URL:-http://localhost:8081}"
mgmt="${MGMT_URL:-http://localhost:9000}"
realm="${REALM:-test}"
admin_user="${KC_ADMIN_USER:-admin}"
admin_pass="${KC_ADMIN_PASSWORD:-admin}"

echo ">> waiting for $mgmt/health/ready"
for _ in $(seq 1 90); do
  if curl -fsS "$mgmt/health/ready" >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS "$mgmt/health/ready" >/dev/null || { echo "!! Keycloak not ready"; exit 1; }
echo "   ready"

issuer() { curl -fsS "$1/realms/$realm/.well-known/openid-configuration" | python3 -c 'import sys,json;print(json.load(sys.stdin)["issuer"])'; }
echo ">> issuer via proxy : $(issuer "$proxy")"
echo ">> issuer direct    : $(issuer "$direct")"

token="$(curl -fsS -d grant_type=password -d client_id=admin-cli \
  -d username="$admin_user" -d password="$admin_pass" \
  "$direct/realms/master/protocol/openid-connect/token" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')"
serverinfo="$(curl -fsS -H "Authorization: Bearer $token" "$direct/admin/serverinfo")"

missing=0
for pair in ${EXPECT:-}; do
  spi="${pair%%:*}"; id="${pair#*:}"
  if printf '%s' "$serverinfo" | python3 -c 'import sys,json
spi,pid=sys.argv[1],sys.argv[2]
p=json.load(sys.stdin)["providers"].get(spi,{}).get("providers",{})
sys.exit(0 if pid in p else 1)' "$spi" "$id"; then
    echo ">> provider $spi/$id: LOADED"
  else
    echo "!! provider $spi/$id: NOT loaded"; missing=1
  fi
done

probe() {
  local label="$1" url="$2" accept="${3:-}"
  local args=(-s -o /dev/null -w '%{http_code} %{content_type}')
  [ -n "$accept" ] && args+=(-H "Accept: $accept")
  printf '   %-40s -> %s\n' "$label" "$(curl "${args[@]}" "$url")"
}
for path in ${PROBE_PATHS:-}; do
  echo ">> $path"
  probe "proxy"  "$proxy$path"
  probe "direct" "$direct$path"
  if [ -n "${PROBE_ACCEPT:-}" ]; then
    probe "proxy, Accept $PROBE_ACCEPT"  "$proxy$path"  "$PROBE_ACCEPT"
    probe "direct, Accept $PROBE_ACCEPT" "$direct$path" "$PROBE_ACCEPT"
  fi
done

exit "$missing"
