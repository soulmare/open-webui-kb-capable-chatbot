#!/usr/bin/env python3
"""Sync the local KB directory to the Open WebUI knowledge base via oikb.

Reads OIKB_BIN, KB_PATH, and KB_ID from a .env file in the repo root
(see .env.template) instead of hardcoding them.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='show changes without applying them')
    parser.add_argument('--watch', action='store_true', help='watch the directory and sync on changes')
    args = parser.parse_args()

    env = {**load_env_file(REPO_ROOT / '.env'), **os.environ}

    oikb_bin = os.path.expanduser(env.get('OIKB_BIN', '~/.venvs/oikb/bin/oikb'))
    kb_path = env.get('KB_PATH')
    kb_id = env.get('KB_ID')

    missing = [name for name, value in [('KB_PATH', kb_path), ('KB_ID', kb_id)] if not value]
    if missing:
        sys.exit(f'Missing required .env values: {", ".join(missing)} (see .env.template)')

    command = 'watch' if args.watch else 'sync'
    cmd = [oikb_bin, command, kb_path, '--kb-id', kb_id]
    if args.dry_run:
        cmd.append('--dry-run')

    sys.exit(subprocess.call(cmd))


if __name__ == '__main__':
    main()
