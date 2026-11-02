#!/usr/bin/env bash
# List frontend source files changed on this branch (vs. its merge base) plus uncommitted/untracked ones.
# Only files under "reviewRoots" from .claude/frontend.config.json are listed (default: themes/custom, modules/custom).
# Compiled output, source maps, vendor/contrib and Drupal config YAML are skipped.
# Usage: changed-files.sh [base-branch]   (default: origin/main, falling back to main/master/develop)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

roots=$(python3 -c 'import json,sys
try: c=json.load(open(".claude/frontend.config.json"))
except Exception: c={}
print("|".join(c.get("reviewRoots", ["themes/custom/", "modules/custom/"])))')

base="${1:-}"
if [[ -z "$base" ]]; then
  for b in origin/main origin/master origin/develop main master develop; do
    git rev-parse --verify -q "$b" >/dev/null && { base="$b"; break; }
  done
fi

{
  [[ -n "$base" ]] && git diff --name-only "$(git merge-base HEAD "$base")"...HEAD 2>/dev/null || true
  git diff --name-only HEAD
  git ls-files --others --exclude-standard
} | sort -u \
  | grep -E "^(${roots})" \
  | grep -E '\.(twig|html|scss|sass|css|less|js|mjs|ts|jsx|tsx|vue|svelte|theme)$|\.(libraries|breakpoints|info|component)\.yml$' \
  | grep -vE '(^|/)(node_modules|contrib|vendor)/|\.map$|\.min\.(js|css)$' \
  | grep -vE '^themes/custom/[^/]+/(css|js)/' \
  | while read -r f; do [[ -f "$f" ]] && echo "$f"; done
