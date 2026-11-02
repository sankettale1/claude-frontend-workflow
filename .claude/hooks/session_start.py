#!/usr/bin/env python3
"""SessionStart: give Claude the project's frontend conventions up front."""
import subprocess

from _common import emit, load_config, project_dir, read_input

data = read_input()
root = project_dir(data)
cfg = load_config(root)
theme = cfg.get('theme', {})


def git(*args):
    r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return r.stdout.strip()


branch = git('branch', '--show-current') or 'unknown'
changed = [l[3:] for l in git('status', '--porcelain').splitlines()
           if theme.get('path', '~') in l]
t = theme.get('path', '')
context = f"""Frontend workflow is active (/frontend skill, reviewer subagents, guard + scan hooks).
Stack: {cfg.get('stack', 'auto-detect')}. Theme: {theme.get('name')} at {t}. Branch: {branch}. \
Uncommitted theme files: {len(changed)}.
House rules for this project (legacy, non-SDC theme):
- Twig: {t}/templates/<group>/<Pascal>/*.html.twig; attach '{theme.get('name')}/<lib>' or '<lib>-rtl' via `is_rtl`.
- Styles: edit {t}/dev/scss/style/components/<Pascal>/*.scss only; compiled css/ and -rtl.css come from gulp.
- JS: {t}/dev/js/components/*.js with Drupal.behaviors + core `once` (never jQuery.once).
- Libraries: {t}/{theme.get('name')}.libraries.yml, LTR + -rtl twin, JS with {{attributes: {{defer: true}}}}.
- Theme facts are in {theme.get('profile')}; read it instead of re-scanning the theme.
- Build: cd {cfg.get('build', {}).get('cwd')} && {cfg.get('build', {}).get('command')} (ask first). Cache: {cfg.get('cacheClear')}."""

emit({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': context}})
