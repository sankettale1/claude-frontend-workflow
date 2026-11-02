# Standards and best-practice checklist

For Drupal-specific rules, the team skill `~/.claude/skills/drupal-coding-standards/data/*.md` is authoritative when present. This list covers what reviewers check most.

## General
- Follow the project's existing structure and naming (the stack reference), and match sibling files.
- No dead code, commented-out blocks, `console.log`, `debugger`, `dump()`/`kint()`.
- US English in comments and identifiers; every new file has a `@file` docblock (Twig/JS/PHP).
- Indentation: 2 spaces (Twig, SCSS, JS, YAML); files end with a newline.

## Twig
- Root element prints `{{ attributes.addClass(classes) }}`; keep `title_prefix`/`title_suffix` (contextual links).
- Logic stays light: compute in preprocess when it needs more than one `set`.
- Translatable text uses `|t` with placeholders (`{{ 'Showing @count'|t({'@count': n}) }}`), never string concatenation.
- No `|raw` on anything user-editable. Use `|clean_class` / `|clean_id` for class or id values from data.
- Whitespace control (`{%-`) only where it matters.

## SCSS / CSS
- BEM: `.block`, `.block__element`, `.block--modifier`; a max nesting depth of 3; no element selectors at root level.
- Tokens only (`$var`, `var(--x)`); new values become component-scoped custom properties.
- Mobile-first unless the component's siblings use `down()` consistently (many Bootstrap 4 themes use `media-breakpoint-down` throughout, so stay consistent within a file).
- Property order: positioning → box model → typography → visual → misc.
- No IDs, no `!important`, no vendor prefixes (autoprefixer adds them).

## JavaScript
- `Drupal.behaviors.<camelCase>` + core `once`; IIFE with `(Drupal, once)`; `'use strict'`.
- Respect the project's ESLint `ecmaVersion`. If it's **6 (ES2015)** and the build runs ESLint with `failAfterError` (no transpiling), `const`/`let`/arrow functions are fine, but newer syntax such as `async/await`, `?.`, `??` and object spread **breaks the build**.
- Strings: `Drupal.t()`; settings: `drupalSettings`; no globals; clean up in `detach` when listeners are added to `window`/`document`.
- No jQuery in new code unless the file or its library already depends on it.

## SDC components
- Folder `components/[<group>/]<name>/` with `<name>.component.yml` + `<name>.twig`; follow the siblings' group folders and name prefix.
- component.yml: `$schema`, `name`, `status`, `props: {type: object, properties: …}`; each prop has `type`, `title`, `examples`; variants are `enum`s; rendered markup is a **slot**, not a string prop.
- The component Twig uses only its props/slots + `attributes` (no `content.*`, entities, `attach_library` or preprocess variables); the root element prints `{{ attributes.addClass(classes) }}`.
- Dependencies go in `libraryOverrides.dependencies` (core/drupal, core/once).
- Adapter templates stay thin: `include`/`embed` with `with_context = false`/`only`, mapping fields → props/slots.
- Components referenced as `provider:name` must exist.

## libraries.yml
- Paths relative to the theme; an LTR + `-rtl` twin only when the theme uses rtlcss-generated `-rtl.css` files; `core/drupal` and `core/once` when there's JS; never `core/jquery.once`.
- Keep entries next to related ones; don't reorder or reformat existing entries.

## PHP (.theme preprocess)
- Drupal PHP standards: docblocks with `@param`/`@return`/hook references (`Implements hook_preprocess_HOOK().`), typed where the file already does, `\Drupal::` only in procedural code, and cacheable metadata when reading other entities or config.

## Git hygiene (when asked to prepare a commit)
- Commit the compiled CSS/JS together with the sources (this project commits build output).
- Message: `<TICKET>: <imperative summary>`.
