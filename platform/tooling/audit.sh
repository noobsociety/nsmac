#!/usr/bin/env bash
set -euo pipefail

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

check_runtime_preflight() {
  local contract="platform/standards/runtime-contract.md"
  local python_status=0
  local bash_status=0
  local git_root=""

  [[ -f "$contract" ]] || fail "runtime-contract: missing $contract"

  if ! command -v python3 >/dev/null 2>&1; then
    fail "runtime-contract: missing required executable: python3"
  else
    python3 - <<'PYCODE' || python_status=$?
import sys

if sys.version_info < (3, 9):
    print(
        "runtime-contract: Python >= 3.9 required; found "
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        file=sys.stderr,
    )
    sys.exit(1)
PYCODE
    ((python_status == 0)) || fail "runtime-contract: Python >= 3.9 required"
  fi

  if ! command -v bash >/dev/null 2>&1; then
    fail "runtime-contract: missing required executable: bash"
  else
    bash -c '((BASH_VERSINFO[0] > 3 || (BASH_VERSINFO[0] == 3 && BASH_VERSINFO[1] >= 2)))' || bash_status=$?
    ((bash_status == 0)) || fail "runtime-contract: bash >= 3.2 required"
  fi

  if ! command -v git >/dev/null 2>&1; then
    fail "runtime-contract: missing required executable: git"
  else
    git_root="$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null || true)"
    [[ "$git_root" == "$ROOT" ]] || fail "runtime-contract: audit.sh must resolve to the repository root"
  fi
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
    .gitignore|.collab.json|CLAUDE.md|AGENTS.md|README.md|REPOSITORY.md|registry.schema.json) return 0 ;;
    .github/*) return 0 ;;
    platform/reference.md) return 0 ;;
    platform/standards/*|platform/data/*|platform/tooling/*|generated/*|platform/templates/*|tests/specs/*|commands/*|tests/*) return 0 ;;
    *) return 1 ;;
  esac
}

check_required_surface() {
  require_file CLAUDE.md
  require_file AGENTS.md
  require_file README.md
  require_file .collab.json
  require_file commands/commands.md
  require_dir platform/standards
  require_dir generated
  require_dir commands/collab/reference/roles
  require_dir tests/specs
  require_dir platform/tooling
}

check_adapters() {
  grep -Fq 'AGENTS.md' CLAUDE.md || fail "CLAUDE.md does not route to AGENTS.md"
  grep -Fq 'commands/commands.md' AGENTS.md || fail "AGENTS.md does not route to commands/commands.md"
  grep -Fq 'generated/registry-cli.md' AGENTS.md || fail "AGENTS.md Fail-fast section is missing availability-check carve-out (generated/registry-cli.md)"
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
  local status=0
  python3 - <<'PY' || status=$?
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

tracked = subprocess.run(['git', 'ls-files', '-z'], check=True, stdout=subprocess.PIPE).stdout.decode().split('\0')
canonical = 'user-scope ' + 'collab ' + 'state root'
checks = [
    ('retired marker filename', '.collab-project' + '.json', set(), False),
    ('retired repo-local stub path', '.collabs/project' + '.json', {'commands/collab/reference/identity-contract.md'}, False),
    ('retired collab phrase', 'global ' + 'home', {'commands/collab/reference/glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'state ' + 'directory', {'commands/collab/reference/glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'resolved state ' + 'directory', {'commands/collab/reference/glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'home ' + 'state root', {'commands/collab/reference/glossary.md'}, False),
    ('forbidden substitute for user-scope collab state root', 'collab ' + 'state root', {'commands/collab/reference/glossary.md'}, True),
    ('forbidden substitute for user-scope collab state root', 'resolved state root ' + 'path', {'commands/collab/reference/glossary.md'}, False),
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
  ((status == 0)) || failures=$((failures + 1))
  ((status == 0)) && ok "collab retired vocabulary and topology stay contained"
}

check_collab_registry_lock() {
  local status=0
  python3 - <<'PY' || status=$?
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
    [sys.executable, 'commands/collab/engine/registry.py', 'validate'],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if result.returncode:
    print(result.stdout, end='', file=sys.stderr)
    sys.exit(result.returncode)
print('OK: collab registry lock state is valid')
PY
  ((status == 0)) || failures=$((failures + 1))
}

check_retired_name_allowlist() {
  local status=0
  python3 - <<'PY' || status=$?
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
  python3 platform/tooling/check-source-ledger.py --check || failures=$((failures + 1))
  platform/tooling/sync-context-gate.sh --check || failures=$((failures + 1))
  platform/tooling/sync-commands-catalog.sh --check || failures=$((failures + 1))
  platform/tooling/sync-framework-boundaries.sh --check || failures=$((failures + 1))
  platform/tooling/sync-roles-roster.sh --check || failures=$((failures + 1))
  python3 platform/tooling/command-advisories.py --check || failures=$((failures + 1))
  python3 platform/tooling/command-reference.py --check || failures=$((failures + 1))
  commands/collab/engine/registry.py registry-cli-doc --check || failures=$((failures + 1))
  platform/tooling/audit-topology.sh || failures=$((failures + 1))
  python3 platform/tooling/audit-collab-route-wiring.py || failures=$((failures + 1))
  python3 platform/tooling/audit-collab-readonly-contract.py || failures=$((failures + 1))
  python3 platform/tooling/audit-projector-loader-symbols.py || failures=$((failures + 1))
  python3 platform/tooling/audit-doc-paths.py || failures=$((failures + 1))
  python3 platform/tooling/audit-present-state.py || failures=$((failures + 1))
  platform/tooling/audit-flag-scope.sh || failures=$((failures + 1))
  platform/tooling/audit-placement.sh || failures=$((failures + 1))
  commands/collab/engine/lifecycle-doc.py --check || failures=$((failures + 1))
  platform/tooling/coverage-gate.sh || failures=$((failures + 1))
  platform/tooling/audit-role-prose.sh || failures=$((failures + 1))
}

check_generated_boundary() {
  local path bad=0
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    case "$path" in
      generated/command-reference.md|generated/collab-lifecycle.md|generated/content-invariants.tsv|generated/registry-cli.md) ;;
      *)
        printf 'FAIL: unexpected generated artifact: %s\n' "$path" >&2
        bad=1
        ;;
    esac
  done < <(find generated -type f | sort)
  ((bad == 0)) || failures=$((failures + 1))
  ((bad == 0)) && ok "framework-generated output is isolated in generated/"
}

check_retired_collab_residue() {
  local output status hits rel_source source_path bad=0
  local help_output

  if grep -R "RAW_PROVENANCE_BANNER" commands/collab/engine >/dev/null 2>&1; then
    fail "RAW_PROVENANCE_BANNER remains in collab engine"
  fi

  help_output="$(commands/collab/engine/registry.py --help)"
  if grep -Fq 'migrate-raw-transcript' <<<"$help_output"; then
    fail "migrate-raw-transcript helper command remains in registry CLI"
  fi

  if grep -R "migrate_raw_transcript\\|legacy_raw_transcript\\|raw_transcript_path_for_entry" commands/collab/engine >/dev/null 2>&1; then
    fail "raw transcript migration path remains in collab engine"
  fi

  for command in synthesize-state synthesize render-raw-transcript render-projection-transcript; do
    if grep -Fq "$command" <<<"$help_output"; then
      fail "registry.py help still exposes $command"
    fi

    set +e
    output="$(commands/collab/engine/registry.py "$command" 2>&1)"
    status=$?
    set -e
    if [[ "$status" -eq 0 || "$output" != *"invalid choice"* ]]; then
      fail "registry.py $command remains invocable"
    fi

    if grep -Fq "### \`$command\`" generated/registry-cli.md; then
      fail "generated registry CLI docs still list $command"
    fi
  done

  if git ls-files --error-unmatch commands/collab/engine/synthesis.py >/dev/null 2>&1; then
    fail "commands/collab/engine/synthesis.py is still tracked"
  fi

  if find tests/commands/collab/registry.py -maxdepth 1 -name 'synthesize-*.test.sh' -print -quit | grep -q .; then
    fail "synthesize registry tests are still present"
  fi

  for source_path in \
    tests/commands/collab/aggregate-transcript.test.sh \
    tests/commands/collab/modules/transcript-render-projection-store.test.sh
  do
    if [[ -n "$(git ls-files "$source_path")" || -e "$source_path" ]]; then
      fail "stale projection test remains: $source_path"
    fi
  done

  hits="$(git grep -nE 'contribution_store_digest|projection_source_digest|projection_store_records' \
    -- commands/collab/engine '*.py' 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "dead synthesis digest/store symbol remains: $hits"
  fi

  python3 - <<'PY' || failures=$((failures + 1))
from commands.collab.engine import registry
from commands.collab.engine import seal_verification
from commands.collab.engine import transcript_render

assert registry
assert seal_verification
for name in (
    'excerpt_source',
    'stance_for_content',
    'is_hidden_metadata_line',
):
    assert hasattr(transcript_render, name), name
assert not hasattr(transcript_render, 'projection_excerpt_source')
assert not hasattr(transcript_render, 'projection_stance_for_content')
assert not hasattr(transcript_render, 'is_projection_hidden_metadata_line')
PY

  if grep -Fq 'synthesis artifacts' commands/collab/summarize/index.md 2>/dev/null; then
    fail "synthesis-artifact negation residue found in summarize route prose"
  fi

  if grep -Fq 'Projector metadata is intentionally absent' commands/collab/show-policy/index.md 2>/dev/null; then
    fail "projector-metadata negation residue found in show-policy route prose"
  fi

  if grep -Fq '## Deterministic Projector (dp)' commands/collab/reference/role-prohibitions.md 2>/dev/null; then
    fail "Deterministic Projector (dp) prohibition section still present in role-prohibitions.md"
  fi

  if grep -Fq '(collab aggregate)' commands/collab/init/index.md commands/collab/open/index.md 2>/dev/null; then
    fail "retired (collab aggregate) dispatch reference found in init or open route docs"
  fi

  if grep -P 'records/[^`]*-raw\.md' commands/collab/init/index.md commands/collab/open/index.md >/dev/null 2>&1; then
    fail "raw transcript sibling path reference found in init or open route docs"
  fi

  hits="$(git grep -nP '\bprojection-mode\b' \
    -- 'commands/' 'platform/standards/' \
    ':(exclude)commands/collab/engine/' \
    ':(exclude)records/' 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "synthesis projection-mode flag found in live doc surfaces: $hits"
  fi

  hits="$(git grep -nP '\bper-piece\b' \
    -- 'commands/' 'platform/standards/' \
    ':(exclude)commands/collab/engine/' \
    ':(exclude)records/' 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "synthesis per-piece mode found in live doc surfaces: $hits"
  fi

  hits="$(git grep -nP '\b(?:is_)?projection_[a-z_]+\s*[\(=]' \
    -- 'commands/collab/engine/*.py' 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "legacy projection_* / is_projection_* render symbol found in engine Python: $hits"
  fi

  if [[ -d "commands/collab/reference/synthesizers" ]]; then
    fail "commands/collab/reference/synthesizers/ directory still exists"
  fi

  if [[ -f "commands/collab/reference/synthesizers/sy.json" ]]; then
    fail "synthesizers/sy.json still exists"
  fi

  if [[ -d "commands/collab/reference/projectors" ]]; then
    fail "commands/collab/reference/projectors/ directory still exists"
  fi

  if [[ -f "commands/collab/reference/projectors/dp.json" ]]; then
    fail "projectors/dp.json still exists"
  fi

  hits="$(git grep -nP '\bSynthesizer\b' \
    -- 'commands/' 'platform/standards/' \
    ':(exclude)commands/collab/engine/' \
    ':(exclude)records/' \
    ':(exclude)commands/collab/reference/roles/' 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    fail "Synthesizer role identity prose found in live surfaces: $hits"
  fi

  if grep -Eq '\(collab synthesize\)|synthesize/index\.md' commands/commands.md 2>/dev/null; then
    fail "synthesis dispatch found in commands/commands.md"
  fi

  if grep -Eq '\(collab synthesize\)|synthesize/index\.md' generated/command-reference.md 2>/dev/null; then
    fail "synthesis dispatch found in generated/command-reference.md"
  fi

  for source_path in \
    "commands/collab/reference/transcript-template.md" \
    "commands/collab/reference/transcript-template-raw.md"
  do
    if [[ -e "$source_path" ]]; then
      fail "retired target-format transcript template still exists: $source_path"
    fi
  done

  if ! grep -Fq 'commands/collab/engine/transcript_render.py' commands/collab/reference/anchor-convention.md; then
    fail "anchor convention missing transcript renderer emitter citation"
  fi

  while IFS= read -r source_path; do
    rel_source="${source_path#"$ROOT"/}"
    if [[ "$rel_source" == "platform/tooling/audit.sh" ]]; then
      continue
    fi
    if grep -Eq 'transcript-template(-raw)?\.md' "$source_path"; then
      fail "retired transcript template reference remains in live source: $rel_source"
      bad=1
    fi
  done < <(rg -l 'transcript-template' "$ROOT/commands" "$ROOT/tests" "$ROOT/platform")

  ((bad == 0)) || failures=$((failures + 1))
  ((bad == 0)) && ok "retired raw/synthesis/template surfaces remain absent"
}

check_links() {
  local status=0
  python3 - <<'PY' || status=$?
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
  ((status == 0)) || failures=$((failures + 1))
}

check_public_dispatch_surface() {
  local status=0
  python3 platform/tooling/check-public-dispatch-surface.py --root "$ROOT" || status=$?
  ((status == 0)) || failures=$((failures + 1))
}

check_verification_round_call_sites() {
  local status=0
  python3 - commands/collab/engine/registry_core.py commands/collab/engine/seal_verification_render.py <<'PY' || status=$?
import ast
import sys
from pathlib import Path
from typing import Union

registry_core_path = Path(sys.argv[1])
seal_path = Path(sys.argv[2])
FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


def parse_functions(path: Path) -> dict[str, FunctionNode]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


registry_core_functions = parse_functions(registry_core_path)
seal_functions = parse_functions(seal_path)


def require_function(
    functions: dict[str, FunctionNode],
    function_name: str,
    message: str,
) -> FunctionNode:
    function = functions.get(function_name)
    assert function is not None, message
    return function


def calls_name(function: FunctionNode, callee_name: str) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name) and callee.id == callee_name:
                return True
    return False


def delegates_to_seal_verification_render(
    function: FunctionNode,
    callee_name: str,
) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            callee = node.func
            if (
                isinstance(callee, ast.Attribute)
                and callee.attr == callee_name
                and isinstance(callee.value, ast.Name)
                and callee.value.id == '_seal_verification_render'
            ):
                return True
    return False


registry_core_participant_verify_render = require_function(
    registry_core_functions,
    'participant_verify_render',
    'registry_core.py must define participant_verify_render as part of the permanent seal facade pair',
)
registry_core_render_seal = require_function(
    registry_core_functions,
    'render_seal',
    'registry_core.py must define render_seal as the legacy seal dispatch shim',
)
seal_participant_verify_render = require_function(
    seal_functions,
    'participant_verify_render',
    'seal_verification_render.py must define the participant_verify_render implementation',
)
seal_write = require_function(
    seal_functions,
    'seal_write',
    'seal_verification_render.py must define the seal_write implementation',
)
record_verdict = require_function(
    seal_functions,
    'record_verdict',
    'seal_verification_render.py must define the record_verdict implementation',
)
legacy_render_seal = require_function(
    seal_functions,
    'render_seal',
    'seal_verification_render.py must define the legacy render_seal dispatch shim',
)

assert delegates_to_seal_verification_render(
    registry_core_participant_verify_render,
    'participant_verify_render',
), (
    'registry_core.py participant_verify_render facade must delegate to '
    '_seal_verification_render.participant_verify_render'
)
assert delegates_to_seal_verification_render(registry_core_render_seal, 'render_seal'), (
    'registry_core.py render_seal shim must delegate to _seal_verification_render.render_seal'
)
assert calls_name(seal_participant_verify_render, 'record_verification_round_for_execution'), (
    'participant_verify_render must record the paired verification round'
)
assert not calls_name(registry_core_participant_verify_render, 'record_verification_round_for_execution'), (
    'registry_core.py participant_verify_render facade must not call '
    'record_verification_round_for_execution; seal_verification.py owns the recorder call'
)
assert not calls_name(registry_core_render_seal, 'record_verification_round_for_execution'), (
    'protected seal-render recorder boundary: registry_core.py render_seal must not call '
    'record_verification_round_for_execution'
)
for function_name, function in [
    ('seal_write', seal_write),
    ('record_verdict', record_verdict),
    ('render_seal', legacy_render_seal),
]:
    assert not calls_name(function, 'record_verification_round_for_execution'), (
        'protected seal recorder boundary: seal_verification_render.py '
        f'{function_name} must not call record_verification_round_for_execution'
    )

assert calls_name(legacy_render_seal, 'seal_write'), (
    'legacy render_seal shim must dispatch bare seals to seal_write'
)
assert calls_name(legacy_render_seal, 'record_verdict'), (
    'legacy render_seal shim must dispatch verdict writes to record_verdict'
)
PY
  ((status == 0)) || failures=$((failures + 1))
  ((status == 0)) && ok "verification round recorder call sites stay owned by participant verification"
}

check_contribution_validation_placement() {
  local status=0
  python3 - commands/collab/engine/registry_core.py commands/collab/engine/contribution_validation.py <<'PY' || status=$?
import ast
import sys
from pathlib import Path

registry_core_path = Path(sys.argv[1])
validation_path = Path(sys.argv[2])


def function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


registry_core_functions = function_names(registry_core_path)
validation_functions = function_names(validation_path)
owned_by_validation = {
    'assert_turn_order_not_drifted',
    'enforce_contribution_budget',
    'validate_action_plan_executable_scope',
    'validate_action_plan_shape',
    'validate_conclusion_directive_gap',
    'validate_effort_override',
    'validate_reviewer_conclusion_gates',
}

missing = sorted(owned_by_validation - validation_functions)
assert not missing, (
    'contribution_validation.py must own speak-time contribution gates: '
    + ', '.join(missing)
)

leaked = sorted(owned_by_validation & registry_core_functions)
assert not leaked, (
    'registry_core.py must stay a facade for speak-time contribution gates; move back to '
    'contribution_validation.py: '
    + ', '.join(leaked)
)
PY
  ((status == 0)) || failures=$((failures + 1))
  ((status == 0)) && ok "speak-time contribution validation stays outside registry.py facade"
}

check_route_arg_defaults() {
  local status=0
  python3 - <<'PY' || status=$?
from __future__ import annotations

import sys
from pathlib import Path

failures: list[str] = []

for path in sorted(Path('commands').rglob('index.md')):
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
  ((status == 0)) || failures=$((failures + 1))
}

check_qa_spec_rosters() {
  local status=0
  python3 - <<'PY' || status=$?
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(".")


def extract_bullets(path: Path, marker: str, stop_markers: tuple[str, ...]) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(marker) + 1
    except ValueError:
        raise AssertionError(f"{path}: missing marker: {marker}")
    items: list[str] = []
    for line in lines[start:]:
        if line in stop_markers or line.startswith("## "):
            break
        match = re.match(r"- `([^`]+)`$", line)
        if match:
            items.append(match.group(1))
    return items


def assert_equal(label: str, actual: list[str], expected: list[str]) -> list[str]:
    if sorted(actual) == sorted(expected):
        return []
    return [
        f"{label} roster mismatch",
        f"  actual:   {actual}",
        f"  expected: {expected}",
    ]


failures: list[str] = []

commands_root = ROOT / "commands"
commands_spec = ROOT / "tests/specs/commands.md"
expected_command_routers = sorted(
    ["commands.md"]
    + [
        path.relative_to(commands_root).as_posix()
        for path in commands_root.glob("*/index.md")
    ]
)
expected_command_routes = sorted(
    path.relative_to(commands_root).as_posix()
    for path in commands_root.glob("*/*/index.md")
)
failures.extend(assert_equal(
    "commands.md public router",
    extract_bullets(
        commands_spec,
        "Public command routers under `~/.cursor/commands/`:",
        ("Route playbooks under `~/.cursor/commands/`:",),
    ),
    expected_command_routers,
))
failures.extend(assert_equal(
    "commands.md route playbook",
    extract_bullets(
        commands_spec,
        "Route playbooks under `~/.cursor/commands/`:",
        ("## Output",),
    ),
    expected_command_routes,
))

