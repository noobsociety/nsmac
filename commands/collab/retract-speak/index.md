# /collab retract speak

Retract the current role's latest contribution in the active phase while preserving the original text as audit history.

## Trigger

**Slash:** `/collab retract speak`
**Signature:** `/collab retract speak [--reason <text>]`
**Prose dispatch:** `(collab retract speak ...)` — prose routing hint; not a terminal command.
**Search phrases:** collab retract, withdraw contribution, delete collab speak

## Steps

1. Read [invariants.md](../../../core/collab/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with the same registry targeting rule used by `/collab speak`; when absent, use `activeCollabId`.
2. Resolve the executing role from the current joined participant. If the role is not registered, **ABORT**: role not registered; run `/collab join --role <role>` first.
3. If the record is closed, archived, or in `Completion`, **ABORT** before any write. Completed execution records are finalized by `/collab run plan` and are not retracted by this route.
4. Call `tools/collab/registry.py retract-speak <target> <role> [--reason <text>] --caller-role <role>`.
5. Display the helper output. A successful helper call leaves the original contribution block in place, replaces the visible body with a tombstone, and nests the original text under `Retracted content`.
6. Stop. Do not delete anchors, Table of Contents entries, timestamps, summaries, or revision history.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `retract speak`; when absent, resolved per **Registry targeting** in **Notes**. `--reason <text>` is optional short human text explaining why the contribution is withdrawn.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Transcript-safe semantics:** Retraction is not physical deletion. It preserves the contribution anchor and details block so existing references remain stable.
- **Full-body preservation:** Retraction tombstones the excerpt AND preserves any managed full body under "Retracted content".
- **Rewrite reversibility:** `/collab rewrite speak` replaces a tombstoned contribution in place. The tombstone moves into revision history and the new content becomes the active body. To re-tombstone after a rewrite, run `/collab retract speak` again.
- **Not found:** If no active-phase contribution exists for the role, the helper exits 1 and names the missing role and phase.
- **Already finalized:** In `Completion`, use `/collab rewrite execution` for execution-history correction or a moderator follow-up for governance context.
- **Role boundary:** The helper enforces `--caller-role` equality with the subject role; one participant cannot retract another participant's contribution.

```route-arg
dispatch: (collab retract speak [--reason <text>])
param: name=--reason; required=optional; placeholder=<text>; class=type; rule=free text; default=literal:unspecified
```
