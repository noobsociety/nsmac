#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import importlib.util
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = Path(os.environ.get("COMMAND_CONFIG_ROOT", ROOT)).expanduser().resolve()
COMMANDS_DIR = CONFIG_ROOT / "commands"
ARTIFACT = CONFIG_ROOT / "generated" / "command-reference.md"
BEGIN_MARKER = "<!-- BEGIN GENERATED:COMMAND_REFERENCE -->"
END_MARKER = "<!-- END GENERATED:COMMAND_REFERENCE -->"
ROLE_SOURCE = "platform/tooling/roles.py roles"
ROLE_DYNAMIC_DETAIL = "role keys from commands/collab/reference/roles/"
VALID_CLASSES = {"literal", "type", "dynamic"}
VALID_REQUIRED = {"required", "optional"}
ADVISORIES_PATH = ROOT / "platform" / "tooling" / "command-advisories.py"


@dataclass(frozen=True)
class Param:
    name: str
    required: str
    placeholder: str
    value_class: str
    detail: str


@dataclass(frozen=True)
class Route:
    path: Path
    namespace: str
    route: str
    dispatch: str
    params: list[Param]


class ReferenceError(Exception):
    pass


def load_command_advisories_module():
    spec = importlib.util.spec_from_file_location("command_advisories", ADVISORIES_PATH)
    if spec is None or spec.loader is None:
        raise ReferenceError(f"cannot load command advisories module: {ADVISORIES_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_advisory_catalog():
    module = load_command_advisories_module()
    try:
        catalog = module.load_catalog(
            data_dir=CONFIG_ROOT / "platform" / "data",
            commands_dir=COMMANDS_DIR,
            roles_dir=CONFIG_ROOT / "commands/collab/reference/roles",
        )
    except module.AdvisoryError as exc:
        raise ReferenceError(f"command advisories invalid: {exc}") from exc
    return module, catalog


def fenced_blocks(text: str, info: str) -> list[str]:
    blocks: list[str] = []
    lines = text.splitlines()
    in_block = False
    fence = ""
    body: list[str] = []
    for line in lines:
        opener = re.match(rf"^\s*(`{{3,}}|~{{3,}}){re.escape(info)}\s*$", line)
        if not in_block and opener:
            in_block = True
            fence = opener.group(1)
            body = []
            continue
        if in_block:
            if re.match(rf"^\s*{re.escape(fence)}\s*$", line):
                blocks.append("\n".join(body))
                in_block = False
                fence = ""
                body = []
                continue
            body.append(line.strip())
    if in_block:
        blocks.append("\n".join(body))
    return blocks


def first_label(text: str, label: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}:\*\* (.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def uncode(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def first_code_span(value: str) -> str:
    match = re.search(r"`([^`]+)`", value)
    if match:
        return match.group(1)
    return uncode(value)


def route_name_from_dispatch(path: Path, namespace: str, route_slug: str, dispatch: str) -> str:
    if not (dispatch.startswith("(") and dispatch.endswith(")")):
        raise ReferenceError(f"{path}: invalid Dispatch routed form: {dispatch}")
    tokens = dispatch[1:-1].split()
    if not tokens or tokens[0] != namespace:
        raise ReferenceError(f"{path}: Dispatch route does not match namespace {namespace}: {dispatch}")
    candidate_tokens: list[str] = []
    for token in tokens[1:]:
        if token.startswith(("<", "[", "--")) or "<" in token:
            break
        candidate_tokens.append(token)
    candidate = " ".join(candidate_tokens).strip()
    slug_words = route_slug.replace("-", " ")
    if candidate == route_slug or candidate == slug_words:
        return candidate
    if candidate.startswith(slug_words + " "):
        return slug_words
    return candidate or slug_words


def route_has_params(dispatch: str) -> bool:
    return any(token in dispatch for token in ("<", "[", "--"))


def parse_key_values(path: Path, raw: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for part in re.split(r";\s+(?=[a-z-]+=)", raw):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise ReferenceError(f"{path}: malformed route-arg field: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in data:
            raise ReferenceError(f"{path}: duplicate route-arg field: {key}")
        data[key] = value
    return data


def registry_role_keys() -> list[str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "platform" / "tooling" / "roles.py"), "roles"],
        cwd=ROOT,
        env={**os.environ, "COMMAND_CONFIG_ROOT": str(CONFIG_ROOT)},
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    keys: list[str] = []
    for line in proc.stdout.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit() and cells[1]:
            keys.append(cells[1])
    if not keys:
        raise ReferenceError("platform/tooling/roles.py roles returned no role keys")
    return keys


def parse_route_arg(path: Path, text: str, public_dispatch: str) -> list[Param]:
    blocks = fenced_blocks(text, "route-arg")
    has_params = route_has_params(public_dispatch)
    if not has_params:
        if blocks:
            raise ReferenceError(f"{path}: route-arg block present on parameterless route")
        return []
    if len(blocks) != 1:
        raise ReferenceError(f"{path}: expected exactly one route-arg block for parameterized route")

    dispatch = ""
    params: list[Param] = []
    for raw_line in blocks[0].splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("dispatch:"):
            if dispatch:
                raise ReferenceError(f"{path}: duplicate dispatch field")
            dispatch = line.split(":", 1)[1].strip()
            continue
        if not line.startswith("param:"):
            raise ReferenceError(f"{path}: malformed route-arg line: {line}")
        data = parse_key_values(path, line.split(":", 1)[1])
        for key in ("name", "required", "placeholder", "class"):
            if not data.get(key):
                raise ReferenceError(f"{path}: route-arg param missing {key}")
        value_class = data["class"]
        required = data["required"]
        if value_class not in VALID_CLASSES:
            raise ReferenceError(f"{path}: invalid value class: {value_class}")
        if required not in VALID_REQUIRED:
            raise ReferenceError(f"{path}: invalid required value: {required}")

        detail = ""
        if value_class == "literal":
            if data.get("source") == ROLE_SOURCE:
                detail = " | ".join(registry_role_keys())
            elif data.get("values"):
                detail = data["values"]
            elif data.get("source"):
                detail = data["source"]
            else:
                raise ReferenceError(f"{path}: literal param needs values or source")
        elif value_class == "dynamic" and data.get("source") == ROLE_SOURCE:
            registry_role_keys()
            detail = ROLE_DYNAMIC_DETAIL
        else:
            detail = data.get("rule", "")
            if not detail:
                raise ReferenceError(f"{path}: {value_class} param needs rule")

        name = data["name"]
        placeholder = data["placeholder"]
        if name not in public_dispatch and placeholder not in public_dispatch:
            raise ReferenceError(f"{path}: route-arg param absent from Dispatch: {name}")
        params.append(Param(name, required, placeholder, value_class, detail))

    if not dispatch:
        raise ReferenceError(f"{path}: route-arg block missing dispatch")
    if dispatch != public_dispatch:
        raise ReferenceError(f"{path}: route-arg dispatch disagrees with Trigger Dispatch")
    if not params:
        raise ReferenceError(f"{path}: route-arg block has no params")
    return params


def load_routes() -> list[Route]:
    routes: list[Route] = []
    if COMMANDS_DIR.exists():
        for path in sorted(COMMANDS_DIR.glob("*/*/index.md")):
            text = path.read_text(encoding="utf-8")
            dispatch_label = first_label(text, "Dispatch")
            if not dispatch_label or "reference only" in dispatch_label:
                continue
            dispatch = first_code_span(dispatch_label)
            params = parse_route_arg(path, text, dispatch)
            rel = path.relative_to(COMMANDS_DIR)
            namespace = rel.parts[0]
            route = path.parent.name
            routes.append(Route(path, namespace, route, dispatch, params))
    return routes


def render_block() -> str:
    routes = load_routes()
    advisory_module, advisory_catalog = load_advisory_catalog()
    lines = [
        "_Generated by `platform/tooling/command-reference.py`; do not edit this block by hand._",
        "",
    ]
    current_namespace = ""
    for route in routes:
        if route.namespace != current_namespace:
            if current_namespace:
                lines.append("")
            current_namespace = route.namespace
            lines.append(f"## {current_namespace}")
        route_label = route_name_from_dispatch(route.path, route.namespace, route.route, route.dispatch)
        lines.append(f"### {route_label}")
        lines.append(f"`{route.dispatch}`")
        try:
            lines.extend(advisory_module.render_lines_for_route(advisory_catalog, route.namespace, route_label))
        except advisory_module.AdvisoryError as exc:
            raise ReferenceError(f"command advisory render failed for {route.dispatch}: {exc}") from exc
        if route.params:
            for param in route.params:
                lines.append(f"  `{param.name}`    {param.required}    {param.value_class}: `{param.detail}`")
    return "\n".join(lines).rstrip() + "\n"


def replacegenerated_block(existing: str, generated: str) -> str:
    lines = existing.splitlines(keepends=True)
    begin_indexes = [i for i, line in enumerate(lines) if line.rstrip("\n") == BEGIN_MARKER]
    end_indexes = [i for i, line in enumerate(lines) if line.rstrip("\n") == END_MARKER]
    if len(begin_indexes) != 1 or len(end_indexes) != 1 or begin_indexes[0] >= end_indexes[0]:
        raise ReferenceError(f"{ARTIFACT}: expected exactly one generated marker pair")
    begin = begin_indexes[0]
    end = end_indexes[0]
    return "".join(lines[: begin + 1]) + generated + "".join(lines[end:])


def write_artifact() -> None:
    if not ARTIFACT.exists():
        raise ReferenceError(f"missing artifact shell: {ARTIFACT}")
    current = ARTIFACT.read_text(encoding="utf-8")
    rendered = replacegenerated_block(current, render_block())
    with ARTIFACT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)
    print(f"command-reference: rendered {ARTIFACT.relative_to(ROOT)}")


def check_artifact() -> int:
    if not ARTIFACT.exists():
        print(
            "command-reference: missing generated artifact; run `platform/tooling/command-reference.py --render` to update",
            file=sys.stderr,
        )
        return 1
    current = ARTIFACT.read_text(encoding="utf-8")
    try:
        expected = replacegenerated_block(current, render_block())
    except ReferenceError as exc:
        print(f"command-reference: {exc}", file=sys.stderr)
        return 1
    if current != expected:
        diff = "".join(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                expected.splitlines(keepends=True),
                fromfile=str(ARTIFACT),
                tofile="rendered",
            )
        )
        print(
            "command-reference: generated artifact is stale; run `platform/tooling/command-reference.py --render` to update",
            file=sys.stderr,
        )
        print(diff, file=sys.stderr, end="")
        return 1
    print("command-reference: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render or validate the generated command reference.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render", action="store_true", help="update generated/command-reference.md")
    mode.add_argument("--check", action="store_true", help="verify generated/command-reference.md is current")
    args = parser.parse_args()
    try:
        if args.render:
            write_artifact()
            return 0
        return check_artifact()
    except ReferenceError as exc:
        print(f"command-reference: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
