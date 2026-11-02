# Build mode: Figma → code in the project's own structure

Same discipline as `/figma-to-sdc` (fetch, token map, spec, human gates, visual QA), but the **output follows the stack reference**. For `drupal-legacy`, that means templates + SCSS + JS + libraries.yml, **not** SDC.

Read first (skip any that are missing):
- `.claude/docs/simplified-mcp-format.md`: how to read the Framelink MCP output
- `.claude/docs/figma-to-code.md`: layout, token, responsive and asset rules
- `.claude/docs/deviation-rules.md`: when you may auto-fix and when you must stop
- `references/stacks/<stack>.md`

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

Match every colour, font, size, spacing, radius and shadow against `theme-profile.json.tokens` (or `globals.css`/Tailwind config on other stacks):
`exact` → use it · `implicit` (a repeated literal) → propose a token · `near` (within the deviation-rules tolerance) → flag it, never apply silently · `missing` → a component-scoped custom property `--<block>-<purpose>` set from SCSS.

## 4. Find the Drupal target (Drupal stacks)

Using the profile (`contentModel`, `templates`, `preprocess`):
- Which entity renders this: paragraph type (+ view mode), block_content, node view mode, or view?
- Does a template already exist (update) or do we add a new suggestion (new)?
- Which fields exist and how they render (`content.field_x` vs. `paragraph.field_x.value`), and which preprocess variables are available (`is_rtl`, …)?
- Existing partials to reuse (`_play-pause-button.html.twig`, etc.) and existing JS behaviours that target the same markup.

**If the fields or paragraph type don't exist yet, don't create config.** List the needed fields in the spec as a backend dependency.

### Gate 1: plan (`AskUserQuestion`)
Show: the component name, Drupal target, new vs. update, reused partials, file list, and the token summary (exact/implicit/near/missing counts). Options: approve / change target / stop.

## 5. Spec

Write `<theme>/docs/components/<name>.md`:
1. Overview + Figma links + screenshots
2. Markup outline (BEM block `<name>`, elements, modifiers)
3. Field → Twig mapping table
4. Token map table
5. Responsive behaviour per breakpoint
6. Accessibility notes (headings, names, keyboard, motion, contrast)
7. JS behaviour (if any): name, selectors, `once` id, events
8. Files to **create** and files to **change** (with the exact library entries)
9. Open questions / backend dependencies

### Gate 2: spec review (`AskUserQuestion`)
"Spec written to <path>. Review the token map and markup." Options: generate / I'll edit first (then STOP).

## 6. Generate

Create the new files exactly as `references/stacks/<stack>.md` shows, copying the header and import block from a sibling file in the same folder. Write accessible, performant code from the start (`references/checklists/*`).

### Gate 3: diffs to existing files (`AskUserQuestion`)
Before editing `<theme>.libraries.yml`, `<theme>.theme`, or any existing template, show a unified diff of each one. Apply only what's approved. Add entries; never delete or reorder existing ones.

## 7. Build and cache

### Gate 4 (`AskUserQuestion`)
"Run `cd <build.cwd> && PATH=<build.node>:$PATH <build.command>` and `<cacheClear>`?" Only run the build if `node_modules/` exists. Report the output and confirm that the compiled `.css` and `-rtl.css` exist.

## 8. Visual QA

Ask the user for a page URL that renders the component (or a node to add it to). Launch the `fe-visual-qa` subagent with the url, selector, Figma PNGs and out dir. Show the verdict per width. Fix major mismatches in the **source** (SCSS/Twig), rebuild, and re-run (max 2 rounds).

### Gate 5 (`AskUserQuestion`)
Accept / fix the remaining minor items / stop.

## 9. Review

Run **Mode: review** on all created and changed files (the 3 reviewer agents in parallel), fix critical/major findings, then give the final summary.
