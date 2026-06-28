#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
GATE="$ROOT/platform/tooling/audit-present-state.py"

clean="$TMPDIR/clean"
mkdir -p "$clean/commands/collab/reference" "$clean/platform/data" "$clean/tests/fixtures"
doctrine_ban="Do not retain legacy aliases, deprecation win""dows, or backwards-""compatibility shims."
cat >"$clean/commands/collab/reference/current.md" <<'MD'
# Current Fixture

The retract tombstone feature and dp tombstone status are current behavior.
Legacy-named test fixtures are allowed when they are live fixture names.
The P9 no-legacy-dispatch rule remains a present-tense invariant.
Each source file is capped at <= 250 lines per file.
Module size policy: ≤250 lines per file as a standing rule.
Keep modules under 300 lines.
`registry.py` is 6008 lines.
MD
{
  printf '# Platform Doctrines\n\n'
  printf '**Rule:** When a name is wrong, remove it at source. %s\n' "$doctrine_ban"
} >"$clean/platform/data/doctrines.md"
cat >"$clean/tests/fixtures/legacy-name.md" <<'MD'
# Fixture

This live fixture keeps its legacy filename for parser coverage.
MD

python3 "$GATE" --root "$clean" >/dev/null

bad="$TMPDIR/bad"
cp -R "$clean" "$bad"
weekly_line="Next weekly ""target: reduce to <=50 ""by ""W31"
printf '\n%s\n' "$weekly_line" >>"$bad/commands/collab/reference/current.md"

set +e
python3 "$GATE" --root "$bad" >"$TMPDIR/bad.out" 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: expected present-state audit to reject weekly target residue\n' >&2
  exit 1
fi
expected_weekly='present-state residue (next weekly '"target)"
if ! grep -Fq "$expected_weekly" "$TMPDIR/bad.out"; then
  printf 'FAIL: present-state audit output did not name weekly target residue\n' >&2
  cat "$TMPDIR/bad.out" >&2
  exit 1
fi
expected_week='by '"W31"
if ! grep -Fq "$expected_week" "$TMPDIR/bad.out"; then
  printf 'FAIL: present-state audit output did not preserve offending text\n' >&2
  cat "$TMPDIR/bad.out" >&2
  exit 1
fi

# Structured roadmap/snapshot/quota residue class (the registry.md gap): dated
# certifications, issue-numbered roadmap promises, and line-count baselines/targets.
bad2="$TMPDIR/bad2"
cp -R "$clean" "$bad2"
roadmap_line="Proposed #""57 should extract the renderer surface."
baseline_line="Baseline before the extraction: registry.py is 6008 ""lines."
target_line_a="Success requires \`registry.py\` at 5200 ""lines or fewer after #""57."
target_line_b="Reduce \`registry.py\` to 5200 ""lines in the seal extraction."
cert_line="Subsystem certif""ication (2026-06-23): all checks clean."
{
  printf '\n%s\n' "$roadmap_line"
  printf '%s\n' "$baseline_line"
  printf '%s\n' "$target_line_a"
  printf '%s\n' "$target_line_b"
  printf '%s\n' "$cert_line"
} >>"$bad2/commands/collab/reference/current.md"

set +e
python3 "$GATE" --root "$bad2" >"$TMPDIR/bad2.out" 2>&1
status2=$?
set -e
if [[ "$status2" -eq 0 ]]; then
  printf 'FAIL: expected present-state audit to reject roadmap, baseline, target, and certification residue\n' >&2
  exit 1
fi
for label in 'issue-roadmap promise' "line-""count baseline" "line-""count target" 'dated certification'; do
  if ! grep -Fq "present-state residue ($label)" "$TMPDIR/bad2.out"; then
    printf 'FAIL: present-state audit did not flag %s residue\n' "$label" >&2
    cat "$TMPDIR/bad2.out" >&2
    exit 1
  fi
done
target_hits=$(grep -Fc "present-state residue (line-""count target)" "$TMPDIR/bad2.out")
if [[ "$target_hits" -lt 2 ]]; then
  printf 'FAIL: present-state audit did not flag both line-count target forms\n' >&2
  cat "$TMPDIR/bad2.out" >&2
  exit 1
fi

printf 'OK: present-state audit rejects past/future outcome residue without banning live terminology\n'
