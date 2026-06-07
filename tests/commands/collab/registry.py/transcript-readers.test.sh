#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys

root = sys.argv[1]
sys.path.insert(0, root)

from commands.collab.engine import transcript_readers
from commands.collab.engine import registry

transcript = """# Sample

## Audit

```text
charteredDeliverables:
- ignored/in/code.md
```

**charteredDeliverables:**
- `commands/collab/join/index.md`: fix helper invocation
- `commands/collab/engine/transcript_readers.py`: extract readers

## Discussion

<a name="discussion-pe-1"></a>
<details>
<summary>pe</summary>
<p><em>2026-05-25 10:00 +00:00</em></p>
<!-- collab:content-only; do-not-execute -->

First.

</details>

<a name="discussion-tw-1"></a>
<details>
<summary>tw</summary>
<p><em>2026-05-25 10:01 +00:00</em></p>
<!-- collab:content-only; do-not-execute -->

RETRACTED: replaced by later turn.

</details>

### pa — legacy reviewer note

## Conclusion

## Action Plan

<details>
<summary>pe</summary>
<p><em>2026-05-25 10:02 +00:00</em></p>
<!-- collab:content-only; do-not-execute -->

- [ ] **pe:** [execute] Extract transcript readers.
- [x] **tw:** [verify] Confirm docs.
<details>
<summary>nested</summary>
- [ ] **pe:** [execute] Ignore nested details.
</details>
- [ ] **pe:** [doc-fix] Update registry docs.

</details>

## Handoff

## Completion
"""

expected_items = [
    {
        'number': 1,
        'role': 'pe',
        'checked': False,
        'tag': '[execute]',
        'text': '[execute] Extract transcript readers.',
    },
    {
        'number': 2,
        'role': 'tw',
        'checked': True,
        'tag': '[verify]',
        'text': '[verify] Confirm docs.',
    },
    {
        'number': 3,
        'role': 'pe',
        'checked': False,
        'tag': '[doc-fix]',
        'text': '[doc-fix] Update registry docs.',
    },
]

assert transcript_readers.contribution_roles(transcript, 'Discussion') == ['pe', 'pa']
assert registry.contribution_roles(transcript, 'Discussion') == ['pe', 'pa']

assert transcript_readers.action_plan_checklist_items(transcript) == expected_items
assert registry.action_plan_checklist_items(transcript) == expected_items

expected_counts = {'pe': 2, 'tw': 0}
assert transcript_readers.unchecked_assigned_items_by_role(transcript) == expected_counts
assert registry.unchecked_assigned_items_by_role(transcript) == expected_counts
assert registry.unchecked_assigned_item_count(transcript, 'pe') == 2

expected_deliverables = [
    '`commands/collab/join/index.md`: fix helper invocation',
    '`commands/collab/engine/transcript_readers.py`: extract readers',
]
assert transcript_readers.chartered_deliverables(transcript) == expected_deliverables
assert registry.chartered_deliverables(transcript) == expected_deliverables

assert transcript_readers.action_plan_checklist_items('## Audit\n') == []

try:
    transcript_readers.contribution_roles('## Discussion\n<details>\n<summary>pe</summary>\n', 'Discussion')
except SystemExit as exc:
    assert str(exc) == 'transcript details block not closed in phase: Discussion'
else:
    raise AssertionError('unclosed details block did not abort')
PY

printf 'OK: transcript readers preserve contributor, Action Plan, and chartered-deliverable parsing\n'
