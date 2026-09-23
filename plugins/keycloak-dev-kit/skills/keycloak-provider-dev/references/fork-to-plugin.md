# Fork (or upstream PR) → plugin

Use when a feature exists as a Keycloak fork or an unmerged PR and you need
to decide whether to ship it as a provider JAR instead.

## 1. Classify every change

Get the diff against its real fork point (`git merge-base`, or the parent of
the PR's first commit - not the date-based guess), then list each changed
file in one table:

| Change | Category | Plugin mapping |
| --- | --- | --- |
| new endpoint | SPI exists | `RealmResourceProviderFactory` / `WellKnownProviderFactory` / admin resource |
| new realm fields / columns | replace | realm attributes or a component; avoid `JpaEntityProvider` |
| new model interface methods | replace | adapter over attributes, no model change |
| hook in core flow (DCR, token, auth) | SPI exists? | policy/check SPI (`ClientRegistrationPolicy`, `AuthorizationEndpointCheckSpi`, authenticator) - grep the call site on the target tag |
| admin UI (React) | replace | `UiPageProvider` component page, or admin REST + external UI |
| cache / cluster events, ProtoStream types | redesign | persisted state + `ClusterAwareScheduledTaskRunner` sweep |
| core behaviour change with no hook | **gap** | upstream issue, proxy workaround, or keep a tiny patch |

A plugin is feasible when every row lands in the first three categories or
has an accepted workaround; list the gaps explicitly.

## 2. Price the fork: rebase onto the target tag

Do this even when the plugin route looks clear - it reveals what the fork
would cost to maintain and which APIs moved:

```sh
cd references
git clone --depth 1 --branch <tag> https://github.com/keycloak/keycloak.git keycloak
# PR commits + their fork point: depth = number of PR commits + 1
git -C keycloak fetch --depth=<n+1> origin pull/<N>/head:pr-<N>
git -C keycloak worktree add ../keycloak-pr<N> pr-<N>                          # the PR as-is
git -C keycloak worktree add -b pr-<N>-on-<tag> ../keycloak-pr<N>-on-<tag> pr-<N>
cd keycloak-pr<N>-on-<tag>
git rebase --onto <tag> <fork-point> pr-<N>-on-<tag>                            # resolve, --continue
# compile only the touched modules (and what they need), in a container
docker run --rm -v "$PWD":/src -v kc-src-m2:/root/.m2 -w /src maven:3.9-eclipse-temurin-21 \
  mvn -B -DskipTests -Dspotless.check.skip=true -Dspotless.apply.skip=true \
      -Dmaven.javadoc.skip=true -Denforcer.skip \
      -pl <core,server-spi,server-spi-private,services,...> -am install
```

The fork point is the **parent of the PR's first commit**. GitHub's
`base.sha` is the tip of the base branch at the last PR update, not the fork
point: rebasing from it replays unrelated upstream commits.

Keep the rebased branch in its own worktree, commit the conflict resolutions
and the compatibility fixes separately, and document: conflicts with their
resolution, auto-merged files, compile errors and fixes, what was not
compiled/tested. Typical 26.7 fixes are in [pitfalls.md](pitfalls.md) (last
section).

## 3. Reuse with care

- Reused code keeps its licence header and attribution (Keycloak: Apache-2.0).
- Re-derive protocol logic from the **final** spec, not from the PR, if the
  PR predates it; list the PR's known bugs and add tests that would catch them.
