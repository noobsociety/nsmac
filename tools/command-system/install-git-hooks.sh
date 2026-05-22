#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOKS_DIR="${COMMAND_SYSTEM_GIT_HOOKS_DIR:-}"

if [[ -z "$HOOKS_DIR" ]]; then
  HOOKS_DIR="$(git -C "$ROOT" rev-parse --git-path hooks)"
fi

mkdir -p "$HOOKS_DIR"

existing=()
for hook in pre-commit pre-push; do
  if [[ -e "$HOOKS_DIR/$hook" ]]; then
    existing+=("$hook")
  fi
done

if ((${#existing[@]} > 0)); then
  for hook in "${existing[@]}"; do
    printf 'ERROR: refusing to overwrite existing hook: %s\n' "$HOOKS_DIR/$hook" >&2
  done
  exit 1
fi

write_hook() {
  local hook="$1"
  cat >"$HOOKS_DIR/$hook" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
exec ./tests/run.sh
HOOK
  chmod 0755 "$HOOKS_DIR/$hook"
  printf 'installed %s\n' "$HOOKS_DIR/$hook"
}

write_hook pre-commit
write_hook pre-push
