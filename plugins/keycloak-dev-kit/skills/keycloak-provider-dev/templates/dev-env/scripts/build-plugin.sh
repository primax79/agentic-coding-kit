#!/usr/bin/env bash
# Build the provider in a Maven container (JDK 21), deploy exactly one JAR into
# dev-env/providers, then restart Keycloak so start-dev re-augments.
#
# Usage: scripts/build-plugin.sh [PLUGIN_DIR]
#   PLUGIN_DIR  provider Maven project (default: $PLUGIN_DIR or the parent of dev-env/)
# Env:
#   MAVEN_IMAGE   default maven:3.9-eclipse-temurin-21
#   M2_VOLUME     named volume for ~/.m2 (default kc-provider-m2)
#   NO_RESTART=1  skip the Keycloak restart
#   MVN_ARGS      extra Maven arguments, e.g. MVN_ARGS=-DskipTests
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
plugin_dir="$(cd "${1:-${PLUGIN_DIR:-$here/..}}" && pwd)"
maven_image="${MAVEN_IMAGE:-maven:3.9-eclipse-temurin-21}"

echo ">> building $plugin_dir with $maven_image"
docker run --rm \
  -v "$plugin_dir":/src \
  -v "${M2_VOLUME:-kc-provider-m2}":/root/.m2 \
  -w /src "$maven_image" \
  mvn -B -q ${MVN_ARGS:-} clean package

# Deploy the final JAR only (skip sources, javadoc, tests and shade's original-*).
shopt -s nullglob
jars=()
for j in "$plugin_dir"/target/*.jar; do
  case "$(basename "$j")" in
    original-*|*-sources.jar|*-javadoc.jar|*-tests.jar) ;;
    *) jars+=("$j") ;;
  esac
done
if [ "${#jars[@]}" -ne 1 ]; then
  echo "!! expected exactly one deployable JAR in $plugin_dir/target, found: ${jars[*]:-none}" >&2
  exit 1
fi

rm -f "$here"/providers/*.jar
cp "${jars[0]}" "$here/providers/"
echo ">> deployed $(basename "${jars[0]}") to dev-env/providers"

if [ "${NO_RESTART:-0}" != "1" ]; then
  # "docker compose restart" silently does nothing when the container is not running
  if [ -n "$(cd "$here" && docker compose ps -q --status running keycloak)" ]; then
    (cd "$here" && docker compose restart keycloak >/dev/null)
    echo ">> keycloak restarted; wait for readiness with scripts/smoke-test.sh"
  else
    echo ">> keycloak is not running; start it with: (cd dev-env && docker compose up -d)"
  fi
fi
