"""Shared helpers for the frontend workflow hooks."""
import json
import os
import sys
from pathlib import Path


def read_input():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def project_dir(data=None):
    return Path(os.environ.get('CLAUDE_PROJECT_DIR') or (data or {}).get('cwd') or os.getcwd())


def load_config(root):
    try:
        return json.loads((root / '.claude' / 'frontend.config.json').read_text())
    except (OSError, ValueError):
        return {}


def rel_path(root, file_path):
    """Project-relative POSIX path, or None if the file is outside the project."""
    if not file_path:
        return None
    p = Path(file_path)
    if not p.is_absolute():
        p = root / p
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def state_file(root, session_id):
    d = root / '.claude' / 'state'
    d.mkdir(parents=True, exist_ok=True)
    return d / f'frontend-{session_id or "default"}.json'


def load_state(root, session_id):
    try:
        return json.loads(state_file(root, session_id).read_text())
    except (OSError, ValueError):
        return {'pending': [], 'lastBlock': ''}


def save_state(root, session_id, state):
    state_file(root, session_id).write_text(json.dumps(state, indent=2))


def emit(obj):
    print(json.dumps(obj))
    sys.exit(0)
