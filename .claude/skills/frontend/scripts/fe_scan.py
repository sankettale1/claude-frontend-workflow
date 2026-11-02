#!/usr/bin/env python3
"""Fast static frontend checks: accessibility, performance, standards, Drupal.

Usage:
  fe_scan.py [--all-lines | --base REF|auto] [--json] [--min-severity info|warn|error] FILE...

By default only lines added since git HEAD are reported, so legacy debt does
not drown out what you just wrote. --base auto compares with the branch's
merge base instead (whole-branch review). Untracked files are scanned in full.
Pass --all-lines to audit whole files.

Exit code: 1 if any "error" finding is reported, else 0.
"""
import argparse
import functools
import json
import re
import subprocess
import sys
from pathlib import Path

MARKUP = ('.twig', '.html', '.htm', '.vue', '.jsx', '.tsx', '.svelte', '.astro')
STYLE = ('.scss', '.sass', '.css', '.less')
SCRIPT = ('.js', '.mjs', '.cjs', '.ts', '.jsx', '.tsx', '.vue', '.svelte')
PHP = ('.php', '.theme', '.module', '.inc')
TWIG = ('.twig',)
YAML = ('.yml', '.yaml')

SEVERITY_RANK = {'info': 0, 'warn': 1, 'error': 2}

# Tags that spread attributes in (Drupal attributes, JSX spread) can't be judged statically.
SPREAD = r'(?![^>]*(\{\{\s*[\w.]*attributes|\{\s*\.\.\.))'

# (id, severity, category, extensions, pattern, flags, message)
RULES = [
    # Accessibility
    ('img-alt', 'error', 'a11y', MARKUP,
     r'<img\b' + SPREAD + r'(?![^>]*\balt\s*=)[^>]*>', re.I,
     '<img> has no alt attribute. Use meaningful alt text, or alt="" if decorative.'),
    ('iframe-title', 'error', 'a11y', MARKUP,
     r'<iframe\b' + SPREAD + r'(?![^>]*\btitle\s*=)[^>]*>', re.I,
     '<iframe> has no title attribute.'),
    ('positive-tabindex', 'error', 'a11y', MARKUP,
     r'tabindex\s*=\s*["\'{]?\s*[1-9]', re.I,
     'Positive tabindex breaks natural focus order. Use 0 or -1.'),
    ('click-non-interactive', 'error', 'a11y', MARKUP,
     r'<(div|span|li|p)\b[^>]*\s(onclick|onClick|@click|v-on:click)\s*=', 0,
     'Click handler on a non-interactive element. Use <button>, or add role, tabindex="0" and key handling.'),
    ('href-hash', 'warn', 'a11y', MARKUP,
     r'<a\b[^>]*\bhref\s*=\s*["\']#["\']', re.I,
     'href="#" link. If it triggers an action, it should be a <button>.'),
    ('zoom-lock', 'error', 'a11y', MARKUP,
     r'user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b', re.I,
     'Viewport blocks zoom (WCAG 1.4.4).'),
    ('outline-none', 'warn', 'a11y', STYLE,
     r'outline\s*:\s*(none|0)\b', re.I,
     'Focus outline removed. Make sure a visible :focus-visible style replaces it.'),
    ('autoplay-unmuted', 'warn', 'a11y', MARKUP,
     r'<video\b(?=[^>]*\bautoplay)(?![^>]*\bmuted)[^>]*>', re.I,
     'Autoplaying video without muted. Also provide a pause control (WCAG 2.2.2).'),

    # Performance
    ('img-dimensions', 'info', 'perf', MARKUP,
     r'<img\b' + SPREAD + r'(?![^>]*\b(width|height)\s*=)[^>]*>', re.I,
     '<img> without width/height can cause layout shift (CLS). Prefer Drupal image styles / responsive_image.'),
    ('sync-script', 'warn', 'perf', MARKUP,
     r'<script\b(?=[^>]*\bsrc\s*=)(?![^>]*\b(defer|async|type\s*=\s*["\']module))[^>]*>', re.I,
     'Render-blocking <script src>. Add defer/async, or attach it through a library.'),
    ('remote-css-import', 'warn', 'perf', STYLE,
     r'@import\s+(url\()?\s*["\']?https?:', re.I,
     'Remote @import is render-blocking. Load fonts/CSS via a library or <link rel="preload">.'),
    ('document-write', 'error', 'perf', SCRIPT + MARKUP,
     r'\bdocument\.write\s*\(', 0,
     'document.write blocks parsing.'),

    # Standards / best practice
    ('console-log', 'warn', 'standards', SCRIPT,
     r'\bconsole\.(log|debug)\s*\(', 0,
     'Leftover console.log/debug.'),
    ('debugger', 'error', 'standards', SCRIPT,
     r'^\s*debugger\s*;', re.M,
     'Leftover debugger statement.'),
    ('jquery-once', 'error', 'drupal', SCRIPT + YAML,
     r'\.once\(\s*["\']|core/jquery\.once', 0,
     'jQuery.once is removed in Drupal 10. Use core/once: once("id", selector, context).'),
    ('debug-dump', 'error', 'standards', PHP + TWIG,
     r'\b(var_dump|dpm|dsm|kint|ksm|dump)\s*\(', 0,
     'Debug dump left in code.'),
    ('twig-raw', 'warn', 'security', TWIG,
     r'\|\s*raw\b', 0,
     '|raw bypasses autoescaping (XSS risk). Render arrays and Markup objects are already safe.'),
    ('target-blank', 'warn', 'security', MARKUP,
     r'<a\b(?=[^>]*target\s*=\s*["\']_blank)(?![^>]*\brel\s*=)[^>]*>', re.I,
     'target="_blank" without rel="noopener". Also tell users it opens a new tab.'),
    ('important', 'warn', 'standards', STYLE,
     r'!important', 0,
     '!important. Raise specificity through the component root class instead.'),
    ('id-selector', 'warn', 'standards', STYLE,
     r'^(?![^\n]*(#\{|[(\'"]))[^;\n]*#[A-Za-z_][\w-]*[^;\n]*[{,]\s*$', re.M,
     'ID selector in CSS. Use a class (keeps specificity low and reusable).'),
    ('hardcoded-color', 'warn', 'tokens', ('.scss', '.sass', '.less'),
     r'^(?!\s*(\$|--|//))[^\n]*:\s*[^;\n]*#[0-9a-fA-F]{3,8}\b', re.M,
     'Hard-coded colour. Use a theme token ($variable or var(--token)).'),
]


