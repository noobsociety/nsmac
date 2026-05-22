#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"
CATALOG="${COMMAND_CONFIG_ROOT}/commands/commands.md"

python3 - "$COMMAND_CONFIG_ROOT" "$CATALOG" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
catalog = Path(sys.argv[2])

if not catalog.exists():
    print(f"ERROR: missing commands catalog: {catalog}", file=sys.stderr)
    sys.exit(1)

text = catalog.read_text()
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
namespace_links: set[str] = set()
command_links: set[tuple[str, str]] = set()

for label, href in link_re.findall(text):
    href = href.split("#", 1)[0]
    parts = Path(href).parts
    if len(parts) == 2 and parts[1] == "index.md":
        namespace_links.add(parts[0])
    elif len(parts) == 3 and parts[2] == "index.md":
        command_links.add((parts[0], parts[1]))

commands_dir = root / "commands"
actual_namespace_entries = {
    path.parent.name
    for path in commands_dir.glob("*/index.md")
    if path.parent.is_dir()
}
actual_command_entries = {
    (path.parent.parent.name, path.parent.name)
    for path in commands_dir.glob("*/*/index.md")
    if path.parent.parent.is_dir()
}

if not actual_namespace_entries and not actual_command_entries:
    print("audit-topology: OK (no restructured command entries)")
    sys.exit(0)

failures = 0

for ns in sorted(namespace_links):
    expected = commands_dir / ns / "index.md"
    if not expected.exists():
        print(f"ERROR: missing namespace entry point: commands/{ns}/index.md", file=sys.stderr)
        failures += 1

for ns, cmd in sorted(command_links):
    expected = commands_dir / ns / cmd / "index.md"
    if not expected.exists():
        print(f"ERROR: missing command entry point: commands/{ns}/{cmd}/index.md", file=sys.stderr)
        failures += 1

for ns in sorted(actual_namespace_entries - namespace_links):
    print(
        f"WARN: orphaned entry point: commands/{ns}/index.md (no catalog entry for namespace {ns})",
        file=sys.stderr,
    )

for ns, cmd in sorted(actual_command_entries - command_links):
    print(
        f"WARN: orphaned entry point: commands/{ns}/{cmd}/index.md (no catalog entry for command {ns}/{cmd})",
        file=sys.stderr,
    )

if failures:
    sys.exit(1)

print("audit-topology: OK")
PY
