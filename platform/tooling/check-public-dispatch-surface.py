#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

LEGACY_LABELS = ("Slash", "Signature", "Prose dispatch")
COMMAND_NAMESPACES = ("agent", "collab", "commands", "doc", "git", "quality", "test")
TRACKED_SWEEP_EXCLUDED_PREFIXES = ("records/",)
SLASH_COMMAND_RE = re.compile(
    r"(?<![\w./~:-])/(" + "|".join(re.escape(ns) for ns in COMMAND_NAMESPACES) + r")(?=$|[\s`.,;:)<])"
)


def public_command_paths(root: Path) -> list[Path]:
    commands_root = root / "commands"
    paths = [commands_root / "commands.md"]
    paths.extend(sorted(commands_root.glob("*/index.md")))
    paths.extend(sorted(commands_root.glob("*/*/index.md")))
    return [path for path in paths if path.exists()]


def expected_h1(root: Path, path: Path, dispatch: str | None = None) -> str:
    rel = path.relative_to(root)
    if rel.as_posix() == "commands/commands.md":
        return "# (commands)"
    parts = rel.parts
    if len(parts) == 3 and parts[0] == "commands" and parts[2] == "index.md":
        return f"# ({parts[1]})"
    if len(parts) == 4 and parts[0] == "commands" and parts[3] == "index.md":
        if dispatch and dispatch.startswith("(") and dispatch.endswith(")"):
            tokens: list[str] = []
            for token in dispatch[1:-1].split():
                if token.startswith(("<", "[", "--")) or "<" in token:
                    break
                tokens.append(token)
            if tokens:
                return f"# ({' '.join(tokens)})"
        return f"# ({parts[1]} {parts[2].replace('-', ' ')})"
    return "# (<namespace route>)"


def tracked_paths(root: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode == 0:
        paths = [root / line for line in proc.stdout.splitlines() if line.strip()]
    else:
        paths = [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]
    return [path for path in paths if path.exists()]


def tracked_sweep_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in tracked_paths(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(TRACKED_SWEEP_EXCLUDED_PREFIXES):
            continue
        paths.append(path)
    return paths


def code_spans(line: str) -> list[str]:
    return re.findall(r"`([^`]+)`", line)


def route_arg_dispatches(text: str) -> list[tuple[int, str]]:
    dispatches: list[tuple[int, str]] = []
    in_block = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not in_block and stripped == "```route-arg":
            in_block = True
            continue
        if in_block and stripped == "```":
            in_block = False
            continue
        if in_block and stripped.startswith("dispatch:"):
            dispatches.append((number, stripped.split(":", 1)[1].strip()))
    return dispatches


def check_path(root: Path, path: Path) -> list[str]:
    failures: list[str] = []
    rel = path.relative_to(root)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for number, line in enumerate(lines, start=1):
        for label in LEGACY_LABELS:
            if line.startswith(f"**{label}:**"):
                failures.append(f"{rel}:{number}: legacy public label is forbidden: {label}")

    dispatch_lines = [
        (number, line)
        for number, line in enumerate(lines, start=1)
        if line.startswith("**Dispatch:**")
    ]
    if len(dispatch_lines) != 1:
        failures.append(f"{rel}: expected exactly one **Dispatch:** line, found {len(dispatch_lines)}")
        return failures

    number, line = dispatch_lines[0]
    spans = code_spans(line)
    if len(spans) != 1:
        failures.append(f"{rel}:{number}: Dispatch line must include exactly one code span")
        return failures

    dispatch = spans[0]
    expected = expected_h1(root, path, dispatch)
    actual = lines[0].strip() if lines else ""
    if actual != expected:
        failures.append(f"{rel}: H1 must be `{expected}`, found `{actual}`")

    if not (dispatch.startswith("(") and dispatch.endswith(")")):
        failures.append(f"{rel}:{number}: Dispatch must use routed form `(namespace route ...)`: {dispatch}")
    elif dispatch.startswith("(/"):
        failures.append(f"{rel}:{number}: Dispatch must not expose slash form: {dispatch}")

    route_dispatches = route_arg_dispatches(text)
    if len(route_dispatches) > 1:
        failures.append(f"{rel}: expected at most one route-arg dispatch line, found {len(route_dispatches)}")
    if route_dispatches and route_dispatches[0][1] != dispatch:
        failures.append(
            f"{rel}: Dispatch `{dispatch}` disagrees with route-arg dispatch `{route_dispatches[0][1]}`"
        )
    return failures


def check_tracked_slash_surface(root: Path) -> list[str]:
    failures: list[str] = []
    for path in tracked_sweep_paths(root):
        rel = path.relative_to(root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            if SLASH_COMMAND_RE.search(line):
                failures.append(f"{rel}:{number}: tracked slash command invocation is forbidden")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repository root to scan")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures: list[str] = []
    for path in public_command_paths(root):
        failures.extend(check_path(root, path))
    failures.extend(check_tracked_slash_surface(root))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: command dispatch surface uses routed forms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
