#!/usr/bin/env bash
set -euo pipefail

# Content-addressed seal is invariant under tree-preserving rewrites: amending a
# deliverable commit that leaves the tree identical does not change the scope
# digest, so the success verdict still passes.  The prior commit-reachability
# gate that rejected amend-orphaned commits is replaced by
# the content-digest equality check, which is tree-invariant.
#
# An uncommitted (staged-only) path is still rejected via SEAL-CONTENT-INCOMPLETE,
# because HEAD has no committed blob for that path.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / 'tools' / 'collab'))
import registry as R

with tempfile.TemporaryDirectory() as tmpdir:
    repo = Path(tmpdir)

    def git(*args, env_extra=None):
        env = {**os.environ, **(env_extra or {})}
        subprocess.run(
            ['git', '-C', str(repo)] + list(args),
            check=True, capture_output=True, env=env,
        )

    git('init', '-q')
    git('config', 'user.email', 'tester@example.com')
    git('config', 'user.name', 'tester')

    (repo / 'foo.txt').write_text('deliverable\n')
    git('add', 'foo.txt')
    git('commit', '-qm', 'deliverable',
        env_extra={'GIT_AUTHOR_DATE': '2026-01-01T00:00:00',
                   'GIT_COMMITTER_DATE': '2026-01-01T00:00:00'})

    digest_before = R.content_digest_for_touched_paths(repo, 'HEAD', ['foo.txt'])

    # Amend: re-date the commit, tree unchanged.  The original SHA is now orphaned.
    git('commit', '--amend', '-qm', 'deliverable (re-dated)',
        env_extra={'GIT_AUTHOR_DATE': '2026-06-03T18:00:00',
                   'GIT_COMMITTER_DATE': '2026-06-03T18:00:00'})

    digest_after = R.content_digest_for_touched_paths(repo, 'HEAD', ['foo.txt'])

    assert digest_before == digest_after, (
        f'amend changed content digest:\n  before: {digest_before!r}\n  after:  {digest_after!r}'
    )

    # Staged-only path (not committed): must fail SEAL-CONTENT-INCOMPLETE.
    (repo / 'staged.txt').write_text('staged only\n')
    git('add', 'staged.txt')

    try:
        R.content_digest_for_touched_paths(repo, 'HEAD', ['staged.txt'])
    except SystemExit as exc:
        msg = str(exc)
        assert 'SEAL-CONTENT-INCOMPLETE' in msg, f'unexpected error: {msg!r}'
    else:
        raise AssertionError('staged-only path did not raise SEAL-CONTENT-INCOMPLETE')

print('OK: amend leaves content digest unchanged; uncommitted path raises SEAL-CONTENT-INCOMPLETE')
PY

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"
printf '{"projectId":"test-staged-seal-fixture","label":"test"}\n' > .collab.json

WORK="$TMPDIR/work"
mkdir -p "$WORK"
git -C "$WORK" init -q
git -C "$WORK" config user.email tester@example.com
git -C "$WORK" config user.name tester
printf 'tracked\n' > "$WORK/tracked.txt"
git -C "$WORK" add tracked.txt
git -C "$WORK" commit -qm 'tracked fixture'
printf 'staged\n' > "$WORK/staged.txt"
git -C "$WORK" add staged.txt

RUN_DATE="$(date +%Y-%m-%d)"
"$ROOT/tools/collab/registry.py" init --agent-id codex --reviewer pa \
  --no-participant-verification --work-repo "$WORK" "Seal Rejects Staged Paths" >/dev/null
TARGET="$RUN_DATE-seal-rejects-staged-paths"
REGISTRY="$("$ROOT/tools/collab/registry.py" registry-path)"
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pa --agent-id opus >/dev/null
"$ROOT/tools/collab/registry.py" join-participants "$TARGET" pe --agent-id codex >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/tools/collab/registry.py" set "$TARGET" active-phase Completion --force --caller-role mod >/dev/null
"$ROOT/tools/collab/registry.py" execution "$TARGET" pe completed "2026-05-23T18:00:00+02:00" \
  --assigned-role pe \
  --validation-result passed \
  --validation-scope scoped \
  --agent-id codex \
  --touched-path staged.txt \
  --caller-role pe >/dev/null

python3 - "$REGISTRY" "$TARGET" <<'PY'
import base64
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
target = sys.argv[2]
data = json.loads(path.read_text())
entry = next(item for item in data['collabs'] if item['id'] == target)
entries = []
for role, state in sorted(entry.get('execution', {}).items()):
    row = {
        'role': role,
        'entryId': state.get('entryId') or f"{role}-execution",
        'status': state.get('status'),
        'date': state.get('date'),
        'validationResult': state.get('validationResult'),
        'validationScope': state.get('validationScope'),
        'touchedPaths': list(state.get('touchedPaths', [])),
        'commits': list(state.get('commits', [])),
    }
    if state.get('contentDigest'):
        row['contentDigest'] = state.get('contentDigest')
    if isinstance(state.get('pathDigests'), dict):
        row['pathDigests'] = state.get('pathDigests')
    if state.get('agentId'):
        row['agentId'] = state.get('agentId')
    entries.append(row)
signature = base64.urlsafe_b64encode(
    json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
).decode().rstrip('=')
entry.setdefault('verification', {})['rounds'] = 1
entry['verification']['subState'] = 'seal'
entry['verification']['pairedExecutionSignature'] = signature
path.write_text(json.dumps(data, indent=2) + '\n')
PY

state="$("$ROOT/tools/collab/registry.py" seal-state "$TARGET" pa)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"
set +e
output="$("$ROOT/tools/collab/registry.py" seal-render "$TARGET" pa \
  --observed-revision "$revision" --caller-role pa 2>&1)"
status=$?
set -e
if [[ "$status" -eq 0 || "$output" != *"SEAL-GIT-STATE"* ]]; then
  printf 'FAIL: seal-render did not reject staged touchedPath with SEAL-GIT-STATE\n%s\n' "$output" >&2
  exit 1
fi

printf 'OK: seal-render rejects staged touchedPaths with SEAL-GIT-STATE\n'
