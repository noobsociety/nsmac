#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1

failures=0

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  failures=$((failures + 1))
}

ok() {
  printf 'OK: %s\n' "$*"
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] && ok "found $path" || fail "missing required file: $path"
}

require_dir() {
  local path="$1"
  [[ -d "$path" ]] && ok "found $path/" || fail "missing required directory: $path/"
}

is_source_path() {
  case "$1" in
    .gitignore|CLAUDE.md|AGENTS.md|_CURSOR.md|README.md|REPOSITORY.md) return 0 ;;
    .github/*) return 0 ;;
    _core/*|_functions/*|_generated/*|_mdc/*|_roles/*|_templates/*|_tests/*|commands/*|rules/*|tests/*|tools/*) return 0 ;;
    *) return 1 ;;
  esac
}

check_required_surface() {
  require_file CLAUDE.md
  require_file AGENTS.md
  require_file _CURSOR.md
  require_file README.md
  require_file commands/commands.md
  require_file rules/auto.mdc
  require_file rules/shared.mdc
  require_dir _core
  require_dir _functions
  require_dir _generated
  require_dir _mdc
  require_dir _roles
  require_dir _tests
  require_dir tools/cursor
}

check_adapters() {
  grep -Fq 'AGENTS.md' CLAUDE.md || fail "CLAUDE.md does not route to AGENTS.md"
  grep -Fq '_CURSOR.md' AGENTS.md || fail "AGENTS.md does not route to _CURSOR.md"
  grep -Fq 'commands/commands.md' _CURSOR.md || fail "_CURSOR.md does not route to commands/commands.md"
  grep -Fq 'alwaysApply: true' rules/auto.mdc || fail "rules/auto.mdc is not auto-applied"
  grep -Fq 'alwaysApply: false' rules/shared.mdc || fail "rules/shared.mdc is not shared/on-request"
  ok "adapter and Cursor entry surfaces are named"
}

check_runtime_boundary() {
  local path
  for path in .collabs .claude projects extensions ide_state.json skills-cursor plugins skills plans subagents; do
    if [[ -e "$path" ]]; then
      git check-ignore -q "$path" || fail "runtime path is not ignored: $path"
    fi
  done

  if grep -Eq '^!(\.collabs|\.claude|projects|extensions|ide_state\.json|skills-cursor|plugins|skills|plans|subagents)(/|$)' .gitignore; then
    fail ".gitignore un-ignores a runtime-only path"
  else
    ok "runtime-only paths remain ignored by policy"
  fi
}

check_untracked_payload() {
  local path bad=0
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if is_source_path "$path"; then
      printf 'NOTE: untracked source candidate: %s\n' "$path"
    else
      printf 'FAIL: accidental untracked payload: %s\n' "$path" >&2
      bad=1
    fi
  done < <(git ls-files --others --exclude-standard)
  ((bad == 0)) || failures=$((failures + 1))
  ((bad == 0)) && ok "no accidental untracked payload"
}

check_tracked_source_boundary() {
  local path bad=0
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if ! is_source_path "$path"; then
      printf 'FAIL: tracked file outside source boundary: %s\n' "$path" >&2
      bad=1
    fi
  done < <(git ls-files)
  ((bad == 0)) || failures=$((failures + 1))
  ((bad == 0)) && ok "tracked files stay inside the source boundary"
}

check_generated_freshness() {
  tools/cursor/sync-commands-catalog.sh --check || failures=$((failures + 1))
  tools/cursor/sync-framework-boundaries.sh --check || failures=$((failures + 1))
  tools/cursor/sync-roles-roster.sh --check || failures=$((failures + 1))
  python3 tools/cursor/command-reference.py --check || failures=$((failures + 1))
  tools/collab/lifecycle-doc.py --check || failures=$((failures + 1))
  tools/cursor/coverage-gate.sh || failures=$((failures + 1))
}

check_generated_boundary() {
  local path bad=0
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    case "$path" in
      _generated/command-reference.md|_generated/collab-lifecycle.md|_generated/content-invariants.tsv) ;;
      *)
        printf 'FAIL: unexpected generated artifact: %s\n' "$path" >&2
        bad=1
        ;;
    esac
  done < <(find _generated -type f | sort)
  ((bad == 0)) || failures=$((failures + 1))
  ((bad == 0)) && ok "framework-generated output is isolated in _generated/"
}

check_links() {
  python3 - <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

root = Path.cwd()
tracked = subprocess.run(
    ["git", "ls-files", "*.md", "*.mdc"],
    cwd=root,
    check=True,
    text=True,
    stdout=subprocess.PIPE,
).stdout.splitlines()

link_re = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
bad: list[str] = []

for rel in tracked:
    path = root / rel
    lines: list[str] = []
    in_fence = False
    fence = ""
    for line in path.read_text().splitlines():
        marker = fence_re.match(line)
        if marker and not in_fence:
            in_fence = True
            fence = marker.group(1)[0]
            continue
        if in_fence:
            if line.lstrip().startswith(fence * 3):
                in_fence = False
                fence = ""
            continue
        lines.append(line)
    text = "\n".join(lines)
    for match in link_re.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        target = unquote(target)
        if target.startswith("~/.cursor/"):
            candidate = root / target.removeprefix("~/.cursor/")
        elif target.startswith("/"):
            continue
        else:
            candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            bad.append(f"{rel}: link escapes repo: {match.group(1)}")
            continue
        if not candidate.exists():
            bad.append(f"{rel}: broken link: {match.group(1)}")

if bad:
    for item in bad:
        print(f"FAIL: {item}", file=sys.stderr)
    sys.exit(1)
print("OK: markdown reference graph has no broken local links")
PY
  local status=$?
  ((status == 0)) || failures=$((failures + 1))
}

check_required_surface
check_adapters
check_runtime_boundary
check_untracked_payload
check_tracked_source_boundary
check_generated_freshness
check_generated_boundary
check_links

if ((failures > 0)); then
  printf 'audit: failed with %d issue(s)\n' "$failures" >&2
  exit 1
fi

printf 'audit: OK\n'
