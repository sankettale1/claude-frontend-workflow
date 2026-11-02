#!/usr/bin/env python3
"""Notification: desktop popup when Claude is waiting on you (permission, idle)."""
import subprocess

from _common import read_input

msg = read_input().get('message') or 'Claude Code needs your attention'
subprocess.run(['notify-send', '-a', 'Claude Code', 'Claude Code', msg], capture_output=True)
