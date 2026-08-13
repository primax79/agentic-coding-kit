---
name: angular-icons-lucide
description: "Use Lucide icons in an Angular v20+ application or library: which of the two similarly named packages to install (@lucide/angular, not lucide-angular), the application pattern (provideLucideIcons plus <svg [lucideIcon]>) versus the library pattern (per-icon standalone components, never the app registry), sizing icons so they match the surrounding text, rendering a filled on/off state, and driving icon names from configuration. Also covers migrating away from an icon font (Bootstrap Icons, Font Awesome), where the failures are silent: a missing directive import renders an empty <svg> with no build error, conditional and interpolated class forms survive a naive grep, CSS written on the `i` selector goes orphaned, and filled/outline glyph pairs collapse onto one name. Triggers on lucide, @lucide/angular, lucide-angular, lucideIcon, provideLucideIcons, LucideDynamicIcon, `add an icon`, `the icons are too big/small`, `the icon does not show`, an empty or blank icon, or replacing bootstrap-icons / font-awesome / an icon font."
metadata:
  category: development
---

# Lucide icons in Angular

## First: there are two packages, and the wrong one is easy to install

| package | what it is | API |
| --- | --- | --- |
| `@lucide/angular` | the official scoped package, v1.x | `<svg lucideIcon="x">`, `provideLucideIcons()` |
| `lucide-angular` | the older community package | `<lucide-icon name="x">`, `LucideAngularModule`, `LUCIDE_ICONS` + `LucideIconProvider` |

They are not interchangeable, their names differ by one character, and an
application can end up shipping **both** — a library declaring the old one as a
peer dependency drags it in beside the new one. Check `package.json` before
writing any icon code, and check the peers of every `@`-scoped library that
renders icons.

Worth adding to a project's editor settings, because the auto-import lands on the
wrong one constantly:

```jsonc
"js/ts.preferences.autoImportFileExcludePatterns": [
  "lucide-angular", "lucide-react", "lucide-preact", "lucide-react-native", "@lucide/vue"
]
```

The rest of this skill is `@lucide/angular` v1.

## Applications: register, then render by name

```ts
// icons.ts — one place listing what the application uses
import { LucideStar, LucideChevronRight /* … */ } from '@lucide/angular';
export const appIcons = [LucideStar, LucideChevronRight /* … */];

// app.config.ts
providers: [provideLucideIcons(...appIcons)]
```

```html
<svg lucideIcon="star"></svg>
<svg [lucideIcon]="iconName"></svg>   <!-- name computed at runtime -->
```

The component that renders these is `LucideDynamicIcon`, selector
`svg[lucideIcon]`; it must be in the `imports` of every standalone component that
uses it. Its input accepts a registered **name**, an icon **component**, or raw
icon **data** (`{name, node}`).

`provideLucideIcons()` registers each icon under its canonical name *and* its
aliases, so deprecated names (`more-vertical` for `ellipsis-vertical`) keep
resolving.

## Libraries: never touch the application's registry

Every icon is also its own standalone component, with the selector
`svg[lucide<Name>]`:

```ts
import { LucideCopy, LucideX } from '@lucide/angular';

@Component({ imports: [LucideCopy, LucideX], /* … */ })
```
```html
<svg lucideX size="18"></svg>
```

This is the right shape for a library: self-contained, tree-shakeable, imposing
nothing on the consumer. `provideLucideIcons()` is the *application's* registry —
a library writing into it is a library deciding something that is not its call.
Use `[lucideIcon]` in a library only when the name is genuinely dynamic, and then
document that the consumer must register those icons.

## Sizing: match the text, not the default

A Lucide icon renders as an `<svg>` with hard-coded `width`/`height="24"`. It
does **not** follow `font-size`, so an icon font's sizing classes (`fs-4`,
`text-lg`, an inline `font-size`) become inert the moment the markup changes —
every icon renders at 24px regardless.

```css
svg.lucide {
  width: 1.2em;
  height: 1.2em;
  vertical-align: -0.225em;   /* keeps the box centred on the text baseline */
  flex-shrink: 0;
}
```

