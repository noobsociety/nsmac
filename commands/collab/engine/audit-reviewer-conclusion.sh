#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      if [[ $# -lt 2 ]]; then
        printf 'audit-reviewer-conclusion: --root requires a value\n' >&2
        exit 2
      fi
      ROOT="$2"
      shift 2
      ;;
    --help|-h)
      printf 'usage: %s [--root DIR]\n' "$(basename "$0")"
      exit 0
      ;;
    *)
      printf 'audit-reviewer-conclusion: unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
speak_path = root / 'commands/collab/speak/index.md'
speak_commands_path = root / 'commands/collab/engine/speak_commands.py'
validation_path = root / 'commands/collab/engine/contribution_validation.py'
expected_gates = (
    'DIRECTIVE TEST',
    'AUDIT CONFIRMED',
    'PRECEDENT CITED',
    'LOOP CHECK',
)
failures: list[str] = []


def read(path: Path) -> str:
    if not path.is_file():
        failures.append(f'missing required file: {path.relative_to(root)}')
        return ''
    return path.read_text(encoding='utf-8')


speak = read(speak_path)
speak_commands = read(speak_commands_path)
validation = read(validation_path)

audit_note = speak.partition('**Reviewer-discipline gates (Audit phase):**')[2]
if not audit_note:
    failures.append('missing Reviewer-discipline gates (Audit phase) note in commands/collab/speak/index.md')
else:
    for gate in expected_gates:
        if gate not in audit_note:
            failures.append(f'missing Audit reviewer gate in speak docs: {gate}')
    if 'Invariant #16' not in audit_note:
        failures.append('Audit reviewer gate note must cite Invariant #16 evidence anchors')
    if 'agent judgment' not in audit_note or 'no helper enforcement' not in audit_note:
        failures.append('Audit reviewer gate note must preserve the honor-system enforcement boundary')

if 'def validate_reviewer_conclusion_gates' not in validation:
    failures.append('contribution_validation.py missing validate_reviewer_conclusion_gates')
if "if phase != 'Conclusion' or role != reviewer_role(entry):" not in validation:
    failures.append('reviewer Conclusion gate must target only the active reviewer in Conclusion')
if 'REVIEWER-CONCLUSION-GATE-MISSING:' not in validation:
    failures.append('reviewer Conclusion gate missing stable abort family')
if 'validate_reviewer_conclusion_gates(content, phase, role, current_entry)' not in speak_commands:
    failures.append('speak-render must call reviewer Conclusion gate before mutation')

tuple_match = re.search(r'REVIEWER_DISCIPLINE_GATES = \((?P<body>.*?)\)', validation, re.S)
if not tuple_match:
    failures.append('contribution_validation.py missing REVIEWER_DISCIPLINE_GATES tuple')
else:
    tuple_body = tuple_match.group('body')
    for gate in expected_gates:
        if repr(gate) not in tuple_body:
            failures.append(f'missing reviewer gate in registry tuple: {gate}')

if failures:
    print('\n'.join(f'FAIL: {item}' for item in failures), file=sys.stderr)
    raise SystemExit(1)

print('OK: reviewer Audit/Conclusion discipline gates are documented and wired')
PY
