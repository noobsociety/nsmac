#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


DEFAULT_CONFIG_ROOT = Path(os.environ.get('COMMAND_CONFIG_ROOT', '.')).expanduser()
DEFAULT_ROLES_DIR = DEFAULT_CONFIG_ROOT / '_roles'


def die(message: str) -> None:
    raise SystemExit(message)


def validate_role_data(data: dict, expected_key: str, source: str) -> None:
    if not isinstance(data, dict):
        die(f'{source}: role must be an object')
    if data.get('key') != expected_key:
        die(f'{source}: key must match role name')
    for field in ('displayName',):
        if not isinstance(data.get(field), str) or not data[field].strip():
            die(f'{source}: {field} must be a non-empty string')
    concerns = data.get('concerns')
    if not isinstance(concerns, list) or not concerns:
        die(f'{source}: concerns must be a non-empty array')
    if any(not isinstance(item, str) or not item.strip() for item in concerns):
        die(f'{source}: concerns must contain only non-empty strings')
    prohibitions = data.get('prohibitions')
    if prohibitions is not None:
        if not isinstance(prohibitions, list):
            die(f'{source}: prohibitions must be an array when present')
        if any(not isinstance(item, str) or not item.strip() for item in prohibitions):
            die(f'{source}: prohibitions must contain only non-empty strings')


def load_role(roles_dir: Path, role: str) -> dict:
    path = roles_dir / f'{role}.json'
    if not path.exists():
        die(f'role missing: {path}')
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f'role invalid JSON: {path}: {exc}')
    validate_role_data(data, role, str(path))
    return data


def participant_row(role_data: dict, index: int = 1, agent_id: str = '') -> str:
    concerns = '; '.join(role_data['concerns'])
    return (
        f"| {index} | {role_data['key']} | {role_data['displayName']} | "
        f"{agent_id} | {concerns} |"
    )


def role_catalog(roles_dir: Path) -> list[dict]:
    roles: list[dict] = []
    seen: dict[str, Path] = {}
    for path in sorted(roles_dir.glob('*.json')):
        role = path.stem
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            die(f'role invalid JSON: {path}: {exc}')
        key = data.get('key') if isinstance(data, dict) else None
        if isinstance(key, str) and key in seen:
            die(f'duplicate role key: {key}: {seen[key]} and {path}')
        if isinstance(key, str):
            seen[key] = path
        validate_role_data(data, role, str(path))
        roles.append(data)
    if not roles:
        die(f'roles missing: {roles_dir}')
    return roles


def roles_command(roles_dir: Path) -> int:
    for index, data in enumerate(role_catalog(roles_dir), start=1):
        print(participant_row(data, index))
    return 0


def roster_command(roles_dir: Path) -> int:
    for data in role_catalog(roles_dir):
        print(f"| `{data['key']}` | {data['displayName']} |")
    return 0


def validate_command(roles_dir: Path) -> int:
    role_catalog(roles_dir)
    print('roles OK')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Shared role helper.')
    parser.add_argument('--roles-dir', default=str(DEFAULT_ROLES_DIR))
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('validate')
    subparsers.add_parser('roles')
    subparsers.add_parser('roster')

    row_parser = subparsers.add_parser('row')
    row_parser.add_argument('role')
    row_parser.add_argument('--index', type=int, default=1)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    roles_dir = Path(args.roles_dir)

    if args.command == 'validate':
        return validate_command(roles_dir)
    if args.command == 'roles':
        return roles_command(roles_dir)
    if args.command == 'roster':
        return roster_command(roles_dir)
    if args.command == 'row':
        print(participant_row(load_role(roles_dir, args.role), args.index))
        return 0
    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
