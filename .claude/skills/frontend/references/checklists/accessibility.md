# Accessibility checklist (WCAG 2.2 AA), all stacks

| # | Check | WCAG | Severity if failed |
|---|---|---|---|
| 1 | Every `<img>` has alt; decorative images have `alt=""`; Drupal media alt comes from the field, not hard-coded | 1.1.1 | critical |
| 2 | Icon-only buttons/links have an accessible name (`aria-label` or `.visually-hidden` text, translated) | 4.1.2 | critical |
| 3 | Actions are `<button type="button">`, navigation is `<a href>`; no click handlers on div/span | 2.1.1 / 4.1.2 | critical |
| 4 | Everything works by keyboard; no positive tabindex; logical DOM order matches the visual order (also in RTL) | 2.1.1 / 2.4.3 | critical |
| 5 | A visible focus style (`:focus-visible`) with ≥3:1 contrast; never `outline: none` without a replacement | 2.4.7 / 2.4.11 | major |
| 6 | Text contrast ≥ 4.5:1 (≥ 3:1 for large text ≥ 24px or 18.66px bold); UI and icon contrast ≥ 3:1; text over images has an overlay that guarantees it | 1.4.3 / 1.4.11 | major |
| 7 | Headings are in order inside the component and don't skip levels; only one `h1` per page (the page title) | 1.3.1 / 2.4.6 | major |
| 8 | Lists are `<ul>/<ol>`; card grids are lists when they're a collection | 1.3.1 | minor |
| 9 | Toggles expose state: `aria-expanded` + `aria-controls`; tabs use the tablist/tab/tabpanel pattern with arrow keys; the current page uses `aria-current="page"` | 4.1.2 | major |
| 10 | Carousels/sliders: prev/next and pause buttons, slides labelled "n of m", no keyboard trap, autoplay stops on focus or hover | 2.2.2 | major |
| 11 | Video: autoplay only when muted, with a visible pause control, captions/transcript available; parallax and animation respect `prefers-reduced-motion` | 2.2.2 / 2.3.3 | major |
| 12 | Links that open a new tab say so (visually hidden "(opens in new tab)"); link text makes sense out of context (not "Read more" alone; add a visually hidden title) | 2.4.4 | minor |
| 13 | Form fields have a `<label>`, errors are linked with `aria-describedby`, correct `autocomplete` tokens | 1.3.1 / 3.3.1 / 1.3.5 | critical |
| 14 | Dynamic updates are announced (`aria-live` / `Drupal.announce`); focus moves into modals and returns on close; Esc closes | 4.1.3 / 2.4.3 | major |
| 15 | Content reflows at 320px with no horizontal scroll; text resizes to 200%; target size ≥ 24×24px | 1.4.10 / 1.4.4 / 2.5.8 | major |
| 16 | `lang`/`dir` are correct; RTL mirrors the layout; translatable strings go through `|t` / `Drupal.t()` | 3.1.1 / 1.3.2 | minor |
| 17 | `iframe` has a `title`; SVG icons are `aria-hidden="true" focusable="false"` when decorative, or have `role="img"` + `<title>` | 4.1.2 / 1.1.1 | major |

Drupal notes: `.visually-hidden` and `.visually-hidden.focusable` are core classes; `Drupal.announce(text)` needs `core/drupal.announce`; use `{{ 'text'|t }}`.
