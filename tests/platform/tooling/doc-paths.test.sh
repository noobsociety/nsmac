#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
GATE="$ROOT/platform/tooling/audit-doc-paths.py"

clean="$TMPDIR/clean"
mkdir -p "$clean/commands/collab" "$clean/platform/standards"
git -C "$clean" init -q
git -C "$clean" config user.email test@example.com
git -C "$clean" config user.name Test
printf '# Target\n' >"$clean/platform/standards/target.md"
cat >"$clean/commands/collab/index.md" <<'MD'
# Fixture

Read `platform/standards/target.md`.
External `~/.collabs/project/registry.json` and template `weekly/<YYYY-Www>` are not repo paths.
MD
git -C "$clean" add .
git -C "$clean" commit -qm init
python3 "$GATE" --root "$clean" >/dev/null

bad="$TMPDIR/bad"
cp -R "$clean" "$bad"
printf '\nMissing `platform/standards/missing.md`.\n' >>"$bad/commands/collab/index.md"
git -C "$bad" add .
git -C "$bad" commit -qm bad
set +e
python3 "$GATE" --root "$bad" >"$TMPDIR/bad.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected missing backticked repo path to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'backticked repo path missing: `platform/standards/missing.md`' "$TMPDIR/bad.out"; then
  printf 'FAIL: doc-path output mismatch\n' >&2
  cat "$TMPDIR/bad.out" >&2
  exit 1
fi

printf 'OK: doc path gate rejects missing backticked repo-relative paths\n'
