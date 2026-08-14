# Packaging a library with ng-packagr

Reference for the build side of library authoring. Behaviour described here was
verified against ng-packagr 20.3.x; the file/field names are stable across
Angular 16+, but re-check the schema (`node_modules/ng-packagr/ng-package.schema.json`)
if something doesn't match.

## Contents

- [Project shape](#project-shape)
- [ng-package.json options](#ng-packagejson-options)
- [How the published manifest is generated](#how-the-published-manifest-is-generated)
- [Dependency rules ng-packagr enforces](#dependency-rules-ng-packagr-enforces)
- [Secondary entry points](#secondary-entry-points)
- [Assets and styles](#assets-and-styles)
- [Publishing](#publishing)
- [Versioning and peer ranges](#versioning-and-peer-ranges)
- [Build errors and what they mean](#build-errors-and-what-they-mean)

## Project shape

A library project in an Angular workspace:

```
projects/<name>/
├── ng-package.json        # build config: where the output goes, what the entry is
├── package.json           # the manifest consumers install (name, version, peers)
├── README.md              # shipped with the package - the configuration docs live here
├── tsconfig.lib.json
├── tsconfig.lib.prod.json
└── src/
    ├── public-api.ts      # the public surface
    └── lib/               # implementation
```

Registered in `angular.json` with `"projectType": "library"` and the
`@angular/build:ng-packagr` builder (older workspaces:
`@angular-devkit/build-angular:ng-packagr`). The workspace `tsconfig.json`
usually maps the package name to the source so sibling projects and the demo app
resolve it without a build:

```json
{
  "compilerOptions": {
    "paths": {
      "@scope/name": ["./projects/<name>/src/public-api.ts"]
    }
  }
}
```

That path mapping is a development convenience and a source of false confidence:
it resolves the *source*, so an export missing from `public-api.ts` still works
in the workspace and fails only for real consumers. Verify against a built
tarball before releasing.

## ng-package.json options

Minimal and usually sufficient:

```json
{
  "$schema": "../../node_modules/ng-packagr/ng-package.schema.json",
  "dest": "../../dist/<name>",
  "lib": {
    "entryFile": "src/public-api.ts"
  }
}
```

Full option set:

| Option | Purpose |
|---|---|
| `dest` | Output folder (default `dist`). Publish from here. |
| `deleteDestPath` | Wipe the output folder before building. |
| `allowedNonPeerDependencies` | Regex list of package names permitted in `dependencies`. See below. |
| `assets` | Files copied verbatim into the package (globs or `{glob, input, output}`). |
| `inlineStyleLanguage` | `css` \| `less` \| `sass` \| `scss` for inline component styles. |
| `keepLifecycleScripts` | Keep `scripts` in the published manifest. Off by default as a security measure - leave it off. |
| `lib.entryFile` | Public API entry (default `src/public_api.ts`). |
| `lib.flatModuleFile` | Name of the generated flat module file; defaults to the package name. |
| `lib.cssUrl` | `none` \| `inline` - embed assets referenced from CSS as data URIs. |
| `lib.styleIncludePaths` | Extra resolution paths for style imports. |
| `lib.sass` | `fatalDeprecations` / `silenceDeprecations` / `futureDeprecations` passed to the Sass compiler. |

## How the published manifest is generated

The `package.json` inside the output folder is your library's manifest, modified:

**Added / overwritten**

- `name` - set from the entry point's module id
- `module` - path to the fesm2022 bundle
- `typings` - path to the bundled declarations
- `exports` - generated per Angular Package Format, merged with any `exports`
  you declared. Your manually declared conditions win and are placed first;
  declaring a condition that the generator also emits is an **error**, so add
  subpaths rather than redefining generated ones.
- `sideEffects` - your value if set, otherwise `false`

**Removed**

`devDependencies`, `scripts` (unless `keepLifecycleScripts`), `ngPackage`,
`stylelint`, `prettier`, `browserslist`, `jest`, `workspaces`, `husky`.

**Also written**

- `.npmignore` containing `**/package.json` - the nested manifests in secondary
  entry point folders exist for the dev-time resolver and aren't published.
- A `prepublishOnly` script that hard-fails, **if** the build ran in full rather
  than partial compilation mode. That guard exists because a fully compiled
  package is bound to one Angular version; if you hit it, fix the tsconfig
  (`"compilationMode": "partial"`) rather than deleting the script.

Everything else you put in the library's `package.json` survives untouched -
which is exactly why `publishConfig`, `license`, `repository`, `author`,
`keywords`, and `description` belong there and not at the workspace root.

## Dependency rules ng-packagr enforces

`dependencies` is checked entry by entry against `allowedNonPeerDependencies`
(regexes matched against package names). An entry that matches nothing **throws**:

```
Dependency <name> must be explicitly allowed using the "allowedNonPeerDependencies" option.
```

preceded by the advisory `Distributing npm packages with 'dependencies' is not
recommended. Please consider adding <name> to 'peerDependencies' or remove it
from 'dependencies'.`

Special handling for `tslib`:

- always allowed, no configuration needed
- if declared in `peerDependencies` it's **moved** to `dependencies` with a
  warning - the modern recommendation
- if absent entirely it's added automatically, using the version `@angular/compiler`
  depends on

The right response to the error is almost always to move the package to
`peerDependencies`. Reach for `allowedNonPeerDependencies` only for a small,
stateless, framework-unaware utility where a duplicated copy is genuinely
harmless.

## Secondary entry points

A secondary entry point is any subfolder of the library containing its own
`ng-package.json` (discovered by glob, excluding `node_modules`, `.git`, and the
destination folder). It becomes importable as `@scope/name/<relative-path>`:

```
projects/<name>/
├── ng-package.json                 # primary  -> @scope/name
└── testing/
    ├── ng-package.json             # secondary -> @scope/name/testing
    └── src/public-api.ts
```

The secondary's `ng-package.json` only needs its entry file:

```json
{ "lib": { "entryFile": "src/public-api.ts" } }
```

Each secondary gets a minimal `package.json` in the output (just `module`) and a
subpath entry in the primary's `exports` map.

Worth doing when a slice of the library is optional and would otherwise be dead
weight - test doubles, an adapter for one backend, a heavy optional feature -
because consumers only pull in what they import. Not worth doing to organise
code: folders already do that, and every entry point is a permanent piece of
public API.

## Assets and styles

Files that must ship as-is (SCSS partials for theming, icons, JSON schemas) go
through `assets`:

```json
{
  "assets": [
    "./styles/_theme.scss",
    { "glob": "**/*", "input": "./assets", "output": "./assets" }
  ]
}
```

Component styles are compiled and inlined into the bundles automatically -
`assets` is for files consumers reference themselves, e.g. `@use '@scope/name/styles/theme'`.

## Publishing

```bash
ng build <name>
cd dist/<name>
npm pack --dry-run     # inspect the exact file list and manifest
npm publish
```

Check in the dry run: `name`, `version`, `peerDependencies` ranges, the `exports`
map covers every entry point, `publishConfig.registry` is the intended one, and
no source or test files leaked in.

To validate before publishing, install the tarball into a scratch app:

```bash
npm pack                       # produces scope-name-<version>.tgz
cd /path/to/scratch-app
npm install /path/to/dist/<name>/scope-name-<version>.tgz
```

This catches missing exports, wrong peer ranges, and environment crashes that the
workspace `paths` mapping hides. `npm link` is quicker but resolves differently
from a real install, so prefer the tarball for a pre-release check.

## Versioning and peer ranges

- Semver applies to the *public API*, which includes types, token identities,
  DI scope, and observable behaviour - not just function signatures.
- Adding a required config field is breaking; adding an optional one with a
  default is not.
- Peer ranges should express tested compatibility. Widening the upper bound
  without building against it converts a support burden into a runtime failure.
- Prereleases (`1.2.0-rc.0`) are the cheap way to let a consumer validate a
  breaking change before it's permanent.

## Build errors and what they mean

| Message | Cause |
|---|---|
| `Dependency X must be explicitly allowed using the "allowedNonPeerDependencies" option` | X is in `dependencies`; move it to `peerDependencies`. |
| `Cannot read secondary entry point. It's already a primary entry point` | A nested `ng-package.json` sits at the primary's own path. |
| Duplicate/conflicting `exports` condition | You declared a condition in `exports` that the generator also emits; keep only added subpaths. |
| `prepublishOnly` refusing the publish | Built in full compilation mode; rebuild with partial. |
| Consumer sees `NullInjectorError` for a library service | The service isn't provided by `provideX()` and isn't `providedIn: 'root'`, or the consumer never called `provideX()`. |
| Consumer sees two instances of a service | A duplicated copy of the library (peer declared as a hard dependency), or `EnvironmentProviders` spread into a component's `providers`. |
