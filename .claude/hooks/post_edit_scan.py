#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit): scan the lines Claude just changed.

Errors are fed back to Claude as a blocking message so it fixes them right away;
warnings are added as context. The file is also queued for the Stop gate.
"""
import json
import subprocess
import sys

from _common import emit, load_state, project_dir, read_input, rel_path, save_state

FE_EXT = ('.twig', '.html', '.scss', '.sass', '.css', '.less', '.js', '.mjs', '.ts',
          '.jsx', '.tsx', '.vue', '.svelte', '.yml', '.yaml', '.theme', '.php')

data = read_input()
root = project_dir(data)
rel = rel_path(root, (data.get('tool_input') or {}).get('file_path'))
if rel is None or not rel.endswith(FE_EXT) or rel.startswith('.claude/'):
    sys.exit(0)

state = load_state(root, data.get('session_id'))
if rel not in state['pending']:
    state['pending'].append(rel)
save_state(root, data.get('session_id'), state)

scanner = root / '.claude' / 'skills' / 'frontend' / 'scripts' / 'fe_scan.py'
res = subprocess.run([sys.executable, str(scanner), '--json', str(root / rel)],
                     capture_output=True, text=True, timeout=30)
try:
    findings = json.loads(res.stdout or '[]')
except ValueError:
    sys.exit(0)
if not findings:
    sys.exit(0)

lines = '\n'.join(f"- {rel}:{f['line']} {f['severity'].upper()} [{f['category']}/{f['rule']}] {f['message']}"
                  for f in findings)
if any(f['severity'] == 'error' for f in findings):
    emit({'decision': 'block',
          'reason': f'[frontend scan] Your edit introduced issues. Fix the ERRORs now:\n{lines}'})
emit({'hookSpecificOutput': {
    'hookEventName': 'PostToolUse',
    'additionalContext': f'[frontend scan] Warnings on the lines you changed (fix if reasonable, otherwise mention them):\n{lines}',
}})