core_spec = ROOT / "tests/specs/core.md"
expected_standards = sorted(path.name for path in (ROOT / "platform/standards").glob("*.md"))
failures.extend(assert_equal(
    "core.md platform standards",
    extract_bullets(core_spec, "## Required roster", ("## Output",)),
    expected_standards,
))

roles_dir = ROOT / "commands/collab/reference/roles"
roles_spec = ROOT / "tests/specs/roles.md"
expected_roles = sorted(path.name for path in roles_dir.glob("*.json"))
expected_joinable_roles: list[str] = []
for path in sorted(roles_dir.glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("joinable", True) is not False:
        expected_joinable_roles.append(path.name)
failures.extend(assert_equal(
    "roles.md tracked source",
    extract_bullets(
        roles_spec,
        "Tracked role source files under `commands/collab/reference/roles/`:",
        ("Joinable role source files under `commands/collab/reference/roles/`:",),
    ),
    expected_roles,
))
failures.extend(assert_equal(
    "roles.md joinable source",
    extract_bullets(
        roles_spec,
        "Joinable role source files under `commands/collab/reference/roles/`:",
        ("## Output",),
    ),
    expected_joinable_roles,
))

settings_spec = (ROOT / "tests/specs/settings.md").read_text(encoding="utf-8")
if (ROOT / "settings").exists():
    failures.append("settings.md declares no tracked settings, but settings/ exists")
if "Tracked user-settings source files under `settings/`: none." not in settings_spec:
    failures.append("settings.md must declare an empty tracked settings roster")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    sys.exit(1)

print("OK: QA spec rosters match source state")
PY
  ((status == 0)) || failures=$((failures + 1))
}

check_runtime_preflight
if ((failures > 0)); then
  printf 'audit: runtime preflight failed with %d issue(s)\n' "$failures" >&2
  exit 1
fi

check_required_surface
check_adapters
check_runtime_boundary
check_retired_name_allowlist
check_collab_contract_terms
check_untracked_payload
check_tracked_source_boundary
check_collab_registry_lock
check_public_dispatch_surface
check_verification_round_call_sites
check_contribution_validation_placement
check_generated_freshness
check_generated_boundary
check_retired_collab_residue
check_links
platform/tooling/audit-reachability.sh || failures=$((failures + 1))
platform/tooling/audit-vocabulary.sh || failures=$((failures + 1))
check_route_arg_defaults
check_qa_spec_rosters

if ((failures > 0)); then
  printf 'audit: failed with %d issue(s)\n' "$failures" >&2
  exit 1
fi

printf 'audit: OK\n'
