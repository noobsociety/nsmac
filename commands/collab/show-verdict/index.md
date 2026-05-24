# /collab show verdict

Display the recorded verification verdict metadata for a collaboration record.

## Trigger

**Slash:** `/collab show verdict`
**Signature:** `/collab show verdict [<target>]`
**Prose dispatch:** `(collab show verdict [<target>])` — prose routing hint; not a terminal command.
**Search phrases:** collab verdict, show verification verdict, closed collab verdict metadata

## Steps

1. Read [invariants.md](../../../core/collab/invariants.md) before executing; call the helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Call `tools/collab/registry.py show-verdict <target>`.
3. Display the helper output exactly. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `show verdict`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Output:** JSON with target id, status, active phase, completion sub-state, verification review sub-state, verdict object, and seal metadata when a seal is present.
- **No verdict:** The helper aborts with `verdict unavailable for target` when no assessment verdict has been recorded.
- **Read-only:** This route does not mutate registry state or transcript text.

```route-arg
dispatch: (collab show verdict [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
