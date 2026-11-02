#!/usr/bin/env python3
"""Render the merged findings JSON into the Markdown review report (same name, .md).

Usage: render_report.py <report.json>

JSON shape (written by the /frontend skill after merging the reviewer agents):
{
  "title": "strategic-cards", "date": "2026-11-02", "mode": "component|review|audit|build",
  "stack": "drupal-legacy (hq)", "branch": "…", "url": null, "figma": null,
  "files": ["themes/…"], "lighthouse": {"performance": 72, "accessibility": 95, "bestPractices": 100, "seo": 92} | null,
  "findings": [{"severity": "critical|major|minor", "area": "a11y|perf|standards|visual",
                "ref": "1.4.3 | LCP | rule-id", "file": "…", "line": 12, "issue": "…", "fix": "…",
                "autoFixable": true, "sources": ["a11y", "standards"]}],
  "decisions": ["… (refer to file:line, not #numbers; findings are renumbered)"], "notes": ["…"]
}
"""
import json
import sys
from pathlib import Path

SEV = ['critical', 'major', 'minor']
AREAS = [('a11y', 'Accessibility'), ('perf', 'Performance'), ('standards', 'Standards & best practice'),
         ('visual', 'Visual QA')]


def cell(s):
    return str(s if s is not None else '').replace('|', '\\|').replace('\n', ' ')


def main():
    src = Path(sys.argv[1])
    d = json.loads(src.read_text())
    findings = sorted(d.get('findings', []), key=lambda f: (SEV.index(f.get('severity', 'minor')),
                                                            f.get('file', ''), f.get('line') or 0))
    for i, f in enumerate(findings, 1):
        f['id'] = i
    count = lambda area, sev: sum(1 for f in findings if f.get('area') == area and f.get('severity') == sev)
    crit = sum(1 for f in findings if f['severity'] == 'critical')
    major = sum(1 for f in findings if f['severity'] == 'major')
    verdict = 'fix critical issues first' if crit else ('ready after the major fixes' if major else 'ready to merge')

    out = [f"# Frontend review: {d.get('title', '')}", '',
           f"- **Date**: {d.get('date', '')}   **Mode**: {d.get('mode', '')}   **Stack**: {d.get('stack', '')}   **Branch**: {d.get('branch', '')}",
           f"- **Scope**: {len(d.get('files', []))} files" + (f" · URL {d['url']}" if d.get('url') else '')
           + (f" · Figma {d['figma']}" if d.get('figma') else '')]
    lh = d.get('lighthouse')
    if lh:
        out.append(f"- **Lighthouse (mobile)**: Perf {lh.get('performance')} · A11y {lh.get('accessibility')} · "
                   f"BP {lh.get('bestPractices')} · SEO {lh.get('seo')}")
    out += ['', '## Summary', '| Area | Critical | Major | Minor |', '|---|---|---|---|']
    for key, label in AREAS:
        if key == 'visual' and not any(f.get('area') == 'visual' for f in findings):
            continue
        out.append(f"| {label} | {count(key, 'critical')} | {count(key, 'major')} | {count(key, 'minor')} |")
    auto = sum(1 for f in findings if f.get('autoFixable'))
    out += ['', f"**Verdict**: {verdict}. {len(findings)} findings, {auto} auto-fixable (`/frontend fix`).", '',
            '## Findings', '| # | Sev | Area | File:line | Issue | Fix | Auto |', '|---|---|---|---|---|---|---|']
    for f in findings:
        loc = f"`{f.get('file', '')}{':' + str(f['line']) if f.get('line') else ''}`"
        area = f.get('area', '') + (f" ({f['ref']})" if f.get('ref') else '')
        out.append(f"| {f['id']} | {f['severity']} | {cell(area)} | {loc} | {cell(f.get('issue'))} | "
                   f"{cell(f.get('fix'))} | {'yes' if f.get('autoFixable') else 'no'} |")
    if d.get('decisions'):
        out += ['', '## Needs a decision'] + [f'- {x}' for x in d['decisions']]
    if d.get('notes'):
        out += ['', '## Notes'] + [f'- {x}' for x in d['notes']]
    out += ['', '## Files reviewed'] + [f'- `{x}`' for x in d.get('files', [])]

    md = src.with_suffix('.md')
    md.write_text('\n'.join(out) + '\n')
    src.write_text(json.dumps({**d, 'findings': findings}, indent=2))
    print(md)


if __name__ == '__main__':
    main()
