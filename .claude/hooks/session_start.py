#!/usr/bin/env python3
"""SessionStart: give Claude the project's frontend conventions up front.

The rules come from the "## Quick rules" section of the stack reference
(.claude/skills/frontend/references/stacks/<stack>.md), with placeholders filled
from frontend.config.json, so every stack (legacy Drupal, SDC, Next, …) gets its own.
"""
import re
import subprocess

from _common import emit, load_config, project_dir, read_input

data = read_input()
root = project_dir(data)
cfg = load_config(root)
if not cfg:
    emit({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext':
          'Frontend workflow installed but .claude/frontend.config.json is missing. When frontend work starts, '
          'run `python3 .claude/skills/frontend/scripts/detect_project.py --write` (show the result to the user).'}})

theme = cfg.get('theme', {})
build = cfg.get('build', {})
stacks = root / '.claude' / 'skills' / 'frontend' / 'references' / 'stacks'


def quick_rules(stack):
    try:
        text = (stacks / f'{stack}.md').read_text()
    except OSError:
        return ''
    m = re.search(r'^## Quick rules\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not m:
        return ''
    values = {'<T>': theme.get('path', ''), '<t>': theme.get('name') or '', '<build>': build.get('command') or 'the build',
              '<build.cwd>': build.get('cwd') or '.', '<cacheClear>': cfg.get('cacheClear') or 'drush cr'}
    rules = m.group(1).strip()
    for k, v in values.items():
        rules = rules.replace(k, v)
    return rules


def git(*args):
    r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return r.stdout.strip()


stack = cfg.get('stack', 'auto-detect')
new = cfg.get('newComponents')
changed = [l for l in git('status', '--porcelain').splitlines() if theme.get('path') and theme['path'] in l]
lines = [
    'Frontend workflow is active (/frontend skill, fe-* reviewer subagents, guard + scan hooks).',
    f"Stack: {stack}. Theme: {theme.get('name')} at {theme.get('path')}"
    + (f" (other custom themes: {', '.join(cfg['otherThemes'])})" if cfg.get('otherThemes') else '')
    + f". Branch: {git('branch', '--show-current') or 'unknown'}. Uncommitted theme files: {len(changed)}.",
    quick_rules(stack),
]
# Mixed Drupal projects: existing components keep their style; new ones follow newComponents.
if stack.startswith('drupal') and new:
    other = 'drupal-sdc' if new == 'sdc' else 'drupal-legacy'
    lines.append(f'New components use the {new.upper()} structure. Existing components keep the structure they already have'
                 + (f' (see references/stacks/{other}.md for those).' if other != stack else '.'))
if theme.get('profile'):
    lines.append(f"Theme facts are in {theme['profile']}; read it instead of re-scanning the theme.")
lines.append(f"Build: cd {build.get('cwd') or '.'} && {build.get('command') or '(not configured)'} (ask first). "
             f"Cache: {cfg.get('cacheClear') or 'n/a'}.")

emit({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '\n'.join(l for l in lines if l)}})
