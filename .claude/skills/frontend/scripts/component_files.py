#!/usr/bin/env python3
"""Find every source file that belongs to a component, in any Drupal structure.

Usage:
  component_files.py <name-or-path> [--json]

Works for SDC components (components/**/<name>/<name>.component.yml), legacy
themes (templates + Sass/JS + libraries.yml), and mixed projects, across all
custom themes and modules. <name> can be written any way: PricingCard,
pricing-card, pricing_card, "Pricing card", an SDC id (mytheme:pricing-card)
or a file/folder path. Compiled output is never returned; review the sources.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fe_common import (SDC_REF, extensions, is_generated, load_config, project_root,  # noqa: E402
                       search_roots, walk_files)

SRC_EXT = ('.twig', '.scss', '.sass', '.pcss', '.css', '.less', '.js', '.ts', '.jsx', '.tsx', '.vue', '.yml', '.json', '.md')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def tiered(candidates, key, name_of):
    """Exact match first, then prefix/suffix, then substring, so 'card' doesn't swallow everything."""
    for test in (lambda n: n == key, lambda n: n.endswith(key) or n.startswith(key), lambda n: key in n):
        hits = [c for c in candidates if test(norm(name_of(c)))]
        if hits:
            return hits
    return []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    query = ' '.join(args)
    root = project_root()
    cfg = load_config(root)
    exts = extensions(cfg, root)
    relp = lambda p: Path(p).resolve().relative_to(root.resolve()).as_posix()

    files, notes = set(), []
    target = Path(query) if Path(query).is_absolute() else root / query
    if ':' in query and not target.exists():          # SDC id: provider:name
        query = query.split(':', 1)[1]
    if target.exists():
        items = target.rglob('*') if target.is_dir() else [target]
        files.update(p for p in items if p.is_file())
        name = target.name if target.is_dir() else target.name.split('.')[0]
        key = norm(re.sub(r'^(paragraph|block|node|field|views-view)-+', '', name))
    else:
        key = norm(query)
    if len(key) < 3:
        sys.exit('Name too short to match safely.')

    all_files = [f for base in search_roots(cfg, root) for f in walk_files(base)]

    # 1. SDC components: folders that contain <folder>.component.yml.
    sdc_dirs = [f.parent for f in all_files if f.name == f'{f.parent.name}.component.yml']
    sdc_hits = tiered(sdc_dirs, key, lambda d: d.name)
    components = []
    for d in sdc_hits:
        provider = next((n for n, p in exts.items() if p in d.parents), '?')
        components.append({'id': f'{provider}:{d.name}', 'dir': relp(d)})
        files.update(p for p in d.rglob('*') if p.is_file())

    # 2. Legacy pieces: files whose name or parent folder matches.
    for f in all_files:
        if f.suffix not in SRC_EXT or f.name.endswith(('.info.yml', '.libraries.yml', '.component.yml')):
            continue
        parts = [norm(x) for x in f.parent.parts[-3:]]
        if key in norm(f.name.split('.html')[0].split('.')[0]) or key in parts:
            files.add(f)

    # 3. Library entries + their source files + templates attaching them.
    libraries, attach_patterns = [], []
    for ext, ext_dir in exts.items():
        lib_file = ext_dir / f'{ext}.libraries.yml'
        if not lib_file.exists():
            continue
        text = lib_file.read_text(errors='ignore')
        blocks = re.findall(r'^([\w.-]+):\s*\n((?:[ \t]+.*\n?|[ \t]*\n)*)', text, re.M)
        for name, body in blocks:
            if key in norm(name) or key in norm(body):
                line = text[:text.find(f'\n{name}:') + 1].count('\n') + 1 if not text.startswith(f'{name}:') else 1
                libraries.append({'name': f'{ext}/{name}', 'file': relp(lib_file), 'line': line})
                attach_patterns.append(f'{ext}/{name}')
                for asset in re.findall(r'([\w./-]+\.(?:css|js)):', body):
                    a = ext_dir / asset
                    if a.exists():
                        files.add(a)

    # 4. Templates that use the component (SDC include/embed or attach_library) = adapters to review.
    sdc_ids = {c['id'] for c in components}
    used_by, uses = set(), set()
    for f in all_files:
        if not f.name.endswith('.twig'):
            continue
        text = f.read_text(errors='ignore')
        refs = {f'{a}:{b}' for a, b in SDC_REF.findall(text)}
        if refs & sdc_ids or any(f"'{p}'" in text or f'"{p}"' in text for p in attach_patterns):
            if f not in files:
                used_by.add(f)
        if f in files:
            uses.update(r for r in refs if r not in sdc_ids)

    # 5. Twig partials included by legacy templates (one level, by file name).
    by_name = {}
    for f in all_files:
        if f.name.endswith('.twig'):
            by_name.setdefault(f.name, []).append(f)
    for f in [f for f in files | used_by if f.name.endswith('.twig')]:
        for ref in re.findall(r'''(?:include|embed|extends)\s*\(?\s*["']([^"':]+\.twig)["']''', f.read_text(errors='ignore')):
            files.update(by_name.get(Path(ref).name, []))

    # 6. Preprocess/hooks in .theme/.module files.
    preprocess = []
    for ext, ext_dir in exts.items():
        for php in (ext_dir / f'{ext}.theme', ext_dir / f'{ext}.module'):
            if php.exists():
                for i, line in enumerate(php.read_text(errors='ignore').splitlines(), 1):
                    m = re.match(r'^function\s+(\w+)\s*\(', line)
                    if m and key in norm(m.group(1)):
                        preprocess.append({'function': m.group(1), 'file': relp(php), 'line': i})

    src = sorted({relp(f) for f in files | used_by if f.is_file()} - {None})
    reports = (cfg.get('reportsDir') or '\0').rstrip('/') + '/'
    src = [f for f in src if not is_generated(f, cfg, root) and not f.startswith(reports)
           and not f.endswith(('.png', '.jpg', '.svg', '.gif', '.webp'))]
    lib_files = sorted({l['file'] for l in libraries})
    kind = 'sdc' if components and not any(f.endswith('.html.twig') for f in src if relp(root / f) not in
                                            {relp(u) for u in used_by}) else ('mixed' if components else 'legacy')
    result = {
        'query': query, 'key': key, 'exists': bool(src or libraries), 'kind': kind if src else None,
        'components': components,
        'templates': [f for f in src if f.endswith('.twig') and root / f not in used_by],
        'usedBy': sorted(relp(u) for u in used_by),
        'styles': [f for f in src if f.endswith(('.scss', '.sass', '.pcss', '.css', '.less'))],
        'scripts': [f for f in src if f.endswith(('.js', '.ts', '.jsx', '.tsx', '.vue'))],
        'definitions': [f for f in src if f.endswith(('.component.yml', '.stories.js', '.stories.json', '.md'))],
        'libraries': libraries, 'preprocess': preprocess,
        'usesComponents': sorted(uses),
        'reviewFiles': sorted(set(src) | set(lib_files)),
        'tooBroad': len(src) > 40,
    }
    if '--json' in sys.argv:
        print(json.dumps(result, indent=2))
        return
    print(f"Component '{query}' (key: {key}) — {'found, ' + str(result['kind']) if result['exists'] else 'NOT FOUND'}")
    for c in components:
        print(f"  sdc       {c['id']}  ({c['dir']})")
    for g in ('definitions', 'templates', 'styles', 'scripts', 'usedBy'):
        for f in result[g]:
            print(f'  {g[:9]:9} {f}')
    for l in libraries:
        print(f"  library   {l['file']}:{l['line']}  {l['name']}")
    for p in preprocess:
        print(f"  preproc   {p['file']}:{p['line']}  {p['function']}()")
    if uses:
        print(f"  uses      {', '.join(sorted(uses))}")
    if result['tooBroad']:
        print('  WARNING: more than 40 files matched; use a more specific name, an SDC id or a path.')


if __name__ == '__main__':
    main()
