#!/usr/bin/env bash
set -euo pipefail

ROOT="${COMMAND_CONFIG_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
constants_path = root / "commands/collab/engine/registry_constants.py"
glossary_path = root / "commands/collab/reference/glossary.md"
verification_path = root / "commands/collab/reference/verification.md"
phase_path = root / "commands/collab/reference/phase-admissibility.md"

failures: list[str] = []


def read(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        failures.append(f"missing vocabulary source: {path.relative_to(root)}")
        return ""


constants_text = read(constants_path)
glossary_text = read(glossary_path)
verification_text = read(verification_path)
phase_text = read(phase_path)

values: dict[str, object] = {}
if constants_text:
    tree = ast.parse(constants_text, filename=str(constants_path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                try:
                    values[target.id] = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    pass


def as_tokens(name: str) -> list[str]:
    value = values.get(name)
    if not isinstance(value, (list, set, tuple)):
        failures.append(f"missing constant set: {name}")
        return []
    return sorted(str(item) for item in value)


def require_tokens(name: str, text: str, rel: str) -> None:
    for token in as_tokens(name):
        if not re.search(rf"(?<![A-Za-z0-9_-]){re.escape(token)}(?![A-Za-z0-9_-])", text):
            failures.append(f"{rel}: missing `{token}` from {name}")


require_tokens("PHASES", phase_text, "commands/collab/reference/phase-admissibility.md")
require_tokens("ALLOWED_COMPLETION_SUBSTATES", verification_text, "commands/collab/reference/verification.md")
require_tokens("ALLOWED_VERIFICATION_SUBSTATES", verification_text, "commands/collab/reference/verification.md")
require_tokens("ALLOWED_PARTICIPANT_VERIFICATION_STAGES", verification_text, "commands/collab/reference/verification.md")
require_tokens("ALLOWED_VERDICT_OUTCOMES", verification_text, "commands/collab/reference/verification.md")
require_tokens("ALLOWED_VERDICT_RESTORE_TARGETS", verification_text, "commands/collab/reference/verification.md")


def heading_anchors(text: str) -> set[str]:
    # GitHub-style slugger for ATX headings: strip the optional closing-hash run,
    # lowercase, drop punctuation (keeping word chars incl. Unicode and underscore,
    # spaces, hyphens), spaces -> hyphens, and disambiguate duplicates with -N.
    # Setext headings are intentionally unsupported: the only doc this gate validates
    # (verification.md) is ATX-only, and a setext ref would fail loud, never silent-pass.
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(r"#{1,6}\s+(.+)", line)
        if not match:
            continue
        heading = re.sub(r"\s+#+\s*$", "", match.group(1).strip())
        slug = re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
        if not slug:
            continue
        if slug in counts:
            counts[slug] += 1
            anchors.add(f"{slug}-{counts[slug]}")
        else:
            counts[slug] = 0
            anchors.add(slug)
    return anchors


# F-MSG parity: the operator-guidance prose lives in verification.md; seal_verification.py
# emits only terse runtime pointers into it. Assert every verification.md#<anchor> referenced
# from the engine resolves to a real heading so the pointer can never silently dangle.
seal_text = read(root / "commands/collab/engine/seal_verification.py")
verification_anchors = heading_anchors(verification_text)
for anchor in sorted(set(re.findall(r"verification\.md#([\w-]+)", seal_text))):
    if anchor not in verification_anchors:
        failures.append(
            f"commands/collab/engine/seal_verification.py: dangling ref "
            f"`verification.md#{anchor}` (no matching heading in verification.md)"
        )

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    sys.exit(1)

print("OK: collab vocabulary mirrors registry constants")
PY
