#!/usr/bin/env python3
"""Ubicación del CLI de OpenCode. Busca en npm global y desktop app."""
import os


def find_opencode_cli():
    """Busca opencode CLI en las ubicaciones conocidas."""
    candidates = [
        os.path.join(os.environ.get("APPDATA", ""), "npm", "opencode.cmd"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


OPENCODE_CLI = find_opencode_cli()
