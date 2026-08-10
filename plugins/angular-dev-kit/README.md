# angular-dev-kit

Angular v20+ reference skills for Claude Code / Kilo Code. Two different
provenances live side by side here — kept explicit rather than blended,
so credit lands where it's due.

## Authored in this repo

- **[`angular-library`](skills/angular-library)** — authoring and packaging a
  publishable Angular library with ng-packagr: the `provideX()` /
  `makeEnvironmentProviders` configuration surface, `peerDependencies` vs
  `dependencies`, `public-api.ts` discipline, secondary entry points,
  environment-safe code, and the build-from-dist release loop.

## Vendored from analogjs/angular-skills

The other ten — `angular-component`, `angular-di`, `angular-directives`,
`angular-forms`, `angular-http`, `angular-routing`, `angular-signals`,
`angular-ssr`, `angular-testing`, `angular-tooling` — are copied unmodified
from [analogjs/angular-skills](https://github.com/analogjs/angular-skills)
by Brandon Roberts, MIT-licensed. Each keeps its own `LICENSE` file and
records its origin commit under `metadata.source` in its `SKILL.md`
frontmatter. They document application-side Angular (components, DI,
signals, HTTP, routing, testing, SSR, CLI) — `angular-library` is the one
piece written for this kit, covering the library-authoring side those ten
don't touch.

If you change one of the vendored ten, consider upstreaming the fix instead
of drifting from the source repo — that keeps re-syncing future updates
cheap.
