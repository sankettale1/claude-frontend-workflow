#!/usr/bin/env python3
"""Find every source file that belongs to a component in a legacy Drupal theme.

Usage:
  component_files.py <name-or-path> [--json]

<name> can be written any way: StrategicCards, strategic-cards, strategic_cards,
"Strategic cards", a paragraph bundle, or a file/folder path. Matching ignores
case and separators. Compiled css/ and js/ output is never returned (review the
sources); library entries and preprocess functions are reported with line numbers.
"""
import json
import re
import sys
from pathlib import Path

SRC_EXT = ('.twig', '.scss', '.sass', '.css', '.js', '.ts', '.jsx', '.tsx', '.vue')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def load_config(root):
    try:
        return json.loads((root / '.claude' / 'frontend.config.json').read_text())
    except (OSError, ValueError):
        return {}


def find_root():
    for p in [Path.cwd(), *Path.cwd().parents]:
        if (p / '.claude' / 'frontend.config.json').exists() or (p / '.git').exists():
            return p
    return Path.cwd()


def is_compiled(rel, cfg):
    return any(rel.startswith(c['output']) for c in cfg.get('compiled', []))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    as_json = '--json' in sys.argv
    if not args:
        sys.exit(__doc__)
    query = ' '.join(args)
    root = find_root()
    cfg = load_config(root)
    theme_name = cfg.get('theme', {}).get('name', '')
    theme = root / cfg.get('theme', {}).get('path', '.')

    files = set()
    target = (root / query) if not Path(query).is_absolute() else Path(query)
    if target.exists():
        # A path: take it (and everything under it), then also match by its name.
        items = target.rglob('*') if target.is_dir() else [target]
        files.update(p for p in items if p.is_file() and p.suffix in SRC_EXT)
        name = target.name.split('.')[0] if target.is_file() else target.name
        key = norm(re.sub(r'^(paragraph|block|node|field|views-view)-+', '', name))
    else:
        key = norm(query)
    if len(key) < 3:
        sys.exit('Name too short to match safely.')

    for p in theme.rglob('*'):
        rel = p.relative_to(root).as_posix()
        if 'node_modules' in rel or is_compiled(rel, cfg) or p.suffix not in SRC_EXT or not p.is_file():
            continue
        parts = [norm(x) for x in p.relative_to(theme).parts[:-1]]
        if key in norm(p.name.split('.html')[0]) or key in parts:
            files.add(p)

    rel_files = sorted(p.relative_to(root).as_posix() for p in files if not is_compiled(p.relative_to(root).as_posix(), cfg))

    # Library entries: key matches the library name or one of its asset paths.
    libraries = []
    lib_file = theme / f'{theme_name}.libraries.yml'
    if lib_file.exists():
        current, start = None, 0
        for i, line in enumerate(lib_file.read_text(errors='ignore').splitlines(), 1):
            m = re.match(r'^([\w.-]+):\s*$', line)
            if m:
                current, start = m.group(1), i
                if key in norm(current):
                    libraries.append({'name': current, 'line': i})
            elif current and key in norm(line) and not any(l['name'] == current for l in libraries):
                libraries.append({'name': current, 'line': start})

    # Follow the wiring: sources behind each library's assets, and templates that attach it.
    if libraries:
        names = {l['name'] for l in libraries}
        lib_text = lib_file.read_text(errors='ignore')
        for name in names:
            block = re.search(rf'^{re.escape(name)}:\s*\n((?:[ \t]+.*\n?|\s*\n)*)', lib_text, re.M)
            for asset in re.findall(r'([\w./-]+\.(?:css|js)):', block.group(1) if block else ''):
                rel = (theme / asset).relative_to(root).as_posix()
                for c in cfg.get('compiled', []):
                    if rel.startswith(c['output']) and rel.endswith(c['outputExt']):
                        stem = rel[len(c['output']):-len(c['outputExt'])]
                        if c.get('rtlSuffix') and stem.endswith(c['rtlSuffix']):
                            stem = stem[:-len(c['rtlSuffix'])]
                        src = root / f"{c['source']}{stem}{c['sourceExt']}"
                        if src.exists():
                            rel_files.append(src.relative_to(root).as_posix())
        attach = re.compile(r'attach_library\(\s*["\']' + re.escape(theme_name) + r'/(' +
                            '|'.join(re.escape(n) for n in names) + r')["\']')
        for twig in theme.rglob('*.twig'):
            if attach.search(twig.read_text(errors='ignore')):
                rel_files.append(twig.relative_to(root).as_posix())
        rel_files = sorted(set(rel_files))

    # Partials included/embedded by the component's templates (one level).
    by_name = {}
    for twig in theme.rglob('*.twig'):
        by_name.setdefault(twig.name, []).append(twig)
    for f in [f for f in rel_files if f.endswith('.twig')]:
        text = (root / f).read_text(errors='ignore')
        for ref in re.findall(r'(?:include|embed|extends)\s*\(?\s*["\']([^"\']+\.twig)["\']', text):
            for match in by_name.get(Path(ref).name, []):
                rel_files.append(match.relative_to(root).as_posix())
    rel_files = sorted(set(rel_files))

    # Preprocess / hook functions in the .theme file.
    preprocess = []
    theme_file = theme / f'{theme_name}.theme'
    if theme_file.exists():
        for i, line in enumerate(theme_file.read_text(errors='ignore').splitlines(), 1):
            m = re.match(r'^function\s+(\w+)\s*\(', line)
            if m and key in norm(m.group(1)):
                preprocess.append({'function': m.group(1), 'line': i})

    groups = {
        'templates': [f for f in rel_files if f.endswith('.twig')],
        'styles': [f for f in rel_files if f.endswith(('.scss', '.sass', '.css'))],
        'scripts': [f for f in rel_files if f.endswith(('.js', '.ts', '.jsx', '.tsx', '.vue'))],
    }
    result = {
        'query': query, 'key': key, 'exists': bool(rel_files or libraries),
        **groups,
        'libraries': libraries,
        'librariesFile': lib_file.relative_to(root).as_posix() if libraries else None,
        'preprocess': preprocess,
        'themeFile': theme_file.relative_to(root).as_posix() if preprocess else None,
        'reviewFiles': rel_files + ([lib_file.relative_to(root).as_posix()] if libraries else []),
        'tooBroad': len(rel_files) > 40,
    }
    if as_json:
        print(json.dumps(result, indent=2))
        return
    print(f"Component '{query}' (key: {key}) — {'found' if result['exists'] else 'NOT FOUND'}")
    for g in ('templates', 'styles', 'scripts'):
        for f in result[g]:
            print(f'  {g[:-1]:9} {f}')
    for l in libraries:
        print(f"  library   {result['librariesFile']}:{l['line']}  {l['name']}")
    for f in preprocess:
        print(f"  preproc   {result['themeFile']}:{f['line']}  {f['function']}()")
    if result['tooBroad']:
        print('  WARNING: more than 40 files matched; use a more specific name or a path.')


if __name__ == '__main__':
    main()
