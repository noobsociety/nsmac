#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

repo="$TMPDIR/repo"
git init -q "$repo"
mkdir -p "$repo/tests"

cat >"$repo/tests/run.sh" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail

printf 'ran %s\n' "$(basename "$0")" >>"$HOOK_TEST_MARKER"
RUN
chmod 0755 "$repo/tests/run.sh"

hooks_dir="$repo/.git/hooks"
marker="$TMPDIR/marker"

COMMAND_SYSTEM_GIT_HOOKS_DIR="$hooks_dir" "$ROOT/platform/tooling/install-git-hooks.sh" >"$TMPDIR/install.out"

for hook in pre-commit pre-push; do
  if [[ ! -x "$hooks_dir/$hook" ]]; then
    printf 'FAIL: expected executable hook: %s\n' "$hook" >&2
    exit 1
  fi

  if ! grep -Fq './tests/run.sh' "$hooks_dir/$hook"; then
    printf 'FAIL: hook does not invoke ./tests/run.sh: %s\n' "$hook" >&2
    exit 1
  fi

  (cd "$repo" && HOOK_TEST_MARKER="$marker" "$hooks_dir/$hook")
done

line_count="$(wc -l <"$marker" | tr -d '[:space:]')"
if [[ "$line_count" != "2" ]]; then
  printf 'FAIL: expected both hooks to invoke tests/run.sh\n' >&2
  cat "$marker" >&2
  exit 1
fi

set +e
COMMAND_SYSTEM_GIT_HOOKS_DIR="$hooks_dir" "$ROOT/platform/tooling/install-git-hooks.sh" >"$TMPDIR/reinstall.out" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: reinstall unexpectedly overwrote existing hooks\n' >&2
  exit 1
fi

if ! grep -Fq 'refusing to overwrite existing hook:' "$TMPDIR/reinstall.out"; then
  printf 'FAIL: reinstall did not explain existing-hook refusal\n' >&2
  cat "$TMPDIR/reinstall.out" >&2
  exit 1
fi

printf 'OK: git hook installer writes and protects pre-commit/pre-push hooks\n'
