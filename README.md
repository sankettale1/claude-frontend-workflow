# Claude Frontend Workflow

One Claude Code command, **`/frontend`**, for all frontend work on a component, in **any Drupal 9/10/11 project**:

| Drupal setup | Supported |
|---|---|
| **SDC** themes (`components/<name>/<name>.component.yml`, PostCSS/Tailwind/Sass, webpack/vite) | ✅ |
| **Legacy** themes (templates + Sass + gulp + `libraries.yml`, optional rtlcss `-rtl.css` twins) | ✅ |
| **Mixed** (a legacy theme that has started adding SDC) | ✅ per component |
| Docroot at `./`, `web/`, `docroot/` or `html/`; several custom themes; components in custom modules | ✅ |
| Non-Drupal: Next/React, Vue/Nuxt, plain HTML | ✅ (basic) |

What it does:

- **Build** a component from a Figma design, in your project's own structure (an SDC folder + adapter template, or legacy template + Sass + JS + library)
- **Review** it for **accessibility**, **performance** and **coding standards** with three AI reviewers that run **in parallel**
- **Fix** what they find, safely

It combines the three Claude Code building blocks:

| Building block | What it does here |
|---|---|
| **Skill** (`/frontend`) | The playbook: finds the component's files, decides build vs. review, launches the reviewers, merges their results into one report, and applies fixes |
| **Sub-agents** (4) | Specialist reviewers that run side by side: accessibility, performance, coding standards and visual QA against Figma |
| **Hooks** (6) | Automatic guard-rails that run whatever Claude decides: block edits to core/contrib/compiled files, block dangerous commands, scan every edit, check quality before Claude finishes, and send desktop notifications |

```
/frontend strategic-cards [figma-url] [--url page]
        │
        ├─ 1. find all the component's files (templates, partials, SCSS, JS, library entries, preprocess)
        ├─ 2. Figma? build or compare (only when a Figma link is given)
        ├─ 3. ONE parallel batch:  fe-a11y-reviewer │ fe-perf-reviewer │ fe-standards-reviewer │ (fe-visual-qa)
        ├─ 4. merge → report (.md + .json) in docs/frontend-reviews/
        └─ 5. "Fix the N auto-fixable findings?" → /frontend fix

Hooks, always on:  SessionStart (project rules) · PreToolUse (guards) · PostToolUse (scan each edit)
                   Stop (quality gate) · Notification (desktop popup)
```

---

## Contents

