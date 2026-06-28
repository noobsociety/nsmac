#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET_ROOT="$ROOT"
SYNC=1

usage() {
  cat <<'EOF'
usage:
  platform/tooling/new-route.sh <namespace> <route> [--root <path>] [--no-sync]
  platform/tooling/new-route.sh --self-test

Scaffold a public command route in commands/<namespace>/<route>/index.md and,
when possible, refresh generated command surfaces.
EOF
}

die() {
  printf 'new-route: %s\n' "$*" >&2
  exit 1
}

valid_name() {
  [[ "$1" =~ ^[a-z][a-z0-9-]*$ ]]
}

route_title() {
  local raw="$1"
  raw="${raw//-/ }"
  printf '%s' "$raw" | awk '{for (i=1;i<=NF;i++) {$i=toupper(substr($i,1,1)) substr($i,2)}; print}'
}

scaffold_route() {
  local namespace="$1"
  local route="$2"
  local commands_dir="$TARGET_ROOT/commands"
  local namespace_dir="$commands_dir/$namespace"
  local route_dir="$namespace_dir/$route"
  local route_file="$route_dir/index.md"
  local title

  valid_name "$namespace" || die "namespace must match ^[a-z][a-z0-9-]*$: $namespace"
  valid_name "$route" || die "route must match ^[a-z][a-z0-9-]*$: $route"
  [[ -d "$commands_dir" ]] || die "missing commands directory: $commands_dir"
  [[ -e "$route_file" ]] && die "route already exists: $route_file"

  mkdir -p "$route_dir"
  title="$(route_title "$route")"

  if [[ ! -f "$namespace_dir/index.md" ]]; then
    cat >"$namespace_dir/index.md" <<EOF
# ($namespace)

Namespace router for $namespace commands.

## Trigger

**Dispatch:** \`($namespace <command>)\` - routing-only command form; not a shell command.
**Search phrases:** $namespace commands

## Steps

1. Resolve the command token after \`$namespace\`.
2. Load the matching route file under \`commands/$namespace/<route>/index.md\`.
3. Stop after the selected route completes.
EOF
  fi

  cat >"$route_file" <<EOF
# ($namespace $route)

$title command route.

## Trigger

**Dispatch:** \`($namespace $route)\` - routing-only command form; not a shell command.
**Search phrases:** $namespace $route

## Steps

1. Read this route before acting.
<!-- abort: $route-scaffold-unimplemented -->
2. If the scaffold placeholder is still present, **ABORT**: route-specific behavior is not implemented.
3. Replace this scaffold with route-specific behavior before shipping.
4. Stop after reporting the outcome.

## Notes

- Add route-specific parameters, abort anchors, advisory data, and tests before shipping.
EOF

  mkdir -p "$TARGET_ROOT/tests/commands/$namespace/registry.py"
  cat >"$TARGET_ROOT/tests/commands/$namespace/registry.py/$route-scaffold-unimplemented.test.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail

ROOT="\$(cd "\$(dirname "\$0")/../../../.." && pwd)"
cd "\$ROOT"

test -f "commands/$namespace/$route/index.md"
grep -Fq "route-specific behavior is not implemented" "commands/$namespace/$route/index.md"
EOF
  chmod +x "$TARGET_ROOT/tests/commands/$namespace/registry.py/$route-scaffold-unimplemented.test.sh"

  if [[ "$namespace" == "collab" ]]; then
    run_collab_coverage_gate
  fi

  if ((SYNC)); then
    if [[ -x "$TARGET_ROOT/platform/tooling/sync-commands-catalog.sh" ]]; then
      "$TARGET_ROOT/platform/tooling/sync-commands-catalog.sh" >/dev/null
    fi
    if [[ -f "$TARGET_ROOT/platform/tooling/command-reference.py" ]]; then
      python3 "$TARGET_ROOT/platform/tooling/command-reference.py" --render >/dev/null 2>&1 || true
    fi
  fi

  printf 'new-route: created commands/%s/%s/index.md\n' "$namespace" "$route"
}

run_collab_coverage_gate() {
  "$ROOT/platform/tooling/coverage-gate.sh" \
    --routes-dir "$TARGET_ROOT" \
    --tests-dir "$TARGET_ROOT/tests/commands/collab/registry.py" >/dev/null
}

self_test() {
  local tmp
  tmp="$(mktemp -d)"
  trap "rm -rf '$tmp'" EXIT

  mkdir -p "$tmp/commands"
  TARGET_ROOT="$tmp"
  SYNC=0
  scaffold_route collab discovered-route >/dev/null

  cat >>"$tmp/commands/collab/discovered-route/index.md" <<'EOF'
<!-- abort: discovered-route-demo -->
**ABORT**: demo missing-coverage branch.
EOF

  if "$ROOT/platform/tooling/coverage-gate.sh" \
    --routes-dir "$tmp" \
    --tests-dir "$tmp/tests/commands/collab/registry.py" >/tmp/new-route-coverage.out 2>&1; then
    cat /tmp/new-route-coverage.out >&2
    die "self-test expected coverage-gate to fail for discovered missing coverage"
  fi

  if ! grep -Fq "discovered-route-demo.test.sh" /tmp/new-route-coverage.out; then
    cat /tmp/new-route-coverage.out >&2
    die "self-test did not observe discovery-based missing coverage"
  fi

  printf 'new-route: self-test OK\n'
}

if (($# == 0)); then
  usage
  exit 1
fi

if [[ "${1:-}" == "--self-test" ]]; then
  self_test
  exit 0
fi

namespace="${1:-}"
route="${2:-}"
shift 2 || die "missing namespace or route"

while (($#)); do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || die "--root requires a value"
      TARGET_ROOT="$(cd "$2" && pwd)"
      shift 2
      ;;
    --no-sync)
      SYNC=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

scaffold_route "$namespace" "$route"
