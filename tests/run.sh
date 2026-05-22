#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

./tools/command-system/audit.sh
./tools/command-system/audit-role-prose.sh

while IFS= read -r test_script; do
  [[ -n "$test_script" ]] || continue
  bash "$test_script"
done < <(find tests -name "*.test.sh" -type f | sort)
