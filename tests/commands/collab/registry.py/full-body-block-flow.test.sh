#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
export COLLAB_STATE_HOME="$TMPDIR/state-home"

RUN_DATE="$(date +%Y-%m-%d)"
TARGET="$RUN_DATE-full-body-flow"

"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Full Body Flow" >/dev/null
REGISTRY="$("$ROOT/commands/collab/engine/registry.py" registry-path)"
"$ROOT/commands/collab/engine/registry.py" join-participants "$TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$TARGET" active-phase Discussion --force --caller-role mod >/dev/null

state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$TARGET" pe)"
revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$state")"

printf 'Visible excerpt with the standalone finding.\n' >excerpt.md
python3 - <<'PY' >full-body.md
print(' '.join(f'fullbodyword{i}' for i in range(280)))
PY

"$ROOT/commands/collab/engine/registry.py" speak-render "$TARGET" pe \
  --content-file excerpt.md \
  --full-body-file full-body.md \
  --observed-revision "$revision" \
  --caller-role pe >/dev/null

transcript_path="$(python3 - "$REGISTRY" "$TARGET" <<'PY'
import json
import sys
from pathlib import Path
registry = Path(sys.argv[1])
target = sys.argv[2]
entry = next(item for item in json.loads(registry.read_text())['collabs'] if item['id'] == target)
print(registry.parent / Path(entry['transcriptPath']).with_name(f"{Path(entry['transcriptPath']).stem}-raw.md"))
PY
)"

python3 - "$transcript_path" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
assert '<summary>Full contribution</summary>' in text
assert 'fullbodyword279' in text
assert 'Visible excerpt with the standalone finding.' in text
PY

"$ROOT/commands/collab/engine/registry.py" transcript-view "$TARGET" Discussion --raw >raw-view.md
"$ROOT/commands/collab/engine/registry.py" transcript-view "$TARGET" Audit --raw >audit-view.md
"$ROOT/commands/collab/engine/registry.py" aggregate "$TARGET" >/dev/null
"$ROOT/commands/collab/engine/registry.py" transcript-view "$TARGET" Discussion >discussion-view.md

grep -Fq 'fullbodyword279' raw-view.md
if grep -Fq 'Visible excerpt with the standalone finding.' audit-view.md; then
  printf 'FAIL: Audit phase view exposed Discussion contribution\n' >&2
  exit 1
fi
if grep -Fq 'fullbodyword279' discussion-view.md; then
  printf 'FAIL: rendered Discussion view exposed full-body content\n' >&2
  exit 1
fi
grep -Fq 'Visible excerpt with the standalone finding.' discussion-view.md

printf 'Rewritten visible excerpt.\n' >rewrite-excerpt.md
printf 'Rewritten full body text.\n' >rewrite-full-body.md
"$ROOT/commands/collab/engine/registry.py" rewrite-speak-render "$TARGET" pe \
  --content-file rewrite-excerpt.md \
  --full-body-file rewrite-full-body.md \
  --caller-role pe >/dev/null

python3 - "$transcript_path" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
assert 'Rewritten visible excerpt.' in text
assert 'Rewritten full body text.' in text
assert 'Previous revision,' in text
assert 'fullbodyword279' in text
PY

"$ROOT/commands/collab/engine/registry.py" retract-speak "$TARGET" pe --reason "test withdrawal" --caller-role pe >/dev/null

python3 - "$transcript_path" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
assert 'RETRACTED: contribution withdrawn; retained for audit history.' in text
assert '<details><summary>Retracted content</summary>' in text
assert 'Rewritten full body text.' in text
PY

REJECT_TARGET="$RUN_DATE-full-body-reject-details"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Full Body Reject Details" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$REJECT_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$REJECT_TARGET" turn-order pe --caller-role mod >/dev/null
reject_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$REJECT_TARGET" pe)"
reject_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$reject_state")"
cat >bad-excerpt.md <<'BAD'
Visible text.
<details>
<summary>Full contribution</summary>

hand-authored full body

</details>
BAD

set +e
reject_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$REJECT_TARGET" pe --content-file bad-excerpt.md --observed-revision "$reject_revision" --caller-role pe 2>&1)"
reject_status=$?
set -e

if [[ "$reject_status" -eq 0 || "$reject_output" != *"excerpt must not contain hand-authored <details> blocks"* ]]; then
  printf 'FAIL: speak-render did not reject hand-authored excerpt details\n%s\n' "$reject_output" >&2
  exit 1
fi

CLOSE_TAG_TARGET="$RUN_DATE-full-body-reject-close-tag"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Full Body Reject Close Tag" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$CLOSE_TAG_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$CLOSE_TAG_TARGET" turn-order pe --caller-role mod >/dev/null
close_tag_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$CLOSE_TAG_TARGET" pe)"
close_tag_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$close_tag_state")"
printf 'Visible text.\n</details>\nEscaped text.\n' >bad-close-excerpt.md

set +e
close_tag_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$CLOSE_TAG_TARGET" pe --content-file bad-close-excerpt.md --observed-revision "$close_tag_revision" --caller-role pe 2>&1)"
close_tag_status=$?
set -e

