#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

for template in \
  "commands/collab/reference/transcript-template.md" \
  "commands/collab/reference/transcript-template-raw.md"
do
  if [[ -e "$ROOT/$template" ]]; then
    printf 'FAIL: retired target-format transcript template still exists: %s\n' "$template" >&2
    exit 1
  fi
done

if ! grep -Fq 'commands/collab/engine/transcript_render.py' "$ROOT/commands/collab/reference/anchor-convention.md"; then
  printf 'FAIL: anchor convention missing transcript renderer emitter citation\n' >&2
  exit 1
fi

while IFS= read -r source_path; do
  rel_source="${source_path#"$ROOT"/}"
  if [[ "$rel_source" == "tests/commands/collab/registry.py/target-spec-template-runtime-exemption.test.sh" ]]; then
    continue
  fi
  if grep -Eq 'transcript-template(-raw)?\.md' "$source_path"; then
    printf 'FAIL: retired transcript template reference remains in live source: %s\n' "$rel_source" >&2
    exit 1
  fi
done < <(rg -l 'transcript-template' "$ROOT/commands" "$ROOT/tests" "$ROOT/platform")

printf 'OK: retired target-format transcript templates remain absent from live source\n'
