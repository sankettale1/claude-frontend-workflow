"""Shared project helpers for the /frontend scripts and hooks (standard library only)."""
import json
import os
import re
import subprocess
from pathlib import Path

PRUNE = {'node_modules', 'vendor', 'contrib', '.git', '.next', '.nuxt', 'dist', 'build', 'storybook-static'}


def project_root(start=None):
    start = Path(start or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()).resolve()
    for p in [start, *start.parents]:
        if (p / '.claude' / 'frontend.config.json').exists():
            return p
    try:
        out = subprocess.run(['git', '-C', str(start), 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return start


def load_config(root):
    try:
        return json.loads((Path(root) / '.claude' / 'frontend.config.json').read_text())
    except (OSError, ValueError):
        return {}


def compiled_source(rel, cfg, root):
    """If rel is a compiled output whose source exists, return the source path; else None."""
    for c in cfg.get('compiled', []):
        out, oext = c['output'], c['outputExt']
        if not rel.startswith(out) or not rel.endswith(oext):
            continue
        stem = rel[len(out):-len(oext)]
        rtl = c.get('rtlSuffix')
        if rtl and stem.endswith(rtl):
            stem = stem[:-len(rtl)]
        source = f"{c['source']}{stem}{c['sourceExt']}"
        if source != rel and (Path(root) / source).exists():
            return source
    return None


def is_generated(rel, cfg, root):
    return rel.endswith('.map') or compiled_source(rel, cfg, root) is not None


def search_roots(cfg, root):
    """Folders that hold the project's own frontend code."""
    roots = list(cfg.get('reviewRoots') or [])
    for p in [cfg.get('theme', {}).get('path'), *cfg.get('otherThemes', [])]:
        if p and not any(p.startswith(r) for r in roots if r):
            roots.append(p)
    roots = [Path(root) / r for r in roots if r is not None]
    return [r for r in roots if r.is_dir()] or [Path(root)]


def walk_files(base):
    for d, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in PRUNE and not x.startswith('.')]
        for f in files:
            yield Path(d) / f


def extensions(cfg, root):
    """Custom themes/modules: {machine_name: folder}."""
    found = {}
    for base in search_roots(cfg, root):
        for f in walk_files(base):
            if f.name.endswith('.info.yml'):
                found.setdefault(f.name[:-len('.info.yml')], f.parent)
    return found


def owner_extension(path):
    """(name, folder) of the nearest theme/module that contains path."""
    for parent in Path(path).resolve().parents:
        infos = list(parent.glob('*.info.yml'))
        if infos:
            return infos[0].name[:-len('.info.yml')], parent
        if (parent / '.git').exists():
            break
    return None, None


def sdc_component(ext_dir, name):
    """Path of <name>.component.yml inside an extension's components/ folder, or None."""
    comps = Path(ext_dir) / 'components'
    if not comps.is_dir():
        return None
    for f in walk_files(comps):
        if f.name == f'{name}.component.yml':
            return f
    return None


SDC_REF = re.compile(r'''(?:include|embed|extends|source)\s*\(?\s*["']([a-z_][a-z0-9_]*):([a-z0-9_-]+)["']''')