if [[ "$close_tag_status" -eq 0 || "$close_tag_output" != *"excerpt must not contain hand-authored <details> blocks"* ]]; then
  printf 'FAIL: speak-render did not reject excerpt closing details tag\n%s\n' "$close_tag_output" >&2
  exit 1
fi

FULL_BODY_CONTROL_TARGET="$RUN_DATE-full-body-reject-control-lines"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Full Body Reject Control Lines" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$FULL_BODY_CONTROL_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$FULL_BODY_CONTROL_TARGET" turn-order pe --caller-role mod >/dev/null
full_body_control_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$FULL_BODY_CONTROL_TARGET" pe)"
full_body_control_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$full_body_control_state")"
printf 'Visible text.\n' >safe-excerpt.md
printf 'Full body text.\n</details>\nEscaped text.\n' >bad-full-body.md

set +e
full_body_control_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$FULL_BODY_CONTROL_TARGET" pe --content-file safe-excerpt.md --full-body-file bad-full-body.md --observed-revision "$full_body_control_revision" --caller-role pe 2>&1)"
full_body_control_status=$?
set -e

if [[ "$full_body_control_status" -eq 0 || "$full_body_control_output" != *"full body must not contain hand-authored <details> control lines"* ]]; then
  printf 'FAIL: speak-render did not reject full-body details control line\n%s\n' "$full_body_control_output" >&2
  exit 1
fi

OVER_LIMIT_TARGET="$RUN_DATE-full-body-over-limit-hint"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Full Body Over Limit Hint" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$OVER_LIMIT_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$OVER_LIMIT_TARGET" turn-order pe --caller-role mod >/dev/null
over_limit_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$OVER_LIMIT_TARGET" pe)"
over_limit_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$over_limit_state")"
python3 - <<'PY' >over-limit-excerpt.md
print(' '.join(f'overflowword{i}' for i in range(251)))
PY

set +e
over_limit_output="$("$ROOT/commands/collab/engine/registry.py" speak-render "$OVER_LIMIT_TARGET" pe --content-file over-limit-excerpt.md --observed-revision "$over_limit_revision" --caller-role pe 2>&1)"
over_limit_status=$?
set -e

if [[ "$over_limit_status" -eq 0 || "$over_limit_output" != *"contribution excerpt is 251 words; limit is 250; keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file"* ]]; then
  printf 'FAIL: speak-render did not include full-body recovery hint on over-limit excerpt\n%s\n' "$over_limit_output" >&2
  exit 1
fi

REWRITE_EFFORT_TARGET="$RUN_DATE-full-body-rewrite-effort"
"$ROOT/commands/collab/engine/registry.py" init --agent-id codex "Full Body Rewrite Effort" >/dev/null
"$ROOT/commands/collab/engine/registry.py" join-participants "$REWRITE_EFFORT_TARGET" pe --agent-id gpt >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$REWRITE_EFFORT_TARGET" turn-order pe --caller-role mod >/dev/null
"$ROOT/commands/collab/engine/registry.py" set "$REWRITE_EFFORT_TARGET" active-phase Discussion --force --caller-role mod >/dev/null
rewrite_effort_state="$("$ROOT/commands/collab/engine/registry.py" speak-state "$REWRITE_EFFORT_TARGET" pe)"
rewrite_effort_revision="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["registryRevision"])' <<<"$rewrite_effort_state")"
printf 'Initial visible excerpt.\n' >rewrite-initial.md
"$ROOT/commands/collab/engine/registry.py" speak-render "$REWRITE_EFFORT_TARGET" pe --content-file rewrite-initial.md --observed-revision "$rewrite_effort_revision" --caller-role pe >/dev/null
printf 'EFFORT OVERRIDE: matrix\nEFFORT OVERRIDE: matrix\n' >bad-rewrite-effort.md

set +e
rewrite_effort_output="$("$ROOT/commands/collab/engine/registry.py" rewrite-speak-render "$REWRITE_EFFORT_TARGET" pe --content-file bad-rewrite-effort.md --caller-role pe 2>&1)"
rewrite_effort_status=$?
set -e

if [[ "$rewrite_effort_status" -eq 0 || "$rewrite_effort_output" != *"EFFORT OVERRIDE must appear at most once"* ]]; then
  printf 'FAIL: rewrite-speak-render did not reject duplicate effort override lines\n%s\n' "$rewrite_effort_output" >&2
  exit 1
fi

grep -Fq 'The cap is a visible-excerpt budget, not a total contribution budget.' "$ROOT/commands/collab/reference/contribution-budget.md"
grep -Fq 'Agents must not summarize away or omit that detail solely to satisfy the excerpt cap.' "$ROOT/commands/collab/reference/contribution-budget.md"
grep -Fq 'preserve that material in the full body instead of trimming it out' "$ROOT/commands/collab/speak/index.md"

printf 'OK: full-body blocks are helper-owned, budget-exempt, rewrite/retract-preserved, and hidden from rendered non-Audit reads\n'