Why `1.2em` and not `1em`: a Lucide glyph is drawn inside **20 of its 24 viewBox
units**, while a font glyph fills its em square. `24/20 = 1.2` makes the visible
artwork match the icon it replaced at the same font size. Measure it rather than
trusting the ratio blindly — `getBBox().width / 24 * renderedWidth` gives the ink
actually painted.

Two consequences to know before choosing this:

- Targeting `.lucide` in CSS is an approach the library documents, but **CSS wins
  over the per-icon `size`/`color`/`strokeWidth` inputs**. Adopting it means
  giving those up application-wide. Check first that nothing binds `[size]`.
- The alternative, `provideLucideConfig({size, color, strokeWidth})`, keeps the
  inputs working but takes a fixed number — it cannot make icons scale with their
  surrounding text.

On a 1x display, a 2-unit stroke on a small icon lands under one physical pixel
and washes out. The `em` factor above lifts it back over 1px; on a dark
background, where strokes read thinner than they measure, a local
`stroke-width: 2.25` restores the weight.

## Filled state: a class, not a second icon

Icon fonts ship filled twins (`bi-star` / `bi-star-fill`). Lucide ships **one
outline glyph** and expects the filled state to come from `fill`:

```css
svg.lucide.icon-filled { fill: currentColor; }
```
```html
<svg lucideIcon="star" [class.icon-filled]="isStarred"></svg>
```

## Names from configuration

Names are plain kebab-case strings, so configuration can carry them — but nothing
type-checks them, and the package exposes no union of valid names. Two failure
modes follow: a name the registry never received renders an empty `<svg>`, and
config and registry drift apart with nothing to catch it.

- Generate the registry from the same configuration at build time, so the two
  cannot disagree, and fail the build on an unknown name.
- Registering the whole set is possible — `import { icons } from '@lucide/angular'`
  is a namespace of every icon component — but every icon is a full Angular
  component, so this pulls the entire package (~500 kB gzipped) into the bundle.
- Lucide's own guidance advises against the dynamic-import route for the general
  case: the icons are still bundled at build time, the bundler fragments them into
  many modules, and the icon flashes in after paint.
- If names must come from a server at runtime, consider sending the icon **data**
  (`{name, node}`) instead: `[lucideIcon]` accepts it directly and it costs the
  bundle nothing.

## Migrating from an icon font

The dangerous part is that **none of these fail the build**. Angular treats an
unknown attribute on an `<svg>` as an attribute; a missing import renders an empty
icon in silence. Verify in the running application, not in the compiler.

Work through the classes in this order:

1. **Every reference, not the obvious ones.** A search for `class="bi bi-x"`
   misses `[class.bi-star]="starred"`, `[ngClass]`, `class="bi {{ name }}"`, and
   `'bi-star'` string literals in TypeScript — decorator arguments, config maps,
   functions returning an icon name. Search for the prefix alone.
2. **Names in configuration and decorators**, together with the components that
   consume them. Converting one without the other yields blank icons wherever the
   value is dynamic.
3. **Filled/outline pairs collapse.** Both map to the same Lucide name, so a
   toggle becomes `cond ? 'star' : 'star'` — two identical branches, rendering
   identically in both states. Sweep for that pattern explicitly; it is the
   signature of a lost distinction. Replace with the `fill` class above.
4. **CSS written on the `i` selector.** Component stylesheets sizing or colouring
   icons through `i { }` stop applying the moment the element is an `<svg>`, and
   nothing reports it. Retarget them.
5. **A bare `svg { }` rule** in a component that also draws real SVG — a chart, a
   graph canvas — now hits every icon in that component too. Scope it to the
   element it was written for.
6. **Imperative DOM manipulation.** Code doing `element.querySelector('i')` and
   swapping `className` silently stops working: an icon is now a rendered
   component. Drive it from component state instead.
7. **Directive imports.** Every standalone component using `lucideIcon` needs
   `LucideDynamicIcon` (or the per-icon component) in its `imports`. This is the
   one that hides best — check every file that renders an icon.

Then verify in the browser, where the answers are unambiguous:

```js
// empty icons: registered nowhere, or directive not imported
document.querySelectorAll('svg.lucide').length
[...document.querySelectorAll('svg.lucide')].filter(s => !s.children.length).length
// leftovers from the old font
document.querySelectorAll('i[class*="bi-"]').length
```
