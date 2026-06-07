#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT/commands/collab/engine/registry.py" <<'PY'
import ast
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
tree = ast.parse(source_path.read_text(), filename=str(source_path))
functions = {
    node.name: node
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}


def calls_recorder(function_name: str) -> bool:
    function = functions[function_name]
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name) and callee.id == 'record_verification_round_for_execution':
                return True
    return False


assert calls_recorder('participant_verify_render'), (
    'participant_verify_render must record the paired verification round'
)
assert not calls_recorder('render_seal'), (
    'seal-render must not record or advance verification rounds'
)
PY

printf 'OK: verification round recorder call sites stay owned by participant verification\n'