@functools.lru_cache(maxsize=None)
def _git_root_of(directory):
    try:
        out = subprocess.run(['git', '-C', directory, 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, timeout=10)
        return Path(out.stdout.strip()) if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def git_root(path):
    return _git_root_of(str(path.resolve().parent))


@functools.lru_cache(maxsize=None)
def resolve_base(root, base):
    if base != 'auto':
        return base
    for ref in ('origin/main', 'origin/master', 'origin/develop', 'main', 'master', 'develop'):
        ok = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '-q', ref], capture_output=True)
        if ok.returncode == 0:
            mb = subprocess.run(['git', '-C', str(root), 'merge-base', 'HEAD', ref], capture_output=True, text=True)
            if mb.returncode == 0:
                return mb.stdout.strip()
    return 'HEAD'


def added_lines(path, base='HEAD'):
    """Line numbers added since base, or None meaning 'whole file'."""
    root = git_root(path)
    if root is None:
        return None
    rel = str(path.resolve().relative_to(root))
    tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--error-unmatch', rel],
                             capture_output=True, text=True)
    if tracked.returncode != 0:
        return None
    diff = subprocess.run(['git', '-C', str(root), 'diff', '-U0', resolve_base(root, base), '--', rel],
                          capture_output=True, text=True).stdout
    lines = set()
    for m in re.finditer(r'^@@ -\S+ \+(\d+)(?:,(\d+))? @@', diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


def line_of(text, offset):
    return text.count('\n', 0, offset) + 1


def find_theme_libraries(path):
    """Return (theme_name, set_of_library_keys) for the nearest Drupal theme/module."""
    for parent in path.resolve().parents:
        infos = list(parent.glob('*.info.yml'))
        if infos:
            name = infos[0].name[:-len('.info.yml')]
            lib = parent / f'{name}.libraries.yml'
            keys = set()
            if lib.exists():
                keys = set(re.findall(r'^([\w.-]+):\s*$', lib.read_text(errors='ignore'), re.M))
            return name, keys
        if (parent / '.git').exists():
            break
    return None, set()


def drupal_checks(path, text):
    findings = []
    if path.suffix == '.twig':
        theme, keys = find_theme_libraries(path)
        if theme:
            for m in re.finditer(r'attach_library\(\s*["\']([\w.-]+)/([\w.-]+)["\']', text):
                if m.group(1) == theme and m.group(2) not in keys:
                    findings.append(('library-missing', 'error', 'drupal', m.start(),
                                     f'attach_library("{theme}/{m.group(2)}") is not defined in {theme}.libraries.yml.'))
    if path.name.endswith('.libraries.yml'):
        for m in re.finditer(r'^\s+([\w./-]+\.(css|js)):', text, re.M):
            asset = m.group(1)
            if asset.startswith(('http', '//', '/')):
                continue
            if not (path.parent / asset).exists():
                findings.append(('asset-missing', 'error', 'drupal', m.start(),
                                 f'{asset} does not exist. If it is compiled output, run the theme build.'))
    return findings


def scan(path, all_lines, base='HEAD'):
    try:
        text = path.read_text(errors='ignore')
    except OSError:
        return []
    ext = path.suffix.lower()
    if path.name.endswith('.html.twig'):
        ext = '.twig'
    raw = []
    for rid, sev, cat, exts, pattern, flags, msg in RULES:
        if ext not in exts:
            continue
        for m in re.finditer(pattern, text, flags):
            raw.append((rid, sev, cat, m.start(), m.end(), msg))
    for rid, sev, cat, start, msg in drupal_checks(path, text):
        raw.append((rid, sev, cat, start, start, msg))

    wanted = None if all_lines else added_lines(path, base)
    out = []
    for rid, sev, cat, start, end, msg in raw:
        first, last = line_of(text, start), line_of(text, max(start, end - 1))
        if wanted is not None and not wanted.intersection(range(first, last + 1)):
            continue
        out.append({'file': str(path), 'line': first, 'rule': rid, 'severity': sev,
                    'category': cat, 'message': msg})
    return sorted(out, key=lambda f: f['line'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--all-lines', action='store_true')
    ap.add_argument('--base', default='HEAD', help="git ref to diff against, or 'auto' for the branch merge base")
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--min-severity', default='info', choices=SEVERITY_RANK)
    args = ap.parse_args()

    findings = []
    for f in args.files:
        p = Path(f)
        if p.is_file():
            findings.extend(scan(p, args.all_lines, args.base))
    findings = [f for f in findings if SEVERITY_RANK[f['severity']] >= SEVERITY_RANK[args.min_severity]]

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}  {f['severity'].upper():5}  [{f['category']}/{f['rule']}] {f['message']}")
        if not findings:
            print('fe_scan: no findings')
    sys.exit(1 if any(f['severity'] == 'error' for f in findings) else 0)


if __name__ == '__main__':
    main()
