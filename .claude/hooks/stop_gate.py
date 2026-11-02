#!/usr/bin/env python3
"""Stop: quality gate for the frontend files edited this turn.

Re-scans the edited files and checks that compiled CSS/JS is not older than its
dev/ source. With reviewGate "block", Claude is sent back once per distinct
problem set to fix it; otherwise the user just gets a summary and a desktop
notification.
"""
import hashlib
import json
import subprocess
import sys

from _common import emit, load_config, load_state, project_dir, read_input, rel_path, save_state

data = read_input()
root = project_dir(data)
cfg = load_config(root)
sid = data.get('session_id')
state = load_state(root, sid)
files = [f for f in state['pending'] if (root / f).exists()]
if not files:
    sys.exit(0)

scanner = root / '.claude' / 'skills' / 'frontend' / 'scripts' / 'fe_scan.py'
res = subprocess.run([sys.executable, str(scanner), '--json', *[str(root / f) for f in files]],
                     capture_output=True, text=True, timeout=60)
try:
    findings = json.loads(res.stdout or '[]')
except ValueError:
    findings = []
errors = [f for f in findings if f['severity'] == 'error']
warns = [f for f in findings if f['severity'] == 'warn']

stale = []
for c in cfg.get('compiled', []):
    for f in files:
        name = f.rsplit('/', 1)[-1]
        if not f.startswith(c['source']) or not f.endswith(c['sourceExt']) or name.startswith('_'):
            continue
        out = root / (c['output'] + f[len(c['source']):-len(c['sourceExt'])] + c['outputExt'])
        if not out.exists() or out.stat().st_mtime < (root / f).stat().st_mtime:
            stale.append(out.relative_to(root).as_posix())

problems = [f"- {rel_path(root, f['file'])}:{f['line']} [{f['rule']}] {f['message']}" for f in errors]
problems += [f'- {s} is missing or older than its source (build not run)' for s in stale]
signature = hashlib.sha1('\n'.join(problems).encode()).hexdigest()

if problems and cfg.get('reviewGate') == 'block' and not data.get('stop_hook_active') \
        and signature != state.get('lastBlock'):
    state['lastBlock'] = signature
    save_state(root, sid, state)
    build = cfg.get('build', {})
    todo = []
    if errors:
        todo.append('Fix the errors in the source files.')
    if stale:
        todo.append(f"Ask the user whether to run `cd {build.get('cwd', '.')} && {build.get('command', 'npm run build')}` "
                    f"(node from {build.get('node', 'PATH')}), or tell them the build is still pending.")
    emit({'decision': 'block', 'reason':
          '[frontend gate] Before finishing, resolve these:\n' + '\n'.join(problems) + '\n' + ' '.join(todo)})

summary = (f'Frontend: {len(files)} file(s) edited, {len(errors)} error(s), {len(warns)} warning(s)'
           + (f', {len(stale)} stale build output(s)' if stale else '')
           + '. Full review: /frontend review --changed')
state['pending'] = []
save_state(root, sid, state)
subprocess.run(['notify-send', '-a', 'Claude Code', 'Frontend turn finished', summary],
               capture_output=True)
print(json.dumps({'systemMessage': summary}))
