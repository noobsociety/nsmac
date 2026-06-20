#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'commands/collab/engine/registry.py'


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def migrate_records_dir(records_dir: Path) -> dict:
    migrated_raw: list[str] = []
    removed_artifacts: list[str] = []

    for raw_path in sorted(records_dir.glob('*-raw.md')):
        canonical = raw_path.with_name(f'{raw_path.name[:-7]}.md')
        canonical.write_bytes(raw_path.read_bytes())
        raw_path.unlink()
        migrated_raw.append(str(raw_path))

    for artifact in sorted(records_dir.glob('*-synthesis.json')):
        remove_path(artifact)
        removed_artifacts.append(str(artifact))
    for artifact in sorted(records_dir.glob('*-synthesis')):
        remove_path(artifact)
        removed_artifacts.append(str(artifact))

    return {
        'migratedRaw': migrated_raw,
        'removedArtifacts': removed_artifacts,
    }


def refresh_summaries(registry_path: Path) -> list[str]:
    data = json.loads(registry_path.read_text())
    refreshed: list[str] = []
    for entry in data.get('collabs', []):
        target = entry.get('id')
        if not isinstance(target, str) or not target:
            continue
        if entry.get('status') == 'archived':
            continue
        subprocess.run(
            [
                sys.executable,
                str(REGISTRY),
                '--registry',
                str(registry_path),
                'summarize',
                target,
            ],
            cwd=registry_path.parent,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        refreshed.append(target)
    return refreshed


def migrate_state_root(state_root: Path) -> dict:
    registries = sorted(state_root.glob('*/registry.json'))
    result = {
        'stateRoot': str(state_root),
        'registries': [],
    }
    for registry_path in registries:
        records_dir = registry_path.parent / 'records'
        record_result = {'registry': str(registry_path)}
        if records_dir.is_dir():
            record_result.update(migrate_records_dir(records_dir))
        else:
            record_result.update({'migratedRaw': [], 'removedArtifacts': []})
        record_result['refreshedSummaries'] = refresh_summaries(registry_path)
        result['registries'].append(record_result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Migrate collab records to single canonical transcript files.'
    )
    parser.add_argument(
        '--state-root',
        default=str(Path.home() / '.collabs'),
        help='user-scope collab state root containing */registry.json entries',
    )
    args = parser.parse_args()

    result = migrate_state_root(Path(args.state_root).expanduser())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
