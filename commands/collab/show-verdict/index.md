# (collab show verdict)

Display the recorded verification verdict metadata for a collaboration record.

## Trigger

**Dispatch:** `(collab show verdict [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab verdict, show verification verdict, closed collab verdict metadata

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Call `commands/collab/engine/registry.py show-verdict <target>`.
3. Display the helper output exactly. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `show verdict`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Output:** JSON with target id, status, active phase, completion sub-state, verification review sub-state, verdict object, and seal metadata when a seal is present.
- **No verdict:** The helper aborts with `verdict unavailable for target` when no assessment verdict has been recorded.
- **Read-only:** The route does not mutate registry state or transcript text.

```route-arg
dispatch: (collab show verdict [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
