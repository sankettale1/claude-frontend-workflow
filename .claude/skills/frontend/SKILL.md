---
name: frontend
description: One entry point for all frontend work in this project. Covers building UI from a Figma node in the project's own structure (legacy Drupal theme, SDC, React/Next, Vue or plain HTML/CSS), reviewing changed code for accessibility, performance and coding standards with parallel reviewer subagents, auditing a live URL, and applying fixes. Use whenever the user asks to build/implement a design or Figma link, create or change a component, template, SCSS, JS or library, review or audit frontend code, check WCAG, Lighthouse or Core Web Vitals, or "check my FE changes".
argument-hint: "<component> [figma-url] [--url <page>] [--changed-only] | build <figma-url> | review [--changed | <paths>] | audit <url> | fix [report]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, mcp__framelink-figma-mcp__get_figma_data, mcp__framelink-figma-mcp__download_figma_images
---

# /frontend: Figma → code → review → fix

## Input

$ARGUMENTS

| Mode | Trigger | What happens |
|---|---|---|
| **`<component>`** (default) | any argument that isn't a mode keyword: a name like `strategic-cards`, `"Four cards"`, or a path | **One command for any component, new or existing.** Resolve its files → (Figma build or compare, only if a Figma URL is given) → a11y + perf + standards reviewers **in one parallel batch** → one report → offer fix |
| `build <figma-url>` | a Figma link, "build/implement this design" | Figma → spec → code in the project's **own** structure → visual QA → review |
| `review [--changed \| paths]` | "review", "check my changes" | Static scan + 3 reviewer subagents in parallel → merged report |
| `audit <url>` | a URL, "Lighthouse", "is this page accessible" | Runtime a11y + performance (+ static review of the templates behind it) |
| `fix [report]` | "fix the findings" | Apply safe fixes from the latest report, ask about the rest, re-scan |

