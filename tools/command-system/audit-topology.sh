#!/usr/bin/env bash
# Contract: tools/command-system/topology-validator-contract.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"
CATALOG="${COMMAND_CONFIG_ROOT}/commands/commands.md"
MODE="post-migration"

usage() {
  cat <<'USAGE'
Usage: ./tools/command-system/audit-topology.sh [--migration]

Options:
  --migration  Accept flat commands/<ns>.md and directory commands/<ns>/index.md namespace entries.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --migration)
      MODE="migration"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "audit-topology: unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

python3 - "$COMMAND_CONFIG_ROOT" "$CATALOG" "$MODE" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
catalog = Path(sys.argv[2])
mode = sys.argv[3]

if not catalog.exists():
    print(f"ERROR: missing commands catalog: {catalog}", file=sys.stderr)
    sys.exit(1)

text = catalog.read_text()
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
block_re = re.compile(
    r"<!-- BEGIN GENERATED:COMMANDS_ROSTER -->(.*?)<!-- END GENERATED:COMMANDS_ROSTER -->",
    re.S,
)
namespace_links: set[str] = set()
command_links: set[tuple[str, str]] = set()

for label, href in link_re.findall(text):
    href = href.split("#", 1)[0]
    parts = Path(href).parts
    if mode == "migration" and len(parts) == 1 and href.endswith(".md") and href not in {"commands.md", "index.md"}:
        namespace_links.add(Path(href).stem)
    elif len(parts) == 2 and parts[1] == "index.md":
        namespace_links.add(parts[0])
    elif len(parts) == 3 and parts[2] == "index.md":
        command_links.add((parts[0], parts[1]))

commands_dir = root / "commands"
actual_namespace_entries = {
    path.parent.name
    for path in commands_dir.glob("*/index.md")
    if path.parent.is_dir()
}
if mode == "migration":
    actual_namespace_entries.update(
        path.stem
        for path in commands_dir.glob("*.md")
        if path.name not in {"commands.md", "index.md"}
    )
actual_command_entries = {
    (path.parent.parent.name, path.parent.name)
    for path in commands_dir.glob("*/*/index.md")
    if path.parent.parent.is_dir()
}

if not actual_namespace_entries and not actual_command_entries:
    print("audit-topology: OK (no restructured command entries)")
    sys.exit(0)

failures = 0
generated_match = block_re.search(text)
if generated_match:
    for label, href in link_re.findall(generated_match.group(1)):
        target = href.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (catalog.parent / unquote(target)).resolve()
        try:
            rel = candidate.relative_to(root).as_posix()
        except ValueError:
            print(f"ERROR: generated catalog link escapes repository: {href}", file=sys.stderr)
            failures += 1
            continue
        if not candidate.exists():
            print(f"ERROR: generated catalog link target missing: {rel}", file=sys.stderr)
            failures += 1

for ns in sorted(namespace_links):
    expected = commands_dir / ns / "index.md"
    flat = commands_dir / f"{ns}.md"
    if mode == "migration" and flat.exists():
        continue
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
