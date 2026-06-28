#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Route:
    label: str
    slug: str
    path: Path
    dispatch: str


def first_dispatch(text: str) -> str | None:
    match = re.search(r"^\*\*Dispatch:\*\*\s*`([^`]+)`", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def route_label_from_dispatch(slug: str, dispatch: str) -> str:
    slug_words = slug.replace("-", " ")
    if not (dispatch.startswith("(") and dispatch.endswith(")")):
        return slug_words
    tokens = dispatch[1:-1].split()
    candidate_tokens: list[str] = []
    for token in tokens[1:]:
        if token.startswith(("<", "[", "--")) or "<" in token:
            break
        candidate_tokens.append(token)
    candidate = " ".join(candidate_tokens).strip()
    if candidate == slug or candidate == slug_words:
        return candidate
    if candidate.startswith(slug_words + " "):
        return slug_words
    return candidate or slug_words


def load_routes(root: Path) -> list[Route]:
    routes: list[Route] = []
    for path in sorted((root / "commands/collab").glob("*/index.md")):
        text = path.read_text(encoding="utf-8")
        dispatch = first_dispatch(text)
        if not dispatch or "reference only" in dispatch:
            continue
        slug = path.parent.name
        routes.append(Route(route_label_from_dispatch(slug, dispatch), slug, path, dispatch))
    return routes


def registry_subcommands(root: Path) -> set[str]:
    registry = root / "commands/collab/engine/registry.py"
    if not registry.exists():
        return set()
    result = subprocess.run(
        [sys.executable, str(registry), "--help"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    match = re.search(r"\{([^}]+)\}", result.stdout)
    if not match:
        return set()
    return {item.strip() for item in match.group(1).split(",") if item.strip()}


def helper_calls(path: Path) -> list[tuple[int, str]]:
    calls: list[tuple[int, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for match in re.finditer(r"commands/collab/engine/registry\.py\s+([A-Za-z0-9_-]+)", line):
            calls.append((number, match.group(1)))
    return calls


def router_routes(root: Path) -> tuple[set[str], set[str], list[str]]:
    path = root / "commands/collab/index.md"
    if not path.exists():
        return set(), set(), ["commands/collab/index.md missing"]
    text = path.read_text(encoding="utf-8")
    dispatch = first_dispatch(text) or ""
    dispatch_routes: set[str] = set()
    match = re.search(r"\(collab\s+<([^>]+)>\)", dispatch)
    if match:
        dispatch_routes = {item.strip() for item in match.group(1).split("|") if item.strip()}
    route_entries = {
        match.group(1).strip()
        for match in re.finditer(r"`([^`]+)`\s*->\s*\[[^\]]+\]\(([^)]+/index\.md)\)", text)
    }
    failures: list[str] = []
    if not dispatch_routes:
        failures.append("commands/collab/index.md: Dispatch route roster missing")
    if not route_entries:
        failures.append("commands/collab/index.md: Notes route roster missing")
    return dispatch_routes, route_entries, failures


def generated_routes(root: Path) -> set[str]:
    path = root / "generated/command-reference.md"
    if not path.exists():
        return set()
    routes: set[str] = set()
    in_collab = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_collab = line.strip() == "## collab"
            continue
        if in_collab and line.startswith("### "):
            routes.add(line.removeprefix("### ").strip())
    return routes


def check(root: Path) -> list[str]:
    failures: list[str] = []
    routes = load_routes(root)
    leaf_labels = {route.label for route in routes}

    subcommands = registry_subcommands(root)
    for route in routes:
        for line, subcommand in helper_calls(route.path):
            if subcommand not in subcommands:
                failures.append(
                    f"{route.path.relative_to(root)}:{line}: registry subcommand missing: {subcommand}"
                )

    dispatch_routes, route_entries, router_failures = router_routes(root)
    failures.extend(router_failures)
    for label in sorted(leaf_labels - dispatch_routes):
        failures.append(f"commands/collab/index.md: Dispatch missing route `{label}`")
    for label in sorted(dispatch_routes - leaf_labels):
        failures.append(f"commands/collab/index.md: Dispatch names missing leaf route `{label}`")
    for label in sorted(leaf_labels - route_entries):
        failures.append(f"commands/collab/index.md: Route roster missing `{label}`")
    for label in sorted(route_entries - leaf_labels):
        failures.append(f"commands/collab/index.md: Route roster names missing leaf route `{label}`")

    generated = generated_routes(root)
    for label in sorted(leaf_labels - generated):
        failures.append(f"generated/command-reference.md: missing collab route `{label}`")
    for label in sorted(generated - leaf_labels):
        failures.append(f"generated/command-reference.md: names missing collab leaf route `{label}`")

    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit collab route helper wiring and public route parity.")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = check(root)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: collab route wiring and public route parity pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
