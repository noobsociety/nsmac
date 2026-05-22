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
    .gitignore|.collab.json|CLAUDE.md|AGENTS.md|README.md|REPOSITORY.md) return 0 ;;
    .github/*) return 0 ;;
    _core/*|_data/*|_functions/*|_generated/*|_roles/*|_templates/*|_tests/*|commands/*|core/*|tests/*|tools/*) return 0 ;;
    *) return 1 ;;
  esac
}

check_required_surface() {
  require_file CLAUDE.md
  require_file AGENTS.md
  require_file README.md
  require_file .collab.json
  require_file commands/commands.md
  require_dir _core
  require_dir _functions
  require_dir _generated
  require_dir _roles
  require_dir _tests
  require_dir tools/command-system
}

check_adapters() {
  grep -Fq 'AGENTS.md' CLAUDE.md || fail "CLAUDE.md does not route to AGENTS.md"
  grep -Fq 'commands/commands.md' AGENTS.md || fail "AGENTS.md does not route to commands/commands.md"
  ok "adapter entry surfaces are named"
}

check_runtime_boundary() {
  local path skill_payload
  skill_payload="skills-cur""sor"
  for path in .claude projects extensions ide_state.json "$skill_payload" plugins skills plans subagents; do
    if [[ -e "$path" ]]; then
      git check-ignore -q "$path" || fail "runtime path is not ignored: $path"
    fi
  done

  if grep -Eq '^!(\.claude|projects|extensions|ide_state\.json|skills-cur''sor|plugins|skills|plans|subagents)(/|$)' .gitignore; then
    fail ".gitignore un-ignores a runtime-only path"
  else
    ok "runtime-only paths remain ignored by policy"
  fi
}

check_collab_contract_terms() {
  python3 - <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

tracked = subprocess.run(['git', 'ls-files', '-z'], check=True, stdout=subprocess.PIPE).stdout.decode().split('\0')
canonical = 'user-scope ' + 'collab ' + 'state root'
checks = [
    ('retired marker filename', '.collab-project' + '.json', set(), False),
    ('retired repo-local stub path', '.collabs/project' + '.json', {'_functions/collab/_identity-contract.md'}, False),
    ('retired collab phrase', 'global ' + 'home', {'_functions/collab/_glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'state ' + 'directory', {'_functions/collab/_glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'resolved state ' + 'directory', {'_functions/collab/_glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'home ' + 'state root', {'_functions/collab/_glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'collab ' + 'state root', {'_functions/collab/_glossary.md'}, True),
    ('forbidden substitute for user-scope collab state root', 'resolved state root ' + 'path', {'_functions/collab/_glossary.md'}, False),
]
failures: list[str] = []

for rel in filter(None, tracked):
    path = Path(rel)
    if not path.exists() or path.is_dir():
        continue
    try:
        lines = path.read_text(errors='strict').splitlines()
    except UnicodeDecodeError:
        continue
    for number, line in enumerate(lines, start=1):
        for kind, phrase, allow, strip_canonical in checks:
            haystack = line
            if strip_canonical:
                haystack = re.sub(re.escape(canonical), '', haystack, flags=re.IGNORECASE)
            if phrase.lower() in haystack.lower() and rel not in allow:
                failures.append(f'FAIL: {kind}: {rel}:{number}: {phrase}')

if re.search(r'^!?\.collabs(/|$)', Path('.gitignore').read_text(), flags=re.MULTILINE):
    failures.append('FAIL: .gitignore still has a repo-local .collabs entry')
if Path('.collabs').exists():
    failures.append('FAIL: repo-local .collabs/ exists; current collab state must resolve through the user-scope collab state root')

if failures:
    print('\n'.join(failures), file=sys.stderr)
    sys.exit(1)
PY
  local status=$?
  ((status == 0)) || failures=$((failures + 1))
  ((status == 0)) && ok "collab retired vocabulary and topology stay contained"
}

check_collab_registry_lock() {
  python3 - <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

marker = Path('.collab.json')
if not marker.exists():
    print('OK: collab registry lock check skipped; .collab.json missing')
    sys.exit(0)
try:
    identity = json.loads(marker.read_text())
except json.JSONDecodeError as exc:
    print(f'FAIL: .collab.json invalid JSON: {exc}', file=sys.stderr)
    sys.exit(1)
project_id = identity.get('projectId')
if not isinstance(project_id, str) or not project_id:
    print('FAIL: .collab.json missing projectId', file=sys.stderr)
    sys.exit(1)
state_home = Path(os.environ.get('COLLAB_STATE_HOME', Path.home() / '.collabs')).expanduser()
registry = state_home / project_id / 'registry.json'
if not registry.exists():
    print('OK: collab registry lock check skipped; registry absent')
    sys.exit(0)
import subprocess

result = subprocess.run(
    [sys.executable, 'tools/collab/registry.py', 'validate'],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if result.returncode:
    print(result.stdout, end='', file=sys.stderr)
    sys.exit(result.returncode)
print('OK: collab registry lock state is valid')
PY
  local status=$?
  ((status == 0)) || failures=$((failures + 1))
}

check_retired_name_allowlist() {
  python3 - <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

result = subprocess.run(
    ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
    check=True,
    stdout=subprocess.PIPE,
)
paths = [item for item in result.stdout.decode().split('\0') if item]
needle = 'cur' + 'sor'
pattern = re.compile(needle, re.IGNORECASE)
failures: list[str] = []


def allowed(line: str, start: int) -> bool:
    lower = line.lower()
    if start >= 3 and lower[start - 3:start + 6] == '~/.cursor':
        return True
    accepted_system = 'dot' + needle
    if start >= 3 and lower[start - 3:start + 6] == accepted_system:
        before = lower[start - 4] if start >= 4 else ' '
        after = lower[start + 6] if start + 6 < len(lower) else ' '
        return not (before.isalnum() or before in '_-') and not (after.isalnum() or after in '_-')
    return False


for rel in paths:
    path = Path(rel)
    if not path.is_file():
        continue
    try:
        lines = path.read_text(errors='strict').splitlines()
    except UnicodeDecodeError:
        continue
    for number, line in enumerate(lines, start=1):
        for match in pattern.finditer(line):
            if not allowed(line, match.start()):
                failures.append(f'FAIL: retired-name vocabulary outside allowlist: {rel}:{number}: {line}')
                break

if failures:
    print('\n'.join(failures), file=sys.stderr)
    sys.exit(1)
print('OK: retired-name vocabulary is allowlisted')
PY
  local status=$?
  ((status == 0)) || failures=$((failures + 1))
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
    [[ -e "$path" ]] || continue
    if ! is_source_path "$path"; then
      printf 'FAIL: tracked file outside source boundary: %s\n' "$path" >&2
      bad=1
    fi
  done < <(git ls-files)
  ((bad == 0)) || failures=$((failures + 1))
  ((bad == 0)) && ok "tracked files stay inside the source boundary"
}

check_generated_freshness() {
  python3 tools/command-system/check-source-ledger.py --check || failures=$((failures + 1))
  tools/command-system/sync-context-gate.sh --check || failures=$((failures + 1))
  tools/command-system/sync-commands-catalog.sh --check || failures=$((failures + 1))
  tools/command-system/sync-framework-boundaries.sh --check || failures=$((failures + 1))
  tools/command-system/sync-roles-roster.sh --check || failures=$((failures + 1))
  python3 tools/command-system/command-advisories.py --check || failures=$((failures + 1))
  python3 tools/command-system/command-reference.py --check || failures=$((failures + 1))
  tools/command-system/audit-topology.sh || failures=$((failures + 1))
  tools/command-system/audit-flag-scope.sh || failures=$((failures + 1))
  tools/command-system/audit-placement.sh || failures=$((failures + 1))
  tools/collab/lifecycle-doc.py --check || failures=$((failures + 1))
  tools/command-system/coverage-gate.sh || failures=$((failures + 1))
  tools/command-system/audit-role-prose.sh || failures=$((failures + 1))
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
    ["git", "ls-files", "*.md"],
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
    if not path.exists():
        continue
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

check_route_arg_defaults() {
  python3 - <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

failures: list[str] = []

for path in sorted(Path('_functions').rglob('*.md')):
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith('param: '):
            continue
        fields: dict[str, str] = {}
        for part in stripped.removeprefix('param: ').split(';'):
            if '=' not in part:
                continue
            key, value = part.strip().split('=', 1)
            fields[key.strip()] = value.strip()
        required = fields.get('required')
        if required == 'optional' and 'default' not in fields:
            failures.append(f'{path}:{number}: optional route-arg param missing default=')
        if required == 'required' and 'default' in fields:
            failures.append(f'{path}:{number}: required route-arg param must not declare default=')

if failures:
    for failure in failures:
        print(f'FAIL: {failure}', file=sys.stderr)
    sys.exit(1)
print('OK: route-arg optional defaults are declared')
PY
  local status=$?
  ((status == 0)) || failures=$((failures + 1))
}

check_required_surface
check_adapters
check_runtime_boundary
check_retired_name_allowlist
check_collab_contract_terms
check_untracked_payload
check_tracked_source_boundary
check_collab_registry_lock
check_generated_freshness
check_generated_boundary
check_links
check_route_arg_defaults

if ((failures > 0)); then
  printf 'audit: failed with %d issue(s)\n' "$failures" >&2
  exit 1
fi

printf 'audit: OK\n'
