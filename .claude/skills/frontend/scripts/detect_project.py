#!/usr/bin/env python3
"""Detect a project's frontend setup and print (or write) .claude/frontend.config.json.

Usage:
  detect_project.py [project-root] [--write] [--force]

Works for any Drupal 9/10/11 project (docroot at ., web/, docroot/ or html/;
SDC, legacy or mixed themes; gulp/webpack/vite builds) and falls back to a
generic config for non-Drupal frontends (Next, React, Vue, static).
Without --write it only prints the config, so you can review it first.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP = {'node_modules', '.git', 'vendor', 'contrib'}


def rel(p, root):
    return p.relative_to(root).as_posix()


def walk(base, pattern, max_depth=6):
    """Find files matching a glob pattern, pruning node_modules/vendor/contrib and deep folders."""
    out = []
    if not base.is_dir():
        return out
    base_depth = len(base.parts)
    for d, dirs, files in os.walk(base):
        depth = len(Path(d).parts) - base_depth
        dirs[:] = [x for x in dirs if x not in SKIP and not x.startswith('.')] if depth < max_depth - 1 else []
        out.extend(Path(d) / f for f in files if Path(f).match(pattern))
    return out


def read_json(p):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def find_docroot(root):
    for d in ('web', 'docroot', 'html', 'public', '.'):
        if (root / d / 'core' / 'lib' / 'Drupal.php').exists():
            return d
    for d in ('web', 'docroot', 'html', '.'):  # core not installed yet: look for custom themes/modules
        if (root / d / 'themes' / 'custom').is_dir() or (root / d / 'modules' / 'custom').is_dir():
            return d
    return None


def default_theme(root):
    for cfg in walk(root, 'system.theme.yml', 5):
        m = re.search(r'^default:\s*(\S+)', cfg.read_text(errors='ignore'), re.M)
        if m:
            return m.group(1).strip('\'"')
    return None


def theme_info(info, custom_dir):
    """Facts about one custom theme (info = its *.info.yml)."""
    path = info.parent
    pkg_dir = next((d for d in [path, *path.parents] if (d / 'package.json').exists()
                    and custom_dir in d.parents), None)
    return {'name': info.name[:-len('.info.yml')], 'path': path,
            'components': len(walk(path / 'components', '*.component.yml', 5)),
            'templates': len(walk(path / 'templates', '*.twig', 6)),
            'pkgDir': pkg_dir, 'pkg': read_json(pkg_dir / 'package.json') if pkg_dir else {}}


def build_tool(pkg_dir, pkg):
    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
    scripts = pkg.get('scripts', {})
    tool = next((t for t in ('gulp', 'webpack', 'vite', 'laravel-mix', 'parcel', 'esbuild', 'sass', 'postcss')
                 if t in deps or any(t in s for s in scripts.values())), None)
    mgr = 'yarn' if (pkg_dir / 'yarn.lock').exists() and not (pkg_dir / 'package-lock.json').exists() else 'npm run'
    names = [n for n in ('build', 'production', 'prod', 'dist', 'compile', 'build:drupal', 'build:theme') if n in scripts]
    names += [n for n in scripts if n.startswith('build') and 'storybook' not in n and 'watch' not in n]
    return (f'{mgr} {names[0]}' if names else None), tool, deps


def node_bin(dirs):
    for d in dirs:
        f = d / '.nvmrc'
        if f.exists():
            v = f.read_text().strip().lstrip('v')
            matches = sorted(Path.home().glob(f'.nvm/versions/node/v{v}*'))
            if matches:
                return f'~/{rel(matches[-1], Path.home())}/bin'
    return None


def compiled_pairs(root, theme_path):
    pairs = []
    t = theme_path
    # Legacy: a separate source folder compiled into an output folder.
    for src, out, sext, oext in (
        ('dev/scss', 'css', '.scss', '.css'), ('scss', 'css', '.scss', '.css'), ('sass', 'css', '.scss', '.css'),
        ('src/scss', 'dist/css', '.scss', '.css'), ('src/scss', 'css', '.scss', '.css'),
        ('assets/scss', 'assets/css', '.scss', '.css'), ('src/sass', 'dist/css', '.scss', '.css'),
        ('dev/js', 'js', '.js', '.js'), ('src/js', 'dist/js', '.js', '.js'), ('src/js', 'js', '.js', '.js'),
        ('js-src', 'js', '.js', '.js'), ('assets/js/src', 'assets/js', '.js', '.js'),
    ):
        if (t / src).is_dir() and (t / out).is_dir():
            pairs.append({'source': f'{rel(t / src, root)}/', 'sourceExt': sext,
                          'output': f'{rel(t / out, root)}/', 'outputExt': oext})
    # SDC / co-located: source and compiled file side by side in components/.
    comp = t / 'components'
    for sext, oext in (('.pcss', '.css'), ('.scss', '.css'), ('.behavior.js', '.js'), ('.src.js', '.js'),
                       ('.es6.js', '.js'), ('.ts', '.js')):
        for f in walk(comp, f'*{sext}', 6):
            if Path(str(f)[:-len(sext)] + oext).exists():
                pairs.append({'source': f'{rel(comp, root)}/', 'sourceExt': sext,
                              'output': f'{rel(comp, root)}/', 'outputExt': oext})
                break
    if any(walk(t, '*-rtl.css', 6)):
        for p in pairs:
            if p['outputExt'] == '.css':
                p['rtlSuffix'] = '-rtl'
    return pairs


def ddev_url(root):
    cfg = root / '.ddev' / 'config.yaml'
    if not cfg.exists():
        return None
    text = cfg.read_text(errors='ignore')
    m = re.search(r'^name:\s*(\S+)', text, re.M)
    tld = re.search(r'^project_tld:\s*(\S+)', text, re.M)
    return f"https://{m.group(1).lower()}.{tld.group(1) if tld else 'ddev.site'}" if m else None


def detect(root):
    doc = find_docroot(root)
    pre = '' if doc in (None, '.') else f'{doc}/'
    has_ddev = (root / '.ddev').is_dir()
    cfg = {}

    if doc is None:  # Not Drupal: generic frontend.
        pkg = read_json(root / 'package.json')
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        stack = next((s for s, d in (('next', 'next'), ('nuxt', 'nuxt'), ('vue', 'vue'), ('astro', 'astro'),
                                     ('svelte', 'svelte'), ('react', 'react')) if d in deps), 'static')
        src = next((d for d in ('src', 'app', 'components', '.') if (root / d).is_dir()), '.')
        cmd, _, _ = build_tool(root, pkg)
        return {
            'stack': stack, 'newComponents': stack,
            'theme': {'name': root.name, 'path': src},
            'localUrl': 'http://localhost:3000' if stack in ('next', 'react', 'nuxt', 'vue') else None,
            'build': {'command': cmd, 'cwd': '.'},
            'protectedPaths': ['node_modules/', '.next/', 'dist/', 'build/', '.nuxt/'],
            'askPaths': ['package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '.env'],
            'compiled': [], 'reviewRoots': [f'{src}/' if src != '.' else ''],
            'reviewGate': 'block', 'reportsDir': 'docs/frontend-reviews',
        }

    custom = root / pre / 'themes' / 'custom'
    themes = [theme_info(p, custom) for p in walk(custom, '*.info.yml', 4)
              if re.search(r'^type:\s*theme', p.read_text(errors='ignore'), re.M)]
    dflt = default_theme(root)
    # The theme people actually build in: the most components/templates, has a build, default theme as a tiebreak.
    chosen = max(themes, key=lambda t: t['components'] * 5 + t['templates'] + (200 if t['pkg'] else 0)
                 + (100 if t['name'] == dflt else 0), default=None)
    module_components = len(walk(root / pre / 'modules' / 'custom', '*.component.yml', 6))

    if chosen:
        sdc, legacy = chosen['components'], chosen['templates']
        stack = 'drupal-sdc' if sdc and sdc * 3 >= legacy else 'drupal-legacy'
        new = 'sdc' if sdc else 'legacy'
        t = chosen['path']
        pkg_dir = chosen['pkgDir'] or root
        cmd, tool, deps = build_tool(pkg_dir, chosen['pkg'] or read_json(root / 'package.json'))
        cfg.update({
            'stack': stack,
            'newComponents': new,
            'theme': {'name': chosen['name'], 'path': rel(t, root)},
            'otherThemes': [rel(x['path'], root) for x in themes if x is not chosen],
            'build': {'command': cmd, 'cwd': rel(pkg_dir, root) if pkg_dir != root else '.', 'tool': tool},
            'compiled': compiled_pairs(root, t),
            'rtl': any(k in deps for k in ('rtlcss', 'gulp-rtlcss', 'postcss-rtlcss', 'rtlcss-webpack-plugin')),
            'reportsDir': f'{rel(t, root)}/docs/frontend-reviews',
        })
        nb = node_bin([t, pkg_dir, root])
        if nb:
            cfg['build']['node'] = nb
        profile = root / '.claude' / 'theme-discovery' / 'theme-profile.json'
        if profile.exists():
            cfg['theme']['profile'] = rel(profile, root)
    else:
        cfg.update({'stack': 'drupal-sdc',
                    'newComponents': 'sdc', 'theme': {'name': None, 'path': f'{pre}themes/custom'},
                    'build': {'command': None, 'cwd': '.'}, 'compiled': [],
                    'reportsDir': 'docs/frontend-reviews'})

    cfg.update({
        'docroot': doc,
        'drupal': True,
        'localUrl': ddev_url(root),
        'cacheClear': 'ddev drush cr' if has_ddev else 'vendor/bin/drush cr',
        'screenshotNode': next((f'~/{rel(p, Path.home())}' for p in sorted(Path.home().glob('.nvm/versions/node/v2[2-9]*/bin/node'))[-1:]), 'node'),
        'protectedPaths': [f'{pre}core/', 'vendor/', f'{pre}modules/contrib/', f'{pre}themes/contrib/',
                           f'{pre}profiles/contrib/', f'{pre}libraries/', 'node_modules/', f'{pre}sites/default/files/',
                           'patches/'],
        'askPaths': ['sites/default/settings.php', 'sites/default/settings.local.php', 'sites/default/services.yml',
                     'composer.json', 'composer.lock', 'package.json', 'package-lock.json', 'yarn.lock',
                     'gulpfile.js', 'webpack.config.js', 'vite.config.js'],
        'reviewRoots': [f'{pre}themes/custom/', f'{pre}modules/custom/'],
        'reviewGate': 'block',
    })
    return cfg


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    root = Path(args[0] if args else '.').resolve()
    try:
        top = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
        if top.returncode == 0 and not args:
            root = Path(top.stdout.strip())
    except OSError:
        pass
    cfg = detect(root)
    text = json.dumps(cfg, indent=2)
    if '--write' in sys.argv:
        out = root / '.claude' / 'frontend.config.json'
        if out.exists() and '--force' not in sys.argv:
            sys.exit(f'{out} exists; use --force to overwrite (or review the printed config and merge by hand).\n{text}')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + '\n')
        print(f'wrote {out}')
    print(text)


if __name__ == '__main__':
    main()