Routing: if the first word is `build`, `review`, `audit` or `fix`, use that mode. Any other argument means **component** mode (a figma.com URL among the arguments is the component's design; `--url` is the page that renders it). No arguments: ask which component, or offer `review --changed`. Infer from natural language when it's clear ("check the hero banner" → component mode).

## Step 0: Context (every mode)

1. Read `.claude/frontend.config.json`. If it's missing, detect the stack with `references/stacks/detect.md`, show what you found, and offer to write the config.
2. Load the stack reference: `references/stacks/<stack>.md` (e.g. `drupal-legacy.md`). This is the source of truth for **where files go and how they're wired**.
3. For Drupal themes, read `theme.profile` (theme-profile.json) **sections as needed**: templates, tokens, breakpoints, libraries, JS. Don't re-scan facts it already records. If it's missing on a legacy theme, suggest `/legacy-theme-discovery` first, but don't block on it.
4. Hooks already protect core/contrib/compiled files and scan each edit. Don't fight them: if a guard denies an edit, follow its instruction.

## Mode: component (default; one command for any component)

`/frontend <component> [figma-url] [--url <page>] [--changed-only]`

The reviews (accessibility, performance, coding standards) **always** run for every component. Figma and visual QA run **only** when a Figma URL is given.

1. **Resolve the component**: `python3 .claude/skills/frontend/scripts/component_files.py "<component>" --json`. It returns templates (plus included partials and templates that attach its library), the SCSS/JS sources behind its library, the library entries and the preprocess functions. If the user named several things, run it for each and merge. If `tooBroad` is true, ask for a more specific name.
2. **Decide the path** (no question needed when it's obvious):

   | Found? | Figma URL? | Do this |
   |---|---|---|
   | yes | no | Review only (step 3) |
   | yes | yes | Fetch the Figma frames; if `--url` is given, run visual QA in the same batch as the reviews (step 3). Implementation changes come from the findings, through `fix`. |
   | no | yes | **New component**: run **Mode: build** (all of its gates), then continue at step 3 with the files it created. |
   | no | no | **New component, no design**: ask (`AskUserQuestion`) whether to scaffold it from a description (follow `references/stacks/<stack>.md`; show the file list first) or stop. After scaffolding, continue at step 3. |

3. **Review: one parallel batch.** Print the resolved file list (one line each), then in a **single message** launch all of these `Agent` calls together, never one after another:
   - `fe-a11y-reviewer`, `fe-perf-reviewer` and `fe-standards-reviewer`: always
   - `fe-visual-qa`: only if there's a Figma URL **and** a page URL (`--url`, or one the user gave earlier)

   Give every agent the same brief: stack, theme path, the component name, the exact `reviewFiles` list, the library names and preprocess functions with line numbers, the spec path (if `<theme>/docs/components/<name>.md` exists), the page URL if any (the perf and a11y agents then also run their runtime checks), and the instruction to return their JSON block. By default reviewers judge **whole files** (this is a component review); with `--changed-only` tell them to judge only lines changed on the branch (`fe_scan.py --base auto`).
4. **Merge and report** exactly as in Mode: review steps 4–6, with slug = the component name, `mode: "component"`, and `files` = the resolved list.
5. **Offer fix**: `AskUserQuestion`: "Fix the N auto-fixable findings now?" with the options Fix now / Show me first / Not now. On "Fix now", run **Mode: fix** with this report, then re-run only the scan (not the agents) to show before/after.

## Mode: build

Follow `references/figma-build.md` end to end. Summary of the gates (each one is an `AskUserQuestion`, never auto-approved):

1. **Plan**: Figma analysed, Drupal target chosen (paragraph type, view mode, block or view), new vs. update of an existing template, sub-parts reused.
2. **Spec**: `<theme>/docs/components/<name>.md` with the token map, markup, file list and diffs to existing files.
3. **Diffs to existing files**: `<theme>.libraries.yml`, `.theme` preprocess and existing templates, shown before writing.
4. **Build**: run the theme build and clear the cache (ask first).
5. **Visual QA**: `fe-visual-qa` subagent; the user accepts or asks for fixes.

Then run **Mode: review** on every file you created or changed.

> In a legacy theme, **never generate SDC** (`components/`, `*.component.yml`) unless the user explicitly asks for it. Use the theme's existing template + SCSS + JS + library pattern.

## Mode: review

1. **Collect files**: with `--changed` or no paths, run `bash .claude/skills/frontend/scripts/changed-files.sh`, which lists uncommitted and branch-changed frontend files, skipping compiled output. Otherwise use the given paths (expand directories with Glob). If there are none, say so and stop.
2. **Fast scan**: `python3 .claude/skills/frontend/scripts/fe_scan.py --base auto <files>`. This reports only lines changed on this branch; use `--all-lines` instead when the user asks for a full-file audit.
3. **Parallel reviewers**: in a **single message**, launch three `Agent` calls:
   - `fe-a11y-reviewer`, `fe-perf-reviewer` and `fe-standards-reviewer`
   - Give each one: the stack, theme path, exact file list, the spec path if this came from build mode, and the URL if one is known. Tell them to return their JSON block.
4. **Merge**: parse the three JSON blocks plus the scan. Dedupe findings with the same file, line and issue (keep the higher severity and note both sources). Sort by critical → major → minor. Drop low-confidence findings you can't confirm by reading the line yourself.
5. **Report (mandatory, two files)**: first write the merged findings to `<reportsDir>/<YYYY-MM-DD>-<slug>.json` in the shape documented at the top of `scripts/render_report.py` (every finding has severity, area, ref, file, line, issue, fix, autoFixable, sources). Then run `python3 .claude/skills/frontend/scripts/render_report.py <that.json>`, which writes the `.md` report next to it. Never hand-write the `.md`; `fix` mode reads the `.json`.
6. **Reply**: a short summary (counts per area, the top 5 issues with `file:line`), the report path, and an offer to run `/frontend fix`.

## Mode: audit <url>

1. Check the URL is reachable: `curl -sk -o /dev/null -w '%{http_code}' <url>`. Local DDEV must be running; if it isn't, tell the user `ddev start`.
2. In one message, launch `fe-a11y-reviewer` and `fe-perf-reviewer` with the `url`. If you can map the page to templates (via the theme profile, or the paragraph types the user mentions), also pass those files and launch `fe-standards-reviewer` on them.
3. Merge and report exactly as in review (same files and format, with the Lighthouse scores at the top).

## Mode: fix

1. Load the newest `<reportsDir>/*.json`, or the one named.
2. **Auto-apply** findings where `autoFixable` is true and the fix stays inside project source files (alt/aria/label attributes, `rel="noopener"`, `|t` on strings, `once()` migration, `defer` on library JS, scoping a selector, replacing a literal with an **existing** token).
3. **Ask** with `AskUserQuestion` (batch them, up to 4 per question) for anything that changes the design or content: colours that fail contrast, alt text wording, DOM order, new tokens, removing `!important` that may change rendering.
4. Edit **sources only**. Then ask whether to run the build + cache clear, re-run `fe_scan.py` on the touched files, and show a before/after count.

## Always (also when no mode is invoked but you write frontend code here)

- Put files where `references/stacks/<stack>.md` says; copy the header and pattern of a sibling file.
- Accessibility, performance and standards rules: `references/checklists/*.md`. Apply them while writing, not only in review.
- RTL: this site has RTL languages; rely on rtlcss and check that nothing breaks when the layout mirrors.
- Never install dependencies, never commit, never edit compiled assets.

## Final summary format

```
Mode: build | review | audit | fix
Files created: …   Files changed: …
Findings: a11y C/M/m · perf C/M/m · standards C/M/m (fixed N)
Build: run / pending (`cd <build.cwd> && <build.command>`)   Cache: cleared / pending
Report: <path>
Next: …
```
