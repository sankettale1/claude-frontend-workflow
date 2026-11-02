# Build mode: Figma → code in the project's own structure

Same discipline as `/figma-to-sdc` (fetch, token map, spec, human gates, visual QA), and the **output follows the project's structure**: `newComponents: "sdc"` → an SDC folder + a thin adapter template (`stacks/drupal-sdc.md`); `"legacy"` → templates + Sass + JS + libraries.yml (`stacks/drupal-legacy.md`); other stacks → `stacks/detect.md`.

Read first (skip any that are missing):
- `.claude/docs/simplified-mcp-format.md`: how to read the Framelink MCP output
- `.claude/docs/figma-to-code.md`: layout, token, responsive and asset rules
- `.claude/docs/deviation-rules.md`: when you may auto-fix and when you must stop
- the stack reference chosen in SKILL.md Step 0.2

## 1. Fetch

- Parse the URL: `fileKey` from `/design/<key>/` or `/file/<key>/`, and `nodeId` from `node-id=12-345` → `12:345`.
- `mcp__framelink-figma-mcp__get_figma_data` (fileKey, nodeId). If the frame has mobile/tablet/desktop siblings, fetch them as well.
- `mcp__framelink-figma-mcp__download_figma_images` (PNG, scale 2) for each breakpoint frame into `<theme>/docs/components/screenshots/<name>/figma/`. Also export the real image and SVG assets the design needs (icons → SVG).
- If the MCP isn't connected, stop and tell the user to check `.mcp.json` / `/mcp`.

## 2. Analyse → intermediate representation

Write down, before any code:
- the element tree (semantic tag for each layer: section/h2/p/ul/button/a/figure)
- layout per breakpoint (flex/grid, gaps, columns) mapped to the theme grid (`breakpoints.sassGrid` in the profile; e.g. xs 0 / sm 576 / md 768 / lg 1180 / xl 1366)
- variants and states (hover, focus, active, disabled; colour variants → modifier classes)
- content that comes from Drupal fields vs. static text (static text → `|t`)
- interactions that need JS (carousel, accordion, tabs, video, parallax)

## 3. Token map

Match every colour, font, size, spacing, radius and shadow against the project's tokens: `theme-profile.json.tokens` if present, otherwise the Sass variables partial, `tailwind.config.*` / `@theme`, or CSS custom properties (`:root`, `globals.css`, design-token JSON):
`exact` → use it · `implicit` (a repeated literal) → propose a token · `near` (within the deviation-rules tolerance) → flag it, never apply silently · `missing` → a component-scoped custom property `--<block>-<purpose>` set from SCSS.

## 4. Find the Drupal target (Drupal stacks)

Using the profile (`contentModel`, `templates`, `preprocess`):
- Which entity renders this: paragraph type (+ view mode), block_content, node view mode, or view?
- Does a template already exist (update) or do we add a new suggestion (new)?
- Which fields exist and how they render (`content.field_x` vs. `paragraph.field_x.value`), and which preprocess variables are available (`is_rtl`, …)?
- Existing pieces to reuse: SDC components (`component_files.py <name>` or list `components/`), legacy partials (`_*.html.twig`), and JS behaviours that already target the same markup.
- **SDC**: design the component's **props** (strings, enums, booleans, URLs) and **slots** (rendered fields, images, nested components) from the Figma layers, and plan the adapter template that maps fields → props/slots.

**If the fields or paragraph type don't exist yet, don't create config.** List the needed fields in the spec as a backend dependency.

### Gate 1: plan (`AskUserQuestion`)
Show: the component name, Drupal target, new vs. update, reused partials, file list, and the token summary (exact/implicit/near/missing counts). Options: approve / change target / stop.

## 5. Spec

Write `<theme>/docs/components/<name>.md`:
1. Overview + Figma links + screenshots
2. Markup outline (BEM block `<name>`, elements, modifiers)
3. Field → Twig mapping table (legacy) **or** props/slots table + adapter mapping (SDC)
4. Token map table
5. Responsive behaviour per breakpoint
6. Accessibility notes (headings, names, keyboard, motion, contrast)
7. JS behaviour (if any): name, selectors, `once` id, events
8. Files to **create** and files to **change** (legacy: the exact library entries; SDC: the component.yml, and which adapter template changes)
9. Open questions / backend dependencies

### Gate 2: spec review (`AskUserQuestion`)
"Spec written to <path>. Review the token map and markup." Options: generate / I'll edit first (then STOP).

## 6. Generate

Create the new files exactly as the stack reference shows, copying the header, imports and conventions of a sibling (SDC: a sibling component folder, so the same group folder, name prefix, styling and JS source naming). For SDC, write `<name>.component.yml` first, then the Twig, styles and JS, then the adapter. Write accessible, performant code from the start (`references/checklists/*`).

### Gate 3: diffs to existing files (`AskUserQuestion`)
Before editing `<theme>.libraries.yml`, `<theme>.theme`, or any existing template, show a unified diff of each one. Apply only what's approved. Add entries; never delete or reorder existing ones.

## 7. Build and cache

### Gate 4 (`AskUserQuestion`)
"Run `cd <build.cwd> && PATH=<build.node>:$PATH <build.command>` and `<cacheClear>`?" Only run the build if `node_modules/` exists. Report the output and confirm that the compiled files exist (e.g. `.css`, plus `-rtl.css` with rtlcss, plus the SDC `<name>.css`/`<name>.js`). For SDC, the cache clear is required so Drupal discovers the new component.

## 8. Visual QA

Ask the user for a page URL that renders the component (or a node to add it to). Launch the `fe-visual-qa` subagent with the url, selector, Figma PNGs and out dir. Show the verdict per width. Fix major mismatches in the **source** (SCSS/Twig), rebuild, and re-run (max 2 rounds).

### Gate 5 (`AskUserQuestion`)
Accept / fix the remaining minor items / stop.

## 9. Review

Run **Mode: review** on all created and changed files (the 3 reviewer agents in parallel), fix critical/major findings, then give the final summary.
