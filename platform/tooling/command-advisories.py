#!/usr/bin/env python3
# Contract: platform/tooling/advisory-coverage-policy.md
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = Path(os.environ.get("COMMAND_CONFIG_ROOT", ROOT)).expanduser().resolve()
DATA_DIR = CONFIG_ROOT / "platform" / "data"
COMMANDS_DIR = CONFIG_ROOT / "commands"
ROLES_DIR = CONFIG_ROOT / "commands/collab/reference/roles"
ARTIFACT = CONFIG_ROOT / "generated" / "command-reference.md"
SCHEMA_PATH = DATA_DIR / "command-advisory.schema.json"
POLICY_PATH = DATA_DIR / "command-advisory-policy.json"
BEGIN_MARKER = "<!-- BEGIN GENERATED:COMMAND_REFERENCE -->"
END_MARKER = "<!-- END GENERATED:COMMAND_REFERENCE -->"

PUBLIC_RENDER_FIELDS = {"route", "role", "capabilityTier", "effortTier", "rationale", "recommendation"}
INTERNAL_FIELDS = {"concerns", "runtimePolicyRef"}
INTERNAL_RENDER_TOKENS = {"runtimePolicyRef", "concerns[]", "`concerns`", "`runtimePolicyRef`"}
ALLOWED_FIELDS = PUBLIC_RENDER_FIELDS | INTERNAL_FIELDS
NOT_APPLICABLE = "not-applicable"


class AdvisoryError(Exception):
    pass


@dataclass(frozen=True)
class Route:
    namespace: str
    name: str
    slash: str
    path: Path


@dataclass(frozen=True)
class Advisory:
    namespace: str
    route: str
    role: str | None
    capability_tier: str | None
    effort_tier: str | None
    rationale: str
    recommendation: str | None
    source: Path
    index: int

    @property
    def is_not_applicable(self) -> bool:
        return self.recommendation == NOT_APPLICABLE


@dataclass(frozen=True)
class Catalog:
    defaults: dict[tuple[str, str], Advisory]
    overrides: dict[tuple[str, str], list[Advisory]]