1. [Requirements](#1-requirements)
2. [Install](#2-install)
3. [Configure for your project](#3-configure-for-your-project)
4. [Connect Figma (optional)](#4-connect-figma-optional)
5. [Check that it works](#5-check-that-it-works)
6. [Usage](#6-usage)
7. [What the hooks do](#7-what-the-hooks-do)
8. [The reviewers (sub-agents)](#8-the-reviewers-sub-agents)
9. [Reports and fixing](#9-reports-and-fixing)
10. [Customising](#10-customising)
11. [Troubleshooting](#11-troubleshooting)
12. [Uninstall](#12-uninstall)
13. [File reference](#13-file-reference)

---

## 1. Requirements

| Need | Why | Check |
|---|---|---|
| **Claude Code** (CLI, VS Code or JetBrains extension), a recent 2.x | Skills, sub-agents and hooks | `claude --version` |
| **Python 3.8+** | The hooks and scripts (standard library only, nothing to `pip install`) | `python3 --version` |
| **git** | Finding changed lines and files | `git --version` |
| A project that is a **git repository** | "Only new issues" scanning compares with git | `git status` |
| *Optional:* **Node 22+** and **Google Chrome** | Screenshots for visual QA against Figma | `node --version`, `google-chrome --version` |
| *Optional:* **Figma personal access token** | Building from or comparing with Figma | see [step 4](#4-connect-figma-optional) |
| *Optional:* **DDEV** (or any local URL) | Visual QA and Lighthouse on a running page | `ddev describe` |
| *Optional:* `notify-send` (Linux) | Desktop notifications | `which notify-send` |

---

## 2. Install

**Step 2.1: clone this repo** (anywhere, e.g. your home folder):

```bash
git clone https://github.com/sankettale1/claude-frontend-workflow.git
cd claude-frontend-workflow
```

**Step 2.2: install it into your project:**

```bash
./install.sh /path/to/your/project
```

This copies the files into `your-project/.claude/`:

```
.claude/
├── skills/frontend/          the /frontend skill (+ scripts and checklists)
├── agents/fe-*.md            the 4 reviewer sub-agents
├── hooks/*.py                the 6 hooks
├── settings.json             registers the hooks (merged if you already have one)
├── frontend.config.json      YOUR project settings, AUTO-DETECTED, which you check in step 3
└── state/                    runtime data (git-ignored)
```

- The installer **auto-detects your project**: the docroot, custom themes, SDC vs legacy, the build command, which files are compiled from which sources, RTL and the DDEV URL. It writes `.claude/frontend.config.json` and prints a summary:
  ```
    detected       .claude/frontend.config.json
                   stack: drupal-sdc   new components: sdc   docroot: docroot
                   theme: mytheme (docroot/themes/custom/mytheme)
                   build: npm run build (in docroot/themes/custom/mytheme)   compiled pairs: 2   url: https://myproject.ddev.site
  ```
- Existing files are **never overwritten**. Use `./install.sh /path --force` to update to a newer version (your `frontend.config.json` is still kept).
- If `.claude/settings.json` already exists, the hooks are **merged** into it, and a backup is saved as `settings.json.bak`.

**Manual install (instead of the script):** copy the `.claude/` folder of this repo into your project, then run `python3 .claude/skills/frontend/scripts/detect_project.py --write` from the project root (or copy `frontend.config.example.json` to `frontend.config.json` and edit it). If you already have a `.claude/settings.json`, copy the `"hooks"` block into it by hand.

---

## 3. Configure for your project

The installer already filled in **`your-project/.claude/frontend.config.json`**. Open it and **check** the values, especially `theme` (the theme you build in) and `newComponents`. To re-detect at any time:

```bash
python3 .claude/skills/frontend/scripts/detect_project.py            # print only (review it)
python3 .claude/skills/frontend/scripts/detect_project.py --write --force   # overwrite the config
```

Every field:

| Field | Meaning | Example |
|---|---|---|
| `stack` | The theme's main style: `drupal-sdc` (components/), `drupal-legacy` (templates + Sass + libraries), or `next`, `react`, `vue`, `static` | `"drupal-sdc"` |
| `newComponents` | Structure for **new** components: `sdc` or `legacy`. Existing components always keep their own structure, so mixed themes work | `"sdc"` |
| `docroot` | Drupal docroot (`.`, `web`, `docroot`, `html`) | `"web"` |
| `theme.name` | Theme machine name (the name of `<name>.info.yml`) | `"mytheme"` |
| `theme.path` | Theme folder, relative to the project root | `"web/themes/custom/mytheme"` |
| `otherThemes` | Other custom themes (searched for components too) | `["web/themes/custom/admin_x"]` |
| `rtl` | The theme builds RTL CSS (rtlcss/postcss-rtlcss) | `true` |
| `theme.profile` | *Optional* theme-profile JSON (from a theme discovery skill). If it exists, Claude reads facts from it instead of re-scanning the theme. | `".claude/theme-discovery/theme-profile.json"` |
| `localUrl` | Your local site | `"https://myproject.ddev.site"` |
| `build.command` / `build.cwd` | How to compile SCSS/JS, and from which folder | `"npm run build"`, `"themes/custom/mytheme"` |
| `build.node` | Node `bin` folder for the build (the old gulp setup often needs Node 16) | `"~/.nvm/versions/node/v16.18.1/bin"` |
| `screenshotNode` | Node 22+ binary used for screenshots (visual QA) | `"~/.nvm/versions/node/v22.9.0/bin/node"` |
| `cacheClear` | Cache-clear command | `"ddev drush cr"` |
| `protectedPaths` | Folders Claude may **never edit** | `core/`, `vendor/`, `modules/contrib/` … |
| `askPaths` | Files Claude must **ask before editing** | `settings.php`, `package.json` … |
| `compiled` | Source → compiled-output pairs. Editing a compiled file is blocked when its source exists, and the stop gate flags out-of-date output. Works for separate folders (legacy `dev/scss/` → `css/`) and side-by-side SDC files (`card.pcss` → `card.css`, `card.behavior.js` → `card.js`). `rtlSuffix` covers rtlcss twins like `x-rtl.css`. | see below |
| `reviewRoots` | Folders that count as "your frontend code" for `review --changed` | `["themes/custom/mytheme/", "modules/custom/"]` |
| `reviewGate` | `"block"`: Claude must fix new errors before finishing (once per problem set). `"warn"`: only show a summary. | `"block"` |
| `reportsDir` | Where review reports are written | `"themes/custom/mytheme/docs/frontend-reviews"` |

Examples of `compiled`:

```jsonc
// Legacy theme: separate source and output folders
{ "source": "themes/custom/mytheme/dev/scss/", "sourceExt": ".scss", "output": "themes/custom/mytheme/css/", "outputExt": ".css", "rtlSuffix": "-rtl" }
// SDC theme: compiled file next to its source inside components/
{ "source": "web/themes/custom/mytheme/components/", "sourceExt": ".pcss", "output": "web/themes/custom/mytheme/components/", "outputExt": ".css" }
{ "source": "web/themes/custom/mytheme/components/", "sourceExt": ".behavior.js", "output": "web/themes/custom/mytheme/components/", "outputExt": ".js" }
```

> Using a **non-Drupal** project? Set `stack` (e.g. `"next"`), point `theme.path` at your source folder (e.g. `"src"`), leave `compiled` empty (`[]`) unless you commit build output, and adjust `protectedPaths`.

---

## 4. Connect Figma (optional)

Only needed for `build` and for visual comparison. This uses the [Framelink Figma MCP](https://github.com/GLips/Figma-Context-MCP) server.

**Step 4.1:** create a Figma personal access token: Figma → *Settings* → *Security* → *Personal access tokens* (read access to file content is enough).

**Step 4.2:** put the token in an **environment variable**, not in a file. Add it to `~/.bashrc` or `~/.zshrc`:

```bash
export FIGMA_API_KEY="figd_xxxxxxxxxxxxxxxx"
```

**Step 4.3:** create `your-project/.mcp.json`:

```json
{
  "mcpServers": {
    "framelink-figma-mcp": {
      "command": "npx",
      "args": ["-y", "figma-developer-mcp", "--stdio"],
      "env": { "FIGMA_API_KEY": "${FIGMA_API_KEY}" }
    }
  }
}
```

> ⚠️ **Never commit a real token.** Keep `.mcp.json` in `.gitignore` if anyone ever pastes a key into it directly.

**Step 4.4:** restart Claude Code, run `/mcp`, and check that `framelink-figma-mcp` is **connected**.

---

## 5. Check that it works

Open Claude Code **in your project folder** (hooks use the project's `.claude/settings.json`), then:

| Check | How | Expected |
|---|---|---|
| Hooks loaded | type `/hooks` | SessionStart, PreToolUse (2), PostToolUse, Stop and Notification entries pointing at `.claude/hooks/*.py` |
| Agents loaded | type `/agents` | `fe-a11y-reviewer`, `fe-perf-reviewer`, `fe-standards-reviewer`, `fe-visual-qa` |
| Skill loaded | type `/frontend` (press Tab) | the skill is suggested |
| Guard works | ask: *"add a comment to `<theme>/css/<some compiled file>.css`"* | Blocked: *"is compiled output. Edit … .scss instead"* |
| Scan works | ask: *"create a test twig with `<img src="x.png">`"* | Claude is told about the missing `alt` and fixes it (delete the test file afterwards) |

Test the scripts directly, without Claude:

```bash
python3 .claude/skills/frontend/scripts/component_files.py "my component"   # which files belong to it
python3 .claude/skills/frontend/scripts/fe_scan.py --all-lines path/to/file.html.twig
python3 .claude/skills/frontend/scripts/changed_files.py                   # frontend files changed on your branch
```

---

## 6. Usage

### The one command: `/frontend <component>`

Works for **any** component, existing or new, SDC or legacy. The name can be written any way you like: `pricing-card`, `PricingCard`, `"Pricing card"`, `pricing_card`, an SDC ID (`mytheme:pricing-card`), or a path. It searches **all custom themes and modules** and finds:

- **SDC**: the component folder (`.component.yml`, `.twig`, style/JS **sources**, stories, README) and the Drupal templates that `include`/`embed` it
- **Legacy**: the templates and partials, the Sass/JS sources behind its library, the `libraries.yml` entries, the templates that attach it, and preprocess functions

If a name matches several components (e.g. "card"), it asks which one.

| You type | What happens |
|---|---|
| `/frontend strategic-cards` | **Existing component, review only.** Finds all its files and runs the 3 reviewers in parallel, giving one report. |
| `/frontend mytheme:pricing-card` | Same, for an SDC component by its ID. |
| `/frontend pricing-table https://www.figma.com/design/KEY/File?node-id=12-345` | **New component with a design.** Builds it from Figma in your structure (with approval steps), then reviews it. |
| `/frontend pricing-table` *(doesn't exist, no Figma)* | Asks whether to scaffold it from your description, then reviews it. |
| `/frontend hero-banner <figma-url> --url https://myproject.ddev.site/node/12` | Review **plus** visual QA against Figma **plus** runtime checks (Lighthouse/a11y) on that page, all in the same parallel batch. |
| `/frontend strategic-cards --changed-only` | Judges only the lines changed on your branch (fast PR check). |

The accessibility, performance and standards reviews **always run**. Figma steps run **only** when you give a Figma link.

### Other modes

| Command | Use it for |
|---|---|
| `/frontend review --changed` | Review **every** frontend file changed on your branch (before a PR) |
| `/frontend review path/to/folder` | Review specific files or folders |
| `/frontend audit https://myproject.ddev.site/page` | Runtime audit of a page: Lighthouse + accessibility, plus static review of its templates |
| `/frontend build <figma-url>` | Figma → code only (then it reviews automatically) |
| `/frontend fix` | Apply the fixes from the latest report (see [section 9](#9-reports-and-fixing)) |

Natural language works too: *"check the hero banner component"* or *"build this design: <link>"*.

### Build from Figma: step by step

Claude stops for your approval at every **⏸** step:

1. **Fetch:** reads the Figma node and downloads the frame images (all breakpoints).
2. **Analyse:** element tree, layout per breakpoint, variants and states, what's static text and what's a Drupal field.
3. **Token map:** each Figma colour, font and spacing is matched to your existing tokens: *exact*, *implicit* (a repeated literal), *near* (flagged) or *missing* (becomes a component-scoped CSS variable).
4. **Drupal target:** which paragraph type, view mode, block or view renders it; new template or update; partials to reuse. (It never creates fields or config; missing fields are listed as backend dependencies.)
5. ⏸ **Plan approval**
6. **Spec:** written to `<theme>/docs/components/<name>.md`. ⏸ **Spec approval** (you can edit the file first).
7. **Generate** in your structure (from `newComponents`):
   - **SDC:** `components/<group>/<name>/` with `<name>.component.yml` (props + slots), `<name>.twig`, styles and JS (sources if the theme compiles them), then a thin **adapter** template (`paragraph--<bundle>.html.twig` → `{% embed 'mytheme:<name>' … %}`)
   - **Legacy:** template in `templates/…/<Pascal>/`, Sass in the theme's Sass folder, JS in its JS source folder, and a `libraries.yml` entry (+ `-rtl` twin with rtlcss)
8. ⏸ **Diffs to existing files:** adapter templates, `libraries.yml` entries, preprocess and existing templates are shown as diffs before writing.
9. ⏸ **Build + cache clear:** runs your build command and `drush cr`.
10. **Visual QA:** screenshots at 375/768/1366 compared with the Figma frames, with up to 2 fix rounds. ⏸ **Accept**
11. **Review:** the 3 reviewers in parallel, with critical and major issues fixed.

---

## 7. What the hooks do

Hooks run **automatically**: you don't call them, and Claude can't skip them.

| Hook (event) | File | Behaviour |
|---|---|---|
| **SessionStart** | `session_start.py` | Gives Claude your project's rules at the start of every session: theme path, where files go, the build command, the branch, and the number of uncommitted theme files |
| **PreToolUse**: Edit/Write | `guard_paths.py` | **Denies** edits in `protectedPaths` (core, contrib, vendor …). **Denies** edits to compiled CSS/JS and source maps when the source exists ("edit the .scss instead"). **Asks you** before editing `askPaths` (settings.php, package.json …) |
| **PreToolUse**: Bash | `guard_bash.py` | **Denies** `drush sql-drop` / `site:install`, `git reset --hard`, `git clean -f`, `git push --force`, and `rm -rf` on root folders. **Asks you** before `npm/yarn install`, `composer require/update`, `drush cim/updb/en/pmu`, `git push` |
| **PostToolUse**: Edit/Write | `post_edit_scan.py` | Scans **only the lines Claude just changed** (`fe_scan.py`). Errors (e.g. `<img>` without alt, `jQuery.once`, `attach_library` to a library that doesn't exist) are sent back so Claude fixes them immediately; warnings are added as context |
| **Stop** | `stop_gate.py` | When Claude is about to finish: re-scans the files edited this turn and checks whether compiled CSS/JS is older than its source. With `reviewGate: "block"`, Claude must resolve it first (once per problem set, so it can't loop). Then it shows a summary and sends a desktop notification |
| **Notification** | `notify.py` | Desktop popup when Claude is waiting for your permission or input |

In practice the hooks back each other up: if Claude ignores the post-edit warning, the stop gate catches the same issue before it finishes.

**Scan rules** (`fe_scan.py`) by category:

- **a11y:** img-alt, iframe-title, positive-tabindex, click handler on div/span, `href="#"`, zoom lock, `outline: none`, autoplay without muted
- **perf:** img without width/height, render-blocking `<script src>`, remote `@import`, `document.write`
- **standards / security / Drupal:** `console.log`, `debugger`, jQuery.once, `dump()`/`kint()`/`dpm()`, `|raw`, `target="_blank"` without rel, `!important`, ID selectors, hard-coded colours, `attach_library` with an undefined library, a missing asset file in `libraries.yml`
- **SDC:** `include`/`embed` of a `provider:name` component that doesn't exist, a component template without its `.component.yml`, `props` without `type: object`, `content.*`/entity access or `attach_library` inside a component

---

## 8. The reviewers (sub-agents)

Defined in `.claude/agents/`. They are **read-only** (they never edit) and return JSON that the skill merges.

| Agent | Checks | Model |
|---|---|---|
| `fe-a11y-reviewer` | WCAG 2.2 AA: semantics, headings, names, keyboard, focus, ARIA, contrast (computed), motion, carousels/video, RTL, translatable strings | sonnet |
| `fe-perf-reviewer` | Core Web Vitals: LCP image handling, CLS (reserved space, JS-initialised widgets), INP (listeners, observers, `once`), CSS weight, Drupal library and render-cache patterns. Runs Lighthouse when a URL is given and a Lighthouse script is available | sonnet |
| `fe-standards-reviewer` | Project structure, SDC (component.yml schema, props vs. slots, thin adapters), Twig, SCSS/PostCSS/Tailwind (BEM, tokens, nesting), JS (behaviours + `once`, ES level), `libraries.yml`, PHP preprocess, security | sonnet |
| `fe-visual-qa` | Screenshots at 375/768/1366 vs. Figma frames: layout, spacing, typography, colours, RTL mirroring | sonnet |

Their rules live in `.claude/skills/frontend/references/checklists/` (accessibility, performance, standards). If your team has these skills installed in `~/.claude/skills/`, the reviewers **also** read them as the authoritative source: `accessibility-audit`, `performance-audit`, `drupal-coding-standards`. They are optional.

---

## 9. Reports and fixing

Each review writes two files to `reportsDir`:

- `YYYY-MM-DD-<component>.md`: a readable report (summary table per area, a findings table with file:line, issue, fix and auto-fixable, decisions needed, files reviewed)
- `YYYY-MM-DD-<component>.json`: the same findings, as machine-readable input for `/frontend fix`

`/frontend fix`:
1. **Auto-applies** safe fixes: alt/aria/labels, `rel="noopener"`, `|t` on strings, `once()` migration, `defer` on library JS, selector scoping, swapping a literal for an **existing** token, wrong library paths
2. **Asks you** about anything that changes the design or content: contrast colours, alt text wording, DOM order, new tokens, removing `!important`
3. Edits **source files only**, asks before running the build and cache clear, then re-scans and shows before/after

---

## 10. Customising

| I want to… | Edit |
|---|---|
| Protect more folders or files | `protectedPaths` / `askPaths` in `frontend.config.json` |
| Turn off the blocking stop gate | `"reviewGate": "warn"` |
| Add a scan rule | add a tuple to `RULES` in `.claude/skills/frontend/scripts/fe_scan.py`: `(id, severity, category, extensions, regex, flags, message)` |
| Add or change review rules | `.claude/skills/frontend/references/checklists/*.md` |
| Support another stack's file layout | add `.claude/skills/frontend/references/stacks/<stack>.md` (copy `drupal-legacy.md`) and set `"stack"` |
| Use a stronger or cheaper model for reviewers | the `model:` line in `.claude/agents/fe-*.md` (`sonnet`, `opus`, `haiku`, or `inherit`) |
| Block another dangerous command | `DENY` / `ASK` lists in `.claude/hooks/guard_bash.py` |
| Disable one hook | remove its entry from `.claude/settings.json` (or `/hooks` in Claude Code) |

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| The wrong theme was detected | Edit `theme` in `.claude/frontend.config.json` (the detector picks the custom theme with the most components/templates and a build). Run `detect_project.py` (no `--write`) to see what it finds |
| New components get the wrong structure | Set `"newComponents": "sdc"` or `"legacy"` |
| `/frontend` isn't suggested | Start Claude Code **from the project root** (where `.claude/` is), and check that `.claude/skills/frontend/SKILL.md` exists |
| Hooks don't fire | Run `/hooks`. Hooks come from the **project** `.claude/settings.json`, so Claude must be opened in that folder. Check `python3` is on PATH. Run `claude --debug hooks` to see each hook run |
| A hook blocks something legitimate | Read its message: it says why. Adjust `protectedPaths`/`askPaths`, or run the command yourself in a terminal |
| The scan reports nothing on an old file | By design it reports only **lines changed** vs. git. Use `fe_scan.py --all-lines <file>`, or `--base auto` for the whole branch |
| `component_files.py` finds too many or too few files | Use a more specific name or a folder path; you can name several things: `/frontend hero-banner "hero video parallax"` |
| Figma tools are missing | `/mcp` must show `framelink-figma-mcp` connected; check `FIGMA_API_KEY` is exported in the shell that starts Claude Code |
| Screenshots fail | `screenshotNode` must be Node 22+, Chrome must be installed, and the local site must be reachable (`ddev start`) |
| Build fails after Claude edits JS | Check your ESLint `ecmaVersion`. Old gulp setups (ES2015) fail on `?.`, `??`, `async/await` |
| The stop gate keeps asking | It blocks only once per identical problem set. Set `"reviewGate": "warn"` to only get summaries |

---

## 12. Uninstall

From your project root:

```bash
rm -rf .claude/skills/frontend .claude/agents/fe-*.md .claude/hooks .claude/state .claude/frontend.config.json
```

Then remove the hook entries from `.claude/settings.json`, or restore `.claude/settings.json.bak` if the installer created one.

---

## 13. File reference

```
.claude/
├── settings.json                         hook registration
├── frontend.config.example.json          copy → frontend.config.json and edit
├── skills/frontend/
│   ├── SKILL.md                          the /frontend playbook (modes, steps, gates)
│   ├── references/
│   │   ├── figma-build.md                Figma → code steps and approval gates
│   │   ├── stacks/detect.md              stack detection + conventions for React/Next/Vue/static
│   │   ├── stacks/drupal-sdc.md          SDC: folder layout, component.yml, Twig, JS, adapter templates
│   │   ├── stacks/drupal-legacy.md       legacy themes: templates, Sass, JS, libraries.yml
│   │   └── checklists/                   accessibility.md · performance.md · standards.md
│   └── scripts/
│       ├── detect_project.py             auto-detects the project → frontend.config.json
│       ├── fe_common.py                  shared helpers (config, compiled-file pairs, themes/modules)
│       ├── component_files.py            finds every file of a component (SDC + legacy, all custom themes/modules)
│       ├── fe_scan.py                    fast static scanner (changed lines, branch, or whole file)
│       ├── changed_files.py              frontend files changed on the branch
│       └── render_report.py              merged findings JSON → Markdown report
├── agents/
│   ├── fe-a11y-reviewer.md
│   ├── fe-perf-reviewer.md
│   ├── fe-standards-reviewer.md
│   └── fe-visual-qa.md
└── hooks/
    ├── _common.py                        shared helpers
    ├── session_start.py · guard_paths.py · guard_bash.py
    ├── post_edit_scan.py · stop_gate.py · notify.py
install.sh                                installer (auto-detects config; never overwrites; merges settings.json)
```

---

Built with Claude Code. Author: [@sankettale1](https://github.com/sankettale1).
