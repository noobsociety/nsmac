#!/usr/bin/env bash
# Contract: platform/tooling/topology-validator-contract.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMAND_CONFIG_ROOT="${COMMAND_CONFIG_ROOT:-$ROOT}"
CATALOG="${COMMAND_CONFIG_ROOT}/commands/commands.md"

python3 - "$COMMAND_CONFIG_ROOT" "$CATALOG" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
catalog = Path(sys.argv[2])
commands_dir = root / "commands"
failures: list[str] = []
retired_namespaces = {"doc", "git", "quality"}

if not catalog.exists():
    print(f"ERROR: missing commands catalog: {catalog}", file=sys.stderr)
    sys.exit(1)

if commands_dir.exists():
    for path in sorted(commands_dir.rglob("*")):
        if path.is_dir() and not any(path.iterdir()):
            failures.append(f"empty command directory remains: {path.relative_to(root).as_posix()}")
    for namespace in sorted(retired_namespaces):
        path = commands_dir / namespace
        if path.exists():
            failures.append(f"retired command namespace directory remains: {path.relative_to(root).as_posix()}")

text = catalog.read_text(encoding="utf-8")
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
block_re = re.compile(r"<!-- BEGIN GENERATED:COMMANDS_ROSTER -->(.*?)<!-- END GENERATED:COMMANDS_ROSTER -->", re.S)

namespace_links: set[str] = set()
route_links: set[tuple[str, str]] = set()
backing_catalog_links: list[str] = []

for label, href in link_re.findall(text):
    target = href.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        continue
    parts = Path(unquote(target)).parts
    if len(parts) >= 3 and parts[0] in {"collab", "agent", "doc", "git", "quality", "test"} and parts[1] in {"engine", "reference", "data"}:
        backing_catalog_links.append(target)
    if len(parts) == 2 and parts[1] == "index.md":
        namespace_links.add(parts[0])
    elif len(parts) == 3 and parts[2] == "index.md":
        route_links.add((parts[0], parts[1]))

generated_match = block_re.search(text)
if not generated_match:
    failures.append("commands catalog missing generated roster block")
else:
    for label, href in link_re.findall(generated_match.group(1)):
        target = href.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (catalog.parent / unquote(target)).resolve()
        try:
            rel = candidate.relative_to(root).as_posix()
        except ValueError:
            failures.append(f"generated catalog link escapes repository: {href}")
            continue
        if not candidate.exists():
            failures.append(f"generated catalog link target missing: {rel}")
        parts = Path(unquote(target)).parts
        if len(parts) >= 2 and parts[1] in {"engine", "reference", "data"}:
            failures.append(f"generated catalog links backing file instead of route entry: {target}")

for target in backing_catalog_links:
    failures.append(f"commands catalog links backing file instead of public route entry: {target}")

actual_namespaces = {path.parent.name for path in commands_dir.glob("*/index.md") if path.parent.is_dir()}
actual_routes = {(path.parent.parent.name, path.parent.name) for path in commands_dir.glob("*/*/index.md") if path.parent.parent.is_dir()}

for ns in sorted(actual_namespaces - namespace_links):
    failures.append(f"namespace missing from commands catalog: commands/{ns}/index.md")
for ns in sorted(namespace_links - actual_namespaces):
    failures.append(f"catalog names missing namespace entry point: commands/{ns}/index.md")
for ns, route in sorted(actual_routes - route_links):
    failures.append(f"route missing from commands catalog: commands/{ns}/{route}/index.md")
for ns, route in sorted(route_links - actual_routes):
    failures.append(f"catalog names missing route entry point: commands/{ns}/{route}/index.md")

if failures:
    for item in failures:
        print(f"ERROR: {item}", file=sys.stderr)
    sys.exit(1)

print("audit-topology: OK")
PY
