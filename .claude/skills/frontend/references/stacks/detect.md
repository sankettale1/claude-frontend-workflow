# Stack detection and per-stack conventions

Run `python3 .claude/skills/frontend/scripts/detect_project.py` first: it detects all of this automatically (Drupal docroot, custom themes, SDC vs legacy, build tool, compiled pairs, RTL, DDEV URL). The table below is the logic it follows, for when you need to adjust the result by hand.

| Signal | Stack | Reference |
|---|---|---|
| `*.info.yml` theme with `components/**/*.component.yml` | `drupal-sdc` | `drupal-sdc.md` |
| `*.info.yml` theme, templates + `dev/scss` or `sass/` + gulp/webpack, no SDC | `drupal-legacy` | `drupal-legacy.md` |
| Both (a legacy theme that has started adding SDC) | the majority style; `newComponents` says which style new components use | both files, per component |
| `next.config.*` | `next` | below |
| `package.json` with `react` (Vite/CRA) | `react` | below |
| `nuxt.config.*` or `vue` dependency | `vue` | below |
| `astro.config.*`, `svelte.config.*` | `astro` / `svelte` | below |
| Only `.html` + `.css` + `.js` | `static` | below |

Also record: the styling approach (Sass, Tailwind (check v3 config vs. v4 `@theme`), CSS Modules, styled-components), the token source (Sass partial, `globals.css`, `tailwind.config`), breakpoints, the build command, lint configs (`.eslintrc*`, `.stylelintrc*`, `phpcs.xml*`), and RTL support.

## next / react
- Component = `components/<Name>/<Name>.tsx` (+ `.module.css` or Tailwind classes), co-located test/story if the project has them.
- Props typed; server components by default in the Next app router; `"use client"` only for interactivity.
- Images via `next/image` (with `sizes`, `priority` for LCP); fonts via `next/font`; links via `next/link`.
- State and effects: no data fetching in `useEffect` when a server fetch works; memoise only measured hot paths.

## vue / nuxt
SFC `<Name>.vue` with `<script setup lang="ts">`, scoped styles or Tailwind; `defineProps` typed; `NuxtImg` when available.

## static
Semantic HTML file + one CSS file per component (BEM) + one ES module per behaviour; `<script type="module" defer>`.

## Token sources by stack
Sass `$vars` (legacy) · CSS custom properties in `globals.css` / `:root` · Tailwind theme (`@theme` in v4, `theme.extend` in v3). Never introduce a second token system in an existing project.
