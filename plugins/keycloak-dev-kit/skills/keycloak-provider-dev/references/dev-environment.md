# Docker dev environment

Templates: [../templates/dev-env/](../templates/dev-env/). Copy the folder
into the project as `dev-env/`, set `COMPOSE_PROJECT_NAME`/`name:` and the
realm, done. Tested with Docker 29.7 (macOS arm64), `keycloak/keycloak:26.7`.

## Layout

```text
dev-env/
  docker-compose.yml       keycloak (start-dev) + nginx; profile "cluster": postgres, kc1, kc2, proxy-cluster
  nginx/default.conf       reverse proxy (X-Forwarded-*), per-location overrides go here
  nginx/cluster.conf       round-robin over kc1/kc2
  import/<realm>.json      realm imported at start (--import-realm)
  providers/               the plugin JAR (gitignored: *.jar)
  scripts/build-plugin.sh  Maven in Docker -> exactly one deployable JAR -> providers/ -> restart
  scripts/smoke-test.sh    readiness, issuer, provider LOADED in serverinfo, endpoint probes
  scripts/kcadm.sh         kcadm.sh in the container, already authenticated
```

## Design choices (and why)

- **Behind a reverse proxy from day one.** Production Keycloak always is;
  `KC_HOSTNAME=<proxy URL>` + `KC_PROXY_HEADERS=xforwarded` make every issuer
  and endpoint URL use the public address, even when calling Keycloak directly.
  Expose Keycloak directly too (e.g. 8081) to see its raw behaviour.
- **`start-dev` + H2 in the default profile**: throw-away state, realm
  re-imported at each start; reproducible tests.
- **Providers mounted read-only** from `providers/`; `build-plugin.sh` refuses
  to deploy unless exactly one JAR qualifies (skips `original-*`, sources,
  javadoc, tests), so stale JARs never pile up.
- **Maven runs in a container** (`maven:3.9-eclipse-temurin-21`, named
  volume for `~/.m2`) - no host JDK/Maven assumptions.
- **Management port 9000** (`KC_HEALTH_ENABLED=true`): `/health/ready` is the
  readiness signal. The image has **no curl**: container healthchecks use
  bash `/dev/tcp`.
- **JDWP on 8787** (`KC_DEBUG=true`, `KC_DEBUG_PORT=*:8787`);
  `KC_DEBUG_SUSPEND=y` to debug `init`/`postInit`.

## Cluster profile

Needed for anything cluster-aware (timers, caches, invalidation):

- PostgreSQL + `KC_CACHE=ispn`, `KC_CACHE_STACK=jdbc-ping` (discovery through
  the DB, no multicast).
- **Start kc2 only after kc1 is healthy** (`depends_on: condition:
  service_healthy`): two nodes initialising an empty DB at once race on the
  Liquibase `databasechangelog` table and one dies.
- Nodes run `start` (not `--optimized`), so the first start re-augments with
  the mounted providers (~1 min).
- Check membership: `docker compose --profile cluster logs kc1 | grep -i 'cluster view'`
  must show 2 members.

## Ports and parallel agents

Defaults: 8080 proxy, 8081 direct, 9000 management, 8787 debug, 8090 cluster
proxy. Two agents/worktrees testing at the same time **must** get distinct
ports and compose project names (`-p <name>`, env overrides) - worktree
isolation does not isolate Docker.
