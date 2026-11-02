#!/usr/bin/env bash
# Install the /frontend workflow into a project.
#
#   ./install.sh /path/to/project            # add files, never overwrite
#   ./install.sh /path/to/project --force    # also update files that already exist
#
# An existing .claude/settings.json is never replaced: the hooks are merged into it
# (a backup is written to settings.json.bak first).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
target="${1:?usage: ./install.sh /path/to/project [--force]}"
force="${2:-}"
[[ -d "$target" ]] || { echo "No such directory: $target" >&2; exit 1; }
target="$(cd "$target" && pwd)"
dest="$target/.claude"
mkdir -p "$dest/skills" "$dest/agents" "$dest/hooks" "$dest/state"

copy() { # copy <src> <dst>: skip existing unless --force
  if [[ -e "$2" && "$force" != "--force" ]]; then
    echo "  skip (exists)  ${2#"$target"/}"
  else
    if [[ -d "$1" ]]; then mkdir -p "$2" && cp -R "$1/." "$2/"; else cp "$1" "$2"; fi
    echo "  added          ${2#"$target"/}"
  fi
}

echo "Installing into $target"
copy "$here/.claude/skills/frontend" "$dest/skills/frontend"
for f in "$here"/.claude/agents/*.md; do copy "$f" "$dest/agents/$(basename "$f")"; done
for f in "$here"/.claude/hooks/*.py; do copy "$f" "$dest/hooks/$(basename "$f")"; done
copy "$here/.claude/state/.gitignore" "$dest/state/.gitignore"

if [[ -e "$dest/settings.json" ]]; then
  cp "$dest/settings.json" "$dest/settings.json.bak"
  python3 - "$here/.claude/settings.json" "$dest/settings.json" <<'EOF'
import json, sys
ours, theirs_path = json.load(open(sys.argv[1])), sys.argv[2]
theirs = json.load(open(theirs_path))
hooks = theirs.setdefault('hooks', {})
added = 0
for event, groups in ours['hooks'].items():
    existing = {h.get('command') for g in hooks.get(event, []) for h in g.get('hooks', [])}
    for group in groups:
        if not any(h['command'] in existing for h in group['hooks']):
            hooks.setdefault(event, []).append(group)
            added += 1
json.dump(theirs, open(theirs_path, 'w'), indent=2)
print(f'  merged         .claude/settings.json ({added} hook group(s) added, backup: settings.json.bak)')
EOF
else
  cp "$here/.claude/settings.json" "$dest/settings.json"
  echo "  added          .claude/settings.json"
fi

if [[ ! -e "$dest/frontend.config.json" ]]; then
  cp "$here/.claude/frontend.config.example.json" "$dest/frontend.config.json"
  echo "  added          .claude/frontend.config.json   <-- edit this for your project (README step 3)"
fi

chmod +x "$dest"/hooks/*.py "$dest"/skills/frontend/scripts/*
echo "Done. Next: edit .claude/frontend.config.json, then restart Claude Code in $target."
