#!/usr/bin/env python3
"""List frontend source files changed on this branch (vs. its merge base) plus uncommitted/untracked ones.

Usage: changed_files.py [base-branch]   (default: origin/main, falling back to master/develop)

Only files under reviewRoots from .claude/frontend.config.json are listed. Compiled
output (per the config's "compiled" pairs), source maps, vendor/contrib/node_modules
and Drupal config YAML are skipped.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fe_common import is_generated, load_config, project_root  # noqa: E402

EXT = re.compile(r'\.(twig|html|scss|sass|pcss|css|less|js|mjs|ts|jsx|tsx|vue|svelte|theme|module)$'
                 r'|\.(libraries|breakpoints|info|component)\.yml$|\.stories\.(js|json|yml)$')
SKIP = re.compile(r'(^|/)(node_modules|contrib|vendor|\.next|dist|build)/|\.min\.(js|css)$')


def git(root, *args):
    r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def main():
    root = project_root()
    cfg = load_config(root)
    roots = tuple(cfg.get('reviewRoots') or [''])
    base = sys.argv[1] if len(sys.argv) > 1 else next(
        (b for b in ('origin/main', 'origin/master', 'origin/develop', 'main', 'master', 'develop')
         if subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '-q', b], capture_output=True).returncode == 0), None)
    names = set(git(root, 'diff', '--name-only', 'HEAD')) | set(git(root, 'ls-files', '--others', '--exclude-standard'))
    if base:
        mb = git(root, 'merge-base', 'HEAD', base)
        if mb:
            names |= set(git(root, 'diff', '--name-only', f'{mb[0]}...HEAD'))
    for f in sorted(names):
        if f.startswith(roots) and EXT.search(f) and not SKIP.search(f) and not f.startswith('.claude/') \
                and (root / f).is_file() and not is_generated(f, cfg, root):
            print(f)


if __name__ == '__main__':
    main()
