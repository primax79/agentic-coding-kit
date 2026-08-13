# angular-dev-kit

Angular v20+ reference skills for Claude Code / Kilo Code. Two different
provenances live side by side here — kept explicit rather than blended,
so credit lands where it's due.

## Authored in this repo

- **[`angular-library`](skills/angular-library)** — authoring and packaging a
  publishable Angular library with ng-packagr: the `provideX()` /
  `makeEnvironmentProviders` configuration surface, `peerDependencies` vs
  `dependencies`, `public-api.ts` discipline, secondary entry points,
  environment-safe code, the build-from-dist release loop, and how an
  application develops against a local build (`npm link`, and why not
  `tsconfig` `paths`).
- **[`angular-icons-lucide`](skills/angular-icons-lucide)** — using Lucide in an
  Angular application or library: telling `@lucide/angular` from the older
  `lucide-angular`, the registry pattern versus the per-icon components a
  library should use, sizing icons against the surrounding text, the filled
  on/off state, names coming from configuration, and migrating off an icon font
  — where every failure mode is silent rather than a build error.

## Vendored from analogjs/angular-skills

The other ten — `angular-component`, `angular-di`, `angular-directives`,
`angular-forms`, `angular-http`, `angular-routing`, `angular-signals`,
`angular-ssr`, `angular-testing`, `angular-tooling` — are copied unmodified
from [analogjs/angular-skills](https://github.com/analogjs/angular-skills)
by Brandon Roberts, MIT-licensed. Each keeps its own `LICENSE` file and
records its origin commit under `metadata.source` in its `SKILL.md`
frontmatter. They document application-side Angular (components, DI,
signals, HTTP, routing, testing, SSR, CLI). The two written for this kit cover
what those ten don't touch: authoring a library, and icons.

If you change one of the vendored ten, consider upstreaming the fix instead
of drifting from the source repo — that keeps re-syncing future updates
cheap.
