#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit): keep Claude out of files it must not touch.

- deny: core, contrib, vendor, node_modules ... (frontend.config.json protectedPaths)
- deny: compiled CSS/JS (and source maps) when the source exists -> edit the source instead
- ask:  settings.php, services.yml, package.json, gulpfile.js ... (askPaths)
"""
from _common import emit, load_config, project_dir, read_input, rel_path, skill_scripts

skill_scripts()
from fe_common import compiled_source  # noqa: E402

data = read_input()
root = project_dir(data)
cfg = load_config(root)
rel = rel_path(root, (data.get('tool_input') or {}).get('file_path'))
if rel is None:
    raise SystemExit(0)


def decide(decision, reason):
    emit({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': decision,
        'permissionDecisionReason': reason,
    }})


for prefix in cfg.get('protectedPaths', []):
    if rel.startswith(prefix) or f'/{prefix}' in f'/{rel}':
        decide('deny', f'[frontend guard] {rel} is under {prefix}, which is not project code. '
                       'Override it from the custom theme/module (template override, library-override, patch) instead.')

if rel.endswith('.map'):
    decide('deny', f'[frontend guard] {rel} is a generated source map. Never edit it by hand.')
source = compiled_source(rel, cfg, root)
if source:
    decide('deny', f'[frontend guard] {rel} is compiled output. Edit {source} instead, '
                   'then run the build to regenerate it.')

for path in cfg.get('askPaths', []):
    if rel == path or rel.endswith('/' + path):
        decide('ask', f'[frontend guard] {rel} is a sensitive project file. Confirm this edit.')
