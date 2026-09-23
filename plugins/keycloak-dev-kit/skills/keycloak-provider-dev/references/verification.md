# Verification

A green `mvn package` proves only that the code compiles against the
`provided` API. A provider can compile and still not load (missing
`META-INF/services`, factory throwing in `init`, a class missing at runtime,
`isSupported` returning false). Verify in this order:

1. **Build and deploy**: `dev-env/scripts/build-plugin.sh` (restarts Keycloak).
2. **Server started cleanly**: `docker compose logs keycloak | grep -iE 'error|exception|warn.*provider'`;
   Keycloak logs `KC-SERVICES0047: <id> (<factory FQN>) is implementing the internal SPI <spi>. This SPI is internal and may change without notice`
   (`ServicesLogger` id 47) for private SPIs - expected, and a proof it was picked up.
3. **Provider LOADED**: `GET /admin/serverinfo` (admin token) →
   `providers.<spi-id>.providers` contains your id. `smoke-test.sh` does this.
4. **Real HTTP calls**, asserting status **and** `Content-Type`, both through
   the proxy and directly, with and without a strict `Accept` header.
5. **Negative cases**: feature disabled / realm not configured → the endpoint
   is absent (404), not a 500.
6. **Cluster** (only for cluster-aware code): with the cluster profile, the
   task never runs on two nodes at the same time (non-overlapping runs on
   several nodes in one interval are normal: `ClusterAwareScheduledTaskRunner`
   is mutual exclusion only), running it twice is harmless; stop one node, the
   other keeps running it; restart both, state survives.
7. **Unit tests** for pure logic (parsing, validation, policy); Keycloak's
   own testsuite/`keycloak-test-framework` is heavy - use it only when the
   Docker checks can't reach the behaviour.

`kcadm.sh get realms/<r> --fields attributes` returns `{}` on 26.7 even when
the realm has attributes (observed 2026-09-24): an "attribute not stored"
check based on it proves nothing. Read the full representation and filter it.

Fetch an admin token for scripts:

```sh
curl -s -d grant_type=password -d client_id=admin-cli -d username=admin -d password=admin \
  http://localhost:8081/realms/master/protocol/openid-connect/token | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
```

Decode a JWS payload returned by an endpoint, to check claims rather than
trusting a 200:

```sh
curl -s URL | python3 -c 'import sys,json,base64
h,p,_=sys.stdin.read().strip().split(".")
d=lambda s: json.loads(base64.urlsafe_b64decode(s+"="*(-len(s)%4)))
print(json.dumps({"header":d(h),"payload":d(p)},indent=2))'
```
