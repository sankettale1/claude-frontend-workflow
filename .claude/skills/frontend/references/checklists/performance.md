# Performance checklist (Core Web Vitals), all stacks

Targets (mobile, p75): **LCP < 2.5s · CLS < 0.1 · INP < 200ms**. In the lab: TBT < 200ms.

## LCP
- The hero/LCP image is an `<img>` (not a CSS background) with `loading="eager"` and `fetchpriority="high"`, served through a responsive image style (Drupal) or `next/image priority`.
- Never lazy-load above-the-fold images. Lazy-load everything below the fold (`loading="lazy"`, the Drupal default).
- Hero video: a poster image, `preload="metadata"` or `none`, a separate small mobile source, and no autoplay on `prefers-reduced-motion` or Save-Data.
- Fonts: `font-display: swap`; preload only the 1–2 critical woff2 files.

## CLS
- Images, iframes, video and ads reserve space: width/height attributes or CSS `aspect-ratio`.
- JS-initialised widgets (sliders, tabs) have the same height before and after init; style the non-JS state.
- No banners or cookie bars injected above content after load, unless they overlay it.

## INP / JavaScript
- One behaviour per component, attached through its own library; `once()` so it doesn't run twice.
- Scroll and resize work: `IntersectionObserver`, `ResizeObserver`, `matchMedia` listeners, or `requestAnimationFrame` throttling. Never read layout (offsetHeight, getBoundingClientRect) and write styles in the same loop.
- Event delegation for long lists; passive listeners for scroll and touch.
- No new heavy dependency for a small job (e.g. jQuery for a toggle, moment.js for one date); check whether the project already ships one (swiper, video.js).
- `defer` on library JS (`{attributes: { defer: true }}`); no inline `<script src>` in templates.

## CSS
- A per-component CSS file attached only where the component renders; don't add to the global library.
- The component SCSS imports only functions/mixins/variables (no CSS output), so Bootstrap isn't duplicated: check the compiled size (`wc -c`). Warn above ~30KB per component.
- Avoid expensive properties on large areas (`filter: blur` and `backdrop-filter` on full-screen layers, box-shadow animations); animate `transform`/`opacity` only.

## Images and media
- Use Drupal image styles/responsive image styles with WebP/AVIF where configured; never the original upload.
- SVG icons inline or as a sprite; no icon fonts for new work when SVG exists.

## Drupal render caching
- Render `content.field_x` (bubbles cache tags). When reading `paragraph.field_x.value` or loading entities in preprocess, add cacheable metadata.
- Don't disable caching (`max-age: 0`) for presentational reasons.