@dataclass(frozen=True)
class AdvisoryPolicy:
    required_namespaces: set[str]
    namespace_coverage_exemptions: dict[str, str]
    model_or_harness_leakage_terms: set[str]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AdvisoryError(f"missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AdvisoryError(f"invalid JSON: {path}: {exc}") from exc


def string_list_field(data: dict[str, Any], field: str, path: Path) -> set[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise AdvisoryError(f"{path}: {field} must be a non-empty array")
    items: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AdvisoryError(f"{path}: {field} entries must be non-empty strings")
        items.add(item.strip())
    return items


def string_map_field(data: dict[str, Any], field: str, path: Path) -> dict[str, str]:
    value = data.get(field)
    if not isinstance(value, dict):
        raise AdvisoryError(f"{path}: {field} must be an object")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise AdvisoryError(f"{path}: {field} keys must be non-empty strings")
        if not isinstance(item, str) or not item.strip():
            raise AdvisoryError(f"{path}: {field}.{key} must be a non-empty string")
        result[key.strip()] = item.strip()
    return result


def load_advisory_policy(path: Path = POLICY_PATH) -> AdvisoryPolicy:
    data = load_json(path)
    if not isinstance(data, dict):
        raise AdvisoryError(f"{path}: advisory policy must be an object")
    allowed = {
        "requiredNamespaces",
        "namespaceCoverageExemptions",
        "modelOrHarnessLeakageTerms",
    }
    unknown = set(data) - allowed
    if unknown:
        raise AdvisoryError(f"{path}: unknown field(s): {', '.join(sorted(unknown))}")
    return AdvisoryPolicy(
        required_namespaces=string_list_field(data, "requiredNamespaces", path),
        namespace_coverage_exemptions=string_map_field(data, "namespaceCoverageExemptions", path),
        model_or_harness_leakage_terms=string_list_field(data, "modelOrHarnessLeakageTerms", path),
    )


def first_label(text: str, label: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}:\*\* (.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def first_code_span(value: str) -> str:
    match = re.search(r"`([^`]+)`", value)
    if match:
        return match.group(1)
    return value.strip()


def route_name_from_slash(slash: str, namespace: str) -> str:
    prefix = f"/{namespace}"
    if slash == prefix:
        return ""
    if not slash.startswith(prefix + " "):
        raise AdvisoryError(f"slash route does not match namespace {namespace}: {slash}")
    return slash[len(prefix) + 1 :].strip()


def load_routes(commands_dir: Path = COMMANDS_DIR) -> dict[str, dict[str, Route]]:
    routes: dict[str, dict[str, Route]] = {}
    if commands_dir.exists():
        for path in sorted(commands_dir.glob("*/*/index.md")):
            text = path.read_text(encoding="utf-8")
            slash_label = first_label(text, "Slash")
            if not slash_label or "reference only" in slash_label:
                continue
            slash = first_code_span(slash_label)
            rel = path.relative_to(commands_dir)
            namespace = rel.parts[0]
            route_name = route_name_from_slash(slash, namespace)
            if not route_name:
                continue
            by_namespace = routes.setdefault(namespace, {})
            if route_name in by_namespace:
                raise AdvisoryError(f"duplicate invocable route name in {namespace}: {route_name}")
            by_namespace[route_name] = Route(namespace, route_name, slash, path)
    return routes


def load_public_namespaces(commands_dir: Path = COMMANDS_DIR) -> set[str]:
    if not commands_dir.exists():
        return set()
    return {
        path.parent.name
        for path in sorted(commands_dir.glob("*/index.md"))
        if path.parent.name
    }


def load_role_keys(roles_dir: Path = ROLES_DIR) -> set[str]:
    if not roles_dir.exists():
        raise AdvisoryError(f"roles directory missing: {roles_dir}")
    keys: set[str] = set()
    for path in sorted(roles_dir.glob("*.json")):
        data = load_json(path)
        if not isinstance(data, dict) or not isinstance(data.get("key"), str):
            raise AdvisoryError(f"role file missing string key: {path}")
        key = data["key"]
        if key in keys:
            raise AdvisoryError(f"duplicate role key: {key}")
        keys.add(key)
    if not keys:
        raise AdvisoryError(f"no role keys found in {roles_dir}")
    return keys


def load_alias_keys(path: Path, label: str) -> set[str]:
    data = load_json(path)
    if not isinstance(data, dict) or not data:
        raise AdvisoryError(f"{label} source must be a non-empty object: {path}")
    for key, value in data.items():
        if not isinstance(key, str) or not key:
            raise AdvisoryError(f"{label} source contains invalid key: {path}")
        if not isinstance(value, dict):
            raise AdvisoryError(f"{label} entry must be an object: {path}: {key}")
    return set(data)


def runtime_policy_refs(policy: Any) -> set[str]:
    refs: set[str] = set()
    if not isinstance(policy, dict):
        return refs
    for key, value in policy.items():
        if isinstance(key, str) and key:
            refs.add(key)
        if isinstance(value, dict):
            for child in value:
                if isinstance(child, str) and child:
                    refs.add(f"{key}.{child}")
    return refs


def runtime_policy_forbidden_terms(policy: Any, advisory_policy: AdvisoryPolicy) -> set[str]:
    terms = set(advisory_policy.model_or_harness_leakage_terms)
    if isinstance(policy, dict):
        terms.update(str(key) for key in policy if isinstance(key, str))
    stack = [policy]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, str):
            terms.add(value)
    return {term.lower() for term in terms if term}


def validate_string(value: Any, field: str, path: Path, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdvisoryError(f"{path}: advisory {index} field {field} must be a non-empty string")
    return value.strip()


def validate_advisory(
    raw: Any,
    namespace: str,
    path: Path,
    index: int,
    capability_aliases: set[str],
    effort_tiers: set[str],
    role_keys: set[str],
    runtime_refs: set[str],
) -> Advisory:
    if not isinstance(raw, dict):
        raise AdvisoryError(f"{path}: advisory {index} must be an object")
    unknown = set(raw) - ALLOWED_FIELDS
    if unknown:
        raise AdvisoryError(f"{path}: advisory {index} has unknown field(s): {', '.join(sorted(unknown))}")

    route = validate_string(raw.get("route"), "route", path, index)
    role = raw.get("role")
    if role is not None:
        role = validate_string(role, "role", path, index)
        if role not in role_keys:
            raise AdvisoryError(f"{path}: advisory {index} role override is not a known joinable role: {role}")

    rationale = validate_string(raw.get("rationale"), "rationale", path, index)
    recommendation = raw.get("recommendation")
    if recommendation is not None and recommendation != NOT_APPLICABLE:
        raise AdvisoryError(f"{path}: advisory {index} recommendation must be {NOT_APPLICABLE!r}")

    capability_tier = raw.get("capabilityTier")
    effort_tier = raw.get("effortTier")
    if recommendation == NOT_APPLICABLE:
        if capability_tier is not None or effort_tier is not None:
            raise AdvisoryError(f"{path}: advisory {index} not-applicable entries must not set capabilityTier or effortTier")
        capability_value = None
        effort_value = None
    else:
        capability_value = validate_string(capability_tier, "capabilityTier", path, index)
        effort_value = validate_string(effort_tier, "effortTier", path, index)
        if capability_value not in capability_aliases:
            raise AdvisoryError(f"{path}: advisory {index} unknown capabilityTier: {capability_value}")
        if effort_value not in effort_tiers:
            raise AdvisoryError(f"{path}: advisory {index} unknown effortTier: {effort_value}")

    concerns = raw.get("concerns")
    if concerns is not None:
        if not isinstance(concerns, list) or not all(isinstance(item, str) and item.strip() for item in concerns):
            raise AdvisoryError(f"{path}: advisory {index} concerns must be a list of non-empty strings")

    runtime_policy_ref = raw.get("runtimePolicyRef")
    if runtime_policy_ref is not None:
        runtime_policy_ref = validate_string(runtime_policy_ref, "runtimePolicyRef", path, index)
        if runtime_policy_ref not in runtime_refs:
            raise AdvisoryError(f"{path}: advisory {index} runtimePolicyRef is not present in runtime policy: {runtime_policy_ref}")

    return Advisory(
        namespace=namespace,
        route=route,
        role=role,
        capability_tier=capability_value,
        effort_tier=effort_value,
        rationale=rationale,
        recommendation=recommendation,
        source=path,
        index=index,
    )


def differs_from_default(default: Advisory, override: Advisory) -> bool:
    if default.is_not_applicable != override.is_not_applicable:
        return True
    return (
        default.capability_tier != override.capability_tier
        or default.effort_tier != override.effort_tier
    )


def load_catalog(
    data_dir: Path = DATA_DIR,
    commands_dir: Path = COMMANDS_DIR,
    roles_dir: Path = ROLES_DIR,
) -> Catalog:
    schema_path = data_dir / "command-advisory.schema.json"
    if not schema_path.exists():
        raise AdvisoryError(f"missing advisory schema: {schema_path}")

    routes = load_routes(commands_dir)
    public_namespaces = load_public_namespaces(commands_dir)
    role_keys = load_role_keys(roles_dir)
    capability_aliases = load_alias_keys(data_dir / "capability-aliases.json", "capability alias")
    effort_tiers = load_alias_keys(data_dir / "effort-tiers.json", "effort tier")
    runtime_policy = load_json(data_dir / "runtime-policy.json")
    runtime_refs = runtime_policy_refs(runtime_policy)
    advisory_policy = load_advisory_policy(data_dir / "command-advisory-policy.json")

    advisories_dir = data_dir / "advisories"
    namespace_files: dict[str, Path] = {}
    if advisories_dir.exists():
        namespace_files.update({path.stem: path for path in sorted(advisories_dir.glob("*.json"))})
    for path in sorted(commands_dir.glob("*/data/*.json")):
        namespace = path.parent.parent.name
        if path.stem != namespace:
            continue
        if namespace in namespace_files:
            raise AdvisoryError(f"duplicate advisory namespace source for {namespace}: {namespace_files[namespace]} and {path}")
        namespace_files[namespace] = path
    if not namespace_files:
        raise AdvisoryError(f"no advisory namespace files found in {advisories_dir} or commands/*/data")
    required_namespaces = advisory_policy.required_namespaces
    coverage_exemptions = advisory_policy.namespace_coverage_exemptions
    known_namespaces = set(routes) | public_namespaces
    unknown_required = sorted(required_namespaces - known_namespaces)
    if unknown_required:
        raise AdvisoryError(f"required advisory namespace has no invocable routes: {', '.join(unknown_required)}")
    unknown_exemptions = sorted(set(coverage_exemptions) - known_namespaces)
    if unknown_exemptions:
        raise AdvisoryError(f"advisory coverage exemption has no invocable routes: {', '.join(unknown_exemptions)}")
    overlapping = sorted(required_namespaces & set(coverage_exemptions))
    if overlapping:
        raise AdvisoryError(f"advisory namespace cannot be both required and exempt: {', '.join(overlapping)}")
    missing_namespaces = sorted(required_namespaces - set(namespace_files))
    if missing_namespaces:
        raise AdvisoryError(f"missing required advisory namespace file(s): {', '.join(missing_namespaces)}")
    undecided_namespaces = sorted(known_namespaces - set(namespace_files) - set(coverage_exemptions))
    if undecided_namespaces:
        raise AdvisoryError(f"advisory coverage policy lacks namespace decision(s): {', '.join(undecided_namespaces)}")

    defaults: dict[tuple[str, str], Advisory] = {}
    overrides: dict[tuple[str, str], list[Advisory]] = {}
    seen: set[tuple[str, str, str | None]] = set()

    for namespace, path in namespace_files.items():
        data = load_json(path)
        if not isinstance(data, dict):
            raise AdvisoryError(f"{path}: advisory namespace file must be an object")
        declared_namespace = data.get("namespace")
        if declared_namespace != namespace:
            raise AdvisoryError(f"{path}: namespace must match filename stem: {namespace}")
        if namespace not in routes:
            raise AdvisoryError(f"{path}: namespace has no invocable route directory: {namespace}")
        raw_advisories = data.get("advisories")
        if not isinstance(raw_advisories, list) or not raw_advisories:
            raise AdvisoryError(f"{path}: advisories must be a non-empty array")
        route_names = routes[namespace]
        for index, raw in enumerate(raw_advisories, start=1):
            advisory = validate_advisory(
                raw,
                namespace,
                path,
                index,
                capability_aliases,
                effort_tiers,
                role_keys,
                runtime_refs,
            )
            if advisory.route not in route_names:
                raise AdvisoryError(f"{path}: advisory {index} route is not invocable in namespace {namespace}: {advisory.route}")
            key = (namespace, advisory.route, advisory.role)
            if key in seen:
                role_label = advisory.role if advisory.role is not None else "<default>"
                raise AdvisoryError(f"{path}: duplicate advisory for {namespace} {advisory.route} role {role_label}")
            seen.add(key)
            route_key = (namespace, advisory.route)
            if advisory.role is None:
                defaults[route_key] = advisory
            else:
                overrides.setdefault(route_key, []).append(advisory)

        missing_routes = sorted(set(route_names) - {route for ns, route in defaults if ns == namespace})
        if missing_routes:
            raise AdvisoryError(f"{path}: missing default advisory or not-applicable marker for route(s): {', '.join(missing_routes)}")

    for route_key, role_overrides in overrides.items():
        default = defaults.get(route_key)
        if default is None:
            namespace, route = route_key
            raise AdvisoryError(f"{namespace}/{route}: role override has no route default")
        for override in role_overrides:
            if not differs_from_default(default, override):
                raise AdvisoryError(
                    f"{override.source}: advisory {override.index} role override for {override.route}/{override.role} "
                    "must differ from the route default capabilityTier or effortTier"
                )

    return Catalog(defaults=defaults, overrides=overrides)


def route_key_from_slash(slash: str) -> tuple[str, str]:
    parts = slash.split()
    if not parts or not parts[0].startswith("/"):
        raise AdvisoryError(f"invalid slash route: {slash}")
    namespace = parts[0][1:]
    route = " ".join(parts[1:])
    return namespace, route


def render_advisory(advisory: Advisory) -> str:
    if advisory.role:
        prefix = f"> **Recommended for `{advisory.role}`:**"
    else:
        prefix = "> **Recommended:**"
    if advisory.is_not_applicable:
        line = f"{prefix} not applicable - {advisory.rationale}"
    else:
        line = f"{prefix} {advisory.capability_tier} capability; {advisory.effort_tier} effort - {advisory.rationale}"
    leaked = [token for token in INTERNAL_RENDER_TOKENS if token in line]
    if leaked:
        raise AdvisoryError(f"internal advisory field leaked into render output: {', '.join(sorted(leaked))}")
    return line


def render_lines_for_slash(catalog: Catalog, slash: str) -> list[str]:
    namespace, route = route_key_from_slash(slash)
    route_key = (namespace, route)
    default = catalog.defaults.get(route_key)
    if default is None:
        return []
    lines = [render_advisory(default)]
    for override in sorted(catalog.overrides.get(route_key, []), key=lambda item: item.role or ""):
        lines.append(render_advisory(override))
    return lines


def generated_advisory_lines(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        begin = lines.index(BEGIN_MARKER)
        end = lines.index(END_MARKER)
    except ValueError as exc:
        raise AdvisoryError(f"generated command reference marker missing in {ARTIFACT}") from exc
    if begin >= end:
        raise AdvisoryError(f"generated command reference markers out of order in {ARTIFACT}")
    return [line for line in lines[begin:end] if line.startswith("> **Recommended")]


def check_generated_leakage(artifact: Path, data_dir: Path = DATA_DIR) -> None:
    if not artifact.exists():
        raise AdvisoryError(f"missing generated artifact: {artifact}")
    runtime_policy = load_json(data_dir / "runtime-policy.json")
    advisory_policy = load_advisory_policy(data_dir / "command-advisory-policy.json")
    forbidden_terms = runtime_policy_forbidden_terms(runtime_policy, advisory_policy)
    text = artifact.read_text(encoding="utf-8")
    version_terms = "|".join(re.escape(term) for term in sorted(advisory_policy.model_or_harness_leakage_terms))
    model_version = re.compile(rf"\b(?:{version_terms})-[A-Za-z0-9._-]*\d[A-Za-z0-9._-]*\b", re.IGNORECASE)
    for line in generated_advisory_lines(text):
        lowered = line.lower()
        for token in INTERNAL_RENDER_TOKENS:
            if token.lower() in lowered:
                raise AdvisoryError(f"generated advisory leaks internal field {token}: {line}")
        for term in forbidden_terms:
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                raise AdvisoryError(f"generated advisory leaks runtime policy or model term {term!r}: {line}")
        if model_version.search(line):
            raise AdvisoryError(f"generated advisory leaks concrete model version: {line}")


def check(
    data_dir: Path = DATA_DIR,
    commands_dir: Path = COMMANDS_DIR,
    roles_dir: Path = ROLES_DIR,
    artifact: Path = ARTIFACT,
) -> int:
    try:
        load_catalog(data_dir=data_dir, commands_dir=commands_dir, roles_dir=roles_dir)
        check_generated_leakage(artifact=artifact, data_dir=data_dir)
    except AdvisoryError as exc:
        print(f"command-advisories: {exc}", file=sys.stderr)
        return 1
    print("command-advisories: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate command advisory data and generated output.")
    parser.add_argument("--check", action="store_true", required=True, help="validate advisory data and generated output")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--commands-dir", default=str(COMMANDS_DIR))
    parser.add_argument("--roles-dir", default=str(ROLES_DIR))
    parser.add_argument("--artifact", default=str(ARTIFACT))
    args = parser.parse_args()
    return check(
        data_dir=Path(args.data_dir),
        commands_dir=Path(args.commands_dir),
        roles_dir=Path(args.roles_dir),
        artifact=Path(args.artifact),
    )


if __name__ == "__main__":
    raise SystemExit(main())
