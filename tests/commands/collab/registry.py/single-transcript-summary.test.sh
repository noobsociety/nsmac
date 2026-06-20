#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-single-transcript-summary"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Single Transcript Summary" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
RECORDS_DIR="$(dirname "$REGISTRY")/records"
TRANSCRIPT="$RECORDS_DIR/$TARGET.md"
RAW="$RECORDS_DIR/$TARGET-raw.md"
STORE="$RECORDS_DIR/$TARGET-contributions.json"

if [[ ! -f "$TRANSCRIPT" ]]; then
  printf 'FAIL: canonical transcript missing: %s\n' "$TRANSCRIPT" >&2
  exit 1
fi
if [[ -e "$RAW" ]]; then
  printf 'FAIL: init created legacy raw transcript: %s\n' "$RAW" >&2
  exit 1
fi
if [[ ! -f "$STORE" ]]; then
  printf 'FAIL: contribution store missing: %s\n' "$STORE" >&2
  exit 1
fi
if [[ "$(find "$RECORDS_DIR" -maxdepth 1 -name "$TARGET*.md" -type f | wc -l | tr -d ' ')" != "1" ]]; then
  printf 'FAIL: init should leave exactly one markdown transcript for target\n' >&2
  find "$RECORDS_DIR" -maxdepth 1 -name "$TARGET*.md" -type f >&2
  exit 1
fi

cat >>"$TRANSCRIPT" <<'EOF'

### Summary — 2026-01-01

Old generated summary.
EOF
cat >summary.md <<'EOF'
Generated phase summary lives in the canonical transcript.
EOF

"$ROOT/commands/collab/engine/registry.py" summarize "$TARGET" --date 2026-01-01 >/dev/null
grep -Fq '<!-- collab:phase-summary-managed -->' "$TRANSCRIPT"
grep -Fq '## Phase Summary' "$TRANSCRIPT"
grep -Fq '_Last refreshed: 2026-01-01_' "$TRANSCRIPT"
grep -Fq -- '- **Audit:** no contributions' "$TRANSCRIPT"
grep -Fq -- '- **Completion:**' "$TRANSCRIPT"

"$ROOT/commands/collab/engine/registry.py" summarize "$TARGET" --date 2026-01-01 >/dev/null
if [[ "$(grep -cF '<!-- collab:phase-summary-managed -->' "$TRANSCRIPT")" != "1" ]]; then
  printf 'FAIL: summarize duplicated the managed phase summary block\n' >&2
  exit 1
fi

"$ROOT/commands/collab/engine/registry.py" rewrite-summary "$TARGET" \
  --summary-file summary.md \
  --date 2026-01-02 >/dev/null

grep -Fq '### Summary — 2026-01-02' "$TRANSCRIPT"
grep -Fq 'Generated phase summary lives in the canonical transcript.' "$TRANSCRIPT"
if grep -Fq 'Old generated summary.' "$TRANSCRIPT"; then
  printf 'FAIL: rewrite-summary left the old summary body in place\n' >&2
  exit 1
fi
if [[ -e "$RAW" ]]; then
  printf 'FAIL: summary write created legacy raw transcript: %s\n' "$RAW" >&2
  exit 1
fi
if find "$RECORDS_DIR" -maxdepth 1 \( -name "$TARGET-synthesis.json" -o -name "$TARGET-synthesis" \) | grep -q .; then
  printf 'FAIL: summary write created synthesis artifacts\n' >&2
  exit 1
fi

printf 'OK: summary writes stay inside the single canonical transcript\n'
