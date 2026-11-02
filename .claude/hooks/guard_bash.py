#!/usr/bin/env python3
"""PreToolUse (Bash): block destructive commands, ask before dependency/config changes."""
import re

from _common import emit, read_input

cmd = ((read_input().get('tool_input') or {}).get('command') or '').strip()

DENY = [
    (r'\bdrush\b.*\b(sql-drop|sql:drop|site-install|site:install|si)\b', 'drops or reinstalls the database'),
    (r'\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)', 'force-pushes'),
    (r'\bgit\s+reset\s+--hard\b', 'discards uncommitted work'),
    (r'\bgit\s+clean\s+-\w*f', 'deletes untracked files'),
    (r'\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)', 'discards all working-tree changes'),
    (r'\brm\s+-\w*r\w*\s+(.*\s)?(/|~|\.|\.\.|core|vendor|sites|themes|modules|\.git)/?(\s|$)', 'recursively deletes a project root folder'),
]
ASK = [
    (r'\b(npm|yarn|pnpm)\s+(install|i|ci|add|remove|uninstall|update|upgrade)\b', 'changes node dependencies / lockfile'),
    (r'\bcomposer\s+(require|update|remove|install)\b', 'changes PHP dependencies'),
    (r'\bdrush\b.*\b(cim|config:import|config-import|updb|updatedb|pmu|pm:uninstall|en|pm:enable|pm:install)\b', 'changes site configuration/modules'),
    (r'\bgit\s+push\b', 'publishes commits'),
]

for pattern, why in DENY:
    if re.search(pattern, cmd):
        emit({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': f'[frontend guard] Blocked: this command {why}. Ask the user to run it themselves if it is really needed.',
        }})
for pattern, why in ASK:
    if re.search(pattern, cmd):
        emit({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'ask',
            'permissionDecisionReason': f'[frontend guard] This command {why}. Confirm before it runs.',
        }})
